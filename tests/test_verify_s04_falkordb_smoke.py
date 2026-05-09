"""Tests for the S04 FalkorDB capability smoke verifier."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from hypothesis import given, settings
from hypothesis import strategies as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = PROJECT_ROOT / "scripts/verify-s04-falkordb-smoke.py"


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s04_falkordb_smoke", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VERIFIER = _load_verifier()
VerificationMode = VERIFIER.VerificationMode


def _valid_finding(capability_id: str, status: str = "smoke-needed") -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "status": status,
        "evidence_class": "smoke-needed",
        "phase": "schema-seed",
        "timestamp": "2026-05-09T00:00:00Z",
        "owner": "S04",
        "resolution_path": f"Run the bounded runtime probe for `{capability_id}` in T03/T04.",
        "verification_criteria": f"Verifier records a terminal runtime status for `{capability_id}` with raw-log evidence.",
        "raw_log_reference": ".gsd/milestones/M001/slices/S04/logs/schema-seed.log",
        "diagnostics": {
            "root_cause": "not-run",
            "detail": "Runtime probes have not executed in schema-only mode.",
        },
    }


def _valid_json() -> dict[str, Any]:
    capability_ids = list(cast("tuple[str, ...]", VERIFIER.REQUIRED_CAPABILITY_IDS))
    return {
        "schema_version": VERIFIER.SCHEMA_VERSION,
        "generated_at": "2026-05-09T00:00:00Z",
        "phase": "schema-only",
        "capabilities": capability_ids,
        "findings": [_valid_finding(capability_id) for capability_id in capability_ids],
        "command_summary": {
            "schema_only_verifier": "not-run",
            "runtime_smoke": "not-run",
        },
        "image_metadata": {
            "docker_daemon": "not-run",
            "falkordb_image": "not-run",
        },
        "package_metadata": {
            "falkordb": "not-run",
            "falkordblite": "not-run",
            "sentence_transformers": "not-run",
        },
        "cleanup_status": "not-run; no runtime resources created by schema seed",
        "log_artifact_path": ".gsd/milestones/M001/slices/S04/logs/schema-seed.log",
    }


def _valid_markdown() -> str:
    rows = "\n".join(
        f"| `{capability_id}` | smoke-needed | smoke-needed | S04 | Run bounded runtime probe. | Terminal status with raw-log evidence. | `.gsd/milestones/M001/slices/S04/logs/schema-seed.log` |"
        for capability_id in cast("tuple[str, ...]", VERIFIER.REQUIRED_CAPABILITY_IDS)
    )
    return f"""# S04 FalkorDB Capability Smoke

## Purpose

Seed the S04 capability smoke contract without claiming runtime proof. This is within the M001 architecture-only boundary and exists to prevent omitted findings from disappearing.

## Capability Findings

| Capability ID | Status | Evidence Class | Owner | Resolution Path | Verification Criteria | Raw Log |
|---|---|---|---|---|---|---|
{rows}

## Runtime Boundary

Runtime probes have not executed. `smoke-needed` means S04 still owns bounded verification.

## Command Summary

No runtime commands have run in the schema seed.

## Environment Metadata

Environment metadata is pending runtime smoke execution.

## Cleanup Status

No Docker containers, temp venvs, or model downloads were created by this schema seed.

## Failure Diagnostics

Each finding carries a placeholder diagnostic explaining that the runtime probe has not run yet.

## Verification

