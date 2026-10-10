#!/usr/bin/env python3
"""M223/S02 cleaned-path resource probe (process-only harness).

This helper measures the *cleaned projection* path over a bounded, deterministic
stratified sample of the pinned Consultant corpus.  It is a process harness: it
spawns the real ``cleaned-project`` binary, live-enforces and measures wall time
and peak RSS, performs an actual cleaned read-back (``cleaned-project read``) for
every successful export, and writes closed-vocabulary outcomes.

Design constraints (M223-S02-readback-budget and M223-S02-live-rss-bound rework
findings):

* declared time / RSS / output / disk bounds are live-enforced while each child
  runs (the parent polls ``/proc/<pid>/status`` VmHWM, the growing artifact size
  and free disk, and SIGKILLs the child on breach), not merely classified after
  exit; ``rss_enforced`` records whether live sampling was actually possible, so
  a measured value is never presented as enforced;
* the harness does **not** claim ``RLIMIT_RSS`` (a no-op on Linux) or
  ``RLIMIT_AS`` (a virtual-address cap) enforcement;
* every successful export gets its own read-back outcome and timing — the
  read-back is *not* presented as an independent substrate verify (that is
  ``cleaned-project verify`` and belongs elsewhere);
* a harness timeout / resource breach is classified separately from a typed
  product refusal (exit 5) or any other product exit;
* the harness never re-implements product parsing.  Structural classification
  uses already-ready metadata: manifest bytes and the counts-only read-back
  summary emitted by the Rust product;
* evidence is persisted incrementally, so an interruption keeps every completed
  record and the process exits with the original signal-derived code.

No raw decoded text ever reaches the evidence or the diagnostics: only paths,
counts, sizes and hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m223-s02-clean-path-probe/v1"
VERSION = 1
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_CORPUS_ROOT = "consru_export/consru_export/exports"
DEFAULT_BIN = ROOT / "target/release/cleaned-project"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m223-s02-clean-path-probe.json"

# Read-back counts-only keys emitted by `cleaned-project read` (Rust product).
READBACK_INT_KEYS = (
    "views",
    "segments",
    "references",
    "source_segments",
    "derived_segments",
    "records",
    "text_chars",
    "text_bytes",
    "inline_chars",
    "inline_bytes",
)
READBACK_STR_KEYS = ("contract_version", "completion", "completion_basis", "incomplete_reasons")

# Closed outcome vocabulary for one sampled file.
EXPORT_OUTCOMES = (
    "accepted",
    "typed_refusal",
    "usage_error",
    "out_unwritable",
    "artifact_verify_failed",
    "exec_error",
    "timeout",
    "signaled",
    "rss_limit_exceeded",
    "output_limit_exceeded",
    "disk_limit_exceeded",
    "unknown_exit",
    "harness_error",
    "not_run",
)
READBACK_OUTCOMES = (
    "readback_ok",
    "readback_failed",
    "readback_usage_error",
    "readback_timeout",
    "readback_signaled",
    "readback_rss_exceeded",
    "readback_disk_exceeded",
    "readback_error",
)
RUN_STATUSES = ("complete", "interrupted", "budget_exhausted", "disk_guard_stopped")


@dataclass(frozen=True)
class Limits:
    """Declared resource bounds; a breach is a failure, never a silent pass."""

    export_wall_s: float = 180.0
    readback_wall_s: float = 60.0
    peak_rss_kb: int = 6 * 1024 * 1024
    min_free_disk_bytes: int = 2 * 1024**3
    abort_free_disk_bytes: int = 1 * 1024**3
    max_single_artifact_bytes: int = 2 * 1024**3
    total_budget_wall_s: float = 1800.0


@dataclass
class Entry:
    relative_path: str
    sha256: str
    bytes: int


@dataclass
class SampleItem:
    relative_path: str
    bytes: int
    strata: list[str] = field(default_factory=list)


class Interrupted(Exception):
    """Raised from a SIGINT/SIGTERM handler to unwind the run loop."""

    def __init__(self, signum: int) -> None:
        super().__init__(f"interrupted by signal {signum}")
        self.signum = signum


# --------------------------------------------------------------- manifest #


def parse_manifest(path: Path) -> tuple[dict[str, Any], list[Entry]]:
    """Read the T01 JSONL manifest: header record + one entry per file."""
    header: dict[str, Any] | None = None
    entries: list[Entry] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if header is None:
                if record.get("schema") != "m223-s02-corpus-inventory/v1":
                    raise ValueError(f"unexpected manifest schema: {record.get('schema')!r}")
                header = record
                continue
            entries.append(
                Entry(
                    relative_path=record["relative_path"],
                    sha256=record["sha256"],
                    bytes=int(record["bytes"]),
                )
            )
    if header is None:
        raise ValueError("manifest has no header record")
    return header, entries


def build_sample(
    entries: list[Entry], *, seed: int, per_decile: int, tail_n: int
) -> tuple[list[SampleItem], dict[str, Any]]:
    """Deterministic stratified sample: per-decile picks + the largest tail.

    Strata are size deciles by rank over the full manifest.  A fixed seed draws
    ``per_decile`` files from each decile; the ``tail_n`` largest files are added
    unconditionally because the tail drives the feasibility decision (§8.5).
    """
    by_size = sorted(entries, key=lambda e: (e.bytes, e.relative_path))
    total = len(by_size)
    deciles: list[list[Entry]] = [[] for _ in range(10)]
    for index, entry in enumerate(by_size):
        deciles[min(9, index * 10 // total)].append(entry)

    rng = random.Random(seed)
    chosen: dict[str, SampleItem] = {}
    strata_counts: dict[str, int] = {}
    for decile_index, bucket in enumerate(deciles):
        picked = rng.sample(bucket, min(per_decile, len(bucket)))
        strata_counts[f"decile_{decile_index}"] = len(picked)
        for entry in picked:
            item = chosen.setdefault(
                entry.relative_path, SampleItem(entry.relative_path, entry.bytes)
            )
            item.strata.append(f"decile_{decile_index}")

    tail = by_size[-tail_n:] if tail_n > 0 else []
    tail_included = 0
    for entry in tail:
        item = chosen.setdefault(entry.relative_path, SampleItem(entry.relative_path, entry.bytes))
        if "tail_largest" not in item.strata:
            item.strata.append("tail_largest")
            tail_included += 1

    sample = sorted(chosen.values(), key=lambda item: item.relative_path)
    strata = {
        "deciles": strata_counts,
        "tail_n": tail_n,
        "tail_included": tail_included,
        "union_count": len(sample),
        "per_decile": per_decile,
    }
    return sample, strata


# -------------------------------------------------------------- measuring #


def _proc_peak_rss_kb(pid: int) -> int | None:
    """Live peak RSS (VmHWM) of a running child, or ``None`` if unavailable."""
    try:
        with open(f"/proc/{pid}/status", "rb") as stream:
            for line in stream:
                if line.startswith(b"VmHWM:"):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _kill_child(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def measure_subprocess(
    argv: list[str],
    *,
    timeout_s: float,
    cwd: Path | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    rss_limit_kb: int | None = None,
    output_path: Path | None = None,
    max_output_bytes: int | None = None,
    disk_free_probe: Any = None,
    disk_floor_bytes: int | None = None,
    poll_s: float = 0.02,
) -> dict[str, Any]:
    """Fork/exec one child and *live-enforce* the declared resource bounds.

    The bounds are enforced while the child runs, not merely classified after
    exit: the parent polls the child's peak RSS (``/proc/<pid>/status`` VmHWM),
    the growing ``output_path`` size, and the free-disk probe, and SIGKILLs the
    child as soon as a bound is crossed.  This deliberately does not use
    ``RLIMIT_RSS`` (a no-op on Linux) or ``RLIMIT_AS`` (a virtual-address cap,
    not a resident-size cap); it reports ``rss_enforced`` so a measured value is
    never presented as enforced when ``/proc`` was unavailable.  ``os.wait4``
    supplies the per-child ``ru_maxrss`` high-water mark in KB after exit.
    """
    stdout_fd = (
        os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        if stdout_path
        else os.open(os.devnull, os.O_WRONLY)
    )
    try:
        stderr_fd = (
            os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            if stderr_path
            else os.open(os.devnull, os.O_WRONLY)
        )
    except OSError:
        os.close(stdout_fd)
        raise

    started = time.monotonic()
    pid = os.fork()
    if pid == 0:  # child
        try:
            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)
            if cwd is not None:
                os.chdir(cwd)
            os.execv(argv[0], argv)
        except OSError:
            pass
        os._exit(127)

    # Guard the whole parent-side lifetime after the fork.  If this frame
    # unwinds for any reason — notably a SIGINT/SIGTERM handler raising
    # `Interrupted` from inside the poll loop — the running child is SIGKILLed
    # and reaped here, so an interrupted attempt never orphans an export.
    try:
        os.close(stdout_fd)
        os.close(stderr_fd)

        timed_out = False
        rss_exceeded = False
        output_exceeded = False
        disk_exceeded = False
        rss_enforced = False
        observed_rss = 0
        observed_output = 0
        status = 0
        usage: Any = None
        last_disk_check = 0.0

        # The product's atomic publisher writes `<path>.tmp` and renames it onto
        # `<path>`, so the growing payload is the sibling `.tmp`, not the final
        # path.  Guard the final artifact *and* its `.tmp` sibling while the child
        # runs, and re-check after exit (the loop may end before a fast publisher
        # publishes) so an oversized atomic output is never accepted.
        guard_paths: list[Path] = []
        if output_path is not None:
            guard_paths = [output_path, Path(str(output_path) + ".tmp")]

        def output_size() -> int:
            largest = 0
            for candidate in guard_paths:
                try:
                    largest = max(largest, os.path.getsize(candidate))
                except OSError:
                    continue
            return largest

        while True:
            wpid, status, usage = os.wait4(pid, os.WNOHANG)
            if wpid == pid:
                break
            now = time.monotonic()
            if now - started > timeout_s:
                timed_out = True
                _kill_child(pid)
                _, status, usage = os.wait4(pid, 0)
                break
            if rss_limit_kb is not None:
                peak = _proc_peak_rss_kb(pid)
                if peak is not None:
                    rss_enforced = True
                    observed_rss = max(observed_rss, peak)
                    if peak > rss_limit_kb:
                        rss_exceeded = True
                        _kill_child(pid)
                        _, status, usage = os.wait4(pid, 0)
                        break
            if guard_paths and max_output_bytes is not None:
                size = output_size()
                observed_output = max(observed_output, size)
                if size > max_output_bytes:
                    output_exceeded = True
                    _kill_child(pid)
                    _, status, usage = os.wait4(pid, 0)
                    break
            if (
                disk_free_probe is not None
                and disk_floor_bytes is not None
                and now - last_disk_check > 0.2
            ):
                last_disk_check = now
                try:
                    free_now = disk_free_probe()
                except OSError:
                    free_now = None
                if free_now is not None and free_now < disk_floor_bytes:
                    disk_exceeded = True
                    _kill_child(pid)
                    _, status, usage = os.wait4(pid, 0)
                    break
            time.sleep(poll_s)
    except BaseException:
        _kill_child(pid)
        try:
            os.wait4(pid, 0)
        except OSError:
            pass
        raise

    wall_s = time.monotonic() - started
    signaled = os.WIFSIGNALED(status)
    rc = None if signaled else os.WEXITSTATUS(status)
    # Post-exit budget check: the wait loop can end before a fast atomic
    # publisher renames `<path>.tmp` onto `<path>`.  This detects an oversized
    # final/tmp artifact and marks the breach, keeping the child's original rc
    # separate from the budget verdict.
    if guard_paths and max_output_bytes is not None:
        final_size = output_size()
        observed_output = max(observed_output, final_size)
        if final_size > max_output_bytes:
            output_exceeded = True
    final_rss = int(usage.ru_maxrss) if usage is not None else 0
    peak_rss_kb = max(final_rss, observed_rss) if (final_rss or observed_rss) else None
    return {
        "wall_s": round(wall_s, 6),
        "peak_rss_kb": peak_rss_kb,
        "rc": rc,
        "signal": signal.Signals(os.WTERMSIG(status)).name if signaled else None,
        "timed_out": timed_out,
        "exec_error": (not signaled) and rc == 127,
        "rss_exceeded": rss_exceeded,
        "output_exceeded": output_exceeded,
        "disk_exceeded": disk_exceeded,
        "rss_enforced": rss_enforced,
        "observed_output_bytes": observed_output,
    }


def classify_export(result: dict[str, Any], limits: Limits) -> str:
    """Closed outcome for one export child (harness breach beats product exit)."""
    if result["timed_out"]:
        return "timeout"
    if result.get("rss_exceeded"):
        return "rss_limit_exceeded"
    if result.get("output_exceeded"):
        return "output_limit_exceeded"
    if result.get("disk_exceeded"):
        return "disk_limit_exceeded"
    if result["signal"] is not None:
        return "signaled"
    rc = result["rc"]
    if rc == 0:
        # Residual post-hoc detection for the case where live /proc sampling was
        # unavailable; it never replaces live enforcement, only backs it up.
        if result["peak_rss_kb"] is not None and result["peak_rss_kb"] > limits.peak_rss_kb:
            return "rss_limit_exceeded"
        return "accepted"
    if rc == 5:
        return "typed_refusal"
    if rc == 2:
        return "usage_error"
    if rc == 3:
        return "out_unwritable"
    if rc == 4:
        return "artifact_verify_failed"
    if rc == 127:
        return "exec_error"
    return "unknown_exit"


def classify_readback(result: dict[str, Any]) -> str:
    """Closed outcome for one read-back child (separate from the export)."""
    if result["timed_out"]:
        return "readback_timeout"
    if result.get("rss_exceeded"):
        return "readback_rss_exceeded"
    if result.get("disk_exceeded"):
        return "readback_disk_exceeded"
    if result["signal"] is not None:
        return "readback_signaled"
    rc = result["rc"]
    if rc == 0:
        return "readback_ok"
    if rc == 4:
        return "readback_failed"
    if rc == 2:
        return "readback_usage_error"
    return "readback_error"


def parse_readback_counts(text: str) -> dict[str, Any]:
    """Parse the product's counts-only summary.  Never returns decoded text."""
    ints: dict[str, int] = {}
    strs: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        if key in READBACK_INT_KEYS:
            try:
                ints[key] = int(value)
            except ValueError:
                continue
        elif key in READBACK_STR_KEYS:
            strs[key] = value
    return {"counts": ints, "declared": strs}


