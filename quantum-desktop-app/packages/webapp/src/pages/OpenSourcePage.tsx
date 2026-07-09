import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";

export default function OpenSourcePage(): JSX.Element {
  return (
    <>
      <PageMeta
        title="Open Source"
        description="Contributing, roadmap, architecture, and issue templates for QuantumLab."
      />
      <div className="platform-container max-w-3xl py-12 sm:py-16">
        <SectionHeader
          eyebrow="Open Source"
          title="Built in the open"
          subtitle="MIT-licensed core and API. CC-BY-SA education content. Contributions welcome."
        />

        <div className="space-y-6">
          <section className="platform-card p-6">
            <h3 className="font-sans text-lg font-semibold">Repository structure</h3>
            <ul className="mt-3 space-y-2 text-sm text-text-secondary">
              <li><code className="text-accent-glow">quantum-simulator-core/</code> — Python engine</li>
              <li><code className="text-accent-glow">fastapi-server/</code> — HTTP API</li>
              <li><code className="text-accent-glow">quantum-desktop-app/</code> — React platform + Electron</li>
              <li><code className="text-accent-glow">quantum-education-content/</code> — Learning materials</li>
            </ul>
          </section>

          <section className="platform-card p-6">
            <h3 className="font-sans text-lg font-semibold">Contributing</h3>
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">
              Fork, branch, test, and open a pull request. Run pytest for Python and npm test for the webapp.
              See CONTRIBUTING.md in each package.
            </p>
          </section>

          <section className="platform-card p-6">
            <h3 className="font-sans text-lg font-semibold">Roadmap</h3>
            <ul className="mt-3 space-y-2 text-sm text-text-secondary">
              <li>✓ v1 — Circuit builder, visualizations, ELI15</li>
              <li>✓ v2 — Density matrices, noise, metrics</li>
              <li>→ v3 — Mission browser, scoring, dynamic hints</li>
              <li>→ Platform — Unified website, learn, algorithms, docs</li>
            </ul>
          </section>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary btn-md"
          >
            View on GitHub
          </a>
          <Link to="/docs/contributing" className="btn btn-secondary btn-md">
            Contributing Guide
          </Link>
        </div>
      </div>
    </>
  );
}
