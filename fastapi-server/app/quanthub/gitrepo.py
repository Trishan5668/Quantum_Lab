"""Thin, explicit wrapper around the ``git`` binary for project storage.

Each QuantHub project is a real bare Git repository.  Writes are built with Git
plumbing (``hash-object`` → ``update-index`` → ``write-tree`` →
``commit-tree`` → ``update-ref``) so a multi-file change becomes exactly one
immutable commit, and so optimistic concurrency is enforced by ``update-ref``'s
compare-and-swap semantics instead of application-level locking.

No user-supplied path ever reaches the filesystem here: every path is validated
by :func:`normalize_repo_path` and written into a Git index, not into a working
tree.  This removes the classic "committed a symlink outside the repository"
failure mode by construction (all entries are mode ``100644``).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.quanthub.config import limits
from app.quanthub.errors import HubError, bad_request, conflict, not_found

_RESERVED_SEGMENTS = {".git", ".gitattributes_dir"}
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class GitError(HubError):
    def __init__(self, message: str) -> None:
        super().__init__(500, "GitError", message)


@dataclass(frozen=True)
class HeadInfo:
    branch: str
    sha: str | None


def _env() -> dict[str, str]:
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    return env


def _git(
    repo: Path | None,
    *args: str,
    input_bytes: bytes | None = None,
    env_extra: dict[str, str] | None = None,
) -> bytes:
    command = ["git"]
    if repo is not None:
        command.extend(["--git-dir", str(repo)])
    command.extend(args)
    env = _env()
    if env_extra:
        env.update(env_extra)
    try:
        proc = subprocess.run(
            command,
            input=input_bytes,
            capture_output=True,
            env=env,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git is a hard requirement
        raise GitError("The server has no git binary available.") from exc
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace").strip() or "git command failed"
        raise GitError(message[:2000])
    return proc.stdout


def normalize_repo_path(raw: str) -> str:
    """Validate and normalise a repository-relative path.

    Rejects traversal, absolute paths, control characters, Windows reserved
    names, and over-long paths while preserving nested directories.
    """
    if raw is None:
        raise bad_request("InvalidPath", "A file path is required.")
    if _CONTROL_RE.search(raw):
        raise bad_request("InvalidPath", "Paths may not contain control characters.")
    original = raw.replace("\\", "/").strip()
    if original.startswith(("/", "~")) or re.match(r"^[a-zA-Z]:", original):
        raise bad_request("InvalidPath", "Absolute paths are not allowed.")
    path = original
    while path.startswith("./"):
        path = path[2:]
    path = re.sub(r"/{2,}", "/", path)
    path = path.strip("/")
    if not path:
        raise bad_request("InvalidPath", "A file path is required.")
    conf = limits()
    if len(path) > conf.max_path_length:
        raise bad_request("InvalidPath", "Path is too long.")
    segments = path.split("/")
    if len(segments) > conf.max_path_depth:
        raise bad_request("InvalidPath", "Path is nested too deeply.")
    cleaned: list[str] = []
    for segment in segments:
        if segment in {"", ".", ".."}:
            raise bad_request("InvalidPath", "Paths may not contain '.' or '..' segments.")
        if _CONTROL_RE.search(segment):
            raise bad_request("InvalidPath", "Paths may not contain control characters.")
        if segment.lower() in _RESERVED_SEGMENTS or segment.lower().endswith(".git"):
            raise bad_request("InvalidPath", "Paths may not reference Git internals.")
        if segment.lower().split(".")[0] in _WINDOWS_RESERVED:
            raise bad_request("InvalidPath", f"'{segment}' is a reserved file name.")
        if segment.endswith((" ", ".")):
            raise bad_request("InvalidPath", "Path segments may not end with a space or dot.")
        if len(segment) > 255:
            raise bad_request("InvalidPath", "A path segment is too long.")
        cleaned.append(segment)
    return "/".join(cleaned)


def init_repo(path: Path, default_branch: str = "main") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and any(path.iterdir()):
        raise GitError("Repository directory already exists.")
    _git(None, "init", "--bare", "--quiet", str(path))
    _git(path, "symbolic-ref", "HEAD", f"refs/heads/{default_branch}")


def head_sha(repo: Path, branch: str = "main") -> str | None:
    try:
        out = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}")
    except GitError:
        return None
    sha = out.decode().strip()
    return sha or None


def _tree_of_commit(repo: Path, sha: str) -> str:
    return _git(repo, "rev-parse", f"{sha}^{{tree}}").decode().strip()


def commit_files(
    repo: Path,
    *,
    branch: str,
    changes: dict[str, bytes | None],
    message: str,
    author_name: str,
    author_email: str,
    expected_head: str | None | object = ...,
    author_timestamp: str | None = None,
) -> tuple[str, bool]:
    """Create one commit containing ``changes``.

    ``changes`` maps validated repository paths to new bytes, or ``None`` to
    delete.  ``expected_head`` enables compare-and-swap: pass the revision the
    caller read, or ``None`` when the branch is expected to be empty.  When
    omitted the current head is used (last-writer-wins for internal callers such
    as imports that were just authorised).
    """
    current = head_sha(repo, branch)
    if expected_head is not ... and expected_head != current:
        raise conflict(
            "RevisionConflict",
            "This project changed since you loaded it. Reload and reapply your edit.",
            expected_revision=expected_head,
            current_revision=current,
        )
    if not changes:
        return current or "", False

    normalised: dict[str, bytes | None] = {}
    for raw_path, content in changes.items():
        normalised[normalize_repo_path(raw_path)] = content

    if not current:
        total = sum(1 for value in normalised.values() if value is not None)
        if total > limits().max_repo_files:
            raise bad_request("TooManyFiles", "This project would exceed the file limit.")

    with tempfile.NamedTemporaryFile(prefix="quanthub-index-", delete=False) as handle:
        index_path = handle.name
    os.unlink(index_path)
    index_env = {"GIT_INDEX_FILE": index_path}
    try:
        if current:
            _git(repo, "read-tree", current, env_extra=index_env)
        else:
            _git(repo, "read-tree", "--empty", env_extra=index_env)

        for path, content in normalised.items():
            if content is None:
                # Bare repositories have no working tree, so ``--force-remove``
                # is unavailable; remove the entry through --index-info instead.
                removal = f"0 {'0' * 40}\t{path}\n".encode()
                try:
                    _git(repo, "update-index", "--index-info", input_bytes=removal, env_extra=index_env)
                except GitError:
                    # Deleting a path that is not tracked is a no-op.
                    pass
                continue
            blob = _git(repo, "hash-object", "-w", "--stdin", input_bytes=content).decode().strip()
            _git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{path}",
                env_extra=index_env,
            )

        tree = _git(repo, "write-tree", env_extra=index_env).decode().strip()
        if current and tree == _tree_of_commit(repo, current):
            return current, False

        identity = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        if author_timestamp:
            identity["GIT_AUTHOR_DATE"] = author_timestamp
            identity["GIT_COMMITTER_DATE"] = author_timestamp
        args = ["commit-tree", tree, "-m", message]
        if current:
            args.extend(["-p", current])
        commit = _git(repo, *args, env_extra=identity).decode().strip()

        update_args = ["update-ref", f"refs/heads/{branch}", commit]
        update_args.append(current or "")
        try:
            _git(repo, *update_args, env_extra=identity)
        except GitError as exc:
            raise conflict(
                "RevisionConflict",
                "Another change landed while you were saving. Reload and retry.",
            ) from exc
        return commit, True
    finally:
        try:
            os.unlink(index_path)
        except FileNotFoundError:
            pass


@dataclass(frozen=True)
class TreeEntry:
    name: str
    path: str
    type: str
    size: int | None
    sha: str


def list_tree(repo: Path, rev: str, path: str = "") -> list[TreeEntry]:
    spec = f"{rev}:{path}" if path else rev
    try:
        raw = _git(repo, "ls-tree", "-z", "-l", spec)
    except GitError as exc:
        raise not_found("That path does not exist at this revision.") from exc
    entries: list[TreeEntry] = []
    for record in raw.split(b"\x00"):
        if not record:
            continue
        meta, _, name = record.partition(b"\t")
        parts = meta.split()
        if len(parts) < 4:
            continue
        obj_type, sha, size = parts[1], parts[2], parts[3]
        name_str = name.decode("utf-8", "replace")
        entries.append(
            TreeEntry(
                name=name_str,
                path=f"{path}/{name_str}" if path else name_str,
                type=obj_type.decode(),
                size=None if obj_type == b"tree" or size == b"-" else int(size),
                sha=sha.decode(),
            )
        )
    entries.sort(key=lambda item: (item.type != "tree", item.name.lower()))
    return entries


def list_all_paths(repo: Path, rev: str) -> list[TreeEntry]:
    raw = _git(repo, "ls-tree", "-r", "-z", "-l", rev)
    entries: list[TreeEntry] = []
    for record in raw.split(b"\x00"):
        if not record:
            continue
        meta, _, name = record.partition(b"\t")
        parts = meta.split()
        if len(parts) < 4:
            continue
        entries.append(
            TreeEntry(
                name=name.decode("utf-8", "replace").split("/")[-1],
                path=name.decode("utf-8", "replace"),
                type=parts[1].decode(),
                size=None if parts[3] == b"-" else int(parts[3]),
                sha=parts[2].decode(),
            )
        )
    return entries


def count_files(repo: Path, rev: str) -> int:
    raw = _git(repo, "ls-tree", "-r", "--name-only", "-z", rev)
    return len([item for item in raw.split(b"\x00") if item])


def read_file(repo: Path, rev: str, path: str) -> bytes:
    clean = normalize_repo_path(path)
    try:
        return _git(repo, "cat-file", "blob", f"{rev}:{clean}")
    except GitError as exc:
        raise not_found("That file does not exist at this revision.") from exc


def file_size(repo: Path, rev: str, path: str) -> int | None:
    clean = normalize_repo_path(path)
    try:
        out = _git(repo, "cat-file", "-s", f"{rev}:{clean}")
    except GitError:
        return None
    try:
        return int(out.decode().strip())
    except ValueError:
        return None


def find_readme(repo: Path, rev: str) -> str | None:
    candidates: Iterable[str] = (
        "README.md",
        "README.MD",
        "readme.md",
        "README.rst",
        "README.txt",
        "README",
    )
    names = {entry.path.lower(): entry.path for entry in list_tree(repo, rev) if entry.type == "blob"}
    for candidate in candidates:
        found = names.get(candidate.lower())
        if found:
            return found
    return None


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    parents: list[str]
    author_name: str
    author_email: str
    authored_at: str
    message: str


_FIELD = "\x1f"


def log(repo: Path, rev: str | None = None, *, limit: int = 30, path: str | None = None) -> list[CommitInfo]:
    if not rev:
        return []
    args = [
        "log",
        f"--max-count={max(1, min(limit, 200))}",
        f"--format=%H{_FIELD}%P{_FIELD}%an{_FIELD}%ae{_FIELD}%aI{_FIELD}%s{_FIELD}",
        rev,
    ]
    if path:
        args.extend(["--", normalize_repo_path(path)])
    try:
        raw = _git(repo, *args).decode("utf-8", "replace")
    except GitError:
        return []
    commits: list[CommitInfo] = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        parts = line.split(_FIELD)
        if len(parts) < 6:
            continue
        sha, parents, name, email, when, subject = parts[:6]
        commits.append(
            CommitInfo(
                sha=sha,
                parents=[p for p in parents.split() if p],
                author_name=name,
                author_email=email,
                authored_at=when,
                message=subject,
            )
        )
    return commits


def commit_exists(repo: Path, sha: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return False
    try:
        _git(repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    except GitError:
        return False
    return True


def diff_stats(repo: Path, old: str | None, new: str) -> dict[str, int]:
    if not old:
        files = list_all_paths(repo, new)
        return {"files": len(files), "additions": sum(entry.size or 0 for entry in files), "deletions": 0}
    try:
        raw = _git(repo, "diff", "--numstat", old, new).decode("utf-8", "replace")
    except GitError:
        return {"files": 0, "additions": 0, "deletions": 0}
    files = additions = deletions = 0
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        files += 1
        additions += int(parts[0]) if parts[0].isdigit() else 0
        deletions += int(parts[1]) if parts[1].isdigit() else 0
    return {"files": files, "additions": additions, "deletions": deletions}


def write_archive(repo: Path, rev: str, destination: Path, *, max_bytes: int) -> int:
    """Stream ``git archive`` output to ``destination`` enforcing a byte cap."""
    env = _env()
    proc = subprocess.Popen(
        ["git", "--git-dir", str(repo), "archive", "--format=zip", rev],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    written = 0
    assert proc.stdout is not None
    with destination.open("wb") as handle:
        while True:
            chunk = proc.stdout.read(1024 * 256)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                proc.kill()
                handle.close()
                destination.unlink(missing_ok=True)
                raise bad_request(
                    "ArchiveTooLarge",
                    "This project is too large to export in one archive.",
                    limit_bytes=max_bytes,
                )
            handle.write(chunk)
    proc.wait(timeout=60)
    if proc.returncode != 0:
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        destination.unlink(missing_ok=True)
        raise GitError(f"Archive export failed: {stderr.strip()[:400]}")
    return written


def is_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    try:
        data[:8192].decode("utf-8")
    except UnicodeDecodeError as exc:
        return exc.start < 8000
    return False


def delete_repo(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def repo_summary(repo: Path, branch: str) -> dict[str, Any]:
    sha = head_sha(repo, branch)
    if not sha:
        return {"revision": None, "files": 0, "commits": 0, "latest_commit": None}
    commits = log(repo, sha, limit=1)
    return {
        "revision": sha,
        "files": count_files(repo, sha),
        "commits": len(log(repo, sha, limit=200)),
        "latest_commit": (
            {
                "sha": commits[0].sha,
                "message": commits[0].message,
                "authored_at": commits[0].authored_at,
                "author_name": commits[0].author_name,
            }
            if commits
            else None
        ),
    }
