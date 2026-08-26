"""Pydantic v2 models for QuantumLab API v2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models import ComplexAmplitude, GatePlacementIn, StateOut


class NoiseConfigIn(BaseModel):
    enabled: bool = False
    channel: Literal[
        "amplitude_damping",
        "phase_damping",
        "depolarizing",
        "bit_flip",
        "phase_flip",
        "t1_t2",
    ] = "depolarizing"
    probability: float = Field(default=0.01, ge=0.0, le=1.0)
    t1_us: float = Field(default=50.0, gt=0.0)
    t2_us: float = Field(default=25.0, gt=0.0)
    gate_time_ns: float = Field(default=50.0, ge=0.0)
    target_qubits: list[int] | None = None


class SimulationConfigIn(BaseModel):
    mode: Literal["statevector", "density"] = "statevector"
    noise: NoiseConfigIn = Field(default_factory=NoiseConfigIn)


class CircuitV2In(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    initial_basis_state: str | None = None
    gates: list[GatePlacementIn] = Field(default_factory=list)
    simulation: SimulationConfigIn = Field(default_factory=SimulationConfigIn)


class ResearchVerifyRequest(CircuitV2In):
    final_state: list[ComplexAmplitude] | None = None
    density_real: list[list[float]] | None = None
    density_imag: list[list[float]] | None = None
    measurement_probabilities: list[float] = Field(default_factory=list)


class DensityMatrixOut(BaseModel):
    num_qubits: int
    dim: int
    real: list[list[float]]
    imag: list[list[float]]
    probabilities: list[float]
    purity: float
    basis_labels: list[str]


class CircuitV2RunOut(BaseModel):
    num_qubits: int
    execution_time_ms: float
    simulation_mode: str
    mixed_state: bool = False
    noise_enabled: bool = False
    noise_channel: str | None = None
    final_state: StateOut
    final_density: DensityMatrixOut | None = None
    purity: float | None = None
    steps: list[dict[str, object]]


class FidelityRequest(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    amplitudes: list[ComplexAmplitude] | None = None
    density_real: list[list[float]] | None = None
    density_imag: list[list[float]] | None = None
    target: Literal["bell", "ghz", "zero"] = "bell"


class FidelityOut(BaseModel):
    fidelity: float
    target_state: str
    interpretation: str


class EntropyRequest(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    subsystem: list[int] = Field(..., min_length=1)
    amplitudes: list[ComplexAmplitude] | None = None
    density_real: list[list[float]] | None = None
    density_imag: list[list[float]] | None = None


class EntropyOut(BaseModel):
    entropy: float
    interpretation: str


class PurityRequest(BaseModel):
    num_qubits: int = Field(..., ge=1, le=8)
    amplitudes: list[ComplexAmplitude] | None = None
    density_real: list[list[float]] | None = None
    density_imag: list[list[float]] | None = None


class PurityOut(BaseModel):
    purity: float
    interpretation: str
