import { useRef, useState } from "react";

export function ThetaInput({
  value,
  onChange,
  onClose,
}: {
  value: number;
  onChange: (v: number) => void;
  onClose: () => void;
}): JSX.Element {
  const [v, setV] = useState(value);
  const ref = useRef<HTMLInputElement>(null);
  const presets = [
    { label: "π/4", v: Math.PI / 4 },
    { label: "π/2", v: Math.PI / 2 },
    { label: "π", v: Math.PI },
    { label: "3π/2", v: (3 * Math.PI) / 2 },
    { label: "2π", v: 2 * Math.PI },
  ];
  return (
    <div className="flex w-56 flex-col gap-2">
      <label className="font-mono text-[10px] uppercase tracking-widest text-text-muted">
        θ (radians)
      </label>
      <input
        ref={ref}
        type="number"
        step="0.0001"
        value={Number.isFinite(v) ? v : 0}
        onChange={(e) => setV(parseFloat(e.target.value))}
        className="rounded border border-border bg-bg-base px-2 py-1 font-mono text-xs text-text-primary focus:border-accent-quantum focus:outline-none"
      />
      <div className="flex flex-wrap gap-1">
        {presets.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setV(p.v)}
            className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-text-secondary hover:border-accent-glow hover:text-accent-glow"
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="flex justify-end gap-2 text-[11px]">
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-border px-2 py-1 text-text-secondary hover:border-text-secondary"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => {
            onChange(v);
            onClose();
          }}
          className="rounded bg-accent-quantum px-2 py-1 font-mono text-white hover:bg-accent-glow"
        >
          Apply
        </button>
      </div>
    </div>
  );
}

export function ThetaModal({
  initial,
  gateLabel,
  onCancel,
  onConfirm,
}: {
  initial: number;
  gateLabel: string;
  onCancel: () => void;
  onConfirm: (theta: number) => void;
}): JSX.Element {
  const [v, setV] = useState(initial);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-base/70 backdrop-blur-sm">
      <div className="w-80 rounded-lg border border-border bg-bg-surface p-5 shadow-2xl">
        <h3 className="mb-3 font-display text-base font-semibold text-accent-glow">
          Set θ for {gateLabel}
        </h3>
        <ThetaInput value={v} onChange={(x) => setV(x)} onClose={onCancel} />
        <div className="mt-3 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-border px-3 py-1.5 font-mono text-xs text-text-secondary hover:border-text-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(v)}
            className="rounded bg-accent-quantum px-3 py-1.5 font-mono text-xs font-semibold text-white hover:bg-accent-glow"
          >
            Place Gate
          </button>
        </div>
      </div>
    </div>
  );
}

export function formatTheta(theta: number): string {
  const fractionsOfPi = [
    { label: "π/4", v: Math.PI / 4 },
    { label: "π/2", v: Math.PI / 2 },
    { label: "π", v: Math.PI },
    { label: "3π/2", v: (3 * Math.PI) / 2 },
    { label: "2π", v: 2 * Math.PI },
  ];
  for (const p of fractionsOfPi) {
    if (Math.abs(p.v - theta) < 1e-4) return p.label;
  }
  return theta.toFixed(3);
}
