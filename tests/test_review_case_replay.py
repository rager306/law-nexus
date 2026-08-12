"""Deterministic pure event replay for Review Case packets.

Non-authoritative process contour only. No filesystem I/O, codecs, CLI,
Governor, GSD, or product-domain semantics.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DerivedStatus,
    DispositionStatus,
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
    apply_event,
    assert_relation,
    derive_finding_status,
    mark_stale,
    record_disposition,
    record_normalization_review,
    record_verification,
    reopen_finding,
    replay_events,
    validate_review_policy,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
TS3 = "2026-08-12T01:00:00Z"
PATH = "doc/review/review-11-08-2026.md"
ANCHOR = "tests/test_review_case_replay.py"


def codes(exc: ReviewCaseValidationError) -> set[str]:
    return {item.code for item in exc.violations}


def source(**overrides: Any) -> ReviewSource:
    payload: dict[str, Any] = {
        "path": PATH,
        "content_sha256": HASH_A,
        "reviewed_git_revision": REV,
        "received_at": TS,
        "source_kind": SourceKind.HUMAN_EXTERNAL,
    }
    payload.update(overrides)
    return ReviewSource(**payload)


def normalization(**overrides: Any) -> NormalizationRecord:
    payload: dict[str, Any] = {
        "status": NormalizationStatus.SOURCE_VERIFIED,
        "method": NormalizationMethod.MANUAL,
        "source_hash": HASH_A,
    }
    payload.update(overrides)
    return NormalizationRecord(**payload)


def span(**overrides: Any) -> SourceSpan:
    payload: dict[str, Any] = {
        "path": PATH,
        "line_start": 10,
        "line_end": 20,
        "quote_sha256": HASH_B,
        "heading": "# Gap",
    }
    payload.update(overrides)
    return SourceSpan(**payload)


def finding(
    finding_id: str = "RC11-F01",
    *,
    required_proof_class: ProofClass = ProofClass.IMPLEMENTATION,
    **overrides: Any,
) -> Finding:
    payload: dict[str, Any] = {
        "finding_id": finding_id,
        "kind": FindingKind.GAP,
        "concern_class": ConcernClass.DESIGN,
        "reviewer_severity": ReviewerSeverity.CRITICAL,
        "summary": "Missing process contour",
        "source_spans": (span(),),
        "candidate_targets": (
            CandidateTarget(surface=CandidateSurface.TSG, id="TSG-006", note="candidate only"),
        ),
        "required_proof_class": required_proof_class,
        "normalization_status": NormalizationStatus.SOURCE_VERIFIED,
        "disposition_status": DispositionStatus.OPEN,
        "execution_status": ExecutionStatus.UNPLANNED,
        "verification_status": VerificationStatus.UNVERIFIED,
        "non_claims": ("Not an accepted requirement",),
    }
    payload.update(overrides)
    return Finding(**payload)


def base_packet(
    findings: tuple[Finding, ...] | None = None,
    **overrides: Any,
) -> ReviewPacket:
    """Immutable registered base: findings present, no consequential history."""
    payload: dict[str, Any] = {
        "packet_id": "RC-2026-08-11-001",
        "source": source(),
        "normalization": normalization(),
        "non_claims": ("Non-authoritative review projection",),
        "findings": findings if findings is not None else (finding(),),
        "edges": (),
        "events": (),
    }
    payload.update(overrides)
    return ReviewPacket(**payload)


def disposition_event(
    finding_id: str = "RC11-F01",
    disposition: DispositionStatus = DispositionStatus.ACCEPTED_AS_GAP,
    event_id: str = "E-DISP-1",
    actor_class: ActorClass = ActorClass.HUMAN,
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.DISPOSITION_RECORDED,
        "at": TS2,
        "actor_class": actor_class,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Human disposition",
        "disposition": disposition,
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def edge_event(
    edge: ReviewEdge,
    event_id: str = "E-EDGE-1",
    actor_class: ActorClass = ActorClass.HUMAN,
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.EDGE_ASSERTED,
        "at": TS2,
        "actor_class": actor_class,
        "finding_id": edge.from_id,
        "source_revision": REV,
        "rationale": "Human relation assertion",
        "edge_type": edge.type,
        "from_id": edge.from_id,
        "to_id": edge.to_id,
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def verification_event(
    finding_id: str = "RC11-F01",
    *,
    event_id: str = "E-VER-1",
    proof_class: ProofClass = ProofClass.IMPLEMENTATION,
    tested_revision: str | None = REV,
    evidence_anchors: Any = (ANCHOR,),
    completed_scope: Any = ("pure proof recorded",),
    residual_scope: Any = (),
    non_claims: Any = ("No product readiness claim",),
    actor_class: ActorClass = ActorClass.HUMAN,
    verification_result: VerificationStatus = VerificationStatus.PASSED_BOUNDED,
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.VERIFICATION_RECORDED,
        "at": TS2,
        "actor_class": actor_class,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Record class-matched proof",
        "proof_class": proof_class,
        "verification_result": verification_result,
        "tested_revision": tested_revision,
        "evidence_anchors": evidence_anchors,
        "completed_scope": completed_scope,
        "residual_scope": residual_scope,
        "non_claims": non_claims,
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def stale_event(
    finding_id: str = "RC11-F01",
    event_id: str = "E-STALE-1",
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.MARKED_STALE,
        "at": TS3,
        "actor_class": ActorClass.HUMAN,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Source or proof revision drifted",
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def reopen_event(
    finding_id: str = "RC11-F01",
    event_id: str = "E-REOPEN-1",
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.REOPENED,
        "at": TS3,
        "actor_class": ActorClass.HUMAN,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Reopen after residual gap",
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def normalization_event(
    event_id: str = "E-NORM-1",
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.NORMALIZATION_REVIEWED,
        "at": TS2,
        "actor_class": ActorClass.HUMAN,
        "source_revision": REV,
        "rationale": "Human normalization review",
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def execution_event(
    finding_id: str = "RC11-F01",
    *,
    event_id: str = "E-EXEC-1",
    execution_status: ExecutionStatus = ExecutionStatus.IMPLEMENTED,
    actor_class: ActorClass = ActorClass.HUMAN,
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.EXECUTION_LINKED,
        "at": TS2,
        "actor_class": actor_class,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Opaque execution reference only",
        "to_id": "GSD-M166-S04-T01",
        "completed_scope": (execution_status.value,),
        "non_claims": ("Does not create or mutate GSD lifecycle",),
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def test_replay_matches_command_built_disposition_and_relation() -> None:
    base = base_packet(findings=(finding("RC11-F01"), finding("RC11-F02")))
    edge = ReviewEdge(
        type=RelationType.REFINES,
        from_id="RC11-F02",
        to_id="RC11-F01",
        status=RelationStatus.ACCEPTED,
    )
    disp = disposition_event(finding_id="RC11-F01")
    rel = edge_event(edge)
    command_built = assert_relation(
        record_disposition(base, disp),
        edge,
        rel,
    )
    replayed = replay_events(base, (disp, rel))
    assert replayed is not base
    assert replayed is not command_built
    assert replayed == command_built
    assert derive_finding_status(replayed, "RC11-F01") is DerivedStatus.OPEN
    validate_review_policy((replayed,))


def test_replay_matches_verification_stale_and_reopen_chain() -> None:
    base = base_packet(
        findings=(
            finding(
                "RC11-F01",
                execution_status=ExecutionStatus.IMPLEMENTED,
            ),
        )
    )
    disp = disposition_event()
    ver = verification_event()
    stale = stale_event()
    reopen = reopen_event()
    command_built = reopen_finding(
        mark_stale(
            record_verification(
                record_disposition(base, disp),
                ver,
                status=VerificationStatus.PASSED_BOUNDED,
            ),
            stale,
        ),
        reopen,
    )
    replayed = replay_events(base, (disp, ver, stale, reopen))
    assert replayed == command_built
    assert replayed.findings[0].disposition_status is DispositionStatus.OPEN
    assert replayed.findings[0].execution_status is ExecutionStatus.UNPLANNED
    assert replayed.findings[0].verification_status is VerificationStatus.UNVERIFIED
    assert derive_finding_status(replayed, "RC11-F01") is DerivedStatus.OPEN


def test_replay_matches_normalization_review() -> None:
    base = base_packet()
    event = normalization_event()
    command_built = record_normalization_review(base, event)
    replayed = replay_events(base, (event,))
    assert replayed == command_built
    assert replayed.normalization.status is NormalizationStatus.HUMAN_REVIEWED


def test_apply_event_execution_linked_updates_execution_status() -> None:
    base = base_packet()
    disposed = record_disposition(base, disposition_event())
    linked = apply_event(disposed, execution_event())
    assert disposed.findings[0].execution_status is ExecutionStatus.UNPLANNED
    assert linked.findings[0].execution_status is ExecutionStatus.IMPLEMENTED
    assert linked.events[-1].event_type is EventType.EXECUTION_LINKED
    assert derive_finding_status(linked, "RC11-F01") is DerivedStatus.READY_FOR_CLOSURE
    validate_review_policy((linked,))


def test_replay_rejects_base_with_existing_consequential_history() -> None:
    base = replace(
        base_packet(),
        events=(disposition_event(),),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(base, (disposition_event(event_id="E-DISP-2"),))
    assert "base_packet_not_clean" in codes(exc.value)


def test_replay_rejects_duplicate_event_ids() -> None:
    base = base_packet()
    event = disposition_event()
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(base, (event, replace(event, at=TS3)))
    assert "duplicate_event_id" in codes(exc.value)


def test_replay_rejects_non_human_disposition() -> None:
    base = base_packet()
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(
            base,
            (disposition_event(actor_class=ActorClass.TOOL),),
        )
    assert "human_actor_required" in codes(exc.value)


def test_replay_rejects_stale_before_verification() -> None:
    base = base_packet()
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(
            base,
            (
                disposition_event(),
                stale_event(),
            ),
        )
    assert "prior_verification_required" in codes(exc.value)


def test_replay_rejects_mismatched_proof_class() -> None:
    base = base_packet(
        findings=(
            finding(
                execution_status=ExecutionStatus.IMPLEMENTED,
            ),
        )
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(
            base,
            (
                disposition_event(),
                verification_event(proof_class=ProofClass.DOCS),
            ),
        )
    assert "proof_class_mismatch" in codes(exc.value)


def test_replay_rejects_promoted_to_without_accepting_disposition() -> None:
    base = base_packet()
    edge = ReviewEdge(
        type=RelationType.PROMOTED_TO,
        from_id="RC11-F01",
        to_id="TSG-006",
        status=RelationStatus.ACCEPTED,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        replay_events(base, (edge_event(edge),))
    assert "promoted_to_requires_human_accepting_disposition" in codes(exc.value)


def test_replay_rejects_unknown_event_type_for_apply() -> None:
    base = base_packet()
    event = ReviewEvent(
        event_id="E-REG",
        event_type=EventType.PACKET_REGISTERED,
        at=TS,
        actor_class=ActorClass.TOOL,
        source_revision=REV,
        rationale="Registration belongs on the base packet, not the ledger tail",
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        apply_event(base, event)
    assert "unsupported_replay_event" in codes(exc.value)


def test_post_reopen_old_verification_is_not_closed() -> None:
    base = base_packet(
        findings=(
            finding(
                execution_status=ExecutionStatus.IMPLEMENTED,
            ),
        )
    )
    disp = disposition_event()
    ver = verification_event()
    reopen = reopen_event()
    replayed = replay_events(base, (disp, ver, reopen))
    assert derive_finding_status(replayed, "RC11-F01") is DerivedStatus.OPEN
    assert replayed.findings[0].verification_status is VerificationStatus.UNVERIFIED
    # Reusing the same old verification identity must fail after reopen.
    with pytest.raises(ReviewCaseValidationError) as exc:
        apply_event(replayed, ver)
    assert "duplicate_event_id" in codes(exc.value)
    # A fresh verification after reopen is allowed only with a new event identity.
    fresh = verification_event(event_id="E-VER-2")
    # But reopen reset execution; passing verification still needs implemented/not_required.
    with pytest.raises(ReviewCaseValidationError) as exc2:
        apply_event(replayed, fresh)
    assert "execution_incomplete_for_passing_verification" in codes(exc2.value)
