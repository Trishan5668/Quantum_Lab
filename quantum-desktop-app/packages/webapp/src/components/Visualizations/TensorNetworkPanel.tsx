import { useCircuitStore } from "../../store/circuitStore";

/** Displays measured MPS metadata supplied by the backend, never estimates it in the UI. */
export function TensorNetworkPanel(): JSX.Element | null {
  const data = useCircuitStore((s) => s.results?.tensor_network);
  if (!data) return null;
  return (
    <section className="border-t border-border px-4 py-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Tensor network / MPS</p>
      <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px] text-text-secondary">
        <span>Peak bond: <b className="text-text-primary">{data.max_bond_dimension}</b></span>
        <span>Memory: <b className="text-text-primary">{(data.estimated_memory_bytes / 1024).toFixed(1)} KiB</b></span>
        <span className="col-span-2">Bonds: <b className="text-text-primary">{data.bond_dimensions.join(" · ") || "product state"}</b></span>
        <span className="col-span-2">Discarded weight: <b className="text-text-primary">{data.cumulative_truncation_error.toExponential(2)}</b></span>
        <span className="col-span-2">Entropy by bond: <b className="text-text-primary">{data.entanglement_entropy.map((v) => v.toFixed(3)).join(" · ") || "—"}</b></span>
      </div>
    </section>
  );
}
