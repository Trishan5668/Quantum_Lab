# Reproducibility instructions

This directory records how to reproduce the QEC research artifacts without
editing raw data. The raw artifacts are committed under
`results/raw/<experiment_id>/` and each is independently verifiable.

## Environment

| Component | Version used |
| --- | --- |
| Python | 3.11.2 |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| PyYAML | 6.0.3 |
| Stim | 1.16.0 |
| PyMatching | 2.4.0 |
| pytest | 9.1.1 |
| hypothesis | 6.170.2 |
| ruff | 0.17.1 |
| mypy | 2.4.0 |
| OS | Linux 6.1 (x86_64) |

Install the exact optional tools for the recorded numerics:

```bash
python -m pip install -e ".[dev]"
python -m pip install "stim==1.16.0" "pymatching==2.4.0"
```

The core package does not require Stim/PyMatching; those paths are optional
and are labeled as delegated in every artifact.

## Commands

All commands run from `quantum-simulator-core`.

```bash
# Gate A
ruff check quantumlab tests research/qec/scripts research/qec/benchmarks
mypy quantumlab

# Gate B
pytest -q

# Gate C
python -m quantumlab.research.qec audit

# Gate D
python research/qec/scripts/verify_artifacts.py
python -m quantumlab.research.qec claims <artifact-directory>

# Gate E: Phase 2 reproduction (fresh artifact; does not overwrite raw)
python -m quantumlab.research.qec reproduce \
  research/qec/reproduction/surface_code_threshold_v1.yaml \
  --output /tmp/qec_reproduction

# Gate E: Phase 3/4 studies (takes about 5 minutes)
python -m quantumlab.research.qec.calibration --output /tmp/qec_calibration
python - <<'PY'
from pathlib import Path
from quantumlab.research.qec.calibration import run_generalization_study
print(run_generalization_study(Path("/tmp/qec_calibration")))
PY

# Independent validation
python - <<'PY'
from pathlib import Path
from quantumlab.research.qec.validation import run_validation
print(run_validation(Path("/tmp/qec_validation"))["overall_status"])
PY

# Processed tables (refuses artifacts that fail integrity)
python research/qec/scripts/build_processed.py
```

## Seeds

| Study | Master seed | Derivation |
| --- | ---: | --- |
| Phase 2 reproduction | 20261020 | `SeedSequence([20261020, d, round(p*1e6), stage])` |
| Phase 3 limitation | 3101 | `SeedSequence([3101, d, p_gate, p_meas, 0])` |
| Phase 4 v1 development | 4101 | `SeedSequence([4101, d, p_gate, p_meas, purpose])` |
| Phase 4 v1 held-out | 9101 | same, held-out master |
| Phase 4 v2 development | 4201 | same, generalization grid |
| Phase 4 v2 held-out | 9201 | same, generalization grid |

No held-out seed was used for candidate selection.

## Committed artifacts

| Role | Experiment ID | Status |
| --- | --- | --- |
| Phase 2 threshold reproduction | `20261019T160933Z-bc711864` | `REPRODUCED_WITHIN_DECLARED_MODEL` |
| Phase 3/4 calibration v1 | `20261019T162813Z-fab5ad81` | `PROMOTED` (identifiability only; not default) |
| Phase 4 generalization v2 | `20261019T162505Z-08ad35cb` | `REJECTED` (control degradation) |
| Superseded pre-fix runs | `results/raw/superseded/` | retained, not valid evidence |

The `summary.json` and `checksums.sha256` in each directory are the authority.
`results/processed/ARTIFACTS.json` records their hashes and claim-audit status.

## Determinism

- The Pauli backend uses NumPy `SeedSequence` streams recorded in the summary.
- Stim sampling uses explicit integer seeds derived from the master seeds.
- Same seed and same package versions reproduce byte-identical per-shot
  records for the Pauli backend (`V8` validation check).
- Stim guarantees are version-dependent. Re-running with a different Stim
  version can change sampled shots; the versions are recorded and CI pins
  Stim 1.16.0 / PyMatching 2.4.0.
- Artifact directories are unique and never overwritten. A failed run is
  preserved as `failed-<id>`.

## What is not reproducible here

- Hardware measurements: not performed.
- Leakage/coherent/correlated/drift noise: not modeled.
- External replication: blocked; no reviewer or independent group.
- Native circuit-level surface-code execution: not implemented; Stim executes.
