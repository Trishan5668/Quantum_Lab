import type { CircuitSnapshot } from "./types";

const DB_NAME = "quantumlab-offline";
const STORE_NAME = "pendingCircuitSaves";
const DB_VERSION = 1;

interface QueuedCircuitSave {
  id: string;
  snapshot: CircuitSnapshot;
  queuedAt: string;
}

function openQueue(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T> | void,
): Promise<T | undefined> {
  const db = await openQueue();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode);
    const store = tx.objectStore(STORE_NAME);
    const request = run(store);
    let result: T | undefined;
    if (request) {
      request.onsuccess = () => {
        result = request.result;
      };
      request.onerror = () => reject(request.error);
    }
    tx.oncomplete = () => {
      db.close();
      resolve(result);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

export async function enqueueCircuitSave(snapshot: CircuitSnapshot): Promise<void> {
  const id = snapshot.id ?? crypto.randomUUID();
  await withStore("readwrite", (store) =>
    store.put({ id, snapshot: { ...snapshot, id }, queuedAt: new Date().toISOString() }),
  );
}

export async function getQueuedCircuitSaves(): Promise<QueuedCircuitSave[]> {
  return (await withStore<QueuedCircuitSave[]>("readonly", (store) => store.getAll())) ?? [];
}

export async function removeQueuedCircuitSave(id: string): Promise<void> {
  await withStore("readwrite", (store) => {
    store.delete(id);
  });
}

