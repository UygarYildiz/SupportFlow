"""FastAPI application factory."""

import logging

from fastapi import FastAPI

from app.api import health
from app.api.errors import register_exception_handlers
from app.api.v1 import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="SupportFlow AI",
        version="0.1.0",
        description="Support operations API with AI-drafted proposals and human approval.",
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
