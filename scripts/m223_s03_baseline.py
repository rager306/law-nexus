#!/usr/bin/env python3
"""M223/S03 resumable corpus baseline runner (process harness).

This harness runs the *cleaned/admission* path over every entry of the pinned
S02 corpus manifest and gives each entry **exactly one terminal outcome**:

* ``accepted`` — the product export exited ``0`` **and** the counts-only
  read-back of the produced artifact succeeded (artifact identity recorded);
* ``refused`` — a typed product refusal (exit ``5``) whose closed stderr reason
  token is recognised;
* ``incomplete`` — a harness class (timeout / signal / resource stop / usage /
  unwritable / verify failed / exec error / unknown exit / not run / input or
  binary drift); an ``incomplete`` entry is never a success and is never
  reported as ``accepted``.

Every receipt is bound to three hash families (§8.6) plus the executable
identity:

* **input** — per-entry ``sha256`` + ``bytes`` from the manifest *and* the
  bytes actually observed on disk before export (and re-verified after);
* **code** — the aggregate source revision from
  ``scripts/m204_s08_source_revision.mjs`` (never a guessed HEAD);
* **rules** — the closed ``profile`` / ``contract_version`` / ``completion``
  tuple of the cleaned-projection contract, confirmed by the product read-back;
* **binary** — the sha256 of the ``cleaned-project`` executable actually run.

A receipt is *current* only when all four pin the live values; otherwise it is
stale and the entry is recomputed.  A full run is ``complete`` only when every
manifest entry has a current terminal receipt — a partial run is never reported
as full (``partial_is_not_full`` is always ``true``).

Resource discipline is inherited verbatim from ``scripts/m223_s02_probe.py``
(``measure_subprocess`` live-polls ``/proc/<pid>/status`` VmHWM, the growing
artifact *and* its ``.tmp`` sibling, and free disk, SIGKILLing on breach) — this
module imports that core rather than forking it.

No raw decoded text ever reaches a receipt, the run report, a diagnostic or
stdout/stderr: only paths, counts, sizes and hashes.  The counts-only read-back
is explicitly **not** an independent substrate verification.

Reads stay under the gitignored ``target/m223-s03/`` scratch path; the ledger and
scratch are not tracked, because a tracked ledger under
``prd/migration/rust-evidence/`` would shift the aggregate code hash and void
the binding on resume.  Publication of a finished ledger/report is a separate,
deliberate step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:  # pragma: no cover - exercised implicitly by every import site
    import m223_s02_probe as probe
except ImportError:  # pragma: no cover - fallback for exotic import roots
    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "m223_s02_probe", _SCRIPTS_DIR / "m223_s02_probe.py"
    )
    if _spec is None or _spec.loader is None:  # pragma: no cover
        raise
    probe = importlib.util.module_from_spec(_spec)
    sys.modules.setdefault("m223_s02_probe", probe)
    _spec.loader.exec_module(probe)

# ------------------------------------------------------------------ paths #

RECEIPT_SCHEMA = "m223-s03-baseline-receipt/v1"
RUN_SCHEMA = "m223-s03-baseline-run/v1"

MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
DECISION_SCHEMA = "m223-s02-corpus-feasibility/v1"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_DECISION = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-feasibility.json"
DEFAULT_CORPUS_ROOT = Path("consru_export/consru_export/exports")
DEFAULT_BIN = ROOT / "target/release/cleaned-project"
DEFAULT_SCRATCH = ROOT / "target/m223-s03"
SOURCE_REVISION_SCRIPT = _SCRIPTS_DIR / "m204_s08_source_revision.mjs"

# ----------------------------------------------------------- vocabularies #

#: Terminal outcomes: the run may skip a *current* receipt of one of these.
TERMINAL_OUTCOMES = ("accepted", "refused")
#: Closed outcome vocabulary.
ALL_OUTCOMES = ("accepted", "refused", "incomplete")

#: The decision verdict this runner is authorised to execute.
EXPECTED_DECISION_VERDICT = "full-stream-discard"

#: Closed rules tuple of the cleaned-projection contract.
RULES_PROFILE = "cleaned_projection_wordml/v1"
RULES_CONTRACT_VERSION = 1
RULES_COMPLETION = "complete"

#: Reader transfer-gate source classes that are *refusals* (never accepted).
READER_SOURCE_REFUSALS = frozenset(
    {"source_not_wordml", "unsupported_schema", "namespace_absent", "empty_source"}
)

#: Closed ``WireErrorKind`` tokens (cleaned_wire.rs).
WIRE_ERROR_KINDS = frozenset(
    {
        "schema_mismatch",
        "version_mismatch",
        "line_bytes_limit",
        "records_limit",
        "text_bytes_limit",
        "text_loss",
        "fragment_missing",
        "provenance_mismatch",
        "completion_marker_invalid",
        "missing_trailing_lf",
        "carriage_return",
        "empty_line",
        "missing_manifest",
        "misordered_manifest",
        "missing_policies",
        "misordered_policies",
        "missing_footer",
        "misordered_footer",
        "trailing_record_after_footer",
        "unknown_kind",
        "hash_shape_invalid",
        "contract_field_invalid",
        "hash_mismatch",
        "record_group_order",
        "record_field_invalid",
        "write_failed",
    }
)

#: Closed source-package ``ErrorKind`` tokens (source_package.rs).
PACKAGE_ERROR_KINDS = frozenset(
    {
        "input_too_large",
        "package_too_large",
        "line_too_long",
        "non_utf8_input",
        "non_utf8_package",
        "unsupported_encoding",
        "dtd_forbidden",
        "malformed_xml",
        "multiple_roots",
        "no_root",
        "unclosed_elements",
        "document_level_text",
        "unbound_prefix",
        "duplicate_attribute",
        "attribute_count_exceeded",
        "invalid_xml_space",
        "depth_exceeded",
        "node_cap_exceeded",
        "text_fragment_cap_exceeded",
        "text_byte_cap_exceeded",
        "record_cap_exceeded",
        "missing_trailing_lf",
        "carriage_return_forbidden",
        "empty_line",
        "empty_package",
        "missing_footer",
        "misordered_footer",
        "missing_manifest",
        "misordered_manifest",
        "json_syntax",
        "duplicate_json_key",
        "type_mismatch",
        "unknown_kind",
        "schema_mismatch",
        "version_unsupported",
        "source_hash_mismatch",
        "hash_missing",
        "hash_malformed",
        "records_seal_mismatch",
        "manifest_hash_mismatch",
        "count_mismatch",
        "duplicate_record_id",
        "section_order_mismatch",
        "root_count",
        "parent_dangling",
        "depth_mismatch",
        "child_index_mismatch",
        "element_order_mismatch",
        "text_owner_dangling",
        "text_slot_duplicate",
        "text_ref_dangling",
        "text_ref_mismatch",
        "text_order_mismatch",
        "text_length_mismatch",
        "invalid_xml_char",
        "limit_exceeded",
        "serialization",
        "io",
    }
)

#: Closed ``io_error_token`` values for ``cannot read --from-xml``.
IO_TOKENS = frozenset({"not_found", "permission_denied", "invalid_data", "io_error"})

#: Incomplete harness classes.  ``input_drift`` / ``binary_drift`` are the
#: fail-closed classes for a corpus file or executable that changed so the
#: pinned binding no longer holds; ``not_run`` marks an entry an interrupted or
#: budget-stopped attempt did not reach.
INCOMPLETE_CLASSES = frozenset(
    {
        "timeout",
        "signal",
        "rss_limit_exceeded",
        "output_limit_exceeded",
        "disk_limit_exceeded",
        "usage_error",
        "out_unwritable",
        "artifact_verify_failed",
        "exec_error",
        "unknown_exit",
        "harness_error",
        "not_run",
        "input_drift",
        "binary_drift",
    }
)

#: Map a ``probe.classify_export`` verdict to an incomplete class.
EXPORT_OUTCOME_TO_INCOMPLETE = {
    "timeout": "timeout",
    "rss_limit_exceeded": "rss_limit_exceeded",
    "output_limit_exceeded": "output_limit_exceeded",
    "disk_limit_exceeded": "disk_limit_exceeded",
    "signaled": "signal",
    "usage_error": "usage_error",
    "out_unwritable": "out_unwritable",
    "artifact_verify_failed": "artifact_verify_failed",
    "exec_error": "exec_error",
    "unknown_exit": "unknown_exit",
    "harness_error": "harness_error",
    "not_run": "not_run",
}

#: Map a ``probe.classify_readback`` verdict to an incomplete class.
READBACK_OUTCOME_TO_INCOMPLETE = {
    "readback_failed": "artifact_verify_failed",
    "readback_usage_error": "usage_error",
    "readback_timeout": "timeout",
    "readback_signaled": "signal",
    "readback_rss_exceeded": "rss_limit_exceeded",
    "readback_disk_exceeded": "disk_limit_exceeded",
    "readback_error": "harness_error",
}

#: Run-level status vocabulary.
RUN_STATUSES = (
    "complete",
    "incomplete",
    "budget_exhausted",
    "disk_guard_stopped",
    "interrupted",
    "dry_run",
    "preflight_failed",
)

NON_CLAIMS = (
    "Not an authenticity or legal-completeness claim; R1000 stays active/unclosed.",
    "Read-back (cleaned-project read) is a counts-only re-read by this same "
    "process; it is NOT an independent substrate verification.",
    "A partial run is never reported as full (partial_is_not_full=true).",
    "No raw decoded text reaches receipts, the report, diagnostics or stdout.",
    "Feasibility projections come from S02; this runner records baseline outcomes only.",
)

REFUSAL_PATTERNS: tuple[tuple[str, re.Pattern[str], frozenset[str]], ...] = (
    ("source", re.compile(r"^cleaned-project: source refused: (\S+)$"), READER_SOURCE_REFUSALS),
    ("wire", re.compile(r"^cleaned-project: projection failed: (\S+)$"), WIRE_ERROR_KINDS),
    ("wire", re.compile(r"^cleaned-project: export failed: (\S+)$"), WIRE_ERROR_KINDS),
    (
        "package",
        re.compile(r"^cleaned-project: capture failed: source package error: ([\w]+)"),
        PACKAGE_ERROR_KINDS,
    ),
    ("io", re.compile(r"^cleaned-project: cannot read --from-xml: (\S+)$"), IO_TOKENS),
)

# ------------------------------------------------------------- exit codes #

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PREFLIGHT = 6
EXIT_VERIFY_FAILED = 7
EXIT_NOT_COMPLETE = 10
EXIT_DISK_GUARD = 11
EXIT_INCOMPLETE = 12


class HarnessError(RuntimeError):
    """A fail-closed harness-level error (bad pin, unknown token, bad input)."""


# -------------------------------------------------------------- binding #


def rules_digest() -> str:
    """Canonical sha256 over the closed cleaned-projection rules tuple."""
    canonical = (
        f"profile={RULES_PROFILE}\n"
        f"contract_version={RULES_CONTRACT_VERSION}\n"
        f"completion={RULES_COMPLETION}\n"
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Binding:
    """Run-level identity binding: code revision, rules digest, binary sha256."""

    code_revision: str
    rules_digest: str
    binary_sha256: str
    binary_path: str

    def key(self) -> tuple[str, str, str]:
        return (self.code_revision, self.rules_digest, self.binary_sha256)

    def as_dict(self) -> dict[str, str]:
        return {
            "code_revision": self.code_revision,
            "rules_digest": self.rules_digest,
            "binary_sha256": self.binary_sha256,
            "binary_path": self.binary_path,
        }


def receipt_binding_key(receipt: dict[str, Any]) -> tuple[str, str, str]:
    return (
        receipt["code_revision"],
        receipt["rules_digest"],
        receipt["binary_sha256"],
    )


def source_revision(*, timeout_s: float = 180.0) -> str:
    """Aggregate code source revision from the live engine hasher replica.

    Never guesses a HEAD; the script imports the GSD engine hasher and fails
    closed when the shape is not ``sha256:<64 lowercase hex>``.
    """
    try:
        completed = subprocess.run(
            ["node", str(SOURCE_REVISION_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise HarnessError(f"source revision computation failed: {type(error).__name__}") from error
    if completed.returncode != 0:
        raise HarnessError(f"source revision runner exited {completed.returncode}")
    line = completed.stdout.strip().splitlines()
    if not line:
        raise HarnessError("source revision runner produced no output")
    try:
        payload = json.loads(line[-1])
    except json.JSONDecodeError as error:
        raise HarnessError("source revision runner produced non-JSON") from error
    revision = payload.get("source_revision") if isinstance(payload, dict) else None
    if not payload.get("ok") or not isinstance(revision, str):
        raise HarnessError("source revision runner reported not-ok")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", revision):
        raise HarnessError("source revision has an unexpected shape")
    return revision


def compute_binding(
    bin_path: Path,
    *,
    code_revision: str | None = None,
    hash_file: Callable[[Path], str] = probe.sha256_file,
) -> Binding:
    """Bind run identity to the actual binary sha256 and the code revision.

    ``code_revision`` is a test/ops seam only; when omitted it is computed from
    the live engine hasher, never guessed.  A missing binary is a fail-closed
    harness error.
    """
    if not bin_path.is_file():
        raise HarnessError(f"cleaned-project binary missing: {bin_path}")
    revision = code_revision if code_revision is not None else source_revision()
    return Binding(
        code_revision=revision,
        rules_digest=rules_digest(),
        binary_sha256=hash_file(bin_path),
        binary_path=str(bin_path),
    )


# ----------------------------------------------------------------- input #


def _is_safe_relative(relative_path: str) -> bool:
    if not relative_path or relative_path.startswith("/") or relative_path.startswith("\\"):
        return False
    pure = Path(relative_path)
    if pure.is_absolute():
        return False
    return not any(part in ("", "..") for part in pure.parts)


def load_decision(path: Path) -> dict[str, Any]:
    """Load and fail-closed validate the S02 feasibility decision."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError(f"decision unreadable: {type(error).__name__}") from error
    if not isinstance(payload, dict):
        raise HarnessError("decision is not an object")
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise HarnessError("decision.verdict block is absent")
    verdict = decision.get("verdict")
    if verdict != EXPECTED_DECISION_VERDICT:
        raise HarnessError(f"unknown decision verdict: {verdict!r}")
    stop = decision.get("stop_thresholds")
    if not isinstance(stop, dict):
        raise HarnessError("decision.stop_thresholds is absent")
    for key in ("wall_s", "peak_rss_kb", "single_artifact_bytes"):
        if not isinstance(stop.get(key), (int, float)):
            raise HarnessError(f"decision.stop_thresholds.{key} is absent")
    preflight = decision.get("preflight_requirements")
    if not isinstance(preflight, list) or not preflight:
        raise HarnessError("decision.preflight_requirements is absent")
    authorization = decision.get("authorization")
    if not isinstance(authorization, dict) or authorization.get("partial_is_not_full") is not True:
        raise HarnessError("decision.authorization.partial_is_not_full is not true")
    if not isinstance(payload.get("inputs"), dict):
        raise HarnessError("decision.inputs is absent")
    return payload


