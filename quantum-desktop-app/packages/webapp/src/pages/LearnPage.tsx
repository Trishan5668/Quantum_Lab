import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";

export default function LearnPage(): JSX.Element {
  return (
    <>
      <PageMeta title="Learn Quantum Computing" description="Quantum computing lessons, references, and a research-capable simulator." />
      <div className="platform-container py-12 sm:py-16">
        <SectionHeader eyebrow="Learn" title="One complete quantum workspace." subtitle="Use the same simulator for circuits, analysis, physics, and mathematics." />
        <div className="platform-card p-6 text-sm leading-relaxed text-text-secondary">
          Build circuits and inspect state evolution, density matrices, noise, entanglement, physics, mathematics, and execution reports in one workspace.
        </div>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/app" className="btn btn-primary btn-md">Open Simulator</Link>
          <Link to="/algorithms" className="btn btn-secondary btn-md">Browse Algorithms</Link>
          <Link to="/docs" className="btn btn-ghost btn-md">Read Documentation</Link>
        </div>
      </div>
    </>
  );
}
