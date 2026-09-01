from __future__ import annotations

import logging
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm.base import (
    AuthenticationError,
    ConfigurationError,
    MissingApiKeyError,
    ProviderNoFinalAnswerError,
    ProviderTimeoutError,
    ProviderTruncatedResponseError,
    RateLimitError,
    UpstreamProviderError,
    get_chat_provider,
)
from app.llm.featherless_provider import (
    CHAT_COMPLETIONS_URL,
    DEFAULT_MODEL,
    FeatherlessChatProvider,
    build_messages,
)
from app.main import create_app
from app.models_v2 import AIChatRequest


def _request() -> AIChatRequest:
    return AIChatRequest.model_validate(
        {
            "message": "Why is this entangled?",
            "history": [{"role": "user", "content": "Explain the circuit."}],
            "context": {
                "learning_mode": "research",
                "circuit": {
                    "num_qubits": 2,
                    "initial_basis_state": "00",
                    "gates": [{"id": "h", "gate_type": "H", "qubit_targets": [0], "time_step": 0}],
                },
                "simulation": {"final_state": [{"real": 0.70710678, "imag": 0}, {"real": 0, "imag": 0}]},
                "mathematics": {"metrics": {"purity": {"purity": 1}}},
                "physics": {"sections": [{"title": "Entanglement", "markdown": "Report context"}]},
                "wolfram": {"status": "VERIFIED", "message": "Verified"},
            },
        }
    )


def _factory(handler: httpx.MockTransport):
    return lambda: httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_successful_featherless_request_uses_model_and_context() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "The context shows a Bell preparation."}}]})

    client = FeatherlessChatProvider(api_key="test-secret", client_factory=_factory(httpx.MockTransport(handler)))
    assert await client.chat(_request()) == "The context shows a Bell preparation."
    assert seen["body"]["model"] == DEFAULT_MODEL  # type: ignore[index]
    assert seen["headers"]["authorization"] == "Bearer test-secret"  # type: ignore[index]
    assert seen["url"] == CHAT_COMPLETIONS_URL
    messages = seen["body"]["messages"]  # type: ignore[index]
    assert any("Current QuantumLab context" in item["content"] for item in messages)
    assert "test-secret" not in str(seen["body"])


def test_model_can_be_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATHERLESS_MODEL", "custom/deepseek")
    assert FeatherlessChatProvider(api_key="key").model == "custom/deepseek"


def test_chat_provider_factory_selects_featherless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_CHAT_PROVIDER", "featherless")
    assert isinstance(get_chat_provider(), FeatherlessChatProvider)


@pytest.mark.asyncio
async def test_missing_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        await FeatherlessChatProvider().chat(_request())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, ConfigurationError),
        (429, RateLimitError),
        (500, UpstreamProviderError),
    ],
)
async def test_http_errors_are_safe(status: int, error: type[Exception]) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "provider internals"})

    client = FeatherlessChatProvider(api_key="key", client_factory=_factory(httpx.MockTransport(handler)))
    with pytest.raises(error):
        await client.chat(_request())


@pytest.mark.asyncio
async def test_timeout_and_malformed_response_are_unavailable() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = FeatherlessChatProvider(api_key="key", client_factory=_factory(httpx.MockTransport(timeout)))
    with pytest.raises(ProviderTimeoutError):
        await client.chat(_request())

    malformed = FeatherlessChatProvider(
        api_key="key",
        client_factory=_factory(httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": []}))),
    )
    with pytest.raises(UpstreamProviderError):
        await malformed.chat(_request())


@pytest.mark.asyncio
async def test_reasoning_response_uses_final_content_and_classifies_truncation() -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                json={
                    "usage": {"completion_tokens": 120},
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "Final answer.", "reasoning": "internal only"},
                        }
                    ],
                },
            ),
            httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": None, "reasoning_content": "internal only"},
                        }
                    ]
                },
            ),
            httpx.Response(
                200,
                json={"choices": [{"finish_reason": "stop", "message": {"content": None, "reasoning": "internal only"}}]},
            ),
        ]
    )
    client = FeatherlessChatProvider(
        api_key="key",
        client_factory=_factory(httpx.MockTransport(lambda _: next(responses))),
    )
    assert await client.chat(_request()) == "Final answer."
    with pytest.raises(ProviderTruncatedResponseError):
        await client.chat(_request())
    with pytest.raises(ProviderNoFinalAnswerError):
        await client.chat(_request())


@pytest.mark.asyncio
async def test_diagnostics_redact_provider_key(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    key = "secret-provider-key"
    client = FeatherlessChatProvider(
        api_key=key,
        client_factory=_factory(httpx.MockTransport(lambda _: httpx.Response(403, text=f"Authorization: Bearer {key}"))),
    )
    with pytest.raises(AuthenticationError):
        await client.chat(_request())
    messages = build_messages(_request())
    assert messages[0]["role"] == "system"
    assert '"learning_mode":"research"' in messages[1]["content"]
    logged = "\n".join(record.message for record in caplog.records)
    assert key not in logged
    assert "provider=featherless" in logged
    assert "content_type=" in logged


def test_route_returns_safe_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    response = TestClient(create_app()).post("/api/v2/ai/chat", json=_request().model_dump(mode="json"))
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "AIUnavailable"
    assert "FEATHERLESS_API_KEY" not in body["error"]["message"]
