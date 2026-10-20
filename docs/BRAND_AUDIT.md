# Legacy identifier audit (QuantumLab → QuantHub)

Date: 2026-10-20. This audit lists what was renamed, what was deliberately kept,
and how to find remaining legacy references.

## Renamed (user-facing)

| Surface | Before | After |
| --- | --- | --- |
| Web app title, meta, JSON-LD | QuantumLab | QuantHub |
| Desktop `productName` / window title | QuantumLab | QuantHub |
| API title and OpenAPI description | QuantumLab API | QuantHub API |
| Platform navigation and footer | QuantumLab | QuantHub |
| Page metadata helper | QuantumLab | QuantHub |
| Education content prose | QuantumLab V1/V2 | QuantHub V1/V2 |
| LLM prompt context header | Current QuantumLab context | Current QuantHub context |
| Repository-wide `.gitignore` banner | QuantumLab | QuantHub |

The web app additionally gained a new top-level workspace (home dashboard,
projects, experiments, QEC workbench, community) that never mentions the old
name.

## Deliberately preserved

| Identifier | Reason |
| --- | --- |
| Python package `quantumlab`, module imports | Published distribution and import path; renaming breaks installs |
| npm workspaces `@quantumlab/webapp`, `@quantumlab/desktop` | Workspace coordinates in lockfiles and packaging |
| `QuantumLabError` and subclasses | Public exception API used by downstream code and tests |
| `QuantumLabUser` TypeScript interface | Firestore document shape shared with existing user data |
| `QuantumLab_Mathematical_Foundations.md/.pdf` | Referenced asset filenames |
| Electron `appId: io.quantumlab.desktop` | Changing it would orphan existing installs and settings |
| `QUANTUMLAB_*` environment variables already in deployments | Compatibility; new `QUANTHUB_*` variables are additive |
| Deployed URLs (`*.onrender.com`, Vercel project) and repository URLs | No replacement destination exists |
| Per-component `LICENSE` holders | Copyright attribution must not be edited |
| `quantum-simulator-core/research/qec/**` raw artifacts | Historical evidence must remain byte-identical |
| Firestore collection names | Existing user data |

## How to re-run the audit

```bash
# Any remaining camel-case product references
grep -rn "QuantumLab" --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=dist --exclude-dir=__pycache__ .

# Engine-only references (expected: package, engine name, exceptions)
grep -rn "quantumlab" --include="*.py" --include="*.toml" quantum-simulator-core | head
```

The remaining `QuantumLab` occurrences are confined to: the engine's own package
name and exception classes, per-component license files, historical research
artifacts, and two docstrings that refer to the QuantumLab engine (which is still
the engine's name).
