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
DEFAULT_POLICY_DOC_PATH = ROOT / "prd/architecture/README.md"
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


TRACEABILITY_CRITICAL_TYPES = {"requirement", "decision", "proof_gate"}
TRACEABILITY_EXEMPT_STATUSES = {"out-of-scope", "rejected"}
DECISION_FITNESS_EDGE_TYPES = {"checked_by", "validated_by"}
DECISION_FITNESS_EDGE_STATUSES = {"active", "hypothesis", "validated"}
DECISION_FITNESS_TARGET_TYPES = {"proof_gate", "workflow_check"}
HARD_CONTRADICTION_STATUSES = {"active", "hypothesis", "bounded-evidence"}
PROSE_CLAIM_FIELDS = {
    "title",
    "summary",
    "verification",
    "rationale",
    "positive_consequences",
    "negative_consequences",
    "decision_drivers",
    "assumptions",
    "constraints",
    "implications",
}
PROSE_OPTION_FIELDS = {"title", "summary", "pros", "cons"}
OVERCLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "LegalGraph product promotion",
        re.compile(r"\bLegalGraph\s+product\b[^\n.]{0,100}\b(?:production\s+ready|ready\s+for\s+production|implemented|shipped|validated|proven)\b", re.I),
    ),
    (
        "Legal KnowQL runtime/parser proof",
        re.compile(r"\bLegal\s+KnowQL\b[^\n.]{0,100}\b(?:runtime|parser)\b[^\n.]{0,100}\b(?:proven|validated|production\s+ready|complete|safe)\b", re.I),
    ),
    (
        "ODT parser completeness",
        re.compile(r"\bODT\s+parser\b[^\n.]{0,100}\b(?:complete|proven|validated|production\s+ready|authoritative)\b", re.I),
    ),
    (
        "retrieval quality proof",
        re.compile(r"\bretrieval\s+quality\b[^\n.]{0,100}\b(?:proven|validated|confirmed|production\s+ready|guaranteed)\b", re.I),
    ),
    (
        "FalkorDB production scale proof",
        re.compile(r"\bFalkorDB\b[^\n.]{0,100}\bproduction\s+scale\b[^\n.]{0,100}\b(?:proven|validated|confirmed|ready|supported)\b", re.I),
    ),
    (
        "generated Cypher safety proof",
        re.compile(r"\bgenerated\s+Cypher\b[^\n.]{0,100}\b(?:safe|safety\s+(?:is\s+)?(?:proven|validated|guaranteed)|validated|proven|guaranteed)\b", re.I),
    ),
    (
        "legal answer correctness",
        re.compile(r"\blegal\s+answers?\b[^\n.]{0,100}\b(?:correct|validated|authoritative|guaranteed|legally\s+sound)\b", re.I),
    ),
    (
        "LLM authority",
        re.compile(r"\bLLM(?:\s+output)?\b[^\n.]{0,80}\b(?:is|are|acts?\s+as|serves?\s+as|becomes?|creates?)\b[^\n.]{0,40}\b(?:authoritative|legal\s+authority|binding|legal\s+facts?)\b", re.I),
    ),
)


@dataclass
class GraphIndex:
    items_by_id: dict[str, LocatedRecord]
    edges: list[LocatedRecord]
    incoming: dict[str, list[LocatedRecord]] = field(default_factory=dict)
    outgoing: dict[str, list[LocatedRecord]] = field(default_factory=dict)

    def connected_edges(self, record_id: str) -> list[LocatedRecord]:
        return [*self.incoming.get(record_id, []), *self.outgoing.get(record_id, [])]


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def build_graph_index(item_records: list[LocatedRecord], edge_records: list[LocatedRecord], result: VerificationResult) -> GraphIndex:
    items_by_id = {
        located.record_id: located
        for located in item_records
        if located.record_id != "<missing-id>" and located.record_kind == "item"
    }
    index = GraphIndex(items_by_id=items_by_id, edges=edge_records)

    for edge in edge_records:
        if edge.record_kind != "edge":
            continue
        from_id = edge.record.get("from")
        to_id = edge.record.get("to")
        if isinstance(from_id, str) and from_id:
            index.outgoing.setdefault(from_id, []).append(edge)
        if isinstance(to_id, str) and to_id:
            index.incoming.setdefault(to_id, []).append(edge)
        for field_name, endpoint in (("from", from_id), ("to", to_id)):
            if isinstance(endpoint, str) and endpoint and endpoint not in items_by_id:
                result.add(
                    edge.diagnostic(
                        "missing-endpoint",
                        f"edge references absent endpoint {endpoint}",
                        field=field_name,
                    )
                )
    return index


def item_status(located: LocatedRecord) -> str:
    value = located.record.get("status")
    return value if isinstance(value, str) else "<missing-status>"


