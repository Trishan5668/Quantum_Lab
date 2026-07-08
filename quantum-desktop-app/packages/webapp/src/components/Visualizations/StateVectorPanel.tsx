import { useMemo } from "react";
import { InlineMath } from "react-katex";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";
import { PanelSection, PanelPlaceholder } from "../ui/PanelSection";

const AMP_EPS = 1e-10;

export function StateVectorPanel(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);

  const rows = useMemo(() => {
    if (!snapshot?.amplitudes) return [];
    return snapshot.amplitudes
      .map((a, i) => ({
        idx: i,
        label: snapshot.basis_labels[i],
        re: a.real,
        im: a.imag,
        p: snapshot.probabilities[i],
      }))
      .filter((r) => Math.abs(r.re) > AMP_EPS || Math.abs(r.im) > AMP_EPS);
  }, [snapshot]);

  return (
    <PanelSection title="State Vector" subtitle="Live amplitudes and Born-rule probabilities">
      {!snapshot ? (
        <PanelPlaceholder>Run a circuit to see the live state vector.</PanelPlaceholder>
      ) : rows.length === 0 ? (
        <PanelPlaceholder>No non-zero amplitudes (mixed state or |0…0⟩).</PanelPlaceholder>
      ) : (
        <div className="panel-card overflow-x-auto">
          <table className="w-full text-left font-mono text-[11px]">
            <thead className="sticky top-0 bg-bg-elevated/95">
              <tr className="border-b border-border text-text-muted">
                <th className="px-2 py-1.5">Basis</th>
                <th className="px-2 py-1.5 text-right">Re</th>
                <th className="px-2 py-1.5 text-right">Im</th>
                <th className="px-2 py-1.5 text-right">P</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.idx} className="border-b border-border/40 last:border-b-0">
                  <td className="px-2 py-1">
                    <InlineMath math={`|${labelInner(r.label)}\\rangle`} />
                  </td>
                  <td className="px-2 py-1 text-right text-text-primary">{fmt(r.re)}</td>
                  <td className="px-2 py-1 text-right text-text-secondary">{fmt(r.im)}</td>
                  <td className="px-2 py-1 text-right">
                    <ProbCell p={r.p} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PanelSection>
  );
}

function ProbCell({ p }: { p: number }): JSX.Element {
  const pct = (p * 100).toFixed(2);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-accent-glow">{pct}%</span>
      <span className="relative inline-block h-1.5 w-12 overflow-hidden rounded-full bg-bg-elevated">
        <span
          className="absolute left-0 top-0 h-full bg-gradient-to-r from-accent-quantum to-accent-glow transition-[width] duration-300"
          style={{ width: `${Math.min(100, p * 100)}%` }}
        />
      </span>
    </span>
  );
}

function labelInner(label: string): string {
  return label.replace(/^\|/, "").replace(/>$/, "");
}

function fmt(v: number): string {
  if (Math.abs(v) < 1e-12) return "0.000";
  return (v >= 0 ? " " : "") + v.toFixed(3);
}
