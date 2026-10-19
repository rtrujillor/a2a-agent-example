"""Bridge between A2A requests and the LangGraph workflow."""

import asyncio
import logging
from typing import Any, Protocol

from a2a.helpers.proto_helpers import new_task, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState
from langgraph.types import Overwrite

from housing_access_agent.a2a.messages import Text, interpretation, plan_summary, search_update, sources_summary, text
from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Outcome
from housing_access_agent.domain.errors import ClassificationError, ModelUnavailableError, PlanningError
from housing_access_agent.domain.models import ClassifiedRequest, Evidence, ResearchPlan, SearchGap

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 2000
TEXT_MEDIA_TYPES = {"", "text/plain"}


class ResearchGraph(Protocol):
    def astream(self, input: Any, config: Any, *, stream_mode: str) -> Any: ...


def read_question(message: Message | None) -> tuple[str | None, Text | None]:
    """Return the trimmed question, or the intake error to report."""
    if message is None or len(message.parts) != 1:
        return None, Text.INTAKE_UNSUPPORTED
    part = message.parts[0]
    if part.WhichOneof("content") != "text" or part.media_type not in TEXT_MEDIA_TYPES:
        return None, Text.INTAKE_UNSUPPORTED
    question = part.text.strip()
    if not question:
        return None, Text.INTAKE_EMPTY
    if len(question) > MAX_QUESTION_LENGTH:
        return None, Text.INTAKE_TOO_LONG
    return question, None


class HousingAgentExecutor(AgentExecutor):
    """Turns A2A messages into graph runs and graph outcomes into task states."""

    def __init__(self, graph: ResearchGraph, settings: Settings, callbacks: list[Any] | None = None):
        self._graph = graph
        self._settings = settings
        self._callbacks = callbacks or []

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id, context_id = context.task_id or "", context.context_id or ""
        updater = TaskUpdater(event_queue, task_id, context_id)

        def say(message: str) -> Message:
            return updater.new_agent_message(parts=[new_text_part(message)])

        current = context.current_task
        if current is None:
            history = [context.message] if context.message else []
            await event_queue.enqueue_event(
                new_task(task_id, context_id, TaskState.TASK_STATE_SUBMITTED, history=history)
            )

        question, intake_error = read_question(context.message)
        if intake_error is not None:
            logger.info("Task %s rejected at intake: %s", task_id, intake_error.value)
            await updater.reject(say(text(intake_error)))
            return

        await updater.start_work()

        continuing = current is not None and current.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
        # A plan or search from an earlier round in this context must never be reported again.
        research_reset: dict[str, Any] = {
            "plan": None,
            "planner_iterations": 0,
            "searches_used": 0,
            "research_step": 0,
            "evidence": [],
            "gaps": [],
        }
        graph_input: dict[str, Any] = (
            {"user_turns": [question], **research_reset}
            if continuing
            else {
                "user_turns": Overwrite([question]),
                "clarification_rounds": 0,
                "classification": None,
                "outcome": None,
                **research_reset,
            }
        )
        config = {"configurable": {"thread_id": context_id}, "callbacks": self._callbacks}

        interpreted = planned = False
        reported_steps = 0

        async def report_progress(state: dict[str, Any]) -> None:
            """Send each step once, as soon as the streamed state first holds it."""
            nonlocal interpreted, planned, reported_steps
            classified: ClassifiedRequest | None = state.get("classification")
            if classified is None or state.get("outcome") is not Outcome.IN_SCOPE:
                return
            if not interpreted:
                interpreted = True
                await updater.update_status(TaskState.TASK_STATE_WORKING, say(interpretation(classified)))
            plan: ResearchPlan | None = state.get("plan")
            if plan is not None and not planned:
                planned = True
                await updater.update_status(
                    TaskState.TASK_STATE_WORKING, say(plan_summary(plan, classified.language))
                )
            if plan is None or not planned:
                return
            evidence: list[Evidence] = state.get("evidence") or []
            gaps: list[SearchGap] = state.get("gaps") or []
            done = min(state.get("research_step", 0), len(plan.steps))
            for step in range(reported_steps, done):
                await updater.update_status(
                    TaskState.TASK_STATE_WORKING, say(search_update(plan, step, evidence, gaps, classified.language))
                )
            reported_steps = max(reported_steps, done)

        try:
            async with asyncio.timeout(self._settings.request_timeout_seconds):
                state: dict[str, Any] = {}
                async for state in self._graph.astream(graph_input, config, stream_mode="values"):
                    await report_progress(state)
        except (TimeoutError, ClassificationError, ModelUnavailableError, PlanningError) as error:
            logger.warning("Task %s failed: %s", task_id, type(error).__name__)
            await updater.failed(say(text(Text.FAILURE)))
            return
        except Exception:
            logger.exception("Task %s failed with an unexpected error", task_id)
            await updater.failed(say(text(Text.FAILURE)))
            return

        outcome: Outcome | None = state.get("outcome")
        classified: ClassifiedRequest | None = state.get("classification")
        if outcome is None or classified is None:
            logger.error("Task %s ended without an outcome", task_id)
            await updater.failed(say(text(Text.FAILURE)))
            return

        logger.info("Task %s outcome: %s", task_id, outcome.value)
        lang = classified.language
        if outcome is Outcome.IN_SCOPE:
            if not planned:
                logger.error("Task %s ended in scope without a plan", task_id)
                await updater.failed(say(text(Text.FAILURE, lang)))
                return
            evidence = state.get("evidence") or []
            if not evidence:
                logger.warning("Task %s failed: no search kept a source", task_id)
                await updater.failed(say(text(Text.FAILURE, lang)))
                return
            await updater.complete(say(sources_summary(evidence, state.get("gaps") or [], lang)))
        elif outcome is Outcome.NEEDS_CLARIFICATION:
            await updater.requires_input(say(classified.clarifying_question or text(Text.REPHRASE, lang)))
        elif outcome is Outcome.OUT_OF_SCOPE:
            await updater.reject(say(f"{classified.reason}\n\n{text(Text.SCOPE_HINT, lang)}"))
        else:
            await updater.reject(say(text(Text.REPHRASE, lang)))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id or "", context.context_id or "")
        await updater.cancel()
