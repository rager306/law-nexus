from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "prd/parser/consultant_prior_art_inventory.json"
REPORT_PATH = ROOT / "prd/parser/consultant_prior_art_inventory.md"
SOURCE_FIXTURE_INVENTORY_PATH = ROOT / "prd/parser/source_fixture_inventory.json"


def load_inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_prior_art_inventory_records_required_assets_and_boundaries() -> None:
    inventory = load_inventory()

    assert inventory["schema_version"] == "consultant-prior-art-inventory/v1"
    assert inventory["status"] == "pass"
    assert inventory["non_authoritative"] is True
    assert inventory["asset_count"] == len(inventory["assets"])
    assert inventory["asset_count"] >= 8

    assets_by_type = {asset["asset_type"]: asset for asset in inventory["assets"]}
    for required_type in {
        "full-fixture",
        "structure-json",
        "articles-jsonl",
        "source-format-yaml",
        "structure-yaml",
        "parsing-prompt-yaml",
        "structural-rules-yaml",
        "semantic-rules-yaml",
    }:
        assert required_type in assets_by_type

    assert assets_by_type["full-fixture"]["classification"] == "keep"
    assert assets_by_type["structure-json"]["classification"] == "adapt"
    assert assets_by_type["articles-jsonl"]["classification"] == "adapt"
    assert assets_by_type["semantic-rules-yaml"]["classification"] == "defer"
    assert "parsed legal semantics" in assets_by_type["full-fixture"]["reuse_boundary"]
    assert "authoritative parsed output" in assets_by_type["structure-json"]["reuse_boundary"]

    for asset in inventory["assets"]:
        assert asset["exists"] is True
        assert len(asset["sha256"]) == 64
        assert asset["hash_matches_expected"] is True
        assert asset["expected_sha256"] == asset["sha256"]
        assert "Does not claim parser completeness." in asset["non_claims"]
        assert "Does not claim legal correctness or authoritative legal interpretation." in asset["non_claims"]


def test_prior_art_inventory_diagnostics_and_classification_counts_are_consistent() -> None:
    inventory = load_inventory()

    counts = Counter(asset["classification"] for asset in inventory["assets"])
    assert inventory["classification_counts"] == dict(counts)
    assert set(counts) >= {"keep", "adapt", "defer", "reject"}
    assert inventory["diagnostics"]["classification_count_total"] == inventory["asset_count"]
    assert inventory["diagnostics"]["missing_prior_art_files"] == []
    assert inventory["diagnostics"]["hash_drift_paths"] == []
    assert "law-parser derived JSON/JSONL outputs are not imported as authoritative parsed legal data." in inventory["diagnostics"]["source_priority_notes"]

    blocked_claims = set(inventory["blocked_claims"])
    assert "parser completeness" in blocked_claims
    assert "legal correctness" in blocked_claims
    assert "Consultant WordML legal authority" in blocked_claims
    assert "FalkorDB loading/runtime readiness" in blocked_claims


def test_full_fixture_hash_matches_canonical_source_fixture_inventory() -> None:
    prior_art = load_inventory()
    source_inventory = json.loads(SOURCE_FIXTURE_INVENTORY_PATH.read_text(encoding="utf-8"))

    source_fixture = next(
        fixture
        for fixture in source_inventory["fixtures"]
        if fixture["path"] == "law-source/consultant/44-FZ-2026.xml"
    )
    prior_art_fixture = next(
        asset
        for asset in prior_art["assets"]
        if asset["source_path"] == "law-source/consultant/44-FZ-2026.xml"
    )

    assert source_fixture["source_role"] == "full-normative-act"
    assert prior_art_fixture["sha256"] == source_fixture["sha256"]
    assert prior_art_fixture["size_bytes"] == source_fixture["size_bytes"]
    assert prior_art_fixture["classification"] == "keep"


def test_prior_art_markdown_is_non_empty_and_cold_reader_visible() -> None:
    markdown = REPORT_PATH.read_text(encoding="utf-8")

    assert REPORT_PATH.stat().st_size > 0
    assert "# Consultant prior-art inventory" in markdown
    assert "## Reuse boundaries" in markdown
    assert "## Blocked claims" in markdown
    assert "## Diagnostics" in markdown
    assert "law-source/consultant/44-FZ-2026.xml" in markdown
    assert "/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json" in markdown
    assert "/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl" in markdown
    assert "/root/law-parser/prompt_domain_44fz/sources/consultant_word2003xml.yaml" in markdown
    assert "/root/law-parser/prompt_domain_44fz/validation/structural_rules.yaml" in markdown
    assert "This inventory does not claim parser completeness." in markdown
    assert "This inventory does not claim legal correctness." in markdown
    assert "No raw full legal text is embedded" in markdown
