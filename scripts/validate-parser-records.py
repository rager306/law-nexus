#!/usr/bin/env python3
"""Validate and generate LegalGraph parser record contract artifacts.

This command is intentionally local and deterministic. It validates parser JSONL
records, generates JSON Schema/contract examples/report artifacts, and emits a
compact JSON summary that is safe for agent inspection. It does not parse legal
sources or claim legal correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from parser_records import (
    PARSER_RECORD_ADAPTER,
    DocumentRecord,
    RelationCandidateRecord,
    SourceBlockRecord,
    dumps_jsonl_record,
    load_jsonl_records,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path("prd/parser/source_fixture_inventory.json")
SCHEMA_DIR = Path("prd/parser/schemas")
EXAMPLE_DIR = Path("prd/parser/examples")
CONTRACT_REPORT_PATH = Path("prd/parser/parser_record_contract.md")

RecordKind = Literal["document", "source_block", "relation_candidate"]
EXPECTED_EXAMPLE_FILES: dict[RecordKind, Path] = {
    "document": EXAMPLE_DIR / "document_records.jsonl",
    "source_block": EXAMPLE_DIR / "source_block_records.jsonl",
    "relation_candidate": EXAMPLE_DIR / "relation_candidate_records.jsonl",
}
EXPECTED_SCHEMA_FILES = {
    "document_record": SCHEMA_DIR / "document_record.schema.json",
    "source_block_record": SCHEMA_DIR / "source_block_record.schema.json",
    "relation_candidate_record": SCHEMA_DIR / "relation_candidate_record.schema.json",
    "parser_record": SCHEMA_DIR / "parser_record.schema.json",
}
NON_CLAIMS = [
    "Contract examples do not claim parser completeness.",
    "Contract examples do not claim legal correctness or authoritative legal interpretation.",
    "Contract examples do not claim product ETL readiness.",
    "Contract examples do not claim FalkorDB runtime/load readiness.",
]


@dataclass(frozen=True)
class GeneratedArtifact:
    path: Path
    content: str


def stable_json(data: Any) -> str:
    """Return deterministic pretty JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compact_json(data: Any) -> str:
    """Return deterministic compact JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_text(text: str) -> str:
    """Return SHA-256 for a bounded example excerpt."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_inventory(root: Path) -> dict[str, Any]:
    """Load and validate the canonical parser fixture inventory."""

    path = root / INVENTORY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"canonical fixture inventory is missing: {INVENTORY_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"canonical fixture inventory is malformed JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("canonical fixture inventory must decode to an object")
    if payload.get("status") != "pass":
        raise ValueError("canonical fixture inventory status must be 'pass'")
    if payload.get("non_authoritative") is not True:
        raise ValueError("canonical fixture inventory must preserve non_authoritative: true")

    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("canonical fixture inventory must contain a non-empty fixtures list")

    seen_paths: set[str] = set()
    for index, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict):
            raise ValueError(f"fixture entry {index} must be an object")
        fixture_path = fixture.get("path")
        if not isinstance(fixture_path, str) or not fixture_path:
            raise ValueError(f"fixture entry {index} is missing a path")
        if fixture_path in seen_paths:
            raise ValueError(f"duplicate fixture path in canonical inventory: {fixture_path}")
        seen_paths.add(fixture_path)
        if fixture.get("canonical") is not True or fixture.get("exists") is not True:
            raise ValueError(f"fixture {fixture_path} must be canonical and present")
        source_kind = fixture.get("source_kind")
        if source_kind not in {"garant-odt", "consultant-wordml-xml"}:
            raise ValueError(f"fixture {fixture_path} has unsupported source_kind {source_kind!r}")
        sha256 = fixture.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64 or sha256.lower() != sha256:
            raise ValueError(f"fixture {fixture_path} must include lowercase sha256")

    return payload


