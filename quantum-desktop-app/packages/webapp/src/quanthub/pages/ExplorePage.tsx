import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api } from "../client";
import { useAsync } from "../hooks";
import type { ProjectList } from "../types";
import { ProjectCard } from "../components/ProjectCard";
import { EmptyState, ErrorState, LoadingPanel } from "../components/ui";

const SORTS = [
  { id: "recent", label: "Recently updated" },
  { id: "stars", label: "Most starred" },
  { id: "name", label: "Name" },
] as const;

export default function ExplorePage(): JSX.Element {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const topic = params.get("topic") ?? "";
  const language = params.get("language") ?? "";
  const sort = (params.get("sort") ?? "recent") as (typeof SORTS)[number]["id"];
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const [draft, setDraft] = useState(q);

  useEffect(() => setDraft(q), [q]);

  const queryString = useMemo(() => {
    const search = new URLSearchParams();
    search.set("view", "discover");
    search.set("page", String(page));
    search.set("sort", sort);
    if (q) search.set("q", q);
    if (topic) search.set("topic", topic);
    if (language) search.set("language", language);
    return search.toString();
  }, [page, sort, q, topic, language]);

  const state = useAsync(
    (signal) => api<ProjectList>(`/projects?${queryString}`, { signal }),
    [queryString],
  );

  const update = (next: Record<string, string | null>) => {
    const search = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === "") search.delete(key);
      else search.set(key, value);
    }
    if (!("page" in next)) search.delete("page");
    setParams(search, { replace: false });
  };

  return (
    <>
      <PageMeta
        title="Explore projects"
        description="Discover public QuantHub projects, quantum software and reproducible experiments."
      />
      <div className="qh-container py-6">
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="m-0 text-[20px] font-semibold">Explore projects</h1>
            <p className="qh-subtle m-0">
              Public projects, quantum software and reproducible experiments.
            </p>
          </div>
          <form
            className="flex w-full max-w-md gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              update({ q: draft.trim() || null, page: null });
            }}
            role="search"
          >
            <input
              className="qh-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Search name, description or topic"
              aria-label="Search projects"
            />
            <button type="submit" className="qh-btn qh-btn-primary">
              Search
            </button>
          </form>
        </header>

        <div className="mb-4 flex flex-wrap items-center gap-2 text-[12px]">
          <span className="text-[#6e7681]">Sort:</span>
          {SORTS.map((option) => (
            <button
              key={option.id}
              type="button"
              className="qh-btn qh-btn-sm"
              data-active={sort === option.id}
              style={sort === option.id ? { borderColor: "#58a6ff", color: "#79c0ff" } : undefined}
              onClick={() => update({ sort: option.id, page: null })}
            >
              {option.label}
            </button>
          ))}
          {topic && (
            <span className="qh-topic inline-flex items-center gap-1">
              topic: {topic}
              <button
                type="button"
                aria-label="Clear topic filter"
                className="border-0 bg-transparent p-0 text-[#e6edf3]"
                onClick={() => update({ topic: null })}
              >
                ×
              </button>
            </span>
          )}
          {language && (
            <span className="qh-topic inline-flex items-center gap-1">
              language: {language}
              <button
                type="button"
                aria-label="Clear language filter"
                className="border-0 bg-transparent p-0 text-[#e6edf3]"
                onClick={() => update({ language: null })}
              >
                ×
              </button>
            </span>
          )}
          {(q || topic || language) && (
            <Link to="/explore" className="qh-muted ml-1 underline">
              Reset
            </Link>
          )}
        </div>

        {state.loading && !state.data && <LoadingPanel rows={5} />}
        {state.error && (
          <ErrorState message={state.error.message} onRetry={state.reload} />
        )}

        {state.data && state.data.items.length === 0 && (
          <EmptyState
            title={q || topic || language ? "No projects match those filters" : "No public projects yet"}
            description={
              q || topic || language
                ? "Try a broader search, or clear the filters to browse everything."
                : "Projects appear here once someone publishes one. Create the first project."
            }
            action={
              <Link to="/new" className="qh-btn qh-btn-primary">
                New project
              </Link>
            }
          />
        )}

        {state.data && state.data.items.length > 0 && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {state.data.items.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between text-[12px] text-[#8b949e]">
              <span>
                {state.data.total} project{state.data.total === 1 ? "" : "s"}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="qh-btn qh-btn-sm"
                  disabled={page <= 1}
                  onClick={() => update({ page: String(page - 1) })}
                >
                  Previous
                </button>
                <span>Page {state.data.page}</span>
                <button
                  type="button"
                  className="qh-btn qh-btn-sm"
                  disabled={!state.data.has_more}
                  onClick={() => update({ page: String(page + 1) })}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
