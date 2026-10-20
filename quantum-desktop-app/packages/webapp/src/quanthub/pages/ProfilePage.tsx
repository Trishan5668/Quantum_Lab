import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, formatDate } from "../client";
import { useAsync } from "../hooks";
import { useSession } from "../session";
import type { ProjectList } from "../types";
import { ProjectCard } from "../components/ProjectCard";
import { EmptyState, ErrorState, LoadingPanel, LockIcon } from "../components/ui";

export default function ProfilePage(): JSX.Element {
  const { handle } = useParams();
  const { viewer, identity, usingFirebase } = useSession();
  const target = handle ?? viewer?.handle ?? identity.handle;
  const isSelf = Boolean(viewer && target === viewer.handle);

  const projects = useAsync(
    (signal) =>
      api<ProjectList>(
        `/projects?view=${isSelf ? "mine" : "discover"}&owner=${encodeURIComponent(target)}&per_page=30`,
        { signal },
      ),
    [target, isSelf],
  );

  return (
    <>
      <PageMeta title={`@${target}`} description={`Projects published by @${target} on QuantHub.`} />
      <div className="qh-container py-6">
        <header className="mb-5 flex flex-wrap items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[#30363d] bg-[#21262d] text-2xl font-semibold">
            {target.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <h1 className="m-0 text-[20px] font-semibold">{isSelf ? viewer?.display_name ?? identity.display_name : target}</h1>
            <p className="qh-subtle m-0 text-[13px]">@{target}</p>
            <p className="m-0 mt-1 text-[12px] text-[#8b949e]">
              {isSelf ? (
                usingFirebase ? (
                  "Signed in with a Firebase account."
                ) : (
                  <span className="inline-flex items-center gap-1">
                    <LockIcon size={10} /> Local session — this identity is stored in this browser only.
                  </span>
                )
              ) : (
                "Public profile"
              )}
            </p>
          </div>
          {isSelf && (
            <div className="ml-auto flex gap-2">
              <Link to="/new" className="qh-btn qh-btn-primary">
                New project
              </Link>
              <Link to="/settings" className="qh-btn">
                Account settings
              </Link>
            </div>
          )}
        </header>

        <section>
          <h2 className="mb-3 text-[15px] font-semibold">
            {isSelf ? "Your projects" : "Public projects"}
          </h2>
          {projects.loading && !projects.data && <LoadingPanel rows={4} />}
          {projects.error && (
            <ErrorState message={projects.error.message} onRetry={projects.reload} />
          )}
          {projects.data && projects.data.items.length === 0 && (
            <EmptyState
              title={isSelf ? "No projects yet" : "No public projects"}
              description={
                isSelf
                  ? "Create a project to publish quantum software and reproducible experiments."
                  : "This identity has no public projects, or they are all private."
              }
              action={
                isSelf ? (
                  <Link to="/new" className="qh-btn qh-btn-primary">
                    New project
                  </Link>
                ) : undefined
              }
            />
          )}
          {projects.data && projects.data.items.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {projects.data.items.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          )}
        </section>

        {isSelf && viewer && (
          <section className="mt-6">
            <h2 className="mb-2 text-[15px] font-semibold">Account</h2>
            <dl className="qh-card qh-card-body grid gap-2 text-[12px] sm:grid-cols-2">
              <div>
                <dt className="text-[#6e7681]">Handle</dt>
                <dd className="m-0 qh-mono">@{viewer.handle}</dd>
              </div>
              <div>
                <dt className="text-[#6e7681]">Email</dt>
                <dd className="m-0">{viewer.email ?? "not set"}</dd>
              </div>
              <div>
                <dt className="text-[#6e7681]">Authentication</dt>
                <dd className="m-0">{viewer.mode}</dd>
              </div>
              <div>
                <dt className="text-[#6e7681]">Member since</dt>
                <dd className="m-0">{viewer.profile ? formatDate(viewer.profile.created_at) : "—"}</dd>
              </div>
            </dl>
          </section>
        )}
      </div>
    </>
  );
}
