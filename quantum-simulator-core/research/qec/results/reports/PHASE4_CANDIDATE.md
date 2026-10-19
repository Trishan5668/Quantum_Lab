# Exploratory calibration generalization (v2)

- Status: **REJECTED**
- Rationale: A core gate failed on held-out seeds.
- This test was designed after the v1 result; it is exploratory.

| Gate | Result | Detail |
| --- | --- | --- |
| G1_selection_isolation | PASS | "development master seed 4201; held-out master seed 9201" |
| G2_no_control_degradation | FAIL | {"control_relative_change": 0.032510535821794195, "interval": [0.0018600000000000005, 0.0035400000000000015]} |
| G3_recovery_ge_50pct | PASS | {"candidate_ler": 0.00609, "nominal_ler": 0.00767, "oracle_ler": 0.00614, "recovery": 1.0326797385620914} |
| G4_replication_d3_d5 | PASS | {"d3": {"both_failure": 1180, "both_success": 98251, "difference_bootstrap_ci": [-0.0021899999999999992, -0.0012399999999999998], "difference_first_minus_second": -0.00171, "discordant": 569, "first_failures": 1379, "first_ler": 0.01379, "first_only": 199, "first_summary": {"confidence_level": 0.95, "failures": 1379, "interval_high": 0.01453169886670615, "interval_low": 0.013085654812231853, "method": "wilson", "probability": 0.01379, "trials": 100000}, "mcnemar": {"both_failure": 1180, "both_success": 98251, "discordant": 569, "first_only": 199, "method": "exact_binomial_two_sided", "p_value": 6.9460585807036e-13, "second_only": 370, "statistic": 51.390158172231985}, "relative_excess": -0.11032258064516129, "second_failures": 1550, "second_ler": 0.0155, "second_only": 370, "second_summary": {"confidence_level": 0.95, "failures": 1550, "interval_high": 0.016284457658396454, "interval_low": 0.014752764647696518, "method": "wilson", "probability": 0.0155, "trials": 100000}, "trials": 100000, "zero_failure_note": null}, "d5": {"both_failure": 481, "both_success": 99105, "difference_bootstrap_ci": [-0.00198, -0.00119], "difference_first_minus_second": -0.00158, "discordant": 414, "first_failures": 609, "first_ler": 0.00609, "first_only": 128, "first_summary": {"confidence_level": 0.95, "failures": 609, "interval_high": 0.0065915398661085785, "interval_low": 0.0056264053747632015, "method": "wilson", "probability": 0.00609, "trials": 100000}, "mcnemar": {"both_failure": 481, "both_success": 99105, "discordant": 414, "first_only": 128, "method": "exact_binomial_two_sided", "p_value": 5.622527433703863e-15, "second_only": 286, "statistic": 60.29951690821256}, "relative_excess": -0.20599739243807041, "second_failures": 767, "second_ler": 0.00767, "second_only": 286, "second_summary": {"confidence_level": 0.95, "failures": 767, "interval_high": 0.008229953916257797, "interval_low": 0.007147869939178221, "method": "wilson", "probability": 0.00767, "trials": 100000}, "trials": 100000, "zero_failure_note": null}} |
| G5_mcnemar_p_lt_0.05 | PASS | {"p_value": 5.622527433703863e-15} |

| Cell | p_gate | p_meas | Selection score | Ambiguous |
| --- | ---: | ---: | ---: | --- |
| control_d3 | 0.012 | 0.004 | 0.0933965 | False |
| control_d5 | 0.012 | 0.001 | 0.0753922 | False |
| measurement_heavy_d3 | 0.001 | 0.025 | 0.0865695 | False |
| measurement_heavy_d5 | 0.001 | 0.025 | 0.0888599 | False |
| gate_heavy_d3 | 0.018 | 0.004 | 0.0645579 | True |
| gate_heavy_d5 | 0.018 | 0.012 | 0.0333953 | False |

---

## v1 identifiability result

# Static-DEM mismatch and calibrated candidate

**Claim labels:** limitation measurement on a declared simulation; no novelty claim; no hardware claim; no AI model was used.

## Phase 3 — measured limitation

| Profile | d | Nominal LER | Oracle LER | Relative excess | Nominal vs oracle p |
| --- | ---: | ---: | ---: | ---: | ---: |
| control | 3 | 0.05824 | 0.05824 | 0.0000% | 1 |
| control | 5 | 0.08479 | 0.08479 | 0.0000% | 1 |
| measurement_heavy | 3 | 0.01515 | 0.01325 | 14.3396% | 1.49e-20 |
| measurement_heavy | 5 | 0.00745 | 0.00609 | 22.3317% | 4.7e-14 |
| gate_heavy | 3 | 0.14461 | 0.14598 | -0.9385% | 0.000468 |
| gate_heavy | 5 | 0.26775 | 0.27056 | -1.0386% | 0.00197 |

