import type { GatePlacement, SimulationMode, SimulationResult, SimulationResultV2 } from "../types";
export type PreferredNotation = "dirac" | "matrix" | "bloch";
export type SaveStatus = "idle" | "saving" | "saved" | "offline" | "error";

export interface UserPreferences {
  theme: "dark" | "light";
  defaultSimulationMode: SimulationMode;
  preferredNotation: PreferredNotation;
  autoSave: boolean;
  showAdvancedMathematics: boolean;
  showPhysicsReport: boolean;
}

export interface QuantumLabUser {
  uid: string;
  name: string;
  email: string;
  photoURL: string;
  provider: string;
  createdAt: string;
  lastLogin: string;
  role: "student" | "educator" | "admin";
  savedCircuits: string[];
  recentCircuits: string[];
  favoriteCircuits: string[];
  bookmarkedReports: string[];
  preferences: UserPreferences;
  theme: UserPreferences["theme"];
  defaultSimulationMode: SimulationMode;
  totalSimulationsRun: number;
  mostUsedGate: string;
  favoriteSimulationMode: SimulationMode;
}

export interface CircuitSnapshot {
  id?: string;
  name: string;
  userId: string;
  circuitJson: {
    numQubits: number;
    initialBasisState?: string;
    selectedBasisState?: string;
    gates: GatePlacement[];
    simulationMode: SimulationMode;
    noiseEnabled: boolean;
  };
  gateSequence: string[];
  simulationResult: SimulationResult | null;
  simulationResultV2: SimulationResultV2 | null;
  timestamp: string;
  qubitCount: number;
  gateCount: number;
  statevector: SimulationResult["final_state"] | null;
  densityMatrix: SimulationResultV2["final_density"] | null;
  measurementProbabilities: number[];
  explanationCache: Record<string, string>;
  physicsReport: string;
  mathReport: string;
  createdAt: string;
  modifiedAt: string;
  thumbnail: string;
  source: "autosave" | "manual" | "run";
}
