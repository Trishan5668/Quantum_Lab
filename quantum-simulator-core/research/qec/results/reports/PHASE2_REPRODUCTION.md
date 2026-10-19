# Reproduction: surface_code_threshold_mwpm_v1

- Experiment ID: `20261019T160933Z-bc711864`
- Status: **REPRODUCED** (`REPRODUCED_WITHIN_DECLARED_MODEL`)
- Rationale: The measured crossing is inside the pre-declared literature band, is statistically resolved at the refinement points, and both distance-ordering checks pass for the declared model.
- Pre-declared band: [0.0055, 0.0085]
- Measured bracket: [0.006, 0.007]

## Reference result

Circuit-level threshold of the rotated surface code under depolarizing noise with minimum-weight perfect matching, reported at approximately 0.57% per step (Fowler et al., PRA 86, 032324, 2012; DOI 10.1103/PhysRevA.86.032324) and approximately 0.7% for the standard circuit-level depolarizing model in the PyMatching documentation (Higgott, ACM TQC 3(3), Article 16, 2022; DOI 10.1145/3505637).

## Model under test

Stim generated surface_code:rotated_memory_z circuit, distances 3/5/7, rounds equal to distance; all four Stim depolarizing hooks set to p; PyMatching MWPM on the decomposed detector error model. This is Stim's standard circuit-level model, not the exact gate-level model of Fowler et al.

## Results

| Stage | d | p | Shots | Failures | LER | Wilson 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| coarse | 3 | 0.0040 | 20000 | 243 | 0.01215 | [0.0107226, 0.0137648] |
| coarse | 3 | 0.0050 | 20000 | 324 | 0.0162 | [0.014541, 0.0180448] |
| coarse | 3 | 0.0060 | 20000 | 493 | 0.02465 | [0.0225906, 0.0268919] |
| coarse | 3 | 0.0070 | 20000 | 657 | 0.03285 | [0.030468, 0.0354114] |
| coarse | 3 | 0.0080 | 20000 | 788 | 0.0394 | [0.0367911, 0.0421858] |
| coarse | 3 | 0.0100 | 20000 | 1177 | 0.05885 | [0.0556723, 0.0621971] |
| coarse | 5 | 0.0040 | 20000 | 160 | 0.008 | [0.00685637, 0.0093326] |
| coarse | 5 | 0.0050 | 20000 | 284 | 0.0142 | [0.0126511, 0.0159355] |
| coarse | 5 | 0.0060 | 20000 | 480 | 0.024 | [0.0219685, 0.0262143] |
| coarse | 5 | 0.0070 | 20000 | 697 | 0.03485 | [0.0323963, 0.0374824] |
| coarse | 5 | 0.0080 | 20000 | 945 | 0.04725 | [0.0443954, 0.0502785] |
| coarse | 5 | 0.0100 | 20000 | 1720 | 0.086 | [0.0821935, 0.0899655] |
| coarse | 7 | 0.0040 | 20000 | 80 | 0.004 | [0.0032154, 0.0049751] |
| coarse | 7 | 0.0050 | 20000 | 206 | 0.0103 | [0.00899174, 0.0117963] |
| coarse | 7 | 0.0060 | 20000 | 374 | 0.0187 | [0.0169129, 0.0206719] |
| coarse | 7 | 0.0070 | 20000 | 673 | 0.03365 | [0.031239, 0.0362401] |
| coarse | 7 | 0.0080 | 20000 | 1073 | 0.05365 | [0.050612, 0.0568594] |
| coarse | 7 | 0.0100 | 20000 | 2073 | 0.10365 | [0.0995015, 0.107951] |
| refinement | 3 | 0.0060 | 200000 | 4931 | 0.024655 | [0.0239845, 0.0253438] |
| refinement | 3 | 0.0070 | 200000 | 6364 | 0.03182 | [0.0310597, 0.0325983] |
| refinement | 5 | 0.0060 | 200000 | 4510 | 0.02255 | [0.0219085, 0.0232099] |
| refinement | 5 | 0.0070 | 200000 | 6970 | 0.03485 | [0.0340551, 0.0356627] |

## Pre-declared criteria

| Criterion | Result | Detail |
| --- | --- | --- |
| bracket_exists | PASS | bracket=[0.006, 0.007] |
| bracket_in_predeclared_band | PASS | band=[0.0055, 0.0085] |
| refinement_significant | PASS | Newcombe 95% intervals exclude zero with opposite signs |
| ordering_below_threshold | PASS | LER(d3,d5,d7) at p=0.004 = (0.01215, 0.008, 0.004) |
| ordering_above_threshold | PASS | LER(d3,d5,d7) at p=0.010 = (0.05885, 0.086, 0.10365) |

## Claim labels

| Claim | Label |
| --- | --- |
| Declared model reproduces the published threshold band | REPRODUCED_WITHIN_DECLARED_MODEL |
| Native QuantumLab circuit-level sampler | NOT_CLAIMED (Stim used) |
| Hardware behavior | NOT_CLAIMED |
| Novelty or superiority | NOT_CLAIMED |

## Limitations and disclosures

- The model is Stim's standard circuit-level depolarizing model, not Fowler et al.'s exact gate-level error placement.
- Threshold values are decoder- and model-dependent; the quoted band is a literature band, not a universal constant.
- The exploratory pilot disclosed in the target is not evidence.
- Raw per-shot logical outcomes are stored compressed in `outcomes.npz`; circuits and detector error models are identified by SHA-256 in the summary.
