#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/representative_retrieval_corpus_contract.md"
LOCAL_BENCHMARK_PATH = ROOT / "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
OFFLINE_CASES_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
REAL_ARTIFACT_CASES_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
SOURCE_FIXTURE_INVENTORY_PATH = ROOT / "prd/parser/source_fixture_inventory.json"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
REPORT_PATH = ROOT / "prd/retrieval/representative_retrieval_corpus_manifest.md"

SCHEMA_VERSION = "representative-retrieval-corpus/v1"
CORPUS_ID = "CORPUS-M016-REPRESENTATIVE-V1"
GENERATED_BY = "scripts/build_representative_retrieval_corpus_manifest.py"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
REPORT_ARTIFACT = "prd/retrieval/representative_retrieval_corpus_manifest.md"
GATE = "GATE-G011"
REQUIREMENT = "R034"

REQUIRED_SOURCE_PATHS = [
    CONTRACT_PATH,
    LOCAL_BENCHMARK_PATH,
    OFFLINE_CASES_PATH,
    REAL_ARTIFACT_CASES_PATH,
    SOURCE_FIXTURE_INVENTORY_PATH,
]

REDACTION_FLAGS = {
    "raw_legal_text_persisted": False,
    "raw_query_text_persisted": False,
    "raw_prompt_persisted": False,
    "raw_vector_persisted": False,
    "provider_payload_persisted": False,
    "raw_falkordb_row_persisted": False,
    "generated_legal_advice_persisted": False,
    "absolute_path_persisted": False,
}

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text": "unsafe_payload_field",
    "raw_text": "unsafe_payload_field",
    "source_excerpt": "unsafe_payload_field",
    "source_excerpts": "unsafe_payload_field",
    "query_text": "unsafe_payload_field",
    "raw_query_text": "unsafe_payload_field",
    "prompt": "unsafe_payload_field",
    "user_prompt": "unsafe_payload_field",
    "provider_payload": "managed_api_forbidden",
    "provider_response_body": "managed_api_forbidden",
    "managed_api_payload": "managed_api_forbidden",
    "secret": "unsafe_payload_field",
    "secrets": "unsafe_payload_field",
    "token": "unsafe_payload_field",
    "password": "unsafe_payload_field",
    "vector": "raw_vector_forbidden",
    "vectors": "raw_vector_forbidden",
    "embedding": "raw_vector_forbidden",
    "embedding_vector": "raw_vector_forbidden",
    "raw_falkordb_row": "raw_falkordb_row_forbidden",
    "falkordb_row": "raw_falkordb_row_forbidden",
    "runtime_row": "raw_falkordb_row_forbidden",
    "generated_answer_prose": "gate_overclaim_forbidden",
    "legal_advice": "gate_overclaim_forbidden",
}

FORBIDDEN_STRING_PATTERNS = [
    (re.compile(r"/(?:root|home|Users)/"), "absolute_path_persisted"),
    (re.compile(r"\.gsd/exec"), "unsafe_payload_field"),
    (re.compile(r"\.planning/"), "unsafe_payload_field"),
    (re.compile(r"\.audits/"), "unsafe_payload_field"),
    (re.compile(r"GATE-G011 is closed", re.IGNORECASE), "gate_overclaim_forbidden"),
    (re.compile(r"managed (?:giga)?chat api fallback is allowed", re.IGNORECASE), "managed_api_forbidden"),
    (re.compile(r"managed embedding api fallback is allowed", re.IGNORECASE), "managed_api_forbidden"),
]

REQUIRED_COVERAGE = [
    ("COV-M016-001", "source_family_consultant_wordml"),
    ("COV-M016-002", "source_family_garant_odt_metadata"),
    ("COV-M016-003", "legal_unit_path_coverage"),
    ("COV-M016-004", "positive_retrieval"),
    ("COV-M016-005", "distractor_retrieval"),
    ("COV-M016-006", "scoped_no_answer"),
    ("COV-M016-007", "ambiguous_rejection"),
    ("COV-M016-008", "unsafe_rejection"),
    ("COV-M016-009", "edition_path_mismatch"),
    ("COV-M016-010", "environment_runtime_handoff_boundary"),
]

