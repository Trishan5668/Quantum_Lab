import type { GatePlacement } from "../../types";
import { gateMeta } from "../../types";

const PAD_LEFT = 56;
const COL_W = 64;
const ROW_H = 44;
const SUPERSCRIPTS: Record<string, string> = {
  "0": "\u2070",
  "1": "\u00b9",
  "2": "\u00b2",
  "3": "\u00b3",
  "4": "\u2074",
  "5": "\u2075",
  "6": "\u2076",
  "7": "\u2077",
  "8": "\u2078",
  "9": "\u2079",
};

export function exportCircuitPng({
  numQubits,
  gates,
}: {
  numQubits: number;
  gates: GatePlacement[];
}): void {
  const maxStep = gates.reduce((max, gate) => Math.max(max, gate.timeStep), -1);
  const cols = Math.max(maxStep + 2, 4);
  const width = PAD_LEFT + cols * COL_W + 16;
  const height = numQubits * ROW_H + 32;
  const source = circuitSvgMarkup({ numQubits, gates, cols, width, height });
  const svgBlob = new Blob(['<?xml version="1.0" standalone="no"?>\r\n', source], {
    type: "image/svg+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(svgBlob);
  const image = new Image();

  image.onload = () => {
    const canvas = document.createElement("canvas");
    const scale = 2;
    canvas.width = width * scale;
    canvas.height = height * scale;
    const context = canvas.getContext("2d");
    if (!context) {
      URL.revokeObjectURL(url);
      return;
    }
    context.fillStyle = "#0a0b0f";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    canvas.toBlob((png) => {
      if (!png) return;
      const link = document.createElement("a");
      link.href = URL.createObjectURL(png);
      link.download = "quantumlab-circuit.png";
      link.click();
      URL.revokeObjectURL(link.href);
    }, "image/png");
  };
  image.src = url;
}

function circuitSvgMarkup({
  numQubits,
  gates,
  cols,
  width,
  height,
}: {
  numQubits: number;
  gates: GatePlacement[];
  cols: number;
  width: number;
  height: number;
}): string {
  const wires = Array.from({ length: numQubits }, (_, qubit) => {
    const y = 16 + qubit * ROW_H + ROW_H / 2;
    return `<g><text x="8" y="${y}" fill="#94a3b8" font-family="'JetBrains Mono', monospace" font-size="11" alignment-baseline="middle">q[${qubit}]</text><line x1="${PAD_LEFT}" y1="${y}" x2="${PAD_LEFT + cols * COL_W}" y2="${y}" stroke="#475569" stroke-width="1.2" /></g>`;
  }).join("");
  const renderedGates = gates.map(renderGate).join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="${width}" height="${height}" fill="#0a0b0f" />${wires}${renderedGates}</svg>`;
}

function renderGate(gate: GatePlacement): string {
  const x = PAD_LEFT + gate.timeStep * COL_W + COL_W / 2;
  if (gate.qubitTargets.length === 1) {
    const y = 16 + gate.qubitTargets[0] * ROW_H + ROW_H / 2;
    const meta = gateMeta(gate.gateType);
    const theta = gate.params.theta === undefined
      ? ""
      : `<text x="${x}" y="${y + 22}" text-anchor="middle" fill="#94a3b8" font-family="'JetBrains Mono', monospace" font-size="8">&#952;=${gate.params.theta.toFixed(2)}</text>`;
    return `<g><rect x="${x - 16}" y="${y - 14}" width="32" height="28" fill="#12141a" stroke="${meta.color}" stroke-width="1.5" rx="4" /><text x="${x}" y="${y + 0.5}" text-anchor="middle" alignment-baseline="middle" fill="${meta.color}" font-family="'JetBrains Mono', monospace" font-size="12" font-weight="600">${stackedGateLabel(gate.gateType, gate.stackCount ?? 1)}</text>${theta}</g>`;
  }

  const [control, target] = gate.qubitTargets;
  const controlY = 16 + control * ROW_H + ROW_H / 2;
  const targetY = 16 + target * ROW_H + ROW_H / 2;
  const stackCount = gate.stackCount ?? 1;
  const stack = stackCount > 1
    ? `<text x="${x + 10}" y="${controlY - 8}" fill="#a78bfa" font-family="'JetBrains Mono', monospace" font-size="10" font-weight="600">${stackCountText(stackCount)}</text>`
    : "";
  return `<g><line x1="${x}" y1="${controlY}" x2="${x}" y2="${targetY}" stroke="#dc2626" stroke-width="1.5" /><circle cx="${x}" cy="${controlY}" r="5" fill="#dc2626" /><circle cx="${x}" cy="${targetY}" r="10" fill="#12141a" stroke="#dc2626" stroke-width="1.5" /><line x1="${x - 7}" y1="${targetY}" x2="${x + 7}" y2="${targetY}" stroke="#dc2626" stroke-width="1.5" /><line x1="${x}" y1="${targetY - 7}" x2="${x}" y2="${targetY + 7}" stroke="#dc2626" stroke-width="1.5" />${stack}</g>`;
}

function stackedGateLabel(gateType: string, stackCount: number): string {
  return stackCount <= 1 ? gateType : `${gateType}${stackCountText(stackCount)}`;
}

function stackCountText(stackCount: number): string {
  return String(stackCount)
    .split("")
    .map((digit) => SUPERSCRIPTS[digit] ?? digit)
    .join("");
}
