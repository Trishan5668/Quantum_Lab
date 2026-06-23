import { useMemo, useRef } from "react";
import { useCircuitStore } from "../../store/circuitStore";
import { gateMeta } from "../../types";

const PAD_LEFT = 56;
const COL_W = 64;
const ROW_H = 44;

export function CircuitDiagram(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const gates = useCircuitStore((s) => s.gates);
  const svgRef = useRef<SVGSVGElement>(null);

  const maxStep = useMemo(
    () => gates.reduce((m, g) => Math.max(m, g.timeStep), -1),
    [gates],
  );
  const cols = Math.max(maxStep + 2, 4);
  const width = PAD_LEFT + cols * COL_W + 16;
  const height = numQubits * ROW_H + 32;

  const handleExport = () => {
    const svg = svgRef.current;
    if (!svg) return;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svg);
    const svgBlob = new Blob(
      ['<?xml version="1.0" standalone="no"?>\r\n', source],
      { type: "image/svg+xml;charset=utf-8" },
    );
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const scale = 2;
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(url);
        return;
      }
      ctx.fillStyle = "#0a0b0f";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((png) => {
        if (!png) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(png);
        a.download = "quantumlab-circuit.png";
        a.click();
        URL.revokeObjectURL(a.href);
      }, "image/png");
    };
    img.src = url;
  };

  return (
    <div className="border-t border-border bg-bg-surface/60 px-5 py-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
          Diagram (export-ready)
        </h2>
        <button
          type="button"
          onClick={handleExport}
          className="rounded-md border border-border px-2 py-1 font-mono text-[10px] text-text-secondary hover:border-accent-glow hover:text-accent-glow"
        >
          ⬇ Export PNG
        </button>
      </div>
      <div className="overflow-auto rounded-md border border-border bg-bg-base/50 p-2">
        <svg ref={svgRef} width={width} height={height} className="block">
          <rect width={width} height={height} fill="#0a0b0f" />
          {Array.from({ length: numQubits }).map((_, q) => (
            <g key={q}>
              <text
                x={8}
                y={16 + q * ROW_H + ROW_H / 2}
                fill="#94a3b8"
                fontFamily="'JetBrains Mono', monospace"
                fontSize={11}
                alignmentBaseline="middle"
              >
                q[{q}]
              </text>
              <line
                x1={PAD_LEFT}
                y1={16 + q * ROW_H + ROW_H / 2}
                x2={PAD_LEFT + cols * COL_W}
                y2={16 + q * ROW_H + ROW_H / 2}
                stroke="#475569"
                strokeWidth={1.2}
              />
            </g>
          ))}
          {gates.map((g) => {
            const x = PAD_LEFT + g.timeStep * COL_W + COL_W / 2;
            if (g.qubitTargets.length === 1) {
              const y = 16 + g.qubitTargets[0] * ROW_H + ROW_H / 2;
              const meta = gateMeta(g.gateType);
              return (
                <g key={g.id}>
                  <rect
                    x={x - 16}
                    y={y - 14}
                    width={32}
                    height={28}
                    fill="#12141a"
                    stroke={meta.color}
                    strokeWidth={1.5}
                    rx={4}
                  />
                  <text
                    x={x}
                    y={y + 0.5}
                    textAnchor="middle"
                    alignmentBaseline="middle"
                    fill={meta.color}
                    fontFamily="'JetBrains Mono', monospace"
                    fontSize={12}
                    fontWeight="600"
                  >
                    {g.gateType}
                  </text>
                  {g.params.theta !== undefined && (
                    <text
                      x={x}
                      y={y + 22}
                      textAnchor="middle"
                      fill="#94a3b8"
                      fontFamily="'JetBrains Mono', monospace"
                      fontSize={8}
                    >
                      θ={g.params.theta.toFixed(2)}
                    </text>
                  )}
                </g>
              );
            }
            // CNOT
            const [c, t] = g.qubitTargets;
            const yc = 16 + c * ROW_H + ROW_H / 2;
            const yt = 16 + t * ROW_H + ROW_H / 2;
            return (
              <g key={g.id}>
                <line
                  x1={x}
                  y1={yc}
                  x2={x}
                  y2={yt}
                  stroke="#dc2626"
                  strokeWidth={1.5}
                />
                <circle cx={x} cy={yc} r={5} fill="#dc2626" />
                <circle
                  cx={x}
                  cy={yt}
                  r={10}
                  fill="#12141a"
                  stroke="#dc2626"
                  strokeWidth={1.5}
                />
                <line x1={x - 7} y1={yt} x2={x + 7} y2={yt} stroke="#dc2626" strokeWidth={1.5} />
                <line x1={x} y1={yt - 7} x2={x} y2={yt + 7} stroke="#dc2626" strokeWidth={1.5} />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
