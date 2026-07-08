from __future__ import annotations

import numpy as np
import pytest

from quantumlab.circuit import CircuitDefinition, GatePlacement, run_circuit
from quantumlab.density import DensityMatrix
from quantumlab.exceptions import InvalidDensityMatrixError, NormalizationError
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


def test_from_statevector_is_projector() -> None:
    sv = StateVector.zero(1)
    rho = DensityMatrix.from_statevector(sv)
    assert np.allclose(rho.matrix, sv.density_matrix(), atol=1e-12)
    assert rho.purity() == pytest.approx(1.0, abs=1e-10)


def test_pure_state_entropy_zero() -> None:
    rho = DensityMatrix.from_statevector(StateVector.zero(2))
    assert rho.von_neumann_entropy() == pytest.approx(0.0, abs=1e-10)


def test_bell_partial_trace_entropy() -> None:
    result = run_circuit(_bell_circuit(), mode="density")
    reduced = result.final_density.partial_trace([0])
    assert reduced.purity() == pytest.approx(0.5, abs=1e-10)
    assert reduced.von_neumann_entropy() == pytest.approx(1.0, abs=1e-10)


def test_density_mode_matches_statevector_probabilities() -> None:
    sv_result = run_circuit(_bell_circuit())
    dm_result = run_circuit(_bell_circuit(), mode="density")
    assert np.allclose(
        sv_result.final_state.probabilities(),
        dm_result.final_density.probabilities(),
        atol=1e-12,
    )


def test_maximally_mixed() -> None:
    rho = DensityMatrix.maximally_mixed(1)
    assert rho.purity() == pytest.approx(0.5, abs=1e-10)
    assert rho.von_neumann_entropy() == pytest.approx(1.0, abs=1e-10)


def test_to_statevector_roundtrip() -> None:
    sv = StateVector.from_amplitudes(
        np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
    )
    rho = DensityMatrix.from_statevector(sv)
    recovered = rho.to_statevector()
    assert fidelity_overlap(sv, recovered) == pytest.approx(1.0, abs=1e-10)


def test_mixed_cannot_to_statevector() -> None:
    rho = DensityMatrix.maximally_mixed(1)
    with pytest.raises(NormalizationError):
        rho.to_statevector()


def test_invalid_density_raises() -> None:
    bad = np.array([[0.5, 0.0], [0.0, 0.0]], dtype=np.complex128)
    with pytest.raises(InvalidDensityMatrixError):
        DensityMatrix.from_matrix(bad, num_qubits=1)


def test_apply_unitary_matches_statevector() -> None:
    sv = StateVector.zero(1)
    sv_h = sv.apply_gate(__import__("quantumlab.gates", fromlist=["H"]).H(), [0])
    rho = DensityMatrix.from_statevector(sv)
    from quantumlab.gates import H

    rho_h = rho.apply_unitary(H(), [0])
    assert np.allclose(rho_h.probabilities(), sv_h.probabilities(), atol=1e-12)


def fidelity_overlap(a: StateVector, b: StateVector) -> float:
    return float(np.abs(np.vdot(a.amplitudes, b.amplitudes)) ** 2)
