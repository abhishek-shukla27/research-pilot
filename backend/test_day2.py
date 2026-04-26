"""
test_day2.py
Tests for Day 2 — Searcher Agent + Tavily integration.

Run from backend/ folder:
  python test_day2.py

Make sure your .env has both GROQ_API_KEY and TAVILY_API_KEY set.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from graph.state import ResearchState
from agents.planner import planner_agent
from agents.searcher import searcher_agent
from tools.search_tool import quick_search
from core.logger import get_logger

logger = get_logger("test_day2")


def make_test_state(topic: str) -> ResearchState:
    return {
        "topic": topic,
        "session_id": str(uuid.uuid4()),
        "research_plan": "",
        "sub_questions": [],
        "search_results": [],
        "answered_questions": [],
        "conflicts": [],
        "needs_research": [],
        "critic_approved": False,
        "iteration_count": 0,
        "final_report": "",
        "agent_trace": [],
        "current_agent": "",
        "error": None,
    }


def test_tavily_direct():
    """Test 1 — Tavily API key works and returns results."""
    print("\n" + "="*60)
    print("TEST 1: Tavily API direct call")
    print("="*60)

    results = quick_search("what is LangGraph in AI agents", max_results=2)

    if not results:
        print("❌ No results — check your TAVILY_API_KEY in .env")
        return False

    print(f"✅ Tavily returned {len(results)} results")
    for i, r in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Title   : {r.get('title', 'N/A')[:70]}")
        print(f"    URL     : {r.get('url', 'N/A')[:70]}")
        print(f"    Content : {r.get('content', '')[:120]}...")

    return True


def test_searcher_agent_isolated():
    """Test 2 — Searcher with manually crafted sub-questions (no Planner needed)."""
    print("\n" + "="*60)
    print("TEST 2: Searcher Agent (isolated — no Planner)")
    print("="*60)

    state = make_test_state("Retrieval Augmented Generation")

    # Manually inject sub-questions (simulates Planner output)
    state["sub_questions"] = [
        {
            "id": "sq001",
            "question": "What is retrieval augmented generation and how does it work?",
            "status": "pending",
            "answer": None,
            "sources": [],
            "confidence": 0.0,
        },
        {
            "id": "sq002",
            "question": "What are the main use cases and benefits of RAG in production systems?",
            "status": "pending",
            "answer": None,
            "sources": [],
            "confidence": 0.0,
        },
    ]

    result = searcher_agent(state)

    if result.get("error"):
        print(f"❌ Searcher error: {result['error']}")
        return False

    search_results = result.get("search_results", [])
    updated_questions = result.get("sub_questions", [])

    print(f"✅ Found {len(search_results)} unique relevant results")
    for r in search_results:
        print(f"\n  [{r['relevance_score']:.2f}] {r['title'][:60]}")
        print(f"         {r['url'][:70]}")

    print(f"\n✅ Sub-question status updates:")
    for sq in updated_questions:
        print(f"  [{sq['id']}] status={sq['status']} | sources={len(sq['sources'])}")

    print(f"\n✅ Agent trace:")
    trace = result.get("agent_trace", [])
    if trace:
        last = trace[-1]
        print(f"  Agent  : {last['agent']}")
        print(f"  Action : {last['action']}")
        print(f"  Output : {last['output'][:200]}")

    return True


def test_planner_then_searcher():
    """Test 3 — Full Planner → Searcher pipeline."""
    print("\n" + "="*60)
    print("TEST 3: Planner → Searcher (full 2-agent pipeline)")
    print("="*60)

    topic = "How does vector similarity search work in AI applications?"
    state = make_test_state(topic)

    # Step 1: Planner
    print(f"\n🧠 Running Planner for: '{topic}'")
    state = planner_agent(state)
    print(f"✅ Planner created {len(state['sub_questions'])} sub-questions")

    # Step 2: Searcher
    print(f"\n🔍 Running Searcher...")
    state = searcher_agent(state)

    if state.get("error"):
        print(f"❌ Searcher error: {state['error']}")
        return False

    search_results = state.get("search_results", [])
    print(f"\n✅ Pipeline result:")
    print(f"   Sub-questions     : {len(state['sub_questions'])}")
    print(f"   Search results    : {len(search_results)}")
    print(f"   Agent trace steps : {len(state['agent_trace'])}")

    print(f"\n📋 All agent trace steps:")
    for step in state["agent_trace"]:
        print(f"  [{step['agent']}] {step['action']} @ {step['timestamp'][:19]}")

    print(f"\n🏆 Top 3 search results:")
    for r in search_results[:3]:
        print(f"  [{r['relevance_score']:.2f}] {r['title'][:70]}")

    return True


def test_research_loop():
    """
    Test 4 — Simulates the Critic triggering a re-search loop.
    The Searcher should only re-search flagged question IDs.
    """
    print("\n" + "="*60)
    print("TEST 4: Re-search loop (Critic → Searcher)")
    print("="*60)

    state = make_test_state("AI agents in production")
    state["sub_questions"] = [
        {"id": "sq001", "question": "What are AI agents?",
         "status": "answered", "answer": "Some answer", "sources": ["http://a.com"], "confidence": 0.8},
        {"id": "sq002", "question": "What frameworks exist for building AI agents?",
         "status": "conflicted", "answer": None, "sources": [], "confidence": 0.2},
    ]
    state["search_results"] = []
    state["needs_research"] = ["sq002"]  # Critic flagged only sq002

    print("  Pre-state: sq001=answered, sq002=conflicted")
    print("  Critic flagged: ['sq002'] for re-search")

    result = searcher_agent(state)

    updated_qs = result.get("sub_questions", [])
    sq001_status = next(q["status"] for q in updated_qs if q["id"] == "sq001")
    sq002_status = next(q["status"] for q in updated_qs if q["id"] == "sq002")

    print(f"\n✅ Post-search statuses:")
    print(f"   sq001 (should stay 'answered') : {sq001_status}")
    print(f"   sq002 (should be 'searching')  : {sq002_status}")
    print(f"   needs_research cleared         : {result.get('needs_research') == []}")

    return sq001_status == "answered" and sq002_status == "searching"


if __name__ == "__main__":
    print("\n🔍 ResearchPilot AI — Day 2 Tests")

    # Key checks
    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    if not groq_key:
        print("❌ GROQ_API_KEY missing")
        sys.exit(1)
    if not tavily_key:
        print("❌ TAVILY_API_KEY missing — get free key at https://app.tavily.com")
        sys.exit(1)

    print(f"✅ GROQ_API_KEY   : {groq_key[:8]}...")
    print(f"✅ TAVILY_API_KEY : {tavily_key[:8]}...")

    results = []
    results.append(("Tavily direct call", test_tavily_direct()))
    results.append(("Searcher isolated", test_searcher_agent_isolated()))
    results.append(("Planner → Searcher", test_planner_then_searcher()))
    results.append(("Re-search loop", test_research_loop()))

    print("\n" + "="*60)
    print("RESULTS:")
    all_passed = True
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All Day 2 tests passed!")
        print("Next steps:")
        print("  1. uvicorn main:app --reload")
        print("  2. Open http://localhost:8000/docs")
        print("  3. POST /api/v1/research with a topic")
        print("  4. You should see Planner + Searcher both running")
    else:
        print("\n⚠️  Some tests failed — check logs above")

    print("="*60)