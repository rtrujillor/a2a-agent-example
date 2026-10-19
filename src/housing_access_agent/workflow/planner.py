"""Plan bounded searches and evidence requirements for a request."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import SourceKind, Topic
from housing_access_agent.domain.errors import ModelUnavailableError, PlanningError
from housing_access_agent.domain.models import ModelPlan, PlanStep, ResearchPlan
from housing_access_agent.prompts import PLANNER_SYSTEM, render_planning_request
from housing_access_agent.state import ResearchState
from housing_access_agent.tools.catalog import DEFAULT_CATALOG, ToolCatalog, domain_matches, normalize_domain

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = 0.5

PlannerNode = Callable[[ResearchState], Awaitable[dict[str, Any]]]


def plan_budget(settings: Settings, iteration: int, searches_used: int) -> int:
    """Searches a plan may use; the first plan keeps one per allowed replan."""
    remaining = settings.max_searches_per_request - searches_used
    if iteration == 0:
        first = settings.max_searches_per_request - settings.max_planner_iterations
        return max(1, min(remaining, first))
    return max(0, remaining)


def _site(raw: str) -> str:
    """A bare domain from what the model wrote, tolerating a scheme or path."""
    raw = raw.strip()
    if "://" in raw:
        try:
            raw = urlsplit(raw).hostname or ""
        except ValueError:
            return ""
    return normalize_domain(raw.split("/")[0])


def enforce_plan(
    proposed: ModelPlan,
    topic: Topic | None,
    budget: int,
    catalog: ToolCatalog,
    iteration: int = 0,
) -> ResearchPlan | None:
    """Apply the catalog, allowlist, budget, and official-first rules, or None."""
    allowlist = catalog.allowlist(topic)
    valid: list[PlanStep] = []
    for step in proposed.steps:
        tool = catalog.tool(step.tool)
        query = step.query.strip()
        if tool is None or not query:
            continue
        sites = list(dict.fromkeys(site for site in map(_site, step.sites) if site))
        if any(not domain_matches(site, allowlist) for site in sites):
            continue
        kind = step.source_kind
        if sites:
            kind = SourceKind.OFFICIAL
        elif kind is SourceKind.OFFICIAL:
            if not allowlist:
                continue
            sites = list(allowlist)
        valid.append(
            PlanStep(
                sub_question=step.sub_question.strip(),
                tool=tool,
                query=query,
                query_language=step.query_language,
                source_kind=kind,
                freshness=step.freshness,
                sites=sites,
            )
        )

    kept = valid[:budget]
    if allowlist and not any(step.source_kind is SourceKind.OFFICIAL for step in kept):
        official = next((step for step in valid[budget:] if step.source_kind is SourceKind.OFFICIAL), None)
        if official is None or not kept:
            return None
        # Every kept step is non-official here, so the last one gives way.
        kept[-1] = official
    if not kept:
        return None
    return ResearchPlan(steps=kept, iteration=iteration)


def make_planner(
    model: BaseChatModel,
    settings: Settings,
    catalog: ToolCatalog = DEFAULT_CATALOG,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> PlannerNode:
    """Build the plan node around an injected chat model."""
    structured = model.with_structured_output(ModelPlan, method="json_schema")
    attempts = 1 + settings.http_max_retries
    tools = sorted(tool.value for tool in catalog.tools)

    async def plan(state: ResearchState) -> dict[str, Any]:
        classified = state.get("classification")
        if classified is None:
            raise PlanningError("No classification to plan for")
        iteration = state.get("planner_iterations", 0)
        budget = plan_budget(settings, iteration, state.get("searches_used", 0))
        allowlist = catalog.allowlist(classified.topic)
        # Only the classification reaches the planner, never the user's own messages.
        messages = [
            SystemMessage(PLANNER_SYSTEM),
            HumanMessage(render_planning_request(classified, budget, tools, allowlist)),
        ]
        for attempt in range(attempts):
            try:
                result = await structured.ainvoke(messages)
            except ValueError as error:
                logger.warning("Invalid planner output (attempt %d): %s", attempt + 1, type(error).__name__)
                logger.debug("Invalid planner output (attempt %d): %s", attempt + 1, error)
            except Exception as error:
                raise ModelUnavailableError(type(error).__name__) from error
            else:
                if isinstance(result, ModelPlan):
                    # Queries derive from the question, so they are logged at DEBUG only.
                    logger.debug("Proposed plan (attempt %d): %s", attempt + 1, result.model_dump_json())
                    enforced = enforce_plan(result, classified.topic, budget, catalog, iteration)
                    if enforced is not None:
                        logger.info(
                            "Plan with %d of %d proposed steps (budget %d)",
                            len(enforced.steps),
                            len(result.steps),
                            budget,
                        )
                        return {"plan": enforced, "planner_iterations": iteration + 1}
                    logger.warning("No valid plan after enforcement (attempt %d)", attempt + 1)
                else:
                    logger.warning("Empty planner output (attempt %d)", attempt + 1)
            if attempt + 1 < attempts:
                await sleep(BACKOFF_SECONDS * 2**attempt)
        raise PlanningError(f"No valid plan after {attempts} attempts")

    return plan
