# pyright: reportMissingImports=false
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from source_lifecycle import (  # noqa: E402
    SourceLifecycleError,
    append_run_error,
    append_run_event,
    append_trajectory_record,
    build_external_review_pack,
    build_review_pack,
    classify_batch,
    discover_with_minimax,
    lifecycle_status,
    load_batch_manifest,
    manifest_input_summary,
    minimax_attempt_directory,
    normalize_discovery_candidates,
    output_summary,
    probe_xml_shape,
    process_batch,
    register_batch,
    run_batch_with_envelope,
    run_directory,
    run_metrics_summary,
    safe_run_id,
    stable_discovery_id,
    trajectory_directory,
    trajectory_record,
    verify_discovery_candidates,
    workspace_tracking_warning,
    write_minimax_attempt_summary,
)

SCRIPT_PATH = ROOT / "scripts" / "source_cli.py"
WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"


def write_xml(path: Path, body: str | None = None, marker: str = "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = body or (
        f'<w:wordDocument xmlns:w="{WORDML_NS}"><w:body><w:p><w:r><w:t>'
        f"{marker}"
        "</w:t></w:r></w:p></w:body></w:wordDocument>"
    )
    path.write_text(payload, encoding="utf-8")


def write_manifest(
    batch_dir: Path,
    artifacts: list[dict],
    *,
    batch_id: str = "batch-test",
    source_family_hint: str = "consultant_wordml",
) -> Path:
    manifest = {
        "schema_version": "legalgraph-source-batch/v1",
        "batch_id": batch_id,
        "source_family_hint": source_family_hint,
        "artifacts": artifacts,
        "non_authoritative": True,
        "non_claims": ["test manifest does not claim parser completeness"],
    }
    path = batch_dir / "batch.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def artifact(relative_path: str, role: str = "full_normative_act") -> dict:
    return {
        "submitted_name_hash": f"sha256:{hashlib.sha256(relative_path.encode()).hexdigest()}",
        "relative_path": relative_path,
        "declared_role_hint": role,
        "declared_identity_hint": {
            "jurisdiction": "RU",
            "act_type": "federal_law",
            "act_number": "44-FZ",
            "edition_label": "test",
        },
    }


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_register_writes_safe_registry_rows_and_raw_store(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])

    result = register_batch(manifest, workspace)

    assert result["status"] == "registered"
    assert result["registered_count"] == 1
    registry = workspace / "registry"
    artifact_rows = read_jsonl(registry / "source_artifacts.jsonl")
    revision_rows = read_jsonl(registry / "source_revisions.jsonl")
    batch_rows = read_jsonl(registry / "batches.jsonl")
    assert len(artifact_rows) == 1
    assert len(revision_rows) == 1
    assert len(batch_rows) == 1
    row = artifact_rows[0]
    assert row["source_family"] == "consultant_wordml"
    assert row["raw_storage_ref"].startswith("law-source/consultant/raw/sha256/")
    assert (workspace / "raw" / "sha256" / row["raw_sha256"][:2] / row["raw_sha256"][2:4] / f"{row['raw_sha256']}.xml").is_file()
    durable = "\n".join(path.read_text(encoding="utf-8") for path in registry.glob("*.jsonl"))
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable
    assert "parser completeness" in durable


def test_register_counts_duplicate_sha_without_duplicate_artifact_rows(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "a.xml")
    write_xml(batch_dir / "incoming" / "b.xml")
    manifest = write_manifest(batch_dir, [artifact("a.xml"), artifact("b.xml")])

    result = register_batch(manifest, workspace)
    second = register_batch(manifest, workspace)

    assert result["duplicate_count"] == 1
    assert second["duplicate_count"] == 1
    assert len(read_jsonl(workspace / "registry" / "source_artifacts.jsonl")) == 1


def test_classify_detects_wordml_and_routes_document_roles(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "act.xml", marker="ACT_TEXT_SHOULD_NOT_LEAK")
    write_xml(batch_dir / "incoming" / "relations.xml", marker="RELATION_TEXT_SHOULD_NOT_LEAK")
    manifest = write_manifest(
        batch_dir,
        [artifact("act.xml", "full_normative_act"), artifact("relations.xml", "relation_list")],
    )

    result = classify_batch(manifest, workspace)

    assert result["route_counts"] == {"full_act": 1, "relation_list": 1}
    rows = read_jsonl(workspace / "registry" / "source_classification.safe.jsonl")
    by_role = {row["document_role"]: row for row in rows}
    assert by_role["full_normative_act"]["source_family"] == "consultant_wordml"
    assert by_role["full_normative_act"]["parser_route"] == "full_act"
    assert by_role["relation_list"]["parser_route"] == "relation_list"
    assert by_role["full_normative_act"]["detected_shape"]["root_namespace"] == WORDML_NS


