import type {
  ComplexAmplitude,
  DensityMatrixData,
  GatePlacement,
  GateType,
  NoiseChannelType,
  StateSnapshot,
} from "../../types";

export interface Complex {
  re: number;
  im: number;
}

export type ComplexMatrix = Complex[][];

export interface AmplitudeRow {
  basis: string;
  amplitude: Complex;
  magnitude: number;
  probability: number;
  phase: number;
}

export interface MultiplicationCell {
  row: number;
  terms: string[];
  total: Complex;
}

export interface TensorBlock {
  row: number;
  col: number;
  scalar: Complex;
  block: ComplexMatrix;
}

export interface GateMath {
  label: string;
  symbol: string;
  localMatrix: ComplexMatrix;
  fullMatrix: ComplexMatrix;
  equation: string;
  derivation: string[];
  eigenvalues: string[];
  determinant: string;
  trace: string;
  unitarity: string;
  tensorFactors: string[];
  tensorBlocks: TensorBlock[];
}

export interface EvolutionStep {
  placement: GatePlacement;
  inputState: Complex[];
  outputState: Complex[];
  inputSnapshot: StateSnapshot;
  outputSnapshot: StateSnapshot;
  gate: GateMath;
  multiplication: MultiplicationCell[];
  explanation: string;
}

export interface MathematicsDerivation {
  numQubits: number;
  basisLabels: string[];
  initialState: StateSnapshot;
  steps: EvolutionStep[];
  finalState: StateSnapshot;
}

const ZERO: Complex = { re: 0, im: 0 };
const ONE: Complex = { re: 1, im: 0 };
const I: Complex = { re: 0, im: 1 };
const EPS = 1e-10;

export function buildDerivation(
  numQubits: number,
  gates: GatePlacement[],
  resultSteps?: { state_after?: StateSnapshot }[],
): MathematicsDerivation {
  const basisLabels = basisLabelsFor(numQubits);
  let state = zeroState(numQubits);
  const initialState = snapshotFromVector(numQubits, state);
  const ordered = [...gates].sort((a, b) => a.timeStep - b.timeStep || a.id.localeCompare(b.id));
  const steps = ordered.map((placement, index) => {
    const inputState = state;
    const inputSnapshot = snapshotFromVector(numQubits, inputState);
    const gate = gateMath(placement, numQubits);
    const computedOutput = matVec(gate.fullMatrix, inputState);
    const canonical = resultSteps?.[index]?.state_after;
    const outputState = canonical?.amplitudes?.length
      ? canonical.amplitudes.map(fromAmplitude)
      : computedOutput;
    const outputSnapshot = canonical ?? snapshotFromVector(numQubits, outputState);
    const multiplication = multiplicationCells(gate.fullMatrix, inputState);
    state = outputState;
    return {
      placement,
      inputState,
      outputState,
      inputSnapshot,
      outputSnapshot,
      gate,
      multiplication,
      explanation: gateExplanation(placement, inputSnapshot, outputSnapshot),
    };
  });

  return {
    numQubits,
    basisLabels,
    initialState,
    steps,
    finalState: steps.at(-1)?.outputSnapshot ?? initialState,
  };
}

export function basisLabelsFor(numQubits: number): string[] {
  return Array.from({ length: 1 << numQubits }, (_, i) => `|${i.toString(2).padStart(numQubits, "0")}>`);
}

export function zeroState(numQubits: number): Complex[] {
  return Array.from({ length: 1 << numQubits }, (_, i) => (i === 0 ? ONE : ZERO));
}

export function snapshotFromVector(numQubits: number, vector: Complex[]): StateSnapshot {
  return {
    num_qubits: numQubits,
    amplitudes: vector.map((a) => ({ real: clean(a.re), imag: clean(a.im) })),
    probabilities: vector.map((a) => clean(abs2(a))),
    basis_labels: basisLabelsFor(numQubits),
  };
}

