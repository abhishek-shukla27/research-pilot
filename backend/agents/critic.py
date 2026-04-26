"""
agents/critic.py — Day 4: Critic Agent

Reviews all answered sub-questions and:
  1. Checks for low-confidence answers (below threshold)
  2. Detects contradictions between answers
  3. Flags questions needing re-search
  4. Approves the pipeline to move to Writer if quality is good

This is the key "agentic" behavior — the pipeline can loop back
to Searcher if Critic finds issues (up to MAX_ITERATIONS times).
"""
import json
from datetime import datetime
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ResearchState, SubQuestion, AgentStep
from core.llm import get_llm
from core.logger import get_logger

logger = get_logger("critic")

# Questions with confidence below this get flagged for re-search
CONFIDENCE_THRESHOLD = 0.5

CRITIC_SYSTEM_PROMPT = """You are a rigorous research quality critic. You review research answers and identify:
1. Contradictions between different answers
2. Answers that are too vague or incomplete
3. Claims that seem inconsistent with other answers

You will be given a list of research questions and their answers.

Output ONLY a JSON object in this format:
{
  "approved": true or false,
  "conflicts": [
    "Answer to Q1 says X but Answer to Q3 says Y — contradiction detected",
    "Answer to Q2 is too vague to be useful"
  ],
  "needs_research": ["id_of_question1", "id_of_question2"],
  "overall_quality": 0.85,
  "critique": "Brief overall assessment of research quality"
}

Rules:
- approved = true if overall quality >= 0.7 AND no major conflicts
- needs_research = list of question IDs that need better answers
- conflicts = human-readable descriptions of any contradictions found
- If approved = true, needs_research should be empty
- Output ONLY the JSON, no markdown, no explanation
"""


def _check_low_confidence(sub_questions: List[SubQuestion]) -> List[str]:
    """Flag question IDs where confidence is below threshold."""
    flagged = []
    for sq in sub_questions:
        if sq.get("confidence", 0.0) < CONFIDENCE_THRESHOLD:
            flagged.append(sq["id"])
            logger.info(f"Low confidence: Q[{sq['id']}] = {sq.get('confidence', 0):.2f}")
    return flagged


def _run_llm_critique(sub_questions: List[SubQuestion], session_id: str) -> dict:
    """Use LLM to detect contradictions and assess overall quality."""
    # Build Q&A summary for LLM
    qa_summary = ""
    for i, sq in enumerate(sub_questions, 1):
        qa_summary += f"\nQ{i} [ID: {sq['id']}]: {sq['question']}\n"
        qa_summary += f"Answer: {sq.get('answer', 'No answer')[:400]}\n"
        qa_summary += f"Confidence: {sq.get('confidence', 0):.2f}\n"
        qa_summary += "---"

    llm = get_llm()
    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=f"""Review these research answers for quality and contradictions:

{qa_summary}

Identify any conflicts or low-quality answers that need improvement.""")
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        logger.warning(f"[{session_id}] Critic LLM parse error: {e}")
        # Safe fallback — approve if we can't critique
        return {
            "approved": True,
            "conflicts": [],
            "needs_research": [],
            "overall_quality": 0.7,
            "critique": "Auto-approved (critique parsing failed)"
        }


def critic_agent(state: ResearchState) -> ResearchState:
    """
    LangGraph node: Critic Agent

    Input:  state with answered_questions
    Output: state with conflicts, needs_research, critic_approved updated
    """
    session_id = state["session_id"]
    iteration = state.get("iteration_count", 0) + 1
    answered: List[SubQuestion] = state.get("answered_questions", [])

    logger.info(f"[{session_id}] Critic starting — iteration {iteration}, {len(answered)} answers to review")

    if not answered:
        logger.warning(f"[{session_id}] No answered questions to critique!")
        return {
            **state,
            "conflicts": [],
            "needs_research": [],
            "critic_approved": True,
            "iteration_count": iteration,
            "current_agent": "Critic",
        }

    # Step 1: Flag low-confidence answers
    low_confidence_ids = _check_low_confidence(answered)
    logger.info(f"[{session_id}] Low confidence questions: {low_confidence_ids}")

    # Step 2: LLM contradiction check
    critique_result = _run_llm_critique(answered, session_id)

    llm_conflicts = critique_result.get("conflicts", [])
    llm_needs_research = critique_result.get("needs_research", [])
    llm_approved = critique_result.get("approved", True)
    overall_quality = critique_result.get("overall_quality", 0.7)
    critique_text = critique_result.get("critique", "")

    # Merge: low confidence + LLM flagged
    all_needs_research = list(set(low_confidence_ids + llm_needs_research))

    # Update conflicted question statuses
    updated_questions = []
    for sq in answered:
        if sq["id"] in all_needs_research:
            updated_questions.append({**sq, "status": "conflicted"})
        else:
            updated_questions.append(sq)

    # Final approval decision
    approved = llm_approved and len(all_needs_research) == 0

    logger.info(f"[{session_id}] Critic result: approved={approved}, conflicts={len(llm_conflicts)}, needs_research={all_needs_research}")

    # Build trace
    trace_step: AgentStep = {
        "agent": "Critic",
        "action": "quality_review",
        "input": f"Reviewing {len(answered)} answers (iteration {iteration})",
        "output": (
            f"Quality: {overall_quality:.2f} | Approved: {approved}\n"
            f"Critique: {critique_text}\n"
            f"Conflicts found: {len(llm_conflicts)}\n"
            f"Questions needing re-search: {all_needs_research}\n"
            + ("\n".join(f"  ⚠ {c}" for c in llm_conflicts) if llm_conflicts else "  ✓ No conflicts detected")
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        **state,
        "conflicts": llm_conflicts,
        "needs_research": all_needs_research,
        "critic_approved": approved,
        "iteration_count": iteration,
        "sub_questions": updated_questions,
        "answered_questions": updated_questions,
        "current_agent": "Critic",
        "agent_trace": [trace_step],
    }