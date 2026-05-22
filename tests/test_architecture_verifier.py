from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-architecture-graph.py"
GENERATOR_SCRIPT_PATH = ROOT / "scripts/generate-architecture-views.py"
ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
REPORT_MD_PATH = ROOT / "prd/architecture/architecture_report.md"
ARCHITECTURE_README_PATH = ROOT / "prd/architecture/README.md"
FIXTURE_DIR = ROOT / "tests/fixtures/architecture"


def load_verifier_module() -> Any:
    spec = importlib.util.spec_from_file_location("architecture_verifier", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_view_generator_module() -> Any:
    spec = importlib.util.spec_from_file_location("architecture_view_generator", GENERATOR_SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def minimal_item(record_id: str, source_anchors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "legalgraph-architecture-registry/v1",
        "record_kind": "item",
        "id": record_id,
        "type": "requirement",
        "title": f"{record_id} title",
        "summary": "Minimal verifier fixture record.",
        "layer": "architecture-governance",
        "status": "active",
        "proof_level": "source-anchor",
        "risk_level": "medium",
        "source_anchors": source_anchors,
        "owner": "M004/S04",
        "verification": "Verified by architecture verifier tests.",
        "generated_draft": False,
        "non_claims": [],
    }


def minimal_edge(record_id: str, source_anchors: list[dict[str, Any]], *, from_id: str = "NODE-A", to_id: str = "NODE-A") -> dict[str, Any]:
    return {
        "schema_version": "legalgraph-architecture-registry/v1",
        "record_kind": "edge",
        "id": record_id,
        "from": from_id,
        "to": to_id,
        "type": "depends_on",
        "status": "active",
        "rationale": "Minimal verifier fixture edge.",
        "source_anchors": source_anchors,
        "generated_draft": False,
    }


def test_baseline_cli_passes_with_non_authoritative_summary() -> None:
    result = run_cli()

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["failure_count"] == 0
    assert summary["upstream_checks"] == "passed"
    assert summary["non_authoritative"] is True
    assert "non-authoritative" in summary["boundary"]
    assert summary["items"] == 63
    assert summary["edges"] == 98


def test_gsd_report_contract_documents_minimal_non_authoritative_fields() -> None:
    readme = ARCHITECTURE_README_PATH.read_text(encoding="utf-8")
    generator = GENERATOR_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Minimal GSD validation report contract" in readme
    for required_field in [
        "Priority buckets",
        "Promotion blockers",
        "Typed drift classes",
        "R035 gate status",
        "Claim-safety buckets",
    ]:
        assert required_field in readme

    for drift_kind in [
        "freshness-drift",
        "source-anchor-drift",
        "graph-integrity-drift",
        "decision-fitness-drift",
        "proof-gate-drift",
        "contradiction-drift",
        "overclaim-drift",
    ]:
        assert drift_kind in readme

    assert "no dashboard or" in generator.lower()
    assert "interactive graph UI" in generator
    assert "not a dashboard, interactive graph UI, or broad visualization project" in readme
    assert "generated reports remain derived planning artifacts" in readme


def test_upstream_check_nonzero_is_stable_diagnostic_without_rewriting(tmp_path: Path, monkeypatch: Any) -> None:
    verifier = load_verifier_module()
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[-1] == "--check" and "extract-prd-architecture-items.py" in command[-2]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="stale generated output: fixtures are old\nsecond line")
        return subprocess.CompletedProcess(command, 0, stdout="architecture graph outputs are current\n", stderr="")

    before_items = ITEMS_PATH.read_bytes()
    before_report = REPORT_JSON_PATH.read_bytes()
    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    exit_code = verifier.run([])

    assert exit_code == 1
    assert calls, "verifier should invoke upstream freshness checks for default paths"
    assert ITEMS_PATH.read_bytes() == before_items
    assert REPORT_JSON_PATH.read_bytes() == before_report
    assert verifier.LAST_RESULT is not None
    formatted = "\n".join(diagnostic.format() for diagnostic in verifier.LAST_RESULT.diagnostics)
    assert "rule=upstream-s02-check" in formatted
    assert "stale generated output" in formatted


def test_malformed_jsonl_surfaces_rule_file_and_line(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    items_path.write_text('{"record_kind":"item","id":"OK"}\n{"record_kind":', encoding="utf-8")
    edges_path.write_text("", encoding="utf-8")

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "rule=malformed-jsonl" in result.stderr
    assert "items.jsonl:2" in result.stderr
    assert "id=<unknown>" in result.stderr


def test_wrong_record_kind_and_duplicate_ids_are_hard_failures(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    write_jsonl(
        items_path,
        [
            {"record_kind": "item", "id": "DUPLICATE"},
            {"record_kind": "item", "id": "DUPLICATE"},
        ],
    )
    write_jsonl(edges_path, [{"record_kind": "item", "id": "EDGE-WRONG"}])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "rule=duplicate-id" in result.stderr
    assert "rule=record-kind" in result.stderr
    assert "id=EDGE-WRONG" in result.stderr


def test_missing_report_output_default_gate_becomes_upstream_s03_diagnostic(monkeypatch: Any) -> None:
    verifier = load_verifier_module()

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if "build-architecture-graph.py" in command[-2]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="missing report output: prd/architecture/architecture_report.md")
        return subprocess.CompletedProcess(command, 0, stdout="architecture JSONL outputs are current\n", stderr="")

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    exit_code = verifier.run([])

    assert exit_code == 1
    assert verifier.LAST_RESULT is not None
    formatted = "\n".join(diagnostic.format() for diagnostic in verifier.LAST_RESULT.diagnostics)
    assert "rule=upstream-s03-check" in formatted
    assert "missing report output" in formatted


def test_typed_drift_diagnostic_marks_only_freshness_as_safe_to_regenerate(monkeypatch: Any) -> None:
    verifier = load_verifier_module()

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if "extract-prd-architecture-items.py" in command[-2]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="stale generated output: architecture_items.jsonl")
        return subprocess.CompletedProcess(command, 0, stdout="architecture graph outputs are current\n", stderr="")

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    exit_code = verifier.run([])

    assert exit_code == 1
    assert verifier.LAST_RESULT is not None
    formatted = "\n".join(diagnostic.format() for diagnostic in verifier.LAST_RESULT.diagnostics)
    assert "drift_kind=freshness-drift" in formatted
    assert "safe_to_regenerate=true" in formatted
    assert "remediation_hint=regenerate-derived-artifact-after-confirming-source-evidence-is-current" in formatted
    summary = verifier.LAST_RESULT.summary()
    assert summary["drift_counts"]["freshness-drift"] >= 1


def test_typed_drift_diagnostic_for_source_anchor_is_not_auto_regenerable() -> None:
    result = run_cli("--items", str(FIXTURE_DIR / "invalid_stale_anchor.jsonl"), "--edges", str(FIXTURE_DIR / "valid_edges.jsonl"))

    assert result.returncode == 1
    assert "id=REQ-STALE-ANCHOR" in result.stderr
    assert "drift_kind=source-anchor-drift" in result.stderr
    assert "field=source_anchors[0].path" in result.stderr
    assert "affected_field=source_anchors[0].path" in result.stderr
    assert "safe_to_regenerate=false" in result.stderr
    assert "remediation_hint=edit-authoritative-source-anchor-or-source-evidence-then-regenerate-derived-projections" in result.stderr


def test_typed_drift_diagnostic_classes_cover_policy_failures(tmp_path: Path) -> None:
    active_contradiction = run_cli(
        "--items",
        str(FIXTURE_DIR / "valid_items.jsonl"),
        "--edges",
        str(FIXTURE_DIR / "invalid_active_contradiction_edges.jsonl"),
    )
    assert active_contradiction.returncode == 1
    assert "drift_kind=contradiction-drift" in active_contradiction.stderr

    no_gate = run_cli("--items", str(FIXTURE_DIR / "invalid_high_risk_no_gate.jsonl"), "--edges", str(tmp_path / "empty-edges.jsonl"))
    assert no_gate.returncode == 1
    assert "drift_kind=decision-fitness-drift" in no_gate.stderr

    overclaim_edges = tmp_path / "empty-edges-overclaim.jsonl"
    overclaim_edges.write_text("", encoding="utf-8")
    overclaim = run_cli("--items", str(FIXTURE_DIR / "invalid_forbidden_overclaim.jsonl"), "--edges", str(overclaim_edges))
    assert overclaim.returncode == 1
    assert "drift_kind=overclaim-drift" in overclaim.stderr
    assert "safe_to_regenerate=false" in overclaim.stderr


def test_representative_drift_policies_are_diagnostics_not_repair_claims() -> None:
    verifier = load_verifier_module()
    representative_rules = {
        "upstream-s02-check": "freshness-drift",
        "source-anchor-exists": "source-anchor-drift",
        "missing-endpoint": "graph-integrity-drift",
        "decision-fitness": "decision-fitness-drift",
        "proof-gate-metadata": "proof-gate-drift",
        "active-contradiction": "contradiction-drift",
        "forbidden-overclaim": "overclaim-drift",
    }

    for rule, drift_kind in representative_rules.items():
        policy = verifier.drift_policy_for_rule(rule)
        assert policy.drift_kind == drift_kind
        assert "repair completed" not in policy.remediation_hint
        assert "source repaired" not in policy.remediation_hint
        assert "proof passed" not in policy.remediation_hint

    assert verifier.drift_policy_for_rule("upstream-s02-check").safe_to_regenerate is True
    for rule in representative_rules.keys() - {"upstream-s02-check"}:
        assert verifier.drift_policy_for_rule(rule).safe_to_regenerate is False


def test_generated_health_view_surfaces_drift_counts_as_non_authoritative_diagnostics() -> None:
    generator = load_view_generator_module()
    report = {
        "counts": {"nodes": 1, "edges": 0},
        "layer_coverage": {"counts": {"architecture-governance": 1}, "missing_layers": [], "invalid_layers": []},
        "unresolved_proof_gates": [],
        "orphan_findings": [],
        "high_risk_nodes": [],
        "contradiction_edges": [],
        "non_claims_summary": {"nodes_with_non_claims": 0, "total_non_claims": 0, "by_node": []},
        "drift_counts": {
            "freshness-drift": 1,
            "source-anchor-drift": 2,
            "overclaim-drift": 1,
        },
    }

    content = generator.render_health_dashboard(report)

    assert "## Drift Diagnostics" in content
    assert "| Drift Diagnostics | 4 |" in content
    assert "| freshness-drift | 1 |" in content
    assert "| source-anchor-drift | 2 |" in content
    assert "| overclaim-drift | 1 |" in content
    assert "non-authoritative diagnostics only" in content
    assert "do not prove product readiness" in content
    assert "repair authoritative sources" in content
    assert "repair completed" not in content.lower()
    assert "source repaired" not in content.lower()


def test_current_generated_views_do_not_claim_repair_or_proof_completion() -> None:
    for path in (
        ROOT / "prd/architecture/architecture_health.md",
        ROOT / "prd/architecture/product_readiness_blockers.md",
        ROOT / "prd/architecture/claims_ledger.md",
    ):
        content = path.read_text(encoding="utf-8").lower()
        assert "repair completed" not in content
        assert "source repaired" not in content
        assert "auto-repaired" not in content
        assert "proof completed" not in content


def test_custom_paths_skip_upstream_and_preserve_summary_boundary(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    write_jsonl(items_path, [minimal_item("NODE-A", anchor)])
    write_jsonl(edges_path, [minimal_edge("EDGE-A", anchor)])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["non_authoritative"] is True
    assert "non-authoritative" in summary["boundary"]
    assert summary["upstream_checks"] == "skipped-custom-paths"


def test_schema_anchor_rules_reject_missing_and_unknown_fields(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    missing_path = minimal_item("REQ-MISSING-PATH", [{"kind": "prd", "selector": "anything"}])
    unknown_field = minimal_item(
        "REQ-UNKNOWN-FIELD",
        [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}],
    )
    unknown_field["unexpected"] = True
    bad_enum = minimal_item(
        "REQ-BAD-ENUM",
        [{"path": "prd/architecture/architecture.schema.json", "kind": "not-a-kind", "selector": "record_kind"}],
    )
    write_jsonl(items_path, [missing_path, unknown_field, bad_enum])
    edges_path.write_text("", encoding="utf-8")

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-MISSING-PATH" in result.stderr
    assert "field=source_anchors[0].path" in result.stderr
    assert "rule=required" in result.stderr
    assert "id=REQ-UNKNOWN-FIELD" in result.stderr
    assert "field=unexpected" in result.stderr
    assert "rule=additionalProperties=false" in result.stderr
    assert "id=REQ-BAD-ENUM" in result.stderr
    assert "field=source_anchors[0].kind" in result.stderr
    assert "rule=enum" in result.stderr


def test_missing_anchor_fixture_is_schema_failure() -> None:
    result = run_cli("--items", str(FIXTURE_DIR / "invalid_missing_anchor.jsonl"), "--edges", str(FIXTURE_DIR / "valid_edges.jsonl"))

    assert result.returncode == 1
    assert "id=REQ-MISSING-ANCHOR" in result.stderr
    assert "field=source_anchors" in result.stderr
    assert "rule=minItems=1" in result.stderr
    assert "source_anchor=<no-source-anchor>" in result.stderr


def test_anchor_paths_must_exist_and_stay_repository_local(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    write_jsonl(
        items_path,
        [
            minimal_item("REQ-ABSOLUTE-PATH", [{"path": "/tmp/architecture.md", "kind": "prd", "selector": "anything"}]),
            minimal_item("REQ-LOCAL-EXEC-PATH", [{"path": ".gsd/exec/run.stdout", "kind": "runtime-artifact"}]),
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(FIXTURE_DIR / "valid_edges.jsonl"))

    assert result.returncode == 1
    assert "id=REQ-ABSOLUTE-PATH" in result.stderr
    assert "rule=source-anchor-path-local" in result.stderr
    assert "id=REQ-LOCAL-EXEC-PATH" in result.stderr
    assert "rule=source-anchor-path-local" in result.stderr


def test_stale_anchor_fixture_reports_missing_source_file() -> None:
    result = run_cli("--items", str(FIXTURE_DIR / "invalid_stale_anchor.jsonl"), "--edges", str(FIXTURE_DIR / "valid_edges.jsonl"))

    assert result.returncode == 1
    assert "id=REQ-STALE-ANCHOR" in result.stderr
    assert "field=source_anchors[0].path" in result.stderr
    assert "rule=source-anchor-exists" in result.stderr
    assert "prd/architecture/does-not-exist.md" in result.stderr


def test_anchor_line_ranges_must_be_bounded_ordered_and_in_bounds(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    write_jsonl(
        items_path,
        [
            minimal_item(
                "REQ-UNBOUNDED-LINE-START",
                [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "line_start": 1}],
            ),
            minimal_item(
                "REQ-REVERSED-LINES",
                [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "line_start": 2, "line_end": 1}],
            ),
            minimal_item(
                "REQ-OUT-OF-RANGE-LINES",
                [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "line_start": 1, "line_end": 9999}],
            ),
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(FIXTURE_DIR / "valid_edges.jsonl"))

    assert result.returncode == 1
    assert "id=REQ-UNBOUNDED-LINE-START" in result.stderr
    assert "failure_class=unbounded-line-range" in result.stderr
    assert "anchor_kind=test-artifact" in result.stderr
    assert "remediation_class=add-source-anchor" in result.stderr
    assert "id=REQ-REVERSED-LINES" in result.stderr
    assert "failure_class=reversed-line-range" in result.stderr
    assert "id=REQ-OUT-OF-RANGE-LINES" in result.stderr
    assert "failure_class=line-range-out-of-bounds" in result.stderr


def test_anchor_symlink_resolving_into_gsd_is_rejected_without_raw_content(tmp_path: Path, monkeypatch: Any) -> None:
    verifier = load_verifier_module()
    repo_root = tmp_path / "repo"
    gsd_dir = repo_root / ".gsd"
    gsd_dir.mkdir(parents=True)
    gsd_target = gsd_dir / "summary.md"
    gsd_target.write_text("SECRET LEGAL TEXT selector-token\n", encoding="utf-8")
    (repo_root / "evidence.md").symlink_to(gsd_target)

    record = minimal_item(
        "REQ-SYMLINK-GSD",
        [{"path": "evidence.md", "kind": "gsd-summary", "selector": "selector-token"}],
    )
    located = verifier.LocatedRecord(path=repo_root / "items.jsonl", line_number=1, record=record)
    result = verifier.VerificationResult()
    monkeypatch.setattr(verifier, "ROOT", repo_root)

    verifier.validate_source_anchors([located], result)

    formatted = "\n".join(diagnostic.format() for diagnostic in result.diagnostics)
    assert "id=REQ-SYMLINK-GSD" in formatted
    assert "rule=source-anchor-resolved-local" in formatted
    assert "field=source_anchors[0].path" in formatted
    assert "anchor_path=evidence.md" in formatted
    assert "anchor_kind=gsd-summary" in formatted
    assert "failure_class=unsafe-resolved-gsd-target" in formatted
    assert "remediation_class=add-source-anchor" in formatted
    assert "SECRET LEGAL TEXT" not in formatted


def test_anchor_selector_or_section_must_appear_but_path_only_json_anchor_can_pass(tmp_path: Path) -> None:
    path_only_items = tmp_path / "path-only-items.jsonl"
    path_only_edges = tmp_path / "path-only-edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact"}]
    write_jsonl(path_only_items, [minimal_item("REQ-PATH-ONLY", anchor)])
    write_jsonl(path_only_edges, [minimal_edge("EDGE-PATH-ONLY-SELF", anchor, from_id="REQ-PATH-ONLY", to_id="REQ-PATH-ONLY")])

    passing = run_cli("--items", str(path_only_items), "--edges", str(path_only_edges))
    assert passing.returncode == 0, passing.stderr

    failing = run_cli(
        "--items",
        str(FIXTURE_DIR / "invalid_selector_anchor.jsonl"),
        "--edges",
        str(FIXTURE_DIR / "valid_edges.jsonl"),
    )
    assert failing.returncode == 1
    assert "id=REQ-SELECTOR-ANCHOR" in failing.stderr
    assert "field=source_anchors[0].selector" in failing.stderr
    assert "rule=source-anchor-token" in failing.stderr


def decision_item(record_id: str, anchor: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    record = minimal_item(record_id, anchor)
    record.update(
        {
            "type": "decision",
            "deciders": ["gsd-agent"],
            "decision_drivers": ["Exercise verifier decision policy."],
            "considered_options": [
                {
                    "id": f"OPT-{record_id}",
                    "title": "Fixture option",
                    "summary": "Fixture option summary.",
                    "status": "chosen",
                }
            ],
            "positive_consequences": ["Fixture consequence."],
        }
    )
    record.update(overrides)
    return record


def proof_gate_item(record_id: str, anchor: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    record = minimal_item(record_id, anchor)
    record.update({"type": "proof_gate", "proof_level": "none", "risk_level": "high"})
    record.update(overrides)
    return record


def workflow_check_item(record_id: str, anchor: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    record = minimal_item(record_id, anchor)
    record.update({"type": "workflow_check", "proof_level": "static-check", "risk_level": "medium"})
    record.update(overrides)
    return record


def test_missing_edge_endpoint_is_hard_graph_failure(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    write_jsonl(items_path, [minimal_item("REQ-NODE-A", anchor)])
    write_jsonl(edges_path, [minimal_edge("EDGE-MISSING-ENDPOINT", anchor, from_id="REQ-NODE-A", to_id="REQ-NODE-MISSING")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=EDGE-MISSING-ENDPOINT" in result.stderr
    assert "record_kind=edge" in result.stderr
    assert "field=to" in result.stderr
    assert "rule=missing-endpoint" in result.stderr
    assert "REQ-NODE-MISSING" in result.stderr


def test_traceability_critical_orphans_fail_but_evidence_and_assumption_isolates_do_not(tmp_path: Path) -> None:
    orphan_result = run_cli("--items", str(FIXTURE_DIR / "invalid_orphan_requirement.jsonl"), "--edges", str(tmp_path / "empty-edges.jsonl"))
    assert orphan_result.returncode == 1
    assert "id=REQ-ORPHAN-TRACEABILITY" in orphan_result.stderr
    assert "rule=orphan-traceability" in orphan_result.stderr

    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "empty-edges.jsonl"
    edges_path.write_text("", encoding="utf-8")
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    evidence = minimal_item("EVID-ISOLATED", anchor)
    evidence.update({"type": "evidence", "status": "bounded-evidence"})
    assumption = minimal_item("ASSUMP-ISOLATED", anchor)
    assumption.update({"type": "assumption"})
    write_jsonl(items_path, [evidence, assumption])

    nonfatal_result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert nonfatal_result.returncode == 0, nonfatal_result.stderr


def test_active_unresolved_gate_requires_metadata_but_baseline_owned_gates_pass(tmp_path: Path) -> None:
    result = run_cli("--items", str(FIXTURE_DIR / "invalid_gate_metadata.jsonl"), "--edges", str(tmp_path / "empty-edges.jsonl"))

    assert result.returncode == 1
    assert "id=GATE-MISSING-METADATA" in result.stderr
    assert "rule=proof-gate-metadata" in result.stderr
    assert "field=owner" in result.stderr
    assert "field=verification" in result.stderr
    assert "field=source_anchors" in result.stderr


def test_decision_consequence_supersession_and_high_risk_gate_policies(tmp_path: Path) -> None:
    empty_edges = tmp_path / "empty-edges.jsonl"
    empty_edges.write_text("", encoding="utf-8")

    no_consequence = run_cli("--items", str(FIXTURE_DIR / "invalid_decision_no_consequence.jsonl"), "--edges", str(empty_edges))
    assert no_consequence.returncode == 1
    assert "id=DEC-NO-CONSEQUENCE" in no_consequence.stderr
    assert "rule=decision-consequence" in no_consequence.stderr

    no_successor = run_cli("--items", str(FIXTURE_DIR / "invalid_superseded_no_successor.jsonl"), "--edges", str(empty_edges))
    assert no_successor.returncode == 1
    assert "id=DEC-SUPERSEDED-NO-SUCCESSOR" in no_successor.stderr
    assert "rule=decision-supersession" in no_successor.stderr

    no_gate = run_cli("--items", str(FIXTURE_DIR / "invalid_high_risk_no_gate.jsonl"), "--edges", str(empty_edges))
    assert no_gate.returncode == 1
    assert "id=DEC-HIGH-RISK-NO-GATE" in no_gate.stderr
    assert "rule=decision-fitness" in no_gate.stderr


def test_decision_policy_accepts_successor_and_gate_coverage(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    old_decision = decision_item(
        "DEC-OLD",
        anchor,
        status="superseded",
        risk_level="medium",
        superseded_by="DEC-NEW",
    )
    new_decision = decision_item("DEC-NEW", anchor, risk_level="high")
    check = workflow_check_item("CHECK-DECISION", anchor)
    write_jsonl(items_path, [old_decision, new_decision, check])
    write_jsonl(
        edges_path,
        [
            minimal_edge("EDGE-NEW-SUPERSEDES-OLD", anchor, from_id="DEC-NEW", to_id="DEC-OLD")
            | {"type": "supersedes"},
            minimal_edge("EDGE-NEW-CHECKED-BY-CHECK", anchor, from_id="DEC-NEW", to_id="CHECK-DECISION")
            | {"type": "checked_by", "status": "validated"},
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr


def test_active_contradiction_edge_fails_but_rejected_contradiction_is_nonfatal(tmp_path: Path) -> None:
    active_result = run_cli(
        "--items",
        str(FIXTURE_DIR / "valid_items.jsonl"),
        "--edges",
        str(FIXTURE_DIR / "invalid_active_contradiction_edges.jsonl"),
    )
    assert active_result.returncode == 1
    assert "id=EDGE-ACTIVE-CONTRADICTION" in active_result.stderr
    assert "rule=active-contradiction" in active_result.stderr

    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    write_jsonl(items_path, [minimal_item("REQ-NODE-A", anchor), minimal_item("REQ-NODE-B", anchor)])
    write_jsonl(
        edges_path,
        [minimal_edge("EDGE-REJECTED-CONTRADICTION", anchor, from_id="REQ-NODE-A", to_id="REQ-NODE-B") | {"type": "contradicts", "status": "rejected"}],
    )

    rejected_result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert rejected_result.returncode == 0, rejected_result.stderr


def test_forbidden_positive_product_overclaim_is_hard_failure(tmp_path: Path) -> None:
    edges_path = tmp_path / "empty-edges.jsonl"
    edges_path.write_text("", encoding="utf-8")

    result = run_cli("--items", str(FIXTURE_DIR / "invalid_forbidden_overclaim.jsonl"), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-FORBIDDEN-OVERCLAIM" in result.stderr
    assert "record_kind=item" in result.stderr
    assert "field=title" in result.stderr
    assert "rule=forbidden-overclaim" in result.stderr
    assert "production ready" in result.stderr


def test_forbidden_overclaim_categories_fail_with_precise_fields(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    edges_path.write_text("", encoding="utf-8")
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    generated_cypher = minimal_item("REQ-GENERATED-CYPHER-SAFE", anchor)
    generated_cypher["summary"] = "Generated Cypher is safe for unrestricted execution by the product."
    retrieval = minimal_item("REQ-RETRIEVAL-QUALITY-PROVEN", anchor)
    retrieval["verification"] = "Retrieval quality is proven for legal answers."
    llm = minimal_item("REQ-LLM-AUTHORITY", anchor)
    llm["implications"] = ["LLM output is authoritative legal guidance for users."]
    legal_answer = minimal_item("REQ-LEGAL-ANSWER-CORRECT", anchor)
    legal_answer["positive_consequences"] = ["Legal answers are correct for real matters."]
    falkordb = minimal_item("REQ-FALKORDB-PRODUCTION-SCALE", anchor)
    falkordb["summary"] = "FalkorDB production scale is validated for LegalGraph workloads."
    odt = minimal_item("REQ-ODT-PARSER-COMPLETE", anchor)
    odt["summary"] = "The ODT parser is complete and production ready."
    knowql = minimal_item("REQ-KNOWQL-RUNTIME-PROVEN", anchor)
    knowql["summary"] = "Legal KnowQL runtime and parser are proven for production use."
    write_jsonl(items_path, [generated_cypher, retrieval, llm, legal_answer, falkordb, odt, knowql])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    for record_id in (
        "REQ-GENERATED-CYPHER-SAFE",
        "REQ-RETRIEVAL-QUALITY-PROVEN",
        "REQ-LLM-AUTHORITY",
        "REQ-LEGAL-ANSWER-CORRECT",
        "REQ-FALKORDB-PRODUCTION-SCALE",
        "REQ-ODT-PARSER-COMPLETE",
        "REQ-KNOWQL-RUNTIME-PROVEN",
    ):
        assert f"id={record_id}" in result.stderr
    assert result.stderr.count("rule=forbidden-overclaim") >= 7


def test_negative_guardrails_and_non_claim_boundaries_do_not_fail_overclaim_scan(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    guardrail = minimal_item("REQ-NEGATED-GUARDRAIL", anchor)
    guardrail.update(
        {
            "summary": "This workflow does not validate product/runtime/legal claims or production retrieval quality.",
            "verification": "No generated Cypher safety, LLM authority, legal-answer correctness, or ODT parser completeness is proven here.",
            "non_claims": [
                "Does not prove LegalGraph product readiness.",
                "Does not prove FalkorDB production scale.",
                "Does not prove Legal KnowQL runtime/parser behavior.",
            ],
        }
    )
    boundary = minimal_item("REQ-NON-CLAIM-BOUNDARY", anchor)
    boundary.update(
        {
            "summary": "The architecture registry is non-authoritative and must not be used as legal authority.",
            "negative_consequences": ["Legal answers are not correct merely because a derived verifier passes."],
            "non_claims": ["LLM output is not authoritative legal guidance."],
        }
    )
    write_jsonl(items_path, [guardrail, boundary])
    write_jsonl(edges_path, [minimal_edge("EDGE-GUARDRAIL", anchor, from_id="REQ-NEGATED-GUARDRAIL", to_id="REQ-NON-CLAIM-BOUNDARY")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr



def test_claim_lifecycle_rejects_unverified_validated_promotion(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    unverified = minimal_item("REQ-UNVERIFIED-VALIDATED", anchor)
    unverified.update({"status": "validated", "proof_level": "source-anchor"})
    write_jsonl(items_path, [unverified])
    write_jsonl(edges_path, [minimal_edge("EDGE-SELF", anchor, from_id="REQ-UNVERIFIED-VALIDATED", to_id="REQ-UNVERIFIED-VALIDATED")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-UNVERIFIED-VALIDATED" in result.stderr
    assert "rule=claim-lifecycle" in result.stderr
    assert "current_status=validated" in result.stderr
    assert "forbidden_transition=unverified-to-validated" in result.stderr
    assert "remediation=add-evidence-class-or-downgrade-claim" in result.stderr


def test_claim_lifecycle_rejects_deferred_or_rejected_records_used_as_proof(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    deferred_evidence = minimal_item("EVID-DEFERRED-PROOF", anchor)
    deferred_evidence.update({"type": "evidence", "status": "deferred"})
    rejected_evidence = minimal_item("EVID-REJECTED-PROOF", anchor)
    rejected_evidence.update({"type": "evidence", "status": "rejected"})
    requirement = minimal_item("REQ-ACTIVE-CLAIM", anchor)
    write_jsonl(items_path, [deferred_evidence, rejected_evidence, requirement])
    write_jsonl(
        edges_path,
        [
            minimal_edge("EDGE-DEFERRED-SATISFIES", anchor, from_id="EVID-DEFERRED-PROOF", to_id="REQ-ACTIVE-CLAIM")
            | {"type": "satisfies"},
            minimal_edge("EDGE-REJECTED-EVIDENCES", anchor, from_id="EVID-REJECTED-PROOF", to_id="REQ-ACTIVE-CLAIM")
            | {"type": "evidenced_by"},
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=EDGE-DEFERRED-SATISFIES" in result.stderr
    assert "current_status=deferred" in result.stderr
    assert "forbidden_transition=deferred-claim-used-as-proof" in result.stderr
    assert "id=EDGE-REJECTED-EVIDENCES" in result.stderr
    assert "current_status=rejected" in result.stderr
    assert "forbidden_transition=rejected-claim-used-as-proof" in result.stderr
    assert "remediation=supersede-or-reject-edge-or-downgrade-claim" in result.stderr


def test_claim_lifecycle_allows_proposed_and_bounded_records_without_proof_use(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    proposed = minimal_item("EVID-PROPOSED-IDEA", anchor)
    proposed.update({"type": "evidence", "status": "proposed", "proof_level": "none"})
    bounded = minimal_item("EVID-BOUNDED-IDEA", anchor)
    bounded.update({"type": "evidence", "status": "bounded-evidence", "proof_level": "runtime-smoke"})
    write_jsonl(items_path, [proposed, bounded])
    write_jsonl(edges_path, [minimal_edge("EDGE-IDEA-DEPENDENCY", anchor, from_id="EVID-PROPOSED-IDEA", to_id="EVID-BOUNDED-IDEA")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr


def test_claim_lifecycle_preserve_as_backlog_allows_low_priority_deferred_ideas(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "empty-edges.jsonl"
    edges_path.write_text("", encoding="utf-8")
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    backlog_idea = minimal_item("EVID-PRESERVE-BACKLOG", anchor)
    backlog_idea.update(
        {
            "type": "evidence",
            "status": "deferred",
            "proof_level": "none",
            "priority": "low",
            "summary": "Preserve as backlog only; this is not promoted architecture proof.",
            "verification": "Preserve-as-backlog fixture must not fail unless the idea is used as proof.",
            "non_claims": ["Does not validate or promote this backlog idea."],
        }
    )
    write_jsonl(items_path, [backlog_idea])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["failure_count"] == 0


def test_claim_lifecycle_unsafe_promotion_diagnostic_names_priority_status_and_remediation(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    promoted_without_proof = minimal_item("REQ-UNSAFE-PROMOTION", anchor)
    promoted_without_proof.update({"status": "validated", "proof_level": "source-anchor", "priority": "high"})
    write_jsonl(items_path, [promoted_without_proof])
    write_jsonl(edges_path, [minimal_edge("EDGE-UNSAFE-PROMOTION-SELF", anchor, from_id="REQ-UNSAFE-PROMOTION", to_id="REQ-UNSAFE-PROMOTION")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-UNSAFE-PROMOTION" in result.stderr
    assert "rule=claim-lifecycle" in result.stderr
    assert "priority=high" in result.stderr
    assert "lifecycle_status=validated" in result.stderr
    assert "failure_class=unsafe-promotion" in result.stderr
    assert "remediation_class=add-evidence-or-downgrade" in result.stderr


def test_evidence_class_boundary_rejects_validated_unit_test_without_test_artifact(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "runtime-artifact", "selector": "record_kind"}]
    validated = minimal_item("EVID-UNIT-TEST-WITH-RUNTIME-ONLY", anchor)
    validated.update({"type": "evidence", "status": "validated", "proof_level": "unit-test", "priority": "high"})
    write_jsonl(items_path, [validated])
    write_jsonl(edges_path, [minimal_edge("EDGE-UNIT-TEST-SELF", anchor, from_id="EVID-UNIT-TEST-WITH-RUNTIME-ONLY", to_id="EVID-UNIT-TEST-WITH-RUNTIME-ONLY")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=EVID-UNIT-TEST-WITH-RUNTIME-ONLY" in result.stderr
    assert "field=source_anchors" in result.stderr
    assert "rule=evidence-class-boundary" in result.stderr
    assert "proof_level=unit-test" in result.stderr
    assert "current_evidence_classes=runtime-artifact" in result.stderr
    assert "required_evidence_class=test-artifact" in result.stderr
    assert "failure_class=proof-level-evidence-class-mismatch" in result.stderr
    assert "remediation_class=add-evidence-class" in result.stderr


def test_evidence_class_boundary_rejects_derived_report_as_proof_anchor(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture_report.md", "kind": "manual-note", "selector": "Architecture Graph Report"}]
    claim = minimal_item("REQ-DERIVED-REPORT-AS-PROOF", anchor)
    write_jsonl(items_path, [claim])
    write_jsonl(edges_path, [minimal_edge("EDGE-DERIVED-REPORT-SELF", anchor, from_id="REQ-DERIVED-REPORT-AS-PROOF", to_id="REQ-DERIVED-REPORT-AS-PROOF")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-DERIVED-REPORT-AS-PROOF" in result.stderr
    assert "rule=evidence-class-boundary" in result.stderr
    assert "proof_level=source-anchor" in result.stderr
    assert "failure_class=derived-artifact-used-as-proof" in result.stderr
    assert "anchor_path=prd/architecture/architecture_report.md" in result.stderr


def test_claim_lifecycle_proof_from_backlog_diagnostic_names_priority_status_and_remediation(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    backlog_idea = minimal_item("EVID-BACKLOG-PROOF", anchor)
    backlog_idea.update({"type": "evidence", "status": "deferred", "proof_level": "none", "priority": "low"})
    active_claim = minimal_item("REQ-ACTIVE-NEEDS-PROOF", anchor)
    write_jsonl(items_path, [backlog_idea, active_claim])
    write_jsonl(
        edges_path,
        [minimal_edge("EDGE-BACKLOG-PROOF", anchor, from_id="EVID-BACKLOG-PROOF", to_id="REQ-ACTIVE-NEEDS-PROOF") | {"type": "evidenced_by"}],
    )

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=EDGE-BACKLOG-PROOF" in result.stderr
    assert "endpoint=EVID-BACKLOG-PROOF" in result.stderr
    assert "priority=low" in result.stderr
    assert "lifecycle_status=deferred" in result.stderr
    assert "failure_class=proof-from-backlog" in result.stderr
    assert "remediation_class=supersede-reject-or-downgrade" in result.stderr


def test_report_markdown_positive_overclaim_is_hard_failure(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    report_path = tmp_path / "architecture_report.md"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    write_jsonl(items_path, [minimal_item("REQ-REPORT-SCAN", anchor)])
    write_jsonl(edges_path, [minimal_edge("EDGE-REPORT-SCAN", anchor, from_id="REQ-REPORT-SCAN", to_id="REQ-REPORT-SCAN")])
    report_path.write_text("# Report\n\nThe LegalGraph product is production ready for legal answers.\n", encoding="utf-8")

    result = run_cli("--items", str(items_path), "--edges", str(edges_path), "--report-md", str(report_path))

    assert result.returncode == 1
    assert "architecture_report.md" in result.stderr
    assert "rule=forbidden-overclaim" in result.stderr
    assert "record_kind=derived-report" in result.stderr


def test_ontology_promotion_gate_rejects_validated_standard_without_required_proof(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact"}]
    claim = minimal_item("REQ-AKOMA-VALIDATED-OVERREACH", anchor)
    claim.update(
        {
            "summary": "Akoma Ntoso projection is validated for the architecture registry.",
            "status": "validated",
            "proof_level": "source-anchor",
            "priority": "high",
        }
    )
    write_jsonl(items_path, [claim])
    write_jsonl(edges_path, [minimal_edge("EDGE-AKOMA-SELF", anchor, from_id="REQ-AKOMA-VALIDATED-OVERREACH", to_id="REQ-AKOMA-VALIDATED-OVERREACH")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-AKOMA-VALIDATED-OVERREACH" in result.stderr
    assert "rule=ontology-promotion-gate" in result.stderr
    assert "r035_trigger=Akoma Ntoso" in result.stderr
    assert "failure_class=missing-source-mapping" in result.stderr
    assert "failure_class=missing-proof-gate" in result.stderr
    assert "required_gate_ids=GATE-AKOMA-FRBR-NORMALIZATION" in result.stderr
    assert "failure_class=proof-level-overreach" in result.stderr
    assert "required_proof_level=static-check" in result.stderr


def test_ontology_promotion_gate_allows_bounded_research_candidate(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    candidate = minimal_item("EVID-LKIF-CANDIDATE", anchor)
    candidate.update(
        {
            "type": "evidence",
            "summary": "LKIF deontic mapping remains a bounded proof-gated candidate only.",
            "status": "bounded-evidence",
            "proof_level": "source-anchor",
            "non_claims": ["Does not validate LKIF conformance or legal correctness."],
        }
    )
    write_jsonl(items_path, [candidate])
    write_jsonl(edges_path, [minimal_edge("EDGE-LKIF-SELF", anchor, from_id="EVID-LKIF-CANDIDATE", to_id="EVID-LKIF-CANDIDATE")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr


def test_ontology_promotion_gate_allows_proposed_external_standard_with_boundary_language(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    candidate = minimal_item("REQ-LEGALDOCML-PROPOSED-CANDIDATE", anchor)
    candidate.update(
        {
            "summary": "LegalDocML remains a non-authoritative candidate mapping for future ontology research only.",
            "status": "proposed",
            "proof_level": "none",
            "priority": "low",
            "non_claims": ["Does not prove LegalDocML compatibility or production readiness."],
        }
    )
    write_jsonl(items_path, [candidate])
    write_jsonl(edges_path, [minimal_edge("EDGE-LEGALDOCML-SELF", anchor, from_id="REQ-LEGALDOCML-PROPOSED-CANDIDATE", to_id="REQ-LEGALDOCML-PROPOSED-CANDIDATE")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr


def test_ontology_promotion_gate_rejects_research_candidate_without_boundary_language(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    candidate = minimal_item("REQ-OWL-PROPOSED-OPEN", anchor)
    candidate.update(
        {
            "summary": "OWL 2 formal alignment for the architecture registry.",
            "status": "proposed",
            "proof_level": "none",
            "priority": "low",
        }
    )
    write_jsonl(items_path, [candidate])
    write_jsonl(edges_path, [minimal_edge("EDGE-OWL-SELF", anchor, from_id="REQ-OWL-PROPOSED-OPEN", to_id="REQ-OWL-PROPOSED-OPEN")])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-OWL-PROPOSED-OPEN" in result.stderr
    assert "rule=ontology-promotion-gate" in result.stderr
    assert "r035_trigger=OWL" in result.stderr
    assert "failure_class=status-overreach" in result.stderr
    assert "current_status=proposed" in result.stderr
    assert "remediation=add-non-authoritative-boundary-language-or-downgrade-claim" in result.stderr


def test_ontology_promotion_gate_names_missing_owner_and_status(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    missing_owner = minimal_item("REQ-AKOMA-MISSING-OWNER", anchor)
    missing_owner.update(
        {
            "summary": "Akoma Ntoso projection is validated only for this static fixture.",
            "status": "validated",
            "proof_level": "static-check",
            "priority": "high",
        }
    )
    del missing_owner["owner"]
    missing_status = minimal_item("REQ-RUSLEGALCORE-MISSING-STATUS", anchor)
    missing_status.update(
        {
            "summary": "RusLegalCore scope is validated only for this static fixture.",
            "proof_level": "static-check",
            "priority": "high",
        }
    )
    del missing_status["status"]
    akoma_gate = proof_gate_item("GATE-AKOMA-FRBR-NORMALIZATION", anchor, status="active", verification="Static fixture gate.")
    ruslegalcore_gate = proof_gate_item("GATE-RUSLEGALCORE-SCOPE", anchor, status="active", verification="Static fixture gate.")
    write_jsonl(items_path, [missing_owner, missing_status, akoma_gate, ruslegalcore_gate])
    write_jsonl(
        edges_path,
        [
            minimal_edge("EDGE-AKOMA-MISSING-OWNER-GATE", anchor, from_id="REQ-AKOMA-MISSING-OWNER", to_id="GATE-AKOMA-FRBR-NORMALIZATION")
            | {"type": "checked_by", "status": "validated"},
            minimal_edge("EDGE-RUSLEGALCORE-MISSING-STATUS-GATE", anchor, from_id="REQ-RUSLEGALCORE-MISSING-STATUS", to_id="GATE-RUSLEGALCORE-SCOPE")
            | {"type": "checked_by", "status": "validated"},
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 1
    assert "id=REQ-AKOMA-MISSING-OWNER" in result.stderr
    assert "rule=ontology-promotion-gate" in result.stderr
    assert "failure_class=missing-owner" in result.stderr
    assert "field=owner" in result.stderr
    assert "id=REQ-RUSLEGALCORE-MISSING-STATUS" in result.stderr
    assert "failure_class=missing-status" in result.stderr
    assert "field=status" in result.stderr
    assert "current_status=<missing-status>" in result.stderr


def test_ontology_promotion_gate_accepts_validated_claim_with_mapping_gate_and_proof(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    anchor = [{"path": "prd/architecture/architecture.schema.json", "kind": "test-artifact", "selector": "record_kind"}]
    claim = minimal_item("REQ-AKOMA-VALIDATED-WITH-GATE", anchor)
    claim.update(
        {
            "summary": "Akoma Ntoso projection is validated only for the tested architecture schema fixture.",
            "status": "validated",
            "proof_level": "static-check",
            "priority": "high",
        }
    )
    gate = proof_gate_item(
        "GATE-AKOMA-FRBR-NORMALIZATION",
        anchor,
        status="active",
        verification="Static fixture validates bounded Akoma/FRBR source-preserving projection only.",
    )
    write_jsonl(items_path, [claim, gate])
    write_jsonl(
        edges_path,
        [
            minimal_edge("EDGE-AKOMA-CHECKED-BY-GATE", anchor, from_id="REQ-AKOMA-VALIDATED-WITH-GATE", to_id="GATE-AKOMA-FRBR-NORMALIZATION")
            | {"type": "checked_by", "status": "validated"},
        ],
    )

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr
