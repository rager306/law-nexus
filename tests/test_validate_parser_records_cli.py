from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/validate-parser-records.py"
EXAMPLE_DIR = ROOT / "prd/parser/examples"
SCHEMA_DIR = ROOT / "prd/parser/schemas"
CONTRACT_REPORT = ROOT / "prd/parser/parser_record_contract.md"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_summary(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_write_then_check_generates_fresh_contract_artifacts() -> None:
    result = run_cli("--write")
    assert result.returncode == 0, result.stderr
    summary = parse_summary(result)
    assert summary["status"] == "pass"
    assert summary["non_authoritative"] is True
    assert str(Path("prd/parser/schemas/parser_record.schema.json")) in summary["written"]
    assert (SCHEMA_DIR / "parser_record.schema.json").is_file()
    assert CONTRACT_REPORT.is_file()

    check = run_cli("--check")
    assert check.returncode == 0, check.stdout + check.stderr
    check_summary = parse_summary(check)
    assert check_summary["status"] == "pass"
    assert check_summary["counts"] == {
        "document": 2,
        "source_block": 1,
        "relation_candidate": 1,
    }
    assert all(status == "fresh" for status in check_summary["artifact_status"].values())


def test_rejects_malformed_jsonl_with_compact_diagnostic(tmp_path: Path) -> None:
    bad_jsonl = tmp_path / "bad.jsonl"
    bad_jsonl.write_text("{not json}\n", encoding="utf-8")

    result = run_cli(str(bad_jsonl))

    assert result.returncode == 1
    summary = parse_summary(result)
    assert summary["status"] == "fail"
    diagnostic = summary["diagnostics"][0]
    assert diagnostic["file"] == str(bad_jsonl)
    assert diagnostic["line"] == 1
    assert diagnostic["rule"] == "json_invalid"
    assert diagnostic["field"] == "record"


def test_expected_kind_rejects_mixed_record_file() -> None:
    run_cli("--write")

    result = run_cli("--kind", "document", "prd/parser/examples/relation_candidate_records.jsonl")

    assert result.returncode == 1
    summary = parse_summary(result)
    assert summary["status"] == "fail"
    diagnostic = summary["diagnostics"][0]
    assert diagnostic["record_kind"] == "relation_candidate"
    assert diagnostic["field"] == "record_kind"
    assert diagnostic["rule"] == "unexpected_record_kind"


def test_check_reports_stale_generated_artifact() -> None:
    run_cli("--write")
    schema_path = SCHEMA_DIR / "parser_record.schema.json"
    original = schema_path.read_text(encoding="utf-8")
    try:
        schema_path.write_text(original + "\n", encoding="utf-8")
        result = run_cli("--check")
    finally:
        schema_path.write_text(original, encoding="utf-8")

    assert result.returncode == 1
    summary = parse_summary(result)
    assert summary["artifact_status"]["prd/parser/schemas/parser_record.schema.json"] == "stale"
    assert any(diagnostic["rule"] == "artifact_stale" for diagnostic in summary["diagnostics"])


def test_check_reports_missing_examples_or_schemas() -> None:
    run_cli("--write")
    example_path = EXAMPLE_DIR / "source_block_records.jsonl"
    backup_path = example_path.with_suffix(".jsonl.bak")
    if backup_path.exists():
        backup_path.unlink()
    shutil.move(example_path, backup_path)
    try:
        result = run_cli("--check")
    finally:
        shutil.move(backup_path, example_path)

    assert result.returncode == 1
    summary = parse_summary(result)
    assert summary["artifact_status"]["prd/parser/examples/source_block_records.jsonl"] == "missing"
    rules = {diagnostic["rule"] for diagnostic in summary["diagnostics"]}
    assert {"artifact_missing", "file_missing"}.issubset(rules)
