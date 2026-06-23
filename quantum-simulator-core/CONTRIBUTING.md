# Contributing to quantum-simulator-core

Thanks for your interest. This package is the math heart of QuantumLab —
correctness is paramount. Read this before opening a PR.

## House rules

1. **No silent fallbacks.** Every failure path raises a typed exception
   from `quantumlab.exceptions`.
2. **No untyped Python.** Every function has full type annotations.
   `from __future__ import annotations` at the top of every file.
3. **No mocking quantum math.** Every gate matrix must be exact to
   `float64` precision. No approximations marketed as "good enough."
4. **Use `np.kron`** when building full-Hilbert-space operators. Don't
   iterate over basis states by hand.
5. **Commits are atomic and present-tense.** `Add T gate matrix`, not
   `stuff`.

## Adding a new gate

Template:

1. In `quantumlab/gates.py`, add a public function that returns a
   `complex128` NumPy array. Document its convention.
2. In `quantumlab/circuit.py`, register it in `_SINGLE_QUBIT_GATES` (or
   the appropriate dict) and add a `gate_type` literal.
3. In `tests/test_gates.py`, add unit tests for unitarity and any known
   identities (e.g. `S^2 = Z`, `T^4 = Z`).
4. In `tests/test_state.py`, add an end-to-end test exercising the gate
   on an `n >= 1` state vector.
5. Run:
   ```bash
   python -m pytest -q
   python -m mypy quantumlab
   ruff check quantumlab tests
   ```

All three must pass green before review.

## Code style

- Line length: 100
- Formatter: `ruff format` (compatible with `black`).
- Naming: keep textbook math identifiers (`H`, `RX`, `theta`) — these
  are explicitly whitelisted in the `ruff` config.

## Reporting bugs

Open a GitHub issue with:

- The failing input (state vector, gate, qubit indices).
- Expected vs. actual numerical output.
- Python + NumPy versions.

Include a minimal reproduction. The smaller, the faster we can fix it.
