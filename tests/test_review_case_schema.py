"""Contract tests for the non-authoritative Review Case v1 wire schema.

This module is a test-side oracle only. It is not the future runtime validator,
codec, CLI, or Governor implementation. Runtime validation remains deferred to
later harness adapters under ADR-0024.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "prd/architecture/review-case.schema.json"
README_PATH = ROOT / "prd/architecture/review-cases/README.md"
SCHEMA_VERSION = "review-case/v1"

ACCEPTING_DISPOSITIONS = frozenset(
    {
        "accepted_as_gap",
        "accepted_as_requirement_candidate",
        "accepted_as_decision_candidate",
        "accepted_as_process_defect",
    }
)
PASSED_VERIFICATION = frozenset(
    {
        "passed_bounded",
        "passed_smoke",
        "passed_validated",
    }
)
DOCS_OR_PROCESS_PROOF = frozenset({"docs", "process"})
IMPLEMENTATION_OR_EVIDENCE = frozenset({"implementation", "evidence"})
TERMINAL_WITHOUT_WORK = frozenset(
    {
        "rejected",
        "duplicate",
        "superseded",
        "not_applicable",
        "already_satisfied",
    }
)


def minimal_packet() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "authoritative": False,
        "authority_required": True,
        "packet_id": "RC-2026-08-11-001",
        "source": {
            "path": "doc/review/review-11-08-2026.md",
            "content_sha256": "a" * 64,
            "reviewed_git_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
            "received_at": "2026-08-11T10:33:40Z",
            "source_kind": "human_external",
        },
        "normalization": {
            "status": "source_verified",
            "method": "manual",
            "source_hash": "a" * 64,
        },
        "non_claims": [
            "Non-authoritative review projection",
            "Does not promote requirements, ADRs, roadmap, or lifecycle",
        ],
        "findings": [
            {
                "finding_id": "RC11-F04",
                "kind": "gap",
                "concern_class": "design",
                "reviewer_severity": "critical",
                "summary": "Missing core NormRule and applicability chain",
                "source_spans": [
                    {
                        "path": "doc/review/review-11-08-2026.md",
                        "heading": "# 2. Main gap",
                        "line_start": 125,
                        "line_end": 180,
                        "quote_sha256": "b" * 64,
                    }
                ],
                "candidate_targets": [
                    {
                        "surface": "tsg",
                        "id": "TSG-006",
                        "note": "candidate only",
                    }
                ],
                "required_proof_class": "implementation",
                "normalization_status": "source_verified",
                "disposition_status": "open",
                "execution_status": "unplanned",
                "verification_status": "unverified",
                "non_claims": [
                    "Not an accepted requirement",
                    "Not a runtime capability",
                ],
            }
        ],
        "edges": [
            {
                "type": "maps_to",
                "from": "RC11-F04",
                "to": "TSG-006",
                "status": "candidate",
            }
        ],
        "events": [
            {
                "event_id": "E001",
                "event_type": "packet_registered",
                "at": "2026-08-11T10:33:40Z",
                "actor_class": "human",
                "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "rationale": "Register immutable review source",
            }
        ],
    }


def resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    assert ref.startswith("#/")
    current: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        current = current[part]
    assert isinstance(current, Mapping)
    return current


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


def schema_errors(
    value: Any,
    schema_node: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    field: str = "$",
) -> list[tuple[str, str, str]]:
    if "$ref" in schema_node:
        return schema_errors(
            value, resolve_ref(root_schema, schema_node["$ref"]), root_schema, field
        )

    errors: list[tuple[str, str, str]] = []

    expected_type = schema_node.get("type")
    if expected_type and not type_matches(value, expected_type):
        errors.append(
            (
                field,
                f"type={expected_type}",
                f"expected {expected_type}, got {type(value).__name__}",
            )
        )
        return errors

    if "const" in schema_node and value != schema_node["const"]:
        errors.append((field, "const", f"expected {schema_node['const']!r}, got {value!r}"))
    if "enum" in schema_node and value not in schema_node["enum"]:
        errors.append((field, "enum", f"unexpected value {value!r}"))

    if isinstance(value, str):
        min_length = schema_node.get("minLength")
        max_length = schema_node.get("maxLength")
        if min_length is not None and len(value) < min_length:
            errors.append((field, f"minLength={min_length}", "string too short"))
        if max_length is not None and len(value) > max_length:
            errors.append((field, f"maxLength={max_length}", "string too long"))
        pattern = schema_node.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append((field, f"pattern={pattern}", f"value {value!r} does not match pattern"))
        not_schema = schema_node.get("not")
        if isinstance(not_schema, Mapping) and not schema_errors(
            value, not_schema, root_schema, field
        ):
            errors.append((field, "not", f"value {value!r} matched forbidden schema"))

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
                errors.append((f"{field}.{key}" if field != "$" else key, "required", "missing"))
        properties = schema_node.get("properties", {})
        if schema_node.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(
                        (
                            f"{field}.{key}" if field != "$" else key,
                            "additionalProperties=false",
                            "unexpected field",
                        )
                    )
        for key, property_schema in properties.items():
            if key in value:
                child = f"{field}.{key}" if field != "$" else key
                errors.extend(schema_errors(value[key], property_schema, root_schema, child))

    return errors


def structural_errors(packet: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    return [
        f"{field} rule={rule} message={message}"
        for field, rule, message in schema_errors(packet, schema, schema)
    ]


def invariant_errors(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    findings = {
        finding["finding_id"]: finding
        for finding in packet.get("findings", [])
        if isinstance(finding, Mapping) and isinstance(finding.get("finding_id"), str)
    }
    events = [event for event in packet.get("events", []) if isinstance(event, Mapping)]
    edges = [edge for edge in packet.get("edges", []) if isinstance(edge, Mapping)]

    source = packet.get("source")
    normalization = packet.get("normalization")
    if (
        isinstance(source, Mapping)
        and isinstance(normalization, Mapping)
        and normalization.get("source_hash") != source.get("content_sha256")
    ):
        errors.append("normalization.source_hash must equal source.content_sha256")

    if "derived_status" in packet:
        errors.append("packet.derived_status is author-written and forbidden")

    human_dispositions = {
        (event.get("finding_id"), event["payload"].get("disposition"))
        for event in events
        if event.get("event_type") == "disposition_recorded"
        and event.get("actor_class") == "human"
        and isinstance(event.get("payload"), Mapping)
    }
    if (
        isinstance(normalization, Mapping)
        and normalization.get("status") == "human_reviewed"
        and not any(
            event.get("event_type") == "normalization_reviewed"
            and event.get("actor_class") == "human"
            for event in events
        )
    ):
        errors.append("human_reviewed requires human normalization_reviewed event")

    for finding_id, finding in findings.items():
        if "derived_status" in finding:
            errors.append(f"{finding_id}.derived_status is author-written and forbidden")
        for index, span in enumerate(finding.get("source_spans", [])):
            if not isinstance(span, Mapping):
                continue
            start = span.get("line_start")
            end = span.get("line_end")
            if isinstance(start, int) and isinstance(end, int) and end < start:
                errors.append(
                    f"{finding_id}.source_spans[{index}] line_end {end} < line_start {start}"
                )

        disposition = finding.get("disposition_status")
        if disposition != "open" and (finding_id, disposition) not in human_dispositions:
            errors.append(
                f"{finding_id} disposition {disposition} requires matching human "
                "disposition_recorded event"
            )
        execution = finding.get("execution_status")
        if disposition in TERMINAL_WITHOUT_WORK and execution not in {
            "not_required",
            "cancelled",
        }:
            errors.append(
                f"{finding_id} terminal disposition {disposition} requires execution_status=not_required"
            )

        verification = finding.get("verification_status")
        if verification in PASSED_VERIFICATION:
            proof_events = [
                event
                for event in events
                if event.get("event_type") == "verification_recorded"
                and event.get("finding_id") == finding_id
            ]
            if not proof_events:
                errors.append(f"{finding_id} passed verification lacks verification_recorded event")
            for event in proof_events:
                payload = event.get("payload")
                if not isinstance(payload, Mapping):
                    errors.append(f"{finding_id} verification event missing payload object")
                    continue
                if payload.get("proof_class") not in {
                    "docs",
                    "design",
                    "implementation",
                    "evidence",
                    "process",
                }:
                    errors.append(f"{finding_id} verification missing proof_class")
                tested_revision = payload.get("tested_revision")
                if not isinstance(tested_revision, str) or not tested_revision:
                    errors.append(f"{finding_id} verification missing tested_revision")
                elif re.fullmatch(r"[a-f0-9]{40}", tested_revision) is None:
                    errors.append(
                        f"{finding_id} verification tested_revision must be 40 lowercase hex"
                    )
                anchors = payload.get("evidence_anchors")
                if not isinstance(anchors, list) or not anchors:
                    errors.append(f"{finding_id} verification missing evidence_anchors")
                required = finding.get("required_proof_class")
                proof = payload.get("proof_class")
                if (
                    required in IMPLEMENTATION_OR_EVIDENCE
                    and proof in DOCS_OR_PROCESS_PROOF
                    and verification in PASSED_VERIFICATION
                ):
                    errors.append(
                        f"{finding_id} docs/process proof cannot close {required} requirement"
                    )

    human_accepting = {
        event.get("finding_id")
        for event in events
        if event.get("event_type") == "disposition_recorded"
        and event.get("actor_class") == "human"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("disposition") in ACCEPTING_DISPOSITIONS
    }

    for event in events:
        if event.get("event_type") != "disposition_recorded":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            errors.append(f"{event.get('event_id')} disposition_recorded requires payload")
            continue
        disposition = payload.get("disposition")
        if disposition in ACCEPTING_DISPOSITIONS and event.get("actor_class") != "human":
            errors.append(
                f"{event.get('event_id')} accepting disposition requires actor_class=human"
            )

    for index, edge in enumerate(edges):
        edge_type = edge.get("type")
        status = edge.get("status")
        source = edge.get("from")
        if edge_type == "maps_to" and status != "candidate":
            errors.append(f"edges[{index}] maps_to must remain candidate")
        if edge_type != "maps_to" and status != "candidate":
            matching_human_events = [
                event
                for event in events
                if event.get("event_type") == "edge_asserted"
                and event.get("actor_class") == "human"
                and isinstance(event.get("payload"), Mapping)
                and event["payload"].get("edge_type") == edge_type
                and event["payload"].get("from") == source
                and event["payload"].get("to") == edge.get("to")
            ]
            if not matching_human_events:
                errors.append(
                    f"edges[{index}] non-candidate relation requires matching human "
                    "edge_asserted event"
                )
        if edge_type == "promoted_to":
            if source not in human_accepting:
                errors.append(
                    f"edges[{index}] promoted_to requires prior human accepting disposition"
                )
            promoting_events = [
                event
                for event in events
                if event.get("event_type") == "edge_asserted"
                and event.get("actor_class") == "human"
                and isinstance(event.get("payload"), Mapping)
                and event["payload"].get("edge_type") == "promoted_to"
                and event["payload"].get("from") == source
                and event["payload"].get("to") == edge.get("to")
            ]
            if not promoting_events:
                errors.append(f"edges[{index}] promoted_to lacks human edge_asserted event")
        if edge_type in {"promoted_to", "implemented_by", "verified_by"} and status == "accepted":
            if any(
                event.get("actor_class") in {"tool", "llm"}
                and event.get("event_type") == "edge_asserted"
                and isinstance(event.get("payload"), Mapping)
                and event["payload"].get("from") == source
                and event["payload"].get("edge_type") == edge_type
                for event in events
            ):
                errors.append(f"edges[{index}] accepted {edge_type} asserted by tool/llm")

    open_children: set[str] = set()
    for edge in edges:
        if edge.get("type") != "splits_into":
            continue
        parent = edge.get("from")
        child = edge.get("to")
        child_finding = findings.get(child)
        if child_finding is None:
            errors.append(f"splits_into target {child!r} is missing")
            continue
        child_terminal = child_finding.get("disposition_status") in TERMINAL_WITHOUT_WORK or (
            child_finding.get("execution_status") == "implemented"
            and child_finding.get("verification_status") in PASSED_VERIFICATION
        )
        if not child_terminal:
            open_children.add(parent if isinstance(parent, str) else "")

    for edge in edges:
        if edge.get("type") != "blocked_by":
            continue
        parent = edge.get("from")
        blocker = edge.get("to")
        if isinstance(parent, str) and parent in findings and blocker in findings:
            blocker_status = findings[blocker].get("disposition_status")
            if blocker_status not in TERMINAL_WITHOUT_WORK:
                open_children.add(parent)

    for finding_id, finding in findings.items():
        if (
            finding.get("execution_status") == "implemented"
            and finding.get("verification_status") in PASSED_VERIFICATION
            and finding_id in open_children
        ):
            errors.append(f"{finding_id} cannot close while required children/blockers remain open")

    return errors


def validate_packet(packet: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    return structural_errors(packet, schema) + invariant_errors(packet)


@pytest.fixture(scope="module")
def schema() -> Mapping[str, Any]:
    assert SCHEMA_PATH.is_file(), f"missing schema: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_and_readme_exist() -> None:
    assert SCHEMA_PATH.is_file()
    assert README_PATH.is_file()
    readme = README_PATH.read_text(encoding="utf-8")
    for needle in (
        "L0",
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "maps_to",
        "promoted_to",
        "Pydantic",
        "Adaptix",
        "non-authoritative",
        "non-claims",
    ):
        assert needle in readme


def test_schema_root_contract(schema: Mapping[str, Any]) -> None:
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert schema["properties"]["authoritative"]["const"] is False
    assert schema["properties"]["authority_required"]["const"] is True
    finding_props = schema["$defs"]["finding"]["properties"]
    event_payload_props = schema["$defs"]["event"]["properties"]["payload"]["properties"]
    assert event_payload_props["verification_result"]["enum"] == [
        "passed_bounded",
        "passed_smoke",
        "failed",
        "inconclusive",
    ]
    assert "derived_status" not in finding_props
    assert "derived_status" not in schema["properties"]


def test_valid_minimal_packet(schema: Mapping[str, Any]) -> None:
    errors = validate_packet(minimal_packet(), schema)
    assert errors == []


def test_unknown_root_field_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["unexpected"] = True
    errors = validate_packet(packet, schema)
    assert any("additionalProperties=false" in error for error in errors)


def test_author_written_derived_status_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["derived_status"] = "closed"
    errors = validate_packet(packet, schema)
    assert any("derived_status is author-written and forbidden" in error for error in errors)


def test_normalization_source_hash_must_match_source(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["normalization"]["source_hash"] = "c" * 64
    errors = validate_packet(packet, schema)
    assert any("source_hash must equal source.content_sha256" in error for error in errors)


def test_authoritative_true_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["authoritative"] = True
    errors = validate_packet(packet, schema)
    assert any("authoritative" in error and "const" in error for error in errors)


def test_unknown_enum_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["kind"] = "ontology_class"
    errors = validate_packet(packet, schema)
    assert any("kind" in error and "enum" in error for error in errors)


def test_malformed_span_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["source_spans"][0]["line_start"] = 0
    errors = validate_packet(packet, schema)
    assert any("line_start" in error for error in errors)

    packet = minimal_packet()
    packet["findings"][0]["source_spans"][0]["line_start"] = 20
    packet["findings"][0]["source_spans"][0]["line_end"] = 10
    errors = validate_packet(packet, schema)
    assert any("line_end" in error and "line_start" in error for error in errors)


def test_invalid_edge_type_fails(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["edges"][0]["type"] = "owl_same_as"
    errors = validate_packet(packet, schema)
    assert any("type" in error and "enum" in error for error in errors)


def test_non_open_disposition_without_matching_human_event_fails(
    schema: Mapping[str, Any],
) -> None:
    for disposition in (
        "accepted_as_gap",
        "already_satisfied",
        "rejected",
        "deferred",
        "duplicate",
        "superseded",
        "not_applicable",
    ):
        packet = minimal_packet()
        packet["findings"][0]["disposition_status"] = disposition
        if disposition in TERMINAL_WITHOUT_WORK:
            packet["findings"][0]["execution_status"] = "not_required"
        errors = validate_packet(packet, schema)
        assert any(
            "requires matching human disposition_recorded event" in error for error in errors
        )


def test_maps_to_edge_is_always_candidate(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["edges"][0]["status"] = "accepted"
    errors = validate_packet(packet, schema)
    assert any("maps_to must remain candidate" in error for error in errors)


def test_non_candidate_relation_requires_matching_human_event(
    schema: Mapping[str, Any],
) -> None:
    packet = minimal_packet()
    packet["findings"].append(copy.deepcopy(packet["findings"][0]))
    packet["findings"][1]["finding_id"] = "RC11-F05"
    packet["edges"][0] = {
        "type": "refines",
        "from": "RC11-F05",
        "to": "RC11-F04",
        "status": "accepted",
    }
    errors = validate_packet(packet, schema)
    assert any(
        "non-candidate relation requires matching human edge_asserted" in error for error in errors
    )


def test_event_payload_rejects_authority_like_unknown_fields(
    schema: Mapping[str, Any],
) -> None:
    packet = minimal_packet()
    packet["events"][0]["payload"] = {"authoritative": True}
    errors = validate_packet(packet, schema)
    assert any(
        "payload.authoritative" in error and "additionalProperties=false" in error
        for error in errors
    )


def test_verification_payload_requires_git_revision(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["required_proof_class"] = "docs"
    packet["findings"][0]["verification_status"] = "passed_bounded"
    packet["events"].append(
        {
            "event_id": "E-BAD-REV",
            "event_type": "verification_recorded",
            "at": "2026-08-12T00:00:00Z",
            "actor_class": "human",
            "finding_id": "RC11-F04",
            "payload": {
                "proof_class": "docs",
                "tested_revision": "not-a-git-revision",
                "evidence_anchors": ["prd/ARCHITECTURE.md"],
            },
        }
    )
    errors = validate_packet(packet, schema)
    assert any("verification tested_revision must be 40 lowercase hex" in error for error in errors)


def test_human_reviewed_normalization_requires_human_event(
    schema: Mapping[str, Any],
) -> None:
    packet = minimal_packet()
    packet["normalization"]["status"] = "human_reviewed"
    errors = validate_packet(packet, schema)
    assert any(
        "human_reviewed requires human normalization_reviewed event" in error for error in errors
    )


def test_promotion_without_human_disposition_fails(schema: Mapping[str, Any]) -> None:
    for status in ("candidate", "accepted"):
        packet = minimal_packet()
        packet["findings"][0]["disposition_status"] = "accepted_as_gap"
        packet["edges"].append(
            {
                "type": "promoted_to",
                "from": "RC11-F04",
                "to": "TSG-006",
                "status": status,
            }
        )
        errors = validate_packet(packet, schema)
        assert any("promoted_to requires prior human accepting disposition" in e for e in errors)


def test_tool_cannot_accept_or_promote(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["disposition_status"] = "accepted_as_gap"
    packet["events"].extend(
        [
            {
                "event_id": "E-TOOL",
                "event_type": "disposition_recorded",
                "at": "2026-08-12T00:00:00Z",
                "actor_class": "tool",
                "finding_id": "RC11-F04",
                "payload": {"disposition": "accepted_as_gap"},
            },
            {
                "event_id": "E-EDGE",
                "event_type": "edge_asserted",
                "at": "2026-08-12T00:00:01Z",
                "actor_class": "llm",
                "finding_id": "RC11-F04",
                "payload": {
                    "edge_type": "promoted_to",
                    "from": "RC11-F04",
                    "to": "TSG-006",
                },
            },
        ]
    )
    packet["edges"].append(
        {
            "type": "promoted_to",
            "from": "RC11-F04",
            "to": "TSG-006",
            "status": "accepted",
        }
    )
    errors = validate_packet(packet, schema)
    assert any("requires actor_class=human" in error for error in errors)


def test_passed_verification_requires_proof_and_revision(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["verification_status"] = "passed_bounded"
    errors = validate_packet(packet, schema)
    assert any("lacks verification_recorded event" in error for error in errors)


def test_docs_proof_cannot_close_implementation_gap(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["required_proof_class"] = "implementation"
    packet["findings"][0]["verification_status"] = "passed_bounded"
    packet["events"].append(
        {
            "event_id": "E-VER",
            "event_type": "verification_recorded",
            "at": "2026-08-12T00:00:00Z",
            "actor_class": "human",
            "finding_id": "RC11-F04",
            "payload": {
                "proof_class": "docs",
                "tested_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "evidence_anchors": ["prd/ARCHITECTURE.md"],
            },
        }
    )
    errors = validate_packet(packet, schema)
    assert any("docs/process proof cannot close implementation" in error for error in errors)


def test_parent_cannot_close_with_open_required_child(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    parent = copy.deepcopy(packet["findings"][0])
    child = copy.deepcopy(packet["findings"][0])
    parent["finding_id"] = "RC11-F04"
    parent["execution_status"] = "implemented"
    parent["verification_status"] = "passed_bounded"
    parent["required_proof_class"] = "design"
    child["finding_id"] = "RC11-F04b"
    child["disposition_status"] = "open"
    child["execution_status"] = "unplanned"
    child["verification_status"] = "unverified"
    packet["findings"] = [parent, child]
    packet["edges"] = [
        {
            "type": "splits_into",
            "from": "RC11-F04",
            "to": "RC11-F04b",
            "status": "accepted",
        }
    ]
    packet["events"].append(
        {
            "event_id": "E-VER",
            "event_type": "verification_recorded",
            "at": "2026-08-12T00:00:00Z",
            "actor_class": "human",
            "finding_id": "RC11-F04",
            "payload": {
                "proof_class": "design",
                "tested_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "evidence_anchors": ["doc/adr/0024-review-case-intake-and-disposition.md"],
            },
        }
    )
    errors = validate_packet(packet, schema)
    assert any("cannot close while required children/blockers remain open" in e for e in errors)


def test_human_promotion_and_matching_proof_can_pass(schema: Mapping[str, Any]) -> None:
    packet = minimal_packet()
    packet["findings"][0]["disposition_status"] = "accepted_as_gap"
    packet["findings"][0]["required_proof_class"] = "docs"
    packet["findings"][0]["execution_status"] = "implemented"
    packet["findings"][0]["verification_status"] = "passed_bounded"
    packet["edges"].append(
        {
            "type": "promoted_to",
            "from": "RC11-F04",
            "to": "TSG-006",
            "status": "accepted",
        }
    )
    packet["events"].extend(
        [
            {
                "event_id": "E-DISP",
                "event_type": "disposition_recorded",
                "at": "2026-08-12T00:00:00Z",
                "actor_class": "human",
                "finding_id": "RC11-F04",
                "source_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                "rationale": "Accepted as tracked gap",
                "payload": {"disposition": "accepted_as_gap"},
            },
            {
                "event_id": "E-PROMO",
                "event_type": "edge_asserted",
                "at": "2026-08-12T00:00:01Z",
                "actor_class": "human",
                "finding_id": "RC11-F04",
                "payload": {
                    "edge_type": "promoted_to",
                    "from": "RC11-F04",
                    "to": "TSG-006",
                },
            },
            {
                "event_id": "E-VER",
                "event_type": "verification_recorded",
                "at": "2026-08-12T00:00:02Z",
                "actor_class": "human",
                "finding_id": "RC11-F04",
                "payload": {
                    "proof_class": "docs",
                    "tested_revision": "60fd8245ace999f3f29911844375dd7cc36a2a38",
                    "evidence_anchors": ["prd/architecture/temporal-semantic-gap-register.md"],
                },
            },
        ]
    )
    errors = validate_packet(packet, schema)
    assert errors == []
