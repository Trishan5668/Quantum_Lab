"""Language and file-type capability registry.

QuantHub can *store, browse, edit, import, export and highlight* every language
listed here.  That is deliberately separate from **execution**, which requires a
tested isolated runtime.  The registry therefore states execution support
explicitly and, for everything except the pre-existing constrained editor
workers, reports ``supported: false``.

``mode`` values are Monaco/CodeMirror-compatible language identifiers used by
the web client; ``highlight: false`` means the client renders the file as plain
text while still allowing edits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LanguageSpec:
    id: str
    label: str
    extensions: tuple[str, ...] = ()
    filenames: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    mode: str | None = None
    highlight: bool = True
    editable: bool = True
    formatter: str | None = None
    linter: str | None = None
    execute: bool = False
    runtime: str | None = None
    sandboxed: bool = False
    execution_notes: str = ""
    category: str = "code"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "extensions": list(self.extensions),
            "filenames": list(self.filenames),
            "prefixes": list(self.prefixes),
            "mode": self.mode,
            "highlight": self.highlight,
            "editable": self.editable,
            "formatter": self.formatter,
            "linter": self.linter,
            "execution": {
                "supported": self.execute,
                "runtime": self.runtime,
                "sandboxed": self.sandboxed,
                "enabled_by_default": False,
                "notes": self.execution_notes,
            },
            "category": self.category,
        }


_NO_EXEC = "Execution is not offered for user repositories; files are stored and highlighted only."

LANGUAGES: tuple[LanguageSpec, ...] = (
    LanguageSpec("python", "Python", (".py", ".pyi", ".pyw"), mode="python", linter="ruff (CI only)"),
    LanguageSpec("javascript", "JavaScript", (".js", ".mjs", ".cjs", ".jsx"), mode="javascript"),
    LanguageSpec("typescript", "TypeScript", (".ts", ".tsx", ".mts", ".cts"), mode="typescript"),
    LanguageSpec("java", "Java", (".java",), mode="java"),
    LanguageSpec("cpp", "C++", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"), mode="cpp"),
    LanguageSpec("csharp", "C#", (".cs", ".csx"), mode="csharp"),
    LanguageSpec("c", "C", (".c",), mode="c"),
    LanguageSpec("go", "Go", (".go",), mode="go"),
    LanguageSpec("rust", "Rust", (".rs",), mode="rust"),
    LanguageSpec("sql", "SQL", (".sql",), mode="sql"),
    LanguageSpec("php", "PHP", (".php", ".phtml"), mode="php"),
    LanguageSpec("kotlin", "Kotlin", (".kt", ".kts"), mode="kotlin"),
    LanguageSpec("swift", "Swift", (".swift",), mode="swift"),
    LanguageSpec("ruby", "Ruby", (".rb", ".rake", ".gemspec"), ("Gemfile", "Rakefile"), mode="ruby"),
    LanguageSpec("r", "R", (".r", ".R", ".rmd"), mode="r"),
    LanguageSpec("html", "HTML", (".html", ".htm", ".xhtml"), mode="html"),
    LanguageSpec("css", "CSS", (".css", ".scss", ".sass", ".less"), mode="css"),
    LanguageSpec("matlab", "MATLAB", (".m", ".mlx"), mode="matlab"),
    LanguageSpec("scala", "Scala", (".scala", ".sc"), mode="scala"),
    LanguageSpec(
        "shell",
        "Shell / Bash",
        (".sh", ".bash", ".zsh", ".ksh", ".fish"),
        (".bashrc", ".zshrc", ".profile", ".bash_profile", ".envrc"),
        mode="shell",
    ),
    LanguageSpec(
        "example",
        "Example (.example)",
        (".example",),
        mode="plaintext",
        category="config",
    ),
    LanguageSpec("yaml", "YAML", (".yaml", ".yml"), mode="yaml", category="config"),
    LanguageSpec(
        "rules",
        "Security rules (.rules)",
        (".rules",),
        mode="plaintext",
        category="config",
    ),
    LanguageSpec("text", "Plain text", (".txt", ".text", ".log"), ("LICENSE", "NOTICE", "AUTHORS"), mode="plaintext", category="text"),
    LanguageSpec("toml", "TOML", (".toml",), mode="ini", category="config"),
    LanguageSpec("perl", "Perl", (".pl", ".pm", ".t"), mode="perl"),
    LanguageSpec("markdown", "Markdown", (".md", ".markdown", ".mdx"), mode="markdown", category="docs"),
    LanguageSpec("json", "JSON", (".json", ".jsonc", ".json5"), mode="json", category="data"),
    LanguageSpec("jsonl", "JSON Lines", (".jsonl", ".ndjson"), mode="plaintext", category="data"),
    LanguageSpec("xml", "XML", (".xml", ".xsd", ".xsl", ".svg"), mode="xml", category="data"),
    LanguageSpec("csv", "CSV", (".csv", ".tsv"), mode="plaintext", category="data"),
    LanguageSpec("notebook", "Jupyter notebook", (".ipynb",), mode="json", category="data"),
    LanguageSpec("dockerfile", "Dockerfile", (), ("Dockerfile", "Containerfile"), mode="dockerfile", category="config"),
    LanguageSpec("makefile", "Makefile", (".mk",), ("Makefile", "GNUmakefile", "makefile"), mode="makefile", category="config"),
    LanguageSpec(
        "lockfile",
        "Lockfile",
        (".lock",),
        ("package-lock.json", "poetry.lock", "pipfile.lock", "cargo.lock", "yarn.lock", "go.sum", "uv.lock"),
        mode="plaintext",
        editable=False,
        category="config",
    ),
    LanguageSpec(
        "dotenv",
        "Environment template",
        (".env", ".env.example", ".env.local", ".env.sample", ".env.template"),
        (".env.example", ".env.sample", ".env.template"),
        mode="ini",
        category="config",
    ),
    LanguageSpec("gitignore", "Git ignore", (".gitignore", ".dockerignore", ".npmignore"), mode="plaintext", category="config"),
    LanguageSpec("gitattributes", "Git attributes", (".gitattributes",), mode="plaintext", category="config"),
    LanguageSpec(
        "binary",
        "Binary artifact",
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".tar", ".gz", ".tgz", ".npy", ".npz", ".h5", ".hdf5", ".pt", ".pkl", ".parquet", ".onnx", ".wav", ".mp4", ".woff", ".woff2", ".ttf", ".otf"),
        mode=None,
        highlight=False,
        editable=False,
        category="binary",
    ),
)

_BY_FILENAME: dict[str, LanguageSpec] = {}
_BY_EXTENSION: dict[str, LanguageSpec] = {}
for _spec in LANGUAGES:
    for _name in _spec.filenames:
        _BY_FILENAME[_name.lower()] = _spec
    for _ext in _spec.extensions:
        _BY_EXTENSION[_ext.lower()] = _spec


def detect_language(path: str) -> LanguageSpec:
    """Resolve a path to a language spec.

    Filenames win over extensions (``Dockerfile``), then the longest matching
    extension (``.env.example`` before ``.example``).  Unknown files fall back to
    plain text rather than guessing a language.
    """
    name = path.rsplit("/", 1)[-1].lower()
    if name in _BY_FILENAME:
        return _BY_FILENAME[name]
    best: tuple[int, LanguageSpec] | None = None
    for ext, spec in _BY_EXTENSION.items():
        if name.endswith(ext) and (best is None or len(ext) > best[0]):
            best = (len(ext), spec)
    if best is not None:
        return best[1]
    return LanguageSpec(
        "unknown",
        "Text",
        mode="plaintext",
        category="text",
        execution_notes=_NO_EXEC,
    )


def language_registry() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "notice": (
            "File support (storage, browsing, editing, highlighting, import and "
            "export) does not imply execution support. Execution requires a "
            "tested isolated runtime and is disabled by default for every "
            "language listed here."
        ),
        "languages": [spec.to_dict() for spec in LANGUAGES],
    }


def language_for_filename(path: str) -> dict[str, Any]:
    spec = detect_language(path)
    payload = spec.to_dict()
    payload["id"] = spec.id
    return payload
