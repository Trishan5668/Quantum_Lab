import { useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchResearchVerification } from "../../apiV2";
import type { ReportMetadata, ReportSection } from "../Reports/ReportReader";
import { FullscreenReport, ReportReader } from "../Reports/ReportReader";
import { LatexBlock } from "./LatexBlock";
import { MatrixRenderer } from "./MatrixRenderer";
import {
  amplitudeRows,
  buildDerivation,
  complexToLatex,
  complexToText,
  densityFromData,
  densityFromState,
  matrixToLatex,
  vectorToLatex,
  type Complex,
  type ComplexMatrix,
} from "./mathDerivations";
import type { GatePlacement, MetricsResult, NoiseChannelType, ResearchVerification, SimulationMode, SimulationResultV2 } from "../../types";

const ZERO: Complex = { re: 0, im: 0 };
const ONE: Complex = { re: 1, im: 0 };
const I: Complex = { re: 0, im: 1 };
const EPS = 1e-10;

interface ResearchMathematicsReportProps {
  numQubits: number;
  initialBasisState: string;
  gates: GatePlacement[];
  resultSteps?: Parameters<typeof buildDerivation>[2];
  resultsV2: SimulationResultV2 | null;
  metrics: MetricsResult | null;
  simulationMode: SimulationMode;
  noiseEnabled: boolean;
  noiseModel: NoiseChannelType;
  noiseProbability: number;
  t1Us: number;
  t2Us: number;
  gateTimeNs: number;
  metadata?: ReportMetadata;
}

