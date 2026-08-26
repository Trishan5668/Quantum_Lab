import { usePlatformStore, LEARNING_LAYERS } from "../../store/platformStore";

export function LearningLayerSelector(): JSX.Element {
  const learningMode = usePlatformStore((s) => s.learningMode);
  const setLearningMode = usePlatformStore((s) => s.setLearningMode);
  const activePanel = usePlatformStore((s) => s.activeWorkspacePanel);
  const setActivePanel = usePlatformStore((s) => s.setActiveWorkspacePanel);
  const selected = LEARNING_LAYERS.find((layer) => layer.id === learningMode) ?? LEARNING_LAYERS[0];

  return (
    <div
      className="hidden items-center gap-1 rounded-md border border-border bg-bg-elevated/60 p-0.5 sm:flex"
      aria-label="Workspace mode"
    >
      <label className={`workspace-tab ${activePanel === "learning" ? "is-active" : ""}`}>
        <span>Learning</span>
        <select
          value={learningMode}
          onChange={(event) => {
            setLearningMode(event.target.value as typeof learningMode);
            setActivePanel("learning");
          }}
          title={`${selected.tagline}: ${selected.description}`}
          aria-label="Learning mode"
        >
          {LEARNING_LAYERS.map((layer) => (
            <option key={layer.id} value={layer.id}>
              {layer.label}
            </option>
          ))}
        </select>
      </label>
      {(["math", "physics"] as const).map((panel) => (
        <button
          key={panel}
          type="button"
          onClick={() => setActivePanel(panel)}
          aria-pressed={activePanel === panel}
          className={`workspace-tab ${activePanel === panel ? "is-active" : ""}`}
        >
          {panel === "math" ? "Math" : "Physics"}
        </button>
      ))}
    </div>
  );
}
