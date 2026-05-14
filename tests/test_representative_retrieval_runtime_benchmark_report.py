from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/verify-representative-retrieval-runtime-benchmark.py"
REPORT = ROOT / "prd/retrieval/representative_retrieval_runtime_benchmark_proof.md"

SCHEMA_VERSION = "representative-retrieval-runtime-benchmark-proof/v1"
REQUIRED_SECTIONS = [
    "# Representative Retrieval Runtime Benchmark Proof",
    "## Inputs Consumed",
    "## Command Run",
    "## Runtime Status",
    "## Metric/Threshold Summary",
    "## Diagnostics Inventory",
    "## Redaction Boundary",
    "## GATE-G011 Disposition Inputs",
    "## Non-claims",
    "## S04 Handoff",
]
REQUIRED_PATHS = [
    "prd/retrieval/representative_retrieval_runtime_benchmark_contract.md",
    "scripts/check-local-retrieval-runtime.py",
    "scripts/verify-representative-retrieval-runtime-benchmark.py",
    "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json",
    "prd/retrieval/local_retrieval_runtime_boundary_proof.md",
    "prd/retrieval/representative_retrieval_corpus_manifest.md",
    "prd/retrieval/representative_retrieval_runtime_benchmark_proof.md",
]
REQUIRED_METRICS = [
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "no_answer_accuracy",
    "ambiguous_rejection_rate",
    "unsafe_rejection_rate",
    "edition_path_mismatch_rejection_rate",
    "runtime_boundary_confirmed",
]
REDACTION_FIELDS = [
    "raw_legal_text_persisted",
    "raw_query_text_persisted",
    "raw_prompt_persisted",
    "raw_vector_persisted",
    "provider_payload_persisted",
    "raw_falkordb_row_persisted",
    "managed_api_evidence_persisted",
    "generated_legal_advice_persisted",
    "absolute_path_persisted",
    "secrets_persisted",
]
REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove production ranker quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not make proof-local IDs production IDs",
    "does not authorize managed embedding API fallback",
    "does not authorize GigaChat or GigaEmbeddings runtime use",
    "does not make LLM output legal authority",
    "does not close GATE-G011; GATE-G011 remains open",
]
FORBIDDEN_MARKERS = [
    ".gsd/exec",
    "GIGACHAT_AUTH_DATA",
    "Bearer ",
    "sk-",
    "api_key",
    "api-key",
    "provider_response_body",
    "managed_api_payload",
    "source_excerpt",
    '"query_text"',
    "user_prompt",
    "embedding_vector",
    '"falkordb_row"',
    "generated_answer",
    "GATE-G011 is closed",
    "closes GATE-G011",
    "managed API fallback is allowed",
    "managed embedding API fallback is allowed",
    "GigaChat fallback is allowed",
]


def report_text() -> str:
    assert REPORT.exists()
    return REPORT.read_text(encoding="utf-8")


def test_report_has_required_sections_schema_and_command() -> None:
    text = report_text()
    positions = [text.find(section) for section in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)
    assert f"Schema version: `{SCHEMA_VERSION}`" in text
    assert "uv run python scripts/verify-representative-retrieval-runtime-benchmark.py --allow-runtime-blocker" in text
    assert "Safe compact stdout summary excerpt" in text


def test_report_references_only_repository_relative_artifact_paths() -> None:
    text = report_text()

    for path in REQUIRED_PATHS:
        assert f"`{path}`" in text
    assert str(ROOT) not in text
    assert not re.search(r"(?<![A-Za-z0-9_])/(root|home|tmp|var|Users)/", text)
    assert ".gsd/exec" not in text


def test_report_metric_status_and_diagnostics_are_categorical() -> None:
    text = report_text()

    assert "Benchmark status:" in text
    assert "Failure class:" in text
    assert "Diagnostic code:" in text or "Diagnostic codes: `none`" in text
    assert "Runtime status:" in text
    assert "Runtime boundary confirmed:" in text
    for metric in REQUIRED_METRICS:
        assert f"`{metric}`" in text
    assert "If runtime is blocked, this report preserves `blocked_runtime` status" in text


def test_report_redaction_boundary_and_payload_exclusions_are_explicit() -> None:
    text = report_text()

    for field in REDACTION_FIELDS:
        assert f"`{field}` = `false`" in text
    assert "does not persist raw legal text, raw query text, prompts, vectors" in text
    assert "provider payloads, managed-API evidence, raw FalkorDB rows" in text
    assert "secrets, generated legal advice, or absolute paths" in text
    for marker in FORBIDDEN_MARKERS:
        assert marker not in text


def test_report_gate_g011_is_handoff_input_not_final_closure() -> None:
    text = report_text()

    assert "`GATE-G011` remains open" in text
    assert "not final gate closure" in text
    assert "this report does not close it" in text
    assert "S04 may consume this report" in text
    assert "not as threshold-pass evidence" in text


def test_report_contains_required_non_claims() -> None:
    text = report_text()

    for claim in REQUIRED_NON_CLAIMS:
        assert claim in text
    assert "does not authorize managed embedding API fallback" in text
    assert "does not close GATE-G011" in text


def test_cli_regenerates_report_with_same_schema_and_safe_json(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    completed = subprocess.run(
        [sys.executable, str(CLI), "--report", str(report), "--allow-runtime-blocker"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    generated = report.read_text(encoding="utf-8")
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["benchmark_status"] in {"metrics_confirmed", "blocked_runtime"}
    assert "## GATE-G011 Disposition Inputs" in generated
    assert str(ROOT) not in generated
    assert ".gsd/exec" not in generated
    assert "GATE-G011 is closed" not in generated
