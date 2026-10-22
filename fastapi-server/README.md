# quantumlab-api (fastapi-server)

QuantHub REST API and the JSON-over-HTTP bridge between the web/desktop client and
the [`quantumlab`](../quantum-simulator-core) Python engine.

The server runs on **localhost:8765** by default. Every route returns:

```json
{ "data": { }, "error": null }
```

Failures carry a code and message, and use real HTTP status codes:

```json
{ "data": null, "error": { "code": "RevisionConflict", "message": "…", "details": { } } }
```

## QuantHub routes (`/api/v1`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/me` | Current identity |
| `GET` | `/dashboard` | Projects, recent runs, activity, tools, news |
| `GET`/`POST` | `/projects` | List (discover/mine/starred) or create |
| `GET` | `/projects/templates` | Licenses, `.gitignore` templates, language registry |
| `GET`/`PATCH`/`DELETE` | `/projects/{owner}/{slug}` | Detail / update / archive |
| `POST` | `/projects/{owner}/{slug}/star` \| `/watch` | Star / watch |
| `GET` | `/projects/{owner}/{slug}/tree` \| `/blob` \| `/raw` | Browse and read |
| `PUT`/`DELETE` | `/projects/{owner}/{slug}/contents` | Commit a change / delete |
| `POST` | `/projects/{owner}/{slug}/contents/move` | Move or rename |
| `POST` | `/projects/{owner}/{slug}/upload` \| `/import/zip` | Multi-file and ZIP import |
| `GET` | `/projects/{owner}/{slug}/archive` | ZIP export |
| `GET` | `/projects/{owner}/{slug}/commits` \| `/activity` | History and activity |
| `GET`/`POST` | `/projects/{owner}/{slug}/experiments` | List / create specifications |
| `POST` | `/experiments/validate` | Validate a protocol with the real engine |
| `GET`/`PATCH`/`DELETE` | `/projects/{owner}/{slug}/experiments/{id}` | Spec CRUD |
| `POST` | `/projects/{owner}/{slug}/experiments/{id}/runs` | Start a run (202) |
| `GET` | `/projects/{owner}/{slug}/runs` \| `/runs/{run}` | Run list / detail |
| `POST` | `/projects/{owner}/{slug}/runs/{run}/cancel` \| `/verify` | Cancel / verify integrity |
| `GET` | `/projects/{owner}/{slug}/runs/{run}/claims` | Claim audit |
| `GET` | `/projects/{owner}/{slug}/runs/{run}/artifacts/{name}` \| `/bundle` \| `/export` | Downloads |
| `GET` | `/community/news` | Curated and/or live verified news |
| `GET` | `/capabilities/qec` \| `/capabilities/languages` | Engine and file-support capabilities |

Historical simulator routes are unchanged: `/api/v1/health`,
`/api/v1/circuit/*`, `/api/v1/visualize/*`, `/api/v1/explain`, `/api/v2/*`,
`/api/v2/editor/*`.

## Identity

- **Firebase** — `Authorization: Bearer <id token>`; verified server-side with
  the Firebase Admin SDK against `FIREBASE_PROJECT_ID` (canonical; also
  `GOOGLE_CLOUD_PROJECT`, deprecated `QUANTHUB_FIREBASE_PROJECT`). Failures are a
  single opaque `401`, and the token's `uid` is the identity used for ownership.
- **Local development** — `X-QuantHub-User`, `X-QuantHub-Name`, `X-QuantHub-Email`.
  Accepted only when `QUANTHUB_ENV=development|test` **and**
  `QUANTHUB_TRUST_CLIENT_IDENTITY=1`. With `QUANTHUB_ENV` unset or in
  production the headers are ignored and the caller is a guest. This is not
  authentication and must not be enabled on a public deployment.
- Startup validates the configuration: production requires a project id and an
  importable `firebase-admin`; enabling identity headers outside development is
  a startup error.

## Experiment execution

Experiments are validated by `quantumlab.research.qec.protocol` and executed in a
separate process:

```
setsid /bin/sh -c 'ulimit -t <cpu>; ulimit -v 2097152; ulimit -n 512; exec python -m quantumlab.research.qec run …'
```

The environment is scrubbed, output is captured to a per-run log, and cancellation
escalates from `SIGTERM` to `SIGKILL`. Run state is tracked in-process, so run the
API with `--workers 1`.

## Configuration

See the root [`README.md`](../README.md#server-environment) for the full table.
The essentials:

```bash
QUANTHUB_ENV=development                # development | test | production
QUANTHUB_DATA_DIR=./.quanthub-data     # database, repositories, artifacts
QUANTHUB_TRUST_CLIENT_IDENTITY=1       # development only (needs QUANTHUB_ENV)
QUANTHUB_MAX_CONCURRENT_RUNS=2
QUANTHUB_RUN_TIMEOUT_SECONDS=900
CORS_ORIGINS=http://127.0.0.1:5173
FIREBASE_PROJECT_ID=                   # backend token verification; required in production
```

LLM/Wolfram keys are optional and only affect the explanation and research
assistance features, never project hosting or experiment execution.

## Local development

```bash
# from repository root
python -m pip install -e quantum-simulator-core
python -m pip install -e "fastapi-server[dev]"

# Sets QUANTHUB_ENV=development and QUANTHUB_TRUST_CLIENT_IDENTITY=1, which the
# local session requires. A bare `uvicorn app.main:app` runs read-only.
./scripts/dev-api.sh
```

Open <http://127.0.0.1:8765/docs> for the OpenAPI UI.

## Tests

```bash
cd fastapi-server
python -m pytest -q
```

The suite covers project creation, import safety, revision conflicts, private
project authorization, experiment validation, real engine runs, cancellation,
artifact verification and the news feed.

## License

MIT
