from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from quantumlab.research.qec.artifacts import verify_artifact
from quantumlab.research.qec.reproduction import (
    ReproductionError,
    ThresholdPoint,
    _analyse,
    _load_target,
    run_reproduction_target,
)
from quantumlab.research.qec.stats import summarize_with_method

TARGET: dict = {
    "name": "synthetic_reproduction",
    "reference": {"description": "Synthetic"},
    "model": {"description": "Synthetic"},
    "coarse": {
        "p": [0.004, 0.006, 0.007, 0.010],
        "shots": 1000,
        "distances": [3, 5, 7],
    },
    "refinement": {"p": [0.006, 0.007], "shots": 10000, "distances": [3, 5]},
    "acceptance": {"master_seed": 1, "threshold_band": [0.0055, 0.0085]},
    "statistics": {"confidence_level": 0.95},
}


def _point(stage: str, distance: int, p: float, shots: int, failures: int) -> ThresholdPoint:
    return ThresholdPoint(
        distance=distance,
        p=p,
        shots=shots,
        seed=1,
        failures=failures,
        summary=summarize_with_method(failures, shots, 0.95, method="wilson"),
        dem_sha256="0" * 64,
        circuit_sha256="1" * 64,
        stage=stage,
    )


def _synthetic_points() -> list[ThresholdPoint]:
    points = []
    coarse_counts = {
        (3, 0.004): 300,
        (5, 0.004): 100,
        (7, 0.004): 50,
        (3, 0.010): 100,
        (5, 0.010): 300,
        (7, 0.010): 600,
    }
    for (distance, p), failures in coarse_counts.items():
        points.append(_point("coarse", distance, p, 1000, failures))
    points.extend(
        [
            _point("refinement", 3, 0.006, 10000, 200),
            _point("refinement", 5, 0.006, 10000, 100),
            _point("refinement", 3, 0.007, 10000, 100),
            _point("refinement", 5, 0.007, 10000, 200),
        ]
    )
    return points


def test_analysis_reproduces_when_criteria_hold() -> None:
    analysis = _analyse(TARGET, _synthetic_points())
    assert analysis["status"] == "REPRODUCED"
    assert analysis["bracket"] == [0.006, 0.007]
    assert all(criterion["passed"] for criterion in analysis["criteria"])


def test_analysis_fails_when_bracket_is_outside_band() -> None:
    target = dict(TARGET)
    target["acceptance"] = {"master_seed": 1, "threshold_band": [0.0075, 0.009]}
    analysis = _analyse(target, _synthetic_points())
    assert analysis["status"] == "FAILED"
    assert not analysis["within_predeclared_band"]


def test_analysis_is_inconclusive_without_sign_change() -> None:
    points = [
        point
        for point in _synthetic_points()
        if not (point.stage == "refinement" and point.p == 0.007)
    ]
    points.extend(
        [
            _point("refinement", 3, 0.007, 10000, 150),
            _point("refinement", 5, 0.007, 10000, 100),
        ]
    )
    analysis = _analyse(TARGET, points)
    assert analysis["status"] == "INCONCLUSIVE"
    assert analysis["bracket"] is None


def test_target_validation_rejects_bad_band(tmp_path: Path) -> None:
    raw = dict(TARGET)
    raw["acceptance"] = {"master_seed": 1, "threshold_band": [0.9, 0.1]}
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ReproductionError):
        _load_target(path)


def test_full_reproduction_flow_with_synthetic_sampler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("stim")
    pytest.importorskip("pymatching")
    path = tmp_path / "target.yaml"
    path.write_text(yaml.safe_dump(TARGET), encoding="utf-8")

    rates = {
        ("coarse", 3, 0.004): 0.30,
        ("coarse", 5, 0.004): 0.10,
        ("coarse", 7, 0.004): 0.05,
        ("coarse", 3, 0.010): 0.10,
        ("coarse", 5, 0.010): 0.30,
        ("coarse", 7, 0.010): 0.60,
        ("coarse", 3, 0.006): 0.20,
        ("coarse", 5, 0.006): 0.15,
        ("coarse", 7, 0.006): 0.12,
        ("coarse", 3, 0.007): 0.24,
        ("coarse", 5, 0.007): 0.20,
        ("coarse", 7, 0.007): 0.18,
        ("refinement", 3, 0.006): 0.02,
        ("refinement", 5, 0.006): 0.01,
        ("refinement", 3, 0.007): 0.01,
        ("refinement", 5, 0.007): 0.02,
    }

    def fake_run_point(
        distance: int,
        probability: float,
        shots: int,
        master_seed: int,
        stage_code: int,
        stage: str,
    ) -> tuple[ThresholdPoint, np.ndarray]:
        rate = rates[(stage, distance, probability)]
        failures = int(round(rate * shots))
        point = _point(stage, distance, probability, shots, failures)
        return point, np.zeros(shots, dtype=np.uint8)

    monkeypatch.setattr(
        "quantumlab.research.qec.reproduction._run_point", fake_run_point
    )
    payload = run_reproduction_target(path, tmp_path / "runs")
    assert payload["status"] == "REPRODUCED"
    artifact = Path(payload["artifact_dir"])
    assert verify_artifact(artifact).ok
    assert (artifact / "outcomes.npz").is_file()
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    assert summary["analysis"]["claim_label"] == "REPRODUCED_WITHIN_DECLARED_MODEL"
    report = (artifact / "report.md").read_text(encoding="utf-8")
    assert "REPRODUCED" in report
    assert "NOT_CLAIMED" in report
