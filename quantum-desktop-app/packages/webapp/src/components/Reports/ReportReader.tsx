import { useEffect, useMemo, useState, type ReactNode } from "react";
import pkg from "../../../package.json";

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

export interface ReportMetadata {
  reportKind?: "Mathematics" | "Physics" | "Research Mathematics" | string;
  circuitName?: string;
  qubitCount?: number;
  gateCount?: number;
  initialState?: string;
  simulationMode?: string;
  noiseModel?: string;
  generatedAt?: string;
  quantumLabVersion?: string;
  authorName?: string;
  authorId?: string;
  learningMode?: string;
  circuitJson?: unknown;
  gateSequence?: string[];
  backendVersion?: string;
  randomSeed?: string;
}

interface ReportReaderProps {
  title: string;
  subtitle?: string;
  sections: ReportSection[];
  compact?: boolean;
  metadata?: ReportMetadata;
}

type NavigatorTab = "contents" | "bookmarks" | "figures" | "tables" | "equations" | "definitions" | "appendices" | "references";

interface EquationEntry {
  id: string;
  number: number;
  sectionId: string;
  sectionNumber: string;
  sectionTitle: string;
  latex: string;
}

interface ReportReference {
  id: string;
  title: string;
  citation: string;
  relevantWhen: (text: string) => boolean;
}

const REFERENCES: ReportReference[] = [
  {
    id: "nielsen-chuang",
    title: "Nielsen and Chuang",
    citation: "M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, Cambridge University Press.",
    relevantWhen: (text) => /density|entropy|trace|fidelity|measurement|cnot|qubit|unitary/i.test(text),
  },
  {
    id: "preskill",
    title: "Preskill Lecture Notes",
    citation: "J. Preskill, Lecture Notes for Physics 219: Quantum Computation.",
    relevantWhen: (text) => /quantum information|partial trace|schmidt|correlation|noise|kraus/i.test(text),
  },
  {
    id: "dirac",
    title: "Dirac",
    citation: "P. A. M. Dirac, The Principles of Quantum Mechanics, Oxford University Press.",
    relevantWhen: (text) => /ket|bra|dirac|operator|observable|eigen/i.test(text),
  },
  {
    id: "von-neumann",
    title: "von Neumann",
    citation: "J. von Neumann, Mathematical Foundations of Quantum Mechanics, Princeton University Press.",
    relevantWhen: (text) => /density|measurement|projection|trace|hilbert/i.test(text),
  },
  {
    id: "sakurai",
    title: "Sakurai",
    citation: "J. J. Sakurai and J. Napolitano, Modern Quantum Mechanics, Cambridge University Press.",
    relevantWhen: (text) => /observable|expectation|spin|pauli|bloch|hamiltonian/i.test(text),
  },
  {
    id: "shor",
    title: "Shor",
    citation: "P. W. Shor, Algorithms for quantum computation: discrete logarithms and factoring.",
    relevantWhen: (text) => /fourier|phase estimation|period|shor/i.test(text),
  },
  {
    id: "grover",
    title: "Grover",
    citation: "L. K. Grover, A fast quantum mechanical algorithm for database search.",
    relevantWhen: (text) => /grover|amplitude amplification|search|oracle/i.test(text),
  },
];

const NAVIGATOR_TABS: { id: NavigatorTab; label: string }[] = [
  { id: "contents", label: "Contents" },
  { id: "bookmarks", label: "Bookmarks" },
  { id: "figures", label: "Figures" },
  { id: "tables", label: "Tables" },
  { id: "equations", label: "Equations" },
  { id: "definitions", label: "Definitions" },
  { id: "appendices", label: "Appendices" },
  { id: "references", label: "References" },
];

