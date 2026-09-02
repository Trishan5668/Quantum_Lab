import type { ReactNode } from "react";
import { BlockMath, InlineMath } from "react-katex";
import { LatexBlock } from "../Mathematics/LatexBlock";
import type { ReportMetadata, ReportSection } from "../Reports/ReportReader";
import { EDITOR_LANGUAGES, type EditorLanguageId, type OutputState } from "../../store/editorStore";
import type { LearningMode } from "../../store/platformStore";
import type { GatePlacement } from "../../types";
import { gateMeta } from "../../types";
import {
  analyzeCode,
  circuitSummaryLabel,
  languageDependencies,
  languageReportTitle,
  type CodeAnalysis,
  type CodeBlock,
} from "./codeReportAnalyzer";

interface BuildCodeReportInput {
  language: EditorLanguageId;
  code: string;
  numQubits: number;
  initialBasisState: string;
  gates: GatePlacement[];
  outputState: OutputState;
  outputText: string;
  errorText: string;
  learningMode: LearningMode;
  authorName?: string;
  authorId?: string;
}

export function buildCodeReportMetadata(input: BuildCodeReportInput): ReportMetadata {
  const languageLabel = EDITOR_LANGUAGES.find((item) => item.id === input.language)?.label ?? input.language;
  return {
    reportKind: "Code",
    circuitName: circuitSummaryLabel(input.numQubits, input.gates),
    qubitCount: input.numQubits,
    gateCount: input.gates.length,
    initialState: `|${input.initialBasisState}>`,
    authorName: input.authorName,
    authorId: input.authorId,
    learningMode: input.learningMode,
    generatedAt: new Date().toISOString(),
    circuitJson: {
      numQubits: input.numQubits,
      initialBasisState: input.initialBasisState,
      gates: input.gates,
      language: input.language,
      languageLabel,
    },
    gateSequence: input.gates.map(
      (gate) =>
        `${gate.gateType}${gate.stackCount && gate.stackCount > 1 ? `^${gate.stackCount}` : ""} q[${gate.qubitTargets.join(",")}] @t${gate.timeStep}`,
    ),
    backendVersion: `editor/${input.language}`,
  };
}

