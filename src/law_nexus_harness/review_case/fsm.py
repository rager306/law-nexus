"""Event-sourced multi-axis Review Case FSM projection.

Pure read-only automaton over materialized packet state (base + ledger replay).
Does not append events, promote authority, create GSD work, or write derived
status into packets.

Architecture (onion):

```text
domain values  →  policy.apply_event / derive_finding_status
               →  fsm residual + next_admissible projection (this module)
               →  application inventory use case
               →  adapters / CLI
```

The writable lifecycle remains append-only ledger events. This module only
classifies residual stage continuity and enabled transitions (AST-like fold of
events → axes → residual/next).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from law_nexus_harness.review_case.domain import (
    DerivedStatus,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    Finding,
    NormalizationStatus,
    ProofClass,
    RelationType,
    ReviewEvent,
    ReviewPacket,
    VerificationStatus,
)
from law_nexus_harness.review_case.policy import derive_finding_status

FSM_SCHEMA_VERSION = "review-case-fsm-inventory/v1"

_ACCEPTING_DISPOSITIONS = frozenset(
    {
        DispositionStatus.ACCEPTED_AS_GAP,
        DispositionStatus.ACCEPTED_AS_REQUIREMENT_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_DECISION_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
    }
)
_TERMINAL_WITHOUT_WORK = frozenset(
    {
        DispositionStatus.REJECTED,
        DispositionStatus.DUPLICATE,
        DispositionStatus.SUPERSEDED,
        DispositionStatus.NOT_APPLICABLE,
        DispositionStatus.ALREADY_SATISFIED,
    }
)
_AWAITING_DISPOSITION = frozenset(
    {
        DispositionStatus.OPEN,
        DispositionStatus.NEEDS_DISCUSSION,
        DispositionStatus.NEEDS_RESEARCH,
    }
)
_COMPLETE_EXECUTION = frozenset(
    {
        ExecutionStatus.IMPLEMENTED,
        ExecutionStatus.NOT_REQUIRED,
    }
)
_PASSING_VERIFICATION = frozenset(
    {
        VerificationStatus.PASSED_BOUNDED,
        VerificationStatus.PASSED_SMOKE,
    }
)


class ResidualClass(StrEnum):
    """Deterministic residual taxonomy for operator continuity."""

    TERMINAL_WITHOUT_IMPLEMENTATION = "terminal_without_implementation"
    DEFERRED_PARKED = "deferred_parked"
    STALE = "stale"
    CLOSED = "closed"
    READY_FOR_CLOSURE = "ready_for_closure"
    BLOCKED_GRAPH = "blocked_graph"
    PARTIAL = "partial"
    PROCESS_CLOSEABLE = "process_closeable"
    PRODUCT_OPEN = "product_open"
    AWAITING_DISPOSITION = "awaiting_disposition"
    OPEN = "open"


class OperatorStage(StrEnum):
    """Operator-facing stage view over axes (not a writable packet field)."""

    S0_SOURCE_SEALED = "S0_source_sealed"
    S1_NORMALIZED = "S1_normalized"
    S2_DISPOSITIONED = "S2_dispositioned"
    S3_EXECUTION_LINKED = "S3_execution_linked"
    S4_EXTERNAL_WORK = "S4_external_work"
    S5_VERIFICATION = "S5_verification"
    S6_TERMINAL_OR_CLOSED = "S6_terminal_or_closed"


@dataclass(frozen=True, slots=True)
class LastEventView:
    event_id: str
    event_type: str
    at: str
    actor_class: str
    actor_id: str | None
    rationale: str | None


@dataclass(frozen=True, slots=True)
class GraphContextView:
    blocked_by: tuple[str, ...]
    splits_into: tuple[str, ...]
    open_children: tuple[str, ...]
    active_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FindingFsmSnapshot:
    """One finding's multi-axis FSM projection."""

    finding_id: str
    summary: str
    kind: str
    concern_class: str
    required_proof_class: str
    normalization_status: str
    disposition_status: str
    execution_status: str
    verification_status: str
    derived_status: str
    residual_class: str
    operator_stage: str
    next_admissible_events: tuple[str, ...]
    missing_for_next: tuple[str, ...]
    graph: GraphContextView
    last_event: LastEventView | None
    non_claims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PacketFsmInventory:
    packet_id: str
    source_path: str
    reviewed_git_revision: str
    content_sha256: str
    normalization_status: str
    finding_count: int
    residual_counts: tuple[tuple[str, int], ...]
    stage_counts: tuple[tuple[str, int], ...]
    findings: tuple[FindingFsmSnapshot, ...]
    open_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewFsmInventory:
    schema_version: str
    authoritative: bool
    authority_required: bool
    packet_count: int
    finding_count: int
    residual_counts: tuple[tuple[str, int], ...]
    stage_counts: tuple[tuple[str, int], ...]
    packets: tuple[PacketFsmInventory, ...]
    open_blockers: tuple[tuple[str, str], ...]
    non_claims: tuple[str, ...]


