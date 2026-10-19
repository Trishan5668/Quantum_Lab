"""Exact Pauli algebra for stabilizer-code research.

Conventions
-----------
A Pauli operator is represented by two bit masks and a phase:

``P = i**phase * X**x * Z**z``

where ``X**x`` means a tensor product of ``X`` on every qubit set in ``x``
(and identity elsewhere), and similarly for ``z``.  Qubit 0 is the most
significant bit of the masks, matching the simulator's big-endian
convention.  Products use

``(X^x1 Z^z1)(X^x2 Z^z2) = (-1)^(z1 . x2) X^(x1 xor x2) Z^(z1 xor z2)``.

A Pauli is Hermitian iff ``phase mod 2 == popcount(x & z) mod 2``.  All
stabilizer generators and logical operators accepted by
:mod:`quantumlab.research.qec.stabilizer` must be Hermitian.

The phase is retained because it matters for multiplication and for exact
matrix construction.  Syndrome and logical-failure tests use the symplectic
representation and are insensitive to an overall sign, as they must be.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

_PAULI_LABELS = "IXYZ"
_LABEL_TO_MASKS: dict[str, tuple[int, int]] = {
    "I": (0, 0),
    "X": (1, 0),
    "Y": (1, 1),
    "Z": (0, 1),
}


class PauliError(ValueError):
    """Raised for malformed Pauli data or incompatible qubit counts."""


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PauliError(f"{name} must be an integer, got {type(value).__name__}")
    return value


@dataclass(frozen=True)
class Pauli:
    """A Pauli operator on ``num_qubits`` qubits in the ``X^x Z^z`` basis."""

    x: int
    z: int
    phase: int = 0
    num_qubits: int = field(default=1)

    def __post_init__(self) -> None:
        n = _require_int(self.num_qubits, "num_qubits")
        if n < 1:
            raise PauliError(f"num_qubits must be >= 1, got {n}")
        if n > 64:
            raise PauliError(
                "Pauli masks use Python integers but matrix construction and "
                "exhaustive enumeration are limited to 64 qubits"
            )
        limit = 1 << n
        for name, mask in (("x", self.x), ("z", self.z)):
            value = _require_int(mask, name)
            if value < 0 or value >= limit:
                raise PauliError(
                    f"{name} mask {value} does not fit in {n} qubits "
                    f"(allowed 0..{limit - 1})"
                )
        phase = _require_int(self.phase, "phase")
        if phase % 4 != phase:
            raise PauliError(f"phase must be an integer in 0..3, got {phase}")

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def identity(cls, num_qubits: int) -> Pauli:
        return cls(0, 0, 0, num_qubits)

    @classmethod
    def from_string(cls, label: str) -> Pauli:
        """Parse ``IXYZ`` labels with an optional leading ``+`` or ``-``."""
        text = label.strip().replace(" ", "")
        if not text:
            raise PauliError("Pauli label must not be empty")
        sign = 0
        if text[0] in "+-":
            sign = 0 if text[0] == "+" else 2
            text = text[1:]
        if not text:
            raise PauliError("Pauli label must contain at least one qubit")
        bad = sorted({char for char in text if char not in _PAULI_LABELS})
        if bad:
            raise PauliError(f"invalid Pauli label characters: {bad}")
        x = 0
        z = 0
        phase = sign
        n = len(text)
        for index, char in enumerate(text):
            qubit = n - 1 - index
            dx, dz = _LABEL_TO_MASKS[char]
            x |= dx << qubit
            z |= dz << qubit
            if char == "Y":
                phase = (phase + 1) % 4
        return cls(x, z, phase, n)

    @classmethod
    def from_masks(cls, x: int, z: int, num_qubits: int, phase: int = 0) -> Pauli:
        return cls(x, z, phase, num_qubits)

    def copy_with_phase(self, phase: int) -> Pauli:
        return Pauli(self.x, self.z, phase, self.num_qubits)

    # ------------------------------------------------------------------
    # Labels and basic queries
    # ------------------------------------------------------------------
    @property
    def weight(self) -> int:
        return (self.x | self.z).bit_count()

    @property
    def x_weight(self) -> int:
        return self.x.bit_count()

    @property
    def z_weight(self) -> int:
        return self.z.bit_count()

    @property
    def y_count(self) -> int:
        return (self.x & self.z).bit_count()

    @property
    def symplectic(self) -> tuple[int, int]:
        return (self.x, self.z)

    def is_identity(self) -> bool:
        return self.x == 0 and self.z == 0

    def is_hermitian(self) -> bool:
        return (self.phase % 2) == ((self.x & self.z).bit_count() % 2)

    def _chars(self) -> str:
        chars = []
        for qubit in range(self.num_qubits):
            bit = 1 << (self.num_qubits - 1 - qubit)
            x = bool(self.x & bit)
            z = bool(self.z & bit)
            if not x and not z:
                chars.append("I")
            elif x and not z:
                chars.append("X")
            elif z and not x:
                chars.append("Z")
            else:
                chars.append("Y")
        return "".join(chars)

    def label(self) -> str:
        """Return a sign-aware IXYZ label when the operator is ``+/-`` a Pauli.

        A standard ``Y`` contributes ``i`` in the ``X^x Z^z`` representation,
        so the signed Pauli phase is ``phase - y_count`` modulo 4.
        """
        standard_phase = (self.phase - self.y_count) % 4
        if standard_phase not in (0, 2):
            raise PauliError(
                f"phase i^{self.phase} (standard phase i^{standard_phase}) "
                "cannot be represented as a +/- Pauli string"
            )
        return ("-" if standard_phase == 2 else "+") + self._chars()

    def unsigned_label(self) -> str:
        """Return an IXYZ label ignoring the phase."""
        return self._chars()

    def __str__(self) -> str:
        try:
            return self.label()
        except PauliError:
            standard_phase = (self.phase - self.y_count) % 4
            return f"i^{standard_phase}*{self.unsigned_label()}"

    # ------------------------------------------------------------------
    # Algebra
    # ------------------------------------------------------------------
    def _check_compatible(self, other: Pauli) -> None:
        if self.num_qubits != other.num_qubits:
            raise PauliError(
                f"Pauli qubit-count mismatch: {self.num_qubits} vs {other.num_qubits}"
            )

    def multiply(self, other: Pauli) -> Pauli:
        """Return ``self * other`` with the correct ``i`` phase."""
        self._check_compatible(other)
        phase = (self.phase + other.phase + 2 * ((self.z & other.x).bit_count() % 2)) % 4
        return Pauli(self.x ^ other.x, self.z ^ other.z, phase, self.num_qubits)

    def __mul__(self, other: Pauli) -> Pauli:
        return self.multiply(other)

    def symplectic_product(self, other: Pauli) -> int:
        """Return the GF(2) symplectic product (0 commute, 1 anticommute)."""
        return symplectic_product(self, other)

    def commutes(self, other: Pauli) -> bool:
        """Return True iff the two Pauli operators commute."""
        self._check_compatible(other)
        return symplectic_product(self, other) == 0

    def anticommutes(self, other: Pauli) -> bool:
        return not self.commutes(other)

    def adjoint(self) -> Pauli:
        phase = (-self.phase + 2 * ((self.x & self.z).bit_count() % 2)) % 4
        return Pauli(self.x, self.z, phase, self.num_qubits)

    def matrix(self) -> np.ndarray:
        """Return the exact ``(2**n, 2**n)`` matrix (n <= 10)."""
        if self.num_qubits > 10:
            raise PauliError("exact matrices are limited to 10 qubits")
        eye = np.eye(2, dtype=np.complex128)
        pauli_x = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        pauli_z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        out = np.array([[1.0 + 0.0j]])
        for qubit in range(self.num_qubits):
            bit = 1 << (self.num_qubits - 1 - qubit)
            x = bool(self.x & bit)
            z = bool(self.z & bit)
            local = pauli_x @ pauli_z if x and z else pauli_x if x else pauli_z if z else eye
            out = np.kron(out, local)
        return (1j**self.phase) * out


def symplectic_product(a: Pauli, b: Pauli) -> int:
    """Return ``a . b = x_a.z_b + z_a.x_b mod 2``."""
    if a.num_qubits != b.num_qubits:
        raise PauliError(
            f"symplectic product requires equal qubit counts: {a.num_qubits} vs {b.num_qubits}"
        )
    return (((a.x & b.z) ^ (a.z & b.x)).bit_count()) % 2


def gf2_rank(rows: list[int], num_bits: int) -> int:
    """Rank of a list of GF(2) row vectors represented as integer masks."""
    if num_bits < 1:
        raise ValueError("num_bits must be >= 1")
    basis: dict[int, int] = {}
    for row in rows:
        if row < 0 or row >= (1 << num_bits):
            raise ValueError(f"row {row} does not fit in {num_bits} bits")
        value = row
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


def gf2_in_span(rows: list[int], target: int, num_bits: int) -> bool:
    """Return True iff ``target`` is in the GF(2) span of ``rows``."""
    if target < 0 or target >= (1 << num_bits):
        raise ValueError(f"target {target} does not fit in {num_bits} bits")
    in_span, _, _ = gf2_reduce(rows, target, num_bits)
    return in_span


def gf2_reduce(rows: list[int], target: int, num_bits: int) -> tuple[bool, int, list[int]]:
    """Reduce ``target`` by ``rows``; return (in_span, residual, echelon_basis)."""
    basis: dict[int, int] = {}
    for row in rows:
        if row < 0 or row >= (1 << num_bits):
            raise ValueError(f"row {row} does not fit in {num_bits} bits")
        value = row
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    value = target
    while value:
        pivot = value.bit_length() - 1
        if pivot in basis:
            value ^= basis[pivot]
        else:
            break
    return value == 0, value, list(basis.values())


def enumerate_paulis(
    num_qubits: int,
    *,
    min_weight: int = 0,
    max_weight: int | None = None,
    hermitian_only: bool = True,
) -> Iterator[Pauli]:
    """Enumerate Pauli operators by increasing weight.

    The enumeration is deterministic and exhaustive for the requested weight
    range.  A ``Y`` on a site carries ``XZ`` and the Pauli phase ``i``; the
    ``phase`` field is therefore 1 on ``Y`` and the operator is Hermitian.
    """
    if num_qubits < 1:
        raise ValueError("num_qubits must be >= 1")
    if min_weight < 0:
        raise ValueError("min_weight must be non-negative")
    top = num_qubits if max_weight is None else max_weight
    if top < min_weight or top > num_qubits:
        raise ValueError("max_weight must be in [min_weight, num_qubits]")
    for weight in range(min_weight, top + 1):
        for positions in itertools.combinations(range(num_qubits), weight):
            for labels in itertools.product("XYZ", repeat=weight):
                x = 0
                z = 0
                phase = 0
                for position, label in zip(positions, labels, strict=True):
                    dx, dz = _LABEL_TO_MASKS[label]
                    x |= dx << (num_qubits - 1 - position)
                    z |= dz << (num_qubits - 1 - position)
                    if label == "Y":
                        phase += 1
                pauli = Pauli(x, z, phase % 4, num_qubits)
                if hermitian_only and not pauli.is_hermitian():
                    continue
                yield pauli


def pauli_from_int(index: int, num_qubits: int) -> Pauli:
    """Map ``0 <= index < 4**n`` to a deterministic Pauli (base-4 IXYZ)."""
    if num_qubits < 1:
        raise ValueError("num_qubits must be >= 1")
    if index < 0 or index >= 4**num_qubits:
        raise ValueError(f"index {index} out of range for {num_qubits} qubits")
    x = 0
    z = 0
    phase = 0
    value = index
    for qubit in range(num_qubits - 1, -1, -1):
        label = value % 4
        value //= 4
        if label == 0:
            continue
        dx, dz = _LABEL_TO_MASKS[_PAULI_LABELS[label]]
        x |= dx << qubit
        z |= dz << qubit
        if label == 2:  # Y
            phase += 1
    return Pauli(x, z, phase % 4, num_qubits)


def commutation_matrix(paulis: list[Pauli]) -> list[list[int]]:
    """Return the GF(2) commutation matrix (0 = commute, 1 = anticommute)."""
    return [[symplectic_product(a, b) for b in paulis] for a in paulis]


def is_hermitian_set(paulis: list[Pauli]) -> bool:
    return all(pauli.is_hermitian() for pauli in paulis)


def validate_pauli_set(paulis: list[Pauli], num_qubits: int) -> None:
    for index, pauli in enumerate(paulis):
        if not isinstance(pauli, Pauli):
            raise PauliError(f"element {index} is not a Pauli")
        if pauli.num_qubits != num_qubits:
            raise PauliError(
                f"element {index} acts on {pauli.num_qubits} qubits, expected {num_qubits}"
            )
        if not pauli.is_hermitian():
            raise PauliError(f"element {index} is not Hermitian: {pauli}")
