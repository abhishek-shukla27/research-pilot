"""
agents/searcher.py
Searcher Agent — Day 2

Responsibilities:
  1. Takes sub_questions from the Planner
  2. Calls Tavily search API for each sub-question
  3. Scores each result for relevance using the LLM
  4. Deduplicates URLs across all results
  5. Returns enriched search_results + updates sub_question statuses

Why Tavily over SerpAPI/Google?
  - Built for LLM pipelines (returns clean extracted content, not raw HTML)
  - Free tier: 1000 searches/month
  - Direct Python SDK — no browser automation needed
"""
import json
from datetime import datetime
from typing import List

from tavily import TavilyClient

from graph.state import ResearchState, SearchResult, SubQuestion, AgentStep
from core.config import get_settings
from core.llm import get_llm, get_precise_llm
from core.logger import get_logger
from langchain_core.messages import SystemMessage, HumanMessage

logger = get_logger("searcher")

# How many web results to fetch per sub-question
RESULTS_PER_QUESTION = 3

# Relevance score threshold — results below this are dropped
MIN_RELEVANCE_SCORE = 0.4

# ─────────────────────────────────────────────
# Relevance Scoring Prompt
# ─────────────────────────────────────────────
RELEVANCE_PROMPT = """You are a research quality evaluator. Given a research question and a web search result, score how relevant and useful this result is for answering the question.

Output ONLY a JSON object like this:
{
  "score": 0.85,
  "reason": "Directly addresses the question with technical depth"
}

Scoring guide:
  0.9 - 1.0 : Perfect match, directly and completely answers the question
  0.7 - 0.9 : Highly relevant, covers most of the question
  0.5 - 0.7 : Partially relevant, some useful information
  0.3 - 0.5 : Tangentially related, limited usefulness
  0.0 - 0.3 : Not relevant

Output ONLY the JSON, no explanation, no markdown."""


def _score_result(question: str, result_title: str, result_content: str, session_id: str) -> float:
    """
    Uses the LLM to score how relevant a search result is for a given question.
    Returns a float between 0.0 and 1.0.
    Falls back to 0.5 if LLM fails.
    """
    llm = get_precise_llm()

    content_preview = result_content[:600]  # Keep tokens low

    messages = [
        SystemMessage(content=RELEVANCE_PROMPT),
        HumanMessage(content=f"""Research question: {question}

Search result title: {result_title}
Search result content: {content_preview}

Score this result's relevance.""")
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.5))
        reason = parsed.get("reason", "")
        logger.info(f"[{session_id}] Relevance score: {score:.2f} — {reason[:60]}")
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    except Exception as e:
        logger.warning(f"[{session_id}] Relevance scoring failed: {e}. Using default 0.5")
        return 0.5


def _search_for_question(
    client: TavilyClient,
    question: str,
    session_id: str,
) -> List[SearchResult]:
    """
    Calls Tavily for a single sub-question.
    Returns a list of SearchResult dicts with relevance scores.
    """
    logger.info(f"[{session_id}] Searching: '{question[:80]}'")

    try:
        response = client.search(
            query=question,
            search_depth="advanced",   # More thorough than "basic"
            max_results=RESULTS_PER_QUESTION,
            include_answer=False,       # We want raw results, not Tavily's summary
            include_raw_content=False,  # Clean extracted text is enough
        )
    except Exception as e:
        logger.error(f"[{session_id}] Tavily API error: {e}")
        return []

    results: List[SearchResult] = []
    raw_results = response.get("results", [])
    logger.info(f"[{session_id}] Tavily returned {len(raw_results)} results")

    for item in raw_results:
        url = item.get("url", "")
        title = item.get("title", "No title")
        content = item.get("content", "")

        if not content or not url:
            continue

        # LLM-based relevance scoring
        score = _score_result(question, title, content, session_id)

        if score < MIN_RELEVANCE_SCORE:
            logger.info(f"[{session_id}] Dropping low-relevance result (score={score:.2f}): {url}")
            continue

        results.append({
            "url": url,
            "title": title,
            "content": content,
            "relevance_score": score,
        })

    # Sort best results first
    results.sort(key=lambda r: r["relevance_score"], reverse=True)
    return results


