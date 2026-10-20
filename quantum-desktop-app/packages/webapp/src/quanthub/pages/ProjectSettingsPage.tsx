import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, ApiError } from "../client";
import { useAsync } from "../hooks";
import type { ProjectDetail } from "../types";
import { ProjectChrome } from "../components/ProjectChrome";

interface Templates {
  licenses: Array<{ spdx: string; name: string }>;
}

export default function ProjectSettingsPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const navigate = useNavigate();
  const templates = useAsync((signal) => api<Templates>("/projects/templates", { signal }), []);

  return (
    <>
      <PageMeta title={`Settings · ${owner}/${slug}`} description="Project settings." />
      <ProjectChrome owner={owner} slug={slug} tab="settings">
        {(project, reload) => (
          <SettingsForm
            project={project}
            licenses={templates.data?.licenses ?? []}
            onSaved={reload}
            onArchived={() => navigate("/projects")}
          />
        )}
      </ProjectChrome>
    </>
  );
}

function SettingsForm({
  project,
  licenses,
  onSaved,
  onArchived,
}: {
  project: ProjectDetail;
  licenses: Array<{ spdx: string; name: string }>;
  onSaved: () => void;
  onArchived: () => void;
}): JSX.Element {
  const base = `/projects/${project.owner.handle}/${project.slug}`;
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [visibility, setVisibility] = useState<"public" | "private">(project.visibility);
  const [website, setWebsite] = useState(project.website ?? "");
  const [topics, setTopics] = useState(project.topics.join(", "));
  const [license, setLicense] = useState(project.license ?? "none");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    setName(project.name);
    setDescription(project.description);
    setVisibility(project.visibility);
    setWebsite(project.website ?? "");
    setTopics(project.topics.join(", "));
    setLicense(project.license ?? "none");
  }, [project]);

  async function save(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      await api(base, {
        method: "PATCH",
        body: {
          name,
          description,
          visibility,
          website: website.trim() || null,
          topics: topics
            .split(",")
            .map((topic) => topic.trim())
            .filter(Boolean),
          license: license === "none" ? null : license,
        },
      });
      setSaved("Project settings saved.");
      onSaved();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Settings could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function archive(): Promise<void> {
    if (!window.confirm("Archive this project? It becomes read-only; files and runs are preserved.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api(base, { method: "DELETE" });
      onArchived();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The project could not be archived.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="qh-card" onSubmit={save}>
        <div className="qh-card-header">
          <h2 className="m-0 text-[14px] font-semibold">Project settings</h2>
        </div>
        <div className="qh-card-body">
          <div className="qh-field">
            <label className="qh-label" htmlFor="project-name">Name</label>
            <input
              id="project-name"
              className="qh-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
            />
          </div>
          <div className="qh-field">
            <label className="qh-label" htmlFor="project-description">Description</label>
            <textarea
              id="project-description"
              className="qh-textarea"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={350}
            />
          </div>
          <div className="qh-two-col">
            <div className="qh-field">
              <label className="qh-label" htmlFor="project-visibility">Visibility</label>
              <select
                id="project-visibility"
                className="qh-select"
                value={visibility}
                onChange={(event) => setVisibility(event.target.value as "public" | "private")}
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>
            <div className="qh-field">
              <label className="qh-label" htmlFor="project-license">License</label>
              <select
                id="project-license"
                className="qh-select"
                value={license}
                onChange={(event) => setLicense(event.target.value)}
              >
                {licenses.map((option) => (
                  <option key={option.spdx} value={option.spdx}>{option.name}</option>
                ))}
                <option value="none">No license</option>
              </select>
            </div>
          </div>
          <div className="qh-field">
            <label className="qh-label" htmlFor="project-website">Website</label>
            <input
              id="project-website"
              className="qh-input"
              value={website}
              onChange={(event) => setWebsite(event.target.value)}
              placeholder="https://…"
            />
            <p className="qh-help">Only http(s) URLs are accepted. Empty clears the field.</p>
          </div>
          <div className="qh-field">
            <label className="qh-label" htmlFor="project-topics">Topics</label>
            <input
              id="project-topics"
              className="qh-input"
              value={topics}
              onChange={(event) => setTopics(event.target.value)}
              placeholder="qec, surface-code, reproducibility"
            />
          </div>

          {error && <div className="qh-form-error mb-3">{error}</div>}
          {saved && <p className="mb-2 text-[12px] text-[#3fb950]">{saved}</p>}

          <button type="submit" className="qh-btn qh-btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>

      <div className="qh-card">
        <div className="qh-card-header">
          <h2 className="m-0 text-[14px] font-semibold">Danger zone</h2>
        </div>
        <div className="qh-card-body flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="m-0 text-[13px] font-semibold">Archive this project</p>
            <p className="qh-help m-0">
              Archiving makes the project read-only. Files, experiments, runs and artifacts are
              retained; this is not a hard delete.
            </p>
          </div>
          <button
            type="button"
            className="qh-btn qh-btn-danger"
            onClick={() => void archive()}
            disabled={busy || project.archived}
          >
            {project.archived ? "Already archived" : "Archive project"}
          </button>
        </div>
      </div>
    </div>
  );
}
