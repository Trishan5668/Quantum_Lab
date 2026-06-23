"""Typed exception hierarchy for QuantumLab.

Every failure path inside the simulator MUST raise a subclass of
``QuantumLabError``. Silent fallbacks are forbidden by project rules.
"""

from __future__ import annotations


class QuantumLabError(Exception):
    """Root of the QuantumLab exception hierarchy."""


class InvalidGateError(QuantumLabError):
    """Raised when a gate matrix is malformed (shape, dtype, unitarity)."""


class QubitIndexError(QuantumLabError):
    """Raised when a qubit target index is out of bounds or duplicated."""


class SimulationError(QuantumLabError):
    """Raised when a circuit cannot be executed for structural reasons."""


class NormalizationError(QuantumLabError):
    """Raised when a state vector or density matrix fails normalization."""
