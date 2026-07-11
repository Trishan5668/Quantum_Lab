import type { ReactNode } from "react";
import { LatexBlock } from "../Mathematics/LatexBlock";
import { MatrixRenderer } from "../Mathematics/MatrixRenderer";
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
} from "../Mathematics/mathDerivations";
import type { ReportSection } from "../Reports/ReportReader";
import type { GatePlacement, MetricsResult, SimulationResultV2 } from "../../types";

const EPS = 1e-10;
const ZERO: Complex = { re: 0, im: 0 };
const ONE: Complex = { re: 1, im: 0 };

export function buildPhysicsReport({
  numQubits,
  gates,
  steps,
  resultsV2,
  metrics,
}: {
  numQubits: number;
  gates: GatePlacement[];
  steps?: Parameters<typeof buildDerivation>[2];
  resultsV2: SimulationResultV2 | null;
  metrics: MetricsResult | null;
}): ReportSection[] {
  const derivation = buildDerivation(numQubits, gates, steps);
  const dim = 1 << numQubits;
  const finalDensity = resultsV2?.final_density ? densityFromData(resultsV2.final_density) : densityFromState(derivation.finalState);
  const reduced = numQubits >= 2 ? reducedDensityFirstQubit(finalDensity, numQubits) : finalDensity;
  const bloch = reduced.length === 2 ? blochVector(reduced) : null;
  const purity = trace(matMul(finalDensity, finalDensity)).re;
  const reducedPurity = reduced.length === 2 ? trace(matMul(reduced, reduced)).re : purity;
  const totalUnitary = derivation.steps.reduce((acc, step) => matMul(step.gate.fullMatrix, acc), identity(dim));
  const finalByUnitary = matVec(totalUnitary, derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag })));
  const sections: ReportSection[] = [];
  const addSection = (title: string, subtitle: string, latex: string[], paragraphs: string[], render: () => JSX.Element, defaultOpen = false) => {
    const number = String(sections.length + 1);
    sections.push({
      id: `physics-${slug(title)}-${number}`,
      number,
      title,
      subtitle,
      latex,
      markdown: [...paragraphs, ...latex.map((equation) => `$$\n${equation}\n$$`)].join("\n\n"),
      searchText: [title, subtitle, ...paragraphs, ...latex].join(" "),
      defaultOpen,
      render,
    });
  };

  addSection(
    "Hilbert Space",
    `${numQubits} qubit${numQubits === 1 ? "" : "s"} occupy ${dim} basis directions`,
    [`\\dim\\mathcal{H} = 2^{${numQubits}}=${dim}`, `|\\psi\\rangle=\\sum_{x=0}^{${dim - 1}} a_x |x\\rangle,\\quad a_x\\in\\mathbb{C}`],
    [
      `This circuit has ${numQubits} qubit${numQubits === 1 ? "" : "s"}, so its wavefunction lives in a ${dim}-dimensional complex Hilbert space.`,
      "Complex amplitudes are used because phase is physically observable through interference, even when global phase is not.",
    ],
    () => (
      <TextbookBlock
        paragraphs={[
          `A classical register with ${numQubits} bits can be in one of ${dim} strings. A quantum register assigns a complex amplitude to every one of those strings at the same time.`,
          `The state vector therefore has ${dim} entries. Its length is not a storage accident; it is the coordinate list of one vector in a ${dim}-dimensional Hilbert space.`,
        ]}
        latex={[`\\mathcal{H}=(\\mathbb{C}^2)^{\\otimes ${numQubits}}`, `\\dim\\mathcal{H}=2^{${numQubits}}=${dim}`, stateExpansionLatex(derivation.finalState, 10)]}
      />
    ),
    true,
  );

  addSection(
    "Computational Basis",
    "orthonormal directions used by the simulator",
    basisLatex(numQubits).concat(["\\langle x|y\\rangle=\\delta_{xy}"]),
    ["The computational basis is the coordinate system in which QuantumLab displays amplitudes and probabilities."],
    () => (
      <TextbookBlock
        paragraphs={[
          "Each basis ket is a mutually exclusive physical readout of all wires. Orthogonality means two different bit strings can be perfectly distinguished by an ideal measurement.",
          "Normalization puts total probability mass equal to one, while orthogonality prevents probability assigned to one basis state from leaking into the label of another.",
        ]}
        latex={basisLatex(numQubits).concat(["\\langle 0\\cdots0|0\\cdots0\\rangle=1", "\\langle 0\\cdots0|1\\cdots1\\rangle=0"])}
      />
    ),
  );

  addSection(
    "Initial State",
    `prepared as |${"0".repeat(numQubits)}>`,
    [`|\\psi_0\\rangle=|${"0".repeat(numQubits)}\\rangle`, vectorToLatex(derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag })))],
    ["QuantumLab starts in the all-zero computational basis state, the standard cold-start state for circuit models."],
    () => (
      <TextbookBlock
        paragraphs={[
          "Physically, this says every qubit is initialized in the lower-energy or reference basis state before controlled operations are applied.",
          "The norm is one because the first amplitude has magnitude one and every other amplitude is zero.",
        ]}
        latex={[`|\\psi_0\\rangle=|${"0".repeat(numQubits)}\\rangle`, "\\langle\\psi_0|\\psi_0\\rangle=1", vectorToLatex(derivation.initialState.amplitudes.map((a) => ({ re: a.real, im: a.imag })))]}
      />
    ),
  );

  derivation.steps.forEach((step, index) => {
    const changed = changedAmplitudes(step.inputState, step.outputState, derivation.basisLabels);
    addSection(
      `Gate Physics: ${step.gate.label}`,
      `step ${index + 1}, time ${step.placement.timeStep}, q[${step.placement.qubitTargets.join(", ")}]`,
      [step.gate.equation, matrixToLatex(step.gate.localMatrix), matrixToLatex(step.gate.fullMatrix), ...rowExpansionLatex(step.gate.fullMatrix, step.inputState, 12)],
      [
        physicsForGate(step.placement, changed),
        `The actual simulation changes ${changed.length} displayed amplitudes above numerical tolerance.`,
      ],
      () => (
        <div className="space-y-3" data-gate-id={step.placement.id}>
          <TextbookBlock
            paragraphs={[
              physicsForGate(step.placement, changed),
              `Before this gate, the largest occupied basis component was ${dominantBasis(step.inputState, derivation.basisLabels)}. Afterward it is ${dominantBasis(step.outputState, derivation.basisLabels)}.`,
            ]}
            latex={[step.gate.equation, matrixToLatex(step.gate.localMatrix), stateTransitionLatex(step, derivation.basisLabels)]}
          />
          <PhysicsSubsection title="Tensor-product embedding">
            <p>Only the targeted qubit or qubits are directly driven. The identity factors represent qubits that are present in the joint Hilbert space but not acted on by the Hamiltonian pulse.</p>
            <LatexBlock math={`${step.gate.symbol}_{embedded}=${step.gate.tensorFactors.join("\\otimes")}`} compact />
            {step.placement.qubitTargets.length === 1 && (
              <LatexBlock math={"\\begin{pmatrix}a&b\\\\c&d\\end{pmatrix}\\otimes I=\\begin{pmatrix}aI&bI\\\\cI&dI\\end{pmatrix}"} compact />
            )}
            <MatrixRenderer matrix={step.gate.fullMatrix} rowLabels={derivation.basisLabels} colLabels={derivation.basisLabels} maxDim={8} />
          </PhysicsSubsection>
          <PhysicsSubsection title="Complete row-column action">
            <p>Each output amplitude is the coherent sum of row entries times input amplitudes. Nonzero terms are the physically active paths; zero entries are forbidden transitions for this gate.</p>
            {step.multiplication.slice(0, 16).map((cell) => (
              <LatexBlock
                key={cell.row}
                math={`a'_{${cell.row}}=${cell.terms.join("+").replace(/\*/g, "\\cdot ")}=${complexToLatex(cell.total)}`}
                compact
              />
            ))}
            {step.multiplication.length > 16 && <p className="text-xs text-text-muted">Rows 17-{step.multiplication.length} follow the same row-column rule; the panel limits visible rows to preserve responsiveness on large Hilbert spaces.</p>}
          </PhysicsSubsection>
          <PhysicsSubsection title="Physical interpretation">
            <AmplitudeChangeList changes={changed} />
          </PhysicsSubsection>
        </div>
      ),
    );
  });

  addSection(
    "Entanglement Analysis",
    numQubits >= 2 ? `first-qubit reduced purity ${fmt(reducedPurity)}` : "single-qubit states are not multipartite entangled",
    entanglementLatex(derivation.finalState, reduced, reducedPurity),
    ["The report tests separability by tracing out the rest of the register and checking whether the reduced state remains pure."],
    () => (
      <TextbookBlock
        paragraphs={[
          numQubits < 2
            ? "There is only one subsystem, so multipartite entanglement is not defined for this circuit."
            : reducedPurity < 1 - 1e-6
              ? "The first qubit cannot be assigned its own pure state after the rest of the register is ignored. That loss of purity is the operational signature of entanglement across this cut."
              : "The reduced state remains pure across the first-qubit cut, so the final pure state is separable across that cut.",
        ]}
        latex={entanglementLatex(derivation.finalState, reduced, reducedPurity)}
      />
    ),
  );

  addSection(
    "Circuit Unitary",
    "ordered product of every embedded gate",
    [`U_{total}=G_${derivation.steps.length}\\cdots G_2G_1`, matrixToLatex(totalUnitary), `U_{total}|\\psi_0\\rangle=${vectorToLatex(finalByUnitary)}`],
    ["Because every non-measurement gate is unitary, the complete circuit is the product of the embedded gate operators in time order."],
    () => (
      <div className="space-y-3">
        <TextbookBlock
          paragraphs={["The rightmost gate acts first. Multiplying the full embedded matrices gives the single operator that maps the prepared state to the final wavefunction."]}
          latex={[`U_{total}=G_${derivation.steps.length}\\cdots G_2G_1`, matrixToLatex(totalUnitary), `|\\psi_f\\rangle=U_{total}|\\psi_0\\rangle=${vectorToLatex(finalByUnitary)}`]}
        />
        <MatrixRenderer matrix={totalUnitary} rowLabels={derivation.basisLabels} colLabels={derivation.basisLabels} maxDim={8} />
      </div>
    ),
  );

  addSection(
    "Density Matrix and Coherence",
    `purity Tr(rho^2) = ${fmt(purity)}`,
    [`\\rho=|\\psi\\rangle\\langle\\psi|`, matrixToLatex(finalDensity), `\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`],
    ["The density matrix stores probabilities on the diagonal and phase coherence in the off-diagonal entries."],
    () => (
      <div className="space-y-3">
        <TextbookBlock
          paragraphs={[
            "The outer product multiplies each final amplitude by the conjugate of each other final amplitude. Diagonal entries are measurement probabilities; off-diagonal entries measure coherent phase relationships.",
            resultsV2?.final_density ? "This circuit is using density-mode data from the simulator." : "This density matrix is derived deterministically from the final statevector.",
          ]}
          latex={[`\\rho_{ij}=a_i a_j^*`, matrixToLatex(finalDensity), `\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`]}
        />
        <MatrixRenderer matrix={finalDensity} rowLabels={derivation.basisLabels} colLabels={derivation.basisLabels} maxDim={8} />
      </div>
    ),
  );

  if (numQubits >= 2) {
    addSection(
      "Reduced Density Matrix",
      "partial trace over unobserved qubits",
      [`\\rho_A=\\mathrm{Tr}_B(\\rho)`, partialTraceLatex(finalDensity, numQubits), matrixToLatex(reduced)],
      ["Tracing out a subsystem means summing over degrees of freedom that are not observed."],
      () => (
        <div className="space-y-3">
          <TextbookBlock
            paragraphs={[
              "If you only inspect q[0], the remaining wires become unobserved information. The partial trace adds all compatible environmental basis labels, producing the state accessible to q[0] alone.",
              `The resulting first-qubit purity is ${fmt(reducedPurity)}.`,
            ]}
            latex={[`(\\rho_A)_{ij}=\\sum_b \\rho_{ib,jb}`, matrixToLatex(reduced), `\\mathrm{Tr}(\\rho_A^2)=${fmt(reducedPurity)}`]}
          />
          <MatrixRenderer matrix={reduced} rowLabels={["|0>", "|1>"]} colLabels={["|0>", "|1>"]} maxDim={2} />
        </div>
      ),
    );
  }

  addSection(
    "Measurement",
    "Born-rule probabilities without collapse",
    measurementLatex(derivation.finalState),
    ["QuantumLab computes measurement probabilities from the final amplitudes. It does not collapse the wavefunction until an actual measurement sample is requested."],
    () => (
      <div className="space-y-3">
        <TextbookBlock
          paragraphs={[
            "The Born rule converts complex amplitude into observable frequency. Phase influences probabilities indirectly through previous interference, then the final probability is the squared magnitude.",
            "This simulator reports the distribution; it keeps the state available for explanation instead of replacing it with one sampled outcome.",
          ]}
          latex={measurementLatex(derivation.finalState)}
        />
        <AmplitudeProbabilityTable snapshot={derivation.finalState} />
      </div>
    ),
  );

  if (bloch) {
    addSection(
      "Bloch Sphere",
      `first-qubit vector (${fmt(bloch.x)}, ${fmt(bloch.y)}, ${fmt(bloch.z)})`,
      [`x=2\\mathrm{Re}(\\rho_{01})=${fmt(bloch.x)}`, `y=-2\\mathrm{Im}(\\rho_{01})=${fmt(bloch.y)}`, `z=\\rho_{00}-\\rho_{11}=${fmt(bloch.z)}`, `|\\vec r|=${fmt(bloch.length)}`],
      ["A one-qubit density matrix maps to a point inside the Bloch sphere."],
      () => (
        <TextbookBlock
          paragraphs={[
            `The first qubit's reduced state has Bloch-vector length ${fmt(bloch.length)}. A length near one means a pure local state; a shorter vector means information about that qubit is shared with other qubits or noise.`,
          ]}
          latex={[`\\rho=\\frac{1}{2}(I+xX+yY+zZ)`, `x=${fmt(bloch.x)},\\quad y=${fmt(bloch.y)},\\quad z=${fmt(bloch.z)}`, `|\\vec r|=${fmt(bloch.length)}`]}
        />
      ),
    );
  }

  addSection(
    "Eigenvalues and Symmetry",
    "unitary spectra lie on the unit circle",
    derivation.steps.flatMap((step, index) => [`G_${index + 1}^{\\dagger}G_${index + 1}=I`, `\\lambda(${step.gate.symbol})\\in\\{${step.gate.eigenvalues.join(", ")}\\}`]),
    ["Unitary evolution preserves norm, so its eigenvalues can only rotate phase and must have magnitude one."],
    () => (
      <TextbookBlock
        paragraphs={[
          "Hermitian gates correspond to observables or involutive flips when their eigenvalues are real. Rotation gates are generated by Hermitian Pauli operators through exponentiation.",
          "Normality ensures the gate has an orthogonal eigenbasis, which is why spectral interpretation is physically meaningful.",
        ]}
        latex={derivation.steps.flatMap((step, index) => [`G_${index + 1}^{\\dagger}G_${index + 1}=I`, `|\\lambda|=1`, `\\lambda(${step.gate.symbol})\\in\\{${step.gate.eigenvalues.join(", ")}\\}`])}
      />
    ),
  );

  addSection(
    "Quantum Information",
    "metrics meaningful for this run",
    informationLatex(metrics, purity, reducedPurity),
    ["Information measures are shown only when they correspond to simulator data for the current circuit."],
    () => (
      <TextbookBlock
        paragraphs={[
          `Global purity is ${fmt(purity)}.`,
          numQubits >= 2 ? `First-qubit reduced purity is ${fmt(reducedPurity)}, so entanglement entropy is meaningful for this bipartition.` : "Entropy and mutual information need a subsystem split, so they are omitted for a one-qubit circuit.",
        ]}
        latex={informationLatex(metrics, purity, reducedPurity)}
      />
    ),
  );

  addSection(
    "Research Notes",
    classifyCircuit(derivation.finalState, gates, reducedPurity),
    [stateExpansionLatex(derivation.finalState, 12)],
    ["The final note classifies the observed physics from the actual final amplitudes and gate sequence."],
    () => (
      <TextbookBlock
        paragraphs={[
          `This circuit demonstrates ${classifyCircuit(derivation.finalState, gates, reducedPurity)}.`,
          researchInterpretation(derivation.finalState, gates, reducedPurity),
        ]}
        latex={[stateExpansionLatex(derivation.finalState, 12)]}
      />
    ),
  );

  return sections;
}

