from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd" / "retrieval" / "local_retrieval_runtime_boundary_contract.md"

REQUIRED_SECTIONS = [
    "# Local Retrieval Runtime Boundary Contract",
    "## Source artifacts",
    "## Approved runtime boundary",
    "## Forbidden runtime paths",
    "## Runtime status values",
    "## Failure classes and diagnostic codes",
    "## Safe JSON diagnostic schema",
    "### Redaction object",
    "## Pass and fail-closed semantics",
    "## Safe artifact references",
    "## Non-claims",
    "## Downstream implementation checklist",
    "## Verification hook",
]

REQUIRED_SOURCE_REFERENCES = [
    "prd/retrieval/local_retrieval_quality_benchmark_contract.md",
    ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
    ".gsd/milestones/M016/M016-CONTEXT.md",
]

REQUIRED_JSON_FIELDS = [
    "schema_version",
    "model_id",
    "execution_mode",
    "runtime_status",
    "failure_class",
    "diagnostic_codes",
    "vector_dimension",
    "dependency_versions",
    "source_artifacts",
    "redaction",
    "managed_api_used",
    "giga_chat_used",
    "network_used",
    "non_claims",
]

REQUIRED_REDACTION_FIELDS = [
    "raw_legal_text_excluded",
    "raw_query_text_excluded",
    "raw_vectors_excluded",
    "provider_payloads_excluded",
    "secrets_excluded",
    "absolute_paths_excluded",
    "legal_advice_excluded",
]

REQUIRED_STATUSES = [
    "confirmed_runtime",
    "blocked_environment",
    "blocked_model_unavailable",
    "blocked_dimension_mismatch",
    "blocked_policy_violation",
    "blocked_unsafe_artifact",
    "not_run_contract_only",
]

REQUIRED_FAILURE_CLASSES = [
    "none",
    "environment",
    "model_unavailable",
    "dimension_mismatch",
    "policy_violation",
    "unsafe_artifact",
    "internal_error",
]

REQUIRED_DIAGNOSTIC_CODES = [
    "LRR_MODEL_CACHE_MISSING",
    "LRR_DEPENDENCY_MISSING",
    "LRR_DIMENSION_MISMATCH",
    "LRR_MANAGED_API_FORBIDDEN",
    "LRR_RAW_VECTOR_FORBIDDEN",
    "LRR_RAW_TEXT_FORBIDDEN",
    "LRR_PROVIDER_PAYLOAD_FORBIDDEN",
    "LRR_UNSAFE_PATH_FORBIDDEN",
    "LRR_INTERNAL_ERROR_REDACTED",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove representative corpus quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not close GATE-G011 by itself",
    "does not authorize managed embedding API fallback",
    "does not authorize GigaChat or GigaEmbeddings runtime use",
    "does not persist raw legal text, raw query text, raw vectors, provider payloads, secrets, or legal advice",
    "does not make LLM output legal authority",
]

FORBIDDEN_SNIPPETS = [
    "/root/",
    "/tmp/",
    "BEGIN PRIVATE KEY",
    "legal advice:",
    "Настоящий Федеральный закон регулирует отношения",
]


def contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_contract_required_sections_are_present_in_order() -> None:
    text = contract_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_contract_references_required_sources_without_using_ignored_fixtures() -> None:
    text = contract_text()
    source_artifacts = section(text, "## Source artifacts")
    safe_artifacts = section(text, "## Safe artifact references")

    assert CONTRACT_PATH.exists()
    assert (ROOT / "prd" / "retrieval" / "local_retrieval_quality_benchmark_contract.md").exists()
    for artifact in REQUIRED_SOURCE_REFERENCES:
        assert f"`{artifact}`" in source_artifacts
    assert "repository-relative artifact references only" in source_artifacts
    assert "runtime smoke/check tests must not require ignored `.gsd` files as fixtures" in safe_artifacts
    assert "without copying raw logs or absolute log paths" in safe_artifacts
    assert "`.gsd/exec` paths" in safe_artifacts


