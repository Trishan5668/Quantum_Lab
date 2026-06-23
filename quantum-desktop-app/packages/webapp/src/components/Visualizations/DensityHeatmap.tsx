import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";
import { fetchDensity } from "../../api";
import type { DensityMatrixData } from "../../types";

export function DensityHeatmap(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);
  const [data, setData] = useState<DensityMatrixData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    if (!snapshot) {
      setData(null);
      setError(null);
      return;
    }
    setError(null);
    fetchDensity(snapshot)
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
        Density Matrix ρ
      </h2>
      {!snapshot ? (
        <Placeholder text="Run a circuit to see ρ." />
      ) : error ? (
        <Placeholder text={`ρ unavailable: ${error}`} />
      ) : !data ? (
        <Placeholder text="Computing density matrix..." />
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <Heatmap title="Re(ρ)" matrix={data.real} labels={data.basis_labels} />
          <Heatmap title="Im(ρ)" matrix={data.imag} labels={data.basis_labels} />
        </div>
      )}
    </div>
  );
}

function Heatmap({
  title,
  matrix,
  labels,
}: {
  title: string;
  matrix: number[][];
  labels: string[];
}): JSX.Element {
  const dim = matrix.length;
  const max = Math.max(
    1e-6,
    ...matrix.flat().map((v) => Math.abs(v)),
  );
  return (
    <div className="rounded-md border border-border bg-bg-base/40 p-1">
      <div className="px-1 pb-1 font-mono text-[10px] uppercase tracking-widest text-text-muted">
        {title}
      </div>
      <Plot
        data={[
          {
            type: "heatmap",
            z: [...matrix].reverse(),
            x: labels.map((s) => s.replace(/^\|/, "").replace(/>$/, "")),
            y: [...labels].reverse().map((s) => s.replace(/^\|/, "").replace(/>$/, "")),
            colorscale: "RdBu",
            reversescale: true,
            zmin: -max,
            zmax: max,
            showscale: false,
            hovertemplate: "ρ[%{y},%{x}] = %{z:.3f}<extra></extra>",
          },
        ]}
        layout={{
          autosize: true,
          height: 130 + dim * 4,
          margin: { l: 26, r: 4, t: 2, b: 22 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: "'JetBrains Mono', monospace", size: 9, color: "#94a3b8" },
          xaxis: { tickangle: 0, scaleanchor: "y" },
          yaxis: { autorange: false, range: [-0.5, dim - 0.5] },
        }}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%" }}
      />
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
