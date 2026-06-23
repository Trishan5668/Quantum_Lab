from __future__ import annotations

import numpy as np
import pytest

from quantumlab.exceptions import (
    InvalidGateError,
    NormalizationError,
    QubitIndexError,
)
from quantumlab.gates import CNOT, RX, RY, RZ, H, X, Y, Z
from quantumlab.state import StateVector


def test_zero_state_initialization() -> None:
    s = StateVector.zero(3)
    assert s.num_qubits == 3
    assert s.amplitudes.shape == (8,)
    assert s.amplitudes[0] == 1.0 + 0j
    assert np.allclose(s.amplitudes[1:], 0.0, atol=1e-15)


def test_hadamard_superposition() -> None:
    state = StateVector.zero(1)
    state = state.apply_gate(H(), [0])
    assert np.allclose(state.probabilities(), [0.5, 0.5], atol=1e-10)


def test_x_flips_zero_to_one() -> None:
    state = StateVector.zero(1).apply_gate(X(), [0])
    assert np.allclose(state.probabilities(), [0.0, 1.0], atol=1e-12)


def test_z_does_not_change_zero() -> None:
    state = StateVector.zero(1).apply_gate(Z(), [0])
    assert np.allclose(state.amplitudes, [1.0, 0.0], atol=1e-15)


def test_y_on_zero_gives_i_on_one() -> None:
    state = StateVector.zero(1).apply_gate(Y(), [0])
    assert np.allclose(state.amplitudes, [0.0, 1j], atol=1e-15)


def test_rx_rotation() -> None:
    state = StateVector.zero(1)
    state = state.apply_gate(RX(np.pi), [0])
    assert np.allclose(state.probabilities(), [0.0, 1.0], atol=1e-10)


def test_ry_rotation_half_pi() -> None:
    state = StateVector.zero(1)
    state = state.apply_gate(RY(np.pi / 2.0), [0])
    assert np.allclose(state.probabilities(), [0.5, 0.5], atol=1e-12)


def test_rz_only_adds_phase() -> None:
    state = StateVector.zero(1).apply_gate(RZ(1.234), [0])
    assert np.allclose(state.probabilities(), [1.0, 0.0], atol=1e-12)


def test_cnot_entanglement() -> None:
    state = StateVector.zero(2)
    state = state.apply_gate(H(), [0])
    state = state.apply_gate(CNOT(), [0, 1])
    probs = state.probabilities()
    assert np.allclose(probs[0], 0.5, atol=1e-10)
    assert np.allclose(probs[3], 0.5, atol=1e-10)
    assert np.allclose(probs[1], 0.0, atol=1e-10)
    assert np.allclose(probs[2], 0.0, atol=1e-10)


def test_cnot_reverse_control_target() -> None:
    state = StateVector.zero(2).apply_gate(X(), [1])
    state = state.apply_gate(CNOT(), [1, 0])
    assert np.allclose(state.probabilities(), [0.0, 0.0, 0.0, 1.0], atol=1e-12)


def test_cnot_non_adjacent_qubits() -> None:
    state = StateVector.zero(3).apply_gate(X(), [0])
    state = state.apply_gate(CNOT(), [0, 2])
    probs = state.probabilities()
    expected = np.zeros(8)
    expected[0b101] = 1.0
    assert np.allclose(probs, expected, atol=1e-12)


def test_cnot_non_adjacent_reverse() -> None:
    state = StateVector.zero(3).apply_gate(X(), [2])
    state = state.apply_gate(CNOT(), [2, 0])
    probs = state.probabilities()
    expected = np.zeros(8)
    expected[0b101] = 1.0
    assert np.allclose(probs, expected, atol=1e-12)


def test_ghz_state_3_qubits() -> None:
    state = (
        StateVector.zero(3)
        .apply_gate(H(), [0])
        .apply_gate(CNOT(), [0, 1])
        .apply_gate(CNOT(), [1, 2])
    )
    probs = state.probabilities()
    expected = np.zeros(8)
    expected[0] = 0.5
    expected[7] = 0.5
    assert np.allclose(probs, expected, atol=1e-12)


