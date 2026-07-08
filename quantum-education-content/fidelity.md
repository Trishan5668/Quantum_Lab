# Fidelity

**Fidelity** measures how close two quantum states are.

## Pure states

For |ψ⟩ and |φ⟩:

F = |⟨ψ|φ⟩|²

- F = 1: identical up to global phase
- F = 0: orthogonal states

## Mixed states (Uhlmann fidelity)

For density matrices ρ and σ:

F(ρ, σ) = (Tr √(√ρ σ √ρ))²

When one state is pure, this reduces to the overlap formula.

## Interpretation in QuantumLab

| Fidelity | Meaning        |
|----------|----------------|
| ≥ 99%    | Excellent      |
| 90–99%   | Good           |
| < 90%    | Needs improvement |

## Example

A Bell-state circuit (H + CNOT) should achieve F = 1 against the |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 target. Adding depolarizing noise lowers F, showing how decoherence degrades state preparation.

Select a **Fidelity target** in the toolbar and run in density or noise mode to see the metric card.
