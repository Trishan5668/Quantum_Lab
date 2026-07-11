import type { StateSnapshot } from "../../types";
import { ProbabilityDerivation } from "./ProbabilityDerivation";

export function MeasurementProof({ snapshot }: { snapshot: StateSnapshot }): JSX.Element {
  return (
    <div className="space-y-2">
      <p className="text-xs leading-5 text-text-secondary">
        A computational-basis measurement asks which basis vector is observed. QuantumLab computes each chance from the
        squared magnitude of its amplitude before any sampling or collapse.
      </p>
      <ProbabilityDerivation snapshot={snapshot} />
    </div>
  );
}
