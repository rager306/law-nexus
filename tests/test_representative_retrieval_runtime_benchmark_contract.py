from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/representative_retrieval_runtime_benchmark_contract.md"

REQUIRED_SECTIONS = [
    "# Representative Retrieval Runtime Benchmark Contract",
    "## Source artifacts and default inputs",
    "## Executable proof behavior",
    "## Status values and failure classes",
    "## Stdout JSON schema",
    "## Metrics and thresholds",
    "## Metric input boundaries",
    "## Redaction and forbidden payload fields",
    "## Managed provider and network policy",
    "## Durable proof report",
    "## Non-claims",
    "## Implementation checklist",
    "## Verification hook",
]

REQUIRED_SOURCE_REFERENCES = [
    "prd/retrieval/local_retrieval_runtime_boundary_contract.md",
    "prd/retrieval/local_retrieval_runtime_boundary_proof.md",
    "scripts/check-local-retrieval-runtime.py",
    "prd/retrieval/representative_retrieval_corpus_contract.md",
    "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json",
    "prd/retrieval/representative_retrieval_corpus_manifest.md",
]

CLI_PATH = "scripts/verify-representative-retrieval-runtime-benchmark.py"
SCHEMA_VERSION = "representative-retrieval-runtime-benchmark-proof/v1"
MANIFEST_SCHEMA_VERSION = "representative-retrieval-corpus/v1"

REQUIRED_STATUSES = [
    "metrics_confirmed",
    "blocked_runtime",
    "blocked_manifest",
    "blocked_metric",
    "blocked_policy_violation",
    "blocked_unsafe_artifact",
    "not_run_contract_only",
]

REQUIRED_FAILURE_CLASSES = [
    "none",
    "runtime_boundary",
    "manifest_input",
    "metric_threshold",
    "policy_violation",
    "unsafe_artifact",
    "internal_error",
]

REQUIRED_DIAGNOSTIC_CODES = [
    "RRB_RUNTIME_DIAGNOSTIC_MISSING",
    "RRB_RUNTIME_DIAGNOSTIC_MALFORMED",
    "RRB_RUNTIME_TIMEOUT",
    "RRB_RUNTIME_NOT_CONFIRMED",
    "RRB_MANIFEST_MISSING",
    "RRB_MANIFEST_MALFORMED",
    "RRB_MANIFEST_SCHEMA_MISMATCH",
    "RRB_MANIFEST_UNSAFE_PAYLOAD",
    "RRB_METRIC_THRESHOLD_MISSED",
    "RRB_MANAGED_API_FORBIDDEN",
    "RRB_GIGACHAT_FORBIDDEN",
    "RRB_RAW_TEXT_FORBIDDEN",
    "RRB_RAW_QUERY_FORBIDDEN",
    "RRB_RAW_VECTOR_FORBIDDEN",
    "RRB_PROVIDER_PAYLOAD_FORBIDDEN",
    "RRB_RAW_FALKORDB_ROW_FORBIDDEN",
    "RRB_UNSAFE_PATH_FORBIDDEN",
    "RRB_GATE_OVERCLAIM_FORBIDDEN",
    "RRB_INTERNAL_ERROR_REDACTED",
]

