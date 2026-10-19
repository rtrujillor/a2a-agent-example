"""Test doubles for the language model. No network access."""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, PrivateAttr


def classification(**overrides: Any) -> dict[str, Any]:
    """A valid in-scope model classification payload, with overrides."""
    payload: dict[str, Any] = {
        "language": "es",
        "verdict": "in_scope",
        "reason": "Pregunta sobre alquileres en Madrid.",
        "topic": "rents",
        "location": {"name": "Madrid", "level": "municipality"},
        "period": {"start_year": 2020, "end_year": None, "label": "desde 2020"},
        "intent": "evolución de los alquileres",
        "depth": "evidence_analysis",
        "clarifying_question": None,
        "reframed_question": None,
    }
    payload.update(overrides)
    return payload


def ambiguous(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "verdict": "ambiguous",
        "reason": "No queda claro qué precios interesan.",
        "topic": None,
        "location": None,
        "period": None,
        "intent": "precios",
        "clarifying_question": "¿Te interesan los precios de compra o de alquiler, y en qué zona?",
    }
    return classification(**(fields | overrides))


def plan_step(**overrides: Any) -> dict[str, Any]:
    """A valid official model plan step payload, with overrides."""
    step: dict[str, Any] = {
        "sub_question": "¿Cuál es el alquiler medio en Madrid?",
        "tool": "web_search",
        "query": "índice de precios de vivienda en alquiler Madrid",
        "query_language": "es",
        "source_kind": "official",
        "freshness": None,
        "sites": ["ine.es"],
    }
    step.update(overrides)
    return step


def media_step(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "sub_question": "¿Qué se ha publicado recientemente?",
        "query": "alquiler Madrid noticias",
        "source_kind": "media",
        "sites": [],
    }
    return plan_step(**(fields | overrides))


def plan(*steps: dict[str, Any]) -> dict[str, Any]:
    """A model plan payload; one official step by default."""
    return {"steps": list(steps) if steps else [plan_step()]}


class FakeStructuredChatModel(BaseChatModel):
    """Chat model whose structured output returns scripted results in order.

    Each script item is a payload dict (validated against the requested schema,
    so an invalid dict raises like a real parse failure) or an exception to raise.
    """

    script: list[Any] = []
    _calls: list[list[BaseMessage]] = PrivateAttr(default_factory=list)
    _schemas: list[Any] = PrivateAttr(default_factory=list)

    @property
    def calls(self) -> list[list[BaseMessage]]:
        return self._calls

    @property
    def methods(self) -> list[Any]:
        return self._schemas

    @property
    def _llm_type(self) -> str:
        return "fake-structured"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise NotImplementedError("Use with_structured_output")

    def with_structured_output(self, schema: type[BaseModel], **kwargs: Any):  # type: ignore[override]
        self._schemas.append(kwargs.get("method"))

        async def respond(messages: Sequence[BaseMessage]) -> BaseModel:
            self._calls.append(list(messages))
            if not self.script:
                raise AssertionError("FakeStructuredChatModel has no scripted result left")
            item = self.script.pop(0)
            if isinstance(item, BaseException):
                raise item
            return schema.model_validate(item)

        return RunnableLambda(respond)
