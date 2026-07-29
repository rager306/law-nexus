"""Reusable local embedding proof environment helpers.

These helpers support bounded proof and smoke wrappers for local/open-weight
embedding experiments. They inspect environment metadata and filesystem/cache
shape only; they do not load models or validate retrieval/legal quality.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EMBEDDING_PROOF_ENVIRONMENT_NON_CLAIMS = (
    "Does not call managed GigaChat or external embedding APIs.",
    "Does not prove a model is installed or usable for encode calls.",
    "Does not prove embedding quality or retrieval quality.",
    "Does not prove legal correctness or answer faithfulness.",
    "Does not prove FalkorDB vector-index production readiness.",
    "Does not persist raw vectors.",
)


@dataclass(frozen=True)
class PackageAvailability:
    """Observed import/distribution availability for a runtime requirement."""

    requirement: str
    distribution: str
    import_name: str
    status: str
    version: str | None

    def to_json(self) -> dict[str, Any]:
        """Return the stable JSON shape used by proof wrappers."""

        return {
            "package": self.requirement,
            "distribution": self.distribution,
            "import_name": self.import_name,
            "status": self.status,
            "version": self.version,
        }


def normalized_path(path: Path, *, root: Path, prefer_gsd_root: bool = False) -> str:
    """Render a path relative to root, optionally preferring the root's .gsd subtree."""

    resolved = path.resolve()
    if prefer_gsd_root:
        gsd_root = root / ".gsd"
        if gsd_root.exists():
            try:
                return f".gsd/{resolved.relative_to(gsd_root.resolve()).as_posix()}"
            except ValueError:
                pass
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def write_json_log(
    log_dir: Path,
    name: str,
    payload: Mapping[str, Any],
    *,
    forbidden_terms: Iterable[str] = (),
) -> Path:
    """Write a bounded JSON log and fail closed if forbidden terms would leak."""

    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "__")
    path = log_dir / f"{safe_name}.log"
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for term in forbidden_terms:
        if term and term in text:
            raise ValueError(f"refusing to write forbidden term in log {safe_name}")
    path.write_text(text, encoding="utf-8")
    return path


def model_cache_name(model_id: str) -> str:
    """Return the Hugging Face cache directory name for a model id."""

    return "models--" + model_id.replace("/", "--")


def unique_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    """Deduplicate paths after user expansion while preserving order."""

    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if expanded in seen:
            continue
        seen.add(expanded)
        result.append(expanded)
    return tuple(result)


def huggingface_cache_roots(
    env: Mapping[str, str] | None = None,
    *,
    include_transformers_cache: bool = False,
) -> tuple[Path, ...]:
    """Return candidate Hugging Face cache roots without creating directories."""

    active_env = env or os.environ
    paths: list[Path] = []
    if hub_cache := active_env.get("HUGGINGFACE_HUB_CACHE"):
        paths.append(Path(hub_cache))
    if hf_home := active_env.get("HF_HOME"):
        paths.append(Path(hf_home) / "hub")
    if include_transformers_cache and (transformers_cache := active_env.get("TRANSFORMERS_CACHE")):
        paths.append(Path(transformers_cache))
    paths.append(Path.home() / ".cache/huggingface/hub")
    return unique_paths(paths)


def requirement_package_name(requirement: str) -> str:
    """Extract a distribution name from a PEP 508-ish requirement string."""

    for separator in ("<", ">", "=", "!", "~", ";", "["):
        if separator in requirement:
            return requirement.split(separator, maxsplit=1)[0].strip()
    return requirement.strip()


def import_name_for_requirement(
    requirement: str, package_imports: Mapping[str, str] | None = None
) -> str:
    """Return the Python import name for a requirement."""

    package = requirement_package_name(requirement)
    imports = package_imports or {}
    return imports.get(package, package.replace("-", "_"))


def probe_package_availability(
    requirement: str,
    *,
    package_imports: Mapping[str, str] | None = None,
) -> PackageAvailability:
    """Inspect whether a runtime requirement is importable without importing it."""

    distribution = requirement_package_name(requirement)
    import_name = import_name_for_requirement(requirement, package_imports)
    available = importlib.util.find_spec(import_name) is not None
    version: str | None = None
    if available:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return PackageAvailability(
        requirement=requirement,
        distribution=distribution,
        import_name=import_name,
        status="available" if available else "absent",
        version=version,
    )
