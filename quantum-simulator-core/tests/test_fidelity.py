from __future__ import annotations

import numpy as np
import pytest

from quantumlab.circuit import CircuitDefinition, GatePlacement, run_circuit
from quantumlab.density import DensityMatrix
from quantumlab.fidelity import (
    bell_state_vector,
    fidelity,
    interpret_fidelity,
    target_state_fidelity,
)
from quantumlab.state import StateVector


def test_identical_pure_fidelity_one() -> None:
    sv = StateVector.zero(1)
    assert fidelity(sv, sv) == pytest.approx(1.0, abs=1e-12)


def test_orthogonal_pure_fidelity_zero() -> None:
    z = StateVector.zero(1)
    x = z.apply_gate(__import__("quantumlab.gates", fromlist=["X"]).X(), [0])
    assert fidelity(z, x) == pytest.approx(0.0, abs=1e-12)


def test_bell_self_fidelity() -> None:
    circuit = CircuitDefinition(
        num_qubits=2,
        gates=[
            GatePlacement(id="g0", gate_type="H", qubit_targets=[0], time_step=0),
            GatePlacement(
                id="g1", gate_type="CNOT", qubit_targets=[0, 1], time_step=1
            ),
        ],
    )
    result = run_circuit(circuit)
    fid, _ = target_state_fidelity(result.final_state, "bell")
    assert fid == pytest.approx(1.0, abs=1e-10)


def test_bell_vs_zero_fidelity_half() -> None:
    bell = StateVector.from_amplitudes(bell_state_vector(2))
    zero = StateVector.zero(2)
    assert fidelity(bell, zero) == pytest.approx(0.5, abs=1e-10)


def test_mixed_fidelity_bounds() -> None:
    rho = DensityMatrix.maximally_mixed(1)
    sv = StateVector.zero(1)
    fid = fidelity(rho, sv)
    assert 0.0 <= fid <= 1.0


def test_interpret_fidelity() -> None:
    assert "Excellent" in interpret_fidelity(0.995)
    assert "Good" in interpret_fidelity(0.95)
    assert "Needs improvement" in interpret_fidelity(0.5)
