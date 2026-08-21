"""TDD contracts for the repository trajectory governor."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.governor import (
    _ACTIVE_REQUIREMENT_POLICY,
    _EXPECTED_DIRECTION,
    GOVERNOR_SCHEMA_VERSION,
    GovernorEvidence,
    _freshness_trigger_gaps,
    check_active_requirement_contradictions,
    check_active_surface_era_noise,
    check_adr_cross_surface_matrix,
    check_adr_doc_matrix_coverage,
    check_adr_index_completeness,
    check_adr_link_integrity,
    check_adr_retired_id_ban,
    check_adr_review_date_staleness,
    check_adr_structure_hygiene,
    check_adr_supersession_graph,
    check_adr_truth_oracle_sync,
    check_architecture_direction,
    check_archive_path_policy,
    check_ci_quality_gate_drift,
    check_document_freshness_triggers,
    check_forward_roadmap_sequence,
    check_historical_test_debt_visibility,
    check_hostile_negative_suite_coverage,
    check_hostile_proof_chain,
    check_model_crystal_anchors,
    check_port_contract_coverage,
    check_published_trace_contract,
    check_roadmap_freshness,
    check_semantic_stub_in_product_code,
    check_temporal_vocabulary_contract,
    check_temporal_vocabulary_drift,
    check_temporal_vocabulary_presentation_drift,
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
    assert failed["roadmap-current-tracks-gsd"].evidence == (
        GovernorEvidence(path="prd/project-state/data/roadmap.json", line=1),
        GovernorEvidence(path=".gsd/STATE.md", line=9),
    )
    assert (
        "completed_milestone_groups[].range=M117-M117"
        in failed["roadmap-range-coverage"].remediation
    )
    assert failed["roadmap-range-coverage"].evidence == (
        GovernorEvidence(path="prd/project-state/data/roadmap.json", line=1),
        GovernorEvidence(path=".gsd/STATE.md", line=9),
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
    assert failed["hostile-baseline-aggregate"].evidence == (
        GovernorEvidence(path="prd/architecture/m111-final-architecture-baseline.md", line=1),
        GovernorEvidence(
            path="prd/migration/rust-evidence/probes/hc01-example-runtime.json", line=1
        ),
        GovernorEvidence(
            path="prd/migration/rust-evidence/probes/hc02-example-runtime.json", line=1
        ),
    )


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


def test_cli_governor_json_flag_is_format_alias(capsys) -> None:
    code = main(["governor", "--json", "--check", "adr-truth-oracle-sync"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["schema_version"] == GOVERNOR_SCHEMA_VERSION
    assert [item["check_id"] for item in payload["findings"]] == ["adr-truth-oracle-sync"]


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


def test_cli_governor_fail_on_warn_is_opt_in(tmp_path: Path, capsys) -> None:
    # Deterministic fixture: planned-only inventory emits advisory warn without
    # hard residual debt. Live registry may be clean; do not depend on it.
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M165-2som4e: Temporal ontology\n"
        "**Active Milestone:** M166-iyy4ak: Review Governance Lifecycle\n"
        "**Phase:** planning\n\n"
        "## Milestone Registry\n"
        "- ✅ **M165-2som4e:** Temporal ontology\n"
        "- ⬜ **M166-iyy4ak:** Review Governance Lifecycle\n",
        encoding="utf-8",
    )
    code = main(
        [
            "governor",
            "--root",
            str(tmp_path),
            "--check",
            "gsd-residual-debt",
            "--fail-on-warn",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["status"] == "ok"
    assert payload["warn_count"] > 0
    assert payload["tool_error_count"] == 0
    assert any(
        item["check_id"]
        in {
            "gsd-planned-inventory-visibility",
            "gsd-code-complete-lag",
        }
        for item in payload["findings"]
    )


def test_cli_governor_lists_machine_readable_check_inventory(capsys) -> None:
    code = main(["governor", "--list-checks"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["schema_version"] == "law-nexus-governor-check-inventory/v1"
    assert payload["non_authoritative"] is True
    ids = [item["check_id"] for item in payload["checks"]]
    assert len(ids) == len(set(ids))
    assert "temporal-vocabulary-contract" in ids
    assert all(item["kind"] in {"deterministic", "heuristic"} for item in payload["checks"])
    assert all(item["non_claim"] for item in payload["checks"])


def test_cli_governor_list_checks_rejects_execution_selectors(capsys) -> None:
    code = main(["governor", "--list-checks", "--check", "adr-truth-oracle-sync"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "tool-error"
    assert payload["error"] == "conflicting-selectors"


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

    code = main(["governor", "--root", str(tmp_path), "--check", "roadmap-freshness"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "failure"
    assert payload["tool_error_count"] == 1
    tool_errors = [item for item in payload["findings"] if item["rule_id"] == "tool-error"]
    assert len(tool_errors) == 1
    assert tool_errors[0]["check_id"] == "roadmap-freshness"
    assert "not-json" not in tool_errors[0]["observed"]


def test_governor_inventory_loader_failures_are_tool_errors(tmp_path: Path, monkeypatch) -> None:
    def unavailable(*args, **kwargs):
        raise OSError("inventory unavailable")

    loader_checks = (
        ("_load_port_contract_coverage_module", "port-contract-coverage"),
        ("_load_hostile_negative_suite_module", "hostile-negative-suite-coverage"),
        ("_load_multi_adapter_port_coverage_module", "multi-adapter-port-coverage"),
        ("_load_live_adapter_readiness_module", "live-adapter-readiness"),
    )
    for loader, check_id in loader_checks:
        monkeypatch.setattr(f"law_nexus_harness.governor.{loader}", unavailable)
        report = run_governor(tmp_path, check=check_id)
        assert report.status == "failure"
        assert report.tool_error_count == 1
        assert report.findings[0].rule_id == "tool-error"
        assert "inventory unavailable" not in report.findings[0].observed


def test_governor_quality_inventory_read_failures_are_tool_errors(
    tmp_path: Path, monkeypatch
) -> None:
    inventory = tmp_path / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("{}", encoding="utf-8")
    original = Path.read_text

    def fail_selected(path: Path, *args, **kwargs):
        if path == inventory:
            raise OSError("quality inventory unavailable")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_selected)
    for check_id in ("ci-quality-gate-drift", "verify-test-coverage-drift"):
        report = run_governor(tmp_path, check=check_id)
        assert report.status == "failure"
        assert report.tool_error_count == 1
        assert report.findings[0].rule_id == "tool-error"
        assert "quality inventory unavailable" not in report.findings[0].observed


def test_selected_local_projection_checks_are_portable_without_gsd_state(
    tmp_path: Path, capsys
) -> None:
    roadmap = tmp_path / "prd" / "project-state" / "data"
    roadmap.mkdir(parents=True)
    (roadmap / "roadmap.json").write_text("{}", encoding="utf-8")

    for check_id in ("roadmap-freshness", "gsd-residual-debt"):
        code = main(["governor", "--root", str(tmp_path), "--check", check_id])
        payload = json.loads(capsys.readouterr().out)
        assert code == 0
        assert payload["status"] == "ok"
        assert payload["error_count"] == 0
        assert payload["findings"][0]["status"] == "pass"
        assert "not-applicable" in payload["findings"][0]["observed"]


def test_tracked_roadmap_is_required_without_local_gsd_state(tmp_path: Path) -> None:
    findings = check_roadmap_freshness(tmp_path)
    assert findings[0].check_id == "roadmap-json-present"
    assert findings[0].status == "fail"
    assert findings[0].severity == "error"


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


def test_registry_parser_includes_white_large_square_planned_marker() -> None:
    """STATE.md planned rows use ⬜; residual debt must not silently drop them."""
    from law_nexus_harness.governor import _registry_milestones

    text = (
        "## Milestone Registry\n"
        "- ✅ **M160-65pdoz:** Verify Test CI Coverage\n"
        "- 🔄 **M161-2som4e:** Retrieval ranking\n"
        "- ⬜ **M162-t9mjgj:** Governor semantic-stub probe\n"
        "- ⬜ **M166-iyy4ak:** Review Governance Lifecycle\n"
        "## Recent Decisions\n"
    )
    rows = _registry_milestones(text)
    by_seq = {seq: marker for seq, marker, _ in rows}
    assert by_seq[160] == "✅"
    assert by_seq[161] == "🔄"
    assert by_seq[162] == "⬜"
    assert by_seq[166] == "⬜"


def test_planned_white_square_next_wave_is_inventory_not_hard_debt(tmp_path: Path) -> None:
    """Planned ⬜ next-wave is advisory inventory, not hard residual debt."""
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M165-2som4e: Temporal ontology\n"
        "**Active Milestone:** M166-iyy4ak: Review Governance Lifecycle\n"
        "**Phase:** planning\n\n"
        "## Milestone Registry\n"
        "- ✅ **M165-2som4e:** Temporal ontology\n"
        "- ⬜ **M166-iyy4ak:** Review Governance Lifecycle\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_gsd_residual_debt

    findings = check_gsd_residual_debt(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["gsd-no-open-registry-debt"].status == "pass"
    assert by_id["gsd-no-open-registry-debt"].severity == "ok"
    assert by_id["gsd-planned-inventory-visibility"].status == "fail"
    assert by_id["gsd-planned-inventory-visibility"].severity == "warn"
    assert "M166" in by_id["gsd-planned-inventory-visibility"].observed
    assert by_id["gsd-phase-complete-consistent"].status == "pass"


def test_code_complete_lag_warns_when_summary_exists_but_marker_open(
    tmp_path: Path,
) -> None:
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Active Milestone:** M166-iyy4ak: Review Governance\n"
        "**Phase:** planning\n\n"
        "## Milestone Registry\n"
        "- ✅ **M165-2som4e:** Temporal ontology\n"
        "- ⬜ **M166-iyy4ak:** Review Governance\n",
        encoding="utf-8",
    )
    mdir = state / "milestones" / "M166-iyy4ak"
    mdir.mkdir(parents=True)
    (mdir / "M166-iyy4ak-SUMMARY.md").write_text("# summary\n", encoding="utf-8")
    from law_nexus_harness.governor import check_gsd_residual_debt

    findings = check_gsd_residual_debt(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["gsd-code-complete-lag"].status == "fail"
    assert by_id["gsd-code-complete-lag"].severity == "warn"
    assert "M166" in by_id["gsd-code-complete-lag"].observed


def test_gsd_review_dual_truth_warns_when_dt_lag_matches_active(tmp_path: Path) -> None:
    """Declared DT-lag for active hard-open milestone is advisory warn (D154)."""
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Active Milestone:** M167-odlgt8: NormRule IR\n"
        "**Phase:** evaluating-gates\n\n"
        "## Milestone Registry\n"
        "- ✅ **M166-iyy4ak:** Review Governance\n"
        "- 🔄 **M167-odlgt8:** NormRule IR\n",
        encoding="utf-8",
    )
    bridge = tmp_path / "prd" / "architecture" / "review-cases"
    bridge.mkdir(parents=True)
    (bridge / "gsd-review-bridge.md").write_text(
        "# bridge\n\n```text\nclass: DT-lag\ndelivery_unit=gsd:M167-odlgt8\n```\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_gsd_review_dual_truth

    findings = check_gsd_review_dual_truth(tmp_path)
    assert len(findings) == 1
    assert findings[0].check_id == "gsd-review-dual-truth"
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "M167" in findings[0].observed


def test_gsd_review_dual_truth_pass_when_bridge_absent(tmp_path: Path) -> None:
    from law_nexus_harness.governor import check_gsd_review_dual_truth

    findings = check_gsd_review_dual_truth(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_capability_promotion_board_warns_when_tsg_missing(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "temporal-semantic-gap-register.md").write_text(
        "# gaps\n\n| Gap ID | x |\n|---|---|\n| TSG-001 | a |\n| TSG-002 | b |\n",
        encoding="utf-8",
    )
    (arch / "capability-promotion-board.md").write_text(
        "# board\n\n## Non-authority\n\n"
        "does not close TSG rows; L_capability inventory only.\n\n"
        "| TSG | state |\n|---|---|\n| TSG-001 | S0 |\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_capability_promotion_board

    findings = check_capability_promotion_board(tmp_path)
    assert findings[0].check_id == "capability-promotion-board"
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "TSG-002" in findings[0].observed


def test_capability_promotion_board_pass_when_complete(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "temporal-semantic-gap-register.md").write_text(
        "# gaps\n\n| Gap ID | x |\n|---|---|\n| TSG-001 | a |\n| TSG-002 | b |\n",
        encoding="utf-8",
    )
    (arch / "capability-promotion-board.md").write_text(
        "# board\n\n## Non-authority\n\n"
        "does not close TSG rows; L_capability inventory only.\n\n"
        "| TSG | state |\n|---|---|\n| TSG-001 | S0 |\n| TSG-002 | S1 |\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_capability_promotion_board

    findings = check_capability_promotion_board(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"
    assert "missing_on_board=0" in findings[0].observed


def test_kb_ontology_draft_warns_when_missing(tmp_path: Path) -> None:
    from law_nexus_harness.governor import check_kb_ontology_draft

    findings = check_kb_ontology_draft(tmp_path)
    assert findings[0].check_id == "kb-ontology-draft"
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "missing_files" in findings[0].observed


def test_kb_ontology_draft_pass_when_complete(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology-requirements.md").write_text(
        "# KB\n\n## Non-authority\n\nnot production graph schema; not Applicable.\n\n"
        "| ID | x |\n|---|---|\n" + "\n".join(f"| KBO-R{i:03d} | r |" for i in range(1, 12)) + "\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-l1-l3-draft.md").write_text(
        "# draft\n\nNon-authority: not production graph schema, not Applicable.\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-projection-contract.json").write_text(
        """{
          "schema_version": "law-nexus-kb-ontology-projection/v1",
          "authoritative": false,
          "fsm_state": "O2_decode_lift",
          "node_kinds": [
            {"kind": "Work"},
            {"kind": "Expression"},
            {"kind": "ComponentConcept"},
            {"kind": "ForceStatusEvent"},
            {"kind": "MembershipEdge"}
          ],
          "forbidden_node_kinds": ["ApplicableDecision", "NormativeBlob"]
        }""",
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_decode_lift\n  states:\n    O2_decode_lift:\n      name: lift\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n    - Expression\n    - ComponentConcept\n"
        "    - ForceStatusEvent\n    - MembershipEdge\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n    - NormativeBlob\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_kb_ontology_draft

    findings = check_kb_ontology_draft(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"
    assert "kbo_r_count=" in findings[0].observed


def test_corpus_grounding_pass_when_needle_matches_real_path(tmp_path: Path, monkeypatch) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-hierarchy-registry.yaml").write_text(
        "# fixture registry\n"
        "bindings:\n"
        '  - {path_needle: law_2013-04-05_44-fz, level: glava, number: "1", cc: cc:44-fz:glava-1}\n'
        '  - {path_needle: n-44-fz, level: statya, number: "31", cc: cc:44-fz:statya-31}\n',
        encoding="utf-8",
    )
    edition = (
        tmp_path / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
    )
    edition.mkdir(parents=True)
    (edition / "edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml").write_text(
        "<doc/>", encoding="utf-8"
    )
    monkeypatch.delenv("CONSULTANT_EXPORT_DIR", raising=False)
    from law_nexus_harness.governor import check_corpus_grounding

    findings = check_corpus_grounding(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"
    assert "grounded=1" in findings[0].observed
    assert "ungrounded=1" in findings[0].observed


def test_corpus_grounding_warns_when_no_needle_matches(tmp_path: Path, monkeypatch) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-hierarchy-registry.yaml").write_text(
        "bindings:\n"
        '  - {path_needle: n-44-fz, level: statya, number: "31", cc: cc:44-fz:statya-31}\n',
        encoding="utf-8",
    )
    toy = tmp_path / "consru_export" / "consru_export" / "exports" / "npa"
    toy.mkdir(parents=True)
    (toy / "decree_2020-09-14_558_rev-2024-07-08_a6d600ea.xml").write_text(
        "<doc/>", encoding="utf-8"
    )
    monkeypatch.delenv("CONSULTANT_EXPORT_DIR", raising=False)
    from law_nexus_harness.governor import check_corpus_grounding

    findings = check_corpus_grounding(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "grounded=0" in findings[0].observed


def test_corpus_grounding_skips_without_corpus(tmp_path: Path, monkeypatch) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-hierarchy-registry.yaml").write_text(
        "bindings:\n"
        '  - {path_needle: n-44-fz, level: statya, number: "31", cc: cc:44-fz:statya-31}\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("CONSULTANT_EXPORT_DIR", raising=False)
    from law_nexus_harness.governor import check_corpus_grounding

    findings = check_corpus_grounding(tmp_path)
    assert findings[0].status == "pass"
    assert "skipped" in findings[0].observed


_VALID_DOCUMENT_GROUPS_YAML = (
    "schema_version: law-nexus-kb-ontology/v1\n"
    "authoritative: false\n"
    "fsm:\n  current: O2_catalog_coverage\n  states:\n"
    "    O2_catalog_coverage:\n      name: cov\n"
    "vocabulary:\n"
    "  hierarchy_levels:\n    - statya\n"
    "  node_kinds:\n    - Work\n"
    "  forbidden_node_kinds:\n    - ApplicableDecision\n"
    "  decode_level_aliases:\n"
    "    Statya: statya\n"
    "    Glava: glava\n"
    "document_groups:\n"
    "  non_claims:\n"
    '    - "document group binding is a system_observation heuristic"\n'
    "  structural_roles:\n"
    "    - container\n"
    "    - unit\n"
    "  structural_only_tokens:\n"
    "    - primechanie\n"
    "  groups:\n"
    "    - id: federal_law@v1\n"
    "      granularity: statya\n"
    "      text_boundary: [unit, container]\n"
    "      needles:\n"
    "        - {field: path, needle: federalnyi-zakon, rank: 10}\n"
    "      ladder:\n"
    "        - {token: glava, role: container}\n"
    "        - {token: statya, role: unit}\n"
)


def test_document_groups_coverage_pass_when_complete(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology.yaml").write_text(_VALID_DOCUMENT_GROUPS_YAML, encoding="utf-8")
    from law_nexus_harness.governor import check_document_groups_coverage

    findings = check_document_groups_coverage(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"
    assert "groups=1" in findings[0].observed
    assert "federal_law_v1=present" in findings[0].observed
    assert "catalog_version=fnv1a64-" in findings[0].observed
    assert "not TSG" in findings[0].observed


def test_document_groups_coverage_warns_when_ladder_token_outside_catalog(
    tmp_path: Path,
) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    yaml_text = _VALID_DOCUMENT_GROUPS_YAML.replace(
        "        - {token: statya, role: unit}\n",
        "        - {token: statya, role: unit}\n        - {token: zzz-unknown, role: container}\n",
    )
    (arch / "kb-ontology.yaml").write_text(yaml_text, encoding="utf-8")
    from law_nexus_harness.governor import check_document_groups_coverage

    findings = check_document_groups_coverage(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "token_outside_catalog=zzz-unknown" in findings[0].observed


def test_document_groups_coverage_warns_when_role_outside_closed_list(
    tmp_path: Path,
) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    yaml_text = _VALID_DOCUMENT_GROUPS_YAML.replace(
        "        - {token: glava, role: container}\n",
        "        - {token: glava, role: bogus-role}\n",
    )
    (arch / "kb-ontology.yaml").write_text(yaml_text, encoding="utf-8")
    from law_nexus_harness.governor import check_document_groups_coverage

    findings = check_document_groups_coverage(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "unknown_role=bogus-role" in findings[0].observed


def test_document_groups_coverage_warns_when_federal_law_missing(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    yaml_text = _VALID_DOCUMENT_GROUPS_YAML.replace(
        "    - id: federal_law@v1\n", "    - id: code\n"
    )
    (arch / "kb-ontology.yaml").write_text(yaml_text, encoding="utf-8")
    from law_nexus_harness.governor import check_document_groups_coverage

    findings = check_document_groups_coverage(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "missing_federal_law_v1" in findings[0].observed


def test_document_groups_coverage_warns_when_version_not_detectable(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_catalog_coverage\n  states:\n"
        "    O2_catalog_coverage:\n      name: cov\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_document_groups_coverage

    findings = check_document_groups_coverage(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "not detectable" in findings[0].message


def test_document_groups_section_hash_is_deterministic_fnv1a64() -> None:
    from law_nexus_harness.governor import document_groups_section_hash

    v1 = document_groups_section_hash(_VALID_DOCUMENT_GROUPS_YAML)
    v2 = document_groups_section_hash(_VALID_DOCUMENT_GROUPS_YAML)
    assert v1 == v2
    assert v1.startswith("fnv1a64-")
    assert len(v1) == len("fnv1a64-") + 16
    assert all(c in "0123456789abcdef" for c in v1[len("fnv1a64-") :])
    # Section sensitivity: a one-token edit changes the version (drift is a
    # visible warning, not a silent skip).
    edited = _VALID_DOCUMENT_GROUPS_YAML.replace(
        "        - {token: statya, role: unit}\n",
        '        - {token: statya, role: unit, suffix: ")"}\n',
    )
    assert document_groups_section_hash(edited) != v1
    # Fail-closed: absent section yields an empty version, never a guess.
    assert document_groups_section_hash("schema_version: law-nexus-kb-ontology/v1\n") == ""


def test_corpus_grounding_reports_document_groups_group_needles(
    tmp_path: Path, monkeypatch
) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-hierarchy-registry.yaml").write_text(
        "bindings:\n"
        '  - {path_needle: law_2013-04-05_44-fz, level: statya, number: "31", cc: cc:44-fz:statya-31}\n',
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        _VALID_DOCUMENT_GROUPS_YAML.replace(
            "needle: federalnyi-zakon, rank: 10",
            "needle: law_, rank: 10",
        ),
        encoding="utf-8",
    )
    edition = (
        tmp_path / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
    )
    edition.mkdir(parents=True)
    (edition / "edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml").write_text(
        "<doc/>", encoding="utf-8"
    )
    monkeypatch.delenv("CONSULTANT_EXPORT_DIR", raising=False)
    from law_nexus_harness.governor import check_corpus_grounding

    findings = check_corpus_grounding(tmp_path)
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"
    assert "group_needles_total=1" in findings[0].observed
    assert "group_grounded=1" in findings[0].observed
    assert "group_ungrounded=0" in findings[0].observed


def test_corpus_grounding_warns_when_group_needles_ungrounded(tmp_path: Path, monkeypatch) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-hierarchy-registry.yaml").write_text(
        "bindings:\n"
        '  - {path_needle: law_2013-04-05_44-fz, level: statya, number: "31", cc: cc:44-fz:statya-31}\n',
        encoding="utf-8",
    )
    # Group needle names a corpus path that does not exist -> group_grounded=0.
    (arch / "kb-ontology.yaml").write_text(
        _VALID_DOCUMENT_GROUPS_YAML.replace(
            "needle: federalnyi-zakon, rank: 10",
            "needle: nonexistent-group-path, rank: 10",
        ),
        encoding="utf-8",
    )
    edition = (
        tmp_path / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
    )
    edition.mkdir(parents=True)
    (edition / "edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml").write_text(
        "<doc/>", encoding="utf-8"
    )
    monkeypatch.delenv("CONSULTANT_EXPORT_DIR", raising=False)
    from law_nexus_harness.governor import check_corpus_grounding

    findings = check_corpus_grounding(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "group_grounded=0" in findings[0].observed


def test_kb_ontology_closed_vocab_warns_when_rust_token_missing_from_yaml(
    tmp_path: Path,
) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology-requirements.md").write_text(
        "# KB\n\n## Non-authority\n\nnot production graph schema; not Applicable.\n\n"
        "| ID | x |\n|---|---|\n" + "\n".join(f"| KBO-R{i:03d} | r |" for i in range(1, 12)) + "\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-l1-l3-draft.md").write_text(
        "# draft\n\nNon-authority: not production graph schema, not Applicable.\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-projection-contract.json").write_text(
        """{
          "schema_version": "law-nexus-kb-ontology-projection/v1",
          "authoritative": false,
          "fsm_state": "O2_catalog_coverage",
          "node_kinds": [{"kind": "Work"}],
          "forbidden_node_kinds": ["ApplicableDecision"]
        }""",
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_catalog_coverage\n  states:\n    O2_catalog_coverage:\n      name: cov\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n"
        "  decode_level_aliases:\n    Statya: statya\n"
        "  closed_vocabularies:\n"
        "    - id: decode_hierarchy_level\n"
        "      rust_path: crates/ln-decode/src/domain.rs\n"
        "      rust_enum: HierarchyLevel\n"
        "      yaml_map: decode_level_aliases\n"
        "      compare: variant_names_are_map_keys\n",
        encoding="utf-8",
    )
    rust = tmp_path / "crates" / "ln-decode" / "src"
    rust.mkdir(parents=True)
    (rust / "domain.rs").write_text(
        "pub enum HierarchyLevel {\n    Statya,\n    ExtraLevel,\n}\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_kb_ontology_draft

    findings = check_kb_ontology_draft(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "ExtraLevel" in findings[0].observed


def test_closed_vocab_as_str_stays_inside_named_impl() -> None:
    from law_nexus_harness.governor import _rust_as_str_tokens

    source = Path("crates/ln-temporal/src/domain.rs").read_text(encoding="utf-8")
    tokens = set(_rust_as_str_tokens(source, "ClockKind"))
    assert tokens == {
        "factual_event",
        "proceeding",
        "legal_act_effect",
        "source_publication",
        "system_observation",
    }
    assert "edition_order" not in tokens
    assert "interval_overlap" not in tokens


def test_kb_ontology_assembly_fsm_colliding_with_readiness_is_warned(
    tmp_path: Path,
) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology-requirements.md").write_text(
        "# KB\n\n## Non-authority\n\nnot production graph schema; not Applicable.\n\n"
        "| ID | x |\n|---|---|\n" + "\n".join(f"| KBO-R{i:03d} | r |" for i in range(1, 12)) + "\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-l1-l3-draft.md").write_text(
        "# draft\n\nNon-authority: not production graph schema, not Applicable.\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-projection-contract.json").write_text(
        """{
          "schema_version": "law-nexus-kb-ontology-projection/v1",
          "authoritative": false,
          "fsm_state": "O2_calendar_ordinal",
          "node_kinds": [{"kind": "Work"}],
          "forbidden_node_kinds": ["ApplicableDecision"]
        }""",
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_calendar_ordinal\n  states:\n"
        "    O2_calendar_ordinal:\n      name: calendar\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n"
        "assembly_fsm:\n  current: O2_calendar_ordinal\n  states:\n"
        "    O2_calendar_ordinal:\n      name: leaked\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_kb_ontology_draft

    findings = check_kb_ontology_draft(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "assembly_fsm" in findings[0].observed
    assert "O2_calendar_ordinal" in findings[0].observed


def test_kb_ontology_assembly_fsm_stale_non_claim_is_warned(tmp_path: Path) -> None:
    """non_claims referencing a state that is no longer current must be flagged."""
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology-requirements.md").write_text(
        "# KB\n\n## Non-authority\n\nnot production graph schema; not Applicable.\n\n"
        "| ID | x |\n|---|---|\n" + "\n".join(f"| KBO-R{i:03d} | r |" for i in range(1, 12)) + "\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-l1-l3-draft.md").write_text(
        "# draft\n\nNon-authority: not production graph schema, not Applicable.\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-projection-contract.json").write_text(
        """{
          "schema_version": "law-nexus-kb-ontology-projection/v1",
          "authoritative": false,
          "fsm_state": "O2_calendar_ordinal",
          "node_kinds": [{"kind": "Work"}],
          "forbidden_node_kinds": ["ApplicableDecision"]
        }""",
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_calendar_ordinal\n  states:\n"
        "    O2_calendar_ordinal:\n      name: calendar\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n"
        "assembly_fsm:\n  current: S_commit\n  states:\n"
        "    S_commit:\n      name: append_events\n"
        "  non_claims:\n"
        "    - current S_propose drafts attach from YAML ranks\n"
        "    - not S_fold, not O3 gold\n",
        encoding="utf-8",
    )
    import yaml

    from law_nexus_harness.governor import _kb_assembly_fsm_gaps

    catalog = yaml.safe_load((arch / "kb-ontology.yaml").read_text(encoding="utf-8"))
    gaps = _kb_assembly_fsm_gaps(catalog)
    assert any("stale_state" in g for g in gaps), f"expected stale_state gap, got {gaps}"
    assert any("S_propose" in g for g in gaps)


def test_kb_ontology_assembly_fsm_non_claim_matches_current_passes(tmp_path: Path) -> None:
    """non_claims referencing the actual current must not be flagged."""
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_calendar_ordinal\n  states:\n"
        "    O2_calendar_ordinal:\n      name: calendar\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n"
        "assembly_fsm:\n  current: S_commit\n  states:\n"
        "    S_commit:\n      name: append_events\n"
        "  non_claims:\n"
        "    - current S_commit appends admitted drafts\n"
        "    - not S_fold, not O3 gold\n",
        encoding="utf-8",
    )
    import yaml

    from law_nexus_harness.governor import _kb_assembly_fsm_gaps

    catalog = yaml.safe_load((arch / "kb-ontology.yaml").read_text(encoding="utf-8"))
    gaps = _kb_assembly_fsm_gaps(catalog)
    assert not any("stale_state" in g for g in gaps), f"unexpected stale gap: {gaps}"


def test_kb_ontology_prefix_key_outside_aliases_is_warned(tmp_path: Path) -> None:
    arch = tmp_path / "prd" / "architecture"
    arch.mkdir(parents=True)
    (arch / "kb-ontology-requirements.md").write_text(
        "# KB\n\n## Non-authority\n\nnot production graph schema; not Applicable.\n\n"
        "| ID | x |\n|---|---|\n" + "\n".join(f"| KBO-R{i:03d} | r |" for i in range(1, 12)) + "\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-l1-l3-draft.md").write_text(
        "# draft\n\nNon-authority: not production graph schema, not Applicable.\n",
        encoding="utf-8",
    )
    (arch / "kb-ontology-projection-contract.json").write_text(
        """{
          "schema_version": "law-nexus-kb-ontology-projection/v1",
          "authoritative": false,
          "fsm_state": "O2_decode_prefixes",
          "node_kinds": [{"kind": "Work"}],
          "forbidden_node_kinds": ["ApplicableDecision"]
        }""",
        encoding="utf-8",
    )
    (arch / "kb-ontology.yaml").write_text(
        "schema_version: law-nexus-kb-ontology/v1\n"
        "authoritative: false\n"
        "fsm:\n  current: O2_decode_prefixes\n  states:\n    O2_decode_prefixes:\n      name: prefixes\n"
        "vocabulary:\n  hierarchy_levels:\n    - statya\n"
        "  node_kinds:\n    - Work\n"
        "  forbidden_node_kinds:\n    - ApplicableDecision\n"
        "  decode_level_aliases:\n    Statya: statya\n"
        "  decode_marker_prefixes:\n    Article: [Article]\n",
        encoding="utf-8",
    )
    from law_nexus_harness.governor import check_kb_ontology_draft

    findings = check_kb_ontology_draft(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
    assert "Article" in findings[0].observed


def test_orphan_summary_outside_registry_is_advisory_inventory(tmp_path: Path) -> None:
    """SUMMARY dirs not listed in STATE registry must still surface as lag."""
    state = tmp_path / ".gsd"
    state.mkdir()
    (state / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Active Milestone:** M161-2som4e: Retrieval ranking\n"
        "**Phase:** executing\n\n"
        "## Milestone Registry\n"
        "- ✅ **M160-65pdoz:** Verify Test CI Coverage\n"
        "- 🔄 **M161-2som4e:** Retrieval ranking\n",
        encoding="utf-8",
    )
    orphan = state / "milestones" / "M165-2som4e"
    orphan.mkdir(parents=True)
    (orphan / "M165-2som4e-SUMMARY.md").write_text("# orphan summary\n", encoding="utf-8")
    from law_nexus_harness.governor import check_gsd_residual_debt

    findings = check_gsd_residual_debt(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["gsd-code-complete-lag"].status == "fail"
    assert by_id["gsd-code-complete-lag"].severity == "warn"
    assert "M165" in by_id["gsd-code-complete-lag"].observed
    assert "orphan" in by_id["gsd-code-complete-lag"].observed


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
    assert GovernorEvidence(path="prd/migration/forward-roadmap.md") in finding.evidence
    assert {item.line for item in finding.evidence if item.line is not None} == {3, 4, 5}


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
        "review-case-integrity.open-findings",
        "gsd-planned-inventory-visibility",
        "gsd-code-complete-lag",
        "gsd-review-dual-truth",
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
        "review-case-integrity.open-findings",
        "gsd-planned-inventory-visibility",
        "gsd-code-complete-lag",
        "gsd-review-dual-truth",
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
    assert finding.evidence == (GovernorEvidence(path="crates/ln-fake/src/lib.rs", line=3),)


def test_semantic_stub_in_product_code_unreadable_source_is_tool_error(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "crates" / "ln-scan" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
    original = Path.read_text

    def fail_selected(path: Path, *args, **kwargs):
        if path == source:
            raise OSError("unreadable source")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_selected)
    report = run_governor(tmp_path, check="semantic-stub-in-product-code")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"
    assert report.findings[0].severity == "error"
    assert "unreadable source" not in report.findings[0].observed


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
        "# residual historical hard dependency on decommissioned eras\n"
        "from archived_product import FalkorDBClient\n"
        "def test_falkordb_graph():\n"
        "    assert FalkorDBClient().ping()\n"
    )
    findings = check_historical_test_debt_visibility(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "historical-test-debt-visibility"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "historical_test_count=" in finding.observed
    assert "test_zz_planted.py" in finding.observed


def test_historical_test_debt_unreadable_test_is_tool_error(tmp_path: Path, monkeypatch) -> None:
    test_file = tmp_path / "tests" / "test_policy_history.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_policy(): assert True\n", encoding="utf-8")
    original = Path.read_text

    def fail_selected(path: Path, *args, **kwargs):
        if path == test_file:
            raise OSError("unreadable policy test")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_selected)
    report = run_governor(tmp_path, check="historical-test-debt-visibility")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"
    assert report.findings[0].severity == "error"
    assert "unreadable policy test" not in report.findings[0].observed


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


def test_historical_test_debt_excludes_ci_process_suite_and_anti_era_controls(
    tmp_path: Path,
) -> None:
    """CI process-suite and pure anti-era control language are not residual debt."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    inventory = tmp_path / "prd/migration/decommission/repository-quality-gate.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps(
            {
                "schema_version": "law-nexus/repository-quality-gate/v1",
                "ci_process_suite": ["tests/test_ci_anti_era.py"],
            }
        ),
        encoding="utf-8",
    )
    (tests_dir / "test_ci_anti_era.py").write_text(
        "# active CI process control\n"
        "def test_no_production_falkordb():\n"
        "    assert 'No production-scale FalkorDB claim'\n",
        encoding="utf-8",
    )
    (tests_dir / "test_skill_reject_pyo3.py").write_text(
        "# active skill/process control\n"
        "def test_reject_pyo3():\n"
        "    assert 'Reject PyO3' in skill\n",
        encoding="utf-8",
    )
    (tests_dir / "test_residual_hard_dep.py").write_text(
        "# residual historical hard dependency, not anti-era control\n"
        "from archived_product import FalkorDBClient\n"
        "def test_old_graph():\n"
        "    assert FalkorDBClient().ping()\n",
        encoding="utf-8",
    )
    findings = check_historical_test_debt_visibility(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "test_residual_hard_dep.py" in finding.observed
    assert "test_ci_anti_era.py" not in finding.observed
    assert "test_skill_reject_pyo3.py" not in finding.observed


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


def test_live_document_freshness_trigger_catalog_is_valid() -> None:
    finding = check_document_freshness_triggers(ROOT)[0]

    assert finding.status in {"pass", "fail"}
    assert finding.severity in {"ok", "warn"}
    assert "semantic validation" in finding.observed or finding.status == "fail"


def test_live_freshness_catalog_rejects_derived_matrix_as_sole_companion() -> None:
    catalog = json.loads(
        (ROOT / "prd/architecture/document-freshness-triggers.json").read_text(encoding="utf-8")
    )
    changed = {
        "doc/adr/0009-five-clock-temporal-model.md",
        "prd/architecture/adr-matrix.json",
    }

    assert _freshness_trigger_gaps(catalog, changed) == ["adr-contract-change"]


def test_document_freshness_trigger_gap_requires_distinct_companion() -> None:
    catalog = {
        "schema_version": "law-nexus-document-freshness-triggers/v1",
        "authoritative": False,
        "triggers": [
            {
                "id": "adr-change",
                "sources": ["doc/adr/0*.md"],
                "required_any": ["prd/ARCHITECTURE.md", "doc/adr/README.md"],
                "review": "Recheck lifecycle projection.",
            }
        ],
    }

    assert _freshness_trigger_gaps(catalog, {"doc/adr/0024-new.md"}) == ["adr-change"]
    assert (
        _freshness_trigger_gaps(
            catalog,
            {"doc/adr/0024-new.md", "prd/ARCHITECTURE.md"},
        )
        == []
    )


def test_document_freshness_trigger_catalog_rejects_authority_promotion() -> None:
    catalog = {
        "schema_version": "law-nexus-document-freshness-triggers/v1",
        "authoritative": True,
        "triggers": [
            {
                "id": "x",
                "sources": ["prd/PRODUCT.md"],
                "required_any": ["prd/REQUIREMENTS.md"],
                "review": "Review.",
            }
        ],
    }

    try:
        _freshness_trigger_gaps(catalog, {"prd/PRODUCT.md"})
    except ValueError as error:
        assert "non-authoritative" in str(error)
    else:
        raise AssertionError("authoritative freshness catalog must be rejected")


def test_live_temporal_vocabulary_contract_is_complete() -> None:
    finding = check_temporal_vocabulary_contract(ROOT)[0]

    catalog = json.loads(
        (ROOT / "prd" / "architecture" / "temporal-vocabulary-contract.json").read_text(
            encoding="utf-8"
        )
    )
    expected_terms = len(catalog["rows"])
    expected_gaps = len(catalog["gap_ids"])
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert f"terms={expected_terms}" in finding.observed
    assert f"gaps={expected_gaps}" in finding.observed
    assert "complete glossary-row inventory" in finding.observed
    assert "not semantic validation" in finding.observed


def test_live_temporal_vocabulary_drift_is_clean() -> None:
    finding = check_temporal_vocabulary_drift(ROOT)[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "deprecated aliases" in finding.observed


def _write_temporal_governance_fixture(architecture: Path) -> None:
    (architecture / "glossary-governance.md").write_text(
        "[bounded]` repository-control contract\n"
        "does not define legal meaning\n"
        "must not read the JSON catalog\n",
        encoding="utf-8",
    )


def test_temporal_vocabulary_contract_warns_on_missing_term_and_gap(tmp_path: Path) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    _write_temporal_governance_fixture(architecture)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | canonical | bounded |\n\n"
        "## 4. Next\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "# Gaps\n| TSG-001 | x |\n",
        encoding="utf-8",
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "governance_path": "prd/architecture/glossary-governance.md",
                "governance_required_fragments": [
                    "[bounded]` repository-control contract",
                    "does not define legal meaning",
                    "must not read the JSON catalog",
                ],
                "rows": [
                    {
                        "id": "EvidenceSpan",
                        "needle": "| `EvidenceSpan` |",
                        "required_fragments": ["deferred-undefined"],
                    }
                ],
                "gap_ids": ["TSG-001", "TSG-016"],
            }
        ),
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "term:EvidenceSpan" in finding.observed
    assert "gap:TSG-016" in finding.observed
    assert finding.rule_id == "temporal-vocabulary.contract-gap"


