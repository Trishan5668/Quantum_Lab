import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError, download, formatBytes, formatDate } from "../client";
import { useAsync, usePolling } from "../hooks";
import type { RunDetail } from "../types";
import { ResultsView } from "../components/ResultsView";
import { EmptyState, ErrorState, LoadingPanel, RunStatusPill } from "../components/ui";

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
  report_present?: boolean;
}

const TABS = ["results", "scaling", "artifacts", "validation", "log"] as const;

export default function RunDetailPage(): JSX.Element {
  const { owner = "", slug = "", runId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((item) => item === params.get("tab")) ?? "results") as (typeof TABS)[number];
  const base = `/projects/${owner}/${slug}`;
  const run = useAsync((signal) => api<RunDetail>(`${base}/runs/${runId}`, { signal }), [owner, slug, runId]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationReport | null>(null);
  const [claims, setClaims] = useState<ClaimsReport | null>(null);
  const [log, setLog] = useState<string | null>(null);

  const active = run.data?.status === "queued" || run.data?.status === "running" || run.data?.status === "cancelling";
  usePolling(Boolean(active), 2000, run.reload);

  async function act(name: string, body?: unknown): Promise<void> {
    setBusy(name);
    setActionError(null);
    try {
      if (name === "verify") {
        setVerification(await api<VerificationReport>(`${base}/runs/${runId}/verify`, { method: "POST" }));
      } else if (name === "claims") {
        setClaims(await api<ClaimsReport>(`${base}/runs/${runId}/claims`));
      } else if (name === "log") {
        const payload = await api<{ content: string; truncated: boolean }>(`${base}/runs/${runId}/log`);
        setLog(payload.content || "(no log output recorded)");
      } else if (name === "cancel") {
        await api(`${base}/runs/${runId}/cancel`, { method: "POST" });
        run.reload();
      } else if (name === "reproduce") {
        const created = await api<{ id: string }>(`${base}/experiments/${run.data?.spec_id}/runs`, {
          body: { reproduce_run: runId },
        });
        window.location.assign(`/${owner}/${slug}/runs/${created.id}`);
      } else if (name === "bundle") {
        await download(`${base}/runs/${runId}/bundle`, `${runId}-research-bundle.zip`);
      } else if (name === "export") {
        await download(`${base}/runs/${runId}/export`, `${runId}-summary.json`);
      } else if (name === "artifact" && body) {
        await download(`${base}/runs/${runId}/artifacts/${encodeURIComponent(String(body))}`, String(body));
      }
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : "The action failed.");
    } finally {
      setBusy(null);
    }
  }

  if (run.loading && !run.data) {
    return <div className="qh-container py-6"><LoadingPanel rows={6} /></div>;
  }
  if (run.error) {
    return (
      <div className="qh-container py-6">
        <ErrorState message={run.error.message} onRetry={run.reload} />
      </div>
    );
  }
  if (!run.data) return <></>;
  const detail = run.data;

  const summary = (detail.summary ?? {}) as Record<string, unknown>;
  const analysis = summary.analysis as Record<string, unknown> | undefined;
  const result = summary.result as Record<string, unknown> | undefined;
  const scalingPoints: unknown[] = Array.isArray(result?.scaling)
    ? result.scaling
    : Array.isArray(analysis?.scaling)
      ? analysis.scaling
      : Array.isArray(summary.results)
        ? summary.results
        : [];

  return (
    <>
      <PageMeta title={`Run ${detail.id}`} description="Reproducible QEC run results and artifacts." />
      <div className="qh-container py-6">
        <nav className="qh-muted mb-2 text-[12px]" aria-label="Breadcrumb">
          <Link to="/">Home</Link> / <Link to={`/${owner}/${slug}`}>{owner}/{slug}</Link> /{" "}
          <Link to={`/${owner}/${slug}/runs`}>Runs</Link> / <span className="qh-mono">{detail.id}</span>
        </nav>

        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="m-0 flex flex-wrap items-center gap-2 text-[20px] font-semibold">
              <span className="qh-mono text-[16px]">{detail.id}</span>
              <RunStatusPill status={detail.status} />
            </h1>
            <p className="qh-subtle m-0 text-[12px]">
              Created {formatDate(detail.created_at)} · {detail.actor ? `by ${detail.actor}` : "unknown actor"}
              {detail.spec_id && (
                <>
                  {" · "}
                  <Link
                    className="text-[#79c0ff]"
                    to={`/${owner}/${slug}/experiments/${detail.spec_id}`}
                  >
                    experiment
                  </Link>
                </>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {active && (
              <button
                type="button"
                className="qh-btn qh-btn-danger"
                onClick={() => void act("cancel")}
                disabled={busy !== null}
              >
                {detail.status === "cancelling" ? "Cancelling…" : "Cancel run"}
              </button>
            )}
            {detail.status === "completed" && detail.reproduction_of && (
              <span className="qh-badge qh-badge-accent">reproduction</span>
            )}
            {detail.status === "completed" && (
              <button
                type="button"
                className="qh-btn"
                onClick={() => void act("reproduce")}
                disabled={busy !== null || !detail.spec_id}
                title="Runs the stored protocol again as a new run"
              >
                Reproduce
              </button>
            )}
            {detail.artifacts_available && (
              <button
                type="button"
                className="qh-btn"
                onClick={() => void act("bundle")}
                disabled={busy !== null}
              >
                Download bundle
              </button>
            )}
            <button
              type="button"
              className="qh-btn"
              onClick={() => void act("export")}
              disabled={busy !== null}
            >
              Export summary
            </button>
          </div>
        </header>

        {actionError && <div className="qh-form-error mb-3">{actionError}</div>}

        <div className="qh-tabs mb-4" role="tablist">
          {TABS.map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={tab === item}
              className="qh-tab"
              data-active={tab === item}
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set("tab", item);
                setParams(next, { replace: true });
              }}
            >
              {item === "scaling" ? "Scaling" : item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>

        {tab === "results" && <ResultsView run={detail} />}

        {tab === "scaling" && (
          <div className="qh-card">
            <div className="qh-card-header">
              <h2 className="m-0 text-[14px] font-semibold">Scaling data</h2>
            </div>
            <div className="qh-card-body">
              {scalingPoints.length === 0 ? (
                <EmptyState
                  title="No scaling table in this run"
                  description="This experiment records a single distance/round point. Multi-distance sweeps are not implemented yet, so no trend or threshold is inferred here."
                />
              ) : (
                <pre className="qh-code m-0 max-h-[480px] overflow-auto">
                  {JSON.stringify(scalingPoints, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}

        {tab === "artifacts" && (
          <div className="qh-card overflow-hidden">
            <div className="qh-card-header">
              <h2 className="m-0 text-[14px] font-semibold">Artifacts</h2>
              <span className="text-[11px] text-[#6e7681]">
                Integrity digests are computed from the files on disk.
              </span>
            </div>
            {detail.artifacts.length === 0 ? (
              <div className="qh-card-body">
                <EmptyState
                  title="No artifacts"
                  description="Artifacts appear when the engine writes its evidence directory."
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
                  {detail.artifacts.map((artifact) => (
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
                          onClick={() => void act("artifact", artifact.name)}
                          disabled={busy !== null}
                        >
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {detail.manifest && (
              <details className="border-t border-[#21262d] px-4 py-2 text-[12px]">
                <summary className="cursor-pointer text-[#79c0ff]">Manifest</summary>
                <pre className="qh-code mt-2 max-h-64 overflow-auto">
                  {JSON.stringify(detail.manifest, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {tab === "validation" && (
          <div className="space-y-4">
            <div className="qh-card">
              <div className="qh-card-header">
                <h2 className="m-0 text-[14px] font-semibold">Integrity verification</h2>
                <span className="qh-badge">checksums, not scientific validity</span>
              </div>
              <div className="qh-card-body">
                <p className="qh-help mt-0">
                  Verification recomputes SHA-256 digests for every file listed in{" "}
                  <span className="qh-mono">checksums.sha256</span> and cross-checks the manifest,
                  config and summary. It proves the artifacts are unchanged, not that the
                  conclusion is correct.
                </p>
                <button
                  type="button"
                  className="qh-btn qh-btn-primary"
                  onClick={() => void act("verify")}
                  disabled={busy !== null || !detail.artifacts_available}
                >
                  {busy === "verify" ? "Verifying…" : "Verify artifacts"}
                </button>
                {!detail.artifacts_available && (
                  <p className="qh-help mb-0">No artifact directory exists for this run.</p>
                )}
                {verification && (
                  <div className="mt-3 text-[12px]">
                    <p className={`m-0 font-semibold ${verification.ok ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                      {verification.ok ? "Integrity check passed" : "Integrity check failed"} ·{" "}
                      {verification.checked_files} file(s) checked
                    </p>
                    {verification.errors.length > 0 && (
                      <ul className="mb-0 mt-1 pl-4 text-[#f85149]">
                        {verification.errors.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}
                    {verification.warnings.length > 0 && (
                      <ul className="mb-0 mt-1 pl-4 text-[#e3b341]">
                        {verification.warnings.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="qh-card">
              <div className="qh-card-header">
                <h2 className="m-0 text-[14px] font-semibold">Claim audit</h2>
                <span className="qh-badge">banned-phrase and field checks</span>
              </div>
              <div className="qh-card-body">
                <p className="qh-help mt-0">
                  The audit checks the summary for required fields, zero-failure rows without an
                  upper bound, and unsupported claim language in the generated report. A passing
                  audit is a formatting check, not peer review.
                </p>
                <button
                  type="button"
                  className="qh-btn"
                  onClick={() => void act("claims")}
                  disabled={busy !== null || !detail.artifacts_available}
                >
                  {busy === "claims" ? "Auditing…" : "Audit claims"}
                </button>
                {claims && (
                  <div className="mt-3 text-[12px]">
                    <p
                      className={`m-0 font-semibold ${
                        claims.status === "PASS" ? "text-[#3fb950]" : "text-[#f85149]"
                      }`}
                    >
                      Audit status: {claims.status}
                      {claims.shape ? ` (${claims.shape})` : ""}
                    </p>
                    {claims.errors.length > 0 && (
                      <ul className="mb-0 mt-1 pl-4 text-[#f85149]">
                        {claims.errors.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}
                    {claims.warnings.length > 0 && (
                      <ul className="mb-0 mt-1 pl-4 text-[#e3b341]">
                        {claims.warnings.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="qh-card">
              <div className="qh-card-header">
                <h2 className="m-0 text-[14px] font-semibold">What is not claimed</h2>
              </div>
              <div className="qh-card-body text-[12px] text-[#9198a1]">
                <ul className="m-0 pl-4">
                  <li>No independent reproduction has been performed by another party.</li>
                  <li>No peer review has occurred for this run.</li>
                  <li>Results describe the simulated noise model only, not hardware.</li>
                  <li>Integrity and audit checks do not establish scientific correctness.</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {tab === "log" && (
          <div className="qh-card">
            <div className="qh-card-header flex items-center justify-between">
              <h2 className="m-0 text-[14px] font-semibold">Engine log</h2>
              <button
                type="button"
                className="qh-btn qh-btn-sm"
                onClick={() => void act("log")}
                disabled={busy !== null}
              >
                {busy === "log" ? "Loading…" : "Load log"}
              </button>
            </div>
            <pre className="qh-code m-0 max-h-[520px] overflow-auto border-0">
              {log ?? "Load the captured stdout/stderr of the engine process."}
            </pre>
          </div>
        )}
      </div>
    </>
  );
}
