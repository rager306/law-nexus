"""Filesystem adapter contracts for Review Case ports.

Root-confined I/O only. No disposition/promotion/GSD behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_nexus_harness.review_case import (
    ActorClass,
    EventType,
    NormalizationMethod,
    NormalizationRecord,
    NormalizationStatus,
    ReviewEvent,
    ReviewPacket,
    ReviewSource,
    SourceKind,
)
from law_nexus_harness.review_case.adapters.filesystem import (
    FilesystemReviewPacketStore,
    FilesystemReviewSourceReader,
)
from law_nexus_harness.review_case.adapters.pydantic_codec import dump_packet, load_packet
from law_nexus_harness.review_case.ports import (
    ReviewCasePortError,
    ReviewPacketStore,
    ReviewSourceReader,
)

HASH_A = "a" * 64
REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
SOURCE_REL = "doc/review/review-11-08-2026.md"
SOURCE_BYTES = b"# review fixture body\n"


def _packet(packet_id: str = "RC-2026-08-11-001") -> ReviewPacket:
    return ReviewPacket(
        packet_id=packet_id,
        source=ReviewSource(
            path=SOURCE_REL,
            content_sha256=HASH_A,
            reviewed_git_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
        ),
        normalization=NormalizationRecord(
            status=NormalizationStatus.DRAFT_EXTRACTED,
            method=NormalizationMethod.MANUAL,
            source_hash=HASH_A,
            extractor_version="fs-test/v1",
        ),
        non_claims=("Non-authoritative review projection",),
        findings=(),
        edges=(),
        events=(
            ReviewEvent(
                event_id=f"{packet_id}:packet_registered",
                event_type=EventType.PACKET_REGISTERED,
                at=TS,
                actor_class=ActorClass.TOOL,
                source_revision=REV,
                rationale="Register immutable review source as draft packet",
            ),
        ),
    )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    source = root / SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_bytes(SOURCE_BYTES)
    return root


def test_source_reader_protocol_and_positive_read(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    reader = FilesystemReviewSourceReader(root)
    assert isinstance(reader, ReviewSourceReader)
    assert reader.read_bytes(SOURCE_REL) == SOURCE_BYTES


def test_source_reader_rejects_missing_and_invalid_paths(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    reader = FilesystemReviewSourceReader(root)

    with pytest.raises(ReviewCasePortError) as missing:
        reader.read_bytes("doc/review/missing.md")
    assert missing.value.code == "source_not_found"

    for bad in (
        "/etc/passwd",
        "../outside.md",
        "doc/review/../secrets.md",
        "doc\\review\\x.md",
        "doc/review/with space.md",
        ".gsd/state.json",
        "python_archive/product/x.py",
        "",
    ):
        with pytest.raises(ReviewCasePortError) as exc:
            reader.read_bytes(bad)
        assert exc.value.code in {"invalid_path", "path_escape", "source_not_found"}


def test_source_reader_rejects_symlink_file_and_ancestor(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret-bytes")

    link = root / "doc/review/linked.md"
    link.symlink_to(outside)
    reader = FilesystemReviewSourceReader(root)
    with pytest.raises(ReviewCasePortError) as exc:
        reader.read_bytes("doc/review/linked.md")
    assert exc.value.code == "symlink_rejected"
    assert b"secret-bytes" not in str(exc.value).encode()

    nested_dir = root / "doc/review/nested"
    nested_dir.mkdir()
    nested_dir.rmdir()
    nested_link = root / "doc/review/nested"
    nested_link.symlink_to(tmp_path)
    (tmp_path / "file.md").write_bytes(b"via-ancestor")
    with pytest.raises(ReviewCasePortError) as exc:
        reader.read_bytes("doc/review/nested/file.md")
    assert exc.value.code == "symlink_rejected"


def test_packet_store_roundtrip_and_deterministic_list(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    assert isinstance(store, ReviewPacketStore)

    first = _packet("RC-2026-08-11-001")
    second = _packet("RC-2026-08-11-002")
    store.add(second)
    store.add(first)

    loaded = store.get("RC-2026-08-11-001")
    assert loaded == first
    listed = store.list_all()
    assert [item.packet_id for item in listed] == [
        "RC-2026-08-11-001",
        "RC-2026-08-11-002",
    ]
    assert listed[0] == first
    assert listed[1] == second

    # Wire bytes under packets dir are codec-canonical and loadable.
    on_disk = (store.packets_dir / "RC-2026-08-11-001.json").read_bytes()
    assert on_disk == dump_packet(first)
    assert load_packet(on_disk) == first


def test_packet_store_rejects_duplicate_and_invalid_id(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    packet = _packet()
    store.add(packet)
    with pytest.raises(ReviewCasePortError) as dup:
        store.add(packet)
    assert dup.value.code == "duplicate_packet"

    with pytest.raises(ReviewCasePortError) as bad_id:
        store.add(_packet("../escape"))
    assert bad_id.value.code == "invalid_packet_id"


def test_packet_store_rejects_corrupt_and_missing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    store.add(_packet())
    target = store.packets_dir / "RC-2026-08-11-001.json"
    target.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ReviewCasePortError) as corrupt:
        store.get("RC-2026-08-11-001")
    assert corrupt.value.code == "corrupt_packet"

    with pytest.raises(ReviewCasePortError) as missing:
        store.get("RC-missing")
    assert missing.value.code == "packet_not_found"


def test_packet_store_atomic_write_and_interrupted_temp(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    leftover = store.packets_dir
    leftover.mkdir(parents=True, exist_ok=True)
    temp = leftover / ".RC-2026-08-11-001.json.tmp"
    temp.write_bytes(b"partial")
    # Leftover temp must not be treated as a packet, and add still works after cleanup path.
    assert store.list_all() == ()
    store.add(_packet())
    assert (store.packets_dir / "RC-2026-08-11-001.json").is_file()
    # leftover temp may remain; it must not appear in list_all
    assert [p.packet_id for p in store.list_all()] == ["RC-2026-08-11-001"]


def test_packet_store_rejects_symlink_packet_and_directory(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    store.add(_packet("RC-A"))
    # Replace packet with symlink to outside content.
    outside = tmp_path / "evil.json"
    outside.write_bytes(dump_packet(_packet("RC-A")))
    target = store.packets_dir / "RC-A.json"
    target.unlink()
    target.symlink_to(outside)
    with pytest.raises(ReviewCasePortError) as exc:
        store.get("RC-A")
    assert exc.value.code == "symlink_rejected"

    # Symlinked store directory is rejected at construction / access.
    store2_root = tmp_path / "repo2"
    store2_root.mkdir()
    real_packets = tmp_path / "real-packets"
    real_packets.mkdir()
    linked = store2_root / "prd/architecture/review-cases/packets"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(real_packets)
    with pytest.raises(ReviewCasePortError) as list_exc:
        FilesystemReviewPacketStore(store2_root)
    assert list_exc.value.code == "symlink_rejected"


def test_packet_store_rejects_paths_outside_dedicated_projection_root(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    for forbidden in (
        "doc/adr/review-packets",
        "prd/architecture",
        "prd/architecture/review-cases",
        "prd/architecture/review-cases/fixtures",
        "prd/architecture/review-cases/other",
        "prd/PRODUCT.md",
        "prd/REQUIREMENTS.md",
    ):
        with pytest.raises(ReviewCasePortError) as exc:
            FilesystemReviewPacketStore(root, packets_dir=forbidden)
        assert exc.value.code == "invalid_store_path"


def test_packet_store_default_path_not_authority_or_gsd(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    store = FilesystemReviewPacketStore(root)
    store.add(_packet())
    rel = str(store.packets_dir.relative_to(root)).replace("\\", "/")
    assert rel == "prd/architecture/review-cases/packets"
    assert not rel.startswith(".gsd/")
    assert "doc/adr" not in rel
    assert "prd/ARCHITECTURE.md" not in rel


def test_integration_register_via_filesystem_adapters(tmp_path: Path) -> None:
    import hashlib

    from law_nexus_harness.review_case.application import (
        RegisterReviewCaseCommand,
        register_review_case,
        validate_review_cases,
    )

    class HashlibAdapter:
        def sha256(self, data: bytes) -> str:
            return hashlib.sha256(data).hexdigest()

    root = _repo(tmp_path)
    reader = FilesystemReviewSourceReader(root)
    store = FilesystemReviewPacketStore(root)
    report = register_review_case(
        RegisterReviewCaseCommand(
            packet_id="RC-FS-001",
            source_path=SOURCE_REL,
            reviewed_revision=REV,
            received_at=TS,
            source_kind=SourceKind.HUMAN_EXTERNAL,
            normalization_method=NormalizationMethod.MANUAL,
            non_claims=("fixture non-claim",),
            extractor_version="fs-test/v1",
        ),
        reader,
        HashlibAdapter(),
        store,
    )
    assert report.authoritative is False
    assert report.authority_required is True
    assert report.content_sha256 == hashlib.sha256(SOURCE_BYTES).hexdigest()
    assert store.get("RC-FS-001").packet_id == "RC-FS-001"
    validation = validate_review_cases(reader, HashlibAdapter(), store)
    assert validation.ok is True
    assert validation.packet_count == 1
