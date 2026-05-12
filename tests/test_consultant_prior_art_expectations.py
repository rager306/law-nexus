from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build-consultant-prior-art-expectations.py"
JSON_PATH = ROOT / "prd" / "parser" / "consultant_prior_art_expectations.json"
REPORT_PATH = ROOT / "prd" / "parser" / "consultant_prior_art_expectations.md"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_consultant_prior_art_expectations", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generated_expectation_artifact_contains_comparable_counts_and_advisory_rules():
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    assert payload["phase"] == "consultant_prior_art_expectations_build"
    assert payload["non_authoritative"] is True
    assert payload["fatal_error_count"] == 0
    assert payload["hash_drift_count"] == 0
    assert all(source["hash_matches_expected"] is True for source in payload["sources"])

    structure_counts = payload["expectations"]["comparable_counts"]["structure"]["counts"]
    assert structure_counts == {
        "all_references_count": 0,
        "chapter_article_refs_total": 47,
        "chapter_count": 8,
        "chapter_paragraphs_total": 9,
        "chapters_with_article_refs": 7,
        "chapters_with_paragraphs": 1,
        "definitions_count": 0,
        "external_laws_count": 0,
        "key_dates_count": 0,
        "metadata_field_count": 7,
    }

    article_counts = payload["expectations"]["comparable_counts"]["articles"]["counts"]
    assert article_counts["article_record_count"] == 94
    assert article_counts["article_invalid_true_count"] == 11
    assert article_counts["part_count"] == 668
    assert article_counts["clause_count"] == 912
    assert article_counts["subclause_count"] == 272

    validation_counts = payload["expectations"]["validation_rules"]["counts"]
    assert validation_counts == {
        "advisory_rule_count": 9,
        "comparable_rule_count": 6,
        "validation_file_count": 2,
        "validation_rule_count": 15,
    }
    rules = payload["expectations"]["validation_rules"]["rules"]
    assert {rule["rule_id"] for rule in rules if rule["classification"] == "comparable"} == {
        "STRUCT-001",
        "STRUCT-002",
        "STRUCT-003",
        "STRUCT-004",
        "STRUCT-005",
        "STRUCT-006",
    }
    assert {rule["rule_id"] for rule in rules if rule["classification"] == "advisory"} == {
        "SEM-001",
        "SEM-002",
        "SEM-003",
        "SEM-004",
        "SEM-005",
        "SEM-006",
        "SEM-007",
        "SEM-008",
        "SEM-009",
    }


def test_cli_check_reports_fresh_expectation_artifacts_and_hash_diagnostics():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "pass"
    assert payload["artifact_freshness"] == {
        "prd/parser/consultant_prior_art_expectations.json": True,
        "prd/parser/consultant_prior_art_expectations.md": True,
    }
    assert payload["fatal_error_count"] == 0
    assert payload["hash_drift_count"] == 0
    assert payload["diagnostics_bounded"] is True


