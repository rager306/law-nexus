from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
VALIDATOR_PATH = ROOT / "scripts/retrieval_output_validator.py"
SUMMARY_SCHEMA_VERSION = "offline-citation-retrieval-proof/v1"
_ALLOWED_SELECTION_RESULTS = frozenset({"selected", "scoped_no_answer", "rejected"})
_ALLOWED_VALIDATOR_RESULTS = frozenset({"accepted", "accepted_scoped_no_answer", "rejected"})
_SAFE_DIAGNOSTIC_FIELDS = frozenset(
    {
        "code",
        "severity",
        "case_id",
        "query_id",
        "candidate_id",
        "source_record_id",
        "field_path",
        "proof_artifact",
        "result",
        "retrieval_output_id",
        "scope_id",
        "safe_id_value",
        "expected_id",
        "resolved_id",
        "fixture_artifact",
    }
)
_BOUNDED_FIELDS = frozenset({"case_id", "query_id", "candidate_id", "field_path", "proof_artifact", "retrieval_output_id", "scope_id"})
_MAX_SAFE_FIELD_LENGTH = 180


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retrieval_output_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import validator from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bounded_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)[:_MAX_SAFE_FIELD_LENGTH]


def _error_summary(*, fixtures: Path, phase: str, code: str, detail: str | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {
        "phase": phase,
        "code": code,
        "fixture_path": _bounded_path(fixtures),
    }
    if detail:
        error["detail"] = detail[:_MAX_SAFE_FIELD_LENGTH]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixtures),
        "total_cases": 0,
        "selected_count": 0,
        "scoped_no_answer_count": 0,
        "rejected_count": 0,
        "validator_accepted_count": 0,
        "validator_rejected_count": 0,
        "mismatch_count": 1,
        "diagnostic_code_inventory": [],
        "mismatches": [error],
    }


def _load_json(path: Path) -> tuple[int, dict[str, Any] | None, dict[str, Any] | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="fixture_not_found", detail=str(exc))
    except json.JSONDecodeError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="malformed_fixture_json", detail=exc.msg)
    except OSError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="fixture_load_error", detail=str(exc))
    if not isinstance(data, dict):
        return 2, None, _error_summary(fixtures=path, phase="fixture_shape", code="malformed_output_shape", detail="fixture root must be an object")
    return 0, data, None


def _build_validator_fixture(validator: ModuleType, data: Mapping[str, Any], fixtures: Path) -> tuple[int, Any | None, dict[str, Any] | None]:
    graph = data.get("derived_fixture_graph")
    if not isinstance(graph, Mapping):
        return 2, None, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_output_shape", detail="derived_fixture_graph must be an object")
    try:
        fixture = validator.build_fixture(
            {"fixture_graph": graph}, fixture_artifact=str(data.get("fixture_artifact") or _bounded_path(fixtures))
        )
    except ValueError as exc:
        return 2, None, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_output_shape", detail=str(exc))
    return 0, fixture, None


def _validator_codes(result: Any) -> list[str]:
    return [diagnostic.code for diagnostic in result.diagnostics]


def _validator_payloads(result: Any) -> list[dict[str, Any]]:
    return [diagnostic.to_dict() for diagnostic in result.diagnostics]


def _offline_diagnostic_payloads(case: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    diagnostics = case.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []
    return [diagnostic for diagnostic in diagnostics if isinstance(diagnostic, Mapping)]


def _offline_codes(case: Mapping[str, Any]) -> list[str]:
    return [str(diagnostic.get("code")) for diagnostic in _offline_diagnostic_payloads(case) if isinstance(diagnostic.get("code"), str)]


def _safe_payload_errors(*, case_id: str, payloads: Sequence[Mapping[str, Any]], known_codes: set[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for index, payload in enumerate(payloads):
        extra_fields = sorted(set(payload) - _SAFE_DIAGNOSTIC_FIELDS)
        if extra_fields:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
                    "code": "unsafe_diagnostic_field",
                    "field_path": f"diagnostics[{index}]",
                    "actual_fields": extra_fields,
                }
            )
        diagnostic_code = payload.get("code")
        if diagnostic_code not in known_codes:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
                    "code": "unknown_diagnostic_code",
                    "field_path": f"diagnostics[{index}].code",
                    "actual_codes": [str(diagnostic_code)[:_MAX_SAFE_FIELD_LENGTH]],
                }
            )
        for field in _BOUNDED_FIELDS:
            value = payload.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > _MAX_SAFE_FIELD_LENGTH):
                errors.append(
                    {
                        "phase": "diagnostic_safety",
                        "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
                        "code": "malformed_output_shape",
                        "field_path": f"diagnostics[{index}].{field}",
                    }
                )
    return errors


def _selection_shape_errors(case: Mapping[str, Any], *, index: int) -> list[dict[str, Any]]:
    case_id = case.get("case_id") if isinstance(case.get("case_id"), str) else f"<index:{index}>"
    errors: list[dict[str, Any]] = []
    query = case.get("query")
    candidates = case.get("candidates")
    expected_selection = case.get("expected_selection_result")
    if expected_selection not in _ALLOWED_SELECTION_RESULTS:
        errors.append({"phase": "selection_shape", "case_id": case_id, "code": "malformed_output_shape", "field_path": "expected_selection_result"})
    if not isinstance(query, Mapping):
        errors.append({"phase": "selection_shape", "case_id": case_id, "code": "malformed_output_shape", "field_path": "query"})
    if not isinstance(candidates, list):
        errors.append({"phase": "selection_shape", "case_id": case_id, "code": "malformed_output_shape", "field_path": "candidates"})
        return errors

    output = case.get("output")
    selected_candidates = [candidate for candidate in candidates if isinstance(candidate, Mapping) and isinstance(candidate.get("validator_output"), Mapping)]
    if expected_selection == "selected" and len(selected_candidates) != 1:
        errors.append({"phase": "selection_shape", "case_id": case_id, "code": "expectation_mismatch", "field_path": "candidates"})
    if expected_selection == "scoped_no_answer":
        if candidates or not isinstance(output, Mapping) or output.get("output_kind") != "scoped_no_answer":
            errors.append({"phase": "selection_shape", "case_id": case_id, "code": "unsafe_no_answer_shape", "field_path": "output"})
    if expected_selection == "rejected" and case.get("expected_validator_result") is None and isinstance(output, Mapping):
        errors.append({"phase": "selection_shape", "case_id": case_id, "code": "expectation_mismatch", "field_path": "output"})
    return errors


