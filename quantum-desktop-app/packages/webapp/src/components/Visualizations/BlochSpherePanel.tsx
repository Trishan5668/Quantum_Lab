import { useEffect, useState } from "react";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";
import { fetchBloch } from "../../api";
import { BlochSphereCanvas } from "./BlochSphereCanvas";
import type { BlochData } from "../../types";
import { PanelSection, PanelPlaceholder } from "../ui/PanelSection";

export function BlochSpherePanel(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);
  const numQubits = useCircuitStore((s) => s.numQubits);
  const [data, setData] = useState<BlochData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    if (!snapshot || snapshot.amplitudes.length === 0) {
      setData(null);
      setError(null);
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

  const subtitle = numQubits > 1 ? "Reduced density matrix per qubit" : "Single-qubit Bloch vector";

  return (
    <PanelSection title="Bloch Sphere" subtitle={subtitle}>
      {!snapshot ? (
        <PanelPlaceholder>Run a circuit to see qubits on the Bloch sphere.</PanelPlaceholder>
      ) : snapshot.amplitudes.length === 0 ? (
        <PanelPlaceholder>Bloch view requires a pure state (mixed ρ has no amplitudes).</PanelPlaceholder>
      ) : error ? (
        <PanelPlaceholder>{error}</PanelPlaceholder>
      ) : !data ? (
        <PanelPlaceholder>Loading Bloch data…</PanelPlaceholder>
      ) : (
        <div className="grid grid-cols-1 gap-2">
          {data.qubits.map((q) => (
            <div key={q.qubit} className="panel-card p-2">
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
    </PanelSection>
  );
}
