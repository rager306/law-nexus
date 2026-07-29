#!/usr/bin/env python3
"""Build deterministic non-authoritative Consultant WordML hierarchy records.

This command parses the canonical ConsultantPlus Word 2003 WordML fixture with a
streaming paragraph reader. It emits context-first hierarchy/source records only;
it does not claim legal correctness, parser completeness, or authoritative legal
interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from law_nexus.adapters.sources.consultant_hierarchy import normalize_text as _normalize_text
from law_nexus.adapters.sources.consultant_hierarchy import stream_wordml_paragraphs
from law_nexus.composition import make_consultant_hierarchy_use_case
from law_nexus.ports.source_hierarchy import SourceHierarchyParagraph, SourceHierarchyRequest
from parser_records import dumps_jsonl_record, parse_parser_record

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = Path(
    "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml"
)
INVENTORY_PATH = Path("prd/parser/source_fixture_inventory.json")
# Single-mode outputs (canonical 44-FZ-2026 fixture only, 2185 records).
# Corpus consumers must NOT read these paths; they read the corpus paths below.
JSONL_PATH = Path("prd/parser/consultant_hierarchy_records.jsonl")
JSON_PATH = Path("prd/parser/consultant_hierarchy_records.json")
REPORT_PATH = Path("prd/parser/consultant_hierarchy_records.md")
# Corpus-mode outputs (all in-scope fixtures: 7 federal_law + 3 code, 15249 records).
# Downstream relation/norm/retrieval/staging builders consume corpus paths so
# that single-mode and corpus-mode baselines no longer overwrite each other.
CORPUS_JSONL_PATH = Path("prd/parser/consultant_hierarchy_corpus_records.jsonl")
CORPUS_JSON_PATH = Path("prd/parser/consultant_hierarchy_corpus_records.json")
CORPUS_REPORT_PATH = Path("prd/parser/consultant_hierarchy_corpus_records.md")
#: Canonical baseline manifest recording deterministic source/output hashes for both modes.
BASELINE_MANIFEST_PATH = Path("prd/parser/consultant_hierarchy_baseline_manifest.json")
MANIFEST_SCHEMA_VERSION = "consultant-hierarchy-baseline-manifest/v1"
#: Repo-relative path to this generator script (used by manifest provenance).
GENERATOR_PATH = Path("scripts/build-consultant-hierarchy-records.py")
MAX_DIAGNOSTICS = 100
#: In-scope document types for M072 S05 hierarchy extraction. These are the
#: source-roles that have a normative-act structure (full-federal-law + code).
#: Other source-roles (court decisions, antimonopoly decisions, government
#: resolutions, lists, reviews, ODT) are out-of-scope and get a documented
#: 'no hierarchy' statement in the corpus report.
IN_SCOPE_DOCUMENT_TYPES: tuple[str, ...] = ("federal_law", "code")
NON_CLAIMS = [
    "Consultant hierarchy records are deterministic parser-source records only.",
    "Consultant hierarchy records do not claim legal correctness or authoritative legal interpretation.",
    "Consultant hierarchy records do not claim parser completeness.",
    "Consultant hierarchy records do not claim product ETL or FalkorDB load readiness.",
]

Paragraph = SourceHierarchyParagraph
normalize_text = _normalize_text


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved repo-relative output paths for one build mode."""

    jsonl: Path
    json: Path
    report: Path
    mode: str


#: Single-mode (canonical 44-FZ-2026 fixture) artifact paths.
SINGLE_PATHS = ArtifactPaths(jsonl=JSONL_PATH, json=JSON_PATH, report=REPORT_PATH, mode="single")
#: Corpus-mode (all in-scope fixtures) artifact paths.
CORPUS_PATHS = ArtifactPaths(
    jsonl=CORPUS_JSONL_PATH, json=CORPUS_JSON_PATH, report=CORPUS_REPORT_PATH, mode="corpus"
)


@dataclass(frozen=True)
class BuildResult:
    """Generated artifacts and diagnostics for one build mode."""

    records: list[dict[str, Any]]
    jsonl: str
    summary_json: str
    report_md: str
    diagnostics: dict[str, Any]
    paths: ArtifactPaths


