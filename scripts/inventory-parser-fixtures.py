#!/usr/bin/env python3
"""Inventory canonical parser fixtures for source hygiene (M006, M072).

The script is intentionally stdlib-only. It DISCOVERS every ``*.xml`` under
``law-source/consultant/`` and every ``*.odt`` under ``law-source/garant/``,
records deterministic diagnostics (SHA-256, XML/ODT shape), classifies each
Consultant fixture by the first line of its ``<o:Title>`` element into an
extended source-role taxonomy, and writes a JSON manifest plus Markdown report
under ``prd/parser/``.

Compared to the v1 inventory, the v2 schema is:

  * Discovery-based — no hardcoded ``EXPECTED_FIXTURES`` list. New fixtures
    appear automatically; the inventory is the truth, not the script.
  * Extended source-role taxonomy per fixture (``source_role_v2`` plus a
    ``document_type`` field). ODT fixtures retain the legacy
    ``odt-document-fixture`` role; Consultant fixtures are classified by the
    pattern matchers below.
  * Internal-duplicate detection — fixtures that are tracked and share a
    SHA-256 are reported in ``internal_duplicate_pairs`` for visibility, but
    do NOT fail the inventory by themselves (per user direction: duplicates
    surfaced, not enforced-cleaned).
  * Pre-existing guards preserved: the removed root-level duplicate must
    remain absent; the PP filename mismatch must remain visible.
  * Classification is title-pattern matching only and is NOT a parser
    assertion. See the explicit non-claims block.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "parser-source-fixture-inventory/v2"
SCRIPT_PATH = "scripts/inventory-parser-fixtures.py"
JSON_OUTPUT = Path("prd/parser/source_fixture_inventory.json")
MARKDOWN_OUTPUT = Path("prd/parser/source_fixture_inventory.md")
REMOVED_DUPLICATE_PATH = "law-source/Список документов (5).xml"
CANONICAL_CONSULTANT_XML_PATH = "law-source/consultant/Список документов (5).xml"
CONSULTANT_FULL_ACT_XML_PATH = "law-source/consultant/44-FZ-2026.xml"
STATED_PP_FIXTURE_PATH = "law-source/garant/PP_60_27-02-2022.odt"
OBSERVED_PP_FIXTURE_PATH = "law-source/garant/PP_60_27-01-2022.odt"

# Office namespaces used by Consultant WordML.
_OFFICE_NS = "urn:schemas-microsoft-com:office:office"
_WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"

# Document-type taxonomy (per M072 S01). These are the observed patterns in the
# current corpus. A fixture whose first-line title matches no pattern falls
# through to ``other_document``; that fall-through is captured and reported but
# does not fail the inventory.
DOCUMENT_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("federal_law", re.compile(r"Федеральн[ыы]й\s+закон", re.IGNORECASE | re.UNICODE)),
    ("code_amendment_overview", re.compile(r"Обзор\s+изменений.*Кодекс", re.IGNORECASE | re.UNICODE)),
    ("code", re.compile(r"\bКодекс\b", re.IGNORECASE | re.UNICODE)),
    ("court_practice_review", re.compile(r"Обзор\s+судебной\s+практики", re.IGNORECASE | re.UNICODE)),
    ("fas_review", re.compile(r"Обзор.*\b(ФАС|Казначейств)", re.IGNORECASE | re.UNICODE)),
    ("government_resolution", re.compile(r"Постановление\s+Правительства", re.IGNORECASE | re.UNICODE)),
    ("constitutional_court_ruling", re.compile(
        r"(Постановление|Определение)\s+Конституционного\s+Суда", re.IGNORECASE | re.UNICODE
    )),
    ("supreme_court_ruling", re.compile(
        r"(Постановление|Определение)\s+Верховного\s+Суда", re.IGNORECASE | re.UNICODE
    )),
    ("lower_court_ruling", re.compile(
        r"Постановление.*(?:арбитражн|кассацион)", re.IGNORECASE | re.UNICODE
    )),
    ("antimonopoly_decision", re.compile(
        r"(Решение|Приказ)\s+(ФАС|УФАС)", re.IGNORECASE | re.UNICODE
    )),
    ("document_list", re.compile(r"Список\s+документов", re.IGNORECASE | re.UNICODE)),
    ("list_related", re.compile(r"^List-", re.IGNORECASE | re.UNICODE)),
)

# Mapping from document_type to source_role_v2 (the v2 taxonomy is just the
# document_type for Consultant fixtures, except the four canonical role names
# from the v1 taxonomy that must be preserved for non-regression).
LEGACY_ROLE_BY_PATH: dict[str, str] = {
    CANONICAL_CONSULTANT_XML_PATH: "document-list-prior-art",
    CONSULTANT_FULL_ACT_XML_PATH: "full-normative-act",
}

NON_CLAIMS = (
    "This inventory does not claim parser completeness.",
    "This inventory does not claim legal correctness or authoritative legal interpretation.",
    "This inventory does not claim product ETL readiness.",
    "This inventory does not claim FalkorDB product runtime readiness.",
    "This inventory does not classify documents beyond first-line title pattern matching; classification is NOT a parser assertion.",
    "Internal duplicates (two tracked fixtures sharing a SHA-256) are surfaced for visibility only — they do NOT fail the inventory by themselves; removal or dedup is a separate user-directed decision.",
    "Consultant document-list WordML XML is classified only as a relation fixture / prior-art evidence source until later validation proves candidate relations.",
    "Consultant full-act WordML XML is the M009 primary source fixture for full normative-act source-shape evidence only; this inventory does not claim parsed legal semantics from it.",
    "Garant ODT work is lower-priority/deferred from M009 and remains covered only by earlier bounded ODT smoke/parser-record evidence.",
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


def xml_name_observations(tag: str | None) -> dict[str, str | None]:
    if not tag:
        return {"root_namespace": None, "root_local_name": None}
    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", 1)
        return {"root_namespace": namespace, "root_local_name": local_name}
    return {"root_namespace": None, "root_local_name": tag}


def xml_summary_from_bytes(data: bytes) -> dict[str, Any]:
    root = ET.fromstring(data)
    return {
        "well_formed": True,
        "root_tag": root.tag,
        **xml_name_observations(root.tag),
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
            "root_namespace": None,
            "root_local_name": None,
            "direct_child_count": None,
        }
    return {
        "well_formed": True,
        "root_tag": root.tag,
        **xml_name_observations(root.tag),
        "direct_child_count": len(list(root)),
    }


def extract_consultant_title_first_line(path: Path) -> str | None:
    """Return the first line of the Consultant ``<o:Title>`` or ``None``.

    Uses stdlib iterparse to avoid loading the entire XML tree — fixtures can
    be tens of MB. We walk the Office namespace ``DocumentProperties`` block
    and pull the ``Title`` text. Consultant Title is plain text (no nested
    elements), so ``elem.text`` at the ``Title`` ``start`` event is enough.
    """
    title_tag = f"{{{_OFFICE_NS}}}Title"
    props_tag = f"{{{_OFFICE_NS}}}DocumentProperties"
    in_props = False
    title_text: str | None = None
    try:
        for event, elem in ET.iterparse(path, events=("start", "end")):
            if event == "start":
                if not in_props and elem.tag == props_tag:
                    in_props = True
                elif in_props and elem.tag == title_tag:
                    title_text = elem.text
            elif event == "end":
                if in_props and elem.tag == props_tag:
                    elem.clear()
                    break
                if elem.tag == title_tag:
                    elem.clear()
    except ET.ParseError:
        return None
    if not title_text:
        return None
    first_line = title_text.strip().splitlines()[0] if title_text.strip() else ""
    return first_line or None


def classify_document_type(first_line: str | None) -> str:
    """Return one of the DOCUMENT_TYPE_PATTERNS labels, or ``other_document``."""
    if not first_line:
        return "other_document"
    for label, pattern in DOCUMENT_TYPE_PATTERNS:
        if pattern.search(first_line):
            return label
    return "other_document"


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
            "root_namespace": None,
            "root_local_name": None,
            "direct_child_count": None,
        },
        "meta_xml": {
            "well_formed": False,
            "root_tag": None,
            "root_namespace": None,
            "root_local_name": None,
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
                            "root_namespace": None,
                            "root_local_name": None,
                            "direct_child_count": None,
                        }
    except zipfile.BadZipFile as exc:
        diagnostics["zip_error"] = str(exc)
    return diagnostics


def discover_fixtures(root: Path) -> list[str]:
    """Return sorted relative paths of every Consultant *.xml + Garant *.odt."""
    found: set[str] = set()
    for pattern in ("law-source/consultant/*.xml",):
        for path in sorted((root / "law-source/consultant").glob("*.xml")) if (root / "law-source/consultant").is_dir() else []:
            found.add(str(path.relative_to(root)))
    for pattern in ("law-source/garant/*.odt",):
        garant_dir = root / "law-source/garant"
        if garant_dir.is_dir():
            for path in sorted(garant_dir.glob("*.odt")):
                found.add(str(path.relative_to(root)))
    return sorted(found)


def inspect_fixture(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    exists = path.is_file()
    sha256 = sha256_file(path)
    fixture: dict[str, Any] = {
        "path": relative_path,
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256,
    }
    if relative_path.endswith(".odt"):
        fixture["source_kind"] = "garant-odt"
        fixture["source_role"] = "odt-document-fixture"
        fixture["source_role_v2"] = "odt-document-fixture"
        fixture["document_type"] = "odt_document"
        fixture["title_first_line"] = None
        fixture["odt_shape"] = inspect_odt(path)
        fixture["xml_shape"] = None
    else:
        fixture["source_kind"] = "consultant-wordml-xml"
        title = extract_consultant_title_first_line(path) if exists else None
        fixture["title_first_line"] = title
        document_type = classify_document_type(title)
        fixture["document_type"] = document_type
        # Legacy role preserves the v1 taxonomy for the two canonical paths;
        # every other Consultant fixture uses the v2 role (which equals its
        # document_type with hyphens replaced by underscores, except a few
        # documented mappings below).
        if relative_path in LEGACY_ROLE_BY_PATH:
            fixture["source_role"] = LEGACY_ROLE_BY_PATH[relative_path]
            fixture["source_role_v2"] = LEGACY_ROLE_BY_PATH[relative_path]
        else:
            # v2 source_role is the same word as document_type but in
            # hyphenated form to match existing taxonomy style.
            fixture["source_role_v2"] = document_type.replace("_", "-")
            fixture["source_role"] = fixture["source_role_v2"]
        fixture["odt_shape"] = None
        fixture["xml_shape"] = xml_summary_from_file(path) if exists else {
            "well_formed": False,
            "root_tag": None,
            "root_namespace": None,
            "root_local_name": None,
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


def find_internal_duplicates(fixtures: list[dict[str, Any]]) -> list[list[str]]:
    """Return sorted list of fixture-path groups (>=2) sharing a SHA-256.

    Each inner list is sorted. The outer list is sorted by the first path.
    Pairs are surfaced for visibility only — they do NOT fail the inventory
    unless they overlap with the existing ``unexpected_duplicate_paths``
    semantics (removed-duplicate reappearing, PP stated path reappearing).
    """
    by_hash: dict[str, list[str]] = {}
    for fixture in fixtures:
        sha = fixture.get("sha256")
        if not sha:
            continue
        by_hash.setdefault(sha, []).append(fixture["path"])
    groups = [sorted(paths) for paths in by_hash.values() if len(paths) >= 2]
    return sorted(groups, key=lambda group: group[0])


def build_fixture_hygiene(
    root: Path,
    duplicate_absent: bool,
    internal_duplicate_pairs: list[list[str]],
) -> dict[str, Any]:
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
            "consultant_full_act_fixture": {
                "canonical_path": CONSULTANT_FULL_ACT_XML_PATH,
                "classification": "canonical-full-act-wordml-source-shape-fixture",
                "diagnostic": "The full Consultant 44-ФЗ WordML file is inventoried as the M009 primary source-shape fixture with hash and XML diagnostics; it does not assert parsed legal semantics, parser completeness, or multi-source readiness. Garant ODT work is lower-priority/deferred from M009.",
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
        "internal_duplicate_pairs": internal_duplicate_pairs,
    }


def build_inventory(root: Path) -> dict[str, Any]:
    relative_paths = discover_fixtures(root)
    fixtures = [inspect_fixture(root, relative_path) for relative_path in relative_paths]
    duplicate_path = root / REMOVED_DUPLICATE_PATH
    duplicate_absent = not duplicate_path.exists()
    internal_duplicate_pairs = find_internal_duplicates(fixtures)
    fixture_hygiene = build_fixture_hygiene(root, duplicate_absent, internal_duplicate_pairs)
    no_unexpected_duplicates = not fixture_hygiene["unexpected_duplicate_paths"]
    all_exist = all(fixture.get("exists") is True for fixture in fixtures)
    all_shapes_valid = all(fixture_ok(fixture) for fixture in fixtures)
    status = "pass" if all_exist and all_shapes_valid and no_unexpected_duplicates else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": SCRIPT_PATH,
        "status": status,
        "non_authoritative": True,
        "fixture_count": len(fixtures),
        "document_type_taxonomy": [label for label, _ in DOCUMENT_TYPE_PATTERNS] + ["other_document"],
        "duplicate_check": {
            "removed_duplicate_path": REMOVED_DUPLICATE_PATH,
            "canonical_path": CANONICAL_CONSULTANT_XML_PATH,
            "duplicate_absent": duplicate_absent,
            "classification": "removed-root-level-byte-identical-duplicate-must-remain-absent",
            "internal_duplicate_pairs": internal_duplicate_pairs,
        },
        "fixture_hygiene": fixture_hygiene,
        "canonical_path_decision": {
            "consultant_wordml_relation_fixture": CANONICAL_CONSULTANT_XML_PATH,
            "consultant_wordml_full_act_fixture": CONSULTANT_FULL_ACT_XML_PATH,
            "removed_duplicate_path": REMOVED_DUPLICATE_PATH,
            "rationale": "The consultant-folder document-list XML remains the canonical relation fixture; the full 44-ФЗ XML is the M009 primary full normative-act source-shape fixture. Garant ODT work is lower-priority/deferred from M009, and no fixture creates parser-completeness, legal-correctness, or multi-source-readiness claims.",
        },
        "source_priority_notes": [
            "Consultant Plus WordML is primary for M009 full normative-act source-shape evidence.",
            "Consultant document-list WordML remains prior-art relation evidence only.",
            "Garant ODT fixtures are lower-priority/deferred from M009; earlier ODT smoke/parser-record artifacts remain bounded evidence, not M009 source priority.",
            "No current inventory artifact claims parser completeness, legal correctness, or multi-source readiness.",
            "M072 S01 extends the inventory to discovery-based coverage of all 54 fixtures and adds a first-line-title classification taxonomy for Consultant XML; classification is NOT a parser assertion.",
        ],
        "non_claims": list(NON_CLAIMS),
        "canonical_paths": [
            fixture["path"]
            for fixture in fixtures
            if fixture.get("source_role") in ("document-list-prior-art", "full-normative-act")
        ],
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
        f"- Internal duplicate pairs: `{len(manifest['duplicate_check']['internal_duplicate_pairs'])}`",
        "",
        "## Canonical path decision",
        "",
        f"- Canonical Consultant WordML relation fixture: `{manifest['canonical_path_decision']['consultant_wordml_relation_fixture']}`",
        f"- Canonical Consultant WordML full-act fixture: `{manifest['canonical_path_decision']['consultant_wordml_full_act_fixture']}`",
        f"- Removed duplicate path that must remain absent: `{manifest['canonical_path_decision']['removed_duplicate_path']}`",
        f"- Rationale: {manifest['canonical_path_decision']['rationale']}",
        "",
        "## Source priority notes",
        "",
    ]
    lines.extend(f"- {note}" for note in manifest["source_priority_notes"])
    lines.extend(
        [
            "",
            "## Document-type taxonomy (v2)",
            "",
        ]
    )
    lines.extend(f"- `{label}`" for label in manifest["document_type_taxonomy"])
    lines.extend(
        [
            "",
            "## Role coverage by document_type",
            "",
        ]
    )
    coverage: dict[str, int] = {}
    for fixture in manifest["fixtures"]:
        coverage[fixture["document_type"]] = coverage.get(fixture["document_type"], 0) + 1
    for label, count in sorted(coverage.items()):
        lines.append(f"- `{label}`: {count}")
    lines.extend(
        [
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
        f"- Consultant full-act hygiene classification: `{manifest['fixture_hygiene']['canonical_path_decisions']['consultant_full_act_fixture']['classification']}`",
        f"- Consultant full-act diagnostic: {manifest['fixture_hygiene']['canonical_path_decisions']['consultant_full_act_fixture']['diagnostic']}",
        f"- Removed duplicate status: `absent={str(manifest['fixture_hygiene']['removed_duplicate_status']['absent']).lower()}`; failure_if_present=`{str(manifest['fixture_hygiene']['removed_duplicate_status']['failure_if_present']).lower()}`",
        f"- Unexpected duplicate paths: `{', '.join(manifest['fixture_hygiene']['unexpected_duplicate_paths']) if manifest['fixture_hygiene']['unexpected_duplicate_paths'] else 'none'}`",
        f"- Internal duplicate pairs (tracked fixtures sharing a SHA-256, surfaced only):",
        ]
    )
    if manifest["fixture_hygiene"]["internal_duplicate_pairs"]:
        for group in manifest["fixture_hygiene"]["internal_duplicate_pairs"]:
            lines.append(f"  - {', '.join(f'`{p}`' for p in group)}")
    else:
        lines.append("  - none")
    lines.extend(
        [
            "",
            "## Fixture inventory",
            "",
            "| Path | Kind | Source role (v2) | Document type | Title (first line) | Exists | Shape diagnostics | SHA-256 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for fixture in manifest["fixtures"]:
        if fixture["source_kind"] == "garant-odt":
            odt_shape = fixture["odt_shape"]
            shape = (
                f"zip={str(odt_shape['zip_valid']).lower()}; "
                f"content.xml={str(odt_shape['required_members']['content.xml']).lower()} "
                f"root={odt_shape['content_xml']['root_tag']} "
                f"namespace={odt_shape['content_xml'].get('root_namespace')} "
                f"children={odt_shape['content_xml']['direct_child_count']}; "
                f"meta.xml={str(odt_shape['required_members']['meta.xml']).lower()} "
                f"root={odt_shape['meta_xml']['root_tag']} "
                f"namespace={odt_shape['meta_xml'].get('root_namespace')} "
                f"children={odt_shape['meta_xml']['direct_child_count']}"
            )
        else:
            xml_shape = fixture["xml_shape"]
            shape = (
                f"xml_well_formed={str(xml_shape['well_formed']).lower()}; "
                f"root={xml_shape['root_tag']}; "
                f"namespace={xml_shape.get('root_namespace')}; "
                f"local={xml_shape.get('root_local_name')}; "
                f"children={xml_shape['direct_child_count']}"
            )
        title_display = (fixture.get("title_first_line") or "").replace("|", "\\|")[:120]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{fixture['path']}`",
                    str(fixture["source_kind"]),
                    str(fixture["source_role_v2"]),
                    str(fixture["document_type"]),
                    title_display or "—",
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
            f"- Internal duplicate pairs (tracked fixtures sharing SHA-256): {len(manifest['duplicate_check']['internal_duplicate_pairs'])}.",
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


def artifact_sha_mismatch_errors(actual_text: str, manifest: dict[str, Any]) -> list[str]:
    try:
        actual_manifest = json.loads(actual_text)
    except json.JSONDecodeError:
        return []
    actual_by_path = {
        fixture.get("path"): fixture.get("sha256")
        for fixture in actual_manifest.get("fixtures", [])
        if isinstance(fixture, dict)
    }
    errors: list[str] = []
    for fixture in manifest["fixtures"]:
        path = fixture["path"]
        if path in actual_by_path and actual_by_path[path] != fixture.get("sha256"):
            errors.append(
                f"SHA mismatch for {path}: generated={fixture.get('sha256')} artifact={actual_by_path[path]}"
            )
    return errors


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
            if relative_path == JSON_OUTPUT:
                errors.extend(artifact_sha_mismatch_errors(actual, manifest))
    if manifest["status"] != "pass":
        errors.append("Inventory status is not pass")
    return errors


def observability_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": manifest["status"],
        "fixture_count": manifest["fixture_count"],
        "duplicate_absent": manifest["duplicate_check"]["duplicate_absent"],
        "internal_duplicate_pairs": manifest["duplicate_check"]["internal_duplicate_pairs"],
        "pp_filename_mismatch": manifest["fixture_hygiene"]["pp_filename_mismatch"],
        "unexpected_duplicate_paths": manifest["fixture_hygiene"]["unexpected_duplicate_paths"],
        "canonical_paths": [fixture["path"] for fixture in manifest["fixtures"] if fixture.get("source_role") in ("document-list-prior-art", "full-normative-act")],
        "source_roles": {
            fixture["path"]: fixture["source_role_v2"] for fixture in manifest["fixtures"]
        },
        "document_types": {
            fixture["path"]: fixture["document_type"] for fixture in manifest["fixtures"]
        },
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