| Hypothesis | Supported |
| --- | --- |
| H3a_measurement_heavy_d5_excess_ge_10pct | True |
| H3b_gate_heavy_d5_excess_lt_5pct | True |
| H3c_excess_larger_at_d5 | True |

## Phase 4 — gated candidate

- Status: **PROMOTED**
- Rationale: All pre-declared gates passed on held-out seeds.
- PROMOTED means only that the pre-declared identifiability gates passed. The v1 grid contains the true profiles, so this is not evidence of calibration under misspecification. It is not a default decoder and not a production recommendation.
- **Identifiability caveat:** the v1 candidate grid contains the exact generating profiles. Recovering them demonstrates parameter identifiability, not calibration under model misspecification. See the separately pre-declared generalization test, which used a grid excluding the true values and was REJECTED for control degradation. No default decoder change is made.

| Gate | Result | Detail |
| --- | --- | --- |
| G1_selection_isolation | PASS | "selection used development master seed 4101; held-out master seed 9101" |
| G2_no_control_degradation | PASS | {"control_relative_change": 0.0, "required": "<= 0.02 and interval upper < 2% of nominal"} |
| G3_recovery_ge_50pct | PASS | {"candidate_ler": 0.00569, "nominal_ler": 0.00717, "oracle_ler": 0.00569, "recovery": 1.0} |
| G4_replication_d3_d5 | PASS | {"d3": {"both_failure": 1270, "both_success": 98292, "difference_bootstrap_ci": [-0.002660000000000001, -0.00183], "difference_first_minus_second": -0.00224, "discordant": 438, "first_failures": 1377, "first_ler": 0.01377, "first_only": 107, "first_summary": {"confidence_level": 0.95, "failures": 1377, "interval_high": 0.014511182826829441, "interval_low": 0.013066172388633062, "method": "wilson", "probability": 0.01377, "trials": 100000}, "mcnemar": {"both_failure": 1270, "both_success": 98292, "discordant": 438, "first_only": 107, "method": "exact_binomial_two_sided", "p_value": 1.0540688016088015e-27, "second_only": 331, "statistic": 114.55707762557077}, "relative_excess": -0.13991255465334165, "second_failures": 1601, "second_ler": 0.01601, "second_only": 331, "second_summary": {"confidence_level": 0.95, "failures": 1601, "interval_high": 0.01680672620738319, "interval_low": 0.015250456917334943, "method": "wilson", "probability": 0.01601, "trials": 100000}, "trials": 100000, "zero_failure_note": null}, "d5": {"both_failure": 498, "both_success": 99212, "difference_bootstrap_ci": [-0.0018199999999999996, -0.00115], "difference_first_minus_second": -0.00148, "discordant": 290, "first_failures": 569, "first_ler": 0.00569, "first_only": 71, "first_summary": {"confidence_level": 0.95, "failures": 569, "interval_high": 0.006175557902653089, "interval_low": 0.005242418068708756, "method": "wilson", "probability": 0.00569, "trials": 100000}, "mcnemar": {"both_failure": 498, "both_success": 99212, "discordant": 290, "first_only": 71, "method": "exact_binomial_two_sided", "p_value": 1.00999233357721e-18, "second_only": 219, "statistic": 75.53103448275863}, "relative_excess": -0.20641562064156208, "second_failures": 717, "second_ler": 0.00717, "second_only": 219, "second_summary": {"confidence_level": 0.95, "failures": 717, "interval_high": 0.007712195531306848, "interval_low": 0.0066656667372417535, "method": "wilson", "probability": 0.00717, "trials": 100000}, "trials": 100000, "zero_failure_note": null}} |
| G5_mcnemar_p_lt_0.05 | PASS | {"p_value": 1.00999233357721e-18} |

## Selected candidates (development only)

| Cell | p_gate | p_meas | Score | Ambiguous |
| --- | ---: | ---: | ---: | --- |
| control_d3 | 0.01 | 0.01 | 0.0123989 | False |
| control_d5 | 0.01 | 0.01 | 0.00981508 | False |
| measurement_heavy_d3 | 0.002 | 0.02 | 0.0138566 | False |
| measurement_heavy_d5 | 0.002 | 0.02 | 0.0152639 | False |
| gate_heavy_d3 | 0.02 | 0.002 | 0.0127043 | False |
| gate_heavy_d5 | 0.02 | 0.001 | 0.00748113 | False |

## Honest limitations

- Stim/PyMatching execute the circuit-level simulation and decoding; these are not native QuantumLab results.
- No leakage, coherent, correlated, drift, or non-Markovian noise is modeled.
- Threshold and LER values are model- and decoder-specific.
- The candidate is rule-based; no AI API was called, so no AI-discovery claim is made.
- The gate status is not a production recommendation.
