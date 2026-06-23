"""Streaming ELI15 explanation endpoint (Server-Sent Events).

The endpoint is provider-agnostic: it asks
:func:`app.llm.get_provider` for an :class:`ExplanationProvider`
instance, then splices its token stream into SSE frames.

Wire contract:

* Method+path: ``POST /api/v1/explain``
* Media type:  ``text/event-stream``
* Frames:

  - ``event: token``  ``data: {"text": "..."}``  per token
  - ``event: done``   ``data: {}``               once at the end

This route MUST NOT import any provider-specific SDK -- all
backend-aware code lives behind :mod:`app.llm`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.llm import (
    AuthenticationError,
    ConfigurationError,
    ExplanationProvider,
    ExplanationRequest,
    MissingApiKeyError,
    RateLimitError,
    UpstreamProviderError,
    get_provider,
)
from app.llm.base import ComplexAmplitude as LlmComplexAmplitude
from app.models import ExplainRequest

router = APIRouter(prefix="/api/v1/explain", tags=["explain"])


def _to_llm_request(req: ExplainRequest) -> ExplanationRequest:
    """Translate the wire-level Pydantic body into the provider DTO."""
    return ExplanationRequest(
        gate=req.gate,
        num_qubits=req.num_qubits,
        state_before=[
            LlmComplexAmplitude(a.real, a.imag) for a in req.state_before
        ],
        state_after=[
            LlmComplexAmplitude(a.real, a.imag) for a in req.state_after
        ],
        context=req.context,
        mode=req.mode,
        qubit=req.qubit,
        qubits=req.qubits,
    )


def _error_envelope(code: str, message: str) -> dict[str, object]:
    return {
        "data": None,
        "error": {"code": code, "message": message, "trace": None},
    }


async def _wrap_as_sse(
    provider: ExplanationProvider,
    llm_req: ExplanationRequest,
) -> AsyncGenerator[str, None]:
    """Adapt a provider's token stream into SSE frames.

    Provider exceptions raised after the headers have already been
    flushed are surfaced inline as ``event: error`` frames so the
    client can show a meaningful message instead of a silent hang.
    """
    try:
        async for token in provider.stream_explanation(llm_req):
            if token:
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
    except (
        AuthenticationError,
        RateLimitError,
        UpstreamProviderError,
        MissingApiKeyError,
    ) as exc:
        code = type(exc).__name__
        yield (
            "event: error\n"
            f"data: {json.dumps({'code': code, 'message': str(exc)})}\n\n"
        )
        return
    yield "event: done\ndata: {}\n\n"


@router.post("")
async def explain(req: ExplainRequest) -> StreamingResponse:
    """Stream an ELI15 explanation as Server-Sent Events.

    The endpoint is POST (not GET) because we need a structured request
    body. The response media type is ``text/event-stream`` and the
    client should consume tokens incrementally.

    The active provider is selected via the ``LLM_PROVIDER`` env var:

    * ``gemini`` -- Google ``gemini-2.5-flash`` (requires ``GEMINI_API_KEY``).
    * ``local``  -- offline deterministic templates.

    When ``LLM_PROVIDER`` is unset, the route auto-selects ``gemini``
    if ``GEMINI_API_KEY`` is present, otherwise falls back to ``local``.
    """
    # Resolve provider eagerly so configuration mistakes and missing
    # keys turn into clean HTTP errors BEFORE streaming headers are
    # committed.
    try:
        provider = get_provider()
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail=_error_envelope("LlmConfigurationError", str(exc)),
        ) from exc

    # Validate that the chosen provider can actually run. For Gemini
    # this means we surface a 503 if no API key is configured -- doing
    # it here (before StreamingResponse) keeps the failure path on a
    # proper HTTP status code instead of an in-stream error frame.
    if hasattr(provider, "_api_key") and getattr(provider, "_api_key") in (None, ""):
        raise HTTPException(
            status_code=503,
            detail=_error_envelope(
                "MissingApiKeyError",
                "GEMINI_API_KEY is not set. Either set it, or set "
                "LLM_PROVIDER=local for offline deterministic explanations.",
            ),
        )

    llm_req = _to_llm_request(req)
    return StreamingResponse(
        _wrap_as_sse(provider, llm_req),
        media_type="text/event-stream",
    )