Run `uv run python scripts/verify-s04-falkordb-smoke.py --require-schema-only` for this scaffold, then `--require-runtime-results` after runtime probes.
"""


def _write_artifacts(tmp_path: Path, payload: dict[str, Any] | None = None, markdown: str | None = None) -> tuple[Path, Path]:
    markdown_path = tmp_path / "S04-FALKORDB-CAPABILITY-SMOKE.md"
    json_path = tmp_path / "S04-FALKORDB-CAPABILITY-SMOKE.json"
    markdown_path.write_text(_valid_markdown() if markdown is None else markdown, encoding="utf-8")
    json_path.write_text(json.dumps(_valid_json() if payload is None else payload), encoding="utf-8")
    return markdown_path, json_path


def _validate(payload: dict[str, Any], tmp_path: Path) -> list[str]:
    markdown_path, json_path = _write_artifacts(tmp_path, payload)
    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.SCHEMA_ONLY)
    return cast("list[str]", failures)


def test_valid_schema_only_fixture_passes(tmp_path: Path) -> None:
    markdown_path, json_path = _write_artifacts(tmp_path)

    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.SCHEMA_ONLY)

    assert failures == []


def test_cli_accepts_valid_schema_only_fixture(tmp_path: Path) -> None:
    markdown_path, json_path = _write_artifacts(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_PATH),
            "--require-schema-only",
            "--markdown",
            str(markdown_path),
            "--json",
            str(json_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "S04 FalkorDB capability smoke verification passed." in result.stdout


def test_rejects_missing_owner(tmp_path: Path) -> None:
    payload = _valid_json()
    cast("dict[str, Any]", payload["findings"][0])["owner"] = ""

    failures = _validate(payload, tmp_path)

    assert any("owner must be a non-empty string" in failure for failure in failures)


@given(status=st.text(min_size=1).filter(lambda value: value not in VERIFIER.ALLOWED_RUNTIME_STATUSES))
@settings(max_examples=25)
def test_rejects_unknown_status(status: str) -> None:
    payload = _valid_json()
    cast("dict[str, Any]", payload["findings"][0])["status"] = status

    with tempfile.TemporaryDirectory() as directory:
        failures = _validate(payload, Path(directory))

    assert any("invalid status" in failure for failure in failures)


@given(
    evidence_class=st.text(min_size=1).filter(
        lambda value: value not in VERIFIER.ALLOWED_EVIDENCE_CLASSES
    )
)
@settings(max_examples=25)
def test_rejects_unknown_evidence_class(evidence_class: str) -> None:
    payload = _valid_json()
    cast("dict[str, Any]", payload["findings"][0])["evidence_class"] = evidence_class

    with tempfile.TemporaryDirectory() as directory:
        failures = _validate(payload, Path(directory))

    assert any("invalid evidence_class" in failure for failure in failures)


def test_rejects_missing_capability_id(tmp_path: Path) -> None:
    payload = _valid_json()
    payload["capabilities"] = [
        capability_id
        for capability_id in cast("list[str]", payload["capabilities"])
        if capability_id != "embedding-cpu-tiny"
    ]
    payload["findings"] = [
        finding
        for finding in cast("list[dict[str, Any]]", payload["findings"])
        if finding["capability_id"] != "embedding-cpu-tiny"
    ]
    markdown = _valid_markdown().replace("`embedding-cpu-tiny`", "`omitted-embedding-cpu-tiny`")
    markdown_path, json_path = _write_artifacts(tmp_path, payload, markdown)

    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.SCHEMA_ONLY)

    assert any("markdown missing capability ID: embedding-cpu-tiny" in failure for failure in failures)
    assert any(
        "JSON capabilities missing required capability ID: embedding-cpu-tiny" in failure
        for failure in failures
    )
    assert any(
        "JSON findings missing required capability ID: embedding-cpu-tiny" in failure
        for failure in failures
    )


def test_rejects_invalid_json(tmp_path: Path) -> None:
    markdown_path = tmp_path / "S04-FALKORDB-CAPABILITY-SMOKE.md"
    json_path = tmp_path / "S04-FALKORDB-CAPABILITY-SMOKE.json"
    markdown_path.write_text(_valid_markdown(), encoding="utf-8")
    json_path.write_text("{invalid", encoding="utf-8")

    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.SCHEMA_ONLY)

    assert any("invalid JSON" in failure for failure in failures)


def test_rejects_missing_findings_top_level_key(tmp_path: Path) -> None:
    payload = _valid_json()
    del payload["findings"]

    failures = _validate(payload, tmp_path)

    assert any("JSON missing top-level field: findings" in failure for failure in failures)
    assert any("JSON findings must be a list" in failure for failure in failures)


def test_rejects_blank_resolution_and_verification_fields(tmp_path: Path) -> None:
    payload = _valid_json()
    first_finding = cast("dict[str, Any]", payload["findings"][0])
    first_finding["resolution_path"] = ""
    first_finding["verification_criteria"] = ""

    failures = _validate(payload, tmp_path)

    assert any("resolution_path must be a non-empty string" in failure for failure in failures)
    assert any("verification_criteria must be a non-empty string" in failure for failure in failures)


def test_missing_markdown_file_reports_path(tmp_path: Path) -> None:
    _markdown_path, json_path = _write_artifacts(tmp_path)
    missing_markdown = tmp_path / "missing.md"

    failures = VERIFIER.validate_artifacts(missing_markdown, json_path, VerificationMode.SCHEMA_ONLY)

    assert any(f"markdown artifact missing: {missing_markdown}" in failure for failure in failures)


def test_missing_json_file_reports_path(tmp_path: Path) -> None:
    markdown_path, _json_path = _write_artifacts(tmp_path)
    missing_json = tmp_path / "missing.json"

    failures = VERIFIER.validate_artifacts(markdown_path, missing_json, VerificationMode.SCHEMA_ONLY)

    assert any(f"JSON artifact missing: {missing_json}" in failure for failure in failures)


def test_runtime_mode_rejects_schema_only_statuses(tmp_path: Path) -> None:
    markdown_path, json_path = _write_artifacts(tmp_path)

    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.RUNTIME_RESULTS)

    assert any("non-terminal runtime status" in failure for failure in failures)
    assert any("JSON phase must be 'runtime-results'" in failure for failure in failures)


def test_runtime_mode_accepts_terminal_statuses_with_specific_diagnostics(tmp_path: Path) -> None:
    payload = _valid_json()
    payload["phase"] = "runtime-results"
    terminal_findings = deepcopy(cast("list[dict[str, Any]]", payload["findings"]))
    for finding in terminal_findings:
        finding["status"] = "blocked-environment"
        finding["diagnostics"] = {
            "root_cause": "docker image unavailable in bounded smoke environment",
            "detail": "Runtime smoke recorded an explicit blocked condition and cleanup status.",
        }
    payload["findings"] = terminal_findings
    markdown_path, json_path = _write_artifacts(tmp_path, payload)

    failures = VERIFIER.validate_artifacts(markdown_path, json_path, VerificationMode.RUNTIME_RESULTS)

    assert failures == []
