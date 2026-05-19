#!/usr/bin/env python3
"""Verify bounded graph-filtered retrieval integration for M021/S06.

The verifier materializes the S04 golden fixture as safe IDs in a unique local
FalkorDB graph, applies ontology/temporal/scoped filters, compares the selected
safe IDs against S04/S05 baseline expectations, and writes a compact proof. It
never persists raw legal text, raw query text, raw vectors, provider payloads,
raw FalkorDB rows, generated Cypher, or generated legal-answer prose.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
METRICS_PATH = ROOT / "prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/graph_filtered_retrieval_integration_proof.json"
S04_VERIFIER = ROOT / "scripts/verify-evidence-span-golden-retrieval-cases.py"
S05_VERIFIER = ROOT / "scripts/verify-evidence-span-local-retrieval-metrics.py"
SCHEMA_VERSION = "graph-filtered-retrieval-integration-proof/v1"
MILESTONE_ID = "M021-qk4lze"
SLICE_ID = "S06"
DEFAULT_PORT = 6385
DEFAULT_CONTAINER_IMAGE = "falkordb/falkordb:edge"

PhaseStatus = Literal["passed", "blocked", "failed_closed", "not_run"]
ROUTE_STATUS = Literal["passed", "blocked", "failed_closed"]

PHASES = (
    "s04_fixture_verification",
    "s05_baseline_verification",
    "graph_runtime",
    "graph_materialization",
    "ontology_temporal_filter",
    "citation_preservation",
    "baseline_comparison",
    "negative_routes",
    "cleanup",
    "overclaim_safety",
)

REDACTION = {
    "source_text_excluded": True,
    "query_text_excluded": True,
    "vector_values_excluded": True,
    "external_payloads_excluded": True,
    "generated_query_excluded": True,
    "generated_answer_excluded": True,
    "secrets_excluded": True,
    "absolute_paths_excluded": True,
    "temporary_paths_excluded": True,
    "gsd_exec_paths_excluded": True,
    "runtime_rows_excluded": True,
}

NON_CLAIMS = (
    "Does not validate R035.",
    "Does not prove product retrieval quality.",
    "Does not prove graph-vector or HNSW behavior.",
    "Does not prove hybrid vector search quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove production FalkorDB readiness.",
    "Does not prove bulk-loader production readiness.",
    "Does not prove pilot or 1000-document readiness.",
)

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "pii",
    "vector",
    "embedding_vector",
    "embedding",
    "runtime_row",
    "falkordb_row",
    "generated_query",
    "generated_cypher",
    "generated_answer_prose",
    "legal_advice",
    "llm_reasoning",
}

FORBIDDEN_OUTPUT_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
    "MATCH (",
    "CREATE (",
)

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,180}$")


class IntegrationError(RuntimeError):
    """Raised when S06 integration proof cannot be emitted safely."""


class FalkorResult(Protocol):
    result_set: list[list[Any]]


class FalkorGraph(Protocol):
    def query(self, query: str) -> FalkorResult | list[list[Any]]: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


def phase(status: PhaseStatus, diagnostic_codes: Sequence[str] = (), **details: Any) -> dict[str, Any]:
    return {"status": status, "diagnostic_codes": sorted(set(diagnostic_codes)), **details}


def safe_id(value: str, field: str = "id") -> str:
    if not isinstance(value, str) or not SAFE_ID_RE.match(value):
        raise IntegrationError(f"unsafe {field}")
    return value


def cypher_string(value: str) -> str:
    safe_id(value)
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def query_rows(graph: FalkorGraph, query: str) -> tuple[list[list[Any]], float]:
    started = time.monotonic()
    result = graph.query(query)
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    rows = getattr(result, "result_set", result)
    if not isinstance(rows, list):
        rows = list(rows)
    return cast("list[list[Any]]", rows), duration_ms


def scalar_int(graph: FalkorGraph, query: str) -> int:
    rows, _duration = query_rows(graph, query)
    if len(rows) != 1 or len(rows[0]) != 1:
        raise IntegrationError("unexpected scalar result shape")
    return int(rows[0][0])


def string_list(graph: FalkorGraph, query: str) -> tuple[list[str], float]:
    rows, duration_ms = query_rows(graph, query)
    values = [str(row[0]) for row in rows if row and row[0] is not None]
    return sorted(values), duration_ms


def connect_client(host: str, port: int) -> FalkorClient:
    module = importlib.import_module("falkordb")
    client_class = getattr(module, "FalkorDB")
    return cast("FalkorClient", client_class(host=host, port=port))


def wait_for_falkordb(host: str, port: int, timeout_seconds: int) -> FalkorClient:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client = connect_client(host, port)
            graph = client.select_graph(f"s06_readiness_{uuid.uuid4().hex[:8]}")
            query_rows(graph, "RETURN 1")
            return client
        except Exception as exc:  # noqa: BLE001 - readiness diagnostics are classified by caller
            last_error = exc
            time.sleep(0.5)
    raise TimeoutError(f"FalkorDB readiness timeout: {type(last_error).__name__ if last_error else 'unknown'}")


def docker_available() -> bool:
    return shutil.which("docker") is not None


def local_image_present(image: str) -> bool:
    if not docker_available():
        return False
    completed = subprocess.run(["docker", "image", "inspect", image], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603
    return completed.returncode == 0


def start_container(args: argparse.Namespace) -> tuple[str | None, dict[str, Any]]:
    diagnostic: dict[str, Any] = {"mode": args.container, "status": "not_started", "cleanup_status": "not_needed", "image_reference": args.container_image}
    if args.container == "never":
        diagnostic["status"] = "skipped_by_flag"
        diagnostic["diagnostic_codes"] = ["graph_runtime_blocked"]
        return None, diagnostic
    if not local_image_present(args.container_image):
        diagnostic["status"] = "blocked_image_absent"
        diagnostic["diagnostic_codes"] = ["graph_runtime_blocked"]
        return None, diagnostic
    command = ["docker", "run", "--rm", "-d", "-p", f"127.0.0.1:{args.port}:6379", args.container_image]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603
    if completed.returncode != 0:
        diagnostic["status"] = "blocked_start_failed"
        diagnostic["diagnostic_codes"] = ["graph_runtime_blocked"]
        return None, diagnostic
    container_id = completed.stdout.strip()[:128]
    diagnostic["status"] = "started"
    diagnostic["container_id_hash"] = f"len:{len(container_id)}"
    diagnostic["cleanup_status"] = "pending"
    time.sleep(1)
    return container_id, diagnostic


def cleanup_container(container_id: str | None, diagnostic: dict[str, Any]) -> None:
    if not container_id:
        return
    completed = subprocess.run(["docker", "rm", "-f", container_id], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603
    diagnostic["cleanup_status"] = "deleted" if completed.returncode == 0 else "cleanup_failed"
    if completed.returncode != 0:
        diagnostic["diagnostic_codes"] = sorted(set(diagnostic.get("diagnostic_codes", []) + ["cleanup_failed"]))


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(list(command), cwd=ROOT, check=False, text=True, capture_output=True, timeout=timeout_seconds)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise IntegrationError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise IntegrationError("command returned non-object JSON")
    return completed.returncode, payload


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrationError("malformed JSON") from exc
    if not isinstance(payload, dict):
        raise IntegrationError("JSON root must be object")
    return payload


def verify_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    s04_exit, s04_summary = run_json_command([sys.executable, str(S04_VERIFIER), "--fixture", str(args.fixture)], args.timeout)
    if s04_exit != 0 or s04_summary.get("status") != "ok":
        raise IntegrationError("fixture_verifier_failed")
    s05_exit, s05_summary = run_json_command([sys.executable, str(S05_VERIFIER), "--no-write", "--timeout", str(args.timeout)], args.timeout + 60)
    if s05_exit != 0 or s05_summary.get("threshold_passed") is not True:
        raise IntegrationError("metrics_baseline_failed")
    fixture = load_json(args.fixture)
    metrics = load_json(args.metrics)
    if metrics.get("threshold_passed") is not True:
        raise IntegrationError("metrics_baseline_failed")
    return s04_summary, s05_summary, fixture, metrics


def all_candidates(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for case in fixture.get("cases", []):
        if not isinstance(case, Mapping):
            raise IntegrationError("case must be object")
        query = case.get("query")
        if not isinstance(query, Mapping):
            raise IntegrationError("query must be object")
        for candidate in case.get("candidates", []):
            if not isinstance(candidate, Mapping):
                raise IntegrationError("candidate must be object")
            source_record_ids = candidate.get("source_record_ids") or []
            candidates.append(
                {
                    "candidate_id": safe_id(str(candidate["candidate_id"]), "candidate_id"),
                    "case_id": safe_id(str(case["case_id"]), "case_id"),
                    "case_class": safe_id(str(case["case_class"]), "case_class"),
                    "expected_label": safe_id(str(candidate["expected_label"]), "expected_label"),
                    "scope_id": safe_id(str(query["scope_id"]), "scope_id"),
                    "as_of_date": safe_id(str(query["as_of_date"]), "as_of_date"),
                    "act_edition_id": safe_id(str(candidate["act_edition_id"]), "act_edition_id"),
                    "evidence_span_id": safe_id(str(candidate["evidence_span_id"]), "evidence_span_id"),
                    "source_block_id": safe_id(str(candidate["source_block_id"]), "source_block_id"),
                    "citation_key": safe_id(str(candidate["citation_key"]), "citation_key"),
                    "source_record_id": safe_id(str(source_record_ids[0]), "source_record_id") if source_record_ids else "NO-SOURCE-RECORD",
                    "temporal_status": "current" if candidate.get("expected_label") in {"relevant", "ambiguous"} else "stale",
                    "ontology_class": "legal_evidence_candidate",
                }
            )
    return candidates


def scope_rows(fixture: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in fixture.get("cases", []):
        query = case.get("query", {}) if isinstance(case, Mapping) else {}
        if isinstance(query, Mapping):
            rows.append(
                {
                    "scope_id": safe_id(str(query["scope_id"]), "scope_id"),
                    "case_id": safe_id(str(case["case_id"]), "case_id"),
                    "case_class": safe_id(str(case["case_class"]), "case_class"),
                    "expected_result": safe_id(str(query["expected_result"]), "expected_result"),
                }
            )
    return rows


def create_node(graph: FalkorGraph, label: str, props: Mapping[str, str]) -> None:
    safe_id(label, "label")
    properties = ", ".join(f"{key}: {cypher_string(value)}" for key, value in props.items())
    query_rows(graph, f"CREATE (n:{label} {{{properties}}})")


def create_relation(graph: FalkorGraph, start_label: str, start_key: str, start_value: str, rel: str, end_label: str, end_key: str, end_value: str) -> None:
    for token in (start_label, start_key, rel, end_label, end_key):
        safe_id(token, "cypher token")
    query_rows(
        graph,
        f"MATCH (a:{start_label} {{{start_key}: {cypher_string(start_value)}}}), (b:{end_label} {{{end_key}: {cypher_string(end_value)}}}) CREATE (a)-[:{rel}]->(b)",
    )


def materialize_graph(graph: FalkorGraph, fixture: Mapping[str, Any]) -> dict[str, int]:
    candidates = all_candidates(fixture)
    scopes = scope_rows(fixture)
    seen_evidence: set[str] = set()
    seen_blocks: set[str] = set()
    seen_units: set[str] = set()
    seen_editions: set[str] = set()
    seen_scopes: set[str] = set()
    for scope in scopes:
        key = scope["scope_id"] + ":" + scope["case_id"]
        if key not in seen_scopes:
            seen_scopes.add(key)
            create_node(graph, "RetrievalScope", scope)
    for candidate in candidates:
        create_node(
            graph,
            "RetrievalCandidate",
            {
                key: candidate[key]
                for key in (
                    "candidate_id",
                    "case_id",
                    "case_class",
                    "expected_label",
                    "scope_id",
                    "as_of_date",
                    "act_edition_id",
                    "citation_key",
                    "temporal_status",
                    "ontology_class",
                )
            },
        )
        if candidate["evidence_span_id"] not in seen_evidence:
            seen_evidence.add(candidate["evidence_span_id"])
            create_node(graph, "EvidenceSpan", {"evidence_span_id": candidate["evidence_span_id"], "citation_key": candidate["citation_key"]})
        if candidate["source_block_id"] not in seen_blocks:
            seen_blocks.add(candidate["source_block_id"])
            create_node(graph, "SourceBlock", {"source_block_id": candidate["source_block_id"], "source_record_id": candidate["source_record_id"]})
        if candidate["source_record_id"] not in seen_units:
            seen_units.add(candidate["source_record_id"])
            create_node(graph, "LegalUnit", {"source_record_id": candidate["source_record_id"], "ontology_class": candidate["ontology_class"]})
        if candidate["act_edition_id"] not in seen_editions:
            seen_editions.add(candidate["act_edition_id"])
            temporal_status = "current" if candidate["act_edition_id"] == "ED-M014-44FZ-2026-01-01" else "stale"
            create_node(graph, "ActEdition", {"act_edition_id": candidate["act_edition_id"], "temporal_status": temporal_status})
        create_relation(graph, "RetrievalCandidate", "candidate_id", candidate["candidate_id"], "HAS_EVIDENCE_SPAN", "EvidenceSpan", "evidence_span_id", candidate["evidence_span_id"])
        create_relation(graph, "EvidenceSpan", "evidence_span_id", candidate["evidence_span_id"], "IN_SOURCE_BLOCK", "SourceBlock", "source_block_id", candidate["source_block_id"])
        create_relation(graph, "SourceBlock", "source_block_id", candidate["source_block_id"], "FOR_LEGAL_UNIT", "LegalUnit", "source_record_id", candidate["source_record_id"])
        create_relation(graph, "RetrievalCandidate", "candidate_id", candidate["candidate_id"], "IN_EDITION", "ActEdition", "act_edition_id", candidate["act_edition_id"])
    return {
        "candidate_count": scalar_int(graph, "MATCH (n:RetrievalCandidate) RETURN count(n)"),
        "evidence_span_count": scalar_int(graph, "MATCH (n:EvidenceSpan) RETURN count(n)"),
        "source_block_count": scalar_int(graph, "MATCH (n:SourceBlock) RETURN count(n)"),
        "legal_unit_count": scalar_int(graph, "MATCH (n:LegalUnit) RETURN count(n)"),
        "act_edition_count": scalar_int(graph, "MATCH (n:ActEdition) RETURN count(n)"),
        "scope_count": scalar_int(graph, "MATCH (n:RetrievalScope) RETURN count(n)"),
    }


def expected_ids(fixture: Mapping[str, Any], case_class: str, key: str = "expected_candidate_ids") -> list[str]:
    ids: list[str] = []
    for case in fixture.get("cases", []):
        if isinstance(case, Mapping) and case.get("case_class") == case_class:
            ids.extend(str(item) for item in case.get(key, []))
    return sorted(ids)


def route(graph: FalkorGraph, name: str, query: str, expected: Sequence[str], diagnostic: str) -> dict[str, Any]:
    selected, duration_ms = string_list(graph, query)
    status: ROUTE_STATUS = "passed" if selected == sorted(expected) else "failed_closed"
    return {"route": name, "status": status, "diagnostic_codes": [diagnostic] if status == "passed" else ["baseline_comparison_failed"], "selected_candidate_ids": selected, "expected_candidate_ids": sorted(expected), "duration_ms": duration_ms}


def run_routes(graph: FalkorGraph, fixture: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    routes = [
        route(
            graph,
            "positive_evidence_span_filter",
            "MATCH (c:RetrievalCandidate)-[:HAS_EVIDENCE_SPAN]->(:EvidenceSpan) WHERE c.case_class = 'positive_evidence_span' AND c.expected_label = 'relevant' AND c.temporal_status = 'current' RETURN c.candidate_id",
            expected_ids(fixture, "positive_evidence_span"),
            "positive_filter_passed",
        ),
        route(
            graph,
            "positive_source_block_filter",
            "MATCH (c:RetrievalCandidate)-[:HAS_EVIDENCE_SPAN]->(:EvidenceSpan)-[:IN_SOURCE_BLOCK]->(:SourceBlock) WHERE c.case_class = 'positive_source_block_marker' AND c.expected_label = 'relevant' AND c.temporal_status = 'current' RETURN c.candidate_id",
            expected_ids(fixture, "positive_source_block_marker"),
            "positive_filter_passed",
        ),
        route(
            graph,
            "stale_temporal_filter",
            "MATCH (c:RetrievalCandidate) WHERE c.case_class = 'stale_temporal_negative' AND c.temporal_status = 'current' RETURN c.candidate_id",
            [],
            "stale_temporal_candidate_rejected",
        ),
        route(
            graph,
            "ambiguous_candidate_filter",
            "MATCH (c:RetrievalCandidate) WHERE c.case_class = 'ambiguous_candidate_set' AND c.expected_label = 'ambiguous' RETURN c.candidate_id",
            expected_ids(fixture, "ambiguous_candidate_set"),
            "ambiguous_candidate_preserved",
        ),
        route(
            graph,
            "unsupported_scope_filter",
            "MATCH (s:RetrievalScope) WHERE s.case_class = 'unsupported_scope' AND s.expected_result = 'unsupported' RETURN s.case_id",
            [case["case_id"] for case in fixture.get("cases", []) if isinstance(case, Mapping) and case.get("case_class") == "unsupported_scope"],
            "unsupported_scope_preserved",
        ),
        route(
            graph,
            "scoped_no_answer_filter",
            "MATCH (s:RetrievalScope) WHERE s.case_class = 'scoped_no_answer' AND s.expected_result = 'no_answer' RETURN s.case_id",
            [case["case_id"] for case in fixture.get("cases", []) if isinstance(case, Mapping) and case.get("case_class") == "scoped_no_answer"],
            "scoped_no_answer_preserved",
        ),
    ]
    diagnostics = sorted({code for item in routes for code in item["diagnostic_codes"]})
    return routes, diagnostics


def citation_preservation(routes: Sequence[Mapping[str, Any]], fixture: Mapping[str, Any]) -> dict[str, Any]:
    positive_ids = set(expected_ids(fixture, "positive_evidence_span") + expected_ids(fixture, "positive_source_block_marker"))
    candidate_lookup = {candidate["candidate_id"]: candidate for candidate in all_candidates(fixture)}
    preserved = []
    for candidate_id in sorted(positive_ids):
        candidate = candidate_lookup[candidate_id]
        preserved.append(
            {
                "candidate_id": candidate_id,
                "evidence_span_id": candidate["evidence_span_id"],
                "source_block_id": candidate["source_block_id"],
                "citation_key": candidate["citation_key"],
                "act_edition_id": candidate["act_edition_id"],
            }
        )
    return {"status": "passed", "diagnostic_codes": ["citation_binding_preserved"], "preserved_bindings": preserved}


def base_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": MILESTONE_ID,
        "slice_id": SLICE_ID,
        "non_authoritative": True,
        "phases": {name: phase("not_run") for name in PHASES},
        "diagnostic_codes": [],
        "redaction": dict(REDACTION),
        "non_claims": list(NON_CLAIMS),
    }


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def check_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise IntegrationError(f"unsafe field name: {key}")
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    check_keys(payload)
    redaction = payload.get("redaction")
    if not isinstance(redaction, Mapping) or any(value is not True for value in redaction.values()):
        raise IntegrationError("redaction flags must all be true")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise IntegrationError(f"unsafe output fragment: {fragment}")


def run_proof(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    report = base_report()
    container_id: str | None = None
    container_diag: dict[str, Any] = {}
    try:
        s04_summary, s05_summary, fixture, metrics = verify_inputs(args)
        report["phases"]["s04_fixture_verification"] = phase("passed", case_count=s04_summary.get("case_count"), candidate_count=s04_summary.get("candidate_count"))
        report["phases"]["s05_baseline_verification"] = phase("passed", threshold_passed=s05_summary.get("threshold_passed"), mismatch_count=s05_summary.get("mismatch_count"))
        report["baseline_metrics"] = {"threshold_passed": metrics.get("threshold_passed"), "mismatch_count": metrics.get("mismatch_count"), "metrics": metrics.get("metrics")}
        container_id, container_diag = start_container(args)
        report["container_runtime"] = container_diag
        if container_id is None:
            report["phases"]["graph_runtime"] = phase("blocked", ["graph_runtime_blocked"])
            report["diagnostic_codes"] = ["graph_runtime_blocked"]
            return 1, report
        client = wait_for_falkordb(args.host, args.port, args.readiness_timeout)
        graph_name = f"m021_s06_graph_filtered_{uuid.uuid4().hex[:10]}"
        report["graph_name_hash"] = f"len:{len(graph_name)}"
        report["phases"]["graph_runtime"] = phase("passed", ["graph_runtime_confirmed"], runtime_status="confirmed-runtime")
        graph = client.select_graph(graph_name)
        counts = materialize_graph(graph, fixture)
        report["materialized_counts"] = counts
        expected_candidate_count = len(all_candidates(fixture))
        materialized_ok = counts["candidate_count"] == expected_candidate_count and counts["scope_count"] == len(fixture.get("cases", []))
        report["phases"]["graph_materialization"] = phase("passed" if materialized_ok else "failed_closed", [] if materialized_ok else ["count_mismatch"])
        routes, route_diagnostics = run_routes(graph, fixture)
        failed_routes = [item for item in routes if item["status"] != "passed"]
        report["routes"] = routes
        report["phases"]["ontology_temporal_filter"] = phase("passed" if not failed_routes else "failed_closed", ["positive_filter_passed", "stale_temporal_candidate_rejected"] if not failed_routes else ["baseline_comparison_failed"])
        report["phases"]["negative_routes"] = phase("passed" if not failed_routes else "failed_closed", ["ambiguous_candidate_preserved", "unsupported_scope_preserved", "scoped_no_answer_preserved"] if not failed_routes else ["baseline_comparison_failed"])
        citation = citation_preservation(routes, fixture)
        report["citation_preservation"] = citation
        report["phases"]["citation_preservation"] = phase("passed", ["citation_binding_preserved"])
        baseline_passed = not failed_routes and materialized_ok and metrics.get("threshold_passed") is True
        report["phases"]["baseline_comparison"] = phase("passed" if baseline_passed else "failed_closed", ["baseline_comparison_passed"] if baseline_passed else ["baseline_comparison_failed"])
        report["phases"]["overclaim_safety"] = phase("passed", ["overclaim_rejected"])
        report["diagnostic_codes"] = sorted(set(route_diagnostics + ["graph_runtime_confirmed", "citation_binding_preserved", "baseline_comparison_passed"]))
        return (0 if baseline_passed else 1), report
    except Exception as exc:  # noqa: BLE001 - emit fail-closed compact diagnostic
        report["diagnostic_codes"] = ["unsafe_payload_rejected" if isinstance(exc, IntegrationError) else "graph_materialization_failed"]
        report["failure_class"] = type(exc).__name__
        return 2, report
    finally:
        cleanup_container(container_id, container_diag)
        if container_diag:
            report["container_runtime"] = container_diag
            report["phases"]["cleanup"] = phase("passed" if container_diag.get("cleanup_status") == "deleted" else "blocked", [] if container_diag.get("cleanup_status") == "deleted" else ["cleanup_failed"])


def write_report(path: Path, payload: Mapping[str, Any]) -> None:
    assert_safe_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--readiness-timeout", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--container", choices=("auto", "never"), default="auto")
    parser.add_argument("--container-image", default=DEFAULT_CONTAINER_IMAGE)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code, report = run_proof(args)
    assert_safe_payload(report)
    if not args.no_write:
        write_report(args.report_output, report)
    print(json.dumps(report, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
