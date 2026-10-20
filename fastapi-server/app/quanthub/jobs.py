"""Background execution of QEC experiments.

Experiments run in a **separate OS process** with CPU, memory and wall-clock
limits, never inside the FastAPI event loop or the API process itself.  This
gives real cancellation (process-group kill), isolates engine crashes, and
prevents a pathological protocol from taking down the API.

Deployment note: the job registry is in-process.  Run the API with a single
worker (``uvicorn --workers 1``) or move ``jobs`` onto a dedicated worker; the
database remains the source of truth and stale runs are reconciled on read.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.quanthub import config, db

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="quanthub-run")
_SEMAPHORE = threading.BoundedSemaphore(max(1, config.limits().max_concurrent_runs))
_LOCK = threading.Lock()
_PROCESSES: dict[str, subprocess.Popen[bytes]] = {}
_CANCEL: set[str] = set()

MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024


def _guarded_command(command: list[str]) -> list[str]:
    """Wrap a command with POSIX resource limits.

    ``preexec_fn`` is deliberately avoided: it is unsafe in a threaded server.
    ``ulimit`` is applied by ``/bin/sh`` before ``exec`` replaces the shell, so
    the limits are inherited by the engine process without a fork hook.
    """
    cpu = max(30, config.limits().experiment_timeout_seconds)
    memory_kb = MEMORY_LIMIT_BYTES // 1024
    script = (
        f"ulimit -t {cpu} 2>/dev/null || true; "
        f"ulimit -v {memory_kb} 2>/dev/null || true; "
        f"ulimit -n 512 2>/dev/null || true; "
        'exec "$@"'
    )
    if os.name == "posix" and Path("/bin/sh").exists():
        return ["/bin/sh", "-c", script, "quanthub-run", *command]
    return command


def _update(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    columns = ", ".join(f"{key} = ?" for key in fields)
    with db.db() as conn:
        conn.execute(f"UPDATE runs SET {columns} WHERE id = ?", [*fields.values(), run_id])


def request_cancel(run_id: str) -> None:
    with _LOCK:
        _CANCEL.add(run_id)
        process = _PROCESSES.get(run_id)
    if process is None:
        return
    _terminate(process)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()


def _tail(path: Path, limit: int = 1200) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-limit:].strip()


def submit(ctx: Any, run_id: str, protocol_path: Path, artifacts_root: Path, log_path: Path) -> None:
    _EXECUTOR.submit(_execute, ctx.id, run_id, protocol_path, artifacts_root, log_path)


def _execute(
    project_id: str,
    run_id: str,
    protocol_path: Path,
    artifacts_root: Path,
    log_path: Path,
) -> None:
    conf = config.limits()
    timed_out = False
    cancelled = False
    exit_code = -1
    with _SEMAPHORE:
        with _LOCK:
            cancelled_early = run_id in _CANCEL
        if cancelled_early:
            _update(
                run_id,
                status="cancelled",
                finished_at=db.utc_now(),
                error="Cancelled before execution started.",
            )
            return
        _update(run_id, status="running", started_at=db.utc_now())

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONUNBUFFERED": "1",
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "MPLBACKEND": "Agg",
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C.UTF-8",
        }
        command = [
            sys.executable,
            "-m",
            "quantumlab.research.qec",
            "run",
            str(protocol_path),
            "--output",
            str(artifacts_root),
            "--experiment-id",
            run_id,
        ]
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("wb") as log_handle:
            log_handle.write(
                f"# QuantHub experiment run {run_id}\n# protocol: {protocol_path}\n".encode()
            )
            log_handle.flush()
            try:
                process = subprocess.Popen(
                    _guarded_command(command),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env,
                    cwd=str(protocol_path.parent),
                    start_new_session=True,
                )
            except OSError as exc:
                _update(
                    run_id,
                    status="failed",
                    finished_at=db.utc_now(),
                    error=f"Could not start the execution engine: {exc}",
                )
                return
            with _LOCK:
                _PROCESSES[run_id] = process

            deadline = time.monotonic() + conf.experiment_timeout_seconds
            try:
                while True:
                    if process.poll() is not None:
                        break
                    with _LOCK:
                        cancel = run_id in _CANCEL
                    if cancel:
                        cancelled = True
                        _terminate(process)
                        break
                    if time.monotonic() > deadline:
                        timed_out = True
                        _terminate(process)
                        break
                    time.sleep(0.2)
                exit_code = process.wait(timeout=30)
            finally:
                with _LOCK:
                    _PROCESSES.pop(run_id, None)

    # A cancellation can race with process exit: ``poll()`` may observe the
    # terminated process before the loop notices the cancel flag. Resolve the
    # final state from both the in-memory flag and the persisted request.
    with _LOCK:
        cancelled = cancelled or run_id in _CANCEL
        _CANCEL.discard(run_id)
    with db.db() as conn:
        stored = conn.execute(
            "SELECT cancel_requested FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
    if stored is not None and int(stored["cancel_requested"] or 0) == 1:
        cancelled = True

    artifact_dir = artifacts_root / run_id
    summary: dict[str, Any] | None = None
    summary_path = artifact_dir / "summary.json"
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            summary = None

    if cancelled:
        status = "cancelled"
        error = "Cancelled by the user."
    elif timed_out:
        status = "failed"
        error = f"Run exceeded the {conf.experiment_timeout_seconds}s execution limit."
    elif exit_code == 0 and summary is not None:
        status = "completed"
        error = None
    else:
        status = "failed"
        error = (
            f"Engine exited with code {exit_code}. "
            f"{_tail(log_path) or 'No engine output was produced.'}"
        )

    software_revision = None
    if summary:
        provenance = summary.get("provenance")
        if isinstance(provenance, dict):
            software_revision = provenance.get("source_revision")

    payload = json.dumps(summary, sort_keys=True) if summary else None
    if payload is not None and len(payload) > 4 * 1024 * 1024:
        payload = json.dumps(
            {"truncated": True, "note": "Summary exceeded the metadata limit; see artifacts."}
        )
    _update(
        run_id,
        status=status,
        finished_at=db.utc_now(),
        exit_code=exit_code,
        error=error,
        artifacts_path=str(artifact_dir) if artifact_dir.is_dir() else None,
        summary=payload,
        software_revision=software_revision,
    )
    with db.db() as conn:
        db.record_activity(
            conn,
            project_id=project_id,
            actor_id=None,
            actor_handle="engine",
            event_type=f"run.{status}",
            payload={"run_id": run_id, "exit_code": exit_code},
        )


def reconcile_stale_runs(project_id: str, *, older_than_seconds: int | None = None) -> None:
    """Mark rows left 'running' by a dead worker as failed.

    Only called from read paths, and only for runs old enough that no live
    process could plausibly still be working on them.
    """
    threshold = older_than_seconds or (config.limits().experiment_timeout_seconds * 2)
    cutoff = time.time() - threshold
    with db.db() as conn:
        rows = conn.execute(
            "SELECT id, created_at, status FROM runs WHERE project_id = ? AND status IN"
            " ('queued', 'running', 'cancelling')",
            (project_id,),
        ).fetchall()
    for row in rows:
        with _LOCK:
            active = row["id"] in _PROCESSES or row["id"] in _CANCEL
        if active:
            continue
        try:
            from datetime import datetime

            created = datetime.fromisoformat(str(row["created_at"]))
            if created.timestamp() > cutoff:
                continue
        except ValueError:
            continue
        _update(
            row["id"],
            status="failed",
            finished_at=db.utc_now(),
            error="Execution worker stopped before this run finished. Re-run to regenerate evidence.",
        )
