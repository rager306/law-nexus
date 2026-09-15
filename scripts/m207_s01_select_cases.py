#!/usr/bin/env python3
"""Deterministic pilot-case draw for the M207 S01 annotation pilot (T02).

This is the offline, fail-closed case-draw gate for the pilot promised by
RC28-F15 ("freeze codebook and independently annotate 20-40 identifying cases
before scaling; do not automatically expand the 180-fragment seed").  It emits
``prd/migration/rust-evidence/m207-s01-pilot-cases.json`` -- 20-40 cases drawn
strictly inside the frozen M199 seed (180 fragments / 40 documents) -- and
``check`` re-derives that artifact byte-for-byte.

Design invariants (each one is enforced, not merely documented):

* **Frozen frame.**  The draw reads only the frozen M199 manifest (sha256-pinned)
  and the frozen fixture ``*.txt`` block texts.  No new fixture file is created
  and no fragment is allocated outside the seed; the fixture tree must stay a
  bijection with the seed and hold exactly 180 ``.txt`` files (``SEED_ENLARGED``).
* **Prediction-free spans.**  The span offered for coding is the *whole* frozen
  decoded block: ``start == 0`` and ``end == byte_len``.  Any narrowing needs a
  predicate over the text, and every such predicate is distant supervision: the
  frozen ``lawref_seed.json`` sidecar (159 rule-seed spans with filled slots)
  must never reach the pilot, and a pre-narrowed window would also bias the span
  measurement S03 has to make.  This builder never opens that sidecar
  (``SPAN_NOT_FULL_FRAGMENT``).
* **Deterministic order.**  Cases are ranked by
  ``sha256(f"{draw_seed}|{document content identity}|{fragment id}")`` and taken
  in that order subject to a cap of ``work_family_cap`` cases per Work family.
  No sorted-prefix draw, no path-derived ordering.
* **Metadata is validated-or-Unknown (D468).**  ``year`` / ``document_type`` are
  either merged from a *declared validated* manifest or explicitly ``unknown``.
  Deriving them from the path is the RC28-F02 defect and is rejected
  (``METADATA_PATH_DERIVED``); the D367/M199 draw stratum is stored separately in
  the explicitly non-validated ``draw_stratum`` field.  The join is measured
  (``join_path_matches``) but only a manifest that declares itself validated
  (sealed + digest + non-proposed lifecycle) may supply values.

Success prints exactly one deterministic line carrying the marker
``M207_S01_SELECT_CASES_OK``.  Every failure is a non-zero exit with named
diagnostics on stderr (``FROZEN_SOURCE_DRIFT``, ``SEED_ENLARGED``,
``CASE_COUNT_OUT_OF_RANGE``, ``SPAN_OUT_OF_BOUNDS``, ``SPAN_NOT_UTF8_BOUNDARY``,
``LEAK_FORBIDDEN_KEY``, ``WORK_FAMILY_DOMINANCE``, ``MANIFEST_DRIFT``, ...).
This slice fabricates no annotation: the artifact is a draw of coding units, not
a coding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S01_SELECT_CASES_OK"
GATE = "M207_S01_SELECT_CASES_GATE"

CASE_SCHEMA_ID = "m207-s01-pilot-cases/v1"
CASE_SCHEMA_VERSION = 1
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
SEED_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
SEED_SHA256 = "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f"
SEED_SCHEMA = "npa-lawref-sample/v1"
METADATA_REL = "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-400.json"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
EXPORT_PREFIX = "consru_export/consru_export/exports/"
FRAGMENT_FILE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*\.txt$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

FIXTURE_TXT_COUNT = 180
SEED_DOCUMENT_COUNT = 40
SEED_FRAGMENT_COUNT = 180
PILOT_DRAW_SEED = 20260915
TARGET_CASES = 40
CASE_COUNT_RANGE = (20, 40)
WORK_FAMILY_CAP = 4
UNKNOWN = "unknown"
METADATA_SOURCES = ("validated-manifest", UNKNOWN)
VALIDATED_LIFECYCLES = ("[validated]", "[sealed]")

# The closed decision space of the codebook (section 3): identical for every
# case, so it can never encode a per-fragment answer.
ALTERNATIVE_CLASSES: list[dict[str, Any]] = [
    {"axis": "reference_decision", "values": ["reference", "not_a_reference"]},
    {"axis": "slot_presence", "values": ["slot_present", "slot_absent"]},
    {"axis": "scope", "values": ["scope_local", "scope_inherited"]},
    {"axis": "binding", "values": ["binding_explicit", "binding_unresolved"]},
]

NON_CLAIMS = [
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not gold: no S01 span or slot is a gold label",
    "not a human pilot: S01 performs no coding and reports no agreement",
    "not product authority: prompt output is AnnotationSuggestion only",
]
LIFECYCLE = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

MANIFEST_CLOSED_KEYS = (
    "schema",
    "schema_version",
    "codebook",
    "source_seed",
    "draw_seed",
    "work_family_cap",
    "case_count",
    "cases",
    "non_claims",
    "lifecycle",
)
SOURCE_SEED_CLOSED_KEYS = ("schema", "sha256", "documents", "fragments", "draw_seed")
CASE_CLOSED_KEYS = (
    "case_id",
    "fragment_id",
    "doc_id",
    "source_path",
    "source_sha256",
    "byte_len",
    "source_block_index",
    "start",
    "end",
    "alternative_classes",
    "abstention_available",
    "span_offered_for_coding",
    "metadata_source",
    "year",
    "document_type",
    "draw_stratum",
    "work_family",
)

FORBIDDEN_KEYS_CANONICAL = ("label", "expected", "answer", "prediction", "gold", "capture")
FORBIDDEN_SEED_KEYS_CANONICAL = (
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots",
)
FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "label",
        "labels",
        "expected",
        "answer",
        "answers",
        "prediction",
        "predictions",
        "predicted",
        "gold",
        "golden",
        "capture",
        "captures",
    }
)
FORBIDDEN_EXACT_KEYS = frozenset(FORBIDDEN_SEED_KEYS_CANONICAL)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")

# Work/edition-family separation (R081).  These patterns are structural
# identities over the frozen source path; they are never parsed back into a
# `year` or `document_type` field.
FORTY_FOUR_FZ_RE = re.compile(r"(?:^|[/_\-])44-fz(?:[/_\-.]|$)")
STEM_HASH_RE = re.compile(r"^(?P<base>.+?)(?:_rev-[^_]*)?_(?P<hash>[0-9a-f]{6,})$")
EDITION_HASH_RE = re.compile(r"^(?P<base>.+?)-edition-(?P<hash>[0-9a-f]{6,})$")

Failures = list[tuple[str, str]]


class GateError(Exception):
    """Fatal, named gate failure that stops the run immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_artifact(
    root: Path,
    raw: str,
    label: str,
    *,
    suffix: str | None = None,
    prefix: str | None = None,
) -> Path:
    """Resolve a repository-relative path, fail-closed on escapes."""
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if suffix is not None and relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix is not None and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(
            "SCHEMA_PARSE_ERROR",
            f"{label} is not closed JSON (YAML, comments, merged or truncated "
            f"documents are rejected): {exc}",
        ) from exc