def test_temporal_vocabulary_contract_warns_when_catalog_omits_glossary_row(
    tmp_path: Path,
) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    _write_temporal_governance_fixture(architecture)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | canonical | bounded |\n"
        "| Beta | beta | ADR | canonical | bounded |\n\n"
        "## 4. Next\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "| TSG-001 | gap |\n",
        encoding="utf-8",
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "governance_path": "prd/architecture/glossary-governance.md",
                "governance_required_fragments": [
                    "[bounded]` repository-control contract",
                    "does not define legal meaning",
                    "must not read the JSON catalog",
                ],
                "rows": [
                    {"id": "alpha", "needle": "| Alpha |", "required_fragments": ["canonical"]}
                ],
                "gap_ids": ["TSG-001"],
            }
        ),
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "uncatalogued_glossary=['| Beta |']" in finding.observed


def test_temporal_vocabulary_contract_warns_on_unlisted_register_gap(tmp_path: Path) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    _write_temporal_governance_fixture(architecture)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | canonical | bounded |\n\n"
        "## 4. Next\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "| TSG-001 | gap |\n| TSG-002 | gap |\n",
        encoding="utf-8",
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "governance_path": "prd/architecture/glossary-governance.md",
                "governance_required_fragments": [
                    "[bounded]` repository-control contract",
                    "does not define legal meaning",
                    "must not read the JSON catalog",
                ],
                "rows": [
                    {"id": "alpha", "needle": "| Alpha |", "required_fragments": ["canonical"]}
                ],
                "gap_ids": ["TSG-001"],
            }
        ),
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "uncatalogued_gaps=['TSG-002']" in finding.observed


