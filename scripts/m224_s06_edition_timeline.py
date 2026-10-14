#!/usr/bin/env python3
"""Corpus edition-timeline driver for M224/S06 (T05).

Reads the pinned S02 corpus manifest, selects every ``npa/law_2013-04-05_44-fz``
edition (expected 118), and for each edition runs the *producer* half exactly
once (``cleaned-project export`` turns the source XML into a cleaned-wire JSONL
artifact).  The *consumer* half (``edition-timeline``) then reads **only** that
materialized JSONL layer: one pass folds the ascending 118-edition structural
timeline (``--mode timeline``) and one pass adds the per-edition AST
presence + text CTV layer (``--mode timeline --ctv``).  The producer never runs
downstream of the fold, so ``xml_reparse`` is false by construction -- the
consumer has no XML decoding surface at all (no ``--from-xml``).

The driver is *orchestration and aggregation only*: every number it publishes is
copied out of a counts payload produced by the Rust consumer and the two counts
payloads are joined on ``edition_number``.  The timeline/CTV logic is never
re-implemented in Python.  The tracked artifact carries counts, closed-vocabulary
tokens, hashes and paths only -- no decoded text ever reaches it (ASCII by
construction via ``ensure_ascii``).

Fail-closed surfaces (a harness error, never a skip): missing manifest, a
manifest header with the wrong schema, a manifest whose sha256 does not match
the pin, a corpus that does not yield exactly 118 selected editions, missing
corpus root, missing release binary after a rebuild attempt, a manifest row
whose ``relative_path`` is not a safe corpus-relative path, an XML whose bytes
do not match the manifest sha256, export failure or timeout, consumer refusal,
a payload with the wrong schema/keys, an accounting-identity violation, a
non-zero per-edition drift, a non-monotonic transition other than the
documented 0036->0037 residual, an output that is not writable, and ``--check``
byte drift.

``--check`` re-runs the derivation (reusing the manifest/binary-pinned producer
cache) and byte-compares the live render against the tracked artifact without
writing (MEM1459 pattern); drift is exit 6.

Boundary: this is a bounded single-act (44-FZ, 118 editions) corpus proof, not a
multi-work corpus timeline and it does not close R1000 (``r1000_status`` stays
``active/unclosed``); R070 stays active (structural timeline, no commencement
or transitional proof).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m224-s06-edition-timeline/v1"
VERSION = 1
KIND = "edition_timeline_corpus"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
#: The manifest is pinned by content sha256; a drifted manifest is a harness
#: error, never a silent re-derivation over unpinned corpus bytes.
EXPECTED_MANIFEST_SHA256 = "sha256:565ec492b42d6b2f2a652cb32e8423eba56c7f376596c35239991db2d72e429c"
TIMELINE_SCHEMA = "edition-timeline/v1"
AST_CTV_SCHEMA = "edition-ast-ctv/v1"
R1000_STATUS = "active/unclosed"

#: The single selected work: 44-FZ editions under this corpus-relative prefix.
EDITION_PREFIX = "npa/law_2013-04-05_44-fz/edition-"
#: Pinned expected edition count (the manifest yields exactly this many rows).
EXPECTED_EDITIONS = 118
#: Pinned work slug the consumer derives for the local historical re-bind.
EXPECTED_SLUG = "44-fz"
#: Pinned embedded registry binding count for the 44-FZ work.
EXPECTED_REGISTRY_BINDINGS = 102
#: The single documented non-monotonic transition (D767 residual).
EXPECTED_NON_MONOTONIC = (36, 37)

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_ONTOLOGY = ROOT / "prd/architecture/kb-ontology.yaml"
DEFAULT_REGISTRY = ROOT / "prd/architecture/kb-hierarchy-registry.yaml"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m224-s06-edition-timeline.json"
DEFAULT_PRODUCER_BIN = ROOT / "target/release/cleaned-project"
DEFAULT_CONSUMER_BIN = ROOT / "target/release/edition-timeline"
DEFAULT_CACHE_DIR = ROOT / "target/m224-s06-edition-timeline-cache"

#: Per-edition payload keys emitted by the T03 timeline consumer (exact set).
TIMELINE_KEYS = frozenset(
    {
        "schema",
        "kind",
        "slug",
        "registry_bindings",
        "historical_rebinds",
        "editions",
        "totals",
        "non_monotonic_transitions",
        "per_edition",
        "r1000_status",
        "non_claims",
    }
)
TIMELINE_TOTAL_KEYS = frozenset(
    {
        "markers",
        "drafts",
        "applied",
        "applied_attach",
        "applied_detach",
        "quarantined",
        "drift",
        "missing",
        "phantom",
        "max_nodes",
    }
)
TIMELINE_POINT_KEYS = frozenset(
    {
        "edition_number",
        "effect_day",
        "applied_day",
        "markers",
        "drafts",
        "applied",
        "applied_attach",
        "applied_detach",
        "quarantined",
        "drift",
        "missing",
        "phantom",
        "roots",
        "nodes",
    }
)
#: Per-edition payload keys emitted by the T04 AST/CTV consumer (exact set).
AST_CTV_KEYS = frozenset(
    {
        "schema",
        "kind",
        "slug",
        "registry_bindings",
        "historical_rebinds",
        "editions",
        "totals",
        "per_edition",
        "r1000_status",
        "non_claims",
    }
)
AST_CTV_TOTAL_KEYS = frozenset(
    {"admitted", "visible", "hidden", "ctv_resolved", "ctv_unknown", "ctv_conflict"}
)
AST_CTV_POINT_KEYS = frozenset(
    {
        "edition_number",
        "effect_day",
        "admitted",
        "visible",
        "hidden",
        "ctv_resolved",
        "ctv_unknown",
        "ctv_conflict",
    }
)

#: Evidence redaction: every artifact string is a path, hash, token or
#: snake_case / slash label.  Decoded corpus text never fits this closed shape.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:@]{1,240}$")
FORBIDDEN_KEYS = frozenset({"text", "literal", "decoded", "content", "detail"})

NON_CLAIMS = (
    "not_r1000_closure",
    "structural_timeline_is_not_legal_amendment_correctness",
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml",
    "no_xml_reparse_in_the_timeline_or_ctv_layer",
    "historical_rebind_is_a_local_fixture_decision_it_never_edits_the_embedded_registry",
    "effect_day_prefers_from_date_else_rev_date_process_truth_not_legal_truth",
    "presence_log_is_oracle_synthesized_not_expression_inheritance",
    "bounded_single_corpus_act_44fz_not_tsg_s6_not_applicable",
    "practice_courts_and_fas_are_non_normative_and_outside_the_timeline",
    "counts_only_no_decoded_text",
    "r070_stays_active_only_a_structural_timeline_is_claimed",
)

#: Exit codes (mirrors the T03/T04 consumer contract 0/2/3/4/5 and adds the
#: drift code 6 the plan assigns to ``--check``).
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INPUT_UNREADABLE = 3
EXIT_OUT_UNWRITABLE = 4
EXIT_WIRE_REFUSED = 5
EXIT_DRIFT = 6

DEFAULT_PRODUCER_TIMEOUT_S = 300.0
DEFAULT_CONSUMER_TIMEOUT_S = 3600.0
DEFAULT_BUDGET_WALL_S = 7200.0
DEFAULT_PRODUCER_WORKERS = 8


class DriverHarnessError(RuntimeError):
    """Fail-closed harness failure: never a skip, never a silent pass."""

    def __init__(self, message: str, exit_code: int = EXIT_WIRE_REFUSED) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class Entry:
    """One accepted manifest entry (relative to the corpus root)."""

    relative_path: str
    sha256: str
    bytes: int


@dataclass
class Edition:
    """One selected edition with its materialized cleaned-wire artifact."""

    edition_number: int
    relative_path: str
    xml_path: Path
    wire_path: Path
    marker: str = field(default="")


# --------------------------------------------------------------- manifest #


def parse_manifest(path: Path) -> tuple[dict[str, Any], list[Entry]]:
    """Read the S02 JSONL manifest: header record + one entry per file."""
    header: dict[str, Any] | None = None
    entries: list[Entry] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if header is None:
                if record.get("schema") != MANIFEST_SCHEMA:
                    raise DriverHarnessError(
                        f"driver harness error: unexpected manifest schema {record.get('schema')!r}",
                        EXIT_INPUT_UNREADABLE,
                    )
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
        raise DriverHarnessError(
            "driver harness error: manifest has no header record", EXIT_INPUT_UNREADABLE
        )
    if not entries:
        raise DriverHarnessError(
            "driver harness error: manifest has no entries", EXIT_INPUT_UNREADABLE
        )
    return header, entries


def edition_number_from_path(relative_path: str) -> int:
    """Extract the zero-padded edition number from an edition file name.

    ``npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_<hex>.xml``
    -> ``118``.  A path without the closed ``edition-<digits>_`` shape is a
    harness error, never a silent skip.
    """
    name = PurePosixPath(relative_path).name
    match = re.match(r"^edition-(\d{4})_", name)
    if match is None:
        raise DriverHarnessError(
            f"driver harness error: edition file name is not edition-<dddd>_: {name}",
            EXIT_INPUT_UNREADABLE,
        )
    return int(match.group(1))


def select_editions(entries: list[Entry], expected: int = EXPECTED_EDITIONS) -> list[Entry]:
    """Select and ascending-sort the 44-FZ edition rows (fail-closed on count)."""
    selected = [entry for entry in entries if entry.relative_path.startswith(EDITION_PREFIX)]
    if len(selected) != expected:
        raise DriverHarnessError(
            f"driver harness error: manifest yields {len(selected)} editions under "
            f"{EDITION_PREFIX!r}, expected {expected}",
            EXIT_INPUT_UNREADABLE,
        )
    numbers = sorted(edition_number_from_path(entry.relative_path) for entry in selected)
    if len(set(numbers)) != len(numbers):
        raise DriverHarnessError(
            "driver harness error: duplicate edition numbers in the manifest selection",
            EXIT_INPUT_UNREADABLE,
        )
    selected.sort(key=lambda entry: edition_number_from_path(entry.relative_path))
    return selected


def validate_relative_path(relative_path: str) -> None:
    """Reject a manifest row whose path cannot be safely joined to the root.

    Defence in depth (S05/S06 threat model): a ``..`` component, an absolute
    path, a backslash, or a non-ASCII/control character is a harness error,
    never a skip.  The TSV trust boundary (Q3 gap 1) is closed here: every
    path the driver hands the consumer was validated against the pinned
    manifest before the join.
    """
    if not relative_path or relative_path.startswith("/") or "\\" in relative_path:
        raise DriverHarnessError(
            "driver harness error: unsafe corpus-relative path (absolute/empty/backslash)",
            EXIT_INPUT_UNREADABLE,
        )
    if not relative_path.isascii():
        raise DriverHarnessError(
            "driver harness error: unsafe corpus-relative path (non-ASCII)",
            EXIT_INPUT_UNREADABLE,
        )
    if any(ord(character) < 0x20 for character in relative_path):
        raise DriverHarnessError(
            "driver harness error: unsafe corpus-relative path (control character)",
            EXIT_INPUT_UNREADABLE,
        )
    parts = PurePosixPath(relative_path).parts
    if any(part in ("..", ".") for part in parts):
        raise DriverHarnessError(
            "driver harness error: unsafe corpus-relative path (dot component)",
            EXIT_INPUT_UNREADABLE,
        )


# ------------------------------------------------------------------ hashes #


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def relative_label(path: Path) -> str:
    """Repo-relative posix label for evidence paths (absolute fallback)."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def ensure_release_binary(bin_path: Path, package: str, name: str) -> None:
    """Use the existing release binary, else build it; missing = fail-closed."""
    if bin_path.is_file():
        return
    build = subprocess.run(
        ["cargo", "build", "--release", "-p", package, "--bin", name, "--offline"],
        cwd=ROOT,
        capture_output=True,
    )
    if build.returncode != 0 or not bin_path.is_file():
        raise DriverHarnessError(
            "driver harness error: release binary missing after cargo build "
            f"(rc={build.returncode})",
            EXIT_INPUT_UNREADABLE,
        )


