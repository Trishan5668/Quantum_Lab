"""Exact decoders for small stabilizer codes.

``ExactDecoder`` enumerates every Pauli error up to a documented weight and
stores the minimum-weight or maximum-likelihood correction for each syndrome.
It is a correctness oracle, not a scalable decoder: the enumeration size is
``4**n`` and is capped explicitly.  Ties are broken deterministically by
weight, then by the IXYZ label so repeated runs are bit-for-bit identical.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Literal

from quantumlab.research.qec.decoders.base import (
    DecoderError,
    DecoderInputError,
    DecoderSpec,
    PauliDecoder,
)
from quantumlab.research.qec.noise import NoiseModelError, PauliChannel
from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.stabilizer import StabilizerCode


@dataclass(frozen=True)
class TableEntry:
    correction: Pauli
    log_likelihood: float
    weight: int
    label: str


class ExactDecoder(PauliDecoder):
    """Exact minimum-weight or maximum-likelihood decoder on a small code."""

    VERSION = "1.0.0"

    def __init__(
        self,
        code: StabilizerCode,
        channel: PauliChannel,
        *,
        mode: Literal["min_weight", "maximum_likelihood"] = "min_weight",
        max_weight: int | None = None,
        max_enumeration: int = 1_000_000,
    ) -> None:
        if mode not in {"min_weight", "maximum_likelihood"}:
            raise DecoderInputError("mode must be 'min_weight' or 'maximum_likelihood'")
        n = code.num_qubits
        top = n if max_weight is None else max_weight
        if top < 0 or top > n:
            raise DecoderInputError("max_weight must be in [0, num_qubits]")
        if 4**n > max_enumeration:
            raise DecoderInputError(
                f"exhaustive enumeration of {4**n} Paulis exceeds max_enumeration="
                f"{max_enumeration}; use a smaller code or a different decoder"
            )
        super().__init__(
            code,
            DecoderSpec(
                name=f"exact_{mode}",
                version=self.VERSION,
                decoder_type="pauli",
                supported_code_families=("stabilizer_small",),
                noise_assumptions=("independent Pauli errors",),
                deterministic=True,
                config={
                    "mode": mode,
                    "max_weight": top,
                    "max_enumeration": max_enumeration,
                    "tie_break": "deterministic",
                },
            ),
        )
        self.channel = channel
        self.mode = mode
        self.table = self._build_table(top)

    def _build_table(self, max_weight: int) -> dict[tuple[int, ...], TableEntry]:
        table: dict[tuple[int, ...], TableEntry] = {}
        for masks in itertools.product(range(4), repeat=self.code.num_qubits):
            x = 0
            z = 0
            phase = 0
            weight = 0
            for qubit, code in enumerate(masks):
                bit = 1 << (self.code.num_qubits - 1 - qubit)
                if code == 1:  # X
                    x |= bit
                    weight += 1
                elif code == 2:  # Z
                    z |= bit
                    weight += 1
                elif code == 3:  # Y
                    x |= bit
                    z |= bit
                    phase += 1
                    weight += 1
            if weight > max_weight:
                continue
            pauli = Pauli(x, z, phase % 4, self.code.num_qubits)
            syndrome = self.code.syndrome(pauli)
            log_likelihood = self.channel.log_probability(pauli)
            entry = TableEntry(
                correction=pauli,
                log_likelihood=log_likelihood,
                weight=pauli.weight,
                label=pauli.label(),
            )
            current = table.get(syndrome)
            if current is None or self._prefer(entry, current):
                table[syndrome] = entry
        if not table:
            raise DecoderError("exact decoder table is empty")
        return table

    def _prefer(self, candidate: TableEntry, current: TableEntry) -> bool:
        if self.mode == "min_weight":
            if candidate.weight != current.weight:
                return candidate.weight < current.weight
            return candidate.label < current.label
        if candidate.log_likelihood != current.log_likelihood:
            return candidate.log_likelihood > current.log_likelihood
        if candidate.weight != current.weight:
            return candidate.weight < current.weight
        return candidate.label < current.label

    def _decode(self, syndrome: tuple[int, ...]) -> Pauli:
        entry = self.table.get(syndrome)
        if entry is None:
            raise DecoderError(
                "syndrome is not reachable by any error within max_weight="
                f"{self.spec.config['max_weight']}"
            )
        return entry.correction

    @property
    def table_size(self) -> int:
        return len(self.table)

    def correction_weight(self, syndrome: tuple[int, ...]) -> int:
        return self.table[syndrome].weight

    def degeneracy(self, syndrome: tuple[int, ...]) -> int:
        """Number of enumerated errors with this syndrome (not decoded ties)."""
        target = tuple(int(bit) for bit in syndrome)
        count = 0
        for masks in itertools.product(range(4), repeat=self.code.num_qubits):
            x = 0
            z = 0
            phase = 0
            for qubit, code in enumerate(masks):
                bit = 1 << (self.code.num_qubits - 1 - qubit)
                if code in (1, 3):
                    x |= bit
                if code in (2, 3):
                    z |= bit
                if code == 3:
                    phase += 1
            pauli = Pauli(x, z, phase % 4, self.code.num_qubits)
            if self.code.syndrome(pauli) == target:
                count += 1
        return count


class LookupDecoder(ExactDecoder):
    """Alias for a minimum-weight lookup table decoder."""

    def __init__(
        self,
        code: StabilizerCode,
        channel: PauliChannel,
        *,
        max_weight: int | None = None,
        max_enumeration: int = 1_000_000,
    ) -> None:
        super().__init__(
            code,
            channel,
            mode="min_weight",
            max_weight=max_weight,
            max_enumeration=max_enumeration,
        )


def channel_from_probabilities(p_x: float, p_y: float, p_z: float) -> PauliChannel:
    """Convenience constructor with explicit validation."""
    try:
        return PauliChannel(p_x=p_x, p_y=p_y, p_z=p_z)
    except NoiseModelError as exc:
        raise DecoderInputError(str(exc)) from exc


__all__ = ["ExactDecoder", "LookupDecoder", "TableEntry", "channel_from_probabilities"]
