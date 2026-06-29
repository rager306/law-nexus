#!/usr/bin/env python3
# ruff: noqa: E402
"""Build deterministic golden-case artifacts from tracked parser outputs.

This generator consumes only tracked ``prd/parser`` artifacts. It creates
bounded, non-authoritative golden-case fixtures for later parser/retrieval
evaluators and never rescans raw legal sources or claims parser completeness,
retrieval quality, legal-answer correctness, citation-safe retrieval readiness,
or FalkorDB runtime readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parser_records import (  # noqa: E402
    DocumentRecord,
    RelationCandidateRecord,
    SourceBlockRecord,
)

from law_nexus.adapters.sources import parser_golden_cases as golden_case_helpers  # noqa: E402

DEFAULT_OUTPUT_DIR = ROOT / "prd/parser"
CONTRACT_PATH = ROOT / "prd/parser/golden_test_contract.md"
DOCUMENT_RECORDS_PATH = ROOT / "prd/parser/odt_document_records.jsonl"
SOURCE_BLOCK_RECORDS_PATH = ROOT / "prd/parser/odt_source_block_records.jsonl"
RELATION_CANDIDATES_PATH = ROOT / "prd/parser/consultant_relation_candidates.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
REPORT_JSON = "golden_cases.json"
REPORT_MD = "golden_cases.md"
SCHEMA_VERSION = "legalgraph-parser-golden-cases/v1"
GENERATED_BY = "scripts/build-parser-golden-cases.py"
BLOCKED_CLAIMS = [
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness",
    "citation-safe retrieval readiness",
    "product ETL readiness",
    "FalkorDB loading/runtime readiness",
    "Consultant WordML legal authority",
    "relation correctness",
    "product graph truth",
]
REQUIRED_CASE_CLASSES = [
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
]
SOURCE_ARTIFACT_PATHS = [
    CONTRACT_PATH,
    DOCUMENT_RECORDS_PATH,
    SOURCE_BLOCK_RECORDS_PATH,
    RELATION_CANDIDATES_PATH,
    STAGING_GRAPH_PATH,
]


def display_path(path: Path) -> str:
    """Return a stable repository-relative path when possible."""

    return golden_case_helpers.display_path(path, root=ROOT)


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest for an artifact file."""

    return golden_case_helpers.sha256_file(path)


def diagnostic(
    *,
    case_id: str | None,
    case_class: str | None,
    severity: str,
    rule: str,
    artifact_path: str,
    message: str,
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    expected_state: str | None = None,
    actual_state: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create a compact S01-contract diagnostic for agents and tests."""

    return golden_case_helpers.diagnostic(
        case_id=case_id,
        case_class=case_class,
        severity=severity,
        rule=rule,
        artifact_path=artifact_path,
        message=message,
        record_id=record_id,
        record_kind=record_kind,
        source_path=source_path,
        expected_state=expected_state,
        actual_state=actual_state,
        non_authoritative=non_authoritative,
        **extra,
    )


def load_source_artifacts() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load the bounded tracked parser artifacts and return diagnostics."""

    diagnostics: list[dict[str, Any]] = []
    for path in SOURCE_ARTIFACT_PATHS:
        if not path.exists():
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="missing_source_artifact",
                    artifact_path=display_path(path),
                    message="Required tracked golden-case source artifact is missing.",
                    expected_state="readable-source-artifact",
                    actual_state="missing",
                )
            )

    documents_raw, document_diagnostics = load_jsonl_if_exists(DOCUMENT_RECORDS_PATH)
    source_blocks_raw, source_block_diagnostics = load_jsonl_if_exists(SOURCE_BLOCK_RECORDS_PATH)
    relation_candidates_raw, relation_diagnostics = load_jsonl_if_exists(RELATION_CANDIDATES_PATH)
    diagnostics.extend(convert_loader_diagnostics(document_diagnostics, None, None))
    diagnostics.extend(convert_loader_diagnostics(source_block_diagnostics, None, None))
    diagnostics.extend(convert_loader_diagnostics(relation_diagnostics, None, None))

    staging_graph: dict[str, Any] = {}
    if STAGING_GRAPH_PATH.exists():
        try:
            loaded = json.loads(STAGING_GRAPH_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                staging_graph = loaded
            else:
                diagnostics.append(
                    diagnostic(
                        case_id=None,
                        case_class=None,
                        severity="error",
                        rule="json_type",
                        artifact_path=display_path(STAGING_GRAPH_PATH),
                        message="Parser staging graph artifact must decode to a JSON object.",
                        expected_state="object",
                        actual_state=type(loaded).__name__,
                    )
                )
        except json.JSONDecodeError as exc:
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="json_invalid",
                    artifact_path=display_path(STAGING_GRAPH_PATH),
                    message=exc.msg,
                    expected_state="valid-json",
                    actual_state="invalid-json",
                )
            )

    documents = [record for record in documents_raw if isinstance(record, DocumentRecord)]
    source_blocks = [record for record in source_blocks_raw if isinstance(record, SourceBlockRecord)]
    relation_candidates = [record for record in relation_candidates_raw if isinstance(record, RelationCandidateRecord)]
    return {
        "documents": documents,
        "source_blocks": source_blocks,
        "relation_candidates": relation_candidates,
        "staging_graph": staging_graph,
    }, diagnostics


