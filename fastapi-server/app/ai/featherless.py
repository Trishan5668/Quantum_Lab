"""Featherless-backed conversational AI for the QuantumLab side pane."""

from __future__ import annotations

import json
import os
from typing import Any, Final

import httpx

from app.llm.base import (
    AuthenticationError,
    MissingApiKeyError,
    RateLimitError,
    UpstreamProviderError,
)
from app.models_v2 import AIChatRequest

DEFAULT_MODEL: Final[str] = "deepseek-ai/DeepSeek-V4-Flash"
CHAT_COMPLETIONS_URL: Final[str] = "https://api.featherless.ai/v1/chat/completions"
MAX_CONTEXT_CHARS: Final[int] = 24000

SYSTEM_PROMPT: Final[str] = """You are QuantumLab AI, an assistant embedded in a quantum computing simulator.

Answer questions about the supplied circuit and its mathematical and physical results. Treat the supplied QuantumLab context as the source of truth for circuit-specific values. Never invent amplitudes, probabilities, matrices, eigenvalues, entropy, fidelity, trace distance, or any other numerical result. If a requested quantity is absent, say it is unavailable.

Clearly distinguish QuantumLab simulation results, Wolfram-verified results, and your own explanation. Only call a result Wolfram verified when the supplied Wolfram status is VERIFIED. If it is UNAVAILABLE, PENDING, or DISCREPANCY, say so and do not imply independent verification.

Adapt to the supplied learning mode: Explore is concise and beginner-friendly; Understand is step-by-step with moderate mathematics; Intuition emphasizes physical meaning; Research uses formal quantum mechanics and quantum-information terminology, with equations only where the supplied context supports them. Use LaTex when useful. Refer to actual gates, qubits, states, and values in the supplied context. Do not claim to have calculated or verified anything beyond that context."""


class FeatherlessChatClient:
    """Small OpenAI-compatible Featherless client with safe error translation."""

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
            raise MissingApiKeyError("QuantumLab AI is not configured. FEATHERLESS_API_KEY is not set.")

        messages = build_messages(request)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.25,
            "max_tokens": 900,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://quantumlab.app",
            "X-Title": "QuantumLab",
        }
        try:
            if self._client_factory is not None:
                async with self._client_factory() as client:
                    response = await client.post(CHAT_COMPLETIONS_URL, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await client.post(CHAT_COMPLETIONS_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise UpstreamProviderError("QuantumLab AI timed out. Please try again.") from exc
        except httpx.HTTPError as exc:
            raise UpstreamProviderError("QuantumLab AI is temporarily unavailable. Please try again.") from exc

        if response.status_code in (401, 403):
            raise AuthenticationError("QuantumLab AI could not authenticate with its provider.")
        if response.status_code == 429:
            raise RateLimitError("QuantumLab AI is rate limited. Please try again shortly.")
        if response.is_error:
            raise UpstreamProviderError("QuantumLab AI is temporarily unavailable. Please try again.")

        try:
            payload_out = response.json()
            content = payload_out["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise UpstreamProviderError("QuantumLab AI returned an invalid response. Please try again.") from exc
        if not isinstance(content, str) or not content.strip():
            raise UpstreamProviderError("QuantumLab AI returned an empty response. Please try again.")
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
