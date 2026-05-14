from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
REPORT_PATH = ROOT / "prd/retrieval/representative_retrieval_corpus_manifest.md"
BUILDER_PATH = ROOT / "scripts/build_representative_retrieval_corpus_manifest.py"
HYPHEN_BUILDER_PATH = ROOT / "scripts/build-representative-retrieval-corpus.py"

REQUIRED_COVERAGE_CLASSES = {
    "source_family_consultant_wordml",
    "source_family_garant_odt_metadata",
    "legal_unit_path_coverage",
    "positive_retrieval",
    "distractor_retrieval",
    "scoped_no_answer",
    "ambiguous_rejection",
    "unsafe_rejection",
    "edition_path_mismatch",
    "environment_runtime_handoff_boundary",
}

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
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "query_text",
    "raw_query_text",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "token",
    "password",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "raw_falkordb_row",
    "falkordb_row",
    "runtime_row",
    "generated_answer_prose",
    "legal_advice",
}

FORBIDDEN_STRING_TOKENS = [
    "/root/",
    "/home/",
    "/Users/",
    ".gsd/exec",
    ".planning/",
    ".audits/",
    "GATE-G011 is closed",
    "managed API fallback is allowed",
    "managed embedding API fallback is allowed",
]

REQUIRED_NON_CLAIMS = {
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
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location("representative_builder", BUILDER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def ids(items: list[dict[str, Any]], key: str) -> list[str]:
    return [item[key] for item in items]


def test_manifest_paths_exist_and_schema_root_is_stable() -> None:
    assert BUILDER_PATH.exists()
    assert HYPHEN_BUILDER_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert REPORT_PATH.exists()

    manifest = load_manifest()
    assert manifest["schema_version"] == "representative-retrieval-corpus/v1"
    assert manifest["corpus_id"] == "CORPUS-M016-REPRESENTATIVE-V1"
    assert manifest["generated_by"] == "scripts/build_representative_retrieval_corpus_manifest.py"
    assert manifest["fixture_artifact"] == "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
    assert manifest["gate"] == "GATE-G011"
    assert manifest["requirement"] == "R034"
    assert manifest["non_authoritative"] is True
    assert manifest["diagnostics"] == []


def test_source_artifact_hashes_match_tracked_inputs() -> None:
    manifest = load_manifest()
    actual = {item["path"]: item["sha256"] for item in manifest["source_artifacts"]}
    expected_paths = {
        "prd/retrieval/representative_retrieval_corpus_contract.md",
        "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
        "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
        "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
        "prd/parser/source_fixture_inventory.json",
    }
    assert set(actual) == expected_paths
    for artifact, digest in actual.items():
        assert digest == sha256_path(ROOT / artifact)


def test_required_coverage_classes_and_minimum_cases_are_present() -> None:
    manifest = load_manifest()
    coverage_names = {item["class_name"] for item in manifest["coverage_classes"]}
    assert REQUIRED_COVERAGE_CLASSES <= coverage_names
    assert len(manifest["coverage_classes"]) >= len(REQUIRED_COVERAGE_CLASSES)

    query_kinds = {item["query_kind"] for item in manifest["query_labels"]}
    assert {
        "positive_retrieval",
        "distractor_retrieval",
        "scoped_no_answer",
        "ambiguous_rejection",
        "unsafe_rejection",
        "edition_path_mismatch",
        "environment_runtime_handoff_boundary",
    } <= query_kinds

    source_families = {item["source_family"] for item in manifest["candidate_references"]}
    assert {"consultant_wordml", "garant_odt_metadata"} <= source_families
    garant_refs = [item for item in manifest["candidate_references"] if item["source_family"] == "garant_odt_metadata"]
    assert garant_refs
    assert all(item["reference_role"] == "environment_boundary" for item in garant_refs)
    assert manifest["explicit_limits"]["garant_odt_metadata_only"] is True
    assert manifest["explicit_limits"]["garant_parsed_content_claimed"] is False
    assert manifest["explicit_limits"]["garant_retrieval_quality_claimed"] is False


def test_unique_stable_ids_and_cross_references() -> None:
    manifest = load_manifest()
    coverage_ids = ids(manifest["coverage_classes"], "coverage_class_id")
    query_ids = ids(manifest["query_labels"], "query_label_id")
    reference_ids = ids(manifest["candidate_references"], "reference_id")

    assert coverage_ids == sorted(coverage_ids)
    assert query_ids == sorted(query_ids)
    assert reference_ids == sorted(reference_ids)
    assert len(coverage_ids) == len(set(coverage_ids))
    assert len(query_ids) == len(set(query_ids))
    assert len(reference_ids) == len(set(reference_ids))
    assert all(item.startswith("COV-M016-") for item in coverage_ids)
    assert all(item.startswith("QRL-M016-") for item in query_ids)
    assert all(item.startswith("RC-M016-") for item in reference_ids)

    coverage_set = set(coverage_ids)
    reference_set = set(reference_ids)
    for query in manifest["query_labels"]:
        assert set(query["coverage_class_ids"]) <= coverage_set
        assert set(query["expected_relevant_reference_ids"]) <= reference_set
        assert query["query_label_sha256"]
        assert "query_text" not in query


def test_redaction_shape_and_forbidden_payload_tokens_are_absent() -> None:
    manifest = load_manifest()
    for query in manifest["query_labels"]:
        assert query["redaction"] == REDACTION_FLAGS
    for reference in manifest["candidate_references"]:
        assert reference["redaction"] == REDACTION_FLAGS
    assert manifest["redaction_boundaries"] | REDACTION_FLAGS == manifest["redaction_boundaries"]

    for path, value in walk(manifest):
        field = path.split(".")[-1]
        assert field not in FORBIDDEN_FIELD_NAMES, path
        if isinstance(value, str):
            assert not any(token in value for token in FORBIDDEN_STRING_TOKENS), (path, value)


def test_non_claims_and_s03_handoff_are_explicitly_bounded() -> None:
    manifest = load_manifest()
    assert REQUIRED_NON_CLAIMS <= set(manifest["non_claims"])
    handoff = manifest["s03_handoff"]
    assert handoff == manifest["runtime_handoff"]
    assert handoff["manifest_path"] == "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
    assert handoff["builder_check_command"] == "uv run python scripts/build-representative-retrieval-corpus.py --check"
    assert handoff["canonical_builder_check_command"] == "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check"
    assert handoff["schema_version"] == manifest["schema_version"]
    assert handoff["corpus_id"] == manifest["corpus_id"]
    assert handoff["managed_api_allowed"] is False
    assert handoff["managed_embedding_api_fallback_allowed"] is False
    assert handoff["raw_payload_persistence_allowed"] is False
    assert handoff["gate_g011_status"] == "open"
    assert handoff["quality_claim_scope"] == "manifest-readiness only; not product retrieval quality"


def test_builder_check_success_outputs_compact_safe_json() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/build-representative-retrieval-corpus.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["schema_version"] == "representative-retrieval-corpus/v1"
    assert payload["corpus_id"] == "CORPUS-M016-REPRESENTATIVE-V1"
    assert payload["source_artifact_count"] == 5
    assert payload["coverage_class_count"] >= len(REQUIRED_COVERAGE_CLASSES)
    assert not result.stderr
    assert not any(token in result.stdout for token in FORBIDDEN_STRING_TOKENS)


def test_builder_check_detects_stale_manifest_without_touching_repo(monkeypatch, tmp_path) -> None:
    builder = load_builder()
    stale_manifest = tmp_path / "representative_retrieval_corpus_manifest.json"
    stale_report = tmp_path / "representative_retrieval_corpus_manifest.md"
    stale_manifest.write_text('{"stale": true}\n', encoding="utf-8")
    stale_report.write_text(builder.render_report(builder.build_payload()), encoding="utf-8")
    monkeypatch.setattr(builder, "OUTPUT_PATH", stale_manifest)
    monkeypatch.setattr(builder, "REPORT_PATH", stale_report)

    assert builder.main(["--check"]) == 1


def test_builder_rejects_forbidden_field_names_duplicate_ids_and_missing_coverage() -> None:
    builder = load_builder()
    base = builder.build_payload()

    unsafe = deepcopy(base)
    unsafe["query_labels"][0]["raw_query_text"] = "forbidden"
    try:
        builder.validate_payload(unsafe)
    except builder.ManifestError as exc:
        assert exc.diagnostic["code"] == "unsafe_payload_field"
        assert "raw_query_text" in exc.diagnostic["field_path"]
    else:  # pragma: no cover - failure branch is the assertion target
        raise AssertionError("unsafe payload was accepted")

    duplicate = deepcopy(base)
    duplicate["query_labels"][1]["query_label_id"] = duplicate["query_labels"][0]["query_label_id"]
    try:
        builder.validate_payload(duplicate)
    except builder.ManifestError as exc:
        assert exc.diagnostic["code"] == "query_label_mismatch"
    else:  # pragma: no cover
        raise AssertionError("duplicate query label ID was accepted")

    missing_coverage = deepcopy(base)
    missing_coverage["coverage_classes"] = missing_coverage["coverage_classes"][:-1]
    try:
        builder.validate_payload(missing_coverage)
    except builder.ManifestError as exc:
        assert exc.diagnostic["code"] == "coverage_class_missing"
    else:  # pragma: no cover
        raise AssertionError("missing coverage class was accepted")


def test_report_is_bounded_and_manifest_ready() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "Representative Retrieval Corpus Manifest" in report
    assert "Garant boundary: ODT fixture metadata only" in report
    assert "no raw legal text" in report
    assert "closed-gate claim" in report
    assert not any(token in report for token in FORBIDDEN_STRING_TOKENS)
