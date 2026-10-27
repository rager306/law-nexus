"""TDD contracts for the typed workflow-state adapter (MIGRATION.md section 4.1)."""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from law_nexus_harness.governor import check_workflow_state_surface
from law_nexus_harness.preflight import _workflow_state_surface_check
from law_nexus_harness.workflow_state import (
    CUTOVER_MARKER_RELATIVE_PATH,
    LEGACY_SURFACE_CHECKS,
    NO_RUNTIME_INFO,
    RUNTIME_DECLARATION_RELATIVE_PATH,
    STATUS_RUNTIME_SHIM_RELATIVE_PATH,
    WORKFLOW_STATE_SCHEMA_VERSION,
    LegacySurface,
    RuntimeResolution,
    WorkflowStateKind,
    WorkflowStateReport,
    read_legacy_gsd_snapshot,
    read_legacy_surface,
    read_workflow_state,
    workflow_readiness,
)

# Pinned Path runtime digest from .ai/versions.json (path.runtimeDigest).
PINNED_RUNTIME_DIGEST = "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"
# Old experiment runtime digest from the local runtime cache; used only as a
# distinct mismatch fixture.
OTHER_RUNTIME_DIGEST = "aa93973ec660712b8a38f6c49b6c480ecae48cfd854c25df765bbb0425029a49"
PINNED_RUNTIME_VERSION = "1.6.2"

FRESH_STATE_TEXT = (
    "# GSD Path State\n\n**Active Milestone:** M001-bootstrap\n**Phase:** define/active\n"
)


def write_cutover_marker(
    root: Path,
    *,
    cutover: bool = False,
    payload: dict[str, Any] | None = None,
    raw: str | None = None,
) -> None:
    path = root / CUTOVER_MARKER_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
        return
    if payload is None:
        payload = {"schema": 1, "backend": "gsd-path", "cutover": cutover}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_runtime_declaration(
    root: Path,
    *,
    version: str = PINNED_RUNTIME_VERSION,
    digest: str = PINNED_RUNTIME_DIGEST,
    raw: str | None = None,
) -> None:
    path = root / RUNTIME_DECLARATION_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
        return
    path.write_text(
        json.dumps({"schema": "gsd-path/runtime/v1", "version": version, "digest": digest}),
        encoding="utf-8",
    )


def write_project_state(root: Path, text: str = FRESH_STATE_TEXT) -> None:
    project = root / ".project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "STATE.md").write_text(text, encoding="utf-8")


def write_legacy_gsd_state(root: Path) -> None:
    gsd = root / ".gsd"
    gsd.mkdir(parents=True, exist_ok=True)
    (gsd / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Active Milestone:** M225-qrwdfv: Reference knowledge layer in Rust\n"
        "**Active Slice:** None\n"
        "**Phase:** blocked\n"
        "\n## Milestone Registry\n",
        encoding="utf-8",
    )


def resolved_runtime_resolver(
    *,
    digest: str = PINNED_RUNTIME_DIGEST,
    version: str = PINNED_RUNTIME_VERSION,
) -> Callable[[Path], RuntimeResolution]:
    def resolver(root: Path) -> RuntimeResolution:
        return RuntimeResolution(
            available=True,
            runtime_path=root / "runtime-cache" / digest,
            version=version,
            digest=digest,
            detail="",
        )

    return resolver


# Verbatim payload of the pinned Path 1.6.2 helper on a probe repo:
#     python3 -B "<runtime>/pipeline_state.py" status --repo /tmp/wf-probe3
# The probe STATE.md was build/active on branch gsd-path/M001, so the router
# routes the build phase. Only `schema`, `state`, and `route` are consumed by
# the adapter; the remaining keys are kept so the fixture stays a real payload.
NATIVE_STATUS_VALID: dict[str, Any] = {
    "advance": False,
    "completion": {"status": "not-shipped"},
    "default_branch": "main",
    "git": {
        "ancestor_of_origin_main": False,
        "branch": "gsd-path/M001",
        "dirty": [],
        "head": "8e9454a45f6d2a7707222f96fa999faee4ef8767",
        "origin_branch": None,
        "origin_main": None,
        "published": False,
        "subject": "init",
    },
    "handoff": {
        "next": "Invoke $gsd-path to continue with build.",
        "outcome": "build/active",
        "phase_next": "Invoke $gsd-path to continue with build.",
        "review": "/tmp/wf-probe3/.project/STATE.md",
        "router_next": "Continue with build; honor its input and approval gates.",
    },
    "journals": {
        "abandon": None,
        "bind_next": None,
        "checkpoint": None,
        "collect_artifact": None,
        "promotion": None,
        "shipment": None,
        "undo": None,
    },
    "lookahead": False,
    "next_skill": "gsd-path-build",
    "path": "/tmp/wf-probe3/.project/STATE.md",
    "pending_answers": [],
    "pending_error": None,
    "route": {
        "action": "run-phase",
        "mode": "recovery",
        "phase": "build",
        "reason": "state is build/active",
    },
    "schema": "gsd-path/status/v1",
    "state": {
        "archive": None,
        "branch": "gsd-path/M001",
        "integration": "direct",
        "integration_default": "direct",
        "integration_source": "default",
        "milestone": "001-probe",
        "phase": "build",
        "pipeline": "gsd-path/v2",
        "project": "probe",
        "status": "active",
    },
}


