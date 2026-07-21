"""Pydantic v2 models for the FastAPI bridge.

Every API response is wrapped in :class:`ApiResponse` so the client can
distinguish ``data`` from a structured ``error``. Errors never sneak
through inside a 200 response body -- routes use proper HTTP status
codes via :class:`fastapi.HTTPException`.
"""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ComplexAmplitude(BaseModel):
    real: float
    imag: float


class GatePlacementIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    gate_type: Literal["H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT", "M"]
    qubit_targets: list[int] = Field(..., min_length=1, max_length=2)
    params: dict[str, float] = Field(default_factory=dict)
    time_step: int = Field(default=0, ge=0)
    stack_count: int = Field(default=1, ge=1)


class CircuitIn(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    initial_basis_state: str | None = None
    gates: list[GatePlacementIn] = Field(default_factory=list)


class StateOut(BaseModel):
    num_qubits: int
    amplitudes: list[ComplexAmplitude]
    probabilities: list[float]
    basis_labels: list[str]


class StepOut(BaseModel):
    gate_id: str
    gate_type: str
    qubit_targets: list[int]
    params: dict[str, float]
    time_step: int
    state_after: StateOut
    probabilities: list[float]


class CircuitRunOut(BaseModel):
    num_qubits: int
    execution_time_ms: float
    steps: list[StepOut]
    final_state: StateOut


class StepRequest(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    state_in: list[ComplexAmplitude]
    placement: GatePlacementIn


class BlochQubitOut(BaseModel):
    qubit: int
    theta: float
    phi: float
    x: float
    y: float
    z: float
    purity: float


class BlochOut(BaseModel):
    num_qubits: int
    qubits: list[BlochQubitOut]


class DensityMatrixOut(BaseModel):
    num_qubits: int
    dim: int
    real: list[list[float]]
    imag: list[list[float]]
    basis_labels: list[str]


class ExplainRequest(BaseModel):
    gate: str
    qubit: int | None = None
    qubits: list[int] | None = None
    state_before: list[ComplexAmplitude]
    state_after: list[ComplexAmplitude]
    num_qubits: int = Field(..., ge=1, le=8)
    context: str = "step"
    mode: Literal["normal", "deep", "hint"] = "normal"


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    core_version: str


class ApiError(BaseModel):
    code: str
    message: str
    trace: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Wrapper used by every JSON route.

    The contract is: when the HTTP status is 2xx, ``data`` is populated
    and ``error`` is ``None``. Errors are returned via non-2xx codes and
    use this same envelope with ``data == None``.
    """

    data: T | None = None
    error: ApiError | None = None


def envelope(data: Any) -> dict[str, Any]:
    return {"data": data, "error": None}
