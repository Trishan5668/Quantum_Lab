"""Circuit definition and execution engine.

A ``CircuitDefinition`` is a plain dataclass describing the JSON
payload the FastAPI bridge receives from the desktop client. The
executor materializes each placement into a real ``GateMatrix`` and
applies it via ``StateVector.apply_gate``.

Per project rules, ``Measure`` is treated as a marker: it does NOT
collapse the simulated state because the educational UI needs the
post-circuit probability distribution for visualization. A separate
sampling endpoint can be added later if required.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

import numpy as np

from quantumlab.exceptions import (
    InvalidGateError,
    QubitIndexError,
    SimulationError,
)
from quantumlab.gates import CNOT, RX, RY, RZ, GateMatrix, H, X, Y, Z
from quantumlab.state import StateVector

GateType = Literal[
    "H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT", "M"
]

_SINGLE_QUBIT_GATES: dict[str, GateMatrix] = {
    "H": H(),
    "X": X(),
    "Y": Y(),
    "Z": Z(),
}
_ROTATION_GATES: dict[str, Callable[[float], GateMatrix]] = {
    "RX": RX,
    "RY": RY,
    "RZ": RZ,
}


@dataclass(frozen=True)
class GatePlacement:
    """A single gate at a specific time-step of the circuit."""

    id: str
    gate_type: str
    qubit_targets: list[int]
    params: dict[str, float] = field(default_factory=dict)
    time_step: int = 0


@dataclass(frozen=True)
class CircuitDefinition:
    num_qubits: int
    gates: list[GatePlacement]

    def validate(self) -> None:
        if self.num_qubits < 1 or self.num_qubits > 8:
            raise SimulationError(
                f"num_qubits must be in [1, 8], got {self.num_qubits}"
            )
        for g in self.gates:
            for q in g.qubit_targets:
                if not (0 <= q < self.num_qubits):
                    raise QubitIndexError(
                        f"gate {g.id} targets qubit {q} "
                        f"out of range [0, {self.num_qubits - 1}]"
                    )


@dataclass
class StepResult:
    gate_id: str
    gate_type: str
    qubit_targets: list[int]
    params: dict[str, float]
    time_step: int
    state_after: StateVector
    probabilities: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "qubit_targets": list(self.qubit_targets),
            "params": dict(self.params),
            "time_step": self.time_step,
            "state_after": self.state_after.to_dict(),
            "probabilities": [float(p) for p in self.probabilities],
        }


@dataclass
class CircuitResult:
    steps: list[StepResult]
    final_state: StateVector
    execution_time_ms: float
    num_qubits: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_qubits": self.num_qubits,
            "execution_time_ms": self.execution_time_ms,
            "steps": [s.to_dict() for s in self.steps],
            "final_state": self.final_state.to_dict(),
        }


def _resolve_gate(placement: GatePlacement) -> GateMatrix | None:
    """Materialize the gate matrix for a placement.

    Returns ``None`` for measurement markers (they do not transform the state).
    """
    gt = placement.gate_type
    if gt == "M":
        return None
    if gt in _SINGLE_QUBIT_GATES:
        if len(placement.qubit_targets) != 1:
            raise InvalidGateError(
                f"single-qubit gate {gt} expects 1 target, got {placement.qubit_targets}"
            )
        return _SINGLE_QUBIT_GATES[gt]
    if gt in _ROTATION_GATES:
        if len(placement.qubit_targets) != 1:
            raise InvalidGateError(
                f"rotation gate {gt} expects 1 target, got {placement.qubit_targets}"
            )
        if "theta" not in placement.params:
            raise InvalidGateError(
                f"rotation gate {gt} requires a 'theta' parameter"
            )
        theta = float(placement.params["theta"])
        return _ROTATION_GATES[gt](theta)
    if gt == "CNOT":
        if len(placement.qubit_targets) != 2:
            raise InvalidGateError(
                f"CNOT expects 2 targets [control, target], got {placement.qubit_targets}"
            )
        return CNOT()
    raise InvalidGateError(f"unknown gate type: {gt!r}")


def run_step(state: StateVector, placement: GatePlacement) -> StepResult:
    """Apply a single placement to ``state`` and return a structured result."""
    gate = _resolve_gate(placement)
    if gate is None:
        new_state = state
    else:
        new_state = state.apply_gate(gate, placement.qubit_targets)
    return StepResult(
        gate_id=placement.id,
        gate_type=placement.gate_type,
        qubit_targets=list(placement.qubit_targets),
        params=dict(placement.params),
        time_step=placement.time_step,
        state_after=new_state,
        probabilities=new_state.probabilities(),
    )


def run_circuit(circuit: CircuitDefinition) -> CircuitResult:
    """Execute the entire circuit, returning per-step and final results."""
    circuit.validate()
    t0 = perf_counter()
    ordered = sorted(circuit.gates, key=lambda g: (g.time_step, g.id))
    state = StateVector.zero(circuit.num_qubits)
    steps: list[StepResult] = []
    for placement in ordered:
        step = run_step(state, placement)
        steps.append(step)
        state = step.state_after
    elapsed_ms = (perf_counter() - t0) * 1000.0
    return CircuitResult(
        steps=steps,
        final_state=state,
        execution_time_ms=elapsed_ms,
        num_qubits=circuit.num_qubits,
    )