def key_tokens(key: str) -> list[str]:
    spaced = CAMEL_BOUNDARY_RE.sub("_", key)
    return [token for token in TOKEN_SEPARATOR_RE.split(spaced.lower()) if token]


def forbidden_key_hit(name: str) -> str | None:
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if name.strip().lower() in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_forbidden_keys(node: Any, pointer: str, failures: Failures, *, in_key_list: bool) -> None:
    """Reject predicted-answer and rule-seed key names at any nesting depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            hit = forbidden_key_hit(key)
            if hit is not None:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer}/{key} is a forbidden {hit} key",
                )
            scan_forbidden_keys(value, f"{pointer}/{key}", failures, in_key_list=False)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            scan_forbidden_keys(value, f"{pointer}[{index}]", failures, in_key_list=in_key_list)


def work_family(source_path: str) -> str:
    """Return the R081 Work/edition-family identity of a frozen source path.

    The identity is an opaque grouping token: it is never parsed back into a
    year or a document type, and the case schema forbids such derived values.
    """
    relative = (
        source_path[len(EXPORT_PREFIX) :] if source_path.startswith(EXPORT_PREFIX) else source_path
    )
    parts = relative.split("/")
    name = parts[-1][:-4] if parts[-1].endswith(".xml") else parts[-1]
    if FORTY_FOUR_FZ_RE.search(relative.lower()):
        # One Work: every edition of 44-FZ, including the tracked
        # law-source/consultant member of the M199 44-FZ cluster (M199 §13).
        return "work:law-44fz-cluster"
    if name.startswith("edition-"):
        return "workdir:" + "/".join(parts[:-1])
    for pattern in (EDITION_HASH_RE, STEM_HASH_RE):
        match = pattern.match(name)
        if match is not None:
            return "stem:" + match.group("base")
    return "stem:" + name


def _slug(value: Any) -> str:
    """Return a compact, deterministic token safe for a key=value status line."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-") or "none"


