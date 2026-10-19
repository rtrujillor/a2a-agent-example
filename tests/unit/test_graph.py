import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Overwrite

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Outcome, ToolName
from housing_access_agent.graph import build_graph
from housing_access_agent.workflow.classifier import make_classifier
from housing_access_agent.workflow.planner import make_planner
from housing_access_agent.workflow.researcher import make_researcher
from tests.fakes import (
    FakeSearchTool,
    FakeStructuredChatModel,
    ambiguous,
    classification,
    media_step,
    plan,
    plan_step,
    source,
)


def _graph(script, searches=None):
    model = FakeStructuredChatModel(script=list(script))
    settings = Settings(_env_file=None, model_name="fake")
    tool = FakeSearchTool(searches if searches is not None else [[source("https://www.ine.es/a")]] * 3)
    graph = build_graph(
        make_classifier(model, settings),
        make_planner(model, settings),
        make_researcher({ToolName.WEB_SEARCH: tool}, settings),
        InMemorySaver(),
    )
    graph.tool = tool
    return graph, model


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
    assert graph.tool.queries == []


async def test_in_scope_plan_is_researched_step_by_step():
    steps = [plan_step(), media_step(query="a"), media_step(query="b")]
    searches = [[source("https://www.ine.es/a")], [source("https://elpais.com/b")], []]
    graph, model = _graph([classification(), plan(*steps)], searches)

    result = await graph.ainvoke({"user_turns": ["Alquileres en Madrid"], "clarification_rounds": 0}, _config("r"))

    assert len(graph.tool.queries) == 3
    assert result["searches_used"] == 3
    assert result["research_step"] == 3
    assert [item.step for item in result["evidence"]] == [0, 1]
    assert [gap.step for gap in result["gaps"]] == [2]
    assert len(model.calls) == 2
