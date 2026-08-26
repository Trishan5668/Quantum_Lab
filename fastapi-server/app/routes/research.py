"""Research Mode verification endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import envelope
from app.models_v2 import ResearchVerifyRequest
from app.wolfram import verify_research_payload

router = APIRouter(prefix="/api/v2/research", tags=["research"])


@router.post("/verify")
async def verify(payload: ResearchVerifyRequest) -> dict[str, object]:
    """Verify Research Mode mathematics through the Wolfram boundary.

    The route intentionally returns 200 with ``status == UNAVAILABLE`` when
    Wolfram is not configured or reachable. Research Mode can then stay usable
    while clearly labeling native simulator output as unverified.
    """
    result = await verify_research_payload(payload)
    return envelope(result)