# ------------------------------------------------------------------- disk #


def disk_snapshot(path: Path) -> dict[str, int]:
    stat = os.statvfs(path)
    free = stat.f_bavail * stat.f_frsize
    total = stat.f_blocks * stat.f_frsize
    return {"free_bytes": free, "total_bytes": total}


# --------------------------------------------------------------- run loop #


def run_probe(
    *,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    sample: list[SampleItem],
    limits: Limits,
    tmp_dir: Path,
    on_record: Any = None,
) -> dict[str, Any]:
    """Run the measured export + read-back for every sampled file."""
    disk_before = disk_snapshot(tmp_dir)
    records: list[dict[str, Any]] = []
    started = time.monotonic()
    run_status = "complete"
    peak_tmp_bytes = 0
    transient_output_bytes = 0

    def emit(record: dict[str, Any]) -> None:
        records.append(record)
        if on_record is not None:
            on_record(records)

    try:
        for item in sample:
            free = disk_snapshot(tmp_dir)["free_bytes"]
            if free < limits.abort_free_disk_bytes:
                run_status = "disk_guard_stopped"
                emit(_not_run_record(item, "not_run"))
                continue
            if time.monotonic() - started > limits.total_budget_wall_s:
                run_status = "budget_exhausted"
                emit(_not_run_record(item, "not_run"))
                continue

            artifact = (
                tmp_dir
                / f"artifact-{hashlib.sha256(item.relative_path.encode()).hexdigest()[:16]}.json"
            )
            export_stdout = tmp_dir / "export.stdout"
            export_stderr = tmp_dir / "export.stderr"
            record: dict[str, Any] = {
                "relative_path": item.relative_path,
                "input_bytes": item.bytes,
                "strata": list(item.strata),
                "outcome": None,
                "export": None,
                "readback": None,
                "output_bytes": None,
                "output_input_ratio": None,
                "tmp_removed": True,
            }
            try:
                if free < limits.min_free_disk_bytes:
                    record["outcome"] = "not_run"
                    record["export"] = {"note": "free disk below declared minimum before file"}
                    emit(record)
                    continue

                try:
                    export_result = measure_subprocess(
                        [
                            str(bin_path),
                            "export",
                            "--from-xml",
                            str(corpus_root / item.relative_path),
                            "--out",
                            str(artifact),
                        ],
                        timeout_s=limits.export_wall_s,
                        cwd=ROOT,
                        stdout_path=export_stdout,
                        stderr_path=export_stderr,
                        rss_limit_kb=limits.peak_rss_kb,
                        output_path=artifact,
                        max_output_bytes=limits.max_single_artifact_bytes,
                        disk_free_probe=lambda: disk_snapshot(tmp_dir)["free_bytes"],
                        disk_floor_bytes=limits.abort_free_disk_bytes,
                    )
                except OSError as error:  # harness-level failure, not a product refusal
                    record["outcome"] = "harness_error"
                    record["export"] = {"error": f"{type(error).__name__}: {error}"}
                    emit(record)
                    continue
                outcome = classify_export(export_result, limits)
                record["outcome"] = outcome
                record["export"] = {
                    "rc": export_result["rc"],
                    "signal": export_result["signal"],
                    "timed_out": export_result["timed_out"],
                    "wall_s": export_result["wall_s"],
                    "peak_rss_kb": export_result["peak_rss_kb"],
                    "rss_enforced": export_result["rss_enforced"],
                    "rss_exceeded": export_result["rss_exceeded"],
                    "output_exceeded": export_result["output_exceeded"],
                    "disk_exceeded": export_result["disk_exceeded"],
                    "observed_output_bytes": export_result["observed_output_bytes"],
                    "stderr_bytes": export_stderr.stat().st_size if export_stderr.exists() else 0,
                }

                if outcome == "accepted" and artifact.exists():
                    output_bytes = artifact.stat().st_size
                    record["output_bytes"] = output_bytes
                    if item.bytes > 0:
                        record["output_input_ratio"] = round(output_bytes / item.bytes, 6)
                    transient_output_bytes += output_bytes
                    peak_tmp_bytes = max(peak_tmp_bytes, output_bytes)

                    readback_stdout = tmp_dir / "readback.stdout"
                    readback_stderr = tmp_dir / "readback.stderr"
                    try:
                        readback_result = measure_subprocess(
                            [str(bin_path), "read", "--artifact", str(artifact)],
                            timeout_s=limits.readback_wall_s,
                            cwd=ROOT,
                            stdout_path=readback_stdout,
                            stderr_path=readback_stderr,
                            rss_limit_kb=limits.peak_rss_kb,
                            disk_free_probe=lambda: disk_snapshot(tmp_dir)["free_bytes"],
                            disk_floor_bytes=limits.abort_free_disk_bytes,
                        )
                        readback_outcome = classify_readback(readback_result)
                    except OSError:
                        readback_result = {
                            "rc": None,
                            "signal": None,
                            "timed_out": False,
                            "wall_s": None,
                            "peak_rss_kb": None,
                            "rss_enforced": False,
                            "rss_exceeded": False,
                            "disk_exceeded": False,
                        }
                        readback_outcome = "readback_error"
                    parsed: dict[str, Any] = {"counts": {}, "declared": {}}
                    if readback_outcome == "readback_ok" and readback_stdout.exists():
                        parsed = parse_readback_counts(readback_stdout.read_text(encoding="utf-8"))
                    record["readback"] = {
                        "outcome": readback_outcome,
                        "rc": readback_result["rc"],
                        "signal": readback_result["signal"],
                        "timed_out": readback_result["timed_out"],
                        "wall_s": readback_result["wall_s"],
                        "peak_rss_kb": readback_result["peak_rss_kb"],
                        "rss_enforced": readback_result["rss_enforced"],
                        "rss_exceeded": readback_result["rss_exceeded"],
                        "counts": parsed["counts"],
                        "declared": parsed["declared"],
                    }
                emit(record)
            finally:
                removed = True
                for leftover in (
                    artifact,
                    Path(str(artifact) + ".tmp"),
                    export_stdout,
                    export_stderr,
                    tmp_dir / "readback.stdout",
                    tmp_dir / "readback.stderr",
                ):
                    if leftover.exists():
                        try:
                            leftover.unlink()
                        except OSError:
                            removed = False
                record["tmp_removed"] = removed
                if not removed:
                    run_status = "interrupted"
    except Interrupted:
        raise
    finally:
        pass

    disk_after = disk_snapshot(tmp_dir)
    return {
        "records": records,
        "run_status": run_status,
        "disk_before": disk_before,
        "disk_after": disk_after,
        "peak_tmp_artifact_bytes": peak_tmp_bytes,
        "transient_output_bytes": transient_output_bytes,
        "elapsed_s": round(time.monotonic() - started, 3),
    }


