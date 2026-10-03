"""QuantumLab core: pure NumPy quantum circuit simulator."""

from __future__ import annotations

from quantumlab.circuit import (
    CircuitDefinition,
    CircuitResult,
    DensityCircuitResult,
    DensityStepResult,
    MPSCircuitResult,
    GatePlacement,
    SimulationMode,
    StepResult,
    run_circuit,
    run_density_step,
    run_step,
)
from quantumlab.density import DensityMatrix
from quantumlab.entropy import entanglement_entropy, interpret_entropy
from quantumlab.exceptions import (
    InvalidDensityMatrixError,
    InvalidGateError,
    NormalizationError,
    QuantumLabError,
    QubitIndexError,
    SimulationError,
)
from quantumlab.fidelity import (
    fidelity,
    interpret_fidelity,
    target_state_fidelity,
)
from quantumlab.gates import CNOT, RX, RY, RZ, GateMatrix, H, I, X, Y, Z
from quantumlab.noise import (
    SUPERCONDUCTING_QUBIT_PRESET,
    AmplitudeDampingChannel,
    BitFlipChannel,
    DepolarizingChannel,
    NoiseConfig,
    PhaseDampingChannel,
    PhaseFlipChannel,
    QuantumChannel,
    T1T2NoiseModel,
    apply_noise,
    build_channel,
)
from quantumlab.state import StateVector
from quantumlab.tensor_networks import MPS, MPSConfig, TruncationEvent

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "QuantumLabError",
    "InvalidGateError",
    "InvalidDensityMatrixError",
    "QubitIndexError",
    "SimulationError",
    "NormalizationError",
    "GateMatrix",
    "H",
    "X",
    "Y",
    "Z",
    "RX",
    "RY",
    "RZ",
    "CNOT",
    "I",
    "StateVector",
    "MPS",
    "MPSConfig",
    "TruncationEvent",
    "DensityMatrix",
    "CircuitDefinition",
    "CircuitResult",
    "DensityCircuitResult",
    "DensityStepResult",
    "MPSCircuitResult",
    "GatePlacement",
    "StepResult",
    "SimulationMode",
    "NoiseConfig",
    "run_circuit",
    "run_step",
    "run_density_step",
    "QuantumChannel",
    "AmplitudeDampingChannel",
    "PhaseDampingChannel",
    "DepolarizingChannel",
    "BitFlipChannel",
    "PhaseFlipChannel",
    "T1T2NoiseModel",
    "SUPERCONDUCTING_QUBIT_PRESET",
    "apply_noise",
    "build_channel",
    "fidelity",
    "interpret_fidelity",
    "target_state_fidelity",
    "entanglement_entropy",
    "interpret_entropy",
]
