import { motion } from "framer-motion";
import { LatexBlock } from "./LatexBlock";
import { MatrixRenderer } from "./MatrixRenderer";
import type { GateMath } from "./mathDerivations";
import { complexToText, matrixToLatex } from "./mathDerivations";

export function TensorVisualizer({ gate }: { gate: GateMath }): JSX.Element {
  const expression = gate.tensorFactors.join("\\otimes");
  return (
    <div className="space-y-2">
      <LatexBlock label="Embedded operator" math={`${gate.symbol}_{full}=${expression}`} compact />
      {gate.tensorBlocks.length > 0 && (
        <div className="grid gap-2">
          <p className="text-xs leading-5 text-text-secondary">
            Each scalar from the left matrix multiplies every element of the identity, forming one block at a time.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {gate.tensorBlocks.map((block, index) => (
              <motion.div
                key={`${block.row}-${block.col}`}
                className="panel-card p-2"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <p className="mb-1 font-mono text-[10px] text-text-muted">
                  element ({block.row + 1},{block.col + 1}) = {complexToText(block.scalar)}
                </p>
                <LatexBlock math={`${complexToText(block.scalar)}I=${matrixToLatex(block.block, 2)}`} compact />
              </motion.div>
            ))}
          </div>
        </div>
      )}
      <MatrixRenderer matrix={gate.fullMatrix} maxDim={8} />
    </div>
  );
}
