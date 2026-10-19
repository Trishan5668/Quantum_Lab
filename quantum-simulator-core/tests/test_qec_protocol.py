from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from quantumlab.research.qec.protocol import (
    ExperimentProtocol,
    Protocol,
    ProtocolError,
    load_protocol,
    validate_experiment_protocol,
)

BASE: dict = {
    "schema_version": "2.0",
    "name": "unit_protocol",
    "research_question": "A precise question?",
    "hypothesis": "A falsifiable hypothesis.",
    "code": {"family": "repetition", "distance": 3, "rounds": 1, "task": "memory_z"},
    "noise": {
        "kind": "code_capacity",
        "model": "bit_flip",
        "parameters": {"p": 0.1},
    },
    "decoders": [{"name": "exact"}, {"name": "majority_vote"}],
    "comparisons": ["exact:majority_vote"],
    "experiment": {
        "shots": 100,
        "seed": 7,
        "partition": "development",
        "stopping_rule": "fixed_shots",
    },
    "statistics": {
        "method": "wilson",
        "confidence_level": 0.95,
        "primary_metric": "operational_failure_probability",
    },
    "resources": {"data_qubits": 3},
    "limitations": ["Synthetic test protocol."],
}


def _protocol(**updates: object) -> dict:
    raw = copy.deepcopy(BASE)
    raw.update(updates)
    return raw


def test_valid_v2_protocol_and_hash_stability() -> None:
    first = validate_experiment_protocol(_protocol())
    second = validate_experiment_protocol(_protocol())
    assert isinstance(first, ExperimentProtocol)
    assert first.config_hash == second.config_hash
    changed = validate_experiment_protocol(
        _protocol(
            noise={
                "kind": "code_capacity",
                "model": "bit_flip",
                "parameters": {"p": 0.2},
            }
        )
    )
    assert changed.config_hash != first.config_hash
    assert first.primary_decoder.name == "exact"
    assert first.to_dict()["code"]["distance"] == 3


def test_loader_records_source_hash(tmp_path: Path) -> None:
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(_protocol()), encoding="utf-8")
    protocol = load_protocol(path)
    assert isinstance(protocol, ExperimentProtocol)
    assert protocol.source_path == str(path)
    assert protocol.source_sha256 is not None
    assert len(protocol.source_sha256) == 64


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema_version": "1.0"},
        {"unknown_key": 1},
        {"code": {"family": "repetition", "distance": 4, "rounds": 1}},
        {"code": {"family": "surface_code", "distance": 2, "rounds": 1}},
        {"code": {"family": "surface_code", "distance": 4, "rounds": 1}},
        {"code": {"family": "fictional", "distance": 3, "rounds": 1}},
        {"code": {"family": "repetition", "distance": 3, "rounds": 1, "task": "teleport"}},
        {
            "decoders": [
                {"name": "exact"},
                {"name": "exact"},
            ]
        },
        {"decoders": [{"name": "oracle"}]},
        {"comparisons": ["exact:missing"]},
        {"comparisons": ["exact"]},
        {"comparisons": ["exact:exact"]},
        {
            "experiment": {
                "shots": 0,
                "seed": 1,
                "partition": "development",
                "stopping_rule": "fixed_shots",
            }
        },
        {
            "experiment": {
                "shots": 10,
                "seed": 1,
                "partition": "training",
                "stopping_rule": "fixed_shots",
            }
        },
        {
            "experiment": {
                "shots": 10,
                "seed": 1,
                "partition": "development",
                "stopping_rule": "stop_when_significant",
            }
        },
        {"statistics": {"method": "normal", "confidence_level": 0.95}},
        {"statistics": {"method": "wilson", "confidence_level": 1.0}},
        {
            "noise": {
                "kind": "code_capacity",
                "model": "bit_flip",
                "parameters": {"p": 0.1},
                "measurement_error": 0.01,
            }
        },
        {
            "noise": {
                "kind": "phenomenological",
                "model": "phenomenological",
                "parameters": {},
            }
        },
        {
            "noise": {
                "kind": "circuit_level",
                "model": "circuit_level",
                "parameters": {"p_gate": 0.01},
            }
        },
        {
            "code": {"family": "steane", "distance": None, "rounds": 1},
            "noise": {
                "kind": "circuit_level",
                "model": "circuit_level",
                "parameters": {"p_gate": 0.01},
            },
        },
    ],
)
def test_invalid_protocols_are_rejected(mutation: dict) -> None:
    with pytest.raises(ProtocolError):
        validate_experiment_protocol(_protocol(**mutation))


def test_boolean_is_not_an_integer() -> None:
    raw = _protocol()
    raw["experiment"]["shots"] = True
    with pytest.raises(ProtocolError):
        validate_experiment_protocol(raw)
    raw = _protocol()
    raw["experiment"]["seed"] = False
    with pytest.raises(ProtocolError):
        validate_experiment_protocol(raw)


def test_nonfinite_noise_is_rejected() -> None:
    raw = _protocol()
    raw["noise"]["parameters"]["p"] = float("nan")
    with pytest.raises(ProtocolError):
        validate_experiment_protocol(raw)


def test_legacy_protocol_still_loads() -> None:
    path = (
        Path(__file__).parents[1]
        / "research"
        / "qec"
        / "protocols"
        / "rq1_noise_aware_qec.yaml"
    )
    protocol = load_protocol(path)
    assert isinstance(protocol, Protocol)
    assert protocol.code_distance == 3
    assert protocol.trials == 10000


def test_legacy_protocol_rejects_non_repetition() -> None:
    raw = yaml.safe_load(
        (
            Path(__file__).parents[1]
            / "research"
            / "qec"
            / "protocols"
            / "rq1_noise_aware_qec.yaml"
        ).read_text(encoding="utf-8")
    )
    raw["code"]["distance"] = 5
    from quantumlab.research.qec.protocol import validate_protocol

    with pytest.raises(ValueError):
        validate_protocol(raw)
