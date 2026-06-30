"""Bounded local job ledger primitives.

The ledger is operational/debug evidence only. It does not prove legal
correctness, parser completeness, retrieval quality, generated-Cypher
correctness, or FalkorDB production readiness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

SCHEMA_VERSION = "law-nexus-job-ledger/v1"
DEFAULT_PROOF_LEVEL = "bounded"
DEFAULT_LIFECYCLE_TAG = "bounded"
DEFAULT_NON_CLAIM = "job ledger events are operational/debug evidence only"

SOURCE_INVENTORY_EVENTS = frozenset(
    {
        "source_inventory_job_queued",
        "source_inventory_scan_started",
        "source_fixture_seen",
        "source_fixture_classified",
        "source_inventory_built",
        "source_inventory_artifact_written",
        "source_inventory_job_failed",
    }
)

PARSER_GOLDEN_EVENTS = frozenset(
    {
        "parser_golden_job_queued",
        "parser_golden_cases_built",
        "parser_golden_evaluation_started",
        "parser_golden_case_evaluated",
        "parser_golden_diagnostics_written",
        "parser_golden_regression_detected",
        "parser_golden_job_failed",
    }
)

EVENT_NAMES = SOURCE_INVENTORY_EVENTS | PARSER_GOLDEN_EVENTS

STATUS_VALUES = frozenset({"queued", "running", "succeeded", "failed", "blocked", "skipped"})

REQUEST_REASON_CODES = frozenset(
    {
        "manual_check_requested",
        "scheduled_check_requested",
        "source_tree_scan_requested",
        "source_inventory_changed",
        "parser_artifact_changed",
    }
)
FRESHNESS_REASON_CODES = frozenset(
    {"source_hash_changed", "source_hash_unchanged", "artifact_fresh", "artifact_stale"}
)
SCOPE_REASON_CODES = frozenset(
    {"fixture_in_scope", "fixture_out_of_scope", "classification_unknown"}
)
EXECUTION_REASON_CODES = frozenset(
    {"job_started", "cases_built", "cases_reused", "inventory_built", "inventory_reused"}
)
RESULT_REASON_CODES = frozenset(
    {
        "case_passed",
        "case_failed",
        "case_skipped",
        "case_blocked",
        "diagnostics_written",
        "no_diagnostics",
    }
)
FAILURE_REASON_CODES = frozenset(
    {
        "input_invalid",
        "source_missing",
        "artifact_missing",
        "json_invalid",
        "validation_failed",
        "write_conflict_detected",
    }
)
REGRESSION_REASON_CODES = frozenset(
    {"diagnostic_error", "missing_evidence", "unexpected_relation", "artifact_invalid"}
)
RECOVERY_REASON_CODES = frozenset(
    {"retry_scheduled", "retry_exhausted", "blocked_waiting_for_artifact", "blocked_waiting_for_user"}
)

REASON_CODES = frozenset().union(
    REQUEST_REASON_CODES,
    FRESHNESS_REASON_CODES,
    SCOPE_REASON_CODES,
    EXECUTION_REASON_CODES,
    RESULT_REASON_CODES,
    FAILURE_REASON_CODES,
    REGRESSION_REASON_CODES,
    RECOVERY_REASON_CODES,
)

JOB_TYPES_BY_EVENT_PREFIX = {
    "source_inventory_": "source_inventory",
    "source_fixture_": "source_inventory",
    "parser_golden_": "parser_golden",
}


class JobLedgerValidationError(ValueError):
    """Raised when a job ledger record violates the bounded contract."""


@dataclass(frozen=True)
class JobLedgerRecord:
    """A single local job ledger event record.

    The shape mirrors the M083 contract. Optional future fields should live
    inside ``safe_details`` until a schema migration promotes them.
    """

    ts: str
    event_name: str
    trace_id: str
    correlation_id: str
    job_id: str
    component: str
    phase: str
    status_after: str
    reason_code: str
    source_ref: str
    artifact_ref: str
    input_fingerprint: str
    job_type: str | None = None
    parent_job_id: str | None = None
    status_before: str | None = None
    attempt: int = 0
    retryable: bool = False
    output_fingerprint: str | None = None
    produced_artifacts: tuple[str, ...] = ()
    proof_level: str = DEFAULT_PROOF_LEVEL
    lifecycle_tag: str = DEFAULT_LIFECYCLE_TAG
    non_claims: tuple[str, ...] = (DEFAULT_NON_CLAIM,)
    redaction_applied: bool = True
    safe_details: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_class: str | None = None
    error_message: str | None = None
    recovery_instruction: str | None = None

    schema_version: ClassVar[str] = SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_job_ledger_record(self)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping with the contract field names."""
        return {
            "schema_version": self.schema_version,
            "ts": self.ts,
            "event_name": self.event_name,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "job_id": self.job_id,
            "parent_job_id": self.parent_job_id,
            "job_type": self.effective_job_type,
            "component": self.component,
            "phase": self.phase,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "reason_code": self.reason_code,
            "attempt": self.attempt,
            "retryable": self.retryable,
            "source_ref": self.source_ref,
            "artifact_ref": self.artifact_ref,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "produced_artifacts": list(self.produced_artifacts),
            "proof_level": self.proof_level,
            "lifecycle_tag": self.lifecycle_tag,
            "non_claims": list(self.non_claims),
            "redaction_applied": self.redaction_applied,
            "safe_details": self.safe_details,
            "error_code": self.error_code,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "recovery_instruction": self.recovery_instruction,
        }

    @property
    def effective_job_type(self) -> str:
        """Return explicit or inferred job type for this event."""
        if self.job_type is not None:
            return self.job_type
        return infer_job_type_from_event(self.event_name)


