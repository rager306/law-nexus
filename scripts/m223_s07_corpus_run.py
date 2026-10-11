#!/usr/bin/env python3
"""M223/S07 consumer acceptance corpus harness (process harness).

This harness runs the **counts-only consumer binary** ``consumer-run`` over the
entries of a pinned corpus manifest and gives each entry **exactly one terminal
consumer outcome**:

* ``accepted`` — ``consumer-run`` exited ``0`` **and** the emitted counts
  document passed the closed accounting/redaction check (schema
  ``m223-s07-consumer-counts/v1``);
* ``refused`` — a typed, closed refusal (exit ``5`` source / exit ``6``
  consumer) whose closed stderr reason token is recognised; a refusal is **not**
  a functional success and is never counted as one;
* ``incomplete`` — a harness class (timeout / signal / resource stop / usage /
  unwritable / artifact-verify failed / exec error / unknown exit / not run /
  input or binary drift); an ``incomplete`` entry is always re-attempted on
  resume and is never reported as ``accepted``.

Every receipt is bound to four hash families (acceptance contract §8.6):

* **input** — per-entry ``sha256`` + ``bytes`` from the manifest *and* the bytes
  actually observed on disk before (and re-verified after) the run;
* **code** — the aggregate source revision from
  ``scripts/m204_s08_source_revision.mjs`` (never a guessed HEAD);
* **rules** — the closed consumer profile tuple (``reader_tokenizer/v1``,
  ``npa_graph_projection/v1``, ``m223-s07-consumer-counts/v1``);
* **binary** — the sha256 of the ``consumer-run`` executable actually run.

A receipt is *current* only when all four pin the live values; otherwise it is
stale and the entry is recomputed.  A full run is ``complete`` only when every
manifest entry has a current terminal receipt — a partial run is never reported
as full (``partial_is_not_full`` is always ``true``).

Resource discipline is inherited verbatim from ``scripts/m223_s02_probe.py``
(``measure_subprocess`` live-polls ``/proc/<pid>/status`` VmHWM, the growing
artifact and its ``.tmp`` sibling, and free disk, SIGKILLing on breach) — this
module imports that core rather than forking it.

No raw decoded text ever reaches a receipt, the run report, a diagnostic or
stdout/stderr: only paths, counts, sizes and hashes.  The counts document is
itself counts-only; this harness additionally asserts the redaction invariant
over every string it persists.

Reads stay under the gitignored ``target/m223-s07/`` scratch path; the live
ledger is not tracked, because a tracked ledger under
``prd/migration/rust-evidence/`` would shift the aggregate code hash and void
the binding on resume.  Publication of a finished ledger/report is a separate,
deliberate step (``publish``).
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

RECEIPT_SCHEMA = "m223-s07-consumer-receipt/v1"
RUN_SCHEMA = "m223-s07-corpus-run/v1"
PROOF_SCHEMA = "m223-s07-resume-proof/v1"
REPEAT_PROOF_SCHEMA = "m223-s07-repeat-import-proof/v1"
COUNTS_SCHEMA = "m223-s07-consumer-counts/v1"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
S03_BASELINE_SCHEMA = "m223-s03-baseline-run/v1"
DECISION_SCHEMA = "m223-s02-corpus-feasibility/v1"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_CORPUS_ROOT = Path("consru_export/consru_export/exports")
DEFAULT_BIN = ROOT / "target/release/consumer-run"
DEFAULT_DECISION = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-feasibility.json"
DEFAULT_S03_BASELINE = ROOT / "prd/migration/rust-evidence/m223-s03-baseline-run.json"
DEFAULT_SCRATCH = ROOT / "target/m223-s07"
DEFAULT_RUN_OUT = ROOT / "prd/migration/rust-evidence/m223-s07-corpus-run.json"
DEFAULT_RECEIPTS_OUT = ROOT / "prd/migration/rust-evidence/m223-s07-corpus-receipts.jsonl"
DEFAULT_RESUME_PROOF_OUT = ROOT / "prd/migration/rust-evidence/m223-s07-resume-proof.json"
DEFAULT_REPEAT_PROOF_OUT = ROOT / "prd/migration/rust-evidence/m223-s07-repeat-import-proof.json"
SOURCE_REVISION_SCRIPT = _SCRIPTS_DIR / "m204_s08_source_revision.mjs"

# ----------------------------------------------------------- vocabularies #

#: Terminal outcomes: the run may skip a *current* receipt of one of these.
TERMINAL_OUTCOMES = ("accepted", "refused")
#: Closed outcome vocabulary.
ALL_OUTCOMES = ("accepted", "refused", "incomplete")

#: Closed consumer profile tuple (acceptance contract §8.6 "rules").
CONSUMER_PROFILES = (
    ("tokenizer", "reader_tokenizer/v1"),
    ("graph", "npa_graph_projection/v1"),
    ("counts", "m223-s07-consumer-counts/v1"),
)

#: Reader transfer-gate source classes that are *refusals* (never accepted).
READER_SOURCE_REFUSALS = frozenset(
    {"source_not_wordml", "unsupported_schema", "namespace_absent", "empty_source"}
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

#: Closed cleaned-wire ``WireErrorKind`` tokens (cleaned_wire.rs).
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

#: Closed ``TokenizerErrorKind`` tokens (reader_tokenizer.rs).
TOKENIZER_ERROR_KINDS = frozenset(
    {
        "artifact_unreadable",
        "identity_invalid",
        "unknown_view",
        "not_primary_view",
        "order_unavailable",
        "missing_segment",
        "missing_fragment",
        "missing_provenance",
        "output_gap",
        "span_invalid",
        "address_refused",
    }
)

#: Closed ``GraphErrorKind`` tokens (npa_graph_projection.rs).
GRAPH_ERROR_KINDS = frozenset(
    {
        "envelope_unreadable",
        "cross_document",
        "source_identity_mismatch",
        "document_version_mismatch",
        "unknown_fragment",
    }
)

#: Closed ``AnalysisWireErrorKind`` tokens (npa_analysis_wire.rs).
ANALYSIS_WIRE_ERROR_KINDS = frozenset(
    {
        "line_bytes_limit",
        "records_limit",
        "missing_trailing_lf",
        "carriage_return",
        "empty_line",
        "envelope_structural",
        "unknown_kind",
        "hash_shape_invalid",
        "completion_marker_invalid",
        "refused_record_not_promoted",
        "temporal_field_forbidden",
        "corpus_transfer_forbidden",
        "fragment_missing",
    }
)

#: Consumer-side closed refusal tokens the binary emits explicitly.
EXPLICIT_CONSUMER_TOKENS = frozenset(
    {
        "projection_refused",
        "record_index_refused",
        "analysis_identity_refused",
        "analysis_version_refused",
        "analysis_mapping_refused",
        "analysis_refused",
        "repeat_import_counts_drift",
    }
)

#: The closed set of tokens ``consumer-run: consumer failed: <token>`` may carry.
CONSUMER_REFUSAL_TOKENS = (
    WIRE_ERROR_KINDS
    | TOKENIZER_ERROR_KINDS
    | GRAPH_ERROR_KINDS
    | ANALYSIS_WIRE_ERROR_KINDS
    | EXPLICIT_CONSUMER_TOKENS
)

#: Closed ``io_error_token`` values for ``cannot read --from-xml``.
IO_TOKENS = frozenset({"not_found", "permission_denied", "invalid_data", "io_error"})

#: Incomplete harness classes.
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

#: Map a ``classify_consumer`` verdict to an incomplete class.
CONSUMER_OUTCOME_TO_INCOMPLETE = {
    "timeout": "timeout",
    "rss_limit_exceeded": "rss_limit_exceeded",
    "output_limit_exceeded": "output_limit_exceeded",
    "disk_limit_exceeded": "disk_limit_exceeded",
    "signaled": "signal",
    "usage_error": "usage_error",
    "out_unwritable": "out_unwritable",
    "input_unreadable": "input_drift",
    "exec_error": "exec_error",
    "unknown_exit": "unknown_exit",
    "harness_error": "harness_error",
    "not_run": "not_run",
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
    "Not an R1000 closure artifact and not a semantic or legal interpretation; "
    "R1000 stays active/unclosed.",
    "The counts document is a counts-only read of the materialized JSONL layers; "
    "it is NOT an independent substrate verification and NOT an authenticity claim.",
    "A partial run is never reported as full (partial_is_not_full=true).",
    "No raw decoded text reaches receipts, the report, diagnostics or stdout; every "
    "persisted string is a path, a hash, a count or a closed token.",
    "The S03 baseline is an acceptance/integrity baseline, not a semantic oracle; "
    "S07 reconciles counts only.",
)

REFUSAL_PATTERNS: tuple[tuple[str, re.Pattern[str], frozenset[str]], ...] = (
    ("source", re.compile(r"^consumer-run: source refused: (\S+)$"), READER_SOURCE_REFUSALS),
    (
        "package",
        re.compile(r"^consumer-run: capture failed: source package error: (\w+)"),
        PACKAGE_ERROR_KINDS,
    ),
    ("consumer", re.compile(r"^consumer-run: consumer failed: (\S+)$"), CONSUMER_REFUSAL_TOKENS),
    ("io", re.compile(r"^consumer-run: cannot read --from-xml: (\S+)$"), IO_TOKENS),
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
    """Canonical sha256 over the closed consumer profile tuple."""
    canonical = "".join(f"{key}={value}\n" for key, value in CONSUMER_PROFILES)
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
    lines = completed.stdout.strip().splitlines()
    if not lines:
        raise HarnessError("source revision runner produced no output")
    try:
        payload = json.loads(lines[-1])
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
        raise HarnessError(f"consumer-run binary missing: {bin_path}")
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
    """Load and fail-closed validate the S02 feasibility resource authority."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError(f"decision unreadable: {type(error).__name__}") from error
    if not isinstance(payload, dict) or payload.get("schema") != DECISION_SCHEMA:
        raise HarnessError("decision is not the S02 feasibility authority")
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise HarnessError("decision block is absent")
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
    return payload


