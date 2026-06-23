"""HTTP-aware translation of QuantumLab errors."""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from quantumlab.exceptions import (
    InvalidGateError,
    NormalizationError,
    QuantumLabError,
    QubitIndexError,
    SimulationError,
)


_STATUS_MAP: dict[type[QuantumLabError], int] = {
    InvalidGateError: 400,
    QubitIndexError: 400,
    SimulationError: 422,
    NormalizationError: 422,
}


def _status_for(exc: QuantumLabError) -> int:
    for cls, code in _STATUS_MAP.items():
        if isinstance(exc, cls):
            return code
    return 500


def _error_payload(exc: BaseException, *, include_trace: bool) -> dict[str, Any]:
    return {
        "data": None,
        "error": {
            "code": type(exc).__name__,
            "message": str(exc),
            "trace": (
                "".join(traceback.format_exception(exc)) if include_trace else None
            ),
        },
    }


async def quantumlab_exception_handler(
    request: Request, exc: QuantumLabError
) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for(exc),
        content=_error_payload(exc, include_trace=False),
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_payload(exc, include_trace=True),
    )
