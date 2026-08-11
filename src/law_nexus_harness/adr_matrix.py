"""Derived, non-authoritative ADR matrix for repository diagnostics."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ADR_MATRIX_SCHEMA_VERSION = "law-nexus-adr-matrix/v1"
DEFAULT_ADR_MATRIX_PATH = Path("prd/architecture/adr-matrix.json")

_LIFECYCLE_RE = re.compile(r"\[(proposed|deferred|bounded|smoke|validated)\]", re.I)
_ADR_REF_RE = re.compile(
    r"\bADR-(?P<id>\d{4})(?:#(?P<scope>[a-z0-9][a-z0-9-]*))?\b",
    re.I,
)
_AUTHORITY_OUTPUT_PATHS = {
    "README.md",
    "prd/ARCHITECTURE.md",
    "prd/PRODUCT.md",
    "prd/REQUIREMENTS.md",
    "doc/adr/README.md",
}


class AdrMatrixError(RuntimeError):
    """Bounded CLI/tool error without source-content leakage."""

    def __init__(self, error: str, value: str) -> None:
        super().__init__(f"{error}: {value}")
        self.error = error
        self.value = value


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"^(?P<key>[a-z_]+):\s*(?P<value>.*)$", line, re.I)
        if match is not None:
            fields[match.group("key").lower()] = match.group("value").split(" #", 1)[0].strip()
    return {}


def _lifecycle(value: str) -> str | None:
    match = _LIFECYCLE_RE.search(value)
    return match.group(1).lower() if match is not None else None


def _refs(value: str) -> list[str]:
    refs = []
    for match in _ADR_REF_RE.finditer(value):
        ref = f"ADR-{match.group('id')}"
        if match.group("scope"):
            ref += f"#{match.group('scope').lower()}"
        refs.append(ref)
    return sorted(set(refs))


def _surface_lifecycle(text: str, adr_id: str) -> str | None:
    for line in text.splitlines():
        if adr_id in line:
            lifecycle = _lifecycle(line)
            if lifecycle is not None:
                return lifecycle
    return None


def _read_optional(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def build_adr_matrix(root: Path) -> dict[str, Any]:
    """Derive a diagnostic ADR matrix from active ADR files and living surfaces."""
    root = root.resolve()
    adr_dir = root / "doc" / "adr"
    if not adr_dir.is_dir():
        raise AdrMatrixError("missing-input", "doc/adr")

    surfaces = {
        "architecture": _read_optional(root, "prd/ARCHITECTURE.md"),
        "root_readme": _read_optional(root, "README.md"),
        "adr_index": _read_optional(root, "doc/adr/README.md"),
    }
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(adr_dir.glob("0*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fields = _frontmatter(text)
        id_match = re.fullmatch(r"ADR-(\d{4})", fields.get("id", ""), re.I)
        if id_match is None:
            raise AdrMatrixError("invalid-adr-id", path.relative_to(root).as_posix())
        adr_id = f"ADR-{id_match.group(1)}"
        if adr_id in seen_ids:
            raise AdrMatrixError("duplicate-adr-id", adr_id)
        seen_ids.add(adr_id)
        status_lifecycle = _lifecycle(fields.get("lifecycle", ""))
        supersedes = _refs(fields.get("supersedes", fields.get("superseds", "")))
        superseded_by = _refs(fields.get("superseded_by", ""))
        rows.append(
            {
                "adr_id": adr_id,
                "path": path.relative_to(root).as_posix(),
                "status_lifecycle": status_lifecycle,
                "oracle_lifecycle": _surface_lifecycle(surfaces["architecture"], adr_id),
                "index_lifecycle": _surface_lifecycle(surfaces["adr_index"], adr_id),
                "supersedes": supersedes,
                "superseded_by": superseded_by,
                "surfaces": {name: adr_id in content for name, content in surfaces.items()},
            }
        )

    return {
        "schema_version": ADR_MATRIX_SCHEMA_VERSION,
        "authoritative": False,
        "generated_from": ["doc/adr/0*.md", "prd/ARCHITECTURE.md", "doc/adr/README.md"],
        "rows": rows,
        "summary": {
            "adr_count": len(rows),
            "supersession_edge_count": sum(len(row["supersedes"]) for row in rows),
        },
        "non_claims": [
            "This matrix is derived repository-control evidence only.",
            "A matrix row does not amend an ADR, satisfy a requirement, promote lifecycle, or validate product, runtime, legal, parser, retrieval, citation, ontology, applicability, TEI, or RuVector behavior.",
        ],
    }


def render_adr_matrix(matrix: dict[str, Any]) -> str:
    return json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_matrix_output_target(root: Path, output: Path) -> Path:
    root = root.resolve()
    resolved = output.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise AdrMatrixError("outside-root-output", str(output)) from error
    if relative in _AUTHORITY_OUTPUT_PATHS or relative.startswith("doc/adr/"):
        raise AdrMatrixError("authority-output-target", relative)
    return resolved


def check_adr_matrix_output(root: Path, output: Path) -> dict[str, Any]:
    target = validate_matrix_output_target(root, output)
    expected = render_adr_matrix(build_adr_matrix(root))
    if not target.is_file():
        return {
            "schema_version": ADR_MATRIX_SCHEMA_VERSION,
            "status": "stale",
            "authoritative": False,
            "output": target.relative_to(root.resolve()).as_posix(),
            "reason": "missing-output",
        }
    actual = target.read_text(encoding="utf-8", errors="replace")
    return {
        "schema_version": ADR_MATRIX_SCHEMA_VERSION,
        "status": "ok" if actual == expected else "stale",
        "authoritative": False,
        "output": target.relative_to(root.resolve()).as_posix(),
        "reason": "current" if actual == expected else "content-mismatch",
    }
