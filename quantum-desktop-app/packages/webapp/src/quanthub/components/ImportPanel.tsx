import { useMemo, useRef, useState } from "react";
import { ApiError, formatBytes, uploadForm } from "../client";

export interface ImportResult {
  import_id?: string;
  revision: string;
  files: string[];
  skipped: Array<{ path: string; reason: string }>;
  kind?: string;
  preserved_history?: boolean;
}

function relativePath(file: File): string {
  const withPath = file as File & { webkitRelativePath?: string };
  return withPath.webkitRelativePath || file.name;
}

export function ImportPanel({
  basePath,
  onImported,
}: {
  basePath: string;
  onImported?: (result: ImportResult) => void;
}): JSX.Element {
  const [files, setFiles] = useState<File[]>([]);
  const [archive, setArchive] = useState<File | null>(null);
  const [message, setMessage] = useState("Import existing project");
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const folderInput = useRef<HTMLInputElement | null>(null);
  const zipInput = useRef<HTMLInputElement | null>(null);

  const totalBytes = useMemo(
    () => files.reduce((sum, file) => sum + file.size, 0) + (archive?.size ?? 0),
    [files, archive],
  );

  const busy = progress !== null;

  function choose(nextFiles: File[] | null, nextArchive: File | null = null): void {
    setError(null);
    setResult(null);
    setArchive(nextArchive);
    setFiles(nextFiles ?? []);
  }

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    if (busy) return;
    if (!archive && files.length === 0) {
      setError("Choose at least one file, a folder, or a ZIP archive first.");
      return;
    }
    const form = new FormData();
    let endpoint = `${basePath}/upload`;
    if (archive) {
      endpoint = `${basePath}/import/zip`;
      form.append("archive", archive, archive.name);
      form.append("message", message || `Import ${archive.name}`);
    } else {
      files.forEach((file) => form.append("files", file, relativePath(file)));
      form.append("paths", JSON.stringify(files.map(relativePath)));
      form.append("message", message || "Upload files");
    }

    const abort = new AbortController();
    controller.current = abort;
    setProgress(0);
    setError(null);
    try {
      const response = await uploadForm<ImportResult>(endpoint, form, {
        signal: abort.signal,
        onProgress: (fraction) => setProgress(fraction),
      });
      setResult(response);
      setFiles([]);
      setArchive(null);
      onImported?.(response);
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "Aborted") {
        setError("Upload cancelled. Nothing was committed.");
      } else {
        setError(cause instanceof Error ? cause.message : "The import failed.");
      }
    } finally {
      controller.current = null;
      setProgress(null);
    }
  }

  function cancel(): void {
    controller.current?.abort();
  }

  return (
    <div className="qh-card">
      <div className="qh-card-header">
        <h2 className="m-0 text-[14px] font-semibold">Import files</h2>
        <span className="qh-badge">multi-file · folder · ZIP</span>
      </div>
      <form className="qh-card-body" onSubmit={submit}>
        <div
          className="rounded-md border border-dashed p-4 text-center"
          style={{
            borderColor: dragging ? "#58a6ff" : "#30363d",
            background: dragging ? "rgba(56,139,253,0.07)" : "transparent",
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            const dropped = Array.from(event.dataTransfer.files);
            if (dropped.length === 1 && dropped[0].name.toLowerCase().endsWith(".zip")) {
              choose(null, dropped[0]);
            } else {
              choose(dropped);
            }
          }}
        >
          <p className="m-0 text-[13px]">
            Drop files, a folder, or a <span className="qh-mono">.zip</span> here
          </p>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <button type="button" className="qh-btn qh-btn-sm" onClick={() => fileInput.current?.click()}>
              Choose files
            </button>
            <button
              type="button"
              className="qh-btn qh-btn-sm"
              onClick={() => {
                folderInput.current?.setAttribute("webkitdirectory", "");
                folderInput.current?.setAttribute("directory", "");
                folderInput.current?.click();
              }}
            >
              Choose folder
            </button>
            <button type="button" className="qh-btn qh-btn-sm" onClick={() => zipInput.current?.click()}>
              Choose ZIP
            </button>
          </div>
          <input
            ref={fileInput}
            type="file"
            multiple
            className="hidden"
            onChange={(event) => choose(Array.from(event.target.files ?? []))}
          />
          <input
            ref={folderInput}
            type="file"
            multiple
            className="hidden"
            onChange={(event) => choose(Array.from(event.target.files ?? []))}
          />
          <input
            ref={zipInput}
            type="file"
            accept=".zip,application/zip"
            className="hidden"
            onChange={(event) => {
              const next = event.target.files?.[0];
              choose(null, next ?? null);
            }}
          />
        </div>

        {(files.length > 0 || archive) && (
          <div className="mt-3 rounded border border-[#21262d] p-3 text-[12px]">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">
                {archive ? archive.name : `${files.length} file${files.length === 1 ? "" : "s"}`}
              </span>
              <span className="text-[#9198a1]">{formatBytes(totalBytes)}</span>
            </div>
            {!archive && (
              <ul className="mt-1 max-h-40 overflow-auto pl-4 text-[#9198a1]">
                {files.slice(0, 50).map((file) => (
                  <li key={relativePath(file)} className="qh-mono truncate">
                    {relativePath(file)}
                  </li>
                ))}
                {files.length > 50 && <li>…and {files.length - 50} more</li>}
              </ul>
            )}
          </div>
        )}

        <div className="qh-field mt-3">
          <label className="qh-label" htmlFor="import-commit-message">
            Commit message
          </label>
          <input
            id="import-commit-message"
            className="qh-input"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={200}
          />
        </div>

        <p className="qh-help">
          Directory structure is preserved and paths are validated on the server. A file
          upload creates one revision; local Git history is not transferred.
        </p>

        {progress !== null && (
          <div className="mb-3">
            <div
              className="h-1.5 w-full overflow-hidden rounded bg-[#21262d]"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progress * 100)}
            >
              <div
                className="h-full bg-[#238636] transition-[width]"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
            <p className="qh-help mb-0">{Math.round(progress * 100)}% uploaded</p>
          </div>
        )}

        {error && (
          <div className="qh-form-error mb-3" role="alert">
            {error}
          </div>
        )}

        {result && (
          <div className="mb-3 rounded border border-[#238636] bg-[rgba(35,134,54,0.1)] p-3 text-[12px]">
            <p className="m-0 font-semibold">
              Imported {result.files.length} file{result.files.length === 1 ? "" : "s"} · revision{" "}
              <span className="qh-mono">{result.revision.slice(0, 7)}</span>
            </p>
            {result.skipped.length > 0 && (
              <>
                <p className="mb-1 mt-2 text-[#e3b341]">
                  Skipped {result.skipped.length} entr{result.skipped.length === 1 ? "y" : "ies"}:
                </p>
                <ul className="m-0 max-h-32 overflow-auto pl-4 text-[#9198a1]">
                  {result.skipped.slice(0, 25).map((item) => (
                    <li key={`${item.path}-${item.reason}`}>
                      <span className="qh-mono">{item.path}</span> — {item.reason}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <button type="submit" className="qh-btn qh-btn-primary" disabled={busy}>
            {busy ? "Importing…" : result ? "Import again" : "Start import"}
          </button>
          {busy && (
            <button type="button" className="qh-btn qh-btn-danger" onClick={cancel}>
              Cancel upload
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
