#!/usr/bin/env python3
"""Verify a bounded FalkorDB LOAD CSV ingest proof for M021.

This command is a runtime smoke for CSV ingest mechanics only. It verifies that
tracked safe CSV fixtures can be loaded into a local FalkorDB graph with source
row counts matching graph node/relationship counts. It does not prove retrieval
quality, parser completeness, production FalkorDB readiness, graph-vector/HNSW
behavior, legal-answer correctness, or pilot readiness.
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from law_nexus.adapters.cli.runtime import repo_relative_path, write_json_report
from law_nexus.adapters.graph.falkordb_csv_loader import (
    FALKORDB_CSV_INGEST_NON_CLAIMS,
    FalkorCsvIngestRequest,
    build_base_report,
    build_load_csv_query_plan,
    compare_graph_counts,
    expected_counts_from_rows,
    validate_safe_report,
)
from law_nexus.adapters.graph.falkordb_csv_loader import (
    read_csv_rows as adapter_read_csv_rows,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest"
UNITS_CSV = FIXTURE_DIR / "legal_units.csv"
EDGES_CSV = FIXTURE_DIR / "legal_unit_edges.csv"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json"
SCHEMA_VERSION = "falkordb-csv-ingest-proof/v1"
MILESTONE_ID = "M021-qk4lze"
SLICE_ID = "S02"
DEFAULT_PORT = 6381
DEFAULT_CONTAINER_IMAGE = "falkordb/falkordb:edge"
CONTAINER_IMPORT_DIR = "/data"

RuntimeDisposition = Literal["load_csv_passed", "blocked", "failed_closed"]

FORBIDDEN_OUTPUT_FRAGMENTS = (
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

NON_CLAIMS = FALKORDB_CSV_INGEST_NON_CLAIMS


class FalkorResult(Protocol):
    result_set: list[list[Any]]


class FalkorGraph(Protocol):
    def query(self, query: str) -> FalkorResult | list[list[Any]]: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


def bounded_path(path: Path) -> str:
    return repo_relative_path(path, root=ROOT)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    return adapter_read_csv_rows(path)


def expected_counts() -> dict[str, int]:
    units = read_csv_rows(UNITS_CSV)
    edges = read_csv_rows(EDGES_CSV)
    return expected_counts_from_rows(units, edges)


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    validate_safe_report(payload)


def query_rows(graph: FalkorGraph, query: str) -> tuple[list[list[Any]], float]:
    started = time.monotonic()
    result = graph.query(query)
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    rows = getattr(result, "result_set", result)
    if not isinstance(rows, list):
        rows = list(cast(Iterable[Any], rows))
    return cast("list[list[Any]]", rows), duration_ms


def scalar_int(graph: FalkorGraph, query: str) -> int:
    rows, _duration = query_rows(graph, query)
    if len(rows) != 1 or len(rows[0]) != 1:
        raise RuntimeError("unexpected count result shape")
    return int(rows[0][0])


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
            graph = client.select_graph(f"csv_readiness_{uuid.uuid4().hex[:8]}")
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
    completed = subprocess.run(["docker", "image", "inspect", image], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed executable and args
    return completed.returncode == 0


def start_container(args: argparse.Namespace) -> tuple[str | None, dict[str, Any]]:
    diagnostic: dict[str, Any] = {
        "mode": args.container,
        "status": "not_started",
        "cleanup_status": "not_needed",
        "image_reference": args.container_image,
        "import_mount": "fixture_dir_to_container_import",
    }
    if args.container == "never":
        diagnostic["status"] = "skipped_by_flag"
        return None, diagnostic
    if not local_image_present(args.container_image):
        diagnostic["status"] = "blocked_image_absent"
        diagnostic["diagnostic_codes"] = ["CSV_FALKORDB_CONTAINER_IMAGE_ABSENT"]
        return None, diagnostic
    command = [
        "docker",
        "run",
        "--rm",
        "-d",
        "-p",
        f"127.0.0.1:{args.port}:6379",
        "-v",
        f"{FIXTURE_DIR.resolve()}:{CONTAINER_IMPORT_DIR}:ro",
        "-e",
        f"FALKORDB_ARGS=IMPORT_FOLDER {CONTAINER_IMPORT_DIR}",
        args.container_image,
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed executable and args
    if completed.returncode != 0:
        diagnostic["status"] = "blocked_start_failed"
        diagnostic["diagnostic_codes"] = ["CSV_FALKORDB_CONTAINER_START_BLOCKED"]
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
    completed = subprocess.run(["docker", "rm", "-f", container_id], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed executable and args
    diagnostic["cleanup_status"] = "deleted" if completed.returncode == 0 else "cleanup_failed"
    if completed.returncode != 0:
        diagnostic["diagnostic_codes"] = sorted(set(diagnostic.get("diagnostic_codes", []) + ["LOAD_CSV_CLEANUP_FAILED"]))


def load_csv_queries(graph: FalkorGraph) -> dict[str, float]:
    durations: dict[str, float] = {}
    for step in build_load_csv_query_plan().steps:
        _rows, durations[f"{step.name}_ms"] = query_rows(graph, step.cypher)
    return durations


def graph_counts(graph: FalkorGraph) -> dict[str, int]:
    return {
        "node_count": scalar_int(graph, "MATCH (n:LegalUnit) RETURN count(n)"),
        "relationship_count": scalar_int(graph, "MATCH (:LegalUnit)-[r:LINKS_TO]->(:LegalUnit) RETURN count(r)"),
        "current_nodes": scalar_int(graph, "MATCH (n:LegalUnit {temporal_status:'current'}) RETURN count(n)"),
        "inactive_nodes": scalar_int(graph, "MATCH (n:LegalUnit {temporal_status:'inactive'}) RETURN count(n)"),
    }


def base_report(args: argparse.Namespace, disposition: RuntimeDisposition, diagnostic_codes: Sequence[str]) -> dict[str, Any]:
    request = FalkorCsvIngestRequest.from_args(
        args,
        source_units_path=bounded_path(UNITS_CSV),
        source_edges_path=bounded_path(EDGES_CSV),
    )
    return build_base_report(
        request,
        expected_counts=expected_counts(),
        disposition=disposition,
        diagnostic_codes=diagnostic_codes,
    )


def compare_counts(report: dict[str, Any]) -> list[str]:
    return compare_graph_counts(report["expected_counts"], report["graph_counts"])


def run_proof(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    container_id: str | None = None
    container_diag: dict[str, Any] = {}
    report = base_report(args, "blocked", [])
    try:
        container_id, container_diag = start_container(args)
        report["container_runtime"] = container_diag
        if container_id is None:
            report["runtime_disposition"] = "blocked"
            report["diagnostic_codes"] = sorted(set(container_diag.get("diagnostic_codes", []) + ["CSV_FILE_ACCESS_BLOCKED"]))
            return 1, report
        client = wait_for_falkordb(args.host, args.port, args.readiness_timeout)
        graph_name = f"m021_csv_ingest_{uuid.uuid4().hex[:10]}"
        graph = client.select_graph(graph_name)
        report["graph_name_hash"] = f"len:{len(graph_name)}"
        report["load_durations_ms"] = load_csv_queries(graph)
        counts_after_first_and_rerun = graph_counts(graph)
        report["graph_counts"] = counts_after_first_and_rerun
        diagnostics = compare_counts(report)
        if diagnostics:
            report["runtime_disposition"] = "failed_closed"
            report["diagnostic_codes"] = diagnostics
            return 1, report
        report["idempotency"] = {
            "mode": "MERGE rerun",
            "status": "passed",
            "duplicate_nodes_created": 0,
            "duplicate_relationships_created": 0,
        }
        report["runtime_disposition"] = "load_csv_passed"
        report["diagnostic_codes"] = []
        return 0, report
    except TimeoutError:
        report["runtime_disposition"] = "blocked"
        report["container_runtime"] = container_diag or report["container_runtime"]
        report["diagnostic_codes"] = ["LOAD_CSV_RUNTIME_FAILED"]
        return 1, report
    except Exception as exc:  # noqa: BLE001 - fail closed with sanitized class only
        report["runtime_disposition"] = "failed_closed"
        report["container_runtime"] = container_diag or report["container_runtime"]
        code = "CSV_FILE_ACCESS_BLOCKED" if type(exc).__name__ in {"ResponseError", "DataError"} else "LOAD_CSV_RUNTIME_FAILED"
        report["diagnostic_codes"] = sorted({code, f"LOAD_CSV_{type(exc).__name__.upper()}"})
        return 1, report
    finally:
        cleanup_container(container_id, container_diag)
        if container_diag:
            report["container_runtime"] = container_diag


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    write_json_report(path, report, validator=assert_safe_payload)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--readiness-timeout", type=int, default=5)
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
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
