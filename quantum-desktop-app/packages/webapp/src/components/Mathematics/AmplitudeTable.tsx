import type { StateSnapshot } from "../../types";
import { amplitudeRows, complexToText, fmt } from "./mathDerivations";

export function AmplitudeTable({ snapshot }: { snapshot: StateSnapshot }): JSX.Element {
  const rows = amplitudeRows(snapshot);
  return (
    <div className="panel-card overflow-x-auto">
      <table className="w-full text-left font-mono text-[11px]">
        <thead className="bg-bg-elevated/80 text-text-muted">
          <tr>
            <th className="px-2 py-1.5">Basis</th>
            <th className="px-2 py-1.5">Amplitude</th>
            <th className="px-2 py-1.5 text-right">|a|</th>
            <th className="px-2 py-1.5 text-right">P</th>
            <th className="px-2 py-1.5 text-right">Phase</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.basis} className="border-t border-border/50">
              <td className="px-2 py-1 text-accent-glow">{row.basis}</td>
              <td className="px-2 py-1 text-text-primary">{complexToText(row.amplitude)}</td>
              <td className="px-2 py-1 text-right">{fmt(row.magnitude)}</td>
              <td className="px-2 py-1 text-right">{fmt(row.probability)}</td>
              <td className="px-2 py-1 text-right">{fmt(row.phase)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
