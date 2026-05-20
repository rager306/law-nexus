#!/usr/bin/env python3
"""Deterministic ConsultantPlus source lifecycle helpers.

This module is the no-LLM foundation for the M031 ConsultantPlus WordML
source-structuring CLI. It handles safe manifest loading, content-addressed
references, deterministic JSON/JSONL writes, and bounded XML shape probing.
It does not parse legal semantics, claim parser completeness, or emit raw
legal text in durable outputs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BATCH_SCHEMA_VERSION = "legalgraph-source-batch/v1"
WORDML_2003_NAMESPACE = "http://schemas.microsoft.com/office/word/2003/wordml"
SOURCE_ARTIFACT_SCHEMA_VERSION = "legalgraph-source-artifact/v1"
SOURCE_REVISION_SCHEMA_VERSION = "legalgraph-source-revision/v1"
BATCH_RUN_SCHEMA_VERSION = "legalgraph-source-batch-run/v1"
SOURCE_CLASSIFICATION_SCHEMA_VERSION = "legalgraph-source-classification/v1"
KNOWN_DOCUMENT_ROLES = {"full_normative_act", "relation_list", "inventory_only"}
SIZE_BUCKETS = (
    (10 * 1024, "lt_10kb"),
    (100 * 1024, "lt_100kb"),
    (1024 * 1024, "lt_1mb"),
    (10 * 1024 * 1024, "lt_10mb"),
)
NON_CLAIMS = (
    "source lifecycle output does not claim legal correctness",
    "source lifecycle output does not claim parser completeness",
    "source lifecycle output does not validate R035",
)
MAX_XML_PROBE_BYTES = 16 * 1024 * 1024
TRAJECTORY_SCHEMA_VERSION = "m032.s02.trajectory.v1"
MINIMAX_ATTEMPT_SCHEMA_VERSION = "m032.s03.minimax-attempt.v1"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_MINIMAX_ENDPOINT = "https://api.minimax.io/v1/chat/completions"
DEFAULT_MINIMAX_API_KEY_ENV = "MINIMAX_API_KEY"
CANDIDATE_SCHEMA_VERSION = "m032.s04.graph-context-candidate.v1"
GRAPH_CONTEXT_SIGNAL_SCHEMA_VERSION = "m032.s04.graph-context-signal.v1"
NORMALIZATION_DIAGNOSTIC_SCHEMA_VERSION = "m032.s04.normalization-diagnostic.v1"
CANDIDATE_VERIFIER_DECISION_SCHEMA_VERSION = "m032.s05.candidate-verifier-decision.v1"
CANDIDATE_REVIEW_QUEUE_SCHEMA_VERSION = "m032.s05.candidate-review-queue-item.v1"
CANDIDATE_REJECTION_SCHEMA_VERSION = "m032.s05.candidate-rejection-reason.v1"
EXTERNAL_REVIEW_PACK_SCHEMA_VERSION = "m032.s06.external-review-pack.v1"
GRAPH_CONTEXT_STAGING_SCHEMA_VERSION = "m033.s01.graph-context-staging.v1"
GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION = "m033.s01.graph-context-diagnostic.v1"
GRAPH_CONTEXT_SUMMARY_SCHEMA_VERSION = "m033.s01.graph-context-summary.v1"
KNOWN_CANDIDATE_KINDS = {
    "source_pattern_observation",
    "artifact_candidate",
    "structure_candidate",
    "relationship_candidate",
    "graph_context_signal",
}
GRAPH_CONTEXT_RECORD_KINDS = set(KNOWN_CANDIDATE_KINDS)


class SourceLifecycleError(Exception):
    """Raised for deterministic source lifecycle validation failures."""


@dataclass(frozen=True)
class ManifestArtifact:
    """One artifact declared by a source batch manifest."""

    submitted_name_hash: str
    relative_path: str | None = None
    declared_role_hint: str | None = None
    declared_identity_hint: dict[str, Any] | None = None


@dataclass(frozen=True)
class BatchManifest:
    """Validated no-raw-text batch manifest."""

    path: Path
    batch_dir: Path
    incoming_dir: Path
    batch_id: str
    source_family_hint: str | None
    artifacts: tuple[ManifestArtifact, ...]
    raw_payload: dict[str, Any]


def stable_json(data: Any) -> str:
    """Return deterministic UTF-8 JSON text with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, data: Any) -> None:
    """Atomically write deterministic JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(stable_json(data), encoding="utf-8")
    tmp_path.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically write deterministic JSONL rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_path.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL object rows, returning an empty list for missing files."""

    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SourceLifecycleError(f"malformed JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise SourceLifecycleError(f"JSONL row at {path}:{line_no} must be an object")
            rows.append(row)
    return rows


def upsert_jsonl(path: Path, key: str, new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Upsert rows by a stable key and rewrite deterministic JSONL."""

    by_key: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        value = row.get(key)
        if isinstance(value, str):
            by_key[value] = row
    for row in new_rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise SourceLifecycleError(f"upsert row missing stable key {key!r}")
        by_key[value] = row
    rows = [by_key[value] for value in sorted(by_key)]
    write_jsonl(path, rows)
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append deterministic JSONL rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    """Return a file SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_ref(sha256: str) -> str:
    """Return the logical raw-store ref for a SHA-256 XML artifact."""

    return f"law-source/consultant/raw/sha256/{sha256[:2]}/{sha256[2:4]}/{sha256}.xml"


def source_artifact_id(sha256: str) -> str:
    """Return a stable source artifact id."""

    return f"SA-CONSULTANT-{sha256[:12]}"


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SourceLifecycleError(f"missing batch manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SourceLifecycleError(f"malformed batch manifest JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceLifecycleError("batch manifest must be a JSON object")
    return payload


def load_batch_manifest(path: Path) -> BatchManifest:
    """Load and validate a source batch manifest.

    Artifact paths are optional for S02 compatibility, but if present they must
    stay inside the batch incoming directory and may not be absolute paths,
    symlinks, directories, or parent-directory escapes.
    """

    manifest_path = path.resolve()
    payload = _load_json_object(manifest_path)
    schema_version = payload.get("schema_version")
    if schema_version != BATCH_SCHEMA_VERSION:
        raise SourceLifecycleError(
            f"unsupported batch manifest schema_version: {schema_version!r}"
        )
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise SourceLifecycleError("batch manifest requires a non-empty batch_id")
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise SourceLifecycleError("batch manifest requires an artifacts array")

    batch_dir = manifest_path.parent
    incoming_dir = (batch_dir / "incoming").resolve()
    artifacts: list[ManifestArtifact] = []
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, dict):
            raise SourceLifecycleError(f"artifact[{index}] must be an object")
        submitted_name_hash = raw_artifact.get("submitted_name_hash")
        if not isinstance(submitted_name_hash, str) or not submitted_name_hash.startswith(
            "sha256:"
        ):
            raise SourceLifecycleError(
                f"artifact[{index}] requires submitted_name_hash='sha256:<hash>'"
            )
        relative_path = raw_artifact.get("relative_path")
        if relative_path is not None:
            if not isinstance(relative_path, str) or not relative_path.strip():
                raise SourceLifecycleError(f"artifact[{index}].relative_path must be a string")
            resolve_incoming_artifact(incoming_dir, relative_path)
        declared_identity_hint = raw_artifact.get("declared_identity_hint")
        if declared_identity_hint is not None and not isinstance(declared_identity_hint, dict):
            raise SourceLifecycleError(
                f"artifact[{index}].declared_identity_hint must be an object"
            )
        declared_role_hint = raw_artifact.get("declared_role_hint")
        if declared_role_hint is not None and not isinstance(declared_role_hint, str):
            raise SourceLifecycleError(f"artifact[{index}].declared_role_hint must be a string")
        artifacts.append(
            ManifestArtifact(
                submitted_name_hash=submitted_name_hash,
                relative_path=relative_path,
                declared_role_hint=declared_role_hint,
                declared_identity_hint=declared_identity_hint,
            )
        )

    source_family_hint = payload.get("source_family_hint")
    if source_family_hint is not None and not isinstance(source_family_hint, str):
        raise SourceLifecycleError("source_family_hint must be a string when present")
    return BatchManifest(
        path=manifest_path,
        batch_dir=batch_dir,
        incoming_dir=incoming_dir,
        batch_id=batch_id,
        source_family_hint=source_family_hint,
        artifacts=tuple(artifacts),
        raw_payload=payload,
    )


def resolve_incoming_artifact(incoming_dir: Path, relative_path: str) -> Path:
    """Resolve a manifest artifact path and reject traversal/symlink escapes."""

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise SourceLifecycleError("manifest artifact paths must be relative")
    if any(part == ".." for part in candidate.parts):
        raise SourceLifecycleError("manifest artifact paths may not contain '..'")
    resolved_incoming = incoming_dir.resolve()
    unresolved = resolved_incoming / candidate
    if unresolved.is_symlink():
        raise SourceLifecycleError("manifest artifact path may not be a symlink")
    resolved = unresolved.resolve()
    if not resolved.is_relative_to(resolved_incoming):
        raise SourceLifecycleError("manifest artifact path escapes incoming directory")
    if not resolved.is_file():
        raise SourceLifecycleError("manifest artifact path must point to a file")
    if resolved.suffix.lower() != ".xml":
        raise SourceLifecycleError("S03 source lifecycle only accepts .xml artifacts")
    return resolved


def raw_store_path(workspace_root: Path, sha256: str) -> Path:
    """Return the filesystem path for a content-addressed raw XML artifact."""

    return workspace_root / "raw" / "sha256" / sha256[:2] / sha256[2:4] / f"{sha256}.xml"


def copy_to_raw_store(source_path: Path, workspace_root: Path) -> tuple[str, Path]:
    """Copy a file into the SHA-addressed raw store and return digest/path."""

    digest = sha256_file(source_path)
    destination = raw_store_path(workspace_root, digest)
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
    return digest, destination


def split_xml_name(tag: str | None) -> dict[str, str | None]:
    """Split an ElementTree tag into namespace/local-name fields."""

    if not tag:
        return {"root_namespace": None, "root_local_name": None}
    if tag.startswith("{") and "}" in tag:
        namespace, local_name = tag[1:].split("}", 1)
        return {"root_namespace": namespace, "root_local_name": local_name}
    return {"root_namespace": None, "root_local_name": tag}


def probe_xml_shape(path: Path, *, max_bytes: int = MAX_XML_PROBE_BYTES) -> dict[str, Any]:
    """Probe XML shape without returning raw text or element content."""

    size_bytes = path.stat().st_size if path.is_file() else None
    if size_bytes is None:
        return _xml_error_shape("missing_file", "artifact does not exist", size_bytes)
    if size_bytes > max_bytes:
        return _xml_error_shape("xml_probe_size_limit", "artifact exceeds probe byte limit", size_bytes)
    prefix = path.read_bytes()[:4096].lower()
    if b"<!doctype" in prefix or b"<!entity" in prefix:
        return _xml_error_shape("xml_unsafe_doctype", "XML doctype/entity declarations are not allowed", size_bytes)
    parser = ET.XMLParser()
    try:
        root = ET.parse(path, parser=parser).getroot()
    except ET.ParseError as exc:
        return _xml_error_shape("malformed_xml", str(exc), size_bytes)
    name = split_xml_name(root.tag)
    namespace = name["root_namespace"]
    local_name = name["root_local_name"]
    return {
        "container": "plain_xml",
        "well_formed": True,
        "root_namespace": namespace,
        "root_local_name": local_name,
        "direct_child_count": len(list(root)),
        "source_family": "consultant_wordml"
        if namespace == WORDML_2003_NAMESPACE and local_name == "wordDocument"
        else "unknown_xml",
        "non_authoritative": True,
    }


def _xml_error_shape(kind: str, message: str, size_bytes: int | None) -> dict[str, Any]:
    return {
        "container": "plain_xml",
        "well_formed": False,
        "error_kind": kind,
        "error_message": message[:220],
        "size_bytes": size_bytes,
        "root_namespace": None,
        "root_local_name": None,
        "direct_child_count": None,
        "source_family": "unknown_xml",
        "non_authoritative": True,
    }


def artifact_row(source_path: Path, workspace_root: Path) -> dict[str, Any]:
    """Build a safe source_artifacts.jsonl row for a local XML artifact."""

    digest, _destination = copy_to_raw_store(source_path, workspace_root)
    shape = probe_xml_shape(source_path)
    return {
        "schema_version": SOURCE_ARTIFACT_SCHEMA_VERSION,
        "source_artifact_id": source_artifact_id(digest),
        "source_family": shape["source_family"],
        "raw_sha256": digest,
        "raw_size_bytes": source_path.stat().st_size,
        "media_type": "application/xml",
        "raw_storage_ref": sha256_ref(digest),
        "detected_shape": shape,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def _role_from_hint(hint: str | None, source_family: str) -> str:
    if source_family != "consultant_wordml":
        return "unsupported_source"
    if hint in KNOWN_DOCUMENT_ROLES:
        return hint
    return "inventory_only"


def _parser_route(document_role: str, source_family: str) -> str:
    if source_family != "consultant_wordml":
        return "unsupported_xml"
    if document_role == "full_normative_act":
        return "full_act"
    if document_role == "relation_list":
        return "relation_list"
    return "inventory_only"


def _identity_key(identity_hint: dict[str, Any] | None) -> dict[str, Any]:
    if not identity_hint:
        return {"jurisdiction": "unknown", "act_type": "unknown", "act_number": "unknown"}
    return {
        "jurisdiction": str(identity_hint.get("jurisdiction") or "unknown"),
        "act_type": str(identity_hint.get("act_type") or "unknown"),
        "act_number": str(identity_hint.get("act_number") or "unknown"),
    }


def _identity_slug(identity_key: dict[str, Any]) -> str:
    digest = hashlib.sha256(stable_json(identity_key).encode("utf-8")).hexdigest()
    return digest[:12]


def revision_row(artifact: ManifestArtifact, artifact_payload: dict[str, Any]) -> dict[str, Any]:
    """Build a safe source_revisions.jsonl row for a manifest artifact."""

    identity_key = _identity_key(artifact.declared_identity_hint)
    digest = str(artifact_payload["raw_sha256"])
    edition_label = None
    if artifact.declared_identity_hint:
        edition_label = artifact.declared_identity_hint.get("edition_label")
    return {
        "schema_version": SOURCE_REVISION_SCHEMA_VERSION,
        "source_revision_id": f"SR-CONSULTANT-{_identity_slug(identity_key)}-{digest[:12]}",
        "source_artifact_id": artifact_payload["source_artifact_id"],
        "source_family": artifact_payload["source_family"],
        "legal_document_key": identity_key,
        "edition": {
            "edition_date": None,
            "edition_label": edition_label,
            "detected_from": "manifest_hint" if artifact.declared_identity_hint else "not_detected",
            "confidence": "bounded",
        },
        "status": "registered",
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def classification_row(artifact: ManifestArtifact, artifact_payload: dict[str, Any]) -> dict[str, Any]:
    """Build a safe source_classification.safe.jsonl row."""

    source_family = str(artifact_payload["source_family"])
    document_role = _role_from_hint(artifact.declared_role_hint, source_family)
    parser_route = _parser_route(document_role, source_family)
    return {
        "schema_version": SOURCE_CLASSIFICATION_SCHEMA_VERSION,
        "source_artifact_id": artifact_payload["source_artifact_id"],
        "source_family": source_family,
        "document_role": document_role,
        "parser_route": parser_route,
        "route_confidence": "bounded" if source_family == "consultant_wordml" else "needs_review",
        "detected_shape": artifact_payload["detected_shape"],
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def _manifest_artifact_path(manifest: BatchManifest, artifact: ManifestArtifact) -> Path:
    if artifact.relative_path is None:
        raise SourceLifecycleError("register/classify requires artifact.relative_path")
    return resolve_incoming_artifact(manifest.incoming_dir, artifact.relative_path)


def register_batch(manifest_path: Path, workspace_root: Path) -> dict[str, Any]:
    """Register manifest artifacts into safe lifecycle registry files."""

    manifest = load_batch_manifest(manifest_path)
    registry_dir = workspace_root / "registry"
    artifact_rows: list[dict[str, Any]] = []
    revision_rows: list[dict[str, Any]] = []
    seen_digests: set[str] = set()
    duplicate_count = 0
    for artifact in manifest.artifacts:
        source_path = _manifest_artifact_path(manifest, artifact)
        row = artifact_row(source_path, workspace_root)
        if row["raw_sha256"] in seen_digests:
            duplicate_count += 1
        seen_digests.add(str(row["raw_sha256"]))
        artifact_rows.append(row)
        revision_rows.append(revision_row(artifact, row))

    all_artifacts = upsert_jsonl(
        registry_dir / "source_artifacts.jsonl", "source_artifact_id", artifact_rows
    )
    all_revisions = upsert_jsonl(
        registry_dir / "source_revisions.jsonl", "source_revision_id", revision_rows
    )
    batch_row = {
        "schema_version": BATCH_RUN_SCHEMA_VERSION,
        "batch_id": manifest.batch_id,
        "source_family_hint": manifest.source_family_hint,
        "registered_count": len(artifact_rows),
        "duplicate_count": duplicate_count,
        "failed_count": 0,
        "status": "registered",
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }
    all_batches = upsert_jsonl(registry_dir / "batches.jsonl", "batch_id", [batch_row])
    return {
        "status": "registered",
        "batch_id": manifest.batch_id,
        "registered_count": len(artifact_rows),
        "duplicate_count": duplicate_count,
        "registry_counts": {
            "source_artifacts": len(all_artifacts),
            "source_revisions": len(all_revisions),
            "batches": len(all_batches),
        },
        "non_authoritative": True,
    }


def classify_batch(manifest_path: Path, workspace_root: Path) -> dict[str, Any]:
    """Classify manifest artifacts and write safe classification rows."""

    manifest = load_batch_manifest(manifest_path)
    registry_dir = workspace_root / "registry"
    rows: list[dict[str, Any]] = []
    route_counts: dict[str, int] = {}
    for artifact in manifest.artifacts:
        source_path = _manifest_artifact_path(manifest, artifact)
        row = artifact_row(source_path, workspace_root)
        classified = classification_row(artifact, row)
        rows.append(classified)
        route = str(classified["parser_route"])
        route_counts[route] = route_counts.get(route, 0) + 1
    all_rows = upsert_jsonl(
        registry_dir / "source_classification.safe.jsonl", "source_artifact_id", rows
    )
    return {
        "status": "classified",
        "batch_id": manifest.batch_id,
        "classified_count": len(rows),
        "route_counts": route_counts,
        "registry_counts": {"source_classification": len(all_rows)},
        "non_authoritative": True,
    }


def corpus_id_for_batch(batch_id: str) -> str:
    """Return a safe corpus id derived from batch_id without exposing names."""

    digest = hashlib.sha256(batch_id.encode("utf-8")).hexdigest()
    return f"CORPUS-{digest[:12]}"


def size_bucket(size_bytes: int) -> str:
    """Return a coarse safe size bucket."""

    for threshold, label in SIZE_BUCKETS:
        if size_bytes < threshold:
            return label
    return "gte_10mb"


def safe_selector(shape: dict[str, Any]) -> str:
    """Return a structural selector without text content."""

    namespace = shape.get("root_namespace") or "none"
    local_name = shape.get("root_local_name") or "unknown"
    namespace_hash = hashlib.sha256(str(namespace).encode("utf-8")).hexdigest()[:12]
    return f"root:{local_name}:namespace_sha256:{namespace_hash}"


def xml_inventory_metrics(path: Path) -> dict[str, Any]:
    """Collect safe XML structure counts without preserving text."""

    namespace_counts: dict[str, int] = {}
    element_count = 0
    max_depth = 0
    stack: list[str] = []
    try:
        for event, elem in ET.iterparse(path, events=("start", "end")):
            if event == "start":
                element_count += 1
                stack.append(elem.tag)
                max_depth = max(max_depth, len(stack))
                namespace = split_xml_name(elem.tag)["root_namespace"] or "none"
                namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1
            else:
                if stack:
                    stack.pop()
                elem.clear()
    except ET.ParseError as exc:
        return {
            "well_formed": False,
            "error_kind": "malformed_xml",
            "error_message": str(exc)[:220],
            "element_count": 0,
            "max_depth": 0,
            "namespace_counts": {},
        }
    return {
        "well_formed": True,
        "element_count": element_count,
        "max_depth": max_depth,
        "namespace_counts": dict(sorted(namespace_counts.items())),
    }


def inventory_row(artifact: ManifestArtifact, artifact_payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    """Build a safe inventory-only processed row."""

    shape = artifact_payload["detected_shape"]
    metrics = xml_inventory_metrics(source_path) if shape.get("well_formed") else {
        "well_formed": False,
        "error_kind": shape.get("error_kind"),
        "element_count": 0,
        "max_depth": 0,
        "namespace_counts": {},
    }
    return {
        "schema_version": "legalgraph-source-inventory/v1",
        "source_artifact_id": artifact_payload["source_artifact_id"],
        "source_family": artifact_payload["source_family"],
        "document_role": _role_from_hint(artifact.declared_role_hint, str(artifact_payload["source_family"])),
        "raw_sha256": artifact_payload["raw_sha256"],
        "raw_size_bucket": size_bucket(int(artifact_payload["raw_size_bytes"])),
        "selector": safe_selector(shape),
        "shape": shape,
        "metrics": metrics,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def process_batch(manifest_path: Path, workspace_root: Path) -> dict[str, Any]:
    """Emit safe inventory-only processed outputs for a batch."""

    manifest = load_batch_manifest(manifest_path)
    corpus_id = corpus_id_for_batch(manifest.batch_id)
    output_dir = workspace_root / "processed" / "consultant-wordml-v1" / corpus_id
    inventory_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    source_families: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}
    malformed_count = 0
    for artifact in manifest.artifacts:
        source_path = _manifest_artifact_path(manifest, artifact)
        row = artifact_row(source_path, workspace_root)
        inventory = inventory_row(artifact, row, source_path)
        inventory_rows.append(inventory)
        family = str(inventory["source_family"])
        role = str(inventory["document_role"])
        bucket = str(inventory["raw_size_bucket"])
        source_families[family] = source_families.get(family, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1
        size_counts[bucket] = size_counts.get(bucket, 0) + 1
        diagnostic = {
            "schema_version": "legalgraph-source-diagnostic/v1",
            "source_artifact_id": row["source_artifact_id"],
            "well_formed": inventory["metrics"]["well_formed"],
            "error_kind": inventory["metrics"].get("error_kind"),
            "parser_route": _parser_route(role, family),
            "non_authoritative": True,
            "non_claims": list(NON_CLAIMS),
        }
        if not diagnostic["well_formed"]:
            malformed_count += 1
        diagnostic_rows.append(diagnostic)
    metrics = {
        "schema_version": "legalgraph-source-inventory-metrics/v1",
        "batch_id_hash": hashlib.sha256(manifest.batch_id.encode("utf-8")).hexdigest(),
        "corpus_id": corpus_id,
        "artifact_count": len(inventory_rows),
        "malformed_count": malformed_count,
        "source_family_counts": dict(sorted(source_families.items())),
        "document_role_counts": dict(sorted(role_counts.items())),
        "raw_size_bucket_counts": dict(sorted(size_counts.items())),
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }
    write_jsonl(output_dir / "source_inventory.safe.jsonl", inventory_rows)
    write_jsonl(output_dir / "diagnostics.safe.jsonl", diagnostic_rows)
    write_json(output_dir / "metrics.safe.json", metrics)
    return {
        "status": "processed",
        "batch_id": manifest.batch_id,
        "corpus_id": corpus_id,
        "processed_count": len(inventory_rows),
        "malformed_count": malformed_count,
        "output_dir": str(output_dir.relative_to(workspace_root)),
        "non_authoritative": True,
    }


def _count_jsonl(path: Path) -> int:
    return len(read_jsonl(path)) if path.exists() else 0


def lifecycle_status(workspace_root: Path) -> dict[str, Any]:
    """Summarize registry and processed lifecycle state."""

    registry_dir = workspace_root / "registry"
    processed_root = workspace_root / "processed" / "consultant-wordml-v1"
    runs_root = workspace_root / "runs"
    registry_counts = {
        "source_artifacts": _count_jsonl(registry_dir / "source_artifacts.jsonl"),
        "source_revisions": _count_jsonl(registry_dir / "source_revisions.jsonl"),
        "batches": _count_jsonl(registry_dir / "batches.jsonl"),
        "source_classification": _count_jsonl(registry_dir / "source_classification.safe.jsonl"),
    }
    batches = read_jsonl(registry_dir / "batches.jsonl") if (registry_dir / "batches.jsonl").exists() else []
    latest_batch_id_hash = None
    if batches:
        latest_batch_id = str(batches[-1].get("batch_id") or "")
        latest_batch_id_hash = hashlib.sha256(latest_batch_id.encode("utf-8")).hexdigest()
    processed_corpora = sorted(
        path.name for path in processed_root.iterdir() if path.is_dir()
    ) if processed_root.exists() else []
    run_ids = sorted(path.name for path in runs_root.iterdir() if path.is_dir()) if runs_root.exists() else []
    latest_run_id = run_ids[-1] if run_ids else None
    latest_run_status = None
    if latest_run_id is not None:
        run_json = runs_root / latest_run_id / "run.json"
        if run_json.exists():
            latest_run = _load_json_object(run_json)
            latest_run_status = latest_run.get("status")
    return {
        "status": "ok",
        "registry_counts": registry_counts,
        "processed_corpus_count": len(processed_corpora),
        "processed_corpora": processed_corpora,
        "run_count": len(run_ids),
        "latest_run_id": latest_run_id,
        "latest_run_status": latest_run_status,
        "latest_batch_id_hash": latest_batch_id_hash,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def utc_now_iso() -> str:
    """Return a compact UTC timestamp for run envelopes."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_run_id(batch_id: str, started_at: str | None = None) -> str:
    """Return a safe run id derived from batch id and timestamp."""

    timestamp = started_at or utc_now_iso()
    digest = hashlib.sha256(f"{batch_id}\n{timestamp}".encode("utf-8")).hexdigest()
    return f"RUN-{digest[:12]}"


def run_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run directory for a safe run id."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runs" / run_id


def stable_discovery_id(prefix: str, *parts: str) -> str:
    """Return a stable discovery identifier for trajectory artifacts."""

    if not prefix.isupper() or not re_match_safe_id(prefix):
        raise SourceLifecycleError("discovery id prefix must be uppercase and path-safe")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12]}"


def trajectory_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped trajectory directory for a discovery run."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "trajectory" / run_id


def minimax_attempt_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped MiniMax attempt summary directory."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "minimax-attempts" / run_id


def trajectory_record(
    *,
    run_id: str,
    event_type: str,
    phase: str,
    step_id: str,
    summary: str,
    observed_context: str,
    decision: str,
    decision_reason: str,
    next_action: str,
    parent_step_id: str | None = None,
    source_refs: list[str] | None = None,
    input_refs: list[str] | None = None,
    output_refs: list[str] | None = None,
    record_id: str | None = None,
    timestamp_utc: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an S02-compatible trajectory record."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    if not step_id.startswith("STEP-") or not re_match_safe_id(step_id):
        raise SourceLifecycleError("step_id must be a safe STEP- identifier")
    if parent_step_id is not None and (
        not parent_step_id.startswith("STEP-") or not re_match_safe_id(parent_step_id)
    ):
        raise SourceLifecycleError("parent_step_id must be a safe STEP- identifier")
    selected_record_id = record_id or stable_discovery_id("REC", run_id, step_id, event_type, summary)
    if not selected_record_id.startswith("REC-") or not re_match_safe_id(selected_record_id):
        raise SourceLifecycleError("record_id must be a safe REC- identifier")
    row: dict[str, Any] = {
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
        "run_id": run_id,
        "record_id": selected_record_id,
        "event_type": event_type,
        "phase": phase,
        "step_id": step_id,
        "parent_step_id": parent_step_id,
        "timestamp_utc": timestamp_utc or utc_now_iso(),
        "source_refs": sorted(source_refs or []),
        "input_refs": sorted(input_refs or []),
        "output_refs": sorted(output_refs or []),
        "summary": summary,
        "observed_context": observed_context,
        "decision": decision,
        "decision_reason": decision_reason,
        "next_action": next_action,
        "non_authoritative": True,
    }
    if extra:
        row.update({key: value for key, value in sorted(extra.items()) if value is not None})
    return row


def append_trajectory_record(
    workspace_root: Path,
    run_id: str,
    record: dict[str, Any],
    *,
    file_name: str = "trajectory.jsonl",
) -> Path:
    """Append one trajectory record and return the written file path."""

    if file_name not in {
        "trajectory.jsonl",
        "discovery_steps.jsonl",
        "filtering_decisions.jsonl",
        "rejected_branches.jsonl",
    }:
        raise SourceLifecycleError("unsupported trajectory JSONL file")
    path = trajectory_directory(workspace_root, run_id) / file_name
    append_jsonl(path, [record])
    return path


def write_minimax_attempt_summary(
    workspace_root: Path,
    run_id: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Write a normalized MiniMax attempt summary and return output refs."""

    attempt_id = summary.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id.startswith("ATTEMPT-") or not re_match_safe_id(attempt_id):
        raise SourceLifecycleError("attempt summary requires a safe ATTEMPT- attempt_id")
    allowed = {
        "attempt_id",
        "source_step_id",
        "source_refs",
        "prompt_summary",
        "response_summary",
        "candidate_refs",
        "trajectory_refs",
        "model_name",
        "status",
        "decision_reason",
    }
    row = {key: summary[key] for key in sorted(summary) if key in allowed and summary[key] is not None}
    row.update({"schema_version": MINIMAX_ATTEMPT_SCHEMA_VERSION, "non_authoritative": True})
    path = minimax_attempt_directory(workspace_root, run_id) / "attempts.jsonl"
    append_jsonl(path, [row])
    return {
        "schema_version": "m032.s03.minimax-attempt-write/v1",
        "status": "attempt_summary_written",
        "attempt_id": attempt_id,
        "attempt_ref": safe_output_ref(path, workspace_root),
        "non_authoritative": True,
    }


def discovery_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped discovery candidate directory."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "discovery" / run_id


def normalize_candidate_kind(value: Any) -> tuple[str, list[str]]:
    """Normalize a model-suggested candidate kind into the closed S04 vocabulary."""

    if isinstance(value, str) and value in KNOWN_CANDIDATE_KINDS:
        return value, []
    if isinstance(value, str) and value.strip():
        return "graph_context_signal", [f"unsupported_candidate_kind:{value[:80]}"]
    return "graph_context_signal", ["missing_candidate_kind"]


def _candidate_entries(response_summary: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract candidate-like entries and diagnostics from a response summary."""

    stripped = response_summary.strip()
    if not stripped:
        return [], [{"error_kind": "empty_discovery_output", "status": "rejected", "message": "Discovery response was empty."}]
    if stripped[0] in "[{":
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return [], [
                {
                    "error_kind": "malformed_candidate_payload",
                    "status": "rejected",
                    "message": "Discovery response looked like JSON but could not be parsed.",
                }
            ]
        if isinstance(payload, list):
            entries = payload
        elif isinstance(payload, dict):
            raw_entries = payload.get("candidates", payload.get("graph_context_signals"))
            entries = raw_entries if isinstance(raw_entries, list) else []
        else:
            entries = []
        dict_entries = [entry for entry in entries if isinstance(entry, dict)]
        if not dict_entries:
            return [], [
                {
                    "error_kind": "malformed_candidate_payload",
                    "status": "needs_review",
                    "message": "Structured discovery response contained no candidate objects.",
                }
            ]
        return dict_entries, []
    return [
        {
            "candidate_kind": "graph_context_signal",
            "candidate_summary": stripped[:500],
            "supporting_context": stripped[:1000],
            "confidence_bucket": "unknown",
        }
    ], []


def normalize_discovery_candidates(
    workspace_root: Path,
    *,
    run_id: str,
    attempt_id: str,
    response_summary: str,
    source_refs: list[str] | None = None,
    trajectory_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize MiniMax discovery output into proposed graph-context candidates."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    if not attempt_id.startswith("ATTEMPT-") or not re_match_safe_id(attempt_id):
        raise SourceLifecycleError("attempt_id must be a safe ATTEMPT- identifier")
    refs = sorted(source_refs or [])
    trajectory = sorted(trajectory_refs or [])
    entries, diagnostics = _candidate_entries(response_summary)
    candidate_rows: list[dict[str, Any]] = []
    signal_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    for index, diagnostic in enumerate(diagnostics):
        diagnostic_rows.append(
            {
                "schema_version": NORMALIZATION_DIAGNOSTIC_SCHEMA_VERSION,
                "diagnostic_id": stable_discovery_id("DIAG", run_id, attempt_id, str(index), diagnostic["error_kind"]),
                "run_id": run_id,
                "attempt_id": attempt_id,
                "status": diagnostic["status"],
                "error_kind": diagnostic["error_kind"],
                "message": diagnostic["message"],
                "source_refs": refs,
                "trajectory_refs": trajectory,
                "non_authoritative": True,
            }
        )
    for index, entry in enumerate(entries):
        kind, warnings = normalize_candidate_kind(entry.get("candidate_kind", entry.get("kind")))
        status_value = entry.get("lifecycle_status", entry.get("status"))
        ignored_claims: list[str] = []
        if isinstance(status_value, str) and status_value in {"accepted", "verified", "validated", "production_ready"}:
            ignored_claims.append(f"model_claimed_status:{status_value}")
        summary = entry.get("candidate_summary", entry.get("summary", entry.get("title")))
        if not isinstance(summary, str) or not summary.strip():
            summary = "Discovery output proposed a graph-context signal requiring review."
            warnings.append("missing_candidate_summary")
        supporting_context = entry.get("supporting_context", entry.get("context", entry.get("evidence")))
        if not isinstance(supporting_context, str) or not supporting_context.strip():
            supporting_context = response_summary[:1000]
        confidence = entry.get("confidence_bucket", "unknown")
        if confidence not in {"low", "medium", "high", "unknown"}:
            confidence = "unknown"
            warnings.append("unsupported_confidence_bucket")
        candidate_id = stable_discovery_id("CAND", run_id, attempt_id, kind, str(index), summary)
        candidate = {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "candidate_kind": kind,
            "lifecycle_status": "proposed",
            "source_refs": refs,
            "trajectory_refs": trajectory,
            "attempt_refs": [f"attempt:{attempt_id}"],
            "candidate_summary": summary[:700],
            "supporting_context": supporting_context[:1200],
            "confidence_bucket": confidence,
            "normalization_warnings": sorted(set(warnings)),
            "model_claims_ignored": sorted(set(ignored_claims)),
            "non_authoritative": True,
            "non_claims": [
                "Candidate is proposed only.",
                "No deterministic verifier acceptance.",
                "No legal correctness claim.",
                "No parser completeness claim.",
                "No R035 validation.",
                "No R038 validation.",
            ],
        }
        candidate_rows.append(candidate)
        signal_rows.append(
            {
                "schema_version": GRAPH_CONTEXT_SIGNAL_SCHEMA_VERSION,
                "signal_id": stable_discovery_id("SIGNAL", candidate_id, kind),
                "candidate_id": candidate_id,
                "run_id": run_id,
                "signal_type": kind,
                "signal_summary": candidate["candidate_summary"],
                "source_refs": refs,
                "trajectory_refs": trajectory,
                "lifecycle_status": "proposed",
                "non_authoritative": True,
            }
        )
    directory = discovery_directory(workspace_root, run_id)
    output_paths: list[Path] = []
    if candidate_rows:
        path = directory / "candidate_hypotheses.jsonl"
        write_jsonl(path, candidate_rows)
        output_paths.append(path)
    if signal_rows:
        path = directory / "graph_context_signals.jsonl"
        write_jsonl(path, signal_rows)
        output_paths.append(path)
    if diagnostic_rows:
        path = directory / "normalization_diagnostics.jsonl"
        write_jsonl(path, diagnostic_rows)
        output_paths.append(path)
    return {
        "schema_version": "m032.s04.candidate-normalization-result/v1",
        "status": "normalized" if candidate_rows else "needs_review",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_count": len(candidate_rows),
        "signal_count": len(signal_rows),
        "diagnostic_count": len(diagnostic_rows),
        "output_refs": output_summary(output_paths, workspace_root)["output_refs"] if output_paths else [],
        "candidate_refs": [f"candidate:{row['candidate_id']}" for row in candidate_rows],
        "non_authoritative": True,
    }


def verifier_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped verifier output directory."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "verifier" / run_id


def _safe_verifier_refs(refs: list[str]) -> list[str]:
    """Return refs compatible with the legacy deterministic verifier."""

    allowed_prefixes = (
        "processed/consultant-wordml-v1/",
        "runs/",
        "registry/",
        "metrics.safe.json",
        "diagnostics.safe.jsonl",
        "review_pack.json",
    )
    safe: list[str] = []
    for ref in refs:
        if isinstance(ref, str) and not ref.startswith("/") and ".." not in Path(ref).parts:
            if ref.startswith(allowed_prefixes):
                safe.append(ref)
    return sorted(set(safe))


def _verifier_hypothesis_kind(candidate_kind: str) -> str | None:
    mapping = {
        "source_pattern_observation": "structural_marker_rule",
        "artifact_candidate": "diagnostic_bucket_hint",
        "structure_candidate": "safe_section_boundary_hint",
        "relationship_candidate": "structural_marker_rule",
        "graph_context_signal": "diagnostic_bucket_hint",
    }
    return mapping.get(candidate_kind)


def _graph_context_signal_support_reasons(candidate: dict[str, Any]) -> list[str]:
    """Return evidence-shape reasons for weak graph-context signal candidates."""

    if candidate.get("candidate_kind") != "graph_context_signal":
        return []
    reasons: list[str] = []
    confidence = candidate.get("confidence_bucket")
    supporting_context = str(candidate.get("supporting_context") or "").strip()
    candidate_summary = str(candidate.get("candidate_summary") or "").strip()
    if confidence == "low":
        reasons.append("graph-context-signal-weak-evidence-shape")
        if len(supporting_context) < 40:
            reasons.append("graph-context-signal-inherited-refs-only")
    if len(candidate_summary) < 20:
        reasons.append("graph-context-signal-needs-review")
    return sorted(set(reasons))


def candidate_to_verifier_proposal(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Adapt one S04 candidate into the legacy verifier proposal contract."""

    reasons: list[str] = []
    if candidate.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        reasons.append("candidate_schema_violation")
    if candidate.get("lifecycle_status") != "proposed":
        reasons.append("candidate_not_proposed")
    if candidate.get("non_authoritative") is not True:
        reasons.append("candidate_not_non_authoritative")
    candidate_id = candidate.get("candidate_id")
    attempt_id = candidate.get("attempt_id")
    run_id = candidate.get("run_id")
    candidate_kind = candidate.get("candidate_kind")
    if not isinstance(candidate_id, str) or not candidate_id.startswith("CAND-") or not re_match_safe_id(candidate_id):
        reasons.append("candidate_id_invalid")
    if not isinstance(attempt_id, str) or not attempt_id.startswith("ATTEMPT-") or not re_match_safe_id(attempt_id):
        reasons.append("attempt_id_invalid")
    if not isinstance(run_id, str) or not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        reasons.append("run_id_invalid")
    if not isinstance(candidate_kind, str):
        reasons.append("candidate_kind_invalid")
        verifier_kind = None
    else:
        verifier_kind = _verifier_hypothesis_kind(candidate_kind)
        if verifier_kind is None:
            reasons.append("candidate_kind_unsupported")
    source_refs = candidate.get("source_refs")
    if not isinstance(source_refs, list):
        source_refs = []
        reasons.append("source_refs_missing")
    reasons.extend(_graph_context_signal_support_reasons(candidate))
    safe_refs = _safe_verifier_refs(source_refs)
    ambiguous_graph_signal = (
        candidate_kind == "graph_context_signal"
        and not reasons
        and len(str(candidate.get("supporting_context") or "").strip()) < 40
    )
    confidence = candidate.get("confidence_bucket")
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    if reasons or verifier_kind is None or not isinstance(candidate_id, str) or not isinstance(attempt_id, str) or not isinstance(run_id, str):
        return None, sorted(set(reasons))
    summary = str(candidate.get("candidate_summary") or candidate_id)[:120]
    proposal = {
        "schema_version": "legalgraph-structural-hypothesis-proposal/v1",
        "proposal_id": stable_discovery_id("SHP", candidate_id, run_id),
        "worker_attempt_id": stable_discovery_id("WA", attempt_id, run_id),
        "source_artifact_id": stable_discovery_id("SA-CONSULTANT", candidate_id, "artifact"),
        "source_revision_id": stable_discovery_id("SR-CONSULTANT", candidate_id, "revision"),
        "run_id": run_id,
        "output_refs": safe_refs or ["registry/source_artifacts.jsonl"],
        "source_family": "consultant_wordml",
        "document_role": "inventory_only",
        "parser_route": "inventory_only",
        "hypothesis_kind": verifier_kind,
        "hypothesis_payload": {
            "selector": f"candidate:{candidate_id}",
            "safe_rule_id": stable_discovery_id("RULE", candidate_id, summary),
            "confidence_bucket": confidence,
            "evidence_refs": [] if ambiguous_graph_signal else safe_refs,
        },
        "verifier_status": "pending",
        "non_authoritative": True,
        "non_claims": [
            "proposal is a structural hypothesis only",
            "proposal does not claim legal correctness",
            "proposal does not claim parser completeness",
            "proposal does not validate R035",
        ],
    }
    return proposal, []


def _graph_context_diagnostic(
    *,
    run_id: str,
    candidate_id: str | None,
    decision_id: str | None,
    reason_codes: list[str],
    safe_summary: str = "candidate was not staged",
) -> dict[str, Any]:
    """Return a safe graph-context staging diagnostic row."""

    safe_candidate_id = candidate_id if isinstance(candidate_id, str) and re_match_safe_id(candidate_id) else "unknown-candidate"
    safe_decision_id = decision_id if isinstance(decision_id, str) and re_match_safe_id(decision_id) else "unknown-decision"
    return {
        "schema_version": GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION,
        "diagnostic_id": stable_discovery_id("GCTXDIAG", run_id, safe_candidate_id, safe_decision_id, *sorted(set(reason_codes))),
        "run_id": run_id,
        "candidate_id": candidate_id if isinstance(candidate_id, str) and re_match_safe_id(candidate_id) else None,
        "decision_id": decision_id if isinstance(decision_id, str) and re_match_safe_id(decision_id) else None,
        "diagnostic_status": "skipped",
        "reason_codes": sorted(set(reason_codes)),
        "safe_summary": safe_summary,
        "non_authoritative": True,
    }


def graph_context_candidate_to_record(
    candidate: dict[str, Any],
    decision: dict[str, Any],
    *,
    run_id: str,
    review_pack_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Convert one accepted candidate and verifier decision into a graph-context staging row.

    Non-accepted or unsafe inputs return a diagnostic row instead of raising, so
    downstream export can preserve skipped-candidate visibility.
    """

    candidate_id = candidate.get("candidate_id")
    decision_id = decision.get("decision_id")
    candidate_kind = candidate.get("candidate_kind")
    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    reason_codes: list[str] = []
    if not isinstance(candidate_id, str) or not candidate_id.startswith("CAND-") or not re_match_safe_id(candidate_id):
        reason_codes.append("candidate-id-invalid")
    if not isinstance(decision_id, str) or not decision_id.startswith("DECISION-") or not re_match_safe_id(decision_id):
        reason_codes.append("decision-id-invalid")
    if decision.get("verifier_status") != "accepted":
        reason_codes.append("verifier-status-not-accepted")
    if not isinstance(candidate_kind, str) or candidate_kind not in GRAPH_CONTEXT_RECORD_KINDS:
        reason_codes.append("unsupported-record-kind")
    candidate_source_refs = candidate.get("source_refs")
    decision_evidence_refs = decision.get("acceptance_evidence_refs")
    if not isinstance(candidate_source_refs, list):
        candidate_source_refs = []
        reason_codes.append("source-refs-missing")
    if not isinstance(decision_evidence_refs, list):
        decision_evidence_refs = []
    source_refs = _safe_verifier_refs([ref for ref in candidate_source_refs if isinstance(ref, str)])
    evidence_refs = _safe_verifier_refs([ref for ref in decision_evidence_refs if isinstance(ref, str)])
    if len(source_refs) != len([ref for ref in candidate_source_refs if isinstance(ref, str)]):
        reason_codes.append("unsafe-source-ref")
    if not source_refs and not evidence_refs:
        reason_codes.append("source-refs-missing")
    if reason_codes or not isinstance(candidate_id, str) or not isinstance(decision_id, str) or not isinstance(candidate_kind, str):
        return _graph_context_diagnostic(
            run_id=run_id,
            candidate_id=candidate_id if isinstance(candidate_id, str) else None,
            decision_id=decision_id if isinstance(decision_id, str) else None,
            reason_codes=reason_codes,
        )
    trajectory_refs = [ref for ref in candidate.get("trajectory_refs", []) if isinstance(ref, str) and ref.startswith("trajectory:STEP-")]
    attempt_refs = [ref for ref in candidate.get("attempt_refs", []) if isinstance(ref, str) and ref.startswith("attempt:ATTEMPT-")]
    review_refs = [ref for ref in review_pack_refs or [] if isinstance(ref, str) and not ref.startswith("/") and ".." not in Path(ref).parts]
    safe_summary = str(candidate.get("candidate_summary") or candidate_id)[:240]
    return {
        "schema_version": GRAPH_CONTEXT_STAGING_SCHEMA_VERSION,
        "graph_context_id": stable_discovery_id("GCTX", run_id, candidate_id, decision_id, candidate_kind),
        "run_id": run_id,
        "record_kind": candidate_kind,
        "candidate_id": candidate_id,
        "decision_id": decision_id,
        "staging_status": "staged",
        "safe_summary": safe_summary,
        "confidence_bucket": candidate.get("confidence_bucket") if candidate.get("confidence_bucket") in {"low", "medium", "high"} else "unknown",
        "candidate_refs": [f"candidate:{candidate_id}"],
        "verifier_refs": [f"decision:{decision_id}"],
        "trajectory_refs": trajectory_refs,
        "source_refs": source_refs or evidence_refs,
        "attempt_refs": attempt_refs,
        "review_pack_refs": review_refs,
        "non_authoritative": True,
        "non_claims": [
            "graph_context staging does not claim legal correctness",
            "graph_context staging does not claim parser completeness",
            "graph_context staging does not validate R035",
            "graph_context staging does not validate R037",
            "graph_context staging does not validate R038",
        ],
    }


def graph_context_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped graph-context staging output directory."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "graph-context" / run_id


def export_graph_context_staging(
    workspace_root: Path,
    *,
    run_id: str,
    candidate_rows: list[dict[str, Any]] | None = None,
    decision_rows: list[dict[str, Any]] | None = None,
    review_pack_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Write graph-context staging, diagnostics, and summary artifacts for one run."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    if candidate_rows is None:
        candidate_rows = read_jsonl(discovery_directory(workspace_root, run_id) / "candidate_hypotheses.jsonl")
    if decision_rows is None:
        decision_rows = read_jsonl(verifier_directory(workspace_root, run_id) / "verifier_decisions.jsonl")
    decisions_by_candidate: dict[str, dict[str, Any]] = {}
    for decision in decision_rows:
        candidate_id = decision.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id not in decisions_by_candidate:
            decisions_by_candidate[candidate_id] = decision
    staging_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    for candidate in candidate_rows:
        candidate_id = candidate.get("candidate_id")
        if isinstance(candidate_id, str):
            seen_candidate_ids.add(candidate_id)
        decision = decisions_by_candidate.get(candidate_id) if isinstance(candidate_id, str) else None
        if decision is None:
            diagnostic_rows.append(
                _graph_context_diagnostic(
                    run_id=run_id,
                    candidate_id=candidate_id if isinstance(candidate_id, str) else None,
                    decision_id=None,
                    reason_codes=["missing-verifier-decision"],
                )
            )
            continue
        row = graph_context_candidate_to_record(
            candidate,
            decision,
            run_id=run_id,
            review_pack_refs=review_pack_refs,
        )
        if row["schema_version"] == GRAPH_CONTEXT_STAGING_SCHEMA_VERSION:
            staging_rows.append(row)
        else:
            diagnostic_rows.append(row)
    for decision in decision_rows:
        candidate_id = decision.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id not in seen_candidate_ids:
            diagnostic_rows.append(
                _graph_context_diagnostic(
                    run_id=run_id,
                    candidate_id=candidate_id,
                    decision_id=decision.get("decision_id") if isinstance(decision.get("decision_id"), str) else None,
                    reason_codes=["missing-candidate-row"],
                )
            )
    output_dir = graph_context_directory(workspace_root, run_id)
    staging_path = output_dir / "graph_context_staging.jsonl"
    diagnostics_path = output_dir / "graph_context_diagnostics.jsonl"
    summary_path = output_dir / "graph_context_summary.json"
    write_jsonl(staging_path, staging_rows)
    write_jsonl(diagnostics_path, diagnostic_rows)
    accepted = sum(1 for decision in decision_rows if decision.get("verifier_status") == "accepted")
    summary = {
        "schema_version": GRAPH_CONTEXT_SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "status": "graph_context_staging_exported",
        "accepted": accepted,
        "staged": len(staging_rows),
        "skipped": len(diagnostic_rows),
        "diagnostics": len(diagnostic_rows),
        "staging_ref": safe_output_ref(staging_path, workspace_root),
        "diagnostics_ref": safe_output_ref(diagnostics_path, workspace_root),
        "summary_ref": safe_output_ref(summary_path, workspace_root),
        "output_refs": [
            safe_output_ref(staging_path, workspace_root),
            safe_output_ref(diagnostics_path, workspace_root),
            safe_output_ref(summary_path, workspace_root),
        ],
        "non_authoritative": True,
        "non_claims": [
            "graph_context staging export does not claim legal correctness",
            "graph_context staging export does not claim parser completeness",
            "graph_context staging export does not validate R035",
            "graph_context staging export does not validate R037",
            "graph_context staging export does not validate R038",
        ],
    }
    write_json(summary_path, summary)
    return summary


def verify_discovery_candidates(
    workspace_root: Path,
    *,
    run_id: str,
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify S04 candidate rows and write S05 decision artifacts."""

    from source_hypothesis_verifier import review_queue_item, verify_proposal  # noqa: I001  # pyright: ignore[reportMissingImports]

    decisions: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []
    for candidate in candidate_rows:
        candidate_id = str(candidate.get("candidate_id") or stable_discovery_id("CAND", stable_json(candidate)))
        proposal, adapter_reasons = candidate_to_verifier_proposal(candidate)
        if proposal is None:
            base_decision = {
                "proposal_id": stable_discovery_id("SHP", candidate_id, "invalid"),
                "verifier_status": "rejected",
                "checked_refs": [],
                "acceptance_evidence_refs": [],
                "rejection_reasons": adapter_reasons,
                "decision_notes": ["candidate rejected before verifier proposal construction"],
                "non_authoritative": True,
            }
        else:
            base_decision = verify_proposal(proposal)
        status = str(base_decision["verifier_status"])
        decision_id = stable_discovery_id("DECISION", candidate_id, status, stable_json(base_decision))
        decision = {
            "schema_version": CANDIDATE_VERIFIER_DECISION_SCHEMA_VERSION,
            "decision_id": decision_id,
            "run_id": run_id,
            "candidate_id": candidate_id,
            "candidate_kind": candidate.get("candidate_kind"),
            "verifier_status": status,
            "checked_refs": base_decision.get("checked_refs", []),
            "acceptance_evidence_refs": base_decision.get("acceptance_evidence_refs", []),
            "rejection_reasons": base_decision.get("rejection_reasons", []),
            "decision_notes": base_decision.get("decision_notes", []),
            "trajectory_refs": candidate.get("trajectory_refs", []),
            "attempt_refs": candidate.get("attempt_refs", []),
            "source_refs": candidate.get("source_refs", []),
            "non_authoritative": True,
            "non_claims": [
                "verifier decision accepts or rejects a structural candidate only",
                "verifier decision does not claim legal correctness",
                "verifier decision does not claim parser completeness",
                "verifier decision does not validate R035",
                "verifier decision does not validate R038",
            ],
        }
        decisions.append(decision)
        if status == "needs_review" and proposal is not None:
            item = review_queue_item(proposal, base_decision)
            review_items.append(
                {
                    "schema_version": CANDIDATE_REVIEW_QUEUE_SCHEMA_VERSION,
                    "queue_item_id": stable_discovery_id("RQ", decision_id, candidate_id),
                    "candidate_id": candidate_id,
                    "decision_id": decision_id,
                    "proposal_id": item["proposal_id"],
                    "verifier_status": "needs_review",
                    "review_reason": item["review_reason"],
                    "safe_summary": item["safe_summary"],
                    "evidence_refs": item["evidence_refs"],
                    "non_authoritative": True,
                }
            )
        if status == "rejected":
            rejection_rows.append(
                {
                    "schema_version": CANDIDATE_REJECTION_SCHEMA_VERSION,
                    "rejection_id": stable_discovery_id("REJECT", decision_id, candidate_id),
                    "candidate_id": candidate_id,
                    "decision_id": decision_id,
                    "rejection_reasons": decision["rejection_reasons"],
                    "trajectory_refs": decision["trajectory_refs"],
                    "source_refs": decision["source_refs"],
                    "non_authoritative": True,
                }
            )
    directory = verifier_directory(workspace_root, run_id)
    output_paths: list[Path] = []
    if decisions:
        path = directory / "verifier_decisions.jsonl"
        write_jsonl(path, decisions)
        output_paths.append(path)
    if review_items:
        path = directory / "review_queue_items.jsonl"
        write_jsonl(path, review_items)
        output_paths.append(path)
    if rejection_rows:
        path = directory / "rejection_reasons.jsonl"
        write_jsonl(path, rejection_rows)
        output_paths.append(path)
    status_counts = {status: sum(1 for row in decisions if row["verifier_status"] == status) for status in ("accepted", "rejected", "needs_review")}
    return {
        "schema_version": "m032.s05.candidate-verifier-result/v1",
        "status": "verified",
        "run_id": run_id,
        "decision_count": len(decisions),
        "status_counts": status_counts,
        "output_refs": output_summary(output_paths, workspace_root)["output_refs"] if output_paths else [],
        "non_authoritative": True,
    }


def external_review_directory(workspace_root: Path, run_id: str) -> Path:
    """Return the run-scoped external review output directory."""

    if not run_id.startswith("RUN-") or not re_match_safe_id(run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    return workspace_root / "runtime" / "external-review" / run_id


def _rows_at(workspace_root: Path, ref: str) -> list[dict[str, Any]]:
    path = workspace_root / ref
    return read_jsonl(path) if path.exists() else []


def _status_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if isinstance(value, str):
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_external_review_pack(workspace_root: Path, run_id: str) -> dict[str, Any]:
    """Build deterministic external GPT-5.5 review pack artifacts without calling GPT-5.5."""

    refs = {
        "trajectory": f"runtime/trajectory/{run_id}/discovery_steps.jsonl",
        "attempts": f"runtime/minimax-attempts/{run_id}/attempts.jsonl",
        "candidates": f"runtime/discovery/{run_id}/candidate_hypotheses.jsonl",
        "signals": f"runtime/discovery/{run_id}/graph_context_signals.jsonl",
        "diagnostics": f"runtime/discovery/{run_id}/normalization_diagnostics.jsonl",
        "decisions": f"runtime/verifier/{run_id}/verifier_decisions.jsonl",
        "review_queue": f"runtime/verifier/{run_id}/review_queue_items.jsonl",
        "rejections": f"runtime/verifier/{run_id}/rejection_reasons.jsonl",
    }
    rows = {name: _rows_at(workspace_root, ref) for name, ref in refs.items()}
    missing_sections = [name for name, ref in refs.items() if not (workspace_root / ref).exists()]
    review_id = stable_discovery_id("REVIEW", run_id, stable_json({name: len(value) for name, value in rows.items()}))
    decisions = rows["decisions"]
    candidates = rows["candidates"]
    attempts = rows["attempts"]
    trajectory = rows["trajectory"]
    rejections = rows["rejections"]
    review_queue = rows["review_queue"]
    diagnostics = rows["diagnostics"]
    pack = {
        "schema_version": EXTERNAL_REVIEW_PACK_SCHEMA_VERSION,
        "run_id": run_id,
        "review_id": review_id,
        "review_scope": "external_gpt55_cli_output_review",
        "trajectory_summary": {
            "record_count": len(trajectory),
            "event_types": sorted({str(row.get("event_type")) for row in trajectory if row.get("event_type")}),
            "phases": sorted({str(row.get("phase")) for row in trajectory if row.get("phase")}),
            "step_refs": [f"trajectory:{row['step_id']}" for row in trajectory if isinstance(row.get("step_id"), str)],
        },
        "minimax_attempt_summary": {
            "attempt_count": len(attempts),
            "statuses": _status_counts(attempts, "status"),
            "model_names": sorted({str(row.get("model_name")) for row in attempts if row.get("model_name")}),
            "response_summaries": [row.get("response_summary") for row in attempts if row.get("response_summary")],
            "non_authoritative": True,
        },
        "candidate_summary": {
            "candidate_count": len(candidates),
            "candidate_kinds": _status_counts(candidates, "candidate_kind"),
            "lifecycle_statuses": _status_counts(candidates, "lifecycle_status"),
            "candidate_refs": [f"candidate:{row['candidate_id']}" for row in candidates if isinstance(row.get("candidate_id"), str)],
            "model_claims_ignored": [claim for row in candidates for claim in row.get("model_claims_ignored", []) if isinstance(claim, str)],
        },
        "verifier_summary": {
            "decision_count": len(decisions),
            "status_counts": _status_counts(decisions, "verifier_status"),
            "checked_refs": sorted({ref for row in decisions for ref in row.get("checked_refs", []) if isinstance(ref, str)}),
            "acceptance_evidence_refs": sorted({ref for row in decisions for ref in row.get("acceptance_evidence_refs", []) if isinstance(ref, str)}),
            "decision_notes": [note for row in decisions for note in row.get("decision_notes", []) if isinstance(note, str)],
        },
        "rejected_branch_summary": {
            "rejected_count": len(rejections),
            "candidate_ids": [row.get("candidate_id") for row in rejections if row.get("candidate_id")],
            "reason_categories": sorted({reason for row in rejections for reason in row.get("rejection_reasons", []) if isinstance(reason, str)}),
        },
        "review_queue_summary": {
            "needs_review_count": len(review_queue),
            "queue_item_ids": [row.get("queue_item_id") for row in review_queue if row.get("queue_item_id")],
            "review_reasons": sorted({str(row.get("review_reason")) for row in review_queue if row.get("review_reason")}),
        },
        "normalization_diagnostics_summary": {
            "diagnostic_count": len(diagnostics),
            "error_kinds": sorted({str(row.get("error_kind")) for row in diagnostics if row.get("error_kind")}),
            "statuses": _status_counts(diagnostics, "status"),
        },
        "artifact_refs": [ref for ref in refs.values() if (workspace_root / ref).exists()],
        "review_questions": [
            "Are the discovered structures and graph-context candidates understandable from the trajectory and supporting context?",
            "Do accepted verifier decisions appear traceable to candidate refs, trajectory refs, and evidence refs?",
            "Are rejected or needs_review branches useful for parser or graph-context improvements?",
            "Are there ambiguities in refs, trajectory steps, or candidate summaries that would block review?",
            "Does the pack avoid overclaiming legal correctness, parser completeness, R035 validation, or R038 validation?",
        ],
        "expected_external_review_output": {
            "review_verdict": "useful|needs_more_evidence|not_useful|blocked_by_traceability",
            "fields": ["useful_findings", "candidate_concerns", "traceability_concerns", "recommended_next_actions", "non_claims"],
        },
        "missing_sections": missing_sections,
        "boundary": {
            "gpt55_role": "external control over CLI outputs",
            "not_runtime_judge": True,
            "deterministic_verifier_remains_runtime_gate": True,
        },
        "non_authoritative": True,
        "non_claims": [
            "external review pack does not claim legal correctness",
            "external review pack does not claim parser completeness",
            "external review pack does not validate R035",
            "external review pack does not validate R038",
        ],
    }
    output_dir = external_review_directory(workspace_root, run_id)
    json_path = output_dir / "review_pack.json"
    md_path = output_dir / "review_pack.md"
    summary_path = output_dir / "external_review_summary.md"
    write_json(json_path, pack)
    md_lines = [
        f"# External GPT-5.5 Review Pack — {run_id}",
        "",
        "GPT-5.5 is external control over CLI outputs, not an embedded runtime judge.",
        "Deterministic verifier decisions remain the runtime candidate gate.",
        "",
        f"- Candidates: {pack['candidate_summary']['candidate_count']}",
        f"- Verifier decisions: {pack['verifier_summary']['decision_count']}",
        f"- Missing sections: {', '.join(missing_sections) if missing_sections else 'none'}",
        "",
        "## Review Questions",
        *[f"- {question}" for question in pack["review_questions"]],
        "",
        "## Non-claims",
        *[f"- {claim}" for claim in pack["non_claims"]],
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    summary_path.write_text(
        "# External Review Summary\n\n"
        "This local summary identifies the bundle prepared for external GPT-5.5 review. "
        "It is not an external review verdict.\n",
        encoding="utf-8",
    )
    return {
        "schema_version": "m032.s06.external-review-pack-result/v1",
        "status": "review_pack_written",
        "run_id": run_id,
        "review_id": review_id,
        "review_pack_ref": safe_output_ref(md_path, workspace_root),
        "review_pack_json_ref": safe_output_ref(json_path, workspace_root),
        "external_review_summary_ref": safe_output_ref(summary_path, workspace_root),
        "missing_sections": missing_sections,
        "non_authoritative": True,
    }


def _load_mock_minimax_response(path: Path) -> str:
    """Load a mocked MiniMax response summary for deterministic tests."""

    payload = _load_json_object(path)
    for key in ("response_summary", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise SourceLifecycleError("mock MiniMax response requires response_summary, content, or message")


def _call_minimax_chat(
    *,
    prompt_summary: str,
    model: str,
    endpoint: str,
    api_key: str,
    timeout_seconds: int,
) -> str:
    """Call MiniMax through its OpenAI-compatible chat-completions surface."""

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You propose non-authoritative structural discovery observations for open legal "
                    "source artifacts. Return concise graph-context candidates only."
                ),
            },
            {"role": "user", "content": prompt_summary},
        ],
        "temperature": 0.1,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SourceLifecycleError(f"MiniMax provider HTTP error: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SourceLifecycleError("MiniMax provider connection failed") from exc
    except json.JSONDecodeError as exc:
        raise SourceLifecycleError("MiniMax provider returned malformed JSON") from exc
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()
    raise SourceLifecycleError("MiniMax provider response missing message content")


def discover_with_minimax(
    workspace_root: Path,
    *,
    run_id: str | None = None,
    source_refs: list[str] | None = None,
    prompt_summary: str = "Discover source structures useful for graph context.",
    model: str = DEFAULT_MINIMAX_MODEL,
    endpoint: str = DEFAULT_MINIMAX_ENDPOINT,
    api_key_env: str = DEFAULT_MINIMAX_API_KEY_ENV,
    mock_response_path: Path | None = None,
    started_at: str | None = None,
    timeout_seconds: int = 30,
    verify_candidates: bool = False,
) -> dict[str, Any]:
    """Run one non-authoritative MiniMax-assisted discovery attempt."""

    selected_run_id = run_id or safe_run_id("minimax-discovery", started_at)
    if not selected_run_id.startswith("RUN-") or not re_match_safe_id(selected_run_id):
        raise SourceLifecycleError("run_id must be a safe RUN- identifier")
    refs = sorted(source_refs or [])
    start_step_id = stable_discovery_id("STEP", selected_run_id, "minimax-discovery-start")
    attempt_id = stable_discovery_id("ATTEMPT", selected_run_id, prompt_summary, "minimax")
    append_trajectory_record(
        workspace_root,
        selected_run_id,
        trajectory_record(
            run_id=selected_run_id,
            event_type="minimax_attempt_prepared",
            phase="minimax_discovery",
            step_id=start_step_id,
            summary="Prepared MiniMax structural discovery attempt.",
            observed_context=prompt_summary,
            decision="prepared",
            decision_reason="Discovery command received workspace/run refs and prompt summary.",
            next_action="minimax_attempt_completed",
            source_refs=refs,
            output_refs=[f"attempt:{attempt_id}"],
            timestamp_utc=started_at,
            extra={
                "attempt_refs": [f"attempt:{attempt_id}"],
                "model_name": model,
                "operation": "prepare_minimax_prompt",
            },
        ),
        file_name="discovery_steps.jsonl",
    )

    api_key = os.environ.get(api_key_env, "")
    if mock_response_path is not None:
        response_summary = _load_mock_minimax_response(mock_response_path)
        status = "completed"
        decision_reason = "Mocked MiniMax response normalized for deterministic CLI verification."
    elif not api_key:
        response_summary = "MiniMax API key was not configured; no provider request was made."
        status = "blocked_missing_config"
        decision_reason = "Missing MiniMax API key environment variable."
    else:
        response_summary = _call_minimax_chat(
            prompt_summary=prompt_summary,
            model=model,
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        status = "completed"
        decision_reason = "MiniMax provider response summarized without persisting transport payloads."

    completed_step_id = stable_discovery_id("STEP", selected_run_id, attempt_id, status)
    append_trajectory_record(
        workspace_root,
        selected_run_id,
        trajectory_record(
            run_id=selected_run_id,
            event_type="minimax_attempt_completed" if status == "completed" else "run_failed",
            phase="minimax_discovery",
            step_id=completed_step_id,
            parent_step_id=start_step_id,
            summary="MiniMax structural discovery attempt completed." if status == "completed" else "MiniMax discovery blocked before provider call.",
            observed_context=response_summary,
            decision=status,
            decision_reason=decision_reason,
            next_action="candidate_normalization" if status == "completed" else "configure_minimax_and_retry",
            source_refs=refs,
            output_refs=[f"attempt:{attempt_id}"],
            timestamp_utc=started_at,
            extra={
                "attempt_refs": [f"attempt:{attempt_id}"],
                "model_name": model,
                "operation": "complete_minimax_attempt",
            },
        ),
        file_name="discovery_steps.jsonl",
    )
    attempt = write_minimax_attempt_summary(
        workspace_root,
        selected_run_id,
        {
            "attempt_id": attempt_id,
            "source_step_id": start_step_id,
            "source_refs": refs,
            "prompt_summary": prompt_summary,
            "response_summary": response_summary,
            "candidate_refs": [],
            "trajectory_refs": [f"trajectory:{start_step_id}", f"trajectory:{completed_step_id}"],
            "model_name": model,
            "status": status,
            "decision_reason": decision_reason,
        },
    )
    candidate_result = None
    verifier_result = None
    if status == "completed":
        candidate_result = normalize_discovery_candidates(
            workspace_root,
            run_id=selected_run_id,
            attempt_id=attempt_id,
            response_summary=response_summary,
            source_refs=refs,
            trajectory_refs=[f"trajectory:{start_step_id}", f"trajectory:{completed_step_id}"],
        )
        if verify_candidates and candidate_result["candidate_count"]:
            candidate_path = next(
                (
                    workspace_root / ref
                    for ref in candidate_result["output_refs"]
                    if ref.endswith("candidate_hypotheses.jsonl")
                ),
                None,
            )
            if candidate_path is not None:
                verifier_result = verify_discovery_candidates(
                    workspace_root,
                    run_id=selected_run_id,
                    candidate_rows=read_jsonl(candidate_path),
                )
    trajectory_ref = safe_output_ref(
        trajectory_directory(workspace_root, selected_run_id) / "discovery_steps.jsonl",
        workspace_root,
    )
    return {
        "schema_version": "m032.s03.minimax-discovery-result/v1",
        "status": status,
        "run_id": selected_run_id,
        "attempt_id": attempt_id,
        "trajectory_ref": trajectory_ref,
        "attempt_ref": attempt["attempt_ref"],
        "candidate_count": candidate_result["candidate_count"] if candidate_result else 0,
        "signal_count": candidate_result["signal_count"] if candidate_result else 0,
        "candidate_refs": candidate_result["candidate_refs"] if candidate_result else [],
        "discovery_output_refs": candidate_result["output_refs"] if candidate_result else [],
        "verifier_status_counts": verifier_result["status_counts"] if verifier_result else {},
        "verifier_output_refs": verifier_result["output_refs"] if verifier_result else [],
        "root_cause": "minimax-credential-missing" if status == "blocked_missing_config" else None,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def re_match_safe_id(value: str) -> bool:
    """Return true when a generated id is safe for relative paths."""

    return bool(value) and all(ch.isalnum() or ch == "-" for ch in value)


def append_run_event(run_dir: Path, event: dict[str, Any]) -> None:
    """Append one safe event row to a run envelope."""

    append_jsonl(run_dir / "events.jsonl", [safe_log_row("event", event)])


def append_run_error(run_dir: Path, error: dict[str, Any]) -> None:
    """Append one safe error row to a run envelope."""

    append_jsonl(run_dir / "errors.jsonl", [safe_log_row("error", error)])


def safe_log_row(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a closed safe log row for events/errors."""

    allowed = {
        "phase",
        "status",
        "source_artifact_id",
        "parser_route",
        "error_kind",
        "count",
        "message",
    }
    row = {key: payload[key] for key in sorted(payload) if key in allowed and payload[key] is not None}
    if "message" in row:
        row["message"] = str(row["message"])[:220]
    row.update({"schema_version": f"legalgraph-source-run-{kind}/v1", "non_authoritative": True})
    return row


def manifest_input_summary(manifest: BatchManifest) -> dict[str, Any]:
    """Return a safe hashed input summary for a run."""

    artifacts = []
    for index, artifact in enumerate(manifest.artifacts):
        artifacts.append(
            {
                "artifact_index": index,
                "submitted_name_hash": artifact.submitted_name_hash,
                "declared_role_hint": artifact.declared_role_hint,
                "has_identity_hint": artifact.declared_identity_hint is not None,
            }
        )
    return {
        "schema_version": "legalgraph-source-run-inputs/v1",
        "batch_id_hash": hashlib.sha256(manifest.batch_id.encode("utf-8")).hexdigest(),
        "source_family_hint": manifest.source_family_hint,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def safe_output_ref(path: Path, workspace_root: Path) -> str:
    """Return a workspace-relative output ref or fail if path escapes."""

    resolved_workspace = workspace_root.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(resolved_workspace):
        raise SourceLifecycleError("output path escapes workspace")
    return str(resolved.relative_to(resolved_workspace))


def output_summary(paths: list[Path], workspace_root: Path) -> dict[str, Any]:
    """Return safe output refs for a run."""

    refs = [safe_output_ref(path, workspace_root) for path in paths]
    return {
        "schema_version": "legalgraph-source-run-outputs/v1",
        "output_count": len(refs),
        "output_refs": sorted(refs),
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def run_metrics_summary(
    *,
    registered_count: int = 0,
    classified_count: int = 0,
    processed_count: int = 0,
    error_count: int = 0,
) -> dict[str, Any]:
    """Return safe aggregate metrics for a run."""

    return {
        "schema_version": "legalgraph-source-run-metrics/v1",
        "registered_count": registered_count,
        "classified_count": classified_count,
        "processed_count": processed_count,
        "error_count": error_count,
        "status": "failed" if error_count else "completed",
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def workspace_tracking_warning(workspace_root: Path) -> dict[str, Any]:
    """Return tracking-policy diagnostics for lifecycle output directories."""

    lifecycle_dirs = ["inbox", "raw", "registry", "processed", "runs"]
    ignored: dict[str, bool] = {}
    for name in lifecycle_dirs:
        path = workspace_root / name / ".gsd-ignore-probe"
        ignored[name] = git_check_ignored(path)
    all_ignored = all(ignored.values())
    return {
        "schema_version": "legalgraph-source-workspace-tracking-warning/v1",
        "status": "ok" if all_ignored else "warning",
        "ignored": ignored,
        "message": "lifecycle output directories are ignored" if all_ignored else "review tracking policy before persistent real-corpus runs",
        "non_authoritative": True,
    }


def git_check_ignored(path: Path) -> bool:
    """Return whether git would ignore path; false outside a repo or on errors."""

    try:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=Path.cwd(),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return completed.returncode == 0


def run_batch_with_envelope(
    manifest_path: Path,
    workspace_root: Path,
    *,
    started_at: str | None = None,
) -> dict[str, Any]:
    """Run register/classify/process and persist a safe run envelope."""

    start_time = started_at or utc_now_iso()
    manifest: BatchManifest | None = None
    error_count = 0
    try:
        manifest = load_batch_manifest(manifest_path)
        run_id = safe_run_id(manifest.batch_id, start_time)
    except SourceLifecycleError:
        run_id = safe_run_id("manifest-error", start_time)
    run_dir = run_directory(workspace_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    tracking = workspace_tracking_warning(workspace_root)
    write_json(
        run_dir / "run.json",
        {
            "schema_version": "legalgraph-source-run/v1",
            "run_id": run_id,
            "started_at": start_time,
            "status": "running",
            "workspace_tracking": tracking,
            "non_authoritative": True,
            "non_claims": list(NON_CLAIMS),
        },
    )

    registered: dict[str, Any] | None = None
    classified: dict[str, Any] | None = None
    processed: dict[str, Any] | None = None
    output_paths: list[Path] = []
    try:
        manifest = manifest or load_batch_manifest(manifest_path)
        write_json(run_dir / "inputs.json", manifest_input_summary(manifest))
        append_run_event(run_dir, {"phase": "register", "status": "started"})
        registered = register_batch(manifest_path, workspace_root)
        append_run_event(run_dir, {"phase": "register", "status": "completed", "count": registered["registered_count"]})
        append_run_event(run_dir, {"phase": "classify", "status": "started"})
        classified = classify_batch(manifest_path, workspace_root)
        append_run_event(run_dir, {"phase": "classify", "status": "completed", "count": classified["classified_count"]})
        append_run_event(run_dir, {"phase": "process", "status": "started"})
        processed = process_batch(manifest_path, workspace_root)
        append_run_event(run_dir, {"phase": "process", "status": "completed", "count": processed["processed_count"]})
        output_dir = workspace_root / str(processed["output_dir"])
        output_paths = [
            workspace_root / "registry" / "source_artifacts.jsonl",
            workspace_root / "registry" / "source_revisions.jsonl",
            workspace_root / "registry" / "batches.jsonl",
            workspace_root / "registry" / "source_classification.safe.jsonl",
            output_dir / "source_inventory.safe.jsonl",
            output_dir / "diagnostics.safe.jsonl",
            output_dir / "metrics.safe.json",
        ]
        write_json(run_dir / "outputs.json", output_summary(output_paths, workspace_root))
    except SourceLifecycleError as exc:
        error_count = 1
        append_run_error(
            run_dir,
            {"phase": "run-batch", "status": "failed", "error_kind": "source_lifecycle_error", "message": str(exc)},
        )

    metrics = run_metrics_summary(
        registered_count=int((registered or {}).get("registered_count", 0)),
        classified_count=int((classified or {}).get("classified_count", 0)),
        processed_count=int((processed or {}).get("processed_count", 0)),
        error_count=error_count,
    )
    write_json(run_dir / "metrics.json", metrics)
    final = {
        "schema_version": "legalgraph-source-run/v1",
        "run_id": run_id,
        "started_at": start_time,
        "completed_at": utc_now_iso(),
        "status": metrics["status"],
        "workspace_tracking": tracking,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }
    write_json(run_dir / "run.json", final)
    return {
        "status": metrics["status"],
        "run_id": run_id,
        "run_ref": safe_output_ref(run_dir, workspace_root),
        "registered": registered,
        "classified": classified,
        "processed": processed,
        "metrics": metrics,
        "workspace_tracking": tracking,
        "non_authoritative": True,
    }


def latest_run_id(workspace_root: Path) -> str:
    """Return the latest run id in a workspace."""

    runs_root = workspace_root / "runs"
    run_ids = sorted(path.name for path in runs_root.iterdir() if path.is_dir()) if runs_root.exists() else []
    if not run_ids:
        raise SourceLifecycleError("no runs found in workspace")
    return run_ids[-1]


def build_review_pack(workspace_root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Build safe review_pack.md and review_pack.json for a run."""

    selected_run_id = run_id or latest_run_id(workspace_root)
    run_dir = run_directory(workspace_root, selected_run_id)
    run_json = _load_json_object(run_dir / "run.json")
    metrics = _load_json_object(run_dir / "metrics.json")
    outputs = _load_json_object(run_dir / "outputs.json") if (run_dir / "outputs.json").exists() else {
        "output_refs": [],
        "output_count": 0,
    }
    errors = read_jsonl(run_dir / "errors.jsonl") if (run_dir / "errors.jsonl").exists() else []
    events = read_jsonl(run_dir / "events.jsonl") if (run_dir / "events.jsonl").exists() else []
    pack = {
        "schema_version": "legalgraph-source-review-pack/v1",
        "run_id": selected_run_id,
        "run_status": run_json.get("status"),
        "metrics": metrics,
        "output_refs": outputs.get("output_refs", []),
        "event_count": len(events),
        "error_count": len(errors),
        "error_kinds": sorted({str(error.get("error_kind")) for error in errors if error.get("error_kind")}),
        "workspace_tracking": run_json.get("workspace_tracking"),
        "rerun_hint": "uv run python scripts/source_cli.py --workspace <workspace> run-batch <manifest>",
        "next_steps": review_next_steps(str(run_json.get("status")), int(metrics.get("error_count", 0))),
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }
    write_json(run_dir / "review_pack.json", pack)
    (run_dir / "review_pack.md").write_text(render_review_pack_markdown(pack), encoding="utf-8")
    return {
        "status": "review_pack_written",
        "run_id": selected_run_id,
        "review_pack_ref": safe_output_ref(run_dir / "review_pack.md", workspace_root),
        "review_pack_json_ref": safe_output_ref(run_dir / "review_pack.json", workspace_root),
        "run_status": pack["run_status"],
        "error_count": pack["error_count"],
        "non_authoritative": True,
    }


def review_next_steps(status: str, error_count: int) -> list[str]:
    """Return bounded next-step recommendations for a review pack."""

    if status == "completed" and error_count == 0:
        return [
            "Inspect metrics and output refs for expected counts.",
            "Proceed to S05/S06 only if deterministic artifacts match the planned source boundary.",
        ]
    return [
        "Inspect errors.jsonl for bounded failure categories.",
        "Fix manifest or artifact issues, then rerun run-batch in a temporary workspace.",
    ]


def render_review_pack_markdown(pack: dict[str, Any]) -> str:
    """Render a safe human-readable review pack."""

    output_refs = "\n".join(f"- `{ref}`" for ref in pack.get("output_refs", [])) or "- None"
    error_kinds = "\n".join(f"- `{kind}`" for kind in pack.get("error_kinds", [])) or "- None"
    next_steps = "\n".join(f"- {step}" for step in pack.get("next_steps", []))
    metrics = pack.get("metrics", {})
    tracking = pack.get("workspace_tracking") or {}
    return f"""# Consultant XML Run Review Pack

## Run

- Run ID: `{pack['run_id']}`
- Status: `{pack['run_status']}`
- Registered: `{metrics.get('registered_count', 0)}`
- Classified: `{metrics.get('classified_count', 0)}`
- Processed: `{metrics.get('processed_count', 0)}`
- Errors: `{pack.get('error_count', 0)}`
- Workspace tracking: `{tracking.get('status', 'unknown')}`

## Output refs

{output_refs}

## Error kinds

{error_kinds}

## Rerun hint

```bash
{pack['rerun_hint']}
```

## Non-claims

- This review pack does not claim legal correctness.
- This review pack does not claim parser completeness.
- This review pack does not validate R035.
- This review pack does not claim product retrieval quality.

## Next steps

{next_steps}
"""
