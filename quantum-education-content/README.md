# quantum-education-content

**Missions, hints, and curricula for QuantumLab.**

This repository holds all the *content* of QuantumLab — the missions
the user plays through, the textual hints, and the reference solution
circuits.

It is intentionally separated from the engine and the desktop app so
that educators, curriculum designers, and quantum educators can fork
it independently without touching the code.

## Structure

```
missions/             one JSON file per mission
hints/                short plain-text hints, referenced by id
solutions/            JSON circuit definitions, used to grade
```

## Mission schema (v3 draft)

```json
{
  "id": "bell_state_01",
  "title": "Entangle Two Qubits",
  "description": "Create the Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2",
  "difficulty": "beginner",
  "estimated_minutes": 10,
  "initial_circuit": { "numQubits": 2, "gates": [] },
  "success_condition": {
    "type": "fidelity",
    "target_state": [0.707, 0, 0, 0.707],
    "threshold": 0.98
  },
  "hints": ["hint_bell_01", "hint_bell_02"],
  "solution_circuit": "solution_bell_state.json"
}
```

Mission IDs must be globally unique, lowercase, and snake_case.

## Launch missions (v3)

| ID                  | Title                          | Concept                  | Difficulty   |
| ------------------- | ------------------------------ | ------------------------ | ------------ |
| `bell_state_01`     | Create a Bell State            | Entanglement, CNOT       | beginner     |
| `teleport_01`       | Teleport a Qubit               | Quantum teleportation    | intermediate |
| `grover_2q`         | Grover's Algorithm (2 qubit)   | Amplitude amplification  | intermediate |
| `qft_4q`            | Quantum Fourier Transform      | Phase kickback           | advanced     |
| `cavity_coherence`  | 3D Cavity Advantage            | Decoherence, T1/T2       | advanced     |
| `threshold_01`      | Beat the Noise Threshold       | Error correction         | expert       |

## License

CC-BY-SA 4.0. See `LICENSE`.

The QuantumLab engine and desktop app are licensed under MIT in their
own repositories; only the educational content is share-alike to
guarantee curricula stay open.
