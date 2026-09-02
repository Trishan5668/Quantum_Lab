import type { OutputState } from "../../store/editorStore";

interface OutputPaneProps {
  state: OutputState;
  outputText: string;
  errorText: string;
}

export function OutputPane({ state, outputText, errorText }: OutputPaneProps): JSX.Element {
  const isError = state === "error";
  const isSuccess = state === "success";

  return (
    <section className="editor-output-pane flex min-h-[140px] flex-col border-t border-border bg-bg-surface/60">
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-2">
        <p
          className={`font-display text-[10px] uppercase tracking-[0.2em] ${
            isError ? "text-red-300" : isSuccess ? "text-emerald-300" : "text-text-muted"
          }`}
        >
          {isError ? "Error" : isSuccess ? "Output" : "Output"}
        </p>
        {state === "running" && (
          <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-accent-glow">
            <span className="btn-spinner" aria-hidden />
            Running...
          </span>
        )}
      </div>
      <pre
        className={`editor-output-text flex-1 overflow-auto px-4 py-3 font-mono text-xs leading-relaxed ${
          isError ? "text-red-200" : "text-text-secondary"
        }`}
        aria-live="polite"
      >
        {state === "idle" && "Run your program to see output."}
        {state === "running" && "Running..."}
        {state === "success" && (outputText || "(no output)")}
        {state === "error" && (
          <>
            {outputText ? `${outputText}\n\n` : ""}
            {errorText}
          </>
        )}
      </pre>
    </section>
  );
}
