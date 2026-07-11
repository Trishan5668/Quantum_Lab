import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GatePalette } from "../components/CircuitBuilder/GatePalette";
import { CircuitCanvas } from "../components/CircuitBuilder/CircuitCanvas";
import { CircuitDiagram } from "../components/CircuitBuilder/CircuitDiagram";
import { CircuitDndProvider } from "../components/CircuitBuilder/CircuitDndProvider";
import { Toolbar } from "../components/CircuitBuilder/Toolbar";
import { NoiseSettings } from "../components/CircuitBuilder/NoiseSettings";
import { StateVectorPanel } from "../components/Visualizations/StateVectorPanel";
import { BlochSpherePanel } from "../components/Visualizations/BlochSpherePanel";
import { ProbabilityChart } from "../components/Visualizations/ProbabilityChart";
import { DensityHeatmap } from "../components/Visualizations/DensityHeatmap";
import { MetricsPanel } from "../components/Visualizations/MetricsPanel";
import { ELI15Panel } from "../components/ELI15Panel/ELI15Panel";
import { MathematicsPanel } from "../components/Mathematics/MathematicsPanel";
import { LearningLayerSelector } from "../components/platform/LearningLayerSelector";
import { PageMeta } from "../components/platform/PageMeta";
import { fetchHealth } from "../api";
import {
  API_BASE_URL,
  BACKEND_UNAVAILABLE_MESSAGE,
  ENVIRONMENT_LABEL,
  frontendUrl,
} from "../config/api";
import { usePlatformStore, type LearningLayer } from "../store/platformStore";

type HealthStatus = "checking" | "ok" | "down";

function panelVisible(layer: LearningLayer, panel: string): boolean {
  switch (panel) {
    case "statevector":
      return layer !== "explore";
    case "density":
    case "metrics":
    case "noise":
      return layer === "research";
    case "mathematics":
      return layer === "mathematics" || layer === "research";
    default:
      return true;
  }
}

