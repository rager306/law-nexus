"""Pure relation and disposition policy contracts for Review Case.

Non-authoritative process types only. No filesystem I/O, codecs, CLI, Governor,
GSD, or product-domain semantics. Closure/proof/execution linking is out of scope.
"""

from __future__ import annotations

from typing import Any

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
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
    assert_relation,
    record_disposition,
    record_normalization_review,
    validate_review_policy,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
PATH_11 = "doc/review/review-11-08-2026.md"
PATH_12 = "doc/review/review-12-08-2026.md"


def codes(exc: ReviewCaseValidationError) -> set[str]:
    return {item.code for item in exc.violations}


def source(path: str = PATH_11, **overrides: Any) -> ReviewSource:
    payload: dict[str, Any] = {
        "path": path,
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


def span(path: str = PATH_11, **overrides: Any) -> SourceSpan:
    payload: dict[str, Any] = {
        "path": path,
        "line_start": 10,
        "line_end": 20,
        "quote_sha256": HASH_B,
        "heading": "# Gap",
    }
    payload.update(overrides)
    return SourceSpan(**payload)


def finding(finding_id: str = "RC11-F01", path: str = PATH_11, **overrides: Any) -> Finding:
    payload: dict[str, Any] = {
        "finding_id": finding_id,
        "kind": FindingKind.GAP,
        "concern_class": ConcernClass.DESIGN,
        "reviewer_severity": ReviewerSeverity.CRITICAL,
        "summary": "Missing process contour",
        "source_spans": (span(path=path),),
        "candidate_targets": (
            CandidateTarget(surface=CandidateSurface.TSG, id="TSG-006", note="candidate only"),
        ),
        "required_proof_class": ProofClass.IMPLEMENTATION,
        "normalization_status": NormalizationStatus.SOURCE_VERIFIED,
        "disposition_status": DispositionStatus.OPEN,
        "execution_status": ExecutionStatus.UNPLANNED,
        "verification_status": VerificationStatus.UNVERIFIED,
        "non_claims": ("Not an accepted requirement",),
    }
    payload.update(overrides)
    return Finding(**payload)


def packet(
    packet_id: str = "RC-2026-08-11-001",
    path: str = PATH_11,
    findings: tuple[Finding, ...] | None = None,
    **overrides: Any,
) -> ReviewPacket:
    payload: dict[str, Any] = {
        "packet_id": packet_id,
        "source": source(path=path),
        "normalization": normalization(),
        "non_claims": ("Non-authoritative review projection",),
        "findings": findings if findings is not None else (finding(path=path),),
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


def test_candidate_multi_packet_relations_validate() -> None:
    p11 = packet(
        packet_id="RC-11",
        path=PATH_11,
        findings=(finding("RC11-F04", path=PATH_11), finding("RC11-F04a", path=PATH_11)),
        edges=(
            ReviewEdge(
                type=RelationType.SPLITS_INTO,
                from_id="RC11-F04",
                to_id="RC11-F04a",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.MAPS_TO,
                from_id="RC11-F04",
                to_id="TSG-006",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    p12 = packet(
        packet_id="RC-12",
        path=PATH_12,
        findings=(finding("RC12-F05", path=PATH_12),),
        edges=(
            ReviewEdge(
                type=RelationType.REASSESSES,
                from_id="RC12-F05",
                to_id="RC11-F04",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.REFINES,
                from_id="RC12-F05",
                to_id="RC11-F04a",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    validate_review_policy((p11, p12))


def test_maps_to_accepted_fails() -> None:
    p = packet(
        edges=(
            ReviewEdge(
                type=RelationType.MAPS_TO,
                from_id="RC11-F01",
                to_id="TSG-006",
                status=RelationStatus.ACCEPTED,
            ),
        )
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "maps_to_must_remain_candidate" in codes(exc.value)


def test_non_open_disposition_requires_matching_human_event() -> None:
    p = packet(
        findings=(finding(disposition_status=DispositionStatus.ACCEPTED_AS_GAP),),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "disposition_event_required" in codes(exc.value)


def test_human_reviewed_requires_human_event() -> None:
    p = packet(
        normalization=normalization(status=NormalizationStatus.HUMAN_REVIEWED),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "normalization_review_event_required" in codes(exc.value)


def test_non_candidate_relation_requires_human_edge_event() -> None:
    p = packet(
        findings=(finding("RC11-F01"), finding("RC11-F02")),
        edges=(
            ReviewEdge(
                type=RelationType.REFINES,
                from_id="RC11-F02",
                to_id="RC11-F01",
                status=RelationStatus.ACCEPTED,
            ),
        ),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "edge_event_required" in codes(exc.value)


def test_external_reference_relations_require_finding_source() -> None:
    for relation in (
        RelationType.PROMOTED_TO,
        RelationType.IMPLEMENTED_BY,
        RelationType.VERIFIED_BY,
    ):
        p = packet(
            edges=(
                ReviewEdge(
                    type=relation,
                    from_id="MISSING",
                    to_id="EXTERNAL-1",
                    status=RelationStatus.CANDIDATE,
                ),
            )
        )
        with pytest.raises(ReviewCaseValidationError) as exc:
            validate_review_policy((p,))
        assert "missing_relation_endpoint" in codes(exc.value)


def test_promoted_to_requires_human_accepting_disposition_and_event() -> None:
    edge = ReviewEdge(
        type=RelationType.PROMOTED_TO,
        from_id="RC11-F01",
        to_id="TSG-006",
        status=RelationStatus.CANDIDATE,
    )
    p = packet(edges=(edge,))
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "promoted_to_requires_human_accepting_disposition" in codes(exc.value)


def test_tool_cannot_record_accepting_disposition_or_promotion() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(
            packet(),
            disposition_event(actor_class=ActorClass.TOOL),
        )
    assert "human_actor_required" in codes(exc.value)

    human_packet = record_disposition(packet(), disposition_event())
    edge = ReviewEdge(
        type=RelationType.PROMOTED_TO,
        from_id="RC11-F01",
        to_id="TSG-006",
        status=RelationStatus.ACCEPTED,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        assert_relation(human_packet, edge, edge_event(edge, actor_class=ActorClass.LLM))
    assert "human_actor_required" in codes(exc.value)


def test_invalid_packet_and_duplicate_packet_identity_fail_structured() -> None:
    invalid_packet: Any = "not-a-packet"
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((invalid_packet,))
    assert "invalid_type" in codes(exc.value)

    duplicate_a = packet(packet_id="DUPLICATE")
    duplicate_b = packet(packet_id="DUPLICATE", path=PATH_12)
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((duplicate_a, duplicate_b))
    assert "duplicate_packet_id" in codes(exc.value)


def test_cross_packet_duplicate_finding_event_and_cycle_fail() -> None:
    duplicate_finding_a = packet(packet_id="P-A", findings=(finding("SHARED"),))
    duplicate_finding_b = packet(
        packet_id="P-B",
        path=PATH_12,
        findings=(finding("SHARED", path=PATH_12),),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((duplicate_finding_a, duplicate_finding_b))
    assert "duplicate_global_finding_id" in codes(exc.value)

    shared_event = ReviewEvent(
        event_id="GLOBAL-EVENT",
        event_type=EventType.PACKET_REGISTERED,
        at=TS2,
        actor_class=ActorClass.HUMAN,
    )
    duplicate_event_a = packet(packet_id="P-A", events=(shared_event,))
    duplicate_event_b = packet(packet_id="P-B", path=PATH_12, events=(shared_event,))
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((duplicate_event_a, duplicate_event_b))
    assert "duplicate_global_event_id" in codes(exc.value)

    cycle_a = packet(
        packet_id="P-A",
        findings=(finding("A"),),
        edges=(
            ReviewEdge(
                type=RelationType.DEPENDS_ON,
                from_id="A",
                to_id="B",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    cycle_b = packet(
        packet_id="P-B",
        path=PATH_12,
        findings=(finding("B", path=PATH_12),),
        edges=(
            ReviewEdge(
                type=RelationType.BLOCKED_BY,
                from_id="B",
                to_id="A",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((cycle_a, cycle_b))
    assert "relation_cycle" in codes(exc.value)


def test_consequential_event_shape_requires_revision_rationale_and_closed_fields() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(
            packet(),
            disposition_event(source_revision=None, rationale=None),
        )
    assert "invalid_event_shape" in codes(exc.value)

    mixed_disposition = disposition_event(
        edge_type=RelationType.REFINES,
        from_id="RC11-F01",
        to_id="RC11-F02",
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(packet(), mixed_disposition)
    assert "invalid_event_shape" in codes(exc.value)

    edge = ReviewEdge(
        type=RelationType.REFINES,
        from_id="RC11-F02",
        to_id="RC11-F01",
        status=RelationStatus.ACCEPTED,
    )
    base = packet(findings=(finding("RC11-F01"), finding("RC11-F02")))
    with pytest.raises(ReviewCaseValidationError) as exc:
        assert_relation(base, edge, edge_event(edge, source_revision=None, rationale=None))
    assert "invalid_event_shape" in codes(exc.value)


def test_missing_endpoint_self_relation_cycle_and_duplicate_event_fail() -> None:
    missing = packet(
        edges=(
            ReviewEdge(
                type=RelationType.REFINES,
                from_id="RC11-F01",
                to_id="RC11-MISSING",
                status=RelationStatus.CANDIDATE,
            ),
        )
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((missing,))
    assert "missing_relation_endpoint" in codes(exc.value)

    self_edge = packet(
        edges=(
            ReviewEdge(
                type=RelationType.DEPENDS_ON,
                from_id="RC11-F01",
                to_id="RC11-F01",
                status=RelationStatus.CANDIDATE,
            ),
        )
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((self_edge,))
    assert "self_relation" in codes(exc.value)

    cycle = packet(
        findings=(finding("A"), finding("B")),
        edges=(
            ReviewEdge(
                type=RelationType.DEPENDS_ON,
                from_id="A",
                to_id="B",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.BLOCKED_BY,
                from_id="B",
                to_id="A",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((cycle,))
    assert "relation_cycle" in codes(exc.value)

    original = packet()
    event = disposition_event(event_id="DUP")
    once = record_disposition(original, event)
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(once, event)
    assert "duplicate_event_id" in codes(exc.value)


def test_orphan_disposition_event_fails_validation() -> None:
    orphan = packet(
        events=(disposition_event(finding_id="GHOST"),),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((orphan,))
    assert "unknown_finding" in codes(exc.value)


def test_terminal_disposition_command_is_atomic_and_preserves_existing_work() -> None:
    rejected = record_disposition(
        packet(),
        disposition_event(disposition=DispositionStatus.REJECTED),
    )
    assert rejected.findings[0].execution_status is ExecutionStatus.NOT_REQUIRED
    validate_review_policy((rejected,))

    started = packet(
        findings=(finding(execution_status=ExecutionStatus.IN_PROGRESS),),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(
            started,
            disposition_event(disposition=DispositionStatus.REJECTED),
        )
    assert "terminal_execution_transition_requires_resolution" in codes(exc.value)
    assert started.findings[0].execution_status is ExecutionStatus.IN_PROGRESS
    assert started.events == ()


def test_status_event_mismatch_fails_validation() -> None:
    p = packet(
        findings=(finding(disposition_status=DispositionStatus.REJECTED),),
        events=(
            disposition_event(
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
            ),
        ),
    )
    # terminal disposition without matching execution not_required may also fire;
    # require exact disposition match failure either way.
    with pytest.raises(ReviewCaseValidationError) as exc:
        validate_review_policy((p,))
    assert "disposition_event_required" in codes(exc.value)


def test_record_disposition_is_pure_and_updates_finding() -> None:
    original = packet()
    event = disposition_event()
    updated = record_disposition(original, event)
    assert original.findings[0].disposition_status is DispositionStatus.OPEN
    assert original.events == ()
    assert updated is not original
    assert updated.findings[0].disposition_status is DispositionStatus.ACCEPTED_AS_GAP
    assert updated.events == (event,)
    validate_review_policy((updated,))


def test_human_disposition_then_promotion_flow() -> None:
    base = packet()
    disposed = record_disposition(base, disposition_event())
    edge = ReviewEdge(
        type=RelationType.PROMOTED_TO,
        from_id="RC11-F01",
        to_id="TSG-006",
        status=RelationStatus.ACCEPTED,
    )
    promoted = assert_relation(disposed, edge, edge_event(edge))
    assert base.edges == ()
    assert disposed.edges == ()
    assert promoted.edges == (edge,)
    assert promoted.events[-1].event_type is EventType.EDGE_ASSERTED
    validate_review_policy((promoted,))


def test_normalization_review_requires_revision_and_rationale() -> None:
    event = ReviewEvent(
        event_id="E-NORM-BAD",
        event_type=EventType.NORMALIZATION_REVIEWED,
        at=TS2,
        actor_class=ActorClass.HUMAN,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_normalization_review(packet(), event)
    assert "invalid_event_shape" in codes(exc.value)


def test_record_normalization_review_is_pure() -> None:
    original = packet()
    event = ReviewEvent(
        event_id="E-NORM",
        event_type=EventType.NORMALIZATION_REVIEWED,
        at=TS2,
        actor_class=ActorClass.HUMAN,
        source_revision=REV,
        rationale="Reviewed extraction",
    )
    updated = record_normalization_review(original, event)
    assert original.normalization.status is NormalizationStatus.SOURCE_VERIFIED
    assert updated.normalization.status is NormalizationStatus.HUMAN_REVIEWED
    assert updated.events == (event,)
    validate_review_policy((updated,))


def test_assert_relation_rejects_maps_to_accepted_command() -> None:
    edge = ReviewEdge(
        type=RelationType.MAPS_TO,
        from_id="RC11-F01",
        to_id="TSG-006",
        status=RelationStatus.ACCEPTED,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        assert_relation(packet(), edge, edge_event(edge))
    assert "maps_to_must_remain_candidate" in codes(exc.value)


def test_assert_relation_requires_matching_event_payload() -> None:
    edge = ReviewEdge(
        type=RelationType.REFINES,
        from_id="RC11-F02",
        to_id="RC11-F01",
        status=RelationStatus.ACCEPTED,
    )
    base = packet(findings=(finding("RC11-F01"), finding("RC11-F02")))
    mismatched = edge_event(
        edge,
        edge_type=RelationType.DUPLICATES,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        assert_relation(base, edge, mismatched)
    assert "edge_event_mismatch" in codes(exc.value)


def test_unknown_finding_disposition_fails() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_disposition(packet(), disposition_event(finding_id="MISSING"))
    assert "unknown_finding" in codes(exc.value)
