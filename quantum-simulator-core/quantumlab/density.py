"""Density-matrix representation for pure and mixed quantum states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from quantumlab._operators import full_unitary
from quantumlab.exceptions import (
    InvalidDensityMatrixError,
    InvalidGateError,
    NormalizationError,
    QubitIndexError,
)
from quantumlab.gates import GateMatrix, assert_valid_gate

if TYPE_CHECKING:
    from quantumlab.state import StateVector

_TRACE_TOL: float = 1e-8
_HERM_TOL: float = 1e-8
_PSD_TOL: float = 1e-8
_PURE_TOL: float = 1e-9


@dataclass
class DensityMatrix:
    """Mixed-state density operator rho of shape (2**n, 2**n), complex128."""

    matrix: np.ndarray
    num_qubits: int

    def __post_init__(self) -> None:
        if self.num_qubits < 1:
            raise QubitIndexError(
                f"num_qubits must be >= 1, got {self.num_qubits}"
            )
        expected = 1 << self.num_qubits
        if self.matrix.shape != (expected, expected):
            raise InvalidDensityMatrixError(
                f"density matrix shape {self.matrix.shape} does not match "
                f"{self.num_qubits} qubits (expected ({expected}, {expected}))"
            )
        if self.matrix.dtype != np.complex128:
            self.matrix = self.matrix.astype(np.complex128)
        self.validate()

    @classmethod
    def from_statevector(cls, state: StateVector) -> DensityMatrix:
        """Construct rho = |psi><psi| from a pure state vector."""
        psi = state.amplitudes.reshape(-1, 1)
        return cls(matrix=psi @ psi.conj().T, num_qubits=state.num_qubits)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray, num_qubits: int) -> DensityMatrix:
        mat = np.asarray(matrix, dtype=np.complex128)
        return cls(matrix=mat, num_qubits=num_qubits)

    @classmethod
    def maximally_mixed(cls, num_qubits: int) -> DensityMatrix:
        dim = 1 << num_qubits
        return cls(
            matrix=np.eye(dim, dtype=np.complex128) / dim,
            num_qubits=num_qubits,
        )

    def validate(self) -> None:
        """Ensure Hermiticity, trace unity, and positive semidefiniteness."""
        trace = float(np.real(np.trace(self.matrix)))
        if abs(trace - 1.0) > _TRACE_TOL:
            raise InvalidDensityMatrixError(
                f"density matrix trace must be 1, got {trace}"
            )
        if not np.allclose(self.matrix, self.matrix.conj().T, atol=_HERM_TOL):
            raise InvalidDensityMatrixError("density matrix is not Hermitian")
        eigvals = np.linalg.eigvalsh(self.matrix)
        if float(np.min(eigvals)) < -_PSD_TOL:
            raise InvalidDensityMatrixError(
                f"density matrix is not positive semidefinite "
                f"(min eigenvalue {float(np.min(eigvals))})"
            )

    def apply_unitary(
        self, gate: GateMatrix, target_qubits: list[int]
    ) -> DensityMatrix:
        """Return rho' = U rho U^dagger."""
        k = len(target_qubits)
        if k == 0:
            raise QubitIndexError("target_qubits must not be empty")
        if k > 2:
            raise InvalidGateError(
                f"gates with more than two target qubits are not supported "
                f"(got k={k})"
            )
        for q in target_qubits:
            if not (0 <= q < self.num_qubits):
                raise QubitIndexError(
                    f"qubit index {q} out of range for {self.num_qubits} qubits"
                )
        if len(set(target_qubits)) != k:
            raise QubitIndexError(
                f"target_qubits must be distinct, got {target_qubits}"
            )
        assert_valid_gate(gate, k_qubits=k)
        u = full_unitary(gate, target_qubits, self.num_qubits)
        new_rho = u @ self.matrix @ u.conj().T
        return DensityMatrix(matrix=new_rho, num_qubits=self.num_qubits)

    def partial_trace(self, keep_qubits: list[int]) -> DensityMatrix:
        """Trace out all qubits not listed in ``keep_qubits``."""
        if not keep_qubits:
            raise QubitIndexError("keep_qubits must not be empty")
        n = self.num_qubits
        keep = sorted(set(keep_qubits))
        for q in keep:
            if not (0 <= q < n):
                raise QubitIndexError(
                    f"qubit index {q} out of range for {n} qubits"
                )
        trace_out = [q for q in range(n) if q not in keep]
        dim_keep = 1 << len(keep)
        rho_red = np.zeros((dim_keep, dim_keep), dtype=np.complex128)

        def split_index(idx: int) -> tuple[int, int]:
            bits = [(idx >> (n - 1 - q)) & 1 for q in range(n)]
            keep_bits = [bits[q] for q in keep]
            trace_bits = [bits[q] for q in trace_out]
            keep_idx = sum(
                b << (len(keep) - 1 - i) for i, b in enumerate(keep_bits)
            )
            trace_idx = sum(
                b << (len(trace_out) - 1 - i) for i, b in enumerate(trace_bits)
            )
            return keep_idx, trace_idx

        full_dim = 1 << n
        for i in range(full_dim):
            for j in range(full_dim):
                ki, ti = split_index(i)
                kj, tj = split_index(j)
                if ti == tj:
                    rho_red[ki, kj] += self.matrix[i, j]

        return DensityMatrix(matrix=rho_red, num_qubits=len(keep))

    def von_neumann_entropy(self) -> float:
        """Return S(rho) = -Tr(rho log2 rho) in bits."""
        eigvals = np.linalg.eigvalsh(self.matrix)
        entropy = 0.0
        for ev in eigvals:
            if ev > _PSD_TOL:
                entropy -= float(ev * np.log2(ev))
        return entropy

    def purity(self) -> float:
        """Return Tr(rho^2)."""
        return float(np.real(np.trace(self.matrix @ self.matrix)))

    def probabilities(self) -> np.ndarray:
        """Return Born-rule probabilities diag(rho)."""
        probs = np.real(np.diag(self.matrix))
        return cast(np.ndarray, probs.astype(np.float64))

    def is_pure(self) -> bool:
        return self.purity() > 1.0 - _PURE_TOL

    def to_statevector(self) -> StateVector:
        """Extract a pure-state vector when purity is approximately 1."""
        from quantumlab.state import StateVector

        if not self.is_pure():
            raise NormalizationError(
                "cannot convert mixed density matrix to a pure state vector"
            )
        eigvals, eigvecs = np.linalg.eigh(self.matrix)
        idx = int(np.argmax(eigvals))
        psi = eigvecs[:, idx]
        if np.abs(psi[0]) > _PSD_TOL:
            phase = psi[0] / np.abs(psi[0])
        else:
            nonzero = np.where(np.abs(psi) > _PSD_TOL)[0]
            if len(nonzero) == 0:
                raise NormalizationError("density matrix has no support")
            phase = psi[nonzero[0]] / np.abs(psi[nonzero[0]])
        psi = psi / phase
        return StateVector.from_amplitudes(psi)

    def basis_label(self, index: int) -> str:
        if not (0 <= index < (1 << self.num_qubits)):
            raise QubitIndexError(
                f"basis index {index} out of range for {self.num_qubits} qubits"
            )
        bits = format(index, f"0{self.num_qubits}b")
        return f"|{bits}>"

    def to_dict(self) -> dict[str, Any]:
        real = [[float(np.real(self.matrix[i, j])) for j in range(self.matrix.shape[1])]
                for i in range(self.matrix.shape[0])]
        imag = [[float(np.imag(self.matrix[i, j])) for j in range(self.matrix.shape[1])]
                for i in range(self.matrix.shape[0])]
        probs = self.probabilities()
        result: dict[str, Any] = {
            "num_qubits": self.num_qubits,
            "dim": self.matrix.shape[0],
            "real": real,
            "imag": imag,
            "probabilities": [float(p) for p in probs],
            "purity": self.purity(),
            "basis_labels": [
                self.basis_label(i) for i in range(1 << self.num_qubits)
            ],
        }
        if self.is_pure():
            sv = self.to_statevector()
            result["amplitudes"] = sv.to_dict()["amplitudes"]
        return result