export function amplitudeRows(snapshot: StateSnapshot): AmplitudeRow[] {
  return snapshot.basis_labels.map((basis, index) => {
    const amplitude = fromAmplitude(snapshot.amplitudes[index] ?? { real: 0, imag: 0 });
    const magnitude = magnitudeOf(amplitude);
    return {
      basis,
      amplitude,
      magnitude,
      probability: snapshot.probabilities[index] ?? abs2(amplitude),
      phase: magnitude < EPS ? 0 : Math.atan2(amplitude.im, amplitude.re),
    };
  });
}

export function densityFromState(snapshot: StateSnapshot): ComplexMatrix {
  const vector = snapshot.amplitudes.map(fromAmplitude);
  return vector.map((a) => vector.map((b) => mul(a, conjugate(b))));
}

export function densityFromData(data: DensityMatrixData): ComplexMatrix {
  return data.real.map((row, r) => row.map((value, c) => ({ re: value, im: data.imag[r]?.[c] ?? 0 })));
}

export function matrixToLatex(matrix: ComplexMatrix, maxDim = 8): string {
  if (matrix.length === 0) return "\\begin{pmatrix}\\end{pmatrix}";
  if (matrix.length > maxDim || matrix[0].length > maxDim) {
    return `\\text{${matrix.length}\\times ${matrix[0].length}\\ matrix}`;
  }
  return `\\begin{pmatrix}${matrix
    .map((row) => row.map((v) => complexToLatex(v)).join(" & "))
    .join(" \\\\ ")}\\end{pmatrix}`;
}

export function vectorToLatex(vector: Complex[], maxDim = 8): string {
  if (vector.length > maxDim) return `\\text{${vector.length}\\text{-entry vector}}`;
  return `\\begin{pmatrix}${vector.map((v) => complexToLatex(v)).join(" \\\\ ")}\\end{pmatrix}`;
}

export function complexToLatex(z: Complex): string {
  const re = clean(z.re);
  const im = clean(z.im);
  if (Math.abs(im) < EPS) return numberLatex(re);
  if (Math.abs(re) < EPS) return `${numberLatex(im)}i`;
  const sign = im >= 0 ? "+" : "-";
  return `${numberLatex(re)} ${sign} ${numberLatex(Math.abs(im))}i`;
}

export function complexToText(z: Complex): string {
  const re = clean(z.re);
  const im = clean(z.im);
  if (Math.abs(im) < EPS) return fmt(re);
  if (Math.abs(re) < EPS) return `${fmt(im)}i`;
  return `${fmt(re)} ${im >= 0 ? "+" : "-"} ${fmt(Math.abs(im))}i`;
}

export function noiseKrausLatex(channel: NoiseChannelType, p: number, t1Us: number, t2Us: number, gateTimeNs: number): string[] {
  const configuredP = `p=${fmt(p)}`;
  if (channel === "amplitude_damping") {
    return [
      configuredP,
      `K_0=\\begin{pmatrix}1&0\\\\0&\\sqrt{1-p}\\end{pmatrix}`,
      `K_1=\\begin{pmatrix}0&\\sqrt{p}\\\\0&0\\end{pmatrix}`,
    ];
  }
  if (channel === "phase_damping") {
    return [
      configuredP,
      `K_0=\\begin{pmatrix}1&0\\\\0&\\sqrt{1-p}\\end{pmatrix}`,
      `K_1=\\begin{pmatrix}0&0\\\\0&\\sqrt{p}\\end{pmatrix}`,
    ];
  }
  if (channel === "depolarizing") {
    return [
      configuredP,
      `K_0=\\sqrt{1-p}\\,I`,
      `K_1=\\sqrt{p/3}\\,X`,
      `K_2=\\sqrt{p/3}\\,Y`,
      `K_3=\\sqrt{p/3}\\,Z`,
    ];
  }
  if (channel === "bit_flip") return [configuredP, `K_0=\\sqrt{1-p}\\,I`, `K_1=\\sqrt{p}\\,X`];
  if (channel === "phase_flip") return [configuredP, `K_0=\\sqrt{1-p}\\,I`, `K_1=\\sqrt{p}\\,Z`];
  const tUs = gateTimeNs * 1e-3;
  const pAmp = 1 - Math.exp(-tUs / t1Us);
  const pPhase = 1 - Math.exp((-2 * tUs) / t2Us);
  return [
    `p_{T1}=1-e^{-t/T_1}=${fmt(pAmp)}`,
    `p_{T2}=1-e^{-2t/T_2}=${fmt(pPhase)}`,
    "\\mathcal{E}_{T1,T2}=\\mathcal{E}_{phase}\\circ\\mathcal{E}_{amplitude}",
  ];
}

