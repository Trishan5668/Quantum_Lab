"""Cross-validation against Qiskit as mathematical ground truth.

QuantumLab uses big-endian tensor products (q[0] is MSB). Qiskit uses
little-endian statevector indexing (qubit 0 is LSB). Wire remap
``qiskit_q = n - 1 - qlab_q`` aligns equivalent circuits.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest

qiskit = pytest.importorskip("qiskit")

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector as QiskitStatevector

from quantumlab.circuit import CircuitDefinition, GatePlacement, run_circuit
from quantumlab.density import DensityMatrix
from quantumlab.entropy import entanglement_entropy
from quantumlab.fidelity import bell_state_vector, fidelity
from quantumlab.gates import CNOT, RX, RY, RZ, H, X, Y, Z
from quantumlab.state import StateVector

_ATOL = 1e-10


def _qiskit_wire(n: int, qlab_q: int) -> int:
    return n - 1 - qlab_q


def _qlab_state(num_qubits: int, ops: list[tuple]) -> np.ndarray:
    sv = StateVector.zero(num_qubits)
    for op in ops:
        factory, targets, *params = op
        gate = factory(*params) if params else factory()
        sv = sv.apply_gate(gate, list(targets))
    return sv.amplitudes


def _qiskit_from_qlab_ops(
    num_qubits: int,
    ops: list[tuple],
) -> np.ndarray:
    qc = QuantumCircuit(num_qubits)
    for op in ops:
        factory, targets, *params = op
        wires = [_qiskit_wire(num_qubits, t) for t in targets]
        name = factory.__name__
        if name == "H":
            qc.h(wires[0])
        elif name == "X":
            qc.x(wires[0])
        elif name == "Y":
            qc.y(wires[0])
        elif name == "Z":
            qc.z(wires[0])
        elif name == "RX":
            qc.rx(params[0], wires[0])
        elif name == "RY":
            qc.ry(params[0], wires[0])
        elif name == "RZ":
            qc.rz(params[0], wires[0])
        elif name == "CNOT":
            qc.cx(wires[0], wires[1])
        else:
            raise ValueError(f"unsupported gate {name}")
    return QiskitStatevector(qc).data


def _assert_states_equal(qlab: np.ndarray, qiskit_sv: np.ndarray) -> None:
    overlap = np.vdot(qiskit_sv, qlab)
    if abs(overlap) > _ATOL:
        phase = overlap / abs(overlap)
        qlab = qlab * phase.conj()
    assert np.allclose(qlab, qiskit_sv, atol=_ATOL), (
        f"QLab: {np.round(qlab, 6)}\nQiskit: {np.round(qiskit_sv, 6)}"
    )


def _assert_circuit_matches(num_qubits: int, ops: list[tuple]) -> None:
    _assert_states_equal(_qlab_state(num_qubits, ops), _qiskit_from_qlab_ops(num_qubits, ops))


@pytest.mark.parametrize("factory", [H, X, Y, Z])
def test_single_qubit_gates_match_qiskit(factory: Callable) -> None:
    _assert_circuit_matches(1, [(factory, (0,))])


@pytest.mark.parametrize("factory,theta", [(RX, 0.7), (RY, 1.2), (RZ, -0.9)])
def test_rotation_gates_match_qiskit(factory: Callable, theta: float) -> None:
    _assert_circuit_matches(1, [(factory, (0,), theta)])


def test_cnot_bell_matches_qiskit() -> None:
    _assert_circuit_matches(2, [(H, (0,)), (CNOT, (0, 1))])


def test_cnot_reverse_wires_matches_qiskit() -> None:
    _assert_circuit_matches(2, [(X, (1,)), (CNOT, (1, 0))])


def test_cnot_non_adjacent_matches_qiskit() -> None:
    _assert_circuit_matches(3, [(X, (0,)), (CNOT, (0, 2))])


def test_ghz_state_matches_qiskit() -> None:
    _assert_circuit_matches(
        3, [(H, (0,)), (CNOT, (0, 1)), (CNOT, (1, 2))]
    )


def test_deutsch_algorithm_matches_qiskit() -> None:
    _assert_circuit_matches(
        2,
        [
            (X, (1,)),
            (H, (0,)),
            (H, (1,)),
            (CNOT, (0, 1)),
            (H, (0,)),
        ],
    )


def test_deutsch_jozsa_balanced_matches_qiskit() -> None:
    _assert_circuit_matches(
        3,
        [
            (X, (2,)),
            (H, (0,)),
            (H, (1,)),
            (H, (2,)),
            (CNOT, (0, 2)),
            (H, (0,)),
            (H, (1,)),
        ],
    )


def test_bernstein_vazirani_matches_qiskit() -> None:
    _assert_circuit_matches(
        3,
        [
            (H, (0,)),
            (H, (1,)),
            (H, (2,)),
            (Z, (2,)),
            (CNOT, (0, 2)),
            (H, (0,)),
            (H, (1,)),
            (H, (2,)),
        ],
    )


def test_grover_2q_matches_qiskit() -> None:
    _assert_circuit_matches(
        2,
        [
            (H, (0,)),
            (H, (1,)),
            (Z, (1,)),
            (CNOT, (0, 1)),
            (H, (0,)),
            (H, (1,)),
        ],
    )


def test_qft_3q_matches_qiskit() -> None:
    theta2 = math.pi / 2
    theta4 = math.pi / 4
    _assert_circuit_matches(
        3,
        [
            (H, (0,)),
            (RZ, (1,), theta2),
            (CNOT, (0, 1)),
            (H, (1,)),
            (RZ, (2,), theta4),
            (CNOT, (1, 2)),
            (H, (2,)),
        ],
    )


def test_run_circuit_api_matches_qiskit_bell() -> None:
    circuit = CircuitDefinition(
        num_qubits=2,
        gates=[
            GatePlacement("g1", "H", [0], {}, 0),
            GatePlacement("g2", "CNOT", [0, 1], {}, 1),
        ],
    )
    result = run_circuit(circuit)
    qiskit_sv = _qiskit_from_qlab_ops(2, [(H, (0,)), (CNOT, (0, 1))])
    _assert_states_equal(result.final_state.amplitudes, qiskit_sv)


def test_bell_entanglement_entropy_matches_theory() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    rho = DensityMatrix.from_statevector(sv)
    entropy = entanglement_entropy(rho, [0])
    assert entropy == pytest.approx(1.0, abs=_ATOL)


def test_bell_fidelity_to_target() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    target = StateVector.from_amplitudes(bell_state_vector(2))
    assert fidelity(sv, target) == pytest.approx(1.0, abs=_ATOL)


def test_mixed_fidelity_bell_reduced_state() -> None:
    sv = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])
    rho_full = DensityMatrix.from_statevector(sv)
    rho_reduced = rho_full.partial_trace([0])
    identity = DensityMatrix.maximally_mixed(1)
    assert fidelity(rho_reduced, identity) == pytest.approx(1.0, abs=0.01)
