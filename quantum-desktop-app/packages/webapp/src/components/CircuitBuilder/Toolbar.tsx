import { useCircuitStore } from "../../store/circuitStore";

export function Toolbar(): JSX.Element {
  const isRunning = useCircuitStore((s) => s.isRunning);
  const stepMode = useCircuitStore((s) => s.stepMode);
  const currentStep = useCircuitStore((s) => s.currentStep);
  const totalSteps = useCircuitStore((s) => s.results?.steps.length ?? 0);
  const lastError = useCircuitStore((s) => s.lastError);
  const gates = useCircuitStore((s) => s.gates);
  const run = useCircuitStore((s) => s.run);
  const setStepMode = useCircuitStore((s) => s.setStepMode);
  const stepForward = useCircuitStore((s) => s.stepForward);
  const stepBackward = useCircuitStore((s) => s.stepBackward);
  const resetSteps = useCircuitStore((s) => s.resetSteps);
  const clearCircuit = useCircuitStore((s) => s.clearCircuit);

  const canRun = !isRunning && gates.length > 0;

  return (
    <div className="flex items-center justify-between border-b border-border bg-bg-surface/40 px-5 py-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!canRun}
          onClick={() => void run()}
          className="inline-flex items-center gap-2 rounded-md bg-accent-quantum px-3 py-1.5 font-mono text-xs font-semibold text-white shadow-sm shadow-accent-quantum/30 transition hover:bg-accent-glow disabled:cursor-not-allowed disabled:opacity-40"
        >
          <PlayIcon /> {isRunning ? "Running..." : "Run Circuit"}
        </button>
        <button
          type="button"
          onClick={() => setStepMode(!stepMode)}
          className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 font-mono text-xs transition ${
            stepMode
              ? "border-accent-glow bg-accent-quantum/15 text-accent-glow"
              : "border-border text-text-secondary hover:border-accent-glow/40"
          }`}
        >
          <StepIcon /> Step Through {stepMode ? "[on]" : "[off]"}
        </button>
        {stepMode && (
          <div className="ml-2 flex items-center gap-1 rounded-md border border-border bg-bg-elevated/60 px-2 py-1 text-[11px] font-mono text-text-secondary">
            <button
              type="button"
              onClick={resetSteps}
              className="rounded px-1.5 py-0.5 hover:bg-bg-base/50"
              title="Reset"
            >
              «
            </button>
            <button
              type="button"
              onClick={stepBackward}
              className="rounded px-1.5 py-0.5 hover:bg-bg-base/50"
              title="Back"
            >
              ‹
            </button>
            <span className="px-2">
              {currentStep}/{totalSteps}
            </span>
            <button
              type="button"
              onClick={stepForward}
              className="rounded px-1.5 py-0.5 hover:bg-bg-base/50"
              title="Forward"
            >
              ›
            </button>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        {lastError && (
          <span className="rounded-md border border-red-500/40 bg-red-500/10 px-2 py-1 font-mono text-[11px] text-red-300">
            {lastError}
          </span>
        )}
        <button
          type="button"
          onClick={clearCircuit}
          className="rounded-md border border-border px-3 py-1.5 font-mono text-xs text-text-secondary transition hover:border-red-500/40 hover:text-red-300"
        >
          Clear
        </button>
      </div>
    </div>
  );
}

function PlayIcon(): JSX.Element {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden>
      <path d="M2 1l7 4-7 4z" />
    </svg>
  );
}
function StepIcon(): JSX.Element {
  return (
    <svg width="12" height="10" viewBox="0 0 12 10" fill="currentColor" aria-hidden>
      <path d="M1 1v8l6-4zM9 1h2v8H9z" />
    </svg>
  );
}
