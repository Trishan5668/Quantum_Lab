# QuantHub

> A project-centric platform for quantum software, experiments and reproducible research.

QuantHub is built on the QuantumLab simulation engine. It keeps the existing
state-vector simulator, density-matrix engine, noise models, circuit designer,
math derivations and QEC research code, and wraps them in a GitHub-style
workspace where a **project** is the unit of work:

- **Projects** — files, a README, topics, license, visibility and real revision
  history, backed by Git repositories on the server.
- **Experiments** — declared protocols that are validated and executed by the
  Python QEC engine, never re-implemented in the browser.
- **Runs** — immutable evidence directories with config, provenance,
  environment, records, summary, report, manifest and checksums.
- **Discovery** — public projects, topics, search and a verified community news
  feed.

Everything above works without an account, an API key or a subscription. AI
assistance remains available as an optional, clearly separate feature.

---

## Status

| Area | State |
| --- | --- |
| Project hosting, import/export, editing, revision checks | Implemented and covered by API tests |
| Authentication (Firebase bearer tokens + explicit local dev identity) | Implemented |
| Private-project authorization | Enforced in the API and in `firestore.rules` |
| QEC experiment specs, sandboxed runs, artifacts, verification | Implemented; real engine runs verified |
| QEC Workbench UI (Configuration / Execution / Results / Scaling / Artifacts / Validation) | Implemented |
| Circuit Designer (state-vector, density matrix, noise, step-through) | Preserved from v1/v2 |
| Community news | Curated, individually verified snapshot; optionally live RSS when configured |
| Code execution in the API process | **Disabled by design** — experiments run in a separate, resource-limited process |

A project's file support is *not* an execution capability. The language registry
documents storage, browsing, editing and highlighting separately from execution,
and every language is marked as non-executable by default.

---

## Monorepo layout

| Folder | Package | Purpose |
| --- | --- | --- |
| `quantum-simulator-core/` | `quantumlab` (Python) | Pure NumPy state-vector + density-matrix engine, QEC research package. MIT. |
| `fastapi-server/` | `quantumlab-api` | QuantHub REST API, project hosting, experiment runner, simulator routes. MIT. |
| `quantum-desktop-app/` | Electron + React + TypeScript | QuantHub web app and desktop shell. MIT. |
| `quantum-education-content/` | content | Lessons and explanations. CC-BY-SA 4.0. |

The Python distribution, import package and npm workspaces keep their existing
names (`quantumlab`, `quantumlab-api`, `@quantumlab/*`) so existing installs,
imports and deployments continue to work.

---

## Quickstart

Requires Python 3.11+ and Node 20+.

```bash
# 1. Install the engine and the API
python -m pip install -e quantum-simulator-core
python -m pip install -e "fastapi-server[dev]"

# 2. Start the API (terminal 1) — http://127.0.0.1:8765
#    QUANTHUB_ENV opts into the labelled local session; see "Local identity".
cd fastapi-server
QUANTHUB_ENV=development QUANTHUB_TRUST_CLIENT_IDENTITY=1 \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# 3. Start the web app (terminal 2) — http://127.0.0.1:5173
cd quantum-desktop-app/packages/webapp
npm install
npm run dev

# 4. Optional: Electron desktop shell (terminal 3)
cd quantum-desktop-app/packages/desktop
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The web app proxies `/api` to
`http://127.0.0.1:8765` in development (`VITE_API_PROXY` overrides the target).

To populate an empty instance with a few real projects, files and one finished
run (all created through the public API):

```bash
scripts/dev-seed.sh                      # against http://127.0.0.1:8765
QUANTHUB_SEED_HANDLE=you scripts/dev-seed.sh
```

### Local identity

With no Firebase configuration the UI runs a clearly labelled **local session**.
The handle is stored in `localStorage` and sent as `X-QuantHub-User`. The server
accepts those headers only when **both** `QUANTHUB_ENV=development` (or `test`)
and `QUANTHUB_TRUST_CLIENT_IDENTITY=1` are set. This is a development
convenience and **not** an authentication mechanism: any client could claim any
identity, which is why it cannot be enabled outside a development environment.