export function ResearchMathematicsReport(props: ResearchMathematicsReportProps): JSX.Element {
  const [verification, setVerification] = useState<ResearchVerification | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const derivation = useMemo(
    () => buildDerivation(props.numQubits, props.gates, props.resultSteps, props.initialBasisState),
    [props.numQubits, props.gates, props.resultSteps, props.initialBasisState],
  );
  useEffect(() => {
    let cancelled = false;
    setVerification(null);
    setVerificationError(null);
    console.log("RESEARCH RESULTS V2:", props.resultsV2);
    fetchResearchVerification(
      { numQubits: props.numQubits, gates: props.gates, initialBasisState: props.initialBasisState },
      {
        simulationMode: props.simulationMode,
        noiseEnabled: props.noiseEnabled,
        noiseModel: props.noiseModel,
        noiseProbability: props.noiseProbability,
        t1Us: props.t1Us,
        t2Us: props.t2Us,
        gateTimeNs: props.gateTimeNs,
      },
      props.resultsV2,
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
  }, [props.gateTimeNs, props.gates, props.initialBasisState, props.noiseEnabled, props.noiseModel, props.noiseProbability, props.numQubits, props.resultsV2, props.simulationMode, props.t1Us, props.t2Us]);
  const sections = useMemo(() => buildResearchMathSections({ ...props, derivation, verification, verificationError }), [props, derivation, verification, verificationError]);
  const subtitle = `${props.numQubits} qubits; Hilbert dimension ${1 << props.numQubits}; initial ket |${props.initialBasisState}>`;

  return (
    <div className="research-math-report">
      <VerificationBanner verification={verification} error={verificationError} />
      <div className="mb-2 flex justify-end">
        <FullscreenReport label="Research mathematics fullscreen" title="QuantumLab Research Mathematics" subtitle={subtitle}>
          <ReportReader title="QuantumLab Research Mathematics" subtitle={subtitle} sections={sections} metadata={props.metadata} />
        </FullscreenReport>
      </div>
      <ReportReader title="QuantumLab Research Mathematics" subtitle={subtitle} sections={sections} metadata={props.metadata} compact />
    </div>
  );
}

interface ResearchContext extends ResearchMathematicsReportProps {
  derivation: ReturnType<typeof buildDerivation>;
  finalDensity: ComplexMatrix;
  referenceDensity: ComplexMatrix;
  circuitUnitary: ComplexMatrix;
  verification: ResearchVerification | null;
  verificationError: string | null;
}

function buildResearchMathSections(input: ResearchMathematicsReportProps & {
  derivation: ReturnType<typeof buildDerivation>;
  verification: ResearchVerification | null;
  verificationError: string | null;
}): ReportSection[] {
  const finalDensity = input.resultsV2?.final_density
    ? densityFromData(input.resultsV2.final_density)
    : densityFromState(input.derivation.finalState);
  const referenceDensity = densityFromState(input.derivation.initialState);
  const circuitUnitary = input.derivation.steps.reduce(
    (acc, step) => matMul(step.gate.fullMatrix, acc),
    identity(1 << input.numQubits),
  );
  const ctx: ResearchContext = { ...input, finalDensity, referenceDensity, circuitUnitary };
  const sections = [
    section("Research Verification", "Wolfram authority status for this Research Mode report", verificationSection(ctx), true),
    section("Initial State", "Computational-basis preparation and state-vector invariants", initialSection(ctx), true),
    section("Operator Definitions", "Local operator data, spectra, and powers", operatorDefinitionsSection(ctx)),
    section("Tensor Embeddings", "Explicit Kronecker embeddings into the register Hilbert space", tensorEmbeddingSection(ctx)),
    section("State Evolution", "Row-expanded amplitude propagation for every placement", stateEvolutionSection(ctx)),
    section("Circuit Unitary", "Ordered product U_n ... U_2 U_1 and spectral diagnostics", circuitUnitarySection(ctx)),
    section("Density Operators", "Elementwise construction rho_ij = psi_i psi_j^*", densitySection(ctx)),
    section("Schmidt Decomposition", "Singular values for the q[0] | rest bipartition", schmidtSection(ctx)),
    section("Partial Trace", "Reduced state derivation by summing environmental indices", partialTraceSection(ctx)),
    section("Entropy", "Von Neumann entropy from reduced spectral data", entropySection(ctx)),
    section("Fidelity", "Uhlmann fidelity against the initial pure reference", fidelitySection(ctx)),
    section("Trace Distance", "Trace norm of rho - sigma for the same reference", traceDistanceSection(ctx)),
    section("Purity", "Tr(rho^2) with intermediate matrix product", puritySection(ctx)),
    section("Correlation Functions", "Pauli correlation tensor entries on the first two qubits", correlationSection(ctx)),
    section("Measurement Theory", "Projective computational-basis POVM and Born probabilities", measurementSection(ctx)),
    section("Mathematical Summary", "Compact invariant table for the generated circuit", summarySection(ctx)),
  ];
  return sections.map((item, index) => ({ ...item, number: String(index + 1) }));
}

function section(title: string, subtitle: string, content: SectionContent, defaultOpen = false): ReportSection {
  return {
    id: `research-math-${slug(title)}`,
    number: "",
    title,
    subtitle,
    latex: content.latex,
    markdown: content.markdown,
    searchText: [title, subtitle, content.markdown, ...content.latex].join(" "),
    defaultOpen,
    render: content.render,
  };
}

interface SectionContent {
  latex: string[];
  markdown: string;
  render: () => JSX.Element;
}

function initialSection(ctx: ResearchContext): SectionContent {
  const vector = ctx.derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag }));
  const support = amplitudeRows(ctx.derivation.initialState).filter((row) => row.probability > EPS);
  const latex = [
    `|\\psi_0\\rangle=|${ctx.initialBasisState}\\rangle`,
    `|\\psi_0\\rangle=${vectorToLatex(vector)}`,
    `\\langle\\psi_0|\\psi_0\\rangle=${fmt(norm2(vector))}`,
    `\\mathrm{supp}(\\psi_0)=\\{${support.map((row) => row.basis.replace(">", "\\rangle")).join(", ")}\\}`,
  ];
  return {
    latex,
    markdown: `Initial computational basis state |${ctx.initialBasisState}> in big-endian ordering. Norm ${fmt(norm2(vector))}; support cardinality ${support.length}.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock label="State vector" math={latex[1]} />
        <LatexBlock label="Normalization" math={latex[2]} compact />
        <InvariantGrid rows={[
          ["Hilbert dimension", String(1 << ctx.numQubits)],
          ["Basis ordering", "big-endian"],
          ["Support cardinality", String(support.length)],
          ["Global phase convention", "canonical real unit amplitude"],
        ]} />
      </ResearchBlock>
    ),
  };
}

function operatorDefinitionsSection(ctx: ResearchContext): SectionContent {
  const latex = ctx.derivation.steps.flatMap((step, index) => {
    return [
      `U_{${index + 1}}=${matrixToLatex(step.gate.effectiveLocalMatrix)}`,
      `U_{${index + 1}}^{\\dagger}U_{${index + 1}}=I`,
      `\\det(U_{${index + 1}})=${detLatex(step.gate.effectiveLocalMatrix)},\\quad \\mathrm{tr}(U_{${index + 1}})=${complexToLatex(trace(step.gate.effectiveLocalMatrix))}`,
      `\\mathrm{Spectrum}(U_{${index + 1}})=${verifiedGateValue(ctx, step.placement.id, "eigenvalues") ?? "\\text{Wolfram verification unavailable}"}`,
    ];
  });
  return {
    latex: latex.length ? latex : ["\\text{No nontrivial gate operators are present.}"],
    markdown: ctx.derivation.steps.map((step, i) => `${i + 1}. ${step.placement.gateType}: dim ${step.gate.effectiveLocalMatrix.length}, stack ${step.gate.stackCount}.`).join("\n"),
    render: () => (
      <ResearchBlock>
        {ctx.derivation.steps.length === 0 ? <p>No gate operators are present.</p> : ctx.derivation.steps.map((step, index) => {
          const spectral = spectralData(step.gate.effectiveLocalMatrix);
          const verifiedEigenvalues = verifiedGateValue(ctx, step.placement.id, "eigenvalues");
          return (
            <details key={step.placement.id} className="math-proof" open={index === 0}>
              <summary className="math-proof-summary">
                <span className="report-section-title">{index + 1}. {step.placement.gateType}^{step.gate.stackCount}</span>
                <span className="math-why">{step.gate.effectiveLocalMatrix.length} x {step.gate.effectiveLocalMatrix.length}</span>
              </summary>
              <div className="math-proof-body">
                <MatrixRenderer matrix={step.gate.effectiveLocalMatrix} maxDim={8} />
                <InvariantGrid rows={[
                  ["Operator class", "finite-dimensional unitary"],
                  ["Hermitian", isHermitian(step.gate.effectiveLocalMatrix) ? "yes" : "no"],
                  ["Unitary", verificationLabel(ctx, verifiedGateValue(ctx, step.placement.id, "unitarity"), isUnitary(step.gate.effectiveLocalMatrix) ? "native yes" : "native no")],
                  ["Determinant", verificationLabel(ctx, verifiedGateValue(ctx, step.placement.id, "determinant"), detLatex(step.gate.effectiveLocalMatrix))],
                  ["Trace", verificationLabel(ctx, verifiedGateValue(ctx, step.placement.id, "trace"), complexToText(trace(step.gate.effectiveLocalMatrix)))],
                  ["Eigenvalues", verificationLabel(ctx, verifiedEigenvalues, spectral.values.map(complexToText).join(", "))],
                ]} />
                <LatexBlock label="Spectral resolution" math={verifiedEigenvalues ? `U=\\sum_i\\lambda_i|v_i\\rangle\\langle v_i|\\quad\\text{(Wolfram verified)}` : `\\text{Spectral resolution unavailable until Wolfram verifies it.}`} compact />
                {!verifiedEigenvalues && spectral.vectors.map((vector, i) => (
                  <LatexBlock key={i} label={`eigenvector ${i + 1}`} math={`|v_${i + 1}\\rangle=${vectorToLatex(vector)}`} compact />
                ))}
              </div>
            </details>
          );
        })}
      </ResearchBlock>
    ),
  };
}

function tensorEmbeddingSection(ctx: ResearchContext): SectionContent {
  const latex = ctx.derivation.steps.flatMap((step, i) => [
    `U_{${i + 1}}^{local}=${matrixToLatex(step.gate.effectiveLocalMatrix)}`,
    `I_2=${matrixToLatex(identity(2))}`,
    `\\widetilde U_{${i + 1}}=\\mathrm{Embed}_{${step.placement.qubitTargets.join(",")}}(U_{${i + 1}}^{local})`,
    `\\widetilde U_{${i + 1}}=${matrixToLatex(step.gate.fullMatrix)}`,
  ]);
  return {
    latex: latex.length ? latex : ["\\widetilde U=I"],
    markdown: "Each local operator is embedded by explicit Kronecker construction with identity operators on untouched tensor factors.",
    render: () => (
      <ResearchBlock>
        {ctx.derivation.steps.map((step, i) => (
          <details key={step.placement.id} className="math-proof">
            <summary className="math-proof-summary">
              <span className="report-section-title">Embedding {i + 1}: {step.placement.gateType} on q[{step.placement.qubitTargets.join(", ")}]</span>
            </summary>
            <div className="math-proof-body">
              <LatexBlock label="Step 1: local operator" math={`U=${matrixToLatex(step.gate.effectiveLocalMatrix)}`} />
              <LatexBlock label="Step 2: identity factor" math={`I_2=${matrixToLatex(identity(2))}`} compact />
              <LatexBlock label="Step 3: Kronecker construction" math={`\\widetilde U=\\bigotimes_{k=0}^{${ctx.numQubits - 1}} A_k\\quad\\text{with target substitution and permutation as required}`} />
              {step.gate.tensorBlocks.slice(0, 8).map((block) => (
                <LatexBlock key={`${block.row}-${block.col}`} label={`Step 4: block (${block.row},${block.col})`} math={`${complexToLatex(block.scalar)}I=${matrixToLatex(block.block)}`} compact />
              ))}
              <LatexBlock label="Step 5: embedded operator" math={`\\widetilde U=${matrixToLatex(step.gate.fullMatrix)}`} />
              <MatrixRenderer matrix={step.gate.fullMatrix} rowLabels={ctx.derivation.basisLabels} colLabels={ctx.derivation.basisLabels} maxDim={8} />
            </div>
          </details>
        ))}
      </ResearchBlock>
    ),
  };
}

function stateEvolutionSection(ctx: ResearchContext): SectionContent {
  const latex = ctx.derivation.steps.flatMap((step, i) => [
    `|\\psi_${i}\\rangle=${vectorToLatex(step.inputState)}`,
    `|\\psi_${i + 1}\\rangle=\\widetilde U_${i + 1}|\\psi_${i}\\rangle=${vectorToLatex(step.outputState)}`,
    ...step.multiplication.map((cell) => `(U\\psi)_{${cell.row}}=${cell.terms.join("+")}=${complexToLatex(cell.total)}`),
  ]);
  return {
    latex: latex.length ? latex : [`|\\psi_0\\rangle=${vectorToLatex(ctx.derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag })))}`],
    markdown: "State evolution is computed by row-expanding every embedded operator against the current state vector.",
    render: () => (
      <ResearchBlock>
        {ctx.derivation.steps.map((step, i) => (
          <details key={step.placement.id} className="math-proof" open={i === 0}>
            <summary className="math-proof-summary"><span className="report-section-title">{`State transition ${i} -> ${i + 1}`}</span></summary>
            <div className="math-proof-body">
              <LatexBlock label="Symbolic action" math={`(U\\psi)_i=\\sum_j U_{ij}\\psi_j`} compact />
              <LatexBlock label="Input" math={`|\\psi_${i}\\rangle=${vectorToLatex(step.inputState)}`} />
              {step.multiplication.map((cell) => (
                <LatexBlock key={cell.row} label={`row ${cell.row}`} math={`(U\\psi)_{${cell.row}}=${cell.terms.join("+")}=${complexToLatex(cell.total)}`} compact />
              ))}
              <StateInvariantTable vector={step.outputState} basisLabels={ctx.derivation.basisLabels} />
            </div>
          </details>
        ))}
      </ResearchBlock>
    ),
  };
}

function circuitUnitarySection(ctx: ResearchContext): SectionContent {
  const intermediates: ComplexMatrix[] = [];
  ctx.derivation.steps.reduce((acc, step) => {
    const next = matMul(step.gate.fullMatrix, acc);
    intermediates.push(next);
    return next;
  }, identity(1 << ctx.numQubits));
  const spectral = spectralData(ctx.circuitUnitary);
  const latex = [
    `U_{circuit}=U_n\\cdots U_2U_1`,
    ...intermediates.map((m, i) => `U^{(${i + 1})}=${matrixToLatex(m)}`),
    `U_{circuit}=${matrixToLatex(ctx.circuitUnitary)}`,
    `\\det(U_{circuit})=${detLatex(ctx.circuitUnitary)},\\quad \\mathrm{tr}(U_{circuit})=${complexToLatex(trace(ctx.circuitUnitary))}`,
  ];
  return {
    latex,
    markdown: `Circuit unitary assembled from ${ctx.derivation.steps.length} ordered embedded operators.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock label="Ordered product" math={latex[0]} />
        {intermediates.map((m, i) => <LatexBlock key={i} label={`intermediate product ${i + 1}`} math={`U^{(${i + 1})}=${matrixToLatex(m)}`} />)}
        <MatrixRenderer matrix={ctx.circuitUnitary} rowLabels={ctx.derivation.basisLabels} colLabels={ctx.derivation.basisLabels} maxDim={8} />
        <InvariantGrid rows={[
          ["Determinant", verificationLabel(ctx, verifiedCircuitValue(ctx, "determinant"), detLatex(ctx.circuitUnitary))],
          ["Trace", verificationLabel(ctx, verifiedCircuitValue(ctx, "trace"), complexToText(trace(ctx.circuitUnitary)))],
          ["Eigenvalues", verificationLabel(ctx, verifiedCircuitValue(ctx, "eigenvalues"), spectral.values.map(complexToText).join(", "))],
        ]} />
      </ResearchBlock>
    ),
  };
}

