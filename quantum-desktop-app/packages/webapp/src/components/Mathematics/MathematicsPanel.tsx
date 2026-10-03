import { useMemo } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { useCircuitStore } from "../../store/circuitStore";
import type { GatePlacement } from "../../types";
import { PanelPlaceholder, PanelSection } from "../ui/PanelSection";
import { AmplitudeTable } from "./AmplitudeTable";
import { DensityDerivation } from "./DensityDerivation";
import { ExpandableProof } from "./ExpandableProof";
import { GateDerivation } from "./GateDerivation";
import { LatexBlock } from "./LatexBlock";
import { MeasurementProof } from "./MeasurementProof";
import { ProofTree } from "./ProofTree";
import { StateEvolution } from "./StateEvolution";
import { buildDerivation, noiseKrausLatex, vectorToLatex } from "./mathDerivations";
import { basisIndex, displayKet, normalizeBasisState } from "../../utils/basisState";
import { ResearchMathematicsReport } from "./ResearchMathematicsReport";

type Difficulty = "beginner" | "intermediate" | "advanced" | "research";

export function MathematicsPanel(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const initialBasisState = useCircuitStore((s) => s.initialBasisState);
  const gates = useCircuitStore((s) => s.gates);
  const results = useCircuitStore((s) => s.results);
  const resultsV2 = useCircuitStore((s) => s.resultsV2);
  const metrics = useCircuitStore((s) => s.metrics);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const noiseModel = useCircuitStore((s) => s.noiseModel);
  const noiseProbability = useCircuitStore((s) => s.noiseProbability);
  const t1Us = useCircuitStore((s) => s.t1Us);
  const t2Us = useCircuitStore((s) => s.t2Us);
  const gateTimeNs = useCircuitStore((s) => s.gateTimeNs);
  const { profile, user } = useAuth();

  const metadata = useMemo(
    () => ({
      reportKind: "Research Mathematics",
      circuitName: circuitName(gates),
      qubitCount: numQubits,
      gateCount: gates.length,
      initialState: displayKet(initialBasisState),
      simulationMode: resultsV2?.simulation_mode ?? "statevector",
      noiseModel: noiseEnabled ? `${noiseModel} p=${noiseProbability}` : "Ideal",
      authorName: profile?.name ?? user?.displayName ?? user?.email ?? undefined,
      authorId: profile?.uid ?? user?.uid,
      circuitJson: {
        numQubits,
        initialBasisState,
        gates,
        simulationMode: resultsV2?.simulation_mode ?? "statevector",
        noiseEnabled,
        noiseModel,
      },
      gateSequence: gates.map((gate) => `${gate.gateType}${gate.stackCount && gate.stackCount > 1 ? `^${gate.stackCount}` : ""} q[${gate.qubitTargets.join(",")}] @t${gate.timeStep}`),
      backendVersion: resultsV2 ? "v2" : results ? "v1" : "not run",
    }),
    [gates, initialBasisState, noiseEnabled, noiseModel, noiseProbability, numQubits, profile?.name, profile?.uid, results, resultsV2, user?.displayName, user?.email, user?.uid],
  );

  return (
    <PanelSection
      title="Mathematics"
      subtitle="Research-grade derivation, operator formalism, and publication exports"
    >
      <ResearchMathematicsReport
        numQubits={numQubits}
        initialBasisState={initialBasisState}
        gates={gates}
        resultSteps={results?.steps}
        resultsV2={resultsV2}
        metrics={metrics}
        simulationMode={resultsV2?.simulation_mode ?? "statevector"}
        noiseEnabled={noiseEnabled}
        noiseModel={noiseModel}
        noiseProbability={noiseProbability}
        t1Us={t1Us}
        t2Us={t2Us}
        gateTimeNs={gateTimeNs}
        metadata={metadata}
      />
    </PanelSection>
  );
}

function circuitName(gates: GatePlacement[]): string {
  if (gates.length === 0) return "Initial State Preparation";
  const labels = gates.slice(0, 4).map((gate) => gate.gateType).join("-");
  return `${labels}${gates.length > 4 ? "-..." : ""} Circuit`;
}

