"""Contracts for the proposed NPA corpus, metric, and ledger controls."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "prd/architecture/npa-corpus-control.yaml"
METRICS = ROOT / "prd/architecture/npa-metric-baselines.yaml"
LEDGERS = ROOT / "prd/architecture/npa-control-ledgers.yaml"
ASSESSMENT = ROOT / "assessment/31-npa-control-artifact-verification.md"


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    assert isinstance(value, dict)
    return value


def test_corpus_contract_has_closed_strata_and_authority_boundary() -> None:
    data = load(CORPUS)
    assert data["schema_version"] == "law-nexus-npa-corpus-control/v1"
    assert data["lifecycle"] == "[proposed]"
    assert data["authoritative"] is False
    assert data["source_authority"] == {
        "full_corpus_root": "consru_export/consru_export/exports",
        "allowed_file_glob": "**/*.xml",
        "forbidden_corpus_roots": ["law-source/consultant", "law-source/garant"],
        "raw_text_persistence": "forbidden",
        "source_anchor_fields": ["document_relative_path", "document_content_hash", "source_span"],
    }
    strata = {item["id"]: item for item in data["strata"]}
    assert set(strata) == {"C0", "C1", "C2", "C3", "C4", "C5"}
    assert strata["C4"]["lifecycle"] == "[diagnostic]"
    assert strata["C5"]["gold"] is True
    assert strata["C5"]["admission"] == "two_coder_agreement_and_human_acceptance"


def test_manifest_binds_revision_snapshot_environment_and_safe_anchors() -> None:
    data = load(CORPUS)["manifest_schema"]
    assert {
        "schema_version",
        "manifest_id",
        "stratum",
        "parser_revision",
        "corpus_snapshot_hash",
        "provider_strata",
        "environment",
        "entries",
        "lifecycle",
    } <= set(data["required"])
    assert data["properties"]["stratum"]["enum"] == ["C0", "C1", "C2", "C3", "C4", "C5"]
    assert load(CORPUS)["manifest_entry"]["evidence_anchor_required"] == [
        "document_relative_path",
        "source_span",
    ]


def test_metric_contract_separates_classification_and_fail_closed_rules() -> None:
    data = load(METRICS)
    binding = data["measurement_binding"]
    assert binding["classification"] == ["exact", "estimate", "proxy"]
    assert set(binding["required"]) >= {
        "parser_revision",
        "corpus_snapshot_hash",
        "manifest_id",
        "provider_strata",
        "environment",
        "classification",
        "evidence_anchors",
    }
    proxy = next(item for item in data["metric_families"] if item["id"] == "lexical_proxy")
    assert proxy["classification"] == "proxy"
    assert "never count as semantic frames" in proxy["semantic_non_claim"]
    thresholds = data["provisional_thresholds"]
    assert thresholds["status"] == "provisional_non_authoritative"
    assert thresholds["semantic_loss"] == {
        "critical_field_loss": 0,
        "source_span_loss": 0,
        "false_fact_mint": 0,
    }
    assert thresholds["resource"]["top_k"] == "deferred-undefined"
    assert "measurement_binding_mismatch" in data["rollback_criteria"]["conditions"]


def test_ledgers_are_append_only_and_corrections_are_superseding() -> None:
    data = load(LEDGERS)
    envelope = data["common_envelope"]
    assert envelope["append_only"] is True
    assert envelope["update_rule"] == "append_superseding_event_only"
    assert "parser_revision" in envelope["required"]
    assert "corpus_snapshot_hash" in envelope["required"]
    assert "manifest_id" in envelope["required"]
    ledgers = data["ledgers"]
    assert set(ledgers) == {"metrics_history", "regression", "gaps", "semantic_corrections"}
    assert ledgers["regression"]["comparability"] == [
        "comparable",
        "incomparable",
        "not_assessable",
    ]
    assert ledgers["regression"]["disposition"] == ["pass", "fail", "quarantine", "deferred"]
    correction = ledgers["semantic_corrections"]
    assert correction["correction_code"]["stable"] is True
    assert "accepted_requires_human_disposition_and_supersedes_target" in correction["rule"]
    assert "no_delete_or_in_place_update" in data["integrity"]


def test_control_artifacts_and_assessment_do_not_persist_raw_corpus_text() -> None:
    for path in (CORPUS, METRICS, LEDGERS, ASSESSMENT):
        text = path.read_text(encoding="utf-8")
        assert "raw_text: forbidden" in text or "raw corpus text" in text
        assert "source_span" in text
    assert "law-source/consultant/" in ASSESSMENT.read_text(encoding="utf-8")
    assert "not legal gold" in ASSESSMENT.read_text(encoding="utf-8")
