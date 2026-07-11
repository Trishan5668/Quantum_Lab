import type { DensityMatrixData, StateSnapshot } from "../../types";
import { LatexBlock } from "./LatexBlock";
import { MatrixRenderer } from "./MatrixRenderer";
import { densityFromData, densityFromState, fmt } from "./mathDerivations";

interface DensityDerivationProps {
  finalState: StateSnapshot;
  densityData?: DensityMatrixData | null;
  purity?: number | null;
}

export function DensityDerivation({ finalState, densityData, purity }: DensityDerivationProps): JSX.Element {
  const matrix = densityData ? densityFromData(densityData) : densityFromState(finalState);
  const displayedPurity = purity ?? traceRhoSquared(matrix);
  return (
    <div className="space-y-3">
      <LatexBlock label="Outer product" math={"\\rho=|\\psi\\rangle\\langle\\psi|"} compact />
      <p className="text-xs leading-5 text-text-secondary">
        Each density-matrix entry is an amplitude times the complex conjugate of another amplitude: rho_ij = a_i a_j^*.
      </p>
      <MatrixRenderer matrix={matrix} rowLabels={finalState.basis_labels} colLabels={finalState.basis_labels} maxDim={8} />
      <LatexBlock label="Purity" math={`\\mathrm{Tr}(\\rho^2)=${fmt(displayedPurity)}`} compact />
      <p className="text-xs leading-5 text-text-secondary">
        Purity near 1 means the state is pure. Values below 1 mean noise or tracing out information has produced a mixed state.
      </p>
    </div>
  );
}

function traceRhoSquared(matrix: ReturnType<typeof densityFromState>): number {
  let total = 0;
  for (let r = 0; r < matrix.length; r += 1) {
    for (let c = 0; c < matrix.length; c += 1) {
      const a = matrix[r][c];
      const b = matrix[c][r];
      total += a.re * b.re - a.im * b.im;
    }
  }
  return total;
}
