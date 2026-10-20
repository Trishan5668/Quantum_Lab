import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api } from "../client";
import { useAsync } from "../hooks";
import type { ExperimentSpec, ProjectList, RunSummary } from "../types";
import { EmptyState, ErrorState, LoadingPanel, RunStatusPill } from "../components/ui";
import { formatRelativeTime } from "../client";

interface Row {
  project: string;
  spec: ExperimentSpec;
  runs: RunSummary[];
}

export default function GlobalExperimentsPage(): JSX.Element {
  const state = useAsync(async (signal) => {
    const mine = await api<ProjectList>("/projects?view=mine&per_page=8", { signal });
    const rows = await Promise.all(
      mine.items.map(async (project) => {
        try {
          const payload = await api<{ experiments: ExperimentSpec[]; runs: RunSummary[] }>(
            `/projects/${project.owner.handle}/${project.slug}/experiments`,
            { signal },
          );
          return payload.experiments.map((spec) => ({
            project: project.full_name,
            spec,
            runs: payload.runs.filter((run) => run.spec_id === spec.id),
          }));
        } catch {
          return [];
        }
      }),
    );
    return rows.flat();
  }, []);

  const rows = (state.data ?? []) as Row[];

  return (
    <>
      <PageMeta
        title="Experiments"
        description="Experiment specifications across your QuantHub projects."
      />
      <div className="qh-container py-6">
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">Experiments</h1>
            <p className="qh-subtle m-0">
              Specifications across your projects. Runs are executed by the Python QEC engine.
            </p>
          </div>
          <Link to="/qec" className="qh-btn qh-btn-primary">
            Open QEC Workbench
          </Link>
        </header>

        {state.loading && !state.data && <LoadingPanel rows={5} />}
        {state.error && <ErrorState message={state.error.message} onRetry={state.reload} />}

        {state.data && rows.length === 0 && (
          <EmptyState
            title="No experiments yet"
            description="Create an experiment specification inside a project, or start from a template in the QEC Workbench."
            action={<Link to="/qec" className="qh-btn">QEC Workbench</Link>}
          />
        )}

        {rows.length > 0 && (
          <div className="qh-card overflow-hidden">
            <table className="qh-data">
              <thead>
                <tr>
                  <th scope="col">Experiment</th>
                  <th scope="col">Project</th>
                  <th scope="col" className="text-right">Runs</th>
                  <th scope="col">Last run</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const [owner, slug] = row.project.split("/");
                  const last = row.runs[0];
                  return (
                    <tr key={row.spec.id}>
                      <td>
                        <Link
                          to={`/${owner}/${slug}/experiments/${row.spec.id}`}
                          className="text-[#79c0ff]"
                        >
                          {row.spec.name}
                        </Link>
                      </td>
                      <td>
                        <Link to={`/${owner}/${slug}`} className="qh-mono text-[12px] text-[#9198a1]">
                          {row.project}
                        </Link>
                      </td>
                      <td className="text-right">{row.spec.run_count}</td>
                      <td className="text-[12px]">
                        {last ? (
                          <span className="flex items-center gap-2">
                            <RunStatusPill status={last.status} />
                            <Link
                              to={`/${owner}/${slug}/runs/${last.id}`}
                              className="qh-mono text-[11px] text-[#79c0ff]"
                            >
                              {last.id}
                            </Link>
                            <span className="text-[11px] text-[#6e7681]">
                              {formatRelativeTime(last.created_at)}
                            </span>
                          </span>
                        ) : (
                          <span className="text-[#6e7681]">never run</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
