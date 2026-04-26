"""
api/routes.py - FastAPI routes for ResearchPilot AI
"""
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.schemas import ResearchRequest, ResearchResponse, HealthResponse
from graph.pipeline import get_pipeline
from graph.state import ResearchState
from core.config import get_settings
from core.logger import get_logger
from langgraph.checkpoint.base import empty_checkpoint
import copy
logger = get_logger("routes")
router = APIRouter()


def _build_initial_state(topic: str) -> dict:
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


def _build_config() -> dict:
    """Build LangGraph invoke config with unique thread_id.
    Required in langgraph 0.1.9 with MemorySaver to avoid KeyError: '__start__'
    """
    return {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": 25,
    }

def _build_config_with_checkpoint(pipeline) -> dict:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25}
    
    # Pre-populate checkpoint with __start__ in versions_seen
    checkpoint = empty_checkpoint()
    # versions_seen needs ALL node names + __start__ pre-seeded
    for key in ["__start__", "planner", "searcher", "reader", "critic", "writer"]:
        checkpoint["versions_seen"][key] = {}
    
    pipeline.checkpointer.put(
        config,
        checkpoint,
        {"source": "input", "step": -1, "writes": None, "parents": {}}
    )
    return config



@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        model=settings.model_name,
        agents=["Planner", "Searcher", "Reader", "Critic", "Writer"],
    )


@router.post("/research")
async def run_research(request: ResearchRequest):
    """Run the full multi-agent research pipeline."""
    logger.info(f"Research request: '{request.topic}'")

    initial_state = _build_initial_state(request.topic)
    pipeline = get_pipeline()
    config = _build_config()

    try:
        final_state = pipeline.invoke(initial_state, config=config)
        logger.info(f"Pipeline completed for topic: '{request.topic}'")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "session_id": final_state.get("session_id"),
        "topic": final_state.get("topic"),
        "research_plan": final_state.get("research_plan", ""),
        "sub_questions": final_state.get("sub_questions", []),
        "final_report": final_state.get("final_report", ""),
        "agent_trace": final_state.get("agent_trace", []),
        "iteration_count": final_state.get("iteration_count", 0),
        "conflicts": final_state.get("conflicts", []),
        "completed_at": datetime.utcnow().isoformat(),
    }


@router.post("/research/stream")
async def stream_research(request: ResearchRequest):
    """Stream agent updates via SSE."""
    initial_state = _build_initial_state(request.topic)
    pipeline = get_pipeline()
    config = _build_config()

    async def event_generator():
        try:
            async for event in pipeline.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    agent_name = node_output.get("current_agent", node_name)
                    trace = node_output.get("agent_trace", [])
                    last_step = trace[-1] if trace else None

                    payload = {
                        "agent": agent_name,
                        "output": last_step["output"] if last_step else "",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    yield {"event": "agent_complete", "data": json.dumps(payload)}

                    if agent_name == "Writer" and node_output.get("final_report"):
                        yield {
                            "event": "done",
                            "data": json.dumps({
                                "final_report": node_output["final_report"],
                                "session_id": node_output.get("session_id", ""),
                            })
                        }
        except Exception as e:
            logger.error(f"Stream error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())