The server has exactly three identity modes, reported by `GET /api/v1/me` as
`mode`: `guest` (no credentials), `local` (trusted development headers) and
`authenticated` (a verified Firebase ID token). The same rules apply to every
private-project route; there is no per-route bypass.

```bash
# Development only: trust client-supplied identity headers
QUANTHUB_ENV=development \
QUANTHUB_TRUST_CLIENT_IDENTITY=1 \
QUANTHUB_DATA_DIR=./.quanthub-data \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

With Firebase configured, the web app sends a verified ID token as
`Authorization: Bearer …` and the server verifies it with the Firebase Admin SDK
(`firebase-admin`, a declared dependency). Verification failures always return a
single opaque `401`; the token, its claims and any traceback stay server-side.
The project's stable identity is the token subject (`uid`), and it is the key
used for project ownership.

### Deployment environment

| `QUANTHUB_ENV` | Identity headers | Startup checks |
| --- | --- | --- |
| `development` | allowed when `QUANTHUB_TRUST_CLIENT_IDENTITY=1` | none |
| `test` | allowed when `QUANTHUB_TRUST_CLIENT_IDENTITY=1` | none |
| `production` | always ignored | fails without `FIREBASE_PROJECT_ID`; fails if identity headers are enabled |
| unset | always ignored | logs a warning (treated as non-development) |
| anything else | always ignored | startup fails with an actionable error |

Configuration is validated once while the app is built, so a misconfigured
deployment refuses to start instead of silently falling back to unverified
identities. Unknown values for `QUANTHUB_TRUST_CLIENT_IDENTITY` (for example
`yes-please`) are an error, not a truthy default.

### Server environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `QUANTHUB_ENV` | unset (`unspecified`) | `development` / `test` / `production`; gates every security check |
| `QUANTHUB_DATA_DIR` | `<repo>/.quanthub-data` | SQLite database, Git repositories, run artifacts |
| `QUANTHUB_DB_PATH` | `<data>/quanthub.sqlite3` | Override the database location |
| `QUANTHUB_TRUST_CLIENT_IDENTITY` | off | Accept `X-QuantHub-*` headers (requires dev/test) |
| `QUANTHUB_RUN_TIMEOUT_SECONDS` | 900 | Hard CPU-time limit per experiment run |
| `QUANTHUB_MAX_CONCURRENT_RUNS` | 2 | Parallel engine processes |
| `QUANTHUB_NEWS_FEEDS` | empty | Comma-separated RSS/Atom URLs for the live feed |
| `QUANTHUB_NEWS_TTL_SECONDS` | 900 | Live-feed cache lifetime |
| `FIREBASE_PROJECT_ID` | unset | Canonical backend project id; required in production |
| `GOOGLE_CLOUD_PROJECT` | unset | Fallback for `FIREBASE_PROJECT_ID` |
| `QUANTHUB_FIREBASE_PROJECT` | unset | Deprecated alias (logs a warning) |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Allowed browser origins |

`VITE_*` variables are consumed by the browser bundle only. The API never reads
them, so a `VITE_FIREBASE_PROJECT_ID` alone does not enable server-side token
verification.

### Database lifecycle

The runtime SQLite database is derived state and is **not** tracked in Git
(`.quanthub-data/` is ignored). It is created on first start and upgraded
through ordered, additive migrations recorded in `schema_meta.schema_version`.
Initialisation takes an immediate write lock, so several workers starting at
once serialise instead of racing; a database written by a *newer* release is
refused rather than silently downgraded, and a pre-versioning database is
upgraded in place without dropping rows.

Run artifacts and repositories are written under the data directory. Nothing is
executed inside the API process; each run is launched with
`python -m quantumlab.research.qec run …` inside a restricted subprocess.

---

## Product concepts

### Projects

A project has a name, slug, description, owner, topics, visibility and an
optional SPDX license. Creating one initializes a real Git repository with an
optional README, `.gitignore` template and license file, and records an initial
commit. Importing files (multi-file, folder or ZIP) commits them as a new
revision; local Git history is not transferred, and the API reports this
explicitly.

Editing a file requires the revision the editor started from. A stale revision
returns `RevisionConflict` rather than overwriting someone else's work.

### Experiments and runs

An experiment specification stores a validated protocol plus its config hash.
Starting a run snapshots the protocol and executes it in a separate process:

```
<artifacts>/<run_id>/
  config.json  provenance.json  environment.json  summary.json
  manifest.json  checksums.sha256  records.jsonl  report.md
