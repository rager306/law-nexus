from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.citation_safe_answer_validator import (
    CitationSafeAnswerValidator,
    build_citation_safe_fixture,
)
from law_nexus.ports.citation_safe_answer_validator import (
    CITATION_SAFE_ANSWER_VALIDATOR_NON_CLAIMS,
    CitationSafeAnswerValidationRequest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/retrieval/fixtures/retrieval_output_validator_cases.json"


def _fixture_data() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> dict[str, object]:
    for case in _fixture_data()["cases"]:  # type: ignore[index]
        if case["case_id"] == case_id:
            return case
    raise AssertionError(f"case not found: {case_id}")


def _request(case_id: str) -> CitationSafeAnswerValidationRequest:
    case = _case(case_id)
    return CitationSafeAnswerValidationRequest(
        output=case["output"],
        fixture_data=_fixture_data(),
        fixture_artifact="prd/retrieval/fixtures/retrieval_output_validator_cases.json",
        case_id=case_id,
    )


def test_validator_accepts_cited_answer_and_exposes_bounded_result() -> None:
    result = CitationSafeAnswerValidator().validate(_request("CASE-M012-VALID-ANSWER-CLAIM"))

    assert result.result == "accepted"
    assert result.diagnostics == ()
    assert result.non_claims == CITATION_SAFE_ANSWER_VALIDATOR_NON_CLAIMS
    assert result.to_dict() == {"result": "accepted", "diagnostics": []}


def test_validator_accepts_scoped_no_answer_without_citation() -> None:
    result = CitationSafeAnswerValidator().validate(_request("CASE-M012-SCOPED-NOANSWER"))

    assert result.result == "accepted_scoped_no_answer"
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["scoped_no_answer"]
    assert result.diagnostics[0].severity == "info"


def test_validator_rejects_missing_and_unsafe_citations_with_safe_diagnostics() -> None:
    missing = CitationSafeAnswerValidator().validate(_request("CASE-M012-ANSWER-CLAIM-WITHOUT-EVIDENCE"))
    unsafe = CitationSafeAnswerValidator().validate(_request("CASE-M012-UNSAFE-NOANSWER-WITH-CITATION"))
    ambiguous = CitationSafeAnswerValidator().validate(_request("CASE-M012-AMBIGUOUS-CITATION-KEY"))

    assert missing.result == "rejected"
    assert "answer_claim_without_evidence" in {diagnostic.code for diagnostic in missing.diagnostics}
    assert unsafe.result == "rejected"
    assert "unsafe_no_answer_shape" in {diagnostic.code for diagnostic in unsafe.diagnostics}
    assert ambiguous.result == "rejected"
    assert "ambiguous_citation_key" in {diagnostic.code for diagnostic in ambiguous.diagnostics}

    for result in (missing, unsafe, ambiguous):
        for diagnostic in result.diagnostics:
            payload = diagnostic.to_dict()
            assert set(payload) <= {
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
            assert "raw_legal_text" not in payload
            assert "answer_text" not in payload


def test_build_citation_safe_fixture_indexes_fixture_graph() -> None:
    fixture = build_citation_safe_fixture(_fixture_data(), fixture_artifact="prd/retrieval/fixtures/retrieval_output_validator_cases.json")

    assert fixture.fixture_artifact == "prd/retrieval/fixtures/retrieval_output_validator_cases.json"
    assert fixture.citation_bindings_by_scope_key
    assert fixture.evidence_spans_by_id
    assert fixture.source_blocks_by_id
    assert fixture.legal_units_by_id
