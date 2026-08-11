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
    check_active_surface_era_noise,
    check_adr_cross_surface_matrix,
    check_adr_doc_matrix_coverage,
    check_adr_index_completeness,
    check_adr_retired_id_ban,
    check_adr_structure_hygiene,
    check_adr_truth_oracle_sync,
    check_architecture_direction,
    check_archive_path_policy,
    check_ci_quality_gate_drift,
    check_forward_roadmap_sequence,
    check_historical_test_debt_visibility,
    check_hostile_negative_suite_coverage,
    check_hostile_proof_chain,
    check_port_contract_coverage,
    check_roadmap_freshness,
    check_semantic_stub_in_product_code,
    check_verify_test_coverage_drift,
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
    assert "current_milestone.id=M117-a06sez" in failed["roadmap-current-tracks-gsd"].remediation
    assert (
        "completed_milestone_groups[].range=M117-M117"
        in failed["roadmap-range-coverage"].remediation
    )


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


def test_cli_governor_supports_adr_group_selection(capsys) -> None:
    code = main(["governor", "--only", "adr"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["findings"]
    assert all(
        item["check_id"].startswith("adr-") or item["check_id"] == "archive-path-policy"
        for item in payload["findings"]
    )
    assert all("rule_id" in item for item in payload["findings"])
    assert all("expected" in item for item in payload["findings"])
    assert all("evidence" in item for item in payload["findings"])


def test_cli_governor_supports_exact_check_selection(capsys) -> None:
    code = main(["governor", "--check", "adr-truth-oracle-sync"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert [item["check_id"] for item in payload["findings"]] == ["adr-truth-oracle-sync"]


def test_cli_governor_explain_is_read_only_and_structured(capsys) -> None:
    code = main(["governor", "--explain", "adr-truth-oracle-sync"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["check_id"] == "adr-truth-oracle-sync"
    assert payload["group"] == "adr"
    assert payload["kind"] == "deterministic"
    assert payload["authority_inputs"] == [
        "doc/adr/0*.md",
        "prd/ARCHITECTURE.md",
    ]
    assert payload["non_claim"]


def test_cli_governor_text_format_is_human_readable(capsys) -> None:
    code = main(
        [
            "governor",
            "--check",
            "adr-truth-oracle-sync",
            "--format",
            "text",
        ]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "governor status=ok" in out
    assert "[PASS/ok] adr-truth-oracle-sync" in out


def test_cli_governor_unknown_selector_is_contract_error(capsys) -> None:
    code = main(["governor", "--check", "does-not-exist"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "tool-error"
    assert payload["error"] == "unknown-check"


def test_cli_governor_warn_only_semantic_selection_exits_zero(capsys) -> None:
    code = main(["governor", "--only", "semantic"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "ok"
    assert all(item["severity"] in {"ok", "warn"} for item in payload["findings"])


def test_cli_governor_runner_failure_uses_tool_error_exit_two(tmp_path: Path, capsys) -> None:
    roadmap = tmp_path / "prd" / "project-state" / "data"
    roadmap.mkdir(parents=True)
    (roadmap / "roadmap.json").write_text("{not-json", encoding="utf-8")
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n**Last Completed Milestone:** M001: x\n"
        "## Milestone Registry\n- ✅ **M001:** x\n",
        encoding="utf-8",
    )

    code = main(["governor", "--root", str(tmp_path), "--only", "docs"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "failure"
    assert payload["tool_error_count"] == 1
    tool_errors = [item for item in payload["findings"] if item["rule_id"] == "tool-error"]
    assert len(tool_errors) == 1
    assert tool_errors[0]["check_id"] == "roadmap-freshness"
    assert "not-json" not in tool_errors[0]["observed"]


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


def test_port_contract_coverage_pass_includes_evidence_ceiling_non_claim() -> None:
    findings = check_port_contract_coverage(ROOT)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "port-contract-coverage"
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "covered=22" in finding.observed or "covered=" in finding.observed
    assert "not real" in finding.observed.lower() or "not tei" in finding.observed.lower()
    assert "bounded" in finding.observed.lower()


def test_port_contract_coverage_debt_is_non_blocking_warn(tmp_path: Path) -> None:
    crates = tmp_path / "crates" / "ln-example" / "src"
    crates.mkdir(parents=True)
    (crates / "adapters.rs").write_text(
        "pub struct InMemoryExampleStore {\n    value: u8,\n}\n",
        encoding="utf-8",
    )
    # Inventory module loads from the real harness repository; discovery runs
    # against this temporary crates tree (declared covered set is missing).
    findings = check_port_contract_coverage(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "port-contract-coverage"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "uncovered=" in finding.observed
    assert "not real" in finding.observed.lower() or "not tei" in finding.observed.lower()


def test_port_contract_coverage_missing_crates_tree_is_debt_warn(tmp_path: Path) -> None:
    # Empty fixture root: discovery finds nothing, declared covered set is missing
    # -> debt warn (non-blocking), not silent pass.
    findings = check_port_contract_coverage(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "port-contract-coverage"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing_declared=" in finding.observed


def test_live_governor_includes_port_contract_coverage_finding() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "port-contract-coverage" in by_id
    assert by_id["port-contract-coverage"].status == "pass"
    assert report.error_count == 0
    assert report.status == "ok"


def test_live_governor_passes_hostile_negative_suite_coverage() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "hostile-negative-suite-coverage" in by_id
    finding = by_id["hostile-negative-suite-coverage"]
    # Residual hostiles closed: all discovered hostiles have shared-negative mentions.
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "missing_shared_negative=0" in finding.observed
    assert report.error_count == 0
    # Advisory probes may warn without failing the governor overall.
    advisory_warn_ids = {
        "historical-test-debt-visibility",
        "archive-path-policy",
    }
    other_warns = [
        f for f in report.findings if f.severity == "warn" and f.check_id not in advisory_warn_ids
    ]
    assert other_warns == []
    assert report.status == "ok"


def test_live_governor_passes_multi_adapter_port_coverage() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "multi-adapter-port-coverage" in by_id
    finding = by_id["multi-adapter-port-coverage"]
    # After WordML shared suite, residual real multi-adapter gaps are closed.
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "missing_shared_suite=0" in finding.observed
    assert report.error_count == 0


def test_live_governor_passes_live_adapter_readiness() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "live-adapter-readiness" in by_id
    finding = by_id["live-adapter-readiness"]
    # Repository-evidence ceiling: TEI stub transport only, RuVector proposed.
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "tei=stub_transport_only" in finding.observed
    assert "ruvector=proposed" in finding.observed
    assert "overclaim_count=0" in finding.observed
    assert report.error_count == 0
    # Advisory probes may warn without failing the governor overall.
    advisory_warn_ids = {
        "historical-test-debt-visibility",
        "archive-path-policy",
    }
    other_warns = [
        f for f in report.findings if f.severity == "warn" and f.check_id not in advisory_warn_ids
    ]
    assert other_warns == []
    assert report.status == "ok"


def test_live_governor_passes_ci_quality_gate_drift() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "ci-quality-gate-drift" in by_id
    finding = by_id["ci-quality-gate-drift"]
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "hooks=" in finding.observed
    assert "process_suite=" in finding.observed
    assert "inventory_scripts=" in finding.observed
    assert report.error_count == 0
    assert report.status == "ok"


def test_live_governor_passes_verify_test_coverage_drift() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "verify-test-coverage-drift" in by_id
    finding = by_id["verify-test-coverage-drift"]
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "active_scripts=" in finding.observed
    assert report.error_count == 0
    assert report.status == "ok"


def test_verify_test_coverage_drift_detects_missing_test(tmp_path: Path) -> None:
    import json as _j

    inv = tmp_path / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(
        _j.dumps(
            {
                "ci_process_suite": [],
                "ci_inventory_scripts": ["scripts/verify-active.py"],
            }
        )
    )
    tests = tmp_path / "tests"
    tests.mkdir(parents=True)
    (tests / "test_verify_active.py").write_text("# scripts/verify-active.py")
    pre = tmp_path / ".pre-commit-config.yaml"
    pre.write_text("")
    ci = tmp_path / ".github" / "workflows" / "repository-quality.yml"
    ci.parent.mkdir(parents=True, exist_ok=True)
    ci.write_text("")
    findings = check_verify_test_coverage_drift(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing_count=" in finding.observed


def test_ci_quality_gate_drift_detects_hook_mismatch(tmp_path: Path) -> None:
    import json as _json

    inv = tmp_path / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(
        _json.dumps(
            {
                "checks": [{"id": "ruff-check-python"}, {"id": "fake-extra-hook"}],
                "ci_process_suite": [],
                "ci_inventory_scripts": [],
            }
        )
    )
    pre = tmp_path / ".pre-commit-config.yaml"
    pre.write_text("repos:\n  - repo: local\n    hooks:\n      - id: ruff-check-python\n")
    ci = tmp_path / ".github" / "workflows" / "repository-quality.yml"
    ci.parent.mkdir(parents=True, exist_ok=True)
    ci.write_text("")
    findings = check_ci_quality_gate_drift(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "pre_commit_vs_qg_checks" in finding.observed


def test_ci_quality_gate_drift_detects_ci_suite_missing(tmp_path: Path) -> None:
    import json as _json

    inv = tmp_path / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(
        _json.dumps(
            {
                "checks": [{"id": "ruff-check-python"}],
                "ci_process_suite": ["tests/test_missing_from_ci.py"],
                "ci_inventory_scripts": ["scripts/verify-missing.py"],
            }
        )
    )
    pre = tmp_path / ".pre-commit-config.yaml"
    pre.write_text("repos:\n  - repo: local\n    hooks:\n      - id: ruff-check-python\n")
    ci = tmp_path / ".github" / "workflows" / "repository-quality.yml"
    ci.parent.mkdir(parents=True, exist_ok=True)
    ci.write_text("")
    findings = check_ci_quality_gate_drift(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "process_suite_missing_from_ci" in finding.observed
    assert "inventory_scripts_missing_from_ci" in finding.observed


def test_hostile_negative_suite_coverage_pass_when_no_hostiles(tmp_path: Path) -> None:
    # Empty crates tree: no hostiles discovered -> pass (mention inventory empty).
    findings = check_hostile_negative_suite_coverage(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "hostile-negative-suite-coverage"
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "missing_shared_negative=0" in finding.observed


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


def test_live_governor_passes_semantic_stub_in_product_code() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "semantic-stub-in-product-code" in by_id
    finding = by_id["semantic-stub-in-product-code"]
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "stub_count=0" in finding.observed
    assert report.error_count == 0
    assert report.status == "ok"


def test_semantic_stub_in_product_code_detects_planted_stub(tmp_path: Path) -> None:
    crates_src = tmp_path / "crates" / "ln-fake" / "src"
    crates_src.mkdir(parents=True)
    (crates_src / "lib.rs").write_text(
        "// real module\nfn thing() -> f64 {\n    let score = 1.0; // stub ranking\n    score\n}\n"
    )
    findings = check_semantic_stub_in_product_code(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "semantic-stub-in-product-code"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "stub_count=" in finding.observed
    assert "crates/ln-fake/src/lib.rs:3" in finding.observed
    assert "stub ranking" not in finding.observed
    assert "let score" not in finding.observed


def test_semantic_stub_in_product_code_ignores_tests_and_testkit(tmp_path: Path) -> None:
    # A stub marker under tests/ and ln-testkit must NOT be flagged.
    test_file = tmp_path / "crates" / "ln-fake" / "tests" / "x.rs"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("// stub in test, not product\n")
    testkit_file = tmp_path / "crates" / "ln-testkit" / "src" / "lib.rs"
    testkit_file.parent.mkdir(parents=True)
    testkit_file.write_text("// stub in testkit, not product\n")
    findings = check_semantic_stub_in_product_code(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_live_governor_reports_historical_test_debt_visibility() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "historical-test-debt-visibility" in by_id
    finding = by_id["historical-test-debt-visibility"]
    # Advisory inventory: status may be 'fail' (debt present, warn) but the
    # governor overall stays ok. The observed field must carry a count.
    assert "historical_test_count=" in finding.observed
    assert finding.severity == "warn" or finding.severity == "ok"
    assert report.status == "ok"


def test_historical_test_debt_visibility_detects_planted(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_zz_planted.py").write_text(
        "# historical proof test referencing decommissioned eras\n"
        "def test_falkordb_graph():\n"
        "    assert 'falkordb' or 'git_lex' or 'minimax' or 'pyo3'\n"
    )
    findings = check_historical_test_debt_visibility(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "historical-test-debt-visibility"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "historical_test_count=" in finding.observed
    assert "test_zz_planted.py" in finding.observed


def test_historical_test_debt_visibility_excludes_active_controls(
    tmp_path: Path,
) -> None:
    # A file whose name marks it as an active decommission-policy control
    # must NOT be flagged even if it mentions 'acp'.
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_verify_acp_decommission.py").write_text(
        "# active control asserting ACP is decommissioned\n"
        "def test_acp_decommissioned():\n"
        "    assert 'acp' not in active_imports\n"
    )
    findings = check_historical_test_debt_visibility(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_live_governor_includes_adr_and_archive_checks() -> None:
    report = run_governor(ROOT)
    by_id = {item.check_id: item for item in report.findings}
    assert "adr-truth-oracle-sync" in by_id
    assert "adr-index-completeness" in by_id
    assert "adr-doc-matrix-coverage" in by_id
    assert "adr-structure-hygiene" in by_id
    assert "adr-cross-surface-matrix" in by_id
    assert "adr-retired-id-ban" in by_id
    assert "active-surface-era-noise" in by_id
    assert "archive-path-policy" in by_id
    assert by_id["adr-truth-oracle-sync"].status == "pass"
    assert by_id["adr-index-completeness"].status == "pass"
    assert by_id["adr-doc-matrix-coverage"].status == "pass"
    assert by_id["adr-structure-hygiene"].status == "pass"
    assert by_id["adr-cross-surface-matrix"].status == "pass"
    assert by_id["adr-retired-id-ban"].status == "pass"
    assert by_id["active-surface-era-noise"].status == "pass"
    assert by_id["archive-path-policy"].status == "pass"
    assert report.error_count == 0
    assert report.status == "ok"


def test_adr_truth_oracle_sync_detects_lifecycle_mismatch(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-rust-migration-decision.md").write_text(
        "# ADR-0004\n\n## Status\n\nAccepted `[bounded]`.\n",
        encoding="utf-8",
    )
    arch = tmp_path / "prd"
    arch.mkdir()
    (arch / "ARCHITECTURE.md").write_text(
        "# ARCH\n\n"
        "Rust direction [validated] (ADR-0004/0005)\n"
        "Harness ADR-0007 [validated]\n"
        "Authority ADR-0008 [bounded] ADR-0011 [bounded] ADR-0012 [bounded]\n"
        "Clocks ADR-0009 [bounded] ADR-0010 [bounded]\n"
        "Parser ADR-0013 [bounded] ADR-0014 [proposed] ADR-0015 [bounded]\n"
        "Ontology ADR-0016 [proposed] ADR-0017 [proposed] ADR-0018 [proposed]\n"
        "ADR-0019 [proposed] ADR-0020 [proposed] ADR-0021 [proposed] ADR-0022 [proposed]\n"
        "ADR-0023 [proposed]\n",
        encoding="utf-8",
    )
    findings = check_adr_truth_oracle_sync(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "adr-truth-oracle-sync"
    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "mismatched=" in finding.observed
    assert "ADR-0004" in finding.observed
    assert {item.path for item in finding.evidence} == {
        "doc/adr/0004-rust-migration-decision.md",
        "prd/ARCHITECTURE.md",
    }
    assert all(item.line is not None for item in finding.evidence)


def test_adr_truth_oracle_sync_rejects_dual_lifecycle_overclaim(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0024-future.md").write_text(
        "# ADR-0024\n\n## Status\n\nAccepted `[proposed]`.\n",
        encoding="utf-8",
    )
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "ARCHITECTURE.md").write_text(
        "# ARCH\n\nADR-0024 [proposed] [validated]\n",
        encoding="utf-8",
    )

    finding = check_adr_truth_oracle_sync(tmp_path)[0]
    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "ADR-0024:expected=proposed:seen=proposed,validated" in finding.observed


def test_adr_truth_oracle_sync_discovers_future_adr(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0024-future.md").write_text(
        "# ADR-0024\n\n## Status\n\nAccepted `[proposed]`.\n",
        encoding="utf-8",
    )
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "ARCHITECTURE.md").write_text("# ARCH\n", encoding="utf-8")

    finding = check_adr_truth_oracle_sync(tmp_path)[0]
    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "ADR-0024" in finding.observed


def test_adr_truth_oracle_sync_rejects_adr_without_status_lifecycle(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0024-bad.md").write_text(
        "# ADR-0024\n\n## Status\n\nAccepted without lifecycle.\n",
        encoding="utf-8",
    )
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "ARCHITECTURE.md").write_text(
        "# ARCH\n\nADR-0024 [proposed]\n",
        encoding="utf-8",
    )

    finding = check_adr_truth_oracle_sync(tmp_path)[0]
    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "expected=status-lifecycle:seen=none" in finding.observed


def test_adr_truth_oracle_sync_passes_matching_tags(tmp_path: Path) -> None:
    arch = tmp_path / "prd"
    arch.mkdir()
    (arch / "ARCHITECTURE.md").write_text(
        "# ARCH\n\n"
        "ADR-0004 [bounded]\n"
        "ADR-0005 [bounded]\n"
        "ADR-0007 [validated]\n"
        "ADR-0008 [bounded]\n"
        "ADR-0009 [bounded]\n"
        "ADR-0010 [bounded]\n"
        "ADR-0011 [bounded]\n"
        "ADR-0012 [bounded]\n"
        "ADR-0013 [bounded]\n"
        "ADR-0014 [proposed]\n"
        "ADR-0015 [bounded]\n"
        "ADR-0016 [proposed]\n"
        "ADR-0017 [proposed]\n"
        "ADR-0018 [proposed]\n"
        "ADR-0019 [proposed]\n"
        "ADR-0020 [proposed]\n"
        "ADR-0021 [proposed]\n"
        "ADR-0022 [proposed]\n"
        "ADR-0023 [proposed]\n",
        encoding="utf-8",
    )
    findings = check_adr_truth_oracle_sync(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"


def test_archive_path_policy_warns_when_not_ignored(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("# empty policy\n", encoding="utf-8")
    findings = check_archive_path_policy(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "archive-path-policy"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing_gitignore=" in finding.observed


def test_archive_path_policy_warns_on_active_alias_into_vault(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        "\n".join(
            [
                ".lex/",
                "python_archive/",
                "Old_project/",
                "prd/archive/acp-git-lex/",
                "prd/archive/pre-rust-prd/",
                "prd/archive/milestone-proofs-era/",
                "prd/archive/research-era/",
                "prd/archive/project-state-era/",
                "prd/archive/architecture-era/",
                "prd/archive/parser-dumps-era/",
                "prd/archive/retrieval-era/",
                "prd/archive/migration-era/",
                "archive/",
                "probes/",
                ".commandcode/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    active = tmp_path / "prd" / "architecture"
    active.mkdir(parents=True)
    (active / "acp").symlink_to("../archive/acp-git-lex")
    findings = check_archive_path_policy(tmp_path)
    assert findings[0].status == "fail"
    assert "active_aliases=['prd/architecture/acp']" in findings[0].observed


def test_archive_path_policy_warns_on_unlisted_symlink_into_vault(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        "\n".join(
            [
                ".lex/",
                "python_archive/",
                "Old_project/",
                "prd/archive/acp-git-lex/",
                "prd/archive/pre-rust-prd/",
                "prd/archive/milestone-proofs-era/",
                "prd/archive/research-era/",
                "prd/archive/project-state-era/",
                "prd/archive/architecture-era/",
                "prd/archive/parser-dumps-era/",
                "prd/archive/retrieval-era/",
                "prd/archive/migration-era/",
                "archive/",
                "probes/",
                ".commandcode/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    vault = tmp_path / "python_archive" / "product"
    vault.mkdir(parents=True)
    active = tmp_path / "prd" / "current"
    active.mkdir(parents=True)
    (active / "legacy-source").symlink_to(vault)

    finding = check_archive_path_policy(tmp_path)[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "prd/current/legacy-source->python_archive/product" in finding.observed


def test_archive_path_policy_passes_when_ignored(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        ".lex/\n"
        "python_archive/\n"
        "Old_project/\n"
        "prd/archive/acp-git-lex/\n"
        "prd/archive/pre-rust-prd/\n"
        "prd/archive/milestone-proofs-era/\n"
        "prd/archive/research-era/\n"
        "prd/archive/project-state-era/\n"
        "prd/archive/architecture-era/\n"
        "prd/archive/parser-dumps-era/\n"
        "prd/archive/retrieval-era/\n"
        "prd/archive/migration-era/\n"
        "archive/\n"
        "probes/\n"
        ".commandcode/\n",
        encoding="utf-8",
    )
    # Not a git repo => tracked list empty; ignore-only is enough for pass.
    findings = check_archive_path_policy(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_adr_index_completeness_detects_missing(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "README.md").write_text("# ADRs\n\n- ADR-0004 only\n", encoding="utf-8")
    (adr / "0004-rust.md").write_text("# x\n", encoding="utf-8")
    (adr / "0099-missing.md").write_text("# y\n", encoding="utf-8")
    findings = check_adr_index_completeness(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "0099-missing.md" in finding.observed


def test_adr_index_completeness_detects_missing_lifecycle(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "README.md").write_text("# ADRs\n\n- ADR-0004 Rust\n", encoding="utf-8")
    (adr / "0004-rust.md").write_text(
        "# ADR-0004\n\n## Status\n\nAccepted `[bounded]`.\n",
        encoding="utf-8",
    )
    findings = check_adr_index_completeness(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "ADR-0004:expected=bounded" in finding.observed


def test_adr_doc_matrix_coverage_detects_missing_surface(tmp_path: Path) -> None:
    gsd = tmp_path / ".gsd"
    gsd.mkdir()
    (gsd / "REQUIREMENTS.md").write_text(
        "# R\nADR-0016 ADR-0017 ADR-0018 ADR-0019 ADR-0020 ADR-0021 ADR-0022\n",
        encoding="utf-8",
    )
    # PROJECT missing entirely
    findings = check_adr_doc_matrix_coverage(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "adr-doc-matrix-coverage"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "PROJECT.md" in finding.observed


def test_adr_structure_hygiene_detects_missing_status_lifecycle(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-bad.md").write_text(
        "# ADR-0004\n\n"
        "## Status\n\nAccepted without tag.\n\n"
        "## Context\n\nx\n\n"
        "## Decision\n\ny\n\n"
        "## Consequences\n\nz\n\n"
        "## Non-claims\n\nnone\n",
        encoding="utf-8",
    )
    findings = check_adr_structure_hygiene(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "adr-structure-hygiene"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "0004-bad.md" in finding.observed


def test_adr_cross_surface_matrix_detects_gap(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-rust.md").write_text(
        "# ADR-0004\n\n## Status\n\nAccepted [bounded].\n\n"
        "## Context\n\nx\n\n## Decision\n\ny\n\n"
        "## Consequences\n\nz\n\n## Non-claims\n\nnone\n",
        encoding="utf-8",
    )
    (adr / "README.md").write_text("# ADR\n\nADR-0004\n", encoding="utf-8")
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "ARCHITECTURE.md").write_text("# A\n\nADR-0004 [bounded]\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# root\n\nno citation\n", encoding="utf-8")
    findings = check_adr_cross_surface_matrix(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "adr-cross-surface-matrix"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "ADR-0008" not in finding.observed
    assert "ADR-0004@README.md" in finding.observed


def test_adr_retired_id_ban_detects_unqualified_cite(tmp_path: Path) -> None:
    (tmp_path / "prd").mkdir()
    (tmp_path / "prd" / "ARCHITECTURE.md").write_text(
        "# A\n\nUse ADR-0003 for library boundary.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# r\n", encoding="utf-8")
    findings = check_adr_retired_id_ban(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "adr-retired-id-ban"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "ADR-0003" in finding.observed


def test_adr_retired_id_ban_allows_historical_qualifier(tmp_path: Path) -> None:
    (tmp_path / "prd").mkdir()
    (tmp_path / "prd" / "ARCHITECTURE.md").write_text(
        "# A\n\nHistorical library boundary (retired ADR-0003, prior art only).\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# r\n", encoding="utf-8")
    findings = check_adr_retired_id_ban(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"


def test_active_surface_era_noise_detects_unqualified_token(tmp_path: Path) -> None:
    (tmp_path / "prd").mkdir()
    (tmp_path / "prd" / "ARCHITECTURE.md").write_text(
        "# A\n\nDeploy FalkorDB for production graph.\n",
        encoding="utf-8",
    )
    findings = check_active_surface_era_noise(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "active-surface-era-noise"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "falkordb" in finding.observed.lower()


def test_active_surface_era_noise_rejects_adjacent_qualifier_laundering(
    tmp_path: Path,
) -> None:
    (tmp_path / "prd").mkdir()
    (tmp_path / "prd" / "ARCHITECTURE.md").write_text(
        "# A\n\nRuVector is proposed.\nDeploy FalkorDB for production.\n",
        encoding="utf-8",
    )

    finding = check_active_surface_era_noise(tmp_path)[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "falkordb" in finding.observed.lower()


def test_active_surface_era_noise_allows_qualified_token(tmp_path: Path) -> None:
    (tmp_path / "prd").mkdir()
    (tmp_path / "prd" / "ARCHITECTURE.md").write_text(
        "# A\n\nFalkorDB is historical evidence, not active infrastructure.\n",
        encoding="utf-8",
    )
    findings = check_active_surface_era_noise(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"
