from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.real_artifact_retrieval_cases import (
    RealArtifactRetrievalCaseBuilder,
    stable_real_artifact_retrieval_json,
)
from law_nexus.ports.real_artifact_retrieval_cases import (
    REAL_ARTIFACT_RETRIEVAL_CASE_NON_CLAIMS,
    RealArtifactRetrievalCaseBuildRequest,
    RealArtifactSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]


def _request() -> RealArtifactRetrievalCaseBuildRequest:
    hierarchy_summary = json.loads((ROOT / "prd/parser/consultant_hierarchy_records.json").read_text(encoding="utf-8"))
    staging_graph = json.loads((ROOT / "prd/parser/parser_staging_graph.json").read_text(encoding="utf-8"))
    hierarchy_records = [
        json.loads(line)
        for line in (ROOT / "prd/parser/consultant_hierarchy_records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return RealArtifactRetrievalCaseBuildRequest(
        hierarchy_summary=hierarchy_summary,
        staging_graph=staging_graph,
        hierarchy_records=hierarchy_records,
        source_artifacts=(
            RealArtifactSourceArtifact(path="prd/parser/consultant_hierarchy_records.json", sha256="sha-summary"),
            RealArtifactSourceArtifact(path="prd/parser/consultant_hierarchy_records.jsonl", sha256="sha-records"),
            RealArtifactSourceArtifact(path="prd/parser/parser_staging_graph.json", sha256="sha-graph"),
        ),
    )


def test_real_artifact_case_builder_handles_current_hierarchy_summary_without_source_key() -> None:
    payload = RealArtifactRetrievalCaseBuilder().build_payload(_request())

    assert payload["schema_version"] == "real-artifact-retrieval-cases/v1"
    assert payload["generated_by"] == "scripts/build-real-artifact-retrieval-cases.py"
    assert payload["non_authoritative"] is True
    assert payload["non_claims"] == list(REAL_ARTIFACT_RETRIEVAL_CASE_NON_CLAIMS)
    assert payload["source_artifacts"] == [
        {"path": "prd/parser/consultant_hierarchy_records.json", "sha256": "sha-summary"},
        {"path": "prd/parser/consultant_hierarchy_records.jsonl", "sha256": "sha-records"},
        {"path": "prd/parser/parser_staging_graph.json", "sha256": "sha-graph"},
    ]
    assert payload["source_summary"]["source_path"]
    assert payload["source_summary"]["source_sha256"]
    assert len(payload["cases"]) == 7


def test_real_artifact_case_builder_preserves_expected_diagnostics() -> None:
    payload = RealArtifactRetrievalCaseBuilder().build_payload(_request())
    cases = {case["case_id"]: case for case in payload["cases"]}

    assert cases["CASE-M013-VALID-REAL-ARTIFACT"]["expected_result"] == "accepted"
    assert cases["CASE-M013-SCOPED-NO-ANSWER"]["output"]["output_kind"] == "scoped_no_answer"
    assert cases["CASE-M013-AMBIGUOUS-CITATION"]["expected_diagnostic_codes"] == ["ambiguous_citation_key"]
    assert payload["expected_diagnostics"] == {
        "CASE-M013-AMBIGUOUS-CITATION": ["ambiguous_citation_key"],
        "CASE-M013-MISSING-EVIDENCE-ID": ["missing_required_field"],
        "CASE-M013-SCOPED-NO-ANSWER": ["scoped_no_answer"],
        "CASE-M013-UNRESOLVED-SOURCE-BLOCK": ["id_path_mismatch", "orphaned_source_path"],
        "CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION": ["unsafe_no_answer_shape"],
        "CASE-M013-VALID-REAL-ARTIFACT": [],
        "CASE-M013-WRONG-EDITION-PROXY": ["wrong_edition"],
    }


def test_stable_real_artifact_retrieval_json_is_deterministic() -> None:
    payload = RealArtifactRetrievalCaseBuilder().build_payload(_request())

    first = stable_real_artifact_retrieval_json(payload)
    second = stable_real_artifact_retrieval_json(payload)

    assert first == second
    assert first.endswith("\n")
    assert '"raw_legal_text":' not in first
    assert '"generated_answer_prose":' not in first
