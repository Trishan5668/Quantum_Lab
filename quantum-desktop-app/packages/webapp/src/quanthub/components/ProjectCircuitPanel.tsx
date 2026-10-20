import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../client";
import type { BlobPayload, ProjectDetail, TreeEntry, TreePayload } from "../types";
import { useCircuitStore } from "../../store/circuitStore";

interface CircuitFile {
  schema_version: number;
  name: string;
  num_qubits: number;
  initial_basis_state?: string;
  selected_basis_state?: string;
  simulation_mode: string;
  noise_enabled: boolean;
  gates: Array<Record<string, unknown>>;
  saved_at: string;
  project?: string;
}

/**
 * Project-aware controls for the Circuit Designer.
 *
 * Circuits are stored as ordinary JSON files in the project, so they show up
 * in the file browser, follow the same revision checks as any other edit, and
 * can be diffed or exported like code.
 */
export function ProjectCircuitPanel(): JSX.Element | null {
  const [params] = useSearchParams();
  const fullName = params.get("project");
  const [owner, slug] = (fullName ?? "").split("/");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<TreeEntry[] | null>(null);

  if (!owner || !slug) return null;

  const base = `/projects/${owner}/${slug}`;

  async function loadFiles(): Promise<TreeEntry[]> {
    try {
      const tree = await api<TreePayload>(`${base}/tree?path=circuits`);
      return tree.entries.filter((entry) => entry.type === "blob" && entry.name.endsWith(".json"));
    } catch {
      // A project without a circuits/ directory is a normal, empty state.
      return [];
    }
  }

  async function save(): Promise<void> {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const project = await api<ProjectDetail>(base);
      if (!project.viewer.can_write) {
        throw new ApiError(403, "Forbidden", "You do not have write access to this project.");
      }
      const state = useCircuitStore.getState();
      const payload: CircuitFile = {
        schema_version: 1,
        name: "circuit",
        num_qubits: state.numQubits,
        initial_basis_state: state.initialBasisState,
        selected_basis_state: state.selectedBasisState,
        simulation_mode: state.simulationMode,
        noise_enabled: state.noiseEnabled,
        gates: state.gates as unknown as Array<Record<string, unknown>>,
        saved_at: new Date().toISOString(),
        project: `${owner}/${slug}`,
      };
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      const path = `circuits/circuit-${stamp}.json`;
      await api(`${base}/contents`, {
        method: "PUT",
        body: {
          path,
          content: JSON.stringify(payload, null, 2),
          message: `Save circuit (${state.numQubits} qubits, ${state.gates.length} gates)`,
          expected_revision: project.revision,
        },
      });
      setStatus(`Saved to ${path}`);
      setFiles(null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The circuit could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function load(path: string): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const blob = await api<BlobPayload>(`${base}/blob?path=${encodeURIComponent(path)}`);
      if (!blob.content) throw new Error("That circuit file is empty or binary.");
      const parsed = JSON.parse(blob.content) as CircuitFile;
      if (!Array.isArray(parsed.gates) || typeof parsed.num_qubits !== "number") {
        throw new Error("That file is not a QuantHub circuit.");
      }
      useCircuitStore.getState().loadSavedCircuit({
        numQubits: parsed.num_qubits,
        initialBasisState: parsed.initial_basis_state,
        selectedBasisState: parsed.selected_basis_state,
        gates: parsed.gates as never,
        simulationMode: parsed.simulation_mode as never,
        results: null,
        resultsV2: null,
        noiseEnabled: Boolean(parsed.noise_enabled),
      });
      setStatus(`Loaded ${path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The circuit could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-b border-border/70 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-display text-[10px] uppercase tracking-[0.18em] text-text-muted">
          Project
        </p>
        <Link to={`/${owner}/${slug}`} className="truncate text-xs text-accent-glow hover:underline">
          {owner}/{slug}
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-bg-elevated disabled:opacity-50"
          onClick={() => void save()}
          disabled={busy}
        >
          {busy ? "Working…" : "Save circuit to project"}
        </button>
        <button
          type="button"
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-bg-elevated disabled:opacity-50"
          onClick={() => {
            setBusy(true);
            setError(null);
            loadFiles()
              .then((next) => setFiles(next))
              .catch((cause: unknown) =>
                setError(cause instanceof Error ? cause.message : "Could not list circuits."),
              )
              .finally(() => setBusy(false));
          }}
          disabled={busy}
        >
          Load from project
        </button>
      </div>
      {files && files.length === 0 && (
        <p className="mt-2 text-[11px] text-text-muted">No saved circuits in this project yet.</p>
      )}
      {files && files.length > 0 && (
        <ul className="mt-2 max-h-32 list-none space-y-1 overflow-auto p-0 text-[11px]">
          {files.map((file) => (
            <li key={file.path}>
              <button
                type="button"
                className="truncate text-accent-glow hover:underline"
                onClick={() => void load(file.path)}
              >
                {file.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {status && <p className="mt-2 text-[11px] text-emerald-400">{status}</p>}
      {error && <p className="mt-2 text-[11px] text-red-400">{error}</p>}
      <p className="mt-2 text-[10px] leading-snug text-text-muted">
        Circuits are stored as JSON files and committed with the same revision checks as code.
      </p>
    </div>
  );
}
