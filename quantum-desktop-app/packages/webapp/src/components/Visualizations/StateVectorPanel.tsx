import { useMemo } from "react";
import { InlineMath } from "react-katex";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";

const AMP_EPS = 1e-10;

export function StateVectorPanel(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);

  const rows = useMemo(() => {
    if (!snapshot) return [];
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
    <div className="border-b border-border px-4 py-3">
      <h2 className="mb-3 font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
        State Vector
      </h2>
      {!snapshot ? (
        <EmptyState message="Run a circuit to see the live state vector." />
      ) : rows.length === 0 ? (
        <EmptyState message="(no non-zero amplitudes)" />
      ) : (
        <div className="overflow-x-auto rounded-md border border-border bg-bg-base/40">
          <table className="w-full text-left font-mono text-[11px]">
            <thead>
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
                  <td className="px-2 py-1 text-right text-text-primary">
                    {fmt(r.re)}
                  </td>
                  <td className="px-2 py-1 text-right text-text-secondary">
                    {fmt(r.im)}
                  </td>
                  <td className="px-2 py-1 text-right">
                    <ProbCell p={r.p} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
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
          style={{ width: `${(p * 100).toFixed(2)}%` }}
        />
      </span>
    </span>
  );
}

function EmptyState({ message }: { message: string }): JSX.Element {
  return (
    <div className="rounded-md border border-dashed border-border bg-bg-base/30 px-3 py-4 text-center font-mono text-[11px] text-text-muted">
      {message}
    </div>
  );
}

function labelInner(label: string): string {
  // expects "|XYZ>" -> "XYZ"
  return label.replace(/^\|/, "").replace(/>$/, "");
}

function fmt(v: number): string {
  if (Math.abs(v) < 1e-12) return "0.000";
  return (v >= 0 ? " " : "") + v.toFixed(3);
}
