import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { ContentCard } from "../components/platform/ContentCard";

const LiveSimulatorEmbed = lazy(
  () => import("../components/platform/LiveSimulatorEmbed").then((m) => ({ default: m.LiveSimulatorEmbed })),
);

const FEATURES = [
  {
    title: "Circuit Builder",
    description: "Drag-and-drop gates with step-through simulation and export.",
    to: "/app",
  },
  {
    title: "Visualizations",
    description: "Bloch sphere, probability charts, density heatmaps, and metrics.",
    to: "/app",
  },
  {
    title: "AI Tutor",
    description: "ELI15 explanations streamed as you build and run circuits.",
    to: "/app",
  },
  {
    title: "Research Mode",
    description: "Density matrices, noise channels, fidelity, and entanglement entropy.",
    to: "/research",
  },
  {
    title: "Algorithm Library",
    description: "Bell, GHZ, Grover, QFT, and more — open directly in the simulator.",
    to: "/algorithms",
  },
  {
    title: "Open Source",
    description: "MIT core, CC-BY-SA education. Built for students and researchers.",
    to: "/opensource",
  },
] as const;

export default function LandingPage(): JSX.Element {
  return (
    <>
      <PageMeta
        title="QuantumLab — The Open Source Quantum Computing Platform"
        description="Build, visualize, and understand quantum computing. From your first qubit to quantum research."
      />

      <section className="platform-container relative py-16 sm:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="mx-auto max-w-4xl text-center"
        >
          <p className="mb-4 font-display text-[10px] font-semibold uppercase tracking-[0.3em] text-accent-measure">
            Open Source · Production Quality
          </p>
          <h1 className="font-sans text-4xl font-semibold leading-[1.1] tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
            The Open Source
            <br />
            <span className="bg-gradient-to-r from-accent-glow to-accent-measure bg-clip-text text-transparent">
              Quantum Computing Platform
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-text-secondary sm:text-lg">
            <span className="text-text-primary">Build.</span>{" "}
            <span className="text-text-primary">Visualize.</span>{" "}
            <span className="text-text-primary">Understand.</span>
            <br />
            From your first qubit to quantum research.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/app" className="btn btn-primary btn-md">
              Launch QuantumLab
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary btn-md"
            >
              GitHub
            </a>
            <Link to="/app" className="btn btn-ghost btn-md">
              Demo
            </Link>
          </div>
        </motion.div>
      </section>

      <section className="platform-container pb-16 sm:pb-24">
        <SectionHeader
          eyebrow="Live"
          title="Real simulator, right on the homepage"
          subtitle="Not a mockup. The same React components that power the full IDE."
        />
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <Suspense
            fallback={
              <div className="live-simulator-embed flex h-[360px] items-center justify-center">
                <span className="font-mono text-xs text-text-muted">Loading simulator…</span>
              </div>
            }
          >
            <LiveSimulatorEmbed />
          </Suspense>
        </motion.div>
      </section>

      <section className="border-t border-border/60 bg-bg-surface/30 py-16 sm:py-20">
        <div className="platform-container">
          <SectionHeader
            eyebrow="Platform"
            title="Everything in one ecosystem"
            subtitle="Simulator, learning, algorithms, documentation, and research — unified design language."
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <ContentCard key={f.title} title={f.title} description={f.description} to={f.to} />
            ))}
          </div>
        </div>
      </section>

      <section className="platform-container py-16 sm:py-20">
        <SectionHeader
          eyebrow="Progressive disclosure"
          title="Learn at your own depth"
          subtitle="The simulator UI stays identical. Only the depth of information changes."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { layer: "Explore", desc: "Visual learning. No math required." },
            { layer: "Understand", desc: "State vectors, amplitudes, tensors." },
            { layer: "Intuition", desc: "Phase, interference, entanglement." },
            { layer: "Research", desc: "Density matrices, noise, entropy." },
          ].map((item) => (
            <div key={item.layer} className="platform-card p-5">
              <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-accent-glow">
                {item.layer}
              </p>
              <p className="mt-2 text-sm text-text-secondary">{item.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 text-center">
          <Link to="/learn" className="btn btn-secondary btn-md">
            Start Learning
          </Link>
        </div>
      </section>
    </>
  );
}
