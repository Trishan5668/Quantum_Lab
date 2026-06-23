# quantumlab-api (fastapi-server)

JSON-over-HTTP bridge between the QuantumLab desktop client and the
[`quantumlab`](../quantum-simulator-core) Python engine.

The server runs on **localhost:8765** by default. Every route returns
the envelope:

```json
{ "data": ..., "error": null | { "code": "...", "message": "...", "trace": null | "..." } }
```

Errors never sneak through with HTTP 200 — failure paths use proper
status codes (`400`, `422`, `500`, `503`).

## Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/health`             | Service + core version |
| `POST` | `/api/v1/circuit/run`        | Run a full circuit, return per-step + final state |
| `POST` | `/api/v1/circuit/step`       | Apply one gate to a caller-provided state |
| `POST` | `/api/v1/visualize/bloch`    | Bloch angles + vector + purity per qubit |
| `POST` | `/api/v1/visualize/density` | Density matrix real/imag parts |
| `POST` | `/api/v1/explain`            | SSE stream of ELI15 explanation tokens |

## LLM provider

The `/explain` endpoint is backed by a pluggable provider selected via
`LLM_PROVIDER`:

| `LLM_PROVIDER` | Backend                          | API key             |
| -------------- | -------------------------------- | ------------------- |
| `gemini`       | Google `gemini-2.5-flash` (default) | `GEMINI_API_KEY` |
| `local`        | Deterministic offline templates  | none                |

If `LLM_PROVIDER` is unset, the server defaults to `gemini` when
`GEMINI_API_KEY` is present, and otherwise falls back to `local` —
this guarantees `/explain` always works, even without an API key.

## Local dev

```powershell
# from repo root
python -m pip install -e quantum-simulator-core
python -m pip install -e "fastapi-server[dev]"

# pick a provider (optional; defaults are sane)
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "AIza..."

# run
cd fastapi-server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Then hit `http://127.0.0.1:8765/docs` for the auto-generated OpenAPI UI.

## Docker

```bash
docker build -t quantumlab-api -f fastapi-server/Dockerfile .
docker run --rm -p 8765:8765 \
  -e LLM_PROVIDER=gemini \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  quantumlab-api
```

## License

MIT
