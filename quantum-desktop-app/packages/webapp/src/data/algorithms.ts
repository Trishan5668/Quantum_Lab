import type { GatePlacement } from "../types";

export interface AlgorithmPreset {
  id: string;
  name: string;
  category: "foundations" | "algorithms" | "advanced";
  qubits: number;
  summary: string;
  description: string;
  math: string;
  researchNotes: string;
  numQubits: number;
  gates: Omit<GatePlacement, "id">[];
  fidelityTarget?: "bell" | "ghz" | "zero" | "none";
}

export const ALGORITHMS: AlgorithmPreset[] = [
  {
    id: "bell-state",
    name: "Bell State",
    category: "foundations",
    qubits: 2,
    summary: "Maximally entangled two-qubit state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2.",
    description:
      "The Bell state is the canonical example of quantum entanglement. Apply H to qubit 0, then CNOT with control 0 and target 1. Measurement outcomes are perfectly correlated.",
    math: "|Φ⁺⟩ = (1/√2)(|00⟩ + |11⟩). Created by H ⊗ I followed by CNOT₀₁.",
    researchNotes:
      "Bell states are used in quantum teleportation, superdense coding, and entanglement verification. Fidelity to |Φ⁺⟩ is a standard benchmark.",
    numQubits: 2,
    fidelityTarget: "bell",
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 1 },
    ],
  },
  {
    id: "ghz",
    name: "GHZ State",
    category: "foundations",
    qubits: 3,
    summary: "Three-qubit entanglement: (|000⟩ + |111⟩)/√2.",
    description:
      "Greenberger–Horne–Zeilinger states generalize Bell states to three or more qubits. Build with H on q0, then CNOT chains.",
    math: "|GHZ⟩ = (1/√2)(|000⟩ + |111⟩).",
    researchNotes:
      "GHZ states violate Mermin-type Bell inequalities and are fragile under decoherence — useful for studying multipartite entanglement.",
    numQubits: 3,
    fidelityTarget: "ghz",
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 2], params: {}, timeStep: 2 },
    ],
  },
  {
    id: "teleportation",
    name: "Quantum Teleportation",
    category: "algorithms",
    qubits: 3,
    summary: "Transfer an unknown qubit state using entanglement and classical bits.",
    description:
      "Alice shares a Bell pair with Bob. She entangles her unknown qubit with her half of the pair, measures, and sends two classical bits. Bob applies corrective gates.",
    math: "Protocol uses Bell measurement basis and conditional X/Z corrections on Bob's qubit.",
    researchNotes:
      "Teleportation does not violate relativity — information still travels classically. Key primitive for quantum networks.",
    numQubits: 3,
    gates: [
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 0 },
      { gateType: "CNOT", qubitTargets: [1, 2], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
    ],
  },
  {
    id: "deutsch",
    name: "Deutsch Algorithm",
    category: "algorithms",
    qubits: 2,
    summary: "Determine if f:{0,1}→{0,1} is constant or balanced with one query.",
    description:
      "The first algorithm showing quantum parallelism advantage. Prepares superposition, applies oracle Uf, then interference reveals the answer.",
    math: "Uses phase kickback: |x⟩|y⟩ → |x⟩|y⊕f(x)⟩. Final H on input qubit yields deterministic outcome.",
    researchNotes:
      "Foundation for Deutsch–Jozsa, Simon, and Grover. Demonstrates query complexity separation.",
    numQubits: 2,
    gates: [
      { gateType: "X", qubitTargets: [1], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 1 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
    ],
  },
  {
    id: "deutsch-jozsa",
    name: "Deutsch–Jozsa",
    category: "algorithms",
    qubits: 3,
    summary: "Decide if a function is constant or balanced in one query (n=2).",
    description:
      "Generalizes Deutsch to n-bit functions. Quantum algorithm needs one query; classical needs up to 2^(n-1)+1.",
    math: "Prepare uniform superposition, apply oracle, apply H⊗ⁿ, measure — constant functions yield |0…0⟩.",
    researchNotes:
      "Early proof that quantum computers can be exponentially faster for specific promise problems.",
    numQubits: 3,
    gates: [
      { gateType: "X", qubitTargets: [2], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 1 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 1 },
      { gateType: "H", qubitTargets: [2], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 2], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 3 },
    ],
  },
  {
    id: "bernstein-vazirani",
    name: "Bernstein–Vazirani",
    category: "algorithms",
    qubits: 3,
    summary: "Find hidden bit string s in f(x) = s·x mod 2 with one query.",
    description:
      "Uses the same interference pattern as Deutsch–Jozsa to recover a hidden string encoded in a linear Boolean function.",
    math: "Oracle: |x⟩ → (-1)^(s·x)|x⟩. After H⊗ⁿ the measurement directly yields s.",
    researchNotes:
      "Precursor to Shor and important for understanding quantum query algorithms.",
    numQubits: 3,
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [2], params: {}, timeStep: 0 },
      { gateType: "Z", qubitTargets: [2], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 2], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 3 },
      { gateType: "H", qubitTargets: [2], params: {}, timeStep: 3 },
    ],
  },
  {
    id: "grover",
    name: "Grover Search",
    category: "algorithms",
    qubits: 2,
    summary: "Quadratic speedup for unstructured search over N items.",
    description:
      "Amplitude amplification rotates the state toward the marked item. One Grover iteration for 4 items (2 qubits) finds |11⟩ with high probability.",
    math: "Grover operator G = D·O where O flips marked state phase and D inverts about average.",
    researchNotes:
      "Optimal for unstructured search. Composes with QFT in algorithms like amplitude estimation.",
    numQubits: 2,
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 0 },
      { gateType: "Z", qubitTargets: [1], params: {}, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 3 },
    ],
  },
  {
    id: "qft",
    name: "Quantum Fourier Transform",
    category: "advanced",
    qubits: 3,
    summary: "Basis change to Fourier domain — core of Shor and phase estimation.",
    description:
      "Applies controlled rotations and Hadamards to map computational basis to Fourier basis. Educational 3-qubit demonstration.",
    math: "QFT|j⟩ = (1/√N) Σₖ e^(2πijk/N)|k⟩.",
    researchNotes:
      "Efficient QFT is O(n²) gates vs classical FFT O(n·2ⁿ). Enables period finding.",
    numQubits: 3,
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "RZ", qubitTargets: [1], params: { theta: Math.PI / 2 }, timeStep: 1 },
      { gateType: "CNOT", qubitTargets: [0, 1], params: {}, timeStep: 2 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 3 },
      { gateType: "RZ", qubitTargets: [2], params: { theta: Math.PI / 4 }, timeStep: 4 },
      { gateType: "CNOT", qubitTargets: [1, 2], params: {}, timeStep: 5 },
      { gateType: "H", qubitTargets: [2], params: {}, timeStep: 6 },
    ],
  },
  {
    id: "shor-educational",
    name: "Shor (Educational)",
    category: "advanced",
    qubits: 3,
    summary: "Conceptual period-finding circuit structure for factoring education.",
    description:
      "Full Shor requires many qubits; this educational preset shows superposition + modular arithmetic oracle structure for learning.",
    math: "Period r of f(x)=a^x mod N found via QFT on superposition register.",
    researchNotes:
      "Polynomial-time factoring threatens RSA. Hardware needs error correction for cryptographically relevant instances.",
    numQubits: 3,
    gates: [
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 0 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 0 },
      { gateType: "CNOT", qubitTargets: [0, 2], params: {}, timeStep: 1 },
      { gateType: "RZ", qubitTargets: [2], params: { theta: Math.PI / 3 }, timeStep: 2 },
      { gateType: "H", qubitTargets: [0], params: {}, timeStep: 3 },
      { gateType: "H", qubitTargets: [1], params: {}, timeStep: 3 },
    ],
  },
];

export function getAlgorithm(id: string): AlgorithmPreset | undefined {
  return ALGORITHMS.find((a) => a.id === id);
}
