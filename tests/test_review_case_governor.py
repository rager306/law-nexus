"""Governor structural integrity contracts for Review Case projections.

Process visibility only. Open findings are advisory; structural defects error.
"""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.governor import (
    check_review_case_integrity,
    get_governor_check_spec,
    run_governor,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "prd" / "architecture" / "review-cases" / "fixtures" / "review-11-12-delta-v1.json"


def _write_packet(path: Path, packet: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _minimal_packet(**overrides: object) -> dict:
    packet: dict = {
        "schema_version": "review-case/v1",
        "authoritative": False,
        "authority_required": True,
        "packet_id": "RC-GOV-001",
        "source": {
            "path": "doc/review/review-11-08-2026.md",
            "content_sha256": "a" * 64,
            "reviewed_git_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
            "received_at": "2026-08-11T10:33:40Z",
            "source_kind": "human_external",
        },
        "normalization": {
            "status": "source_verified",
            "method": "manual",
            "source_hash": "a" * 64,
        },
        "non_claims": ["Non-authoritative review projection"],
        "findings": [
            {
                "finding_id": "RC-GOV-F01",
                "kind": "gap",
                "concern_class": "design",
                "reviewer_severity": "critical",
                "summary": "Governor fixture finding",
                "source_spans": [
                    {
                        "path": "doc/review/review-11-08-2026.md",
                        "line_start": 1,
                        "line_end": 2,
                        "quote_sha256": "b" * 64,
                    }
                ],
                "candidate_targets": [],
                "required_proof_class": "implementation",
                "normalization_status": "source_verified",
                "disposition_status": "open",
                "execution_status": "unplanned",
                "verification_status": "unverified",
                "non_claims": ["Not an accepted requirement"],
            }
        ],
        "edges": [],
        "events": [],
    }
    packet.update(overrides)
    return packet


def test_check_is_registered_and_selectable() -> None:
    spec = get_governor_check_spec("review-case-integrity")
    assert spec.check_id == "review-case-integrity"
    assert spec.group == "docs"
    assert spec.default_severity == "error"
    report = run_governor(ROOT, check="review-case-integrity")
    by_id = {item.check_id: item for item in report.findings}
    assert "review-case-integrity" in by_id
    # Tracked real fixture has open findings only: structural pass + advisory open inventory.
    assert by_id["review-case-integrity"].status == "pass"
    assert by_id["review-case-integrity"].severity == "ok"
    assert "open_count=" in by_id["review-case-integrity"].observed
    assert "review-case-integrity.open-findings" in by_id
    assert by_id["review-case-integrity.open-findings"].severity == "warn"
    assert report.status == "ok"
    assert report.error_count == 0


def test_live_fixture_has_no_structural_defects_and_advisory_opens() -> None:
    assert FIXTURE.is_file()
    findings = check_review_case_integrity(ROOT)
    by_id = {item.check_id: item for item in findings}
    assert by_id["review-case-integrity"].status == "pass"
    open_finding = by_id["review-case-integrity.open-findings"]
    assert open_finding.status == "fail"
    assert open_finding.severity == "warn"
    assert "open_count=16" in open_finding.observed or "open_count=" in open_finding.observed


def test_authority_laundering_is_hard_error(tmp_path: Path) -> None:
    packet = _minimal_packet(authoritative=True)
    _write_packet(
        tmp_path / "prd/architecture/review-cases/fixtures/hostile.json",
        packet,
    )
    findings = check_review_case_integrity(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["review-case-integrity"].status == "fail"
    assert by_id["review-case-integrity"].severity == "error"
    assert "authority_laundering" in by_id["review-case-integrity"].observed


def test_orphan_promotion_is_hard_error(tmp_path: Path) -> None:
    packet = _minimal_packet(
        edges=[
            {
                "type": "promoted_to",
                "from": "RC-GOV-F01",
                "to": "TSG-006",
                "status": "accepted",
            }
        ]
    )
    _write_packet(
        tmp_path / "prd/architecture/review-cases/fixtures/orphan.json",
        packet,
    )
    findings = check_review_case_integrity(tmp_path)
    observed = findings[0].observed
    assert findings[0].severity == "error"
    assert "orphan_promotion" in observed


def test_class_mismatched_closure_is_hard_error(tmp_path: Path) -> None:
    packet = _minimal_packet(
        findings=[
            {
                "finding_id": "RC-GOV-F01",
                "kind": "gap",
                "concern_class": "design",
                "reviewer_severity": "critical",
                "summary": "Governor fixture finding",
                "source_spans": [
                    {
                        "path": "doc/review/review-11-08-2026.md",
                        "line_start": 1,
                        "line_end": 2,
                        "quote_sha256": "b" * 64,
                    }
                ],
                "candidate_targets": [],
                "required_proof_class": "implementation",
                "normalization_status": "source_verified",
                "disposition_status": "accepted_as_gap",
                "execution_status": "implemented",
                "verification_status": "passed_bounded",
                "non_claims": ["Not an accepted requirement"],
            }
        ],
        events=[
            {
                "event_id": "E-DISP-1",
                "event_type": "disposition_recorded",
                "at": "2026-08-12T00:00:00Z",
                "actor_class": "human",
                "finding_id": "RC-GOV-F01",
                "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "rationale": "human accept",
                "payload": {"disposition": "accepted_as_gap"},
            },
            {
                "event_id": "E-VER-1",
                "event_type": "verification_recorded",
                "at": "2026-08-12T01:00:00Z",
                "actor_class": "human",
                "finding_id": "RC-GOV-F01",
                "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "rationale": "docs cannot close implementation",
                "payload": {
                    "proof_class": "docs",
                    "verification_result": "passed_bounded",
                    "tested_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                    "evidence_anchors": ["tests/test_review_case_governor.py"],
                    "non_claims": ["No product claim"],
                },
            },
        ],
    )
    _write_packet(
        tmp_path / "prd/architecture/review-cases/fixtures/mismatch.json",
        packet,
    )
    findings = check_review_case_integrity(tmp_path)
    observed = findings[0].observed
    assert findings[0].severity == "error"
    assert (
        "class_mismatched_closure" in observed
        or "docs_process_cannot_close_implementation" in observed
    )


def test_source_hash_mismatch_is_hard_error(tmp_path: Path) -> None:
    packet = _minimal_packet()
    packet["normalization"]["source_hash"] = "c" * 64
    _write_packet(
        tmp_path / "prd/architecture/review-cases/fixtures/hash.json",
        packet,
    )
    findings = check_review_case_integrity(tmp_path)
    assert findings[0].severity == "error"
    assert "source_hash_mismatch" in findings[0].observed


def test_ledger_chain_break_is_hard_error(tmp_path: Path) -> None:
    events_dir = tmp_path / "prd/architecture/review-cases/packets" / "RC-GOV-001" / "events"
    events_dir.mkdir(parents=True)
    env1 = {
        "schema_version": "review-case-event-ledger/v1",
        "authoritative": False,
        "authority_required": True,
        "packet_id": "RC-GOV-001",
        "sequence": 1,
        "event": {
            "event_id": "E1",
            "event_type": "normalization_reviewed",
            "at": "2026-08-12T00:00:00Z",
            "actor_class": "human",
        },
        "event_sha256": "b" * 64,
        "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
        "envelope_sha256": "c" * 64,
    }
    env2 = {
        "schema_version": "review-case-event-ledger/v1",
        "authoritative": False,
        "authority_required": True,
        "packet_id": "RC-GOV-001",
        "sequence": 2,
        "previous_envelope_sha256": "e" * 64,
        "event": {
            "event_id": "E2",
            "event_type": "normalization_reviewed",
            "at": "2026-08-12T01:00:00Z",
            "actor_class": "human",
        },
        "event_sha256": "b" * 64,
        "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
        "envelope_sha256": "d" * 64,
    }
    (events_dir / "000001-E1.json").write_text(
        json.dumps(env1, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    (events_dir / "000002-E2.json").write_text(
        json.dumps(env2, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    findings = check_review_case_integrity(tmp_path)
    assert findings[0].severity == "error"
    assert "ledger_chain_break" in findings[0].observed


def test_open_findings_do_not_become_errors(tmp_path: Path) -> None:
    packet = _minimal_packet()
    _write_packet(
        tmp_path / "prd/architecture/review-cases/fixtures/open.json",
        packet,
    )
    findings = check_review_case_integrity(tmp_path)
    by_id = {item.check_id: item for item in findings}
    assert by_id["review-case-integrity"].status == "pass"
    assert by_id["review-case-integrity"].severity == "ok"
    assert by_id["review-case-integrity.open-findings"].severity == "warn"
    report = run_governor(tmp_path, check="review-case-integrity")
    assert report.status == "ok"
    assert report.error_count == 0
    assert report.warn_count == 1
