"""Pure Review Case relation and disposition policy.

Returns immutable replacement packets. No I/O, codecs, CLI, Governor, GSD, or
product-domain semantics. Closure and proof policy remain out of scope.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from law_nexus_harness.review_case.domain import (
    ActorClass,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    Finding,
    NormalizationStatus,
    RelationStatus,
    RelationType,
    ReviewCaseValidationError,
    ReviewCaseViolation,
    ReviewEdge,
    ReviewEvent,
    ReviewPacket,
)

_FINDING_ENDPOINT_RELATIONS = frozenset(
    {
        RelationType.REFINES,
        RelationType.REASSESSES,
        RelationType.DUPLICATES,
        RelationType.SUPERSEDES,
        RelationType.CONFLICTS_WITH,
        RelationType.SPLITS_INTO,
        RelationType.DEPENDS_ON,
        RelationType.BLOCKED_BY,
    }
)
_CYCLE_RELATIONS = frozenset({RelationType.DEPENDS_ON, RelationType.BLOCKED_BY})
_EXTERNAL_TARGET_RELATIONS = frozenset(
    {
        RelationType.PROMOTED_TO,
        RelationType.IMPLEMENTED_BY,
        RelationType.VERIFIED_BY,
    }
)
_ACCEPTING_DISPOSITIONS = frozenset(
    {
        DispositionStatus.ACCEPTED_AS_GAP,
        DispositionStatus.ACCEPTED_AS_REQUIREMENT_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_DECISION_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
        DispositionStatus.ALREADY_SATISFIED,
    }
)
_TERMINAL_WITHOUT_WORK = frozenset(
    {
        DispositionStatus.REJECTED,
        DispositionStatus.DUPLICATE,
        DispositionStatus.SUPERSEDED,
        DispositionStatus.NOT_APPLICABLE,
    }
)


def _raise_if(violations: Iterable[ReviewCaseViolation]) -> None:
    material = tuple(violations)
    if material:
        raise ReviewCaseValidationError(material)


def _finding_map(packets: Sequence[ReviewPacket]) -> dict[str, Finding]:
    findings: dict[str, Finding] = {}
    for packet in packets:
        for item in packet.findings:
            findings[item.finding_id] = item
    return findings


def _event_shape_violations(event: ReviewEvent, *, field_path: str) -> list[ReviewCaseViolation]:
    violations: list[ReviewCaseViolation] = []
    if event.event_type is EventType.DISPOSITION_RECORDED:
        if (
            event.finding_id is None
            or event.disposition is None
            or event.source_revision is None
            or event.rationale is None
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "disposition_recorded requires finding, disposition, source revision, and rationale",
                    event.event_id,
                )
            )
        if event.edge_type is not None or event.from_id is not None or event.to_id is not None:
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "disposition_recorded cannot carry relation fields",
                    event.event_id,
                )
            )
    elif event.event_type is EventType.NORMALIZATION_REVIEWED:
        if event.source_revision is None or event.rationale is None:
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "normalization_reviewed requires source revision and rationale",
                    event.event_id,
                )
            )
        if any(
            value is not None
            for value in (
                event.finding_id,
                event.disposition,
                event.edge_type,
                event.from_id,
                event.to_id,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "normalization_reviewed cannot carry finding, disposition, or relation fields",
                    event.event_id,
                )
            )
    elif event.event_type is EventType.EDGE_ASSERTED:
        if (
            event.edge_type is None
            or event.from_id is None
            or event.to_id is None
            or event.source_revision is None
            or event.rationale is None
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "edge_asserted requires relation, endpoints, source revision, and rationale",
                    event.event_id,
                )
            )
        if event.disposition is not None:
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "edge_asserted cannot carry disposition",
                    event.event_id,
                )
            )
    return violations


def _human_dispositions(packet: ReviewPacket) -> set[tuple[str, DispositionStatus]]:
    matches: set[tuple[str, DispositionStatus]] = set()
    for event in packet.events:
        if (
            event.event_type is EventType.DISPOSITION_RECORDED
            and event.actor_class is ActorClass.HUMAN
            and event.finding_id is not None
            and event.disposition is not None
        ):
            matches.add((event.finding_id, event.disposition))
    return matches


def _human_accepting_findings(packet: ReviewPacket) -> set[str]:
    return {
        finding_id
        for finding_id, disposition in _human_dispositions(packet)
        if disposition in _ACCEPTING_DISPOSITIONS
    }


def _matching_human_edge_events(
    packet: ReviewPacket,
    *,
    edge_type: RelationType,
    from_id: str,
    to_id: str,
) -> list[ReviewEvent]:
    return [
        event
        for event in packet.events
        if event.event_type is EventType.EDGE_ASSERTED
        and event.actor_class is ActorClass.HUMAN
        and event.edge_type is edge_type
        and event.from_id == from_id
        and event.to_id == to_id
    ]


def _has_cycle(edges: Sequence[ReviewEdge]) -> bool:
    graph: dict[str, set[str]] = {}
    for edge in edges:
        if edge.type not in _CYCLE_RELATIONS:
            continue
        graph.setdefault(edge.from_id, set()).add(edge.to_id)
        graph.setdefault(edge.to_id, set())

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, ()):
            if dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in graph)


def validate_review_policy(packets: tuple[ReviewPacket, ...]) -> None:
    if not isinstance(packets, tuple):
        raise ReviewCaseValidationError(
            (
                ReviewCaseViolation(
                    "invalid_collection",
                    "packets",
                    "expected immutable tuple of ReviewPacket",
                    type(packets).__name__,
                ),
            )
        )
    violations: list[ReviewCaseViolation] = []
    valid_packets: list[ReviewPacket] = []
    packet_ids: set[str] = set()
    for packet_index, packet in enumerate(packets):
        if not isinstance(packet, ReviewPacket):
            violations.append(
                ReviewCaseViolation(
                    "invalid_type",
                    f"packets[{packet_index}]",
                    "expected ReviewPacket",
                    type(packet).__name__,
                )
            )
            continue
        if packet.packet_id in packet_ids:
            violations.append(
                ReviewCaseViolation(
                    "duplicate_packet_id",
                    f"packets[{packet_index}].packet_id",
                    "packet ids must be unique across validated packets",
                    packet.packet_id,
                )
            )
        packet_ids.add(packet.packet_id)
        valid_packets.append(packet)

    findings = _finding_map(valid_packets)
    global_finding_ids: set[str] = set()
    global_event_ids: set[str] = set()
    all_edges: list[ReviewEdge] = []
    for packet_index, packet in enumerate(valid_packets):
        for finding in packet.findings:
            if finding.finding_id in global_finding_ids:
                violations.append(
                    ReviewCaseViolation(
                        "duplicate_global_finding_id",
                        f"packets[{packet_index}].findings",
                        "finding ids must be unique across validated packets",
                        finding.finding_id,
                    )
                )
            global_finding_ids.add(finding.finding_id)
        for event in packet.events:
            if event.event_id in global_event_ids:
                violations.append(
                    ReviewCaseViolation(
                        "duplicate_global_event_id",
                        f"packets[{packet_index}].events",
                        "event ids must be unique across validated packets",
                        event.event_id,
                    )
                )
            global_event_ids.add(event.event_id)
        all_edges.extend(packet.edges)

    for packet_index, packet in enumerate(valid_packets):
        human_dispositions = _human_dispositions(packet)
        human_accepting = _human_accepting_findings(packet)

        if packet.normalization.status is NormalizationStatus.HUMAN_REVIEWED and not any(
            event.event_type is EventType.NORMALIZATION_REVIEWED
            and event.actor_class is ActorClass.HUMAN
            for event in packet.events
        ):
            violations.append(
                ReviewCaseViolation(
                    "normalization_review_event_required",
                    f"packets[{packet_index}].normalization.status",
                    "human_reviewed requires human normalization_reviewed event",
                    packet.normalization.status.value,
                )
            )

        for finding in packet.findings:
            if finding.disposition_status is DispositionStatus.OPEN:
                continue
            if (finding.finding_id, finding.disposition_status) not in human_dispositions:
                violations.append(
                    ReviewCaseViolation(
                        "disposition_event_required",
                        f"findings[{finding.finding_id}].disposition_status",
                        "non-open disposition requires matching human disposition_recorded event",
                        finding.disposition_status.value,
                    )
                )
            if (
                finding.disposition_status in _TERMINAL_WITHOUT_WORK
                and finding.execution_status.value not in {"not_required", "cancelled"}
            ):
                violations.append(
                    ReviewCaseViolation(
                        "terminal_execution_mismatch",
                        f"findings[{finding.finding_id}].execution_status",
                        "terminal disposition requires execution_status=not_required",
                        finding.execution_status.value,
                    )
                )

        packet_finding_ids = {finding.finding_id for finding in packet.findings}
        for event_index, event in enumerate(packet.events):
            violations.extend(
                _event_shape_violations(
                    event,
                    field_path=f"packets[{packet_index}].events[{event_index}]",
                )
            )
            if event.event_type is not EventType.DISPOSITION_RECORDED:
                continue
            if event.finding_id not in packet_finding_ids:
                violations.append(
                    ReviewCaseViolation(
                        "unknown_finding",
                        f"events[{event.event_id}].finding_id",
                        "disposition event finding must exist in the same packet",
                        event.finding_id,
                    )
                )
            if event.disposition is None:
                violations.append(
                    ReviewCaseViolation(
                        "invalid_event_shape",
                        f"events[{event.event_id}].disposition",
                        "disposition_recorded requires disposition",
                        None,
                    )
                )
                continue
            if (
                event.disposition is not DispositionStatus.OPEN
                and event.actor_class is not ActorClass.HUMAN
            ):
                violations.append(
                    ReviewCaseViolation(
                        "human_actor_required",
                        f"events[{event.event_id}].actor_class",
                        "non-open disposition requires actor_class=human",
                        event.actor_class.value,
                    )
                )

        for edge_index, edge in enumerate(packet.edges):
            if edge.from_id == edge.to_id and edge.type in _FINDING_ENDPOINT_RELATIONS | {
                RelationType.DEPENDS_ON,
                RelationType.BLOCKED_BY,
                RelationType.SPLITS_INTO,
            }:
                violations.append(
                    ReviewCaseViolation(
                        "self_relation",
                        f"edges[{edge_index}]",
                        "finding relation cannot target itself",
                        edge.type.value,
                    )
                )

            if edge.type is RelationType.MAPS_TO:
                if edge.from_id not in findings:
                    violations.append(
                        ReviewCaseViolation(
                            "missing_relation_endpoint",
                            f"edges[{edge_index}].from_id",
                            "maps_to source must resolve to a finding",
                            edge.from_id,
                        )
                    )
                if edge.to_id in findings:
                    violations.append(
                        ReviewCaseViolation(
                            "opaque_maps_to_target_required",
                            f"edges[{edge_index}].to_id",
                            "maps_to target must remain an opaque external id",
                            edge.to_id,
                        )
                    )
                if edge.status is not RelationStatus.CANDIDATE:
                    violations.append(
                        ReviewCaseViolation(
                            "maps_to_must_remain_candidate",
                            f"edges[{edge_index}].status",
                            "maps_to must remain candidate",
                            edge.status.value,
                        )
                    )
                continue

            if edge.type in _EXTERNAL_TARGET_RELATIONS and edge.from_id not in findings:
                violations.append(
                    ReviewCaseViolation(
                        "missing_relation_endpoint",
                        f"edges[{edge_index}].from_id",
                        "external reference relation source must resolve to a finding",
                        edge.from_id,
                    )
                )

            if edge.type in _FINDING_ENDPOINT_RELATIONS:
                for endpoint, field_name in (
                    (edge.from_id, "from_id"),
                    (edge.to_id, "to_id"),
                ):
                    if endpoint not in findings:
                        violations.append(
                            ReviewCaseViolation(
                                "missing_relation_endpoint",
                                f"edges[{edge_index}].{field_name}",
                                "relation endpoint must resolve to a finding",
                                endpoint,
                            )
                        )

            if (
                edge.type is not RelationType.MAPS_TO
                and edge.status is not RelationStatus.CANDIDATE
            ):
                if not _matching_human_edge_events(
                    packet,
                    edge_type=edge.type,
                    from_id=edge.from_id,
                    to_id=edge.to_id,
                ):
                    violations.append(
                        ReviewCaseViolation(
                            "edge_event_required",
                            f"edges[{edge_index}]",
                            "non-candidate relation requires matching human edge_asserted event",
                            edge.type.value,
                        )
                    )

            if edge.type is RelationType.PROMOTED_TO:
                if edge.from_id not in human_accepting:
                    violations.append(
                        ReviewCaseViolation(
                            "promoted_to_requires_human_accepting_disposition",
                            f"edges[{edge_index}]",
                            "promoted_to requires prior human accepting disposition",
                            edge.from_id,
                        )
                    )
                if not _matching_human_edge_events(
                    packet,
                    edge_type=RelationType.PROMOTED_TO,
                    from_id=edge.from_id,
                    to_id=edge.to_id,
                ):
                    violations.append(
                        ReviewCaseViolation(
                            "edge_event_required",
                            f"edges[{edge_index}]",
                            "promoted_to requires matching human edge_asserted event",
                            edge.to_id,
                        )
                    )
                if any(
                    event.event_type is EventType.EDGE_ASSERTED
                    and event.actor_class is not ActorClass.HUMAN
                    and event.edge_type is RelationType.PROMOTED_TO
                    and event.from_id == edge.from_id
                    and event.to_id == edge.to_id
                    for event in packet.events
                ):
                    violations.append(
                        ReviewCaseViolation(
                            "human_actor_required",
                            f"edges[{edge_index}]",
                            "promoted_to cannot be asserted by tool or llm",
                            edge.from_id,
                        )
                    )

    if _has_cycle(all_edges):
        violations.append(
            ReviewCaseViolation(
                "relation_cycle",
                "packets[*].edges",
                "depends_on/blocked_by graph must be acyclic across packets",
                None,
            )
        )

    _raise_if(violations)


def record_disposition(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.DISPOSITION_RECORDED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected disposition_recorded",
                event.event_type.value,
            )
        )
    if event.actor_class is not ActorClass.HUMAN:
        violations.append(
            ReviewCaseViolation(
                "human_actor_required",
                "event.actor_class",
                "disposition_recorded requires actor_class=human",
                event.actor_class.value,
            )
        )
    if event.finding_id is None:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.finding_id",
                "disposition_recorded requires finding_id",
                None,
            )
        )
    if event.disposition is None:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.disposition",
                "disposition_recorded requires disposition",
                None,
            )
        )
    if any(item.event_id == event.event_id for item in packet.events):
        violations.append(
            ReviewCaseViolation(
                "duplicate_event_id",
                "event.event_id",
                "event ids must be unique within a packet",
                event.event_id,
            )
        )
    finding_index = next(
        (
            index
            for index, item in enumerate(packet.findings)
            if item.finding_id == event.finding_id
        ),
        None,
    )
    if event.finding_id is not None and finding_index is None:
        violations.append(
            ReviewCaseViolation(
                "unknown_finding",
                "event.finding_id",
                "disposition target finding is unknown",
                event.finding_id,
            )
        )
    _raise_if(violations)
    assert finding_index is not None
    assert event.disposition is not None
    current_finding = packet.findings[finding_index]
    updated_execution = current_finding.execution_status
    if event.disposition in _TERMINAL_WITHOUT_WORK:
        if current_finding.execution_status is ExecutionStatus.UNPLANNED:
            updated_execution = ExecutionStatus.NOT_REQUIRED
        elif current_finding.execution_status not in {
            ExecutionStatus.NOT_REQUIRED,
            ExecutionStatus.CANCELLED,
        }:
            violations.append(
                ReviewCaseViolation(
                    "terminal_execution_transition_requires_resolution",
                    "finding.execution_status",
                    "terminal disposition cannot erase existing execution progress",
                    current_finding.execution_status.value,
                )
            )
    _raise_if(violations)
    updated_finding = replace(
        current_finding,
        disposition_status=event.disposition,
        execution_status=updated_execution,
    )
    findings = list(packet.findings)
    findings[finding_index] = updated_finding
    return replace(
        packet,
        findings=tuple(findings),
        events=(*packet.events, event),
    )


def assert_relation(
    packet: ReviewPacket,
    edge: ReviewEdge,
    event: ReviewEvent,
) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.EDGE_ASSERTED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected edge_asserted",
                event.event_type.value,
            )
        )
    if event.actor_class is not ActorClass.HUMAN:
        violations.append(
            ReviewCaseViolation(
                "human_actor_required",
                "event.actor_class",
                "edge_asserted requires actor_class=human",
                event.actor_class.value,
            )
        )
    if edge.type is RelationType.MAPS_TO and edge.status is not RelationStatus.CANDIDATE:
        violations.append(
            ReviewCaseViolation(
                "maps_to_must_remain_candidate",
                "edge.status",
                "maps_to must remain candidate",
                edge.status.value,
            )
        )
    if (
        event.edge_type is not edge.type
        or event.from_id != edge.from_id
        or event.to_id != edge.to_id
    ):
        violations.append(
            ReviewCaseViolation(
                "edge_event_mismatch",
                "event",
                "edge_asserted payload must match edge type and endpoints",
                event.event_id,
            )
        )
    if any(item.event_id == event.event_id for item in packet.events):
        violations.append(
            ReviewCaseViolation(
                "duplicate_event_id",
                "event.event_id",
                "event ids must be unique within a packet",
                event.event_id,
            )
        )
    if edge.type is RelationType.PROMOTED_TO:
        if edge.from_id not in _human_accepting_findings(packet):
            violations.append(
                ReviewCaseViolation(
                    "promoted_to_requires_human_accepting_disposition",
                    "edge.from_id",
                    "promoted_to requires prior human accepting disposition",
                    edge.from_id,
                )
            )
    provisional = replace(
        packet,
        edges=(*packet.edges, edge),
        events=(*packet.events, event),
    )
    # Endpoint and cycle checks reuse the shared validator after construction.
    try:
        validate_review_policy((provisional,))
    except ReviewCaseValidationError as exc:
        violations.extend(exc.violations)
    _raise_if(violations)
    return provisional


def record_normalization_review(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.NORMALIZATION_REVIEWED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected normalization_reviewed",
                event.event_type.value,
            )
        )
    if event.actor_class is not ActorClass.HUMAN:
        violations.append(
            ReviewCaseViolation(
                "human_actor_required",
                "event.actor_class",
                "normalization_reviewed requires actor_class=human",
                event.actor_class.value,
            )
        )
    if any(item.event_id == event.event_id for item in packet.events):
        violations.append(
            ReviewCaseViolation(
                "duplicate_event_id",
                "event.event_id",
                "event ids must be unique within a packet",
                event.event_id,
            )
        )
    _raise_if(violations)
    return replace(
        packet,
        normalization=replace(
            packet.normalization,
            status=NormalizationStatus.HUMAN_REVIEWED,
        ),
        events=(*packet.events, event),
    )