def _deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """
    Removes duplicate URLs. Keeps the first occurrence (highest relevance
    since results are sorted before being added).
    """
    seen_urls: set[str] = set()
    unique: List[SearchResult] = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique.append(r)
    return unique


def searcher_agent(state: ResearchState) -> ResearchState:
    """
    LangGraph node: Searcher Agent

    Input:  state with `sub_questions` (from Planner)
            OR `needs_research` list (from Critic, on re-search loops)
    Output: state with `search_results` filled in,
            sub_questions status updated to "searching"
    """
    session_id = state["session_id"]
    sub_questions: List[SubQuestion] = state.get("sub_questions", [])
    needs_research: List[str] = state.get("needs_research", [])  # IDs from Critic

    settings = get_settings()

    if not settings.tavily_api_key:
        logger.error(f"[{session_id}] TAVILY_API_KEY not set!")
        return {
            **state,
            "error": "TAVILY_API_KEY is missing. Add it to your .env file.",
            "current_agent": "Searcher",
        }

    client = TavilyClient(api_key=settings.tavily_api_key)

    # On re-search loops, only re-search flagged questions
    # On first run, search all pending questions
    if needs_research:
        questions_to_search = [
            sq for sq in sub_questions
            if sq["id"] in needs_research
        ]
        logger.info(f"[{session_id}] Re-search mode: {len(questions_to_search)} flagged questions")
    else:
        questions_to_search = [
            sq for sq in sub_questions
            if sq["status"] == "pending"
        ]
        logger.info(f"[{session_id}] First search: {len(questions_to_search)} pending questions")

    if not questions_to_search:
        logger.warning(f"[{session_id}] No questions to search!")
        return {**state, "current_agent": "Searcher"}

    # ── Run search for each sub-question ──
    all_new_results: List[SearchResult] = []
    updated_questions: List[SubQuestion] = []

    for sq in sub_questions:
        # Is this question in our search batch?
        should_search = sq in questions_to_search

        if should_search:
            results = _search_for_question(client, sq["question"], session_id)
            all_new_results.extend(results)

            # Update this sub-question's status and source URLs
            updated_sq = {
                **sq,
                "status": "searching",
                "sources": [r["url"] for r in results],
            }
            logger.info(
                f"[{session_id}] Q[{sq['id']}] got {len(results)} relevant results"
            )
        else:
            updated_sq = sq  # Unchanged

        updated_questions.append(updated_sq)

    # Merge with existing results (important on re-search loops)
    existing_results: List[SearchResult] = state.get("search_results", [])
    merged_results = _deduplicate(existing_results + all_new_results)

    logger.info(
        f"[{session_id}] Search complete — "
        f"{len(all_new_results)} new results, "
        f"{len(merged_results)} total after dedup"
    )

    # ── Build agent trace step ──
    top_results_summary = "\n".join(
        f"  [{r['relevance_score']:.2f}] {r['title'][:60]} — {r['url'][:50]}"
        for r in merged_results[:6]
    )

    trace_step: AgentStep = {
        "agent": "Searcher",
        "action": "web_search",
        "input": f"Searching {len(questions_to_search)} sub-questions via Tavily",
        "output": (
            f"Found {len(merged_results)} unique relevant results.\n"
            f"Top results:\n{top_results_summary}"
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        **state,
        "search_results": merged_results,
        "sub_questions": updated_questions,
        "needs_research": [],          # Clear Critic's flags after re-search
        "current_agent": "Searcher",
        "agent_trace": [trace_step],  # LangGraph 1.x accumulates automatically
    }