def _not_run_record(item: SampleItem, outcome: str) -> dict[str, Any]:
    return {
        "relative_path": item.relative_path,
        "input_bytes": item.bytes,
        "strata": list(item.strata),
        "outcome": outcome,
        "export": None,
        "readback": None,
        "output_bytes": None,
        "output_input_ratio": None,
        "tmp_removed": True,
    }


# ------------------------------------------------------------------ stats #


def percentile(sorted_values: list[float], q: float) -> float | None:
    """Linear-interpolation percentile (numpy default); ``None`` when empty."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * (q / 100.0)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def _stats(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "median": percentile(ordered, 50),
        "p95": percentile(ordered, 95),
        "max": ordered[-1] if ordered else None,
        "min": ordered[0] if ordered else None,
    }


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Median/p95/max for wall, RSS, output and ratio over accepted exports."""
    accepted = [r for r in records if r["outcome"] == "accepted"]
    wall = [r["export"]["wall_s"] for r in accepted]
    rss = [float(r["export"]["peak_rss_kb"]) for r in accepted if r["export"]["peak_rss_kb"]]
    output = [float(r["output_bytes"]) for r in accepted if r["output_bytes"] is not None]
    ratio = [
        float(r["output_input_ratio"]) for r in accepted if r["output_input_ratio"] is not None
    ]
    readback_wall = [
        r["readback"]["wall_s"]
        for r in accepted
        if r["readback"] and r["readback"]["outcome"] == "readback_ok"
    ]
    outcome_counts: dict[str, int] = {}
    for record in records:
        outcome_counts[record["outcome"]] = outcome_counts.get(record["outcome"], 0) + 1
    subject_to_live_rss = [r for r in records if r["export"] and "rss_enforced" in r["export"]]
    rss_enforced = sum(1 for r in subject_to_live_rss if r["export"]["rss_enforced"])
    readback_rss_enforced = sum(
        1 for r in accepted if r["readback"] and r["readback"].get("rss_enforced")
    )
    return {
        "sampled": len(records),
        "accepted": len(accepted),
        "accept_rate": round(len(accepted) / len(records), 6) if records else None,
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "rss_enforced_files": rss_enforced,
        "rss_enforced_candidates": len(subject_to_live_rss),
        "readback_rss_enforced_files": readback_rss_enforced,
        "export_wall_s": _stats(wall),
        "export_peak_rss_kb": _stats(rss),
        "output_bytes": _stats(output),
        "output_input_ratio": _stats(ratio),
        "readback_wall_s": _stats(readback_wall),
    }


