"""Quantum state fidelity (pure and Uhlmann)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy.linalg import sqrtm

if TYPE_CHECKING:
    from quantumlab.density import DensityMatrix
    from quantumlab.state import StateVector

_FIDELITY_TOL: float = 1e-10


def _as_density(
    state: StateVector | DensityMatrix,
) -> np.ndarray:
    from quantumlab.density import DensityMatrix

    if isinstance(state, DensityMatrix):
        return state.matrix
    return state.density_matrix()


def fidelity(
    state1: StateVector | DensityMatrix,
    state2: StateVector | DensityMatrix,
) -> float:
    """Compute fidelity between two quantum states.

    For pure states returns |<psi|phi>|^2. For mixed states uses the
    Uhlmann fidelity F(rho, sigma) = (Tr sqrt(sqrt(rho) sigma sqrt(rho)))^2.
    """
    from quantumlab.density import DensityMatrix
    from quantumlab.state import StateVector

    if isinstance(state1, StateVector) and isinstance(state2, StateVector):
        overlap = np.vdot(state1.amplitudes, state2.amplitudes)
        return float(np.abs(overlap) ** 2)

    rho = _as_density(state1)
    sigma = _as_density(state2)

    sqrt_rho = sqrtm(rho)
    inner = sqrtm(sqrt_rho @ sigma @ sqrt_rho)
    fid = float(np.real(np.trace(inner)) ** 2)
    return max(0.0, min(1.0, fid))


def bell_state_vector(num_qubits: int = 2) -> np.ndarray:
    """Return |Phi+> = (|00> + |11>)/sqrt(2) amplitudes."""
    if num_qubits != 2:
        raise ValueError("Bell state requires exactly 2 qubits")
    amps = np.zeros(4, dtype=np.complex128)
    amps[0] = 1.0 / np.sqrt(2.0)
    amps[3] = 1.0 / np.sqrt(2.0)
    return amps


def ghz_state_vector(num_qubits: int) -> np.ndarray:
    """Return (|0...0> + |1...1>)/sqrt(2) amplitudes."""
    if num_qubits < 2:
        raise ValueError("GHZ state requires at least 2 qubits")
    dim = 1 << num_qubits
    amps = np.zeros(dim, dtype=np.complex128)
    amps[0] = 1.0 / np.sqrt(2.0)
    amps[dim - 1] = 1.0 / np.sqrt(2.0)
    return amps


def target_state_fidelity(
    state: StateVector | DensityMatrix,
    target: str,
) -> tuple[float, str]:
    """Compute fidelity against a named target state."""
    from quantumlab.density import DensityMatrix
    from quantumlab.state import StateVector

    n = state.num_qubits
    if target.lower() == "bell":
        if n != 2:
            raise ValueError("Bell target requires a 2-qubit state")
        target_sv = StateVector.from_amplitudes(bell_state_vector(2))
    elif target.lower() == "ghz":
        target_sv = StateVector.from_amplitudes(ghz_state_vector(n))
    elif target.lower() == "zero":
        target_sv = StateVector.zero(n)
    else:
        raise ValueError(f"unknown target state: {target!r}")

    fid = fidelity(state, target_sv)
    return fid, target.lower()


def interpret_fidelity(value: float) -> str:
    """Return an educational interpretation string for a fidelity value."""
    if value >= 0.99:
        return "Excellent quantum state preparation."
    if value >= 0.90:
        return "Good state preparation with minor deviation."
    return "Needs improvement — significant deviation from target."
