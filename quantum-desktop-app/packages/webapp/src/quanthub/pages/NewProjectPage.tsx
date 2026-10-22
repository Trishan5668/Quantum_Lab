import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError, rememberProject } from "../client";
import { useSession } from "../session";
import type { ProjectDetail } from "../types";
import { ErrorState } from "../components/ui";
import { SessionNotice } from "../components/SessionNotice";

interface TemplatesPayload {
  licenses: Array<{ spdx: string; name: string; requires_attribution: boolean }>;
  license_notice: string;
  gitignore_templates: Array<{ id: string; content: string }>;
}

interface ImportResult {
  files: string[];
  skipped: Array<{ path: string; reason: string }>;
  revision: string;
  preserved_history: boolean;
}

function slugify(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[^\w\s.-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^[-._]+|[-._]+$/g, "")
    .slice(0, 100);
}

export default function NewProjectPage(): JSX.Element {
  const { viewer, readOnlySession, capabilities, usingFirebase } = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [templates, setTemplates] = useState<TemplatesPayload | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [topics, setTopics] = useState("");
  const [initializeReadme, setInitializeReadme] = useState(true);
  const [gitignore, setGitignore] = useState("python");
  const [license, setLicense] = useState("MIT");
  const [mode, setMode] = useState<"new" | "import">(
    params.get("mode") === "import" ? "import" : "new",
  );

  const [files, setFiles] = useState<File[]>([]);
  const [archive, setArchive] = useState<File | null>(null);
  const [importMessage, setImportMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    api<TemplatesPayload>("/projects/templates")
      .then(setTemplates)
      .catch((cause: unknown) =>
        setTemplateError(cause instanceof Error ? cause.message : "Templates unavailable."),
      );
  }, []);

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
      folderInputRef.current.setAttribute("directory", "");
    }
  }, []);

  const derivedSlug = useMemo(() => slugify(name), [name]);
  const effectiveSlug = slugTouched ? slug : derivedSlug;
  const owner = viewer?.handle ?? "…";
  const licenseNotice = useMemo(() => {
    if (!templates) return "";
    return templates.license_notice;
  }, [templates]);

  const totalBytes = useMemo(
    () => files.reduce((sum, file) => sum + file.size, 0) + (archive?.size ?? 0),
    [files, archive],
  );

  // The form is disabled in these sessions, but guard the handler too: a
  // read-only server rejects the POST with 401 regardless of what the UI shows.
  const cannotCreate = readOnlySession || (viewer?.mode === "guest" && !usingFirebase && !capabilities?.local_sessions);

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    if (submitting) return;
    if (cannotCreate) {
      setError(
        "This server cannot authenticate you, so the project was not created. " +
          "Start the API with QUANTHUB_ENV=development QUANTHUB_TRUST_CLIENT_IDENTITY=1 " +
          "for local use, or sign in with a Firebase account.",
      );
      return;
    }
    setError(null);
    setFieldErrors({});
    setSubmitting(true);
    const wantedSlug = effectiveSlug;
    try {
      const project = await api<ProjectDetail>("/projects", {
        method: "POST",
        body: {
          name,
          slug: wantedSlug || undefined,
          description,
          visibility,
          topics: topics
            .split(",")
            .map((topic) => topic.trim())
            .filter(Boolean),
          initialize_readme: initializeReadme,
          gitignore_template: gitignore,
          license: license === "none" ? null : license,
        },
      });
      rememberProject({
        full_name: project.full_name,
        name: project.name,
        visibility: project.visibility,
      });

      if (mode === "import" && (archive || files.length > 0)) {
        const base = `/projects/${project.owner.handle}/${project.slug}`;
        const form = new FormData();
        if (archive) {
          form.append("archive", archive, archive.name);
          form.append("message", importMessage || `Import ${archive.name}`);
          const result = await api<ImportResult>(`${base}/import/zip`, { form });
          setImportResult(result);
        } else {
          files.forEach((file) => form.append("files", file, file.name));
          const relative = files.map((file) => {
            const withPath = file as File & { webkitRelativePath?: string };
            return withPath.webkitRelativePath || file.name;
          });
          form.append("paths", JSON.stringify(relative));
          form.append("message", importMessage || "Import existing project");
          const result = await api<ImportResult>(`${base}/upload`, { form });
          setImportResult(result);
        }
      }
      navigate(`/${project.owner.handle}/${project.slug}`);
    } catch (cause) {
      if (cause instanceof ApiError) {
        setError(cause.message);
        if (cause.code === "InvalidName") setFieldErrors({ name: cause.message });
        if (cause.code === "InvalidSlug" || cause.code === "ReservedSlug" || cause.code === "SlugTaken") {
          setFieldErrors({ slug: cause.message });
        }
        if (cause.code === "InvalidTopic") setFieldErrors({ topics: cause.message });
        if (cause.code === "InvalidWebsite") setFieldErrors({});
      } else {
        setError(cause instanceof Error ? cause.message : "Project creation failed.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageMeta
        title="New project"
        description="Create a QuantHub project with a README, .gitignore and license."
      />
      <div className="qh-container max-w-[880px] py-8">
        <nav className="qh-muted mb-2" aria-label="Breadcrumb">
          <Link to="/">Home</Link> / <span>New project</span>
        </nav>
        <h1 className="mb-1 mt-0 text-[22px] font-semibold">Create a new project</h1>
        <p className="qh-subtle mb-6">
          A project is a product-level container for files, circuits and experiments. QuantHub
          backs it with a real Git repository, so every change is a revision you can inspect.
        </p>

        <div className="mb-6 flex gap-1 border-b border-[#30363d]">
          <button
            type="button"
            className="qh-tab"
            data-active={mode === "new"}
            onClick={() => setMode("new")}
          >
            New project
          </button>
          <button
            type="button"
            className="qh-tab"
            data-active={mode === "import"}
            onClick={() => setMode("import")}
          >
            Import an existing project
          </button>
        </div>

        {templateError && (
          <div className="mb-4">
            <ErrorState message={`License and template options are unavailable: ${templateError}`} />
          </div>
        )}
        {error && (
          <div className="mb-4">
            <div className="qh-form-error" role="alert">
              {error}
            </div>
          </div>
        )}

        <form onSubmit={submit}>
          <fieldset className="mb-6 rounded-md border border-[#30303d] p-4">
            <legend className="px-1 text-[12px] font-semibold uppercase tracking-wide text-[#6e7681]">
              Project details
            </legend>

            <div className="qh-field">
              <label className="qh-label" htmlFor="owner">
                Owner
              </label>
              <select id="owner" className="qh-select" value={owner} disabled>
                <option value={owner}>{owner} (you)</option>
              </select>
              <p className="qh-help">
                Projects are owned by the signed-in identity. Collaborator namespaces are not
                available yet.
              </p>
            </div>

            <div className="qh-two-col">
              <div className="qh-field">
                <label className="qh-label" htmlFor="name">
                  Project name <span className="text-[#f85149]">*</span>
                </label>
                <input
                  id="name"
                  className="qh-input"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={100}
                  required
                  autoFocus
                  aria-invalid={Boolean(fieldErrors.name)}
                />
                {fieldErrors.name && <p className="qh-error-text">{fieldErrors.name}</p>}
              </div>
              <div className="qh-field">
                <label className="qh-label" htmlFor="slug">
                  Slug
                </label>
                <input
                  id="slug"
                  className="qh-input qh-mono"
                  value={slugTouched ? slug : derivedSlug}
                  onChange={(event) => {
                    setSlugTouched(true);
                    setSlug(slugify(event.target.value));
                  }}
                  onBlur={() => {
                    if (!slugTouched) setSlug(derivedSlug);
                  }}
                  placeholder="my-project"
                  aria-invalid={Boolean(fieldErrors.slug)}
                />
                {fieldErrors.slug ? (
                  <p className="qh-error-text">{fieldErrors.slug}</p>
                ) : (
                  <p className="qh-help">
                    URL: <span className="qh-mono">/{owner}/{slugTouched ? slug : derivedSlug || "…"}</span>
                  </p>
                )}
              </div>
            </div>

            <div className="qh-field">
              <label className="qh-label" htmlFor="description">
                Description <span className="text-[#6e7681]">(optional)</span>
              </label>
              <textarea
                id="description"
                className="qh-textarea"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={350}
                placeholder="What will this project contain?"
              />
              <p className="qh-help">{description.length}/350 characters</p>
            </div>

            <div className="qh-field">
              <label className="qh-label" htmlFor="topics">
                Topics <span className="text-[#6e7681]">(optional, comma separated)</span>
              </label>
              <input
                id="topics"
                className="qh-input"
                value={topics}
                onChange={(event) => setTopics(event.target.value)}
                placeholder="qec, surface-code, stimulation"
                aria-invalid={Boolean(fieldErrors.topics)}
              />
              {fieldErrors.topics ? (
                <p className="qh-error-text">{fieldErrors.topics}</p>
              ) : (
                <p className="qh-help">Lowercase letters, numbers, dots, hyphens and underscores.</p>
              )}
            </div>

            <div className="qh-field mb-0">
              <span className="qh-label">Visibility</span>
              <div className="space-y-2">
                {(
                  [
                    ["public", "Public", "Anyone can discover and read this project."],
                    ["private", "Private", "Only you and explicitly authorized collaborators can access it."],
                  ] as const
                ).map(([value, label, help]) => (
                  <label key={value} className="flex items-start gap-2 text-[13px]">
                    <input
                      type="radio"
                      name="visibility"
                      value={value}
                      checked={visibility === value}
                      onChange={() => setVisibility(value)}
                      className="mt-1"
                    />
                    <span>
                      <span className="font-semibold">{label}</span>
                      <span className="block text-[12px] text-[#9198a1]">{help}</span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </fieldset>

          <fieldset className="mb-6 rounded-md border border-[#30303d] p-4">
            <legend className="px-1 text-[12px] font-semibold uppercase tracking-wide text-[#6e7681]">
              Initialize this project with
            </legend>

            <label className="mb-3 flex items-start gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={initializeReadme}
                onChange={(event) => setInitializeReadme(event.target.checked)}
                className="mt-1"
              />
              <span>
                <span className="font-semibold">README</span>
                <span className="block text-[12px] text-[#9198a1]">
                  Creates README.md with overview, setup, experiments and reproducibility sections.
                </span>
              </span>
            </label>

            <div className="qh-two-col">
              <div className="qh-field">
                <label className="qh-label" htmlFor="gitignore">
                  .gitignore template
                </label>
                <select
                  id="gitignore"
                  className="qh-select"
                  value={gitignore}
                  onChange={(event) => setGitignore(event.target.value)}
                >
                  {(templates?.gitignore_templates ?? [{ id: "none", content: "" }]).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.id === "none" ? "No .gitignore" : item.id}
                    </option>
                  ))}
                </select>
                <p className="qh-help">
                  Templates are text only; they do not imply a runtime is installed on the server.
                </p>
              </div>

              <div className="qh-field">
                <label className="qh-label" htmlFor="license">
                  License
                </label>
                <select
                  id="license"
                  className="qh-select"
                  value={license}
                  onChange={(event) => setLicense(event.target.value)}
                >
                  {(templates?.licenses ?? []).map((option) => (
                    <option key={option.spdx} value={option.spdx}>
                      {option.name}
                    </option>
                  ))}
                  <option value="none">No license</option>
                </select>
                {license === "none" ? (
                  <p className="qh-help text-[#e3b341]">{licenseNotice}</p>
                ) : (
                  <p className="qh-help">License text is written to LICENSE verbatim.</p>
                )}
              </div>
            </div>
          </fieldset>

          {mode === "import" && (
            <fieldset className="mb-6 rounded-md border border-[#30303d] p-4">
              <legend className="px-1 text-[12px] font-semibold uppercase tracking-wide text-[#6e7681]">
                Import files
              </legend>
              <p className="qh-help mb-3 mt-0">
                Upload a folder, individual files, or a ZIP archive. Directory structure is
                preserved. This is a <strong>file upload</strong>: Git history from a local
                repository is not preserved.
              </p>

              <div className="mb-3 flex flex-wrap gap-2">
                <button type="button" className="qh-btn" onClick={() => fileInputRef.current?.click()}>
                  Choose files
                </button>
                <button
                  type="button"
                  className="qh-btn"
                  onClick={() => folderInputRef.current?.click()}
                >
                  Choose folder
                </button>
                <label className="qh-btn cursor-pointer">
                  Choose ZIP
                  <input
                    type="file"
                    accept=".zip,application/zip"
                    className="hidden"
                    onChange={(event) => {
                      setArchive(event.target.files?.[0] ?? null);
                      setFiles([]);
                    }}
                  />
                </label>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(event) => {
                  setFiles(Array.from(event.target.files ?? []));
                  setArchive(null);
                }}
              />
              <input
                ref={folderInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(event) => {
                  setFiles(Array.from(event.target.files ?? []));
                  setArchive(null);
                }}
              />

              {(files.length > 0 || archive) && (
                <div className="rounded border border-[#21262d] bg-[#0d1117] p-3 text-[12px]">
                  <div className="font-semibold">
                    {archive ? archive.name : `${files.length} files selected`}
                  </div>
                  <div className="text-[#9198a1]">
                    {(totalBytes / 1024).toFixed(1)} KB total
                  </div>
                  <ul className="mt-2 max-h-32 overflow-auto pl-4 text-[#9198a1]">
                    {archive
                      ? <li>{archive.name}</li>
                      : files.slice(0, 40).map((file) => (
                          <li key={(file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name}>
                            {(file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name}
                          </li>
                        ))}
                    {files.length > 40 && <li>…and {files.length - 40} more</li>}
                  </ul>
                </div>
              )}

              <div className="qh-field mt-3 mb-0">
                <label className="qh-label" htmlFor="import-message">
                  Import commit message
                </label>
                <input
                  id="import-message"
                  className="qh-input"
                  value={importMessage}
                  onChange={(event) => setImportMessage(event.target.value)}
                  placeholder="Import existing project"
                />
              </div>
            </fieldset>
          )}

          {importResult && (
            <div className="qh-card qh-card-body mb-4 text-[13px]">
              <p className="m-0 font-semibold">
                Imported {importResult.files.length} file(s) at revision{" "}
                <span className="qh-mono">{importResult.revision.slice(0, 7)}</span>.
              </p>
              {importResult.skipped.length > 0 && (
                <div className="mt-2">
                  <p className="m-0 text-[#e3b341]">Skipped {importResult.skipped.length} entry(ies):</p>
                  <ul className="m-0 max-h-32 overflow-auto pl-4 text-[12px] text-[#9198a1]">
                    {importResult.skipped.slice(0, 20).map((item) => (
                      <li key={`${item.path}-${item.reason}`}>
                        <span className="qh-mono">{item.path}</span> — {item.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {cannotCreate && <SessionNotice />}
          <div className="flex items-center justify-between gap-3">
            <Link to="/" className="qh-btn">
              Cancel
            </Link>
            <button
              type="submit"
              className="qh-btn qh-btn-primary"
              disabled={submitting || !name.trim() || cannotCreate}
              title={cannotCreate ? "This server cannot authenticate you" : undefined}
            >
              {submitting ? "Creating…" : "Create project"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
