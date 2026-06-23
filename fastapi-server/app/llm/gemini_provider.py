"""Google Gemini provider for the ELI15 explanation endpoint.

Uses the official ``google-genai`` SDK and streams tokens through the
async API so the FastAPI route can splice them into Server-Sent Events
as they arrive.

All failure paths raise a typed :mod:`app.llm.base` exception. Silent
fallbacks are forbidden.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any, Final

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.llm.base import (
    AuthenticationError,
    ExplanationProvider,
    ExplanationRequest,
    MissingApiKeyError,
    RateLimitError,
    UpstreamProviderError,
)
from app.llm.prompts import system_prompt_for, user_message_for


DEFAULT_MODEL: Final[str] = "gemini-2.5-flash"
"""Model id used unless overridden via ``QUANTUMLAB_GEMINI_MODEL``."""


def _max_output_tokens(mode: str) -> int:
    if mode == "deep":
        return 600
    if mode == "hint":
        return 220
    return 350


class GeminiProvider(ExplanationProvider):
    """Streams ELI15 tutor responses from Google Gemini."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self._model = model or os.environ.get("QUANTUMLAB_GEMINI_MODEL") or DEFAULT_MODEL
        # ``client_factory`` is an injection seam used by tests so they can
        # substitute a fake genai-style client without monkey-patching the
        # SDK module.
        self._client_factory = client_factory

    def _build_client(self) -> Any:
        if not self._api_key:
            raise MissingApiKeyError(
                "GEMINI_API_KEY is not set. Either set it, or set "
                "LLM_PROVIDER=local for offline deterministic explanations."
            )
        if self._client_factory is not None:
            return self._client_factory(api_key=self._api_key)
        return genai.Client(api_key=self._api_key)

    async def stream_explanation(
        self,
        request: ExplanationRequest,
    ) -> AsyncIterator[str]:
        client = self._build_client()
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt_for(request),
            max_output_tokens=_max_output_tokens(request.mode),
            temperature=0.7,
        )

        try:
            stream = await client.aio.models.generate_content_stream(
                model=self._model,
                contents=user_message_for(request),
                config=config,
            )
        except genai_errors.APIError as exc:
            raise _translate_api_error(exc) from exc

        try:
            async for chunk in stream:
                text = _chunk_text(chunk)
                if text:
                    yield text
        except genai_errors.APIError as exc:
            raise _translate_api_error(exc) from exc


def _chunk_text(chunk: Any) -> str:
    """Extract the textual delta from a streaming response chunk.

    The SDK exposes ``chunk.text`` as a convenience property in recent
    versions. We fall back to walking the candidates structure in case
    a future release changes that surface.
    """
    text = getattr(chunk, "text", None)
    if isinstance(text, str) and text:
        return text
    candidates = getattr(chunk, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text:
                return part_text
    return ""


def _translate_api_error(exc: genai_errors.APIError) -> Exception:
    """Map a google-genai error to our typed hierarchy."""
    status = getattr(exc, "code", None) or getattr(exc, "status", None)
    # ``status`` is sometimes a string like 'UNAUTHENTICATED' on the gRPC
    # path. Normalize both numeric and named status hints.
    numeric: int | None = None
    if isinstance(status, int):
        numeric = status
    elif isinstance(status, str):
        try:
            numeric = int(status)
        except ValueError:
            numeric = None
    message = getattr(exc, "message", None) or str(exc) or repr(exc)

    if numeric in (401, 403):
        return AuthenticationError(
            f"Gemini rejected our credentials (HTTP {numeric}): {message}"
        )
    if numeric == 429:
        return RateLimitError(f"Gemini rate-limited the request: {message}")
    if isinstance(status, str) and status.upper() in {
        "UNAUTHENTICATED",
        "PERMISSION_DENIED",
    }:
        return AuthenticationError(f"Gemini rejected our credentials: {message}")
    if isinstance(status, str) and status.upper() in {
        "RESOURCE_EXHAUSTED",
    }:
        return RateLimitError(f"Gemini rate-limited the request: {message}")
    return UpstreamProviderError(f"Gemini upstream error: {message}")
