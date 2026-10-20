"""Project lifecycle, file operations and imports.

Design boundaries
-----------------
* Project metadata and permissions: SQLite (``db``).
* File contents: a bare Git repository per project (``gitrepo``).
* Binary/large payloads: never stored in metadata tables.

Every mutation takes the revision the caller last saw and is applied as a
compare-and-swap commit, so concurrent edits cannot silently overwrite each
other.
"""

from __future__ import annotations

import io
import json
import shutil
import sqlite3
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.quanthub import auth, config, db, gitrepo, templates, validation
from app.quanthub.errors import HubError, bad_request, conflict, forbidden, not_found
from app.quanthub.languages import detect_language, language_for_filename

MAX_README_PREVIEW = 200_000


@dataclass
class ProjectContext:
    project: dict[str, Any]
    owner: dict[str, Any]
    role: str | None
    repo: Path

    @property
    def id(self) -> str:
        return str(self.project["id"])

    @property
    def branch(self) -> str:
        return str(self.project["default_branch"])

    @property
    def owner_handle(self) -> str:
        return str(self.owner["handle"])


def repo_path_for(project_id: str) -> Path:
    return config.repos_dir() / f"{project_id}.git"


def _owner_row(conn: sqlite3.Connection, owner_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (owner_id,)).fetchone()
    if row is None:  # pragma: no cover - FK integrity guarantees this
        raise not_found("Project owner not found.")
    return dict(row)


def load_project(conn: sqlite3.Connection, owner: str, slug: str) -> ProjectContext:
    row = conn.execute(
        "SELECT p.* FROM projects p JOIN users u ON u.id = p.owner_id"
        " WHERE lower(u.handle) = ? AND lower(p.slug) = ?",
        (owner.strip().lower(), slug.strip().lower()),
    ).fetchone()
    if row is None:
        raise not_found()
    project = dict(row)
    project["topics"] = db.json_load(project.get("topics"), [])
    return ProjectContext(
        project=project,
        owner=_owner_row(conn, project["owner_id"]),
        role=None,
        repo=repo_path_for(project["id"]),
    )


def require_project(
    conn: sqlite3.Connection,
    owner: str,
    slug: str,
    principal: auth.Principal,
    *,
    write: bool = False,
) -> ProjectContext:
    ctx = load_project(conn, owner, slug)
    ctx.role = auth.project_role(conn, ctx.project, principal)
    auth.require_read(ctx.project, ctx.role)
    if ctx.project["archived_at"] is not None and ctx.role not in auth.WRITE_ROLES:
        # Archived projects are read-only and hidden from discovery; only the
        # owner and maintainers can still open them.
        raise not_found("This project has been archived.")
    if write:
        auth.require_write(ctx.project, ctx.role)
    return ctx


