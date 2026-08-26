export type GateType = "H" | "X" | "Y" | "Z" | "RX" | "RY" | "RZ" | "CNOT" | "M";

export type SimulationMode = "statevector" | "density";

export type NoiseChannelType =
  | "amplitude_damping"
  | "phase_damping"
  | "depolarizing"
  | "bit_flip"
  | "phase_flip"
  | "t1_t2";

export type FidelityTarget = "none" | "bell" | "ghz" | "zero";

export interface GateParams {
  theta?: number;
}

export interface GatePlacement {
  id: string;
  gateType: GateType;
  qubitTargets: number[];
  params: GateParams;
  timeStep: number;
  stackCount?: number;
}

export interface CircuitState {
  numQubits: number;
  initialBasisState: string;
  selectedBasisState: string;
  gates: GatePlacement[];
  results: SimulationResult | null;
  resultsV2: SimulationResultV2 | null;
  isRunning: boolean;
  stepMode: boolean;
  currentStep: number;
  lastError: string | null;
  simulationMode: SimulationMode;
  noiseEnabled: boolean;
  noiseModel: NoiseChannelType;
  noiseProbability: number;
  t1Us: number;
  t2Us: number;
  gateTimeNs: number;
  fidelityTarget: FidelityTarget;
  metrics: MetricsResult | null;
}

export interface ComplexAmplitude {
  real: number;
  imag: number;
}

export interface StateSnapshot {
  num_qubits: number;
  amplitudes: ComplexAmplitude[];
  probabilities: number[];
  basis_labels: string[];
}

export interface StepResult {
  gate_id: string;
  gate_type: string;
  qubit_targets: number[];
  params: Record<string, number>;
  time_step: number;
  stack_count?: number;
  state_after: StateSnapshot;
  probabilities: number[];
}

export interface SimulationResult {
  num_qubits: number;
  execution_time_ms: number;
  steps: StepResult[];
  final_state: StateSnapshot;
}

export interface SimulationResultV2 extends SimulationResult {
  simulation_mode: SimulationMode;
  mixed_state?: boolean;
  noise_enabled?: boolean;
  noise_channel?: string | null;
  final_density?: DensityMatrixData | null;
  purity?: number | null;
}

export interface FidelityMetric {
  fidelity: number;
  target_state: string;
  interpretation: string;
}

export interface EntropyMetric {
  entropy: number;
  interpretation: string;
}

export interface PurityMetric {
  purity: number;
  interpretation: string;
}

export interface MetricsResult {
  fidelity: FidelityMetric | null;
  entropy: EntropyMetric | null;
  purity: PurityMetric | null;
}

export type ResearchVerificationStatus = "VERIFIED" | "DISCREPANCY" | "UNAVAILABLE" | "SIMULATED";

export interface ResearchVerificationWarning {
  severity?: string;
  message: string;
  difference?: number;
  affectedCalculation?: string;
  quantumLab?: unknown;
  wolfram?: unknown;
}

export interface ResearchVerification {
  status: ResearchVerificationStatus;
  source: string;
  message: string;
  query_hash: string;
  structured_input?: unknown;
  calculations: Record<string, unknown>;
  warnings: ResearchVerificationWarning[];
}

export interface ApiError {
  code: string;
  message: string;
  trace: string | null;
}

export interface ApiEnvelope<T> {
  data: T | null;
  error: ApiError | null;
}

export interface BlochQubit {
  qubit: number;
  theta: number;
  phi: number;
  x: number;
  y: number;
  z: number;
  purity: number;
}

export interface BlochData {
  num_qubits: number;
  qubits: BlochQubit[];
}

export interface DensityMatrixData {
  num_qubits: number;
  dim: number;
  real: number[][];
  imag: number[][];
  basis_labels: string[];
}

export interface GateMeta {
  type: GateType;
  label: string;
  category: "single" | "rotation" | "two" | "measure";
  arity: 1 | 2;
  takesTheta: boolean;
  color: string;
  description: string;
  latex: string;
}

