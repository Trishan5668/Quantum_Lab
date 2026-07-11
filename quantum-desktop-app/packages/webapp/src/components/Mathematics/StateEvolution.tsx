import { AmplitudeTable } from "./AmplitudeTable";
import { LatexBlock } from "./LatexBlock";
import { MatrixMultiplication } from "./MatrixMultiplication";
import type { EvolutionStep } from "./mathDerivations";
import { matrixToLatex, vectorToLatex } from "./mathDerivations";

interface StateEvolutionProps {
  step: EvolutionStep;
  basisLabels: string[];
  level: "beginner" | "intermediate" | "advanced" | "research";
}

export function StateEvolution({ step, basisLabels, level }: StateEvolutionProps): JSX.Element {
  return (
    <div className="space-y-3">
      <div className="grid gap-2">
        <LatexBlock label="Input state" math={`|\\psi_{in}\\rangle=${vectorToLatex(step.inputState)}`} compact />
        <LatexBlock
          label="Operation"
          math={`|\\psi_{out}\\rangle=${step.gate.symbol}_{full}|\\psi_{in}\\rangle=${matrixToLatex(step.gate.fullMatrix)}${vectorToLatex(step.inputState)}`}
          compact
        />
        <LatexBlock label="Output state" math={`|\\psi_{out}\\rangle=${vectorToLatex(step.outputState)}`} compact />
      </div>
      {(level === "advanced" || level === "research") && (
        <MatrixMultiplication cells={step.multiplication} basisLabels={basisLabels} />
      )}
      <p className="text-xs leading-5 text-text-secondary">{step.explanation}</p>
      {level !== "beginner" && <AmplitudeTable snapshot={step.outputSnapshot} />}
    </div>
  );
}