# ------------------------------------------------------------- subprocesses #


def run_producer(producer_bin: Path, xml_path: Path, out_path: Path, timeout_s: float) -> None:
    """Run ``cleaned-project export --from-xml`` to materialize the JSONL layer."""
    try:
        result = subprocess.run(
            [
                str(producer_bin),
                "export",
                "--from-xml",
                str(xml_path),
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as error:
        raise DriverHarnessError(
            f"driver harness error: export timeout after {timeout_s}s for {xml_path.name}"
        ) from error
    except OSError as error:
        raise DriverHarnessError(
            f"driver harness error: export spawn failed: {type(error).__name__}"
        ) from error
    if result.returncode != 0 or not out_path.is_file():
        raise DriverHarnessError(
            f"driver harness error: export refused rc={result.returncode} for {xml_path.name}"
        )


def run_consumer(
    consumer_bin: Path,
    tsv_path: Path,
    mode_args: list[str],
    out_path: Path,
    timeout_s: float,
    label: str,
) -> dict[str, Any]:
    """Run one JSONL-only consumer lane and parse its counts payload.

    The consumer exit code is mapped onto the driver contract: ``2`` usage,
    ``3`` input unreadable, ``4`` out unwritable, anything else wire-refused.
    """
    command = [str(consumer_bin), "--editions", str(tsv_path), *mode_args, "--out", str(out_path)]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as error:
        raise DriverHarnessError(
            f"driver harness error: {label} consumer timeout after {timeout_s}s"
        ) from error
    except OSError as error:
        raise DriverHarnessError(
            f"driver harness error: {label} consumer spawn failed: {type(error).__name__}"
        ) from error
    if result.returncode != 0 or not out_path.is_file():
        mapped = {
            2: EXIT_USAGE,
            3: EXIT_INPUT_UNREADABLE,
            4: EXIT_OUT_UNWRITABLE,
        }.get(result.returncode, EXIT_WIRE_REFUSED)
        raise DriverHarnessError(
            f"driver harness error: {label} consumer refused rc={result.returncode}", mapped
        )
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DriverHarnessError(
            f"driver harness error: {label} consumer payload is not JSON"
        ) from error


# ------------------------------------------------------- payload validation #


def _require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DriverHarnessError(f"driver harness error: {label} is not a non-negative int")
    return value


def _require_exact_keys(record: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise DriverHarnessError(f"driver harness error: {label} is not an object")
    if set(record) != keys:
        missing = sorted(keys - set(record))
        extra = sorted(set(record) - keys)
        raise DriverHarnessError(
            f"driver harness error: {label} keys drift (missing={missing}, extra={extra})"
        )
    return record


def validate_timeline_payload(
    payload: dict[str, Any], expected_editions: int = EXPECTED_EDITIONS
) -> None:
    """Fail-closed schema, key-set and accounting check on the timeline payload."""
    _require_exact_keys(payload, TIMELINE_KEYS, "timeline payload")
    if payload["schema"] != TIMELINE_SCHEMA:
        raise DriverHarnessError(
            f"driver harness error: unexpected timeline schema {payload['schema']!r}"
        )
    if payload["r1000_status"] != R1000_STATUS:
        raise DriverHarnessError(
            "driver harness error: timeline r1000_status is not active/unclosed"
        )
    if payload["slug"] != EXPECTED_SLUG:
        raise DriverHarnessError(f"driver harness error: timeline slug {payload['slug']!r}")
    if payload["registry_bindings"] != EXPECTED_REGISTRY_BINDINGS:
        raise DriverHarnessError(
            f"driver harness error: timeline registry_bindings {payload['registry_bindings']!r}"
        )
    editions = _require_int(payload["editions"], "timeline editions")
    if editions != expected_editions:
        raise DriverHarnessError(
            f"driver harness error: timeline editions {editions} != {expected_editions}"
        )
    points = payload["per_edition"]
    if not isinstance(points, list) or len(points) != editions:
        raise DriverHarnessError("driver harness error: timeline per_edition length mismatch")
    totals = _require_exact_keys(payload["totals"], TIMELINE_TOTAL_KEYS, "timeline totals")
    for key in TIMELINE_TOTAL_KEYS:
        _require_int(totals[key], f"timeline totals.{key}")
    seen: dict[str, int] = {key: 0 for key in TIMELINE_TOTAL_KEYS}
    seen["max_nodes"] = 0
    for point in points:
        record = _require_exact_keys(point, TIMELINE_POINT_KEYS, "timeline per_edition point")
        for key in TIMELINE_POINT_KEYS:
            _require_int(record[key], f"timeline per_edition.{key}")
        if record["drift"] != record["missing"] + record["phantom"]:
            raise DriverHarnessError("driver harness error: timeline drift != missing + phantom")
        if record["applied"] != record["applied_attach"] + record["applied_detach"]:
            raise DriverHarnessError(
                "driver harness error: timeline applied != applied_attach + applied_detach"
            )
        if record["applied"] + record["quarantined"] != record["drafts"]:
            raise DriverHarnessError(
                "driver harness error: timeline applied + quarantined != drafts"
            )
        for key in TIMELINE_TOTAL_KEYS:
            if key == "max_nodes":
                seen[key] = max(seen[key], record["nodes"])
            else:
                seen[key] = seen[key] + record[key]
    for key in TIMELINE_TOTAL_KEYS:
        if seen[key] != totals[key]:
            raise DriverHarnessError(f"driver harness error: timeline totals.{key} does not sum")


def validate_ast_ctv_payload(
    payload: dict[str, Any], expected_editions: int = EXPECTED_EDITIONS
) -> None:
    """Fail-closed schema, key-set and accounting check on the AST/CTV payload."""
    _require_exact_keys(payload, AST_CTV_KEYS, "ast-ctv payload")
    if payload["schema"] != AST_CTV_SCHEMA:
        raise DriverHarnessError(
            f"driver harness error: unexpected ast-ctv schema {payload['schema']!r}"
        )
    if payload["r1000_status"] != R1000_STATUS:
        raise DriverHarnessError(
            "driver harness error: ast-ctv r1000_status is not active/unclosed"
        )
    if payload["slug"] != EXPECTED_SLUG:
        raise DriverHarnessError(f"driver harness error: ast-ctv slug {payload['slug']!r}")
    editions = _require_int(payload["editions"], "ast-ctv editions")
    if editions != expected_editions:
        raise DriverHarnessError(
            f"driver harness error: ast-ctv editions {editions} != {expected_editions}"
        )
    points = payload["per_edition"]
    if not isinstance(points, list) or len(points) != editions:
        raise DriverHarnessError("driver harness error: ast-ctv per_edition length mismatch")
    totals = _require_exact_keys(payload["totals"], AST_CTV_TOTAL_KEYS, "ast-ctv totals")
    for key in AST_CTV_TOTAL_KEYS:
        _require_int(totals[key], f"ast-ctv totals.{key}")
    seen = {key: 0 for key in AST_CTV_TOTAL_KEYS}
    for point in points:
        record = _require_exact_keys(point, AST_CTV_POINT_KEYS, "ast-ctv per_edition point")
        for key in AST_CTV_POINT_KEYS:
            _require_int(record[key], f"ast-ctv per_edition.{key}")
        if record["visible"] + record["hidden"] != record["admitted"]:
            raise DriverHarnessError("driver harness error: ast-ctv visible + hidden != admitted")
        for key in AST_CTV_TOTAL_KEYS:
            seen[key] = seen[key] + record[key]
    for key in AST_CTV_TOTAL_KEYS:
        if seen[key] != totals[key]:
            raise DriverHarnessError(f"driver harness error: ast-ctv totals.{key} does not sum")


# -------------------------------------------------------------- redaction #


def redaction_check(artifact: dict[str, Any]) -> None:
    """Fail-closed before writing: only counts/hashes/paths/tokens may ship."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN_KEYS:
                    raise DriverHarnessError(
                        f"driver harness error: forbidden artifact key {key!r}",
                        EXIT_OUT_UNWRITABLE,
                    )
                if not SAFE_STRING.match(key):
                    raise DriverHarnessError(
                        f"driver harness error: unsafe artifact key {key!r}", EXIT_OUT_UNWRITABLE
                    )
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, bool):
            return
        elif isinstance(node, int):
            return
        elif isinstance(node, str) and not SAFE_STRING.match(node):
            raise DriverHarnessError(
                "driver harness error: unsafe artifact string (redaction guard)",
                EXIT_OUT_UNWRITABLE,
            )

    walk(artifact)


# ---------------------------------------------------------------- harness #


def materialize(
    editions: list[Edition],
    args: argparse.Namespace,
    wire_dir: Path,
    started: float,
) -> None:
    """Producer half: materialize one cleaned-wire JSONL per edition.

    Every XML is verified against its pinned manifest sha256 before the producer
    touches it (a drifted source is a harness error).  A cached artifact whose
    key matches the producer binary + source sha is reused (the manifest-pinned
    cache the plan sanctions); otherwise the producer runs.  Exports are
    independent per edition, so they run on a bounded worker pool.
    """

    def one(edition: Edition) -> None:
        if time.monotonic() - started > args.budget_wall_s:
            raise DriverHarnessError(
                f"driver harness error: budget wall {args.budget_wall_s}s exceeded"
            )
        if not edition.xml_path.is_file():
            raise DriverHarnessError(
                f"driver harness error: corpus file not found: {edition.relative_path}",
                EXIT_INPUT_UNREADABLE,
            )
        actual = sha256_file(edition.xml_path)
        if actual != edition.marker:
            raise DriverHarnessError(
                f"driver harness error: corpus file sha256 drifted: {edition.relative_path}",
                EXIT_INPUT_UNREADABLE,
            )
        if not (
            args.use_cache and edition.wire_path.is_file() and edition.wire_path.stat().st_size > 0
        ):
            run_producer(
                args.producer_bin, edition.xml_path, edition.wire_path, args.producer_timeout_s
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.producer_workers) as pool:
        futures = [pool.submit(one, edition) for edition in editions]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def build_tsv(editions: list[Edition], tsv_path: Path) -> None:
    """Write the ``edition_number<TAB>corpus_path<TAB>cleaned_wire`` TSV."""
    lines = []
    for edition in editions:
        lines.append(f"{edition.edition_number}\t{edition.relative_path}\t{edition.wire_path}\n")
    try:
        tsv_path.write_text("".join(lines), encoding="ascii")
    except OSError as error:
        raise DriverHarnessError(
            f"driver harness error: editions TSV is not writable: {error}", EXIT_OUT_UNWRITABLE
        ) from error


def derive(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run the producer and both consumer lanes, then merge the counts."""
    started = time.monotonic()

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        raise DriverHarnessError(
            f"driver harness error: manifest not found: {manifest_path}", EXIT_INPUT_UNREADABLE
        )
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise DriverHarnessError(
            f"driver harness error: manifest sha256 does not match the pin ({manifest_sha})",
            EXIT_INPUT_UNREADABLE,
        )
    header, entries = parse_manifest(manifest_path)

    corpus_root: Path = args.corpus_root or ROOT / str(header["root"])
    if not corpus_root.is_dir():
        raise DriverHarnessError(
            f"driver harness error: corpus root not found: {corpus_root}", EXIT_INPUT_UNREADABLE
        )

    for label, path in (("ontology", args.ontology), ("registry", args.registry)):
        if not path.is_file():
            raise DriverHarnessError(
                f"driver harness error: {label} not found: {path}", EXIT_INPUT_UNREADABLE
            )

    selected = select_editions(entries)

    if args.use_cache:
        try:
            args.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise DriverHarnessError(
                f"driver harness error: cache directory is not writable: {error}",
                EXIT_OUT_UNWRITABLE,
            ) from error
        producer_key = sha256_file(args.producer_bin)[len("sha256:") : 16]
        wire_dir = args.cache_dir / producer_key
        wire_dir.mkdir(parents=True, exist_ok=True)
    else:
        wire_dir = Path(tempfile.mkdtemp(prefix="m224-s06-edition-timeline-"))

    editions: list[Edition] = []
    for entry in selected:
        validate_relative_path(entry.relative_path)
        number = edition_number_from_path(entry.relative_path)
        wire_name = f"{entry.sha256[len('sha256:') :]}.jsonl"
        editions.append(
            Edition(
                edition_number=number,
                relative_path=entry.relative_path,
                xml_path=corpus_root / entry.relative_path,
                wire_path=wire_dir / wire_name,
                marker=entry.sha256,
            )
        )

    try:
        materialize(editions, args, wire_dir, started)
        tsv_path = wire_dir / "editions.tsv"
        build_tsv(editions, tsv_path)
        if args.tsv_out is not None:
            try:
                args.tsv_out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tsv_path, args.tsv_out)
            except OSError as error:
                raise DriverHarnessError(
                    f"driver harness error: --tsv-out is not writable: {error}",
                    EXIT_OUT_UNWRITABLE,
                ) from error
        run_dir = Path(tempfile.mkdtemp(prefix="m224-s06-lanes-"))
        try:
            timeline_json = run_dir / "timeline.json"
            ctv_json = run_dir / "ctv.json"
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                timeline_future = pool.submit(
                    run_consumer,
                    args.consumer_bin,
                    tsv_path,
                    ["--mode", "timeline"],
                    timeline_json,
                    args.consumer_timeout_s,
                    "timeline",
                )
                ctv_future = pool.submit(
                    run_consumer,
                    args.consumer_bin,
                    tsv_path,
                    ["--mode", "timeline", "--ctv"],
                    ctv_json,
                    args.consumer_timeout_s,
                    "ast-ctv",
                )
                timeline = timeline_future.result()
                ast_ctv = ctv_future.result()
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)
    finally:
        if not args.use_cache and not args.keep_wire:
            shutil.rmtree(wire_dir, ignore_errors=True)

    validate_timeline_payload(timeline)
    validate_ast_ctv_payload(ast_ctv)

    # Join the two lanes on edition_number (both already ascending).
    timeline_points = {point["edition_number"]: point for point in timeline["per_edition"]}
    ctv_points = {point["edition_number"]: point for point in ast_ctv["per_edition"]}
    if set(timeline_points) != set(ctv_points):
        raise DriverHarnessError("driver harness error: timeline and ast-ctv edition sets differ")

    per_edition: list[dict[str, Any]] = []
    drift_nonzero = 0
    effect_days: set[int] = set()
    for number in sorted(timeline_points):
        tpoint = timeline_points[number]
        cpoint = ctv_points[number]
        if tpoint["effect_day"] != cpoint["effect_day"]:
            raise DriverHarnessError(
                f"driver harness error: effect_day mismatch for edition {number}"
            )
        if tpoint["drift"] != 0:
            drift_nonzero += 1
        effect_days.add(tpoint["effect_day"])
        per_edition.append(
            {
                "edition_number": number,
                "effect_day": tpoint["effect_day"],
                "markers": tpoint["markers"],
                "drafts": tpoint["drafts"],
                "drift": tpoint["drift"],
                "missing": tpoint["missing"],
                "phantom": tpoint["phantom"],
                "roots": tpoint["roots"],
                "nodes": tpoint["nodes"],
                "ctv_resolved": cpoint["ctv_resolved"],
                "ctv_unknown": cpoint["ctv_unknown"],
                "ctv_conflict": cpoint["ctv_conflict"],
                "visible": cpoint["visible"],
                "hidden": cpoint["hidden"],
            }
        )

    if drift_nonzero != 0:
        raise DriverHarnessError(
            f"driver harness error: {drift_nonzero} edition(s) carry non-zero drift"
        )
    transitions = timeline["non_monotonic_transitions"]
    if (
        len(transitions) != 1
        or (
            transitions[0].get("from_edition"),
            transitions[0].get("to_edition"),
        )
        != EXPECTED_NON_MONOTONIC
    ):
        raise DriverHarnessError(
            "driver harness error: non-monotonic transitions are not the documented 0036->0037 residual"
        )
    if len(effect_days) != EXPECTED_EDITIONS:
        raise DriverHarnessError(
            f"driver harness error: {len(effect_days)} distinct effect days != {EXPECTED_EDITIONS}"
        )

    totals = dict(timeline["totals"])
    totals.update(ast_ctv["totals"])

    evidence = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": KIND,
        "non_claims": list(NON_CLAIMS),
        "manifest_path": relative_label(manifest_path),
        "manifest_sha256": manifest_sha,
        "manifest_entries": len(entries),
        "inventory_digest": header.get("inventory_digest", ""),
        "corpus_root": relative_label(corpus_root),
        "edition_prefix": EDITION_PREFIX,
        "producer_binary_path": relative_label(args.producer_bin),
        "producer_binary_sha256": sha256_file(args.producer_bin),
        "consumer_binary_path": relative_label(args.consumer_bin),
        "consumer_binary_sha256": sha256_file(args.consumer_bin),
        "ontology_path": relative_label(args.ontology),
        "ontology_sha256": sha256_file(args.ontology),
        "registry_path": relative_label(args.registry),
        "registry_sha256": sha256_file(args.registry),
        "editions": len(per_edition),
        "slug": timeline["slug"],
        "registry_bindings": timeline["registry_bindings"],
        "historical_rebinds": timeline["historical_rebinds"],
        "distinct_effect_days": len(effect_days),
        "drift_nonzero_count": drift_nonzero,
        "totals": dict(sorted(totals.items())),
        "per_edition": per_edition,
        "non_monotonic_transitions": transitions,
        "xml_reparse": False,
        "r1000_status": R1000_STATUS,
    }
    redaction_check(evidence)
    return evidence, timeline, ast_ctv