_DEFAULT_NON_CLAIMS = (
    "Non-authoritative review FSM projection",
    "Derived residual/next_admissible are read-only and not authority",
    "Does not promote requirements, ADRs, roadmap, or lifecycle",
    "Does not create GSD milestones or product claims",
    "Enabled transitions require human-gated ledger events outside this view",
)


def _latest_finding_event(packet: ReviewPacket, finding_id: str) -> ReviewEvent | None:
    latest: ReviewEvent | None = None
    for event in packet.events:
        if event.finding_id == finding_id:
            latest = event
    return latest


def _graph_context(packet: ReviewPacket, finding_id: str) -> GraphContextView:
    findings = {item.finding_id: item for item in packet.findings}
    blocked_by: list[str] = []
    splits_into: list[str] = []
    open_children: list[str] = []
    active_blockers: list[str] = []

    def _is_split_parent(parent_id: str, child_id: str) -> bool:
        return any(
            edge.from_id == parent_id
            and edge.to_id == child_id
            and edge.type is RelationType.SPLITS_INTO
            for edge in packet.edges
        )

    for edge in packet.edges:
        if edge.from_id != finding_id:
            continue
        if edge.type is RelationType.BLOCKED_BY:
            blocked_by.append(edge.to_id)
            blocker = findings.get(edge.to_id)
            if blocker is None:
                active_blockers.append(edge.to_id)
                continue
            if blocker.disposition_status in _TERMINAL_WITHOUT_WORK:
                continue
            # Mirror policy: split-parent blocked_by is informational for children.
            if _is_split_parent(edge.to_id, finding_id):
                continue
            active_blockers.append(edge.to_id)
        if edge.type is RelationType.SPLITS_INTO:
            splits_into.append(edge.to_id)
            child = findings.get(edge.to_id)
            if child is None:
                open_children.append(edge.to_id)
                continue
            if child.disposition_status in _TERMINAL_WITHOUT_WORK:
                continue
            if (
                child.execution_status is ExecutionStatus.IMPLEMENTED
                and child.verification_status in _PASSING_VERIFICATION
            ):
                continue
            open_children.append(edge.to_id)

    return GraphContextView(
        blocked_by=tuple(blocked_by),
        splits_into=tuple(splits_into),
        open_children=tuple(open_children),
        active_blockers=tuple(active_blockers),
    )


