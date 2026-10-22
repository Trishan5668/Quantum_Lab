# QuantHub platform guide

This document describes the QuantHub layer that sits on top of the QuantumLab
engine: the data model, the experiment pipeline, the frontend module map, and the
limits that remain.

## 1. Data model

All metadata lives in SQLite (`QUANTHUB_DATA_DIR/quanthub.sqlite3`); file content
and history live in bare Git repositories under `QUANTHUB_DATA_DIR/repos`; run
evidence lives under `QUANTHUB_DATA_DIR/projects/<project_id>/runs/<run_id>`.

| Table | Purpose |
| --- | --- |
| `users` | Identity records derived from Firebase tokens or the dev identity |
| `projects` | Owner, name, slug, description, topics, visibility, license, language, timestamps |
| `project_members` | Roles: `owner`, `maintainer`, `reader` |
| `commits` | Denormalized commit metadata for listing without shelling out |
| `stars`, `watches` | Viewer relationships |
| `experiment_specs` | Validated protocol JSON, config hash, author |
| `runs` | Status, timings, config hash, project revision, engine revision, summary, artifact path, log path |
| `import_jobs` | Import kind, accepted file count and skipped entries |
| `activity` | Per-project event stream rendered on the dashboard and project sidebar |
| `news_cache` | Cached live feed payloads with fetch timestamps |

Projects are addressed by `owner/slug`, and both components are validated:
slugs are lowercased, restricted to `[a-z0-9._-]`, length-limited, and reserved
names (`new`, `explore`, `docs`, `settings`, …) are rejected.

### Compatibility

- Repository directories remain keyed by project id, not by name, so renaming a
  project does not move data.
- The Python package (`quantumlab`), the npm workspace names (`@quantumlab/*`),
  environment prefixes used by existing deployments (`QUANTUMLAB_*` where they
  already existed) and the Firestore collection names are unchanged.
- Existing simulator routes and their payload shapes are untouched.

## 2. Experiment pipeline

1. **Validate.** `POST /api/v1/experiments/validate` runs the protocol through
   `quantumlab.research.qec.protocol`. The API additionally rejects unknown noise
   parameters, decoders incompatible with the code family, and Stim-backed
   families when Stim/PyMatching is missing.
2. **Store.** A specification stores the accepted protocol and its config hash.
3. **Execute.** `POST .../experiments/{id}/runs` launches
   `python -m quantumlab.research.qec run <protocol> --output <dir> --experiment-id <id>`
   in a new session (`setsid`) with:
   - a scrubbed environment,
   - `ulimit -t` (CPU seconds), `-v` (2 GiB address space), `-n` (512 files),
   - a wall-clock timeout of `QUANTHUB_RUN_TIMEOUT_SECONDS`,
   - concurrency capped by `QUANTHUB_MAX_CONCURRENT_RUNS`.
4. **Collect.** The engine writes `config.json`, `provenance.json`,
   `environment.json`, `summary.json`, `manifest.json`, `checksums.sha256`,
   `records.jsonl` and `report.md`. The API stores a normalized view of
   `summary.result` for the UI and links each artifact by name.
5. **Verify.** `POST .../runs/{id}/verify` recomputes SHA-256 digests and
   cross-checks the manifest. This proves integrity, not correctness.
6. **Audit.** `GET .../runs/{id}/claims` reuses `quantumlab.research.qec.claims`
   to check required fields, zero-failure rows without an upper bound and banned
   claim language in the generated report.
7. **Reproduce.** A reproduction starts a new run from the stored protocol and
   records `reproduction_of`. It is not an independent reproduction.

Runs are never rewritten. Cancelling terminates the process and preserves the
partial log; failed runs keep their artifacts under a `failed-` prefix and are
not valid evidence.

## 3. Frontend module map

`quantum-desktop-app/packages/webapp/src/quanthub/`

