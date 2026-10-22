import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../session";
import { SessionNotice } from "./SessionNotice";
import { LockIcon } from "./ui";

const NAV = [
  { to: "/", label: "Home", exact: true },
  { to: "/explore", label: "Explore" },
  { to: "/projects", label: "Projects", match: "/projects" },
  { to: "/experiments", label: "Experiments" },
  { to: "/community", label: "Community" },
  { to: "/docs", label: "Docs" },
] as const;

export function QuantHubShell({ children }: { children: React.ReactNode }): JSX.Element {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { viewer, identity } = useSession();
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const active = (to: string, exact?: boolean) =>
    exact ? pathname === to : pathname === to || pathname.startsWith(`${to}/`);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();
    navigate(trimmed ? `/explore?q=${encodeURIComponent(trimmed)}` : "/explore");
  };

  return (
    <div className="qh-root">
      <header className="qh-topbar">
        <div className="qh-container qh-topbar-inner">
          <Link to="/" className="qh-brand" aria-label="QuantHub home">
            <span className="qh-brand-mark">Q</span>
            <span className="hidden sm:inline">QuantHub</span>
          </Link>

          <form className="qh-search hidden md:flex" onSubmit={submitSearch} role="search">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z" />
            </svg>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search projects…"
              aria-label="Search projects"
            />
          </form>

          <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Primary">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="qh-nav-link"
                data-active={active(item.to, "exact" in item ? item.exact : false)}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Link to="/new" className="qh-btn qh-btn-sm qh-btn-primary" title="New project">
              <span aria-hidden="true">＋</span>
              <span className="hidden sm:inline">New project</span>
            </Link>
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-[#30363d] bg-[#21262d] text-xs font-semibold text-[#e6edf3]"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
                title={viewer?.handle ?? identity.handle}
              >
                {(viewer?.display_name ?? identity.display_name).slice(0, 1).toUpperCase()}
              </button>
              {menuOpen && (
                <div className="qh-menu" role="menu">
                  <div className="px-2 py-2 text-xs text-[#9198a1]">
                    <div className="font-semibold text-[#e6edf3]">
                      {viewer?.display_name ?? identity.display_name}
                    </div>
                    <div>@{viewer?.handle ?? identity.handle}</div>
                    <div className="mt-1 inline-flex items-center gap-1">
                      {viewer?.mode === "authenticated" ? (
                        <span className="qh-badge qh-badge-public">Firebase account</span>
                      ) : viewer?.mode === "local" ? (
                        <span className="qh-badge qh-badge-private">
                          <LockIcon size={10} /> Local session
                        </span>
                      ) : (
                        <span className="qh-badge qh-badge-private">
                          <LockIcon size={10} /> Guest · read only
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="my-1 h-px bg-[#30363d]" />
                  <Link to="/profile" role="menuitem">
                    Your profile
                  </Link>
                  <Link to="/projects" role="menuitem">
                    Your projects
                  </Link>
                  <Link to="/settings" role="menuitem">
                    Settings
                  </Link>
                  <Link to="/welcome" role="menuitem">
                    About QuantHub
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
        <nav
          className="qh-container flex gap-1 overflow-x-auto border-t border-[#21262d] py-1 lg:hidden"
          aria-label="Primary mobile"
        >
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="qh-nav-link"
              data-active={active(item.to, "exact" in item ? item.exact : false)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main>
        <div className="qh-container pt-4">
          <SessionNotice />
        </div>
        {children}
      </main>

      <footer className="mt-12 border-t border-[#21262d] py-6">
        <div className="qh-container flex flex-wrap items-center justify-between gap-3 text-xs text-[#6e7681]">
          <span>© 2026 QuantHub · project-centric quantum research</span>
          <div className="flex flex-wrap gap-4">
            <Link to="/welcome">About</Link>
            <Link to="/docs">Documentation</Link>
            <Link to="/api">API</Link>
            <Link to="/app">Circuit Designer</Link>
            <Link to="/qec">QEC Workbench</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
