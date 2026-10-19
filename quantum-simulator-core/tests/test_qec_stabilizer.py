from __future__ import annotations

import numpy as np
import pytest

from quantumlab.research.qec.codes import (
    UnsupportedCodeFamilyError,
    five_qubit_code,
    make_code,
    repetition_code,
    steane_code,
)
from quantumlab.research.qec.pauli import Pauli, enumerate_paulis
from quantumlab.research.qec.stabilizer import (
    DistanceComputationError,
    EncodingUnavailableError,
    ResidualClass,
    StabilizerCodeError,
    build_code,
)


@pytest.mark.parametrize(
    "code",
    [repetition_code(3), repetition_code(5), steane_code(), five_qubit_code()],
)
def test_declared_codes_validate_algebraically(code) -> None:
    validation = code.validate()
    assert validation.ok
    assert validation.generators_commute
    assert validation.generators_independent
    assert validation.logicals_commute_with_stabilizers
    assert validation.logicals_anticommute_correctly
    assert validation.logicals_independent_modulo_stabilizers
    assert validation.hermitian
    assert code.stabilizer_rank() == code.num_stabilizers
    assert code.num_logical_qubits == 1


@pytest.mark.parametrize(
    ("code", "full", "x_distance", "z_distance"),
    [
        (repetition_code(3), 1, 3, 1),
        (repetition_code(5), 1, 5, 1),
        (steane_code(), 3, 3, 3),
        (five_qubit_code(), 3, 3, 3),
    ],
)
def test_exact_distances(code, full: int, x_distance: int, z_distance: int) -> None:
    assert code.distance(kind="full") == full
    assert code.distance(kind="x") == x_distance
    assert code.distance(kind="z") == z_distance


@pytest.mark.parametrize("code", [repetition_code(3), steane_code(), five_qubit_code()])
def test_code_space_dimension_and_projector(code) -> None:
    projector = code.code_space_projector()
    assert np.allclose(projector @ projector, projector, atol=1e-10)
    assert np.allclose(projector, projector.conj().T, atol=1e-12)
    assert code.code_space_dimension() == 1 << code.num_logical_qubits
    assert np.trace(projector).real == pytest.approx(2**code.num_logical_qubits, rel=1e-9)


@pytest.mark.parametrize("code", [repetition_code(3), steane_code(), five_qubit_code()])
def test_encoder_preserves_logical_algebra(code) -> None:
    assert code.validate_encoder()
    logical_zero = np.zeros(2, dtype=np.complex128)
    logical_zero[0] = 1.0
    physical_zero = code.encode_state(logical_zero)
    assert abs(float(np.vdot(physical_zero, physical_zero).real) - 1.0) < 1e-10
    for generator in code.stabilizers:
        assert np.vdot(physical_zero, generator.matrix() @ physical_zero).real == pytest.approx(
            1.0, abs=1e-8
        )
    logical_plus = np.ones(2, dtype=np.complex128) / np.sqrt(2.0)
    physical_plus = code.encode_state(logical_plus)
    assert abs(float(np.linalg.norm(physical_plus)) - 1.0) < 1e-10


@pytest.mark.parametrize("code", [repetition_code(3), steane_code(), five_qubit_code()])
def test_syndrome_linearity(code) -> None:
    errors = list(enumerate_paulis(code.num_qubits, max_weight=2))
    for left, right in zip(errors[::7], errors[1::7], strict=False):
        combined = left * right
        pairs = zip(code.syndrome(left), code.syndrome(right), strict=False)
        expected = tuple(a ^ b for a, b in pairs)
        assert code.syndrome(combined) == expected


@pytest.mark.parametrize("code", [repetition_code(3), steane_code(), five_qubit_code()])
def test_correction_matching_and_residual_classification(code) -> None:
    identity = Pauli.identity(code.num_qubits)
    assert code.syndrome(identity) == (0,) * code.num_stabilizers
    assert code.correction_matches_syndrome(identity, (0,) * code.num_stabilizers)
    assert code.classify_residual(identity) is ResidualClass.TRIVIAL
    logical_x = code.logical_x[0]
    assert code.classify_residual(logical_x, basis="z") is ResidualClass.LOGICAL_FAILURE
    assert code.classify_residual(logical_x, basis="x") is ResidualClass.TRIVIAL
    # A single-qubit error is generally not a valid residual (it is detectable).
    single = Pauli(1 << (code.num_qubits - 1), 0, 0, code.num_qubits)
    assert code.classify_residual(single) is ResidualClass.INVALID
    assert not code.correction_matches_syndrome(single, (0,) * code.num_stabilizers)


def test_repetition_code_is_not_a_quantum_distance_three_code() -> None:
    """The legacy benchmark's 'distance 3' is a bit-flip distance, not full d=3."""
    code = repetition_code(3)
    assert code.distance(kind="x") == 3
    assert code.distance(kind="full") == 1
    assert code.num_logical_qubits == 1


def test_bad_stabilizer_declarations_are_rejected() -> None:
    with pytest.raises(StabilizerCodeError):
        build_code(
            "noncommuting",
            2,
            (Pauli.from_string("XI"), Pauli.from_string("ZI")),
            (),
            (),
        )
    with pytest.raises(StabilizerCodeError):
        build_code(
            "dependent",
            3,
            (Pauli.from_string("ZZI"), Pauli.from_string("ZZI")),
            (Pauli.from_string("XXX"),),
            (Pauli.from_string("ZII"),),
        )
    with pytest.raises(StabilizerCodeError):
        build_code(
            "wrong_logical_count",
            3,
            (Pauli.from_string("ZZI"),),
            (),
            (),
        )
    with pytest.raises(StabilizerCodeError):
        build_code(
            "logical_in_stabilizer",
            2,
            (Pauli.from_string("ZI"),),
            (Pauli.from_string("ZI"),),
            (Pauli.from_string("IZ"),),
        )


def test_rejects_wrong_pauli_width() -> None:
    code = repetition_code(3)
    with pytest.raises(StabilizerCodeError):
        code.syndrome(Pauli.from_string("XX"))


def test_unsupported_family_and_even_repetition() -> None:
    with pytest.raises(UnsupportedCodeFamilyError):
        repetition_code(4)
    with pytest.raises(UnsupportedCodeFamilyError):
        repetition_code(1)
    with pytest.raises(UnsupportedCodeFamilyError):
        make_code("surface_code")
    with pytest.raises(UnsupportedCodeFamilyError):
        make_code("repetition")


def test_encoder_size_limits() -> None:
    code = repetition_code(11)
    with pytest.raises(EncodingUnavailableError):
        code.code_space_projector()
    with pytest.raises(DistanceComputationError):
        code.distance(kind="x")


def test_make_code_registry() -> None:
    assert make_code("steane").name == "steane_7_1_3"
    assert make_code("five_qubit").name == "five_qubit_5_1_3"
    assert make_code("repetition", 3).name == "repetition_d3"


def test_unknown_logical_basis_is_rejected() -> None:
    code = repetition_code(3)
    with pytest.raises(StabilizerCodeError):
        code.logical_action(Pauli.from_string("III"), basis="q")
