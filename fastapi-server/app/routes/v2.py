"""QuantumLab API v2 — density mode, noise, and metrics."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter

from quantumlab.circuit import (
    CircuitDefinition,
    DensityCircuitResult,
    GatePlacement,
    run_circuit,
)
from quantumlab.density import DensityMatrix
from quantumlab.entropy import entanglement_entropy, interpret_entropy
from quantumlab.fidelity import interpret_fidelity, target_state_fidelity
from quantumlab.noise import NoiseConfig
from quantumlab.state import StateVector

from app.models import envelope
from app.models_v2 import (
    CircuitV2In,
    CircuitV2RunOut,
    DensityMatrixOut,
    EntropyOut,
    EntropyRequest,
    FidelityOut,
    FidelityRequest,
    PurityOut,
    PurityRequest,
    StateOut,
)


router = APIRouter(prefix="/api/v2", tags=["v2"])


def _circuit_from_in(payload: CircuitV2In) -> CircuitDefinition:
    placements = [
        GatePlacement(
            id=g.id,
            gate_type=g.gate_type,
            qubit_targets=list(g.qubit_targets),
            params=dict(g.params),
            time_step=g.time_step,
        )
        for g in payload.gates
    ]
    return CircuitDefinition(num_qubits=payload.num_qubits, gates=placements)


def _noise_from_in(payload: CircuitV2In) -> NoiseConfig:
    n = payload.simulation.noise
    return NoiseConfig(
        enabled=n.enabled,
        channel=n.channel,
        probability=n.probability,
        t1_us=n.t1_us,
        t2_us=n.t2_us,
        gate_time_ns=n.gate_time_ns,
        target_qubits=n.target_qubits,
    )


def _state_from_amplitudes(
    amps_in: list, num_qubits: int
) -> StateVector:
    amps = np.array(
        [complex(a.real, a.imag) for a in amps_in],
        dtype=np.complex128,
    )
    return StateVector(amplitudes=amps, num_qubits=num_qubits)


def _density_from_request(
    payload: FidelityRequest | EntropyRequest | PurityRequest,
) -> DensityMatrix:
    if payload.density_real is not None and payload.density_imag is not None:
        mat = np.array(payload.density_real, dtype=np.float64) + 1j * np.array(
            payload.density_imag, dtype=np.float64
        )
        return DensityMatrix.from_matrix(mat.astype(np.complex128), payload.num_qubits)
    if payload.amplitudes is not None:
        sv = _state_from_amplitudes(payload.amplitudes, payload.num_qubits)
        return DensityMatrix.from_statevector(sv)
    raise ValueError("provide amplitudes or density matrix")


def _density_out(dm: DensityMatrix) -> DensityMatrixOut:
    d = dm.to_dict()
    return DensityMatrixOut(
        num_qubits=d["num_qubits"],
        dim=d["dim"],
        real=d["real"],
        imag=d["imag"],
        probabilities=d["probabilities"],
        purity=d["purity"],
        basis_labels=d["basis_labels"],
    )


@router.post("/circuit/run")
async def run(payload: CircuitV2In) -> dict[str, object]:
    """Execute a circuit with optional density mode and noise."""
    circuit = _circuit_from_in(payload)
    noise = _noise_from_in(payload)
    mode = payload.simulation.mode

    if mode == "statevector" and not noise.enabled:
        result = run_circuit(circuit)
        out = CircuitV2RunOut(
            num_qubits=result.num_qubits,
            execution_time_ms=result.execution_time_ms,
            simulation_mode=result.simulation_mode,
            final_state=StateOut.model_validate(result.final_state.to_dict()),
            steps=[s.to_dict() for s in result.steps],
        )
        return envelope(out.model_dump())

    result = run_circuit(circuit, mode="density", noise=noise)
    assert isinstance(result, DensityCircuitResult)
    d = result.to_dict()
    out = CircuitV2RunOut(
        num_qubits=result.num_qubits,
        execution_time_ms=result.execution_time_ms,
        simulation_mode=result.simulation_mode,
        mixed_state=result.mixed_state,
        noise_enabled=result.noise_enabled,
        noise_channel=result.noise_channel,
        final_state=StateOut.model_validate(d["final_state"]),
        final_density=_density_out(result.final_density),
        purity=result.final_density.purity(),
        steps=[s.to_dict() for s in result.steps],
    )
    return envelope(out.model_dump())


@router.post("/metrics/fidelity")
async def metrics_fidelity(payload: FidelityRequest) -> dict[str, object]:
    rho = _density_from_request(payload)
    if payload.amplitudes is not None and payload.density_real is None:
        sv = _state_from_amplitudes(payload.amplitudes, payload.num_qubits)
        fid, target = target_state_fidelity(sv, payload.target)
    else:
        fid, target = target_state_fidelity(rho, payload.target)
    out = FidelityOut(
        fidelity=fid,
        target_state=target,
        interpretation=interpret_fidelity(fid),
    )
    return envelope(out.model_dump())


@router.post("/metrics/entropy")
async def metrics_entropy(payload: EntropyRequest) -> dict[str, object]:
    rho = _density_from_request(payload)
    s = entanglement_entropy(rho, payload.subsystem)
    out = EntropyOut(
        entropy=s,
        interpretation=interpret_entropy(s, len(payload.subsystem)),
    )
    return envelope(out.model_dump())


@router.post("/metrics/purity")
async def metrics_purity(payload: PurityRequest) -> dict[str, object]:
    rho = _density_from_request(payload)
    p = rho.purity()
    interpretation = "Pure state." if p > 0.999 else "Mixed due to noise or decoherence."
    out = PurityOut(purity=p, interpretation=interpretation)
    return envelope(out.model_dump())
