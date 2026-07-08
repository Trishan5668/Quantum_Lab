import { memo, useMemo } from "react";
import Plot from "react-plotly.js";
import { useCircuitStore, selectCurrentState } from "../../store/circuitStore";
import { PanelSection, PanelPlaceholder } from "../ui/PanelSection";

export function ProbabilityChart(): JSX.Element {
  const snapshot = useCircuitStore(selectCurrentState);

  const { x, y } = useMemo(() => {
    if (!snapshot?.probabilities) return { x: [] as string[], y: [] as number[] };
    return {
      x: snapshot.basis_labels.map((s) => s.replace(/^\|/, "|").replace(/>$/, "⟩")),
      y: snapshot.probabilities,
    };
  }, [snapshot]);

  return (
    <PanelSection title="Measurement Probabilities" subtitle="Born-rule |⟨b|ψ⟩|²">
      {!snapshot ? (
        <PanelPlaceholder>Run the circuit to see probabilities.</PanelPlaceholder>
      ) : (
        <div className="panel-card overflow-hidden p-1">
          <ProbabilityPlot x={x} y={y} />
        </div>
      )}
    </PanelSection>
  );
}

const ProbabilityPlot = memo(function ProbabilityPlot({
  x,
  y,
}: {
  x: string[];
  y: number[];
}) {
  return (
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
        margin: { l: 32, r: 8, t: 8, b: 36 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "'JetBrains Mono', monospace", size: 10, color: "#94a3b8" },
        yaxis: {
          range: [0, Math.max(0.1, Math.max(...y, 0) * 1.18)],
          gridcolor: "rgba(148,163,184,0.12)",
          zerolinecolor: "rgba(148,163,184,0.2)",
          tickformat: ".2f",
        },
        xaxis: { gridcolor: "rgba(148,163,184,0.06)", tickangle: -25 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
});
