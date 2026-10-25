#!/usr/bin/env python3
"""Bounded real-corpus class census for the M223/S05 clean-rule profile (T03).

Reads the pinned S02 corpus manifest, deterministically selects a bounded
stratified sample (fixed seed + size deciles + the largest tail — the same
method as the S02 probe, with smaller strata), runs the real ``cleaned-project
export`` release binary over every sampled file, stream-tallies the
``semantic`` (and ``origin`` / derived kind) fields of the emitted JSONL
artifacts, and checks every observed class against the machine-readable
``reader_clean_profile/v1`` block of the S05 design contract.  The census
evidence carries counts, hashes and paths only — no decoded text ever reaches
the artifact.

Fail-closed surfaces (a harness error, never a skip): missing manifest or
corpus root, missing release binary after a rebuild attempt, export failure or
timeout, an unknown ``semantic``/``origin`` token, a malformed contract
profile block, an observed class without a declared disposition, and a
revision class observed while its profile disposition is ``dropped``.

Boundary: this is a bounded census, not a full-corpus run (that belongs to
S07) and it does not close R1000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "m223-s05-real-class-census/v1"
VERSION = 1
PROFILE_ID = "reader_clean_profile/v1"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"

DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
DEFAULT_CONTRACT = ROOT / "prd/architecture/intermediate-source-clean-view-contract.md"
DEFAULT_OUT = ROOT / "prd/migration/rust-evidence/m223-s05-real-class-census.json"
DEFAULT_BIN = ROOT / "target/release/cleaned-project"

#: Mirrors the closed ``ReaderSemantic`` vocabulary of reader_contract.rs; the
#: census fails closed on any other wire token instead of inventing a bucket.
READER_SEMANTIC_CLASSES = (
    "body",
    "whitespace",
    "field_code",
    "revision_insertion",
    "revision_deletion",
    "derived_separator",
    "empty",
)
DISPOSITIONS = ("primary", "service", "dropped")
#: The profile contract pins revision classes away from ``dropped``; the census
#: re-checks the observed classes against these required dispositions.
REVISION_REQUIRED_DISPOSITIONS = {
    "revision_insertion": "primary",
    "revision_deletion": "service",
}
ORIGIN_TOKENS = (
    "source_fragment",
    "derived:tab",
    "derived:line_break",
    "derived:page_break",
)
#: Wire line kinds of the export artifact (cleaned_wire.rs closed vocabulary);
#: segment lines carry the tallied ``semantic``/``origin`` tokens.
SEGMENT_LINE_KIND = "cleaned_projection_segment"
WIRE_LINE_KINDS = (
    "cleaned_projection_manifest",
    "cleaned_projection_policies",
    "cleaned_projection_view",
    SEGMENT_LINE_KIND,
    "cleaned_projection_reference",
    "cleaned_projection_footer",
)

#: Bounded sample: the S02 decile+tail method with smaller strata; the union
#: must stay inside [24, 32] accepted files.
SAMPLE_MIN = 24
SAMPLE_MAX = 32
DEFAULT_SEED = 22305
DEFAULT_PER_DECILE = 2
DEFAULT_TAIL_N = 8
DEFAULT_EXPORT_TIMEOUT_S = 180.0
DEFAULT_BUDGET_WALL_S = 1200.0

#: Evidence redaction: every artifact string is a path, hash, token, rule id or
#: snake_case label.  Decoded corpus text never fits this closed shape.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:]{1,240}$")
FORBIDDEN_KEYS = frozenset({"text", "literal", "decoded", "content", "detail"})

NON_CLAIMS = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "not_normalization",
    "not_authenticity_evidence",
    "bounded_sample_not_full_corpus_s07",
    "cleaned_wire_remains_lossless",
    "census_counts_only_no_decoded_text",
)

PROFILE_BEGIN = "<!-- clean-rule-profile:begin -->"
PROFILE_END = "<!-- clean-rule-profile:end -->"


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


def build_sample(
    entries: list[Entry], *, seed: int, per_decile: int, tail_n: int
) -> tuple[list[SampleItem], dict[str, int]]:
    """Deterministic stratified sample: per-decile picks + the largest tail.

    Same method as the S02 probe sampler: files are ranked by
    ``(bytes, relative_path)`` and split into ten deciles; a fixed seed draws
    ``per_decile`` files per decile; the ``tail_n`` largest files are added
    unconditionally.  Re-running with the same seed re-selects the same files.
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


# ----------------------------------------------------------------- profile #


