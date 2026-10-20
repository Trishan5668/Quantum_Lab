"""HTTP surface for QuantHub projects, files, experiments and news."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.models import envelope
from app.quanthub import (
    auth,
    config,
    db,
    experiments,
    gitrepo,
    news,
    service,
    templates,
    validation,
)
from app.quanthub.errors import bad_request, not_found
from app.quanthub.languages import language_registry

router = APIRouter(prefix="/api/v1", tags=["quanthub"])

MAX_CHUNK = 1024 * 256


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateProjectIn(BaseModel):
    # Length and character rules live in ``validation.clean_name`` so the API
    # returns the same ``{data, error}`` envelope for every invalid input.
    name: str = Field(default="")
    description: str = ""
    visibility: str = "public"
    topics: list[str] = Field(default_factory=list)
    website: str | None = None
    slug: str | None = None
    license: str | None = None
    initialize_readme: bool = True
    gitignore_template: str = "none"


class UpdateProjectIn(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    topics: list[str] | None = None
    website: str | None = None
    license: str | None = None


class ContentsIn(BaseModel):
    path: str
    content: str
    message: str | None = None
    expected_revision: str | None = None
    create: bool = True


class MoveIn(BaseModel):
    from_path: str
    to_path: str
    expected_revision: str | None = None


class StarIn(BaseModel):
    starred: bool = True


class WatchIn(BaseModel):
    watching: bool = True


class SpecIn(BaseModel):
    name: str | None = None
    description: str | None = None
    protocol: dict[str, Any]


class SpecPatchIn(BaseModel):
    name: str | None = None
    description: str | None = None
    protocol: dict[str, Any] | None = None


class RunIn(BaseModel):
    protocol: dict[str, Any] | None = None
    reproduce_run: str | None = None


class ValidateProtocolIn(BaseModel):
    protocol: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def principal(request: Request) -> auth.Principal:
    who = auth.principal_from_request(request)
    if who.is_authenticated and who.id != auth.GUEST.id:
        auth.ensure_user(who)
    return who


def query_flag(request: Request, name: str, default: bool = False) -> bool:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Identity and capabilities
# ---------------------------------------------------------------------------


@router.get("/me")
def me(request: Request) -> dict[str, Any]:
    who = principal(request)
    payload = who.to_dict()
    if who.is_authenticated:
        with db.db() as conn:
            row = conn.execute(
                "SELECT id, handle, display_name, email, created_at FROM users WHERE id = ?",
                (who.id,),
            ).fetchone()
            payload["profile"] = dict(row) if row else None
            payload["project_count"] = conn.execute(
                "SELECT COUNT(*) AS n FROM projects p WHERE p.owner_id = ? AND p.archived_at IS NULL",
                (who.id,),
            ).fetchone()["n"]
    return envelope(payload)


@router.get("/capabilities/languages")
def languages_capability() -> dict[str, Any]:
    return envelope(language_registry())


@router.get("/capabilities/qec")
def qec_capability() -> dict[str, Any]:
    return envelope(experiments.capabilities_payload())


@router.get("/community/news")
def community_news(
    category: str | None = Query(default=None, max_length=40),
    tag: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=12, ge=1, le=40),
    live: bool = Query(default=True),
) -> dict[str, Any]:
    return envelope(news.news_payload(category=category, tag=tag, limit=limit, allow_live=live))


# ---------------------------------------------------------------------------
# Project templates / metadata
# ---------------------------------------------------------------------------


@router.get("/projects/templates")
def project_templates() -> dict[str, Any]:
    return envelope(
        {
            "licenses": templates.license_options(),
            "license_notice": templates.LICENSE_NOTICE,
            "gitignore_templates": [
                {"id": item["id"], "content": item["content"]}
                for item in templates.gitignore_templates()
            ],
            "languages": [
                {"id": item["id"], "label": item["label"], "extensions": item["extensions"]}
                for item in language_registry()["languages"]
                if item["id"] not in {"unknown"}
            ],
        }
    )


@router.get("/experiments/templates")
def experiment_templates() -> dict[str, Any]:
    return envelope(
        {
            "templates": experiments.templates_payload(),
            "decoders": experiments.capabilities_payload().get("ui_decoders", []),
            "code_families": experiments.capabilities_payload().get("ui_code_families", []),
        }
    )


@router.post("/experiments/validate")
def validate_experiment(payload: ValidateProtocolIn) -> dict[str, Any]:
    return envelope(experiments.validate_protocol_payload(payload.protocol))


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/projects")
def list_projects(
    request: Request,
    view: str = Query(default="discover", pattern="^(discover|mine|starred)$"),
    q: str = Query(default="", max_length=120),
    topic: str | None = Query(default=None, max_length=40),
    owner: str | None = Query(default=None, max_length=40),
    language: str | None = Query(default=None, max_length=40),
    page: int = Query(default=1, ge=1, le=1000),
    per_page: int = Query(default=24, ge=1, le=100),
    sort: str = Query(default="recent", pattern="^(recent|stars|name)$"),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        payload = service.list_projects(
            conn,
            who,
            view=view,
            query=q,
            topic=topic,
            owner=owner,
            language=language,
            page=page,
            per_page=per_page,
            sort=sort,
        )
    return envelope(payload)


@router.post("/projects", status_code=201)
def create_project(request: Request, payload: CreateProjectIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        project = service.create_project(conn, who, payload.model_dump())
    return envelope(project)


@router.get("/projects/{owner}/{slug}")
def get_project(request: Request, owner: str, slug: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        project = service.project_payload(conn, ctx, who)
        project["readme"] = service.readme_payload(ctx, project["revision"])
        project["tree"] = service.tree_payload(ctx, project["revision"], "")
        project["recent_commits"] = service.history_payload(conn, ctx, limit=5)
        project["experiments"] = experiments.list_specs(conn, ctx)
        project["runs"] = experiments.list_runs(conn, ctx, limit=8)
    return envelope(project)


@router.patch("/projects/{owner}/{slug}")
def update_project(request: Request, owner: str, slug: str, payload: UpdateProjectIn) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        project = service.update_project(conn, ctx, who, payload.model_dump(exclude_unset=True))
    return envelope(project)


@router.delete("/projects/{owner}/{slug}")
def archive_project(request: Request, owner: str, slug: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        project = service.archive_project(conn, ctx, who)
    return envelope(project)


@router.post("/projects/{owner}/{slug}/star")
def star_project(request: Request, owner: str, slug: str, payload: StarIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        result = service.star_project(conn, ctx, who, star=payload.starred)
    return envelope(result)


@router.post("/projects/{owner}/{slug}/watch")
def watch_project(request: Request, owner: str, slug: str, payload: WatchIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        result = service.watch_project(conn, ctx, who, watch=payload.watching)
    return envelope(result)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@router.get("/projects/{owner}/{slug}/tree")
def project_tree(
    request: Request,
    owner: str,
    slug: str,
    path: str = Query(default="", max_length=400),
    revision: str | None = Query(default=None, max_length=40),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = service.tree_payload(ctx, revision, path)
    return envelope(payload)


@router.get("/projects/{owner}/{slug}/blob")
def project_blob(
    request: Request,
    owner: str,
    slug: str,
    path: str = Query(..., min_length=1, max_length=400),
    revision: str | None = Query(default=None, max_length=40),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = service.blob_payload(ctx, revision, path)
    return envelope(payload)


@router.get("/projects/{owner}/{slug}/raw")
def project_raw(
    request: Request,
    owner: str,
    slug: str,
    path: str = Query(..., min_length=1, max_length=400),
    revision: str | None = Query(default=None, max_length=40),
) -> FileResponse:
    """Serve a file's bytes for binary previews and downloads."""
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
    rev = revision or gitrepo.head_sha(ctx.repo, ctx.branch)
    if not rev:
        raise not_found("This project has no files yet.")
    clean = gitrepo.normalize_repo_path(path)
    data = gitrepo.read_file(ctx.repo, rev, clean)
    media_type = "application/octet-stream"
    import mimetypes

    guessed, _ = mimetypes.guess_type(clean)
    if guessed:
        media_type = guessed
    from fastapi.responses import Response

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{Path(clean).name}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=60",
        },
    )


