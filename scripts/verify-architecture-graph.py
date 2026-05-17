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
DriftKind = Literal[
    "freshness-drift",
    "source-anchor-drift",
    "graph-integrity-drift",
    "decision-fitness-drift",
    "proof-gate-drift",
    "contradiction-drift",
    "overclaim-drift",
]
LAST_RESULT: VerificationResult | None = None


@dataclass(frozen=True)
class DriftDiagnosticPolicy:
    drift_kind: DriftKind
    remediation_hint: str
    safe_to_regenerate: bool = False


FRESHNESS_DRIFT_RULES = {"upstream-s02-check", "upstream-s03-check", "report-json", "report-md"}
SOURCE_ANCHOR_DRIFT_RULES = {
    "source-anchor-path-local",
    "source-anchor-resolved-local",
    "source-anchor-exists",
    "source-anchor-line-range",
    "source-anchor-token",
}
GRAPH_INTEGRITY_DRIFT_RULES = {
    "read-jsonl",
    "malformed-jsonl",
    "jsonl-object",
    "record-id",
    "duplicate-id",
    "record-kind",
    "schema-malformed-json",
    "schema-read",
    "schema-object",
    "schema-validator",
    "missing-endpoint",
    "orphan-traceability",
    "read-claim-text",
}
DECISION_FITNESS_DRIFT_RULES = {"decision-consequence", "decision-supersession", "decision-fitness"}
PROOF_GATE_DRIFT_RULES = {"proof-gate-metadata", "evidence-class-boundary", "claim-lifecycle", "ontology-promotion-gate"}
CONTRADICTION_DRIFT_RULES = {"active-contradiction"}
OVERCLAIM_DRIFT_RULES = {"forbidden-overclaim"}
SCHEMA_RULE_FRAGMENTS = (
    "required",
    "additionalProperties",
    "enum",
    "const",
    "oneOf",
    "type=",
    "pattern=",
    "minLength",
    "minimum=",
    "maximum=",
    "minItems=",
    "uniqueItems",
    "format=date",
)


