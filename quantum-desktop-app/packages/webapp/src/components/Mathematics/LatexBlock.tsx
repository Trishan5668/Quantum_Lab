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
      <div className="math-copy-cluster">
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0"
          title="Copy LaTeX"
          onClick={() => void navigator.clipboard?.writeText(math)}
        >
          TeX
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0"
          title="Copy Unicode approximation"
          onClick={() => void navigator.clipboard?.writeText(latexToUnicode(math))}
        >
          Unicode
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0"
          title="Copy MathML wrapper"
          onClick={() => void navigator.clipboard?.writeText(`<math><semantics><annotation encoding="application/x-tex">${escapeXml(math)}</annotation></semantics></math>`)}
        >
          MathML
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0"
          title="Copy rendered equation text"
          onClick={() => void navigator.clipboard?.writeText(latexToUnicode(math))}
        >
          Rendered
        </button>
      </div>
    </div>
  );
}

export function InlineLatex({ math }: { math: string }): JSX.Element {
  return <InlineMath math={math} />;
}

function latexToUnicode(value: string): string {
  return value
    .replace(/\\rangle/g, "⟩")
    .replace(/\\langle/g, "⟨")
    .replace(/\\ket\{([^}]+)\}/g, "|$1⟩")
    .replace(/\\bra\{([^}]+)\}/g, "⟨$1|")
    .replace(/\\psi/g, "ψ")
    .replace(/\\rho/g, "ρ")
    .replace(/\\sigma/g, "σ")
    .replace(/\\lambda/g, "λ")
    .replace(/\\theta/g, "θ")
    .replace(/\\phi/g, "φ")
    .replace(/\\otimes/g, "⊗")
    .replace(/\\dagger/g, "†")
    .replace(/\\sum/g, "Σ")
    .replace(/\\mathrm\{Tr\}/g, "Tr")
    .replace(/\\left|/g, "|")
    .replace(/\\right|/g, "|")
    .replace(/[{}\\]/g, "");
}

function escapeXml(value: string): string {
  return value.replace(/[<>&"']/g, (char) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[char] ?? char);
}
