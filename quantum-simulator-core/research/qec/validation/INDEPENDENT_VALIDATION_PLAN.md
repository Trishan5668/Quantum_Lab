# Independent validation plan

**Pre-declared:** 2026-10-19, before the validation run recorded in
`independent_validation.json`.

## What “independent” means here

| Level | Meaning | Available? |
| --- | --- | --- |
| L1 — analytic | Closed-form identities or exhaustive enumeration independent of sampling | Yes |
| L2 — independent implementation | A second simulator/decoder codebase (Stim + PyMatching) | Yes, installed |
| L3 — external replication | A different group, hardware, or independently written analysis | **BLOCKED** (no external party) |

Passing L1/L2 does **not** constitute external replication. No reviewer,
hardware result, or third-party reproduction is claimed.

## Pre-declared checks and pass criteria

| ID | Check | Pass criterion | Independence |
| --- | --- | --- | --- |
| V1 | Pauli matrix/product consistency | For random Paulis on ≤5 qubits, `P1.matrix() @ P2.matrix()` equals `(P1*P2).matrix()` up to 1e-10 | L1 (matrix algebra) |
| V2 | Code parameters | Repetition d3/d5 full/X distances are (1,3)/(1,5); Steane and five-qubit are (3,3); all validated codes pass algebraic checks | L1 (exhaustive) |
| V3 | Exhaustive decoder oracle | For every syndrome of the d=5 repetition code under bit flips, the exact decoder returns a correction with that syndrome; no missing syndrome | L1 (enumeration) |
| V4 | Exact vs MWPM logical equivalence | For every d=5 repetition syndrome, exact and MWPM corrections differ only by a stabilizer element | L2 (PyMatching) |
| V5 | Analytic repetition d=3 | Exact enumeration of the bit-flip failure probability equals `3p²(1-p)+p³` within 1e-12 at p=0.1 | L1 |
| V6 | Stim vs native repetition | At d=3/5/7, p=0.1, 50,000 shots, the Newcombe 95% interval for native minus Stim logical failure contains zero | L2 (Stim sampling + MWPM vs native exact decoder) |
| V7 | Interval identities | Wilson(84/10000), Wilson(0/100), Clopper–Pearson(0/100), and zero-failure bound match their closed forms to 1e-12 | L1 |
| V8 | Artifact reproducibility | Two runs of a 200-shot protocol with the same seed produce byte-identical `records.jsonl` | L1 (determinism) |

## Declared tolerances

- V1/V2/V3/V5/V7: numerical tolerance 1e-10 or exact integer equality, as
  stated.
- V4: exact group-membership equality, no tolerance.
- V6: 95% Newcombe interval must contain zero; no post-hoc widening.
- V8: SHA-256 equality.

## Blocked checks

| Check | Status | Reason |
| --- | --- | --- |
| V9 external replication | BLOCKED | No external group or reviewer |
| V10 hardware logical error rate | BLOCKED | No hardware/calibration data |
| V11 leakage/coherent-noise validation | BLOCKED | Not modeled |
| V12 surface-code distance >7 exact validation | BLOCKED | Cost; Stim-only path not natively validated |

Blocked checks are reported as `BLOCKED`, never as passing.

## Interpretation rules

- A failed check is reported as `FAIL`; the overall status is not “validated”.
- A blocked check is reported as `BLOCKED`; it is not silently omitted.
- V6 compares two different codebases but shares the detector-error-model
  abstraction and the depolarizing noise definition. It is not a hardware
  validation.
- Passing V1–V8 supports **implementation correctness**, not novelty,
  superiority, or production readiness.
- Any later change to the decoders or code algebra requires re-running this
  suite and preserving the previous report.