def load_manifest(
    path: Path,
    *,
    hash_file: Callable[[Path], str] = probe.sha256_file,
) -> tuple[dict[str, Any], list[probe.Entry]]:
    """Read a pinned manifest and fail-closed validate safety and pins."""
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

    counts = header.get("counts") or {}
    if counts.get("entries") is not None and int(counts["entries"]) != len(entries):
        raise HarnessError("manifest header counts.entries disagrees with the body")
    return header, entries


def hash_and_size(path: Path, hash_file: Callable[[Path], str]) -> tuple[str | None, int]:
    """Actual sha256 + byte size of a source file; ``(None, 0)`` when unreadable."""
    try:
        return hash_file(path), path.stat().st_size
    except OSError:
        return None, 0


def load_s03_baseline(path: Path) -> dict[str, Any]:
    """Load the S03 baseline and extract the four reconciled numbers."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError(f"S03 baseline unreadable: {type(error).__name__}") from error
    if not isinstance(payload, dict) or payload.get("schema") != S03_BASELINE_SCHEMA:
        raise HarnessError("S03 baseline is not the expected schema")
    counts = payload.get("counts")
    if not isinstance(counts, dict):
        raise HarnessError("S03 baseline counts block is absent")
    return {
        "path": str(path),
        "entries": counts.get("entries"),
        "accepted": counts.get("accepted"),
        "refused": counts.get("refused"),
        "incomplete": counts.get("incomplete"),
        "terminal": counts.get("terminal"),
        "r1000_status": payload.get("r1000_status"),
        "status": payload.get("status"),
    }


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
        "counts": None,
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
    """Closed parse of a consumer refusal stderr line.

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


