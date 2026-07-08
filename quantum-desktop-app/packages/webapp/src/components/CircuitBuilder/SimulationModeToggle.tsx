import { useCircuitStore } from "../../store/circuitStore";
import type { FidelityTarget, SimulationMode } from "../../types";

export function SimulationModeToggle(): JSX.Element {
  const simulationMode = useCircuitStore((s) => s.simulationMode);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const fidelityTarget = useCircuitStore((s) => s.fidelityTarget);
  const setSimulationMode = useCircuitStore((s) => s.setSimulationMode);
  const setFidelityTarget = useCircuitStore((s) => s.setFidelityTarget);

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Simulation settings">
      <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Mode</span>
      {(["statevector", "density"] as SimulationMode[]).map((mode) => (
        <button
          key={mode}
          type="button"
          onClick={() => setSimulationMode(mode)}
          aria-pressed={simulationMode === mode}
          className={`btn btn-sm rounded-md border px-2 py-1 font-mono transition ${
            simulationMode === mode
              ? "border-accent-glow bg-accent-quantum/15 text-accent-glow"
              : "btn-secondary border-border text-text-secondary"
          }`}
          title={
            mode === "statevector"
              ? "Pure statevector simulation (default)"
              : "Density matrix evolution"
          }
        >
          {mode === "statevector" ? "Statevector" : "Density"}
        </button>
      ))}
      {noiseEnabled && (
        <span className="rounded-full bg-amber-500/15 px-2 py-0.5 font-mono text-[10px] text-amber-300 ring-1 ring-amber-500/30">
          Noise on
        </span>
      )}
      <select
        value={fidelityTarget}
        onChange={(e) => setFidelityTarget(e.target.value as FidelityTarget)}
        className="max-w-[10rem] truncate rounded-md border border-border bg-bg-base px-2 py-1 font-mono text-[10px] text-text-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
        title="Target state for fidelity metric"
        aria-label="Fidelity target"
      >
        <option value="none">Fidelity: none</option>
        <option value="bell">Fidelity: Bell</option>
        <option value="ghz">Fidelity: GHZ</option>
        <option value="zero">Fidelity: |0…0⟩</option>
      </select>
    </div>
  );
}
