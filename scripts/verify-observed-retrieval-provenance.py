#!/usr/bin/env python3
"""Verify M023 observed-retrieval query/source provenance artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
QUERY_REGISTRY_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_query_provenance_registry.json"
SOURCE_MANIFEST_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_source_provenance_manifest.json"
QUERY_SCHEMA = "observed-retrieval-query-provenance-registry/v1"
SOURCE_SCHEMA = "observed-retrieval-source-provenance-manifest/v1"

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "query_text",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
    "generated_query",
    "generated_cypher",
    "legal_advice",
    "llm_reasoning",
}
FORBIDDEN_STRING_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)


class ProvenanceError(RuntimeError):
    """Raised when provenance verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProvenanceError(f"malformed JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProvenanceError(f"JSON root must be object: {path}")
    return payload


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_repo_path(value: str) -> Path:
    if value.startswith("/") or value.startswith(".gsd/exec"):
        raise ProvenanceError(f"unsafe path: {value}")
    path = ROOT / value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ProvenanceError(f"path outside repository: {value}") from exc
    return path


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise ProvenanceError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise ProvenanceError(f"unsafe payload fragment: {fragment}")


def source_index(path_value: str) -> dict[str, set[str] | bool]:
    data = load_json(resolve_repo_path(path_value))
    cases: set[str] = set()
    records: set[str] = set()
    for case in data.get("cases", []):
        if not isinstance(case, Mapping):
            continue
        case_id = case.get("case_id") or case.get("benchmark_case_id")
        if isinstance(case_id, str):
            cases.add(case_id)
        records.update(rid for rid in case.get("source_record_ids", []) if isinstance(rid, str))
    graph = data.get("derived_fixture_graph") if isinstance(data.get("derived_fixture_graph"), Mapping) else {}
    evidence_spans: set[str] = set()
    source_blocks: set[str] = set()
    citation_keys: set[str] = set()
    act_editions: set[str] = set()
    for key in ("source_blocks", "evidence_spans", "legal_units", "source_documents"):
        for row in graph.get(key, []):
            if not isinstance(row, Mapping):
                continue
            for field in ("source_hierarchy_id", "source_record_id"):
                if isinstance(row.get(field), str):
                    records.add(row[field])
    for row in graph.get("evidence_spans", []):
        if not isinstance(row, Mapping):
            continue
        if isinstance(row.get("evidence_span_id"), str):
            evidence_spans.add(row["evidence_span_id"])
        if isinstance(row.get("source_block_id"), str):
            source_blocks.add(row["source_block_id"])
        if isinstance(row.get("act_edition_id"), str):
            act_editions.add(row["act_edition_id"])
    for row in graph.get("source_blocks", []):
        if isinstance(row, Mapping) and isinstance(row.get("source_block_id"), str):
            source_blocks.add(row["source_block_id"])
    for row in graph.get("citation_bindings", []):
        if not isinstance(row, Mapping):
            continue
        if isinstance(row.get("citation_key"), str):
            citation_keys.add(row["citation_key"])
        if isinstance(row.get("evidence_span_id"), str):
            evidence_spans.add(row["evidence_span_id"])
    for row in graph.get("act_editions", []):
        if isinstance(row, Mapping) and isinstance(row.get("act_edition_id"), str):
            act_editions.add(row["act_edition_id"])
    return {
        "case_ids": cases,
        "source_record_ids": records,
        "evidence_span_ids": evidence_spans,
        "source_block_ids": source_blocks,
        "citation_keys": citation_keys,
        "act_edition_ids": act_editions,
        "graph_available": bool(graph),
    }


def fixture_cases(fixture: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise ProvenanceError("fixture cases must be list")
    return [case for case in cases if isinstance(case, Mapping)]


def verify_query_registry(fixture: Mapping[str, Any], registry: Mapping[str, Any]) -> list[str]:
    if registry.get("schema_version") != QUERY_SCHEMA:
        raise ProvenanceError("query registry schema mismatch")
    assert_safe_payload(registry)
    source_fixture = str(registry.get("source_fixture", ""))
    if sha256_path(resolve_repo_path(source_fixture)) != registry.get("source_fixture_sha256"):
        raise ProvenanceError("query registry source_fixture sha256 mismatch")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ProvenanceError("query registry entries must be list")
    case_to_entry = {entry.get("case_id"): entry for entry in entries if isinstance(entry, Mapping)}
    query_hashes: set[str] = set()
    diagnostics = ["query_registry_verified"]
    for case in fixture_cases(fixture):
        query = case.get("query")
        if not isinstance(query, Mapping):
            raise ProvenanceError(f"missing query: {case.get('case_id')}")
        entry = case_to_entry.get(case.get("case_id"))
        if not isinstance(entry, Mapping):
            raise ProvenanceError(f"query_hash_unregistered: {case.get('case_id')}")
        if entry.get("query_id") != query.get("query_id"):
            raise ProvenanceError(f"query_id mismatch: {case.get('case_id')}")
        if entry.get("query_hash") != query.get("query_text_sha256"):
            raise ProvenanceError(f"query_hash_unregistered: {case.get('case_id')}")
        query_hash = entry.get("query_hash")
        if not isinstance(query_hash, str) or len(query_hash) != 64:
            raise ProvenanceError(f"malformed query hash: {case.get('case_id')}")
        if query_hash in query_hashes:
            raise ProvenanceError(f"duplicate query hash: {case.get('case_id')}")
        query_hashes.add(query_hash)
        if entry.get("query_hash_field") != "query_text_sha256":
            raise ProvenanceError(f"query hash field mismatch: {case.get('case_id')}")
    if registry.get("entry_count") != len(entries) or len(entries) != len(fixture_cases(fixture)):
        raise ProvenanceError("query registry count mismatch")
    return diagnostics


def candidate_lookup(fixture: Mapping[str, Any]) -> dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]]:
    lookup: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for case in fixture_cases(fixture):
        for candidate in case.get("candidates", []):
            if isinstance(candidate, Mapping):
                candidate_id = candidate.get("candidate_id")
                if not isinstance(candidate_id, str):
                    raise ProvenanceError("candidate missing candidate_id")
                lookup[candidate_id] = (case, candidate)
    return lookup


