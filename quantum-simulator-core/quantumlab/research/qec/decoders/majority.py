"""Minimum-weight majority decoding for the odd repetition code.

For the bit-flip repetition code the syndrome completely determines an error
pattern up to a global bit flip.  Reconstructing the pattern from syndrome
differences and, if its weight exceeds ``n/2``, complementing every bit gives
an exact minimum-weight correction.  This is the same decoding rule as
majority vote, expressed in the code's syndrome coordinates.
"""

from __future__ import annotations

from quantumlab.research.qec.decoders.base import DecoderInputError, DecoderSpec, PauliDecoder
from quantumlab.research.qec.pauli import Pauli
from quantumlab.research.qec.stabilizer import StabilizerCode


class RepetitionMajorityDecoder(PauliDecoder):
    """Exact minimum-weight decoder for the odd-distance bit-flip code."""

    VERSION = "1.0.0"

    def __init__(self, code: StabilizerCode) -> None:
        n = code.num_qubits
        if not code.name.startswith("repetition_d") or n % 2 == 0 or n < 3:
            raise DecoderInputError(
                "RepetitionMajorityDecoder requires an odd-distance repetition code"
            )
        if len(code.logical_x) != 1:
            raise DecoderInputError("repetition decoder supports exactly one logical qubit")
        super().__init__(
            code,
            DecoderSpec(
                name="repetition_majority_vote",
                version=self.VERSION,
                decoder_type="pauli",
                supported_code_families=("repetition",),
                noise_assumptions=(
                    "independent X errors",
                    "perfect syndrome",
                ),
                deterministic=True,
                config={"distance": n},
            ),
        )

    def _decode(self, syndrome: tuple[int, ...]) -> Pauli:
        n = self.code.num_qubits
        # s_i = e_i xor e_{i+1}; fix e_0 = 0 and integrate left to right.
        # The complementary pattern has the same syndrome; choose the lighter.
        bits = [0] * n
        for index in range(1, n):
            bits[index] = bits[index - 1] ^ syndrome[index - 1]
        if sum(bits) > n // 2:
            bits = [1 - bit for bit in bits]
        x = 0
        for qubit, bit in enumerate(bits):
            if bit:
                x |= 1 << (n - 1 - qubit)
        return Pauli(x, 0, 0, n)


__all__ = ["RepetitionMajorityDecoder"]