def drift_policy_for_rule(rule: str, field: str = "<none>") -> DriftDiagnosticPolicy:
    if rule in FRESHNESS_DRIFT_RULES:
        return DriftDiagnosticPolicy(
            "freshness-drift",
            "regenerate-derived-artifact-after-confirming-source-evidence-is-current",
            safe_to_regenerate=True,
        )
    if rule in SOURCE_ANCHOR_DRIFT_RULES or field.startswith("source_anchors"):
        return DriftDiagnosticPolicy(
            "source-anchor-drift",
            "edit-authoritative-source-anchor-or-source-evidence-then-regenerate-derived-projections",
        )
    if rule in DECISION_FITNESS_DRIFT_RULES:
        return DriftDiagnosticPolicy(
            "decision-fitness-drift",
            "update-source-decision-evidence-consequences-supersession-or-proof-gate-coverage",
        )
    if rule in PROOF_GATE_DRIFT_RULES:
        return DriftDiagnosticPolicy(
            "proof-gate-drift",
            "add-required-evidence-class-proof-gate-owner-or-downgrade-the-claim-in-source-evidence",
        )
    if rule in CONTRADICTION_DRIFT_RULES:
        return DriftDiagnosticPolicy(
            "contradiction-drift",
            "resolve-reject-or-supersede-the-contradiction-in-source-evidence",
        )
    if rule in OVERCLAIM_DRIFT_RULES:
        return DriftDiagnosticPolicy(
            "overclaim-drift",
            "downgrade-positive-claim-to-bounded-non-authoritative-language-or-add-required-proof",
        )
    if rule in GRAPH_INTEGRITY_DRIFT_RULES or any(fragment in rule for fragment in SCHEMA_RULE_FRAGMENTS):
        return DriftDiagnosticPolicy(
            "graph-integrity-drift",
            "fix-schema-or-graph-integrity-source-mapping-then-regenerate-derived-projections",
        )
    return DriftDiagnosticPolicy(
        "graph-integrity-drift",
        "inspect-verifier-rule-and-repair-source-mapping-without-auto-changing-authoritative-sources",
    )


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

    @property
    def drift_policy(self) -> DriftDiagnosticPolicy:
        return drift_policy_for_rule(self.rule, self.field)

    def format(self) -> str:
        policy = self.drift_policy
        return (
            f"{display_path(self.path)}:{self.line_number} "
            f"drift_kind={policy.drift_kind} id={self.record_id} record_kind={self.record_kind} "
            f"field={self.field} affected_field={self.field} rule={self.rule} source_anchor={self.source_anchor} "
            f"safe_to_regenerate={str(policy.safe_to_regenerate).lower()} "
            f"remediation_hint={policy.remediation_hint} message={self.message}"
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

    def drift_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for diagnostic in self.diagnostics:
            drift_kind = diagnostic.drift_policy.drift_kind
            counts[drift_kind] = counts.get(drift_kind, 0) + 1
        return counts

    def summary(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.ok else "fail",
            "failure_count": len(self.diagnostics),
            "items": self.items,
            "edges": self.edges,
            "upstream_checks": self.upstream_checks,
            "drift_counts": self.drift_counts(),
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


def source_anchor_kind(anchor: Mapping[str, Any]) -> str:
    kind = anchor.get("kind")
    return kind if isinstance(kind, str) and kind else "<missing-kind>"


def source_anchor_failure_message(anchor_path: str, anchor_kind: str, failure_class: str, remediation_class: str, remediation: str) -> str:
    return (
        f"anchor_path={anchor_path} anchor_kind={anchor_kind} failure_class={failure_class} "
        f"remediation_class={remediation_class} remediation={remediation}"
    )


def source_anchor_resolves_inside_gsd(anchor_path: str) -> bool:
    """Reject repository-relative symlinks that resolve into local `.gsd` state.

    Lexical `.gsd/...` source anchors remain allowed by `source_anchor_is_portable_gsd_reference`
    when they are not `.gsd/exec`; this check only catches non-`.gsd` paths whose
    resolved target would smuggle local GSD state into source evidence.
    """

    if anchor_path.startswith(".gsd/"):
        return False
    try:
        resolved_path = (ROOT / anchor_path).resolve(strict=True)
        gsd_root = (ROOT / ".gsd").resolve(strict=False)
    except OSError:
        return False
    return resolved_path == gsd_root or gsd_root in resolved_path.parents


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


def source_anchor_is_portable_gsd_reference(anchor_path: str) -> bool:
    """Return True for non-local GSD evidence that may be absent in slice worktrees.

    Auto-mode worktrees carry the current `.gsd` state, not every historical GSD
    source artifact referenced by the architecture registry. These anchors remain
    valid source-truth references, but the verifier must not make isolated
    worktree portability depend on copying old `.gsd` files into the task tree.
    `.gsd/exec` stays forbidden by `source_anchor_path_is_local`.
    """

    return anchor_path.startswith(".gsd/") and not anchor_path.startswith(".gsd/exec")


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
            anchor_kind = source_anchor_kind(anchor)
            if not source_anchor_path_is_local(raw_path):
                result.add(
                    located.diagnostic(
                        "source-anchor-path-local",
                        source_anchor_failure_message(
                            raw_path,
                            anchor_kind,
                            "unsafe-anchor-path",
                            "add-source-anchor",
                            "use-repository-relative-non-exec-anchor",
                        ),
                        field=f"{field_prefix}.path",
                    )
                )
                continue
            if source_anchor_resolves_inside_gsd(raw_path):
                result.add(
                    located.diagnostic(
                        "source-anchor-resolved-local",
                        source_anchor_failure_message(
                            raw_path,
                            anchor_kind,
                            "unsafe-resolved-gsd-target",
                            "add-source-anchor",
                            "replace-symlink-with-stable-source-anchor",
                        ),
                        field=f"{field_prefix}.path",
                    )
                )
                continue
            cached = read_anchor_lines(raw_path, cache)
            if cached is None:
                if source_anchor_is_portable_gsd_reference(raw_path):
                    continue
                result.add(
                    located.diagnostic(
                        "source-anchor-exists",
                        source_anchor_failure_message(
                            raw_path,
                            anchor_kind,
                            "missing-anchor-file",
                            "add-source-anchor",
                            "point-to-existing-repository-evidence",
                        ),
                        field=f"{field_prefix}.path",
                    )
                )
                continue
            _, lines = cached
            line_start = anchor.get("line_start")
            line_end = anchor.get("line_end")
            has_line_start = isinstance(line_start, int)
            has_line_end = isinstance(line_end, int)
            if has_line_start != has_line_end:
                result.add(
                    located.diagnostic(
                        "source-anchor-line-range",
                        source_anchor_failure_message(
                            raw_path,
                            anchor_kind,
                            "unbounded-line-range",
                            "add-source-anchor",
                            "provide-both-line_start-and-line_end-or-use-selector",
                        ),
                        field=f"{field_prefix}.line_start" if has_line_start else f"{field_prefix}.line_end",
                    )
                )
            elif has_line_start and has_line_end:
                if line_start > line_end:
                    result.add(
                        located.diagnostic(
                            "source-anchor-line-range",
                            source_anchor_failure_message(
                                raw_path,
                                anchor_kind,
                                "reversed-line-range",
                                "add-source-anchor",
                                "make-line_start-less-than-or-equal-to-line_end",
                            ),
                            field=f"{field_prefix}.line_start",
                        )
                    )
                if line_end > len(lines):
                    result.add(
                        located.diagnostic(
                            "source-anchor-line-range",
                            source_anchor_failure_message(
                                raw_path,
                                anchor_kind,
                                "line-range-out-of-bounds",
                                "add-source-anchor",
                                f"line_end-must-be-at-most-{len(lines)}",
                            ),
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
                            source_anchor_failure_message(
                                raw_path,
                                anchor_kind,
                                "stale-anchor-token",
                                "add-source-anchor",
                                f"update-{token_field}-to-current-source-text",
                            ),
                            field=f"{field_prefix}.{token_field}",
                        )
                    )


TRACEABILITY_CRITICAL_TYPES = {"requirement", "decision", "proof_gate"}
TRACEABILITY_EXEMPT_STATUSES = {"out-of-scope", "rejected"}
PROOF_USING_EDGE_TYPES = {"satisfies", "validated_by", "checked_by", "evidenced_by", "bounded_by"}
PROOF_FORBIDDEN_STATUSES = {"deferred", "rejected"}
VALIDATED_MINIMUM_PROOF_LEVELS = {
    "static-check",
    "unit-test",
    "integration-test",
    "runtime-smoke",
    "real-document-proof",
    "production-observation",
}
PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES = {
    "static-check": {"source-code", "test-artifact", "gsd-summary"},
    "unit-test": {"test-artifact"},
    "integration-test": {"test-artifact"},
    "runtime-smoke": {"runtime-artifact"},
    "real-document-proof": {"runtime-artifact", "gsd-summary"},
    "production-observation": {"runtime-artifact", "external-reference", "gsd-summary"},
}
DERIVED_NON_AUTHORITATIVE_PATH_PATTERNS = (
    "prd/architecture/architecture_graph_report.json",
    "prd/architecture/architecture_report.md",
    "prd/architecture/architecture_health.md",
    "prd/architecture/product_readiness_blockers.md",
    "prd/architecture/claims_ledger.md",
    ".agents/skills/",
    ".claude/skills/",
)
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

PROOF_LEVEL_ORDER = {
    "none": 0,
    "source-anchor": 1,
    "static-check": 2,
    "unit-test": 3,
    "integration-test": 4,
    "runtime-smoke": 5,
    "real-document-proof": 6,
    "production-observation": 7,
}
ONTOLOGY_PROMOTION_GATE_EDGE_TYPES = {"checked_by", "validated_by", "bounded_by"}
ONTOLOGY_PROMOTION_GATE_TARGET_TYPES = {"proof_gate", "workflow_check"}
ONTOLOGY_PROMOTION_GATE_EDGE_STATUSES = {"active", "bounded-evidence", "validated"}
ONTOLOGY_RESEARCH_STATUSES = {"proposed", "hypothesis", "bounded-evidence", "deferred", "blocked"}
ONTOLOGY_BOUNDARY_TERMS = (
    "non-authoritative",
    "does not prove",
    "does not validate",
    "must not",
    "cannot",
    "bounded",
    "candidate",
    "defer",
    "proof-gated",
    "no ",
    "not ",
)
ONTOLOGY_PROMOTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "label": "Akoma Ntoso / LegalDocML compatibility projection",
        "trigger_terms": ("Akoma Ntoso", "LegalDocML"),
        "required_gate_ids": ("GATE-AKOMA-FRBR-NORMALIZATION",),
        "minimum_proof_level": "static-check",
    },
    {
        "label": "FRBR legal identity reference layer",
        "trigger_terms": ("FRBR",),
        "required_gate_ids": ("GATE-AKOMA-FRBR-NORMALIZATION",),
        "minimum_proof_level": "static-check",
    },
    {
        "label": "LKIF / deontic mapping proof gate",
        "trigger_terms": ("LKIF", "deontic"),
        "required_gate_ids": ("GATE-LKIF-DEONTIC-BENCHMARK",),
        "minimum_proof_level": "unit-test",
    },
    {
        "label": "RusLegalCore domain ontology scope gate",
        "trigger_terms": ("RusLegalCore",),
        "required_gate_ids": ("GATE-RUSLEGALCORE-SCOPE",),
        "minimum_proof_level": "static-check",
    },
    {
        "label": "BFO / GOST / OWL / Common Logic formal alignment",
        "trigger_terms": ("BFO", "GOST", "GOST R 59798-2021", "OWL", "OWL 2", "Common Logic"),
        "required_gate_ids": ("GATE-BFO-GOST-ALIGNMENT",),
        "minimum_proof_level": "static-check",
    },
    {
        "label": "Ontology GraphRAG integration proof",
        "trigger_terms": ("Ontology GraphRAG", "ontology-aware GraphRAG", "ontology-driven GraphRAG"),
        "required_gate_ids": ("GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",),
        "minimum_proof_level": "integration-test",
    },
    {
        "label": "graph-vector / HNSW / FalkorDB graph-vector behavior",
        "trigger_terms": ("graph-vector", "HNSW", "hybrid retrieval"),
        "required_gate_ids": ("GATE-G015", "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"),
        "minimum_proof_level": "runtime-smoke",
    },
    {
        "label": "pilot-scale / 1000-document readiness",
        "trigger_terms": ("pilot-scale", "1000-document", "1,000-document", "1000 document", "1,000 document"),
        "required_gate_ids": ("GATE-PILOT-SCALE-READINESS",),
        "minimum_proof_level": "integration-test",
    },
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


def claim_priority(located: LocatedRecord) -> str:
    priority = located.record.get("priority")
    if isinstance(priority, str) and priority:
        return priority
    risk_level = located.record.get("risk_level")
    return risk_level if isinstance(risk_level, str) and risk_level else "unspecified"


def anchor_evidence_classes(located: LocatedRecord) -> set[str]:
    anchors = located.record.get("source_anchors")
    if not isinstance(anchors, list):
        return set()
    classes: set[str] = set()
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        kind = anchor.get("kind")
        if isinstance(kind, str) and kind:
            classes.add(kind)
    return classes


def anchor_paths(located: LocatedRecord) -> list[str]:
    anchors = located.record.get("source_anchors")
    if not isinstance(anchors, list):
        return []
    paths: list[str] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        path = anchor.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return paths


def is_derived_non_authoritative_path(anchor_path: str) -> bool:
    return any(pattern in anchor_path for pattern in DERIVED_NON_AUTHORITATIVE_PATH_PATTERNS)


def evidence_class_message(
    *,
    proof_level: str,
    current_classes: set[str],
    required_classes: set[str],
    failure_class: str,
    anchor_path: str | None = None,
) -> str:
    current = ",".join(sorted(current_classes)) if current_classes else "<none>"
    required = ",".join(sorted(required_classes)) if required_classes else "<non-authoritative-derived-artifact>"
    path_context = f" anchor_path={anchor_path}" if anchor_path else ""
    return (
        f"proof_level={proof_level} current_evidence_classes={current} "
        f"required_evidence_class={required} failure_class={failure_class}{path_context} "
        "remediation_class=add-evidence-class remediation=add-proof-level-matching-evidence-or-downgrade-claim"
    )


def validate_evidence_class_boundaries(item_records: list[LocatedRecord], result: VerificationResult) -> None:
    for located in item_records:
        proof_level = located.record.get("proof_level")
        if not isinstance(proof_level, str) or proof_level == "none":
            continue
        current_classes = anchor_evidence_classes(located)
        for anchor_path in anchor_paths(located):
            if is_derived_non_authoritative_path(anchor_path):
                result.add(
                    located.diagnostic(
                        "evidence-class-boundary",
                        evidence_class_message(
                            proof_level=proof_level,
                            current_classes=current_classes,
                            required_classes=set(),
                            failure_class="derived-artifact-used-as-proof",
                            anchor_path=anchor_path,
                        ),
                        field="source_anchors",
                    )
                )
        if item_status(located) != "validated":
            continue
        required_classes = PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES.get(proof_level)
        if not required_classes:
            continue
        if current_classes.isdisjoint(required_classes):
            result.add(
                located.diagnostic(
                    "evidence-class-boundary",
                    evidence_class_message(
                        proof_level=proof_level,
                        current_classes=current_classes,
                        required_classes=required_classes,
                        failure_class="proof-level-evidence-class-mismatch",
                    ),
                    field="source_anchors",
                )
            )


def validate_claim_lifecycle(index: GraphIndex, result: VerificationResult) -> None:
    for record_id, located in sorted(index.items_by_id.items()):
        status = item_status(located)
        proof_level = located.record.get("proof_level")
        priority = claim_priority(located)
        if status == "validated" and proof_level not in VALIDATED_MINIMUM_PROOF_LEVELS:
            result.add(
                located.diagnostic(
                    "claim-lifecycle",
                    (
                        f"record={record_id} priority={priority} lifecycle_status={status} current_status={status} proof_level={proof_level} "
                        "failure_class=unsafe-promotion forbidden_transition=unverified-to-validated "
                        "remediation_class=add-evidence-or-downgrade remediation=add-evidence-class-or-downgrade-claim"
                    ),
                    field="status",
                )
            )

    for edge in index.edges:
        edge_type = edge.record.get("type")
        edge_status = edge.record.get("status")
        if edge_type not in PROOF_USING_EDGE_TYPES or edge_status not in {"active", "bounded-evidence", "validated"}:
            continue
        for endpoint_field in ("from", "to"):
            endpoint_id = edge_endpoint(edge, endpoint_field)
            if endpoint_id is None:
                continue
            endpoint = index.items_by_id.get(endpoint_id)
            if endpoint is None:
                continue
            endpoint_status = item_status(endpoint)
            if endpoint_status not in PROOF_FORBIDDEN_STATUSES:
                continue
            endpoint_priority = claim_priority(endpoint)
            result.add(
                edge.diagnostic(
                    "claim-lifecycle",
                    (
                        f"record={edge.record_id} endpoint={endpoint_id} priority={endpoint_priority} "
                        f"lifecycle_status={endpoint_status} current_status={endpoint_status} "
                        "failure_class=proof-from-backlog "
                        f"forbidden_transition={endpoint_status}-claim-used-as-proof "
                        "remediation_class=supersede-reject-or-downgrade remediation=supersede-or-reject-edge-or-downgrade-claim"
                    ),
                    field=endpoint_field,
                )
            )


def lower_claim_text(located: LocatedRecord) -> str:
    values = [text for _, text in iter_record_claim_text(located)]
    non_claims = located.record.get("non_claims")
    if isinstance(non_claims, list):
        values.extend(item for item in non_claims if isinstance(item, str))
    return "\n".join(values).lower()


def matched_ontology_rules(located: LocatedRecord) -> list[tuple[dict[str, Any], str]]:
    text = lower_claim_text(located)
    matches: list[tuple[dict[str, Any], str]] = []
    for rule in ONTOLOGY_PROMOTION_RULES:
        for term in rule["trigger_terms"]:
            if str(term).lower() in text:
                matches.append((rule, str(term)))
                break
    return matches


def anchor_has_bounded_source_mapping(anchor: Mapping[str, Any]) -> bool:
    if not isinstance(anchor.get("path"), str) or not anchor.get("path"):
        return False
    if isinstance(anchor.get("selector"), str) and anchor.get("selector"):
        return True
    if isinstance(anchor.get("section"), str) and anchor.get("section"):
        return True
    return isinstance(anchor.get("line_start"), int) and isinstance(anchor.get("line_end"), int)


def has_bounded_source_mapping(located: LocatedRecord) -> bool:
    anchors = located.record.get("source_anchors")
    if not isinstance(anchors, list):
        return False
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        anchor_path = anchor.get("path")
        if isinstance(anchor_path, str) and is_derived_non_authoritative_path(anchor_path):
            continue
        if anchor_has_bounded_source_mapping(anchor):
            return True
    return False


def proof_level_at_least(current: Any, required: str) -> bool:
    if not isinstance(current, str):
        return False
    return PROOF_LEVEL_ORDER.get(current, -1) >= PROOF_LEVEL_ORDER[required]


def ontology_gate_ids_for(record_id: str, index: GraphIndex) -> set[str]:
    gate_ids: set[str] = set()
    for edge in index.outgoing.get(record_id, []):
        if edge.record.get("type") not in ONTOLOGY_PROMOTION_GATE_EDGE_TYPES:
            continue
        if edge.record.get("status") not in ONTOLOGY_PROMOTION_GATE_EDGE_STATUSES:
            continue
        target_id = edge_endpoint(edge, "to")
        if target_id is None:
            continue
        target = index.items_by_id.get(target_id)
        if target is None or item_type(target) not in ONTOLOGY_PROMOTION_GATE_TARGET_TYPES:
            continue
        gate_ids.add(target_id)
    return gate_ids


def has_research_boundary_language(located: LocatedRecord) -> bool:
    text = lower_claim_text(located)
    return any(term in text for term in ONTOLOGY_BOUNDARY_TERMS)


def ontology_promotion_message(*, trigger_term: str, label: str, failure_class: str, remediation_class: str, remediation: str, detail: str) -> str:
    return (
        f"r035_trigger={trigger_term} ontology_rule={label} failure_class={failure_class} {detail} "
        f"remediation_class={remediation_class} remediation={remediation}"
    )


def validate_ontology_promotion_gates(index: GraphIndex, result: VerificationResult) -> None:
    for record_id, located in sorted(index.items_by_id.items()):
        matches = matched_ontology_rules(located)
        if not matches:
            continue
        status = item_status(located)
        if status == "<missing-status>":
            rule, trigger_term = matches[0]
            result.add(
                located.diagnostic(
                    "ontology-promotion-gate",
                    ontology_promotion_message(
                        trigger_term=trigger_term,
                        label=str(rule["label"]),
                        failure_class="missing-status",
                        remediation_class="downgrade-claim",
                        remediation="record-status-before-validated-ontology-promotion",
                        detail="current_status=<missing-status>",
                    ),
                    field="status",
                )
            )
            continue
        if status in ONTOLOGY_RESEARCH_STATUSES:
            if not has_research_boundary_language(located):
                rule, trigger_term = matches[0]
                result.add(
                    located.diagnostic(
                        "ontology-promotion-gate",
                        ontology_promotion_message(
                            trigger_term=trigger_term,
                            label=str(rule["label"]),
                            failure_class="status-overreach",
                            remediation_class="downgrade-claim",
                            remediation="add-non-authoritative-boundary-language-or-downgrade-claim",
                            detail=f"current_status={status}",
                        ),
                        field="status",
                    )
                )
            continue
        if status != "validated":
            continue

        if not non_empty_string(located.record.get("owner")):
            rule, trigger_term = matches[0]
            result.add(
                located.diagnostic(
                    "ontology-promotion-gate",
                    ontology_promotion_message(
                        trigger_term=trigger_term,
                        label=str(rule["label"]),
                        failure_class="missing-owner",
                        remediation_class="add-source-anchor",
                        remediation="record-owner-before-validated-ontology-promotion",
                        detail=f"current_status={status}",
                    ),
                    field="owner",
                )
            )
        if not non_empty_string(located.record.get("status")):
            rule, trigger_term = matches[0]
            result.add(
                located.diagnostic(
                    "ontology-promotion-gate",
                    ontology_promotion_message(
                        trigger_term=trigger_term,
                        label=str(rule["label"]),
                        failure_class="missing-status",
                        remediation_class="downgrade-claim",
                        remediation="record-status-before-validated-ontology-promotion",
                        detail="current_status=<missing-status>",
                    ),
                    field="status",
                )
            )
        if not has_bounded_source_mapping(located):
            rule, trigger_term = matches[0]
            result.add(
                located.diagnostic(
                    "ontology-promotion-gate",
                    ontology_promotion_message(
                        trigger_term=trigger_term,
                        label=str(rule["label"]),
                        failure_class="missing-source-mapping",
                        remediation_class="add-source-anchor",
                        remediation="add-bounded-selector-section-or-line-range-source-mapping",
                        detail=f"current_status={status}",
                    ),
                    field="source_anchors",
                )
            )

        linked_gate_ids = ontology_gate_ids_for(record_id, index)
        for rule, trigger_term in matches:
            required_gate_ids = set(rule["required_gate_ids"])
            if linked_gate_ids.isdisjoint(required_gate_ids):
                result.add(
                    located.diagnostic(
                        "ontology-promotion-gate",
                        ontology_promotion_message(
                            trigger_term=trigger_term,
                            label=str(rule["label"]),
                            failure_class="missing-proof-gate",
                            remediation_class="add-proof-gate",
                            remediation="link-claim-to-required-proof-gate-before-validation",
                            detail=f"required_gate_ids={','.join(sorted(required_gate_ids))} linked_gate_ids={','.join(sorted(linked_gate_ids)) or '<none>'}",
                        ),
                        field="id",
                    )
                )
            required_proof_level = str(rule["minimum_proof_level"])
            current_proof_level = located.record.get("proof_level")
            if not proof_level_at_least(current_proof_level, required_proof_level):
                result.add(
                    located.diagnostic(
                        "ontology-promotion-gate",
                        ontology_promotion_message(
                            trigger_term=trigger_term,
                            label=str(rule["label"]),
                            failure_class="proof-level-overreach",
                            remediation_class="add-evidence-class",
                            remediation="add-required-proof-level-evidence-or-downgrade-claim",
                            detail=f"current_proof_level={current_proof_level} required_proof_level={required_proof_level}",
                        ),
                        field="proof_level",
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
    validate_evidence_class_boundaries(item_records, result)
    validate_claim_lifecycle(index, result)
    validate_ontology_promotion_gates(index, result)


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
