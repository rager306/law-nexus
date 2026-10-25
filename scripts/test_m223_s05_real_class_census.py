#!/usr/bin/env python3
"""Contracts for the M223/S05 bounded real-class census (T03).

Hermetic suite: it checks the tracked census artifact against the design
contract profile block, proves sample determinism as a pure property, and
drives the fail-closed harness paths (missing corpus, missing manifest) in a
temporary sandbox.  It never runs the real export binary against the pinned
corpus — the census run itself does that once and records counts, hashes and
paths only.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS_PATH = ROOT / "scripts/m223_s05_real_class_census.py"
CONTRACT_PATH = ROOT / "prd/architecture/intermediate-source-clean-view-contract.md"
MANIFEST_PATH = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
ARTIFACT_PATH = ROOT / "prd/migration/rust-evidence/m223-s05-real-class-census.json"
SCHEMA = "m223-s05-real-class-census/v1"


def load_census():
    spec = importlib.util.spec_from_file_location("m223_s05_real_class_census", CENSUS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


census = load_census()
ARTIFACT = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
PROFILE_ID, RULES = census.parse_clean_profile(CONTRACT_PATH)


# --------------------------------------------------------- artifact schema #


def test_census_artifact_carries_schema_and_version():
    assert ARTIFACT["schema"] == SCHEMA
    assert ARTIFACT["version"] == 1


def test_profile_id_is_reader_clean_profile_v1():
    assert ARTIFACT["profile_id"] == PROFILE_ID == "reader_clean_profile/v1"


def test_uncovered_classes_empty():
    assert ARTIFACT["uncovered_classes"] == []


def test_observed_classes_are_covered_by_the_profile():
    observed = set(ARTIFACT["observed_classes"])
    assert observed
    assert observed <= set(RULES)
    for cls in observed:
        assert RULES[cls][1] in census.DISPOSITIONS


# ------------------------------------------------------------------ profile #


def test_profile_block_is_total_over_seven_reader_semantic_classes():
    assert len(RULES) == len(census.READER_SEMANTIC_CLASSES) == 7
    assert set(RULES) == set(census.READER_SEMANTIC_CLASSES)
    rule_ids = [rule_id for rule_id, _ in RULES.values()]
    assert len(set(rule_ids)) == 7


def test_observed_revision_classes_are_never_dropped():
    per_class = ARTIFACT["per_class"]
    insertions = per_class.get("revision_insertion", 0)
    deletions = per_class.get("revision_deletion", 0)
    assert ARTIFACT["revision_insertion_observed"] is (insertions > 0)
    assert ARTIFACT["revision_deletion_observed"] is (deletions > 0)
    if insertions > 0:
        assert RULES["revision_insertion"][1] == "primary"
    if deletions > 0:
        assert RULES["revision_deletion"][1] == "service"


# ---------------------------------------------------------------- redaction #


def test_artifact_is_redacted_counts_hashes_paths_only():
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in census.FORBIDDEN_KEYS, f"forbidden key: {key}"
                assert census.SAFE_STRING.match(key), f"unsafe key: {key}"
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            assert census.SAFE_STRING.match(node), f"unsafe artifact string: {node[:80]}"

    walk(ARTIFACT)


def test_artifact_carries_expected_evidence_fields():
    assert ARTIFACT["manifest_path"] == MANIFEST_PATH.relative_to(ROOT).as_posix()
    assert ARTIFACT["contract_path"] == CONTRACT_PATH.relative_to(ROOT).as_posix()
    assert ARTIFACT["manifest_sha256"].startswith("sha256:")
    assert ARTIFACT["binary_sha256"].startswith("sha256:")
    assert ARTIFACT["contract_sha256"].startswith("sha256:")
    assert "not_r1000_closure" in ARTIFACT["non_claims"]
    assert "bounded_sample_not_full_corpus_s07" in ARTIFACT["non_claims"]


# --------------------------------------------------- counts internal honesty #


def test_counts_are_internally_consistent_and_exports_accepted():
    assert census.SAMPLE_MIN <= ARTIFACT["sample_size"] <= census.SAMPLE_MAX
    assert ARTIFACT["exports"] == {
        "attempted": ARTIFACT["sample_size"],
        "accepted": ARTIFACT["sample_size"],
        "failed": 0,
    }
    assert ARTIFACT["segments_total"] > 0  # an empty tally is not census evidence
    assert ARTIFACT["segments_total"] == sum(ARTIFACT["per_class"].values())
    assert sum(ARTIFACT["per_origin"].values()) == ARTIFACT["segments_total"]
    assert sorted(ARTIFACT["observed_classes"]) == ARTIFACT["observed_classes"]


# --------------------------------------------------------------- determinism #


def test_sample_selection_is_deterministic_on_reselection_inline():
    entries = [
        census.Entry("e.xml", "sha256:5", 150),
        census.Entry("b.xml", "sha256:2", 200),
        census.Entry("d.xml", "sha256:4", 250),
        census.Entry("a.xml", "sha256:1", 100),
        census.Entry("c.xml", "sha256:3", 300),
        census.Entry("f.xml", "sha256:6", 260),
    ]
    kwargs = {"seed": 7, "per_decile": 1, "tail_n": 1}
    first, first_strata = census.build_sample(entries, **kwargs)
    second, second_strata = census.build_sample(entries, **kwargs)
    assert [item.relative_path for item in first] == [item.relative_path for item in second]
    assert first_strata == second_strata
    assert [item.relative_path for item in first] == sorted(item.relative_path for item in first)


def test_recorded_census_sample_is_reproducible_from_the_pinned_manifest():
    _, entries = census.parse_manifest(MANIFEST_PATH)
    kwargs = {
        "seed": ARTIFACT["sample_seed"],
        "per_decile": ARTIFACT["sample_per_decile"],
        "tail_n": ARTIFACT["sample_tail_n"],
    }
    first, _ = census.build_sample(entries, **kwargs)
    second, _ = census.build_sample(entries, **kwargs)
    assert [item.relative_path for item in first] == [item.relative_path for item in second]
    assert len(first) == ARTIFACT["sample_size"]
    assert census.SAMPLE_MIN <= len(first) <= census.SAMPLE_MAX


# ---------------------------------------------------------------- fail-closed #


def _run_census(*extra_args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(CENSUS_PATH), *extra_args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_missing_corpus_fails_closed_with_harness_error(tmp_path):
    out = tmp_path / "census.json"
    result = _run_census("--corpus-root", str(tmp_path / "missing-corpus"), "--out", str(out))
    assert result.returncode != 0
    assert "census harness error" in result.stderr
    assert "corpus root not found" in result.stderr
    assert not out.exists()


def test_missing_manifest_fails_closed_with_harness_error(tmp_path):
    out = tmp_path / "census.json"
    result = _run_census("--manifest", str(tmp_path / "absent-manifest.jsonl"), "--out", str(out))
    assert result.returncode != 0
    assert "census harness error" in result.stderr
    assert not out.exists()
