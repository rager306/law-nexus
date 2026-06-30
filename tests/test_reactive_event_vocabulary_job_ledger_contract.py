from __future__ import annotations

from pathlib import Path

CONTRACT_PATH = Path("prd/architecture/reactive-event-vocabulary-job-ledger-contract.md")


def test_reactive_event_vocabulary_contract_records_required_guardrails() -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")

    required_phrases = [
        "**Status:** [proposed] architecture contract",
        "D101",
        "R060",
        "R061",
        "R062",
        "First pilot: source inventory",
        "Second family: parser golden-case jobs",
        "source_inventory_job_queued",
        "source_inventory_job_failed",
        "parser_golden_job_queued",
        "parser_golden_regression_detected",
        "Job lifecycle state machine",
        "queued -> running -> succeeded",
        "Invalid transitions",
        "Reason-code taxonomy",
        "Local job ledger record schema",
        "law-nexus-job-ledger/v1",
        "trace_id",
        "correlation_id",
        "job_id",
        "reason_code",
        "input_fingerprint",
        "output_fingerprint",
        "redaction_applied",
        "Trace bundle shape",
        "Storage option comparison",
        "Append-only JSONL",
        "Idempotency and single-writer rules",
        "Redaction and portability rules",
        "Adoption ladder",
        "Validator expectations",
        "Event logs and job ledger records are operational/debug evidence only",
        "This contract does **not** prove",
        "FalkorDB production readiness",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]

    assert missing == []
