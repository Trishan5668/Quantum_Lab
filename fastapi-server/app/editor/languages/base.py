"""Language runner abstraction for the quantum code editor."""

from __future__ import annotations

import abc
from typing import Literal

EditorLanguageId = Literal["qiskit", "qsharp"]


class LanguageRunner(abc.ABC):
    language: EditorLanguageId

    @abc.abstractmethod
    async def run(self, code: str, *, timeout_s: float) -> tuple[str, str, int]:
        """Execute code in an isolated subprocess.

        Returns (stdout, stderr, exit_code).
        """


def get_language_runner(language: EditorLanguageId) -> LanguageRunner:
    if language == "qiskit":
        from app.editor.languages.qiskit import QiskitRunner

        return QiskitRunner()
    if language == "qsharp":
        from app.editor.languages.qsharp import QSharpRunner

        return QSharpRunner()
    raise ValueError(f"Unsupported editor language: {language}")
