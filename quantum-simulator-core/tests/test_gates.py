from __future__ import annotations

import numpy as np
import pytest

from quantumlab.exceptions import InvalidGateError
from quantumlab.gates import CNOT, RX, RY, RZ, H, I, X, Y, Z, assert_valid_gate


def _is_unitary(u: np.ndarray, atol: float = 1e-12) -> bool:
    return bool(np.allclose(u @ u.conj().T, np.eye(u.shape[0]), atol=atol))


@pytest.mark.parametrize(
    "gate",
    [I(), H(), X(), Y(), Z(), RX(0.7), RY(1.3), RZ(-2.1), CNOT()],
)
def test_gates_are_unitary(gate: np.ndarray) -> None:
    assert _is_unitary(gate)
    assert gate.dtype == np.complex128


def test_hadamard_matrix_exact() -> None:
    expected = (1.0 / np.sqrt(2.0)) * np.array(
        [[1, 1], [1, -1]], dtype=np.complex128
    )
    assert np.allclose(H(), expected, atol=1e-15)


def test_pauli_x_squared_is_identity() -> None:
    assert np.allclose(X() @ X(), I(), atol=1e-15)


def test_pauli_y_squared_is_identity() -> None:
    assert np.allclose(Y() @ Y(), I(), atol=1e-15)


def test_pauli_z_squared_is_identity() -> None:
    assert np.allclose(Z() @ Z(), I(), atol=1e-15)


def test_pauli_anticommutators() -> None:
    assert np.allclose(X() @ Y() + Y() @ X(), np.zeros((2, 2)), atol=1e-15)
    assert np.allclose(Y() @ Z() + Z() @ Y(), np.zeros((2, 2)), atol=1e-15)
    assert np.allclose(X() @ Z() + Z() @ X(), np.zeros((2, 2)), atol=1e-15)


def test_rotation_identity_at_zero() -> None:
    assert np.allclose(RX(0.0), I(), atol=1e-15)
    assert np.allclose(RY(0.0), I(), atol=1e-15)
    assert np.allclose(RZ(0.0), I(), atol=1e-15)


def test_rx_pi_is_minus_i_x() -> None:
    assert np.allclose(RX(np.pi), -1j * X(), atol=1e-12)


def test_ry_pi_is_minus_i_y() -> None:
    assert np.allclose(RY(np.pi), -1j * Y(), atol=1e-12)


def test_rz_pi_is_minus_i_z() -> None:
    assert np.allclose(RZ(np.pi), -1j * Z(), atol=1e-12)


def test_cnot_is_involution() -> None:
    assert np.allclose(CNOT() @ CNOT(), np.eye(4), atol=1e-15)


def test_cnot_matrix_layout() -> None:
    expected = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        dtype=np.complex128,
    )
    assert np.allclose(CNOT(), expected, atol=1e-15)


def test_assert_valid_gate_rejects_non_unitary() -> None:
    bad = np.array([[1, 1], [0, 1]], dtype=np.complex128)
    with pytest.raises(InvalidGateError):
        assert_valid_gate(bad)


def test_assert_valid_gate_rejects_wrong_dtype() -> None:
    with pytest.raises(InvalidGateError):
        assert_valid_gate(np.eye(2, dtype=np.float64))
