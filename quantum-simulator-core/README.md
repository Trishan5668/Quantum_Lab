# quantum-simulator-core

**The math engine. NumPy-based quantum circuit simulator.**

A pure-Python, dependency-light state-vector simulator with mathematically
exact gate matrices and a strict typed API. No Qiskit, no approximations,
no silent fallbacks — every failure raises a named exception.

This package is the foundation of [QuantumLab](https://github.com/quantumlab),
an open-source educational quantum simulator. It can also be used standalone
for research, teaching, or as a reference implementation.

## Why another simulator?

- **Pedagogical clarity.** Every gate is exactly the matrix in a textbook.
  Nothing is hidden behind compiled C++ kernels.
- **Type-safe.** Strict `mypy` clean, with `from __future__ import annotations`
  on every file.
- **Tested.** 58+ tests cover gate unitarity, anticommutation relations,
  entanglement (Bell, GHZ), Bloch sphere mappings, and adversarial inputs.
- **Convention-explicit.** Big-endian basis order: `q[0]` is the most
  significant bit. Documented at the module level so there are no surprises.

## Installation

```bash
python -m pip install -e ".[dev]"
```

Requires Python 3.11+, NumPy, SciPy.

## Quickstart

```python
from quantumlab import StateVector, H, CNOT

# Bell state: (|00> + |11>) / sqrt(2)
state = StateVector.zero(2).apply_gate(H(), [0]).apply_gate(CNOT(), [0, 1])

print(state.probabilities())
# -> [0.5, 0. , 0. , 0.5]

print(state.bloch_angles(0))
# -> (1.5707..., 0.0)   # maximally mixed reduced state -> r = 0; defaults to (0,0)
#   In fact, each qubit of the Bell state has a maximally mixed reduced
#   density matrix, so the Bloch vector has zero length.
```

### Running a full circuit

```python
from quantumlab import CircuitDefinition, GatePlacement, run_circuit

circuit = CircuitDefinition(
    num_qubits=2,
    gates=[
        GatePlacement(id="g0", gate_type="H", qubit_targets=[0], time_step=0),
        GatePlacement(id="g1", gate_type="CNOT", qubit_targets=[0, 1], time_step=1),
    ],
)
result = run_circuit(circuit)
print(result.execution_time_ms, "ms")
print(result.final_state.probabilities())
```

## Supported gates (v1)

| Symbol | Class       | Notes                       |
| ------ | ----------- | --------------------------- |
| `H`    | Hadamard    | Single qubit                |
| `X`    | Pauli-X     | Single qubit                |
| `Y`    | Pauli-Y     | Single qubit                |
| `Z`    | Pauli-Z     | Single qubit                |
| `RX`   | Rotation X  | Single qubit, takes `theta` |
| `RY`   | Rotation Y  | Single qubit, takes `theta` |
| `RZ`   | Rotation Z  | Single qubit, takes `theta` |
| `CNOT` | Controlled-NOT | Two qubits `[control, target]` |
| `M`    | Measurement | No-op marker (sampling endpoint TBD) |

## Conventions

- **Big-endian basis order**: with `n = 2`, index 3 = `|11>` means
  `q[0] = 1, q[1] = 1`.
- `CNOT()` matrix layout: rows/columns ordered `|00>, |01>, |10>, |11>`.
- `apply_gate(CNOT(), [c, t])` treats `c` as control, `t` as target.
- Non-adjacent two-qubit gates are routed onto wires `(0, 1)` via SWAP
  operators built with `np.kron`.

## Exceptions

All failures are subclasses of `QuantumLabError`:

- `InvalidGateError` — malformed gate matrix
- `QubitIndexError` — bad qubit target
- `SimulationError` — structural circuit failure
- `NormalizationError` — state vector failed `<psi|psi> = 1`

## Testing

```bash
python -m pytest -q
python -m mypy quantumlab
```

## License

MIT
