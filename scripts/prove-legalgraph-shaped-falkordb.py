#!/usr/bin/env python3
"""Run a bounded LegalGraph-shaped synthetic topology proof against FalkorDB.

This is a runtime-mechanics proof only. It verifies that the current FalkorDB
runtime can store and traverse a LegalGraph-like topology over synthetic nodes:
Act, Article, Authority, SourceBlock, and EvidenceSpan. It does not prove ODT
parser behavior, production graph schema fitness, legal retrieval quality, or any
LLM/legal-answering product flow.
"""

from __future__ import annotations

import argparse
import importlib
import json
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/runtime-smoke/legalgraph-shaped-falkordb"
SCHEMA_VERSION = "legalgraph-shaped-falkordb-proof/v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6380

Status = Literal["confirmed-runtime", "blocked-environment", "failed-runtime"]
EvidenceClass = Literal["confirmed", "smoke-needed", "contradicted"]

FORBIDDEN_TERMS = (
    "GIGACHAT" + "_AUTH_DATA",
    "Bearer ",
    "sk-",
    "api_key",
    "BEGIN PRIVATE KEY",
)


class FalkorGraph(Protocol):
    def query(self, query: str) -> Any: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


@dataclass(frozen=True)
class QueryProof:
    proof_id: str
    status: Status
    evidence_class: EvidenceClass
    query_class: str
    expected: Mapping[str, Any]
    observed: Mapping[str, Any]
    duration_ms: float
    diagnostics: Mapping[str, Any]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        sanitized = value
        for term in FORBIDDEN_TERMS:
            sanitized = sanitized.replace(term, "[REDACTED]")
        return sanitized
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    return value


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term: {term}")


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    safe_payload = cast("Mapping[str, Any]", sanitize(dict(payload)))
    assert_safe_payload(safe_payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized_path(path)


def write_markdown(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LegalGraph-Shaped FalkorDB Runtime Proof",
        "",
        "## Boundary",
        "",
        "This artifact is bounded synthetic runtime evidence. It proves only that this FalkorDB runtime can store and traverse a small LegalGraph-shaped topology. It does not prove ODT parsing, product ETL/import, production retrieval quality, Legal KnowQL, Legal Nexus runtime, or legal-answer correctness.",
        "",
        "## Runtime",
        "",
        f"- Schema: `{payload['schema_version']}`",
        f"- Generated: `{payload['generated_at']}`",
        f"- Graph: `{payload['graph_name']}`",
        f"- Endpoint: `{payload['endpoint']['host']}:{payload['endpoint']['port']}`",
        f"- Status: `{payload['status']}`",
        "",
        "## Query Proofs",
        "",
    ]
    for proof in payload["query_proofs"]:
        lines.extend(
            [
                f"### `{proof['proof_id']}`",
                "",
                f"- Status: `{proof['status']}`",
                f"- Query class: `{proof['query_class']}`",
                f"- Expected: `{json.dumps(proof['expected'], ensure_ascii=False, sort_keys=True)}`",
                f"- Observed: `{json.dumps(proof['observed'], ensure_ascii=False, sort_keys=True)}`",
                f"- Duration: `{proof['duration_ms']}ms`",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Classification",
            "",
            "- `confirmed-runtime`: synthetic topology storage/traversal mechanics for the listed query proofs only.",
            "- `not-proven`: production graph schema fitness, legal retrieval quality, parser behavior, Legal KnowQL, Legal Nexus runtime, and legal-answer correctness.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return normalized_path(path)


def query_result_set(graph: FalkorGraph, query: str) -> tuple[list[list[Any]], float]:
    started = time.monotonic()
    result = graph.query(query)
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    rows = getattr(result, "result_set", result)
    if not isinstance(rows, list):
        rows = list(rows)
    return cast("list[list[Any]]", rows), duration_ms


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
            graph = client.select_graph(f"readiness_{uuid.uuid4().hex[:8]}")
            query_result_set(graph, "RETURN 1")
            return client
        except Exception as exc:  # noqa: BLE001 - classify environment readiness failures
            last_error = exc
            time.sleep(0.5)
    raise TimeoutError(f"FalkorDB readiness timeout: {last_error}")


def setup_graph(graph: FalkorGraph) -> None:
    query_result_set(graph, "MATCH (n) DETACH DELETE n")
    query_result_set(
        graph,
        """
        CREATE
          (:Act {id:'act:44fz', title_hash:'sha256:act-title', jurisdiction:'RU', status:'active'}),
          (:Article {id:'article:44fz:1', number:'1', valid_from:'2024-01-01', valid_to:'9999-12-31', text_hash:'sha256:article-1'}),
          (:Article {id:'article:44fz:2', number:'2', valid_from:'2024-01-01', valid_to:'9999-12-31', text_hash:'sha256:article-2'}),
          (:Authority {id:'authority:minfin', level:'federal', name_hash:'sha256:authority-minfin'}),
          (:SourceBlock {id:'sourceblock:garant:44fz:1', source_id:'garant-44fz-synthetic', block_hash:'sha256:sourceblock-1'}),
          (:EvidenceSpan {id:'evidence:44fz:art1:span1', span_hash:'sha256:evidence-1', start_offset:0, end_offset:42})
        """,
    )
    query_result_set(
        graph,
        """
        MATCH
          (act:Act {id:'act:44fz'}),
          (a1:Article {id:'article:44fz:1'}),
          (a2:Article {id:'article:44fz:2'}),
          (authority:Authority {id:'authority:minfin'}),
          (block:SourceBlock {id:'sourceblock:garant:44fz:1'}),
          (span:EvidenceSpan {id:'evidence:44fz:art1:span1'})
        CREATE
          (act)-[:HAS_ARTICLE {ordinal:1}]->(a1),
          (act)-[:HAS_ARTICLE {ordinal:2}]->(a2),
          (a2)-[:CITES {kind:'synthetic-cross-reference'}]->(a1),
          (authority)-[:ISSUED]->(act),
          (a1)-[:SUPPORTED_BY]->(block),
          (span)-[:IN_BLOCK]->(block),
          (span)-[:SUPPORTS]->(a1)
        """,
    )


def exact_row(rows: Sequence[Sequence[Any]]) -> list[Any]:
    if len(rows) != 1:
        raise AssertionError(f"expected exactly one row, got {rows!r}")
    return list(rows[0])


def build_proof(
    proof_id: str,
    query_class: str,
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    duration_ms: float,
) -> QueryProof:
    if dict(expected) != dict(observed):
        return QueryProof(
            proof_id,
            "failed-runtime",
            "contradicted",
            query_class,
            expected,
            observed,
            duration_ms,
            {"root_cause": "unexpected-result", "detail": "Observed query result did not match expected synthetic contract."},
        )
    return QueryProof(
        proof_id,
        "confirmed-runtime",
        "confirmed",
        query_class,
        expected,
        observed,
        duration_ms,
        {"root_cause": "none", "detail": "Synthetic query result matched expected contract."},
    )


def run_query_proofs(graph: FalkorGraph) -> list[QueryProof]:
    proofs: list[QueryProof] = []

    rows, duration = query_result_set(
        graph,
        """
        MATCH (act:Act), (article:Article), (authority:Authority), (block:SourceBlock), (span:EvidenceSpan)
        RETURN count(DISTINCT act), count(DISTINCT article), count(DISTINCT authority), count(DISTINCT block), count(DISTINCT span)
        """,
    )
    act_count, article_count, authority_count, block_count, span_count = exact_row(rows)
    proofs.append(
        build_proof(
            "legalgraph-node-counts",
            "label-cardinality",
            {"acts": 1, "articles": 2, "authorities": 1, "source_blocks": 1, "evidence_spans": 1},
            {
                "acts": act_count,
                "articles": article_count,
                "authorities": authority_count,
                "source_blocks": block_count,
                "evidence_spans": span_count,
            },
            duration,
        )
    )

    rows, duration = query_result_set(
        graph,
        """
        MATCH (:Article {id:'article:44fz:2'})-[:CITES]->(target:Article)<-[:HAS_ARTICLE]-(act:Act)
        RETURN act.id, target.id
        """,
    )
    act_id, target_id = exact_row(rows)
    proofs.append(
        build_proof(
            "legalgraph-citation-to-act",
            "citation-traversal",
            {"act_id": "act:44fz", "target_article_id": "article:44fz:1"},
            {"act_id": act_id, "target_article_id": target_id},
            duration,
        )
    )

    rows, duration = query_result_set(
        graph,
        """
        MATCH (authority:Authority)-[:ISSUED]->(:Act)-[:HAS_ARTICLE]->(article:Article)
        RETURN authority.id, collect(article.id)
        """,
    )
    authority_id, article_ids = exact_row(rows)
    proofs.append(
        build_proof(
            "legalgraph-authority-chain",
            "authority-act-article-traversal",
            {"authority_id": "authority:minfin", "article_ids": ["article:44fz:1", "article:44fz:2"]},
            {"authority_id": authority_id, "article_ids": sorted(article_ids)},
            duration,
        )
    )

    rows, duration = query_result_set(
        graph,
        """
        MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock), (span)-[:IN_BLOCK]->(block)
        RETURN span.id, article.id, block.id
        """,
    )
    span_id, article_id, block_id = exact_row(rows)
    proofs.append(
        build_proof(
            "legalgraph-evidence-chain",
            "evidence-sourceblock-article-traversal",
            {
                "span_id": "evidence:44fz:art1:span1",
                "article_id": "article:44fz:1",
                "source_block_id": "sourceblock:garant:44fz:1",
            },
            {"span_id": span_id, "article_id": article_id, "source_block_id": block_id},
            duration,
        )
    )

    rows, duration = query_result_set(
        graph,
        """
        MATCH (article:Article)
        WHERE article.valid_from <= '2025-01-01' AND '2025-01-01' < article.valid_to
        RETURN count(article)
        """,
    )
    (active_count,) = exact_row(rows)
    proofs.append(
        build_proof(
            "legalgraph-temporal-filter",
            "validity-window-filter",
            {"active_article_count": 2},
            {"active_article_count": active_count},
            duration,
        )
    )
    return proofs


def payload_status(proofs: Sequence[QueryProof]) -> Status:
    if all(proof.status == "confirmed-runtime" for proof in proofs):
        return "confirmed-runtime"
    return "failed-runtime"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--graph-name", default=f"legalgraph_shape_{uuid.uuid4().hex[:10]}")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--readiness-timeout", type=int, default=20)
    parser.add_argument("--keep-graph", action="store_true", help="Do not cleanup synthetic graph nodes after proof.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    graph_name = args.graph_name
    started = time.monotonic()
    generated_at = utc_now()

    try:
        client = wait_for_falkordb(args.host, args.port, args.readiness_timeout)
        graph = client.select_graph(graph_name)
        setup_graph(graph)
        proofs = run_query_proofs(graph)
        cleanup_status = "kept" if args.keep_graph else "deleted"
        if not args.keep_graph:
            query_result_set(graph, "MATCH (n) DETACH DELETE n")
    except Exception as exc:  # noqa: BLE001 - write terminal diagnostic artifact
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "status": "blocked-environment",
            "endpoint": {"host": args.host, "port": args.port},
            "graph_name": graph_name,
            "duration_ms": duration_ms,
            "query_proofs": [],
            "diagnostics": {
                "root_cause": type(exc).__name__,
                "detail": str(exc),
            },
            "boundary": "bounded synthetic LegalGraph-shaped runtime mechanics only; no product/legal-quality proof",
        }
        json_path = write_json(output_dir / "LEGALGRAPH-SHAPED-FALKORDB-PROOF.json", payload)
        print(f"LegalGraph-shaped FalkorDB proof blocked. artifact={json_path}")
        return 2

    duration_ms = round((time.monotonic() - started) * 1000, 2)
    proof_payloads = [
        {
            "proof_id": proof.proof_id,
            "status": proof.status,
            "evidence_class": proof.evidence_class,
            "query_class": proof.query_class,
            "expected": dict(proof.expected),
            "observed": dict(proof.observed),
            "duration_ms": proof.duration_ms,
            "diagnostics": dict(proof.diagnostics),
        }
        for proof in proofs
    ]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": payload_status(proofs),
        "endpoint": {"host": args.host, "port": args.port},
        "graph_name": graph_name,
        "duration_ms": duration_ms,
        "cleanup_status": cleanup_status,
        "query_proofs": proof_payloads,
        "claim_boundary": {
            "confirmed_runtime": "Synthetic LegalGraph-shaped node/edge storage and traversal mechanics for this FalkorDB runtime.",
            "not_proven": [
                "Garant ODT parsing behavior",
                "production graph schema fitness",
                "Legal KnowQL or Legal Nexus runtime",
                "legal retrieval quality",
                "legal-answer correctness",
                "LLM authority",
            ],
        },
    }
    json_path = write_json(output_dir / "LEGALGRAPH-SHAPED-FALKORDB-PROOF.json", payload)
    markdown_path = write_markdown(output_dir / "LEGALGRAPH-SHAPED-FALKORDB-PROOF.md", payload)
    print(f"LegalGraph-shaped FalkorDB proof {payload['status']}. json={json_path} markdown={markdown_path}")
    return 0 if payload["status"] == "confirmed-runtime" else 1


if __name__ == "__main__":
    raise SystemExit(main())
