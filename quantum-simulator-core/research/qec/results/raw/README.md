# Raw artifacts

Each directory is identified by UTC timestamp plus a random suffix and is
written atomically. `checksums.sha256` covers every file except itself;
`manifest.json` records sizes and hashes. Verify with:

```bash
python -m quantumlab.research.qec verify <directory>
python -m quantumlab.research.qec claims <directory>
```

The `superseded/` subdirectory contains runs whose summary/config hash
serialization was inconsistent. They are retained for provenance, not cited
as evidence.

## Known provenance defect in the committed 2026-10-19 artifacts

The Phase 2/3/4 scripts compute all samples **before** opening the
`ArtifactRun` context (so that a computation failure cannot leave a
half-written artifact). In those three artifacts, `start_utc`,
`end_utc`, and `runtime_seconds` therefore measure only artifact writing
(tens of milliseconds), not the study wall-clock time. The experiment-ID
timestamp likewise marks the start of writing.

Actual durations were observed separately: Phase 2 about 1.5 minutes,
Phase 4 v1 2 m 49 s, Phase 4 v2 2 m 0 s.

The scripts were corrected afterwards to record `start_utc` and
`runtime_seconds` around the whole study. The committed artifacts were
**not** rewritten or re-run, because re-running would change their IDs and
because the numerical results are unaffected. This affects provenance
timing only; it does not affect the recorded outcomes, hashes, or seeds.
