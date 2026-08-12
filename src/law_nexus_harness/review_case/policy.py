"""Pure Review Case relation, disposition, proof, and derived-rollup policy.

Returns immutable replacement packets. No I/O, codecs, CLI, Governor, GSD, or
product-domain semantics. DerivedStatus is computed only and never persisted.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from law_nexus_harness.review_case.domain import (
    ActorClass,
    DerivedStatus,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    Finding,
    NormalizationStatus,
    ProofClass,
    RelationStatus,
    RelationType,
    ReviewCaseValidationError,
    ReviewCaseViolation,
    ReviewEdge,
    ReviewEvent,
    ReviewPacket,
    VerificationStatus,
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
        # already_satisfied is terminal residual (docs/process satisfaction),
        # not an accepting path that still requires execution/proof work.
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
_PASSING_VERIFICATION = frozenset(
    {
        VerificationStatus.PASSED_BOUNDED,
        VerificationStatus.PASSED_SMOKE,
    }
)
_ALLOWED_VERIFICATION_RESULTS = frozenset(
    {
        VerificationStatus.PASSED_BOUNDED,
        VerificationStatus.PASSED_SMOKE,
        VerificationStatus.FAILED,
        VerificationStatus.INCONCLUSIVE,
    }
)
_COMPLETE_EXECUTION = frozenset(
    {
        ExecutionStatus.IMPLEMENTED,
        ExecutionStatus.NOT_REQUIRED,
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
        if any(
            value is not None
            for value in (
                event.edge_type,
                event.from_id,
                event.to_id,
                event.proof_class,
                event.verification_result,
                event.tested_revision,
                event.evidence_anchors,
                event.completed_scope,
                event.residual_scope,
                event.non_claims,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "disposition_recorded cannot carry relation or proof fields",
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
                event.proof_class,
                event.verification_result,
                event.tested_revision,
                event.evidence_anchors,
                event.completed_scope,
                event.residual_scope,
                event.non_claims,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "normalization_reviewed cannot carry finding, disposition, relation, or proof fields",
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
        if any(
            value is not None
            for value in (
                event.proof_class,
                event.verification_result,
                event.tested_revision,
                event.evidence_anchors,
                event.completed_scope,
                event.residual_scope,
                event.non_claims,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "edge_asserted cannot carry proof payload",
                    event.event_id,
                )
            )
    elif event.event_type is EventType.VERIFICATION_RECORDED:
        if event.actor_class not in {ActorClass.HUMAN, ActorClass.TOOL}:
            violations.append(
                ReviewCaseViolation(
                    "human_or_tool_actor_required",
                    field_path,
                    "verification_recorded requires actor_class=human or tool",
                    event.actor_class.value,
                )
            )
        if (
            event.finding_id is None
            or event.source_revision is None
            or event.rationale is None
            or event.proof_class is None
            or event.verification_result is None
            or event.tested_revision is None
            or not event.evidence_anchors
            or not event.non_claims
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "verification_recorded requires finding, revisions, proof class, anchors, and non-claims",
                    event.event_id,
                )
            )
        if event.residual_scope and not event.completed_scope:
            violations.append(
                ReviewCaseViolation(
                    "partial_scope_requires_completed_scope",
                    field_path,
                    "partial verification requires non-empty completed_scope",
                    event.event_id,
                )
            )
        if any(
            value is not None
            for value in (
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
                    "verification_recorded cannot carry disposition or relation fields",
                    event.event_id,
                )
            )
    elif event.event_type in {EventType.REOPENED, EventType.MARKED_STALE}:
        if event.actor_class is not ActorClass.HUMAN:
            violations.append(
                ReviewCaseViolation(
                    "human_actor_required",
                    field_path,
                    f"{event.event_type.value} requires actor_class=human",
                    event.actor_class.value,
                )
            )
        if event.finding_id is None or event.source_revision is None or event.rationale is None:
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    f"{event.event_type.value} requires finding, source revision, and rationale",
                    event.event_id,
                )
            )
        if any(
            value is not None
            for value in (
                event.disposition,
                event.edge_type,
                event.from_id,
                event.to_id,
                event.proof_class,
                event.verification_result,
                event.tested_revision,
                event.evidence_anchors,
                event.completed_scope,
                event.residual_scope,
                event.non_claims,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    f"{event.event_type.value} cannot carry disposition, relation, or proof payload",
                    event.event_id,
                )
            )
    elif event.event_type is EventType.EXECUTION_LINKED:
        if event.actor_class is not ActorClass.HUMAN:
            violations.append(
                ReviewCaseViolation(
                    "human_actor_required",
                    field_path,
                    "execution_linked requires actor_class=human",
                    event.actor_class.value,
                )
            )
        if (
            event.finding_id is None
            or event.source_revision is None
            or event.rationale is None
            or event.to_id is None
            or not event.completed_scope
            or not event.non_claims
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "execution_linked requires finding, opaque reference, status scope, revision, rationale, and non-claims",
                    event.event_id,
                )
            )
        if event.completed_scope is not None:
            if len(event.completed_scope) != 1:
                violations.append(
                    ReviewCaseViolation(
                        "invalid_event_shape",
                        field_path,
                        "execution_linked completed_scope must carry exactly one ExecutionStatus value",
                        event.event_id,
                    )
                )
            else:
                try:
                    ExecutionStatus(event.completed_scope[0])
                except ValueError:
                    violations.append(
                        ReviewCaseViolation(
                            "invalid_execution_status",
                            field_path,
                            "execution_linked completed_scope must be a valid ExecutionStatus",
                            event.completed_scope[0],
                        )
                    )
        if any(
            value is not None
            for value in (
                event.disposition,
                event.edge_type,
                event.from_id,
                event.proof_class,
                event.verification_result,
                event.tested_revision,
                event.evidence_anchors,
                event.residual_scope,
            )
        ):
            violations.append(
                ReviewCaseViolation(
                    "invalid_event_shape",
                    field_path,
                    "execution_linked cannot carry disposition, relation endpoints, or proof payload",
                    event.event_id,
                )
            )
    return violations


def _latest_event(
    packet: ReviewPacket,
    *,
    event_type: EventType,
    finding_id: str,
) -> ReviewEvent | None:
    for event in reversed(packet.events):
        if event.event_type is event_type and event.finding_id == finding_id:
            return event
    return None


def _has_active_blocker_or_open_child(packet: ReviewPacket, finding_id: str) -> bool:
    findings = {item.finding_id: item for item in packet.findings}
    for edge in packet.edges:
        if edge.from_id != finding_id:
            continue
        if edge.type is RelationType.BLOCKED_BY:
            blocker = findings.get(edge.to_id)
            if blocker is None:
                return True
            if blocker.disposition_status not in _TERMINAL_WITHOUT_WORK:
                return True
        if edge.type is RelationType.SPLITS_INTO:
            child = findings.get(edge.to_id)
            if child is None:
                return True
            if child.disposition_status in _TERMINAL_WITHOUT_WORK:
                continue
            if (
                child.execution_status is ExecutionStatus.IMPLEMENTED
                and child.verification_status in _PASSING_VERIFICATION
            ):
                continue
            return True
    return False


def _latest_residual_scope(packet: ReviewPacket, finding_id: str) -> tuple[str, ...]:
    event = _latest_event(
        packet,
        event_type=EventType.VERIFICATION_RECORDED,
        finding_id=finding_id,
    )
    if event is None or event.residual_scope is None:
        return ()
    return event.residual_scope


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
            if finding.verification_status is VerificationStatus.PASSED_VALIDATED:
                violations.append(
                    ReviewCaseViolation(
                        "validated_proof_forbidden",
                        f"findings[{finding.finding_id}].verification_status",
                        "passed_validated is forbidden in the Review Case process contour",
                        finding.verification_status.value,
                    )
                )
            if finding.verification_status in _PASSING_VERIFICATION | {
                VerificationStatus.FAILED,
                VerificationStatus.INCONCLUSIVE,
            }:
                latest = _latest_event(
                    packet,
                    event_type=EventType.VERIFICATION_RECORDED,
                    finding_id=finding.finding_id,
                )
                if latest is None:
                    violations.append(
                        ReviewCaseViolation(
                            "verification_event_required",
                            f"findings[{finding.finding_id}].verification_status",
                            "recorded verification status requires verification_recorded event",
                            finding.verification_status.value,
                        )
                    )
                elif latest.proof_class is not finding.required_proof_class:
                    violations.append(
                        ReviewCaseViolation(
                            "proof_class_mismatch",
                            f"findings[{finding.finding_id}].required_proof_class",
                            "latest verification proof class must exactly match required proof class",
                            latest.proof_class.value if latest.proof_class else None,
                        )
                    )
                elif latest.verification_result is not finding.verification_status:
                    violations.append(
                        ReviewCaseViolation(
                            "verification_result_mismatch",
                            f"findings[{finding.finding_id}].verification_status",
                            "latest verification event result must match materialized status",
                            latest.verification_result.value
                            if latest.verification_result
                            else None,
                        )
                    )
            if finding.verification_status is VerificationStatus.STALE:
                if not any(
                    event.event_type is EventType.MARKED_STALE
                    and event.actor_class is ActorClass.HUMAN
                    and event.finding_id == finding.finding_id
                    for event in packet.events
                ):
                    violations.append(
                        ReviewCaseViolation(
                            "stale_event_required",
                            f"findings[{finding.finding_id}].verification_status",
                            "stale verification requires human marked_stale event",
                            finding.verification_status.value,
                        )
                    )
            if (
                finding.verification_status in _PASSING_VERIFICATION
                and finding.execution_status is ExecutionStatus.IMPLEMENTED
                and not _latest_residual_scope(packet, finding.finding_id)
                and _has_active_blocker_or_open_child(packet, finding.finding_id)
                and finding.disposition_status in _ACCEPTING_DISPOSITIONS
            ):
                # Parent may pass verification, but cannot claim closed while blocked.
                # Derived rollup enforces blocked; validation keeps history legal.
                pass

        packet_finding_ids = {finding.finding_id for finding in packet.findings}
        scoped_event_types = {
            EventType.DISPOSITION_RECORDED,
            EventType.VERIFICATION_RECORDED,
            EventType.REOPENED,
            EventType.MARKED_STALE,
        }
        seen_verification_findings: set[str] = set()
        for event_index, event in enumerate(packet.events):
            violations.extend(
                _event_shape_violations(
                    event,
                    field_path=f"packets[{packet_index}].events[{event_index}]",
                )
            )
            if (
                event.event_type in scoped_event_types
                and event.finding_id not in packet_finding_ids
            ):
                violations.append(
                    ReviewCaseViolation(
                        "unknown_finding",
                        f"events[{event.event_id}].finding_id",
                        "scoped event finding must exist in the same packet",
                        event.finding_id,
                    )
                )
            if event.event_type is EventType.MARKED_STALE and (
                event.finding_id not in seen_verification_findings
            ):
                violations.append(
                    ReviewCaseViolation(
                        "prior_verification_required",
                        f"events[{event.event_id}]",
                        "marked_stale requires an earlier verification event",
                        event.finding_id,
                    )
                )
            if event.event_type is EventType.VERIFICATION_RECORDED and event.finding_id:
                seen_verification_findings.add(event.finding_id)
            if event.event_type is not EventType.DISPOSITION_RECORDED:
                continue
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


def _finding_index(packet: ReviewPacket, finding_id: str | None) -> int | None:
    if finding_id is None:
        return None
    return next(
        (index for index, item in enumerate(packet.findings) if item.finding_id == finding_id),
        None,
    )


def record_verification(
    packet: ReviewPacket,
    event: ReviewEvent,
    *,
    status: VerificationStatus,
) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.VERIFICATION_RECORDED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected verification_recorded",
                event.event_type.value,
            )
        )
    if status is VerificationStatus.PASSED_VALIDATED:
        violations.append(
            ReviewCaseViolation(
                "validated_proof_forbidden",
                "status",
                "passed_validated is forbidden in the Review Case process contour",
                status.value,
            )
        )
    if status not in _ALLOWED_VERIFICATION_RESULTS:
        violations.append(
            ReviewCaseViolation(
                "invalid_verification_status",
                "status",
                "verification status must be passed_bounded, passed_smoke, failed, or inconclusive",
                status.value,
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
    finding_index = _finding_index(packet, event.finding_id)
    if event.finding_id is not None and finding_index is None:
        violations.append(
            ReviewCaseViolation(
                "unknown_finding",
                "event.finding_id",
                "verification target finding is unknown",
                event.finding_id,
            )
        )
    _raise_if(violations)
    assert finding_index is not None
    current = packet.findings[finding_index]
    if current.disposition_status not in _ACCEPTING_DISPOSITIONS:
        violations.append(
            ReviewCaseViolation(
                "accepting_disposition_required",
                f"findings[{current.finding_id}].disposition_status",
                "verification requires an accepting disposition (not terminal residual)",
                current.disposition_status.value,
            )
        )
    if event.verification_result is not status:
        violations.append(
            ReviewCaseViolation(
                "verification_result_mismatch",
                "event.verification_result",
                "verification event result must match requested status",
                event.verification_result.value if event.verification_result else None,
            )
        )
    if event.proof_class is not current.required_proof_class:
        violations.append(
            ReviewCaseViolation(
                "proof_class_mismatch",
                "event.proof_class",
                "proof class must exactly match required_proof_class",
                event.proof_class.value if isinstance(event.proof_class, ProofClass) else None,
            )
        )
    residual = event.residual_scope or ()
    completed = event.completed_scope or ()
    if residual and not completed:
        violations.append(
            ReviewCaseViolation(
                "partial_scope_requires_completed_scope",
                "event.completed_scope",
                "partial verification requires non-empty completed_scope",
                completed,
            )
        )
    updated_execution = current.execution_status
    if status in _PASSING_VERIFICATION:
        if residual:
            updated_execution = ExecutionStatus.PARTIALLY_IMPLEMENTED
        elif current.execution_status not in _COMPLETE_EXECUTION:
            violations.append(
                ReviewCaseViolation(
                    "execution_incomplete_for_passing_verification",
                    f"findings[{current.finding_id}].execution_status",
                    "passing verification requires implemented or not_required execution",
                    current.execution_status.value,
                )
            )
    _raise_if(violations)
    updated_finding = replace(
        current,
        execution_status=updated_execution,
        verification_status=status,
    )
    findings = list(packet.findings)
    findings[finding_index] = updated_finding
    provisional = replace(
        packet,
        findings=tuple(findings),
        events=(*packet.events, event),
    )
    validate_review_policy((provisional,))
    return provisional


def mark_stale(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.MARKED_STALE:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected marked_stale",
                event.event_type.value,
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
    finding_index = _finding_index(packet, event.finding_id)
    if event.finding_id is not None and finding_index is None:
        violations.append(
            ReviewCaseViolation(
                "unknown_finding",
                "event.finding_id",
                "stale target finding is unknown",
                event.finding_id,
            )
        )
    if (
        finding_index is not None
        and _latest_event(
            packet,
            event_type=EventType.VERIFICATION_RECORDED,
            finding_id=event.finding_id or "",
        )
        is None
    ):
        violations.append(
            ReviewCaseViolation(
                "prior_verification_required",
                "event.finding_id",
                "marked_stale requires prior verification history",
                event.finding_id,
            )
        )
    _raise_if(violations)
    assert finding_index is not None
    findings = list(packet.findings)
    findings[finding_index] = replace(
        findings[finding_index],
        verification_status=VerificationStatus.STALE,
    )
    provisional = replace(
        packet,
        findings=tuple(findings),
        events=(*packet.events, event),
    )
    validate_review_policy((provisional,))
    return provisional


_REPLAYABLE_EVENT_TYPES = frozenset(
    {
        EventType.NORMALIZATION_REVIEWED,
        EventType.DISPOSITION_RECORDED,
        EventType.EDGE_ASSERTED,
        EventType.EXECUTION_LINKED,
        EventType.VERIFICATION_RECORDED,
        EventType.REOPENED,
        EventType.MARKED_STALE,
    }
)
_BASE_ONLY_EVENT_TYPES = frozenset(
    {
        EventType.PACKET_REGISTERED,
        EventType.FINDING_EXTRACTED,
        EventType.SPAN_VERIFIED,
    }
)


def record_execution_link(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    """Record an opaque execution reference and materialize execution_status.

    Does not create or mutate GSD/task lifecycle. The external ID is opaque.
    """
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.EXECUTION_LINKED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected execution_linked",
                event.event_type.value,
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
    finding_index = _finding_index(packet, event.finding_id)
    if event.finding_id is not None and finding_index is None:
        violations.append(
            ReviewCaseViolation(
                "unknown_finding",
                "event.finding_id",
                "execution link target finding is unknown",
                event.finding_id,
            )
        )
    _raise_if(violations)
    assert finding_index is not None
    assert event.completed_scope is not None and len(event.completed_scope) == 1
    current = packet.findings[finding_index]
    if current.disposition_status not in _ACCEPTING_DISPOSITIONS:
        violations.append(
            ReviewCaseViolation(
                "accepting_disposition_required",
                f"findings[{current.finding_id}].disposition_status",
                "execution_linked requires an accepting disposition (not terminal residual)",
                current.disposition_status.value,
            )
        )
    try:
        next_status = ExecutionStatus(event.completed_scope[0])
    except ValueError:
        violations.append(
            ReviewCaseViolation(
                "invalid_execution_status",
                "event.completed_scope",
                "execution_linked completed_scope must be a valid ExecutionStatus",
                event.completed_scope[0],
            )
        )
        _raise_if(violations)
        raise AssertionError("unreachable")  # pragma: no cover
    if next_status is ExecutionStatus.UNPLANNED:
        violations.append(
            ReviewCaseViolation(
                "invalid_execution_status",
                "event.completed_scope",
                "execution_linked cannot materialize unplanned; use reopen instead",
                next_status.value,
            )
        )
    _raise_if(violations)
    findings = list(packet.findings)
    findings[finding_index] = replace(current, execution_status=next_status)
    provisional = replace(
        packet,
        findings=tuple(findings),
        events=(*packet.events, event),
    )
    validate_review_policy((provisional,))
    return provisional


def apply_event(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    """Apply one consequential event to a materialized packet.

    Registration/extraction events belong on the immutable base and are not
    replayed through this path.
    """
    if event.event_type is EventType.DISPOSITION_RECORDED:
        return record_disposition(packet, event)
    if event.event_type is EventType.EDGE_ASSERTED:
        if event.edge_type is None or event.from_id is None or event.to_id is None:
            raise ReviewCaseValidationError(
                (
                    ReviewCaseViolation(
                        "invalid_event_shape",
                        "event",
                        "edge_asserted requires type and endpoints",
                        event.event_id,
                    ),
                )
            )
        status = (
            RelationStatus.CANDIDATE
            if event.edge_type is RelationType.MAPS_TO
            else RelationStatus.ACCEPTED
        )
        edge = ReviewEdge(
            type=event.edge_type,
            from_id=event.from_id,
            to_id=event.to_id,
            status=status,
        )
        return assert_relation(packet, edge, event)
    if event.event_type is EventType.NORMALIZATION_REVIEWED:
        return record_normalization_review(packet, event)
    if event.event_type is EventType.EXECUTION_LINKED:
        return record_execution_link(packet, event)
    if event.event_type is EventType.VERIFICATION_RECORDED:
        if event.verification_result is None:
            raise ReviewCaseValidationError(
                (
                    ReviewCaseViolation(
                        "invalid_event_shape",
                        "event.verification_result",
                        "verification_recorded requires verification_result",
                        event.event_id,
                    ),
                )
            )
        return record_verification(
            packet,
            event,
            status=event.verification_result,
        )
    if event.event_type is EventType.MARKED_STALE:
        return mark_stale(packet, event)
    if event.event_type is EventType.REOPENED:
        return reopen_finding(packet, event)
    raise ReviewCaseValidationError(
        (
            ReviewCaseViolation(
                "unsupported_replay_event",
                "event.event_type",
                "event type cannot be applied through pure replay",
                event.event_type.value,
            ),
        )
    )


def replay_events(
    base: ReviewPacket,
    events: Sequence[ReviewEvent],
) -> ReviewPacket:
    """Materialize current state from a clean base packet plus ordered events."""
    violations: list[ReviewCaseViolation] = []
    for event_index, event in enumerate(base.events):
        if event.event_type in _REPLAYABLE_EVENT_TYPES:
            violations.append(
                ReviewCaseViolation(
                    "base_packet_not_clean",
                    f"base.events[{event_index}]",
                    "base packet must not already contain replayable consequential history",
                    event.event_id,
                )
            )
        elif event.event_type not in _BASE_ONLY_EVENT_TYPES:
            violations.append(
                ReviewCaseViolation(
                    "base_packet_not_clean",
                    f"base.events[{event_index}]",
                    "base packet may only retain registration/extraction events",
                    event.event_type.value,
                )
            )
    _raise_if(violations)
    # Validate the immutable base before replaying the ledger tail.
    validate_review_policy((base,))
    current = base
    for event in events:
        current = apply_event(current, event)
    return current


def reopen_finding(packet: ReviewPacket, event: ReviewEvent) -> ReviewPacket:
    violations = _event_shape_violations(event, field_path="event")
    if event.event_type is not EventType.REOPENED:
        violations.append(
            ReviewCaseViolation(
                "invalid_event_shape",
                "event.event_type",
                "expected reopened",
                event.event_type.value,
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
    finding_index = _finding_index(packet, event.finding_id)
    if event.finding_id is not None and finding_index is None:
        violations.append(
            ReviewCaseViolation(
                "unknown_finding",
                "event.finding_id",
                "reopen target finding is unknown",
                event.finding_id,
            )
        )
    _raise_if(violations)
    assert finding_index is not None
    findings = list(packet.findings)
    findings[finding_index] = replace(
        findings[finding_index],
        disposition_status=DispositionStatus.OPEN,
        execution_status=ExecutionStatus.UNPLANNED,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    provisional = replace(
        packet,
        findings=tuple(findings),
        events=(*packet.events, event),
    )
    validate_review_policy((provisional,))
    return provisional


def derive_finding_status(packet: ReviewPacket, finding_id: str) -> DerivedStatus:
    finding = next((item for item in packet.findings if item.finding_id == finding_id), None)
    if finding is None:
        raise ReviewCaseValidationError(
            (
                ReviewCaseViolation(
                    "unknown_finding",
                    "finding_id",
                    "finding is unknown in packet",
                    finding_id,
                ),
            )
        )
    if finding.disposition_status in _TERMINAL_WITHOUT_WORK:
        return DerivedStatus.TERMINAL_WITHOUT_IMPLEMENTATION
    if (
        finding.verification_status is VerificationStatus.STALE
        or packet.normalization.status is NormalizationStatus.STALE
    ):
        return DerivedStatus.STALE
    if _has_active_blocker_or_open_child(packet, finding_id):
        return DerivedStatus.BLOCKED
    residual = _latest_residual_scope(packet, finding_id)
    if residual or finding.execution_status is ExecutionStatus.PARTIALLY_IMPLEMENTED:
        return DerivedStatus.PARTIAL
    if (
        finding.disposition_status in _ACCEPTING_DISPOSITIONS
        and finding.execution_status in _COMPLETE_EXECUTION
        and finding.verification_status in _PASSING_VERIFICATION
        and not residual
    ):
        return DerivedStatus.CLOSED
    if (
        finding.disposition_status in _ACCEPTING_DISPOSITIONS
        and finding.execution_status in _COMPLETE_EXECUTION
        and finding.verification_status not in _PASSING_VERIFICATION
    ):
        return DerivedStatus.READY_FOR_CLOSURE
    return DerivedStatus.OPEN


def derive_packet_statuses(packet: ReviewPacket) -> tuple[tuple[str, DerivedStatus], ...]:
    return tuple(
        (finding.finding_id, derive_finding_status(packet, finding.finding_id))
        for finding in packet.findings
    )
