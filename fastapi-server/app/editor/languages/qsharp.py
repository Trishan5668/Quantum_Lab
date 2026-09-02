"""Q# execution via isolated subprocess using Microsoft QDK."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from app.editor.languages.base import LanguageRunner
from app.editor.subprocess_utils import run_isolated_subprocess

_WORKER = Path(__file__).resolve().parent.parent / "workers" / "run_qsharp.py"


class QSharpRunner(LanguageRunner):
    language = "qsharp"

    async def run(self, code: str, *, timeout_s: float) -> tuple[str, str, int]:
        with tempfile.TemporaryDirectory(prefix="qlab-qsharp-") as tmp:
            source_path = Path(tmp) / "user_code.qs"
            source_path.write_text(code, encoding="utf-8")
            cmd = [sys.executable, "-I", "-u", str(_WORKER), str(source_path)]
            return await run_isolated_subprocess(cmd, cwd=tmp, timeout_s=timeout_s)
