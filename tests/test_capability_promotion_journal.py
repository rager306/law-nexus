"""Drift contract: TSG-017 promotion journal on the capability board (M173 S03).

T01 recorded packet D204 on ``prd/architecture/capability-promotion-board.md``:
TSG-017 moved from the stale S0–S1 cell to the honest S3 ``bounded_runtime``
ceiling via two class-matched append-only history steps (2026-08-16 S0–S1→S2
M169 implementation spine; 2026-08-18 S2→S3 M169–M171 bounded runtime), plus
a §5c journal with the de Martim v5 scorecard, the 44-ФЗ edition axis, the
cross-act C1 axis, and support-act anchors for the five M171 document_groups.

These tests fail closed when a board edit regresses that journal: TSG-017
rolls back to S0–S1, the ceiling is inflated to S4/S6, the append-only
history loses or rewrites a D204 step, a scorecard axis disappears, or the
governor advisory ``capability-promotion-board`` turns red on TSG id
coverage. The full governor run is deliberately not acceptance here — only
this one advisory check is pinned, per the M173 S03 slice contract.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from law_nexus_harness.governor import check_capability_promotion_board

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "prd" / "architecture" / "capability-promotion-board.md"

# D204 append-only contract: journal steps land strictly after the
# pre-existing 2026-08-14 wave; the 2026-08-13 intake row must survive.
_JOURNAL_CUTOFF = date(2026, 8, 14)
_TSG017_HISTORY_DATES = (
    date(2026, 8, 13),
    date(2026, 8, 16),
    date(2026, 8, 18),
    date(2026, 8, 20),
)

# §5c de Martim v5 scorecard axes (Review 5, review-14-08-2026.md §1) with
# the law-nexus column pinned; a doc edit may not silently rescore.
_SCORECARD_AXES = (
    "Theory completeness (clocks, canons, cross-act)",
    "Executability (Rust pipeline on live XML)",
    "CTV text reconstruction (`resolve_CTV`)",
    "Validated amendment corpus",
    "Formal ontology (LRMoo/ELI/AKN)",
    "Engineering maturity (TDD, hex, Governor, D098)",
)
_SCORECARD_LAW_NEXUS_SCORES = ("**8/10**", "**7/10**", "2.5/10", "3/10", "5/10", "**7/10**")

# Five M171 document_groups that must each carry a support-act anchor row.
_DOCUMENT_GROUPS = (
    "federal_law@v1",
    "code",
    "government_resolution",
    "departmental_order",
    "court_practice",
)

_BOARD_TABLE_COLUMNS = 5
_HISTORY_COLUMNS = 5


def _board_text() -> str:
    return BOARD_PATH.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _section(heading_prefix: str) -> str:
    """Body of the heading starting with ``heading_prefix`` until the next
    heading at the same or lower level (fail-closed on a missing heading)."""
    lines = _board_text().splitlines()
    start = None
    level = 0
    for idx, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = idx
            level = len(line) - len(line.lstrip("#"))
            break
    assert start is not None, f"board heading not found: {heading_prefix!r}"
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")][1:-1]


def _board_table_row(tsg: str) -> list[str]:
    matches = [ln for ln in _board_text().splitlines() if ln.startswith(f"| {tsg} |")]
    assert len(matches) == 1, f"expected exactly one {tsg} board row, found {len(matches)}"
    row = _cells(matches[0])
    assert len(row) == _BOARD_TABLE_COLUMNS, (
        f"{tsg}: expected {_BOARD_TABLE_COLUMNS} board cells, got {len(row)}"
    )
    return row


def _history_rows() -> list[list[str]]:
    section = _section("### Promotion history (append-only)")
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = _cells(line)
        if cells and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            assert len(cells) == _HISTORY_COLUMNS, (
                f"history row must have {_HISTORY_COLUMNS} cells: {line!r}"
            )
            rows.append(cells)
    return rows


def _tsg017_history() -> list[list[str]]:
    rows = [row for row in _history_rows() if row[1] == "TSG-017"]
    assert len(rows) == 4, f"expected 4 TSG-017 history rows, found {len(rows)}"
    return rows


def _tsg017_ceiling_violations(ladder_cell: str) -> list[str]:
    violations: list[str] = []
    if "**S3**" not in ladder_cell:
        violations.append("board ladder cell is not bold S3")
    if "bounded_runtime" not in ladder_cell:
        violations.append("bounded_runtime ceiling tag missing")
    for inflated in ("S4", "S5", "S6"):
        if inflated in ladder_cell:
            violations.append(f"ceiling inflated past S3: {inflated}")
    for stale in ("S0", "S1", "S2"):
        if re.search(rf"\b{stale}\b", ladder_cell):
            violations.append(f"stale pre-S3 state present: {stale}")
    return violations


def test_board_row_pins_tsg017_at_s3_bounded_runtime() -> None:
    row = _board_table_row("TSG-017")
    assert _tsg017_ceiling_violations(row[1]) == [], "TSG-017 ladder drifted from S3 ceiling"
    # Progress notes stay tied to the M169–M171 packet and the §5c journal.
    assert "M169–M171 packet" in row[2] and "§5c journal" in row[2], row[2]
    # The honest next step is representative multi-edition replay + human
    # scope (S4/S5) with the CTV product gap still open — never S6.
    assert "S4/S5" in row[4], row[4]
    assert "`resolve_CTV` product open" in row[4], row[4]


def test_history_records_class_matched_steps_after_cutoff() -> None:
    intake, step_s2, step_s3, step_ctv = _tsg017_history()
    dates = [date.fromisoformat(row[0]) for row in (intake, step_s2, step_s3, step_ctv)]
    assert dates == list(_TSG017_HISTORY_DATES), f"TSG-017 history dates drifted: {dates}"
    # Append-only: the three D204 rows survive unwritten.
    # Append-only: the pre-cutoff Review-4 intake row survives unwritten…
    assert intake[2] == "→ **S0–S1**", intake[2]
    # …and both D204 steps land strictly after the 2026-08-14 wave.
    assert dates[1] > _JOURNAL_CUTOFF and dates[2] > _JOURNAL_CUTOFF
    # Step 1 (2026-08-16): M169 implementation spine on real corpus paths.
    assert step_s2[2] == "S0–S1 → **S2**", step_s2[2]
    assert "M169 implementation spine" in step_s3[3] or "M169 implementation spine" in step_s2[3]
    assert "`consru_export`" in step_s2[3] and "GSD M169" in step_s2[4], step_s2
    # Step 2 (2026-08-18): M169–M171 bounded runtime, drift=0 replay anchors.
    assert step_s3[2] == "S2 → **S3**", step_s3[2]
    for anchor in ("M169–M171", "402-ФЗ", "edition-0118", "0080→0081", "drift=0"):
        assert anchor in step_s3[3], f"step-2 evidence anchor missing: {anchor}"
    assert "D204" in step_s3[4], step_s3[4]


def test_history_records_intra_s3_ctv_step() -> None:
    """M172 S03 (D214): intra-S3 class-matched CTV step, not an S4 promotion."""
    step_ctv = _tsg017_history()[3]
    assert step_ctv[0] == "2026-08-20", step_ctv
    assert step_ctv[2] == "S3 (class-matched CTV step)", step_ctv[2]
    assert "S3 → **S4**" not in step_ctv[2], "ceiling inflated to S4"
    for anchor in (
        "PP_60",
        "inspect",
        "punkt",
        "ctv_resolved>0",
        "membership_committed=0",
        "fixture-CC",
    ):
        assert anchor in step_ctv[3], f"intra-S3 CTV step anchor missing: {anchor}"
    assert "D214" in step_ctv[4] and "M172" in step_ctv[4], step_ctv[4]


def test_punkt_subunit_ctv_axis_pinned() -> None:
    """§5c names the Punkt/subunit text-CTV axis with the S3 ceiling intact."""
    journal = _normalized(_section("### Punkt/subunit text-CTV axis"))
    # The heading itself carries the axis name; body carries the contract.
    assert "Punkt/subunit text-CTV axis" in _board_text(), "axis heading missing"
    for phrase in (
        "**not** a promotion to S4",
        "`PP_60` YAML mint level = punkt granularity",
        "(D208, unexpanded)",
        "`ctv_resolved>0`",
        "`membership_committed=0`",
        "fixture-CC local only",
        "ADR-0017 (stays `[proposed]`)",
    ):
        assert phrase in journal, f"axis phrase missing: {phrase!r}"
    # §5 as-of keeps the M172 append named without raising the ceiling.
    board = _normalized(_board_text())
    assert "M172 S03 appends the intra-S3 class-matched CTV step (2026-08-20)" in board
    # Support-acts government_resolution names the inspect/ctv_resolved surface.
    assert "inspect: YAML granularity punkt, ctv_resolved>0" in board


def test_journal_section_declares_ceiling_and_non_authority() -> None:
    journal = _normalized(_section("## 5c."))
    for phrase in (
        "Ceiling is **S3 `bounded_runtime`**",
        "not S4",
        "not S6",
        "TSG-003/TSG-013 stay S3",
        "does not close TSG rows",
        "D204",
    ):
        assert phrase in journal, f"§5c journal phrase missing: {phrase!r}"
    # §5 as-of line names the M171 closeout revision and the journal packet.
    board = _normalized(_board_text())
    assert "M171 final `db8d1db`" in board, "§5 as-of M171 revision anchor missing"
    assert "TSG-017 journal recorded at S3 (§5c, D204 packet)" in board


def test_de_martim_v5_scorecard_pinned() -> None:
    journal = _normalized(_section("## 5c."))
    assert "de Martim v5 scorecard" in journal
    assert "`doc/review/review-14-08-2026.md`" in journal, "Review 5 source link missing"
    for axis in _SCORECARD_AXES:
        assert axis in journal, f"scorecard axis missing: {axis!r}"
    for score in _SCORECARD_LAW_NEXUS_SCORES:
        assert score in journal, f"law-nexus score missing: {score!r}"
    # Kept-ahead / still-behind axes stay explicit (Review 5 §1b/§1c).
    for phrase in ("5 clocks", "cross-act edges", "`resolve_CTV` product", "ELI/AKN mapping"):
        assert phrase in journal, f"scorecard ahead/behind phrase missing: {phrase!r}"


def test_edition_axis_pinned() -> None:
    journal = _normalized(_section("## 5c."))
    for anchor in (
        "12-state `assembly_fsm` on edition-0118",
        "propose=94 / commit=94",
        "8 roots / 102 nodes",
        "`ctv_resolved=102`, drift=0",
        "replay 0080→0081 (476-ФЗ purge)",
        "drafts=81, added=24 / removed=57",
        "text-only probe 0001→0002",
        "oracle assert, not a replay proof",
        "no 118-edition verify",
        "process truth, not legal truth (D116/D117)",
    ):
        assert anchor in journal, f"edition-axis anchor missing: {anchor!r}"


def test_cross_act_c1_axis_pinned() -> None:
    journal = _normalized(_section("## 5c."))
    assert "`doc/review/review-16-08-2026.md`" in journal, "Review 7 source link missing"
    assert "138-ФЗ" in journal and "ст. 31/43" in journal
    assert "333-ФЗ" in journal and "ст. 95" in journal
    assert "real C1 edge executed (KBO-R049 S1)" in journal
    assert "484-ФЗ" in journal and "acquired; edge not executed" in journal


def test_support_acts_cover_five_document_groups() -> None:
    section = _section("### Support acts by document_group")
    rows = {
        _cells(line)[0].strip("`"): _cells(line)
        for line in section.splitlines()
        if line.startswith("|") and not set(line) <= set("|-: ") and not line.startswith("| doc")
    }
    assert set(rows) == set(_DOCUMENT_GROUPS), (
        f"support-act groups drifted: {sorted(set(rows) ^ set(_DOCUMENT_GROUPS))}"
    )
    # Executed-proof column keeps the honest distinctions per group.
    assert (
        "402-ФЗ" in rows["federal_law@v1"][1] and "44-ФЗ edition-0118" in rows["federal_law@v1"][1]
    )
    assert "`S_ready_bounded`" in rows["federal_law@v1"][2]
    assert "145-ФЗ" in rows["code"][1] and "catalog-only" in rows["code"][2]
    assert "PP_60" in rows["government_resolution"][1]
    assert "приказ № 45" in rows["departmental_order"][1]
    assert "inline fixture" in rows["departmental_order"][2]
    assert "ADR-0020" in rows["court_practice"][1], rows["court_practice"][1]
    assert "probe-only" in rows["court_practice"][2], rows["court_practice"][2]
    # D205: the on-disk приказ stays a disk fact, not an executed run.
    journal = _normalized(_section("## 5c."))
    assert "disk fact, not an executed run" in journal
    assert "`prd/architecture/assembly-pipeline-map.md` §5" in journal, "map authority link missing"


def test_neighbors_tsg003_tsg013_stay_s3() -> None:
    for tsg in ("TSG-003", "TSG-013"):
        ladder = _board_table_row(tsg)[1]
        assert "**S3**" in ladder, f"{tsg} ladder drifted below S3: {ladder!r}"
        assert "S6" not in ladder, f"{tsg} ladder inflated to S6: {ladder!r}"
    board = _normalized(_board_text())
    assert "No row advanced to S6 in the spine wave" in board


def test_governor_advisory_covers_tsg_ids() -> None:
    findings = check_capability_promotion_board(ROOT)
    assert len(findings) == 1, f"expected one advisory finding, got {len(findings)}"
    finding = findings[0]
    assert finding.check_id == "capability-promotion-board"
    assert finding.status == "pass", f"advisory red on TSG id coverage: {finding.observed}"
    assert finding.severity == "ok"
    assert "missing_on_board=0" in finding.observed


def test_ceiling_detector_flags_synthetic_regressions() -> None:
    legacy = "S0–S1 partial"
    assert _tsg017_ceiling_violations(legacy) == [
        "board ladder cell is not bold S3",
        "bounded_runtime ceiling tag missing",
        "stale pre-S3 state present: S0",
        "stale pre-S3 state present: S1",
    ]
    inflated = "**S4** (`representative_evidence`)"
    assert _tsg017_ceiling_violations(inflated) == [
        "board ladder cell is not bold S3",
        "bounded_runtime ceiling tag missing",
        "ceiling inflated past S3: S4",
    ]
    closed = "**S6** (`closed_bounded`)"
    assert _tsg017_ceiling_violations(closed) == [
        "board ladder cell is not bold S3",
        "bounded_runtime ceiling tag missing",
        "ceiling inflated past S3: S6",
    ]
    honest = "**S3** (`bounded_runtime`)"
    assert _tsg017_ceiling_violations(honest) == []