def parse_clean_profile(contract_path: Path) -> tuple[str, dict[str, tuple[str, str]]]:
    """Parse the machine-readable clean-rule-profile block, fail-closed.

    Returns ``(profile_id, rules)`` where ``rules`` maps every ReaderSemantic
    class to its ``(rule_id, disposition)``.
    """
    lines = contract_path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(PROFILE_BEGIN)
        stop = lines.index(PROFILE_END, start + 1)
    except ValueError as error:
        raise CensusHarnessError(
            f"census harness error: clean-rule-profile markers missing in {contract_path.name}"
        ) from error

    profile_id: str | None = None
    rules: dict[str, tuple[str, str]] = {}
    for raw in lines[start + 1 : stop]:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("profile:"):
            profile_id = stripped.split(":", 1)[1].strip()
            continue
        fields: dict[str, str] = {}
        for part in stripped.split():
            key, sep, value = part.partition(":")
            if not sep:
                raise CensusHarnessError(
                    f"census harness error: malformed profile line {stripped!r}"
                )
            fields[key] = value
        if set(fields) != {"rule", "class", "disposition"}:
            raise CensusHarnessError(f"census harness error: malformed profile line {stripped!r}")
        if fields["disposition"] not in DISPOSITIONS:
            raise CensusHarnessError(
                f"census harness error: unknown disposition {fields['disposition']!r}"
            )
        if fields["class"] in rules:
            raise CensusHarnessError(
                f"census harness error: duplicate profile class {fields['class']!r}"
            )
        rules[fields["class"]] = (fields["rule"], fields["disposition"])

    if profile_id != PROFILE_ID:
        raise CensusHarnessError(f"census harness error: unexpected profile id {profile_id!r}")
    if len(rules) != len(READER_SEMANTIC_CLASSES) or set(rules) != set(READER_SEMANTIC_CLASSES):
        missing = sorted(set(READER_SEMANTIC_CLASSES) - set(rules))
        extra = sorted(set(rules) - set(READER_SEMANTIC_CLASSES))
        raise CensusHarnessError(
            "census harness error: profile not total over the closed ReaderSemantic "
            f"vocabulary (missing={missing}, extra={extra})"
        )
    return profile_id, rules


# ------------------------------------------------------------------ harness #


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
            "cleaned-project",
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


def tally_export_artifact(artifact_path: Path) -> tuple[dict[str, int], dict[str, int]]:
    """Stream one export artifact and tally semantic/origin tokens only.

    The ``text`` payload of every segment line is parsed and dropped on the
    floor; only the closed-vocabulary tokens are counted.
    """
    per_class: dict[str, int] = {}
    per_origin: dict[str, int] = {}
    with artifact_path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            kind = record.get("kind")
            if kind not in WIRE_LINE_KINDS:
                raise CensusHarnessError(f"census harness error: unknown wire line kind {kind!r}")
            if kind != SEGMENT_LINE_KIND:
                continue
            semantic = record.get("semantic")
            if semantic not in READER_SEMANTIC_CLASSES:
                raise CensusHarnessError(
                    f"census harness error: unknown semantic token {semantic!r}"
                )
            origin = record.get("origin")
            if origin not in ORIGIN_TOKENS:
                raise CensusHarnessError(f"census harness error: unknown origin token {origin!r}")
            per_class[semantic] = per_class.get(semantic, 0) + 1
            per_origin[origin] = per_origin.get(origin, 0) + 1
    return per_class, per_origin