def test_temporal_vocabulary_contract_rejects_catalog_row_outside_glossary(
    tmp_path: Path,
) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    _write_temporal_governance_fixture(architecture)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | canonical | bounded |\n\n"
        "## 4. Next\n\n| Beta | decoy | ADR | canonical | bounded |\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "| TSG-001 | gap |\n", encoding="utf-8"
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "governance_path": "prd/architecture/glossary-governance.md",
                "governance_required_fragments": [
                    "[bounded]` repository-control contract",
                    "does not define legal meaning",
                    "must not read the JSON catalog",
                ],
                "rows": [
                    {"id": "alpha", "needle": "| Alpha |", "required_fragments": ["canonical"]},
                    {"id": "beta", "needle": "| Beta |", "required_fragments": ["canonical"]},
                ],
                "gap_ids": ["TSG-001"],
            }
        ),
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert "stale_catalog_glossary=['| Beta |']" in finding.observed


def test_temporal_vocabulary_contract_ignores_decoy_row_before_glossary(
    tmp_path: Path,
) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    _write_temporal_governance_fixture(architecture)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n| Alpha | decoy | ADR | canonical | bounded |\n\n"
        "## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | proposed | bounded |\n\n"
        "## 4. Next\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "| TSG-001 | gap |\n", encoding="utf-8"
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "governance_path": "prd/architecture/glossary-governance.md",
                "governance_required_fragments": [
                    "[bounded]` repository-control contract",
                    "does not define legal meaning",
                    "must not read the JSON catalog",
                ],
                "rows": [
                    {"id": "alpha", "needle": "| Alpha |", "required_fragments": ["canonical"]}
                ],
                "gap_ids": ["TSG-001"],
            }
        ),
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert "term:alpha" in finding.observed


