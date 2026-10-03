import { useEffect, useState } from "react";
import { PageMeta } from "../components/platform/PageMeta";
import { useAuth } from "../auth/AuthProvider";
import { defaultPreferences } from "../auth/firebaseService";
import type { UserPreferences } from "../auth/types";

export default function SettingsPage(): JSX.Element {
  const { profile, user, openLogin, savePreferences } = useAuth();
  const [preferences, setPreferences] = useState<UserPreferences>(profile?.preferences ?? defaultPreferences);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    setPreferences(profile?.preferences ?? defaultPreferences);
  }, [profile?.preferences]);

  const save = async () => {
    setStatus("Saving...");
    await savePreferences(preferences);
    setStatus("Saved");
  };

  return (
    <>
      <PageMeta title="Settings | QuantumLab" description="QuantumLab account and simulator preferences." />
      <section className="platform-container py-10">
        <div className="settings-head">
          <div>
            <h1>Settings</h1>
            <p>Sync defaults across devices.</p>
          </div>
          {!user ? (
            <button type="button" className="btn btn-primary btn-md" onClick={openLogin}>
              Login
            </button>
          ) : (
            <button type="button" className="btn btn-primary btn-md" onClick={() => void save()}>
              Save
            </button>
          )}
        </div>

        <div className="settings-grid">
          <label>
            Theme
            <select
              value={preferences.theme}
              onChange={(event) => setPreferences({ ...preferences, theme: event.target.value as UserPreferences["theme"] })}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </label>
          <label>
            Preferred notation
            <select
              value={preferences.preferredNotation}
              onChange={(event) =>
                setPreferences({ ...preferences, preferredNotation: event.target.value as UserPreferences["preferredNotation"] })
              }
            >
              <option value="dirac">Dirac</option>
              <option value="matrix">Matrix</option>
              <option value="bloch">Bloch</option>
            </select>
          </label>
          <label>
            Default simulation mode
            <select
              value={preferences.defaultSimulationMode}
              onChange={(event) =>
                setPreferences({
                  ...preferences,
                  defaultSimulationMode: event.target.value as UserPreferences["defaultSimulationMode"],
                })
              }
            >
              <option value="statevector">Statevector</option>
              <option value="density">Density</option>
            </select>
          </label>
        </div>

        <div className="settings-toggles">
          <Toggle label="Auto-save" checked={preferences.autoSave} onChange={(autoSave) => setPreferences({ ...preferences, autoSave })} />
          <Toggle
            label="Show advanced mathematics"
            checked={preferences.showAdvancedMathematics}
            onChange={(showAdvancedMathematics) => setPreferences({ ...preferences, showAdvancedMathematics })}
          />
          <Toggle
            label="Show physics report"
            checked={preferences.showPhysicsReport}
            onChange={(showPhysicsReport) => setPreferences({ ...preferences, showPhysicsReport })}
          />
        </div>
        {status && <p className="settings-status">{status}</p>}
      </section>
    </>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}): JSX.Element {
  return (
    <label className="settings-toggle">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}
