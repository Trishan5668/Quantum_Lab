import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError, download, formatBytes, formatDate } from "../client";
import { useAsync, usePolling } from "../hooks";
import type {
  DecoderInfo,
  ExperimentSpec,
  ExperimentTemplate,
  ProjectList,
  QecCapabilities,
  RunDetail,
  RunSummary,
} from "../types";
import { ExperimentBuilder } from "../components/ExperimentBuilder";
import { ResultsView } from "../components/ResultsView";
import { RunsTable } from "../components/RunsTable";
import { EmptyState, ErrorState, LoadingPanel, RunStatusPill } from "../components/ui";

interface ExperimentsPayload {
  experiments: ExperimentSpec[];
  templates: ExperimentTemplate[];
  runs: RunSummary[];
  capabilities: QecCapabilities;
}

const TABS = ["configuration", "execution", "results", "scaling", "artifacts", "validation"] as const;
type Tab = (typeof TABS)[number];

const LABELS: Record<Tab, string> = {
  configuration: "Configuration",
  execution: "Execution",
  results: "Results",
  scaling: "Scaling",
  artifacts: "Artifacts",
  validation: "Validation",
};

interface VerificationReport {
  ok: boolean;
  errors: string[];
  warnings: string[];
  checked_files: number;
}

interface ClaimsReport {
  status: string;
  errors: string[];
  warnings: string[];
  shape?: string;
}

