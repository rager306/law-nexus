#!/usr/bin/env python3
"""Fail-closed host verifier for the M205/S04 reconciliation pin."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for the S04 host verifier") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = "prd/architecture/m205-s04-docs-reconciliation.yaml"
MAX_BYTES = 64 * 1024
DEFERRED = [f"G{i:02d}" for i in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16)]
SELECTED = ["G01", "G02", "G14"]
PC_X = [
    "PC-X-SemanticService",
    "PC-X-MorphEngine",
    "PC-X-global-analyzer-init",
    "PC-X-Instrument-tree",
    "PC-X-occurrence-span",
]
EXPECTED_HASHES = {
    "prd/architecture/m205-s01-pullenti-matrix.yaml": "559b6637139acdf81f8a09cd8683cf28e48f1dd4507e0b9aa6ac67905727a131",
    "prd/architecture/m205-s02-pre-capture-grammar.yaml": "aa21e8b14a8d9e23bf39b8770fec307c31a7989791e36b70600c53c9ffc7588b",
    "prd/architecture/m205-s03-context-fsm.yaml": "1d6fdf0ab295839e81aa301b8db89ada6d6be26d7b200f8604f60ccc0ac02d9d",
    "prd/architecture/npa-capture-arbitration.yaml": "f6d693e8ec5c5e312623d4c971f80c073972e43a0da789e3028e1d6677f0e343",
    "prd/architecture/npa-document-context.yaml": "7e54fcab83da17174d6f85dbbe7705d6c21ce627c7cd750851e7f97aa68e492c",
    "prd/architecture/npa-identifying-cycle.yaml": "72e8901b20cb1a3feb5f62df4084402ed0fab03a93be065429c9adb19bfac0b0",
    "prd/architecture/npa-semantic-process.yaml": "b63bdb1a5d997853369ff39ef4ab52122aa2e631d346e084e17fb882f67ace9b",
    "prd/architecture/current-document-requisites.yaml": "f011db54af7a6c790f046b487ea10e51b395c5f7a6036ef9e7718ba2cf8f60aa",
    "prd/architecture/npa-bounds-scanner-profile.yaml": "ae594b0f6af00cb32d63539d6d0a92a3dc1f8e0d9a67c1f28272a4bb50084e6f",
    "prd/architecture/glossary-governance.md": "0cca23e272b2c270221c1fa59d10725410a5d63aac05778ef23891f6f151728a",
    "prd/architecture/temporal-vocabulary-contract.json": "5b834e913b2d3af7d95493e9b073453c4ddb92ff86f38219df7cb583c7c486b7",
    "prd/architecture/operation-registry.yaml": "cee807b9b7cc68c1a23fa44a3d1fb1432349118e85e36dc7ddaffa36c049e8d6",
    "prd/migration/rust-evidence/m200-s04-contract-reconciliation.json": "6e8d6c37d19b19b9d47d69271bc49fa88e4a890e2debc38f18ee46c2061c329c",
}


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


def load(path: Path, *, limit: int = MAX_BYTES) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink file")
    if path.stat().st_size > limit:
        raise ValueError(f"input exceeds {limit} byte limit")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("input is not valid UTF-8") from exc
    if any(line.lstrip().startswith(("&", "*")) for line in text.splitlines()) or "<<:" in text:
        raise ValueError("YAML anchors, aliases, and merge keys are forbidden")
    return yaml.load(text, Loader=StrictLoader)


def keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys drift: expected {sorted(expected)}, got {sorted(value)}")


def check_pin(value: Any, root: Path) -> None:
    if not isinstance(value, dict):
        raise ValueError("contract must be a mapping")
    keys(
        value,
        {
            "schema",
            "lifecycle",
            "authoritative",
            "owner_adr",
            "consumes",
            "human_adoption",
            "runtime_stop_active",
            "related_decisions",
            "rc28",
            "non_claims",
            "hashed_yaml_mutation",
            "p9_status",
            "s04_owns_p9",
            "pc_x_leave",
            "d388_control",
            "fsm_projection",
            "surfaces",
            "tensions",
            "source_bindings",
        },
        "top-level",
    )
    if (value["schema"], value["lifecycle"], value["authoritative"], value["owner_adr"]) != (
        "law-nexus/m205-s04-docs-reconciliation/v1",
        ["proposed"],
        False,
        "0028",
    ):
        raise ValueError("schema/lifecycle/authority pin drift")
    if value["human_adoption"] != "pending" or value["runtime_stop_active"] is not True:
        raise ValueError("human-adoption or runtime-stop pin drift")
    rc28 = value["rc28"]
    keys(rc28, {"primary", "boundary_only", "disposition"}, "rc28")
    if rc28 != {"primary": ["F19"], "boundary_only": ["F18"], "disposition": "open"}:
        raise ValueError("RC28 disposition drift")
    surfaces = value["surfaces"]
    expected_surfaces = {
        "architecture",
        "adr",
        "adr_readme",
        "cross_matrix",
        "glossary",
        "hashed_npa_yaml",
        "verification_matrix",
        "program_control",
    }
    keys(surfaces, expected_surfaces, "surfaces")
    for name, surface in surfaces.items():
        keys(surface, {"path", "edit"}, f"surface {name}")
    if any(
        surfaces[name]["edit"] != expected_edit
        for name, expected_edit in {
            "glossary": "none",
            "hashed_npa_yaml": "none",
            "architecture": "append",
            "adr": "append",
            "adr_readme": "append",
            "cross_matrix": "append",
            "verification_matrix": "append",
            "program_control": "append",
        }.items()
    ):
        raise ValueError("surface edit policy drift")
    if (
        value["hashed_yaml_mutation"] != "forbidden"
        or value["s04_owns_p9"] is not False
        or value["p9_status"] != "not-s04-after-this/deferred-to-later"
    ):
        raise ValueError("mutation or P9 ownership drift")
    if value["related_decisions"] != ["D380", "D402", "D403", "D457", "D458", "D459"]:
        raise ValueError("related decision set drift")
    if value["consumes"] != [
        "law-nexus/m205-s01-pullenti-matrix/v1",
        "law-nexus/m205-s02-pre-capture-grammar/v1",
        "law-nexus/m205-s03-context-fsm/v1",
    ]:
        raise ValueError("consumed pin set drift")
    control = value["d388_control"]
    keys(
        control,
        {
            "deferred_undefined",
            "selected_baseline",
            "g02_status",
            "not_required_is_process_side_only",
        },
        "d388_control",
    )
    if (
        control["deferred_undefined"] != DEFERRED
        or control["selected_baseline"] != SELECTED
        or control["g02_status"] != "already-wired-do-not-implement-twice"
        or control["not_required_is_process_side_only"] is not True
    ):
        raise ValueError("D388 gate control drift")
    leave = value["pc_x_leave"]
    keys(leave, {"take_or_leave", "ids"}, "pc_x_leave")
    if leave != {"take_or_leave": "leave", "ids": PC_X}:
        raise ValueError("PC-X leave set drift")
    fsm = value["fsm_projection"]
    keys(
        fsm,
        {
            "context_pin_states",
            "context_hashed_states",
            "process_pin_states",
            "process_hashed_states",
            "resolved_is_not_sufficient",
            "not_required_process_side_only",
            "merge_forbidden",
        },
        "fsm_projection",
    )
    if (
        fsm["resolved_is_not_sufficient"] is not True
        or fsm["not_required_process_side_only"] is not True
        or fsm["merge_forbidden"] is not True
    ):
        raise ValueError("FSM projection safety rail drift")
    bindings = value["source_bindings"]
    if not isinstance(bindings, list) or len(bindings) != len(EXPECTED_HASHES):
        raise ValueError("source binding inventory drift")
    seen: set[str] = set()
    for row in bindings:
        keys(row, {"path", "sha256", "kind"}, "source binding")
        path = row["path"]
        if path in seen or path not in EXPECTED_HASHES:
            raise ValueError(f"unknown or duplicate source binding: {path!r}")
        seen.add(path)
        source = safe_file(root, path)
        hasher = hashlib.sha256()
        with source.open("rb") as stream:
            while chunk := stream.read(8192):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        if digest != EXPECTED_HASHES[path] or row["sha256"] != digest:
            raise ValueError(f"source hash drift: {path}")
    if seen != set(EXPECTED_HASHES):
        raise ValueError("source binding paths incomplete")
    tensions = value["tensions"]
    if not isinstance(tensions, list) or len(tensions) != 10:
        raise ValueError("tension inventory must contain exactly ten rows")
    ids: set[str] = set()
    for row in tensions:
        keys(
            row,
            {"id", "owning_source", "anchor", "scope", "proof", "non_claims", "pending_adoption"},
            "tension",
        )
        if row["id"] in ids or row["pending_adoption"] is not True:
            raise ValueError("tension identity or adoption state drift")
        ids.add(row["id"])
    expected_ids = {
        "T-D380-DECREECHANGE",
        "T-G02-ALREADY-WIRED",
        "T-13-GATES",
        "T-P9-RECLASS",
        "T-FSM-PROJECTION",
        "T-IDENTIFYING-OMIT-CHANGE",
        "T-PC-X-LEAVE",
        "T-HUMAN-ADOPTION-PENDING",
        "T-ADR-S03-NAME-COLLISION",
        "T-F18-BOUNDARY",
    }
    if ids != expected_ids:
        raise ValueError("tension ids drift")
    check_documents(root, required=False)


def check_documents(root: Path, *, required: bool) -> None:
    companions = [
        "doc/adr/0028-typed-lexer-legal-marker-lexicon.md",
        "prd/ARCHITECTURE.md",
        "doc/adr/README.md",
        "doc/adr-architecture-cross-matrix.md",
        "prd/architecture/review-cases/rc28-remediation-program.md",
        ".agents/skills/law-nexus-rust/references/verification-matrix.md",
    ]
    missing = [path for path in companions if not safe_file(root, path).is_file()]
    if missing:
        if required:
            raise ValueError("--check-docs requires companion sections: " + ", ".join(missing))
        return
    if required:
        required_by_companion = {
            companions[0]: (
                "m205-s04-docs-reconciliation/v1",
                "D459",
                "human_adoption",
                "runtime_stop",
                "G15",
                "P9",
                "F19",
            ),
            companions[1]: (
                "m205-s04-docs-reconciliation/v1",
                "ADR-0028",
                "[proposed]",
                "G02",
                "P9",
                "F19",
            ),
            companions[2]: (
                "m205-s04-docs-reconciliation/v1",
                "D459",
                "G02",
                "already-wired",
                "P9",
            ),
            companions[3]: (
                "m205-s04-docs-reconciliation/v1",
                "design-only",
                "G02",
                "P9",
                "F19",
            ),
            companions[4]: (
                "m205-s04-docs-reconciliation/v1",
                "G02",
                "already-wired",
                "P9",
                "not-s04-after-this",
                "F19",
            ),
            companions[5]: (
                "design-only",
                "offline fail-closed verifier",
                "adversarial",
                "hashed closeout",
                "ADR conformance",
                "non-claims",
            ),
        }
        for path, literals in required_by_companion.items():
            companion_text = safe_file(root, path).read_text(encoding="utf-8")
            if any(literal not in companion_text for literal in literals):
                raise ValueError(f"--check-docs companion section incomplete: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--check-docs", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        check_pin(load(safe_file(root, args.input)), root)
        if args.check_docs:
            check_documents(root, required=True)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"S04 verifier rejected input: {exc}", file=sys.stderr)
        return 2
    print("S04 verifier: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
