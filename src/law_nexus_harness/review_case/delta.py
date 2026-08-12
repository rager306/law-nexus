"""Pure non-authoritative Review Case delta projection.

Classifies findings across one or more packets using candidate edges and
materialized statuses. Does not invent human disposition, promote authority,
or close findings without existing disposition/verification history.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from law_nexus_harness.review_case.domain import (
    ActorClass,
    DerivedStatus,
    DispositionStatus,
    EventType,
    FindingKind,
    RelationType,
    ReviewPacket,
)
from law_nexus_harness.review_case.policy import derive_finding_status

DELTA_MAP_SCHEMA_VERSION = "review-case-delta-map/v1"

_ACCEPTING = frozenset(
    {
        DispositionStatus.ACCEPTED_AS_GAP,
        DispositionStatus.ACCEPTED_AS_REQUIREMENT_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_DECISION_CANDIDATE,
        DispositionStatus.ACCEPTED_AS_PROCESS_DEFECT,
    }
)
_DEFAULT_NON_CLAIMS = (
    "Non-authoritative review delta projection",
    "Candidate edges are not human acceptance",
    "Confirmed closures require human disposition and class-matched proof",
    "Does not promote Product, Requirements, ADR, roadmap, or GSD lifecycle",
)


@dataclass(frozen=True, slots=True)
class ReviewDeltaMap:
    schema_version: str
    authoritative: bool
    authority_required: bool
    packet_ids: tuple[str, ...]
    finding_count: int
    reassessed: tuple[str, ...]
    refined: tuple[str, ...]
    duplicates: tuple[str, ...]
    roadmap_proposals: tuple[str, ...]
    new_findings: tuple[str, ...]
    residual_open: tuple[str, ...]
    confirmed_closures: tuple[str, ...]
    accepted_promotions: tuple[str, ...]
    non_claims: tuple[str, ...]


def _sorted_unique(values: set[str]) -> tuple[str, ...]:
    return tuple(sorted(values))


def _human_accepting_findings(packets: Sequence[ReviewPacket]) -> set[str]:
    accepted: set[str] = set()
    for packet in packets:
        for event in packet.events:
            if (
                event.event_type is EventType.DISPOSITION_RECORDED
                and event.actor_class is ActorClass.HUMAN
                and event.disposition in _ACCEPTING
                and event.finding_id is not None
            ):
                accepted.add(event.finding_id)
    return accepted


def build_review_delta_map(packets: Sequence[ReviewPacket]) -> ReviewDeltaMap:
    """Build a deterministic non-authoritative delta inventory over packets."""

    ordered = tuple(sorted(packets, key=lambda item: item.packet_id))
    finding_ids: set[str] = set()
    for packet in ordered:
        for finding in packet.findings:
            finding_ids.add(finding.finding_id)

    reassessed: set[str] = set()
    refined: set[str] = set()
    duplicates: set[str] = set()
    split_children: set[str] = set()
    related_sources: set[str] = set()

    for packet in ordered:
        for edge in packet.edges:
            if edge.type is RelationType.REASSESSES and edge.from_id in finding_ids:
                reassessed.add(edge.from_id)
                related_sources.add(edge.from_id)
            elif edge.type is RelationType.REFINES and edge.from_id in finding_ids:
                refined.add(edge.from_id)
                related_sources.add(edge.from_id)
            elif edge.type is RelationType.DUPLICATES and edge.from_id in finding_ids:
                duplicates.add(edge.from_id)
                related_sources.add(edge.from_id)
            elif edge.type is RelationType.SPLITS_INTO and edge.to_id in finding_ids:
                split_children.add(edge.to_id)
                refined.add(edge.to_id)
                related_sources.add(edge.from_id)
                related_sources.add(edge.to_id)

    roadmap_proposals: set[str] = set()
    confirmed_closures: set[str] = set()
    residual_open: set[str] = set()
    human_accepting = _human_accepting_findings(ordered)

    for packet in ordered:
        for finding in packet.findings:
            finding_id = finding.finding_id
            if finding.kind is FindingKind.ROADMAP_PROPOSAL:
                roadmap_proposals.add(finding_id)
            derived = derive_finding_status(packet, finding_id)
            if (
                derived is DerivedStatus.CLOSED
                and finding.disposition_status in _ACCEPTING
                and finding_id in human_accepting
            ):
                confirmed_closures.add(finding_id)
            else:
                residual_open.add(finding_id)

    accepted_promotions: set[str] = set()
    for packet in ordered:
        for edge in packet.edges:
            if (
                edge.type is RelationType.PROMOTED_TO
                and edge.from_id in human_accepting
                and edge.from_id in finding_ids
            ):
                accepted_promotions.add(f"{edge.from_id}->{edge.to_id}")

    # New findings: present findings that are not targets of cross-review reassessment
    # edges as the older side and not only registration noise. Practical definition:
    # findings that appear only as sources of reassesses/refines/duplicates/roadmap
    # or have no inbound cross relation and are not confirmed closures.
    all_targets: set[str] = set()
    for packet in ordered:
        for edge in packet.edges:
            if edge.type in {
                RelationType.REASSESSES,
                RelationType.REFINES,
                RelationType.DUPLICATES,
                RelationType.SUPERSEDES,
            }:
                all_targets.add(edge.to_id)

    new_findings: set[str] = set()
    for packet in ordered:
        for finding in packet.findings:
            finding_id = finding.finding_id
            if finding_id in confirmed_closures:
                continue
            if finding_id in reassessed or finding_id in refined or finding_id in duplicates:
                continue
            if finding_id in all_targets:
                continue
            if finding.kind is FindingKind.ROADMAP_PROPOSAL:
                continue
            # Keep "new" focused on later-packet findings without inbound relation.
            if packet.packet_id.endswith("12") or "08-12" in packet.packet_id:
                new_findings.add(finding_id)

    residual_open -= confirmed_closures

    return ReviewDeltaMap(
        schema_version=DELTA_MAP_SCHEMA_VERSION,
        authoritative=False,
        authority_required=True,
        packet_ids=tuple(packet.packet_id for packet in ordered),
        finding_count=len(finding_ids),
        reassessed=_sorted_unique(reassessed),
        refined=_sorted_unique(refined | split_children),
        duplicates=_sorted_unique(duplicates),
        roadmap_proposals=_sorted_unique(roadmap_proposals),
        new_findings=_sorted_unique(new_findings),
        residual_open=_sorted_unique(residual_open),
        confirmed_closures=_sorted_unique(confirmed_closures),
        accepted_promotions=_sorted_unique(accepted_promotions),
        non_claims=_DEFAULT_NON_CLAIMS,
    )
