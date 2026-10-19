"""Verify every committed raw artifact and audit its claims."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from quantumlab.research.qec.artifacts import verify_artifact
from quantumlab.research.qec.claims import audit_artifact


def main() -> int:
    base = Path(__file__).resolve().parents[1] / "results" / "raw"
    failures = []
    checked = 0
    for directory in sorted(base.glob("2026*/")):
        if not directory.is_dir():
            continue
        checked += 1
        integrity = verify_artifact(directory)
        claims = audit_artifact(directory)
        print(
            f"{directory.name}: integrity={integrity.ok} "
            f"claims={claims['status']}"
        )
        if not integrity.ok:
            failures.append((directory.name, "integrity", integrity.errors))
        if claims["status"] != "PASS":
            failures.append((directory.name, "claims", claims["errors"]))
    print(json.dumps({"checked": checked, "failures": failures}, indent=2))
    return 0 if checked > 0 and not failures else 1


if __name__ == "__main__":
    sys.exit(main())
