#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
OFFLINE_CASES_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
REAL_CASES_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
CONTRACT_PATH = ROOT / "prd/research/ontology_architecture_requirements/09-ontology-graphrag-fixture-contract.md"
OUTPUT_PATH = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"

SCHEMA_VERSION = "ontology-graphrag-proof-cases/v1"
PROOF_ID = "OG-M020-S02-FIXTURE-PROOF"
GENERATED_BY = "scripts/build-ontology-graphrag-proof-cases.py"
FIXTURE_ARTIFACT = "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
CORE_VALUE = "DATA-LEGAL-EVIDENCE-CORE"
GATE_VALUE = "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"
CURRENT_VALUE = "current_version"
UNSUPPORTED_VALUE = "UNSUPPORTED-ONTOLOGY-GATE"
AS_OF_DATE = "2026-01-01"

NON_CLAIMS = [
    "Does not validate R035.",
    "Does not satisfy GATE-ONTOLOGY-GRAPHRAG-INTEGRATION.",
    "Does not prove product retrieval quality.",
    "Does not prove legal-answer correctness.",
    "Does not prove parser completeness.",
    "Does not prove FalkorDB production behavior.",
    "Does not prove graph-vector, HNSW, or hybrid retrieval behavior.",
    "Does not prove generated-Cypher safety.",
    "Does not prove BFO, GOST, OWL, Common Logic, LKIF, RusLegalCore, Akoma Ntoso, LegalDocML, or FRBR conformance.",
    "Does not prove 1000-document or pilot-scale readiness.",
    "Does not make LLM output legal authority.",
]

FORBIDDEN_PAYLOAD_CLASSES = [
    "raw legal text",
    "raw query text",
    "raw prompts",
    "generated legal advice",
    "raw vectors",
    "provider payloads",
    "raw FalkorDB rows",
    "secrets",
    "absolute local paths",
    ".gsd/exec proof paths",
]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        data = json.load(fixture_file)
    if not isinstance(data, dict):
        raise ValueError(f"{relative(path)} root must be an object")
    return data


def offline_case_by_id(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in data.get("cases", []):
        if isinstance(case, dict) and case.get("case_id") == case_id:
            return case
    raise ValueError(f"source case not found: {case_id}")


def base_query(*, query_id: str, kind: str, scope_id: str, target_record_id: str | None = "HIER-CONS-ARTICLE-0001", target_level: str | None = "article") -> dict[str, Any]:
    query: dict[str, Any] = {
        "query_id": query_id,
        "query_kind": kind,
        "scope_id": scope_id,
    }
    if target_record_id is not None:
        query["target_record_id"] = target_record_id
    if target_level is not None:
        query["target_level"] = target_level
    return query


def ontology_filter(*, filter_id: str, kind: str, requested_value: str, expected: str, allowed_values: list[str] | None = None) -> dict[str, Any]:
    return {
        "filter_id": filter_id,
        "filter_kind": kind,
        "allowed_values": allowed_values or [CORE_VALUE, GATE_VALUE, CURRENT_VALUE],
        "requested_value": requested_value,
        "expected_filter_result": expected,
    }


def temporal_filter(*, expected: str, mode: str = "current_only", edition_id: str | None = "ED-M014-44FZ-2026-01-01") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "as_of_date": AS_OF_DATE,
        "mode": mode,
        "expected_temporal_result": expected,
    }
    if edition_id is not None:
        payload["evidence_edition_id"] = edition_id
    return payload


def candidate(
    *,
    candidate_id: str,
    source_record_id: str | None,
    citation_key: str | None,
    evidence_span_id: str | None,
    act_edition_id: str | None,
    ontology_values: list[str],
    selection_reason: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "ontology_values": ontology_values,
        "selection_reason": selection_reason,
    }
    if source_record_id is not None:
        payload["source_record_id"] = source_record_id
    if citation_key is not None:
        payload["citation_key"] = citation_key
    if evidence_span_id is not None:
        payload["evidence_span_id"] = evidence_span_id
    if act_edition_id is not None:
        payload["act_edition_id"] = act_edition_id
    return payload


