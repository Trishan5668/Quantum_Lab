import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { MarkdownText } from "../components/ui/MarkdownText";
import { DOC_CATEGORIES, DOC_ARTICLES, getDoc, getDocsByCategory } from "../data/docs";

export default function DocsPage(): JSX.Element {
  const { slug } = useParams<{ slug?: string }>();

  if (slug) {
    return <DocArticle slug={slug} />;
  }

  return (
    <>
      <PageMeta
        title="Documentation"
        description="Installation, architecture, quantum theory, simulation engine, API, and contributing guides."
      />
      <div className="platform-container py-12 sm:py-16">
        <SectionHeader
          eyebrow="Docs"
          title="Production documentation"
          subtitle="Everything you need to install, understand, and contribute to QuantumLab."
        />
        <div className="grid gap-8 lg:grid-cols-[220px_1fr]">
          <nav className="space-y-4" aria-label="Documentation categories">
            {DOC_CATEGORIES.map((cat) => (
              <div key={cat.id}>
                <p className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-muted">
                  {cat.label}
                </p>
                <ul className="mt-2 space-y-1">
                  {getDocsByCategory(cat.id).map((doc) => (
                    <li key={doc.slug}>
                      <Link
                        to={`/docs/${doc.slug}`}
                        className="block rounded px-2 py-1 text-sm text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
                      >
                        {doc.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
          <div className="grid gap-4 sm:grid-cols-2">
            {DOC_ARTICLES.map((doc) => (
              <Link
                key={doc.slug}
                to={`/docs/${doc.slug}`}
                className="platform-card block p-5 hover:border-accent-quantum/30"
              >
                <p className="font-mono text-[10px] text-accent-measure">{doc.category}</p>
                <h3 className="mt-1 font-sans text-base font-semibold">{doc.title}</h3>
                <p className="mt-2 text-sm text-text-secondary">{doc.summary}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function DocArticle({ slug }: { slug: string }): JSX.Element {
  const doc = getDoc(slug);
  if (!doc) {
    return (
      <div className="platform-container py-16 text-center">
        <p className="text-text-secondary">Article not found.</p>
        <Link to="/docs" className="btn btn-secondary btn-sm mt-4">Back to docs</Link>
      </div>
    );
  }

  return (
    <>
      <PageMeta title={doc.title} description={doc.summary} />
      <article className="platform-container max-w-3xl py-12 sm:py-16">
        <Link to="/docs" className="mb-6 inline-flex font-mono text-[10px] text-text-muted hover:text-text-primary">
          ← Documentation
        </Link>
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-measure">{doc.category}</p>
        <h1 className="mt-2 font-sans text-3xl font-semibold tracking-tight">{doc.title}</h1>
        <p className="mt-3 text-text-secondary">{doc.summary}</p>
        <div className="markdown-body mt-8 text-sm leading-relaxed">
          <MarkdownText text={doc.content} />
        </div>
      </article>
    </>
  );
}
