import { create } from "zustand";

export type LearningMode = "explore" | "understand" | "intuition" | "research";
export type WorkspacePanel = "learning" | "math" | "physics";
export type LearningLayer = LearningMode;

interface PlatformState {
  learningMode: LearningMode;
  activeWorkspacePanel: WorkspacePanel;
  setLearningMode: (mode: LearningMode) => void;
  setActiveWorkspacePanel: (panel: WorkspacePanel) => void;
  learningLayer: LearningLayer;
  setLearningLayer: (layer: LearningLayer) => void;
}

export const usePlatformStore = create<PlatformState>((set) => ({
  learningMode: "explore",
  activeWorkspacePanel: "learning",
  learningLayer: "explore",
  setLearningMode: (mode) => set({ learningMode: mode, learningLayer: mode }),
  setActiveWorkspacePanel: (panel) => set({ activeWorkspacePanel: panel }),
  setLearningLayer: (layer) => set({ learningMode: layer, learningLayer: layer }),
}));

export const LEARNING_LAYERS: {
  id: LearningMode;
  label: string;
  tagline: string;
  description: string;
}[] = [
  {
    id: "explore",
    label: "Explore",
    tagline: "Visual learning",
    description: "Build circuits, watch probabilities and the Bloch sphere. No equations required.",
  },
  {
    id: "understand",
    label: "Understand",
    tagline: "Reveal the math",
    description: "State vectors, amplitudes, basis kets, and tensor products appear as you need them.",
  },
  {
    id: "intuition",
    label: "Intuition",
    tagline: "Plain English",
    description: "Phase, interference, measurement, entanglement, and decoherence explained clearly.",
  },
  {
    id: "research",
    label: "Research",
    tagline: "Full depth",
    description: "Density matrices, Kraus operators, entropy, fidelity, noise models, and reduced states.",
  },
];
