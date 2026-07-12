import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { useAuth } from "../auth/AuthProvider";
import { listRecentCircuits } from "../auth/firebaseService";
import type { CircuitSnapshot } from "../auth/types";
import { useCircuitStore } from "../store/circuitStore";

function fmt(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function HistoryPage(): JSX.Element {
  const { user, openLogin } = useAuth();
  const [circuits, setCircuits] = useState<CircuitSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const loadSavedCircuit = useCircuitStore((state) => state.loadSavedCircuit);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    void listRecentCircuits(user.uid)
      .then(setCircuits)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Could not load circuits."))
      .finally(() => setLoading(false));
  }, [user]);

  const reopen = (snapshot: CircuitSnapshot) => {
    loadSavedCircuit({
      numQubits: snapshot.circuitJson.numQubits,
      gates: snapshot.circuitJson.gates,
      simulationMode: snapshot.circuitJson.simulationMode,
      results: snapshot.simulationResult,
      resultsV2: snapshot.simulationResultV2,
      noiseEnabled: snapshot.circuitJson.noiseEnabled,
    });
    navigate("/app");
  };

  return (
    <>
      <PageMeta title="Recent Circuits | QuantumLab" description="Reopen saved QuantumLab circuits." />
      <section className="platform-container py-10">
        <div className="settings-head">
          <div>
            <h1>Recent Circuits</h1>
            <p>Saved runs and drafts from Firestore.</p>
          </div>
          {!user && (
            <button type="button" className="btn btn-primary btn-md" onClick={openLogin}>
              Login
            </button>
          )}
        </div>

        {loading && <p className="panel-placeholder">Loading saved circuits...</p>}
        {error && <p className="auth-error">{error}</p>}
        {!loading && user && circuits.length === 0 && <p className="panel-placeholder">No saved circuits yet.</p>}
        <div className="history-list">
          {circuits.map((snapshot) => (
            <button key={snapshot.id ?? snapshot.timestamp} type="button" className="history-row" onClick={() => reopen(snapshot)}>
              <span className="history-thumb">{snapshot.thumbnail}</span>
              <span>
                <strong>{snapshot.name}</strong>
                <small>Last edited {fmt(snapshot.modifiedAt)}</small>
              </span>
              <span>{snapshot.qubitCount} qubits</span>
              <span>{snapshot.gateCount} gates</span>
              <span>Created {fmt(snapshot.createdAt)}</span>
              <span>Modified {fmt(snapshot.modifiedAt)}</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

