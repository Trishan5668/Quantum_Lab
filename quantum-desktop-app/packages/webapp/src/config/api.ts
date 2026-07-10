const DEVELOPMENT_API_URL = "http://127.0.0.1:8765";
const PRODUCTION_FALLBACK_API_URL = "https://quantum-lab-2ukm.onrender.com";

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL?.trim();
  if (configured) return trimTrailingSlash(configured);

  return import.meta.env.DEV ? DEVELOPMENT_API_URL : PRODUCTION_FALLBACK_API_URL;
}

function toWebSocketUrl(httpUrl: string): string {
  if (httpUrl.startsWith("https://")) return `wss://${httpUrl.slice("https://".length)}`;
  if (httpUrl.startsWith("http://")) return `ws://${httpUrl.slice("http://".length)}`;
  return httpUrl;
}

export const API_BASE_URL = resolveApiBaseUrl();
export const API_V1_BASE_URL = `${API_BASE_URL}/api/v1`;
export const API_V2_BASE_URL = `${API_BASE_URL}/api/v2`;
export const WEBSOCKET_BASE_URL = toWebSocketUrl(API_BASE_URL);
export const ENVIRONMENT_LABEL = import.meta.env.DEV ? "Development" : "Production";
export const BACKEND_UNAVAILABLE_MESSAGE = "Backend unavailable.";

export function apiUrl(path: string, version: "v1" | "v2" = "v1"): string {
  const base = version === "v1" ? API_V1_BASE_URL : API_V2_BASE_URL;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export function backendUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function websocketUrl(path: string): string {
  return `${WEBSOCKET_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function frontendUrl(): string {
  return typeof window === "undefined" ? "" : window.location.origin;
}
