# Contributing to quantum-desktop-app

The desktop app is the public face of QuantumLab. UI changes need to feel
deliberate and stay inside the design system.

## House rules

- **TypeScript strict** is non-negotiable. Run `npm run typecheck` before
  every PR.
- **No placeholder UI.** Every panel, every button must do something
  real.
- **Dark only.** No light theme work in v1. Use the CSS variables in
  `src/index.css`, not raw hex codes.
- **No global state outside Zustand.** Don't add a Redux store, don't
  smuggle data through React Context except for ephemeral UI
  cross-cutting (theme provider, etc.).
- **No drag-drop library other than `@dnd-kit/core`.**

## Adding a new visualization panel

1. Create `src/components/Visualizations/MyPanel.tsx`.
2. Pull live state with `useCircuitStore(selectCurrentState)`.
3. Use Plotly for 2D charts and Three.js for 3D. Stick to the palette
   variables.
4. Add a unit test under `src/components/Visualizations/__tests__/`
   exercising one realistic state vector.

## Adding a new gate type

1. Add the matrix + tests in `quantum-simulator-core` first.
2. In `src/types.ts`, add the `GateType` literal and a `GATE_CATALOG`
   entry with KaTeX matrix.
3. In `fastapi-server/app/models.py`, add the gate to the
   `gate_type` Literal.
4. In `quantum-simulator-core/quantumlab/circuit.py`, register it in
   the appropriate gate dispatch dict.

## Style and commits

- One feature per PR.
- Present-tense commit messages: `Add T gate to palette`, not `more
  stuff`.
- Run `npm run typecheck && npm test` before pushing.
