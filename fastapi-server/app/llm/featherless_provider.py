"""OpenAI-compatible Featherless provider for QuantumLab AI chat."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Final

import httpx

from app.llm.base import (
    AuthenticationError,
    ConfigurationError,
    MissingApiKeyError,
    ProviderTimeoutError,
    RateLimitError,
    UpstreamProviderError,
)
from app.models_v2 import AIChatRequest

logger = logging.getLogger(__name__)

PROVIDER_NAME: Final[str] = "featherless"
DEFAULT_MODEL: Final[str] = "deepseek-ai/DeepSeek-V4-Flash"
BASE_URL: Final[str] = "https://api.featherless.ai/v1"
CHAT_COMPLETIONS_URL: Final[str] = f"{BASE_URL}/chat/completions"
MAX_CONTEXT_CHARS: Final[int] = 24000

SYSTEM_PROMPT: Final[str] = """You are QuantumLab AI, an assistant embedded in a quantum computing simulator.

Answer questions about the supplied circuit and its mathematical and physical results. Treat the supplied QuantumLab context as the source of truth for circuit-specific values. Never invent amplitudes, probabilities, matrices, eigenvalues, entropy, fidelity, trace distance, or any other numerical result. If a requested quantity is absent, say it is unavailable.

Clearly distinguish QuantumLab simulation results, Wolfram-verified results, and your own explanation. Only call a result Wolfram verified when the supplied Wolfram status is VERIFIED. If it is UNAVAILABLE, PENDING, or DISCREPANCY, say so and do not imply independent verification.

Adapt to the supplied learning mode: Explore is concise and beginner-friendly; Understand is step-by-step with moderate mathematics; Intuition emphasizes physical meaning; Research uses formal quantum mechanics and quantum-information terminology, with equations only where the supplied context supports them. Use LaTex when useful. Refer to actual gates, qubits, states, and values in the supplied context. Do not claim to have calculated or verified anything beyond that context."""


class FeatherlessChatProvider:
    """Server-side Featherless chat provider using its OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("FEATHERLESS_API_KEY")
        self.model = model or os.getenv("FEATHERLESS_MODEL") or DEFAULT_MODEL
        self._client_factory = client_factory

    async def chat(self, request: AIChatRequest) -> str:
        if not self._api_key:
            raise MissingApiKeyError("FEATHERLESS_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": build_messages(request),
            "temperature": 0.25,
            "max_tokens": 900,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://quantumlab.app",
            "X-Title": "QuantumLab",
        }
        logger.info("AI provider request provider=%s model=%s", PROVIDER_NAME, self.model)
        try:
            if self._client_factory is not None:
                async with self._client_factory() as client:
                    response = await client.post(CHAT_COMPLETIONS_URL, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await client.post(CHAT_COMPLETIONS_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("AI provider timeout provider=%s model=%s", PROVIDER_NAME, self.model)
            raise ProviderTimeoutError("Featherless timed out while generating a response.") from exc
        except httpx.HTTPError as exc:
            logger.warning("AI provider connection failure provider=%s model=%s error=%s", PROVIDER_NAME, self.model, type(exc).__name__)
            raise UpstreamProviderError("Featherless connection failed. Please try again.") from exc

        content_type = response.headers.get("content-type", "unknown")
        logger.info(
            "AI provider response provider=%s model=%s status=%s content_type=%s",
            PROVIDER_NAME,
            self.model,
            response.status_code,
            content_type,
        )
        if response.status_code in (401, 403):
            _log_error_response(response, self._api_key, self.model)
            raise AuthenticationError(
                f"Featherless rejected the configured credentials or model access (HTTP {response.status_code})."
            )
        if response.status_code == 404:
            _log_error_response(response, self._api_key, self.model)
            raise ConfigurationError(
                f"Featherless could not find the configured chat endpoint or model (HTTP 404, model {self.model})."
            )
        if response.status_code == 429:
            _log_error_response(response, self._api_key, self.model)
            raise RateLimitError("Featherless rate limited this request. Please try again shortly.")
        if response.status_code >= 500:
            _log_error_response(response, self._api_key, self.model)
            raise UpstreamProviderError(f"Featherless upstream service error (HTTP {response.status_code}).")
        if response.is_error:
            _log_error_response(response, self._api_key, self.model)
            raise UpstreamProviderError(f"Featherless rejected the request (HTTP {response.status_code}).")

        try:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("AI provider malformed response provider=%s model=%s", PROVIDER_NAME, self.model)
            raise UpstreamProviderError("Featherless returned a malformed chat response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise UpstreamProviderError("Featherless returned an empty chat response.")
        return content.strip()


def build_messages(request: AIChatRequest) -> list[dict[str, str]]:
    context = request.context.model_dump(mode="json")
    context_text = json.dumps(context, separators=(",", ":"), ensure_ascii=True)
    if len(context_text) > MAX_CONTEXT_CHARS:
        context_text = context_text[:MAX_CONTEXT_CHARS] + "...[context truncated]"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": f"Current QuantumLab context:\n{context_text}"})
    messages.extend(message.model_dump() for message in request.history[-12:])
    messages.append({"role": "user", "content": request.message})
    return messages


def _log_error_response(response: httpx.Response, api_key: str, model: str) -> None:
    logger.warning(
        "AI provider upstream error provider=%s model=%s status=%s content_type=%s body=%s",
        PROVIDER_NAME,
        model,
        response.status_code,
        response.headers.get("content-type", "unknown"),
        _safe_error_body(response.text, api_key),
    )


def _safe_error_body(body: str, api_key: str) -> str:
    safe = body[:800].replace(api_key, "[REDACTED]")
    safe = re.sub(r"(?i)bearer\\s+[^\\s\"']+", "Bearer [REDACTED]", safe)
    safe = re.sub(r"(?i)(api[_-]?key[=:\\s]+)[^,\\s\"'}]+", r"\\1[REDACTED]", safe)
    return safe
