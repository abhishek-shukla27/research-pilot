"""
core/llm.py
Single place to create/configure the LLM. Swap models here without touching agents.

lru_cache doesn't work well with float args, so we use named functions per use-case.
"""
from functools import lru_cache
from langchain_groq import ChatGroq
from core.config import get_settings


def _make_llm(temperature: float) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.model_name,
        temperature=temperature,
        max_tokens=4096,
    )


@lru_cache()
def get_llm() -> ChatGroq:
    """Default LLM — low temperature for factual/structured tasks."""
    return _make_llm(temperature=0.1)


@lru_cache()
def get_precise_llm() -> ChatGroq:
    """Zero temperature — used for scoring, classification, JSON extraction."""
    return _make_llm(temperature=0.0)


@lru_cache()
def get_creative_llm() -> ChatGroq:
    """Higher temperature — used by Writer agent for fluent prose."""
    return _make_llm(temperature=0.4)