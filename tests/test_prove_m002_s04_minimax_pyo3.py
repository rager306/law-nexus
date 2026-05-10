from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


class FakeResult:
    def __init__(self, rows: list[list[object]]) -> None:
        self.result_set = rows


class FakeGraph:
    def __init__(self, *, ro_exc: Exception | None = None) -> None:
        self.query_calls: list[str] = []
        self.ro_calls: list[tuple[str, dict[str, object] | None, int | None]] = []
        self.ro_exc = ro_exc

    def query(self, query: str) -> FakeResult:
        self.query_calls.append(query)
        return FakeResult([])

    def ro_query(self, query: str, params: dict[str, object] | None = None, timeout: int | None = None) -> FakeResult:
        self.ro_calls.append((query, params, timeout))
        if self.ro_exc is not None:
            raise self.ro_exc
        return FakeResult([["article:44fz:1", "evidence:44fz:art1:span1", "sourceblock:garant:44fz:1", "raw legal text omitted"]])


class FakeClient:
    def __init__(self, graph: FakeGraph) -> None:
        self.graph = graph

    def select_graph(self, graph_name: str) -> FakeGraph:
        return self.graph


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m002-s04-minimax-pyo3.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m002_s04_minimax_pyo3", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_redact_masks_credentials_headers_and_secret_like_values() -> None:
    harness = load_harness()

    redacted = harness.redact(
        "Authorization: Bearer sk-testsecret123456789 api_key=minimax-secret token:abcd",
        sensitive_values=["minimax-secret"],
    )

    assert "Bearer sk-" not in redacted
    assert "minimax-secret" not in redacted
    assert "abcd" not in redacted
    assert "<redacted>" in redacted


def test_classify_provider_failure_codes() -> None:
    harness = load_harness()

    assert harness.classify_provider_failure("401 unauthorized invalid api key") == "minimax-auth-failed"
    assert harness.classify_provider_failure("missing field choices in response json") == "minimax-openai-schema-mismatch"
    assert harness.classify_provider_failure("resolver endpoint route failed") == "minimax-endpoint-routing-blocked"
    assert harness.classify_provider_failure("anything else") == "minimax-provider-call-failed"


def test_reasoning_contamination_detects_think_and_prose() -> None:
    harness = load_harness()

    assert harness.detect_reasoning_contamination({"has_think_tag": True})
    assert harness.detect_reasoning_contamination({"candidate_kind": "non_cypher_text"})
    assert not harness.detect_reasoning_contamination({"candidate_kind": "cypher_like", "has_think_tag": False})


def test_create_proof_project_writes_minimax_target_resolver_source(tmp_path: Path) -> None:
    harness = load_harness()

    project_dir = harness.create_proof_project(tmp_path)

    cargo = (project_dir / "Cargo.toml").read_text(encoding="utf-8")
    lib = (project_dir / "src/lib.rs").read_text(encoding="utf-8")

    assert "genai = \"0.5.3\"" in cargo
    assert "text-to-cypher" not in cargo
    assert "ServiceTargetResolver::from_resolver_fn" in lib
    assert "Endpoint::from_static(DEFAULT_MINIMAX_ENDPOINT)" in lib
    assert "AdapterKind::OpenAI" in lib
    assert "MiniMax-M2.7-highspeed" in lib
    assert "https://api.minimax.io/v1" in lib
    assert "with_normalize_reasoning_content(true)" in lib
    assert "TextToCypherClient" not in lib


def test_payload_status_prefers_specific_blockers() -> None:
    harness = load_harness()

    assert (
        harness.payload_status(
            [
                {"status": "confirmed-runtime"},
                {"status": "blocked-credential", "root_cause": "minimax-credential-missing"},
            ]
        )
        == "blocked-credential"
    )
    assert harness.payload_status([{"status": "blocked-environment"}]) == "blocked-environment"
    assert harness.payload_status([{"status": "failed-runtime"}]) == "failed-runtime"
    assert harness.payload_status([{"status": "confirmed-runtime"}]) == "confirmed-runtime"


def test_write_artifacts_preserves_boundary_language_and_safety(tmp_path: Path) -> None:
    harness = load_harness()
    payload = {
        "schema_version": harness.SCHEMA_VERSION,
        "generated_at": "2026-05-10T00:00:00Z",
        "status": "blocked-credential",
        "phase": "credential-check",
        "model": harness.DEFAULT_MODEL,
        "endpoint": harness.DEFAULT_ENDPOINT,
        "provider_attempts": 0,
        "findings": [
            {
                "id": "minimax-live-proof",
                "status": "blocked-credential",
                "phase": "credential-check",
                "root_cause": "minimax-credential-missing",
                "summary": "MiniMax API key was not present; no provider request was made.",
                "diagnostics": {"safe_category": "missing-credential"},
            }
        ],
        "commands": [],
        "boundaries": harness.boundary_payload(),
    }

    json_path, markdown_path = harness.write_artifacts(tmp_path, payload)

    machine = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert machine["status"] == "blocked-credential"
    assert "proof-only MiniMax PyO3/genai adapter route" in markdown
    assert "does not prove Legal KnowQL product behavior" in markdown
    assert "raw provider bodies are not persisted" in markdown
    assert "Authorization" not in markdown
    assert "api_key" not in markdown
    assert "sk-" not in json_path.read_text(encoding="utf-8")


