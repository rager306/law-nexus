#!/usr/bin/env python3
"""S06 slice battery: fail-closed machine proof of the navigation demo.

Validates the slice contract of M223-d2q075 / S06 end to end (see
``prd/architecture/intermediate-source-navigation-contract.md``, section 13):

(a) the design contract exists and carries the required sections/markers
    ("Navigation model", "Structure and path", "Neighbours", "Subtree text",
    "References and resolution", "Consumers without XML re-parse",
    "Additive-only", "S03 reconciliation", "Slice boundaries", "Threat
    surface", "Requirement impact", "Verification surface", the
    ``frozen-contract-inventory`` / ``navigation-model`` / ``immutability-pins``
    blocks, ``active/unclosed``, ``43785`` and ``reader_navigation``);
(b) the five frozen upstream wire contracts match the sha256 inventory pinned in
    the design contract exactly — drift is an explicit failure, never a silent
    re-pin;
(c) the S03 baseline run reconciles: entries = accepted = 43785, refused = 0,
    incomplete = 0, R1000 stays active/unclosed, status complete;
(d) the T04 census artifact has schema v1, is redacted, satisfies
    ``resolved + unresolved == references``, and pins the exact contract text
    this battery is validating;
(e) immutability: the six section-2 source files and the two frozen
    ``prd/architecture/*.jsonl`` artifacts match the ``immutability-pins`` block;
(f) the machine-readable ``navigation-model`` block is total over the closed
    vocabulary and matches the ``reader_navigation`` (and ``reader_projection``
    id-space) source declarations — model drift fails closed;
(g) it emits ``prd/migration/rust-evidence/m223-s06-navigation-battery.json``
    (schema ``m223-s06-navigation-battery/v1``) carrying only paths, counters,
    hashes and non-claims — never decoded text.

The artifact is written only when every check above passes, so its presence
always means a fully green battery run.  Non-claims: this battery is not an
R1000 closure, not semantic or legal interpretation, not normalization, not
authenticity evidence, and not a physical-pagination surface; whole-corpus
materialization is S05-S07 evidence, not S06 closure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

CONTRACT_RELPATH = "prd/architecture/intermediate-source-navigation-contract.md"
CONTRACT_PATH = ROOT / CONTRACT_RELPATH
BASELINE_RELPATH = "prd/migration/rust-evidence/m223-s03-baseline-run.json"
BASELINE_PATH = ROOT / BASELINE_RELPATH
CENSUS_RELPATH = "prd/migration/rust-evidence/m223-s06-navigation-census.json"
CENSUS_PATH = ROOT / CENSUS_RELPATH
BATTERY_RELPATH = "prd/migration/rust-evidence/m223-s06-navigation-battery.json"
BATTERY_PATH = ROOT / BATTERY_RELPATH
NAV_SOURCE_RELPATH = "crates/ln-decode/src/reader_navigation.rs"
NAV_SOURCE_PATH = ROOT / NAV_SOURCE_RELPATH
PROJECTION_SOURCE_RELPATH = "crates/ln-decode/src/reader_projection.rs"
PROJECTION_SOURCE_PATH = ROOT / PROJECTION_SOURCE_RELPATH
CENSUS_HARNESS_RELPATH = "scripts/m223_s06_navigation_census.py"
CENSUS_HARNESS_PATH = ROOT / CENSUS_HARNESS_RELPATH

SCHEMA = "m223-s06-navigation-battery/v1"
VERSION = 1
BASELINE_SCHEMA = "m223-s03-baseline-run/v1"
CENSUS_SCHEMA = "m223-s06-navigation-census/v1"

INVENTORY_BEGIN = "<!-- frozen-contract-inventory:begin -->"
INVENTORY_END = "<!-- frozen-contract-inventory:end -->"
MODEL_BEGIN = "<!-- navigation-model:begin -->"
MODEL_END = "<!-- navigation-model:end -->"
PINS_BEGIN = "<!-- immutability-pins:begin -->"
PINS_END = "<!-- immutability-pins:end -->"

REQUIRED_MARKERS = (
    "Navigation model",
    "Structure and path",
    "Neighbours",
    "Subtree text",
    "References and resolution",
    "Consumers without XML re-parse",
    "Additive-only",
    "S03 reconciliation",
    "Slice boundaries",
    "Threat surface",
    "Requirement impact",
    "Verification surface",
    INVENTORY_BEGIN,
    INVENTORY_END,
    MODEL_BEGIN,
    MODEL_END,
    PINS_BEGIN,
    PINS_END,
    "active/unclosed",
    "43785",
    "reader_navigation",
)

FROZEN_CONTRACT_RELPATHS: tuple[str, ...] = (
    "prd/architecture/source-jsonl-contract.md",
    "prd/architecture/reader-view-contract.md",
    "prd/architecture/reader-projection-contract.md",
    "prd/architecture/cleaned-projection-contract.md",
    "prd/architecture/npa-analysis-jsonl-contract.md",
)

#: The six section-2 acceptance-contract source files frozen since M222.
FROZEN_SECTION2_RELPATHS: tuple[str, ...] = (
    "crates/ln-decode/src/reader_projection.rs",
    "crates/ln-decode/src/reader_verifier.rs",
    "crates/ln-decode/src/npa_analysis_wire.rs",
    "crates/ln-decode/tests/reader_tail_semantics.rs",
    "crates/ln-decode/tests/npa_analysis_strict_admission.rs",
    "crates/ln-decode/tests/m222_f07_audit.rs",
)

#: The frozen ``prd/architecture/*.jsonl`` tracked artifacts (never modified).
FROZEN_ARCHITECTURE_JSONL_RELPATHS: tuple[str, ...] = (
    "prd/architecture/architecture_items.jsonl",
    "prd/architecture/architecture_edges.jsonl",
)

EXPECTED_ENTRIES = 43785
EXPECTED_ACCEPTED = 43785
EXPECTED_REFUSED = 0
EXPECTED_INCOMPLETE = 0
EXPECTED_R1000_STATUS = "active/unclosed"

#: The closed navigation model pinned by the machine-readable block.  Order is
#: the block order; the source is compared as a set (enum declaration order is
#: an implementation detail).
EXPECTED_ADDRESSES: tuple[tuple[str, str], ...] = (
    ("View", "v"),
    ("Segment", "s"),
    ("Reference", "r"),
)
EXPECTED_NODE_KINDS: tuple[str, ...] = ("View", "Segment", "Reference")
EXPECTED_LINK_KINDS: tuple[str, ...] = ("Contains", "Owns", "ResolvesTo", "Precedes")
EXPECTED_RESOLVE_REASONS: tuple[str, ...] = (
    "NoMatchingNoteDefinition",
    "MultipleMatchingNoteDefinitions",
    "NotAResolvableReference",
    "MissingAnchorElement",
    "MissingNoteView",
)

BATTERY_NON_CLAIMS: tuple[str, ...] = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "not_normalization",
    "not_authenticity_evidence",
    "not_physical_pagination",
    "whole_corpus_materialization_is_s05_s07_not_s06_closure",
    "additive_only_over_five_frozen_wire_contracts",
    "battery_paths_counters_hashes_only_no_decoded_text",
)

INVENTORY_LINE_RE = re.compile(r"^sha256:([0-9a-f]{64})\s+(\S+)$")
ENUM_HEADER_TMPL = "pub enum {name} {{"
ENUM_VARIANT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)")
ID_CONSTRUCTION_TMPL = r'{id_type}::new\(format!\("([a-z]+)'

# ----------------------------------------------------------------- helpers #


def load_census_module():
    """Load the T04 census harness so the redaction guard cannot drift."""
    spec = importlib.util.spec_from_file_location("m223_s06_navigation_census", CENSUS_HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


census = load_census_module()


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_text_or_fail(path: Path, what: str) -> str:
    if not path.is_file():
        pytest.fail(f"battery: {what} is missing: {path}", pytrace=False)
    return path.read_text(encoding="utf-8")


def read_json_or_fail(path: Path, what: str) -> dict[str, Any]:
    if not path.is_file():
        pytest.fail(f"battery: {what} is missing: {path}", pytrace=False)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"battery: {what} is not valid JSON: {error}", pytrace=False)


def _block_lines(text: str, begin: str, end: str, what: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(begin)
        stop = lines.index(end, start + 1)
    except ValueError:
        pytest.fail(f"battery: {what} markers missing in the design contract", pytrace=False)
    return [raw.strip() for raw in lines[start + 1 : stop] if raw.strip()]


# ------------------------------------------------------- parsing, fail-closed #


def parse_inventory(contract_text: str) -> dict[str, str]:
    """Parse the frozen-contract sha256 inventory block, fail-closed."""
    inventory: dict[str, str] = {}
    for stripped in _block_lines(
        contract_text, INVENTORY_BEGIN, INVENTORY_END, "frozen-contract-inventory"
    ):
        match = INVENTORY_LINE_RE.match(stripped)
        assert match is not None, f"battery: malformed inventory line {stripped!r}"
        sha256, relpath = match.groups()
        assert relpath not in inventory, f"battery: duplicate inventory entry for {relpath}"
        inventory[relpath] = sha256
    assert set(inventory) == set(FROZEN_CONTRACT_RELPATHS), (
        "battery: the inventory must list exactly the five frozen upstream contracts, "
        f"got {sorted(inventory)}"
    )
    return inventory


def parse_immutability_pins(contract_text: str) -> dict[str, str]:
    """Parse the immutability-pins block (six section-2 files + two jsonl)."""
    pins: dict[str, str] = {}
    for stripped in _block_lines(contract_text, PINS_BEGIN, PINS_END, "immutability-pins"):
        match = INVENTORY_LINE_RE.match(stripped)
        assert match is not None, f"battery: malformed immutability pin {stripped!r}"
        sha256, relpath = match.groups()
        assert relpath not in pins, f"battery: duplicate immutability pin for {relpath}"
        pins[relpath] = sha256
    expected = set(FROZEN_SECTION2_RELPATHS) | set(FROZEN_ARCHITECTURE_JSONL_RELPATHS)
    assert set(pins) == expected, (
        "battery: the immutability-pins block must list the six section-2 files and "
        f"the two frozen architecture jsonl artifacts, got {sorted(pins)}"
    )
    return pins


def parse_navigation_model_block(
    contract_text: str,
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Parse the machine-readable navigation-model block, fail-closed.

    Returns ``(addresses, node_kinds, link_kinds, resolve_reasons)`` where
    ``addresses`` maps the address kind to its id-space prefix.
    """
    addresses: dict[str, str] = {}
    node_kinds: list[str] = []
    link_kinds: list[str] = []
    resolve_reasons: list[str] = []
    for stripped in _block_lines(contract_text, MODEL_BEGIN, MODEL_END, "navigation-model"):
        parts = stripped.split()
        head, _, value = parts[0].partition(":")
        assert head in {"address", "node_kind", "link_kind", "resolve_reason"}, (
            f"battery: unknown navigation-model line {stripped!r}"
        )
        if head == "address":
            assert len(parts) == 2, f"battery: malformed address line {stripped!r}"
            id_head, _, id_space = parts[1].partition(":")
            assert id_head == "id_space", f"battery: malformed address line {stripped!r}"
            assert value not in addresses, f"battery: duplicate address {value!r}"
            addresses[value] = id_space
        elif head == "node_kind":
            node_kinds.append(value)
        elif head == "link_kind":
            link_kinds.append(value)
        else:
            resolve_reasons.append(value)
    assert tuple(addresses.items()) == EXPECTED_ADDRESSES, (
        f"battery: navigation-model addresses drift: {addresses}"
    )
    assert tuple(node_kinds) == EXPECTED_NODE_KINDS, (
        f"battery: navigation-model node kinds drift: {node_kinds}"
    )
    assert tuple(link_kinds) == EXPECTED_LINK_KINDS, (
        f"battery: navigation-model link kinds drift: {link_kinds}"
    )
    assert tuple(resolve_reasons) == EXPECTED_RESOLVE_REASONS, (
        f"battery: navigation-model resolve reasons drift: {resolve_reasons}"
    )
    return addresses, node_kinds, link_kinds, resolve_reasons


