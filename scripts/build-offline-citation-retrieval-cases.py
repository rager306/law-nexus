#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/offline_citation_retrieval_contract.md"
REAL_CASES_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
HIERARCHY_JSON_PATH = ROOT / "prd/parser/consultant_hierarchy_records.json"
HIERARCHY_JSONL_PATH = ROOT / "prd/parser/consultant_hierarchy_records.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"

SCHEMA_VERSION = "offline-citation-retrieval-cases/v1"
GENERATED_BY = "scripts/build-offline-citation-retrieval-cases.py"
VALIDATOR_CONTRACT_VERSION = "retrieval-output-validator/v1"
AS_OF_DATE = "2026-01-01"
SOURCE_CORPUS_ID = "CORPUS-M014-CONSULTANT-44FZ"
SCOPE_ID = "SCOPE-M014-CONSULTANT-44FZ-2026-001"
RETRIEVAL_RUN_ID = "RUN-M014-OFFLINE-CITATION-001"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"

NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not prove local embedding quality.",
    "Does not close GATE-G008 unless final milestone validation explicitly confirms full gate criteria.",
    "Does not close GATE-G011.",
    "Does not make LLM output legal authority.",
    "Does not make proof-local IDs production IDs.",
]

SOURCE_ARTIFACT_PATHS = [
    CONTRACT_PATH,
    REAL_CASES_PATH,
    HIERARCHY_JSON_PATH,
    HIERARCHY_JSONL_PATH,
    STAGING_GRAPH_PATH,
]