def complex_classes(records: list[dict[str, Any]], top_n: int = 10) -> dict[str, Any]:
    """Tail-driving classes from measured values and ready product metadata."""

    def top(key: Any) -> list[dict[str, Any]]:
        scored = [(key(r), r) for r in records if key(r) is not None]
        scored.sort(key=lambda pair: (-pair[0], pair[1]["relative_path"]))
        return [
            {"relative_path": r["relative_path"], "value": round(float(value), 6)}
            for value, r in scored[:top_n]
        ]

    def readback_count(record: dict[str, Any], name: str) -> float | None:
        readback = record.get("readback")
        if not readback or readback.get("outcome") != "readback_ok":
            return None
        value = readback["counts"].get(name)
        return float(value) if value is not None else None

    def density(name: str) -> Any:
        def inner(record: dict[str, Any]) -> float | None:
            value = readback_count(record, name)
            if value is None or not record["input_bytes"]:
                return None
            return value / (record["input_bytes"] / 1024.0)

        return inner

    return {
        "slowest_export": top(lambda r: r["export"]["wall_s"] if r["export"] else None),
        "peak_rss": top(
            lambda r: (
                float(r["export"]["peak_rss_kb"])
                if r["export"] and r["export"]["peak_rss_kb"]
                else None
            )
        ),
        "largest_output": top(
            lambda r: float(r["output_bytes"]) if r["output_bytes"] is not None else None
        ),
        "largest_input": top(lambda r: float(r["input_bytes"])),
        "largest_text": top(lambda r: readback_count(r, "text_chars")),
        "densest_records_per_kib": top(density("records")),
        "densest_segments_per_kib": top(density("segments")),
        "most_references": top(lambda r: readback_count(r, "references")),
    }