def test_approved_runtime_boundary_is_user_bge_m3_local_only() -> None:
    text = contract_text()
    approved = section(text, "## Approved runtime boundary")

    assert "The only approved model" in approved
    assert "`deepvk/USER-bge-m3`" in approved
    assert "`local_open_weight`" in approved
    assert "`1024`" in approved
    for field in [
        "model_id",
        "execution_mode",
        "managed_api_used",
        "giga_chat_used",
        "raw_vectors_persisted",
        "raw_legal_text_persisted",
        "provider_payload_persisted",
        "expected_vector_dimension",
    ]:
        assert f"`{field}`" in approved
    assert "managed embedding API" in approved
    assert "external network fetch" in approved
    assert "must fail closed instead of inventing a dimension" in approved


def test_forbidden_runtime_paths_exclude_managed_api_and_gigachat() -> None:
    text = contract_text()
    forbidden = section(text, "## Forbidden runtime paths")

    for phrase in [
        "GigaChat",
        "GIGACHAT_AUTH_DATA",
        "GigaEmbeddings as a default, challenger, fallback, or replacement",
        "managed embedding APIs from any provider",
        "remote hosted LLM APIs",
        "provider response bodies",
        "network downloads during the smoke/check command",
        "must not call the provider",
    ]:
        assert phrase in forbidden
    assert "must return a fail-closed diagnostic" in forbidden


def test_statuses_failure_classes_and_codes_are_closed() -> None:
    text = contract_text()
    statuses = section(text, "## Runtime status values")
    failures = section(text, "## Failure classes and diagnostic codes")

    for status in REQUIRED_STATUSES:
        assert f"`{status}`" in statuses
    assert "Success requires `confirmed_runtime`" in statuses
    assert "Every other status is fail-closed" in statuses
    for failure_class in REQUIRED_FAILURE_CLASSES:
        assert f"`{failure_class}`" in failures
    for code in REQUIRED_DIAGNOSTIC_CODES:
        assert f"`{code}`" in failures


def test_safe_json_schema_has_required_fields_and_redaction_constraints() -> None:
    text = contract_text()
    schema = section(text, "## Safe JSON diagnostic schema")

    for field in REQUIRED_JSON_FIELDS:
        assert f"`{field}`" in schema
    for field in REQUIRED_REDACTION_FIELDS:
        assert f"`{field}`" in schema
    for phrase in [
        "one compact JSON object",
        "Must be `deepvk/USER-bge-m3`",
        "Must be `false`",
        "Integer `1024` only when observed",
        "Safe package-name/version map",
        "must not include raw query text",
        "raw embedding arrays",
        "provider request/response payloads",
        "raw FalkorDB rows",
        "generated legal advice",
        "all set to `true`",
    ]:
        assert phrase in schema


def test_pass_fail_closed_semantics_are_explicit() -> None:
    text = contract_text()
    semantics = section(text, "## Pass and fail-closed semantics")

    for phrase in [
        "passes only when all of these are true",
        "`runtime_status` is `confirmed_runtime`",
        "Local inference actually ran without managed API calls",
        "Observed `vector_dimension` is `1024`",
        "Redaction booleans are all `true`",
        "fail closed with a non-zero exit",
        "forbidden runtime path is reachable as fallback",
    ]:
        assert phrase in semantics


def test_non_claims_preserve_gate_and_legal_authority_boundaries() -> None:
    text = contract_text()
    non_claims = section(text, "## Non-claims").lower()

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in non_claims
    assert "gigaembeddings runtime use" in non_claims
    assert "gate-g011" in non_claims


def test_downstream_checklist_and_verification_hook_are_actionable() -> None:
    text = contract_text()
    checklist = section(text, "## Downstream implementation checklist")
    verification = section(text, "## Verification hook")

    for phrase in [
        "load this contract and the approved model boundary",
        "verify no managed API or GigaChat fallback",
        "probe local dependency versions",
        "execute `deepvk/USER-bge-m3` locally",
        "observe and validate vector dimension `1024`",
        "emit the safe JSON diagnostic schema",
        "exit `0` only for `confirmed_runtime`",
        "keep `GATE-G011` open",
    ]:
        assert phrase in checklist
    assert "uv run pytest tests/test_local_retrieval_runtime_boundary_contract.py -q" in verification


def test_contract_avoids_unsafe_absolute_raw_or_secret_payload_snippets() -> None:
    text = contract_text()

    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
