import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import { runCircuit, ApiClientError } from "../api";
import {
  runCircuitV2,
  fetchFidelity,
  fetchEntropy,
  fetchPurity,
  fetchPurityFromDensity,
  ApiV2ClientError,
} from "../apiV2";
import type {
  CircuitState,
  ComplexAmplitude,
  FidelityTarget,
  GatePlacement,
  GateType,
  NoiseChannelType,
  SimulationMode,
  SimulationResult,
  SimulationResultV2,
  StateSnapshot,
  StepResult,
  MetricsResult,
} from "../types";
import { BACKEND_UNAVAILABLE_MESSAGE } from "../config/api";

const MAX_QUBITS = 8;

interface CircuitActions {
  addQubit: () => void;
  removeQubit: () => void;
  setNumQubits: (n: number) => void;
  addGate: (gateType: GateType, qubitTargets: number[], timeStep: number, theta?: number) => void;
  removeGate: (id: string) => void;
  updateGateParams: (id: string, params: Partial<GatePlacement["params"]>) => void;
  moveGate: (id: string, newTimeStep: number, newQubitTargets?: number[]) => void;
  clearCircuit: () => void;
  loadPreset: (preset: {
    numQubits: number;
    gates: Omit<GatePlacement, "id">[];
    simulationMode?: SimulationMode;
    noiseEnabled?: boolean;
    fidelityTarget?: FidelityTarget;
  }) => void;
  loadSavedCircuit: (saved: {
    numQubits: number;
    gates: GatePlacement[];
    simulationMode: SimulationMode;
    results: SimulationResult | null;
    resultsV2: SimulationResultV2 | null;
    noiseEnabled: boolean;
  }) => void;
  run: () => Promise<void>;
  setStepMode: (enabled: boolean) => void;
  stepForward: () => void;
  stepBackward: () => void;
  resetSteps: () => void;
  setError: (msg: string | null) => void;
  setSimulationMode: (mode: SimulationMode) => void;
  setNoiseEnabled: (enabled: boolean) => void;
  setNoiseModel: (model: NoiseChannelType) => void;
  setNoiseProbability: (p: number) => void;
  setT1Us: (v: number) => void;
  setT2Us: (v: number) => void;
  setGateTimeNs: (v: number) => void;
  setFidelityTarget: (target: FidelityTarget) => void;
}

type Store = CircuitState & CircuitActions;

const initialState: CircuitState = {
  numQubits: 1,
  gates: [],
  results: null,
  resultsV2: null,
  isRunning: false,
  stepMode: false,
  currentStep: 0,
  lastError: null,
  simulationMode: "statevector",
  noiseEnabled: false,
  noiseModel: "depolarizing",
  noiseProbability: 0.01,
  t1Us: 50,
  t2Us: 25,
  gateTimeNs: 50,
  fidelityTarget: "none",
  metrics: null,
};

function usesV2(state: Pick<CircuitState, "simulationMode" | "noiseEnabled">): boolean {
  return state.simulationMode === "density" || state.noiseEnabled;
}

/** V2 density steps expose ``density_after`` instead of ``state_after``. */
interface RawV2Step {
  gate_id: string;
  gate_type: string;
  qubit_targets: number[];
  params: Record<string, number>;
  time_step: number;
  state_after?: StateSnapshot;
  density_after?: {
    amplitudes?: ComplexAmplitude[];
    probabilities: number[];
    basis_labels: string[];
  };
  probabilities: number[];
}

function snapshotFromV2Step(step: RawV2Step, numQubits: number): StateSnapshot {
  if (step.state_after) {
    return {
      ...step.state_after,
      amplitudes: step.state_after.amplitudes ?? [],
      probabilities: step.state_after.probabilities ?? [],
      basis_labels: step.state_after.basis_labels ?? [],
    };
  }
  const density = step.density_after;
  return {
    num_qubits: numQubits,
    amplitudes: density?.amplitudes ?? [],
    probabilities: density?.probabilities ?? step.probabilities ?? [],
    basis_labels: density?.basis_labels ?? [],
  };
}