def classify_residual_class(
    *,
    finding: Finding,
    derived: DerivedStatus,
    graph: GraphContextView,
) -> ResidualClass:
    """Pure residual classifier (observer automaton over axes + graph)."""

    if derived is DerivedStatus.TERMINAL_WITHOUT_IMPLEMENTATION:
        return ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION
    if finding.disposition_status is DispositionStatus.DEFERRED:
        return ResidualClass.DEFERRED_PARKED
    if derived is DerivedStatus.STALE:
        return ResidualClass.STALE
    if derived is DerivedStatus.CLOSED:
        return ResidualClass.CLOSED
    if derived is DerivedStatus.READY_FOR_CLOSURE:
        return ResidualClass.READY_FOR_CLOSURE
    if derived is DerivedStatus.BLOCKED or graph.active_blockers or graph.open_children:
        return ResidualClass.BLOCKED_GRAPH
    if derived is DerivedStatus.PARTIAL:
        return ResidualClass.PARTIAL
    if finding.disposition_status in _AWAITING_DISPOSITION:
        return ResidualClass.AWAITING_DISPOSITION
    if finding.disposition_status in _ACCEPTING_DISPOSITIONS:
        process_like = (
            finding.disposition_status is DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT
            or finding.required_proof_class is ProofClass.PROCESS
        )
        if process_like and finding.execution_status not in _COMPLETE_EXECUTION:
            return ResidualClass.PROCESS_CLOSEABLE
        return ResidualClass.PRODUCT_OPEN
    return ResidualClass.OPEN


def classify_operator_stage(
    *,
    finding: Finding,
    residual: ResidualClass,
) -> OperatorStage:
    if residual in {
        ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION,
        ResidualClass.DEFERRED_PARKED,
        ResidualClass.CLOSED,
    }:
        return OperatorStage.S6_TERMINAL_OR_CLOSED
    if residual is ResidualClass.STALE:
        return OperatorStage.S1_NORMALIZED
    if residual is ResidualClass.AWAITING_DISPOSITION:
        return OperatorStage.S1_NORMALIZED
    if residual is ResidualClass.READY_FOR_CLOSURE:
        return OperatorStage.S5_VERIFICATION
    if residual is ResidualClass.PARTIAL:
        return OperatorStage.S5_VERIFICATION
    if finding.disposition_status in _AWAITING_DISPOSITION:
        return OperatorStage.S1_NORMALIZED
    if finding.execution_status is ExecutionStatus.UNPLANNED:
        return OperatorStage.S2_DISPOSITIONED
    if finding.execution_status in {
        ExecutionStatus.PLANNED,
        ExecutionStatus.IN_PROGRESS,
        ExecutionStatus.BLOCKED,
    }:
        return OperatorStage.S3_EXECUTION_LINKED
    if finding.execution_status is ExecutionStatus.PARTIALLY_IMPLEMENTED:
        return OperatorStage.S5_VERIFICATION
    if finding.execution_status in _COMPLETE_EXECUTION:
        if finding.verification_status in _PASSING_VERIFICATION:
            return OperatorStage.S6_TERMINAL_OR_CLOSED
        return OperatorStage.S5_VERIFICATION
    return OperatorStage.S2_DISPOSITIONED


