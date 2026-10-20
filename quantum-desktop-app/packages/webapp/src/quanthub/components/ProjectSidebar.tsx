import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../client";
import type { ActivityEvent, ProjectDetail } from "../types";
import { formatRelativeTime } from "../client";
import { LockIcon, VisibilityBadge } from "./ui";

function ActivityLine({ event }: { event: ActivityEvent }): JSX.Element {
  const payload = event.payload ?? {};
  const detail =
    typeof payload.message === "string"
      ? payload.message
      : typeof payload.revision === "string"
        ? payload.revision.slice(0, 7)
        : "";
  return (
    <li className="qh-list-row text-[12px]">
      <span className="text-[#9198a1]">
        <strong className="font-semibold text-[#c9d1d9]">{event.actor}</strong>{" "}
        {event.type.replace(/\./g, " ").replace(/_/g, " ")}
        {detail && <> · <span className="qh-mono">{detail}</span></>}
      </span>
      <span className="shrink-0 text-[#6e7681]">{formatRelativeTime(event.created_at)}</span>
    </li>
  );
}

export function ProjectSidebar({ project }: { project: ProjectDetail }): JSX.Element {
  const [starred, setStarred] = useState(project.viewer.starred);
  const [stars, setStars] = useState(project.stars);
  const [watched, setWatched] = useState(project.viewer.watched);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[] | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [showActivity, setShowActivity] = useState(false);

  const base = `/projects/${project.owner.handle}/${project.slug}`;

  async function toggle(next: boolean): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      if (next) {
        const result = await api<{ stars: number }>(`${base}/star`, {
          body: { starred: true },
        });
        setStarred(true);
        setStars(result.stars ?? stars + 1);
      } else {
        const result = await api<{ stars: number }>(`${base}/star`, {
          body: { starred: false },
        });
        setStarred(false);
        setStars(result.stars ?? Math.max(0, stars - 1));
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not update the star.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleWatch(): Promise<void> {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api(`${base}/watch`, { body: { watching: !watched } });
      setWatched(!watched);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not update the watch.");
    } finally {
      setBusy(false);
    }
  }

  async function loadActivity(): Promise<void> {
    if (showActivity) {
      setShowActivity(false);
      return;
    }
    setShowActivity(true);
    if (activity) return;
    try {
      const result = await api<{ activity: ActivityEvent[] }>(`${base}/activity?limit=12`);
      setActivity(result.activity);
    } catch (cause) {
      setActivityError(cause instanceof Error ? cause.message : "Activity unavailable.");
    }
  }

  return (
    <aside className="qh-side-panel">
      <section>
        <h2 className="qh-side-title">About</h2>
        <p className="m-0 text-[13px] text-[#c9d1d9]">
          {project.description || "No description has been added to this project."}
        </p>
        {project.website && (
          <p className="mt-2 text-[13px]">
            <a
              href={project.website}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="text-[#79c0ff] underline"
            >
              {project.website.replace(/^https?:\/\//, "")}
            </a>
          </p>
        )}
        {project.topics.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {project.topics.map((topic) => (
              <Link key={topic} to={`/explore?topic=${encodeURIComponent(topic)}`} className="qh-topic">
                {topic}
              </Link>
            ))}
          </div>
        )}

        <div className="mt-3 space-y-1.5 text-[12px] text-[#9198a1]">
          <div className="flex items-center gap-1.5">
            {project.visibility === "public" ? <VisibilityBadge visibility="public" /> : (
              <span className="qh-badge qh-badge-private"><LockIcon size={10} /> Private</span>
            )}
            {project.archived && <span className="qh-badge">Archived</span>}
          </div>
          <div>
            <span className="font-semibold text-[#c9d1d9]">{project.experiment_count}</span>{" "}
            experiment{project.experiment_count === 1 ? "" : "s"} ·{" "}
            <span className="font-semibold text-[#c9d1d9]">{project.run_count}</span> runs
          </div>
          <div>
            {project.file_count} file{project.file_count === 1 ? "" : "s"} ·{" "}
            {project.commit_count} revision{project.commit_count === 1 ? "" : "s"}
          </div>
          {project.license ? (
            <div>License: {project.license}</div>
          ) : (
            <div className="text-[#e3b341]">No license specified</div>
          )}
          <div>Created {formatRelativeTime(project.created_at)}</div>
          <div>
            <Link to={`/${project.owner.handle}`} className="text-[#79c0ff]">
              @{project.owner.handle}
            </Link>
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            className="qh-btn qh-btn-sm"
            onClick={() => toggle(!starred)}
            disabled={busy}
            aria-pressed={starred}
          >
            <span aria-hidden="true">{starred ? "★" : "☆"}</span> {starred ? "Starred" : "Star"}{" "}
            <span className="text-[#9198a1]">{stars}</span>
          </button>
          <button
            type="button"
            className="qh-btn qh-btn-sm"
            onClick={toggleWatch}
            disabled={busy}
            aria-pressed={watched}
          >
            {watched ? "Watching" : "Watch"} · {project.watchers}
          </button>
        </div>
        {error && <p className="qh-error-text">{error}</p>}

        <button type="button" className="qh-btn qh-btn-sm mt-2 w-full" onClick={loadActivity}>
          {showActivity ? "Hide activity" : "Show activity"}
        </button>
        {showActivity && (
          <div className="mt-2">
            {activityError && <p className="qh-error-text">{activityError}</p>}
            {!activity && !activityError && (
              <p className="qh-help m-0">Loading activity…</p>
            )}
            {activity && activity.length === 0 && (
              <p className="qh-help m-0">No recorded activity yet.</p>
            )}
            {activity && activity.length > 0 && (
              <ul className="m-0 list-none p-0">
                {activity.map((event) => (
                  <ActivityLine key={event.id} event={event} />
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="qh-side-title">Experiments</h2>
        <Link
          to={`/qec?project=${encodeURIComponent(project.full_name)}`}
          className="qh-btn qh-btn-primary w-full justify-center"
        >
          QEC Workbench
        </Link>
        <p className="qh-help mb-0 mt-1">
          Configure, run and audit error-correction experiments on the Python engine.
        </p>
      </section>

      <section>
        <h2 className="qh-side-title">Tools</h2>
        <Link
          to={`/app/editor?project=${encodeURIComponent(project.full_name)}`}
          className="qh-btn w-full justify-center"
        >
          Circuit Designer
        </Link>
        <p className="qh-help mb-0 mt-1">
          Build and simulate circuits; saved circuits can live alongside this project's files.
        </p>
      </section>
    </aside>
  );
}
