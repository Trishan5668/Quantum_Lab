#!/usr/bin/env python3
"""Isolated Q# worker — invoked only as a subprocess, never in the API process."""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_qsharp.py <source.qs>", file=sys.stderr)
        return 2

    source_path = sys.argv[1]
    try:
        with open(source_path, encoding="utf-8") as handle:
            code = handle.read()
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        from qdk import qsharp
    except ImportError as exc:
        print(
            f"Q# runtime not available. Install qdk on the server: {exc}",
            file=sys.stderr,
        )
        return 127

    try:
        qsharp.init()
        qsharp.eval(code)
        result = qsharp.run("Main()", shots=1)
        if result is not None:
            print(result)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