def next_admissible_events(
    *,
    finding: Finding,
    residual: ResidualClass,
    graph: GraphContextView,
) -> tuple[str, ...]:
    """Enabled ledger event types for progressive continuity (not auto-fire)."""

    enabled: list[str] = []

    if residual is ResidualClass.STALE:
        return (EventType.MARKED_STALE.value,)

    if residual in {
        ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION,
        ResidualClass.CLOSED,
    }:
        return (EventType.REOPENED.value,)

    if residual is ResidualClass.DEFERRED_PARKED:
        return (EventType.REOPENED.value, EventType.DISPOSITION_RECORDED.value)

    if residual is ResidualClass.AWAITING_DISPOSITION:
        enabled.append(EventType.DISPOSITION_RECORDED.value)
        if finding.normalization_status in {
            NormalizationStatus.DRAFT_EXTRACTED,
            NormalizationStatus.SOURCE_VERIFIED,
        }:
            enabled.append(EventType.NORMALIZATION_REVIEWED.value)
        return tuple(dict.fromkeys(enabled))

    # Accepting / residual product-process paths.
    if finding.disposition_status in _ACCEPTING_DISPOSITIONS:
        if residual is ResidualClass.BLOCKED_GRAPH:
            # Parent with open children: graph first. Child-only residual can still
            # advance execution when active_blockers is empty after split exemption.
            enabled.append(EventType.EDGE_ASSERTED.value)
            if not graph.open_children and not graph.active_blockers:
                if finding.execution_status is ExecutionStatus.UNPLANNED:
                    enabled.append(EventType.EXECUTION_LINKED.value)
                elif finding.execution_status in _COMPLETE_EXECUTION:
                    if finding.verification_status not in _PASSING_VERIFICATION:
                        enabled.append(EventType.VERIFICATION_RECORDED.value)
            enabled.append(EventType.REOPENED.value)
            return tuple(dict.fromkeys(enabled))

        if finding.execution_status is ExecutionStatus.UNPLANNED:
            enabled.append(EventType.EXECUTION_LINKED.value)
        elif finding.execution_status in {
            ExecutionStatus.PLANNED,
            ExecutionStatus.IN_PROGRESS,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.PARTIALLY_IMPLEMENTED,
        }:
            enabled.append(EventType.EXECUTION_LINKED.value)
            if finding.execution_status in _COMPLETE_EXECUTION or finding.execution_status in {
                ExecutionStatus.PARTIALLY_IMPLEMENTED,
                ExecutionStatus.IN_PROGRESS,
                ExecutionStatus.PLANNED,
            }:
                # verification only legal after complete exec for passing results;
                # still surface as next when exec is complete.
                if finding.execution_status in _COMPLETE_EXECUTION:
                    enabled.append(EventType.VERIFICATION_RECORDED.value)
        elif finding.execution_status in _COMPLETE_EXECUTION:
            if finding.verification_status not in _PASSING_VERIFICATION:
                enabled.append(EventType.VERIFICATION_RECORDED.value)
            else:
                enabled.append(EventType.REOPENED.value)

        if residual is ResidualClass.READY_FOR_CLOSURE:
            # Policy READY_FOR_CLOSURE = accepting + complete exec + non-passing ver.
            # Next continuity step is class-matched verification, not silent close.
            enabled = [
                EventType.VERIFICATION_RECORDED.value,
                EventType.REOPENED.value,
            ]

    enabled.append(EventType.REOPENED.value)
    return tuple(dict.fromkeys(enabled))


def missing_for_next(
    *,
    finding: Finding,
    residual: ResidualClass,
    next_events: tuple[str, ...],
    graph: GraphContextView,
) -> tuple[str, ...]:
    missing: list[str] = []

    if residual is ResidualClass.AWAITING_DISPOSITION:
        missing.append("human disposition_recorded with rationale and source_revision")
        return tuple(missing)

    if residual is ResidualClass.DEFERRED_PARKED:
        missing.append("explicit reopen or un-defer disposition before product work")
        return tuple(missing)

    if residual is ResidualClass.TERMINAL_WITHOUT_IMPLEMENTATION:
        missing.append("none — terminal residual without implementation work")
        return tuple(missing)

    if residual is ResidualClass.CLOSED:
        missing.append("none — derived closed")
        return tuple(missing)

    if residual is ResidualClass.BLOCKED_GRAPH:
        if graph.open_children:
            missing.append(
                "close or terminalize open split children: " + ", ".join(graph.open_children)
            )
        if graph.active_blockers:
            missing.append("resolve active blockers: " + ", ".join(graph.active_blockers))
        return tuple(missing)

    if (
        EventType.EXECUTION_LINKED.value in next_events
        and finding.execution_status is ExecutionStatus.UNPLANNED
    ):
        missing.append(
            "execution_linked with opaque ref and execution status "
            f"(proof_class={finding.required_proof_class.value})"
        )
    if EventType.VERIFICATION_RECORDED.value in next_events:
        missing.append(
            "class-matched verification_recorded "
            f"(proof_class={finding.required_proof_class.value}, "
            "tested_revision, evidence_anchors; passed_validated forbidden)"
        )
    if residual is ResidualClass.PROCESS_CLOSEABLE:
        missing.append("process evidence anchors (governor/status/commit) via human ceremony")
    if residual is ResidualClass.PRODUCT_OPEN:
        missing.append("product/design/impl work outside contour; link via execution_linked only")

    return tuple(missing)