def native_status(payload: dict[str, Any]) -> Callable[[Path, Path], dict[str, Any]]:
    def runner(root: Path, runtime_path: Path) -> dict[str, Any]:
        return payload

    return runner


def ok_native_status(root: Path, runtime_path: Path) -> dict[str, Any]:
    return NATIVE_STATUS_VALID


def blocking_native_status(reason: str) -> Callable[[Path, Path], dict[str, Any]]:
    # Verbatim shape of the pinned helper's own block route:
    #     {"route": {"action": "block",
    #                "reason": "current branch main != STATE.branch gsd-path/M001"}}
    payload = copy.deepcopy(NATIVE_STATUS_VALID)
    payload["route"] = {"action": "block", "reason": reason}
    return native_status(payload)


# Recorded proof of the shipped integrated M001 main (task T002 Context, probe
# of 2026-10-27 on a fresh named-branch checkout of 4e0cd4db with the restored
# runtime; the hashes are real objects in this repository's history):
#     ship commit        886a36a8f9ed77ad315f4b16fee0cdbc68bf4d02
#     integrate/landing  4e0cd4dba087b3a0dfaacb4cc6a443f1bc5d495f (= origin/main tip)
#     tag                milestone/001-001-native-workflow-acceptance
SHIP_COMMIT = "886a36a8f9ed77ad315f4b16fee0cdbc68bf4d02"
INTEGRATE_COMMIT = "4e0cd4dba087b3a0dfaacb4cc6a443f1bc5d495f"
M001_ARCHIVE = ".project/archive/001-001-native-workflow-acceptance"
M001_BLOCK_REASON = "current branch main != STATE.branch gsd-path/M001"


def shipped_main_status() -> dict[str, Any]:
    return copy.deepcopy(NATIVE_STATUS_SHIPPED_MAIN)


# Shape of the pinned helper on integrated M001 main, composed from the probe
# facts above on the same verbatim key set as NATIVE_STATUS_VALID: the router
# owns the retired bound branch away from main (block), while the completion
# verdict proves the shipped/done state and its integration evidence.
NATIVE_STATUS_SHIPPED_MAIN: dict[str, Any] = {
    "advance": False,
    "completion": {
        "status": "verified",
        "proof": {
            "archive": M001_ARCHIVE,
            "commit": SHIP_COMMIT,
            "integrate": INTEGRATE_COMMIT,
            "landing": INTEGRATE_COMMIT,
            "base": INTEGRATE_COMMIT,
            "mode": "direct",
            "tag": "milestone/001-001-native-workflow-acceptance",
        },
    },
    "default_branch": "main",
    "git": {
        "ancestor_of_origin_main": False,
        "branch": "main",
        "dirty": [],
        "head": INTEGRATE_COMMIT,
        "origin_branch": INTEGRATE_COMMIT,
        "origin_main": INTEGRATE_COMMIT,
        "published": True,
        "subject": "integrate: M001 — merge gsd-path/M001 into main",
    },
    "handoff": {
        "next": f"block: {M001_BLOCK_REASON}",
        "outcome": "shipped/done",
        "phase_next": f"block: {M001_BLOCK_REASON}",
        "review": "/tmp/wf-probe3/.project/STATE.md",
        "router_next": f"block: {M001_BLOCK_REASON}",
    },
    "journals": {
        "abandon": None,
        "bind_next": None,
        "checkpoint": None,
        "collect_artifact": None,
        "promotion": None,
        "shipment": None,
        "undo": None,
    },
    "lookahead": False,
    "next_skill": "gsd-path",
    "path": "/tmp/wf-probe3/.project/STATE.md",
    "pending_answers": [],
    "pending_error": None,
    "route": {"action": "block", "reason": M001_BLOCK_REASON},
    "schema": "gsd-path/status/v1",
    "state": {
        "archive": M001_ARCHIVE,
        "branch": "gsd-path/M001",
        "integration": "direct",
        "integration_default": "direct",
        "integration_source": "default",
        "milestone": "001-native-workflow-acceptance",
        "phase": "shipped",
        "pipeline": "gsd-path/v2",
        "project": "probe",
        "status": "done",
    },
}


def write_operational_surface_files(root: Path) -> None:
    """Marker, STATE.md, and declaration: the files every native-status test needs."""

    write_cutover_marker(root, cutover=True)
    write_project_state(root)
    write_runtime_declaration(root)