def stable_json(data: Any) -> str:
    """Return deterministic pretty JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(path: Path) -> str:
    """Return SHA-256 of a source file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truncate(text: str, limit: int) -> str:
    """Return a bounded string without splitting deterministic behavior across callers."""

    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def compact_error(kind: str, message: str, **extra: Any) -> dict[str, Any]:
    """Return a bounded deterministic diagnostic error."""

    payload = {"kind": kind, "message": truncate(str(message), 240)}
    payload.update(extra)
    return payload


def _derive_scope_id(path: str) -> str:
    """Derive a deterministic ASCII-safe scope id from a fixture path.

    The scope id prefixes all hierarchy record ids emitted for that fixture
    (e.g. ``CONS-FL-44-FZ-2026``, ``CONS-CODE-BK-145-FZ``). It must be unique
    across the in-scope corpus so that concatenated JSONL output has no id
    collisions.
    """

    stem = Path(path).stem
    ascii_safe = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-")[:24]
    if not ascii_safe:
        ascii_safe = re.sub(r"[^A-Za-z0-9]+", "-", Path(path).name).strip("-")[:24]
    return f"CONS-{ascii_safe}" if ascii_safe else "CONS-UNKNOWN"


def _document_id(scope_id: str) -> str:
    """Stable document record id derived from the per-fixture scope id."""

    return f"DOC-{scope_id}"


def _document_hierarchy_id(scope_id: str) -> str:
    """Stable document-hierarchy (root) record id for a fixture."""

    return f"HIER-{scope_id}-DOCUMENT"


