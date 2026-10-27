"""Mechanical pins for the post-ship pointers (M002 task T004, SC4).

After the M001 ship every pointer a fresh agent reads must describe the
shipped world. The roadmap three-way identity (STATE.md = roadmap.json =
the live marker bullet) and the dated superseded M001 bullet are pinned by
tests/test_project_state_roadmap_freshness.py; this module pins the rest:
the exact current_milestone projection, the crosswalk M225 closure row
(updated in place, never deleted — E6), the DOCS-AUDIT queue rows that
reference their closing M001 task ids, the dated post-ship report that
supersedes the pre-ship cutover snapshot together with its Contract D
"Fresh-session bootstrap" section, and the AGENTS.md / AGENT_HANDOFF.md
pointers at the report. The pre-ship snapshot must still exist — N4 keeps
it untouched as the dated record.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROADMAP_JSON = REPO / "prd" / "project-state" / "data" / "roadmap.json"
CROSSWALK = REPO / "docs" / "agent-stack" / "history" / "LEGACY_CROSSWALK.md"
DOCS_AUDIT = REPO / ".project" / "research" / "DOCS-AUDIT.md"
REPORT = REPO / "docs" / "agent-stack" / "POST-SHIP-STATE-2026-10-27.md"
PRE_SHIP_SNAPSHOT = REPO / "docs" / "agent-stack" / "CUTOVER-READINESS-M001.md"
AGENTS = REPO / "AGENTS.md"
AGENT_HANDOFF = REPO / "docs" / "agent-stack" / "AGENT_HANDOFF.md"

M225_RECEIPT = "prd/migration/rust-evidence/m225-validation-rerun-m001.json"
M225_VERDICT = "hermetic-pass-parity-unproven"

BOOTSTRAP_HEADING = "## Fresh-session bootstrap"
# The restore procedure (vendored archive extraction + the installer's
# --runtime-restore) then the three verification commands, in this order.
BOOTSTRAP_COMMANDS = (
    "tar -xzf .ai/vendor/gsd-path-1.6.2.tgz",
    "--runtime-restore",
    "python3 scripts/ai/path-run.py status",
    "uv run --frozen python -m law_nexus_harness.governor",
    "uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q",
)
PROOF_FILE = "M002-ACCEPTANCE-PROOF.md"


def _user_rulings_rows() -> list[list[str]]:
    """Parse the DOCS-AUDIT "User rulings" table into 4-cell rows."""
    text = DOCS_AUDIT.read_text(encoding="utf-8")
    start = text.index("## User rulings")
    section = text[start:]
    section = section[: section.index("\n## ", 1)]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            rows.append(cells)
    return rows


def test_roadmap_json_current_milestone_is_the_exact_m002_projection() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    assert roadmap["current_milestone"] == {"id": "post-ship-hardening", "status": "active"}, (
        "roadmap.json current_milestone must be exactly the M002 projection "
        '{"id": "post-ship-hardening", "status": "active"} (T004 AC1)'
    )


def test_crosswalk_m225_row_records_the_t004_closure() -> None:
    """E6: the M225 row is updated in place, never deleted, and links the receipt."""
    rows = [
        line
        for line in CROSSWALK.read_text(encoding="utf-8").splitlines()
        if line.startswith("| M225-qrwdfv ")
    ]
    assert len(rows) == 1, (
        f"expected exactly one M225-qrwdfv obligations row in the crosswalk, found {len(rows)}"
    )
    row = rows[0]
    assert "T004" in row, "the row must record that the residual was closed by T004"
    assert M225_RECEIPT in row, "the row must link the T004 rerun receipt"
    assert M225_VERDICT in row, "the row must record the rerun verdict"
    assert "corpus parity remains unproven" in row, (
        "the row must state that corpus parity remains unproven (E6)"
    )


def test_docs_audit_queue_rows_reference_their_closing_tasks() -> None:
    rows = {int(cells[0]): cells for cells in _user_rulings_rows()}
    assert set(rows) == set(range(1, 20)), (
        "the DOCS-AUDIT rulings queue must keep all 19 rows (never deleted)"
    )
    assert rows[6][1] == "fix-code" and rows[6][3] == "T005"
    assert rows[19][1] == "fix-code" and rows[19][3] == "T005"
    assert rows[9][1] == "fix-code" and rows[9][3] == "T006"


def test_post_ship_report_supersedes_the_pre_ship_snapshot() -> None:
    assert REPORT.exists(), f"the dated post-ship report is missing: {REPORT}"
    assert PRE_SHIP_SNAPSHOT.exists(), (
        "the pre-ship cutover snapshot must remain as the dated record (N4)"
    )
    text = REPORT.read_text(encoding="utf-8")
    assert "2026-10-27" in text, "the report must be dated 2026-10-27"
    assert "CUTOVER-READINESS-M001.md" in text, "the report must state which document it supersedes"
    lowered = text.lower()
    assert "supersedes" in lowered and "current-state" in lowered


def test_report_carries_the_fresh_session_bootstrap_contract() -> None:
    """Contract D: the exact bootstrap commands, in order, plus the proof rule."""
    text = REPORT.read_text(encoding="utf-8")
    assert BOOTSTRAP_HEADING in text, "the Fresh-session bootstrap section is missing"
    section = text[text.index(BOOTSTRAP_HEADING) :]
    section = section[: section.index("\n## ", 1)]

    positions = []
    for command in BOOTSTRAP_COMMANDS:
        position = section.find(command)
        assert position != -1, f"bootstrap command missing from the report: {command!r}"
        positions.append(position)
    assert positions == sorted(positions), (
        "the bootstrap section must list the restore procedure and then the "
        "three verification commands, in order"
    )
    assert PROOF_FILE in section and ".project/build" in section, (
        "the bootstrap section must send every real command output to the "
        "proof file in the pipeline .project/build/ workspace"
    )


def test_agent_entry_points_point_at_the_report() -> None:
    for path in (AGENTS, AGENT_HANDOFF):
        assert "POST-SHIP-STATE-2026-10-27.md" in path.read_text(encoding="utf-8"), (
            f"{path.name} must point at the current-state document"
        )