@router.put("/projects/{owner}/{slug}/contents")
def write_contents(request: Request, owner: str, slug: str, payload: ContentsIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    content = payload.content.encode("utf-8")
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = service.commit_changes(
            conn,
            ctx,
            who,
            {payload.path: content},
            message=validation.clean_commit_message(
                payload.message, default=f"Update {payload.path}"
            ),
            expected_revision=payload.expected_revision or ...,
        )
    return envelope(result)


@router.delete("/projects/{owner}/{slug}/contents")
def delete_contents(
    request: Request,
    owner: str,
    slug: str,
    path: str = Query(..., min_length=1, max_length=400),
    expected_revision: str | None = Query(default=None, max_length=40),
) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = service.delete_file(
            conn, ctx, who, path, expected_revision=expected_revision or ...
        )
    return envelope(result)


@router.post("/projects/{owner}/{slug}/contents/move")
def move_contents(request: Request, owner: str, slug: str, payload: MoveIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = service.move_file(
            conn, ctx, who, payload.from_path, payload.to_path,
            expected_revision=payload.expected_revision or ...,
        )
    return envelope(result)


@router.post("/projects/{owner}/{slug}/upload")
async def upload_files(
    request: Request,
    owner: str,
    slug: str,
    files: list[UploadFile] = File(...),  # noqa: B008 - FastAPI dependency idiom
    paths: str = Form(default="[]"),
    message: str = Form(default="Upload files"),
    expected_revision: str = Form(default=""),
) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    conf = config.limits()
    try:
        relative_paths = json.loads(paths)
        if not isinstance(relative_paths, list):
            raise TypeError("paths must be a JSON array")
        relative_paths = [str(item) for item in relative_paths]
    except (json.JSONDecodeError, ValueError):
        relative_paths = [file.filename or "upload.bin" for file in files]
    if len(relative_paths) != len(files):
        relative_paths = [file.filename or "upload.bin" for file in files]
    if len(files) > conf.max_files_per_upload:
        raise bad_request("TooManyFiles", f"Uploads are limited to {conf.max_files_per_upload} files.")

    collected: list[tuple[str, bytes]] = []
    total = 0
    for file, declared in zip(files, relative_paths, strict=True):
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = await file.read(MAX_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            total += len(chunk)
            if size > conf.max_file_bytes:
                raise bad_request(
                    "FileTooLarge",
                    f"'{declared}' exceeds the {conf.max_file_bytes} byte file limit.",
                )
            if total > conf.max_upload_bytes:
                raise bad_request(
                    "UploadTooLarge",
                    f"Uploads are limited to {conf.max_upload_bytes} bytes.",
                )
            chunks.append(chunk)
        collected.append((declared, b"".join(chunks)))
        await file.close()

    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = service.import_files(
            conn,
            ctx,
            who,
            collected,
            message=message,
            kind="upload",
            expected_revision=expected_revision or ...,
        )
    return envelope(result)


@router.post("/projects/{owner}/{slug}/import/zip")
async def import_zip(
    request: Request,
    owner: str,
    slug: str,
    archive: UploadFile = File(...),  # noqa: B008 - FastAPI dependency idiom
    message: str = Form(default="Import project archive"),
) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    conf = config.limits()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await archive.read(MAX_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > conf.max_upload_bytes:
            raise bad_request(
                "ArchiveTooLarge",
                f"Archives are limited to {conf.max_upload_bytes} bytes.",
            )
        chunks.append(chunk)
    await archive.close()
    if not chunks:
        raise bad_request("EmptyArchive", "The uploaded archive is empty.")
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = service.import_zip(conn, ctx, who, b"".join(chunks), message=message)
    return envelope(result)


@router.get("/projects/{owner}/{slug}/archive")
def download_archive(
    request: Request,
    owner: str,
    slug: str,
    revision: str | None = Query(default=None, max_length=40),
) -> FileResponse:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
    path, filename = service.export_archive(ctx, revision)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=filename,
        background=None,
    )


@router.get("/projects/{owner}/{slug}/commits")
def project_commits(
    request: Request,
    owner: str,
    slug: str,
    path: str | None = Query(default=None, max_length=400),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = service.history_payload(conn, ctx, limit=limit, path=path)
    return envelope({"commits": payload})


@router.get("/projects/{owner}/{slug}/activity")
def project_activity(
    request: Request,
    owner: str,
    slug: str,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = service.activity_payload(conn, ctx.id, limit=limit)
    return envelope({"activity": payload})


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@router.get("/projects/{owner}/{slug}/experiments")
def list_experiments(request: Request, owner: str, slug: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = {
            "experiments": experiments.list_specs(conn, ctx),
            "templates": experiments.templates_payload(),
            "runs": experiments.list_runs(conn, ctx, limit=12),
            "capabilities": experiments.capabilities_payload(),
        }
    return envelope(payload)


@router.post("/projects/{owner}/{slug}/experiments", status_code=201)
def create_experiment(
    request: Request, owner: str, slug: str, payload: SpecIn
) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        spec = experiments.create_spec(conn, ctx, who, payload.model_dump())
    return envelope(spec)


@router.get("/projects/{owner}/{slug}/experiments/{spec_id}")
def get_experiment(request: Request, owner: str, slug: str, spec_id: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        spec = experiments.get_spec(conn, ctx, spec_id)
        runs = experiments.list_runs(conn, ctx, spec_id=spec_id, limit=25)
    return envelope({"experiment": spec, "runs": runs})


@router.patch("/projects/{owner}/{slug}/experiments/{spec_id}")
def patch_experiment(
    request: Request, owner: str, slug: str, spec_id: str, payload: SpecPatchIn
) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        spec = experiments.update_spec(
            conn, ctx, who, spec_id, payload.model_dump(exclude_unset=True)
        )
    return envelope(spec)


@router.delete("/projects/{owner}/{slug}/experiments/{spec_id}")
def remove_experiment(request: Request, owner: str, slug: str, spec_id: str) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        result = experiments.delete_spec(conn, ctx, who, spec_id)
    return envelope(result)


@router.get("/projects/{owner}/{slug}/runs")
def list_runs(
    request: Request,
    owner: str,
    slug: str,
    spec_id: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        from app.quanthub import jobs

        jobs.reconcile_stale_runs(ctx.id)
        payload = experiments.list_runs(conn, ctx, spec_id=spec_id, limit=limit)
    return envelope({"runs": payload})


@router.post("/projects/{owner}/{slug}/experiments/{spec_id}/runs", status_code=202)
def start_run(request: Request, owner: str, slug: str, spec_id: str, payload: RunIn) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        if payload.reproduce_run:
            source = experiments.get_run(conn, ctx, payload.reproduce_run)
            if source["status"] != "completed":
                raise bad_request(
                    "RunNotCompleted",
                    "Only a completed run can be reproduced.",
                )
            protocol = db.json_load(source["protocol"], None)
            if not isinstance(protocol, dict):
                raise bad_request("RunNotReproducible", "That run has no stored protocol.")
            run = experiments.create_run(
                conn, ctx, who, spec_id, reproduction_of=payload.reproduce_run, protocol_override=protocol
            )
        else:
            run = experiments.create_run(
                conn, ctx, who, spec_id, protocol_override=payload.protocol
            )
    return envelope(run)


@router.get("/projects/{owner}/{slug}/runs/{run_id}")
def get_run(request: Request, owner: str, slug: str, run_id: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = experiments.run_detail(conn, ctx, run_id)
    return envelope(payload)


@router.post("/projects/{owner}/{slug}/runs/{run_id}/cancel")
def cancel_run(request: Request, owner: str, slug: str, run_id: str) -> dict[str, Any]:
    who = auth.require_user(principal(request))
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who, write=True)
        payload = experiments.cancel_run(conn, ctx, who, run_id)
    return envelope(payload)


@router.get("/projects/{owner}/{slug}/runs/{run_id}/log")
def run_log(
    request: Request,
    owner: str,
    slug: str,
    run_id: str,
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        experiments.get_run(conn, ctx, run_id)
    payload = experiments.run_log(ctx, run_id)
    return envelope(payload)


@router.post("/projects/{owner}/{slug}/runs/{run_id}/verify")
def verify_run(request: Request, owner: str, slug: str, run_id: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = experiments.verify_run(ctx, run_id, conn)
    return envelope(payload)


@router.get("/projects/{owner}/{slug}/runs/{run_id}/claims")
def run_claims(request: Request, owner: str, slug: str, run_id: str) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = experiments.claims_run(ctx, run_id, conn)
    return envelope(payload)


@router.get("/projects/{owner}/{slug}/runs/{run_id}/export")
def export_run(request: Request, owner: str, slug: str, run_id: str) -> JSONResponse:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        payload = experiments.summary_for_export(conn, ctx, run_id)
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": f'attachment; filename="{run_id}-summary.json"',
        },
    )


@router.get("/projects/{owner}/{slug}/runs/{run_id}/artifacts/{name}")
def download_artifact(
    request: Request, owner: str, slug: str, run_id: str, name: str
) -> FileResponse:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        path = experiments.artifact_path(ctx, run_id, name, conn)
    return FileResponse(path, media_type="application/octet-stream", filename=name)


@router.get("/projects/{owner}/{slug}/runs/{run_id}/bundle")
def download_bundle(request: Request, owner: str, slug: str, run_id: str) -> FileResponse:
    who = principal(request)
    with db.db() as conn:
        ctx = service.require_project(conn, owner, slug, who)
        experiments.get_run(conn, ctx, run_id)
        archive = experiments.materialise_reproduction_bundle(conn, ctx, run_id)
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=f"{run_id}-research-bundle.zip",
    )


# ---------------------------------------------------------------------------
# Global activity / dashboard
# ---------------------------------------------------------------------------


def _visible_project_ids(conn: Any, who: auth.Principal) -> list[str]:
    if who.is_authenticated:
        rows = conn.execute(
            "SELECT p.id FROM projects p WHERE p.visibility = 'public' OR p.owner_id = ?"
            " OR EXISTS (SELECT 1 FROM project_members m WHERE m.project_id = p.id AND m.user_id = ?)",
            (who.id, who.id),
        ).fetchall()
    else:
        rows = conn.execute("SELECT id FROM projects WHERE visibility = 'public'").fetchall()
    return [str(row["id"]) for row in rows]


def _activity_rows(conn: Any, ids: list[str], limit: int) -> list[dict[str, Any]]:
    """Read the newest activity rows for the given visible projects."""
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT a.*, p.name AS project_name, p.slug AS project_slug,"
        f" u.handle AS owner_handle FROM activity a"
        f" JOIN projects p ON p.id = a.project_id"
        f" JOIN users u ON u.id = p.owner_id"
        f" WHERE a.project_id IN ({placeholders}) ORDER BY a.id DESC LIMIT ?",
        [*ids, limit],
    ).fetchall()
    return [
        {
            "id": row["id"],
            "type": row["type"],
            "actor": row["actor_handle"],
            "payload": db.json_load(row["payload"], {}),
            "created_at": row["created_at"],
            "project": {
                "full_name": f"{row['owner_handle']}/{row['project_slug']}",
                "name": row["project_name"],
            },
        }
        for row in rows
    ]


@router.get("/activity")
def global_activity(
    request: Request, limit: int = Query(default=20, ge=1, le=100)
) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        ids = _visible_project_ids(conn, who)
        return envelope({"activity": _activity_rows(conn, ids, limit)})


@router.get("/dashboard")
def dashboard(request: Request) -> dict[str, Any]:
    who = principal(request)
    with db.db() as conn:
        mine = service.list_projects(conn, who, view="mine", per_page=6) if who.is_authenticated else {"items": []}
        trending = service.list_projects(conn, who, view="discover", per_page=6, sort="stars")
        ids = _visible_project_ids(conn, who)
        runs: list[dict[str, Any]] = []
        activity: list[dict[str, Any]] = []
        if ids:
            placeholders = ",".join("?" for _ in ids)
            run_rows = conn.execute(
                f"SELECT r.*, p.slug AS project_slug, p.name AS project_name, u.handle AS owner_handle"
                f" FROM runs r JOIN projects p ON p.id = r.project_id JOIN users u ON u.id = p.owner_id"
                f" WHERE r.project_id IN ({placeholders}) ORDER BY r.created_at DESC LIMIT 6",
                ids,
            ).fetchall()
            runs = [
                {
                    "id": row["id"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "finished_at": row["finished_at"],
                    "config_hash": row["config_hash"],
                    "spec_id": row["spec_id"],
                    "project": {
                        "full_name": f"{row['owner_handle']}/{row['project_slug']}",
                        "name": row["project_name"],
                    },
                }
                for row in run_rows
            ]
            activity = _activity_rows(conn, ids, 12)
        stats = {
            "projects": len(ids),
            "experiments": conn.execute(
                "SELECT COUNT(*) AS n FROM experiment_specs WHERE project_id IN (SELECT id FROM projects WHERE visibility='public')"
            ).fetchone()["n"],
        }
    return envelope(
        {
            "viewer": who.to_dict(),
            "my_projects": mine["items"],
            "trending_projects": trending["items"],
            "recent_runs": runs,
            "activity": activity,
            "news": news.news_payload(limit=4),
            "stats": stats,
            "tools": [
                {
                    "id": "circuit-designer",
                    "name": "Circuit Designer",
                    "href": "/app",
                    "description": "Build and simulate circuits with state-vector and density-matrix modes.",
                },
                {
                    "id": "qec-workbench",
                    "name": "QEC Workbench",
                    "href": "/qec",
                    "description": "Configure, execute and audit quantum error-correction experiments.",
                },
            ],
        }
    )


