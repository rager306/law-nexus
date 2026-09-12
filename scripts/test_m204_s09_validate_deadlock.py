#!/usr/bin/env python3
"""Fail-closed, isolated SQLite fixtures for the M204/S09 validate deadlock.

The fixtures use only an in-memory database and the tracked trigger snapshot
created by T01.  They never open the live GSD database or call the validate
workflow.  Running this file directly executes the assertions, which keeps the
host verifier single-command and dependency-light.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRIGGER_PATH = ROOT / "prd/migration/rust-evidence/m204-s09-trigger-sql.json"
ABORT_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
RESULT_ABORT_MESSAGE = "attempt result requires a settled attempt"


def trigger_sql() -> tuple[str, str]:
    document = json.loads(TRIGGER_PATH.read_text(encoding="utf-8"))
    snapshots = document["snapshots"]
    return (
        snapshots["v34"]["create_trigger_sql"],
        snapshots["v42"]["create_trigger_sql"],
    )


def connection() -> sqlite3.Connection:
    """Build the smallest schema needed by the two pinned runtime triggers."""
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE workflow_execution_attempts (
            attempt_id TEXT PRIMARY KEY,
            lifecycle_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            authority_epoch INTEGER NOT NULL,
            attempt_state TEXT NOT NULL
        );
        CREATE TABLE workflow_attempt_results (
            result_id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL,
            lifecycle_id TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            authority_epoch INTEGER NOT NULL,
            outcome TEXT NOT NULL
        );
        CREATE TABLE workflow_acceptance_criteria (
            criterion_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            lifecycle_id TEXT NOT NULL,
            criterion_kind TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            authority_epoch INTEGER NOT NULL,
            supersedes_criterion_id TEXT
        );
        CREATE TABLE workflow_technical_verdicts (
            verdict_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            lifecycle_id TEXT NOT NULL,
            criterion_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            authority_epoch INTEGER NOT NULL,
            verdict TEXT NOT NULL
        );
        CREATE TABLE workflow_operations (
            operation_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            operation_type TEXT NOT NULL
        );
        """
    )
    v34, v42 = trigger_sql()
    db.executescript(v34)
    db.executescript(v42)
    return db


def seed_criterion(db: sqlite3.Connection) -> None:
    db.execute(
        """
        INSERT INTO workflow_acceptance_criteria
          (criterion_id, project_id, lifecycle_id, criterion_kind,
           project_revision, authority_epoch, supersedes_criterion_id)
        VALUES ('criterion-1', 'project-1', 'life-1', 'technical', 7, 1, NULL)
        """
    )


def verdict(db: sqlite3.Connection, *, operation_id: str = "validate-op") -> None:
    db.execute(
        """
        INSERT INTO workflow_technical_verdicts
          (verdict_id, project_id, lifecycle_id, criterion_id, attempt_id,
           operation_id, project_revision, authority_epoch, verdict)
        VALUES ('verdict-1', 'project-1', 'life-1', 'criterion-1', 'attempt-1',
                ?, 8, 1, 'needs-remediation')
        """,
        (operation_id,),
    )


def test_verdict_without_settled_attempt_aborts() -> None:
    db = connection()
    seed_criterion(db)
    try:
        verdict(db)
    except sqlite3.IntegrityError as error:
        assert str(error) == ABORT_MESSAGE, str(error)
    else:
        raise AssertionError("technical verdict without settled attempt was accepted")


def test_same_revision_settlement_still_aborts_chicken_egg() -> None:
    db = connection()
    seed_criterion(db)
    db.execute(
        """
        INSERT INTO workflow_execution_attempts
          (attempt_id, lifecycle_id, project_id, project_revision,
           authority_epoch, attempt_state)
        VALUES ('attempt-1', 'life-1', 'project-1', 8, 1, 'running')
        """
    )
    # v34 independently proves that result creation before settlement is barred.
    try:
        db.execute(
            """
            INSERT INTO workflow_attempt_results
              (result_id, attempt_id, lifecycle_id, operation_id,
               project_revision, authority_epoch, outcome)
            VALUES ('result-before-settle', 'attempt-1', 'life-1', 'validate-op', 8, 1, 'succeeded')
            """
        )
    except sqlite3.IntegrityError as error:
        assert str(error) == RESULT_ABORT_MESSAGE, str(error)
    else:
        raise AssertionError("v34 accepted a result before settlement")

    db.execute("UPDATE workflow_execution_attempts SET attempt_state = 'settled'")
    # Same-revision settlement is valid for v34, but not enough for v42's
    # older-result predicate when the operation identity is not the same.
    db.execute(
        """
        INSERT INTO workflow_attempt_results
          (result_id, attempt_id, lifecycle_id, operation_id,
           project_revision, authority_epoch, outcome)
        VALUES ('result-1', 'attempt-1', 'life-1', 'settle-op', 8, 1, 'succeeded')
        """
    )
    db.execute(
        "INSERT INTO workflow_operations VALUES ('different-op', 'project-1', 'milestone.validate')"
    )
    try:
        verdict(db, operation_id="different-op")
    except sqlite3.IntegrityError as error:
        assert str(error) == ABORT_MESSAGE, str(error)
    else:
        raise AssertionError("v42 accepted a same-revision result without the matching operation")


def test_forged_c4_pass_is_rejected_by_s08_fixture_pin() -> None:
    s08_path = ROOT / "scripts/test_m204_s08_battery.py"
    spec = importlib.util.spec_from_file_location("m204_s08_battery", s08_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load S08 fixture: {s08_path}")
    s08 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s08)
    battery: dict[str, Any] = s08.load(s08.BATTERY_PATH)
    receipt: dict[str, Any] = s08.load(s08.RECEIPT_PATH)
    forged = copy.deepcopy(battery)
    forged["c4"]["operational_acceptance"] = "pass"
    try:
        s08.reject_untrusted_battery(forged, receipt)
    except ValueError as error:
        assert str(error) == "forged operational pass over non-pass receipt"
    else:
        raise AssertionError("S08 fixture accepted forged C4 operational pass")


def main() -> None:
    test_verdict_without_settled_attempt_aborts()
    test_same_revision_settlement_still_aborts_chicken_egg()
    test_forged_c4_pass_is_rejected_by_s08_fixture_pin()
    print("S09 T02 OK: isolated triggers, chicken-egg abort, and C4 pin are fail-closed")


if __name__ == "__main__":
    main()