export function buildCodeReport(input: BuildCodeReportInput): ReportSection[] {
  const analysis = analyzeCode(input.code, input.language);
  const circuitLabel = circuitSummaryLabel(input.numQubits, input.gates);
  const executionLabel =
    input.outputState === "success"
      ? "Successful"
      : input.outputState === "error"
        ? "Failed"
        : input.outputState === "running"
          ? "Running"
          : "Not executed";

  const sections: ReportSection[] = [
    section(
      "abstract",
      "Abstract / Overview",
      "Executive summary of the quantum program",
      abstractMarkdown(input, analysis, circuitLabel, executionLabel),
      abstractLatex(input),
      () => <AbstractChapter input={input} analysis={analysis} circuitLabel={circuitLabel} executionLabel={executionLabel} />,
      true,
    ),
    section(
      "objective",
      "Program Objective",
      "What this program is designed to compute",
      objectiveMarkdown(input, analysis),
      [],
      () => <ObjectiveChapter input={input} analysis={analysis} />,
    ),
    section(
      "environment",
      "Environment and Dependencies",
      "Runtime stack required to execute this program",
      environmentMarkdown(input.language),
      [],
      () => <EnvironmentChapter language={input.language} />,
    ),
    section(
      "source",
      "Source Code",
      "Original program as written in the editor",
      "The source code is reproduced verbatim below.",
      [],
      () => <SourceChapter code={input.code} language={input.language} />,
      true,
    ),
    section(
      "architecture",
      "Code Architecture",
      "Structural organization of the program",
      architectureMarkdown(analysis),
      [],
      () => <ArchitectureChapter analysis={analysis} />,
    ),
    section(
      "explanation",
      "Line-by-Line / Block-by-Block Explanation",
      "Annotated walkthrough of each code block",
      explanationMarkdown(analysis),
      [],
      () => <ExplanationChapter analysis={analysis} />,
    ),
    section(
      "circuit",
      "Quantum Algorithm / Circuit Interpretation",
      "Mapping between code and the QuantumLab circuit model",
      circuitMarkdown(input, circuitLabel),
      circuitLatex(input),
      () => <CircuitChapter input={input} circuitLabel={circuitLabel} />,
      true,
    ),
    section(
      "math",
      "Mathematical Formulation",
      "Unitary operators implied by the circuit",
      mathMarkdown(input),
      mathLatex(input),
      () => <MathChapter input={input} />,
    ),
  ];

  if (input.gates.length > 0) {
    sections.push(
      section(
        "evolution",
        "State Evolution",
        "How the quantum state transforms through the circuit",
        evolutionMarkdown(input),
        evolutionLatex(input),
        () => <EvolutionChapter input={input} />,
      ),
    );
  }

  if (analysis.hasMeasurement || input.outputState === "success") {
    sections.push(
      section(
        "measurement",
        "Measurement / Output Analysis",
        "Observables, readouts, and printed results",
        measurementMarkdown(input, analysis),
        [],
        () => <MeasurementChapter input={input} analysis={analysis} />,
      ),
    );
  }

  sections.push(
    section(
      "complexity",
      "Computational Complexity",
      "Resource scaling of the implemented circuit",
      complexityMarkdown(input),
      complexityLatex(input),
      () => <ComplexityChapter input={input} />,
    ),
    section(
      "implementation",
      "Implementation Notes",
      "Framework-specific considerations",
      implementationMarkdown(input, analysis),
      [],
      () => <ImplementationChapter input={input} analysis={analysis} />,
    ),
  );

  if (input.outputState !== "idle") {
    sections.push(
      section(
        "execution",
        "Execution Results",
        "Captured stdout and runtime outcome",
        executionMarkdown(input),
        [],
        () => <ExecutionChapter input={input} />,
        true,
      ),
    );
  }

  sections.push(
    section(
      "limitations",
      "Error Analysis / Limitations",
      "Known constraints and failure modes",
      limitationsMarkdown(input, analysis),
      [],
      () => <LimitationsChapter input={input} analysis={analysis} />,
    ),
    section(
      "reproducibility",
      "Reproducibility",
      "How to rerun and verify this report",
      reproducibilityMarkdown(input),
      [],
      () => <ReproducibilityChapter input={input} />,
    ),
    section(
      "conclusion",
      "Conclusion",
      "Summary of findings",
      conclusionMarkdown(input, analysis, circuitLabel, executionLabel),
      [],
      () => <ConclusionChapter circuitLabel={circuitLabel} executionLabel={executionLabel} />,
    ),
  );

  return filterCodeSections(sections, input.learningMode).map((item, index) => ({
    ...item,
    number: String(index + 1),
  }));
}

function filterCodeSections(sections: ReportSection[], mode: LearningMode): ReportSection[] {
  if (mode === "research") return sections;
  const allowed =
    mode === "explore"
      ? new Set([
          "Abstract / Overview",
          "Source Code",
          "Quantum Algorithm / Circuit Interpretation",
          "Execution Results",
          "Conclusion",
        ])
      : mode === "understand"
        ? new Set([
            "Abstract / Overview",
            "Program Objective",
            "Source Code",
            "Code Architecture",
            "Quantum Algorithm / Circuit Interpretation",
            "Mathematical Formulation",
            "Execution Results",
            "Conclusion",
          ])
        : new Set([
            "Abstract / Overview",
            "Program Objective",
            "Source Code",
            "Code Architecture",
            "Line-by-Line / Block-by-Block Explanation",
            "Quantum Algorithm / Circuit Interpretation",
            "Mathematical Formulation",
            "State Evolution",
            "Measurement / Output Analysis",
            "Computational Complexity",
            "Execution Results",
            "Conclusion",
          ]);
  return sections.filter((section) => allowed.has(section.title));
}

function section(
  id: string,
  title: string,
  subtitle: string,
  markdown: string,
  latex: string[],
  render: () => ReactNode,
  defaultOpen = false,
): ReportSection {
  return {
    id: `code-${id}`,
    number: "",
    title,
    subtitle,
    markdown,
    latex,
    searchText: [title, subtitle, markdown, ...latex].join(" "),
    defaultOpen,
    render,
  };
}

