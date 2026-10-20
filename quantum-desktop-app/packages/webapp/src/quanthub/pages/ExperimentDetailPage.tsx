import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError, formatDate } from "../client";
import { useAsync } from "../hooks";
import type { ExperimentSpec, RunSummary } from "../types";
import { RunsTable } from "../components/RunsTable";
import { ErrorState, LoadingPanel } from "../components/ui";

interface ExperimentPayload {
  experiment: ExperimentSpec;
  runs: RunSummary[];
}

export default function ExperimentDetailPage(): JSX.Element {
  const { owner = "", slug = "", specId = "" } = useParams();
  const navigate = useNavigate();
  const base = `/projects/${owner}/${slug}`;
  const projectBase = `/${owner}/${slug}`;
  const state = useAsync(
    (signal) => api<ExperimentPayload>(`${base}/experiments/${specId}`, { signal }),
    [owner, slug, specId],
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(): Promise<void> {
    setBusy("run");
    setError(null);
    try {
      const created = await api<RunSummary>(`${base}/experiments/${specId}/runs`, { body: {} });
      navigate(`${projectBase}/runs/${created.id}`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The run could not be started.");
    } finally {
      setBusy(null);
    }
  }

  async function remove(): Promise<void> {
    if (!window.confirm("Delete this experiment specification? Existing runs and artifacts are kept.")) {
      return;
    }
    setBusy("delete");
    setError(null);
    try {
      await api(`${base}/experiments/${specId}`, { method: "DELETE" });
      navigate(`${projectBase}/experiments`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The experiment could not be deleted.");
    } finally {
      setBusy(null);
    }
  }

  if (state.loading && !state.data) {
    return <div className="qh-container py-6"><LoadingPanel rows={6} /></div>;
  }
  if (state.error) {
    return (
      <div className="qh-container py-6">
        <ErrorState message={state.error.message} onRetry={state.reload} />
      </div>
    );
  }
  if (!state.data) return <></>;
  const { experiment, runs } = state.data;

  return (
    <>
      <PageMeta title={`${experiment.name} · ${owner}/${slug}`} description={experiment.description} />
      <div className="qh-container py-6">
        <nav className="qh-muted mb-2 text-[12px]">
          <Link to={projectBase}>{owner}/{slug}</Link> /{" "}
          <Link to={`${projectBase}/experiments`}>Experiments</Link> / {experiment.slug}
        </nav>
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">{experiment.name}</h1>
            <p className="qh-subtle m-0 text-[12px]">
              Created {formatDate(experiment.created_at)} by {experiment.created_by} · config{" "}
              <span className="qh-mono">{experiment.config_hash?.slice(0, 16) ?? "—"}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qh-btn qh-btn-primary"
              onClick={() => void run()}
              disabled={busy !== null}
            >
              {busy === "run" ? "Starting…" : "Start run"}
            </button>
            <button
              type="button"
              className="qh-btn qh-btn-danger"
              onClick={() => void remove()}
              disabled={busy !== null}
            >
              Delete
            </button>
          </div>
        </header>

        {error && <div className="qh-form-error mb-3">{error}</div>}

        {experiment.description && (
          <p className="mb-4 text-[13px] text-[#c9d1d9]">{experiment.description}</p>
        )}

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-4">
            <div className="qh-card overflow-hidden">
              <div className="qh-card-header">
                <h2 className="m-0 text-[14px] font-semibold">Runs</h2>
              </div>
              <div className="p-3">
                <RunsTable
                  runs={runs}
                  basePath={projectBase}
                  emptyTitle="No runs for this experiment"
                  emptyDescription="Start a run to execute the stored protocol."
                />
              </div>
            </div>

            <div className="qh-card">
              <div className="qh-card-header">
                <h2 className="m-0 text-[14px] font-semibold">Stored protocol</h2>
                <span className="qh-badge">immutable snapshot per run</span>
              </div>
              <pre className="qh-code m-0 max-h-[520px] overflow-auto border-0">
                {JSON.stringify(experiment.protocol, null, 2)}
              </pre>
            </div>
          </div>

          <aside className="qh-side-panel">
            <section>
              <h2 className="qh-side-title">Runs</h2>
              <p className="m-0 text-[12px] text-[#9198a1]">
                {experiment.run_count} run{experiment.run_count === 1 ? "" : "s"} · last status{" "}
                {experiment.last_status ?? "none"}
              </p>
              <p className="qh-help mb-0 mt-1">
                Editing this specification does not rewrite past runs; each run stores the protocol
                it executed.
              </p>
            </section>
            <section>
              <h2 className="qh-side-title">Related</h2>
              <Link to={`/qec?project=${owner}/${slug}`} className="qh-btn w-full justify-center">
                Open in QEC Workbench
              </Link>
            </section>
          </aside>
        </div>
      </div>
    </>
  );
}
