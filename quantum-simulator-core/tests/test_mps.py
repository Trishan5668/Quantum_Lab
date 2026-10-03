"""Cross-check the MPS backend against exact small statevectors."""

import numpy as np
import pytest

from quantumlab.gates import CNOT, H, X
from quantumlab.tensor_networks import MPS, MPSConfig


def test_bell_state_matches_exact_and_has_one_bit_entropy() -> None:
    state = MPS.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    expected = np.array([1 / np.sqrt(2), 0, 0, 1 / np.sqrt(2)], dtype=np.complex128)
    assert np.allclose(state.to_statevector(), expected)
    assert state.norm() == pytest.approx(1.0)
    assert state.entanglement_entropy(0) == pytest.approx(1.0)
    assert np.allclose(state.reduced_density_matrix(0), np.eye(2) / 2)
    assert state.expectation_pauli({0: "Z", 1: "Z"}) == pytest.approx(1.0)


def test_non_nearest_cnot_preserves_big_endian_wire_order() -> None:
    state = MPS.zero(3).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 2])
    expected = np.zeros(8, dtype=np.complex128)
    expected[0] = expected[5] = 1 / np.sqrt(2)  # |000> + |101>
    assert np.allclose(state.to_statevector(), expected)


def test_truncation_history_is_observable() -> None:
    state = MPS.zero(2, MPSConfig(max_bond_dimension=1)).apply_gate(H(), [0])
    state.apply_gate(CNOT(), [0, 1])
    assert state.truncation_history[-1].discarded_weight == pytest.approx(0.5)
    assert state.metadata()["cumulative_truncation_error"] == pytest.approx(0.5)


def test_sampling_uses_collapsed_mps_distribution() -> None:
    state = MPS.zero(2).apply_gate(X(), [1])
    assert state.sample(20, seed=9) == {"01": 20}
