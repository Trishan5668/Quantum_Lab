import { Link } from "react-router-dom";

export function PlatformFooter(): JSX.Element {
  return (
    <footer className="platform-footer border-t border-border bg-bg-surface/40">
      <div className="platform-container py-10">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Platform
            </p>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li><Link to="/app" className="hover:text-text-primary">Simulator</Link></li>
              <li><Link to="/learn" className="hover:text-text-primary">Learn</Link></li>
              <li><Link to="/algorithms" className="hover:text-text-primary">Algorithms</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Resources
            </p>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li><Link to="/docs" className="hover:text-text-primary">Documentation</Link></li>
              <li><Link to="/research" className="hover:text-text-primary">Research</Link></li>
              <li><Link to="/api" className="hover:text-text-primary">API Reference</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Community
            </p>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li><Link to="/opensource" className="hover:text-text-primary">Contributing</Link></li>
              <li><Link to="/community" className="hover:text-text-primary">Community</Link></li>
              <li><Link to="/blog" className="hover:text-text-primary">Blog</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              QuantumLab
            </p>
            <p className="mt-3 text-sm leading-relaxed text-text-muted">
              The open-source quantum computing platform. Build, visualize, and understand — from your first qubit to research.
            </p>
          </div>
        </div>
        <p className="mt-10 border-t border-border/60 pt-6 font-mono text-[10px] text-text-muted">
          MIT License · Core &amp; API · CC-BY-SA 4.0 · Education content
        </p>
      </div>
    </footer>
  );
}