export const GATE_CATALOG: readonly GateMeta[] = [
  {
    type: "H",
    label: "H",
    category: "single",
    arity: 1,
    takesTheta: false,
    color: "var(--gate-h)",
    description: "Hadamard. Creates equal superposition: H|0> = (|0>+|1>)/sqrt(2).",
    latex: "H = \\tfrac{1}{\\sqrt{2}}\\begin{pmatrix}1 & 1 \\\\ 1 & -1\\end{pmatrix}",
  },
  {
    type: "X",
    label: "X",
    category: "single",
    arity: 1,
    takesTheta: false,
    color: "var(--gate-xyz)",
    description: "Pauli-X (NOT). Flips |0> <-> |1>.",
    latex: "X = \\begin{pmatrix}0 & 1 \\\\ 1 & 0\\end{pmatrix}",
  },
  {
    type: "Y",
    label: "Y",
    category: "single",
    arity: 1,
    takesTheta: false,
    color: "var(--gate-xyz)",
    description: "Pauli-Y. Bit-and-phase flip with i factors.",
    latex: "Y = \\begin{pmatrix}0 & -i \\\\ i & 0\\end{pmatrix}",
  },
  {
    type: "Z",
    label: "Z",
    category: "single",
    arity: 1,
    takesTheta: false,
    color: "var(--gate-xyz)",
    description: "Pauli-Z. Phase flip on |1>.",
    latex: "Z = \\begin{pmatrix}1 & 0 \\\\ 0 & -1\\end{pmatrix}",
  },
  {
    type: "RX",
    label: "RX(θ)",
    category: "rotation",
    arity: 1,
    takesTheta: true,
    color: "var(--gate-rot)",
    description: "Rotation around X axis by angle θ.",
    latex:
      "R_x(\\theta) = \\begin{pmatrix}\\cos\\tfrac{\\theta}{2} & -i\\sin\\tfrac{\\theta}{2} \\\\ -i\\sin\\tfrac{\\theta}{2} & \\cos\\tfrac{\\theta}{2}\\end{pmatrix}",
  },
  {
    type: "RY",
    label: "RY(θ)",
    category: "rotation",
    arity: 1,
    takesTheta: true,
    color: "var(--gate-rot)",
    description: "Rotation around Y axis by angle θ.",
    latex:
      "R_y(\\theta) = \\begin{pmatrix}\\cos\\tfrac{\\theta}{2} & -\\sin\\tfrac{\\theta}{2} \\\\ \\sin\\tfrac{\\theta}{2} & \\cos\\tfrac{\\theta}{2}\\end{pmatrix}",
  },
  {
    type: "RZ",
    label: "RZ(θ)",
    category: "rotation",
    arity: 1,
    takesTheta: true,
    color: "var(--gate-rot)",
    description: "Rotation around Z axis by angle θ.",
    latex:
      "R_z(\\theta) = \\begin{pmatrix}e^{-i\\theta/2} & 0 \\\\ 0 & e^{i\\theta/2}\\end{pmatrix}",
  },
  {
    type: "CNOT",
    label: "CNOT",
    category: "two",
    arity: 2,
    takesTheta: false,
    color: "var(--gate-cnot)",
    description:
      "Controlled-NOT. Flips target iff control is |1>. Source of entanglement.",
    latex:
      "\\mathrm{CNOT} = \\begin{pmatrix}1&0&0&0\\\\0&1&0&0\\\\0&0&0&1\\\\0&0&1&0\\end{pmatrix}",
  },
  {
    type: "M",
    label: "M",
    category: "measure",
    arity: 1,
    takesTheta: false,
    color: "var(--gate-measure)",
    description: "Measurement marker (Z-basis).",
    latex: "M_z = \\sum_{i\\in\\{0,1\\}} |i\\rangle\\langle i|",
  },
] as const;

export function gateMeta(type: GateType): GateMeta {
  const meta = GATE_CATALOG.find((g) => g.type === type);
  if (!meta) {
    throw new Error(`Unknown gate type: ${type}`);
  }
  return meta;
}