def metadata_source_verdict(manifest: Any) -> tuple[bool, str]:
    """Decide whether a metadata manifest may supply validated metadata (D468).

    A manifest supplies values only when it declares itself validated: sealed,
    carrying a manifest digest, with a non-proposed lifecycle.  Anything else --
    including the C5 ladder manifest, which is ``[proposed]``, unsealed and
    digest-less while its own receipt says "not measured"/"not accepted gold" --
    yields ``unknown`` metadata rather than importing path-derived values.
    """
    if not isinstance(manifest, dict):
        return False, "unvalidated-not-an-object"
    lifecycle = manifest.get("lifecycle")
    if not isinstance(lifecycle, str) or lifecycle not in VALIDATED_LIFECYCLES:
        return False, f"unvalidated-lifecycle-{_slug(lifecycle)}"
    if manifest.get("sealed") is not True:
        return False, "unvalidated-sealed-false"
    digest = manifest.get("manifest_digest")
    if not isinstance(digest, str) or not digest.strip():
        return False, "unvalidated-digest-missing"
    return True, f"validated-lifecycle-{_slug(lifecycle)}"


def metadata_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise GateError("SCHEMA_PARSE_ERROR", "metadata manifest has no entries array")
    index: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise GateError("SCHEMA_PARSE_ERROR", "metadata manifest entry is not an object")
        path = entry.get("document_relative_path")
        if not isinstance(path, str) or not path:
            raise GateError("SCHEMA_PARSE_ERROR", "metadata entry lacks document_relative_path")
        index.setdefault(path, entry)
    return index


def relative_to_export(source_path: str) -> str | None:
    if not source_path.startswith(EXPORT_PREFIX):
        return None
    return source_path[len(EXPORT_PREFIX) :]


def utf8_boundaries(data: bytes, label: str) -> set[int]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("FRAGMENT_NOT_UTF8", f"{label} is not valid UTF-8: {exc}") from exc
    boundaries = {0}
    offset = 0
    for char in text:
        offset += len(char.encode("utf-8"))
        boundaries.add(offset)
    return boundaries


def draw_cases(seed: dict[str, Any]) -> list[dict[str, Any]]:
    """Rank every (document, fragment) pair by content hash and apply the cap."""
    documents = {doc["doc_id"]: doc for doc in seed["documents"]}
    ranked: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for fragment in seed["fragments"]:
        doc = documents[fragment["doc_id"]]
        key = hashlib.sha256(
            f"{PILOT_DRAW_SEED}|{doc['source_sha256']}|{fragment['id']}".encode()
        ).hexdigest()
        ranked.append((key, fragment["id"], fragment, doc))
    ranked.sort(key=lambda row: (row[0], row[1]))
    selected: list[dict[str, Any]] = []
    per_family: dict[str, int] = {}
    for key, fragment_id, fragment, doc in ranked:
        family = work_family(doc["source_path"])
        if per_family.get(family, 0) >= WORK_FAMILY_CAP:
            continue
        per_family[family] = per_family.get(family, 0) + 1
        selected.append(
            {
                "draw_key": key,
                "fragment": fragment,
                "document": doc,
                "work_family": family,
            }
        )
        if len(selected) >= TARGET_CASES:
            break
    return selected


