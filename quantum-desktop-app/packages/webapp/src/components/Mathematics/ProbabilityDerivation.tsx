import type { StateSnapshot } from "../../types";
import { LatexBlock } from "./LatexBlock";
import { amplitudeRows, complexToLatex, fmt } from "./mathDerivations";

export function ProbabilityDerivation({ snapshot }: { snapshot: StateSnapshot }): JSX.Element {
  const rows = amplitudeRows(snapshot);
  return (
    <div className="space-y-3">
      <LatexBlock label="Born rule" math={"P(i)=|a_i|^2=a_i a_i^*"} compact />
      <div className="grid gap-1">
        {rows.map((row) => (
          <div key={row.basis} className="math-born-row">
            <span className="text-accent-glow">{row.basis}</span>
            <span>
              P = |{complexToLatex(row.amplitude)}|^2 = {fmt(row.probability)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
