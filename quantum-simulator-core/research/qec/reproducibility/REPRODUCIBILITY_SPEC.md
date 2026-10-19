# Reproducibility specification

Status: **IMPLEMENTED_AND_LOCALLY_VERIFIED** for the three committed research
artifacts. External replication remains **BLOCKED** (see
`validation/INDEPENDENT_VALIDATION_PLAN.md`).

This specification defines what "reproducible" means in this repository and
the exact steps a third party must take to verify or re-run each result.

## 1. Artifact format

Every run writes to `results/raw/<experiment_id>/`, where `experiment_id` is
`<UTC timestamp>Z-<8 hex chars>` and is never reused.

| File | Role |
| --- | --- |
| `summary.json` | Machine-readable result, config hash, seeds, status, claim label |
| `config.json` | Fully expanded experiment configuration |
| `provenance.json` | Git commit, dirty flag, package versions, command |
| `environment.json` | Python/platform/package snapshot |
| `report.md` | Human-readable summary, including limitations |
| `manifest.json` | Declared file sizes and hashes |
| `checksums.sha256` | SHA-256 of every file except itself |
| `records.jsonl.gz` or `trials.npz` | Per-shot data where applicable |

`summary.json` includes `schema_version`, `experiment_id`, `config_hash`,
`status`, `claim_label`, and `limitations`. The config hash is computed over
`canonical_json(config)` (sorted keys, no whitespace). Changing any
scientifically relevant parameter changes the hash.

Artifacts written **before** the canonical-hash fix are in
`results/raw/superseded/`; they are retained to document the defect but must
not be cited.

## 2. Integrity

```bash
python -m quantumlab.research.qec verify results/raw/<id>
python research/qec/scripts/verify_artifacts.py
```

`verify` recomputes the checksum file, compares it with the in-process
manifest, and re-derives the config hash. `verify_artifacts.py` additionally
runs the claims audit on every artifact listed in
`results/processed/ARTIFACTS.json`. Current result: `{"checked": 3,
"failures": []}`.

Integrity is necessary but not sufficient: it shows the bytes are the ones
that were produced, not that the science is correct.

## 3. Determinism and seeds

- Seeds are derived with `numpy.random.SeedSequence` from a declared master
  seed, the code distance, the noise parameters, and a purpose tag. The
  derivation is recorded in the artifact.
- Development and held-out seeds are disjoint. Held-out seeds were not used
  for candidate selection or tolerance selection.
- Same seeds + same package versions reproduce byte-identical Pauli-backend
  shot records (`V8` in the validation suite, SHA-256 `36607140…4ed47c`).
- Stim sampling is reproducible for a fixed Stim version. CI pins
  `stim==1.16.0` and `pymatching==2.4.0`.

Independent re-derivation of results (as opposed to a byte-level replay)
should use a **fresh seed block** not present in the artifact, declared before
running:

| Block | Range | Reserved for |
| --- | --- | --- |
| Development (used) | 4101–4201 | Phase 4 v1/v2 selection |
| Held-out (used) | 9101–9201 | Phase 4 evaluation only |
| Independent replication (unused) | 20000–20099 | External or future replication |

An independent run with block 20000–20099 is expected to agree within the
pre-declared statistical tolerances; it is not expected to be byte-identical.

## 4. Exact reproduction commands

From `quantum-simulator-core`:

```bash
# Phase 2: surface-code threshold bracket (pymatching/stim)
python -m quantumlab.research.qec reproduce \
  research/qec/reproduction/surface_code_threshold_v1.yaml \
  --output /tmp/repro_phase2

# Phase 3/4 v1 calibration (about 3 minutes)
python -m quantumlab.research.qec.calibration --output /tmp/repro_calibration

# Phase 4 v2 generalization
python - <<'PY'
from pathlib import Path
from quantumlab.research.qec.calibration import run_generalization_study
print(run_generalization_study(Path("/tmp/repro_calibration")))
PY

# Phase 6 validation
python - <<'PY'
from pathlib import Path
from quantumlab.research.qec.validation import run_validation
print(run_validation(Path("/tmp/repro_validation"))["overall_status"])
PY
```

Expected outcomes (committed artifacts):

| Command | Committed ID | Expected |
| --- | --- | --- |
| Phase 2 | `20261019T160933Z-bc711864` | `REPRODUCED`, bracket `[0.006, 0.007]` |
| Phase 4 v1 | `20261019T162813Z-fab5ad81` | `PROMOTED` (identifiability only) |
| Phase 4 v2 | `20261019T162505Z-08ad35cb` | `REJECTED` (G2 control failure) |
| Validation | `validation/independent_validation.json` | `PASS_L1_L2_EXTERNAL_REPLICATION_BLOCKED` |

The v2 `REJECTED` result is expected. Reproducing it is success, not failure.

## 5. Tolerances

Tolerances were declared in
`reproduction/surface_code_threshold_v1.yaml` before the confirmatory run and
are not adjusted. Statistical comparisons use 95% binomial intervals and
McNemar exact tests; no zero-event rate is reported as zero (rule of three /
Wilson upper bounds are used instead).

A result is "reproduced" only if the measured bracket lies inside the
pre-declared acceptance interval. A result that misses it is reported as
`NOT_REPRODUCED` and the artifact is kept.

## 6. Evidence packages

```bash
python -m quantumlab.research.qec package results/raw/<id> \
  --output reproducibility/packages/<id>-evidence.tar.gz
```

Each package has a `.manifest.json` with the package SHA-256, artifact
integrity report, and `scientific_claim_status` set to
`NOT_INDEPENDENTLY_VALIDATED`. Package integrity is not a scientific claim.

## 7. Known defect in committed artifacts (timing only)

The three committed artifacts record `runtime_seconds` and `start_utc` from
the artifact-writing phase only, because their scripts computed samples before
opening the artifact context. The scripts now time the whole study, so a fresh
run records the true duration. The committed artifacts were not rewritten:
their numerical content, seeds, and hashes are unaffected, and re-running
would change the cited experiment IDs. See `results/raw/README.md`.

## 8. Known non-reproducible / blocked items

| Item | Status | Reason |
| --- | --- | --- |
| External independent replication | BLOCKED | No external group/reviewer |
| Hardware logical-error measurement | BLOCKED | No hardware access |
| Leakage/coherent/correlated noise | NOT_MODELED | Outside declared noise class |
| Native surface-code d>7 exact decoding | NOT_RUN | Exponential table growth |
| GitHub-hosted CI result | UNVERIFIED | Workflow never executed here |
