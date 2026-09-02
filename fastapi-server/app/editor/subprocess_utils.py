"""Shared subprocess isolation helpers for editor execution."""

from __future__ import annotations

import asyncio
import os
import signal
import sys

MAX_OUTPUT_BYTES = 64_000


def sanitized_env() -> dict[str, str]:
    """Build a minimal environment without application secrets."""
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "LANG",
        "LC_ALL",
        "DOTNET_ROOT",
        "DOTNET_MULTILEVEL_LOOKUP",
    }
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


async def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    if sys.platform == "win32":
        proc.kill()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            proc.kill()
    try:
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pass


async def run_isolated_subprocess(
    cmd: list[str],
    *,
    cwd: str,
    timeout_s: float,
) -> tuple[str, str, int]:
    """Run a command in an isolated subprocess with timeout and output caps."""
    start_new_session = sys.platform != "win32"
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=sanitized_env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=start_new_session,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        await _kill_process_tree(proc)
        return "", "Execution timed out", -1

    stdout = stdout_b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    stderr = stderr_b[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    if len(stdout_b) > MAX_OUTPUT_BYTES:
        stdout += "\n[output truncated]"
    if len(stderr_b) > MAX_OUTPUT_BYTES:
        stderr += "\n[stderr truncated]"
    return stdout, stderr, proc.returncode if proc.returncode is not None else 0
