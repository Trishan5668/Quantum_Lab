from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest

from app.llm.base import (
    AuthenticationError,
    ComplexAmplitude,
    ExplanationRequest,
    MissingApiKeyError,
    RateLimitError,
    UpstreamProviderError,
)
from app.llm.gemini_provider import DEFAULT_MODEL, GeminiProvider


@dataclass
class _StubChunk:
    text: str


class _StubStream:
    def __init__(self, chunks: list[_StubChunk]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> AsyncIterator[_StubChunk]:
        return self._gen()

    async def _gen(self) -> AsyncIterator[_StubChunk]:
        for c in self._chunks:
            yield c


class _StubModels:
    def __init__(self, chunks: list[_StubChunk]) -> None:
        self._chunks = chunks
        self.calls: list[dict[str, Any]] = []

    async def generate_content_stream(
        self, *, model: str, contents: Any, config: Any
    ) -> _StubStream:
        self.calls.append({"model": model, "contents": contents, "config": config})
        return _StubStream(self._chunks)


class _StubClient:
    def __init__(self, chunks: list[_StubChunk]) -> None:
        self.aio = type("_Aio", (), {})()
        self.aio.models = _StubModels(chunks)  # type: ignore[attr-defined]


def _make_request() -> ExplanationRequest:
    return ExplanationRequest(
        gate="H",
        num_qubits=1,
        state_before=[ComplexAmplitude(1.0, 0.0), ComplexAmplitude(0.0, 0.0)],
        state_after=[
            ComplexAmplitude(0.7071067811865475, 0.0),
            ComplexAmplitude(0.7071067811865475, 0.0),
        ],
        context="first_gate",
        mode="normal",
        qubit=0,
    )


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider()

    async def go() -> None:
        async for _ in provider.stream_explanation(_make_request()):
            pass

    import asyncio

    with pytest.raises(MissingApiKeyError):
        asyncio.run(go())


def test_streaming_yields_concatenated_text() -> None:
    chunks = [_StubChunk("Imagine a coin "), _StubChunk("spinning in mid-air.")]
    captured: list[_StubClient] = []

    def factory(*, api_key: str) -> _StubClient:
        assert api_key == "AIza-test"
        c = _StubClient(chunks)
        captured.append(c)
        return c

    provider = GeminiProvider(api_key="AIza-test", client_factory=factory)

    import asyncio

    async def collect() -> list[str]:
        out: list[str] = []
        async for tok in provider.stream_explanation(_make_request()):
            out.append(tok)
        return out

    tokens = asyncio.run(collect())
    assert tokens == ["Imagine a coin ", "spinning in mid-air."]
    assert captured[0].aio.models.calls[0]["model"] == DEFAULT_MODEL
    sent_contents = captured[0].aio.models.calls[0]["contents"]
    assert "Applied" in sent_contents or "Just applied" in sent_contents
    assert "H" in sent_contents


def test_model_override_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTUMLAB_GEMINI_MODEL", "gemini-2.5-pro")
    provider = GeminiProvider(api_key="x", client_factory=lambda *, api_key: _StubClient([]))
    assert provider._model == "gemini-2.5-pro"


def test_constructor_model_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTUMLAB_GEMINI_MODEL", "gemini-2.5-pro")
    provider = GeminiProvider(
        api_key="x",
        model="custom-model",
        client_factory=lambda *, api_key: _StubClient([]),
    )
    assert provider._model == "custom-model"


def test_chunk_text_fallback_to_candidates() -> None:
    from app.llm.gemini_provider import _chunk_text

    class _Part:
        def __init__(self, t: str) -> None:
            self.text = t

    class _Content:
        def __init__(self) -> None:
            self.parts = [_Part("hello")]

    class _Candidate:
        def __init__(self) -> None:
            self.content = _Content()

    class _Chunk:
        text = None
        candidates = [_Candidate()]

    assert _chunk_text(_Chunk()) == "hello"


def test_translate_authentication_error() -> None:
    from google.genai import errors as ge

    from app.llm.gemini_provider import _translate_api_error

    exc = ge.ClientError(401, {"error": {"message": "bad key"}})
    out = _translate_api_error(exc)
    assert isinstance(out, AuthenticationError)


def test_translate_rate_limit_error() -> None:
    from google.genai import errors as ge

    from app.llm.gemini_provider import _translate_api_error

    exc = ge.ClientError(429, {"error": {"message": "slow down"}})
    out = _translate_api_error(exc)
    assert isinstance(out, RateLimitError)


def test_translate_generic_upstream_error() -> None:
    from google.genai import errors as ge

    from app.llm.gemini_provider import _translate_api_error

    exc = ge.ServerError(503, {"error": {"message": "down"}})
    out = _translate_api_error(exc)
    assert isinstance(out, UpstreamProviderError)


def test_api_error_during_streaming_is_translated() -> None:
    from google.genai import errors as ge

    class _BoomModels:
        async def generate_content_stream(
            self, *, model: str, contents: Any, config: Any
        ) -> Any:
            raise ge.ClientError(429, {"error": {"message": "rate"}})

    class _BoomClient:
        def __init__(self) -> None:
            self.aio = type("_A", (), {})()
            self.aio.models = _BoomModels()  # type: ignore[attr-defined]

    provider = GeminiProvider(
        api_key="x", client_factory=lambda *, api_key: _BoomClient()
    )

    import asyncio

    async def collect() -> None:
        async for _ in provider.stream_explanation(_make_request()):
            pass

    with pytest.raises(RateLimitError):
        asyncio.run(collect())
