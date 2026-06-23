import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError, streamExplain, type ExplainRequest } from "../../api";
import { useCircuitStore } from "../../store/circuitStore";
import { gateMeta } from "../../types";

export function ELI15Panel(): JSX.Element {
  const stepMode = useCircuitStore((s) => s.stepMode);
  const currentStep = useCircuitStore((s) => s.currentStep);
  const results = useCircuitStore((s) => s.results);
  const numQubits = useCircuitStore((s) => s.numQubits);

  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "streaming" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const trigger = useMemo(() => {
    if (!results || results.steps.length === 0) return null;
    if (stepMode) {
      if (currentStep <= 0) return null;
      const step = results.steps[currentStep - 1];
      if (!step) return null;
      const before = currentStep <= 1
        ? zeroState(numQubits)
        : results.steps[currentStep - 2].state_after.amplitudes;
      return {
        step,
        stateBefore: before,
        stateAfter: step.state_after.amplitudes,
      };
    }
    const lastIdx = results.steps.length - 1;
    const step = results.steps[lastIdx];
    const before =
      lastIdx === 0
        ? zeroState(numQubits)
        : results.steps[lastIdx - 1].state_after.amplitudes;
    return { step, stateBefore: before, stateAfter: step.state_after.amplitudes };
  }, [results, stepMode, currentStep, numQubits]);

  const startStream = useCallback(
    (mode: ExplainRequest["mode"]) => {
      if (!trigger) return;
      if (abortRef.current) abortRef.current.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setText("");
      setError(null);
      setStatus("streaming");
      const req: ExplainRequest = {
        gate: trigger.step.gate_type,
        qubit:
          trigger.step.qubit_targets.length === 1
            ? trigger.step.qubit_targets[0]
            : null,
        qubits:
          trigger.step.qubit_targets.length === 2
            ? trigger.step.qubit_targets
            : null,
        state_before: trigger.stateBefore,
        state_after: trigger.stateAfter,
        num_qubits: numQubits,
        context: stepMode ? "step_through" : "full_run_last_gate",
        mode,
      };
      void streamExplain(
        req,
        {
          onToken: (t) => setText((prev) => prev + t),
          onDone: () => setStatus("idle"),
          onError: (err: ApiClientError) => {
            setStatus("error");
            setError(`${err.code}: ${err.message}`);
          },
        },
        ctrl.signal,
      );
    },
    [trigger, numQubits, stepMode],
  );

  useEffect(() => {
    if (!trigger) {
      setText("");
      setError(null);
      setStatus("idle");
      return;
    }
    startStream("normal");
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [trigger?.step.gate_id, trigger, startStream]);

  const handleCopy = () => {
    if (!text) return;
    void navigator.clipboard.writeText(text);
  };

  const meta = trigger ? gateMeta(trigger.step.gate_type as never) : null;

  return (
    <section className="h-[160px] shrink-0 border-t border-border bg-bg-surface/70">
      <div className="flex h-full flex-col">
        <header className="flex items-center justify-between border-b border-border/70 px-5 py-2">
          <div className="flex items-center gap-3">
            <span className="font-display text-[11px] uppercase tracking-[0.2em] text-text-secondary">
              ELI15 Explanation
            </span>
            {trigger && meta && (
              <span className="font-mono text-[11px] text-text-secondary">
                Applied:{" "}
                <span style={{ color: meta.color }}>{trigger.step.gate_type}</span>{" "}
                to q[{trigger.step.qubit_targets.join(",")}]
              </span>
            )}
            {status === "streaming" && (
              <span className="font-mono text-[10px] text-accent-glow">streaming…</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={!trigger || status === "streaming"}
              onClick={() => startStream("deep")}
              className="rounded-md border border-border px-2 py-1 font-mono text-[10px] text-text-secondary hover:border-accent-glow hover:text-accent-glow disabled:opacity-30"
            >
              ⚡ Explain deeper
            </button>
            <button
              type="button"
              disabled={!text}
              onClick={handleCopy}
              className="rounded-md border border-border px-2 py-1 font-mono text-[10px] text-text-secondary hover:border-accent-glow hover:text-accent-glow disabled:opacity-30"
            >
              📋 Copy
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {!trigger ? (
            <p className="font-sans text-[12px] leading-relaxed text-text-muted">
              Run a circuit (or step through one) and a friendly explanation will
              appear here.
            </p>
          ) : error ? (
            <p className="font-mono text-[11px] leading-relaxed text-red-300">
              {error}
              <span className="block pt-1 text-text-muted">
                Set GEMINI_API_KEY (or LLM_PROVIDER=local) on the server to enable streaming explanations.
              </span>
            </p>
          ) : (
            <p className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-text-secondary">
              {text}
              {status === "streaming" && <span className="ml-0.5 animate-pulse">▌</span>}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function zeroState(n: number): { real: number; imag: number }[] {
  const dim = 1 << n;
  const amps = Array.from({ length: dim }, (_, i) => ({
    real: i === 0 ? 1 : 0,
    imag: 0,
  }));
  return amps;
}
