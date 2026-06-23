"""QuantumLab core: pure NumPy quantum circuit simulator."""

from __future__ import annotations

from quantumlab.circuit import (
    CircuitDefinition,
    CircuitResult,
    GatePlacement,
    StepResult,
    run_circuit,
    run_step,
)
from quantumlab.exceptions import (
    InvalidGateError,
    NormalizationError,
    QuantumLabError,
    QubitIndexError,
    SimulationError,
)
from quantumlab.gates import CNOT, RX, RY, RZ, GateMatrix, H, I, X, Y, Z
from quantumlab.state import StateVector

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "QuantumLabError",
    "InvalidGateError",
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
    "CircuitDefinition",
    "CircuitResult",
    "GatePlacement",
    "StepResult",
    "run_circuit",
    "run_step",
]
