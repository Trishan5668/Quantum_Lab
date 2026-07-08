import { useEffect, useState } from "react";

import { GatePalette } from "./components/CircuitBuilder/GatePalette";

import { CircuitCanvas } from "./components/CircuitBuilder/CircuitCanvas";

import { CircuitDiagram } from "./components/CircuitBuilder/CircuitDiagram";

import { CircuitDndProvider } from "./components/CircuitBuilder/CircuitDndProvider";

import { Toolbar } from "./components/CircuitBuilder/Toolbar";

import { NoiseSettings } from "./components/CircuitBuilder/NoiseSettings";

import { StateVectorPanel } from "./components/Visualizations/StateVectorPanel";

import { BlochSpherePanel } from "./components/Visualizations/BlochSpherePanel";

import { ProbabilityChart } from "./components/Visualizations/ProbabilityChart";

import { DensityHeatmap } from "./components/Visualizations/DensityHeatmap";

import { MetricsPanel } from "./components/Visualizations/MetricsPanel";

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

    <div className="app-shell bg-bg-base text-text-primary">

      <header className="flex shrink-0 items-center justify-between border-b border-border bg-bg-surface/80 px-4 py-2.5 backdrop-blur sm:px-5">

        <div className="flex min-w-0 items-center gap-3">

          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">

            <span className="font-display text-sm font-bold text-accent-glow">Q</span>

          </div>

          <div className="min-w-0">

            <h1 className="truncate font-display text-base font-semibold tracking-wide">

              QuantumLab

            </h1>

            <p className="truncate text-xs text-text-muted">

              An open-source quantum circuit simulator

            </p>

          </div>

        </div>

        <HealthBadge status={health} version={healthVersion} />

      </header>



      <Toolbar />



      <CircuitDndProvider>

        <main className="app-main-grid">

          <aside className="sidebar-left border-r border-border bg-bg-surface/60">

            <div className="sidebar-scroll">

              <GatePalette />

            </div>

            <NoiseSettings />

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

              <StateVectorPanel />

              <BlochSpherePanel />

              <ProbabilityChart />

              <DensityHeatmap />

              <MetricsPanel />

            </div>

          </aside>

        </main>

      </CircuitDndProvider>

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

      className={`inline-flex max-w-[min(100%,280px)] shrink-0 items-center gap-2 truncate rounded-full px-3 py-1 font-mono text-[10px] ring-1 ${color}`}

      title={label}

    >

      <span className={`h-1.5 w-1.5 shrink-0 animate-pulse rounded-full ${dotColor}`} />

      <span className="truncate">{label}</span>

    </span>

  );

}


