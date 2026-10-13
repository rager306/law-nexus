#!/usr/bin/env python3
"""Bounded stratified corpus hierarchy-lift census for M224/S05 (T04).

Reads the pinned S02 corpus manifest, deterministically selects a bounded
stratified sample (fixed seed + ten deciles of the manifest order + the largest
tail), and for every sampled document runs the *producer* half exactly once
(``cleaned-project export`` turns the source XML into a cleaned-wire JSONL
artifact) and then the *consumer* half (``hierarchy-lift-census`` reads **only**
that JSONL layer, bridges it into a ParsedBlock stream, extracts hierarchy
markers and places them on the detected ``document_groups`` ladder).  The
producer never runs downstream of the lift, so ``xml_reparse_in_lift`` is false
by construction: the consumer has no XML decoding surface at all.

The driver is *orchestration and aggregation only*: every number it publishes is
copied out of a per-document counts payload produced by the Rust consumer, and
the lift logic is never re-implemented in Python.  The tracked census carries
counts, closed-vocabulary tokens, hashes and paths only — no decoded text ever
reaches the artifact (ASCII by construction via ``ensure_ascii``).

Fail-closed surfaces (a harness error, never a skip): missing manifest, missing
corpus root, missing release binary after a rebuild attempt, a manifest row
whose ``relative_path`` is not a safe corpus-relative path, export failure or
timeout, consumer refusal, a per-document payload with the wrong schema, a
non-closed-vocabulary token, an accounting-identity violation, an output that
is not writable, and ``--check`` byte drift.

``--check`` re-runs the bounded census and byte-compares the live render against
the tracked artifact without writing (MEM1459 pattern); drift is exit 6.

Boundary: this is a bounded seeded census, not a full-corpus materialization
and it does not close R1000 (``r1000_status`` stays ``active/unclosed``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m224-s05-hierarchy-lift-census/v1"
VERSION = 1
KIND = "hierarchy_lift_census"
DOC_SCHEMA = "m224-s05-hierarchy-lift-doc/v1"
DOC_KIND = "hierarchy_lift_doc"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
R1000_STATUS = "active/unclosed"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_ONTOLOGY = ROOT / "prd/architecture/kb-ontology.yaml"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m224-s05-hierarchy-lift-census.json"
DEFAULT_PRODUCER_BIN = ROOT / "target/release/cleaned-project"
DEFAULT_CONSUMER_BIN = ROOT / "target/release/hierarchy-lift-census"

#: Closed decode-level catalog vocabulary of the authoritative extractor
#: (``ln_decode::hierarchy::catalog_token``); the census fails closed on any
#: token outside this set instead of inventing a bucket.
CATALOG_TOKENS = (
    "razdel",
    "glava",
    "paragraph",
    "statya",
    "chast",
    "punkt",
    "podpunkt",
)
#: Closed ladder roles declared by the ``document_groups`` ladders.
ROLES = ("container", "unit", "subunit", "subunit-text")
#: Closed ``document_groups`` id vocabulary (embedded catalog, 7 groups).
GROUPS = (
    "federal_law@v1",
    "code",
    "government_resolution",
    "presidential_decree",
    "departmental_order",
    "court_practice",
    "non_normative",
)
#: ``by_group`` keys: the closed group vocabulary plus the fail-closed key.
GROUP_KEYS = frozenset(GROUPS) | {"Unknown"}
#: Per-document payload keys emitted by the T03 consumer (exact set).
DOC_KEYS = frozenset(
    {
        "schema",
        "kind",
        "corpus_path",
        "source_format",
        "group",
        "detection",
        "lift",
        "by_group",
        "by_catalog_token",
        "by_role",
        "unmapped_tokens",
        "non_normative",
        "wire_source",
        "cleaned_wire_sha256",
        "r1000_status",
        "non_claims",
    }
)
DOC_LIFT_KEYS = frozenset({"markers", "bound", "unknown", "non_normative"})
WIRE_SOURCE_KEYS = frozenset({"sha256", "bytes"})
#: Corpus paths (``courts/`` / ``fas/``) that the text-only barrier classifies
#: as non-normative (ADR-0020 / ADR-0030 D2).  The census records both the
#: observed ``non_normative_documents`` count and this path-prefix count so a
#: drift between the structural classification and the bank-prefix expectation
#: is visible in the tracked bytes (T06 re-derives it independently).
NON_NORMATIVE_PREFIXES = ("courts/", "fas/")

#: Bounded sample: ten deciles of the manifest order, ``per_decile`` picks each,
#: plus the ``tail_n`` largest files.  The plan pins seed/per-decile/tail-n and
#: the resulting union (manifest is sha256-pinned, so the sample is stable).
SAMPLE_SEED = 22405
SAMPLE_PER_DECILE = 2
SAMPLE_TAIL_N = 8
SAMPLE_SIZE = 28
SAMPLE_DEFINITION = "manifest_order_deciles_plus_largest_tail"

DEFAULT_EXPORT_TIMEOUT_S = 240.0
DEFAULT_BUDGET_WALL_S = 1800.0

#: Evidence redaction: every artifact string is a path, hash, token, role or
#: snake_case / slash label.  Decoded corpus text never fits this closed shape.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:@]{1,240}$")
FORBIDDEN_KEYS = frozenset({"text", "literal", "decoded", "content", "detail"})

NON_CLAIMS = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "integrity_is_not_semantic_completeness",
    "bounded_sample_not_full_corpus",
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml",
    "no_xml_reparse_in_lift",
    "an_unmapped_marker_is_fail_closed_never_a_guessed_default",
    "non_normative_is_a_structural_barrier_not_a_legal_claim",
    "census_counts_only_no_decoded_text",
)

#: Exit codes (mirrors the T03 consumer contract 0/2/3/4/5 and adds the drift
#: code 6 the plan assigns to ``--check``).
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INPUT_UNREADABLE = 3
EXIT_OUT_UNWRITABLE = 4
EXIT_WIRE_REFUSED = 5
EXIT_DRIFT = 6


class CensusHarnessError(RuntimeError):
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
                        f"census harness error: unexpected manifest schema {record.get('schema')!r}",
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
        raise CensusHarnessError(
            "census harness error: manifest has no header record", EXIT_INPUT_UNREADABLE
        )
    if not entries:
        raise CensusHarnessError(
            "census harness error: manifest has no entries", EXIT_INPUT_UNREADABLE
        )
    return header, entries


def validate_relative_path(relative_path: str) -> None:
    """Reject a manifest row whose path cannot be safely joined to the root.

    Defence in depth (S05 threat model): a ``..`` component, an absolute path,
    a backslash, or a non-ASCII/control character is a harness error, never a
    skip.  The current manifest is hygienic; this keeps the last line of
    defence before the join.
    """
    if not relative_path or relative_path.startswith("/") or "\\" in relative_path:
        raise CensusHarnessError(
            "census harness error: unsafe corpus-relative path (absolute/empty/backslash)",
            EXIT_INPUT_UNREADABLE,
        )
    if not relative_path.isascii():
        raise CensusHarnessError(
            "census harness error: unsafe corpus-relative path (non-ASCII)",
            EXIT_INPUT_UNREADABLE,
        )
    if any(ord(character) < 0x20 for character in relative_path):
        raise CensusHarnessError(
            "census harness error: unsafe corpus-relative path (control character)",
            EXIT_INPUT_UNREADABLE,
        )
    parts = PurePosixPath(relative_path).parts
    if any(part in ("..", ".") for part in parts):
        raise CensusHarnessError(
            "census harness error: unsafe corpus-relative path (dot component)",
            EXIT_INPUT_UNREADABLE,
        )


def build_sample(
    entries: list[Entry], *, seed: int, per_decile: int, tail_n: int
) -> tuple[list[SampleItem], dict[str, int]]:
    """Deterministic stratified sample: manifest-order deciles + largest tail.

    The manifest (already pinned by sha256) is walked in its recorded order and
    split into ten positional deciles; a fixed seed draws ``per_decile`` files
    per decile.  The ``tail_n`` largest files (by ``(bytes, relative_path)``)
    are added unconditionally -- the tail is taken from the size-ranking (the
    M223 precedent) so that the manifest-order tail (the single ``xml/pas/``
    practice member) cannot silently enter the bounded sample.  Re-running with
    the same seed and pinned manifest re-selects the same files.
    """
    total = len(entries)
    deciles: list[list[Entry]] = [[] for _ in range(10)]
    for index, entry in enumerate(entries):
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

    by_size = sorted(entries, key=lambda entry: (entry.bytes, entry.relative_path))
    tail = by_size[-tail_n:] if tail_n > 0 else []
    strata_counts["tail_largest"] = len(tail)
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
        raise CensusHarnessError(
            "census harness error: release binary missing after cargo build "
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
        raise CensusHarnessError(
            f"census harness error: export timeout after {timeout_s}s for {xml_path.name}"
        ) from error
    except OSError as error:
        raise CensusHarnessError(
            f"census harness error: export spawn failed: {type(error).__name__}"
        ) from error
    if result.returncode != 0 or not out_path.is_file():
        raise CensusHarnessError(
            f"census harness error: export refused rc={result.returncode} for {xml_path.name}"
        )


def run_consumer(
    consumer_bin: Path,
    cleaned_wire: Path,
    corpus_path: str,
    out_path: Path,
    timeout_s: float,
) -> dict[str, Any]:
    """Run the JSONL-only consumer and parse its per-document counts payload."""
    source_format = "odt" if corpus_path.lower().endswith(".odt") else "wordml"
    try:
        result = subprocess.run(
            [
                str(consumer_bin),
                "--cleaned-wire",
                str(cleaned_wire),
                "--corpus-path",
                corpus_path,
                "--source-format",
                source_format,
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as error:
        raise CensusHarnessError(
            f"census harness error: consumer timeout after {timeout_s}s for {corpus_path}"
        ) from error
    except OSError as error:
        raise CensusHarnessError(
            f"census harness error: consumer spawn failed: {type(error).__name__}"
        ) from error
    if result.returncode != 0 or not out_path.is_file():
        raise CensusHarnessError(
            f"census harness error: consumer refused rc={result.returncode} for {corpus_path}"
        )
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CensusHarnessError(
            f"census harness error: consumer payload is not JSON for {corpus_path}"
        ) from error


# ------------------------------------------------------- payload validation #


def _int_map(
    value: Any, vocabulary: tuple[str, ...] | frozenset[str], label: str
) -> dict[str, int]:
    if not isinstance(value, dict):
        raise CensusHarnessError(f"census harness error: {label} is not an object")
    out: dict[str, int] = {}
    for token, count in value.items():
        if token not in vocabulary:
            raise CensusHarnessError(f"census harness error: unknown {label} token {token!r}")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise CensusHarnessError(f"census harness error: non-integer count in {label}")
        out[token] = count
    return out


def validate_doc_payload(document: dict[str, Any], corpus_path: str) -> None:
    """Fail-closed schema, vocabulary and accounting check on one payload."""
    if not isinstance(document, dict):
        raise CensusHarnessError("census harness error: consumer payload is not an object")
    if document.get("schema") != DOC_SCHEMA:
        raise CensusHarnessError(
            f"census harness error: unexpected doc schema {document.get('schema')!r}"
        )
    if document.get("kind") != DOC_KIND:
        raise CensusHarnessError(
            f"census harness error: unexpected doc kind {document.get('kind')!r}"
        )
    if document.get("r1000_status") != R1000_STATUS:
        raise CensusHarnessError("census harness error: doc r1000_status is not active/unclosed")
    if set(document) != DOC_KEYS:
        missing = sorted(DOC_KEYS - set(document))
        extra = sorted(set(document) - DOC_KEYS)
        raise CensusHarnessError(
            f"census harness error: doc keys drift (missing={missing}, extra={extra})"
        )
    if document.get("corpus_path") != corpus_path:
        raise CensusHarnessError("census harness error: doc corpus_path does not echo the sample")
    if document.get("source_format") not in ("wordml", "odt"):
        raise CensusHarnessError("census harness error: doc source_format is not wordml|odt")
    if document.get("group") not in GROUP_KEYS | {""}:
        raise CensusHarnessError(
            f"census harness error: unknown doc group {document.get('group')!r}"
        )
    if not isinstance(document.get("non_normative"), bool):
        raise CensusHarnessError("census harness error: doc non_normative is not a boolean")

    lift = document["lift"]
    if not isinstance(lift, dict) or set(lift) != DOC_LIFT_KEYS:
        raise CensusHarnessError("census harness error: doc lift keys drift")
    for key in ("markers", "bound", "unknown", "non_normative"):
        value = lift[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CensusHarnessError(f"census harness error: doc lift.{key} is not an int")

    by_group = _int_map(document["by_group"], GROUP_KEYS, "by_group")
    by_catalog_token = _int_map(document["by_catalog_token"], CATALOG_TOKENS, "by_catalog_token")
    by_role = _int_map(document["by_role"], ROLES, "by_role")
    unmapped = _int_map(document["unmapped_tokens"], CATALOG_TOKENS, "unmapped_tokens")

    if lift["markers"] != lift["bound"] + lift["unknown"] + lift["non_normative"]:
        raise CensusHarnessError(
            "census harness error: doc markers != bound + unknown + non_normative"
        )
    if sum(by_group.values()) != lift["markers"]:
        raise CensusHarnessError("census harness error: doc sum(by_group) != markers")
    if sum(by_catalog_token.values()) != lift["markers"]:
        raise CensusHarnessError("census harness error: doc sum(by_catalog_token) != markers")
    if sum(by_role.values()) != lift["bound"]:
        raise CensusHarnessError("census harness error: doc sum(by_role) != bound")
    if sum(unmapped.values()) != lift["unknown"]:
        raise CensusHarnessError("census harness error: doc sum(unmapped_tokens) != unknown")
    if document["non_normative"] and lift["non_normative"] != lift["markers"]:
        raise CensusHarnessError("census harness error: text_only doc does not account markers")

    wire_source = document["wire_source"]
    if not isinstance(wire_source, dict) or set(wire_source) != WIRE_SOURCE_KEYS:
        raise CensusHarnessError("census harness error: doc wire_source keys drift")


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
                        f"census harness error: forbidden artifact key {key!r}",
                        EXIT_OUT_UNWRITABLE,
                    )
                if not SAFE_STRING.match(key):
                    raise CensusHarnessError(
                        f"census harness error: unsafe artifact key {key!r}", EXIT_OUT_UNWRITABLE
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
            raise CensusHarnessError(
                "census harness error: unsafe artifact string (redaction guard)",
                EXIT_OUT_UNWRITABLE,
            )

    walk(artifact)


# ---------------------------------------------------------------- harness #


def run_census(args: argparse.Namespace) -> dict[str, Any]:
    """Select, export, consume, aggregate, check invariants, emit evidence."""
    started = time.monotonic()

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        raise CensusHarnessError(
            f"census harness error: manifest not found: {manifest_path}", EXIT_INPUT_UNREADABLE
        )
    header, entries = parse_manifest(manifest_path)

    corpus_root: Path = args.corpus_root or ROOT / str(header["root"])
    if not corpus_root.is_dir():
        raise CensusHarnessError(
            f"census harness error: corpus root not found: {corpus_root}", EXIT_INPUT_UNREADABLE
        )

    ontology_path: Path = args.ontology
    if not ontology_path.is_file():
        raise CensusHarnessError(
            f"census harness error: ontology not found: {ontology_path}", EXIT_INPUT_UNREADABLE
        )

    sample, strata = build_sample(
        entries,
        seed=args.seed,
        per_decile=args.per_decile,
        tail_n=args.tail_n,
    )
    if len(sample) != SAMPLE_SIZE:
        raise CensusHarnessError(
            f"census harness error: sample size {len(sample)} != pinned {SAMPLE_SIZE}",
            EXIT_INPUT_UNREADABLE,
        )

    ensure_release_binary(args.producer_bin, "ln-decode", "cleaned-project")
    ensure_release_binary(args.consumer_bin, "ln-consultant-parser", "hierarchy-lift-census")

    by_group: dict[str, int] = {}
    by_catalog_token: dict[str, int] = {}
    by_role: dict[str, int] = {}
    unmapped_tokens: dict[str, int] = {}
    lift_markers = 0
    lift_bound = 0
    lift_unknown = 0
    lift_non_normative = 0
    non_normative_documents = 0
    accepted = 0

    for item in sample:
        if time.monotonic() - started > args.budget_wall_s:
            raise CensusHarnessError(
                f"census harness error: budget wall {args.budget_wall_s}s exceeded"
            )
        validate_relative_path(item.relative_path)
        xml_path = corpus_root / item.relative_path
        if not xml_path.is_file():
            raise CensusHarnessError(
                f"census harness error: sampled corpus file not found: {item.relative_path}",
                EXIT_INPUT_UNREADABLE,
            )
        with tempfile.TemporaryDirectory(prefix="m224-s05-census-") as tmp:
            wire_path = Path(tmp) / "wire.jsonl"
            doc_path = Path(tmp) / "doc.json"
            run_producer(args.producer_bin, xml_path, wire_path, args.export_timeout_s)
            document = run_consumer(
                args.consumer_bin,
                wire_path,
                item.relative_path,
                doc_path,
                args.export_timeout_s,
            )
        validate_doc_payload(document, item.relative_path)

        lift = document["lift"]
        lift_markers += lift["markers"]
        lift_bound += lift["bound"]
        lift_unknown += lift["unknown"]
        lift_non_normative += lift["non_normative"]
        if document["non_normative"]:
            non_normative_documents += 1
        merge(by_group, document["by_group"])
        merge(by_catalog_token, document["by_catalog_token"])
        merge(by_role, document["by_role"])
        merge(unmapped_tokens, document["unmapped_tokens"])
        accepted += 1

    # Aggregate invariants (the per-document checks already passed).
    if lift_markers != lift_bound + lift_unknown + lift_non_normative:
        raise CensusHarnessError(
            "census harness error: aggregate markers != bound + unknown + non_normative"
        )
    if sum(by_group.values()) != lift_markers:
        raise CensusHarnessError("census harness error: aggregate sum(by_group) != markers")
    if sum(by_catalog_token.values()) != lift_markers:
        raise CensusHarnessError("census harness error: aggregate sum(by_catalog_token) != markers")
    if sum(by_role.values()) != lift_bound:
        raise CensusHarnessError("census harness error: aggregate sum(by_role) != bound")
    if sum(unmapped_tokens.values()) != lift_unknown:
        raise CensusHarnessError("census harness error: aggregate sum(unmapped_tokens) != unknown")
    if lift_unknown > 0 and not unmapped_tokens:
        raise CensusHarnessError(
            "census harness error: lift.unknown > 0 but unmapped_tokens is empty"
        )

    prefix_non_normative = sum(
        1 for item in sample if item.relative_path.startswith(NON_NORMATIVE_PREFIXES)
    )

    evidence = {
        "schema": SCHEMA,
        "version": VERSION,
        "kind": KIND,
        "non_claims": list(NON_CLAIMS),
        "manifest_path": relative_label(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_entries": len(entries),
        "inventory_digest": header.get("inventory_digest", ""),
        "corpus_root": relative_label(corpus_root),
        "producer_binary_path": relative_label(args.producer_bin),
        "producer_binary_sha256": sha256_file(args.producer_bin),
        "consumer_binary_path": relative_label(args.consumer_bin),
        "consumer_binary_sha256": sha256_file(args.consumer_bin),
        "ontology_path": relative_label(ontology_path),
        "ontology_sha256": sha256_file(ontology_path),
        "sample_seed": args.seed,
        "sample_per_decile": args.per_decile,
        "sample_tail_n": args.tail_n,
        "sample_definition": SAMPLE_DEFINITION,
        "sample_strata": strata,
        "sample_size": len(sample),
        "documents": {"attempted": len(sample), "accepted": accepted, "refused": 0},
        "by_group": dict(sorted(by_group.items())),
        "by_catalog_token": dict(sorted(by_catalog_token.items())),
        "by_role": dict(sorted(by_role.items())),
        "lift": {
            "markers": lift_markers,
            "bound": lift_bound,
            "unknown": lift_unknown,
            "non_normative": lift_non_normative,
        },
        "unmapped_tokens": dict(sorted(unmapped_tokens.items())),
        "non_normative_documents": non_normative_documents,
        "non_normative_prefix_documents": prefix_non_normative,
        "xml_reparse_in_lift": False,
        "r1000_status": R1000_STATUS,
    }
    redaction_check(evidence)
    return evidence


def render_artifact(evidence: dict[str, Any]) -> str:
    """Canonical deterministic ASCII render of the census artifact."""
    return json.dumps(evidence, indent=2, ensure_ascii=True) + "\n"


# -------------------------------------------------------------------- cli #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--producer-bin", type=Path, default=DEFAULT_PRODUCER_BIN, dest="producer_bin"
    )
    parser.add_argument(
        "--consumer-bin", type=Path, default=DEFAULT_CONSUMER_BIN, dest="consumer_bin"
    )
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument("--per-decile", type=int, default=SAMPLE_PER_DECILE)
    parser.add_argument("--tail-n", type=int, default=SAMPLE_TAIL_N)
    parser.add_argument("--export-timeout-s", type=float, default=DEFAULT_EXPORT_TIMEOUT_S)
    parser.add_argument("--budget-wall-s", type=float, default=DEFAULT_BUDGET_WALL_S)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-run the bounded census and byte-compare against --out without writing",
    )
    return parser.parse_args(argv)


def preflight_out(args: argparse.Namespace) -> None:
    """Fail fast on the output surface before the expensive census pass.

    Without this, an unwritable ``--out`` or a missing ``--check`` artifact
    would only surface after a full ~28-document export pass (fail-closed but
    needlessly late).
    """
    out_path: Path = args.out
    if args.check:
        if not out_path.is_file():
            raise CensusHarnessError(
                f"census harness error: census artifact not found: {out_path}",
                EXIT_INPUT_UNREADABLE,
            )
        return
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CensusHarnessError(
            f"census harness error: output directory is not writable: {error}",
            EXIT_OUT_UNWRITABLE,
        ) from error
    if not os.access(out_path.parent, os.W_OK):
        raise CensusHarnessError(
            f"census harness error: output directory is not writable: {out_path.parent}",
            EXIT_OUT_UNWRITABLE,
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        preflight_out(args)
        evidence = run_census(args)
        rendered = render_artifact(evidence)
        if args.check:
            out_path: Path = args.out
            actual = out_path.read_bytes()
            if actual != rendered.encode("ascii"):
                raise CensusHarnessError(
                    "census harness error: census artifact differs from the live render (drift)",
                    EXIT_DRIFT,
                )
            print(
                f"census check=ok sample_size={evidence['sample_size']} "
                f"markers={evidence['lift']['markers']} bound={evidence['lift']['bound']} "
                f"unknown={evidence['lift']['unknown']} "
                f"non_normative={evidence['lift']['non_normative']} out={args.out}"
            )
            return EXIT_OK
        out_path = args.out
        out_path.write_text(rendered, encoding="ascii")
    except CensusHarnessError as error:
        print(error, file=sys.stderr)
        return error.exit_code
    except OSError as error:
        print(f"census harness error: output is not writable: {error}", file=sys.stderr)
        return EXIT_OUT_UNWRITABLE
    print(
        f"census sample_size={evidence['sample_size']} "
        f"markers={evidence['lift']['markers']} bound={evidence['lift']['bound']} "
        f"unknown={evidence['lift']['unknown']} "
        f"non_normative={evidence['lift']['non_normative']} "
        f"non_normative_documents={evidence['non_normative_documents']} out={args.out}"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
