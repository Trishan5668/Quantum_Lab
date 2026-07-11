import { BlockMath, InlineMath } from "react-katex";

interface LatexBlockProps {
  math: string;
  label?: string;
  compact?: boolean;
}

export function LatexBlock({ math, label, compact = false }: LatexBlockProps): JSX.Element {
  return (
    <div className={`math-latex-block ${compact ? "math-latex-compact" : ""}`}>
      <div className="min-w-0 flex-1 overflow-x-auto">
        {label && <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{label}</p>}
        <BlockMath math={math} />
      </div>
      <button
        type="button"
        className="btn btn-ghost btn-sm shrink-0"
        title="Copy LaTeX"
        onClick={() => void navigator.clipboard?.writeText(math)}
      >
        TeX
      </button>
    </div>
  );
}

export function InlineLatex({ math }: { math: string }): JSX.Element {
  return <InlineMath math={math} />;
}
