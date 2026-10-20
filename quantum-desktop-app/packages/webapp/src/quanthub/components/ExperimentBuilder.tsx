import { useMemo, useState } from "react";
import { api, ApiError } from "../client";
import type { ExperimentSpec, ExperimentTemplate } from "../types";

interface ValidationPayload {
  protocol: Record<string, unknown>;
  config_hash: string;
  summary: {
    name: string;
    backend: string;
    code: Record<string, unknown>;
    noise: Record<string, unknown>;
    decoders: Array<Record<string, unknown>>;
    shots: number;
    seed: number;
    partition: string;
    statistics: Record<string, unknown>;
  };
}

export function ExperimentBuilder({
  basePath,
  templates,
  onCreated,
  initialProtocol,
}: {
  basePath: string;
  templates: ExperimentTemplate[];
  onCreated?: (spec: ExperimentSpec) => void;
  initialProtocol?: Record<string, unknown> | null;
}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0]?.id ?? "");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [protocolText, setProtocolText] = useState(() =>
    JSON.stringify(templates[0]?.protocol ?? initialProtocol ?? {}, null, 2),
  );
  const [validation, setValidation] = useState<ValidationPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"validate" | "save" | null>(null);
  const [created, setCreated] = useState<ExperimentSpec | null>(null);
  const [runNow, setRunNow] = useState(true);

  const chosenTemplate = useMemo(
    () => templates.find((template) => template.id === templateId) ?? null,
    [templates, templateId],
  );

  function parse(): Record<string, unknown> | null {
    try {
      const parsed = JSON.parse(protocolText) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        setError("The protocol must be a JSON object.");
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch (cause) {
      setError(cause instanceof Error ? `Invalid JSON: ${cause.message}` : "Invalid JSON.");
      return null;
    }
  }

  async function validate(): Promise<Record<string, unknown> | null> {
    const protocol = parse();
    if (!protocol) return null;
    setBusy("validate");
    setError(null);
    setValidation(null);
    try {
      const payload = await api<ValidationPayload>("/experiments/validate", {
        body: { protocol },
      });
      setValidation(payload);
      return payload.protocol;
    } catch (cause) {
      setError(
        cause instanceof ApiError ? cause.message : "The protocol could not be validated.",
      );
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function save(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const validated = await validate();
    if (!validated) return;
    setBusy("save");
    setError(null);
    try {
      const summary = validation?.summary;
      const spec = await api<ExperimentSpec>(`${basePath}/experiments`, {
        body: {
          name: name.trim() || summary?.name || "Untitled experiment",
          description: description.trim(),
          protocol: validated,
        },
      });
      setCreated(spec);
      onCreated?.(spec);
      if (runNow) {
        await api(`${basePath}/experiments/${spec.id}/runs`, { body: {} });
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The experiment could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <form className="qh-card" onSubmit={save}>
      <div className="qh-card-header flex items-center justify-between gap-2">
        <h2 className="m-0 text-[14px] font-semibold">New experiment</h2>
        <span className="qh-badge">validated by the Python engine</span>
      </div>
      <div className="qh-card-body">
        <div className="qh-two-col">
          <div className="qh-field">
            <label className="qh-label" htmlFor="template">
              Template
            </label>
            <select
              id="template"
              className="qh-select"
              value={templateId}
              onChange={(event) => {
                const next = templates.find((item) => item.id === event.target.value);
                setTemplateId(event.target.value);
                setValidation(null);
                if (next) setProtocolText(JSON.stringify(next.protocol, null, 2));
              }}
            >
              {templates.map((template) => (
                <option key={template.id} value={template.id} disabled={!template.available}>
                  {template.name}
                  {template.available ? "" : " (unavailable)"}
                </option>
              ))}
              <option value="">Custom (keep current JSON)</option>
            </select>
            {chosenTemplate && (
              <p className="qh-help">{chosenTemplate.description}</p>
            )}
          </div>
          <div className="qh-field">
            <label className="qh-label" htmlFor="experiment-name">
              Name
            </label>
            <input
              id="experiment-name"
              className="qh-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={validation?.summary.name ?? "Name defaults to the protocol name"}
              maxLength={120}
            />
            <input
              className="qh-input mt-2"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Short description (optional)"
              maxLength={1000}
              aria-label="Description"
            />
          </div>
        </div>

        <div className="qh-field">
          <label className="qh-label" htmlFor="protocol-json">
            Protocol (JSON)
          </label>
          <textarea
            id="protocol-json"
            className="qh-textarea qh-mono"
            style={{ minHeight: 260, fontSize: 12 }}
            value={protocolText}
            spellCheck={false}
            onChange={(event) => {
              setProtocolText(event.target.value);
              setValidation(null);
            }}
          />
          <p className="qh-help">
            The protocol is validated against <span className="qh-mono">quantumlab.research.qec</span>.
            QuantHub stores exactly what the engine accepted.
          </p>
        </div>

        {error && (
          <div className="qh-form-error mb-3" role="alert">
            {error}
          </div>
        )}

        {validation && (
          <div className="mb-3 rounded border border-[#238636] bg-[rgba(35,134,54,0.08)] p-3 text-[12px]">
            <p className="m-0 font-semibold">Protocol validated</p>
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[#9198a1]">
              <dt>Config hash</dt>
              <dd className="qh-mono m-0 truncate">{validation.config_hash.slice(0, 16)}…</dd>
              <dt>Backend</dt>
              <dd className="m-0">{validation.summary.backend}</dd>
              <dt>Shots</dt>
              <dd className="m-0">{validation.summary.shots.toLocaleString()}</dd>
              <dt>Seed</dt>
              <dd className="m-0">{validation.summary.seed}</dd>
              <dt>Decoders</dt>
              <dd className="m-0">
                {validation.summary.decoders
                  .map((decoder) => String(decoder.name ?? ""))
                  .join(", ")}
              </dd>
            </dl>
          </div>
        )}

        {created && (
          <div className="mb-3 rounded border border-[#30363d] p-3 text-[12px]">
            Experiment <span className="qh-mono">{created.slug}</span> saved
            {runNow ? " and a run was queued." : "."}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="qh-btn"
            onClick={() => void validate()}
            disabled={busy !== null}
          >
            {busy === "validate" ? "Validating…" : "Validate protocol"}
          </button>
          <label className="flex items-center gap-2 text-[12px] text-[#9198a1]">
            <input
              type="checkbox"
              checked={runNow}
              onChange={(event) => setRunNow(event.target.checked)}
            />
            Start a run after saving
          </label>
          <button type="submit" className="qh-btn qh-btn-primary ml-auto" disabled={busy !== null}>
            {busy === "save" ? "Saving…" : "Save experiment"}
          </button>
        </div>
      </div>
    </form>
  );
}
