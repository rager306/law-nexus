#!/usr/bin/env python3
"""Verify derived architecture graph artifacts without authoring claims.

This S04 verifier is a deterministic policy surface over the generated S02/S03
architecture registry and graph reports. It is read-only: default-path runs first
compose the upstream ``--check`` freshness gates, then local verifier rules inspect
JSONL shape and emit compact diagnostics plus a non-authoritative summary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
DEFAULT_EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
DEFAULT_REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
DEFAULT_REPORT_MD_PATH = ROOT / "prd/architecture/architecture_report.md"
RecordKind = Literal["item", "edge"]
LAST_RESULT: VerificationResult | None = None


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    message: str
    path: Path
    line_number: int = 0
    record_id: str = "<none>"
    record_kind: str = "<none>"
    field: str = "<none>"
    source_anchor: str = "<none>"

    def format(self) -> str:
        return (
            f"{display_path(self.path)}:{self.line_number} "
            f"id={self.record_id} record_kind={self.record_kind} field={self.field} "
            f"rule={self.rule} source_anchor={self.source_anchor} message={self.message}"
        )


@dataclass(frozen=True)
class LocatedRecord:
    path: Path
    line_number: int
    record: dict[str, Any]

    @property
    def record_id(self) -> str:
        value = self.record.get("id")
        return value if isinstance(value, str) and value else "<missing-id>"

    @property
    def record_kind(self) -> str:
        value = self.record.get("record_kind")
        return value if isinstance(value, str) and value else "<missing-record-kind>"

    @property
    def source_anchor(self) -> str:
        anchors = self.record.get("source_anchors")
        if not isinstance(anchors, list) or not anchors:
            return "<no-source-anchor>"
        first = anchors[0]
        if not isinstance(first, dict):
            return "<malformed-source-anchor>"
        path = first.get("path", "<missing-path>")
        selector = first.get("selector") or first.get("section") or first.get("line_start")
        return f"{path}#{selector}" if selector else str(path)

    def diagnostic(self, rule: str, message: str, *, field: str = "<none>") -> Diagnostic:
        return Diagnostic(
            rule=rule,
            message=message,
            path=self.path,
            line_number=self.line_number,
            record_id=self.record_id,
            record_kind=self.record_kind,
            field=field,
            source_anchor=self.source_anchor,
        )


@dataclass
class VerificationResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    items: int = 0
    edges: int = 0
    upstream_checks: str = "not-run"

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    def add(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def summary(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.ok else "fail",
            "failure_count": len(self.diagnostics),
            "items": self.items,
            "edges": self.edges,
            "upstream_checks": self.upstream_checks,
            "non_authoritative": True,
            "boundary": "Verifier output is derived and non-authoritative; source evidence remains authoritative.",
        }


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def is_default_path(path: Path, default: Path) -> bool:
    try:
        return path.resolve() == default.resolve()
    except OSError:
        return path.absolute() == default.absolute()


def first_actionable_line(stdout: str, stderr: str) -> str:
    for line in [*stderr.splitlines(), *stdout.splitlines()]:
        stripped = line.strip()
        if stripped:
            return stripped
    return "upstream check failed without output"


def run_upstream_check(rule: str, command: list[str], path: Path, timeout_seconds: int = 30) -> Diagnostic | None:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        error = exc.stderr if isinstance(exc.stderr, str) else ""
        return Diagnostic(rule=rule, message=f"timeout after {timeout_seconds}s: {first_actionable_line(output, error)}", path=path)
    except OSError as exc:
        return Diagnostic(rule=rule, message=str(exc), path=path)

    if completed.returncode != 0:
        return Diagnostic(rule=rule, message=first_actionable_line(completed.stdout, completed.stderr), path=path)
    return None


def should_run_default_freshness(args: argparse.Namespace) -> bool:
    return (
        is_default_path(args.items, DEFAULT_ITEMS_PATH)
        and is_default_path(args.edges, DEFAULT_EDGES_PATH)
        and is_default_path(args.report_json, DEFAULT_REPORT_JSON_PATH)
        and is_default_path(args.report_md, DEFAULT_REPORT_MD_PATH)
    )


def run_upstream_freshness(args: argparse.Namespace, result: VerificationResult) -> None:
    if not should_run_default_freshness(args):
        result.upstream_checks = "skipped-custom-paths"
        return

    checks = [
        (
            "upstream-s02-check",
            [sys.executable, "scripts/extract-prd-architecture-items.py", "--check"],
            args.items,
        ),
        (
            "upstream-s03-check",
            [sys.executable, "scripts/build-architecture-graph.py", "--check"],
            args.report_json,
        ),
    ]
    for rule, command, path in checks:
        diagnostic = run_upstream_check(rule, command, path)
        if diagnostic:
            result.add(diagnostic)
    result.upstream_checks = "passed" if result.ok else "failed"


def load_jsonl(path: Path, *, expected_kind: RecordKind, result: VerificationResult) -> list[LocatedRecord]:
    located: list[LocatedRecord] = []
    seen_ids: dict[str, LocatedRecord] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        result.add(Diagnostic(rule="read-jsonl", message=str(exc), path=path))
        return located

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except JSONDecodeError as exc:
            result.add(
                Diagnostic(
                    rule="malformed-jsonl",
                    message=exc.msg,
                    path=path,
                    line_number=line_number,
                    record_id="<unknown>",
                    record_kind="<unknown>",
                )
            )
            continue
        if not isinstance(record, dict):
            result.add(
                Diagnostic(
                    rule="jsonl-object",
                    message="expected each JSONL record to be an object",
                    path=path,
                    line_number=line_number,
                    record_id="<unknown>",
                    record_kind="<unknown>",
                )
            )
            continue

        current = LocatedRecord(path=path, line_number=line_number, record=record)
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            result.add(current.diagnostic("record-id", "expected non-empty string record id", field="id"))
        elif record_id in seen_ids:
            first = seen_ids[record_id]
            result.add(
                current.diagnostic(
                    "duplicate-id",
                    f"record id already appeared in this file at line {first.line_number}",
                    field="id",
                )
            )
        else:
            seen_ids[record_id] = current

        if current.record_kind != expected_kind:
            result.add(
                current.diagnostic(
                    "record-kind",
                    f"expected record_kind={expected_kind}",
                    field="record_kind",
                )
            )

        located.append(current)

    return located


def verify_report_paths(args: argparse.Namespace, result: VerificationResult) -> None:
    for path, rule in [(args.report_json, "report-json"), (args.report_md, "report-md")]:
        if not path.exists():
            result.add(Diagnostic(rule=rule, message="expected report output to exist", path=path))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify derived, non-authoritative architecture graph artifacts without rewriting them."
    )
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD_PATH)
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    global LAST_RESULT
    args = parse_args(argv)
    result = VerificationResult()

    run_upstream_freshness(args, result)
    item_records = load_jsonl(args.items, expected_kind="item", result=result)
    edge_records = load_jsonl(args.edges, expected_kind="edge", result=result)
    result.items = len(item_records)
    result.edges = len(edge_records)
    verify_report_paths(args, result)

    LAST_RESULT = result
    if result.diagnostics:
        for diagnostic in sorted(result.diagnostics, key=lambda item: (item.rule, display_path(item.path), item.line_number, item.record_id)):
            print(diagnostic.format(), file=sys.stderr)
        print(json.dumps(result.summary(), sort_keys=True))
        return 1

    print(json.dumps(result.summary(), sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