def build_manifest(
    seed: dict[str, Any],
    *,
    seed_sha256: str,
    metadata: dict[str, Any],
    metadata_validated: bool,
    fixture_bytes: dict[str, bytes],
) -> tuple[dict[str, Any], dict[str, int]]:
    index = metadata_index(metadata)
    join_matches = sum(
        1
        for doc in seed["documents"]
        if (rel := relative_to_export(doc["source_path"])) is not None and rel in index
    )
    cases: list[dict[str, Any]] = []
    validated_cases = 0
    for number, selection in enumerate(draw_cases(seed), start=1):
        fragment = selection["fragment"]
        doc = selection["document"]
        data = fixture_bytes.get(fragment["file"])
        if data is None:
            raise GateError(
                "MISSING_ARTIFACT", f"fixture bytes for fragment {fragment['id']} are absent"
            )
        byte_len = len(data)
        rel = relative_to_export(doc["source_path"])
        entry = index.get(rel) if rel is not None else None
        if metadata_validated and entry is not None:
            source = "validated-manifest"
            year = str(entry.get("year", UNKNOWN))
            document_type = str(entry.get("document_type", UNKNOWN))
            validated_cases += 1
        else:
            source = UNKNOWN
            year = UNKNOWN
            document_type = UNKNOWN
        cases.append(
            {
                "case_id": f"m207-s01-case-{number:03d}",
                "fragment_id": fragment["id"],
                "doc_id": doc["doc_id"],
                "source_path": doc["source_path"],
                "source_sha256": doc["source_sha256"],
                "byte_len": byte_len,
                "source_block_index": fragment["source_block_index"],
                "start": 0,
                "end": byte_len,
                "alternative_classes": [dict(axis) for axis in ALTERNATIVE_CLASSES],
                "abstention_available": True,
                "span_offered_for_coding": True,
                "metadata_source": source,
                "year": year,
                "document_type": document_type,
                "draw_stratum": f"{doc['family']}/{doc['doc_type']}",
                "work_family": selection["work_family"],
            }
        )
    manifest = {
        "schema": CASE_SCHEMA_ID,
        "schema_version": CASE_SCHEMA_VERSION,
        "codebook": CODEBOOK_REL,
        "source_seed": {
            "schema": SEED_SCHEMA,
            "sha256": seed_sha256,
            "documents": len(seed["documents"]),
            "fragments": len(seed["fragments"]),
            "draw_seed": seed["draw_seed"],
        },
        "draw_seed": PILOT_DRAW_SEED,
        "work_family_cap": WORK_FAMILY_CAP,
        "case_count": len(cases),
        "cases": cases,
        "non_claims": list(NON_CLAIMS),
        "lifecycle": dict(LIFECYCLE),
    }
    stats = {
        "cases": len(cases),
        "work_families": len({case["work_family"] for case in cases}),
        "metadata_validated_cases": validated_cases,
        "join_path_matches": join_matches,
    }
    return manifest, stats


