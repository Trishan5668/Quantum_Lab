import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { useAuth } from "../auth/AuthProvider";

function formatDate(value: string | undefined): string {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

export default function ProfilePage(): JSX.Element {
  const { profile, user, openLogin } = useAuth();
  const name = profile?.name ?? user?.displayName ?? "QuantumLab User";
  const photo = profile?.photoURL || user?.photoURL || "";

  return (
    <>
      <PageMeta title="Profile | QuantumLab" description="QuantumLab account profile and simulator activity." />
      <section className="platform-container py-10">
        {!user ? (
          <div className="profile-empty">
            <h1>Profile</h1>
            <p>Sign in to view saved circuits and account activity.</p>
            <button type="button" className="btn btn-primary btn-md" onClick={openLogin}>
              Login
            </button>
          </div>
        ) : (
          <div className="profile-grid">
            <div className="profile-hero">
              <div className="profile-photo">
                {photo ? <img src={photo} alt="" referrerPolicy="no-referrer" /> : <span>{name.slice(0, 1)}</span>}
              </div>
              <div>
                <h1>{name}</h1>
                <p>{profile?.email ?? user.email}</p>
                <span>Joined {formatDate(profile?.createdAt)}</span>
              </div>
            </div>
            <div className="profile-stats">
              <Metric label="Saved circuits" value={profile?.savedCircuits.length ?? 0} />
              <Metric label="Total simulations run" value={profile?.totalSimulationsRun ?? 0} />
              <Metric label="Most-used gate" value={profile?.mostUsedGate ?? "None"} />
              <Metric label="Favorite mode" value={profile?.favoriteSimulationMode ?? "statevector"} />
              <Metric label="Account created" value={formatDate(profile?.createdAt)} />
            </div>
            <div className="profile-actions">
              <Link to="/history" className="btn btn-secondary btn-md">
                Recent Circuits
              </Link>
              <Link to="/settings" className="btn btn-primary btn-md">
                Settings
              </Link>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string | number }): JSX.Element {
  return (
    <div className="profile-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

