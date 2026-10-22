/**
 * QuantHub HTTP client.
 *
 * Identity
 * --------
 * When Firebase is configured the signed-in user's ID token is sent as a
 * bearer token and the backend verifies it. Otherwise the app runs a clearly
 * labelled **local session**: the handle is stored in localStorage and sent in
 * `X-QuantHub-*` headers. The server honours those headers only when
 * `QUANTHUB_ENV` is `development`/`test` *and*
 * `QUANTHUB_TRUST_CLIENT_IDENTITY=1`; elsewhere they are ignored and the
 * caller is a guest (`viewer.mode === "guest"`), so the UI must not imply that
 * local-session writes are accepted there.
 */

import { firebaseClient } from "../firebase/config";

const configuredBase = (import.meta.env.VITE_API_URL as string | undefined)
  ?.trim()
  .replace(/\/+$/, "");

/**
 * Same-origin `/api/v1` by default (the Vite dev server proxies it), or the
 * configured backend origin when `VITE_API_URL` is set for a split deployment.
 */
export const API_ROOT = `${configuredBase ?? ""}/api/v1`;

export interface LocalIdentity {
  handle: string;
  display_name: string;
  email: string | null;
  created_at: string;
}

const IDENTITY_KEY = "quanthub.identity.v1";
const RECENTS_KEY = "quanthub.recentProjects.v1";

function randomSuffix(): string {
  return Math.random().toString(36).slice(2, 6);
}

export function defaultIdentity(): LocalIdentity {
  return {
    handle: `researcher-${randomSuffix()}`,
    display_name: "Local Researcher",
    email: null,
    created_at: new Date().toISOString(),
  };
}

export function loadIdentity(): LocalIdentity {
  try {
    const raw = window.localStorage.getItem(IDENTITY_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<LocalIdentity>;
      if (parsed.handle) {
        return {
          handle: parsed.handle,
          display_name: parsed.display_name || parsed.handle,
          email: parsed.email ?? null,
          created_at: parsed.created_at || new Date().toISOString(),
        };
      }
    }
  } catch {
    // corrupt storage falls through to a fresh local identity
  }
  const identity = defaultIdentity();
  saveIdentity(identity);
  return identity;
}

export function saveIdentity(identity: LocalIdentity): void {
  try {
    window.localStorage.setItem(IDENTITY_KEY, JSON.stringify(identity));
  } catch {
    // storage can be unavailable (private mode); the session still works for reads
  }
}

export function clearIdentity(): void {
  try {
    window.localStorage.removeItem(IDENTITY_KEY);
  } catch {
    /* ignore */
  }
}

export interface RecentProject {
  full_name: string;
  name: string;
  visibility: string;
  opened_at: string;
}

export function loadRecentProjects(): RecentProject[] {
  try {
    const raw = window.localStorage.getItem(RECENTS_KEY);
    const parsed = raw ? (JSON.parse(raw) as RecentProject[]) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
  } catch {
    return [];
  }
}

export function rememberProject(project: {
  full_name: string;
  name: string;
  visibility: string;
}): void {
  try {
    const existing = loadRecentProjects().filter(
      (item) => item.full_name !== project.full_name,
    );
    const next = [{ ...project, opened_at: new Date().toISOString() }, ...existing].slice(0, 8);
    window.localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

async function identityHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  const user = firebaseClient?.auth.currentUser;
  if (user) {
    try {
      const token = await user.getIdToken();
      headers.Authorization = `Bearer ${token}`;
      return headers;
    } catch {
      // fall through to the local identity when the token cannot be refreshed
    }
  }
  const identity = loadIdentity();
  headers["X-QuantHub-User"] = identity.handle;
  headers["X-QuantHub-Name"] = identity.display_name;
  if (identity.email) headers["X-QuantHub-Email"] = identity.email;
  return headers;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
}

/** A short, non-sensitive description for an unsuccessful HTTP status. */
function describeStatus(status: number): string {
  if (status === 401) return "Sign in to continue (HTTP 401).";
  if (status === 403) return "You do not have permission to do that (HTTP 403).";
  if (status === 404) return "Not found (HTTP 404).";
  if (status === 429) return "Too many requests (HTTP 429).";
  if (status >= 500) return `The server failed to handle the request (HTTP ${status}).`;
  return `The request was rejected (HTTP ${status}).`;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = await identityHeaders();
  const init: RequestInit = {
    method: options.method ?? (options.body !== undefined || options.form ? "POST" : "GET"),
    headers,
    signal: options.signal,
  };
  if (options.form) {
    init.body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, init);
  } catch (error) {
    throw new ApiError(
      0,
      "NetworkError",
      "The QuantHub server could not be reached. Check that the API is running.",
    );
  }
  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    let code = `HTTP${response.status}`;
    // Never present a bare "Request failed.": include the status so a proxy,
    // an unauthenticated deployment and a server bug are distinguishable.
    let message = describeStatus(response.status);
    let details: Record<string, unknown> | undefined;
    if (contentType.includes("application/json")) {
      try {
        const body = (await response.json()) as {
          error?: { code?: string; message?: string; details?: Record<string, unknown> };
          detail?: unknown;
        };
        if (body.error?.message) {
          code = body.error.code || code;
          message = body.error.message;
          details = body.error.details;
        } else if (typeof body.detail === "string") {
          message = body.detail;
        } else if (Array.isArray(body.detail) && body.detail.length > 0) {
          message = "The request was rejected by validation.";
          details = { validation: body.detail as unknown as Record<string, unknown> };
        }
      } catch {
        /* keep the status-based message */
      }
    }
    throw new ApiError(response.status, code, message, details);
  }
  if (!contentType.includes("application/json")) {
    return (await response.blob()) as unknown as T;
  }
  const payload = (await response.json()) as { data: T; error: unknown };
  return payload.data;
}

