"""S05 slice battery: fail-closed machine proof of the clean-view demo.

Validates the slice contract of M223/S05 end to end (see
prd/architecture/intermediate-source-clean-view-contract.md, section 12):

(a) the design contract document exists and carries the required sections and
    markers (source versus clean views boundary, the machine-readable
    clean-rule-profile block, source mapping, S03 reconciliation, the slice
    boundary S05/S06, the real-class obligation and the frozen-contract
    inventory);
(b) the five frozen upstream wire contracts match the sha256 inventory pinned
    in the design contract exactly — drift is an explicit failure, never a
    silent re-pin;
(c) the S03 baseline run reconciles: entries = accepted = 43785, refused = 0,
    incomplete = 0, R1000 stays active/unclosed;
(d) the machine-readable clean-rule-profile block is total over the seven
    ReaderSemantic classes and matches the declarations parsed from
    crates/ln-decode/src/reader_clean_view.rs — profile drift fails closed;
(e) the T03 real-class census artifact reports uncovered_classes == [] and
    profile_id == reader_clean_profile/v1, and pins the exact contract text
    the census proved coverage for;
(f) emits prd/migration/rust-evidence/m223-s05-clean-view-battery.json
    (schema m223-s05-clean-view-battery/v1) carrying only paths, counters,
    hashes and non-claims — never decoded text.

The artifact is written only when every check above passes, so its presence
always means a fully green battery run.  Non-claims: this battery is not an
R1000 closure, not semantic or legal interpretation, not normalization, not
authenticity evidence; whole-corpus materialization is S05-S07 evidence, not
S05 closure; the cleaned_wire envelope stays lossless and is not re-described.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELPATH = "prd/architecture/intermediate-source-clean-view-contract.md"
CONTRACT_PATH = ROOT / CONTRACT_RELPATH
BASELINE_RELPATH = "prd/migration/rust-evidence/m223-s03-baseline-run.json"
BASELINE_PATH = ROOT / BASELINE_RELPATH
CENSUS_RELPATH = "prd/migration/rust-evidence/m223-s05-real-class-census.json"
CENSUS_PATH = ROOT / CENSUS_RELPATH
BATTERY_RELPATH = "prd/migration/rust-evidence/m223-s05-clean-view-battery.json"
BATTERY_PATH = ROOT / BATTERY_RELPATH
CLEAN_VIEW_RELPATH = "crates/ln-decode/src/reader_clean_view.rs"
CLEAN_VIEW_PATH = ROOT / CLEAN_VIEW_RELPATH

SCHEMA = "m223-s05-clean-view-battery/v1"
VERSION = 1
PROFILE_ID = "reader_clean_profile/v1"
BASELINE_SCHEMA = "m223-s03-baseline-run/v1"
CENSUS_SCHEMA = "m223-s05-real-class-census/v1"
PROFILE_BEGIN = "<!-- clean-rule-profile:begin -->"
PROFILE_END = "<!-- clean-rule-profile:end -->"
INVENTORY_BEGIN = "<!-- frozen-contract-inventory:begin -->"
INVENTORY_END = "<!-- frozen-contract-inventory:end -->"

REQUIRED_MARKERS = (
    "Source versus clean views boundary",
    "Source mapping",
    "S03 reconciliation",
    "Slice boundary S05 / S06",
    "Real-class obligation",
    PROFILE_BEGIN,
    PROFILE_END,
    INVENTORY_BEGIN,
    INVENTORY_END,
    PROFILE_ID,
    "active/unclosed",
    "43785",
    "reader_clean_view",
    "revision_deletion",
)

EXPECTED_CLASSES: tuple[str, ...] = (
    "body",
    "whitespace",
    "field_code",
    "revision_insertion",
    "revision_deletion",
    "derived_separator",
    "empty",
)
VALID_DISPOSITIONS: tuple[str, ...] = ("primary", "service", "dropped")
REVISION_CLASSES: tuple[str, ...] = ("revision_insertion", "revision_deletion")

FROZEN_CONTRACT_RELPATHS: tuple[str, ...] = (
    "prd/architecture/source-jsonl-contract.md",
    "prd/architecture/reader-view-contract.md",
    "prd/architecture/reader-projection-contract.md",
    "prd/architecture/cleaned-projection-contract.md",
    "prd/architecture/npa-analysis-jsonl-contract.md",
)

#: The six section-2 acceptance-contract source files frozen since M222.  The
#: battery records their current sha256 as the S05 pin, so any later drift is
#: machine-detectable against this artifact.
FROZEN_SECTION2_RELPATHS: tuple[str, ...] = (
    "crates/ln-decode/src/reader_projection.rs",
    "crates/ln-decode/src/reader_verifier.rs",
    "crates/ln-decode/src/npa_analysis_wire.rs",
    "crates/ln-decode/tests/reader_tail_semantics.rs",
    "crates/ln-decode/tests/npa_analysis_strict_admission.rs",
    "crates/ln-decode/tests/m222_f07_audit.rs",
)

RUST_CLASS_TO_NAME = {
    "Body": "body",
    "Whitespace": "whitespace",
    "FieldCode": "field_code",
    "RevisionInsertion": "revision_insertion",
    "RevisionDeletion": "revision_deletion",
    "DerivedSeparator": "derived_separator",
    "Empty": "empty",
}
RUST_DISPOSITION_TO_NAME = {
    "Primary": "primary",
    "Service": "service",
    "Dropped": "dropped",
}

INVENTORY_LINE_RE = re.compile(r"^sha256:([0-9a-f]{64})\s+(\S+)$")
RUST_STATIC_RULE_RE = re.compile(
    r"static\s+RULE_\w+\s*:\s*CleanRule\s*=\s*CleanRule\s*\{"
    r"[^}]*?id:\s*\"(?P<id>[^\"]+)\""
    r"[^}]*?class:\s*ReaderSemantic::(?P<class>\w+)"
    r"[^}]*?disposition:\s*CleanDisposition::(?P<disposition>\w+)"
)
RUST_MATCH_ARM_RE = re.compile(r"ReaderSemantic::(\w+)\s*=>\s*&RULE_\w+,")
RUST_PROFILE_ID_RE = re.compile(r"READER_CLEAN_PROFILE\s*:\s*&str\s*=\s*\"([^\"]+)\"")

#: Evidence redaction: every artifact string is a path, hash, token or
#: snake_case label; decoded corpus text never fits this closed shape.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:]{1,240}$")
FORBIDDEN_KEYS = frozenset({"text", "literal", "decoded", "content", "detail"})

NON_CLAIMS: tuple[str, ...] = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "not_normalization",
    "not_authenticity_evidence",
    "whole_corpus_materialization_is_s05_s07_not_s05_closure",
    "cleaned_wire_remains_lossless_not_redescribed",
    "battery_counts_paths_hashes_only_no_decoded_text",
)

# ----------------------------------------------------------------- helpers #


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


# ------------------------------------------------------- parsing, fail-closed #


def parse_inventory(contract_text: str) -> dict[str, str]:
    """Parse the frozen-contract sha256 inventory block, fail-closed."""
    lines = contract_text.splitlines()
    try:
        start = lines.index(INVENTORY_BEGIN)
        stop = lines.index(INVENTORY_END, start + 1)
    except ValueError:
        pytest.fail(
            "battery: frozen-contract-inventory markers missing in the design contract",
            pytrace=False,
        )
    inventory: dict[str, str] = {}
    for raw in lines[start + 1 : stop]:
        stripped = raw.strip()
        if not stripped:
            continue
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


def parse_profile_block(contract_text: str) -> tuple[str, dict[str, tuple[str, str]]]:
    """Parse the machine-readable clean-rule-profile block, fail-closed.

    Returns ``(profile_id, rules)`` where ``rules`` maps every ReaderSemantic
    class to its pinned ``(rule_id, disposition)``.
    """
    lines = contract_text.splitlines()
    try:
        start = lines.index(PROFILE_BEGIN)
        stop = lines.index(PROFILE_END, start + 1)
    except ValueError:
        pytest.fail(
            "battery: clean-rule-profile markers missing in the design contract",
            pytrace=False,
        )
    profile_id: str | None = None
    rules: dict[str, tuple[str, str]] = {}
    for raw in lines[start + 1 : stop]:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("profile:"):
            assert profile_id is None, "battery: duplicate profile header line"
            profile_id = stripped.split(":", 1)[1].strip()
            continue
        fields: dict[str, str] = {}
        for part in stripped.split():
            key, sep, value = part.partition(":")
            assert sep, f"battery: malformed profile line {stripped!r}"
            fields[key] = value
        assert set(fields) == {"rule", "class", "disposition"}, (
            f"battery: malformed profile line {stripped!r}"
        )
        assert fields["class"] in EXPECTED_CLASSES, (
            f"battery: unknown class {fields['class']!r} in the profile block"
        )
        assert fields["disposition"] in VALID_DISPOSITIONS, (
            f"battery: unknown disposition {fields['disposition']!r} for {fields['class']!r}"
        )
        assert fields["class"] not in rules, (
            f"battery: duplicate profile line for class {fields['class']!r}"
        )
        rules[fields["class"]] = (fields["rule"], fields["disposition"])
    assert profile_id == PROFILE_ID, (
        f"battery: profile header must be {PROFILE_ID}, got {profile_id!r}"
    )
    assert set(rules) == set(EXPECTED_CLASSES), (
        f"battery: the profile block must be total over the seven classes, got {sorted(rules)}"
    )
    assert len({rule_id for rule_id, _ in rules.values()}) == len(EXPECTED_CLASSES), (
        "battery: profile rule ids must be unique"
    )
    return PROFILE_ID, rules


def parse_reader_clean_view_source(source_text: str) -> tuple[str, dict[str, tuple[str, str]]]:
    """Parse the pinned profile declarations out of reader_clean_view.rs."""
    statics: dict[str, tuple[str, str]] = {}
    for match in RUST_STATIC_RULE_RE.finditer(source_text):
        rust_class = match.group("class")
        assert rust_class in RUST_CLASS_TO_NAME, (
            f"battery: unknown ReaderSemantic::{rust_class} in reader_clean_view.rs"
        )
        class_name = RUST_CLASS_TO_NAME[rust_class]
        assert class_name not in statics, f"battery: duplicate static rule for {class_name}"
        disposition = RUST_DISPOSITION_TO_NAME.get(match.group("disposition"))
        assert disposition is not None, (
            f"battery: unknown CleanDisposition::{match.group('disposition')}"
        )
        statics[class_name] = (match.group("id"), disposition)
    assert set(statics) == set(EXPECTED_CLASSES), (
        f"battery: reader_clean_view.rs must pin one static rule per class, got {sorted(statics)}"
    )
    arms_raw = RUST_MATCH_ARM_RE.findall(source_text)
    assert len(arms_raw) == len(EXPECTED_CLASSES), (
        f"battery: rule_for must have exactly seven match arms, found {len(arms_raw)}"
    )
    assert all(arm in RUST_CLASS_TO_NAME for arm in arms_raw), (
        "battery: rule_for references an unknown ReaderSemantic class"
    )
    assert {RUST_CLASS_TO_NAME[arm] for arm in arms_raw} == set(EXPECTED_CLASSES), (
        "battery: rule_for is not a closed total match over the seven classes"
    )
    header = RUST_PROFILE_ID_RE.search(source_text)
    assert header is not None, (
        "battery: READER_CLEAN_PROFILE constant is missing from reader_clean_view.rs"
    )
    return header.group(1), statics


# ------------------------------------------------------------------ battery #


def run_battery() -> dict[str, Any]:
    """Run every battery check; raise before emitting anything on failure."""
    contract_text = read_text_or_fail(CONTRACT_PATH, "design contract")
    baseline = read_json_or_fail(BASELINE_PATH, "S03 baseline run")
    census = read_json_or_fail(CENSUS_PATH, "T03 census artifact")
    source_text = read_text_or_fail(CLEAN_VIEW_PATH, "reader_clean_view source")
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

    # The six section-2 files frozen since M222: pin their current hashes so
    # any later drift is detectable against this artifact.
    frozen_section2: list[dict[str, Any]] = []
    for relpath in FROZEN_SECTION2_RELPATHS:
        path = ROOT / relpath
        assert path.is_file(), f"battery: frozen section-2 file is missing: {relpath}"
        frozen_section2.append({"path": relpath, "sha256": sha256_of_file(path)})

    # (c) S03 baseline reconciliation.
    assert baseline.get("schema") == BASELINE_SCHEMA, (
        f"battery: unexpected baseline schema {baseline.get('schema')!r}"
    )
    counts = baseline.get("counts")
    assert isinstance(counts, dict), "battery: baseline carries no counts object"
    for key, expected in (
        ("entries", 43785),
        ("accepted", 43785),
        ("refused", 0),
        ("incomplete", 0),
    ):
        assert counts.get(key) == expected, (
            f"battery: S03 baseline counts.{key} must be {expected}, got {counts.get(key)!r}"
        )
    assert baseline.get("r1000_status") == "active/unclosed", (
        f"battery: R1000 must stay active/unclosed, got {baseline.get('r1000_status')!r}"
    )
    assert baseline.get("status") == "complete", (
        f"battery: the baseline run must be complete, got {baseline.get('status')!r}"
    )

    # (d) the profile block is total and matches the Rust declarations.
    block_profile_id, block_rules = parse_profile_block(contract_text)
    source_profile_id, source_rules = parse_reader_clean_view_source(source_text)
    assert block_profile_id == source_profile_id == PROFILE_ID, (
        f"battery: profile id drift: block={block_profile_id!r} source={source_profile_id!r}"
    )
    assert block_rules == source_rules, (
        "battery: profile drift between the machine-readable block and the "
        f"reader_clean_view.rs declarations: block={block_rules} source={source_rules}"
    )
    for class_name in REVISION_CLASSES:
        assert block_rules[class_name][1] != "dropped", (
            f"battery: revision class {class_name} may never be declared dropped"
        )
    assert block_rules["revision_insertion"][1] == "primary", (
        "battery: revision_insertion must stay primary (never silently discarded)"
    )
    assert block_rules["revision_deletion"][1] == "service", (
        "battery: revision_deletion must stay service (never silently discarded)"
    )
    dropped = sorted(name for name, (_, disp) in block_rules.items() if disp == "dropped")
    assert dropped == ["empty"], f"battery: only the empty class may drop, got {dropped}"

    # (e) the census artifact agrees with the profile and pins this contract.
    assert census.get("schema") == CENSUS_SCHEMA, (
        f"battery: unexpected census schema {census.get('schema')!r}"
    )
    assert census.get("profile_id") == PROFILE_ID, (
        f"battery: census profile id drift: {census.get('profile_id')!r}"
    )
    assert census.get("uncovered_classes") == [], (
        f"battery: census left real classes uncovered: {census.get('uncovered_classes')!r}"
    )
    assert census.get("contract_sha256") == contract_sha256, (
        "battery: the census pinned a different contract text — re-run the census "
        f"before trusting its coverage (census {census.get('contract_sha256')!r} "
        f"!= current {contract_sha256})"
    )

    return {
        "contract_sha256": contract_sha256,
        "frozen_contracts": frozen,
        "frozen_section2_files": frozen_section2,
        "profile_rules": {
            name: {"rule_id": rule_id, "disposition": disposition}
            for name, (rule_id, disposition) in sorted(block_rules.items())
        },
        "baseline": baseline,
        "census": census,
    }


def build_artifact(analysis: dict[str, Any]) -> dict[str, Any]:
    counts = analysis["baseline"]["counts"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "profile_id": PROFILE_ID,
        "non_claims": list(NON_CLAIMS),
        "contract_path": CONTRACT_RELPATH,
        "contract_sha256": analysis["contract_sha256"],
        "frozen_contracts": analysis["frozen_contracts"],
        "frozen_contracts_match_inventory": True,
        "frozen_section2_files": analysis["frozen_section2_files"],
        "s03_baseline_path": BASELINE_RELPATH,
        "s03_baseline_reconciled": {
            "entries": counts["entries"],
            "accepted": counts["accepted"],
            "refused": counts["refused"],
            "incomplete": counts["incomplete"],
            "r1000_status": analysis["baseline"]["r1000_status"],
        },
        "profile_block_total": True,
        "profile_class_count": len(EXPECTED_CLASSES),
        "profile_matches_reader_clean_view_source": True,
        "reader_clean_view_source_path": CLEAN_VIEW_RELPATH,
        "census_path": CENSUS_RELPATH,
        "census_profile_id": analysis["census"]["profile_id"],
        "census_uncovered_classes": analysis["census"]["uncovered_classes"],
        "census_contract_sha256_matches_contract": True,
        "redaction": "counts_paths_hashes_and_non_claims_only_no_decoded_text",
    }


def redaction_check(artifact: dict[str, Any]) -> None:
    """Fail closed before writing: only counts/hashes/paths/tokens may ship."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in FORBIDDEN_KEYS, f"battery: forbidden artifact key {key!r}"
                assert SAFE_STRING.match(key), f"battery: unsafe artifact key {key!r}"
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            assert SAFE_STRING.match(node), (
                f"battery: unsafe artifact string (redaction guard): {node[:80]!r}"
            )

    walk(artifact)


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
    assert counts["entries"] == counts["accepted"] == 43785
    assert counts["refused"] == 0
    assert counts["incomplete"] == 0
    assert battery["baseline"]["r1000_status"] == "active/unclosed"
    assert battery["baseline"]["status"] == "complete"


