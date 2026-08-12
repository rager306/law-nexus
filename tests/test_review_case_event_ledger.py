"""Append-only filesystem event ledger contracts for Review Case.

Outer adapter tests only. No product-domain semantics, no GSD mutation, and no
authority promotion claims.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DispositionStatus,
    ExecutionStatus,
    Finding,
    FindingKind,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ProofClass,
    ReviewerSeverity,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
)
from law_nexus_harness.review_case.adapters.filesystem_ledger import FilesystemEventLedger
from law_nexus_harness.review_case.adapters.pydantic_codec import (
    dump_envelope,
    dump_event,
    envelope_body_bytes,
    load_envelope,
)
from law_nexus_harness.review_case.domain import (
    ActorClass,
    EventLedgerEnvelope,
    EventType,
    ReviewEvent,
)
from law_nexus_harness.review_case.policy import replay_events
from law_nexus_harness.review_case.ports import ReviewCasePortError

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
PATH = "doc/review/review-11-08-2026.md"
PACKET_ID = "RC-2026-08-11-001"


def codes(exc: ReviewCasePortError) -> str:
    return exc.code


def disposition_event(
    event_id: str = "E-DISP-1",
    finding_id: str = "RC11-F01",
    **overrides: Any,
) -> ReviewEvent:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "event_type": EventType.DISPOSITION_RECORDED,
        "at": TS2,
        "actor_class": ActorClass.HUMAN,
        "actor_id": "human-reviewer-1",
        "finding_id": finding_id,
        "source_revision": REV,
        "rationale": "Human disposition",
        "disposition": DispositionStatus.ACCEPTED_AS_GAP,
    }
    payload.update(overrides)
    return ReviewEvent(**payload)


def base_packet() -> ReviewPacket:
    return ReviewPacket(
        packet_id=PACKET_ID,
        source=ReviewSource(
            path=PATH,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.SOURCE_VERIFIED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
        ),
        non_claims=("Non-authoritative review projection",),
        findings=(
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
        edges=(),
        events=(),
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / "doc" / "review").mkdir(parents=True)
    (root / "doc" / "review" / "review-11-08-2026.md").write_text("# review\n", encoding="utf-8")
    return root


def _forged_envelope(
    *,
    sequence: int,
    previous: str | None,
    event: ReviewEvent,
) -> EventLedgerEnvelope:
    event_bytes = dump_event(event)
    provisional = EventLedgerEnvelope(
        packet_id=PACKET_ID,
        sequence=sequence,
        previous_envelope_sha256=previous,
        event=event,
        event_sha256=hashlib.sha256(event_bytes).hexdigest(),
        source_revision=REV,
        envelope_sha256="0" * 64,
    )
    body = envelope_body_bytes(provisional)
    return EventLedgerEnvelope(
        packet_id=PACKET_ID,
        sequence=sequence,
        previous_envelope_sha256=previous,
        event=event,
        event_sha256=provisional.event_sha256,
        source_revision=REV,
        envelope_sha256=hashlib.sha256(body).hexdigest(),
    )


def test_append_and_list_preserves_chain_and_replay(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ledger = FilesystemEventLedger(root)
    first = disposition_event("E-DISP-1")
    second = disposition_event(
        "E-DISP-2",
        disposition=DispositionStatus.REJECTED,
        rationale="Second human disposition supersedes",
    )
    env1 = ledger.append(PACKET_ID, first, source_revision=REV)
    env2 = ledger.append(PACKET_ID, second, source_revision=REV)
    assert env1.sequence == 1
    assert env1.previous_envelope_sha256 is None
    assert env2.sequence == 2
    assert env2.previous_envelope_sha256 == env1.envelope_sha256
    listed = ledger.list_envelopes(PACKET_ID)
    assert listed == (env1, env2)
    path1 = (
        root
        / "prd/architecture/review-cases/packets"
        / PACKET_ID
        / "events"
        / "000001-E-DISP-1.json"
    )
    assert path1.is_file()
    durable = path1.read_bytes()
    assert load_envelope(durable) == env1
    replayed = replay_events(base_packet(), tuple(item.event for item in listed))
    assert replayed.findings[0].disposition_status is DispositionStatus.REJECTED
    assert replayed.events == (first, second)


def test_duplicate_event_id_and_invalid_root_fail_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ledger = FilesystemEventLedger(root)
    event = disposition_event()
    ledger.append(PACKET_ID, event, source_revision=REV)
    with pytest.raises(ReviewCasePortError) as exc:
        ledger.append(PACKET_ID, event, source_revision=REV)
    assert codes(exc.value) == "duplicate_event_id"
    with pytest.raises(ReviewCasePortError) as exc2:
        FilesystemEventLedger(root, packets_dir="doc/adr/review-packets")
    assert codes(exc2.value) == "invalid_store_path"
    with pytest.raises(ReviewCasePortError) as exc3:
        ledger.append("bad/id", event, source_revision=REV)
    assert codes(exc3.value) == "invalid_packet_id"


def test_gap_and_hash_tamper_are_detected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ledger = FilesystemEventLedger(root)
    env1 = ledger.append(PACKET_ID, disposition_event("E-DISP-1"), source_revision=REV)
    events_dir = root / "prd/architecture/review-cases/packets" / PACKET_ID / "events"
    forged_env = _forged_envelope(
        sequence=3,
        previous=env1.envelope_sha256,
        event=disposition_event("E-DISP-3"),
    )
    (events_dir / "000003-E-DISP-3.json").write_bytes(dump_envelope(forged_env))
    with pytest.raises(ReviewCasePortError) as exc:
        ledger.list_envelopes(PACKET_ID)
    assert codes(exc.value) == "ledger_gap_or_fork"

    clean = _repo(tmp_path / "tamper")
    ledger2 = FilesystemEventLedger(clean)
    ledger2.append(PACKET_ID, disposition_event("E-DISP-1"), source_revision=REV)
    path = (
        clean
        / "prd/architecture/review-cases/packets"
        / PACKET_ID
        / "events"
        / "000001-E-DISP-1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["event_sha256"] = "f" * 64
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(ReviewCasePortError) as exc2:
        ledger2.list_envelopes(PACKET_ID)
    assert codes(exc2.value) in {
        "event_hash_mismatch",
        "corrupt_envelope",
        "envelope_hash_mismatch",
    }


def test_symlink_and_partial_temp_are_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ledger = FilesystemEventLedger(root)
    ledger.append(PACKET_ID, disposition_event("E-DISP-1"), source_revision=REV)
    events_dir = root / "prd/architecture/review-cases/packets" / PACKET_ID / "events"
    (events_dir / ".000002-E-DISP-2.partial.json.tmp").write_text("{}", encoding="utf-8")
    listed = ledger.list_envelopes(PACKET_ID)
    assert len(listed) == 1
    target = events_dir / "000002-E-DISP-2.json"
    outside = root / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    os.symlink(outside, target)
    with pytest.raises(ReviewCasePortError) as exc:
        ledger.append(PACKET_ID, disposition_event("E-DISP-2"), source_revision=REV)
    assert codes(exc.value) in {"symlink_rejected", "ledger_fork", "corrupt_ledger"}


def test_chain_break_on_previous_hash_tamper(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ledger = FilesystemEventLedger(root)
    env1 = ledger.append(PACKET_ID, disposition_event("E-DISP-1"), source_revision=REV)
    env2 = ledger.append(PACKET_ID, disposition_event("E-DISP-2"), source_revision=REV)
    path = (
        root
        / "prd/architecture/review-cases/packets"
        / PACKET_ID
        / "events"
        / "000002-E-DISP-2.json"
    )
    fixed = _forged_envelope(
        sequence=2,
        previous="e" * 64,
        event=disposition_event("E-DISP-2"),
    )
    path.write_bytes(dump_envelope(fixed))
    with pytest.raises(ReviewCasePortError) as exc:
        ledger.list_envelopes(PACKET_ID)
    assert codes(exc.value) == "ledger_chain_break"
    assert env1.sequence == 1
    assert env2.sequence == 2
