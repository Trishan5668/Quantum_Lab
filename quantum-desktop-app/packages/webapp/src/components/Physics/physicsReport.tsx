import type { ReactNode } from "react";
import { BlockMath, InlineMath } from "react-katex";
import {
  amplitudeRows,
  buildDerivation,
  complexToLatex,
  complexToText,
  densityFromData,
  densityFromState,
  type Complex,
  type ComplexMatrix,
} from "../Mathematics/mathDerivations";
import type { ReportSection } from "../Reports/ReportReader";
import type { GatePlacement, MetricsResult, ResearchVerification, SimulationResultV2, StateSnapshot } from "../../types";
import { displayKet, normalizeBasisState } from "../../utils/basisState";


function stackPhysicsInterpretation(
  gateName: string,
  stackCount: number
): string {
  if (stackCount <= 1) return "";

  if (gateName === "H") {
    return `Applying Hadamard ${stackCount} times corresponds to H^${stackCount}. Repeated applications can alternately create and remove superposition.`;
  }

  if (gateName === "X") {
    return `Applying X ${stackCount} times corresponds to repeated bit flips. X² = I, so even powers restore the original basis state.`;
  }

  if (gateName === "CNOT") {
    return `Applying CNOT ${stackCount} times corresponds to repeated controlled bit flips. CNOT² = I, so every pair of applications cancels out.`;
  }

  return `This operation applies ${gateName} ${stackCount} consecutive times, producing the effective operator ${gateName}^${stackCount}.`;
}


const EPS = 1e-10;
const ZERO: Complex = { re: 0, im: 0 };

interface PhysicsContext {
  numQubits: number;
  dim: number;
  gates: GatePlacement[];
  initialBasisState: string;
  derivation: ReturnType<typeof buildDerivation>;
  density: ComplexMatrix;
  reduced: ComplexMatrix;
  purity: number;
  reducedPurity: number;
  bloch: { x: number; y: number; z: number; length: number } | null;
  metrics: MetricsResult | null;
  motif: CircuitMotif;
  support: ReturnType<typeof amplitudeRows>;
  quietBasisCount: number;
  verification: ResearchVerification | null;
  verificationError: string | null;
}

type CircuitMotif =
  | "bell"
  | "ghz"
  | "teleportation-primitive"
  | "interference"
  | "phase-control"
  | "basis-transport"
  | "generic-entangling";

export function buildPhysicsReport({
  numQubits,
  initialBasisState,
  gates,
  steps,
  resultsV2,
  metrics,
  verification = null,
  verificationError = null,
}: {
  numQubits: number;
  initialBasisState?: string;
  gates: GatePlacement[];
  steps?: Parameters<typeof buildDerivation>[2];
  resultsV2: SimulationResultV2 | null;
  metrics: MetricsResult | null;
  verification?: ResearchVerification | null;
  verificationError?: string | null;
}): ReportSection[] {
  const selectedBasis = normalizeBasisState(numQubits, initialBasisState);
  const derivation = buildDerivation(numQubits, gates, steps, selectedBasis);
  const dim = 1 << numQubits;
  const density = resultsV2?.final_density ? densityFromData(resultsV2.final_density) : densityFromState(derivation.finalState);
  const reduced = numQubits >= 2 ? reducedDensityFirstQubit(density, numQubits) : density;
  const purity = trace(matMul(density, density)).re;
  const reducedPurity = reduced.length === 2 ? trace(matMul(reduced, reduced)).re : purity;
  const bloch = reduced.length === 2 ? blochVector(reduced) : null;
  const support = amplitudeRows(derivation.finalState).filter((row) => row.probability > 1e-8);
  const quietBasisCount = Math.max(0, dim - support.length);
  const motif = classifyCircuit(derivation.finalState, gates, reducedPurity);
  const ctx: PhysicsContext = {
    numQubits,
    dim,
    gates,
    initialBasisState: selectedBasis,
    derivation,
    density,
    reduced,
    purity,
    reducedPurity,
    bloch,
    metrics,
    motif,
    support,
    quietBasisCount,
    verification,
    verificationError,
  };

  const chapters = [
    chapter("Hilbert Space", hilbertSubtitle(ctx), hilbertLatex(ctx), hilbertMarkdown(ctx), () => <HilbertChapter ctx={ctx} />, true),
    chapter("Computational Basis", basisSubtitle(ctx), basisLatex(ctx), basisMarkdown(ctx), () => <ComputationalBasisChapter ctx={ctx} />),
    chapter("Initial State", initialSubtitle(ctx), initialLatex(ctx), initialMarkdown(ctx), () => <InitialStateChapter ctx={ctx} />),
    chapter("Gate Stacking", stackingSubtitle(ctx), stackingLatex(ctx), stackingMarkdown(ctx), () => <GateStackingChapter ctx={ctx} />),
    chapter("Superposition", superpositionSubtitle(ctx), superpositionLatex(ctx), superpositionMarkdown(ctx), () => <SuperpositionChapter ctx={ctx} />),
    chapter("Tensor Products", tensorSubtitle(ctx), tensorLatex(ctx), tensorMarkdown(ctx), () => <TensorChapter ctx={ctx} />),
    chapter("Entanglement", entanglementSubtitle(ctx), entanglementLatex(ctx), entanglementMarkdown(ctx), () => <EntanglementChapter ctx={ctx} />),
    chapter("Measurement", measurementSubtitle(ctx), measurementLatex(ctx), measurementMarkdown(ctx), () => <MeasurementChapter ctx={ctx} />),
    chapter("Density Operators", densitySubtitle(ctx), densityLatex(ctx), densityMarkdown(ctx), () => <DensityChapter ctx={ctx} />),
    chapter("Partial Trace", partialTraceSubtitle(ctx), partialTraceLatex(ctx), partialTraceMarkdown(ctx), () => <PartialTraceChapter ctx={ctx} />),
    chapter("Information-Theoretic Interpretation", informationSubtitle(ctx), informationLatex(ctx), informationMarkdown(ctx), () => <InformationChapter ctx={ctx} />),
    chapter("Research Notes", researchSubtitle(ctx), researchLatex(ctx), researchMarkdown(ctx), () => <ResearchChapter ctx={ctx} />),
  ];
  return chapters.map((section, index) => ({ ...section, number: String(index + 1) }));
}

function GateStackingChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const stacked = ctx.gates.filter((gate) => (gate.stackCount ?? 1) > 1);
  return (
    <ArticleChapter>
      <Lead>
        Gate stacking means QuantumLab treats repeated gates at one circuit location as one effective unitary power. {stacked.length ? `This circuit has ${stacked.length} stacked placement${stacked.length === 1 ? "" : "s"}.` : "This circuit has no stacked placements yet."}
      </Lead>
      {stacked.length ? (
        <>
          <ul>
            {stacked.map((gate) => (
              <li key={gate.id}>
                {gate.gateType}^{gate.stackCount ?? 1} on q[{gate.qubitTargets.join(", ")}]: {stackPhysicsInterpretation(
  gate.gateType,
  gate.stackCount ?? 1
)}
              </li>
            ))}
          </ul>
          <Equation math={"U_{eff}=U^n=\\underbrace{U\\cdot U\\cdots U}_{n\\text{ times}}"} />
        </>
      ) : (
        <p>Drag the same gate onto the same qubit or control-target pair to compose repeated evolution in place.</p>
      )}
      <Conclusion>
        A stack is physical composition, not visual compression: the second operation can undo, reinforce, or continue the first depending on the unitary.
      </Conclusion>
    </ArticleChapter>
  );
}

function chapter(
  title: string,
  subtitle: string,
  latex: string[],
  markdown: string,
  render: () => JSX.Element,
  defaultOpen = false,
): ReportSection {
  return {
    id: `physics-${slug(title)}`,
    number: "",
    title,
    subtitle,
    latex,
    markdown,
    searchText: [title, subtitle, markdown, ...latex].join(" "),
    defaultOpen,
    render,
  };
}

function HilbertChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <ArticleChapter>
      <Lead>
        Your circuit is a physical story about a vector in a Hilbert space, not merely a list of gates. With {ctx.numQubits} qubit{ctx.numQubits === 1 ? "" : "s"}, the relevant space has {ctx.dim} mutually distinguishable computational directions. QuantumLab tracks one complex amplitude for each direction, and the collection of those amplitudes is the wavefunction that every later chapter interprets.
      </Lead>
      <p>
        The important physics is that a qubit register does not choose one classical string while the circuit evolves. Instead, the register carries a coherent amplitude distribution across the basis strings. In this run, the final state has observable support on {ctx.support.length} of the {ctx.dim} basis directions. The remaining {ctx.quietBasisCount} directions have probability below numerical tolerance, which means this particular circuit did not leave measurable population there after all interference effects were accounted for.
      </p>
      <Equation math={`\\mathcal{H}=(\\mathbb{C}^{2})^{\\otimes ${ctx.numQubits}},\\qquad \\dim\\mathcal{H}=2^{${ctx.numQubits}}=${ctx.dim}`} />
      <BasisDiagram ctx={ctx} />
      <p>
        Complex numbers appear because quantum amplitudes carry both magnitude and phase. Magnitude determines how much probability can be revealed by measurement; phase determines how paths add or cancel before measurement. This is why two circuits can have the same intermediate probabilities and different final behavior: the hidden phase bookkeeping changes later interference.
      </p>
      <Conclusion>
        The Hilbert-space chapter for this circuit is therefore: {ctx.numQubits} qubit{ctx.numQubits === 1 ? "" : "s"}, {ctx.dim} possible basis directions, and a final wavefunction whose occupied directions are {supportSentence(ctx)}.
      </Conclusion>
    </ArticleChapter>
  );
}

function ComputationalBasisChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const labels = ctx.derivation.basisLabels.slice(0, Math.min(ctx.dim, 8));
  return (
    <ArticleChapter>
      <Lead>
        The computational basis is the set of mutually distinguishable outcomes that would appear if every qubit were measured in the standard readout basis. For this {ctx.numQubits}-qubit circuit, QuantumLab labels those directions as bit strings such as {labels.join(", ")}{ctx.dim > labels.length ? ", ..." : ""}.
      </Lead>
      <p>
        These labels are not extra mathematics placed on top of the physics. They are the possible classical records a measurement device can return. The Hilbert-space vector is expressed in this basis so the simulator can say how much amplitude sits on each possible detector outcome. Orthogonality means that two different labels represent experimentally distinguishable alternatives.
      </p>
      <BasisDiagram ctx={ctx} />
      <Equation math={"\\langle x|y\\rangle=\\delta_{xy}"} />
      <p>
        The Kronecker delta in the equation says that a basis state overlaps perfectly with itself and not at all with a different basis state. That is the physical reason probabilities can be assigned cleanly to the displayed basis labels after the wavefunction has finished evolving.
      </p>
      <Proof title="Two sample inner products">
        <Equation math={"\\langle 0\\cdots0|0\\cdots0\\rangle=1"} />
        <Equation math={"\\langle 0\\cdots0|1\\cdots1\\rangle=0"} />
      </Proof>
      <Conclusion>
        The computational basis gives this report a common language for amplitudes, measurement, density matrices, and entanglement diagnostics.
      </Conclusion>
    </ArticleChapter>
  );
}

function InitialStateChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const ket = `|${ctx.initialBasisState}\\rangle`;
  return (
    <ArticleChapter>
      <Lead>
        QuantumLab prepares this circuit in {displayKet(ctx.initialBasisState)}. Physically, that means the register begins in a pure computational basis state before any gate has been applied.
      </Lead>
      <p>
        This starting condition is intentionally sharp. No superposition exists initially: one selected basis amplitude is one, all other basis amplitudes are zero, and measurement in the computational basis would be deterministic before evolution begins.
      </p>
      <Equation math={`|\\psi_0\\rangle=${ket}`} />
      <Equation math={"\\langle\\psi_0|\\psi_0\\rangle=1"} />
      <p>
        If the final report shows population outside {displayKet(ctx.initialBasisState)}, that population was created by the user's gates. If it shows phase structure or entanglement, those features were likewise generated by the circuit dynamics and not assumed at initialization.
      </p>
      <Conclusion>
        The system is initialized in a pure computational basis state: one occupied basis direction, unit total probability, no superposition, and deterministic measurement before evolution begins.
      </Conclusion>
    </ArticleChapter>
  );
}

function SuperpositionChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const hasH = ctx.gates.some((gate) => gate.gateType === "H");
  const hasRot = ctx.gates.some((gate) => ["RX", "RY", "RZ"].includes(gate.gateType));
  return (
    <ArticleChapter>
      <Lead>
        Superposition in this circuit means the final wavefunction cannot be described as a single occupied computational basis string. QuantumLab finds {ctx.support.length} populated basis component{ctx.support.length === 1 ? "" : "s"} above tolerance, so the physical reading is {ctx.support.length === 1 ? "a definite basis outcome for the final state" : "a coherent spread of alternatives that remain simultaneously present until measurement"}.
      </Lead>
      <p>
        The gates that most directly create or reshape superposition here are {gateList(ctx.gates.filter((gate) => gate.gateType === "H" || ["RX", "RY"].includes(gate.gateType)))}. A Hadamard pulse changes a qubit from a sharp computational-basis description into an equal pair of phase-sensitive alternatives. A rotation gate changes the state continuously, as if a spinor were precessing under a controlled Hamiltonian. These are different physical mechanisms, but both have the same consequence: amplitudes become shared among basis labels instead of living in a single label.
      </p>
      <AmplitudeWave ctx={ctx} />
      <Equation math={stateExpansionLatex(ctx.derivation.finalState, 14)} />
      <p>
        The distribution shown above is not a set of classical odds assigned after the fact. It is the result of coherent path addition. If a basis component has amplitude {ctx.support[0] ? complexToText(ctx.support[0].amplitude) : "0"}, its probability is the squared magnitude of that complex number, but its phase can still influence future gates before measurement. That phase is why superposition is physically richer than uncertainty.
      </p>
      <Proof title="Why this is not just classical randomness">
        <p>
          A classical mixture would say the system secretly occupies one basis state and we lack knowledge. A coherent superposition instead keeps relative phase between occupied components. The simulator exposes this through complex amplitudes:
        </p>
        <Equation math={"|\\psi\\rangle=\\sum_x a_x|x\\rangle,\\qquad P(x)=|a_x|^2"} />
        <p>
          {hasH || hasRot ? "Because this circuit contains superposition-producing gates, future gates can recombine those amplitudes and change probabilities through interference." : "This circuit does not use a superposition-producing gate, so its final state remains concentrated unless conditional gates move population between basis labels."}
        </p>
      </Proof>
      <Conclusion>
        For this circuit, superposition is best read from its support: {supportSentence(ctx)}.
      </Conclusion>
    </ArticleChapter>
  );
}

function TensorChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <ArticleChapter>
      <Lead>
        Tensor products enter because a multi-qubit device is one joint physical system. A single qubit has a two-dimensional state space, but {ctx.numQubits} qubit{ctx.numQubits === 1 ? "" : "s"} require the combined space {ctx.numQubits === 1 ? "of one qubit" : "formed by multiplying subsystem spaces"}. This multiplication of spaces is the origin of the exponential dimension {ctx.dim}.
      </Lead>
      <TensorDiagram ctx={ctx} />
      <p>
        The key conceptual point is not the matrix block construction. It is locality. A pulse applied to one wire is local in the lab, yet the wavefunction it acts on belongs to the full register. The rest of the register is not erased or ignored; it is carried along as identity evolution. When a control gate is present, locality becomes conditional: one branch of the wavefunction receives one target evolution and another branch receives a different one.
      </p>
      <Equation math={`\\mathcal{H}_{total}=\\mathcal{H}_{q_0}\\otimes\\cdots\\otimes\\mathcal{H}_{q_${ctx.numQubits - 1}}`} />
      <p>
        In this circuit, {ctx.gates.length ? `${ctx.gates.length} gate${ctx.gates.length === 1 ? "" : "s"} act on selected wires while the full register remains one shared object.` : "no gates have yet acted, so the tensor-product structure is present but dynamically unused."} The tensor product is therefore the bridge between what the circuit diagram suggests locally and what the simulator evolves globally.
      </p>
      <Proof title="Dimension check">
        <Equation math={`\\underbrace{2\\times2\\times\\cdots\\times2}_{${ctx.numQubits}\\text{ factors}}=2^{${ctx.numQubits}}=${ctx.dim}`} />
        <p>
          This is why a single-qubit physical operation must be interpreted inside a {ctx.dim}-dimensional state space for this circuit.
        </p>
      </Proof>
      <Conclusion>
        Tensor products explain why each local gate can affect global amplitudes without becoming a different kind of operation: locality is preserved by identities on untouched subsystems, while the state remains joint.
      </Conclusion>
    </ArticleChapter>
  );
}

function EntanglementChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const entangled = ctx.numQubits >= 2 && ctx.reducedPurity < 1 - 1e-6;
  return (
    <ArticleChapter>
      <Lead>
        Entanglement asks whether the final wavefunction can be split into independent subsystem states. For this circuit, the first-qubit reduced purity is {fmt(ctx.reducedPurity)}. {entangled ? "That value is below one, so the first qubit does not possess its own pure state after the rest of the register is ignored." : "That value is one within tolerance, so this bipartition is separable in the final state."}
      </Lead>
      <EntanglementDiagram ctx={ctx} />
      <p>
        The physical distinction is sharp. If the register is separable, each subsystem can be assigned a state of its own, and correlations are explainable without making the wavefunction indivisible. If it is entangled, the state belongs to the pair or larger register first; subsystem descriptions are incomplete shadows obtained by discarding information.
      </p>
      <Equation math={`\\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`} />
      <p>
        {entangled
          ? `The populated basis components ${supportSentence(ctx)} cannot be interpreted as independent local facts across the first-qubit cut. Their amplitudes encode correlations that survive even when no classical outcome has been selected.`
          : `The populated basis components ${supportSentence(ctx)} do not force mixedness in the first-qubit reduced state. This does not mean the circuit is uninteresting; it means its final correlations across this cut can be factored.`}
      </p>
      <Proof title="Reduced purity separability test">
        <p>
          For a global pure state, a subsystem is pure exactly when it is not entangled with the complementary subsystem. QuantumLab computes the reduced state by summing over the unobserved basis labels.
        </p>
        <Equation math={"(\\rho_A)_{ij}=\\sum_b \\rho_{ib,jb}"} />
        <Equation math={reducedMatrixLatex(ctx.reduced)} />
        <Equation math={`\\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`} />
      </Proof>
      <Conclusion>
        This circuit is classified as {motifLabel(ctx.motif)}. The entanglement conclusion is derived from the simulated final state, not from the gate names alone.
      </Conclusion>
    </ArticleChapter>
  );
}

function MeasurementChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <ArticleChapter>
      <Lead>
        Measurement turns the wavefunction into a classical record. QuantumLab reports the Born-rule distribution for this circuit but keeps the explanatory wavefunction intact, so the report can still analyze phase, density operators, and subsystem structure after the probabilities are computed.
      </Lead>
      <MeasurementBars ctx={ctx} />
      <p>
        The measurement probabilities are obtained from the final amplitudes. If a basis state has amplitude <InlineMath math={"a_x"} />, its chance of appearing in an ideal computational-basis measurement is <InlineMath math={"|a_x|^2"} />. For this circuit, the visible outcomes are {supportSentence(ctx)}. Basis states not listed are below tolerance and therefore would not be expected in an ideal noiseless sample at the displayed precision.
      </p>
      <Equation math={"P(x)=|\\langle x|\\psi\\rangle|^2=|a_x|^2"} />
      <p>
        Collapse is a different physical step from probability calculation. Probability calculation is deterministic and reversible as analysis. Collapse is the stochastic update that would replace the state by one observed basis ket after an actual measurement. This distinction matters in educational simulation because it lets the same final state be inspected from several angles before sampling destroys phase information.
      </p>
      <Proof title="Born rule applied to the displayed support">
        {ctx.support.slice(0, 12).map((row) => (
          <Equation key={row.basis} math={`P(${basisInner(row.basis)})=|${complexToLatex(row.amplitude)}|^2=${fmt(row.probability)}`} />
        ))}
      </Proof>
      <Conclusion>
        The measurement chapter says what the circuit would reveal, not that the simulator has already forced the state to choose an outcome.
      </Conclusion>
    </ArticleChapter>
  );
}

function DensityChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <ArticleChapter>
      <Lead>
        The density operator is the report's way of turning a state vector into an object that can discuss coherence, ignorance, noise, and subsystems in one language. For this run the global purity is {fmt(ctx.purity)}, so the global state is {ctx.purity > 1 - 1e-6 ? "pure within numerical tolerance" : "mixed, likely because density/noise mode supplied a non-projector state"}.
      </Lead>
      <DensityDiagram ctx={ctx} />
      <p>
        The diagonal entries of <InlineMath math={"\\rho"} /> are classical measurement probabilities in the computational basis. The off-diagonal entries are coherences: they remember phase relationships between different basis alternatives. A probability chart alone cannot show those coherences, but the density operator can. This is why density matrices become unavoidable when discussing decoherence and partial observation.
      </p>
      <Equation math={"\\rho=|\\psi\\rangle\\langle\\psi|,\\qquad \\rho_{ij}=a_i a_j^*"} />
      <p>
        In this circuit, coherence is concentrated among the populated support states. If two populated basis directions have a nonzero off-diagonal element, the state still carries phase information connecting them. If environmental noise or subsystem tracing removes that term, the report would shift from a coherent quantum explanation toward a classical-probabilistic one.
      </p>
      <Proof title="Purity diagnostic">
        <Equation math={`\\mathrm{Tr}(\\rho^2)=${fmt(ctx.purity)}`} />
        <p>
          A pure global state has purity one. A mixed state has smaller purity because it cannot be represented as a single normalized ket.
        </p>
      </Proof>
      <Conclusion>
        The density operator confirms whether the final state should be read as one coherent wavefunction or as a mixed statistical state.
      </Conclusion>
    </ArticleChapter>
  );
}

function PartialTraceChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  if (ctx.numQubits < 2) {
    return (
      <ArticleChapter>
        <Lead>
          A partial trace requires at least two subsystems. This circuit has one qubit, so there is no complementary register to ignore.
        </Lead>
        <Conclusion>The single-qubit density operator already is the accessible local state.</Conclusion>
      </ArticleChapter>
    );
  }

  return (
    <ArticleChapter>
      <Lead>
        The partial trace answers a deliberately limited question: what state can be assigned to q[0] if every other qubit is ignored? The answer is not guessed from the circuit diagram. It is computed by summing over the unobserved basis labels of the final density operator.
      </Lead>
      <PartialTraceDiagram />
      <p>
        Ignoring a subsystem is not the same as deleting it. The discarded subsystem may still carry information about phases and correlations. The partial trace keeps exactly the statistics available to the subsystem being examined and removes all distinctions that require access to the rest of the register.
      </p>
      <Equation math={"(\\rho_A)_{ij}=\\sum_b \\rho_{ib,jb}"} />
      <Equation math={reducedMatrixLatex(ctx.reduced)} />
      <p>
        For this circuit, q[0] has reduced Bloch-vector length {ctx.bloch ? fmt(ctx.bloch.length) : "not available"}. A full-length vector means the local state is pure; a shorter vector means q[0] is locally mixed because information has moved into correlations with the other qubits or into noise.
      </p>
      <Proof title="Local purity">
        <Equation math={`\\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`} />
        {ctx.bloch && <Equation math={`\\vec r=(${fmt(ctx.bloch.x)},${fmt(ctx.bloch.y)},${fmt(ctx.bloch.z)}),\\qquad |\\vec r|=${fmt(ctx.bloch.length)}`} />}
      </Proof>
      <Conclusion>
        The partial trace turns global wavefunction structure into the local physics of one wire, making entanglement and decoherence visible as reduced purity loss.
      </Conclusion>
    </ArticleChapter>
  );
}

function InformationChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <ArticleChapter>
      <Lead>
        Quantum information theory translates the circuit's physical state into resource language: purity, entropy, coherence, distinguishability, and correlation. For this run, the most meaningful scalar diagnostics are global purity {fmt(ctx.purity)} and first-qubit reduced purity {fmt(ctx.reducedPurity)}.
      </Lead>
      <InfoGrid ctx={ctx} />
      <p>
        A pure global state with a mixed subsystem is the hallmark of entanglement. Nothing noisy has to happen for a local observer to see a mixed state; local mixedness can arise purely because information is stored nonlocally. This is one of the deepest differences between quantum and classical descriptions of composite systems.
      </p>
      <Equation math={"S(\\rho)=-\\mathrm{Tr}(\\rho\\log_2\\rho)"} />
      <p>
        {ctx.metrics?.entropy
          ? `The simulator reports entropy ${fmt(ctx.metrics.entropy.entropy)} for the configured bipartition.`
          : "Entropy is not currently supplied by the simulator for this exact run, so the report emphasizes purity and reduced purity instead of inventing an entropy value."} {ctx.metrics?.fidelity ? `The reported fidelity is ${fmt(ctx.metrics.fidelity.fidelity)}.` : "No fidelity target is selected, so fidelity is omitted from the physical interpretation."}
      </p>
      <Proof title="Meaning of the displayed metrics">
        {informationLatex(ctx).map((math) => <Equation key={math} math={math} />)}
      </Proof>
      <Conclusion>
        In information language, this circuit demonstrates {motifLabel(ctx.motif)} with support {supportSentence(ctx)} and reduced purity {fmt(ctx.reducedPurity)}.
      </Conclusion>
    </ArticleChapter>
  );
}

