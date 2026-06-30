from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_PATH = Path("scripts/inventory-parser-fixtures.py")


class FakeInventoryUseCase:
    def __init__(self, manifest: dict[str, object]) -> None:
        self._manifest = manifest

    def build_parser_fixture_inventory(self, root: Path) -> dict[str, object]:
        assert root == Path.cwd()
        return self._manifest


def _load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("inventory_parser_fixtures", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _patch_script(
    monkeypatch: Any,
    module: ModuleType,
    *,
    manifest: dict[str, object] | None = None,
    errors: list[str] | None = None,
) -> dict[str, object]:
    selected_manifest = manifest or {"status": "pass", "fixture_count": 1}
    selected_errors = errors or []
    monkeypatch.setattr(
        module,
        "make_parser_inventory_use_case",
        lambda: FakeInventoryUseCase(selected_manifest),
    )
    monkeypatch.setattr(module, "check_outputs", lambda _root, _manifest: selected_errors)
    monkeypatch.setattr(module, "write_outputs", lambda _root, _manifest: None)
    monkeypatch.setattr(module, "observability_summary", lambda payload: payload)
    return selected_manifest


def test_inventory_cli_without_ledger_keeps_stdout_behavior(monkeypatch: Any, capsys: Any) -> None:
    module = _load_script_module()
    manifest = _patch_script(monkeypatch, module)

    result = module.main(["--check"])
    captured = capsys.readouterr()

    assert result == 0
    assert json.loads(captured.out) == manifest
    assert captured.err == ""


def test_inventory_cli_ledger_flag_appends_success_events(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    module = _load_script_module()
    _patch_script(monkeypatch, module)
    ledger_path = tmp_path / "source-inventory.jsonl"

    result = module.main(["--check", "--ledger-jsonl", str(ledger_path)])
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]

    assert result == 0
    assert captured.err == ""
    assert [line["event_name"] for line in lines] == [
        "source_inventory_job_queued",
        "source_inventory_scan_started",
        "source_inventory_built",
        "source_inventory_artifact_written",
    ]
    assert lines[-1]["status_after"] == "succeeded"
    assert lines[-1]["reason_code"] == "artifact_fresh"
    assert all(line["job_type"] == "source_inventory" for line in lines)


def test_inventory_cli_ledger_flag_appends_failed_check_event(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    module = _load_script_module()
    _patch_script(monkeypatch, module, errors=["artifact stale"])
    ledger_path = tmp_path / "source-inventory.jsonl"

    result = module.main(["--check", "--ledger-jsonl", str(ledger_path)])
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]

    assert result == 1
    assert "ERROR: artifact stale" in captured.err
    assert [line["event_name"] for line in lines] == [
        "source_inventory_job_queued",
        "source_inventory_scan_started",
        "source_inventory_job_failed",
    ]
    assert lines[-1]["status_after"] == "failed"
    assert lines[-1]["reason_code"] == "validation_failed"
    assert lines[-1]["error_code"] == "source_inventory_check_failed"