# ----------------------------------------------------------- counts check #

#: The decoded corpus is Russian legal text, so any non-ASCII character in a
#: persisted string is a decoded-text leak.  A generous length cap catches an
#: ASCII leak (e.g. a long English fragment) that the byte check would miss.
_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_MAX_PERSISTED_STRING = 4096


def assert_no_raw_text(value: Any, *, where: str = "$") -> None:
    """Fail-closed redaction invariant over a persisted JSON value.

    Every persisted string must be a path, a hash, a count, a closed token or a
    bounded English diagnostic.  Decoded legal text (Cyrillic) can never pass.
    """
    if isinstance(value, str):
        if _NON_ASCII.search(value):
            raise HarnessError(f"raw decoded text leaked into {where}")
        if len(value) > _MAX_PERSISTED_STRING:
            raise HarnessError(f"oversized string persisted at {where}")
    elif isinstance(value, dict):
        for key, item in value.items():
            assert_no_raw_text(item, where=f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_raw_text(item, where=f"{where}[{index}]")
    elif value is not None and not isinstance(value, (int, float, bool)):
        raise HarnessError(f"unexpected value type at {where}")


def validate_counts_doc(text: str, *, input_sha256: str) -> tuple[dict[str, Any], str | None]:
    """Parse and validate one consumer counts document.  Returns (doc, error)."""
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return {}, "counts document is not JSON"
    if not isinstance(doc, dict):
        return {}, "counts document is not an object"
    if doc.get("schema") != COUNTS_SCHEMA:
        return {}, "counts schema mismatch"

    required = {
        "schema",
        "docs",
        "tokens_total",
        "tokens_source",
        "tokens_derived",
        "tokens_composite",
        "tokens_by_class",
        "derived_by_kind",
        "graph",
        "repeat_import",
        "identity",
        "profiles",
    }
    if not required.issubset(doc):
        return {}, "counts document is missing required keys"

    if doc["docs"] != 1:
        return {}, "counts document does not cover exactly one document"
    if (
        doc["tokens_total"]
        != doc["tokens_source"] + doc["tokens_derived"] + doc["tokens_composite"]
    ):
        return {}, "token accounting is broken"
    if sum(doc["tokens_by_class"].values()) != doc["tokens_source"]:
        return {}, "source by-class tally does not sum to the source count"
    if sum(doc["derived_by_kind"].values()) != doc["tokens_derived"]:
        return {}, "derived by-kind tally does not sum to the derived count"

    graph = doc["graph"]
    if graph.get("nodes") != graph.get("fragments", 0) + graph.get("members", 0) + graph.get(
        "classifications", 0
    ):
        return {}, "graph node accounting is broken"

    repeat = doc["repeat_import"]
    if (
        repeat.get("already_present") is not True
        or repeat.get("added_nodes") != 0
        or repeat.get("added_edges") != 0
        or repeat.get("counts_identical") is not True
    ):
        return {}, "repeat import was not an idempotent no-op"

    identity = doc["identity"]
    expected_hex = input_sha256.split(":", 1)[-1]
    if identity.get("source_sha256") != expected_hex:
        return {}, "counts identity does not match the input sha256"

    try:
        assert_no_raw_text(doc)
    except HarnessError:
        return {}, "counts document failed the redaction invariant"
    return doc, None


# --------------------------------------------------------------- process #


def _artifact_path(scratch_dir: Path, relative_path: str) -> Path:
    token = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]
    return scratch_dir / f"counts-{token}.json"


