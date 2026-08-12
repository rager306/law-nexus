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
    EventType,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ReviewCaseValidationError,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
)
from law_nexus_harness.review_case.policy import (
    derive_finding_status,
    derive_packet_statuses,
    validate_review_policy,
)
from law_nexus_harness.review_case.ports import (
    ContentHasher,
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