def check_seed(seed: Any, failures: Failures) -> dict[str, Any]:
    if not isinstance(seed, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "M199 seed manifest is not an object")
        return {}
    if seed.get("schema") != SEED_SCHEMA:
        _fail(failures, "FROZEN_SOURCE_DRIFT", f"M199 seed schema {seed.get('schema')!r}")
    documents = seed.get("documents")
    fragments = seed.get("fragments")
    if not isinstance(documents, list) or not isinstance(fragments, list):
        _fail(failures, "SCHEMA_PARSE_ERROR", "M199 seed lacks documents/fragments arrays")
        return seed
    if len(documents) != SEED_DOCUMENT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed carries {len(documents)} documents, expected {SEED_DOCUMENT_COUNT}",
        )
    if len(fragments) != SEED_FRAGMENT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"M199 seed carries {len(fragments)} fragments, expected {SEED_FRAGMENT_COUNT}",
        )
    for fragment in fragments:
        if fragment.get("status") != "seed":
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"fragment {fragment.get('id')} status {fragment.get('status')!r} is not 'seed'",
            )
        if fragment.get("seed_span") is not None:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"fragment {fragment.get('id')} carries a seed_span; the pilot must stay prediction-free",
            )
    return seed


def check_fixture_tree(
    fixture_dir: Path, seed: dict[str, Any], failures: Failures
) -> dict[str, bytes]:
    declared = {fragment["file"] for fragment in seed.get("fragments", [])}
    if not fixture_dir.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"fixture directory {fixture_dir} does not exist")
        return {}
    on_disk = {path.relative_to(fixture_dir).as_posix() for path in fixture_dir.rglob("*.txt")}
    if len(on_disk) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture tree holds {len(on_disk)} .txt files, expected {FIXTURE_TXT_COUNT}",
        )
    for extra in sorted(on_disk - declared):
        _fail(failures, "SEED_ENLARGED", f"fixture file {extra} is not declared by the M199 seed")
    for missing in sorted(declared - on_disk):
        _fail(failures, "MISSING_ARTIFACT", f"declared fragment file {missing} is absent")
    payload: dict[str, bytes] = {}
    for name in sorted(on_disk & declared):
        if not FRAGMENT_FILE_RE.match(name):
            _fail(failures, "UNSAFE_PATH", f"fragment file name {name!r} is not a safe .txt name")
            continue
        data = (fixture_dir / name).read_bytes()
        payload[name] = data
        if data.startswith(b"\xef\xbb\xbf"):
            _fail(failures, "FRAGMENT_BOM", f"fragment {name} carries a UTF-8 BOM")
        try:
            utf8_boundaries(data, name)
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    return payload


def check_fragment_bindings(
    seed: dict[str, Any], fixture_bytes: dict[str, bytes], failures: Failures
) -> None:
    for fragment in seed.get("fragments", []):
        data = fixture_bytes.get(fragment["file"])
        if data is None:
            continue
        if len(data) != fragment.get("byte_len"):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"fragment {fragment['id']} byte_len drifted: seed "
                f"{fragment.get('byte_len')} != file {len(data)}",
            )