def write_shipped_main_real_stack(root: Path) -> None:
    """Fixture that reaches the governor/preflight checks through the real stack.

    The default runtime resolver runs the tracked shim, and the default native
    runner executes ``pipeline_state.py`` from the resolved runtime directory,
    so both are faked in the checkout the way
    ``test_default_resolver_runs_real_shim_end_to_end`` fakes the shim: a
    runtime cache directory whose helper prints one fixed status payload. No
    network and no real runtime store are involved.
    """

    write_operational_surface_files(root)
    runtime_dir = root / "runtime-cache" / PINNED_RUNTIME_DIGEST
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "manifest.json").write_text(
        json.dumps({"version": PINNED_RUNTIME_VERSION, "files": {"pipeline_state.py": "0" * 64}}),
        encoding="utf-8",
    )
    payload_text = json.dumps(shipped_main_status(), sort_keys=True)
    (runtime_dir / "pipeline_state.py").write_text(
        f"import sys\nsys.stdout.write({payload_text!r})\n",
        encoding="utf-8",
    )
    shim = root / STATUS_RUNTIME_SHIM_RELATIVE_PATH
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(f"print({runtime_dir.as_posix()!r})\n", encoding="utf-8")


def test_bootstrap_mode_without_project_is_bootstrap_not_cut_over(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=False)

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER
    assert workflow_readiness(report) == "bootstrap-not-cut-over"
    assert report.legacy_gsd_present is False
    assert report.evidence == (CUTOVER_MARKER_RELATIVE_PATH,)
    assert report.schema_version == WORKFLOW_STATE_SCHEMA_VERSION


