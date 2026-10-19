from __future__ import annotations

import numpy as np
import pytest

from quantumlab.research.qec.codes import five_qubit_code, repetition_code, steane_code
from quantumlab.research.qec.decoders import (
    DecoderInputError,
    ExactDecoder,
    LookupDecoder,
    PauliMWPMDecoder,
    RepetitionMajorityDecoder,
)
from quantumlab.research.qec.decoders.base import DecoderSpec, PauliDecoder
from quantumlab.research.qec.noise import bit_flip, depolarizing
from quantumlab.research.qec.pauli import Pauli, enumerate_paulis
from quantumlab.research.qec.stabilizer import ResidualClass


def _assert_correctable(code, channel, errors) -> None:
    decoder = ExactDecoder(code, channel)
    for error in errors:
        result = decoder.decode(code.syndrome(error))
        assert result.status == "ok"
        assert result.correction is not None
        residual = error * result.correction
        assert code.classify_residual(residual) is ResidualClass.TRIVIAL


def test_repetition_exact_decoder_corrects_all_weight_two_x_errors() -> None:
    code = repetition_code(5)
    channel = bit_flip(0.1)
    errors = list(enumerate_paulis(5, max_weight=2))
    x_errors = [error for error in errors if error.z == 0]
    _assert_correctable(code, channel, x_errors)


def test_steane_exact_decoder_corrects_every_weight_one_pauli() -> None:
    code = steane_code()
    channel = depolarizing(0.1)
    errors = list(enumerate_paulis(7, max_weight=1))
    assert len(errors) == 22
    _assert_correctable(code, channel, errors)


def test_five_qubit_exact_decoder_corrects_every_weight_one_pauli() -> None:
    code = five_qubit_code()
    channel = depolarizing(0.1)
    errors = list(enumerate_paulis(5, max_weight=1))
    assert len(errors) == 16
    _assert_correctable(code, channel, errors)


def test_exact_decoder_handles_every_reachable_syndrome() -> None:
    code = repetition_code(5)
    decoder = ExactDecoder(code, bit_flip(0.1))
    for syndrome in (format(index, "04b") for index in range(16)):
        bits = tuple(int(bit) for bit in syndrome)
        result = decoder.decode(bits)
        assert result.status == "ok"
        assert result.syndrome_valid
        assert result.correction is not None
        assert code.syndrome(result.correction) == bits


def test_exact_and_majority_corrections_are_logically_equivalent() -> None:
    code = repetition_code(5)
    exact = ExactDecoder(code, bit_flip(0.1))
    majority = RepetitionMajorityDecoder(code)
    for index in range(16):
        syndrome = tuple((index >> (3 - bit)) & 1 for bit in range(4))
        first = exact.decode(syndrome)
        second = majority.decode(syndrome)
        assert first.status == second.status == "ok"
        assert first.correction is not None and second.correction is not None
        residual = first.correction * second.correction
        assert code.in_stabilizer_group(residual)


def test_mwpm_matches_exact_logical_class_for_repetition() -> None:
    pytest.importorskip("pymatching")
    code = repetition_code(5)
    exact = ExactDecoder(code, bit_flip(0.1))
    mwpm = PauliMWPMDecoder(code, error_probability=0.1)
    for index in range(16):
        syndrome = tuple((index >> (3 - bit)) & 1 for bit in range(4))
        first = exact.decode(syndrome)
        second = mwpm.decode(syndrome)
        assert first.status == second.status == "ok"
        assert first.correction is not None and second.correction is not None
        residual = first.correction * second.correction
        assert code.in_stabilizer_group(residual)


def test_exact_decoder_is_deterministic() -> None:
    code = five_qubit_code()
    decoder = ExactDecoder(code, depolarizing(0.05))
    syndrome = code.syndrome(Pauli.from_string("XIIII"))
    first = decoder.decode(syndrome)
    second = decoder.decode(syndrome)
    assert first.correction is not None and second.correction is not None
    assert first.correction.label() == second.correction.label()