def redaction_check(artifact: dict[str, Any]) -> None:
    """Fail-closed before writing: only counts/hashes/paths/tokens may ship."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN_KEYS:
                    raise CensusHarnessError(
                        f"census harness error: forbidden artifact key {key!r}"
                    )
                if not SAFE_STRING.match(key):
                    raise CensusHarnessError(f"census harness error: unsafe artifact key {key!r}")
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and not SAFE_STRING.match(node):
            raise CensusHarnessError(
                "census harness error: unsafe artifact string (redaction guard)"
            )

    walk(artifact)


def run_census(args: argparse.Namespace) -> dict[str, Any]:
    """Select, export, tally, check coverage, emit the counts-only artifact."""
    started = time.monotonic()

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        raise CensusHarnessError(f"census harness error: manifest not found: {manifest_path}")
    header, entries = parse_manifest(manifest_path)

    corpus_root: Path = args.corpus_root or ROOT / str(header["root"])
    if not corpus_root.is_dir():
        raise CensusHarnessError(f"census harness error: corpus root not found: {corpus_root}")

    sample, strata = build_sample(
        entries, seed=args.seed, per_decile=args.per_decile, tail_n=args.tail_n
    )
    if not SAMPLE_MIN <= len(sample) <= SAMPLE_MAX:
        raise CensusHarnessError(
            f"census harness error: sample size {len(sample)} outside [{SAMPLE_MIN}, {SAMPLE_MAX}]"
        )

    ensure_release_binary(args.bin_path)

    contract_path: Path = args.contract
    if not contract_path.is_file():
        raise CensusHarnessError(f"census harness error: contract not found: {contract_path}")
    profile_id, rules = parse_clean_profile(contract_path)

    per_class_total: dict[str, int] = {}
    per_origin_total: dict[str, int] = {}
    accepted = 0
    for item in sample:
        if time.monotonic() - started > args.budget_wall_s:
            raise CensusHarnessError(
                f"census harness error: budget wall {args.budget_wall_s}s exceeded"
            )
        try:
            with tempfile.TemporaryDirectory(prefix="m223-s05-census-") as tmp:
                artifact = Path(tmp) / "export.jsonl"
                try:
                    result = subprocess.run(
                        [
                            str(args.bin_path),
                            "export",
                            "--from-xml",
                            str(corpus_root / item.relative_path),
                            "--out",
                            str(artifact),
                        ],
                        cwd=ROOT,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=args.export_timeout_s,
                    )
                except subprocess.TimeoutExpired as error:
                    raise CensusHarnessError(
                        "census harness error: export timeout after "
                        f"{args.export_timeout_s}s for {item.relative_path}"
                    ) from error
                except OSError as error:
                    raise CensusHarnessError(
                        f"census harness error: export spawn failed: {type(error).__name__}"
                    ) from error
                if result.returncode != 0 or not artifact.is_file():
                    raise CensusHarnessError(
                        "census harness error: export refused "
                        f"rc={result.returncode} for {item.relative_path}"
                    )
                per_class, per_origin = tally_export_artifact(artifact)
                artifact.unlink()
        except CensusHarnessError:
            raise
        for token, count in per_class.items():
            per_class_total[token] = per_class_total.get(token, 0) + count
        for token, count in per_origin.items():
            per_origin_total[token] = per_origin_total.get(token, 0) + count
        accepted += 1

    if not per_class_total:
        raise CensusHarnessError(
            "census harness error: census observed zero segments over the whole sample "
            "— tally is not evidence, refusing to emit an artifact"
        )

    observed = sorted(per_class_total)
    uncovered = sorted(set(observed) - set(rules))
    if uncovered:
        raise CensusHarnessError(
            f"census harness error: observed classes without a profile disposition: {uncovered}"
        )
    for revision_class, required in REVISION_REQUIRED_DISPOSITIONS.items():
        observed_count = per_class_total.get(revision_class, 0)
        if observed_count > 0 and rules[revision_class][1] != required:
            raise CensusHarnessError(
                f"census harness error: revision class {revision_class} observed but the "
                f"profile does not keep it {required} (observed {observed_count} segments)"
            )

    evidence = {
        "schema": SCHEMA,
        "version": VERSION,
        "profile_id": profile_id,
        "non_claims": list(NON_CLAIMS),
        "manifest_path": relative_label(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_entries": len(entries),
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
        "observed_classes": observed,
        "per_class": dict(sorted(per_class_total.items())),
        "per_origin": dict(sorted(per_origin_total.items())),
        "segments_total": sum(per_class_total.values()),
        "uncovered_classes": uncovered,
        "revision_insertion_observed": per_class_total.get("revision_insertion", 0) > 0,
        "revision_deletion_observed": per_class_total.get("revision_deletion", 0) > 0,
        "exports": {"attempted": len(sample), "accepted": accepted, "failed": 0},
        "wall_s": round(time.monotonic() - started, 3),
    }
    redaction_check(evidence)
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


# --------------------------------------------------------------------- cli #


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--bin", type=Path, default=DEFAULT_BIN, dest="bin_path")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--per-decile", type=int, default=DEFAULT_PER_DECILE)
    parser.add_argument("--tail-n", type=int, default=DEFAULT_TAIL_N)
    parser.add_argument("--export-timeout-s", type=float, default=DEFAULT_EXPORT_TIMEOUT_S)
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
        f"classes={evidence['observed_classes']} "
        f"segments={evidence['segments_total']} out={args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
