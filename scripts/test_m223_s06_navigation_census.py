#!/usr/bin/env python3
"""Contracts for the M223/S06 bounded real-corpus navigation census (T04).

Hermetic suite: it checks the tracked census artifact against the design
contract, proves sample determinism as a pure property, checks the closed
navigation profile totality, and drives the fail-closed harness paths (missing
corpus, missing manifest) in a temporary sandbox.  It never runs the real
``reader-nav`` binary against the pinned corpus — the census run itself does
that once and records counts, hashes and paths only.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS_PATH = ROOT / "scripts/m223_s06_navigation_census.py"
CONTRACT_PATH = ROOT / "prd/architecture/intermediate-source-navigation-contract.md"
MANIFEST_PATH = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
S03_PATH = ROOT / "prd/migration/rust-evidence/m223-s03-baseline-run.json"
ARTIFACT_PATH = ROOT / "prd/migration/rust-evidence/m223-s06-navigation-census.json"
SCHEMA = "m223-s06-navigation-census/v1"


def load_census():
    spec = importlib.util.spec_from_file_location("m223_s06_navigation_census", CENSUS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


census = load_census()
ARTIFACT = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))

# --------------------------------------------------------- artifact schema #


def test_census_artifact_carries_schema_and_version():
    assert ARTIFACT["schema"] == SCHEMA
    assert ARTIFACT["version"] == 1
    assert ARTIFACT["counts_schema"] == census.COUNTS_SCHEMA


def test_census_artifact_declares_non_claims():
    for claim in census.NON_CLAIMS:
        assert claim in ARTIFACT["non_claims"]
    assert "not_r1000_closure" in ARTIFACT["non_claims"]
    assert "bounded_sample_not_full_corpus_s05_s07" in ARTIFACT["non_claims"]
    assert "no_physical_pagination_surface" in ARTIFACT["non_claims"]


# ------------------------------------------------------------------ profile #


def test_uncovered_is_empty():
    assert ARTIFACT["uncovered"] == []


def test_observed_tokens_are_covered_by_the_closed_profile():
    for observed_key, declared, label in (
        ("observed_node_kinds", census.NODE_KINDS, "node_kind"),
        ("observed_link_kinds", census.LINK_KINDS, "link_kind"),
        ("observed_view_kinds", census.VIEW_KINDS, "view_kind"),
        ("observed_segment_kinds", census.SEGMENT_KINDS, "segment_kind"),
        ("observed_origins", census.ORIGINS, "origin"),
        ("observed_reference_types", census.REFERENCE_TYPES, "reference_type"),
        ("observed_resolve_reasons", census.RESOLVE_REASONS, "resolve_reason"),
    ):
        observed = ARTIFACT[observed_key]
        assert observed == sorted(observed), f"{observed_key} is not sorted"
        assert set(observed) <= set(declared), f"{label} observed outside declared profile"


def test_profile_is_total_over_the_closed_vocabularies():
    assert len(census.NODE_KINDS) == 3
    assert len(census.LINK_KINDS) == 4
    assert len(census.VIEW_KINDS) == 6
    assert len(census.SEGMENT_KINDS) == 2
    assert len(census.ORIGINS) == 4
    assert len(census.REFERENCE_TYPES) == 7
    assert len(census.RESOLVE_REASONS) == 5
    assert len(set(census.RESOLVE_REASONS)) == 5


# ---------------------------------------------------------------- redaction #


def test_artifact_is_redacted_counts_hashes_paths_only():
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in census.FORBIDDEN_KEYS, f"forbidden key: {key}"
                assert key not in census.PAGINATION_KEYS, f"pagination key: {key}"
                assert census.SAFE_STRING.match(key), f"unsafe key: {key}"
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            assert census.SAFE_STRING.match(node), f"unsafe artifact string: {node[:80]}"

    walk(ARTIFACT)


def test_artifact_has_no_pagination_field():
    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in census.PAGINATION_KEYS, f"pagination key at {path}/{key}"
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(ARTIFACT)


# --------------------------------------------------------------- invariants #


def test_resolved_plus_unresolved_equals_references():
    assert ARTIFACT["resolved_total"] + ARTIFACT["unresolved_total"] == ARTIFACT["references_total"]
    assert ARTIFACT["reference_accounting_ok"] is True
    assert sum(ARTIFACT["unresolved_by_reason"].values()) == ARTIFACT["unresolved_total"]


def test_path_is_terminal_and_cycle_free():
    assert ARTIFACT["path_terminal"] is True
    assert ARTIFACT["cycles"] == 0


def test_counts_are_internally_consistent_and_documents_accepted():
    assert census.SAMPLE_MIN <= ARTIFACT["sample_size"] <= census.SAMPLE_MAX
    assert ARTIFACT["documents"] == {
        "attempted": ARTIFACT["sample_size"],
        "accepted": ARTIFACT["sample_size"],
        "failed": 0,
    }
    assert ARTIFACT["views_total"] > 0
    assert ARTIFACT["segments_total"] > 0
    assert sum(ARTIFACT["views_by_kind"].values()) == ARTIFACT["views_total"]
    assert sum(ARTIFACT["segments_by_kind"].values()) == ARTIFACT["segments_total"]
    assert sum(ARTIFACT["segments_by_origin"].values()) == ARTIFACT["segments_total"]
    assert sum(ARTIFACT["references_by_type"].values()) == ARTIFACT["references_total"]


def test_subtree_chars_are_non_negative_counts():
    subtree = ARTIFACT["subtree_chars"]
    assert set(subtree) == {"primary", "service"}
    assert subtree["primary"] >= 0
    assert subtree["service"] >= 0


# --------------------------------------------------------------- bindings #


def test_artifact_carries_expected_evidence_bindings():
    assert ARTIFACT["manifest_path"] == MANIFEST_PATH.relative_to(ROOT).as_posix()
    assert ARTIFACT["contract_path"] == CONTRACT_PATH.relative_to(ROOT).as_posix()
    assert ARTIFACT["binary_path"] == census.DEFAULT_BIN.relative_to(ROOT).as_posix()
    assert ARTIFACT["manifest_sha256"] == census.sha256_file(MANIFEST_PATH)
    assert ARTIFACT["contract_sha256"] == census.sha256_file(CONTRACT_PATH)
    assert ARTIFACT["binary_sha256"].startswith("sha256:")
    assert ARTIFACT["manifest_entries"] == 43785


def test_census_contract_hash_is_pinned_to_the_design_contract():
    # The census artifact binds the exact design-contract bytes it was produced
    # under; a drift would change the recorded hash, never silently re-pin.
    assert ARTIFACT["contract_sha256"] == census.sha256_file(CONTRACT_PATH)
    assert ARTIFACT["contract_path"] == CONTRACT_PATH.relative_to(ROOT).as_posix()


# ------------------------------------------------------------------- s03 #


def test_s03_baseline_is_reconciled():
    reconciled = ARTIFACT["s03_baseline_reconciled"]
    assert reconciled["entries"] == 43785
    assert reconciled["accepted"] == 43785
    assert reconciled["refused"] == 0
    assert reconciled["incomplete"] == 0
    assert reconciled["r1000_status"] == "active/unclosed"
    baseline = json.loads(S03_PATH.read_text(encoding="utf-8"))
    assert baseline["counts"]["entries"] == reconciled["entries"]
    assert baseline["counts"]["accepted"] == reconciled["accepted"]
    assert baseline["counts"]["refused"] == reconciled["refused"]
    assert baseline["counts"]["incomplete"] == reconciled["incomplete"]
    assert baseline["r1000_status"] == reconciled["r1000_status"]


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
    bounded = census.filter_entries(entries, ARTIFACT["sample_max_bytes"])
    assert len(entries) - len(bounded) == ARTIFACT["manifest_entries_over_cap"]
    kwargs = {
        "seed": ARTIFACT["sample_seed"],
        "per_decile": ARTIFACT["sample_per_decile"],
        "tail_n": ARTIFACT["sample_tail_n"],
    }
    first, strata = census.build_sample(bounded, **kwargs)
    second, _ = census.build_sample(bounded, **kwargs)
    assert [item.relative_path for item in first] == [item.relative_path for item in second]
    assert len(first) == ARTIFACT["sample_size"]
    assert census.SAMPLE_MIN <= len(first) <= census.SAMPLE_MAX
    assert strata == ARTIFACT["sample_strata"]


def test_bounded_input_guard_is_recorded_and_never_silent():
    assert ARTIFACT["sample_max_bytes"] == census.DEFAULT_MAX_BYTES
    assert ARTIFACT["manifest_entries"] == 43785
    assert ARTIFACT["manifest_entries_over_cap"] > 0
    assert ARTIFACT["manifest_entries_over_cap"] < ARTIFACT["manifest_entries"]
    assert "bounded_by_input_size_guard" in ARTIFACT["non_claims"]


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


def test_missing_s03_baseline_fails_closed_with_harness_error(tmp_path):
    out = tmp_path / "census.json"
    result = _run_census("--s03", str(tmp_path / "absent-s03.json"), "--out", str(out))
    assert result.returncode != 0
    assert "census harness error" in result.stderr
    assert "S03 baseline not found" in result.stderr
    assert not out.exists()


def test_impossible_input_guard_fails_closed_with_harness_error(tmp_path):
    out = tmp_path / "census.json"
    result = _run_census("--max-bytes", "1", "--out", str(out))
    assert result.returncode != 0
    assert "census harness error" in result.stderr
    assert "input guard" in result.stderr
    assert not out.exists()


# ------------------------------------------------------ counts doc contract #


def test_counts_document_validator_accepts_a_well_formed_document():
    document = {
        "schema": census.COUNTS_SCHEMA,
        "views": 1,
        "segments": 1,
        "references": 1,
        "views_by_kind": {"paragraph": 1},
        "segments_by_kind": {"text": 1},
        "segments_by_origin": {"source_fragment": 1},
        "references_by_type": {"note_reference": 1},
        "links_by_kind": {"resolves_to": 1},
        "resolved": 1,
        "unresolved": 0,
        "unresolved_by_reason": {},
        "max_depth": 0,
        "max_path_len": 1,
        "subtree_chars_primary": 3,
        "subtree_chars_service": 0,
        "docs": 1,
        "path_terminal": True,
        "cycles": 0,
    }
    census.validate_counts_document(document)


def test_counts_document_validator_rejects_accounting_drift():
    document = {
        "schema": census.COUNTS_SCHEMA,
        "views": 0,
        "segments": 0,
        "references": 2,
        "views_by_kind": {},
        "segments_by_kind": {},
        "segments_by_origin": {},
        "references_by_type": {"note_reference": 2},
        "links_by_kind": {},
        "resolved": 0,
        "unresolved": 0,
        "unresolved_by_reason": {},
        "max_depth": 0,
        "max_path_len": 0,
        "subtree_chars_primary": 0,
        "subtree_chars_service": 0,
        "docs": 1,
        "path_terminal": True,
        "cycles": 0,
    }
    try:
        census.validate_counts_document(document)
    except census.CensusHarnessError as error:
        assert "resolved + unresolved != references" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("accounting drift was not refused")


def test_counts_document_validator_rejects_unknown_token():
    document = {
        "schema": census.COUNTS_SCHEMA,
        "views": 1,
        "segments": 0,
        "references": 0,
        "views_by_kind": {"sidebar": 1},
        "segments_by_kind": {},
        "segments_by_origin": {},
        "references_by_type": {},
        "links_by_kind": {},
        "resolved": 0,
        "unresolved": 0,
        "unresolved_by_reason": {},
        "max_depth": 0,
        "max_path_len": 1,
        "subtree_chars_primary": 0,
        "subtree_chars_service": 0,
        "docs": 1,
        "path_terminal": True,
        "cycles": 0,
    }
    try:
        census.validate_counts_document(document)
    except census.CensusHarnessError as error:
        assert "unknown" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown token was not refused")


def test_counts_document_validator_rejects_pagination_field():
    document = {
        "schema": census.COUNTS_SCHEMA,
        "views": 0,
        "segments": 0,
        "references": 0,
        "views_by_kind": {},
        "segments_by_kind": {},
        "segments_by_origin": {},
        "references_by_type": {},
        "links_by_kind": {},
        "resolved": 0,
        "unresolved": 0,
        "unresolved_by_reason": {},
        "max_depth": 0,
        "max_path_len": 0,
        "subtree_chars_primary": 0,
        "subtree_chars_service": 0,
        "docs": 1,
        "path_terminal": True,
        "cycles": 0,
        "page": 1,
    }
    try:
        census.validate_counts_document(document)
    except census.CensusHarnessError as error:
        assert "keys drift" in str(error) or "pagination" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("pagination field was not refused")


def test_redaction_guard_refuses_a_pagination_field():
    try:
        census.redaction_check({"page": 1})
    except census.CensusHarnessError as error:
        assert "pagination" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("redaction guard accepted a pagination field")


def test_redaction_guard_refuses_raw_text():
    try:
        census.redaction_check({"note": "сырой декодированный текст"})
    except census.CensusHarnessError as error:
        assert "unsafe artifact string" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("redaction guard accepted raw text")


def test_redaction_guard_refuses_a_string_under_a_text_key():
    # ``text`` is a legitimate ReaderSegmentKind tally key when its value is a
    # count, but a string payload under it is raw text and is refused.
    try:
        census.redaction_check({"text": "abc"})
    except census.CensusHarnessError as error:
        assert "raw-text artifact key" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("redaction guard accepted a string under a text key")
    # The integer tally form is accepted.
    census.redaction_check({"text": 3})