const NOTATION: { symbol: string; meaning: string; pattern: RegExp }[] = [
  { symbol: "\\psi", meaning: "Quantum state vector in the selected computational basis", pattern: /\\psi|state vector|amplitude/i },
  { symbol: "\\rho", meaning: "Density operator", pattern: /\\rho|density/i },
  { symbol: "U", meaning: "Unitary operator or complete circuit operator", pattern: /unitary|operator|U_/i },
  { symbol: "\\mathcal{H}", meaning: "Hilbert space of the qubit register", pattern: /Hilbert|\\mathcal\{H\}/i },
  { symbol: "\\mathrm{Tr}", meaning: "Matrix trace", pattern: /trace|\\mathrm\{Tr\}/i },
  { symbol: "\\otimes", meaning: "Tensor product", pattern: /tensor|\\otimes|Kronecker/i },
  { symbol: "\\lambda_i", meaning: "Eigenvalue, Schmidt coefficient, or spectral coefficient according to context", pattern: /eigen|Schmidt|\\lambda/i },
  { symbol: "\\Pi_i", meaning: "Measurement projector", pattern: /measurement|projector|\\Pi/i },
  { symbol: "S(\\rho)", meaning: "von Neumann entropy", pattern: /entropy|S\(/i },
  { symbol: "F(\\rho,\\sigma)", meaning: "Fidelity between quantum states", pattern: /fidelity|F\(/i },
];

export function ReportReader({ title, subtitle, sections, compact = false, metadata }: ReportReaderProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [allOpen, setAllOpen] = useState(false);
  const [tocCollapsed, setTocCollapsed] = useState(false);
  const [navigatorTab, setNavigatorTab] = useState<NavigatorTab>("contents");
  const [activeSectionId, setActiveSectionId] = useState(sections[0]?.id ?? "");
  const normalizedQuery = query.trim().toLowerCase();
  const generatedAt = useMemo(() => metadata?.generatedAt ?? new Date().toISOString(), [metadata?.generatedAt]);
  const resolvedMetadata = useMemo(
    () => ({
      ...metadata,
      reportKind: metadata?.reportKind ?? title,
      generatedAt,
      quantumLabVersion: metadata?.quantumLabVersion ?? pkg.version,
    }),
    [generatedAt, metadata, title],
  );
  const reportId = useMemo(() => shortHash(JSON.stringify({ title, subtitle, sections: sections.map(sectionDigest), metadata: resolvedMetadata })), [resolvedMetadata, sections, subtitle, title]);
  const reportHash = useMemo(() => shortHash(JSON.stringify({ reportId, sections })), [reportId, sections]);
  const bookmarkStorageKey = `quantumlab:report-bookmarks:${resolvedMetadata.authorId ?? "local"}:${reportId}`;
  const [bookmarks, setBookmarks] = useState<Set<string>>(() => new Set());
  const allText = useMemo(() => [title, subtitle, ...sections.flatMap((section) => [section.title, section.subtitle, section.markdown, ...section.latex])].filter(Boolean).join(" "), [sections, subtitle, title]);
  const equations = useMemo(() => flattenEquations(sections), [sections]);
  const notation = useMemo(() => NOTATION.filter((entry) => entry.pattern.test(allText)), [allText]);
  const references = useMemo(() => REFERENCES.filter((entry) => entry.relevantWhen(allText)), [allText]);
  const figures = useMemo(() => inferFigures(sections), [sections]);
  const tables = useMemo(() => inferTables(sections), [sections]);
  const appendices = useMemo(() => buildAppendices(sections, resolvedMetadata), [resolvedMetadata, sections]);
  const definitions = useMemo(() => notation.map((entry, index) => ({ id: `definition-${index + 1}`, number: index + 1, title: entry.symbol, meaning: entry.meaning })), [notation]);
  const filtered = useMemo(
    () =>
      normalizedQuery
        ? sections.filter((section) => section.searchText.toLowerCase().includes(normalizedQuery))
        : sections,
    [normalizedQuery, sections],
  );
  const markdown = useMemo(
    () => reportMarkdown(title, subtitle, sections, resolvedMetadata, reportId, reportHash, equations, notation, references, figures, tables, appendices),
    [appendices, equations, figures, notation, references, reportHash, reportId, resolvedMetadata, sections, subtitle, tables, title],
  );
  const latex = useMemo(
    () => reportLatex(title, subtitle, sections, resolvedMetadata, reportId, reportHash, equations, notation, references, appendices),
    [appendices, equations, notation, references, reportHash, reportId, resolvedMetadata, sections, subtitle, title],
  );
  const printableHtml = useMemo(() => reportHtml(title, subtitle, markdown), [markdown, subtitle, title]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(bookmarkStorageKey) ?? "[]");
      if (Array.isArray(saved)) setBookmarks(new Set(saved.map(String)));
    } catch {
      setBookmarks(new Set());
    }
  }, [bookmarkStorageKey]);

  useEffect(() => {
    localStorage.setItem(bookmarkStorageKey, JSON.stringify([...bookmarks]));
  }, [bookmarkStorageKey, bookmarks]);

  useEffect(() => {
    if (compact) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setActiveSectionId(visible.target.id);
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.25, 0.5] },
    );
    sections.forEach((section) => {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    });
    return () => observer.disconnect();
  }, [compact, sections]);

  const toggleBookmark = (id: string) => {
    setBookmarks((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const shareUrl = `${window.location.origin}/report/${reportId}`;

  return (
    <div className={`report-reader academic-report ${compact ? "report-reader-compact" : ""}`}>
      <div className="report-tools">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="report-search"
          placeholder="Search text, LaTeX, labels, gates, observables"
          aria-label={`Search ${title}`}
        />
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAllOpen(true)}>
          Expand all
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAllOpen(false)}>
          Collapse all
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.print()}>
          Print / PDF
        </button>
        <ExportButton label="Markdown" filename={`${slug(title)}.md`} content={markdown} />
        <ExportButton label="LaTeX" filename={`${slug(title)}.tex`} content={latex} />
        <ExportButton label="PDF HTML" filename={`${slug(title)}-print.html`} content={printableHtml} type="text/html;charset=utf-8" />
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void navigator.clipboard?.writeText(shareUrl)}>
          Copy share link
        </button>
      </div>

      <div className={`report-layout ${tocCollapsed ? "report-layout-single" : ""}`}>
        {!tocCollapsed && (
          <AcademicNavigator
            title={title}
            sections={sections}
            activeSectionId={activeSectionId}
            bookmarks={bookmarks}
            equations={equations}
            figures={figures}
            tables={tables}
            definitions={definitions}
            appendices={appendices}
            references={references}
            tab={navigatorTab}
            onTabChange={setNavigatorTab}
          />
        )}
        <div className="report-sections">
          <article className="report-paper">
            <TitlePage
              title={title}
              subtitle={subtitle}
              metadata={resolvedMetadata}
              reportId={reportId}
              reportHash={reportHash}
              tocCollapsed={tocCollapsed}
              onToggleToc={() => setTocCollapsed((value) => !value)}
            />
            <NotationTable notation={notation} />
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
                  <span className="flex shrink-0 items-center gap-1 report-section-actions">
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
            <AppendixSections appendices={appendices} />
            <ReferencesSection references={references} />
            <FurtherReading text={allText} />
            <ReproducibilitySection metadata={resolvedMetadata} reportId={reportId} reportHash={reportHash} />
          </article>
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

