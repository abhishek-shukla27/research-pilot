"""
api/schemas.py
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "How does retrieval augmented generation work in LLMs?"
            }
        }


class SubQuestionResponse(BaseModel):
    id: str
    question: str
    status: str
    answer: Optional[str] = None
    sources: List[str] = []
    confidence: float = 0.0


class AgentStepResponse(BaseModel):
    agent: str
    action: str
    input: str
    output: str
    timestamp: str


class ResearchResponse(BaseModel):
    session_id: str
    topic: str
    research_plan: str
    sub_questions: List[SubQuestionResponse]
    final_report: str
    agent_trace: List[AgentStepResponse]
    iteration_count: int
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    model: str
    agents: List[str]