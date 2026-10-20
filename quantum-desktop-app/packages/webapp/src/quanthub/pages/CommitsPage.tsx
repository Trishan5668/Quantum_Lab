import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, formatDate, formatRelativeTime } from "../client";
import { useAsync } from "../hooks";
import type { CommitInfo } from "../types";
import { ProjectChrome } from "../components/ProjectChrome";
import { EmptyState, ErrorState, LoadingPanel } from "../components/ui";

export default function CommitsPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const path = params.get("path");
  const query = new URLSearchParams({ limit: "50" });
  if (path) query.set("path", path);

  const state = useAsync(
    (signal) =>
      api<{ commits: CommitInfo[] }>(`/projects/${owner}/${slug}/commits?${query.toString()}`, {
        signal,
      }),
    [owner, slug, path],
  );

  return (
    <>
      <PageMeta title={`Commits · ${owner}/${slug}`} description="Revision history for this project." />
      <ProjectChrome owner={owner} slug={slug} tab="commits">
        {() => (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0 text-[15px] font-semibold">
                {path ? `History for ${path}` : "Commit history"}
              </h2>
              {path && (
                <button
                  type="button"
                  className="qh-btn qh-btn-sm"
                  onClick={() => {
                    const next = new URLSearchParams(params);
                    next.delete("path");
                    setParams(next, { replace: true });
                  }}
                >
                  Show all commits
                </button>
              )}
            </div>

            {state.loading && !state.data && <LoadingPanel rows={6} />}
            {state.error && <ErrorState message={state.error.message} onRetry={state.reload} />}
            {state.data && state.data.commits.length === 0 && (
              <EmptyState
                title="No commits"
                description="This project has no revisions matching the current filter."
              />
            )}
            {state.data && state.data.commits.length > 0 && (
              <div className="qh-card overflow-hidden">
                <table className="qh-data">
                  <thead>
                    <tr>
                      <th scope="col">Commit</th>
                      <th scope="col">Message</th>
                      <th scope="col">Author</th>
                      <th scope="col" className="text-right">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.data.commits.map((commit) => (
                      <tr key={commit.sha}>
                        <td className="qh-mono text-[#79c0ff]">{commit.sha.slice(0, 7)}</td>
                        <td>
                          <div className="text-[#c9d1d9]">{commit.message}</div>
                          {commit.parents && commit.parents.length > 0 && (
                            <div className="qh-mono text-[11px] text-[#6e7681]">
                              parent {commit.parents[0]?.slice(0, 7)}
                            </div>
                          )}
                        </td>
                        <td className="text-[#8b949e]">{commit.author_name}</td>
                        <td className="text-right text-[#8b949e]" title={formatDate(commit.authored_at)}>
                          {formatRelativeTime(commit.authored_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <p className="qh-help">
              Commits are created by the server's Git layer. QuantHub does not display diffs yet;
              open a file to see its current contents and per-file history.
            </p>
            <Link to={`/${owner}/${slug}`} className="qh-btn qh-btn-sm">
              Back to files
            </Link>
          </div>
        )}
      </ProjectChrome>
    </>
  );
}
