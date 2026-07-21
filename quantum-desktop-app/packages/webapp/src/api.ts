import type {
  ApiEnvelope,
  BlochData,
  CircuitState,
  DensityMatrixData,
  GatePlacement,
  SimulationResult,
  StateSnapshot,
} from "./types";
import { BACKEND_UNAVAILABLE_MESSAGE, apiUrl } from "./config/api";

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly trace: string | null;
  constructor(code: string, message: string, status: number, trace: string | null) {
    super(message);
    this.code = code;
    this.status = status;
    this.trace = trace;
  }
}

async function postJson<TResponse, TBody = unknown>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  let resp: Response;
  try {
    const finalUrl = apiUrl(path);
    console.log("API URL =", finalUrl);
    console.trace();
    resp = await fetch(finalUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiClientError(
      "NetworkError",
      BACKEND_UNAVAILABLE_MESSAGE,
      0,
      null,
    );
  }

  let envelope: ApiEnvelope<TResponse> | null = null;
  try {
    envelope = (await resp.json()) as ApiEnvelope<TResponse>;
  } catch {
    throw new ApiClientError(
      "BadResponse",
      `Server returned non-JSON response (status ${resp.status})`,
      resp.status,
      null,
    );
  }

  if (!resp.ok) {
    const err = envelope?.error;
    const detail =
      (envelope as unknown as { detail?: { error?: { code: string; message: string; trace: string | null } } })
        ?.detail?.error ?? null;
    const e = err ?? detail;
    throw new ApiClientError(
      e?.code ?? "HttpError",
      e?.message ?? `HTTP ${resp.status}`,
      resp.status,
      e?.trace ?? null,
    );
  }

  if (envelope.error) {
    throw new ApiClientError(
      envelope.error.code,
      envelope.error.message,
      resp.status,
      envelope.error.trace,
    );
  }
  if (envelope.data === null || envelope.data === undefined) {
    throw new ApiClientError(
      "EmptyResponse",
      `API returned no data in 2xx envelope`,
      resp.status,
      null,
    );
  }
  return envelope.data;
}

function serializeCircuit(state: Pick<CircuitState, "numQubits" | "gates" | "initialBasisState">) {
  return {
    num_qubits: state.numQubits,
    initial_basis_state: state.initialBasisState,
    gates: state.gates.map((g: GatePlacement) => ({
      id: g.id,
      gate_type: g.gateType,
      qubit_targets: g.qubitTargets,
      params: g.params.theta !== undefined ? { theta: g.params.theta } : {},
      time_step: g.timeStep,
      stack_count: g.stackCount ?? 1,
    })),
  };
}

export async function runCircuit(
  state: Pick<CircuitState, "numQubits" | "gates" | "initialBasisState">,
): Promise<SimulationResult> {
  return postJson<SimulationResult>("/circuit/run", serializeCircuit(state));
}

export async function fetchBloch(state: StateSnapshot): Promise<BlochData> {
  return postJson<BlochData>("/visualize/bloch", {
    num_qubits: state.num_qubits,
    amplitudes: state.amplitudes,
  });
}

export async function fetchDensity(state: StateSnapshot): Promise<DensityMatrixData> {
  return postJson<DensityMatrixData>("/visualize/density", {
    num_qubits: state.num_qubits,
    amplitudes: state.amplitudes,
  });
}

export async function fetchHealth(): Promise<{ status: string; version: string; core_version: string }> {
  let resp: Response;
  try {
    const finalUrl = apiUrl("/health");
    console.log("API URL =", finalUrl);
    console.trace();
    resp = await fetch(finalUrl);
  } catch {
    throw new ApiClientError("NetworkError", BACKEND_UNAVAILABLE_MESSAGE, 0, null);
  }
  if (!resp.ok) {
    throw new ApiClientError("Unreachable", BACKEND_UNAVAILABLE_MESSAGE, resp.status, null);
  }
  const env = (await resp.json()) as ApiEnvelope<{
    status: string;
    version: string;
    core_version: string;
  }>;
  if (!env.data) {
    throw new ApiClientError("EmptyResponse", "health returned no data", resp.status, null);
  }
  return env.data;
}

export interface ExplainTokenHandlers {
  onToken: (text: string) => void;
  onDone: () => void;
  onError: (err: ApiClientError) => void;
}

export interface ExplainRequest {
  gate: string;
  qubit?: number | null;
  qubits?: number[] | null;
  state_before: { real: number; imag: number }[];
  state_after: { real: number; imag: number }[];
  num_qubits: number;
  context: string;
  mode?: "normal" | "deep" | "hint";
}

export async function streamExplain(
  req: ExplainRequest,
  handlers: ExplainTokenHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let resp: Response;
  try {
    const finalUrl = apiUrl("/explain");
    console.log("API URL =", finalUrl);
    console.trace();
    resp = await fetch(finalUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(req),
      signal,
    });
  } catch {
    handlers.onError(
      new ApiClientError(
        "NetworkError",
        BACKEND_UNAVAILABLE_MESSAGE,
        0,
        null,
      ),
    );
    return;
  }

  if (!resp.ok) {
    let detail: ApiClientError;
    try {
      const body = (await resp.json()) as
        | { detail?: { error?: { code: string; message: string; trace: string | null } } }
        | ApiEnvelope<unknown>;
      const e =
        (body as { detail?: { error?: { code: string; message: string; trace: string | null } } }).detail?.error ??
        (body as ApiEnvelope<unknown>).error ??
        null;
      detail = new ApiClientError(
        e?.code ?? "HttpError",
        e?.message ?? `HTTP ${resp.status}`,
        resp.status,
        e?.trace ?? null,
      );
    } catch {
      detail = new ApiClientError("HttpError", `HTTP ${resp.status}`, resp.status, null);
    }
    handlers.onError(detail);
    return;
  }

  if (!resp.body) {
    handlers.onError(new ApiClientError("EmptyStream", "no response body", resp.status, null));
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx = buffer.indexOf("\n\n");
      while (idx !== -1) {
        const eventChunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        processSseChunk(eventChunk, handlers);
        idx = buffer.indexOf("\n\n");
      }
    }
    handlers.onDone();
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") {
      return;
    }
    handlers.onError(
      new ApiClientError(
        "StreamError",
        err instanceof Error ? err.message : String(err),
        0,
        null,
      ),
    );
  }
}

function processSseChunk(chunk: string, handlers: ExplainTokenHandlers): void {
  let event = "message";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }
  if (!data) return;
  if (event === "token") {
    try {
      const parsed = JSON.parse(data) as { text?: string };
      if (parsed.text) handlers.onToken(parsed.text);
    } catch {
      // ignore malformed token frame
    }
  } else if (event === "done") {
    handlers.onDone();
  }
}
