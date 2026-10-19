import asyncio
import logging

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.types import Message, Part, Role, SendMessageRequest, Task, TaskState, TaskStatus, TaskStatusUpdateEvent
from langgraph.types import Overwrite

from housing_access_agent.a2a.executor import HousingAgentExecutor
from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import GapReason, Outcome, Topic
from housing_access_agent.domain.errors import ClassificationError, ModelUnavailableError, PlanningError
from housing_access_agent.domain.models import Evidence, ModelClassification, ModelPlan, SearchGap
from housing_access_agent.tools.catalog import DEFAULT_CATALOG
from housing_access_agent.workflow.classifier import apply_defaults
from housing_access_agent.workflow.planner import enforce_plan
from tests.fakes import ambiguous, classification, media_step, plan, plan_step, source

QUESTION = "¿Cómo han evolucionado los alquileres en Madrid desde 2020?"


class RecordingQueue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


class StubGraph:
    """Yields the given states in order, then raises the error if any."""

    def __init__(self, result=None, error=None, delay=0.0, states=None):
        self.states = states if states is not None else ([result] if result is not None else [])
        self.error, self.delay = error, delay
        self.inputs, self.configs = [], []

    async def astream(self, graph_input, config, *, stream_mode):
        self.inputs.append(graph_input)
        self.configs.append(config)
        if self.delay:
            await asyncio.sleep(self.delay)
        for state in self.states:
            yield state
        if self.error:
            raise self.error


def _plan(*steps):
    proposed = ModelPlan.model_validate(plan(*steps) if steps else plan(plan_step(), media_step()))
    return enforce_plan(proposed, Topic.RENTS, 4, DEFAULT_CATALOG)


def _state(outcome, **payload):
    data = payload or classification()
    state = {"outcome": outcome, "classification": apply_defaults(ModelClassification.model_validate(data))}
    if outcome is Outcome.IN_SCOPE:
        state["plan"] = _plan()
        state |= _researched()
    return state


def _researched(evidence=None, gaps=None, steps=2):
    """State after research of the default two-step plan: one official and one media source."""
    if evidence is None:
        evidence = [
            Evidence(step=0, source=source("https://www.ine.es/prensa/ipva.htm")),
            Evidence(step=1, source=source("https://elpais.com/economia/alquiler")),
        ]
    return {"research_step": steps, "evidence": evidence, "gaps": gaps or [], "searches_used": steps}


def _context(parts=None, task=None):
    message = Message(
        message_id="m1",
        role=Role.ROLE_USER,
        parts=parts if parts is not None else [Part(text=QUESTION)],
        task_id=task.id if task else "",
        context_id=task.context_id if task else "",
    )
    return RequestContext(
        ServerCallContext(),
        request=SendMessageRequest(message=message),
        task_id=task.id if task else None,
        context_id=task.context_id if task else None,
        task=task,
    )


async def _run(graph, context=None, **settings):
    queue = RecordingQueue()
    executor = HousingAgentExecutor(graph, Settings(_env_file=None, model_name="m", **settings))
    await executor.execute(context or _context(), queue)
    return queue.events


def _statuses(events):
    return [(e.status.state, "".join(p.text for p in e.status.message.parts)) for e in events if isinstance(e, TaskStatusUpdateEvent)]


async def test_in_scope_reports_interpretation_then_completes():
    events = await _run(StubGraph(_state(Outcome.IN_SCOPE)))

    assert isinstance(events[0], Task)
    assert events[0].id and events[0].context_id
    states = _statuses(events)
    assert states[0] == (TaskState.TASK_STATE_WORKING, "")
    assert states[1][0] == TaskState.TASK_STATE_WORKING
    assert states[1][1].startswith("Entendido: alquileres · Madrid")
    assert states[2][0] == TaskState.TASK_STATE_WORKING
    assert states[2][1].startswith("Plan de investigación (2 búsquedas):")
    assert states[3] == (
        TaskState.TASK_STATE_WORKING,
        "Búsqueda 1/2 · fuentes oficiales: ¿Cuál es el alquiler medio en Madrid?\nFuentes encontradas: 1.",
    )
    assert states[4][1].startswith("Búsqueda 2/2 · medios:")
    assert states[5][0] == TaskState.TASK_STATE_COMPLETED
    assert states[5][1].startswith("Fuentes encontradas: 2 (oficiales: 1 · medios: 1).")
    assert "aún no están disponibles" in states[5][1]
    assert len(states) == 6


async def test_english_request_gets_english_texts():
    events = await _run(StubGraph(_state(Outcome.IN_SCOPE, **classification(language="en"))))

    states = _statuses(events)
    assert states[1][1].startswith("Understood: rents")
    assert states[2][1].startswith("Research plan (2 searches):")
    assert states[3][1].startswith("Search 1/2 · official sources:")
    assert states[5][1].startswith("Sources found: 2 (official: 1 · media: 1).")
    assert "not available yet" in states[5][1]


