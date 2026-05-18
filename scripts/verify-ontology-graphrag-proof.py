#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
VALIDATOR_PATH = ROOT / "scripts/retrieval_output_validator.py"
SUMMARY_SCHEMA_VERSION = "ontology-graphrag-proof/v1"
EXPECTED_SCHEMA_VERSION = "ontology-graphrag-proof-cases/v1"
EXPECTED_PROOF_ID = "OG-M020-S02-FIXTURE-PROOF"

_ALLOWED_RESULT_STATES = frozenset({"accepted", "accepted_scoped_no_answer", "rejected", "blocked_unsupported_filter"})
_PROOF_LOCAL_CODES = frozenset(
    {
        "ontology_filter_matched",
        "unsupported_ontology_filter",
        "temporal_filter_excluded",
        "ambiguous_candidate_set",
        "forbidden_payload_field",
    }
)
_SAFE_DIAGNOSTIC_FIELDS = frozenset({"code", "severity", "result", "field_path", "case_id", "rule", "remediation"})
_MAX_SAFE_FIELD_LENGTH = 160

_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "raw_legal_text",
        "raw_text",
        "source_excerpt",
        "source_excerpts",
        "prompt",
        "user_prompt",
        "provider_payload",
        "provider_response_body",
        "secret",
        "secrets",
        "pii",
        "vector",
        "embedding_vector",
        "falkordb_row",
        "runtime_row",
        "generated_answer_prose",
        "legal_advice",
        "llm_reasoning",
    }
)


class ProofError(Exception):
    pass


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


def _safe(value: Any) -> str:
    if isinstance(value, str) and value:
        return value[:_MAX_SAFE_FIELD_LENGTH]
    return "<missing>"


def _error_summary(*, fixtures: Path, phase: str, code: str, detail: str | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"phase": phase, "code": code, "fixture_path": _bounded_path(fixtures)}
    if detail:
        error["detail"] = detail[:_MAX_SAFE_FIELD_LENGTH]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixtures),
        "proof_id": EXPECTED_PROOF_ID,
        "non_authoritative": True,
        "total_cases": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "blocked_count": 0,
        "mismatch_count": 1,
        "diagnostic_code_inventory": [],
        "mismatches": [error],
    }


def _load_json(path: Path) -> tuple[int, dict[str, Any] | None, dict[str, Any] | None]:
    try:
        with path.open(encoding="utf-8") as fixture_file:
            data = json.load(fixture_file)
    except FileNotFoundError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="fixture_not_found", detail=str(exc))
    except json.JSONDecodeError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="malformed_fixture_json", detail=exc.msg)
    except OSError as exc:
        return 2, None, _error_summary(fixtures=path, phase="fixture_load", code="fixture_load_error", detail=str(exc))
    if not isinstance(data, dict):
        return 2, None, _error_summary(fixtures=path, phase="fixture_shape", code="malformed_fixture_shape", detail="fixture root must be an object")
    return 0, data, None


def _diagnostic(code: str, *, case_id: str, result: str, field_path: str, severity: str = "error", rule: str, remediation: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "result": result,
        "field_path": field_path[:_MAX_SAFE_FIELD_LENGTH],
        "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
        "rule": rule[:_MAX_SAFE_FIELD_LENGTH],
        "remediation": remediation[:_MAX_SAFE_FIELD_LENGTH],
    }


def _validator_codes(result: Any) -> list[str]:
    return [diagnostic.code for diagnostic in result.diagnostics]


def _check_forbidden_field_names(value: Any, *, path: str = "$", hits: list[str] | None = None) -> list[str]:
    found = hits if hits is not None else []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            field_path = f"{path}.{key}" if path != "$" else str(key)
            if str(key).lower() in _FORBIDDEN_FIELD_NAMES:
                found.append(field_path[:_MAX_SAFE_FIELD_LENGTH])
            _check_forbidden_field_names(nested, path=field_path, hits=found)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _check_forbidden_field_names(nested, path=f"{path}[{index}]", hits=found)
    return found


def _build_validator_fixture(validator: ModuleType, data: Mapping[str, Any], fixtures: Path) -> tuple[int, Any | None, dict[str, Any] | None]:
    graph = data.get("validator_fixture_graph")
    if not isinstance(graph, Mapping):
        return 2, None, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_fixture_shape", detail="validator_fixture_graph must be an object")
    try:
        fixture = validator.build_fixture(
            {"fixture_graph": graph}, fixture_artifact=str(data.get("fixture_artifact") or _bounded_path(fixtures))
        )
    except ValueError as exc:
        return 2, None, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_fixture_shape", detail=str(exc))
    return 0, fixture, None


