"""Circuit execution endpoints."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter

from quantumlab.circuit import (
    CircuitDefinition,
    GatePlacement,
    run_circuit,
    run_step,
)
from quantumlab.state import StateVector
from quantumlab.tensor_networks import MPS, MPSConfig

from app.models import (
    CircuitIn,
    CircuitRunOut,
    StepOut,
    StepRequest,
    envelope,
)


router = APIRouter(prefix="/api/v1/circuit", tags=["circuit"])


def _circuit_from_in(payload: CircuitIn) -> CircuitDefinition:
    placements = [
        GatePlacement(
            id=g.id,
            gate_type=g.gate_type,
            qubit_targets=list(g.qubit_targets),
            params=dict(g.params),
            time_step=g.time_step,
            stack_count=g.stack_count,
        )
        for g in payload.gates
    ]
    return CircuitDefinition(num_qubits=payload.num_qubits, gates=placements)


def _initial_state_from_basis(payload: CircuitIn) -> StateVector:
    basis = payload.initial_basis_state or ("0" * payload.num_qubits)
    if len(basis) != payload.num_qubits or any(bit not in "01" for bit in basis):
        basis = "0" * payload.num_qubits
    amps = np.zeros(1 << payload.num_qubits, dtype=np.complex128)
    amps[int(basis, 2)] = 1.0
    return StateVector(amplitudes=amps, num_qubits=payload.num_qubits)


@router.post("/run")
async def run(payload: CircuitIn) -> dict[str, object]:
    """Execute the full circuit and return per-step + final state."""
    circuit = _circuit_from_in(payload)
    backend = payload.simulation_backend
    if backend == "auto":
        backend = "mps" if payload.num_qubits > 8 else "statevector"
    if backend == "mps":
        basis = payload.initial_basis_state or ("0" * payload.num_qubits)
        if len(basis) != payload.num_qubits or any(bit not in "01" for bit in basis):
            basis = "0" * payload.num_qubits
        config = MPSConfig(max_bond_dimension=payload.max_bond_dimension, truncation_cutoff=payload.truncation_cutoff)
        result = run_circuit(circuit, mode="mps", initial_mps=MPS.basis(basis, config))
        return envelope(result.to_dict())
    result = run_circuit(circuit, mode="density" if backend == "density" else "statevector", initial_state=_initial_state_from_basis(payload))
    out = CircuitRunOut.model_validate(result.to_dict())
    return envelope(out.model_dump())


@router.post("/step")
async def step(payload: StepRequest) -> dict[str, object]:
    """Apply one placement to a caller-provided state, returning a StepResult."""
    amps = np.array(
        [complex(a.real, a.imag) for a in payload.state_in],
        dtype=np.complex128,
    )
    state = StateVector(amplitudes=amps, num_qubits=payload.num_qubits)
    placement = GatePlacement(
        id=payload.placement.id,
        gate_type=payload.placement.gate_type,
        qubit_targets=list(payload.placement.qubit_targets),
        params=dict(payload.placement.params),
        time_step=payload.placement.time_step,
        stack_count=payload.placement.stack_count,
    )
    step_result = run_step(state, placement)
    out = StepOut.model_validate(step_result.to_dict())
    return envelope(out.model_dump())
