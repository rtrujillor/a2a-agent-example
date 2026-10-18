"""Composition root for the LangGraph research workflow."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from housing_access_agent.state import ResearchState
from housing_access_agent.workflow.classifier import ClassifierNode

CLASSIFY = "classify"


def build_graph(classify: ClassifierNode, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Compose the workflow. Only classification exists so far."""
    builder = StateGraph(ResearchState)
    builder.add_node(CLASSIFY, classify)
    builder.add_edge(START, CLASSIFY)
    builder.add_edge(CLASSIFY, END)
    return builder.compile(checkpointer=checkpointer)
