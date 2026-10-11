#!/usr/bin/env python3
"""Bounded real-corpus navigation census for M223/S06 (T04).

Reads the pinned S02 corpus manifest, deterministically selects a bounded
stratified sample (fixed seed + size deciles + the largest tail — the same
method as the S02 probe / S05 census), runs the real ``reader-nav`` release
binary over every sampled file, and aggregates the single counts document each
invocation prints.  The census evidence carries counts, hashes and paths only —
no decoded text ever reaches the artifact, and no pagination field is emitted.

Fail-closed surfaces (a harness error, never a skip): missing manifest, missing
corpus root, missing release binary after a rebuild attempt, a non-zero
``reader-nav`` exit, a timeout, a malformed or wrong-schema counts document, an
unknown closed-vocabulary token, an invariant violation (``resolved +
unresolved != references``, a non-terminal ``path_to_root``, a parent cycle) or
a pagination field in the counts document or the artifact.

Boundary: this is a bounded seeded census, not a full-corpus materialization
(that is S05–S07) and it does not close R1000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m223-s06-navigation-census/v1"
VERSION = 1
COUNTS_SCHEMA = "m223-s06-navigation-counts/v1"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
S03_SCHEMA = "m223-s03-baseline-run/v1"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_CONTRACT = ROOT / "prd/architecture/intermediate-source-navigation-contract.md"
DEFAULT_S03 = ROOT / "prd/migration/rust-evidence/m223-s03-baseline-run.json"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m223-s06-navigation-census.json"
DEFAULT_BIN = ROOT / "target/release/reader-nav"

#: The closed navigation profile.  Mirrors the Rust declarations of
#: ``reader_navigation`` / ``reader_projection`` / ``reader_contract``; the
#: census fails closed on any observed token outside this profile instead of
#: inventing a bucket.
NODE_KINDS = ("view", "segment", "reference")
LINK_KINDS = ("contains", "owns", "precedes", "resolves_to")
VIEW_KINDS = ("paragraph", "residual", "table", "row", "cell", "note")
SEGMENT_KINDS = ("text", "derived")
ORIGINS = ("source_fragment", "derived:tab", "derived:line_break", "derived:page_break")
REFERENCE_TYPES = (
    "note_reference",
    "endnote_reference",
    "comment_reference",
    "annotation_reference",
    "field",
    "unknown_wordml_element",
    "foreign_element",
)
RESOLVE_REASONS = (
    "no_matching_note_definition",
    "multiple_matching_note_definitions",
    "not_a_resolvable_reference",
    "missing_anchor_element",
    "missing_note_view",
)

#: Bounded sample: the S02 decile+tail method with smaller strata; the union
#: must stay inside [20, 32] accepted files.
SAMPLE_MIN = 20
SAMPLE_MAX = 32
DEFAULT_SEED = 22306
DEFAULT_PER_DECILE = 2
DEFAULT_TAIL_N = 6
#: Bounded-input guard: the census is a bounded seeded sample, so inputs above
#: this many bytes are excluded before sampling. The cap keeps 99.35% of the
#: pinned corpus (286 of 43 785 files are larger) and bounds the per-input cost;
#: it is recorded in the artifact and never a silent filter.
DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_RUN_TIMEOUT_S = 120.0
DEFAULT_BUDGET_WALL_S = 900.0

#: Evidence redaction: every artifact string is a path, hash, token, or
#: snake_case / slash label.  Decoded corpus text never fits this closed shape.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:]{1,240}$")
#: Keys that may never appear at all in the artifact.
FORBIDDEN_KEYS = frozenset({"literal", "decoded", "content", "detail"})
#: Keys that may appear only as an integer tally key, never carrying a string
#: payload.  ``text`` is a legitimate closed ``ReaderSegmentKind`` token, so it
#: is forbidden only when its value is a string (a raw-text payload).
FORBIDDEN_STRING_KEYS = frozenset({"text", "raw_text", "decoded_text"})
#: No physical-pagination surface may appear in a navigation counts document or
#: the census artifact (contract §11).
PAGINATION_KEYS = frozenset(
    {
        "page",
        "pages",
        "pagination",
        "page_number",
        "page_index",
        "page_boundary",
        "physical_page",
        "page_model",
    }
)

NON_CLAIMS = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "not_normalization",
    "not_authenticity_evidence",
    "bounded_sample_not_full_corpus_s05_s07",
    "bounded_by_input_size_guard",
    "no_xml_reparse",
    "no_physical_pagination_surface",
    "census_counts_only_no_decoded_text",
)

COUNTS_KEYS = frozenset(
    {
        "schema",
        "views",
        "segments",
        "references",
        "views_by_kind",
        "segments_by_kind",
        "segments_by_origin",
        "references_by_type",
        "links_by_kind",
        "resolved",
        "unresolved",
        "unresolved_by_reason",
        "max_depth",
        "max_path_len",
        "subtree_chars_primary",
        "subtree_chars_service",
        "docs",
        "path_terminal",
        "cycles",
    }
)


class CensusHarnessError(RuntimeError):
    """Fail-closed harness failure: never a skip, never a silent pass."""


@dataclass(frozen=True)
class Entry:
    """One accepted manifest entry (relative to the corpus root)."""

    relative_path: str
    sha256: str
    bytes: int


@dataclass
class SampleItem:
    """One selected file with the strata that pulled it in (mutable strata)."""

    relative_path: str
    bytes: int
    strata: list[str] = field(default_factory=list)


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
                    raise CensusHarnessError(
                        f"census harness error: unexpected manifest schema {record.get('schema')!r}"
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
        raise CensusHarnessError("census harness error: manifest has no header record")
    if not entries:
        raise CensusHarnessError("census harness error: manifest has no entries")
    return header, entries


def filter_entries(entries: list[Entry], max_bytes: int) -> list[Entry]:
    """Keep only manifest entries whose input is at most ``max_bytes``.

    A documented bounded-input guard, never a silent drop: the caller records
    the cap and the excluded count in the artifact.
    """
    return [entry for entry in entries if entry.bytes <= max_bytes]


def build_sample(
    entries: list[Entry], *, seed: int, per_decile: int, tail_n: int
) -> tuple[list[SampleItem], dict[str, int]]:
    """Deterministic stratified sample: per-decile picks + the largest tail.

    Files are ranked by ``(bytes, relative_path)`` and split into ten deciles; a
    fixed seed draws ``per_decile`` files per decile; the ``tail_n`` largest
    files are added unconditionally.  Re-running with the same seed re-selects
    the same files.
    """
    by_size = sorted(entries, key=lambda entry: (entry.bytes, entry.relative_path))
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
    for entry in tail:
        item = chosen.setdefault(entry.relative_path, SampleItem(entry.relative_path, entry.bytes))
        if "tail_largest" not in item.strata:
            item.strata.append("tail_largest")

    sample = sorted(chosen.values(), key=lambda item: item.relative_path)
    return sample, strata_counts


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


def ensure_release_binary(bin_path: Path) -> None:
    """Use the existing release binary, else build it; missing = fail-closed."""
    if bin_path.is_file():
        return
    build = subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "-p",
            "ln-decode",
            "--bin",
            "reader-nav",
            "--offline",
        ],
        cwd=ROOT,
        capture_output=True,
    )
    if build.returncode != 0 or not bin_path.is_file():
        raise CensusHarnessError(
            "census harness error: release binary missing after cargo build "
            f"(rc={build.returncode})"
        )


# ---------------------------------------------------------- counts document #


def run_reader_nav(bin_path: Path, xml_path: Path, timeout_s: float) -> dict[str, Any]:
    """Run ``reader-nav`` on one file and parse its single counts document."""
    try:
        result = subprocess.run(
            [str(bin_path), "--from-xml", str(xml_path)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as error:
        raise CensusHarnessError(
            f"census harness error: reader-nav timeout after {timeout_s}s for {xml_path.name}"
        ) from error
    except OSError as error:
        raise CensusHarnessError(
            f"census harness error: reader-nav spawn failed: {type(error).__name__}"
        ) from error
    if result.returncode != 0:
        raise CensusHarnessError(
            f"census harness error: reader-nav refused rc={result.returncode} for {xml_path.name}"
        )
    text = result.stdout.decode("utf-8", errors="strict").strip()
    if not text:
        raise CensusHarnessError(
            f"census harness error: reader-nav printed no counts document for {xml_path.name}"
        )
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise CensusHarnessError(
            f"census harness error: reader-nav counts document is not JSON for {xml_path.name}"
        ) from error
    if not isinstance(document, dict):
        raise CensusHarnessError(
            f"census harness error: reader-nav counts document is not an object for {xml_path.name}"
        )
    return document


def _tally_tokens(
    document: dict[str, Any], key: str, vocabulary: tuple[str, ...]
) -> dict[str, int]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise CensusHarnessError(f"census harness error: counts field {key!r} is not an object")
    tallied: dict[str, int] = {}
    for token, count in value.items():
        if token not in vocabulary:
            raise CensusHarnessError(f"census harness error: unknown {key} token {token!r}")
        if not isinstance(count, int) or count < 0:
            raise CensusHarnessError(f"census harness error: non-integer count in {key!r}")
        tallied[token] = count
    return tallied


def validate_counts_document(document: dict[str, Any]) -> None:
    """Fail-closed schema, vocabulary and invariant check on one counts doc."""
    if document.get("schema") != COUNTS_SCHEMA:
        raise CensusHarnessError(
            f"census harness error: unexpected counts schema {document.get('schema')!r}"
        )
    if set(document) != COUNTS_KEYS:
        missing = sorted(COUNTS_KEYS - set(document))
        extra = sorted(set(document) - COUNTS_KEYS)
        raise CensusHarnessError(
            f"census harness error: counts document keys drift (missing={missing}, extra={extra})"
        )
    for key in PAGINATION_KEYS:
        if key in document:
            raise CensusHarnessError(f"census harness error: pagination field {key!r} present")

    for key in ("views", "segments", "references", "resolved", "unresolved"):
        if not isinstance(document[key], int) or document[key] < 0:
            raise CensusHarnessError(f"census harness error: counts field {key!r} is not an int")

    views_by_kind = _tally_tokens(document, "views_by_kind", VIEW_KINDS)
    segments_by_kind = _tally_tokens(document, "segments_by_kind", SEGMENT_KINDS)
    segments_by_origin = _tally_tokens(document, "segments_by_origin", ORIGINS)
    references_by_type = _tally_tokens(document, "references_by_type", REFERENCE_TYPES)
    _tally_tokens(document, "links_by_kind", LINK_KINDS)
    unresolved_by_reason = _tally_tokens(document, "unresolved_by_reason", RESOLVE_REASONS)

    # Internal consistency of the per-kind tallies.
    if sum(views_by_kind.values()) != document["views"]:
        raise CensusHarnessError("census harness error: views_by_kind does not sum to views")
    if sum(segments_by_kind.values()) != document["segments"]:
        raise CensusHarnessError("census harness error: segments_by_kind does not sum to segments")
    if sum(segments_by_origin.values()) != document["segments"]:
        raise CensusHarnessError(
            "census harness error: segments_by_origin does not sum to segments"
        )
    if sum(references_by_type.values()) != document["references"]:
        raise CensusHarnessError(
            "census harness error: references_by_type does not sum to references"
        )
    if sum(unresolved_by_reason.values()) != document["unresolved"]:
        raise CensusHarnessError(
            "census harness error: unresolved_by_reason does not sum to unresolved"
        )

    # Invariant: resolved + unresolved == references.
    if document["resolved"] + document["unresolved"] != document["references"]:
        raise CensusHarnessError(
            "census harness error: resolved + unresolved != references "
            f"({document['resolved']} + {document['unresolved']} != {document['references']})"
        )
    # Invariant: path_to_root is terminal and cycle-free.
    if document["path_terminal"] is not True:
        raise CensusHarnessError("census harness error: path_to_root is not terminal")
    if document["cycles"] != 0:
        raise CensusHarnessError("census harness error: a parent cycle was reported")


def empty_tally() -> dict[str, int]:
    return {}


def merge(totals: dict[str, int], addition: dict[str, int]) -> None:
    for token, count in addition.items():
        totals[token] = totals.get(token, 0) + count


# -------------------------------------------------------------- redaction #


def redaction_check(artifact: dict[str, Any]) -> None:
    """Fail-closed before writing: only counts/hashes/paths/tokens may ship."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN_KEYS:
                    raise CensusHarnessError(
                        f"census harness error: forbidden artifact key {key!r}"
                    )
                if key in FORBIDDEN_STRING_KEYS and isinstance(value, str):
                    raise CensusHarnessError(f"census harness error: raw-text artifact key {key!r}")
                if key in PAGINATION_KEYS:
                    raise CensusHarnessError(
                        f"census harness error: pagination artifact key {key!r}"
                    )
                if not SAFE_STRING.match(key):
                    raise CensusHarnessError(f"census harness error: unsafe artifact key {key!r}")
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, bool):
            return
        elif isinstance(node, int):
            return
        elif isinstance(node, str) and not SAFE_STRING.match(node):
            raise CensusHarnessError(
                "census harness error: unsafe artifact string (redaction guard)"
            )

    walk(artifact)


