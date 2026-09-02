import type { EditorLanguageId } from "../../store/editorStore";
import type { GatePlacement } from "../../types";

export interface CodeBlock {
  startLine: number;
  endLine: number;
  text: string;
  kind: "import" | "definition" | "gate" | "measurement" | "output" | "other";
  summary: string;
}

export interface CodeAnalysis {
  language: EditorLanguageId;
  lineCount: number;
  imports: string[];
  definitions: string[];
  detectedGates: string[];
  hasMeasurement: boolean;
  hasDevice: boolean;
  hasQnode: boolean;
  hasEntryPoint: boolean;
  blocks: CodeBlock[];
}

const MEASUREMENT_PATTERNS = [
  /\bmeasure\s*\(/i,
  /\bMReset/i,
  /\bM\s*\(/,
  /\bprobs\s*\(/i,
  /\bsample\s*\(/i,
  /\bcounts\s*\(/i,
  /\bexpval\s*\(/i,
  /\bexpectation/i,
];

const GATE_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /\.h\s*\(|Hadamard|qml\.H\b|\bH\s*\(/i, label: "Hadamard (H)" },
  { pattern: /\.cx\s*\(|CNOT|qml\.CNOT|Controlled/i, label: "CNOT" },
  { pattern: /\.x\s*\(|qml\.PauliX|qml\.X\b/i, label: "Pauli-X" },
  { pattern: /\.y\s*\(|qml\.PauliY|qml\.Y\b/i, label: "Pauli-Y" },
  { pattern: /\.z\s*\(|qml\.PauliZ|qml\.Z\b/i, label: "Pauli-Z" },
  { pattern: /\.rz\s*\(|qml\.RZ/i, label: "RZ rotation" },
  { pattern: /\.ry\s*\(|qml\.RY/i, label: "RY rotation" },
  { pattern: /\.rx\s*\(|qml\.RX/i, label: "RX rotation" },
  { pattern: /SWAP|qml\.SWAP/i, label: "SWAP" },
];

export function analyzeCode(code: string, language: EditorLanguageId): CodeAnalysis {
  const lines = code.split(/\r?\n/);
  const imports: string[] = [];
  const definitions: string[] = [];
  const detectedGates = new Set<string>();
  let hasMeasurement = false;
  let hasDevice = false;
  let hasQnode = false;
  let hasEntryPoint = false;

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("//")) return;

    if (/^(import|from)\s+/.test(trimmed)) imports.push(trimmed);
    if (/^(def |@qml\.qnode|operation |function )/.test(trimmed)) definitions.push(trimmed);
    if (/device\s*\(|qml\.device/i.test(trimmed)) hasDevice = true;
    if (/@qml\.qnode/.test(trimmed)) hasQnode = true;
    if (/@EntryPoint/.test(trimmed)) hasEntryPoint = true;
    if (MEASUREMENT_PATTERNS.some((pattern) => pattern.test(trimmed))) hasMeasurement = true;

    for (const gate of GATE_PATTERNS) {
      if (gate.pattern.test(trimmed)) detectedGates.add(gate.label);
    }
  });

  const blocks = buildBlocks(lines);

  return {
    language,
    lineCount: lines.length,
    imports,
    definitions,
    detectedGates: [...detectedGates],
    hasMeasurement,
    hasDevice,
    hasQnode,
    hasEntryPoint,
    blocks,
  };
}

function buildBlocks(lines: string[]): CodeBlock[] {
  const blocks: CodeBlock[] = [];
  let start = 0;
  let buffer: string[] = [];

  const flush = (end: number) => {
    if (buffer.length === 0) return;
    const text = buffer.join("\n");
    blocks.push({
      startLine: start + 1,
      endLine: end,
      text,
      kind: classifyBlock(text),
      summary: summarizeBlock(text),
    });
    buffer = [];
  };

  lines.forEach((line, index) => {
    if (line.trim() === "" && buffer.length > 0) {
      flush(index);
      return;
    }
    if (buffer.length === 0) start = index;
    buffer.push(line);
  });
  if (buffer.length > 0) flush(lines.length);
  return blocks;
}

function classifyBlock(text: string): CodeBlock["kind"] {
  if (/^(import|from)\s+/m.test(text)) return "import";
  if (/^(def |@qml\.qnode|operation |function )/m.test(text)) return "definition";
  if (MEASUREMENT_PATTERNS.some((pattern) => pattern.test(text))) return "measurement";
  if (GATE_PATTERNS.some((gate) => gate.pattern.test(text))) return "gate";
  if (/\bprint\s*\(/.test(text)) return "output";
  return "other";
}

function summarizeBlock(text: string): string {
  const first = text.split("\n").find((line) => line.trim())?.trim() ?? "";
  if (first.length > 72) return `${first.slice(0, 69)}...`;
  return first;
}

export function circuitSummaryLabel(numQubits: number, gates: GatePlacement[]): string {
  if (gates.length === 0) return `${numQubits} qubit${numQubits === 1 ? "" : "s"} | no gates`;
  const sequence = gates
    .slice()
    .sort((a, b) => a.timeStep - b.timeStep)
    .map((gate) => gate.gateType)
    .join(" → ");
  return `${numQubits} qubit${numQubits === 1 ? "" : "s"} | ${sequence}`;
}

export function languageDependencies(language: EditorLanguageId): string[] {
  switch (language) {
    case "qiskit":
      return ["Python 3.11+", "qiskit"];
    case "pennylane":
      return ["Python 3.11+", "pennylane", "numpy"];
    case "qsharp":
      return ["Microsoft QDK (qdk)", "Q# language runtime"];
    default:
      return [];
  }
}

export function languageReportTitle(language: EditorLanguageId): string {
  switch (language) {
    case "qiskit":
      return "Qiskit Program Documentation";
    case "pennylane":
      return "PennyLane Program Documentation";
    case "qsharp":
      return "Q# Program Documentation";
    default:
      return "Quantum Program Documentation";
  }
}
