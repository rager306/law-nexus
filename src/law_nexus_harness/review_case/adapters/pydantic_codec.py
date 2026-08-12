"""Outer Pydantic v2 codec for review-case/v1.

Adapter-only. Public load/dump APIs return pure domain types, never BaseModel.
Tracked `prd/architecture/review-case.schema.json` remains wire authority;
generated schema is diagnostics only.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Mapping, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from law_nexus_harness.review_case.domain import (
    EVENT_LEDGER_SCHEMA_VERSION,
    ActorClass,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DispositionStatus,
    EventLedgerEnvelope,
    EventType,
    ExecutionStatus,
    Finding,
    FindingKind,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ProofClass,
    RelationStatus,
    RelationType,
    ReviewCaseValidationError,
    ReviewEdge,
    ReviewerSeverity,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
)
from law_nexus_harness.review_case.policy import validate_review_policy

_WIRE_CONFIG = ConfigDict(strict=True, extra="forbid", frozen=True)
_VERIFICATION_RESULT_VALUES = frozenset(
    {
        VerificationStatus.PASSED_BOUNDED.value,
        VerificationStatus.PASSED_SMOKE.value,
        VerificationStatus.FAILED.value,
        VerificationStatus.INCONCLUSIVE.value,
    }
)


class ReviewCaseCodecError(Exception):
    """Structured codec failure without raw input values or secret bytes."""

    def __init__(
        self,
        *,
        code: str,
        field_path: tuple[str | int, ...],
        message: str,
    ) -> None:
        if not code or not message:
            raise ValueError("ReviewCaseCodecError requires code and message")
        self.code = code
        self.field_path = tuple(field_path)
        self.message = message
        path = ".".join(str(part) for part in self.field_path) if self.field_path else "$"
        super().__init__(f"{code} at {path}: {message}")


class _WireModel(BaseModel):
    model_config = _WIRE_CONFIG


class SourceWire(_WireModel):
    path: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_git_revision: str = Field(min_length=40, max_length=40, pattern=r"^[a-f0-9]{40}$")
    received_at: str = Field(min_length=1, pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T")
    source_kind: SourceKind

    @field_validator("path")
    @classmethod
    def _reject_absolute_path(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("path must be repository-relative")
        return value


class NormalizationWire(_WireModel):
    status: NormalizationStatus
    method: NormalizationMethod
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    extractor_version: str | None = Field(default=None, min_length=1)


class SourceSpanWire(_WireModel):
    path: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    quote_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    heading: str | None = Field(default=None, min_length=1)

    @field_validator("path")
    @classmethod
    def _reject_absolute_path(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("path must be repository-relative")
        return value

    @model_validator(mode="after")
    def _line_range(self) -> SourceSpanWire:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be >= line_start")
        return self


class CandidateTargetWire(_WireModel):
    surface: CandidateSurface
    id: str = Field(min_length=1)
    note: str | None = Field(default=None, min_length=1)


class FindingWire(_WireModel):
    finding_id: str = Field(min_length=1)
    kind: FindingKind
    concern_class: ConcernClass
    reviewer_severity: ReviewerSeverity
    summary: str = Field(min_length=1)
    source_spans: list[SourceSpanWire] = Field(min_length=1)
    candidate_targets: list[CandidateTargetWire]
    required_proof_class: ProofClass
    normalization_status: NormalizationStatus
    disposition_status: DispositionStatus
    execution_status: ExecutionStatus
    verification_status: VerificationStatus
    non_claims: list[str] = Field(min_length=1)


class EdgeWire(_WireModel):
    type: RelationType
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    status: RelationStatus
    note: str | None = Field(default=None, min_length=1)


class EventPayloadWire(_WireModel):
    disposition: DispositionStatus | None = None
    edge_type: RelationType | None = None
    from_: str | None = Field(default=None, alias="from", min_length=1)
    to: str | None = Field(default=None, min_length=1)
    proof_class: ProofClass | None = None
    verification_result: (
        Literal[
            "passed_bounded",
            "passed_smoke",
            "failed",
            "inconclusive",
        ]
        | None
    ) = None
    tested_revision: str | None = Field(
        default=None,
        min_length=40,
        max_length=40,
        pattern=r"^[a-f0-9]{40}$",
    )
    evidence_anchors: list[str] | None = Field(default=None, min_length=1)
    completed_scope: list[str] | None = None
    residual_scope: list[str] | None = None
    non_claims: list[str] | None = Field(default=None, min_length=1)

    @field_validator("evidence_anchors")
    @classmethod
    def _reject_absolute_anchors(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        for value in values:
            if value.startswith("/"):
                raise ValueError("evidence anchor must be repository-relative")
        return values


class EventWire(_WireModel):
    event_id: str = Field(min_length=1)
    event_type: EventType
    at: str = Field(min_length=1, pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T")
    actor_class: ActorClass
    actor_id: str | None = Field(default=None, min_length=1)
    finding_id: str | None = Field(default=None, min_length=1)
    source_revision: str | None = Field(
        default=None,
        min_length=40,
        max_length=40,
        pattern=r"^[a-f0-9]{40}$",
    )
    tested_revision: str | None = Field(
        default=None,
        min_length=40,
        max_length=40,
        pattern=r"^[a-f0-9]{40}$",
    )
    rationale: str | None = Field(default=None, min_length=1)
    payload: EventPayloadWire | None = None

    @model_validator(mode="after")
    def _reject_root_tested_revision(self) -> EventWire:
        if self.tested_revision is not None:
            raise ValueError("tested_revision is payload-only in the codec wire policy")
        return self


class EnvelopeWire(_WireModel):
    schema_version: Literal["review-case-event-ledger/v1"]
    authoritative: Literal[False]
    authority_required: Literal[True]
    packet_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    previous_envelope_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
    )
    event: EventWire
    event_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(min_length=40, max_length=40, pattern=r"^[a-f0-9]{40}$")
    envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("authoritative", mode="before")
    @classmethod
    def _require_json_false(cls, value: object) -> object:
        if value is not False:
            raise ValueError("authoritative must be JSON false")
        return value

    @field_validator("authority_required", mode="before")
    @classmethod
    def _require_json_true(cls, value: object) -> object:
        if value is not True:
            raise ValueError("authority_required must be JSON true")
        return value


class PacketWire(_WireModel):
    schema_version: Literal["review-case/v1"]
    authoritative: Literal[False]
    authority_required: Literal[True]

    @field_validator("authoritative", mode="before")
    @classmethod
    def _require_json_false(cls, value: object) -> object:
        if value is not False:
            raise ValueError("authoritative must be JSON false")
        return value

    @field_validator("authority_required", mode="before")
    @classmethod
    def _require_json_true(cls, value: object) -> object:
        if value is not True:
            raise ValueError("authority_required must be JSON true")
        return value

    packet_id: str = Field(min_length=1)
    source: SourceWire
    normalization: NormalizationWire
    non_claims: list[str] = Field(min_length=1)
    findings: list[FindingWire]
    edges: list[EdgeWire]
    events: list[EventWire]


def _field_path(error: Any) -> tuple[str | int, ...]:
    parts: list[str | int] = []
    for item in error.get("loc", ()):
        if isinstance(item, (str, int)):
            parts.append(item)
        else:
            parts.append(str(item))
    return tuple(parts)


def _from_validation_error(error: ValidationError) -> ReviewCaseCodecError:
    first = error.errors(include_url=False)[0]
    field_path = _field_path(first)
    message = str(first.get("msg", "wire validation failed"))
    if "tested_revision" in message and not any(part == "tested_revision" for part in field_path):
        field_path = (*field_path, "tested_revision")
    return ReviewCaseCodecError(
        code="wire_validation",
        field_path=field_path,
        message=message,
    )


def _to_source(model: SourceWire) -> ReviewSource:
    return ReviewSource(
        path=model.path,
        content_sha256=model.content_sha256,
        reviewed_git_revision=model.reviewed_git_revision,
        received_at=model.received_at,
        source_kind=model.source_kind,
    )


def _to_normalization(model: NormalizationWire) -> NormalizationRecord:
    return NormalizationRecord(
        status=model.status,
        method=model.method,
        source_hash=model.source_hash,
        extractor_version=model.extractor_version,
    )


def _to_span(model: SourceSpanWire) -> SourceSpan:
    return SourceSpan(
        path=model.path,
        line_start=model.line_start,
        line_end=model.line_end,
        quote_sha256=model.quote_sha256,
        heading=model.heading,
    )


def _to_target(model: CandidateTargetWire) -> CandidateTarget:
    return CandidateTarget(surface=model.surface, id=model.id, note=model.note)


def _to_finding(model: FindingWire) -> Finding:
    return Finding(
        finding_id=model.finding_id,
        kind=model.kind,
        concern_class=model.concern_class,
        reviewer_severity=model.reviewer_severity,
        summary=model.summary,
        source_spans=tuple(_to_span(item) for item in model.source_spans),
        candidate_targets=tuple(_to_target(item) for item in model.candidate_targets),
        required_proof_class=model.required_proof_class,
        normalization_status=model.normalization_status,
        disposition_status=model.disposition_status,
        execution_status=model.execution_status,
        verification_status=model.verification_status,
        non_claims=tuple(model.non_claims),
    )


def _to_edge(model: EdgeWire) -> ReviewEdge:
    return ReviewEdge(
        type=model.type,
        from_id=model.from_,
        to_id=model.to,
        status=model.status,
        note=model.note,
    )


def _to_event(model: EventWire) -> ReviewEvent:
    payload = model.payload
    tested_revision = None if payload is None else payload.tested_revision
    verification_result: VerificationStatus | None = None
    if payload is not None and payload.verification_result is not None:
        verification_result = VerificationStatus(payload.verification_result)
    return ReviewEvent(
        event_id=model.event_id,
        event_type=model.event_type,
        at=model.at,
        actor_class=model.actor_class,
        actor_id=model.actor_id,
        finding_id=model.finding_id,
        source_revision=model.source_revision,
        rationale=model.rationale,
        disposition=None if payload is None else payload.disposition,
        edge_type=None if payload is None else payload.edge_type,
        from_id=None if payload is None else payload.from_,
        to_id=None if payload is None else payload.to,
        proof_class=None if payload is None else payload.proof_class,
        verification_result=verification_result,
        tested_revision=tested_revision,
        evidence_anchors=(
            None
            if payload is None or payload.evidence_anchors is None
            else tuple(payload.evidence_anchors)
        ),
        completed_scope=(
            None
            if payload is None or payload.completed_scope is None
            else tuple(payload.completed_scope)
        ),
        residual_scope=(
            None
            if payload is None or payload.residual_scope is None
            else tuple(payload.residual_scope)
        ),
        non_claims=(
            None if payload is None or payload.non_claims is None else tuple(payload.non_claims)
        ),
    )


def _to_packet(model: PacketWire) -> ReviewPacket:
    return ReviewPacket(
        packet_id=model.packet_id,
        source=_to_source(model.source),
        normalization=_to_normalization(model.normalization),
        non_claims=tuple(model.non_claims),
        findings=tuple(_to_finding(item) for item in model.findings),
        edges=tuple(_to_edge(item) for item in model.edges),
        events=tuple(_to_event(item) for item in model.events),
    )


def _from_source(value: ReviewSource) -> SourceWire:
    return SourceWire(
        path=value.path,
        content_sha256=value.content_sha256,
        reviewed_git_revision=value.reviewed_git_revision,
        received_at=value.received_at,
        source_kind=value.source_kind,
    )


def _from_normalization(value: NormalizationRecord) -> NormalizationWire:
    return NormalizationWire(
        status=value.status,
        method=value.method,
        source_hash=value.source_hash,
        extractor_version=value.extractor_version,
    )


def _from_span(value: SourceSpan) -> SourceSpanWire:
    return SourceSpanWire(
        path=value.path,
        line_start=value.line_start,
        line_end=value.line_end,
        quote_sha256=value.quote_sha256,
        heading=value.heading,
    )


def _from_target(value: CandidateTarget) -> CandidateTargetWire:
    return CandidateTargetWire(surface=value.surface, id=value.id, note=value.note)


def _from_finding(value: Finding) -> FindingWire:
    return FindingWire(
        finding_id=value.finding_id,
        kind=value.kind,
        concern_class=value.concern_class,
        reviewer_severity=value.reviewer_severity,
        summary=value.summary,
        source_spans=[_from_span(item) for item in value.source_spans],
        candidate_targets=[_from_target(item) for item in value.candidate_targets],
        required_proof_class=value.required_proof_class,
        normalization_status=value.normalization_status,
        disposition_status=value.disposition_status,
        execution_status=value.execution_status,
        verification_status=value.verification_status,
        non_claims=list(value.non_claims),
    )


def _from_edge(value: ReviewEdge) -> EdgeWire:
    return EdgeWire.model_validate(
        {
            "type": value.type,
            "from": value.from_id,
            "to": value.to_id,
            "status": value.status,
            "note": value.note,
        }
    )


def _from_event(value: ReviewEvent) -> EventWire:
    payload_data: dict[str, Any] = {}
    if value.disposition is not None:
        payload_data["disposition"] = value.disposition
    if value.edge_type is not None:
        payload_data["edge_type"] = value.edge_type
    if value.from_id is not None:
        payload_data["from"] = value.from_id
    if value.to_id is not None:
        payload_data["to"] = value.to_id
    if value.proof_class is not None:
        payload_data["proof_class"] = value.proof_class
    if value.verification_result is not None:
        if value.verification_result.value not in _VERIFICATION_RESULT_VALUES:
            raise ReviewCaseCodecError(
                code="wire_validation",
                field_path=("events", "payload", "verification_result"),
                message="verification_result is outside closed wire enum",
            )
        payload_data["verification_result"] = value.verification_result.value
    if value.tested_revision is not None:
        # Proof/event tested_revision lives in payload per adapter mapping policy.
        payload_data["tested_revision"] = value.tested_revision
    if value.evidence_anchors is not None:
        payload_data["evidence_anchors"] = list(value.evidence_anchors)
    if value.completed_scope is not None:
        payload_data["completed_scope"] = list(value.completed_scope)
    if value.residual_scope is not None:
        payload_data["residual_scope"] = list(value.residual_scope)
    if value.non_claims is not None:
        payload_data["non_claims"] = list(value.non_claims)

    payload = EventPayloadWire.model_validate(payload_data) if payload_data else None
    return EventWire(
        event_id=value.event_id,
        event_type=value.event_type,
        at=value.at,
        actor_class=value.actor_class,
        actor_id=value.actor_id,
        finding_id=value.finding_id,
        source_revision=value.source_revision,
        tested_revision=None,
        rationale=value.rationale,
        payload=payload,
    )


def _from_packet(value: ReviewPacket) -> PacketWire:
    return PacketWire(
        schema_version="review-case/v1",
        authoritative=False,
        authority_required=True,
        packet_id=value.packet_id,
        source=_from_source(value.source),
        normalization=_from_normalization(value.normalization),
        non_claims=list(value.non_claims),
        findings=[_from_finding(item) for item in value.findings],
        edges=[_from_edge(item) for item in value.edges],
        events=[_from_event(item) for item in value.events],
    )


def _canonical_json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_packet(data: bytes) -> ReviewPacket:
    if not isinstance(data, (bytes, bytearray)):
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="packet input must be UTF-8 JSON bytes",
        )
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="packet input is not valid UTF-8 JSON",
        ) from error
    try:
        wire = PacketWire.model_validate_json(text, strict=True)
    except ValidationError as error:
        # Distinguish parse failures from schema/type failures.
        errors = error.errors(include_url=False)
        if errors and errors[0].get("type") == "json_invalid":
            raise ReviewCaseCodecError(
                code="invalid_json",
                field_path=(),
                message="packet input is not valid JSON",
            ) from error
        raise _from_validation_error(error) from error
    try:
        packet = _to_packet(wire)
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    try:
        validate_review_policy((packet,))
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="policy_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    return packet


def dump_packet(packet: ReviewPacket) -> bytes:
    try:
        validate_review_policy((packet,))
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="policy_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    try:
        wire = _from_packet(packet)
    except ReviewCaseCodecError:
        raise
    except ValidationError as error:
        raise _from_validation_error(error) from error
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    payload = wire.model_dump(mode="json", by_alias=True, exclude_none=True)
    return _canonical_json_bytes(cast(Mapping[str, Any], payload))


def dump_event(event: ReviewEvent) -> bytes:
    """Canonical JSON bytes for one pure ReviewEvent."""
    try:
        wire = _from_event(event)
    except ReviewCaseCodecError:
        raise
    except ValidationError as error:
        raise _from_validation_error(error) from error
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    payload = wire.model_dump(mode="json", by_alias=True, exclude_none=True)
    return _canonical_json_bytes(cast(Mapping[str, Any], payload))


def load_event(data: bytes) -> ReviewEvent:
    if not isinstance(data, (bytes, bytearray)):
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="event input must be UTF-8 JSON bytes",
        )
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="event input is not valid UTF-8 JSON",
        ) from error
    try:
        wire = EventWire.model_validate_json(text, strict=True)
    except ValidationError as error:
        errors = error.errors(include_url=False)
        if errors and errors[0].get("type") == "json_invalid":
            raise ReviewCaseCodecError(
                code="invalid_json",
                field_path=(),
                message="event input is not valid JSON",
            ) from error
        raise _from_validation_error(error) from error
    try:
        return _to_event(wire)
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error


def _envelope_wire(envelope: EventLedgerEnvelope) -> EnvelopeWire:
    try:
        return EnvelopeWire(
            schema_version=EVENT_LEDGER_SCHEMA_VERSION,
            authoritative=False,
            authority_required=True,
            packet_id=envelope.packet_id,
            sequence=envelope.sequence,
            previous_envelope_sha256=envelope.previous_envelope_sha256,
            event=_from_event(envelope.event),
            event_sha256=envelope.event_sha256,
            source_revision=envelope.source_revision,
            envelope_sha256=envelope.envelope_sha256,
        )
    except ValidationError as error:
        raise _from_validation_error(error) from error
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error


def _envelope_body_dict(envelope: EventLedgerEnvelope) -> dict[str, Any]:
    # Hash covers durable fields excluding envelope_sha256 itself.
    payload = _envelope_wire(envelope).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    payload.pop("envelope_sha256", None)
    return cast(dict[str, Any], payload)


def envelope_body_bytes(envelope: EventLedgerEnvelope) -> bytes:
    """Canonical body bytes used to compute envelope_sha256 (hash excluded)."""
    return _canonical_json_bytes(_envelope_body_dict(envelope))


def dump_envelope(envelope: EventLedgerEnvelope) -> bytes:
    """Canonical durable envelope bytes including envelope_sha256."""
    wire = _envelope_wire(envelope)
    payload = wire.model_dump(mode="json", by_alias=True, exclude_none=True)
    return _canonical_json_bytes(cast(Mapping[str, Any], payload))


def load_envelope(data: bytes) -> EventLedgerEnvelope:
    if not isinstance(data, (bytes, bytearray)):
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="envelope input must be UTF-8 JSON bytes",
        )
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReviewCaseCodecError(
            code="invalid_json",
            field_path=(),
            message="envelope input is not valid UTF-8 JSON",
        ) from error
    try:
        wire = EnvelopeWire.model_validate_json(text, strict=True)
    except ValidationError as error:
        errors = error.errors(include_url=False)
        if errors and errors[0].get("type") == "json_invalid":
            raise ReviewCaseCodecError(
                code="invalid_json",
                field_path=(),
                message="envelope input is not valid JSON",
            ) from error
        raise _from_validation_error(error) from error
    try:
        event = _to_event(wire.event)
        envelope = EventLedgerEnvelope(
            packet_id=wire.packet_id,
            sequence=wire.sequence,
            previous_envelope_sha256=wire.previous_envelope_sha256,
            event=event,
            event_sha256=wire.event_sha256,
            source_revision=wire.source_revision,
            envelope_sha256=wire.envelope_sha256,
        )
    except ReviewCaseValidationError as error:
        first = error.violations[0]
        raise ReviewCaseCodecError(
            code="domain_validation",
            field_path=tuple(part for part in first.field_path.split(".") if part),
            message=first.message,
        ) from error
    return envelope


def generated_wire_schema() -> dict[str, Any]:
    """Return Pydantic's unmodified diagnostic schema projection.

    The projection is not authority. Callers must resolve its native `$ref`
    structure when comparing it with the tracked review-case schema.
    """

    return PacketWire.model_json_schema(by_alias=True, mode="validation")
