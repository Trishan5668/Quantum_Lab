import { Link } from "react-router-dom";
import { formatRelativeTime } from "../client";
import type { RunSummary } from "../types";
import { EmptyState, RunStatusPill } from "./ui";

export function RunsTable({
  runs,
  basePath,
  emptyTitle = "No runs yet",
  emptyDescription,
  action,
}: {
  runs: RunSummary[];
  basePath: string;
  emptyTitle?: string;
  emptyDescription?: string;
  action?: React.ReactNode;
}): JSX.Element {
  if (runs.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={action} />;
  }
  return (
    <div className="qh-card overflow-hidden">
      <table className="qh-data">
        <thead>
          <tr>
            <th scope="col">Run</th>
            <th scope="col">Status</th>
            <th scope="col">Experiment</th>
            <th scope="col" className="text-right">Created</th>
            <th scope="col" className="text-right">Finished</th>
            <th scope="col">Scientific status</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>
                <Link to={`${basePath}/runs/${run.id}`} className="qh-mono text-[#79c0ff]">
                  {run.id}
                </Link>
                {run.reproduction_of && (
                  <span className="qh-badge ml-2" title={`Reproduction of ${run.reproduction_of}`}>
                    repro
                  </span>
                )}
              </td>
              <td><RunStatusPill status={run.status} /></td>
              <td className="qh-mono text-[11px] text-[#8b949e]">{run.spec_id ?? "—"}</td>
              <td className="text-right text-[#8b949e]">{formatRelativeTime(run.created_at)}</td>
              <td className="text-right text-[#8b949e]">{formatRelativeTime(run.finished_at)}</td>
              <td className="text-[11px] text-[#8b949e]">{run.scientific_status ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
