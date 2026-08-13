"""CLI vertical-slice contracts for non-authoritative Review Case operations."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.review_case.adapters.filesystem import FilesystemReviewPacketStore
from law_nexus_harness.review_case.adapters.hashlib_adapter import HashlibContentHasher

REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
SOURCE_REL = "doc/review/review-11-08-2026.md"
SOURCE_BYTES = b"# review fixture body\n"
PACKETS_DIR = "prd/architecture/review-cases/packets"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    source = root / SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_bytes(SOURCE_BYTES)
    return root


def _register_args(root: Path, *, packet_id: str = "RC-CLI-001") -> list[str]:
    return [
        "review-case",
        "--root",
        str(root),
        "--packets-dir",
        PACKETS_DIR,
        "register",
        "--packet-id",
        packet_id,
        "--source-path",
        SOURCE_REL,
        "--reviewed-revision",
        REV,
        "--received-at",
        TS,
        "--non-claim",
        "CLI fixture non-claim",
        "--extractor-version",
        "cli-test/v1",
    ]


def test_register_validate_status_happy_path(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    code = main(_register_args(root))
    out = capsys.readouterr().out
    assert code == 0
    report = json.loads(out)
    assert report["schema_version"] == "review-case-cli-report/v1"
    assert report["status"] == "ok"
    assert report["authoritative"] is False
    assert report["authority_required"] is True
    assert report["operation"] == "review-case.register"
    assert report["result"]["packet_id"] == "RC-CLI-001"
    assert report["result"]["content_sha256"] == HashlibContentHasher().sha256(SOURCE_BYTES)

    store = FilesystemReviewPacketStore(root, packets_dir=PACKETS_DIR)
    assert store.get("RC-CLI-001").packet_id == "RC-CLI-001"

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "validate",
        ]
    )
    validate_report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert validate_report["status"] == "ok"
    assert validate_report["result"]["ok"] is True
    assert validate_report["result"]["packet_count"] == 1

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
        ]
    )
    status_report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert status_report["status"] == "ok"
    assert status_report["result"]["packets"][0][0] == "RC-CLI-001"
    assert "Does not create GSD milestones or product claims" in status_report["non_claims"]


def test_duplicate_register_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    assert main(_register_args(root)) == 0
    capsys.readouterr()
    code = main(_register_args(root))
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "duplicate_packet"


def test_missing_source_is_tool_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    (root / SOURCE_REL).unlink()
    code = main(_register_args(root))
    report = json.loads(capsys.readouterr().out)
    assert code == 2
    assert report["status"] == "tool-error"
    assert report["error"]["code"] == "source_not_found"


def test_authority_like_packet_store_path_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    args = _register_args(root)
    index = args.index("--packets-dir")
    args[index + 1] = "doc/adr/review-packets"
    code = main(args)
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "invalid_store_path"
    assert not (root / "doc/adr/review-packets").exists()


def test_invalid_path_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    args = _register_args(root)
    # replace --source-path value
    idx = args.index("--source-path")
    args[idx + 1] = "../escape.md"
    code = main(args)
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "invalid_path"


def test_source_hash_drift_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    assert main(_register_args(root)) == 0
    capsys.readouterr()
    (root / SOURCE_REL).write_bytes(b"drifted body\n")
    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "validate",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "source_hash_drift"


def test_inventory_cli_projects_fsm_residual(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    assert main(_register_args(root)) == 0
    capsys.readouterr()
    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "inventory",
            "--packet-id",
            "RC-CLI-001",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["status"] == "ok"
    assert report["operation"] == "review-case.inventory"
    assert report["authoritative"] is False
    result = report["result"]
    assert result["schema_version"] == "review-case-fsm-inventory/v1"
    assert result["packet_count"] == 1
    assert result["finding_count"] == 0 or isinstance(result["finding_count"], int)
    assert "Does not create GSD milestones or product claims" in " ".join(result["non_claims"])


def test_status_missing_packet_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
            "--packet-id",
            "RC-MISSING",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "packet_not_found"


def test_cli_has_no_disposition_or_gsd_surface() -> None:
    from law_nexus_harness import cli as cli_module

    source = Path(cli_module.__file__).read_text(encoding="utf-8").lower()
    # No command surface for human decisions or GSD mutation.
    forbidden_commands = (
        "record_human_disposition",
        "record_relation",
        "record_execution_link",
        "reopen_finding",
        "promoted_to",
        "gsd_plan",
        "gsd_task",
        "create_milestone",
        "accept_finding",
    )
    for token in forbidden_commands:
        assert token not in source
    help_ops = {"register", "validate", "status", "inventory"}
    assert help_ops.issubset(set(source.split()))


def test_status_materializes_ledger_disposition(tmp_path: Path, capsys) -> None:
    from dataclasses import replace

    from law_nexus_harness.review_case import (
        ActorClass,
        ConcernClass,
        DispositionStatus,
        EventType,
        ExecutionStatus,
        Finding,
        FindingKind,
        ProofClass,
        ReviewerSeverity,
        ReviewEvent,
        SourceSpan,
        VerificationStatus,
        materialize_review_packet,
    )
    from law_nexus_harness.review_case.adapters.filesystem_ledger import (
        FilesystemEventLedger,
    )
    from law_nexus_harness.review_case.adapters.pydantic_codec import dump_packet

    root = _repo(tmp_path)
    assert main(_register_args(root, packet_id="RC-CLI-LEDGER")) == 0
    capsys.readouterr()

    store = FilesystemReviewPacketStore(root, packets_dir=PACKETS_DIR)
    base = store.get("RC-CLI-LEDGER")
    finding = Finding(
        finding_id="RC-CLI-F01",
        kind=FindingKind.GAP,
        concern_class=ConcernClass.DESIGN,
        reviewer_severity=ReviewerSeverity.CRITICAL,
        summary="CLI materialize fixture",
        source_spans=(
            SourceSpan(
                path=SOURCE_REL,
                line_start=1,
                line_end=1,
                quote_sha256="b" * 64,
            ),
        ),
        candidate_targets=(),
        required_proof_class=ProofClass.IMPLEMENTATION,
        normalization_status=base.normalization.status,
        disposition_status=DispositionStatus.OPEN,
        execution_status=ExecutionStatus.UNPLANNED,
        verification_status=VerificationStatus.UNVERIFIED,
        non_claims=("Not an accepted requirement",),
    )
    enriched = replace(base, findings=(finding,))
    (root / PACKETS_DIR / "RC-CLI-LEDGER.json").write_bytes(dump_packet(enriched))

    ledger = FilesystemEventLedger(root, packets_dir=PACKETS_DIR)
    ledger.append(
        "RC-CLI-LEDGER",
        ReviewEvent(
            event_id="E-CLI-DISP-1",
            event_type=EventType.DISPOSITION_RECORDED,
            at="2026-08-12T00:00:00Z",
            actor_class=ActorClass.HUMAN,
            actor_id="human-reviewer-1",
            finding_id="RC-CLI-F01",
            source_revision=REV,
            rationale="Human disposition recorded outside CLI",
            disposition=DispositionStatus.ACCEPTED_AS_GAP,
        ),
        source_revision=REV,
    )

    # Base store remains open; materialization and CLI status use ledger.
    assert store.get("RC-CLI-LEDGER").findings[0].disposition_status is DispositionStatus.OPEN
    materialized = materialize_review_packet(store, ledger, "RC-CLI-LEDGER")
    assert materialized.findings[0].disposition_status is DispositionStatus.ACCEPTED_AS_GAP

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
            "--packet-id",
            "RC-CLI-LEDGER",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["status"] == "ok"
    finding_rows = report["result"]["packets"][0][4]
    assert finding_rows[0][0] == "RC-CLI-F01"
    # Accepted without proof remains derived open; finding is visible after materialize.
    assert finding_rows[0][1] == "open"

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "validate",
        ]
    )
    validate_report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert validate_report["result"]["ok"] is True
    assert validate_report["result"]["finding_count"] == 1


def test_status_fails_closed_on_ledger_chain_break(tmp_path: Path, capsys) -> None:
    import hashlib

    from law_nexus_harness.review_case import (
        ActorClass,
        EventType,
        ReviewEvent,
    )
    from law_nexus_harness.review_case.adapters.pydantic_codec import (
        dump_envelope,
        dump_event,
        envelope_body_bytes,
    )
    from law_nexus_harness.review_case.domain import EventLedgerEnvelope

    root = _repo(tmp_path)
    assert main(_register_args(root, packet_id="RC-CLI-BREAK")) == 0
    capsys.readouterr()

    event1 = ReviewEvent(
        event_id="E-BREAK-1",
        event_type=EventType.NORMALIZATION_REVIEWED,
        at="2026-08-12T00:00:00Z",
        actor_class=ActorClass.HUMAN,
        actor_id="human-reviewer-1",
        source_revision=REV,
        rationale="First normalization review",
    )
    event2 = ReviewEvent(
        event_id="E-BREAK-2",
        event_type=EventType.NORMALIZATION_REVIEWED,
        at="2026-08-12T01:00:00Z",
        actor_class=ActorClass.HUMAN,
        actor_id="human-reviewer-1",
        source_revision=REV,
        rationale="Second normalization review with broken chain",
    )

    def _env(
        *,
        sequence: int,
        previous: str | None,
        event: ReviewEvent,
    ) -> EventLedgerEnvelope:
        event_bytes = dump_event(event)
        provisional = EventLedgerEnvelope(
            packet_id="RC-CLI-BREAK",
            sequence=sequence,
            previous_envelope_sha256=previous,
            event=event,
            event_sha256=hashlib.sha256(event_bytes).hexdigest(),
            source_revision=REV,
            envelope_sha256="0" * 64,
        )
        body = envelope_body_bytes(provisional)
        return EventLedgerEnvelope(
            packet_id="RC-CLI-BREAK",
            sequence=sequence,
            previous_envelope_sha256=previous,
            event=event,
            event_sha256=provisional.event_sha256,
            source_revision=REV,
            envelope_sha256=hashlib.sha256(body).hexdigest(),
        )

    env1 = _env(sequence=1, previous=None, event=event1)
    env2 = _env(sequence=2, previous="e" * 64, event=event2)
    events_dir = root / PACKETS_DIR / "RC-CLI-BREAK" / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "000001-E-BREAK-1.json").write_bytes(dump_envelope(env1))
    (events_dir / "000002-E-BREAK-2.json").write_bytes(dump_envelope(env2))

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
            "--packet-id",
            "RC-CLI-BREAK",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "ledger_chain_break"


def test_cli_help_exposes_review_case_ops(capsys) -> None:
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["review-case", "--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "register" in help_text
    assert "validate" in help_text
    assert "status" in help_text