def render_artifact(evidence: dict[str, Any]) -> str:
    """Canonical deterministic ASCII render of the edition-timeline artifact."""
    return json.dumps(evidence, indent=2, ensure_ascii=True) + "\n"


# -------------------------------------------------------------------- cli #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--producer-bin", type=Path, default=DEFAULT_PRODUCER_BIN, dest="producer_bin"
    )
    parser.add_argument(
        "--consumer-bin", type=Path, default=DEFAULT_CONSUMER_BIN, dest="consumer_bin"
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, dest="cache_dir")
    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="use_cache",
        help="materialize into a throwaway temp directory instead of the pinned cache",
    )
    parser.add_argument(
        "--keep-wire",
        action="store_true",
        help="keep the temp wire directory (debugging only; ignored with the cache)",
    )
    parser.add_argument("--tsv-out", type=Path, default=None, dest="tsv_out")
    parser.add_argument("--producer-workers", type=int, default=DEFAULT_PRODUCER_WORKERS)
    parser.add_argument("--producer-timeout-s", type=float, default=DEFAULT_PRODUCER_TIMEOUT_S)
    parser.add_argument("--consumer-timeout-s", type=float, default=DEFAULT_CONSUMER_TIMEOUT_S)
    parser.add_argument("--budget-wall-s", type=float, default=DEFAULT_BUDGET_WALL_S)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-derive and byte-compare against --out without writing",
    )
    parser.set_defaults(use_cache=True)
    return parser.parse_args(argv)


