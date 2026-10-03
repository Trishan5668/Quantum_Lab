import {
  arrayUnion,
  collection,
  doc,
  getDoc,
  getDocs,
  increment,
  limit,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
  where,
  writeBatch,
} from "firebase/firestore";
import type { User } from "firebase/auth";
import { firebaseClient } from "../firebase/config";
import type { CircuitState, GatePlacement, SimulationMode } from "../types";
import { gateMeta } from "../types";
import type { CircuitSnapshot, QuantumLabUser, UserPreferences } from "./types";
import { enqueueCircuitSave, getQueuedCircuitSaves, removeQueuedCircuitSave } from "./offlineQueue";

export const defaultPreferences: UserPreferences = {
  theme: "dark",
  defaultSimulationMode: "statevector",
  preferredNotation: "dirac",
  autoSave: true,
  showAdvancedMathematics: false,
  showPhysicsReport: true,
};

function requireDb() {
  if (!firebaseClient) throw new Error("Firebase is not configured.");
  return firebaseClient.db;
}

function iso(value: unknown, fallback = new Date().toISOString()): string {
  if (value && typeof value === "object" && "toDate" in value && typeof value.toDate === "function") {
    return value.toDate().toISOString();
  }
  return typeof value === "string" ? value : fallback;
}

function providerId(user: User): string {
  return user.providerData[0]?.providerId ?? "password";
}

export async function ensureUserDocument(user: User): Promise<QuantumLabUser> {
  const db = requireDb();
  const ref = doc(db, "users", user.uid);
  const existing = await getDoc(ref);
  const now = new Date().toISOString();
  const base = {
    uid: user.uid,
    name: user.displayName ?? user.email?.split("@")[0] ?? "QuantumLab User",
    email: user.email ?? "",
    photoURL: user.photoURL ?? "",
    provider: providerId(user),
    lastLogin: now,
  };

  if (!existing.exists()) {
    await setDoc(ref, {
      ...base,
      createdAt: user.metadata.creationTime ?? now,
      role: "student",
      savedCircuits: [],
      recentCircuits: [],
      favoriteCircuits: [],
      bookmarkedReports: [],
      preferences: defaultPreferences,
      theme: defaultPreferences.theme,
      defaultSimulationMode: defaultPreferences.defaultSimulationMode,
      totalSimulationsRun: 0,
      mostUsedGate: "None",
      favoriteSimulationMode: defaultPreferences.defaultSimulationMode,
      updatedAt: serverTimestamp(),
    });
  } else {
    await updateDoc(ref, {
      ...base,
      updatedAt: serverTimestamp(),
    });
  }

  const fresh = await getDoc(ref);
  return normalizeUser(fresh.data() ?? { ...base, createdAt: now });
}

export function normalizeUser(data: Record<string, unknown>): QuantumLabUser {
  const preferences = {
    ...defaultPreferences,
    ...(typeof data.preferences === "object" && data.preferences ? data.preferences : {}),
  } as UserPreferences;
  return {
    uid: String(data.uid ?? ""),
    name: String(data.name ?? "QuantumLab User"),
    email: String(data.email ?? ""),
    photoURL: String(data.photoURL ?? ""),
    provider: String(data.provider ?? "password"),
    createdAt: iso(data.createdAt),
    lastLogin: iso(data.lastLogin),
    role: data.role === "admin" || data.role === "educator" ? data.role : "student",
    savedCircuits: Array.isArray(data.savedCircuits) ? data.savedCircuits.map(String) : [],
    recentCircuits: Array.isArray(data.recentCircuits) ? data.recentCircuits.map(String) : [],
    favoriteCircuits: Array.isArray(data.favoriteCircuits) ? data.favoriteCircuits.map(String) : [],
    bookmarkedReports: Array.isArray(data.bookmarkedReports) ? data.bookmarkedReports.map(String) : [],
    preferences,
    theme: preferences.theme,
    defaultSimulationMode: preferences.defaultSimulationMode,
    totalSimulationsRun: Number(data.totalSimulationsRun ?? 0),
    mostUsedGate: String(data.mostUsedGate ?? "None"),
    favoriteSimulationMode: (data.favoriteSimulationMode as SimulationMode) ?? preferences.defaultSimulationMode,
  };
}

