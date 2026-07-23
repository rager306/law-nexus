"""TDD contracts for the repository trajectory governor."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.governor import (
    GOVERNOR_SCHEMA_VERSION,
    check_hostile_proof_chain,
    check_roadmap_freshness,
    run_governor,
)

ROOT = Path(__file__).resolve().parents[1]


def test_governor_report_schema_and_live_repo_pass() -> None:
    report = run_governor(ROOT)
    payload = report.to_dict()
    assert payload["schema_version"] == GOVERNOR_SCHEMA_VERSION
    assert payload["status"] in {"ok", "failure"}
    assert isinstance(payload["findings"], list)
    assert payload["pass_count"] + payload["error_count"] + payload["warn_count"] == len(
        payload["findings"]
    )
    # After post-M117 debt close and current proofs, governor must be green.
    assert report.status == "ok", report.to_json()
    assert report.error_count == 0


def test_roadmap_freshness_fails_when_range_lags(tmp_path: Path) -> None:
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M117-a06sez: HC 05\n"
        "**Active Slice:** None\n"
        "**Phase:** complete\n\n"
        "## Milestone Registry\n"
        "- ✅ **M116-l1avxb:** HC 04\n"
        "- ✅ **M117-a06sez:** HC 05\n",
        encoding="utf-8",
    )
    roadmap_dir = tmp_path / "prd" / "project-state" / "data"
    roadmap_dir.mkdir(parents=True)
    (roadmap_dir / "roadmap.json").write_text(
        json.dumps(
            {
                "completed_milestone_groups": [
                    {"range": "M116-M116", "status": "complete"},
                ],
                "current_milestone": {
                    "id": "M116-l1avxb",
                    "status": "complete",
                    "title": "HC 04",
                },
            }
        ),
        encoding="utf-8",
    )
    findings = check_roadmap_freshness(tmp_path)
    failed = {item.check_id: item for item in findings if item.status == "fail"}
    assert "roadmap-current-tracks-gsd" in failed
    assert "roadmap-range-coverage" in failed


def test_hostile_proof_chain_detects_aggregate_mismatch(tmp_path: Path) -> None:
    probes = tmp_path / "prd" / "migration" / "rust-evidence" / "probes"
    probes.mkdir(parents=True)
    for n, remaining in ((1, 19), (2, 18)):
        (probes / f"hc{n:02d}-example-runtime.json").write_text(
            json.dumps(
                {
                    "evidence_id": f"S10-HC-{n:02d}-RT",
                    "verdict": "PASS",
                    "remaining_unsupported_cases": remaining,
                }
            ),
            encoding="utf-8",
        )
    baseline = tmp_path / "prd" / "architecture"
    baseline.mkdir(parents=True)
    (baseline / "m111-final-architecture-baseline.md").write_text(
        "| Runtime aggregate | PASS 1/20; FAIL 0/20; `unsupported-case` 19/20 | stale |\n",
        encoding="utf-8",
    )
    findings = check_hostile_proof_chain(tmp_path)
    failed = {item.check_id: item for item in findings if item.status == "fail"}
    assert "hostile-baseline-aggregate" in failed


def test_cli_governor_command_emits_report(capsys) -> None:
    code = main(["governor"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["schema_version"] == GOVERNOR_SCHEMA_VERSION
    assert "findings" in payload
    assert code in {0, 1}
    # Live repository after debt close should exit 0.
    assert code == 0
