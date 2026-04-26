
from typing import List, Optional
from tavily import TavilyClient

from core.config import get_settings
from core.logger import get_logger

logger = get_logger("search_tool")


def quick_search(query: str, max_results: int = 3) -> List[dict]:
    """
    Minimal search helper — returns raw Tavily results.
    Used by agents that need a fast single-query search.

    Returns list of dicts with keys: url, title, content
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY not configured")
        return []

    client = TavilyClient(api_key=settings.tavily_api_key)

    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
        )
        return response.get("results", [])
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []


def deep_search(query: str, max_results: int = 5) -> List[dict]:
    """
    Advanced search — used when the Critic flags a question as needing more evidence.
    Uses Tavily's 'advanced' depth which fetches and parses full page content.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    client = TavilyClient(api_key=settings.tavily_api_key)

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
        )
        return response.get("results", [])
    except Exception as e:
        logger.error(f"Tavily deep search error: {e}")
        return []