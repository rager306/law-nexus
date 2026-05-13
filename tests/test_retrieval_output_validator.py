from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/retrieval/fixtures/retrieval_output_validator_cases.json"
VALIDATOR_PATH = ROOT / "scripts/retrieval_output_validator.py"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retrieval_output_validator", VALIDATOR_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator_module = load_validator()
KNOWN_DIAGNOSTIC_CODES = validator_module.KNOWN_DIAGNOSTIC_CODES
SAFE_DIAGNOSTIC_FIELDS = validator_module.SAFE_DIAGNOSTIC_FIELDS
ValidationResult = validator_module.ValidationResult
load_fixture_file = validator_module.load_fixture_file
validate_case = validator_module.validate_case
validate_output = validator_module.validate_output

EXPECTED_DIAGNOSTIC_CODES = {
    "missing_required_field",
    "malformed_output_shape",
    "unknown_id_namespace",
    "unresolved_citation_key",
    "ambiguous_citation_key",
    "unresolved_evidence_span",
    "orphaned_source_path",
    "orphaned_legal_unit_path",
    "id_path_mismatch",
    "superseded_evidence",
    "wrong_edition",
    "answer_claim_without_evidence",
    "citation_without_evidence",
    "unsafe_no_answer_shape",
    "forbidden_payload_field",
    "scoped_no_answer",
}

REQUIRED_CASE_IDS = {
    "CASE-M012-VALID-RETRIEVAL": "accepted",
    "CASE-M012-VALID-ANSWER-CLAIM": "accepted",
    "CASE-M012-SCOPED-NOANSWER": "accepted_scoped_no_answer",
    "CASE-M012-MISSING-EVIDENCE-SPAN-ID": "rejected",
    "CASE-M012-MALFORMED-CITATIONS-SHAPE": "rejected",
    "CASE-M012-UNKNOWN-ID-NAMESPACE": "rejected",
    "CASE-M012-UNRESOLVED-CITATION-KEY": "rejected",
    "CASE-M012-AMBIGUOUS-CITATION-KEY": "rejected",
    "CASE-M012-UNRESOLVED-EVIDENCE-SPAN-ID": "rejected",
    "CASE-M012-ORPHANED-SOURCE-BLOCK": "rejected",
    "CASE-M012-ORPHANED-LEGAL-UNIT": "rejected",
    "CASE-M012-SOURCE-PATH-MISMATCH": "rejected",
    "CASE-M012-SUPERSEDED-EVIDENCE-SPAN": "rejected",
    "CASE-M012-WRONG-ACT-EDITION": "rejected",
    "CASE-M012-ANSWER-CLAIM-WITHOUT-EVIDENCE": "rejected",
    "CASE-M012-CITATION-WITHOUT-EVIDENCE": "rejected",
    "CASE-M012-UNSAFE-NOANSWER-WITH-CITATION": "rejected",
    "CASE-M012-FORBIDDEN-RAW-TEXT-FIELD": "rejected",
}

REQUIRED_GRAPH_COUNTS = {
    "legal_acts": 1,
    "act_editions": 2,
    "legal_units": 2,
    "source_documents": 2,
    "source_blocks": 3,
    "evidence_spans": 5,
}

SAFE_DIAGNOSTIC_FIELDS = {
    "code",
    "severity",
    "result",
    "field_path",
    "retrieval_output_id",
    "scope_id",
    "case_id",
    "safe_id_value",
    "expected_id",
    "resolved_id",
    "fixture_artifact",
}

REQUIRED_NON_CLAIMS = {
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove FalkorDB runtime behavior.",
    "Does not prove generated-Cypher safety.",
    "Does not prove legal-answer correctness.",
}

FORBIDDEN_CONTENT_SNIPPETS = {
    "according to the law",
    "user prompt",
    "provider response body",
    "BEGIN PRIVATE KEY",
    "embedding_vector",
    "GRAPH.QUERY row",
    "legal advice:",
}


