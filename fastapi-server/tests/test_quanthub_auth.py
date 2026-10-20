"""Regression tests for the authentication and configuration boundary.

Every test here pins a specific historical failure mode:

* the backend read the frontend ``VITE_FIREBASE_PROJECT_ID`` variable;
* unverified ``X-QuantHub-*`` headers were trusted unless ``QUANTHUB_ENV`` was
  exactly ``production`` (fail-open);
* ``QUANTHUB_ALLOW_LOCAL_IDENTITY`` was documented but never read;
* ``firebase_admin`` was optional and its absence silently degraded to
  unauthenticated;
* an unexpected exception returned the full Python traceback to the client;
* a verified Firebase identity could be written under a different primary key
  than the one used for project ownership.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from app.main import create_app
from app.quanthub import auth as hub_auth
from app.quanthub import db as hub_db
from app.quanthub.config import (
    ConfigError,
    firebase_project_id,
    trust_client_identity,
    validate_configuration,
)
from fastapi.testclient import TestClient

PROJECT = "quanthub-test-project"


@pytest.fixture()
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    """Neutral environment: no Firebase config, no identity headers trusted."""
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("QUANTHUB_NEWS_FEEDS", "")
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("QUANTHUB_FIREBASE_PROJECT", raising=False)
    monkeypatch.delenv("QUANTHUB_TRUST_CLIENT_IDENTITY", raising=False)
    monkeypatch.delenv("QUANTHUB_ENV", raising=False)
    hub_db.reset_init_cache()
    yield
    hub_db.reset_init_cache()


@pytest.fixture()
def client(isolated: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("QUANTHUB_ENV", "test")
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    with TestClient(create_app()) as test_client:
        yield test_client


def identity_headers(handle: str = "alice") -> dict[str, str]:
    return {
        "X-QuantHub-User": handle,
        "X-QuantHub-Name": handle.title(),
        "X-QuantHub-Email": f"{handle}@example.org",
    }


def fake_verifier(monkeypatch: pytest.MonkeyPatch, claims: dict[str, Any]) -> None:
    """Replace the Firebase SDK seam; the SDK is never called in tests."""

    def _verify(token: str, project: str) -> dict[str, Any]:
        assert project == PROJECT
        return dict(claims)

    monkeypatch.setattr(hub_auth, "_verify_id_token_with_sdk", _verify)


def valid_claims(**overrides: Any) -> dict[str, Any]:
    import time

    claims: dict[str, Any] = {
        "uid": "firebase-uid-1234",
        "sub": "firebase-uid-1234",
        "aud": PROJECT,
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "exp": int(time.time()) + 3600,
        "email": "Dana.Quanta@example.org",
        "name": "Dana Quanta",
    }
    claims.update(overrides)
    return claims


# ---------------------------------------------------------------------------
# 1. Canonical project variable
# ---------------------------------------------------------------------------


def test_canonical_firebase_project_id_is_used(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    assert firebase_project_id() == PROJECT


def test_frontend_vite_variable_is_not_backend_truth(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VITE_FIREBASE_PROJECT_ID", "frontend-only")
    assert firebase_project_id() is None


def test_legacy_alias_still_resolves_and_warns(
    isolated: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("QUANTHUB_FIREBASE_PROJECT", PROJECT)
    with caplog.at_level("WARNING"):
        assert firebase_project_id() == PROJECT
    assert "legacy alias" in caplog.text


def test_canonical_variable_wins_over_deprecated_alias(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    monkeypatch.setenv("QUANTHUB_FIREBASE_PROJECT", "old-project")
    assert firebase_project_id() == PROJECT


# ---------------------------------------------------------------------------
# 2. Fail-closed identity headers
# ---------------------------------------------------------------------------


def test_headers_are_not_trusted_when_environment_is_unset(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    assert trust_client_identity() is False


@pytest.mark.parametrize("env", ["production", "Production", "prod", ""])
def test_headers_are_not_trusted_outside_development(
    isolated: None, monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", env)
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    # An unknown environment is rejected outright rather than treated as dev.
    with pytest.raises(ConfigError):
        validate_configuration()
    assert trust_client_identity() is False


@pytest.mark.parametrize("env", ["development", "test"])
def test_headers_are_trusted_only_in_development_and_test(
    isolated: None, monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", env)
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    assert trust_client_identity() is True
    validate_configuration()


def test_invalid_flag_value_is_rejected_and_fails_closed(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", "development")
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "yes-please")
    with pytest.raises(ConfigError):
        validate_configuration()
    assert trust_client_identity() is False


def test_production_without_project_id_refuses_to_start(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", "production")
    with pytest.raises(ConfigError, match="FIREBASE_PROJECT_ID"):
        create_app()


def test_production_with_project_id_starts(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", "production")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    create_app()


def test_production_without_firebase_sdk_refuses_to_start(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.quanthub import config as hub_config

    monkeypatch.setenv("QUANTHUB_ENV", "production")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    monkeypatch.setattr(hub_config, "firebase_admin_available", lambda: False)
    with pytest.raises(ConfigError, match="firebase-admin"):
        hub_config.validate_configuration()


def test_identity_headers_are_ignored_in_production(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTHUB_ENV", "production")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    with TestClient(create_app()) as production_client:
        response = production_client.post(
            "/api/v1/projects", json={"name": "Sneaky"}, headers=identity_headers()
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "Unauthorized"


# ---------------------------------------------------------------------------
# 3. Bearer token verification
# ---------------------------------------------------------------------------


def test_bearer_token_without_configured_project_is_rejected(
    isolated: None,
) -> None:
    with pytest.raises(Exception) as excinfo:
        hub_auth.verify_bearer_token("some.jwt.value")
    assert getattr(excinfo.value, "status_code", None) == 401


def test_verified_token_produces_principal_keyed_by_firebase_subject(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    fake_verifier(monkeypatch, valid_claims())
    principal = hub_auth.verify_bearer_token("token")
    assert principal.id == "firebase-uid-1234"
    assert principal.email == "Dana.Quanta@example.org"
    assert principal.is_authenticated is True
    assert principal.source == "firebase"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "another-project"},
        {"iss": "https://securetoken.google.com/another-project"},
        {"exp": 1},
        {"uid": "", "sub": ""},
    ],
    ids=["wrong-audience", "wrong-issuer", "expired", "missing-subject"],
)
def test_token_claim_failures_are_single_opaque_401(
    isolated: None, monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    fake_verifier(monkeypatch, valid_claims(**overrides))
    with pytest.raises(Exception) as excinfo:
        hub_auth.verify_bearer_token("token")
    error = excinfo.value
    assert getattr(error, "status_code", None) == 401
    assert "token" in str(error).lower()
    assert "another-project" not in str(error)


def test_sdk_failure_is_a_401_and_never_leaks_the_token(
    isolated: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    secret = "eyJhbGciOiJSUzI1NiJ9.super-secret-token.signature"

    def _boom(token: str, project: str) -> dict[str, Any]:
        raise ValueError(f"invalid token {token}")

    monkeypatch.setattr(hub_auth, "_verify_id_token_with_sdk", _boom)
    with caplog.at_level("WARNING"), pytest.raises(Exception) as excinfo:
        hub_auth.verify_bearer_token(secret)
    assert getattr(excinfo.value, "status_code", None) == 401
    assert secret not in caplog.text
    assert secret not in str(excinfo.value)


# ---------------------------------------------------------------------------
# 4. Principal wire format and ownership key
# ---------------------------------------------------------------------------


def test_guest_principal_reports_guest_mode(client: TestClient) -> None:
    body = client.get("/api/v1/me").json()["data"]
    assert body["authenticated"] is False
    assert body["mode"] == "guest"


def test_local_principal_reports_local_mode(client: TestClient) -> None:
    body = client.get("/api/v1/me", headers=identity_headers("bob")).json()["data"]
    assert body["authenticated"] is True
    assert body["mode"] == "local"


def test_verified_token_principal_owns_projects_by_firebase_subject(
    isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    fake_verifier(monkeypatch, valid_claims())
    headers = {"Authorization": "Bearer token"}
    with TestClient(create_app()) as token_client:
        created = token_client.post(
            "/api/v1/projects", json={"name": "Token Owned"}, headers=headers
        )
        assert created.status_code == 201, created.text
        project_id = created.json()["data"]["id"]
        with hub_db.db() as conn:
            row = conn.execute(
                "SELECT owner_id FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            handle = conn.execute(
                "SELECT handle FROM users WHERE id = ?", ("firebase-uid-1234",)
            ).fetchone()["handle"]
        assert row["owner_id"] == "firebase-uid-1234"
        # The owner can read their own project back through the public route.
        detail = token_client.get(
            f"/api/v1/projects/{handle}/{created.json()['data']['slug']}",
            headers=headers,
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["id"] == project_id


def test_handle_collision_keeps_ownership_and_returns_stored_handle(
    isolated: None,
) -> None:
    """Two Firebase users with the same email local part must not collide."""
    hub_db.init_db()
    with hub_db.db() as conn:
        first = hub_auth.upsert_user(
            conn, handle="dana", name="Dana", email="dana@a.example", user_id="uid-one"
        )
        second = hub_auth.upsert_user(
            conn, handle="dana", name="Dana", email="dana@b.example", user_id="uid-two"
        )
        handles = {
            row["handle"]: row["id"]
            for row in conn.execute("SELECT handle, id FROM users").fetchall()
        }
    assert first.handle == "dana"
    assert first.id == "uid-one"
    assert second.id == "uid-two"
    assert second.handle != first.handle
    assert handles[first.handle] == "uid-one"
    assert handles[second.handle] == "uid-two"


# ---------------------------------------------------------------------------
# 5. Error responses must not leak internals
# ---------------------------------------------------------------------------


def test_unexpected_exception_hides_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import exceptions as app_exceptions

    monkeypatch.setenv("QUANTHUB_ENV", "test")
    app = create_app()

    @app.get("/api/v1/_boom")
    async def boom() -> None:
        raise RuntimeError("/srv/secret/path.py line 42: postgres://user:hunter2@db")

    with TestClient(app, raise_server_exceptions=False) as failing:
        response = failing.get("/api/v1/_boom")

    assert response.status_code == 500
    payload = response.json()
    assert payload["data"] is None
    assert set(payload["error"]) <= {"code", "message", "reference"}
    assert payload["error"]["code"] == "InternalError"
    text = response.text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "hunter2" not in text
    assert "secret" not in text
    assert payload["error"]["reference"]
    assert app_exceptions._GENERIC_MESSAGE in text
