import { useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";

export function LoginModal(): JSX.Element | null {
  const {
    firebaseReady,
    loginOpen,
    closeLogin,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    resetPassword,
    authError,
  } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loginOpen) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      if (mode === "signup") {
        await signUpWithEmail(name.trim(), email.trim(), password);
      } else {
        await signInWithEmail(email.trim(), password);
      }
    } finally {
      setBusy(false);
    }
  };

  const forgot = async () => {
    if (!email.trim()) {
      setStatus("Enter your email first.");
      return;
    }
    setBusy(true);
    try {
      await resetPassword(email.trim());
      setStatus("Password reset email sent.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <div className="auth-panel">
        <button type="button" className="auth-close" onClick={closeLogin} aria-label="Close login">
          x
        </button>
        <div className="auth-brand">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">
            <span className="font-display text-base font-bold text-accent-glow">Q</span>
          </div>
          <div>
            <h2 id="auth-title">QuantumLab</h2>
            <p>Sign in to sync circuits, reports, and preferences.</p>
          </div>
        </div>

        {!firebaseReady && (
          <div className="auth-alert">
            Firebase environment variables are missing. Add your project config to `.env`.
          </div>
        )}

        <button
          type="button"
          className="auth-google"
          disabled={!firebaseReady || busy}
          onClick={() => {
            setBusy(true);
            void signInWithGoogle().finally(() => setBusy(false));
          }}
        >
          <span>G</span>
          Continue with Google
        </button>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          {mode === "signup" && (
            <label>
              Name
              <input value={name} onChange={(event) => setName(event.target.value)} required autoComplete="name" />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
            />
          </label>
          {(authError || status) && (
            <p className={authError ? "auth-error" : "auth-success"}>{authError ?? status}</p>
          )}
          <button type="submit" className="btn btn-primary btn-md w-full" disabled={!firebaseReady || busy}>
            {busy ? "Working..." : mode === "signup" ? "Sign Up" : "Continue with Email"}
          </button>
        </form>

        <div className="auth-actions">
          <button type="button" onClick={() => setMode(mode === "signup" ? "login" : "signup")}>
            {mode === "signup" ? "Use Login" : "Sign Up"}
          </button>
          <button type="button" onClick={() => void forgot()} disabled={busy}>
            Forgot Password
          </button>
        </div>
      </div>
    </div>
  );
}

