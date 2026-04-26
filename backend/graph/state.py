"""
graph/state.py
ResearchState — shared state for all agents in the LangGraph pipeline.

LangGraph 1.x requires Annotated fields with reducer functions for lists
so that state merges correctly between nodes instead of overwriting.
"""
from typing import TypedDict, List, Optional, Literal, Annotated
import operator


class SubQuestion(TypedDict):
    id: str
    question: str
    status: Literal["pending", "searching", "answered", "conflicted"]
    answer: Optional[str]
    sources: List[str]
    confidence: float


class SearchResult(TypedDict):
    url: str
    title: str
    content: str
    relevance_score: float


class AgentStep(TypedDict):
    agent: str
    action: str
    input: str
    output: str
    timestamp: str


class ResearchState(TypedDict):
    # --- Input ---
    topic: str
    session_id: str

    # --- Planner output ---
    research_plan: str
    sub_questions: List[SubQuestion]

    # --- Searcher output ---
    search_results: List[SearchResult]

    # --- Reader output ---
    answered_questions: List[SubQuestion]

    # --- Critic output ---
    conflicts: List[str]
    needs_research: List[str]
    critic_approved: bool
    iteration_count: int

    # --- Writer output ---
    final_report: str

    # --- Observability ---
    # Annotated with operator.add so trace steps ACCUMULATE across nodes
    # instead of being overwritten
    agent_trace: Annotated[List[AgentStep], operator.add]
    current_agent: str
    error: Optional[str]