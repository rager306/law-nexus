#!/usr/bin/env python3
"""Evaluate local/open-weight S09 embedding candidates on synthetic Russian legal retrieval.

The evaluator is intentionally bounded and local-first: it never contacts managed
embedding APIs, never downloads models unless --allow-download is explicit, and logs
only synthetic fixture identifiers plus metrics/diagnostics. Absent packages, caches,
or FalkorDB client/runtime support are terminally classified in the artifact instead
of being treated as silent success.
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
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/milestones/M001/slices/S09"
DEFAULT_CONTRACT = DEFAULT_OUTPUT_DIR / "S09-LOCAL-EMBEDDING-EVALUATION.json"
SCHEMA_VERSION = "s09-local-embedding-retrieval-evaluation/v1"
OWNER = "S09"
PRIMARY_MODEL_IDS = {
    "ai-sage/Giga-Embeddings-instruct",
    "deepvk/USER-bge-m3",
}
OPTIONAL_MODEL_IDS = {"BAAI/bge-m3"}
ALLOWED_MODEL_IDS = PRIMARY_MODEL_IDS | OPTIONAL_MODEL_IDS
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"
USER_MODEL_ID = "deepvk/USER-bge-m3"
QUERY_INSTRUCTION = (
    "Найди синтетические фрагменты российского права, которые отвечают на юридический вопрос."
)

Status = Literal[
    "available",
    "absent",
    "blocked-environment",
    "blocked-policy",
    "confirmed-runtime",
    "failed-runtime",
    "not-attempted",
]


@dataclass(frozen=True)
class RetrievalDocument:
    fixture_id: str
    topic: str
    text: str


@dataclass(frozen=True)
class RetrievalQuery:
    fixture_id: str
    relevant_document_id: str
    text: str


@dataclass(frozen=True)
class PackageProbe:
    package: str
    import_name: str
    status: Status
    version: str | None

    def to_json(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "import_name": self.import_name,
            "status": self.status,
            "version": self.version,
        }


PACKAGE_IMPORTS = {
    "sentence-transformers": "sentence_transformers",
    "transformers": "transformers",
    "torch": "torch",
    "flash-attn": "flash_attn",
    "FlagEmbedding": "FlagEmbedding",
    "falkordb": "falkordb",
    "redis": "redis",
}

DOCUMENTS: tuple[RetrievalDocument, ...] = (
    RetrievalDocument(
        "doc-procurement-notice-term",
        "procurement",
        "Синтетическая норма: заказчик размещает извещение о закупке и документацию в единой информационной системе не позднее установленного законом срока.",
    ),
    RetrievalDocument(
        "doc-contract-performance-penalty",
        "contract",
        "Синтетическая норма: поставщик обязан исполнить контракт в срок; за просрочку начисляется неустойка, если нарушение не вызвано обстоятельствами непреодолимой силы.",
    ),
    RetrievalDocument(
        "doc-court-appeal-deadline",
        "court",
        "Синтетическая норма: апелляционная жалоба подается через суд первой инстанции до истечения процессуального срока, исчисляемого со дня изготовления решения.",
    ),
    RetrievalDocument(
        "doc-personal-data-consent",
        "privacy",
        "Синтетическая норма: оператор обрабатывает персональные данные на основании согласия субъекта или иного законного основания и обязан обеспечить конфиденциальность.",
    ),
)

QUERIES: tuple[RetrievalQuery, ...] = (
    RetrievalQuery(
        "query-procurement-notice-term",
        "doc-procurement-notice-term",
        "Когда заказчик должен разместить извещение о закупке?",
    ),
    RetrievalQuery(
        "query-contract-performance-penalty",
        "doc-contract-performance-penalty",
        "Какие последствия возникают при просрочке исполнения контракта поставщиком?",
    ),
    RetrievalQuery(
        "query-court-appeal-deadline",
        "doc-court-appeal-deadline",
        "Куда подается апелляционная жалоба и как учитывается срок?",
    ),
    RetrievalQuery(
        "query-personal-data-consent",
        "doc-personal-data-consent",
        "На каком основании оператор может обрабатывать персональные данные?",
    ),
)


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
    hub_cache = active_env.get("HUGGINGFACE_HUB_CACHE")
    hf_home = active_env.get("HF_HOME")
    transformers_cache = active_env.get("TRANSFORMERS_CACHE")
    if hub_cache:
        paths.append(Path(hub_cache))
    if hf_home:
        paths.append(Path(hf_home) / "hub")
    if transformers_cache:
        paths.append(Path(transformers_cache))
    paths.append(Path.home() / ".cache/huggingface/hub")
    return unique_paths(paths)


def requirement_package_name(requirement: str) -> str:
    for separator in ("<", ">", "=", "!", "~", ";", "["):
        if separator in requirement:
            return requirement.split(separator, maxsplit=1)[0].strip()
    return requirement.strip()


def probe_package(package: str) -> PackageProbe:
    distribution_name = requirement_package_name(package)
    import_name = PACKAGE_IMPORTS.get(distribution_name, distribution_name.replace("-", "_"))
    if importlib.util.find_spec(import_name) is None:
        return PackageProbe(package, import_name, "absent", None)
    try:
        version = importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        version = None
    return PackageProbe(package, import_name, "available", version)


def probe_required_packages(packages: Sequence[str]) -> dict[str, Any]:
    probes = [probe_package(package) for package in packages]
    missing = [probe.package for probe in probes if probe.status != "available"]
    return {
        "status": "available" if not missing else "blocked-environment",
        "missing": missing,
        "packages": [probe.to_json() for probe in probes],
    }


def probe_model_cache(model_id: str, cache_roots: Sequence[Path]) -> dict[str, Any]:
    checked_paths: list[str] = []
    snapshots: list[str] = []
    for root in cache_roots:
        model_dir = root / model_cache_name(model_id)
        checked_paths.append(normalized_path(model_dir))
        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.is_dir():
            snapshots.extend(sorted(path.name for path in snapshots_dir.iterdir() if path.is_dir()))
    present = bool(snapshots)
    return {
        "model_id": model_id,
        "status": "available" if present else "absent",
        "present": present,
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
        "mem_total_mib": values.get("MemTotal"),
        "mem_available_mib": values.get("MemAvailable"),
        "swap_total_mib": values.get("SwapTotal"),
        "no_swap": values.get("SwapTotal") == 0 if "SwapTotal" in values else None,
    }


def resource_metadata() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        **memory_metadata(),
    }


def fixture_metadata() -> dict[str, Any]:
    return {
        "fixture_class": "synthetic-russian-legal-style-retrieval",
        "documents": [document.fixture_id for document in DOCUMENTS],
        "queries": [query.fixture_id for query in QUERIES],
        "contents_logged": False,
        "deterministic_ids": True,
    }


def format_query_for_model(model_id: str, query: str) -> str:
    if model_id == GIGA_MODEL_ID:
        return f"Instruct: {QUERY_INSTRUCTION}\nQuery: {query}"
    return query


def format_document_for_model(_model_id: str, document: str) -> str:
    return document


def dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def l2_norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    denominator = l2_norm(left) * l2_norm(right)
    if denominator == 0:
        return 0.0
    return dot_product(left, right) / denominator


def coerce_vectors(value: object) -> list[list[float]]:
    raw_value: Any = value
    tolist = getattr(raw_value, "tolist", None)
    if callable(tolist):
        raw_value = tolist()
    if not isinstance(raw_value, list):
        raise TypeError("encoded vectors must be list-like")
    result: list[list[float]] = []
    for row in raw_value:
        raw_row: Any = row
        row_tolist = getattr(raw_row, "tolist", None)
        if callable(row_tolist):
            raw_row = row_tolist()
        if not isinstance(raw_row, list):
            raise TypeError("encoded vector row must be list-like")
        result.append([float(item) for item in raw_row])
    return result


def compute_retrieval_metrics(
    query_vectors: Sequence[Sequence[float]],
    document_vectors: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if len(query_vectors) != len(QUERIES):
        raise ValueError("query vector count does not match fixture count")
    if len(document_vectors) != len(DOCUMENTS):
        raise ValueError("document vector count does not match fixture count")

    document_ids = [document.fixture_id for document in DOCUMENTS]
    ranks: list[int] = []
    top_hits: list[dict[str, Any]] = []
    for query, query_vector in zip(QUERIES, query_vectors, strict=True):
        scored = sorted(
            (
                (document_ids[index], cosine_similarity(query_vector, document_vector))
                for index, document_vector in enumerate(document_vectors)
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_ids = [document_id for document_id, _score in scored]
        rank = ranked_ids.index(query.relevant_document_id) + 1
        ranks.append(rank)
        top_hits.append(
            {
                "query_id": query.fixture_id,
                "expected_document_id": query.relevant_document_id,
                "top_document_id": scored[0][0],
                "rank": rank,
                "top_score": round(scored[0][1], 6),
            }
        )
    return {
        "query_count": len(QUERIES),
        "document_count": len(DOCUMENTS),
        "recall_at_1": round(sum(1 for rank in ranks if rank <= 1) / len(ranks), 6),
        "recall_at_3": round(sum(1 for rank in ranks if rank <= 3) / len(ranks), 6),
        "mrr": round(sum(1 / rank for rank in ranks) / len(ranks), 6),
        "ranks": ranks,
        "top_hits": top_hits,
    }


def encode_fixture_with_sentence_transformers(
    model_id: str,
    *,
    allow_download: bool,
    trust_remote_code: bool,
    max_token_limit: int | None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        module = importlib.import_module("sentence_transformers")
        sentence_transformer = getattr(module, "SentenceTransformer")
        model = sentence_transformer(
            model_id,
            trust_remote_code=trust_remote_code,
            local_files_only=not allow_download,
        )
        if max_token_limit is not None and hasattr(model, "max_seq_length"):
            model.max_seq_length = min(max_token_limit, 256)
        query_inputs = [format_query_for_model(model_id, query.text) for query in QUERIES]
        document_inputs = [format_document_for_model(model_id, document.text) for document in DOCUMENTS]
        query_vectors = coerce_vectors(
            model.encode(
                query_inputs,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        )
        document_vectors = coerce_vectors(
            model.encode(
                document_inputs,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        )
        observed_dimension = len(document_vectors[0]) if document_vectors else None
        return {
            "runtime_status": "confirmed-runtime",
            "encode_duration_ms": round((time.monotonic() - started) * 1000, 2),
            "observed_vector_dimension": observed_dimension,
            "metrics": compute_retrieval_metrics(query_vectors, document_vectors),
            "error": None,
        }
    except BaseException as exc:  # noqa: BLE001 - evaluator records bounded model/runtime failures.
        return {
            "runtime_status": "failed-runtime",
            "encode_duration_ms": round((time.monotonic() - started) * 1000, 2),
            "observed_vector_dimension": None,
            "metrics": None,
            "error": {
                "exception_class": exc.__class__.__name__,
                "exception_message": str(exc)[:600],
            },
        }


def package_blocker(package_probe: Mapping[str, Any]) -> str | None:
    if package_probe.get("status") != "available":
        missing = [str(package) for package in package_probe.get("missing", [])]
        return "embedding-packages-missing:" + ",".join(missing)
    return None


def cache_blocker(cache_probe: Mapping[str, Any], allow_download: bool) -> str | None:
    if bool(cache_probe.get("present")) or allow_download:
        return None
    return "model-cache-absent-no-download"


def download_status(cache_present: bool, allow_download: bool) -> str:
    if cache_present:
        return "allowed-not-needed" if allow_download else "not-attempted"
    if allow_download:
        return "allowed-download-may-run"
    return "disabled-no-download"


def should_attempt_runtime(package_probe: Mapping[str, Any], cache_probe: Mapping[str, Any], allow_download: bool) -> bool:
    return package_blocker(package_probe) is None and cache_blocker(cache_probe, allow_download) is None


def probe_falkordb_vector_dimension(dimension: int, log_dir: Path) -> dict[str, Any]:
    started = time.monotonic()
    package_probe = probe_required_packages(["falkordb", "redis"])
    vector = [0.0] * dimension
    vector[0] = 1.0
    vector[-1] = 1.0
    status = "blocked-environment" if package_probe["status"] != "available" else "not-attempted"
    root_cause = None
    if package_probe["status"] != "available":
        root_cause = "falkordb-client-packages-missing:" + ",".join(str(item) for item in package_probe["missing"])
    else:
        root_cause = "falkordb-runtime-not-configured-for-t03-no-download-probe"
    payload: dict[str, Any] = {
        "dimension": dimension,
        "status": status,
        "blocked_root_cause": root_cause,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
        "synthetic_vector_metadata": {
            "dimension": len(vector),
            "value_type": "float32-compatible-python-float",
            "contents_logged": False,
            "non_zero_count": 2,
        },
        "package_status": package_probe,
        "basis": "Dimension-specific synthetic vector payload generated; live FalkorDB index/query is blocked unless FalkorDB client/runtime packages are available.",
    }
    log_path = write_log(log_dir, f"falkordb-vector-dim-{dimension}", payload)
    payload["raw_log_paths"] = [normalized_path(log_path)]
    write_log(log_dir, f"falkordb-vector-dim-{dimension}", payload)
    return payload


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def configured_candidates(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates = contract.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Contract field 'candidates' must be a list.")
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        model_id = str(candidate.get("id", ""))
        if model_id in ALLOWED_MODEL_IDS:
            result.append(candidate)
    return result


def write_log(log_dir: Path, name: str, payload: Mapping[str, Any]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "__")
    path = log_dir / f"{safe_name}.log"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def evaluate_candidate(
    candidate: Mapping[str, Any],
    *,
    cache_roots: Sequence[Path],
    allow_download: bool,
    log_dir: Path,
    resources: Mapping[str, Any],
    vector_probes: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    model_id = str(candidate["id"])
    if model_id not in ALLOWED_MODEL_IDS:
        raise ValueError(f"Model is outside the S09 open-weight allow-list: {model_id}")
    runtime_requirements = candidate.get("runtime_requirements", {})
    package_names = runtime_requirements.get("python_packages", []) if isinstance(runtime_requirements, dict) else []
    packages = [str(package) for package in package_names if isinstance(package, str)]
    package_probe = probe_required_packages(packages)
    cache_probe = probe_model_cache(model_id, cache_roots)
    expected_dimension_raw = candidate.get("vector_dimension")
    expected_dimension = int(expected_dimension_raw) if isinstance(expected_dimension_raw, int) else None
    max_token_limit_raw = candidate.get("max_token_limit")
    max_token_limit = int(max_token_limit_raw) if isinstance(max_token_limit_raw, int) else None
    trust_remote_code = bool(
        isinstance(runtime_requirements, dict) and runtime_requirements.get("trust_remote_code_required")
    )
    root_cause = package_blocker(package_probe) or cache_blocker(cache_probe, allow_download)

    if should_attempt_runtime(package_probe, cache_probe, allow_download):
        runtime = encode_fixture_with_sentence_transformers(
            model_id,
            allow_download=allow_download,
            trust_remote_code=trust_remote_code,
            max_token_limit=max_token_limit,
        )
        if runtime["runtime_status"] == "failed-runtime" and root_cause is None:
            root_cause = "encode-runtime-failed"
    else:
        runtime = {
            "runtime_status": "blocked-environment",
            "encode_duration_ms": None,
            "observed_vector_dimension": None,
            "metrics": None,
            "error": None,
        }

    vector_probe = vector_probes.get(expected_dimension) if expected_dimension is not None else None
    result: dict[str, Any] = {
        "id": model_id,
        "role": candidate.get("role"),
        "package_status": package_probe["status"],
        "package_details": package_probe,
        "cache_status": cache_probe["status"],
        "cache_details": cache_probe,
        "download_status": download_status(bool(cache_probe["present"]), allow_download),
        "runtime_status": runtime["runtime_status"],
        "vector_dimension": expected_dimension,
        "observed_vector_dimension": runtime["observed_vector_dimension"],
        "max_token_limit": max_token_limit,
        "encode_duration_ms": runtime["encode_duration_ms"],
        "benchmark_result_status": "completed" if runtime["metrics"] is not None else "blocked",
        "retrieval_metrics": runtime["metrics"],
        "blocked_root_cause": root_cause,
        "runtime_error": runtime["error"],
        "resource_metadata": dict(resources),
        "instruction_handling": {
            "query_instruction_applied": model_id == GIGA_MODEL_ID,
            "query_instruction_template": "Instruct: {task_description}\\nQuery: {query}" if model_id == GIGA_MODEL_ID else None,
            "document_instruction_applied": False,
            "baseline_plain_encoding": model_id in {USER_MODEL_ID, "BAAI/bge-m3"},
        },
        "fixture_metadata": fixture_metadata(),
        "falkordb_vector_compatibility": vector_probe,
        "raw_log_paths": [],
    }
    log_path = write_log(log_dir, f"retrieval-{model_id}", result)
    result["raw_log_paths"] = [normalized_path(log_path)]
    if vector_probe is not None:
        result["raw_log_paths"].extend(str(path) for path in vector_probe.get("raw_log_paths", []))
    write_log(log_dir, f"retrieval-{model_id}", result)
    return result


def summarize_status(model_results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in model_results:
        status = str(model.get("runtime_status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def write_json_artifact(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    path = output_dir / "S09-LOCAL-EMBEDDING-RETRIEVAL-EVAL.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_markdown_artifact(output_dir: Path, payload: Mapping[str, Any], json_path: Path) -> Path:
    rows = []
    for model in payload["models"]:
        metrics = model.get("retrieval_metrics") or {}
        rows.append(
            "| `{id}` | {runtime} | {dim} | {max_tokens} | {encode_ms} | {benchmark} | {recall} | {mrr} | {vector_status} | `{blocked}` | {logs} |".format(
                id=model["id"],
                runtime=model["runtime_status"],
                dim=model["vector_dimension"],
                max_tokens=model["max_token_limit"],
                encode_ms=model["encode_duration_ms"],
                benchmark=model["benchmark_result_status"],
                recall=metrics.get("recall_at_1"),
                mrr=metrics.get("mrr"),
                vector_status=(model.get("falkordb_vector_compatibility") or {}).get("status"),
                blocked=model["blocked_root_cause"],
                logs=", ".join(f"`{path}`" for path in model["raw_log_paths"]),
            )
        )
    body = "\n".join(
        [
            "# S09 Synthetic Russian Legal Retrieval Evaluation",
            "",
            f"- Schema: `{payload['schema_version']}`",
            f"- Generated: `{payload['generated_at']}`",
            f"- Download mode: `{payload['download_mode']}`",
            f"- JSON artifact: `{normalized_path(json_path)}`",
            f"- Managed APIs contacted: `{payload['managed_apis_contacted']}`",
            f"- Synthetic fixtures only: `{payload['synthetic_fixtures_only']}`",
            "",
            "| Model | Runtime | Dim | Max tokens | Encode ms | Benchmark | Recall@1 | MRR | FalkorDB vector | Blocked root cause | Raw logs |",
            "|---|---|---:|---:|---:|---|---:|---:|---|---|---|",
            *rows,
            "",
            "## Boundary",
            "",
            "Metrics are produced only when local/open-weight candidate models can run from cache or explicit download. Synthetic fixture scores are runtime smoke evidence, not Russian legal retrieval quality proof. No managed GigaChat or other external embedding API path is used.",
            "",
        ]
    )
    path = output_dir / "S09-LOCAL-EMBEDDING-RETRIEVAL-EVAL.md"
    path.write_text(body, encoding="utf-8")
    return path


def update_contract_with_evaluation(contract_path: Path, payload: Mapping[str, Any], json_path: Path, markdown_path: Path) -> None:
    contract = load_contract(contract_path)
    contract["latest_synthetic_retrieval_evaluation"] = {
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "download_mode": payload["download_mode"],
        "artifact_paths": {
            "json": normalized_path(json_path),
            "markdown": normalized_path(markdown_path),
        },
        "status_counts": payload["status_counts"],
        "vector_probe_dimensions": [probe["dimension"] for probe in payload["falkordb_vector_probes"]],
        "models": [
            {
                "id": model["id"],
                "runtime_status": model["runtime_status"],
                "benchmark_result_status": model["benchmark_result_status"],
                "encode_duration_ms": model["encode_duration_ms"],
                "blocked_root_cause": model["blocked_root_cause"],
                "raw_log_paths": model["raw_log_paths"],
                "retrieval_metrics": model["retrieval_metrics"],
                "falkordb_vector_compatibility": model["falkordb_vector_compatibility"],
            }
            for model in payload["models"]
        ],
    }
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_payload(
    *,
    output_dir: Path,
    contract_path: Path,
    allow_download: bool,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    candidates = configured_candidates(contract)
    resources = resource_metadata()
    log_dir = output_dir / "logs"
    vector_dimensions = sorted(
        {
            int(candidate["vector_dimension"])
            for candidate in candidates
            if isinstance(candidate.get("vector_dimension"), int) and int(candidate["vector_dimension"]) in {1024, 2048}
        }
        | {1024, 2048}
    )
    vector_probes_by_dimension = {
        dimension: probe_falkordb_vector_dimension(dimension, log_dir) for dimension in vector_dimensions
    }
    cache_roots = huggingface_cache_roots()
    model_results = [
        evaluate_candidate(
            candidate,
            cache_roots=cache_roots,
            allow_download=allow_download,
            log_dir=log_dir,
            resources=resources,
            vector_probes=vector_probes_by_dimension,
        )
        for candidate in candidates
    ]
    summary_log = write_log(
        log_dir,
        "retrieval-summary",
        {
            "generated_at": utc_now(),
            "download_mode": "allow-download" if allow_download else "no-download",
            "model_count": len(model_results),
            "status_counts": summarize_status(model_results),
            "vector_dimensions": vector_dimensions,
        },
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "generated_at": utc_now(),
        "contract_path": normalized_path(contract_path),
        "download_mode": "allow-download" if allow_download else "no-download",
        "managed_apis_contacted": False,
        "allowed_model_ids": sorted(ALLOWED_MODEL_IDS),
        "synthetic_fixtures_only": True,
        "fixture_metadata": fixture_metadata(),
        "resource_metadata": resources,
        "cache_roots_checked": [normalized_path(path) for path in cache_roots],
        "falkordb_vector_probes": [vector_probes_by_dimension[dimension] for dimension in vector_dimensions],
        "models": model_results,
        "status_counts": summarize_status(model_results),
        "raw_log_paths": [normalized_path(summary_log)],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    download_group = parser.add_mutually_exclusive_group()
    download_group.add_argument(
        "--no-download",
        action="store_true",
        help="Do not download models; classify absent cache as blocked. This is the default.",
    )
    download_group.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow Hugging Face downloads for allow-listed open-weight model IDs only.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.contract.is_file():
        print(f"Contract not found: {args.contract}", file=sys.stderr)
        return 2
    payload = build_payload(
        output_dir=output_dir,
        contract_path=args.contract,
        allow_download=bool(args.allow_download),
    )
    json_path = write_json_artifact(output_dir, payload)
    markdown_path = write_markdown_artifact(output_dir, payload, json_path)
    update_contract_with_evaluation(args.contract, payload, json_path, markdown_path)
    print(
        json.dumps(
            {
                "json": normalized_path(json_path),
                "markdown": normalized_path(markdown_path),
                "status_counts": payload["status_counts"],
                "vector_probe_dimensions": [probe["dimension"] for probe in payload["falkordb_vector_probes"]],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
