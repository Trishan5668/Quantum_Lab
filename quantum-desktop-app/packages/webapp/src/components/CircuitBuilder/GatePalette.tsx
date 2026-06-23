import { useDraggable } from "@dnd-kit/core";
import { BlockMath } from "react-katex";
import { GATE_CATALOG, type GateMeta } from "../../types";

const SECTIONS: { title: string; types: GateMeta["category"][] }[] = [
  { title: "Single-qubit", types: ["single"] },
  { title: "Rotation (θ)", types: ["rotation"] },
  { title: "Two-qubit", types: ["two"] },
  { title: "Measurement", types: ["measure"] },
];

export function GatePalette(): JSX.Element {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3">
        <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
          Gate Palette
        </h2>
        <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
          Drag a gate onto a wire. Hover for the matrix.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {SECTIONS.map((section) => (
          <div key={section.title} className="mb-5">
            <h3 className="px-1 pb-2 font-mono text-[10px] uppercase tracking-widest text-text-muted">
              {section.title}
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {GATE_CATALOG.filter((g) => section.types.includes(g.category)).map((meta) => (
                <PaletteCard key={meta.type} meta={meta} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PaletteCard({ meta }: { meta: GateMeta }): JSX.Element {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${meta.type}`,
    data: {
      source: "palette",
      gateType: meta.type,
      takesTheta: meta.takesTheta,
      arity: meta.arity,
    },
  });

  return (
    <div className="group relative">
      <button
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        type="button"
        aria-roledescription="draggable gate"
        className={`gate-chip flex w-full cursor-grab select-none flex-col items-center justify-center gap-1 rounded-md border bg-bg-elevated/60 px-2 py-2 text-text-primary transition hover:bg-bg-elevated focus-visible:outline focus-visible:outline-1 focus-visible:outline-accent-glow active:cursor-grabbing ${
          isDragging ? "opacity-40" : "opacity-100"
        }`}
        style={{
          borderColor: meta.color,
          boxShadow: `inset 0 0 0 1px ${meta.color}33`,
          touchAction: "none",
        }}
      >
        <span
          className="pointer-events-none font-display text-base font-semibold tracking-wide"
          style={{ color: meta.color }}
        >
          {meta.label}
        </span>
        <span className="pointer-events-none rounded-sm bg-bg-base/60 px-1.5 py-0.5 font-mono text-[9px] text-text-muted">
          {meta.arity === 1 ? "1Q" : "2Q"}
        </span>
      </button>
      <div className="pointer-events-none absolute left-full top-0 z-30 ml-3 hidden w-72 rounded-md border border-border bg-bg-surface px-3 py-3 text-xs text-text-secondary shadow-xl group-hover:block">
        <div className="mb-1 font-display text-sm" style={{ color: meta.color }}>
          {meta.label}
        </div>
        <p className="mb-2 text-[11px] leading-relaxed text-text-secondary">
          {meta.description}
        </p>
        <div className="overflow-x-auto rounded bg-bg-base/60 px-2 py-2">
          <BlockMath math={meta.latex} />
        </div>
      </div>
    </div>
  );
}
