import { useMemo } from "react";
import Plot from "react-plotly.js";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";

export function ProbabilityChart(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);

  const { x, y } = useMemo(() => {
    if (!snapshot) return { x: [] as string[], y: [] as number[] };
    return {
      x: snapshot.basis_labels.map((s) => s.replace(/^\|/, "|").replace(/>$/, "⟩")),
      y: snapshot.probabilities,
    };
  }, [snapshot]);

  return (
    <div className="border-b border-border px-4 py-3">
      <h2 className="mb-2 font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
        Measurement Probabilities
      </h2>
      {!snapshot ? (
        <div className="rounded-md border border-dashed border-border bg-bg-base/30 px-3 py-4 text-center font-mono text-[11px] text-text-muted">
          Run the circuit to see probabilities.
        </div>
      ) : (
        <Plot
          data={[
            {
              type: "bar",
              x,
              y,
              marker: {
                color: y.map((v) =>
                  v > 0.001 ? "rgba(124,58,237,0.85)" : "rgba(124,58,237,0.18)",
                ),
                line: { color: "rgba(167,139,250,0.7)", width: 1 },
              },
              hovertemplate: "%{x}: %{y:.4f}<extra></extra>",
              text: y.map((v) => (v > 0.005 ? v.toFixed(3) : "")),
              textposition: "outside",
              textfont: { color: "#94a3b8", size: 10 },
            },
          ]}
          layout={{
            autosize: true,
            height: 160,
            margin: { l: 30, r: 6, t: 4, b: 30 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { family: "'JetBrains Mono', monospace", size: 10, color: "#94a3b8" },
            yaxis: {
              range: [0, Math.max(0.1, Math.max(...y, 0) * 1.18)],
              gridcolor: "rgba(148,163,184,0.12)",
              zerolinecolor: "rgba(148,163,184,0.2)",
              tickformat: ".2f",
            },
            xaxis: { gridcolor: "rgba(148,163,184,0.06)" },
          }}
          config={{ displayModeBar: false, responsive: true, staticPlot: false }}
          useResizeHandler
          style={{ width: "100%" }}
        />
      )}
    </div>
  );
}