function gateMath(placement: GatePlacement, numQubits: number): GateMath {
  const localMatrix = localGateMatrix(placement.gateType, placement.params.theta ?? Math.PI / 2);
  const fullMatrix =
    placement.gateType === "M"
      ? identity(1 << numQubits)
      : fullUnitary(localMatrix, placement.qubitTargets, numQubits);
  const symbol = gateSymbol(placement);
  return {
    label: gateLabel(placement),
    symbol,
    localMatrix,
    fullMatrix,
    equation: gateEquation(placement),
    derivation: gateDerivation(placement),
    eigenvalues: gateEigenvalues(placement),
    determinant: gateDeterminant(placement),
    trace: gateTrace(placement),
    unitarity: `${symbol}^{\\dagger}${symbol}=I`,
    tensorFactors: tensorFactors(placement, numQubits),
    tensorBlocks: placement.qubitTargets.length === 1 ? tensorBlocks(localMatrix, identity(2)) : [],
  };
}

function localGateMatrix(type: GateType, theta: number): ComplexMatrix {
  const c = Math.cos(theta / 2);
  const s = Math.sin(theta / 2);
  switch (type) {
    case "H":
      return scale([[ONE, ONE], [ONE, { re: -1, im: 0 }]], 1 / Math.sqrt(2));
    case "X":
      return [[ZERO, ONE], [ONE, ZERO]];
    case "Y":
      return [[ZERO, { re: 0, im: -1 }], [I, ZERO]];
    case "Z":
      return [[ONE, ZERO], [ZERO, { re: -1, im: 0 }]];
    case "RX":
      return [[{ re: c, im: 0 }, { re: 0, im: -s }], [{ re: 0, im: -s }, { re: c, im: 0 }]];
    case "RY":
      return [[{ re: c, im: 0 }, { re: -s, im: 0 }], [{ re: s, im: 0 }, { re: c, im: 0 }]];
    case "RZ":
      return [[{ re: c, im: -s }, ZERO], [ZERO, { re: c, im: s }]];
    case "CNOT":
      return [
        [ONE, ZERO, ZERO, ZERO],
        [ZERO, ONE, ZERO, ZERO],
        [ZERO, ZERO, ZERO, ONE],
        [ZERO, ZERO, ONE, ZERO],
      ];
    case "M":
      return identity(2);
  }
}

function fullUnitary(gate: ComplexMatrix, targets: number[], numQubits: number): ComplexMatrix {
  const dim = 1 << numQubits;
  const out = zeroMatrix(dim, dim);
  for (let col = 0; col < dim; col += 1) {
    const inputBits = bitsOf(col, numQubits);
    const targetCol = bitsToIndex(targets.map((q) => inputBits[q]));
    for (let targetRow = 0; targetRow < gate.length; targetRow += 1) {
      const amp = gate[targetRow]?.[targetCol] ?? ZERO;
      if (magnitudeOf(amp) < EPS) continue;
      const outputBits = [...inputBits];
      const targetBits = bitsOf(targetRow, targets.length);
      targets.forEach((q, i) => {
        outputBits[q] = targetBits[i];
      });
      out[bitsToIndex(outputBits)][col] = amp;
    }
  }
  return out;
}

function multiplicationCells(matrix: ComplexMatrix, vector: Complex[]): MultiplicationCell[] {
  return matrix.map((row, rowIndex) => {
    const products = row.map((value, col) => mul(value, vector[col] ?? ZERO));
    return {
      row: rowIndex,
      terms: row.map((value, col) => `${complexToText(value)}*${complexToText(vector[col] ?? ZERO)}`),
      total: products.reduce(add, ZERO),
    };
  });
}