function verificationSection(ctx: ResearchContext): SectionContent {
  const status = ctx.verification?.status ?? (ctx.verificationError ? "UNAVAILABLE" : "UNAVAILABLE");
  const message = ctx.verification?.message ?? ctx.verificationError ?? "Waiting for Wolfram verification.";
  const rows: [string, string][] = [
    ["Overall status", status],
    ["Authority", ctx.verification?.source ?? "Wolfram unavailable"],
    ["Query hash", ctx.verification?.query_hash?.slice(0, 16) ?? "not available"],
    ["Warnings", String(ctx.verification?.warnings?.length ?? (ctx.verificationError ? 1 : 0))],
  ];
  return {
    latex: [`\\text{Wolfram verification status: ${status}}`],
    markdown: `${status}: ${message}`,
    render: () => (
      <ResearchBlock>
        <p className="text-sm text-text-secondary">{message}</p>
        <InvariantGrid rows={rows} />
        {(ctx.verification?.warnings ?? []).map((warning, index) => (
          <div key={index} className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-100">
            <strong>Research Verification Warning:</strong> {warning.message}
            {warning.difference !== undefined && <span> Difference: {fmt(warning.difference)}</span>}
          </div>
        ))}
        {!ctx.verification && (
          <p className="text-xs text-text-muted">Wolfram-derived sections remain unavailable until the server verifies this circuit.</p>
        )}
      </ResearchBlock>
    ),
  };
}

