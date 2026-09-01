import { useEffect, useMemo, useRef, useState } from "react";
import { BlockMath } from "react-katex";
import { ApiV2ClientError, fetchAIChat, fetchResearchVerification, type AIChatContextRequest } from "../../apiV2";
import { useCircuitStore } from "../../store/circuitStore";
import { usePlatformStore } from "../../store/platformStore";
import type { AIChatMessage, ResearchVerification } from "../../types";
import { buildPhysicsReport } from "../Physics/physicsReport";
import { MarkdownText } from "../ui/MarkdownText";

const QUICK_QUESTIONS = [
  "Explain this circuit",
  "Why does this circuit produce this state?",
  "Explain the last gate",
  "Why is this state entangled?",
  "Explain the mathematics",
  "Explain the physics",
  "What does the Wolfram verification mean?",
];

export function AIAssistantPane(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const initialBasisState = useCircuitStore((s) => s.initialBasisState);
  const gates = useCircuitStore((s) => s.gates);
  const results = useCircuitStore((s) => s.results);
  const resultsV2 = useCircuitStore((s) => s.resultsV2);
  const metrics = useCircuitStore((s) => s.metrics);
  const simulationMode = useCircuitStore((s) => s.simulationMode);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const noiseModel = useCircuitStore((s) => s.noiseModel);
  const noiseProbability = useCircuitStore((s) => s.noiseProbability);
  const t1Us = useCircuitStore((s) => s.t1Us);
  const t2Us = useCircuitStore((s) => s.t2Us);
  const gateTimeNs = useCircuitStore((s) => s.gateTimeNs);
  const learningMode = usePlatformStore((s) => s.learningMode);
  const [messages, setMessages] = useState<AIChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [verification, setVerification] = useState<ResearchVerification | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (learningMode !== "research") {
      setVerification(null);
      return;
    }
    let cancelled = false;
    fetchResearchVerification(
      { numQubits, gates, initialBasisState },
      { simulationMode, noiseEnabled, noiseModel, noiseProbability, t1Us, t2Us, gateTimeNs },
      resultsV2,
    ).then((value) => {
      if (!cancelled) setVerification(value);
    }).catch(() => {
      if (!cancelled) setVerification(null);
    });
    return () => { cancelled = true; };
  }, [gateTimeNs, gates, initialBasisState, learningMode, noiseEnabled, noiseModel, noiseProbability, numQubits, resultsV2, simulationMode, t1Us, t2Us]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  const context = useMemo<AIChatContextRequest>(() => {
    const physicsSections = buildPhysicsReport({
      numQubits,
      initialBasisState,
      gates,
      steps: results?.steps,
      resultsV2,
      metrics,
      learningMode,
      verification,
    });
    const density = resultsV2?.final_density;
    const includeDensity = density && density.dim <= 16;
    const wolframStatus = verification?.status === "SIMULATED" ? "UNAVAILABLE" : verification?.status;
    return {
      learning_mode: learningMode,
      circuit: {
        num_qubits: numQubits,
        initial_basis_state: initialBasisState,
        gates: gates.map((gate) => ({
          id: gate.id,
          gate_type: gate.gateType,
          qubit_targets: gate.qubitTargets,
          params: gate.params,
          time_step: gate.timeStep,
          stack_count: gate.stackCount ?? 1,
        })),
      },
      simulation: {
        mode: resultsV2?.simulation_mode ?? simulationMode,
        noise: { enabled: noiseEnabled, channel: noiseModel, probability: noiseProbability, t1_us: t1Us, t2_us: t2Us, gate_time_ns: gateTimeNs },
        final_state: (resultsV2 ?? results)?.final_state?.amplitudes ?? null,
        measurement_probabilities: (resultsV2 ?? results)?.final_state?.probabilities ?? [],
        density_real: includeDensity ? density.real : null,
        density_imag: includeDensity ? density.imag : null,
        metrics,
      },
      mathematics: {
        source: "QuantumLab mathematical report data",
        metrics,
        circuit_unitary: "not serialized by the current report",
        density_matrix_included: Boolean(includeDensity),
      },
      physics: {
        source: "QuantumLab Physics report",
        sections: physicsSections.map((section) => ({
          title: section.title,
          subtitle: section.subtitle,
          markdown: section.markdown.slice(0, 900),
          latex: section.latex.slice(0, 3),
        })),
      },
      wolfram: {
        status: learningMode === "research" ? wolframStatus ?? "PENDING" : "UNAVAILABLE",
        message: learningMode === "research" ? verification?.message ?? "Wolfram verification is pending." : "Wolfram verification is only used in Research Mode.",
        results: verification?.calculations ?? {},
      },
    };
  }, [gateTimeNs, gates, initialBasisState, learningMode, metrics, noiseEnabled, noiseModel, noiseProbability, numQubits, results, resultsV2, simulationMode, t1Us, t2Us, verification]);

  const summary = `${numQubits} qubit${numQubits === 1 ? "" : "s"}${gates.length ? ` | ${gates.map((gate) => gate.gateType).join(" -> ")}` : " | initial state"}`;
  const verificationStatus = context.wolfram.status;

  const send = async (text = draft) => {
    const message = text.trim();
    if (!message || loading) return;
    const nextMessages = [...messages, { role: "user" as const, content: message }];
    setMessages(nextMessages);
    setDraft("");
    setError(null);
    setLoading(true);
    try {
      const response = await fetchAIChat(message, context);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch (reason) {
      const detail = reason instanceof ApiV2ClientError ? reason.message : "QuantumLab AI could not respond. Please try again.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className={`ai-assistant-pane ${open ? "ai-assistant-pane-open" : ""}`} aria-label="QuantumLab AI assistant">
      <button type="button" className="ai-pane-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        {open ? "Close AI" : "Ask AI"}
      </button>
      <section className="ai-pane-surface">
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-border/70 px-3 py-3">
          <div className="min-w-0">
            <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">Ask QuantumLab</h2>
            <p className="mt-1 truncate font-mono text-[10px] text-text-muted">AI | DeepSeek</p>
            <p className="mt-1 truncate font-mono text-[10px] text-text-muted" title={summary}>{summary}</p>
            <p className={`mt-1 font-mono text-[10px] ${verificationStatus === "VERIFIED" ? "text-emerald-300" : "text-text-muted"}`}>Wolfram: {verificationStatus}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setMessages([]); setError(null); }} disabled={messages.length === 0 && !error}>
            Clear
          </button>
        </header>
        <div className="ai-chat-history">
          {messages.length === 0 && !loading && (
            <div className="ai-quick-questions">
              {QUICK_QUESTIONS.map((question) => (
                <button key={question} type="button" onClick={() => void send(question)}>{question}</button>
              ))}
            </div>
          )}
          {messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={`ai-chat-message ai-chat-message-${message.role}`}>
              <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">{message.role === "user" ? "You" : "QuantumLab AI"}</p>
              {message.role === "assistant" ? <AssistantText text={message.content} /> : <p className="whitespace-pre-wrap text-xs leading-5">{message.content}</p>}
            </article>
          ))}
          {loading && <p className="font-mono text-[11px] text-accent-glow">Thinking...</p>}
          {error && <p className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs leading-5 text-red-200">{error}</p>}
          <div ref={chatEndRef} />
        </div>
        <form className="ai-chat-composer" onSubmit={(event) => { event.preventDefault(); void send(); }}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder="Ask about this circuit..." rows={3} disabled={loading} />
          <button type="submit" className="btn btn-primary btn-sm" disabled={!draft.trim() || loading}>Send</button>
        </form>
      </section>
    </aside>
  );
}

function AssistantText({ text }: { text: string }): JSX.Element {
  const blocks = text.split(/\$\$([\s\S]*?)\$\$/);
  return <>{blocks.map((block, index) => index % 2 === 1 ? <BlockMath key={index} math={block.trim()} /> : block.trim() ? <MarkdownText key={index} text={block} /> : null)}</>;
}
