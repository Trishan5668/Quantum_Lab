"""Language runner abstraction for the quantum code editor."""

from __future__ import annotations

import abc
import importlib
from typing import Literal

EditorLanguageId = Literal["qiskit", "pennylane", "qsharp"]

_RUNNER_SPECS: dict[EditorLanguageId, tuple[str, str]] = {
    "qiskit": ("app.editor.languages.qiskit", "QiskitRunner"),
    "pennylane": ("app.editor.languages.pennylane", "PennylaneRunner"),
    "qsharp": ("app.editor.languages.qsharp", "QSharpRunner"),
}


class LanguageRunner(abc.ABC):
    language: EditorLanguageId

    @abc.abstractmethod
    async def run(self, code: str, *, timeout_s: float) -> tuple[str, str, int]:
        """Execute code in an isolated subprocess.

        Returns (stdout, stderr, exit_code).
        """


def get_language_runner(language: EditorLanguageId) -> LanguageRunner:
    spec = _RUNNER_SPECS.get(language)
    if spec is None:
        raise ValueError(f"Unsupported editor language: {language}")
    module_path, class_name = spec
    module = importlib.import_module(module_path)
    runner_cls = getattr(module, class_name)
    return runner_cls()