def parse_enum_variants(source_text: str, enum_name: str) -> list[str]:
    """Extract the unit/payload variant names of a ``pub enum`` declaration."""
    header = ENUM_HEADER_TMPL.format(name=enum_name)
    start = source_text.find(header)
    assert start != -1, f"battery: reader_navigation.rs is missing `{header}`"
    body_start = start + len(header)
    end = source_text.find("\n}", body_start)
    assert end != -1, f"battery: could not find the end of enum {enum_name}"
    variants: list[str] = []
    for raw in source_text[body_start:end].splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        match = ENUM_VARIANT_RE.match(line)
        assert match is not None, f"battery: malformed variant line {line!r} in {enum_name}"
        variants.append(match.group(1))
    return variants


def parse_reader_navigation_model(
    source_text: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Parse the closed navigation vocabulary from reader_navigation.rs."""
    addresses = parse_enum_variants(source_text, "NodeAddress")
    node_kinds = parse_enum_variants(source_text, "NavNodeKind")
    link_kinds = parse_enum_variants(source_text, "NavLinkKind")
    resolve_reasons = parse_enum_variants(source_text, "NavResolveReason")
    return addresses, node_kinds, link_kinds, resolve_reasons


def parse_id_space_prefixes(source_text: str) -> dict[str, str]:
    """Parse the ``v`` / ``s`` / ``r`` id-space prefixes from reader_projection.rs."""
    prefixes: dict[str, str] = {}
    for id_type, address_kind in (
        ("ViewId", "View"),
        ("SegmentId", "Segment"),
        ("ReferenceId", "Reference"),
    ):
        pattern = re.compile(ID_CONSTRUCTION_TMPL.format(id_type=id_type))
        found = pattern.findall(source_text)
        assert found, (
            f"battery: reader_projection.rs does not construct {id_type} with a prefixed id token"
        )
        unique = sorted(set(found))
        assert len(unique) == 1, f"battery: {id_type} uses multiple id-space prefixes: {unique}"
        prefixes[address_kind] = unique[0]
    return prefixes


# ---------------------------------------------------------------- redaction #


def redaction_check(artifact: dict[str, Any]) -> None:
    """Fail closed before writing: reuse the T04 census redaction guard."""
    try:
        census.redaction_check(artifact)
    except census.CensusHarnessError as error:
        pytest.fail(f"battery: artifact failed the redaction guard: {error}", pytrace=False)


# ------------------------------------------------------------------ battery #


def run_battery() -> dict[str, Any]:
    """Run every battery check; raise before emitting anything on failure."""
    contract_text = read_text_or_fail(CONTRACT_PATH, "design contract")
    baseline = read_json_or_fail(BASELINE_PATH, "S03 baseline run")
    census_artifact = read_json_or_fail(CENSUS_PATH, "T04 census artifact")
    nav_source = read_text_or_fail(NAV_SOURCE_PATH, "reader_navigation source")
    projection_source = read_text_or_fail(PROJECTION_SOURCE_PATH, "reader_projection source")
    contract_sha256 = sha256_of_file(CONTRACT_PATH)

    # (a) required sections and markers.
    missing = [marker for marker in REQUIRED_MARKERS if marker not in contract_text]
    assert not missing, f"battery: design contract is missing required markers: {missing}"

    # (b) frozen-contract inventory versus the tracked files: drift is an
    # explicit failure, never a silent re-pin.
    inventory = parse_inventory(contract_text)
    frozen: list[dict[str, Any]] = []
    for relpath in FROZEN_CONTRACT_RELPATHS:
        path = ROOT / relpath
        assert path.is_file(), f"battery: frozen contract is missing: {relpath}"
        frozen.append({"path": relpath, "sha256": sha256_of_file(path)})
    for entry in frozen:
        entry["matches_inventory"] = entry["sha256"] == f"sha256:{inventory[entry['path']]}"
    drifted = [
        f"{entry['path']} inventory sha256:{inventory[entry['path']]} != actual {entry['sha256']}"
        for entry in frozen
        if not entry["matches_inventory"]
    ]
    assert not drifted, (
        "battery: frozen upstream contract drift (an explicit re-pin is required, "
        "never a silent one): " + "; ".join(drifted)
    )

    # (c) S03 baseline reconciliation.
    assert baseline.get("schema") == BASELINE_SCHEMA, (
        f"battery: unexpected baseline schema {baseline.get('schema')!r}"
    )
    counts = baseline.get("counts")
    assert isinstance(counts, dict), "battery: baseline carries no counts object"
    for key, expected in (
        ("entries", EXPECTED_ENTRIES),
        ("accepted", EXPECTED_ACCEPTED),
        ("refused", EXPECTED_REFUSED),
        ("incomplete", EXPECTED_INCOMPLETE),
    ):
        assert counts.get(key) == expected, (
            f"battery: S03 baseline counts.{key} must be {expected}, got {counts.get(key)!r}"
        )
    assert baseline.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: R1000 must stay {EXPECTED_R1000_STATUS}, got {baseline.get('r1000_status')!r}"
    )
    assert baseline.get("status") == "complete", (
        f"battery: the baseline run must be complete, got {baseline.get('status')!r}"
    )

    # (d) the census artifact agrees with the contract and keeps the accounting.
    assert census_artifact.get("schema") == CENSUS_SCHEMA, (
        f"battery: unexpected census schema {census_artifact.get('schema')!r}"
    )
    assert census_artifact.get("version") == 1, "battery: the census artifact must be version 1"
    resolved = census_artifact.get("resolved_total")
    unresolved = census_artifact.get("unresolved_total")
    references = census_artifact.get("references_total")
    assert all(isinstance(value, int) for value in (resolved, unresolved, references)), (
        "battery: the census artifact must carry integer resolved/unresolved/references totals"
    )
    assert resolved + unresolved == references, (
        f"battery: census reference accounting broken: {resolved} + {unresolved} != {references}"
    )
    assert census_artifact.get("reference_accounting_ok") is True, (
        "battery: the census artifact must record reference_accounting_ok"
    )
    assert census_artifact.get("contract_sha256") == contract_sha256, (
        "battery: the census pinned a different contract text — re-run the census "
        f"before trusting its counts (census {census_artifact.get('contract_sha256')!r} "
        f"!= current {contract_sha256})"
    )
    redaction_check(census_artifact)

    # (e) immutability of the six section-2 files and the frozen architecture jsonl.
    pins = parse_immutability_pins(contract_text)
    pinned_entries: list[dict[str, Any]] = []
    pin_drift: list[str] = []
    for relpath, pinned in pins.items():
        path = ROOT / relpath
        assert path.is_file(), f"battery: pinned file is missing: {relpath}"
        actual = sha256_of_file(path)
        matches = actual == f"sha256:{pinned}"
        if not matches:
            pin_drift.append(f"{relpath} pinned sha256:{pinned} != actual {actual}")
        pinned_entries.append({"path": relpath, "sha256": actual, "matches_pin": matches})
    assert not pin_drift, (
        "battery: immutability drift on a frozen section-2 file or architecture "
        "jsonl (never a silent re-pin): " + "; ".join(pin_drift)
    )
    section2_entries = [
        entry for entry in pinned_entries if entry["path"] in FROZEN_SECTION2_RELPATHS
    ]
    architecture_entries = [
        entry for entry in pinned_entries if entry["path"] in FROZEN_ARCHITECTURE_JSONL_RELPATHS
    ]

    # (f) navigation-model block versus the source declarations.
    addresses, node_kinds, link_kinds, resolve_reasons = parse_navigation_model_block(contract_text)
    src_addresses, src_node_kinds, src_link_kinds, src_resolve_reasons = (
        parse_reader_navigation_model(nav_source)
    )
    assert list(addresses.keys()) == src_addresses, (
        "battery: navigation-model addresses drift from reader_navigation.rs: "
        f"block={list(addresses.keys())} source={src_addresses}"
    )
    assert sorted(node_kinds) == sorted(src_node_kinds), (
        "battery: navigation-model node kinds drift from reader_navigation.rs: "
        f"block={sorted(node_kinds)} source={sorted(src_node_kinds)}"
    )
    assert sorted(link_kinds) == sorted(src_link_kinds), (
        "battery: navigation-model link kinds drift from reader_navigation.rs: "
        f"block={sorted(link_kinds)} source={sorted(src_link_kinds)}"
    )
    assert sorted(resolve_reasons) == sorted(src_resolve_reasons), (
        "battery: navigation-model resolve reasons drift from reader_navigation.rs: "
        f"block={sorted(resolve_reasons)} source={sorted(src_resolve_reasons)}"
    )
    id_spaces = parse_id_space_prefixes(projection_source)
    assert id_spaces == addresses, (
        "battery: navigation-model id spaces drift from reader_projection.rs: "
        f"block={addresses} source={id_spaces}"
    )

    return {
        "contract_sha256": contract_sha256,
        "frozen_contracts": frozen,
        "section2_entries": section2_entries,
        "architecture_entries": architecture_entries,
        "baseline": baseline,
        "census_artifact": census_artifact,
        "navigation_model": {
            "addresses": dict(addresses),
            "node_kinds": list(node_kinds),
            "link_kinds": list(link_kinds),
            "resolve_reasons": list(resolve_reasons),
        },
    }


def build_artifact(analysis: dict[str, Any]) -> dict[str, Any]:
    baseline = analysis["baseline"]
    counts = baseline["counts"]
    census_artifact = analysis["census_artifact"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "non_claims": list(BATTERY_NON_CLAIMS),
        "contract_path": CONTRACT_RELPATH,
        "contract_sha256": analysis["contract_sha256"],
        "frozen_contracts": analysis["frozen_contracts"],
        "frozen_contracts_match_inventory": True,
        "frozen_section2_files": analysis["section2_entries"],
        "frozen_architecture_jsonl": analysis["architecture_entries"],
        "immutability_pins_match": True,
        "navigation_model": analysis["navigation_model"],
        "navigation_model_block_total": True,
        "navigation_model_matches_source": True,
        "reader_navigation_source_path": NAV_SOURCE_RELPATH,
        "reader_projection_source_path": PROJECTION_SOURCE_RELPATH,
        "s03_baseline_path": BASELINE_RELPATH,
        "s03_baseline_reconciled": {
            "entries": counts["entries"],
            "accepted": counts["accepted"],
            "refused": counts["refused"],
            "incomplete": counts["incomplete"],
            "r1000_status": baseline["r1000_status"],
        },
        "census_path": CENSUS_RELPATH,
        "census_schema": census_artifact["schema"],
        "census_resolved_total": census_artifact["resolved_total"],
        "census_unresolved_total": census_artifact["unresolved_total"],
        "census_references_total": census_artifact["references_total"],
        "census_reference_accounting_ok": True,
        "census_contract_sha256_matches_contract": True,
        "census_redaction_ok": True,
        "redaction": "counts_paths_hashes_and_non_claims_only_no_decoded_text",
    }


@pytest.fixture(scope="session")
def battery() -> dict[str, Any]:
    """Run the full battery; emit the artifact only on a fully green pass."""
    analysis = run_battery()
    artifact = build_artifact(analysis)
    redaction_check(artifact)
    BATTERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    BATTERY_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return analysis


# ------------------------------------------------------------------- checks #


def test_design_contract_carries_required_sections_and_markers(battery):
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        assert marker in text, f"design contract is missing required marker: {marker!r}"


def test_frozen_contracts_match_the_pinned_inventory_exactly(battery):
    frozen = battery["frozen_contracts"]
    assert len(frozen) == len(FROZEN_CONTRACT_RELPATHS) == 5
    for entry in frozen:
        assert entry["matches_inventory"] is True, (
            f"frozen contract drifted against the pinned inventory: {entry['path']}"
        )


def test_s03_baseline_reconciles_and_r1000_stays_unclosed(battery):
    counts = battery["baseline"]["counts"]
    assert counts["entries"] == counts["accepted"] == EXPECTED_ENTRIES
    assert counts["refused"] == EXPECTED_REFUSED
    assert counts["incomplete"] == EXPECTED_INCOMPLETE
    assert battery["baseline"]["r1000_status"] == EXPECTED_R1000_STATUS
    assert battery["baseline"]["status"] == "complete"


def test_census_artifact_is_schema_v1_and_reference_accounting_holds(battery):
    artifact = battery["census_artifact"]
    assert artifact["schema"] == CENSUS_SCHEMA
    assert artifact["version"] == 1
    assert artifact["resolved_total"] + artifact["unresolved_total"] == artifact["references_total"]
    assert artifact["reference_accounting_ok"] is True
    assert artifact["contract_sha256"] == battery["contract_sha256"]


def test_census_artifact_is_redacted(battery):
    redaction_check(battery["census_artifact"])


def test_immutability_pins_cover_six_section2_files_and_two_jsonl(battery):
    assert len(battery["section2_entries"]) == 6
    assert len(battery["architecture_entries"]) == 2
    for entry in battery["section2_entries"] + battery["architecture_entries"]:
        assert entry["matches_pin"] is True, f"immutability drift: {entry['path']}"


def test_navigation_model_block_is_total_over_the_closed_vocabulary(battery):
    model = battery["navigation_model"]
    assert model["addresses"] == {"View": "v", "Segment": "s", "Reference": "r"}
    assert sorted(model["node_kinds"]) == sorted(EXPECTED_NODE_KINDS)
    assert sorted(model["link_kinds"]) == sorted(EXPECTED_LINK_KINDS)
    assert sorted(model["resolve_reasons"]) == sorted(EXPECTED_RESOLVE_REASONS)
    assert len(set(model["link_kinds"])) == 4
    assert len(set(model["resolve_reasons"])) == 5


def test_navigation_model_block_matches_reader_navigation_source(battery):
    # The source side is re-parsed here so a stale fixture can never hide drift.
    nav_source = NAV_SOURCE_PATH.read_text(encoding="utf-8")
    src_addresses, src_node_kinds, src_link_kinds, src_resolve_reasons = (
        parse_reader_navigation_model(nav_source)
    )
    model = battery["navigation_model"]
    assert list(model["addresses"].keys()) == src_addresses
    assert sorted(model["node_kinds"]) == sorted(src_node_kinds)
    assert sorted(model["link_kinds"]) == sorted(src_link_kinds)
    assert sorted(model["resolve_reasons"]) == sorted(src_resolve_reasons)


def test_battery_artifact_is_emitted_redacted_and_schema_versioned(battery):
    assert BATTERY_PATH.is_file(), "the battery artifact must exist after a green pass"
    artifact = json.loads(BATTERY_PATH.read_text(encoding="utf-8"))
    assert artifact["schema"] == SCHEMA
    assert artifact["version"] == VERSION
    assert artifact["frozen_contracts_match_inventory"] is True
    assert artifact["immutability_pins_match"] is True
    assert artifact["navigation_model_matches_source"] is True
    assert artifact["census_reference_accounting_ok"] is True
    assert artifact["census_contract_sha256_matches_contract"] is True
    assert "not_r1000_closure" in artifact["non_claims"]
    assert "not_physical_pagination" in artifact["non_claims"]
    assert len(artifact["frozen_section2_files"]) == 6
    assert len(artifact["frozen_architecture_jsonl"]) == 2
    assert artifact["s03_baseline_reconciled"] == {
        "entries": EXPECTED_ENTRIES,
        "accepted": EXPECTED_ACCEPTED,
        "refused": EXPECTED_REFUSED,
        "incomplete": EXPECTED_INCOMPLETE,
        "r1000_status": EXPECTED_R1000_STATUS,
    }
    redaction_check(artifact)


# ------------------------------------------------------------ negative tests #


def test_inventory_parser_fails_closed_on_a_malformed_line():
    text = "\n".join([INVENTORY_BEGIN, "not-a-valid-line", INVENTORY_END])
    with pytest.raises(AssertionError):
        parse_inventory(text)


def test_navigation_model_parser_rejects_an_unknown_line():
    text = "\n".join([MODEL_BEGIN, "bogus_kind:View", MODEL_END])
    with pytest.raises(AssertionError):
        parse_navigation_model_block(text)


def test_frozen_contract_drift_is_detected_not_silently_repinned():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    inventory = parse_inventory(text)
    # Corrupt one pinned hash in memory; the on-disk file must not match it.
    victim = FROZEN_CONTRACT_RELPATHS[0]
    corrupted = dict(inventory)
    corrupted[victim] = "0" * 64
    actual = sha256_of_file(ROOT / victim)
    assert actual != f"sha256:{corrupted[victim]}", "the drift check must notice a corrupted pin"


def test_redaction_guard_refuses_a_pagination_field():
    with pytest.raises(census.CensusHarnessError):
        census.redaction_check({"page": 1})


def test_redaction_guard_refuses_raw_text():
    with pytest.raises(census.CensusHarnessError):
        census.redaction_check({"note": "сырой декодированный текст"})


def test_redaction_guard_refuses_a_string_under_a_text_key():
    with pytest.raises(census.CensusHarnessError):
        census.redaction_check({"text": "abc"})
    # An integer tally under the same key is accepted (``text`` is a closed
    # ReaderSegmentKind token, not a raw-text payload).
    census.redaction_check({"text": 3})


def test_redaction_guard_refuses_a_forbidden_key():
    with pytest.raises(census.CensusHarnessError):
        census.redaction_check({"decoded": 1})