export interface UploadOptions {
  onProgress?: (fraction: number) => void;
  signal?: AbortSignal;
}

/**
 * Multipart upload with real progress reporting and cancellation.
 * `fetch` cannot report request-body progress, so uploads use XHR.
 */
export async function uploadForm<T>(
  path: string,
  form: FormData,
  options: UploadOptions = {},
): Promise<T> {
  const headers = await identityHeaders();
  return new Promise<T>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_ROOT}${path}`);
    for (const [key, value] of Object.entries(headers)) {
      request.setRequestHeader(key, value);
    }
    request.responseType = "text";

    const cleanup = () => options.signal?.removeEventListener("abort", onAbort);
    const onAbort = () => {
      request.abort();
    };
    if (options.signal) {
      if (options.signal.aborted) {
        reject(new ApiError(0, "Aborted", "The upload was cancelled."));
        return;
      }
      options.signal.addEventListener("abort", onAbort);
    }

    request.upload.onprogress = (event) => {
      if (event.lengthComputable && options.onProgress) {
        options.onProgress(Math.min(1, event.loaded / event.total));
      }
    };
    request.onerror = () => {
      cleanup();
      reject(new ApiError(0, "NetworkError", "The upload failed because the server could not be reached."));
    };
    request.onabort = () => {
      cleanup();
      reject(new ApiError(0, "Aborted", "The upload was cancelled."));
    };
    request.onload = () => {
      cleanup();
      interface Envelope {
        data?: T;
        error?: { code?: string; message?: string; details?: Record<string, unknown> };
      }
      let body: Envelope | null = null;
      try {
        body = JSON.parse(request.responseText) as Envelope;
      } catch {
        body = null;
      }
      if (request.status >= 200 && request.status < 300 && body && "data" in body) {
        resolve(body.data as T);
        return;
      }
      const error = body?.error;
      reject(
        new ApiError(
          request.status,
          error?.code ?? `HTTP${request.status}`,
          error?.message ?? describeStatus(request.status),
          error?.details,
        ),
      );
    };
    request.send(form);
  });
}

export function downloadUrl(path: string): string {
  return `${API_ROOT}${path}`;
}

/** Trigger a browser download for an authenticated endpoint. */
export async function download(path: string, filename: string): Promise<void> {
  const headers = await identityHeaders();
  const response = await fetch(`${API_ROOT}${path}`, { headers });
  if (!response.ok) {
    throw new ApiError(response.status, "DownloadFailed", describeStatus(response.status));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return "unknown";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return value;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 45) return "just now";
  const units: Array<[number, string]> = [
    [60, "minute"],
    [3600, "hour"],
    [86400, "day"],
    [604800, "week"],
    [2592000, "month"],
    [31536000, "year"],
  ];
  let previous = 1;
  let label = "second";
  for (const [limit, name] of units) {
    if (seconds < limit) {
      const amount = Math.max(1, Math.round(seconds / previous));
      return `${amount} ${label}${amount === 1 ? "" : "s"} ago`;
    }
    previous = limit;
    label = name;
  }
  const years = Math.max(1, Math.round(seconds / 31536000));
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[index]}`;
}

export function formatProbability(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "0";
  if (Math.abs(value) < 0.001) return value.toExponential(2);
  return value.toFixed(5).replace(/0+$/, "").replace(/\.$/, "");
}
