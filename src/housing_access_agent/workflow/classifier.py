"""Classify requests by topic, scope, time period, and research mode."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Assumption, LocationLevel, Outcome, Verdict
from housing_access_agent.domain.errors import ClassificationError, ModelUnavailableError
from housing_access_agent.domain.models import (
    ClassifiedRequest,
    Location,
    ModelClassification,
    Period,
)
from housing_access_agent.prompts import CLASSIFIER_SYSTEM, render_user_turns
from housing_access_agent.state import ResearchState

logger = logging.getLogger(__name__)

DEFAULT_LOCATION = Location(name="España", level=LocationLevel.SPAIN)
DEFAULT_PERIOD = Period(label="latest available data")
BACKOFF_SECONDS = 0.5

ClassifierNode = Callable[[ResearchState], Awaitable[dict[str, Any]]]


def make_classifier(
    model: BaseChatModel,
    settings: Settings,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ClassifierNode:
    """Build the classify node around an injected chat model."""
    structured = model.with_structured_output(ModelClassification, method="json_schema")
    attempts = 1 + settings.http_max_retries

    async def extract(turns: list[str]) -> ModelClassification:
        messages = [SystemMessage(CLASSIFIER_SYSTEM), HumanMessage(render_user_turns(turns))]
        for attempt in range(attempts):
            try:
                result = await structured.ainvoke(messages)
            except ValueError as error:
                # Pydantic validation and output parsing errors are ValueErrors.
                logger.warning("Invalid classifier output (attempt %d): %s", attempt + 1, type(error).__name__)
                # The error text holds the model's output; DEBUG only, as it may echo the question.
                logger.debug("Invalid model output (attempt %d): %s", attempt + 1, error)
            except Exception as error:
                raise ModelUnavailableError(type(error).__name__) from error
            else:
                if isinstance(result, ModelClassification):
                    logger.debug("Model classification (attempt %d): %s", attempt + 1, result.model_dump_json())
                    return result
                logger.warning("Empty classifier output (attempt %d)", attempt + 1)
            if attempt + 1 < attempts:
                await sleep(BACKOFF_SECONDS * 2**attempt)
        raise ClassificationError(f"No valid classification after {attempts} attempts")

    async def classify(state: ResearchState) -> dict[str, Any]:
        extracted = await extract(state.get("user_turns", []))
        classified = apply_defaults(extracted)
        rounds = state.get("clarification_rounds", 0)

        if classified.verdict is Verdict.IN_SCOPE:
            return {"classification": classified, "outcome": Outcome.IN_SCOPE}
        if classified.verdict is Verdict.OUT_OF_SCOPE:
            return {"classification": classified, "outcome": Outcome.OUT_OF_SCOPE}
        if rounds < settings.max_clarification_rounds:
            return {
                "classification": classified,
                "outcome": Outcome.NEEDS_CLARIFICATION,
                "clarification_rounds": rounds + 1,
            }
        return {"classification": classified, "outcome": Outcome.CLARIFICATION_EXHAUSTED}

    return classify


def apply_defaults(extracted: ModelClassification) -> ClassifiedRequest:
    """Fill in a missing location or period and record every assumption."""
    assumptions: list[Assumption] = []
    location = extracted.location
    if location is None:
        location = DEFAULT_LOCATION
        assumptions.append(Assumption.DEFAULT_LOCATION_SPAIN)
    elif location.level is LocationLevel.UNSPECIFIED:
        assumptions.append(Assumption.LOCATION_LEVEL_UNSPECIFIED)

    period = extracted.period
    if period is None:
        period = DEFAULT_PERIOD
        assumptions.append(Assumption.DEFAULT_PERIOD_LATEST)

    reframed = (extracted.reframed_question or "").strip() or None
    if reframed:
        assumptions.append(Assumption.NO_PERSONAL_ADVICE)

    return ClassifiedRequest(
        **extracted.model_dump(exclude={"location", "period", "reframed_question"}),
        location=location,
        period=period,
        reframed_question=reframed,
        assumptions=assumptions,
    )