def output_with_wrong_edition(output: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(output)
    copied["citations"][0]["act_edition_id"] = "ED-M014-44FZ-1900-01-01"
    return copied


def output_without_evidence_id(output: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(output)
    copied["citations"][0].pop("evidence_span_id", None)
    return copied


def case(
    *,
    case_id: str,
    case_class: str,
    source_case_ids: list[str],
    query: dict[str, Any],
    ontology_filter_payload: dict[str, Any],
    temporal_filter_payload: dict[str, Any],
    candidate_set: list[dict[str, Any]],
    expected_result: str,
    expected_diagnostic_codes: list[str],
    output: dict[str, Any] | None = None,
    safety_probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "case_id": case_id,
        "case_class": case_class,
        "source_case_ids": source_case_ids,
        "query": query,
        "ontology_filter": ontology_filter_payload,
        "temporal_filter": temporal_filter_payload,
        "candidate_set": candidate_set,
        "expected_result": expected_result,
        "expected_diagnostic_codes": expected_diagnostic_codes,
        "non_authoritative": True,
    }
    if output is not None:
        payload["output"] = output
    if safety_probe is not None:
        payload["safety_probe"] = safety_probe
    return payload


def build_payload() -> dict[str, Any]:
    offline = load_json(OFFLINE_CASES_PATH)
    real = load_json(REAL_CASES_PATH)
    valid_offline = offline_case_by_id(offline, "CASE-M014-VALID-EXACT-RECORD-CANDIDATE")
    scoped_no_answer = offline_case_by_id(offline, "CASE-M014-SCOPED-NO-CANDIDATE")
    valid_output = deepcopy(valid_offline["output"])
    scope_id = valid_output["scope"]["scope_id"]

    valid_candidate = candidate(
        candidate_id="CAND-M020-OG-VALID-CURRENT-001",
        source_record_id="HIER-CONS-ARTICLE-0001",
        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
        act_edition_id="ED-M014-44FZ-2026-01-01",
        ontology_values=[CORE_VALUE, GATE_VALUE, CURRENT_VALUE],
        selection_reason="ontology_and_temporal_match",
    )

    inactive_candidate = candidate(
        candidate_id="CAND-M020-OG-INACTIVE-001",
        source_record_id="HIER-CONS-ARTICLE-0001",
        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
        act_edition_id="ED-M014-44FZ-1900-01-01",
        ontology_values=[CORE_VALUE, GATE_VALUE],
        selection_reason="inactive_version_excluded",
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "proof_id": PROOF_ID,
        "generated_by": GENERATED_BY,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "requirement": "R035",
        "gate": "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
        "non_authoritative": True,
        "source_inputs": [
            relative(CONTRACT_PATH),
            relative(OFFLINE_CASES_PATH),
            relative(REAL_CASES_PATH),
            "scripts/retrieval_output_validator.py",
        ],
        "validator_fixture_graph": deepcopy(offline["derived_fixture_graph"]),
        "redaction": {
            "forbidden_payload_classes_absent": True,
            "forbidden_payload_classes": FORBIDDEN_PAYLOAD_CLASSES,
            "safe_summary_only": True,
        },
        "non_claims": NON_CLAIMS,
        "source_summary": {
            "offline_case_count": len(offline.get("cases", [])),
            "real_artifact_case_count": len(real.get("cases", [])),
            "source_backed_evidence_span_ids": ["EV-M014-HIER-CONS-ARTICLE-0001"],
        },
        "cases": [
            case(
                case_id="CASE-M020-OG-VALID-ONTOLOGY-TEMPORAL-CITATION",
                case_class="valid_ontology_temporal_citation",
                source_case_ids=["CASE-M014-VALID-EXACT-RECORD-CANDIDATE"],
                query=base_query(query_id="QUERY-M020-OG-VALID-001", kind="ontology_filter_lookup", scope_id=scope_id),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-LEGAL-EVIDENCE-CORE", kind="legal_evidence_core", requested_value=CORE_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="included"),
                candidate_set=[valid_candidate],
                output=valid_output,
                expected_result="accepted",
                expected_diagnostic_codes=["ontology_filter_matched"],
            ),
            case(
                case_id="CASE-M020-OG-INACTIVE-OR-WRONG-EDITION-EXCLUDED",
                case_class="inactive_or_wrong_edition_excluded",
                source_case_ids=["CASE-M013-WRONG-EDITION-PROXY", "CASE-M014-VALID-EXACT-RECORD-CANDIDATE"],
                query=base_query(query_id="QUERY-M020-OG-TEMPORAL-001", kind="current_status_lookup", scope_id=scope_id),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-CURRENT-VERSION", kind="temporal_status", requested_value=CURRENT_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="wrong_edition", edition_id="ED-M014-44FZ-2026-01-01"),
                candidate_set=[inactive_candidate],
                output=output_with_wrong_edition(valid_output),
                expected_result="rejected",
                expected_diagnostic_codes=["temporal_filter_excluded", "wrong_edition"],
            ),
            case(
                case_id="CASE-M020-OG-UNSUPPORTED-ONTOLOGY-FILTER",
                case_class="unsupported_ontology_filter",
                source_case_ids=[],
                query=base_query(query_id="QUERY-M020-OG-UNSUPPORTED-001", kind="negative_guardrail", scope_id=scope_id, target_record_id=None, target_level=None),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-UNSUPPORTED-GATE", kind="unsupported_gate", requested_value=UNSUPPORTED_VALUE, expected="unsupported", allowed_values=[CORE_VALUE, GATE_VALUE]),
                temporal_filter_payload=temporal_filter(expected="not_applicable", mode="not_applicable", edition_id=None),
                candidate_set=[],
                expected_result="blocked_unsupported_filter",
                expected_diagnostic_codes=["unsupported_ontology_filter"],
            ),
            case(
                case_id="CASE-M020-OG-MISSING-CITATION-OR-EVIDENCE-ID",
                case_class="missing_citation_or_evidence_id",
                source_case_ids=["CASE-M013-MISSING-EVIDENCE-ID", "CASE-M014-VALID-EXACT-RECORD-CANDIDATE"],
                query=base_query(query_id="QUERY-M020-OG-MISSING-EVIDENCE-001", kind="ontology_filter_lookup", scope_id=scope_id),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-MISSING-EVIDENCE", kind="legal_evidence_core", requested_value=CORE_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="included"),
                candidate_set=[valid_candidate],
                output=output_without_evidence_id(valid_output),
                expected_result="rejected",
                expected_diagnostic_codes=["missing_required_field"],
            ),
            case(
                case_id="CASE-M020-OG-AMBIGUOUS-CANDIDATE-SET",
                case_class="ambiguous_candidate_set",
                source_case_ids=["CASE-M014-AMBIGUOUS-CANDIDATES"],
                query=base_query(query_id="QUERY-M020-OG-AMBIGUOUS-001", kind="ontology_filter_lookup", scope_id=scope_id),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-AMBIGUOUS", kind="legal_evidence_core", requested_value=CORE_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="included"),
                candidate_set=[
                    valid_candidate,
                    {**valid_candidate, "candidate_id": "CAND-M020-OG-AMBIGUOUS-002", "selection_reason": "ontology_and_temporal_match"},
                ],
                expected_result="rejected",
                expected_diagnostic_codes=["ambiguous_candidate_set"],
            ),
            case(
                case_id="CASE-M020-OG-SCOPED-NO-ANSWER",
                case_class="scoped_no_answer",
                source_case_ids=["CASE-M014-SCOPED-NO-CANDIDATE"],
                query=base_query(query_id="QUERY-M020-OG-SCOPED-NO-ANSWER-001", kind="scoped_no_answer", scope_id=scope_id, target_record_id="HIER-CONS-NOT-PRESENT", target_level="article"),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-SCOPED-NO-ANSWER", kind="legal_evidence_core", requested_value=CORE_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="not_applicable", mode="not_applicable", edition_id=None),
                candidate_set=[],
                output=deepcopy(scoped_no_answer["output"]),
                expected_result="accepted_scoped_no_answer",
                expected_diagnostic_codes=["scoped_no_answer"],
            ),
            case(
                case_id="CASE-M020-OG-FORBIDDEN-PAYLOAD-FIELD",
                case_class="forbidden_payload_field",
                source_case_ids=[],
                query=base_query(query_id="QUERY-M020-OG-FORBIDDEN-PAYLOAD-001", kind="negative_guardrail", scope_id=scope_id, target_record_id=None, target_level=None),
                ontology_filter_payload=ontology_filter(filter_id="OF-M020-FORBIDDEN-PAYLOAD", kind="legal_evidence_core", requested_value=CORE_VALUE, expected="matched"),
                temporal_filter_payload=temporal_filter(expected="not_applicable", mode="not_applicable", edition_id=None),
                candidate_set=[],
                safety_probe={"field_path": "output.disallowed_payload", "payload_class": "unsafe_external_payload"},
                expected_result="rejected",
                expected_diagnostic_codes=["forbidden_payload_field"],
            ),
        ],
    }


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the M020 S02 ontology GraphRAG proof fixture.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output fixture path.")
    parser.add_argument("--check", action="store_true", help="Check that the output fixture is current without writing it.")
    args = parser.parse_args(argv)

    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = build_payload()
    rendered = canonical_json(payload)

    if args.check:
        existing = output.read_text(encoding="utf-8") if output.exists() else None
        status = "ok" if existing == rendered else "drift"
        summary = {
            "schema_version": "ontology-graphrag-proof-builder/v1",
            "fixture_path": relative(output),
            "status": status,
            "case_count": len(payload["cases"]),
            "non_authoritative": payload["non_authoritative"],
        }
        json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 0 if status == "ok" else 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    summary = {
        "schema_version": "ontology-graphrag-proof-builder/v1",
        "fixture_path": relative(output),
        "status": "written",
        "case_count": len(payload["cases"]),
        "non_authoritative": payload["non_authoritative"],
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
