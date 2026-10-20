import { Link } from "react-router-dom";
import { formatBytes } from "../client";
import type { TreeEntry } from "../types";
import { FileIcon } from "./ui";

function Breadcrumbs({ base, path }: { base: string; path: string }): JSX.Element {
  const parts = path ? path.split("/") : [];
  return (
    <nav className="flex flex-wrap items-center gap-1 text-[13px]" aria-label="Breadcrumb">
      <Link to={base} className="text-[#79c0ff]">
        {base.split("/").slice(-1)[0]}
      </Link>
      {parts.map((part, index) => {
        const target = parts.slice(0, index + 1).join("/");
        const last = index === parts.length - 1;
        return (
          <span key={target} className="flex items-center gap-1">
            <span className="text-[#6e7681]">/</span>
            {last ? (
              <span className="font-semibold">{part}</span>
            ) : (
              <Link to={`${base}?path=${encodeURIComponent(target)}`} className="text-[#79c0ff]">
                {part}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function FileBrowser({
  base,
  path,
  entries,
  revision,
  emptyMessage,
  readOnly,
  onDelete,
}: {
  base: string;
  path: string;
  entries: TreeEntry[];
  revision: string | null;
  emptyMessage?: string;
  readOnly?: boolean;
  onDelete?: (entry: TreeEntry) => void;
}): JSX.Element {
  return (
    <div className="qh-card overflow-hidden">
      <div className="qh-card-header flex flex-wrap items-center justify-between gap-2">
        <Breadcrumbs base={base} path={path} />
        <span className="qh-mono text-[11px] text-[#6e7681]">
          {revision ? revision.slice(0, 7) : "empty"}
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="m-0 px-4 py-6 text-center text-[13px] text-[#8b949e]">
          {emptyMessage ?? "This directory is empty."}
        </p>
      ) : (
        <table className="qh-file-table" aria-label="Project files">
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Type</th>
              <th scope="col" className="text-right">Size</th>
              {!readOnly && onDelete && <th scope="col"><span className="sr-only">Actions</span></th>}
            </tr>
          </thead>
          <tbody>
            {path && (
              <tr>
                <td colSpan={readOnly || !onDelete ? 3 : 4}>
                  <Link
                    to={`${base}${path.includes("/") ? `?path=${encodeURIComponent(path.split("/").slice(0, -1).join("/"))}` : ""}`}
                    className="text-[#79c0ff]"
                  >
                    ..
                  </Link>
                </td>
              </tr>
            )}
            {entries.map((entry) => {
              const href =
                entry.type === "tree"
                  ? `${base}?path=${encodeURIComponent(entry.path)}`
                  : `${base}/blob/${entry.path}`;
              return (
                <tr key={entry.path} className="qh-file-row">
                  <td>
                    <span className="flex min-w-0 items-center gap-2">
                      <FileIcon entry={entry} />
                      <Link to={href} className="truncate text-[#c9d1d9] hover:text-[#79c0ff]">
                        {entry.name}
                      </Link>
                    </span>
                  </td>
                  <td className="text-[#8b949e]">{entry.label ?? (entry.type === "tree" ? "Directory" : "File")}</td>
                  <td className="text-right text-[#8b949e]">
                    {entry.type === "blob" ? formatBytes(entry.size) : "—"}
                  </td>
                  {!readOnly && onDelete && (
                    <td className="text-right">
                      <button
                        type="button"
                        className="qh-btn qh-btn-sm qh-btn-danger"
                        onClick={() => onDelete(entry)}
                      >
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