REQUIRED_JSON_FIELDS = [
    "schema_version",
    "benchmark_id",
    "benchmark_status",
    "failure_class",
    "diagnostic_codes",
    "runtime_boundary_confirmed",
    "runtime_diagnostic",
    "manifest",
    "metrics",
    "thresholds",
    "metric_inputs",
    "source_artifacts",
    "redaction",
    "managed_api_used",
    "giga_chat_used",
    "network_used",
    "non_claims",
    "gate",
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

FORBIDDEN_PAYLOAD_TERMS = [
    "raw query text",
    "raw legal text",
    "user prompts",
    "generated legal-answer prose",
    "legal advice",
    "provider payloads",
    "provider trace IDs",
    "credentials",
    "secrets",
    "environment variable values",
    "absolute local paths",
    "raw embedding arrays",
    "vectors",
    "raw FalkorDB rows",
    "managed-API evidence",
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
    "does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice",
    "does not make LLM output legal authority",
    "does not close `GATE-G011`; `GATE-G011` remains open",
]

FORBIDDEN_SUCCESS_WORDING = [
    "GATE-G011 is closed",
    "closes GATE-G011",
    "managed API fallback is allowed",
    "managed embedding API fallback is allowed",
    "GigaChat fallback is allowed",
    "raw legal text persistence is allowed",
    "raw query text persistence is allowed",
    "raw vectors persistence is allowed",
    "provider payload persistence is allowed",
    "raw FalkorDB row persistence is allowed",
]


def contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def assert_terms_present(text: str, terms: list[str]) -> None:
    for term in terms:
        assert term in text, term


def test_contract_file_exists_and_required_sections_are_ordered() -> None:
    assert CONTRACT_PATH.exists()
    text = contract_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_schema_cli_and_s01_s02_inputs_are_declared() -> None:
    text = contract_text()
    sources = section(text, "## Source artifacts and default inputs")
    behavior = section(text, "## Executable proof behavior")

    assert SCHEMA_VERSION in text
    assert f"uv run python {CLI_PATH}" in sources
    assert f"`{CLI_PATH}`" in sources
    assert_terms_present(sources, REQUIRED_SOURCE_REFERENCES)
    assert "consume S01 runtime diagnostics" in sources
    assert "consume S02 manifest data" in sources
    assert "`.gsd/exec`" in sources
    assert "absolute host paths" in sources
    assert MANIFEST_SCHEMA_VERSION in behavior
    assert "one compact JSON object to stdout" in behavior
    assert "durable proof report" in behavior


def test_statuses_fail_closed_failure_classes_and_diagnostic_codes_are_closed() -> None:
    text = contract_text()
    statuses = section(text, "## Status values and failure classes")

    assert_terms_present(statuses, REQUIRED_STATUSES)
    assert_terms_present(statuses, REQUIRED_FAILURE_CLASSES)
    assert_terms_present(statuses, REQUIRED_DIAGNOSTIC_CODES)
    assert "exit `0`" in statuses
    assert "non-zero" in statuses
    assert "Runtime timeout must be `blocked_runtime`" in statuses
    assert "Malformed diagnostic JSON must be `blocked_runtime`" in statuses
    assert "Malformed or missing S01 or S02 inputs must be classified as blocker/unsafe" in statuses


def test_stdout_schema_declares_required_fields_and_payload_exclusions() -> None:
    text = contract_text()
    schema = section(text, "## Stdout JSON schema")

    assert "exactly one compact JSON object to stdout" in schema
    assert f"Must be exactly `{SCHEMA_VERSION}`" in schema
    assert_terms_present(schema, REQUIRED_JSON_FIELDS)
    assert "Must be `false`" in schema
    assert "GATE-G011" in schema
    assert "gate remains open" in schema
    assert_terms_present(schema, FORBIDDEN_PAYLOAD_TERMS)


def test_metrics_and_thresholds_are_predeclared_at_one_point_zero() -> None:
    text = contract_text()
    metrics = section(text, "## Metrics and thresholds")

    assert "predeclare exactly these metrics and thresholds" in metrics
    for metric in REQUIRED_METRICS:
        assert f"`{metric}`" in metrics
    assert metrics.count("| `1.0` |") == len(REQUIRED_METRICS)
    assert "query_labels.expected_relevant_reference_ids" in metrics
    assert "candidate_references.reference_role" in metrics
    assert "They are not product retrieval quality" in metrics
    assert "not legal correctness" in metrics
    assert "No additional metric may be emitted" in metrics


def test_metric_input_boundaries_use_manifest_ids_only() -> None:
    text = contract_text()
    boundaries = section(text, "## Metric input boundaries")

    assert_terms_present(
        boundaries,
        [
            "query_labels.query_label_id",
            "expected_relevant_reference_ids",
            "candidate_references.reference_id",
            "candidate_references.reference_role",
            "Metric output must use manifest IDs only",
            "QRL-M016-*",
            "RC-M016-*",
            "COV-M016-*",
        ],
    )
    assert_terms_present(boundaries, FORBIDDEN_PAYLOAD_TERMS[:8])
    assert "raw FalkorDB rows" in boundaries
    assert "absolute paths" in boundaries


def test_redaction_boundaries_forbid_payload_fields_and_managed_api_evidence() -> None:
    text = contract_text()
    redaction = section(text, "## Redaction and forbidden payload fields")

    assert_terms_present(redaction, REDACTION_FIELDS)
    assert redaction.count("`false`") >= len(REDACTION_FIELDS)
    for field_name in [
        "raw_legal_text",
        "query_text",
        "vector",
        "embedding_vector",
        "provider_payload",
        "managed_api_payload",
        "raw_falkordb_row",
        "secret",
        "token",
        "generated_answer",
        "legal_advice",
    ]:
        assert f"`{field_name}`" in redaction
    assert "managed-API evidence" in redaction


def test_managed_provider_policy_has_no_fallback_or_network_escape() -> None:
    text = contract_text()
    policy = section(text, "## Managed provider and network policy")

    assert_terms_present(
        policy,
        [
            "must not use, call, import as a required execution path, configure, or fall back",
            "GigaChat",
            "GigaChat API",
            "GigaEmbeddings",
            "GIGACHAT_AUTH_DATA",
            "managed embedding APIs",
            "hosted LLM APIs",
            "remote vector stores",
            "managed_api_used` as `false`",
            "giga_chat_used` as `false`",
            "network_used` as `false`",
            "fail-closed runtime blocker instead of falling back to a managed API",
        ],
    )


def test_non_claims_keep_gate_g011_open_and_non_authoritative() -> None:
    text = contract_text()
    non_claims = section(text, "## Non-claims")

    assert_terms_present(non_claims, REQUIRED_NON_CLAIMS)
    assert "`GATE-G011` remains open until a later milestone validation explicitly closes it" in non_claims


def test_implementation_checklist_preserves_fail_closed_runtime_contract() -> None:
    text = contract_text()
    checklist = section(text, "## Implementation checklist")

    assert f"`{CLI_PATH}`" in checklist
    assert "scripts/check-local-retrieval-runtime.py" in checklist
    assert "confirmed local/open-weight S01 diagnostics" in checklist
    assert "representative_retrieval_corpus_manifest.json" in checklist
    assert "compute only the predeclared metrics" in checklist
    assert "exit `0` only for `metrics_confirmed`" in checklist
    assert "every other status must exit non-zero" in checklist
    assert "keep `GATE-G011` open" in checklist


def test_negative_forbidden_success_claims_are_absent() -> None:
    text = contract_text()
    for forbidden in FORBIDDEN_SUCCESS_WORDING:
        assert forbidden not in text

    assert "does not close `GATE-G011`" in text
    assert "instead of falling back to a managed API" in text
    assert "must not store raw payloads" in text


def test_negative_missing_required_terms_would_be_detected() -> None:
    text = contract_text()
    required_terms = [SCHEMA_VERSION, CLI_PATH, "runtime_boundary_confirmed", "GATE-G011"]
    mutated = text
    for term in required_terms:
        mutated = mutated.replace(term, "")

    for term in required_terms:
        assert term not in mutated
        assert term in text


def test_metric_table_contains_only_required_metric_names() -> None:
    text = contract_text()
    metrics = section(text, "## Metrics and thresholds")
    table_metric_names = re.findall(r"^\| `(.*?)` \|", metrics, flags=re.MULTILINE)

    assert table_metric_names == REQUIRED_METRICS