def build_job_ledger_record(
    *,
    ts: str,
    event_name: str,
    trace_id: str,
    correlation_id: str,
    job_id: str,
    component: str,
    phase: str,
    status_after: str,
    reason_code: str,
    source_ref: str,
    artifact_ref: str,
    input_fingerprint: str,
    job_type: str | None = None,
    parent_job_id: str | None = None,
    status_before: str | None = None,
    attempt: int = 0,
    retryable: bool = False,
    output_fingerprint: str | None = None,
    produced_artifacts: tuple[str, ...] = (),
    proof_level: str = DEFAULT_PROOF_LEVEL,
    lifecycle_tag: str = DEFAULT_LIFECYCLE_TAG,
    non_claims: tuple[str, ...] = (DEFAULT_NON_CLAIM,),
    redaction_applied: bool = True,
    safe_details: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_class: str | None = None,
    error_message: str | None = None,
    recovery_instruction: str | None = None,
) -> JobLedgerRecord:
    """Build a validated local job ledger record."""
    return JobLedgerRecord(
        ts=ts,
        event_name=event_name,
        trace_id=trace_id,
        correlation_id=correlation_id,
        job_id=job_id,
        component=component,
        phase=phase,
        status_after=status_after,
        reason_code=reason_code,
        source_ref=source_ref,
        artifact_ref=artifact_ref,
        input_fingerprint=input_fingerprint,
        job_type=job_type,
        parent_job_id=parent_job_id,
        status_before=status_before,
        attempt=attempt,
        retryable=retryable,
        output_fingerprint=output_fingerprint,
        produced_artifacts=produced_artifacts,
        proof_level=proof_level,
        lifecycle_tag=lifecycle_tag,
        non_claims=non_claims,
        redaction_applied=redaction_applied,
        safe_details=safe_details or {},
        error_code=error_code,
        error_class=error_class,
        error_message=error_message,
        recovery_instruction=recovery_instruction,
    )


def infer_job_type_from_event(event_name: str) -> str:
    """Infer a job type from a validated event name."""
    for prefix, job_type in JOB_TYPES_BY_EVENT_PREFIX.items():
        if event_name.startswith(prefix):
            return job_type
    raise JobLedgerValidationError(f"cannot infer job_type for event {event_name!r}")


def validate_job_ledger_record(record: JobLedgerRecord) -> None:
    """Validate a ledger record against the bounded M083 vocabulary."""
    if record.event_name not in EVENT_NAMES:
        raise JobLedgerValidationError(f"unknown event_name: {record.event_name}")
    if record.status_after not in STATUS_VALUES:
        raise JobLedgerValidationError(f"unknown status_after: {record.status_after}")
    if record.status_before is not None and record.status_before not in STATUS_VALUES:
        raise JobLedgerValidationError(f"unknown status_before: {record.status_before}")
    if record.reason_code not in REASON_CODES:
        raise JobLedgerValidationError(f"unknown reason_code: {record.reason_code}")
    if record.attempt < 0:
        raise JobLedgerValidationError("attempt must be non-negative")
    if record.redaction_applied is not True:
        raise JobLedgerValidationError("redaction_applied must be true")
    if not record.non_claims:
        raise JobLedgerValidationError("non_claims must not be empty")
    if DEFAULT_NON_CLAIM not in record.non_claims:
        raise JobLedgerValidationError("default operational/debug non-claim is required")
    if not record.input_fingerprint.startswith("sha256:"):
        raise JobLedgerValidationError("input_fingerprint must use sha256: prefix")
    if record.output_fingerprint is not None and not record.output_fingerprint.startswith("sha256:"):
        raise JobLedgerValidationError("output_fingerprint must use sha256: prefix")
    inferred_job_type = infer_job_type_from_event(record.event_name)
    if record.job_type is not None and record.job_type != inferred_job_type:
        raise JobLedgerValidationError("job_type does not match event family")
