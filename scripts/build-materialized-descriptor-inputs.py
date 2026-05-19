#!/usr/bin/env python3
"""Build safe descriptor inputs from M027 materialized candidate records."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZATION = ROOT / "prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"
MATERIALIZATION_VERIFIER = ROOT / "scripts/verify-parser-evidence-span-materialization.py"
OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json"
SCHEMA_VERSION = "materialized-descriptor-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_v1"
DERIVATION_FIELDS = (
    "candidate_kind",
    "structural_unit_kind",
    "citation_granularity",
    "content_role",
    "temporal_status",
    "materialization_method",
    "source_order_index_bucket",
)
ALLOWED_DESCRIPTOR_FIELDS = {
    "candidate_kind": ["evidence_span", "source_block", "citation_boundary", "temporal_scope_marker", "blocked_candidate"],
    "structural_unit_kind": ["document", "article", "clause", "paragraph", "table", "list_item", "unknown_structural_unit"],
    "citation_granularity": ["act_edition", "article_or_evidence_span", "clause", "source_block_marker", "temporal_marker", "unknown_granularity"],
    "content_role": ["retrieval_candidate", "citation_boundary", "scope_boundary", "temporal_boundary", "blocked_unsafe"],
    "temporal_status": ["current_edition", "as_of_date_required", "edition_consistency_required", "unknown_temporal_status"],
    "materialization_method": ["odt_structure_smoke", "content_xml_order_anchor", "parser_blocked"],
    "source_order_index_bucket": ["early_source_order", "middle_source_order", "late_source_order"],
}


class MaterializedDescriptorBuildError(RuntimeError):
    """Raised when descriptor inputs cannot be built from materialization."""


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def safe_hash(*parts: object) -> str:
    return f"sha256:{hashlib.sha256('|'.join(str(part) for part in parts).encode('utf-8')).hexdigest()}"


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MaterializedDescriptorBuildError("JSON root must be object")
    return payload


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MaterializedDescriptorBuildError(f"module load failed: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_order_bucket(index: int) -> str:
    if index <= 3:
        return "early_source_order"
    if index <= 8:
        return "middle_source_order"
    return "late_source_order"


def descriptors_from_candidate(candidate: Mapping[str, Any]) -> dict[str, str]:
    order_index = candidate.get("source_order_index")
    if not isinstance(order_index, int):
        raise MaterializedDescriptorBuildError("source_order_index missing")
    descriptors = {
        "candidate_kind": str(candidate.get("candidate_kind")),
        "structural_unit_kind": str(candidate.get("structural_unit_kind")),
        "citation_granularity": str(candidate.get("citation_granularity")),
        "content_role": str(candidate.get("content_role")),
        "temporal_status": str(candidate.get("temporal_status")),
        "materialization_method": str(candidate.get("materialization_method")),
        "source_order_index_bucket": source_order_bucket(order_index),
    }
    for field, value in descriptors.items():
        if value not in ALLOWED_DESCRIPTOR_FIELDS[field]:
            raise MaterializedDescriptorBuildError(f"descriptor enum not allowed: {field}")
    return descriptors


def descriptor_tokens(descriptors: Mapping[str, str]) -> list[str]:
    return [f"{field}:{descriptors[field]}" for field in DERIVATION_FIELDS]


def build_inputs(materialization_path: Path = MATERIALIZATION) -> dict[str, Any]:
    verifier = load_module(MATERIALIZATION_VERIFIER, "materialization_verifier_for_descriptor_builder")
    verification = verifier.verify_artifact(materialization_path)
    materialization = load_json(materialization_path)
    if materialization.get("status") != "ok":
        raise MaterializedDescriptorBuildError("materialization_not_ok")
    candidates = materialization.get("materialized_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise MaterializedDescriptorBuildError("materialized candidates missing")
    query_descriptors: list[dict[str, Any]] = []
    candidate_descriptors: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, Mapping):
            raise MaterializedDescriptorBuildError("candidate must be object")
        descriptors = descriptors_from_candidate(candidate)
        tokens = descriptor_tokens(descriptors)
        case_id = f"CASE-M027-MAT-{ordinal:03d}"
        query_id = f"QUERY-M027-MAT-{ordinal:03d}"
        materialized_id = str(candidate["candidate_id"])
        base = {
            "case_id": case_id,
            "query_id": query_id,
            "representation_kind": REPRESENTATION_KIND,
            "descriptors": descriptors,
            "descriptor_tokens": tokens,
            "materialized_candidate_ref": materialized_id,
            "source_anchor_ref": str(candidate["source_anchor_id"]),
            "source_anchor_sha256": str(candidate["source_anchor_sha256"]),
            "non_authoritative": True,
        }
        query_descriptors.append(
            {
                **base,
                "descriptor_input_id": f"MAT-DESCQ-M027-{ordinal:03d}",
                "query_hash_ref": safe_hash(query_id, materialized_id, "query"),
            }
        )
        candidate_descriptors.append(
            {
                **base,
                "candidate_id": f"DESC-CAND-M027-{ordinal:03d}",
                "descriptor_input_id": f"MAT-DESCC-M027-{ordinal:03d}",
                "source_record_ids": [materialized_id],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M027-vxdy7c",
        "slice_id": "S03",
        "representation_kind": REPRESENTATION_KIND,
        "materialization_source": repo_ref(materialization_path),
        "materialization_source_sha256": sha256_path(materialization_path),
        "materialization_verification_summary": verification,
        "derivation_fields": list(DERIVATION_FIELDS),
        "allowed_descriptor_fields": ALLOWED_DESCRIPTOR_FIELDS,
        "query_descriptor_count": len(query_descriptors),
        "candidate_descriptor_count": len(candidate_descriptors),
        "query_descriptors": query_descriptors,
        "candidate_descriptors": candidate_descriptors,
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "generated_answer_prose_excluded": True,
            "generated_query_excluded": True,
            "expected_answer_fields_excluded_from_descriptor_inputs": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "r035_non_validation_declared": True,
        "r038_review_required": True,
        "non_authoritative": True,
        "non_claim_boundary": "Descriptor bridge from materialized structural records only; does not validate R035 or prove retrieval quality.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialization", type=Path, default=MATERIALIZATION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_inputs(args.materialization)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "schema_version": manifest["schema_version"],
                "representation_kind": manifest["representation_kind"],
                "query_descriptor_count": manifest["query_descriptor_count"],
                "candidate_descriptor_count": manifest["candidate_descriptor_count"],
                "non_authoritative": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