def test_safe_payload_redacts_forbidden_terms_before_persisting(tmp_path: Path) -> None:
    harness = load_harness()

    json_path, markdown_path = harness.write_artifacts(
        tmp_path,
        {
            "schema_version": harness.SCHEMA_VERSION,
            "status": "failed-runtime",
            "phase": "test",
            "findings": [{"summary": "Authorization: Bearer sk-testsecret123456789"}],
            "commands": [],
            "boundaries": harness.boundary_payload(),
        },
    )

    assert "Authorization" not in json_path.read_text(encoding="utf-8")
    assert "Bearer" not in markdown_path.read_text(encoding="utf-8")
    assert "sk-testsecret" not in markdown_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("candidate", "expected_code"),
    [
        ("```cypher\nMATCH (n) RETURN n LIMIT 5\n```", "E_CANDIDATE_FORMAT"),
        ("<think>plan</think> MATCH (n) RETURN n LIMIT 5", "E_CANDIDATE_FORMAT"),
        ("MATCH (a:Article) SET a.id = 'x' RETURN a.id LIMIT 5", "E_WRITE_OPERATION"),
        (
            "MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock), (span)-[:IN_BLOCK]->(block) RETURN article.id, span.id, block.id, block.source_id",
            "E_LIMIT_REQUIRED",
        ),
        (
            "MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock), (span)-[:IN_BLOCK]->(block) RETURN article.id, span.id, block.id, block.source_id LIMIT 500",
            "E_LIMIT_EXCEEDED",
        ),
        (
            "MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock), (span)-[:IN_BLOCK]->(block) WHERE article.id = $article_id RETURN article.id, span.id, block.id, block.source_id LIMIT 5",
            "E_TEMPORAL_REQUIRED",
        ),
        (
            "MATCH (article:Article) WHERE article.valid_from <= $as_of AND $as_of < article.valid_to RETURN article.id LIMIT 5",
            "E_EVIDENCE_REQUIRED",
        ),
    ],
)
def test_generated_cypher_validation_rejects_unsafe_drafts(candidate: str, expected_code: str) -> None:
    harness = load_harness()

    report, payload = harness.validate_generated_cypher(candidate)

    assert not report.accepted
    assert expected_code in report.rejection_codes
    assert payload["execution_skipped"] is True
    assert payload["legal_answer_produced"] is False
    assert payload["report"]["normalized_query"] == "<omitted-untrusted-draft>"


def test_generated_cypher_validation_accepts_temporal_evidence_candidate() -> None:
    harness = load_harness()

    report, payload = harness.validate_generated_cypher(harness.default_safe_candidate())

    assert report.accepted
    assert payload["accepted"] is True
    assert "Graph.ro_query" not in payload["report"]["normalized_query"]
    assert "valid_from <= $as_of" in payload["report"]["normalized_query"]


def test_read_only_execution_uses_ro_query_timeout_and_safe_rows() -> None:
    harness = load_harness()
    report, _payload = harness.validate_generated_cypher(harness.default_safe_candidate())
    graph = FakeGraph()

    execution = harness.execute_validated_cypher(report, client=FakeClient(graph), graph_name="unit_s04")

    assert execution["status"] == "confirmed-runtime"
    assert execution["query_method"] == "Graph.ro_query"
    assert graph.ro_calls
    query, params, timeout = graph.ro_calls[0]
    assert query == report.normalized_query
    assert params == {"article_id": "article:44fz:1", "as_of": "2025-01-01"}
    assert timeout == 1000
    assert execution["diagnostics"]["row_count"] == 1
    assert execution["diagnostics"]["safe_identifiers"] == [["article:44fz:1", "evidence:44fz:art1:span1", "sourceblock:garant:44fz:1"]]
    assert "raw legal text omitted" not in json.dumps(execution)


def test_read_only_execution_skips_when_validation_failed() -> None:
    harness = load_harness()
    report, _payload = harness.validate_generated_cypher("DELETE (n)")
    graph = FakeGraph()

    execution = harness.execute_validated_cypher(report, client=FakeClient(graph))

    assert execution["status"] == "skipped"
    assert execution["root_cause"] == "generated-cypher-validation-failed"
    assert graph.query_calls == []
    assert graph.ro_calls == []
    assert execution["legal_answer_produced"] is False


@pytest.mark.parametrize(
    ("exc", "expected_root"),
    [
        (TimeoutError("read timeout"), "read-only-execution-timeout"),
        (RuntimeError("server failed"), "read-only-execution-failed"),
    ],
)
def test_read_only_execution_classifies_timeout_and_errors(exc: Exception, expected_root: str) -> None:
    harness = load_harness()
    report, _payload = harness.validate_generated_cypher(harness.default_safe_candidate())
    graph = FakeGraph(ro_exc=exc)

    execution = harness.execute_validated_cypher(report, client=FakeClient(graph))

    assert execution["root_cause"] == expected_root
    assert execution["legal_answer_produced"] is False


def test_write_artifacts_include_validation_execution_boundaries(tmp_path: Path) -> None:
    harness = load_harness()
    report, validation = harness.validate_generated_cypher(harness.default_safe_candidate())
    execution = harness.execute_validated_cypher(report, client=FakeClient(FakeGraph()), graph_name="unit_s04")
    payload = {
        "schema_version": harness.SCHEMA_VERSION,
        "generated_at": "2026-05-10T00:00:00Z",
        "status": "confirmed-runtime",
        "phase": "read-only-execution",
        "model": harness.DEFAULT_MODEL,
        "endpoint": harness.DEFAULT_ENDPOINT,
        "provider_attempts": 0,
        "candidate_source": "synthetic-safe-candidate",
        "validation": validation,
        "execution": execution,
        "findings": [],
        "commands": [],
        "boundaries": harness.boundary_payload(),
    }

    json_path, markdown_path = harness.write_artifacts(tmp_path, payload)

    machine = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert machine["validation"]["accepted"] is True
    assert machine["execution"]["query_method"] == "Graph.ro_query"
    assert "Validation and Read-Only Execution" in markdown
    assert "Legal answer produced: `False`" in markdown
    assert "raw legal text omitted" not in markdown