def _manifest_cases(artifact: Any, failures: Failures) -> list[Any]:
    if not isinstance(artifact, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest is not an object")
        return []
    cases = artifact.get("cases")
    if not isinstance(cases, list):
        _fail(failures, "SCHEMA_PARSE_ERROR", "case manifest has no cases array")
        return []
    return cases


def _exact_keys(node: Any, expected: tuple[str, ...], pointer: str, failures: Failures) -> None:
    if not isinstance(node, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", f"{pointer} is not an object")
        return
    actual = set(node)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{pointer} closed keys drifted (missing={missing}, extra={extra})",
        )


def inspect_manifest(
    artifact: Any,
    *,
    seed: dict[str, Any],
    fixture_bytes: dict[str, bytes],
    metadata: dict[str, Any],
    metadata_validated: bool,
    failures: Failures,
) -> None:
    """Structurally validate an on-disk case manifest, fail-closed."""
    if artifact is None:
        return
    _exact_keys(artifact, MANIFEST_CLOSED_KEYS, "manifest", failures)
    scan_forbidden_keys(artifact, "", failures, in_key_list=False)
    if not isinstance(artifact, dict):
        return
    _exact_keys(artifact.get("source_seed"), SOURCE_SEED_CLOSED_KEYS, "source_seed", failures)
    if artifact.get("schema") != CASE_SCHEMA_ID:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"manifest schema {artifact.get('schema')!r}")
    if artifact.get("codebook") != CODEBOOK_REL:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"manifest codebook {artifact.get('codebook')!r}")
    if artifact.get("draw_seed") != PILOT_DRAW_SEED:
        _fail(
            failures,
            "DRAW_SEED_DRIFT",
            f"manifest draw_seed {artifact.get('draw_seed')!r} != {PILOT_DRAW_SEED}",
        )
    if artifact.get("work_family_cap") != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"manifest work_family_cap {artifact.get('work_family_cap')!r} != {WORK_FAMILY_CAP}",
        )
    if artifact.get("non_claims") != NON_CLAIMS:
        _fail(failures, "MISSING_NON_CLAIM", "manifest non_claims drifted from the codebook set")
    if artifact.get("lifecycle") != LIFECYCLE:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            "manifest lifecycle markers drifted from the codebook set",
        )
    cases = _manifest_cases(artifact, failures)
    case_count = artifact.get("case_count")
    if not isinstance(case_count, int) or case_count != len(cases):
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"manifest case_count {case_count!r} does not match {len(cases)} cases",
        )
    if not CASE_COUNT_RANGE[0] <= len(cases) <= CASE_COUNT_RANGE[1]:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"draw holds {len(cases)} cases, outside {list(CASE_COUNT_RANGE)}",
        )

    documents = {doc["doc_id"]: doc for doc in seed.get("documents", [])}
    fragments = {fragment["id"]: fragment for fragment in seed.get("fragments", [])}
    strata = {
        f"{row['family']}/{row['doc_type']}"
        for row in seed.get("strata", [])
        if isinstance(row, dict)
    }
    index = metadata_index(metadata) if metadata else {}
    per_family: dict[str, int] = {}
    case_ids: set[str] = set()
    for number, case in enumerate(cases):
        pointer = f"cases[{number}]"
        _exact_keys(case, CASE_CLOSED_KEYS, pointer, failures)
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        expected_id = f"m207-s01-case-{number + 1:03d}"
        if case_id != expected_id:
            _fail(
                failures,
                "CASE_ORDER_DRIFT",
                f"{pointer} case_id {case_id!r} != deterministic {expected_id!r}",
            )
        if case_id in case_ids:
            _fail(failures, "DUPLICATE_CASE", f"{pointer} duplicates case_id {case_id!r}")
        case_ids.add(case_id)

        fragment = fragments.get(case.get("fragment_id"))
        if fragment is None:
            _fail(failures, "UNKNOWN_FRAGMENT", f"{pointer} references {case.get('fragment_id')!r}")
            continue
        doc = documents.get(fragment["doc_id"])
        if doc is None or case.get("doc_id") != fragment["doc_id"]:
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} doc binding is not the seed document")
            continue
        if case.get("source_path") != doc["source_path"]:
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_path drifted from the seed")
        if case.get("source_sha256") != doc["source_sha256"]:
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_sha256 drifted from the seed")
        if not isinstance(case.get("source_sha256"), str) or not SHA256_RE.match(
            case["source_sha256"]
        ):
            _fail(failures, "PROVENANCE_DRIFT", f"{pointer} source_sha256 is not 64 hex chars")
        if case.get("source_block_index") != fragment["source_block_index"]:
            _fail(
                failures,
                "PROVENANCE_DRIFT",
                f"{pointer} source_block_index drifted from the seed fragment",
            )
        data = fixture_bytes.get(fragment["file"])
        if data is not None and case.get("byte_len") != len(data):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"{pointer} byte_len {case.get('byte_len')!r} != frozen fragment {len(data)}",
            )
        if case.get("byte_len") != fragment.get("byte_len"):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"{pointer} byte_len drifted from the seed fragment byte_len",
            )

        start, end, byte_len = case.get("start"), case.get("end"), case.get("byte_len")
        if not all(isinstance(value, int) for value in (start, end, byte_len)):
            _fail(failures, "SPAN_OUT_OF_BOUNDS", f"{pointer} span fields are not integers")
        elif not 0 <= start < end <= byte_len:
            _fail(
                failures,
                "SPAN_OUT_OF_BOUNDS",
                f"{pointer} span [{start}, {end}) is empty or past EOF (byte_len={byte_len})",
            )
        elif data is not None:
            boundaries = utf8_boundaries(data, fragment["file"])
            if start not in boundaries or end not in boundaries:
                _fail(
                    failures,
                    "SPAN_NOT_UTF8_BOUNDARY",
                    f"{pointer} span [{start}, {end}) splits a UTF-8 code point",
                )
            if (start, end) != (0, len(data)):
                _fail(
                    failures,
                    "SPAN_NOT_FULL_FRAGMENT",
                    f"{pointer} offered span [{start}, {end}) is not the frozen decoded block; "
                    "a narrowed window would import a prediction",
                )

        if case.get("alternative_classes") != ALTERNATIVE_CLASSES:
            _fail(
                failures,
                "ALTERNATIVES_DRIFT",
                f"{pointer} alternative_classes drifted from the closed codebook decision space",
            )
        if case.get("abstention_available") is not True:
            _fail(failures, "ABSTENTION_COLLAPSE", f"{pointer} abstention_available is not true")
        if case.get("span_offered_for_coding") is not True:
            _fail(failures, "OFFER_FLAG_DRIFT", f"{pointer} span_offered_for_coding is not true")
        stratum = f"{doc['family']}/{doc['doc_type']}"
        if case.get("draw_stratum") != stratum:
            _fail(
                failures,
                "STRATUM_DRIFT",
                f"{pointer} draw_stratum {case.get('draw_stratum')!r} != {stratum!r}",
            )
        if strata and stratum not in strata:
            _fail(failures, "STRATUM_DRIFT", f"{pointer} stratum {stratum!r} not declared by M199")
        if case.get("work_family") != work_family(doc["source_path"]):
            _fail(
                failures,
                "WORK_FAMILY_DRIFT",
                f"{pointer} work_family {case.get('work_family')!r} is not the R081 identity",
            )
        per_family[case["work_family"]] = per_family.get(case["work_family"], 0) + 1

        source = case.get("metadata_source")
        if source not in METADATA_SOURCES:
            _fail(
                failures,
                "METADATA_PATH_DERIVED",
                f"{pointer} metadata_source {source!r} is outside {list(METADATA_SOURCES)}",
            )
        elif source == UNKNOWN:
            if case.get("year") != UNKNOWN or case.get("document_type") != UNKNOWN:
                _fail(
                    failures,
                    "METADATA_PATH_DERIVED",
                    f"{pointer} carries year/document_type without a validated manifest",
                )
        elif not metadata_validated:
            _fail(
                failures,
                "METADATA_SOURCE_UNVALIDATED",
                f"{pointer} claims validated-manifest while the source manifest is not validated",
            )
        elif case.get("year") != str(
            index[relative_to_export(doc["source_path"])].get("year", UNKNOWN)
        ):
            _fail(
                failures,
                "METADATA_PATH_DERIVED",
                f"{pointer} year does not come from the validated manifest",
            )

    for family, count in sorted(per_family.items()):
        if count > WORK_FAMILY_CAP:
            _fail(
                failures,
                "WORK_FAMILY_DOMINANCE",
                f"Work family {family!r} contributes {count} cases, above cap {WORK_FAMILY_CAP}",
            )