function AbstractChapter({
  input,
  analysis,
  circuitLabel,
  executionLabel,
}: {
  input: BuildCodeReportInput;
  analysis: CodeAnalysis;
  circuitLabel: string;
  executionLabel: string;
}): JSX.Element {
  const languageLabel = EDITOR_LANGUAGES.find((item) => item.id === input.language)?.label ?? input.language;
  return (
    <Article>
      <p className="code-report-lead">
        This report documents a <strong>{languageLabel}</strong> quantum program written in the QuantumLab Editor.
        The linked simulator circuit contains <strong>{circuitLabel}</strong>. Execution status: <strong>{executionLabel}</strong>.
      </p>
      <MetaGrid
        rows={[
          ["Language", languageLabel],
          ["Lines of code", String(analysis.lineCount)],
          ["Detected operations", analysis.detectedGates.join(", ") || "None identified in source"],
          ["Learning mode", input.learningMode],
        ]}
      />
    </Article>
  );
}

function ObjectiveChapter({ input, analysis }: { input: BuildCodeReportInput; analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      <p>
        {objectiveText(input, analysis)}
      </p>
    </Article>
  );
}

function EnvironmentChapter({ language }: { language: EditorLanguageId }): JSX.Element {
  return (
    <Article>
      <ul>
        {languageDependencies(language).map((dep) => (
          <li key={dep}>{dep}</li>
        ))}
      </ul>
    </Article>
  );
}

function SourceChapter({ code, language }: { code: string; language: EditorLanguageId }): JSX.Element {
  const prismLang = language === "qsharp" ? "qsharp" : "python";
  return (
    <Article>
      <p>The following listing reproduces the editor buffer exactly. No rewriting or formatting normalization is applied.</p>
      <CodeBlock code={code} language={prismLang} />
    </Article>
  );
}

function ArchitectureChapter({ analysis }: { analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      <p>
        The program contains {analysis.blocks.length} logical block{analysis.blocks.length === 1 ? "" : "s"} separated by blank lines.
        {analysis.hasQnode && " A PennyLane QNode wraps the quantum subroutine."}
        {analysis.hasEntryPoint && " The Q# program declares an entry-point operation."}
        {analysis.hasDevice && " A quantum device/backend is configured explicitly."}
      </p>
      {analysis.definitions.length > 0 && (
        <>
          <p className="code-report-subheading">Definitions</p>
          <ul>
            {analysis.definitions.map((line) => (
              <li key={line}>
                <code>{line}</code>
              </li>
            ))}
          </ul>
        </>
      )}
    </Article>
  );
}

function ExplanationChapter({ analysis }: { analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      {analysis.blocks.map((block) => (
        <details key={`${block.startLine}-${block.endLine}`} className="code-report-block">
          <summary>
            Lines {block.startLine}–{block.endLine}: {block.summary}
          </summary>
          <p>{blockExplanation(block)}</p>
          <CodeBlock code={block.text} language={analysis.language === "qsharp" ? "qsharp" : "python"} compact />
        </details>
      ))}
    </Article>
  );
}

function CircuitChapter({ input, circuitLabel }: { input: BuildCodeReportInput; circuitLabel: string }): JSX.Element {
  return (
    <Article>
      <p>
        QuantumLab maintains a synchronized circuit model used by the simulator preview. The current model is{" "}
        <strong>{circuitLabel}</strong> with initial state <InlineMath math={`|${input.initialBasisState}\\rangle`} />.
      </p>
      {input.gates.length > 0 ? (
        <ol>
          {input.gates
            .slice()
            .sort((a, b) => a.timeStep - b.timeStep)
            .map((gate) => (
              <li key={gate.id}>
                <strong>{gate.gateType}</strong> on qubit
                {gate.qubitTargets.length > 1 ? "s" : ""}{" "}
                {gate.qubitTargets.map((q) => `q[${q}]`).join(", ")} at time step {gate.timeStep}
                {(gate.stackCount ?? 1) > 1 ? ` (stack ×${gate.stackCount})` : ""}
              </li>
            ))}
        </ol>
      ) : (
        <p>No gates are currently placed in the simulator circuit.</p>
      )}
    </Article>
  );
}

function MathChapter({ input }: { input: BuildCodeReportInput }): JSX.Element {
  const latex = mathLatex(input);
  return (
    <Article>
      <p>Gate matrices are expressed in the computational basis. Multi-qubit operators use tensor products on inactive wires.</p>
      {latex.map((math) => (
        <LatexBlock key={math} math={math} />
      ))}
    </Article>
  );
}

function EvolutionChapter({ input }: { input: BuildCodeReportInput }): JSX.Element {
  return (
    <Article>
      <p>
        Starting from <InlineMath math={`|\\psi_0\\rangle = |${input.initialBasisState}\\rangle`} />, the circuit applies a sequence of
        unitaries. The composite operator is
      </p>
      <Equation math={compositeOperatorLatex(input.gates)} />
      <p>Each step is unitary, so probability is conserved before measurement.</p>
    </Article>
  );
}

