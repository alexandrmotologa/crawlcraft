"""FastAPI application factory, CORS configuration, and static dashboard mounting."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from crawlcraft import __version__
from crawlcraft.server.routes import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for setup and teardown."""
    yield
    # Any teardown logic can be placed here


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    app = FastAPI(
        title="CrawlCraft Engine",
        description="High-throughput asynchronous web crawler and semantic markdown synthesizer for LLMs and RAG pipelines.",
        version=__version__,
        lifespan=lifespan,
    )

    # Enable CORS for frontend dashboard and external clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    @app.get("/v1/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": __version__,
            "engine": "Selectolax C-Modest + HTTPX HTTP/2",
            "playwright_enabled": True,
        }

    # If web studio has been built, serve its static assets
    web_dist_path = Path(__file__).parent.parent.parent / "web" / "dist"
    if web_dist_path.exists() and web_dist_path.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dist_path), html=True), name="web_dist")

    return app


app = create_app()