export function AcademicBox({
  kind,
  title,
  children,
}: {
  kind: "Definition" | "Theorem" | "Lemma" | "Corollary" | "Remark" | "Proof" | "Example" | "Algorithm" | "Observation";
  title?: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <section className={`academic-box academic-box-${slug(kind)}`}>
      <p className="academic-box-title">{title ? `${kind}: ${title}` : kind}</p>
      <div>{children}</div>
    </section>
  );
}

export function DerivationBox({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }): JSX.Element {
  return (
    <details className="academic-derivation" open={defaultOpen}>
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  );
}

function AcademicNavigator({
  title,
  sections,
  activeSectionId,
  bookmarks,
  equations,
  figures,
  tables,
  definitions,
  appendices,
  references,
  tab,
  onTabChange,
}: {
  title: string;
  sections: ReportSection[];
  activeSectionId: string;
  bookmarks: Set<string>;
  equations: EquationEntry[];
  figures: NumberedArtifact[];
  tables: NumberedArtifact[];
  definitions: { id: string; number: number; title: string; meaning: string }[];
  appendices: NumberedArtifact[];
  references: ReportReference[];
  tab: NavigatorTab;
  onTabChange: (tab: NavigatorTab) => void;
}): JSX.Element {
  return (
    <nav className="report-toc academic-sidebar" aria-label={`${title} academic navigator`}>
      <p className="report-eyebrow">Academic navigator</p>
      <div className="academic-nav-tabs">
        {NAVIGATOR_TABS.map((item) => (
          <button key={item.id} type="button" className={tab === item.id ? "is-active" : ""} onClick={() => onTabChange(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="academic-nav-list">
        {tab === "contents" &&
          sections.map((section) => (
            <a key={section.id} href={`#${section.id}`} className={`report-toc-link ${activeSectionId === section.id ? "is-active" : ""}`}>
              <span>{section.number}</span>
              <span>{section.title}</span>
              {bookmarks.has(section.id) && <span aria-label="Bookmarked">*</span>}
            </a>
          ))}
        {tab === "bookmarks" &&
          (sections.filter((section) => bookmarks.has(section.id)).length ? (
            sections.filter((section) => bookmarks.has(section.id)).map((section) => (
              <a key={section.id} href={`#${section.id}`} className="report-toc-link">
                <span>{section.number}</span>
                <span>{section.title}</span>
              </a>
            ))
          ) : (
            <p className="academic-nav-empty">No bookmarks yet.</p>
          ))}
        {tab === "equations" &&
          equations.map((equation) => (
            <a key={equation.id} href={`#${equation.sectionId}`} className="report-toc-link" title={equation.latex}>
              <span>({equation.number})</span>
              <span>{equation.sectionTitle}</span>
            </a>
          ))}
        {tab === "figures" && <ArtifactLinks artifacts={figures} prefix="Figure" />}
        {tab === "tables" && <ArtifactLinks artifacts={tables} prefix="Table" />}
        {tab === "definitions" &&
          definitions.map((definition) => (
            <a key={definition.id} href="#report-notation" className="report-toc-link" title={definition.meaning}>
              <span>{definition.number}</span>
              <span>{definition.title}</span>
            </a>
          ))}
        {tab === "appendices" && <ArtifactLinks artifacts={appendices} prefix="Appendix" />}
        {tab === "references" &&
          references.map((reference, index) => (
            <a key={reference.id} href="#report-references" className="report-toc-link" title={reference.citation}>
              <span>[{index + 1}]</span>
              <span>{reference.title}</span>
            </a>
          ))}
      </div>
    </nav>
  );
}

function ArtifactLinks({ artifacts, prefix }: { artifacts: NumberedArtifact[]; prefix: string }): JSX.Element {
  return artifacts.length ? (
    <>
      {artifacts.map((artifact) => (
        <a key={artifact.id} href={`#${artifact.id}`} className="report-toc-link">
          <span>{prefix === "Appendix" ? artifact.number : `${prefix} ${artifact.number}`}</span>
          <span>{artifact.title}</span>
        </a>
      ))}
    </>
  ) : (
    <p className="academic-nav-empty">No numbered entries for this report.</p>
  );
}

function TitlePage({
  title,
  subtitle,
  metadata,
  reportId,
  reportHash,
  tocCollapsed,
  onToggleToc,
}: {
  title: string;
  subtitle?: string;
  metadata: ReportMetadata;
  reportId: string;
  reportHash: string;
  tocCollapsed: boolean;
  onToggleToc: () => void;
}): JSX.Element {
  const rows = [
    ["Circuit", metadata.circuitName ?? "Untitled circuit"],
    ["Generated", formatDate(metadata.generatedAt)],
    ["Simulation", metadata.simulationMode ?? "Statevector"],
    ["Noise", metadata.noiseModel ?? "Ideal"],
    ["Qubits", valueOrDash(metadata.qubitCount)],
    ["Gates", valueOrDash(metadata.gateCount)],
    ["Initial state", metadata.initialState ?? "not specified"],
    ["Learning mode", metadata.learningMode ?? "not specified"],
    ["QuantumLab version", metadata.quantumLabVersion ?? pkg.version],
    ["Author", metadata.authorName ?? "Unsigned local user"],
    ["Report ID", reportId],
    ["Report hash", reportHash],
  ];
  return (
    <header className="report-title-block report-title-page">
      <div className="report-title-row">
        <div>
          <p className="report-eyebrow">QuantumLab Research Report</p>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button type="button" className="btn btn-ghost btn-sm report-toggle-toc" onClick={onToggleToc}>
          {tocCollapsed ? "Show navigator" : "Hide navigator"}
        </button>
      </div>
      <dl className="report-metadata-grid">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </header>
  );
}

function NotationTable({ notation }: { notation: typeof NOTATION }): JSX.Element {
  if (!notation.length) return <></>;
  return (
    <section id="report-notation" className="report-generated-section">
      <h3>Notation</h3>
      <table className="academic-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          {notation.map((entry) => (
            <tr key={entry.symbol}>
              <td>{entry.symbol}</td>
              <td>{entry.meaning}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AppendixSections({ appendices }: { appendices: NumberedArtifact[] }): JSX.Element {
  return (
    <section id="report-appendices" className="report-generated-section">
      <h3>Appendices</h3>
      {appendices.map((appendix) => (
        <details key={appendix.id} id={appendix.id} className="academic-derivation">
          <summary>{appendix.number}. {appendix.title}</summary>
          <p>{appendix.description}</p>
        </details>
      ))}
    </section>
  );
}

function ReferencesSection({ references }: { references: ReportReference[] }): JSX.Element {
  if (!references.length) return <></>;
  return (
    <section id="report-references" className="report-generated-section">
      <h3>References</h3>
      <ol className="academic-reference-list">
        {references.map((reference) => (
          <li key={reference.id}>{reference.citation}</li>
        ))}
      </ol>
    </section>
  );
}

function FurtherReading({ text }: { text: string }): JSX.Element {
  const reading = suggestedReading(text);
  if (!reading.length) return <></>;
  return (
    <section id="report-further-reading" className="report-generated-section">
      <h3>Suggested Further Reading</h3>
      <ul className="academic-reference-list">
        {reading.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function ReproducibilitySection({ metadata, reportId, reportHash }: { metadata: ReportMetadata; reportId: string; reportHash: string }): JSX.Element {
  const payload = {
    reportId,
    reportHash,
    circuitJson: metadata.circuitJson ?? null,
    gateSequence: metadata.gateSequence ?? [],
    initialBasisState: metadata.initialState ?? null,
    simulationMode: metadata.simulationMode ?? null,
    noiseModel: metadata.noiseModel ?? "Ideal",
    backendVersion: metadata.backendVersion ?? "not reported",
    randomSeed: metadata.randomSeed ?? "not applicable",
    generatedAt: metadata.generatedAt,
  };
  return (
    <section id="report-reproducibility" className="report-generated-section">
      <h3>Reproducibility</h3>
      <pre className="academic-json">{JSON.stringify(payload, null, 2)}</pre>
    </section>
  );
}

function ExportButton({ label, filename, content, type = "text/plain;charset=utf-8" }: { label: string; filename: string; content: string; type?: string }): JSX.Element {
  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm"
      onClick={() => {
        const blob = new Blob([content], { type });
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

function flattenEquations(sections: ReportSection[]): EquationEntry[] {
  let count = 0;
  return sections.flatMap((section) =>
    section.latex.map((latex) => {
      count += 1;
      return {
        id: `eq-${count}`,
        number: count,
        sectionId: section.id,
        sectionNumber: section.number,
        sectionTitle: section.title,
        latex,
      };
    }),
  );
}

interface NumberedArtifact {
  id: string;
  number: string;
  title: string;
  description: string;
}

function inferFigures(sections: ReportSection[]): NumberedArtifact[] {
  const candidates = sections.filter((section) => /bloch|density|circuit|probability|measurement|basis|correlation|state evolution/i.test(section.searchText));
  return candidates.slice(0, 8).map((section, index) => ({
    id: `figure-${index + 1}`,
    number: String(index + 1),
    title: `${section.title} diagnostic`,
    description: `Automatically associated visualization for Section ${section.number}: ${section.title}.`,
  }));
}

function inferTables(sections: ReportSection[]): NumberedArtifact[] {
  return sections.filter((section) => /amplitude|probability|expectation|invariant|summary|matrix|operator/i.test(section.searchText)).slice(0, 8).map((section, index) => ({
    id: `table-${index + 1}`,
    number: String(index + 1),
    title: `${section.title} tabulation`,
    description: `Numerical table associated with Section ${section.number}: ${section.title}.`,
  }));
}

function buildAppendices(sections: ReportSection[], metadata: ReportMetadata): NumberedArtifact[] {
  const appendices = [
    ["A", "Gate matrices", "Collected local and embedded gate matrices appearing in the report."],
    ["B", "Basis ordering", `Computational basis ordering for ${metadata.qubitCount ?? "the"} qubit register and initial state ${metadata.initialState ?? "not specified"}.`],
    ["C", "State vector evolution", "Stepwise simulator state snapshots and amplitude support."],
    ["D", "Circuit operator", "Complete ordered product defining the circuit-level operator."],
    ["E", "Additional derivations", "Supplementary derivations, proof blocks, and section-local formulae."],
  ];
  return appendices
    .filter(([letter]) => letter !== "D" || sections.some((section) => /circuit unitary|operator/i.test(section.title)))
    .map(([number, title, description]) => ({ id: `appendix-${number.toLowerCase()}`, number: `Appendix ${number}`, title, description }));
}

function reportMarkdown(
  title: string,
  subtitle: string | undefined,
  sections: ReportSection[],
  metadata: ReportMetadata,
  reportId: string,
  reportHash: string,
  equations: EquationEntry[],
  notation: typeof NOTATION,
  references: ReportReference[],
  figures: NumberedArtifact[],
  tables: NumberedArtifact[],
  appendices: NumberedArtifact[],
): string {
  const equationMap = new Map(equations.map((equation) => [equation.latex, equation.number]));
  return [
    `# ${title}`,
    subtitle ?? "",
    metadataMarkdown(metadata, reportId, reportHash),
    "## Table of Contents",
    ...sections.map((section) => `- [${section.number}. ${section.title}](#${slug(`${section.number}-${section.title}`)})`),
    "## Notation",
    notation.length ? notation.map((entry) => `| ${entry.symbol} | ${entry.meaning} |`).join("\n") : "No specialized notation detected.",
    ...sections.map((section) => [
      `## ${section.number}. ${section.title}`,
      section.subtitle ? `_${section.subtitle}_` : "",
      section.markdown,
      ...section.latex.map((equation) => `\n\\[\n${equation}\n\\]\\hfill (${equationMap.get(equation) ?? "?"})`),
    ].filter(Boolean).join("\n\n")),
    "## Figures",
    figures.map((figure) => `- Figure ${figure.number}. ${figure.title}: ${figure.description}`).join("\n"),
    "## Tables",
    tables.map((table) => `- Table ${table.number}. ${table.title}: ${table.description}`).join("\n"),
    "## Appendices",
    appendices.map((appendix) => `### ${appendix.number}. ${appendix.title}\n\n${appendix.description}`).join("\n\n"),
    "## References",
    references.map((reference, index) => `${index + 1}. ${reference.citation}`).join("\n"),
    "## Suggested Further Reading",
    suggestedReading([title, subtitle, ...sections.map((section) => section.searchText)].join(" ")).map((item) => `- ${item}`).join("\n"),
    "## Reproducibility",
    "```json",
    JSON.stringify({ reportId, reportHash, circuitJson: metadata.circuitJson ?? null, gateSequence: metadata.gateSequence ?? [], initialBasisState: metadata.initialState, simulationMode: metadata.simulationMode, noiseModel: metadata.noiseModel ?? "Ideal", backendVersion: metadata.backendVersion ?? "not reported", randomSeed: metadata.randomSeed ?? "not applicable" }, null, 2),
    "```",
  ]
    .filter(Boolean)
    .join("\n\n");
}

function reportLatex(
  title: string,
  subtitle: string | undefined,
  sections: ReportSection[],
  metadata: ReportMetadata,
  reportId: string,
  reportHash: string,
  equations: EquationEntry[],
  notation: typeof NOTATION,
  references: ReportReference[],
  appendices: NumberedArtifact[],
): string {
  const equationMap = new Map(equations.map((equation) => [equation.latex, equation.number]));
  return [
    "\\documentclass[11pt]{article}",
    "\\usepackage[margin=1in]{geometry}",
    "\\usepackage{amsmath,amssymb,amsfonts,mathtools}",
    "\\usepackage{hyperref}",
    "\\usepackage{booktabs}",
    "\\usepackage{longtable}",
    "\\usepackage{fancyhdr}",
    "\\usepackage{enumitem}",
    "\\pagestyle{fancy}",
    "\\fancyhf{}",
    `\\lhead{${escapeLatex(metadata.reportKind ?? title)}}`,
    "\\rhead{QuantumLab}",
    "\\cfoot{\\thepage}",
    "\\begin{document}",
    `\\title{${escapeLatex(title)}}`,
    `\\author{${escapeLatex(metadata.authorName ?? "QuantumLab User")}}`,
    `\\date{${escapeLatex(formatDate(metadata.generatedAt))}}`,
    "\\maketitle",
    subtitle ? `\\begin{abstract}${escapeLatex(subtitle)}\\end{abstract}` : "",
    metadataLatex(metadata, reportId, reportHash),
    "\\tableofcontents",
    "\\newpage",
    "\\section*{Notation}",
    "\\begin{longtable}{ll}",
    ...notation.map((entry) => `${escapeLatex(entry.symbol)} & ${escapeLatex(entry.meaning)}\\\\`),
    "\\end{longtable}",
    ...sections.map((section) => [
      `\\section{${escapeLatex(section.title)}}`,
      section.subtitle ? `\\textit{${escapeLatex(section.subtitle)}}` : "",
      escapeLatex(section.markdown),
      ...section.latex.map((equation) => [
        "\\begin{equation}",
        equation,
        `\\tag{${equationMap.get(equation) ?? "?"}}\\label{eq:${equationMap.get(equation) ?? "x"}}`,
        "\\end{equation}",
      ].join("\n")),
    ].filter(Boolean).join("\n\n")),
    "\\appendix",
    ...appendices.map((appendix) => `\\section{${escapeLatex(appendix.title)}}\n${escapeLatex(appendix.description)}`),
    "\\begin{thebibliography}{99}",
    ...references.map((reference) => `\\bibitem{${reference.id}} ${escapeLatex(reference.citation)}`),
    "\\end{thebibliography}",
    "\\end{document}",
  ].filter(Boolean).join("\n");
}

function reportHtml(title: string, subtitle: string | undefined, markdown: string): string {
  return [
    "<!doctype html>",
    "<html>",
    "<head>",
    "<meta charset=\"utf-8\" />",
    `<title>${escapeHtml(title)}</title>`,
    "<style>body{font-family:Georgia,'Times New Roman',serif;max-width:760px;margin:40px auto;line-height:1.65;color:#111}pre{white-space:pre-wrap;background:#f5f5f5;padding:1rem}h1,h2,h3{page-break-after:avoid}.math{font-family:serif}@page{size:A4;margin:20mm}a{color:#0645ad}</style>",
    "<script>window.MathJax={tex:{inlineMath:[[\"$\",\"$\"],[\"\\\\(\",\"\\\\)\"]]}};</script>",
    "<script async src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js\"></script>",
    "</head>",
    "<body>",
    `<h1>${escapeHtml(title)}</h1>`,
    subtitle ? `<p><em>${escapeHtml(subtitle)}</em></p>` : "",
    markdown.split("\n").map((line) => `<p>${escapeHtml(line)}</p>`).join("\n"),
    "</body>",
    "</html>",
  ].join("\n");
}

function metadataMarkdown(metadata: ReportMetadata, reportId: string, reportHash: string): string {
  return [
    "## Report Metadata",
    `- Circuit: ${metadata.circuitName ?? "Untitled circuit"}`,
    `- Qubits: ${valueOrDash(metadata.qubitCount)}`,
    `- Gates: ${valueOrDash(metadata.gateCount)}`,
    `- Initial state: ${metadata.initialState ?? "not specified"}`,
    `- Simulation mode: ${metadata.simulationMode ?? "Statevector"}`,
    `- Noise model: ${metadata.noiseModel ?? "Ideal"}`,
    `- Generated: ${formatDate(metadata.generatedAt)}`,
    `- QuantumLab version: ${metadata.quantumLabVersion ?? pkg.version}`,
    `- Author: ${metadata.authorName ?? "Unsigned local user"}`,
    `- Report ID: ${reportId}`,
    `- Report hash: ${reportHash}`,
  ].join("\n");
}

function metadataLatex(metadata: ReportMetadata, reportId: string, reportHash: string): string {
  const rows = [
    ["Circuit", metadata.circuitName ?? "Untitled circuit"],
    ["Qubits", valueOrDash(metadata.qubitCount)],
    ["Gates", valueOrDash(metadata.gateCount)],
    ["Initial state", metadata.initialState ?? "not specified"],
    ["Simulation mode", metadata.simulationMode ?? "Statevector"],
    ["Noise model", metadata.noiseModel ?? "Ideal"],
    ["Generated", formatDate(metadata.generatedAt)],
    ["QuantumLab version", metadata.quantumLabVersion ?? pkg.version],
    ["Report ID", reportId],
    ["Report hash", reportHash],
  ];
  return [
    "\\begin{center}",
    "\\begin{tabular}{ll}",
    "\\toprule",
    ...rows.map(([label, value]) => `${escapeLatex(label)} & ${escapeLatex(value)}\\\\`),
    "\\bottomrule",
    "\\end{tabular}",
    "\\end{center}",
  ].join("\n");
}

function sectionDigest(section: ReportSection): Record<string, unknown> {
  return {
    id: section.id,
    number: section.number,
    title: section.title,
    subtitle: section.subtitle,
    markdown: section.markdown,
    latex: section.latex,
  };
}

function suggestedReading(text: string): string[] {
  const items = new Set<string>();
  if (/bell|entanglement|schmidt|cnot/i.test(text)) {
    items.add("Bell's theorem");
    items.add("CHSH inequality");
    items.add("Quantum teleportation");
    items.add("Superdense coding");
  }
  if (/fourier|qft|phase/i.test(text)) {
    items.add("Quantum Fourier transform");
    items.add("Phase estimation");
    items.add("Shor algorithm");
  }
  if (/grover|oracle|search/i.test(text)) {
    items.add("Amplitude amplification");
    items.add("Grover search");
  }
  if (/density|noise|kraus|purity/i.test(text)) {
    items.add("Open quantum systems");
    items.add("Quantum process tomography");
  }
  if (!items.size) {
    items.add("Nielsen and Chuang, Chapters 2-4");
    items.add("Preskill quantum computation lecture notes");
  }
  return [...items];
}

function escapeLatex(value: string): string {
  return value.replace(/[&_#$%{}]/g, (char) => `\\${char}`);
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
}

function formatDate(value?: string): string {
  if (!value) return "not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function valueOrDash(value?: number): string {
  return value === undefined ? "not specified" : String(value);
}

function shortHash(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
