"""Pure multi-axis Review Case FSM residual projection tests.

No filesystem I/O except dogfood against tracked RC11 packet store when present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    ConcernClass,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    Finding,
    FindingKind,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    OperatorStage,
    ProofClass,
    RelationStatus,
    RelationType,
    ResidualClass,
    ReviewEdge,
    ReviewerSeverity,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
    build_finding_fsm_snapshot,
    build_review_fsm_inventory,
    classify_residual_class,
    derive_finding_status,
    next_admissible_events,
    record_disposition,
    record_execution_link,
)

HASH = "a" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
PATH = "doc/review/review-11-08-2026.md"
ROOT = Path(__file__).resolve().parents[1]


def source() -> ReviewSource:
    return ReviewSource(
        path=PATH,
        content_sha256=HASH,
        reviewed_git_revision=REV,
        received_at=TS,
        source_kind=SourceKind.HUMAN_EXTERNAL,
    )


def normalization() -> NormalizationRecord:
    return NormalizationRecord(
        status=NormalizationStatus.SOURCE_VERIFIED,
        method=NormalizationMethod.MANUAL,
        source_hash=HASH,
    )


def span() -> SourceSpan:
    return SourceSpan(
        path=PATH,
        line_start=1,
        line_end=1,
        quote_sha256=HASH,
    )


def finding(**overrides: Any) -> Finding:
    payload: dict[str, Any] = {
        "finding_id": "F-1",
        "kind": FindingKind.GAP,
        "concern_class": ConcernClass.PROCESS,
        "reviewer_severity": ReviewerSeverity.HIGH,
        "summary": "process gap summary",
        "source_spans": (span(),),
        "candidate_targets": (),
        "required_proof_class": ProofClass.PROCESS,
        "normalization_status": NormalizationStatus.SOURCE_VERIFIED,
        "disposition_status": DispositionStatus.OPEN,
        "execution_status": ExecutionStatus.UNPLANNED,
        "verification_status": VerificationStatus.UNVERIFIED,
        "non_claims": ("non-authoritative finding",),
    }
    payload.update(overrides)
    return Finding(**payload)


def packet(
    *, findings: tuple[Finding, ...] | None = None, edges: tuple[ReviewEdge, ...] = ()
) -> ReviewPacket:
    return ReviewPacket(
        packet_id="RC-FSM-001",
        source=source(),
        normalization=normalization(),
        non_claims=("Non-authoritative review projection",),
        findings=findings or (finding(),),
        edges=edges,
        events=(),
    )


def test_open_finding_awaits_disposition_and_enables_disposition_event() -> None:
    snap = build_finding_fsm_snapshot(packet(), "F-1")
    assert snap.residual_class == ResidualClass.AWAITING_DISPOSITION.value
    assert snap.operator_stage == OperatorStage.S1_NORMALIZED.value
    assert EventType.DISPOSITION_RECORDED.value in snap.next_admissible_events
    assert any("disposition_recorded" in item for item in snap.missing_for_next)


def test_already_satisfied_is_terminal_without_implementation() -> None:
    base = packet(findings=(finding(disposition_status=DispositionStatus.OPEN),))
    event = ReviewEvent(
        event_id="EVT-1",
        event_type=EventType.DISPOSITION_RECORDED,
        at=TS,
        actor_class=ActorClass.HUMAN,
        actor_id="human-1",
        finding_id="F-1",
        source_revision=REV,
        rationale="docs already present",
        disposition=DispositionStatus.ALREADY_SATISFIED,
    )
    material = record_disposition(base, event)
    snap = build_finding_fsm_snapshot(material, "F-1")
    assert snap.derived_status == "terminal_without_implementation"
    assert snap.residual_class == ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION.value
    assert snap.operator_stage == OperatorStage.S6_TERMINAL_OR_CLOSED.value
    assert snap.next_admissible_events == (EventType.REOPENED.value,)


def _with_disposition(
    base: ReviewPacket,
    *,
    finding_id: str,
    disposition: DispositionStatus,
    event_id: str,
) -> ReviewPacket:
    event = ReviewEvent(
        event_id=event_id,
        event_type=EventType.DISPOSITION_RECORDED,
        at=TS,
        actor_class=ActorClass.HUMAN,
        actor_id="human-1",
        finding_id=finding_id,
        source_revision=REV,
        rationale=f"human disposition {disposition.value}",
        disposition=disposition,
    )
    return record_disposition(base, event)


def test_process_defect_unplanned_is_process_closeable() -> None:
    base = packet(
        findings=(
            finding(
                required_proof_class=ProofClass.PROCESS,
            ),
        )
    )
    material = _with_disposition(
        base,
        finding_id="F-1",
        disposition=DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
        event_id="EVT-PROC-1",
    )
    snap = build_finding_fsm_snapshot(material, "F-1")
    assert snap.residual_class == ResidualClass.PROCESS_CLOSEABLE.value
    assert snap.operator_stage == OperatorStage.S2_DISPOSITIONED.value
    assert EventType.EXECUTION_LINKED.value in snap.next_admissible_events
    assert any("execution_linked" in item for item in snap.missing_for_next)


def test_accepted_gap_design_is_product_open() -> None:
    base = packet(
        findings=(
            finding(
                finding_id="F-D",
                required_proof_class=ProofClass.DESIGN,
                concern_class=ConcernClass.DESIGN,
                summary="design gap",
            ),
        )
    )
    material = _with_disposition(
        base,
        finding_id="F-D",
        disposition=DispositionStatus.ACCEPTED_AS_GAP,
        event_id="EVT-DES-1",
    )
    snap = build_finding_fsm_snapshot(material, "F-D")
    assert snap.residual_class == ResidualClass.PRODUCT_OPEN.value
    assert EventType.EXECUTION_LINKED.value in snap.next_admissible_events


def test_deferred_is_parked() -> None:
    base = packet()
    material = _with_disposition(
        base,
        finding_id="F-1",
        disposition=DispositionStatus.DEFERRED,
        event_id="EVT-DEF-1",
    )
    snap = build_finding_fsm_snapshot(material, "F-1")
    assert snap.residual_class == ResidualClass.DEFERRED_PARKED.value
    assert snap.operator_stage == OperatorStage.S6_TERMINAL_OR_CLOSED.value


def test_parent_split_children_blocked_graph() -> None:
    parent = finding(
        finding_id="F-P",
        required_proof_class=ProofClass.IMPLEMENTATION,
        concern_class=ConcernClass.IMPLEMENTATION,
        summary="parent gap",
    )
    child_a = finding(
        finding_id="F-A",
        required_proof_class=ProofClass.DESIGN,
        concern_class=ConcernClass.DESIGN,
        summary="child a",
    )
    child_b = finding(
        finding_id="F-B",
        required_proof_class=ProofClass.IMPLEMENTATION,
        concern_class=ConcernClass.IMPLEMENTATION,
        summary="child b",
    )
    edges = (
        ReviewEdge(
            type=RelationType.SPLITS_INTO,
            from_id="F-P",
            to_id="F-A",
            status=RelationStatus.CANDIDATE,
            note="split a",
        ),
        ReviewEdge(
            type=RelationType.SPLITS_INTO,
            from_id="F-P",
            to_id="F-B",
            status=RelationStatus.CANDIDATE,
            note="split b",
        ),
        ReviewEdge(
            type=RelationType.BLOCKED_BY,
            from_id="F-A",
            to_id="F-P",
            status=RelationStatus.CANDIDATE,
            note="parent",
        ),
        ReviewEdge(
            type=RelationType.BLOCKED_BY,
            from_id="F-B",
            to_id="F-P",
            status=RelationStatus.CANDIDATE,
            note="parent",
        ),
    )
    material = packet(findings=(parent, child_a, child_b), edges=edges)
    for finding_id, event_id in (
        ("F-P", "EVT-P"),
        ("F-A", "EVT-A"),
        ("F-B", "EVT-B"),
    ):
        material = _with_disposition(
            material,
            finding_id=finding_id,
            disposition=DispositionStatus.ACCEPTED_AS_GAP,
            event_id=event_id,
        )
    parent_snap = build_finding_fsm_snapshot(material, "F-P")
    child_snap = build_finding_fsm_snapshot(material, "F-A")
    assert parent_snap.residual_class == ResidualClass.BLOCKED_GRAPH.value
    assert child_snap.residual_class == ResidualClass.BLOCKED_GRAPH.value
    assert "F-A" in parent_snap.graph.open_children
    assert "F-P" in child_snap.graph.active_blockers
    assert derive_finding_status(material, "F-P").value == "blocked"


def test_execution_link_advances_stage_toward_verification() -> None:
    base = packet(
        findings=(
            finding(
                required_proof_class=ProofClass.PROCESS,
            ),
        )
    )
    material = _with_disposition(
        base,
        finding_id="F-1",
        disposition=DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
        event_id="EVT-PROC-2",
    )
    event = ReviewEvent(
        event_id="EVT-EXEC-1",
        event_type=EventType.EXECUTION_LINKED,
        at=TS,
        actor_class=ActorClass.HUMAN,
        actor_id="human-1",
        finding_id="F-1",
        source_revision=REV,
        rationale="link process work",
        to_id="opaque:gsd:M166",
        completed_scope=(ExecutionStatus.IMPLEMENTED.value,),
        non_claims=("Opaque execution reference only",),
    )
    material = record_execution_link(material, event)
    snap = build_finding_fsm_snapshot(material, "F-1")
    assert snap.execution_status == ExecutionStatus.IMPLEMENTED.value
    assert snap.operator_stage == OperatorStage.S5_VERIFICATION.value
    assert EventType.VERIFICATION_RECORDED.value in snap.next_admissible_events


def test_inventory_rollup_counts_are_deterministic() -> None:
    open_f = finding(finding_id="F-OPEN")
    deferred_base = finding(
        finding_id="F-DEF",
        summary="deferred item",
    )
    material = packet(findings=(open_f, deferred_base))
    material = _with_disposition(
        material,
        finding_id="F-DEF",
        disposition=DispositionStatus.DEFERRED,
        event_id="EVT-DEF-2",
    )
    inv = build_review_fsm_inventory((material,))
    assert inv.schema_version == "review-case-fsm-inventory/v1"
    assert inv.authoritative is False
    assert inv.packet_count == 1
    assert inv.finding_count == 2
    residual_map = dict(inv.residual_counts)
    assert residual_map[ResidualClass.AWAITING_DISPOSITION.value] == 1
    assert residual_map[ResidualClass.DEFERRED_PARKED.value] == 1


def test_classify_residual_helper_matches_snapshot() -> None:
    base = packet(findings=(finding(),))
    material = _with_disposition(
        base,
        finding_id="F-1",
        disposition=DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
        event_id="EVT-PROC-3",
    )
    snap = build_finding_fsm_snapshot(material, "F-1")
    finding_obj = material.findings[0]
    derived = derive_finding_status(material, "F-1")
    residual = classify_residual_class(
        finding=finding_obj,
        derived=derived,
        graph=snap.graph,
    )
    assert residual.value == snap.residual_class
    enabled = next_admissible_events(
        finding=finding_obj,
        residual=residual,
        graph=snap.graph,
    )
    assert enabled == snap.next_admissible_events


@pytest.mark.parametrize(
    ("packet_id", "expected"),
    [
        (
            "RC-2026-08-11-001",
            {
                "RC11-F01": ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION.value,
                "RC11-F03": ResidualClass.PROCESS_CLOSEABLE.value,
                "RC11-F04": ResidualClass.BLOCKED_GRAPH.value,
                "RC11-F04a": ResidualClass.BLOCKED_GRAPH.value,
                "RC11-F04b": ResidualClass.BLOCKED_GRAPH.value,
                "RC11-F13": ResidualClass.DEFERRED_PARKED.value,
            },
        ),
    ],
)
def test_dogfood_rc11_live_packet_residual_board(
    packet_id: str,
    expected: dict[str, str],
) -> None:
    from law_nexus_harness.review_case.adapters.filesystem import FilesystemReviewPacketStore
    from law_nexus_harness.review_case.adapters.filesystem_ledger import FilesystemEventLedger
    from law_nexus_harness.review_case.application import (
        materialize_review_packet,
        review_case_inventory,
    )

    packet_path = ROOT / "prd/architecture/review-cases/packets" / f"{packet_id}.json"
    if not packet_path.is_file():
        pytest.skip("RC11 packet not present in workspace")

    store = FilesystemReviewPacketStore(ROOT)
    ledger = FilesystemEventLedger(ROOT)
    material = materialize_review_packet(store, ledger, packet_id)
    inv = review_case_inventory(store, packet_id=packet_id, ledger=ledger)
    assert inv.packet_count == 1
    assert inv.packets[0].packet_id == packet_id
    by_id = {item.finding_id: item for item in inv.packets[0].findings}
    for finding_id, residual in expected.items():
        assert finding_id in by_id, finding_id
        assert by_id[finding_id].residual_class == residual, finding_id
    # Product open residual remains for design/impl gaps without graph block.
    assert by_id["RC11-F06"].residual_class == ResidualClass.PRODUCT_OPEN.value
    assert by_id["RC11-F09"].residual_class == ResidualClass.PRODUCT_OPEN.value
    # Continuity: F03 next step is execution link, not fake close.
    assert EventType.EXECUTION_LINKED.value in by_id["RC11-F03"].next_admissible_events
    assert material.packet_id == packet_id
