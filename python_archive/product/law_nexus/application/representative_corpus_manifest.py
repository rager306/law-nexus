"""Representative corpus manifest builder use case.

[bounded] M076 S12 application seam extracted from the representative corpus
manifest script. The builder assembles deterministic handoff/proof-planning
metadata only; it does not claim retrieval quality, parser completeness,
legal correctness, LLM authority, or production runtime readiness.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from law_nexus.ports.representative_corpus_manifest import (
    REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS,
    RepresentativeCorpusManifestBuildRequest,
)

SCHEMA_VERSION = "representative-retrieval-corpus/v1"
CORPUS_ID = "CORPUS-M016-REPRESENTATIVE-V1"
GENERATED_BY = "scripts/build_representative_retrieval_corpus_manifest.py"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
REPORT_ARTIFACT = "prd/retrieval/representative_retrieval_corpus_manifest.md"
GATE = "GATE-G011"
REQUIREMENT = "R034"
SOURCE_FIXTURE_INVENTORY_ARTIFACT = "prd/parser/source_fixture_inventory.json"
REAL_ARTIFACT_CASES_ARTIFACT = "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
OFFLINE_CASES_ARTIFACT = "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"

DIAGNOSTIC_CODE_INVENTORY: tuple[str, ...] = (
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
)

REDACTION_FLAGS: dict[str, bool] = {
    "raw_legal_text_persisted": False,
    "raw_query_text_persisted": False,
    "raw_prompt_persisted": False,
    "raw_vector_persisted": False,
    "provider_payload_persisted": False,
    "raw_falkordb_row_persisted": False,
    "generated_legal_advice_persisted": False,
    "absolute_path_persisted": False,
}

COVERAGE_DESCRIPTIONS: dict[str, str] = {
    "source_family_consultant_wordml": "Consultant WordML/XML-derived parser and retrieval proof artifacts represented by IDs, selectors, and hashes only.",
    "source_family_garant_odt_metadata": "Garant ODT source fixture metadata represented by repository-relative inventory path, source hash, and ODT shape metadata only.",
    "legal_unit_path_coverage": "Source document, source block, evidence span, legal unit, act edition, and legal act path IDs are represented where available.",
    "positive_retrieval": "At least one bounded query label expects relevant references.",
    "distractor_retrieval": "At least one bounded query label includes a distractor reference that must not outrank relevant evidence.",
    "scoped_no_answer": "At least one bounded query label expects no answer inside an explicit proof scope.",
    "ambiguous_rejection": "At least one bounded query label is intentionally ambiguous and expects rejection.",
    "unsafe_rejection": "At least one bounded query label covers unsafe payload rejection.",
    "edition_path_mismatch": "At least one bounded query label covers act edition mismatch rejection.",
    "environment_runtime_handoff_boundary": "Manifest includes static runtime handoff constraints without computing runtime retrieval metrics.",
}


@dataclass(frozen=True)
class ManifestError(Exception):
    """Validation failure with structured manifest diagnostics."""

    diagnostic: dict[str, str]

    def __str__(self) -> str:
        return json.dumps(
            {"diagnostic": self.diagnostic, "status": "fail"}, ensure_ascii=False, sort_keys=True
        )


class RepresentativeCorpusManifestBuilder:
    """Build deterministic representative corpus manifests from loaded inputs."""

    def build_payload(self, request: RepresentativeCorpusManifestBuildRequest) -> dict[str, Any]:
        """Return the representative corpus manifest payload."""

        source_artifacts = [
            artifact.as_dict()
            for artifact in sorted(request.source_artifacts, key=lambda item: item.path)
        ]
        local_benchmark = dict(request.local_retrieval_quality_benchmark)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "corpus_id": CORPUS_ID,
            "generated_by": GENERATED_BY,
            "created_by": GENERATED_BY,
            "fixture_artifact": FIXTURE_ARTIFACT,
            "gate": GATE,
            "requirement": REQUIREMENT,
            "non_authoritative": True,
            "source_artifacts": source_artifacts,
            "coverage_classes": coverage_classes(),
            "query_labels": query_labels(),
            "candidate_references": candidate_references(
                dict(request.real_artifact_retrieval_cases),
                dict(request.offline_citation_retrieval_cases),
                dict(request.source_fixture_inventory),
            ),
            "redaction_boundaries": {
                **redaction(),
                "durable_payloads_allowed": [
                    "stable IDs",
                    "bounded enums",
                    "repository-relative paths",
                    "SHA-256 hashes",
                    "counts",
                    "diagnostic codes",
                ],
            },
            "runtime_handoff": runtime_handoff(local_benchmark),
            "s03_handoff": runtime_handoff(local_benchmark),
            "diagnostics": [],
            "diagnostic_code_inventory": list(DIAGNOSTIC_CODE_INVENTORY),
            "non_claims": list(REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS),
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


def stable_representative_corpus_manifest_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic JSON for manifest output."""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def diagnostic(
    code: str, *, severity: str, artifact_path: str, field_path: str | None = None, **ids: str
) -> dict[str, str]:
    """Return a compact structured diagnostic."""

    payload = {"code": code, "severity": severity, "artifact_path": artifact_path}
    if field_path:
        payload["field_path"] = field_path
    for key, value in ids.items():
        if value:
            payload[key] = value
    return payload


