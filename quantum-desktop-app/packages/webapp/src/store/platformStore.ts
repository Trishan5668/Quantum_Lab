import { create } from "zustand";

export type WorkspacePanel = "learning" | "math" | "physics";

interface PlatformState {
  activeWorkspacePanel: WorkspacePanel;
  setActiveWorkspacePanel: (panel: WorkspacePanel) => void;
}

export const usePlatformStore = create<PlatformState>((set) => ({
  activeWorkspacePanel: "learning",
  setActiveWorkspacePanel: (panel) => set({ activeWorkspacePanel: panel }),
}));
