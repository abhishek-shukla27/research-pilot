"""
graph/pipeline.py - LangGraph 0.1.9 compatible
Fix: versions_seen defaultdict patch for __start__ KeyError
"""
from collections import defaultdict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import empty_checkpoint

from graph.state import ResearchState
from agents.planner import planner_agent
from agents.searcher import searcher_agent
from agents.reader import reader_agent
from agents.critic import critic_agent
from agents.writer import writer_agent
from core.logger import get_logger

logger = get_logger("pipeline")

MAX_ITERATIONS = 3


def route_after_critic(state: ResearchState) -> str:
    if (state.get("critic_approved", False)
            or not state.get("needs_research", [])
            or state.get("iteration_count", 0) >= MAX_ITERATIONS):
        return "writer"
    return "searcher"


def route_after_writer(state: ResearchState) -> str:
    return END


class PatchedMemorySaver(MemorySaver):
    """
    Patch for LangGraph 0.1.9 bug:
    empty_checkpoint() returns versions_seen as a plain dict.
    _prepare_next_tasks does checkpoint["versions_seen"][name] — KeyError: '__start__'
    Fix: override get() to always return a defaultdict for versions_seen.
    """
    def get_tuple(self, config):
        result = super().get_tuple(config)
        if result is None:
            return result
        checkpoint = result.checkpoint
        if not isinstance(checkpoint.get("versions_seen"), defaultdict):
            checkpoint["versions_seen"] = defaultdict(
                dict, checkpoint.get("versions_seen", {})
            )
        return result

    def get(self, config):
        checkpoint = super().get(config)
        if checkpoint is None:
            return checkpoint
        if not isinstance(checkpoint.get("versions_seen"), defaultdict):
            checkpoint["versions_seen"] = defaultdict(
                dict, checkpoint.get("versions_seen", {})
            )
        return checkpoint


def build_pipeline():
    builder = StateGraph(ResearchState)

    builder.add_node("planner",  planner_agent)
    builder.add_node("searcher", searcher_agent)
    builder.add_node("reader",   reader_agent)
    builder.add_node("critic",   critic_agent)
    builder.add_node("writer",   writer_agent)

    builder.set_entry_point("planner")

    builder.add_edge("planner",  "searcher")
    builder.add_edge("searcher", "reader")
    builder.add_edge("reader",   "critic")

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {"writer": "writer", "searcher": "searcher"}
    )

    builder.add_conditional_edges(
        "writer",
        route_after_writer,
        {END: END}
    )

    checkpointer = PatchedMemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Pipeline compiled successfully")
    return graph


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline