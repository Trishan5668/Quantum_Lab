# Repository audit — QuantumLab QEC subsystem

**Audit date:** 2026-10-19  
**Audited revision:** `100f8a3` (`v3.3`) plus the working-tree changes described
below. The tree was dirty during the audit; that is itself recorded as a
finding and every run records `git.dirty`.  
**Scope:** `quantum-simulator-core` (package `quantumlab`), its QEC research
slice, tests, CI, and the FastAPI research route. Frontend and education
content were inspected only for QEC claims.

Status vocabulary: **VERIFIED** means the implementation exists, is exercised
by a test that would fail if the behavior were removed, and its limits are
stated. **PARTIALLY_IMPLEMENTED** means some paths are verified but the
capability is not complete. **NOT_IMPLEMENTED** means no implementation was
found. **UNVERIFIED** means code exists but no adequate test/record supports
the claim. **BLOCKED** means an external dependency, data set, or reviewer is
required. A symbol existing is never sufficient for VERIFIED.

## 1. Baseline and commands

| Check | Result | Evidence |
| --- | --- | --- |
| Test suite | 305 passed, 4 skipped (309 collected) | `python -m pytest -q` from `quantum-simulator-core` |
| Skips | qiskit optional extra (1); qubit-index edge cases (3) | pytest summary |
| Ruff | clean | `ruff check quantumlab tests` |
| Mypy strict | clean | `mypy quantumlab` |
| Python | 3.11.2 in the audit environment | `sys.version` |
| Optional research tools | Stim 1.16.0, PyMatching 2.4.0 installed | package metadata |
| Qiskit | not installed in the audit environment | import probe |
| CI | core+API and frontend jobs exist | `.github/workflows/ci.yml` |

The CI workflow does **not** install the optional research dependencies and
therefore did not previously exercise the Stim/PyMatching path, threshold
reproduction, or the artifact-integrity tests. This is fixed in the same
change set by a separate research job.

## 2. What exists and is verified

### 2.1 Core simulator

| Capability | Status | Limits and evidence |
| --- | --- | --- |
| State-vector simulation | VERIFIED | Big-endian convention; tests for gates, Bell/GHZ, probabilities |
| Density-matrix simulation | VERIFIED | Validates trace, Hermiticity, PSD; tests |
| Gate set | VERIFIED | Exact I, H, X, Y, Z, RX, RY, RZ, CNOT; **no** S, T, CZ, SWAP, Toffoli |
| Multi-target gates | PARTIALLY_IMPLEMENTED | kron embedding for at most 2 targets |
| MPS backend | PARTIALLY_IMPLEMENTED | truncation is approximate; `reduced_density_matrix` limited to ≤10 contiguous qubits |
| Kraus channels | VERIFIED | Amplitude/phase damping, depolarizing, bit/phase flip; CPTP tests |
| T1/T2 composite model | VERIFIED | Uses `1/T2 = 1/(2T1) + 1/Tphi`; coherence equals `0.5·exp(-t/T2)` to 1e-15 across four (T1,T2) pairs |
| Measurement sampling | NOT_IMPLEMENTED | `M` is an execution marker only; there is no collapse or classical-bit API |
| Mid-circuit measurement/reset | NOT_IMPLEMENTED | Not present |
| Leakage / coherent / correlated / drift noise | NOT_IMPLEMENTED | Explicitly rejected by `require_supported_noise`; never claimed |

### 2.2 QEC research layer

