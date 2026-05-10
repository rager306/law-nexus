from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "prd/architecture/architecture.schema.json"
FIXTURE_DIR = ROOT / "tests/fixtures/architecture"
VALID_FIXTURES = [
    FIXTURE_DIR / "valid_items.jsonl",
    FIXTURE_DIR / "valid_edges.jsonl",
]
INVALID_FIXTURES = [
    FIXTURE_DIR / "invalid_missing_anchor.jsonl",
    FIXTURE_DIR / "invalid_decision_no_consequence.jsonl",
    FIXTURE_DIR / "invalid_superseded_no_successor.jsonl",
    FIXTURE_DIR / "invalid_high_risk_no_gate.jsonl",
]


@dataclass(frozen=True)
class LocatedRecord:
    path: Path
    line_number: int
    record: Mapping[str, Any]

    @property
    def record_id(self) -> str:
        value = self.record.get("id")
        return value if isinstance(value, str) else "<missing-id>"

    @property
    def record_kind(self) -> str:
        value = self.record.get("record_kind")
        return value if isinstance(value, str) else "<missing-record-kind>"

    @property
    def source_anchor(self) -> str:
        anchors = self.record.get("source_anchors")
        if not isinstance(anchors, list) or not anchors:
            return "<no-source-anchor>"
        first = anchors[0]
        if not isinstance(first, Mapping):
            return "<malformed-source-anchor>"
        path = first.get("path", "<missing-path>")
        selector = first.get("selector") or first.get("section") or first.get("line_start")
        return f"{path}#{selector}" if selector else str(path)


@dataclass(frozen=True)
class ValidationErrorDetail:
    located: LocatedRecord
    field: str
    rule: str
    message: str

    def format(self) -> str:
        rel_path = self.located.path.relative_to(ROOT)
        return (
            f"{rel_path}:{self.located.line_number} "
            f"id={self.located.record_id} "
            f"record_kind={self.located.record_kind} "
            f"field={self.field} "
            f"rule={self.rule} "
            f"source_anchor={self.located.source_anchor} "
            f"message={self.message}"
        )


