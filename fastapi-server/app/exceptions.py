"""HTTP-aware translation of QuantHub errors.

Client-visible error bodies never carry a stack trace, a filesystem path, or an
exception message taken from an unexpected failure: both can disclose source
layout, SQL, tokens in URLs, or internal state.  The full traceback is logged
server-side with a short correlation id that is echoed to the client, so an
operator can match a user report to a log entry without leaking internals.
"""

from __future__ import annotations

import logging
import uuid
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

logger = logging.getLogger("quanthub.exceptions")

_STATUS_MAP: dict[type[QuantumLabError], int] = {
    InvalidGateError: 400,
    QubitIndexError: 400,
    SimulationError: 422,
    NormalizationError: 422,
}

_GENERIC_MESSAGE = "An internal error occurred. Quote the reference when reporting it."


def _status_for(exc: QuantumLabError) -> int:
    for cls, code in _STATUS_MAP.items():
        if isinstance(exc, cls):
            return code
    return 500


def _error_payload(
    code: str,
    message: str,
    *,
    reference: str | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if reference is not None:
        error["reference"] = reference
    return {"data": None, "error": error}


async def quantumlab_exception_handler(
    request: Request, exc: QuantumLabError
) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for(exc),
        content=_error_payload(type(exc).__name__, str(exc)),
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    reference = uuid.uuid4().hex[:12]
    logger.exception(
        "Unhandled error handling %s %s [reference=%s]",
        request.method,
        request.url.path,
        reference,
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload("InternalError", _GENERIC_MESSAGE, reference=reference),
    )
