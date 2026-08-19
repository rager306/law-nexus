"""Drift contract: M171 closeout alignment of the living oracle.

M171 S04 T03 deliberately kept a conservative leftover in
``prd/ARCHITECTURE.md`` — "Recursive walk, CC-path identity and
StructuralNearMiss census remain ``[proposed]``" — while M171 S02/S03 had
already executed those mechanics ``[bounded]``.  M173 S02 replaced that
leftover with the M171 current-fact and recorded the same current-fact in
the TSG-017 lifecycle cell without closing the row.

These tests fail closed when an oracle edit regresses that alignment: the
"census remain" leftover returns, a bounded mechanics claim disappears, the
document_groups/parsed_as vocabulary loses its ``[bounded]`` ceiling, the
one-page budget breaks, or TSG-017 drifts back to presenting the historical
Review 4 design inventory as the current lifecycle (or is closed outright,
which the register's own disposition rules forbid from a doc edit).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_PATH = ROOT / "prd" / "ARCHITECTURE.md"
REGISTER_PATH = ROOT / "prd" / "architecture" / "temporal-semantic-gap-register.md"

# M173 S02 Must-Have: the living oracle stays a one-pager (<= 325 lines).
ARCHITECTURE_LINE_BUDGET = 325

# A documentation mirror may never promote a lifecycle past [bounded]/[smoke].
FORBIDDEN_LIFECYCLE_TAGS: tuple[str, ...] = ("[validated]", "[adopted]")

# Register columns: Gap ID | capability | class | owner | Current lifecycle |
# non-claim | closure trigger | status.
_LIFECYCLE_COLUMN = 4
_NON_CLAIM_COLUMN = 5
_CLOSURE_COLUMN = 6
_STATUS_COLUMN = 7


def _architecture_text() -> str:
    return ARCHITECTURE_PATH.read_text(encoding="utf-8")


def _register_text() -> str:
    return REGISTER_PATH.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")][1:-1]


def _tsg017_row() -> list[str]:
    lines = [line for line in _register_text().splitlines() if line.startswith("| TSG-017 ")]
    assert len(lines) == 1, f"expected exactly one TSG-017 row, found {len(lines)}"
    row = _cells(lines[0])
    assert len(row) == 8, f"TSG-017: expected 8 table cells, got {len(row)}"
    return row


def _tsg017_lifecycle_violations(cell: str) -> list[str]:
    violations: list[str] = []
    if "design inventory (Review 4)" in cell:
        violations.append("historical Review 4 inventory presented as current lifecycle")
    if "historical" not in cell:
        violations.append("lifecycle cell does not mark the Review 4 inventory historical")
    if "`[bounded]`" not in cell:
        violations.append("no [bounded] current-fact for the executed M171 mechanics")
    if "`S_ready_bounded`" not in cell:
        violations.append("S_ready_bounded assembly anchor missing")
    violations.extend(
        f"forbidden lifecycle tag {tag}" for tag in FORBIDDEN_LIFECYCLE_TAGS if tag in cell
    )
    return violations


def test_architecture_drops_the_m171_leftover_proposed_claim() -> None:
    # The exact M171 S04 leftover sentence must not come back.
    assert "census remain" not in _architecture_text()


def test_architecture_states_m171_mechanics_as_bounded() -> None:
    normalized = " ".join(_architecture_text().split())
    for phrase in (
        "Recursive walk is `[bounded]` on the subordinate act corpus",
        "(44-ФЗ registry stays a flat anchor, D192)",
        "CC-path identity",
        "`cc:work:statya-93/punkt-4/punkt-4.2`, D191",
        "StructuralNearMiss census → human-apply loop (D194) are `[bounded]`",
    ):
        assert phrase in normalized, f"M171 bounded mechanics claim missing: {phrase!r}"


def test_architecture_keeps_document_groups_and_parsed_as_bounded() -> None:
    normalized = " ".join(_architecture_text().split())
    for phrase in (
        "(`kb-ontology.yaml` `document_groups:`) are `[bounded]` YAML vocabulary",
        "`Work ──(parsed_as)──▶ DocumentGroupRef{group, catalog_version}`",
        "FNV-1a 64 catalog section hash",
    ):
        assert phrase in normalized, f"S01 map alignment phrase missing: {phrase!r}"


def test_architecture_page_budget_holds() -> None:
    line_count = len(_architecture_text().splitlines())
    assert line_count <= ARCHITECTURE_LINE_BUDGET, (
        f"living oracle grew to {line_count} lines (budget {ARCHITECTURE_LINE_BUDGET})"
    )


def test_tsg017_row_stays_active_with_current_fact() -> None:
    row = _tsg017_row()
    violations = _tsg017_lifecycle_violations(row[_LIFECYCLE_COLUMN])
    assert not violations, f"TSG-017 lifecycle drift: {violations}"
    # A documentation edit may not close the row (M173 S02 sketch forbids close).
    assert row[_STATUS_COLUMN] == "active", f"TSG-017 status must stay active: {row[-1]!r}"


def test_tsg017_non_claim_and_closure_trigger_survive() -> None:
    row = _tsg017_row()
    assert "not legislative history" in row[_NON_CLAIM_COLUMN]
    assert "fold projection is not CTV text" in row[_NON_CLAIM_COLUMN]
    assert "C0/C1" in row[_CLOSURE_COLUMN]


def test_lifecycle_detector_flags_synthetic_regression() -> None:
    legacy = "`[proposed]` design inventory (Review 4); Review 5 adds oracle diff (KBO-R047)"
    assert _tsg017_lifecycle_violations(legacy) == [
        "historical Review 4 inventory presented as current lifecycle",
        "lifecycle cell does not mark the Review 4 inventory historical",
        "no [bounded] current-fact for the executed M171 mechanics",
        "S_ready_bounded assembly anchor missing",
    ]

    promoted = "single Consultant-act assembly is `[validated]` at `S_ready_bounded`"
    assert _tsg017_lifecycle_violations(promoted) == [
        "lifecycle cell does not mark the Review 4 inventory historical",
        "no [bounded] current-fact for the executed M171 mechanics",
        "forbidden lifecycle tag [validated]",
    ]

    honest = (
        "Review 4 inventory is historical; single Consultant-act assembly is "
        "`[bounded]` at `S_ready_bounded`; resolve_CTV (KBO-R046) remains open"
    )
    assert _tsg017_lifecycle_violations(honest) == []


def test_register_has_no_second_tsg017_projection() -> None:
    # The sketch allows exactly one current-fact line: the single TSG-017 row
    # in the active-gaps table, not a duplicated projection elsewhere.
    matches = re.findall(r"^\| TSG-017 \|", _register_text(), flags=re.MULTILINE)
    assert len(matches) == 1, f"expected one TSG-017 row, found {len(matches)}"