function VerificationBanner({ verification, error }: { verification: ResearchVerification | null; error: string | null }): JSX.Element {
  const status = verification?.status ?? (error ? "UNAVAILABLE" : "UNAVAILABLE");
  const label = verification ? (verification.status === "VERIFIED" ? "Wolfram Verified" : verification.status === "DISCREPANCY" ? "Wolfram discrepancy" : "Wolfram verification unavailable") : error ? "Wolfram verification unavailable" : "Wolfram verification pending";
  return (
    <div className={`mb-3 rounded-md border px-3 py-2 text-xs ${status === "VERIFIED" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100" : status === "DISCREPANCY" ? "border-amber-500/40 bg-amber-500/10 text-amber-100" : "border-slate-500/40 bg-slate-500/10 text-text-secondary"}`}>
      <strong>Research Mode:</strong> {label}
    </div>
  );
}

function densitySection(ctx: ResearchContext): SectionContent {
  const finalVector = ctx.derivation.finalState.amplitudes.map((a) => ({ re: a.real, im: a.imag }));
  const entries = ctx.finalDensity.flatMap((row, i) => row.map((value, j) => `\\rho_{${i}${j}}=\\psi_${i}\\psi_${j}^{*}=${complexToLatex(finalVector[i] ?? ZERO)}\\cdot ${complexToLatex(conj(finalVector[j] ?? ZERO))}=${complexToLatex(value)}`));
  return {
    latex: [`\\rho=|\\psi\\rangle\\langle\\psi|`, ...entries, `\\rho=${matrixToLatex(ctx.finalDensity)}`],
    markdown: "Density operator constructed elementwise from the final state, or read from density-mode simulator output when present.",
    render: () => (
      <ResearchBlock>
        <LatexBlock label="Outer product" math={"\\rho_{ij}=\\psi_i\\psi_j^*"} />
        {entries.slice(0, 64).map((entry, i) => <LatexBlock key={i} label={`element ${i + 1}`} math={entry} compact />)}
        {entries.length > 64 && <p className="text-xs text-text-muted">Additional element derivations are included in Markdown/LaTeX export.</p>}
        <MatrixRenderer matrix={ctx.finalDensity} rowLabels={ctx.derivation.basisLabels} colLabels={ctx.derivation.basisLabels} maxDim={8} />
      </ResearchBlock>
    ),
  };
}

