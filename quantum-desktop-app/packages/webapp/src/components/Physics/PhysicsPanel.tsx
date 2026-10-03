import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { fetchResearchVerification } from "../../apiV2";
import { useCircuitStore } from "../../store/circuitStore";
import type { ResearchVerification } from "../../types";
import { FullscreenReport, ReportReader } from "../Reports/ReportReader";
import { PanelPlaceholder, PanelSection } from "../ui/PanelSection";
import { buildPhysicsReport } from "./physicsReport";

export function PhysicsPanel(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const initialBasisState = useCircuitStore((s) => s.initialBasisState);
  const gates = useCircuitStore((s) => s.gates);
  const results = useCircuitStore((s) => s.results);
  const resultsV2 = useCircuitStore((s) => s.resultsV2);
  const metrics = useCircuitStore((s) => s.metrics);
  const simulationMode = useCircuitStore((s) => s.simulationMode);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const noiseModel = useCircuitStore((s) => s.noiseModel);
  const noiseProbability = useCircuitStore((s) => s.noiseProbability);
  const t1Us = useCircuitStore((s) => s.t1Us);
  const t2Us = useCircuitStore((s) => s.t2Us);
  const gateTimeNs = useCircuitStore((s) => s.gateTimeNs);
  const { profile, user } = useAuth();
  const [verification, setVerification] = useState<ResearchVerification | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setVerification(null);
    setVerificationError(null);
    fetchResearchVerification(
      { numQubits, gates, initialBasisState },
      { simulationMode, noiseEnabled, noiseModel, noiseProbability, t1Us, t2Us, gateTimeNs },
      resultsV2,
    )
      .then((data) => {
        if (!cancelled) setVerification(data);
      })
      .catch((err) => {
        if (!cancelled) setVerificationError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [gateTimeNs, gates, initialBasisState, noiseEnabled, noiseModel, noiseProbability, numQubits, resultsV2, simulationMode, t1Us, t2Us]);
  const sections = useMemo(
    () =>
      buildPhysicsReport({
        numQubits,
        initialBasisState,
        gates,
        steps: results?.steps,
        resultsV2,
        metrics,
        verification,
        verificationError,
      }),
    [gates, initialBasisState, metrics, numQubits, results?.steps, resultsV2, verification, verificationError],
  );

  const subtitle = results
    ? `Generated from the latest simulation: ${gates.length} gate${gates.length === 1 ? "" : "s"}, ${numQubits} qubit${numQubits === 1 ? "" : "s"}`
    : "Run the circuit to generate the physics report from simulator data";
  const metadata = useMemo(
    () => ({
      reportKind: "Physics",
      circuitName: circuitName(gates),
      qubitCount: numQubits,
      gateCount: gates.length,
      initialState: `|${initialBasisState}>`,
      simulationMode: resultsV2?.simulation_mode ?? simulationMode,
      noiseModel: noiseEnabled ? `${noiseModel} p=${noiseProbability}` : "Ideal",
      authorName: profile?.name ?? user?.displayName ?? user?.email ?? undefined,
      authorId: profile?.uid ?? user?.uid,
      circuitJson: {
        numQubits,
        initialBasisState,
        gates,
        simulationMode,
        noiseEnabled,
        noiseModel,
      },
      gateSequence: gates.map((gate) => `${gate.gateType}${gate.stackCount && gate.stackCount > 1 ? `^${gate.stackCount}` : ""} q[${gate.qubitTargets.join(",")}] @t${gate.timeStep}`),
      backendVersion: resultsV2 ? "v2" : results ? "v1" : "not run",
    }),
    [gates, initialBasisState, noiseEnabled, noiseModel, noiseProbability, numQubits, profile?.name, profile?.uid, results, resultsV2, simulationMode, user?.displayName, user?.email, user?.uid],
  );

  return (
    <PanelSection
      title="Physics"
      subtitle="Why the circuit behaves this way"
      actions={
        <FullscreenReport label="Physics fullscreen" title="QuantumLab Physics Report" subtitle={subtitle}>
          <div className="physics-report-surface physics-report-fullscreen">
            <ReportReader title="QuantumLab Physics Report" subtitle={subtitle} sections={sections} metadata={metadata} />
          </div>
        </FullscreenReport>
      }
    >
      {!results && gates.length > 0 && (
        <PanelPlaceholder>Run the circuit to bind this report to the latest simulator output.</PanelPlaceholder>
      )}
      <div className="physics-report-surface">
        <ReportReader title="QuantumLab Physics Report" subtitle={subtitle} sections={sections} metadata={metadata} compact />
      </div>
    </PanelSection>
  );
}

function circuitName(gates: { gateType: string }[]): string {
  if (gates.length === 0) return "Initial State Preparation";
  const labels = gates.slice(0, 4).map((gate) => gate.gateType).join("-");
  return `${labels}${gates.length > 4 ? "-..." : ""} Circuit`;
}
