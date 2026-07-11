import { LatexBlock } from "./LatexBlock";
import { MatrixRenderer } from "./MatrixRenderer";
import { TensorVisualizer } from "./TensorVisualizer";
import type { EvolutionStep } from "./mathDerivations";
import { matrixToLatex } from "./mathDerivations";

interface GateDerivationProps {
  step: EvolutionStep;
  level: "beginner" | "intermediate" | "advanced" | "research";
}

export function GateDerivation({ step, level }: GateDerivationProps): JSX.Element {
  const gate = step.gate;
  return (
    <div className="space-y-3">
      <LatexBlock label="Gate definition" math={gate.equation} compact />
      <LatexBlock label="Gate matrix" math={`${gate.symbol}=${matrixToLatex(gate.localMatrix)}`} compact />
      {level !== "beginner" && (
        <div className="space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">Construction</p>
          <ul className="grid gap-1 text-xs leading-5 text-text-secondary">
            {gate.derivation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {(level === "advanced" || level === "research") && <TensorVisualizer gate={gate} />}
      {level === "research" && (
        <div className="grid gap-2">
          <div className="grid grid-cols-3 gap-2 font-mono text-[10px]">
            <Info label="trace" value={gate.trace} />
            <Info label="det" value={gate.determinant} />
            <Info label="eig" value={gate.eigenvalues.join(", ")} />
          </div>
          <LatexBlock label="Unitarity proof" math={gate.unitarity} compact />
          <MatrixRenderer matrix={gate.fullMatrix} maxDim={8} />
        </div>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="panel-card min-w-0 p-2">
      <p className="uppercase tracking-[0.14em] text-text-muted">{label}</p>
      <p className="truncate text-text-primary" title={value}>{value}</p>
    </div>
  );
}