def test_classify_unknown_xml_routes_to_unsupported(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "unknown.xml", "<root><child /></root>")
    manifest = write_manifest(batch_dir, [artifact("unknown.xml")])

    classify_batch(manifest, workspace)

    row = read_jsonl(workspace / "registry" / "source_classification.safe.jsonl")[0]
    assert row["source_family"] == "unknown_xml"
    assert row["document_role"] == "unsupported_source"
    assert row["parser_route"] == "unsupported_xml"
    assert row["route_confidence"] == "needs_review"


def test_malformed_manifest_and_path_escape_fail_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "batch.manifest.json"
    malformed.write_text("[]", encoding="utf-8")
    try:
        load_batch_manifest(malformed)
    except SourceLifecycleError as exc:
        assert "JSON object" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("malformed manifest unexpectedly loaded")

    batch_dir = tmp_path / "batch"
    (batch_dir / "incoming").mkdir(parents=True)
    manifest = write_manifest(batch_dir, [artifact("../escape.xml")])
    try:
        load_batch_manifest(manifest)
    except SourceLifecycleError as exc:
        assert "may not contain '..'" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("path escape unexpectedly loaded")


def test_xml_probe_rejects_doctype_entities(tmp_path: Path) -> None:
    source = tmp_path / "entity.xml"
    source.write_text("<!DOCTYPE x [<!ENTITY e 'boom'>]><root>&e;</root>", encoding="utf-8")

    shape = probe_xml_shape(source)

    assert shape["well_formed"] is False
    assert shape["error_kind"] == "xml_unsafe_doctype"
    assert shape["source_family"] == "unknown_xml"