def test_probabilities_sum_to_one_after_many_gates() -> None:
    state = (
        StateVector.zero(4)
        .apply_gate(H(), [0])
        .apply_gate(H(), [2])
        .apply_gate(CNOT(), [0, 3])
        .apply_gate(RX(0.7), [1])
        .apply_gate(RY(1.1), [2])
        .apply_gate(CNOT(), [3, 1])
    )
    assert np.isclose(state.probabilities().sum(), 1.0, atol=1e-12)


def test_bloch_angles_zero_state() -> None:
    s = StateVector.zero(1)
    theta, _phi = s.bloch_angles(0)
    assert np.isclose(theta, 0.0, atol=1e-12)


def test_bloch_angles_one_state() -> None:
    s = StateVector.zero(1).apply_gate(X(), [0])
    theta, _phi = s.bloch_angles(0)
    assert np.isclose(theta, np.pi, atol=1e-12)


def test_bloch_angles_plus_state() -> None:
    s = StateVector.zero(1).apply_gate(H(), [0])
    theta, phi = s.bloch_angles(0)
    assert np.isclose(theta, np.pi / 2.0, atol=1e-12)
    assert np.isclose(phi, 0.0, atol=1e-12)


def test_bloch_angles_minus_state() -> None:
    s = StateVector.zero(1).apply_gate(X(), [0]).apply_gate(H(), [0])
    theta, phi = s.bloch_angles(0)
    assert np.isclose(theta, np.pi / 2.0, atol=1e-12)
    assert np.isclose(abs(phi), np.pi, atol=1e-12)


def test_bloch_angles_plus_i_state() -> None:
    s = StateVector.zero(1).apply_gate(H(), [0]).apply_gate(RZ(np.pi / 2.0), [0])
    theta, phi = s.bloch_angles(0)
    assert np.isclose(theta, np.pi / 2.0, atol=1e-12)
    assert np.isclose(phi, np.pi / 2.0, atol=1e-12)


def test_reduced_density_matrix_of_bell_is_maximally_mixed() -> None:
    s = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    rho_q0 = s.reduced_density_matrix(0)
    expected = 0.5 * np.eye(2)
    assert np.allclose(rho_q0, expected, atol=1e-12)
    rho_q1 = s.reduced_density_matrix(1)
    assert np.allclose(rho_q1, expected, atol=1e-12)


def test_density_matrix_of_pure_state_is_rank_one() -> None:
    s = StateVector.zero(2).apply_gate(H(), [0])
    rho = s.density_matrix()
    purity = float(np.real(np.trace(rho @ rho)))
    assert np.isclose(purity, 1.0, atol=1e-12)


def test_to_dict_serializes_correctly() -> None:
    s = StateVector.zero(2).apply_gate(H(), [0])
    d = s.to_dict()
    assert d["num_qubits"] == 2
    assert d["basis_labels"] == ["|00>", "|01>", "|10>", "|11>"]
    assert len(d["amplitudes"]) == 4
    assert len(d["probabilities"]) == 4


def test_apply_gate_rejects_invalid_qubit_index() -> None:
    s = StateVector.zero(2)
    with pytest.raises(QubitIndexError):
        s.apply_gate(H(), [5])


def test_apply_gate_rejects_duplicate_targets() -> None:
    s = StateVector.zero(2)
    with pytest.raises(QubitIndexError):
        s.apply_gate(CNOT(), [0, 0])


def test_apply_gate_rejects_three_qubit_gate() -> None:
    s = StateVector.zero(3)
    bad_gate = np.eye(8, dtype=np.complex128)
    with pytest.raises(InvalidGateError):
        s.apply_gate(bad_gate, [0, 1, 2])


def test_construction_rejects_unnormalized() -> None:
    with pytest.raises(NormalizationError):
        StateVector(amplitudes=np.array([1.0, 1.0], dtype=np.complex128), num_qubits=1)


def test_purity_zero_state_is_one() -> None:
    s = StateVector.zero(1)
    assert np.isclose(s.purity(), 1.0, atol=1e-12)
