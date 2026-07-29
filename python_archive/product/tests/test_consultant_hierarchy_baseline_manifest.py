"""Read-only contract checks for the Consultant hierarchy baseline manifest.

The tests intentionally do not rebuild parser artifacts. Generation is an
explicit repository operation; the normal test suite validates the tracked
manifest against tracked files without mutating either.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_baseline_manifest.json"
SCHEMA_VERSION = "consultant-hierarchy-baseline-manifest/v1"
EXPECTED_COUNTS = {"single": 2185, "corpus": 15249}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sections_by_mode(manifest: dict) -> dict[str, dict]:
    return {section["mode"]: section for section in manifest["modes"]}


def test_manifest_is_canonical_deterministic_json() -> None:
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    payload = json.loads(raw)
    expected = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert raw == expected


def test_manifest_exposes_bounded_mode_separated_contract() -> None:
    manifest = _load_manifest()
    sections = _sections_by_mode(manifest)

    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["non_authoritative"] is True
    assert set(sections) == {"single", "corpus"}
    assert sections["single"]["semantic_counts"]["record_count"] == EXPECTED_COUNTS["single"]
    assert sections["corpus"]["semantic_counts"]["record_count"] == EXPECTED_COUNTS["corpus"]

    single_paths = {entry["path"] for entry in sections["single"]["outputs"]}
    corpus_paths = {entry["path"] for entry in sections["corpus"]["outputs"]}
    assert single_paths.isdisjoint(corpus_paths)
    assert "prd/parser/consultant_hierarchy_records.jsonl" in single_paths
    assert "prd/parser/consultant_hierarchy_corpus_records.jsonl" in corpus_paths


@pytest.mark.slow
def test_manifest_source_output_and_generator_hashes_match_tracked_files() -> None:
    manifest = _load_manifest()

    for section in manifest["modes"]:
        assert section["cli_invocation"][0:2] == [
            "uv",
            "run",
        ], "durable invocation must use the repository uv environment"
        for entry in section["sources"] + section["outputs"]:
            path = ROOT / entry["path"]
            assert path.is_file(), f"manifest path missing: {entry['path']}"
            assert entry["sha256"] == _sha256(path), f"hash drift: {entry['path']}"

        generator = section["generator"]
        generator_path = ROOT / generator["path"]
        assert generator_path.is_file()
        assert generator["sha256"] == _sha256(generator_path)
