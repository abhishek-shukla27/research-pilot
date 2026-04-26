"""
agents/writer.py — Day 5: Writer Agent

Takes all answered sub-questions and synthesizes a professional
markdown research report with:
  - Executive summary
  - Detailed findings per sub-question
  - Source citations
  - Confidence indicators
  - Conclusion
"""
import json
from datetime import datetime
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ResearchState, SubQuestion, AgentStep
from core.llm import get_creative_llm
from core.logger import get_logger

logger = get_logger("writer")

WRITER_SYSTEM_PROMPT = """You are an expert research writer. You synthesize research findings into clear, professional markdown reports.

Given a research topic and answered sub-questions, write a comprehensive research report.

Format the report in clean markdown with these sections:
1. # Title (topic as title)
2. ## Executive Summary (2-3 sentence overview)
3. ## Key Findings (bullet points of most important findings)
4. ## Detailed Analysis (one ## subsection per sub-question with full answer)
5. ## Sources (numbered list of all unique URLs cited)
6. ## Conclusion (2-3 sentences wrapping up)

Rules:
- Write in clear, professional English
- Each finding should reference its confidence level with an emoji:
    🟢 High confidence (>0.8), 🟡 Medium (0.5-0.8), 🔴 Low (<0.5)
- Cite sources inline as [Source N]
- Be comprehensive but concise
- Output ONLY the markdown report, no JSON wrapping
"""


def _collect_sources(sub_questions: List[SubQuestion]) -> List[str]:
    """Collect all unique source URLs from answered questions."""
    seen = set()
    sources = []
    for sq in sub_questions:
        for url in sq.get("sources", []):
            if url not in seen:
                seen.add(url)
                sources.append(url)
    return sources


def _build_qa_context(sub_questions: List[SubQuestion]) -> str:
    """Build a structured Q&A context string for the Writer LLM."""
    parts = []
    for i, sq in enumerate(sub_questions, 1):
        confidence = sq.get("confidence", 0.0)
        if confidence >= 0.8:
            conf_label = "HIGH"
        elif confidence >= 0.5:
            conf_label = "MEDIUM"
        else:
            conf_label = "LOW"

        sources_str = ", ".join(sq.get("sources", [])) or "No sources"
        parts.append(
            f"Sub-question {i}: {sq['question']}\n"
            f"Answer: {sq.get('answer', 'Not answered')}\n"
            f"Confidence: {conf_label} ({confidence:.2f})\n"
            f"Sources: {sources_str}"
        )
    return "\n\n---\n\n".join(parts)


def writer_agent(state: ResearchState) -> ResearchState:
    """
    LangGraph node: Writer Agent

    Input:  state with answered_questions, topic, research_plan
    Output: state with final_report filled in
    """
    session_id = state["session_id"]
    topic = state.get("topic", "Research Topic")
    research_plan = state.get("research_plan", "")
    answered: List[SubQuestion] = state.get("answered_questions", [])
    conflicts = state.get("conflicts", [])
    iteration_count = state.get("iteration_count", 1)

    logger.info(f"[{session_id}] Writer starting — {len(answered)} answered questions, {iteration_count} iterations")

    # Collect all sources
    all_sources = _collect_sources(answered)

    # Build Q&A context for LLM
    qa_context = _build_qa_context(answered)

    # Conflicts section if any
    conflicts_note = ""
    if conflicts:
        conflicts_note = f"\n\nNOTE — The following conflicts were detected during research:\n"
        conflicts_note += "\n".join(f"- {c}" for c in conflicts)

    llm = get_creative_llm()
    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Research Topic: {topic}

Research Strategy: {research_plan}

Answered Sub-questions:
{qa_context}
{conflicts_note}

All Sources (for citations):
{chr(10).join(f'{i+1}. {url}' for i, url in enumerate(all_sources))}

Write a comprehensive research report on this topic.""")
    ]

    try:
        logger.info(f"[{session_id}] Writer calling LLM...")
        response = llm.invoke(messages)
        final_report = response.content.strip()
        logger.info(f"[{session_id}] Report generated — {len(final_report)} chars")
    except Exception as e:
        logger.error(f"[{session_id}] Writer LLM error: {e}")
        # Fallback: build report manually without LLM
        final_report = f"# Research Report: {topic}\n\n"
        final_report += f"**Research Plan:** {research_plan}\n\n"
        final_report += "## Findings\n\n"
        for sq in answered:
            conf = sq.get("confidence", 0)
            emoji = "🟢" if conf >= 0.8 else "🟡" if conf >= 0.5 else "🔴"
            final_report += f"### {sq['question']}\n\n"
            final_report += f"{emoji} **Confidence: {conf:.0%}**\n\n"
            final_report += f"{sq.get('answer', 'No answer available.')}\n\n"
        if all_sources:
            final_report += "## Sources\n\n"
            for i, url in enumerate(all_sources, 1):
                final_report += f"{i}. {url}\n"

    # Build trace
    trace_step: AgentStep = {
        "agent": "Writer",
        "action": "synthesize_report",
        "input": f"Synthesizing {len(answered)} answers into final report",
        "output": f"Report generated — {len(final_report)} characters, {len(all_sources)} sources cited",
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        **state,
        "final_report": final_report,
        "current_agent": "Writer",
        "agent_trace": [trace_step],
    }