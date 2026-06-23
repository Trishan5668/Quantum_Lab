"""Visualization helper endpoints (Bloch, density matrix)."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from quantumlab.state import StateVector

from app.models import (
    BlochOut,
    BlochQubitOut,
    ComplexAmplitude,
    DensityMatrixOut,
    envelope,
)


router = APIRouter(prefix="/api/v1/visualize", tags=["visualize"])


class _VizRequest(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    amplitudes: list[ComplexAmplitude]


def _state_from_request(payload: _VizRequest) -> StateVector:
    amps = np.array(
        [complex(a.real, a.imag) for a in payload.amplitudes],
        dtype=np.complex128,
    )
    return StateVector(amplitudes=amps, num_qubits=payload.num_qubits)


@router.post("/bloch")
async def bloch(payload: _VizRequest) -> dict[str, object]:
    state = _state_from_request(payload)
    qubits: list[BlochQubitOut] = []
    for q in range(state.num_qubits):
        theta, phi = state.bloch_angles(q)
        x, y, z = state.bloch_vector(q)
        qubits.append(
            BlochQubitOut(
                qubit=q,
                theta=theta,
                phi=phi,
                x=x,
                y=y,
                z=z,
                purity=state.purity(qubit=q),
            )
        )
    out = BlochOut(num_qubits=state.num_qubits, qubits=qubits)
    return envelope(out.model_dump())


@router.post("/density")
async def density(payload: _VizRequest) -> dict[str, object]:
    state = _state_from_request(payload)
    rho = state.density_matrix()
    dim = rho.shape[0]
    labels = [state.basis_label(i) for i in range(dim)]
    out = DensityMatrixOut(
        num_qubits=state.num_qubits,
        dim=dim,
        real=[[float(x) for x in row] for row in rho.real],
        imag=[[float(x) for x in row] for row in rho.imag],
        basis_labels=labels,
    )
    return envelope(out.model_dump())
