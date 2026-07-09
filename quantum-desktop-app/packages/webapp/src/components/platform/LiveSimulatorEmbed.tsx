import { useEffect } from "react";
import { Link } from "react-router-dom";
import { CircuitCanvas } from "../CircuitBuilder/CircuitCanvas";
import { CircuitDiagram } from "../CircuitBuilder/CircuitDiagram";
import { CircuitDndProvider } from "../CircuitBuilder/CircuitDndProvider";
import { Toolbar } from "../CircuitBuilder/Toolbar";
import { ProbabilityChart } from "../Visualizations/ProbabilityChart";
import { useCircuitStore } from "../../store/circuitStore";
import { getAlgorithm } from "../../data/algorithms";
import { Button } from "../ui/Button";

/** Live simulator preview using real QuantumLab components — not a mockup. */
export function LiveSimulatorEmbed(): JSX.Element {
  const loadPreset = useCircuitStore((s) => s.loadPreset);
  const run = useCircuitStore((s) => s.run);
  const results = useCircuitStore((s) => s.results);

  useEffect(() => {
    const bell = getAlgorithm("bell-state");
    if (!bell) return;
    loadPreset({
      numQubits: bell.numQubits,
      gates: bell.gates,
      fidelityTarget: bell.fidelityTarget,
    });
    void run();
  }, [loadPreset, run]);

  return (
    <div className="live-simulator-embed panel-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-2.5">
        <div>
          <p className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-accent-measure">
            Live Preview
          </p>
          <p className="text-xs text-text-muted">Real simulator · Bell state preset</p>
        </div>
        <Link to="/app">
          <Button variant="primary" size="sm">
            Open Full Simulator
          </Button>
        </Link>
      </div>

      <CircuitDndProvider>
        <div className="live-simulator-grid">
          <div className="live-simulator-canvas min-h-0 overflow-hidden">
            <Toolbar compact />
            <div className="min-h-0 flex-1 overflow-hidden">
              <CircuitCanvas />
            </div>
          </div>
          <div className="live-simulator-side min-h-0 overflow-hidden border-l border-border/60">
            <div className="max-h-[9rem] min-h-0 overflow-hidden">
              <CircuitDiagram />
            </div>
            <div className="min-h-0 flex-1 overflow-hidden border-t border-border/60">
              <ProbabilityChart compact />
            </div>
          </div>
        </div>
      </CircuitDndProvider>

      {results && (
        <p className="border-t border-border/60 px-4 py-2 font-mono text-[10px] text-text-muted">
          Measured probabilities: [{results.final_state.probabilities.map((p) => p.toFixed(2)).join(", ")}]
        </p>
      )}
    </div>
  );
}