class _IdentityDecoder(PauliDecoder):
    def __init__(self, code) -> None:
        super().__init__(
            code,
            DecoderSpec(
                name="deliberately_broken",
                version="0.0.0",
                decoder_type="pauli",
                supported_code_families=("test",),
                noise_assumptions=("none",),
                deterministic=True,
            ),
        )

    def _decode(self, syndrome: tuple[int, ...]) -> Pauli:
        return Pauli.identity(self.code.num_qubits)


def test_decoder_contract_rejects_wrong_syndrome() -> None:
    code = repetition_code(3)
    decoder = _IdentityDecoder(code)
    result = decoder.decode((1, 0))
    assert result.status == "invalid"
    assert not result.syndrome_valid
    assert "does not satisfy" in result.message
    assert decoder.decode((0, 0)).status == "ok"


def test_decoder_contract_rejects_malformed_input() -> None:
    code = repetition_code(3)
    decoder = RepetitionMajorityDecoder(code)
    assert decoder.decode((1,)).status == "error"
    assert decoder.decode((2, 0)).status == "error"
    assert decoder.decode([1, 0]).status == "ok"
    with pytest.raises(DecoderInputError):
        decoder.decode((0, 0), timeout_seconds=0.0)


def test_decoder_timeout_is_reported_separately() -> None:
    code = repetition_code(7)
    decoder = ExactDecoder(code, bit_flip(0.01))
    result = decoder.decode((1, 0, 0, 0, 0, 0), timeout_seconds=1e-12)
    assert result.status in {"timeout", "ok"}
    if result.status == "timeout":
        assert not result.syndrome_valid


def test_decoder_spec_hash_changes_with_configuration() -> None:
    first = DecoderSpec(
        "a", "1", "pauli", ("repetition",), ("bit flip",), True, {"p": 0.1}
    )
    second = DecoderSpec(
        "a", "1", "pauli", ("repetition",), ("bit flip",), True, {"p": 0.2}
    )
    assert first.config_hash != second.config_hash


def test_exact_decoder_rejects_excessive_enumeration() -> None:
    code = repetition_code(5)
    with pytest.raises(DecoderInputError):
        ExactDecoder(code, bit_flip(0.1), max_enumeration=10)
    with pytest.raises(DecoderInputError):
        ExactDecoder(code, bit_flip(0.1), mode="wrong")  # type: ignore[arg-type]
    with pytest.raises(DecoderInputError):
        ExactDecoder(code, bit_flip(0.1), max_weight=6)


def test_lookup_decoder_alias_and_table_size() -> None:
    code = repetition_code(3)
    decoder = LookupDecoder(code, bit_flip(0.1))
    assert isinstance(decoder, ExactDecoder)
    assert decoder.table_size == 4
    assert decoder.correction_weight((1, 0)) == 1
    # Two X patterns (100 and 011) share the syndrome; each has 2^3 Z/Y choices.
    assert decoder.degeneracy((1, 0)) == 16


def test_mwpm_rejects_non_css_code() -> None:
    pytest.importorskip("pymatching")
    code = steane_code()
    with pytest.raises(DecoderInputError):
        PauliMWPMDecoder(code, error_probability=0.1)


def test_exact_decoder_maximum_likelihood_prefers_likely_error() -> None:
    code = repetition_code(3)
    channel = bit_flip(0.2)
    decoder = ExactDecoder(code, channel, mode="maximum_likelihood")
    syndrome = (1, 0)
    result = decoder.decode(syndrome)
    assert result.status == "ok"
    assert result.correction is not None
    assert result.correction.weight == 1


def test_batch_decode_matches_individual_decode() -> None:
    code = repetition_code(5)
    decoder = ExactDecoder(code, bit_flip(0.1))
    syndromes = [(0, 0, 0, 0), (1, 0, 0, 0), (1, 1, 0, 0), (1, 1, 1, 1)]
    batch = decoder.decode_batch(syndromes)
    individual = [decoder.decode(syndrome) for syndrome in syndromes]
    assert [item.correction for item in batch] == [item.correction for item in individual]  # type: ignore[list-item]
    assert np.all([item.status == "ok" for item in batch])
