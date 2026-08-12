"""Pure proof and derived-rollup contracts for Review Case.

Non-authoritative process contour only. No filesystem I/O, codecs, CLI,
Governor, GSD, or product-domain semantics.
"""

from __future__ import annotations

from dataclasses import fields
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
    derive_finding_status,
    derive_packet_statuses,
    mark_stale,
    record_disposition,
    record_verification,
    reopen_finding,
    validate_review_policy,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
TS3 = "2026-08-12T01:00:00Z"
PATH = "doc/review/review-11-08-2026.md"
ANCHOR = "tests/test_review_case_closure.py"


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


def packet(
    findings: tuple[Finding, ...] | None = None,
    **overrides: Any,
) -> ReviewPacket:
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
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.DISPOSITION_RECORDED,
        "at": TS2,
        "actor_class": ActorClass.HUMAN,
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Human disposition",
        "disposition": disposition,
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
        "verification_result": VerificationStatus.PASSED_BOUNDED,
        "tested_revision": tested_revision,
        "evidence_anchors": evidence_anchors,
        "completed_scope": completed_scope,
        "residual_scope": residual_scope,
        "non_claims": non_claims,
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def accepted_implemented(
    finding_id: str = "RC11-F01",
    *,
    required_proof_class: ProofClass = ProofClass.IMPLEMENTATION,
) -> ReviewPacket:
    base = packet(
        findings=(
            finding(
                finding_id,
                required_proof_class=required_proof_class,
                execution_status=ExecutionStatus.IMPLEMENTED,
            ),
        )
    )
    return record_disposition(base, disposition_event(finding_id=finding_id))


def test_derived_status_is_not_persisted_on_packet_or_finding() -> None:
    assert "derived_status" not in {item.name for item in fields(Finding)}
    assert "derived_status" not in {item.name for item in fields(ReviewPacket)}
    assert DerivedStatus.OPEN.value == "open"


def test_verification_event_result_must_match_materialized_status() -> None:
    base = accepted_implemented()
    mismatched = verification_event(
        verification_result=VerificationStatus.PASSED_SMOKE,
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            mismatched,
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "verification_result_mismatch" in codes(exc.value)


def test_exact_matching_proof_closes_finding() -> None:
    base = accepted_implemented()
    verified = record_verification(
        base,
        verification_event(),
        status=VerificationStatus.PASSED_BOUNDED,
    )
    assert base.events[-1].event_type is EventType.DISPOSITION_RECORDED
    assert verified is not base
    assert verified.findings[0].verification_status is VerificationStatus.PASSED_BOUNDED
    assert derive_finding_status(verified, "RC11-F01") is DerivedStatus.CLOSED
    validate_review_policy((verified,))


def test_mismatched_proof_class_and_docs_cannot_close_implementation() -> None:
    base = accepted_implemented(required_proof_class=ProofClass.IMPLEMENTATION)
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(proof_class=ProofClass.DOCS),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "proof_class_mismatch" in codes(exc.value)
    assert base.findings[0].verification_status is VerificationStatus.UNVERIFIED


def test_verification_requires_revision_evidence_and_nonclaims() -> None:
    base = accepted_implemented()
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(
                tested_revision=None,
                evidence_anchors=(),
                non_claims=(),
            ),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert codes(exc.value) & {"invalid_event_shape", "missing_items", "invalid_git_revision"}

    with pytest.raises(ReviewCaseValidationError) as exc:
        verification_event(tested_revision="not-a-revision")
    assert "invalid_git_revision" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        verification_event(evidence_anchors=(".gsd/STATE.md",))
    assert "invalid_path" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        verification_event(evidence_anchors=["mutable"])
    assert "invalid_collection" in codes(exc.value)


def test_passed_validated_is_forbidden_in_this_contour() -> None:
    base = accepted_implemented()
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(),
            status=VerificationStatus.PASSED_VALIDATED,
        )
    assert "validated_proof_forbidden" in codes(exc.value)