def load_schema() -> Mapping[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def load_jsonl(path: Path) -> Iterator[LocatedRecord]:
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            yield LocatedRecord(path=path, line_number=line_number, record=json.loads(line))


def load_records(paths: Iterable[Path]) -> list[LocatedRecord]:
    return [record for path in paths for record in load_jsonl(path)]


def resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    assert ref.startswith("#/")
    current: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        current = current[part]
    assert isinstance(current, Mapping)
    return current


def schema_errors(
    value: Any,
    schema_node: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    field: str = "$",
) -> list[tuple[str, str, str]]:
    if "$ref" in schema_node:
        return schema_errors(value, resolve_ref(root_schema, schema_node["$ref"]), root_schema, field)

    errors: list[tuple[str, str, str]] = []

    if "oneOf" in schema_node:
        option_errors = [schema_errors(value, option, root_schema, field) for option in schema_node["oneOf"]]
        passing = [candidate for candidate in option_errors if not candidate]
        if len(passing) != 1:
            details = "; ".join(error[2] for candidate in option_errors for error in candidate[:2])
            errors.append((field, "oneOf", f"expected exactly one schema branch to match; {details}"))
        return errors

    expected_type = schema_node.get("type")
    if expected_type and not type_matches(value, expected_type):
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
        if pattern and not re.search(pattern, value):
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
        for key in required:
            if key not in value:
                errors.append((key, "required", "missing required field"))
        properties = schema_node.get("properties", {})
        if schema_node.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append((key, "additionalProperties=false", "unexpected field"))
        for key, property_schema in properties.items():
            if key in value:
                errors.extend(schema_errors(value[key], property_schema, root_schema, key))
        for condition in schema_node.get("allOf", []):
            if_errors = schema_errors(value, condition.get("if", {}), root_schema, field)
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
    msg = f"Unsupported schema type in test validator: {expected_type}"
    raise AssertionError(msg)


def array_items_are_unique(items: list[Any]) -> bool:
    seen: set[str] = set()
    for item in items:
        marker = json.dumps(item, sort_keys=True)
        if marker in seen:
            return False
        seen.add(marker)
    return True


def validate_schema_records(records: Iterable[LocatedRecord], schema: Mapping[str, Any]) -> list[ValidationErrorDetail]:
    errors: list[ValidationErrorDetail] = []
    for located in records:
        record_kind = located.record.get("record_kind")
        if record_kind == "item":
            schema_node = resolve_ref(schema, "#/$defs/item")
        elif record_kind == "edge":
            schema_node = resolve_ref(schema, "#/$defs/edge")
        else:
            schema_node = schema
        for field, rule, message in schema_errors(located.record, schema_node, schema):
            errors.append(ValidationErrorDetail(located, field, rule, message))
    return errors


def validate_decision_rules(records: Iterable[LocatedRecord]) -> list[ValidationErrorDetail]:
    located_records = list(records)
    active_successor_edges = {
        (record.record.get("from"), record.record.get("to"), record.record.get("type"))
        for record in located_records
        if record.record.get("record_kind") == "edge" and record.record.get("status") == "active"
    }
    proof_gate_edges = {
        record.record.get("from")
        for record in located_records
        if record.record.get("record_kind") == "edge"
        and record.record.get("status") in {"active", "validated", "hypothesis"}
        and record.record.get("type") in {"checked_by", "validated_by"}
    }

    errors: list[ValidationErrorDetail] = []
    for located in located_records:
        record = located.record
        if record.get("record_kind") != "item" or record.get("type") != "decision":
            continue

        record_id = record.get("id")
        positive = record.get("positive_consequences") or []
        negative = record.get("negative_consequences") or []
        if record.get("status") == "active" and not positive and not negative:
            errors.append(
                ValidationErrorDetail(
                    located,
                    "positive_consequences|negative_consequences",
                    "accepted-decision-requires-consequence",
                    "active decision must list at least one positive or negative consequence",
                )
            )

        successor = record.get("superseded_by")
        if record.get("status") == "superseded" and (
            not successor
            or not (
                (successor, record_id, "supersedes") in active_successor_edges
                or (record_id, successor, "superseded_by") in active_successor_edges
            )
        ):
            errors.append(
                ValidationErrorDetail(
                    located,
                    "superseded_by",
                    "superseded-decision-requires-successor-edge",
                    "superseded decision must name a successor and have active supersession edge coverage",
                )
            )

        if record.get("risk_level") in {"high", "critical"} and record_id not in proof_gate_edges:
            errors.append(
                ValidationErrorDetail(
                    located,
                    "risk_level",
                    "high-risk-decision-requires-proof-gate",
                    "high-risk decision must have an active checked_by or validated_by proof-gate edge",
                )
            )
    return errors


def format_errors(errors: Iterable[ValidationErrorDetail]) -> str:
    return "\n".join(error.format() for error in errors)


def test_valid_architecture_fixtures_match_schema_and_decision_rules() -> None:
    schema = load_schema()
    records = load_records(VALID_FIXTURES)

    errors = validate_schema_records(records, schema) + validate_decision_rules(records)

    assert not errors, format_errors(errors)


def test_invalid_architecture_fixtures_fail_with_observable_diagnostics() -> None:
    schema = load_schema()
    failures_by_path: dict[str, str] = {}

    for path in INVALID_FIXTURES:
        records = load_records([path])
        errors = validate_schema_records(records, schema) + validate_decision_rules(records)
        failures_by_path[path.name] = format_errors(errors)

    assert "id=REQ-MISSING-ANCHOR" in failures_by_path["invalid_missing_anchor.jsonl"]
    assert "field=source_anchors" in failures_by_path["invalid_missing_anchor.jsonl"]
    assert "rule=minItems=1" in failures_by_path["invalid_missing_anchor.jsonl"]
    assert "source_anchor=<no-source-anchor>" in failures_by_path["invalid_missing_anchor.jsonl"]

    assert "id=DEC-NO-CONSEQUENCE" in failures_by_path["invalid_decision_no_consequence.jsonl"]
    assert (
        "rule=accepted-decision-requires-consequence"
        in failures_by_path["invalid_decision_no_consequence.jsonl"]
    )
    assert "source_anchor=prd/09_architecture_planning_verification_research.md#ADR repository addendum" in failures_by_path[
        "invalid_decision_no_consequence.jsonl"
    ]

    assert "id=DEC-SUPERSEDED-NO-SUCCESSOR" in failures_by_path[
        "invalid_superseded_no_successor.jsonl"
    ]
    assert "field=superseded_by" in failures_by_path["invalid_superseded_no_successor.jsonl"]
    assert "rule=required" in failures_by_path["invalid_superseded_no_successor.jsonl"]
    assert "rule=superseded-decision-requires-successor-edge" in failures_by_path[
        "invalid_superseded_no_successor.jsonl"
    ]

    assert "id=DEC-HIGH-RISK-NO-GATE" in failures_by_path["invalid_high_risk_no_gate.jsonl"]
    assert "rule=high-risk-decision-requires-proof-gate" in failures_by_path[
        "invalid_high_risk_no_gate.jsonl"
    ]

    for path_name, diagnostics in failures_by_path.items():
        assert diagnostics, f"{path_name} unexpectedly passed"
        assert f"tests/fixtures/architecture/{path_name}:1" in diagnostics
        assert "record_kind=item" in diagnostics
        assert "field=" in diagnostics
        assert "rule=" in diagnostics
        assert "source_anchor=" in diagnostics
