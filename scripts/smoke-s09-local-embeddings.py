#!/usr/bin/env python3
"""Cache-aware local/open-weight Russian embedding smoke harness for M001/S09.

The harness is deliberately local-first: it never calls managed embedding APIs,
never downloads by default, and only attempts Hugging Face model loading when the
required packages and either a local cache or explicit --allow-download are present.
All emitted text uses synthetic legal-style fixtures and bounded metadata; raw legal
document contents, secrets, and embedding values are not logged.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
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
SCHEMA_VERSION = "s09-local-embedding-smoke/v1"
OWNER = "S09"
PRIMARY_MODEL_IDS = {
    "ai-sage/Giga-Embeddings-instruct",
    "deepvk/USER-bge-m3",
}
OPTIONAL_MODEL_IDS = {"BAAI/bge-m3"}
ALLOWED_MODEL_IDS = PRIMARY_MODEL_IDS | OPTIONAL_MODEL_IDS
SYNTHETIC_FIXTURES = (
    "Синтетическая правовая норма: заказчик размещает извещение о закупке в установленный срок.",
    "Синтетический запрос: какие обязанности возникают у поставщика по контракту?",
)
PACKAGE_IMPORTS = {
    "sentence-transformers": "sentence_transformers",
    "transformers": "transformers",
    "torch": "torch",
    "flash-attn": "flash_attn",
    "FlagEmbedding": "FlagEmbedding",
}

ProbeStatus = Literal[
    "available",
    "absent",
    "not-required",
    "not-attempted",
    "disabled-no-download",
    "allowed-not-needed",
    "allowed-download-may-run",
    "blocked-environment",
    "blocked-policy",
    "confirmed-runtime",
    "failed-runtime",
    "pending-dimension-specific-probe",
]


@dataclass(frozen=True)
class PackageProbe:
    package: str
    import_name: str
    status: ProbeStatus
    version: str | None

    def to_json(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "import_name": self.import_name,
            "status": self.status,
            "version": self.version,
        }


@dataclass(frozen=True)
class CacheProbe:
    model_id: str
    status: ProbeStatus
    present: bool
    checked_paths: tuple[str, ...]
    snapshots: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "status": self.status,
            "present": self.present,
            "checked_paths": list(self.checked_paths),
            "snapshot_count": len(self.snapshots),
            "snapshots": list(self.snapshots),
        }


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    gsd_root = ROOT / ".gsd"
    if gsd_root.exists():
        try:
            return f".gsd/{resolved.relative_to(gsd_root.resolve()).as_posix()}"
        except ValueError:
            pass
    try:
        return resolved.relative_to(ROOT).as_posix()
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
    if hub_cache:
        paths.append(Path(hub_cache))
    if hf_home:
        paths.append(Path(hf_home) / "hub")
    paths.append(Path.home() / ".cache/huggingface/hub")
    return unique_paths(paths)


def requirement_package_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()


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


def probe_model_cache(model_id: str, cache_roots: Sequence[Path]) -> CacheProbe:
    checked: list[str] = []
    snapshots: list[str] = []
    for root in cache_roots:
        model_dir = root / model_cache_name(model_id)
        checked.append(normalized_path(model_dir))
        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.is_dir():
            snapshots.extend(sorted(path.name for path in snapshots_dir.iterdir() if path.is_dir()))
    present = bool(snapshots)
    return CacheProbe(
        model_id=model_id,
        status="available" if present else "absent",
        present=present,
        checked_paths=tuple(checked),
        snapshots=tuple(sorted(set(snapshots))),
    )


def memory_metadata() -> dict[str, Any]:
    meminfo = Path("/proc/meminfo")
    values: dict[str, float] = {}
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].rstrip(":") in {"MemTotal", "MemAvailable", "SwapTotal"}:
                values[parts[0].rstrip(":")] = round(int(parts[1]) / 1024, 1)
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


def download_status(cache_present: bool, allow_download: bool) -> ProbeStatus:
    if cache_present:
        return "allowed-not-needed" if allow_download else "not-attempted"
    if allow_download:
        return "allowed-download-may-run"
    return "disabled-no-download"


def blocked_root_cause(
    package_status: str,
    missing_packages: Sequence[str],
    cache_present: bool,
    allow_download: bool,
) -> str | None:
    if package_status != "available":
        return "embedding-packages-missing:" + ",".join(missing_packages)
    if not cache_present and not allow_download:
        return "model-cache-absent-no-download"
    return None


def synthetic_fixture_metadata() -> dict[str, Any]:
    return {
        "fixture_class": "synthetic-russian-legal-style",
        "fixture_count": len(SYNTHETIC_FIXTURES),
        "contents_logged": False,
        "max_chars": max(len(text) for text in SYNTHETIC_FIXTURES),
    }


def encode_with_sentence_transformers(
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
            model.max_seq_length = min(max_token_limit, 128)
        vectors = model.encode(
            list(SYNTHETIC_FIXTURES),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        shape = getattr(vectors, "shape", None)
        vector_count = int(shape[0]) if shape is not None and len(shape) >= 1 else len(vectors)
        vector_dimension = int(shape[1]) if shape is not None and len(shape) >= 2 else None
        return {
            "runtime_status": "confirmed-runtime",
            "encode_duration_ms": round((time.monotonic() - started) * 1000, 2),
            "vector_count": vector_count,
            "observed_vector_dimension": vector_dimension,
            "error": None,
        }
    except BaseException as exc:  # noqa: BLE001 - smoke harness records bounded runtime failures.
        return {
            "runtime_status": "failed-runtime",
            "encode_duration_ms": round((time.monotonic() - started) * 1000, 2),
            "vector_count": None,
            "observed_vector_dimension": None,
            "error": {
                "exception_class": exc.__class__.__name__,
                "exception_message": str(exc)[:600],
            },
        }


def should_attempt_encode(root_cause: str | None, cache_present: bool, allow_download: bool) -> bool:
    if root_cause is not None:
        return False
    return cache_present or allow_download


def probe_candidate(
    candidate: Mapping[str, Any],
    *,
    cache_roots: Sequence[Path],
    allow_download: bool,
    log_dir: Path,
    resources: Mapping[str, Any],
) -> dict[str, Any]:
    model_id = str(candidate["id"])
    if model_id not in ALLOWED_MODEL_IDS:
        raise ValueError(f"Model is outside the S09 open-weight allow-list: {model_id}")

    runtime_requirements = candidate.get("runtime_requirements", {})
    package_names = runtime_requirements.get("python_packages", []) if isinstance(runtime_requirements, dict) else []
    packages = [str(package) for package in package_names if isinstance(package, str)]
    package_probe = probe_required_packages(packages)
    cache_probe = probe_model_cache(model_id, cache_roots)
    root_cause = blocked_root_cause(
        str(package_probe["status"]),
        [str(package) for package in package_probe["missing"]],
        cache_probe.present,
        allow_download,
    )
    max_token_limit_raw = candidate.get("max_token_limit")
    max_token_limit = int(max_token_limit_raw) if isinstance(max_token_limit_raw, int) else None
    expected_dimension_raw = candidate.get("vector_dimension")
    expected_dimension = int(expected_dimension_raw) if isinstance(expected_dimension_raw, int) else None
    trust_remote_code = bool(
        isinstance(runtime_requirements, dict) and runtime_requirements.get("trust_remote_code_required")
    )

    encode_result: dict[str, Any]
    if should_attempt_encode(root_cause, cache_probe.present, allow_download):
        encode_result = encode_with_sentence_transformers(
            model_id,
            allow_download=allow_download,
            trust_remote_code=trust_remote_code,
            max_token_limit=max_token_limit,
        )
        if encode_result["runtime_status"] == "failed-runtime" and root_cause is None:
            root_cause = "encode-runtime-failed"
    else:
        encode_result = {
            "runtime_status": "blocked-environment",
            "encode_duration_ms": None,
            "vector_count": None,
            "observed_vector_dimension": None,
            "error": None,
        }

    falkordb_vector_compatibility = {
        "dimension": expected_dimension,
        "status": "pending-dimension-specific-probe",
        "required_probe_owner": "S09-T03",
        "basis": "T02 records candidate dimension and local runtime state; T03 owns FalkorDB dimension-specific vector probes.",
    }
    result: dict[str, Any] = {
        "id": model_id,
        "role": candidate.get("role"),
        "package_status": package_probe["status"],
        "package_details": package_probe,
        "cache_status": cache_probe.status,
        "cache_details": cache_probe.to_json(),
        "download_status": download_status(cache_probe.present, allow_download),
        "runtime_status": encode_result["runtime_status"],
        "vector_dimension": expected_dimension,
        "observed_vector_dimension": encode_result["observed_vector_dimension"],
        "max_token_limit": max_token_limit,
        "encode_duration_ms": encode_result["encode_duration_ms"],
        "resource_metadata": dict(resources),
        "falkordb_vector_compatibility": falkordb_vector_compatibility,
        "benchmark_result_status": "not-run-smoke-only",
        "blocked_root_cause": root_cause,
        "synthetic_fixture_metadata": synthetic_fixture_metadata(),
        "runtime_error": encode_result["error"],
        "raw_log_paths": [],
    }
    log_path = write_log(log_dir, model_id, result)
    result["raw_log_paths"] = [normalized_path(log_path)]
    write_log(log_dir, model_id, result)
    return result


def summarize_status(model_results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in model_results:
        status = str(model.get("runtime_status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def write_json_artifact(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    path = output_dir / "S09-LOCAL-EMBEDDING-SMOKE.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_markdown_artifact(output_dir: Path, payload: Mapping[str, Any], json_path: Path) -> Path:
    rows = []
    for model in payload["models"]:
        rows.append(
            "| `{id}` | {package_status} | {cache_status} | {download_status} | {runtime_status} | {vector_dimension} | {max_token_limit} | {encode_duration_ms} | {benchmark_result_status} | `{blocked_root_cause}` | {raw_logs} |".format(
                id=model["id"],
                package_status=model["package_status"],
                cache_status=model["cache_status"],
                download_status=model["download_status"],
                runtime_status=model["runtime_status"],
                vector_dimension=model["vector_dimension"],
                max_token_limit=model["max_token_limit"],
                encode_duration_ms=model["encode_duration_ms"],
                benchmark_result_status=model["benchmark_result_status"],
                blocked_root_cause=model["blocked_root_cause"],
                raw_logs=", ".join(f"`{path}`" for path in model["raw_log_paths"]),
            )
        )
    body = "\n".join(
        [
            "# S09 Local Embedding Smoke Results",
            "",
            f"- Schema: `{payload['schema_version']}`",
            f"- Generated: `{payload['generated_at']}`",
            f"- Download mode: `{payload['download_mode']}`",
            f"- JSON artifact: `{normalized_path(json_path)}`",
            f"- Managed APIs contacted: `{payload['managed_apis_contacted']}`",
            f"- Synthetic fixtures only: `{payload['synthetic_fixtures_only']}`",
            "",
            "| Model | Packages | Cache | Download | Runtime | Dim | Max tokens | Encode ms | Benchmark | Blocked root cause | Raw logs |",
            "|---|---|---|---|---|---:|---:|---:|---|---|---|",
            *rows,
            "",
            "## Resource Metadata",
            "",
            "```json",
            json.dumps(payload["resource_metadata"], ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Boundary",
            "",
            "This smoke harness is local/open-weight only. It does not contact managed GigaChat or other embedding APIs. In no-download mode, absent Hugging Face cache is reported as a blocked environment condition rather than triggering network access.",
            "",
        ]
    )
    path = output_dir / "S09-LOCAL-EMBEDDING-SMOKE.md"
    path.write_text(body, encoding="utf-8")
    return path


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
    cache_roots = huggingface_cache_roots()
    model_results = [
        probe_candidate(
            candidate,
            cache_roots=cache_roots,
            allow_download=allow_download,
            log_dir=log_dir,
            resources=resources,
        )
        for candidate in candidates
    ]
    summary_log = write_log(
        log_dir,
        "summary",
        {
            "generated_at": utc_now(),
            "download_mode": "allow-download" if allow_download else "no-download",
            "model_count": len(model_results),
            "status_counts": summarize_status(model_results),
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
        "synthetic_fixture_metadata": synthetic_fixture_metadata(),
        "resource_metadata": resources,
        "cache_roots_checked": [normalized_path(path) for path in cache_roots],
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
    print(json.dumps({"json": normalized_path(json_path), "markdown": normalized_path(markdown_path), "status_counts": payload["status_counts"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