function MeasurementChapter({ input, analysis }: { input: BuildCodeReportInput; analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      {analysis.hasMeasurement ? (
        <p>The source code includes measurement, sampling, or probability-returning constructs.</p>
      ) : (
        <p>The source code does not declare an explicit measurement primitive, but execution output is available for inspection.</p>
      )}
      {input.outputState === "success" && input.outputText && (
        <>
          <p className="code-report-subheading">Captured output</p>
          <pre className="code-report-output">{input.outputText}</pre>
        </>
      )}
    </Article>
  );
}

function ComplexityChapter({ input }: { input: BuildCodeReportInput }): JSX.Element {
  return (
    <Article>
      <p>
        The simulator circuit uses {input.numQubits} qubit{input.numQubits === 1 ? "" : "s"} and {input.gates.length} gate
        placement{input.gates.length === 1 ? "" : "s"}.
      </p>
      <Equation math={`T = O\\bigl(n_{\\mathrm{gates}}\\cdot 2^{n_{\\mathrm{qubits}}}\\bigr)`} />
      <p>Exact simulation cost grows exponentially with qubit count for arbitrary states.</p>
    </Article>
  );
}

function ImplementationChapter({ input, analysis }: { input: BuildCodeReportInput; analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      <ul>
        {implementationNotes(input, analysis).map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </Article>
  );
}

function ExecutionChapter({ input }: { input: BuildCodeReportInput }): JSX.Element {
  return (
    <Article>
      <MetaGrid
        rows={[
          ["Status", input.outputState],
          ["Stdout", input.outputText ? "Present" : "Empty"],
          ["Error", input.errorText ? "Present" : "None"],
        ]}
      />
      {input.outputText && (
        <>
          <p className="code-report-subheading">Stdout</p>
          <pre className="code-report-output">{input.outputText}</pre>
        </>
      )}
      {input.errorText && (
        <>
          <p className="code-report-subheading">Error</p>
          <pre className="code-report-output code-report-error">{input.errorText}</pre>
        </>
      )}
    </Article>
  );
}

function LimitationsChapter({ input, analysis }: { input: BuildCodeReportInput; analysis: CodeAnalysis }): JSX.Element {
  return (
    <Article>
      <ul>
        <li>Static analysis cannot prove semantic equivalence between editor code and the simulator circuit.</li>
        <li>Mathematical sections are derived from the QuantumLab circuit model and detected source patterns.</li>
        {input.outputState === "idle" && <li>No execution output was available when this report was generated.</li>}
        {input.outputState === "error" && <li>The most recent execution failed; see Execution Results for diagnostics.</li>}
        {!analysis.hasMeasurement && <li>No explicit measurement operation was detected in the source listing.</li>}
      </ul>
    </Article>
  );
}

function ReproducibilityChapter({ input }: { input: BuildCodeReportInput }): JSX.Element {
  return (
    <Article>
      <p>Re-run the program from the editor with the same language selection, then regenerate this report.</p>
      <MetaGrid
        rows={[
          ["Language", input.language],
          ["Qubits", String(input.numQubits)],
          ["Initial state", `|${input.initialBasisState}⟩`],
          ["Gate count", String(input.gates.length)],
        ]}
      />
    </Article>
  );
}

function ConclusionChapter({ circuitLabel, executionLabel }: { circuitLabel: string; executionLabel: string }): JSX.Element {
  return (
    <Article>
      <p>
        This documentation ties the editor source, the QuantumLab circuit ({circuitLabel}), and the latest execution outcome (
        {executionLabel}) into a single reproducible technical record.
      </p>
    </Article>
  );
}

function Article({ children }: { children: ReactNode }): JSX.Element {
  return <div className="code-report-article">{children}</div>;
}

function Equation({ math }: { math: string }): JSX.Element {
  return (
    <div className="code-report-equation">
      <BlockMath math={math} />
    </div>
  );
}

function CodeBlock({ code, language, compact = false }: { code: string; language: string; compact?: boolean }): JSX.Element {
  return (
    <div className={`code-report-source ${compact ? "code-report-source-compact" : ""}`}>
      <div className="code-report-source-label">{language}</div>
      <pre>
        <code>{code}</code>
      </pre>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void navigator.clipboard?.writeText(code)}>
        Copy code
      </button>
    </div>
  );
}

