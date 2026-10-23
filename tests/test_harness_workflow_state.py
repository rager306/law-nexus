"""TDD contracts for the typed workflow-state adapter (MIGRATION.md section 4.1)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from law_nexus_harness.workflow_state import (
    CUTOVER_MARKER_RELATIVE_PATH,
    RUNTIME_DECLARATION_RELATIVE_PATH,
    STATUS_RUNTIME_SHIM_RELATIVE_PATH,
    WORKFLOW_STATE_SCHEMA_VERSION,
    RuntimeResolution,
    WorkflowStateKind,
    read_legacy_gsd_snapshot,
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


def ok_native_status(root: Path, runtime_path: Path) -> dict[str, Any]:
    return {"ok": True}


def conflicting_native_status(reason: str) -> Callable[[Path, Path], dict[str, Any]]:
    def runner(root: Path, runtime_path: Path) -> dict[str, Any]:
        return {"ok": False, "reason": reason}

    return runner


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
            native_status_runner=conflicting_native_status(reason),
        )
        assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP, reason
        assert reason in report.detail
        assert workflow_readiness(report) == "blocked"


def test_unmapped_native_status_reason_stays_conflicting_ownership(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=conflicting_native_status("unexpected-thing"),
    )

    assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP
    assert "unexpected-thing" in report.detail
    assert "unmapped" in report.observed


def test_malformed_native_status_payload_is_invalid_schema(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    def bad_runner(root: Path, runtime_path: Path) -> dict[str, Any]:
        return {"ok": "yes"}

    report = read_workflow_state(
        tmp_path,
        runtime_resolver=resolved_runtime_resolver(),
        native_status_runner=bad_runner,
    )

    assert report.kind is WorkflowStateKind.INVALID_SCHEMA
    assert "boolean ok" in report.detail


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
    assert report.detail == "native status ok"
    assert report.remediation == "none"
    assert report.runtime.version == PINNED_RUNTIME_VERSION
    assert report.runtime.digest == PINNED_RUNTIME_DIGEST
    assert report.runtime.path is not None
    payload = report.to_dict()
    assert payload["schema_version"] == WORKFLOW_STATE_SCHEMA_VERSION
    assert payload["kind"] == "operational-valid"
    assert json.loads(report.to_json())["kind"] == "operational-valid"


def test_unverified_operational_detail_without_native_runner(tmp_path: Path) -> None:
    write_cutover_marker(tmp_path, cutover=True)
    write_project_state(tmp_path)
    write_runtime_declaration(tmp_path)

    report = read_workflow_state(tmp_path, runtime_resolver=resolved_runtime_resolver())

    assert report.kind is WorkflowStateKind.OPERATIONAL_VALID
    assert report.detail == "unverified: native status helper not wired"
    assert "unverified" in report.observed


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
