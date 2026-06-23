"""Provider abstraction for the ELI15 explanation endpoint.

The public surface is::

    ExplanationProvider          - Protocol implemented by every backend
    ExplanationRequest           - structured input describing one gate step
    get_provider(name=None)      - factory; reads LLM_PROVIDER if name is None

Exception hierarchy (all subclass :class:`LlmError`)::

    LlmError
      ConfigurationError         - bad/unsupported LLM_PROVIDER value
      MissingApiKeyError         - provider needs a key that isn't set
      AuthenticationError        - upstream rejected the key (401/403)
      RateLimitError             - upstream throttled us (429)
      UpstreamProviderError      - anything else from the upstream API

These are never silently swallowed -- the route surfaces them as
non-2xx responses using the same ``{ data, error }`` envelope used
by the rest of the API.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

ProviderName = Literal["gemini", "local"]
"""Names of all supported provider backends."""


SUPPORTED_PROVIDERS: tuple[ProviderName, ...] = ("gemini", "local")


class LlmError(Exception):
    """Root of the LLM provider exception hierarchy."""


class ConfigurationError(LlmError):
    """Raised when the requested provider name is not supported."""


class MissingApiKeyError(LlmError):
    """Raised when a provider that needs a key is invoked without one."""


class AuthenticationError(LlmError):
    """Raised when the upstream LLM API rejects our credentials."""


class RateLimitError(LlmError):
    """Raised when the upstream LLM API rate-limits us."""


class UpstreamProviderError(LlmError):
    """Raised for any other non-success upstream response."""


@dataclass(frozen=True)
class ComplexAmplitude:
    """JSON-friendly complex number used by the request body."""

    real: float
    imag: float


ExplanationMode = Literal["normal", "deep", "hint"]


@dataclass(frozen=True)
class ExplanationRequest:
    """Structured input passed to every provider.

    The shape intentionally matches the wire format consumed by the
    :class:`~app.models.ExplainRequest` Pydantic model so route adapters
    can translate without information loss.
    """

    gate: str
    num_qubits: int
    state_before: list[ComplexAmplitude]
    state_after: list[ComplexAmplitude]
    context: str = "step"
    mode: ExplanationMode = "normal"
    qubit: int | None = None
    qubits: list[int] | None = None
    probabilities: list[float] = field(default_factory=list)


@runtime_checkable
class ExplanationProvider(Protocol):
    """Stream a token-by-token ELI15 explanation.

    Implementations must yield UTF-8 text fragments. The caller wraps
    each fragment in an SSE ``event: token`` frame, so providers MUST
    NOT emit raw SSE framing themselves.

    Implementations MUST raise one of the typed errors above on
    failure -- silent fallbacks are forbidden.
    """

    def stream_explanation(
        self,
        request: ExplanationRequest,
    ) -> AsyncIterator[str]:
        """Yield UTF-8 text fragments token-by-token.

        Implementations are async generators (``async def`` with
        ``yield``), so calling this method returns an ``AsyncIterator``
        immediately and the actual work happens during iteration.
        """
        ...


def _resolve_provider_name(explicit: ProviderName | None) -> ProviderName:
    if explicit is not None:
        if explicit not in SUPPORTED_PROVIDERS:
            raise ConfigurationError(
                f"unsupported LLM provider: {explicit!r}. "
                f"Supported: {SUPPORTED_PROVIDERS}"
            )
        return explicit

    env = os.environ.get("LLM_PROVIDER")
    if env is None or env == "":
        # No explicit choice -> auto-select: prefer gemini when a key is
        # present, otherwise fall back to the offline deterministic
        # provider so /explain is always usable.
        if os.environ.get("GEMINI_API_KEY"):
            return "gemini"
        return "local"

    env_lower = env.strip().lower()
    if env_lower not in SUPPORTED_PROVIDERS:
        raise ConfigurationError(
            f"unsupported LLM_PROVIDER={env!r}. "
            f"Supported values: {SUPPORTED_PROVIDERS}"
        )
    return env_lower


def get_provider(name: ProviderName | None = None) -> ExplanationProvider:
    """Return an :class:`ExplanationProvider` instance.

    Resolution order:

    1. The explicit ``name`` argument, if given.
    2. The ``LLM_PROVIDER`` environment variable.
    3. Auto-pick: ``gemini`` if ``GEMINI_API_KEY`` is set, else ``local``.

    Raises
    ------
    ConfigurationError
        If the resolved name is not in :data:`SUPPORTED_PROVIDERS`.
    """
    resolved = _resolve_provider_name(name)
    if resolved == "gemini":
        from app.llm.gemini_provider import GeminiProvider

        return GeminiProvider()
    if resolved == "local":
        from app.llm.local_provider import LocalProvider

        return LocalProvider()
    # Defensive: _resolve_provider_name already validates this branch is
    # unreachable, but keep an explicit raise to satisfy type narrowing
    # and make accidental enum extensions loud.
    raise ConfigurationError(f"unsupported provider after resolution: {resolved!r}")