| Path | Role |
| --- | --- |
| `client.ts` | `api<T>()` envelope unwrapping, uploads with progress/cancel, downloads, formatters, local identity and recents |
| `session.tsx` | `SessionProvider` / `useSession()` over Firebase + local identity |
| `types.ts` | TypeScript mirrors of the API payloads |
| `hooks.ts` | `useAsync`, polling, document title |
| `components/Shell.tsx` | Topbar, search, primary navigation, avatar menu |
| `components/ProjectChrome.tsx` | Project header, tabs, layout and sidebar |
| `components/FileBrowser.tsx` | Tree table and breadcrumbs |
| `components/ImportPanel.tsx` | Multi-file / folder / ZIP import with progress and cancel |
| `components/ExperimentBuilder.tsx` | Protocol editor with engine validation |
| `components/ResultsView.tsx` | Engine results, paired comparisons, provenance |
| `components/Markdown.tsx` | Sanitized Markdown |
| `components/NewsPanel.tsx` | Verified news rail |
| `pages/` | Home, Explore, Projects, New project, Project, Blob, Commits, Import, Settings, Experiments, Runs, Run detail, QEC Workbench, Community, Profile, Account settings, Welcome, 404 |

Routes are mounted at `/`, `/explore`, `/projects`, `/new`, `/experiments`,
`/community`, `/qec`, `/profile`, `/settings`, `/welcome`, `/:owner/:slug` and its
sub-routes (`blob/*`, `commits`, `import`, `settings`, `experiments[/:specId]`,
`runs[/:runId]`), plus `/:handle` for public profiles. Existing platform pages
(`/learn`, `/algorithms`, `/docs`, `/research`, `/api`, `/about`, `/blog`,
`/history`, `/app`, `/app/editor`) keep their URLs.

The Circuit Designer (`/app`) accepts `?project=owner/slug` and can save or load
circuits as JSON files inside that project, using the same revision checks as any
other edit.

## 4. Capability registry

`GET /api/v1/capabilities/languages` returns the full registry with separate
flags:

- `highlight`, `editable` — file-level support in the browser.
- `execution.supported` — whether a tested isolated runtime exists (false for
  every language today).
- `execution.enabled_by_default` — false everywhere.

The UI must never imply that a file being writable means it can be executed.

## 5. Security limitations (known)

- **No general API rate limiting.** The run queue caps concurrent experiments, but
  project and upload routes are not rate-limited. Put the API behind a reverse
  proxy with request limits in production.
- **Single worker.** Run state is tracked in-process, so `--workers 1` is
  required for experiment execution.
- **Collaborators** exist in the schema and API authorization, but there is no
  invitation UI yet; membership is currently managed out-of-band.
- **Archive scanning.** ZIP imports are validated for traversal, size and symlinks
  but are not malware-scanned.
- **Local identity is not authentication.** `QUANTHUB_TRUST_CLIENT_IDENTITY=1`
  is honoured only when `QUANTHUB_ENV` is `development` or `test`; startup fails
  otherwise, and with `QUANTHUB_ENV` unset the headers are ignored. A server in
  that state is read-only: `GET /api/v1/me` reports
  `capabilities.local_sessions = false`, the web app disables writes and
  explains the remedy, and any write still returns `401`. Use
  `scripts/dev-api.sh` for local work.
- **Firebase verification needs `firebase-admin` and a project id.** The SDK is a
  declared dependency; if it or `FIREBASE_PROJECT_ID` is missing, bearer tokens
  are rejected with `401` (fail closed) rather than treated as valid.
- **Unhandled errors are opaque.** Clients receive a `500` with a generic message
  and a short correlation reference; the traceback is logged server-side only.
- **No content moderation or abuse reporting** for public projects.
- **Firestore rules** cover profile documents; project metadata lives in SQLite,
  so its authorization is entirely server-side.
- **Artifacts are retained indefinitely.** There is no retention policy or quota
  enforcement beyond per-request limits.

## 6. Operational notes

- Back up `QUANTHUB_DATA_DIR`: it holds the database, the bare repositories and
  every run's evidence.
- The repository layout is append-only for runs; deleting a project archives it
  instead of deleting data.
- `GET /api/v1/dashboard` reads projects, runs and activity from one connection;
  the earlier nested-connection call was removed to avoid SQLite lock contention.

## 7. Unresolved

- The documentation previously referenced `/api/v2/hub` in planning notes; the
  implemented prefix is `/api/v1` for all QuantHub routes, with `/api/v2` retained
  for the simulator. Any external notes should be corrected to `/api/v1`.
- No automated browser test suite (Playwright) is present. Frontend verification
  is TypeScript, unit tests and a production build.
