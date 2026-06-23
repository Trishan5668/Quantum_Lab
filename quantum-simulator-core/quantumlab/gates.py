"""Exact gate matrices, complex128, NumPy only.

All gates are returned as fresh ``np.ndarray`` objects so callers cannot
mutate shared state. The CNOT convention used throughout the engine is:

    CNOT(control=0, target=1) on |c, t>  ->  |c, c xor t>

When wired into ``StateVector.apply_gate`` the qubit-index argument list
``[control, target]`` determines which physical wires those abstract
slots map to.
"""

from __future__ import annotations

from typing import TypeAlias

import numpy as np

from quantumlab.exceptions import InvalidGateError

GateMatrix: TypeAlias = np.ndarray
"""Alias for a complex128 unitary matrix of shape (2**k, 2**k)."""


_SQRT2_INV: float = 1.0 / np.sqrt(2.0)


def I() -> GateMatrix:  # noqa: E743 - mathematical name
    """2x2 identity."""
    return np.eye(2, dtype=np.complex128)


def H() -> GateMatrix:
    """Hadamard."""
    return _SQRT2_INV * np.array(
        [[1.0, 1.0], [1.0, -1.0]],
        dtype=np.complex128,
    )


def X() -> GateMatrix:
    """Pauli-X (bit flip)."""
    return np.array(
        [[0.0, 1.0], [1.0, 0.0]],
        dtype=np.complex128,
    )


def Y() -> GateMatrix:
    """Pauli-Y."""
    return np.array(
        [[0.0, -1.0j], [1.0j, 0.0]],
        dtype=np.complex128,
    )


def Z() -> GateMatrix:
    """Pauli-Z (phase flip)."""
    return np.array(
        [[1.0, 0.0], [0.0, -1.0]],
        dtype=np.complex128,
    )


def RX(theta: float) -> GateMatrix:
    """Rotation around X: exp(-i theta/2 X)."""
    c = np.cos(theta / 2.0)
    s = np.sin(theta / 2.0)
    return np.array(
        [[c, -1.0j * s], [-1.0j * s, c]],
        dtype=np.complex128,
    )


def RY(theta: float) -> GateMatrix:
    """Rotation around Y: exp(-i theta/2 Y)."""
    c = np.cos(theta / 2.0)
    s = np.sin(theta / 2.0)
    return np.array(
        [[c, -s], [s, c]],
        dtype=np.complex128,
    )


def RZ(theta: float) -> GateMatrix:
    """Rotation around Z: exp(-i theta/2 Z)."""
    e_neg = np.exp(-1.0j * theta / 2.0)
    e_pos = np.exp(1.0j * theta / 2.0)
    return np.array(
        [[e_neg, 0.0], [0.0, e_pos]],
        dtype=np.complex128,
    )


def CNOT() -> GateMatrix:
    """Controlled-NOT in the convention (control, target) on basis |c t>.

    Row/column ordering: |00>, |01>, |10>, |11>.
    """
    return np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        dtype=np.complex128,
    )


def assert_valid_gate(gate: GateMatrix, *, k_qubits: int | None = None) -> None:
    """Validate a gate matrix's shape, dtype, and unitarity.

    Raises
    ------
    InvalidGateError
        If the matrix is not a square complex128 array of size 2**k or if
        it fails the unitarity check ``U U^\\dagger ~= I``.
    """
    if not isinstance(gate, np.ndarray):
        raise InvalidGateError(
            f"gate must be a numpy.ndarray, got {type(gate).__name__}"
        )
    if gate.dtype != np.complex128:
        raise InvalidGateError(
            f"gate dtype must be complex128, got {gate.dtype}"
        )
    if gate.ndim != 2 or gate.shape[0] != gate.shape[1]:
        raise InvalidGateError(
            f"gate must be a square matrix, got shape {gate.shape}"
        )
    dim = gate.shape[0]
    if dim & (dim - 1) != 0 or dim < 2:
        raise InvalidGateError(
            f"gate dimension must be a power of two >= 2, got {dim}"
        )
    if k_qubits is not None and dim != (1 << k_qubits):
        raise InvalidGateError(
            f"gate dimension {dim} does not match {k_qubits} qubits "
            f"(expected {1 << k_qubits})"
        )
    product = gate @ gate.conj().T
    if not np.allclose(product, np.eye(dim, dtype=np.complex128), atol=1e-10):
        raise InvalidGateError("gate is not unitary (U U^dagger != I)")
