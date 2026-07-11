export interface DocArticle {
  slug: string;
  title: string;
  category: string;
  summary: string;
  content: string;
}

export const DOC_CATEGORIES = [
  { id: "getting-started", label: "Getting Started" },
  { id: "architecture", label: "Architecture" },
  { id: "quantum-theory", label: "Quantum Theory" },
  { id: "simulation", label: "Simulation Engine" },
  { id: "api", label: "API Reference" },
  { id: "frontend", label: "Frontend" },
] as const;

export const DOC_ARTICLES: DocArticle[] = [
  {
    slug: "installation",
    title: "Installation",
    category: "getting-started",
    summary: "Install Python core, FastAPI server, and the React web application.",
    content: `## Requirements

Python 3.11+, Node.js 20+.

## Python packages

\`\`\`bash
python -m pip install -e quantum-simulator-core
python -m pip install -e "fastapi-server[dev]"
\`\`\`

## Web application

\`\`\`bash
cd quantum-desktop-app/packages/webapp
npm install
npm run dev
\`\`\`

Open the Vite dev server URL for the platform, or append \`/app\` for the simulator.

## Desktop (optional)

\`\`\`bash
cd quantum-desktop-app/packages/desktop
npm install
npm run dev
\`\`\``,
  },
  {
    slug: "architecture",
    title: "Platform Architecture",
    category: "architecture",
    summary: "System layout: core engine, API bridge, React platform, education content.",
    content: `## Packages

| Package | Role |
|---------|------|
| \`quantum-simulator-core\` | NumPy state-vector and density-matrix engine |
| \`fastapi-server\` | HTTP/SSE API bridge |
| \`quantum-desktop-app\` | Electron + React platform UI |
| \`quantum-education-content\` | CC-BY-SA learning materials |

## Data flow

Browser/Electron → React UI → FastAPI → quantumlab Python core

## API versions

- **v1** — statevector simulation (default, backward compatible)
- **v2** — density matrices, noise, fidelity, entropy metrics`,
  },
  {
    slug: "state-vectors",
    title: "State Vectors",
    category: "quantum-theory",
    summary: "Pure states as complex amplitude vectors in Hilbert space.",
    content: `An n-qubit pure state is a unit vector |ψ⟩ in ℂ^(2ⁿ).

QuantumLab uses **big-endian** indexing: qubit 0 is the most significant bit in the basis label |q₀q₁…⟩.

The simulator normalizes after every gate and reports measurement probabilities |aᵢ|².`,
  },
  {
    slug: "density-matrices",
    title: "Density Matrices",
    category: "quantum-theory",
    summary: "Mixed states, decoherence, and the ρ formalism.",
    content: `A density matrix ρ is a positive semidefinite, trace-1 operator describing mixed and pure states.

- **Pure state:** ρ = |ψ⟩⟨ψ|
- **Purity:** Tr(ρ²) — equals 1 for pure states, < 1 for mixed
- **Evolution:** ρ → UρU†

Enable density mode in the simulator or apply noise channels to automatically use the v2 engine.`,
  },
  {
    slug: "simulation-engine",
    title: "Simulation Engine",
    category: "simulation",
    summary: "Gate application, noise channels, and metrics in quantumlab.",
    content: `## Modes

- **Statevector** — default, pure states, all v1 gates
- **Density** — mixed states via ρ evolution

## Noise (v2)

Kraus channels: amplitude/phase damping, depolarizing, bit/phase flip, T1/T2 preset.

## Metrics

Fidelity (pure & Uhlmann), von Neumann entanglement entropy, purity.`,
  },
  {
    slug: "api-v1",
    title: "API v1",
    category: "api",
    summary: "Circuit run, step, visualize, and explain endpoints.",
    content: `Base URL: configured with \`VITE_API_URL\`.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Health check |
| POST | /api/v1/circuit/run | Run full circuit |
| POST | /api/v1/circuit/step | Step simulation |
| POST | /api/v1/visualize/bloch | Bloch coordinates |
| POST | /api/v1/visualize/density | Density heatmap data |
| POST | /api/v1/explain | SSE ELI15 stream |

Interactive OpenAPI docs: \`/docs\``,
  },
  {
    slug: "api-v2",
    title: "API v2",
    category: "api",
    summary: "Density simulation and metrics endpoints.",
    content: `| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v2/circuit/run | Run with density/noise options |
| POST | /api/v2/metrics/fidelity | State fidelity |
| POST | /api/v2/metrics/entropy | Entanglement entropy |
| POST | /api/v2/metrics/purity | Purity Tr(ρ²) |`,
  },
  {
    slug: "frontend",
    title: "Frontend",
    category: "frontend",
    summary: "React, Zustand, Tailwind, Three.js, Plotly — one shared codebase.",
    content: `The webapp uses:

- **React 18** + TypeScript strict
- **Zustand** for circuit state
- **@dnd-kit** for gate drag-and-drop
- **Three.js** Bloch sphere
- **Plotly** probability and density charts
- **react-router-dom** for platform routes

Electron and browser share the same components. The simulator lives at \`/app\`.`,
  },
];

export function getDoc(slug: string): DocArticle | undefined {
  return DOC_ARTICLES.find((d) => d.slug === slug);
}

export function getDocsByCategory(category: string): DocArticle[] {
  return DOC_ARTICLES.filter((d) => d.category === category);
}
