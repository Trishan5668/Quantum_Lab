import { useEffect, useState } from "react";
import { GatePalette } from "./components/CircuitBuilder/GatePalette";
import { CircuitCanvas } from "./components/CircuitBuilder/CircuitCanvas";
import { CircuitDiagram } from "./components/CircuitBuilder/CircuitDiagram";
import { CircuitDndProvider } from "./components/CircuitBuilder/CircuitDndProvider";
import { Toolbar } from "./components/CircuitBuilder/Toolbar";
import { StateVectorPanel } from "./components/Visualizations/StateVectorPanel";
import { BlochSpherePanel } from "./components/Visualizations/BlochSpherePanel";
import { ProbabilityChart } from "./components/Visualizations/ProbabilityChart";
import { DensityHeatmap } from "./components/Visualizations/DensityHeatmap";
import { ELI15Panel } from "./components/ELI15Panel/ELI15Panel";
import { fetchHealth } from "./api";

type HealthStatus = "checking" | "ok" | "down";

export default function App(): JSX.Element {
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [healthVersion, setHealthVersion] = useState<string>("");

  useEffect(() => {
    let alive = true;
    const ping = async () => {
      try {
        const data = await fetchHealth();
        if (!alive) return;
        setHealth("ok");
        setHealthVersion(`core v${data.core_version} / api v${data.version}`);
      } catch {
        if (!alive) return;
        setHealth("down");
      }
    };
    void ping();
    const id = window.setInterval(ping, 8000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div className="flex h-full w-full flex-col bg-bg-base text-text-primary">
      <header className="flex items-center justify-between border-b border-border bg-bg-surface/80 px-5 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">
            <span className="font-display text-sm font-bold text-accent-glow">Q</span>
          </div>
          <div>
            <h1 className="font-display text-base font-semibold tracking-wide">
              QuantumLab
            </h1>
            <p className="text-xs text-text-muted">
              An open-source quantum circuit simulator
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <HealthBadge status={health} version={healthVersion} />
        </div>
      </header>

      <Toolbar />

      <CircuitDndProvider>
        <main className="grid min-h-0 flex-1 grid-cols-[260px_1fr_360px] gap-0">
          <aside className="border-r border-border bg-bg-surface/60">
            <GatePalette />
          </aside>
          <section className="flex min-h-0 flex-col">
            <div className="min-h-0 flex-1 overflow-auto">
              <CircuitCanvas />
            </div>
            <CircuitDiagram />
          </section>
          <aside className="flex min-h-0 flex-col overflow-y-auto border-l border-border bg-bg-surface/60">
            <StateVectorPanel />
            <BlochSpherePanel />
            <ProbabilityChart />
            <DensityHeatmap />
          </aside>
        </main>
      </CircuitDndProvider>

      <ELI15Panel />
    </div>
  );
}

function HealthBadge({
  status,
  version,
}: {
  status: HealthStatus;
  version: string;
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
      ? `API connected · ${version}`
      : status === "down"
        ? "API unreachable @127.0.0.1:8765"
        : "Checking API...";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 font-mono text-[10px] ring-1 ${color}`}
    >
      <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${dotColor}`} />
      {label}
    </span>
  );
}
