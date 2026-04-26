"""
agents/reader.py — Day 3: Reader Agent

Takes search_results (URLs + content from Searcher) and for each sub_question:
  1. Finds the most relevant content chunks from search results
  2. Uses LLM to answer the sub-question from those chunks
  3. Assigns a confidence score to the answer
  4. Updates sub_question status to "answered"

NOTE: We use simple in-memory chunking here (no Pinecone needed for MVP).
Pinecone can be added later for persistence across sessions.
"""
import json
from datetime import datetime
from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ResearchState, SubQuestion, AgentStep
from core.llm import get_llm
from core.logger import get_logger

logger = get_logger("reader")

CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 100     # overlap between chunks
TOP_K_CHUNKS = 4        # how many chunks to send to LLM per question


READER_SYSTEM_PROMPT = """You are a precise research analyst. You are given:
1. A research sub-question
2. Relevant content chunks from web sources

Your job is to answer the sub-question using ONLY the provided content.

Output ONLY a JSON object in this format:
{
  "answer": "Your detailed answer here based on the content...",
  "confidence": 0.85,
  "key_points": ["point 1", "point 2", "point 3"]
}

Confidence scoring guide:
  0.9 - 1.0 : Content directly and completely answers the question
  0.7 - 0.9 : Content mostly answers the question
  0.5 - 0.7 : Content partially answers the question
  0.3 - 0.5 : Content has limited relevant information
  0.0 - 0.3 : Content does not answer the question

Rules:
- Base your answer ONLY on the provided content chunks
- If content is insufficient, say so and give low confidence
- Be specific and cite information from the chunks
- Output ONLY the JSON, no markdown, no explanation
"""


def _chunk_content(content: str, url: str) -> List[dict]:
    """Split content into overlapping chunks with source tracking."""
    chunks = []
    start = 0
    while start < len(content):
        end = start + CHUNK_SIZE
        chunk_text = content[start:end]
        chunks.append({"text": chunk_text, "url": url})
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _find_relevant_chunks(question: str, all_chunks: List[dict], top_k: int) -> List[dict]:
    """
    Simple keyword-based chunk retrieval.
    Scores chunks by how many question words appear in them.
    (No vector DB needed — works great for this scale)
    """
    question_words = set(question.lower().split())
    # Remove common stop words
    stop_words = {"what", "how", "why", "when", "where", "is", "are", "the",
                  "a", "an", "of", "in", "and", "or", "to", "does", "do", "did"}
    question_words -= stop_words

    scored = []
    for chunk in all_chunks:
        chunk_lower = chunk["text"].lower()
        score = sum(1 for word in question_words if word in chunk_lower)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def _answer_question(question: str, chunks: List[dict], session_id: str) -> dict:
    """Use LLM to answer a sub-question from the given content chunks."""
    if not chunks:
        return {
            "answer": "Insufficient information found in search results.",
            "confidence": 0.1,
            "key_points": []
        }

    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}: {chunk['url']}]\n{chunk['text']}")
    context = "\n\n---\n\n".join(context_parts)

    llm = get_llm()
    messages = [
        SystemMessage(content=READER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Sub-question: {question}

Content chunks:
{context}

Answer the sub-question based on this content.""")
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        return parsed
    except Exception as e:
        logger.warning(f"[{session_id}] Reader LLM parse error: {e}")
        return {
            "answer": "Could not parse answer from search results.",
            "confidence": 0.2,
            "key_points": []
        }


def reader_agent(state: ResearchState) -> ResearchState:
    """
    LangGraph node: Reader Agent

    Input:  state with search_results and sub_questions
    Output: state with answered_questions filled in
    """
    session_id = state["session_id"]
    sub_questions: List[SubQuestion] = state.get("sub_questions", [])
    search_results = state.get("search_results", [])

    logger.info(f"[{session_id}] Reader starting — {len(search_results)} sources, {len(sub_questions)} questions")

    if not search_results:
        logger.warning(f"[{session_id}] No search results to read!")
        return {
            **state,
            "answered_questions": sub_questions,
            "current_agent": "Reader",
        }

    # Step 1: Chunk all search result content
    all_chunks = []
    for result in search_results:
        chunks = _chunk_content(result["content"], result["url"])
        all_chunks.extend(chunks)

    logger.info(f"[{session_id}] Created {len(all_chunks)} chunks from {len(search_results)} sources")

    # Step 2: Answer each sub-question
    answered: List[SubQuestion] = []
    for sq in sub_questions:
        logger.info(f"[{session_id}] Answering: {sq['question'][:60]}...")

        # Find relevant chunks for this question
        relevant_chunks = _find_relevant_chunks(sq["question"], all_chunks, TOP_K_CHUNKS)

        # Get LLM answer
        result = _answer_question(sq["question"], relevant_chunks, session_id)

        answer_text = result.get("answer", "")
        confidence = float(result.get("confidence", 0.5))

        logger.info(f"[{session_id}] Q[{sq['id']}] confidence={confidence:.2f}")

        answered.append({
            **sq,
            "answer": answer_text,
            "confidence": confidence,
            "status": "answered",
        })

    # Build trace step
    avg_confidence = sum(q["confidence"] for q in answered) / len(answered) if answered else 0
    trace_step: AgentStep = {
        "agent": "Reader",
        "action": "rag_answer",
        "input": f"Answering {len(sub_questions)} questions from {len(all_chunks)} chunks",
        "output": (
            f"Answered {len(answered)} sub-questions.\n"
            f"Avg confidence: {avg_confidence:.2f}\n"
            + "\n".join(
                f"  Q[{q['id']}] conf={q['confidence']:.2f}: {q['answer'][:80]}..."
                for q in answered
            )
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        **state,
        "answered_questions": answered,
        "sub_questions": answered,   # Keep sub_questions in sync
        "current_agent": "Reader",
        "agent_trace": [trace_step],
    }