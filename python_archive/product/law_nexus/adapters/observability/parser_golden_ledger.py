"""Parser golden-case event factories for the local job ledger."""

from __future__ import annotations

from dataclasses import dataclass

from law_nexus.adapters.observability.job_ledger import JobLedgerRecord, build_job_ledger_record

PARSER_GOLDEN_COMPONENT = "parser-golden-ledger"


@dataclass(frozen=True)
class ParserGoldenLedgerContext:
    """Stable identifiers and refs shared by one parser golden-case job."""

    trace_id: str
    correlation_id: str
    job_id: str
    source_ref: str
    artifact_ref: str
    input_fingerprint: str
    component: str = PARSER_GOLDEN_COMPONENT


def build_parser_golden_job_queued(
    context: ParserGoldenLedgerContext,
    *,
    ts: str,
    reason_code: str = "source_inventory_changed",
) -> JobLedgerRecord:
    """Build a queued parser golden-case job event."""
    return build_job_ledger_record(
        ts=ts,
        event_name="parser_golden_job_queued",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="queue",
        status_after="queued",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
    )


def build_parser_golden_evaluation_started(
    context: ParserGoldenLedgerContext,
    *,
    ts: str,
) -> JobLedgerRecord:
    """Build a running parser golden-case evaluation event."""
    return build_job_ledger_record(
        ts=ts,
        event_name="parser_golden_evaluation_started",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="evaluate",
        status_before="queued",
        status_after="running",
        reason_code="job_started",
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
    )


def build_parser_golden_case_evaluated(
    context: ParserGoldenLedgerContext,
    *,
    ts: str,
    reason_code: str,
    safe_details: dict[str, object] | None = None,
) -> JobLedgerRecord:
    """Build an in-progress parser golden-case result event."""
    return build_job_ledger_record(
        ts=ts,
        event_name="parser_golden_case_evaluated",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="evaluate_case",
        status_before="running",
        status_after="running",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
        safe_details=safe_details or {},
    )


def build_parser_golden_regression_detected(
    context: ParserGoldenLedgerContext,
    *,
    ts: str,
    reason_code: str,
    safe_details: dict[str, object] | None = None,
) -> JobLedgerRecord:
    """Build an in-progress parser golden-case regression event."""
    return build_job_ledger_record(
        ts=ts,
        event_name="parser_golden_regression_detected",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="regression",
        status_before="running",
        status_after="running",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
        safe_details=safe_details or {},
    )


def build_parser_golden_job_failed(
    context: ParserGoldenLedgerContext,
    *,
    ts: str,
    reason_code: str,
    error_code: str,
    error_class: str,
    error_message: str,
    recovery_instruction: str,
    retryable: bool = False,
) -> JobLedgerRecord:
    """Build a bounded parser golden-case job failure event."""
    return build_job_ledger_record(
        ts=ts,
        event_name="parser_golden_job_failed",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="fail",
        status_before="running",
        status_after="failed",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
        retryable=retryable,
        error_code=error_code,
        error_class=error_class,
        error_message=error_message,
        recovery_instruction=recovery_instruction,
    )
