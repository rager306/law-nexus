"""Pure-domain contracts for Review Case value objects.

Non-authoritative process types only. No filesystem I/O, codecs, CLI, Governor,
GSD, or product-domain semantics.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    SCHEMA_VERSION,
    CandidateSurface,
    CandidateTarget,
    ConcernClass,
    DispositionStatus,
    ExecutionStatus,
    Finding,
    FindingKind,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ProofClass,
    ReviewCaseValidationError,
    ReviewCaseViolation,
    ReviewerSeverity,
    ReviewPacket,
    ReviewSource,
    SourceKind,
    SourceSpan,
    VerificationStatus,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
SOURCE_PATH = "doc/review/review-11-08-2026.md"


def valid_source(**overrides: Any) -> ReviewSource:
    payload: dict[str, Any] = {
        "path": SOURCE_PATH,
        "content_sha256": HASH_A,
        "reviewed_git_revision": REV,
        "received_at": TS,
        "source_kind": SourceKind.HUMAN_EXTERNAL,
    }
    payload.update(overrides)
    return ReviewSource(**payload)


def valid_normalization(**overrides: Any) -> NormalizationRecord:
    payload: dict[str, Any] = {
        "status": NormalizationStatus.SOURCE_VERIFIED,
        "method": NormalizationMethod.MANUAL,
        "source_hash": HASH_A,
    }
    payload.update(overrides)
    return NormalizationRecord(**payload)


def valid_span(**overrides: Any) -> SourceSpan:
    payload: dict[str, Any] = {
        "path": SOURCE_PATH,
        "line_start": 10,
        "line_end": 20,
        "quote_sha256": HASH_B,
        "heading": "# Gap",
    }
    payload.update(overrides)
    return SourceSpan(**payload)


def valid_finding(finding_id: str = "RC11-F01", **overrides: Any) -> Finding:
    payload: dict[str, Any] = {
        "finding_id": finding_id,
        "kind": FindingKind.GAP,
        "concern_class": ConcernClass.DESIGN,
        "reviewer_severity": ReviewerSeverity.CRITICAL,
        "summary": "Missing process contour",
        "source_spans": (valid_span(),),
        "candidate_targets": (
            CandidateTarget(surface=CandidateSurface.TSG, id="TSG-006", note="candidate only"),
        ),
        "required_proof_class": ProofClass.IMPLEMENTATION,
        "normalization_status": NormalizationStatus.SOURCE_VERIFIED,
        "disposition_status": DispositionStatus.OPEN,
        "execution_status": ExecutionStatus.UNPLANNED,
        "verification_status": VerificationStatus.UNVERIFIED,
        "non_claims": ("Not an accepted requirement",),
    }
    payload.update(overrides)
    return Finding(**payload)


def valid_packet(**overrides: Any) -> ReviewPacket:
    payload: dict[str, Any] = {
        "packet_id": "RC-2026-08-11-001",
        "source": valid_source(),
        "normalization": valid_normalization(),
        "non_claims": ("Non-authoritative review projection",),
        "findings": (valid_finding(),),
    }
    payload.update(overrides)
    return ReviewPacket(**payload)


def codes(exc: ReviewCaseValidationError) -> set[str]:
    return {item.code for item in exc.violations}


def test_public_exports_and_constants() -> None:
    assert SCHEMA_VERSION == "review-case/v1"
    packet = valid_packet()
    assert packet.schema_version == SCHEMA_VERSION
    assert packet.authoritative is False
    assert packet.authority_required is True


def test_mutable_or_string_collections_are_rejected() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(source_spans=[valid_span()])
    assert "invalid_collection" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(candidate_targets=[])
    assert "invalid_collection" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(non_claims="not a tuple")
    assert "invalid_collection" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(findings=[valid_finding()])
    assert "invalid_collection" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(non_claims=["mutable"])
    assert "invalid_collection" in codes(exc.value)


def test_proof_class_is_distinct_from_concern_class() -> None:
    finding = valid_finding(required_proof_class=ProofClass.IMPLEMENTATION)
    assert finding.required_proof_class is ProofClass.IMPLEMENTATION
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(required_proof_class=ConcernClass.IMPLEMENTATION)
    assert "invalid_enum" in codes(exc.value)


def test_valid_packet_is_immutable() -> None:
    packet = valid_packet()
    with pytest.raises(Exception):
        setattr(packet, "packet_id", "changed")
    with pytest.raises(Exception):
        setattr(packet.findings[0], "summary", "mutated")
    assert isinstance(packet.findings, tuple)
    assert isinstance(packet.non_claims, tuple)
    assert isinstance(packet.findings[0].source_spans, tuple)


def test_packet_rejects_writable_authority_and_derived_fields() -> None:
    init_fields = {item.name for item in fields(ReviewPacket) if item.init}
    all_fields = {item.name for item in fields(ReviewPacket)}
    assert "authoritative" not in init_fields
    assert "authority_required" not in init_fields
    assert "schema_version" not in init_fields
    assert "derived_status" not in all_fields
    packet = valid_packet()
    assert packet.authoritative is False
    assert packet.authority_required is True
    assert packet.schema_version == SCHEMA_VERSION
    with pytest.raises(Exception):
        setattr(packet, "authoritative", True)
    with pytest.raises(AttributeError):
        getattr(packet, "derived_status")


def test_source_and_normalization_hash_must_match() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(normalization=valid_normalization(source_hash=HASH_C))
    assert "source_hash_mismatch" in codes(exc.value)


def test_invalid_ids_and_empty_text_fail() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(packet_id=" ")
    assert "empty_id" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(summary="")
    assert "empty_text" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(non_claims=())
    assert "missing_non_claims" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(non_claims=(" ",))
    assert "empty_text" in codes(exc.value)


def test_path_invariants() -> None:
    for bad in (
        "/tmp/x.md",
        "../escape.md",
        "doc//double.md",
        "doc/./x.md",
        "doc\\win.md",
        " doc/x.md",
        "doc/x.md ",
        "doc/x\t.md",
        "doc/x\ny.md",
        "http:evil/x.md",
        "file:doc/x.md",
        "C:docs/x.md",
        ".gsd/STATE.md",
        ".agents/skills/x.md",
        "Old_project/x.md",
        "python_archive/x.md",
        "prd/archive/x.md",
        "",
        ".",
    ):
        with pytest.raises(ReviewCaseValidationError) as exc:
            valid_source(path=bad)
        assert "invalid_path" in codes(exc.value)


def test_hash_and_revision_invariants() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(content_sha256="A" * 64)
    assert "invalid_sha256" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(content_sha256="a" * 63)
    assert "invalid_sha256" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(reviewed_git_revision="not-a-revision")
    assert "invalid_git_revision" in codes(exc.value)


def test_timestamp_requires_explicit_timezone() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(received_at="2026-08-11T10:33:40")
    assert "invalid_timestamp" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(received_at="not-a-timestamp")
    assert "invalid_timestamp" in codes(exc.value)

    assert valid_source(received_at="2026-08-11T10:33:40+00:00").received_at.endswith("+00:00")


def test_span_line_range_and_path_alignment() -> None:
    for line_start, line_end in ((0, 1), (True, 2), (1, False)):
        with pytest.raises(ReviewCaseValidationError) as exc:
            valid_span(line_start=line_start, line_end=line_end)
        assert "invalid_line_range" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_span(line_start=20, line_end=10)
    assert "invalid_line_range" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(
            findings=(
                valid_finding(
                    source_spans=(valid_span(path="doc/review/other.md"),),
                ),
            )
        )
    assert "span_path_mismatch" in codes(exc.value)


def test_finding_requires_span_and_unique_ids() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_finding(source_spans=())
    assert "missing_source_spans" in codes(exc.value)

    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_packet(findings=(valid_finding("RC11-F01"), valid_finding("RC11-F01")))
    assert "duplicate_finding_id" in codes(exc.value)


def test_candidate_target_and_optional_note() -> None:
    target = CandidateTarget(surface=CandidateSurface.ADR, id="ADR-0024")
    assert target.note is None
    with pytest.raises(ReviewCaseValidationError) as exc:
        CandidateTarget(surface=CandidateSurface.ADR, id=" ")
    assert "empty_id" in codes(exc.value)


def test_validation_error_is_structured() -> None:
    with pytest.raises(ReviewCaseValidationError) as exc:
        valid_source(path="/abs.md", content_sha256="nope", reviewed_git_revision="short")
    assert isinstance(exc.value.violations[0], ReviewCaseViolation)
    assert all(item.field_path for item in exc.value.violations)
    assert all(item.message for item in exc.value.violations)
    assert any(item.code == "invalid_path" for item in exc.value.violations)
