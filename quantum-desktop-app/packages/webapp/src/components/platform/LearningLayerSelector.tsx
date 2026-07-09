import { usePlatformStore, LEARNING_LAYERS } from "../../store/platformStore";

export function LearningLayerSelector(): JSX.Element {
  const layer = usePlatformStore((s) => s.learningLayer);
  const setLayer = usePlatformStore((s) => s.setLearningLayer);

  return (
    <div
      className="hidden items-center gap-0.5 rounded-md border border-border bg-bg-elevated/60 p-0.5 sm:flex"
      role="group"
      aria-label="Learning depth"
    >
      {LEARNING_LAYERS.map((l) => (
        <button
          key={l.id}
          type="button"
          onClick={() => setLayer(l.id)}
          aria-pressed={layer === l.id}
          title={`${l.tagline}: ${l.description}`}
          className={`rounded px-2 py-1 font-mono text-[10px] transition-colors ${
            layer === l.id
              ? "bg-accent-quantum/20 text-accent-glow"
              : "text-text-muted hover:text-text-secondary"
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