def fixtures_by_path(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index validated inventory fixture entries by canonical path."""

    return {fixture["path"]: fixture for fixture in inventory["fixtures"]}


def build_example_records(inventory: dict[str, Any]) -> dict[RecordKind, list[dict[str, Any]]]:
    """Build bounded JSONL example records from canonical manifest paths/hashes."""

    fixtures = fixtures_by_path(inventory)
    odt_44 = fixtures["law-source/garant/44-fz.odt"]
    odt_pp = fixtures["law-source/garant/PP_60_27-01-2022.odt"]
    consultant = fixtures["law-source/consultant/Список документов (5).xml"]

    block_excerpt = "Bounded content.xml excerpt placeholder for parser contract shape only."
    relation_excerpt = "Bounded Consultant WordML excerpt placeholder for relation-candidate shape only."

    document_records = [
        {
            "record_kind": "document",
            "schema_version": "legalgraph-parser-record/v1",
            "id": "DOC-44-FZ",
            "source_kind": odt_44["source_kind"],
            "source_path": odt_44["path"],
            "source_sha256": odt_44["sha256"],
            "title": "44-FZ canonical parser fixture",
            "non_authoritative": True,
            "non_claims": NON_CLAIMS,
        },
        {
            "record_kind": "document",
            "schema_version": "legalgraph-parser-record/v1",
            "id": "DOC-PP-60",
            "source_kind": odt_pp["source_kind"],
            "source_path": odt_pp["path"],
            "source_sha256": odt_pp["sha256"],
            "title": "PP-60 canonical parser fixture",
            "non_authoritative": True,
            "non_claims": NON_CLAIMS,
        },
    ]
    source_block_records = [
        {
            "record_kind": "source_block",
            "schema_version": "legalgraph-parser-record/v1",
            "id": "BLOCK-44-FZ-0001",
            "document_id": "DOC-44-FZ",
            "source_kind": odt_44["source_kind"],
            "source_path": odt_44["path"],
            "source_sha256": odt_44["sha256"],
            "source_member": "content.xml",
            "order_index": 0,
            "location": {
                "selector": "/office:document-content/office:body",
                "label": "bounded contract example locator",
            },
            "excerpt": block_excerpt,
            "excerpt_sha256": sha256_text(block_excerpt),
            "non_authoritative": True,
            "non_claims": NON_CLAIMS,
        }
    ]
    relation_candidate_records = [
        {
            "record_kind": "relation_candidate",
            "schema_version": "legalgraph-parser-record/v1",
            "id": "REL-CONS-0001",
            "source_kind": consultant["source_kind"],
            "source_path": consultant["path"],
            "source_sha256": consultant["sha256"],
            "source_member": None,
            "source_block_id": "BLOCK-CONS-0001",
            "subject_ref": "DOC-44-FZ",
            "object_ref": "DOC-PP-60",
            "relation_type": "mentions",
            "status": "candidate",
            "evidence_excerpt": relation_excerpt,
            "evidence_sha256": sha256_text(relation_excerpt),
            "non_authoritative": True,
            "non_claims": NON_CLAIMS
            + ["Relation example is candidate-only and not evidence of an authoritative relation."],
        }
    ]
    return {
        "document": document_records,
        "source_block": source_block_records,
        "relation_candidate": relation_candidate_records,
    }


def jsonl_content(records: list[dict[str, Any]]) -> str:
    """Serialize records as deterministic JSONL."""

    return "".join(dumps_jsonl_record(record) + "\n" for record in records)


def schema_artifacts() -> list[GeneratedArtifact]:
    """Generate deterministic JSON Schema artifacts for parser records."""

    schema_inputs: list[tuple[str, Path, dict[str, Any]]] = [
        ("DocumentRecord", EXPECTED_SCHEMA_FILES["document_record"], DocumentRecord.model_json_schema()),
        (
            "SourceBlockRecord",
            EXPECTED_SCHEMA_FILES["source_block_record"],
            SourceBlockRecord.model_json_schema(),
        ),
        (
            "RelationCandidateRecord",
            EXPECTED_SCHEMA_FILES["relation_candidate_record"],
            RelationCandidateRecord.model_json_schema(),
        ),
        ("ParserRecord", EXPECTED_SCHEMA_FILES["parser_record"], PARSER_RECORD_ADAPTER.json_schema()),
    ]
    artifacts: list[GeneratedArtifact] = []
    for kind, path, schema in schema_inputs:
        if not isinstance(schema, dict):
            raise ValueError(f"schema generation for {kind} did not return an object")
        schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
        schema.setdefault("description", f"Generated JSON Schema for {kind}.")
        artifacts.append(GeneratedArtifact(path=path, content=stable_json(schema)))
    return artifacts


def example_artifacts(inventory: dict[str, Any]) -> list[GeneratedArtifact]:
    """Generate JSONL example artifacts."""

    examples = build_example_records(inventory)
    return [
        GeneratedArtifact(path=EXPECTED_EXAMPLE_FILES[kind], content=jsonl_content(records))
        for kind, records in examples.items()
    ]


def contract_report(inventory: dict[str, Any]) -> str:
    """Generate the human-readable parser record contract report."""

    examples = build_example_records(inventory)
    counts = {kind: len(records) for kind, records in examples.items()}
    return f"""# Parser Record Contract

Generated by `uv run python scripts/validate-parser-records.py --write`.

## Purpose

This contract defines the strict parser boundary records for downstream M006 parser and graph staging work. `DocumentRecord`, `SourceBlockRecord`, and `RelationCandidateRecord` are provenance-preserving Pydantic v2 models with generated JSON Schema artifacts and JSONL examples.

The records are non-authoritative inspection artifacts. They validate shape, provenance, bounded excerpts, candidate status, and non-claim preservation; they do not validate legal correctness, parser completeness, product ETL readiness, or FalkorDB runtime readiness.

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `prd/parser/schemas/document_record.schema.json` | JSON Schema for document-level parser records. |
| `prd/parser/schemas/source_block_record.schema.json` | JSON Schema for bounded source-block records. |
| `prd/parser/schemas/relation_candidate_record.schema.json` | JSON Schema for candidate-only relation records. |
| `prd/parser/schemas/parser_record.schema.json` | Discriminated union schema over all parser record kinds. |
| `prd/parser/examples/document_records.jsonl` | Positive document examples seeded from canonical fixture paths and hashes. |
| `prd/parser/examples/source_block_records.jsonl` | Positive source-block examples with bounded excerpts and excerpt hashes. |
| `prd/parser/examples/relation_candidate_records.jsonl` | Positive candidate-only relation examples. |

## Record kinds and required boundaries

| Record kind | Model | Downstream consumer note |
|---|---|---|
| `document` | `DocumentRecord` | S03/S04/S05 may use this as a document identity/provenance input, not as a legal authority claim. |
| `source_block` | `SourceBlockRecord` | ODT source blocks must use `source_member: "content.xml"`; excerpts are bounded and hashed. |
| `relation_candidate` | `RelationCandidateRecord` | Relations remain `candidate`, `needs-review`, or `rejected`; no authoritative/product-ready status is valid. |

All models reject unexpected properties through strict Pydantic configuration. All records require `non_authoritative: true`, non-empty `non_claims`, repository-relative `source_path`, and lowercase SHA-256 provenance.

## CLI usage

```bash
uv run python scripts/validate-parser-records.py --write
uv run python scripts/validate-parser-records.py --check
uv run python scripts/validate-parser-records.py --kind document prd/parser/examples/document_records.jsonl
```

`--check` regenerates expected schemas, examples, and this report in memory, compares them to tracked files, validates all three example JSONL files, and emits a compact JSON summary with `status`, counts per record kind, artifact freshness, diagnostics, and `non_authoritative: true`.

Validation diagnostics include file, line, record id/kind when available, field/location, rule/type, source path when available, and a human-readable message. Diagnostics intentionally avoid raw legal text beyond bounded example excerpts.

## Current example counts

```json
{compact_json(counts).strip()}
```

## Explicit non-claims

- This contract does not claim parser completeness.
- This contract does not claim legal correctness or authoritative legal interpretation.
- This contract does not claim product ETL readiness.
- This contract does not claim FalkorDB graph load/runtime readiness.
- Consultant WordML XML remains relation fixture / prior-art evidence until later validation proves candidate relations.

## Consumer boundary for S03/S04/S05

- S03 ODT work should emit only records accepted by this contract and must preserve `source_path`, `source_sha256`, bounded excerpts, and `non_claims`.
- S04 Consultant WordML work should treat relation outputs as candidate-only and preserve prior-art/non-authoritative language.
- S05 NetworkX staging may consume validated records as deterministic staging/debug inputs, not as product graph truth or legal evidence.
"""


def generated_artifacts(root: Path) -> list[GeneratedArtifact]:
    """Return every generated artifact with expected content."""

    inventory = load_inventory(root)
    return [
        *schema_artifacts(),
        *example_artifacts(inventory),
        GeneratedArtifact(path=CONTRACT_REPORT_PATH, content=contract_report(inventory)),
    ]


def write_artifacts(root: Path) -> list[str]:
    """Write generated artifacts and return repository-relative paths."""

    written: list[str] = []
    for artifact in generated_artifacts(root):
        target = root / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8", newline="\n")
        written.append(str(artifact.path))
    return written


def stale_artifact_diagnostic(path: Path, rule: str, message: str) -> dict[str, Any]:
    """Return a deterministic artifact freshness diagnostic."""

    return {
        "file": str(path),
        "line": None,
        "record_id": None,
        "record_kind": None,
        "field": "artifact",
        "rule": rule,
        "source_path": None,
        "message": message,
    }


def check_artifacts(root: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Compare generated artifacts against tracked files."""

    artifact_status: dict[str, str] = {}
    diagnostics: list[dict[str, Any]] = []
    for artifact in generated_artifacts(root):
        target = root / artifact.path
        if not target.exists():
            artifact_status[str(artifact.path)] = "missing"
            diagnostics.append(
                stale_artifact_diagnostic(
                    artifact.path,
                    "artifact_missing",
                    "generated artifact is missing; run --write",
                )
            )
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != artifact.content:
            artifact_status[str(artifact.path)] = "stale"
            diagnostics.append(
                stale_artifact_diagnostic(
                    artifact.path,
                    "artifact_stale",
                    "generated artifact is stale; run --write",
                )
            )
        else:
            artifact_status[str(artifact.path)] = "fresh"
    return artifact_status, diagnostics


def validate_paths(
    paths: list[Path], *, expected_kind: RecordKind | None = None
) -> tuple[Counter[str], list[dict[str, Any]]]:
    """Validate JSONL paths and return counts plus diagnostics."""

    counts: Counter[str] = Counter()
    diagnostics: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            diagnostics.append(
                stale_artifact_diagnostic(
                    path,
                    "file_missing",
                    "JSONL file is missing",
                )
            )
            continue
        records, record_diagnostics = load_jsonl_records(path)
        diagnostics.extend(record_diagnostics)
        for record in records:
            counts[record.record_kind] += 1
            if expected_kind is not None and record.record_kind != expected_kind:
                diagnostics.append(
                    {
                        "file": str(path),
                        "line": None,
                        "record_id": record.id,
                        "record_kind": record.record_kind,
                        "field": "record_kind",
                        "rule": "unexpected_record_kind",
                        "source_path": record.source_path,
                        "message": f"expected record kind {expected_kind!r}, got {record.record_kind!r}",
                    }
                )
    return counts, diagnostics


def default_check_paths(root: Path) -> list[Path]:
    """Return example files validated by --check."""

    return [root / path for path in EXPECTED_EXAMPLE_FILES.values()]


def build_summary(
    *,
    status: str,
    counts: Counter[str],
    artifact_status: dict[str, str] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    written: list[str] | None = None,
) -> dict[str, Any]:
    """Build the CLI JSON summary."""

    ordered_counts = {
        "document": counts.get("document", 0),
        "source_block": counts.get("source_block", 0),
        "relation_candidate": counts.get("relation_candidate", 0),
    }
    return {
        "status": status,
        "non_authoritative": True,
        "counts": ordered_counts,
        "artifact_status": artifact_status or {},
        "diagnostic_count": len(diagnostics or []),
        "diagnostics": diagnostics or [],
        "written": written or [],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate parser record JSONL and generated parser contract artifacts."
    )
    parser.add_argument("files", nargs="*", type=Path, help="JSONL files to validate")
    parser.add_argument(
        "--kind",
        choices=["document", "source_block", "relation_candidate"],
        help="Require every validated record to use this record kind",
    )
    parser.add_argument("--write", action="store_true", help="Write generated schemas/examples/report")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check generated artifact freshness and validate contract examples",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.write and args.check:
        print("--write and --check are mutually exclusive", file=sys.stderr)
        return 2

    try:
        if args.write:
            written = write_artifacts(ROOT)
            counts, diagnostics = validate_paths(default_check_paths(ROOT))
            status = "pass" if not diagnostics else "fail"
            print(compact_json(build_summary(status=status, counts=counts, diagnostics=diagnostics, written=written)), end="")
            return 0 if status == "pass" else 1

        if args.check:
            artifact_status, artifact_diagnostics = check_artifacts(ROOT)
            paths = [path if path.is_absolute() else ROOT / path for path in args.files]
            if not paths:
                paths = default_check_paths(ROOT)
            counts, record_diagnostics = validate_paths(paths, expected_kind=args.kind)
            diagnostics = artifact_diagnostics + record_diagnostics
            status = "pass" if not diagnostics else "fail"
            print(compact_json(build_summary(status=status, counts=counts, artifact_status=artifact_status, diagnostics=diagnostics)), end="")
            return 0 if status == "pass" else 1

        paths = [path if path.is_absolute() else ROOT / path for path in args.files]
        if not paths:
            print("at least one JSONL file is required unless --write or --check is used", file=sys.stderr)
            return 2
        counts, diagnostics = validate_paths(paths, expected_kind=args.kind)
        status = "pass" if not diagnostics else "fail"
        print(compact_json(build_summary(status=status, counts=counts, diagnostics=diagnostics)), end="")
        return 0 if status == "pass" else 1
    except Exception as exc:  # noqa: BLE001 - CLI must surface model/generation errors loudly.
        summary = build_summary(
            status="fail",
            counts=Counter(),
            diagnostics=[
                {
                    "file": None,
                    "line": None,
                    "record_id": None,
                    "record_kind": None,
                    "field": "command",
                    "rule": exc.__class__.__name__,
                    "source_path": None,
                    "message": str(exc),
                }
            ],
        )
        print(compact_json(summary), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
