"""Shared full Hilbert-space operator construction via ``numpy.kron``.

Both :class:`~quantumlab.state.StateVector` and
:class:`~quantumlab.density.DensityMatrix` use these helpers so gate
placement is identical across simulation modes.
"""

from __future__ import annotations

from functools import reduce
from typing import cast

import numpy as np

from quantumlab.exceptions import QubitIndexError
from quantumlab.gates import GateMatrix


def i2() -> np.ndarray:
    return np.eye(2, dtype=np.complex128)


def kron_chain(factors: list[np.ndarray]) -> np.ndarray:
    """Reduce a list of 2x2 matrices into their full Kronecker product."""
    return reduce(np.kron, factors)


def swap_4x4() -> np.ndarray:
    return np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.complex128,
    )


def adjacent_swap_full(q: int, num_qubits: int) -> np.ndarray:
    """Build the SWAP operator on qubits (q, q+1) over the full Hilbert space."""
    if q < 0 or q + 1 >= num_qubits:
        raise QubitIndexError(
            f"adjacent swap position {q} out of range for {num_qubits} qubits"
        )
    factors: list[np.ndarray] = []
    if q > 0:
        factors.append(np.eye(1 << q, dtype=np.complex128))
    factors.append(swap_4x4())
    if num_qubits - q - 2 > 0:
        factors.append(np.eye(1 << (num_qubits - q - 2), dtype=np.complex128))
    return kron_chain(factors)


def swap_qubits_full(i: int, j: int, num_qubits: int) -> np.ndarray:
    """Operator swapping qubit positions ``i`` and ``j`` in an n-qubit register."""
    if i == j:
        return np.eye(1 << num_qubits, dtype=np.complex128)
    lo, hi = (i, j) if i < j else (j, i)
    op = np.eye(1 << num_qubits, dtype=np.complex128)
    for k in range(hi - 1, lo, -1):
        op = adjacent_swap_full(k, num_qubits) @ op
    op = adjacent_swap_full(lo, num_qubits) @ op
    for k in range(lo + 1, hi):
        op = adjacent_swap_full(k, num_qubits) @ op
    return op


def single_qubit_full(gate: GateMatrix, q: int, num_qubits: int) -> np.ndarray:
    factors: list[np.ndarray] = []
    for i in range(num_qubits):
        factors.append(gate if i == q else i2())
    return kron_chain(factors)


def two_qubit_full(
    gate: GateMatrix, q0: int, q1: int, num_qubits: int
) -> np.ndarray:
    """Apply a 4x4 gate on logical qubits (q0, q1) of an n-qubit register."""
    if q0 == q1:
        raise QubitIndexError(
            f"two-qubit gate cannot target the same qubit twice: {q0}"
        )

    factors: list[np.ndarray] = [gate]
    for _ in range(num_qubits - 2):
        factors.append(i2())
    embedded = kron_chain(factors)

    s0 = swap_qubits_full(0, q0, num_qubits)
    if q0 == 0:
        q1_after = q1
    elif q1 == 0:
        q1_after = q0
    else:
        q1_after = q1
    s1 = swap_qubits_full(1, q1_after, num_qubits)

    perm = s1 @ s0
    return cast(np.ndarray, perm.conj().T @ embedded @ perm)


def embed_kraus(kraus: GateMatrix, qubit: int, num_qubits: int) -> np.ndarray:
    """Embed a single-qubit Kraus operator on ``qubit`` via Kronecker products."""
    factors: list[np.ndarray] = []
    for i in range(num_qubits):
        factors.append(kraus if i == qubit else i2())
    return kron_chain(factors)


def full_unitary(
    gate: GateMatrix, target_qubits: list[int], num_qubits: int
) -> np.ndarray:
    """Build the full-space unitary for ``gate`` on ``target_qubits``."""
    if len(target_qubits) == 1:
        return single_qubit_full(gate, target_qubits[0], num_qubits)
    return two_qubit_full(
        gate, target_qubits[0], target_qubits[1], num_qubits
    )