def test_temporal_vocabulary_contract_requires_declared_governance_surface(
    tmp_path: Path,
) -> None:
    prd = tmp_path / "prd"
    architecture = prd / "architecture"
    architecture.mkdir(parents=True)
    (prd / "temporal-legal-model.md").write_text(
        "# Model\n\n## 3. Glossary and ownership\n\n"
        "| Term | Meaning | Owner | Status | Boundary |\n"
        "|------|---------|-------|--------|----------|\n"
        "| Alpha | alpha | ADR | canonical | bounded |\n\n## 4. Next\n",
        encoding="utf-8",
    )
    (architecture / "temporal-semantic-gap-register.md").write_text(
        "| TSG-001 | gap |\n", encoding="utf-8"
    )
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "coverage_mode": "complete-glossary-table",
                "model_path": "prd/temporal-legal-model.md",
                "gap_register_path": "prd/architecture/temporal-semantic-gap-register.md",
                "rows": [
                    {"id": "alpha", "needle": "| Alpha |", "required_fragments": ["canonical"]}
                ],
                "gap_ids": ["TSG-001"],
            }
        ),
        encoding="utf-8",
    )

    report = run_governor(tmp_path, check="temporal-vocabulary-contract")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"


def test_temporal_vocabulary_drift_warns_on_unqualified_deprecated_alias(
    tmp_path: Path,
) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0018-normative-state-resolver.md").write_text(
        "# Resolver\n\nThe NormativeStatus resolver returns Unknown.\n",
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_drift(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "0018-normative-state-resolver.md:3:NormativeStatus" in finding.observed
    assert finding.rule_id == "temporal-vocabulary.unqualified-alias"


def _write_temporal_presentation_catalog(root: Path) -> None:
    architecture = root / "prd" / "architecture"
    architecture.mkdir(parents=True, exist_ok=True)
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "presentation_drift": {
                    "scan_patterns": [
                        "prd/project-state/roadmap.md",
                        "prd/migration/*.md",
                        "doc/adr/0*.md",
                    ],
                    "deferred_terms": ["EvidenceSpan", "SourceBlock"],
                    "presentation_cues": ["real ", "fixtures", "implemented"],
                    "presentation_qualifiers": ["future-schema", "deferred-undefined"],
                    "interval_fields": ["effective_from"],
                    "source_truth_cues": ["source truth", "canonical field"],
                    "interval_qualifiers": ["projection-only", "not source truth"],
                    "clock_tokens": ["own clock", "sixth core clock"],
                    "clock_qualifiers": ["not a sixth", "over the five", "five clocks"],
                },
            }
        ),
        encoding="utf-8",
    )


