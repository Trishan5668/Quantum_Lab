"""Regression tests for runtime database creation and migration.

The runtime database is derived state that used to be created ad hoc with an
unversioned ``CREATE TABLE IF NOT EXISTS`` script.  These tests pin the
replacement contract:

* first start creates the schema and records ``SCHEMA_VERSION``;
* repeated starts are idempotent and preserve existing rows;
* a database from a *newer* release is refused instead of being corrupted;
* a database without a recorded version (the pre-migration shape) is upgraded
  in place, never dropped;
* concurrent starters serialise instead of racing;
* an unusable path raises a loud, path-bearing error.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest
from app.quanthub import db as hub_db
from app.quanthub.config import db_path


@pytest.fixture()
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Path:
    target = tmp_path / "runtime"
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(target))
    hub_db.reset_init_cache()
    yield target
    hub_db.reset_init_cache()


def schema_version(path: Path) -> int:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
    return int(row[0])


def table_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as conn:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }


def test_init_creates_versioned_schema(data_dir: Path) -> None:
    hub_db.init_db()
    path = db_path()
    assert path.exists()
    assert schema_version(path) == hub_db.SCHEMA_VERSION
    expected = {
        "schema_meta",
        "users",
        "projects",
        "project_members",
        "commits",
        "stars",
        "watches",
        "experiment_specs",
        "runs",
        "activity",
        "import_jobs",
        "news_cache",
    }
    assert expected <= table_names(path)


def test_init_is_idempotent_and_preserves_rows(data_dir: Path) -> None:
    hub_db.init_db()
    path = db_path()
    with hub_db.db() as conn:
        conn.execute(
            "INSERT INTO users (id, handle, display_name, email, created_at)"
            " VALUES ('u1', 'alice', 'Alice', NULL, '2026-01-01T00:00:00Z')"
        )
    hub_db.reset_init_cache()
    hub_db.init_db()
    hub_db.init_db()
    assert schema_version(path) == hub_db.SCHEMA_VERSION
    with hub_db.db() as conn:
        rows = conn.execute("SELECT id FROM users").fetchall()
    assert [row["id"] for row in rows] == ["u1"]


def test_newer_schema_is_refused(data_dir: Path) -> None:
    hub_db.init_db()
    path = db_path()
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
            (str(hub_db.SCHEMA_VERSION + 1),),
        )
    hub_db.reset_init_cache()
    with pytest.raises(hub_db.DatabaseInitializationError, match="newer QuantHub"):
        hub_db.init_db()
    # The database is left untouched rather than downgraded or dropped.
    assert schema_version(path) == hub_db.SCHEMA_VERSION + 1


def test_unversioned_database_is_upgraded_in_place(data_dir: Path) -> None:
    """A database written before versioning has tables but no version row."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = db_path()
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE users (id TEXT PRIMARY KEY, handle TEXT UNIQUE NOT NULL,"
            " display_name TEXT NOT NULL, email TEXT, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO users VALUES ('legacy', 'legacy', 'Legacy', NULL, '2025-01-01')"
        )
    hub_db.reset_init_cache()
    hub_db.init_db()
    assert schema_version(path) == hub_db.SCHEMA_VERSION
    with hub_db.db() as conn:
        row = conn.execute("SELECT handle FROM users WHERE id = 'legacy'").fetchone()
    assert row["handle"] == "legacy"


def test_non_integer_schema_version_is_refused(data_dir: Path) -> None:
    hub_db.init_db()
    path = db_path()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE schema_meta SET value = 'v1' WHERE key = 'schema_version'")
    hub_db.reset_init_cache()
    with pytest.raises(hub_db.DatabaseInitializationError, match="not an integer"):
        hub_db.init_db()


def test_unusable_path_fails_loudly(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("this is a file, not a directory", encoding="utf-8")
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(blocker / "nested"))
    hub_db.reset_init_cache()
    with pytest.raises((hub_db.DatabaseInitializationError, NotADirectoryError, PermissionError)):
        hub_db.init_db()
    hub_db.reset_init_cache()


def test_concurrent_first_starts_serialise(data_dir: Path) -> None:
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def start() -> None:
        try:
            barrier.wait()
            hub_db.init_db()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            errors.append(exc)

    threads = [threading.Thread(target=start) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not errors, errors
    assert schema_version(db_path()) == hub_db.SCHEMA_VERSION


def test_reset_init_cache_forces_revalidation(data_dir: Path) -> None:
    hub_db.init_db()
    hub_db.reset_init_cache()
    # Deleting the file and re-initialising must recreate it, which proves the
    # cache is a performance optimisation rather than the source of truth.
    db_path().unlink()
    hub_db.init_db()
    assert db_path().exists()
    assert schema_version(db_path()) == hub_db.SCHEMA_VERSION


def test_db_path_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    explicit = tmp_path / "custom" / "state.sqlite3"
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("QUANTHUB_DB_PATH", str(explicit))
    hub_db.reset_init_cache()
    hub_db.init_db()
    assert explicit.exists()
    assert schema_version(explicit) == hub_db.SCHEMA_VERSION
    hub_db.reset_init_cache()
