# Phase 2 reproduction target (pre-declared)

**Pre-declared:** 2026-10-19, before the confirmatory run recorded in
`results/reproduction/`.  
**Target ID:** `surface_code_threshold_mwpm_v1`  
**Machine-readable declaration:** `reproduction/surface_code_threshold_v1.yaml`

## Result being reproduced

The circuit-level threshold of the rotated surface code under depolarizing
noise with minimum-weight perfect matching (MWPM) decoding is approximately
**0.6%–0.8% per operation**, depending on the exact circuit-level error model
and decoder. This is a well-established published result, not a claim of
novelty by this repository.

### References (metadata verified)

1. A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland,
   “Surface codes: Towards practical large-scale quantum computation,”
   *Physical Review A* **86**, 032324 (2012).
   DOI: [10.1103/PhysRevA.86.032324](https://doi.org/10.1103/PhysRevA.86.032324).
   The paper reports a threshold of **0.57% per step** for its explicitly
   defined circuit-level error sources.
2. O. Higgott, “PyMatching: A Python Package for Decoding Quantum Codes with
   Minimum-Weight Perfect Matching,” *ACM Transactions on Quantum Computing*
   **3**(3), Article 16 (2022).
   DOI: [10.1145/3505637](https://doi.org/10.1145/3505637).
   The PyMatching documentation’s toric/surface-code example reports a
   threshold of approximately **0.7%** for a circuit-level depolarizing model.
3. “Suppressing quantum errors by scaling a surface code logical qubit”
   (Google Quantum AI), *Nature* **614**, 676–681 (2023), is **not** used as a
   numerical target because it is a hardware result with device-specific
   noise. It is cited only as context for why decoder- and model-specific
   thresholds must be named.

The threshold is model- and decoder-dependent; the literature band above is
therefore a **band**, not a single number. No citation here is presented as
having been independently replicated by this repository.

## Exact model under test

- Circuit generator: `stim.Circuit.generated("surface_code:rotated_memory_z",
  distance=d, rounds=d, after_clifford_depolarization=p,
  before_measure_flip_probability=p, after_reset_flip_probability=p,
  before_round_data_depolarization=p)`.
- Memory basis: **Z** (the logical observable is the Z-memory frame).
- Decoder: PyMatching MWPM built from
  `circuit.detector_error_model(decompose_errors=True)`.
- Distances: 3, 5, 7; rounds equal to distance.
- Sampler: Stim compiled detector sampler, independent shots.

This is **Stim’s** standard circuit-level depolarizing model. It is related
to, but not identical with, the gate-by-gate error placement in Fowler et al.
(2012). The reproduction is therefore a reproduction of the published
**threshold scale/band for this model class**, and the report says so.

## Pre-declared design

| Item | Value |
| --- | --- |
| Coarse grid `p` | 0.004, 0.005, 0.006, 0.007, 0.008, 0.010 |
| Coarse shots per point | 20,000 |
| Refinement grid `p` | 0.006, 0.007 |
| Refinement shots per point | 200,000 |
| Distances at coarse grid | 3, 5, 7 |
| Distances at refinement | 3, 5 |
| Master seed | 20261020 |
| Seed derivation | `SeedSequence([master_seed, distance, round(p*1e6), stage])` |
| Threshold band (acceptance) | [0.0055, 0.0085] |
| Bracket rule | crossing of `LER(d=3) - LER(d=5)` between adjacent refinement points |
| Significance rule | Newcombe 95% interval for the difference must exclude zero at both refinement points, with opposite signs |
| Ordering below threshold | at p=0.004, `LER(3) > LER(5) > LER(7)` |
| Ordering above threshold | at p=0.010, `LER(3) < LER(5) < LER(7)` |

The band is derived from the published range (0.57%–0.82%) rounded outward to
the nearest 0.05 percentage point. It is **not** fitted to a pilot.

## Exploratory pilot disclosure

An earlier, non-predeclared pilot scan was run with a different seed family
and only 20,000 shots per point; it suggested a crossover near 0.006–0.007.
That pilot is **exploratory** and is not used as evidence. The confirmatory
run uses the fresh master seed above, a larger refinement sample, and the
acceptance rules fixed in this document. The pilot artifacts are not part of
the Phase 2 evidence package.

## Decision rule

- **REPRODUCED** — bracket exists, bracket lies inside [0.0055, 0.0085], both
  refinement differences exclude zero with opposite signs, and both ordering
  checks pass.
- **FAILED** — the bracket is decisive but lies outside the band, or an
  ordering check is decisively violated.
- **INCONCLUSIVE** — the data do not determine a bracket or the difference
  intervals include zero. Point estimates are still reported; no threshold
  claim is made.

All outcomes, including FAILED and INCONCLUSIVE, are retained. The analysis
must not be re-run with different tolerances after seeing the result.

## What is not claimed

- Not a hardware result.
- Not a reproduction of Fowler et al.’s exact circuit-level error placement.
- Not evidence that QuantumLab’s native simulator performs circuit-level QEC;
  Stim performs the sampling and PyMatching the decoding.
- Not a claim of novelty, superiority, or production readiness.
