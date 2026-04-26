"""
agents/planner.py
The Planner Agent is the first node in the LangGraph pipeline.

It takes the user's topic and:
1. Creates a high-level research plan
2. Decomposes the topic into 3-5 focused sub-questions
3. Returns an updated ResearchState

This is purely an LLM call — no tools needed at this stage.
"""
import json
import uuid
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ResearchState, SubQuestion, AgentStep
from core.llm import get_llm
from core.logger import get_logger

logger = get_logger("planner")


PLANNER_SYSTEM_PROMPT = """You are a research planning expert. Your job is to analyze a research topic and create a structured research plan.

Given a topic, you will:
1. Write a brief research strategy (2-3 sentences)
2. Break the topic into exactly 3-5 focused sub-questions that together would give a comprehensive understanding

Your output MUST be valid JSON in this exact format:
{
  "research_plan": "Brief strategy explaining how to approach this research...",
  "sub_questions": [
    "What is X and how does it work?",
    "What are the main applications/use cases of X?",
    "What are the limitations and challenges of X?",
    "How does X compare to alternatives?",
    "What is the future outlook for X?"
  ]
}

Rules:
- Sub-questions must be specific and answerable through web search
- Each sub-question should cover a DIFFERENT aspect of the topic
- Do NOT repeat similar questions
- Output ONLY the JSON, no markdown, no explanation
"""


def planner_agent(state: ResearchState) -> ResearchState:
    """
    LangGraph node: Planner Agent
    
    Input:  state with `topic` set
    Output: state with `research_plan` and `sub_questions` filled in
    """
    topic = state["topic"]
    session_id = state["session_id"]
    
    logger.info(f"[{session_id}] Planner starting for topic: '{topic}'")
    
    llm = get_llm()
    
    # Build the prompt
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"Create a research plan for this topic: {topic}")
    ]
    
    # Call Groq
    logger.info(f"[{session_id}] Calling Groq LLM for research plan...")
    response = llm.invoke(messages)
    raw_output = response.content.strip()
    
    logger.info(f"[{session_id}] Planner raw response received ({len(raw_output)} chars)")
    
    # Parse JSON response
    try:
        parsed = json.loads(raw_output)
        research_plan = parsed["research_plan"]
        raw_questions = parsed["sub_questions"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[{session_id}] Failed to parse planner JSON: {e}")
        logger.error(f"[{session_id}] Raw output was: {raw_output[:500]}")
        # Fallback: create generic sub-questions
        research_plan = f"Comprehensive research on {topic}"
        raw_questions = [
            f"What is {topic} and how does it work?",
            f"What are the main applications of {topic}?",
            f"What are the limitations of {topic}?",
            f"What is the future of {topic}?",
        ]
    
    # Convert to SubQuestion TypedDicts
    sub_questions: list[SubQuestion] = [
        {
            "id": str(uuid.uuid4())[:8],
            "question": q,
            "status": "pending",
            "answer": None,
            "sources": [],
            "confidence": 0.0,
        }
        for q in raw_questions
    ]
    
    logger.info(f"[{session_id}] Planner created {len(sub_questions)} sub-questions")
    for i, sq in enumerate(sub_questions, 1):
        logger.info(f"[{session_id}]   Q{i}: {sq['question']}")
    
    # Build agent trace step (this gets streamed to frontend)
    trace_step: AgentStep = {
        "agent": "Planner",
        "action": "decompose_topic",
        "input": topic,
        "output": f"Created {len(sub_questions)} sub-questions:\n" + "\n".join(
            f"  {i+1}. {sq['question']}" for i, sq in enumerate(sub_questions)
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Return updated state (LangGraph merges this with existing state)
    return {
        **state,
        "research_plan": research_plan,
        "sub_questions": sub_questions,
        "current_agent": "Planner",
        "agent_trace": [trace_step],  # LangGraph 1.x accumulates automatically
    }