from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantumlab.research.qec.validation import (
    _check_analytic_repetition,
    _check_code_parameters,
    _check_exact_decoder_all_syndromes,
    _check_exact_vs_mwpm,
    _check_intervals,
    _check_pauli_products,
    run_validation,
)


def test_analytic_checks_pass() -> None:
    for check in (
        _check_pauli_products(),
        _check_code_parameters(),
        _check_exact_decoder_all_syndromes(),
        _check_exact_vs_mwpm(),
        _check_analytic_repetition(),
        _check_intervals(),
    ):
        assert check.status in {"PASS", "BLOCKED"}, check.to_dict()


def test_full_validation_report(tmp_path: Path) -> None:
    pytest.importorskip("stim")
    pytest.importorskip("pymatching")
    payload = run_validation(tmp_path)
    assert payload["overall_status"].startswith("PASS")
    assert len(payload["checks"]) == 8
    assert all(
        check["status"] in {"PASS", "BLOCKED"} for check in payload["checks"]
    )
    assert "external replication" in payload["independence_level"].lower()
    assert (tmp_path / "independent_validation.json").is_file()
    assert (tmp_path / "independent_validation.sha256").is_file()
    assert (tmp_path / "independent_validation.md").is_file()
    stored = json.loads(
        (tmp_path / "independent_validation.json").read_text(encoding="utf-8")
    )
    assert stored["overall_status"] == payload["overall_status"]
