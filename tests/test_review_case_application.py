"""Application/port contracts for pure Review Case use cases.

In-memory adapters only. No filesystem, codec, CLI, Governor, GSD, or
product-domain semantics.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import pytest

from law_nexus_harness.review_case import (
    DerivedStatus,
    NormalizationMethod,
    SourceKind,
    register_review_case,
    review_case_status,
    validate_review_cases,
)
from law_nexus_harness.review_case.application import (
    APP_REPORT_SCHEMA_VERSION,
    RegisterReviewCaseCommand,
    ReviewCaseApplicationError,
)
from law_nexus_harness.review_case.ports import (
    ContentHasher,
    ReviewCasePortError,
    ReviewPacketStore,
    ReviewSourceReader,
)

REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
SOURCE_PATH = "doc/review/review-11-08-2026.md"
SOURCE_BYTES = b"# review\nfinding text\n"


@dataclass
class InMemorySourceReader:
    payloads: dict[str, bytes] = field(default_factory=dict)
    fail_code: str | None = None
    calls: list[str] = field(default_factory=list)

    def read_bytes(self, repo_relative_path: str) -> bytes:
        self.calls.append(repo_relative_path)
        if self.fail_code is not None:
            raise ReviewCasePortError(
                code=self.fail_code,
                operation="read_bytes",
                message="source reader failed",
            )
        if repo_relative_path not in self.payloads:
            raise ReviewCasePortError(
                code="source_not_found",
                operation="read_bytes",
                message="source path is missing",
            )
        return self.payloads[repo_relative_path]


@dataclass
class InMemoryHasher:
    fail_code: str | None = None

    def sha256(self, data: bytes) -> str:
        if self.fail_code is not None:
            raise ReviewCasePortError(
                code=self.fail_code,
                operation="sha256",
                message="hasher failed",
            )
        return hashlib.sha256(data).hexdigest()


@dataclass
class InMemoryPacketStore:
    packets: dict[str, Any] = field(default_factory=dict)
    fail_on_add: str | None = None
    fail_on_get: str | None = None
    fail_on_list: str | None = None

    def add(self, packet: Any) -> None:
        if self.fail_on_add is not None:
            raise ReviewCasePortError(
                code=self.fail_on_add,
                operation="add",
                message="store add failed",
            )
        packet_id = packet.packet_id
        if packet_id in self.packets:
            raise ReviewCasePortError(
                code="duplicate_packet",
                operation="add",
                message="packet already exists",
            )
        self.packets[packet_id] = packet

    def get(self, packet_id: str) -> Any:
        if self.fail_on_get is not None:
            raise ReviewCasePortError(
                code=self.fail_on_get,
                operation="get",
                message="store get failed",
            )
        if packet_id not in self.packets:
            raise ReviewCasePortError(
                code="packet_not_found",
                operation="get",
                message="packet is missing",
            )
        return self.packets[packet_id]

    def list_all(self) -> tuple[Any, ...]:
        if self.fail_on_list is not None:
            raise ReviewCasePortError(
                code=self.fail_on_list,
                operation="list_all",
                message="store list failed",
            )
        return tuple(self.packets[key] for key in sorted(self.packets))


def command(**overrides: Any) -> RegisterReviewCaseCommand:
    payload: dict[str, Any] = {
        "packet_id": "RC-2026-08-11-001",
        "source_path": SOURCE_PATH,
        "reviewed_revision": REV,
        "received_at": TS,
        "source_kind": SourceKind.HUMAN_EXTERNAL,
        "normalization_method": NormalizationMethod.MANUAL,
        "non_claims": ("Non-authoritative review projection",),
    }
    payload.update(overrides)
    return RegisterReviewCaseCommand(**payload)


def adapters(
    *,
    source_bytes: bytes = SOURCE_BYTES,
    source_path: str = SOURCE_PATH,
) -> tuple[InMemorySourceReader, InMemoryHasher, InMemoryPacketStore]:
    reader = InMemorySourceReader(payloads={source_path: source_bytes})
    return reader, InMemoryHasher(), InMemoryPacketStore()


def test_ports_are_protocol_compatible() -> None:
    reader, hasher, store = adapters()
    assert isinstance(reader, ReviewSourceReader)
    assert isinstance(hasher, ContentHasher)
    assert isinstance(store, ReviewPacketStore)


def test_register_review_case_is_atomic_and_non_authoritative() -> None:
    reader, hasher, store = adapters()
    report = register_review_case(command(), reader, hasher, store)
    assert report.schema_version == APP_REPORT_SCHEMA_VERSION
    assert report.authoritative is False
    assert report.authority_required is True
    assert report.packet_id == "RC-2026-08-11-001"
    assert report.source_path == SOURCE_PATH
    assert report.content_sha256 == hashlib.sha256(SOURCE_BYTES).hexdigest()
    assert report.finding_count == 0
    assert "Non-authoritative" in " ".join(report.non_claims)
    assert len(store.packets) == 1
    stored = store.get("RC-2026-08-11-001")
    assert stored.findings == ()
    assert stored.normalization.source_hash == report.content_sha256
    assert stored.source.content_sha256 == report.content_sha256


def test_registration_command_fails_before_any_port_io() -> None:
    invalid_commands = (
        command(source_path="/etc/passwd"),
        command(source_path="../escape.md"),
        command(source_path=".gsd/STATE.md"),
        command(source_path="prd/archive/review.md"),
        command(reviewed_revision="not-a-revision"),
        command(non_claims=()),
    )
    for invalid in invalid_commands:
        reader, hasher, store = adapters()
        with pytest.raises(ReviewCaseApplicationError) as exc:
            register_review_case(invalid, reader, hasher, store)
        assert exc.value.cause_code == "validation"
        assert reader.calls == []
        assert store.packets == {}


def test_register_duplicate_and_port_failures_leave_store_empty() -> None:
    reader, hasher, store = adapters()
    register_review_case(command(), reader, hasher, store)
    with pytest.raises(ReviewCaseApplicationError) as exc:
        register_review_case(command(), reader, hasher, store)
    assert exc.value.code == "duplicate_packet"
    assert len(store.packets) == 1

    empty_store = InMemoryPacketStore()
    missing_reader = InMemorySourceReader()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        register_review_case(command(), missing_reader, hasher, empty_store)
    assert exc.value.code == "source_not_found"
    assert empty_store.packets == {}

    fail_store = InMemoryPacketStore(fail_on_add="store_unavailable")
    with pytest.raises(ReviewCaseApplicationError) as exc:
        register_review_case(command(), reader, hasher, fail_store)
    assert exc.value.code == "store_unavailable"
    assert fail_store.packets == {}

    fail_hasher = InMemoryHasher(fail_code="hash_failed")
    with pytest.raises(ReviewCaseApplicationError) as exc:
        register_review_case(command(), reader, fail_hasher, InMemoryPacketStore())
    assert exc.value.code == "hash_failed"


def test_validate_and_status_positive_flow() -> None:
    reader, hasher, store = adapters()
    register_review_case(command(), reader, hasher, store)
    validation = validate_review_cases(reader, hasher, store)
    assert validation.schema_version == APP_REPORT_SCHEMA_VERSION
    assert validation.authoritative is False
    assert validation.packet_count == 1
    assert validation.finding_count == 0
    assert validation.open_count == 0
    assert validation.blocked_count == 0
    assert validation.partial_count == 0
    assert validation.closed_count == 0
    assert validation.stale_count == 0
    assert validation.ok is True

    status = review_case_status(store, packet_id="RC-2026-08-11-001")
    assert status.schema_version == APP_REPORT_SCHEMA_VERSION
    assert status.authoritative is False
    assert status.packets == (
        (
            "RC-2026-08-11-001",
            SOURCE_PATH,
            REV,
            hashlib.sha256(SOURCE_BYTES).hexdigest(),
            (),
        ),
    )
    assert status.open_blockers == ()
    assert "Non-authoritative" in " ".join(status.non_claims)


def test_validate_detects_source_hash_drift_and_missing_source() -> None:
    reader, hasher, store = adapters()
    register_review_case(command(), reader, hasher, store)
    reader.payloads[SOURCE_PATH] = b"mutated source bytes"
    with pytest.raises(ReviewCaseApplicationError) as exc:
        validate_review_cases(reader, hasher, store)
    assert exc.value.code == "source_hash_drift"
    assert SOURCE_BYTES not in repr(exc.value).encode("utf-8", errors="ignore")

    missing = InMemorySourceReader()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        validate_review_cases(missing, hasher, store)
    assert exc.value.code == "source_not_found"


def test_status_all_packets_is_ordered_and_does_not_reread_source() -> None:
    reader, hasher, store = adapters()
    register_review_case(command(packet_id="RC-B"), reader, hasher, store)
    register_review_case(
        command(packet_id="RC-A", source_path="doc/review/review-12-08-2026.md"),
        InMemorySourceReader(payloads={"doc/review/review-12-08-2026.md": b"second"}),
        hasher,
        store,
    )
    # Mutating reader after registration must not affect pure status projection.
    reader.payloads.clear()
    status = review_case_status(store)
    assert [item[0] for item in status.packets] == ["RC-A", "RC-B"]
    assert all(item[4] == () for item in status.packets)


def test_status_missing_packet_and_store_failures() -> None:
    store = InMemoryPacketStore()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        review_case_status(store, packet_id="missing")
    assert exc.value.code == "packet_not_found"

    store.fail_on_list = "store_unavailable"
    with pytest.raises(ReviewCaseApplicationError) as exc:
        review_case_status(store)
    assert exc.value.code == "store_unavailable"


def test_application_errors_do_not_embed_raw_bytes() -> None:
    secret = b"SECRET-REVIEW-BYTES-SHOULD-NOT-LEAK"
    reader = InMemorySourceReader()
    hasher = InMemoryHasher()
    store = InMemoryPacketStore()
    with pytest.raises(ReviewCaseApplicationError) as exc:
        register_review_case(command(), reader, hasher, store)
    rendered = str(exc.value)
    assert "SECRET-REVIEW-BYTES-SHOULD-NOT-LEAK" not in rendered
    assert secret not in rendered.encode("utf-8", errors="ignore")


def test_no_semantic_promotion_or_gsd_creation_surface() -> None:
    reader, hasher, store = adapters()
    report = register_review_case(command(), reader, hasher, store)
    assert not hasattr(report, "milestone_id")
    assert not hasattr(report, "requirement_id")
    assert not hasattr(report, "promoted_to")
    status = review_case_status(store)
    for packet_row in status.packets:
        for finding_row in packet_row[4]:
            assert finding_row[1] in {status.value for status in DerivedStatus}
