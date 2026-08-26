import { Link, useNavigate, useParams } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { ContentCard } from "../components/platform/ContentCard";
import { MarkdownText } from "../components/ui/MarkdownText";
import { Button } from "../components/ui/Button";
import { ALGORITHMS, getAlgorithm } from "../data/algorithms";
import { useCircuitStore } from "../store/circuitStore";
import { usePlatformStore } from "../store/platformStore";

export default function AlgorithmsPage(): JSX.Element {
  const { id } = useParams<{ id?: string }>();

  if (id) {
    return <AlgorithmDetail id={id} />;
  }

  return (
    <>
      <PageMeta
        title="Quantum Algorithm Library"
        description="Interactive algorithm presets with mathematics, AI explanations, and simulator integration."
      />
      <div className="platform-container py-12 sm:py-16">
        <SectionHeader
          eyebrow="Algorithms"
          title="Canonical quantum algorithms"
          subtitle="Each algorithm opens in the real simulator with preset circuits and research notes."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ALGORITHMS.map((algo) => (
            <ContentCard
              key={algo.id}
              title={algo.name}
              description={algo.summary}
              badge={`${algo.qubits} qubits`}
              to={`/algorithms/${algo.id}`}
            />
          ))}
        </div>
      </div>
    </>
  );
}

function AlgorithmDetail({ id }: { id: string }): JSX.Element {
  const algo = getAlgorithm(id);
  const navigate = useNavigate();
  const loadPreset = useCircuitStore((s) => s.loadPreset);
  const setLayer = usePlatformStore((s) => s.setLearningLayer);
  const setActivePanel = usePlatformStore((s) => s.setActiveWorkspacePanel);

  if (!algo) {
    return (
      <div className="platform-container py-16 text-center">
        <p className="text-text-secondary">Algorithm not found.</p>
        <Link to="/algorithms" className="btn btn-secondary btn-sm mt-4">
          Back to library
        </Link>
      </div>
    );
  }

  const openInSimulator = () => {
    loadPreset({
      numQubits: algo.numQubits,
      gates: algo.gates,
      fidelityTarget: algo.fidelityTarget,
    });
    setLayer("research");
    setActivePanel("learning");
    void navigate("/app");
  };

  return (
    <>
      <PageMeta title={algo.name} description={algo.summary} />
      <div className="platform-container py-12 sm:py-16">
        <Link
          to="/algorithms"
          className="mb-6 inline-flex font-mono text-[10px] text-text-muted hover:text-text-primary"
        >
          ← Algorithms
        </Link>
        <SectionHeader
          eyebrow={algo.category}
          title={algo.name}
          subtitle={algo.summary}
        >
          <Button variant="primary" size="md" onClick={openInSimulator}>
            Open in Simulator
          </Button>
        </SectionHeader>

        <div className="grid gap-6 lg:grid-cols-2">
          <article className="platform-card p-6">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Description
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">{algo.description}</p>
          </article>
          <article className="platform-card p-6">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Mathematics
            </h3>
            <div className="markdown-body mt-3 text-sm">
              <MarkdownText text={algo.math} />
            </div>
          </article>
          <article className="platform-card p-6 lg:col-span-2">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Research Notes
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">{algo.researchNotes}</p>
          </article>
        </div>
      </div>
    </>
  );
}
