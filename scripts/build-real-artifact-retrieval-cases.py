#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HIERARCHY_JSON_PATH = ROOT / "prd/parser/consultant_hierarchy_records.json"
HIERARCHY_JSONL_PATH = ROOT / "prd/parser/consultant_hierarchy_records.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
MAPPING_PATH = ROOT / "prd/retrieval/real_artifact_evidence_mapping.md"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"

SCHEMA_VERSION = "real-artifact-retrieval-cases/v1"
SCOPE_ID = "SCOPE-M013-CONSULTANT-44FZ-2026-001"
SOURCE_CORPUS_ID = "CORPUS-M013-CONSULTANT-44FZ"
RETRIEVAL_RUN_ID = "RUN-M013-REAL-ARTIFACT-001"
QUERY_ID = "QUERY-M013-REAL-ARTIFACT-001"
AS_OF_DATE = "2026-01-01"
VALIDATOR_CONTRACT_VERSION = "retrieval-output-validator/v1"

NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not prove local embedding quality.",
    "Does not close GATE-G008.",
    "Does not close GATE-G011.",
    "Does not make LLM output legal authority.",
    "Does not make proof-local IDs production IDs.",
]

REQUIRED_CASES = [
    ("CASE-M013-VALID-REAL-ARTIFACT", "valid_real_artifact_path", "accepted", []),
    ("CASE-M013-MISSING-EVIDENCE-ID", "missing_evidence_id", "rejected", ["missing_required_field"]),
    ("CASE-M013-UNRESOLVED-SOURCE-BLOCK", "unresolved_source_block", "rejected", ["id_path_mismatch", "orphaned_source_path"]),
    ("CASE-M013-AMBIGUOUS-CITATION", "ambiguous_citation_key", "rejected", ["ambiguous_citation_key"]),
    ("CASE-M013-WRONG-EDITION-PROXY", "wrong_edition_proxy", "rejected", ["wrong_edition"]),
    ("CASE-M013-SCOPED-NO-ANSWER", "scoped_no_answer", "accepted_scoped_no_answer", ["scoped_no_answer"]),
    ("CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION", "unsafe_no_answer_with_citation", "rejected", ["unsafe_no_answer_shape"]),
]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def select_records(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    document = next(record for record in records if record.get("level") == "document")
    article = next(record for record in records if record.get("level") == "article")
    return document, article


def base_scope() -> dict[str, str]:
    return {
        "scope_id": SCOPE_ID,
        "query_id": QUERY_ID,
        "retrieval_run_id": RETRIEVAL_RUN_ID,
        "as_of_date": AS_OF_DATE,
        "source_corpus_id": SOURCE_CORPUS_ID,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
    }


def valid_citation() -> dict[str, str]:
    return {
        "retrieval_output_id": "RET-M013-REAL-ARTIFACT-001",
        "citation_key": "CIT-M013-HIER-CONS-ARTICLE-0001",
        "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
        "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
        "source_document_id": "SD-M013-DOC-CONS-44FZ",
        "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
        "act_edition_id": "ED-M013-44FZ-2026-01-01",
    }


def make_output(case_id: str, case_class: str) -> dict[str, Any]:
    if case_class == "scoped_no_answer":
        return {
            "retrieval_output_id": "RET-M013-SCOPED-NO-ANSWER",
            "output_kind": "scoped_no_answer",
            "scope": base_scope(),
            "citations": [],
            "answer_claims": [],
        }

    citation = valid_citation()
    retrieval_output_id = citation["retrieval_output_id"]
    output_kind = "retrieval_candidate"
    citations = [citation]
    answer_claims: list[dict[str, Any]] = []

    if case_class == "missing_evidence_id":
        citation = citation.copy()
        citation.pop("evidence_span_id")
        citations = [citation]
    elif case_class == "unresolved_source_block":
        citation = citation.copy()
        citation["evidence_span_id"] = "EV-M013-ORPHAN-SOURCE"
        citation["source_block_id"] = "SB-M013-MISSING-SOURCE-BLOCK"
        citations = [citation]
    elif case_class == "ambiguous_citation_key":
        citation = citation.copy()
        citation["citation_key"] = "CIT-M013-AMBIG"
        citations = [citation]
    elif case_class == "wrong_edition_proxy":
        citation = citation.copy()
        citation["act_edition_id"] = "ED-M013-44FZ-1900-01-01"
        citations = [citation]
    elif case_class == "unsafe_no_answer_with_citation":
        retrieval_output_id = "RET-M013-UNSAFE-NO-ANSWER-WITH-CITATION"
        citation = citation.copy()
        citation["retrieval_output_id"] = retrieval_output_id
        output_kind = "scoped_no_answer"
        citations = [citation]

    return {
        "retrieval_output_id": retrieval_output_id,
        "output_kind": output_kind,
        "scope": base_scope(),
        "citations": citations,
        "answer_claims": answer_claims,
    }


def build_payload() -> dict[str, Any]:
    hierarchy_summary = load_json(HIERARCHY_JSON_PATH)
    staging_graph = load_json(STAGING_GRAPH_PATH)
    hierarchy_records = load_jsonl(HIERARCHY_JSONL_PATH)
    document_record, article_record = select_records(hierarchy_records)

    source = hierarchy_summary["source"]
    source_sha256 = source["sha256"]
    source_path = source["path"]
    if source_path != article_record["source_path"]:
        raise ValueError("source path mismatch between hierarchy summary and selected article record")
    if source_sha256 != article_record["source_sha256"]:
        raise ValueError("source sha256 mismatch between hierarchy summary and selected article record")

    cases = []
    expected_diagnostics: dict[str, list[str]] = {}
    for case_id, case_class, expected_result, expected_codes in REQUIRED_CASES:
        cases.append(
            {
                "case_id": case_id,
                "case_class": case_class,
                "expected_result": expected_result,
                "expected_diagnostic_codes": expected_codes,
                "source_record_ids": [article_record["id"]] if case_class != "scoped_no_answer" else [],
                "output": make_output(case_id, case_class),
            }
        )
        expected_diagnostics[case_id] = expected_codes

    return {
        "schema_version": SCHEMA_VERSION,
        "non_authoritative": True,
        "contract_version": VALIDATOR_CONTRACT_VERSION,
        "requirement": "R034",
        "fixture_artifact": relative(OUTPUT_PATH),
        "generated_by": relative(Path(__file__)),
        "source_artifacts": [
            {"path": relative(HIERARCHY_JSON_PATH), "sha256": sha256_path(HIERARCHY_JSON_PATH)},
            {"path": relative(HIERARCHY_JSONL_PATH), "sha256": sha256_path(HIERARCHY_JSONL_PATH)},
            {"path": relative(STAGING_GRAPH_PATH), "sha256": sha256_path(STAGING_GRAPH_PATH)},
            {"path": relative(MAPPING_PATH), "sha256": sha256_path(MAPPING_PATH)},
        ],
        "namespace_strategy": {
            "status": "safe_namespace_extension_selected",
            "current_validator_prefixes": ["*-M012-*", "*-M013-*"],
            "proposed_m013_prefixes": ["RET-M013-*", "CIT-M013-*", "EV-M013-*", "SB-M013-*", "SD-M013-*", "LU-M013-*", "ED-M013-*", "AC-M013-*"],
            "implemented_s02_option": "safe_namespace_extension",
        },
        "fixture_boundaries": {
            "proof_only": True,
            "real_artifact_derived": True,
            "source_text_persisted": False,
            "excerpt_hashes_only": True,
            "falkordb_runtime_executed": False,
            "embedding_quality_measured": False,
        },
        "non_claims": NON_CLAIMS,
        "source_summary": {
            "source_path": source_path,
            "source_sha256": source_sha256,
            "hierarchy_record_count": len(hierarchy_records),
            "staging_graph_status": staging_graph["graph_status"],
            "staging_graph_diagnostic_count": staging_graph["diagnostic_count"],
        },
        "derived_fixture_graph": {
            "legal_acts": [
                {
                    "legal_act_id": "LA-M013-44FZ",
                    "source_record_id": document_record["id"],
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "status": "bounded_proxy",
                }
            ],
            "act_editions": [
                {
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "legal_act_id": "LA-M013-44FZ",
                    "valid_from": AS_OF_DATE,
                    "valid_to": None,
                    "status": "active",
                    "proof_boundary": "bounded_source_snapshot_proxy",
                    "source_sha256": source_sha256,
                }
            ],
            "legal_units": [
                {
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "source_hierarchy_id": article_record["id"],
                    "level": article_record["level"],
                    "parent_id": article_record["parent_id"],
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "legal_act_id": "LA-M013-44FZ",
                    "status": "bounded_hierarchy_proxy",
                }
            ],
            "source_documents": [
                {
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "source_corpus_id": SOURCE_CORPUS_ID,
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "source_record_id": document_record["id"],
                    "status": "active",
                }
            ],
            "source_blocks": [
                {
                    "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "source_hierarchy_id": article_record["id"],
                    "location": article_record["location"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "active",
                }
            ],
            "evidence_spans": [
                {
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "source_hierarchy_id": article_record["id"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "active",
                },
                {
                    "evidence_span_id": "EV-M013-ORPHAN-SOURCE",
                    "source_block_id": "SB-M013-MISSING-SOURCE-BLOCK",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "source_hierarchy_id": article_record["id"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "orphan_fixture",
                },
            ],
            "citation_bindings": [
                {
                    "citation_key": "CIT-M013-HIER-CONS-ARTICLE-0001",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "unique",
                },
                {
                    "citation_key": "CIT-M013-AMBIG",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "ambiguous",
                },
                {
                    "citation_key": "CIT-M013-AMBIG",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "ambiguous",
                },
            ],
        },
        "cases": cases,
        "expected_diagnostics": expected_diagnostics,
    }


def render_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build M013 real-artifact retrieval case corpus.")
    parser.add_argument("--check", action="store_true", help="Check generated corpus freshness instead of writing it.")
    args = parser.parse_args(argv)

    payload = build_payload()
    rendered = render_payload(payload)
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        status = "pass" if current == rendered else "fail"
        print(json.dumps({"status": status, "artifact": relative(OUTPUT_PATH), "case_count": len(payload["cases"]), "schema_version": SCHEMA_VERSION}, ensure_ascii=False, sort_keys=True))
        return 0 if status == "pass" else 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "written", "artifact": relative(OUTPUT_PATH), "case_count": len(payload["cases"]), "schema_version": SCHEMA_VERSION}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
