export interface ResearchTopic {
  slug: string;
  title: string;
  summary: string;
  content: string;
  references: string[];
}

export const RESEARCH_TOPICS: ResearchTopic[] = [
  {
    slug: "noise",
    title: "Quantum Noise",
    summary: "Decoherence channels and their Kraus operator representations.",
    content: `Real hardware couples qubits to the environment. QuantumLab models common channels:

- **Amplitude damping** — T1 energy relaxation
- **Phase damping** — T2 dephasing
- **Depolarizing** — uniform Pauli errors
- **Bit / phase flip** — discrete error models

Apply noise to evolve density matrices and track purity loss.`,
    references: [
      "Nielsen & Chuang, Quantum Computation and Quantum Information, Ch. 8",
      "Preskill, Quantum Information Theory lecture notes",
    ],
  },
  {
    slug: "tomography",
    title: "Quantum State Tomography",
    summary: "Reconstructing ρ from measurement statistics.",
    content: `State tomography estimates the density matrix from repeated measurements in different bases.

For n qubits, exhaustive tomography requires 3ⁿ − 1 independent parameters. QuantumLab's density visualization helps validate reconstructed states against theoretical targets.`,
    references: [
      "Paris & Řeháček, Quantum State Estimation",
      "Blume-Kohout, Optimal, reliable estimation of quantum states",
    ],
  },
  {
    slug: "density-matrices",
    title: "Density Matrix Formalism",
    summary: "Reduced states, partial trace, and entanglement entropy.",
    content: `The reduced density matrix ρ_A = Tr_B(ρ_AB) describes a subsystem.

**Entanglement entropy** S(ρ_A) = −Tr(ρ_A log₂ ρ_A) quantifies bipartite entanglement.

Use the Metrics panel to compute entropy and fidelity against reference states.`,
    references: [
      "Nielsen & Chuang, Ch. 11",
      "quantum-education-content/density-matrices.md",
    ],
  },
  {
    slug: "error-correction",
    title: "Quantum Error Correction",
    summary: "Protecting logical qubits from physical noise.",
    content: `QEC encodes logical information across many physical qubits. The threshold theorem shows that if physical error rates are below a threshold, arbitrarily long computations are possible.

QuantumLab's noise models help build intuition for how error rates degrade fidelity before introducing full stabilizer codes.`,
    references: [
      "Shor, Fault-tolerant quantum computation",
      "Gottesman, Stabilizer codes and quantum error correction",
    ],
  },
  {
    slug: "hardware",
    title: "Quantum Hardware",
    summary: "Superconducting, trapped-ion, and photonic platforms.",
    content: `Leading platforms:

- **Superconducting** (IBM, Google) — fast gates, cryogenic
- **Trapped ions** (IonQ, Quantinuum) — high fidelity, slower gates
- **Photonic** (Xanadu, PsiQuantum) — room temperature, measurement-based

T1/T2 noise presets in QuantumLab approximate realistic decoherence timescales.`,
    references: [
      "IBM Quantum Documentation",
      "Preskill, NISQ era and beyond",
    ],
  },
];

export function getResearchTopic(slug: string): ResearchTopic | undefined {
  return RESEARCH_TOPICS.find((t) => t.slug === slug);
}