def test_temporal_vocabulary_presentation_drift_warns_on_deferred_type(
    tmp_path: Path,
) -> None:
    _write_temporal_presentation_catalog(tmp_path)
    roadmap = tmp_path / "prd" / "project-state"
    roadmap.mkdir(parents=True)
    (roadmap / "roadmap.md").write_text(
        "Real EvidenceSpan fixtures are bounded.\n",
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_presentation_drift(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert finding.rule_id == "temporal-vocabulary.deferred-as-present"
    assert "prd/project-state/roadmap.md:1:EvidenceSpan" in finding.observed


def test_temporal_vocabulary_presentation_drift_warns_on_sixth_clock_like_wording(
    tmp_path: Path,
) -> None:
    _write_temporal_presentation_catalog(tmp_path)
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0020-judicial-fas-practice-overlay.md").write_text(
        "Practice has its own clock.\n",
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_presentation_drift(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.rule_id == "temporal-vocabulary.sixth-clock-like"
    assert "0020-judicial-fas-practice-overlay.md:1:own clock" in finding.observed


def test_temporal_vocabulary_presentation_drift_accepts_explicit_qualifiers(
    tmp_path: Path,
) -> None:
    _write_temporal_presentation_catalog(tmp_path)
    roadmap = tmp_path / "prd" / "project-state"
    roadmap.mkdir(parents=True)
    (roadmap / "roadmap.md").write_text(
        "Future-schema EvidenceSpan remains deferred-undefined.\n",
        encoding="utf-8",
    )
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0020-judicial-fas-practice-overlay.md").write_text(
        "Practice has first-class temporality over the five clocks, not a sixth core clock.\n",
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_presentation_drift(tmp_path)[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"


def test_temporal_vocabulary_presentation_drift_warns_on_static_interval_source_truth(
    tmp_path: Path,
) -> None:
    _write_temporal_presentation_catalog(tmp_path)
    migration = tmp_path / "prd" / "migration"
    migration.mkdir(parents=True)
    (migration / "rust-migration-roadmap.md").write_text(
        "effective_from is a canonical field and source truth.\n",
        encoding="utf-8",
    )

    finding = check_temporal_vocabulary_presentation_drift(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.rule_id == "temporal-vocabulary.static-interval-as-source"
    assert "rust-migration-roadmap.md:1:effective_from" in finding.observed


def test_temporal_vocabulary_presentation_policy_parse_failure_is_tool_error(
    tmp_path: Path,
) -> None:
    architecture = tmp_path / "prd" / "architecture"
    architecture.mkdir(parents=True)
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": False,
                "presentation_drift": {"scan_patterns": []},
            }
        ),
        encoding="utf-8",
    )

    report = run_governor(tmp_path, check="temporal-vocabulary-presentation-drift")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"


def test_temporal_vocabulary_catalog_rejects_authority_promotion(tmp_path: Path) -> None:
    architecture = tmp_path / "prd" / "architecture"
    architecture.mkdir(parents=True)
    (architecture / "temporal-vocabulary-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "law-nexus-temporal-vocabulary-contract/v1",
                "authoritative": True,
            }
        ),
        encoding="utf-8",
    )

    report = run_governor(tmp_path, check="temporal-vocabulary-contract")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"


