#!/usr/bin/env python3
"""Allspark phase dispatch adapter for GSD Path 1.6.2 (repo-owned glue).

Upstream Path has no Allspark branch in its shared dispatch contract, so this
adapter executes the mandatory integration task from ``docs/agent-stack/WORKFLOW.md``
§3: it runs one fresh worker child per plan role and records what each child
produced. It never writes Path state, answers, or approvals; state mutations
stay with native Path helpers. Full contract: ``docs/agent-stack/PHASE-ADAPTER.md``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

PRIMARY = Path(__file__).resolve().parents[2]
CONFIG_PATH = PRIMARY / ".ai/path-run.json"
PLAN_SCHEMA = 1
RECORD_SCHEMA = "law-nexus-phase-dispatch/v1"
PLAN_SCHEMA_NAME = "law-nexus-phase-dispatch-plan/v1"
CAPTURE_LIMIT_BYTES = 256 * 1024
READ_CHUNK_BYTES = 65536
JOIN_GRACE_SECONDS = 5.0
INTERRUPT_SIGNALS = (signal.SIGTERM, signal.SIGINT)
INTERRUPT_GRACE_SECONDS = 2.0
WAIT_SLICE_SECONDS = 0.05
TOP_FIELDS = ("schema", "phase", "roles")
ROLE_FIELDS = ("name", "brief_file", "cwd", "timeout_seconds", "artifact")
# Mirrors the vendored GSD Path 1.6.2 dispatch_driver.py contract markers.
RESULT_LINE = re.compile(r"(?im)^RESULT:\s*(?P<task>\S+)\s+(?P<verdict>ready|blocked)\s*$")
QUESTION_MARK = "NEEDS-ORCHESTRATOR"


class PlanError(Exception):
    """The --plan file is not a valid dispatch plan (exit 2)."""


class UsageError(Exception):
    """The adapter invocation is unusable (exit 3)."""


class AdapterParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"usage error: {message}", file=sys.stderr)
        raise SystemExit(3)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _absolute_path(value: object, pointer: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise PlanError(f"plan error: {pointer} must be a non-empty string")
    if not Path(value).is_absolute():
        raise PlanError(f"plan error: {pointer} must be an absolute path: {value}")
    return value


def load_plan(path: Path) -> dict:
    try:
        text = path.read_bytes()
    except OSError as error:
        raise UsageError(f"usage error: cannot read plan {path}: {error}") from error
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PlanError(f"plan error: {path} is not valid JSON: {error}") from error
    if not isinstance(document, dict):
        raise PlanError(f"plan error: {path} must be a JSON object")
    unknown = sorted(set(document) - set(TOP_FIELDS))
    if unknown:
        raise PlanError(f"plan error: $ has unknown key {unknown[0]!r}")
    missing = [field for field in TOP_FIELDS if field not in document]
    if missing:
        raise PlanError(f"plan error: $ is missing required key {missing[0]!r}")
    if type(document["schema"]) is not int or document["schema"] != PLAN_SCHEMA:
        raise PlanError(f"plan error: $.schema must be {PLAN_SCHEMA}")
    phase = document["phase"]
    if not isinstance(phase, str) or not phase.strip() or "\0" in phase:
        raise PlanError("plan error: $.phase must be a non-empty string")
    roles = document["roles"]
    if not isinstance(roles, list) or not roles:
        raise PlanError("plan error: $.roles must be a non-empty array")
    names: set[str] = set()
    normalized = []
    for index, role in enumerate(roles):
        pointer = f"$.roles[{index}]"
        if not isinstance(role, dict):
            raise PlanError(f"plan error: {pointer} must be a JSON object")
        unknown = sorted(set(role) - set(ROLE_FIELDS))
        if unknown:
            raise PlanError(f"plan error: {pointer} has unknown key {unknown[0]!r}")
        missing = [field for field in ROLE_FIELDS if field not in role]
        if missing:
            raise PlanError(f"plan error: {pointer} is missing required key {missing[0]!r}")
        name = role["name"]
        if not isinstance(name, str) or not name.strip() or "\0" in name:
            raise PlanError(f"plan error: {pointer}.name must be a non-empty string")
        if name in names:
            raise PlanError(f"plan error: {pointer}.name duplicates earlier role {name!r}")
        names.add(name)
        brief_file = _absolute_path(role["brief_file"], f"{pointer}.brief_file")
        if not Path(brief_file).is_file():
            raise PlanError(
                f"plan error: {pointer}.brief_file is not an existing file: {brief_file}"
            )
        cwd = _absolute_path(role["cwd"], f"{pointer}.cwd")
        if not Path(cwd).is_dir():
            raise PlanError(f"plan error: {pointer}.cwd is not an existing directory: {cwd}")
        artifact = _absolute_path(role["artifact"], f"{pointer}.artifact")
        timeout = role["timeout_seconds"]
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise PlanError(
                f"plan error: {pointer}.timeout_seconds must be a positive finite number"
            )
        normalized.append(
            {
                "name": name,
                "brief_file": brief_file,
                "cwd": cwd,
                "timeout_seconds": timeout,
                "artifact": artifact,
            }
        )
    return {"phase": phase, "roles": normalized}


def parse_child_command(text: str) -> list[str]:
    try:
        argv = json.loads(text)
    except json.JSONDecodeError as error:
        raise UsageError(f"usage error: --child-command is not valid JSON: {error}") from error
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(item, str) or not item or "\0" in item for item in argv)
    ):
        raise UsageError("usage error: --child-command must be a JSON array of non-empty strings")
    return argv


def configured_worker() -> list[str]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except OSError as error:
        raise UsageError(
            f"usage error: cannot read worker configuration {CONFIG_PATH}: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise UsageError(
            f"usage error: worker configuration {CONFIG_PATH} is not valid JSON"
        ) from error
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise UsageError(f"usage error: invalid launcher configuration: {CONFIG_PATH}")
    argv = data.get("worker")
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(item, str) or not item or "\0" in item for item in argv)
    ):
        raise UsageError(
            f"usage error: worker must be a nonempty argv array of strings in {CONFIG_PATH}"
        )
    if not any(flag in argv for flag in ("-p", "--print")):
        raise UsageError(
            "usage error: Path worker argv must include -p/--print; Path does not add it"
        )
    executable = (PRIMARY / argv[0]).resolve()
    if not executable.is_file():
        raise UsageError(f"usage error: worker is missing: {executable}")
    return [str(executable), *argv[1:]]


def classify(timed_out: bool, exit_code: int | None, stdout_tail: str) -> str:
    """Map child evidence to a Path outcome.

    Precedence mirrors the vendored Path 1.6.2 dispatch_driver.py ``classify``:
    a killed or crashing child is a failure even when it wrote a question or a
    RESULT line; a clean exit is classified from the captured stdout tail.
    """
    if timed_out:
        return "timeout"
    if exit_code != 0:
        return "failed"
    if any(QUESTION_MARK in line for line in stdout_tail.splitlines()):
        return "question"
    matches = list(RESULT_LINE.finditer(stdout_tail))
    if matches:
        return matches[-1].group("verdict").lower()
    return "failed"


def kill_process_group(process: subprocess.Popen, number: int = signal.SIGKILL) -> None:
    try:
        os.killpg(process.pid, number)
    except ProcessLookupError:
        pass


def process_group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_process_group(process: subprocess.Popen) -> int:
    """Stop the whole worker group: SIGTERM, bounded grace, then SIGKILL; reap the child.

    The grace is measured on the group, not just the direct child: a worker that
    spawns helpers of its own can exit while a helper ignores SIGTERM.
    """
    kill_process_group(process, signal.SIGTERM)
    deadline = time.monotonic() + INTERRUPT_GRACE_SECONDS
    exit_code = None
    while True:
        if exit_code is None:
            exit_code = process.poll()
        if exit_code is not None and not process_group_alive(process.pid):
            return exit_code
        if time.monotonic() >= deadline:
            break
        time.sleep(WAIT_SLICE_SECONDS)
    kill_process_group(process)
    return process.wait()


class InterruptGuard:
    """Record SIGTERM/SIGINT so the active role can stop its worker and record it.

    Only a flag is set from the handler; cleanup and the default disposition
    re-raise happen on the main path, where the worker group is known.
    """

    def __init__(self) -> None:
        self._numbers: list[int] = []
        self._lock = threading.Lock()

    def install(self) -> InterruptGuard:
        for number in INTERRUPT_SIGNALS:
            signal.signal(number, self._record)
        return self

    def _record(self, number: int, frame: object) -> None:
        with self._lock:
            self._numbers.append(number)

    @property
    def signal_number(self) -> int | None:
        with self._lock:
            return self._numbers[0] if self._numbers else None

    @property
    def interrupted(self) -> bool:
        return self.signal_number is not None

    def terminate(self) -> None:
        """Die by the original signal, so the caller sees an interrupted exit.

        The default disposition is restored first so the signal really kills the
        process instead of re-entering this handler.
        """
        number = self.signal_number
        if number is None:
            return
        for candidate in INTERRUPT_SIGNALS:
            signal.signal(candidate, signal.SIG_DFL)
        os.kill(os.getpid(), number)


def feed_stdin(stream, payload: bytes) -> None:
    try:
        stream.write(payload)
        stream.flush()
    except OSError:
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


class TailReader(threading.Thread):
    """Drain one pipe from a daemon thread, keeping only the last `limit` bytes."""

    def __init__(self, stream, limit: int = CAPTURE_LIMIT_BYTES) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._limit = limit
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def run(self) -> None:
        while True:
            chunk = self._stream.read(READ_CHUNK_BYTES)
            if not chunk:
                break
            with self._lock:
                self._buffer += chunk
                if len(self._buffer) > self._limit:
                    del self._buffer[: len(self._buffer) - self._limit]

    def text(self) -> str:
        with self._lock:
            return bytes(self._buffer).decode("utf-8", errors="replace")


def await_child(
    process: subprocess.Popen, timeout_seconds: float, guard: InterruptGuard
) -> tuple[str, int]:
    """Wait for the child, honouring the role timeout and adapter interruptions.

    Returns ``(status, exit_code)`` where status is ``exited``, ``timeout`` or
    ``interrupted``; the timeout and interruption branches stop the whole
    worker group before returning, so no child outlives the adapter.
    """
    deadline = time.monotonic() + timeout_seconds
    while True:
        if guard.interrupted:
            return "interrupted", stop_process_group(process)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            kill_process_group(process)
            return "timeout", process.wait()
        try:
            return "exited", process.wait(timeout=min(remaining, WAIT_SLICE_SECONDS))
        except subprocess.TimeoutExpired:
            continue


def run_role(role: dict, argv: list[str], brief: bytes, guard: InterruptGuard) -> dict:
    started_at = now()
    started = time.monotonic()
    pid = None
    exit_code = None
    status = "not-started"  # replaced by await_child; a failed spawn never waits
    stdout_reader = None
    stderr_reader = None
    spawn_error = None
    try:
        process = subprocess.Popen(
            argv,
            cwd=role["cwd"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as error:
        spawn_error = error
        process = None
    if process is not None:
        pid = process.pid
        stdout_reader = TailReader(process.stdout)
        stderr_reader = TailReader(process.stderr)
        stdout_reader.start()
        stderr_reader.start()
        feeder = threading.Thread(target=feed_stdin, args=(process.stdin, brief), daemon=True)
        feeder.start()
        try:
            status, exit_code = await_child(process, role["timeout_seconds"], guard)
        finally:
            for thread in (feeder, stdout_reader, stderr_reader):
                thread.join(JOIN_GRACE_SECONDS)
    ended = time.monotonic()
    stdout_tail = stdout_reader.text() if stdout_reader is not None else ""
    stderr_tail = stderr_reader.text() if stderr_reader is not None else ""
    timed_out = status == "timeout"
    if spawn_error is not None:
        outcome = "failed"
        exit_code = None
        stderr_tail = f"spawn error: {spawn_error}"
    elif status == "interrupted":
        outcome = "interrupted"
    else:
        outcome = classify(timed_out, exit_code, stdout_tail)
    return {
        "name": role["name"],
        "brief_file": role["brief_file"],
        "cwd": role["cwd"],
        "pid": pid,
        "started_at": started_at,
        "ended_at": now(),
        "duration_ms": int((ended - started) * 1000),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "outcome": outcome,
    }


def read_brief(role: dict) -> bytes:
    try:
        return Path(role["brief_file"]).read_bytes()
    except OSError as error:
        raise PlanError(
            f"plan error: cannot read brief for role {role['name']!r}: {error}"
        ) from error


def overall_outcome(outcomes: list[str]) -> str:
    distinct = {outcome for outcome in outcomes if outcome != "ready"}
    if not distinct:
        return "ready"
    if len(distinct) == 1:
        return distinct.pop()
    return "mixed"


def dispatch_exit_code(outcomes: list[str]) -> int:
    if "interrupted" in outcomes:
        return 6
    if "failed" in outcomes or "timeout" in outcomes:
        return 5
    if "blocked" in outcomes or "question" in outcomes:
        return 4
    return 0


def run_plan(plan: dict, argv: list[str], guard: InterruptGuard) -> dict:
    started_at = now()
    records = []
    for role in plan["roles"]:
        if guard.interrupted:
            break
        record = run_role(role, argv, read_brief(role), guard)
        try:
            write_json(Path(role["artifact"]), record)
        except OSError as error:
            raise PlanError(
                f"plan error: cannot write artifact for role {role['name']!r}: {error}"
            ) from error
        records.append(record)
        print(
            f"[{role['name']}] outcome={record['outcome']} "
            f"exit_code={record['exit_code']} timed_out={record['timed_out']}",
            file=sys.stderr,
        )
    outcomes = [record["outcome"] for record in records]
    # An interruption that arrived between roles leaves no interrupted role
    # record, but the dispatch as a whole is still unfinished.
    overall = "interrupted" if guard.interrupted else overall_outcome(outcomes)
    return {
        "schema": RECORD_SCHEMA,
        "phase": plan["phase"],
        "started_at": started_at,
        "ended_at": now(),
        "roles": records,
        "overall": overall,
    }


def print_resolved_plan(plan: dict, argv: list[str]) -> None:
    payload = {
        "schema": PLAN_SCHEMA_NAME,
        "phase": plan["phase"],
        "worker": argv,
        "roles": [
            {
                "name": role["name"],
                "brief_file": role["brief_file"],
                "cwd": role["cwd"],
                "timeout_seconds": role["timeout_seconds"],
                "artifact": role["artifact"],
            }
            for role in plan["roles"]
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = AdapterParser(
        prog="phase-dispatch.py",
        description="Run one fresh Allspark worker child per dispatch-plan role and record outcomes.",
    )
    parser.add_argument("--plan", required=True, metavar="PATH", help="dispatch plan JSON file")
    parser.add_argument(
        "--record", required=True, metavar="PATH", help="summary dispatch record JSON output"
    )
    parser.add_argument(
        "--child-command",
        metavar="ARGV_JSON",
        help="override the worker argv with a JSON array; used verbatim (for stub tests)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the resolved plan without spawning anything"
    )
    arguments = parser.parse_args(argv)
    try:
        plan = load_plan(Path(arguments.plan))
        if arguments.child_command is not None:
            worker_argv = parse_child_command(arguments.child_command)
        else:
            worker_argv = configured_worker()
        if arguments.dry_run:
            print_resolved_plan(plan, worker_argv)
            return 0
        guard = InterruptGuard().install()
        record = run_plan(plan, worker_argv, guard)
        try:
            write_json(Path(arguments.record), record)
        except OSError as error:
            raise UsageError(
                f"usage error: cannot write record {arguments.record}: {error}"
            ) from error
        exit_code = dispatch_exit_code([role["outcome"] for role in record["roles"]])
        if guard.interrupted:
            print(
                f"interrupted by signal {guard.signal_number}; "
                f"active worker stopped and {len(record['roles'])} role record(s) written",
                file=sys.stderr,
            )
            guard.terminate()
        return exit_code
    except PlanError as error:
        print(str(error), file=sys.stderr)
        return 2
    except UsageError as error:
        print(str(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