def load_manifest(
    path: Path,
    *,
    decision: dict[str, Any] | None = None,
    verify_pins: bool = True,
    hash_file: Callable[[Path], str] = probe.sha256_file,
) -> tuple[dict[str, Any], list[probe.Entry]]:
    """Read the pinned manifest and fail-closed validate safety and pins.

    * every ``relative_path`` must be relative and free of ``..``;
    * no duplicate entry paths;
    * when ``decision`` is supplied, the manifest file sha256, inventory digest
      and counts must match the pinned S02 authority.
    """
    try:
        header, entries = probe.parse_manifest(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HarnessError(f"manifest unreadable: {type(error).__name__}") from error
    if header.get("schema") != MANIFEST_SCHEMA:
        raise HarnessError(f"unexpected manifest schema: {header.get('schema')!r}")

    seen: set[str] = set()
    for entry in entries:
        if not _is_safe_relative(entry.relative_path):
            raise HarnessError(f"unsafe manifest path: {entry.relative_path!r}")
        if entry.relative_path in seen:
            raise HarnessError(f"duplicate manifest path: {entry.relative_path!r}")
        seen.add(entry.relative_path)

    if verify_pins and decision is not None:
        pinned = decision["inputs"]["manifest"]
        actual_sha = hash_file(path)
        if pinned.get("sha256") != actual_sha:
            raise HarnessError("manifest sha256 does not match the pinned decision")
        if pinned.get("inventory_digest") != header.get("inventory_digest"):
            raise HarnessError("manifest inventory_digest does not match the pinned decision")
        counts = pinned.get("counts") or {}
        header_counts = header.get("counts") or {}
        for key in ("entries", "total_bytes", "max_bytes"):
            if counts.get(key) != header_counts.get(key):
                raise HarnessError(f"manifest counts.{key} does not match the pinned decision")
    return header, entries


def hash_and_size(path: Path, hash_file: Callable[[Path], str]) -> tuple[str | None, int]:
    """Actual sha256 + byte size of a source file; ``(None, 0)`` when unreadable."""
    try:
        return hash_file(path), path.stat().st_size
    except OSError:
        return None, 0


# --------------------------------------------------------------- receipts #


def _base_receipt(
    entry: probe.Entry,
    binding: Binding,
    attempt: int,
    recorded_at: float,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "attempt": attempt,
        "relative_path": entry.relative_path,
        "input_sha256": entry.sha256,
        "input_bytes": entry.bytes,
        "actual_sha256": None,
        "actual_bytes": None,
        "code_revision": binding.code_revision,
        "rules_digest": binding.rules_digest,
        "binary_sha256": binding.binary_sha256,
        "outcome": None,
        "outcome_class": None,
        "reason_family": None,
        "reason_token": None,
        "artifact_sha256": None,
        "artifact_bytes": None,
        "readback": None,
        "wall_s": None,
        "peak_rss_kb": None,
        "tmp_removed": True,
        "input_verified_after": False,
        "recorded_at": recorded_at,
        "note": None,
    }


def _finish(
    receipt: dict[str, Any],
    outcome: str,
    outcome_class: str,
    *,
    reason_family: str | None = None,
    reason_token: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if outcome not in ALL_OUTCOMES:
        raise HarnessError(f"unknown outcome: {outcome!r}")
    receipt["outcome"] = outcome
    receipt["outcome_class"] = outcome_class
    receipt["reason_family"] = reason_family
    receipt["reason_token"] = reason_token
    if note is not None:
        receipt["note"] = note
    return receipt


def parse_refusal(stderr_text: str) -> tuple[str, str, str] | None:
    """Closed parse of a product refusal stderr line.

    Returns ``(outcome_class, reason_family, reason_token)`` for a recognised
    refusal, or ``None`` for an unknown token — the caller then fails closed to
    ``harness_error`` and never ``accepted``.
    """
    for raw in stderr_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        for family, pattern, allowed in REFUSAL_PATTERNS:
            match = pattern.match(line)
            if match is None:
                continue
            token = match.group(1)
            if token not in allowed:
                return None
            return (f"{family}:{token}", family, token)
    return None


class ReceiptLog:
    """Append-only, crash-safe JSONL receipt log.

    Each receipt is one JSON line flushed and fsynced immediately, so an
    interruption keeps every completed receipt.  A truncated final line (a
    crash mid-write) is ignored on read; a corrupt *interior* line is a
    fail-closed harness error.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        receipts: list[dict[str, Any]] = []
        raw_lines = self.path.read_text(encoding="utf-8").splitlines()
        for index, raw in enumerate(raw_lines):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as error:
                if index == len(raw_lines) - 1:
                    break  # torn trailing line from a crash: drop it
                raise HarnessError("receipt ledger has a corrupt interior line") from error
            if not isinstance(record, dict) or record.get("schema") != RECEIPT_SCHEMA:
                raise HarnessError("receipt ledger holds a foreign record")
            receipts.append(record)
        return receipts

    def append(self, receipt: dict[str, Any]) -> None:
        line = json.dumps(receipt, ensure_ascii=True, sort_keys=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def latest_by_path(receipts: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Last receipt wins for each ``relative_path``."""
    latest: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        latest[receipt["relative_path"]] = receipt
    return latest


def receipt_is_current(
    receipt: dict[str, Any],
    entry: probe.Entry,
    binding: Binding,
    actual_sha256: str | None,
    actual_bytes: int,
) -> bool:
    """A receipt is current only when all four pins match the live values."""
    return (
        receipt["input_sha256"] == entry.sha256 == actual_sha256
        and receipt["input_bytes"] == entry.bytes == actual_bytes
        and receipt["code_revision"] == binding.code_revision
        and receipt["rules_digest"] == binding.rules_digest
        and receipt["binary_sha256"] == binding.binary_sha256
        and receipt["outcome"] in TERMINAL_OUTCOMES
    )


# --------------------------------------------------------------- process #


def _artifact_path(scratch_dir: Path, relative_path: str) -> Path:
    token = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
    return scratch_dir / f"artifact-{token}.jsonl"


def process_entry(
    entry: probe.Entry,
    *,
    corpus_root: Path,
    bin_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    attempt: int,
    verify_input_after: bool = True,
    hash_file: Callable[[Path], str] = probe.sha256_file,
    measure: Callable[..., dict[str, Any]] = probe.measure_subprocess,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Run one entry's export + read-back and return a closed receipt.

    Fail-closed: an unreadable or drifted source, an unrecognised refusal token,
    a resource breach or a read-back failure never yields ``accepted``.
    """
    receipt = _base_receipt(entry, binding, attempt, now())
    source = corpus_root / entry.relative_path
    artifact = _artifact_path(scratch_dir, entry.relative_path)
    export_stdout = scratch_dir / "export.stdout"
    export_stderr = scratch_dir / "export.stderr"
    readback_stdout = scratch_dir / "readback.stdout"
    readback_stderr = scratch_dir / "readback.stderr"

    scratch_dir.mkdir(parents=True, exist_ok=True)
    try:
        actual_sha256, actual_bytes = hash_and_size(source, hash_file)
        receipt["actual_sha256"] = actual_sha256
        receipt["actual_bytes"] = actual_bytes
        if actual_sha256 is None:
            return _finish(receipt, "incomplete", "harness_error", note="input unreadable")
        if actual_sha256 != entry.sha256 or actual_bytes != entry.bytes:
            return _finish(
                receipt, "incomplete", "input_drift", note="source bytes differ from manifest pin"
            )

        try:
            export_result = measure(
                [
                    str(bin_path),
                    "export",
                    "--from-xml",
                    str(source),
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
                disk_free_probe=lambda: probe.disk_snapshot(scratch_dir)["free_bytes"],
                disk_floor_bytes=limits.abort_free_disk_bytes,
            )
        except OSError as error:
            return _finish(
                receipt,
                "incomplete",
                "harness_error",
                note=f"export spawn failed: {type(error).__name__}",
            )

        receipt["wall_s"] = export_result["wall_s"]
        receipt["peak_rss_kb"] = export_result["peak_rss_kb"]
        outcome = probe.classify_export(export_result, limits)

        if outcome == "typed_refusal":
            stderr_text = (
                export_stderr.read_text(encoding="utf-8", errors="replace")
                if export_stderr.exists()
                else ""
            )
            parsed = parse_refusal(stderr_text)
            if parsed is None:
                return _finish(
                    receipt,
                    "incomplete",
                    "harness_error",
                    note="unrecognized refusal token",
                )
            outcome_class, family, token = parsed
            return _finish(
                receipt, "refused", outcome_class, reason_family=family, reason_token=token
            )

        if outcome != "accepted":
            return _finish(
                receipt,
                "incomplete",
                EXPORT_OUTCOME_TO_INCOMPLETE.get(outcome, "harness_error"),
                note=f"export classified {outcome}",
            )

        if not artifact.exists():
            return _finish(receipt, "incomplete", "harness_error", note="artifact missing")
        artifact_sha256 = hash_file(artifact)
        artifact_bytes = artifact.stat().st_size

        try:
            readback_result = measure(
                [str(bin_path), "read", "--artifact", str(artifact)],
                timeout_s=limits.readback_wall_s,
                cwd=ROOT,
                stdout_path=readback_stdout,
                stderr_path=readback_stderr,
                rss_limit_kb=limits.peak_rss_kb,
                disk_free_probe=lambda: probe.disk_snapshot(scratch_dir)["free_bytes"],
                disk_floor_bytes=limits.abort_free_disk_bytes,
            )
        except OSError as error:
            return _finish(
                receipt,
                "incomplete",
                "harness_error",
                note=f"read-back spawn failed: {type(error).__name__}",
            )
        readback_outcome = probe.classify_readback(readback_result)
        if readback_outcome != "readback_ok":
            return _finish(
                receipt,
                "incomplete",
                READBACK_OUTCOME_TO_INCOMPLETE.get(readback_outcome, "harness_error"),
                note=f"read-back classified {readback_outcome}",
            )

        parsed_counts = probe.parse_readback_counts(
            readback_stdout.read_text(encoding="utf-8", errors="replace")
        )
        declared = parsed_counts["declared"]
        if (
            declared.get("contract_version") != str(RULES_CONTRACT_VERSION)
            or declared.get("completion") != RULES_COMPLETION
        ):
            return _finish(
                receipt,
                "incomplete",
                "harness_error",
                note="declared rules tuple not confirmed by product read-back",
            )

        if verify_input_after:
            after_sha256, after_bytes = hash_and_size(source, hash_file)
            if after_sha256 != actual_sha256 or after_bytes != actual_bytes:
                return _finish(
                    receipt,
                    "incomplete",
                    "input_drift",
                    note="source changed during processing",
                )
        receipt["input_verified_after"] = bool(verify_input_after)
        receipt["artifact_sha256"] = artifact_sha256
        receipt["artifact_bytes"] = artifact_bytes
        receipt["readback"] = {
            "outcome": "readback_ok",
            "counts": parsed_counts["counts"],
            "declared": declared,
            "is_substrate_verify": False,
        }
        return _finish(receipt, "accepted", "accepted")
    finally:
        removed = True
        for leftover in (
            artifact,
            Path(str(artifact) + ".tmp"),
            export_stdout,
            export_stderr,
            readback_stdout,
            readback_stderr,
        ):
            if leftover.exists():
                try:
                    leftover.unlink()
                except OSError:
                    removed = False
        receipt["tmp_removed"] = removed


# ------------------------------------------------------------------- run #


def _empty_counts() -> dict[str, int]:
    return {"accepted": 0, "refused": 0, "incomplete": 0}


def _tally(counts: dict[str, int], receipt: dict[str, Any]) -> None:
    outcome = receipt["outcome"]
    counts[outcome] = counts.get(outcome, 0) + 1


def summarize_receipts(
    entries: Sequence[probe.Entry],
    latest: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Coverage summary over the manifest: terminal/incomplete/remaining."""
    counts = _empty_counts()
    refused_by_class: dict[str, int] = {}
    incomplete_by_class: dict[str, int] = {}
    for entry in entries:
        receipt = latest.get(entry.relative_path)
        if receipt is None:
            continue
        _tally(counts, receipt)
        klass = receipt["outcome_class"]
        if receipt["outcome"] == "refused":
            refused_by_class[klass] = refused_by_class.get(klass, 0) + 1
        elif receipt["outcome"] == "incomplete":
            incomplete_by_class[klass] = incomplete_by_class.get(klass, 0) + 1
    present = sum(counts.values())
    terminal = counts["accepted"] + counts["refused"]
    return {
        "entries": len(entries),
        "present": present,
        "remaining": len(entries) - present,
        "accepted": counts["accepted"],
        "refused": counts["refused"],
        "incomplete": counts["incomplete"],
        "terminal": terminal,
        "refused_by_class": dict(sorted(refused_by_class.items())),
        "incomplete_by_class": dict(sorted(incomplete_by_class.items())),
    }


def run_baseline(
    *,
    entries: Sequence[probe.Entry],
    corpus_root: Path,
    bin_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    receipts_path: Path,
    attempt_wall_s: float,
    resume: bool = True,
    dry_run: bool = False,
    max_entries: int | None = None,
    verify_input_after: bool = True,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], float] = time.time,
    hash_file: Callable[[Path], str] = probe.sha256_file,
    measure: Callable[..., dict[str, Any]] = probe.measure_subprocess,
    on_receipt: Callable[[dict[str, Any]], None] | None = None,
    status_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run one resumable attempt over the manifest entries.

    Returns a state dict; the caller composes/writes the run report.  Entries
    with a *current* terminal receipt are skipped (``skipped``), stale or
    incomplete entries are recomputed/retried.  The attempt stops as
    ``budget_exhausted`` when ``attempt_wall_s`` elapses, or
    ``disk_guard_stopped`` when free disk drops below the abort floor.
    """
    scratch_dir.mkdir(parents=True, exist_ok=True)
    log = ReceiptLog(receipts_path)
    existing = log.read() if resume else []
    latest = latest_by_path(existing)
    prior_attempts = [record["attempt"] for record in existing]
    attempt = (max(prior_attempts) + 1) if prior_attempts else 1

    disk_before = probe.disk_snapshot(scratch_dir)
    started = clock()
    state: dict[str, Any] = {
        "status": "complete",
        "attempt": attempt,
        "binding": binding.as_dict(),
        "skipped": 0,
        "processed": 0,
        "written_receipts": 0,
        "existing_receipts": len(existing),
        "disk_before": disk_before,
        "disk_after": disk_before,
        "counts": _empty_counts(),
        "summary": {},
        "planned": 0,
        "stopped_signal": None,
        "used_entries": 0,
    }

    def emit(receipt: dict[str, Any]) -> None:
        if dry_run:
            return
        log.append(receipt)
        latest[receipt["relative_path"]] = receipt
        state["written_receipts"] += 1
        _tally(state["counts"], receipt)
        if on_receipt is not None:
            on_receipt(receipt)

    processed_limit = 0
    try:
        for entry in entries:
            if attempt_wall_s > 0 and (clock() - started) >= attempt_wall_s:
                state["status"] = "budget_exhausted"
                break
            if max_entries is not None and processed_limit >= max_entries:
                state["status"] = "budget_exhausted"
                break
            free = probe.disk_snapshot(scratch_dir)["free_bytes"]
            if free < limits.abort_free_disk_bytes:
                state["status"] = "disk_guard_stopped"
                break

            actual_sha256, actual_bytes = hash_and_size(
                corpus_root / entry.relative_path, hash_file
            )
            previous = latest.get(entry.relative_path)
            if (
                resume
                and previous is not None
                and receipt_is_current(previous, entry, binding, actual_sha256, actual_bytes)
            ):
                state["skipped"] += 1
                state["used_entries"] += 1
                if status_cb is not None:
                    status_cb(f"skip {entry.relative_path}")
                continue

            if dry_run:
                state["planned"] += 1
                continue

            try:
                receipt = process_entry(
                    entry,
                    corpus_root=corpus_root,
                    bin_path=bin_path,
                    binding=binding,
                    limits=limits,
                    scratch_dir=scratch_dir,
                    attempt=attempt,
                    verify_input_after=verify_input_after,
                    hash_file=hash_file,
                    measure=measure,
                    now=now,
                )
            except probe.Interrupted as interrupted:
                # The in-flight entry never completed: record it explicitly as
                # incomplete/not_run so the interruption is not silent.
                aborted = _base_receipt(entry, binding, attempt, now())
                aborted["actual_sha256"] = actual_sha256
                aborted["actual_bytes"] = actual_bytes
                emit(_finish(aborted, "incomplete", "not_run", note="attempt interrupted"))
                state["status"] = "interrupted"
                state["stopped_signal"] = interrupted.signum
                state["disk_after"] = probe.disk_snapshot(scratch_dir)
                state["summary"] = summarize_receipts(entries, latest)
                raise
            emit(receipt)
            processed_limit += 1
    finally:
        pass

    if state["status"] == "complete":
        summary = summarize_receipts(entries, latest)
        state["summary"] = summary
        if (
            summary["remaining"] > 0
            or summary["incomplete"] > 0
            or summary["terminal"] != summary["entries"]
        ):
            state["status"] = "incomplete"
    else:
        state["summary"] = summarize_receipts(entries, latest)
    state["disk_after"] = probe.disk_snapshot(scratch_dir)
    # Fail closed if the executable changed under the attempt: every receipt
    # records the attempt-start binary sha256, so a mid-attempt swap must not be
    # reported as a full run. Detected once per attempt, not per entry.
    state["binary_drift"] = False
    if not dry_run and state["status"] == "complete":
        if hash_file(bin_path) != binding.binary_sha256:
            state["binary_drift"] = True
            state["status"] = "incomplete"
    return state


# -------------------------------------------------------------- preflight #


def mem_available_bytes() -> int | None:
    try:
        with open("/proc/meminfo", "rb") as stream:
            for line in stream:
                if line.startswith(b"MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _preflight_thresholds(decision: dict[str, Any]) -> tuple[int, int]:
    requirements = decision["decision"]["preflight_requirements"]
    disk_threshold = None
    memory_threshold = None
    for requirement in requirements:
        check = str(requirement.get("check", ""))
        if disk_threshold is None and "free_disk_bytes" in check:
            disk_threshold = int(requirement["threshold_bytes"])
        if memory_threshold is None and "available_memory" in check:
            memory_threshold = int(requirement["threshold_bytes"])
    if disk_threshold is None or memory_threshold is None:
        raise HarnessError("decision preflight requirements are incomplete")
    return disk_threshold, memory_threshold


def preflight(
    *,
    decision: dict[str, Any],
    bin_path: Path,
    scratch_dir: Path,
    mem_probe: Callable[[], int | None] = mem_available_bytes,
    disk_probe: Callable[[Path], dict[str, int]] = probe.disk_snapshot,
) -> dict[str, Any]:
    """Fail-closed preflight: free disk, available memory, binary presence."""
    disk_threshold, memory_threshold = _preflight_thresholds(decision)
    stop = decision["decision"]["stop_thresholds"]
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    probe_dir = scratch_dir if scratch_dir.exists() else scratch_dir.parent
    try:
        free_disk = disk_probe(probe_dir)["free_bytes"]
    except OSError:
        free_disk = None
    disk_ok = free_disk is not None and free_disk >= disk_threshold
    checks.append(
        {
            "id": "free_disk_bytes",
            "threshold_bytes": disk_threshold,
            "observed_bytes": free_disk,
            "ok": disk_ok,
        }
    )
    if not disk_ok:
        failures.append("free_disk_bytes")

    available_memory = mem_probe()
    memory_ok = available_memory is not None and available_memory >= memory_threshold
    checks.append(
        {
            "id": "available_memory_bytes",
            "threshold_bytes": memory_threshold,
            "observed_bytes": available_memory,
            "ok": memory_ok,
        }
    )
    if not memory_ok:
        failures.append("available_memory_bytes")

    binary_ok = bin_path.is_file() and os.access(bin_path, os.X_OK)
    checks.append(
        {
            "id": "binary_present",
            "path": str(bin_path),
            "ok": binary_ok,
        }
    )
    if not binary_ok:
        failures.append("binary_present")

    return {
        "ok": not failures,
        "checks": checks,
        "failures": failures,
        "stop_thresholds": dict(stop),
    }


# ---------------------------------------------------------- verify ledger #


def verify_ledger(
    *,
    entries: Sequence[probe.Entry],
    receipts: Sequence[dict[str, Any]],
    live_binding: Binding | None = None,
) -> dict[str, Any]:
    """Objectively confirm ledger completeness and a single binding tuple.

    Requires exactly one authoritative (latest) receipt per manifest entry, each
    terminal, input-pinned to the manifest and a single binding tuple.  A live
    aggregate drift (e.g. the ledger's own publication shifted the code hash) is
    reported explicitly and does not fail the check.
    """
    latest = latest_by_path(receipts)
    entry_by_path = {entry.relative_path: entry for entry in entries}
    manifest_paths = [entry.relative_path for entry in entries]
    errors: list[dict[str, Any]] = []

    missing = [path for path in manifest_paths if path not in latest]
    extra = [path for path in latest if path not in entry_by_path]
    for path in missing:
        errors.append({"code": "missing_receipt", "relative_path": path})
    for path in extra:
        errors.append({"code": "unknown_receipt", "relative_path": path})

    counts = _empty_counts()
    bindings: dict[tuple[str, str, str], int] = {}
    for path in manifest_paths:
        receipt = latest.get(path)
        if receipt is None:
            continue
        _tally(counts, receipt)
        bindings[receipt_binding_key(receipt)] = bindings.get(receipt_binding_key(receipt), 0) + 1
        entry = entry_by_path[path]
        if receipt["input_sha256"] != entry.sha256 or receipt["input_bytes"] != entry.bytes:
            errors.append({"code": "input_mismatch", "relative_path": path})
        if receipt["outcome"] not in TERMINAL_OUTCOMES:
            errors.append({"code": "non_terminal", "relative_path": path})

    if len(bindings) > 1:
        errors.append({"code": "multiple_bindings", "count": len(bindings)})

    binding_key_out = None
    if len(bindings) == 1:
        code, rules, binary = next(iter(bindings))
        binding_key_out = {
            "code_revision": code,
            "rules_digest": rules,
            "binary_sha256": binary,
        }

    live_drift = None
    if live_binding is not None and binding_key_out is not None:
        live_drift = binding_key_out != {
            "code_revision": live_binding.code_revision,
            "rules_digest": live_binding.rules_digest,
            "binary_sha256": live_binding.binary_sha256,
        }

    ok = not errors
    return {
        "schema": RUN_SCHEMA,
        "ok": ok,
        "entries": len(entries),
        "received_receipts": len(receipts),
        "counts": counts,
        "terminal": counts["accepted"] + counts["refused"],
        "binding": binding_key_out,
        "distinct_bindings": len(bindings),
        "live_binding": live_binding.as_dict() if live_binding is not None else None,
        "live_drift": live_drift,
        "errors": errors,
        "partial_is_not_full": True,
    }


# ------------------------------------------------------------ resume proof #

PROOF_SCHEMA = "m223-s03-resume-proof/v1"
DEFAULT_PROOF_OUT = ROOT / "prd/migration/rust-evidence/m223-s03-resume-proof.json"
HARNESS_PATH = Path(__file__).resolve()

#: Seed for the deterministic proof subset (S02 probe seed, for traceability).
PROOF_SEED = 22302
#: Entries drawn per top-level corpus subdirectory.
PROOF_PER_SUBDIR = 25

#: Real, git-tracked non-WordML reader fixtures.  They validate the closed
#: refusal dictionary against actual product refusal tokens; whether the pinned
#: corpus itself emits typed refusals is reported by the ledger
#: (``refused_by_class``), never asserted in advance.
PROOF_REFUSAL_FIXTURES = (
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-not-wordml.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-namespace-absent.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-unsupported-schema.xml",
)

PROOF_NON_CLAIMS = NON_CLAIMS + (
    "Whether the pinned corpus emits any typed product refusal is a result of the "
    "run, reported by the ledger's refused_by_class, and is never asserted in "
    "advance; the closed refusal dictionary is validated against real non-WordML "
    "reader fixtures instead.",
    "The proof subset is a deterministic sample of the pinned manifest; its "
    "receipt bindings are snapshot-bound and shift with any tracked-file change.",
    "The SIGTERM interruption is enforced by timeout -s TERM on the real harness "
    "subprocess; the harness signal handler unwinds the live-poll loop, which "
    "SIGKILLs and reaps the in-flight export child, so an interrupted attempt "
    "never orphans an export. Resuming the same ledger re-attempts only the "
    "interrupted incomplete entry while preserving every current receipt.",
)


@dataclass(frozen=True)
class ProofSubset:
    """A deterministic proof subset derived from the pinned manifest."""

    entries: tuple[probe.Entry, ...]
    subdir_counts: dict[str, int]
    digest: str


#: Top-level corpus subdirectory of a manifest path.
def _top_subdir(relative_path: str) -> str:
    return relative_path.split("/", 1)[0]


def select_proof_subset(
    entries: Sequence[probe.Entry],
    *,
    seed: int = PROOF_SEED,
    per_subdir: int = PROOF_PER_SUBDIR,
) -> ProofSubset:
    """Deterministic seeded sample of the smallest per-subdir pool.

    Each top-level subdirectory contributes ``per_subdir`` entries drawn without
    replacement (fixed seed) from its ``3*per_subdir`` smallest files.  The
    selection is stable across runs and is fingerprinted by ``digest`` so the
    proof artifact is recomputable from its declared inputs.
    """
    grouped: dict[str, list[probe.Entry]] = {}
    for entry in entries:
        grouped.setdefault(_top_subdir(entry.relative_path), []).append(entry)

    rng = random.Random(seed)
    chosen: list[probe.Entry] = []
    counts: dict[str, int] = {}
    for top in sorted(grouped):
        bucket = sorted(grouped[top], key=lambda item: (item.bytes, item.relative_path))
        pool = bucket[: max(per_subdir, min(len(bucket), per_subdir * 3))]
        picked = rng.sample(pool, min(per_subdir, len(pool)))
        counts[top] = len(picked)
        chosen.extend(picked)
    chosen.sort(key=lambda item: item.relative_path)
    digest = (
        "sha256:"
        + hashlib.sha256(
            "".join(
                f"{item.relative_path}\t{item.sha256}\t{item.bytes}\n" for item in chosen
            ).encode("utf-8")
        ).hexdigest()
    )
    return ProofSubset(entries=tuple(chosen), subdir_counts=counts, digest=digest)


def run_refusal_probe(
    *,
    bin_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    attempt: int,
    corpus_root: Path = ROOT,
    fixture_paths: Sequence[str] = PROOF_REFUSAL_FIXTURES,
    hash_file: Callable[[Path], str] = probe.sha256_file,
    measure: Callable[..., dict[str, Any]] = probe.measure_subprocess,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Real typed refusals from real non-WordML inputs through the product path.

    Validates the closed refusal dictionary against the actual ``cleaned-project``
    tokens (the T01 known-issue follow-up).  Never carries decoded text — only
    paths, hashes, sizes and the closed outcome/reason tokens.
    """
    inputs: list[dict[str, Any]] = []
    for relative_path in fixture_paths:
        source = corpus_root / relative_path
        if not source.is_file():
            inputs.append({"relative_path": relative_path, "available": False})
            continue
        sha256, size = hash_and_size(source, hash_file)
        entry = probe.Entry(relative_path=relative_path, sha256=sha256 or "", bytes=size)
        receipt = process_entry(
            entry,
            corpus_root=corpus_root,
            bin_path=bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=scratch_dir / "refusal-probe",
            attempt=attempt,
            verify_input_after=False,
            hash_file=hash_file,
            measure=measure,
            now=now,
        )
        inputs.append(
            {
                "relative_path": relative_path,
                "available": True,
                "input_sha256": receipt["input_sha256"],
                "input_bytes": receipt["input_bytes"],
                "outcome": receipt["outcome"],
                "outcome_class": receipt["outcome_class"],
                "reason_family": receipt["reason_family"],
                "reason_token": receipt["reason_token"],
            }
        )
    available = [item for item in inputs if item.get("available")]
    observed = sorted({str(item["outcome_class"]) for item in available})
    all_refused = bool(available) and all(item["outcome"] == "refused" for item in available)
    return {
        "available": bool(available),
        "inputs": inputs,
        "observed_classes": observed,
        "all_refused_typed": all_refused,
        "note": "these are real non-WordML reader fixtures, not corpus entries; "
        "whether the pinned corpus emits refusals itself is reported by the ledger",
    }


def _mutate_ledger(
    path: Path,
    relative_path: str,
    updates: dict[str, Any],
    *,
    log: ReceiptLog | None = None,
) -> None:
    """Overwrite the latest receipt's fields in a working ledger copy."""
    reader = log if log is not None else ReceiptLog(path)
    records = reader.read()
    found = False
    for record in reversed(records):
        if record["relative_path"] == relative_path:
            record.update(updates)
            found = True
            break
    if not found:
        raise HarnessError(f"ledger has no receipt for {relative_path!r}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _mutate_ledger_binding(
    path: Path,
    relative_path: str,
    field: str,
    value: str,
    *,
    log: ReceiptLog | None = None,
) -> None:
    """Overwrite the latest receipt's binding field in a working ledger copy."""
    _mutate_ledger(path, relative_path, {field: value}, log=log)


def _run_harness_subprocess(
    cmd: Sequence[str], *, timeout_s: float | None = None, cwd: Path = ROOT
) -> dict[str, Any]:
    """Run the harness CLI, optionally wrapped in ``timeout -s TERM``."""
    full = ["timeout", "-s", "TERM", str(timeout_s), *cmd] if timeout_s is not None else list(cmd)
    started = time.monotonic()
    try:
        completed = subprocess.run(full, cwd=str(cwd), capture_output=True, text=True, check=False)
    except OSError as error:  # pragma: no cover - environment dependent
        raise HarnessError(f"harness subprocess failed to start: {type(error).__name__}") from error
    stderr_lines = completed.stderr.strip().splitlines()
    return {
        "rc": completed.returncode,
        "wall_s": round(time.monotonic() - started, 3),
        "command": full,
        "stdout_lines": completed.stdout.strip().splitlines(),
        "stderr_lines": stderr_lines,
        "stderr_tail": stderr_lines[-6:],
    }


def _harness_run_cmd(
    *,
    python: str,
    harness: Path,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    decision_path: Path,
    scratch_dir: Path,
    receipts_path: Path,
    report_path: Path,
    code_revision: str,
    extra: Sequence[str],
) -> list[str]:
    return [
        python,
        str(harness),
        "run",
        "--manifest",
        str(manifest_path),
        "--corpus-root",
        str(corpus_root),
        "--bin",
        str(bin_path),
        "--decision",
        str(decision_path),
        "--scratch",
        str(scratch_dir),
        "--receipts",
        str(receipts_path),
        "--report",
        str(report_path),
        "--code-revision",
        code_revision,
        *extra,
    ]


def interrupt_attempt(
    *,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    decision_path: Path,
    scratch_dir: Path,
    code_revision: str,
    processing_window_s: float = 4.0,
    harness: Path | None = None,
    python: str | None = None,
    cwd: Path = ROOT,
    retries: int = 1,
) -> dict[str, Any]:
    """Real ``timeout -s TERM`` interruption of the harness over the manifest.

    A calibration run measures the startup wall (manifest load + preflight) with
    zero entries; the interrupt run is then given ``startup + window`` seconds so
    it is killed mid-processing, leaving completed receipts plus an explicit
    ``incomplete/not_run`` receipt for the in-flight entry.
    """
    harness_path = Path(harness) if harness is not None else HARNESS_PATH
    py = python or sys.executable
    work = Path(scratch_dir) / "interrupt"
    work.mkdir(parents=True, exist_ok=True)
    manifest_abs = Path(manifest_path).resolve()
    corpus_abs = Path(corpus_root).resolve()
    bin_abs = Path(bin_path).resolve()
    decision_abs = Path(decision_path).resolve()

    calibration = _run_harness_subprocess(
        _harness_run_cmd(
            python=py,
            harness=harness_path,
            manifest_path=manifest_abs,
            corpus_root=corpus_abs,
            bin_path=bin_abs,
            decision_path=decision_abs,
            scratch_dir=work,
            receipts_path=work / "cal0.jsonl",
            report_path=work / "cal0.json",
            code_revision=code_revision,
            extra=["--max-entries", "0"],
        ),
        cwd=cwd,
    )
    if calibration["rc"] not in (EXIT_OK, EXIT_NOT_COMPLETE):
        raise HarnessError(f"interrupt calibration exited {calibration['rc']}")
    startup_s = float(calibration["wall_s"])

    last: dict[str, Any] | None = None
    for attempt in range(1, retries + 2):
        receipts = work / f"receipts-{attempt}.jsonl"
        report = work / f"run-{attempt}.json"
        if receipts.exists():
            receipts.unlink()
        window = processing_window_s * attempt
        timeout_s = round(startup_s + window + 0.5, 3)
        run = _run_harness_subprocess(
            _harness_run_cmd(
                python=py,
                harness=harness_path,
                manifest_path=manifest_abs,
                corpus_root=corpus_abs,
                bin_path=bin_abs,
                decision_path=decision_abs,
                scratch_dir=work,
                receipts_path=receipts,
                report_path=report,
                code_revision=code_revision,
                extra=["--resume", "--max-wall-s", "3600"],
            ),
            timeout_s=timeout_s,
            cwd=cwd,
        )
        got = ReceiptLog(receipts).read() if receipts.exists() else []
        latest = latest_by_path(got)
        not_run = sorted(
            path
            for path, record in latest.items()
            if record["outcome"] == "incomplete" and record["outcome_class"] == "not_run"
        )
        interrupted = run["rc"] in (124, 128 + signal.SIGTERM)
        last = {
            "mechanism": "timeout -s TERM",
            "signal": "SIGTERM",
            "timeout_s": timeout_s,
            "startup_s": startup_s,
            "processing_window_s": window,
            "exit_code": run["rc"],
            "wall_s": run["wall_s"],
            "receipts_before": 0,
            "receipts_after": len(got),
            "completed_preserved": len(got) >= 1,
            "in_flight_not_run": bool(not_run),
            "in_flight_relative_path": not_run[0] if not_run else None,
            "status": "interrupted" if interrupted else "not_interrupted",
            "report": str(report),
            "receipts_path": str(receipts),
            "stderr_tail": run["stderr_tail"],
        }
        if interrupted and len(got) >= 1 and not_run:
            break
    if last is None or last["status"] != "interrupted" or not last["in_flight_not_run"]:
        raise HarnessError("SIGTERM interruption proof did not observe an interrupted partial run")

    # Same-ledger resume proof: resume the *same* interrupted ledger in place.
    # Every current receipt must be preserved (never re-exported, no new source
    # data, no ledger substitution) and the in-flight ``incomplete/not_run``
    # entry must be re-attempted to a terminal outcome.  This is the finding the
    # previous proof left orphaned: it showed a SIGTERM interruption but then
    # resumed a *different*, fresh ledger.
    interrupted_receipts = Path(str(last["receipts_path"]))
    before = ReceiptLog(interrupted_receipts).read()
    latest_before = latest_by_path(before)
    terminal_before = sorted(
        path for path, record in latest_before.items() if record["outcome"] in TERMINAL_OUTCOMES
    )
    in_flight = last["in_flight_relative_path"]
    next_attempt = max((int(record["attempt"]) for record in before), default=0) + 1
    resume_run = _run_harness_subprocess(
        _harness_run_cmd(
            python=py,
            harness=harness_path,
            manifest_path=manifest_abs,
            corpus_root=corpus_abs,
            bin_path=bin_abs,
            decision_path=decision_abs,
            scratch_dir=work,
            receipts_path=interrupted_receipts,
            report_path=work / "resume-run.json",
            code_revision=code_revision,
            # --max-entries 1 stops right after the single re-attempted entry so
            # the resume proof never spills into a full-corpus run.
            extra=["--resume", "--max-wall-s", "3600", "--max-entries", "1"],
        ),
        cwd=cwd,
    )
    after = ReceiptLog(interrupted_receipts).read()
    latest_after = latest_by_path(after)
    written = [record for record in after if int(record["attempt"]) == next_attempt]
    skip_lines = [line for line in resume_run["stderr_lines"] if ": skip " in line]
    resumed_in_flight = latest_after.get(in_flight) if in_flight else None
    in_flight_terminal = (
        bool(resumed_in_flight) and resumed_in_flight["outcome"] in TERMINAL_OUTCOMES
    )
    preserved = all(latest_after.get(path) == latest_before[path] for path in terminal_before)
    no_new_source_paths = set(latest_after) == set(latest_before)
    if (
        resume_run["rc"] not in (EXIT_OK, EXIT_NOT_COMPLETE)
        or len(written) != 1
        or written[0]["relative_path"] != in_flight
        or not in_flight_terminal
        or not preserved
        or not no_new_source_paths
        or len(skip_lines) != len(terminal_before)
    ):
        raise HarnessError(
            "same-ledger resume proof did not preserve current receipts and "
            "re-attempt the interrupted incomplete entry"
        )
    last["receipts_after_resume"] = len(after)
    last["resume"] = {
        "status": "resumed",
        "same_ledger": True,
        "resumed_receipts_path": str(interrupted_receipts),
        "terminal_before": len(terminal_before),
        "skipped_current": len(skip_lines),
        "reattempted_incomplete": len(written),
        "in_flight_relative_path": in_flight,
        "reattempted_outcome": written[0]["outcome"],
        "reattempted_outcome_class": written[0]["outcome_class"],
        "preserved_current": preserved,
        "no_new_source_paths": no_new_source_paths,
        "receipts_after_resume": len(after),
        "resume_exit_code": resume_run["rc"],
        "note": "the interrupted attempt's own ledger was resumed in place; current "
        "receipts were skipped (not re-exported) and only the in-flight "
        "incomplete entry was re-attempted to a terminal outcome",
    }
    return last


def _attempt_record(
    label: str,
    kind: str,
    state: dict[str, Any],
    *,
    before: int,
    after: int,
    skipped: int,
    written: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = state.get("summary", {}) if isinstance(state, dict) else {}
    record: dict[str, Any] = {
        "label": label,
        "kind": kind,
        "status": state.get("status") if isinstance(state, dict) else None,
        "receipts_before": before,
        "receipts_after": after,
        "skipped_current": skipped,
        "written": written,
        "recomputed_stale": 0,
        "reattempted_incomplete": 0,
        "accepted": summary.get("accepted"),
        "refused": summary.get("refused"),
        "incomplete": summary.get("incomplete"),
        "terminal": summary.get("terminal"),
        "remaining": summary.get("remaining"),
    }
    if extra:
        record.update(extra)
    return record


def prove_resume(
    *,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    decision_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    receipts_path: Path,
    entries: Sequence[probe.Entry],
    seed: int = PROOF_SEED,
    per_subdir: int = PROOF_PER_SUBDIR,
    bounded_wall_s: float = 0.05,
    enable_interrupt: bool = True,
    enable_refusal_probe: bool = True,
    processing_window_s: float = 4.0,
    interrupt: Callable[..., dict[str, Any]] | None = None,
    run: Callable[..., dict[str, Any]] | None = None,
    hash_file: Callable[[Path], str] = probe.sha256_file,
    measure: Callable[..., dict[str, Any]] = probe.measure_subprocess,
    now: Callable[[], float] = time.time,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Prove interruption, resume and stale recompute on a real subset.

    Steps: (a) bounded partial attempt -> ``budget_exhausted``; (b) resume that
    skips the current receipts without re-exporting; (c) a mutated binding that
    is recomputed as stale; (d) a real ``timeout -s TERM`` interruption that
    preserves completed receipts; (e) a refusal probe against real non-WordML
    inputs; (f) a final completeness check over the subset.
    """
    run_fn = run if run is not None else run_baseline
    interrupt_fn = interrupt if interrupt is not None else interrupt_attempt
    subset = select_proof_subset(entries, seed=seed, per_subdir=per_subdir)
    subset_entries = list(subset.entries)
    subset_size = len(subset_entries)
    if subset_size < 2:
        raise HarnessError("proof subset is too small")

    scratch_dir.mkdir(parents=True, exist_ok=True)
    receipts_path.parent.mkdir(parents=True, exist_ok=True)
    if receipts_path.exists():
        receipts_path.unlink()
    log = ReceiptLog(receipts_path)

    export_calls = {"n": 0}

    def counting_measure(argv: Sequence[str], **kwargs: Any) -> dict[str, Any]:
        if len(argv) > 1 and argv[1] == "export":
            export_calls["n"] += 1
        return measure(argv, **kwargs)

    attempts: list[dict[str, Any]] = []

    # (a) bounded partial attempt
    a_state = run_fn(
        entries=subset_entries,
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits,
        scratch_dir=scratch_dir,
        receipts_path=receipts_path,
        attempt_wall_s=bounded_wall_s,
        max_entries=subset_size - 1,
        resume=True,
        hash_file=hash_file,
        measure=counting_measure,
        now=now,
        clock=clock,
    )
    a_receipts = log.read()
    if not (1 <= len(a_receipts) < subset_size):
        raise HarnessError("bounded attempt did not produce a partial ledger")
    if a_state["status"] != "budget_exhausted":
        raise HarnessError(f"bounded attempt status {a_state['status']!r}")
    a_terminal = sum(1 for record in a_receipts if record["outcome"] in TERMINAL_OUTCOMES)
    attempts.append(
        _attempt_record(
            "bounded-budget",
            "in-process",
            a_state,
            before=0,
            after=len(a_receipts),
            skipped=0,
            written=len(a_receipts),
            extra={"bounded_wall_s": bounded_wall_s, "max_entries": subset_size - 1},
        )
    )

    # (b) resume: skip current receipts, process the rest
    export_calls["n"] = 0
    b_state = run_fn(
        entries=subset_entries,
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits,
        scratch_dir=scratch_dir,
        receipts_path=receipts_path,
        attempt_wall_s=0.0,
        resume=True,
        hash_file=hash_file,
        measure=counting_measure,
        now=now,
        clock=clock,
    )
    b_receipts = log.read()
    b_written = len(b_receipts) - len(a_receipts)
    if b_state["status"] != "complete":
        raise HarnessError(f"resume attempt did not reach complete: {b_state['status']!r}")
    if b_state["skipped"] != a_terminal or export_calls["n"] != b_written or b_written < 1:
        raise HarnessError("resume did not skip exactly the current receipts")
    attempts.append(
        _attempt_record(
            "resume-skip",
            "in-process",
            b_state,
            before=len(a_receipts),
            after=len(b_receipts),
            skipped=b_state["skipped"],
            written=b_written,
            extra={"exports": export_calls["n"], "resumed_without_reexport": True},
        )
    )

    # (c) stale probe: mutate one current binding and prove recompute
    target = subset_entries[0].relative_path
    _mutate_ledger_binding(receipts_path, target, "code_revision", "sha256:" + "0" * 64, log=log)
    export_calls["n"] = 0
    c_state = run_fn(
        entries=subset_entries,
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits,
        scratch_dir=scratch_dir,
        receipts_path=receipts_path,
        attempt_wall_s=0.0,
        resume=True,
        hash_file=hash_file,
        measure=counting_measure,
        now=now,
        clock=clock,
    )
    c_receipts = log.read()
    c_latest = latest_by_path(c_receipts)
    if (
        c_state["status"] != "complete"
        or c_state["skipped"] != subset_size - 1
        or export_calls["n"] != 1
        or c_latest[target]["code_revision"] != binding.code_revision
    ):
        raise HarnessError("stale probe did not recompute exactly the mutated entry")
    attempts.append(
        _attempt_record(
            "stale-recompute",
            "in-process",
            c_state,
            before=len(b_receipts),
            after=len(c_receipts),
            skipped=c_state["skipped"],
            written=export_calls["n"],
            extra={
                "mutated_relative_path": target,
                "mutated_field": "code_revision",
                "recomputed_stale": 1,
            },
        )
    )
    stale_probe = {
        "how": "mutated one current receipt's code_revision in a working copy of the ledger, "
        "then resumed; a stale receipt is recomputed, never skipped",
        "mutated_relative_path": target,
        "field": "code_revision",
        "recomputed": True,
        "skipped_others": c_state["skipped"],
        "written": export_calls["n"],
    }

    # (c2) incomplete re-attempt: an incomplete receipt must never be skipped
    target2 = subset_entries[1].relative_path
    _mutate_ledger(
        receipts_path,
        target2,
        {"outcome": "incomplete", "outcome_class": "not_run", "note": "proof: forced incomplete"},
        log=log,
    )
    export_calls["n"] = 0
    d_state = run_fn(
        entries=subset_entries,
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits,
        scratch_dir=scratch_dir,
        receipts_path=receipts_path,
        attempt_wall_s=0.0,
        resume=True,
        hash_file=hash_file,
        measure=counting_measure,
        now=now,
        clock=clock,
    )
    d_receipts = log.read()
    d_latest = latest_by_path(d_receipts)
    if (
        d_state["status"] != "complete"
        or d_state["skipped"] != subset_size - 1
        or export_calls["n"] != 1
        or d_latest[target2]["outcome"] not in TERMINAL_OUTCOMES
    ):
        raise HarnessError("incomplete probe did not re-attempt exactly the incomplete entry")
    attempts.append(
        _attempt_record(
            "incomplete-reattempt",
            "in-process",
            d_state,
            before=len(c_receipts),
            after=len(d_receipts),
            skipped=d_state["skipped"],
            written=export_calls["n"],
            extra={
                "mutated_relative_path": target2,
                "reattempted_incomplete": 1,
                "forced_outcome": "incomplete/not_run",
            },
        )
    )

    # (d) real SIGTERM interruption via timeout -s TERM
    interruption = None
    if enable_interrupt:
        interruption = interrupt_fn(
            manifest_path=manifest_path,
            corpus_root=corpus_root,
            bin_path=bin_path,
            decision_path=decision_path,
            scratch_dir=scratch_dir,
            code_revision=binding.code_revision,
            processing_window_s=processing_window_s,
        )
        attempts.append(
            {
                "label": "sigterm-interrupt",
                "kind": "subprocess-timeout",
                "status": interruption.get("status"),
                "receipts_before": interruption.get("receipts_before"),
                "receipts_after": interruption.get("receipts_after"),
                "exit_code": interruption.get("exit_code"),
                "signal": interruption.get("signal"),
            }
        )

    # (e) closed refusal dictionary against real non-WordML inputs
    refusal_probe = None
    if enable_refusal_probe:
        refusal_probe = run_refusal_probe(
            bin_path=bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=scratch_dir,
            attempt=len(attempts) + 1,
            hash_file=hash_file,
            measure=measure,
            now=now,
        )
        if not refusal_probe["available"] or not refusal_probe["all_refused_typed"]:
            raise HarnessError("refusal probe did not observe real typed refusals")

    # (f) final completeness over the subset
    final = verify_ledger(entries=subset_entries, receipts=log.read(), live_binding=binding)
    if not final["ok"]:
        raise HarnessError("final verify-ledger over the proof subset failed")

    return {
        "schema": PROOF_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": {
            "path": str(manifest_path),
            "sha256": hash_file(manifest_path),
            "entries": len(entries),
        },
        "bindings": binding.as_dict(),
        "subset": {
            "definition": "seeded sample of the smallest per-subdir pool of the pinned manifest",
            "seed": seed,
            "per_subdir": per_subdir,
            "size": subset_size,
            "digest": subset.digest,
            "subdirs": subset.subdir_counts,
            "non_wordml_subdir_present": False,
            "refusal_capable": False,
        },
        "attempts": attempts,
        "interruption": interruption,
        "stale_probe": stale_probe,
        "refusal_probe": refusal_probe,
        "final": {
            "verify_ledger_ok": final["ok"],
            "entries": final["entries"],
            "terminal": final["terminal"],
            "accepted": final["counts"]["accepted"],
            "refused": final["counts"]["refused"],
            "incomplete": final["counts"]["incomplete"],
            "distinct_bindings": final["distinct_bindings"],
        },
        "partial_is_not_full": True,
        "non_claims": list(PROOF_NON_CLAIMS),
    }


def verify_proof(
    *,
    proof: dict[str, Any],
    entries: Sequence[probe.Entry],
    receipts: Sequence[dict[str, Any]],
    live_binding: Binding | None = None,
) -> dict[str, Any]:
    """Re-derive a proof artifact from its declared inputs.

    Recomputes the deterministic subset digest from the manifest and re-runs the
    ledger completeness check over the subset; a mismatch is fail-closed.
    """
    if not isinstance(proof, dict) or proof.get("schema") != PROOF_SCHEMA:
        return {"ok": False, "errors": ["proof_schema"], "ledger": None}
    subset_spec = proof.get("subset") or {}
    subset = select_proof_subset(
        entries,
        seed=int(subset_spec.get("seed", PROOF_SEED)),
        per_subdir=int(subset_spec.get("per_subdir", PROOF_PER_SUBDIR)),
    )
    errors: list[str] = []
    if subset.digest != subset_spec.get("digest"):
        errors.append("subset_digest_mismatch")
    if len(subset.entries) != subset_spec.get("size"):
        errors.append("subset_size_mismatch")
    ledger = verify_ledger(
        entries=list(subset.entries), receipts=receipts, live_binding=live_binding
    )
    if not ledger["ok"]:
        errors.append("ledger_not_current")

    # The interruption block, when present, must carry a counts-only same-ledger
    # resume claim: current receipts preserved (skipped, not re-exported), the
    # in-flight incomplete entry re-attempted, and no new source paths introduced.
    interruption = proof.get("interruption")
    if interruption is not None:
        resume = interruption.get("resume") if isinstance(interruption, dict) else None
        if not isinstance(resume, dict):
            errors.append("interruption_resume_missing")
        else:
            if resume.get("same_ledger") is not True:
                errors.append("interruption_resume_not_same_ledger")
            if resume.get("skipped_current") != resume.get("terminal_before"):
                errors.append("interruption_resume_skip_mismatch")
            if resume.get("reattempted_incomplete") != 1:
                errors.append("interruption_resume_reattempt_mismatch")
            if resume.get("preserved_current") is not True:
                errors.append("interruption_resume_current_not_preserved")
            if resume.get("no_new_source_paths") is not True:
                errors.append("interruption_resume_new_paths")
    return {"ok": not errors, "errors": errors, "ledger": ledger}


# ------------------------------------------------------------------ report #


def build_run_report(
    *,
    state: dict[str, Any],
    header: dict[str, Any],
    manifest_path: Path,
    decision: dict[str, Any],
    attempts: list[dict[str, Any]],
    preflight_result: dict[str, Any] | None,
    manifest_sha256: str,
) -> dict[str, Any]:
    summary = state["summary"]
    return {
        "schema": RUN_SCHEMA,
        "status": state["status"],
        "partial_is_not_full": True,
        "manifest": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "inventory_digest": header.get("inventory_digest"),
            "entries": summary.get("entries"),
            "counts": header.get("counts"),
        },
        "bindings": state["binding"],
        "counts": {
            "entries": summary.get("entries"),
            "accepted": summary.get("accepted"),
            "refused": summary.get("refused"),
            "incomplete": summary.get("incomplete"),
            "terminal": summary.get("terminal"),
            "remaining": summary.get("remaining"),
        },
        "refused_by_class": summary.get("refused_by_class"),
        "incomplete_by_class": summary.get("incomplete_by_class"),
        "disk": {
            "before": state.get("disk_before"),
            "after": state.get("disk_after"),
            "persisted_layer_bytes": 0,
        },
        "stop_thresholds": decision["decision"]["stop_thresholds"],
        "preflight": preflight_result,
        "attempts": attempts,
        "r1000_status": "active/unclosed",
        "binary_drift": bool(state.get("binary_drift")),
        "readback_is_substrate_verify": False,
        "non_claims": list(NON_CLAIMS),
    }


def _readback_disclaimer() -> dict[str, Any]:
    return {
        "counts_only": True,
        "independent_substrate_verify": False,
        "note": NON_CLAIMS[1],
    }


# -------------------------------------------------------------------- cli #


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--bin", dest="bin_path", type=Path, default=DEFAULT_BIN)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--receipts", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument(
        "--code-revision",
        default=None,
        help="test/ops override for the aggregate code revision (never guessed in production)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M223/S03 resumable corpus baseline runner")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run one resumable attempt")
    _add_common(run_parser)
    run_parser.add_argument("--resume", action="store_true", help="skip current receipts")
    run_parser.add_argument(
        "--max-wall-s", type=float, default=0.0, help="attempt wall budget; 0 = decision wall stop"
    )
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--max-entries", type=int, default=None)
    run_parser.add_argument("--skip-preflight", action="store_true")
    run_parser.add_argument("--export-wall-s", type=float, default=None)
    run_parser.add_argument("--readback-wall-s", type=float, default=None)

    status_parser = sub.add_parser("status", help="machine-readable progress snapshot")
    _add_common(status_parser)

    verify_parser = sub.add_parser("verify-ledger", help="verify ledger completeness")
    _add_common(verify_parser)

    preflight_parser = sub.add_parser("preflight", help="fail-closed environment preflight")
    _add_common(preflight_parser)

    prove_parser = sub.add_parser(
        "prove-resume", help="prove interruption, resume and stale recompute on a real subset"
    )
    _add_common(prove_parser)
    prove_parser.add_argument("--out", type=Path, default=DEFAULT_PROOF_OUT)
    prove_parser.add_argument("--seed", type=int, default=PROOF_SEED)
    prove_parser.add_argument("--per-subdir", type=int, default=PROOF_PER_SUBDIR)
    prove_parser.add_argument("--bounded-wall-s", type=float, default=0.05)
    prove_parser.add_argument("--processing-window-s", type=float, default=4.0)
    prove_parser.add_argument("--skip-interrupt", action="store_true")
    prove_parser.add_argument("--skip-refusal-probe", action="store_true")

    verify_proof_parser = sub.add_parser(
        "verify-proof", help="re-derive a resume-proof artifact from its inputs"
    )
    _add_common(verify_proof_parser)
    verify_proof_parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF_OUT)

    return parser


def _proof_receipts_path(args: argparse.Namespace) -> Path:
    if args.receipts is not None:
        return args.receipts
    return args.scratch / "proof" / "receipts.jsonl"


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    receipts = args.receipts if args.receipts is not None else args.scratch / "receipts.jsonl"
    report = args.report if args.report is not None else args.scratch / "run.json"
    return receipts, report


def _limits_from_decision(
    decision: dict[str, Any],
    *,
    export_wall_s: float | None,
    readback_wall_s: float | None,
) -> probe.Limits:
    stop = decision["decision"]["stop_thresholds"]
    return probe.Limits(
        export_wall_s=export_wall_s if export_wall_s is not None else 1800.0,
        readback_wall_s=readback_wall_s if readback_wall_s is not None else 600.0,
        peak_rss_kb=int(stop["peak_rss_kb"]),
        min_free_disk_bytes=int(probe.Limits.min_free_disk_bytes),
        abort_free_disk_bytes=int(probe.Limits.abort_free_disk_bytes),
        max_single_artifact_bytes=int(stop["single_artifact_bytes"]),
        total_budget_wall_s=float(stop["wall_s"]),
    )


def cmd_run(args: argparse.Namespace) -> int:
    receipts_path, report_path = _resolve_paths(args)
    args.scratch.mkdir(parents=True, exist_ok=True)
    try:
        decision = load_decision(args.decision)
        manifest_sha256 = probe.sha256_file(args.manifest)
        header, entries = load_manifest(args.manifest, decision=decision)
        binding = compute_binding(args.bin_path, code_revision=args.code_revision)
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT

    limits = _limits_from_decision(
        decision, export_wall_s=args.export_wall_s, readback_wall_s=args.readback_wall_s
    )
    attempt_wall_s = (
        args.max_wall_s
        if args.max_wall_s > 0
        else float(decision["decision"]["stop_thresholds"]["wall_s"])
    )

    preflight_result = None
    if not args.skip_preflight:
        preflight_result = preflight(
            decision=decision, bin_path=args.bin_path, scratch_dir=args.scratch
        )
        if not preflight_result["ok"]:
            report = build_run_report(
                state={
                    "status": "preflight_failed",
                    "binding": binding.as_dict(),
                    "summary": {"entries": len(entries)},
                    "disk_before": probe.disk_snapshot(args.scratch),
                    "disk_after": probe.disk_snapshot(args.scratch),
                },
                header=header,
                manifest_path=args.manifest,
                decision=decision,
                attempts=[],
                preflight_result=preflight_result,
                manifest_sha256=manifest_sha256,
            )
            report_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(report, report_path)
            print(
                f"m223-s03-baseline: preflight failed: {','.join(preflight_result['failures'])}",
                file=sys.stderr,
            )
            print(json.dumps(preflight_result, ensure_ascii=True))
            return EXIT_PREFLIGHT

    print(
        f"m223-s03-baseline: run attempt_wall_s={attempt_wall_s} "
        f"entries={len(entries)} code_revision={binding.code_revision} "
        f"binary_sha256={binding.binary_sha256} resume={bool(args.resume)}",
        file=sys.stderr,
    )

    def on_receipt(receipt: dict[str, Any]) -> None:
        print(
            f"m223-s03-baseline: {receipt['relative_path']} -> "
            f"{receipt['outcome']}/{receipt['outcome_class']}",
            file=sys.stderr,
        )

    def status_cb(message: str) -> None:
        print(f"m223-s03-baseline: {message}", file=sys.stderr)

    exit_code = EXIT_OK
    try:
        state = run_baseline(
            entries=entries,
            corpus_root=args.corpus_root,
            bin_path=args.bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=args.scratch,
            receipts_path=receipts_path,
            attempt_wall_s=attempt_wall_s,
            resume=bool(args.resume),
            dry_run=bool(args.dry_run),
            max_entries=args.max_entries,
            on_receipt=on_receipt,
            status_cb=status_cb,
        )
    except probe.Interrupted as interrupted:
        exit_code = 128 + interrupted.signum
        state = {
            "status": "interrupted",
            "binding": binding.as_dict(),
            "summary": summarize_receipts(
                entries, latest_by_path(ReceiptLog(receipts_path).read())
            ),
            "disk_before": probe.disk_snapshot(args.scratch),
            "disk_after": probe.disk_snapshot(args.scratch),
        }

    if state["status"] == "complete":
        exit_code = EXIT_OK
    elif state["status"] == "dry_run":
        exit_code = EXIT_OK
    elif state["status"] == "budget_exhausted":
        exit_code = EXIT_NOT_COMPLETE
    elif state["status"] == "disk_guard_stopped":
        exit_code = EXIT_DISK_GUARD
    elif state["status"] == "incomplete":
        exit_code = EXIT_INCOMPLETE

    existing_attempts = _recent_attempts(ReceiptLog(receipts_path).read())
    report = build_run_report(
        state=state,
        header=header,
        manifest_path=args.manifest,
        decision=decision,
        attempts=existing_attempts,
        preflight_result=preflight_result,
        manifest_sha256=manifest_sha256,
    )
    report["readback"] = _readback_disclaimer()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(report, report_path)
    print(
        f"m223-s03-baseline: status={state['status']} "
        f"accepted={state['summary'].get('accepted')} refused={state['summary'].get('refused')} "
        f"incomplete={state['summary'].get('incomplete')} remaining={state['summary'].get('remaining')}",
        file=sys.stderr,
    )
    return exit_code


def _recent_attempts(receipts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts: dict[int, dict[str, Any]] = {}
    for receipt in receipts:
        attempt = int(receipt["attempt"])
        record = attempts.setdefault(attempt, {"attempt": attempt, "receipts": 0})
        record["receipts"] += 1
    ordered = [attempts[key] for key in sorted(attempts)]
    return ordered[-20:]


def cmd_status(args: argparse.Namespace) -> int:
    receipts_path, _ = _resolve_paths(args)
    try:
        decision = load_decision(args.decision)
        header, entries = load_manifest(args.manifest, decision=decision)
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    try:
        receipts = ReceiptLog(receipts_path).read()
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_VERIFY_FAILED
    latest = latest_by_path(receipts)
    summary = summarize_receipts(entries, latest)
    snapshot = {
        "schema": RUN_SCHEMA,
        "receipts_path": str(receipts_path),
        "manifest_entries": len(entries),
        "inventory_digest": header.get("inventory_digest"),
        "summary": summary,
        "partial_is_not_full": summary["terminal"] != summary["entries"],
    }
    print(json.dumps(snapshot, ensure_ascii=True, sort_keys=True))
    return EXIT_OK


def cmd_verify_ledger(args: argparse.Namespace) -> int:
    receipts_path, _ = _resolve_paths(args)
    try:
        decision = load_decision(args.decision)
        header, entries = load_manifest(args.manifest, decision=decision)
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    try:
        receipts = ReceiptLog(receipts_path).read()
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_VERIFY_FAILED

    live_binding = None
    try:
        live_binding = compute_binding(args.bin_path, code_revision=args.code_revision)
    except HarnessError:
        live_binding = None

    result = verify_ledger(entries=entries, receipts=receipts, live_binding=live_binding)
    result["manifest"] = {
        "path": str(args.manifest),
        "sha256": probe.sha256_file(args.manifest),
        "inventory_digest": header.get("inventory_digest"),
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return EXIT_OK if result["ok"] else EXIT_VERIFY_FAILED


def cmd_preflight(args: argparse.Namespace) -> int:
    try:
        decision = load_decision(args.decision)
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    result = preflight(decision=decision, bin_path=args.bin_path, scratch_dir=args.scratch)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if not result["ok"]:
        print(
            f"m223-s03-baseline: preflight failed: {','.join(result['failures'])}", file=sys.stderr
        )
        return EXIT_PREFLIGHT
    return EXIT_OK


def cmd_prove_resume(args: argparse.Namespace) -> int:
    receipts_path = _proof_receipts_path(args)
    args.scratch.mkdir(parents=True, exist_ok=True)
    try:
        decision = load_decision(args.decision)
        _header, entries = load_manifest(args.manifest, decision=decision)
        binding = compute_binding(args.bin_path, code_revision=args.code_revision)
        limits = _limits_from_decision(decision, export_wall_s=None, readback_wall_s=None)
        proof = prove_resume(
            manifest_path=args.manifest,
            corpus_root=args.corpus_root,
            bin_path=args.bin_path,
            decision_path=args.decision,
            binding=binding,
            limits=limits,
            scratch_dir=args.scratch,
            receipts_path=receipts_path,
            entries=entries,
            seed=args.seed,
            per_subdir=args.per_subdir,
            bounded_wall_s=args.bounded_wall_s,
            processing_window_s=args.processing_window_s,
            enable_interrupt=not args.skip_interrupt,
            enable_refusal_probe=not args.skip_refusal_probe,
        )
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_VERIFY_FAILED

    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(proof, args.out)
    print(
        json.dumps(
            {
                "schema": PROOF_SCHEMA,
                "subset_size": proof["subset"]["size"],
                "final": proof["final"],
                "interruption": (proof["interruption"] or {}).get("status"),
                "out": str(args.out),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return EXIT_OK


def cmd_verify_proof(args: argparse.Namespace) -> int:
    receipts_path = _proof_receipts_path(args)
    try:
        decision = load_decision(args.decision)
        _header, entries = load_manifest(args.manifest, decision=decision)
    except HarnessError as error:
        print(f"m223-s03-baseline: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    try:
        proof = json.loads(args.proof.read_text(encoding="utf-8"))
        receipts = ReceiptLog(receipts_path).read()
    except (OSError, json.JSONDecodeError, HarnessError) as error:
        print(f"m223-s03-baseline: fail-closed: {type(error).__name__}", file=sys.stderr)
        return EXIT_VERIFY_FAILED

    live_binding = None
    try:
        live_binding = compute_binding(args.bin_path, code_revision=args.code_revision)
    except HarnessError:
        live_binding = None

    result = verify_proof(
        proof=proof, entries=entries, receipts=receipts, live_binding=live_binding
    )
    result["proof"] = str(args.proof)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return EXIT_OK if result["ok"] else EXIT_VERIFY_FAILED


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        _install_signal_handlers()
        return cmd_run(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "verify-ledger":
        return cmd_verify_ledger(args)
    if args.command == "preflight":
        return cmd_preflight(args)
    if args.command == "prove-resume":
        return cmd_prove_resume(args)
    if args.command == "verify-proof":
        return cmd_verify_proof(args)
    parser.error("unknown command")
    return EXIT_USAGE


def _install_signal_handlers() -> None:
    def handler(signum: int, _frame: Any) -> None:
        raise probe.Interrupted(signum)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
    os.replace(tmp, path)


if __name__ == "__main__":
    raise SystemExit(main())
