from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-architecture-graph.py"
ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
REPORT_MD_PATH = ROOT / "prd/architecture/architecture_report.md"
FIXTURE_DIR = ROOT / "tests/fixtures/architecture"


def load_verifier_module() -> Any:
    spec = importlib.util.spec_from_file_location("architecture_verifier", SCRIPT_PATH)
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
    assert summary["non_authoritative"] is True
    assert "non-authoritative" in summary["boundary"]
    assert summary["items"] == 23
    assert summary["edges"] == 17


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


def test_anchor_line_ranges_must_be_ordered_and_in_bounds(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    write_jsonl(
        items_path,
        [
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
    assert "id=REQ-REVERSED-LINES" in result.stderr
    assert "rule=source-anchor-line-range" in result.stderr
    assert "id=REQ-OUT-OF-RANGE-LINES" in result.stderr
    assert "line_end exceeds file length" in result.stderr


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