def coverage_classes() -> list[dict[str, Any]]:
    """Return the stable coverage class inventory."""

    return [
        {
            "coverage_class_id": f"COV-M016-{index:03d}",
            "class_name": name,
            "description": description,
            "non_authoritative": True,
        }
        for index, (name, description) in enumerate(COVERAGE_DESCRIPTIONS.items(), start=1)
    ]


def redaction() -> dict[str, bool]:
    """Return the redaction boundary flags used by references and labels."""

    return deepcopy(REDACTION_FLAGS)


def _index_cases(cases: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(case[key]): case for case in cases}


def _fixture_by_kind(inventory: Mapping[str, Any], source_kind: str) -> Mapping[str, Any]:
    for fixture in inventory.get("fixtures", []):
        if isinstance(fixture, Mapping) and fixture.get("source_kind") == source_kind:
            return fixture
    raise ManifestError(
        diagnostic(
            "source_family_missing",
            severity="error",
            artifact_path=SOURCE_FIXTURE_INVENTORY_ARTIFACT,
            field_path=f"fixtures[{source_kind}]",
        )
    )


def _evidence_path_ids_from_output(output: Mapping[str, Any]) -> dict[str, str]:
    ids = output.get("evidence_path_ids")
    if isinstance(ids, Mapping):
        return {str(key): str(value) for key, value in ids.items() if value}
    scope = output.get("scope")
    if isinstance(scope, Mapping):
        wanted = (
            "source_document_id",
            "source_block_id",
            "evidence_span_id",
            "legal_unit_id",
            "act_edition_id",
            "citation_key",
        )
        return {key: str(scope[key]) for key in wanted if scope.get(key)}
    return {}


def _reference_from_case(
    *,
    reference_id: str,
    source_family: str,
    reference_role: str,
    case: Mapping[str, Any],
    source_fixture_path: str,
    derivation: str,
) -> dict[str, Any]:
    output = case.get("output")
    output_mapping = output if isinstance(output, Mapping) else {}
    output_bytes = stable_representative_corpus_manifest_json(output_mapping)
    reference: dict[str, Any] = {
        "reference_id": reference_id,
        "source_family": source_family,
        "reference_role": reference_role,
        "source_case_id": str(case.get("case_id", "")),
        "case_class": str(case.get("case_class", "")),
        "expected_result": str(
            case.get("expected_result") or case.get("expected_validator_result") or ""
        ),
        "expected_diagnostic_codes": list(case.get("expected_diagnostic_codes", [])),
        "source_record_ids": list(case.get("source_record_ids", [])),
        "evidence_path_ids": _evidence_path_ids_from_output(output_mapping),
        "excerpt_sha256": hashlib.sha256(output_bytes.encode("utf-8")).hexdigest(),
        "provenance": {
            "source_fixture_path": source_fixture_path,
            "source_case_id": str(case.get("case_id", "")),
            "derivation": derivation,
        },
        "redaction": redaction(),
        "non_authoritative": True,
    }
    query = case.get("query")
    if isinstance(query, Mapping):
        reference["source_query_id"] = str(query.get("query_id", ""))
        reference["source_query_kind"] = str(query.get("query_kind", ""))
    return reference