export function MathematicsPanelBody({
  numQubits,
  initialBasisState,
  gates,
  resultsV2,
  metrics,
  noiseEnabled,
  noiseModel,
  noiseProbability,
  t1Us,
  t2Us,
  gateTimeNs,
  difficulty,
  derivation,
}: {
  numQubits: number;
  initialBasisState: string;
  gates: GatePlacement[];
  resultsV2: ReturnType<typeof useCircuitStore.getState>["resultsV2"];
  metrics: ReturnType<typeof useCircuitStore.getState>["metrics"];
  noiseEnabled: boolean;
  noiseModel: ReturnType<typeof useCircuitStore.getState>["noiseModel"];
  noiseProbability: number;
  t1Us: number;
  t2Us: number;
  gateTimeNs: number;
  difficulty: Difficulty;
  derivation: ReturnType<typeof buildDerivation>;
}): JSX.Element {
  return (
    <>
      {gates.length === 0 ? (
        <EmptyDerivation numQubits={numQubits} initialBasisState={initialBasisState} />
      ) : (
        <div className="space-y-3">
          <InitialState
            gates={gates}
            numQubits={numQubits}
            initialBasisState={initialBasisState}
            vector={derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag }))}
          />
          {derivation.steps.map((step, index) => (
            <ExpandableProof
              key={step.placement.id}
              title={`${index + 1}. ${step.gate.label} on q[${step.placement.qubitTargets.join(", ")}]`}
              subtitle={`time step ${step.placement.timeStep}`}
              defaultOpen={index === 0}
            >
              <GateDerivation step={step} level={difficulty} />
              <StateEvolution step={step} basisLabels={derivation.basisLabels} level={difficulty} />
            </ExpandableProof>
          ))}
          <ExpandableProof title="Amplitude evolution" subtitle="basis, amplitude, magnitude, probability, phase">
            <AmplitudeTable snapshot={derivation.finalState} />
          </ExpandableProof>
          <ExpandableProof title="Measurement" subtitle="Born rule calculations">
            <MeasurementProof snapshot={derivation.finalState} />
          </ExpandableProof>
          {(difficulty === "advanced" || difficulty === "research") && (
            <ExpandableProof title="Density matrix" subtitle="outer product and purity">
              <DensityDerivation
                finalState={derivation.finalState}
                densityData={resultsV2?.final_density}
                purity={resultsV2?.purity ?? metrics?.purity?.purity}
              />
            </ExpandableProof>
          )}
          {noiseEnabled && (
            <ExpandableProof title="Noise channel" subtitle={noiseModel}>
              <NoiseProof
                channel={noiseModel}
                p={noiseProbability}
                t1Us={t1Us}
                t2Us={t2Us}
                gateTimeNs={gateTimeNs}
              />
            </ExpandableProof>
          )}
          <ExpandableProof title="Circuit summary" subtitle="complete derivation path">
            <CircuitSummary gates={gates} />
          </ExpandableProof>
          {difficulty === "research" && (
            <ExpandableProof title="Proof mode" subtitle="follow every why">
              <ProofTree />
              <ResearchFormulas entropy={metrics?.entropy?.entropy} fidelity={metrics?.fidelity?.fidelity} />
            </ExpandableProof>
          )}
        </div>
      )}
    </>
  );
}

function EmptyDerivation({ numQubits, initialBasisState }: { numQubits: number; initialBasisState: string }): JSX.Element {
  const initial = useMemo(() => buildDerivation(numQubits, [], undefined, initialBasisState), [numQubits, initialBasisState]);
  return (
    <div className="space-y-3">
      <PanelPlaceholder>Add gates to watch the derivation unfold live.</PanelPlaceholder>
      <InitialState
        gates={[]}
        numQubits={numQubits}
        initialBasisState={initialBasisState}
        vector={initial.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag }))}
      />
      <AmplitudeTable snapshot={initial.initialState} />
    </div>
  );
}

