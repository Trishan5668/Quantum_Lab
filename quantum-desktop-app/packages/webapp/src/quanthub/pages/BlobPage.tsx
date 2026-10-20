import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError, download, formatBytes, formatRelativeTime } from "../client";
import { useAsync } from "../hooks";
import type { BlobPayload, ProjectDetail } from "../types";
import { ProjectChrome } from "../components/ProjectChrome";
import { ErrorState, LoadingPanel, RunStatusPill } from "../components/ui";

function BinaryPreview({ owner, slug, path }: { owner: string; slug: string; path: string }): JSX.Element {
  const url = `/api/v1/projects/${owner}/${slug}/raw?path=${encodeURIComponent(path)}`;
  const image = /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(path);
  return (
    <div className="p-4 text-center text-[13px] text-[#9198a1]">
      {image ? (
        <img
          src={url}
          alt={`Preview of ${path}`}
          className="mx-auto max-h-[420px] max-w-full rounded border border-[#30363d]"
        />
      ) : (
        <p>This file is binary and cannot be displayed inline.</p>
      )}
      <button
        type="button"
        className="qh-btn qh-btn-sm mt-2"
        onClick={() => void download(`/projects/${owner}/${slug}/raw?path=${encodeURIComponent(path)}`, path.split("/").pop() || "file")}
      >
        Download file
      </button>
    </div>
  );
}