# ---------------------------------------------------------------- harness #


def _reconcile_s03(s03_path: Path) -> dict[str, Any]:
    """Read the four numbers and r1000_status from the S03 baseline."""
    if not s03_path.is_file():
        raise CensusHarnessError(f"census harness error: S03 baseline not found: {s03_path}")
    baseline = json.loads(s03_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != S03_SCHEMA:
        raise CensusHarnessError(
            f"census harness error: unexpected S03 schema {baseline.get('schema')!r}"
        )
    counts = baseline.get("counts", {})
    return {
        "entries": int(counts.get("entries", 0)),
        "accepted": int(counts.get("accepted", 0)),
        "refused": int(counts.get("refused", 0)),
        "incomplete": int(counts.get("incomplete", 0)),
        "r1000_status": str(baseline.get("r1000_status", "")),
    }


def run_census(args: argparse.Namespace) -> dict[str, Any]:
    """Select, run ``reader-nav``, aggregate, check invariants, emit evidence."""
    started = time.monotonic()

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        raise CensusHarnessError(f"census harness error: manifest not found: {manifest_path}")
    header, entries = parse_manifest(manifest_path)

    corpus_root: Path = args.corpus_root or ROOT / str(header["root"])
    if not corpus_root.is_dir():
        raise CensusHarnessError(f"census harness error: corpus root not found: {corpus_root}")

    bounded_entries = filter_entries(entries, args.max_bytes)
    if not bounded_entries:
        raise CensusHarnessError(
            f"census harness error: no manifest entry is within the {args.max_bytes}-byte input guard"
        )
    sample, strata = build_sample(
        bounded_entries, seed=args.seed, per_decile=args.per_decile, tail_n=args.tail_n
    )
    if not SAMPLE_MIN <= len(sample) <= SAMPLE_MAX:
        raise CensusHarnessError(
            f"census harness error: sample size {len(sample)} outside [{SAMPLE_MIN}, {SAMPLE_MAX}]"
        )

    ensure_release_binary(args.bin_path)

    contract_path: Path = args.contract
    if not contract_path.is_file():
        raise CensusHarnessError(f"census harness error: contract not found: {contract_path}")

    s03_reconciled = _reconcile_s03(args.s03)

    views_total = 0
    segments_total = 0
    references_total = 0
    resolved_total = 0
    unresolved_total = 0
    max_depth = 0
    max_path_len = 0
    subtree_primary = 0
    subtree_service = 0
    views_by_kind: dict[str, int] = empty_tally()
    segments_by_kind: dict[str, int] = empty_tally()
    segments_by_origin: dict[str, int] = empty_tally()
    references_by_type: dict[str, int] = empty_tally()
    links_by_kind: dict[str, int] = empty_tally()
    unresolved_by_reason: dict[str, int] = empty_tally()

    accepted = 0
    for item in sample:
        if time.monotonic() - started > args.budget_wall_s:
            raise CensusHarnessError(
                f"census harness error: budget wall {args.budget_wall_s}s exceeded"
            )
        xml_path = corpus_root / item.relative_path
        if not xml_path.is_file():
            raise CensusHarnessError(
                f"census harness error: sampled corpus file not found: {item.relative_path}"
            )
        document = run_reader_nav(args.bin_path, xml_path, args.run_timeout_s)
        validate_counts_document(document)

        views_total += document["views"]
        segments_total += document["segments"]
        references_total += document["references"]
        resolved_total += document["resolved"]
        unresolved_total += document["unresolved"]
        max_depth = max(max_depth, document["max_depth"])
        max_path_len = max(max_path_len, document["max_path_len"])
        subtree_primary += document["subtree_chars_primary"]
        subtree_service += document["subtree_chars_service"]
        merge(views_by_kind, document["views_by_kind"])
        merge(segments_by_kind, document["segments_by_kind"])
        merge(segments_by_origin, document["segments_by_origin"])
        merge(references_by_type, document["references_by_type"])
        merge(links_by_kind, document["links_by_kind"])
        merge(unresolved_by_reason, document["unresolved_by_reason"])
        accepted += 1

    if views_total == 0 or segments_total == 0:
        raise CensusHarnessError(
            "census harness error: census observed zero views/segments over the whole "
            "sample — a tally is not evidence, refusing to emit an artifact"
        )

    # Aggregate invariants (the per-document check already passed).
    if resolved_total + unresolved_total != references_total:
        raise CensusHarnessError(
            "census harness error: aggregate resolved + unresolved != references"
        )
    if sum(views_by_kind.values()) != views_total:
        raise CensusHarnessError("census harness error: aggregate views_by_kind drift")
    if sum(segments_by_kind.values()) != segments_total:
        raise CensusHarnessError("census harness error: aggregate segments_by_kind drift")
    if sum(segments_by_origin.values()) != segments_total:
        raise CensusHarnessError("census harness error: aggregate segments_by_origin drift")
    if sum(references_by_type.values()) != references_total:
        raise CensusHarnessError("census harness error: aggregate references_by_type drift")
    if sum(unresolved_by_reason.values()) != unresolved_total:
        raise CensusHarnessError("census harness error: aggregate unresolved_by_reason drift")

    observed_node_kinds = sorted(
        token
        for token, count in (
            ("view", views_total),
            ("segment", segments_total),
            ("reference", references_total),
        )
        if count > 0
    )
    observed_link_kinds = sorted(links_by_kind)
    observed_view_kinds = sorted(views_by_kind)
    observed_segment_kinds = sorted(segments_by_kind)
    observed_origins = sorted(segments_by_origin)
    observed_reference_types = sorted(references_by_type)
    observed_resolve_reasons = sorted(unresolved_by_reason)

    uncovered: list[str] = []
    for observed, declared, label in (
        (observed_node_kinds, NODE_KINDS, "node_kind"),
        (observed_link_kinds, LINK_KINDS, "link_kind"),
        (observed_view_kinds, VIEW_KINDS, "view_kind"),
        (observed_segment_kinds, SEGMENT_KINDS, "segment_kind"),
        (observed_origins, ORIGINS, "origin"),
        (observed_reference_types, REFERENCE_TYPES, "reference_type"),
        (observed_resolve_reasons, RESOLVE_REASONS, "resolve_reason"),
    ):
        for token in observed:
            if token not in declared:
                uncovered.append(f"{label}:{token}")
    if uncovered:
        raise CensusHarnessError(
            f"census harness error: observed tokens outside the closed profile: {uncovered}"
        )

    evidence = {
        "schema": SCHEMA,
        "version": VERSION,
        "counts_schema": COUNTS_SCHEMA,
        "non_claims": list(NON_CLAIMS),
        "manifest_path": relative_label(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_entries": len(entries),
        "manifest_entries_over_cap": len(entries) - len(bounded_entries),
        "sample_max_bytes": args.max_bytes,
        "corpus_root": relative_label(corpus_root),
        "binary_path": relative_label(args.bin_path),
        "binary_sha256": sha256_file(args.bin_path),
        "contract_path": relative_label(contract_path),
        "contract_sha256": sha256_file(contract_path),
        "sample_seed": args.seed,
        "sample_per_decile": args.per_decile,
        "sample_tail_n": args.tail_n,
        "sample_strata": strata,
        "sample_size": len(sample),
        "documents": {"attempted": len(sample), "accepted": accepted, "failed": 0},
        "views_total": views_total,
        "segments_total": segments_total,
        "references_total": references_total,
        "views_by_kind": dict(sorted(views_by_kind.items())),
        "segments_by_kind": dict(sorted(segments_by_kind.items())),
        "segments_by_origin": dict(sorted(segments_by_origin.items())),
        "references_by_type": dict(sorted(references_by_type.items())),
        "links_by_kind": dict(sorted(links_by_kind.items())),
        "resolved_total": resolved_total,
        "unresolved_total": unresolved_total,
        "unresolved_by_reason": dict(sorted(unresolved_by_reason.items())),
        "max_depth": max_depth,
        "max_path_len": max_path_len,
        "subtree_chars": {"primary": subtree_primary, "service": subtree_service},
        "observed_node_kinds": observed_node_kinds,
        "observed_link_kinds": observed_link_kinds,
        "observed_view_kinds": observed_view_kinds,
        "observed_segment_kinds": observed_segment_kinds,
        "observed_origins": observed_origins,
        "observed_reference_types": observed_reference_types,
        "observed_resolve_reasons": observed_resolve_reasons,
        "uncovered": uncovered,
        "path_terminal": True,
        "cycles": 0,
        "reference_accounting_ok": True,
        "s03_baseline_reconciled": s03_reconciled,
        "wall_s": round(time.monotonic() - started, 3),
    }
    redaction_check(evidence)
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


# -------------------------------------------------------------------- cli #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--bin", type=Path, default=DEFAULT_BIN, dest="bin_path")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--s03", type=Path, default=DEFAULT_S03)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--per-decile", type=int, default=DEFAULT_PER_DECILE)
    parser.add_argument("--tail-n", type=int, default=DEFAULT_TAIL_N)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--run-timeout-s", type=float, default=DEFAULT_RUN_TIMEOUT_S)
    parser.add_argument("--budget-wall-s", type=float, default=DEFAULT_BUDGET_WALL_S)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        evidence = run_census(args)
    except CensusHarnessError as error:
        print(error, file=sys.stderr)
        return 2
    print(
        f"census: sample_size={evidence['sample_size']} "
        f"views={evidence['views_total']} segments={evidence['segments_total']} "
        f"references={evidence['references_total']} "
        f"resolved={evidence['resolved_total']} unresolved={evidence['unresolved_total']} "
        f"out={args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
