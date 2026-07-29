#!/usr/bin/env python3
# ruff: noqa: E402
"""Evaluate parser golden cases against tracked parser artifacts.

The evaluator is deterministic and local-only: it reads bounded artifacts under
``prd/parser`` and never rescans raw legal sources, calls FalkorDB, invokes an
LLM, or claims parser/retrieval/legal-answer readiness.
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
    load_jsonl_records,
)

from law_nexus.adapters.sources import parser_golden_cases as golden_case_helpers  # noqa: E402

SCHEMA_VERSION = "legalgraph-parser-golden-evaluator/v1"
GENERATED_BY = "scripts/evaluate-parser-golden-cases.py"
GOLDEN_CASES_SCHEMA_VERSION = "legalgraph-parser-golden-cases/v1"
DEFAULT_PARSER_DIR = ROOT / "prd/parser"
REQUIRED_CASE_CLASSES = {
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
}
SOURCE_ARTIFACT_FILENAMES = {
    "documents": "odt_document_records.jsonl",
    "source_blocks": "odt_source_block_records.jsonl",
    "relations": "consultant_relation_candidates.jsonl",
    "staging_graph": "parser_staging_graph.json",
}


def display_path(path: Path) -> str:
    """Return a stable repository-relative path when possible."""

    return golden_case_helpers.display_path(path, root=ROOT)


def diagnostic(
    *,
    case_id: str | None,
    case_class: str | None,
    severity: str,
    rule: str,
    artifact_path: str,
    expected_state: str | None,
    actual_state: str | None,
    message: str,
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create the compact path-qualified diagnostic contract for stdout."""

    return golden_case_helpers.diagnostic(
        case_id=case_id,
        case_class=case_class,
        severity=severity,
        rule=rule,
        artifact_path=artifact_path,
        message=message,
        expected_state=expected_state,
        actual_state=actual_state,
        record_id=record_id,
        record_kind=record_kind,
        source_path=source_path,
        non_authoritative=non_authoritative,
        **extra,
    )


def sort_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort diagnostics deterministically by severity context and path."""

    return golden_case_helpers.sort_evaluation_diagnostics(diagnostics)


def severity_counts(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    """Return deterministic severity counts with explicit zeroes."""

    return golden_case_helpers.evaluation_severity_counts(diagnostics)


def load_json_object(
    path: Path, *, artifact_label: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load a JSON object with fail-closed diagnostics."""

    if not path.exists():
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path),
                expected_state="readable-json-object",
                actual_state="missing",
                message=f"Required {artifact_label} artifact is missing.",
            )
        ]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="json_invalid",
                artifact_path=display_path(path),
                expected_state="valid-json-object",
                actual_state="invalid-json",
                message=exc.msg,
            )
        ]
    if not isinstance(loaded, dict):
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="json_type",
                artifact_path=display_path(path),
                expected_state="object",
                actual_state=type(loaded).__name__,
                message=f"{artifact_label} artifact must decode to a JSON object.",
            )
        ]
    return loaded, []


def convert_loader_diagnostics(
    loader_diagnostics: list[dict[str, Any]], *, artifact_path: Path
) -> list[dict[str, Any]]:
    """Normalize parser-record loader diagnostics to evaluator diagnostics."""

    normalized: list[dict[str, Any]] = []
    for item in loader_diagnostics:
        normalized.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule=str(item.get("rule") or "validation_error"),
                artifact_path=str(item.get("file") or display_path(artifact_path)),
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