def load_jsonl_if_exists(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load parser JSONL records if the path exists; missing is reported elsewhere."""

    return golden_case_helpers.load_jsonl_if_exists(path)


def convert_loader_diagnostics(
    loader_diagnostics: list[dict[str, Any]], case_id: str | None, case_class: str | None
) -> list[dict[str, Any]]:
    """Normalize parser-record loader diagnostics to the golden-case shape."""

    normalized: list[dict[str, Any]] = []
    for item in loader_diagnostics:
        normalized.append(
            diagnostic(
                case_id=case_id,
                case_class=case_class,
                severity="error",
                rule=str(item.get("rule") or "validation_error"),
                artifact_path=str(item.get("file") or item.get("artifact_path") or "<unknown>"),
                record_id=item.get("record_id"),
                record_kind=item.get("record_kind"),
                source_path=item.get("source_path"),
                expected_state="valid-parser-record",
                actual_state="invalid-parser-record",
                message=str(item.get("message") or "Parser record validation failed."),
                field=item.get("field"),
                line=item.get("line"),
            )
        )
    return normalized


def source_artifact_inventory() -> list[dict[str, Any]]:
    """Return deterministic source artifact paths and file hashes."""

    return golden_case_helpers.source_artifact_inventory_core(SOURCE_ARTIFACT_PATHS, root=ROOT)


def make_anchor(record: Any, artifact_path: Path) -> dict[str, Any]:
    """Project one parser record into a bounded source anchor."""

    return golden_case_helpers.make_anchor_core(record, artifact_path, root=ROOT)


def build_cases(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build bounded golden cases from tracked parser artifacts."""

    return golden_case_helpers.build_cases(
        sources,
        contract_path=CONTRACT_PATH,
        document_records_path=DOCUMENT_RECORDS_PATH,
        source_block_records_path=SOURCE_BLOCK_RECORDS_PATH,
        relation_candidates_path=RELATION_CANDIDATES_PATH,
        staging_graph_path=STAGING_GRAPH_PATH,
        required_case_classes=REQUIRED_CASE_CLASSES,
        blocked_claims=BLOCKED_CLAIMS,
        root=ROOT,
    )


def build_report(*, artifact_freshness: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create deterministic machine-readable golden-case artifact content."""

    sources, load_diagnostics = load_source_artifacts()
    cases, case_diagnostics = build_cases(sources)
    embedded_case_diagnostics = [
        item
        for case in cases
        for item in case.get("diagnostics", [])
        if isinstance(item, dict)
    ]
    all_case_diagnostics = [*load_diagnostics, *case_diagnostics, *embedded_case_diagnostics]
    case_class_counts = {case_class: 0 for case_class in REQUIRED_CASE_CLASSES}
    for case in cases:
        case_class_counts[case["case_class"]] = case_class_counts.get(case["case_class"], 0) + 1
    freshness = artifact_freshness or {"status": "not-checked", "stale_paths": [], "diagnostics": []}
    freshness_diagnostics = list(freshness.get("diagnostics") or [])
    diagnostics = [*all_case_diagnostics, *freshness_diagnostics]
    error_count = sum(1 for item in diagnostics if item.get("severity") == "error")
    status = "pass" if error_count == 0 else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "status": status,
        "artifact_freshness": freshness,
        "non_authoritative": True,
        "blocked_claims": BLOCKED_CLAIMS,
        "source_artifacts": source_artifact_inventory(),
        "case_count": len(cases),
        "case_class_counts": dict(sorted(case_class_counts.items())),
        "cases": sorted(cases, key=lambda case: case["case_id"]),
        "diagnostic_count": len(diagnostics),
        "error_count": error_count,
        "warning_count": sum(1 for item in diagnostics if item.get("severity") == "warning"),
        "info_count": sum(1 for item in diagnostics if item.get("severity") == "info"),
        "diagnostics": sorted(diagnostics, key=diagnostic_sort_key),
    }


def diagnostic_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Stable diagnostic sort key."""

    return (
        str(item.get("severity") or ""),
        str(item.get("artifact_path") or ""),
        str(item.get("case_id") or ""),
        str(item.get("rule") or ""),
        str(item.get("record_id") or ""),
    )


def render_markdown(report: dict[str, Any]) -> str:
    """Render bounded human-readable golden-case inventory."""

    lines = [
        "# Parser Golden Cases",
        "",
        f"- Status: `{report['status']}`",
        f"- Schema: `{report['schema_version']}`",
        f"- Generated by: `{report['generated_by']}`",
        "- Non-authoritative: true.",
        f"- Case count: {report['case_count']}",
        f"- Artifact freshness: `{report['artifact_freshness']['status']}`",
        "",
        "## Case inventory",
        "",
        "| Case ID | Class | Expected state | Matched | Anchor IDs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        expected = case["expected"]
        anchor_ids = ", ".join(str(anchor.get("record_id")) for anchor in case.get("anchors", [])) or "none"
        lines.append(
            f"| `{case['case_id']}` | `{case['case_class']}` | `{expected.get('answer_state')}` | `{expected.get('matched')}` | {anchor_ids} |"
        )

    lines.extend(["", "## Source artifacts", "", "| Artifact | Exists | SHA-256 |", "| --- | --- | --- |"])
    for artifact in report["source_artifacts"]:
        lines.append(f"| `{artifact['path']}` | `{artifact['exists']}` | `{artifact.get('sha256', '')}` |")

    lines.extend(["", "## Source anchors", ""])
    for case in report["cases"]:
        lines.extend([f"### {case['case_id']} — {case['case_class']}", ""])
        anchors = case.get("anchors", [])
        if not anchors:
            lines.append("- No source anchor: this case intentionally expects no answer.")
        else:
            for anchor in anchors:
                details = [
                    f"artifact `{anchor.get('artifact_path')}`",
                    f"record `{anchor.get('record_id')}`",
                    f"kind `{anchor.get('record_kind')}`",
                ]
                if anchor.get("source_path"):
                    details.append(f"source `{anchor.get('source_path')}`")
                if anchor.get("source_sha256"):
                    details.append(f"source hash `{anchor.get('source_sha256')}`")
                if anchor.get("excerpt_sha256"):
                    details.append(f"excerpt hash `{anchor.get('excerpt_sha256')}`")
                if anchor.get("evidence_sha256"):
                    details.append(f"evidence hash `{anchor.get('evidence_sha256')}`")
                lines.append("- " + "; ".join(details) + ".")
        lines.append("")

    lines.extend(
        [
            "## Blocked claims and non-claim boundaries",
            "",
            "A golden-case pass under this artifact must not be described as proof of:",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in report["blocked_claims"])
    lines.extend(
        [
            "",
            "These fixtures are bounded parser/retrieval evidence inputs only. They do not provide legal advice, authoritative legal interpretation, product retrieval quality proof, citation-safe retrieval readiness, production graph truth, or FalkorDB runtime proof.",
            "",
            "## Diagnostics",
            "",
            f"- Errors: {report['error_count']}",
            f"- Warnings: {report['warning_count']}",
            f"- Info: {report['info_count']}",
            "",
            "| Severity | Case | Rule | Artifact | Record | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if report["diagnostics"]:
        for item in report["diagnostics"][:40]:
            message = str(item.get("message") or "").replace("|", "\\|")
            lines.append(
                f"| `{item.get('severity')}` | `{item.get('case_id')}` | `{item.get('rule')}` | `{item.get('artifact_path')}` | `{item.get('record_id')}` | {message} |"
            )
        if len(report["diagnostics"]) > 40:
            lines.append(
                f"| `info` | `report` | `bounded-report` | `prd/parser/golden_cases.md` | `None` | {len(report['diagnostics']) - 40} additional diagnostics omitted from Markdown. |"
            )
    else:
        lines.append("| `info` | `report` | `none` | `prd/parser/golden_cases.json` | `None` | No diagnostics. |")
    lines.append("")
    return "\n".join(lines)


def output_contents() -> dict[str, str]:
    """Return deterministic artifact bytes keyed by output filename."""

    report = build_report()
    return {
        REPORT_JSON: json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        REPORT_MD: render_markdown(report),
    }


def write_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write deterministic golden-case artifacts and return a CLI report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = output_contents()
    for name, content in expected.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return build_report()


def check_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Byte-compare expected golden-case artifacts and return compact status."""

    expected = output_contents()
    stale_paths: list[str] = []
    freshness_diagnostics: list[dict[str, Any]] = []
    for name, content in expected.items():
        path = output_dir / name
        stable_path = display_path(path)
        if not path.exists():
            stale_paths.append(stable_path)
            freshness_diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="stale-artifact",
                    artifact_path=stable_path,
                    message="Expected parser golden-case artifact is missing.",
                    expected_state="fresh-artifact",
                    actual_state="missing",
                )
            )
            continue
        if path.read_text(encoding="utf-8") != content:
            stale_paths.append(stable_path)
            freshness_diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="stale-artifact",
                    artifact_path=stable_path,
                    message="Expected parser golden-case artifact bytes are stale.",
                    expected_state="fresh-artifact",
                    actual_state="stale",
                )
            )
    freshness = {
        "status": "pass" if not freshness_diagnostics else "stale",
        "stale_paths": stale_paths,
        "diagnostics": freshness_diagnostics,
    }
    return build_report(artifact_freshness=freshness)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic parser golden-case artifacts.")
    mode.add_argument("--check", action="store_true", help="Check parser golden-case artifact freshness and print compact JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Artifact directory, default prd/parser.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = write_outputs(args.output_dir) if args.write else check_outputs(args.output_dir)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
