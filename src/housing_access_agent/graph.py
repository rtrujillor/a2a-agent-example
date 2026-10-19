"""Composition root for the LangGraph research workflow."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from housing_access_agent.domain.enums import Outcome
from housing_access_agent.state import ResearchState
from housing_access_agent.workflow.classifier import ClassifierNode
from housing_access_agent.workflow.planner import PlannerNode

CLASSIFY = "classify"
PLAN = "plan"


def route_after_classify(state: ResearchState) -> str:
    """Only an in-scope request is planned."""
    return PLAN if state.get("outcome") is Outcome.IN_SCOPE else END


def build_graph(
    classify: ClassifierNode, plan: PlannerNode, checkpointer: BaseCheckpointSaver
) -> CompiledStateGraph:
    """Compose the workflow. Classification and planning exist so far."""
    builder = StateGraph(ResearchState)
    builder.add_node(CLASSIFY, classify)
    builder.add_node(PLAN, plan)
    builder.add_edge(START, CLASSIFY)
    builder.add_conditional_edges(CLASSIFY, route_after_classify, [PLAN, END])
    builder.add_edge(PLAN, END)
    return builder.compile(checkpointer=checkpointer)
