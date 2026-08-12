"""Pure non-authoritative two-review delta projection contracts.

No filesystem I/O, codecs, CLI, Governor, GSD, or product-domain semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    ProofClass,
    RelationStatus,
    RelationType,
    ReviewEdge,
    ReviewerSeverity,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
)
from law_nexus_harness.review_case.adapters.pydantic_codec import load_packets
from law_nexus_harness.review_case.delta import (
    DELTA_MAP_SCHEMA_VERSION,
    build_review_delta_map,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
PATH_11 = "doc/review/review-11-08-2026.md"
PATH_12 = "doc/review/review-12-08-2026.md"
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "prd/architecture/review-cases/fixtures/review-11-12-delta-v1.json"
)


def finding(
    finding_id: str,
    *,
    path: str = PATH_11,
    kind: FindingKind = FindingKind.GAP,
    **overrides: Any,
) -> Finding:
    payload: dict[str, Any] = {
        "finding_id": finding_id,
        "kind": kind,
        "concern_class": ConcernClass.DESIGN,
        "reviewer_severity": ReviewerSeverity.CRITICAL,
        "summary": f"Summary for {finding_id}",
        "source_spans": (
            SourceSpan(
                path=path,
                line_start=10,
                line_end=20,
                quote_sha256=HASH_B,
                heading="# Gap",
            ),
        ),
        "candidate_targets": (),
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
    packet_id: str,
    path: str,
    findings: tuple[Finding, ...],
    edges: tuple[ReviewEdge, ...] = (),
    events: tuple[ReviewEvent, ...] = (),
) -> ReviewPacket:
    return ReviewPacket(
        packet_id=packet_id,
        source=ReviewSource(
            path=path,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS if "11" in packet_id else TS2,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.SOURCE_VERIFIED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
        ),
        non_claims=("Non-authoritative review projection",),
        findings=findings,
        edges=edges,
        events=events
        or (
            ReviewEvent(
                event_id=f"{packet_id}:packet_registered",
                event_type=EventType.PACKET_REGISTERED,
                at=TS,
                actor_class=ActorClass.TOOL,
                source_revision=REV,
                rationale="Register immutable review source as draft packet",
            ),
        ),
    )


def test_delta_map_is_non_authoritative_and_empty_without_human_closures() -> None:
    p11 = packet(
        "RC-11",
        PATH_11,
        findings=(finding("RC11-F01"), finding("RC11-F03")),
        edges=(
            ReviewEdge(
                type=RelationType.MAPS_TO,
                from_id="RC11-F01",
                to_id="TSG-001",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    p12 = packet(
        "RC-12",
        PATH_12,
        findings=(
            finding("RC12-F01", path=PATH_12),
            finding("RC12-F03", path=PATH_12),
            finding(
                "RC12-F19",
                path=PATH_12,
                kind=FindingKind.ROADMAP_PROPOSAL,
            ),
        ),
        edges=(
            ReviewEdge(
                type=RelationType.REASSESSES,
                from_id="RC12-F01",
                to_id="RC11-F01",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.DUPLICATES,
                from_id="RC12-F03",
                to_id="RC11-F03",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    delta = build_review_delta_map((p11, p12))
    assert delta.schema_version == DELTA_MAP_SCHEMA_VERSION
    assert delta.authoritative is False
    assert delta.authority_required is True
    assert delta.confirmed_closures == ()
    assert delta.accepted_promotions == ()
    assert "RC12-F01" in delta.reassessed
    assert "RC12-F03" in delta.duplicates
    assert "RC12-F19" in delta.roadmap_proposals
    assert "RC11-F01" in delta.residual_open
    assert "RC11-F03" in delta.residual_open
    assert any("non-authoritative" in item.lower() for item in delta.non_claims)


def test_fixture_delta_classifies_known_cross_review_edges() -> None:
    packets = load_packets(FIXTURE.read_bytes())
    delta = build_review_delta_map(packets)
    assert delta.confirmed_closures == ()
    assert delta.accepted_promotions == ()
    assert "RC12-F01" in delta.reassessed
    assert "RC12-F05" in delta.reassessed
    assert "RC12-F05" in delta.refined
    assert "RC12-F17" in delta.refined
    assert "RC12-F03" in delta.duplicates
    assert "RC12-F19" in delta.roadmap_proposals
    # All 16 findings remain residual open until human disposition.
    assert len(delta.residual_open) == 16
    assert set(delta.residual_open) == {
        finding.finding_id for packet in packets for finding in packet.findings
    }


def test_confirmed_closure_requires_human_accepting_and_passing_verification() -> None:
    base = packet(
        "RC-11",
        PATH_11,
        findings=(
            finding(
                "RC11-F01",
                disposition_status=DispositionStatus.ACCEPTED_AS_GAP,
                execution_status=ExecutionStatus.IMPLEMENTED,
                verification_status=VerificationStatus.PASSED_BOUNDED,
            ),
        ),
        events=(
            ReviewEvent(
                event_id="E-REG",
                event_type=EventType.PACKET_REGISTERED,
                at=TS,
                actor_class=ActorClass.TOOL,
                source_revision=REV,
                rationale="register",
            ),
            ReviewEvent(
                event_id="E-DISP",
                event_type=EventType.DISPOSITION_RECORDED,
                at=TS2,
                actor_class=ActorClass.HUMAN,
                actor_id="human-1",
                finding_id="RC11-F01",
                source_revision=REV,
                rationale="accepted",
                disposition=DispositionStatus.ACCEPTED_AS_GAP,
            ),
            ReviewEvent(
                event_id="E-VER",
                event_type=EventType.VERIFICATION_RECORDED,
                at=TS2,
                actor_class=ActorClass.HUMAN,
                actor_id="human-1",
                finding_id="RC11-F01",
                source_revision=REV,
                rationale="proof",
                proof_class=ProofClass.IMPLEMENTATION,
                verification_result=VerificationStatus.PASSED_BOUNDED,
                tested_revision=REV,
                evidence_anchors=("tests/test_review_case_delta_map.py",),
                completed_scope=("closed",),
                residual_scope=(),
                non_claims=("No product claim",),
            ),
        ),
    )
    delta = build_review_delta_map((base,))
    assert delta.confirmed_closures == ("RC11-F01",)
    assert "RC11-F01" not in delta.residual_open


def test_promoted_to_without_human_accepting_is_not_accepted_promotion() -> None:
    # maps_to remains candidate-only; accepted_promotions requires human accepting
    # disposition plus promoted_to history.
    safe = packet(
        "RC-11",
        PATH_11,
        findings=(finding("RC11-F01"),),
        edges=(
            ReviewEdge(
                type=RelationType.MAPS_TO,
                from_id="RC11-F01",
                to_id="TSG-006",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    delta = build_review_delta_map((safe,))
    assert delta.accepted_promotions == ()
    assert "RC11-F01" in delta.residual_open


def test_split_children_are_refined_not_closures() -> None:
    base = packet(
        "RC-11",
        PATH_11,
        findings=(
            finding("RC11-F04"),
            finding("RC11-F04a"),
            finding("RC11-F04b"),
        ),
        edges=(
            ReviewEdge(
                type=RelationType.SPLITS_INTO,
                from_id="RC11-F04",
                to_id="RC11-F04a",
                status=RelationStatus.CANDIDATE,
            ),
            ReviewEdge(
                type=RelationType.SPLITS_INTO,
                from_id="RC11-F04",
                to_id="RC11-F04b",
                status=RelationStatus.CANDIDATE,
            ),
        ),
    )
    delta = build_review_delta_map((base,))
    assert "RC11-F04a" in delta.refined or "RC11-F04" in delta.refined
    assert delta.confirmed_closures == ()
    assert len(delta.residual_open) == 3


def test_tracked_delta_map_artifact_matches_pure_projection() -> None:
    artifact = (
        Path(__file__).resolve().parents[1]
        / "prd/architecture/review-cases/review-11-12-delta-map.md"
    )
    assert artifact.is_file()
    text = artifact.read_text(encoding="utf-8")
    assert "authoritative = false" in text
    assert "confirmed_closures = []" in text
    assert "accepted_promotions = []" in text
    assert "Non-authoritative" in text or "non-authoritative" in text.lower()
    packets = load_packets(FIXTURE.read_bytes())
    delta = build_review_delta_map(packets)
    assert delta.confirmed_closures == ()
    assert delta.accepted_promotions == ()
    assert len(delta.residual_open) == 16
    for finding_id in delta.residual_open:
        assert finding_id in text
    for finding_id in delta.reassessed:
        assert finding_id in text
    for finding_id in delta.duplicates:
        assert finding_id in text
    assert "RC12-F19" in text
    # No invented acceptance language for real findings.
    assert "confirmed_closures = []" in text
    assert "M166–M176" in text or "M166-M176" in text or "roadmap_proposal" in text


def test_delta_module_is_pure_stdlib_only() -> None:
    import ast
    from pathlib import Path

    path = Path("src/law_nexus_harness/review_case/delta.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"pydantic", "pathlib", "argparse", "subprocess", "gsd"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in forbidden