def preflight_out(args: argparse.Namespace) -> None:
    """Fail fast on the output surface before the expensive derivation pass."""
    out_path: Path = args.out
    if args.check:
        if not out_path.is_file():
            raise DriverHarnessError(
                f"driver harness error: edition-timeline artifact not found: {out_path}",
                EXIT_INPUT_UNREADABLE,
            )
        return
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise DriverHarnessError(
            f"driver harness error: output directory is not writable: {error}",
            EXIT_OUT_UNWRITABLE,
        ) from error
    if not os.access(out_path.parent, os.W_OK):
        raise DriverHarnessError(
            f"driver harness error: output directory is not writable: {out_path.parent}",
            EXIT_OUT_UNWRITABLE,
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.producer_workers < 1:
        print("driver harness error: --producer-workers must be >= 1", file=sys.stderr)
        return EXIT_USAGE
    started = time.monotonic()
    try:
        preflight_out(args)
        evidence, timeline, ast_ctv = derive(args)
        rendered = render_artifact(evidence)
        summary = (
            f"editions={evidence['editions']} drift={evidence['totals']['drift']} "
            f"missing={evidence['totals']['missing']} phantom={evidence['totals']['phantom']} "
            f"ctv_resolved={evidence['totals']['ctv_resolved']} "
            f"hidden={evidence['totals']['hidden']} "
            f"non_monotonic={len(evidence['non_monotonic_transitions'])} "
            f"wall={time.monotonic() - started:.1f}s"
        )
        if args.check:
            actual = args.out.read_bytes()
            if actual != rendered.encode("ascii"):
                raise DriverHarnessError(
                    "driver harness error: edition-timeline artifact differs from the live "
                    "render (drift)",
                    EXIT_DRIFT,
                )
            print(f"edition-timeline check=ok {summary} out={args.out}")
            return EXIT_OK
        args.out.write_text(rendered, encoding="ascii")
        print(f"edition-timeline {summary} out={args.out}")
    except DriverHarnessError as error:
        print(error, file=sys.stderr)
        return error.exit_code
    except OSError as error:
        print(f"driver harness error: output is not writable: {error}", file=sys.stderr)
        return EXIT_OUT_UNWRITABLE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
