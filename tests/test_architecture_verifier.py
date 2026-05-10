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
    write_jsonl(items_path, [{"record_kind": "item", "id": "NODE-A"}])
    write_jsonl(edges_path, [{"record_kind": "edge", "id": "EDGE-A", "from": "NODE-A", "to": "NODE-A"}])

    result = run_cli("--items", str(items_path), "--edges", str(edges_path))

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["non_authoritative"] is True
    assert "non-authoritative" in summary["boundary"]
    assert summary["upstream_checks"] == "skipped-custom-paths"