export async function updateUserPreferences(uid: string, preferences: UserPreferences): Promise<void> {
  const db = requireDb();
  const batch = writeBatch(db);
  batch.set(
    doc(db, "users", uid),
    {
      preferences,
      theme: preferences.theme,
      defaultSimulationMode: preferences.defaultSimulationMode,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
  batch.set(
    doc(db, "preferences", uid),
    {
      userId: uid,
      ...preferences,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
  await batch.commit();
}

function circuitName(gates: GatePlacement[]): string {
  if (gates.length === 0) return "Empty circuit";
  const names = gates.slice(0, 4).map((gate) => gate.gateType).join(" - ");
  return `${names}${gates.length > 4 ? " ..." : ""}`;
}

function buildThumbnail(state: CircuitState): string {
  const rows = Array.from({ length: state.numQubits }, (_, qubit) => {
    const symbols = state.gates
      .filter((gate) => gate.qubitTargets.includes(qubit))
      .sort((a, b) => a.timeStep - b.timeStep)
      .map((gate) => gate.gateType)
      .join("-");
    return `q${qubit}:${symbols || "--"}`;
  });
  return rows.join("|");
}

function gateSequence(gates: GatePlacement[]): string[] {
  return [...gates]
    .sort((a, b) => a.timeStep - b.timeStep)
    .map((gate) => {
      const label = gateMeta(gate.gateType).label;
      return `${label} q[${gate.qubitTargets.join(", ")}]`;
    });
}

function favoriteModeFromState(mode: SimulationMode): SimulationMode {
  return mode;
}

function mostUsedGate(gates: GatePlacement[]): string {
  if (gates.length === 0) return "None";
  const counts = gates.reduce<Record<string, number>>((acc, gate) => {
    acc[gate.gateType] = (acc[gate.gateType] ?? 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "None";
}

function mathReport(state: CircuitState): string {
  const probabilities = state.results?.final_state.probabilities ?? [];
  const labels = state.results?.final_state.basis_labels ?? [];
  const terms = probabilities
    .map((probability, index) => ({ probability, label: labels[index] ?? String(index) }))
    .filter(({ probability }) => probability > 1e-8)
    .slice(0, 12)
    .map(({ label, probability }) => `${label}: ${probability.toFixed(6)}`);
  return [
    `${state.numQubits} qubit circuit`,
    `initial basis: |${state.initialBasisState}>`,
    `${state.gates.length} gates`,
    `mode: ${state.simulationMode}`,
    `probabilities: ${terms.length ? terms.join(", ") : "not simulated"}`,
  ].join("\n");
}

function physicsReport(state: CircuitState): string {
  const density = state.resultsV2?.final_density ? "density matrix available" : "statevector-derived density";
  const noise = state.noiseEnabled ? `${state.noiseModel} noise p=${state.noiseProbability}` : "ideal evolution";
  return [
    `Circuit starts in |${state.initialBasisState}> and evolves ${state.numQubits} qubit${state.numQubits === 1 ? "" : "s"} under ${noise}.`,
    `Final representation: ${density}.`,
    `Metrics: fidelity=${state.metrics?.fidelity?.fidelity ?? "n/a"}, entropy=${state.metrics?.entropy?.entropy ?? "n/a"}, purity=${state.metrics?.purity?.purity ?? state.resultsV2?.purity ?? "n/a"}.`,
  ].join("\n");
}

export function buildCircuitSnapshot(
  uid: string,
  state: CircuitState,
  source: CircuitSnapshot["source"],
  existingId?: string,
): CircuitSnapshot {
  const now = new Date().toISOString();
  return {
    id: existingId,
    name: circuitName(state.gates),
    userId: uid,
    circuitJson: {
      numQubits: state.numQubits,
      initialBasisState: state.initialBasisState,
      selectedBasisState: state.selectedBasisState,
      gates: state.gates,
      simulationMode: state.simulationMode,
      noiseEnabled: state.noiseEnabled,
    },
    gateSequence: gateSequence(state.gates),
    simulationResult: state.results,
    simulationResultV2: state.resultsV2,
    timestamp: now,
    qubitCount: state.numQubits,
    gateCount: state.gates.length,
    statevector: state.results?.final_state ?? null,
    densityMatrix: state.resultsV2?.final_density ?? null,
    measurementProbabilities: state.results?.final_state.probabilities ?? [],
    explanationCache: {
      summary: state.results ? "Simulation completed and cached for reopening." : "Circuit draft saved before simulation.",
    },
    physicsReport: physicsReport(state),
    mathReport: mathReport(state),
    createdAt: now,
    modifiedAt: now,
    thumbnail: buildThumbnail(state),
    source,
  };
}

export async function saveCircuitSnapshot(snapshot: CircuitSnapshot): Promise<string> {
  if (!navigator.onLine) {
    await enqueueCircuitSave(snapshot);
    return snapshot.id ?? "";
  }
  const db = requireDb();
  const id = snapshot.id ?? crypto.randomUUID();
  const simulationRef = doc(db, "simulations", id);
  const recentRef = doc(db, "recentCircuits", id);
  const userRef = doc(db, "users", snapshot.userId);
  const reportsRef = doc(db, "reports", id);

  const payload = {
    ...snapshot,
    id,
    ownerUid: snapshot.userId,
    updatedAt: serverTimestamp(),
  };
  const recentPayload = {
    id,
    ownerUid: snapshot.userId,
    userId: snapshot.userId,
    name: snapshot.name,
    thumbnail: snapshot.thumbnail,
    lastEdited: snapshot.modifiedAt,
    created: snapshot.createdAt,
    modified: snapshot.modifiedAt,
    qubits: snapshot.qubitCount,
    gates: snapshot.gateCount,
    circuitJson: snapshot.circuitJson,
    updatedAt: serverTimestamp(),
  };

  const batch = writeBatch(db);
  batch.set(simulationRef, payload, { merge: true });
  batch.set(recentRef, recentPayload, { merge: true });
  batch.set(
    reportsRef,
    {
      id,
      ownerUid: snapshot.userId,
      userId: snapshot.userId,
      simulationId: id,
      physicsReport: snapshot.physicsReport,
      mathReport: snapshot.mathReport,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
  batch.set(
    userRef,
    {
      savedCircuits: arrayUnion(id),
      recentCircuits: arrayUnion(id),
      totalSimulationsRun: snapshot.source === "run" ? increment(1) : increment(0),
      mostUsedGate: mostUsedGate(snapshot.circuitJson.gates),
      favoriteSimulationMode: favoriteModeFromState(snapshot.circuitJson.simulationMode),
      lastLogin: new Date().toISOString(),
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
  await batch.commit();
  return id;
}

export async function syncQueuedCircuitSaves(uid: string): Promise<void> {
  if (!navigator.onLine || !firebaseClient) return;
  const queued = await getQueuedCircuitSaves();
  for (const item of queued.filter((entry) => entry.snapshot.userId === uid)) {
    await saveCircuitSnapshot(item.snapshot);
    await removeQueuedCircuitSave(item.id);
  }
}

export async function listRecentCircuits(uid: string): Promise<CircuitSnapshot[]> {
  const db = requireDb();
  const q = query(
    collection(db, "simulations"),
    where("ownerUid", "==", uid),
    orderBy("modifiedAt", "desc"),
    limit(50),
  );
  const snapshot = await getDocs(q);
  return snapshot.docs.map((entry) => entry.data() as CircuitSnapshot);
}
