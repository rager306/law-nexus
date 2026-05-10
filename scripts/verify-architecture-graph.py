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
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
DEFAULT_EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
DEFAULT_REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
DEFAULT_REPORT_MD_PATH = ROOT / "prd/architecture/architecture_report.md"
SCHEMA_PATH = ROOT / "prd/architecture/architecture.schema.json"
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


def load_schema(result: VerificationResult) -> Mapping[str, Any] | None:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        result.add(
            Diagnostic(
                rule="schema-malformed-json",
                message=exc.msg,
                path=SCHEMA_PATH,
                line_number=exc.lineno,
                field="schema",
            )
        )
        return None
    except (OSError, UnicodeDecodeError) as exc:
        result.add(Diagnostic(rule="schema-read", message=str(exc), path=SCHEMA_PATH, field="schema"))
        return None
    if not isinstance(schema, Mapping):
        result.add(Diagnostic(rule="schema-object", message="expected JSON schema root object", path=SCHEMA_PATH, field="schema"))
        return None
    return schema


def resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref {ref!r}")
    current: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        if not isinstance(current, Mapping):
            raise ValueError(f"schema ref {ref!r} traversed non-object")
        current = current[part]
    if not isinstance(current, Mapping):
        raise ValueError(f"schema ref {ref!r} resolved to non-object")
    return current


def field_path(parent: str, child: str) -> str:
    if parent == "$":
        return child
    if child.startswith("["):
        return f"{parent}{child}"
    return f"{parent}.{child}"


def schema_errors(
    value: Any,
    schema_node: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    field: str = "$",
) -> list[tuple[str, str, str]]:
    if "$ref" in schema_node:
        try:
            return schema_errors(value, resolve_ref(root_schema, str(schema_node["$ref"])), root_schema, field)
        except (KeyError, ValueError) as exc:
            return [(field, "$ref", str(exc))]

    errors: list[tuple[str, str, str]] = []

    if "oneOf" in schema_node:
        option_errors = [schema_errors(value, option, root_schema, field) for option in schema_node["oneOf"]]
        passing = [candidate for candidate in option_errors if not candidate]
        if len(passing) != 1:
            details = "; ".join(error[2] for candidate in option_errors for error in candidate[:2])
            errors.append((field, "oneOf", f"expected exactly one schema branch to match; {details}"))
        return errors

    expected_type = schema_node.get("type")
    if expected_type and not type_matches(value, str(expected_type)):
        errors.append((field, f"type={expected_type}", f"expected {expected_type}, got {type(value).__name__}"))
        return errors

    if "const" in schema_node and value != schema_node["const"]:
        errors.append((field, "const", f"expected {schema_node['const']!r}, got {value!r}"))
    if "enum" in schema_node and value not in schema_node["enum"]:
        errors.append((field, "enum", f"unexpected value {value!r}"))

    if isinstance(value, str):
        if value == "" and schema_node.get("minLength", 0) >= 1:
            errors.append((field, "minLength", "expected non-empty string"))
        pattern = schema_node.get("pattern")
        if isinstance(pattern, str) and not re.search(pattern, value):
            errors.append((field, f"pattern={pattern}", f"value {value!r} does not match pattern"))
        not_schema = schema_node.get("not")
        if isinstance(not_schema, Mapping) and not schema_errors(value, not_schema, root_schema, field):
            errors.append((field, "not", f"value {value!r} matched forbidden schema"))
        if schema_node.get("format") == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            errors.append((field, "format=date", f"value {value!r} is not YYYY-MM-DD"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema_node.get("minimum")
        maximum = schema_node.get("maximum")
        if minimum is not None and value < minimum:
            errors.append((field, f"minimum={minimum}", f"value {value!r} is too small"))
        if maximum is not None and value > maximum:
            errors.append((field, f"maximum={maximum}", f"value {value!r} is too large"))

    if isinstance(value, list):
        min_items = schema_node.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append((field, f"minItems={min_items}", f"array has {len(value)} items"))
        if schema_node.get("uniqueItems") and not array_items_are_unique(value):
            errors.append((field, "uniqueItems", "array contains duplicate entries"))
        item_schema = schema_node.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, item_schema, root_schema, f"{field}[{index}]"))

    if isinstance(value, Mapping):
        required = schema_node.get("required", [])
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    errors.append((field_path(field, key), "required", "missing required field"))
        properties = schema_node.get("properties", {})
        if not isinstance(properties, Mapping):
            properties = {}
        if schema_node.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append((field_path(field, str(key)), "additionalProperties=false", "unexpected field"))
        for key, property_schema in properties.items():
            if key in value and isinstance(property_schema, Mapping):
                errors.extend(schema_errors(value[key], property_schema, root_schema, field_path(field, str(key))))
        for condition in schema_node.get("allOf", []):
            if isinstance(condition, Mapping):
                if_errors = schema_errors(value, condition.get("if", {}), root_schema, field) if isinstance(condition.get("if", {}), Mapping) else []
                if not if_errors:
                    then_schema = condition.get("then")
                    if isinstance(then_schema, Mapping):
                        errors.extend(schema_errors(value, then_schema, root_schema, field))

    return errors