def candidate_references(
    real_cases_payload: Mapping[str, Any],
    offline_cases_payload: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return stable candidate references without raw legal text or prompts."""

    real_cases = _index_cases(real_cases_payload.get("cases", []), "case_id")
    offline_cases = _index_cases(offline_cases_payload.get("cases", []), "case_id")
    garant_fixture = _fixture_by_kind(inventory, "garant-odt")
    references = [
        _reference_from_case(
            reference_id="RC-M016-001",
            source_family="consultant_wordml",
            reference_role="relevant",
            case=real_cases["CASE-M013-VALID-REAL-ARTIFACT"],
            source_fixture_path=REAL_ARTIFACT_CASES_ARTIFACT,
            derivation="bounded M013 retrieval validator case reference; no source excerpt persisted",
        ),
        _reference_from_case(
            reference_id="RC-M016-002",
            source_family="consultant_wordml",
            reference_role="edition_mismatch",
            case=real_cases["CASE-M013-WRONG-EDITION-PROXY"],
            source_fixture_path=REAL_ARTIFACT_CASES_ARTIFACT,
            derivation="bounded M013 wrong-edition diagnostic reference; no source excerpt persisted",
        ),
        _reference_from_case(
            reference_id="RC-M016-003",
            source_family="consultant_wordml",
            reference_role="no_answer_boundary",
            case=real_cases["CASE-M013-SCOPED-NO-ANSWER"],
            source_fixture_path=REAL_ARTIFACT_CASES_ARTIFACT,
            derivation="bounded M013 scoped no-answer diagnostic reference; no source excerpt persisted",
        ),
        _reference_from_case(
            reference_id="RC-M016-004",
            source_family="consultant_wordml",
            reference_role="ambiguous",
            case=real_cases["CASE-M013-AMBIGUOUS-CITATION"],
            source_fixture_path=REAL_ARTIFACT_CASES_ARTIFACT,
            derivation="bounded M013 ambiguous-citation diagnostic reference; no source excerpt persisted",
        ),
        _reference_from_case(
            reference_id="RC-M016-005",
            source_family="consultant_wordml",
            reference_role="unsafe",
            case=offline_cases["CASE-M014-UNSAFE-CANDIDATE-PAYLOAD"],
            source_fixture_path=OFFLINE_CASES_ARTIFACT,
            derivation="bounded M014 unsafe-payload diagnostic reference; no source excerpt persisted",
        ),
        _reference_from_case(
            reference_id="RC-M016-006",
            source_family="consultant_wordml",
            reference_role="distractor",
            case=offline_cases["CASE-M014-VALID-MARKER-LEVEL-CANDIDATE"],
            source_fixture_path=OFFLINE_CASES_ARTIFACT,
            derivation="bounded M014 marker-level candidate reference used as distractor metadata only",
        ),
        {
            "reference_id": "RC-M016-007",
            "source_family": "garant_odt_metadata",
            "reference_role": "environment_boundary",
            "source_case_ids": [
                SOURCE_FIXTURE_INVENTORY_ARTIFACT,
                "CASE-M015-ENVIRONMENT-BOUNDARY",
            ],
            "fixture_id": str(garant_fixture.get("fixture_id", "")),
            "source_kind": str(garant_fixture.get("source_kind", "")),
            "path": str(garant_fixture.get("path", "")),
            "sha256": str(garant_fixture.get("sha256", "")),
            "provenance": {
                "source_fixture_path": SOURCE_FIXTURE_INVENTORY_ARTIFACT,
                "derivation": "Garant ODT environment-boundary metadata only; no parsed legal text or retrieval-quality claim",
            },
            "redaction": redaction(),
            "non_authoritative": True,
        },
    ]
    return sorted(references, key=lambda item: str(item["reference_id"]))


def query_label(
    index: int,
    *,
    query_kind: str,
    coverage_class_ids: list[str],
    expected_relevant_reference_ids: list[str],
    expected_result: str,
    source_case_ids: list[str],
) -> dict[str, Any]:
    """Return a stable redacted query label."""

    label_id = f"QRL-M016-{index:03d}"
    hash_basis = stable_representative_corpus_manifest_json(
        {
            "query_label_id": label_id,
            "query_kind": query_kind,
            "coverage_class_ids": coverage_class_ids,
            "expected_relevant_reference_ids": expected_relevant_reference_ids,
            "expected_result": expected_result,
            "source_case_ids": source_case_ids,
        }
    )
    return {
        "query_label_id": label_id,
        "query_kind": query_kind,
        "coverage_class_ids": coverage_class_ids,
        "expected_relevant_reference_ids": expected_relevant_reference_ids,
        "expected_result": expected_result,
        "source_case_ids": source_case_ids,
        "query_label_sha256": hashlib.sha256(hash_basis.encode("utf-8")).hexdigest(),
        "redaction": redaction(),
        "non_authoritative": True,
    }


def query_labels() -> list[dict[str, Any]]:
    """Return the stable redacted query label inventory."""

    return [
        query_label(
            1,
            query_kind="positive_retrieval",
            coverage_class_ids=["COV-M016-001", "COV-M016-003", "COV-M016-004"],
            expected_relevant_reference_ids=["RC-M016-001"],
            expected_result="accepted",
            source_case_ids=["CASE-M013-VALID-REAL-ARTIFACT"],
        ),
        query_label(
            2,
            query_kind="distractor_retrieval",
            coverage_class_ids=["COV-M016-001", "COV-M016-005"],
            expected_relevant_reference_ids=["RC-M016-001"],
            expected_result="accepted",
            source_case_ids=["CASE-M014-VALID-MARKER-LEVEL-CANDIDATE"],
        ),
        query_label(
            3,
            query_kind="scoped_no_answer",
            coverage_class_ids=["COV-M016-001", "COV-M016-006"],
            expected_relevant_reference_ids=[],
            expected_result="accepted_scoped_no_answer",
            source_case_ids=["CASE-M013-SCOPED-NO-ANSWER", "CASE-M014-SCOPED-NO-CANDIDATE"],
        ),
        query_label(
            4,
            query_kind="ambiguous_rejection",
            coverage_class_ids=["COV-M016-001", "COV-M016-007"],
            expected_relevant_reference_ids=[],
            expected_result="rejected",
            source_case_ids=["CASE-M013-AMBIGUOUS-CITATION", "CASE-M014-AMBIGUOUS-CANDIDATE-SET"],
        ),
        query_label(
            5,
            query_kind="unsafe_rejection",
            coverage_class_ids=["COV-M016-001", "COV-M016-008"],
            expected_relevant_reference_ids=[],
            expected_result="rejected",
            source_case_ids=[
                "CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION",
                "CASE-M014-UNSAFE-CANDIDATE-PAYLOAD",
            ],
        ),
        query_label(
            6,
            query_kind="edition_path_mismatch",
            coverage_class_ids=["COV-M016-001", "COV-M016-003", "COV-M016-009"],
            expected_relevant_reference_ids=[],
            expected_result="rejected",
            source_case_ids=["CASE-M013-WRONG-EDITION-PROXY"],
        ),
        query_label(
            7,
            query_kind="environment_runtime_handoff_boundary",
            coverage_class_ids=["COV-M016-002", "COV-M016-010"],
            expected_relevant_reference_ids=["RC-M016-007"],
            expected_result="manifest_readiness_only",
            source_case_ids=[SOURCE_FIXTURE_INVENTORY_ARTIFACT, "CASE-M015-ENVIRONMENT-BOUNDARY"],
        ),
    ]


def runtime_handoff(local_benchmark: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded runtime handoff metadata without runtime metric claims."""

    model_boundary = local_benchmark.get("model_boundary", {})
    if not isinstance(model_boundary, Mapping):
        model_boundary = {}
    return {
        "manifest_path": FIXTURE_ARTIFACT,
        "builder_check_command": "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check",
        "canonical_builder_check_command": "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check",
        "schema_version": SCHEMA_VERSION,
        "corpus_id": CORPUS_ID,
        "allowed_runtime_model_boundary": {
            "runtime_class": "local_open_weight_only",
            "expected_baseline_model_id": str(model_boundary.get("model_id", "deepvk/USER-bge-m3")),
            "quality_boundary": "S03 must produce runtime evidence; S02 only hands off redacted static labels and references.",
        },
        "managed_api_allowed": False,
        "managed_embedding_api_fallback_allowed": False,
        "raw_payload_persistence_allowed": False,
        "gate_g011_status": "open",
        "quality_claim_scope": "manifest-readiness only; not product retrieval quality",
    }


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _assert_unique(items: list[Mapping[str, Any]], key: str, artifact_path: str) -> None:
    values = [str(item[key]) for item in items]
    code_by_key = {
        "coverage_class_id": "coverage_class_missing",
        "query_label_id": "query_label_mismatch",
        "reference_id": "candidate_reference_mismatch",
    }
    code = code_by_key.get(key, "manifest_schema_mismatch")
    if len(values) != len(set(values)):
        raise ManifestError(
            diagnostic(
                code,
                severity="error",
                artifact_path=artifact_path,
                field_path=key,
                corpus_id=CORPUS_ID,
            )
        )
    if values != sorted(values):
        raise ManifestError(
            diagnostic(
                code,
                severity="error",
                artifact_path=artifact_path,
                field_path=f"{key}.ordering",
                corpus_id=CORPUS_ID,
            )
        )


def validate_payload(payload: Mapping[str, Any]) -> None:
    """Validate the bounded manifest shape and anti-overclaiming flags."""

    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("corpus_id") != CORPUS_ID:
        raise ManifestError(
            diagnostic(
                "manifest_schema_mismatch",
                severity="error",
                artifact_path=FIXTURE_ARTIFACT,
                field_path="schema_version",
                corpus_id=CORPUS_ID,
            )
        )
    if payload.get("gate") != GATE or payload.get("requirement") != REQUIREMENT:
        raise ManifestError(
            diagnostic(
                "gate_overclaim_forbidden",
                severity="error",
                artifact_path=FIXTURE_ARTIFACT,
                field_path="gate",
                corpus_id=CORPUS_ID,
            )
        )

    coverage = list(payload.get("coverage_classes", []))
    queries = list(payload.get("query_labels", []))
    references = list(payload.get("candidate_references", []))
    _assert_unique(coverage, "coverage_class_id", FIXTURE_ARTIFACT)
    _assert_unique(queries, "query_label_id", FIXTURE_ARTIFACT)
    _assert_unique(references, "reference_id", FIXTURE_ARTIFACT)

    coverage_ids = {item["coverage_class_id"] for item in coverage}
    reference_ids = {item["reference_id"] for item in references}
    for query in queries:
        if not set(query["coverage_class_ids"]) <= coverage_ids:
            raise ManifestError(
                diagnostic(
                    "coverage_class_missing",
                    severity="error",
                    artifact_path=FIXTURE_ARTIFACT,
                    field_path=str(query["query_label_id"]),
                    corpus_id=CORPUS_ID,
                )
            )
        if not set(query["expected_relevant_reference_ids"]) <= reference_ids:
            raise ManifestError(
                diagnostic(
                    "candidate_reference_mismatch",
                    severity="error",
                    artifact_path=FIXTURE_ARTIFACT,
                    field_path=str(query["query_label_id"]),
                    corpus_id=CORPUS_ID,
                )
            )

    for path, value in _walk(payload):
        field = path.split(".")[-1]
        if field in {
            "raw_legal_text",
            "raw_text",
            "source_excerpt",
            "source_excerpts",
            "query_text",
            "raw_query_text",
            "prompt",
            "provider_payload",
        }:
            raise ManifestError(
                diagnostic(
                    "unsafe_payload_field",
                    severity="error",
                    artifact_path=FIXTURE_ARTIFACT,
                    field_path=path,
                    corpus_id=CORPUS_ID,
                )
            )
        if isinstance(value, str) and ("/root/" in value or ".gsd/exec" in value):
            raise ManifestError(
                diagnostic(
                    "unsafe_payload_field",
                    severity="error",
                    artifact_path=FIXTURE_ARTIFACT,
                    field_path=path,
                    corpus_id=CORPUS_ID,
                )
            )

    limits = payload.get("explicit_limits", {})
    if (
        not isinstance(limits, Mapping)
        or limits.get("managed_api_used") is not False
        or limits.get("runtime_metrics_computed") is not False
    ):
        raise ManifestError(
            diagnostic(
                "managed_api_forbidden",
                severity="error",
                artifact_path=FIXTURE_ARTIFACT,
                field_path="explicit_limits",
                corpus_id=CORPUS_ID,
            )
        )

    handoff = payload.get("s03_handoff", {})
    if (
        not isinstance(handoff, Mapping)
        or handoff.get("managed_api_allowed") is not False
        or handoff.get("gate_g011_status") != "open"
    ):
        raise ManifestError(
            diagnostic(
                "gate_overclaim_forbidden",
                severity="error",
                artifact_path=FIXTURE_ARTIFACT,
                field_path="s03_handoff",
                corpus_id=CORPUS_ID,
            )
        )
