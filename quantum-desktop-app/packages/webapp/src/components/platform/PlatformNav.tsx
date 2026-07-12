import { Link, useLocation } from "react-router-dom";
import { UserMenu } from "../../auth/UserMenu";
import { REPOSITORY_URL } from "../../config/attribution";

const NAV_LINKS = [
  { to: "/learn", label: "Learn" },
  { to: "/algorithms", label: "Algorithms" },
  { to: "/docs", label: "Docs" },
  { to: "/research", label: "Research" },
  { to: "/api", label: "API" },
  { to: "/about", label: "About" },
] as const;

export function PlatformNav(): JSX.Element {
  const { pathname } = useLocation();

  return (
    <header className="platform-nav sticky top-0 z-50 border-b border-border/80 bg-bg-base/85 backdrop-blur-md">
      <div className="platform-container flex h-14 items-center justify-between gap-4">
        <Link to="/" className="flex min-w-0 items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">
            <span className="font-display text-sm font-bold text-accent-glow">Q</span>
          </div>
          <span className="truncate font-display text-sm font-semibold tracking-wide">
            QuantumLab
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Platform">
          {NAV_LINKS.map(({ to, label }) => {
            const active = pathname === to || pathname.startsWith(`${to}/`);
            return (
              <Link
                key={to}
                to={to}
                className={`rounded-md px-2.5 py-1.5 font-sans text-xs transition-colors ${
                  active
                    ? "bg-accent-quantum/15 text-accent-glow"
                    : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          {REPOSITORY_URL && (
            <a
              href={REPOSITORY_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost btn-sm hidden sm:inline-flex"
            >
              ★ Star on GitHub
            </a>
          )}
          <Link to="/app" className="btn btn-primary btn-sm">
            Launch
          </Link>
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
