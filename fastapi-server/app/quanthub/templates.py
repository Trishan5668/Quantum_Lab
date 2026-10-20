"""Project initialisation templates: README, .gitignore and licenses.

License texts are stored verbatim from GitHub's licence API
(``api.github.com/licenses/<key>``, which serves SPDX-aligned texts) so the
repository never hand-maintains legal text.  The text is emitted unchanged apart
from the documented copyright placeholders.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

from app.quanthub.errors import bad_request

LICENSE_DIR = Path(__file__).resolve().parent / "licenses"


@dataclass(frozen=True)
class LicenseOption:
    spdx: str
    name: str
    file: str
    requires_attribution: bool


LICENSES: tuple[LicenseOption, ...] = (
    LicenseOption("MIT", "MIT License", "mit", True),
    LicenseOption("Apache-2.0", "Apache License 2.0", "apache-2.0", True),
    LicenseOption("GPL-3.0", "GNU General Public License v3.0", "gpl-3.0", False),
    LicenseOption("BSD-3-Clause", 'BSD 3-Clause "New" or "Revised" License', "bsd-3-clause", True),
    LicenseOption("MPL-2.0", "Mozilla Public License 2.0", "mpl-2.0", False),
    LicenseOption("Unlicense", "The Unlicense", "unlicense", False),
)

LICENSE_NOTICE = (
    "No license means the default copyright rules apply: others may view the "
    "project but do not receive permission to copy, modify, or redistribute it."
)

_GITIGNORE_TEMPLATES: dict[str, str] = {
    "none": "",
    "python": """# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
build/
dist/
.venv/
venv/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
""",
    "node": """# Node
node_modules/
dist/
build/
.env
.env.local
npm-debug.log*
yarn-error.log*
.cache/
coverage/
""",
    "typescript": """# TypeScript / Vite
node_modules/
dist/
dist-ssr/
*.tsbuildinfo
.env
.env.local
coverage/
""",
    "rust": """# Rust
/target/
**/*.rs.bk
Cargo.lock
.env
""",
    "go": """# Go
/bin/
/dist/
*.test
*.out
.env
""",
    "java": """# Java
target/
build/
*.class
*.jar
.gradle/
.idea/
*.iml
""",
    "cpp": """# C / C++
build/
cmake-build-*/
*.o
*.obj
*.so
*.a
*.exe
compile_commands.json
""",
    "jupyter": """# Jupyter
.ipynb_checkpoints/
__pycache__/
.env
data/raw/
""",
    "latex": """# LaTeX
*.aux
*.log
*.out
*.toc
*.synctex.gz
*.fls
*.fdb_latexmk
""",
}


def gitignore_templates() -> list[dict[str, str]]:
    return [{"id": key, "content": value} for key, value in _GITIGNORE_TEMPLATES.items()]


def gitignore_text(template: str | None) -> str:
    key = (template or "none").strip().lower()
    if key not in _GITIGNORE_TEMPLATES:
        raise bad_request(
            "UnknownGitignoreTemplate",
            f"Unknown .gitignore template '{template}'.",
            available=sorted(_GITIGNORE_TEMPLATES),
        )
    return _GITIGNORE_TEMPLATES[key]


def license_options() -> list[dict[str, object]]:
    return [
        {
            "spdx": option.spdx,
            "name": option.name,
            "requires_attribution": option.requires_attribution,
        }
        for option in LICENSES
    ]


def license_text(spdx: str, *, author: str, year: int | None = None) -> str:
    option = next((item for item in LICENSES if item.spdx.lower() == spdx.strip().lower()), None)
    if option is None:
        raise bad_request(
            "UnknownLicense",
            f"Unknown license '{spdx}'.",
            available=[item.spdx for item in LICENSES],
        )
    text = (LICENSE_DIR / f"{option.file}.txt").read_text(encoding="utf-8")
    stamp = str(year or _dt.date.today().year)
    replacements = {
        "[year]": stamp,
        "[yyyy]": stamp,
        "[fullname]": author,
        "[name of copyright owner]": author,
        "<name of author>": author,
        "<year>": stamp,
        "<program>": "this project",
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


README_TEMPLATE = """# {name}

{description}

## Overview

<!-- What problem does this project solve? What is in scope? -->

- **Owner:** {owner}
- **Visibility:** {visibility}
- **Topics:** {topics}

## Installation

```bash
git clone <this-project>
cd {slug}
```

Add the exact commands and pinned dependency versions needed to reproduce your
environment.

## Usage

Document the primary entry point and a minimal working example.

## Experiments

QuantHub experiments live under the project's **Experiments** tab. Each
experiment specification records its code family, noise model, decoders,
statistics settings, and seeds. Runs are executed by the scientific engine and
their artifacts are immutable.

To run an experiment from the command line:

```bash
python -m quantumlab.research.qec run path/to/protocol.yaml --output experiments/
```

## Results and reproducibility

Record, for each reported result:

1. The experiment specification and its configuration hash.
2. The software revision and dependency versions.
3. Random seeds and shot counts.
4. The raw artifact directory and its checksums.
5. The analysis method and confidence intervals.

State clearly what has been validated and what has not.

## License

{license_section}
"""


def readme_text(
    *,
    name: str,
    description: str,
    owner: str,
    visibility: str,
    topics: list[str],
    slug: str,
    license_spdx: str | None,
) -> str:
    if license_spdx:
        license_section = f"Released under the {license_spdx} license. See LICENSE."
    else:
        license_section = (
            "No license has been declared. "
            + LICENSE_NOTICE
        )
    return README_TEMPLATE.format(
        name=name,
        description=description or "_Add a short description of this project._",
        owner=owner,
        visibility=visibility,
        topics=", ".join(topics) if topics else "_none yet_",
        slug=slug,
        license_section=license_section,
    )