function tensorBlocks(left: ComplexMatrix, right: ComplexMatrix): TensorBlock[] {
  return left.flatMap((row, r) =>
    row.map((scalar, c) => ({
      row: r,
      col: c,
      scalar,
      block: right.map((rightRow) => rightRow.map((value) => mul(scalar, value))),
    })),
  );
}

function tensorFactors(placement: GatePlacement, numQubits: number): string[] {
  if (placement.gateType === "M") return Array.from({ length: numQubits }, () => "I");
  if (placement.qubitTargets.length === 1) {
    return Array.from({ length: numQubits }, (_, q) => (q === placement.qubitTargets[0] ? gateSymbol(placement) : "I"));
  }
  if (numQubits === 2) return ["CNOT"];
  return [`CNOT_{q_${placement.qubitTargets[0]},q_${placement.qubitTargets[1]}}`, "embedded in full Hilbert space"];
}

function gateExplanation(placement: GatePlacement, input: StateSnapshot, output: StateSnapshot): string {
  if (placement.gateType === "CNOT") {
    return "CNOT reads basis bits in big-endian order. Rows for |10> and |11> exchange target-bit outcomes while |00> and |01> stay fixed when the control bit is 0.";
  }
  if (placement.gateType === "H") {
    return "Hadamard replaces a definite basis value with equal positive and negative paths, which is where interference begins.";
  }
  if (placement.gateType === "M") {
    return "Measurement is treated as a marker here, so the state is not collapsed; probabilities are computed with the Born rule.";
  }
  const changed = output.probabilities.some((p, i) => Math.abs(p - (input.probabilities[i] ?? 0)) > 1e-8);
  return changed
    ? `${gateLabel(placement)} redistributes amplitude across the computational basis according to its matrix rows.`
    : `${gateLabel(placement)} mainly changes phase here, so probabilities can remain the same while amplitudes rotate in the complex plane.`;
}

function gateEquation(placement: GatePlacement): string {
  const theta = placement.params.theta ?? Math.PI / 2;
  switch (placement.gateType) {
    case "RX":
      return `R_x(\\theta)=e^{-i\\theta X/2}=\\cos(\\theta/2)I-i\\sin(\\theta/2)X,\\quad \\theta=${fmt(theta)}`;
    case "RY":
      return `R_y(\\theta)=e^{-i\\theta Y/2}=\\cos(\\theta/2)I-i\\sin(\\theta/2)Y,\\quad \\theta=${fmt(theta)}`;
    case "RZ":
      return `R_z(\\theta)=e^{-i\\theta Z/2}=\\begin{pmatrix}e^{-i\\theta/2}&0\\\\0&e^{i\\theta/2}\\end{pmatrix},\\quad \\theta=${fmt(theta)}`;
    case "CNOT":
      return "\\mathrm{CNOT}|c,t\\rangle=|c,c\\oplus t\\rangle";
    case "M":
      return "P(i)=|a_i|^2";
    default:
      return `${gateSymbol(placement)}|\\psi\\rangle`;
  }
}

function gateDerivation(placement: GatePlacement): string[] {
  if (placement.gateType === "RX") return ["X^2=I", "e^{-i\\theta X/2}=\\sum_k(-i\\theta X/2)^k/k!", "even powers collect into cosine; odd powers collect into sine"];
  if (placement.gateType === "RY") return ["Y^2=I", "the same Pauli exponential identity applies", "real off-diagonal signs come from the entries of Y"];
  if (placement.gateType === "RZ") return ["Z is diagonal", "|0\\rangle gains e^{-i\\theta/2}", "|1\\rangle gains e^{i\\theta/2}"];
  if (placement.gateType === "CNOT") return ["Basis order is |00>, |01>, |10>, |11>", "control=0 leaves target unchanged", "control=1 swaps |10> and |11>"];
  if (placement.gateType === "M") return ["Measurement probabilities come from squared magnitudes", "the educational simulator keeps the state intact until sampling is requested"];
  return ["Write the input as a column vector", "embed the gate with tensor products", "multiply every row by the state vector"];
}

