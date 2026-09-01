"""AI assistant route for circuit-aware QuantumLab conversations."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.llm import (
    AuthenticationError,
    ConfigurationError,
    MissingApiKeyError,
    ProviderMalformedResponseError,
    ProviderNoChoicesError,
    ProviderNoFinalAnswerError,
    ProviderTimeoutError,
    ProviderTruncatedResponseError,
    RateLimitError,
    UpstreamProviderError,
    get_chat_provider,
)
from app.models import envelope
from app.models_v2 import AIChatOut, AIChatRequest

router = APIRouter(prefix="/api/v2/ai", tags=["ai"])


@router.post("/chat", response_model=None)
async def chat(payload: AIChatRequest) -> dict[str, object] | JSONResponse:
    try:
        provider = get_chat_provider()
        answer = await provider.chat(payload)
    except MissingApiKeyError:
        return _error(503, "AIUnavailable", "QuantumLab AI is not configured on this server.")
    except ConfigurationError as exc:
        return _error(502, "AIProviderConfigurationError", str(exc))
    except AuthenticationError as exc:
        return _error(502, "AIAuthenticationError", str(exc))
    except RateLimitError as exc:
        return _error(429, "AIRateLimited", str(exc))
    except ProviderTimeoutError as exc:
        return _error(504, "AITimeout", str(exc))
    except ProviderTruncatedResponseError as exc:
        return _error(502, "AIResponseTruncated", str(exc))
    except ProviderNoChoicesError as exc:
        return _error(502, "AINoChoices", str(exc))
    except ProviderMalformedResponseError as exc:
        return _error(502, "AIMalformedResponse", str(exc))
    except ProviderNoFinalAnswerError as exc:
        return _error(502, "AINoFinalAnswer", str(exc))
    except UpstreamProviderError as exc:
        return _error(502, "AIUpstreamError", str(exc))
    return envelope(AIChatOut(answer=answer, model=provider.model).model_dump())


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": None, "error": {"code": code, "message": message, "trace": None}},
    )
