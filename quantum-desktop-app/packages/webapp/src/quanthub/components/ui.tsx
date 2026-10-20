import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { formatRelativeTime } from "../client";
import type { TreeEntry, Visibility } from "../types";

export function VisibilityBadge({ visibility }: { visibility: Visibility }): JSX.Element {
  return (
    <span className={`qh-badge ${visibility === "public" ? "qh-badge-public" : "qh-badge-private"}`}>
      {visibility === "public" ? "Public" : "Private"}
    </span>
  );
}

export function LockIcon({ size = 12 }: { size?: number }): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M4 4a4 4 0 0 1 8 0v2h.5A1.5 1.5 0 0 1 14 7.5v6A1.5 1.5 0 0 1 12.5 15h-9A1.5 1.5 0 0 1 2 13.5v-6A1.5 1.5 0 0 1 3.5 6H4Zm1.5 2h5V4a2.5 2.5 0 0 0-5 0Z" />
    </svg>
  );
}

export function RepoIcon({ size = 16 }: { size?: number }): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 0 .5h-3.5a.25.25 0 0 1-.25-.25Zm0-3.5a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 0 .5h-3.5a.25.25 0 0 1-.25-.25Zm0-3.5a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 0 .5h-3.5a.25.25 0 0 1-.25-.25Z" />
    </svg>
  );
}

const FOLDER_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1Z" />
  </svg>
);

const FILE_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Z" />
  </svg>
);

export function FileIcon({ entry }: { entry: TreeEntry }): JSX.Element {
  if (entry.type === "tree") return <span className="text-[#7ee787]">{FOLDER_ICON}</span>;
  return <span className="text-[#8b949e]">{FILE_ICON}</span>;
}

const LANGUAGE_COLORS: Record<string, string> = {
  Python: "#3572A5",
  TypeScript: "#3178c6",
  JavaScript: "#f1e05a",
  Java: "#b07219",
  "C++": "#f34b7d",
  "C#": "#178600",
  C: "#555555",
  Go: "#00ADD8",
  Rust: "#dea584",
  SQL: "#e38c00",
  PHP: "#4F5D95",
  Kotlin: "#A97BFF",
  Swift: "#F05138",
  Ruby: "#701516",
  R: "#198CE7",
  HTML: "#e34c26",
  CSS: "#563d7c",
  MATLAB: "#e16737",
  Scala: "#c22d40",
  "Shell / Bash": "#89e051",
  YAML: "#cb171e",
  TOML: "#9c4221",
  Perl: "#0298c3",
  Markdown: "#083fa1",
  JSON: "#292929",
};

export function LanguageDot({ label }: { label: string | null | undefined }): JSX.Element | null {
  if (!label) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[#9198a1]">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: LANGUAGE_COLORS[label] ?? "#8b949e" }}
      />
      {label}
    </span>
  );
}

export function RelativeTime({ value }: { value: string | null | undefined }): JSX.Element {
  return (
    <time dateTime={value ?? undefined} title={value ?? undefined}>
      {formatRelativeTime(value)}
    </time>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: string }): JSX.Element {
  return <div className="qh-skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function LoadingPanel({ rows = 3 }: { rows?: number }): JSX.Element {
  return (
    <div className="qh-card qh-card-body" aria-busy="true" aria-label="Loading">
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} height={index === 0 ? 20 : 14} width={index === 0 ? "45%" : "85%"} />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}): JSX.Element {
  return (
    <div className="qh-empty">
      <p className="qh-heading m-0 font-semibold text-[#e6edf3]">{title}</p>
      {description && <p className="m-0 max-w-md">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }): JSX.Element {
  return (
    <div className="qh-form-error" role="alert">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {onRetry && (
          <button type="button" className="qh-btn qh-btn-sm" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function RunStatusPill({ status }: { status: string }): JSX.Element {
  return (
    <span className="qh-status">
      <span className={`qh-dot qh-dot-${status}`} />
      {status}
    </span>
  );
}

export function ProjectLink({
  fullName,
  children,
  className,
}: {
  fullName: string;
  children?: ReactNode;
  className?: string;
}): JSX.Element {
  const [owner, slug] = fullName.split("/");
  return (
    <Link to={`/${owner}/${slug}`} className={className}>
      {children ?? fullName}
    </Link>
  );
}
