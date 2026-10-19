# Superseded calibration artifacts

These runs were produced before a config-hash serialization fix.  Their
`summary.json` config hash did not match `config.json`, so
`verify_artifact` correctly reported an integrity error.  They are retained
for provenance, not as valid evidence.  The studies were rerun with the same
pre-declared seeds and the corrected serialization; the replacements are in
the parent directory.

Do not cite the superseded numbers.  Do not delete them to hide the failure.
