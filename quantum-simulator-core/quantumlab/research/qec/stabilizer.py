"""Stabilizer-code algebra, validation, encoders, and exact distance oracles.

The implementation is deliberately conservative: it validates every algebraic
assumption instead of trusting a code declaration.  It is exact for small
codes (the code-space projector and exhaustive distance enumeration are
limited to a documented number of qubits) and raises rather than silently
returning an approximation when a requested computation is infeasible.

Terminology
-----------
* ``n`` physical qubits, ``m`` independent stabilizer generators, and
  ``k = n - m`` logical qubits.
* A stabilizer generator ``G_i`` is a Hermitian Pauli operator with
  ``G_i |psi> = +|psi>`` on the code space; generators must commute and be
  independent.
* Logical operators ``Xbar_i`` and ``Zbar_i`` commute with every stabilizer,
  obey ``Xbar_i Zbar_j = (-1)^(delta_ij) Zbar_j Xbar_i``, and are independent
  modulo the stabilizer group.
* An error ``E`` has syndrome ``s_i = 1`` iff ``E`` anticommutes with
  ``G_i``.  A correction ``C`` is valid for syndrome ``s`` iff ``E C`` has
  the same syndrome as ``E``; equivalently ``C`` has syndrome ``s``.
* A residual ``R = E C`` is *invalid* if it anticommutes with any stabilizer,
  *trivial* if it lies in the stabilizer group, and a *logical failure* if it
  commutes with all stabilizers but acts nontrivially on the logical
  observables.  For a Z-basis memory, only logical-X components flip the
  measured logical Z observable; ``classify_residual(..., basis="z")``
  implements that operational criterion.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from quantumlab.research.qec.pauli import (
    Pauli,
    PauliError,
    enumerate_paulis,
    gf2_in_span,
    gf2_rank,
    symplectic_product,
    validate_pauli_set,
)


class StabilizerCodeError(ValueError):
    """Raised when a stabilizer-code declaration violates the algebra."""


class DistanceComputationError(RuntimeError):
    """Raised when an exact distance cannot be computed within the budget."""


class EncodingUnavailableError(RuntimeError):
    """Raised when exact code-space construction is infeasible for this size."""


class ResidualClass(StrEnum):
    """Classification of a residual error after correction."""

    TRIVIAL = "trivial"
    LOGICAL_FAILURE = "logical_failure"
    INVALID = "invalid"


@dataclass(frozen=True)
class CodeValidation:
    """Result of validating a code declaration."""

    num_qubits: int
    num_stabilizers: int
    num_logical_qubits: int
    stabilizer_rank: int
    generators_commute: bool
    generators_independent: bool
    logicals_commute_with_stabilizers: bool
    logicals_anticommute_correctly: bool
    logicals_independent_modulo_stabilizers: bool
    hermitian: bool
    messages: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.messages


def _require_unique_logicals(logicals_x: tuple[Pauli, ...], logicals_z: tuple[Pauli, ...]) -> None:
    if len(logicals_x) != len(logicals_z):
        raise StabilizerCodeError(
            f"logical X count {len(logicals_x)} != logical Z count {len(logicals_z)}"
        )


@dataclass(frozen=True)
class StabilizerCode:
    """A validated stabilizer code on ``num_qubits`` physical qubits."""

    name: str
    num_qubits: int
    stabilizers: tuple[Pauli, ...]
    logical_x: tuple[Pauli, ...]
    logical_z: tuple[Pauli, ...]
    is_css: bool = False

    def __post_init__(self) -> None:
        validation = self.validate()
        if not validation.ok:
            raise StabilizerCodeError(
                "invalid stabilizer code: " + "; ".join(validation.messages)
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> CodeValidation:
        messages: list[str] = []
        n = self.num_qubits
        if n < 1:
            raise StabilizerCodeError("num_qubits must be >= 1")
        m = len(self.stabilizers)
        k = len(self.logical_x)
        if m < 0 or k < 0:
            raise StabilizerCodeError("stabilizer and logical counts must be non-negative")
        _require_unique_logicals(self.logical_x, self.logical_z)
        if k != n - m:
            messages.append(
                f"k={k} does not equal n-m={n - m}; "
                "generators must be independent and the logical count must match"
            )
        all_ops = list(self.stabilizers) + list(self.logical_x) + list(self.logical_z)
        try:
            validate_pauli_set(all_ops, n)
            hermitian = True
        except PauliError as exc:
            messages.append(str(exc))
            hermitian = False

        generators_commute = True
        for i, j in itertools.combinations(range(m), 2):
            if self.stabilizers[i].symplectic_product(self.stabilizers[j]) != 0:
                generators_commute = False
                messages.append(f"stabilizers {i} and {j} anticommute")

        generator_masks = [p.x << n | p.z for p in self.stabilizers]
        stab_rank = gf2_rank(generator_masks, 2 * n) if n else 0
        generators_independent = stab_rank == m
        if not generators_independent:
            messages.append(f"stabilizer rank {stab_rank} != generator count {m}")

        logicals_commute_with_stabilizers = True
        for index, logical in enumerate(list(self.logical_x) + list(self.logical_z)):
            for gen_index, generator in enumerate(self.stabilizers):
                if logical.symplectic_product(generator) != 0:
                    logicals_commute_with_stabilizers = False
                    messages.append(
                        f"logical operator {index} anticommutes with stabilizer {gen_index}"
                    )

        logicals_anticommute_correctly = True
        for i, lx in enumerate(self.logical_x):
            for j, lz in enumerate(self.logical_z):
                expected = 1 if i == j else 0
                actual = symplectic_product(lx, lz)
                if actual != expected:
                    logicals_anticommute_correctly = False
                    messages.append(
                        f"Xbar_{i} and Zbar_{j} have symplectic product {actual}, "
                        f"expected {expected}"
                    )
        for i, j in itertools.combinations(range(k), 2):
            if symplectic_product(self.logical_x[i], self.logical_x[j]) != 0:
                messages.append(f"Xbar_{i} and Xbar_{j} anticommute")
                logicals_anticommute_correctly = False
            if symplectic_product(self.logical_z[i], self.logical_z[j]) != 0:
                messages.append(f"Zbar_{i} and Zbar_{j} anticommute")
                logicals_anticommute_correctly = False

        logical_masks = [p.x << n | p.z for p in list(self.logical_x) + list(self.logical_z)]
        all_rank = gf2_rank(generator_masks + logical_masks, 2 * n) if n else 0
        logicals_independent = all_rank == m + 2 * k
        if not logicals_independent:
            messages.append(
                f"stabilizers plus logicals have rank {all_rank}, expected {m + 2 * k}"
            )
        for index, logical in enumerate(list(self.logical_x) + list(self.logical_z)):
            if gf2_in_span(generator_masks, logical.x << n | logical.z, 2 * n):
                messages.append(f"logical operator {index} lies in the stabilizer group")

        return CodeValidation(
            num_qubits=n,
            num_stabilizers=m,
            num_logical_qubits=k,
            stabilizer_rank=stab_rank,
            generators_commute=generators_commute,
            generators_independent=generators_independent,
            logicals_commute_with_stabilizers=logicals_commute_with_stabilizers,
            logicals_anticommute_correctly=logicals_anticommute_correctly,
            logicals_independent_modulo_stabilizers=logicals_independent,
            hermitian=hermitian,
            messages=tuple(messages),
        )

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------
    @property
    def num_stabilizers(self) -> int:
        return len(self.stabilizers)

    @property
    def num_logical_qubits(self) -> int:
        return len(self.logical_x)

    @property
    def generator_masks(self) -> list[int]:
        n = self.num_qubits
        return [p.x << n | p.z for p in self.stabilizers]

    def stabilizer_rank(self) -> int:
        return gf2_rank(self.generator_masks, 2 * self.num_qubits)

    def syndrome(self, error: Pauli) -> tuple[int, ...]:
        """Return the commutation syndrome of ``error`` with each generator."""
        self._check_pauli(error)
        return tuple(symplectic_product(error, generator) for generator in self.stabilizers)

    def correction_matches_syndrome(
        self, correction: Pauli, syndrome: tuple[int, ...]
    ) -> bool:
        self._check_pauli(correction)
        if len(syndrome) != self.num_stabilizers:
            raise StabilizerCodeError(
                f"syndrome length {len(syndrome)} != {self.num_stabilizers} generators"
            )
        return self.syndrome(correction) == tuple(int(bit) & 1 for bit in syndrome)

    def commutes_with_stabilizers(self, pauli: Pauli) -> bool:
        self._check_pauli(pauli)
        return all(symplectic_product(pauli, gen) == 0 for gen in self.stabilizers)

    def in_stabilizer_group(self, pauli: Pauli) -> bool:
        self._check_pauli(pauli)
        return gf2_in_span(
            self.generator_masks, pauli.x << self.num_qubits | pauli.z, 2 * self.num_qubits
        )

    def logical_action(self, pauli: Pauli, *, basis: str = "both") -> tuple[int, ...]:
        """Return anticommutation bits with the logical observables.

        ``basis="z"`` returns the logical-X action (which flips a Z-basis
        memory), ``basis="x"`` returns the logical-Z action, and ``"both"``
        returns both blocks concatenated.
        """
        self._check_pauli(pauli)
        if basis not in {"x", "z", "both"}:
            raise StabilizerCodeError("basis must be 'x', 'z', or 'both'")
        x_bits = tuple(symplectic_product(pauli, logical) for logical in self.logical_z)
        z_bits = tuple(symplectic_product(pauli, logical) for logical in self.logical_x)
        if basis == "z":
            return x_bits
        if basis == "x":
            return z_bits
        return x_bits + z_bits

    def classify_residual(self, residual: Pauli, *, basis: str = "both") -> ResidualClass:
        """Classify a residual error under the operational failure criterion."""
        self._check_pauli(residual)
        if not self.commutes_with_stabilizers(residual):
            return ResidualClass.INVALID
        if any(bit for bit in self.logical_action(residual, basis=basis)):
            return ResidualClass.LOGICAL_FAILURE
        return ResidualClass.TRIVIAL

    def is_logical_failure(self, residual: Pauli, *, basis: str = "both") -> bool:
        return self.classify_residual(residual, basis=basis) is ResidualClass.LOGICAL_FAILURE

    def _check_pauli(self, pauli: Pauli) -> None:
        if pauli.num_qubits != self.num_qubits:
            raise StabilizerCodeError(
                f"Pauli acts on {pauli.num_qubits} qubits, code has {self.num_qubits}"
            )

    # ------------------------------------------------------------------
    # Distances (exact, small codes only)
    # ------------------------------------------------------------------
    def distance(
        self,
        *,
        kind: str = "full",
        max_weight: int | None = None,
        max_paulis: int = 2_000_000,
    ) -> int:
        """Compute an exact distance by exhaustive normalizer enumeration.

        ``kind="full"``: minimum weight of any normalizer element outside the
        stabilizer group (the standard Pauli distance).
        ``kind="x"``: minimum weight of a logical-X operator (one that flips a
        Z-basis memory).
        ``kind="z"``: minimum weight of a logical-Z operator.
        """
        if kind not in {"full", "x", "z"}:
            raise StabilizerCodeError("kind must be 'full', 'x', or 'z'")
        if self.num_logical_qubits == 0:
            raise DistanceComputationError("a code with k=0 has no logical operators")
        n = self.num_qubits
        if n > 10:
            raise DistanceComputationError(
                f"exact distance enumeration is limited to 10 qubits, got n={n}"
            )
        top = n if max_weight is None else max_weight
        if top < 1 or top > n:
            raise StabilizerCodeError("max_weight must be in [1, num_qubits]")
        seen = 0
        for pauli in enumerate_paulis(n, min_weight=1, max_weight=top):
            seen += 1
            if seen > max_paulis:
                raise DistanceComputationError(
                    f"distance enumeration exceeded max_paulis={max_paulis}"
                )
            if not self.commutes_with_stabilizers(pauli):
                continue
            if self.in_stabilizer_group(pauli):
                continue
            if kind == "full":
                return pauli.weight
            actions = self.logical_action(pauli, basis="z" if kind == "x" else "x")
            if any(actions):
                return pauli.weight
        raise DistanceComputationError(
            f"no weight-{kind} logical operator found up to weight {top}"
        )

    # ------------------------------------------------------------------
    # Code space and encoder (exact, small codes only)
    # ------------------------------------------------------------------
    def _require_small_for_matrices(self) -> None:
        if self.num_qubits > 8:
            raise EncodingUnavailableError(
                "exact code-space matrices are limited to 8 qubits; "
                f"this code has {self.num_qubits}"
            )

    def code_space_projector(self) -> np.ndarray:
        """Return ``P = 2^-m prod_i (I + G_i)`` as an exact matrix."""
        self._require_small_for_matrices()
        n = self.num_qubits
        dim = 1 << n
        projector = np.eye(dim, dtype=np.complex128)
        for generator in self.stabilizers:
            projector = projector @ (np.eye(dim, dtype=np.complex128) + generator.matrix())
        projector = projector / (2**len(self.stabilizers))
        return np.asarray((projector + projector.conj().T) / 2)

    def code_space_dimension(self) -> int:
        projector = self.code_space_projector()
        return int(round(float(np.trace(projector).real)))

    def encoded_basis(self) -> list[np.ndarray]:
        """Construct ``|b_L>`` for every logical computational basis state.

        The common +1 eigenspace of the stabilizers and the signed logical-Z
        operators has dimension one for each ``b``.  We construct it exactly
        (up to floating-point eigensolver precision) by a projector and
        verify the stabilizer and logical-Z eigenvalues afterwards.
        """
        self._require_small_for_matrices()
        n = self.num_qubits
        k = self.num_logical_qubits
        if k == 0:
            return []
        dim = 1 << n
        eye = np.eye(dim, dtype=np.complex128)
        states: list[np.ndarray] = []
        for logical_index in range(1 << k):
            projector = eye.copy()
            for generator in self.stabilizers:
                projector = projector @ (eye + generator.matrix())
            for qubit, logical_z in enumerate(self.logical_z):
                sign = -1.0 if (logical_index >> (k - 1 - qubit)) & 1 else 1.0
                projector = projector @ (eye + sign * logical_z.matrix())
            projector = projector / (2**n)
            projector = (projector + projector.conj().T) / 2
            eigenvalues, eigenvectors = np.linalg.eigh(projector)
            index = int(np.argmax(eigenvalues))
            if eigenvalues[index] < 1.0 - 1e-8:
                raise EncodingUnavailableError(
                    "logical eigenspace projector is not rank one; "
                    "the code declaration is inconsistent"
                )
            state = eigenvectors[:, index]
            norm = float(np.linalg.norm(state))
            if norm < 1e-12:
                raise EncodingUnavailableError("encoder produced a zero state")
            state = state / norm
            # Verify the defining eigenvalues.
            for gen_index, generator in enumerate(self.stabilizers):
                value = float(np.real(np.vdot(state, generator.matrix() @ state)))
                if abs(value - 1.0) > 1e-7:
                    raise EncodingUnavailableError(
                        f"encoded state fails stabilizer {gen_index}: <G>={value}"
                    )
            for qubit, logical_z in enumerate(self.logical_z):
                expected = -1.0 if (logical_index >> (k - 1 - qubit)) & 1 else 1.0
                value = float(np.real(np.vdot(state, logical_z.matrix() @ state)))
                if abs(value - expected) > 1e-7:
                    raise EncodingUnavailableError(
                        f"encoded state has wrong Lz_{qubit} eigenvalue: {value}"
                    )
            states.append(state)
        return states

    def encode_state(self, logical_amplitudes: np.ndarray) -> np.ndarray:
        """Map a ``2**k`` logical amplitude vector into the physical code space."""
        self._require_small_for_matrices()
        amplitudes = np.asarray(logical_amplitudes, dtype=np.complex128)
        if amplitudes.shape != (1 << self.num_logical_qubits,):
            raise StabilizerCodeError(
                f"logical amplitudes must have shape ({1 << self.num_logical_qubits},), "
                f"got {amplitudes.shape}"
            )
        if abs(float(np.vdot(amplitudes, amplitudes).real) - 1.0) > 1e-9:
            raise StabilizerCodeError("logical amplitudes must be normalized")
        basis = self.encoded_basis()
        physical = np.zeros(1 << self.num_qubits, dtype=np.complex128)
        for coefficient, state in zip(amplitudes, basis, strict=True):
            physical += coefficient * state
        return physical

    def validate_encoder(self) -> bool:
        """Check that the encoder carries the correct logical action.

        For every logical basis state and every logical pair, ``Xbar_i`` must
        map ``|b>`` to ``|b xor 2^i>`` and ``Zbar_i`` must multiply by
        ``(-1)^{b_i}``.  Raises with a diagnostic on the first mismatch.
        """
        self._require_small_for_matrices()
        basis = self.encoded_basis()
        k = self.num_logical_qubits
        for index, state in enumerate(basis):
            pairs = zip(self.logical_x, self.logical_z, strict=True)
            for qubit, (logical_x, logical_z) in enumerate(pairs):
                target = index ^ (1 << (k - 1 - qubit))
                overlap = complex(np.vdot(basis[target], logical_x.matrix() @ state))
                if abs(abs(overlap) - 1.0) > 1e-7:
                    raise StabilizerCodeError(
                        f"Xbar_{qubit} does not map basis state {index} to {target}"
                    )
                expected_z = -1.0 if (index >> (k - 1 - qubit)) & 1 else 1.0
                value = float(np.real(np.vdot(state, logical_z.matrix() @ state)))
                if abs(value - expected_z) > 1e-7:
                    raise StabilizerCodeError(
                        f"Zbar_{qubit} has wrong eigenvalue on basis state {index}"
                    )
        return True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "num_qubits": self.num_qubits,
            "stabilizers": [p.label() for p in self.stabilizers],
            "logical_x": [p.label() for p in self.logical_x],
            "logical_z": [p.label() for p in self.logical_z],
            "num_logical_qubits": self.num_logical_qubits,
            "is_css": self.is_css,
        }


def _num_logical_qubits(n: int, m: int) -> int:
    if m > n:
        return 0
    return n - m


def build_code(
    name: str,
    num_qubits: int,
    stabilizers: tuple[Pauli, ...],
    logical_x: tuple[Pauli, ...],
    logical_z: tuple[Pauli, ...],
    *,
    is_css: bool = False,
) -> StabilizerCode:
    """Construct and validate a code, with a clearer error for count mistakes."""
    expected_k = _num_logical_qubits(num_qubits, len(stabilizers))
    if len(logical_x) != expected_k or len(logical_z) != expected_k:
        raise StabilizerCodeError(
            f"expected {expected_k} logical pairs for n={num_qubits}, "
            f"m={len(stabilizers)}; got {len(logical_x)} and {len(logical_z)}"
        )
    return StabilizerCode(name, num_qubits, stabilizers, logical_x, logical_z, is_css)


def hilbert_dimension(num_qubits: int) -> int:
    if num_qubits < 1:
        raise StabilizerCodeError("num_qubits must be >= 1")
    return int(2**num_qubits)


def log2_code_dimension(code: StabilizerCode) -> float:
    return math.log2(code.code_space_dimension())
