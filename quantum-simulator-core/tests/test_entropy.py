from __future__ import annotations

import pytest

from quantumlab.circuit import CircuitDefinition, GatePlacement, run_circuit
from quantumlab.density import DensityMatrix
from quantumlab.entropy import entanglement_entropy, interpret_entropy
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


def test_bell_entropy_one_bit() -> None:
    result = run_circuit(_bell_circuit(), mode="density")
    s = entanglement_entropy(result.final_density, [0])
    assert s == pytest.approx(1.0, abs=1e-10)


def test_product_state_entropy_zero() -> None:
    rho = DensityMatrix.from_statevector(StateVector.zero(2))
    s = entanglement_entropy(rho, [0])
    assert s == pytest.approx(0.0, abs=1e-10)


def test_interpret_entropy_bell() -> None:
    msg = interpret_entropy(1.0, 1)
    assert "Maximally entangled" in msg


def test_interpret_entropy_pure() -> None:
    msg = interpret_entropy(0.0, 1)
    assert "No entanglement" in msg