def test_run_envelope_helpers_write_safe_events_errors_and_summaries(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest_path = write_manifest(batch_dir, [artifact("doc.xml")])
    manifest = load_batch_manifest(manifest_path)
    run_id = safe_run_id(manifest.batch_id, "2026-05-20T00:00:00Z")
    run_dir = run_directory(workspace, run_id)

    append_run_event(
        run_dir,
        {
            "phase": "register",
            "status": "started",
            "message": "safe message",
            "absolute_path": str(tmp_path),
        },
    )
    append_run_error(
        run_dir,
        {
            "phase": "classify",
            "error_kind": "malformed_manifest",
            "message": "bounded diagnostic",
            "raw_filename": "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS.xml",
        },
    )
    inputs = manifest_input_summary(manifest)
    output = output_summary([workspace / "registry" / "source_artifacts.jsonl"], workspace)
    metrics = run_metrics_summary(registered_count=1, classified_count=1, processed_count=1)

    assert run_id == "RUN-056ace548e13"
    assert read_jsonl(run_dir / "events.jsonl")[0] == {
        "message": "safe message",
        "non_authoritative": True,
        "phase": "register",
        "schema_version": "legalgraph-source-run-event/v1",
        "status": "started",
    }
    error_row = read_jsonl(run_dir / "errors.jsonl")[0]
    assert error_row["error_kind"] == "malformed_manifest"
    assert "raw_filename" not in error_row
    assert inputs["batch_id_hash"] and inputs["artifact_count"] == 1
    assert "relative_path" not in json.dumps(inputs, ensure_ascii=False)
    assert output["output_refs"] == ["registry/source_artifacts.jsonl"]
    assert metrics["status"] == "completed"
    durable = (run_dir / "events.jsonl").read_text(encoding="utf-8") + (run_dir / "errors.jsonl").read_text(encoding="utf-8")
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable


def test_output_ref_rejects_workspace_escape(tmp_path: Path) -> None:
    try:
        output_summary([tmp_path.parent / "outside.json"], tmp_path / "workspace")
    except SourceLifecycleError as exc:
        assert "escapes workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("workspace escape unexpectedly accepted")


def test_workspace_tracking_warning_reports_unignored_lifecycle_dirs(tmp_path: Path) -> None:
    warning = workspace_tracking_warning(tmp_path / "workspace")

    assert warning["schema_version"] == "legalgraph-source-workspace-tracking-warning/v1"
    assert warning["status"] == "warning"
    assert set(warning["ignored"]) == {"inbox", "raw", "registry", "processed", "runs"}
    assert "review tracking policy" in warning["message"]


def test_external_review_pack_summarizes_discovery_and_verifier_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    mock_response = tmp_path / "mock-response.json"
    response = {
        "candidates": [
            {
                "candidate_kind": "relationship_candidate",
                "candidate_summary": "Repeated amendment-reference structure suggests a relationship candidate.",
                "supporting_context": "Open legal/source context explains the repeated structure.",
                "confidence_bucket": "medium",
            }
        ]
    }
    mock_response.write_text(
        json.dumps({"response_summary": json.dumps(response, ensure_ascii=False)}, ensure_ascii=False),
        encoding="utf-8",
    )
    run_id = "RUN-abc123def456"
    discover_with_minimax(
        workspace,
        run_id=run_id,
        source_refs=["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
        prompt_summary="Use open legal/source context to discover graph-context structures.",
        mock_response_path=mock_response,
        verify_candidates=True,
    )

    result = build_external_review_pack(workspace, run_id)

    assert result["status"] == "review_pack_written"
    pack = json.loads((workspace / result["review_pack_json_ref"]).read_text(encoding="utf-8"))
    markdown = (workspace / result["review_pack_ref"]).read_text(encoding="utf-8")
    summary = (workspace / result["external_review_summary_ref"]).read_text(encoding="utf-8")
    assert pack["schema_version"] == "m032.s06.external-review-pack.v1"
    assert pack["candidate_summary"]["candidate_count"] == 1
    assert pack["verifier_summary"]["status_counts"] == {"accepted": 1}
    assert pack["missing_sections"] == ["diagnostics", "review_queue", "rejections"]
    assert pack["boundary"] == {
        "gpt55_role": "external control over CLI outputs",
        "not_runtime_judge": True,
        "deterministic_verifier_remains_runtime_gate": True,
    }
    assert len(pack["review_questions"]) >= 5
    assert "not an embedded runtime judge" in markdown
    assert "does not validate R035" in markdown
    assert "does not validate R038" in markdown
    assert "not an external review verdict" in summary
    durable = json.dumps(pack, ensure_ascii=False) + markdown + summary
    assert str(tmp_path) not in durable


def test_verify_discovery_candidates_writes_accepted_rejected_and_review_outputs(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_id = "RUN-abc123def456"
    accepted = {
        "schema_version": "m032.s04.graph-context-candidate.v1",
        "candidate_id": "CAND-accepted123",
        "run_id": run_id,
        "attempt_id": "ATTEMPT-accepted123",
        "candidate_kind": "relationship_candidate",
        "lifecycle_status": "proposed",
        "source_refs": ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
        "trajectory_refs": ["trajectory:STEP-accepted"],
        "attempt_refs": ["attempt:ATTEMPT-accepted123"],
        "candidate_summary": "Accepted structural relationship candidate.",
        "supporting_context": "Open legal/source context supports the candidate.",
        "confidence_bucket": "medium",
        "normalization_warnings": [],
        "model_claims_ignored": [],
        "non_authoritative": True,
    }
    needs_review = {
        **accepted,
        "candidate_id": "CAND-review123",
        "attempt_id": "ATTEMPT-review123",
        "source_refs": ["processed:inventory-a"],
        "attempt_refs": ["attempt:ATTEMPT-review123"],
        "candidate_summary": "Safe candidate without deterministic evidence refs.",
    }
    rejected = {
        **accepted,
        "candidate_id": "CAND-rejected123",
        "attempt_id": "ATTEMPT-rejected123",
        "lifecycle_status": "accepted",
        "attempt_refs": ["attempt:ATTEMPT-rejected123"],
        "candidate_summary": "Malformed candidate should be rejected.",
    }

    result = verify_discovery_candidates(
        workspace,
        run_id=run_id,
        candidate_rows=[accepted, needs_review, rejected],
    )

    assert result["status"] == "verified"
    assert result["decision_count"] == 3
    assert result["status_counts"] == {"accepted": 1, "rejected": 1, "needs_review": 1}
    decisions_ref = next(ref for ref in result["output_refs"] if ref.endswith("verifier_decisions.jsonl"))
    review_ref = next(ref for ref in result["output_refs"] if ref.endswith("review_queue_items.jsonl"))
    rejection_ref = next(ref for ref in result["output_refs"] if ref.endswith("rejection_reasons.jsonl"))
    decisions = read_jsonl(workspace / decisions_ref)
    reviews = read_jsonl(workspace / review_ref)
    rejections = read_jsonl(workspace / rejection_ref)
    by_candidate = {row["candidate_id"]: row for row in decisions}
    assert by_candidate["CAND-accepted123"]["verifier_status"] == "accepted"
    assert by_candidate["CAND-accepted123"]["acceptance_evidence_refs"] == [
        "processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"
    ]
    assert by_candidate["CAND-review123"]["verifier_status"] == "needs_review"
    assert by_candidate["CAND-rejected123"]["verifier_status"] == "rejected"
    assert "candidate_not_proposed" in by_candidate["CAND-rejected123"]["rejection_reasons"]
    assert reviews[0]["candidate_id"] == "CAND-review123"
    assert rejections[0]["candidate_id"] == "CAND-rejected123"
    durable = "".join((workspace / ref).read_text(encoding="utf-8") for ref in result["output_refs"])
    assert str(tmp_path) not in durable
    assert "legal correctness" in durable
    assert "R035" in durable
    assert "R038" in durable


def test_candidate_normalization_writes_structured_candidates_and_signals(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_id = "RUN-abc123def456"
    attempt_id = "ATTEMPT-abc123def456"
    response = json.dumps(
        {
            "candidates": [
                {
                    "candidate_kind": "relationship_candidate",
                    "candidate_summary": "Repeated amendment-reference structure suggests a relationship candidate.",
                    "supporting_context": "Open legal/source context explains the repeated structure.",
                    "confidence_bucket": "medium",
                    "lifecycle_status": "accepted",
                }
            ]
        },
        ensure_ascii=False,
    )

    result = normalize_discovery_candidates(
        workspace,
        run_id=run_id,
        attempt_id=attempt_id,
        response_summary=response,
        source_refs=["processed:inventory-a"],
        trajectory_refs=["trajectory:STEP-source-structure"],
    )

    assert result["status"] == "normalized"
    assert result["candidate_count"] == 1
    assert result["signal_count"] == 1
    candidate_path = workspace / "runtime" / "discovery" / run_id / "candidate_hypotheses.jsonl"
    signal_path = workspace / "runtime" / "discovery" / run_id / "graph_context_signals.jsonl"
    candidates = read_jsonl(candidate_path)
    signals = read_jsonl(signal_path)
    assert candidates[0]["schema_version"] == "m032.s04.graph-context-candidate.v1"
    assert candidates[0]["candidate_kind"] == "relationship_candidate"
    assert candidates[0]["lifecycle_status"] == "proposed"
    assert candidates[0]["model_claims_ignored"] == ["model_claimed_status:accepted"]
    assert candidates[0]["supporting_context"] == "Open legal/source context explains the repeated structure."
    assert signals[0]["candidate_id"] == candidates[0]["candidate_id"]
    assert signals[0]["lifecycle_status"] == "proposed"
    durable = candidate_path.read_text(encoding="utf-8") + signal_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in durable


def test_candidate_normalization_plain_text_fallback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    result = normalize_discovery_candidates(
        workspace,
        run_id="RUN-abc123def456",
        attempt_id="ATTEMPT-abc123def456",
        response_summary="Possible repeated source pattern that may help graph context.",
        source_refs=["processed:inventory-a"],
        trajectory_refs=["trajectory:STEP-source-structure"],
    )

    assert result["candidate_count"] == 1
    candidate_path = workspace / result["output_refs"][0]
    candidate = read_jsonl(candidate_path)[0]
    assert candidate["candidate_kind"] == "graph_context_signal"
    assert candidate["confidence_bucket"] == "unknown"
    assert candidate["candidate_summary"] == "Possible repeated source pattern that may help graph context."


def test_candidate_normalization_empty_and_malformed_outputs_write_diagnostics(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    empty = normalize_discovery_candidates(
        workspace,
        run_id="RUN-abc123def456",
        attempt_id="ATTEMPT-abc123def456",
        response_summary="  ",
        source_refs=["processed:inventory-a"],
        trajectory_refs=["trajectory:STEP-source-structure"],
    )
    malformed = normalize_discovery_candidates(
        workspace,
        run_id="RUN-def456abc123",
        attempt_id="ATTEMPT-def456abc123",
        response_summary="{not json",
        source_refs=["processed:inventory-b"],
        trajectory_refs=["trajectory:STEP-source-structure-b"],
    )

    assert empty["status"] == "needs_review"
    assert empty["candidate_count"] == 0
    assert empty["diagnostic_count"] == 1
    empty_diag = read_jsonl(workspace / empty["output_refs"][0])[0]
    assert empty_diag["error_kind"] == "empty_discovery_output"
    assert malformed["status"] == "needs_review"
    malformed_diag = read_jsonl(workspace / malformed["output_refs"][0])[0]
    assert malformed_diag["error_kind"] == "malformed_candidate_payload"


def test_discovery_trajectory_helpers_write_attempt_and_records(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_id = "RUN-abc123def456"
    step_id = stable_discovery_id("STEP", run_id, "source-observation")
    attempt_id = stable_discovery_id("ATTEMPT", run_id, step_id, "minimax")

    record = trajectory_record(
        run_id=run_id,
        event_type="source_structure_observed",
        phase="source_observation",
        step_id=step_id,
        parent_step_id=None,
        source_refs=["source:ARTIFACT-abc123def456"],
        input_refs=["processed:inventory-a"],
        output_refs=["candidate:CAND-abc123def456"],
        summary="Observed repeated amendment-reference structure.",
        observed_context="Open legal/source context preserved for analysis.",
        decision="candidate_extraction_needed",
        decision_reason="The structure is repeated and graph-context relevant.",
        next_action="prepare_minimax_attempt",
        timestamp_utc="2026-05-20T05:00:00Z",
        extra={
            "operation": "observe_source_structure",
            "observed_structure": "repeated_amendment_reference",
            "candidate_refs": ["CAND-abc123def456"],
            "confidence_bucket": "medium",
        },
    )
    trajectory_path = append_trajectory_record(
        workspace, run_id, record, file_name="discovery_steps.jsonl"
    )
    attempt_result = write_minimax_attempt_summary(
        workspace,
        run_id,
        {
            "attempt_id": attempt_id,
            "source_step_id": step_id,
            "source_refs": ["source:ARTIFACT-abc123def456"],
            "prompt_summary": "Ask for structural discovery over bounded open source context.",
            "response_summary": "Proposed one relationship candidate for verifier routing.",
            "candidate_refs": ["candidate:CAND-abc123def456"],
            "trajectory_refs": [f"trajectory:{step_id}"],
            "model_name": "minimax",
            "status": "completed",
            "decision_reason": "Attempt summary normalized without provider transport internals.",
            "raw_provider_payload": "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS",
        },
    )

    assert trajectory_path == trajectory_directory(workspace, run_id) / "discovery_steps.jsonl"
    assert attempt_result["status"] == "attempt_summary_written"
    assert attempt_result["attempt_ref"].endswith("attempts.jsonl")
    assert minimax_attempt_directory(workspace, run_id).is_dir()
    trajectory_rows = read_jsonl(trajectory_path)
    attempt_rows = read_jsonl(workspace / attempt_result["attempt_ref"])
    assert trajectory_rows[0]["schema_version"] == "m032.s02.trajectory.v1"
    assert trajectory_rows[0]["non_authoritative"] is True
    assert trajectory_rows[0]["observed_context"] == "Open legal/source context preserved for analysis."
    assert attempt_rows[0]["schema_version"] == "m032.s03.minimax-attempt.v1"
    assert attempt_rows[0]["attempt_id"] == attempt_id
    assert attempt_rows[0]["non_authoritative"] is True
    durable = trajectory_path.read_text(encoding="utf-8") + (workspace / attempt_result["attempt_ref"]).read_text(
        encoding="utf-8"
    )
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable


def test_discovery_helpers_reject_unsafe_ids_and_unknown_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    try:
        trajectory_directory(workspace, "../bad")
    except SourceLifecycleError as exc:
        assert "run_id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unsafe run id unexpectedly accepted")

    try:
        append_trajectory_record(workspace, "RUN-abc123def456", {}, file_name="raw-provider.jsonl")
    except SourceLifecycleError as exc:
        assert "unsupported trajectory" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unsupported trajectory file unexpectedly accepted")

    try:
        write_minimax_attempt_summary(workspace, "RUN-abc123def456", {"attempt_id": "bad/id"})
    except SourceLifecycleError as exc:
        assert "ATTEMPT" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unsafe attempt id unexpectedly accepted")


def test_process_emits_safe_inventory_diagnostics_and_metrics(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml", "inventory_only")])

    result = process_batch(manifest, workspace)

    assert result["status"] == "processed"
    assert result["processed_count"] == 1
    output_dir = workspace / result["output_dir"]
    inventory_rows = read_jsonl(output_dir / "source_inventory.safe.jsonl")
    diagnostic_rows = read_jsonl(output_dir / "diagnostics.safe.jsonl")
    metrics = json.loads((output_dir / "metrics.safe.json").read_text(encoding="utf-8"))
    assert inventory_rows[0]["document_role"] == "inventory_only"
    assert inventory_rows[0]["raw_size_bucket"].startswith("lt_")
    assert inventory_rows[0]["selector"].startswith("root:wordDocument:namespace_sha256:")
    assert inventory_rows[0]["metrics"]["element_count"] > 0
    assert diagnostic_rows[0]["well_formed"] is True
    assert metrics["artifact_count"] == 1
    assert metrics["source_family_counts"] == {"consultant_wordml": 1}
    durable = "\n".join(path.read_text(encoding="utf-8") for path in output_dir.iterdir())
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable
    assert "parser completeness" in durable


def test_status_summarizes_registry_and_processed_state(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])

    register_batch(manifest, workspace)
    classify_batch(manifest, workspace)
    process_batch(manifest, workspace)
    status = lifecycle_status(workspace)

    assert status["status"] == "ok"
    assert status["registry_counts"] == {
        "source_artifacts": 1,
        "source_revisions": 1,
        "batches": 1,
        "source_classification": 1,
    }
    assert status["processed_corpus_count"] == 1
    assert len(status["processed_corpora"]) == 1
    assert len(status["latest_batch_id_hash"]) == 64


def test_run_batch_with_envelope_writes_run_artifacts_and_status(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])

    result = run_batch_with_envelope(
        manifest, workspace, started_at="2026-05-20T01:00:00Z"
    )

    assert result["status"] == "completed"
    run_dir = workspace / result["run_ref"]
    assert (run_dir / "run.json").is_file()
    assert (run_dir / "inputs.json").is_file()
    assert (run_dir / "outputs.json").is_file()
    assert (run_dir / "events.jsonl").is_file()
    assert (run_dir / "metrics.json").is_file()
    assert not (run_dir / "errors.jsonl").exists()
    run_json = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    outputs = json.loads((run_dir / "outputs.json").read_text(encoding="utf-8"))
    events = read_jsonl(run_dir / "events.jsonl")
    assert run_json["status"] == "completed"
    assert run_json["workspace_tracking"]["status"] == "warning"
    assert metrics["registered_count"] == 1
    assert metrics["classified_count"] == 1
    assert metrics["processed_count"] == 1
    assert metrics["error_count"] == 0
    assert len(outputs["output_refs"]) == 7
    assert [event["phase"] for event in events] == [
        "register",
        "register",
        "classify",
        "classify",
        "process",
        "process",
    ]
    status = lifecycle_status(workspace)
    assert status["run_count"] == 1
    assert status["latest_run_status"] == "completed"
    durable = "\n".join(path.read_text(encoding="utf-8") for path in run_dir.iterdir() if path.is_file())
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable


def test_run_batch_with_envelope_records_malformed_manifest_failure(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    manifest = tmp_path / "bad.manifest.json"
    manifest.write_text("[]", encoding="utf-8")

    result = run_batch_with_envelope(
        manifest, workspace, started_at="2026-05-20T02:00:00Z"
    )

    assert result["status"] == "failed"
    run_dir = workspace / result["run_ref"]
    assert not (run_dir / "inputs.json").exists()
    assert not (run_dir / "outputs.json").exists()
    assert read_jsonl(run_dir / "errors.jsonl")[0]["error_kind"] == "source_lifecycle_error"
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["error_count"] == 1
    assert metrics["status"] == "failed"


def test_cli_register_classify_process_status_and_run_batch_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])

    for command in ("register", "classify", "process"):
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--workspace",
                str(workspace),
                command,
                str(manifest),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        assert json.loads(completed.stdout)["status"] in {"registered", "classified", "processed"}
    status = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--workspace", str(workspace), "status"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(status.stdout)["processed_corpus_count"] == 1

    other_workspace = tmp_path / "other-workspace"
    run_batch = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(other_workspace),
            "run-batch",
            str(manifest),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(run_batch.stdout)["status"] == "completed"


def test_cli_discover_writes_mocked_minimax_trajectory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    mock_response = tmp_path / "mock-response.json"
    mock_response.write_text(
        json.dumps({"response_summary": "Observed a source structure candidate for graph context."}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "discover",
            "--run-id",
            "RUN-abc123def456",
            "--source-ref",
            "processed:inventory-a",
            "--prompt-summary",
            "Use open legal/source context to discover graph-context structures.",
            "--mock-response",
            str(mock_response),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "completed"
    assert payload["non_authoritative"] is True
    assert payload["attempt_ref"].endswith("attempts.jsonl")
    assert payload["candidate_count"] == 1
    assert payload["signal_count"] == 1
    assert any(ref.endswith("candidate_hypotheses.jsonl") for ref in payload["discovery_output_refs"])
    assert any(ref.endswith("graph_context_signals.jsonl") for ref in payload["discovery_output_refs"])
    trajectory = read_jsonl(workspace / payload["trajectory_ref"])
    attempts = read_jsonl(workspace / payload["attempt_ref"])
    candidate_ref = next(ref for ref in payload["discovery_output_refs"] if ref.endswith("candidate_hypotheses.jsonl"))
    signal_ref = next(ref for ref in payload["discovery_output_refs"] if ref.endswith("graph_context_signals.jsonl"))
    candidates = read_jsonl(workspace / candidate_ref)
    signals = read_jsonl(workspace / signal_ref)
    assert [row["event_type"] for row in trajectory] == [
        "minimax_attempt_prepared",
        "minimax_attempt_completed",
    ]
    assert attempts[0]["response_summary"] == "Observed a source structure candidate for graph context."
    assert attempts[0]["non_authoritative"] is True
    assert candidates[0]["lifecycle_status"] == "proposed"
    assert candidates[0]["candidate_kind"] == "graph_context_signal"
    assert signals[0]["candidate_id"] == candidates[0]["candidate_id"]
    durable = (
        (workspace / payload["trajectory_ref"]).read_text(encoding="utf-8")
        + (workspace / payload["attempt_ref"]).read_text(encoding="utf-8")
        + (workspace / candidate_ref).read_text(encoding="utf-8")
        + (workspace / signal_ref).read_text(encoding="utf-8")
    )
    assert str(tmp_path) not in durable


def test_cli_discover_can_verify_candidates(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    mock_response = tmp_path / "mock-response.json"
    response = {
        "candidates": [
            {
                "candidate_kind": "relationship_candidate",
                "candidate_summary": "Repeated amendment-reference structure suggests a relationship candidate.",
                "supporting_context": "Open legal/source context explains the repeated structure.",
                "confidence_bucket": "medium",
            }
        ]
    }
    mock_response.write_text(
        json.dumps({"response_summary": json.dumps(response, ensure_ascii=False)}, ensure_ascii=False),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "discover",
            "--run-id",
            "RUN-abc123def456",
            "--source-ref",
            "processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl",
            "--prompt-summary",
            "Use open legal/source context to discover graph-context structures.",
            "--mock-response",
            str(mock_response),
            "--verify-candidates",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "completed"
    assert payload["candidate_count"] == 1
    assert payload["verifier_status_counts"] == {"accepted": 1, "rejected": 0, "needs_review": 0}
    decision_ref = next(ref for ref in payload["verifier_output_refs"] if ref.endswith("verifier_decisions.jsonl"))
    decisions = read_jsonl(workspace / decision_ref)
    assert decisions[0]["verifier_status"] == "accepted"
    assert decisions[0]["candidate_id"].startswith("CAND-")
    assert decisions[0]["acceptance_evidence_refs"] == [
        "processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"
    ]
    assert decisions[0]["non_authoritative"] is True


def test_cli_external_review_pack_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    mock_response = tmp_path / "mock-response.json"
    response = {
        "candidates": [
            {
                "candidate_kind": "relationship_candidate",
                "candidate_summary": "Repeated amendment-reference structure suggests a relationship candidate.",
                "supporting_context": "Open legal/source context explains the repeated structure.",
                "confidence_bucket": "medium",
            }
        ]
    }
    mock_response.write_text(
        json.dumps({"response_summary": json.dumps(response, ensure_ascii=False)}, ensure_ascii=False),
        encoding="utf-8",
    )
    run_id = "RUN-abc123def456"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "discover",
            "--run-id",
            run_id,
            "--source-ref",
            "processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl",
            "--prompt-summary",
            "Use open legal/source context to discover graph-context structures.",
            "--mock-response",
            str(mock_response),
            "--verify-candidates",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "external-review-pack",
            run_id,
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "review_pack_written"
    assert (workspace / payload["review_pack_ref"]).is_file()
    assert (workspace / payload["review_pack_json_ref"]).is_file()
    assert (workspace / payload["external_review_summary_ref"]).is_file()
    pack = json.loads((workspace / payload["review_pack_json_ref"]).read_text(encoding="utf-8"))
    assert pack["verifier_summary"]["status_counts"] == {"accepted": 1}
    assert pack["boundary"]["not_runtime_judge"] is True


def test_cli_discover_reports_missing_minimax_config(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    env = {key: value for key, value in os.environ.items() if key != "MINIMAX_API_KEY"}

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "discover",
            "--run-id",
            "RUN-abc123def456",
            "--source-ref",
            "processed:inventory-a",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "blocked_missing_config"
    assert payload["root_cause"] == "minimax-credential-missing"
    assert payload["non_authoritative"] is True
    attempts = read_jsonl(workspace / payload["attempt_ref"])
    assert attempts[0]["status"] == "blocked_missing_config"
    assert "provider request was made" in attempts[0]["response_summary"]


def test_review_pack_writes_safe_markdown_and_json_for_completed_run(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])
    run = run_batch_with_envelope(
        manifest, workspace, started_at="2026-05-20T03:00:00Z"
    )

    result = build_review_pack(workspace, run["run_id"])

    assert result["status"] == "review_pack_written"
    run_dir = workspace / run["run_ref"]
    pack_json = json.loads((run_dir / "review_pack.json").read_text(encoding="utf-8"))
    pack_md = (run_dir / "review_pack.md").read_text(encoding="utf-8")
    assert pack_json["run_status"] == "completed"
    assert pack_json["metrics"]["processed_count"] == 1
    assert len(pack_json["output_refs"]) == 7
    assert pack_json["error_kinds"] == []
    assert "Consultant XML Run Review Pack" in pack_md
    assert "does not claim parser completeness" in pack_md
    assert "does not validate R035" in pack_md
    assert "uv run python scripts/source_cli.py --workspace <workspace> run-batch <manifest>" in pack_md
    durable = json.dumps(pack_json, ensure_ascii=False) + pack_md
    assert "SHOULD_NOT_APPEAR_IN_DURABLE_OUTPUTS" not in durable
    assert str(tmp_path) not in durable


def test_review_pack_summarizes_failure_errors(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    manifest = tmp_path / "bad.manifest.json"
    manifest.write_text("[]", encoding="utf-8")
    run = run_batch_with_envelope(
        manifest, workspace, started_at="2026-05-20T04:00:00Z"
    )

    result = build_review_pack(workspace)

    run_dir = workspace / run["run_ref"]
    pack_json = json.loads((run_dir / "review_pack.json").read_text(encoding="utf-8"))
    pack_md = (run_dir / "review_pack.md").read_text(encoding="utf-8")
    assert result["run_status"] == "failed"
    assert result["error_count"] == 1
    assert pack_json["error_kinds"] == ["source_lifecycle_error"]
    assert "Inspect errors.jsonl" in pack_md


def test_cli_review_pack_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "run-batch",
            str(manifest),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    run_payload = json.loads(run.stdout)
    review = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--workspace",
            str(workspace),
            "review-pack",
            run_payload["run_id"],
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(review.stdout)
    assert payload["status"] == "review_pack_written"
    assert (workspace / payload["review_pack_ref"]).is_file()
    assert (workspace / payload["review_pack_json_ref"]).is_file()


def test_cli_register_and_classify_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    batch_dir = tmp_path / "batch"
    write_xml(batch_dir / "incoming" / "doc.xml")
    manifest = write_manifest(batch_dir, [artifact("doc.xml")])

    register = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--workspace", str(workspace), "register", str(manifest)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    classify = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--workspace", str(workspace), "classify", str(manifest)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert json.loads(register.stdout)["status"] == "registered"
    assert json.loads(classify.stdout)["route_counts"] == {"full_act": 1}