def load_records(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load one parser JSONL artifact using the shared parser record contracts."""

    if not path.exists():
        return [], [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path),
                expected_state="readable-jsonl-parser-records",
                actual_state="missing",
                message="Required parser JSONL artifact is missing.",
            )
        ]
    records, loader_diagnostics = load_jsonl_records(path)
    return records, convert_loader_diagnostics(loader_diagnostics, artifact_path=path)


def load_source_artifacts(parser_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load bounded parser artifacts used by evaluator."""

    return golden_case_helpers.load_evaluation_source_artifacts(
        parser_dir, source_artifact_filenames=SOURCE_ARTIFACT_FILENAMES, root=ROOT
    )


def load_golden_cases(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load generated golden cases artifact."""

    return golden_case_helpers.load_golden_cases_report(
        path, golden_cases_schema_version=GOLDEN_CASES_SCHEMA_VERSION, root=ROOT
    )


def require_case_mapping(
    case: dict[str, Any], *, golden_path: Path
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Ensure a golden case is an object before evaluating it."""

    return golden_case_helpers.require_case_mapping(
        case, golden_path=golden_path, required_case_classes=REQUIRED_CASE_CLASSES, root=ROOT
    )


def expected_list(case: dict[str, Any], key: str) -> list[str]:
    """Return a stable string list from a golden-case expectation field."""

    return golden_case_helpers.expected_list(case, key)


def case_expected_state(case: dict[str, Any]) -> str | None:
    """Return the case expected answer_state if present."""

    expected = case.get("expected")
    value = expected.get("answer_state") if isinstance(expected, dict) else None
    return str(value) if value is not None else None


def evaluate_evidence_present(
    case: dict[str, Any], source_artifacts: dict[str, Any], golden_path: Path, parser_dir: Path
) -> list[dict[str, Any]]:
    """Evaluate evidence-present golden case."""

    return golden_case_helpers.evaluate_evidence_present(
        case,
        source_blocks=source_artifacts["source_blocks"],
        source_blocks_path=parser_dir / SOURCE_ARTIFACT_FILENAMES["source_blocks"],
        root=ROOT,
    )


def evaluate_no_answer(
    case: dict[str, Any], source_artifacts: dict[str, Any], golden_path: Path
) -> list[dict[str, Any]]:
    """Evaluate no-answer golden case."""

    return golden_case_helpers.evaluate_no_answer(
        case, source_artifacts=source_artifacts, parser_dir=golden_path.parent, root=ROOT
    )


def evaluate_candidate_only(
    case: dict[str, Any], source_artifacts: dict[str, Any], golden_path: Path, parser_dir: Path
) -> list[dict[str, Any]]:
    """Evaluate candidate-only golden case."""

    return golden_case_helpers.evaluate_candidate_only(
        case,
        relations=source_artifacts["relations"],
        staging_graph=source_artifacts["staging_graph"],
        relations_path=parser_dir / SOURCE_ARTIFACT_FILENAMES["relations"],
        staging_path=parser_dir / SOURCE_ARTIFACT_FILENAMES["staging_graph"],
        root=ROOT,
    )


def evaluate_unresolved_reference(
    case: dict[str, Any], golden_report: dict[str, Any], golden_path: Path
) -> list[dict[str, Any]]:
    """Evaluate unresolved-reference golden case."""

    return golden_case_helpers.evaluate_unresolved_reference(
        case, staging_graph=golden_report, staging_path=golden_path, root=ROOT
    )


def evaluate_non_authoritative(
    case: dict[str, Any],
    source_artifacts: dict[str, Any],
    golden_report: dict[str, Any],
    golden_path: Path,
) -> list[dict[str, Any]]:
    """Evaluate non-authoritative boundary case."""

    return golden_case_helpers.evaluate_non_authoritative(
        case,
        golden_report=golden_report,
        source_artifacts=source_artifacts,
        golden_path=golden_path,
        root=ROOT,
    )


def evaluate_cases(
    golden_report: dict[str, Any], golden_path: Path, parser_dir: Path
) -> dict[str, Any]:
    """Evaluate generated golden cases against tracked parser artifacts."""

    return golden_case_helpers.evaluate_cases(
        golden_report,
        golden_path,
        parser_dir,
        source_artifact_filenames=SOURCE_ARTIFACT_FILENAMES,
        required_case_classes=REQUIRED_CASE_CLASSES,
        golden_cases_schema_version=GOLDEN_CASES_SCHEMA_VERSION,
        schema_version=SCHEMA_VERSION,
        generated_by=GENERATED_BY,
        root=ROOT,
    )


def build_result(*, golden_cases_path: Path, parser_dir: Path) -> dict[str, Any]:
    """Build the evaluator result for CLI and tests."""

    return golden_case_helpers.build_evaluation_result(
        golden_cases_path=golden_cases_path,
        parser_dir=parser_dir,
        source_artifact_filenames=SOURCE_ARTIFACT_FILENAMES,
        required_case_classes=REQUIRED_CASE_CLASSES,
        golden_cases_schema_version=GOLDEN_CASES_SCHEMA_VERSION,
        schema_version=SCHEMA_VERSION,
        generated_by=GENERATED_BY,
        root=ROOT,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the evaluator CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        required=True,
        help="Evaluate tracked golden cases and exit non-zero on errors.",
    )
    parser.add_argument(
        "--parser-dir",
        type=Path,
        default=DEFAULT_PARSER_DIR,
        help="Directory containing parser artifacts; defaults to prd/parser.",
    )
    parser.add_argument(
        "--golden-cases",
        type=Path,
        default=None,
        help="Path to golden_cases.json; defaults to <parser-dir>/golden_cases.json.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    parser_dir = args.parser_dir
    golden_cases_path = args.golden_cases or parser_dir / "golden_cases.json"
    result = build_result(golden_cases_path=golden_cases_path, parser_dir=parser_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