def test_live_published_trace_contract_covers_consequential_chains() -> None:
    finding = check_published_trace_contract(ROOT)[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "chains=20" in finding.observed


def test_published_trace_contract_warns_on_broken_chain_and_authority_boundary(
    tmp_path: Path,
) -> None:
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "PRODUCT.md").write_text(
        "| PC-001 | RQ-001 | 0004 | tests/x.rs | bounded |\n",
        encoding="utf-8",
    )
    (prd / "REQUIREMENTS.md").write_text(
        "| RQ-001 | obligation | PC-999 | active `[bounded]` | process-gate | 0004 | tests/x.rs | no product proof |\n",
        encoding="utf-8",
    )
    (prd / "ARCHITECTURE.md").write_text("ADR-0004 [bounded]\n", encoding="utf-8")
    assessment = tmp_path / "assessment"
    assessment.mkdir()
    (assessment / "01-authority-map.md").write_text(
        "Assessment is accepted product proof.\n",
        encoding="utf-8",
    )

    finding = check_published_trace_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "PC-001/RQ-001:requirements-link" in finding.observed
    assert "assessment-process-only-boundary" in finding.observed
    assert GovernorEvidence(path="prd/REQUIREMENTS.md", line=1) in finding.evidence
    assert GovernorEvidence(path="assessment/01-authority-map.md") in finding.evidence


