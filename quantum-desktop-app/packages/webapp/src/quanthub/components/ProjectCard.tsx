import { Link } from "react-router-dom";
import type { ProjectSummary } from "../types";
import { LanguageDot, LockIcon, RelativeTime, RepoIcon, VisibilityBadge } from "./ui";

export function ProjectCard({ project }: { project: ProjectSummary }): JSX.Element {
  return (
    <article className="qh-card flex h-full flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-[#8b949e]">
            <RepoIcon size={15} />
          </span>
          <Link
            to={`/${project.owner.handle}/${project.slug}`}
            className="truncate text-[14px] font-semibold text-[#79c0ff]"
          >
            {project.full_name}
          </Link>
        </div>
        {project.visibility === "private" ? (
          <span className="qh-badge qh-badge-private" title="Private project">
            <LockIcon size={10} /> Private
          </span>
        ) : (
          <VisibilityBadge visibility="public" />
        )}
      </div>

      <p className="m-0 line-clamp-2 min-h-[34px] text-[13px] text-[#9198a1]">
        {project.description || "No description provided yet."}
      </p>

      {project.topics.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {project.topics.slice(0, 4).map((topic) => (
            <Link key={topic} to={`/explore?topic=${encodeURIComponent(topic)}`} className="qh-topic">
              {topic}
            </Link>
          ))}
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#6e7681]">
        <LanguageDot label={project.language} />
        <span>Updated <RelativeTime value={project.updated_at} /></span>
        {project.stars > 0 && <span>★ {project.stars}</span>}
        {project.kinds?.includes("experiments") && <span className="qh-badge">experiments</span>}
      </div>
    </article>
  );
}