def test_generator_build_is_deterministic_against_artifacts():
    module = load_builder_module()
    result = module.build()

    assert result.summary_json == JSON_PATH.read_text(encoding="utf-8")
    assert result.report_md == REPORT_PATH.read_text(encoding="utf-8")
    assert result.diagnostics["expectations"]["validation_rules"]["counts"]["comparable_rule_count"] == 6
    assert "STRUCT-001" in result.report_md
    assert "semantic legal meaning" in result.report_md


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def configure_temp_builder(module, monkeypatch, tmp_path: Path, inventory_hash_override: str | None = None):
    structure_path = tmp_path / "structure.json"
    articles_path = tmp_path / "articles.jsonl"
    validation_dir = tmp_path / "validation"
    structural_path = validation_dir / "structural_rules.yaml"
    semantic_path = validation_dir / "semantic_rules.yaml"
    inventory_path = Path("inventory.json")

    write_json(
        structure_path,
        {
            "metadata": {"law_id": "44-FZ", "number": "44-ФЗ"},
            "chapters": [
                {"number": 1, "title": "One", "articles": [{"article": "1"}], "paragraphs": []},
                {"number": 2, "title": "Two", "articles": [], "paragraphs": [{"number": "1"}]},
            ],
            "all_references": [],
            "external_laws": [],
            "key_dates": {},
            "definitions": {},
        },
    )
    write_text(
        articles_path,
        "\n".join(
            [
                json.dumps(
                    {
                        "doc_id": "DOC",
                        "chapter": 1,
                        "article": "1",
                        "title": "Article 1",
                        "invalid": False,
                        "parts": [
                            {
                                "number": 1,
                                "text": "part",
                                "invalid": False,
                                "references": [],
                                "amendments": [],
                                "clauses": [
                                    {
                                        "number": 1,
                                        "text": "clause",
                                        "invalid": True,
                                        "references": [],
                                        "amendments": [],
                                        "subclauses": [{"number": "а", "text": "sub", "invalid": False}],
                                    }
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                json.dumps({"doc_id": "DOC", "chapter": 2, "article": "2", "title": "Article 2", "invalid": True, "parts": []}, ensure_ascii=False),
            ]
        )
        + "\n",
    )
    write_text(
        structural_path,
        "version: 1.0.0\nrules:\n  - id: STRUCT-001\n    name: article_has_number\n    severity: error\n    target: article\n    check: has_field\n    description: Every article must have a number\n",
    )
    write_text(
        semantic_path,
        "version: 1.0.0\nrules:\n  - id: SEM-001\n    name: article_numbers_sequential\n    severity: error\n    target: article\n    check: sequential_within\n    description: Article numbers should be sequential\n",
    )

    def asset(path: Path, asset_id: str, expected_sha: str | None = None):
        return {
            "asset_id": asset_id,
            "source_path": str(path),
            "classification": "adapt",
            "expected_sha256": expected_sha or hashlib.sha256(path.read_bytes()).hexdigest(),
            "reuse_boundary": "fixture boundary",
        }

    structure_sha = inventory_hash_override or hashlib.sha256(structure_path.read_bytes()).hexdigest()
    inventory = {
        "assets": [
            asset(structure_path, "TMP-STRUCT", structure_sha),
            asset(articles_path, "TMP-ARTICLES"),
            asset(structural_path, "TMP-STRUCT-RULES"),
            asset(semantic_path, "TMP-SEM-RULES"),
        ]
    }
    write_json(tmp_path / inventory_path, inventory)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(module, "JSON_PATH", Path("expectations.json"))
    monkeypatch.setattr(module, "REPORT_PATH", Path("expectations.md"))
    monkeypatch.setattr(module, "STRUCTURE_PATH", structure_path)
    monkeypatch.setattr(module, "ARTICLES_PATH", articles_path)
    monkeypatch.setattr(module, "VALIDATION_DIR", validation_dir)
    return structure_path


def test_inline_fixture_classifies_counts_rules_and_skipped_fields(monkeypatch, tmp_path):
    module = load_builder_module()
    configure_temp_builder(module, monkeypatch, tmp_path)

    result = module.build()
    payload = json.loads(result.summary_json)

    assert payload["fatal_error_count"] == 0
    assert payload["hash_drift_count"] == 0
    assert payload["expectations"]["comparable_counts"]["structure"]["counts"] == {
        "all_references_count": 0,
        "chapter_article_refs_total": 1,
        "chapter_count": 2,
        "chapter_paragraphs_total": 1,
        "chapters_with_article_refs": 1,
        "chapters_with_paragraphs": 1,
        "definitions_count": 0,
        "external_laws_count": 0,
        "key_dates_count": 0,
        "metadata_field_count": 2,
    }
    assert payload["expectations"]["comparable_counts"]["articles"]["counts"]["article_record_count"] == 2
    assert payload["expectations"]["comparable_counts"]["articles"]["counts"]["articles_without_parts"] == 1
    assert payload["expectations"]["comparable_counts"]["articles"]["counts"]["clause_invalid_true_count"] == 1
    assert payload["expectations"]["validation_rules"]["counts"] == {
        "advisory_rule_count": 1,
        "comparable_rule_count": 1,
        "validation_file_count": 2,
        "validation_rule_count": 2,
    }
    assert "text copied from prior-art output" in result.report_md


def test_cli_fail_closed_for_inventory_hash_drift(monkeypatch, tmp_path, capsys):
    module = load_builder_module()
    configure_temp_builder(module, monkeypatch, tmp_path, inventory_hash_override="b" * 64)

    assert module.main(["--check"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "fail"
    assert payload["hash_drift_count"] == 1
    assert payload["hash_drifts"][0]["kind"] == "hash_drift"
    assert payload["diagnostics_bounded"] is True