def type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, Mapping)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"unsupported schema type {expected_type!r}")


def array_items_are_unique(items: list[Any]) -> bool:
    seen: set[str] = set()
    for item in items:
        marker = json.dumps(item, sort_keys=True)
        if marker in seen:
            return False
        seen.add(marker)
    return True


def schema_node_for_record(schema: Mapping[str, Any], located: LocatedRecord) -> Mapping[str, Any]:
    if located.record_kind == "item":
        return resolve_ref(schema, "#/$defs/item")
    if located.record_kind == "edge":
        return resolve_ref(schema, "#/$defs/edge")
    return schema


def validate_schema(records: list[LocatedRecord], schema: Mapping[str, Any], result: VerificationResult) -> None:
    for located in records:
        try:
            schema_node = schema_node_for_record(schema, located)
            errors = schema_errors(located.record, schema_node, schema)
        except (KeyError, ValueError) as exc:
            result.add(located.diagnostic("schema-validator", str(exc), field="schema"))
            continue
        for field, rule, message in errors:
            result.add(located.diagnostic(rule, message, field=field))


def source_anchor_path_is_local(anchor_path: str) -> bool:
    path = Path(anchor_path)
    if path.is_absolute():
        return False
    parts = path.parts
    if ".." in parts:
        return False
    return not (len(parts) >= 2 and parts[0] == ".gsd" and parts[1] == "exec")


def read_anchor_lines(anchor_path: str, cache: dict[str, tuple[Path, list[str]]]) -> tuple[Path, list[str]] | None:
    if anchor_path in cache:
        return cache[anchor_path]
    full_path = ROOT / anchor_path
    try:
        lines = full_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    cache[anchor_path] = (full_path, lines)
    return cache[anchor_path]


def validate_source_anchors(records: list[LocatedRecord], result: VerificationResult) -> None:
    cache: dict[str, tuple[Path, list[str]]] = {}
    for located in records:
        anchors = located.record.get("source_anchors")
        if not isinstance(anchors, list):
            continue
        for index, anchor in enumerate(anchors):
            field_prefix = f"source_anchors[{index}]"
            if not isinstance(anchor, Mapping):
                continue
            raw_path = anchor.get("path")
            if not isinstance(raw_path, str) or not raw_path:
                continue
            if not source_anchor_path_is_local(raw_path):
                result.add(
                    located.diagnostic(
                        "source-anchor-path-local",
                        "source anchor path must be repository-relative and outside .gsd/exec",
                        field=f"{field_prefix}.path",
                    )
                )
                continue
            cached = read_anchor_lines(raw_path, cache)
            if cached is None:
                result.add(
                    located.diagnostic(
                        "source-anchor-exists",
                        "source anchor file is missing or unreadable",
                        field=f"{field_prefix}.path",
                    )
                )
                continue
            _, lines = cached
            line_start = anchor.get("line_start")
            line_end = anchor.get("line_end")
            if isinstance(line_start, int) and isinstance(line_end, int):
                if line_start > line_end:
                    result.add(
                        located.diagnostic(
                            "source-anchor-line-range",
                            "line_start must be less than or equal to line_end",
                            field=f"{field_prefix}.line_start",
                        )
                    )
                if line_end > len(lines):
                    result.add(
                        located.diagnostic(
                            "source-anchor-line-range",
                            f"line_end exceeds file length {len(lines)}",
                            field=f"{field_prefix}.line_end",
                        )
                    )
            elif isinstance(line_start, int) and line_start > len(lines):
                result.add(
                    located.diagnostic(
                        "source-anchor-line-range",
                        f"line_start exceeds file length {len(lines)}",
                        field=f"{field_prefix}.line_start",
                    )
                )
            elif isinstance(line_end, int) and line_end > len(lines):
                result.add(
                    located.diagnostic(
                        "source-anchor-line-range",
                        f"line_end exceeds file length {len(lines)}",
                        field=f"{field_prefix}.line_end",
                    )
                )
            text = "\n".join(lines)
            for token_field in ("selector", "section"):
                token = anchor.get(token_field)
                if isinstance(token, str) and token not in text:
                    result.add(
                        located.diagnostic(
                            "source-anchor-token",
                            f"{token_field} text does not appear in anchored file",
                            field=f"{field_prefix}.{token_field}",
                        )
                    )


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
    all_records = [*item_records, *edge_records]
    result.items = len(item_records)
    result.edges = len(edge_records)
    schema = load_schema(result)
    if schema is not None:
        validate_schema(all_records, schema, result)
    validate_source_anchors(all_records, result)
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
