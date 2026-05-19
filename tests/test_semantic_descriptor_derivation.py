from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-semantic-descriptor-inputs.py"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
CONTRACT = ROOT / "prd/research/ontology_architecture_requirements/44-local-semantic-scoring-iteration-contract.md"
FORBIDDEN_FIELDS = {
    "expected_label",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "selection_reason",
}


def load_builder(name: str = "semantic_descriptor_builder") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write_fixture(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def descriptor_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "allowed_descriptor_fields": manifest["allowed_descriptor_fields"],
        "query_descriptor_count": manifest["query_descriptor_count"],
        "candidate_descriptor_count": manifest["candidate_descriptor_count"],
        "query_descriptors": manifest["query_descriptors"],
        "candidate_descriptors": manifest["candidate_descriptors"],
    }


def projection_digest(projection: dict[str, Any]) -> str:
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def perturb_forbidden_fields(payload: dict[str, Any]) -> dict[str, Any]:
    perturbed = copy.deepcopy(payload)
    for case_index, case in enumerate(perturbed["cases"], start=1):
        case["expected_candidate_ids"] = [f"PERTURBED-EXPECTED-{case_index}"]
        case["expected_rejected_candidate_ids"] = [f"PERTURBED-REJECTED-{case_index}"]
        case["expected_diagnostic_codes"] = [f"PERTURBED-DIAGNOSTIC-{case_index}"]
        case["query"]["expected_result"] = "perturbed_expected_result"
        for candidate_index, candidate in enumerate(case.get("candidates", []), start=1):
            candidate["expected_label"] = f"perturbed_label_{case_index}_{candidate_index}"
            candidate["rank"] = 999 + candidate_index
            candidate["selection_reason"] = f"perturbed_reason_{case_index}_{candidate_index}"
    return perturbed


def test_builder_declares_forbidden_derivation_fields() -> None:
    builder = load_builder("descriptor_builder_forbidden_fields")

    assert FORBIDDEN_FIELDS.issubset(builder.FORBIDDEN_DERIVATION_FIELDS)


def test_forbidden_answer_field_perturbation_does_not_change_descriptors(tmp_path: Path) -> None:
    builder = load_builder("descriptor_builder_perturbation")
    fixture = load_fixture()
    original_path = write_fixture(tmp_path, "original_fixture.json", fixture)
    perturbed_path = write_fixture(tmp_path, "perturbed_fixture.json", perturb_forbidden_fields(fixture))

    original = descriptor_projection(builder.build_manifest(original_path, CONTRACT))
    perturbed = descriptor_projection(builder.build_manifest(perturbed_path, CONTRACT))

    assert original == perturbed
    assert projection_digest(original) == projection_digest(perturbed)


def test_structural_candidate_field_change_does_change_descriptors(tmp_path: Path) -> None:
    builder = load_builder("descriptor_builder_structural_change")
    fixture = load_fixture()
    structural = copy.deepcopy(fixture)
    structural["cases"][2]["candidates"][0]["candidate_id"] = "CAND-M025-STRUCTURAL-ARTICLE"
    original_path = write_fixture(tmp_path, "original_fixture.json", fixture)
    structural_path = write_fixture(tmp_path, "structural_fixture.json", structural)

    original = descriptor_projection(builder.build_manifest(original_path, CONTRACT))
    changed = descriptor_projection(builder.build_manifest(structural_path, CONTRACT))

    assert original != changed


def test_outcome_like_enum_values_are_absent_from_builder_output(tmp_path: Path) -> None:
    builder = load_builder("descriptor_builder_neutral_enums")
    manifest = builder.build_manifest(write_fixture(tmp_path, "fixture.json", load_fixture()), CONTRACT)
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    for forbidden in (
        "ambiguous_candidates_expected",
        "unsupported_scope_expected",
        "no_answer_expected",
        "prefer_granular_marker_over_broad_unit",
    ):
        assert forbidden not in serialized
    for required in (
        "ambiguity_resolution_required",
        "scope_outside_supported_corpus",
        "scoped_absence_check_required",
        "resolve_granularity_conflict",
    ):
        assert required in serialized


def test_builder_output_does_not_persist_forbidden_answer_fields(tmp_path: Path) -> None:
    builder = load_builder("descriptor_builder_no_forbidden_output")
    manifest = builder.build_manifest(write_fixture(tmp_path, "fixture.json", load_fixture()), CONTRACT)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            assert not (set(value) & (FORBIDDEN_FIELDS | {"expected_result"}))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            assert value not in FORBIDDEN_FIELDS

    walk(manifest)
