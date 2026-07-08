import type {
  ApiEnvelope,
  CircuitState,
  DensityMatrixData,
  GatePlacement,
  MetricsResult,
  NoiseChannelType,
  SimulationMode,
  SimulationResultV2,
} from "./types";

const API_V2_BASE = "http://127.0.0.1:8765/api/v2";

export class ApiV2ClientError extends Error {
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

async function postV2<TResponse, TBody = unknown>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  let resp: Response;
  try {
    resp = await fetch(`${API_V2_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new ApiV2ClientError(
      "NetworkError",
      err instanceof Error ? err.message : String(err),
      0,
      null,
    );
  }

  const envelope = (await resp.json()) as ApiEnvelope<TResponse>;
  if (!resp.ok || envelope.error) {
    const e = envelope.error;
    throw new ApiV2ClientError(
      e?.code ?? "HttpError",
      e?.message ?? `HTTP ${resp.status}`,
      resp.status,
      e?.trace ?? null,
    );
  }
  if (envelope.data === null || envelope.data === undefined) {
    throw new ApiV2ClientError("EmptyResponse", "API returned no data", resp.status, null);
  }
  return envelope.data;
}

function serializeCircuitV2(state: Pick<CircuitState, "numQubits" | "gates">) {
  return {
    num_qubits: state.numQubits,
    gates: state.gates.map((g: GatePlacement) => ({
      id: g.id,
      gate_type: g.gateType,
      qubit_targets: g.qubitTargets,
      params: g.params.theta !== undefined ? { theta: g.params.theta } : {},
      time_step: g.timeStep,
    })),
  };
}

export interface RunCircuitV2Options {
  simulationMode: SimulationMode;
  noiseEnabled: boolean;
  noiseModel: NoiseChannelType;
  noiseProbability: number;
  t1Us: number;
  t2Us: number;
  gateTimeNs: number;
}

export async function runCircuitV2(
  state: Pick<CircuitState, "numQubits" | "gates">,
  options: RunCircuitV2Options,
): Promise<SimulationResultV2> {
  const body = {
    ...serializeCircuitV2(state),
    simulation: {
      mode: options.simulationMode,
      noise: {
        enabled: options.noiseEnabled,
        channel: options.noiseModel,
        probability: options.noiseProbability,
        t1_us: options.t1Us,
        t2_us: options.t2Us,
        gate_time_ns: options.gateTimeNs,
      },
    },
  };
  return postV2<SimulationResultV2>("/circuit/run", body);
}

export async function fetchFidelity(
  numQubits: number,
  target: "bell" | "ghz" | "zero",
  opts: {
    amplitudes?: { real: number; imag: number }[];
    density?: DensityMatrixData;
  },
): Promise<MetricsResult["fidelity"]> {
  const body: Record<string, unknown> = {
    num_qubits: numQubits,
    target,
  };
  if (opts.density) {
    body.density_real = opts.density.real;
    body.density_imag = opts.density.imag;
  } else if (opts.amplitudes) {
    body.amplitudes = opts.amplitudes;
  }
  return postV2("/metrics/fidelity", body);
}

export async function fetchEntropy(
  numQubits: number,
  subsystem: number[],
  density: DensityMatrixData,
): Promise<MetricsResult["entropy"]> {
  return postV2("/metrics/entropy", {
    num_qubits: numQubits,
    subsystem,
    density_real: density.real,
    density_imag: density.imag,
  });
}

export async function fetchPurity(
  numQubits: number,
  amplitudes: { real: number; imag: number }[],
): Promise<MetricsResult["purity"]> {
  return postV2("/metrics/purity", {
    num_qubits: numQubits,
    amplitudes,
  });
}

export async function fetchPurityFromDensity(
  numQubits: number,
  density: DensityMatrixData,
): Promise<MetricsResult["purity"]> {
  return postV2("/metrics/purity", {
    num_qubits: numQubits,
    density_real: density.real,
    density_imag: density.imag,
  });
}
