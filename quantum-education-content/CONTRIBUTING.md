# Contributing to quantum-education-content

Curricula live here. Be ruthless about pedagogical clarity.

## Writing a new mission

1. Choose a globally unique `id` (snake_case, e.g. `phase_kickback_01`).
2. Create `missions/<id>.json` matching the schema below.
3. Add the hints referenced in the mission to `hints/<hint_id>.txt`.
   One hint per file. Plain UTF-8 text, no markdown.
4. Add the reference solution to `solutions/<solution_id>.json` as a
   QuantumLab circuit definition.
5. Verify the mission loads in the desktop app and the solution
   actually meets the success condition (run it once, confirm
   fidelity ≥ threshold).
6. Open a pull request titled `Add mission: <title>`.

## Mission schema

```json
{
  "id": "<unique snake_case id>",
  "title": "<<= 50 chars, sentence case>",
  "description": "<one short paragraph, neutral tone>",
  "difficulty": "beginner" | "intermediate" | "advanced" | "expert",
  "estimated_minutes": 1..120,
  "initial_circuit": { "numQubits": 1..8, "gates": [...] },
  "success_condition": {
    "type": "fidelity" | "exact_state" | "probability",
    "target_state": [<real>, ...]   // for fidelity / exact_state
    "target_probabilities": [...],  // for probability
    "threshold": 0.0..1.0
  },
  "hints": ["<hint_id>", ...],
  "solution_circuit": "<solution_id>.json"
}
```

## Style notes

- Educational tone: a curious 15-year-old reads every mission. Define
  every technical term inline the first time it appears.
- Don't spoil the solution in hints. Hints reveal one fact each,
  ordered from gentle to specific.
- Reference real-world experiments where possible (e.g.
  `cavity_coherence` cites Paik et al. 2011).
