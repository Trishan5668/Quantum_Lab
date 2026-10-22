"""FastAPI entrypoint for the QuantHub API.

QuantHub is the product name; the ``quantumlab`` Python distribution keeps its
import path so existing clients, saved artifacts and deployments continue to
work.
"""

from __future__ import annotations

import logging
import os

import quantumlab
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from quantumlab.exceptions import QuantumLabError

from app.exceptions import (
    quantumlab_exception_handler,
    unexpected_exception_handler,
)
from app.models import HealthOut, envelope
from app.quanthub.config import configuration_summary, validate_configuration
from app.quanthub.db import init_db
from app.quanthub.errors import HubError, hub_error_handler
from app.quanthub.router import router as quanthub_router
from app.routes.ai import router as ai_router
from app.routes.circuit import router as circuit_router
from app.routes.editor import router as editor_router
from app.routes.explain import router as explain_router
from app.routes.research import router as research_router
from app.routes.v2 import router as v2_router
from app.routes.visualize import router as visualize_router

logger = logging.getLogger("quanthub.startup")

SERVER_VERSION = "2.0.0"

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "app://quantumlab",
)


def cors_origins_from_env() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or list(DEFAULT_CORS_ORIGINS)


def create_app() -> FastAPI:
    # Fail fast and loudly on an unsafe or ambiguous deployment configuration.
    # ``ConfigError`` carries an actionable message and never includes secrets.
    validate_configuration()
    logger.info("QuantHub identity configuration: %s", configuration_summary())

    app = FastAPI(
        title="QuantHub API",
        description=(
            "QuantHub API: project hosting, file management, experiment "
            "execution and the quantum-simulator-core engine. The historical "
            "/api/v1 and /api/v2 simulator routes are unchanged."
        ),
        version=SERVER_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_from_env(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(circuit_router)
    app.include_router(visualize_router)
    app.include_router(explain_router)
    app.include_router(ai_router)
    app.include_router(v2_router)
    app.include_router(editor_router)
    app.include_router(research_router)
    app.include_router(quanthub_router)

    init_db()

    app.add_exception_handler(QuantumLabError, quantumlab_exception_handler)
    app.add_exception_handler(HubError, hub_error_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

    @app.on_event("startup")
    async def _startup() -> None:
        init_db()

    @app.get("/api/v1/health")
    async def health() -> dict[str, object]:
        body = HealthOut(
            status="ok",
            version=SERVER_VERSION,
            core_version=quantumlab.__version__,
        )
        return envelope(body.model_dump())

    return app


app = create_app()
