#!/usr/bin/env python3
"""Isolated Qiskit/Python worker — invoked only as a subprocess, never in the API process."""

from __future__ import annotations

import io
import runpy
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_qiskit.py <source.py>", file=sys.stderr)
        return 2

    source_path = sys.argv[1]
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    try:
        runpy.run_path(source_path, run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    except Exception:
        import traceback

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
