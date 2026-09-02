import { useCallback } from "react";
import { Link } from "react-router-dom";
import { CircuitPreview } from "../components/editor/CircuitPreview";
import { CodeEditor } from "../components/editor/CodeEditor";
import { OutputPane } from "../components/editor/OutputPane";
import { PageMeta } from "../components/platform/PageMeta";
import { SimulatorNavLink } from "../components/platform/WorkspaceNavLinks";
import { Button } from "../components/ui/Button";
import { runEditorCode } from "../apiV2";
import { ApiV2ClientError, type EditorLanguageId as ApiEditorLanguageId } from "../apiV2";
import { useCircuitPersistence } from "../auth/useCircuitPersistence";
import { UserMenu } from "../auth/UserMenu";
import {
  EDITOR_LANGUAGES,
  selectCurrentCode,
  useEditorStore,
  type EditorLanguageId,
} from "../store/editorStore";

export default function EditorPage(): JSX.Element {
  const language = useEditorStore((s) => s.language);
  const setLanguage = useEditorStore((s) => s.setLanguage);
  const code = useEditorStore(selectCurrentCode);
  const setCode = useEditorStore((s) => s.setCode);
  const outputState = useEditorStore((s) => s.outputState);
  const outputText = useEditorStore((s) => s.outputText);
  const errorText = useEditorStore((s) => s.errorText);
  const setRunning = useEditorStore((s) => s.setRunning);
  const setSuccess = useEditorStore((s) => s.setSuccess);
  const setError = useEditorStore((s) => s.setError);
  const { saveStatus } = useCircuitPersistence();

  const running = outputState === "running";

  const handleRun = useCallback(async () => {
    if (!code.trim() || running) return;
    setRunning();
    try {
      const result = await runEditorCode(language as ApiEditorLanguageId, code);
      if (result.status === "success") {
        setSuccess(result.stdout, result.stderr);
      } else {
        setError(result.stderr || "Execution failed.", result.stdout);
      }
    } catch (error) {
      const message =
        error instanceof ApiV2ClientError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Failed to run program.";
      setError(message);
    }
  }, [code, language, running, setError, setRunning, setSuccess]);

  return (
    <>
      <PageMeta
        title="QuantumLab Editor"
        description="Write and run Qiskit and Q# quantum programs with a live circuit preview."
      />
      <div className="editor-shell bg-bg-base text-text-primary">
        <header className="flex shrink-0 items-center justify-between border-b border-border bg-bg-surface/80 px-4 py-2.5 backdrop-blur sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <Link to="/" className="flex min-w-0 items-center gap-3 hover:opacity-90">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-quantum/15 ring-1 ring-accent-quantum/40">
                <span className="font-display text-sm font-bold text-accent-glow">Q</span>
              </div>
              <div className="min-w-0">
                <h1 className="truncate font-display text-base font-semibold tracking-wide">
                  QuantumLab
                </h1>
                <p className="truncate text-xs text-text-muted">Code editor workspace</p>
              </div>
            </Link>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {saveStatus !== "idle" && (
              <span className="hidden rounded-full border border-border bg-bg-elevated/50 px-2.5 py-1 font-mono text-[10px] text-text-muted sm:inline-flex">
                {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved ✓" : saveStatus}
              </span>
            )}
            <SimulatorNavLink />
            <label className="hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[0.15em] text-text-muted sm:flex">
              <span>Select Language</span>
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value as EditorLanguageId)}
                className="rounded-md border border-border bg-bg-elevated px-2 py-1.5 font-mono text-[11px] text-text-primary outline-none focus:ring-2 focus:ring-accent-quantum/40"
                aria-label="Select programming language"
              >
                {EDITOR_LANGUAGES.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <Button
              variant="primary"
              onClick={() => void handleRun()}
              loading={running}
              disabled={!code.trim() || running}
              aria-label="Run program"
            >
              {running ? "Running..." : "Run"}
            </Button>
            <UserMenu />
          </div>
        </header>

        <div className="editor-main-grid min-h-0 flex-1">
          <aside className="editor-circuit-column min-h-0 border-r border-border bg-bg-surface/60">
            <CircuitPreview />
          </aside>
          <section className="editor-code-column flex min-h-0 flex-col">
            <div className="min-h-0 flex-1">
              <CodeEditor language={language} value={code} onChange={setCode} />
            </div>
            <OutputPane state={outputState} outputText={outputText} errorText={errorText} />
          </section>
        </div>
      </div>
    </>
  );
}
