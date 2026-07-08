"""Entanglement entropy via subsystem partial trace."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quantumlab.density import DensityMatrix


def entanglement_entropy(
    rho: DensityMatrix,
    subsystem_wires: list[int],
) -> float:
    """Compute von Neumann entropy S(rho_A) of a subsystem in bits."""
    reduced = rho.partial_trace(subsystem_wires)
    return reduced.von_neumann_entropy()


def interpret_entropy(value: float, num_subsystem_qubits: int) -> str:
    """Return an educational interpretation for subsystem entropy."""
    max_entropy = float(num_subsystem_qubits)
    if value < 1e-6:
        return "No entanglement (pure subsystem)."
    if num_subsystem_qubits == 1 and value > 0.99:
        return "Maximally entangled pair."
    if value >= max_entropy - 1e-6:
        return f"Maximally entangled ({num_subsystem_qubits}-qubit subsystem)."
    if value > 0.5 * max_entropy:
        return "Strong entanglement detected."
    return "Some entanglement present."
