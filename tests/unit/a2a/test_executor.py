import asyncio
import logging

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.types import Message, Part, Role, SendMessageRequest, Task, TaskState, TaskStatus, TaskStatusUpdateEvent
from langgraph.types import Overwrite

from housing_access_agent.a2a.executor import HousingAgentExecutor
from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Outcome, Topic
from housing_access_agent.domain.errors import ClassificationError, ModelUnavailableError, PlanningError
from housing_access_agent.domain.models import ModelClassification, ModelPlan
from housing_access_agent.tools.catalog import DEFAULT_CATALOG
from housing_access_agent.workflow.classifier import apply_defaults
from housing_access_agent.workflow.planner import enforce_plan
from tests.fakes import ambiguous, classification, media_step, plan, plan_step

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
    return state


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
    assert states[3][0] == TaskState.TASK_STATE_COMPLETED
    assert "aún no está disponible" in states[3][1]


async def test_english_request_gets_english_texts():
    events = await _run(StubGraph(_state(Outcome.IN_SCOPE, **classification(language="en"))))

    states = _statuses(events)
    assert states[1][1].startswith("Understood: rents")
    assert states[2][1].startswith("Research plan (2 searches):")
    assert "not available yet" in states[3][1]


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
    assert [state for state, _ in states] == [TaskState.TASK_STATE_WORKING] * 3 + [TaskState.TASK_STATE_COMPLETED]
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
