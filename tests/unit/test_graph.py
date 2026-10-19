import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Overwrite

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Outcome
from housing_access_agent.graph import build_graph
from housing_access_agent.workflow.classifier import make_classifier
from housing_access_agent.workflow.planner import make_planner
from tests.fakes import FakeStructuredChatModel, ambiguous, classification, plan


def _graph(script):
    model = FakeStructuredChatModel(script=list(script))
    settings = Settings(_env_file=None, model_name="fake")
    return build_graph(make_classifier(model, settings), make_planner(model, settings), InMemorySaver()), model


def _config(thread_id):
    return {"configurable": {"thread_id": thread_id}}


async def test_same_thread_accumulates_turns_and_rounds():
    graph, model = _graph([ambiguous(), classification(), plan()])

    first = await graph.ainvoke({"user_turns": ["¿Y los precios?"], "clarification_rounds": 0}, _config("ctx"))
    second = await graph.ainvoke({"user_turns": ["Alquiler en Bilbao"]}, _config("ctx"))

    assert first["outcome"] is Outcome.NEEDS_CLARIFICATION
    assert second["outcome"] is Outcome.IN_SCOPE
    assert second["user_turns"] == ["¿Y los precios?", "Alquiler en Bilbao"]
    assert second["clarification_rounds"] == 1
    assert '<turn n="2">Alquiler en Bilbao</turn>' in model.calls[1][1].content


async def test_overwrite_starts_a_thread_fresh():
    graph, _ = _graph([ambiguous(), classification(), plan()])
    await graph.ainvoke({"user_turns": ["¿Y los precios?"], "clarification_rounds": 0}, _config("ctx"))

    result = await graph.ainvoke(
        {"user_turns": Overwrite(["Alquileres en Madrid"]), "clarification_rounds": 0},
        _config("ctx"),
    )

    assert result["user_turns"] == ["Alquileres en Madrid"]
    assert result["clarification_rounds"] == 0


async def test_threads_do_not_share_turns():
    graph, _ = _graph([ambiguous(), classification(), plan()])
    await graph.ainvoke({"user_turns": ["¿Y los precios?"], "clarification_rounds": 0}, _config("a"))

    result = await graph.ainvoke({"user_turns": ["Alquileres en Madrid"], "clarification_rounds": 0}, _config("b"))

    assert result["user_turns"] == ["Alquileres en Madrid"]


async def test_in_scope_request_is_planned():
    graph, model = _graph([classification(), plan()])

    result = await graph.ainvoke({"user_turns": ["Alquileres en Madrid"], "clarification_rounds": 0}, _config("p"))

    assert result["outcome"] is Outcome.IN_SCOPE
    assert len(result["plan"].steps) == 1
    assert len(model.calls) == 2


@pytest.mark.parametrize(
    "payload",
    [ambiguous(), classification(verdict="out_of_scope", reason="No es vivienda.", topic=None)],
)
async def test_other_outcomes_are_not_planned(payload):
    # The script holds only the classification: a planner call would fail the test.
    graph, model = _graph([payload])

    result = await graph.ainvoke({"user_turns": ["¿Y lo otro?"], "clarification_rounds": 0}, _config("n"))

    assert result.get("plan") is None
    assert len(model.calls) == 1
