import { motion } from "framer-motion";
import type { MultiplicationCell } from "./mathDerivations";
import { complexToText } from "./mathDerivations";

interface MatrixMultiplicationProps {
  cells: MultiplicationCell[];
  basisLabels: string[];
}

export function MatrixMultiplication({ cells, basisLabels }: MatrixMultiplicationProps): JSX.Element {
  const visible = cells.slice(0, 8);
  return (
    <div className="space-y-2">
      {cells.length > 8 && (
        <p className="text-xs text-text-muted">
          Showing first 8 row-column products. The same rule continues for all {cells.length} rows.
        </p>
      )}
      <div className="grid gap-2">
        {visible.map((cell, index) => (
          <motion.div
            key={cell.row}
            className="math-row-product"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.04 }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] text-accent-glow">{`row ${cell.row + 1} -> ${basisLabels[cell.row]}`}</span>
              <span className="font-mono text-[11px] text-text-primary">{complexToText(cell.total)}</span>
            </div>
            <p className="mt-1 break-words font-mono text-[10px] leading-5 text-text-muted">
              {cell.terms.join(" + ")}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
