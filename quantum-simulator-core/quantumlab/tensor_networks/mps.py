"""Matrix product states with explicit truncation and no implicit full-state expansion.

Site order follows QuantumLab's big-endian convention: site 0 is the most
significant qubit in a computational-basis label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from quantumlab.exceptions import MPSMemoryError, MPSNumericalError, MPSShapeError
from quantumlab.gates import GateMatrix, assert_valid_gate


@dataclass(frozen=True)
class MPSConfig:
    max_bond_dimension: int = 256
    truncation_cutoff: float = 1e-10
    relative_cutoff: float = 0.0
    max_discarded_weight: float | None = None
    memory_limit_bytes: int = 1_073_741_824

    def __post_init__(self) -> None:
        if self.max_bond_dimension < 1 or self.truncation_cutoff < 0 or self.relative_cutoff < 0:
            raise ValueError("MPS truncation settings must be non-negative and max_bond_dimension >= 1")


@dataclass(frozen=True)
class TruncationEvent:
    bond: int
    original_dimension: int
    retained_dimension: int
    discarded_weight: float
    cutoff: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "bond": self.bond,
            "original_dimension": self.original_dimension,
            "retained_dimension": self.retained_dimension,
            "discarded_weight": self.discarded_weight,
            "cutoff": self.cutoff,
        }


@dataclass
class MPS:
    """Open-boundary MPS, with tensors shaped ``(left_bond, physical, right_bond)``."""

    tensors: list[np.ndarray]
    config: MPSConfig = field(default_factory=MPSConfig)
    canonical_form: Literal["none", "left", "right", "mixed"] = "none"
    orthogonality_center: int | None = None
    truncation_history: list[TruncationEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.tensors = [np.asarray(t, dtype=np.complex128).copy() for t in self.tensors]
        self.validate()
        self._ensure_memory_safe()

    @classmethod
    def zero(cls, num_qubits: int, config: MPSConfig | None = None) -> MPS:
        if num_qubits < 1:
            raise MPSShapeError("num_qubits must be >= 1")
        tensors = [np.array([[[1.0], [0.0]]], dtype=np.complex128) for _ in range(num_qubits)]
        return cls(tensors, config or MPSConfig(), canonical_form="right", orthogonality_center=0)

    @classmethod
    def basis(cls, bits: str, config: MPSConfig | None = None) -> MPS:
        if not bits or any(bit not in "01" for bit in bits):
            raise MPSShapeError("basis state must be a non-empty binary string")
        tensors = []
        for bit in bits:
            tensor = np.zeros((1, 2, 1), dtype=np.complex128)
            tensor[0, int(bit), 0] = 1.0
            tensors.append(tensor)
        return cls(tensors, config or MPSConfig(), canonical_form="right", orthogonality_center=0)

    @classmethod
    def product_state(cls, states: list[np.ndarray], config: MPSConfig | None = None) -> MPS:
        tensors: list[np.ndarray] = []
        for state in states:
            vector = np.asarray(state, dtype=np.complex128).reshape(-1)
            if vector.shape != (2,) or not np.isclose(np.vdot(vector, vector).real, 1.0, atol=1e-10):
                raise MPSShapeError("each product-state factor must be a normalized length-2 vector")
            tensors.append(vector.reshape(1, 2, 1))
        return cls(tensors, config or MPSConfig(), canonical_form="right", orthogonality_center=0)

    @classmethod
    def from_statevector(cls, amplitudes: np.ndarray, config: MPSConfig | None = None) -> MPS:
        vector = np.asarray(amplitudes, dtype=np.complex128).reshape(-1)
        if vector.size < 2 or vector.size & (vector.size - 1):
            raise MPSShapeError("statevector length must be a power of two >= 2")
        norm = float(np.vdot(vector, vector).real)
        if not np.isclose(norm, 1.0, atol=1e-9):
            raise MPSNumericalError(f"statevector is not normalized (norm squared={norm})")
        n = vector.size.bit_length() - 1
        cfg = config or MPSConfig()
        if vector.nbytes > cfg.memory_limit_bytes:
            raise MPSMemoryError("statevector conversion exceeds configured MPS memory limit")
        remaining = vector.reshape(1, -1)
        tensors: list[np.ndarray] = []
        history: list[TruncationEvent] = []
        left_dim = 1
        for site in range(n - 1):
            matrix = remaining.reshape(left_dim * 2, -1)
            u, s, vh = np.linalg.svd(matrix, full_matrices=False)
            keep, event = cls._truncate_singular_values(s, cfg, site)
            history.append(event)
            tensors.append(u[:, :keep].reshape(left_dim, 2, keep))
            remaining = s[:keep, None] * vh[:keep, :]
            left_dim = keep
        tensors.append(remaining.reshape(left_dim, 2, 1))
        return cls(tensors, cfg, canonical_form="left", orthogonality_center=n - 1, truncation_history=history)

    @staticmethod
    def _truncate_singular_values(s: np.ndarray, cfg: MPSConfig, bond: int) -> tuple[int, TruncationEvent]:
        if s.size == 0 or not np.all(np.isfinite(s)):
            raise MPSNumericalError("SVD produced invalid singular values")
        threshold = max(cfg.truncation_cutoff, cfg.relative_cutoff * float(s[0]))
        keep = min(cfg.max_bond_dimension, int(np.count_nonzero(s > threshold)))
        keep = max(1, keep)
        if cfg.max_discarded_weight is not None:
            total = float(np.sum(s * s))
            while keep < s.size and float(np.sum(s[keep:] ** 2)) / total > cfg.max_discarded_weight:
                keep += 1
            keep = min(keep, cfg.max_bond_dimension)
        discarded = float(np.sum(s[keep:] ** 2))
        return keep, TruncationEvent(bond, int(s.size), keep, discarded, threshold)

    @property
    def num_qubits(self) -> int:
        return len(self.tensors)

    @property
    def bond_dimensions(self) -> list[int]:
        return [int(t.shape[2]) for t in self.tensors[:-1]]

    @property
    def max_bond_dimension(self) -> int:
        return max(self.bond_dimensions, default=1)

    @property
    def parameter_count(self) -> int:
        return sum(int(t.size) for t in self.tensors)

    @property
    def estimated_memory_bytes(self) -> int:
        return sum(int(t.nbytes) for t in self.tensors)

    @property
    def cumulative_truncation_error(self) -> float:
        return float(sum(event.discarded_weight for event in self.truncation_history))

    def validate(self) -> None:
        if not self.tensors:
            raise MPSShapeError("an MPS needs at least one site")
        for index, tensor in enumerate(self.tensors):
            if tensor.ndim != 3 or tensor.shape[1] != 2:
                raise MPSShapeError(f"tensor {index} must have shape (left, 2, right), got {tensor.shape}")
            if tensor.shape[0] < 1 or tensor.shape[2] < 1:
                raise MPSShapeError(f"tensor {index} has a zero bond dimension")
            if index and tensor.shape[0] != self.tensors[index - 1].shape[2]:
                raise MPSShapeError(f"bond mismatch between tensors {index - 1} and {index}")
        if self.tensors[0].shape[0] != 1 or self.tensors[-1].shape[2] != 1:
            raise MPSShapeError("MPS must have open boundary dimensions of one")

    def _ensure_memory_safe(self) -> None:
        if self.estimated_memory_bytes > self.config.memory_limit_bytes:
            raise MPSMemoryError("MPS tensors exceed configured memory limit")

    def copy(self) -> MPS:
        return MPS([t.copy() for t in self.tensors], self.config, self.canonical_form, self.orthogonality_center, list(self.truncation_history))

    def norm(self) -> float:
        env = np.ones((1, 1), dtype=np.complex128)
        for tensor in self.tensors:
            env = np.einsum("ab,asc,bsd->cd", env, tensor.conj(), tensor, optimize=True)
        return float(np.sqrt(max(0.0, env[0, 0].real)))

    def normalize(self) -> MPS:
        norm = self.norm()
        if norm <= 0 or not np.isfinite(norm):
            raise MPSNumericalError("cannot normalize an MPS with zero or non-finite norm")
        self.tensors[0] /= norm
        return self

    def left_canonicalize(self) -> float:
        for site in range(self.num_qubits - 1):
            tensor = self.tensors[site]
            left, _, right = tensor.shape
            q, r = np.linalg.qr(tensor.reshape(left * 2, right), mode="reduced")
            self.tensors[site] = q.reshape(left, 2, q.shape[1])
            self.tensors[site + 1] = np.einsum("ab,bcd->acd", r, self.tensors[site + 1], optimize=True)
        self.canonical_form, self.orthogonality_center = "left", self.num_qubits - 1
        return self.canonical_residual("left")

    def right_canonicalize(self) -> float:
        for site in range(self.num_qubits - 1, 0, -1):
            tensor = self.tensors[site]
            left, _, right = tensor.shape
            q, r = np.linalg.qr(tensor.reshape(left, 2 * right).T, mode="reduced")
            self.tensors[site] = q.T.reshape(q.shape[1], 2, right)
            self.tensors[site - 1] = np.einsum("asb,bc->asc", self.tensors[site - 1], r.T, optimize=True)
        self.canonical_form, self.orthogonality_center = "right", 0
        return self.canonical_residual("right")

    def mixed_canonicalize(self, center: int) -> float:
        if not 0 <= center < self.num_qubits:
            raise MPSShapeError(f"center {center} is outside the MPS")
        self.right_canonicalize()
        for site in range(center):
            tensor = self.tensors[site]
            left, _, right = tensor.shape
            q, r = np.linalg.qr(tensor.reshape(left * 2, right), mode="reduced")
            self.tensors[site] = q.reshape(left, 2, q.shape[1])
            self.tensors[site + 1] = np.einsum("ab,bcd->acd", r, self.tensors[site + 1], optimize=True)
        self.canonical_form, self.orthogonality_center = "mixed", center
        return max(self.canonical_residual("left", center), self.canonical_residual("right", center))

    def canonical_residual(self, direction: Literal["left", "right"], center: int | None = None) -> float:
        if direction == "left":
            stop = self.num_qubits - 1 if center is None else center
            tensors = self.tensors[:stop]
            return max((float(np.linalg.norm(t.reshape(-1, t.shape[2]).conj().T @ t.reshape(-1, t.shape[2]) - np.eye(t.shape[2]))) for t in tensors), default=0.0)
        start = 1 if center is None else center + 1
        tensors = self.tensors[start:]
        return max((float(np.linalg.norm(t.reshape(t.shape[0], -1) @ t.reshape(t.shape[0], -1).conj().T - np.eye(t.shape[0]))) for t in tensors), default=0.0)

    def apply_one_site_gate(self, gate: GateMatrix, site: int) -> MPS:
        if not 0 <= site < self.num_qubits:
            raise MPSShapeError(f"site {site} is outside the MPS")
        assert_valid_gate(gate, k_qubits=1)
        self.tensors[site] = np.einsum("ab,lbr->lar", gate, self.tensors[site], optimize=True)
        self.canonical_form, self.orthogonality_center = "none", None
        return self

    def apply_two_site_gate(self, gate: GateMatrix, left_site: int) -> MPS:
        if not 0 <= left_site < self.num_qubits - 1:
            raise MPSShapeError("two-site gate must start at an existing adjacent bond")
        assert_valid_gate(gate, k_qubits=2)
        a, b = self.tensors[left_site], self.tensors[left_site + 1]
        theta = np.einsum("lsr,rtu->lstu", a, b, optimize=True)
        transformed = np.einsum("abij,lijr->labr", gate.reshape(2, 2, 2, 2), theta, optimize=True)
        left, _, _, right = transformed.shape
        u, s, vh = np.linalg.svd(transformed.reshape(left * 2, 2 * right), full_matrices=False)
        keep, event = self._truncate_singular_values(s, self.config, left_site)
        self.truncation_history.append(event)
        self.tensors[left_site] = u[:, :keep].reshape(left, 2, keep)
        self.tensors[left_site + 1] = (s[:keep, None] * vh[:keep, :]).reshape(keep, 2, right)
        self._ensure_memory_safe()
        self.canonical_form, self.orthogonality_center = "mixed", left_site + 1
        return self

    def apply_gate(self, gate: GateMatrix, targets: list[int]) -> MPS:
        if len(targets) == 1:
            return self.apply_one_site_gate(gate, targets[0])
        if len(targets) != 2 or len(set(targets)) != 2:
            raise MPSShapeError("MPS supports one- and two-site gates on distinct targets")
        first, second = targets
        if not (0 <= first < self.num_qubits and 0 <= second < self.num_qubits):
            raise MPSShapeError("gate target is outside the MPS")
        if first > second:
            # Convert a gate ordered (second, first) into physical ascending site order.
            swap = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)
            gate = swap @ gate @ swap
            first, second = second, first
        swaps: list[int] = []
        for site in range(second - 1, first, -1):
            self.apply_two_site_gate(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128), site)
            swaps.append(site)
        self.apply_two_site_gate(gate, first)
        for site in reversed(swaps):
            self.apply_two_site_gate(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128), site)
        return self

    def reduced_density_matrix(self, start: int, length: int = 1) -> np.ndarray:
        if length < 1 or start < 0 or start + length > self.num_qubits:
            raise MPSShapeError("requested subsystem is outside the MPS")
        if length > 10:
            raise MPSMemoryError("reduced density matrices are limited to 10 contiguous qubits")
        left_env = np.ones((1, 1), dtype=np.complex128)
        for tensor in self.tensors[:start]:
            left_env = np.einsum("ab,asc,bsd->cd", left_env, tensor.conj(), tensor, optimize=True)
        right_env = np.ones((1, 1), dtype=np.complex128)
        for tensor in reversed(self.tensors[start + length:]):
            right_env = np.einsum("asc,bsd,cd->ab", tensor.conj(), tensor, right_env, optimize=True)
        block = self.tensors[start]
        for tensor in self.tensors[start + 1:start + length]:
            block = np.tensordot(block, tensor, axes=([-1], [0]))
        dim = 1 << length
        block = block.reshape(block.shape[0], dim, block.shape[-1])
        rho = np.einsum("ab,axi,byj,ji->xy", left_env, block, block.conj(), right_env, optimize=True)
        return (rho + rho.conj().T) / 2

    def expectation_pauli(self, operators: dict[int, str]) -> float:
        matrices = {
            "I": np.eye(2, dtype=np.complex128), "X": np.array([[0, 1], [1, 0]], dtype=np.complex128),
            "Y": np.array([[0, -1j], [1j, 0]], dtype=np.complex128), "Z": np.diag([1, -1]).astype(np.complex128),
        }
        env = np.ones((1, 1), dtype=np.complex128)
        for site, tensor in enumerate(self.tensors):
            op = matrices[operators.get(site, "I").upper()]
            env = np.einsum("ab,asc,st,btd->cd", env, tensor.conj(), op, tensor, optimize=True)
        value = env[0, 0]
        if abs(value.imag) > 1e-8:
            raise MPSNumericalError(f"Hermitian expectation has imaginary residual {value.imag}")
        return float(value.real)

    def entanglement_entropy(self, bond: int, alpha: float = 1.0) -> float:
        if not 0 <= bond < self.num_qubits - 1:
            raise MPSShapeError("bond must lie between adjacent sites")
        copy = self.copy()
        copy.mixed_canonicalize(bond)
        theta = np.einsum("lsr,rtu->lstu", copy.tensors[bond], copy.tensors[bond + 1], optimize=True)
        singular = np.linalg.svd(theta.reshape(theta.shape[0] * 2, -1), compute_uv=False)
        probs = singular * singular
        probs /= probs.sum()
        probs = probs[probs > 1e-15]
        if alpha == 1.0:
            return float(-np.sum(probs * np.log2(probs)))
        return float(np.log2(np.sum(probs ** alpha)) / (1.0 - alpha))

    def measure(self, site: int, rng: np.random.Generator | None = None) -> int:
        rho = self.reduced_density_matrix(site)
        probabilities = np.maximum(np.real(np.diag(rho)), 0.0)
        probabilities /= probabilities.sum()
        outcome = int((rng or np.random.default_rng()).choice(2, p=probabilities))
        projected = self.tensors[site].copy()
        projected[:, 1 - outcome, :] = 0
        self.tensors[site] = projected / np.sqrt(probabilities[outcome])
        # Truncation can leave the represented state with norm below one;
        # normalize after each collapse so subsequent conditional draws remain
        # a valid Born sample.
        self.normalize()
        self.canonical_form, self.orthogonality_center = "none", None
        return outcome

    def sample(self, shots: int, seed: int | None = None) -> dict[str, int]:
        if shots < 1:
            raise ValueError("shots must be >= 1")
        rng = np.random.default_rng(seed)
        counts: dict[str, int] = {}
        for _ in range(shots):
            state = self.copy()
            bits = "".join(str(state.measure(site, rng)) for site in range(self.num_qubits))
            counts[bits] = counts.get(bits, 0) + 1
        return counts

    def to_statevector(self, max_qubits: int = 20) -> np.ndarray:
        if self.num_qubits > max_qubits:
            raise MPSMemoryError(f"refusing to materialize {self.num_qubits} qubits (limit {max_qubits})")
        result = self.tensors[0]
        for tensor in self.tensors[1:]:
            result = np.tensordot(result, tensor, axes=([-1], [0]))
        return result.reshape(-1)

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "mps", "num_qubits": self.num_qubits, "bond_dimensions": self.bond_dimensions,
            "max_bond_dimension": self.max_bond_dimension, "tensor_count": len(self.tensors),
            "parameter_count": self.parameter_count, "estimated_memory_bytes": self.estimated_memory_bytes,
            "norm": self.norm(), "canonical_form": self.canonical_form,
            "orthogonality_center": self.orthogonality_center,
            "cumulative_truncation_error": self.cumulative_truncation_error,
            "truncation_history": [event.to_dict() for event in self.truncation_history],
            "entanglement_entropy": [self.entanglement_entropy(bond) for bond in range(self.num_qubits - 1)],
        }