def _count(conn: sqlite3.Connection, table: str, project_id: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE project_id = ?", (project_id,)).fetchone()
    return int(row["n"]) if row else 0


def project_payload(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    *,
    include_files: bool = False,
) -> dict[str, Any]:
    project = ctx.project
    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    latest = gitrepo.log(ctx.repo, revision, limit=1) if revision else []
    file_count = gitrepo.count_files(ctx.repo, revision) if revision else 0
    starred = bool(
        principal.is_authenticated
        and conn.execute(
            "SELECT 1 FROM stars WHERE project_id = ? AND user_id = ?",
            (project["id"], principal.id),
        ).fetchone()
    )
    watched = bool(
        principal.is_authenticated
        and conn.execute(
            "SELECT 1 FROM watches WHERE project_id = ? AND user_id = ?",
            (project["id"], principal.id),
        ).fetchone()
    )
    experiments = conn.execute(
        "SELECT COUNT(*) AS n FROM experiment_specs WHERE project_id = ?",
        (project["id"],),
    ).fetchone()
    runs = conn.execute(
        "SELECT COUNT(*) AS n FROM runs WHERE project_id = ?", (project["id"],)
    ).fetchone()
    payload: dict[str, Any] = {
        "id": project["id"],
        "name": project["name"],
        "slug": project["slug"],
        "owner": {"handle": ctx.owner["handle"], "display_name": ctx.owner["display_name"]},
        "full_name": f"{ctx.owner['handle']}/{project['slug']}",
        "description": project["description"],
        "visibility": project["visibility"],
        "topics": project["topics"] if isinstance(project["topics"], list) else [],
        "website": project["website"],
        "license": project["license_spdx"],
        "default_branch": ctx.branch,
        "language": project["language"],
        "readme_path": project["readme_path"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "archived": project["archived_at"] is not None,
        "archived_at": project["archived_at"],
        "revision": revision,
        "file_count": file_count,
        "commit_count": _count(conn, "commits", project["id"]),
        "latest_commit": (
            {
                "sha": latest[0].sha,
                "message": latest[0].message,
                "author_name": latest[0].author_name,
                "authored_at": latest[0].authored_at,
            }
            if latest
            else None
        ),
        "stars": _count(conn, "stars", project["id"]),
        "watchers": _count(conn, "watches", project["id"]),
        "experiment_count": int(experiments["n"]) if experiments else 0,
        "run_count": int(runs["n"]) if runs else 0,
        "viewer": {
            "role": ctx.role,
            "can_write": ctx.role in auth.WRITE_ROLES,
            "can_admin": ctx.role == "owner",
            "starred": starred,
            "watched": watched,
        },
    }
    if include_files and revision:
        payload["files"] = [
            {"path": entry.path, "size": entry.size, "sha": entry.sha}
            for entry in gitrepo.list_all_paths(ctx.repo, revision)
        ]
    return payload


def _unique_slug(conn: sqlite3.Connection, owner_id: str, base: str) -> str:
    slug = base
    index = 0
    while conn.execute(
        "SELECT 1 FROM projects WHERE owner_id = ? AND slug = ?", (owner_id, slug)
    ).fetchone():
        index += 1
        suffix = f"-{index}"
        slug = f"{base[: 100 - len(suffix)]}{suffix}"
        if index > 1000:  # pragma: no cover - defensive
            raise conflict("SlugUnavailable", "Could not allocate a unique project slug.")
    return slug


def _default_branch_name() -> str:
    return "main"


def create_project(
    conn: sqlite3.Connection,
    principal: auth.Principal,
    payload: dict[str, Any],
) -> dict[str, Any]:
    owner = auth.ensure_user(principal)
    name = validation.clean_name(payload.get("name", ""))
    description = validation.clean_description(payload.get("description"))
    visibility = validation.clean_visibility(payload.get("visibility"))
    topics = validation.clean_topics(payload.get("topics"))
    website = validation.clean_website(payload.get("website"))
    requested_slug = payload.get("slug")
    base_slug = (
        validation.clean_slug(str(requested_slug))
        if requested_slug
        else validation.slugify(name)
    )
    license_spdx = payload.get("license")
    if license_spdx in {"", "none", "None", None}:
        license_spdx = None
    if license_spdx:
        known = {option.spdx for option in templates.LICENSES}
        if license_spdx not in known:
            raise bad_request(
                "UnknownLicense",
                f"Unknown license '{license_spdx}'.",
                available=sorted(known),
            )

    readme_enabled = bool(payload.get("initialize_readme", True))
    gitignore_template = payload.get("gitignore_template") or "none"
    gitignore = templates.gitignore_text(gitignore_template)
    branch = _default_branch_name()

    project_id = "p_" + uuid.uuid4().hex[:20]
    if requested_slug:
        if conn.execute(
            "SELECT 1 FROM projects WHERE owner_id = ? AND slug = ?", (owner.id, base_slug)
        ).fetchone():
            raise conflict(
                "SlugTaken",
                f"You already have a project named '{base_slug}'.",
                slug=base_slug,
            )
        slug = base_slug
    else:
        slug = _unique_slug(conn, owner.id, base_slug)
    repo = repo_path_for(project_id)
    now = db.utc_now()

    files: dict[str, bytes] = {}
    if readme_enabled:
        files["README.md"] = templates.readme_text(
            name=name,
            description=description,
            owner=owner.handle,
            visibility=visibility,
            topics=topics,
            slug=slug,
            license_spdx=license_spdx,
        ).encode("utf-8")
    if gitignore:
        files[".gitignore"] = gitignore.encode("utf-8")
    if license_spdx:
        files["LICENSE"] = templates.license_text(
            license_spdx, author=owner.display_name
        ).encode("utf-8")

    # Only real source files define the primary language: dotfiles (for
    # example .gitignore) and LICENSE are configuration rather than code.
    language = _primary_language(files)

    try:
        conn.execute(
            "INSERT INTO projects (id, owner_id, name, slug, description, visibility,"
            " topics, website, license_spdx, default_branch, language, readme_path,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                owner.id,
                name,
                slug,
                description,
                visibility,
                json.dumps(topics),
                website,
                license_spdx,
                branch,
                language,
                "README.md" if readme_enabled else None,
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO project_members (project_id, user_id, role, created_at)"
            " VALUES (?, ?, 'owner', ?)",
            (project_id, owner.id, now),
        )
        gitrepo.init_repo(repo, branch)
        if files:
            sha, _ = gitrepo.commit_files(
                repo,
                branch=branch,
                changes=files,
                message="Initial commit",
                author_name=owner.display_name,
                author_email=_author_email(owner),
                expected_head=None,
            )
            conn.execute(
                "INSERT INTO commits (project_id, sha, parent_sha, message, author_name,"
                " author_email, author_id, created_at, file_count)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    sha,
                    None,
                    "Initial commit",
                    owner.display_name,
                    _author_email(owner),
                    owner.id,
                    now,
                    len(files),
                ),
            )
        db.record_activity(
            conn,
            project_id=project_id,
            actor_id=owner.id,
            actor_handle=owner.handle,
            event_type="project.created",
            payload={
                "visibility": visibility,
                "initialized": {
                    "readme": readme_enabled,
                    "gitignore": gitignore_template if gitignore else "none",
                    "license": license_spdx,
                },
            },
        )
    except Exception:
        conn.rollback()
        gitrepo.delete_repo(repo)
        raise

    ctx = ProjectContext(
        project={
            "id": project_id,
            "owner_id": owner.id,
            "name": name,
            "slug": slug,
            "description": description,
            "visibility": visibility,
            "topics": topics,
            "website": website,
            "license_spdx": license_spdx,
            "default_branch": branch,
            "language": language,
            "readme_path": "README.md" if readme_enabled else None,
            "created_at": now,
            "updated_at": now,
            "archived_at": None,
        },
        owner={"id": owner.id, "handle": owner.handle, "display_name": owner.display_name},
        role="owner",
        repo=repo,
    )
    return project_payload(conn, ctx, principal)


def _author_email(owner: auth.Principal | dict[str, Any]) -> str:
    if isinstance(owner, dict):
        email = owner.get("email")
        handle = owner.get("handle", "researcher")
    else:
        email = owner.email
        handle = owner.handle
    return str(email or f"{handle}@users.quanthub.local")


def list_projects(
    conn: sqlite3.Connection,
    principal: auth.Principal,
    *,
    view: str = "discover",
    query: str = "",
    topic: str | None = None,
    owner: str | None = None,
    language: str | None = None,
    page: int = 1,
    per_page: int = 24,
    sort: str = "recent",
) -> dict[str, Any]:
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    where: list[str] = []
    params: list[Any] = []
    if view == "mine":
        auth.require_user(principal)
        where.append("(p.owner_id = ? OR EXISTS (SELECT 1 FROM project_members m WHERE m.project_id = p.id AND m.user_id = ?))")
        params.extend([principal.id, principal.id])
    elif view == "starred":
        auth.require_user(principal)
        where.append("EXISTS (SELECT 1 FROM stars s WHERE s.project_id = p.id AND s.user_id = ?)")
        params.append(principal.id)
    else:
        if principal.is_authenticated:
            where.append(
                "(p.visibility = 'public' OR p.owner_id = ? OR EXISTS"
                " (SELECT 1 FROM project_members m WHERE m.project_id = p.id AND m.user_id = ?))"
            )
            params.extend([principal.id, principal.id])
        else:
            where.append("p.visibility = 'public'")
    where.append("p.archived_at IS NULL")
    if query:
        needle = f"%{query.strip().lower()}%"
        where.append(
            "(lower(p.name) LIKE ? OR lower(p.slug) LIKE ? OR lower(p.description) LIKE ?"
            " OR lower(p.topics) LIKE ? OR lower(u.handle) LIKE ?)"
        )
        params.extend([needle] * 5)
    if topic:
        where.append("lower(p.topics) LIKE ?")
        params.append(f'%"{topic.strip().lower()}"%')
    if owner:
        where.append("lower(u.handle) = ?")
        params.append(owner.strip().lower())
    if language:
        where.append("lower(p.language) = ?")
        params.append(language.strip().lower())

    where_sql = " AND ".join(where)
    total_row = conn.execute(
        f"SELECT COUNT(*) AS n FROM projects p JOIN users u ON u.id = p.owner_id WHERE {where_sql}",
        params,
    ).fetchone()
    total = int(total_row["n"]) if total_row else 0
    rows = conn.execute(
        f"SELECT p.*, u.handle AS owner_handle, u.display_name AS owner_name"
        f" FROM projects p JOIN users u ON u.id = p.owner_id WHERE {where_sql}"
        f" ORDER BY {_order_clause(sort)} LIMIT ? OFFSET ?",
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()

    items = []
    for row in rows:
        project = dict(row)
        project["topics"] = db.json_load(project.get("topics"), [])
        revision = gitrepo.head_sha(repo_path_for(project["id"]), project["default_branch"])
        items.append(
            {
                "id": project["id"],
                "name": project["name"],
                "slug": project["slug"],
                "full_name": f"{project['owner_handle']}/{project['slug']}",
                "owner": {"handle": project["owner_handle"], "display_name": project["owner_name"]},
                "description": project["description"],
                "visibility": project["visibility"],
                "topics": project["topics"],
                "language": project["language"],
                "license": project["license_spdx"],
                "updated_at": project["updated_at"],
                "revision": revision,
                "stars": _count(conn, "stars", project["id"]),
                "kinds": _project_kinds(conn, project["id"]),
            }
        )
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": page * per_page < total,
    }


def _order_clause(sort: str) -> str:
    if sort == "stars":
        return (
            "(SELECT COUNT(*) FROM stars s WHERE s.project_id = p.id) DESC,"
            " p.updated_at DESC"
        )
    if sort == "name":
        return "lower(p.name) ASC, p.updated_at DESC"
    return "p.updated_at DESC, p.created_at DESC"


def _project_kinds(conn: sqlite3.Connection, project_id: str) -> list[str]:
    kinds: list[str] = []
    if conn.execute("SELECT 1 FROM experiment_specs WHERE project_id = ?", (project_id,)).fetchone():
        kinds.append("experiments")
    return kinds


def update_project(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    payload: dict[str, Any],
) -> dict[str, Any]:
    fields: list[str] = []
    values: list[Any] = []
    if "description" in payload:
        fields.append("description = ?")
        values.append(validation.clean_description(payload.get("description")))
    if "topics" in payload:
        fields.append("topics = ?")
        values.append(json.dumps(validation.clean_topics(payload.get("topics"))))
    if "website" in payload:
        fields.append("website = ?")
        values.append(validation.clean_website(payload.get("website")))
    if "visibility" in payload:
        visibility = validation.clean_visibility(payload.get("visibility"))
        if ctx.role != "owner":
            raise forbidden("Only the owner can change project visibility.")
        fields.append("visibility = ?")
        values.append(visibility)
    if "name" in payload:
        if ctx.role != "owner":
            raise forbidden("Only the owner can rename a project.")
        fields.append("name = ?")
        values.append(validation.clean_name(payload.get("name")))
    if "license" in payload:
        spdx = payload.get("license") or None
        if spdx and spdx not in {option.spdx for option in templates.LICENSES}:
            raise bad_request("UnknownLicense", f"Unknown license '{spdx}'.")
        fields.append("license_spdx = ?")
        values.append(spdx)
    if not fields:
        raise bad_request("NoChanges", "No supported fields were provided.")

    fields.append("updated_at = ?")
    values.append(db.utc_now())
    conn.execute(
        f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", [*values, ctx.id]
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="project.updated",
        payload={"fields": sorted(payload)},
    )
    refreshed = load_project(conn, ctx.owner_handle, ctx.project["slug"])
    refreshed.role = ctx.role
    return project_payload(conn, refreshed, principal)


def archive_project(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal
) -> dict[str, Any]:
    if ctx.role != "owner":
        raise forbidden("Only the owner can archive this project.")
    now = db.utc_now()
    conn.execute("UPDATE projects SET archived_at = ?, updated_at = ? WHERE id = ?", (now, now, ctx.id))
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="project.archived",
    )
    refreshed = load_project(conn, ctx.owner_handle, ctx.project["slug"])
    refreshed.role = ctx.role
    return project_payload(conn, refreshed, principal)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def _record_commit(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    sha: str,
    message: str,
    file_count: int,
) -> None:
    commits = gitrepo.log(ctx.repo, sha, limit=1)
    parent = commits[0].parents[0] if commits and commits[0].parents else None
    conn.execute(
        "INSERT OR IGNORE INTO commits (project_id, sha, parent_sha, message, author_name,"
        " author_email, author_id, created_at, file_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ctx.id,
            sha,
            parent,
            message,
            principal.display_name,
            principal.email or _author_email(principal),
            principal.id,
            db.utc_now(),
            file_count,
        ),
    )