function ResearchChapter({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const verified = ctx.verification?.status === "VERIFIED";
  return (
    <ArticleChapter>
      <Lead>
        This generated report classifies the circuit as {motifLabel(ctx.motif)}. The classification comes from the actual final amplitudes, the gate sequence, and the reduced-state diagnostics; {verified ? "the mathematical dataset is Wolfram verified." : "Wolfram verification is not available for at least part of this run, so this chapter treats native diagnostics as simulated rather than independently verified."}
      </Lead>
      <VerificationPhysicsNote ctx={ctx} />
      <ResearchSummary ctx={ctx} />
      <p>
        {researchInterpretation(ctx)}
      </p>
      <p>
        The most important experimental signature is the final measurement support: {supportSentence(ctx)}. If this is a Bell-like circuit, that support expresses two correlated alternatives with no independent pure state for either qubit. If this is an interference circuit, the support expresses path recombination. If this is phase control, the report's density/coherence chapters are more important than the probability chart because phase can be present even when populations look unchanged.
      </p>
      <Proof title="State summary">
        <Equation math={stateExpansionLatex(ctx.derivation.finalState, 16)} />
        <Equation math={`\\mathrm{Tr}(\\rho^2)=${fmt(ctx.purity)},\\qquad \\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`} />
      </Proof>
      <Conclusion>
        The circuit is not merely a sequence of operations; it is a small physical experiment about {motifLabel(ctx.motif)}.
      </Conclusion>
    </ArticleChapter>
  );
}

function VerificationPhysicsNote({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const status = ctx.verification?.status ?? "UNAVAILABLE";
  const message = ctx.verification?.message ?? ctx.verificationError ?? "Wolfram verification is unavailable.";
  return (
    <aside className="physics-conclusion">
      <strong>Research verification.</strong> {status}: {message}
      {ctx.verification?.warnings?.length ? ` Warnings: ${ctx.verification.warnings.map((w) => w.message).join(" ")}` : ""}
    </aside>
  );
}

function ArticleChapter({ children }: { children: ReactNode }): JSX.Element {
  return <article className="physics-article-chapter">{children}</article>;
}

function Lead({ children }: { children: ReactNode }): JSX.Element {
  return <p className="physics-lead">{children}</p>;
}

function Conclusion({ children }: { children: ReactNode }): JSX.Element {
  return <aside className="physics-conclusion"><strong>Conclusion.</strong> {children}</aside>;
}

function Proof({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <details className="physics-proof">
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  );
}

function Equation({ math }: { math: string }): JSX.Element {
  return (
    <div className="physics-equation">
      <BlockMath math={math} />
      <button type="button" onClick={() => void navigator.clipboard?.writeText(math)}>Copy</button>
    </div>
  );
}

function BasisDiagram({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const labels = ctx.derivation.basisLabels.slice(0, 8);
  return (
    <figure className="physics-figure">
      <div className="physics-basis-strip">
        {labels.map((label) => {
          const row = amplitudeRows(ctx.derivation.finalState).find((candidate) => candidate.basis === label);
          return (
            <div key={label} className="physics-basis-cell">
              <span>{label}</span>
              <small>P={fmt(row?.probability ?? 0)}</small>
            </div>
          );
        })}
        {ctx.dim > labels.length && <div className="physics-basis-cell"><span>...</span><small>{ctx.dim - labels.length} more</small></div>}
      </div>
      <figcaption>Computational basis directions, annotated with this circuit's final probabilities.</figcaption>
    </figure>
  );
}

function AmplitudeWave({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <figure className="physics-figure">
      <div className="physics-wave">
        {ctx.support.slice(0, 12).map((row) => (
          <div key={row.basis} className="physics-wave-row">
            <span>{row.basis}</span>
            <div><i style={{ width: `${Math.max(2, row.probability * 100)}%` }} /></div>
            <small>{complexToText(row.amplitude)}</small>
          </div>
        ))}
      </div>
      <figcaption>Occupied final amplitudes. Bar length shows probability; the label preserves complex phase.</figcaption>
    </figure>
  );
}

function TensorDiagram({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <figure className="physics-figure">
      <div className="physics-tensor-chain">
        {Array.from({ length: ctx.numQubits }, (_, i) => (
          <div key={i} className="physics-tensor-node">q[{i}]<small>C2</small></div>
        ))}
        <div className="physics-tensor-result">{ctx.dim}D joint space</div>
      </div>
      <figcaption>Subsystem spaces combine into one joint Hilbert space through tensor products.</figcaption>
    </figure>
  );
}

function EntanglementDiagram({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const entangled = ctx.numQubits >= 2 && ctx.reducedPurity < 1 - 1e-6;
  return (
    <figure className="physics-figure">
      <div className={`physics-entanglement-map ${entangled ? "is-entangled" : ""}`}>
        <span>q[0]</span>
        <i>{entangled ? "correlated wavefunction" : "factorable cut"}</i>
        <span>rest</span>
      </div>
      <figcaption>{entangled ? "Reduced mixedness indicates entanglement across this cut." : "The tested cut remains separable within tolerance."}</figcaption>
    </figure>
  );
}

function MeasurementBars({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <figure className="physics-figure">
      <div className="physics-measurement-bars">
        {ctx.support.slice(0, 10).map((row) => (
          <label key={row.basis}>
            <span>{row.basis}</span>
            <meter min={0} max={1} value={row.probability} />
            <small>{fmt(row.probability)}</small>
          </label>
        ))}
      </div>
      <figcaption>Born-rule probabilities for the currently simulated final state.</figcaption>
    </figure>
  );
}

function DensityDiagram({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const visible = ctx.density.slice(0, 8).map((row) => row.slice(0, 8));
  const max = Math.max(1e-8, ...visible.flat().map((z) => Math.sqrt(mag2(z))));
  return (
    <figure className="physics-figure">
      <div className="physics-density-grid" style={{ gridTemplateColumns: `repeat(${visible.length}, minmax(0, 1fr))` }}>
        {visible.flatMap((row, r) => row.map((z, c) => (
          <span
            key={`${r}-${c}`}
            title={`rho[${r},${c}] = ${complexToText(z)}`}
            style={{ opacity: 0.18 + 0.82 * (Math.sqrt(mag2(z)) / max) }}
          />
        )))}
      </div>
      <figcaption>Density-operator magnitude sketch. Bright off-diagonal cells indicate coherence.</figcaption>
    </figure>
  );
}

function PartialTraceDiagram(): JSX.Element {
  return (
    <figure className="physics-figure">
      <div className="physics-partial-trace">
        <span>global rho</span>
        <i>sum over ignored basis labels</i>
        <span>local rho_A</span>
      </div>
      <figcaption>Partial trace converts global information into the state visible to q[0].</figcaption>
    </figure>
  );
}

function InfoGrid({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  const items = [
    ["Global purity", fmt(ctx.purity)],
    ["Reduced purity", fmt(ctx.reducedPurity)],
    ["Support size", `${ctx.support.length}/${ctx.dim}`],
    ["Motif", motifLabel(ctx.motif)],
  ];
  if (ctx.metrics?.entropy) items.push(["Entropy", fmt(ctx.metrics.entropy.entropy)]);
  if (ctx.metrics?.fidelity) items.push(["Fidelity", fmt(ctx.metrics.fidelity.fidelity)]);
  return (
    <div className="physics-info-grid">
      {items.map(([label, value]) => (
        <div key={label}><span>{label}</span><strong>{value}</strong></div>
      ))}
    </div>
  );
}

function ResearchSummary({ ctx }: { ctx: PhysicsContext }): JSX.Element {
  return (
    <figure className="physics-figure">
      <div className="physics-research-summary">
        <strong>{motifLabel(ctx.motif)}</strong>
        <span>{ctx.gates.length} gate{ctx.gates.length === 1 ? "" : "s"}</span>
        <span>{ctx.numQubits} qubit{ctx.numQubits === 1 ? "" : "s"}</span>
        <span>{ctx.support.length} populated basis state{ctx.support.length === 1 ? "" : "s"}</span>
      </div>
      <figcaption>Automatically inferred from the simulated state and circuit structure.</figcaption>
    </figure>
  );
}

function hilbertSubtitle(ctx: PhysicsContext): string {
  return `${ctx.numQubits} qubit${ctx.numQubits === 1 ? "" : "s"} in a ${ctx.dim}-dimensional complex state space`;
}

function basisSubtitle(ctx: PhysicsContext): string {
  return `${ctx.dim} orthonormal readout direction${ctx.dim === 1 ? "" : "s"}`;
}

function initialSubtitle(ctx: PhysicsContext): string {
  return `prepared as |${ctx.initialBasisState}>`;
}

function stackingSubtitle(ctx: PhysicsContext): string {
  const count = ctx.gates.filter((gate) => (gate.stackCount ?? 1) > 1).length;
  return count ? `${count} stacked operator${count === 1 ? "" : "s"} composed as U^n` : "no stacked operators";
}

function superpositionSubtitle(ctx: PhysicsContext): string {
  return `${ctx.support.length} populated basis component${ctx.support.length === 1 ? "" : "s"} after simulation`;
}

function tensorSubtitle(ctx: PhysicsContext): string {
  return `local circuit wires combine into one ${ctx.dim}-dimensional register`;
}

function entanglementSubtitle(ctx: PhysicsContext): string {
  return ctx.numQubits < 2 ? "not defined for a one-qubit circuit" : `first-qubit reduced purity ${fmt(ctx.reducedPurity)}`;
}

function measurementSubtitle(ctx: PhysicsContext): string {
  return `${ctx.support.length} outcomes carry nonzero probability`;
}

function densitySubtitle(ctx: PhysicsContext): string {
  return `global purity ${fmt(ctx.purity)}`;
}

function partialTraceSubtitle(ctx: PhysicsContext): string {
  return ctx.numQubits < 2 ? "no subsystem to trace out" : `q[0] local state extracted from ${ctx.numQubits}-qubit rho`;
}

function informationSubtitle(ctx: PhysicsContext): string {
  return `resource view: ${motifLabel(ctx.motif)}`;
}

function researchSubtitle(ctx: PhysicsContext): string {
  return motifLabel(ctx.motif);
}

function hilbertLatex(ctx: PhysicsContext): string[] {
  return [`\\dim\\mathcal{H}=2^{${ctx.numQubits}}=${ctx.dim}`, stateExpansionLatex(ctx.derivation.finalState, 12)];
}

function basisLatex(ctx: PhysicsContext): string[] {
  const labels = ctx.derivation.basisLabels
    .slice(0, Math.min(ctx.dim, 8))
    .map((label) => label.replace(">", "\\rangle"))
    .join(", ");
  return [`\\mathcal{B}=\\{${labels}${ctx.dim > 8 ? ",\\ldots" : ""}\\}`, "\\langle x|y\\rangle=\\delta_{xy}"];
}

function initialLatex(ctx: PhysicsContext): string[] {
  return [`|\\psi_0\\rangle=|${ctx.initialBasisState}\\rangle`, "\\langle\\psi_0|\\psi_0\\rangle=1"];
}

function stackingLatex(ctx: PhysicsContext): string[] {
  const stacked = ctx.gates.filter((gate) => (gate.stackCount ?? 1) > 1);
  return stacked.length
    ? ["U_{eff}=U^n", ...stacked.map((gate) => `${gate.gateType}_{eff}=${gate.gateType}^{${gate.stackCount ?? 1}}`)]
    : ["U_{eff}=U"];
}

function superpositionLatex(ctx: PhysicsContext): string[] {
  return [`|\\psi\\rangle=\\sum_x a_x|x\\rangle`, stateExpansionLatex(ctx.derivation.finalState, 12)];
}

function tensorLatex(ctx: PhysicsContext): string[] {
  return [`\\mathcal{H}_{total}=\\bigotimes_{k=0}^{${ctx.numQubits - 1}}\\mathcal{H}_{q_k}`, `\\dim\\mathcal{H}_{total}=${ctx.dim}`];
}

function entanglementLatex(ctx: PhysicsContext): string[] {
  return ctx.numQubits < 2
    ? ["\\text{No bipartition exists for one qubit.}"]
    : [`\\rho_A=\\mathrm{Tr}_B(\\rho)`, `\\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`, reducedMatrixLatex(ctx.reduced)];
}

function measurementLatex(ctx: PhysicsContext): string[] {
  return ["P(x)=|a_x|^2", ...ctx.support.slice(0, 10).map((row) => `P(${basisInner(row.basis)})=${fmt(row.probability)}`)];
}

function densityLatex(ctx: PhysicsContext): string[] {
  return ["\\rho=|\\psi\\rangle\\langle\\psi|", `\\mathrm{Tr}(\\rho^2)=${fmt(ctx.purity)}`];
}

function partialTraceLatex(ctx: PhysicsContext): string[] {
  return ctx.numQubits < 2 ? ["\\rho_A=\\rho"] : ["(\\rho_A)_{ij}=\\sum_b \\rho_{ib,jb}", reducedMatrixLatex(ctx.reduced)];
}

function informationLatex(ctx: PhysicsContext): string[] {
  const equations = [`\\mathrm{Tr}(\\rho^2)=${fmt(ctx.purity)}`, `\\mathrm{Tr}(\\rho_A^2)=${fmt(ctx.reducedPurity)}`];
  if (ctx.metrics?.entropy) equations.push(`S(\\rho_A)=${fmt(ctx.metrics.entropy.entropy)}`);
  if (ctx.metrics?.fidelity) equations.push(`F=${fmt(ctx.metrics.fidelity.fidelity)}`);
  return equations;
}

function researchLatex(ctx: PhysicsContext): string[] {
  return [stateExpansionLatex(ctx.derivation.finalState, 16), `\\mathrm{support}= ${ctx.support.length}`];
}

function hilbertMarkdown(ctx: PhysicsContext): string {
  return `This circuit has ${ctx.numQubits} qubits and therefore evolves in dimension ${ctx.dim}. Final support: ${supportSentence(ctx)}.`;
}

function basisMarkdown(ctx: PhysicsContext): string {
  return `The computational basis contains ${ctx.dim} orthonormal readout directions. Different basis strings are distinguishable measurement alternatives.`;
}

function initialMarkdown(ctx: PhysicsContext): string {
  return `The circuit begins in |${ctx.initialBasisState}> as a pure computational basis state. No superposition exists initially, so computational-basis measurement is deterministic.`;
}

function stackingMarkdown(ctx: PhysicsContext): string {
  const stacked = ctx.gates.filter((gate) => (gate.stackCount ?? 1) > 1);
  if (!stacked.length) return "No gate stacks are present.";
  return stacked.map((gate) => `${gate.gateType}^${gate.stackCount ?? 1}: ${stackPhysicsInterpretation(
  gate.gateType,
  gate.stackCount ?? 1
)}`).join(" ");
}

function superpositionMarkdown(ctx: PhysicsContext): string {
  return `The final state has ${ctx.support.length} populated basis components. ${supportSentence(ctx)}.`;
}

function tensorMarkdown(ctx: PhysicsContext): string {
  return `Tensor products combine ${ctx.numQubits} qubit spaces into one ${ctx.dim}-dimensional register.`;
}

function entanglementMarkdown(ctx: PhysicsContext): string {
  return `Reduced purity across the first-qubit cut is ${fmt(ctx.reducedPurity)}. Motif: ${motifLabel(ctx.motif)}.`;
}

function measurementMarkdown(ctx: PhysicsContext): string {
  return `Born-rule probabilities are computed from amplitudes: ${supportSentence(ctx)}.`;
}

function densityMarkdown(ctx: PhysicsContext): string {
  return `Global purity is ${fmt(ctx.purity)}; diagonal density entries are probabilities and off-diagonal entries are coherences.`;
}

function partialTraceMarkdown(ctx: PhysicsContext): string {
  return ctx.numQubits < 2 ? "No partial trace is needed for one qubit." : `The first-qubit reduced state has purity ${fmt(ctx.reducedPurity)}.`;
}

function informationMarkdown(ctx: PhysicsContext): string {
  return `Information metrics for this run: ${informationLatex(ctx).join(", ")}.`;
}

function researchMarkdown(ctx: PhysicsContext): string {
  return `This circuit demonstrates ${motifLabel(ctx.motif)}. ${researchInterpretation(ctx)}`;
}

function classifyCircuit(snapshot: StateSnapshot, gates: GatePlacement[], reducedPurity: number): CircuitMotif {
  const active = snapshot.probabilities.filter((p) => p > 1e-6).length;
  const hasH = gates.some((g) => g.gateType === "H");
  const cnotCount = gates.filter((g) => g.gateType === "CNOT").length;
  const hasMeasurement = gates.some((g) => g.gateType === "M");
  if (snapshot.num_qubits === 2 && active === 2 && hasH && cnotCount >= 1 && reducedPurity < 1 - 1e-6) return "bell";
  if (snapshot.num_qubits >= 3 && active === 2 && hasH && cnotCount >= 2 && reducedPurity < 1 - 1e-6) return "ghz";
  if (snapshot.num_qubits >= 3 && hasMeasurement && cnotCount >= 2 && hasH) return "teleportation-primitive";
  if (reducedPurity < 1 - 1e-6) return "generic-entangling";
  if (hasH && active > 1) return "interference";
  if (gates.some((g) => ["Z", "RZ"].includes(g.gateType))) return "phase-control";
  return "basis-transport";
}

function motifLabel(motif: CircuitMotif): string {
  switch (motif) {
    case "bell":
      return "Bell-state entanglement";
    case "ghz":
      return "GHZ-style multipartite entanglement";
    case "teleportation-primitive":
      return "teleportation primitive";
    case "interference":
      return "coherent superposition and interference";
    case "phase-control":
      return "relative phase control";
    case "generic-entangling":
      return "conditional quantum correlation";
    case "basis-transport":
      return "deterministic basis-state transport";
  }
}

function supportSentence(ctx: PhysicsContext): string {
  if (ctx.support.length === 0) return "no basis component above tolerance";
  return ctx.support
    .slice(0, 8)
    .map((row) => `${row.basis} with P=${fmt(row.probability)}`)
    .join(", ") + (ctx.support.length > 8 ? ", and additional low-rank support" : "");
}

function gateList(gates: GatePlacement[]): string {
  if (gates.length === 0) return "none in this circuit";
  return gates.map((gate) => `${gate.gateType} on q[${gate.qubitTargets.join(", ")}]`).join(", ");
}

function researchInterpretation(ctx: PhysicsContext): string {
  if (ctx.motif === "bell") {
    return `The state has two dominant correlated outcomes, ${supportSentence(ctx)}, and the reduced state is mixed. This is the operational pattern of a Bell pair: local randomness with global order.`;
  }
  if (ctx.motif === "ghz") {
    return `The support is concentrated in two collective branches across ${ctx.numQubits} qubits. That is the characteristic signature of GHZ-style all-or-nothing correlation.`;
  }
  if (ctx.motif === "teleportation-primitive") {
    return "The gate pattern contains the conditional and measurement ingredients used in teleportation-like protocols. The report should be read as a primitive unless the full feed-forward correction circuit is also present.";
  }
  if (ctx.motif === "interference") {
    return "The circuit prepares more than one coherent path. The central physics is not randomness but the possibility that later gates can recombine phases into constructive or destructive interference.";
  }
  if (ctx.motif === "phase-control") {
    return "The circuit emphasizes phase evolution. Some probabilities may appear unchanged even though the state has physically changed in ways future gates can reveal.";
  }
  if (ctx.motif === "generic-entangling") {
    return "The reduced-state purity shows that conditional evolution has distributed information nonlocally across the register.";
  }
  return "The circuit moves population through computational basis states without producing a multi-outcome coherent final support above tolerance.";
}

function stateExpansionLatex(snapshot: StateSnapshot, maxTerms: number): string {
  const terms = snapshot.amplitudes
    .map((amp, i) => ({ amp: { re: amp.real, im: amp.imag }, label: snapshot.basis_labels[i] }))
    .filter(({ amp }) => mag2(amp) > EPS)
    .slice(0, maxTerms)
    .map(({ amp, label }) => `${complexToLatex(amp)}${label.replace(">", "\\rangle")}`);
  return `|\\psi_f\\rangle=${terms.length ? terms.join("+") : "0"}${terms.length === maxTerms ? "+\\cdots" : ""}`;
}

function reducedMatrixLatex(matrix: ComplexMatrix): string {
  return `\\rho_A=\\begin{pmatrix}${matrix.map((row) => row.map(complexToLatex).join(" & ")).join(" \\\\ ")}\\end{pmatrix}`;
}

function basisInner(label: string): string {
  return label.replace("|", "").replace(">", "");
}

function reducedDensityFirstQubit(matrix: ComplexMatrix, numQubits: number): ComplexMatrix {
  const restDim = 1 << (numQubits - 1);
  return [0, 1].map((i) =>
    [0, 1].map((j) =>
      Array.from({ length: restDim }, (_, b) => {
        const row = (i << (numQubits - 1)) + b;
        const col = (j << (numQubits - 1)) + b;
        return matrix[row]?.[col] ?? ZERO;
      }).reduce(add, ZERO),
    ),
  );
}

function blochVector(rho: ComplexMatrix): { x: number; y: number; z: number; length: number } {
  const x = 2 * (rho[0]?.[1]?.re ?? 0);
  const y = -2 * (rho[0]?.[1]?.im ?? 0);
  const z = (rho[0]?.[0]?.re ?? 0) - (rho[1]?.[1]?.re ?? 0);
  return { x, y, z, length: Math.sqrt(x * x + y * y + z * z) };
}

function matMul(a: ComplexMatrix, b: ComplexMatrix): ComplexMatrix {
  const rows = a.length;
  const cols = b[0]?.length ?? 0;
  const inner = b.length;
  return Array.from({ length: rows }, (_, r) =>
    Array.from({ length: cols }, (_, c) =>
      Array.from({ length: inner }, (_, k) => mul(a[r]?.[k] ?? ZERO, b[k]?.[c] ?? ZERO)).reduce(add, ZERO),
    ),
  );
}

function trace(matrix: ComplexMatrix): Complex {
  return matrix.map((row, i) => row[i] ?? ZERO).reduce(add, ZERO);
}

function add(a: Complex, b: Complex): Complex {
  return { re: clean(a.re + b.re), im: clean(a.im + b.im) };
}

function mul(a: Complex, b: Complex): Complex {
  return { re: clean(a.re * b.re - a.im * b.im), im: clean(a.re * b.im + a.im * b.re) };
}

function mag2(a: Complex): number {
  return a.re * a.re + a.im * a.im;
}

function clean(v: number): number {
  return Math.abs(v) < EPS ? 0 : v;
}

function fmt(v: number): string {
  if (Math.abs(v) < EPS) return "0";
  return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
