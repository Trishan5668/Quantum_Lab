import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api } from "../client";
import { useAsync } from "../hooks";
import type {
  DecoderInfo,
  ExperimentSpec,
  ExperimentTemplate,
  RunSummary,
} from "../types";
import { ExperimentBuilder } from "../components/ExperimentBuilder";
import { RunsTable } from "../components/RunsTable";
import { EmptyState, ErrorState, LoadingPanel } from "../components/ui";

interface ExperimentsPayload {
  experiments: ExperimentSpec[];
  templates: ExperimentTemplate[];
  runs: RunSummary[];
  capabilities: {
    engine: { available: boolean; error: string | null };
    stim?: boolean;
    ui_decoders?: DecoderInfo[];
    notice?: string;
  };
}

export default function ExperimentsPage({ projectName }: { projectName?: string }): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const base = `/projects/${owner}/${slug}`;
  const projectBase = `/${owner}/${slug}`;
  const state = useAsync(
    (signal) => api<ExperimentsPayload>(`${base}/experiments`, { signal }),
    [owner, slug],
  );

  const engine = state.data?.capabilities.engine;
  const busy = state.data?.runs.some((run) =>
    ["queued", "running", "cancelling"].includes(run.status),
  );

  return (
    <>
      <PageMeta
        title={`Experiments · ${owner}/${slug}`}
        description="Reproducible quantum error-correction experiments for this project."
      />
      <div className="qh-container py-6">
        <nav className="qh-muted mb-2 text-[12px]">
          <Link to={projectBase}>{owner}/{slug}</Link> / Experiments
        </nav>
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">Experiments</h1>
            <p className="qh-subtle m-0">
              {projectName ? `${projectName} · ` : ""}specifications executed by the Python QEC engine.
            </p>
          </div>
          <Link to={`/qec?project=${owner}/${slug}`} className="qh-btn qh-btn-primary">
            QEC Workbench
          </Link>
        </header>

        {state.loading && !state.data && <LoadingPanel rows={5} />}
        {state.error && <ErrorState message={state.error.message} onRetry={state.reload} />}

        {state.data && !engine?.available && (
          <div className="qh-form-error mb-4">
            The QEC engine is not importable on this server, so experiments cannot be validated or
            run. {engine?.error}
          </div>
        )}

        {state.data && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
            <div className="space-y-4">
              <div className="qh-card overflow-hidden">
                <div className="qh-card-header">
                  <h2 className="m-0 text-[14px] font-semibold">
                    Experiment specifications ({state.data.experiments.length})
                  </h2>
                  {busy && <span className="qh-badge qh-badge-accent">run in progress</span>}
                </div>
                {state.data.experiments.length === 0 ? (
                  <div className="qh-card-body">
                    <EmptyState
                      title="No experiment specifications"
                      description="Define a protocol to run the Python engine with recorded provenance and artifacts."
                    />
                  </div>
                ) : (
                  <table className="qh-data">
                    <thead>
                      <tr>
                        <th scope="col">Name</th>
                        <th scope="col">Config hash</th>
                        <th scope="col" className="text-right">Runs</th>
                        <th scope="col" className="text-right">Last run</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.data.experiments.map((spec) => (
                        <tr key={spec.id}>
                          <td>
                            <Link
                              to={`${projectBase}/experiments/${spec.id}`}
                              className="text-[#79c0ff]"
                            >
                              {spec.name}
                            </Link>
                            <div className="text-[11px] text-[#6e7681]">
                              {spec.description || spec.slug}
                            </div>
                          </td>
                          <td className="qh-mono text-[11px] text-[#8b949e]">
                            {spec.config_hash ? `${spec.config_hash.slice(0, 12)}…` : "—"}
                          </td>
                          <td className="text-right">{spec.run_count}</td>
                          <td className="text-right text-[11px] text-[#8b949e]">
                            {spec.last_status ?? "never"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="qh-card overflow-hidden">
                <div className="qh-card-header">
                  <h2 className="m-0 text-[14px] font-semibold">Recent runs</h2>
                  <Link to={`${projectBase}/runs`} className="text-[12px] text-[#79c0ff]">
                    View all
                  </Link>
                </div>
                <div className="p-3">
                  <RunsTable
                    runs={state.data.runs}
                    basePath={projectBase}
                    emptyTitle="No runs yet"
                    emptyDescription="Save an experiment and start a run to produce evidence."
                  />
                </div>
              </div>
            </div>

            <div className="qh-side-panel">
              <section>
                <h2 className="qh-side-title">Engine</h2>
                <ul className="m-0 list-none space-y-1 p-0 text-[12px] text-[#9198a1]">
                  <li>
                    Engine:{" "}
                    <span className={engine?.available ? "text-[#3fb950]" : "text-[#f85149]"}>
                      {engine?.available ? "importable" : "unavailable"}
                    </span>
                  </li>
                  <li>
                    Stim + PyMatching:{" "}
                    <span className={state.data.capabilities.stim ? "text-[#3fb950]" : "text-[#e3b341]"}>
                      {state.data.capabilities.stim ? "installed" : "not installed"}
                    </span>
                  </li>
                  <li>Decoders: {(state.data.capabilities.ui_decoders ?? []).map((item) => item.id).join(", ") || "—"}</li>
                </ul>
                {state.data.capabilities.notice && (
                  <p className="qh-help">{state.data.capabilities.notice}</p>
                )}
              </section>
              <section>
                <h2 className="qh-side-title">Execution model</h2>
                <p className="qh-help m-0">
                  Each run executes <span className="qh-mono">python -m quantumlab.research.qec run</span>{" "}
                  in a separate resource-limited process. QuantHub never executes user code inside
                  the API process and never recomputes scientific numbers in the browser.
                </p>
              </section>
            </div>
          </div>
        )}

        {state.data && engine?.available && (
          <div className="mt-4">
            <ExperimentBuilder
              basePath={base}
              templates={state.data.templates}
              onCreated={() => state.reload()}
            />
          </div>
        )}
      </div>
    </>
  );
}