def commit_changes(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    changes: dict[str, bytes | None],
    *,
    message: str,
    expected_revision: str | None | object = ...,
) -> dict[str, Any]:
    normalized: dict[str, bytes | None] = {}
    for raw_path, content in changes.items():
        path = gitrepo.normalize_repo_path(raw_path)
        conf = config.limits()
        if content is not None and len(content) > conf.max_file_bytes:
            raise bad_request(
                "FileTooLarge",
                f"'{path}' exceeds the {conf.max_file_bytes} byte file limit.",
                path=path,
            )
        normalized[path] = content
    if not normalized:
        raise bad_request("NoChanges", "No file changes were provided.")

    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    if expected_revision is not ... and expected_revision != revision:
        raise conflict(
            "RevisionConflict",
            "This project changed since you opened the file. Reload before saving.",
            expected_revision=expected_revision,
            current_revision=revision,
        )
    existing = gitrepo.count_files(ctx.repo, revision) if revision else 0
    creates = sum(
        1
        for path, content in normalized.items()
        if content is not None and not _path_exists(ctx.repo, revision, path)
    )
    if existing + creates > config.limits().max_repo_files:
        raise bad_request("TooManyFiles", "This change would exceed the project file limit.")

    sha, changed = gitrepo.commit_files(
        ctx.repo,
        branch=ctx.branch,
        changes=normalized,
        message=message,
        author_name=principal.display_name,
        author_email=principal.email or _author_email(principal),
        expected_head=expected_revision,
    )
    readme = gitrepo.find_readme(ctx.repo, sha)
    conn.execute(
        "UPDATE projects SET updated_at = ?, readme_path = ?, language = COALESCE(?, language)"
        " WHERE id = ?",
        (
            db.utc_now(),
            readme,
            _primary_language(normalized),
            ctx.id,
        ),
    )
    _record_commit(conn, ctx, principal, sha, message, len(normalized))
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="project.files_changed" if changed else "project.noop",
        payload={
            "revision": sha,
            "message": message,
            "files": [
                {"path": path, "deleted": content is None} for path, content in normalized.items()
            ][:50],
        },
    )
    return {"revision": sha, "changed": changed, "files": sorted(normalized)}


def _primary_language(changes: dict[str, bytes | None]) -> str | None:
    for path, content in changes.items():
        if content is not None and not path.startswith("."):
            spec = detect_language(path)
            if spec.id not in {"text", "unknown", "markdown"}:
                return spec.label
    return None


def _path_exists(repo: Path, revision: str | None, path: str) -> bool:
    if not revision:
        return False
    parent = path.rsplit("/", 1)[0] if "/" in path else ""
    try:
        entries = gitrepo.list_tree(repo, revision, parent)
    except HubError:
        return False
    return any(entry.path == path for entry in entries)


def tree_payload(
    ctx: ProjectContext, revision: str | None, path: str = ""
) -> dict[str, Any]:
    rev = revision or gitrepo.head_sha(ctx.repo, ctx.branch)
    if not rev:
        return {"revision": None, "path": path, "entries": [], "parent": None}
    clean = gitrepo.normalize_repo_path(path) if path else ""
    entries = gitrepo.list_tree(ctx.repo, rev, clean)
    items = []
    for entry in entries:
        item: dict[str, Any] = {
            "name": entry.name,
            "path": entry.path,
            "type": entry.type,
            "sha": entry.sha,
            "size": entry.size,
        }
        if entry.type == "blob":
            language = language_for_filename(entry.path)
            item["language"] = language["id"]
            item["label"] = language["label"]
        items.append(item)
    parent = clean.rsplit("/", 1)[0] if "/" in clean else None
    return {"revision": rev, "path": clean, "entries": items, "parent": parent}


def blob_payload(ctx: ProjectContext, revision: str | None, path: str) -> dict[str, Any]:
    rev = revision or gitrepo.head_sha(ctx.repo, ctx.branch)
    if not rev:
        raise not_found("This project has no files yet.")
    clean = gitrepo.normalize_repo_path(path)
    language = language_for_filename(clean)
    size = gitrepo.file_size(ctx.repo, rev, clean)
    if size is None:
        raise not_found("That file does not exist at this revision.")
    conf = config.limits()
    if size > conf.max_blob_view_bytes:
        return {
            "path": clean,
            "revision": rev,
            "size": size,
            "language": language,
            "binary": True,
            "too_large": True,
            "content": None,
            "message": "This file is larger than the in-browser preview limit. Download it instead.",
        }
    data = gitrepo.read_file(ctx.repo, rev, clean)
    binary = gitrepo.is_binary(data)
    content: str | None = None
    truncated = False
    if not binary:
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            binary = True
    if content is not None and len(content) > conf.max_blob_view_bytes:
        content = content[: conf.max_blob_view_bytes]
        truncated = True
    commits = gitrepo.log(ctx.repo, rev, limit=1, path=clean)
    return {
        "path": clean,
        "revision": rev,
        "size": size,
        "language": language,
        "binary": binary,
        "too_large": False,
        "truncated": truncated,
        "content": content,
        "editable": bool(language["editable"]) and not binary,
        "last_commit": (
            {
                "sha": commits[0].sha,
                "message": commits[0].message,
                "author_name": commits[0].author_name,
                "authored_at": commits[0].authored_at,
            }
            if commits
            else None
        ),
    }


def readme_payload(ctx: ProjectContext, revision: str | None) -> dict[str, Any] | None:
    rev = revision or gitrepo.head_sha(ctx.repo, ctx.branch)
    if not rev:
        return None
    path = gitrepo.find_readme(ctx.repo, rev)
    if not path:
        return None
    size = gitrepo.file_size(ctx.repo, rev, path) or 0
    if size > MAX_README_PREVIEW:
        return {"path": path, "content": None, "too_large": True}
    data = gitrepo.read_file(ctx.repo, rev, path)
    if gitrepo.is_binary(data):
        return None
    return {"path": path, "content": data.decode("utf-8", "replace"), "too_large": False}


def history_payload(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    *,
    limit: int = 25,
    path: str | None = None,
) -> list[dict[str, Any]]:
    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    commits = gitrepo.log(ctx.repo, revision, limit=limit, path=path)
    shas = [commit.sha for commit in commits]
    rows: dict[str, dict[str, Any]] = {}
    if shas:
        placeholders = ",".join("?" for _ in shas)
        for row in conn.execute(
            f"SELECT * FROM commits WHERE project_id = ? AND sha IN ({placeholders})",
            [ctx.id, *shas],
        ).fetchall():
            rows[row["sha"]] = dict(row)
    items = []
    for commit in commits:
        stored = rows.get(commit.sha, {})
        items.append(
            {
                "sha": commit.sha,
                "short_sha": commit.sha[:7],
                "message": commit.message,
                "author_name": commit.author_name,
                "authored_at": commit.authored_at,
                "parents": commit.parents,
                "files": stored.get("file_count"),
            }
        )
    return items


