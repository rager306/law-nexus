from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.representative_corpus_manifest import (
    RepresentativeCorpusManifestBuilder,
    stable_representative_corpus_manifest_json,
)
from law_nexus.ports.representative_corpus_manifest import (
    REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS,
    RepresentativeCorpusManifestBuildRequest,
    RepresentativeCorpusSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _request() -> RepresentativeCorpusManifestBuildRequest:
    return RepresentativeCorpusManifestBuildRequest(
        source_fixture_inventory=_json("prd/parser/source_fixture_inventory.json"),
        local_retrieval_quality_benchmark=_json(
            "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
        ),
        offline_citation_retrieval_cases=_json(
            "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
        ),
        real_artifact_retrieval_cases=_json(
            "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
        ),
        source_artifacts=(
            RepresentativeCorpusSourceArtifact(
                path="prd/parser/source_fixture_inventory.json", sha256="sha-inventory"
            ),
            RepresentativeCorpusSourceArtifact(
                path="prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
                sha256="sha-local",
            ),
            RepresentativeCorpusSourceArtifact(
                path="prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
                sha256="sha-offline",
            ),
            RepresentativeCorpusSourceArtifact(
                path="prd/retrieval/fixtures/real_artifact_retrieval_cases.json", sha256="sha-real"
            ),
            RepresentativeCorpusSourceArtifact(
                path="prd/retrieval/representative_retrieval_corpus_contract.md",
                sha256="sha-contract",
            ),
        ),
    )


def test_representative_corpus_manifest_builder_emits_expected_contract_shape() -> None:
    payload = RepresentativeCorpusManifestBuilder().build_payload(_request())

    assert payload["schema_version"] == "representative-retrieval-corpus/v1"
    assert payload["generated_by"] == "scripts/build_representative_retrieval_corpus_manifest.py"
    assert payload["non_authoritative"] is True
    assert payload["non_claims"] == list(REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS)
    assert payload["source_artifacts"] == [
        {"path": "prd/parser/source_fixture_inventory.json", "sha256": "sha-inventory"},
        {
            "path": "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
            "sha256": "sha-local",
        },
        {
            "path": "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
            "sha256": "sha-offline",
        },
        {"path": "prd/retrieval/fixtures/real_artifact_retrieval_cases.json", "sha256": "sha-real"},
        {
            "path": "prd/retrieval/representative_retrieval_corpus_contract.md",
            "sha256": "sha-contract",
        },
    ]
    assert payload["explicit_limits"]["garant_parsed_content_claimed"] is False
    assert payload["explicit_limits"]["runtime_metrics_computed"] is False


def test_representative_corpus_manifest_builder_preserves_coverage_and_references() -> None:
    payload = RepresentativeCorpusManifestBuilder().build_payload(_request())

    coverage_names = {item["class_name"] for item in payload["coverage_classes"]}
    assert "source_family_consultant_wordml" in coverage_names
    assert "source_family_garant_odt_metadata" in coverage_names
    assert "positive_retrieval" in coverage_names
    assert "environment_runtime_handoff_boundary" in coverage_names
    assert payload["candidate_references"]
    assert payload["query_labels"]
    assert payload["diagnostics"] == []


def test_stable_representative_corpus_manifest_json_is_deterministic() -> None:
    payload = RepresentativeCorpusManifestBuilder().build_payload(_request())

    first = stable_representative_corpus_manifest_json(payload)
    second = stable_representative_corpus_manifest_json(payload)

    assert first == second
    assert first.endswith("\n")
    assert '"raw_legal_text":' not in first
    assert '"generated_answer_prose":' not in first
