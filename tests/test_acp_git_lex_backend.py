from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "scripts/acp_git_lex_backend.py"


def load_backend() -> ModuleType:
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("acp_git_lex_backend", BACKEND)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def base_wrapper_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": "m054.git_lex_diagnostic.v1",
        "operation_id": "m054-op-1",
        "operation_type": "list_json",
        "classification": "pass",
        "workspace_path": "/tmp/acp-shadow",
        "workspace_is_main_repo": False,
        "git_lex_binary": "/root/vendor-source/git-lex/target/debug/git-lex",
        "git_lex_source_commit": "eaa4b24d144a78a8b8e4969404d74cf22267df1f",
        "binary_sha256": "40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c",
        "command": [],
        "exit_code": 0,
        "stdout_digest": "class inventory",
        "stderr_digest": "",
        "expected_shapes": [],
        "expected_files": [],
        "observed_validated_count": None,
        "query_id": None,
        "result_count": 12,
        "raw_payload_touched": False,
        "main_lex_absent_before": True,
        "main_lex_absent_after": True,
        "main_squad_absent_before": True,
        "main_squad_absent_after": True,
        "main_raw_absent_before": True,
        "main_raw_absent_after": True,
        "cleanup_status": "not-needed",
        "authority": "non-authoritative-diagnostic",
        "duration_ms": 1,
    }
    record.update(overrides)
    return record


def test_normalize_wrapper_record_adds_acp_contract_fields() -> None:
    backend = load_backend()

    payload = backend.normalize_wrapper_record(
        base_wrapper_record(),
        source_record_id="SRC-001",
        source_record_type="decision",
        source_record_lifecycle="synthetic-fixture",
        created_at="2026-06-02T00:00:00Z",
    )

    assert payload["schema_version"] == "m055.acp_git_lex_backend_diagnostic.v1"
    assert payload["backend_level"] == "L1-shadow-diagnostic-projection"
    assert payload["backend_name"] == "git-lex"
    assert payload["source_record_id"] == "SRC-001"
    assert payload["source_record_type"] == "decision"
    assert payload["source_record_lifecycle"] == "synthetic-fixture"
    assert payload["operation"] == "class_inventory"
    assert payload["operation_class"] == "projection"
    assert payload["classification"] == "pass"
    assert payload["wrapper_classification"] == "pass"
    assert payload["authority"] == "non-authoritative-diagnostic"
    assert payload["can_validate_requirement"] is False
    assert payload["can_mutate_source_truth"] is False
    assert payload["wrapper_schema_version"] == "m054.git_lex_diagnostic.v1"
    assert payload["wrapper_operation_id"] == "m054-op-1"
    assert payload["result_count"] == 12
    assert payload["created_at"] == "2026-06-02T00:00:00Z"


def test_run_backend_operation_dispatches_to_m054_wrapper(monkeypatch: Any) -> None:
    backend = load_backend()
    called: dict[str, object] = {}

    def fake_operation_query(workspace: str, query_id: str, *, json_output: bool) -> dict[str, object]:
        called["workspace"] = workspace
        called["query_id"] = query_id
        called["json_output"] = json_output
        return base_wrapper_record(
            operation_type="query_json",
            query_id=query_id,
            result_count=0,
            stdout_digest="[]",
        )

    monkeypatch.setattr(backend.git_lex, "operation_query", fake_operation_query)

    payload = backend.run_backend_operation(
        "bounded_query_json",
        workspace="/tmp/acp-shadow",
        query_id="negative_empty",
        source_record_id="SRC-QUERY",
        source_record_type="diagnostic_record",
    )

    assert called == {
        "workspace": "/tmp/acp-shadow",
        "query_id": "negative_empty",
        "json_output": True,
    }
    assert payload["operation"] == "bounded_query_json"
    assert payload["operation_class"] == "projection"
    assert payload["query_id"] == "negative_empty"
    assert payload["source_record_id"] == "SRC-QUERY"
    assert payload["classification"] == "pass"


def test_denied_command_rejection_is_policy_record(monkeypatch: Any) -> None:
    backend = load_backend()

    def fake_reject_denied(command: str) -> dict[str, object]:
        return base_wrapper_record(
            operation_type="reject_denied",
            classification="rejected",
            command=["git-lex", command],
            exit_code=None,
            stderr_digest=f"command denied by M054 policy: {command}",
            stdout_digest="",
            workspace_path=None,
            result_count=None,
        )

    monkeypatch.setattr(backend.git_lex, "operation_reject_denied", fake_reject_denied)

    payload = backend.run_backend_operation("reject_denied", command="nuke")

    assert payload["operation"] == "reject_denied"
    assert payload["operation_class"] == "policy-rejection"
    assert payload["classification"] == "rejected"
    assert payload["error_class"] == "denied-surface"
    assert payload["can_mutate_source_truth"] is False
    assert "nuke" in payload["diagnostic_summary"]


def test_private_raw_fields_are_stripped_and_marked_adapter_fail() -> None:
    backend = load_backend()

    payload = backend.normalize_wrapper_record(
        base_wrapper_record(_stdout_raw='[{"secret":"raw"}]', _stderr_raw="raw stderr"),
        acp_operation="class_inventory",
    )

    assert payload["classification"] == "adapter-fail"
    assert payload["error_class"] == "unknown-adapter-error"
    assert "_stdout_raw" not in payload
    assert "_stderr_raw" not in payload
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "secret" not in serialized
    assert "raw stderr" not in serialized


def test_main_state_residue_overrides_pass_classification() -> None:
    backend = load_backend()

    payload = backend.normalize_wrapper_record(
        base_wrapper_record(main_lex_absent_after=False),
        acp_operation="class_inventory",
    )

    assert payload["classification"] == "adapter-fail"
    assert payload["error_class"] == "main-state-residue"
    assert payload["main_lex_absent_after"] is False


def test_validation_git_lex_fail_maps_to_diagnostic_fail() -> None:
    backend = load_backend()

    payload = backend.normalize_wrapper_record(
        base_wrapper_record(
            operation_type="validate_wrapped",
            classification="git-lex-fail",
            stderr_digest="SHACL violation: sh:in constraint",
            observed_validated_count=3,
            result_count=None,
        ),
        acp_operation="validation_diagnostic",
    )

    assert payload["classification"] == "diagnostic-fail"
    assert payload["error_class"] == "concrete-validation-violation"
    assert payload["operation_class"] == "validation-diagnostic"
    assert payload["can_validate_requirement"] is False


def test_cli_emits_acp_facing_json_for_denied_command() -> None:
    result = subprocess.run(
        [sys.executable, str(BACKEND), "reject-denied", "--command", "nuke"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "m055.acp_git_lex_backend_diagnostic.v1"
    assert payload["backend_level"] == "L1-shadow-diagnostic-projection"
    assert payload["operation"] == "reject_denied"
    assert payload["classification"] == "rejected"
    assert payload["authority"] == "non-authoritative-diagnostic"
    assert payload["can_validate_requirement"] is False
    assert "_stdout_raw" not in payload
    assert "_stderr_raw" not in payload