async def test_needs_clarification_requires_input_with_question():
    events = await _run(StubGraph(_state(Outcome.NEEDS_CLARIFICATION, **ambiguous())))

    state, message = _statuses(events)[-1]
    assert state == TaskState.TASK_STATE_INPUT_REQUIRED
    assert message == ambiguous()["clarifying_question"]


async def test_out_of_scope_rejects_with_reason_and_scope_hint():
    payload = classification(verdict="out_of_scope", reason="No es una pregunta sobre vivienda.", topic=None)
    events = await _run(StubGraph(_state(Outcome.OUT_OF_SCOPE, **payload)))

    state, message = _statuses(events)[-1]
    assert state == TaskState.TASK_STATE_REJECTED
    assert message.startswith("No es una pregunta sobre vivienda.")
    assert "acceso a la vivienda en España" in message


async def test_exhausted_clarification_rejects_with_rephrase():
    events = await _run(StubGraph(_state(Outcome.CLARIFICATION_EXHAUSTED, **ambiguous())))

    state, message = _statuses(events)[-1]
    assert state == TaskState.TASK_STATE_REJECTED
    assert message.startswith("No he podido interpretar la pregunta")


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        ([Part(text="x" * 2001)], "2.000 caracteres"),
        ([Part(text="   \n ")], "Escribe una pregunta"),
        ([Part(text="a"), Part(text="b")], "Solo se acepta una pregunta"),
        ([Part(url="https://example.org/a.pdf")], "Solo se acepta una pregunta"),
        ([Part(text="hola", media_type="text/html")], "Solo se acepta una pregunta"),
        ([], "Solo se acepta una pregunta"),
    ],
)
async def test_intake_guards_reject_without_running_the_graph(parts, expected):
    graph = StubGraph(_state(Outcome.IN_SCOPE))
    events = await _run(graph, _context(parts=parts))

    assert graph.inputs == []
    (status,) = _statuses(events)
    assert status[0] == TaskState.TASK_STATE_REJECTED
    assert expected in status[1]


async def test_exactly_2000_characters_is_accepted():
    graph = StubGraph(_state(Outcome.IN_SCOPE))
    await _run(graph, _context(parts=[Part(text="x" * 2000)]))

    assert graph.inputs[0]["user_turns"].value == ["x" * 2000]


async def test_new_task_overwrites_turns_and_uses_context_as_thread():
    graph = StubGraph(_state(Outcome.IN_SCOPE))
    await _run(graph, _context(parts=[Part(text=f"  {QUESTION}\n")]))

    graph_input = graph.inputs[0]
    assert isinstance(graph_input["user_turns"], Overwrite)
    assert graph_input["user_turns"].value == [QUESTION]
    assert graph_input["clarification_rounds"] == 0
    assert graph.configs[0]["configurable"]["thread_id"]


async def test_continuation_appends_the_reply():
    task = Task(id="t1", context_id="c1", status=TaskStatus(state=TaskState.TASK_STATE_INPUT_REQUIRED))
    graph = StubGraph(_state(Outcome.IN_SCOPE))
    events = await _run(graph, _context(parts=[Part(text="Alquiler en Bilbao")], task=task))

    assert not any(isinstance(e, Task) for e in events)
    assert graph.inputs[0] == {
        "user_turns": ["Alquiler en Bilbao"],
        "plan": None,
        "planner_iterations": 0,
        "searches_used": 0,
        "research_step": 0,
        "evidence": [],
        "gaps": [],
    }
    assert graph.configs[0]["configurable"]["thread_id"] == "c1"


@pytest.mark.parametrize(
    "error",
    [
        ClassificationError("bad output"),
        PlanningError("no plan"),
        ModelUnavailableError("APIConnectionError"),
        RuntimeError("Traceback secret"),
    ],
)
async def test_errors_fail_with_fixed_text(error, caplog):
    caplog.set_level(logging.INFO)
    events = await _run(StubGraph(error=error))

    state, message = _statuses(events)[-1]
    assert state == TaskState.TASK_STATE_FAILED
    assert message == "No se ha podido procesar la solicitud. Inténtalo de nuevo más tarde."
    assert QUESTION not in caplog.text


async def test_timeout_fails_with_fixed_text():
    events = await _run(StubGraph(_state(Outcome.IN_SCOPE), delay=1), request_timeout_seconds=0.01)

    state, message = _statuses(events)[-1]
    assert state == TaskState.TASK_STATE_FAILED
    assert "Traceback" not in message


