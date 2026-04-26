"""
main.py - FastAPI entry point for ResearchPilot AI
Run: python -m uvicorn main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.logger import get_logger
from core.config import get_settings

logger = get_logger("main")
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResearchPilot AI",
        description="Autonomous multi-agent research assistant powered by LangGraph + Groq",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000","https://research-pilot-olive.vercel.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info("=" * 50)
        logger.info("ResearchPilot AI starting up")
        logger.info(f"Model  : {settings.model_name}")
        logger.info(f"Env    : {settings.app_env}")
        logger.info(f"Docs   : http://localhost:8000/docs")
        logger.info("=" * 50)
        # NOTE: Pipeline loads lazily on first request (not at startup)
        # This prevents startup failures from crashing the server

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)