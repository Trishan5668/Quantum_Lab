from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from quantumlab.research.qec.artifacts import verify_artifact
from quantumlab.research.qec.experiment import ExperimentError, run_protocol
from quantumlab.research.qec.protocol import ExperimentProtocol, ProtocolError, load_protocol

BASE: dict[str, Any] = {
    "schema_version": "2.0",
    "name": "experiment_unit",
    "research_question": "Do paired decoders agree?",
    "hypothesis": "Exact, majority, and MWPM agree on repetition codes.",
    "code": {"family": "repetition", "distance": 5, "rounds": 1, "task": "memory_z"},
    "noise": {
        "kind": "code_capacity",
        "model": "bit_flip",
        "parameters": {"p": 0.1},
    },
    "decoders": [
        {"name": "exact"},
        {"name": "majority_vote"},
        {"name": "mwpm", "parameters": {"error_probability": 0.1}},
    ],
    "comparisons": ["exact:majority_vote", "exact:mwpm"],
    "experiment": {
        "shots": 500,
        "seed": 11,
        "partition": "development",
        "stopping_rule": "fixed_shots",
    },
    "statistics": {
        "method": "wilson",
        "confidence_level": 0.95,
        "primary_metric": "operational_failure_probability",
    },
    "limitations": ["Unit-test protocol."],
}


def _write(tmp_path: Path, **updates: Any) -> Path:
    raw = copy.deepcopy(BASE)
    raw.update(updates)
    path = tmp_path / "protocol.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=True), encoding="utf-8")
    return path


def _load(path: Path) -> ExperimentProtocol:
    protocol = load_protocol(path)
    assert isinstance(protocol, ExperimentProtocol)
    return protocol


