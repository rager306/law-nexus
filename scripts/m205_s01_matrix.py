#!/usr/bin/env python3
"""Compose and fail-closed check for the M205/S01 design-only matrix.

This is a host verifier, not a product parser.  It reads bounded YAML data and
never imports vendor code or product crates.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment failure
    raise SystemExit("PyYAML is required for the matrix host verifier") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "prd/architecture/m205-s01-pullenti-matrix.yaml"
ROW_KEYS = {
    "id",
    "family",
    "vendor_type",
    "vendor_attr_or_kind",
    "vendor_anchor",
    "pullenti_behavior",
    "take_or_leave",
    "law_nexus_surface",
    "owner_adr",
    "owner_crate_or_yaml",
    "lifecycle",
    "d388_gates",
    "human_adoption",
    "rc28",
    "non_claims",
    "unblocks",
}
TOP_KEYS = {
    "schema",
    "lifecycle",
    "authoritative",
    "owner_adr",
    "non_claims",
    "families",
    "rows",
    "d388_control",
}
DEFERRED = {
    "G03",
    "G04",
    "G05",
    "G06",
    "G07",
    "G08",
    "G09",
    "G10",
    "G11",
    "G12",
    "G13",
    "G15",
    "G16",
}
KIND_WORDS = {
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


def safe_file(root: Path, relative: str, *, write: bool = False) -> Path:
    """Resolve only a relative, slash-separated, non-symlink path below root."""
    value = Path(relative)
    if not relative or value.is_absolute() or "\\" in relative or ".." in value.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    target = (root / value).resolve(strict=False)
    root_real = root.resolve()
    if os.path.commonpath((str(root_real), str(target))) != str(root_real):
        raise ValueError(f"path escapes root: {relative!r}")
    current = root_real
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path rejected: {relative!r}")
    if write and target.exists() and target.is_symlink():
        raise ValueError(f"symlink output rejected: {relative!r}")
    return target


def load(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("matrix symlink rejected")
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("matrix must be a mapping")
    return value


def check(value: dict[str, Any]) -> None:
    if set(value) != TOP_KEYS:
        raise ValueError(f"top-level keys drift: {sorted(set(value) ^ TOP_KEYS)}")
    if value["schema"] != "law-nexus/m205-s01-pullenti-matrix/v1":
        raise ValueError("schema pin drift")
    if (
        value["lifecycle"] != ["proposed"]
        or value["authoritative"] is not False
        or value["owner_adr"] != "0028"
    ):
        raise ValueError("lifecycle/authority/owner contract drift")
    if not isinstance(value["non_claims"], list) or not any(
        "MicroOperation" in x for x in value["non_claims"]
    ):
        raise ValueError("missing design-only non-claims")
    if value["families"] != ["decree", "decree_part", "decree_change", "leave"]:
        raise ValueError("family set drift")
    rows = value["rows"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("rows must be a non-empty list")
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise ValueError("row key shape drift")
        if row["id"] in ids or row["family"] not in value["families"]:
            raise ValueError("duplicate id or unknown family")
        ids.add(row["id"])
        if row["lifecycle"] != ["proposed"] or row["owner_adr"] != "ADR-0028":
            raise ValueError(f"row lifecycle/owner drift: {row['id']}")
        if not row["vendor_anchor"] or not row["non_claims"]:
            raise ValueError(f"missing anchor/non-claim: {row['id']}")
        if row["family"] == "decree_change" and row["human_adoption"] != "pending":
            raise ValueError(f"Change row lacks human_adoption: pending: {row['id']}")
        if row["law_nexus_surface"] in {
            "MicroOperation",
            "LegislativeEffect",
            "InForce",
            "NormRule",
            "WorkId",
        }:
            raise ValueError(f"forbidden promotion surface: {row['id']}")
        text = " ".join(str(x) for x in row.values())
        forbidden = (
            "SemanticService",
            "MorphEngine",
            "m_ru.dat",
            "Instrument tree",
            "global analyzer init",
            "occurrence-span joining",
            "SOURCE=город",
        )
        if row["family"] != "leave" and any(term in text for term in forbidden):
            raise ValueError(f"forbidden leave concept in active row: {row['id']}")
    required = {
        "PC-D-TYPE",
        "PC-D-SOURCE",
        "PC-P-role-ladder",
        "PC-C-OWNER",
        "PC-C-KIND",
        "PC-C-CHILD",
        "PC-C-VALUE",
        "PC-C-PARAM",
        "PC-C-LOCVALUE",
        "PC-C-value-kind",
        "PC-X-SemanticService",
    }
    if not required <= ids:
        raise ValueError(f"matrix inventory incomplete: {sorted(required - ids)}")
    kind = next(row for row in rows if row["id"] == "PC-C-KIND")
    kind_text = f"{kind['vendor_anchor']} {kind['pullenti_behavior']}"
    found_kinds = set(
        re.findall(
            r"(?<![A-Za-z])(Undefined|Container|Append|ExpireChanges|Expire|New|Exchange|Remove|Consider|Suspend|Confidential|Error)(?![A-Za-z])",
            kind_text,
        )
    )
    if kind["vendor_attr_or_kind"] != "KIND" or found_kinds != KIND_WORDS:
        raise ValueError("Change KIND alphabet incomplete")
    if next(row for row in rows if row["id"] == "PC-X-SemanticService")["take_or_leave"] != "leave":
        raise ValueError("SemanticService must remain leave")
    control = value["d388_control"]
    if set(control) != {"deferred_undefined", "selected_already", "overlay_note"}:
        raise ValueError("D388 control keys drift")
    if set(control["deferred_undefined"]) != DEFERRED or set(control["selected_already"]) != {
        "G01",
        "G02",
        "G14",
    }:
        raise ValueError("D388 gate status drift")
    if "G06" not in control["overlay_note"] or "G07" not in control["overlay_note"]:
        raise ValueError("G06/G07 overlay note missing")


def run_check(path: Path) -> None:
    check(load(path))
    print("S01_T01_MATRIX_OK")
    print("S01_T01_HUMAN_ADOPTION_PENDING_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", default="prd/architecture/m205-s01-pullenti-matrix.yaml")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        source = safe_file(root, args.input)
        if args.command == "compose":
            run_check(source)
            if args.output:
                destination = safe_file(root, args.output, write=True)
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Use a subprocess for the copy boundary; no vendor/runtime import is possible.
                subprocess.run(["cp", "--", str(source), str(destination)], check=True, timeout=10)
        else:
            run_check(source)
    except (OSError, ValueError, yaml.YAMLError, subprocess.SubprocessError) as exc:
        print(f"m205_s01_matrix: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
