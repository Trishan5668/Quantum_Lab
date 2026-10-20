import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api } from "../client";
import { useAsync } from "../hooks";
import type { RunSummary } from "../types";
import { RunsTable } from "../components/RunsTable";
import { ErrorState, LoadingPanel } from "../components/ui";

export default function RunsPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const base = `/projects/${owner}/${slug}`;
  const state = useAsync(
    (signal) => api<{ runs: RunSummary[] }>(`${base}/runs?limit=50`, { signal }),
    [owner, slug],
  );

  return (
    <>
      <PageMeta title={`Runs · ${owner}/${slug}`} description="Execution history for this project." />
      <div className="qh-container py-6">
        <nav className="qh-muted mb-2 text-[12px]">
          <Link to={`/${owner}/${slug}`}>{owner}/{slug}</Link> / Runs
        </nav>
        <header className="mb-4">
          <h1 className="m-0 text-[20px] font-semibold">Runs</h1>
          <p className="qh-subtle m-0">
            Every execution is a separate, immutable evidence directory with checksums.
          </p>
        </header>

        {state.loading && !state.data && <LoadingPanel rows={5} />}
        {state.error && <ErrorState message={state.error.message} onRetry={state.reload} />}
        {state.data && (
          <RunsTable
            runs={state.data.runs}
            basePath={`/${owner}/${slug}`}
            emptyTitle="No runs yet"
            emptyDescription="Start an experiment run from the Experiments tab."
            action={
              <Link to={`/${owner}/${slug}/experiments`} className="qh-btn">
                Go to experiments
              </Link>
            }
          />
        )}
      </div>
    </>
  );
}
