"""Bounded FalkorDB CSV ingest proof adapter helpers.

[bounded] M076 S15 extracts reusable CSV/count/query-plan/report mechanics
from the legacy proof script. This module does not prove production FalkorDB
readiness, graph schema correctness, retrieval quality, parser completeness,
or legal-answer correctness. Live runtime execution remains caller-owned.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

RuntimeDisposition = Literal["load_csv_passed", "blocked", "failed_closed"]

SCHEMA_VERSION = "falkordb-csv-ingest-proof/v1"
MILESTONE_ID = "M021-qk4lze"
SLICE_ID = "S02"
CONTAINER_IMPORT_DIR = "/data"

FALKORDB_CSV_INGEST_NON_CLAIMS: tuple[str, ...] = (
    "Does not validate R037 broadly; this is a bounded CSV ingest smoke.",
    "Does not validate R035 broadly; R035 remains Active.",
    "Does not prove retrieval quality, parser completeness, legal-answer correctness, graph-vector/HNSW behavior, FalkorDB production readiness, or pilot readiness.",
    "Does not prove bulk-loader scale readiness; S03 owns that separate assessment.",
)

FORBIDDEN_OUTPUT_FRAGMENTS: tuple[str, ...] = (
    "Федеральный закон",
    "Статья",
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
)


@dataclass(frozen=True)
class FalkorCsvIngestRequest:
    """Bounded request metadata for CSV ingest proof planning/reporting."""

    source_units_path: str
    source_edges_path: str
    container_mode: str
    container_image: str
    container_import_dir: str = CONTAINER_IMPORT_DIR

    @classmethod
    def from_args(
        cls, args: Any, *, source_units_path: str, source_edges_path: str
    ) -> "FalkorCsvIngestRequest":  # noqa: ANN401 - CLI args are argparse-like.
        """Create request metadata from argparse-like CLI args."""

        return cls(
            source_units_path=source_units_path,
            source_edges_path=source_edges_path,
            container_mode=str(args.container),
            container_image=str(args.container_image),
        )


@dataclass(frozen=True)
class LoadCsvQueryStep:
    """One bounded LOAD CSV proof query step."""

    name: str
    cypher: str


@dataclass(frozen=True)
class LoadCsvQueryPlan:
    """Deterministic LOAD CSV query plan metadata."""

    steps: tuple[LoadCsvQueryStep, ...]
    mechanism: str = "LOAD CSV"
    with_headers: bool = True
    type_conversion_checked: bool = True
    raw_query_text_persisted: bool = False


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """Read CSV rows as dictionaries using UTF-8 and headers."""

    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_counts_from_rows(
    units: Sequence[Mapping[str, str]], edges: Sequence[Mapping[str, str]]
) -> dict[str, int]:
    """Return the bounded source/expected graph counts for proof fixtures."""

    return {
        "expected_source_node_rows": len(units),
        "expected_source_relationship_rows": len(edges),
        "expected_node_count": len(units),
        "expected_relationship_count": len(edges),
        "expected_current_nodes": sum(
            1 for row in units if row.get("temporal_status") == "current"
        ),
        "expected_inactive_nodes": sum(
            1 for row in units if row.get("temporal_status") == "inactive"
        ),
    }


def build_load_csv_query_plan(
    *,
    node_csv_uri: str = "file:///legal_units.csv",
    edge_csv_uri: str = "file:///legal_unit_edges.csv",
) -> LoadCsvQueryPlan:
    """Return the deterministic LOAD CSV MERGE proof query plan.

    The plan uses container import URIs only. It is metadata for proof execution;
    callers decide whether/how to execute it.
    """

    return LoadCsvQueryPlan(
        steps=(
            LoadCsvQueryStep("cleanup_before_load", "MATCH (n) DETACH DELETE n"),
            LoadCsvQueryStep(
                "load_nodes_first",
                f"""
                LOAD CSV WITH HEADERS FROM '{node_csv_uri}' AS row
                MERGE (u:LegalUnit {{id: row['id']}})
                SET u.kind = row['kind'],
                    u.source_record_id = row['source_record_id'],
                    u.act_edition_id = row['act_edition_id'],
                    u.ontology_class = row['ontology_class'],
                    u.temporal_status = row['temporal_status'],
                    u.rank = toInteger(row['rank'])
                """,
            ),
            LoadCsvQueryStep(
                "load_relationships_first",
                f"""
                LOAD CSV WITH HEADERS FROM '{edge_csv_uri}' AS row
                MATCH (source:LegalUnit {{id: row['source_id']}}),
                      (target:LegalUnit {{id: row['target_id']}})
                MERGE (source)-[r:LINKS_TO {{kind: row['kind']}}]->(target)
                SET r.rank = toInteger(row['rank'])
                """,
            ),
            LoadCsvQueryStep(
                "load_nodes_second",
                f"""
                LOAD CSV WITH HEADERS FROM '{node_csv_uri}' AS row
                MERGE (u:LegalUnit {{id: row['id']}})
                SET u.kind = row['kind'],
                    u.source_record_id = row['source_record_id'],
                    u.act_edition_id = row['act_edition_id'],
                    u.ontology_class = row['ontology_class'],
                    u.temporal_status = row['temporal_status'],
                    u.rank = toInteger(row['rank'])
                """,
            ),
            LoadCsvQueryStep(
                "load_relationships_second",
                f"""
                LOAD CSV WITH HEADERS FROM '{edge_csv_uri}' AS row
                MATCH (source:LegalUnit {{id: row['source_id']}}),
                      (target:LegalUnit {{id: row['target_id']}})
                MERGE (source)-[r:LINKS_TO {{kind: row['kind']}}]->(target)
                SET r.rank = toInteger(row['rank'])
                """,
            ),
        )
    )


def build_base_report(
    request: FalkorCsvIngestRequest,
    *,
    expected_counts: Mapping[str, int],
    disposition: RuntimeDisposition,
    diagnostic_codes: Sequence[str],
) -> dict[str, Any]:
    """Return a bounded CSV ingest proof report skeleton."""

    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": MILESTONE_ID,
        "slice_id": SLICE_ID,
        "runtime_disposition": disposition,
        "loader": {
            "mechanism": "LOAD CSV",
            "with_headers": True,
            "type_conversion_checked": True,
            "raw_query_text_persisted": False,
        },
        "source_fixture_paths": [request.source_units_path, request.source_edges_path],
        "source_counts": {
            "node_rows": expected_counts["expected_source_node_rows"],
            "relationship_rows": expected_counts["expected_source_relationship_rows"],
        },
        "expected_counts": dict(expected_counts),
        "graph_counts": {},
        "idempotency": {
            "mode": "MERGE rerun",
            "status": "not_run",
            "duplicate_nodes_created": None,
            "duplicate_relationships_created": None,
        },
        "file_access": {
            "mode": "docker_import_mount",
            "container_import_folder": request.container_import_dir,
            "host_path_persisted": False,
        },
        "container_runtime": {
            "mode": request.container_mode,
            "status": "not_run",
            "cleanup_status": "not_needed",
            "image_reference": request.container_image,
        },
        "diagnostic_codes": sorted(set(diagnostic_codes)),
        "redaction": {
            "source_text_excluded": True,
            "raw_vectors_excluded": True,
            "secrets_excluded": True,
            "external_payloads_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "non_authoritative": True,
        "requirement": "R037",
        "related_requirement": "R035",
        "non_claims": list(FALKORDB_CSV_INGEST_NON_CLAIMS),
    }
    validate_safe_report(report)
    return report


def compare_graph_counts(expected: Mapping[str, int], graph: Mapping[str, int]) -> list[str]:
    """Return bounded diagnostic codes for expected/observed graph count mismatch."""

    diagnostics: list[str] = []
    if graph.get("node_count") != expected["expected_node_count"]:
        diagnostics.append("LOAD_CSV_COUNTS_MISMATCH")
    if graph.get("relationship_count") != expected["expected_relationship_count"]:
        diagnostics.append("LOAD_CSV_COUNTS_MISMATCH")
    if graph.get("current_nodes") != expected["expected_current_nodes"]:
        diagnostics.append("LOAD_CSV_COUNTS_MISMATCH")
    if graph.get("inactive_nodes") != expected["expected_inactive_nodes"]:
        diagnostics.append("LOAD_CSV_COUNTS_MISMATCH")
    return sorted(set(diagnostics))


def validate_safe_report(payload: Mapping[str, Any]) -> None:
    """Reject unsafe proof report payloads."""

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    hits = [fragment for fragment in FORBIDDEN_OUTPUT_FRAGMENTS if fragment in serialized]
    if hits:
        raise ValueError(f"unsafe payload fragments present: {hits}")


def execute_query_plan(graph: Any, plan: LoadCsvQueryPlan) -> dict[str, float]:  # noqa: ANN401 - graph is a falkordb-py-like runtime object.
    """Execute a prepared plan against a caller-owned FalkorDB graph object.

    This function is intentionally tiny and runtime-object injected. It does
    not create clients, containers, graphs, or capability claims.
    """

    durations: dict[str, float] = {}
    for step in plan.steps:
        started = _monotonic_ms()
        graph.query(step.cypher)
        durations[f"{step.name}_ms"] = _monotonic_ms() - started
    return durations


def _monotonic_ms() -> float:
    """Return current monotonic timestamp in milliseconds."""

    import time

    return time.monotonic() * 1000


def iter_query_text(plan: LoadCsvQueryPlan) -> Iterable[str]:
    """Yield query text for caller-owned execution surfaces."""

    for step in plan.steps:
        yield step.cypher
