#!/usr/bin/env python3
"""Offline, fail-closed verifier for the M205/S02 design contract."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for the S02 host verifier") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = "prd/architecture/m205-s02-pre-capture-grammar.yaml"
MAX_BYTES = 64 * 1024
PHASES = {
    f"P{i}": name
    for i, name in enumerate(
        [
            "P0_decode_complete_document",
            "P1_build_base_context",
            "P2_local_analysis",
            "P3_literal_projection",
            "P4_build_analysis_overlay",
            "P5_close_document_context",
            "P6_semantic_projection",
            "P7_identity_claim_projection",
            "P8_resolve_bindings",
            "P9_emit_proposed_evidence",
        ]
    )
}
MATRIX_IDS = {
    "PC-D-OWNER",
    "PC-D-list-assembly",
    "PC-P-role-ladder",
    "PC-P-OWNER",
    "PC-P-multi-value",
    "PC-P-range-expand",
}
GROUPS = {"federal_law@v1", "code", "government_resolution", "departmental_order", "court_practice"}
DEFERRED = {f"G{i:02d}" for i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16)}
SELECTED = {"G01", "G02", "G14"}
MUST_NOT = {"G06", "G07", "G12", "G13"}


class StrictLoader(yaml.SafeLoader):
    """Safe loader that rejects duplicate mapping keys and aliases."""


def _mapping(loader: StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ValueError("YAML merge keys are forbidden")
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


def _alias(loader: StrictLoader, node: yaml.Node) -> Any:
    raise ValueError("YAML aliases are forbidden")


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
StrictLoader.add_constructor("tag:yaml.org,2002:merge", _alias)


def safe_file(root: Path, relative: str) -> Path:
    value = Path(relative)
    if not relative or value.is_absolute() or "\\" in relative or ".." in value.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    root_real = root.resolve()
    target = (root_real / value).resolve(strict=False)
    if os.path.commonpath((str(root_real), str(target))) != str(root_real):
        raise ValueError(f"path escapes root: {relative!r}")
    current = root_real
    for part in value.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"symlink path rejected: {relative!r}")
    return target


def load(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink file")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"input exceeds {MAX_BYTES} byte limit")
    text = path.read_text(encoding="utf-8")
    if any(line.lstrip().startswith(("&", "*")) for line in text.splitlines()) or "<<:" in text:
        raise ValueError("YAML anchors, aliases, and merge keys are forbidden")
    value = yaml.load(text, Loader=StrictLoader)
    if not isinstance(value, dict):
        raise ValueError("contract must be a mapping")
    return value


def keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys drift: expected {sorted(expected)}, got {sorted(value)}")


def strings(value: Any, label: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")


def check(value: dict[str, Any], root: Path) -> None:
    keys(
        value,
        {
            "schema",
            "lifecycle",
            "authoritative",
            "owner_adr",
            "consumes_matrix",
            "human_adoption",
            "runtime_stop_active",
            "non_claims",
            "p0_p9_binding",
            "sub_seams",
            "pre_capture_grammar",
            "origin_retention",
            "structural_profiles",
            "range_layers",
            "d388_control",
        },
        "top-level",
    )
    if (
        value["schema"] != "law-nexus/m205-s02-pre-capture-grammar/v1"
        or value["lifecycle"] != ["proposed"]
        or value["authoritative"] is not False
        or value["owner_adr"] != "0028"
    ):
        raise ValueError("schema/lifecycle/authority pin drift")
    if (
        value["consumes_matrix"] != "law-nexus/m205-s01-pullenti-matrix/v1"
        or value["human_adoption"] != "pending"
        or value["runtime_stop_active"] is not True
    ):
        raise ValueError("dependency or runtime-stop pin drift")
    strings(value["non_claims"], "non_claims")

    phases = value["p0_p9_binding"]
    if not isinstance(phases, list) or [row.get("id") for row in phases] != list(PHASES):
        raise ValueError("p0_p9_binding must contain exactly P0..P9 in order")
    for row in phases:
        keys(
            row,
            {"id", "yaml_phase", "flags", "living_surface", "gap", "matrix_ids", "rc28"},
            f"phase {row.get('id')}",
        )
        if (
            row["yaml_phase"] != PHASES[row["id"]]
            or not isinstance(row["flags"], list)
            or not isinstance(row["matrix_ids"], list)
            or not isinstance(row["rc28"], list)
        ):
            raise ValueError(f"phase shape drift: {row['id']}")
        if not set(row["matrix_ids"]) <= MATRIX_IDS:
            raise ValueError(f"unknown matrix id in {row['id']}")
    seams = value["sub_seams"]
    if not isinstance(seams, list) or {row.get("id") for row in seams} != {"P3a", "P8a"}:
        raise ValueError("heterogeneous sub-seams are incomplete")
    for row in seams:
        keys(
            row,
            {"id", "yaml_phase", "flags", "living_surface", "gap", "matrix_ids", "rc28"},
            "sub-seam",
        )
        if row["yaml_phase"] not in PHASES.values() or not set(row["matrix_ids"]) <= MATRIX_IDS:
            raise ValueError("sub-seam reference drift")

    grammar = value["pre_capture_grammar"]
    keys(
        grammar,
        {
            "input",
            "excluded_inputs",
            "refused_members",
            "incomplete_tail",
            "boundaries",
            "independent_mixed_act_sentences",
            "act_list",
            "structural_frames",
            "closed_types",
        },
        "pre_capture_grammar",
    )
    if (
        grammar["input"] != ["tokens", "morph_evidence"]
        or grammar["excluded_inputs"]
        != ["captures", "refused_captures", "ContextView", "CurrentDocumentRequisites"]
        or grammar["refused_members"] != "token_evidence_only"
    ):
        raise ValueError("pre-capture input boundary drift")
    if (
        grammar["incomplete_tail"] != {"valid_without": ["date", "doc_no"]}
        or grammar["boundaries"] != ["sentence", "heading", "paragraph"]
        or grammar["independent_mixed_act_sentences"] != "do_not_merge"
    ):
        raise ValueError("pre-capture boundary drift")
    if (
        grammar["act_list"]
        != {
            "mode": "inverted",
            "retain_local_anchor": True,
            "inherited_fields": "never_source_text",
        }
        or grammar["structural_frames"] != "aligned"
    ):
        raise ValueError("act-list or structural-frame policy drift")
    for name, shape in grammar["closed_types"].items():
        keys(shape, {"required", "properties"}, f"closed type {name}")

    origins = value["origin_retention"]
    keys(
        origins,
        {
            "source_keys",
            "same_span_identical",
            "incompatible_or_partial_overlap",
            "containment_without_policy",
            "unknown_policy",
            "source_function_order",
            "origin_loss",
        },
        "origin_retention",
    )
    if (
        origins["source_keys"] != ["source_id", "source_span", "source_kind"]
        or origins["origin_loss"] != "forbidden"
    ):
        raise ValueError("origin key or loss policy drift")
    if (
        origins["same_span_identical"] != "merge_evidence_with_both_origins"
        or origins["incompatible_or_partial_overlap"] != "conflict"
        or origins["containment_without_policy"] != "ambiguous_both"
        or origins["unknown_policy"] != "conflict"
        or origins["source_function_order"] != "not_precedence"
    ):
        raise ValueError("origin arbitration policy drift")

    profiles = value["structural_profiles"]
    keys(
        profiles,
        {"authority", "implementation_owner", "groups", "sibling_policy", "ambiguous_profile"},
        "structural_profiles",
    )
    if (
        profiles["authority"] != "kb-ontology#document_groups"
        or profiles["implementation_owner"] != "M206/S01"
        or profiles["sibling_policy"] != "same_rank_siblings"
        or profiles["ambiguous_profile"] != "diagnostic_and_fail_closed"
    ):
        raise ValueError("structural profile authority drift")
    groups = profiles["groups"]
    if not isinstance(groups, list) or {row.get("id") for row in groups} != GROUPS:
        raise ValueError("document group inventory drift")
    for row in groups:
        keys(row, {"id", "rank", "text_only", "annex", "razdel"}, f"group {row.get('id')}")
        if row["rank"] != 1 or (row["id"] == "court_practice") != row["text_only"]:
            raise ValueError("group rank/text-only policy drift")
    if (
        next(row for row in groups if row["id"] == "federal_law@v1")["razdel"]
        != "undeclared_fail_closed"
    ):
        raise ValueError("federal-law razdel policy drift")

    ranges = value["range_layers"]
    keys(
        ranges,
        {
            "written_range",
            "endpoint_pair",
            "membership",
            "forbidden",
            "morphology_status",
            "normalization",
        },
        "range_layers",
    )
    if ranges["written_range"] != {
        "phase": "P3",
        "original_anchors": "required",
        "dash_divergence": "retained",
    } or ranges["endpoint_pair"] != {"phase": "P8", "shape": "expanded_pair"}:
        raise ValueError("range layer drift")
    if ranges["membership"] != {
        "phase": "P8",
        "status": "missing",
        "selected_document_version_ref": "DocumentStructureIndex",
    }:
        raise ValueError("membership layer drift")
    if not {
        "arithmetic",
        "vendor_max_min_le_200",
        "CLAUSE_copy_in_local_grammar",
        "edition_substitution_by_ATTR_EDITION",
        "edition_substitution_by_date",
        "edition_substitution_by_CTV",
        "edition_substitution_by_InForce",
    } <= set(ranges["forbidden"]):
        raise ValueError("range forbidden set incomplete")
    if (
        ranges["morphology_status"] != "explicit"
        or ranges["normalization"] != "does_not_create_identity"
    ):
        raise ValueError("range status/identity policy drift")

    control = value["d388_control"]
    keys(control, {"deferred_undefined", "selected_already", "must_not_select"}, "d388_control")
    if (
        set(control["deferred_undefined"]) != DEFERRED
        or set(control["selected_already"]) != SELECTED
        or set(control["must_not_select"]) != MUST_NOT
    ):
        raise ValueError("D388 control drift")
    matrix = safe_file(root, "prd/architecture/m205-s01-pullenti-matrix.yaml")
    semantic = safe_file(root, "prd/architecture/npa-semantic-process.yaml")
    ontology = safe_file(root, "prd/architecture/kb-ontology.yaml")
    if (
        not matrix.is_file()
        or matrix.is_symlink()
        or not semantic.is_file()
        or not ontology.is_file()
    ):
        raise ValueError("source contract unavailable")
    matrix_value = yaml.safe_load(matrix.read_text(encoding="utf-8"))
    semantic_value = yaml.safe_load(semantic.read_text(encoding="utf-8"))
    ontology_value = yaml.safe_load(ontology.read_text(encoding="utf-8"))
    matrix_ids = {row["id"] for row in matrix_value["rows"]}
    process_ids = {row["id"].split("_", 1)[0] for row in semantic_value["pipeline"]}
    ontology_ids = {row["id"] for row in ontology_value["document_groups"]["groups"]}
    referenced_matrix = {item for row in phases + seams for item in row["matrix_ids"]}
    if (
        not referenced_matrix <= matrix_ids
        or set(PHASES) != process_ids
        or not GROUPS <= ontology_ids
    ):
        raise ValueError("source reference resolution drift")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", default=DEFAULT_INPUT)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        check(load(safe_file(root, args.input)), root)
    except (OSError, ValueError, yaml.YAMLError, UnicodeError) as exc:
        print(f"m205_s02_grammar: {exc}", file=sys.stderr)
        return 1
    print("S02_T01_GRAMMAR_OK")
    print("S02_T01_BOUNDARIES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
