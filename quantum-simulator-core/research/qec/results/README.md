# QEC results

- `raw/<experiment_id>/` — immutable artifacts written by the runner. Each
  contains `summary.json`, `config.json`, `provenance.json`,
  `environment.json`, `report.md`, `manifest.json`, `checksums.sha256`, and
  either per-shot records or compressed logical outcomes.
- `raw/superseded/` — runs retained after a provenance/integrity defect. Not
  valid evidence; kept to avoid hiding a failure.
- `processed/` — derived CSV/JSON tables built only from verified raw
  artifacts. `ARTIFACTS.json` maps processed outputs to raw hashes.
- `reports/` — human-readable phase reports with claim labels.

Never overwrite a raw artifact. Re-run into a new directory. `verify_artifact`
must pass before a result is cited.
