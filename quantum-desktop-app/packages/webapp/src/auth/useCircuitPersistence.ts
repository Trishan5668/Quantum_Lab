import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { buildCircuitSnapshot, saveCircuitSnapshot } from "./firebaseService";
import type { SaveStatus } from "./types";
import { useCircuitStore } from "../store/circuitStore";

export function useCircuitPersistence(): {
  saveStatus: SaveStatus;
  lastSavedAt: string | null;
  saveNow: (source?: "autosave" | "manual" | "run") => Promise<void>;
} {
  const { user, profile, openLogin } = useAuth();
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const circuitIdRef = useRef<string | undefined>();
  const dirtyRef = useRef(false);
  const lastResultsRef = useRef(useCircuitStore.getState().results);

  const saveNow = useCallback(
    async (source: "autosave" | "manual" | "run" = "manual") => {
      if (!user) {
        if (source === "manual") openLogin();
        return;
      }
      const state = useCircuitStore.getState();
      if (state.gates.length === 0 && source !== "manual") return;
      setSaveStatus(navigator.onLine ? "saving" : "offline");
      try {
        const snapshot = buildCircuitSnapshot(user.uid, state, source, circuitIdRef.current);
        const id = await saveCircuitSnapshot(snapshot);
        if (id) circuitIdRef.current = id;
        dirtyRef.current = false;
        const now = new Date().toISOString();
        setLastSavedAt(now);
        setSaveStatus(navigator.onLine ? "saved" : "offline");
      } catch {
        setSaveStatus("error");
      }
    },
    [openLogin, user],
  );

  useEffect(() => {
    const unsubscribe = useCircuitStore.subscribe((state, previous) => {
      const circuitChanged =
        state.numQubits !== previous.numQubits ||
        state.initialBasisState !== previous.initialBasisState ||
        state.selectedBasisState !== previous.selectedBasisState ||
        state.simulationMode !== previous.simulationMode ||
        state.noiseEnabled !== previous.noiseEnabled ||
        JSON.stringify(state.gates) !== JSON.stringify(previous.gates);
      if (circuitChanged) dirtyRef.current = true;

      if (state.results && state.results !== lastResultsRef.current) {
        lastResultsRef.current = state.results;
        void saveNow("run");
      }
    });
    return unsubscribe;
  }, [saveNow]);

  useEffect(() => {
    if (!profile?.preferences.autoSave) return;
    const id = window.setInterval(() => {
      if (dirtyRef.current) void saveNow("autosave");
    }, 5000);
    return () => window.clearInterval(id);
  }, [profile?.preferences.autoSave, saveNow]);

  return { saveStatus, lastSavedAt, saveNow };
}
