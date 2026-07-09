import { create } from "zustand";

export type LearningLayer = "explore" | "understand" | "intuition" | "research";

interface PlatformState {
  learningLayer: LearningLayer;
  setLearningLayer: (layer: LearningLayer) => void;
}

export const usePlatformStore = create<PlatformState>((set) => ({
  learningLayer: "explore",
  setLearningLayer: (layer) => set({ learningLayer: layer }),
}));

export const LEARNING_LAYERS: {
  id: LearningLayer;
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
