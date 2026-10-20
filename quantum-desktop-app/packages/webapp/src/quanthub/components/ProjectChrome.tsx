import { useEffect, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, rememberProject } from "../client";
import { useAsync } from "../hooks";
import type { ProjectDetail } from "../types";
import { ProjectSidebar } from "./ProjectSidebar";
import { ErrorState, LoadingPanel, LockIcon, RepoIcon } from "./ui";

export type ProjectTab = "code" | "commits" | "experiments" | "runs" | "import" | "settings";

const TABS: Array<{ id: ProjectTab; label: string }> = [
  { id: "code", label: "Code" },
  { id: "commits", label: "Commits" },
  { id: "experiments", label: "Experiments" },
  { id: "runs", label: "Runs" },
  { id: "import", label: "Import" },
  { id: "settings", label: "Settings" },
];

export function ProjectChrome({
  owner,
  slug,
  tab,
  children,
}: {
  owner: string;
  slug: string;
  tab: ProjectTab;
  children: (project: ProjectDetail, reload: () => void) => ReactNode;
}): JSX.Element {
  const navigate = useNavigate();
  const state = useAsync(
    (signal) => api<ProjectDetail>(`/projects/${owner}/${slug}`, { signal }),
    [owner, slug],
  );

  useEffect(() => {
    if (state.data) {
      rememberProject({
        full_name: state.data.full_name,
        name: state.data.name,
        visibility: state.data.visibility,
      });
    }
  }, [state.data]);

  if (state.loading && !state.data) {
    return (
      <div className="qh-container py-6">
        <LoadingPanel rows={5} />
      </div>
    );
  }
  if (state.error) {
    return (
      <div className="qh-container py-6">
        <ErrorState
          message={state.error.message}
          onRetry={() => {
            if (state.error && "status" in state.error && state.error.status === 404) {
              navigate("/explore");
            }
            state.reload();
          }}
        />
      </div>
    );
  }
  if (!state.data) return <></>;
  const project = state.data;
  const base = `/${project.owner.handle}/${project.slug}`;

  const visibleTabs = TABS.filter((item) => {
    if (item.id === "settings") return project.viewer.can_admin;
    if (item.id === "import") return project.viewer.can_write;
    return true;
  });

  return (
    <div className="qh-container py-5">
      <nav className="qh-muted mb-2 text-[12px]" aria-label="Breadcrumb">
        <Link to="/">Home</Link> /{" "}
        <Link to={`/explore?owner=${encodeURIComponent(project.owner.handle)}`}>
          {project.owner.handle}
        </Link>{" "}
        / <span>{project.slug}</span>
      </nav>

      <header className="qh-project-header">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-[#8b949e]" aria-hidden="true">
            <RepoIcon size={18} />
          </span>
          <h1 className="m-0 truncate text-[20px] font-semibold">
            <Link to={`/${project.owner.handle}`} className="text-[#79c0ff] hover:underline">
              {project.owner.handle}
            </Link>
            <span className="text-[#6e7681]"> / </span>
            <Link to={base} className="text-[#79c0ff] hover:underline">
              {project.slug}
            </Link>
          </h1>
          {project.visibility === "private" ? (
            <span className="qh-badge qh-badge-private">
              <LockIcon size={10} /> Private
            </span>
          ) : (
            <span className="qh-badge qh-badge-public">Public</span>
          )}
          {project.archived && <span className="qh-badge">Archived</span>}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="qh-btn qh-btn-sm"
            onClick={() => navigate(`${base}/import`)}
            disabled={!project.viewer.can_write}
            title={project.viewer.can_write ? "Upload files" : "Read-only access"}
          >
            Import files
          </button>
          <Link
            to={`/qec?project=${encodeURIComponent(project.full_name)}`}
            className="qh-btn qh-btn-sm qh-btn-primary"
          >
            QEC Workbench
          </Link>
        </div>
      </header>

      <div className="qh-tabs mb-4" role="tablist" aria-label="Project sections">
        {visibleTabs.map((item) => (
          <Link
            key={item.id}
            to={item.id === "code" ? base : `${base}/${item.id}`}
            role="tab"
            aria-selected={tab === item.id}
            className="qh-tab"
            data-active={tab === item.id}
          >
            {item.label}
            {item.id === "experiments" && project.experiment_count > 0 && (
              <span className="ml-1 text-[11px] text-[#6e7681]">{project.experiment_count}</span>
            )}
            {item.id === "runs" && project.run_count > 0 && (
              <span className="ml-1 text-[11px] text-[#6e7681]">{project.run_count}</span>
            )}
          </Link>
        ))}
      </div>

      {project.archived && (
        <div className="qh-form-error mb-4">
          This project is archived and read-only. Files, experiments and runs remain available.
        </div>
      )}

      {!project.viewer.can_write && (
        <p className="qh-help mb-3">
          You have read-only access. Editing, importing and running require a maintainer role.
        </p>
      )}

      <div className="qh-project-layout">
        <div className="min-w-0">{children(project, state.reload)}</div>
        <ProjectSidebar project={project} />
      </div>
    </div>
  );
}
