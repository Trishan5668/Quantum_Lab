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
import {
  basisStateResult,
  basisStateSnapshot,
  normalizeBasisState,
} from "../utils/basisState";

const MAX_QUBITS = 8;

interface CircuitActions {
  addQubit: () => void;
  addQubitWithBasisState: (basisState: string) => void;
  removeQubit: () => void;
  setNumQubits: (n: number) => void;
  setInitialBasisState: (basisState: string) => void;
  resetInitialBasisState: () => void;
  randomizeInitialBasisState: () => void;
  addGate: (gateType: GateType, qubitTargets: number[], timeStep: number, theta?: number) => void;
  removeGate: (id: string) => void;
  decrementGateStack: (id: string) => void;
  updateGateParams: (id: string, params: Partial<GatePlacement["params"]>) => void;
  moveGate: (id: string, newTimeStep: number, newQubitTargets?: number[]) => void;
  clearCircuit: () => void;
  loadPreset: (preset: {
    numQubits: number;
    gates: Omit<GatePlacement, "id">[];
    simulationMode?: SimulationMode;
    noiseEnabled?: boolean;
    fidelityTarget?: FidelityTarget;
    initialBasisState?: string;
  }) => void;
  loadSavedCircuit: (saved: {
    numQubits: number;
    initialBasisState?: string;
    selectedBasisState?: string;
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
  initialBasisState: "0",
  selectedBasisState: "0",
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
  stack_count?: number;
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
    stack_count: step.stack_count ?? 1,
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
      const nextN = s.numQubits + 1;
      const nextBasis = "0".repeat(nextN);
      return {
        numQubits: nextN,
        initialBasisState: nextBasis,
        selectedBasisState: nextBasis,
        results: basisStateResult(nextN, nextBasis),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  addQubitWithBasisState: (basisState) =>
    set((s) => {
      if (s.numQubits >= MAX_QUBITS) return s;
      const nextN = s.numQubits + 1;
      const nextBasis = normalizeBasisState(nextN, basisState);
      return {
        numQubits: nextN,
        initialBasisState: nextBasis,
        selectedBasisState: nextBasis,
        results: basisStateResult(nextN, nextBasis),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
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
        initialBasisState: normalizeBasisState(newN, s.initialBasisState.slice(0, newN)),
        selectedBasisState: normalizeBasisState(newN, s.selectedBasisState.slice(0, newN)),
        gates: filtered,
        results: basisStateResult(newN, s.initialBasisState.slice(0, newN)),
        resultsV2: null,
        metrics: null,
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
        initialBasisState: "0".repeat(clamped),
        selectedBasisState: "0".repeat(clamped),
        gates: filtered,
        results: basisStateResult(clamped),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  setInitialBasisState: (basisState) =>
    set((s) => {
      const nextBasis = normalizeBasisState(s.numQubits, basisState);
      return {
        initialBasisState: nextBasis,
        selectedBasisState: nextBasis,
        results: basisStateResult(s.numQubits, nextBasis),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  resetInitialBasisState: () =>
    set((s) => {
      const nextBasis = "0".repeat(s.numQubits);
      return {
        initialBasisState: nextBasis,
        selectedBasisState: nextBasis,
        results: basisStateResult(s.numQubits, nextBasis),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  randomizeInitialBasisState: () =>
    set((s) => {
      const index = Math.floor(Math.random() * (1 << s.numQubits));
      const nextBasis = index.toString(2).padStart(s.numQubits, "0");
      return {
        initialBasisState: nextBasis,
        selectedBasisState: nextBasis,
        results: basisStateResult(s.numQubits, nextBasis),
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  addGate: (gateType, qubitTargets, timeStep, theta) =>
    set((s) => {
      if (qubitTargets.some((q) => q < 0 || q >= s.numQubits)) return s;
      const params = theta !== undefined ? { theta } : {};
      const existing = s.gates.find((g) =>
        isSameGateLocation(g, gateType, qubitTargets, timeStep, params),
      );
      if (existing) {
        return {
          gates: s.gates.map((g) =>
            g.id === existing.id ? { ...g, stackCount: (g.stackCount ?? 1) + 1 } : g,
          ),
          results: null,
          resultsV2: null,
          metrics: null,
          currentStep: 0,
        };
      }
      const placement: GatePlacement = {
        id: uuidv4(),
        gateType,
        qubitTargets,
        params,
        timeStep,
        stackCount: 1,
      };
      return {
        gates: [...s.gates, placement],
        results: null,
        resultsV2: null,
        metrics: null,
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

  decrementGateStack: (id) =>
    set((s) => {
      const gate = s.gates.find((g) => g.id === id);
      if (!gate) return s;
      const nextCount = (gate.stackCount ?? 1) - 1;
      return {
        gates: nextCount <= 0
          ? s.gates.filter((g) => g.id !== id)
          : s.gates.map((g) => (g.id === id ? { ...g, stackCount: nextCount } : g)),
        results: null,
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  updateGateParams: (id, params) =>
    set((s) => ({
      gates: s.gates.map((g) =>
        g.id === id ? { ...g, params: { ...g.params, ...params } } : g,
      ),
      results: null,
      resultsV2: null,
    })),

  moveGate: (id, newTimeStep, newQubitTargets) =>
    set((s) => {
      const moving = s.gates.find((g) => g.id === id);
      if (!moving) return s;
      const moved = {
        ...moving,
        timeStep: newTimeStep,
        ...(newQubitTargets ? { qubitTargets: newQubitTargets } : {}),
      };
      const target = s.gates.find((g) =>
        g.id !== id &&
        isSameGateLocation(g, moved.gateType, moved.qubitTargets, moved.timeStep, moved.params),
      );
      return {
        gates: target
          ? s.gates
              .filter((g) => g.id !== id)
              .map((g) => g.id === target.id ? { ...g, stackCount: (g.stackCount ?? 1) + (moving.stackCount ?? 1) } : g)
          : s.gates.map((g) => (g.id === id ? moved : g)),
        results: null,
        resultsV2: null,
        metrics: null,
        currentStep: 0,
      };
    }),

  clearCircuit: () =>
    set((s) => ({
      gates: [],
      results: basisStateResult(s.numQubits, s.initialBasisState),
      resultsV2: null,
      metrics: null,
      currentStep: 0,
      lastError: null,
    })),

  loadPreset: (preset) =>
    set(() => {
      const nextBasis = normalizeBasisState(preset.numQubits, preset.initialBasisState);
      return {
      numQubits: preset.numQubits,
      initialBasisState: nextBasis,
      selectedBasisState: nextBasis,
      gates: preset.gates.map((g) => ({ ...g, id: uuidv4(), stackCount: g.stackCount ?? 1 })),
      simulationMode: preset.simulationMode ?? "statevector",
      noiseEnabled: preset.noiseEnabled ?? false,
      fidelityTarget: preset.fidelityTarget ?? "none",
      results: basisStateResult(preset.numQubits, nextBasis),
      resultsV2: null,
      metrics: null,
      currentStep: 0,
      lastError: null,
      stepMode: false,
      };
    }),

  loadSavedCircuit: (saved) =>
    set(() => {
      const nextBasis = normalizeBasisState(
        saved.numQubits,
        saved.initialBasisState ?? saved.selectedBasisState,
      );
      return {
      numQubits: saved.numQubits,
      initialBasisState: nextBasis,
      selectedBasisState: nextBasis,
      gates: saved.gates.map((g) => ({ ...g, stackCount: g.stackCount ?? 1 })),
      simulationMode: saved.simulationMode,
      noiseEnabled: saved.noiseEnabled,
      results: saved.results ?? basisStateResult(saved.numQubits, nextBasis),
      resultsV2: saved.resultsV2,
      metrics: null,
      currentStep: saved.results?.steps.length ?? 0,
      lastError: null,
      stepMode: false,
      isRunning: false,
      };
    }),

  run: async () => {
    const state = get();
    const { numQubits, gates, initialBasisState } = state;
    set({ isRunning: true, lastError: null, metrics: null });
    try {
      if (!usesV2(state)) {
        const result: SimulationResult = await runCircuit({ numQubits, gates, initialBasisState });
        set({
          results: result,
          resultsV2: null,
          isRunning: false,
          currentStep: result.steps.length,
        });
        return;
      }

      const resultV2 = await runCircuitV2({ numQubits, gates, initialBasisState }, {
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
    set((s) => ({
      simulationMode: mode,
      results: basisStateResult(s.numQubits, s.initialBasisState),
      resultsV2: null,
      metrics: null,
    })),
  setNoiseEnabled: (enabled) =>
    set((s) => ({
      noiseEnabled: enabled,
      results: basisStateResult(s.numQubits, s.initialBasisState),
      resultsV2: null,
      metrics: null,
    })),
  setNoiseModel: (model) =>
    set((s) => ({
      noiseModel: model,
      results: basisStateResult(s.numQubits, s.initialBasisState),
      resultsV2: null,
      metrics: null,
    })),
  setNoiseProbability: (p) =>
    set((s) => ({
      noiseProbability: p,
      results: basisStateResult(s.numQubits, s.initialBasisState),
      resultsV2: null,
      metrics: null,
    })),
  setT1Us: (v) =>
    set((s) => ({ t1Us: v, results: basisStateResult(s.numQubits, s.initialBasisState), resultsV2: null, metrics: null })),
  setT2Us: (v) =>
    set((s) => ({ t2Us: v, results: basisStateResult(s.numQubits, s.initialBasisState), resultsV2: null, metrics: null })),
  setGateTimeNs: (v) =>
    set((s) => ({ gateTimeNs: v, results: basisStateResult(s.numQubits, s.initialBasisState), resultsV2: null, metrics: null })),
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
      return basisStateSnapshot(s.numQubits, s.initialBasisState);
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

function isSameGateLocation(
  gate: GatePlacement,
  gateType: GateType,
  qubitTargets: number[],
  timeStep: number,
  params: Partial<GatePlacement["params"]>,
): boolean {
  return (
    gate.gateType === gateType &&
    gate.timeStep === timeStep &&
    sameTargets(gate.qubitTargets, qubitTargets) &&
    sameParams(gate.params, params)
  );
}

function sameTargets(a: number[], b: number[]): boolean {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function sameParams(a: Partial<GatePlacement["params"]>, b: Partial<GatePlacement["params"]>): boolean {
  const thetaA = a.theta;
  const thetaB = b.theta;
  if (thetaA === undefined && thetaB === undefined) return true;
  if (thetaA === undefined || thetaB === undefined) return false;
  return Math.abs(thetaA - thetaB) < 1e-12;
}

export const MAX_QUBITS_CONST = MAX_QUBITS;
