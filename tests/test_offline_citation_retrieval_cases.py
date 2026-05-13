from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd" / "retrieval" / "fixtures" / "offline_citation_retrieval_cases.json"
BUILDER_PATH = ROOT / "scripts" / "build-offline-citation-retrieval-cases.py"
VALIDATOR_PATH = ROOT / "scripts" / "retrieval_output_validator.py"

REQUIRED_CASE_CLASSES = {
    "valid_exact_record_candidate",
    "valid_marker_level_candidate",
    "scoped_no_candidate",
    "ambiguous_candidate_set",
    "unresolved_candidate_evidence",
    "unsafe_candidate_payload",
}

REQUIRED_SELECTION_REASONS = {
    "exact_record_id_match",
    "marker_level_match",
    "scoped_no_candidate",
    "ambiguous_candidate_set",
    "unresolved_candidate_evidence",
    "unsafe_payload_rejected",
}

FORBIDDEN_FIELD_NAMES = {
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

REQUIRED_NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not prove local embedding quality.",
    "Does not close GATE-G008 unless final milestone validation explicitly confirms full gate criteria.",
    "Does not close GATE-G011.",
    "Does not make LLM output legal authority.",
    "Does not make proof-local IDs production IDs.",
]


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retrieval_output_validator_for_m014_tests", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def walk(value: Any) -> Sequence[Any]:
    values = [value]
    if isinstance(value, Mapping):
        for item in value.values():
            values.extend(walk(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk(item))
    return values


def test_fixture_top_level_contract_and_source_artifacts() -> None:
    fixture = load_fixture()

    assert fixture["schema_version"] == "offline-citation-retrieval-cases/v1"
    assert fixture["fixture_artifact"] == "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
    assert fixture["generated_by"] == "scripts/build-offline-citation-retrieval-cases.py"
    assert fixture["requirement"] == "GATE-G008"
    assert fixture["non_authoritative"] is True
    assert fixture["contract"] == "prd/retrieval/offline_citation_retrieval_contract.md"
    assert fixture["namespace_strategy"]["status"] == "m014_proof_local_prefixes_allowed_by_shared_validator"
    assert fixture["namespace_strategy"]["must_preserve_unknown_namespace_rejection"] is True

    source_artifacts = fixture["source_artifacts"]
    paths = {artifact["path"] for artifact in source_artifacts}
    for path in [
        "prd/retrieval/offline_citation_retrieval_contract.md",
        "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
        "prd/parser/consultant_hierarchy_records.json",
        "prd/parser/consultant_hierarchy_records.jsonl",
        "prd/parser/parser_staging_graph.json",
    ]:
        assert path in paths
        assert (ROOT / path).exists()
    for artifact in source_artifacts:
        assert len(artifact["sha256"]) == 64
        int(artifact["sha256"], 16)


def test_fixture_contains_required_case_classes_and_deterministic_ids() -> None:
    fixture = load_fixture()
    cases = fixture["cases"]

    assert len(cases) == 6
    assert {case["case_class"] for case in cases} == REQUIRED_CASE_CLASSES
    assert all(case["case_id"].startswith("CASE-M014-") for case in cases)
    assert all(case["query"]["query_id"].startswith("QUERY-M014-") for case in cases)
    assert all(case["query"]["scope_id"].startswith("SCOPE-M014-") for case in cases)
    assert all(case["non_authoritative"] is True for case in cases)

    candidate_ids: list[str] = []
    for case in cases:
        for candidate in case["candidates"]:
            candidate_ids.append(candidate["candidate_id"])
            assert candidate["candidate_id"].startswith("CAND-M014-")
            assert candidate["selection_reason"] in REQUIRED_SELECTION_REASONS
            assert candidate["source_path"] == "law-source/consultant/44-FZ-2026.xml"
            assert len(candidate["source_sha256"]) == 64
            assert len(candidate["excerpt_sha256"]) == 64
    assert len(candidate_ids) == len(set(candidate_ids))


def test_valid_and_no_answer_cases_have_validator_compatible_outputs() -> None:
    fixture = load_fixture()
    validator = load_validator()
    validator_fixture = validator.build_fixture(
        {"fixture_graph": fixture["derived_fixture_graph"]},
        fixture_artifact=fixture["fixture_artifact"],
    )

    expected = {
        case["case_id"]: case["expected_validator_result"]
        for case in fixture["cases"]
        if case["expected_validator_result"] is not None
    }
    assert expected

    for case in fixture["cases"]:
        if case["expected_validator_result"] is None:
            assert "output" not in case
            continue
        result = validator.validate_case(case, validator_fixture)
        assert result.result == case["expected_validator_result"]
        if case["expected_validator_result"] == "accepted":
            assert [diagnostic.code for diagnostic in result.diagnostics] == []
        elif case["expected_validator_result"] == "accepted_scoped_no_answer":
            assert [diagnostic.code for diagnostic in result.diagnostics] == ["scoped_no_answer"]
        elif case["case_class"] == "unresolved_candidate_evidence":
            assert [diagnostic.code for diagnostic in result.diagnostics] == ["id_path_mismatch", "orphaned_source_path"]


def test_redaction_forbids_raw_payload_field_names_and_large_legal_text() -> None:
    fixture = load_fixture()

    for value in walk(fixture):
        if isinstance(value, Mapping):
            forbidden_keys = FORBIDDEN_FIELD_NAMES.intersection(value.keys())
            assert not forbidden_keys
        if isinstance(value, str):
            assert "Настоящий Федеральный закон регулирует отношения" not in value
            assert "BEGIN PRIVATE KEY" not in value
            assert "/root/" not in value
            assert ".gsd/exec" not in value

    assert set(fixture["selection_contract"]["forbidden_payload_fields"]) == FORBIDDEN_FIELD_NAMES


def test_negative_cases_fail_closed_without_arbitrary_candidate_selection() -> None:
    fixture = load_fixture()
    by_class = {case["case_class"]: case for case in fixture["cases"]}

    ambiguous = by_class["ambiguous_candidate_set"]
    assert ambiguous["expected_selection_result"] == "rejected"
    assert ambiguous["expected_validator_result"] is None
    assert len(ambiguous["candidates"]) == 2
    assert "output" not in ambiguous
    assert ambiguous["expected_diagnostic_codes"] == ["ambiguous_candidate_set"]

    unsafe = by_class["unsafe_candidate_payload"]
    assert unsafe["expected_selection_result"] == "rejected"
    assert unsafe["expected_validator_result"] is None
    assert unsafe["expected_diagnostic_codes"] == ["unsafe_payload_rejected"]
    assert "output" not in unsafe

    scoped = by_class["scoped_no_candidate"]
    assert scoped["expected_selection_result"] == "scoped_no_answer"
    assert scoped["candidates"] == []
    assert scoped["output"]["output_kind"] == "scoped_no_answer"
    assert scoped["output"]["citations"] == []
    assert scoped["output"]["answer_claims"] == []


def test_non_claims_preserve_open_gate_boundaries() -> None:
    fixture = load_fixture()

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim in fixture["non_claims"]


def test_builder_check_mode_passes_for_checked_in_fixture() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/build-offline-citation-retrieval-cases.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload == {
        "case_count": 6,
        "path": "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
        "status": "pass",
    }
