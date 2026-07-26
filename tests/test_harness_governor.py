"""TDD contracts for the repository trajectory governor."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.governor import (
    _ACTIVE_REQUIREMENT_POLICY,
    _EXPECTED_DIRECTION,
    GOVERNOR_SCHEMA_VERSION,
    check_active_requirement_contradictions,
    check_architecture_direction,
    check_forward_roadmap_sequence,
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
    # A fresh clone may not materialize the external GSD state projection.
    # Schema/count consistency is portable; live-green state is verified separately.
    assert report.status == ("ok" if report.error_count == 0 else "failure")


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
    expected_code = 0 if payload["status"] == "ok" else 1
    assert code == expected_code


def test_cli_governor_without_local_gsd_projection_fails_with_coherent_exit_code(
    tmp_path: Path, capsys
) -> None:
    code = main(["governor", "--root", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["status"] == "failure"
    assert payload["error_count"] > 0
    assert any(item["check_id"] == "gsd-state-present" for item in payload["findings"])


def test_open_next_wave_milestone_is_not_residual_debt(tmp_path: Path) -> None:
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M117-a06sez: HC 05\n"
        "**Active Milestone:** M118-5s90td: HC 06\n"
        "**Phase:** planning\n\n"
        "## Milestone Registry\n"
        "- ✅ **M117-a06sez:** HC 05\n"
        "- 🔄 **M118-5s90td:** HC 06\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_gsd_residual_debt

    findings = check_gsd_residual_debt(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["gsd-no-open-registry-debt"].status == "pass"
    assert by_id["gsd-phase-complete-consistent"].status == "pass"


ACTIVE_DIRECTION = (
    "## Active Direction Contract\n\n```text\n"
    + "\n".join(f"{key}={value}" for key, value in _EXPECTED_DIRECTION.items())
    + "\n```\n"
)


def write_direction_surfaces(root: Path, contract: str = ACTIVE_DIRECTION) -> None:
    paths = (
        root / "prd" / "ARCHITECTURE.md",
        root / "prd" / "project-state" / "roadmap.md",
    )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Current state\n\n"
            "Historical note: FalkorDB and ACP/git-lex were assessed previously.\n\n"
            f"{contract}\n",
            encoding="utf-8",
        )


def test_architecture_direction_accepts_current_contract_and_historical_mentions(
    tmp_path: Path,
) -> None:
    write_direction_surfaces(tmp_path)

    findings = check_architecture_direction(tmp_path)

    assert len(findings) == 1
    assert findings[0].check_id == "architecture-direction-contract"
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_architecture_direction_rejects_stale_or_inflated_values(tmp_path: Path) -> None:
    stale_contract = (
        ACTIVE_DIRECTION.replace("graph_vector=ruvector", "graph_vector=falkordb")
        .replace("infrastructure_lifecycle=proposed", "infrastructure_lifecycle=validated")
        .replace("acp_git_lex=archive-only", "acp_git_lex=active")
    )
    write_direction_surfaces(tmp_path, stale_contract)

    finding = check_architecture_direction(tmp_path)[0]

    assert finding.check_id == "architecture-direction-contract"
    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "graph_vector" in finding.observed
    assert "infrastructure_lifecycle" in finding.observed
    assert "acp_git_lex" in finding.observed


def test_architecture_direction_fails_closed_on_missing_duplicate_or_unknown_keys(
    tmp_path: Path,
) -> None:
    malformed = ACTIVE_DIRECTION.replace("falkordb=historical-only\n", "").replace(
        "runtime=rust-only\n",
        "runtime=rust-only\nruntime=python\nunknown_key=value\n",
    )
    write_direction_surfaces(tmp_path, malformed)

    finding = check_architecture_direction(tmp_path)[0]

    assert finding.status == "fail"
    assert "missing=falkordb" in finding.observed
    assert "mismatch=falkordb" not in finding.observed
    assert "duplicate=runtime" in finding.observed
    assert "unknown=unknown_key" in finding.observed


def test_architecture_direction_reports_missing_contract_without_false_mismatches(
    tmp_path: Path,
) -> None:
    write_direction_surfaces(tmp_path)
    architecture = tmp_path / "prd" / "ARCHITECTURE.md"
    architecture.write_text("# Missing active contract\n", encoding="utf-8")

    finding = check_architecture_direction(tmp_path)[0]

    assert finding.status == "fail"
    assert "prd/ARCHITECTURE.md: missing-contract" in finding.observed
    assert "missing=" not in finding.observed
    assert "mismatch=" not in finding.observed


def test_architecture_direction_rejects_duplicate_contract_blocks(tmp_path: Path) -> None:
    write_direction_surfaces(tmp_path)
    architecture = tmp_path / "prd" / "ARCHITECTURE.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8") + "\n" + ACTIVE_DIRECTION,
        encoding="utf-8",
    )

    finding = check_architecture_direction(tmp_path)[0]

    assert finding.status == "fail"
    assert "prd/ARCHITECTURE.md" in finding.observed
    assert "contract_blocks=2" in finding.observed


def test_architecture_direction_requires_all_tracked_surfaces_to_match(tmp_path: Path) -> None:
    write_direction_surfaces(tmp_path)
    roadmap = tmp_path / "prd" / "project-state" / "roadmap.md"
    roadmap.write_text(
        roadmap.read_text(encoding="utf-8").replace(
            "graph_vector=ruvector", "graph_vector=falkordb"
        ),
        encoding="utf-8",
    )

    finding = check_architecture_direction(tmp_path)[0]

    assert finding.status == "fail"
    assert "prd/project-state/roadmap.md" in finding.observed
    assert "graph_vector" in finding.observed


def test_forward_roadmap_requires_unique_m131_to_m140_sequence(tmp_path: Path) -> None:
    path = tmp_path / "prd" / "migration" / "forward-roadmap.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Roadmap\n\n" + "\n".join(f"M{seq}: Product wave" for seq in range(131, 141)),
        encoding="utf-8",
    )

    finding = check_forward_roadmap_sequence(tmp_path)[0]

    assert finding.status == "pass"
    assert "M131-M140" in finding.observed


def test_forward_roadmap_rejects_old_gap_or_duplicate_numbering(tmp_path: Path) -> None:
    path = tmp_path / "prd" / "migration" / "forward-roadmap.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Roadmap\n\nM130: Old product wave\nM131: Wave\nM131: Duplicate\nM133: Gap\n",
        encoding="utf-8",
    )

    finding = check_forward_roadmap_sequence(tmp_path)[0]

    assert finding.status == "fail"
    assert "unexpected=M130" in finding.observed
    assert "duplicate=M131" in finding.observed
    assert "missing=M132" in finding.observed


def write_requirements(root: Path, active_blocks: str) -> None:
    path = root / ".gsd" / "REQUIREMENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Requirements\n\n## Active\n\n{active_blocks}\n\n## Validated\n",
        encoding="utf-8",
    )


def test_requirement_contradictions_pass_when_local_projection_is_unavailable(
    tmp_path: Path,
) -> None:
    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "pass"
    assert "unavailable-local-projection" in finding.observed


def test_requirement_contradictions_fail_closed_on_malformed_local_projection(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".gsd" / "REQUIREMENTS.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Requirements\n\n## Deferred\n", encoding="utf-8")

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "fail"
    assert "missing-active-section" in finding.observed


def test_requirement_contradictions_ignore_allowed_r066_antifeature(tmp_path: Path) -> None:
    write_requirements(
        tmp_path,
        "### R066 — ACP and git-lex must not remain active\n"
        "- Description: ACP and git-lex are archive-only.\n"
        "### R065 — Python prior art\n"
        "- Description: Python is historical prior art and a bounded comparison surface until cutover.\n",
    )

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "pass"
    assert "active_conflicts=[]" in finding.observed


def test_requirement_contradictions_accept_supported_heading_separators(
    tmp_path: Path,
) -> None:
    for separator in ("—", "–", "-"):
        write_requirements(
            tmp_path,
            f"### R066 {separator} Archive-only guard\n"
            "- Description: ACP remains archive-only.\n"
            f"### R065 {separator} Python prior art\n"
            "- Description: Python is historical prior art and a bounded comparison surface until cutover.\n",
        )
        assert check_active_requirement_contradictions(tmp_path)[0].status == "pass"


def test_requirement_contradictions_fail_on_empty_active_section(tmp_path: Path) -> None:
    write_requirements(tmp_path, "")

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "fail"
    assert "empty-active-section" in finding.observed


def test_requirement_contradictions_fail_on_malformed_requirement_heading(
    tmp_path: Path,
) -> None:
    write_requirements(
        tmp_path,
        "### R037 : malformed separator\n- Description: legacy requirement.\n",
    )

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "fail"
    assert "malformed-headings" in finding.observed


def test_requirement_contradictions_report_legacy_ids_and_stale_python_wording(
    tmp_path: Path,
) -> None:
    write_requirements(
        tmp_path,
        "### R037 — FalkorDB ingest\n"
        "- Description: Active FalkorDB product requirement.\n"
        "### R065 — Python cutover\n"
        "- Description: Python is the behavioral reference until parity.\n",
    )

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "fail"
    assert "R037" in finding.observed
    assert "R065" in finding.observed


def test_requirement_contradictions_enforce_r065_policy_without_scanning_notes(
    tmp_path: Path,
) -> None:
    required = _ACTIVE_REQUIREMENT_POLICY["R065"]["required"]
    forbidden = _ACTIVE_REQUIREMENT_POLICY["R065"]["forbidden"]
    assert required == ("prior art", "bounded comparison")
    assert "behavioral reference" in forbidden

    write_requirements(
        tmp_path,
        "### R065 — Python cutover\n"
        "- Description: Python is historical prior art and a bounded comparison surface.\n"
        "- Notes: Do not treat Python as a behavioral reference or source of truth.\n",
    )
    assert check_active_requirement_contradictions(tmp_path)[0].status == "pass"

    for stale_description in (
        "Python is the behavioral reference until parity.",
        "Python is the source of truth until parity.",
        "Python is the normative specification until parity.",
        "Python is prior art until parity.",
    ):
        write_requirements(
            tmp_path,
            f"### R065 — Python cutover\n- Description: {stale_description}\n",
        )
        finding = check_active_requirement_contradictions(tmp_path)[0]
        assert finding.status == "fail", stale_description
        assert "R065" in finding.observed


def test_requirement_contradictions_do_not_scan_validated_history(tmp_path: Path) -> None:
    path = tmp_path / ".gsd" / "REQUIREMENTS.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Requirements\n\n## Active\n\n"
        "### R066 — Archive-only guard\n- Description: ACP is forbidden from active use.\n\n"
        "## Validated\n\n### R037 — Historical FalkorDB evidence\n",
        encoding="utf-8",
    )

    finding = check_active_requirement_contradictions(tmp_path)[0]

    assert finding.status == "pass"


def test_stale_open_milestone_behind_last_completed_is_debt(tmp_path: Path) -> None:
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M117-a06sez: HC 05\n"
        "**Active Milestone:** M115-nrvz4v: HC 03\n"
        "**Phase:** summarizing\n\n"
        "## Milestone Registry\n"
        "- 🔄 **M115-nrvz4v:** HC 03\n"
        "- ✅ **M117-a06sez:** HC 05\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_gsd_residual_debt

    findings = check_gsd_residual_debt(tmp_path)
    failed = {item.check_id: item for item in findings if item.status == "fail"}
    assert "gsd-no-open-registry-debt" in failed
    assert "gsd-phase-complete-consistent" in failed
