"""Contract tests for the two-review Review Case delta fixture.

Non-authoritative projection only. Does not accept findings, promote
requirements/ADRs/roadmap items, or claim product/legal readiness.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_HELPER_PATH = Path(__file__).with_name("test_review_case_schema.py")


def _load_review_case_schema() -> ModuleType:
    module_name = "law_nexus_test_review_case_schema"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, _SCHEMA_HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


review_case_schema = _load_review_case_schema()
SCHEMA_PATH = review_case_schema.SCHEMA_PATH
FIXTURE_PATH = ROOT / "prd/architecture/review-cases/fixtures/review-11-12-delta-v1.json"
REVIEW_11 = ROOT / "doc/review/review-11-08-2026.md"
REVIEW_12 = ROOT / "doc/review/review-12-08-2026.md"
REVIEW_11_REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
REVIEW_12_REV = "1092ef435947d74080818f69dd08dbb27bfb8f9c"

FINDING_ENDPOINT_EDGE_TYPES = frozenset(
    {
        "refines",
        "reassesses",
        "duplicates",
        "supersedes",
        "conflicts_with",
        "splits_into",
        "depends_on",
        "blocked_by",
    }
)
FORBIDDEN_EDGE_TYPES = frozenset({"promoted_to", "implemented_by", "verified_by"})
ACCEPTING_DISPOSITIONS = frozenset(
    {
        "accepted_as_gap",
        "accepted_as_requirement_candidate",
        "accepted_as_decision_candidate",
        "accepted_as_process_defect",
    }
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quote_sha256(path: Path, line_start: int, line_end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    quote = "\n".join(lines[line_start - 1 : line_end]).strip()
    return sha256_bytes(quote.encode("utf-8"))


def content_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


@pytest.fixture(scope="module")
def schema() -> Mapping[str, Any]:
    assert SCHEMA_PATH.is_file()
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def packets() -> list[dict[str, Any]]:
    assert FIXTURE_PATH.is_file(), f"missing fixture: {FIXTURE_PATH}"
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def test_fixture_has_exactly_two_packets(packets: list[dict[str, Any]]) -> None:
    assert len(packets) == 2


def test_packets_are_schema_and_invariant_valid(
    schema: Mapping[str, Any], packets: list[dict[str, Any]]
) -> None:
    for packet in packets:
        errors = review_case_schema.validate_packet(packet, schema)
        assert errors == [], errors


def test_source_hashes_and_revisions(packets: list[dict[str, Any]]) -> None:
    by_path = {packet["source"]["path"]: packet for packet in packets}
    assert set(by_path) == {
        "doc/review/review-11-08-2026.md",
        "doc/review/review-12-08-2026.md",
    }

    p11 = by_path["doc/review/review-11-08-2026.md"]
    p12 = by_path["doc/review/review-12-08-2026.md"]
    assert p11["source"]["content_sha256"] == content_sha256(REVIEW_11)
    assert p12["source"]["content_sha256"] == content_sha256(REVIEW_12)
    assert p11["normalization"]["source_hash"] == p11["source"]["content_sha256"]
    assert p12["normalization"]["source_hash"] == p12["source"]["content_sha256"]
    assert p11["source"]["reviewed_git_revision"] == REVIEW_11_REV
    assert p12["source"]["reviewed_git_revision"] == REVIEW_12_REV


def test_span_paths_and_quote_hashes(packets: list[dict[str, Any]]) -> None:
    for packet in packets:
        source_path = packet["source"]["path"]
        review_path = ROOT / source_path
        for finding in packet["findings"]:
            for span in finding["source_spans"]:
                assert span["path"] == source_path
                assert span["quote_sha256"] == quote_sha256(
                    review_path, span["line_start"], span["line_end"]
                )


def test_finding_count_and_authority_boundary(packets: list[dict[str, Any]]) -> None:
    findings = [finding for packet in packets for finding in packet["findings"]]
    assert 10 <= len(findings) <= 20
    for packet in packets:
        assert packet["authoritative"] is False
        assert packet["authority_required"] is True
        assert packet["normalization"]["status"] in {
            "draft_extracted",
            "source_verified",
        }
        assert packet["normalization"]["status"] != "human_reviewed"
        for finding in packet["findings"]:
            assert finding["disposition_status"] not in ACCEPTING_DISPOSITIONS
            assert finding["verification_status"] not in {
                "passed_bounded",
                "passed_smoke",
                "passed_validated",
            }
        for edge in packet["edges"]:
            assert edge["type"] not in FORBIDDEN_EDGE_TYPES
            assert edge["status"] == "candidate"
        for event in packet["events"]:
            assert event["event_type"] not in {
                "disposition_recorded",
                "edge_asserted",
                "verification_recorded",
                "execution_linked",
            }


def test_finding_endpoints_resolve(packets: list[dict[str, Any]]) -> None:
    finding_ids = {finding["finding_id"] for packet in packets for finding in packet["findings"]}
    for packet in packets:
        for edge in packet["edges"]:
            if edge["type"] in FINDING_ENDPOINT_EDGE_TYPES:
                assert edge["from"] in finding_ids
                assert edge["to"] in finding_ids
            if edge["type"] == "maps_to":
                assert edge["from"] in finding_ids
                assert edge["to"] not in finding_ids


def test_cross_review_delta_relations(packets: list[dict[str, Any]]) -> None:
    edges = [edge for packet in packets for edge in packet["edges"]]
    edge_types = {edge["type"] for edge in edges}
    assert "reassesses" in edge_types
    assert "refines" in edge_types or "duplicates" in edge_types
    assert "splits_into" in edge_types
    assert "maps_to" in edge_types
    assert any(
        edge["type"] == "reassesses"
        and edge["from"].startswith("RC12-")
        and edge["to"].startswith("RC11-")
        for edge in edges
    )


def test_real_fixture_has_no_pre_human_lifecycle_claims(
    packets: list[dict[str, Any]],
) -> None:
    findings = [finding for packet in packets for finding in packet["findings"]]
    kinds = {finding["kind"] for finding in findings}

    assert {"roadmap_proposal", "gap", "defect", "decision_need"} <= kinds
    for finding in findings:
        assert finding["normalization_status"] == "source_verified"
        assert finding["disposition_status"] == "open"
        assert finding["execution_status"] == "unplanned"
        assert finding["verification_status"] == "unverified"

    roadmap = [finding for finding in findings if finding["kind"] == "roadmap_proposal"]
    assert roadmap
    for finding in roadmap:
        assert "not adopted project plan" in " ".join(finding["non_claims"])


def test_no_local_or_secret_surfaces(packets: list[dict[str, Any]]) -> None:
    blob = json.dumps(packets, ensure_ascii=False)
    for needle in (
        ".gsd/",
        ".agents/",
        "Old_project/",
        "python_archive/",
        "prd/archive/",
        "/root/",
        "BEGIN PRIVATE",
        "api_key",
        "bearer ",
    ):
        assert needle not in blob