def _case_mismatch(
    *,
    case_id: str,
    field_path: str,
    expected: Any,
    actual: Any,
) -> dict[str, Any]:
    return {
        "phase": "case_expectation",
        "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
        "code": "expectation_mismatch",
        "field_path": field_path,
        "expected": expected if isinstance(expected, (str, int, float, list, dict, type(None))) else str(expected)[:_MAX_SAFE_FIELD_LENGTH],
        "actual": actual if isinstance(actual, (str, int, float, list, dict, type(None))) else str(actual)[:_MAX_SAFE_FIELD_LENGTH],
    }


def run_proof(fixtures: Path) -> tuple[int, dict[str, Any]]:
    validator = _load_validator()
    load_code, data, load_error = _load_json(fixtures)
    if load_code != 0:
        assert load_error is not None
        return load_code, load_error
    assert data is not None

    build_code, validator_fixture, build_error = _build_validator_fixture(validator, data, fixtures)
    if build_code != 0:
        assert build_error is not None
        return build_code, build_error
    assert validator_fixture is not None

    cases = data.get("cases")
    if not isinstance(cases, list):
        return 2, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_output_shape", detail="cases must be a list")

    known_codes = set(validator.KNOWN_DIAGNOSTIC_CODES) | {
        "scoped_no_candidate",
        "ambiguous_candidate_set",
        "unresolved_candidate_evidence",
        "unsafe_payload_rejected",
        "expectation_mismatch",
        "unsafe_diagnostic_field",
        "unknown_diagnostic_code",
    }
    selection_counts: Counter[str] = Counter()
    validator_counts: Counter[str] = Counter()
    diagnostic_inventory: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            mismatches.append({"phase": "fixture_shape", "case_id": f"<index:{index}>", "code": "malformed_output_shape", "field_path": f"cases[{index}]"})
            continue
        case_id = case.get("case_id") if isinstance(case.get("case_id"), str) else f"<index:{index}>"
        selection_errors = _selection_shape_errors(case, index=index)
        mismatches.extend(selection_errors)

        expected_selection = case.get("expected_selection_result")
        if isinstance(expected_selection, str):
            selection_counts[expected_selection] += 1

        expected_validator_result = case.get("expected_validator_result")
        validator_codes: list[str] = []
        validator_payloads: list[dict[str, Any]] = []
        if expected_validator_result is not None:
            if expected_validator_result not in _ALLOWED_VALIDATOR_RESULTS:
                mismatches.append(_case_mismatch(case_id=case_id, field_path="expected_validator_result", expected="allowed validator result", actual=expected_validator_result))
            result = validator.validate_case(case, validator_fixture)
            validator_counts[result.result] += 1
            validator_codes = _validator_codes(result)
            validator_payloads = _validator_payloads(result)
            if result.result != expected_validator_result:
                mismatches.append(_case_mismatch(case_id=case_id, field_path="expected_validator_result", expected=expected_validator_result, actual=result.result))
        elif isinstance(case.get("output"), Mapping):
            mismatches.append(_case_mismatch(case_id=case_id, field_path="output", expected="no validator output", actual="present"))

        offline_codes = _offline_codes(case)
        actual_codes = offline_codes + validator_codes
        diagnostic_inventory.update(actual_codes)
        expected_codes = case.get("expected_diagnostic_codes")
        if actual_codes != expected_codes:
            mismatches.append(_case_mismatch(case_id=case_id, field_path="expected_diagnostic_codes", expected=expected_codes, actual=actual_codes))

        mismatches.extend(_safe_payload_errors(case_id=case_id, payloads=[*_offline_diagnostic_payloads(case), *validator_payloads], known_codes=known_codes))

    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixtures),
        "total_cases": len(cases),
        "selected_count": selection_counts["selected"],
        "scoped_no_answer_count": selection_counts["scoped_no_answer"],
        "rejected_count": selection_counts["rejected"],
        "validator_accepted_count": validator_counts["accepted"] + validator_counts["accepted_scoped_no_answer"],
        "validator_rejected_count": validator_counts["rejected"],
        "mismatch_count": len(mismatches),
        "diagnostic_code_inventory": sorted(diagnostic_inventory),
        "namespace_strategy": data.get("namespace_strategy", {}).get("status") if isinstance(data.get("namespace_strategy"), Mapping) else None,
        "non_authoritative": data.get("non_authoritative") is True,
    }
    if mismatches:
        summary["mismatches"] = mismatches
    return (0 if not mismatches else 1), summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the M014 offline citation-safe retrieval proof against tracked fixtures.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Path to M014 offline citation retrieval fixture JSON.",
    )
    args = parser.parse_args(argv)
    exit_code, summary = run_proof(args.fixtures)
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
