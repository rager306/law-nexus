#!/usr/bin/env python3
"""Run the M001/S10 GigaEmbeddings safety gate and optional 2048-dim vector proof.

This runner intentionally fails closed. GigaEmbeddings uses custom Hugging Face
model code and a 3B-class decoder embedding runtime, so encode is only attempted
when the operator explicitly allows custom code/trust_remote_code and the local
package/cache/hardware gate is safe. Otherwise the proof artifact records a
terminal not-safe/blocked verdict rather than overclaiming runtime success.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/milestones/M001/slices/S10"
DEFAULT_RUNTIME_ARTIFACT = DEFAULT_OUTPUT_DIR / "S10-EMBEDDING-RUNTIME-PROOF.json"
DEFAULT_GIGA_ARTIFACT = DEFAULT_OUTPUT_DIR / "S10-GIGAEMBEDDINGS-PROOF.json"
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"
USER_MODEL_ID = "deepvk/USER-bge-m3"
RUNTIME_SCHEMA_VERSION = "s10-embedding-runtime-proof/v1"
GIGA_SCHEMA_VERSION = "s10-gigaembeddings-proof/v1"
FALKORDB_IMAGE = "falkordb/falkordb:edge"
QUERY_TASK_DESCRIPTION = "Given a question, retrieve passages that answer the question."
FORBIDDEN_TERMS = ("GIGACHAT" + "_AUTH_DATA", "Bearer ", "sk-", "api_key")
GIGA_REQUIREMENTS = ("transformers==4.51.0", "sentence-transformers>=5.1.1", "torch", "flash-attn")
MIN_MEMORY_AVAILABLE_MIB = 24_000
MIN_DISK_FREE_MIB = 20_000


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    fixture_class: str
    text: str
    relevant_document_id: str | None = None


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int | None
    timed_out: bool
    duration_ms: float
    stdout: str
    stderr: str
    log_path: str


class Encoder(Protocol):
    def encode(self, texts: Sequence[str], **kwargs: Any) -> Any: ...


class FalkorGraph(Protocol):
    def query(self, query: str) -> Any: ...

    def create_node_vector_index(self, label: str, attr: str, **kwargs: Any) -> Any: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    gsd_root = (ROOT / ".gsd").resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        pass
    try:
        return f".gsd/{resolved.relative_to(gsd_root).as_posix()}"
    except ValueError:
        return resolved.as_posix()


def sanitize_text(text: str) -> str:
    sanitized = text
    for term in FORBIDDEN_TERMS:
        sanitized = sanitized.replace(term, "[REDACTED]")
    return sanitized


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term: {term}")


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    assert_safe_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized_path(path)


def write_log(log_dir: Path, name: str, payload: Mapping[str, Any]) -> str:
    safe_name = name.replace("/", "__")
    return write_json(log_dir / f"{safe_name}.log", payload)


def run_command(command: Sequence[str], timeout_seconds: int, log_dir: Path, phase: str) -> CommandResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = completed.returncode
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    log_path = write_log(
        log_dir,
        phase,
        {
            "phase": phase,
            "timestamp": utc_now(),
            "command": list(command),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": duration_ms,
            "stdout_tail": sanitize_text(stdout[-4000:]),
            "stderr_tail": sanitize_text(stderr[-4000:]),
        },
    )
    return CommandResult(list(command), exit_code, timed_out, duration_ms, stdout, stderr, log_path)


def command_root_cause(result: CommandResult, label: str) -> str:
    if result.timed_out:
        return f"{label}-timeout"
    if result.exit_code is None:
        return f"{label}-no-exit-code"
    if result.exit_code != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        suffix = detail[-1][:160] if detail else f"exit-{result.exit_code}"
        return f"{label}-failed:{suffix}"
    return ""


def requirement_package_name(requirement: str) -> str:
    for separator in ("<", ">", "=", "!", "~", ";", "["):
        if separator in requirement:
            return requirement.split(separator, maxsplit=1)[0].strip()
    return requirement.strip()


def probe_package(requirement: str) -> dict[str, Any]:
    package = requirement_package_name(requirement)
    import_name = {"sentence-transformers": "sentence_transformers", "flash-attn": "flash_attn"}.get(package, package.replace("-", "_"))
    available = importlib.util.find_spec(import_name) is not None
    version: str | None = None
    if available:
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return {
        "package": requirement,
        "distribution": package,
        "import_name": import_name,
        "status": "available" if available else "absent",
        "version": version,
    }


def package_status(requirements: Sequence[str]) -> dict[str, Any]:
    probes = [probe_package(requirement) for requirement in requirements]
    missing = [probe["package"] for probe in probes if probe["status"] != "available"]
    return {"status": "available" if not missing else "blocked-environment", "missing": missing, "packages": probes}


def model_cache_name(model_id: str) -> str:
    return "models--" + model_id.replace("/", "--")


def unique_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if expanded in seen:
            continue
        seen.add(expanded)
        result.append(expanded)
    return tuple(result)


def huggingface_cache_roots(env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    active_env = env or os.environ
    paths: list[Path] = []
    if hub_cache := active_env.get("HUGGINGFACE_HUB_CACHE"):
        paths.append(Path(hub_cache))
    if hf_home := active_env.get("HF_HOME"):
        paths.append(Path(hf_home) / "hub")
    if transformers_cache := active_env.get("TRANSFORMERS_CACHE"):
        paths.append(Path(transformers_cache))
    paths.append(Path.home() / ".cache/huggingface/hub")
    return unique_paths(paths)


def probe_model_cache(model_id: str, cache_roots: Sequence[Path]) -> dict[str, Any]:
    checked_paths: list[str] = []
    snapshots: list[str] = []
    for root in cache_roots:
        model_dir = root / model_cache_name(model_id)
        checked_paths.append(normalized_path(model_dir))
        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.is_dir():
            snapshots.extend(sorted(path.name for path in snapshots_dir.iterdir() if path.is_dir()))
    return {
        "model_id": model_id,
        "status": "available" if snapshots else "absent",
        "present": bool(snapshots),
        "checked_paths": checked_paths,
        "snapshot_count": len(set(snapshots)),
        "snapshots": sorted(set(snapshots)),
    }


def memory_metadata() -> dict[str, Any]:
    values: dict[str, float] = {}
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            key = parts[0].rstrip(":") if parts else ""
            if len(parts) >= 2 and key in {"MemTotal", "MemAvailable", "SwapTotal"}:
                values[key] = round(int(parts[1]) / 1024, 1)
    return {
        "memory_mib": values.get("MemTotal"),
        "memory_available_mib": values.get("MemAvailable"),
        "swap_total_mib": values.get("SwapTotal"),
        "no_swap": values.get("SwapTotal") == 0 if "SwapTotal" in values else None,
    }


def disk_metadata(output_dir: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output_dir if output_dir.exists() else output_dir.parent)
    return {
        "total_mib": round(usage.total / 1024 / 1024, 1),
        "free_mib": round(usage.free / 1024 / 1024, 1),
        "used_mib": round(usage.used / 1024 / 1024, 1),
    }


def resource_metadata(output_dir: Path | None = None) -> dict[str, Any]:
    docker = shutil.which("docker")
    nvidia_smi = shutil.which("nvidia-smi")
    metadata: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "gpu_probe": {"nvidia_smi": nvidia_smi, "status": "available" if nvidia_smi else "absent"},
        "docker_probe": {"docker": docker, "status": "available" if docker else "absent"},
        **memory_metadata(),
    }
    if output_dir is not None:
        metadata["disk_mib"] = disk_metadata(output_dir)
    return metadata


def format_giga_query(query: str, task_description: str = QUERY_TASK_DESCRIPTION) -> str:
    return f"Instruct: {task_description}\nQuery: {query}"


def synthetic_documents() -> tuple[Fixture, ...]:
    return (
        Fixture("doc-procurement-notice-term", "synthetic-russian-legal-style", "Синтетическая норма: заказчик размещает извещение о закупке и документацию в единой информационной системе в установленный срок."),
        Fixture("doc-contract-performance-penalty", "synthetic-russian-legal-style", "Синтетическая норма: поставщик исполняет контракт в срок; при просрочке начисляется неустойка, кроме случаев непреодолимой силы."),
        Fixture("doc-court-appeal-deadline", "synthetic-russian-legal-style", "Синтетическая норма: апелляционная жалоба подается через суд первой инстанции до истечения процессуального срока."),
        Fixture("s05-span-raw-content-order-oracle", "s05-derived-safe-evidence-span", "S05 safe evidence span: raw content XML traversal is the ordering oracle for parser comparison evidence."),
        Fixture("s05-span-odfdo-direction", "s05-derived-safe-evidence-span", "S05 safe evidence span: odfdo loaded the unmodified ODT in smoke evidence and remains a parser direction to investigate."),
        Fixture("s05-span-odfpy-manifest-boundary", "s05-derived-safe-evidence-span", "S05 safe evidence span: odfpy unmodified load is blocked by a manifest external reference boundary."),
    )


def synthetic_queries() -> tuple[Fixture, ...]:
    return (
        Fixture("query-procurement-notice-term", "synthetic-russian-legal-style-query", "Когда заказчик размещает извещение о закупке?", "doc-procurement-notice-term"),
        Fixture("query-contract-performance-penalty", "synthetic-russian-legal-style-query", "Что происходит при просрочке исполнения контракта поставщиком?", "doc-contract-performance-penalty"),
        Fixture("query-court-appeal-deadline", "synthetic-russian-legal-style-query", "Куда подается апелляционная жалоба и как учитывается срок?", "doc-court-appeal-deadline"),
        Fixture("query-s05-parser-oracle", "s05-derived-safe-evidence-query", "Какой S05 сигнал используется как ordering oracle для сравнения парсеров?", "s05-span-raw-content-order-oracle"),
        Fixture("query-s05-odfdo-direction", "s05-derived-safe-evidence-query", "Какой S05 optional parser остается направлением для исследования?", "s05-span-odfdo-direction"),
        Fixture("query-s05-odfpy-boundary", "s05-derived-safe-evidence-query", "Какой S05 boundary блокирует unmodified odfpy load?", "s05-span-odfpy-manifest-boundary"),
    )


def vector_to_list(row: Any) -> list[float]:
    if hasattr(row, "tolist"):
        row = row.tolist()
    if not isinstance(row, list | tuple):
        raise TypeError("encoded vector row must be list-like")
    return [float(value) for value in row]


def matrix_to_lists(matrix: Any) -> list[list[float]]:
    if hasattr(matrix, "tolist"):
        matrix = matrix.tolist()
    if not isinstance(matrix, list | tuple):
        raise TypeError("encoded vectors must be list-like")
    return [vector_to_list(row) for row in matrix]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieval_metrics(query_fixtures: Sequence[Fixture], document_fixtures: Sequence[Fixture], query_vectors: Sequence[Sequence[float]], document_vectors: Sequence[Sequence[float]]) -> dict[str, Any]:
    doc_ids = [fixture.fixture_id for fixture in document_fixtures]
    ranks: list[int] = []
    top1_matches = 0
    for query, query_vector in zip(query_fixtures, query_vectors, strict=True):
        scored = sorted(
            ((doc_ids[index], cosine_similarity(query_vector, document_vector)) for index, document_vector in enumerate(document_vectors)),
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_ids = [fixture_id for fixture_id, _score in scored]
        expected = query.relevant_document_id
        if expected is None:
            raise ValueError(f"query fixture {query.fixture_id} missing relevant_document_id")
        rank = ranked_ids.index(expected) + 1 if expected in ranked_ids else len(ranked_ids) + 1
        ranks.append(rank)
        if rank == 1:
            top1_matches += 1
    return {"query_count": len(query_fixtures), "document_count": len(document_fixtures), "recall_at_1": round(top1_matches / len(query_fixtures), 4), "mrr": round(sum(1 / rank for rank in ranks) / len(ranks), 4), "ranks": ranks, "fixture_ids_only": True}


def load_sentence_transformer(model_id: str, local_files_only: bool, trust_remote_code: bool) -> Encoder:
    module = importlib.import_module("sentence_transformers")
    sentence_transformer = getattr(module, "SentenceTransformer")
    try:
        return cast("Encoder", sentence_transformer(model_id, local_files_only=local_files_only, trust_remote_code=trust_remote_code))
    except TypeError:
        return cast("Encoder", sentence_transformer(model_id))


def encode_giga_fixtures(model_id: str, local_files_only: bool, log_dir: Path, encoder_factory: Callable[[str, bool, bool], Encoder] | None = None) -> dict[str, Any]:
    documents = synthetic_documents()
    queries = synthetic_queries()
    active_encoder_factory = encoder_factory or load_sentence_transformer
    started = time.monotonic()
    try:
        encoder = active_encoder_factory(model_id, local_files_only, True)
        document_inputs = [fixture.text for fixture in documents]
        query_inputs = [format_giga_query(fixture.text) for fixture in queries]
        document_vectors = matrix_to_lists(encoder.encode(document_inputs, normalize_embeddings=True, batch_size=1))
        query_vectors = matrix_to_lists(encoder.encode(query_inputs, normalize_embeddings=True, batch_size=1))
    except Exception as exc:  # noqa: BLE001 - proof artifact must preserve exact terminal root cause.
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        log_path = write_log(
            log_dir,
            "gigaembeddings-encode-failed",
            {
                "phase": "gigaembeddings-encode",
                "status": "failed-runtime",
                "duration_ms": duration_ms,
                "exception_type": type(exc).__name__,
                "exception_message": sanitize_text(str(exc))[:1000],
                "fixture_ids": [fixture.fixture_id for fixture in (*documents, *queries)],
                "query_instruction_format": "Instruct: {task_description}\\nQuery: {query}",
                "document_instruction_applied": False,
                "raw_text_logged": False,
                "raw_vectors_logged": False,
            },
        )
        return {"status": "failed-runtime", "duration_ms": duration_ms, "blocked_root_cause": f"encode-runtime-failed:{type(exc).__name__}:{sanitize_text(str(exc))[:160]}", "observed_vector_dimension": None, "retrieval_metrics": None, "raw_log_paths": [log_path], "document_vectors": [], "query_vectors": [], "document_ids": [fixture.fixture_id for fixture in documents], "query_ids": [fixture.fixture_id for fixture in queries]}
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    dimensions = {len(vector) for vector in (*document_vectors, *query_vectors)}
    observed_dimension = dimensions.pop() if len(dimensions) == 1 else None
    metrics = retrieval_metrics(queries, documents, query_vectors, document_vectors)
    status = "confirmed-runtime" if observed_dimension == 2048 else "failed-runtime"
    log_path = write_log(
        log_dir,
        "gigaembeddings-encode",
        {
            "phase": "gigaembeddings-encode",
            "status": status,
            "model_id": model_id,
            "duration_ms": duration_ms,
            "observed_vector_dimension": observed_dimension,
            "expected_vector_dimension": 2048,
            "batch_size": 1,
            "document_count": len(documents),
            "query_count": len(queries),
            "fixture_ids": [fixture.fixture_id for fixture in (*documents, *queries)],
            "fixture_classes": sorted({fixture.fixture_class for fixture in (*documents, *queries)}),
            "retrieval_metrics": metrics,
            "resource_metadata": resource_metadata(log_dir.parent),
            "query_instruction_format": "Instruct: {task_description}\\nQuery: {query}",
            "document_instruction_applied": False,
            "raw_text_logged": False,
            "raw_vectors_logged": False,
        },
    )
    return {"status": status, "duration_ms": duration_ms, "blocked_root_cause": None if status == "confirmed-runtime" else f"observed-dimension-{observed_dimension}-expected-2048", "observed_vector_dimension": observed_dimension, "retrieval_metrics": metrics, "raw_log_paths": [log_path], "document_vectors": document_vectors, "query_vectors": query_vectors, "document_ids": [fixture.fixture_id for fixture in documents], "query_ids": [fixture.fixture_id for fixture in queries]}


def vecf32_literal(vector: Sequence[float]) -> str:
    values = ", ".join(f"{value:.8f}" for value in vector)
    return f"vecf32([{values}])"


def cypher_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def query_result_rows(result: Any) -> list[Any]:
    rows = getattr(result, "result_set", result)
    if isinstance(rows, list):
        return rows
    return list(rows) if rows is not None else []


def run_vector_query_with_client(client: FalkorClient, graph_name: str, document_ids: Sequence[str], document_vectors: Sequence[Sequence[float]], query_vector: Sequence[float], log_dir: Path) -> dict[str, Any]:
    started = time.monotonic()
    try:
        graph = client.select_graph(graph_name)
        graph.create_node_vector_index("Embedding", "vec", dim=2048, similarity_function="cosine")
        for fixture_id, vector in zip(document_ids, document_vectors, strict=True):
            graph.query("CREATE (:Embedding {fixture_id: " + cypher_string(fixture_id) + ", vec: " + vecf32_literal(vector) + "})")
        rows = query_result_rows(graph.query("CALL db.idx.vector.queryNodes('Embedding', 'vec', 3, " + vecf32_literal(query_vector) + ") YIELD node, score RETURN node.fixture_id, score"))
        graph.query("MATCH (n:Embedding) DELETE n")
    except Exception as exc:  # noqa: BLE001 - proof runner records terminal runtime root cause.
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        log_path = write_log(log_dir, "falkordb-2048-vector-failed", {"phase": "falkordb-2048-vector-query", "status": "failed-runtime", "duration_ms": duration_ms, "exception_type": type(exc).__name__, "exception_message": sanitize_text(str(exc))[:1000], "document_ids": list(document_ids), "query_vector_dimension": len(query_vector), "raw_vectors_logged": False})
        return {"status": "failed-runtime", "index_created": False, "query_executed": False, "duration_ms": duration_ms, "blocked_root_cause": f"falkordb-vector-query-failed:{type(exc).__name__}:{sanitize_text(str(exc))[:160]}", "raw_log_paths": [log_path]}
    duration_ms = round((time.monotonic() - started) * 1000, 2)
    returned_ids = [str(row[0]) for row in rows if isinstance(row, list | tuple) and row]
    status = "confirmed-runtime" if returned_ids else "failed-runtime"
    log_path = write_log(log_dir, "falkordb-2048-vector", {"phase": "falkordb-2048-vector-query", "status": status, "duration_ms": duration_ms, "index_created": True, "query_executed": bool(returned_ids), "dimension": 2048, "document_ids": list(document_ids), "returned_ids": returned_ids, "row_count": len(rows), "raw_vectors_logged": False})
    return {"status": status, "index_created": True, "query_executed": bool(returned_ids), "duration_ms": duration_ms, "blocked_root_cause": None if status == "confirmed-runtime" else "falkordb-vector-query-returned-no-rows", "raw_log_paths": [log_path]}


def allocate_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(host: str, port: int, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def instantiate_falkordb_client(host: str, port: int) -> FalkorClient:
    module = importlib.import_module("falkordb")
    client_class = getattr(module, "FalkorDB")
    return cast("FalkorClient", client_class(host=host, port=port))


def instantiate_falkordb_client_with_retry(host: str, port: int, timeout_seconds: int, client_factory: Callable[[str, int], FalkorClient]) -> FalkorClient:
    deadline = time.monotonic() + timeout_seconds
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return client_factory(host, port)
        except Exception as exc:  # noqa: BLE001 - readiness handshake is runtime-dependent.
            last_exc = exc
            time.sleep(1)
    if last_exc is not None:
        raise last_exc
    raise TimeoutError("FalkorDB client readiness timeout")


def run_falkordb_vector_proof(document_ids: Sequence[str], document_vectors: Sequence[Sequence[float]], query_vector: Sequence[float], log_dir: Path, timeout_seconds: int, client_factory: Callable[[str, int], FalkorClient] = instantiate_falkordb_client) -> dict[str, Any]:
    if not document_vectors or not query_vector:
        log_path = write_log(log_dir, "falkordb-2048-vector-skipped", {"phase": "falkordb-2048-vector-query", "status": "blocked-environment", "blocked_root_cause": "encode-proof-unavailable", "raw_vectors_logged": False})
        return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": "encode-proof-unavailable", "raw_log_paths": [log_path]}
    if importlib.util.find_spec("falkordb") is None:
        log_path = write_log(log_dir, "falkordb-client-missing-2048", {"phase": "falkordb-2048-vector-query", "status": "blocked-environment", "blocked_root_cause": "python-package-missing:falkordb", "raw_vectors_logged": False})
        return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": "python-package-missing:falkordb", "raw_log_paths": [log_path]}
    if shutil.which("docker") is None:
        log_path = write_log(log_dir, "docker-missing-2048", {"phase": "falkordb-2048-vector-query", "status": "blocked-environment", "blocked_root_cause": "docker-command-missing", "raw_vectors_logged": False})
        return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": "docker-command-missing", "raw_log_paths": [log_path]}

    command_logs: list[str] = []
    docker = run_command(["docker", "version", "--format", "{{json .}}"], 30, log_dir, "falkordb-docker-daemon-2048")
    command_logs.append(docker.log_path)
    root_cause = command_root_cause(docker, "docker-daemon")
    if root_cause:
        return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": root_cause, "raw_log_paths": command_logs}

    inspect = run_command(["docker", "image", "inspect", FALKORDB_IMAGE, "--format", "{{json .}}"], 30, log_dir, "falkordb-image-inspect-2048")
    command_logs.append(inspect.log_path)
    if inspect.exit_code != 0:
        pull = run_command(["docker", "pull", FALKORDB_IMAGE], min(timeout_seconds, 300), log_dir, "falkordb-image-pull-2048")
        command_logs.append(pull.log_path)
        root_cause = command_root_cause(pull, "docker-image-pull")
        if root_cause:
            return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": root_cause, "raw_log_paths": command_logs}

    port = allocate_free_port()
    container_name = f"s10-giga-vector-{uuid.uuid4().hex[:12]}"
    run = run_command(["docker", "run", "--rm", "--name", container_name, "-p", f"127.0.0.1:{port}:6379", "-d", FALKORDB_IMAGE], 60, log_dir, "falkordb-container-start-2048")
    command_logs.append(run.log_path)
    root_cause = command_root_cause(run, "docker-container-start")
    if root_cause:
        return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": root_cause, "raw_log_paths": command_logs}

    try:
        if not wait_for_port("127.0.0.1", port, min(timeout_seconds, 60)):
            return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": "falkordb-port-readiness-timeout", "raw_log_paths": command_logs}
        try:
            client = instantiate_falkordb_client_with_retry("127.0.0.1", port, min(timeout_seconds, 60), client_factory)
        except Exception as exc:  # noqa: BLE001 - record terminal client handshake failure.
            log_path = write_log(log_dir, "falkordb-client-handshake-failed-2048", {"phase": "falkordb-client-handshake", "status": "blocked-environment", "exception_type": type(exc).__name__, "exception_message": sanitize_text(str(exc))[:1000], "raw_vectors_logged": False})
            return {"status": "blocked-environment", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": f"falkordb-client-handshake-failed:{type(exc).__name__}:{sanitize_text(str(exc))[:160]}", "raw_log_paths": [*command_logs, log_path]}
        result = run_vector_query_with_client(client, f"s10_giga_{uuid.uuid4().hex[:8]}", document_ids, document_vectors, query_vector, log_dir)
        result["raw_log_paths"] = [*command_logs, *cast("list[str]", result["raw_log_paths"])]
        return result
    finally:
        run_command(["docker", "rm", "-f", container_name], 30, log_dir, "falkordb-container-cleanup-2048")


def load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if isinstance(parsed, dict):
        return cast("dict[str, Any]", parsed)
    return {}


def safety_gate_reasons(args: argparse.Namespace, pkg: Mapping[str, Any], cache: Mapping[str, Any], resources: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not args.allow_custom_code:
        reasons.append("custom-code-not-explicitly-allowed")
    if not args.allow_trust_remote_code:
        reasons.append("trust-remote-code-not-explicitly-allowed")
    if pkg.get("status") != "available":
        missing = ",".join(cast("list[str]", pkg.get("missing", [])))
        reasons.append(f"embedding-packages-missing:{missing}" if missing else "embedding-packages-missing")
    if cache.get("status") != "available" and not args.cache_or_explicit_download:
        reasons.append("model-cache-absent-and-download-not-allowed")
    raw_gpu_probe = resources.get("gpu_probe")
    gpu_probe = raw_gpu_probe if isinstance(raw_gpu_probe, dict) else {}
    if gpu_probe.get("status") != "available" and not args.allow_cpu_fallback:
        reasons.append("cuda-or-explicit-cpu-fallback-required")
    if resources.get("no_swap") is True and not args.allow_no_swap:
        reasons.append("no-swap-not-explicitly-allowed")
    memory_available = resources.get("memory_available_mib")
    if isinstance(memory_available, int | float) and memory_available < MIN_MEMORY_AVAILABLE_MIB:
        reasons.append(f"memory-available-below-{MIN_MEMORY_AVAILABLE_MIB}mib")
    disk = resources.get("disk_mib")
    free = disk.get("free_mib") if isinstance(disk, dict) else None
    if isinstance(free, int | float) and free < MIN_DISK_FREE_MIB:
        reasons.append(f"disk-free-below-{MIN_DISK_FREE_MIB}mib")
    return reasons


def blocked_giga_encode(reason_status: str, reasons: Sequence[str], pkg: Mapping[str, Any], cache: Mapping[str, Any], resources: Mapping[str, Any], log_dir: Path) -> dict[str, Any]:
    log_path = write_log(
        log_dir,
        "gigaembeddings-safety-gate",
        {
            "phase": "gigaembeddings-safety-gate",
            "status": reason_status,
            "reasons": list(reasons),
            "package_status": pkg,
            "cache_status": cache,
            "resource_metadata": resources,
            "custom_code_required": True,
            "trust_remote_code_required": True,
            "query_instruction_format": "Instruct: {task_description}\\nQuery: {query}",
            "document_instruction_applied": False,
            "raw_text_logged": False,
            "raw_vectors_logged": False,
        },
    )
    return {"status": reason_status, "duration_ms": None, "blocked_root_cause": ";".join(reasons), "observed_vector_dimension": None, "retrieval_metrics": None, "raw_log_paths": [log_path], "document_vectors": [], "query_vectors": [], "document_ids": [], "query_ids": []}


def giga_model_entry(encode_result: Mapping[str, Any], pkg: Mapping[str, Any], cache: Mapping[str, Any], resources: Mapping[str, Any], args: argparse.Namespace, gate_status: str, gate_reasons: Sequence[str]) -> dict[str, Any]:
    confirmed = encode_result.get("status") == "confirmed-runtime"
    status = "confirmed-runtime" if confirmed else str(encode_result.get("status") or gate_status)
    return {
        "id": GIGA_MODEL_ID,
        "role": "quality-challenger",
        "status": status,
        "verdict": "proven-challenger" if confirmed else ("not-safe-challenger" if status == "not-safe-to-run" else "deferred"),
        "vector_dimension": 2048,
        "max_token_limit": 4096,
        "package_status": pkg.get("status"),
        "cache_status": cache.get("status"),
        "download_status": "explicit-open-weight-allowed" if args.cache_or_explicit_download else "cache-only",
        "runtime_status": status,
        "encode_duration_ms": encode_result.get("duration_ms") if confirmed else None,
        "observed_vector_dimension": encode_result.get("observed_vector_dimension") if confirmed else None,
        "resource_metadata": resources,
        "retrieval_metrics": encode_result.get("retrieval_metrics") if confirmed else None,
        "blocked_root_cause": None if confirmed else encode_result.get("blocked_root_cause"),
        "next_proof_step": "Use GigaEmbeddings 2048-dimensional runtime proof as challenger evidence." if confirmed else "Resolve the GigaEmbeddings safety gate reasons, then rerun T04 with explicit custom-code/trust_remote_code approval.",
        "raw_log_paths": encode_result.get("raw_log_paths", []),
        "instruction_handling": {
            "query_instruction_applied": True,
            "query_instruction_format": "Instruct: {task_description}\\nQuery: {query}",
            "document_instruction_applied": False,
        },
        "safety_gate": {"status": "safe-to-run" if confirmed else gate_status, "reasons": list(gate_reasons)},
        "package_details": pkg,
        "cache_details": cache,
    }


def blocked_user_from_existing(existing: Mapping[str, Any], log_dir: Path) -> dict[str, Any]:
    for model in existing.get("models", []):
        if isinstance(model, dict) and model.get("id") == USER_MODEL_ID:
            return dict(model)
    log_path = write_log(log_dir, "user-not-proven-before-giga", {"phase": "user-carry-forward", "status": "not-attempted-by-policy"})
    return {"id": USER_MODEL_ID, "role": "practical-baseline", "status": "not-attempted-by-policy", "verdict": "deferred", "vector_dimension": 1024, "max_token_limit": 8192, "package_status": "blocked-environment", "cache_status": "absent", "download_status": "disabled", "runtime_status": "not-attempted-by-policy", "encode_duration_ms": None, "observed_vector_dimension": None, "resource_metadata": resource_metadata(log_dir.parent), "retrieval_metrics": None, "blocked_root_cause": "user-proof-not-found", "next_proof_step": "Run T03 USER-bge-m3 proof before final S10 verdict.", "raw_log_paths": [log_path], "instruction_handling": {"query_instruction_applied": False, "document_instruction_applied": False}, "safety_gate": {"status": "not-attempted-by-policy", "reasons": ["T04 is GigaEmbeddings only"]}}


def vector_1024_from_existing(existing: Mapping[str, Any], log_dir: Path) -> dict[str, Any]:
    for proof in existing.get("vector_proofs", []):
        if isinstance(proof, dict) and proof.get("dimension") == 1024:
            return dict(proof)
    log_path = write_log(log_dir, "vector-1024-not-proven-before-giga", {"phase": "vector-1024-carry-forward", "status": "not-attempted-by-policy"})
    return {"dimension": 1024, "model_id": USER_MODEL_ID, "status": "not-attempted-by-policy", "index_created": False, "query_executed": False, "duration_ms": None, "blocked_root_cause": "user-vector-proof-not-found", "next_proof_step": "Run T03 USER-bge-m3 vector proof before final S10 verdict.", "raw_log_paths": [log_path]}


def vector_2048_entry(vector_result: Mapping[str, Any]) -> dict[str, Any]:
    return {"dimension": 2048, "model_id": GIGA_MODEL_ID, "status": vector_result["status"], "index_created": vector_result["index_created"], "query_executed": vector_result["query_executed"], "duration_ms": vector_result["duration_ms"], "blocked_root_cause": vector_result["blocked_root_cause"], "next_proof_step": "Use 2048-dim FalkorDB vector query as challenger proof." if vector_result["status"] == "confirmed-runtime" else "Resolve GigaEmbeddings encode/vector runtime blocker and rerun T04.", "raw_log_paths": vector_result["raw_log_paths"]}


def build_runtime_payload(existing: Mapping[str, Any], giga_model: Mapping[str, Any], vector_2048: Mapping[str, Any], pkg: Mapping[str, Any], cache: Mapping[str, Any], resources: Mapping[str, Any], log_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    summary_log = write_log(log_dir, "s10-gigaembeddings-proof-summary", {"phase": "summary", "model_id": GIGA_MODEL_ID, "giga_status": giga_model.get("status"), "vector_2048_status": vector_2048.get("status"), "package_status": pkg.get("status"), "cache_status": cache.get("status"), "safety_gate": giga_model.get("safety_gate"), "raw_text_logged": False, "raw_vectors_logged": False})
    environment: dict[str, Any] = dict(existing.get("environment", {})) if isinstance(existing.get("environment"), dict) else {}
    existing_logs = environment.get("raw_log_paths", []) if isinstance(environment.get("raw_log_paths"), list) else []
    environment.update({**resources, "package_status": pkg.get("status"), "cache_status": cache.get("status"), "raw_log_paths": sorted({*existing_logs, summary_log})})
    user_model = blocked_user_from_existing(existing, log_dir)
    vector_1024 = vector_1024_from_existing(existing, log_dir)
    other_models = [dict(giga_model), user_model]
    for model in existing.get("models", []):
        if isinstance(model, dict) and model.get("id") not in {USER_MODEL_ID, GIGA_MODEL_ID}:
            other_models.append(dict(model))
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "policy": {"managed_embedding_apis": "excluded", "local_open_weight_only": True, "downloads": "explicit-open-weight-only" if args.cache_or_explicit_download else "cache-only"},
        "environment": environment,
        "models": other_models,
        "vector_proofs": [vector_1024, dict(vector_2048)],
        "fixture_policy": {"source": "synthetic-and-s05-evidence-span-ids", "raw_legal_text_logged": False, "raw_vectors_logged": False, "production_legal_quality_claim": "not-proven"},
        "confidence_loop": {"question": "Ты на 100% уверен в этой стратегии?", "answer": "No. GigaEmbeddings runtime proof is safety-gated; a terminal block is evidence about local feasibility, not quality proof, and synthetic/S05-safe fixtures do not prove production legal retrieval quality.", "holes_found": ["GigaEmbeddings requires custom code/trust_remote_code and acceleration-sensitive local runtime conditions.", "Synthetic and S05-safe span fixtures do not prove real legal retrieval quality.", "FalkorDB vector proof is runtime-specific and not product pipeline implementation."], "fixes_or_next_proofs": ["Rerun T04 only when the explicit safety gate is satisfied.", "Use later product slices for real EvidenceSpan/SourceBlock retrieval evaluation.", "Repeat S10 vector proof on target deployment hardware before production claims."], "closed": False},
        "raw_log_paths": sorted({summary_log, *giga_model.get("raw_log_paths", []), *vector_2048.get("raw_log_paths", [])}),
    }


def build_giga_artifact(giga_model: Mapping[str, Any], vector_2048: Mapping[str, Any], pkg: Mapping[str, Any], cache: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema_version": GIGA_SCHEMA_VERSION, "generated_at": utc_now(), "model_id": GIGA_MODEL_ID, "status": "confirmed-runtime" if giga_model.get("status") == "confirmed-runtime" and vector_2048.get("status") == "confirmed-runtime" else giga_model.get("status"), "encode": {"status": giga_model.get("status"), "duration_ms": giga_model.get("encode_duration_ms"), "observed_vector_dimension": giga_model.get("observed_vector_dimension"), "retrieval_metrics": giga_model.get("retrieval_metrics"), "raw_log_paths": giga_model.get("raw_log_paths")}, "vector_2048": vector_2048, "safety_gate": giga_model.get("safety_gate"), "package_probe": pkg, "cache_probe": cache, "instruction_handling": giga_model.get("instruction_handling"), "fixture_policy": {"source": "synthetic-and-s05-evidence-span-ids", "raw_legal_text_logged": False, "raw_vectors_logged": False, "production_legal_quality_claim": "not-proven"}}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--runtime-artifact", type=Path, default=None)
    parser.add_argument("--cache-or-explicit-download", action="store_true")
    parser.add_argument("--require-safety-gate", action="store_true")
    parser.add_argument("--allow-custom-code", action="store_true")
    parser.add_argument("--allow-trust-remote-code", action="store_true")
    parser.add_argument("--allow-cpu-fallback", action="store_true")
    parser.add_argument("--allow-no-swap", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir
    runtime_artifact = args.runtime_artifact or output_dir / DEFAULT_RUNTIME_ARTIFACT.name
    giga_artifact_path = output_dir / DEFAULT_GIGA_ARTIFACT.name
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    existing = load_json(runtime_artifact)
    pkg = package_status(GIGA_REQUIREMENTS)
    cache = probe_model_cache(GIGA_MODEL_ID, huggingface_cache_roots())
    resources = resource_metadata(output_dir)
    gate_reasons = safety_gate_reasons(args, pkg, cache, resources)
    local_files_only = not args.cache_or_explicit_download

    if args.require_safety_gate and gate_reasons:
        gate_status = "blocked-environment" if any(reason.startswith(("embedding-packages-missing", "model-cache")) for reason in gate_reasons) else "not-safe-to-run"
        encode_result = blocked_giga_encode(gate_status, gate_reasons, pkg, cache, resources, log_dir)
    else:
        gate_status = "safe-to-run"
        encode_result = encode_giga_fixtures(GIGA_MODEL_ID, local_files_only, log_dir)

    giga_model = giga_model_entry(encode_result, pkg, cache, resources, args, gate_status, gate_reasons)
    vector_result = run_falkordb_vector_proof(
        cast("Sequence[str]", encode_result.get("document_ids", [])),
        cast("Sequence[Sequence[float]]", encode_result.get("document_vectors", [])),
        cast("Sequence[float]", cast("Sequence[Sequence[float]]", encode_result.get("query_vectors", [[]]))[0] if encode_result.get("query_vectors") else []),
        log_dir,
        args.timeout_seconds,
    )
    vector_2048 = vector_2048_entry(vector_result)

    giga_artifact = build_giga_artifact(giga_model, vector_2048, pkg, cache)
    write_json(giga_artifact_path, giga_artifact)
    runtime_payload = build_runtime_payload(existing, giga_model, vector_2048, pkg, cache, resources, log_dir, args)
    write_json(runtime_artifact, runtime_payload)

    if giga_artifact["status"] == "confirmed-runtime":
        print(f"S10 GigaEmbeddings proof confirmed: {normalized_path(giga_artifact_path)}")
        return 0
    if args.require_safety_gate and gate_reasons:
        print(f"S10 GigaEmbeddings proof gated: {normalized_path(giga_artifact_path)}")
        return 0
    print(f"S10 GigaEmbeddings proof blocked: {normalized_path(giga_artifact_path)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
