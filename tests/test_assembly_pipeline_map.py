"""Drift contract: ``prd/architecture/assembly-pipeline-map.md`` vs YAML.

``prd/architecture/kb-ontology.yaml`` (``assembly_fsm``) stays the canonical
authority; the tracked map is a human-readable mirror.  These tests fail
closed when a map edit silently drops or invents an FSM state, renames a
YAML state, raises a lifecycle tag above the honest ceiling, drops a
document-group profile, renames an L2 canon, weakens an explicit non-goal,
or points an evidence anchor at a path that no longer exists.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "prd" / "architecture" / "assembly-pipeline-map.md"
ONTOLOGY_PATH = ROOT / "prd" / "architecture" / "kb-ontology.yaml"

# A documentation mirror may carry [proposed]/[bounded]/[smoke] only; it can
# never promote itself or one of its state rows to [validated]/[adopted].
ALLOWED_LIFECYCLE_TAGS: tuple[str, ...] = ("[proposed]", "[bounded]", "[smoke]")
FORBIDDEN_LIFECYCLE_TAGS: tuple[str, ...] = ("[validated]", "[adopted]")

# Backticked repo-relative anchors the map may cite.  Gitignored proof
# surfaces (consru_export/) stay outside this contract on purpose.
ANCHOR_ROOTS: tuple[str, ...] = (
    "crates",
    "doc",
    "law-source",
    "prd",
    "scripts",
    "src",
    "tests",
)
_ANCHOR_RE = re.compile(r"`((?:" + "|".join(ANCHOR_ROOTS) + r")/[^`\s]+)`")
_STATE_ROW_RE = re.compile(r"^\|\s*`(S_[a-z0-9_]+)`\s*\|")
_GROUP_ROW_RE = re.compile(r"^\|\s*`([a-z_]+(?:@v1)?)`\s*\|", re.MULTILINE)


def _load_ontology() -> dict[str, Any]:
    with ONTOLOGY_PATH.open("r", encoding="utf-8") as handle:
        data: Any = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise AssertionError(f"ontology root is not a mapping: {type(data)!r}")
    return data


def _map_text() -> str:
    return MAP_PATH.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")][1:-1]


def _state_rows(text: str) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = _STATE_ROW_RE.match(line)
        if match:
            rows.append((match.group(1), _cells(line)))
    return rows


def _section(text: str, heading_needle: str) -> str:
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("## ") and heading_needle in line),
        None,
    )
    assert start is not None, f"heading not found: {heading_needle!r}"
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def _fsm_table_row(text: str, label: str, key: str) -> str:
    for line in _section(text, "Assembly FSM vs readiness").splitlines():
        if line.startswith(f"| {label}") and f"`{key}`" in line:
            return line
    raise AssertionError(f"table row for {label} (`{key}`) not found")


def _lifecycle_violations(lifecycle_cell: str) -> list[str]:
    violations: list[str] = []
    if not any(f"`{tag}`" in lifecycle_cell for tag in ALLOWED_LIFECYCLE_TAGS):
        violations.append("no allowed lifecycle tag ([proposed]/[bounded]/[smoke])")
    violations.extend(
        f"forbidden lifecycle tag {tag}"
        for tag in FORBIDDEN_LIFECYCLE_TAGS
        if tag in lifecycle_cell
    )
    return violations


def _non_claim_strings(values: list[Any]) -> list[str]:
    # YAML quirk: a plain scalar containing ": " parses as a single-pair
    # mapping ("current S_ready_bounded: ..."); rebuild "key: value".
    out: list[str] = []
    for value in values:
        if isinstance(value, dict):
            out.extend(f"{key}: {inner}" for key, inner in value.items())
        else:
            out.append(str(value))
    return out


def test_map_declares_the_yaml_as_canonical_source() -> None:
    assert "Canonical authority: `prd/architecture/kb-ontology.yaml`" in _map_text()


def test_state_table_is_exactly_the_yaml_assembly_fsm() -> None:
    ontology = _load_ontology()
    states: dict[str, Any] = ontology["assembly_fsm"]["states"]
    rows = _state_rows(_map_text())

    assert rows, "state table has no `S_*` rows"
    map_ids = [state_id for state_id, _ in rows]
    assert len(map_ids) == len(set(map_ids)), "duplicate state rows in the map"

    assert set(map_ids) == set(states), (
        "map/YAML state drift: "
        f"missing={sorted(set(states) - set(map_ids))} "
        f"extra={sorted(set(map_ids) - set(states))}"
    )

    for state_id, cells in rows:
        assert len(cells) == 8, f"{state_id}: expected 8 table cells, got {len(cells)}"
        yaml_name = states[state_id]["name"]
        assert cells[1].strip("`") == yaml_name, (
            f"{state_id}: map name {cells[1]!r} != YAML name {yaml_name!r}"
        )


def test_map_quotes_the_yaml_fsm_heads() -> None:
    ontology = _load_ontology()
    assembly: dict[str, Any] = ontology["assembly_fsm"]
    readiness: dict[str, Any] = ontology["fsm"]
    text = _map_text()

    assert f"`name: {assembly['name']}`" in text
    assert f"`initial: {assembly['initial']}`" in text
    assert f"`current: {assembly['current']}`" in text

    assembly_row = _fsm_table_row(text, "Assembly", "assembly_fsm")
    assert f"`{assembly['initial']}`" in assembly_row
    assert f"`{assembly['current']}`" in assembly_row

    readiness_row = _fsm_table_row(text, "Readiness", "fsm")
    assert f"`{readiness['initial']}`" in readiness_row
    assert f"`{readiness['current']}`" in readiness_row
    for terminal in readiness["terminal"]:
        assert f"`{terminal}`" in readiness_row


def test_state_rows_never_raise_a_lifecycle_tag() -> None:
    text = _map_text()
    rows = _state_rows(text)
    assert rows
    for state_id, cells in rows:
        violations = _lifecycle_violations(cells[4])
        assert not violations, f"{state_id}: {violations} (lifecycle cell: {cells[4]!r})"
    for tag in FORBIDDEN_LIFECYCLE_TAGS:
        assert tag not in text, f"the map promotes a lifecycle to {tag}"


def test_profile_table_is_exactly_the_yaml_document_groups() -> None:
    ontology = _load_ontology()
    yaml_ids = [group["id"] for group in ontology["document_groups"]["groups"]]
    section = _section(_map_text(), "Document-group profiles")
    map_ids = _GROUP_ROW_RE.findall(section)
    assert set(map_ids) == set(yaml_ids), (
        f"profile drift: missing={sorted(set(yaml_ids) - set(map_ids))} "
        f"extra={sorted(set(map_ids) - set(yaml_ids))}"
    )
    assert len(map_ids) == len(set(map_ids)), "duplicate profile rows"


def test_three_l2_canons_are_named_in_the_canon_section() -> None:
    section = _section(_map_text(), "three L2 canons")
    for name in (
        "fold_membership_at",
        "fold_expression_presence",
        "filter_ast_to_expression",
        "resolve_ctv",
        "edition_ast_at",
    ):
        assert name in section, f"L2 canon {name} missing from the canon section"


def test_non_goals_name_the_five_boundaries() -> None:
    section = _section(_map_text(), "Explicit non-goals")
    for heading in (
        "Fold cache",
        "Schedule / agent runtime",
        "Durable event store",
        "Force runtime",
        "Applicable runtime",
    ):
        assert heading in section, f"non-goal {heading!r} missing"


def test_yaml_assembly_non_claims_are_quoted_verbatim() -> None:
    ontology = _load_ontology()
    normalized = " ".join(_map_text().split())
    for claim in _non_claim_strings(ontology["assembly_fsm"]["non_claims"]):
        assert claim in normalized, f"non-claim not quoted verbatim: {claim!r}"


def test_backticked_evidence_anchors_exist_in_the_repo() -> None:
    anchors = sorted({match.group(1).split("::")[0] for match in _ANCHOR_RE.finditer(_map_text())})
    assert anchors, "no repo-relative anchors matched; extractor rot?"
    missing = [anchor for anchor in anchors if not (ROOT / anchor).exists()]
    assert missing == [], f"dead evidence anchors: {missing}"


def test_lifecycle_detector_flags_synthetic_drift() -> None:
    raised = _cells("| `S_x` | x | x | x | `[validated]` | e | g | a |")[4]
    assert _lifecycle_violations(raised) == [
        "no allowed lifecycle tag ([proposed]/[bounded]/[smoke])",
        "forbidden lifecycle tag [validated]",
    ]

    untagged = _cells("| `S_x` | x | x | x | executed | e | g | a |")[4]
    assert _lifecycle_violations(untagged) == [
        "no allowed lifecycle tag ([proposed]/[bounded]/[smoke])",
    ]

    honest = _cells("| `S_x` | x | x | x | `[bounded]` (fixture); `[smoke]` | e | g | a |")[4]
    assert _lifecycle_violations(honest) == []


def test_state_row_extraction_reports_set_drift_on_synthetic_map() -> None:
    synthetic = "\n".join(
        [
            "| State | name | meaning | status | lifecycle | evidence | gap | anchor |",
            "|---|---|---|---|---|---|---|---|",
            "| `S_a` | a | a | a | `[bounded]` | e | g | a |",
            "| `S_b` | b | b | b | `[bounded]` | e | g | a |",
        ]
    )
    ids = {state_id for state_id, _ in _state_rows(synthetic)}
    assert ids == {"S_a", "S_b"}
    assert ids - {"S_a", "S_c"} == {"S_b"}  # dropped/extra YAML states surface here
