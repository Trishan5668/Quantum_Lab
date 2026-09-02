"""Qiskit / Python execution via isolated subprocess."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from app.editor.languages.base import LanguageRunner
from app.editor.subprocess_utils import run_isolated_subprocess

_WORKER = Path(__file__).resolve().parent.parent / "workers" / "run_qiskit.py"


class QiskitRunner(LanguageRunner):
    language = "qiskit"

    async def run(self, code: str, *, timeout_s: float) -> tuple[str, str, int]:
        with tempfile.TemporaryDirectory(prefix="qlab-qiskit-") as tmp:
            script_path = Path(tmp) / "user_code.py"
            script_path.write_text(code, encoding="utf-8")
            cmd = [sys.executable, "-I", "-u", str(_WORKER), str(script_path)]
            return await run_isolated_subprocess(cmd, cwd=tmp, timeout_s=timeout_s)
