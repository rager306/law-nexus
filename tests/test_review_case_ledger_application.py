"""Application integration for append-only Review Case ledger commands.

In-memory ports only. No filesystem, codec, CLI, Governor, GSD mutation, or
authority promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DerivedStatus,
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
    RelationType,
    ReviewerSeverity,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
)
from law_nexus_harness.review_case.application import (
    APP_REPORT_SCHEMA_VERSION,
    RecordDispositionCommand,
    RecordExecutionLinkCommand,
    RecordRelationCommand,
    RecordVerificationCommand,
    ReopenFindingCommand,
    ReviewCaseApplicationError,
    materialize_review_packet,
    record_execution_link_command,
    record_human_disposition,
    record_relation,
    record_verification_event,
    reopen_finding_command,
)
from law_nexus_harness.review_case.ports import EventLedger, ReviewCasePortError, ReviewPacketStore

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
PATH = "doc/review/review-11-08-2026.md"
PACKET_ID = "RC-2026-08-11-001"
ANCHOR = "tests/test_review_case_ledger_application.py"


@dataclass
class InMemoryPacketStore:
    packets: dict[str, ReviewPacket] = field(default_factory=dict)

    def add(self, packet: ReviewPacket) -> None:
        if packet.packet_id in self.packets:
            raise ReviewCasePortError(
                code="duplicate_packet",
                operation="add",
                message="packet already exists",
            )
        self.packets[packet.packet_id] = packet

    def get(self, packet_id: str) -> ReviewPacket:
        if packet_id not in self.packets:
            raise ReviewCasePortError(
                code="packet_not_found",
                operation="get",
                message="packet is missing",
            )
        return self.packets[packet_id]

    def list_all(self) -> tuple[ReviewPacket, ...]:
        return tuple(self.packets[key] for key in sorted(self.packets))


@dataclass
class InMemoryEventLedger:
    envelopes: dict[str, list[EventLedgerEnvelope]] = field(default_factory=dict)
    fail_on_append: str | None = None

    def append(
        self,
        packet_id: str,
        event: ReviewEvent,
        *,
        source_revision: str,
    ) -> EventLedgerEnvelope:
        if self.fail_on_append is not None:
            raise ReviewCasePortError(
                code=self.fail_on_append,
                operation="append",
                message="ledger append failed",
            )
        chain = self.envelopes.setdefault(packet_id, [])
        if any(item.event.event_id == event.event_id for item in chain):
            raise ReviewCasePortError(
                code="duplicate_event_id",
                operation="append",
                message="event_id already exists",
            )
        sequence = len(chain) + 1
        previous = chain[-1].envelope_sha256 if chain else None
        envelope = EventLedgerEnvelope(
            packet_id=packet_id,
            sequence=sequence,
            previous_envelope_sha256=previous,
            event=event,
            event_sha256="b" * 64,
            source_revision=source_revision,
            envelope_sha256=("c" if sequence == 1 else "d") * 64,
        )
        chain.append(envelope)
        return envelope

    def list_envelopes(self, packet_id: str) -> tuple[EventLedgerEnvelope, ...]:
        return tuple(self.envelopes.get(packet_id, ()))


def base_packet(**overrides: Any) -> ReviewPacket:
    payload: dict[str, Any] = {
        "packet_id": PACKET_ID,
        "source": ReviewSource(
            path=PATH,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        "normalization": NormalizationRecord(
            status=NormalizationStatus.SOURCE_VERIFIED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
        ),
        "non_claims": ("Non-authoritative review projection",),
        "findings": (
            Finding(
                finding_id="RC11-F01",
                kind=FindingKind.GAP,
                concern_class=ConcernClass.DESIGN,
                reviewer_severity=ReviewerSeverity.CRITICAL,
                summary="Missing process contour",
                source_spans=(
                    SourceSpan(
                        path=PATH,
                        line_start=10,
                        line_end=20,
                        quote_sha256=HASH_B,
                        heading="# Gap",
                    ),
                ),
                candidate_targets=(
                    CandidateTarget(
                        surface=CandidateSurface.TSG,
                        id="TSG-006",
                        note="candidate only",
                    ),
                ),
                required_proof_class=ProofClass.IMPLEMENTATION,
                normalization_status=NormalizationStatus.SOURCE_VERIFIED,
                disposition_status=DispositionStatus.OPEN,
                execution_status=ExecutionStatus.UNPLANNED,
                verification_status=VerificationStatus.UNVERIFIED,
                non_claims=("Not an accepted requirement",),
            ),
        ),
        "edges": (),
        "events": (
            ReviewEvent(
                event_id=f"{PACKET_ID}:packet_registered",
                event_type=EventType.PACKET_REGISTERED,
                at=TS,
                actor_class=ActorClass.TOOL,
                source_revision=REV,
                rationale="Register immutable review source as draft packet",
            ),
        ),
    }
    payload.update(overrides)
    return ReviewPacket(**payload)


def ports() -> tuple[InMemoryPacketStore, InMemoryEventLedger]:
    store = InMemoryPacketStore()
    store.add(base_packet())
    return store, InMemoryEventLedger()


def test_memory_ports_satisfy_protocols() -> None:
    store, ledger = ports()
    assert isinstance(store, ReviewPacketStore)
    assert isinstance(ledger, EventLedger)


def test_record_human_disposition_appends_and_materializes() -> None:
    store, ledger = ports()
    report = record_human_disposition(
        RecordDispositionCommand(
            packet_id=PACKET_ID,
            finding_id="RC11-F01",
            disposition=DispositionStatus.ACCEPTED_AS_GAP,
            actor_id="human-reviewer-1",
            rationale="Accepted as architecture gap after review",
            source_revision=REV,
            at=TS2,
            event_id="E-DISP-1",
        ),
        store,
        ledger,
    )
    assert report.schema_version == APP_REPORT_SCHEMA_VERSION
    assert report.authoritative is False
    assert report.authority_required is True
    assert report.packet_id == PACKET_ID
    assert report.sequence == 1
    assert report.event_id == "E-DISP-1"
    assert report.finding_id == "RC11-F01"
    assert report.disposition_status is DispositionStatus.ACCEPTED_AS_GAP
    assert report.derived_status is DerivedStatus.OPEN
    assert "Does not promote" in " ".join(report.non_claims)
    # Base packet in store remains open; materialization comes from ledger.
    assert store.get(PACKET_ID).findings[0].disposition_status is DispositionStatus.OPEN
    materialized = materialize_review_packet(store, ledger, PACKET_ID)
    assert materialized.findings[0].disposition_status is DispositionStatus.ACCEPTED_AS_GAP
    assert len(ledger.list_envelopes(PACKET_ID)) == 1


def test_tool_or_llm_actor_cannot_record_disposition() -> None:
    store, ledger = ports()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        record_human_disposition(
            RecordDispositionCommand(
                packet_id=PACKET_ID,
                finding_id="RC11-F01",
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
                actor_id="bot",
                actor_class=ActorClass.TOOL,
                rationale="Automated acceptance is forbidden",
                source_revision=REV,
                at=TS2,
                event_id="E-DISP-TOOL",
            ),
            store,
            ledger,
        )
    assert exc.value.code == "human_actor_required"
    assert ledger.list_envelopes(PACKET_ID) == ()


def test_missing_actor_or_rationale_fails_before_ledger() -> None:
    store, ledger = ports()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        record_human_disposition(
            RecordDispositionCommand(
                packet_id=PACKET_ID,
                finding_id="RC11-F01",
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
                actor_id="",
                rationale="Has rationale but empty actor",
                source_revision=REV,
                at=TS2,
                event_id="E-DISP-BAD",
            ),
            store,
            ledger,
        )
    assert exc.value.code in {"invalid_actor", "empty_text", "invalid_id"}
    assert ledger.list_envelopes(PACKET_ID) == ()


def test_unknown_finding_and_ledger_failure_fail_closed() -> None:
    store, ledger = ports()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        record_human_disposition(
            RecordDispositionCommand(
                packet_id=PACKET_ID,
                finding_id="MISSING",
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
                actor_id="human-reviewer-1",
                rationale="Unknown target",
                source_revision=REV,
                at=TS2,
                event_id="E-DISP-MISSING",
            ),
            store,
            ledger,
        )
    assert exc.value.code == "unknown_finding"
    ledger.fail_on_append = "ledger_write_failed"
    with pytest.raises(ReviewCaseApplicationError) as exc2:
        record_human_disposition(
            RecordDispositionCommand(
                packet_id=PACKET_ID,
                finding_id="RC11-F01",
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
                actor_id="human-reviewer-1",
                rationale="Ledger unavailable",
                source_revision=REV,
                at=TS2,
                event_id="E-DISP-1",
            ),
            store,
            ledger,
        )
    assert exc2.value.code == "ledger_write_failed"
    assert store.get(PACKET_ID).findings[0].disposition_status is DispositionStatus.OPEN


def test_relation_execution_verification_and_reopen_flow() -> None:
    store, ledger = ports()
    record_human_disposition(
        RecordDispositionCommand(
            packet_id=PACKET_ID,
            finding_id="RC11-F01",
            disposition=DispositionStatus.ACCEPTED_AS_GAP,
            actor_id="human-reviewer-1",
            rationale="Accepted gap",
            source_revision=REV,
            at=TS2,
            event_id="E-DISP-1",
        ),
        store,
        ledger,
    )
    relation = record_relation(
        RecordRelationCommand(
            packet_id=PACKET_ID,
            edge_type=RelationType.PROMOTED_TO,
            from_id="RC11-F01",
            to_id="TSG-006",
            actor_id="human-reviewer-1",
            rationale="Opaque authority reference only",
            source_revision=REV,
            at=TS2,
            event_id="E-EDGE-1",
        ),
        store,
        ledger,
    )
    assert relation.edge_type is RelationType.PROMOTED_TO
    assert relation.sequence == 2
    execution = record_execution_link_command(
        RecordExecutionLinkCommand(
            packet_id=PACKET_ID,
            finding_id="RC11-F01",
            execution_status=ExecutionStatus.IMPLEMENTED,
            external_ref="GSD-M166-S04-T03",
            actor_id="human-reviewer-1",
            rationale="Opaque execution reference only",
            source_revision=REV,
            at=TS2,
            event_id="E-EXEC-1",
        ),
        store,
        ledger,
    )
    assert execution.execution_status is ExecutionStatus.IMPLEMENTED
    assert execution.derived_status is DerivedStatus.READY_FOR_CLOSURE
    verification = record_verification_event(
        RecordVerificationCommand(
            packet_id=PACKET_ID,
            finding_id="RC11-F01",
            verification_result=VerificationStatus.PASSED_BOUNDED,
            proof_class=ProofClass.IMPLEMENTATION,
            tested_revision=REV,
            evidence_anchors=(ANCHOR,),
            completed_scope=("ledger application proof",),
            residual_scope=(),
            non_claims=("No product readiness claim",),
            actor_id="human-reviewer-1",
            rationale="Class-matched proof recorded",
            source_revision=REV,
            at=TS2,
            event_id="E-VER-1",
        ),
        store,
        ledger,
    )
    assert verification.verification_status is VerificationStatus.PASSED_BOUNDED
    assert verification.derived_status is DerivedStatus.CLOSED
    reopened = reopen_finding_command(
        ReopenFindingCommand(
            packet_id=PACKET_ID,
            finding_id="RC11-F01",
            actor_id="human-reviewer-1",
            rationale="Residual gap found after closure",
            source_revision=REV,
            at=TS2,
            event_id="E-REOPEN-1",
        ),
        store,
        ledger,
    )
    assert reopened.disposition_status is DispositionStatus.OPEN
    assert reopened.derived_status is DerivedStatus.OPEN
    material = materialize_review_packet(store, ledger, PACKET_ID)
    assert material.findings[0].disposition_status is DispositionStatus.OPEN
    # base registration + disposition + relation + execution + verification + reopen
    assert len(material.events) == 6
    assert any(item.event_type is EventType.REOPENED for item in material.events)


def test_no_cli_disposition_surface_and_no_gsd_mirroring() -> None:
    import inspect

    import law_nexus_harness.cli as cli_mod
    import law_nexus_harness.review_case.application as app_mod

    source = inspect.getsource(cli_mod)
    assert "record_human_disposition" not in source
    assert "disposition" not in {name for name in dir(cli_mod) if "disposition" in name.lower()}
    # Application must not import GSD or mutate external lifecycle modules.
    app_source = inspect.getsource(app_mod)
    assert "gsd_" not in app_source
    assert "create_milestone" not in app_source
    assert "roadmap" not in app_source.lower() or "Does not" in app_source
