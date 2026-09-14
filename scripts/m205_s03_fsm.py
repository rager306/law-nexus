#!/usr/bin/env python3
"""Standalone, fail-closed verifier for the M205/S03 design pin."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for the S03 host verifier") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = "prd/architecture/m205-s03-context-fsm.yaml"
MAX_BYTES = 64 * 1024
MATRIX_IDS = {
    "PC-D-ThisDecree",
    "PC-D-EDITION",
    "PC-C-OWNER",
    "PC-C-KIND",
    "PC-C-CHILD",
    "PC-C-VALUE",
    "PC-C-PARAM",
    "PC-C-LOCVALUE",
    "PC-C-value-kind",
    "PC-C-no-auto-reinterpret",
}
KIND_CANDIDATES = {
    "Undefined",
    "Container",
    "Append",
    "Expire",
    "New",
    "Exchange",
    "Remove",
    "Consider",
    "Suspend",
    "ExpireChanges",
    "Confidential",
    "Error",
}
DEFERRED = {f"G{i:02d}" for i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16)}
SELECTED = {"G01", "G02", "G14"}
MUST_NOT = {f"G{i:02d}" for i in (8, 9, 10, 11, 12, 13, 15)}


class StrictLoader(yaml.SafeLoader):
    """Safe loader rejecting duplicate keys, aliases, and merge keys."""


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


def transition_rows(contract: dict[str, Any], label: str) -> None:
    states = set(contract["states"])
    if not isinstance(contract["transitions"], list):
        raise ValueError(f"{label}.transitions must be a list")
    for row in contract["transitions"]:
        keys(row, {"from", "event", "to"}, f"{label} transition")
        origins = row["from"] if isinstance(row["from"], list) else [row["from"]]
        if (
            not set(origins) <= states
            or row["to"] not in states
            or not isinstance(row["event"], str)
        ):
            raise ValueError(f"{label} transition references an unknown state")
    if not set(contract["terminal"]) <= states:
        raise ValueError(f"{label}.terminal references an unknown state")


def check_dependencies(root: Path, value: dict[str, Any]) -> None:
    matrix = load(safe_file(root, "prd/architecture/m205-s01-pullenti-matrix.yaml"))
    grammar = load(safe_file(root, "prd/architecture/m205-s02-pre-capture-grammar.yaml"))
    registry = load(safe_file(root, "prd/architecture/operation-registry.yaml"))
    if matrix.get("schema") != value["consumes_matrix"]:
        raise ValueError("S01 matrix dependency drift")
    if grammar.get("schema") != value["consumes_grammar"]:
        raise ValueError("S02 grammar dependency drift")
    rows = {row.get("id") for row in matrix.get("rows", []) if isinstance(row, dict)}
    if not MATRIX_IDS <= rows:
        raise ValueError("S01 required PC-* row drift")
    if grammar.get("d388_control", {}).get("deferred_undefined") != sorted(DEFERRED):
        raise ValueError("S02 deferred gate set drift")
    if grammar.get("d388_control", {}).get("selected_already") != sorted(SELECTED):
        raise ValueError("S02 selected baseline drift")
    if set(registry.get("schema_version", "")) == set():
        raise ValueError("operation registry is malformed")
    if not isinstance(registry.get("families"), dict):
        raise ValueError("operation registry families drift")


def check(value: dict[str, Any], root: Path) -> None:
    keys(
        value,
        {
            "schema",
            "lifecycle",
            "authoritative",
            "owner_adr",
            "consumes_matrix",
            "consumes_grammar",
            "human_adoption",
            "runtime_stop_active",
            "related_decisions",
            "related_constraints",
            "non_claims",
            "context_fsm_contract",
            "semantic_process_fsm",
            "amendment_alphabet",
        },
        "top-level",
    )
    if (value["schema"], value["lifecycle"], value["authoritative"], value["owner_adr"]) != (
        "law-nexus/m205-s03-context-fsm/v1",
        ["proposed"],
        False,
        "0028",
    ):
        raise ValueError("schema/lifecycle/authority pin drift")
    if value["human_adoption"] != "pending" or value["runtime_stop_active"] is not True:
        raise ValueError("human-adoption or runtime-stop pin drift")
    strings(value["related_decisions"], "related_decisions")
    strings(value["related_constraints"], "related_constraints")
    strings(value["non_claims"], "non_claims")
    check_dependencies(root, value)

    context = value["context_fsm_contract"]
    keys(
        context,
        {
            "id",
            "initial",
            "states",
            "transitions",
            "terminal",
            "resolved_requires",
            "immutability_invariants",
        },
        "context_fsm_contract",
    )
    if (
        context["id"] != "npa-document-context.fsm_contract"
        or context["initial"] != "ContextRequested"
    ):
        raise ValueError("document-context FSM identity drift")
    if context["states"][0] != context["initial"] or "ContextStopped" not in context["states"]:
        raise ValueError("document-context FSM initial/state drift")
    transition_rows(context, "context_fsm_contract")
    if set(context["terminal"]) != {
        "ContextResolved",
        "ContextIncomplete",
        "ContextConflict",
        "ContextStopped",
    }:
        raise ValueError("document-context terminal set drift")
    if (
        "resolved_is_not_sufficient_for_identity_or_temporal_adoption"
        not in context["immutability_invariants"]
    ):
        raise ValueError("resolved sufficiency invariant missing")
    if (
        "not_required_is_process_only_and_never_proves_evidence"
        not in context["immutability_invariants"]
    ):
        raise ValueError("not_required invariant missing")

    process = value["semantic_process_fsm"]
    keys(
        process,
        {"id", "initial", "states", "transitions", "terminal", "immutability_invariants"},
        "semantic_process_fsm",
    )
    if (
        process["id"] != "npa-semantic-process.fsms.context_dependency"
        or process["initial"] != "P0_decode_complete_document"
    ):
        raise ValueError("semantic process FSM identity drift")
    transition_rows(process, "semantic_process_fsm")
    if process["states"][-1] != "Stopped" or process["terminal"] != [
        "P9_emit_proposed_evidence",
        "Stopped",
    ]:
        raise ValueError("semantic process terminal drift")
    if "P9_cannot_claim_edition_membership_or_authority" not in process["immutability_invariants"]:
        raise ValueError("P9 authority invariant missing")

    alphabet = value["amendment_alphabet"]
    keys(
        alphabet,
        {
            "source_rows",
            "operand_roles",
            "kind_source",
            "kind_candidates",
            "kind_not_runtime",
            "distinctions",
            "non_operations",
            "missing_operands",
            "hint_policy",
            "construction_guards",
            "deferred_gates",
            "selected_baseline",
            "must_not_select",
            "living_surface",
            "p9_status",
        },
        "amendment_alphabet",
    )
    if set(alphabet["source_rows"]) != MATRIX_IDS or alphabet["kind_source"] != "PC-C-KIND":
        raise ValueError("amendment source-row drift")
    if set(alphabet["kind_candidates"]) != KIND_CANDIDATES or set(alphabet["kind_not_runtime"]) != {
        "MicroOperation",
        "LegislativeEffect",
        "force",
        "NormRule",
    }:
        raise ValueError("KIND vocabulary boundary drift")
    if (
        set(alphabet["deferred_gates"]) != DEFERRED
        or set(alphabet["selected_baseline"]) != SELECTED
        or set(alphabet["must_not_select"]) != MUST_NOT
    ):
        raise ValueError("gate selection drift")
    if (
        alphabet["missing_operands"] != "IncompleteBecause"
        or alphabet["p9_status"] != "not-s03-after-this/deferred-to-s04-or-later"
    ):
        raise ValueError("fail-closed or P9 status drift")
    guards = alphabet["construction_guards"]
    if not isinstance(guards, list) or [row.get("id") for row in guards] != [
        "self",
        "antecedent",
        "alias",
        "series",
        "edition",
    ]:
        raise ValueError("five construction guards are incomplete or reordered")
    required = {
        "self": {"explicit_ThisRef_grammar", "non_conflicting_required_sidecar_fields"},
        "antecedent": {"proven_cited_series_head"},
        "alias": {
            "declare",
            "use",
            "shadow_or_conflict_status",
            "scope_container_id",
            "boundary_check",
        },
        "series": {
            "open_grammatical_coordination",
            "source_block_order",
            "owner_compatibility",
            "boundary_compatibility",
            "bounded_hops",
            "derivation_path",
        },
        "edition": {"source_backed_relation"},
    }
    for guard in guards:
        keys(
            guard,
            {"id", "required_evidence", "forbidden_substitutes", "positive_case", "negative_case"},
            f"guard {guard.get('id')}",
        )
        if set(guard["required_evidence"]) != required[guard["id"]]:
            raise ValueError(f"guard evidence drift: {guard['id']}")
        if not guard["forbidden_substitutes"] or not guard["negative_case"].get("result"):
            raise ValueError(f"guard is not fail-closed: {guard['id']}")
    if alphabet["living_surface"] != "none_for_P6_P7":
        raise ValueError("P6/P7 living-surface claim drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="root-relative YAML pin")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        path = safe_file(root, args.input)
        value = load(path)
        check(value, root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"S03 verifier rejected input: {exc}", file=sys.stderr)
        return 2
    print("S03 verifier: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