function MetaGrid({ rows }: { rows: Array<[string, string]> }): JSX.Element {
  return (
    <table className="code-report-meta">
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th>{label}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function abstractMarkdown(
  input: BuildCodeReportInput,
  analysis: CodeAnalysis,
  circuitLabel: string,
  executionLabel: string,
): string {
  const languageLabel = EDITOR_LANGUAGES.find((item) => item.id === input.language)?.label ?? input.language;
  return `QuantumLab code report for ${languageLabel}. Circuit: ${circuitLabel}. Execution: ${executionLabel}. ${analysis.lineCount} lines.`;
}

function abstractLatex(input: BuildCodeReportInput): string[] {
  if (input.gates.length === 0) return [];
  return [compositeOperatorLatex(input.gates)];
}

function objectiveMarkdown(input: BuildCodeReportInput, analysis: CodeAnalysis): string {
  return objectiveText(input, analysis);
}

function objectiveText(input: BuildCodeReportInput, analysis: CodeAnalysis): string {
  const languageLabel = EDITOR_LANGUAGES.find((item) => item.id === input.language)?.label ?? input.language;
  if (analysis.detectedGates.includes("CNOT") && analysis.detectedGates.includes("Hadamard (H)")) {
    return `This ${languageLabel} program prepares an entangling two-qubit resource state using Hadamard and CNOT operations.`;
  }
  if (analysis.hasMeasurement) {
    return `This ${languageLabel} program constructs a quantum circuit and extracts classical readouts or probability data.`;
  }
  if (input.gates.length > 0) {
    return `This ${languageLabel} program implements a ${input.numQubits}-qubit unitary circuit with ${input.gates.length} gate placement(s) in the synchronized simulator model.`;
  }
  return `This ${languageLabel} program defines quantum operations in source form; the simulator circuit may still be under construction.`;
}

function environmentMarkdown(language: EditorLanguageId): string {
  return languageDependencies(language).join(", ");
}

function architectureMarkdown(analysis: CodeAnalysis): string {
  return `${analysis.blocks.length} blocks; definitions: ${analysis.definitions.join("; ") || "none"}`;
}

function explanationMarkdown(analysis: CodeAnalysis): string {
  return analysis.blocks.map((block) => `Lines ${block.startLine}-${block.endLine}: ${block.summary}`).join("\n");
}

function circuitMarkdown(input: BuildCodeReportInput, circuitLabel: string): string {
  return `${circuitLabel}; initial |${input.initialBasisState}>`;
}

function circuitLatex(input: BuildCodeReportInput): string[] {
  return input.gates.length > 0 ? [compositeOperatorLatex(input.gates)] : [];
}

function mathMarkdown(input: BuildCodeReportInput): string {
  return input.gates.map((gate) => gate.gateType).join(" ");
}

function mathLatex(input: BuildCodeReportInput): string[] {
  const items: string[] = [];
  const seen = new Set<string>();
  for (const gate of input.gates) {
    const math = singleGateMatrixLatex(gate.gateType);
    if (!seen.has(math)) {
      seen.add(math);
      items.push(math);
    }
  }
  if (input.gates.length > 0) items.push(compositeOperatorLatex(input.gates));
  return items;
}

function evolutionMarkdown(input: BuildCodeReportInput): string {
  return `|psi_0> = |${input.initialBasisState}> then apply ${input.gates.length} gates.`;
}

function evolutionLatex(input: BuildCodeReportInput): string[] {
  return input.gates.length > 0 ? [`|\\psi_f\\rangle = U|\\psi_0\\rangle,\\quad U=${compositeOperatorLatex(input.gates)}`] : [];
}

function measurementMarkdown(input: BuildCodeReportInput, analysis: CodeAnalysis): string {
  return analysis.hasMeasurement ? "Measurement detected in source." : `Output: ${input.outputText || "none"}`;
}

function complexityMarkdown(input: BuildCodeReportInput): string {
  return `${input.numQubits} qubits, ${input.gates.length} gates.`;
}

function complexityLatex(input: BuildCodeReportInput): string[] {
  return [`n_{\\mathrm{qubits}}=${input.numQubits},\\quad n_{\\mathrm{gates}}=${input.gates.length}`];
}

function implementationMarkdown(input: BuildCodeReportInput, analysis: CodeAnalysis): string {
  return implementationNotes(input, analysis).join(" ");
}

function implementationNotes(input: BuildCodeReportInput, analysis: CodeAnalysis): string[] {
  const notes: string[] = [];
  if (input.language === "qiskit") notes.push("Qiskit builds circuits imperatively; gate order follows source execution order.");
  if (input.language === "pennylane") notes.push("PennyLane differentiates through QNodes; device choice affects simulation backend.");
  if (input.language === "qsharp") notes.push("Q# requires qubits to be reset before release; use MReset operations when measuring.");
  if (analysis.imports.length > 0) notes.push(`Imports: ${analysis.imports.join("; ")}`);
  return notes;
}

function executionMarkdown(input: BuildCodeReportInput): string {
  return `status=${input.outputState}; stdout=${input.outputText}; stderr=${input.errorText}`;
}

function limitationsMarkdown(input: BuildCodeReportInput, analysis: CodeAnalysis): string {
  return `execution=${input.outputState}; measurement=${analysis.hasMeasurement}`;
}

function reproducibilityMarkdown(input: BuildCodeReportInput): string {
  return `${input.language}; ${input.numQubits} qubits; ${input.gates.length} gates`;
}

function conclusionMarkdown(
  input: BuildCodeReportInput,
  _analysis: CodeAnalysis,
  circuitLabel: string,
  executionLabel: string,
): string {
  return `Circuit ${circuitLabel}; execution ${executionLabel}; language ${input.language}.`;
}

function blockExplanation(block: CodeBlock): string {
  switch (block.kind) {
    case "import":
      return "Imports external quantum SDK modules required by the program.";
    case "definition":
      return "Declares a callable quantum routine (function, QNode, or Q# operation).";
    case "gate":
      return "Applies one or more quantum gates to specified wires/qubits.";
    case "measurement":
      return "Performs a measurement, samples outcomes, or returns probability data.";
    case "output":
      return "Emits classical output for inspection in the editor output pane.";
    default:
      return "Supporting logic or configuration for the quantum program.";
  }
}

function singleGateMatrixLatex(gateType: GatePlacement["gateType"]): string {
  switch (gateType) {
    case "H":
      return String.raw`H=\frac{1}{\sqrt{2}}\begin{pmatrix}1&1\\1&-1\end{pmatrix}`;
    case "X":
      return String.raw`X=\begin{pmatrix}0&1\\1&0\end{pmatrix}`;
    case "Y":
      return String.raw`Y=\begin{pmatrix}0&-i\\ i&0\end{pmatrix}`;
    case "Z":
      return String.raw`Z=\begin{pmatrix}1&0\\0&-1\end{pmatrix}`;
    case "CNOT":
      return String.raw`\mathrm{CNOT}=\begin{pmatrix}1&0&0&0\\0&1&0&0\\0&0&0&1\\0&0&1&0\end{pmatrix}`;
    
    default:
      return `${gateMeta(gateType).label}`;
  }
}

function compositeOperatorLatex(gates: GatePlacement[]): string {
  if (gates.length === 0) return "U = I";
  const ordered = gates.slice().sort((a, b) => a.timeStep - b.timeStep);
  const factors = ordered.map((gate) => {
    if (gate.gateType === "CNOT") {
      return `\\mathrm{CNOT}_{${gate.qubitTargets[0]}\\rightarrow ${gate.qubitTargets[1]}}`;
    }
    const power = (gate.stackCount ?? 1) > 1 ? `^{${gate.stackCount}}` : "";
    return `${gate.gateType}_{q_{${gate.qubitTargets[0]}}}${power}`;
  });
  return `U = ${factors.join(" \\cdot ")}`;
}

export function codeReportHeaderSubtitle(input: BuildCodeReportInput): string {
  const languageLabel = EDITOR_LANGUAGES.find((item) => item.id === input.language)?.label ?? input.language;
  const executionLabel =
    input.outputState === "success"
      ? "Successful"
      : input.outputState === "error"
        ? "Failed"
        : input.outputState === "running"
          ? "Running"
          : "Not executed";
  return `Language: ${languageLabel} | Circuit: ${circuitSummaryLabel(input.numQubits, input.gates)} | Execution: ${executionLabel}`;
}

export function codeReportDocumentTitle(language: EditorLanguageId): string {
  return languageReportTitle(language);
}
