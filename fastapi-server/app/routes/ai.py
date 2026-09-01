"""AI assistant route for circuit-aware QuantumLab conversations."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.ai import FeatherlessChatClient
from app.llm.base import AuthenticationError, MissingApiKeyError, RateLimitError, UpstreamProviderError
from app.models import envelope
from app.models_v2 import AIChatOut, AIChatRequest

router = APIRouter(prefix="/api/v2/ai", tags=["ai"])


@router.post("/chat", response_model=None)
async def chat(payload: AIChatRequest) -> dict[str, object] | JSONResponse:
    client = FeatherlessChatClient()
    try:
        answer = await client.chat(payload)
    except MissingApiKeyError as exc:
        return _error(503, "AIUnavailable", "QuantumLab AI is not configured on this server.")
    except AuthenticationError:
        return _error(502, "AIAuthenticationError", "QuantumLab AI could not authenticate with its provider.")
    except RateLimitError as exc:
        return _error(429, "AIRateLimited", str(exc))
    except UpstreamProviderError as exc:
        return _error(502, "AIUpstreamError", str(exc))
    return envelope(AIChatOut(answer=answer, model=client.model).model_dump())


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": None, "error": {"code": code, "message": message, "trace": None}},
    )