def test_profile_block_is_total_over_the_seven_classes(battery):
    rules = battery["profile_rules"]
    assert set(rules) == set(EXPECTED_CLASSES)
    assert rules["revision_insertion"]["disposition"] == "primary"
    assert rules["revision_deletion"]["disposition"] == "service"
    dropped = sorted(name for name, rule in rules.items() if rule["disposition"] == "dropped")
    assert dropped == ["empty"]
    assert len({rule["rule_id"] for rule in rules.values()}) == 7


def test_profile_block_matches_reader_clean_view_source_declarations(battery):
    # The source side is re-parsed here so a stale fixture can never hide drift.
    source_profile_id, source_rules = parse_reader_clean_view_source(
        CLEAN_VIEW_PATH.read_text(encoding="utf-8")
    )
    assert source_profile_id == PROFILE_ID
    block_rules = {
        name: (rule["rule_id"], rule["disposition"])
        for name, rule in battery["profile_rules"].items()
    }
    assert source_rules == block_rules


def test_census_artifact_agrees_with_the_profile(battery):
    census = battery["census"]
    assert census["uncovered_classes"] == []
    assert census["profile_id"] == PROFILE_ID
    assert census["contract_sha256"] == battery["contract_sha256"]
    for class_name in REVISION_CLASSES:
        assert isinstance(census.get(f"{class_name}_observed"), bool)


def test_battery_artifact_is_emitted_redacted_and_schema_versioned(battery):
    assert BATTERY_PATH.is_file(), "the battery artifact must exist after a green pass"
    artifact = json.loads(BATTERY_PATH.read_text(encoding="utf-8"))
    assert artifact["schema"] == SCHEMA
    assert artifact["version"] == VERSION
    assert artifact["profile_id"] == PROFILE_ID
    assert artifact["frozen_contracts_match_inventory"] is True
    assert artifact["profile_matches_reader_clean_view_source"] is True
    assert artifact["census_uncovered_classes"] == []
    assert "not_r1000_closure" in artifact["non_claims"]
    assert len(artifact["frozen_section2_files"]) == 6
    redaction_check(artifact)
