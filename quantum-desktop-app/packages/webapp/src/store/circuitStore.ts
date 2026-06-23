import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import { runCircuit, ApiClientError } from "../api";
import type { CircuitState, GatePlacement, GateType, SimulationResult } from "../types";

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
  run: () => Promise<void>;
  setStepMode: (enabled: boolean) => void;
  stepForward: () => void;
  stepBackward: () => void;
  resetSteps: () => void;
  setError: (msg: string | null) => void;
}

type Store = CircuitState & CircuitActions;

const initialState: CircuitState = {
  numQubits: 1,
  gates: [],
  results: null,
  isRunning: false,
  stepMode: false,
  currentStep: 0,
  lastError: null,
};

export const useCircuitStore = create<Store>((set, get) => ({
  ...initialState,

  addQubit: () =>
    set((s) => {
      if (s.numQubits >= MAX_QUBITS) return s;
      return { numQubits: s.numQubits + 1, results: null, currentStep: 0 };
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
        currentStep: 0,
      };
    }),

  removeGate: (id) =>
    set((s) => ({
      gates: s.gates.filter((g) => g.id !== id),
      results: null,
      currentStep: 0,
    })),

  updateGateParams: (id, params) =>
    set((s) => ({
      gates: s.gates.map((g) =>
        g.id === id ? { ...g, params: { ...g.params, ...params } } : g,
      ),
      results: null,
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
      currentStep: 0,
    })),

  clearCircuit: () =>
    set({ gates: [], results: null, currentStep: 0, lastError: null }),

  run: async () => {
    const { numQubits, gates } = get();
    set({ isRunning: true, lastError: null });
    try {
      const result: SimulationResult = await runCircuit({ numQubits, gates });
      set({
        results: result,
        isRunning: false,
        currentStep: result.steps.length,
      });
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? `${err.code}: ${err.message}`
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
    return step.state_after;
  }
  return s.results.final_state;
}

export const MAX_QUBITS_CONST = MAX_QUBITS;