def item_type(located: LocatedRecord) -> str:
    value = located.record.get("type")
    return value if isinstance(value, str) else "<missing-type>"


def item_is_traceability_exempt(located: LocatedRecord) -> bool:
    if located.record.get("generated_draft") is True:
        return True
    return item_status(located) in TRACEABILITY_EXEMPT_STATUSES


def validate_orphan_traceability(index: GraphIndex, result: VerificationResult) -> None:
    for record_id, located in sorted(index.items_by_id.items()):
        if item_type(located) not in TRACEABILITY_CRITICAL_TYPES:
            continue
        if item_is_traceability_exempt(located):
            continue
        if index.connected_edges(record_id):
            continue
        result.add(
            located.diagnostic(
                "orphan-traceability",
                "traceability-critical item has no meaningful incoming or outgoing architecture edge",
                field="id",
            )
        )


def validate_proof_gate_metadata(item_records: list[LocatedRecord], result: VerificationResult) -> None:
    for located in item_records:
        if item_type(located) != "proof_gate":
            continue
        if item_status(located) != "active" or located.record.get("proof_level") != "none":
            continue
        required_fields = [
            ("owner", non_empty_string(located.record.get("owner"))),
            ("status", non_empty_string(located.record.get("status"))),
            ("verification", non_empty_string(located.record.get("verification"))),
            ("source_anchors", non_empty_list(located.record.get("source_anchors"))),
        ]
        for field_name, is_present in required_fields:
            if not is_present:
                result.add(
                    located.diagnostic(
                        "proof-gate-metadata",
                        "active unresolved proof_gate with proof_level=none must retain owner, status, verification, and source anchors",
                        field=field_name,
                    )
                )


def decision_has_consequence(located: LocatedRecord) -> bool:
    return non_empty_list(located.record.get("positive_consequences")) or non_empty_list(located.record.get("negative_consequences"))


def edge_endpoint(edge: LocatedRecord, field_name: str) -> str | None:
    value = edge.record.get(field_name)
    return value if isinstance(value, str) and value else None


def active_supersession_edge_exists(decision_id: str, successor_id: str, index: GraphIndex) -> bool:
    successor = index.items_by_id.get(successor_id)
    if successor is None or item_status(successor) != "active":
        return False
    for edge in index.connected_edges(decision_id):
        if edge.record.get("status") != "active":
            continue
        edge_type = edge.record.get("type")
        from_id = edge_endpoint(edge, "from")
        to_id = edge_endpoint(edge, "to")
        if edge_type == "supersedes" and from_id == successor_id and to_id == decision_id:
            return True
        if edge_type == "superseded_by" and from_id == decision_id and to_id == successor_id:
            return True
    return False


def decision_has_gate_coverage(decision_id: str, index: GraphIndex) -> bool:
    for edge in index.outgoing.get(decision_id, []):
        if edge.record.get("type") not in DECISION_FITNESS_EDGE_TYPES:
            continue
        if edge.record.get("status") not in DECISION_FITNESS_EDGE_STATUSES:
            continue
        target_id = edge_endpoint(edge, "to")
        if target_id is None:
            continue
        target = index.items_by_id.get(target_id)
        if target is not None and item_type(target) in DECISION_FITNESS_TARGET_TYPES:
            return True
    return False


def validate_decision_policies(index: GraphIndex, result: VerificationResult) -> None:
    for record_id, located in sorted(index.items_by_id.items()):
        if item_type(located) != "decision":
            continue
        status = item_status(located)
        if status == "active" and not decision_has_consequence(located):
            result.add(
                located.diagnostic(
                    "decision-consequence",
                    "active decision must document at least one positive or negative consequence",
                    field="positive_consequences",
                )
            )
        if status == "superseded":
            successor_id = located.record.get("superseded_by")
            if not isinstance(successor_id, str) or not successor_id:
                result.add(
                    located.diagnostic(
                        "decision-supersession",
                        "superseded decision must name superseded_by successor and have active supersession edge coverage",
                        field="superseded_by",
                    )
                )
            elif not active_supersession_edge_exists(record_id, successor_id, index):
                result.add(
                    located.diagnostic(
                        "decision-supersession",
                        "superseded decision must have active supersession edge coverage to its active successor",
                        field="superseded_by",
                    )
                )
        if status == "active" and located.record.get("risk_level") in {"high", "critical"} and not decision_has_gate_coverage(record_id, index):
            result.add(
                located.diagnostic(
                    "decision-fitness",
                    "high or critical active decision must be checked_by or validated_by a proof_gate or workflow_check",
                    field="risk_level",
                )
            )


