"""Claim-language and artifact audit.

This module does not decide whether a scientific claim is true.  It rejects
specific unsupported language and catches the most common reporting failure:
turning zero observed failures into a zero-probability claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BANNED_PHRASES: tuple[str, ...] = (
    "state-of-the-art",
    "industry-leading",
    "production-ready",
    "first-ever",
    "solves an open problem",
)

REQUIRED_TOP_LEVEL = (
    "experiment_id",
    "config_hash",
    "provenance",
)


def audit_text(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered]


def audit_summary(summary: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_TOP_LEVEL:
        if key not in summary:
            errors.append(f"missing required summary field: {key}")
    provenance = summary.get("provenance", {})
    if isinstance(provenance, dict):
        if not provenance.get("source_revision"):
            errors.append("provenance.source_revision is missing")
        if provenance.get("dirty") is None:
            errors.append("provenance.dirty is missing")
    else:
        errors.append("provenance must be a mapping")
    result = summary.get("result")
    if not isinstance(result, dict):
        if "analysis" in summary and isinstance(summary.get("results"), list):
            for row in summary["results"]:
                if not isinstance(row, dict):
                    errors.append("reproduction result row is not a mapping")
                    continue
                if row.get("failures") == 0 and not row.get("interval_high"):
                    errors.append(
                        f"reproduction point {row.get('stage')} d={row.get('distance')} "
                        "has zero failures without an upper bound"
                    )
            return {
                "status": "PASS" if not errors else "FAIL",
                "errors": errors,
                "warnings": warnings,
                "shape": "reproduction",
            }
        if "phase3" in summary or "phase4" in summary or "gates" in summary:
            return {
                "status": "PASS" if not errors else "FAIL",
                "errors": errors,
                "warnings": warnings,
                "shape": "study",
            }
        errors.append("result must be a mapping")
        return {"status": "FAIL", "errors": errors, "warnings": warnings}
    backend = result.get("backend")
    if backend == "stim+pymatching":
        for key in ("stim_version", "pymatching_version", "dem_sha256", "circuit_sha256"):
            if not result.get(key):
                errors.append(f"Stim-backed result missing {key}")
    decoders = result.get("decoders", {})
    if not isinstance(decoders, dict) or not decoders:
        errors.append("no decoder results found")
        return {"status": "FAIL", "errors": errors, "warnings": warnings}
    for name, payload in decoders.items():
        if not isinstance(payload, dict):
            errors.append(f"decoder {name!r} payload is not a mapping")
            continue
        failures = payload.get("operational_failures")
        if failures == 0 and payload.get("zero_failure_upper_bound") is None:
            errors.append(
                f"decoder {name!r} reports zero failures without a one-sided upper bound"
            )
        if payload.get("probability") == 0 and payload.get("zero_failure_upper_bound") is None:
            errors.append(
                f"decoder {name!r} reports probability 0.0 without a bound"
            )
        for key in ("interval_low", "interval_high", "trials", "method"):
            if key not in payload:
                errors.append(f"decoder {name!r} missing {key}")
    comparisons = result.get("comparisons", [])
    if len(decoders) > 1 and not comparisons:
        errors.append(
            "multiple decoders are reported without a pre-declared paired comparison"
        )
    if summary.get("scientific_status") is None:
        warnings.append(
            "scientific_status is missing; the run must not be presented as validated"
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "backend": backend,
        "decoder_count": len(decoders),
    }


def audit_artifact(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        return {
            "status": "FAIL",
            "errors": [f"summary.json missing in {root}"],
            "warnings": [],
        }
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "FAIL", "errors": [f"invalid summary.json: {exc}"], "warnings": []}
    report_path = root / "report.md"
    report_text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    result = audit_summary(summary)
    banned = audit_text(report_text)
    if banned:
        result["errors"].extend(
            [f"banned claim phrase in report.md: {phrase!r}" for phrase in banned]
        )
        result["status"] = "FAIL"
    result["report_present"] = report_path.is_file()
    return result