def test_verification_before_disposition_or_completion_fails() -> None:
    open_packet = packet(findings=(finding(execution_status=ExecutionStatus.IMPLEMENTED),))
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            open_packet,
            verification_event(),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "accepting_disposition_required" in codes(exc.value)

    accepted = record_disposition(
        packet(findings=(finding(execution_status=ExecutionStatus.UNPLANNED),)),
        disposition_event(),
    )
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            accepted,
            verification_event(),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "execution_incomplete_for_passing_verification" in codes(exc.value)

    failed = record_verification(
        accepted,
        verification_event(
            event_id="E-FAIL",
            verification_result=VerificationStatus.FAILED,
        ),
        status=VerificationStatus.FAILED,
    )
    assert failed.findings[0].verification_status is VerificationStatus.FAILED
    assert derive_finding_status(failed, "RC11-F01") is DerivedStatus.OPEN

    ready = accepted_implemented()
    assert derive_finding_status(ready, "RC11-F01") is DerivedStatus.READY_FOR_CLOSURE


def test_residual_scope_requires_completed_scope() -> None:
    base = accepted_implemented()
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(
                completed_scope=(),
                residual_scope=("runtime still deferred",),
            ),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "partial_scope_requires_completed_scope" in codes(exc.value)


def test_residual_scope_forces_partial_never_closed() -> None:
    base = accepted_implemented()
    partial = record_verification(
        base,
        verification_event(residual_scope=("runtime still deferred",)),
        status=VerificationStatus.PASSED_BOUNDED,
    )
    assert partial.findings[0].execution_status is ExecutionStatus.PARTIALLY_IMPLEMENTED
    assert partial.findings[0].verification_status is VerificationStatus.PASSED_BOUNDED
    assert derive_finding_status(partial, "RC11-F01") is DerivedStatus.PARTIAL
    validate_review_policy((partial,))


