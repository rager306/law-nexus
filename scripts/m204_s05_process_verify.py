#!/usr/bin/env python3
"""Process-only verifier for the documented M073 residue waiver."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAIVER = ROOT / "prd/migration/rust-evidence/m204-s05-m073-residue-waiver.json"

EXPECTED_TASKS = {"T01", "T02", "T03", "T04"}
EXPECTED_DEFECTS = {
    "claim_dispatch_desync": "not_fixed",
    "gate_completed_no_advance": "not_fixed",
}
FORBIDDEN_TERMS = (
    "gsd.db",
    "gsd_skip_slice",
    "gsd_slice_reopen",
    "gsd_task_reopen",
    "gsd_task_complete",
)


def main() -> int:
    data = json.loads(WAIVER.read_text(encoding="utf-8"))
    assert data["schema"] == "m204-s05-m073-residue-waiver/v1"
    assert data["kind"] == "documentation-only-waiver"

    observation = data["observation"]
    assert observation["source_is_fresh_db_query"] is False
    assert observation["source_is_tracked_snapshot"] is True
    assert observation["external_paths_read"] is False
    assert observation["direct_database_access"] is False
    assert observation["source"].startswith(
        "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json"
    )

    residue = data["residue"]
    assert residue["milestone"] == "M073-68ysz1"
    assert residue["slice"] == "S01"
    assert set(residue["tasks"]) == EXPECTED_TASKS
    assert residue["archive_surface"] == "python_archive/product/LegalDomain"
    assert residue["parent_status"] == "complete"
    assert residue["delivery"] == "none"
    assert residue["review_finding"] == "DT-orphan-gsd"
    assert residue["scope"] == "blocked-in-scope"
    assert residue["upstream_filed"] is False
    assert residue["defects"] == EXPECTED_DEFECTS

    disposition = data["disposition"]
    assert disposition["status"] == "documented-only"
    assert disposition["engine_waiver"] is False
    assert disposition["lifecycle_mutation"] is False
    assert disposition["reopen_authorized"] is False
    assert disposition["human_decision_required"] is True
    assert "fresh sanctioned status" in disposition["required_before_reopen"]
    assert "explicit human decision" in disposition["required_before_reopen"]

    prohibited = "\n".join(data["prohibited_actions"])
    assert all(term in prohibited for term in FORBIDDEN_TERMS)
    assert "LegalDomain" in prohibited
    assert len(data["evidence_refs"]) == 3
    assert all(not Path(ref).is_absolute() for ref in data["evidence_refs"])

    print("S05_PROCESS_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
