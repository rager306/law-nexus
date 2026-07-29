"""Source inventory event factories for the local job ledger."""

from __future__ import annotations

from dataclasses import dataclass

from law_nexus.adapters.observability.job_ledger import JobLedgerRecord, build_job_ledger_record

SOURCE_INVENTORY_COMPONENT = "source-inventory-ledger"


@dataclass(frozen=True)
class SourceInventoryLedgerContext:
    """Stable identifiers and refs shared by one source inventory job."""

    trace_id: str
    correlation_id: str
    job_id: str
    source_ref: str
    artifact_ref: str
    input_fingerprint: str
    component: str = SOURCE_INVENTORY_COMPONENT


def build_source_inventory_job_queued(
    context: SourceInventoryLedgerContext,
    *,
    ts: str,
    reason_code: str = "manual_check_requested",
) -> JobLedgerRecord:
    """Build the queue event for a source inventory job."""
    return build_job_ledger_record(
        ts=ts,
        event_name="source_inventory_job_queued",
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


def build_source_inventory_scan_started(
    context: SourceInventoryLedgerContext,
    *,
    ts: str,
) -> JobLedgerRecord:
    """Build the running event for a source inventory scan."""
    return build_job_ledger_record(
        ts=ts,
        event_name="source_inventory_scan_started",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="scan",
        status_before="queued",
        status_after="running",
        reason_code="job_started",
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
    )


def build_source_inventory_built(
    context: SourceInventoryLedgerContext,
    *,
    ts: str,
    output_fingerprint: str,
    produced_artifacts: tuple[str, ...],
    reason_code: str = "inventory_built",
) -> JobLedgerRecord:
    """Build the in-progress event for a produced inventory payload."""
    return build_job_ledger_record(
        ts=ts,
        event_name="source_inventory_built",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="build",
        status_before="running",
        status_after="running",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
        output_fingerprint=output_fingerprint,
        produced_artifacts=produced_artifacts,
    )


def build_source_inventory_artifact_written(
    context: SourceInventoryLedgerContext,
    *,
    ts: str,
    output_fingerprint: str,
    produced_artifacts: tuple[str, ...],
    reason_code: str = "artifact_written",
) -> JobLedgerRecord:
    """Build the succeeded event for a written or fresh inventory artifact."""
    return build_job_ledger_record(
        ts=ts,
        event_name="source_inventory_artifact_written",
        trace_id=context.trace_id,
        correlation_id=context.correlation_id,
        job_id=context.job_id,
        component=context.component,
        phase="write",
        status_before="running",
        status_after="succeeded",
        reason_code=reason_code,
        source_ref=context.source_ref,
        artifact_ref=context.artifact_ref,
        input_fingerprint=context.input_fingerprint,
        output_fingerprint=output_fingerprint,
        produced_artifacts=produced_artifacts,
    )


def build_source_inventory_job_failed(
    context: SourceInventoryLedgerContext,
    *,
    ts: str,
    reason_code: str,
    error_code: str,
    error_class: str,
    error_message: str,
    recovery_instruction: str,
    retryable: bool = False,
) -> JobLedgerRecord:
    """Build a bounded failure event for a source inventory job."""
    return build_job_ledger_record(
        ts=ts,
        event_name="source_inventory_job_failed",
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
