from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.offline_retrieval_cases import (
    OfflineRetrievalCaseBuilder,
    stable_retrieval_case_json,
)
from law_nexus.ports.offline_retrieval_cases import (
    OFFLINE_RETRIEVAL_CASE_NON_CLAIMS,
    OfflineRetrievalCaseBuildRequest,
    OfflineRetrievalSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_request() -> OfflineRetrievalCaseBuildRequest:
    real_cases_path = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
    hierarchy_jsonl_path = ROOT / "prd/parser/consultant_hierarchy_records.jsonl"
    real_cases = json.loads(real_cases_path.read_text(encoding="utf-8"))
    hierarchy_records = [
        json.loads(line)
        for line in hierarchy_jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return OfflineRetrievalCaseBuildRequest(
        real_cases=real_cases,
        hierarchy_records=hierarchy_records,
        source_artifacts=(
            OfflineRetrievalSourceArtifact(
                path="prd/retrieval/offline_citation_retrieval_contract.md",
                sha256="sha-contract",
            ),
            OfflineRetrievalSourceArtifact(
                path="prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
                sha256="sha-real-cases",
            ),
        ),
    )


def test_offline_retrieval_case_builder_emits_expected_contract_shape() -> None:
    payload = OfflineRetrievalCaseBuilder().build_payload(_fixture_request())

    assert payload["schema_version"] == "offline-citation-retrieval-cases/v1"
    assert payload["generated_by"] == "scripts/build-offline-citation-retrieval-cases.py"
    assert payload["non_authoritative"] is True
    assert payload["non_claims"] == list(OFFLINE_RETRIEVAL_CASE_NON_CLAIMS)
    assert payload["source_artifacts"] == [
        {"path": "prd/retrieval/offline_citation_retrieval_contract.md", "sha256": "sha-contract"},
        {"path": "prd/retrieval/fixtures/real_artifact_retrieval_cases.json", "sha256": "sha-real-cases"},
    ]
    assert len(payload["cases"]) == 6


def test_offline_retrieval_case_builder_keeps_case_diagnostics_bounded() -> None:
    payload = OfflineRetrievalCaseBuilder().build_payload(_fixture_request())
    cases = {case["case_id"]: case for case in payload["cases"]}

    scoped_no_answer = cases["CASE-M014-SCOPED-NO-CANDIDATE"]
    assert scoped_no_answer["output"]["output_kind"] == "scoped_no_answer"
    assert scoped_no_answer["output"]["citations"] == []
    assert scoped_no_answer["expected_diagnostic_codes"] == ["scoped_no_candidate", "scoped_no_answer"]

    ambiguous = cases["CASE-M014-AMBIGUOUS-CANDIDATE-SET"]
    assert ambiguous["expected_selection_result"] == "rejected"
    assert ambiguous["diagnostics"] == [
        {
            "case_id": "CASE-M014-AMBIGUOUS-CANDIDATE-SET",
            "code": "ambiguous_candidate_set",
            "field_path": "candidates",
            "proof_artifact": "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
            "query_id": "QUERY-M014-AMBIGUOUS-CLAUSE-MARKER-001",
            "severity": "error",
        }
    ]


def test_stable_retrieval_case_json_is_deterministic() -> None:
    payload = OfflineRetrievalCaseBuilder().build_payload(_fixture_request())

    first = stable_retrieval_case_json(payload)
    second = stable_retrieval_case_json(payload)

    assert first == second
    assert first.endswith("\n")
    assert '"raw_legal_text":' not in first
    assert '"generated_answer_prose":' not in first
    assert "raw_legal_text" in payload["selection_contract"]["forbidden_payload_fields"]
    assert "generated_answer_prose" in payload["selection_contract"]["forbidden_payload_fields"]
