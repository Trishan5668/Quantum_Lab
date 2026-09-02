import { useCircuitStore } from "../../store/circuitStore";
import { renderCircuitSvg } from "../CircuitBuilder/circuitExport";

export function CircuitPreview(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const gates = useCircuitStore((s) => s.gates);

  const svg = renderCircuitSvg({ numQubits, gates });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-border px-3 py-2">
        <p className="font-display text-[10px] uppercase tracking-[0.2em] text-accent-measure">
          Circuit Preview
        </p>
        <p className="text-[11px] text-text-muted">Synced with simulator circuit</p>
      </div>
      <div className="editor-circuit-preview flex min-h-0 flex-1 items-start justify-center overflow-auto p-3">
        {gates.length === 0 ? (
          <p className="font-mono text-xs text-text-muted">No gates placed yet.</p>
        ) : (
          <div
            className="max-w-full"
            dangerouslySetInnerHTML={{ __html: svg }}
            aria-label="Read-only circuit diagram"
          />
        )}
      </div>
    </div>
  );
}