def validate_active_contradictions(edge_records: list[LocatedRecord], result: VerificationResult) -> None:
    for edge in edge_records:
        if edge.record.get("type") != "contradicts":
            continue
        status = edge.record.get("status")
        if status in HARD_CONTRADICTION_STATUSES:
            result.add(
                edge.diagnostic(
                    "active-contradiction",
                    "contradicts edges in active, hypothesis, or bounded-evidence status must be resolved, rejected, or superseded",
                    field="status",
                )
            )


def is_negated_guardrail(text: str, match: re.Match[str]) -> bool:
    sentence_start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start())) + 1
    next_period = text.find(".", match.end())
    sentence_end = next_period if next_period != -1 else len(text)
    prefix = text[sentence_start : match.start()].strip().lower()
    sentence = text[sentence_start:sentence_end].strip().lower()
    return (
        prefix.endswith("no")
        or prefix.endswith("not")
        or prefix.endswith("never")
        or prefix.endswith("without")
        or sentence.startswith("no ")
        or sentence.startswith("not ")
        or sentence.startswith("do not ")
        or sentence.startswith("does not ")
        or sentence.startswith("must not ")
        or sentence.startswith("cannot ")
        or sentence.startswith("is not ")
        or " is not " in sentence
        or " are not " in sentence
        or " must not " in sentence
        or " does not " in sentence
        or " do not " in sentence
        or " cannot " in sentence
        or " without " in sentence[:80]
        or " no " in sentence[:80]
    )


def iter_string_values(field: str, value: Any) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(field, value)]
    if isinstance(value, list):
        values: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            item_field = f"{field}[{index}]"
            if isinstance(item, str):
                values.append((item_field, item))
            elif isinstance(item, Mapping):
                for key, nested in item.items():
                    if key in PROSE_OPTION_FIELDS:
                        values.extend(iter_string_values(f"{item_field}.{key}", nested))
            # Other nested structures are intentionally ignored to avoid scanning IDs/paths.
        return values
    return []


def iter_record_claim_text(located: LocatedRecord) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for field_name, value in located.record.items():
        if field_name == "non_claims":
            continue
        if field_name in PROSE_CLAIM_FIELDS:
            values.extend(iter_string_values(field_name, value))
        elif field_name == "considered_options":
            values.extend(iter_string_values(field_name, value))
    return values


def first_forbidden_overclaim(text: str) -> tuple[str, str] | None:
    for label, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(text):
            if is_negated_guardrail(text, match):
                continue
            snippet = " ".join(match.group(0).split())
            return label, snippet
    return None


def validate_record_overclaims(records: list[LocatedRecord], result: VerificationResult) -> None:
    for located in records:
        for field_name, text in iter_record_claim_text(located):
            match = first_forbidden_overclaim(text)
            if match is None:
                continue
            label, snippet = match
            result.add(
                located.diagnostic(
                    "forbidden-overclaim",
                    f"positive unsafe architecture claim ({label}): {snippet}",
                    field=field_name,
                )
            )


def line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def validate_text_file_overclaims(path: Path, result: VerificationResult, *, record_kind: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeDecodeError) as exc:
        result.add(Diagnostic(rule="read-claim-text", message=str(exc), path=path, record_kind=record_kind, field="text"))
        return
    for label, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(text):
            if is_negated_guardrail(text, match):
                continue
            snippet = " ".join(match.group(0).split())
            result.add(
                Diagnostic(
                    rule="forbidden-overclaim",
                    message=f"positive unsafe architecture claim ({label}): {snippet}",
                    path=path,
                    line_number=line_number_for_offset(text, match.start()),
                    record_id=display_path(path),
                    record_kind=record_kind,
                    field="text",
                    source_anchor=display_path(path),
                )
            )
            break


def validate_overclaim_policies(records: list[LocatedRecord], args: argparse.Namespace, result: VerificationResult) -> None:
    validate_record_overclaims(records, result)
    validate_text_file_overclaims(args.report_md, result, record_kind="derived-report")
    for policy_doc in args.policy_doc:
        validate_text_file_overclaims(policy_doc, result, record_kind="policy-doc")


def validate_graph_policies(item_records: list[LocatedRecord], edge_records: list[LocatedRecord], result: VerificationResult) -> None:
    index = build_graph_index(item_records, edge_records, result)
    validate_orphan_traceability(index, result)
    validate_proof_gate_metadata(item_records, result)
    validate_decision_policies(index, result)
    validate_active_contradictions(edge_records, result)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify derived, non-authoritative architecture graph artifacts without rewriting them."
    )
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD_PATH)
    parser.add_argument(
        "--policy-doc",
        type=Path,
        action="append",
        default=[DEFAULT_POLICY_DOC_PATH],
        help="Markdown policy document to scan for positive forbidden architecture overclaims; repeatable.",
    )
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
    validate_graph_policies(item_records, edge_records, result)
    validate_overclaim_policies(all_records, args, result)
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
