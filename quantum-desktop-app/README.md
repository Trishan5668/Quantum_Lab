# quantum-desktop-app

**The Electron + React frontend for QuantHub.**

A dark, IDE-style quantum circuit builder. Drag-and-drop gate palette,
live Bloch spheres rendered with Three.js, state-vector + probability
+ density-matrix visualizations rendered with Plotly, and a streaming
ELI15 AI explanation panel.

```
packages/
  webapp/        Vite + React 18 + TypeScript + Tailwind + Zustand + dnd-kit
                  + Three.js + Plotly. Runs standalone in any browser.
  desktop/       Electron shell. Uses contextBridge (no nodeIntegration).
                  Spawns the FastAPI backend on launch.
```

## Quickstart (development)

Open three terminals.

**Terminal 1 — backend (FastAPI + quantumlab core):**

```bash
python -m pip install -e quantum-simulator-core
python -m pip install -e fastapi-server
cd fastapi-server
# QUANTHUB_ENV opts into the labelled local session (identity headers).
QUANTHUB_ENV=development QUANTHUB_TRUST_CLIENT_IDENTITY=1 \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

**Terminal 2 — webapp:**

```bash
cd quantum-desktop-app/packages/webapp
npm install
npm run dev
```

Then open <http://127.0.0.1:5173>.

The webapp uses `VITE_API_URL` for all backend calls. Copy
`packages/webapp/.env.example` to `packages/webapp/.env` for local development.
In production, set `VITE_API_URL` to the deployed FastAPI service URL.

## Deploying the webapp

For Vercel, create the project from `quantum-desktop-app/packages/webapp`:

| Setting | Value |
| --- | --- |
| Framework preset | Vite |
| Install command | `npm install` |
| Build command | `npm run build` |
| Output directory | `dist` |

Set the Vercel environment variable:

```bash
VITE_API_URL=https://your-backend.example.com
```

Deploy the FastAPI app from `fastapi-server/` to Render, Railway, Fly.io, or a
similar host with:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `CORS_ORIGINS=https://your-vercel-app.vercel.app` on the FastAPI host so the
deployed browser app can call it.

Then set `QUANTHUB_ENV=production`, `FIREBASE_PROJECT_ID=<your Firebase project>`
and do **not** set `QUANTHUB_TRUST_CLIENT_IDENTITY`: production requires verified
Firebase tokens, and startup fails if the identity headers are enabled or the
project id is missing. `VITE_*` variables only configure the browser bundle.

Only `VITE_API_URL`, `QUANTHUB_ENV` and `FIREBASE_PROJECT_ID` differ between
local development and production.

**Terminal 3 (optional) — Electron shell:**

```bash
cd quantum-desktop-app/packages/desktop
npm install
QUANTUMLAB_NO_API=1 npm run dev   # the dev terminal already runs the API
```

## Tech stack

| Layer                  | Choice                          |
| ---------------------- | ------------------------------- |
| Desktop shell          | Electron 31, contextBridge      |
| Frontend               | React 18, TypeScript strict     |
| Styling                | Tailwind CSS 3, CSS variables   |
| Global state           | Zustand                         |
| Drag-and-drop          | @dnd-kit/core                   |
| 3D visualization       | Three.js r0.165                 |
| 2D charts              | Plotly.js (dist-min)            |
| LaTeX rendering        | KaTeX + react-katex             |
| API client             | Native fetch + SSE              |

## Design system

Dark only. CSS variables defined in `src/index.css`:

| Token             | Hex     | Use                                  |
| ----------------- | ------- | ------------------------------------ |
| `--bg-base`       | `#0a0b0f` | Window background                    |
| `--bg-surface`    | `#12141a` | Panels                               |
| `--bg-elevated`   | `#1c1f2a` | Drop zones, hover                    |
| `--accent-quantum`| `#7c3aed` | Primary violet                       |
| `--accent-glow`   | `#a78bfa` | Highlights                           |
| `--accent-measure`| `#06b6d4` | Measurement gates                    |
| `--accent-warn`   | `#f59e0b` | Noise / decoherence warnings (V2)    |

Typography: JetBrains Mono for display + math + gate labels, Inter for UI.

## License

MIT. The educational content lives separately in `quantum-education-content`
under CC-BY-SA 4.0.