| Capability | Status | Limits and evidence |
| --- | --- | --- |
| Pauli algebra | VERIFIED | `pauli.py`; 15 tests, including Hypothesis properties for multiplication and anti-commutation |
| Stabilizer codes | VERIFIED | Repetition, Steane, five-qubit; exhaustive validation and distances; 27 tests |
| Code distance | VERIFIED (small codes) | Exhaustive normalizer enumeration limited to ≤10 qubits; repetition full distance is 1 |
| Encoders/projectors | VERIFIED (small codes) | Exact matrices; size guards |
| Noise models | PARTIALLY_IMPLEMENTED | Pauli, one-round phenomenological with classical measurement flips, Stim circuit-level; no native circuit-level executor |
| Exact decoder | VERIFIED | Minimum-weight and maximum-likelihood over all Paulis; enumeration cap; deterministic tie-break |
| Majority decoder | VERIFIED | Exact minimum-weight for the odd repetition code |
| MWPM adapter | VERIFIED | PyMatching on Stim DEMs and on a check matrix for k=1 Z-stabilizer codes |
| Detector decoder | VERIFIED | Batch shape/binary validation, DEM hash in metadata |
| Statistical inference | VERIFIED | Wilson, Clopper–Pearson, zero-failure upper bound, Newcombe difference, exact McNemar, bootstrap helpers; 11 tests |
| Versioned protocols | VERIFIED | Strict v2 schema; unknown keys rejected; legacy v1 preserved |
| Experiment engine | VERIFIED | Paired shots, two explicit backends, decoder-failure accounting, runtime abort |
| Artifacts | VERIFIED | Atomic rename, manifest, checksums, tamper detection, failed-run preservation; 10 tests |
| CLI | PARTIALLY_IMPLEMENTED | `audit/validate/run/analyze/compare/verify/package/reproduce` implemented; `reproduce` target execution is exercised by the Phase 2 suite |
| Independent validation | PARTIALLY_IMPLEMENTED | Analytic, exact-vs-MWPM, and Stim cross-checks; no external reviewer/replication |
| Published-result reproduction | VERIFIED WITHIN DECLARED MODEL | `REPRODUCED_WITHIN_DECLARED_MODEL`; see `results/reports/PHASE2_REPRODUCTION.md` |
| Static-DEM limitation study | VERIFIED (simulation) | Phase 3 confirms a +22.3% relative excess at measurement-heavy d=5; `results/reports/PHASE3_LIMITATION.md` |
| Calibrated candidate | REJECTED on held-out generalization | v1 was identifiability-only; v2 failed control non-degradation; see `results/reports/PHASE4_CANDIDATE.md` |
| Independent validation | PASS (L1/L2), L3 blocked | 8 checks in `validation/independent_validation.json` |

## 3. Defects found and dispositions

These are findings about the pre-existing slice, not hypothetical risks.

1. **The legacy “distance 3” label is misleading.** The three-qubit repetition
   code has full Pauli distance 1; only its X-error distance is 3. It cannot
   detect a single Z error. `StabilizerCode.distance(kind="full")` now reports
   1 and the UI/docs must not present it as a quantum distance-3 code.
   **Status: fixed in the new model; legacy protocol text retained for
   historical comparison and explicitly caveated.**
2. **Legacy logical-failure criterion was code-specific.** `sum(residual) >= 2`
   happens to match the repetition code's residual outcomes, but it is not the
   normalizer/logical-operator definition and would misclassify general codes.
   The new engine classifies residuals by stabilizer membership and logical
   action. **Status: fixed for new runs; legacy path preserved unchanged.**
3. **The legacy baseline is not a paired or resource-matched control.**
   `baseline_failed = flips[0]` uses one physical qubit, a different sample
   space, and calls the absolute difference “paired”. The v2 schema forbids an
   `unencoded` decoder and requires a separate reference protocol; the v2
   comparison is a paired McNemar analysis on identical shots. **Status:
   legacy artifact fields retained for compatibility; reports must label them
   as unpaired.**
4. **Legacy protocol validation is incomplete.** It accepts `bool` where
   integers are required (`isinstance(True, int)`), does not reject unknown
   keys, hard-codes a single code/noise family, and ignores runtime limits
   because none exist. **Status: fixed in v2; v1 loader kept because an
   existing test and published workflow depend on it.**
5. **Legacy artifacts are not atomic and under-report provenance.** Files are
   created directly in the final directory; there is no dirty-tree flag,
   dependency version table, config hash over the protocol bytes, manifest, or
   post-run verification. Checksums cover six files but not themselves.
   **Status: fixed in `artifacts.py`; the legacy writer is retained only for
   the original protocol and is clearly marked legacy.**
6. **Zero-failure reporting is unsafe.** The legacy `analyze` prints
   `logical_failure_probability: 0.0` for 0/10000. The v2 reports always add a
   one-sided upper bound and a warning that zero events do not prove `p=0`.
   **Status: fixed for v2; legacy output retained but annotated by the new
   analysis helper.**