def test_operational_mode_without_project_is_missing_state(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.MISSING_STATE
    assert workflow_readiness(report) == "blocked"
    assert ".project" in report.evidence


def test_missing_cutover_marker_is_invalid_schema(tmp_path: Path) -> None:
    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.INVALID_SCHEMA
    assert report.detail == "cutover marker missing"
    assert report.evidence == (CUTOVER_MARKER_RELATIVE_PATH,)


def test_invalid_cutover_marker_payloads_are_invalid_schema(tmp_path: Path) -> None:
    cases: list[dict[str, Any] | str] = [
        "{not json",
        {"schema": 2, "backend": "gsd-path", "cutover": False},
        {"schema": 1, "backend": "gsd-pi", "cutover": False},
        {"schema": 1, "backend": "gsd-path", "cutover": "false"},
        {"schema": 1, "backend": "gsd-path", "cutover": False, "extra": 1},
        {"schema": True, "backend": "gsd-path", "cutover": False},
    ]
    for case in cases:
        if isinstance(case, str):
            write_cutover_marker(tmp_path, raw=case)
        else:
            write_cutover_marker(tmp_path, payload=case)
        report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, case
        assert report.detail, case
        assert workflow_readiness(report) == "blocked", case


def test_orphan_project_without_state_md_is_invalid_schema(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    (tmp_path / ".project").mkdir()

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.INVALID_SCHEMA
    assert "orphan" in report.observed.lower()


def test_symlinked_project_surfaces_are_invalid_schema(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    outside = tmp_path / "outside-state.md"
    outside.write_text(FRESH_STATE_TEXT, encoding="utf-8")
    (tmp_path / ".project" / "STATE.md").unlink()
    os.symlink(outside, tmp_path / ".project" / "STATE.md")

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.INVALID_SCHEMA
    assert report.detail == "symlinked STATE.md"


def test_invalid_runtime_declaration_is_invalid_schema(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    cases = [
        "{not json",
        json.dumps(
            {"schema": "gsd-path/runtime/v2", "version": "1.6.2", "digest": PINNED_RUNTIME_DIGEST}
        ),
        json.dumps({"schema": "gsd-path/runtime/v1", "version": "", "digest": "0" * 64}),
        json.dumps(
            {
                "schema": "gsd-path/runtime/v1",
                "version": "1.6.2",
                "digest": "not-a-real-digest",
            }
        ),
    ]
    for case in cases:
        write_runtime_declaration(tmp_path, raw=case)
        report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, case
        assert report.evidence == (RUNTIME_DECLARATION_RELATIVE_PATH,), case


def test_missing_declaration_is_runtime_unavailable(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.RUNTIME_UNAVAILABLE
    assert report.detail == "declaration missing"
    assert report.runtime.path is None


def test_missing_shim_is_runtime_unavailable(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(tmp_path)

    assert report.kind is WorkflowStateKind.RUNTIME_UNAVAILABLE
    assert report.detail == "launcher shim missing"
    assert report.runtime.version == PINNED_RUNTIME_VERSION
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.path is None
    assert STATUS_RUNTIME_SHIM_RELATIVE_PATH in report.evidence


def test_shim_failure_maps_stderr_head_into_detail(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)
    shim = tmp_path / STATUS_RUNTIME_SHIM_RELATIVE_PATH
    shim.write_text(
        "import sys\n"
        "sys.stderr.write('Runtime 1.6.2 is unavailable or invalid at /cache\\n')\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )

    report = read_workflow_state(tmp_path)

    assert report.kind is WorkflowStateKind.RUNTIME_UNAVAILABLE
    assert "exit 3" in report.detail
    assert "unavailable or invalid" in report.detail


def test_shim_without_output_is_runtime_unavailable(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)
    (tmp_path / STATUS_RUNTIME_SHIM_RELATIVE_PATH).write_text("", encoding="utf-8")

    report = read_workflow_state(tmp_path)

    assert report.kind is WorkflowStateKind.RUNTIME_UNAVAILABLE
    assert "did not return an absolute runtime directory" in report.detail


def test_runtime_digest_mismatch_is_runtime_mismatch(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path, runtime_resolver=resolved_runtime_resolver(digest=OTHER_RUNTIME_DIGEST)
    )

    assert report.kind is WorkflowStateKind.RUNTIME_MISMATCH
    assert PINNED_RUNTIME_DIGEST in report.detail
    assert OTHER_RUNTIME_DIGEST in report.detail
    assert report.runtime.digest == OTHER_RUNTIME_DIGEST
    assert workflow_readiness(report) == "blocked"


def test_runtime_version_mismatch_is_runtime_mismatch(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path, runtime_resolver=resolved_runtime_resolver(version="1.5.0")
    )

    assert report.kind is WorkflowStateKind.RUNTIME_MISMATCH
    assert "version=1.5.0" in report.detail


def test_conflicting_ownership_reasons_map_from_native_status(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)
    for reason in (
        "branch-mismatch",
        "ownership",
        "partial-transaction",
        "stale-source",
        "writer-conflict",
    ):
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=blocking_native_status(reason),
        )
        assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP, reason
        assert reason in report.detail
        assert workflow_readiness(report) == "blocked"


def test_real_native_block_route_maps_to_conflicting_ownership(tmp_path: Path) -> None:
    """The pinned helper's own block reason is the reason the adapter reports."""
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=blocking_native_status(
            "current branch main != STATE.branch gsd-path/M001"
        ),
    )

    assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP
    assert "current branch main != STATE.branch gsd-path/M001" in report.detail
    assert workflow_readiness(report) == "blocked"


def test_block_route_reason_is_reported_verbatim(tmp_path: Path) -> None:
    """The helper's block reason is free text; the adapter quotes it, not maps it."""
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    reason = "ship is blocked without valid PATCH-FINDINGS.md"

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=blocking_native_status(reason),
    )

    assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP
    assert report.detail == f"native status route=block: {reason}"
    assert "block" in report.observed


def test_shipped_integrated_block_payload_classifies_honest_non_blocking(
    tmp_path: Path,
) -> None:
    """Contract A: verified shipped/done + block is SHIPPED_INTEGRATED, not a defect.

    The helper validated the shipped STATE.md and its integration proof; the
    block is only branch ownership away from the retired bound branch on
    integrated main. AGENTS.md's plain-prompt re-entry already treats that
    state as normal operation - the typed adapter must classify it honestly.
    """
    write_operational_surface_files(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=native_status(shipped_main_status()),
    )

    assert report.kind is WorkflowStateKind.SHIPPED_INTEGRATED
    assert report.kind.value == "shipped-integrated"
    assert workflow_readiness(report) == "operational"
    assert report.remediation == "none"
    # Observed names the shipped/done outcome and the payload's archive path.
    assert "outcome shipped/done" in report.observed
    assert M001_ARCHIVE in report.observed
    assert report.detail == f"native status route=block: {M001_BLOCK_REASON}"
    assert report.runtime.version == PINNED_RUNTIME_VERSION
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.path is not None
    # The shipped milestone is archived, not current: no native identity.
    payload = report.to_dict()
    assert payload["kind"] == "shipped-integrated"
    assert payload["native_milestone"] is None
    assert payload["native_phase"] is None
    assert json.loads(report.to_json())["kind"] == "shipped-integrated"
    assert payload["schema_version"] == WORKFLOW_STATE_SCHEMA_VERSION


def test_shipped_integrated_predicate_requires_every_condition(tmp_path: Path) -> None:
    """Flipping any one predicate fact falls back to the fail-closed kind (N2, E3).

    A foreign bound branch or an active state never reads as shipped proof:
    the differing payloads carry an unverified/not-shipped completion or
    active phases, so the narrow predicate cannot swallow them, and every
    fallback keeps the conflicting-ownership observed/remediation unchanged.
    """
    write_operational_surface_files(tmp_path)

    def flipped(label: str) -> dict[str, Any]:
        payload = shipped_main_status()
        if label == "route.resume-checkpoint":
            payload["route"] = {
                "action": "resume-checkpoint",
                "reason": "a journaled plan or roadmap approval is incomplete",
            }
        elif label == "completion-unverified":
            payload["completion"] = {
                "status": "unverified",
                "reason": "published refs differ from local integration evidence",
            }
        elif label == "completion-not-shipped":
            payload["completion"] = {"status": "not-shipped"}
        elif label == "state-phase-build":
            payload["state"]["phase"] = "build"
            payload["state"]["status"] = "active"
        elif label == "state-status-active":
            payload["state"]["status"] = "active"
        return payload

    for label in (
        "route.resume-checkpoint",
        "completion-unverified",
        "completion-not-shipped",
        "state-phase-build",
        "state-status-active",
    ):
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(flipped(label)),
        )
        assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP, label
        assert workflow_readiness(report) == "blocked", label
        assert report.remediation != "none", label
        assert "Follow the native Path recovery flow" in report.remediation, label
        assert report.observed.startswith(
            "Native status validated STATE.md but routes a native recovery step"
        ), label


def test_shipped_integrated_report_carries_no_current_identity(tmp_path: Path) -> None:
    """Only OPERATIONAL_VALID names a current milestone and phase (kind rule).

    The shipped payload DOES carry state.milestone and state.phase, so their
    absence on the report proves the rule: the archived milestone is not a
    current one.
    """
    write_operational_surface_files(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=native_status(shipped_main_status()),
    )

    assert report.kind is WorkflowStateKind.SHIPPED_INTEGRATED
    assert report.native_milestone is None
    assert report.native_phase is None


def test_wrong_typed_completion_fails_closed(tmp_path: Path) -> None:
    """A present-but-wrongly-typed completion is a broken payload, not a pass."""
    write_operational_surface_files(tmp_path)

    cases: list[tuple[Any, str]] = [
        ("verified", "completion must be an object when present, got str"),
        (7, "completion must be an object when present, got int"),
        ({"status": 7}, "completion.status must be a string when present"),
        ({"status": ["verified"]}, "completion.status must be a string when present"),
    ]
    for bad_completion, expected_detail in cases:
        payload = shipped_main_status()
        payload["completion"] = bad_completion
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, bad_completion
        assert workflow_readiness(report) == "blocked", bad_completion
        assert expected_detail in report.detail, bad_completion


def test_completion_absent_or_null_is_never_shipped_proof(tmp_path: Path) -> None:
    """No completion verdict means no integration proof: fail closed, not shipped."""
    write_operational_surface_files(tmp_path)

    without_completion = shipped_main_status()
    del without_completion["completion"]
    null_completion = shipped_main_status()
    null_completion["completion"] = None

    for payload in (without_completion, null_completion):
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP, payload["state"]
        assert workflow_readiness(report) == "blocked"


def test_wrong_typed_state_predicate_fields_fail_closed(tmp_path: Path) -> None:
    """state.status and state.archive feed the shipped predicate: same E9 rule."""
    write_operational_surface_files(tmp_path)

    cases: list[tuple[str, Any]] = [
        ("status", 7),
        ("status", True),
        ("archive", [M001_ARCHIVE]),
        ("archive", {"path": M001_ARCHIVE}),
    ]
    for field, bad_value in cases:
        payload = shipped_main_status()
        payload["state"][field] = bad_value
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, (field, bad_value)
        assert workflow_readiness(report) == "blocked", (field, bad_value)
        assert f"state.{field}" in report.detail, (field, bad_value)
        assert "must be a string when present" in report.detail, (field, bad_value)


def test_shipped_integrated_governor_finding_pins_contract_a(tmp_path: Path) -> None:
    """The governor surface check passes with rule workflow-state-surface.shipped."""
    write_shipped_main_real_stack(tmp_path)

    findings = check_workflow_state_surface(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "workflow-state-surface"
    assert finding.status == "pass"
    assert finding.severity == "ok"
    assert finding.rule_id == "workflow-state-surface.shipped"
    assert finding.remediation == "none"
    assert finding.observed.startswith("kind=shipped-integrated;")
    assert M001_ARCHIVE in finding.observed
    assert [evidence.path for evidence in finding.evidence] == [".project/STATE.md"]


def test_shipped_integrated_preflight_check_pins_contract_a(tmp_path: Path) -> None:
    """The preflight surface check passes with state=shipped-integrated + archive."""
    write_shipped_main_real_stack(tmp_path)

    check = _workflow_state_surface_check(tmp_path)

    assert check.check_id == "workflow-state-surface"
    assert check.status == "pass"
    assert check.severity == "ok"
    assert check.remediation == "none"
    assert "state=shipped-integrated" in check.observed
    assert M001_ARCHIVE in check.observed


def test_malformed_native_status_payloads_are_invalid_schema(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    def payload_case(payload: Any) -> Callable[[Path, Path], Any]:
        def runner(root: Path, runtime_path: Path) -> Any:
            return payload

        return runner

    without_route = copy.deepcopy(NATIVE_STATUS_VALID)
    del without_route["route"]
    without_state = copy.deepcopy(NATIVE_STATUS_VALID)
    del without_state["state"]
    wrong_schema = copy.deepcopy(NATIVE_STATUS_VALID)
    wrong_schema["schema"] = "gsd-path/status/v0"
    non_string_action = copy.deepcopy(NATIVE_STATUS_VALID)
    non_string_action["route"] = {"action": None}
    empty_state = copy.deepcopy(NATIVE_STATUS_VALID)
    empty_state["state"] = {}
    scalar_state = copy.deepcopy(NATIVE_STATUS_VALID)
    scalar_state["state"] = "build/active"
    cases: list[Any] = [
        # The pre-fix adapter's invented shape: no schema, no state, no route.
        {"ok": True},
        {"ok": "yes"},
        [],
        "gsd-path/status/v1",
        without_route,
        without_state,
        empty_state,
        scalar_state,
        wrong_schema,
        non_string_action,
    ]
    for case in cases:
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=payload_case(case),
        )
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, case
        assert workflow_readiness(report) == "blocked", case
        assert report.detail, case


def test_native_status_runner_failure_is_never_operational(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    def exploding_runner(root: Path, runtime_path: Path) -> dict[str, Any]:
        raise RuntimeError("helper exited 1: error: STATE.md is missing YAML frontmatter")

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=exploding_runner,
    )

    assert report.kind is not WorkflowStateKind.OPERATIONAL_VALID
    assert workflow_readiness(report) == "blocked"
    assert "STATE.md is missing YAML frontmatter" in report.detail


def test_operational_valid_via_fake_resolver_and_native_status(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=ok_native_status,
    )

    assert report.kind is WorkflowStateKind.OPERATIONAL_VALID
    assert workflow_readiness(report) == "operational"
    assert report.detail == "native status route=run-phase: state is build/active"
    assert report.remediation == "none"
    assert report.runtime.version == PINNED_RUNTIME_VERSION
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.path is not None
    payload = report.to_dict()
    assert payload["schema_version"] == WORKFLOW_STATE_SCHEMA_VERSION
    assert payload["kind"] == "operational-valid"
    assert json.loads(report.to_json())["kind"] == "operational-valid"


def test_operational_report_surfaces_native_milestone_and_phase(tmp_path: Path) -> None:
    """The adapter keeps WHICH milestone and phase the native helper proved.

    Discarding that identity leaves a freshness consumer with no live Path
    comparison source, which is why it still had to fall back to the frozen
    Pi registry. The report carries it read-only, on the operational verdict.
    """
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=ok_native_status,
    )

    assert report.kind is WorkflowStateKind.OPERATIONAL_VALID
    # Verbatim from the pinned helper: state.milestone "001-probe", state.phase "build".
    assert report.native_milestone == "001-probe"
    assert report.native_phase == "build"
    payload = report.to_dict()
    assert payload["native_milestone"] == "001-probe"
    assert payload["native_phase"] == "build"
    # The two fields are additive; the report schema version does not move.
    assert payload["schema_version"] == WORKFLOW_STATE_SCHEMA_VERSION


def test_operational_report_tolerates_absent_identity_fields(tmp_path: Path) -> None:
    """An identity field a payload omits reads as None, never as a failure."""
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    # Real shape of /tmp/wf-probe2: state.milestone null and a block route
    # that carries no phase at all.
    null_milestone = copy.deepcopy(NATIVE_STATUS_VALID)
    null_milestone["state"]["milestone"] = None
    del null_milestone["route"]["phase"]

    no_phase_in_state = copy.deepcopy(NATIVE_STATUS_VALID)
    del no_phase_in_state["state"]["phase"]

    no_identity_anywhere = copy.deepcopy(no_phase_in_state)
    del no_identity_anywhere["state"]["milestone"]
    del no_identity_anywhere["route"]["phase"]

    cases: list[tuple[dict[str, Any], str | None, str | None]] = [
        (null_milestone, None, "build"),
        # state lacks the phase, so the route's phase is the fallback.
        (no_phase_in_state, "001-probe", "build"),
        (no_identity_anywhere, None, None),
    ]
    for payload, milestone, phase in cases:
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.OPERATIONAL_VALID, payload
        assert workflow_readiness(report) == "operational", payload
        assert report.native_milestone == milestone, payload
        assert report.native_phase == phase, payload


def test_wrong_typed_identity_field_fails_closed(tmp_path: Path) -> None:
    """E9: a present identity field of the wrong type is rejected, in state and route.

    Missing and null stay absent; any present non-string value is a broken
    payload and must fail closed instead of silently posing as absent. The
    route sites are checked even when their state twin is a valid string.
    """
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    cases: list[tuple[str, str, Any]] = [
        ("state", "milestone", 7),
        ("state", "milestone", True),
        ("state", "phase", 3.13),
        ("state", "phase", ["build"]),
        ("route", "milestone", 7),
        ("route", "milestone", {"slug": "001-probe"}),
        ("route", "phase", ["build"]),
        ("route", "phase", 1),
    ]
    for container, field, bad_value in cases:
        payload = copy.deepcopy(NATIVE_STATUS_VALID)
        payload[container][field] = bad_value
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.INVALID_SCHEMA, (container, field, bad_value)
        assert workflow_readiness(report) == "blocked", (container, field, bad_value)
        assert f"{container}.{field}" in report.detail, (container, field, bad_value)
        assert "must be a string when present" in report.detail, (container, field, bad_value)


def test_identity_fields_accept_null_and_missing_across_all_four_sites(tmp_path: Path) -> None:
    """E9 acceptance side: null and missing stay absent at every identity site.

    A null ``route`` value is a fallback that reads as absent, and a null
    ``state`` value is absent even when the other half carries a valid string.
    """
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    all_null = copy.deepcopy(NATIVE_STATUS_VALID)
    all_null["state"]["milestone"] = None
    all_null["state"]["phase"] = "build"
    all_null["route"]["milestone"] = None
    all_null["route"]["phase"] = None

    missing_state_phase = copy.deepcopy(all_null)
    del missing_state_phase["state"]["phase"]

    missing_everything = copy.deepcopy(missing_state_phase)
    del missing_everything["state"]["milestone"]
    del missing_everything["route"]["milestone"]
    del missing_everything["route"]["phase"]

    cases: list[tuple[dict[str, Any], str | None, str | None]] = [
        (all_null, None, "build"),
        (missing_state_phase, None, None),
        (missing_everything, None, None),
    ]
    for payload, milestone, phase in cases:
        report = read_workflow_state(
            tmp_path,
            runtime_resolver=resolved_runtime_resolver(),
            native_status_runner=native_status(payload),
        )
        assert report.kind is WorkflowStateKind.OPERATIONAL_VALID, payload
        assert workflow_readiness(report) == "operational", payload
        assert report.native_milestone == milestone, payload
        assert report.native_phase == phase, payload


def test_non_operational_reports_carry_no_native_identity(tmp_path: Path) -> None:
    """Only OPERATIONAL_VALID names a current milestone and phase.

    The blocked and unverified payloads below DO carry state.milestone
    "001-probe", so their None proves the kind rule rather than an absence.
    """
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    blocked = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=blocking_native_status("branch-mismatch"),
    )
    unverified = read_workflow_state(
        tmp_path, runtime_resolver=resolved_runtime_resolver(), native_status_runner=None
    )
    bootstrap_root = tmp_path / "bootstrap"
    write_cutover_marker(bootstrap_root, cutover=False)
    bootstrap = read_workflow_state(bootstrap_root, runtime_resolver=resolved_runtime_resolver())

    assert blocked.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP
    assert unverified.kind is WorkflowStateKind.STATE_UNVERIFIED
    assert bootstrap.kind is WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER
    for report in (blocked, unverified, bootstrap):
        assert report.native_milestone is None, report.kind
        assert report.native_phase is None, report.kind
        payload = report.to_dict()
        assert payload["native_milestone"] is None, report.kind
        assert payload["native_phase"] is None, report.kind


def test_state_without_native_validation_is_not_operational(tmp_path: Path) -> None:
    """Defect T-C: a never-validated state must not read as operational.

    Runtime resolved and STATE.md present are two facts; neither of them is
    "STATE.md passed native validation", which is the only fact that may
    yield OPERATIONAL_VALID.
    """
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    # The production default now wires the real pinned runner, so "unwired" has
    # to be requested explicitly - that is the point: it can no longer happen by
    # accident.
    report = read_workflow_state(
        tmp_path, runtime_resolver=resolved_runtime_resolver(), native_status_runner=None
    )

    assert report.kind is WorkflowStateKind.STATE_UNVERIFIED
    assert report.kind is not WorkflowStateKind.OPERATIONAL_VALID
    assert report.kind.value == "state-unverified"
    assert workflow_readiness(report) == "blocked"
    assert report.detail == "unverified: native status helper not wired"
    assert "unverified" in report.observed
    assert report.runtime.version == PINNED_RUNTIME_VERSION
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.path is not None
    assert report.remediation != "none"


def test_state_unverified_kind_maps_to_blocked_readiness() -> None:
    """`workflow_readiness` is the single mapping authority for every kind.

    Contract A adds the verified shipped/done integrated main to the
    operational set; every other kind stays fail-closed.
    """
    readiness = {
        kind: workflow_readiness(
            WorkflowStateReport(
                schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
                kind=kind,
                observed="",
                remediation="",
                detail="",
                evidence=(),
                runtime=NO_RUNTIME_INFO,
                legacy_gsd_present=False,
            )
        )
        for kind in WorkflowStateKind
    }

    assert readiness[WorkflowStateKind.STATE_UNVERIFIED] == "blocked"
    assert readiness[WorkflowStateKind.OPERATIONAL_VALID] == "operational"
    assert readiness[WorkflowStateKind.SHIPPED_INTEGRATED] == "operational"
    assert readiness[WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER] == "bootstrap-not-cut-over"
    assert {kind for kind, value in readiness.items() if value == "operational"} == {
        WorkflowStateKind.OPERATIONAL_VALID,
        WorkflowStateKind.SHIPPED_INTEGRATED,
    }


def test_new_project_without_completed_history_is_operational_valid(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(
        tmp_path,
        "# GSD Path State\n\n**Active Milestone:** None\n**Phase:** define/active\n",
    )
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=ok_native_status,
    )

    assert report.kind is WorkflowStateKind.OPERATIONAL_VALID
    assert workflow_readiness(report) == "operational"
    assert ".project/STATE.md" in report.evidence


def test_legacy_snapshot_reads_header_as_historical_evidence(tmp_path: Path) -> None:
    write_legacy_gsd_state(tmp_path)

    report = read_legacy_gsd_snapshot(tmp_path)

    assert report.kind is WorkflowStateKind.HISTORICAL_LEGACY
    assert report.legacy_gsd_present is True
    assert "M225-qrwdfv" in report.observed
    assert "blocked" in report.observed
    assert "non-authoritative" in report.observed
    assert report.evidence == (".gsd/STATE.md",)
    assert workflow_readiness(report) == "blocked"


def test_legacy_snapshot_absent_stays_historical(tmp_path: Path) -> None:
    report = read_legacy_gsd_snapshot(tmp_path)

    assert report.kind is WorkflowStateKind.HISTORICAL_LEGACY
    assert report.legacy_gsd_present is False
    assert report.evidence == ()


def test_legacy_gsd_present_is_exposed_without_pi_fallback(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=False)
    write_legacy_gsd_state(tmp_path)

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER
    assert report.legacy_gsd_present is True


def test_dangling_legacy_symlink_still_counts_as_present(tmp_path: Path) -> None:
    os.symlink(tmp_path / "nowhere-gsd", tmp_path / ".gsd")

    report = read_legacy_gsd_snapshot(tmp_path)

    assert report.legacy_gsd_present is True


def test_default_resolver_runs_real_shim_end_to_end(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)
    runtime_dir = tmp_path / "runtime-cache" / PINNED_RUNTIME_DIGEST
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "manifest.json").write_text(
        json.dumps({"version": PINNED_RUNTIME_VERSION, "files": {"pipeline_state.py": "0" * 64}}),
        encoding="utf-8",
    )
    shim = tmp_path / STATUS_RUNTIME_SHIM_RELATIVE_PATH
    shim.write_text(f"print({runtime_dir.as_posix()!r})\n", encoding="utf-8")

    report = read_workflow_state(tmp_path, native_status_runner=ok_native_status)

    assert report.kind is WorkflowStateKind.OPERATIONAL_VALID
    assert report.runtime.path == str(runtime_dir)
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.version == PINNED_RUNTIME_VERSION


class TestLegacySurfaceDecision:
    """The one decision point four governor checks read instead of guessing.

    Each case states what the checkout holds and what a legacy-surface check
    is then allowed to claim. The two failure modes this replaces are an
    absence read as a pass, and frozen data read as current state.
    """

    def test_absent_surface_applies_cutover_false(self, tmp_path: Path) -> None:
        write_cutover_marker(tmp_path, cutover=False)

        decision = read_legacy_surface(tmp_path)

        assert decision.surface is LegacySurface.ABSENT
        assert decision.cutover is False
        for check_id in LEGACY_SURFACE_CHECKS:
            assert decision.policy(check_id) == "not-applicable"
            assert decision.blocks(check_id) is False

    def test_absent_surface_after_cutover_blocks_only_roadmap_freshness(
        self, tmp_path: Path
    ) -> None:
        write_cutover_marker(tmp_path, cutover=True)

        decision = read_legacy_surface(tmp_path)

        assert decision.surface is LegacySurface.ABSENT
        assert decision.blocks("roadmap-freshness") is True
        assert decision.policy("roadmap-freshness") == "not-applicable"
        for check_id in ("gsd-review-dual-truth", "journal-retry-loops", "compat-marker-hygiene"):
            assert decision.blocks(check_id) is False
            assert decision.policy(check_id) == "not-applicable"

    def test_missing_cutover_marker_never_blocks(self, tmp_path: Path) -> None:
        # A cutover nobody recorded has not happened, so it cannot turn an
        # absent surface into a blocker.
        decision = read_legacy_surface(tmp_path)

        assert decision.surface is LegacySurface.ABSENT
        assert decision.cutover is False
        assert decision.blocks("roadmap-freshness") is False
        assert "cutover marker missing" in decision.detail

    def test_present_surface_after_cutover_is_historical_only(self, tmp_path: Path) -> None:
        write_cutover_marker(tmp_path, cutover=True)
        write_legacy_gsd_state(tmp_path)

        decision = read_legacy_surface(tmp_path)

        assert decision.surface is LegacySurface.FROZEN_HISTORICAL
        for check_id in LEGACY_SURFACE_CHECKS:
            assert decision.policy(check_id) == "historical-only"
            assert decision.blocks(check_id) is False

    def test_present_surface_before_cutover_applies(self, tmp_path: Path) -> None:
        write_cutover_marker(tmp_path, cutover=False)
        write_legacy_gsd_state(tmp_path)

        decision = read_legacy_surface(tmp_path)

        assert decision.surface is LegacySurface.OPERATIONAL_NOT_CUT_OVER
        for check_id in LEGACY_SURFACE_CHECKS:
            assert decision.policy(check_id) == "applies"
            assert decision.blocks(check_id) is False

    def test_dangling_legacy_symlink_is_a_present_surface(self, tmp_path: Path) -> None:
        write_cutover_marker(tmp_path, cutover=True)
        os.symlink(tmp_path / "nowhere-gsd", tmp_path / ".gsd")

        decision = read_legacy_surface(tmp_path)

        # A surface pointing at a vanished snapshot still exists: the checks
        # must report an unreadable registry, not an absent one.
        assert decision.surface is LegacySurface.FROZEN_HISTORICAL

    def test_unknown_check_id_is_refused(self, tmp_path: Path) -> None:
        decision = read_legacy_surface(tmp_path)

        with pytest.raises(ValueError, match="not a legacy-surface check"):
            decision.policy("workflow-state-surface")

    def test_observed_tokens_name_surface_policy_and_cutover(self, tmp_path: Path) -> None:
        write_cutover_marker(tmp_path, cutover=True)
        write_legacy_gsd_state(tmp_path)

        observed = read_legacy_surface(tmp_path).observed("compat-marker-hygiene")

        assert observed == (
            "legacy_surface=frozen-historical; cutover=true; policy=historical-only"
        )
