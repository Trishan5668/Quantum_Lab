# Entanglement Entropy

**Entanglement entropy** quantifies quantum correlation between subsystems using the von Neumann entropy of a reduced density matrix.

## Definition

For a bipartite state ρ_AB, trace out subsystem B:

ρ_A = Tr_B(ρ_AB)

Then:

S(ρ_A) = −Tr(ρ_A log₂ ρ_A)   (bits)

## Examples

| State              | S(ρ_A) for one qubit |
|--------------------|----------------------|
| Product |00⟩           | 0 (no entanglement)  |
| Bell (|00⟩+|11⟩)/√2 | 1 bit (maximal)      |

For a pure state on AB, S(ρ_A) = S(ρ_B).

## In QuantumLab

After running a 2+ qubit circuit in density mode, the **Metrics** panel shows entropy for subsystem q[0]. A Bell pair yields S ≈ 1 bit with interpretation "Maximally entangled pair."

Noise reduces entanglement: a noisy Bell state has S < 1 and purity < 1.

See Nielsen & Chuang for partial trace and entanglement measures.
