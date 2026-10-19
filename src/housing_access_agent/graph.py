"""Composition root for the LangGraph research workflow."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from housing_access_agent.domain.enums import Outcome
from housing_access_agent.state import ResearchState
from housing_access_agent.workflow.classifier import ClassifierNode
from housing_access_agent.workflow.planner import PlannerNode
from housing_access_agent.workflow.researcher import ResearcherNode, research_done

CLASSIFY = "classify"
PLAN = "plan"
RESEARCH = "research"


def route_after_classify(state: ResearchState) -> str:
    """Only an in-scope request is planned."""
    return PLAN if state.get("outcome") is Outcome.IN_SCOPE else END


def route_after_research(state: ResearchState) -> str:
    """One plan step per pass, so progress streams after each search."""
    return END if research_done(state) else RESEARCH


def build_graph(
    classify: ClassifierNode,
    plan: PlannerNode,
    research: ResearcherNode,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Compose the workflow. Validation and synthesis do not exist yet."""
    builder = StateGraph(ResearchState)
    builder.add_node(CLASSIFY, classify)
    builder.add_node(PLAN, plan)
    builder.add_node(RESEARCH, research)
    builder.add_edge(START, CLASSIFY)
    builder.add_conditional_edges(CLASSIFY, route_after_classify, [PLAN, END])
    builder.add_edge(PLAN, RESEARCH)
    builder.add_conditional_edges(RESEARCH, route_after_research, [RESEARCH, END])
    return builder.compile(checkpointer=checkpointer)
