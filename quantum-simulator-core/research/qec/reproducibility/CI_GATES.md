# CI gates A–E

The research job in `.github/workflows/ci.yml` runs five explicit gates. A
failure in any gate fails the job; blocked external checks are documented,
never silently marked passing.

| Gate | What it enforces | Command |
| --- | --- | --- |
| A | Lint and strict typing | `ruff check quantumlab tests research/qec/scripts research/qec/benchmarks`; `mypy quantumlab` |
| B | Unit and integration tests | `pytest -q` |
| C | Executable capability audit and protocol validation | `python -m quantumlab.research.qec audit`; `validate ...` |
| D | Committed artifact integrity and claim language | `python research/qec/scripts/verify_artifacts.py`; `claims <latest>` |
| E | Reproduction and independent validation on fresh output | `reproduce ...`; `run_validation(...)` |

## Gate E conditions

- The reproduction must produce `status == "REPRODUCED"` under the
  pre-declared target; tolerances are not changed in CI.
- The validation suite must produce an overall status beginning with `PASS`.
- Stim and PyMatching are pinned in CI (`1.16.0`, `2.4.0`) because sampling
  is version-dependent.

## Blocked in CI (reported, not passed)

- External replication (no external group).
- Hardware logical-error measurement (no hardware).
- Leakage/coherent/correlated noise (not modeled).
- GitHub-hosted runner results have not been observed from this sandbox; the
  local commands pass, but the hosted run is `UNVERIFIED` until the workflow
  executes on GitHub.
