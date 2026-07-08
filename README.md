# QuantumLab

> An open-source, AI-native quantum circuit simulator.
> Built for university students, self-taught hackers, and early-career quantum engineers.

QuantumLab is a four-repository monorepo:

| Folder                       | Package                | Purpose                                                                        |
| ---------------------------- | ---------------------- | ------------------------------------------------------------------------------ |
| `quantum-simulator-core/`    | `quantumlab` (Python)  | Pure NumPy quantum state-vector simulator. MIT.                                |
| `fastapi-server/`            | `quantumlab-api`       | JSON-over-HTTP bridge with SSE streaming AI explanations. MIT.                 |
| `quantum-desktop-app/`       | Electron + React + TS  | Dark IDE-style circuit builder UI. MIT.                                        |
| `quantum-education-content/` | (content)              | Missions, hints, curricula. Loaded at runtime by the desktop app. CC-BY-SA 4.0.|

---

## v2 status

QuantumLab v2 adds mixed-state simulation and educational metrics while keeping v1 behavior as the default:

- [x] **Density matrix engine** — ρ evolution via UρU† (`quantumlab/density.py`)
- [x] **Noise channels** — amplitude/phase damping, depolarizing, bit/phase flip, T1/T2 preset
- [x] **Metrics** — fidelity (pure & Uhlmann), entanglement entropy, purity
- [x] **API v2** — `/api/v2/circuit/run`, `/api/v2/metrics/{fidelity,entropy,purity}`
- [x] **UI** — Noise Settings panel, simulation mode toggle, Metrics panel
- [x] **Education** — density, noise, fidelity, entropy markdown docs; LLM prompt updates
- [x] **Backward compatible** — default statevector, no noise; all v1 tests pass

## v1 status

All v1 deliverables are shipped and live-verified end-to-end:

- [x] Drag-and-drop circuit builder with all 8 gate types (H, X, Y, Z, RX, RY, RZ, CNOT, plus M marker)
- [x] Step-through simulation mode
- [x] State vector panel with KaTeX basis kets and probability bars
- [x] Interactive Bloch sphere (Three.js, OrbitControls, slerp animation, one per qubit)
- [x] Density matrix heatmap (Re + Im, RdBu)
- [x] Measurement probability bar chart (Plotly)
- [x] ELI15 streaming explanation panel (SSE, Google Gemini `gemini-2.5-flash` with offline fallback)
- [x] Export circuit as PNG
- [x] Full test suite (58 Python tests for the quantum core, all passing; FastAPI integration tests; Vitest store tests)

The Bell state circuit produces probabilities `[0.5, 0, 0, 0.5]` exactly,
verified live in-browser against the Python engine through the FastAPI
bridge.

---

## Quickstart

Requires: Python 3.11+ and Node 20+.

```bash
# 1. Install the Python engine and the API server
python -m pip install -e quantum-simulator-core
python -m pip install -e "fastapi-server[dev]"

# 2. (optional) Enable cloud-backed ELI15 explanations
$env:LLM_PROVIDER  = "gemini"   # or "local" for offline deterministic explanations
$env:GEMINI_API_KEY = "AIza..."

# 3. Start the backend (terminal 1)
cd fastapi-server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# 4. Start the webapp (terminal 2)
cd quantum-desktop-app/packages/webapp
npm install
npm run dev

# 5. (optional) Launch as an Electron desktop app (terminal 3)
cd quantum-desktop-app/packages/desktop
npm install
QUANTUMLAB_NO_API=1 npm run dev
```

Open <http://127.0.0.1:5173> in a browser, or use the Electron window.

---

## Architecture

```
Electron shell  --renders-->  React webapp  --HTTP/SSE-->  FastAPI bridge  --Python import-->  quantumlab core
   no node                       (port 5173)                 (port 8765)                         (pure NumPy)
   contextBridge
```

- Electron ↔ Webapp: only `contextBridge`, no `nodeIntegration`.
- Webapp ↔ FastAPI: JSON over HTTP on `localhost:8765`; SSE for streaming AI.
- FastAPI ↔ core: direct in-process Python import — no subprocesses.
- Every API response is wrapped in `{ data, error }`. Errors use proper
  HTTP status codes — never a 200 with an error in the body.

## Project rules

These rules are enforced in code and in review:

- **No silent fallbacks.** Every failure raises a typed exception.
- **No mocked quantum math.** Gate matrices are exact, NumPy `complex128`.
- **No untyped Python.** `mypy --strict` passes on the core package.
- **No placeholder UI.** Every panel is functional in v1.
- **No Qiskit in the core.** Gate matrices are implemented from scratch.
- **Atomic, present-tense commits.** `Add H gate matrix computation`, not `stuff`.

## What's next

- **v3** — mission browser (Bell, teleportation, Grover, QFT, cavity coherence,
  threshold), star-based scoring, dynamic AI hints.

## License

- `quantum-simulator-core`, `fastapi-server`, `quantum-desktop-app`: MIT.
- `quantum-education-content`: CC-BY-SA 4.0.