# ----------------------------------------------------------------- output #


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def write_evidence(payload: dict[str, Any], path: Path) -> None:
    """Atomic incremental write: a killed run keeps the last complete records."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(tmp, path)


def build_payload(
    *,
    header: dict[str, Any],
    manifest_path: Path,
    sample: list[SampleItem],
    strata: dict[str, Any],
    limits: Limits,
    run: dict[str, Any],
    seed: int,
    bin_path: Path,
    corpus_root: Path,
) -> dict[str, Any]:
    records = run["records"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "corpus_root": str(corpus_root),
        "binary": {
            "path": str(bin_path),
            "sha256": sha256_file(bin_path) if bin_path.exists() else None,
        },
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "inventory_digest": header.get("inventory_digest"),
            "counts": header.get("counts"),
            "pins": header.get("pins"),
        },
        "limits": asdict(limits),
        "enforcement": {
            "mode": "live",
            "mechanism": (
                "parent polls /proc/<pid>/status VmHWM (peak RSS), the growing artifact size, "
                "and free disk while the child runs; SIGKILL on breach"
            ),
            "phases": ["export", "readback"],
            "rss_enforced": "per-record rss_enforced flag; true only when /proc sampling succeeded",
            "not_used": ["RLIMIT_RSS (no-op on Linux)", "RLIMIT_AS (virtual address, not RSS)"],
            "output_budget_live": (
                "polls the final artifact and its <path>.tmp sibling each interval, then re-checks "
                "after child exit before accepted/readback; bounded overshoot is one poll interval "
                "of growth during the run, and the post-exit check bounds the final artifact exactly"
            ),
            "atomic_publish_aware": "sibling <path>.tmp is guarded and cleaned up; original rc kept separate from the budget verdict",
            "disk_budget_live": "free disk polled (>=0.2s) against abort_free_disk_bytes",
        },
        "sample": {
            "seed": seed,
            "strata": strata,
            "count": len(sample),
            "total_sample_bytes": sum(item.bytes for item in sample),
            "criteria": "size deciles by rank (seeded picks) + largest tail; read-back complex classes computed post-measure",
            "justification": (
                "Bounded deterministic sample: per-decile seeded picks cover the size "
                "distribution, the largest tail drives the wall/RSS/disk bound. Structural "
                "classes are derived post-measure from ready metadata (read-back counts), "
                "not from a new parser."
            ),
        },
        "run": {
            "status": run["run_status"],
            "elapsed_s": run["elapsed_s"],
            "disk_before": run["disk_before"],
            "disk_after": run["disk_after"],
            "peak_tmp_artifact_bytes": run["peak_tmp_artifact_bytes"],
            "transient_output_bytes": run["transient_output_bytes"],
            "persistent_layer_bytes": 0,
            "disk_note": (
                "Each artifact is written to tmp_dir and deleted immediately after read-back; "
                "no persistent cleaned layer remains. Disk accounting is statvfs before/after."
            ),
        },
        "aggregates": aggregate(records),
        "complex_classes": complex_classes(records),
        "structural_coverage": {
            "measured": [
                "export wall time and peak RSS (per file)",
                "read-back wall time (per file)",
                "output artifact bytes and output/input ratio",
                "read-back text_chars (largest text)",
                "read-back records/segments density per input KiB",
                "read-back references",
                "input bytes (manifest)",
            ],
            "not_measured": [
                "per-document nesting depth",
                "per-document table count/density",
            ],
            "note": (
                "No product surface exposes per-document depth or table counts without new XML "
                "parsing, which this harness deliberately does not add. Depth/table heaviness is "
                "represented by read-back segment/record density and input size."
            ),
        },
        "readback_disclaimer": (
            "Read-back (cleaned-project read) is a counts-only re-read of the artifact produced by "
            "this same process. It is NOT an independent substrate verify; substrate independence "
            "is cleaned-project verify against the frozen source package and is out of scope here."
        ),
        "records": records,
        "non_claims": [
            "Not a full-corpus run: a bounded stratified sample only.",
            "Not semantic acceptance: resource measurement only.",
            "Read-back is not an independent substrate verify.",
            "No raw decoded text in evidence; paths/counts/hashes only.",
            "Feasibility conclusions from this sample are conditional extrapolations (T03).",
        ],
    }


# ------------------------------------------------------------------- main #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=Path(DEFAULT_CORPUS_ROOT))
    parser.add_argument("--bin", type=Path, default=DEFAULT_BIN, dest="bin_path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=22302)
    parser.add_argument("--per-decile", type=int, default=25)
    parser.add_argument("--tail-n", type=int, default=50)
    parser.add_argument("--export-wall-s", type=float, default=Limits.export_wall_s)
    parser.add_argument("--readback-wall-s", type=float, default=Limits.readback_wall_s)
    parser.add_argument("--peak-rss-kb", type=int, default=Limits.peak_rss_kb)
    parser.add_argument("--min-free-disk-bytes", type=int, default=Limits.min_free_disk_bytes)
    parser.add_argument("--abort-free-disk-bytes", type=int, default=Limits.abort_free_disk_bytes)
    parser.add_argument(
        "--max-single-artifact-bytes", type=int, default=Limits.max_single_artifact_bytes
    )
    parser.add_argument("--total-budget-wall-s", type=float, default=Limits.total_budget_wall_s)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not args.manifest.is_file():
        print(f"manifest missing: {args.manifest}", file=sys.stderr)
        return 2
    if not args.bin_path.exists():
        print(f"binary missing: {args.bin_path}", file=sys.stderr)
        return 2

    header, entries = parse_manifest(args.manifest)
    sample, strata = build_sample(
        entries, seed=args.seed, per_decile=args.per_decile, tail_n=args.tail_n
    )
    limits = Limits(
        export_wall_s=args.export_wall_s,
        readback_wall_s=args.readback_wall_s,
        peak_rss_kb=args.peak_rss_kb,
        min_free_disk_bytes=args.min_free_disk_bytes,
        abort_free_disk_bytes=args.abort_free_disk_bytes,
        max_single_artifact_bytes=args.max_single_artifact_bytes,
        total_budget_wall_s=args.total_budget_wall_s,
    )

    def handler(signum: int, _frame: Any) -> None:
        raise Interrupted(signum)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    import tempfile

    print(
        f"m223-s02-probe: sampled={len(sample)} seed={args.seed} "
        f"export_wall_s={limits.export_wall_s} peak_rss_kb={limits.peak_rss_kb}",
        file=sys.stderr,
    )

    with tempfile.TemporaryDirectory(prefix="m223-s02-probe-") as tmp_name:
        tmp_dir = Path(tmp_name)
        state: dict[str, Any] = {"records": [], "run_status": "complete"}

        def on_record(records: list[dict[str, Any]]) -> None:
            state["records"] = records
            record = records[-1]
            wall = record["export"]["wall_s"] if record["export"] else "na"
            print(
                f"m223-s02-probe: {len(records)}/{len(sample)} outcome={record['outcome']} wall_s={wall}",
                file=sys.stderr,
            )

        run_result = None
        exit_code = 0
        try:
            run_result = run_probe(
                manifest_path=args.manifest,
                corpus_root=args.corpus_root,
                bin_path=args.bin_path,
                sample=sample,
                limits=limits,
                tmp_dir=tmp_dir,
                on_record=on_record,
            )
        except Interrupted as interrupted:
            exit_code = 128 + interrupted.signum
            run_result = {
                "records": state["records"],
                "run_status": "interrupted",
                "disk_before": disk_snapshot(tmp_dir),
                "disk_after": disk_snapshot(tmp_dir),
                "peak_tmp_artifact_bytes": 0,
                "transient_output_bytes": 0,
                "elapsed_s": 0.0,
            }
        payload = build_payload(
            header=header,
            manifest_path=args.manifest,
            sample=sample,
            strata=strata,
            limits=limits,
            run=run_result,
            seed=args.seed,
            bin_path=args.bin_path,
            corpus_root=args.corpus_root,
        )
        write_evidence(payload, args.out)
        print(
            f"m223-s02-probe: status={run_result['run_status']} "
            f"records={len(run_result['records'])} out={args.out}",
            file=sys.stderr,
        )
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