def render(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def run(mode: str, args: argparse.Namespace) -> tuple[Failures, str]:
    root = Path(args.root)
    if not root.is_dir():
        return [("MISSING_ARTIFACT", f"root {root} is not a directory")], ""
    try:
        seed_path = resolve_artifact(root, args.seed_manifest, "seed-manifest", suffix=".json")
        cases_path = resolve_artifact(root, args.cases, "cases", suffix=".json")
        metadata_path = resolve_artifact(
            root, args.metadata_manifest, "metadata-manifest", suffix=".json"
        )
        fixture_dir = resolve_artifact(root, args.fixture_dir, "fixture-dir")
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)], ""
    failures: Failures = []

    if not seed_path.is_file():
        return [("MISSING_ARTIFACT", f"M199 seed manifest missing at {args.seed_manifest}")], ""
    seed_sha256 = sha256_file(seed_path)
    if seed_sha256 != SEED_SHA256:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"M199 seed sha256 {seed_sha256} != pinned {SEED_SHA256}",
        )
    try:
        seed = check_seed(load_json(seed_path, "M199 seed manifest"), failures)
    except GateError as exc:
        return failures + [(exc.diagnostic, exc.detail)], ""
    if not isinstance(seed, dict) or "documents" not in seed:
        return failures, ""
    fixture_bytes = check_fixture_tree(fixture_dir, seed, failures)
    check_fragment_bindings(seed, fixture_bytes, failures)
    absent = [
        fragment["id"] for fragment in seed["fragments"] if fragment["file"] not in fixture_bytes
    ]
    if absent:
        _fail(
            failures,
            "MISSING_ARTIFACT",
            f"{len(absent)} declared fragment file(s) have no bytes, e.g. {absent[0]}",
        )
        return failures, ""

    try:
        metadata = load_json(metadata_path, "metadata manifest")
    except GateError as exc:
        return failures + [(exc.diagnostic, exc.detail)], ""
    metadata_validated, verdict = metadata_source_verdict(metadata)

    manifest, stats = build_manifest(
        seed,
        seed_sha256=seed_sha256,
        metadata=metadata if isinstance(metadata, dict) else {},
        metadata_validated=metadata_validated,
        fixture_bytes=fixture_bytes,
    )
    inspect_manifest(
        manifest,
        seed=seed,
        fixture_bytes=fixture_bytes,
        metadata=metadata if isinstance(metadata, dict) else {},
        metadata_validated=metadata_validated,
        failures=failures,
    )

    payload = render(manifest)
    if mode == "write":
        if not failures:
            cases_path.parent.mkdir(parents=True, exist_ok=True)
            cases_path.write_bytes(payload)
    else:
        if not cases_path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"case manifest missing at {args.cases}")
        else:
            on_disk = cases_path.read_bytes()
            try:
                inspect_manifest(
                    load_json(cases_path, "case manifest"),
                    seed=seed,
                    fixture_bytes=fixture_bytes,
                    metadata=metadata if isinstance(metadata, dict) else {},
                    metadata_validated=metadata_validated,
                    failures=failures,
                )
            except GateError as exc:
                _fail(failures, exc.diagnostic, exc.detail)
            if on_disk != payload:
                _fail(
                    failures,
                    "MANIFEST_DRIFT",
                    f"on-disk {args.cases} is not the deterministic regeneration "
                    f"({len(on_disk)} vs {len(payload)} bytes)",
                )

    summary = (
        f"{MARKER} mode={mode} cases={stats['cases']} work_families={stats['work_families']} "
        f"draw_seed={PILOT_DRAW_SEED} fixture_txt={len(fixture_bytes)} "
        f"metadata_verdict={verdict} metadata_validated_cases={stats['metadata_validated_cases']} "
        f"join_path_matches={stats['join_path_matches']}"
    )
    return failures, summary


def report(failures: Failures, summary: str) -> int:
    if failures:
        for diagnostic, detail in failures:
            print(f"FAIL {diagnostic}: {detail}", file=sys.stderr)
        print(f"FAIL {GATE}: {len(failures)} finding(s)", file=sys.stderr)
        return 1
    print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "write"],
        help="'check' re-derives the manifest byte-for-byte; 'write' emits it",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--seed-manifest", default=SEED_REL, help="frozen M199 seed manifest")
    parser.add_argument("--cases", default=CASES_REL, help="pilot case manifest path")
    parser.add_argument(
        "--metadata-manifest", default=METADATA_REL, help="declared metadata manifest to join"
    )
    parser.add_argument(
        "--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment fixture dir"
    )
    args = parser.parse_args(argv)
    failures, summary = run(args.mode, args)
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