function gateEigenvalues(placement: GatePlacement): string[] {
  switch (placement.gateType) {
    case "H":
    case "X":
    case "Y":
    case "Z":
    case "CNOT":
      return ["+1", "-1"];
    case "RX":
      return ["e^{-i\\theta/2}", "e^{i\\theta/2}"];
    case "RY":
      return ["e^{-i\\theta/2}", "e^{i\\theta/2}"];
    case "RZ":
      return ["e^{-i\\theta/2}", "e^{i\\theta/2}"];
    case "M":
      return ["1"];
  }
}

function gateDeterminant(placement: GatePlacement): string {
  if (placement.gateType === "H" || placement.gateType === "X" || placement.gateType === "Y" || placement.gateType === "Z") return "-1";
  if (placement.gateType === "CNOT") return "-1";
  return "1";
}

function gateTrace(placement: GatePlacement): string {
  switch (placement.gateType) {
    case "H":
    case "X":
    case "Y":
    case "Z":
    case "CNOT":
      return "0";
    case "M":
      return "2";
    default:
      return "2\\cos(\\theta/2)";
  }
}

function gateLabel(placement: GatePlacement): string {
  return placement.gateType === "M" ? "Measurement" : placement.gateType;
}

function gateSymbol(placement: GatePlacement): string {
  return placement.gateType === "RX" ? "R_x" : placement.gateType === "RY" ? "R_y" : placement.gateType === "RZ" ? "R_z" : placement.gateType;
}

function identity(dim: number): ComplexMatrix {
  return Array.from({ length: dim }, (_, r) => Array.from({ length: dim }, (_, c) => (r === c ? ONE : ZERO)));
}

function zeroMatrix(rows: number, cols: number): ComplexMatrix {
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => ZERO));
}

function matVec(matrix: ComplexMatrix, vector: Complex[]): Complex[] {
  return matrix.map((row) => row.map((value, col) => mul(value, vector[col] ?? ZERO)).reduce(add, ZERO));
}

function bitsOf(index: number, width: number): number[] {
  return index.toString(2).padStart(width, "0").split("").map(Number);
}

function bitsToIndex(bits: number[]): number {
  return Number.parseInt(bits.join(""), 2);
}

function fromAmplitude(a: ComplexAmplitude): Complex {
  return { re: a.real, im: a.imag };
}

function add(a: Complex, b: Complex): Complex {
  return { re: a.re + b.re, im: a.im + b.im };
}

function mul(a: Complex, b: Complex): Complex {
  return { re: a.re * b.re - a.im * b.im, im: a.re * b.im + a.im * b.re };
}

function conjugate(a: Complex): Complex {
  return { re: a.re, im: -a.im };
}

function scale(matrix: ComplexMatrix, factor: number): ComplexMatrix {
  return matrix.map((row) => row.map((z) => ({ re: z.re * factor, im: z.im * factor })));
}

function abs2(a: Complex): number {
  return a.re * a.re + a.im * a.im;
}

function magnitudeOf(a: Complex): number {
  return Math.sqrt(abs2(a));
}

function numberLatex(v: number): string {
  if (Math.abs(v) < EPS) return "0";
  if (Math.abs(v - 1 / Math.sqrt(2)) < 1e-6) return "\\tfrac{1}{\\sqrt{2}}";
  if (Math.abs(v + 1 / Math.sqrt(2)) < 1e-6) return "-\\tfrac{1}{\\sqrt{2}}";
  if (Math.abs(v - 1) < EPS) return "1";
  if (Math.abs(v + 1) < EPS) return "-1";
  return fmt(v);
}

function clean(v: number): number {
  return Math.abs(v) < EPS ? 0 : v;
}

export function fmt(v: number): string {
  if (Math.abs(v) < EPS) return "0";
  return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}
