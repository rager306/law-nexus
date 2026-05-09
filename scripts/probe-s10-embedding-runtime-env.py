#!/usr/bin/env python3
"""Probe S10 local embedding runtime readiness without loading heavy models.

This runner records dependency, cache, download-mode, and hardware provenance for
real embedding runtime proof. It fails closed: no model is marked proven here, and
GigaEmbeddings is only considered safe when custom-code/hardware requirements are
explicitly satisfied by later tasks.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import shutil
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/milestones/M001/slices/S10"
DEFAULT_CONTRACT = ROOT / ".gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json"
SCHEMA_VERSION = "s10-embedding-runtime-proof/v1"
USER_MODEL_ID = "deepvk/USER-bge-m3"
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"
OPTIONAL_MODEL_ID = "BAAI/bge-m3"
ALLOWED_MODEL_IDS = {USER_MODEL_ID, GIGA_MODEL_ID, OPTIONAL_MODEL_ID}
PACKAGE_IMPORTS = {
    "sentence-transformers": "sentence_transformers",
    "transformers": "transformers",
    "torch": "torch",
    "flash-attn": "flash_attn",
    "FlagEmbedding": "FlagEmbedding",
    "falkordb": "falkordb",
    "redis": "redis",
}
FORBIDDEN_TERMS = ("GIGACHAT" + "_AUTH_DATA", "Bearer ", "sk-", "api_key")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def write_log(log_dir: Path, name: str, payload: Mapping[str, Any]) -> str:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "__")
    path = log_dir / f"{safe_name}.log"
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term in log {safe_name}")
    path.write_text(text, encoding="utf-8")
    return normalized_path(path)


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


def requirement_package_name(requirement: str) -> str:
    for separator in ("<", ">", "=", "!", "~", ";", "["):
        if separator in requirement:
            return requirement.split(separator, maxsplit=1)[0].strip()
    return requirement.strip()


def import_name_for_requirement(requirement: str) -> str:
    package = requirement_package_name(requirement)
    return PACKAGE_IMPORTS.get(package, package.replace("-", "_"))


def probe_package(requirement: str) -> dict[str, Any]:
    package = requirement_package_name(requirement)
    import_name = import_name_for_requirement(requirement)
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


def probe_packages(requirements: Sequence[str]) -> dict[str, Any]:
    probes = [probe_package(requirement) for requirement in requirements]
    missing = [probe["package"] for probe in probes if probe["status"] != "available"]
    return {
        "status": "available" if not missing else "blocked-environment",
        "missing": missing,
        "packages": probes,
    }


def probe_cache(model_id: str, roots: Sequence[Path]) -> dict[str, Any]:
    checked: list[str] = []
    snapshots: list[str] = []
    for root in roots:
        model_dir = root / model_cache_name(model_id)
        checked.append(normalized_path(model_dir))
        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.is_dir():
            snapshots.extend(sorted(path.name for path in snapshots_dir.iterdir() if path.is_dir()))
    return {
        "model_id": model_id,
        "status": "available" if snapshots else "absent",
        "present": bool(snapshots),
        "checked_paths": checked,
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


def hardware_metadata() -> dict[str, Any]:
    nvidia_smi = shutil.which("nvidia-smi")
    docker = shutil.which("docker")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "gpu_probe": {
            "nvidia_smi": nvidia_smi,
            "status": "available" if nvidia_smi else "absent",
        },
        "docker_probe": {
            "docker": docker,
            "status": "available" if docker else "absent",
        },
        **memory_metadata(),
    }


def disk_metadata(output_dir: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output_dir if output_dir.exists() else output_dir.parent)
    return {
        "total_mib": round(usage.total / 1024 / 1024, 1),
        "free_mib": round(usage.free / 1024 / 1024, 1),
        "used_mib": round(usage.used / 1024 / 1024, 1),
    }


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def configured_candidates(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates = contract.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Contract candidates must be a list")
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        model_id = candidate.get("id")
        if isinstance(model_id, str) and model_id in ALLOWED_MODEL_IDS:
            result.append(dict(candidate))
    return result


def parse_download_mode(args: argparse.Namespace) -> tuple[str, set[str]]:
    if args.allow_download_user:
        return "explicit-open-weight-only", {USER_MODEL_ID}
    if args.allow_download_giga:
        return "explicit-open-weight-only", {GIGA_MODEL_ID}
    if args.cache_only:
        return "cache-only", set()
    return "disabled", set()


def download_status(model_id: str, cache_present: bool, downloads_policy: str, allowed_downloads: set[str]) -> str:
    if cache_present:
        return "allowed-not-needed" if model_id in allowed_downloads else "cache-present"
    if downloads_policy == "explicit-open-weight-only" and model_id in allowed_downloads:
        return "allowed-download-not-executed-by-env-probe"
    if downloads_policy == "cache-only":
        return "cache-required-absent"
    return "disabled"


def root_cause_for_model(
    model_id: str,
    package_probe: Mapping[str, Any],
    cache_probe: Mapping[str, Any],
    downloads_policy: str,
    allowed_downloads: set[str],
    hardware: Mapping[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    missing = package_probe.get("missing") if isinstance(package_probe.get("missing"), list) else []
    if missing:
        return "blocked-environment", "embedding-packages-missing:" + ",".join(str(item) for item in missing), {}
    cache_present = bool(cache_probe.get("present"))
    if not cache_present and model_id not in allowed_downloads:
        return "blocked-environment", "model-cache-absent-and-download-not-allowed", {}
    if model_id == GIGA_MODEL_ID:
        reasons: list[str] = []
        gpu_probe = hardware.get("gpu_probe")
        if not isinstance(gpu_probe, dict) or gpu_probe.get("status") != "available":
            reasons.append("gpu-not-detected")
        if hardware.get("no_swap") is True:
            reasons.append("host-has-no-swap")
        if reasons:
            return "not-safe-to-run", "giga-safety-gate:" + ",".join(reasons), {
                "status": "not-safe-to-run",
                "reasons": reasons,
            }
    return "blocked-environment", "env-probe-does-not-load-models-run-next-proof-task", {}


def model_role(model_id: str) -> str:
    if model_id == USER_MODEL_ID:
        return "practical-baseline"
    if model_id == GIGA_MODEL_ID:
        return "quality-challenger"
    return "optional-reference"


def verdict_for_model(model_id: str, status: str) -> str:
    if model_id == USER_MODEL_ID:
        return "blocked-baseline"
    if model_id == GIGA_MODEL_ID and status == "not-safe-to-run":
        return "not-safe-challenger"
    if model_id == GIGA_MODEL_ID:
        return "deferred"
    return "deferred"


def model_next_step(model_id: str, status: str) -> str:
    if status == "not-safe-to-run":
        return "Provide GPU/flash-attn/custom-code safety approval or keep challenger deferred."
    if model_id == USER_MODEL_ID:
        return "Install optional embedding dependencies, populate USER-bge-m3 cache or explicitly allow open-weight download, then run T03 proof."
    if model_id == GIGA_MODEL_ID:
        return "Resolve package/cache/hardware gate, then run T04 only if safe."
    return "Evaluate only if runtime budget allows after primary models."


def model_entry(
    candidate: Mapping[str, Any],
    *,
    package_probe: Mapping[str, Any],
    cache_probe: Mapping[str, Any],
    downloads_policy: str,
    allowed_downloads: set[str],
    hardware: Mapping[str, Any],
    log_dir: Path,
) -> dict[str, Any]:
    model_id = str(candidate["id"])
    dimension = int(candidate.get("vector_dimension") or 0)
    status, root_cause, safety_gate = root_cause_for_model(
        model_id,
        package_probe,
        cache_probe,
        downloads_policy,
        allowed_downloads,
        hardware,
    )
    if model_id == GIGA_MODEL_ID and not safety_gate:
        safety_gate = {"status": "blocked-environment", "reasons": [root_cause]}
    elif model_id != GIGA_MODEL_ID:
        safety_gate = {"status": "confirmed-runtime", "reasons": []}
    entry: dict[str, Any] = {
        "id": model_id,
        "role": model_role(model_id),
        "status": status,
        "verdict": verdict_for_model(model_id, status),
        "vector_dimension": dimension,
        "max_token_limit": candidate.get("max_token_limit"),
        "package_status": package_probe.get("status"),
        "cache_status": cache_probe.get("status"),
        "download_status": download_status(model_id, bool(cache_probe.get("present")), downloads_policy, allowed_downloads),
        "runtime_status": status,
        "encode_duration_ms": None,
        "observed_vector_dimension": None,
        "resource_metadata": dict(hardware),
        "retrieval_metrics": None,
        "blocked_root_cause": root_cause,
        "next_proof_step": model_next_step(model_id, status),
        "instruction_handling": {
            "query_instruction_applied": model_id == GIGA_MODEL_ID,
            "document_instruction_applied": False,
        },
        "safety_gate": safety_gate,
        "package_details": package_probe,
        "cache_details": cache_probe,
        "raw_log_paths": [],
    }
    entry["raw_log_paths"] = [write_log(log_dir, f"env-{model_id}", entry)]
    return entry


def vector_entry(dimension: int, model_id: str, falkordb_probe: Mapping[str, Any], log_dir: Path) -> dict[str, Any]:
    missing = falkordb_probe.get("missing") if isinstance(falkordb_probe.get("missing"), list) else []
    root_cause = "falkordb-client-packages-missing:" + ",".join(str(item) for item in missing) if missing else "env-probe-does-not-start-falkordb-run-model-proof-task"
    entry: dict[str, Any] = {
        "dimension": dimension,
        "model_id": model_id,
        "status": "blocked-environment",
        "index_created": False,
        "query_executed": False,
        "duration_ms": None,
        "blocked_root_cause": root_cause,
        "next_proof_step": "Install FalkorDB client/runtime and run live vector proof task.",
        "package_details": falkordb_probe,
        "raw_log_paths": [],
    }
    entry["raw_log_paths"] = [write_log(log_dir, f"vector-env-{dimension}", entry)]
    return entry


def build_payload(output_dir: Path, contract_path: Path, downloads_policy: str, allowed_downloads: set[str]) -> dict[str, Any]:
    contract = load_contract(contract_path)
    candidates = configured_candidates(contract)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "logs"
    cache_roots = huggingface_cache_roots()
    hardware = hardware_metadata()
    hardware["disk_mib"] = disk_metadata(output_dir)
    model_entries: list[dict[str, Any]] = []
    for candidate in candidates:
        model_id = str(candidate["id"])
        requirements = candidate.get("runtime_requirements", {})
        packages = requirements.get("python_packages", []) if isinstance(requirements, dict) else []
        package_probe = probe_packages([str(package) for package in packages if isinstance(package, str)])
        cache_probe = probe_cache(model_id, cache_roots)
        model_entries.append(
            model_entry(
                candidate,
                package_probe=package_probe,
                cache_probe=cache_probe,
                downloads_policy=downloads_policy,
                allowed_downloads=allowed_downloads,
                hardware=hardware,
                log_dir=log_dir,
            )
        )
    falkordb_probe = probe_packages(["falkordb", "redis"])
    vector_entries = [
        vector_entry(1024, USER_MODEL_ID, falkordb_probe, log_dir),
        vector_entry(2048, GIGA_MODEL_ID, falkordb_probe, log_dir),
    ]
    environment = {
        "python": hardware["python"],
        "platform": hardware["platform"],
        "cpu_count": hardware["cpu_count"],
        "memory_mib": hardware.get("memory_mib"),
        "memory_available_mib": hardware.get("memory_available_mib"),
        "swap_total_mib": hardware.get("swap_total_mib"),
        "no_swap": hardware.get("no_swap"),
        "gpu_probe": hardware.get("gpu_probe"),
        "docker_probe": hardware.get("docker_probe"),
        "disk_mib": hardware.get("disk_mib"),
        "package_status": "available" if all(model["package_status"] == "available" for model in model_entries) else "blocked-environment",
        "cache_status": "available" if all(model["cache_status"] == "available" for model in model_entries if model["id"] in {USER_MODEL_ID, GIGA_MODEL_ID}) else "absent",
        "cache_roots_checked": [normalized_path(path) for path in cache_roots],
        "allowed_download_model_ids": sorted(allowed_downloads),
        "raw_log_paths": [],
    }
    environment["raw_log_paths"] = [write_log(log_dir, "environment", environment)]
    confidence_loop = {
        "question": "Ты на 100% уверен в этой стратегии?",
        "answer": "No. T02 is an environment readiness gate only; model encode and live vector query remain for T03/T04.",
        "holes_found": [
            "Embedding packages or model caches may be absent.",
            "GigaEmbeddings may be unsafe without GPU/flash-attn/custom-code approval.",
            "FalkorDB live vector query is not run by this environment probe.",
        ],
        "fixes_or_next_proofs": [
            "Run T03 for USER-bge-m3 after dependency/cache/download readiness is satisfied.",
            "Run T04 for GigaEmbeddings only after safety gate passes.",
            "Run live FalkorDB vector proof in model-specific proof tasks.",
        ],
        "closed": False,
    }
    summary = {
        "generated_at": utc_now(),
        "downloads_policy": downloads_policy,
        "allowed_download_model_ids": sorted(allowed_downloads),
        "model_statuses": {model["id"]: model["status"] for model in model_entries},
        "vector_statuses": {str(vector["dimension"]): vector["status"] for vector in vector_entries},
    }
    summary_log = write_log(log_dir, "summary", summary)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "policy": {
            "managed_embedding_apis": "excluded",
            "local_open_weight_only": True,
            "downloads": downloads_policy,
        },
        "environment": environment,
        "models": model_entries,
        "vector_proofs": vector_entries,
        "fixture_policy": {
            "source": "synthetic-and-s05-evidence-span-ids",
            "raw_legal_text_logged": False,
            "raw_vectors_logged": False,
            "production_legal_quality_claim": "not-proven",
        },
        "confidence_loop": confidence_loop,
        "raw_log_paths": [summary_log],
    }


def write_artifact(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    path = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term in artifact: {term}")
    path.write_text(text, encoding="utf-8")
    return path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--no-download", action="store_true")
    mode.add_argument("--cache-only", action="store_true")
    mode.add_argument("--allow-download-user", action="store_true")
    mode.add_argument("--allow-download-giga", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.contract.is_file():
        print(f"Contract not found: {args.contract}", file=sys.stderr)
        return 2
    downloads_policy, allowed_downloads = parse_download_mode(args)
    payload = build_payload(args.output_dir, args.contract, downloads_policy, allowed_downloads)
    artifact = write_artifact(args.output_dir, payload)
    print(
        json.dumps(
            {
                "artifact": normalized_path(artifact),
                "downloads": downloads_policy,
                "allowed_download_model_ids": sorted(allowed_downloads),
                "model_statuses": {model["id"]: model["status"] for model in payload["models"]},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
