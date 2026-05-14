from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd" / "retrieval" / "local_retrieval_runtime_boundary_proof.md"

REQUIRED_SECTIONS = [
    "# Local Retrieval Runtime Boundary Proof",
    "## Source artifacts",
    "## Runtime check command",
    "## Current observed output",
    "## Safe diagnostic inventory",
    "## Model boundary",
    "## Redaction boundary",
    "## Non-claims and open boundaries",
    "## Handoff contract for S03",
    "## Verification hook",
]

REQUIRED_SOURCES = [
    "scripts/check-local-retrieval-runtime.py",
    "tests/test_local_retrieval_runtime_check_cli.py",
    "prd/retrieval/local_retrieval_runtime_boundary_contract.md",
]

REQUIRED_DIAGNOSTIC_CODES = [
    "LRR_DEPENDENCY_MISSING",
    "LRR_S10_METADATA_MALFORMED",
    "LRR_MODEL_CACHE_MISSING",
    "LRR_LOCAL_INFERENCE_FAILED_REDACTED",
    "LRR_DIMENSION_MISMATCH",
    "LRR_MANAGED_API_FORBIDDEN",
    "LRR_NOT_RUN_CONTRACT_ONLY",
    "LRR_INTERNAL_ERROR_REDACTED",
]

REQUIRED_REDACTION_FLAGS = [
    "raw_legal_text_excluded",
    "raw_query_text_excluded",
    "raw_vectors_excluded",
    "provider_payloads_excluded",
    "secrets_excluded",
    "absolute_paths_excluded",
    "legal_advice_excluded",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove representative corpus quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not close `GATE-G011`",
    "does not authorize managed embedding API fallback",
    "does not authorize GigaChat or GigaEmbeddings runtime use",
    "does not make LLM output legal authority",
]

FORBIDDEN_SNIPPETS = [
    "/root/",
    "/tmp/",
    ".gsd/exec",
    "BEGIN PRIVATE KEY",
    "Bearer ",
    "sk-",
    "api_key",
    "authorization",
    "legal advice:",
    "Настоящий Федеральный закон регулирует отношения",
]


def report_text() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def observed_json(text: str) -> dict[str, object]:
    observed = section(text, "## Current observed output")
    start = observed.index("```json") + len("```json")
    end = observed.index("```", start)
    return json.loads(observed[start:end].strip())


def test_report_required_sections_are_present_in_order() -> None:
    text = report_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_report_references_runtime_sources_and_command() -> None:
    text = report_text()
    sources = section(text, "## Source artifacts")
    command = section(text, "## Runtime check command")

    for source in REQUIRED_SOURCES:
        assert f"`{source}`" in sources
        assert (ROOT / source).exists()
    assert "`.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`" in sources
    assert "uv run python scripts/check-local-retrieval-runtime.py --allow-unavailable" in command
    assert "does not convert fail-closed runtime statuses into success statuses" in command
    assert "The runtime status remains authoritative" in command


def test_observed_output_is_valid_safe_runtime_json() -> None:
    payload = observed_json(report_text())

    assert payload["schema_version"] == "local-retrieval-runtime-boundary/v1"
    assert payload["model_id"] == "deepvk/USER-bge-m3"
    assert payload["execution_mode"] == "local_open_weight"
    assert payload["runtime_status"] == "confirmed_runtime"
    assert payload["failure_class"] == "none"
    assert payload["diagnostic_codes"] == []
    assert payload["expected_vector_dimension"] == 1024
    assert payload["vector_dimension"] == 1024
    assert payload["managed_api_used"] is False
    assert payload["giga_chat_used"] is False
    assert payload["network_used"] is False
    assert payload["raw_vectors_persisted"] is False
    assert payload["raw_legal_text_persisted"] is False
    assert payload["provider_payload_persisted"] is False
    assert payload["source_artifacts"] == [
        "prd/retrieval/local_retrieval_runtime_boundary_contract.md",
        ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
        "pyproject.toml",
    ]


def test_dependency_versions_and_redaction_are_safe_to_publish() -> None:
    payload = observed_json(report_text())
    dependency_versions = payload["dependency_versions"]
    redaction = payload["redaction"]

    assert dependency_versions == {
        "sentence-transformers": "5.4.1",
        "torch": "2.11.0",
        "transformers": "4.51.0",
    }
    assert isinstance(redaction, dict)
    for flag in REQUIRED_REDACTION_FLAGS:
        assert redaction[flag] is True
    assert all("/" not in version for version in dependency_versions.values())


def test_safe_diagnostic_inventory_and_model_boundary_are_explicit() -> None:
    text = report_text()
    diagnostics = section(text, "## Safe diagnostic inventory")
    model = section(text, "## Model boundary")

    for code in REQUIRED_DIAGNOSTIC_CODES:
        assert f"`{code}`" in diagnostics
    assert "no diagnostic codes because the runtime was confirmed" in diagnostics
    assert "`deepvk/USER-bge-m3`" in model
    assert "`local_open_weight`" in model
    assert "expected vector dimension `1024`" in model
    assert "must not silently substitute GigaChat" in model
    assert "managed embedding API" in model
    assert "network download" in model
    assert "blocked_model_unavailable" in model


def test_non_claims_and_s03_handoff_keep_later_proof_boundaries_open() -> None:
    text = report_text()
    non_claims = section(text, "## Non-claims and open boundaries")
    handoff = section(text, "## Handoff contract for S03")

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim in non_claims
    for phrase in [
        "representative benchmark execution validates query fixtures",
        "Use `deepvk/USER-bge-m3` locally only",
        "Treat `runtime_status` as authoritative",
        "Report `vector_dimension` only when observed from real local inference",
        "Keep `GATE-G011` open",
        "Do not infer production FalkorDB behavior",
    ]:
        assert phrase in handoff


def test_report_verification_hook_matches_slice_verification() -> None:
    verification = section(report_text(), "## Verification hook")

    assert (
        "uv run pytest tests/test_local_retrieval_runtime_boundary_contract.py "
        "tests/test_local_retrieval_runtime_check_cli.py "
        "tests/test_local_retrieval_runtime_boundary_report.py -q"
    ) in verification
    assert "uv run python scripts/check-local-retrieval-runtime.py --allow-unavailable" in verification


def test_report_avoids_unsafe_raw_secret_or_local_path_payloads() -> None:
    text = report_text()

    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
