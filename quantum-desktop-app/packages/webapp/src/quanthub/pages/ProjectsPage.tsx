import { useState } from "react";
import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api } from "../client";
import { useAsync } from "../hooks";
import type { ProjectList } from "../types";
import { ProjectCard } from "../components/ProjectCard";
import { EmptyState, ErrorState, LoadingPanel } from "../components/ui";

export default function ProjectsPage(): JSX.Element {
  const [view, setView] = useState<"mine" | "starred">("mine");
  const state = useAsync(
    (signal) => api<ProjectList>(`/projects?view=${view}&per_page=60`, { signal }),
    [view],
  );

  return (
    <>
      <PageMeta title="Your projects" description="Projects you own or contribute to on QuantHub." />
      <div className="qh-container py-6">
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">Your projects</h1>
            <p className="qh-subtle m-0">Everything you own, maintain or have starred.</p>
          </div>
          <Link to="/new" className="qh-btn qh-btn-primary">
            New project
          </Link>
        </header>

        <div className="qh-tabs mb-4" role="tablist" aria-label="Project views">
          <button
            type="button"
            role="tab"
            aria-selected={view === "mine"}
            className="qh-tab"
            data-active={view === "mine"}
            onClick={() => setView("mine")}
          >
            Owned & contributing
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "starred"}
            className="qh-tab"
            data-active={view === "starred"}
            onClick={() => setView("starred")}
          >
            Starred
          </button>
        </div>

        {state.loading && !state.data && <LoadingPanel rows={4} />}
        {state.error && <ErrorState message={state.error.message} onRetry={state.reload} />}
        {state.data && state.data.items.length === 0 && (
          <EmptyState
            title={view === "mine" ? "You have no projects yet" : "No starred projects"}
            description={
              view === "mine"
                ? "Create a project to store code, circuits, and reproducible experiments."
                : "Star projects you want to follow; they will be listed here."
            }
            action={
              view === "mine" ? (
                <Link to="/new" className="qh-btn qh-btn-primary">
                  New project
                </Link>
              ) : (
                <Link to="/explore" className="qh-btn">
                  Explore projects
                </Link>
              )
            }
          />
        )}
        {state.data && state.data.items.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {state.data.items.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
