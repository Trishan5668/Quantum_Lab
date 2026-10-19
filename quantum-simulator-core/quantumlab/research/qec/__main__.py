"""CLI for validating and running bounded QEC research protocols."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from quantumlab.research.qec.protocol import load_protocol
from quantumlab.research.qec.runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m quantumlab.research.qec")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("protocol", type=Path)
    run = subparsers.add_parser("run")
    run.add_argument("protocol", type=Path)
    run.add_argument("--output", type=Path, default=Path("research/qec/experiments"))
    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("experiment", type=Path)
    reproduce = subparsers.add_parser("reproduce")
    reproduce.add_argument("experiment", type=Path)
    reproduce.add_argument("--output", type=Path, default=Path("research/qec/experiments"))
    args = parser.parse_args()
    if args.command == "validate":
        protocol = load_protocol(args.protocol)
        print("valid")
    elif args.command == "run":
        protocol = load_protocol(args.protocol)
        artifact_dir = run_experiment(protocol, args.output)
        print(json.dumps({"experiment_dir": str(artifact_dir)}))
    elif args.command == "analyze":
        summary_path = args.experiment / "summary.json"
        if not summary_path.is_file():
            raise SystemExit(f"summary not found: {summary_path}")
        print(summary_path.read_text(encoding="utf-8"), end="")
    else:
        protocol = load_protocol(args.experiment / "config.yaml")
        artifact_dir = run_experiment(protocol, args.output)
        print(json.dumps({"experiment_dir": str(artifact_dir), "source": str(args.experiment)}))


if __name__ == "__main__":
    main()