function TextbookBlock({ paragraphs, latex }: { paragraphs: string[]; latex: string[] }): JSX.Element {
  return (
    <div className="physics-textbook-block">
      {paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
      {latex.map((math) => (
        <LatexBlock key={math} math={math} compact />
      ))}
    </div>
  );
}

function PhysicsSubsection({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <div className="physics-subsection">
      <h4>{title}</h4>
      {children}
    </div>
  );
}

function AmplitudeChangeList({ changes }: { changes: ReturnType<typeof changedAmplitudes> }): JSX.Element {
  if (changes.length === 0) return <p className="text-xs text-text-secondary">No displayed amplitude changed above tolerance; the gate acted as a symmetry for this input state.</p>;
  return (
    <ul className="grid gap-1 text-xs leading-5 text-text-secondary">
      {changes.slice(0, 12).map((change) => (
        <li key={change.basis} data-amplitude-basis={change.basis}>
          {change.basis}: {change.before} becomes {change.after}; probability changes from {change.pBefore} to {change.pAfter}.
        </li>
      ))}
    </ul>
  );
}

function AmplitudeProbabilityTable({ snapshot }: { snapshot: ReturnType<typeof buildDerivation>["finalState"] }): JSX.Element {
  return (
    <div className="math-matrix-wrap">
      <table className="math-matrix">
        <thead>
          <tr><th>Basis</th><th>Amplitude</th><th>Probability</th></tr>
        </thead>
        <tbody>
          {amplitudeRows(snapshot).map((row) => (
            <tr key={row.basis}><th>{row.basis}</th><td>{complexToText(row.amplitude)}</td><td>{fmt(row.probability)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function basisLatex(numQubits: number): string[] {
  const dim = 1 << numQubits;
  const labels = Array.from({ length: Math.min(dim, 8) }, (_, i) => `|${i.toString(2).padStart(numQubits, "0")}\\rangle`);
  return [`\\mathcal{B}=\\{${labels.join(", ")}${dim > 8 ? ",\\ldots" : ""}\\}`];
}

function stateExpansionLatex(snapshot: ReturnType<typeof buildDerivation>["finalState"], maxTerms: number): string {
  const terms = snapshot.amplitudes
    .map((amp, i) => ({ amp: { re: amp.real, im: amp.imag }, label: snapshot.basis_labels[i] }))
    .filter(({ amp }) => mag2(amp) > EPS)
    .slice(0, maxTerms)
    .map(({ amp, label }) => `${complexToLatex(amp)}${label.replace(">", "\\rangle").replace("|", "|")}`);
  return `|\\psi\\rangle=${terms.length ? terms.join("+") : "0"}${terms.length === maxTerms ? "+\\cdots" : ""}`;
}

function stateTransitionLatex(step: ReturnType<typeof buildDerivation>["steps"][number], labels: string[]): string {
  const before = step.inputState.map((amp, i) => `${complexToLatex(amp)}${labels[i].replace(">", "\\rangle")}`).filter((term) => !term.startsWith("0"));
  const after = step.outputState.map((amp, i) => `${complexToLatex(amp)}${labels[i].replace(">", "\\rangle")}`).filter((term) => !term.startsWith("0"));
  return `${step.gate.symbol}:\\quad ${before.join("+") || "0"}\\mapsto ${after.join("+") || "0"}`;
}

function physicsForGate(gate: GatePlacement, changes: ReturnType<typeof changedAmplitudes>): string {
  const target = `q[${gate.qubitTargets.join(", ")}]`;
  const changedText = changes.length ? ` In this run, ${changes[0].basis} changes from ${changes[0].before} to ${changes[0].after}.` : "";
  switch (gate.gateType) {
    case "H":
      return `Hadamard drives ${target} into a balanced pair of paths. Physically it changes which basis is sharp: computational certainty turns into phase-sensitive alternatives that can later interfere.${changedText}`;
    case "X":
      return `Pauli X is a pi rotation around the Bloch-sphere x axis on ${target}. In the spin picture it flips the north and south poles, so basis labels with the target bit 0 and 1 exchange amplitudes.${changedText}`;
    case "Y":
      return `Pauli Y is a pi rotation around the y axis with imaginary signs. The i factors encode a relative phase, so a flip through Y is not merely a classical bit swap.${changedText}`;
    case "Z":
      return `Pauli Z leaves computational populations fixed but reverses the phase of the |1> component on ${target}. That phase is invisible immediately but becomes observable through later interference.${changedText}`;
    case "RX":
      return `RX is generated by the Pauli X Hamiltonian: the exponential appears because continuous time evolution is unitary flow generated by a Hermitian operator.${changedText}`;
    case "RY":
      return `RY rotates the qubit through real superpositions around the y axis. It changes population continuously because the rotation axis is perpendicular to the measurement z axis.${changedText}`;
    case "RZ":
      return `RZ is phase evolution around the z axis. It changes relative phase between |0> and |1> components while preserving computational-basis probabilities.${changedText}`;
    case "CNOT":
      return `CNOT is conditional dynamics: the target evolves only on branches where the control bit is 1. If the control is in superposition, conditional evolution correlates branches and can create entanglement.${changedText}`;
    case "M":
      return `Measurement is represented as a non-collapsing marker here. It asks what the Born probabilities would be while preserving the explanatory statevector.${changedText}`;
  }
}

function changedAmplitudes(input: Complex[], output: Complex[], labels: string[]) {
  return output
    .map((after, i) => {
      const before = input[i] ?? ZERO;
      return {
        basis: labels[i],
        before: complexToText(before),
        after: complexToText(after),
        pBefore: fmt(mag2(before)),
        pAfter: fmt(mag2(after)),
        delta: mag2(sub(after, before)),
      };
    })
    .filter((row) => row.delta > 1e-8);
}

function dominantBasis(vector: Complex[], labels: string[]): string {
  let best = 0;
  vector.forEach((amp, i) => {
    if (mag2(amp) > mag2(vector[best] ?? ZERO)) best = i;
  });
  return `${labels[best]} with amplitude ${complexToText(vector[best] ?? ZERO)}`;
}

function rowExpansionLatex(matrix: ComplexMatrix, vector: Complex[], maxRows: number): string[] {
  return matrix.slice(0, maxRows).map((row, r) => {
    const terms = row.map((value, c) => `${complexToLatex(value)}\\cdot ${complexToLatex(vector[c] ?? ZERO)}`);
    return `a'_{${r}}=${terms.join("+")}=${complexToLatex(row.map((value, c) => mul(value, vector[c] ?? ZERO)).reduce(add, ZERO))}`;
  });
}

function entanglementLatex(snapshot: ReturnType<typeof buildDerivation>["finalState"], reduced: ComplexMatrix, reducedPurity: number): string[] {
  if (snapshot.num_qubits < 2) return ["\\text{multipartite entanglement: not defined for one qubit}"];
  return [
    "|\\psi\\rangle=(a|0\\rangle+b|1\\rangle)\\otimes|\\phi\\rangle\\quad\\text{would imply}\\quad \\mathrm{Tr}(\\rho_A^2)=1",
    matrixToLatex(reduced),
    `\\mathrm{Tr}(\\rho_A^2)=${fmt(reducedPurity)}`,
    reducedPurity < 1 - 1e-6 ? "\\mathrm{Tr}(\\rho_A^2)<1\\Rightarrow\\text{entangled across this cut}" : "\\mathrm{Tr}(\\rho_A^2)=1\\Rightarrow\\text{separable across this cut}",
  ];
}

function measurementLatex(snapshot: ReturnType<typeof buildDerivation>["finalState"]): string[] {
  return amplitudeRows(snapshot).slice(0, 16).map((row) => `P(${row.basis.replace(/[|>]/g, "")})=|${complexToLatex(row.amplitude)}|^2=${fmt(row.probability)}`);
}

function partialTraceLatex(matrix: ComplexMatrix, numQubits: number): string {
  const restDim = 1 << (numQubits - 1);
  const terms = [0, 1].flatMap((i) =>
    [0, 1].map((j) => {
      const sum = Array.from({ length: restDim }, (_, b) => {
        const row = (i << (numQubits - 1)) + b;
        const col = (j << (numQubits - 1)) + b;
        return complexToLatex(matrix[row]?.[col] ?? ZERO);
      }).join("+");
      return `(\\rho_A)_{${i}${j}}=${sum}`;
    }),
  );
  return terms.join(",\\quad ");
}

function informationLatex(metrics: MetricsResult | null, purity: number, reducedPurity: number): string[] {
  const equations = [`\\mathrm{Tr}(\\rho^2)=${fmt(purity)}`];
  if (Number.isFinite(reducedPurity)) equations.push(`\\mathrm{Tr}(\\rho_A^2)=${fmt(reducedPurity)}`);
  if (metrics?.entropy) equations.push(`S(\\rho_A)=${fmt(metrics.entropy.entropy)}`);
  if (metrics?.fidelity) equations.push(`F=${fmt(metrics.fidelity.fidelity)}`);
  return equations;
}

function classifyCircuit(snapshot: ReturnType<typeof buildDerivation>["finalState"], gates: GatePlacement[], reducedPurity: number): string {
  const active = snapshot.probabilities.filter((p) => p > 1e-6).length;
  if (snapshot.num_qubits >= 2 && reducedPurity < 1 - 1e-6) {
    if (active === 2 && gates.some((g) => g.gateType === "H") && gates.some((g) => g.gateType === "CNOT")) return "a Bell-type entangling primitive";
    if (active === 2 && snapshot.num_qubits >= 3) return "a GHZ-like entangled branch structure";
    return "multipartite correlation generated by conditional unitary evolution";
  }
  if (gates.some((g) => g.gateType === "H") && active > 1) return "single-particle superposition and interference readiness";
  if (gates.some((g) => ["RZ", "Z"].includes(g.gateType))) return "relative phase control";
  return "deterministic basis-state transport";
}

function researchInterpretation(snapshot: ReturnType<typeof buildDerivation>["finalState"], gates: GatePlacement[], reducedPurity: number): string {
  const activeRows = amplitudeRows(snapshot).filter((row) => row.probability > 1e-6);
  const support = activeRows.map((row) => `${row.basis} with probability ${fmt(row.probability)}`).join(", ");
  return `The final support is ${support || "empty above tolerance"}. ${gates.length} gate${gates.length === 1 ? "" : "s"} produced this distribution, and the first-qubit reduced purity is ${fmt(reducedPurity)}.`;
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

function matVec(matrix: ComplexMatrix, vector: Complex[]): Complex[] {
  return matrix.map((row) => row.map((value, col) => mul(value, vector[col] ?? ZERO)).reduce(add, ZERO));
}

function identity(dim: number): ComplexMatrix {
  return Array.from({ length: dim }, (_, r) => Array.from({ length: dim }, (_, c) => (r === c ? ONE : ZERO)));
}

function trace(matrix: ComplexMatrix): Complex {
  return matrix.map((row, i) => row[i] ?? ZERO).reduce(add, ZERO);
}

function add(a: Complex, b: Complex): Complex {
  return { re: clean(a.re + b.re), im: clean(a.im + b.im) };
}

function sub(a: Complex, b: Complex): Complex {
  return { re: a.re - b.re, im: a.im - b.im };
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