function schmidtSection(ctx: ResearchContext): SectionContent {
  if (ctx.numQubits < 2) {
    return simpleSection("\\text{Schmidt decomposition is not applicable for a one-qubit register.}", "No nontrivial bipartition exists.");
  }
  const coeffs = schmidtCoefficientsFirstCut(ctx.derivation.finalState.amplitudes.map((a) => ({ re: a.real, im: a.imag })), ctx.numQubits);
  const entropy = entropyFromProbabilities(coeffs.map((c) => c * c));
  return {
    latex: [
      `|\\psi\\rangle=\\sum_i \\lambda_i |u_i\\rangle|v_i\\rangle`,
      `\\{\\lambda_i\\}=\\{${coeffs.map(fmt).join(", ")}\\}`,
      `\\mathrm{rank}_S=${coeffs.filter((c) => c > EPS).length}`,
      `S=-\\sum_i\\lambda_i^2\\log_2\\lambda_i^2=${fmt(entropy)}`,
    ],
    markdown: `Schmidt coefficients across q[0]|rest: ${coeffs.map(fmt).join(", ")}. Schmidt rank ${coeffs.filter((c) => c > EPS).length}.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock math={`|\\psi\\rangle=\\sum_i \\lambda_i |u_i\\rangle|v_i\\rangle`} />
        <InvariantGrid rows={[
          ["Schmidt coefficients", coeffs.map(fmt).join(", ")],
          ["Schmidt rank", String(coeffs.filter((c) => c > EPS).length)],
          ["Entanglement entropy", fmt(entropy)],
        ]} />
      </ResearchBlock>
    ),
  };
}

function partialTraceSection(ctx: ResearchContext): SectionContent {
  if (ctx.numQubits < 2) return simpleSection("\\rho_A=\\rho", "The register has no environment to trace out.");
  const reduced = partialTraceFirstQubit(ctx.finalDensity, ctx.numQubits);
  const restDim = 1 << (ctx.numQubits - 1);
  const derivations = [0, 1].flatMap((i) => [0, 1].map((j) => `(\\rho_A)_{${i}${j}}=\\sum_{b=0}^{${restDim - 1}}\\rho_{${i}b,${j}b}=${complexToLatex(reduced[i][j])}`));
  return {
    latex: ["\\rho_A=\\mathrm{Tr}_B(\\rho)", ...derivations, `\\rho_A=${matrixToLatex(reduced)}`],
    markdown: "Reduced density operator obtained by explicit summation over the complementary subsystem basis.",
    render: () => (
      <ResearchBlock>
        <LatexBlock math={"(\\rho_A)_{ij}=\\sum_b\\rho_{ib,jb}"} />
        {derivations.map((item) => <LatexBlock key={item} math={item} compact />)}
        <MatrixRenderer matrix={reduced} maxDim={8} />
      </ResearchBlock>
    ),
  };
}

function entropySection(ctx: ResearchContext): SectionContent {
  const rho = ctx.numQubits >= 2 ? partialTraceFirstQubit(ctx.finalDensity, ctx.numQubits) : ctx.finalDensity;
  const eig = spectralData(rho).values.map((z) => Math.max(0, z.re)).filter((v) => v > EPS);
  const terms = eig.map((v) => `-${fmt(v)}\\log_2(${fmt(v)})=${fmt(-v * Math.log2(v))}`);
  const entropy = entropyFromProbabilities(eig);
  return {
    latex: [`S(\\rho)=-\\mathrm{Tr}(\\rho\\log_2\\rho)`, ...terms, `S=${fmt(entropy)}`],
    markdown: `Entropy from nonzero eigenvalues ${eig.map(fmt).join(", ")} equals ${fmt(entropy)}.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock math={"S(\\rho)=-\\sum_i p_i\\log_2 p_i"} />
        {terms.map((term) => <LatexBlock key={term} math={term} compact />)}
        <LatexBlock label="entropy" math={`S=${fmt(entropy)}`} compact />
      </ResearchBlock>
    ),
  };
}

