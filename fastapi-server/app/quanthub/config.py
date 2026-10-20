"""QuantHub runtime configuration.

QuantHub keeps authoritative project state in a single SQLite database and
stores every project's files in a real Git repository.  Both live underneath
``QUANTHUB_DATA_DIR`` so a deployment can be backed up (or moved) as one unit.

Nothing in this module reads secrets from the repository.  Deployment
behaviour is controlled exclusively through environment variables, and the
security-relevant settings are **fail-closed**:

* Unverified client identity headers require ``QUANTHUB_TRUST_CLIENT_IDENTITY=1``
  *and* an explicit ``QUANTHUB_ENV`` of ``development`` (or ``test``).  There is
  no default that enables them.  ``validate_configuration`` refuses to start
  when the two settings disagree.
* ``FIREBASE_PROJECT_ID`` is the canonical backend variable for Firebase
  authentication.  The legacy alias ``QUANTHUB_FIREBASE_PROJECT`` is still
  honoured, and ``GOOGLE_CLOUD_PROJECT`` (the Firebase Admin default) is used
  when neither is set.  Frontend ``VITE_*`` variables are never read here.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("quanthub.config")

# ``fastapi-server/app/quanthub/config.py`` -> repository root
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Environments in which development-only shortcuts may be enabled.
DEVELOPMENT_ENVIRONMENTS = frozenset({"development", "test"})
#: Every environment value the backend understands.
VALID_ENVIRONMENTS = DEVELOPMENT_ENVIRONMENTS | {"production"}

#: Canonical backend variable, then compatibility aliases in precedence order.
FIREBASE_PROJECT_ENV_VARS = (
    "FIREBASE_PROJECT_ID",
    "GOOGLE_CLOUD_PROJECT",
    "QUANTHUB_FIREBASE_PROJECT",
)
#: Aliases that are accepted but emit a deprecation warning.
DEPRECATED_ENV_ALIASES = {"QUANTHUB_FIREBASE_PROJECT": "FIREBASE_PROJECT_ID"}

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off"})


class ConfigError(RuntimeError):
    """Raised when deployment configuration is invalid or unsafe.

    The message is actionable and never contains credentials, tokens or
    environment values that could be secret.
    """


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean flag strictly.

    Unknown values raise :class:`ConfigError` instead of silently falling back,
    because every flag using this helper controls a security boundary.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    raise ConfigError(
        f"{name} must be one of 1/0, true/false, yes/no or on/off (got {raw.strip()!r})."
    )


def data_dir() -> Path:
    """Return the QuantHub data directory, creating it when necessary."""
    configured = os.getenv("QUANTHUB_DATA_DIR")
    path = Path(configured).expanduser() if configured else _REPO_ROOT / ".quanthub-data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repos_dir() -> Path:
    path = data_dir() / "repos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def projects_dir() -> Path:
    path = data_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    """Return the runtime SQLite database location.

    ``QUANTHUB_DB_PATH`` overrides the default ``<data>/quanthub.sqlite3``; it
    must be an absolute path or a path relative to the working directory.  The
    database is derived state and is never stored in source control.
    """
    configured = (os.getenv("QUANTHUB_DB_PATH") or "").strip()
    if configured:
        return Path(configured).expanduser()
    return data_dir() / "quanthub.sqlite3"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def environment() -> str:
    """Return the explicit deployment environment.

    ``QUANTHUB_ENV`` has no implicit default: an unset value resolves to
    ``"unspecified"``, which is treated as **not** development.  Anything other
    than ``development``, ``test`` or ``production`` raises :class:`ConfigError`
    so a typo cannot quietly change the security posture.
    """
    raw = (os.getenv("QUANTHUB_ENV") or "").strip().lower()
    if not raw:
        return "unspecified"
    if raw not in VALID_ENVIRONMENTS:
        raise ConfigError(
            "QUANTHUB_ENV must be 'development', 'test' or 'production' "
            f"(got {raw!r})."
        )
    return raw


def is_production() -> bool:
    return environment() == "production"


def is_development() -> bool:
    """True only when development identity headers are explicitly permitted."""
    return environment() in DEVELOPMENT_ENVIRONMENTS


# ---------------------------------------------------------------------------
# Authentication configuration
# ---------------------------------------------------------------------------


def firebase_project_id() -> str | None:
    """Resolve the Firebase project ID from backend variables only.

    Precedence is deterministic: ``FIREBASE_PROJECT_ID`` (canonical),
    ``GOOGLE_CLOUD_PROJECT`` (Firebase Admin default), then the legacy alias
    ``QUANTHUB_FIREBASE_PROJECT``.  Empty values are treated as unset.
    Frontend ``VITE_*`` variables are deliberately ignored so a browser bundle
    cannot influence server-side token verification.
    """
    for name in FIREBASE_PROJECT_ENV_VARS:
        value = (os.getenv(name) or "").strip()
        if not value:
            continue
        alias_target = DEPRECATED_ENV_ALIASES.get(name)
        if alias_target:
            logger.warning(
                "%s is a legacy alias for %s; please migrate the deployment.",
                name,
                alias_target,
            )
        return value
    return None


def trust_client_identity() -> bool:
    """Whether unverified ``X-QuantHub-*`` headers may establish a session.

    Requires **both** an explicit ``QUANTHUB_TRUST_CLIENT_IDENTITY=1`` and an
    explicit development/test ``QUANTHUB_ENV``.  Any configuration error
    (unknown flag value, unknown environment) resolves to ``False`` so a
    misconfigured deployment can never fall back to header identity; the same
    conditions are reported as startup errors by :func:`validate_configuration`.
    """
    try:
        enabled = _env_flag("QUANTHUB_TRUST_CLIENT_IDENTITY", default=False)
        if not enabled:
            return False
        return environment() in DEVELOPMENT_ENVIRONMENTS
    except ConfigError:
        return False


def firebase_admin_available() -> bool:
    """Whether the Firebase Admin SDK can be imported.

    Kept as a tiny helper so the check is testable without uninstalling a
    dependency, and so an import failure never propagates as a stack trace.
    """
    try:
        import firebase_admin  # noqa: F401  (availability probe only)
    except Exception:  # noqa: BLE001 - any import failure means unavailable
        return False
    return True


def validate_configuration() -> None:
    """Fail fast on missing or contradictory security settings.

    Called once while the application is created.  Raises :class:`ConfigError`
    with an actionable message; no secret values are included.
    """
    env = environment()  # raises on an invalid value
    # Validate the flag even when unused so a typo is reported, not ignored.
    trust = _env_flag("QUANTHUB_TRUST_CLIENT_IDENTITY", default=False)
    project = firebase_project_id()

    if trust and env not in DEVELOPMENT_ENVIRONMENTS:
        where = "production" if env == "production" else "unset (QUANTHUB_ENV)"
        raise ConfigError(
            "QUANTHUB_TRUST_CLIENT_IDENTITY=1 accepts unverified client-supplied "
            f"identities but QUANTHUB_ENV is {where}. Set QUANTHUB_ENV=development "
            "for local work, or remove QUANTHUB_TRUST_CLIENT_IDENTITY in any "
            "deployment reachable by untrusted clients."
        )

    if env == "production" and not project:
        raise ConfigError(
            "QUANTHUB_ENV=production requires Firebase authentication, but no "
            "project ID is configured. Set FIREBASE_PROJECT_ID (or "
            "GOOGLE_CLOUD_PROJECT) to the Firebase project that issues ID tokens."
        )

    if env == "production" and project and not firebase_admin_available():
        raise ConfigError(
            "QUANTHUB_ENV=production requires the Firebase Admin SDK to verify ID "
            "tokens, but it cannot be imported. Install firebase-admin (it is a "
            "declared dependency) in the runtime environment."
        )

    if env == "production" and trust:  # defensive: unreachable, kept explicit
        raise ConfigError("Development identity headers cannot be used in production.")

    if env == "unspecified":
        logger.warning(
            "QUANTHUB_ENV is not set. QuantHub assumes a non-development "
            "deployment: client-supplied identity headers are ignored and only "
            "verified Firebase tokens authenticate. Set QUANTHUB_ENV explicitly."
        )


def configuration_summary() -> dict[str, object]:
    """Non-secret description of the effective security configuration."""
    try:
        env = environment()
    except ConfigError:
        env = "invalid"
    return {
        "environment": env,
        "client_identity_trusted": trust_client_identity(),
        "firebase_project_configured": bool(firebase_project_id()),
        "firebase_project_variable": next(
            (
                name
                for name in FIREBASE_PROJECT_ENV_VARS
                if (os.getenv(name) or "").strip()
            ),
            None,
        ),
    }


# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Limits:
    """Resource limits applied to untrusted uploads and archives."""

    max_file_bytes: int
    max_upload_bytes: int
    max_files_per_upload: int
    max_zip_entries: int
    max_zip_uncompressed_bytes: int
    max_path_depth: int
    max_path_length: int
    max_repo_files: int
    max_blob_view_bytes: int
    experiment_timeout_seconds: int
    max_concurrent_runs: int


def limits() -> Limits:
    return Limits(
        max_file_bytes=_env_int("QUANTHUB_MAX_FILE_BYTES", 5 * 1024 * 1024),
        max_upload_bytes=_env_int("QUANTHUB_MAX_UPLOAD_BYTES", 64 * 1024 * 1024),
        max_files_per_upload=_env_int("QUANTHUB_MAX_FILES_PER_UPLOAD", 2000),
        max_zip_entries=_env_int("QUANTHUB_MAX_ZIP_ENTRIES", 2000),
        max_zip_uncompressed_bytes=_env_int(
            "QUANTHUB_MAX_ZIP_UNCOMPRESSED_BYTES", 256 * 1024 * 1024
        ),
        max_path_depth=_env_int("QUANTHUB_MAX_PATH_DEPTH", 20),
        max_path_length=_env_int("QUANTHUB_MAX_PATH_LENGTH", 400),
        max_repo_files=_env_int("QUANTHUB_MAX_REPO_FILES", 5000),
        max_blob_view_bytes=_env_int("QUANTHUB_MAX_BLOB_VIEW_BYTES", 2 * 1024 * 1024),
        experiment_timeout_seconds=_env_int("QUANTHUB_EXPERIMENT_TIMEOUT", 900),
        max_concurrent_runs=_env_int("QUANTHUB_MAX_CONCURRENT_RUNS", 2),
    )


def cors_origins() -> list[str]:
    raw = os.getenv("QUANTHUB_CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]
