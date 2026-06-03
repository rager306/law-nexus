from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts/git_lex_diagnostic_adapter.py"


def load_adapter() -> ModuleType:
    spec = importlib.util.spec_from_file_location("git_lex_diagnostic_adapter", ADAPTER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_adapter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ADAPTER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def assert_main_safety_fields(payload: dict[str, object]) -> None:
    assert payload["main_lex_absent_before"] is True
    assert payload["main_lex_absent_after"] is True
    assert payload["main_squad_absent_before"] is True
    assert payload["main_squad_absent_after"] is True
    assert payload["main_raw_absent_before"] is True
    assert payload["main_raw_absent_after"] is True
    assert payload["raw_payload_touched"] is False
    assert payload["authority"] == "non-authoritative-diagnostic"


def test_help_emits_complete_non_authoritative_record() -> None:
    result = run_adapter("help", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = parse_stdout(result)
    assert payload["schema_version"] == "m054.git_lex_diagnostic.v1"
    assert payload["operation_type"] == "help"
    assert payload["classification"] == "pass"
    assert payload["workspace_path"] is None
    assert payload["workspace_is_main_repo"] is False
    assert payload["git_lex_source_commit"] == "eaa4b24d144a78a8b8e4969404d74cf22267df1f"
    assert payload["binary_sha256"] == "40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c"
    assert "Git extensions for knowledge graphs" in str(payload["stdout_digest"])
    assert_main_safety_fields(payload)


def test_denied_command_is_rejected_without_exit_code() -> None:
    result = run_adapter("reject-denied", "--command", "nuke")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = parse_stdout(result)
    assert payload["operation_type"] == "reject_denied"
    assert payload["classification"] == "rejected"
    assert payload["exit_code"] is None
    assert "nuke" in payload["command"]
    assert "command denied" in str(payload["stderr_digest"])
    assert_main_safety_fields(payload)


def test_main_repo_workspace_is_blocked_with_json_record() -> None:
    result = run_adapter("sync", "--workspace", str(ROOT))

    assert result.returncode == 1
    payload = parse_stdout(result)
    assert payload["operation_type"] == "sync"
    assert payload["classification"] == "blocked"
    assert "workspace must not be the main repository" in str(payload["stderr_digest"])
    assert_main_safety_fields(payload)


def test_validate_wrapped_missing_expected_inputs_wrapper_fail(tmp_path: Path) -> None:
    adapter = load_adapter()

    payload = adapter.operation_validate_wrapped(
        str(tmp_path),
        expected_shapes=[".lex/ontology/squad/squad-shapes.ttl"],
        expected_files=["Squad/Task/Missing.md"],
        expected_count=1,
        negative=False,
    )

    assert payload["operation_type"] == "validate_wrapped"
    assert payload["classification"] == "wrapper-fail"
    assert payload["exit_code"] is None
    assert "missing_shapes" in payload["stderr_digest"]
    assert_main_safety_fields(payload)


def test_query_id_must_be_bounded(tmp_path: Path) -> None:
    adapter = load_adapter()

    payload = adapter.operation_query(str(tmp_path), "unbounded_user_query", json_output=True)

    assert payload["operation_type"] == "query_json"
    assert payload["classification"] == "rejected"
    assert payload["query_id"] == "unbounded_user_query"
    assert "query_id is not allowed" in payload["stderr_digest"]
    assert_main_safety_fields(payload)


def test_list_json_parses_private_raw_stdout_not_truncated_digest(
    tmp_path: Path, monkeypatch: object
) -> None:
    adapter = load_adapter()
    raw_classes = [{"class": f"Class{i}"} for i in range(40)]

    def fake_run_git_lex(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "schema_version": "m054.git_lex_diagnostic.v1",
            "operation_id": "test",
            "operation_type": "list_json",
            "classification": "pass",
            "workspace_path": str(tmp_path),
            "workspace_is_main_repo": False,
            "git_lex_binary": "fake",
            "git_lex_source_commit": adapter.PINNED_SOURCE_COMMIT,
            "binary_sha256": adapter.PINNED_BINARY_SHA256,
            "command": [],
            "exit_code": 0,
            "stdout_digest": "[{truncated invalid json",
            "stderr_digest": "",
            "expected_shapes": [],
            "expected_files": [],
            "observed_validated_count": None,
            "query_id": None,
            "result_count": None,
            "raw_payload_touched": False,
            "main_lex_absent_before": True,
            "main_lex_absent_after": True,
            "main_squad_absent_before": True,
            "main_squad_absent_after": True,
            "main_raw_absent_before": True,
            "main_raw_absent_after": True,
            "cleanup_status": "not-needed",
            "authority": "non-authoritative-diagnostic",
            "duration_ms": 0,
            "_stdout_raw": json.dumps(raw_classes),
            "_stderr_raw": "",
        }

    monkeypatch.setattr(adapter, "run_git_lex", fake_run_git_lex)

    payload = adapter.operation_list_json(str(tmp_path))

    assert payload["classification"] == "pass"
    assert payload["result_count"] == 40
    assert "_stdout_raw" not in payload
    assert "_stderr_raw" not in payload


def test_allowed_query_ids_are_explicit() -> None:
    adapter = load_adapter()

    assert set(adapter.QUERY_TEMPLATES) == {
        "graph_inventory",
        "frontmatter_fixture",
        "negative_empty",
        "history_reifies_ask",
    }
