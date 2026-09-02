"""Editor code execution dispatcher."""

from __future__ import annotations

import time

from app.editor.languages.base import EditorLanguageId, get_language_runner
from app.models_v2 import EditorRunOut

MAX_CODE_BYTES = 32_768
DEFAULT_TIMEOUT_S = 15.0


async def execute_editor_code(language: EditorLanguageId, code: str) -> EditorRunOut:
    stripped = code.strip()
    if not stripped:
        return EditorRunOut(
            language=language,
            status="error",
            stdout="",
            stderr="Code cannot be empty.",
            execution_time_ms=0.0,
        )

    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return EditorRunOut(
            language=language,
            status="error",
            stdout="",
            stderr=f"Code exceeds maximum size of {MAX_CODE_BYTES} bytes.",
            execution_time_ms=0.0,
        )

    runner = get_language_runner(language)
    started = time.perf_counter()
    stdout, stderr, exit_code = await runner.run(stripped, timeout_s=DEFAULT_TIMEOUT_S)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if exit_code == -1 and "timed out" in stderr.lower():
        return EditorRunOut(
            language=language,
            status="error",
            stdout=stdout,
            stderr=stderr,
            execution_time_ms=elapsed_ms,
        )

    if exit_code == 127:
        return EditorRunOut(
            language=language,
            status="error",
            stdout=stdout,
            stderr=stderr or "Required runtime is not installed on the server.",
            execution_time_ms=elapsed_ms,
        )

    if exit_code != 0:
        return EditorRunOut(
            language=language,
            status="error",
            stdout=stdout,
            stderr=stderr or f"Process exited with code {exit_code}",
            execution_time_ms=elapsed_ms,
        )

    return EditorRunOut(
        language=language,
        status="success",
        stdout=stdout,
        stderr=stderr,
        execution_time_ms=elapsed_ms,
    )
