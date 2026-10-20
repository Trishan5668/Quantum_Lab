import { useState } from "react";
import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { loadRecentProjects } from "../client";
import { useSession } from "../session";
import { LockIcon } from "../components/ui";

export default function AccountSettingsPage(): JSX.Element {
  const { viewer, identity, updateIdentity, usingFirebase, loading, error, refresh } = useSession();
  const [handle, setHandle] = useState(identity.handle);
  const [displayName, setDisplayName] = useState(identity.display_name);
  const [email, setEmail] = useState(identity.email ?? "");
  const [saved, setSaved] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [recents, setRecents] = useState(() => loadRecentProjects());

  function save(event: React.FormEvent): void {
    event.preventDefault();
    const cleanHandle = handle.trim().toLowerCase();
    if (!/^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/.test(cleanHandle)) {
      setValidationError(
        "Handles must be 3–40 characters: lowercase letters, digits and hyphens, starting and ending alphanumeric.",
      );
      return;
    }
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setValidationError("Enter a valid email address, or leave the field empty.");
      return;
    }
    setValidationError(null);
    updateIdentity({
      handle: cleanHandle,
      display_name: displayName.trim() || cleanHandle,
      email: email.trim() || null,
    });
    setSaved(true);
  }

  return (
    <>
      <PageMeta title="Account settings" description="Identity and session settings for QuantHub." />
      <div className="qh-container max-w-[760px] py-6">
        <h1 className="mb-1 mt-0 text-[20px] font-semibold">Account settings</h1>
        <p className="qh-subtle mb-5">
          QuantHub works without an account. A local session keeps your handle and display name in
          this browser and is clearly labelled throughout the app.
        </p>

        <div className="mb-4 rounded border border-[#30363d] bg-[#161b22] p-3 text-[12px]">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">Session mode</span>
            {viewer?.mode === "authenticated" ? (
              <span className="qh-badge qh-badge-public">Firebase account</span>
            ) : viewer?.mode === "local" ? (
              <span className="qh-badge qh-badge-private">
                <LockIcon size={10} /> Local session (development only)
              </span>
            ) : (
              <span className="qh-badge qh-badge-private">
                <LockIcon size={10} /> Guest — this server needs a signed-in account to
                create or edit projects
              </span>
            )}
            {loading && <span className="text-[#6e7681]">checking…</span>}
            {error && (
              <span className="text-[#f85149]">
                {error}{" "}
                <button type="button" className="qh-btn qh-btn-sm ml-1" onClick={refresh}>
                  Retry
                </button>
              </span>
            )}
          </div>
          <p className="qh-help mb-0 mt-2">
            {viewer?.mode === "guest" && !usingFirebase
              ? "This deployment does not accept unverified identity headers. Sign in with a Firebase account to create or modify projects."
              : "Local identities are not passwords and are not a security boundary. Private projects rely on the server's authorization rules; do not store sensitive data under a local session you do not control."}
          </p>
        </div>

        <form className="qh-card" onSubmit={save}>
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Local identity</h2>
          </div>
          <div className="qh-card-body">
            <div className="qh-two-col">
              <div className="qh-field">
                <label className="qh-label" htmlFor="handle">Handle</label>
                <input
                  id="handle"
                  className="qh-input qh-mono"
                  value={handle}
                  onChange={(event) => {
                    setHandle(event.target.value);
                    setSaved(false);
                  }}
                  disabled={usingFirebase}
                />
              </div>
              <div className="qh-field">
                <label className="qh-label" htmlFor="display-name">Display name</label>
                <input
                  id="display-name"
                  className="qh-input"
                  value={displayName}
                  onChange={(event) => {
                    setDisplayName(event.target.value);
                    setSaved(false);
                  }}
                  disabled={usingFirebase}
                />
              </div>
            </div>
            <div className="qh-field">
              <label className="qh-label" htmlFor="email">Email (optional)</label>
              <input
                id="email"
                type="email"
                className="qh-input"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setSaved(false);
                }}
                disabled={usingFirebase}
              />
              <p className="qh-help">Used only to label your projects; it is not verified.</p>
            </div>

            {validationError && <div className="qh-form-error mb-3">{validationError}</div>}
            {saved && <p className="mb-2 text-[12px] text-[#3fb950]">Identity saved.</p>}

            <button type="submit" className="qh-btn qh-btn-primary" disabled={usingFirebase}>
              Save identity
            </button>
            {usingFirebase && (
              <p className="qh-help">
                This conversation is signed in with Firebase, so the identity comes from the
                authenticated account and cannot be edited here.
              </p>
            )}
          </div>
        </form>

        <section className="qh-card mt-4">
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Recently opened projects</h2>
            <span className="text-[11px] text-[#6e7681]">stored in this browser</span>
          </div>
          <div className="qh-card-body">
            {recents.length === 0 ? (
              <p className="qh-help m-0">No recent projects recorded on this device.</p>
            ) : (
              <ul className="m-0 list-none space-y-1 p-0 text-[13px]">
                {recents.map((project) => {
                  const [owner, slug] = project.full_name.split("/");
                  return (
                    <li key={project.full_name} className="flex items-center justify-between gap-2">
                      <Link to={`/${owner}/${slug}`} className="text-[#79c0ff]">
                        {project.full_name}
                      </Link>
                      <span className="text-[11px] text-[#6e7681]">{project.visibility}</span>
                    </li>
                  );
                })}
              </ul>
            )}
            {recents.length > 0 && (
              <button
                type="button"
                className="qh-btn qh-btn-sm mt-3"
                onClick={() => {
                  try {
                    window.localStorage.removeItem("quanthub.recentProjects.v1");
                  } catch {
                    /* ignore */
                  }
                  setRecents([]);
                }}
              >
                Clear recent projects
              </button>
            )}
          </div>
        </section>

        <p className="qh-help mt-4">
          Need the full platform? Visit the <Link to="/welcome" className="underline">about page</Link>,
          the <Link to="/docs" className="underline">documentation</Link>, or the{" "}
          <Link to="/app" className="underline">Circuit Designer</Link>.
        </p>
      </div>
    </>
  );
}
