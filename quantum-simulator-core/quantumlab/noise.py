"""Quantum noise channels via Kraus operators (CPTP maps)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np

from quantumlab._operators import embed_kraus
from quantumlab.density import DensityMatrix
from quantumlab.exceptions import SimulationError
from quantumlab.gates import GateMatrix, I, X, Y, Z

NoiseChannelType = Literal[
    "amplitude_damping",
    "phase_damping",
    "depolarizing",
    "bit_flip",
    "phase_flip",
    "t1_t2",
]


class QuantumChannel(ABC):
    """A single-qubit CPTP channel applied to selected wires."""

    @abstractmethod
    def kraus_operators(self) -> list[GateMatrix]:
        """Return the Kraus operators K_i with sum K_i^dagger K_i = I."""

    def apply(self, rho: DensityMatrix, qubit: int) -> DensityMatrix:
        """Apply rho -> sum_i K_i rho K_i^dagger on ``qubit``."""
        if not (0 <= qubit < rho.num_qubits):
            raise SimulationError(
                f"noise qubit {qubit} out of range for {rho.num_qubits} qubits"
            )
        new_rho = np.zeros_like(rho.matrix)
        for k in self.kraus_operators():
            op = embed_kraus(k, qubit, rho.num_qubits)
            new_rho += op @ rho.matrix @ op.conj().T
        return DensityMatrix.from_matrix(new_rho, rho.num_qubits)


@dataclass(frozen=True)
class AmplitudeDampingChannel(QuantumChannel):
    """Energy relaxation (T1-like): |1> decays toward |0>."""

    p: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.p <= 1.0):
            raise SimulationError(
                f"amplitude damping p must be in [0, 1], got {self.p}"
            )

    def kraus_operators(self) -> list[GateMatrix]:
        p = self.p
        k0 = np.array(
            [[1.0, 0.0], [0.0, np.sqrt(1.0 - p)]],
            dtype=np.complex128,
        )
        k1 = np.array(
            [[0.0, np.sqrt(p)], [0.0, 0.0]],
            dtype=np.complex128,
        )
        return [k0, k1]


@dataclass(frozen=True)
class PhaseDampingChannel(QuantumChannel):
    """Pure dephasing (T2-like): coherence loss without energy change."""

    gamma: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.gamma <= 1.0):
            raise SimulationError(
                f"phase damping gamma must be in [0, 1], got {self.gamma}"
            )

    def kraus_operators(self) -> list[GateMatrix]:
        g = self.gamma
        k0 = np.diag([1.0, np.sqrt(1.0 - g)]).astype(np.complex128)
        k1 = np.diag([0.0, np.sqrt(g)]).astype(np.complex128)
        return [k0, k1]


@dataclass(frozen=True)
class DepolarizingChannel(QuantumChannel):
    """Symmetric Pauli noise mixing toward I/2."""

    p: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.p <= 1.0):
            raise SimulationError(
                f"depolarizing p must be in [0, 1], got {self.p}"
            )

    def kraus_operators(self) -> list[GateMatrix]:
        p = self.p
        scale = np.sqrt(p / 3.0)
        return [
            np.sqrt(1.0 - p) * I(),
            scale * X(),
            scale * Y(),
            scale * Z(),
        ]


@dataclass(frozen=True)
class BitFlipChannel(QuantumChannel):
    """Pauli-X error channel."""

    p: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.p <= 1.0):
            raise SimulationError(
                f"bit flip p must be in [0, 1], got {self.p}"
            )

    def kraus_operators(self) -> list[GateMatrix]:
        p = self.p
        return [np.sqrt(1.0 - p) * I(), np.sqrt(p) * X()]


@dataclass(frozen=True)
class PhaseFlipChannel(QuantumChannel):
    """Pauli-Z error channel."""

    p: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.p <= 1.0):
            raise SimulationError(
                f"phase flip p must be in [0, 1], got {self.p}"
            )

    def kraus_operators(self) -> list[GateMatrix]:
        p = self.p
        return [np.sqrt(1.0 - p) * I(), np.sqrt(p) * Z()]


@dataclass(frozen=True)
class T1T2NoiseModel(QuantumChannel):
    """Combine amplitude and phase damping from T1, T2, and gate duration."""

    t1_us: float
    t2_us: float
    gate_time_ns: float

    def __post_init__(self) -> None:
        if self.t1_us <= 0 or self.t2_us <= 0:
            raise SimulationError("T1 and T2 must be positive")
        if self.gate_time_ns < 0:
            raise SimulationError("gate_time_ns must be non-negative")

    @property
    def p_amplitude(self) -> float:
        gate_time_us = self.gate_time_ns * 1e-3
        return 1.0 - math.exp(-gate_time_us / self.t1_us)

    @property
    def p_phase(self) -> float:
        gate_time_us = self.gate_time_ns * 1e-3
        return 1.0 - math.exp(-gate_time_us / self.t2_us)

    def kraus_operators(self) -> list[GateMatrix]:
        raise SimulationError(
            "T1T2NoiseModel must be applied via apply_t1_t2(), not Kraus list"
        )

    def apply(self, rho: DensityMatrix, qubit: int) -> DensityMatrix:
        amp = AmplitudeDampingChannel(self.p_amplitude)
        phase = PhaseDampingChannel(self.p_phase)
        return phase.apply(amp.apply(rho, qubit), qubit)


@dataclass(frozen=True)
class NoiseConfig:
    """Optional noise settings for circuit execution."""

    enabled: bool = False
    channel: NoiseChannelType = "depolarizing"
    probability: float = 0.01
    t1_us: float = 50.0
    t2_us: float = 25.0
    gate_time_ns: float = 50.0
    target_qubits: list[int] | None = None


def build_channel(config: NoiseConfig) -> QuantumChannel:
    """Materialize a noise channel from configuration."""
    if config.channel == "amplitude_damping":
        return AmplitudeDampingChannel(config.probability)
    if config.channel == "phase_damping":
        return PhaseDampingChannel(config.probability)
    if config.channel == "depolarizing":
        return DepolarizingChannel(config.probability)
    if config.channel == "bit_flip":
        return BitFlipChannel(config.probability)
    if config.channel == "phase_flip":
        return PhaseFlipChannel(config.probability)
    if config.channel == "t1_t2":
        return T1T2NoiseModel(
            t1_us=config.t1_us,
            t2_us=config.t2_us,
            gate_time_ns=config.gate_time_ns,
        )
    raise SimulationError(f"unknown noise channel: {config.channel!r}")


def apply_noise(
    rho: DensityMatrix,
    channel: QuantumChannel,
    wires: list[int] | None = None,
) -> DensityMatrix:
    """Apply ``channel`` to each qubit in ``wires`` (default: all qubits)."""
    targets = wires if wires is not None else list(range(rho.num_qubits))
    result = rho
    for q in targets:
        result = channel.apply(result, q)
    return result


# Paik et al. 2011 typical superconducting transmon values (microseconds).
SUPERCONDUCTING_QUBIT_PRESET = NoiseConfig(
    enabled=True,
    channel="t1_t2",
    t1_us=60.0,
    t2_us=25.0,
    gate_time_ns=50.0,
)