```

The UI distinguishes these states and never advances them automatically:

1. **Configuration validated** — the engine accepted the schema and decoders.
2. **Execution complete** — the engine exited successfully and wrote artifacts.
3. **Integrity verified** — checksums and manifest match the bytes on disk.
4. **Reference comparison** — not automated.
5. **Published reproduction** — requires a published reference.
6. **Independent reproduction** — requires a third party.
7. **Peer review** — external to QuantHub.

QuantHub does not recompute scientific numbers in TypeScript and does not
estimate thresholds. The Scaling tab shows engine-produced series only; when a
run has a single configuration it says so.

---

## API

All QuantHub routes are versioned under `/api/v1` and return:

```json
{ "data": { }, "error": null }
```

Failures carry a stable code and message:

```json
{ "data": null, "error": { "code": "RevisionConflict", "message": "…", "details": { } } }
```

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/me` | Current identity and project count |
| `GET` | `/api/v1/dashboard` | Projects, runs, activity, tools and news |
| `GET` | `/api/v1/projects` | Discover / mine / starred, with search, topic, language and sort |
| `POST` | `/api/v1/projects` | Create a project (README, `.gitignore`, license) |
| `GET` | `/api/v1/projects/templates` | License, `.gitignore` and language options |
| `GET` | `/api/v1/projects/{owner}/{slug}` | Project detail, README, tree, commits, experiments |
| `PATCH`/`DELETE` | `/api/v1/projects/{owner}/{slug}` | Update settings / archive |
| `POST` | `/api/v1/projects/{owner}/{slug}/star` \| `/watch` | Star / watch |
| `GET` | `/api/v1/projects/{owner}/{slug}/tree` \| `/blob` \| `/raw` | Browse and read files |
| `PUT`/`DELETE` | `/api/v1/projects/{owner}/{slug}/contents` | Commit a file change / delete |
| `POST` | `/api/v1/projects/{owner}/{slug}/contents/move` | Move or rename |
| `POST` | `/api/v1/projects/{owner}/{slug}/upload` \| `/import/zip` | Multi-file and archive import |
| `GET` | `/api/v1/projects/{owner}/{slug}/archive` | Download the project as ZIP |
| `GET` | `/api/v1/projects/{owner}/{slug}/commits` | Revision history |
| `GET`/`POST` | `/api/v1/projects/{owner}/{slug}/experiments` | List / create specifications |
| `POST` | `/api/v1/projects/{owner}/{slug}/experiments/{id}/runs` | Start a run |
| `GET` | `/api/v1/projects/{owner}/{slug}/runs/{run}` | Status, results, artifacts, manifest |
| `POST` | `/api/v1/projects/{owner}/{slug}/runs/{run}/cancel` \| `/verify` | Cancel / verify integrity |
| `GET` | `/api/v1/projects/{owner}/{slug}/runs/{run}/claims` | Claim audit |
| `GET` | `/api/v1/projects/{owner}/{slug}/runs/{run}/bundle` | Reproduction bundle (ZIP) |
| `GET` | `/api/v1/community/news` | Curated and/or live verified news |
| `GET` | `/api/v1/capabilities/qec` | Engine, decoder and code-family capabilities |
| `GET` | `/api/v1/capabilities/languages` | Language registry (file vs execution support) |

The historical simulator endpoints (`/api/v1/circuit/*`, `/api/v1/visualize/*`,
`/api/v1/explain`, `/api/v2/*`, `/api/v2/editor/*`) are unchanged. Interactive
API documentation is served at `/docs`.

---

## Architecture

