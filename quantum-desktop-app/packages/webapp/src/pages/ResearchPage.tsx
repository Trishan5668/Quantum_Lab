import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { ContentCard } from "../components/platform/ContentCard";
import { MarkdownText } from "../components/ui/MarkdownText";
import { RESEARCH_TOPICS, getResearchTopic } from "../data/research";

export default function ResearchPage(): JSX.Element {
  const { slug } = useParams<{ slug?: string }>();

  if (slug) {
    return <ResearchArticle slug={slug} />;
  }

  return (
    <>
      <PageMeta
        title="Quantum Research"
        description="Noise, tomography, density matrices, error correction, hardware, and references."
      />
      <div className="platform-container py-12 sm:py-16">
        <SectionHeader
          eyebrow="Research"
          title="From simulation to science"
          subtitle="Deep topics for researchers and advanced learners, available in the simulator by default."
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {RESEARCH_TOPICS.map((topic) => (
            <ContentCard
              key={topic.slug}
              title={topic.title}
              description={topic.summary}
              to={`/research/${topic.slug}`}
            />
          ))}
        </div>
        <div className="mt-8">
          <Link to="/app" className="btn btn-primary btn-md">
            Open Simulator
          </Link>
        </div>
      </div>
    </>
  );
}

function ResearchArticle({ slug }: { slug: string }): JSX.Element {
  const topic = getResearchTopic(slug);
  if (!topic) {
    return (
      <div className="platform-container py-16 text-center">
        <p className="text-text-secondary">Topic not found.</p>
        <Link to="/research" className="btn btn-secondary btn-sm mt-4">Back to research</Link>
      </div>
    );
  }

  return (
    <>
      <PageMeta title={topic.title} description={topic.summary} />
      <article className="platform-container max-w-3xl py-12 sm:py-16">
        <Link to="/research" className="mb-6 inline-flex font-mono text-[10px] text-text-muted hover:text-text-primary">
          ← Research
        </Link>
        <h1 className="font-sans text-3xl font-semibold tracking-tight">{topic.title}</h1>
        <p className="mt-3 text-text-secondary">{topic.summary}</p>
        <div className="markdown-body mt-8 text-sm leading-relaxed">
          <MarkdownText text={topic.content} />
        </div>
        <section className="mt-10 border-t border-border pt-6">
          <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
            References
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-text-muted">
            {topic.references.map((ref) => (
              <li key={ref}>· {ref}</li>
            ))}
          </ul>
        </section>
      </article>
    </>
  );
}
