import { useCircuitStore } from "../../store/circuitStore";
import { SimulationModeToggle } from "./SimulationModeToggle";
import { Button } from "../ui/Button";
import type { SaveStatus } from "../../auth/types";

export function Toolbar({
  compact = false,
  onSave,
  saveStatus = "idle",
}: {
  compact?: boolean;
  onSave?: () => void;
  saveStatus?: SaveStatus;
}): JSX.Element {
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
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-bg-surface/40 px-4 py-2 sm:px-5">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size={compact ? "sm" : "md"}
          disabled={!canRun}
          loading={isRunning}
          onClick={() => void run()}
          aria-label="Run circuit"
        >
          <PlayIcon /> {isRunning ? "Running…" : compact ? "Run" : "Run Circuit"}
        </Button>
        {!compact && (
        <>
        <Button
          variant={stepMode ? "secondary" : "ghost"}
          size="md"
          onClick={() => setStepMode(!stepMode)}
          aria-pressed={stepMode}
          aria-label="Toggle step through mode"
          className={stepMode ? "border-accent-glow bg-accent-quantum/15 text-accent-glow" : ""}
        >
          <StepIcon /> Step {stepMode ? "On" : "Off"}
        </Button>
        {stepMode && (
          <div
            className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated/60 px-1.5 py-1 font-mono text-[11px] text-text-secondary"
            role="group"
            aria-label="Step controls"
          >
            <Button variant="ghost" onClick={resetSteps} aria-label="Reset steps" className="px-1.5">
              «
            </Button>
            <Button variant="ghost" onClick={stepBackward} aria-label="Previous step" className="px-1.5">
              ‹
            </Button>
            <span className="min-w-[3rem] px-1 text-center" aria-live="polite">
              {currentStep}/{totalSteps}
            </span>
            <Button variant="ghost" onClick={stepForward} aria-label="Next step" className="px-1.5">
              ›
            </Button>
          </div>
        )}
        </>
        )}
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-2">
        {!compact && <SimulationModeToggle />}
        {!compact && onSave && (
          <Button
            variant="secondary"
            size="md"
            onClick={onSave}
            loading={saveStatus === "saving"}
            aria-label="Save circuit"
          >
            Save
          </Button>
        )}
        {lastError && (
          <span
            className="max-w-xs truncate rounded-md border border-red-500/40 bg-red-500/10 px-2 py-1 font-mono text-[11px] text-red-300"
            title={lastError}
            role="alert"
          >
            {lastError}
          </span>
        )}
        {!compact && (
        <Button variant="danger" size="md" onClick={clearCircuit} aria-label="Clear circuit">
          Clear
        </Button>
        )}
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
