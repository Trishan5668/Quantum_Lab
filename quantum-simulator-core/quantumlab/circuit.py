"""Circuit definition and execution engine.

A ``CircuitDefinition`` is a plain dataclass describing the JSON
payload the FastAPI bridge receives from the desktop client. The
executor materializes each placement into a real ``GateMatrix`` and
applies it via ``StateVector.apply_gate`` (default) or
``DensityMatrix.apply_unitary`` when ``mode="density"``.

Per project rules, ``Measure`` is treated as a marker: it does NOT
collapse the simulated state because the educational UI needs the
post-circuit probability distribution for visualization.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from time import perf_counter
from typing import Any, Literal, overload

import numpy as np

from quantumlab.density import DensityMatrix
from quantumlab.exceptions import (
    InvalidGateError,
    QubitIndexError,
    SimulationError,
)
from quantumlab.gates import CNOT, RX, RY, RZ, GateMatrix, H, X, Y, Z
from quantumlab.noise import NoiseConfig, apply_noise, build_channel
from quantumlab.state import StateVector
from quantumlab.tensor_networks import MPS, MPSConfig

GateType = Literal[
    "H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT", "M"
]
SimulationMode = Literal["statevector", "density", "mps"]

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
    stack_count: int = 1


@dataclass(frozen=True)
class CircuitDefinition:
    num_qubits: int
    gates: list[GatePlacement]

    def validate(self, max_qubits: int = 8) -> None:
        if self.num_qubits < 1 or self.num_qubits > max_qubits:
            raise SimulationError(
                f"num_qubits must be in [1, {max_qubits}], got {self.num_qubits}"
            )
        for g in self.gates:
            if g.stack_count < 1:
                raise SimulationError(
                    f"gate {g.id} stack_count must be >= 1, got {g.stack_count}"
                )
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
    stack_count: int
    state_after: StateVector
    probabilities: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "qubit_targets": list(self.qubit_targets),
            "params": dict(self.params),
            "time_step": self.time_step,
            "stack_count": self.stack_count,
            "state_after": self.state_after.to_dict(),
            "probabilities": [float(p) for p in self.probabilities],
        }


@dataclass
class DensityStepResult:
    gate_id: str
    gate_type: str
    qubit_targets: list[int]
    params: dict[str, float]
    time_step: int
    stack_count: int
    density_after: DensityMatrix
    probabilities: np.ndarray
    purity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "qubit_targets": list(self.qubit_targets),
            "params": dict(self.params),
            "time_step": self.time_step,
            "stack_count": self.stack_count,
            "density_after": self.density_after.to_dict(),
            "probabilities": [float(p) for p in self.probabilities],
            "purity": self.purity,
        }


@dataclass
class CircuitResult:
    steps: list[StepResult]
    final_state: StateVector
    execution_time_ms: float
    num_qubits: int
    simulation_mode: SimulationMode = "statevector"

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_qubits": self.num_qubits,
            "execution_time_ms": self.execution_time_ms,
            "simulation_mode": self.simulation_mode,
            "steps": [s.to_dict() for s in self.steps],
            "final_state": self.final_state.to_dict(),
        }


@dataclass
class DensityCircuitResult:
    steps: list[DensityStepResult]
    final_density: DensityMatrix
    execution_time_ms: float
    num_qubits: int
    simulation_mode: SimulationMode = "density"
    mixed_state: bool = False
    noise_enabled: bool = False
    noise_channel: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "num_qubits": self.num_qubits,
            "execution_time_ms": self.execution_time_ms,
            "simulation_mode": self.simulation_mode,
            "mixed_state": self.mixed_state,
            "noise_enabled": self.noise_enabled,
            "noise_channel": self.noise_channel,
            "steps": [s.to_dict() for s in self.steps],
            "final_density": self.final_density.to_dict(),
            "purity": self.final_density.purity(),
        }
        if self.final_density.is_pure():
            payload["final_state"] = self.final_density.to_statevector().to_dict()
        else:
            probs = self.final_density.probabilities()
            payload["final_state"] = {
                "num_qubits": self.num_qubits,
                "amplitudes": [],
                "probabilities": [float(p) for p in probs],
                "basis_labels": [
                    self.final_density.basis_label(i)
                    for i in range(1 << self.num_qubits)
                ],
            }
        return payload


@dataclass
class MPSCircuitResult:
    """MPS result which never expands a large quantum state for transport."""

    final_mps: MPS
    execution_time_ms: float
    num_qubits: int
    simulation_mode: SimulationMode = "mps"

    def to_dict(self) -> dict[str, Any]:
        state: dict[str, Any] = {"num_qubits": self.num_qubits, "amplitudes": [], "probabilities": [], "basis_labels": []}
        if self.num_qubits <= 12:
            amplitudes = self.final_mps.to_statevector(max_qubits=12)
            state = {
                "num_qubits": self.num_qubits,
                "amplitudes": [{"real": float(a.real), "imag": float(a.imag)} for a in amplitudes],
                "probabilities": [float(abs(a) ** 2) for a in amplitudes],
                "basis_labels": [f"|{i:0{self.num_qubits}b}>" for i in range(1 << self.num_qubits)],
            }
        return {"num_qubits": self.num_qubits, "execution_time_ms": self.execution_time_ms,
                "simulation_mode": "mps", "steps": [], "final_state": state,
                "tensor_network": self.final_mps.metadata()}


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


@lru_cache(maxsize=128)
def _cached_matrix_power(matrix_key: bytes, shape: tuple[int, int], n: int) -> GateMatrix:
    matrix = np.frombuffer(matrix_key, dtype=np.complex128).reshape(shape)
    result = np.eye(shape[0], dtype=np.complex128)
    for _ in range(n):
        result = matrix @ result
    return result.copy()


def _effective_gate(placement: GatePlacement) -> GateMatrix | None:
    gate = _resolve_gate(placement)
    if gate is None:
        return None
    n = max(1, int(placement.stack_count))
    if n == 1:
        return gate
    contiguous = np.ascontiguousarray(gate, dtype=np.complex128)
    return _cached_matrix_power(contiguous.tobytes(), contiguous.shape, n)


def _noise_wires(
    placement: GatePlacement, noise: NoiseConfig, num_qubits: int
) -> list[int]:
    if noise.target_qubits is not None:
        return list(noise.target_qubits)
    if len(placement.qubit_targets) == 1:
        return [placement.qubit_targets[0]]
    return list(range(num_qubits))


def run_step(state: StateVector, placement: GatePlacement) -> StepResult:
    """Apply a single placement to ``state`` and return a structured result."""
    gate = _effective_gate(placement)
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
        stack_count=placement.stack_count,
        state_after=new_state,
        probabilities=new_state.probabilities(),
    )


def run_density_step(
    density: DensityMatrix,
    placement: GatePlacement,
    noise: NoiseConfig | None = None,
) -> DensityStepResult:
    """Apply a gate (and optional noise) to a density matrix."""
    gate = _effective_gate(placement)
    new_density = density
    if gate is not None:
        new_density = new_density.apply_unitary(gate, placement.qubit_targets)
    if noise is not None and noise.enabled and gate is not None:
        channel = build_channel(noise)
        wires = _noise_wires(placement, noise, new_density.num_qubits)
        new_density = apply_noise(new_density, channel, wires)
    return DensityStepResult(
        gate_id=placement.id,
        gate_type=placement.gate_type,
        qubit_targets=list(placement.qubit_targets),
        params=dict(placement.params),
        time_step=placement.time_step,
        stack_count=placement.stack_count,
        density_after=new_density,
        probabilities=new_density.probabilities(),
        purity=new_density.purity(),
    )


@overload
def run_circuit(
    circuit: CircuitDefinition,
    *,
    mode: Literal["statevector"] = "statevector",
    noise: NoiseConfig | None = None,
    initial_state: StateVector | None = None,
) -> CircuitResult: ...


@overload
def run_circuit(
    circuit: CircuitDefinition,
    *,
    mode: Literal["density"],
    noise: NoiseConfig | None = None,
    initial_state: StateVector | None = None,
) -> DensityCircuitResult: ...


def run_circuit(
    circuit: CircuitDefinition,
    *,
    mode: SimulationMode = "statevector",
    noise: NoiseConfig | None = None,
    initial_state: StateVector | None = None,
    initial_mps: MPS | None = None,
    mps_config: MPSConfig | None = None,
) -> CircuitResult | DensityCircuitResult | MPSCircuitResult:
    """Execute the entire circuit, returning per-step and final results."""
    circuit.validate(max_qubits=256 if mode == "mps" else 8)
    if mode == "mps":
        if noise is not None and noise.enabled:
            raise SimulationError("noise channels are not supported by the pure-state MPS backend")
        mps = initial_mps if initial_mps is not None else MPS.zero(circuit.num_qubits, mps_config)
        if mps.num_qubits != circuit.num_qubits:
            raise SimulationError("initial MPS qubit count does not match circuit")
        t0 = perf_counter()
        for placement in sorted(circuit.gates, key=lambda g: (g.time_step, g.id)):
            gate = _effective_gate(placement)
            if gate is not None:
                mps.apply_gate(gate, placement.qubit_targets)
        return MPSCircuitResult(mps, (perf_counter() - t0) * 1000.0, circuit.num_qubits)
    noise_cfg = noise or NoiseConfig()
    use_density = mode == "density" or noise_cfg.enabled

    t0 = perf_counter()
    ordered = sorted(circuit.gates, key=lambda g: (g.time_step, g.id))

    if not use_density:
        state = initial_state if initial_state is not None else StateVector.zero(
            circuit.num_qubits
        )
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
            simulation_mode="statevector",
        )

    init = initial_state if initial_state is not None else StateVector.zero(
        circuit.num_qubits
    )
    density = DensityMatrix.from_statevector(init)
    dsteps: list[DensityStepResult] = []
    active_noise = noise_cfg if noise_cfg.enabled else None
    for placement in ordered:
        dstep = run_density_step(density, placement, active_noise)
        dsteps.append(dstep)
        density = dstep.density_after
    elapsed_ms = (perf_counter() - t0) * 1000.0
    return DensityCircuitResult(
        steps=dsteps,
        final_density=density,
        execution_time_ms=elapsed_ms,
        num_qubits=circuit.num_qubits,
        simulation_mode="density",
        mixed_state=not density.is_pure(),
        noise_enabled=noise_cfg.enabled,
        noise_channel=noise_cfg.channel if noise_cfg.enabled else None,
    )