function BlobView({
  owner,
  slug,
  project,
  path,
}: {
  owner: string;
  slug: string;
  project: ProjectDetail;
  path: string;
}): JSX.Element {
  const blob = useAsync(
    (signal) =>
      api<BlobPayload>(
        `/projects/${owner}/${slug}/blob?path=${encodeURIComponent(path)}`,
        { signal },
      ),
    [owner, slug, path],
  );
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setEditing(false);
    setNotice(null);
    setError(null);
  }, [path]);

  if (blob.loading && !blob.data) return <LoadingPanel rows={6} />;
  if (blob.error) return <ErrorState message={blob.error.message} onRetry={blob.reload} />;
  if (!blob.data) return <></>;
  const file = blob.data;
  const editable = project.viewer.can_write && !file.binary && !file.too_large && !project.archived;

  async function save(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await api(`/projects/${owner}/${slug}/contents`, {
        method: "PUT",
        body: {
          path,
          content: draft,
          message: message || `Update ${path}`,
          expected_revision: file.revision,
        },
      });
      setEditing(false);
      setNotice("Saved as a new revision.");
      blob.reload();
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "RevisionConflict") {
        setError(
          "This file changed since you opened it. Reload to get the latest revision before saving.",
        );
      } else {
        setError(cause instanceof Error ? cause.message : "The file could not be saved.");
      }
    } finally {
      setBusy(false);
    }
  }

  const lines = (file.content ?? "").split("\n");

  return (
    <div className="space-y-3">
      <div className="qh-card overflow-hidden">
        <div className="qh-card-header flex flex-wrap items-center justify-between gap-2">
          <nav className="flex flex-wrap items-center gap-1 text-[13px]" aria-label="Breadcrumb">
            <Link to={`/${owner}/${slug}`} className="text-[#79c0ff]">
              {slug}
            </Link>
            {path.split("/").map((part, index, all) => {
              const target = all.slice(0, index + 1).join("/");
              const last = index === all.length - 1;
              return (
                <span key={target} className="flex items-center gap-1">
                  <span className="text-[#6e7681]">/</span>
                  {last ? (
                    <span className="font-semibold">{part}</span>
                  ) : (
                    <Link
                      to={`/${owner}/${slug}?path=${encodeURIComponent(all.slice(0, index + 1).join("/"))}`}
                      className="text-[#79c0ff]"
                    >
                      {part}
                    </Link>
                  )}
                </span>
              );
            })}
          </nav>
          <div className="flex items-center gap-2 text-[11px] text-[#8b949e]">
            <span>{file.language?.label ?? "Text"}</span>
            <span>{formatBytes(file.size)}</span>
            <span className="qh-mono">{file.revision.slice(0, 7)}</span>
          </div>
        </div>

        {file.binary || file.too_large ? (
          <BinaryPreview owner={owner} slug={slug} path={path} />
        ) : editing ? (
          <div className="p-3">
            <label className="qh-label" htmlFor="file-editor">
              Editing <span className="qh-mono">{path}</span>
            </label>
            <textarea
              id="file-editor"
              className="qh-textarea qh-mono"
              style={{ minHeight: 420, fontSize: 12 }}
              value={draft}
              spellCheck={false}
              onChange={(event) => setDraft(event.target.value)}
            />
            <div className="qh-field mt-2">
              <label className="qh-label" htmlFor="commit-message">
                Commit message
              </label>
              <input
                id="commit-message"
                className="qh-input"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={`Update ${path}`}
                maxLength={200}
              />
            </div>
            {error && <div className="qh-form-error mb-2">{error}</div>}
            <div className="flex gap-2">
              <button type="button" className="qh-btn qh-btn-primary" onClick={() => void save()} disabled={busy}>
                {busy ? "Saving…" : "Commit changes"}
              </button>
              <button
                type="button"
                className="qh-btn"
                onClick={() => {
                  setEditing(false);
                  setError(null);
                }}
              >
                Cancel
              </button>
              <Link to={`/${owner}/${slug}/commits?path=${encodeURIComponent(path)}`} className="qh-btn ml-auto">
                History
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-auto">
            <table className="qh-code w-full border-0" aria-label="File contents">
              <tbody>
                {lines.map((line, index) => (
                  <tr key={index}>
                    <td
                      className="select-none pr-3 text-right align-top text-[#484f58]"
                      style={{ width: 48 }}
                    >
                      {index + 1}
                    </td>
                    <td className="whitespace-pre-wrap break-words">{line || " "}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {file.truncated && (
              <p className="m-0 border-t border-[#21262d] px-3 py-2 text-[11px] text-[#e3b341]">
                Preview truncated by the server. Download the file for the complete contents.
              </p>
            )}
          </div>
        )}
      </div>

      {notice && <p className="m-0 text-[12px] text-[#3fb950]">{notice}</p>}

      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        {editable && !editing && (
          <button
            type="button"
            className="qh-btn qh-btn-sm qh-btn-primary"
            onClick={() => {
              setDraft(file.content ?? "");
              setEditing(true);
            }}
          >
            Edit file
          </button>
        )}
        <button
          type="button"
          className="qh-btn qh-btn-sm"
          onClick={() =>
            void download(
              `/projects/${owner}/${slug}/raw?path=${encodeURIComponent(path)}`,
              path.split("/").pop() || "file",
            )
          }
        >
          Download
        </button>
        {file.last_commit && (
          <span className="text-[#8b949e]">
            Last change {formatRelativeTime(file.last_commit.authored_at)} by{" "}
            {file.last_commit.author_name} · <span className="qh-mono">{file.last_commit.sha.slice(0, 7)}</span>
          </span>
        )}
        {!editable && project.viewer.can_write && (file.binary || file.too_large) && (
          <span className="qh-muted">Binary and oversized files cannot be edited in the browser.</span>
        )}
        {!editable && !project.viewer.can_write && (
          <span className="qh-muted"><RunStatusPill status="read-only" /> Read-only view</span>
        )}
      </div>
    </div>
  );
}

export default function BlobPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const path = (useParams()["*"] ?? "").replace(/^\/+/, "");

  return (
    <>
      <PageMeta title={`${path} · ${owner}/${slug}`} description="File contents in a QuantHub project." />
      <ProjectChrome owner={owner} slug={slug} tab="code">
        {(project) => <BlobView owner={owner} slug={slug} project={project} path={path} />}
      </ProjectChrome>
    </>
  );
}
