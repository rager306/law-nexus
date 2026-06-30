from __future__ import annotations

import pytest

from law_nexus.adapters.observability.job_ledger import (
    DEFAULT_NON_CLAIM,
    JobLedgerValidationError,
)
from law_nexus.adapters.observability.source_inventory_ledger import (
    SourceInventoryLedgerContext,
    build_source_inventory_artifact_written,
    build_source_inventory_built,
    build_source_inventory_job_failed,
    build_source_inventory_job_queued,
    build_source_inventory_scan_started,
)


def _context() -> SourceInventoryLedgerContext:
    return SourceInventoryLedgerContext(
        trace_id="trace-source-inventory-1",
        correlation_id="corr-source-inventory-1",
        job_id="job-source-inventory-1",
        source_ref="law-source/consultant",
        artifact_ref="prd/parser/source_fixture_inventory.json",
        input_fingerprint="sha256:" + "1" * 64,
    )


def test_source_inventory_factory_builds_queue_and_running_records() -> None:
    queued = build_source_inventory_job_queued(_context(), ts="2026-06-30T00:00:00Z")
    running = build_source_inventory_scan_started(_context(), ts="2026-06-30T00:00:01Z")

    queued_payload = queued.to_dict()

    assert queued_payload["event_name"] == "source_inventory_job_queued"
    assert queued_payload["job_type"] == "source_inventory"
    assert queued_payload["status_after"] == "queued"
    assert queued_payload["reason_code"] == "manual_check_requested"
    assert running.status_before == "queued"
    assert running.status_after == "running"
    assert running.reason_code == "job_started"
    assert DEFAULT_NON_CLAIM in running.non_claims


def test_source_inventory_factory_builds_built_and_written_records() -> None:
    built = build_source_inventory_built(
        _context(),
        ts="2026-06-30T00:00:02Z",
        output_fingerprint="sha256:" + "2" * 64,
        produced_artifacts=("prd/parser/source_fixture_inventory.json",),
    )
    written = build_source_inventory_artifact_written(
        _context(),
        ts="2026-06-30T00:00:03Z",
        output_fingerprint="sha256:" + "3" * 64,
        produced_artifacts=("prd/parser/source_fixture_inventory.json",),
    )

    assert built.event_name == "source_inventory_built"
    assert built.status_before == "running"
    assert built.status_after == "running"
    assert written.event_name == "source_inventory_artifact_written"
    assert written.status_before == "running"
    assert written.status_after == "succeeded"
    assert written.reason_code == "artifact_written"


def test_source_inventory_factory_builds_failure_record() -> None:
    failed = build_source_inventory_job_failed(
        _context(),
        ts="2026-06-30T00:00:04Z",
        reason_code="validation_failed",
        error_code="inventory_validation_failed",
        error_class="InventoryError",
        error_message="source inventory validation failed",
        recovery_instruction="Inspect source fixture inventory inputs and rerun check.",
    )

    assert failed.event_name == "source_inventory_job_failed"
    assert failed.status_after == "failed"
    assert failed.error_code == "inventory_validation_failed"
    assert failed.recovery_instruction == "Inspect source fixture inventory inputs and rerun check."


def test_source_inventory_factory_rejects_wrong_reason_for_failure() -> None:
    with pytest.raises(JobLedgerValidationError, match="is not valid for event"):
        build_source_inventory_job_failed(
            _context(),
            ts="2026-06-30T00:00:04Z",
            reason_code="manual_check_requested",
            error_code="inventory_validation_failed",
            error_class="InventoryError",
            error_message="source inventory validation failed",
            recovery_instruction="Inspect source fixture inventory inputs and rerun check.",
        )


def test_source_inventory_factory_rejects_unportable_context_ref() -> None:
    bad_context = SourceInventoryLedgerContext(
        trace_id="trace-source-inventory-1",
        correlation_id="corr-source-inventory-1",
        job_id="job-source-inventory-1",
        source_ref="/tmp/source",
        artifact_ref="prd/parser/source_fixture_inventory.json",
        input_fingerprint="sha256:" + "1" * 64,
    )

    with pytest.raises(JobLedgerValidationError, match="source_ref must be repository-relative"):
        build_source_inventory_job_queued(bad_context, ts="2026-06-30T00:00:00Z")