```
Browser / Electron shell
        │  React + TypeScript (Vite dev server proxies /api)
        ▼
FastAPI (quantumlab-api)
   ├── /api/v1, /api/v2 simulator routes ──► quantumlab core (in-process, NumPy)
   ├── /api/v1 QuantHub routes ──► SQLite metadata
   │                              ├── bare Git repositories (files, history)
   │                              └── run artifacts on disk
   └── experiment runner ──► subprocess: python -m quantumlab.research.qec run
                             (setsid, ulimit, scrubbed env, timeout)
```

- Electron ↔ web app: `contextBridge` only; no `nodeIntegration`.
- The API never executes user code in-process.
- Run processes are launched with a CPU/memory/file-descriptor limit, a scrubbed
  environment and a hard timeout; cancellation escalates from `SIGTERM` to
  `SIGKILL`.
- In-process run registries mean the API must run with `--workers 1`.

---

## Security model

- **Authorization is server-side.** Private projects return `403` to other
  identities and are excluded from public listings. Firestore rules mirror the
  same rule for profile data.
- **Path safety.** Imported paths reject absolute paths, `.`/`..` segments,
  control characters and overlong components before any write.
- **Archive handling.** ZIP imports cap entry count, uncompressed size and depth,
  and reject symlinks and unsafe names.
- **Upload limits.** 5 MB per file, 64 MB per upload, 2,000 files, 2,000 archive
  entries, 256 MB uncompressed.
- **Markdown is sanitized** with DOMPurify using an allowlist; links open in a new
  tab with `rel="noopener noreferrer nofollow"`.
- **Secrets never reach the browser bundle** or the logs; LLM and Wolfram keys are
  server-side only.

Known limitations are documented in [`docs/QUANTHUB.md`](docs/QUANTHUB.md)
(rate limiting, multi-worker runs, collaborator management, antivirus scanning
of archives and data residency).

---

## Tests

Commands actually executed for this revision:

```bash
# Python engine
cd quantum-simulator-core && python -m pytest -q
# → 325 passed, 3 skipped

# API, including QuantHub suites
cd fastapi-server && python -m pytest -q
# → 140 passed

# Lint (from repository root)
python -m ruff check fastapi-server/app fastapi-server/tests
# → All checks passed!

# Frontend
cd quantum-desktop-app/packages/webapp
npx tsc --noEmit          # clean
npm test -- --run         # 13 passed
npm run build             # succeeds
```

`npm run build` uses a 4 GB Node heap because the existing Plotly chart chunk is
large; the flag is set in the script so the command works on a default machine.

---

## Deployment

### Backend

Deploy `fastapi-server/` with:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Set `QUANTHUB_ENV=production`, `FIREBASE_PROJECT_ID=<your project>` and
`CORS_ORIGINS` to the deployed frontend origin, and mount persistent storage for
`QUANTHUB_DATA_DIR`. Leave `QUANTHUB_TRUST_CLIENT_IDENTITY` unset: startup fails
in production if unverified identity headers are enabled or the project id is
missing. The run registry is in-process, so a single worker is required for
experiment execution.

### Frontend

Build `quantum-desktop-app/packages/webapp` with Vite (`npm run build`, output
`dist`) and set `VITE_API_URL` to the backend origin when the frontend and API
are on different hosts. If `VITE_API_URL` is unset, the app uses same-origin
`/api/v1`, which requires a reverse proxy in front of the API.

---

## Historical v1/v2 status

- **v2** — density-matrix simulation, noise channels, fidelity/entropy/purity
  metrics, API v2 routes and matching panels. All preserved.
- **v1** — drag-and-drop circuit builder, step-through simulation, state vector,
  Bloch spheres, density heatmap, measurement probabilities, PNG export and
  optional explanations. All preserved.

---

## Project rules

- No silent fallbacks: failures raise typed exceptions.
- No mocked quantum math: gate matrices are exact `complex128` values.
- No fabricated results, news or validation states.
- No AI requirement for core functionality.
- Atomic, present-tense commits.

## Creator

Trishan Ghosh — <ghoshtg17@gmail.com> — <https://instagram.com/trishan_5668/>

## License

- `quantum-simulator-core`, `fastapi-server`, `quantum-desktop-app`: MIT.
- `quantum-education-content`: CC-BY-SA 4.0.