function InitialState({
  gates,
  numQubits,
  initialBasisState,
  vector,
}: {
  gates: GatePlacement[];
  numQubits: number;
  initialBasisState: string;
  vector: { re: number; im: number }[];
}): JSX.Element {
  const selected = normalizeBasisState(numQubits, initialBasisState);
  const selectedIndex = basisIndex(selected);
  const ket = `|${selected}\\rangle`;
  const tuple = vector.map((entry) => (Math.abs(entry.re - 1) < 1e-10 && Math.abs(entry.im) < 1e-10 ? "1" : "0")).join(",");
  return (
    <ExpandableProof
      title="Initial computational basis state"
      subtitle={gates.length ? `${gates.length} gate${gates.length === 1 ? "" : "s"} in circuit` : `selected ${displayKet(selected)}`}
      defaultOpen
    >
      <LatexBlock math={`${ket}\\;\\longrightarrow\\;${vectorToLatex(vector)}`} compact />
      <p className="font-mono text-xs leading-5 text-text-secondary">
        Corresponding basis vector: ({tuple})^T
      </p>
      <p className="text-xs leading-5 text-text-secondary">
        Initial state selected by user: {displayKet(selected)}. Basis states are listed in big-endian binary order, so {displayKet(selected)} has index {selectedIndex}; the amplitude at that index equals 1 and every other entry starts at 0.
      </p>
    </ExpandableProof>
  );
}

function NoiseProof({
  channel,
  p,
  t1Us,
  t2Us,
  gateTimeNs,
}: {
  channel: Parameters<typeof noiseKrausLatex>[0];
  p: number;
  t1Us: number;
  t2Us: number;
  gateTimeNs: number;
}): JSX.Element {
  const operators = noiseKrausLatex(channel, p, t1Us, t2Us, gateTimeNs);
  return (
    <div className="space-y-2">
      <LatexBlock math={"\\rho'=\\sum_i K_i\\rho K_i^{\\dagger}"} compact />
      {operators.map((operator) => (
        <LatexBlock key={operator} math={operator} compact />
      ))}
      <p className="text-xs leading-5 text-text-secondary">
        The backend applies these Kraus maps to the density matrix after each non-measurement gate when noise is enabled.
      </p>
    </div>
  );
}

function CircuitSummary({ gates }: { gates: GatePlacement[] }): JSX.Element {
  return (
    <ol className="grid gap-1 font-mono text-[11px] text-text-secondary">
      <li>Initial state</li>
      {gates.map((gate) => (
        <li key={gate.id}>{`down -> ${gate.gateType} -> tensor embedding -> matrix multiplication -> intermediate state`}</li>
      ))}
      <li>{"down -> Born rule -> probability distribution"}</li>
    </ol>
  );
}

function ResearchFormulas({ entropy, fidelity }: { entropy?: number; fidelity?: number }): JSX.Element {
  return (
    <div className="space-y-2">
      <LatexBlock label="Norm" math={"\\|\\psi\\|=\\sqrt{\\sum_i |a_i|^2}=1"} compact />
      <LatexBlock label="Expectation value" math={"\\langle A\\rangle=\\langle\\psi|A|\\psi\\rangle"} compact />
      <LatexBlock label="Entropy" math={`S(\\rho)=-\\mathrm{Tr}(\\rho\\log_2\\rho)${entropy === undefined ? "" : `=${entropy.toFixed(4)}`}`} compact />
      <LatexBlock label="Fidelity" math={`F(\\rho,\\sigma)=\\left(\\mathrm{Tr}\\sqrt{\\sqrt{\\rho}\\sigma\\sqrt{\\rho}}\\right)^2${fidelity === undefined ? "" : `=${fidelity.toFixed(4)}`}`} compact />
      <LatexBlock label="Pure-state fidelity simplification" math={"F(|\\psi\\rangle,|\\phi\\rangle)=|\\langle\\psi|\\phi\\rangle|^2"} compact />
      <LatexBlock label="Global phase" math={"e^{i\\varphi}|\\psi\\rangle\\sim|\\psi\\rangle"} compact />
      <LatexBlock label="Bloch angles" math={"|\\psi\\rangle=\\cos(\\theta/2)|0\\rangle+e^{i\\phi}\\sin(\\theta/2)|1\\rangle"} compact />
    </div>
  );
}
