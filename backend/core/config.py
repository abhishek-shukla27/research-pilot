"""
core/config.py
Loads all environment variables and provides a single config object.
"""
import os
from dotenv import load_dotenv

# Load .env BEFORE anything else — must be at module level, before class definition
load_dotenv(override=True)


class Settings:
    def __init__(self):
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
        self.pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "researchpilot")
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.model_name: str = "llama-3.3-70b-versatile"


# Singleton — created once, reused everywhere
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings