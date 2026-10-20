"""SQLite persistence for QuantHub project metadata.

Authoritative state
-------------------
* Project records, membership, and visibility live in SQLite.
* File contents live in a real Git repository per project (see ``gitrepo``).
* Experiment specifications and run metadata live in SQLite; run *evidence*
  (artifact directories written by the scientific engine) lives on disk and is
  never rewritten once committed.
* Binary payloads never pass through Firestore.

The schema is applied through a small, ordered migration set recorded in
``schema_meta.schema_version``.  Initialisation takes an immediate write lock so
several workers starting at once cannot interleave migrations, refuses to open a
database written by a newer release, and never drops data.  The database is
derived state: it is created on first start and is not shipped in source control.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.quanthub.config import db_path

SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
    topics TEXT NOT NULL DEFAULT '[]',
    website TEXT,
    license_spdx TEXT,
    default_branch TEXT NOT NULL DEFAULT 'main',
    language TEXT,
    readme_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    UNIQUE (owner_id, slug)
);

CREATE TABLE IF NOT EXISTS project_members (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'maintainer', 'reader')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE IF NOT EXISTS commits (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sha TEXT NOT NULL,
    parent_sha TEXT,
    message TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT,
    author_id TEXT,
    created_at TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, sha)
);

CREATE TABLE IF NOT EXISTS stars (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE IF NOT EXISTS watches (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE IF NOT EXISTS experiment_specs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL,
    config_hash TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (project_id, slug)
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    spec_id TEXT REFERENCES experiment_specs(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    config_hash TEXT,
    project_revision TEXT,
    artifacts_path TEXT,
    summary TEXT,
    error TEXT,
    exit_code INTEGER,
    log_path TEXT,
    software_revision TEXT,
    protocol TEXT,
    reproduction_of TEXT,
    actor_id TEXT,
    actor_handle TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    actor_id TEXT,
    actor_handle TEXT,
    type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    files_written INTEGER NOT NULL DEFAULT 0,
    bytes_written INTEGER NOT NULL DEFAULT 0,
    skipped TEXT NOT NULL DEFAULT '[]',
    commit_sha TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS news_cache (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_visibility ON projects(visibility, updated_at);
CREATE INDEX IF NOT EXISTS idx_commits_project_time ON commits(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_activity_project_time ON activity(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_project_time ON runs(project_id, created_at);
"""


#: Ordered migrations.  ``MIGRATIONS[n]`` upgrades a database at version
#: ``n - 1`` to version ``n``.  Every statement must be additive and idempotent
#: (``IF NOT EXISTS``): initialisation must never drop user data.
MIGRATIONS: dict[int, str] = {1: SCHEMA_V1}


class DatabaseInitializationError(RuntimeError):
    """Raised when the runtime database cannot be created or upgraded safely."""


def _statements(script: str) -> Iterator[str]:
    """Split a SQL script on statement boundaries.

    Uses :func:`sqlite3.complete_statement` rather than splitting on ``;`` so a
    semicolon inside a string literal cannot corrupt the schema.
    """
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    tail = buffer.strip()
    if tail:
        yield tail


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_initialised: set[str] = set()
_init_lock = threading.Lock()

_LOCK_RETRIES = 5
_LOCK_BACKOFF_SECONDS = 0.2


def _read_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError) as exc:
        raise DatabaseInitializationError(
            "schema_meta.schema_version is not an integer; refusing to guess."
        ) from exc


def _apply_migrations(target: Path) -> None:
    conn = sqlite3.connect(target, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        # BEGIN IMMEDIATE serialises concurrent starters: the second worker waits
        # for the first to commit, then finds the schema already current.
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta ("
                " key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            current = _read_schema_version(conn)
            if current > SCHEMA_VERSION:
                raise DatabaseInitializationError(
                    f"The database at {target} was written by a newer QuantHub "
                    f"release (schema {current} > {SCHEMA_VERSION}). Upgrade the "
                    "application or point QUANTHUB_DATA_DIR at another directory; "
                    "QuantHub will not downgrade a database in place."
                )
            for version in range(current + 1, SCHEMA_VERSION + 1):
                for statement in _statements(MIGRATIONS[version]):
                    conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(SCHEMA_VERSION),),
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def init_db(path: Path | None = None) -> None:
    """Create or upgrade the runtime database.

    Safe to call repeatedly and from several workers: migrations run under an
    immediate write lock, and a process-local cache avoids the repeated cost.
    Failures raise :class:`DatabaseInitializationError` with the database path
    so a broken deployment fails loudly instead of serving an empty schema.
    """
    target = path or db_path()
    key = str(target)
    if key in _initialised:
        return
    with _init_lock:
        if key in _initialised:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(1, _LOCK_RETRIES + 1):
            try:
                _apply_migrations(target)
                break
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < _LOCK_RETRIES:
                    time.sleep(_LOCK_BACKOFF_SECONDS * attempt)
                    continue
                raise DatabaseInitializationError(
                    f"Could not initialise the QuantHub database at {target}: {exc}"
                ) from exc
            except sqlite3.Error as exc:
                raise DatabaseInitializationError(
                    f"Could not initialise the QuantHub database at {target}: {exc}"
                ) from exc
        _initialised.add(key)


def reset_init_cache() -> None:
    """Used by tests that point ``QUANTHUB_DATA_DIR`` at a temporary path."""
    _initialised.clear()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def record_activity(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    actor_id: str | None,
    actor_handle: str | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO activity (project_id, actor_id, actor_handle, type, payload, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            project_id,
            actor_id,
            actor_handle,
            event_type,
            json.dumps(payload or {}, sort_keys=True),
            utc_now(),
        ),
    )
