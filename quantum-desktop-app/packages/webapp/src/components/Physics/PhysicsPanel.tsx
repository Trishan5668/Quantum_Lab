import { useMemo } from "react";
import { useCircuitStore } from "../../store/circuitStore";
import { FullscreenReport, ReportReader } from "../Reports/ReportReader";
import { PanelPlaceholder, PanelSection } from "../ui/PanelSection";
import { buildPhysicsReport } from "./physicsReport";

export function PhysicsPanel(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const gates = useCircuitStore((s) => s.gates);
  const results = useCircuitStore((s) => s.results);
  const resultsV2 = useCircuitStore((s) => s.resultsV2);
  const metrics = useCircuitStore((s) => s.metrics);
  const sections = useMemo(
    () =>
      buildPhysicsReport({
        numQubits,
        gates,
        steps: results?.steps,
        resultsV2,
        metrics,
      }),
    [gates, metrics, numQubits, results?.steps, resultsV2],
  );

  const subtitle = results
    ? `Generated from the latest simulation: ${gates.length} gate${gates.length === 1 ? "" : "s"}, ${numQubits} qubit${numQubits === 1 ? "" : "s"}`
    : "Run the circuit to generate the physics report from simulator data";

  return (
    <PanelSection
      title="Physics"
      subtitle="Why the circuit behaves this way"
      actions={
        <FullscreenReport label="Physics fullscreen" title="QuantumLab Physics Report" subtitle={subtitle}>
          <ReportReader title="QuantumLab Physics Report" subtitle={subtitle} sections={sections} />
        </FullscreenReport>
      }
    >
      {!results && gates.length > 0 && (
        <PanelPlaceholder>Run the circuit to bind this report to the latest simulator output.</PanelPlaceholder>
      )}
      <ReportReader title="QuantumLab Physics Report" subtitle={subtitle} sections={sections} compact />
    </PanelSection>
  );
}
