from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantumlab.research.qec.code import RepetitionCode
from quantumlab.research.qec.protocol import load_protocol
from quantumlab.research.qec.runner import run_experiment
from quantumlab.research.qec.stats import summarize, wilson_interval


def test_repetition_code_stabilizers_and_syndrome() -> None:
    code = RepetitionCode()
    code.validate()
    assert code.stabilizers == ("ZZI", "IZZ")
    assert code.syndrome((True, False, False)) == (1, 0)
    assert code.correction_for_syndrome((0, 1)) == 2


def test_repetition_code_corrects_single_flips() -> None:
    code = RepetitionCode()
    for index in range(3):
        flips = tuple(position == index for position in range(3))
        syndrome = code.syndrome(flips)
        assert not code.logical_failure(flips, code.correction_for_syndrome(syndrome))


def test_repetition_code_classifies_two_flips_as_failure() -> None:
    code = RepetitionCode()
    flips = (True, True, False)
    assert code.logical_failure(flips, code.correction_for_syndrome(code.syndrome(flips)))


def test_wilson_interval_handles_zero_failures() -> None:
    low, high = wilson_interval(0, 100)
    assert low == pytest.approx(0.0)
    assert high > 0.0


def test_protocol_and_runner_write_evidence(tmp_path) -> None:
    protocol = load_protocol(
        Path(__file__).parents[1] / "research" / "qec" / "protocols" / "rq1_noise_aware_qec.yaml"
    )
    artifact_dir = run_experiment(protocol, tmp_path)
    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["trials"] == 10000
    assert summary["baseline"]["failures"] >= summary["failures"]
    assert (artifact_dir / "config.yaml").exists()
    assert len((artifact_dir / "raw_trials.jsonl").read_text(encoding="utf-8").splitlines()) == 10000
