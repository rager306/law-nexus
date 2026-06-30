from __future__ import annotations

import pytest

from law_nexus.adapters.observability.job_ledger import (
    DEFAULT_NON_CLAIM,
    JobLedgerValidationError,
)
from law_nexus.adapters.observability.parser_golden_ledger import (
    ParserGoldenLedgerContext,
    build_parser_golden_case_evaluated,
    build_parser_golden_evaluation_started,
    build_parser_golden_job_failed,
    build_parser_golden_job_queued,
    build_parser_golden_regression_detected,
)


def _context() -> ParserGoldenLedgerContext:
    return ParserGoldenLedgerContext(
        trace_id="trace-parser-golden-1",
        correlation_id="corr-parser-golden-1",
        job_id="job-parser-golden-1",
        source_ref="prd/parser/parser_golden_cases.json",
        artifact_ref="prd/parser/parser_golden_evaluation.json",
        input_fingerprint="sha256:" + "4" * 64,
    )


def test_parser_golden_factory_builds_queue_and_running_records() -> None:
    queued = build_parser_golden_job_queued(_context(), ts="2026-06-30T00:00:00Z")
    running = build_parser_golden_evaluation_started(_context(), ts="2026-06-30T00:00:01Z")

    queued_payload = queued.to_dict()

    assert queued_payload["event_name"] == "parser_golden_job_queued"
    assert queued_payload["job_type"] == "parser_golden"
    assert queued_payload["reason_code"] == "source_inventory_changed"
    assert running.status_before == "queued"
    assert running.status_after == "running"
    assert DEFAULT_NON_CLAIM in running.non_claims


def test_parser_golden_factory_builds_case_and_regression_records() -> None:
    case = build_parser_golden_case_evaluated(
        _context(),
        ts="2026-06-30T00:00:02Z",
        reason_code="case_failed",
        safe_details={"case_id": "sample-case", "diagnostic_count": 1},
    )
    regression = build_parser_golden_regression_detected(
        _context(),
        ts="2026-06-30T00:00:03Z",
        reason_code="diagnostic_error",
        safe_details={"diagnostic_code": "json_invalid"},
    )

    assert case.event_name == "parser_golden_case_evaluated"
    assert case.status_before == "running"
    assert case.status_after == "running"
    assert case.safe_details == {"case_id": "sample-case", "diagnostic_count": 1}
    assert regression.event_name == "parser_golden_regression_detected"
    assert regression.reason_code == "diagnostic_error"


def test_parser_golden_factory_builds_failure_record() -> None:
    failed = build_parser_golden_job_failed(
        _context(),
        ts="2026-06-30T00:00:04Z",
        reason_code="json_invalid",
        error_code="parser_golden_json_invalid",
        error_class="GoldenCaseError",
        error_message="parser golden case JSON was invalid",
        recovery_instruction="Inspect golden-case JSON and rerun evaluation.",
    )

    assert failed.event_name == "parser_golden_job_failed"
    assert failed.status_after == "failed"
    assert failed.error_code == "parser_golden_json_invalid"


def test_parser_golden_factory_rejects_source_inventory_reason_for_case_event() -> None:
    with pytest.raises(JobLedgerValidationError, match="is not valid for event"):
        build_parser_golden_case_evaluated(
            _context(),
            ts="2026-06-30T00:00:02Z",
            reason_code="source_inventory_changed",
        )


def test_parser_golden_factory_rejects_unsafe_details() -> None:
    with pytest.raises(JobLedgerValidationError, match="unsafe safe_details key"):
        build_parser_golden_regression_detected(
            _context(),
            ts="2026-06-30T00:00:03Z",
            reason_code="diagnostic_error",
            safe_details={"raw_legal_text": "do not store"},
        )
