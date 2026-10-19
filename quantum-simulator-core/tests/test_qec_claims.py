from __future__ import annotations

import json
from pathlib import Path

from quantumlab.research.qec.claims import audit_artifact, audit_summary, audit_text


def _summary(**overrides: object) -> dict:
    base = {
        "experiment_id": "x",
        "config_hash": "a" * 64,
        "scientific_status": "PENDING_VALIDATION",
        "provenance": {"source_revision": "abc", "dirty": True},
        "result": {
            "backend": "pauli",
            "comparisons": [{"first": "a", "second": "b"}],
            "decoders": {
                "a": {
                    "operational_failures": 1,
                    "probability": 0.01,
                    "interval_low": 0.0,
                    "interval_high": 0.02,
                    "trials": 100,
                    "method": "wilson",
                }
            },
        },
    }
    base.update(overrides)
    return base


def test_zero_failure_without_bound_is_rejected() -> None:
    summary = _summary()
    decoder = summary["result"]["decoders"]["a"]
    decoder["operational_failures"] = 0
    decoder["probability"] = 0.0
    report = audit_summary(summary)
    assert report["status"] == "FAIL"
    assert any("upper bound" in error for error in report["errors"])


def test_zero_failure_with_bound_passes() -> None:
    summary = _summary()
    decoder = summary["result"]["decoders"]["a"]
    decoder["operational_failures"] = 0
    decoder["probability"] = 0.0
    decoder["zero_failure_upper_bound"] = 0.03
    assert audit_summary(summary)["status"] == "PASS"


def test_banned_language_is_rejected_in_artifact(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(json.dumps(_summary()), encoding="utf-8")
    (tmp_path / "report.md").write_text(
        "This is a production-ready, state-of-the-art result.", encoding="utf-8"
    )
    report = audit_artifact(tmp_path)
    assert report["status"] == "FAIL"
    assert len([error for error in report["errors"] if "banned" in error]) == 2


def test_clean_report_passes(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(json.dumps(_summary()), encoding="utf-8")
    (tmp_path / "report.md").write_text(
        "A bounded simulation result with no hardware claim.", encoding="utf-8"
    )
    assert audit_artifact(tmp_path)["status"] == "PASS"


def test_multiple_decoders_require_comparison() -> None:
    summary = _summary()
    summary["result"]["comparisons"] = []
    summary["result"]["decoders"]["b"] = dict(summary["result"]["decoders"]["a"])
    report = audit_summary(summary)
    assert report["status"] == "FAIL"
    assert any("paired comparison" in error for error in report["errors"])


def test_text_audit_is_case_insensitive() -> None:
    assert audit_text("State-Of-The-Art") == ["state-of-the-art"]
    assert audit_text("bounded simulation") == []
