from __future__ import annotations

import itertools

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from quantumlab.research.qec.pauli import (
    Pauli,
    PauliError,
    commutation_matrix,
    enumerate_paulis,
    gf2_in_span,
    gf2_rank,
    gf2_reduce,
    pauli_from_int,
    symplectic_product,
)


def test_pauli_label_round_trip() -> None:
    for label in ("I", "X", "Y", "Z", "ZZI", "IZZ", "XXX", "-Y", "+XIZ"):
        pauli = Pauli.from_string(label)
        assert Pauli.from_string(pauli.label()) == pauli


def test_pauli_multiplication_matches_matrices() -> None:
    for left in ("I", "X", "Y", "Z"):
        for right in ("I", "X", "Y", "Z"):
            a = Pauli.from_string(left)
            b = Pauli.from_string(right)
            assert np.allclose((a * b).matrix(), a.matrix() @ b.matrix())


def test_anticommutation_of_distinct_paulis() -> None:
    x = Pauli.from_string("X")
    y = Pauli.from_string("Y")
    z = Pauli.from_string("Z")
    assert not x.commutes(y)
    assert not x.commutes(z)
    assert not y.commutes(z)
    assert x.commutes(x)


def test_y_is_hermitian_and_xz_is_not() -> None:
    assert Pauli.from_string("Y").is_hermitian()
    xz = Pauli.from_string("X") * Pauli.from_string("Z")
    assert not xz.is_hermitian()
    assert (xz * xz).is_identity()
    assert (xz * xz).phase == 2  # (XZ)^2 = -I


def test_phase_conjugation_and_adjoint() -> None:
    pauli = Pauli.from_string("Y")
    assert np.allclose(pauli.adjoint().matrix(), pauli.matrix().conj().T)
    assert np.allclose((pauli * pauli).matrix(), np.eye(2))


def test_invalid_pauli_inputs() -> None:
    with pytest.raises(PauliError):
        Pauli.from_string("")
    with pytest.raises(PauliError):
        Pauli.from_string("AB")
    with pytest.raises(PauliError):
        Pauli(4, 0, 0, 2)
    with pytest.raises(PauliError):
        Pauli(0, 0, -1, 2)
    with pytest.raises(PauliError):
        Pauli(0, 0, 0, 0)
    with pytest.raises(PauliError):
        Pauli.from_string("X").commutes(Pauli.from_string("XX"))


def test_gf2_rank_and_span() -> None:
    assert gf2_rank([0b110, 0b101, 0b011], 3) == 2
    assert gf2_rank([], 3) == 0
    assert gf2_in_span([0b110, 0b101], 0b011, 3)
    assert not gf2_in_span([0b110, 0b101], 0b111, 3)
    in_span, residual, basis = gf2_reduce([0b110, 0b101], 0b111, 3)
    assert not in_span
    assert residual != 0
    assert basis


def test_pauli_enumeration_counts_and_hermiticity() -> None:
    for n in (1, 2, 3):
        operators = list(enumerate_paulis(n))
        assert len(operators) == 4**n
        assert all(operator.is_hermitian() for operator in operators)
        assert len({(p.x, p.z, p.phase) for p in operators}) == 4**n
    assert sum(1 for _ in enumerate_paulis(3, max_weight=1)) == 1 + 3 * 3
    assert all(p.weight == 1 for p in enumerate_paulis(3, min_weight=1, max_weight=1))
    assert {p.weight for p in enumerate_paulis(3, min_weight=2, max_weight=2)} == {2}


def test_pauli_from_int_is_injective() -> None:
    for n in (1, 3):
        generated = [(p.x, p.z, p.phase) for p in (pauli_from_int(i, n) for i in range(4**n))]
        assert len(set(generated)) == 4**n


def test_commutation_matrix_is_symmetric_with_zero_diagonal() -> None:
    paulis = [Pauli.from_string(label) for label in ("I", "X", "Y", "Z")]
    matrix = commutation_matrix(paulis)
    for i in range(4):
        assert matrix[i][i] == 0
        for j in range(4):
            assert matrix[i][j] == matrix[j][i]


@given(
    x=st.integers(min_value=0, max_value=63),
    z=st.integers(min_value=0, max_value=63),
    phase=st.integers(min_value=0, max_value=3),
    other_x=st.integers(min_value=0, max_value=63),
    other_z=st.integers(min_value=0, max_value=63),
    other_phase=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=100, deadline=None)
def test_property_product_matches_matrix_and_label(
    x: int, z: int, phase: int, other_x: int, other_z: int, other_phase: int
) -> None:
    a = Pauli(x, z, phase, 6)
    b = Pauli(other_x, other_z, other_phase, 6)
    product = a * b
    assert np.allclose(product.matrix(), a.matrix() @ b.matrix(), atol=1e-10)
    assert np.allclose((product * a).matrix(), product.matrix() @ a.matrix(), atol=1e-10)


@given(
    x=st.integers(min_value=0, max_value=255),
    z=st.integers(min_value=0, max_value=255),
    other_x=st.integers(min_value=0, max_value=255),
    other_z=st.integers(min_value=0, max_value=255),
)
@settings(max_examples=100, deadline=None)
def test_property_symplectic_product_antisymmetric(
    x: int, z: int, other_x: int, other_z: int
) -> None:
    a = Pauli(x, z, 0, 8)
    b = Pauli(other_x, other_z, 0, 8)
    assert symplectic_product(a, b) == symplectic_product(b, a)


def test_symplectic_product_matches_commutator_for_all_two_qubit_paulis() -> None:
    for left in enumerate_paulis(2, max_weight=2):
        for right in enumerate_paulis(2, max_weight=2):
            commutator = left.matrix() @ right.matrix() - right.matrix() @ left.matrix()
            commutes = bool(np.allclose(commutator, np.zeros((4, 4))))
            assert commutes == (symplectic_product(left, right) == 0)


def test_enumeration_rejects_bad_bounds() -> None:
    with pytest.raises(ValueError):
        list(enumerate_paulis(0))
    with pytest.raises(ValueError):
        list(enumerate_paulis(2, max_weight=3))
    with pytest.raises(ValueError):
        list(enumerate_paulis(2, min_weight=2, max_weight=1))


def test_all_single_qubit_paulis_have_unit_modulus_eigenvalues() -> None:
    for label in "IXYZ":
        matrix = Pauli.from_string(label).matrix()
        eigenvalues = np.linalg.eigvalsh(matrix)
        assert np.allclose(np.abs(eigenvalues), 1.0)
    products = list(itertools.product("IXYZ", repeat=2))
    assert len(products) == 16
