"""Process-only execution boundary for repository-owned Rust binaries."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from law_nexus_harness.result_schema import RustRunResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_OUTPUT_BYTES = 8192


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def _bounded_tail(value: bytes | str | None, limit: int) -> tuple[int, str, bool]:
    raw = _as_bytes(value)
    tail = raw[-limit:] if limit else b""
    return len(raw), tail.decode("utf-8", errors="replace"), len(raw) > limit


def run_rust_binary(
    binary: Path,
    args: Sequence[str] = (),
    *,
    cwd: Path = REPOSITORY_ROOT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> RustRunResult:
    """Run a Rust binary through a bounded subprocess boundary.

    The runner never forwards or logs an environment mapping and never loads a
    Rust shared library. The caller owns the explicit argument list.
    """

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_output_bytes < 0:
        raise ValueError("max_output_bytes must be non-negative")

    root = cwd.resolve()
    executable = binary if binary.is_absolute() else root / binary
    display_binary = _display_path(executable, root)
    display_command = (display_binary, *args)
    started = time.monotonic()

    try:
        completed = subprocess.run(  # noqa: S603 - explicit repository-owned binary boundary
            [str(executable), *args],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        stdout_bytes, stdout_tail, stdout_truncated = _bounded_tail(error.stdout, max_output_bytes)
        stderr_bytes, stderr_tail, stderr_truncated = _bounded_tail(error.stderr, max_output_bytes)
        return RustRunResult(
            command=display_command,
            binary_path=display_binary,
            phase="timeout",
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=None,
            timed_out=True,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            failure_class="timeout",
            status="failure",
        )
    except FileNotFoundError:
        return RustRunResult(
            command=display_command,
            binary_path=display_binary,
            phase="binary_missing",
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=None,
            timed_out=False,
            stdout_bytes=0,
            stderr_bytes=0,
            stdout_tail="",
            stderr_tail="",
            stdout_truncated=False,
            stderr_truncated=False,
            failure_class="binary_missing",
            status="failure",
        )
    except OSError as error:
        message = str(error).encode("utf-8", errors="replace")
        stderr_bytes, stderr_tail, stderr_truncated = _bounded_tail(message, max_output_bytes)
        return RustRunResult(
            command=display_command,
            binary_path=display_binary,
            phase="startup_error",
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=None,
            timed_out=False,
            stdout_bytes=0,
            stderr_bytes=stderr_bytes,
            stdout_tail="",
            stderr_tail=stderr_tail,
            stdout_truncated=False,
            stderr_truncated=stderr_truncated,
            failure_class="startup_oserror",
            status="failure",
        )

    stdout_bytes, stdout_tail, stdout_truncated = _bounded_tail(completed.stdout, max_output_bytes)
    stderr_bytes, stderr_tail, stderr_truncated = _bounded_tail(completed.stderr, max_output_bytes)
    succeeded = completed.returncode == 0
    return RustRunResult(
        command=display_command,
        binary_path=display_binary,
        phase="subprocess_complete",
        duration_ms=round((time.monotonic() - started) * 1000),
        exit_code=completed.returncode,
        timed_out=False,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        failure_class=None if succeeded else "nonzero_exit",
        status="ok" if succeeded else "failure",
    )