function fidelitySection(ctx: ResearchContext): SectionContent {
  const fid = real(trace(matMul(ctx.finalDensity, ctx.referenceDensity)));
  return simpleSection(`F(\\rho,\\sigma)=\\left(\\mathrm{Tr}\\sqrt{\\sqrt{\\rho}\\sigma\\sqrt{\\rho}}\\right)^2=${fmt(fid)}`, `Pure-reference fidelity against the selected initial basis projector is ${fmt(fid)}.`);
}

function traceDistanceSection(ctx: ResearchContext): SectionContent {
  const delta = matSub(ctx.finalDensity, ctx.referenceDensity);
  const approx = 0.5 * spectralData(delta).values.reduce((sum, z) => sum + mag(z), 0);
  return {
    latex: [`\\Delta=\\rho-\\sigma=${matrixToLatex(delta)}`, `D(\\rho,\\sigma)=\\frac12\\mathrm{Tr}|\\Delta|\\approx ${fmt(approx)}`],
    markdown: `Trace distance against the initial pure reference is approximately ${fmt(approx)}.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock label="difference matrix" math={`\\Delta=\\rho-\\sigma=${matrixToLatex(delta)}`} />
        <LatexBlock label="trace norm" math={`D(\\rho,\\sigma)=\\frac12\\mathrm{Tr}|\\Delta|\\approx ${fmt(approx)}`} />
        <MatrixRenderer matrix={delta} maxDim={8} />
      </ResearchBlock>
    ),
  };
}

function puritySection(ctx: ResearchContext): SectionContent {
  const rho2 = matMul(ctx.finalDensity, ctx.finalDensity);
  const purity = real(trace(rho2));
  return {
    latex: [`\\rho^2=${matrixToLatex(rho2)}`, `\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`],
    markdown: `Purity equals ${fmt(purity)}.`,
    render: () => (
      <ResearchBlock>
        <LatexBlock label="rho squared" math={`\\rho^2=${matrixToLatex(rho2)}`} />
        <LatexBlock label="purity" math={`\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`} compact />
        <MatrixRenderer matrix={rho2} maxDim={8} />
      </ResearchBlock>
    ),
  };
}

function correlationSection(ctx: ResearchContext): SectionContent {
  if (ctx.numQubits < 2) return simpleSection("\\text{Two-qubit Pauli correlations require at least two qubits.}", "Correlation tensor not applicable.");
  const rows = ["X", "Y", "Z"].map((name) => {
    const op = embedTwoQubit(pauli(name), pauli(name), ctx.numQubits);
    const value = trace(matMul(ctx.finalDensity, op));
    return { name, op, value };
  });
  return {
    latex: rows.flatMap((row) => [`${row.name}\\otimes ${row.name}=${matrixToLatex(row.op)}`, `\\langle ${row.name}\\otimes ${row.name}\\rangle=\\mathrm{Tr}(\\rho(${row.name}\\otimes ${row.name}))=${complexToLatex(row.value)}`]),
    markdown: rows.map((row) => `<${row.name}${row.name}> = ${complexToText(row.value)}`).join("; "),
    render: () => (
      <ResearchBlock>
        {rows.map((row) => (
          <LatexBlock key={row.name} label={`${row.name}${row.name} correlation`} math={`\\langle ${row.name}\\otimes ${row.name}\\rangle=\\mathrm{Tr}(\\rho(${row.name}\\otimes ${row.name}))=${complexToLatex(row.value)}`} />
        ))}
      </ResearchBlock>
    ),
  };
}

function measurementSection(ctx: ResearchContext): SectionContent {
  const rows = amplitudeRows(ctx.derivation.finalState);
  const latex = rows.map((row, i) => `P(${row.basis.replace(">", "\\rangle")})=\\langle\\psi|\\Pi_${i}|\\psi\\rangle=|${complexToLatex(row.amplitude)}|^2=${fmt(row.probability)}`);
  return {
    latex: [`\\Pi_i=|i\\rangle\\langle i|`, ...latex],
    markdown: "Computational-basis projective measurement probabilities derived from rank-one projectors.",
    render: () => (
      <ResearchBlock>
        <LatexBlock math={"\\Pi_i=|i\\rangle\\langle i|,\\quad P(i)=\\mathrm{Tr}(\\rho\\Pi_i)"} />
        {latex.slice(0, 64).map((item) => <LatexBlock key={item} math={item} compact />)}
      </ResearchBlock>
    ),
  };
}

function summarySection(ctx: ResearchContext): SectionContent {
  const purity = real(trace(matMul(ctx.finalDensity, ctx.finalDensity)));
  const support = amplitudeRows(ctx.derivation.finalState).filter((row) => row.probability > EPS);
  return {
    latex: [`\\dim\\mathcal H=${1 << ctx.numQubits}`, `\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`, `|\\mathrm{supp}(\\psi)|=${support.length}`],
    markdown: `Dimension ${1 << ctx.numQubits}; gates ${ctx.gates.length}; support ${support.length}; purity ${fmt(purity)}.`,
    render: () => (
      <ResearchBlock>
        <InvariantGrid rows={[
          ["Dimension", String(1 << ctx.numQubits)],
          ["Gate placements", String(ctx.gates.length)],
          ["Final support", String(support.length)],
          ["Purity", fmt(purity)],
          ["Noise/density mode", ctx.resultsV2?.final_density ? "density data available" : "pure statevector-derived density"],
          ["Metrics fidelity", ctx.metrics?.fidelity ? fmt(ctx.metrics.fidelity.fidelity) : "not computed"],
        ]} />
      </ResearchBlock>
    ),
  };
}

function simpleSection(latexLine: string, markdown: string): SectionContent {
  return {
    latex: [latexLine],
    markdown,
    render: () => <ResearchBlock><LatexBlock math={latexLine} /></ResearchBlock>,
  };
}

function verifiedGateValue(ctx: ResearchContext, gateId: string, key: string): string | null {
  const gates = ctx.verification?.calculations?.gates;
  if (!Array.isArray(gates)) return null;
  const row = gates.find((item) => isRecord(item) && item.gate_id === gateId);
  if (!isRecord(row)) return null;
  return formatVerifiedValue(row[key]);
}

function verifiedCircuitValue(ctx: ResearchContext, key: string): string | null {
  const circuit = ctx.verification?.calculations?.circuitUnitary;
  if (!isRecord(circuit)) return null;
  return formatVerifiedValue(circuit[key]);
}

function verificationLabel(ctx: ResearchContext, wolframValue: string | null, nativeValue: string): string {
  if (wolframValue) return `${wolframValue} (Wolfram verified)`;
  if (ctx.verification?.status === "DISCREPANCY") return `DISCREPANCY: native ${nativeValue}`;
  return `UNAVAILABLE: native simulated ${nativeValue}`;
}

function formatVerifiedValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => formatVerifiedValue(item) ?? String(item)).join(", ");
  if (isRecord(value)) {
    if (typeof value.exact === "string" && typeof value.numeric === "string") return `${value.exact} ~= ${value.numeric}`;
    if (typeof value.exact === "string") return value.exact;
    if (typeof value.numeric === "string") return value.numeric;
  }
  return JSON.stringify(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function ResearchBlock({ children }: { children: ReactNode }): JSX.Element {
  return <div className="research-math-block">{children}</div>;
}

function InvariantGrid({ rows }: { rows: [string, string][] }): JSX.Element {
  return (
    <div className="research-invariant-grid">
      {rows.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function StateInvariantTable({ vector, basisLabels }: { vector: Complex[]; basisLabels: string[] }): JSX.Element {
  const support = vector.map((amp, i) => ({ amp, label: basisLabels[i] })).filter(({ amp }) => mag2(amp) > EPS);
  return (
    <InvariantGrid rows={[
      ["Normalization", fmt(norm2(vector))],
      ["Support", support.map((row) => row.label).join(", ") || "empty"],
      ["Sparsity", `${vector.length - support.length}/${vector.length} zero amplitudes`],
      ["Nonzero amplitudes", support.map((row) => `${row.label}: ${complexToText(row.amp)}`).join("; ") || "none"],
      ["Dominant phase", support[0] ? fmt(Math.atan2(support[0].amp.im, support[0].amp.re)) : "0"],
    ]} />
  );
}

function identity(dim: number): ComplexMatrix {
  return Array.from({ length: dim }, (_, r) => Array.from({ length: dim }, (_, c) => (r === c ? ONE : ZERO)));
}

function matMul(a: ComplexMatrix, b: ComplexMatrix): ComplexMatrix {
  return a.map((row) => (b[0] ?? []).map((_, c) => row.map((v, k) => mul(v, b[k]?.[c] ?? ZERO)).reduce(add, ZERO)));
}

function matSub(a: ComplexMatrix, b: ComplexMatrix): ComplexMatrix {
  return a.map((row, r) => row.map((v, c) => add(v, scale(b[r]?.[c] ?? ZERO, -1))));
}

function trace(a: ComplexMatrix): Complex {
  return a.map((row, i) => row[i] ?? ZERO).reduce(add, ZERO);
}

function add(a: Complex, b: Complex): Complex {
  return cleanComplex({ re: a.re + b.re, im: a.im + b.im });
}

function mul(a: Complex, b: Complex): Complex {
  return cleanComplex({ re: a.re * b.re - a.im * b.im, im: a.re * b.im + a.im * b.re });
}

function scale(a: Complex, factor: number): Complex {
  return cleanComplex({ re: a.re * factor, im: a.im * factor });
}

function conj(a: Complex): Complex {
  return { re: a.re, im: -a.im };
}

function mag2(a: Complex): number {
  return a.re * a.re + a.im * a.im;
}

function mag(a: Complex): number {
  return Math.sqrt(mag2(a));
}

function norm2(vector: Complex[]): number {
  return vector.reduce((sum, z) => sum + mag2(z), 0);
}

function real(z: Complex): number {
  return Math.abs(z.re) < EPS ? 0 : z.re;
}

function cleanComplex(z: Complex): Complex {
  return { re: Math.abs(z.re) < EPS ? 0 : z.re, im: Math.abs(z.im) < EPS ? 0 : z.im };
}

function isHermitian(m: ComplexMatrix): boolean {
  return m.every((row, r) => row.every((v, c) => Math.abs(v.re - (m[c]?.[r]?.re ?? 0)) < 1e-8 && Math.abs(v.im + (m[c]?.[r]?.im ?? 0)) < 1e-8));
}

function isUnitary(m: ComplexMatrix): boolean {
  const adj = m[0].map((_, c) => m.map((row) => conj(row[c])));
  const product = matMul(adj, m);
  return product.every((row, r) => row.every((v, c) => Math.abs(v.re - (r === c ? 1 : 0)) < 1e-8 && Math.abs(v.im) < 1e-8));
}

function detLatex(m: ComplexMatrix): string {
  if (m.length === 1) return complexToLatex(m[0][0]);
  if (m.length === 2) return complexToLatex(add(mul(m[0][0], m[1][1]), scale(mul(m[0][1], m[1][0]), -1)));
  return "\\det(\\text{matrix})";
}

function spectralData(m: ComplexMatrix): { values: Complex[]; vectors: Complex[][] } {
  if (m.length === 2) {
    const a = m[0][0].re;
    const b = m[0][1].re;
    const c = m[1][0].re;
    const d = m[1][1].re;
    const disc = Math.sqrt(Math.max(0, (a + d) * (a + d) - 4 * (a * d - b * c)));
    const l1 = { re: (a + d + disc) / 2, im: 0 };
    const l2 = { re: (a + d - disc) / 2, im: 0 };
    return { values: [l1, l2], vectors: [eigenvector2(m, l1), eigenvector2(m, l2)] };
  }
  return { values: m.map((row, i) => row[i] ?? ZERO), vectors: identity(m.length).map((row) => row) };
}

function eigenvector2(m: ComplexMatrix, lambda: Complex): Complex[] {
  const a = add(m[0][0], scale(lambda, -1));
  const b = m[0][1];
  const candidate = mag(b) > EPS ? [{ re: -b.re, im: -b.im }, a] : [m[1][0], scale(add(m[1][1], scale(lambda, -1)), -1)];
  const n = Math.sqrt(norm2(candidate));
  return n < EPS ? [ONE, ZERO] : candidate.map((z) => scale(z, 1 / n));
}

function partialTraceFirstQubit(rho: ComplexMatrix, numQubits: number): ComplexMatrix {
  const restDim = 1 << (numQubits - 1);
  return [0, 1].map((i) =>
    [0, 1].map((j) =>
      Array.from({ length: restDim }, (_, b) => rho[(i << (numQubits - 1)) + b]?.[(j << (numQubits - 1)) + b] ?? ZERO).reduce(add, ZERO),
    ),
  );
}

function schmidtCoefficientsFirstCut(vector: Complex[], numQubits: number): number[] {
  const restDim = 1 << (numQubits - 1);
  const rows = [vector.slice(0, restDim), vector.slice(restDim, restDim * 2)];
  const gram = rows.map((rowA) => rows.map((_, j) => rowA.map((a, k) => mul(a, conj(rows[j][k] ?? ZERO))).reduce(add, ZERO)));
  return spectralData(gram).values.map((v) => Math.sqrt(Math.max(0, v.re))).sort((a, b) => b - a);
}

function entropyFromProbabilities(values: number[]): number {
  return values.filter((v) => v > EPS).reduce((sum, v) => sum - v * Math.log2(v), 0);
}

function pauli(name: string): ComplexMatrix {
  if (name === "X") return [[ZERO, ONE], [ONE, ZERO]];
  if (name === "Y") return [[ZERO, { re: 0, im: -1 }], [I, ZERO]];
  return [[ONE, ZERO], [ZERO, { re: -1, im: 0 }]];
}

function embedTwoQubit(a: ComplexMatrix, b: ComplexMatrix, numQubits: number): ComplexMatrix {
  const factors = [a, b, ...Array.from({ length: Math.max(0, numQubits - 2) }, () => identity(2))];
  return factors.reduce((acc, factor) => kron(acc, factor));
}

function kron(a: ComplexMatrix, b: ComplexMatrix): ComplexMatrix {
  return a.flatMap((rowA) => b.map((rowB) => rowA.flatMap((cellA) => rowB.map((cellB) => mul(cellA, cellB)))));
}

function fmt(v: number): string {
  if (Math.abs(v) < EPS) return "0";
  return Number.isInteger(v) ? String(v) : v.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
