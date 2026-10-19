"""Immutable experiment artifacts, provenance, checksums, and verification.

Every run is written into a unique directory.  Data are first written to a
hidden temporary directory, fsynced, hashed, and only then renamed into place.
A failed run is preserved as ``failed-<id>`` with its error record; it is never
silently overwritten.  ``verify_artifact`` independently recomputes checksums
and cross-checks the configuration hash and experiment identifier.

A checksum-valid artifact proves integrity, not scientific validity.  Reports
must not turn ``INTEGRITY_OK`` into a claim of correctness.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import socket
import subprocess
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TextIO

from quantumlab.research.qec.protocol import ExperimentProtocol, Protocol, canonical_protocol_json

ARTIFACT_SCHEMA_VERSION = "1.0"
ANALYSIS_VERSION = "1.0.0"


class ArtifactError(RuntimeError):
    """Raised for invalid artifact operations or failed verification."""


@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_files: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checked_files": self.checked_files,
        }


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout


def git_state() -> dict[str, Any]:
    revision = _git("rev-parse", "HEAD").strip() or "unavailable"
    status = _git("status", "--porcelain")
    diff_text = _git("diff", "--binary", "HEAD")
    untracked = [line[3:] for line in status.splitlines() if line.startswith("?? ")]
    return {
        "source_revision": revision,
        "dirty": bool(status.strip()),
        "dirty_status_sha256": sha256_bytes(status.encode("utf-8")),
        "diff_sha256": sha256_bytes(diff_text.encode("utf-8")),
        "untracked_files": untracked,
    }


def _package_version(name: str) -> str | None:
    try:
        import importlib.metadata as metadata

        return metadata.version(name)
    except Exception:
        return None


def environment_snapshot() -> dict[str, Any]:
    packages = {
        name: _package_version(name)
        for name in (
            "numpy",
            "scipy",
            "PyYAML",
            "stim",
            "pymatching",
            "pytest",
            "hypothesis",
        )
    }
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "hostname": socket.gethostname(),
        "packages": packages,
        "resource_usage": {
            "maxrss_kib": usage.ru_maxrss,
            "user_cpu_seconds": usage.ru_utime,
            "system_cpu_seconds": usage.ru_stime,
        },
        "command_line": sys.argv,
    }


@dataclass
class ArtifactRun:
    """Context manager that writes one immutable experiment directory."""

    output_root: Path
    kind: str
    protocol: ExperimentProtocol | Protocol
    experiment_id: str | None = None
    start_utc: str = field(default_factory=utc_now)
    start_monotonic: float = field(default_factory=time.monotonic)
    warnings: list[str] = field(default_factory=list)
    _tmp_dir: Path | None = field(default=None, init=False)
    _final_dir: Path | None = field(default=None, init=False)
    _committed: bool = field(default=False, init=False)

    def __enter__(self) -> ArtifactRun:
        self.output_root.mkdir(parents=True, exist_ok=True)
        identifier = self.experiment_id or (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        )
        self.experiment_id = identifier
        self._tmp_dir = self.output_root / f".tmp-{identifier}"
        if self._tmp_dir.exists():
            raise ArtifactError(f"temporary artifact directory already exists: {self._tmp_dir}")
        self._tmp_dir.mkdir()
        return self

    def __exit__(
        self, exc_type: object, exc: object, traceback_obj: object
    ) -> Literal[False]:
        if (
            exc_type is not None
            and not self._committed
            and self._tmp_dir is not None
            and self._tmp_dir.exists()
        ):
            self.abort(exc if isinstance(exc, BaseException) else RuntimeError(str(exc)))
        return False

    @property
    def directory(self) -> Path:
        if self._tmp_dir is None:
            raise ArtifactError("artifact run has not been entered")
        return self._tmp_dir

    def path(self, name: str) -> Path:
        if "/" in name or name in {"", ".", ".."}:
            raise ArtifactError(f"artifact name must be a flat file name, got {name!r}")
        return self.directory / name

    def write_text(self, name: str, text: str) -> Path:
        path = self.path(name)
        path.write_text(text, encoding="utf-8")
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
        return path

    def write_json(self, name: str, payload: Any) -> Path:
        return self.write_text(name, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def write_jsonl(self, name: str, records: list[dict[str, Any]]) -> Path:
        lines = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
        return self.write_text(name, lines)

    def open_jsonl(self, name: str) -> TextIO:
        path = self.path(name)
        return path.open("w", encoding="utf-8")

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def _write_config_and_provenance(self) -> None:
        raw = self.protocol.raw
        config_hash = sha256_bytes(canonical_protocol_json(self.protocol).encode("utf-8"))
        self.write_json(
            "config.json",
            {"raw": raw, "config_hash": config_hash, "kind": self.kind},
        )
        self.write_json(
            "provenance.json",
            {
                "experiment_id": self.experiment_id,
                "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
                "analysis_version": ANALYSIS_VERSION,
                "kind": self.kind,
                "config_hash": config_hash,
                "source_path": getattr(self.protocol, "source_path", None),
                "source_sha256": getattr(self.protocol, "source_sha256", None),
                "git": git_state(),
                "start_utc": self.start_utc,
                "rng_policy": (
                    "numpy SeedSequence([seed, purpose_index]) per purpose; "
                    "each purpose's derived seed is recorded in summary.json"
                ),
            },
        )

    def commit(self, summary: dict[str, Any]) -> Path:
        if self._tmp_dir is None or self.experiment_id is None:
            raise ArtifactError("artifact run has not been entered")
        if self._committed:
            raise ArtifactError("artifact run has already been committed")
        end_utc = utc_now()
        elapsed = time.monotonic() - self.start_monotonic
        self._write_config_and_provenance()
        self.write_json("environment.json", environment_snapshot())
        summary_payload = dict(summary)
        summary_payload.setdefault("experiment_id", self.experiment_id)
        summary_payload.setdefault("artifact_schema_version", ARTIFACT_SCHEMA_VERSION)
        summary_payload.setdefault("analysis_version", ANALYSIS_VERSION)
        summary_payload.setdefault("start_utc", self.start_utc)
        summary_payload.setdefault("end_utc", end_utc)
        summary_payload.setdefault("runtime_seconds", elapsed)
        summary_payload.setdefault("warnings", list(self.warnings))
        self.write_json("summary.json", summary_payload)

        files = sorted(
            path
            for path in self._tmp_dir.iterdir()
            if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
        )
        manifest_files = {
            path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in files
        }
        self.write_json(
            "manifest.json",
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "experiment_id": self.experiment_id,
                "kind": self.kind,
                "files": manifest_files,
            },
        )
        all_files = sorted(
            path
            for path in self._tmp_dir.iterdir()
            if path.is_file() and path.name != "checksums.sha256"
        )
        checksum_lines = "".join(
            f"{sha256_file(path)}  {path.name}\n" for path in all_files
        )
        self.write_text("checksums.sha256", checksum_lines)
        final_dir = self.output_root / self.experiment_id
        if final_dir.exists():
            raise ArtifactError(f"final artifact directory already exists: {final_dir}")
        os.replace(self._tmp_dir, final_dir)
        self._final_dir = final_dir
        self._committed = True
        return final_dir

    def abort(self, exc: BaseException) -> Path:
        if self._tmp_dir is None or self.experiment_id is None:
            raise ArtifactError("artifact run has not been entered")
        failure_dir = self.output_root / f"failed-{self.experiment_id}"
        if failure_dir.exists():
            failure_dir = self.output_root / f"failed-{self.experiment_id}-{uuid.uuid4().hex[:6]}"
        payload = {
            "experiment_id": self.experiment_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "start_utc": self.start_utc,
            "failed_utc": utc_now(),
            "runtime_seconds": time.monotonic() - self.start_monotonic,
            "config_hash": sha256_bytes(canonical_protocol_json(self.protocol).encode("utf-8")),
        }
        try:
            self.write_json("error.json", payload)
        except OSError:
            pass
        os.replace(self._tmp_dir, failure_dir)
        return failure_dir


def _parse_checksums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ArtifactError(f"malformed checksums line {line_number}: {line!r}")
        digest, name = parts[0], parts[1].strip()
        if name.startswith("*"):
            name = name[1:]
        entries[name] = digest
    return entries


def verify_artifact(directory: str | Path) -> VerificationReport:
    """Recompute checksums and cross-check identity/configuration metadata."""
    root = Path(directory)
    errors: list[str] = []
    warnings: list[str] = []
    if not root.is_dir():
        return VerificationReport(False, (f"artifact directory does not exist: {root}",), (), 0)
    checksum_path = root / "checksums.sha256"
    if not checksum_path.is_file():
        return VerificationReport(False, ("checksums.sha256 is missing",), (), 0)
    try:
        expected = _parse_checksums(checksum_path)
    except ArtifactError as exc:
        return VerificationReport(False, (str(exc),), (), 0)
    checked = 0
    for name, digest in expected.items():
        path = root / name
        if not path.is_file():
            errors.append(f"missing file listed in checksums: {name}")
            continue
        checked += 1
        actual = sha256_file(path)
        if actual != digest:
            errors.append(f"checksum mismatch for {name}: expected {digest}, got {actual}")
    actual_files = {path.name for path in root.iterdir() if path.is_file()}
    extra = sorted(actual_files - set(expected) - {"checksums.sha256"})
    if extra:
        warnings.append(f"files not covered by checksums.sha256: {extra}")

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append("manifest.json is missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"manifest.json is not valid JSON: {exc}")
        else:
            if manifest.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
                errors.append("manifest schema_version is not supported")
            identifier = str(manifest.get("experiment_id", ""))
            if root.name not in {identifier, f"failed-{identifier}"}:
                errors.append(
                    f"directory name {root.name!r} does not match "
                    f"manifest experiment_id {identifier!r}"
                )
            for name, entry in manifest.get("files", {}).items():
                path = root / name
                if not path.is_file():
                    errors.append(f"manifest file is missing: {name}")
                    continue
                if path.stat().st_size != entry.get("size_bytes"):
                    errors.append(f"size mismatch for {name}")
                if sha256_file(path) != entry.get("sha256"):
                    errors.append(f"manifest hash mismatch for {name}")

    summary_path = root / "summary.json"
    provenance_path = root / "provenance.json"
    config_path = root / "config.json"
    if not summary_path.is_file():
        errors.append("summary.json is missing")
    if not provenance_path.is_file():
        errors.append("provenance.json is missing")
    if not config_path.is_file():
        errors.append("config.json is missing")
    if config_path.is_file() and provenance_path.is_file() and summary_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"artifact metadata is not valid JSON: {exc}")
        else:
            recomputed = sha256_bytes(canonical_json(config.get("raw", {})).encode("utf-8"))
            if config.get("config_hash") != recomputed:
                errors.append("config.json config_hash does not match its raw configuration")
            if provenance.get("config_hash") != recomputed:
                errors.append("provenance.json config_hash does not match config.json")
            if summary.get("config_hash") not in (None, recomputed):
                errors.append("summary.json config_hash does not match config.json")
            if summary.get("experiment_id") != provenance.get("experiment_id"):
                errors.append("summary and provenance experiment_id differ")
    return VerificationReport(not errors, tuple(errors), tuple(warnings), checked)


def read_summary(directory: str | Path) -> dict[str, Any]:
    path = Path(directory) / "summary.json"
    if not path.is_file():
        raise ArtifactError(f"summary.json not found in {directory}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"summary.json is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactError("summary.json root must be a mapping")
    return value


def package_artifact(directory: str | Path, output: str | Path | None = None) -> Path:
    """Create a tar.gz evidence package and verify the source artifact first."""
    import tarfile

    root = Path(directory)
    report = verify_artifact(root)
    if not report.ok:
        raise ArtifactError(
            "refusing to package an artifact that fails integrity verification: "
            + "; ".join(report.errors)
        )
    destination = (
        Path(output)
        if output is not None
        else root.parent / f"{root.name}-evidence.tar.gz"
    )
    if destination.exists():
        raise ArtifactError(f"package destination already exists: {destination}")
    with tarfile.open(destination, "w:gz") as archive:
        archive.add(root, arcname=root.name, recursive=True)
    manifest = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_directory": root.name,
        "package_sha256": sha256_file(destination),
        "package_size_bytes": destination.stat().st_size,
        "integrity_report": report.to_dict(),
        "scientific_claim_status": "NOT_INDEPENDENTLY_VALIDATED",
        "notice": (
            "Package integrity does not establish scientific validity. "
            "See report.md and the independent validation plan."
        ),
    }
    manifest_path = destination.with_suffix(destination.suffix + ".manifest.json")
    write_json(manifest_path, manifest)
    return destination


def copy_artifact(source: str | Path, destination_root: str | Path) -> Path:
    """Copy an artifact only after verifying its checksums."""
    src = Path(source)
    report = verify_artifact(src)
    if not report.ok:
        raise ArtifactError("cannot copy an artifact that fails verification")
    destination_root = Path(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / src.name
    if destination.exists():
        raise ArtifactError(f"destination already exists: {destination}")
    shutil.copytree(src, destination)
    return destination
