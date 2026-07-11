import type { ComplexMatrix } from "./mathDerivations";
import { complexToText } from "./mathDerivations";

interface MatrixRendererProps {
  matrix: ComplexMatrix;
  rowLabels?: string[];
  colLabels?: string[];
  maxDim?: number;
}

export function MatrixRenderer({
  matrix,
  rowLabels,
  colLabels,
  maxDim = 8,
}: MatrixRendererProps): JSX.Element {
  if (matrix.length > maxDim || (matrix[0]?.length ?? 0) > maxDim) {
    return (
      <div className="panel-placeholder">
        {matrix.length} x {matrix[0]?.length ?? 0} matrix hidden for readability.
      </div>
    );
  }

  return (
    <div className="math-matrix-wrap">
      <table className="math-matrix">
        {colLabels && (
          <thead>
            <tr>
              {rowLabels && <th />}
              {colLabels.map((label) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {matrix.map((row, r) => (
            <tr key={r}>
              {rowLabels && <th>{rowLabels[r]}</th>}
              {row.map((value, c) => (
                <td key={`${r}-${c}`}>{complexToText(value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
