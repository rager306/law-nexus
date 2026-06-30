from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from law_nexus.adapters.observability.job_ledger import (
    DEFAULT_NON_CLAIM,
    EVENT_NAMES,
    REASON_CODES,
    SCHEMA_VERSION,
    STATUS_VALUES,
    JobLedgerValidationError,
    append_job_ledger_record,
    build_job_ledger_record,
    serialize_job_ledger_record,
)


def _valid_record_kwargs() -> dict[str, Any]:
    return {
        "ts": "2026-06-30T00:00:00Z",
        "event_name": "source_inventory_job_queued",
        "trace_id": "trace-source-inventory-1",
        "correlation_id": "corr-source-inventory-1",
        "job_id": "job-source-inventory-1",
        "component": "source-inventory-ledger",
        "phase": "queue",
        "status_after": "queued",
        "reason_code": "manual_check_requested",
        "source_ref": "law-source/consultant/sample.xml",
        "artifact_ref": "prd/parser/source_fixture_inventory.json",
        "input_fingerprint": "sha256:" + "1" * 64,
    }


def test_vocabulary_includes_m083_event_families() -> None:
    assert "source_inventory_job_queued" in EVENT_NAMES
    assert "source_inventory_job_failed" in EVENT_NAMES
    assert "parser_golden_job_queued" in EVENT_NAMES
    assert "parser_golden_regression_detected" in EVENT_NAMES
    assert "queued" in STATUS_VALUES
    assert "succeeded" in STATUS_VALUES
    assert "manual_check_requested" in REASON_CODES
    assert "source_inventory_changed" in REASON_CODES
    assert "source_seen" in REASON_CODES
    assert "artifact_written" in REASON_CODES
    assert "diagnostic_error" in REASON_CODES


def test_build_source_inventory_job_ledger_record_has_required_contract_fields() -> None:
    record = build_job_ledger_record(**_valid_record_kwargs())

    payload = record.to_dict()

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["job_type"] == "source_inventory"
    assert payload["trace_id"] == "trace-source-inventory-1"
    assert payload["correlation_id"] == "corr-source-inventory-1"
    assert payload["job_id"] == "job-source-inventory-1"
    assert payload["reason_code"] == "manual_check_requested"
    assert payload["input_fingerprint"].startswith("sha256:")
    assert payload["redaction_applied"] is True
    assert DEFAULT_NON_CLAIM in payload["non_claims"]


def test_build_parser_golden_record_infers_second_event_family_job_type() -> None:
    kwargs = _valid_record_kwargs()
    kwargs.update(
        {
            "event_name": "parser_golden_job_queued",
            "job_id": "job-parser-golden-1",
            "component": "parser-golden-ledger",
            "reason_code": "source_inventory_changed",
        }
    )

    record = build_job_ledger_record(**kwargs)

    assert record.to_dict()["job_type"] == "parser_golden"


def test_running_observation_event_can_remain_running() -> None:
    kwargs = _valid_record_kwargs()
    kwargs.update(
        {
            "event_name": "source_fixture_seen",
            "phase": "scan",
            "status_before": "running",
            "status_after": "running",
            "reason_code": "source_seen",
        }
    )

    record = build_job_ledger_record(**kwargs)

    assert record.status_before == "running"
    assert record.status_after == "running"


def test_reason_code_must_match_event_family() -> None:
    kwargs = _valid_record_kwargs()
    kwargs.update(
        {
            "event_name": "source_inventory_scan_started",
            "status_before": "queued",
            "status_after": "running",
            "reason_code": "artifact_fresh",
        }
    )

    with pytest.raises(JobLedgerValidationError, match="is not valid for event"):
        build_job_ledger_record(**kwargs)


def test_invalid_status_transition_fails() -> None:
    kwargs = _valid_record_kwargs()
    kwargs.update({"status_before": "queued", "status_after": "succeeded"})

    with pytest.raises(JobLedgerValidationError, match="invalid status transition"):
        build_job_ledger_record(**kwargs)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("event_name", "unknown_event", "unknown event_name"),
        ("status_after", "done", "unknown status_after"),
        ("status_before", "done", "unknown status_before"),
        ("reason_code", "because", "unknown reason_code"),
        ("attempt", -1, "attempt must be non-negative"),
        ("redaction_applied", False, "redaction_applied must be true"),
        ("non_claims", (), "non_claims must not be empty"),
        ("input_fingerprint", "md5:abc", "input_fingerprint must use sha256"),
        ("output_fingerprint", "md5:abc", "output_fingerprint must use sha256"),
        ("job_type", "parser_golden", "job_type does not match event family"),
        ("source_ref", "/tmp/source.xml", "source_ref must be repository-relative"),
        ("artifact_ref", "../artifact.json", "artifact_ref must not contain parent traversal"),
        ("artifact_ref", ".gsd/exec/run.stdout", "artifact_ref must not point at .gsd/exec"),
    ],
)
def test_invalid_job_ledger_record_fails_fast(
    field: str,
    value: object,
    expected_error: str,
) -> None:
    kwargs = _valid_record_kwargs()
    kwargs[field] = value

    with pytest.raises(JobLedgerValidationError, match=expected_error):
        build_job_ledger_record(**kwargs)


def test_default_operational_non_claim_is_required() -> None:
    kwargs = _valid_record_kwargs()
    kwargs["non_claims"] = ("custom non-claim",)

    with pytest.raises(JobLedgerValidationError, match="default operational/debug non-claim"):
        build_job_ledger_record(**kwargs)


@pytest.mark.parametrize(
    "safe_details",
    [
        {"secret": "value"},
        {"nested": {"provider_payload": {}}},
        {"note": "OPENAI_API_KEY=example"},
        {"note": object()},
    ],
)
def test_unsafe_safe_details_fail(safe_details: dict[str, object]) -> None:
    kwargs = _valid_record_kwargs()
    kwargs["safe_details"] = safe_details

    with pytest.raises(JobLedgerValidationError, match="unsafe|JSON-safe"):
        build_job_ledger_record(**kwargs)


def test_jsonl_serialization_is_deterministic_and_newline_safe() -> None:
    record = build_job_ledger_record(
        **_valid_record_kwargs(),
        safe_details={"message": "line one\nline two", "count": 2},
    )

    line = serialize_job_ledger_record(record)
    parsed = json.loads(line)

    assert line.endswith("\n")
    assert line.count("\n") == 1
    assert list(parsed) == sorted(parsed)
    assert parsed["safe_details"] == {"count": 2, "message": "line one\nline two"}


def test_append_job_ledger_record_writes_one_jsonl_line_per_record(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger" / "jobs.jsonl"
    first = build_job_ledger_record(**_valid_record_kwargs())
    second_kwargs = _valid_record_kwargs()
    second_kwargs.update(
        {
            "job_id": "job-source-inventory-2",
            "trace_id": "trace-source-inventory-2",
            "correlation_id": "corr-source-inventory-2",
        }
    )
    second = build_job_ledger_record(**second_kwargs)

    append_job_ledger_record(ledger_path, first)
    append_job_ledger_record(ledger_path, second)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["job_id"] == "job-source-inventory-1"
    assert json.loads(lines[1])["job_id"] == "job-source-inventory-2"
