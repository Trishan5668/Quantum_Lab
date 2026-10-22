"""Identity and authorisation for QuantHub.

Authentication modes
--------------------

``firebase`` (production)
    ``Authorization: Bearer <Firebase ID token>``.  The token is verified by the
    official Firebase Admin SDK, which checks the signature against Google's
    rotating public keys plus issuer, audience, expiry and revocation.  QuantHub
    then re-checks the security-relevant claims (``aud``, ``iss``, ``exp``,
    ``sub``) before trusting them, so a caller cannot inject a project or an
    expiry.  Any failure is a ``401`` with no internal detail.

``client-identity`` (development and tests only)
    ``X-QuantHub-User`` / ``X-QuantHub-Name`` / ``X-QuantHub-Email`` headers.
    This is **not** a security boundary.  It requires *both*
    ``QUANTHUB_TRUST_CLIENT_IDENTITY=1`` and an explicit
    ``QUANTHUB_ENV=development`` (or ``test``); see :mod:`app.quanthub.config`.
    There is no default that enables it, and ``QUANTHUB_ENV=production`` with
    the flag set refuses to start.

``guest``
    Everything else: read-only access to public projects.

Authorization is always separate from authentication: :func:`project_role`,
:func:`require_read` and :func:`require_write` decide access per project, so a
valid token for one user cannot reach another user's private project.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from app.quanthub import config, db
from app.quanthub.errors import conflict, forbidden, unauthorized

logger = logging.getLogger("quanthub.auth")

_HANDLE_RE = re.compile(r"[^a-z0-9-]+")

#: Skew tolerated when checking the ``exp`` claim of an already-verified token.
EXPIRY_LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class Principal:
    id: str
    handle: str
    display_name: str
    email: str | None
    is_authenticated: bool
    #: ``firebase``, ``client-identity`` or ``guest`` (diagnostics only).
    source: str = "firebase"

    def to_dict(self) -> dict[str, Any]:
        if not self.is_authenticated:
            mode = "guest"
        elif self.source == "client-identity":
            mode = "local"
        else:
            mode = "authenticated"
        return {
            "id": self.id,
            "handle": self.handle,
            "display_name": self.display_name,
            "email": self.email,
            "authenticated": self.is_authenticated,
            "mode": mode,
        }


GUEST = Principal(
    id="guest",
    handle="guest",
    display_name="Guest",
    email=None,
    is_authenticated=False,
    source="guest",
)


def sanitize_handle(value: str) -> str:
    handle = _HANDLE_RE.sub("-", value.strip().lower()).strip("-")
    handle = re.sub(r"-{2,}", "-", handle)
    return handle[:39] or "researcher"


def _stable_id(handle: str) -> str:
    return "u_" + hashlib.sha256(handle.encode("utf-8")).hexdigest()[:24]


def _free_handle(conn: sqlite3.Connection, base: str, user_id: str) -> str:
    """Return a handle not already owned by a different user record."""
    candidate = base
    for suffix in range(2, 52):
        row = conn.execute("SELECT id FROM users WHERE handle = ?", (candidate,)).fetchone()
        if row is None or str(row["id"]) == user_id:
            return candidate
        candidate = f"{base[:35]}-{suffix}"
    raise conflict(  # pragma: no cover - 50 collisions is not realistic
        "HandleUnavailable",
        f"No free handle could be derived from '{base}'.",
    )


def upsert_user(
    conn: sqlite3.Connection,
    *,
    handle: str,
    name: str,
    email: str | None,
    user_id: str | None = None,
) -> Principal:
    """Create or update the caller's user row.

    ``user_id`` is authoritative when supplied (Firebase subject for token
    verification, stable handle hash for development identities).  It must be
    used verbatim: project ownership is stored as ``projects.owner_id`` and is
    authorised by comparing it with ``Principal.id``.
    """
    handle = sanitize_handle(handle)
    user_id = user_id or _stable_id(handle)
    handle = _free_handle(conn, handle, user_id)
    now = db.utc_now()
    conn.execute(
        "INSERT INTO users (id, handle, display_name, email, created_at)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET display_name = excluded.display_name,"
        " handle = excluded.handle,"
        " email = COALESCE(excluded.email, users.email)",
        (user_id, handle, name or handle, email, now),
    )
    return Principal(user_id, handle, name or handle, email, True)


# ---------------------------------------------------------------------------
# Firebase verification
# ---------------------------------------------------------------------------

_FIREBASE_APP_LOCK = threading.Lock()
_firebase_app: Any | None = None
_firebase_app_project: str | None = None


def reset_firebase_app() -> None:
    """Drop the memoised Firebase app (tests and credential rotation)."""
    global _firebase_app, _firebase_app_project
    with _FIREBASE_APP_LOCK:
        _firebase_app = None
        _firebase_app_project = None


def _firebase_sdk() -> tuple[Any, Any] | None:
    """Import ``firebase_admin`` lazily.

    Returns ``(auth_module, initialize_app)`` or ``None`` when the optional
    dependency is missing.  Missing dependency means "no verification
    possible", which fails closed.
    """
    try:
        from firebase_admin import auth as firebase_auth
        from firebase_admin import initialize_app
    except ImportError:  # pragma: no cover - depends on deployment extras
        return None
    return firebase_auth, initialize_app


def _get_firebase_app(project: str) -> Any | None:
    """Initialise the Admin SDK once per process (never per request)."""
    global _firebase_app, _firebase_app_project
    sdk = _firebase_sdk()
    if sdk is None:
        return None
    _firebase_auth, initialize_app = sdk
    with _FIREBASE_APP_LOCK:
        if _firebase_app is not None and _firebase_app_project == project:
            return _firebase_app
        try:
            from firebase_admin import credentials, get_app

            try:
                app = get_app()
            except ValueError:
                app = initialize_app(
                    credentials.ApplicationDefault(), {"projectId": project}
                )
        except Exception:  # noqa: BLE001 - never leak credential details upward
            logger.error(
                "Firebase Admin could not be initialised. Configure Application "
                "Default Credentials for project %s.",
                project,
            )
            return None
        _firebase_app = app
        _firebase_app_project = project
        return app


def _verify_id_token_with_sdk(token: str, project: str) -> dict[str, Any]:
    """Verify an ID token with the official SDK.

    This is the only place that talks to the trusted verifier.  It is a module
    level seam so tests can substitute a deterministic verifier without ever
    accepting a decoded-but-unverified JWT in production code.
    """
    sdk = _firebase_sdk()
    if sdk is None:
        raise RuntimeError("firebase_admin is not installed")
    firebase_auth, _initialize_app = sdk
    app = _get_firebase_app(project)
    if app is None:
        raise RuntimeError("Firebase Admin is not configured")
    return dict(
        firebase_auth.verify_id_token(token, app=app, check_revoked=True)
    )


def _validate_claims(
    decoded: dict[str, Any], project: str, *, now: float | None = None
) -> dict[str, Any]:
    """Defence-in-depth checks on claims returned by the verifier.

    The SDK already enforces these; repeating them here keeps the guarantee
    explicit and testable, and rejects a verifier that returns a token minted
    for a different project.
    """
    audience = decoded.get("aud")
    if audience != project:
        raise ValueError("token audience does not match the configured project")
    issuer = decoded.get("iss")
    if issuer != f"https://securetoken.google.com/{project}":
        raise ValueError("token issuer does not match the configured project")

    expires = decoded.get("exp")
    if not isinstance(expires, (int, float)):
        raise TypeError("token has no numeric expiry")
    if float(expires) + EXPIRY_LEEWAY_SECONDS < (now if now is not None else time.time()):
        raise ValueError("token has expired")

    subject = decoded.get("uid") or decoded.get("sub") or decoded.get("user_id")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("token has no subject")
    return decoded


def _principal_from_claims(decoded: dict[str, Any]) -> Principal:
    uid = str(decoded.get("uid") or decoded.get("sub") or "").strip()
    email = decoded.get("email")
    email = str(email) if email else None
    # Prefer the verified email local part for a human handle, else the subject.
    basis = (email.split("@")[0] if email else "") or uid
    display = str(decoded.get("name") or "").strip()
    if not display:
        display = (email or uid).split("@")[0] or "Researcher"
    # The stable primary key is the Firebase subject, never a caller-supplied id.
    return Principal(
        id=uid or _stable_id(sanitize_handle(basis)),
        handle=sanitize_handle(basis),
        display_name=display,
        email=email,
        is_authenticated=True,
        source="firebase",
    )


def verify_bearer_token(token: str) -> Principal:
    """Verify a bearer token and return its principal, or raise ``401``."""
    token = token.strip()
    if not token:
        raise unauthorized("Your session token could not be verified. Sign in again.")

    project = config.firebase_project_id()
    if not project:
        logger.warning(
            "Rejected a bearer token because no Firebase project is configured."
        )
        raise unauthorized(
            "Sign-in is not configured on this server. Use a local session for "
            "development, or configure FIREBASE_PROJECT_ID."
        )

    try:
        decoded = _verify_id_token_with_sdk(token, project)
    except Exception as exc:  # noqa: BLE001 - all failures are auth failures
        # Log the failure class only: never the token, the claims, or a trace.
        logger.warning("Firebase token verification failed: %s", type(exc).__name__)
        raise unauthorized(
            "Your session token could not be verified. Sign in again."
        ) from None

    try:
        decoded = _validate_claims(decoded, project)
    except (TypeError, ValueError) as exc:
        logger.warning("Firebase token rejected by claim checks: %s", exc)
        raise unauthorized(
            "Your session token could not be verified. Sign in again."
        ) from None

    return _principal_from_claims(decoded)


# ---------------------------------------------------------------------------
# Request → principal
# ---------------------------------------------------------------------------


def principal_from_request(request: Request) -> Principal:
    """Resolve the caller without touching the database (pure header parsing)."""
    cached = getattr(request.state, "principal", None)
    if cached is not None:
        return cached

    authorization = request.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() == "bearer" and credentials.strip():
        principal = verify_bearer_token(credentials)
        request.state.principal = principal
        return principal

    if config.trust_client_identity():
        handle = request.headers.get("x-quanthub-user", "").strip()
        if handle:
            clean = sanitize_handle(handle)
            principal = Principal(
                id=_stable_id(clean),
                handle=clean,
                display_name=request.headers.get("x-quanthub-name", "").strip() or clean,
                email=request.headers.get("x-quanthub-email", "").strip() or None,
                is_authenticated=True,
                source="client-identity",
            )
            request.state.principal = principal
            return principal
    elif request.headers.get("x-quanthub-user"):
        # Explicitly ignore the header outside development. Nothing is logged
        # beyond the fact that an unverified identity was supplied.
        logger.debug("Ignored client-supplied identity headers (not trusted here).")

    principal = GUEST
    request.state.principal = principal
    return principal


def sign_in_hint() -> str:
    """Explain how *this* server expects a caller to authenticate.

    The text is client-visible, so it never contains a secret, a configured
    value, or a filesystem path.  It does describe the option that is available
    (verified tokens or local development sessions) because a bare "Sign in to
    continue." on a server with neither enabled is impossible to act on.
    """
    if config.trust_client_identity():
        return "Sign in to continue."
    if config.firebase_project_id():
        return "Sign in with your account to continue."
    return (
        "This QuantHub server requires a signed-in account, and local "
        "development sessions are disabled. Sign in with Firebase once "
        "FIREBASE_PROJECT_ID is configured, or start the API with "
        "QUANTHUB_ENV=development and QUANTHUB_TRUST_CLIENT_IDENTITY=1 for "
        "local use."
    )


def require_user(principal: Principal) -> Principal:
    if not principal.is_authenticated:
        raise unauthorized(sign_in_hint())
    return principal


def ensure_user(principal: Principal) -> Principal:
    """Materialise the authenticated principal in the users table.

    Returns the stored identity, whose handle may differ from the requested one
    when another account already owns it.
    """
    require_user(principal)
    if principal.id == GUEST.id:
        raise unauthorized()
    with db.db() as conn:
        stored = upsert_user(
            conn,
            handle=principal.handle,
            name=principal.display_name,
            email=principal.email,
            user_id=principal.id,
        )
    if stored.handle == principal.handle:
        return principal
    return Principal(
        id=principal.id,
        handle=stored.handle,
        display_name=principal.display_name,
        email=principal.email,
        is_authenticated=True,
        source=principal.source,
    )


VISIBILITY_ROLES = {"owner", "maintainer", "reader"}
WRITE_ROLES = {"owner", "maintainer"}


def project_role(conn: sqlite3.Connection, project: dict[str, Any], principal: Principal) -> str | None:
    if not principal.is_authenticated:
        return None
    if project["owner_id"] == principal.id:
        return "owner"
    row = conn.execute(
        "SELECT role FROM project_members WHERE project_id = ? AND user_id = ?",
        (project["id"], principal.id),
    ).fetchone()
    return str(row["role"]) if row else None


def can_read(project: dict[str, Any], role: str | None) -> bool:
    return project["visibility"] == "public" or role is not None


def require_read(project: dict[str, Any], role: str | None) -> None:
    if not can_read(project, role):
        # Deliberately the same response as "missing" so private project
        # slugs cannot be enumerated.
        raise forbidden("You do not have access to this project.")


def require_write(project: dict[str, Any], role: str | None) -> None:
    if role not in WRITE_ROLES:
        raise forbidden("Only the project owner and maintainers may modify it.")
