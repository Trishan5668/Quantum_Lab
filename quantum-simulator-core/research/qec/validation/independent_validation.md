# Independent validation report

- Generated: 2026-10-19T16:18:05.627386+00:00
- Overall status: **PASS_L1_L2_EXTERNAL_REPLICATION_BLOCKED**
- Independence: L1 analytic + L2 independent implementation; L3 external replication BLOCKED

| Check | Status | Independence | Description |
| --- | --- | --- | --- |
| V1_pauli_matrix_product | PASS | L1 | Pauli matrix product equals product of matrices |
| V2_code_parameters | PASS | L1 | Declared code parameters and algebraic validation |
| V3_exact_decoder_all_syndromes | PASS | L1 | Exact decoder returns a syndrome-consistent correction for every syndrome |
| V4_exact_vs_mwpm | PASS | L2 | Exact and MWPM corrections differ only by a stabilizer |
| V5_analytic_repetition_d3 | PASS | L1 | Exact enumeration matches the closed-form d=3 bit-flip failure probability |
| V6_stim_vs_native_repetition | PASS | L2 | Stim/PyMatching and native exact decoding agree on depolarizing repetition memory |
| V7_interval_identities | PASS | L1 | Wilson/Clopper-Pearson/zero-failure identities |
| V8_artifact_reproducibility | PASS | L1 | Same protocol and seed reproduce byte-identical records |

## Blocked

- BLOCKED: V9 external replication (no external group)
- BLOCKED: V10 hardware logical error rate (no hardware)
- BLOCKED: V11 leakage/coherent-noise validation (not modeled)
- BLOCKED: V12 surface-code distance >7 exact validation (cost)

## Scope

Passing these checks supports implementation correctness. It is not external replication, a hardware result, or a novelty claim.
