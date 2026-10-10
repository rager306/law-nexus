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
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
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

    return parser


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
