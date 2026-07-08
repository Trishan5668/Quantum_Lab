import { useCircuitStore } from "../../store/circuitStore";
import { PanelSection, PanelPlaceholder } from "../ui/PanelSection";

function indicatorColor(ratio: number): string {
  if (ratio >= 0.9) return "bg-emerald-400";
  if (ratio >= 0.6) return "bg-amber-400";
  return "bg-red-400";
}

function metricColorClass(ratio: number): string {
  if (ratio >= 0.9) return "text-emerald-300";
  if (ratio >= 0.6) return "text-amber-300";
  return "text-red-300";
}

export function MetricsPanel(): JSX.Element {
  const metrics = useCircuitStore((s) => s.metrics);
  const resultsV2 = useCircuitStore((s) => s.resultsV2);
  const results = useCircuitStore((s) => s.results);
  const simulationMode = useCircuitStore((s) => s.simulationMode);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const noiseModel = useCircuitStore((s) => s.noiseModel);
  const noiseProbability = useCircuitStore((s) => s.noiseProbability);

  const hasRun = results !== null;

  return (
    <PanelSection
      title="Metrics"
      subtitle="Fidelity, entropy, purity, and simulation status"
      noBorder
    >
      {!hasRun ? (
        <PanelPlaceholder>
          Run a circuit to see simulation status. Use density mode or noise for fidelity, entropy, and purity.
        </PanelPlaceholder>
      ) : (
        <div className="metric-grid">
          <MetricCard
            title="Simulation Mode"
            value={simulationMode === "density" ? "Density Matrix" : "Statevector"}
            unit=""
            detail={
              simulationMode === "density"
                ? "Mixed-state evolution enabled."
                : "Pure statevector (default)."
            }
            ratio={1}
          />
          <MetricCard
            title="Noise Level"
            value={noiseEnabled ? noiseModel.replace(/_/g, " ") : "Off"}
            unit={noiseEnabled && noiseModel !== "t1_t2" ? `p=${noiseProbability.toFixed(3)}` : ""}
            detail={
              noiseEnabled
                ? resultsV2?.mixed_state
                  ? "Noise applied — state is mixed."
                  : "Noise enabled on circuit run."
                : "No decoherence channel active."
            }
            ratio={noiseEnabled ? 0.5 : 1}
          />
          {metrics?.fidelity && (
            <MetricCard
              title="Fidelity"
              value={(metrics.fidelity.fidelity * 100).toFixed(1)}
              unit="%"
              detail={`Target: ${metrics.fidelity.target_state} — ${metrics.fidelity.interpretation}`}
              ratio={metrics.fidelity.fidelity}
            />
          )}
          {metrics?.entropy && (
            <MetricCard
              title="Entanglement Entropy"
              value={metrics.entropy.entropy.toFixed(3)}
              unit="bits"
              detail={`Subsystem q[0] — ${metrics.entropy.interpretation}`}
              ratio={Math.min(1, metrics.entropy.entropy)}
            />
          )}
          {(metrics?.purity != null || resultsV2?.purity != null) && (
            <MetricCard
              title="Purity"
              value={(metrics?.purity?.purity ?? resultsV2?.purity ?? 1).toFixed(4)}
              unit="Tr(ρ²)"
              detail={
                (metrics?.purity?.purity ?? resultsV2?.purity ?? 1) < 0.999
                  ? "Mixed state due to noise or density evolution."
                  : "Pure state."
              }
              ratio={metrics?.purity?.purity ?? resultsV2?.purity ?? 1}
            />
          )}
        </div>
      )}
    </PanelSection>
  );
}

function MetricCard({
  title,
  value,
  unit,
  detail,
  ratio,
}: {
  title: string;
  value: string;
  unit: string;
  detail: string;
  ratio: number;
}): JSX.Element {
  const clamped = Math.max(0, Math.min(1, ratio));
  return (
    <div className="metric-card">
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">{title}</span>
        <div className="text-right">
          <span className={`font-mono text-sm font-semibold ${metricColorClass(clamped)}`}>{value}</span>
          {unit && <span className="ml-1 font-mono text-[10px] text-text-muted">{unit}</span>}
        </div>
      </div>
      <p className="mt-1.5 text-[10px] leading-relaxed text-text-muted">{detail}</p>
      <div
        className={`metric-indicator ${indicatorColor(clamped)}`}
        style={{ width: `${clamped * 100}%` }}
        role="presentation"
      />
    </div>
  );
}
