import { create } from "zustand";

export type EditorLanguageId = "qiskit" | "qsharp";

export const EDITOR_LANGUAGES: Array<{ id: EditorLanguageId; label: string }> = [
  { id: "qiskit", label: "Python / Qiskit" },
  { id: "qsharp", label: "Q#" },
];

const STARTER_CODE: Record<EditorLanguageId, string> = {
  qiskit: `from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

print(qc)
`,
  qsharp: `operation Main() : Unit {
    use qs = Qubit[2];
    H(qs[0]);
    CNOT(qs[0], qs[1]);
    let r0 = MResetZ(qs[0]);
    let r1 = MResetZ(qs[1]);
    Message($"Bell results: {r0}, {r1}");
}
`,
};

export type OutputState = "idle" | "running" | "success" | "error";

interface EditorStore {
  language: EditorLanguageId;
  codeByLanguage: Record<EditorLanguageId, string>;
  outputState: OutputState;
  outputText: string;
  errorText: string;
  setLanguage: (language: EditorLanguageId) => void;
  setCode: (code: string) => void;
  setRunning: () => void;
  setSuccess: (stdout: string, stderr: string) => void;
  setError: (message: string, stdout?: string) => void;
  resetOutput: () => void;
}

function initialCode(language: EditorLanguageId): string {
  return STARTER_CODE[language];
}

export const useEditorStore = create<EditorStore>((set) => ({
  language: "qiskit",
  codeByLanguage: {
    qiskit: initialCode("qiskit"),
    qsharp: initialCode("qsharp"),
  },
  outputState: "idle",
  outputText: "",
  errorText: "",
  setLanguage: (language) => set({ language }),
  setCode: (code) =>
    set((state) => ({
      codeByLanguage: { ...state.codeByLanguage, [state.language]: code },
    })),
  setRunning: () => set({ outputState: "running", outputText: "", errorText: "" }),
  setSuccess: (stdout, stderr) =>
    set({
      outputState: "success",
      outputText: stderr ? `${stdout}${stdout ? "\n" : ""}[stderr]\n${stderr}` : stdout,
      errorText: "",
    }),
  setError: (message, stdout = "") =>
    set({
      outputState: "error",
      outputText: stdout,
      errorText: message,
    }),
  resetOutput: () => set({ outputState: "idle", outputText: "", errorText: "" }),
}));

export function selectCurrentCode(state: EditorStore): string {
  return state.codeByLanguage[state.language];
}
