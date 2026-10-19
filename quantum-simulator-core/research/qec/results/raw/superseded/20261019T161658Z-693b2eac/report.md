# Exploratory calibration generalization (v2)

- Status: **REJECTED**
- Rationale: A core gate failed on held-out seeds.
- This test was designed after the v1 result; it is exploratory.

| Gate | Result | Detail |
| --- | --- | --- |
| G1_selection_isolation | PASS | "development master seed 4201; held-out master seed 9201" |
| G2_no_control_degradation | FAIL | {"control_relative_change": 0.032510535821794195, "interval": [0.0018600000000000005, 0.0035400000000000015]} |
| G3_recovery_ge_50pct | PASS | {"candidate_ler": 0.00609, "nominal_ler": 0.00767, "oracle_ler": 0.00614, "recovery": 1.0326797385620914} |
| G4_replication_d3_d5 | PASS | {"d3": {"difference_bootstrap_ci": [-0.0021899999999999992, -0.0012399999999999998], "difference_first_minus_second": -0.00171, "first_failures": 1379, "first_ler": 0.01379, "first_summary": {"confidence_level": 0.95, "failures": 1379, "interval_high": 0.01453169886670615, "interval_low": 0.013085654812231853, "method": "wilson", "probability": 0.01379, "trials": 100000}, "mcnemar": {"both_failure": 1180, "both_success": 98251, "discordant": 569, "first_only": 199, "method": "exact_binomial_two_sided", "p_value": 6.9460585807036e-13, "second_only": 370, "statistic": 51.390158172231985}, "relative_excess": -0.11032258064516129, "second_failures": 1550, "second_ler": 0.0155, "second_summary": {"confidence_level": 0.95, "failures": 1550, "interval_high": 0.016284457658396454, "interval_low": 0.014752764647696518, "method": "wilson", "probability": 0.0155, "trials": 100000}, "trials": 100000, "zero_failure_note": null}, "d5": {"difference_bootstrap_ci": [-0.00198, -0.00119], "difference_first_minus_second": -0.00158, "first_failures": 609, "first_ler": 0.00609, "first_summary": {"confidence_level": 0.95, "failures": 609, "interval_high": 0.0065915398661085785, "interval_low": 0.0056264053747632015, "method": "wilson", "probability": 0.00609, "trials": 100000}, "mcnemar": {"both_failure": 481, "both_success": 99105, "discordant": 414, "first_only": 128, "method": "exact_binomial_two_sided", "p_value": 5.622527433703863e-15, "second_only": 286, "statistic": 60.29951690821256}, "relative_excess": -0.20599739243807041, "second_failures": 767, "second_ler": 0.00767, "second_summary": {"confidence_level": 0.95, "failures": 767, "interval_high": 0.008229953916257797, "interval_low": 0.007147869939178221, "method": "wilson", "probability": 0.00767, "trials": 100000}, "trials": 100000, "zero_failure_note": null}} |
| G5_mcnemar_p_lt_0.05 | PASS | {"p_value": 5.622527433703863e-15} |

| Cell | p_gate | p_meas | Selection score | Ambiguous |
| --- | ---: | ---: | ---: | --- |
| control_d3 | 0.012 | 0.004 | 0.0933965 | False |
| control_d5 | 0.012 | 0.001 | 0.0753922 | False |
| measurement_heavy_d3 | 0.001 | 0.025 | 0.0865695 | False |
| measurement_heavy_d5 | 0.001 | 0.025 | 0.0888599 | False |
| gate_heavy_d3 | 0.018 | 0.004 | 0.0645579 | True |
| gate_heavy_d5 | 0.018 | 0.012 | 0.0333953 | False |