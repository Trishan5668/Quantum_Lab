"""Mathematical validation tests for QuantumLab core.

Verifies postulates of quantum mechanics: unitarity, dimensional consistency,
Born rule, density-matrix properties, and Kraus operator completeness.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quantumlab._operators import full_unitary, single_qubit_full
from quantumlab.density import DensityMatrix
from quantumlab.exceptions import SimulationError
from quantumlab.gates import CNOT, RX, RY, RZ, H, I, X, Y, Z
from quantumlab.noise import (
    AmplitudeDampingChannel,
    BitFlipChannel,
    DepolarizingChannel,
    PhaseDampingChannel,
    PhaseFlipChannel,
    T1T2NoiseModel,
)
from quantumlab.state import StateVector

_ATOL = 1e-10


def _is_unitary(u: np.ndarray, atol: float = 1e-10) -> bool:
    n = u.shape[0]
    return bool(np.allclose(u @ u.conj().T, np.eye(n), atol=atol))


def _kraus_complete(ops: list[np.ndarray], atol: float = 1e-10) -> bool:
    total = sum(op.conj().T @ op for op in ops)
    dim = ops[0].shape[0]
    return bool(np.allclose(total, np.eye(dim), atol=atol))


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_hilbert_space_dimension(n: int) -> None:
    sv = StateVector.zero(n)
    assert sv.amplitudes.shape == (2**n,)
    assert len(sv.probabilities()) == 2**n


@pytest.mark.parametrize(
    "gate",
    [I(), H(), X(), Y(), Z(), RX(0.3), RY(1.1), RZ(-0.7), CNOT()],
)
def test_gate_unitarity_udagger_u_is_identity(gate: np.ndarray) -> None:
    assert _is_unitary(gate)


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("q", [0, 1, 2])
def test_single_qubit_embedding_dimension(n: int, q: int) -> None:
    if q >= n:
        pytest.skip("qubit index out of range")
    full = single_qubit_full(H(), q, n)
    assert full.shape == (2**n, 2**n)
    assert _is_unitary(full)


@pytest.mark.parametrize("n", [2, 3, 4])
def test_two_qubit_embedding_dimension(n: int) -> None:
    full = full_unitary(CNOT(), [0, 1], n)
    assert full.shape == (2**n, 2**n)
    assert _is_unitary(full)


def test_statevector_gate_application_dimension() -> None:
    sv = StateVector.zero(3)
    out = sv.apply_gate(CNOT(), [0, 2])
    assert out.amplitudes.shape == (8,)


def test_born_rule_probabilities_sum_to_one() -> None:
    sv = (
        StateVector.zero(3)
        .apply_gate(H(), [0])
        .apply_gate(RX(0.5), [1])
        .apply_gate(CNOT(), [1, 2])
    )
    probs = sv.probabilities()
    assert np.isclose(probs.sum(), 1.0, atol=_ATOL)
    assert np.all(probs >= -1e-12)


def test_born_rule_equals_amplitude_squared() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0])
    probs = sv.probabilities()
    expected = np.abs(sv.amplitudes) ** 2
    assert np.allclose(probs, expected, atol=_ATOL)


def test_density_matrix_trace_one() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    rho = DensityMatrix.from_statevector(sv)
    assert float(np.real(np.trace(rho.matrix))) == pytest.approx(1.0, abs=_ATOL)


def test_density_matrix_hermitian() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0])
    rho = DensityMatrix.from_statevector(sv)
    assert np.allclose(rho.matrix, rho.matrix.conj().T, atol=_ATOL)


def test_density_matrix_positive_semidefinite() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    rho = DensityMatrix.from_statevector(sv)
    eigvals = np.linalg.eigvalsh(rho.matrix)
    assert np.all(eigvals >= -1e-8)


def test_pure_state_density_matrix_purity_one() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0])
    rho = DensityMatrix.from_statevector(sv)
    assert rho.purity() == pytest.approx(1.0, abs=_ATOL)


@pytest.mark.parametrize(
    "channel",
    [
        AmplitudeDampingChannel(0.2),
        PhaseDampingChannel(0.15),
        DepolarizingChannel(0.1),
        BitFlipChannel(0.05),
        PhaseFlipChannel(0.05),
    ],
)
def test_kraus_operators_complete_pos(channel) -> None:
    ops = channel.kraus_operators()
    assert _kraus_complete(ops)


def test_phase_damping_exponential_t2_coherence_decay() -> None:
    """Off-diagonal coherence must decay as exp(-t/T2) when mapped from T2."""
    sv = StateVector.from_amplitudes(
        np.array([1.0, 1.0], dtype=np.complex128) / np.sqrt(2)
    )
    rho = DensityMatrix.from_statevector(sv)
    t2_us = 50.0
    gate_time_us = 10.0
    gamma = 1.0 - math.exp(-2.0 * gate_time_us / t2_us)
    out = PhaseDampingChannel(gamma).apply(rho, 0)
    expected_coherence = 0.5 * math.exp(-gate_time_us / t2_us)
    assert abs(out.matrix[0, 1]) == pytest.approx(expected_coherence, rel=1e-6)


def test_t1t2_p_phase_uses_correct_t2_mapping() -> None:
    model = T1T2NoiseModel(t1_us=60.0, t2_us=25.0, gate_time_ns=10000.0)
    gate_time_us = 10.0
    expected = 1.0 - math.exp(-2.0 * gate_time_us / 25.0)
    assert model.p_phase == pytest.approx(expected, rel=1e-12)


def test_t1t2_rejects_unphysical_t2_greater_than_2t1() -> None:
    with pytest.raises(SimulationError, match="T2"):
        T1T2NoiseModel(t1_us=10.0, t2_us=25.0, gate_time_ns=50.0)


def test_h_on_qubit_zero_is_tensor_with_identity_on_one() -> None:
    """H on qubit 0 of 2-qubit register: verify against explicit kron(H, I)."""
    sv = StateVector.zero(2).apply_gate(H(), [0])
    expected = np.kron(H(), I()) @ StateVector.zero(2).amplitudes
    assert np.allclose(sv.amplitudes, expected, atol=_ATOL)


def test_h_on_qubit_one_is_tensor_with_identity_on_zero() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [1])
    expected = np.kron(I(), H()) @ StateVector.zero(2).amplitudes
    assert np.allclose(sv.amplitudes, expected, atol=_ATOL)


def test_cnot_truth_table_control_zero() -> None:
    """CNOT(control=0, target=1): |c,t> -> |c, c XOR t>."""
    sv = StateVector.zero(2)
    assert sv.apply_gate(CNOT(), [0, 1]).probabilities()[0] == pytest.approx(1.0, abs=_ATOL)

    sv = StateVector.zero(2).apply_gate(X(), [1])
    assert sv.apply_gate(CNOT(), [0, 1]).probabilities()[1] == pytest.approx(1.0, abs=_ATOL)


def test_cnot_truth_table_control_one() -> None:
    sv = StateVector.zero(2).apply_gate(X(), [0])
    assert sv.apply_gate(CNOT(), [0, 1]).probabilities()[3] == pytest.approx(1.0, abs=_ATOL)