export function normalizeV2ToSimulationResult(resultV2: SimulationResultV2): SimulationResult {
  const steps: StepResult[] = (resultV2.steps as RawV2Step[]).map((step) => ({
    gate_id: step.gate_id,
    gate_type: step.gate_type,
    qubit_targets: step.qubit_targets,
    params: step.params ?? {},
    time_step: step.time_step,
    state_after: snapshotFromV2Step(step, resultV2.num_qubits),
    probabilities: step.probabilities,
  }));
  return {
    num_qubits: resultV2.num_qubits,
    execution_time_ms: resultV2.execution_time_ms,
    steps,
    final_state: {
      ...resultV2.final_state,
      amplitudes: resultV2.final_state.amplitudes ?? [],
      probabilities: resultV2.final_state.probabilities ?? [],
      basis_labels: resultV2.final_state.basis_labels ?? [],
    },
  };
}

export const useCircuitStore = create<Store>((set, get) => ({
  ...initialState,

  addQubit: () =>
    set((s) => {
      if (s.numQubits >= MAX_QUBITS) return s;
      return { numQubits: s.numQubits + 1, results: null, resultsV2: null, currentStep: 0 };
    }),

  removeQubit: () =>
    set((s) => {
      if (s.numQubits <= 1) return s;
      const newN = s.numQubits - 1;
      const filtered = s.gates.filter((g) =>
        g.qubitTargets.every((q) => q < newN),
      );
      return {
        numQubits: newN,
        gates: filtered,
        results: null,
        resultsV2: null,
        currentStep: 0,
      };
    }),

  setNumQubits: (n) =>
    set((s) => {
      const clamped = Math.max(1, Math.min(MAX_QUBITS, n));
      const filtered = s.gates.filter((g) =>
        g.qubitTargets.every((q) => q < clamped),
      );
      return {
        numQubits: clamped,
        gates: filtered,
        results: null,
        resultsV2: null,
        currentStep: 0,
      };
    }),

  addGate: (gateType, qubitTargets, timeStep, theta) =>
    set((s) => {
      if (qubitTargets.some((q) => q < 0 || q >= s.numQubits)) return s;
      const placement: GatePlacement = {
        id: uuidv4(),
        gateType,
        qubitTargets,
        params: theta !== undefined ? { theta } : {},
        timeStep,
      };
      return {
        gates: [...s.gates, placement],
        results: null,
        resultsV2: null,
        currentStep: 0,
      };
    }),

  removeGate: (id) =>
    set((s) => ({
      gates: s.gates.filter((g) => g.id !== id),
      results: null,
      resultsV2: null,
      currentStep: 0,
    })),

  updateGateParams: (id, params) =>
    set((s) => ({
      gates: s.gates.map((g) =>
        g.id === id ? { ...g, params: { ...g.params, ...params } } : g,
      ),
      results: null,
      resultsV2: null,
    })),

  moveGate: (id, newTimeStep, newQubitTargets) =>
    set((s) => ({
      gates: s.gates.map((g) =>
        g.id === id
          ? {
              ...g,
              timeStep: newTimeStep,
              ...(newQubitTargets ? { qubitTargets: newQubitTargets } : {}),
            }
          : g,
      ),
      results: null,
      resultsV2: null,
      currentStep: 0,
    })),

  clearCircuit: () =>
    set({
      gates: [],
      results: null,
      resultsV2: null,
      metrics: null,
      currentStep: 0,
      lastError: null,
    }),

  loadPreset: (preset) =>
    set({
      numQubits: preset.numQubits,
      gates: preset.gates.map((g) => ({ ...g, id: uuidv4() })),
      simulationMode: preset.simulationMode ?? "statevector",
      noiseEnabled: preset.noiseEnabled ?? false,
      fidelityTarget: preset.fidelityTarget ?? "none",
      results: null,
      resultsV2: null,
      metrics: null,
      currentStep: 0,
      lastError: null,
      stepMode: false,
    }),

  loadSavedCircuit: (saved) =>
    set({
      numQubits: saved.numQubits,
      gates: saved.gates,
      simulationMode: saved.simulationMode,
      noiseEnabled: saved.noiseEnabled,
      results: saved.results,
      resultsV2: saved.resultsV2,
      metrics: null,
      currentStep: saved.results?.steps.length ?? 0,
      lastError: null,
      stepMode: false,
      isRunning: false,
    }),

  run: async () => {
    const state = get();
    const { numQubits, gates } = state;
    set({ isRunning: true, lastError: null, metrics: null });
    try {
      if (!usesV2(state)) {
        const result: SimulationResult = await runCircuit({ numQubits, gates });
        set({
          results: result,
          resultsV2: null,
          isRunning: false,
          currentStep: result.steps.length,
        });
        return;
      }

      const resultV2 = await runCircuitV2({ numQubits, gates }, {
        simulationMode: state.simulationMode,
        noiseEnabled: state.noiseEnabled,
        noiseModel: state.noiseModel,
        noiseProbability: state.noiseProbability,
        t1Us: state.t1Us,
        t2Us: state.t2Us,
        gateTimeNs: state.gateTimeNs,
      });

      const mapped = normalizeV2ToSimulationResult(resultV2);

      let metrics: MetricsResult = { fidelity: null, entropy: null, purity: null };

      const amps = resultV2.final_state.amplitudes;
      const density = resultV2.final_density;

      if (state.fidelityTarget !== "none") {
        metrics.fidelity = await fetchFidelity(numQubits, state.fidelityTarget, {
          amplitudes: amps.length > 0 ? amps : undefined,
          density: amps.length === 0 ? density ?? undefined : undefined,
        });
      }

      if (amps.length > 0) {
        metrics.purity = await fetchPurity(numQubits, amps);
      } else if (density) {
        metrics.purity = await fetchPurityFromDensity(numQubits, density);
      }

      if (density && numQubits >= 2) {
        metrics.entropy = await fetchEntropy(numQubits, [0], density);
      }

      set({
        results: mapped,
        resultsV2: resultV2,
        metrics,
        isRunning: false,
        currentStep: mapped.steps.length,
      });
    } catch (err) {
      const message =
        err instanceof ApiClientError || err instanceof ApiV2ClientError
          ? err.status === 0
            ? BACKEND_UNAVAILABLE_MESSAGE
            : `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : String(err);
      set({ isRunning: false, lastError: message });
    }
  },

  setStepMode: (enabled) => set({ stepMode: enabled, currentStep: 0 }),
  stepForward: () =>
    set((s) => {
      if (!s.results) return s;
      return {
        currentStep: Math.min(s.currentStep + 1, s.results.steps.length),
      };
    }),
  stepBackward: () =>
    set((s) => ({
      currentStep: Math.max(0, s.currentStep - 1),
    })),
  resetSteps: () => set({ currentStep: 0 }),
  setError: (msg) => set({ lastError: msg }),
  setSimulationMode: (mode) =>
    set({ simulationMode: mode, results: null, resultsV2: null, metrics: null }),
  setNoiseEnabled: (enabled) =>
    set({ noiseEnabled: enabled, results: null, resultsV2: null, metrics: null }),
  setNoiseModel: (model) =>
    set({ noiseModel: model, results: null, resultsV2: null, metrics: null }),
  setNoiseProbability: (p) =>
    set({ noiseProbability: p, results: null, resultsV2: null, metrics: null }),
  setT1Us: (v) => set({ t1Us: v, results: null, resultsV2: null, metrics: null }),
  setT2Us: (v) => set({ t2Us: v, results: null, resultsV2: null, metrics: null }),
  setGateTimeNs: (v) => set({ gateTimeNs: v, results: null, resultsV2: null, metrics: null }),
  setFidelityTarget: (target) => set({ fidelityTarget: target }),
}));

export function selectCurrentState(s: CircuitState): {
  num_qubits: number;
  amplitudes: { real: number; imag: number }[];
  probabilities: number[];
  basis_labels: string[];
} | null {
  if (!s.results) return null;
  if (s.stepMode) {
    if (s.currentStep <= 0) {
      const n = s.numQubits;
      const dim = 1 << n;
      const amps = Array.from({ length: dim }, (_, i) => ({
        real: i === 0 ? 1 : 0,
        imag: 0,
      }));
      const probs = Array.from({ length: dim }, (_, i) => (i === 0 ? 1 : 0));
      const labels = Array.from(
        { length: dim },
        (_, i) => `|${i.toString(2).padStart(n, "0")}>`,
      );
      return {
        num_qubits: n,
        amplitudes: amps,
        probabilities: probs,
        basis_labels: labels,
      };
    }
    const step = s.results.steps[s.currentStep - 1];
    if (!step) return s.results.final_state;
    return step.state_after ?? s.results.final_state;
  }
  return s.results.final_state;
}

export function selectDensityData(s: CircuitState) {
  return s.resultsV2?.final_density ?? null;
}

export const MAX_QUBITS_CONST = MAX_QUBITS;
