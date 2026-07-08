# Density Matrices

A **density matrix** ρ describes a quantum state that may be **mixed** (a statistical ensemble) rather than a single pure wavefunction.

## Pure states

For a pure state |ψ⟩, the density operator is the outer product:

ρ = |ψ⟩⟨ψ|

The statevector simulator in QuantumLab V1 already computes this for visualization. In V2, ρ can evolve under noise channels.

## Mixed states

When we do not know the exact phase or when decoherence occurs, ρ is a weighted sum of projectors:

ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ|,   Σᵢ pᵢ = 1

## Key properties

- **Trace:** Tr(ρ) = 1 (total probability is conserved).
- **Purity:** Tr(ρ²) = 1 for pure states; lower values indicate mixing.
- **Entropy:** S(ρ) = −Tr(ρ log₂ ρ) measures uncertainty; S = 0 for pure states.

## Why use density matrices?

Noise and decoherence are **non-unitary** processes. They cannot be modeled by multiplying a statevector by a single unitary matrix. Kraus operators acting on ρ capture these effects correctly.

See also: [noise-models.md](./noise-models.md), Nielsen & Chuang Ch. 8.
