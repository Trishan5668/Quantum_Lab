import type { ComplexAmplitude, SimulationResult, StateSnapshot } from "../types";

export function normalizeBasisState(numQubits: number, basisState?: string | null): string {
  const fallback = "0".repeat(numQubits);
  if (!basisState || basisState.length !== numQubits || /[^01]/.test(basisState)) {
    return fallback;
  }
  return basisState;
}

export function basisIndex(basisState: string): number {
  return Number.parseInt(basisState, 2);
}

export function basisLabelsFor(numQubits: number): string[] {
  return Array.from({ length: 1 << numQubits }, (_, i) => `|${i.toString(2).padStart(numQubits, "0")}>`);
}

export function displayKet(binary: string): string {
  return `|${binary}\u27e9`;
}

export function generateBasisStates(numQubits: number): string[] {
  return Array.from({ length: 1 << numQubits }, (_, i) => i.toString(2).padStart(numQubits, "0"));
}

export function basisStateVector(numQubits: number, basisState?: string | null): ComplexAmplitude[] {
  const selected = normalizeBasisState(numQubits, basisState);
  const selectedIndex = basisIndex(selected);
  return Array.from({ length: 1 << numQubits }, (_, i) => ({
    real: i === selectedIndex ? 1 : 0,
    imag: 0,
  }));
}

export function basisStateSnapshot(numQubits: number, basisState?: string | null): StateSnapshot {
  const selected = normalizeBasisState(numQubits, basisState);
  const selectedIndex = basisIndex(selected);
  return {
    num_qubits: numQubits,
    amplitudes: basisStateVector(numQubits, selected),
    probabilities: Array.from({ length: 1 << numQubits }, (_, i) => (i === selectedIndex ? 1 : 0)),
    basis_labels: basisLabelsFor(numQubits),
  };
}

export function basisStateResult(numQubits: number, basisState?: string | null): SimulationResult {
  return {
    num_qubits: numQubits,
    execution_time_ms: 0,
    steps: [],
    final_state: basisStateSnapshot(numQubits, basisState),
  };
}
