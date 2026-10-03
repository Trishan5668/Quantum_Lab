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


class InvalidDensityMatrixError(QuantumLabError):
    """Raised when a density matrix fails structural or physical validation."""


class TensorNetworkError(QuantumLabError):
    """Base error for tensor-network execution."""


class MPSShapeError(TensorNetworkError):
    """Raised when MPS tensors do not have compatible virtual dimensions."""


class MPSCanonicalizationError(TensorNetworkError):
    """Raised when a requested canonical form cannot be obtained safely."""


class MPSContractionError(TensorNetworkError):
    """Raised for an invalid or unsafe tensor contraction."""


class MPSNumericalError(TensorNetworkError):
    """Raised for non-finite tensor-network numerical results."""


class MPSMemoryError(TensorNetworkError):
    """Raised before an MPS operation would exceed its memory budget."""


class UnsupportedTensorNetworkOperation(TensorNetworkError):
    """Raised when an operation needs a tensor-network representation not implemented."""
