"""Structural contract tests for capability-scoped NPA promotion gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATES_PATH = ROOT / "prd/architecture/npa-promotion-gates.json"

CAPABILITIES = {"parsing", "semantic", "identity", "temporal"}
CORPUS_SCOPES = {
    "C2-bounded",
    "C3-holdout",
    "C4-full-diagnostics",
    "C5-100",
    "C5-400",
    "C5-800",
}
BINDING_INPUTS = {
    "prd/architecture/npa-promotion-gates.json",
    "prd/architecture/npa-metric-baselines.yaml",
    "prd/migration/rust-evidence/m203-s08-quality-receipts.jsonl",
    "prd/migration/rust-evidence/m203-s08-ledger-events.jsonl",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-100.json",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-400.json",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-800.json",
}


def load_gates() -> dict[str, Any]:
    with GATES_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    assert isinstance(payload, dict)
    return payload


def test_promotion_gates_schema_lifecycle_and_authority() -> None:
    payload = load_gates()

    assert payload["schema_version"] == "law-nexus-npa-promotion-gates/v1"
    assert payload["lifecycle"] == "[proposed]"
    assert payload["authoritative"] is False
    assert payload["owner"] == "RC-2026-09-05-001"
    assert payload["raw_text"] == "forbidden"
    assert isinstance(payload["promotion_gates"], list)


def test_every_capability_covers_every_corpus_scope() -> None:
    payload = load_gates()
    gates = payload["promotion_gates"]
    pairs = {(gate["capability"], gate["corpus_scope"]) for gate in gates}

    assert len(gates) == 24
    assert {capability for capability, _ in pairs} == CAPABILITIES
    assert {scope for _, scope in pairs} == CORPUS_SCOPES
    assert pairs == {(capability, scope) for capability in CAPABILITIES for scope in CORPUS_SCOPES}


def test_each_gate_has_fail_closed_thresholds_and_human_gate() -> None:
    payload = load_gates()

    for gate in payload["promotion_gates"]:
        assert gate["ladder"] == {
            "from_state": "S4",
            "from_label": "representative_evidence",
            "to_state": "S5",
            "to_label": "human_scope_acceptance",
        }
        thresholds = gate["accepted_thresholds"]
        assert thresholds["zero_tolerance"] == {
            "critical_field_loss": 0,
            "source_span_loss": 0,
            "false_fact_mint": 0,
        }
        assert thresholds["per_layer"] == {"max_missed": 0, "max_extra": 0}
        assert thresholds["threshold_status"] == "accepted-controlled"
        assert gate["human_gate"] == {
            "required": True,
            "role": "legal-reviewer",
            "surface": "prd/architecture/capability-promotion-board.md",
            "evidence_anchor_required": True,
        }
        assert gate["rollback_ref"] == (
            "prd/architecture/npa-metric-baselines.yaml#/rollback_criteria"
        )
        assert gate["rollback_rule"] == (
            "quarantine_current_measurement_and_restore_last_comparable_revision"
        )


def test_control_level_revision_binding_and_forbidden_promotions() -> None:
    payload = load_gates()
    binding = payload["revision_binding"]

    assert binding["algorithm"] == "sha256-over-sha256-lines"
    assert set(binding["binding_inputs"]) == BINDING_INPUTS
    assert binding["binding_inputs"] == sorted(binding["binding_inputs"])
    for relative_path in binding["binding_inputs"]:
        assert (ROOT / relative_path).is_file(), relative_path

    forbidden = payload["forbidden_promotions"]
    assert any(item.get("scope") == "system" for item in forbidden)
    assert any(item.get("scope") == "all" for item in forbidden)
    assert any(item.get("without_human_gate") is True for item in forbidden)


def test_requirement_transitions_are_fail_closed_and_debt_is_explicit() -> None:
    transitions = load_gates()["requirement_transitions"]

    assert transitions["allowed"] == []
    debt = {item["requirement"]: item["remaining"] for item in transitions["debt"]}
    assert set(debt) == {"R035", "R070"}
    assert all(debt[requirement] for requirement in ("R035", "R070"))


def test_artifact_contains_only_non_claims_not_readiness_or_closure_claims() -> None:
    payload = load_gates()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    # R035/R070 are permitted only in the explicit debt/non-claim surfaces.
    assert payload["requirement_transitions"]["allowed"] == []
    assert all(
        "do not" in statement.lower() or "not" in statement.lower()
        for statement in payload["non_claims"]
    )
    assert "promoted" not in payload
    assert "readiness_claim" not in serialized
    assert "closure_claim" not in serialized
    assert "product readiness" in serialized
    assert "do not close r035 or r070" in serialized
