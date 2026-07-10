import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiClientError, streamExplain, type ExplainRequest } from "../../api";
import { BACKEND_UNAVAILABLE_MESSAGE } from "../../config/api";

import { useCircuitStore } from "../../store/circuitStore";

import { gateMeta } from "../../types";

import { Button } from "../ui/Button";

import { MarkdownText } from "../ui/MarkdownText";



type DockSize = "collapsed" | "normal" | "expanded";



export function ELI15Panel(): JSX.Element {

  const stepMode = useCircuitStore((s) => s.stepMode);

  const currentStep = useCircuitStore((s) => s.currentStep);

  const results = useCircuitStore((s) => s.results);

  const numQubits = useCircuitStore((s) => s.numQubits);



  const [text, setText] = useState("");

  const [status, setStatus] = useState<"idle" | "streaming" | "error">("idle");

  const [error, setError] = useState<string | null>(null);

  const [dockSize, setDockSize] = useState<DockSize>("normal");

  const abortRef = useRef<AbortController | null>(null);



  const trigger = useMemo(() => {

    if (!results || results.steps.length === 0) return null;

    if (stepMode) {

      if (currentStep <= 0) return null;

      const step = results.steps[currentStep - 1];

      if (!step?.state_after) return null;

      const before = currentStep <= 1

        ? zeroState(numQubits)

        : (results.steps[currentStep - 2]?.state_after?.amplitudes ?? zeroState(numQubits));

      return {

        step,

        stateBefore: before,

        stateAfter: step.state_after.amplitudes ?? [],

      };

    }

    const lastIdx = results.steps.length - 1;

    const step = results.steps[lastIdx];

    if (!step?.state_after) return null;

    const before =

      lastIdx === 0

        ? zeroState(numQubits)

        : (results.steps[lastIdx - 1]?.state_after?.amplitudes ?? zeroState(numQubits));

    return {

      step,

      stateBefore: before,

      stateAfter: step.state_after.amplitudes ?? [],

    };

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
      setDockSize((s) => (s === "collapsed" ? "normal" : s));

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

            setError(err.status === 0 ? BACKEND_UNAVAILABLE_MESSAGE : `${err.code}: ${err.message}`);

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



  const handleClear = () => {

    if (abortRef.current) abortRef.current.abort();

    setText("");

    setError(null);

    setStatus("idle");

  };



  const meta = trigger ? gateMeta(trigger.step.gate_type as never) : null;



  const dockClass =

    dockSize === "collapsed"

      ? "eli15-dock-collapsed"

      : dockSize === "expanded"

        ? "eli15-dock-expanded"

        : "eli15-dock-normal";



  return (

    <section

      className={`eli15-dock panel-card mx-3 mb-3 mt-0 flex flex-col overflow-hidden rounded-lg border border-border ${dockClass}`}

      aria-label="ELI15 explanation panel"

    >

      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border/70 px-3 py-2">

        <div className="flex min-w-0 flex-1 items-center gap-2">

          <button

            type="button"

            className="btn btn-ghost btn-sm shrink-0 px-1.5"

            onClick={() =>

              setDockSize((s) =>

                s === "collapsed" ? "normal" : s === "normal" ? "expanded" : "collapsed",

              )

            }

            aria-expanded={dockSize !== "collapsed"}

            aria-label={dockSize === "collapsed" ? "Expand explanation panel" : "Toggle panel size"}

            title={dockSize === "expanded" ? "Collapse" : dockSize === "normal" ? "Expand" : "Show panel"}

          >

            {dockSize === "collapsed" ? "▸" : dockSize === "normal" ? "▾" : "◆"}

          </button>

          <span className="panel-title truncate">ELI15 Explanation</span>

          {trigger && meta && dockSize !== "collapsed" && (

            <span className="hidden truncate font-mono text-[10px] text-text-muted sm:inline">

              {trigger.step.gate_type} → q[{trigger.step.qubit_targets.join(",")}]

            </span>

          )}

          {status === "streaming" && dockSize !== "collapsed" && (

            <span className="font-mono text-[10px] text-accent-glow">streaming…</span>

          )}

        </div>

        {dockSize !== "collapsed" && (

          <div className="flex shrink-0 flex-wrap items-center gap-1">

            <Button

              variant="secondary"

              disabled={!trigger || status === "streaming"}

              loading={status === "streaming"}

              onClick={() => startStream("deep")}

              aria-label="Explain deeper"

            >

              Explain Deeper

            </Button>

            <Button

              variant="secondary"

              disabled={!trigger || status === "streaming"}

              onClick={() => startStream("normal")}

              aria-label="Regenerate explanation"

            >

              Regenerate

            </Button>

            <Button variant="secondary" disabled={!text} onClick={handleCopy} aria-label="Copy explanation">

              Copy

            </Button>

            <Button variant="ghost" disabled={!text && !error} onClick={handleClear} aria-label="Clear explanation">

              Clear

            </Button>

          </div>

        )}

      </header>



      {dockSize !== "collapsed" && (

        <div className="eli15-content px-3 py-2.5">

          {!trigger ? (

            <p className="font-sans text-xs leading-relaxed text-text-muted">

              Run a circuit (or step through one) and a friendly explanation will appear here.

            </p>

          ) : error ? (

            <div className="font-mono text-[11px] leading-relaxed text-red-300">

              <p>{error}</p>

              <p className="pt-1 text-text-muted">

                Set GEMINI_API_KEY (or LLM_PROVIDER=local) on the server to enable streaming explanations.

              </p>

            </div>

          ) : text ? (

            <MarkdownText text={text} />

          ) : (

            <p className="font-sans text-xs leading-relaxed text-text-muted">

              {status === "streaming" ? "Generating explanation…" : "Waiting for explanation…"}

              {status === "streaming" && <span className="ml-0.5 animate-pulse">▌</span>}

            </p>

          )}

        </div>

      )}

    </section>

  );

}



function zeroState(n: number): { real: number; imag: number }[] {

  const dim = 1 << n;

  return Array.from({ length: dim }, (_, i) => ({

    real: i === 0 ? 1 : 0,

    imag: 0,

  }));

}


