import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, loadRecentProjects, type RecentProject } from "../client";
import { useSession } from "../session";
import type { DashboardPayload } from "../types";
import { NewsPanel } from "../components/NewsPanel";
import {
  EmptyState,
  ErrorState,
  LockIcon,
  LoadingPanel,
  RelativeTime,
  RepoIcon,
  RunStatusPill,
  Skeleton,
} from "../components/ui";

function activityText(event: DashboardPayload["activity"][number]): string {
  const project = event.project?.full_name ?? "a project";
  const payload = event.payload ?? {};
  switch (event.type) {
    case "project.created":
      return `created ${project}`;
    case "project.files_changed":
      return `pushed ${Array.isArray(payload.files) ? payload.files.length : 0} file change(s) to ${project}`;
    case "project.imported":
      return `imported ${String(payload.files ?? 0)} file(s) into ${project}`;
    case "project.updated":
      return `updated project settings for ${project}`;
    case "project.archived":
      return `archived ${project}`;
    case "project.starred":
      return `starred ${project}`;
    case "experiment.created":
      return `created experiment “${String(payload.name ?? "")}” in ${project}`;
    case "run.queued":
      return `queued run ${String(payload.run_id ?? "")} in ${project}`;
    case "run.completed":
      return `completed run ${String(payload.run_id ?? "")} in ${project}`;
    case "run.failed":
      return `run ${String(payload.run_id ?? "")} failed in ${project}`;
    case "run.cancelled":
      return `cancelled run ${String(payload.run_id ?? "")} in ${project}`;
    default:
      return `${event.type.replace(".", " ")} in ${project}`;
  }
}

