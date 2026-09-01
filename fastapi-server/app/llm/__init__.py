"""LLM provider package for QuantumLab's ELI15 endpoint.

Selecting a provider is environment-driven (:envvar:`LLM_PROVIDER`)
with a deterministic offline fallback so the explanation endpoint is
always available even without a cloud API key.
"""

from __future__ import annotations

from app.llm.base import (
    AuthenticationError,
    ChatProvider,
    ConfigurationError,
    ExplanationProvider,
    ExplanationRequest,
    LlmError,
    MissingApiKeyError,
    ProviderTimeoutError,
    RateLimitError,
    UpstreamProviderError,
    get_chat_provider,
    get_provider,
)

__all__ = [
    "AuthenticationError",
    "ChatProvider",
    "ConfigurationError",
    "ExplanationProvider",
    "ExplanationRequest",
    "LlmError",
    "MissingApiKeyError",
    "ProviderTimeoutError",
    "RateLimitError",
    "UpstreamProviderError",
    "get_chat_provider",
    "get_provider",
]
