# Research question (Phase 3, pre-declared)

**Pre-declared:** 2026-10-19, before the confirmatory runs.  
**Status of the question:** narrow, measurable, and falsifiable.  
**Novelty status:** **none claimed.** The closest literature is cited below.

## Question

> In a Stim circuit-level depolarizing model of a rotated surface-code Z-memory,
> how much logical-error-rate penalty is incurred when the MWPM decoder is
> built from a **static nominal detector error model** (all four Stim noise
> hooks set to 1%) while the true gate and measurement error rates are unequal
> but share a similar total scale? And can a decoder calibrated only from
> observed detector statistics recover a measurable fraction of the
> oracle-model advantage on held-out shots?

## Why this is a limitation of the current system

The current QuantumLab QEC engine supports:

- explicitly specified Pauli/phenomenological noise for small codes, and
- Stim circuit-level noise for surface codes, decoded with PyMatching from
  **the detector error model of the same circuit**.

The engine has no calibration loop. If a real or simulated device has a
measurement-to-gate error ratio different from the nominal model, the decoder
graph is mis-weighted. The resulting penalty is not visible in a standard
threshold plot because both the circuit and the decoder use the same nominal
value. This work isolates that penalty and tests one calibration candidate.

## Pre-declared hypotheses

| ID | Hypothesis | Falsification |
| --- | --- | --- |
| H3a | For a measurement-dominated profile `(p_gate, p_meas) = (0.002, 0.020)`, the nominal uniform-1% decoder has **≥10% relative excess logical failure** at d=5 compared with the oracle DEM. | Relative excess <10% or its paired 95% interval includes 10%. |
| H3b | For a gate-dominated profile `(0.020, 0.002)`, the nominal decoder penalty is **<5%** relative excess at d=5. | Relative excess ≥5% with paired interval excluding 5%. |
| H3c | The measurement-dominated penalty is larger at d=5 than at d=3. | d=5 excess ≤ d=3 excess. |
| H3d | A global two-parameter DEM calibrated from observed detector-cohort rates recovers **at least 50%** of the oracle gain on the measurement-dominated profile at d=5, without degrading the control profile. | <50% recovery, or control degradation >2% relative with interval excluding the bound. |

H3a–H3c are descriptive limitations. H3d is the candidate gate. A failure of
H3d is a preserved negative result, not a reason to retune on held-out data.

## Scope limits

- Only **Z-basis memory**, rotated surface code, distances 3 and 5, rounds =
  distance.
- Only the Stim standard circuit-level depolarizing model with
  `after_clifford_depolarization = before_round_data_depolarization =
  after_reset_flip_probability = p_gate` and
  `before_measure_flip_probability = p_meas`.
- Only MWPM decoding on a decomposed detector error model.
- No leakage, coherent, correlated, drift, or non-Markovian noise.
- No hardware claim.
- No claim that the calibrated candidate is novel; the literature already
  contains noise-adaptive and calibration-based decoding.

## Closest prior work (non-exhaustive, verified metadata)

- The decoding-graph reweighting (DGR) line of work on decoding under drift
  and correlations, `arXiv:2311.16214` (abstract claims 3.6× average and
  >5000× worst-case logical-error reduction). This work does **not**
  implement drift or correlated noise, so it is not a reproduction or
  extension of that claim.
- “Adaptive Estimation of Drifting Noise in QEC,” `arXiv:2511.09491`,
  PRX Quantum DOI `10.1103/z1hc-nqw5`; estimates a time-dependent detector
  error model from syndrome data.
- “Improving error suppression with noise-aware decoding,”
  `arXiv:2502.21044`; ACES calibration of a correlated-matching decoder.
- “Optimal adaptation of surface-code decoders to local noise,”
  `arXiv:2403.08706`, PRX DOI `10.1103/r2dc-qcrx`; only a few critical noise
  parameters need adaptation.
- Google Quantum AI, AlphaQubit, *Nature* (2024), DOI
  `10.1038/s41586-024-08148-8`; a learned decoder, not used here.
- `arXiv:2406.02700`; prior calibration improved decoding by 16% (repetition)
  and 3.3% (surface) on Sycamore data. That is a hardware result and is not
  directly comparable to this simulation.

These works establish that the general area is crowded. This study is an
**engineering limitation measurement plus a gated candidate test**, not a
novelty claim.
