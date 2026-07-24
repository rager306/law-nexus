"""TDD contracts for the repository preflight control-plane command."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.preflight import PREFLIGHT_SCHEMA_VERSION, run_preflight

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_report_schema_and_noop_profile_pass() -> None:
    report = run_preflight(ROOT)
    payload = report.to_dict()

    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert payload["root"] == str(ROOT)
    assert payload["checks"] == []
    assert payload["pass_count"] == 0
    assert payload["warn_count"] == 0
    assert payload["error_count"] == 0


def test_cli_preflight_command_emits_stable_json(capsys) -> None:
    code = main(["preflight", "--root", str(ROOT)])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert code == 0
    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert payload["checks"] == []