def test_published_trace_contract_rejects_undeclared_future_clause(tmp_path: Path) -> None:
    prd = tmp_path / "prd"
    prd.mkdir()
    (prd / "PRODUCT.md").write_text(
        "| PC-021 | future | `[proposed]` | none-design | none | absent | hostile | none |\n",
        encoding="utf-8",
    )
    (prd / "REQUIREMENTS.md").write_text(
        "| RQ-021 | future | PC-021 | `[proposed]` | none-design | none | absent | none |\n",
        encoding="utf-8",
    )
    (prd / "ARCHITECTURE.md").write_text("# A\n", encoding="utf-8")
    assessment = tmp_path / "assessment"
    assessment.mkdir()
    (assessment / "01-authority-map.md").write_text(
        "AssessmentPacket is process evidence and not product proof.\n",
        encoding="utf-8",
    )

    finding = check_published_trace_contract(tmp_path)[0]

    assert finding.status == "fail"
    assert "undeclared-published:PC-021" in finding.observed
    assert "undeclared-published:RQ-021" in finding.observed
    assert GovernorEvidence(path="prd/PRODUCT.md", line=1) in finding.evidence
    assert GovernorEvidence(path="prd/REQUIREMENTS.md", line=1) in finding.evidence


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


def test_archive_path_policy_warns_when_not_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("law_nexus_harness.governor._git_tracked_paths", lambda root, path: [])
    (tmp_path / ".gitignore").write_text("# empty policy\n", encoding="utf-8")
    findings = check_archive_path_policy(tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "archive-path-policy"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing_gitignore=" in finding.observed


def test_archive_path_policy_warns_on_active_alias_into_vault(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("law_nexus_harness.governor._git_tracked_paths", lambda root, path: [])
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


def test_archive_path_policy_warns_on_unlisted_symlink_into_vault(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("law_nexus_harness.governor._git_tracked_paths", lambda root, path: [])
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


def test_archive_path_policy_passes_when_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("law_nexus_harness.governor._git_tracked_paths", lambda root, path: [])
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
    findings = check_archive_path_policy(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == "pass"
    assert findings[0].severity == "ok"


def test_archive_path_policy_reports_tool_error_when_git_inventory_fails(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / ".gitignore").write_text("# inventory must run\n", encoding="utf-8")

    def unavailable(*args, **kwargs):
        raise OSError("git unavailable")

    monkeypatch.setattr("law_nexus_harness.governor.subprocess.run", unavailable)
    report = run_governor(tmp_path, check="archive-path-policy")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].check_id == "archive-path-policy"
    assert report.findings[0].rule_id == "tool-error"
    assert report.findings[0].severity == "error"


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
    assert finding.evidence == (GovernorEvidence(path="doc/adr/README.md", line=3),)


def test_adr_doc_matrix_coverage_rejects_gsd_only_projection(tmp_path: Path) -> None:
    gsd = tmp_path / ".gsd"
    gsd.mkdir()
    ontology_ids = " ".join(f"ADR-{number:04d}" for number in range(16, 23))
    (gsd / "REQUIREMENTS.md").write_text(f"# R\n[proposed] {ontology_ids}\n", encoding="utf-8")
    (gsd / "PROJECT.md").write_text(f"# P\n[proposed] {ontology_ids}\n", encoding="utf-8")

    finding = check_adr_doc_matrix_coverage(tmp_path)[0]

    assert finding.check_id == "adr-doc-matrix-coverage"
    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "prd/PRODUCT.md:missing_file" in finding.observed
    assert "prd/REQUIREMENTS.md:missing_file" in finding.observed
    assert ".gsd" not in finding.observed


def test_adr_doc_matrix_coverage_requires_proposed_ceiling(tmp_path: Path) -> None:
    prd = tmp_path / "prd"
    prd.mkdir()
    ontology_ids = " ".join(f"ADR-{number:04d}" for number in range(16, 23))
    (prd / "PRODUCT.md").write_text(f"# Product\n[proposed] {ontology_ids}\n", encoding="utf-8")
    (prd / "REQUIREMENTS.md").write_text(
        f"# Requirements\n[validated] {ontology_ids}\n", encoding="utf-8"
    )

    finding = check_adr_doc_matrix_coverage(tmp_path)[0]

    assert finding.status == "fail"
    assert "prd/REQUIREMENTS.md:ADR-0016:expected=proposed" in finding.observed
    assert GovernorEvidence(path="prd/REQUIREMENTS.md", line=2) in finding.evidence
    assert all(item.line == 2 for item in finding.evidence)


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
    assert finding.evidence == (GovernorEvidence(path="doc/adr/0004-bad.md", line=3),)


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
    assert GovernorEvidence(path="README.md") in finding.evidence
    assert GovernorEvidence(path="doc/adr/0004-rust.md", line=1) in finding.evidence


def test_adr_link_integrity_allows_existing_relative_target_and_fragment(
    tmp_path: Path,
) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-source.md").write_text(
        "# ADR-0004\n\nSee [the target](0005-target.md#decision).\n",
        encoding="utf-8",
    )
    (adr / "0005-target.md").write_text(
        "# ADR-0005\n\n## Decision\n\nBounded decision.\n",
        encoding="utf-8",
    )

    finding = check_adr_link_integrity(tmp_path)[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"


def test_adr_link_integrity_detects_missing_target_and_fragment(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-source.md").write_text(
        "# ADR-0004\n\n"
        "See [missing file](0099-missing.md) and "
        "[missing section](0005-target.md#absent).\n",
        encoding="utf-8",
    )
    (adr / "0005-target.md").write_text(
        "# ADR-0005\n\n## Decision\n\nBounded decision.\n",
        encoding="utf-8",
    )

    finding = check_adr_link_integrity(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing-target" in finding.observed
    assert "missing-fragment" in finding.observed
    assert {item.line for item in finding.evidence} == {3}
    assert "Bounded decision" not in finding.observed


def test_adr_review_date_staleness_allows_absent_and_future_dates(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-undated.md").write_text(
        "---\nid: ADR-0004\n---\n",
        encoding="utf-8",
    )
    (adr / "0005-future.md").write_text(
        "---\nid: ADR-0005\nreview_by: 2026-08-12\nrevisit_by: 2027-01-01\n---\n",
        encoding="utf-8",
    )

    finding = check_adr_review_date_staleness(tmp_path, as_of=date(2026, 8, 12))[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert "optional_dates=2" in finding.observed


def test_adr_review_date_staleness_warns_on_stale_and_invalid_dates(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-review.md").write_text(
        "---\nid: ADR-0004\nreview_by: 2026-08-11\nrevisit_by: not-a-date\n---\n",
        encoding="utf-8",
    )

    findings = check_adr_review_date_staleness(tmp_path, as_of=date(2026, 8, 12))
    by_rule = {finding.rule_id: finding for finding in findings}

    assert set(by_rule) == {"adr-review-date.stale", "adr-review-date.invalid"}
    assert all(finding.status == "fail" for finding in findings)
    assert all(finding.severity == "warn" for finding in findings)
    assert by_rule["adr-review-date.stale"].evidence == (
        GovernorEvidence(path="doc/adr/0004-review.md", line=3),
    )
    assert by_rule["adr-review-date.invalid"].evidence == (
        GovernorEvidence(path="doc/adr/0004-review.md", line=4),
    )


def test_adr_review_date_unreadable_file_is_tool_error(tmp_path: Path, monkeypatch) -> None:
    adr_file = tmp_path / "doc" / "adr" / "0004-review.md"
    adr_file.parent.mkdir(parents=True)
    adr_file.write_text("---\nid: ADR-0004\n---\n", encoding="utf-8")
    original = Path.read_text

    def fail_selected(path: Path, *args, **kwargs):
        if path == adr_file:
            raise OSError("private unreadable detail")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_selected)
    report = run_governor(tmp_path, check="adr-review-date-staleness")

    assert report.status == "failure"
    assert report.tool_error_count == 1
    assert report.findings[0].rule_id == "tool-error"
    assert "private unreadable detail" not in report.findings[0].observed


def test_adr_review_date_warning_preserves_default_and_strict_exit_codes(
    tmp_path: Path, capsys
) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-review.md").write_text(
        "---\nid: ADR-0004\nreview_by: 2000-01-01\n---\n",
        encoding="utf-8",
    )

    default_code = main(
        ["governor", "--root", str(tmp_path), "--check", "adr-review-date-staleness"]
    )
    default_payload = json.loads(capsys.readouterr().out)
    strict_code = main(
        [
            "governor",
            "--root",
            str(tmp_path),
            "--check",
            "adr-review-date-staleness",
            "--fail-on-warn",
        ]
    )
    strict_payload = json.loads(capsys.readouterr().out)

    assert default_code == 0
    assert strict_code == 1
    assert default_payload["findings"][0]["severity"] == "warn"
    assert strict_payload["findings"][0]["severity"] == "warn"


def test_adr_supersession_graph_allows_reciprocal_partial_edge(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-old.md").write_text(
        "---\nid: ADR-0004\nsuperseded_by: [ADR-0005#scope-a]\n---\n",
        encoding="utf-8",
    )
    (adr / "0005-new.md").write_text(
        "---\nid: ADR-0005\nsupersedes: [ADR-0004#scope-a]\n---\n",
        encoding="utf-8",
    )

    finding = check_adr_supersession_graph(tmp_path)[0]

    assert finding.status == "pass"
    assert finding.severity == "ok"


def test_adr_supersession_graph_rejects_legacy_active_key(tmp_path: Path) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-legacy.md").write_text(
        "---\nid: ADR-0004\nsuperseds: none\n---\n",
        encoding="utf-8",
    )

    finding = check_adr_supersession_graph(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "legacy-key:ADR-0004:superseds" in finding.observed
    assert finding.evidence[0].line == 3


def test_adr_supersession_graph_detects_missing_nonreciprocal_and_cycle(
    tmp_path: Path,
) -> None:
    adr = tmp_path / "doc" / "adr"
    adr.mkdir(parents=True)
    (adr / "0004-a.md").write_text(
        "---\nid: ADR-0004\nsupersedes: [ADR-0005#scope-a, ADR-0099]\n---\n",
        encoding="utf-8",
    )
    (adr / "0005-b.md").write_text(
        "---\nid: ADR-0005\nsupersedes: [ADR-0004#scope-a]\n---\n",
        encoding="utf-8",
    )

    finding = check_adr_supersession_graph(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing-target" in finding.observed
    assert "non-reciprocal" in finding.observed
    assert "cycle" in finding.observed
    assert {item.path for item in finding.evidence} == {
        "doc/adr/0004-a.md",
        "doc/adr/0005-b.md",
    }


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
    assert finding.evidence == (GovernorEvidence(path="prd/ARCHITECTURE.md", line=3),)


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
    assert finding.evidence == (GovernorEvidence(path="prd/ARCHITECTURE.md", line=3),)


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


# .gitignore tabby-upload companion


# model-crystal-anchors companion
def _write_crystal_fixture(
    root: Path,
    *,
    quote: str = "Snapshot \u2260 commit",
    digest_override: str | None = None,
) -> None:
    crystal = root / "prd" / "architecture" / "model-crystal.md"
    crystal.parent.mkdir(parents=True, exist_ok=True)
    source = root / "doc" / "review" / "review-25-08-2026.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source_text = "Snapshot \u2260 commit\n"
    source.write_text(source_text, encoding="utf-8")
    digest = digest_override or hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    sections = "\n".join(
        f"## {name}"
        for name in ("Layer 0", "Layer 1", "Reality boundary", "Non-claims", "Grounding")
    )
    inv_rows = "\n".join(f"| INV-{i:02d} | invariant row |" for i in range(1, 11))
    crystal.write_text(
        "Source: sha256:"
        + digest
        + "\n"
        + sections
        + "\n"
        + inv_rows
        + "\n"
        + f'<!-- anchor: review \u00a7A.2 "{quote}" -->\n',
        encoding="utf-8",
    )


def test_model_crystal_anchors_pass_on_live_repo() -> None:
    findings = check_model_crystal_anchors(ROOT)
    assert findings, "live repo must produce at least one finding"
    assert all(finding.status == "pass" for finding in findings)


def test_model_crystal_anchors_warn_on_quote_drift(tmp_path: Path) -> None:
    _write_crystal_fixture(tmp_path, quote="phrase absent from the L0 source")

    findings = check_model_crystal_anchors(tmp_path)
    failed = [finding for finding in findings if finding.status == "fail"]
    assert failed, "drifted anchor quote must surface a finding"
    assert all(finding.severity == "warn" for finding in failed)
    assert any("anchor" in finding.message.lower() for finding in failed)


def test_model_crystal_anchors_warn_on_source_digest_drift(tmp_path: Path) -> None:
    _write_crystal_fixture(tmp_path, digest_override="0" * 64)

    findings = check_model_crystal_anchors(tmp_path)
    failed = [finding for finding in findings if finding.status == "fail"]
    assert failed
    assert any("digest" in finding.message.lower() for finding in failed)


def test_model_crystal_anchors_warn_when_crystal_absent(tmp_path: Path) -> None:
    findings = check_model_crystal_anchors(tmp_path)
    assert findings[0].status == "fail"
    assert findings[0].severity == "warn"
