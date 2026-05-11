#!/usr/bin/env python3
"""Inventory canonical parser fixtures for M006 source hygiene.

The script is intentionally stdlib-only. It inspects the real ODT and
Consultant WordML fixtures, records deterministic diagnostics, verifies that the
removed root-level Consultant XML duplicate remains absent, and writes a JSON
manifest plus Markdown report under prd/parser/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "parser-source-fixture-inventory/v1"
SCRIPT_PATH = "scripts/inventory-parser-fixtures.py"
JSON_OUTPUT = Path("prd/parser/source_fixture_inventory.json")
MARKDOWN_OUTPUT = Path("prd/parser/source_fixture_inventory.md")
REMOVED_DUPLICATE_PATH = "law-source/Список документов (5).xml"
CANONICAL_CONSULTANT_XML_PATH = "law-source/consultant/Список документов (5).xml"
STATED_PP_FIXTURE_PATH = "law-source/garant/PP_60_27-02-2022.odt"
OBSERVED_PP_FIXTURE_PATH = "law-source/garant/PP_60_27-01-2022.odt"

NON_CLAIMS = (
    "This inventory does not claim parser completeness.",
    "This inventory does not claim legal correctness or authoritative legal interpretation.",
    "This inventory does not claim product ETL readiness.",
    "This inventory does not claim FalkorDB product runtime readiness.",
    "Consultant WordML XML is classified only as a relation fixture / prior-art evidence source until later validation proves candidate relations.",
)

EXPECTED_FIXTURES = (
    {
        "path": "law-source/garant/44-fz.odt",
        "source_kind": "garant-odt",
        "canonical": True,
        "role": "odt-document-fixture",
    },
    {
        "path": OBSERVED_PP_FIXTURE_PATH,
        "source_kind": "garant-odt",
        "canonical": True,
        "role": "odt-document-fixture",
    },
    {
        "path": CANONICAL_CONSULTANT_XML_PATH,
        "source_kind": "consultant-wordml-xml",
        "canonical": True,
        "role": "relation-fixture-prior-art-evidence",
    },
)


@dataclass
class InventoryError(Exception):
    """Raised when inventory generation or checking fails."""

    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(self.errors)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def xml_summary_from_bytes(data: bytes) -> dict[str, Any]:
    root = ET.fromstring(data)
    return {
        "well_formed": True,
        "root_tag": root.tag,
        "direct_child_count": len(list(root)),
    }


def xml_summary_from_file(path: Path) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {
            "well_formed": False,
            "parse_error": str(exc),
            "root_tag": None,
            "direct_child_count": None,
        }
    return {
        "well_formed": True,
        "root_tag": root.tag,
        "direct_child_count": len(list(root)),
    }


def inspect_odt(path: Path) -> dict[str, Any]:
    required_members = ("content.xml", "meta.xml")
    diagnostics: dict[str, Any] = {
        "zip_valid": False,
        "required_members": {member: False for member in required_members},
        "required_members_present": False,
        "member_count": 0,
        "content_xml": {
            "well_formed": False,
            "root_tag": None,
            "direct_child_count": None,
        },
        "meta_xml": {
            "well_formed": False,
            "root_tag": None,
            "direct_child_count": None,
        },
    }
    if not path.is_file():
        return diagnostics
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            name_set = set(names)
            diagnostics["zip_valid"] = True
            diagnostics["member_count"] = len(names)
            diagnostics["required_members"] = {
                member: member in name_set for member in required_members
            }
            diagnostics["required_members_present"] = all(
                diagnostics["required_members"].values()
            )
            for member in required_members:
                if member in name_set:
                    try:
                        diagnostics[member.replace(".", "_")] = xml_summary_from_bytes(
                            archive.read(member)
                        )
                    except ET.ParseError as exc:
                        diagnostics[member.replace(".", "_")] = {
                            "well_formed": False,
                            "parse_error": str(exc),
                            "root_tag": None,
                            "direct_child_count": None,
                        }
    except zipfile.BadZipFile as exc:
        diagnostics["zip_error"] = str(exc)
    return diagnostics


def inspect_fixture(root: Path, spec: dict[str, str | bool]) -> dict[str, Any]:
    relative_path = str(spec["path"])
    path = root / relative_path
    exists = path.is_file()
    fixture: dict[str, Any] = {
        "path": relative_path,
        "source_kind": spec["source_kind"],
        "role": spec["role"],
        "canonical": bool(spec["canonical"]),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path),
    }
    if relative_path.endswith(".odt"):
        fixture["odt_shape"] = inspect_odt(path)
        fixture["xml_shape"] = None
    else:
        fixture["odt_shape"] = None
        fixture["xml_shape"] = xml_summary_from_file(path) if exists else {
            "well_formed": False,
            "root_tag": None,
            "direct_child_count": None,
        }
    return fixture


def fixture_ok(fixture: dict[str, Any]) -> bool:
    if not fixture.get("exists"):
        return False
    if fixture.get("source_kind") == "garant-odt":
        odt_shape = fixture.get("odt_shape")
        return bool(
            isinstance(odt_shape, dict)
            and odt_shape.get("zip_valid") is True
            and odt_shape.get("required_members_present") is True
            and odt_shape.get("content_xml", {}).get("well_formed") is True
            and odt_shape.get("meta_xml", {}).get("well_formed") is True
        )
    xml_shape = fixture.get("xml_shape")
    return bool(isinstance(xml_shape, dict) and xml_shape.get("well_formed") is True)


def build_fixture_hygiene(root: Path, duplicate_absent: bool) -> dict[str, Any]:
    stated_pp_path = root / STATED_PP_FIXTURE_PATH
    observed_pp_path = root / OBSERVED_PP_FIXTURE_PATH
    stated_pp_exists = stated_pp_path.exists()
    observed_pp_exists = observed_pp_path.exists()
    unexpected_duplicate_paths = []
    if not duplicate_absent:
        unexpected_duplicate_paths.append(REMOVED_DUPLICATE_PATH)
    if stated_pp_exists:
        unexpected_duplicate_paths.append(STATED_PP_FIXTURE_PATH)
    return {
        "canonical_path_decisions": {
            "garant_pp_fixture": {
                "canonical_path": OBSERVED_PP_FIXTURE_PATH,
                "observed_path": OBSERVED_PP_FIXTURE_PATH,
                "stated_path": STATED_PP_FIXTURE_PATH,
                "classification": "observed-filename-is-canonical-unless-renamed-by-later-human-instruction",
                "diagnostic": "Human/task context mentioned PP_60_27-02-2022.odt, but the repository fixture currently observed is PP_60_27-01-2022.odt; inventory uses the observed filename and fails if the stated alternate path appears unexpectedly.",
            },
            "consultant_wordml_relation_fixture": {
                "canonical_path": CANONICAL_CONSULTANT_XML_PATH,
                "removed_duplicate_path": REMOVED_DUPLICATE_PATH,
                "classification": "consultant-folder-xml-is-canonical-root-level-byte-identical-duplicate-must-remain-absent",
                "diagnostic": "The root-level Consultant XML duplicate was removed after hash verification and must not be silently consumed if it reappears.",
            },
        },
        "removed_duplicate_status": {
            "path": REMOVED_DUPLICATE_PATH,
            "absent": duplicate_absent,
            "failure_if_present": True,
        },
        "pp_filename_mismatch": {
            "stated_path": STATED_PP_FIXTURE_PATH,
            "observed_path": OBSERVED_PP_FIXTURE_PATH,
            "stated_exists": stated_pp_exists,
            "observed_exists": observed_pp_exists,
            "canonical_path": OBSERVED_PP_FIXTURE_PATH,
            "mismatch_visible": True,
            "failure_if_stated_path_reappears": True,
        },
        "unexpected_duplicate_paths": unexpected_duplicate_paths,
    }


def build_inventory(root: Path) -> dict[str, Any]:
    fixtures = [inspect_fixture(root, spec) for spec in EXPECTED_FIXTURES]
    duplicate_path = root / REMOVED_DUPLICATE_PATH
    duplicate_absent = not duplicate_path.exists()
    fixture_hygiene = build_fixture_hygiene(root, duplicate_absent)
    no_unexpected_duplicates = not fixture_hygiene["unexpected_duplicate_paths"]
    all_expected_exist = all(fixture.get("exists") is True for fixture in fixtures)
    all_shapes_valid = all(fixture_ok(fixture) for fixture in fixtures)
    status = "pass" if all_expected_exist and all_shapes_valid and no_unexpected_duplicates else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": SCRIPT_PATH,
        "status": status,
        "non_authoritative": True,
        "fixture_count": len(fixtures),
        "canonical_paths": [fixture["path"] for fixture in fixtures if fixture.get("canonical")],
        "duplicate_check": {
            "removed_duplicate_path": REMOVED_DUPLICATE_PATH,
            "canonical_path": CANONICAL_CONSULTANT_XML_PATH,
            "duplicate_absent": duplicate_absent,
            "classification": "removed-root-level-byte-identical-duplicate-must-remain-absent",
        },
        "fixture_hygiene": fixture_hygiene,
        "canonical_path_decision": {
            "consultant_wordml_relation_fixture": CANONICAL_CONSULTANT_XML_PATH,
            "removed_duplicate_path": REMOVED_DUPLICATE_PATH,
            "rationale": "The consultant-folder XML is the canonical relation fixture; the root-level XML duplicate was byte-identical and removed to avoid path ambiguity.",
        },
        "non_claims": list(NON_CLAIMS),
        "fixtures": fixtures,
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Parser Source Fixture Inventory",
        "",
        "This report is generated by `scripts/inventory-parser-fixtures.py` from repository-local source fixtures.",
        "",
        "## Summary",
        "",
        f"- Schema version: `{manifest['schema_version']}`",
        f"- Status: `{manifest['status']}`",
        f"- Fixture count: `{manifest['fixture_count']}`",
        f"- Duplicate absent: `{str(manifest['duplicate_check']['duplicate_absent']).lower()}`",
        f"- Non-authoritative: `{str(manifest['non_authoritative']).lower()}`",
        "",
        "## Canonical path decision",
        "",
        f"- Canonical Consultant WordML relation fixture: `{manifest['canonical_path_decision']['consultant_wordml_relation_fixture']}`",
        f"- Removed duplicate path that must remain absent: `{manifest['canonical_path_decision']['removed_duplicate_path']}`",
        f"- Rationale: {manifest['canonical_path_decision']['rationale']}",
        "",
        "## Fixture hygiene",
        "",
        f"- PP fixture stated path: `{manifest['fixture_hygiene']['pp_filename_mismatch']['stated_path']}`",
        f"- PP fixture observed/canonical path: `{manifest['fixture_hygiene']['pp_filename_mismatch']['observed_path']}`",
        f"- PP filename mismatch visible: `{str(manifest['fixture_hygiene']['pp_filename_mismatch']['mismatch_visible']).lower()}`",
        f"- PP stated path currently exists: `{str(manifest['fixture_hygiene']['pp_filename_mismatch']['stated_exists']).lower()}`",
        f"- PP hygiene classification: `{manifest['fixture_hygiene']['canonical_path_decisions']['garant_pp_fixture']['classification']}`",
        f"- PP diagnostic: {manifest['fixture_hygiene']['canonical_path_decisions']['garant_pp_fixture']['diagnostic']}",
        f"- Consultant XML hygiene classification: `{manifest['fixture_hygiene']['canonical_path_decisions']['consultant_wordml_relation_fixture']['classification']}`",
        f"- Removed duplicate status: `absent={str(manifest['fixture_hygiene']['removed_duplicate_status']['absent']).lower()}`; failure_if_present=`{str(manifest['fixture_hygiene']['removed_duplicate_status']['failure_if_present']).lower()}`",
        f"- Unexpected duplicate paths: `{', '.join(manifest['fixture_hygiene']['unexpected_duplicate_paths']) if manifest['fixture_hygiene']['unexpected_duplicate_paths'] else 'none'}`",
        "",
        "## Fixture inventory",
        "",
        "| Path | Kind | Role | Exists | Shape diagnostics | SHA-256 |",
        "|---|---|---|---|---|---|",
    ]
    for fixture in manifest["fixtures"]:
        if fixture["source_kind"] == "garant-odt":
            odt_shape = fixture["odt_shape"]
            shape = (
                f"zip={str(odt_shape['zip_valid']).lower()}; "
                f"content.xml={str(odt_shape['required_members']['content.xml']).lower()} "
                f"root={odt_shape['content_xml']['root_tag']} "
                f"children={odt_shape['content_xml']['direct_child_count']}; "
                f"meta.xml={str(odt_shape['required_members']['meta.xml']).lower()} "
                f"root={odt_shape['meta_xml']['root_tag']} "
                f"children={odt_shape['meta_xml']['direct_child_count']}"
            )
        else:
            xml_shape = fixture["xml_shape"]
            shape = (
                f"xml_well_formed={str(xml_shape['well_formed']).lower()}; "
                f"root={xml_shape['root_tag']}; "
                f"children={xml_shape['direct_child_count']}"
            )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{fixture['path']}`",
                    str(fixture["source_kind"]),
                    str(fixture["role"]),
                    str(fixture["exists"]).lower(),
                    shape.replace("|", "\\|"),
                    f"`{fixture['sha256']}`" if fixture.get("sha256") else "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Duplicate XML classification",
            "",
            f"- `{manifest['duplicate_check']['removed_duplicate_path']}` is classified as `{manifest['duplicate_check']['classification']}`.",
            f"- The duplicate-absence check currently reports `duplicate_absent={str(manifest['duplicate_check']['duplicate_absent']).lower()}`.",
            f"- The canonical Consultant WordML XML path is `{manifest['duplicate_check']['canonical_path']}`.",
            "",
            "## Explicit non-claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in manifest["non_claims"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, manifest: dict[str, Any]) -> None:
    json_path = root / JSON_OUTPUT
    markdown_path = root / MARKDOWN_OUTPUT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(manifest), encoding="utf-8")


def check_outputs(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_json = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    expected_markdown = render_markdown(manifest)
    for relative_path, expected in (
        (JSON_OUTPUT, expected_json),
        (MARKDOWN_OUTPUT, expected_markdown),
    ):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"Missing generated artifact: {relative_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"Generated artifact is stale: {relative_path}")
    if manifest["status"] != "pass":
        errors.append("Inventory status is not pass")
    return errors


def observability_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": manifest["status"],
        "fixture_count": manifest["fixture_count"],
        "duplicate_absent": manifest["duplicate_check"]["duplicate_absent"],
        "pp_filename_mismatch": manifest["fixture_hygiene"]["pp_filename_mismatch"],
        "unexpected_duplicate_paths": manifest["fixture_hygiene"]["unexpected_duplicate_paths"],
        "canonical_paths": manifest["canonical_paths"],
        "non_authoritative": manifest["non_authoritative"],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifacts are current without writing them")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    manifest = build_inventory(root)
    if args.check:
        errors = check_outputs(root, manifest)
        print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        return 0
    write_outputs(root, manifest)
    print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
