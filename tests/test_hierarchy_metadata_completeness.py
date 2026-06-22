from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl"
JSON_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.json"

EXPECTED_LEVELS = {
    "document",
    "chapter",
    "section",
    "article",
    "part",
    "clause",
    "subclause",
}
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _load_corpus_records() -> list[dict]:
    """Load the corpus JSONL produced by the ``--corpus`` build mode."""
    assert JSONL_PATH.exists(), f"corpus JSONL missing: {JSONL_PATH} (run --corpus)"
    return [json.loads(line) for line in JSONL_PATH.read_text(encoding="utf-8").splitlines() if line]


def _load_corpus_summary() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def test_corpus_records_count_matches_summary() -> None:
    """Record count in the JSONL must equal the summary's record count."""
    records = _load_corpus_records()
    summary = _load_corpus_summary()
    assert len(records) == summary["totals"]["record_count"]
    assert len(records) >= 7000, f"expected >=7000 records, got {len(records)}"


def test_every_record_has_required_metadata() -> None:
    """Every record must carry source_hash, excerpt_sha256, excerpt, parent_id, level, marker."""
    records = _load_corpus_records()
    assert records
    for record in records:
        assert HEX_64.match(record.get("source_sha256") or ""), (
            f"{record['id']}: source_sha256 invalid"
        )
        assert HEX_64.match(record.get("excerpt_sha256") or ""), (
            f"{record['id']}: excerpt_sha256 invalid"
        )
        assert record.get("excerpt"), f"{record['id']}: excerpt missing"
        assert len(record["excerpt"]) <= 500, (
            f"{record['id']}: excerpt length {len(record['excerpt'])} > 500"
        )
        assert "parent_id" in record, f"{record['id']}: parent_id missing"
        assert record.get("level") in EXPECTED_LEVELS, (
            f"{record['id']}: level={record.get('level')!r} not in {EXPECTED_LEVELS}"
        )
        if record["level"] != "document":
            assert record["parent_id"] is not None, (
                f"{record['id']}: non-document must have parent_id"
            )
        # marker metadata: present and well-formed for non-document levels
        if record["level"] != "document":
            assert record.get("marker") is not None, (
                f"{record['id']}: non-document must have marker"
            )
            marker = record["marker"]
            assert {"raw", "normalized", "kind"} <= set(marker.keys()), (
                f"{record['id']}: marker missing fields, got {list(marker.keys())}"
            )
        # excerpt_sha256 must match a fresh hash of the excerpt text
        assert hashlib.sha256(record["excerpt"].encode("utf-8")).hexdigest() == record["excerpt_sha256"], (
            f"{record['id']}: excerpt_sha256 does not match excerpt content"
        )


def test_per_in_scope_fixture_metadata_completeness_is_100_percent() -> None:
    """Each in-scope fixture's records must have 100% metadata completeness."""
    records = _load_corpus_records()
    summary = _load_corpus_summary()
    by_path: dict[str, list[dict]] = {}
    for record in records:
        by_path.setdefault(record["source_path"], []).append(record)
    for fixture in summary["in_scope_fixtures"]:
        path = fixture["path"]
        fixture_records = by_path.get(path, [])
        assert fixture_records, f"{path} produced 0 records"
        for record in fixture_records:
            assert HEX_64.match(record.get("source_sha256") or "")
            assert HEX_64.match(record.get("excerpt_sha256") or "")
            assert record.get("excerpt")
            assert "parent_id" in record
            assert record.get("level") in EXPECTED_LEVELS


def test_corpus_record_ids_unique_within_corpus() -> None:
    """No two records share an id (already asserted in S05; re-checked here for the S06 surface)."""
    records = _load_corpus_records()
    ids = [record["id"] for record in records]
    assert len(ids) == len(set(ids)), f"id collision: {len(ids)} records, {len(set(ids))} unique"


def test_level_distribution_matches_summary() -> None:
    """The corpus level distribution must match the per-fixture totals in the summary."""
    records = _load_corpus_records()
    by_path = {fixture["path"]: fixture for fixture in _load_corpus_summary()["in_scope_fixtures"]}
    actual_by_path: dict[str, Counter[str]] = {}
    for record in records:
        actual_by_path.setdefault(record["source_path"], Counter())[record["level"]] += 1
    for path, fixture in by_path.items():
        expected = Counter(fixture.get("emitted_counts_by_level", {}))
        assert actual_by_path[path] == expected, (
            f"{path}: actual={dict(actual_by_path[path])} expected={dict(expected)}"
        )
