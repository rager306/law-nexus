#!/usr/bin/env python3
"""Verify a bounded FalkorDB bulk-loader smoke for M021.

This command evaluates the `falkordb-bulk-loader` scale-path mechanism on a tiny
safe fixture. It is a runtime smoke or precise blocked diagnostic only; it does
not prove production scale, retrieval quality, parser completeness, legal-answer
correctness, graph-vector/HNSW behavior, or pilot readiness.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest"
UNITS_CSV = FIXTURE_DIR / "legal_units.csv"
EDGES_CSV = FIXTURE_DIR / "legal_unit_edges.csv"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json"
SCHEMA_VERSION = "falkordb-bulk-loader-proof/v1"
MILESTONE_ID = "M021-qk4lze"
SLICE_ID = "S03"
DEFAULT_PORT = 6384
DEFAULT_CONTAINER_IMAGE = "falkordb/falkordb:edge"

RuntimeDisposition = Literal["bulk_loader_passed", "blocked", "failed_closed"]

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

NON_CLAIMS = (
    "Does not validate R037 broadly; this is a tiny bulk-loader smoke.",
    "Does not validate R035; R035 remains Active.",
    "Does not prove production FalkorDB readiness, retrieval quality, parser completeness, legal-answer correctness, graph-vector/HNSW behavior, or pilot readiness.",
    "Does not prove idempotent update/upsert semantics for GRAPH.BULK; this smoke uses a unique graph name.",
)


class FalkorResult(Protocol):
    result_set: list[list[Any]]


class FalkorGraph(Protocol):
    def query(self, query: str) -> FalkorResult | list[list[Any]]: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


def bounded_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return "<outside-project>"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_counts() -> dict[str, int]:
    units = read_csv_rows(UNITS_CSV)
    edges = read_csv_rows(EDGES_CSV)
    return {
        "expected_source_node_rows": len(units),
        "expected_source_relationship_rows": len(edges),
        "expected_node_count": len(units),
        "expected_relationship_count": len(edges),
        "expected_current_nodes": sum(1 for row in units if row.get("temporal_status") == "current"),
        "expected_inactive_nodes": sum(1 for row in units if row.get("temporal_status") == "inactive"),
    }


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise ValueError(f"unsafe proof output fragment detected: {fragment}")


def write_bulk_csvs(output_dir: Path) -> tuple[Path, Path]:
    units = read_csv_rows(UNITS_CSV)
    edges = read_csv_rows(EDGES_CSV)
    nodes_path = output_dir / "LegalUnit.csv"
    rels_path = output_dir / "LINKS_TO.csv"
    with nodes_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                ":ID(LegalUnit)",
                "kind:STRING",
                "source_record_id:STRING",
                "act_edition_id:STRING",
                "ontology_class:STRING",
                "temporal_status:STRING",
                "rank:INT",
            ],
        )
        writer.writeheader()
        for row in units:
            writer.writerow(
                {
                    ":ID(LegalUnit)": row["id"],
                    "kind:STRING": row["kind"],
                    "source_record_id:STRING": row["source_record_id"],
                    "act_edition_id:STRING": row["act_edition_id"],
                    "ontology_class:STRING": row["ontology_class"],
                    "temporal_status:STRING": row["temporal_status"],
                    "rank:INT": row["rank"],
                }
            )
    with rels_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                ":START_ID(LegalUnit)",
                ":END_ID(LegalUnit)",
                "edge_type:STRING",
                "evidence_span_id:STRING",
                "citation_key:STRING",
                "rank:INT",
            ],
        )
        writer.writeheader()
        for row in edges:
            writer.writerow(
                {
                    ":START_ID(LegalUnit)": row["source_id"],
                    ":END_ID(LegalUnit)": row["target_id"],
                    "edge_type:STRING": row["type"],
                    "evidence_span_id:STRING": row["evidence_span_id"],
                    "citation_key:STRING": row["citation_key"],
                    "rank:INT": row["rank"],
                }
            )
    return nodes_path, rels_path


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
        raise RuntimeError("unexpected count result shape")
    return int(rows[0][0])


def graph_counts(graph: FalkorGraph) -> dict[str, int]:
    return {
        "node_count": scalar_int(graph, "MATCH (n:LegalUnit) RETURN count(n)"),
        "relationship_count": scalar_int(graph, "MATCH (:LegalUnit)-[r:LINKS_TO]->(:LegalUnit) RETURN count(r)"),
        "current_nodes": scalar_int(graph, "MATCH (n:LegalUnit {temporal_status:'current'}) RETURN count(n)"),
        "inactive_nodes": scalar_int(graph, "MATCH (n:LegalUnit {temporal_status:'inactive'}) RETURN count(n)"),
    }


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
            graph = client.select_graph(f"bulk_readiness_{uuid.uuid4().hex[:8]}")
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
    diagnostic: dict[str, Any] = {
        "mode": args.container,
        "status": "not_started",
        "cleanup_status": "not_needed",
        "image_reference": args.container_image,
    }
    if args.container == "never":
        diagnostic["status"] = "skipped_by_flag"
        return None, diagnostic
    if not local_image_present(args.container_image):
        diagnostic["status"] = "blocked_image_absent"
        diagnostic["diagnostic_codes"] = ["BULK_LOADER_CONTAINER_IMAGE_ABSENT"]
        return None, diagnostic
    command = ["docker", "run", "--rm", "-d", "-p", f"127.0.0.1:{args.port}:6379", args.container_image]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603
    if completed.returncode != 0:
        diagnostic["status"] = "blocked_start_failed"
        diagnostic["diagnostic_codes"] = ["BULK_LOADER_CONTAINER_START_BLOCKED"]
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
        diagnostic["diagnostic_codes"] = sorted(set(diagnostic.get("diagnostic_codes", []) + ["BULK_LOADER_CLEANUP_FAILED"]))


def base_report(args: argparse.Namespace, disposition: RuntimeDisposition, diagnostic_codes: Sequence[str]) -> dict[str, Any]:
    counts = expected_counts()
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": MILESTONE_ID,
        "slice_id": SLICE_ID,
        "runtime_disposition": disposition,
        "loader": {
            "mechanism": "falkordb-bulk-loader",
            "command": "falkordb-bulk-insert",
            "invocation": "uvx --from falkordb-bulk-loader",
            "uses_graph_bulk": True,
            "create_new_graph_semantics": True,
            "idempotent_update_claimed": False,
            "enforce_schema": True,
            "id_type": "STRING",
        },
        "source_fixture_paths": [bounded_path(UNITS_CSV), bounded_path(EDGES_CSV)],
        "source_counts": {"node_rows": counts["expected_source_node_rows"], "relationship_rows": counts["expected_source_relationship_rows"]},
        "expected_counts": counts,
        "graph_counts": {},
        "container_runtime": {"mode": args.container, "status": "not_run", "cleanup_status": "not_needed", "image_reference": args.container_image},
        "diagnostic_codes": sorted(set(diagnostic_codes)),
        "redaction": {
            "source_text_excluded": True,
            "raw_vectors_excluded": True,
            "secrets_excluded": True,
            "external_payloads_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
            "temporary_csv_paths_excluded": True,
        },
        "non_authoritative": True,
        "requirement": "R037",
        "related_requirement": "R035",
        "non_claims": list(NON_CLAIMS),
    }


def compare_counts(report: dict[str, Any]) -> list[str]:
    expected = report["expected_counts"]
    graph = report["graph_counts"]
    diagnostics: list[str] = []
    if graph.get("node_count") != expected["expected_node_count"]:
        diagnostics.append("BULK_LOADER_COUNTS_MISMATCH")
    if graph.get("relationship_count") != expected["expected_relationship_count"]:
        diagnostics.append("BULK_LOADER_COUNTS_MISMATCH")
    if graph.get("current_nodes") != expected["expected_current_nodes"]:
        diagnostics.append("BULK_LOADER_COUNTS_MISMATCH")
    if graph.get("inactive_nodes") != expected["expected_inactive_nodes"]:
        diagnostics.append("BULK_LOADER_COUNTS_MISMATCH")
    return sorted(set(diagnostics))


def run_bulk_loader(args: argparse.Namespace, graph_name: str, nodes_path: Path, rels_path: Path) -> tuple[int, float, str]:
    command = [
        "uvx",
        "--from",
        "falkordb-bulk-loader",
        "falkordb-bulk-insert",
        "--server-url",
        f"redis://{args.host}:{args.port}",
        "--enforce-schema",
        "--id-type",
        "STRING",
        "--nodes-with-label",
        "LegalUnit",
        str(nodes_path),
        "--relations-with-type",
        "LINKS_TO",
        str(rels_path),
        graph_name,
    ]
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed uvx executable and args
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    output_class = "ok" if completed.returncode == 0 else completed.stderr[:200].splitlines()[0] if completed.stderr else "failed"
    return completed.returncode, duration_ms, output_class


def run_proof(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    report = base_report(args, "blocked", [])
    if shutil.which("uvx") is None:
        report["diagnostic_codes"] = ["BULK_LOADER_UNAVAILABLE"]
        return 1, report
    container_id: str | None = None
    container_diag: dict[str, Any] = {}
    try:
        container_id, container_diag = start_container(args)
        report["container_runtime"] = container_diag
        if container_id is None:
            report["diagnostic_codes"] = sorted(set(container_diag.get("diagnostic_codes", []) + ["BULK_LOADER_RUNTIME_FAILED"]))
            return 1, report
        client = wait_for_falkordb(args.host, args.port, args.readiness_timeout)
        graph_name = f"m021_bulk_ingest_{uuid.uuid4().hex[:10]}"
        report["graph_name_hash"] = f"len:{len(graph_name)}"
        with tempfile.TemporaryDirectory(prefix="m021-bulk-loader-") as tmpdir:
            nodes_path, rels_path = write_bulk_csvs(Path(tmpdir))
            loader_exit, loader_duration, output_class = run_bulk_loader(args, graph_name, nodes_path, rels_path)
        report["loader_duration_ms"] = loader_duration
        report["loader_output_class"] = output_class
        if loader_exit != 0:
            report["runtime_disposition"] = "failed_closed"
            report["diagnostic_codes"] = ["BULK_LOADER_RUNTIME_FAILED"]
            return 1, report
        graph = client.select_graph(graph_name)
        report["graph_counts"] = graph_counts(graph)
        diagnostics = compare_counts(report)
        if diagnostics:
            report["runtime_disposition"] = "failed_closed"
            report["diagnostic_codes"] = diagnostics
            return 1, report
        report["runtime_disposition"] = "bulk_loader_passed"
        report["diagnostic_codes"] = []
        return 0, report
    except TimeoutError:
        report["runtime_disposition"] = "blocked"
        report["container_runtime"] = container_diag or report["container_runtime"]
        report["diagnostic_codes"] = ["BULK_LOADER_RUNTIME_FAILED"]
        return 1, report
    except Exception as exc:  # noqa: BLE001 - fail closed with sanitized exception class
        report["runtime_disposition"] = "failed_closed"
        report["container_runtime"] = container_diag or report["container_runtime"]
        code = "BULK_LOADER_SCHEMA_UNSUPPORTED" if type(exc).__name__ in {"KeyError", "ValueError"} else "BULK_LOADER_RUNTIME_FAILED"
        report["diagnostic_codes"] = sorted({code, f"BULK_LOADER_{type(exc).__name__.upper()}"})
        return 1, report
    finally:
        cleanup_container(container_id, container_diag)
        if container_diag:
            report["container_runtime"] = container_diag


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_payload(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
