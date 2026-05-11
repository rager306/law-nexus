#!/usr/bin/env python3
# ruff: noqa: E402
"""Build deterministic Consultant WordML relation candidate records.

This generator emits candidate-only S02 parser records from the canonical
Consultant WordML relation fixture. It preserves provenance and URL identity but
intentionally does not claim parser completeness, legal correctness, product ETL
readiness, FalkorDB loading/runtime readiness, Consultant WordML legal authority,
or relation correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parser_records import (  # noqa: E402
    MAX_EXCERPT_CHARS,
    dumps_jsonl_record,
    parse_parser_record,
)

INVENTORY_PATH = Path("prd/parser/source_fixture_inventory.json")
DEFAULT_OUTPUT_DIR = Path("prd/parser")
RELATION_CANDIDATES_JSONL = "consultant_relation_candidates.jsonl"
REPORT_JSON = "consultant_relation_candidates.json"
SCHEMA_VERSION = "legalgraph-consultant-relation-candidates/v1"
SOURCE_KIND = "consultant-wordml-xml"
WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"
CONSULTANT_FIXTURE_BLOCK_ID = "BLOCK-CONSULTANT-XML-0001"

NON_CLAIMS = [
    "This Consultant WordML relation candidate does not claim parser completeness.",
    "This Consultant WordML relation candidate does not claim legal correctness or authoritative legal interpretation.",
    "This Consultant WordML relation candidate does not claim product ETL readiness.",
    "This Consultant WordML relation candidate does not claim FalkorDB loading/runtime readiness.",
    "This Consultant WordML relation candidate does not claim Consultant WordML legal authority.",
    "This Consultant WordML relation candidate does not claim relation correctness.",
]

REQUIRED_QUERY_FIELDS = ("base", "n", "date")


@dataclass
class BuildResult:
    """Complete generator output for Consultant relation candidates."""

    records: list[dict[str, Any]]
    report: dict[str, Any]
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


def repo_path(path: Path, root: Path = ROOT) -> str:
    """Return a stable repository-relative POSIX path when possible."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest for UTF-8 text."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def namespaced(name: str, namespace: str = WORDML_NS) -> str:
    """Build an ElementTree namespaced tag or attribute name."""

    return f"{{{namespace}}}{name}"


def normalize_text(value: str) -> str:
    """Collapse whitespace into one deterministic text string."""

    return " ".join(value.split())


def flatten_text(element: ElementTree.Element) -> str:
    """Collapse all text descendants into one whitespace-normalized string."""

    return normalize_text("".join(element.itertext()))


def bounded_text(value: str, limit: int = MAX_EXCERPT_CHARS) -> str:
    """Return a deterministic prefix bounded to parser-record field limits."""

    return value[:limit]


def diagnostic(source_path: str | None, rule: str, message: str, **extra: Any) -> dict[str, Any]:
    """Create compact deterministic diagnostics for CLI reports and tests."""

    payload: dict[str, Any] = {
        "source_path": source_path,
        "rule": rule,
        "message": message,
    }
    payload.update(extra)
    return payload


