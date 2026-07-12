import { Link } from "react-router-dom";
import { CREATOR, REPOSITORY_URL } from "../../config/attribution";

const externalLinkClass = "hover:text-text-primary focus:outline-none focus-visible:text-accent-glow";

export function PlatformFooter(): JSX.Element {
  return (
    <footer className="platform-footer border-t border-border bg-bg-surface/55">
      <div className="platform-container py-10">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-[1.3fr_1fr_1fr_1.2fr]">
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              QuantumLab
            </p>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-text-muted">
              Open-source Interactive Quantum Computing Platform.
            </p>
            <p className="mt-4 text-sm text-text-secondary">
              Created by <span className="text-text-primary">{CREATOR.name}</span>
            </p>
          </div>

          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Platform
            </p>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li><Link to="/app" className="hover:text-text-primary">Simulator</Link></li>
              <li><Link to="/learn" className="hover:text-text-primary">Learn</Link></li>
              <li><Link to="/algorithms" className="hover:text-text-primary">Algorithms</Link></li>
              <li><Link to="/about" className="hover:text-text-primary">About</Link></li>
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
              {REPOSITORY_URL && (
                <li>
                  <a href={REPOSITORY_URL} target="_blank" rel="noopener noreferrer" className={externalLinkClass}>
                    GitHub
                  </a>
                </li>
              )}
            </ul>
          </div>

          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Contact
            </p>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              <li>
                <a href={`mailto:${CREATOR.email}`} className={externalLinkClass}>
                  {CREATOR.email}
                </a>
              </li>
              <li>
                <a href={CREATOR.instagram} target="_blank" rel="noopener noreferrer" className={externalLinkClass}>
                  Instagram
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-border/60 pt-6 font-mono text-[10px] text-text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 QuantumLab</p>
          <p>MIT License · Core & API · CC-BY-SA 4.0 · Education content</p>
        </div>
      </div>
    </footer>
  );
}

