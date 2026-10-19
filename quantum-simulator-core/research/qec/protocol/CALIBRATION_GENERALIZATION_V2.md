# Exploratory calibration generalization test (v2)

**Pre-declared:** 2026-10-19, after the v1 result was inspected.  
**Status:** exploratory, post-hoc motivated. It cannot promote a default
decoder and cannot be merged with the v1 confirmatory test as if it were
pre-specified.

## Why this test exists

The v1 candidate grid contained the exact generating profiles
(`(0.002, 0.020)`, `(0.020, 0.002)`, `(0.010, 0.010)`). The feature-based
selector recovered those values almost exactly. That demonstrates that the
detector-cohort features identify the two parameters; it does **not**
demonstrate calibration under model misspecification.

This follow-up removes the true values from the candidate grid and asks
whether interpolation still recovers a useful fraction of the oracle gain.

## Design

- Same physical profiles, distances, and paired design as v1.
- Candidate grid (no true value is a grid point):

```text
p_gate, p_meas in {0.001, 0.004, 0.007, 0.012, 0.018, 0.025}
```

- Development seed master: `4201`.
- Calibration shots: 5,000 per candidate cell and per true profile/d cell.
- Held-out seed master: `9201` (never used in v1).
- Held-out shots: 100,000 per cell.
- Selection score: same detector-cohort mean-absolute-error criterion.
- Candidate frozen before held-out sampling.

## Gates (same structure as v1)

| Gate | Criterion |
| --- | --- |
| G1 isolation | development seed 4201 only; held-out seed 9201 |
| G2 no control degradation | control d=5 candidate LER ≤ 1.02 × nominal, paired upper bound <2% |
| G3 recovery | measurement-heavy d=5 recovers ≥50% of the oracle gain |
| G4 replication | candidate < nominal at d=3 and d=5 |
| G5 evidence | McNemar p < 0.05 at measurement-heavy d=5 |

## Interpretation rules

- **PROMOTED (exploratory only)** if all gates pass. This means “worth a
  separately pre-registered validation”, never a default decoder.
- **REJECTED** if G2 or G3 fails.
- **INCONCLUSIVE** otherwise.
- Regardless of outcome, the v1 “PROMOTED” status remains labeled
  **identifiability-only** and is not a production recommendation.

## Disclosure

This follow-up was designed after seeing v1. It uses fresh seeds and a grid
fixed before execution. It is still vulnerable to analyst degrees of freedom
in choosing the grid; the grid is coarse and the result must be replicated
externally before any stronger claim.
