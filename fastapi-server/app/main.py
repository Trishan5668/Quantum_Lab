"""FastAPI entrypoint for the QuantumLab bridge service."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import quantumlab

from app.exceptions import (
    quantumlab_exception_handler,
    unexpected_exception_handler,
)
from app.models import HealthOut, envelope
from app.routes.circuit import router as circuit_router
from app.routes.explain import router as explain_router
from app.routes.v2 import router as v2_router
from app.routes.visualize import router as visualize_router
from quantumlab.exceptions import QuantumLabError


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
    app = FastAPI(
        title="QuantumLab API",
        description=(
            "JSON-over-HTTP bridge between the QuantumLab desktop client "
            "and the quantum-simulator-core Python engine."
        ),
        version=SERVER_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_from_env(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(circuit_router)
    app.include_router(visualize_router)
    app.include_router(explain_router)
    app.include_router(v2_router)

    app.add_exception_handler(QuantumLabError, quantumlab_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

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
