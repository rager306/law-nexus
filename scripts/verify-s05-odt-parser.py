#!/usr/bin/env python3
"""Verify M001/S05 ODT parser findings against the real probe log.

The verifier is intentionally stdlib-only. It checks that parser direction and
Old_project reuse findings stay tied to the real Garant ODT smoke probe, carry
owners/resolution/verification fields, and avoid product ETL claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REAL_SOURCE_PATH = "law-source/garant/44-fz.odt"
REQUIRED_OLD_PROJECT_PATHS = (
    "Old_project/structures/44fz.yaml",
    "Old_project/parsing_prompt.yaml",
    "Old_project/validation/structural_rules.yaml",
    "Old_project/validation/semantic_rules.yaml",
    "Old_project/contracts/api.yaml",
    "Old_project/contracts/extractor-api.md",
    "Old_project/sources/consultant_word2003xml.yaml",
)

RAW_ALLOWED_STATUSES = {"verified-source-evidence"}
OPTIONAL_ALLOWED_STATUSES = {
    "not-installed",
    "api-incomplete",
    "loaded-unmodified",
    "loaded-temp-clean-manifest",
    "failed-unmodified-load",
    "failed-temp-clean-load",
}
ALLOWED_EVIDENCE_CLASSES = {
    "verified-source-evidence",
    "parser-comparison-evidence",
    "parser-error",
    "policy-error",
}
REQUIRED_SECTIONS = (
    "parser direction",
    "real odt evidence",
    "old_project reuse classification",
    "issues",
    "owners",
    "resolution paths",
    "verification criteria",
)
REQUIRED_TABLE_FIELDS = ("owner", "resolution", "verification")
PRODUCT_ETL_CLAIMS = (
    "ready for product etl",
    "implements product etl",
    "authoritative legal facts",
    "validated: true",
    "keep-as-is reusable",
)


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


@dataclass(frozen=True)
class MarkdownTable:
    headers: list[str]
    rows: list[dict[str, str]]


def load_json(path: Path, result: VerificationResult) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result.add(f"Probe JSON log is missing: {path}")
    except json.JSONDecodeError as exc:
        result.add(f"Probe JSON log is invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
    return None


def load_text(path: Path, result: VerificationResult) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.add(f"Findings markdown is missing: {path}")
    return None


def normalize_cell(value: str) -> str:
    return " ".join(value.strip().strip("`").split())


def split_table_line(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [normalize_cell(cell) for cell in stripped.split("|")]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(cell.replace(":", "").replace("-", "")) <= set() for cell in cells)


def parse_markdown_tables(markdown: str) -> list[MarkdownTable]:
    lines = markdown.splitlines()
    tables: list[MarkdownTable] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            index += 1
            continue
        headers = split_table_line(line)
        if index + 1 >= len(lines):
            index += 1
            continue
        separator = split_table_line(lines[index + 1])
        if not is_separator(separator):
            index += 1
            continue
        rows: list[dict[str, str]] = []
        index += 2
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            cells = split_table_line(lines[index])
            row = {header.lower(): cells[pos] if pos < len(cells) else "" for pos, header in enumerate(headers)}
            rows.append(row)
            index += 1
        tables.append(MarkdownTable(headers=[header.lower() for header in headers], rows=rows))
    return tables


def find_row(tables: list[MarkdownTable], needle: str) -> dict[str, str] | None:
    for table in tables:
        for row in table.rows:
            if any(value == needle for value in row.values()):
                return row
    return None


def row_field(row: dict[str, str], *needles: str) -> str:
    for key, value in row.items():
        lowered = key.lower()
        if any(needle in lowered for needle in needles):
            return value.strip()
    return ""


def validate_probe_log(payload: dict[str, Any], result: VerificationResult) -> None:
    statuses = payload.get("statuses")
    if not isinstance(statuses, dict):
        result.add("Probe JSON log is missing required object key: statuses")
        statuses = {}

    probes = payload.get("probes")
    if not isinstance(probes, list):
        result.add("Probe JSON log is missing required list key: probes")
        probes = []

    probe_log_path = payload.get("probe_log_path")
    if not isinstance(probe_log_path, str) or not probe_log_path.startswith(".gsd/"):
        result.add("Probe JSON log must include normalized .gsd/... probe_log_path")

    raw_status = statuses.get("raw-baseline")
    if raw_status not in RAW_ALLOWED_STATUSES:
        result.add("Probe statuses.raw-baseline must be verified-source-evidence for real source evidence")

    odfpy_status = statuses.get("odfpy")
    if odfpy_status is None:
        result.add("Probe statuses is missing odfpy parser status")
    elif odfpy_status not in OPTIONAL_ALLOWED_STATUSES:
        result.add(f"Probe statuses.odfpy has unsupported status: {odfpy_status}")

    alternative_names = [name for name in statuses if name not in {"raw-baseline", "odfpy"}]
    if not alternative_names:
        result.add("Probe statuses is missing an alternative parser status such as odfdo")
    for name in alternative_names:
        status = statuses.get(name)
        if status not in OPTIONAL_ALLOWED_STATUSES:
            result.add(f"Probe statuses.{name} has unsupported status: {status}")

    raw_probe = next(
        (
            probe
            for probe in probes
            if probe.get("status") == "verified-source-evidence"
            or probe.get("parser") in {"raw-baseline", "raw"}
        ),
        None,
    )
    if not isinstance(raw_probe, dict):
        result.add("Probe JSON log is missing raw verified-source-evidence probe")
    else:
        source = raw_probe.get("source")
        if not isinstance(source, dict):
            result.add("Raw probe is missing source metadata object")
        else:
            if source.get("path") != REAL_SOURCE_PATH:
                result.add(f"Raw probe must use real source path {REAL_SOURCE_PATH}; got {source.get('path')!r}")
            sha256 = source.get("sha256")
            if not isinstance(sha256, str) or len(sha256) != 64:
                result.add("Raw probe source metadata must include a 64-character sha256")
            if not source.get("size_bytes"):
                result.add("Raw probe source metadata must include non-zero size_bytes")
        if raw_probe.get("evidence_class") != "verified-source-evidence":
            result.add("Raw probe evidence_class must be verified-source-evidence")
        if raw_probe.get("parser_direction_claims_authoritative") is not False:
            result.add("Raw probe must keep parser_direction_claims_authoritative false")

    parsers_seen = {probe.get("parser") for probe in probes if isinstance(probe, dict)}
    if "odfpy" not in parsers_seen:
        result.add("Probe JSON log is missing odfpy probe entry")
    if not any(parser not in {None, "raw", "raw-baseline", "odfpy"} for parser in parsers_seen):
        result.add("Probe JSON log is missing alternative parser probe entry")

    for probe in probes:
        if not isinstance(probe, dict):
            result.add("Probe JSON log contains a non-object probe entry")
            continue
        status = probe.get("status")
        parser = probe.get("parser", "raw-baseline")
        allowed = RAW_ALLOWED_STATUSES if parser in {"raw", "raw-baseline"} else OPTIONAL_ALLOWED_STATUSES
        if status not in allowed:
            result.add(f"Probe {parser} has unsupported status: {status}")
        evidence_class = probe.get("evidence_class")
        if evidence_class not in ALLOWED_EVIDENCE_CLASSES:
            result.add(f"Probe {parser} has unsupported evidence_class: {evidence_class}")
        issue_ids = probe.get("issue_ids")
        if not isinstance(issue_ids, list) or not all(isinstance(issue_id, str) and issue_id for issue_id in issue_ids):
            result.add(f"Probe {parser} must include non-empty issue_ids")


def validate_findings(markdown: str, probe_payload: dict[str, Any], result: VerificationResult) -> None:
    lowered = markdown.lower()
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in lowered:
            result.add(f"Findings markdown is missing required section: {section}")

    for phrase in PRODUCT_ETL_CLAIMS:
        if phrase in lowered:
            result.add(f"Findings markdown contains architecture-boundary violation: {phrase}")

    if "odfpy is accepted as the sole parser" in lowered or "odfpy accepted as the sole parser" in lowered:
        result.add("Findings must not accept odfpy as the sole parser after unmodified-load failure")
    if "unmodified-load" not in lowered and "unmodified load" not in lowered:
        result.add("Findings must mention the odfpy unmodified-load manifest issue")
    if "manifest" not in lowered:
        result.add("Findings must include the manifest issue for odfpy comparison")
    if REAL_SOURCE_PATH not in markdown:
        result.add(f"Findings must cite real ODT evidence path {REAL_SOURCE_PATH}")
    if ".gsd/" not in markdown:
        result.add("Findings must cite normalized .gsd/... artifact paths")
    if "prior art" not in lowered:
        result.add("Findings must classify Old_project as prior art, not trusted implementation")

    tables = parse_markdown_tables(markdown)
    validate_old_project_rows(tables, result)
    validate_issue_rows(tables, probe_payload, result)
    validate_alternative_blocked(markdown, probe_payload, result)


def validate_old_project_rows(tables: list[MarkdownTable], result: VerificationResult) -> None:
    found_any = False
    for path in REQUIRED_OLD_PROJECT_PATHS:
        row = find_row(tables, path)
        if row is None:
            result.add(f"Old_project classification table is missing required candidate: {path}")
            continue
        found_any = True
        for field_name in REQUIRED_TABLE_FIELDS:
            if not row_field(row, field_name):
                result.add(f"Old_project candidate {path} lacks {field_name} field")
        if not Path(path).exists():
            result.add(f"Old_project evidence file required by findings table does not exist: {path}")
    if not found_any:
        result.add("Findings markdown is missing the required Old_project classification table")


def validate_issue_rows(tables: list[MarkdownTable], probe_payload: dict[str, Any], result: VerificationResult) -> None:
    issue_ids: set[str] = set()
    for probe in probe_payload.get("probes", []):
        if not isinstance(probe, dict):
            continue
        for issue_id in probe.get("issue_ids", []):
            if isinstance(issue_id, str):
                issue_ids.add(issue_id)

    for issue_id in sorted(issue_ids):
        row = find_row(tables, issue_id)
        if row is None:
            result.add(f"Findings issues table is missing probe issue {issue_id}")
            continue
        for field_name in REQUIRED_TABLE_FIELDS:
            if not row_field(row, field_name):
                result.add(f"Findings issue {issue_id} lacks {field_name} field")


def validate_alternative_blocked(markdown: str, probe_payload: dict[str, Any], result: VerificationResult) -> None:
    statuses = probe_payload.get("statuses", {})
    if not isinstance(statuses, dict):
        return
    alternative_statuses = {
        parser: status
        for parser, status in statuses.items()
        if parser not in {"raw-baseline", "odfpy"}
    }
    if any(status == "not-installed" for status in alternative_statuses.values()):
        lowered = markdown.lower()
        has_blocked = "blocked" in lowered and "alternative parser" in lowered
        has_resolution = "resolution path" in lowered or "resolution:" in lowered
        if not (has_blocked and has_resolution):
            result.add("alternative parser is not-installed; findings must mark comparison blocked and provide a resolution path")


def verify(findings: Path | str, probe_log: Path | str) -> VerificationResult:
    result = VerificationResult()
    probe_payload = load_json(Path(probe_log), result)
    markdown = load_text(Path(findings), result)
    if probe_payload is None or markdown is None:
        return result
    validate_probe_log(probe_payload, result)
    validate_findings(markdown, probe_payload, result)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", required=True, type=Path, help="S05 findings markdown path")
    parser.add_argument("--probe-log", required=True, type=Path, help="S05 machine-readable probe JSON log")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = verify(args.findings, args.probe_log)
    if result.ok:
        print("S05 ODT parser findings verification passed")
        return 0
    print("S05 ODT parser findings verification failed:", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
