"""LangGraph state shared across the research workflow."""

import operator
from typing import Annotated, TypedDict

from housing_access_agent.domain.enums import Outcome
from housing_access_agent.domain.models import ClassifiedRequest, ResearchPlan


class ResearchState(TypedDict, total=False):
    """State of one request, kept per A2A context by the checkpointer."""

    # Every user message of the task; replies to clarifying questions append.
    user_turns: Annotated[list[str], operator.add]
    clarification_rounds: int
    classification: ClassifiedRequest | None
    outcome: Outcome | None
    plan: ResearchPlan | None
    planner_iterations: int
    # Searches already run for this request; nothing runs them yet.
    searches_used: int
