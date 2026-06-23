from __future__ import annotations

import pytest

from app.llm import (
    ConfigurationError,
    ExplanationProvider,
    get_provider,
)
from app.llm.gemini_provider import GeminiProvider
from app.llm.local_provider import LocalProvider


def test_explicit_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = get_provider("gemini")
    assert isinstance(p, GeminiProvider)
    assert isinstance(p, ExplanationProvider)


def test_explicit_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = get_provider("local")
    assert isinstance(p, LocalProvider)
    assert isinstance(p, ExplanationProvider)


def test_env_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_provider(), GeminiProvider)


def test_env_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_provider(), LocalProvider)


def test_env_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", " GEMINI ")
    assert isinstance(get_provider(), GeminiProvider)


def test_auto_prefers_gemini_when_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-key")
    assert isinstance(get_provider(), GeminiProvider)


def test_auto_falls_back_to_local_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_provider(), LocalProvider)


def test_unsupported_provider_name_raises() -> None:
    with pytest.raises(ConfigurationError):
        get_provider("openai")  # type: ignore[arg-type]


def test_unsupported_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(ConfigurationError):
        get_provider()
