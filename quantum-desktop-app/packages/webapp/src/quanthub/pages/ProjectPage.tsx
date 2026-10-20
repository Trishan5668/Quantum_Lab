import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, formatRelativeTime } from "../client";
import { useAsync } from "../hooks";
import type { ProjectDetail, TreePayload } from "../types";
import { ProjectChrome } from "../components/ProjectChrome";
import { FileBrowser } from "../components/FileBrowser";
import { Markdown } from "../components/Markdown";
import { ErrorState, LoadingPanel } from "../components/ui";

function LatestCommit({ project }: { project: ProjectDetail }): JSX.Element | null {
  const commit = project.latest_commit;
  if (!commit) return null;
  return (
    <div className="qh-card mb-4 flex flex-wrap items-center justify-between gap-2 px-4 py-2 text-[12px]">
      <div className="flex min-w-0 items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#1f6feb] text-[10px] font-semibold text-white">
          {commit.author_name.slice(0, 1).toUpperCase()}
        </span>
        <span className="font-semibold text-[#c9d1d9]">{commit.author_name}</span>
        <span className="truncate text-[#8b949e]">{commit.message}</span>
      </div>
      <div className="flex items-center gap-3 text-[#8b949e]">
        <Link to={`/${project.owner.handle}/${project.slug}/commits`} className="qh-mono text-[#79c0ff]">
          {commit.sha.slice(0, 7)}
        </Link>
        <span>{formatRelativeTime(commit.authored_at)}</span>
        <span>
          {project.commit_count} commit{project.commit_count === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}

function CodeTab({ owner, slug, project }: { owner: string; slug: string; project: ProjectDetail }): JSX.Element {
  const [params] = useSearchParams();
  const path = params.get("path") ?? "";
  const tree = useAsync(
    (signal) =>
      api<TreePayload>(
        `/projects/${owner}/${slug}/tree?path=${encodeURIComponent(path)}`,
        { signal },
      ),
    [owner, slug, path, project.revision],
  );

  const readme = project.readme;
  return (
    <div className="space-y-4">
      <LatestCommit project={project} />
      {tree.loading && !tree.data ? (
        <LoadingPanel rows={4} />
      ) : tree.error ? (
        <ErrorState message={tree.error.message} onRetry={tree.reload} />
      ) : (
        <FileBrowser
          base={`/${owner}/${slug}`}
          path={tree.data?.path ?? path}
          entries={tree.data?.entries ?? []}
          revision={tree.data?.revision ?? project.revision}
          emptyMessage="This project has no files yet. Import existing code or create a file."
        />
      )}

      {path === "" && readme && readme.content && (
        <div className="qh-card">
          <div className="qh-card-header flex items-center gap-2">
            <span aria-hidden="true">📄</span>
            <span className="text-[13px] font-semibold">{readme.path}</span>
            <Link
              to={`/${owner}/${slug}/blob/${readme.path}`}
              className="ml-auto text-[12px] text-[#79c0ff]"
            >
              View source
            </Link>
          </div>
          <div className="qh-card-body">
            <Markdown source={readme.content} />
          </div>
        </div>
      )}
      {path === "" && readme?.too_large && (
        <p className="qh-help">
          {readme.path} is too large to render inline;{" "}
          <Link to={`/${owner}/${slug}/blob/${readme.path}`} className="text-[#79c0ff]">
            open the raw file
          </Link>
          .
        </p>
      )}
    </div>
  );
}

function NewFilePanel({ owner, slug, project, onCreated }: {
  owner: string;
  slug: string;
  project: ProjectDetail;
  onCreated: () => void;
}): JSX.Element {
  const [open, setOpen] = useState(false);
  const [path, setPath] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!project.viewer.can_write) return <></>;

  async function save(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await api(`/projects/${owner}/${slug}/contents`, {
        method: "PUT",
        body: {
          path,
          content: "",
          message: message || `Create ${path}`,
          expected_revision: project.revision,
        },
      });
      setOpen(false);
      setPath("");
      setMessage("");
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The file could not be created.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mb-4">
      {!open ? (
        <button type="button" className="qh-btn qh-btn-sm" onClick={() => setOpen(true)}>
          New file
        </button>
      ) : (
        <form
          className="qh-card qh-card-body"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="qh-two-col">
            <div className="qh-field">
              <label className="qh-label" htmlFor="new-file-path">
                File path
              </label>
              <input
                id="new-file-path"
                className="qh-input qh-mono"
                value={path}
                onChange={(event) => setPath(event.target.value)}
                placeholder="src/experiment.py"
                required
              />
            </div>
            <div className="qh-field">
              <label className="qh-label" htmlFor="new-file-message">
                Commit message
              </label>
              <input
                id="new-file-message"
                className="qh-input"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Add file"
              />
            </div>
          </div>
          {error && <p className="qh-error-text">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="qh-btn qh-btn-primary" disabled={busy || !path.trim()}>
              {busy ? "Creating…" : "Create file"}
            </button>
            <button type="button" className="qh-btn" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function ProjectPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();

  return (
    <>
      <PageMeta title={`${owner}/${slug}`} description="A QuantHub quantum software project." />
      <ProjectChrome owner={owner} slug={slug} tab="code">
        {(project, reload) => (
          <>
            <NewFilePanel owner={owner} slug={slug} project={project} onCreated={reload} />
            <CodeTab owner={owner} slug={slug} project={project} />
          </>
        )}
      </ProjectChrome>
    </>
  );
}