def _records(directory: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (directory / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_paired_decoders_agree_shot_by_shot(tmp_path: Path) -> None:
    pytest.importorskip("pymatching")
    artifact = run_protocol(_load(_write(tmp_path)), tmp_path / "runs")
    rows = _records(artifact)
    assert len(rows) == 500
    for row in rows:
        assert row["d"]["exact"]["f"] == row["d"]["majority_vote"]["f"]
        assert row["d"]["exact"]["f"] == row["d"]["mwpm"]["f"]
        assert row["d"]["exact"]["s"] == "ok"
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    comparison = summary["result"]["comparisons"][0]
    assert comparison["first_only"] == 0
    assert comparison["second_only"] == 0
    assert comparison["mcnemar"]["p_value"] == 1.0
    assert summary["result"]["decoders"]["exact"]["operational_failures"] < 500


def test_zero_failures_have_an_explicit_upper_bound(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        name="noiseless",
        noise={"kind": "code_capacity", "model": "bit_flip", "parameters": {"p": 0.0}},
        decoders=[{"name": "exact"}],
        comparisons=[],
        experiment={
            "shots": 1000,
            "seed": 5,
            "partition": "development",
            "stopping_rule": "fixed_shots",
        },
    )
    artifact = run_protocol(_load(path), tmp_path / "runs")
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    exact = summary["result"]["decoders"]["exact"]
    assert exact["operational_failures"] == 0
    assert exact["probability"] == 0.0
    assert exact["zero_failure_upper_bound"] is not None
    assert 0.0 < exact["zero_failure_upper_bound"] < 0.01
    report = (artifact / "report.md").read_text(encoding="utf-8")
    assert "one-sided" in report
    assert "upper bound" in report
    assert "zero_failure_upper_bound" not in report


def test_measurement_error_is_explicit_and_counted(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        name="measurement",
        noise={
            "kind": "phenomenological",
            "model": "phenomenological",
            "parameters": {
                "data_channel": {"model": "bit_flip", "p": 0.0},
            },
            "measurement_error": 0.5,
        },
    )
    artifact = run_protocol(_load(path), tmp_path / "runs")
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    exact = summary["result"]["decoders"]["exact"]
    assert summary["result"]["noise"]["kind"] == "phenomenological"
    assert summary["result"]["noise"]["measurement_error"] == 0.5
    assert exact["operational_failures"] > 0
    assert exact["decoder_failures"] == 0
    assert exact["invalid_residuals"] > 0


def test_same_seed_reproduces_outcomes(tmp_path: Path) -> None:
    protocol = _load(_write(tmp_path))
    first = run_protocol(protocol, tmp_path / "a")
    second = run_protocol(protocol, tmp_path / "b")
    assert _records(first) == _records(second)
    first_summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    second_summary = json.loads((second / "summary.json").read_text(encoding="utf-8"))
    assert first_summary["result"]["decoders"] == second_summary["result"]["decoders"]


def test_stim_surface_code_backend_records_dependency_provenance(
    tmp_path: Path,
) -> None:
    pytest.importorskip("stim")
    pytest.importorskip("pymatching")
    raw = copy.deepcopy(BASE)
    raw.update(
        {
            "name": "surface_smoke",
            "code": {
                "family": "surface_code",
                "distance": 3,
                "rounds": 2,
                "task": "memory_z",
            },
            "noise": {
                "kind": "circuit_level",
                "model": "circuit_level",
                "parameters": {
                    "p_gate": 0.008,
                    "p_measurement": 0.008,
                    "p_reset": 0.008,
                    "p_round": 0.008,
                },
            },
            "decoders": [{"name": "mwpm"}, {"name": "no_correction"}],
            "comparisons": ["mwpm:no_correction"],
            "experiment": {
                "shots": 300,
                "seed": 3,
                "partition": "development",
                "stopping_rule": "fixed_shots",
            },
        }
    )
    path = tmp_path / "stim.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=True), encoding="utf-8")
    artifact = run_protocol(_load(path), tmp_path / "runs")
    assert verify_artifact(artifact).ok
    assert (artifact / "circuit.stim").is_file()
    assert (artifact / "detector_error_model.dem").is_file()
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    result = summary["result"]
    assert result["backend"] == "stim+pymatching"
    assert result["stim_task"] == "surface_code:rotated_memory_z"
    assert result["stim_version"]
    assert result["pymatching_version"]
    assert len(result["dem_sha256"]) == 64
    assert result["decoders"]["mwpm"]["operational_failures"] < 300
    assert result["comparisons"][0]["paired"] is True


def test_incompatible_backends_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ExperimentError):
        run_protocol(
            _load(_write(tmp_path, code={"family": "steane", "rounds": 1})),
            tmp_path / "runs",
        )
    with pytest.raises(ExperimentError):
        run_protocol(
            _load(
                _write(
                    tmp_path,
                    decoders=[{"name": "exact"}],
                    comparisons=[],
                    code={"family": "repetition", "distance": 5, "rounds": 2},
                )
            ),
            tmp_path / "runs",
        )
    with pytest.raises(ProtocolError):
        _load(
            _write(
                tmp_path,
                code={
                    "family": "repetition",
                    "distance": 3,
                    "rounds": 1,
                    "task": "memory_z",
                },
                noise={
                    "kind": "circuit_level",
                    "model": "circuit_level",
                    "parameters": {"p_gate": 0.001},
                },
                decoders=[{"name": "mwpm"}],
                comparisons=[],
            )
        )


def test_unencoded_decoder_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        decoders=[{"name": "unencoded"}],
        comparisons=[],
    )
    with pytest.raises(ExperimentError):
        run_protocol(_load(path), tmp_path / "runs")


def test_report_labels_are_conservative(tmp_path: Path) -> None:
    artifact = run_protocol(_load(_write(tmp_path)), tmp_path / "runs")
    report = (artifact / "report.md").read_text(encoding="utf-8")
    assert "NOT_CLAIMED" in report
    assert "NOT_MODELED" in report
    assert "VERIFIED (integrity only)" in report
    assert "production-ready" not in report.lower()
    assert "state-of-the-art" not in report.lower()