DIAGNOSTIC_CODE_INVENTORY = [
    "missing_source_artifact",
    "manifest_schema_mismatch",
    "unsafe_payload_field",
    "coverage_class_missing",
    "source_family_missing",
    "query_label_mismatch",
    "candidate_reference_mismatch",
    "edition_path_mismatch",
    "managed_api_forbidden",
    "raw_vector_forbidden",
    "raw_falkordb_row_forbidden",
    "gate_overclaim_forbidden",
]

NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not compute runtime benchmark metrics",
    "does not allow managed GigaChat API fallback",
    "does not allow managed embedding API fallback",
    "does not persist raw legal text, raw query prompts, vectors, provider payloads, raw FalkorDB rows, or generated legal advice",
    "does not close GATE-G011",
    "does not close GATE-G008",
    "does not make LLM output legal authority",
    "does not make proof-local IDs production IDs",
]


class ManifestError(RuntimeError):
    def __init__(self, diagnostic: dict[str, str]) -> None:
        super().__init__(diagnostic["code"])
        self.diagnostic = diagnostic


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(
            diagnostic(
                "manifest_schema_mismatch",
                severity="error",
                artifact_path=relative(path),
                field_path=f"json:{exc.lineno}:{exc.colno}",
            )
        ) from exc


def diagnostic(code: str, *, severity: str, artifact_path: str, field_path: str | None = None, **ids: str) -> dict[str, str]:
    payload = {"code": code, "severity": severity, "artifact_path": artifact_path}
    if field_path:
        payload["field_path"] = field_path
    for key, value in ids.items():
        if value:
            payload[key] = value
    return payload


def require_source_paths() -> None:
    for path in REQUIRED_SOURCE_PATHS:
        if not path.exists():
            raise ManifestError(diagnostic("missing_source_artifact", severity="error", artifact_path=relative(path)))
        if not relative(path).startswith("prd/"):
            raise ManifestError(diagnostic("manifest_schema_mismatch", severity="error", artifact_path=relative(path), field_path="source_artifacts"))


def source_artifacts() -> list[dict[str, str]]:
    return [
        {"path": relative(path), "sha256": sha256_path(path)}
        for path in sorted(REQUIRED_SOURCE_PATHS, key=relative)
    ]