7. **The legacy noise model is one-round and phenomenological.** It has ideal
   syndrome extraction and independent X faults. Any text implying
   fault-tolerance or circuit-level behavior was unsupported.
   **Status: documented; circuit-level work is delegated to Stim.**
8. **The FastAPI research route is not a QEC endpoint.** It forwards a generic
   payload to an optional Wolfram verifier and returns 200 `UNAVAILABLE` when
   unset. No QEC claims are served by it.
   **Status: no change; noted to prevent overclaiming an API integration.**
9. **The stale audit/README claim “150 tests” / “58+ tests”.** The measured
   count after this work is 309 collected (305 passed, 4 skipped). The README
   and old audit under `docs/research/qec/` still contain stale numbers; the
   new audit supersedes them. **Status: stale text flagged.**

## 4. Scientific validity threats

| Threat | Current control | Residual risk |
| --- | --- | --- |
| Decoder bug that maps a syndrome to a wrong correction | Base-class contract re-checks the syndrome; exact oracle cross-check | A shared convention bug would affect both decoders |
| Bit-order / endianness | Big-endian convention documented and property-tested | Third-party adapter must convert explicitly |
| Sampling and decoding use the same error model | Declared as a model-consistency check, not independent validation | Real-device model mismatch is untested |
| Stim/PyMatching dependency drift | Versions and DEM/circuit hashes recorded | API changes can still alter results; no wheel pin |
| Multiple comparisons | All planned comparisons reported; no automatic correction | Exploratory p-values can still be over-read |
| Zero failures | One-sided upper bound | Legacy text still shows 0.0 point estimate |
| Correlated/drifting noise | Not modeled; adaptive claims prohibited | Any such claim would be unsupported |
| Source-tree changes during a run | Commit, dirty flag, diff hash recorded | Diff hash covers tracked files only; untracked data files are listed |

## 5. Reproduction and research readiness

- The repetition-code experiments are **code-capacity or one-round
  phenomenological**, not fault-tolerant memory experiments.
- The surface-code experiments are **Stim/PyMatching circuit-level
  simulations**, not native QuantumLab simulations and not hardware.
- The pre-declared Phase 2 target was reproduced within the declared
  Stim/PyMatching model class: `REPRODUCED_WITHIN_DECLARED_MODEL`, bracket
  `[0.006, 0.007]` inside the `[0.0055, 0.0085]` band.
- Phase 3 measured a +22.3% relative excess at measurement-heavy d=5 and a
  −1.0% (no penalty) at gate-heavy d=5. The calibrated v1 candidate recovered
  the exact generating profiles because they were grid points; that is
  identifiability only. The pre-declared interpolation test, with a grid
  excluding the true values, was **REJECTED** because it degraded the matched
  control by 3.25% relative on held-out seeds.
- No novelty claim exists. The literature review identifies adaptive and
  noise-aware decoding as crowded; the study is a limitation measurement with
  held-out gates.
- Independent validation is limited to analytic identities and a second
  implementation (Stim/PyMatching). That is **not** external replication.
  The validation report passes L1/L2 and marks L3 BLOCKED.

## 6. Blocked checks

| Check | Status | Reason |
| --- | --- | --- |
| Hardware logical-error measurement | BLOCKED | No hardware access or calibration data |
| External reviewer sign-off | BLOCKED | No reviewer engaged; cannot be invented |
| Qiskit cross-check | BLOCKED in this environment | Optional `qiskit` extra not installed; test skips honestly |
| Native circuit-level surface-code execution | BLOCKED by design | Not implemented; Stim is used and labeled |
| Leakage/coherent-noise claims | BLOCKED | Not modeled |
| Exact distance above 10 qubits | BLOCKED | Exhaustive enumeration limit |
| CI on GitHub runners | UNVERIFIED in this environment | Workflow updated but not executed on GitHub from the sandbox |
| External replication | BLOCKED | No external group or reviewer |

## 7. Required next actions

1. Run the pre-declared Phase 2 threshold reproduction with fresh seeds and
   record PASS/FAIL/INCONCLUSIVE without tuning.
2. Pre-declare and execute the Phase 3 limitation study on development seeds,
   then evaluate once on held-out seeds.
3. Add the research dependency job to CI and keep the default job fast.
4. Keep all negative and failed runs; never overwrite raw artifacts.
5. Update the stale README test count and QEC description only with measured
   numbers.