def load_consultant_fixture_manifest(root: Path = ROOT) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load the one canonical Consultant WordML fixture from S01 inventory."""

    path = root / INVENTORY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [diagnostic(str(INVENTORY_PATH), "missing-inventory", "S01 fixture inventory does not exist.")]
    except json.JSONDecodeError as exc:
        return None, [
            diagnostic(str(INVENTORY_PATH), "inventory-json-invalid", "S01 fixture inventory is not valid JSON.", error=exc.msg)
        ]

    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        return None, [diagnostic(str(INVENTORY_PATH), "inventory-shape-invalid", "Inventory fixtures must be a list.")]

    matches = [
        fixture
        for fixture in fixtures
        if isinstance(fixture, dict) and fixture.get("source_kind") == SOURCE_KIND and fixture.get("canonical") is True
    ]
    if len(matches) != 1:
        return None, [
            diagnostic(
                str(INVENTORY_PATH),
                "consultant-manifest-shape-invalid",
                "Inventory must contain exactly one canonical consultant-wordml-xml fixture.",
                actual_count=len(matches),
            )
        ]

    fixture = matches[0]
    if not isinstance(fixture.get("path"), str) or not isinstance(fixture.get("sha256"), str):
        return None, [
            diagnostic(
                str(INVENTORY_PATH),
                "consultant-manifest-shape-invalid",
                "Canonical Consultant fixture must include string path and sha256 fields.",
            )
        ]
    return fixture, []


def parse_consultant_identity(dest: str) -> dict[str, str]:
    """Extract stable Consultant URL query identity fields from w:dest."""

    query = parse_qs(urlparse(dest).query, keep_blank_values=True)
    return {key: values[0] for key, values in query.items() if values}


def object_ref_from_identity(identity: dict[str, str]) -> str | None:
    """Return a Consultant object ref when required query identity is complete."""

    if not all(identity.get(field) for field in REQUIRED_QUERY_FIELDS):
        return None
    return f"consultant:{identity['base']}:{identity['n']}@{identity['date']}"


def evidence_excerpt(link_text: str, dest: str) -> str:
    """Build bounded non-secret evidence from hyperlink text and URL."""

    return bounded_text(normalize_text(f"{link_text} — {dest}"))


def make_relation_record(
    *,
    source_path: str,
    source_sha256: str,
    hyperlink_index: int,
    link_text: str,
    dest: str,
    identity: dict[str, str],
) -> dict[str, Any]:
    """Build and validate one S02 RelationCandidateRecord payload."""

    object_ref = object_ref_from_identity(identity)
    excerpt = evidence_excerpt(link_text, dest)
    payload = {
        "record_kind": "relation_candidate",
        "id": f"REL-CONS-{hyperlink_index:04d}",
        "source_kind": SOURCE_KIND,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "source_member": None,
        "source_block_id": f"BLOCK-CONSULTANT-XML-{hyperlink_index:04d}",
        "subject_ref": f"consultant-list:{source_path}",
        "object_ref": object_ref or f"consultant:incomplete:{hyperlink_index:04d}",
        "relation_type": "consultant-list-entry",
        "status": "candidate" if object_ref is not None else "needs-review",
        "evidence_excerpt": excerpt,
        "evidence_sha256": sha256_text(excerpt),
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }
    parse_parser_record(payload)
    return payload


def candidate_report_row(record: dict[str, Any], hyperlink_index: int, identity: dict[str, str]) -> dict[str, Any]:
    """Return deterministic per-candidate report identity fields."""

    return {
        "id": record["id"],
        "source_block_id": record["source_block_id"],
        "status": record["status"],
        "selector": f"wordml:hlink[{hyperlink_index}]",
        "object_ref": record["object_ref"],
        "base": identity.get("base"),
        "n": identity.get("n"),
        "date": identity.get("date"),
        "demo": identity.get("demo"),
    }


def extract_relation_candidates(root: Path, source_path: str, expected_sha256: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Parse the canonical WordML XML fixture and return records/report rows/diagnostics."""

    source = root / source_path
    if not source.exists():
        return [], [], [diagnostic(source_path, "missing-canonical-path", "Canonical Consultant fixture path does not exist.")], None

    actual_sha256 = sha256_file(source)
    if actual_sha256 != expected_sha256:
        return (
            [],
            [],
            [
                diagnostic(
                    source_path,
                    "fixture-mismatch",
                    "Canonical Consultant fixture hash does not match source_fixture_inventory.json.",
                    expected_sha256=expected_sha256,
                    actual_sha256=actual_sha256,
                )
            ],
            actual_sha256,
        )

    try:
        tree = ElementTree.parse(source)
    except ElementTree.ParseError as exc:
        return [], [], [diagnostic(source_path, "xml-parse-error", "Failed to parse Consultant WordML XML.", error=str(exc))], actual_sha256
    except OSError as exc:
        return [], [], [diagnostic(source_path, "read-error", "Failed to read Consultant WordML XML.", error=str(exc))], actual_sha256

    records: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    dest_attr = namespaced("dest")
    for hyperlink_index, hlink in enumerate(tree.getroot().iter(namespaced("hlink")), start=1):
        dest = hlink.attrib.get(dest_attr)
        if not dest:
            diagnostics.append(
                diagnostic(
                    source_path,
                    "missing-hyperlink-dest",
                    "Consultant WordML hyperlink is missing required w:dest URL identity.",
                    selector=f"wordml:hlink[{hyperlink_index}]",
                    candidate_index=hyperlink_index,
                )
            )
            continue
        link_text = flatten_text(hlink)
        identity = parse_consultant_identity(dest)
        try:
            record = make_relation_record(
                source_path=source_path,
                source_sha256=actual_sha256,
                hyperlink_index=hyperlink_index,
                link_text=link_text,
                dest=dest,
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001 - preserve validation class/message in CLI diagnostics.
            diagnostics.append(
                diagnostic(
                    source_path,
                    "record-validation-error",
                    "S02 parser-record validation failed.",
                    selector=f"wordml:hlink[{hyperlink_index}]",
                    candidate_index=hyperlink_index,
                    error=str(exc),
                )
            )
            continue
        records.append(record)
        report_rows.append(candidate_report_row(record, hyperlink_index, identity))
    return records, report_rows, diagnostics, actual_sha256


def build_report(
    *,
    records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    source_path: str | None,
    source_sha256: str | None,
    artifact_freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a deterministic compact report for CLI and tests."""

    freshness = artifact_freshness or {"status": "not-checked", "stale_paths": [], "diagnostics": []}
    all_diagnostics = [*diagnostics, *freshness.get("diagnostics", [])]
    status = "pass" if not all_diagnostics else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/build-consultant-relation-candidates.py",
        "status": status,
        "candidate_count": len(records),
        "source_path": source_path,
        "source_sha256": source_sha256,
        "artifact_freshness": freshness,
        "diagnostic_count": len(all_diagnostics),
        "diagnostics": all_diagnostics,
        "candidates": candidates,
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }


def build_relation_candidates(root: Path = ROOT, artifact_freshness: dict[str, Any] | None = None) -> BuildResult:
    """Build candidate-only Consultant WordML relation records from the canonical fixture."""

    fixture, manifest_diagnostics = load_consultant_fixture_manifest(root)
    if fixture is None:
        report = build_report(
            records=[],
            candidates=[],
            diagnostics=manifest_diagnostics,
            source_path=None,
            source_sha256=None,
            artifact_freshness=artifact_freshness,
        )
        return BuildResult(records=[], report=report, diagnostics=report["diagnostics"])

    source_path = str(fixture["path"])
    expected_sha256 = str(fixture["sha256"])
    records, candidates, diagnostics, actual_sha256 = extract_relation_candidates(root, source_path, expected_sha256)
    report = build_report(
        records=records,
        candidates=candidates,
        diagnostics=diagnostics,
        source_path=source_path,
        source_sha256=actual_sha256,
        artifact_freshness=artifact_freshness,
    )
    return BuildResult(records=records, report=report, diagnostics=report["diagnostics"])


def jsonl_content(records: list[dict[str, Any]]) -> str:
    """Return deterministic JSONL text for relation candidates."""

    return "".join(f"{dumps_jsonl_record(record)}\n" for record in records)


def output_contents(result: BuildResult) -> dict[str, str]:
    """Return deterministic artifact contents keyed by filename."""

    return {
        RELATION_CANDIDATES_JSONL: jsonl_content(result.records),
        REPORT_JSON: json.dumps(result.report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }


def write_outputs(result: BuildResult, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """Write deterministic relation candidate artifacts to an output directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in output_contents(result).items():
        (output_dir / name).write_text(content, encoding="utf-8")


def check_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR, root: Path = ROOT) -> BuildResult:
    """Build expected outputs and byte-compare against existing artifacts."""

    initial = build_relation_candidates(root)
    expected = output_contents(initial)
    diagnostics: list[dict[str, Any]] = []
    stale_paths: list[str] = []
    for name, content in expected.items():
        path = output_dir / name
        stable_path = repo_path(path, root)
        if not path.exists():
            stale_paths.append(stable_path)
            diagnostics.append(diagnostic(None, "stale-artifact", "Expected artifact is missing or stale.", path=stable_path))
            continue
        if path.read_text(encoding="utf-8") != content:
            stale_paths.append(stable_path)
            diagnostics.append(diagnostic(None, "stale-artifact", "Expected artifact is missing or stale.", path=stable_path))
    freshness = {
        "status": "pass" if not diagnostics else "stale",
        "stale_paths": stale_paths,
        "diagnostics": diagnostics,
    }
    return build_relation_candidates(root, artifact_freshness=freshness)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic Consultant relation candidate artifacts.")
    mode.add_argument("--check", action="store_true", help="Check artifacts are fresh and print compact JSON report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Artifact directory, default prd/parser.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.write:
        result = build_relation_candidates(ROOT)
        write_outputs(result, args.output_dir)
    else:
        result = check_outputs(args.output_dir, ROOT)
    print(json.dumps(result.report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result.report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