def test_open_child_and_blocker_keep_parent_blocked() -> None:
    parent = finding("PARENT", execution_status=ExecutionStatus.IMPLEMENTED)
    child = finding("CHILD")
    base = packet(
        findings=(parent, child),
        edges=(
            ReviewEdge(
                type=RelationType.SPLITS_INTO,
                from_id="PARENT",
                to_id="CHILD",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.BLOCKED_BY,
                from_id="PARENT",
                to_id="CHILD",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    disposed = record_disposition(base, disposition_event(finding_id="PARENT"))
    verified = record_verification(
        disposed,
        verification_event(finding_id="PARENT", event_id="E-PARENT"),
        status=VerificationStatus.PASSED_BOUNDED,
    )
    assert derive_finding_status(verified, "PARENT") is DerivedStatus.BLOCKED
    statuses = dict(derive_packet_statuses(verified))
    assert statuses["PARENT"] is DerivedStatus.BLOCKED
    assert statuses["CHILD"] is DerivedStatus.OPEN
    validate_review_policy((verified,))


def test_orphan_scoped_events_and_stale_without_prior_proof_fail() -> None:
    for event_type in (
        EventType.VERIFICATION_RECORDED,
        EventType.MARKED_STALE,
        EventType.REOPENED,
    ):
        if event_type is EventType.VERIFICATION_RECORDED:
            event = verification_event(finding_id="GHOST")
        else:
            event = ReviewEvent(
                event_id=f"E-{event_type.value}",
                event_type=event_type,
                at=TS3,
                actor_class=ActorClass.HUMAN,
                finding_id="GHOST",
                source_revision=REV,
                rationale="hostile orphan",
            )
        hostile = packet(events=(event,))
        with pytest.raises(ReviewCaseValidationError) as exc:
            validate_review_policy((hostile,))
        assert "unknown_finding" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        mark_stale(
            packet(),
            ReviewEvent(
                event_id="E-STALE-NO-PROOF",
                event_type=EventType.MARKED_STALE,
                at=TS3,
                actor_class=ActorClass.HUMAN,
                finding_id="RC11-F01",
                source_revision=REV,
                rationale="cannot stale absent proof",
            ),
        )
    assert "prior_verification_required" in codes(exc.value)


def test_terminal_status_and_stale_after_proof() -> None:
    rejected = record_disposition(
        packet(),
        disposition_event(disposition=DispositionStatus.REJECTED),
    )
    assert (
        derive_finding_status(rejected, "RC11-F01") is DerivedStatus.TERMINAL_WITHOUT_IMPLEMENTATION
    )

    closed = record_verification(
        accepted_implemented(),
        verification_event(verification_result=VerificationStatus.PASSED_SMOKE),
        status=VerificationStatus.PASSED_SMOKE,
    )
    stale = mark_stale(
        closed,
        ReviewEvent(
            event_id="E-STALE",
            event_type=EventType.MARKED_STALE,
            at=TS3,
            actor_class=ActorClass.HUMAN,
            finding_id="RC11-F01",
            source_revision=REV,
            rationale="Governing authority rewrote",
        ),
    )
    assert closed.findings[0].verification_status is VerificationStatus.PASSED_SMOKE
    assert stale.findings[0].verification_status is VerificationStatus.STALE
    assert any(event.event_type is EventType.VERIFICATION_RECORDED for event in stale.events)
    assert derive_finding_status(stale, "RC11-F01") is DerivedStatus.STALE
    validate_review_policy((stale,))


def test_reopen_preserves_history_and_resets_axes() -> None:
    closed = record_verification(
        accepted_implemented(),
        verification_event(),
        status=VerificationStatus.PASSED_BOUNDED,
    )
    reopened = reopen_finding(
        closed,
        ReviewEvent(
            event_id="E-REOPEN",
            event_type=EventType.REOPENED,
            at=TS3,
            actor_class=ActorClass.HUMAN,
            finding_id="RC11-F01",
            source_revision=REV,
            rationale="Need additional residual work",
        ),
    )
    assert closed.findings[0].disposition_status is DispositionStatus.ACCEPTED_AS_GAP
    assert reopened.findings[0].disposition_status is DispositionStatus.OPEN
    assert reopened.findings[0].execution_status is ExecutionStatus.UNPLANNED
    assert reopened.findings[0].verification_status is VerificationStatus.UNVERIFIED
    assert any(event.event_type is EventType.VERIFICATION_RECORDED for event in reopened.events)
    assert reopened.events[-1].event_type is EventType.REOPENED
    assert derive_finding_status(reopened, "RC11-F01") is DerivedStatus.OPEN
    validate_review_policy((reopened,))


def test_unknown_finding_and_nonhuman_actors_fail() -> None:
    base = accepted_implemented()
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(finding_id="MISSING"),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "unknown_finding" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(actor_class=ActorClass.LLM),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "human_or_tool_actor_required" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        mark_stale(
            base,
            ReviewEvent(
                event_id="E-STALE-TOOL",
                event_type=EventType.MARKED_STALE,
                at=TS3,
                actor_class=ActorClass.TOOL,
                finding_id="RC11-F01",
                source_revision=REV,
                rationale="tool cannot mark stale",
            ),
        )
    assert "human_actor_required" in codes(exc.value)


def test_packet_status_projection_is_immutable() -> None:
    statuses = derive_packet_statuses(packet())
    assert statuses == (("RC11-F01", DerivedStatus.OPEN),)
    assert isinstance(statuses, tuple)
    assert not hasattr(statuses, "__setitem__")


def test_commands_are_pure_and_reject_relation_payload_on_verification() -> None:
    base = accepted_implemented()
    with pytest.raises(ReviewCaseValidationError) as exc:
        record_verification(
            base,
            verification_event(disposition=DispositionStatus.ACCEPTED_AS_GAP),
            status=VerificationStatus.PASSED_BOUNDED,
        )
    assert "invalid_event_shape" in codes(exc.value)
    assert base.findings[0].verification_status is VerificationStatus.UNVERIFIED
    assert len(base.events) == 1
