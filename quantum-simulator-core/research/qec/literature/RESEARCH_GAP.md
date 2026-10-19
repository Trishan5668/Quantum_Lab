# Research gap and positioning

**Status:** pre-declared before Phase 3/4 confirmatory runs.  
**Novelty claim:** none. This document exists to prevent overclaiming.

## The practical gap in this repository

The QEC engine can execute two mutually exclusive things:

1. small stabilizer codes with explicitly declared Pauli/phenomenological
   noise, or
2. Stim circuit-level surface-code circuits decoded by PyMatching from the
   **same circuit's** detector error model.

It has no bridge between a device/simulation whose true noise differs from
the nominal model used to build the decoder. In particular, it cannot answer:

> If the measurement error rate is much larger than the gate error rate, but
> the decoder assumes both are 1%, how much logical performance is lost, and
> can a model calibrated from observed detector statistics recover part of it
> without degrading the matched case?

This is a narrow engineering gap, not a gap in the literature. Noise-aware and
adaptive decoding are active, crowded areas (see below). The contribution
here is a **reproducible measurement and a gated candidate test inside this
codebase**, with negative results preserved.

## What the literature already establishes

| Work | What it establishes | Relation to this study |
| --- | --- | --- |
| Decoding-graph reweighting (DGR) line, `arXiv:2311.16214` | Reweighting under drift and correlations; abstract claims 3.6× average and >5000× worst-case logical-error reduction | Drift and correlated noise are **not modeled** here; this is not a reproduction |
| “Adaptive Estimation of Drifting Noise in QEC,” `arXiv:2511.09491`, PRX Quantum DOI `10.1103/z1hc-nqw5` | Estimates a time-dependent detector error model from syndrome data; estimated DEM beats static DEM | Stronger and broader than this study; no novelty claim possible |
| “Improving error suppression with noise-aware decoding,” `arXiv:2502.21044` | ACES calibration of a correlated-matching decoder | Demonstrates calibration is already effective; this study tests a much simpler global two-parameter fit |
| “Optimal adaptation of surface-code decoders to local noise,” `arXiv:2403.08706`, PRX DOI `10.1103/r2dc-qcrx` | Only a few critical noise parameters need adaptation | Motivates a two-parameter fit, but does not establish that this particular fit works here |
| AlphaQubit neural decoder, *Nature* (2024), DOI `10.1038/s41586-024-08148-8` | Learned decoding can outperform baselines on Sycamore data | Out of scope; no neural decoder is implemented |
| `arXiv:2406.02700` | Prior calibration improved decoding by 16% (repetition) and 3.3% (surface) on Sycamore data | Hardware-specific; not directly comparable |
| `arXiv:2609.29018` | Decoder-model compatibility as a postselection signal under drift | Drift is out of scope |

## The precise contribution attempted

1. **A controlled mismatch measurement.** Hold the physical circuit fixed,
   vary only `(p_gate, p_meas)`, and compare a static nominal DEM against the
   oracle DEM on paired shots. This isolates decoder-model mismatch from
   sampler or circuit differences.
2. **A calibrated global candidate.** Fit two global parameters from observed
   detector-cohort rates, with no access to true labels, and evaluate on
   held-out seeds with pre-declared gates.
3. **A preserved negative/positive record.** If the candidate fails, the
   failure and the gate results remain in the repository.

## What would count as evidence

- Paired McNemar tests and paired bootstrap intervals on identical shots.
- Held-out seeds distinct from development seeds.
- Pre-declared profiles, shots, thresholds, and gates.
- Oracle-model results reported alongside nominal and candidate results.
- Honest labeling of Stim/PyMatching delegation.

## What would not count

- A single seed or a post-hoc profile.
- A relative improvement computed against a different shot set.
- A candidate tuned on held-out data.
- Claiming “AI discovery” without an AI-generated, externally recorded
  candidate and without passing the same gates.
- Claiming novelty over DGR/ACES/adaptive-DEM work.

## Feasibility and risks

| Risk | Mitigation |
| --- | --- |
| Global two-parameter fit is not identifiable from detector rates | Report ambiguity; gate fails rather than promoting |
| Calibration data are too small | Pre-declare 5,000 shots/candidate; report uncertainty and score gap |
| Candidate overfits one distance | Require replication at d=3 and d=5 |
| Oracle gain is tiny, so relative excess is noisy | Report absolute differences and intervals; mark INCONCLUSIVE |
| The study duplicates known results | Positioning explicitly disclaims novelty; value is local reproducibility and negative-result preservation |

## Decision

Proceed only with the pre-declared profiles and gates. Do not add profiles or
lower gates after seeing results. If the candidate fails, publish the failure
and do not promote it to any default path.