def load_fixture() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def assert_safe_validation_result(result: ValidationResult, *, case_id: str) -> None:
    assert result.result in {"accepted", "accepted_scoped_no_answer", "rejected"}
    for diagnostic in result.diagnostics:
        payload = diagnostic.to_dict()
        assert set(payload) <= SAFE_DIAGNOSTIC_FIELDS
        assert payload["case_id"] == case_id
        assert payload["code"] in EXPECTED_DIAGNOSTIC_CODES
        assert payload["code"] in KNOWN_DIAGNOSTIC_CODES
        assert payload["severity"] in {"error", "warning", "info"}
        assert payload["result"] in {"accepted", "accepted_scoped_no_answer", "rejected"}
        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in FORBIDDEN_CONTENT_SNIPPETS:
            assert forbidden not in serialized


def assert_retrieval_fixture_inventory(data: dict) -> None:
    required_top_level = {
        "schema_version",
        "non_authoritative",
        "fixture_graph",
        "cases",
        "expected_diagnostics",
        "diagnostic_inventory",
        "non_claims",
    }
    missing = required_top_level - set(data)
    assert not missing, f"missing top-level sections: {sorted(missing)}"
    assert data["schema_version"] == "retrieval-output-validator-fixtures/v1"
    assert data["non_authoritative"] is True
    assert REQUIRED_NON_CLAIMS <= set(data["non_claims"])

    graph = data["fixture_graph"]
    for section, min_count in REQUIRED_GRAPH_COUNTS.items():
        assert section in graph, f"missing fixture_graph.{section}"
        assert isinstance(graph[section], list), f"fixture_graph.{section} must be a list"
        assert len(graph[section]) >= min_count, f"fixture_graph.{section} needs at least {min_count} records"
    assert isinstance(graph.get("citation_bindings"), list), "fixture_graph.citation_bindings must be a list"

    diagnostic_codes = {entry["code"] for entry in data["diagnostic_inventory"]}
    assert diagnostic_codes == EXPECTED_DIAGNOSTIC_CODES

    cases = data["cases"]
    assert isinstance(cases, list), "cases must be a list"
    case_ids = [case.get("case_id") for case in cases]
    assert all(isinstance(case_id, str) and case_id for case_id in case_ids), "case IDs must be non-empty strings"
    duplicated_case_ids = [case_id for case_id, count in Counter(case_ids).items() if count > 1]
    assert not duplicated_case_ids, f"duplicate case IDs: {duplicated_case_ids}"

    cases_by_id = {case["case_id"]: case for case in cases}
    missing_cases = set(REQUIRED_CASE_IDS) - set(cases_by_id)
    assert not missing_cases, f"missing required cases: {sorted(missing_cases)}"
    for case_id, expected_result in REQUIRED_CASE_IDS.items():
        actual_result = cases_by_id[case_id].get("expected_result")
        assert actual_result == expected_result, f"bad result for {case_id}: {actual_result!r}"

    expected_diagnostics = data["expected_diagnostics"]
    assert set(expected_diagnostics) == set(case_ids), "expected_diagnostics keys must align with cases"

    represented_codes: set[str] = set()
    for case in cases:
        case_id = case["case_id"]
        expected_result = case.get("expected_result")
        expected_codes = case.get("expected_diagnostic_codes")
        assert expected_result in {"accepted", "accepted_scoped_no_answer", "rejected"}, f"bad result for {case_id}"
        assert isinstance(expected_codes, list), f"{case_id} missing expected_diagnostic_codes list"
        assert set(expected_codes) <= EXPECTED_DIAGNOSTIC_CODES, f"{case_id} has unknown diagnostic code"
        represented_codes.update(expected_codes)

        diagnostic_entries = expected_diagnostics[case_id]
        assert [entry["code"] for entry in diagnostic_entries] == expected_codes
        if expected_result == "rejected":
            assert expected_codes, f"{case_id} rejected case must expect at least one diagnostic code"
            assert any(code != "scoped_no_answer" for code in expected_codes), f"{case_id} must fail closed with error code"
        elif expected_result == "accepted":
            assert expected_codes == [], f"{case_id} accepted case must not expect errors"
        else:
            assert expected_codes == ["scoped_no_answer"], f"{case_id} scoped no-answer must expect only info code"

        for diagnostic in diagnostic_entries:
            extra_fields = set(diagnostic) - SAFE_DIAGNOSTIC_FIELDS
            assert not extra_fields, f"{case_id} diagnostic has unsafe fields: {sorted(extra_fields)}"
            assert diagnostic["case_id"] == case_id
            assert diagnostic["code"] in EXPECTED_DIAGNOSTIC_CODES
            assert diagnostic["severity"] in {"error", "warning", "info"}
            assert diagnostic["result"] in {"rejected", "accepted", "accepted_scoped_no_answer"}

    assert represented_codes == EXPECTED_DIAGNOSTIC_CODES


