"""Validated phenomenological codes used by the initial QEC benchmark.

The first slice deliberately uses the three-qubit bit-flip repetition code.
It models data-qubit Pauli-X faults and ideal syndrome extraction; it is not a
claim of circuit-level fault tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepetitionCode:
    """Three-qubit repetition code correcting one bit flip."""

    distance: int = 3

    def __post_init__(self) -> None:
        if self.distance != 3:
            raise ValueError("only distance=3 is implemented")

    @property
    def num_qubits(self) -> int:
        return 3

    @property
    def stabilizers(self) -> tuple[str, str]:
        return ("ZZI", "IZZ")

    @property
    def logical_x(self) -> str:
        return "XXX"

    @property
    def logical_z(self) -> str:
        return "ZII"

    def validate(self) -> None:
        if self.stabilizers[0].count("Z") != 2 or self.stabilizers[1].count("Z") != 2:
            raise ValueError("invalid repetition-code stabilizers")
        if self.logical_x != "XXX" or self.logical_z != "ZII":
            raise ValueError("invalid repetition-code logical operators")

    def syndrome(self, flips: tuple[bool, bool, bool]) -> tuple[int, int]:
        """Return parity checks for an X-error pattern."""
        a, b, c = (int(value) for value in flips)
        return (a ^ b, b ^ c)

    def correction_for_syndrome(self, syndrome: tuple[int, int]) -> int | None:
        """Return the data-qubit index to correct, or None for no correction."""
        return {(0, 0): None, (1, 0): 0, (1, 1): 1, (0, 1): 2}.get(syndrome)

    def logical_failure(self, flips: tuple[bool, bool, bool], correction: int | None) -> bool:
        residual = list(flips)
        if correction is not None:
            residual[correction] = not residual[correction]
        return sum(residual) >= 2