def load_inventory_fixture(
    target_path: str = str(SOURCE_PATH),
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load the canonical inventory entry for the given target fixture path."""

    inventory_path = ROOT / INVENTORY_PATH
    if not inventory_path.exists():
        return None, [
            compact_error(
                "missing_inventory",
                f"inventory file missing: {INVENTORY_PATH}",
                path=str(INVENTORY_PATH),
            )
        ]

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [compact_error("malformed_inventory_json", str(exc), path=str(INVENTORY_PATH))]

    for fixture in payload.get("fixtures", []):
        if fixture.get("path") == target_path:
            return fixture, []
    return None, [
        compact_error(
            "missing_inventory_fixture",
            f"canonical inventory fixture missing: {target_path}",
            path=target_path,
        )
    ]


def hierarchy_records(
    paragraphs: list[Paragraph],
    source_sha256: str,
    *,
    scope_id: str,
    document_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract hierarchy records using the package-level Consultant builder seam."""

    request = SourceHierarchyRequest(
        paragraphs=[
            SourceHierarchyParagraph(
                index=paragraph.index, text=paragraph.text, style=paragraph.style
            )
            for paragraph in paragraphs
        ],
        source_sha256=source_sha256,
        scope_id=scope_id,
        document_id=document_id,
        source_path=source_path,
    )
    result = make_consultant_hierarchy_use_case().build_records(request)
    for record in result.records:
        parse_parser_record(record)
    return result.records, result.diagnostics


def build_for_fixture(
    source_path: Path, scope_id: str, paths: ArtifactPaths = SINGLE_PATHS
) -> BuildResult:
    """Build all Consultant hierarchy artifacts in memory for a single fixture.

    ``source_path`` is the repo-relative path to the Consultant WordML
    fixture; ``scope_id`` is the per-fixture id prefix (see :func:`_derive_scope_id`).
    ``paths`` selects whether the summary records single-mode or corpus-mode
    artifact paths. The returned :class:`BuildResult` carries records, jsonl
    text, summary json, report markdown, and diagnostics for that fixture only.
    """

    source = ROOT / source_path
    fatal_errors: list[dict[str, Any]] = []
    inventory_fixture, inventory_errors = load_inventory_fixture(target_path=str(source_path))
    fatal_errors.extend(inventory_errors)

    if source.exists():
        source_sha256 = sha256_bytes(source)
        paragraphs, stream_diagnostics = stream_wordml_paragraphs(source)
    else:
        source_sha256 = None
        paragraphs = []
        stream_diagnostics = {
            "malformed_xml": None,
            "namespace_detected": None,
            "namespace_observations": {},
            "paragraph_count": 0,
            "style_observations": {},
            "skipped_empty_paragraphs": 0,
        }
        fatal_errors.append(
            compact_error(
                "missing_source", f"source fixture missing: {source_path}", path=str(source_path)
            )
        )

    inventory_sha256 = None if inventory_fixture is None else inventory_fixture.get("sha256")
    document_id = _document_id(scope_id)
    records, hierarchy_diagnostics = (
        hierarchy_records(
            paragraphs,
            source_sha256 or "0" * 64,
            scope_id=scope_id,
            document_id=document_id,
            source_path=str(source_path),
        )
        if not fatal_errors and stream_diagnostics["malformed_xml"] is None
        else (
            [],
            {
                "emitted_counts_by_level": {},
                "skipped_marker_counts": {},
                "rejected_context_marker_count": 0,
                "rejected_context_markers": [],
                "structural_errors": [],
                "structural_error_count": 0,
                "validation_errors": [],
                "validation_error_count": 0,
            },
        )
    )

    inventory_hash_matches = (
        source_sha256 == inventory_sha256
        if source_sha256 is not None and inventory_sha256 is not None
        else False
    )
    jsonl = "".join(dumps_jsonl_record(record) + "\n" for record in records)
    summary = {
        "scope_id": scope_id,
        "document_id": document_id,
        "artifact_paths": {
            "json": str(paths.json),
            "jsonl": str(paths.jsonl),
            "report": str(paths.report),
        },
        "artifact_freshness": None,
        "diagnostics_bounded": True,
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "fatal_error_count": len(fatal_errors),
        "non_authoritative": True,
        "phase": "consultant_wordml_hierarchy_build",
        "source": {
            "inventory_hash_matches": inventory_hash_matches,
            "inventory_sha256": inventory_sha256,
            "path": str(source_path),
            "sha256": source_sha256,
        },
        **stream_diagnostics,
        **hierarchy_diagnostics,
    }
    summary_json = stable_json(summary)
    report_md = render_report(summary, records)
    return BuildResult(
        records=records,
        jsonl=jsonl,
        summary_json=summary_json,
        report_md=report_md,
        diagnostics=summary,
        paths=paths,
    )


def build() -> BuildResult:
    """Build all Consultant hierarchy artifacts in memory for the canonical fixture.

    Convenience wrapper that delegates to :func:`build_for_fixture` with the
    legacy ``CONS`` scope id so existing tests, downstream consumers, and the
    documented default behaviour (44-FZ-2026 only) are preserved.
    """

    return build_for_fixture(SOURCE_PATH, "CONS")


def build_corpus() -> BuildResult:
    """Build Consultant hierarchy records for all in-scope fixtures in the corpus.

    In-scope is defined by :data:`IN_SCOPE_DOCUMENT_TYPES` (currently
    ``federal_law`` and ``code`` — the source-roles with normative-act
    structure). Other roles (court decisions, antimonopoly decisions,
    government resolutions, lists, reviews, ODT) are documented as
    out-of-scope in the corpus report. The returned :class:`BuildResult`
    carries concatenated records across all in-scope fixtures plus a
    per-fixture summary and a scope statement.
    """

    inventory_path = ROOT / INVENTORY_PATH
    if not inventory_path.exists():
        return _corpus_fatal(
            ("missing_inventory", f"inventory file missing: {INVENTORY_PATH}", str(INVENTORY_PATH))
        )

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _corpus_fatal(("malformed_inventory_json", exc, str(INVENTORY_PATH)))

    fixtures = payload.get("fixtures", [])
    if not isinstance(fixtures, list):
        return _corpus_fatal(
            ("inventory_shape_invalid", "Inventory fixtures must be a list.", str(INVENTORY_PATH))
        )

    in_scope_fixtures: list[dict[str, Any]] = []
    out_of_scope_by_role: dict[str, list[dict[str, Any]]] = {}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        doc_type = fixture.get("document_type")
        if doc_type in IN_SCOPE_DOCUMENT_TYPES:
            in_scope_fixtures.append(fixture)
        else:
            out_of_scope_by_role.setdefault(doc_type or "unknown", []).append(fixture)

    all_records: list[dict[str, Any]] = []
    per_fixture_summaries: list[dict[str, Any]] = []
    fatal_errors: list[dict[str, Any]] = []

    for fixture in in_scope_fixtures:
        path_str = str(fixture.get("path", ""))
        scope_id = _derive_scope_id(path_str)
        fixture_result = build_for_fixture(Path(path_str), scope_id)
        if fixture_result.diagnostics.get("fatal_error_count", 0) > 0:
            fatal_errors.extend(fixture_result.diagnostics["fatal_errors"])
            continue
        if fixture_result.diagnostics.get("malformed_xml") is not None:
            fatal_errors.append(
                compact_error(
                    "fixture_malformed",
                    f"fixture {path_str} produced malformed XML",
                    path=path_str,
                )
            )
            continue
        all_records.extend(fixture_result.records)
        per_fixture_summaries.append(
            {
                "scope_id": scope_id,
                "path": path_str,
                "document_type": fixture.get("document_type"),
                "record_count": len(fixture_result.records),
                "emitted_counts_by_level": fixture_result.diagnostics.get(
                    "emitted_counts_by_level", {}
                ),
                "source_sha256": fixture_result.diagnostics.get("source", {}).get("sha256"),
                "structural_error_count": fixture_result.diagnostics.get(
                    "structural_error_count", 0
                ),
            }
        )

    # Verify id uniqueness across the concatenated corpus.
    record_ids = [record["id"] for record in all_records]
    id_collisions: list[dict[str, Any]] = []
    if len(record_ids) != len(set(record_ids)):
        seen: set[str] = set()
        for record_id in record_ids:
            if record_id in seen and record_id not in {c["id"] for c in id_collisions}:
                id_collisions.append({"id": record_id})
            seen.add(record_id)

    out_of_scope_breakdown = [
        {
            "document_type": doc_type,
            "fixture_count": len(roles_fixtures),
            "reason": _scope_reason_for(doc_type),
        }
        for doc_type, roles_fixtures in sorted(out_of_scope_by_role.items())
    ]

    corpus_jsonl = "".join(dumps_jsonl_record(record) + "\n" for record in all_records)
    corpus_summary = {
        "schema_version": "consultant-hierarchy-corpus/v1",
        "phase": "consultant_wordml_hierarchy_corpus_build",
        "non_authoritative": True,
        "non_claims": [
            "Consultant hierarchy corpus records are deterministic parser-source records only.",
            "The corpus does not claim legal correctness or authoritative legal interpretation.",
            "The corpus does not claim parser completeness for non-in-scope document kinds.",
            "The corpus does not claim product ETL or FalkorDB load readiness.",
            "Out-of-scope fixtures are documented but not silently skipped — they remain on disk awaiting a later scope expansion.",
        ],
        "in_scope_document_types": list(IN_SCOPE_DOCUMENT_TYPES),
        "in_scope_fixtures": per_fixture_summaries,
        "out_of_scope": out_of_scope_breakdown,
        "totals": {
            "in_scope_fixture_count": len(per_fixture_summaries),
            "out_of_scope_fixture_count": sum(
                item["fixture_count"] for item in out_of_scope_breakdown
            ),
            "record_count": len(all_records),
            "unique_record_id_count": len(set(record_ids)),
            "id_collision_count": len(id_collisions),
        },
        "id_collisions": id_collisions[:MAX_DIAGNOSTICS],
        "artifact_paths": {
            "json": str(CORPUS_JSON_PATH),
            "jsonl": str(CORPUS_JSONL_PATH),
            "report": str(CORPUS_REPORT_PATH),
        },
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "fatal_error_count": len(fatal_errors),
    }
    corpus_json = stable_json(corpus_summary)
    corpus_md = render_corpus_report(corpus_summary, all_records, per_fixture_summaries)
    return BuildResult(
        records=all_records,
        jsonl=corpus_jsonl,
        summary_json=corpus_json,
        report_md=corpus_md,
        diagnostics=corpus_summary,
        paths=CORPUS_PATHS,
    )


def _scope_reason_for(document_type: str) -> str:
    """Return a one-line human-readable reason for a document_type being out of scope."""

    out_of_scope_reasons = {
        "code_amendment_overview": "Amendment overview; not a full normative-act source-shape.",
        "court_practice_review": "Court practice review; not a full normative-act source-shape.",
        "fas_review": "FAS / Treasury review; not a full normative-act source-shape.",
        "government_resolution": "Government resolution; structure is non-hierarchical for M072 S05 scope.",
        "constitutional_court_ruling": "Court ruling; treated as citation-evidence, not a full hierarchy.",
        "supreme_court_ruling": "Court ruling; treated as citation-evidence, not a full hierarchy.",
        "lower_court_ruling": "Lower court ruling; treated as citation-evidence, not a full hierarchy.",
        "antimonopoly_decision": "Antimonopoly decision; non-hierarchical structure for S05 scope.",
        "document_list": "Document list (relation candidate, not hierarchy).",
        "other_document": "Unclassified title; not a full normative-act source-shape.",
        "odt_document": "Garant ODT fixture; covered by separate ODT smoke path, not by Consultant parser.",
    }
    return out_of_scope_reasons.get(
        document_type,
        "Out of scope for hierarchy extraction; reserved for a later scope expansion.",
    )


def _corpus_fatal(error_payload: tuple) -> BuildResult:
    """Build a fatal-only :class:`BuildResult` for a corpus that cannot even start."""

    fatal_error_count = 1
    fatal_errors = [compact_error(*error_payload)]
    summary = {
        "schema_version": "consultant-hierarchy-corpus/v1",
        "phase": "consultant_wordml_hierarchy_corpus_build",
        "non_authoritative": True,
        "in_scope_document_types": list(IN_SCOPE_DOCUMENT_TYPES),
        "in_scope_fixtures": [],
        "out_of_scope": [],
        "totals": {
            "in_scope_fixture_count": 0,
            "out_of_scope_fixture_count": 0,
            "record_count": 0,
            "unique_record_id_count": 0,
            "id_collision_count": 0,
        },
        "id_collisions": [],
        "artifact_paths": {
            "json": str(JSON_PATH),
            "jsonl": str(JSONL_PATH),
            "report": str(REPORT_PATH),
        },
        "fatal_errors": fatal_errors,
        "fatal_error_count": fatal_error_count,
    }
    return BuildResult(
        records=[],
        jsonl="",
        summary_json=stable_json(summary),
        report_md="",
        diagnostics=summary,
    )


def render_corpus_report(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    per_fixture_summaries: list[dict[str, Any]],
) -> str:
    """Render a compact deterministic Markdown report for the corpus build."""

    totals = summary.get("totals", {})
    lines = [
        "# Consultant WordML Hierarchy Corpus (M072 S05)",
        "",
        "This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness. Out-of-scope fixtures are documented below; they remain on disk awaiting a later scope expansion (no silent skipping).",
        "",
        "## Scope",
        "",
        f"- In-scope document types: `{', '.join(summary.get('in_scope_document_types', []))}`",
        f"- In-scope fixtures: `{totals.get('in_scope_fixture_count', 0)}`",
        f"- Out-of-scope fixtures: `{totals.get('out_of_scope_fixture_count', 0)}`",
        f"- Total records emitted: `{totals.get('record_count', 0)}`",
        f"- Unique record ids: `{totals.get('unique_record_id_count', 0)}`",
        f"- ID collisions: `{totals.get('id_collision_count', 0)}`",
        f"- Fatal errors: `{summary.get('fatal_error_count', 0)}`",
        "",
        "## In-scope per-fixture breakdown",
        "",
        "| Scope id | Source path | Document type | Records | Levels | SHA-256 |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for entry in per_fixture_summaries:
        levels = entry.get("emitted_counts_by_level", {}) or {}
        levels_compact = ", ".join(f"{k}={v}" for k, v in sorted(levels.items()))
        lines.append(
            f"| `{entry.get('scope_id')}` | `{entry.get('path')}` | `{entry.get('document_type')}` | {entry.get('record_count', 0)} | {levels_compact} | `{entry.get('source_sha256')}` |"
        )
    lines.extend(
        [
            "",
            "## Out-of-scope fixtures (documented, not silently skipped)",
            "",
            "| Document type | Fixture count | Reason |",
            "| --- | ---: | --- |",
        ]
    )
    for entry in summary.get("out_of_scope", []):
        lines.append(
            f"| `{entry['document_type']}` | {entry['fixture_count']} | {entry['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Non-claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in summary.get("non_claims", []))
    lines.append("")
    return "\n".join(lines)


def freshness_map(expected: dict[Path, str]) -> dict[str, bool]:
    """Return whether generated artifact content matches files on disk."""

    result: dict[str, bool] = {}
    for relative_path, content in expected.items():
        path = ROOT / relative_path
        result[str(relative_path)] = path.exists() and path.read_text(encoding="utf-8") == content
    return result


def render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    """Render a compact deterministic Markdown diagnostic report."""

    counts = summary.get("emitted_counts_by_level", {})
    lines = [
        "# Consultant WordML hierarchy records",
        "",
        "This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness.",
        "",
        "## Source",
        "",
        f"- Path: `{summary['source']['path']}`",
        f"- SHA-256: `{summary['source']['sha256']}`",
        f"- Inventory hash matches: `{str(summary['source']['inventory_hash_matches']).lower()}`",
        f"- WordML namespace detected: `{summary.get('namespace_detected')}`",
        "",
        "## Counts",
        "",
        f"- Source paragraphs: `{summary.get('paragraph_count')}`",
        f"- Empty paragraphs skipped: `{summary.get('skipped_empty_paragraphs')}`",
        f"- Records emitted: `{len(records)}`",
    ]
    for level, count in counts.items():
        lines.append(f"- `{level}`: `{count}`")
    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            f"- Malformed XML: `{summary.get('malformed_xml')}`",
            f"- Validation errors: `{summary.get('validation_error_count', 0)}`",
            f"- Structural errors: `{summary.get('structural_error_count', 0)}`",
            f"- Rejected context markers: `{summary.get('rejected_context_marker_count', 0)}`",
            f"- Fatal errors: `{summary.get('fatal_error_count', 0)}`",
            f"- Skipped marker counts: `{json.dumps(summary.get('skipped_marker_counts', {}), ensure_ascii=False, sort_keys=True)}`",
            f"- Style observations: `{json.dumps(summary.get('style_observations', {}), ensure_ascii=False, sort_keys=True)}`",
            "",
            "## First records",
            "",
        ]
    )
    for record in records[:10]:
        lines.append(
            f"- `{record['id']}` `{record['level']}` parent=`{record['parent_id']}` title={json.dumps(record['title'], ensure_ascii=False)}"
        )
    lines.append("")
    return "\n".join(lines)


def write_artifacts(result: BuildResult) -> None:
    """Write generated artifacts deterministically to mode-resolved paths."""

    for relative_path, content in {
        result.paths.jsonl: result.jsonl,
        result.paths.json: result.summary_json,
        result.paths.report: result.report_md,
    }.items():
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _artifact_map(result: BuildResult) -> dict[Path, str]:
    """Return the mode-resolved path→content map for a build result."""

    return {
        result.paths.jsonl: result.jsonl,
        result.paths.json: result.summary_json,
        result.paths.report: result.report_md,
    }


def check_artifacts(result: BuildResult) -> bool:
    """Return True when all generated artifacts are fresh at mode-resolved paths."""

    expected = _artifact_map(result)
    return all(
        (ROOT / path).exists() and (ROOT / path).read_text(encoding="utf-8") == content
        for path, content in expected.items()
    )


def _record_count_for_mode(result: BuildResult) -> int:
    """Return the semantic record count for the result's mode."""

    if result.paths.mode == "corpus":
        return result.diagnostics.get("totals", {}).get("record_count", 0)
    return len(result.records)


def _emitted_counts_for_mode(result: BuildResult) -> dict[str, int]:
    """Return the emitted-counts-by-level summary for the result's mode."""

    if result.paths.mode == "corpus":
        totals: dict[str, int] = {}
        for entry in result.diagnostics.get("in_scope_fixtures", []):
            for level, count in (entry.get("emitted_counts_by_level") or {}).items():
                totals[level] = totals.get(level, 0) + int(count)
        return totals
    return result.diagnostics.get("emitted_counts_by_level", {})


def _source_paths_for_mode(result: BuildResult) -> list[str]:
    """Return the repo-relative source paths covered by this mode."""

    if result.paths.mode == "corpus":
        return [entry["path"] for entry in result.diagnostics.get("in_scope_fixtures", [])]
    return [result.diagnostics.get("source", {}).get("path", str(SOURCE_PATH))]


def _sha256_text(content: str) -> str:
    """Return the SHA-256 hex digest of UTF-8 encoded text content."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    """Return the SHA-256 of a tracked file on disk, or None if missing."""

    full = ROOT / path
    if not full.exists():
        return None
    return sha256_bytes(full)


def _manifest_section(result: BuildResult) -> dict[str, Any]:
    """Build a deterministic baseline-manifest section for one mode."""

    artifact_map = _artifact_map(result)
    source_paths = _source_paths_for_mode(result)
    source_entries: list[dict[str, Any]] = []
    for source_path in source_paths:
        full = ROOT / source_path
        source_entries.append(
            {
                "path": source_path,
                "sha256": sha256_bytes(full) if full.exists() else None,
                "exists": full.exists(),
            }
        )
    return {
        "mode": result.paths.mode,
        "cli_invocation": (
            ["uv", "run", "python", str(GENERATOR_PATH), "--corpus"]
            if result.paths.mode == "corpus"
            else ["uv", "run", "python", str(GENERATOR_PATH)]
        ),
        "sources": source_entries,
        "generator": {
            "path": str(GENERATOR_PATH),
            "sha256": _sha256_file(GENERATOR_PATH),
        },
        "outputs": [
            {
                "path": str(rel),
                "sha256": _sha256_text(content),
            }
            for rel, content in sorted(artifact_map.items())
        ],
        "semantic_counts": {
            "record_count": _record_count_for_mode(result),
            "emitted_counts_by_level": dict(sorted(_emitted_counts_for_mode(result).items())),
        },
    }


def _read_manifest_mode_section(manifest: dict[str, Any], mode: str) -> dict[str, Any] | None:
    """Return the section for a mode from a baseline manifest, or None."""

    for section in manifest.get("modes", []):
        if section.get("mode") == mode:
            return section
    return None


def _validate_manifest_section(
    section: dict[str, Any],
    result: BuildResult,
) -> tuple[bool, list[str]]:
    """Validate a tracked manifest section against a freshly built result.

    Returns (fresh, mismatches). Compares built content hashes and semantic
    counts only; it never writes to disk or rescans sources.
    """

    mismatches: list[str] = []
    expected_by_path = {entry["path"]: entry["sha256"] for entry in section.get("outputs", [])}
    for rel, content in _artifact_map(result).items():
        actual = _sha256_text(content)
        tracked = expected_by_path.get(str(rel))
        if tracked is None:
            mismatches.append(f"{rel}: missing output entry in manifest")
        elif tracked != actual:
            mismatches.append(
                f"{rel}: manifest hash drifted (tracked={tracked[:12]}, built={actual[:12]})"
            )
    tracked_count = section.get("semantic_counts", {}).get("record_count")
    actual_count = _record_count_for_mode(result)
    if tracked_count != actual_count:
        mismatches.append(f"record_count drift (tracked={tracked_count}, built={actual_count})")
    return (len(mismatches) == 0), mismatches


def build_baseline_manifest(single: BuildResult, corpus: BuildResult) -> str:
    """Return a deterministic baseline manifest covering both modes."""

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "non_authoritative": True,
        "non_claims": [
            "The baseline manifest is deterministic parser evidence only.",
            "It does not claim legal correctness, parser completeness, or product readiness.",
            "Source hashes are recorded for reproducibility, not as a trust anchor.",
        ],
        "modes": [
            _manifest_section(single),
            _manifest_section(corpus),
        ],
    }
    return stable_json(manifest)


def write_baseline_manifest(single: BuildResult, corpus: BuildResult) -> None:
    """Write the baseline manifest covering both modes."""

    path = ROOT / BASELINE_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_baseline_manifest(single, corpus), encoding="utf-8")


def check_baseline_manifest(mode: str, result: BuildResult) -> tuple[bool, list[str]]:
    """Read-only validation of one manifest section without rebuilding or rescanning.

    Returns (fresh, mismatches). Reads the tracked manifest and compares the
    selected mode's output hashes/counts against freshly built content only;
    it never writes to disk.
    """

    manifest_path = ROOT / BASELINE_MANIFEST_PATH
    if not manifest_path.exists():
        return False, [f"{BASELINE_MANIFEST_PATH}: manifest missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"{BASELINE_MANIFEST_PATH}: malformed manifest json: {exc}"]
    section = _read_manifest_mode_section(manifest, mode)
    if section is None:
        return False, [f"{BASELINE_MANIFEST_PATH}: mode section '{mode}' missing"]
    return _validate_manifest_section(section, result)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="verify generated artifacts are fresh without writing"
    )
    parser.add_argument(
        "--corpus",
        action="store_true",
        help="build hierarchy records for all in-scope fixtures in the corpus (federal_law + code); default is the canonical 44-FZ-2026 fixture only.",
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="write the canonical baseline manifest covering both single and corpus modes; requires building both modes and is incompatible with --check.",
    )
    args = parser.parse_args(argv)

    if args.manifest and args.check:
        print(
            stable_json(
                {"status": "fail", "fatal_errors": ["--manifest cannot be combined with --check"]}
            ),
            end="",
        )
        return 1

    if args.manifest:
        single = build()
        corpus = build_corpus()
        if single.diagnostics.get("fatal_error_count", 0) or corpus.diagnostics.get(
            "fatal_error_count", 0
        ):
            print(
                stable_json(
                    {"status": "fail", "fatal_errors": ["manifest build encountered fatal errors"]}
                ),
                end="",
            )
            return 1
        write_artifacts(single)
        write_artifacts(corpus)
        write_baseline_manifest(single, corpus)
        output = {
            "status": "pass",
            "mode": "manifest",
            "single_record_count": _record_count_for_mode(single),
            "corpus_record_count": _record_count_for_mode(corpus),
            "manifest_path": str(BASELINE_MANIFEST_PATH),
        }
        print(stable_json(output), end="")
        return 0

    if args.corpus:
        result = build_corpus()
    else:
        result = build()
    if result.diagnostics.get("fatal_error_count", 0):
        print(result.summary_json, end="")
        return 1
    if not args.corpus:
        # Single-fixture path keeps the legacy fail-closed checks; corpus
        # path only fails on fatal errors.
        if result.diagnostics.get("malformed_xml") is not None:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics["source"]["inventory_hash_matches"] is not True:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("structural_error_count", 0):
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("validation_error_count", 0):
            print(result.summary_json, end="")
            return 1
    else:
        if result.diagnostics.get("totals", {}).get("id_collision_count", 0) > 0:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("totals", {}).get("in_scope_fixture_count", 0) == 0:
            print(result.summary_json, end="")
            return 1

    if args.check:
        artifacts_fresh = check_artifacts(result)
        manifest_fresh, manifest_mismatches = check_baseline_manifest(result.paths.mode, result)
        fresh = artifacts_fresh and manifest_fresh
        output = dict(result.diagnostics)
        output["mode"] = result.paths.mode
        output["artifact_paths"] = {
            "json": str(result.paths.json),
            "jsonl": str(result.paths.jsonl),
            "report": str(result.paths.report),
        }
        output["artifact_freshness"] = freshness_map(_artifact_map(result))
        output["baseline_manifest"] = {
            "fresh": manifest_fresh,
            "mismatches": manifest_mismatches,
            "path": str(BASELINE_MANIFEST_PATH),
        }
        output["status"] = "pass" if fresh else "fail"
        print(stable_json(output), end="")
        return 0 if fresh else 1

    write_artifacts(result)
    output = dict(result.diagnostics)
    output["mode"] = result.paths.mode
    output["artifact_paths"] = {
        "json": str(result.paths.json),
        "jsonl": str(result.paths.jsonl),
        "report": str(result.paths.report),
    }
    output["artifact_freshness"] = freshness_map(_artifact_map(result))
    output["status"] = "pass"
    print(stable_json(output), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