def test_fixture_file_inventory_is_bounded_and_complete() -> None:
    data = load_fixture()

    assert_retrieval_fixture_inventory(data)


def test_validator_diagnostic_code_inventory_matches_contract() -> None:
    assert KNOWN_DIAGNOSTIC_CODES == EXPECTED_DIAGNOSTIC_CODES


def test_validator_executes_all_fixture_cases_with_expected_results_and_codes() -> None:
    data = load_fixture()
    fixture = load_fixture_file(FIXTURE_PATH)

    for case in data["cases"]:
        result = validate_case(case, fixture)

        assert result.result == case["expected_result"], case["case_id"]
        assert [diagnostic.code for diagnostic in result.diagnostics] == case["expected_diagnostic_codes"], case["case_id"]
        assert_safe_validation_result(result, case_id=case["case_id"])
        if case["expected_result"] == "accepted":
            assert not result.diagnostics
        elif case["expected_result"] == "accepted_scoped_no_answer":
            assert [diagnostic.severity for diagnostic in result.diagnostics] == ["info"]
        else:
            assert any(diagnostic.severity == "error" for diagnostic in result.diagnostics)


def test_validator_rejects_malformed_ad_hoc_envelopes_fail_closed() -> None:
    fixture = load_fixture_file(FIXTURE_PATH)

    non_object = validate_output(["not", "an", "object"], fixture, case_id="ADHOC-NON-OBJECT")
    assert non_object.result == "rejected"
    assert [diagnostic.code for diagnostic in non_object.diagnostics] == ["malformed_output_shape"]
    assert_safe_validation_result(non_object, case_id="ADHOC-NON-OBJECT")

    missing_fields = validate_output({}, fixture, case_id="ADHOC-MISSING-FIELDS")
    assert missing_fields.result == "rejected"
    assert "missing_required_field" in [diagnostic.code for diagnostic in missing_fields.diagnostics]
    assert "malformed_output_shape" in [diagnostic.code for diagnostic in missing_fields.diagnostics]
    assert_safe_validation_result(missing_fields, case_id="ADHOC-MISSING-FIELDS")


def test_validator_redacts_forbidden_payload_values_from_diagnostics() -> None:
    data = load_fixture()
    fixture = load_fixture_file(FIXTURE_PATH)
    output = copy.deepcopy(data["cases"][0]["output"])
    output["raw_legal_text"] = "according to the law: legal advice: BEGIN PRIVATE KEY"
    output["provider_payload"] = {"body": "provider response body", "vector": "embedding_vector"}

    result = validate_output(output, fixture, case_id="ADHOC-FORBIDDEN-PAYLOAD")

    assert result.result == "rejected"
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "forbidden_payload_field",
        "forbidden_payload_field",
        "forbidden_payload_field",
    ]
    assert_safe_validation_result(result, case_id="ADHOC-FORBIDDEN-PAYLOAD")
    serialized = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "raw_legal_text" in serialized
    assert "provider_payload" in serialized
    for forbidden in FORBIDDEN_CONTENT_SNIPPETS:
        assert forbidden not in serialized