export default function QecWorkbenchPage(): JSX.Element {
  const [params, setParams] = useSearchParams();
  const selectedProject = params.get("project") ?? "";
  const [tab, setTab] = useState<Tab>("configuration");
  const [runId, setRunId] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationReport | null>(null);
  const [claims, setClaims] = useState<ClaimsReport | null>(null);

  const projects = useAsync(
    (signal) => api<ProjectList>("/projects?view=mine&per_page=60", { signal }),
    [],
  );
  const discover = useAsync(
    (signal) => api<ProjectList>("/projects?view=discover&per_page=30", { signal }),
    [],
  );
  const capabilities = useAsync(
    (signal) => api<QecCapabilities>("/capabilities/qec", { signal }),
    [],
  );

  const [owner, slug] = selectedProject.split("/");
  const base = owner && slug ? `/projects/${owner}/${slug}` : "";
  const experiments = useAsync(
    (signal) =>
      base
        ? api<ExperimentsPayload>(`${base}/experiments`, { signal })
        : Promise.resolve(null),
    [base],
  );

  const runDetail = useAsync(
    (signal) =>
      base && runId ? api<RunDetail>(`${base}/runs/${runId}`, { signal }) : Promise.resolve(null),
    [base, runId],
  );

  useEffect(() => {
    setRunId("");
    setTab("configuration");
    setVerification(null);
    setClaims(null);
  }, [selectedProject]);

  useEffect(() => {
    if (!runId && experiments.data?.runs.length) {
      setRunId(experiments.data.runs[0].id);
    }
  }, [experiments.data, runId]);

  const activeRuns = experiments.data?.runs.filter((run) =>
    ["queued", "running", "cancelling"].includes(run.status),
  ) ?? [];
  usePolling(activeRuns.length > 0 || runDetail.data?.status === "running", 2500, () => {
    experiments.reload();
    runDetail.reload();
  });

  const run = runDetail.data;
  const scaling = useMemo(() => {
    const summary = run?.summary as Record<string, unknown> | null | undefined;
    if (!summary) return [];
    const result = summary.result as Record<string, unknown> | undefined;
    const analysis = summary.analysis as Record<string, unknown> | undefined;
    if (Array.isArray(result?.scaling)) return result.scaling;
    if (Array.isArray(analysis?.scaling)) return analysis.scaling;
    if (Array.isArray(summary.results)) return summary.results;
    return [];
  }, [run]);

  async function act(name: string): Promise<void> {
    if (!base || !runId) return;
    setBusy(name);
    setActionError(null);
    try {
      if (name === "start") {
        const spec = experiments.data?.experiments[0];
        if (!spec) return;
        const created = await api<RunSummary>(`${base}/experiments/${spec.id}/runs`, { body: {} });
        setRunId(created.id);
        setTab("execution");
        experiments.reload();
      } else if (name === "cancel") {
        await api(`${base}/runs/${runId}/cancel`, { method: "POST" });
        runDetail.reload();
      } else if (name === "verify") {
        setVerification(await api<VerificationReport>(`${base}/runs/${runId}/verify`, { method: "POST" }));
      } else if (name === "claims") {
        setClaims(await api<ClaimsReport>(`${base}/runs/${runId}/claims`));
      } else if (name === "reproduce" && run?.spec_id) {
        const created = await api<RunSummary>(`${base}/experiments/${run.spec_id}/runs`, {
          body: { reproduce_run: runId },
        });
        setRunId(created.id);
        experiments.reload();
      } else if (name === "bundle") {
        await download(`${base}/runs/${runId}/bundle`, `${runId}-research-bundle.zip`);
      }
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : "The action failed.");
    } finally {
      setBusy(null);
    }
  }

  const engine = experiments.data?.capabilities.engine ?? capabilities.data?.engine;

  const projectOptions = useMemo(() => {
    const all = [...(projects.data?.items ?? []), ...(discover.data?.items ?? [])];
    const seen = new Set<string>();
    return all.filter((project) => {
      if (seen.has(project.full_name)) return false;
      seen.add(project.full_name);
      return true;
    });
  }, [projects.data, discover.data]);

  return (
    <>
      <PageMeta
        title="QEC Workbench"
        description="Configure, execute and audit quantum error-correction experiments on the Python engine."
      />
      <div className="qh-container py-6">
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">QEC Workbench</h1>
            <p className="qh-subtle m-0">
              Every number here is produced by <span className="qh-mono">quantumlab.research.qec</span>{" "}
              in a sandboxed process. The browser renders results; it never recomputes them.
            </p>
          </div>
          <div className="flex min-w-[260px] flex-col gap-1">
            <label className="qh-label" htmlFor="workbench-project">Project</label>
            <select
              id="workbench-project"
              className="qh-select"
              value={selectedProject}
              onChange={(event) => {
                const next = new URLSearchParams(params);
                if (event.target.value) next.set("project", event.target.value);
                else next.delete("project");
                setParams(next, { replace: true });
              }}
            >
              <option value="">Select a project…</option>
              {projectOptions.map((project) => (
                <option key={project.id} value={project.full_name}>
                  {project.full_name}
                  {project.visibility === "private" ? " (private)" : ""}
                </option>
              ))}
            </select>
          </div>
        </header>

        {capabilities.data && !capabilities.data.engine.available && (
          <div className="qh-form-error mb-4">
            The QEC engine is not importable in this environment: {capabilities.data.engine.error}
          </div>
        )}

        {!selectedProject && (
          <div className="qh-card qh-card-body">
            <EmptyState
              title="Choose a project to begin"
              description="Experiments, runs and artifacts always belong to a project, so they stay reproducible and shareable."
              action={
                projects.data && projects.data.items.length === 0 ? (
                  <Link to="/new" className="qh-btn qh-btn-primary">New project</Link>
                ) : undefined
              }
            />
            {projects.loading && <LoadingPanel rows={3} />}
            {projects.error && (
              <ErrorState message={projects.error.message} onRetry={projects.reload} />
            )}
          </div>
        )}

        {selectedProject && !owner && (
          <div className="qh-form-error">The project parameter must be owner/slug.</div>
        )}

        {selectedProject && owner && (
          <>
            <div className="qh-tabs mb-4" role="tablist">
              {TABS.map((item) => (
                <button
                  key={item}
                  type="button"
                  role="tab"
                  aria-selected={tab === item}
                  className="qh-tab"
                  data-active={tab === item}
                  onClick={() => setTab(item)}
                >
                  {LABELS[item]}
                </button>
              ))}
            </div>

            {experiments.loading && !experiments.data && <LoadingPanel rows={5} />}
            {experiments.error && (
              <ErrorState message={experiments.error.message} onRetry={experiments.reload} />
            )}

            {experiments.data && (
              <>
                {actionError && <div className="qh-form-error mb-3">{actionError}</div>}

                {tab === "configuration" && (
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                    <div className="space-y-4">
                      {engine?.available ? (
                        <ExperimentBuilder
                          basePath={base}
                          templates={experiments.data.templates}
                          onCreated={() => experiments.reload()}
                        />
                      ) : (
                        <div className="qh-form-error">
                          The engine is unavailable, so protocols cannot be validated.
                        </div>
                      )}
                    </div>
                    <aside className="qh-side-panel">
                      <section>
                        <h2 className="qh-side-title">Status ladder</h2>
                        <ol className="m-0 list-decimal space-y-1 pl-4 text-[12px] text-[#9198a1]">
                          <li>Configuration validated (schema + decoder compatibility)</li>
                          <li>Execution completed (engine wrote artifacts)</li>
                          <li>Integrity verified (checksums and manifest)</li>
                          <li>Reference comparison (not automated here)</li>
                          <li>Published reproduction (requires a published reference)</li>
                          <li>Independent reproduction (requires a third party)</li>
                          <li>Peer review (external)</li>
                        </ol>
                        <p className="qh-help">
                          QuantHub never advances these automatically. A completed run is not a
                          validated scientific claim.
                        </p>
                      </section>
                      <section>
                        <h2 className="qh-side-title">Engine capabilities</h2>
                        {capabilities.data?.capabilities ? (
                          <ul className="m-0 list-none space-y-1 p-0 text-[11px]">
                            {capabilities.data.capabilities.map((capability) => (
                              <li key={capability.name} className="flex items-start gap-1">
                                <span
                                  className={
                                    capability.status.includes("VERIFIED")
                                      ? "text-[#3fb950]"
                                      : "text-[#e3b341]"
                                  }
                                >
                                  ●
                                </span>
                                <span>
                                  <span className="qh-mono">{capability.name}</span>
                                  <span className="block text-[#6e7681]">{capability.status}</span>
                                </span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="qh-help m-0">Capabilities unavailable.</p>
                        )}
                      </section>
                      <section>
                        <h2 className="qh-side-title">Decoders</h2>
                        <ul className="m-0 list-none space-y-1 p-0 text-[12px] text-[#9198a1]">
                          {(capabilities.data?.ui_decoders ?? experiments.data.capabilities.ui_decoders ?? []).map(
                            (decoder: DecoderInfo) => (
                              <li key={decoder.id}>
                                <span className="qh-mono text-[#c9d1d9]">{decoder.id}</span>
                                {!decoder.available && <span className="text-[#e3b341]"> (unavailable)</span>}
                              </li>
                            ),
                          )}
                        </ul>
                      </section>
                    </aside>
                  </div>
                )}

                {tab === "execution" && (
                  <div className="space-y-4">
                    <div className="qh-card overflow-hidden">
                      <div className="qh-card-header flex flex-wrap items-center justify-between gap-2">
                        <h2 className="m-0 text-[14px] font-semibold">Experiments</h2>
                        <button
                          type="button"
                          className="qh-btn qh-btn-sm qh-btn-primary"
                          disabled={
                            busy !== null ||
                            !engine?.available ||
                            experiments.data.experiments.length === 0
                          }
                          onClick={() => void act("start")}
                          title="Runs the most recent experiment specification"
                        >
                          {busy === "start" ? "Starting…" : "Start run (latest experiment)"}
                        </button>
                      </div>
                      {experiments.data.experiments.length === 0 ? (
                        <div className="qh-card-body">
                          <EmptyState
                            title="No experiment specifications"
                            description="Create one in the Configuration tab."
                          />
                        </div>
                      ) : (
                        <table className="qh-data">
                          <thead>
                            <tr>
                              <th scope="col">Experiment</th>
                              <th scope="col" className="text-right">Runs</th>
                              <th scope="col">Last status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {experiments.data.experiments.map((spec) => (
                              <tr key={spec.id}>
                                <td>
                                  <Link
                                    to={`/${owner}/${slug}/experiments/${spec.id}`}
                                    className="text-[#79c0ff]"
                                  >
                                    {spec.name}
                                  </Link>
                                </td>
                                <td className="text-right">{spec.run_count}</td>
                                <td className="text-[11px] text-[#8b949e]">{spec.last_status ?? "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h2 className="m-0 text-[14px] font-semibold">Runs</h2>
                        <Link to={`/${owner}/${slug}/runs`} className="text-[12px] text-[#79c0ff]">
                          All runs
                        </Link>
                      </div>
                      <RunsTable
                        runs={experiments.data.runs}
                        basePath={`/${owner}/${slug}`}
                        emptyTitle="No runs yet"
                        emptyDescription="Start a run to execute the stored protocol."
                      />
                    </div>
                  </div>
                )}

                {(tab === "results" || tab === "scaling" || tab === "artifacts" || tab === "validation") && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-end gap-2">
                      <div className="min-w-[240px]">
                        <label className="qh-label" htmlFor="run-select">Run</label>
                        <select
                          id="run-select"
                          className="qh-select"
                          value={runId}
                          onChange={(event) => {
                            setRunId(event.target.value);
                            setVerification(null);
                            setClaims(null);
                          }}
                        >
                          <option value="">Select a run…</option>
                          {experiments.data.runs.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.id} · {item.status}
                            </option>
                          ))}
                        </select>
                      </div>
                      {run && (
                        <div className="flex flex-wrap items-center gap-2 text-[12px] text-[#8b949e]">
                          <RunStatusPill status={run.status} />
                          <span>{formatDate(run.created_at)}</span>
                          {["queued", "running", "cancelling"].includes(run.status) && (
                            <button
                              type="button"
                              className="qh-btn qh-btn-sm qh-btn-danger"
                              onClick={() => void act("cancel")}
                              disabled={busy !== null}
                            >
                              Cancel
                            </button>
                          )}
                          {run.status === "completed" && (
                            <button
                              type="button"
                              className="qh-btn qh-btn-sm"
                              onClick={() => void act("reproduce")}
                              disabled={busy !== null}
                            >
                              Reproduce
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    {!runId && (
                      <EmptyState
                        title="No run selected"
                        description="Pick a run to inspect its engine-produced results, or start a new one in Execution."
                      />
                    )}
                    {runDetail.loading && !run && runId && <LoadingPanel rows={5} />}
                    {runDetail.error && (
                      <ErrorState message={runDetail.error.message} onRetry={runDetail.reload} />
                    )}

                    {run && tab === "results" && <ResultsView run={run} />}

                    {run && tab === "scaling" && (
                      <div className="qh-card">
                        <div className="qh-card-header">
                          <h2 className="m-0 text-[14px] font-semibold">Scaling</h2>
                        </div>
                        <div className="qh-card-body">
                          {scaling.length === 0 ? (
                            <EmptyState
                              title="No scaling series in this run"
                              description="This run records a single configuration. QuantHub does not extrapolate thresholds or trends without a real multi-distance series."
                            />
                          ) : (
                            <pre className="qh-code m-0 max-h-[480px] overflow-auto">
                              {JSON.stringify(scaling, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                    )}

                    {run && tab === "artifacts" && (
                      <div className="qh-card overflow-hidden">
                        <div className="qh-card-header flex items-center justify-between">
                          <h2 className="m-0 text-[14px] font-semibold">Artifacts</h2>
                          <button
                            type="button"
                            className="qh-btn qh-btn-sm"
                            onClick={() => void act("bundle")}
                            disabled={busy !== null || !run.artifacts_available}
                          >
                            Download bundle
                          </button>
                        </div>
                        {run.artifacts.length === 0 ? (
                          <div className="qh-card-body">
                            <EmptyState
                              title="No artifacts"
                              description="Artifacts appear once the engine has written its evidence directory."
                            />
                          </div>
                        ) : (
                          <table className="qh-data">
                            <thead>
                              <tr>
                                <th scope="col">File</th>
                                <th scope="col" className="text-right">Size</th>
                                <th scope="col">SHA-256</th>
                                <th scope="col"><span className="sr-only">Download</span></th>
                              </tr>
                            </thead>
                            <tbody>
                              {run.artifacts.map((artifact) => (
                                <tr key={artifact.name}>
                                  <td className="qh-mono">{artifact.name}</td>
                                  <td className="text-right">{formatBytes(artifact.size)}</td>
                                  <td className="qh-mono text-[11px] text-[#8b949e]">
                                    {artifact.sha256.slice(0, 16)}…
                                  </td>
                                  <td className="text-right">
                                    <button
                                      type="button"
                                      className="qh-btn qh-btn-sm"
                                      onClick={() =>
                                        void download(
                                          `${base}/runs/${run.id}/artifacts/${encodeURIComponent(artifact.name)}`,
                                          artifact.name,
                                        )
                                      }
                                    >
                                      Download
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    )}

                    {run && tab === "validation" && (
                      <div className="space-y-4">
                        <div className="qh-card qh-card-body">
                          <h2 className="m-0 text-[14px] font-semibold">Statuses for this run</h2>
                          <ul className="mt-2 list-none space-y-1 p-0 text-[12px]">
                            <li>
                              <span className="text-[#3fb950]">●</span> Configuration validated by
                              the engine
                            </li>
                            <li>
                              <span className={run.status === "completed" ? "text-[#3fb950]" : "text-[#6e7681]"}>●</span>{" "}
                              Execution: {run.status}
                            </li>
                            <li>
                              <span className={verification?.ok ? "text-[#3fb950]" : "text-[#6e7681]"}>●</span>{" "}
                              Integrity: {verification ? (verification.ok ? "verified" : "failed") : "not checked"}
                            </li>
                            <li><span className="text-[#6e7681]">○</span> Reference comparison: not performed</li>
                            <li><span className="text-[#6e7681]">○</span> Published reproduction: none</li>
                            <li><span className="text-[#6e7681]">○</span> Independent reproduction: none</li>
                            <li><span className="text-[#6e7681]">○</span> Peer review: none</li>
                          </ul>
                        </div>

                        <div className="qh-card qh-card-body">
                          <h2 className="m-0 text-[14px] font-semibold">Integrity verification</h2>
                          <p className="qh-help mt-1">
                            Recomputes SHA-256 digests and cross-checks the manifest. Passing proves
                            the files are unchanged, not that the science is correct.
                          </p>
                          <button
                            type="button"
                            className="qh-btn qh-btn-primary"
                            onClick={() => void act("verify")}
                            disabled={busy !== null || !run.artifacts_available}
                          >
                            {busy === "verify" ? "Verifying…" : "Verify artifacts"}
                          </button>
                          {verification && (
                            <div className="mt-2 text-[12px]">
                              <p className={`m-0 font-semibold ${verification.ok ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                                {verification.ok ? "Passed" : "Failed"} · {verification.checked_files} file(s)
                              </p>
                              {[...verification.errors, ...verification.warnings].map((line) => (
                                <p key={line} className="m-0 text-[#e3b341]">{line}</p>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="qh-card qh-card-body">
                          <h2 className="m-0 text-[14px] font-semibold">Claim audit</h2>
                          <p className="qh-help mt-1">
                            Audits the summary for required fields and unsupported claim language.
                          </p>
                          <button
                            type="button"
                            className="qh-btn"
                            onClick={() => void act("claims")}
                            disabled={busy !== null || !run.artifacts_available}
                          >
                            {busy === "claims" ? "Auditing…" : "Audit claims"}
                          </button>
                          {claims && (
                            <div className="mt-2 text-[12px]">
                              <p className={`m-0 font-semibold ${claims.status === "PASS" ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                                {claims.status}
                              </p>
                              {[...claims.errors, ...claims.warnings].map((line) => (
                                <p key={line} className="m-0 text-[#e3b341]">{line}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}
