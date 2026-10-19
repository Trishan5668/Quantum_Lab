from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from quantumlab.research.qec.artifacts import verify_artifact
from quantumlab.research.qec.calibration import (
    NOMINAL,
    PROFILES,
    NoiseProfile,
    _cell_summary,
    _seed,
    run_calibration_study,
    run_generalization_study,
)


def test_cell_summary_paired_counts() -> None:
    first = np.array([1, 1, 0, 0], dtype=np.uint8)
    second = np.array([1, 0, 0, 0], dtype=np.uint8)
    summary = _cell_summary(first, second, seed=5)
    assert summary["first_failures"] == 2
    assert summary["second_failures"] == 1
    assert summary["both_failure"] == 1
    assert summary["first_only"] == 1
    assert summary["second_only"] == 0
    assert summary["both_success"] == 2
    assert summary["relative_excess"] == 1.0
    assert summary["difference_first_minus_second"] == 0.25
    assert summary["mcnemar"]["discordant"] == 1


def test_cell_summary_zero_oracle_is_undefined_not_zero() -> None:
    summary = _cell_summary(
        np.array([0, 0], dtype=np.uint8), np.array([0, 0], dtype=np.uint8), seed=1
    )
    assert summary["relative_excess"] is None
    assert summary["zero_failure_note"] is not None


def test_profile_seeds_are_distinct() -> None:
    measurement = NoiseProfile("measurement_heavy", 0.002, 0.020)
    gate = NoiseProfile("gate_heavy", 0.020, 0.002)
    seeds = {_seed(3101, 5, profile, 0) for profile in PROFILES}
    assert len(seeds) == len(PROFILES)
    assert _seed(3101, 5, measurement, 0) != _seed(3101, 5, gate, 0)


@pytest.mark.skipif(
    importlib.util.find_spec("stim") is None
    or importlib.util.find_spec("pymatching") is None,
    reason="stim/pymatching not installed",
)
def test_calibration_study_smoke(tmp_path: Path) -> None:
    payload = run_calibration_study(
        tmp_path,
        phase3_shots=1000,
        calibration_shots=300,
        heldout_shots=1000,
        grid=(0.002, 0.010, 0.020),
    )
    assert payload["status"] in {"PROMOTED", "REJECTED", "INCONCLUSIVE"}
    artifact = Path(payload["artifact_dir"])
    assert verify_artifact(artifact).ok
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    assert "control_d3" in summary["phase3"]["cells"]
    assert len(summary["phase4"]["gates"]) == 5
    assert summary["claim_labels"]["ai_assistance"] == "NOT_USED"
    assert "production-ready" not in (artifact / "report.md").read_text(
        encoding="utf-8"
    ).lower()


@pytest.mark.skipif(
    importlib.util.find_spec("stim") is None
    or importlib.util.find_spec("pymatching") is None,
    reason="stim/pymatching not installed",
)
def test_generalization_study_smoke(tmp_path: Path) -> None:
    payload = run_generalization_study(
        tmp_path,
        calibration_shots=300,
        heldout_shots=1000,
        grid=(0.004, 0.012, 0.025),
    )
    assert payload["status"] in {"PROMOTED_EXPLORATORY", "REJECTED", "INCONCLUSIVE"}
    artifact = Path(payload["artifact_dir"])
    assert verify_artifact(artifact).ok
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    assert summary["claim_labels"]["default_decoder_change"] is False
    assert summary["claim_labels"]["exploratory"] is True
    assert NOMINAL.p_gate == 0.010
