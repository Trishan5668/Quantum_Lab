"""Integration tests for QuantHub projects, permissions and file operations."""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from typing import Any

import pytest
from app.main import create_app
from app.quanthub import db as hub_db
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("QUANTHUB_ENV", "test")
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    monkeypatch.setenv("QUANTHUB_NEWS_FEEDS", "")
    hub_db.reset_init_cache()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def auth(handle: str = "alice") -> dict[str, str]:
    return {
        "X-QuantHub-User": handle,
        "X-QuantHub-Name": handle.title(),
        "X-QuantHub-Email": f"{handle}@example.org",
    }


def create(client: TestClient, handle: str = "alice", **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Hadamard Bench",
        "description": "A small circuit benchmark.",
        "visibility": "public",
        "topics": ["qec", "circuits"],
        **overrides,
    }
    response = client.post("/api/v1/projects", json=payload, headers=auth(handle))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["error"] is None
    return body["data"]


def test_guest_cannot_create_project(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json={"name": "Nope"})
    assert response.status_code == 401
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "Unauthorized"


def test_me_reports_authenticated_identity(client: TestClient) -> None:
    response = client.get("/api/v1/me", headers=auth("ada"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["handle"] == "ada"
    assert data["authenticated"] is True


def test_create_public_project_initialises_readme_gitignore_license(client: TestClient) -> None:
    project = create(
        client,
        initialize_readme=True,
        gitignore_template="python",
        license="MIT",
    )
    assert project["visibility"] == "public"
    assert project["default_branch"] == "main"
    assert project["revision"]
    assert project["license"] == "MIT"

    tree = client.get(f"/api/v1/projects/alice/{project['slug']}/tree").json()["data"]
    names = {entry["name"] for entry in tree["entries"]}
    assert {"README.md", ".gitignore", "LICENSE"} <= names

    blob = client.get(
        f"/api/v1/projects/alice/{project['slug']}/blob",
        params={"path": "README.md"},
    ).json()["data"]
    assert "## Experiments" in blob["content"]
    assert "## Results and reproducibility" in blob["content"]
    assert blob["language"]["id"] == "markdown"

    license_blob = client.get(
        f"/api/v1/projects/alice/{project['slug']}/blob", params={"path": "LICENSE"}
    ).json()["data"]
    assert "MIT License" in license_blob["content"]
    assert "Alice" in license_blob["content"]

    commits = client.get(f"/api/v1/projects/alice/{project['slug']}/commits").json()["data"]
    assert len(commits["commits"]) == 1
    assert commits["commits"][0]["message"] == "Initial commit"


def test_private_project_is_isolated_from_other_users(client: TestClient) -> None:
    project = create(client, visibility="private", name="Secret QEC")
    path = f"/api/v1/projects/alice/{project['slug']}"

    anonymous = client.get(path)
    assert anonymous.status_code == 403
    assert anonymous.json()["error"]["code"] == "Forbidden"

    other = client.get(path, headers=auth("mallory"))
    assert other.status_code == 403

    owner = client.get(path, headers=auth("alice"))
    assert owner.status_code == 200

    # private projects must not leak through listing, search or discovery
    listing = client.get("/api/v1/projects", params={"q": "secret"}).json()["data"]
    assert listing["items"] == []
    mine = client.get("/api/v1/projects", params={"view": "mine"}, headers=auth("alice")).json()["data"]
    assert any(item["slug"] == project["slug"] for item in mine["items"])


def test_private_project_file_writes_require_membership(client: TestClient) -> None:
    project = create(client, visibility="private", name="Private Files")
    base = f"/api/v1/projects/alice/{project['slug']}"
    payload = {"path": "notes.md", "content": "# notes\n"}

    denied = client.put(f"{base}/contents", json=payload, headers=auth("mallory"))
    assert denied.status_code == 403

    allowed = client.put(f"{base}/contents", json=payload, headers=auth("alice"))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["data"]["changed"] is True


def test_project_name_and_slug_validation(client: TestClient) -> None:
    cases = [
        ({"name": ""}, "InvalidName"),
        ({"name": "!!!"}, "InvalidName"),
        ({"name": "x" * 101}, "InvalidName"),
        ({"name": "ok", "slug": "has space"}, "InvalidSlug"),
        ({"name": "ok", "slug": "../etc"}, "InvalidSlug"),
        ({"name": "ok", "slug": "settings"}, "ReservedSlug"),
        ({"name": "ok", "topics": ["Bad Topic!"]}, "InvalidTopic"),
        ({"name": "ok", "visibility": "secret"}, "InvalidVisibility"),
        ({"name": "ok", "license": "WTFPL"}, "UnknownLicense"),
        ({"name": "ok", "website": "javascript:alert(1)"}, "InvalidWebsite"),
    ]
    for payload, code in cases:
        response = client.post("/api/v1/projects", json=payload, headers=auth())
        assert response.status_code == 400, (payload, response.text)
        assert response.json()["error"]["code"] == code


def test_duplicate_slug_is_reported(client: TestClient) -> None:
    create(client, name="Taken Name", slug="taken")
    response = client.post(
        "/api/v1/projects",
        json={"name": "Taken Name", "slug": "taken"},
        headers=auth(),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SlugTaken"


def test_duplicate_name_allocates_a_suffix(client: TestClient) -> None:
    first = create(client, name="Same Name")
    second = create(client, name="Same Name")
    assert first["slug"] == "same-name"
    assert second["slug"] == "same-name-1"


def test_file_write_rejects_traversal_and_stale_revisions(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    revision = project["revision"]

    for bad_path in ["../escape.py", "/etc/passwd", "a/../../b.py", ".git/config"]:
        response = client.put(
            f"{base}/contents", json={"path": bad_path, "content": "x"}, headers=auth()
        )
        assert response.status_code == 400, bad_path
        assert response.json()["error"]["code"] == "InvalidPath"

    first = client.put(
        f"{base}/contents",
        json={"path": "src/main.py", "content": "print('hi')\n", "expected_revision": revision},
        headers=auth(),
    )
    assert first.status_code == 200, first.text
    new_revision = first.json()["data"]["revision"]

    stale = client.put(
        f"{base}/contents",
        json={"path": "src/main.py", "content": "print('oops')\n", "expected_revision": revision},
        headers=auth(),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "RevisionConflict"

    fresh = client.put(
        f"{base}/contents",
        json={"path": "src/main.py", "content": "print('hi')\n", "expected_revision": new_revision},
        headers=auth(),
    )
    assert fresh.status_code == 200

    blob = client.get(f"{base}/blob", params={"path": "src/main.py"}).json()["data"]
    assert blob["language"]["id"] == "python"
    assert blob["editable"] is True
    assert blob["last_commit"]["message"].startswith("Update src/main.py")


def test_move_and_delete_files(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    client.put(f"{base}/contents", json={"path": "a.txt", "content": "hello"}, headers=auth())
    moved = client.post(
        f"{base}/contents/move",
        json={"from_path": "a.txt", "to_path": "docs/b.txt"},
        headers=auth(),
    )
    assert moved.status_code == 200, moved.text
    assert client.get(f"{base}/blob", params={"path": "a.txt"}).status_code == 404
    assert client.get(f"{base}/blob", params={"path": "docs/b.txt"}).json()["data"]["content"] == "hello"

    deleted = client.delete(f"{base}/contents", params={"path": "docs/b.txt"}, headers=auth())
    assert deleted.status_code == 200
    assert client.get(f"{base}/blob", params={"path": "docs/b.txt"}).status_code == 404


def test_language_registry_covers_requested_formats(client: TestClient) -> None:
    registry = client.get("/api/v1/capabilities/languages").json()["data"]
    by_id = {entry["id"]: entry for entry in registry["languages"]}
    required = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "java": ".java",
        "cpp": ".cpp",
        "csharp": ".cs",
        "c": ".c",
        "go": ".go",
        "rust": ".rs",
        "sql": ".sql",
        "php": ".php",
        "kotlin": ".kt",
        "swift": ".swift",
        "ruby": ".rb",
        "r": ".R",
        "html": ".html",
        "css": ".css",
        "matlab": ".m",
        "scala": ".scala",
        "shell": ".sh",
        "example": ".example",
        "yaml": ".yml",
        "rules": ".rules",
        "text": ".txt",
        "toml": ".toml",
        "perl": ".pl",
    }
    for language, extension in required.items():
        assert language in by_id, language
        assert extension in by_id[language]["extensions"], (language, extension)
    assert by_id["dockerfile"]["filenames"] == ["Dockerfile", "Containerfile"]
    assert by_id["yaml"]["mode"] == "yaml"
    assert by_id["toml"]["mode"] == "ini"
    # execution must not be claimed for any repository language
    assert all(entry["execution"]["supported"] is False for entry in registry["languages"])


def test_upload_files_preserves_directories_and_reports_conflicts(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    files = [
        ("files", ("main.py", b"print(1)\n", "text/plain")),
        ("files", ("pkg/mod.py", b"x = 1\n", "text/plain")),
        ("files", ("data/readme.txt", b"hello\n", "text/plain")),
    ]
    paths = json.dumps(["main.py", "pkg/mod.py", "data/readme.txt"])
    response = client.post(
        f"{base}/upload",
        files=files,
        data={"paths": paths, "message": "Import local project"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["preserved_history"] is False
    assert sorted(data["files"]) == ["data/readme.txt", "main.py", "pkg/mod.py"]

    tree = client.get(f"{base}/tree", params={"path": "pkg"}).json()["data"]
    assert [entry["name"] for entry in tree["entries"]] == ["mod.py"]


def test_upload_rejects_path_traversal_entries(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    files = [("files", ("../evil.sh", b"rm -rf /\n", "text/plain"))]
    response = client.post(
        f"{base}/upload",
        files=files,
        data={"paths": json.dumps(["../evil.sh"])},
        headers=auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NoFilesAccepted"


def test_zip_import_preserves_structure(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("myresearch/README.md", "# imported\n")
        archive.writestr("myresearch/src/run.py", "print('run')\n")
        archive.writestr("myresearch/.gitignore", "*.pyc\n")
    response = client.post(
        f"{base}/import/zip",
        files={"archive": ("project.zip", buffer.getvalue(), "application/zip")},
        data={"message": "Import zip"},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "src/run.py" in data["files"]
    assert "README.md" in data["files"]
    blob = client.get(f"{base}/blob", params={"path": "src/run.py"}).json()["data"]
    assert blob["content"] == "print('run')\n"


def test_zip_import_rejects_traversal_and_unsafe_entries(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../etc/passwd", "root:x:0:0\n")
        archive.writestr("safe.txt", "safe\n")
    response = client.post(
        f"{base}/import/zip",
        files={"archive": ("evil.zip", buffer.getvalue(), "application/zip")},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["files"] == ["safe.txt"]
    assert any("unsafe" in item["reason"] for item in data["skipped"])


def test_zip_import_rejects_invalid_archives(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    response = client.post(
        f"{base}/import/zip",
        files={"archive": ("bad.zip", b"not a zip", "application/zip")},
        headers=auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "InvalidArchive"


def test_archive_download_returns_zip(client: TestClient) -> None:
    project = create(client)
    response = client.get(f"/api/v1/projects/alice/{project['slug']}/archive")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "README.md" in archive.namelist()


def test_binary_files_are_flagged_not_edited(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    client.post(
        f"{base}/upload",
        files=[("files", ("artifacts/state.npy", b"\x93NUMPY\x00\x01", "application/octet-stream"))],
        data={"paths": json.dumps(["artifacts/state.npy"])},
        headers=auth(),
    )
    blob = client.get(f"{base}/blob", params={"path": "artifacts/state.npy"}).json()["data"]
    assert blob["binary"] is True
    assert blob["editable"] is False
    assert blob["content"] is None
    raw = client.get(f"{base}/raw", params={"path": "artifacts/state.npy"})
    assert raw.status_code == 200
    assert raw.content.startswith(b"\x93NUMPY")


def test_about_metadata_updates_and_permissions(client: TestClient) -> None:
    project = create(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    denied = client.patch(f"{base}", json={"description": "hijack"}, headers=auth("mallory"))
    assert denied.status_code == 403

    updated = client.patch(
        f"{base}",
        json={"description": "Updated description", "topics": ["surface-code"], "website": "https://example.org"},
        headers=auth(),
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()["data"]
    assert data["description"] == "Updated description"
    assert data["topics"] == ["surface-code"]
    assert data["website"] == "https://example.org"

    archived = client.delete(f"{base}", headers=auth())
    assert archived.status_code == 200
    assert archived.json()["data"]["archived"] is True
    assert client.get(f"/api/v1/projects/{'alice'}/{project['slug']}").status_code == 404


def test_activity_and_dashboard(client: TestClient) -> None:
    create(client, name="Public One")
    create(client, name="Hidden One", visibility="private")

    activity = client.get("/api/v1/activity").json()["data"]["activity"]
    assert activity
    assert all(item["project"]["full_name"] != "alice/hidden-one" for item in activity)

    dashboard = client.get("/api/v1/dashboard", headers=auth()).json()["data"]
    assert dashboard["viewer"]["handle"] == "alice"
    assert any(project["slug"] == "public-one" for project in dashboard["trending_projects"])
    assert dashboard["news"]["items"]
    assert {tool["id"] for tool in dashboard["tools"]} == {"circuit-designer", "qec-workbench"}


def test_identity_headers_can_be_disabled(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "secure"))
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "0")
    hub_db.reset_init_cache()
    app = create_app()
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/projects", json={"name": "Nope"}, headers=auth())
        assert response.status_code == 401
        assert test_client.get("/api/v1/me").json()["data"]["authenticated"] is False
