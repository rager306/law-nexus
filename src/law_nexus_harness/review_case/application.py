"""Pure Review Case application use cases.

Depends only on domain/policy/ports. No filesystem, codecs, CLI, Governor,
GSD, or product-domain packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from law_nexus_harness.review_case.domain import (
    ActorClass,
    DerivedStatus,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ProofClass,
    RelationType,
    ReviewCaseValidationError,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    VerificationStatus,
)
from law_nexus_harness.review_case.policy import (
    apply_event,
    derive_finding_status,
    derive_packet_statuses,
    replay_events,
    validate_review_policy,
)
from law_nexus_harness.review_case.ports import (
    ContentHasher,
    EventLedger,
    ReviewCasePortError,
    ReviewPacketStore,
    ReviewSourceReader,
)

APP_REPORT_SCHEMA_VERSION = "review-case-application-report/v1"
_DEFAULT_NON_CLAIMS = (
    "Non-authoritative review projection",
    "Does not promote requirements, ADRs, roadmap, or lifecycle",
    "Does not create GSD milestones or product claims",
)


class ReviewCaseApplicationError(Exception):
    """Structured application failure without raw review bytes."""

    def __init__(
        self,
        *,
        code: str,
        operation: str,
        message: str,
        cause_code: str | None = None,
    ) -> None:
        if not code or not operation or not message:
            raise ValueError("ReviewCaseApplicationError requires code, operation, and message")
        self.code = code
        self.operation = operation
        self.message = message
        self.cause_code = cause_code
        detail = f"{operation}:{code}: {message}"
        if cause_code:
            detail = f"{detail} (cause={cause_code})"
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class RegisterReviewCaseCommand:
    packet_id: str
    source_path: str
    reviewed_revision: str
    received_at: str
    source_kind: SourceKind
    normalization_method: NormalizationMethod
    non_claims: tuple[str, ...]
    extractor_version: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterReviewCaseReport:
    schema_version: str
    authoritative: bool
    authority_required: bool
    packet_id: str
    source_path: str
    reviewed_revision: str
    content_sha256: str
    finding_count: int
    non_claims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidateReviewCasesReport:
    schema_version: str
    authoritative: bool
    authority_required: bool
    ok: bool
    packet_count: int
    finding_count: int
    open_count: int
    blocked_count: int
    partial_count: int
    closed_count: int
    stale_count: int
    non_claims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewCaseStatusReport:
    schema_version: str
    authoritative: bool
    authority_required: bool
    packets: tuple[
        tuple[
            str,
            str,
            str,
            str,
            tuple[tuple[str, str], ...],
        ],
        ...,
    ]
    open_blockers: tuple[tuple[str, str], ...]
    non_claims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecordDispositionCommand:
    packet_id: str
    finding_id: str
    disposition: DispositionStatus
    actor_id: str
    rationale: str
    source_revision: str
    at: str
    event_id: str
    actor_class: ActorClass = ActorClass.HUMAN


@dataclass(frozen=True, slots=True)
class RecordRelationCommand:
    packet_id: str
    edge_type: RelationType
    from_id: str
    to_id: str
    actor_id: str
    rationale: str
    source_revision: str
    at: str
    event_id: str
    actor_class: ActorClass = ActorClass.HUMAN


@dataclass(frozen=True, slots=True)
class RecordExecutionLinkCommand:
    packet_id: str
    finding_id: str
    execution_status: ExecutionStatus
    external_ref: str
    actor_id: str
    rationale: str
    source_revision: str
    at: str
    event_id: str
    actor_class: ActorClass = ActorClass.HUMAN


@dataclass(frozen=True, slots=True)
class RecordVerificationCommand:
    packet_id: str
    finding_id: str
    verification_result: VerificationStatus
    proof_class: ProofClass
    tested_revision: str
    evidence_anchors: tuple[str, ...]
    completed_scope: tuple[str, ...]
    residual_scope: tuple[str, ...]
    non_claims: tuple[str, ...]
    actor_id: str
    rationale: str
    source_revision: str
    at: str
    event_id: str
    actor_class: ActorClass = ActorClass.HUMAN


@dataclass(frozen=True, slots=True)
class ReopenFindingCommand:
    packet_id: str
    finding_id: str
    actor_id: str
    rationale: str
    source_revision: str
    at: str
    event_id: str
    actor_class: ActorClass = ActorClass.HUMAN


@dataclass(frozen=True, slots=True)
class AppendEventReport:
    schema_version: str
    authoritative: bool
    authority_required: bool
    packet_id: str
    event_id: str
    sequence: int
    finding_id: str | None
    disposition_status: DispositionStatus | None
    execution_status: ExecutionStatus | None
    verification_status: VerificationStatus | None
    edge_type: RelationType | None
    derived_status: DerivedStatus | None
    envelope_sha256: str
    non_claims: tuple[str, ...]


def _map_port_error(error: ReviewCasePortError, *, operation: str) -> ReviewCaseApplicationError:
    return ReviewCaseApplicationError(
        code=error.code,
        operation=operation,
        message=error.message,
        cause_code=error.operation,
    )


def _map_validation_error(
    error: ReviewCaseValidationError,
    *,
    operation: str,
) -> ReviewCaseApplicationError:
    first = error.violations[0]
    return ReviewCaseApplicationError(
        code=first.code,
        operation=operation,
        message=first.message,
        cause_code="validation",
    )


def _count_statuses(packets: Sequence[ReviewPacket]) -> dict[str, int]:
    counts = {
        "open": 0,
        "blocked": 0,
        "partial": 0,
        "closed": 0,
        "stale": 0,
        "ready_for_closure": 0,
        "terminal_without_implementation": 0,
    }
    for packet in packets:
        for _, status in derive_packet_statuses(packet):
            counts[status.value] = counts.get(status.value, 0) + 1
    return counts


def _build_registered_packet(
    command: RegisterReviewCaseCommand,
    *,
    content_sha256: str,
) -> ReviewPacket:
    return ReviewPacket(
        packet_id=command.packet_id,
        source=ReviewSource(
            path=command.source_path,
            content_sha256=content_sha256,
            reviewed_git_revision=command.reviewed_revision,
            received_at=command.received_at,
            source_kind=command.source_kind,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.DRAFT_EXTRACTED,
            method=command.normalization_method,
            source_hash=content_sha256,
            extractor_version=command.extractor_version,
        ),
        non_claims=command.non_claims,
        findings=(),
        edges=(),
        events=(
            ReviewEvent(
                event_id=f"{command.packet_id}:packet_registered",
                event_type=EventType.PACKET_REGISTERED,
                at=command.received_at,
                actor_class=ActorClass.TOOL,
                source_revision=command.reviewed_revision,
                rationale="Register immutable review source as draft packet",
            ),
        ),
    )


def register_review_case(
    command: RegisterReviewCaseCommand,
    reader: ReviewSourceReader,
    hasher: ContentHasher,
    store: ReviewPacketStore,
) -> RegisterReviewCaseReport:
    operation = "register_review_case"
    try:
        preflight_packet = _build_registered_packet(command, content_sha256="0" * 64)
        validate_review_policy((preflight_packet,))
        source_bytes = reader.read_bytes(command.source_path)
        content_sha256 = hasher.sha256(source_bytes)
        packet = _build_registered_packet(command, content_sha256=content_sha256)
        validate_review_policy((packet,))
        store.add(packet)
    except ReviewCasePortError as error:
        raise _map_port_error(error, operation=operation) from error
    except ReviewCaseValidationError as error:
        raise _map_validation_error(error, operation=operation) from error
    except ReviewCaseApplicationError:
        raise
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ReviewCaseApplicationError(
            code="unexpected_failure",
            operation=operation,
            message="unexpected application failure",
        ) from error

    return RegisterReviewCaseReport(
        schema_version=APP_REPORT_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        packet_id=command.packet_id,
        source_path=command.source_path,
        reviewed_revision=command.reviewed_revision,
        content_sha256=content_sha256,
        finding_count=0,
        non_claims=_DEFAULT_NON_CLAIMS + command.non_claims,
    )


def validate_review_cases(
    reader: ReviewSourceReader,
    hasher: ContentHasher,
    store: ReviewPacketStore,
) -> ValidateReviewCasesReport:
    operation = "validate_review_cases"
    try:
        packets = store.list_all()
        for packet in packets:
            source_bytes = reader.read_bytes(packet.source.path)
            current_hash = hasher.sha256(source_bytes)
            if (
                current_hash != packet.source.content_sha256
                or current_hash != packet.normalization.source_hash
            ):
                raise ReviewCaseApplicationError(
                    code="source_hash_drift",
                    operation=operation,
                    message="current source hash does not match stored packet hashes",
                )
        validate_review_policy(packets)
    except ReviewCasePortError as error:
        raise _map_port_error(error, operation=operation) from error
    except ReviewCaseValidationError as error:
        raise _map_validation_error(error, operation=operation) from error
    except ReviewCaseApplicationError:
        raise
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ReviewCaseApplicationError(
            code="unexpected_failure",
            operation=operation,
            message="unexpected application failure",
        ) from error

    counts = _count_statuses(packets)
    finding_count = sum(len(packet.findings) for packet in packets)
    return ValidateReviewCasesReport(
        schema_version=APP_REPORT_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        ok=True,
        packet_count=len(packets),
        finding_count=finding_count,
        open_count=counts.get("open", 0),
        blocked_count=counts.get("blocked", 0),
        partial_count=counts.get("partial", 0),
        closed_count=counts.get("closed", 0),
        stale_count=counts.get("stale", 0),
        non_claims=_DEFAULT_NON_CLAIMS,
    )


def review_case_status(
    store: ReviewPacketStore,
    packet_id: str | None = None,
) -> ReviewCaseStatusReport:
    operation = "review_case_status"
    try:
        if packet_id is None:
            packets = store.list_all()
        else:
            packets = (store.get(packet_id),)
    except ReviewCasePortError as error:
        raise _map_port_error(error, operation=operation) from error
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ReviewCaseApplicationError(
            code="unexpected_failure",
            operation=operation,
            message="unexpected application failure",
        ) from error

    ordered = tuple(sorted(packets, key=lambda item: item.packet_id))
    packet_rows: list[
        tuple[
            str,
            str,
            str,
            str,
            tuple[tuple[str, str], ...],
        ]
    ] = []
    open_blockers: list[tuple[str, str]] = []
    for packet in ordered:
        finding_rows = tuple(
            (finding_id, status.value) for finding_id, status in derive_packet_statuses(packet)
        )
        packet_rows.append(
            (
                packet.packet_id,
                packet.source.path,
                packet.source.reviewed_git_revision,
                packet.source.content_sha256,
                finding_rows,
            )
        )
        for finding in packet.findings:
            status = derive_finding_status(packet, finding.finding_id)
            if status is DerivedStatus.BLOCKED:
                open_blockers.append((packet.packet_id, finding.finding_id))

    return ReviewCaseStatusReport(
        schema_version=APP_REPORT_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        packets=tuple(packet_rows),
        open_blockers=tuple(open_blockers),
        non_claims=_DEFAULT_NON_CLAIMS,
    )


def _require_human_actor(*, actor_class: ActorClass, actor_id: str, operation: str) -> None:
    if actor_class is not ActorClass.HUMAN:
        raise ReviewCaseApplicationError(
            code="human_actor_required",
            operation=operation,
            message="only actor_class=human may record disposition, relation, execution, or reopen",
        )
    if not isinstance(actor_id, str) or not actor_id.strip() or actor_id != actor_id.strip():
        raise ReviewCaseApplicationError(
            code="invalid_actor",
            operation=operation,
            message="human actor_id is required",
        )


def materialize_review_packet(
    store: ReviewPacketStore,
    ledger: EventLedger,
    packet_id: str,
) -> ReviewPacket:
    """Load immutable base packet and replay append-only ledger events."""
    operation = "materialize_review_packet"
    try:
        base = store.get(packet_id)
        envelopes = ledger.list_envelopes(packet_id)
        events = tuple(item.event for item in envelopes)
        return replay_events(base, events)
    except ReviewCasePortError as error:
        raise _map_port_error(error, operation=operation) from error
    except ReviewCaseValidationError as error:
        raise _map_validation_error(error, operation=operation) from error
    except ReviewCaseApplicationError:
        raise
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ReviewCaseApplicationError(
            code="unexpected_failure",
            operation=operation,
            message="unexpected application failure",
        ) from error


def _append_event(
    *,
    operation: str,
    packet_id: str,
    event: ReviewEvent,
    source_revision: str,
    store: ReviewPacketStore,
    ledger: EventLedger,
    finding_id: str | None,
) -> AppendEventReport:
    try:
        current = materialize_review_packet(store, ledger, packet_id)
        # Pure apply first so invalid transitions never touch the ledger.
        projected = apply_event(current, event)
        envelope = ledger.append(packet_id, event, source_revision=source_revision)
        # Re-materialize from durable state after append.
        materialized = materialize_review_packet(store, ledger, packet_id)
        if materialized != projected:
            raise ReviewCaseApplicationError(
                code="ledger_projection_mismatch",
                operation=operation,
                message="materialized state diverged from pure apply projection",
            )
    except ReviewCasePortError as error:
        raise _map_port_error(error, operation=operation) from error
    except ReviewCaseValidationError as error:
        raise _map_validation_error(error, operation=operation) from error
    except ReviewCaseApplicationError:
        raise
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ReviewCaseApplicationError(
            code="unexpected_failure",
            operation=operation,
            message="unexpected application failure",
        ) from error

    finding = next(
        (item for item in materialized.findings if item.finding_id == finding_id),
        None,
    )
    derived = (
        derive_finding_status(materialized, finding.finding_id) if finding is not None else None
    )
    return AppendEventReport(
        schema_version=APP_REPORT_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        packet_id=packet_id,
        event_id=event.event_id,
        sequence=envelope.sequence,
        finding_id=finding_id,
        disposition_status=None if finding is None else finding.disposition_status,
        execution_status=None if finding is None else finding.execution_status,
        verification_status=None if finding is None else finding.verification_status,
        edge_type=event.edge_type,
        derived_status=derived,
        envelope_sha256=envelope.envelope_sha256,
        non_claims=_DEFAULT_NON_CLAIMS,
    )


def record_human_disposition(
    command: RecordDispositionCommand,
    store: ReviewPacketStore,
    ledger: EventLedger,
) -> AppendEventReport:
    operation = "record_human_disposition"
    _require_human_actor(
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        operation=operation,
    )
    if not command.rationale.strip():
        raise ReviewCaseApplicationError(
            code="empty_text",
            operation=operation,
            message="disposition rationale is required",
        )
    event = ReviewEvent(
        event_id=command.event_id,
        event_type=EventType.DISPOSITION_RECORDED,
        at=command.at,
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        finding_id=command.finding_id,
        source_revision=command.source_revision,
        rationale=command.rationale,
        disposition=command.disposition,
    )
    return _append_event(
        operation=operation,
        packet_id=command.packet_id,
        event=event,
        source_revision=command.source_revision,
        store=store,
        ledger=ledger,
        finding_id=command.finding_id,
    )


def record_relation(
    command: RecordRelationCommand,
    store: ReviewPacketStore,
    ledger: EventLedger,
) -> AppendEventReport:
    operation = "record_relation"
    _require_human_actor(
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        operation=operation,
    )
    if not command.rationale.strip():
        raise ReviewCaseApplicationError(
            code="empty_text",
            operation=operation,
            message="relation rationale is required",
        )
    event = ReviewEvent(
        event_id=command.event_id,
        event_type=EventType.EDGE_ASSERTED,
        at=command.at,
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        finding_id=command.from_id,
        source_revision=command.source_revision,
        rationale=command.rationale,
        edge_type=command.edge_type,
        from_id=command.from_id,
        to_id=command.to_id,
    )
    return _append_event(
        operation=operation,
        packet_id=command.packet_id,
        event=event,
        source_revision=command.source_revision,
        store=store,
        ledger=ledger,
        finding_id=command.from_id,
    )


def record_execution_link_command(
    command: RecordExecutionLinkCommand,
    store: ReviewPacketStore,
    ledger: EventLedger,
) -> AppendEventReport:
    operation = "record_execution_link_command"
    _require_human_actor(
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        operation=operation,
    )
    if not command.rationale.strip():
        raise ReviewCaseApplicationError(
            code="empty_text",
            operation=operation,
            message="execution-link rationale is required",
        )
    if not command.external_ref.strip():
        raise ReviewCaseApplicationError(
            code="empty_text",
            operation=operation,
            message="opaque external execution reference is required",
        )
    event = ReviewEvent(
        event_id=command.event_id,
        event_type=EventType.EXECUTION_LINKED,
        at=command.at,
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        finding_id=command.finding_id,
        source_revision=command.source_revision,
        rationale=command.rationale,
        to_id=command.external_ref,
        completed_scope=(command.execution_status.value,),
        non_claims=("Does not create or mutate GSD lifecycle",),
    )
    return _append_event(
        operation=operation,
        packet_id=command.packet_id,
        event=event,
        source_revision=command.source_revision,
        store=store,
        ledger=ledger,
        finding_id=command.finding_id,
    )


def record_verification_event(
    command: RecordVerificationCommand,
    store: ReviewPacketStore,
    ledger: EventLedger,
) -> AppendEventReport:
    operation = "record_verification_event"
    if command.actor_class not in {ActorClass.HUMAN, ActorClass.TOOL}:
        raise ReviewCaseApplicationError(
            code="human_or_tool_actor_required",
            operation=operation,
            message="verification requires actor_class=human or tool",
        )
    if command.actor_class is ActorClass.HUMAN:
        _require_human_actor(
            actor_class=command.actor_class,
            actor_id=command.actor_id,
            operation=operation,
        )
    elif not command.actor_id.strip():
        raise ReviewCaseApplicationError(
            code="invalid_actor",
            operation=operation,
            message="tool actor_id is required for verification",
        )
    event = ReviewEvent(
        event_id=command.event_id,
        event_type=EventType.VERIFICATION_RECORDED,
        at=command.at,
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        finding_id=command.finding_id,
        source_revision=command.source_revision,
        rationale=command.rationale,
        proof_class=command.proof_class,
        verification_result=command.verification_result,
        tested_revision=command.tested_revision,
        evidence_anchors=command.evidence_anchors,
        completed_scope=command.completed_scope,
        residual_scope=command.residual_scope,
        non_claims=command.non_claims,
    )
    return _append_event(
        operation=operation,
        packet_id=command.packet_id,
        event=event,
        source_revision=command.source_revision,
        store=store,
        ledger=ledger,
        finding_id=command.finding_id,
    )


def reopen_finding_command(
    command: ReopenFindingCommand,
    store: ReviewPacketStore,
    ledger: EventLedger,
) -> AppendEventReport:
    operation = "reopen_finding"
    _require_human_actor(
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        operation=operation,
    )
    if not command.rationale.strip():
        raise ReviewCaseApplicationError(
            code="empty_text",
            operation=operation,
            message="reopen rationale is required",
        )
    event = ReviewEvent(
        event_id=command.event_id,
        event_type=EventType.REOPENED,
        at=command.at,
        actor_class=command.actor_class,
        actor_id=command.actor_id,
        finding_id=command.finding_id,
        source_revision=command.source_revision,
        rationale=command.rationale,
    )
    return _append_event(
        operation=operation,
        packet_id=command.packet_id,
        event=event,
        source_revision=command.source_revision,
        store=store,
        ledger=ledger,
        finding_id=command.finding_id,
    )