def activity_payload(
    conn: sqlite3.Connection,
    project_id: str | None,
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    if project_id:
        rows = conn.execute(
            "SELECT * FROM activity WHERE project_id = ? ORDER BY id DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [
        {
            "id": row["id"],
            "project_id": row["project_id"],
            "actor": row["actor_handle"],
            "type": row["type"],
            "payload": db.json_load(row["payload"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def star_project(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal, *, star: bool
) -> dict[str, Any]:
    auth.require_user(principal)
    if star:
        conn.execute(
            "INSERT OR IGNORE INTO stars (project_id, user_id, created_at) VALUES (?, ?, ?)",
            (ctx.id, principal.id, db.utc_now()),
        )
        db.record_activity(
            conn,
            project_id=ctx.id,
            actor_id=principal.id,
            actor_handle=principal.handle,
            event_type="project.starred",
        )
    else:
        conn.execute("DELETE FROM stars WHERE project_id = ? AND user_id = ?", (ctx.id, principal.id))
    return {"starred": star, "stars": _count(conn, "stars", ctx.id)}


def watch_project(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal, *, watch: bool
) -> dict[str, Any]:
    auth.require_user(principal)
    if watch:
        conn.execute(
            "INSERT OR IGNORE INTO watches (project_id, user_id, created_at) VALUES (?, ?, ?)",
            (ctx.id, principal.id, db.utc_now()),
        )
    else:
        conn.execute("DELETE FROM watches WHERE project_id = ? AND user_id = ?", (ctx.id, principal.id))
    return {"watching": watch, "watchers": _count(conn, "watches", ctx.id)}


# ---------------------------------------------------------------------------
# Imports and exports
# ---------------------------------------------------------------------------


class _Skipped:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, path: str, reason: str) -> None:
        if len(self.items) < 200:
            self.items.append({"path": path, "reason": reason})


def import_files(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    files: list[tuple[str, bytes]],
    *,
    message: str,
    kind: str = "upload",
    expected_revision: str | None | object = ...,
) -> dict[str, Any]:
    """Commit uploaded files, rejecting unsafe paths and oversize payloads."""
    conf = config.limits()
    total = sum(len(content) for _, content in files)
    if total > conf.max_upload_bytes:
        raise bad_request(
            "UploadTooLarge",
            f"Uploads are limited to {conf.max_upload_bytes} bytes.",
            bytes=total,
        )
    if len(files) > conf.max_files_per_upload:
        raise bad_request(
            "TooManyFiles",
            f"Uploads are limited to {conf.max_files_per_upload} files.",
            files=len(files),
        )
    skipped = _Skipped()
    changes: dict[str, bytes | None] = {}
    for raw_path, content in files:
        try:
            path = gitrepo.normalize_repo_path(raw_path)
        except HubError:
            skipped.add(raw_path, "unsafe or invalid path")
            continue
        if path in changes:
            skipped.add(path, "duplicate path in the same upload")
            continue
        if len(content) > conf.max_file_bytes:
            skipped.add(path, f"larger than {conf.max_file_bytes} bytes")
            continue
        changes[path] = content
    if not changes:
        raise bad_request("NoFilesAccepted", "No files in this upload were accepted.", skipped=skipped.items)

    job_id = "imp_" + uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO import_jobs (id, project_id, kind, status, files_written, bytes_written,"
        " skipped, created_at, finished_at) VALUES (?, ?, ?, 'running', 0, 0, ?, ?, NULL)",
        (job_id, ctx.id, kind, json.dumps(skipped.items), db.utc_now()),
    )
    result = commit_changes(
        conn,
        ctx,
        principal,
        changes,
        message=validation.clean_commit_message(message, default="Add files via QuantHub"),
        expected_revision=expected_revision,
    )
    conn.execute(
        "UPDATE import_jobs SET status = 'completed', files_written = ?, bytes_written = ?,"
        " commit_sha = ?, finished_at = ? WHERE id = ?",
        (len(changes), sum(len(value) for value in changes.values() if value), result["revision"], db.utc_now(), job_id),
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="project.imported",
        payload={
            "kind": kind,
            "files": len(changes),
            "bytes": sum(len(value) for value in changes.values() if value),
            "revision": result["revision"],
        },
    )
    return {
        "import_id": job_id,
        "revision": result["revision"],
        "files": sorted(changes),
        "skipped": skipped.items,
        "kind": kind,
        "preserved_history": False,
    }


def import_zip(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    archive_bytes: bytes,
    *,
    message: str,
) -> dict[str, Any]:
    conf = config.limits()
    if len(archive_bytes) > conf.max_upload_bytes:
        raise bad_request("ArchiveTooLarge", "That archive exceeds the upload size limit.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise bad_request("InvalidArchive", "That file is not a valid ZIP archive.") from exc
    skipped = _Skipped()
    entries: list[tuple[str, bytes]] = []
    total = 0
    with archive:
        infos = archive.infolist()
        if len(infos) > conf.max_zip_entries:
            raise bad_request(
                "ArchiveTooManyEntries",
                f"Archives are limited to {conf.max_zip_entries} entries.",
            )
        for info in infos:
            name = info.filename
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                skipped.add(name, "symbolic links are not imported")
                continue
            if info.flag_bits & 0x1:
                skipped.add(name, "encrypted entries are not supported")
                continue
            total += info.file_size
            if total > conf.max_zip_uncompressed_bytes:
                raise bad_request(
                    "ArchiveTooLarge",
                    "This archive expands beyond the configured limit.",
                    limit_bytes=conf.max_zip_uncompressed_bytes,
                )
            if info.file_size > conf.max_file_bytes:
                skipped.add(name, f"larger than {conf.max_file_bytes} bytes")
                continue
            # Read with a hard cap so a lying header cannot exhaust memory.
            with archive.open(info) as handle:
                data = handle.read(conf.max_file_bytes + 1)
            if len(data) > conf.max_file_bytes:
                skipped.add(name, "larger than the file limit after decompression")
                continue
            entries.append((name, data))

    # Strip a single common top-level directory (GitHub-style archives).
    names = [name.replace("\\", "/") for name, _ in entries]
    common = None
    if names and all("/" in name for name in names):
        first = names[0].split("/", 1)[0]
        if all(name.split("/", 1)[0] == first for name in names):
            common = first
    normalised: list[tuple[str, bytes]] = []
    for (name, data) in entries:
        clean = name.replace("\\", "/")
        if common:
            clean = clean.split("/", 1)[1]
        normalised.append((clean, data))
    if not normalised:
        raise bad_request("EmptyArchive", "That archive contains no importable files.")
    return import_files(
        conn,
        ctx,
        principal,
        normalised,
        message=message,
        kind="zip",
    )


def export_archive(ctx: ProjectContext, revision: str | None = None) -> tuple[Path, str]:
    rev = revision or gitrepo.head_sha(ctx.repo, ctx.branch)
    if not rev:
        raise not_found("This project has no files to export.")
    conf = config.limits()
    target_dir = config.data_dir() / "tmp"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{ctx.owner_handle}-{ctx.project['slug']}-{rev[:7]}.zip"
    destination = target_dir / f"{uuid.uuid4().hex}-{filename}"
    max_bytes = max(conf.max_upload_bytes, 128 * 1024 * 1024)
    gitrepo.write_archive(ctx.repo, rev, destination, max_bytes=max_bytes)
    return destination, filename


def delete_file(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    path: str,
    *,
    expected_revision: str | None | object = ...,
    message: str | None = None,
) -> dict[str, Any]:
    clean = gitrepo.normalize_repo_path(path)
    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    if not revision or not _path_exists(ctx.repo, revision, clean):
        raise not_found("That file does not exist.")
    return commit_changes(
        conn,
        ctx,
        principal,
        {clean: None},
        message=message or f"Delete {clean}",
        expected_revision=expected_revision,
    )


def move_file(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    source: str,
    destination: str,
    *,
    expected_revision: str | None | object = ...,
) -> dict[str, Any]:
    src = gitrepo.normalize_repo_path(source)
    dst = gitrepo.normalize_repo_path(destination)
    if src == dst:
        raise bad_request("NoChanges", "Source and destination are the same.")
    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    if not revision or not _path_exists(ctx.repo, revision, src):
        raise not_found("The file to move does not exist.")
    if _path_exists(ctx.repo, revision, dst):
        raise conflict("PathExists", f"'{dst}' already exists.", path=dst)
    data = gitrepo.read_file(ctx.repo, revision, src)
    return commit_changes(
        conn,
        ctx,
        principal,
        {dst: data, src: None},
        message=f"Rename {src} to {dst}",
        expected_revision=expected_revision,
    )


def copy_tree_to_disk(ctx: ProjectContext, destination: Path) -> None:  # pragma: no cover - ops helper
    """Materialise a project revision on disk (used for maintenance tasks)."""
    revision = gitrepo.head_sha(ctx.repo, ctx.branch)
    if not revision:
        return
    for entry in gitrepo.list_all_paths(ctx.repo, revision):
        target = destination / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gitrepo.read_file(ctx.repo, revision, entry.path))


def project_disk_usage(ctx: ProjectContext) -> int:
    if not ctx.repo.exists():
        return 0
    return sum(path.stat().st_size for path in ctx.repo.rglob("*") if path.is_file())


def cleanup_shadow_dirs() -> None:  # pragma: no cover - maintenance helper
    for path in config.data_dir().glob("tmp/*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


__all__ = [
    "ProjectContext",
    "archive_project",
    "blob_payload",
    "commit_changes",
    "create_project",
    "delete_file",
    "export_archive",
    "history_payload",
    "import_files",
    "import_zip",
    "list_projects",
    "load_project",
    "move_file",
    "project_payload",
    "readme_payload",
    "require_project",
    "star_project",
    "tree_payload",
    "update_project",
    "watch_project",
]

