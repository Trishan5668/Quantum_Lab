"""Quantum code editor execution routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.editor.executor import execute_editor_code
from app.models import envelope
from app.models_v2 import EditorRunIn

router = APIRouter(prefix="/api/v2/editor", tags=["editor"])


@router.post("/run")
async def run_editor(payload: EditorRunIn) -> dict[str, object]:
    """Execute user quantum code in an isolated subprocess."""
    result = await execute_editor_code(payload.language, payload.code)
    return envelope(result.model_dump())
