import { useEffect, useState } from "react";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";
import { fetchBloch } from "../../api";
import { BlochSphereCanvas } from "./BlochSphereCanvas";
import type { BlochData } from "../../types";

export function BlochSpherePanel(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);
  const numQubits = useCircuitStore((s) => s.numQubits);
  const [data, setData] = useState<BlochData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    if (!snapshot) {
      setData(null);
      return;
    }
    setError(null);
    fetchBloch(snapshot)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });
    return () => {
      alive = false;
    };
  }, [snapshot]);

  return (
    <div className="border-b border-border px-4 py-3">
      <h2 className="mb-2 font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
        Bloch Sphere {numQubits > 1 ? "(reduced per qubit)" : ""}
      </h2>
      {!snapshot ? (
        <Placeholder text="Run a circuit to see qubits on the Bloch sphere." />
      ) : error ? (
        <Placeholder text={error} />
      ) : !data ? (
        <Placeholder text="Loading Bloch data..." />
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {data.qubits.map((q) => (
            <div
              key={q.qubit}
              className="rounded-md border border-border bg-bg-base/30 p-2"
            >
              <div className="mb-1 flex items-center justify-between px-1 font-mono text-[10px] text-text-muted">
                <span>q[{q.qubit}]</span>
                <span>purity = {q.purity.toFixed(3)}</span>
              </div>
              <BlochSphereCanvas x={q.x} y={q.y} z={q.z} />
              <div className="mt-1 grid grid-cols-2 gap-1 px-1 font-mono text-[10px] text-text-secondary">
                <span>θ = {q.theta.toFixed(3)}</span>
                <span>φ = {q.phi.toFixed(3)}</span>
                <span>x = {q.x.toFixed(3)}</span>
                <span>y = {q.y.toFixed(3)}</span>
                <span>z = {q.z.toFixed(3)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Placeholder({ text }: { text: string }): JSX.Element {
  return (
    <div className="rounded-md border border-dashed border-border bg-bg-base/30 px-3 py-4 text-center font-mono text-[11px] text-text-muted">
      {text}
    </div>
  );
}
