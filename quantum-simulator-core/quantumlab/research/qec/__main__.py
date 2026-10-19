"""Command-line interface for the QEC research platform.

Commands
--------
``audit``      Print a machine-readable capability and environment audit.
``validate``   Validate a legacy or versioned protocol.
``run``        Execute a protocol and write an immutable artifact.
``analyze``    Print an artifact summary (JSON by default, table on request).
``compare``    Compare two verified artifacts with a Newcombe interval.
``verify``     Recompute checksums and metadata cross-checks.
``package``    Build a verified tar.gz evidence package.
``claims``     Audit claim language and zero-failure reporting.
``reproduce``  Run a pre-declared reproduction target (Phase 2) or rerun a
               legacy artifact directory.
``generalize`` Run the pre-declared Phase 4 generalization study.
``validate-suite`` Run the independent-validation checks and write evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quantumlab.research.qec.artifacts import (
    ArtifactError,
    package_artifact,
    read_summary,
    verify_artifact,
)
from quantumlab.research.qec.audit import repository_capabilities
from quantumlab.research.qec.claims import audit_artifact
from quantumlab.research.qec.experiment import run_protocol
from quantumlab.research.qec.protocol import ExperimentProtocol, Protocol, load_protocol
from quantumlab.research.qec.runner import run_experiment
from quantumlab.research.qec.stats import difference_ci_newcombe


def _dispatch_run(protocol: ExperimentProtocol | Protocol, output: Path) -> Path:
    if isinstance(protocol, ExperimentProtocol):
        return run_protocol(protocol, output)
    return run_experiment(protocol, output)


def _format_table(summary: dict[str, object]) -> str:
    result = summary.get("result")
    if not isinstance(result, dict):
        return _format_research_table(summary)
    lines = [
        f"experiment: {summary.get('experiment_id', 'unknown')}",
        f"backend: {result.get('backend')}",
        f"shots: {result.get('shots')}",
        "",
        f"{'decoder':<20} {'failures':>10} {'estimate':>12} {'interval':>28}",
    ]
    decoders = result.get("decoders", {})
    if isinstance(decoders, dict):
        for name, payload in decoders.items():
            if not isinstance(payload, dict):
                continue
            interval = (
                f"[{payload.get('interval_low'):.6g}, "
                f"{payload.get('interval_high'):.6g}]"
                if isinstance(payload.get("interval_low"), (int, float))
                and isinstance(payload.get("interval_high"), (int, float))
                else "n/a"
            )
            lines.append(
                f"{name:<20} {payload.get('operational_failures'):>10} "
                f"{payload.get('probability'):>12.6g} {interval:>28}"
            )
            if payload.get("operational_failures") == 0:
                lines.append(
                    f"{'  (zero events)':<20} {'':>10} "
                    f"upper bound {payload.get('zero_failure_upper_bound'):.6g}"
                )
    return "\n".join(lines)


def _format_interval(payload: dict[str, object]) -> str:
    low = payload.get("interval_low")
    high = payload.get("interval_high")
    if isinstance(low, (int, float)) and isinstance(high, (int, float)):
        return f"[{low:.6g}, {high:.6g}]"
    return "n/a"


def _format_research_table(summary: dict[str, object]) -> str:
    """Render reproduction, calibration, and validation summaries.

    The table reports exactly what is stored in the artifact.  It never
    upgrades a zero count into a zero probability: rows with zero failures
    show the one-sided upper bound (or ``missing`` if none was recorded).
    """
    lines = [
        f"experiment: {summary.get('experiment_id', 'unknown')}",
        f"status: {summary.get('status', 'n/a')}",
    ]
    labels = summary.get("claim_labels")
    if labels:
        lines.append(f"claim_labels: {json.dumps(labels, sort_keys=True)}")
    provenance = summary.get("provenance")
    if isinstance(provenance, dict):
        lines.append(
            "provenance: revision="
            f"{provenance.get('source_revision', 'n/a')} "
            f"dirty={provenance.get('dirty', 'n/a')}"
        )
    if summary.get("config_hash"):
        lines.append(f"config_hash: {summary.get('config_hash')}")
    if summary.get("runtime_seconds") is not None:
        lines.append(f"runtime_seconds: {summary.get('runtime_seconds')}")

    rows = summary.get("results")
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        lines.extend(
            [
                "",
                f"{'stage':<10} {'d':>3} {'p':>8} {'failures':>9} {'shots':>9} "
                f"{'probability':>12} {'interval':>26}",
            ]
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            failures = row.get("failures")
            note = ""
            if failures == 0:
                bound = row.get("zero_failure_upper_bound", row.get("interval_high"))
                note = (
                    f"  zero events: upper bound {bound:.6g}"
                    if isinstance(bound, (int, float))
                    else "  zero events: upper bound missing"
                )
            lines.append(
                f"{str(row.get('stage')):<10} {str(row.get('distance')):>3} "
                f"{float(row.get('p', float('nan'))):>8.5g} {str(failures):>9} "
                f"{str(row.get('shots', row.get('trials'))):>9} "
                f"{float(row.get('probability', float('nan'))):>12.6g} "
                f"{_format_interval(row):>26}{note}"
            )
        analysis = summary.get("analysis")
        if isinstance(analysis, dict):
            lines.append("")
            lines.append(f"bracket: {analysis.get('bracket')}")
            lines.append(f"claim: {analysis.get('claim_label')}")
            for criterion in analysis.get("criteria", []):
                if isinstance(criterion, dict):
                    lines.append(
                        f"  {criterion.get('id')}: passed={criterion.get('passed')} "
                        f"detail={criterion.get('detail')}"
                    )
        return "\n".join(lines)

    cells = summary.get("cells")
    if isinstance(cells, dict):
        gates = summary.get("gates")
        if isinstance(gates, list) and gates:
            lines.extend(["", "gates:"])
            for gate in gates:
                if isinstance(gate, dict):
                    lines.append(f"  {gate.get('id')}: passed={gate.get('passed')}")
        lines.extend(
            [
                "",
                f"{'condition':<24} {'d':>3} {'failures':>9} {'shots':>9} "
                f"{'probability':>12} {'interval':>26}",
            ]
        )
        for name, cell in sorted(cells.items()):
            if not isinstance(cell, dict):
                continue
            for label, comparison in sorted(cell.items()):
                if not isinstance(comparison, dict) or "first_summary" not in comparison:
                    continue
                payload = comparison["first_summary"]
                if not isinstance(payload, dict):
                    continue
                failures = payload.get("failures")
                note = ""
                if failures == 0:
                    bound = payload.get("zero_failure_upper_bound")
                    note = (
                        f"  zero events: upper bound {bound:.6g}"
                        if isinstance(bound, (int, float))
                        else "  zero events: upper bound missing"
                    )
                lines.append(
                    f"{name + ':' + label:<24} {str(cell.get('distance')):>3} "
                    f"{str(failures):>9} {str(payload.get('trials')):>9} "
                    f"{float(payload.get('probability', float('nan'))):>12.6g} "
                    f"{_format_interval(payload):>26}{note}"
                )
        return "\n".join(lines)

    phase3 = summary.get("phase3")
    if isinstance(phase3, dict):
        payload = _format_research_table(phase3).splitlines()
        lines.extend(["", "phase3:"] + [f"  {line}" for line in payload])
        phase4 = summary.get("phase4")
        if isinstance(phase4, dict):
            lines.extend(
                [
                    "",
                    f"phase4 status: {phase4.get('status')}",
                    f"phase4 rationale: {phase4.get('rationale')}",
                ]
            )
            for gate in phase4.get("gates", []):
                if isinstance(gate, dict):
                    lines.append(f"  {gate.get('id')}: passed={gate.get('passed')}")
        return "\n".join(lines)
    return json.dumps(summary, indent=2, sort_keys=True)


def _compare(first: Path, second: Path, *, allow_different: bool) -> dict[str, object]:
    reports = [verify_artifact(first), verify_artifact(second)]
    if not all(report.ok for report in reports):
        raise ArtifactError(
            "both artifacts must pass integrity verification: "
            + json.dumps([report.to_dict() for report in reports])
        )
    a = read_summary(first)
    b = read_summary(second)
    if not allow_different and a.get("config_hash") != b.get("config_hash"):
        raise ArtifactError(
            "artifacts have different config hashes; use --allow-different-config "
            "to compare them as distinct experiments"
        )
    result_a = a["result"]
    result_b = b["result"]
    names_a = set(result_a["decoders"])
    names_b = set(result_b["decoders"])
    common = sorted(names_a & names_b)
    if not common:
        raise ArtifactError("artifacts have no decoder in common")
    rows = []
    for name in common:
        payload_a = result_a["decoders"][name]
        payload_b = result_b["decoders"][name]
        low, high = difference_ci_newcombe(
            payload_a["operational_failures"],
            payload_a["trials"],
            payload_b["operational_failures"],
            payload_b["trials"],
            a.get("protocol", {})
            .get("statistics", {})
            .get("confidence_level", 0.95),
        )
        rows.append(
            {
                "decoder": name,
                "first": payload_a,
                "second": payload_b,
                "difference_first_minus_second": (
                    payload_a["probability"] - payload_b["probability"]
                ),
                "difference_ci": [low, high],
            }
        )
    return {
        "first": str(first),
        "second": str(second),
        "same_configuration": a.get("config_hash") == b.get("config_hash"),
        "comparison_method": (
            "Newcombe hybrid score interval for independent samples; this is not "
            "a paired analysis"
        ),
        "rows": rows,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m quantumlab.research.qec")
    parser.add_argument("--version", action="version", version="quantumlab-qec 1.0.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="print capability audit")
    audit.add_argument("--output", type=Path)

    validate = subparsers.add_parser("validate", help="validate a protocol")
    validate.add_argument("protocol", type=Path)

    run = subparsers.add_parser("run", help="execute a protocol")
    run.add_argument("protocol", type=Path)
    run.add_argument("--output", type=Path, default=Path("research/qec/experiments"))
    run.add_argument("--experiment-id")

    analyze = subparsers.add_parser("analyze", help="summarize an artifact")
    analyze.add_argument("experiment", type=Path)
    analyze.add_argument("--format", choices=("json", "table"), default="json")

    compare = subparsers.add_parser("compare", help="compare two artifacts")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)
    compare.add_argument("--allow-different-config", action="store_true")

    verify = subparsers.add_parser("verify", help="verify artifact integrity")
    verify.add_argument("artifact", type=Path)
    verify.add_argument("--json", action="store_true")

    claims = subparsers.add_parser("claims", help="audit claim language and zero-failure reporting")
    claims.add_argument("artifact", type=Path)

    package = subparsers.add_parser("package", help="package a verified artifact")
    package.add_argument("artifact", type=Path)
    package.add_argument("--output", type=Path)

    reproduce = subparsers.add_parser("reproduce", help="reproduce a declared target")
    reproduce.add_argument("target", type=Path)
    reproduce.add_argument("--output", type=Path, default=Path("research/qec/experiments"))
    reproduce.add_argument(
        "--rerun-legacy",
        action="store_true",
        help="rerun a legacy artifact directory from its config.yaml",
    )

    generalize = subparsers.add_parser(
        "generalize", help="run the pre-declared Phase 4 generalization study"
    )
    generalize.add_argument(
        "--output", type=Path, default=Path("research/qec/results/raw")
    )

    validate_suite = subparsers.add_parser(
        "validate-suite", help="run the independent-validation checks"
    )
    validate_suite.add_argument(
        "--output", type=Path, default=Path("research/qec/validation")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "audit":
            payload = repository_capabilities()
            text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            if args.output is not None:
                args.output.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
            return 0
        if args.command == "validate":
            protocol = load_protocol(args.protocol)
            payload = {
                "valid": True,
                "schema": "2.0" if isinstance(protocol, ExperimentProtocol) else "legacy",
                "config_hash": (
                    protocol.config_hash
                    if isinstance(protocol, ExperimentProtocol)
                    else None
                ),
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
        if args.command == "run":
            protocol = load_protocol(args.protocol)
            if isinstance(protocol, ExperimentProtocol):
                directory = run_protocol(
                    protocol, args.output, experiment_id=args.experiment_id
                )
            else:
                if args.experiment_id is not None:
                    raise SystemExit(
                        "--experiment-id is only supported for schema_version 2.0"
                    )
                directory = run_experiment(protocol, args.output)
            print(json.dumps({"experiment_dir": str(directory)}))
            return 0
        if args.command == "analyze":
            summary = read_summary(args.experiment)
            if args.format == "table":
                print(_format_table(summary))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            report = verify_artifact(args.artifact)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            else:
                print("INTEGRITY_OK" if report.ok else "INTEGRITY_FAILED")
                for error in report.errors:
                    print(f"error: {error}")
                for warning in report.warnings:
                    print(f"warning: {warning}")
            return 0 if report.ok else 1
        if args.command == "claims":
            claims_report = audit_artifact(args.artifact)
            print(json.dumps(claims_report, indent=2, sort_keys=True))
            return 0 if claims_report["status"] == "PASS" else 1
        if args.command == "package":
            destination = package_artifact(args.artifact, args.output)
            print(json.dumps({"package": str(destination)}))
            return 0
        if args.command == "compare":
            print(
                json.dumps(
                    _compare(
                        args.first,
                        args.second,
                        allow_different=args.allow_different_config,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "reproduce":
            if args.rerun_legacy or (args.target / "config.yaml").is_file():
                protocol = load_protocol(args.target / "config.yaml")
                directory = _dispatch_run(protocol, args.output)
                print(
                    json.dumps(
                        {
                            "experiment_dir": str(directory),
                            "source": str(args.target),
                        }
                    )
                )
                return 0
            from quantumlab.research.qec.reproduction import run_reproduction_target

            payload = run_reproduction_target(args.target, args.output)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload.get("status") in {"REPRODUCED", "PARTIAL"} else 1
        if args.command == "generalize":
            from quantumlab.research.qec.calibration import run_generalization_study

            payload = run_generalization_study(args.output)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "validate-suite":
            from quantumlab.research.qec.validation import run_validation

            payload = run_validation(args.output)
            print(json.dumps(payload, indent=2, sort_keys=True))
            status = str(payload.get("overall_status", ""))
            return 0 if status.startswith("PASS") else 1
    except (ArtifactError, OSError, ValueError, RuntimeError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