async def test_cancel_publishes_canceled():
    queue = RecordingQueue()
    task = Task(id="t1", context_id="c1", status=TaskStatus(state=TaskState.TASK_STATE_WORKING))
    executor = HousingAgentExecutor(StubGraph(), Settings(_env_file=None, model_name="m"))

    await executor.cancel(_context(task=task), queue)

    assert _statuses(queue.events) == [(TaskState.TASK_STATE_CANCELED, "")]


def test_executor_does_not_import_model_or_tools():
    import housing_access_agent.a2a.executor as module

    source = open(module.__file__, encoding="utf-8").read()
    for name in ("langchain_openai", "openai", "httpx", "housing_access_agent.tools", "housing_access_agent.workflow"):
        assert name not in source


async def test_interpretation_is_sent_before_planning_runs():
    classified = _state(Outcome.IN_SCOPE)
    after_classify = {k: v for k, v in classified.items() if k != "plan"}
    events = await _run(StubGraph(states=[{}, after_classify, classified]))

    states = _statuses(events)
    assert [state for state, _ in states] == [TaskState.TASK_STATE_WORKING] * 5 + [TaskState.TASK_STATE_COMPLETED]
    assert states[1][1].startswith("Entendido")
    assert states[2][1].startswith("Plan de investigación")


async def test_planning_failure_after_interpretation_has_no_plan_update():
    classified = _state(Outcome.IN_SCOPE)
    after_classify = {k: v for k, v in classified.items() if k != "plan"}
    events = await _run(StubGraph(states=[after_classify], error=PlanningError("no plan")))

    states = _statuses(events)
    assert states[1][1].startswith("Entendido")
    assert not any(message.startswith("Plan de investigación") for _, message in states)
    assert states[-1] == (TaskState.TASK_STATE_FAILED, "No se ha podido procesar la solicitud. Inténtalo de nuevo más tarde.")


async def test_in_scope_without_plan_fails():
    state = _state(Outcome.IN_SCOPE)
    del state["plan"]
    events = await _run(StubGraph(state))

    assert _statuses(events)[-1][0] == TaskState.TASK_STATE_FAILED


async def test_no_plan_update_for_ambiguous_request_with_stale_plan():
    # A checkpointed plan from an earlier round must not be reported.
    stale = _state(Outcome.NEEDS_CLARIFICATION, **ambiguous()) | {"plan": _plan()}
    events = await _run(StubGraph(stale))

    assert not any("Plan de investigación" in message for _, message in _statuses(events))


async def test_each_search_is_reported_once_as_it_finishes():
    planned = _state(Outcome.IN_SCOPE) | _researched(evidence=[], steps=0)
    first = planned | _researched(evidence=_state(Outcome.IN_SCOPE)["evidence"][:1], steps=1)
    second = _state(Outcome.IN_SCOPE)
    events = await _run(StubGraph(states=[planned, first, first, second]))

    messages = [message for _, message in _statuses(events)]
    searches = [message for message in messages if message.startswith("Búsqueda")]
    assert [m.splitlines()[0][:13] for m in searches] == ["Búsqueda 1/2 ", "Búsqueda 2/2 "]
    assert messages.index(searches[0]) > next(i for i, m in enumerate(messages) if m.startswith("Plan"))


async def test_no_search_update_for_ambiguous_request_with_stale_research():
    stale = _state(Outcome.NEEDS_CLARIFICATION, **ambiguous()) | {"plan": _plan()} | _researched()
    events = await _run(StubGraph(stale))

    assert not any(message.startswith("Búsqueda") for _, message in _statuses(events))


async def test_every_search_a_gap_fails_after_the_search_updates(caplog):
    gaps = [SearchGap(step=0, reason=GapReason.FAILED), SearchGap(step=1, reason=GapReason.EMPTY)]
    state = _state(Outcome.IN_SCOPE) | _researched(evidence=[], gaps=gaps)
    with caplog.at_level(logging.WARNING):
        events = await _run(StubGraph(state))

    states = _statuses(events)
    assert states[3][1].endswith("No se ha podido completar la búsqueda.")
    assert states[4][1].endswith("Sin resultados.")
    assert states[-1] == (TaskState.TASK_STATE_FAILED, "No se ha podido procesar la solicitud. Inténtalo de nuevo más tarde.")
    assert "no search kept a source" in caplog.text
    assert QUESTION not in caplog.text


async def test_search_texts_hide_queries_and_domains():
    events = await _run(StubGraph(_state(Outcome.IN_SCOPE)))

    for _, message in _statuses(events):
        for hidden in ("site:", "ine.es", "https://", plan_step()["query"]):
            assert hidden not in message


async def test_new_round_resets_research():
    graph = StubGraph(_state(Outcome.IN_SCOPE))
    await _run(graph)

    graph_input = graph.inputs[0]
    assert graph_input["research_step"] == 0
    assert graph_input["evidence"] == [] and graph_input["gaps"] == []
