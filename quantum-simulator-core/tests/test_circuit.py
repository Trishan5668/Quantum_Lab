from __future__ import annotations

import numpy as np
import pytest

from quantumlab.circuit import (
    CircuitDefinition,
    GatePlacement,
    run_circuit,
    run_step,
)
from quantumlab.exceptions import InvalidGateError, SimulationError
from quantumlab.state import StateVector


def _bell_circuit() -> CircuitDefinition:
    return CircuitDefinition(
        num_qubits=2,
        gates=[
            GatePlacement(id="g0", gate_type="H", qubit_targets=[0], time_step=0),
            GatePlacement(
                id="g1", gate_type="CNOT", qubit_targets=[0, 1], time_step=1
            ),
        ],
    )


def test_run_circuit_bell_state() -> None:
    result = run_circuit(_bell_circuit())
    probs = result.final_state.probabilities()
    assert np.isclose(probs[0], 0.5, atol=1e-12)
    assert np.isclose(probs[3], 0.5, atol=1e-12)
    assert len(result.steps) == 2
    assert result.execution_time_ms > 0
    assert result.num_qubits == 2


def test_run_circuit_measurement_is_noop() -> None:
    circuit = CircuitDefinition(
        num_qubits=1,
        gates=[
            GatePlacement(id="g0", gate_type="H", qubit_targets=[0], time_step=0),
            GatePlacement(id="g1", gate_type="M", qubit_targets=[0], time_step=1),
        ],
    )
    result = run_circuit(circuit)
    probs = result.final_state.probabilities()
    assert np.allclose(probs, [0.5, 0.5], atol=1e-12)


def test_run_circuit_orders_by_time_step() -> None:
    circuit = CircuitDefinition(
        num_qubits=1,
        gates=[
            GatePlacement(id="g1", gate_type="X", qubit_targets=[0], time_step=1),
            GatePlacement(id="g0", gate_type="H", qubit_targets=[0], time_step=0),
        ],
    )
    result = run_circuit(circuit)
    assert result.steps[0].gate_id == "g0"
    assert result.steps[1].gate_id == "g1"


def test_run_circuit_rotation_with_theta() -> None:
    circuit = CircuitDefinition(
        num_qubits=1,
        gates=[
            GatePlacement(
                id="g0",
                gate_type="RX",
                qubit_targets=[0],
                params={"theta": float(np.pi)},
                time_step=0,
            )
        ],
    )
    result = run_circuit(circuit)
    probs = result.final_state.probabilities()
    assert np.isclose(probs[1], 1.0, atol=1e-10)


def test_run_circuit_rejects_too_many_qubits() -> None:
    with pytest.raises(SimulationError):
        run_circuit(CircuitDefinition(num_qubits=9, gates=[]))


def test_run_circuit_rejects_unknown_gate() -> None:
    bad = CircuitDefinition(
        num_qubits=1,
        gates=[
            GatePlacement(
                id="g0", gate_type="BOGUS", qubit_targets=[0], time_step=0
            )
        ],
    )
    with pytest.raises(InvalidGateError):
        run_circuit(bad)


def test_run_circuit_rotation_missing_theta() -> None:
    bad = CircuitDefinition(
        num_qubits=1,
        gates=[
            GatePlacement(id="g0", gate_type="RX", qubit_targets=[0], time_step=0)
        ],
    )
    with pytest.raises(InvalidGateError):
        run_circuit(bad)


def test_run_step_returns_structured_result() -> None:
    state = StateVector.zero(1)
    placement = GatePlacement(
        id="g0", gate_type="H", qubit_targets=[0], time_step=0
    )
    step = run_step(state, placement)
    assert step.gate_id == "g0"
    assert step.gate_type == "H"
    assert np.allclose(step.probabilities, [0.5, 0.5], atol=1e-12)
    assert np.isclose(step.state_after.probabilities().sum(), 1.0, atol=1e-12)


def test_run_circuit_to_dict_is_json_friendly() -> None:
    import json

    result = run_circuit(_bell_circuit())
    payload = result.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["num_qubits"] == 2
    assert len(payload["steps"]) == 2