FORBIDDEN_PAYLOAD_FIELDS = [
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
]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replace_m013_with_m014(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("M013", "M014")
    if isinstance(value, list):
        return [replace_m013_with_m014(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_m013_with_m014(item) for key, item in value.items()}
    return value


def source_artifacts() -> list[dict[str, str]]:
    return [
        {
            "path": relative(path),
            "sha256": sha256_path(path),
        }
        for path in SOURCE_ARTIFACT_PATHS
    ]


def record_by_id(records: list[dict[str, Any]], record_id: str) -> dict[str, Any]:
    return next(record for record in records if record["id"] == record_id)


def base_scope(query_id: str) -> dict[str, str]:
    return {
        "scope_id": SCOPE_ID,
        "query_id": query_id,
        "retrieval_run_id": RETRIEVAL_RUN_ID,
        "as_of_date": AS_OF_DATE,
        "source_corpus_id": SOURCE_CORPUS_ID,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
    }


def validator_output(*, query_id: str, output_id: str, citation_key: str, evidence_span_id: str, source_block_id: str) -> dict[str, Any]:
    return {
        "retrieval_output_id": output_id,
        "output_kind": "retrieval_candidate",
        "scope": base_scope(query_id),
        "citations": [
            {
                "retrieval_output_id": output_id,
                "citation_key": citation_key,
                "evidence_span_id": evidence_span_id,
                "source_block_id": source_block_id,
                "source_document_id": "SD-M014-DOC-CONS-44FZ",
                "legal_unit_id": "LU-M014-HIER-CONS-ARTICLE-0001",
                "act_edition_id": "ED-M014-44FZ-2026-01-01",
            }
        ],
        "answer_claims": [],
    }


def scoped_no_answer_output(query_id: str) -> dict[str, Any]:
    return {
        "retrieval_output_id": "RET-M014-SCOPED-NO-CANDIDATE-001",
        "output_kind": "scoped_no_answer",
        "scope": base_scope(query_id),
        "citations": [],
        "answer_claims": [],
    }


def candidate(record: dict[str, Any], *, candidate_id: str, query_id: str, reason: str, output: dict[str, Any] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "query_id": query_id,
        "source_record_id": record["id"],
        "source_path": record["source_path"],
        "source_sha256": record["source_sha256"],
        "excerpt_sha256": record["excerpt_sha256"],
        "selection_reason": reason,
    }
    if output is not None:
        payload["validator_output"] = output
    return payload


def diagnostic(code: str, *, case_id: str, query_id: str, severity: str = "error", candidate_id: str | None = None, field_path: str | None = None) -> dict[str, str]:
    payload = {
        "code": code,
        "severity": severity,
        "case_id": case_id,
        "query_id": query_id,
        "proof_artifact": FIXTURE_ARTIFACT,
    }
    if candidate_id:
        payload["candidate_id"] = candidate_id
    if field_path:
        payload["field_path"] = field_path
    return payload


def case(
    *,
    case_id: str,
    case_class: str,
    query: dict[str, Any],
    candidates: list[dict[str, Any]],
    expected_selection_result: str,
    expected_validator_result: str | None,
    expected_diagnostic_codes: list[str],
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "case_id": case_id,
        "case_class": case_class,
        "query": query,
        "candidates": candidates,
        "expected_selection_result": expected_selection_result,
        "expected_validator_result": expected_validator_result,
        "expected_diagnostic_codes": expected_diagnostic_codes,
        "diagnostics": diagnostics,
        "source_record_ids": sorted({candidate["source_record_id"] for candidate in candidates}),
        "non_authoritative": True,
    }
    selected = [candidate for candidate in candidates if "validator_output" in candidate]
    if len(selected) == 1:
        payload["output"] = selected[0]["validator_output"]
    elif expected_selection_result == "scoped_no_answer":
        payload["output"] = scoped_no_answer_output(query["query_id"])
    return payload


def build_payload() -> dict[str, Any]:
    real_cases = load_json(REAL_CASES_PATH)
    records = load_jsonl(HIERARCHY_JSONL_PATH)
    article = record_by_id(records, "HIER-CONS-ARTICLE-0001")
    chapter = record_by_id(records, "HIER-CONS-CHAPTER-0001")
    clause_1 = record_by_id(records, "HIER-CONS-CLAUSE-0001")
    clause_2 = record_by_id(records, "HIER-CONS-CLAUSE-0002")

    derived_graph = replace_m013_with_m014(deepcopy(real_cases["derived_fixture_graph"]))

    exact_query = {
        "query_id": "QUERY-M014-EXACT-ARTICLE-0001",
        "query_kind": "exact_id_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": article["id"],
        "expected_result": "selected",
    }
    marker_query = {
        "query_id": "QUERY-M014-MARKER-ARTICLE-0001",
        "query_kind": "marker_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_marker": "статья 1.",
        "expected_result": "selected",
    }
    no_answer_query = {
        "query_id": "QUERY-M014-SCOPED-NO-CANDIDATE-001",
        "query_kind": "scoped_no_answer",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": "HIER-CONS-ARTICLE-9999",
        "expected_result": "scoped_no_answer",
    }
    ambiguous_query = {
        "query_id": "QUERY-M014-AMBIGUOUS-CLAUSE-MARKER-001",
        "query_kind": "ambiguous_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "clause",
        "target_marker": "1",
        "expected_result": "rejected",
    }
    unresolved_query = {
        "query_id": "QUERY-M014-UNRESOLVED-EVIDENCE-001",
        "query_kind": "invalid_candidate",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": article["id"],
        "expected_result": "rejected",
    }
    unsafe_query = {
        "query_id": "QUERY-M014-UNSAFE-PAYLOAD-001",
        "query_kind": "invalid_candidate",
        "scope_id": SCOPE_ID,
        "target_level": "chapter",
        "target_record_id": chapter["id"],
        "expected_result": "rejected",
        "unsafe_payload_fields": ["raw_text"],
    }

    cases = [
        case(
            case_id="CASE-M014-VALID-EXACT-RECORD-CANDIDATE",
            case_class="valid_exact_record_candidate",
            query=exact_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-EXACT",
                    query_id=exact_query["query_id"],
                    reason="exact_record_id_match",
                    output=validator_output(
                        query_id=exact_query["query_id"],
                        output_id="RET-M014-EXACT-ARTICLE-0001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
                        source_block_id="SB-M014-HIER-CONS-ARTICLE-0001",
                    ),
                )
            ],
            expected_selection_result="selected",
            expected_validator_result="accepted",
            expected_diagnostic_codes=[],
            diagnostics=[],
        ),
        case(
            case_id="CASE-M014-VALID-MARKER-LEVEL-CANDIDATE",
            case_class="valid_marker_level_candidate",
            query=marker_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-MARKER",
                    query_id=marker_query["query_id"],
                    reason="marker_level_match",
                    output=validator_output(
                        query_id=marker_query["query_id"],
                        output_id="RET-M014-MARKER-ARTICLE-0001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
                        source_block_id="SB-M014-HIER-CONS-ARTICLE-0001",
                    ),
                )
            ],
            expected_selection_result="selected",
            expected_validator_result="accepted",
            expected_diagnostic_codes=[],
            diagnostics=[],
        ),
        case(
            case_id="CASE-M014-SCOPED-NO-CANDIDATE",
            case_class="scoped_no_candidate",
            query=no_answer_query,
            candidates=[],
            expected_selection_result="scoped_no_answer",
            expected_validator_result="accepted_scoped_no_answer",
            expected_diagnostic_codes=["scoped_no_candidate", "scoped_no_answer"],
            diagnostics=[diagnostic("scoped_no_candidate", case_id="CASE-M014-SCOPED-NO-CANDIDATE", query_id=no_answer_query["query_id"], severity="info")],
        ),
        case(
            case_id="CASE-M014-AMBIGUOUS-CANDIDATE-SET",
            case_class="ambiguous_candidate_set",
            query=ambiguous_query,
            candidates=[
                candidate(clause_1, candidate_id="CAND-M014-CLAUSE-0001-AMBIG", query_id=ambiguous_query["query_id"], reason="ambiguous_candidate_set", output=None),
                candidate(clause_2, candidate_id="CAND-M014-CLAUSE-0002-AMBIG", query_id=ambiguous_query["query_id"], reason="ambiguous_candidate_set", output=None),
            ],
            expected_selection_result="rejected",
            expected_validator_result=None,
            expected_diagnostic_codes=["ambiguous_candidate_set"],
            diagnostics=[diagnostic("ambiguous_candidate_set", case_id="CASE-M014-AMBIGUOUS-CANDIDATE-SET", query_id=ambiguous_query["query_id"], field_path="candidates")],
        ),
        case(
            case_id="CASE-M014-UNRESOLVED-CANDIDATE-EVIDENCE",
            case_class="unresolved_candidate_evidence",
            query=unresolved_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-UNRESOLVED",
                    query_id=unresolved_query["query_id"],
                    reason="unresolved_candidate_evidence",
                    output=validator_output(
                        query_id=unresolved_query["query_id"],
                        output_id="RET-M014-UNRESOLVED-EVIDENCE-001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-ORPHAN-SOURCE",
                        source_block_id="SB-M014-MISSING-SOURCE-BLOCK",
                    ),
                )
            ],
            expected_selection_result="rejected",
            expected_validator_result="rejected",
            expected_diagnostic_codes=["unresolved_candidate_evidence", "id_path_mismatch", "orphaned_source_path"],
            diagnostics=[diagnostic("unresolved_candidate_evidence", case_id="CASE-M014-UNRESOLVED-CANDIDATE-EVIDENCE", query_id=unresolved_query["query_id"], candidate_id="CAND-M014-ARTICLE-0001-UNRESOLVED", field_path="candidates[0].validator_output.citations[0]")],
        ),
        case(
            case_id="CASE-M014-UNSAFE-CANDIDATE-PAYLOAD",
            case_class="unsafe_candidate_payload",
            query=unsafe_query,
            candidates=[
                candidate(chapter, candidate_id="CAND-M014-CHAPTER-0001-UNSAFE", query_id=unsafe_query["query_id"], reason="unsafe_payload_rejected", output=None)
            ],
            expected_selection_result="rejected",
            expected_validator_result=None,
            expected_diagnostic_codes=["unsafe_payload_rejected"],
            diagnostics=[diagnostic("unsafe_payload_rejected", case_id="CASE-M014-UNSAFE-CANDIDATE-PAYLOAD", query_id=unsafe_query["query_id"], candidate_id="CAND-M014-CHAPTER-0001-UNSAFE", field_path="query.unsafe_payload_fields")],
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "generated_by": GENERATED_BY,
        "contract": relative(CONTRACT_PATH),
        "requirement": "GATE-G008",
        "non_authoritative": True,
        "source_artifacts": source_artifacts(),
        "source_summary": {
            "hierarchy_record_count": len(records),
            "selected_record_ids": [article["id"], chapter["id"], clause_1["id"], clause_2["id"]],
        },
        "namespace_strategy": {
            "status": "m014_proof_local_prefixes_allowed_by_shared_validator",
            "must_preserve_unknown_namespace_rejection": True,
        },
        "selection_contract": {
            "allowed_reason_codes": [
                "exact_record_id_match",
                "marker_level_match",
                "scoped_no_candidate",
                "ambiguous_candidate_set",
                "unresolved_candidate_evidence",
                "unsafe_payload_rejected",
            ],
            "forbidden_payload_fields": FORBIDDEN_PAYLOAD_FIELDS,
        },
        "derived_fixture_graph": derived_graph,
        "cases": cases,
        "non_claims": NON_CLAIMS,
    }


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic M014 offline citation retrieval seed cases.")
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in fixture is stale.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Fixture output path.")
    args = parser.parse_args(argv)

    payload = build_payload()
    rendered = stable_json(payload)
    output_path = args.output
    if args.check:
        try:
            current = output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(json.dumps({"status": "fail", "reason": "missing_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        if current != rendered:
            print(json.dumps({"status": "fail", "reason": "stale_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        print(json.dumps({"status": "pass", "case_count": len(payload["cases"]), "path": relative(output_path)}, sort_keys=True))
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "written", "case_count": len(payload["cases"]), "path": relative(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
