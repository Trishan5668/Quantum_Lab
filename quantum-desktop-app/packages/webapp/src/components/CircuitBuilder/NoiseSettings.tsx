import { useState } from "react";
import { useCircuitStore } from "../../store/circuitStore";
import type { NoiseChannelType } from "../../types";
import { Button } from "../ui/Button";

const NOISE_OPTIONS: { value: NoiseChannelType; label: string }[] = [
  { value: "depolarizing", label: "Depolarizing" },
  { value: "amplitude_damping", label: "Amplitude damping (T1)" },
  { value: "phase_damping", label: "Phase damping (T2)" },
  { value: "bit_flip", label: "Bit flip (X)" },
  { value: "phase_flip", label: "Phase flip (Z)" },
  { value: "t1_t2", label: "Custom T1/T2" },
];

export function NoiseSettings(): JSX.Element {
  const [open, setOpen] = useState(false);
  const noiseEnabled = useCircuitStore((s) => s.noiseEnabled);
  const noiseModel = useCircuitStore((s) => s.noiseModel);
  const noiseProbability = useCircuitStore((s) => s.noiseProbability);
  const t1Us = useCircuitStore((s) => s.t1Us);
  const t2Us = useCircuitStore((s) => s.t2Us);
  const gateTimeNs = useCircuitStore((s) => s.gateTimeNs);
  const setNoiseEnabled = useCircuitStore((s) => s.setNoiseEnabled);
  const setNoiseModel = useCircuitStore((s) => s.setNoiseModel);
  const setNoiseProbability = useCircuitStore((s) => s.setNoiseProbability);
  const setT1Us = useCircuitStore((s) => s.setT1Us);
  const setT2Us = useCircuitStore((s) => s.setT2Us);
  const setGateTimeNs = useCircuitStore((s) => s.setGateTimeNs);

  return (
    <div className="shrink-0 border-t border-border bg-bg-surface/80 px-3 py-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between rounded-md px-1 py-1 font-display text-xs font-semibold uppercase tracking-[0.15em] text-text-secondary hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
        aria-expanded={open}
        aria-controls="noise-settings-body"
      >
        Noise Settings
        <span className="text-text-muted" aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div id="noise-settings-body" className="mt-2 max-h-48 space-y-2 overflow-y-auto overscroll-contain text-[11px]">
          <label className="flex items-center gap-2 text-text-secondary">
            <input
              type="checkbox"
              checked={noiseEnabled}
              onChange={(e) => setNoiseEnabled(e.target.checked)}
              className="rounded border-border accent-accent-quantum"
            />
            Enable noise
          </label>
          {noiseEnabled && (
            <>
              <label className="block text-text-muted">
                Channel
                <select
                  value={noiseModel}
                  onChange={(e) => setNoiseModel(e.target.value as NoiseChannelType)}
                  className="mt-1 w-full rounded-md border border-border bg-bg-base px-2 py-1.5 font-mono text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
                >
                  {NOISE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              {noiseModel !== "t1_t2" ? (
                <label className="block text-text-muted" title="Error probability per gate">
                  Probability p
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={noiseProbability}
                    onChange={(e) => setNoiseProbability(Number(e.target.value))}
                    className="mt-1 w-full rounded-md border border-border bg-bg-base px-2 py-1.5 font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
                  />
                </label>
              ) : (
                <>
                  <label className="block text-text-muted" title="Energy decay time T1">
                    T1 (µs)
                    <input
                      type="number"
                      min={0.1}
                      step={1}
                      value={t1Us}
                      onChange={(e) => setT1Us(Number(e.target.value))}
                      className="mt-1 w-full rounded-md border border-border bg-bg-base px-2 py-1.5 font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
                    />
                  </label>
                  <label className="block text-text-muted" title="Dephasing time T2">
                    T2 (µs)
                    <input
                      type="number"
                      min={0.1}
                      step={1}
                      value={t2Us}
                      onChange={(e) => setT2Us(Number(e.target.value))}
                      className="mt-1 w-full rounded-md border border-border bg-bg-base px-2 py-1.5 font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
                    />
                  </label>
                  <label className="block text-text-muted" title="Gate duration">
                    Gate time (ns)
                    <input
                      type="number"
                      min={0}
                      step={10}
                      value={gateTimeNs}
                      onChange={(e) => setGateTimeNs(Number(e.target.value))}
                      className="mt-1 w-full rounded-md border border-border bg-bg-base px-2 py-1.5 font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-glow/60"
                    />
                  </label>
                </>
              )}
              <Button
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setNoiseEnabled(false);
                  setNoiseModel("depolarizing");
                  setNoiseProbability(0.01);
                }}
              >
                Reset to default (no noise)
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
