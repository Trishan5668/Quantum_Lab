"""Small, explicitly defined stabilizer codes used as verification oracles.

Every code in this module is constructed from named stabilizer generators and
logical operators and is validated by :class:`StabilizerCode` on construction.
The repetition family is included because the existing QuantumLab benchmark
uses it, but its full quantum distance is one: it protects only against bit
flips.  Callers interested in its bit-flip protection must ask for
``distance(kind="x")``; the full distance is reported honestly as one.

No surface-code algebra is implemented here.  The surface-code reproduction
uses Stim's generated circuits and records that dependency explicitly.
"""

from __future__ import annotations

from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.stabilizer import StabilizerCode, build_code


class UnsupportedCodeFamilyError(ValueError):
    """Raised when a requested code family is not implemented."""


def repetition_code(distance: int) -> StabilizerCode:
    """Return the odd-distance bit-flip repetition code.

    ``n = distance`` data qubits, ``n-1`` ZZ stabilizers, logical X = X...X,
    logical Z = Z on qubit 0.  The full Pauli distance is one (a single Z
    error is undetectable); the X-error distance is ``distance``.
    """
    if isinstance(distance, bool) or not isinstance(distance, int):
        raise UnsupportedCodeFamilyError("distance must be an integer")
    if distance < 3 or distance % 2 == 0:
        raise UnsupportedCodeFamilyError(
            "the repetition-code family requires an odd distance >= 3"
        )
    n = distance
    # Qubit q is bit (n-1-q); generator i acts on qubits i and i+1.
    stabilizers = tuple(
        Pauli(0, (1 << (n - 1 - i)) | (1 << (n - 2 - i)), 0, n)
        for i in range(n - 1)
    )
    logical_x = (Pauli.from_string("X" * n),)
    logical_z = (Pauli(0, 1 << (n - 1), 0, n),)
    return build_code(
        f"repetition_d{n}", n, stabilizers, logical_x, logical_z, is_css=True
    )


def steane_code() -> StabilizerCode:
    """Return the [[7,1,3]] Steane code (CSS)."""
    labels = (
        "IIIXXXX",
        "IXXIIXX",
        "XIXIXIX",
        "IIIZZZZ",
        "IZZIIZZ",
        "ZIZIZIZ",
    )
    stabilizers = tuple(Pauli.from_string(label) for label in labels)
    logical_x = (Pauli.from_string("XXXXXXX"),)
    logical_z = (Pauli.from_string("ZZZZZZZ"),)
    return build_code("steane_7_1_3", 7, stabilizers, logical_x, logical_z, is_css=True)


def five_qubit_code() -> StabilizerCode:
    """Return the [[5,1,3]] perfect code (non-CSS)."""
    labels = ("XZZXI", "IXZZX", "XIXZZ", "ZXIXZ")
    stabilizers = tuple(Pauli.from_string(label) for label in labels)
    logical_x = (Pauli.from_string("XXXXX"),)
    logical_z = (Pauli.from_string("ZZZZZ"),)
    return build_code("five_qubit_5_1_3", 5, stabilizers, logical_x, logical_z, is_css=False)


def make_code(family: str, distance: int | None = None) -> StabilizerCode:
    """Construct a named small code.

    Supported families: ``repetition`` (requires odd distance >= 3),
    ``steane``, and ``five_qubit``.
    """
    normalized = family.strip().lower().replace("-", "_")
    if normalized == "repetition":
        if distance is None:
            raise UnsupportedCodeFamilyError("repetition requires an explicit distance")
        return repetition_code(distance)
    if normalized in {"steane", "steane_7_1_3"}:
        return steane_code()
    if normalized in {"five_qubit", "five_qubit_5_1_3", "perfect_5_1_3"}:
        return five_qubit_code()
    raise UnsupportedCodeFamilyError(
        f"unknown code family {family!r}; supported: repetition, steane, five_qubit"
    )


SUPPORTED_CODE_FAMILIES: tuple[str, ...] = ("repetition", "steane", "five_qubit")