def index_cases(cases: Iterable[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {case[key]: case for case in cases}


def first_fixture_by_kind(inventory: dict[str, Any], source_kind: str) -> dict[str, Any]:
    for fixture in inventory["fixtures"]:
        if fixture.get("source_kind") == source_kind and fixture.get("canonical") is True:
            return fixture
    raise ManifestError(
        diagnostic("source_family_missing", severity="error", artifact_path=relative(SOURCE_FIXTURE_INVENTORY_PATH), field_path=f"fixtures[{source_kind}]")
    )


def coverage_classes() -> list[dict[str, Any]]:
    descriptions = {
        "source_family_consultant_wordml": "Consultant WordML/XML-derived parser and retrieval proof artifacts represented by IDs, selectors, and hashes only.",
        "source_family_garant_odt_metadata": "Garant ODT source fixture metadata represented by repository-relative inventory path, source hash, and ODT shape metadata only.",
        "legal_unit_path_coverage": "Source document, source block, evidence span, legal unit, act edition, and legal act path IDs are represented where available.",
        "positive_retrieval": "At least one bounded query label expects relevant references.",
        "distractor_retrieval": "At least one bounded query label includes a distractor reference that must not outrank relevant evidence.",
        "scoped_no_answer": "At least one bounded query label expects no answer inside an explicit proof scope.",
        "ambiguous_rejection": "At least one bounded query label is intentionally ambiguous and must fail closed.",
        "unsafe_rejection": "At least one bounded query label represents forbidden payload shape by labels only and must be rejected.",
        "edition_path_mismatch": "At least one bounded query label exercises wrong-edition or path mismatch rejection.",
        "environment_runtime_handoff_boundary": "S03 gets local/open-weight runtime boundary metadata without managed API or production-readiness assumptions.",
    }
    return [
        {"coverage_class_id": cov_id, "class_name": class_name, "description": descriptions[class_name], "proof_boundary": "redacted_static_manifest"}
        for cov_id, class_name in REQUIRED_COVERAGE
    ]


def redaction() -> dict[str, bool]:
    return dict(REDACTION_FLAGS)


def evidence_path_ids_from_real_case(case: dict[str, Any]) -> dict[str, str]:
    citations = case.get("output", {}).get("citations") or []
    citation = citations[0] if citations else {}
    return {
        key: citation[key]
        for key in ["source_document_id", "source_block_id", "evidence_span_id", "legal_unit_id", "act_edition_id", "citation_key"]
        if key in citation
    }


def candidate_references(real: dict[str, Any], offline: dict[str, Any], inventory: dict[str, Any]) -> list[dict[str, Any]]:
    real_cases = index_cases(real["cases"], "case_id")
    offline_cases = index_cases(offline["cases"], "case_id")
    consultant_source = next(item for item in real["source_artifacts"] if item["path"] == "prd/parser/consultant_hierarchy_records.json")
    offline_source = next(item for item in offline["source_artifacts"] if item["path"] == "prd/retrieval/offline_citation_retrieval_contract.md")
    garant_fixture = first_fixture_by_kind(inventory, "garant-odt")
    inventory_sha = sha256_path(SOURCE_FIXTURE_INVENTORY_PATH)

    def real_ref(reference_id: str, case_id: str, role: str) -> dict[str, Any]:
        case = real_cases[case_id]
        return {
            "reference_id": reference_id,
            "source_family": "consultant_wordml",
            "source_artifact": real["fixture_artifact"],
            "source_sha256": sha256_path(REAL_ARTIFACT_CASES_PATH),
            "source_record_ids": case.get("source_record_ids", []),
            "evidence_path_ids": evidence_path_ids_from_real_case(case),
            "excerpt_sha256": sha256_text(f"{case_id}|{role}"),
            "reference_role": role,
            "provenance": {
                "source_fixture_path": real["fixture_artifact"],
                "source_case_id": case_id,
                "parser_source_artifact": consultant_source["path"],
                "parser_source_sha256": consultant_source["sha256"],
                "derivation": "bounded M013 retrieval validator case reference; no source excerpt persisted",
            },
            "redaction": redaction(),
        }

    def offline_ref(reference_id: str, case_id: str, role: str) -> dict[str, Any]:
        case = offline_cases[case_id]
        return {
            "reference_id": reference_id,
            "source_family": "consultant_wordml",
            "source_artifact": offline["fixture_artifact"],
            "source_sha256": sha256_path(OFFLINE_CASES_PATH),
            "source_record_ids": case.get("source_record_ids", []),
            "evidence_path_ids": evidence_path_ids_from_offline_case(case),
            "excerpt_sha256": sha256_text(f"{case_id}|{role}"),
            "reference_role": role,
            "provenance": {
                "source_fixture_path": offline["fixture_artifact"],
                "source_case_id": case_id,
                "source_contract": offline_source["path"],
                "source_contract_sha256": offline_source["sha256"],
                "derivation": "bounded M014 offline citation case reference; no query or answer text persisted",
            },
            "redaction": redaction(),
        }

    refs = [
        real_ref("RC-M016-001", "CASE-M013-VALID-REAL-ARTIFACT", "relevant"),
        real_ref("RC-M016-002", "CASE-M013-WRONG-EDITION-PROXY", "edition_mismatch"),
        real_ref("RC-M016-003", "CASE-M013-SCOPED-NO-ANSWER", "no_answer_boundary"),
        real_ref("RC-M016-004", "CASE-M013-AMBIGUOUS-CITATION", "ambiguous"),
        real_ref("RC-M016-005", "CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION", "unsafe"),
        offline_ref("RC-M016-006", "CASE-M014-VALID-MARKER-LEVEL-CANDIDATE", "distractor"),
        {
            "reference_id": "RC-M016-007",
            "source_family": "garant_odt_metadata",
            "source_artifact": relative(SOURCE_FIXTURE_INVENTORY_PATH),
            "source_sha256": inventory_sha,
            "source_record_ids": [garant_fixture["path"]],
            "evidence_path_ids": {
                "source_fixture_path": garant_fixture["path"],
                "source_kind": garant_fixture["source_kind"],
                "source_role": garant_fixture["source_role"],
            },
            "excerpt_sha256": garant_fixture["sha256"],
            "reference_role": "environment_boundary",
            "provenance": {
                "source_fixture_path": relative(SOURCE_FIXTURE_INVENTORY_PATH),
                "inventory_fixture_path": garant_fixture["path"],
                "inventory_fixture_sha256": garant_fixture["sha256"],
                "derivation": "Garant ODT metadata boundary only; no parsed-content or retrieval-quality claim",
            },
            "redaction": redaction(),
        },
    ]
    return sorted(refs, key=lambda item: item["reference_id"])


def evidence_path_ids_from_offline_case(case: dict[str, Any]) -> dict[str, str]:
    candidates = case.get("candidates") or []
    candidate = candidates[0] if candidates else {}
    return {key: candidate[key] for key in ["source_document_id", "source_block_id", "evidence_span_id", "legal_unit_id", "act_edition_id"] if key in candidate}


def query_label(query_label_id: str, class_ids: list[str], kind: str, expected_refs: list[str], expected_result: str, source_case_ids: list[str], *, as_of_date: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query_label_id": query_label_id,
        "coverage_class_ids": class_ids,
        "query_kind": kind,
        "query_label_sha256": sha256_text("|".join([query_label_id, kind, *source_case_ids])),
        "scope_id": "SCOPE-M016-REPRESENTATIVE-RETRIEVAL-CORPUS",
        "as_of_date": as_of_date,
        "expected_relevant_reference_ids": expected_refs,
        "expected_result": expected_result,
        "source_case_ids": source_case_ids,
        "redaction": redaction(),
    }
    return payload


def query_labels() -> list[dict[str, Any]]:
    labels = [
        query_label("QRL-M016-001", ["COV-M016-001", "COV-M016-003", "COV-M016-004"], "positive_retrieval", ["RC-M016-001"], "metrics_candidate", ["CASE-M013-VALID-REAL-ARTIFACT", "CASE-M015-POSITIVE-EXACT-RELEVANCE"], as_of_date="2026-01-01"),
        query_label("QRL-M016-002", ["COV-M016-001", "COV-M016-005"], "distractor_retrieval", ["RC-M016-001"], "metrics_candidate", ["CASE-M014-VALID-MARKER-LEVEL-CANDIDATE", "CASE-M015-POSITIVE-WITH-DISTRACTOR"], as_of_date="2026-01-01"),
        query_label("QRL-M016-003", ["COV-M016-001", "COV-M016-006"], "scoped_no_answer", [], "scoped_no_answer", ["CASE-M013-SCOPED-NO-ANSWER", "CASE-M014-SCOPED-NO-CANDIDATE", "CASE-M015-SCOPED-NO-ANSWER-QUALITY"]),
        query_label("QRL-M016-004", ["COV-M016-001", "COV-M016-007"], "ambiguous_rejection", [], "rejected", ["CASE-M013-AMBIGUOUS-CITATION", "CASE-M014-AMBIGUOUS-CANDIDATE-SET", "CASE-M015-AMBIGUOUS-RETRIEVAL-REJECTED"]),
        query_label("QRL-M016-005", ["COV-M016-001", "COV-M016-008"], "unsafe_rejection", [], "rejected", ["CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION", "CASE-M014-UNSAFE-CANDIDATE-PAYLOAD", "CASE-M015-UNSAFE-PAYLOAD-REJECTED"]),
        query_label("QRL-M016-006", ["COV-M016-001", "COV-M016-003", "COV-M016-009"], "edition_path_mismatch", [], "rejected", ["CASE-M013-WRONG-EDITION-PROXY"], as_of_date="1900-01-01"),
        query_label("QRL-M016-007", ["COV-M016-002", "COV-M016-010"], "environment_runtime_handoff_boundary", ["RC-M016-007"], "environment_boundary", ["prd/parser/source_fixture_inventory.json", "CASE-M015-ENVIRONMENT-BOUNDARY"]),
    ]
    return sorted(labels, key=lambda item: item["query_label_id"])


def build_payload() -> dict[str, Any]:
    require_source_paths()
    local_benchmark = load_json(LOCAL_BENCHMARK_PATH)
    offline = load_json(OFFLINE_CASES_PATH)
    real = load_json(REAL_ARTIFACT_CASES_PATH)
    inventory = load_json(SOURCE_FIXTURE_INVENTORY_PATH)
    coverage = coverage_classes()
    queries = query_labels()
    refs = candidate_references(real, offline, inventory)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "corpus_id": CORPUS_ID,
        "generated_by": GENERATED_BY,
        "created_by": GENERATED_BY,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "gate": GATE,
        "requirement": REQUIREMENT,
        "non_authoritative": True,
        "source_artifacts": source_artifacts(),
        "coverage_classes": coverage,
        "query_labels": queries,
        "candidate_references": refs,
        "redaction_boundaries": {
            **redaction(),
            "durable_payloads_allowed": ["stable IDs", "bounded enums", "repository-relative paths", "SHA-256 hashes", "counts", "diagnostic codes"],
        },
        "runtime_handoff": runtime_handoff(local_benchmark),
        "s03_handoff": runtime_handoff(local_benchmark),
        "diagnostics": [],
        "diagnostic_code_inventory": DIAGNOSTIC_CODE_INVENTORY,
        "non_claims": NON_CLAIMS,
        "explicit_limits": {
            "garant_odt_metadata_only": True,
            "garant_parsed_content_claimed": False,
            "garant_retrieval_quality_claimed": False,
            "consultant_real_artifact_evidence_bounded": True,
            "runtime_metrics_computed": False,
            "falkordb_runtime_executed": False,
            "managed_api_used": False,
        },
    }
    validate_payload(payload)
    return payload


def runtime_handoff(local_benchmark: dict[str, Any]) -> dict[str, Any]:
    model_boundary = local_benchmark.get("model_boundary", {})
    return {
        "manifest_path": FIXTURE_ARTIFACT,
        "builder_check_command": "uv run python scripts/build-representative-retrieval-corpus.py --check",
        "canonical_builder_check_command": "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check",
        "schema_version": SCHEMA_VERSION,
        "corpus_id": CORPUS_ID,
        "allowed_runtime_model_boundary": {
            "runtime_class": "local_open_weight_only",
            "expected_baseline_model_id": model_boundary.get("model_id", "deepvk/USER-bge-m3"),
            "quality_boundary": "S03 must produce runtime evidence; S02 only hands off redacted static labels and references.",
        },
        "managed_api_allowed": False,
        "managed_embedding_api_fallback_allowed": False,
        "raw_payload_persistence_allowed": False,
        "gate_g011_status": "open",
        "quality_claim_scope": "manifest-readiness only; not product retrieval quality",
    }


def walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def assert_unique(items: list[dict[str, Any]], id_key: str, code: str) -> None:
    seen: set[str] = set()
    for item in items:
        item_id = item[id_key]
        if item_id in seen:
            raise ManifestError(diagnostic(code, severity="error", artifact_path=FIXTURE_ARTIFACT, field_path=id_key, **{id_key: item_id}))
        seen.add(item_id)


def validate_payload(payload: dict[str, Any]) -> None:
    required_root = {"schema_version", "corpus_id", "generated_by", "fixture_artifact", "gate", "requirement", "source_artifacts", "coverage_classes", "query_labels", "candidate_references", "redaction_boundaries", "runtime_handoff", "non_claims"}
    missing = sorted(required_root - payload.keys())
    if missing:
        raise ManifestError(diagnostic("manifest_schema_mismatch", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path=".".join(missing), corpus_id=CORPUS_ID))

    coverage_names = {item["class_name"] for item in payload["coverage_classes"]}
    for _, class_name in REQUIRED_COVERAGE:
        if class_name not in coverage_names:
            raise ManifestError(diagnostic("coverage_class_missing", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path="coverage_classes", corpus_id=CORPUS_ID))

    assert_unique(payload["coverage_classes"], "coverage_class_id", "coverage_class_missing")
    assert_unique(payload["query_labels"], "query_label_id", "query_label_mismatch")
    assert_unique(payload["candidate_references"], "reference_id", "candidate_reference_mismatch")

    reference_ids = {item["reference_id"] for item in payload["candidate_references"]}
    coverage_ids = {item["coverage_class_id"] for item in payload["coverage_classes"]}
    for query_item in payload["query_labels"]:
        for coverage_id in query_item["coverage_class_ids"]:
            if coverage_id not in coverage_ids:
                raise ManifestError(diagnostic("coverage_class_missing", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path="query_labels.coverage_class_ids", query_label_id=query_item["query_label_id"], coverage_class_id=coverage_id))
        for reference_id in query_item["expected_relevant_reference_ids"]:
            if reference_id not in reference_ids:
                raise ManifestError(diagnostic("candidate_reference_mismatch", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path="query_labels.expected_relevant_reference_ids", query_label_id=query_item["query_label_id"], reference_id=reference_id))
        validate_redaction(query_item.get("redaction"), f"query_labels.{query_item['query_label_id']}.redaction")

    for reference in payload["candidate_references"]:
        validate_redaction(reference.get("redaction"), f"candidate_references.{reference['reference_id']}.redaction")
        source_artifact = reference["source_artifact"]
        source_path = ROOT / source_artifact
        if source_path.exists() and reference["source_sha256"] != sha256_path(source_path):
            raise ManifestError(diagnostic("candidate_reference_mismatch", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path="candidate_references.source_sha256", reference_id=reference["reference_id"]))

    for path, value in walk(payload):
        if path.split(".")[-1] in FORBIDDEN_FIELD_NAMES:
            raise ManifestError(diagnostic(FORBIDDEN_FIELD_NAMES[path.split(".")[-1]], severity="error", artifact_path=FIXTURE_ARTIFACT, field_path=path, corpus_id=CORPUS_ID))
        if isinstance(value, str):
            for pattern, code in FORBIDDEN_STRING_PATTERNS:
                if pattern.search(value):
                    raise ManifestError(diagnostic(code, severity="error", artifact_path=FIXTURE_ARTIFACT, field_path=path, corpus_id=CORPUS_ID))

    if payload["s03_handoff"]["managed_api_allowed"] is not False or payload["s03_handoff"]["gate_g011_status"] != "open":
        raise ManifestError(diagnostic("gate_overclaim_forbidden", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path="s03_handoff", corpus_id=CORPUS_ID))


def validate_redaction(value: Any, field_path: str) -> None:
    if value != REDACTION_FLAGS:
        raise ManifestError(diagnostic("unsafe_payload_field", severity="error", artifact_path=FIXTURE_ARTIFACT, field_path=field_path, corpus_id=CORPUS_ID))


def render_report(payload: dict[str, Any]) -> str:
    class_names = ", ".join(item["class_name"] for item in payload["coverage_classes"])
    return (
        "# Representative Retrieval Corpus Manifest\n\n"
        f"- Schema version: `{payload['schema_version']}`\n"
        f"- Corpus ID: `{payload['corpus_id']}`\n"
        f"- Manifest artifact: `{payload['fixture_artifact']}`\n"
        f"- Source artifact count: {len(payload['source_artifacts'])}\n"
        f"- Query label count: {len(payload['query_labels'])}\n"
        f"- Candidate reference count: {len(payload['candidate_references'])}\n"
        f"- Coverage class count: {len(payload['coverage_classes'])}\n"
        f"- Coverage classes: {class_names}\n"
        "- Boundary: redacted static manifest only; no raw legal text, raw prompts, vectors, provider payloads, raw FalkorDB rows, generated legal advice, or closed-gate claim.\n"
        "- Garant boundary: ODT fixture metadata only; no Garant parsed-content or retrieval-quality claim.\n"
    )


def success_json(payload: dict[str, Any], status: str) -> str:
    return json.dumps(
        {
            "status": status,
            "schema_version": payload["schema_version"],
            "corpus_id": payload["corpus_id"],
            "source_artifact_count": len(payload["source_artifacts"]),
            "query_label_count": len(payload["query_labels"]),
            "candidate_reference_count": len(payload["candidate_references"]),
            "coverage_class_count": len(payload["coverage_classes"]),
            "diagnostic_codes": payload["diagnostic_code_inventory"],
            "artifact": payload["fixture_artifact"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic M016 representative retrieval corpus manifest.")
    parser.add_argument("--check", action="store_true", help="Fail if checked-in manifest/report are stale.")
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        rendered = stable_json(payload)
        report = render_report(payload)
        if args.check:
            if not OUTPUT_PATH.exists():
                raise ManifestError(diagnostic("missing_source_artifact", severity="error", artifact_path=relative(OUTPUT_PATH)))
            if OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
                raise ManifestError(diagnostic("manifest_schema_mismatch", severity="error", artifact_path=relative(OUTPUT_PATH), field_path="manifest_bytes"))
            if not REPORT_PATH.exists() or REPORT_PATH.read_text(encoding="utf-8") != report:
                raise ManifestError(diagnostic("manifest_schema_mismatch", severity="error", artifact_path=relative(REPORT_PATH), field_path="report_bytes"))
            print(success_json(payload, "pass"))
            return 0

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(success_json(payload, "written"))
        return 0
    except ManifestError as exc:
        print(json.dumps({"status": "fail", "diagnostic": exc.diagnostic}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