def require_source_membership(candidate_id: str, field: str, value: str, index: Mapping[str, set[str] | bool], key: str) -> None:
    values = index.get(key)
    if isinstance(values, set) and value not in values:
        raise ProvenanceError(f"{field} missing for {candidate_id}: {value}")


def verify_source_manifest(fixture: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[str]:
    if manifest.get("schema_version") != SOURCE_SCHEMA:
        raise ProvenanceError("source manifest schema mismatch")
    assert_safe_payload(manifest)
    source_fixture = str(manifest.get("source_fixture", ""))
    if sha256_path(resolve_repo_path(source_fixture)) != manifest.get("source_fixture_sha256"):
        raise ProvenanceError("source manifest source_fixture sha256 mismatch")
    artifacts = manifest.get("source_artifacts")
    if not isinstance(artifacts, list):
        raise ProvenanceError("source_artifacts must be list")
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ProvenanceError("source artifact must be object")
        path = str(artifact.get("path", ""))
        if sha256_path(resolve_repo_path(path)) != artifact.get("sha256"):
            raise ProvenanceError(f"source artifact sha256 mismatch: {path}")
    entries = manifest.get("candidate_entries")
    if not isinstance(entries, list):
        raise ProvenanceError("candidate_entries must be list")
    lookup = candidate_lookup(fixture)
    if manifest.get("candidate_count") != len(entries) or len(entries) != len(lookup):
        raise ProvenanceError("candidate count mismatch")
    indexes: dict[str, dict[str, set[str] | bool]] = {}
    diagnostics = ["source_provenance_verified"]
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ProvenanceError("candidate entry must be object")
        candidate_id = str(entry.get("candidate_id", ""))
        if candidate_id not in lookup:
            raise ProvenanceError(f"candidate entry not in fixture: {candidate_id}")
        _case, candidate = lookup[candidate_id]
        for field in ("source_artifact", "source_case_id", "evidence_span_id", "source_block_id", "citation_key", "act_edition_id"):
            if entry.get(field) != candidate.get(field):
                raise ProvenanceError(f"candidate provenance field mismatch: {candidate_id}: {field}")
        if entry.get("source_record_ids") != candidate.get("source_record_ids"):
            raise ProvenanceError(f"source_record_ids mismatch: {candidate_id}")
        source_artifact = str(entry["source_artifact"])
        if source_artifact not in indexes:
            indexes[source_artifact] = source_index(source_artifact)
        index = indexes[source_artifact]
        require_source_membership(candidate_id, "source_case_id", str(entry["source_case_id"]), index, "case_ids")
        for source_record_id in entry.get("source_record_ids", []):
            require_source_membership(candidate_id, "source_record_id", str(source_record_id), index, "source_record_ids")
        expected_label = entry.get("expected_label")
        if expected_label in {"relevant", "distractor", "unsafe"}:
            require_source_membership(candidate_id, "evidence_span_id", str(entry["evidence_span_id"]), index, "evidence_span_ids")
            require_source_membership(candidate_id, "source_block_id", str(entry["source_block_id"]), index, "source_block_ids")
            require_source_membership(candidate_id, "citation_key", str(entry["citation_key"]), index, "citation_keys")
            require_source_membership(candidate_id, "act_edition_id", str(entry["act_edition_id"]), index, "act_edition_ids")
        expectations = entry.get("validation_expectations")
        if not isinstance(expectations, Mapping) or expectations.get("source_case_exists") is not True or expectations.get("source_records_exist") is not True:
            raise ProvenanceError(f"source expectation mismatch: {candidate_id}")
    return diagnostics


def verify(fixture_path: Path, query_registry_path: Path, source_manifest_path: Path) -> dict[str, Any]:
    fixture = load_json(fixture_path)
    query_registry = load_json(query_registry_path)
    source_manifest = load_json(source_manifest_path)
    diagnostics = sorted(set(verify_query_registry(fixture, query_registry) + verify_source_manifest(fixture, source_manifest)))
    return {
        "status": "ok",
        "schema_version": "observed-retrieval-provenance-verification/v1",
        "query_count": query_registry["entry_count"],
        "candidate_count": source_manifest["candidate_count"],
        "diagnostic_codes": diagnostics,
        "non_authoritative": True,
        "non_claim_boundary": "Provenance verification only; does not prove observed retrieval ranking or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--query-registry", type=Path, default=QUERY_REGISTRY_PATH)
    parser.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST_PATH)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify(args.fixture, args.query_registry, args.source_manifest)
    except ProvenanceError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
