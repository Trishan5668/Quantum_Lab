import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";
import { ApiError, download } from "../client";
import { ProjectChrome } from "../components/ProjectChrome";
import { ImportPanel, type ImportResult } from "../components/ImportPanel";

export default function ImportPage(): JSX.Element {
  const { owner = "", slug = "" } = useParams();
  const [last, setLast] = useState<ImportResult | null>(null);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  return (
    <>
      <PageMeta title={`Import · ${owner}/${slug}`} description="Import files into this project." />
      <ProjectChrome owner={owner} slug={slug} tab="import">
        {(project, reload) => (
          <div className="space-y-4">
            <div>
              <h2 className="m-0 text-[15px] font-semibold">Import an existing project</h2>
              <p className="qh-subtle m-0 text-[12px]">
                Add a multi-file tree, a folder, or a ZIP archive to{" "}
                <span className="qh-mono">{project.full_name}</span>. Every import is committed as
                a revision you can inspect.
              </p>
            </div>

            {!project.viewer.can_write ? (
              <div className="qh-form-error">
                You have read-only access to this project, so imports are disabled.
              </div>
            ) : (
              <ImportPanel
                basePath={`/projects/${owner}/${slug}`}
                onImported={(result) => {
                  setLast(result);
                  reload();
                }}
              />
            )}

            {last && (
              <div className="qh-card qh-card-body text-[13px]">
                <p className="m-0 font-semibold">
                  Imported {last.files.length} file(s) at revision{" "}
                  <span className="qh-mono">{last.revision.slice(0, 7)}</span>.
                </p>
                <Link to={`/${owner}/${slug}`} className="qh-btn qh-btn-sm mt-2">
                  View files
                </Link>
              </div>
            )}

            {project.file_count > 0 && (
              <div className="qh-card">
                <div className="qh-card-header">
                  <h3 className="m-0 text-[13px] font-semibold">Export instead</h3>
                </div>
                <div className="qh-card-body">
                  <p className="qh-help mt-0">
                    Download the project as a ZIP archive at its current revision, including its
                    full file tree.
                  </p>
                  <button
                    type="button"
                    className="qh-btn qh-btn-sm"
                    onClick={() =>
                      void (async () => {
                        setArchiveError(null);
                        try {
                          await download(
                            `/projects/${owner}/${slug}/archive`,
                            `${owner}-${slug}.zip`,
                          );
                        } catch (cause) {
                          setArchiveError(
                            cause instanceof ApiError ? cause.message : "Export failed.",
                          );
                        }
                      })()
                    }
                  >
                    Download ZIP
                  </button>
                  {archiveError && <p className="qh-error-text">{archiveError}</p>}
                </div>
              </div>
            )}
          </div>
        )}
      </ProjectChrome>
    </>
  );
}
