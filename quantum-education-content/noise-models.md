# Noise Models

Real qubits decohere. QuantumLab V2 simulates common **CPTP channels** using Kraus operators.

## Amplitude damping (T1)

Models energy relaxation: |1⟩ decays toward |0⟩. Parameter **p** is the decay probability per application.

Physical meaning: **T1** is the energy relaxation time. After gate time Δt, p ≈ 1 − exp(−Δt/T1).

## Phase damping (T2)

Models loss of phase coherence without changing populations. Off-diagonal elements of ρ decay.

**T2** (dephasing time) satisfies T2 ≤ 2T1.

## Depolarizing channel

With probability p, the qubit undergoes a random Pauli (X, Y, or Z) error; otherwise it is unchanged. At p = 1 the state becomes maximally mixed I/2.

## Bit flip and phase flip

- **Bit flip:** X error with probability p.
- **Phase flip:** Z error with probability p.

## Superconducting qubit context

Paik et al. (2011) reported T1 up to ~60 μs and T2 ~ 25 μs for transmon qubits. QuantumLab's T1/T2 preset uses similar educational defaults (T1 = 50 μs, T2 = 25 μs).

## In the UI

Enable **Noise Settings** in the circuit builder, choose a channel, and re-run the circuit. Mixed states show reduced purity and changed fidelity to target states.
