from __future__ import annotations

import json
from pathlib import Path

import yaml

from quantumlab.research.qec.__main__ import main

RAW = {
    "schema_version": "2.0",
    "name": "cli_test",
    "research_question": "Does the CLI work?",
    "hypothesis": "Yes.",
    "code": {"family": "repetition", "distance": 3, "rounds": 1, "task": "memory_z"},
    "noise": {
        "kind": "code_capacity",
        "model": "bit_flip",
        "parameters": {"p": 0.1},
    },
    "decoders": [{"name": "exact"}],
    "comparisons": [],
    "experiment": {
        "shots": 100,
        "seed": 3,
        "partition": "development",
        "stopping_rule": "fixed_shots",
    },
    "statistics": {
        "method": "wilson",
        "confidence_level": 0.95,
        "primary_metric": "operational_failure_probability",
    },
    "limitations": ["CLI test."],
}


def _run(tmp_path: Path) -> Path:
    path = tmp_path / "protocol.yaml"
    path.write_text(yaml.safe_dump(RAW), encoding="utf-8")
    assert main(["run", str(path), "--output", str(tmp_path / "runs")]) == 0
    artifacts = list((tmp_path / "runs").iterdir())
    assert len(artifacts) == 1
    return artifacts[0]


def test_validate_and_audit(tmp_path: Path, capsys) -> None:
    path = tmp_path / "protocol.yaml"
    path.write_text(yaml.safe_dump(RAW), encoding="utf-8")
    assert main(["validate", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert main(["audit"]) == 0
    audit = json.loads(capsys.readouterr().out)
    assert "capabilities" in audit
    assert audit["optional_dependencies"]["stim"] in {True, False}


def test_run_analyze_verify_claims(tmp_path: Path, capsys) -> None:
    artifact = _run(tmp_path)
    capsys.readouterr()
    assert main(["analyze", str(artifact), "--format", "table"]) == 0
    assert "exact" in capsys.readouterr().out
    assert main(["verify", str(artifact), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert main(["claims", str(artifact)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    assert main(["package", str(artifact)]) == 0
    assert json.loads(capsys.readouterr().out)["package"].endswith(".tar.gz")


def test_compare_requires_integrity_and_reports(tmp_path: Path, capsys) -> None:
    artifact = _run(tmp_path)
    capsys.readouterr()
    assert main(["compare", str(artifact), str(artifact)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["same_configuration"] is True
    assert payload["rows"]
    assert payload["rows"][0]["difference_first_minus_second"] == 0.0


def test_verify_reports_failure_for_tampered_artifact(tmp_path: Path, capsys) -> None:
    artifact = _run(tmp_path)
    capsys.readouterr()
    with (artifact / "summary.json").open("a", encoding="utf-8") as handle:
        handle.write(" ")
    assert main(["verify", str(artifact)]) == 1
    assert "INTEGRITY_FAILED" in capsys.readouterr().out


def test_invalid_protocol_exits_nonzero(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump({"schema_version": "2.0"}), encoding="utf-8")
    assert main(["validate", str(path)]) == 1
    assert "error:" in capsys.readouterr().err
