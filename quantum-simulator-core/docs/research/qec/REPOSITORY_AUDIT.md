> **Superseded:** this document describes the pre-expansion slice and reports
> an old test count. The current audit is
> `research/qec/audit/REPOSITORY_AUDIT.md`, which records measured commands,
> classifications, the Phase 2 reproduction, the Phase 3 limitation, the
> rejected Phase 4 candidate, and blocked checks.

# QuantHub QEC repository audit

## Scope and baseline

The audit was performed against the repository layout and source currently in
the working tree. The core package is a Python 3.11+ NumPy/SciPy state-vector
simulator. It also contains a density-matrix implementation and single-qubit
Kraus channels.

Existing locations:

- `quantumlab/state.py` and `quantumlab/gates.py`: pure NumPy state vectors and
  the supported H, X, Y, Z, rotation, and CNOT gates.
- `quantumlab/density.py`: density-matrix evolution and metrics.
- `quantumlab/noise.py`: amplitude damping, phase damping, depolarizing,
  bit-flip, phase-flip, and T1/T2 channels.
- `quantumlab/circuit.py`: circuit placement and state/density execution.
- `tests/`: unit tests for gates, state evolution, density matrices, noise,
  entropy, fidelity, MPS, and validation.

The existing simulator has no measurement sampling API, stabilizer-code
representation, syndrome extraction, repeated rounds, classical decoder
interface, circuit-level preparation/measurement faults, correlated noise, or
logical-failure experiment artifact format. The M marker is documented as a
measurement marker whose sampling endpoint is still pending.

## Verified versus assumed

Verified by source inspection: supported gates and channel classes listed
above, big-endian state convention, strict typed package configuration, and
existing tests for trace preservation and channel limits. Not assumed:
surface-code support, fault tolerance, MWPM support, hardware realism, or
measurement semantics.

## Initial architecture

The first research increment is isolated under
`quantumlab/research/qec/`. It provides a validated YAML protocol, a
three-qubit repetition-code model, an explicit phenomenological X-noise
experiment, majority-vote decoding, Wilson intervals, JSONL trial evidence,
checksums, and environment metadata. It does not modify normal simulator
execution.

## Scientific gaps and impact

The protocol is intentionally bounded because the current backend cannot
faithfully execute a circuit-level surface-code experiment. Ideal syndrome
extraction means the result is not a fault-tolerance threshold result.
Missing preparation, gate, measurement, idle, leakage, and correlated-noise
models prevent claims about a real device. Missing MWPM and independent
differential validation prevent an established-decoder comparison in this
increment.

## Baseline tests

The existing test suite contains the core regression coverage described in the
package README. The exact command is `python -m pytest -q` from
`quantum-simulator-core`; new QEC tests should be run with the same command
after dependencies are installed. No baseline result is represented as
scientific evidence in this document.

## Next scientifically required increments

Add independent single-shot sampling and a separate brute-force reference,
then implement explicit syndrome circuits with preparation and measurement
noise. Only after those checks should a surface-code/MWPM backend or a
noise-aware held-out selection strategy be introduced.