def _shape_mismatches(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    expected = {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "proof_id": EXPECTED_PROOF_ID,
        "non_authoritative": True,
    }
    for field, expected_value in expected.items():
        if data.get(field) != expected_value:
            mismatches.append(
                {
                    "phase": "fixture_shape",
                    "code": "fixture_contract_mismatch",
                    "field_path": field,
                    "expected_result": _safe(expected_value),
                    "actual_result": _safe(data.get(field)),
                }
            )
    for field in ("source_inputs", "cases", "redaction", "non_claims"):
        if field not in data:
            mismatches.append({"phase": "fixture_shape", "code": "missing_required_field", "field_path": field})
    redaction = data.get("redaction")
    if not isinstance(redaction, Mapping) or redaction.get("forbidden_payload_classes_absent") is not True:
        mismatches.append({"phase": "fixture_shape", "code": "redaction_boundary_missing", "field_path": "redaction.forbidden_payload_classes_absent"})
    for field_path in _check_forbidden_field_names(data):
        mismatches.append({"phase": "redaction_boundary", "code": "forbidden_payload_field", "field_path": field_path})
    return mismatches


def _case_local_diagnostics(case: Mapping[str, Any], *, validator_result: Any | None) -> list[dict[str, str]]:
    case_id = _safe(case.get("case_id"))
    expected_result = _safe(case.get("expected_result"))
    diagnostics: list[dict[str, str]] = []
    ontology = case.get("ontology_filter")
    temporal = case.get("temporal_filter")
    candidates = case.get("candidate_set")

    if isinstance(ontology, Mapping):
        requested = ontology.get("requested_value")
        allowed = ontology.get("allowed_values")
        if not isinstance(allowed, list) or requested not in allowed:
            diagnostics.append(
                _diagnostic(
                    "unsupported_ontology_filter",
                    case_id=case_id,
                    result="blocked_unsupported_filter",
                    field_path="ontology_filter.requested_value",
                    rule="ontology_filter_allowed_values",
                    remediation="Use a supported proof-local ontology value or keep the case blocked.",
                )
            )
        elif ontology.get("expected_filter_result") == "matched" and expected_result == "accepted":
            diagnostics.append(
                _diagnostic(
                    "ontology_filter_matched",
                    case_id=case_id,
                    result="accepted",
                    field_path="ontology_filter.requested_value",
                    severity="info",
                    rule="ontology_filter_matched",
                    remediation="Keep citation/evidence validation as the authority for accepted outputs.",
                )
            )

    if isinstance(temporal, Mapping) and temporal.get("expected_temporal_result") in {"excluded_inactive", "wrong_edition"}:
        diagnostics.append(
            _diagnostic(
                "temporal_filter_excluded",
                case_id=case_id,
                result="rejected",
                field_path="temporal_filter.expected_temporal_result",
                rule="current_only_temporal_filter",
                remediation="Exclude inactive or wrong-edition evidence before presenting proof output.",
            )
        )

    if isinstance(candidates, list):
        matching = [candidate for candidate in candidates if isinstance(candidate, Mapping) and candidate.get("selection_reason") == "ontology_and_temporal_match"]
        if len(matching) > 1:
            diagnostics.append(
                _diagnostic(
                    "ambiguous_candidate_set",
                    case_id=case_id,
                    result="rejected",
                    field_path="candidate_set",
                    rule="no_arbitrary_tie_break",
                    remediation="Narrow the query/filter or return scoped no-answer; do not pick a winner.",
                )
            )

    if isinstance(case.get("safety_probe"), Mapping):
        diagnostics.append(
            _diagnostic(
                "forbidden_payload_field",
                case_id=case_id,
                result="rejected",
                field_path=_safe(case["safety_probe"].get("field_path")),
                rule="unsafe_payload_boundary",
                remediation="Remove unsafe payload fields and retain only source/evidence IDs.",
            )
        )

    return diagnostics


def _final_result(case: Mapping[str, Any], validator_result: Any | None, local_diagnostics: list[Mapping[str, str]]) -> str:
    local_codes = {diagnostic["code"] for diagnostic in local_diagnostics}
    if "unsupported_ontology_filter" in local_codes:
        return "blocked_unsupported_filter"
    if local_codes & {"temporal_filter_excluded", "ambiguous_candidate_set", "forbidden_payload_field"}:
        return "rejected"
    if validator_result is not None:
        return validator_result.result
    return "rejected"


def _case_mismatch(case_id: str, expected_result: Any, actual_result: str, expected_codes: Any, actual_codes: list[str]) -> dict[str, Any]:
    return {
        "phase": "case_expectation",
        "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
        "code": "expectation_mismatch",
        "expected_result": _safe(expected_result),
        "actual_result": actual_result,
        "expected_codes": expected_codes if isinstance(expected_codes, list) else [],
        "actual_codes": actual_codes,
    }


def _safe_payload_errors(*, case_id: str, diagnostics: list[Mapping[str, Any]], known_codes: set[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for index, payload in enumerate(diagnostics):
        extra_fields = sorted(set(payload) - _SAFE_DIAGNOSTIC_FIELDS)
        if extra_fields:
            errors.append({"phase": "diagnostic_safety", "case_id": case_id, "code": "unsafe_diagnostic_field", "field_path": f"diagnostics[{index}]", "actual_codes": extra_fields})
        diagnostic_code = payload.get("code")
        if diagnostic_code not in known_codes:
            errors.append({"phase": "diagnostic_safety", "case_id": case_id, "code": "unknown_diagnostic_code", "field_path": f"diagnostics[{index}].code", "actual_codes": [_safe(diagnostic_code)]})
        for field in ("field_path", "case_id", "rule", "remediation"):
            value = payload.get(field)
            if not isinstance(value, str) or len(value) > _MAX_SAFE_FIELD_LENGTH:
                errors.append({"phase": "diagnostic_safety", "case_id": case_id, "code": "malformed_diagnostic_shape", "field_path": f"diagnostics[{index}].{field}"})
    return errors


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

    cases = data.get("cases")
    if not isinstance(cases, list):
        return 2, _error_summary(fixtures=fixtures, phase="fixture_shape", code="malformed_fixture_shape", detail="cases must be a list")

    known_codes = set(validator.KNOWN_DIAGNOSTIC_CODES) | set(_PROOF_LOCAL_CODES)
    result_counts: Counter[str] = Counter()
    diagnostic_inventory: Counter[str] = Counter()
    mismatches = _shape_mismatches(data)

    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            mismatches.append({"phase": "fixture_shape", "case_id": f"<index:{index}>", "code": "malformed_fixture_shape", "field_path": f"cases[{index}]"})
            continue
        case_id = _safe(case.get("case_id") or f"<index:{index}>")
        output = case.get("output")
        validator_result = validator.validate_case(case, validator_fixture) if output is not None else None
        local_diagnostics = _case_local_diagnostics(case, validator_result=validator_result)
        actual_codes = [diagnostic["code"] for diagnostic in local_diagnostics]
        if validator_result is not None:
            actual_codes.extend(_validator_codes(validator_result))
        actual_result = _final_result(case, validator_result, local_diagnostics)
        result_counts[actual_result] += 1
        diagnostic_inventory.update(actual_codes)

        expected_result = case.get("expected_result")
        expected_codes = case.get("expected_diagnostic_codes")
        if actual_result != expected_result or actual_codes != expected_codes:
            mismatches.append(_case_mismatch(case_id, expected_result, actual_result, expected_codes, actual_codes))

        mismatches.extend(_safe_payload_errors(case_id=case_id, diagnostics=local_diagnostics, known_codes=known_codes))

    accepted_count = result_counts["accepted"] + result_counts["accepted_scoped_no_answer"]
    rejected_count = result_counts["rejected"]
    blocked_count = result_counts["blocked_unsupported_filter"]
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixtures),
        "proof_id": _safe(data.get("proof_id")),
        "total_cases": len(cases),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "blocked_count": blocked_count,
        "mismatch_count": len(mismatches),
        "diagnostic_code_inventory": sorted(diagnostic_inventory),
        "non_authoritative": data.get("non_authoritative") is True,
        "redaction_ok": not _check_forbidden_field_names(data),
        "result_states": {key: result_counts[key] for key in sorted(result_counts)},
    }
    if mismatches:
        summary["mismatches"] = mismatches
    return (0 if not mismatches else 1), summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the M020 S02 ontology GraphRAG proof over tracked fixtures.")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES, help="Path to ontology GraphRAG proof fixture JSON.")
    args = parser.parse_args(argv)
    fixtures = args.fixtures if args.fixtures.is_absolute() else ROOT / args.fixtures
    exit_code, summary = run_proof(fixtures)
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