def build_finding_fsm_snapshot(packet: ReviewPacket, finding_id: str) -> FindingFsmSnapshot:
    finding = next(item for item in packet.findings if item.finding_id == finding_id)
    derived = derive_finding_status(packet, finding_id)
    graph = _graph_context(packet, finding_id)
    residual = classify_residual_class(finding=finding, derived=derived, graph=graph)
    stage = classify_operator_stage(finding=finding, residual=residual)
    next_events = next_admissible_events(finding=finding, residual=residual, graph=graph)
    missing = missing_for_next(
        finding=finding,
        residual=residual,
        next_events=next_events,
        graph=graph,
    )
    latest = _latest_finding_event(packet, finding_id)
    last_view = None
    if latest is not None:
        last_view = LastEventView(
            event_id=latest.event_id,
            event_type=latest.event_type.value,
            at=latest.at,
            actor_class=latest.actor_class.value,
            actor_id=latest.actor_id,
            rationale=latest.rationale,
        )
    return FindingFsmSnapshot(
        finding_id=finding.finding_id,
        summary=finding.summary,
        kind=finding.kind.value,
        concern_class=finding.concern_class.value,
        required_proof_class=finding.required_proof_class.value,
        normalization_status=finding.normalization_status.value,
        disposition_status=finding.disposition_status.value,
        execution_status=finding.execution_status.value,
        verification_status=finding.verification_status.value,
        derived_status=derived.value,
        residual_class=residual.value,
        operator_stage=stage.value,
        next_admissible_events=next_events,
        missing_for_next=missing,
        graph=graph,
        last_event=last_view,
        non_claims=finding.non_claims,
    )


def _count_pairs(values: tuple[str, ...]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(counts.items(), key=lambda item: item[0]))


def build_packet_fsm_inventory(packet: ReviewPacket) -> PacketFsmInventory:
    snapshots = tuple(
        build_finding_fsm_snapshot(packet, finding.finding_id) for finding in packet.findings
    )
    residual_counts = _count_pairs(tuple(item.residual_class for item in snapshots))
    stage_counts = _count_pairs(tuple(item.operator_stage for item in snapshots))
    open_blockers = tuple(
        item.finding_id
        for item in snapshots
        if item.residual_class == ResidualClass.BLOCKED_GRAPH.value
        or item.derived_status == DerivedStatus.BLOCKED.value
    )
    return PacketFsmInventory(
        packet_id=packet.packet_id,
        source_path=packet.source.path,
        reviewed_git_revision=packet.source.reviewed_git_revision,
        content_sha256=packet.source.content_sha256,
        normalization_status=packet.normalization.status.value,
        finding_count=len(snapshots),
        residual_counts=residual_counts,
        stage_counts=stage_counts,
        findings=snapshots,
        open_blockers=open_blockers,
    )


def build_review_fsm_inventory(packets: tuple[ReviewPacket, ...]) -> ReviewFsmInventory:
    ordered = tuple(sorted(packets, key=lambda item: item.packet_id))
    packet_rows = tuple(build_packet_fsm_inventory(packet) for packet in ordered)
    all_residuals = tuple(
        finding.residual_class for packet in packet_rows for finding in packet.findings
    )
    all_stages = tuple(
        finding.operator_stage for packet in packet_rows for finding in packet.findings
    )
    open_blockers = tuple(
        (packet.packet_id, finding_id)
        for packet in packet_rows
        for finding_id in packet.open_blockers
    )
    return ReviewFsmInventory(
        schema_version=FSM_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        packet_count=len(packet_rows),
        finding_count=sum(packet.finding_count for packet in packet_rows),
        residual_counts=_count_pairs(all_residuals),
        stage_counts=_count_pairs(all_stages),
        packets=packet_rows,
        open_blockers=open_blockers,
        non_claims=_DEFAULT_NON_CLAIMS,
    )
