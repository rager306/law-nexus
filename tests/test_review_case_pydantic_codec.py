"""Outer Pydantic codec contracts for review-case/v1.

Adapter-only. Pure domain remains authority-free of pydantic types.
Tracked schema remains explicit wire authority.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DispositionStatus,
    EventType,
    ExecutionStatus,
    Finding,
    FindingKind,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ProofClass,
    RelationStatus,
    RelationType,
    ReviewEdge,
    ReviewerSeverity,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
    assert_relation,
    record_disposition,
    record_verification,
)
from law_nexus_harness.review_case.adapters.pydantic_codec import (
    ReviewCaseCodecError,
    dump_packet,
    generated_wire_schema,
    load_packet,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "prd/architecture/review-case.schema.json"
ADAPTER_PATH = ROOT / "src/law_nexus_harness/review_case/adapters/pydantic_codec.py"
INNER_MODULES = (
    ROOT / "src/law_nexus_harness/review_case/domain.py",
    ROOT / "src/law_nexus_harness/review_case/policy.py",
    ROOT / "src/law_nexus_harness/review_case/application.py",
    ROOT / "src/law_nexus_harness/review_case/ports.py",
)

HASH_A = "a" * 64
HASH_B = "b" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
TS2 = "2026-08-12T00:00:00Z"
PATH = "doc/review/review-11-08-2026.md"
ANCHOR = "tests/test_review_case_pydantic_codec.py"


def minimal_registration_packet() -> ReviewPacket:
    return ReviewPacket(
        packet_id="RC-2026-08-11-001",
        source=ReviewSource(
            path=PATH,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.DRAFT_EXTRACTED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
            extractor_version="codec-test/v1",
        ),
        non_claims=("Non-authoritative review projection",),
        findings=(),
        edges=(),
        events=(
            ReviewEvent(
                event_id="RC-2026-08-11-001:packet_registered",
                event_type=EventType.PACKET_REGISTERED,
                at=TS,
                actor_class=ActorClass.TOOL,
                source_revision=REV,
                rationale="Register immutable review source as draft packet",
            ),
        ),
    )


def richer_policy_packet() -> ReviewPacket:
    base = ReviewPacket(
        packet_id="RC-2026-08-11-002",
        source=ReviewSource(
            path=PATH,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.SOURCE_VERIFIED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
        ),
        non_claims=("Non-authoritative review projection",),
        findings=(
            Finding(
                finding_id="RC11-F01",
                kind=FindingKind.GAP,
                concern_class=ConcernClass.DESIGN,
                reviewer_severity=ReviewerSeverity.CRITICAL,
                summary="Missing process contour",
                source_spans=(
                    SourceSpan(
                        path=PATH,
                        line_start=10,
                        line_end=20,
                        quote_sha256=HASH_B,
                        heading="# Gap",
                    ),
                ),
                candidate_targets=(
                    CandidateTarget(
                        surface=CandidateSurface.TSG,
                        id="TSG-006",
                        note="candidate only",
                    ),
                ),
                required_proof_class=ProofClass.IMPLEMENTATION,
                normalization_status=NormalizationStatus.SOURCE_VERIFIED,
                disposition_status=DispositionStatus.OPEN,
                execution_status=ExecutionStatus.IMPLEMENTED,
                verification_status=VerificationStatus.UNVERIFIED,
                non_claims=("Not an accepted requirement",),
            ),
        ),
        edges=(
            ReviewEdge(
                type=RelationType.MAPS_TO,
                from_id="RC11-F01",
                to_id="TSG-006",
                status=RelationStatus.CANDIDATE,
            ),
        ),
        events=(),
    )
    disposed = record_disposition(
        base,
        ReviewEvent(
            event_id="E-DISP-1",
            event_type=EventType.DISPOSITION_RECORDED,
            at=TS2,
            actor_class=ActorClass.HUMAN,
            finding_id="RC11-F01",
            source_revision=REV,
            rationale="Human disposition",
            disposition=DispositionStatus.ACCEPTED_AS_GAP,
        ),
    )
    promoted = assert_relation(
        disposed,
        ReviewEdge(
            type=RelationType.PROMOTED_TO,
            from_id="RC11-F01",
            to_id="TSG-006",
            status=RelationStatus.ACCEPTED,
        ),
        ReviewEvent(
            event_id="E-EDGE-1",
            event_type=EventType.EDGE_ASSERTED,
            at=TS2,
            actor_class=ActorClass.HUMAN,
            finding_id="RC11-F01",
            source_revision=REV,
            rationale="Human promotion",
            edge_type=RelationType.PROMOTED_TO,
            from_id="RC11-F01",
            to_id="TSG-006",
        ),
    )
    return record_verification(
        promoted,
        ReviewEvent(
            event_id="E-VER-1",
            event_type=EventType.VERIFICATION_RECORDED,
            at=TS2,
            actor_class=ActorClass.HUMAN,
            finding_id="RC11-F01",
            source_revision=REV,
            rationale="Record class-matched proof",
            proof_class=ProofClass.IMPLEMENTATION,
            verification_result=VerificationStatus.PASSED_BOUNDED,
            tested_revision=REV,
            evidence_anchors=(ANCHOR,),
            completed_scope=("pure proof recorded",),
            residual_scope=(),
            non_claims=("No product readiness claim",),
        ),
        status=VerificationStatus.PASSED_BOUNDED,
    )


def _as_dict(packet: ReviewPacket) -> dict:
    return json.loads(dump_packet(packet).decode("utf-8"))


def test_minimal_registration_roundtrip() -> None:
    packet = minimal_registration_packet()
    loaded = load_packet(dump_packet(packet))
    assert loaded == packet


def test_richer_policy_roundtrip() -> None:
    packet = richer_policy_packet()
    loaded = load_packet(dump_packet(packet))
    assert loaded == packet


def test_dump_is_deterministic_and_canonical() -> None:
    packet = richer_policy_packet()
    first = dump_packet(packet)
    second = dump_packet(packet)
    assert first == second
    assert not first.endswith(b"\n")
    decoded = json.loads(first.decode("utf-8"))
    # sorted keys at every object level is enforced by dump path
    assert list(decoded.keys()) == sorted(decoded.keys())
    assert list(decoded["source"].keys()) == sorted(decoded["source"].keys())
    event = decoded["events"][-1]
    assert "payload" in event
    assert list(event["payload"].keys()) == sorted(event["payload"].keys())
    assert load_packet(first) == packet
    assert load_packet(dump_packet(load_packet(first))) == packet


def test_load_rejects_coercions_and_unknown_fields() -> None:
    packet = minimal_registration_packet()
    payload = _as_dict(packet)

    bad_line = json.loads(json.dumps(payload))
    bad_line["findings"] = [
        {
            "finding_id": "RC11-F01",
            "kind": "gap",
            "concern_class": "design",
            "reviewer_severity": "critical",
            "summary": "x",
            "source_spans": [
                {
                    "path": PATH,
                    "line_start": "10",
                    "line_end": 20,
                    "quote_sha256": HASH_B,
                }
            ],
            "candidate_targets": [],
            "required_proof_class": "implementation",
            "normalization_status": "source_verified",
            "disposition_status": "open",
            "execution_status": "unplanned",
            "verification_status": "unverified",
            "non_claims": ["n"],
        }
    ]
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(bad_line).encode("utf-8"))
    assert exc.value.code == "wire_validation"

    unknown_root = dict(payload)
    unknown_root["unexpected"] = True
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(unknown_root).encode("utf-8"))
    assert exc.value.code == "wire_validation"

    unknown_nested = json.loads(json.dumps(payload))
    unknown_nested["source"]["extra"] = "nope"
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(unknown_nested).encode("utf-8"))
    assert exc.value.code == "wire_validation"

    richer = _as_dict(richer_policy_packet())
    richer["events"][-1]["payload"]["unexpected"] = "nope"
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(richer).encode("utf-8"))
    assert exc.value.code == "wire_validation"


def test_load_rejects_non_boolean_authority_constants() -> None:
    packet = minimal_registration_packet()
    for field, values in (
        ("authoritative", (0, 1, "false")),
        ("authority_required", (0, 1, "true")),
    ):
        for value in values:
            payload = _as_dict(packet)
            payload[field] = value
            with pytest.raises(ReviewCaseCodecError) as exc:
                load_packet(json.dumps(payload).encode("utf-8"))
            assert exc.value.code == "wire_validation"


def test_load_rejects_authority_true_and_schema_mismatch() -> None:
    packet = minimal_registration_packet()
    payload = _as_dict(packet)
    payload["authoritative"] = True
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "wire_validation"

    payload = _as_dict(packet)
    payload["schema_version"] = "review-case/v0"
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "wire_validation"


def test_load_rejects_invalid_json_and_missing_span() -> None:
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(b"{not-json")
    assert exc.value.code == "invalid_json"
    assert "SECRET" not in exc.value.message

    packet = richer_policy_packet()
    payload = _as_dict(packet)
    payload["findings"][0]["source_spans"] = []
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code in {"wire_validation", "policy_validation", "domain_validation"}


def test_load_rejects_wrong_enum_and_policy_mismatch() -> None:
    packet = richer_policy_packet()
    payload = _as_dict(packet)
    payload["findings"][0]["kind"] = "not-a-kind"
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "wire_validation"

    payload = _as_dict(packet)
    payload["findings"][0]["disposition_status"] = "accepted_as_gap"
    # drop disposition event to force policy mismatch while keeping wire shape
    payload["events"] = [
        event for event in payload["events"] if event["event_type"] != "disposition_recorded"
    ]
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "policy_validation"


def test_load_rejects_partial_proof_without_completed_scope() -> None:
    payload = _as_dict(richer_policy_packet())
    verification = next(
        event for event in payload["events"] if event["event_type"] == "verification_recorded"
    )
    verification["payload"]["completed_scope"] = []
    verification["payload"]["residual_scope"] = ["still open"]
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "policy_validation"


def test_duplicate_tested_revision_is_rejected() -> None:
    packet = richer_policy_packet()
    payload = _as_dict(packet)
    for event in payload["events"]:
        if event["event_type"] == "verification_recorded":
            event["tested_revision"] = REV
            break
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(json.dumps(payload).encode("utf-8"))
    assert exc.value.code == "wire_validation"
    assert "tested_revision" in ".".join(str(part) for part in exc.value.field_path)


def test_codec_error_is_safe_and_structured() -> None:
    secret = b'{"schema_version":"review-case/v1","authoritative":false,"SECRET":"should-not-leak"'
    with pytest.raises(ReviewCaseCodecError) as exc:
        load_packet(secret)
    assert isinstance(exc.value.field_path, tuple)
    assert isinstance(exc.value.code, str) and exc.value.code
    assert isinstance(exc.value.message, str) and exc.value.message
    rendered = str(exc.value)
    assert "should-not-leak" not in rendered
    assert b"should-not-leak" not in rendered.encode("utf-8", errors="ignore")


def test_generated_schema_fidelity_against_tracked_schema() -> None:
    tracked = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    generated = generated_wire_schema()
    assert generated["properties"]["schema_version"]["const"] == "review-case/v1"
    assert generated["properties"]["authoritative"]["const"] is False
    assert generated["properties"]["authority_required"]["const"] is True
    assert generated["additionalProperties"] is False

    defs = generated["$defs"]
    assert set(defs["FindingKind"]["enum"]) == set(
        tracked["$defs"]["finding"]["properties"]["kind"]["enum"]
    )
    enum_pairs = (
        ("NormalizationStatus", "normalization_status"),
        ("DispositionStatus", "disposition_status"),
        ("ExecutionStatus", "execution_status"),
        ("VerificationStatus", "verification_status"),
    )
    for generated_name, tracked_axis in enum_pairs:
        assert set(defs[generated_name]["enum"]) == set(
            tracked["$defs"]["finding"]["properties"][tracked_axis]["enum"]
        )

    assert set(defs["RelationType"]["enum"]) == set(
        tracked["$defs"]["edge"]["properties"]["type"]["enum"]
    )
    assert set(defs["EventType"]["enum"]) == set(
        tracked["$defs"]["event"]["properties"]["event_type"]["enum"]
    )
    assert set(defs["ActorClass"]["enum"]) == set(
        tracked["$defs"]["event"]["properties"]["actor_class"]["enum"]
    )
    assert set(defs["ProofClass"]["enum"]) == set(tracked["$defs"]["proof_class"]["enum"])
    generated_result = defs["EventPayloadWire"]["properties"]["verification_result"]
    generated_result_enum = next(
        item["enum"] for item in generated_result["anyOf"] if "enum" in item
    )
    assert set(generated_result_enum) == set(
        tracked["$defs"]["event"]["properties"]["payload"]["properties"]["verification_result"][
            "enum"
        ]
    )
    assert defs["FindingWire"]["additionalProperties"] is False
    assert defs["EventPayloadWire"]["additionalProperties"] is False


def test_adapter_boundary_imports() -> None:
    adapter_tree = ast.parse(ADAPTER_PATH.read_text(encoding="utf-8"))
    adapter_imports: list[str] = []
    for node in ast.walk(adapter_tree):
        if isinstance(node, ast.Import):
            adapter_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            adapter_imports.append(node.module)
    assert any(name == "pydantic" or name.startswith("pydantic.") for name in adapter_imports)
    assert not any(name == "adaptix" or name.startswith("adaptix.") for name in adapter_imports)

    for path in INNER_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for module in imported:
                root = module.split(".", 1)[0]
                assert root != "pydantic"
                assert root != "adaptix"


def test_public_api_does_not_export_basemodel() -> None:
    packet = minimal_registration_packet()
    loaded = load_packet(dump_packet(packet))
    assert type(loaded).__module__.startswith("law_nexus_harness.review_case.domain")
    assert type(loaded).__name__ == "ReviewPacket"