export default function SimulatorPage(): JSX.Element {
  const learningLayer = usePlatformStore((s) => s.learningLayer);
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [healthVersion, setHealthVersion] = useState("");
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);

  const ping = useCallback(async () => {
    setHealth((current) => (current === "ok" ? current : "checking"));
    try {
      const data = await fetchHealth();
      setHealth("ok");
      setHealthVersion(`core v${data.core_version} / api v${data.version}`);
    } catch {
      setHealth("down");
      setHealthVersion("");
    }
  }, []);

  useEffect(() => {
    let alive = true;
    const guardedPing = async () => {
      try {
        const data = await fetchHealth();
        if (!alive) return;
        setHealth("ok");
        setHealthVersion(`core v${data.core_version} / api v${data.version}`);
      } catch {
        if (!alive) return;
        setHealth("down");
        setHealthVersion("");
      }
    };
    void guardedPing();
    const id = window.setInterval(guardedPing, 8000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  return (
    <>
      <PageMeta
        title="QuantumLab Simulator"
        description="Build quantum circuits, visualize state vectors, Bloch spheres, density matrices, and run AI-powered explanations."
      />
      <div className="app-shell bg-bg-base text-text-primary">
        <header className="flex shrink-0 items-center justify-between border-b border-border bg-bg-surface/80 px-4 py-2.5 backdrop-blur sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <Link to="/" className="flex min-w-0 items-center gap-3 hover:opacity-90">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">
                <span className="font-display text-sm font-bold text-accent-glow">Q</span>
              </div>
              <div className="min-w-0">
                <h1 className="truncate font-display text-base font-semibold tracking-wide">
                  QuantumLab
                </h1>
                <p className="truncate text-xs text-text-muted">
                  Quantum computing learning platform
                </p>
              </div>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <LearningLayerSelector />
            <HealthBadge
              status={health}
              version={healthVersion}
              diagnosticsOpen={diagnosticsOpen}
              onDiagnostics={() => setDiagnosticsOpen((open) => !open)}
              onRetry={() => void ping()}
            />
          </div>
        </header>

        {diagnosticsOpen && (
          <DiagnosticsPanel status={health} version={healthVersion} onRetry={() => void ping()} />
        )}

        <Toolbar />

        <CircuitDndProvider>
          <main className="app-main-grid">
            <aside className="sidebar-left border-r border-border bg-bg-surface/60">
              <div className="sidebar-scroll">
                <GatePalette />
              </div>
              {panelVisible(learningLayer, "noise") && <NoiseSettings />}
            </aside>

            <section className="center-column grid min-h-0 grid-rows-[1fr_13rem_auto] overflow-hidden border-border bg-bg-base/20">
              <div className="min-h-0 overflow-hidden">
                <CircuitCanvas />
              </div>
              <div className="min-h-0 overflow-hidden">
                <CircuitDiagram />
              </div>
              <ELI15Panel />
            </section>

            <aside className="sidebar-right border-l border-border bg-bg-surface/60">
              <div className="sidebar-scroll">
                {panelVisible(learningLayer, "mathematics") && <MathematicsPanel />}
                {panelVisible(learningLayer, "statevector") && <StateVectorPanel />}
                <BlochSpherePanel />
                <ProbabilityChart />
                {panelVisible(learningLayer, "density") && <DensityHeatmap />}
                {panelVisible(learningLayer, "metrics") && <MetricsPanel />}
              </div>
            </aside>
          </main>
        </CircuitDndProvider>
      </div>
    </>
  );
}

function HealthBadge({
  status,
  version,
  diagnosticsOpen,
  onDiagnostics,
  onRetry,
}: {
  status: HealthStatus;
  version: string;
  diagnosticsOpen: boolean;
  onDiagnostics: () => void;
  onRetry: () => void;
}): JSX.Element {
  const color =
    status === "ok"
      ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
      : status === "down"
        ? "bg-red-500/15 text-red-300 ring-red-500/30"
        : "bg-zinc-500/15 text-zinc-300 ring-zinc-500/30";
  const dotColor =
    status === "ok" ? "bg-emerald-400" : status === "down" ? "bg-red-400" : "bg-zinc-400";
  const label =
    status === "ok"
      ? `API connected - ${version}`
      : status === "down"
        ? BACKEND_UNAVAILABLE_MESSAGE
        : "Checking API...";

  return (
    <div className="flex shrink-0 items-center gap-1.5">
      <span
        className={`inline-flex max-w-[min(100%,280px)] shrink-0 items-center gap-2 truncate rounded-full px-3 py-1 font-mono text-[10px] ring-1 ${color}`}
        title={`${label} Backend URL: ${API_BASE_URL}`}
      >
        <span className={`h-1.5 w-1.5 shrink-0 animate-pulse rounded-full ${dotColor}`} />
        <span className="truncate">{label}</span>
      </span>
      {status === "down" && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={onDiagnostics}
        aria-expanded={diagnosticsOpen}
      >
        Diagnostics
      </button>
    </div>
  );
}

function DiagnosticsPanel({
  status,
  version,
  onRetry,
}: {
  status: HealthStatus;
  version: string;
  onRetry: () => void;
}): JSX.Element {
  const backendStatus =
    status === "ok" ? `Connected (${version})` : status === "down" ? BACKEND_UNAVAILABLE_MESSAGE : "Checking...";

  return (
    <section className="border-b border-border bg-bg-surface/95 px-4 py-3 shadow-lg sm:px-5">
      <div className="mx-auto grid max-w-5xl gap-3 font-mono text-[11px] text-text-secondary sm:grid-cols-[1fr_auto] sm:items-start">
        <div className="grid gap-1.5 sm:grid-cols-2">
          <DiagnosticRow label="Environment" value={ENVIRONMENT_LABEL} />
          <DiagnosticRow label="Frontend URL" value={frontendUrl()} />
          <DiagnosticRow label="Configured API URL" value={API_BASE_URL} />
          <DiagnosticRow label="Backend Status" value={backendStatus} />
          <DiagnosticRow label="Backend URL" value={API_BASE_URL} />
        </div>
        <button type="button" className="btn btn-secondary btn-sm justify-self-start" onClick={onRetry}>
          Retry
        </button>
      </div>
    </section>
  );
}

function DiagnosticRow({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="min-w-0">
      <span className="text-text-muted">{label}: </span>
      <span className="break-all text-text-primary">{value}</span>
    </div>
  );
}
