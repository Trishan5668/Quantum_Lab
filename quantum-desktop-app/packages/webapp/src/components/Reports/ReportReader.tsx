import { useMemo, useState, type ReactNode } from "react";

export interface ReportSection {
  id: string;
  number: string;
  title: string;
  subtitle?: string;
  searchText: string;
  markdown: string;
  latex: string[];
  defaultOpen?: boolean;
  render: () => ReactNode;
}

interface ReportReaderProps {
  title: string;
  subtitle?: string;
  sections: ReportSection[];
  compact?: boolean;
}

export function ReportReader({ title, subtitle, sections, compact = false }: ReportReaderProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [allOpen, setAllOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState<Set<string>>(() => new Set());
  const normalizedQuery = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      normalizedQuery
        ? sections.filter((section) => section.searchText.toLowerCase().includes(normalizedQuery))
        : sections,
    [normalizedQuery, sections],
  );
  const markdown = useMemo(() => reportMarkdown(title, subtitle, sections), [title, subtitle, sections]);
  const latex = useMemo(() => reportLatex(title, sections), [title, sections]);

  const toggleBookmark = (id: string) => {
    setBookmarks((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className={`report-reader ${compact ? "report-reader-compact" : ""}`}>
      <div className="report-tools">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="report-search"
          placeholder="Search report or equations"
          aria-label={`Search ${title}`}
        />
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAllOpen(true)}>
          Expand all
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAllOpen(false)}>
          Collapse all
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.print()}>
          Print
        </button>
        <ExportButton label="Markdown" filename={`${slug(title)}.md`} content={markdown} />
        <ExportButton label="LaTeX" filename={`${slug(title)}.tex`} content={latex} />
        <ExportButton label="PDF" filename={`${slug(title)}.md`} content={markdown} />
      </div>

      <div className="report-layout">
        <nav className="report-toc" aria-label={`${title} table of contents`}>
          <p className="report-eyebrow">Contents</p>
          {sections.map((section) => (
            <a key={section.id} href={`#${section.id}`} className="report-toc-link">
              <span>{section.number}</span>
              <span>{section.title}</span>
              {bookmarks.has(section.id) && <span aria-label="Bookmarked">*</span>}
            </a>
          ))}
        </nav>
        <div className="report-sections">
          <div className="report-title-block">
            <p className="report-eyebrow">Generated report</p>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {filtered.map((section) => (
            <details
              key={`${section.id}-${allOpen ? "open" : "natural"}`}
              id={section.id}
              className="report-section"
              open={allOpen || section.defaultOpen}
            >
              <summary className="report-section-summary">
                <span className="min-w-0">
                  <span className="report-section-title">
                    {section.number}. {section.title}
                  </span>
                  {section.subtitle && <span className="report-section-subtitle">{section.subtitle}</span>}
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(event) => {
                      event.preventDefault();
                      toggleBookmark(section.id);
                    }}
                  >
                    {bookmarks.has(section.id) ? "Saved" : "Bookmark"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(event) => {
                      event.preventDefault();
                      void navigator.clipboard?.writeText(section.latex.join("\n\n"));
                    }}
                  >
                    Copy TeX
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(event) => {
                      event.preventDefault();
                      void navigator.clipboard?.writeText(section.markdown);
                    }}
                  >
                    Copy MD
                  </button>
                </span>
              </summary>
              <div className="report-section-body">{section.render()}</div>
            </details>
          ))}
          {filtered.length === 0 && <div className="panel-placeholder">No report sections match that search.</div>}
        </div>
      </div>
    </div>
  );
}

export function FullscreenReport({
  label,
  title,
  subtitle,
  children,
}: {
  label: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
}): JSX.Element {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}>
        Fullscreen
      </button>
      {open && (
        <div className="report-modal" role="dialog" aria-modal="true" aria-label={label}>
          <div className="report-modal-panel">
            <header className="report-modal-header">
              <div className="min-w-0">
                <p className="report-eyebrow">{label}</p>
                <h2>{title}</h2>
                {subtitle && <p>{subtitle}</p>}
              </div>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setOpen(false)}>
                Close
              </button>
            </header>
            <div className="report-modal-body">{children}</div>
          </div>
        </div>
      )}
    </>
  );
}

function ExportButton({ label, filename, content }: { label: string; filename: string; content: string }): JSX.Element {
  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm"
      onClick={() => {
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(href);
      }}
    >
      {label}
    </button>
  );
}

function reportMarkdown(title: string, subtitle: string | undefined, sections: ReportSection[]): string {
  return [
    `# ${title}`,
    subtitle ?? "",
    ...sections.map((section) => `## ${section.number}. ${section.title}\n\n${section.markdown}`),
  ]
    .filter(Boolean)
    .join("\n\n");
}

function reportLatex(title: string, sections: ReportSection[]): string {
  return [
    "\\documentclass{article}",
    "\\usepackage{amsmath,amssymb}",
    "\\begin{document}",
    `\\title{${escapeLatex(title)}}`,
    "\\maketitle",
    ...sections.map((section) => [
      `\\section*{${escapeLatex(`${section.number}. ${section.title}`)}}`,
      ...section.latex.map((equation) => `\\[${equation}\\]`),
    ].join("\n")),
    "\\end{document}",
  ].join("\n");
}

function escapeLatex(value: string): string {
  return value.replace(/[&_#$%{}]/g, (char) => `\\${char}`);
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