export default function HomePage(): JSX.Element {
  const { viewer, loading: sessionLoading } = useSession();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [recent] = useState<RecentProject[]>(() => loadRecentProjects());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api<DashboardPayload>("/dashboard")
      .then(setData)
      .catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : "Unable to load your dashboard."),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load, viewer?.handle]);

  const displayName = data?.viewer.display_name ?? viewer?.display_name ?? "researcher";
  const myProjects = data?.my_projects ?? [];
  const topProjects = data?.trending_projects ?? [];

  return (
    <>
      <PageMeta title="QuantHub" description="Projects, experiments and reproducible quantum research." />
      <div className="qh-container">
        <div className="qh-home-grid">
          {/* ---------------------------------------------------------- */}
          {/* Left sidebar                                               */}
          {/* ---------------------------------------------------------- */}
          <aside
            className="qh-home-sidebar"
            data-open={sidebarOpen}
            aria-label="Project navigation"
          >
            <div className="mb-2 flex items-center justify-between lg:hidden">
              <span className="qh-side-title mb-0">Workspace</span>
              <button
                type="button"
                className="qh-btn qh-btn-sm"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close navigation"
              >
                ✕
              </button>
            </div>

            <nav className="qh-sidebar-section" aria-label="Workspace">
              <Link to="/" className="qh-sidebar-item" data-active="true">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M6.906.664a1.749 1.749 0 0 1 2.187 0l5.25 4.2c.415.332.657.835.657 1.367v7.019A1.75 1.75 0 0 1 13.25 15h-3.5a.75.75 0 0 1-.75-.75V9H7v5.25a.75.75 0 0 1-.75.75h-3.5A1.75 1.75 0 0 1 1 13.25V6.23c0-.531.242-1.034.657-1.366Z" />
                </svg>
                Home
              </Link>
              <Link to="/community" className="qh-sidebar-item">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M1.75 1h8.5c.966 0 1.75.784 1.75 1.75v5a1.75 1.75 0 0 1-1.75 1.75H9.81l1.018 1.018a.75.75 0 1 1-1.06 1.06L6.939 9.75H1.75A1.75 1.75 0 0 1 0 8V2.75C0 1.784.784 1 1.75 1Z" />
                  <path d="M12.5 4H14a1.75 1.75 0 0 1 1.75 1.75v5a1.75 1.75 0 0 1-1.75 1.75h-.31l1.018 1.018a.75.75 0 1 1-1.06 1.06L11.689 12H7.5a1.75 1.75 0 0 1-1.75-1.75V9.5h.5c.4 0 .78-.08 1.13-.22l1.68 1.68a2.25 2.25 0 1 0 3.18-3.18L11.5 5.06c.24-.35.38-.73.38-1.14V4Z" />
                </svg>
                Community feed
              </Link>
              <Link to="/explore" className="qh-sidebar-item">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm7.25-5.5v1.31a4.5 4.5 0 0 0-2.47 1.03L3.85 3.91A6.47 6.47 0 0 1 7.25 2.5Zm-4.6 2.4 1.94 1.94a4.5 4.5 0 0 0-1.03 2.47H2.25a6.47 6.47 0 0 1 .4-4.4Zm.4 5.6a4.5 4.5 0 0 0 1.03 2.47l-.93.93A6.47 6.47 0 0 1 2.5 8.75h1.31Zm2.06 3.5a4.5 4.5 0 0 0 2.47 1.03v1.31a6.47 6.47 0 0 1-4.4-.4l1.93-1.94Zm4.97 1.03a4.5 4.5 0 0 0 2.47-1.03l1.94 1.93a6.47 6.47 0 0 1-4.4.4V14.9Zm3.5-2.06a4.5 4.5 0 0 0 1.03-2.47h1.31a6.47 6.47 0 0 1-.4 4.4l-1.94-1.93ZM14.75 7.25h-1.31a4.5 4.5 0 0 0-1.03-2.47l.93-.93a6.47 6.47 0 0 1 1.41 3.4Zm-2.06-3.5-1.94 1.94a4.5 4.5 0 0 0-2.47-1.03V2.5c1.62.13 3.1.7 4.4 1.4Z" />
                </svg>
                Explore
              </Link>
            </nav>

            <div className="qh-sidebar-section">
              <div className="mb-1 flex items-center justify-between px-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-[#6e7681]">
                  Top projects
                </span>
                <span className="flex items-center gap-1">
                  <Link
                    to="/explore"
                    className="rounded p-1 text-[#9198a1] hover:bg-[#161b22] hover:text-[#e6edf3]"
                    title="Search projects"
                    aria-label="Search projects"
                  >
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                      <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z" />
                    </svg>
                  </Link>
                  <Link
                    to="/new"
                    className="qh-btn qh-btn-sm qh-btn-primary"
                    title="Create a new project"
                  >
                    New
                  </Link>
                </span>
              </div>

              {loading && (
                <div className="space-y-2 px-1 py-2">
                  {[0, 1, 2].map((index) => (
                    <Skeleton key={index} height={18} width={`${80 - index * 10}%`} />
                  ))}
                </div>
              )}

              {!loading && error && (
                <p className="m-0 px-2 py-1 text-[12px] text-[#f85149]">
                  Projects unavailable. <button type="button" className="underline" onClick={load}>Retry</button>
                </p>
              )}

              {!loading && !error && myProjects.length === 0 && (
                <p className="m-0 px-2 py-1 text-[12px] text-[#9198a1]">
                  No projects yet. <Link to="/new">Create your first project</Link>.
                </p>
              )}

              {!loading &&
                !error &&
                myProjects.map((project) => (
                  <Link
                    key={project.id}
                    to={`/${project.owner.handle}/${project.slug}`}
                    className="qh-project-row"
                    title={`${project.full_name} · ${project.visibility}`}
                  >
                    <span className="text-[#8b949e]">
                      {project.visibility === "private" ? <LockIcon size={13} /> : <RepoIcon size={14} />}
                    </span>
                    <span>{project.name}</span>
                    {project.visibility === "private" && (
                      <span className="ml-auto text-[10px] uppercase text-[#e3b341]">private</span>
                    )}
                  </Link>
                ))}

              {!loading && !error && myProjects.length > 0 && (
                <Link to="/projects" className="mt-1 block px-2 text-[12px]">
                  View all your projects →
                </Link>
              )}
            </div>

            <div className="qh-sidebar-section">
              <span className="mb-1 block px-2 text-[11px] font-semibold uppercase tracking-wide text-[#6e7681]">
                Community
              </span>
              {topProjects.slice(0, 4).map((project) => (
                <Link
                  key={project.id}
                  to={`/${project.owner.handle}/${project.slug}`}
                  className="qh-project-row"
                >
                  <span className="text-[#8b949e]"><RepoIcon size={14} /></span>
                  <span>{project.full_name}</span>
                </Link>
              ))}
              {!loading && topProjects.length === 0 && (
                <p className="m-0 px-2 text-[12px] text-[#9198a1]">
                  No public projects yet. <Link to="/new">Publish one</Link>.
                </p>
              )}
            </div>
          </aside>

          {/* ---------------------------------------------------------- */}
          {/* Center dashboard                                           */}
          {/* ---------------------------------------------------------- */}
          <div className="min-w-0 space-y-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="qh-dash-greeting">
                  {sessionLoading ? "Loading…" : `Welcome back, ${displayName.split(" ")[0]}`}
                </h1>
                <p className="qh-subtle m-0">
                  Projects hold your code, circuits, experiments and evidence.
                </p>
              </div>
              <button
                type="button"
                className="qh-btn qh-btn-sm lg:hidden"
                onClick={() => setSidebarOpen((open) => !open)}
                aria-expanded={sidebarOpen}
              >
                ☰ Projects
              </button>
            </div>

            {viewer && viewer.mode === "local" && (
              <p className="qh-card m-0 px-4 py-2 text-[12px] text-[#e3b341]">
                Local session: projects are stored by this QuantHub server under the handle{" "}
                <strong>@{viewer.handle}</strong>. Configure Firebase to sign in with a verified
                account.
              </p>
            )}

            {error && <ErrorState message={error} onRetry={load} />}

            <div className="qh-two-col">
              <div className="qh-card qh-card-body flex flex-col gap-3">
                <div>
                  <h2 className="qh-heading m-0">Create a project</h2>
                  <p className="qh-subtle m-0">
                    Start with a README, .gitignore and license, then add code and experiments.
                  </p>
                </div>
                <div className="mt-auto flex flex-wrap gap-2">
                  <Link to="/new" className="qh-btn qh-btn-primary">
                    New project
                  </Link>
                  <Link to="/new?mode=import" className="qh-btn">
                    Import existing project
                  </Link>
                </div>
              </div>

              <div className="qh-card qh-card-body flex flex-col gap-3">
                <div>
                  <h2 className="qh-heading m-0">Start an experiment</h2>
                  <p className="qh-subtle m-0">
                    Configure a QEC protocol against a project and run it on the scientific engine.
                  </p>
                </div>
                <div className="mt-auto flex flex-wrap gap-2">
                  <Link to="/qec" className="qh-btn qh-btn-accent">
                    QEC Workbench
                  </Link>
                  <Link to="/app" className="qh-btn">
                    Circuit Designer
                  </Link>
                </div>
              </div>
            </div>

            <section className="qh-card" aria-labelledby="qh-recent-projects">
              <div className="qh-card-header">
                <h2 id="qh-recent-projects" className="m-0 text-[13px] font-semibold">
                  Recently opened
                </h2>
                <Link to="/projects" className="text-[12px]">
                  All projects
                </Link>
              </div>
              {recent.length === 0 ? (
                <EmptyState
                  title="Nothing opened yet"
                  description="Projects you open appear here for quick access."
                  action={
                    <Link to="/new" className="qh-btn qh-btn-sm">
                      Create a project
                    </Link>
                  }
                />
              ) : (
                <ul className="m-0 list-none p-0">
                  {recent.slice(0, 5).map((item) => {
                    const [owner, slug] = item.full_name.split("/");
                    return (
                      <li key={item.full_name} className="qh-list-row">
                        <span className="text-[#8b949e]">
                          {item.visibility === "private" ? <LockIcon size={13} /> : <RepoIcon size={14} />}
                        </span>
                        <Link to={`/${owner}/${slug}`} className="font-medium">
                          {item.full_name}
                        </Link>
                        <span className="truncate text-[#6e7681]">{item.name}</span>
                        <span className="ml-auto shrink-0 text-[11px] text-[#6e7681]">
                          <RelativeTime value={item.opened_at} />
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="qh-card" aria-labelledby="qh-recent-runs">
              <div className="qh-card-header">
                <h2 id="qh-recent-runs" className="m-0 text-[13px] font-semibold">
                  Recent experiment runs
                </h2>
                <Link to="/experiments" className="text-[12px]">
                  All runs
                </Link>
              </div>
              {loading ? (
                <div className="p-4">
                  <LoadingPanel rows={2} />
                </div>
              ) : (data?.recent_runs.length ?? 0) === 0 ? (
                <EmptyState
                  title="No runs yet"
                  description="Runs you execute in the QEC Workbench appear here with their config hash and status."
                />
              ) : (
                <ul className="m-0 list-none p-0">
                  {data?.recent_runs.map((run) => (
                    <li key={run.id} className="qh-list-row">
                      <RunStatusPill status={run.status} />
                      <Link
                        to={`/${run.project.full_name}/runs/${run.id}`}
                        className="qh-mono font-medium"
                      >
                        {run.id}
                      </Link>
                      <span className="truncate text-[#6e7681]">{run.project.full_name}</span>
                      <span className="ml-auto shrink-0 text-[11px] text-[#6e7681]">
                        <RelativeTime value={run.created_at} />
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <div className="qh-three-col">
              <Link to="/app" className="qh-tool-card">
                <span className="text-[13px] font-semibold">Circuit Designer</span>
                <span className="text-[12px] text-[#9198a1]">
                  Build circuits, run state-vector or density-matrix simulation, inspect math.
                </span>
              </Link>
              <Link to="/qec" className="qh-tool-card">
                <span className="text-[13px] font-semibold">QEC Workbench</span>
                <span className="text-[12px] text-[#9198a1]">
                  Configure decoders, run experiments, verify artifacts and provenance.
                </span>
              </Link>
              <Link to="/algorithms" className="qh-tool-card">
                <span className="text-[13px] font-semibold">Algorithms &amp; docs</span>
                <span className="text-[12px] text-[#9198a1]">
                  Reference material for gates, algorithms and reproducibility practice.
                </span>
              </Link>
            </div>

            <section className="qh-card" aria-labelledby="qh-activity">
              <div className="qh-card-header">
                <h2 id="qh-activity" className="m-0 text-[13px] font-semibold">
                  Activity
                </h2>
                <span className="qh-muted">Across projects you can access</span>
              </div>
              {loading ? (
                <div className="p-4">
                  <LoadingPanel rows={3} />
                </div>
              ) : (data?.activity.length ?? 0) === 0 ? (
                <EmptyState title="No activity yet" description="Project and experiment events appear here." />
              ) : (
                <ul className="m-0 list-none p-0">
                  {data?.activity.slice(0, 8).map((event) => (
                    <li key={event.id} className="qh-list-row">
                      <span className="font-medium">{event.actor ?? "system"}</span>
                      <span className="min-w-0 flex-1 truncate text-[#9198a1]">{activityText(event)}</span>
                      <span className="shrink-0 text-[11px] text-[#6e7681]">
                        <RelativeTime value={event.created_at} />
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* ---------------------------------------------------------- */}
          {/* Right sidebar                                              */}
          {/* ---------------------------------------------------------- */}
          <aside className="qh-home-right space-y-4" aria-label="Community news">
            <NewsPanel
              feed={data?.news ?? null}
              loading={loading}
              error={error}
              onRetry={load}
              limit={5}
            />
            <section className="qh-card qh-card-body">
              <h2 className="qh-heading mb-2 mt-0">Research shortcuts</h2>
              <ul className="m-0 list-none space-y-1 p-0 text-[13px]">
                <li><Link to="/research">Research overview</Link></li>
                <li><Link to="/docs">Documentation</Link></li>
                <li><Link to="/learn">Learn quantum computing</Link></li>
                <li><Link to="/api">API reference</Link></li>
                <li><Link to="/history">Circuit history</Link></li>
              </ul>
            </section>
          </aside>
        </div>
      </div>
    </>
  );
}
