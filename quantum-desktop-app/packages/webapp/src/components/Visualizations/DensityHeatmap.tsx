import { memo, useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { useCircuitStore, selectCurrentState, selectDensityData } from "../../store/circuitStore";
import { fetchDensity } from "../../api";
import type { DensityMatrixData } from "../../types";
import { PanelSection, PanelPlaceholder } from "../ui/PanelSection";

export function DensityHeatmap(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);
  const v2Density = useCircuitStore(selectDensityData);
  const simulationMode = useCircuitStore((s) => s.simulationMode);
  const [data, setData] = useState<DensityMatrixData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (v2Density) {
      setData(v2Density);
      setError(null);
      return;
    }
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
  }, [snapshot, v2Density]);

  const badge =
    simulationMode === "density" ? (
      <span className="rounded-full bg-accent-quantum/15 px-2 py-0.5 font-mono text-[9px] normal-case tracking-normal text-accent-glow ring-1 ring-accent-quantum/30">
        simulation mode
      </span>
    ) : null;

  return (
    <PanelSection
      title="Density Matrix ρ"
      subtitle="Real and imaginary components of the density operator"
      badge={badge}
    >
      {!snapshot && !v2Density ? (
        <PanelPlaceholder>Run a circuit to see ρ.</PanelPlaceholder>
      ) : error ? (
        <PanelPlaceholder>ρ unavailable: {error}</PanelPlaceholder>
      ) : !data ? (
        <PanelPlaceholder>Computing density matrix…</PanelPlaceholder>
      ) : (
        <div className="density-heatmap-grid">
          <HeatmapCell title="Re(ρ)" matrix={data.real} labels={data.basis_labels} showScale={false} />
          <HeatmapCell title="Im(ρ)" matrix={data.imag} labels={data.basis_labels} showScale />
        </div>
      )}
    </PanelSection>
  );
}

const HeatmapCell = memo(function HeatmapCell({
  title,
  matrix,
  labels,
  showScale,
}: {
  title: string;
  matrix: number[][];
  labels: string[];
  showScale: boolean;
}) {
  const dim = matrix.length;
  const max = useMemo(
    () => Math.max(1e-6, ...matrix.flat().map((v) => Math.abs(v))),
    [matrix],
  );
  const axisLabels = useMemo(
    () => labels.map((s) => s.replace(/^\|/, "").replace(/>$/, "")),
    [labels],
  );

  return (
    <div className="density-heatmap-cell">
      <div className="mb-1 flex items-center justify-between px-0.5">
        <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">{title}</span>
        <span className="font-mono text-[9px] text-text-muted">±{max.toFixed(2)}</span>
      </div>
      <div className="density-plot-wrap">
        <Plot
          data={[
            {
              type: "heatmap",
              z: [...matrix].reverse(),
              x: axisLabels,
              y: [...axisLabels].reverse(),
              colorscale: title.startsWith("Im") ? "PuOr" : "RdBu",
              reversescale: !title.startsWith("Im"),
              zmin: -max,
              zmax: max,
              showscale: showScale,
              colorbar: showScale
                ? {
                    thickness: 10,
                    len: 0.9,
                    tickfont: { size: 8, color: "#94a3b8" },
                    outlinewidth: 0,
                  }
                : undefined,
              hovertemplate: "%{y}, %{x}: %{z:.4f}<extra></extra>",
            },
          ]}
          layout={{
            autosize: true,
            height: 140,
            margin: { l: 36, r: showScale ? 28 : 4, t: 4, b: 28 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { family: "'JetBrains Mono', monospace", size: 8, color: "#94a3b8" },
            xaxis: { tickangle: -45, scaleanchor: "y", side: "bottom" },
            yaxis: { autorange: false, range: [-0.5, dim - 0.5] },
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </div>
  );
});