def classify_consumer(result: dict[str, Any], limits: probe.Limits) -> str:
    """Closed outcome for one ``consumer-run`` child (breach beats product exit)."""
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
        if result["peak_rss_kb"] is not None and result["peak_rss_kb"] > limits.peak_rss_kb:
            return "rss_limit_exceeded"
        return "accepted"
    if rc == 5:
        return "source_refusal"
    if rc == 6:
        return "consumer_refusal"
    if rc == 2:
        return "usage_error"
    if rc == 3:
        return "out_unwritable"
    if rc == 4:
        return "input_unreadable"
    if rc == 127:
        return "exec_error"
    return "unknown_exit"


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
    """Run one entry's consumer and return a closed receipt.

    Fail-closed: an unreadable or drifted source, an unrecognised refusal token,
    a resource breach or a failed counts check never yields ``accepted``.
    """
    receipt = _base_receipt(entry, binding, attempt, now())
    source = corpus_root / entry.relative_path
    artifact = _artifact_path(scratch_dir, entry.relative_path)
    stdout_path = scratch_dir / "consumer.stdout"
    stderr_path = scratch_dir / "consumer.stderr"

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
            result = measure(
                [
                    str(bin_path),
                    "--from-xml",
                    str(source),
                    "--out",
                    str(artifact),
                ],
                timeout_s=limits.export_wall_s,
                cwd=ROOT,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
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
                note=f"consumer spawn failed: {type(error).__name__}",
            )

        receipt["wall_s"] = result["wall_s"]
        receipt["peak_rss_kb"] = result["peak_rss_kb"]
        outcome = classify_consumer(result, limits)

        if outcome in ("source_refusal", "consumer_refusal"):
            stderr_text = (
                stderr_path.read_text(encoding="utf-8", errors="replace")
                if stderr_path.exists()
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
                CONSUMER_OUTCOME_TO_INCOMPLETE.get(outcome, "harness_error"),
                note=f"consumer classified {outcome}",
            )

        if not artifact.exists():
            return _finish(receipt, "incomplete", "harness_error", note="counts artifact missing")
        doc, error = validate_counts_doc(
            artifact.read_text(encoding="utf-8", errors="replace"),
            input_sha256=actual_sha256,
        )
        if error is not None:
            return _finish(receipt, "incomplete", "artifact_verify_failed", note=error)

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
        receipt["counts"] = doc
        return _finish(receipt, "accepted", "accepted")
    finally:
        removed = True
        for leftover in (
            artifact,
            Path(str(artifact) + ".tmp"),
            stdout_path,
            stderr_path,
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


def run_consumers(
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
) -> dict[str, Any]:
    """Run one resumable attempt over the manifest entries.

    Entries with a *current* terminal receipt are skipped; stale or incomplete
    entries are recomputed/retried.  The attempt stops as ``budget_exhausted``
    when ``attempt_wall_s`` elapses, or ``disk_guard_stopped`` when free disk
    drops below the abort floor.
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
        "binary_drift": False,
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

    state["summary"] = summarize_receipts(entries, latest)
    if state["status"] == "complete":
        summary = state["summary"]
        if (
            summary["remaining"] > 0
            or summary["incomplete"] > 0
            or summary["terminal"] != summary["entries"]
        ):
            state["status"] = "incomplete"
    state["disk_after"] = probe.disk_snapshot(scratch_dir)
    # Fail closed if the executable changed under the attempt.
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
    checks.append({"id": "binary_present", "path": str(bin_path), "ok": binary_ok})
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
    """Objectively confirm ledger completeness and a single binding tuple."""
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


# ------------------------------------------------------------- proof set #

#: Seed for the deterministic proof subset (S02 probe seed, for traceability).
PROOF_SEED = 22302
#: Entries drawn per top-level corpus subdirectory.
PROOF_PER_SUBDIR = 4

#: Real, git-tracked non-WordML reader fixtures used to validate the closed
#: refusal dictionary against actual product refusal tokens.
PROOF_REFUSAL_FIXTURES = (
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-not-wordml.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-namespace-absent.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-unsupported-schema.xml",
)

PROOF_NON_CLAIMS = NON_CLAIMS + (
    "The proof subset is a deterministic sample of the pinned manifest; its receipt "
    "bindings are snapshot-bound and shift with any tracked-file change.",
    "The SIGTERM interruption is enforced by a real signal to the harness process; the "
    "harness signal handler unwinds the live-poll loop, which SIGKILLs and reaps the "
    "in-flight consumer child, so an interrupted attempt never orphans a consumer.",
    "Whether the pinned corpus emits any typed consumer refusal is a result of the run, "
    "reported by the ledger's refused_by_class, and is never asserted in advance.",
)


@dataclass(frozen=True)
class ProofSubset:
    """A deterministic proof subset derived from the pinned manifest."""

    entries: tuple[probe.Entry, ...]
    subdir_counts: dict[str, int]
    digest: str


def _top_subdir(relative_path: str) -> str:
    return relative_path.split("/", 1)[0]


def select_proof_subset(
    entries: Sequence[probe.Entry],
    *,
    seed: int = PROOF_SEED,
    per_subdir: int = PROOF_PER_SUBDIR,
) -> ProofSubset:
    """Deterministic seeded sample of the smallest per-subdir pool."""
    grouped: dict[str, list[probe.Entry]] = {}
    for entry in entries:
        grouped.setdefault(_top_subdir(entry.relative_path), []).append(entry)

    rng = random.Random(seed)
    chosen: list[probe.Entry] = []
    counts: dict[str, int] = {}
    for top in sorted(grouped):
        bucket = sorted(grouped[top], key=lambda item: (item.bytes, item.relative_path))
        pool = bucket[: max(per_subdir, min(len(bucket), per_subdir * 4))]
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


def write_subset_manifest(
    subset: ProofSubset,
    path: Path,
    *,
    source_header: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a self-contained manifest for the proof subset."""
    total_bytes = sum(entry.bytes for entry in subset.entries)
    max_bytes = max((entry.bytes for entry in subset.entries), default=0)
    header = {
        "schema": MANIFEST_SCHEMA,
        "version": 1,
        "root": (source_header or {}).get("root", "consru_export/consru_export/exports"),
        "counts": {
            "entries": len(subset.entries),
            "total_bytes": total_bytes,
            "max_bytes": max_bytes,
        },
        "subset_of": (source_header or {}).get("inventory_digest"),
        "inventory_digest": subset.digest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(header, ensure_ascii=True, sort_keys=True) + "\n")
        for entry in subset.entries:
            stream.write(
                json.dumps(
                    {
                        "relative_path": entry.relative_path,
                        "sha256": entry.sha256,
                        "bytes": entry.bytes,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
                + "\n"
            )
    return header


def run_harness_subprocess(
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


def _harness_cmd(
    *,
    python: str,
    harness: Path,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    decision_path: Path,
    s03_path: Path,
    scratch_dir: Path,
    receipts_path: Path,
    report_path: Path,
    code_revision: str | None,
    extra: Sequence[str],
) -> list[str]:
    cmd = [
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
        "--s03-baseline",
        str(s03_path),
        "--scratch",
        str(scratch_dir),
        "--receipts",
        str(receipts_path),
        "--report",
        str(report_path),
        "--skip-preflight",
    ]
    if code_revision is not None:
        cmd += ["--code-revision", code_revision]
    return cmd + list(extra)


def _interrupt_run(
    *,
    cmd: Sequence[str],
    receipts_path: Path,
    min_receipts: int = 1,
    poll_s: float = 0.01,
    max_wait_s: float = 60.0,
) -> dict[str, Any]:
    """Start the harness and SIGTERM it once ``min_receipts`` are durable."""
    started = time.monotonic()
    process = subprocess.Popen(
        list(cmd),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    observed = 0
    signalled = False
    while True:
        if process.poll() is not None:
            break
        try:
            observed = len(ReceiptLog(receipts_path).read())
        except HarnessError:
            observed = 0
        if observed >= min_receipts and not signalled:
            process.send_signal(signal.SIGTERM)
            signalled = True
        if time.monotonic() - started > max_wait_s:
            process.kill()
            break
        time.sleep(poll_s)
    stdout, stderr = process.communicate(timeout=30)
    return {
        "rc": process.returncode,
        "signalled": signalled,
        "receipts_at_signal": observed,
        "wall_s": round(time.monotonic() - started, 3),
        "stderr_tail": stderr.strip().splitlines()[-6:],
        "stdout_lines": stdout.strip().splitlines()[-4:],
    }


def prove_resume(
    *,
    manifest_path: Path,
    corpus_root: Path,
    bin_path: Path,
    decision_path: Path,
    s03_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    receipts_path: Path,
    subset: ProofSubset,
    python: str,
    harness: Path,
    enable_interrupt: bool = True,
    enable_refusal_probe: bool = True,
) -> dict[str, Any]:
    """Prove SIGTERM interruption + same-ledger resume + stale recompute."""
    proof_scratch = scratch_dir / "proof"
    proof_scratch.mkdir(parents=True, exist_ok=True)
    subset_manifest = proof_scratch / "subset-manifest.jsonl"
    write_subset_manifest(subset, subset_manifest)
    report_path = proof_scratch / "subset-run.json"

    base_extra = [
        "--resume",
        "--consumer-wall-s",
        "900",
    ]
    code_revision = binding.code_revision

    interruption: dict[str, Any] | None = None
    if enable_interrupt:
        cmd = _harness_cmd(
            python=python,
            harness=harness,
            manifest_path=subset_manifest,
            corpus_root=corpus_root,
            bin_path=bin_path,
            decision_path=decision_path,
            s03_path=s03_path,
            scratch_dir=proof_scratch / "interrupt",
            receipts_path=receipts_path,
            report_path=report_path,
            code_revision=code_revision,
            extra=base_extra,
        )
        outcome = _interrupt_run(cmd=cmd, receipts_path=receipts_path, min_receipts=1)
        partial_receipts = ReceiptLog(receipts_path).read()
        partial_latest = latest_by_path(partial_receipts)
        partial_summary = summarize_receipts(subset.entries, partial_latest)
        interruption = {
            "status": "interrupted"
            if outcome["rc"] in (128 + signal.SIGTERM, 143, -signal.SIGTERM)
            else "not_interrupted",
            "rc": outcome["rc"],
            "signalled": outcome["signalled"],
            "receipts_at_signal": outcome["receipts_at_signal"],
            "wall_s": outcome["wall_s"],
            "partial": partial_summary,
            "stderr_tail": outcome["stderr_tail"],
            "note": (
                "the in-flight entry is recorded incomplete/not_run; every completed "
                "terminal receipt is preserved in the same ledger"
            ),
        }
    else:
        partial_receipts = []

    # Resume the same ledger to completion (bounded chunks so a large subset
    # never exceeds the per-attempt budget).
    resume_attempts: list[dict[str, Any]] = []
    for _ in range(64):
        result = run_harness_subprocess(
            _harness_cmd(
                python=python,
                harness=harness,
                manifest_path=subset_manifest,
                corpus_root=corpus_root,
                bin_path=bin_path,
                decision_path=decision_path,
                s03_path=s03_path,
                scratch_dir=proof_scratch / "resume",
                receipts_path=receipts_path,
                report_path=report_path,
                code_revision=code_revision,
                extra=base_extra,
            )
        )
        resume_attempts.append(
            {"rc": result["rc"], "wall_s": result["wall_s"], "stderr_tail": result["stderr_tail"]}
        )
        if result["rc"] == EXIT_OK:
            break
        if result["rc"] not in (EXIT_NOT_COMPLETE,):
            break

    final_receipts = ReceiptLog(receipts_path).read()
    final_latest = latest_by_path(final_receipts)
    final_summary = summarize_receipts(subset.entries, final_latest)
    verification = verify_ledger(
        entries=subset.entries, receipts=final_receipts, live_binding=binding
    )

    # Stale recompute: mutate a copy's binding and confirm it is recomputed.
    stale = _prove_stale_recompute(
        subset=subset,
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits,
        scratch_dir=proof_scratch / "stale",
        python=python,
        harness=harness,
        decision_path=decision_path,
        s03_path=s03_path,
        code_revision=code_revision,
    )

    preserved_paths = sorted(set(latest_by_path(partial_receipts))) if partial_receipts else []
    sorted(final_latest)
    preserved_current = [
        path
        for path in preserved_paths
        if final_latest.get(path, {}).get("outcome") in TERMINAL_OUTCOMES
    ]

    refusal_probe = None
    if enable_refusal_probe:
        refusal_probe = run_refusal_probe(
            bin_path=bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=proof_scratch / "refusal",
            attempt=1,
        )

    ok = bool(
        (not enable_interrupt or (interruption and interruption["status"] == "interrupted"))
        and final_summary["terminal"] == len(subset.entries)
        and final_summary["remaining"] == 0
        and verification["ok"]
        and stale["stale_recomputed"]
    )
    return {
        "schema": PROOF_SCHEMA,
        "ok": ok,
        "subset": {
            "size": len(subset.entries),
            "subdir_counts": subset.subdir_counts,
            "digest": subset.digest,
            "manifest": str(subset_manifest),
        },
        "binding": binding.as_dict(),
        "receipts_path": str(receipts_path),
        "interruption": interruption,
        "resume_attempts": resume_attempts,
        "preserved_current_receipts": len(preserved_current),
        "final": final_summary,
        "verification": {
            "ok": verification["ok"],
            "terminal": verification["terminal"],
            "distinct_bindings": verification["distinct_bindings"],
            "errors": verification["errors"],
        },
        "stale_recompute": stale,
        "refusal_probe": refusal_probe,
        "r1000_status": "active/unclosed",
        "non_claims": list(PROOF_NON_CLAIMS),
    }


def _prove_stale_recompute(
    *,
    subset: ProofSubset,
    corpus_root: Path,
    bin_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    python: str,
    harness: Path,
    decision_path: Path,
    s03_path: Path,
    code_revision: str,
) -> dict[str, Any]:
    """A receipt whose binary pin drifted is stale and must be recomputed."""
    scratch_dir.mkdir(parents=True, exist_ok=True)
    ledger = scratch_dir / "receipts.jsonl"
    subset_manifest = scratch_dir / "subset-manifest.jsonl"
    write_subset_manifest(subset, subset_manifest)
    report_path = scratch_dir / "run.json"

    # First pass: one entry, real binding.
    first = run_harness_subprocess(
        _harness_cmd(
            python=python,
            harness=harness,
            manifest_path=subset_manifest,
            corpus_root=corpus_root,
            bin_path=bin_path,
            decision_path=decision_path,
            s03_path=s03_path,
            scratch_dir=scratch_dir,
            receipts_path=ledger,
            report_path=report_path,
            code_revision=code_revision,
            extra=["--resume", "--max-entries", "1"],
        )
    )
    before = ReceiptLog(ledger).read()
    before_paths = latest_by_path(before)
    if not before_paths:
        return {"stale_recomputed": False, "reason": "first pass wrote no receipt"}

    # Poison the latest receipt's binary pin so it is stale.
    _mutate_latest_binding(ledger, "binary_sha256", "sha256:" + "0" * 64)
    poisoned = ReceiptLog(ledger).read()

    # Second pass: the stale entry must be recomputed, not skipped.
    second = run_harness_subprocess(
        _harness_cmd(
            python=python,
            harness=harness,
            manifest_path=subset_manifest,
            corpus_root=corpus_root,
            bin_path=bin_path,
            decision_path=decision_path,
            s03_path=s03_path,
            scratch_dir=scratch_dir,
            receipts_path=ledger,
            report_path=report_path,
            code_revision=code_revision,
            extra=["--resume", "--max-entries", "1"],
        )
    )
    after = ReceiptLog(ledger).read()
    after_latest = latest_by_path(after)
    recomputed = [
        path
        for path in before_paths
        if after_latest.get(path, {}).get("binary_sha256") == binding.binary_sha256
    ]
    return {
        "stale_recomputed": bool(recomputed),
        "first_pass_rc": first["rc"],
        "second_pass_rc": second["rc"],
        "receipts_before": len(before),
        "receipts_after": len(after),
        "poisoned_receipts": len(poisoned),
        "recomputed_paths": recomputed,
    }


def _mutate_latest_binding(path: Path, field: str, value: str) -> None:
    log = ReceiptLog(path)
    records = log.read()
    if not records:
        raise HarnessError("ledger is empty")
    records[-1][field] = value
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    os.replace(tmp, path)


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
    """Real typed refusals from real non-WordML inputs through the product path."""
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
        "note": "real non-WordML reader fixtures; whether the pinned corpus emits "
        "refusals is reported by the ledger, never asserted in advance",
    }


# ---------------------------------------------------- repeat-import proof #


def prove_repeat_import(
    *,
    corpus_root: Path,
    bin_path: Path,
    binding: Binding,
    limits: probe.Limits,
    scratch_dir: Path,
    subset: ProofSubset,
    hash_file: Callable[[Path], str] = probe.sha256_file,
    measure: Callable[..., dict[str, Any]] = probe.measure_subprocess,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Repeat the consumer over the same entries and compare counts byte-for-byte."""
    per_entry: list[dict[str, Any]] = []
    all_identical = True
    for index, entry in enumerate(subset.entries):
        first = process_entry(
            entry,
            corpus_root=corpus_root,
            bin_path=bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=scratch_dir / f"pass-a-{index}",
            attempt=1,
            verify_input_after=False,
            hash_file=hash_file,
            measure=measure,
            now=now,
        )
        second = process_entry(
            entry,
            corpus_root=corpus_root,
            bin_path=bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=scratch_dir / f"pass-b-{index}",
            attempt=2,
            verify_input_after=False,
            hash_file=hash_file,
            measure=measure,
            now=now,
        )
        first_counts = first.get("counts")
        second_counts = second.get("counts")
        identical = (
            first["outcome"] == second["outcome"]
            and first_counts is not None
            and second_counts is not None
            and json.dumps(first_counts, sort_keys=True)
            == json.dumps(second_counts, sort_keys=True)
        )
        if not identical:
            all_identical = False
        per_entry.append(
            {
                "relative_path": entry.relative_path,
                "first_outcome": first["outcome"],
                "second_outcome": second["outcome"],
                "counts_identical": identical,
                "counts_digest": "sha256:"
                + hashlib.sha256(
                    json.dumps(first_counts, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if first_counts is not None
                else None,
            }
        )
    return {
        "schema": REPEAT_PROOF_SCHEMA,
        "ok": bool(per_entry) and all_identical,
        "subset": {
            "size": len(subset.entries),
            "digest": subset.digest,
        },
        "binding": binding.as_dict(),
        "entries": per_entry,
        "counts_byte_identical": all_identical,
        "note": "the consumer imports the same materialized JSONL layers twice; the "
        "repeat import is an idempotent no-op and the counts are byte-identical",
        "r1000_status": "active/unclosed",
        "non_claims": list(PROOF_NON_CLAIMS),
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
    s03: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = state.get("summary", {})
    report = {
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
        "s03_baseline_reconciled": s03,
        "r1000_status": "active/unclosed",
        "binary_drift": bool(state.get("binary_drift")),
        "non_claims": list(NON_CLAIMS),
    }
    assert_no_raw_text(report)
    return report


def _recent_attempts(receipts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts: dict[int, dict[str, Any]] = {}
    for receipt in receipts:
        attempt = int(receipt["attempt"])
        record = attempts.setdefault(attempt, {"attempt": attempt, "receipts": 0})
        record["receipts"] += 1
    ordered = [attempts[key] for key in sorted(attempts)]
    return ordered[-20:]


# -------------------------------------------------------------------- cli #


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--bin", dest="bin_path", type=Path, default=DEFAULT_BIN)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--s03-baseline", dest="s03_path", type=Path, default=DEFAULT_S03_BASELINE)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--receipts", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument(
        "--code-revision",
        default=None,
        help="test/ops override for the aggregate code revision (never guessed in production)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M223/S07 consumer acceptance corpus harness")
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
    run_parser.add_argument("--consumer-wall-s", type=float, default=None)

    status_parser = sub.add_parser("status", help="machine-readable progress snapshot")
    _add_common(status_parser)

    verify_parser = sub.add_parser("verify-ledger", help="verify ledger completeness")
    _add_common(verify_parser)

    preflight_parser = sub.add_parser("preflight", help="fail-closed environment preflight")
    _add_common(preflight_parser)

    publish_parser = sub.add_parser("publish", help="publish the live ledger and report")
    _add_common(publish_parser)
    publish_parser.add_argument("--run-out", type=Path, default=DEFAULT_RUN_OUT)
    publish_parser.add_argument("--receipts-out", type=Path, default=DEFAULT_RECEIPTS_OUT)

    prove_parser = sub.add_parser(
        "prove-resume", help="prove SIGTERM interruption, resume and stale recompute"
    )
    _add_common(prove_parser)
    prove_parser.add_argument("--out", type=Path, default=DEFAULT_RESUME_PROOF_OUT)
    prove_parser.add_argument("--seed", type=int, default=PROOF_SEED)
    prove_parser.add_argument("--per-subdir", type=int, default=PROOF_PER_SUBDIR)
    prove_parser.add_argument("--skip-interrupt", action="store_true")
    prove_parser.add_argument("--skip-refusal-probe", action="store_true")

    repeat_parser = sub.add_parser(
        "prove-repeat-import", help="prove repeat import is byte-identical"
    )
    _add_common(repeat_parser)
    repeat_parser.add_argument("--out", type=Path, default=DEFAULT_REPEAT_PROOF_OUT)
    repeat_parser.add_argument("--seed", type=int, default=PROOF_SEED)
    repeat_parser.add_argument("--per-subdir", type=int, default=PROOF_PER_SUBDIR)

    return parser


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    receipts = args.receipts if args.receipts is not None else args.scratch / "receipts.jsonl"
    report = args.report if args.report is not None else args.scratch / "run.json"
    return receipts, report


def _limits_from_decision(
    decision: dict[str, Any], *, consumer_wall_s: float | None
) -> probe.Limits:
    stop = decision["decision"]["stop_thresholds"]
    return probe.Limits(
        export_wall_s=consumer_wall_s if consumer_wall_s is not None else 900.0,
        readback_wall_s=60.0,
        peak_rss_kb=int(stop["peak_rss_kb"]),
        min_free_disk_bytes=int(probe.Limits.min_free_disk_bytes),
        abort_free_disk_bytes=int(probe.Limits.abort_free_disk_bytes),
        max_single_artifact_bytes=int(stop["single_artifact_bytes"]),
        total_budget_wall_s=float(stop["wall_s"]),
    )


def _load_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], list[probe.Entry], dict[str, Any]]:
    decision = load_decision(args.decision)
    probe.sha256_file(args.manifest)
    header, entries = load_manifest(args.manifest)
    s03 = load_s03_baseline(args.s03_path)
    return decision, header, entries, s03


def cmd_run(args: argparse.Namespace) -> int:
    receipts_path, report_path = _resolve_paths(args)
    args.scratch.mkdir(parents=True, exist_ok=True)
    try:
        decision, header, entries, s03 = _load_inputs(args)
        binding = compute_binding(args.bin_path, code_revision=args.code_revision)
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT

    limits = _limits_from_decision(decision, consumer_wall_s=args.consumer_wall_s)
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
                manifest_sha256=probe.sha256_file(args.manifest),
                s03=s03,
            )
            report_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(report, report_path)
            print(
                f"m223-s07-corpus-run: preflight failed: {','.join(preflight_result['failures'])}",
                file=sys.stderr,
            )
            print(json.dumps(preflight_result, ensure_ascii=True))
            return EXIT_PREFLIGHT

    print(
        f"m223-s07-corpus-run: run attempt_wall_s={attempt_wall_s} "
        f"entries={len(entries)} code_revision={binding.code_revision} "
        f"binary_sha256={binding.binary_sha256} resume={bool(args.resume)}",
        file=sys.stderr,
    )

    def on_receipt(receipt: dict[str, Any]) -> None:
        print(
            f"m223-s07-corpus-run: {receipt['relative_path']} -> "
            f"{receipt['outcome']}/{receipt['outcome_class']}",
            file=sys.stderr,
        )

    exit_code = EXIT_OK
    try:
        state = run_consumers(
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

    attempts = _recent_attempts(ReceiptLog(receipts_path).read())
    report = build_run_report(
        state=state,
        header=header,
        manifest_path=args.manifest,
        decision=decision,
        attempts=attempts,
        preflight_result=preflight_result,
        manifest_sha256=probe.sha256_file(args.manifest),
        s03=s03,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(report, report_path)
    print(
        f"m223-s07-corpus-run: status={state['status']} "
        f"accepted={state['summary'].get('accepted')} refused={state['summary'].get('refused')} "
        f"incomplete={state['summary'].get('incomplete')} "
        f"remaining={state['summary'].get('remaining')}",
        file=sys.stderr,
    )
    return exit_code


def cmd_status(args: argparse.Namespace) -> int:
    receipts_path, _ = _resolve_paths(args)
    try:
        _decision, header, entries, _s03 = _load_inputs(args)
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    try:
        receipts = ReceiptLog(receipts_path).read()
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
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
        _decision, header, entries, _s03 = _load_inputs(args)
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    try:
        receipts = ReceiptLog(receipts_path).read()
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
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
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_PREFLIGHT
    result = preflight(decision=decision, bin_path=args.bin_path, scratch_dir=args.scratch)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if not result["ok"]:
        print(
            f"m223-s07-corpus-run: preflight failed: {','.join(result['failures'])}",
            file=sys.stderr,
        )
        return EXIT_PREFLIGHT
    return EXIT_OK


def cmd_publish(args: argparse.Namespace) -> int:
    receipts_path, report_path = _resolve_paths(args)
    if not receipts_path.is_file():
        print(f"m223-s07-corpus-run: no live ledger at {receipts_path}", file=sys.stderr)
        return EXIT_VERIFY_FAILED
    if not report_path.is_file():
        print(f"m223-s07-corpus-run: no live report at {report_path}", file=sys.stderr)
        return EXIT_VERIFY_FAILED
    receipts = ReceiptLog(receipts_path).read()
    for record in receipts:
        assert_no_raw_text(record)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert_no_raw_text(report)
    args.receipts_out.parent.mkdir(parents=True, exist_ok=True)
    with args.receipts_out.open("w", encoding="utf-8") as stream:
        for record in receipts:
            stream.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    _write_json(report, args.run_out)
    print(
        json.dumps(
            {
                "schema": RUN_SCHEMA,
                "receipts_out": str(args.receipts_out),
                "run_out": str(args.run_out),
                "receipts": len(receipts),
                "status": report.get("status"),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return EXIT_OK


def cmd_prove_resume(args: argparse.Namespace) -> int:
    receipts_path = (
        args.receipts if args.receipts is not None else args.scratch / "proof" / "receipts.jsonl"
    )
    args.scratch.mkdir(parents=True, exist_ok=True)
    try:
        decision, _header, entries, _s03 = _load_inputs(args)
        binding = compute_binding(args.bin_path, code_revision=args.code_revision)
        limits = _limits_from_decision(decision, consumer_wall_s=None)
        subset = select_proof_subset(entries, seed=args.seed, per_subdir=args.per_subdir)
        proof = prove_resume(
            manifest_path=args.manifest,
            corpus_root=args.corpus_root,
            bin_path=args.bin_path,
            decision_path=args.decision,
            s03_path=args.s03_path,
            binding=binding,
            limits=limits,
            scratch_dir=args.scratch,
            receipts_path=receipts_path,
            subset=subset,
            python=sys.executable,
            harness=Path(__file__).resolve(),
            enable_interrupt=not args.skip_interrupt,
            enable_refusal_probe=not args.skip_refusal_probe,
        )
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_VERIFY_FAILED

    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(proof, args.out)
    print(
        json.dumps(
            {
                "schema": PROOF_SCHEMA,
                "subset_size": proof["subset"]["size"],
                "ok": proof["ok"],
                "final": proof["final"],
                "interruption": (proof["interruption"] or {}).get("status"),
                "out": str(args.out),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return EXIT_OK if proof["ok"] else EXIT_VERIFY_FAILED


def cmd_prove_repeat_import(args: argparse.Namespace) -> int:
    args.scratch.mkdir(parents=True, exist_ok=True)
    try:
        decision, _header, entries, _s03 = _load_inputs(args)
        binding = compute_binding(args.bin_path, code_revision=args.code_revision)
        limits = _limits_from_decision(decision, consumer_wall_s=None)
        subset = select_proof_subset(entries, seed=args.seed, per_subdir=args.per_subdir)
        proof = prove_repeat_import(
            corpus_root=args.corpus_root,
            bin_path=args.bin_path,
            binding=binding,
            limits=limits,
            scratch_dir=args.scratch / "repeat-import",
            subset=subset,
        )
    except HarnessError as error:
        print(f"m223-s07-corpus-run: fail-closed: {error}", file=sys.stderr)
        return EXIT_VERIFY_FAILED

    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(proof, args.out)
    print(
        json.dumps(
            {
                "schema": REPEAT_PROOF_SCHEMA,
                "subset_size": proof["subset"]["size"],
                "ok": proof["ok"],
                "counts_byte_identical": proof["counts_byte_identical"],
                "out": str(args.out),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return EXIT_OK if proof["ok"] else EXIT_VERIFY_FAILED


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
    if args.command == "publish":
        return cmd_publish(args)
    if args.command == "prove-resume":
        return cmd_prove_resume(args)
    if args.command == "prove-repeat-import":
        return cmd_prove_repeat_import(args)
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