def test_fixture_graph_contains_required_static_resolution_records() -> None:
    data = load_fixture()
    graph = data["fixture_graph"]

    assert {record["legal_act_id"] for record in graph["legal_acts"]} == {"LA-M012-44FZ"}
    assert {record["act_edition_id"] for record in graph["act_editions"]} == {
        "ED-M012-44FZ-2023-01-01",
        "ED-M012-44FZ-2024-01-01",
    }
    assert {record["legal_unit_id"] for record in graph["legal_units"]} == {
        "LU-M012-44FZ-ART-001",
        "LU-M012-44FZ-ART-001-OLD",
    }
    assert {record["source_document_id"] for record in graph["source_documents"]} == {
        "SD-M012-44FZ-CONSULTANT",
        "SD-M012-44FZ-GARANT",
    }
    assert {record["source_block_id"] for record in graph["source_blocks"]} >= {
        "SB-M012-001",
        "SB-M012-002",
        "SB-M012-ORPHAN",
    }
    assert {record["evidence_span_id"] for record in graph["evidence_spans"]} >= {
        "EV-M012-001",
        "EV-M012-002",
        "EV-M012-SUPERSEDED",
        "EV-M012-ORPHAN-SOURCE",
        "EV-M012-ORPHAN-LEGAL",
    }

    bindings_by_key = Counter(binding["citation_key"] for binding in graph["citation_bindings"])
    assert bindings_by_key["CIT-M012-001"] == 1
    assert bindings_by_key["CIT-M012-002"] == 1
    assert bindings_by_key["CIT-M012-AMBIG"] == 2
    assert bindings_by_key["CIT-M012-SUPERSEDED"] == 1


def test_scoped_no_answer_is_only_accepted_empty_citation_claim_case() -> None:
    data = load_fixture()

    empty_cases = []
    for case in data["cases"]:
        output = case["output"]
        if output.get("citations") == [] and output.get("answer_claims", []) == []:
            empty_cases.append(case)

    assert [case["case_id"] for case in empty_cases] == ["CASE-M012-SCOPED-NOANSWER"]
    no_answer = empty_cases[0]
    assert no_answer["output"]["output_kind"] == "scoped_no_answer"
    assert no_answer["expected_result"] == "accepted_scoped_no_answer"
    assert no_answer["expected_diagnostic_codes"] == ["scoped_no_answer"]


def test_fixture_data_contains_no_raw_text_or_unbounded_payload_values() -> None:
    data = load_fixture()
    serialized = json.dumps(data, ensure_ascii=False)

    for forbidden in FORBIDDEN_CONTENT_SNIPPETS:
        assert forbidden not in serialized
    assert "FORBIDDEN-SENTINEL-NO-RAW-CONTENT" in serialized
    assert "provider_payload" not in serialized
    assert "falkordb_row" not in serialized
    assert '"prompt"' not in serialized.lower()
    assert '"vector"' not in serialized.lower()


def test_inventory_rejects_missing_top_level_section() -> None:
    data = load_fixture()
    broken = copy.deepcopy(data)
    del broken["expected_diagnostics"]

    with pytest.raises(AssertionError, match="missing top-level sections"):
        assert_retrieval_fixture_inventory(broken)


def test_inventory_rejects_non_list_graph_section() -> None:
    data = load_fixture()
    broken = copy.deepcopy(data)
    broken["fixture_graph"]["evidence_spans"] = {"evidence_span_id": "EV-M012-001"}

    with pytest.raises(AssertionError, match="fixture_graph.evidence_spans must be a list"):
        assert_retrieval_fixture_inventory(broken)


def test_inventory_rejects_empty_case_id() -> None:
    data = load_fixture()
    broken = copy.deepcopy(data)
    original_case_id = broken["cases"][0]["case_id"]
    broken["cases"][0]["case_id"] = ""
    broken["expected_diagnostics"][""] = broken["expected_diagnostics"].pop(original_case_id)

    with pytest.raises(AssertionError, match="case IDs must be non-empty strings"):
        assert_retrieval_fixture_inventory(broken)


def test_inventory_rejects_duplicate_case_id() -> None:
    data = load_fixture()
    broken = copy.deepcopy(data)
    broken["cases"][1]["case_id"] = broken["cases"][0]["case_id"]

    with pytest.raises(AssertionError, match="duplicate case IDs"):
        assert_retrieval_fixture_inventory(broken)


def test_inventory_rejects_missing_expected_result_or_codes() -> None:
    data = load_fixture()
    missing_result = copy.deepcopy(data)
    del missing_result["cases"][0]["expected_result"]

    with pytest.raises(AssertionError, match="bad result"):
        assert_retrieval_fixture_inventory(missing_result)

    missing_codes = copy.deepcopy(data)
    del missing_codes["cases"][0]["expected_diagnostic_codes"]

    with pytest.raises(AssertionError, match="missing expected_diagnostic_codes list"):
        assert_retrieval_fixture_inventory(missing_codes)
