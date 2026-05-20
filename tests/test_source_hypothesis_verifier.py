# pyright: reportMissingImports=false
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from source_hypothesis_verifier import review_queue_item, verify_proposal  # noqa: E402

SCRIPT = ROOT / "scripts" / "source_hypothesis_verifier.py"


def accepted_proposal() -> dict:
    return {
        "schema_version": "legalgraph-structural-hypothesis-proposal/v1",
        "proposal_id": "SHP-abc123def456",
        "worker_attempt_id": "WA-abc123def456",
        "source_artifact_id": "SA-CONSULTANT-abc123def456",
        "source_revision_id": "SR-CONSULTANT-doc-abc123def456",
        "run_id": "RUN-abc123def456",
        "output_refs": ["processed/consultant-wordml-v1/CORPUS-abc123def456/source_inventory.safe.jsonl"],
        "source_family": "consultant_wordml",
        "document_role": "full_normative_act",
        "parser_route": "full_act",
        "hypothesis_kind": "structural_marker_rule",
        "hypothesis_payload": {
            "selector": "root:wordDocument:namespace_sha256:abc123def456",
            "safe_rule_id": "RULE-abc123def456",
            "confidence_bucket": "medium",
            "evidence_refs": ["metrics.safe.json", "diagnostics.safe.jsonl", "review_pack.json"],
        },
        "verifier_status": "pending",
        "non_authoritative": True,
        "non_claims": [
            "proposal is a structural hypothesis only",
            "proposal does not claim legal correctness",
            "proposal does not claim parser completeness",
            "proposal does not validate R035",
        ],
    }


def test_accepts_closed_safe_proposal() -> None:
    decision = verify_proposal(accepted_proposal())

    assert decision["schema_version"] == "legalgraph-verifier-decision/v1"
    assert decision["verifier_status"] == "accepted"
    assert decision["rejection_reasons"] == []
    assert decision["acceptance_evidence_refs"] == [
        "metrics.safe.json",
        "diagnostics.safe.jsonl",
        "review_pack.json",
    ]
    assert decision["non_authoritative"] is True
    assert "does not validate R035" in " ".join(decision["non_claims"])


def test_rejects_extra_fields_and_invalid_enums() -> None:
    proposal = accepted_proposal()
    proposal["extra_freeform"] = "not allowed"
    proposal["hypothesis_payload"]["extra_nested"] = "not allowed"
    proposal["hypothesis_payload"]["confidence_bucket"] = "certain"
    proposal["verifier_status"] = "accepted"

    decision = verify_proposal(proposal)

    assert decision["verifier_status"] == "rejected"
    assert decision["rejection_reasons"] == ["schema_violation"]


def test_rejects_missing_non_claims_and_unsafe_refs() -> None:
    proposal = accepted_proposal()
    proposal["non_claims"] = []
    proposal["output_refs"] = ["../raw.xml"]
    proposal["hypothesis_payload"]["evidence_refs"] = []

    decision = verify_proposal(proposal)

    assert decision["verifier_status"] == "rejected"
    assert set(decision["rejection_reasons"]) == {
        "insufficient_deterministic_evidence",
        "missing_safe_ref",
        "schema_violation",
    }


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda p: p["hypothesis_payload"].__setitem__("nested_note", "Федеральный закон"), "raw_text_detected"),
        (lambda p: p.__setitem__("output_refs", ["/tmp/source_inventory.safe.jsonl"]), "absolute_path_detected"),
        (lambda p: p["hypothesis_payload"].__setitem__("provider_debug", "BEGIN PROVIDER PAYLOAD"), "provider_payload_detected"),
        (lambda p: p["hypothesis_payload"].__setitem__("answer", "legal answer: use this interpretation"), "legal_answer_prose_detected"),
        (lambda p: p["hypothesis_payload"].__setitem__("claim", "parser completeness validated"), "parser_completeness_overclaim"),
        (lambda p: p["hypothesis_payload"].__setitem__("claim", "validates R035"), "r035_validation_overclaim"),
        (lambda p: p["hypothesis_payload"].__setitem__("raw_vectors", [0.1, 0.2]), "forbidden_payload_class"),
    ],
)
def test_rejects_forbidden_payload_classes_recursively(mutator, reason: str) -> None:
    proposal = accepted_proposal()
    mutator(proposal)

    decision = verify_proposal(proposal)

    assert decision["verifier_status"] == "rejected"
    assert reason in decision["rejection_reasons"]
    serialized = json.dumps(decision, ensure_ascii=False)
    assert "Федеральный закон" not in serialized
    assert "/tmp/source_inventory.safe.jsonl" not in serialized
    assert "BEGIN PROVIDER PAYLOAD" not in serialized


def test_rejected_decision_notes_are_bounded() -> None:
    proposal = accepted_proposal()
    proposal["hypothesis_payload"]["provider_debug"] = "BEGIN PROVIDER PAYLOAD"

    decision = verify_proposal(proposal)

    assert decision["decision_notes"] == ["proposal rejected with 2 bounded reason categories"]
    assert decision["acceptance_evidence_refs"] == []


def needs_review_proposal() -> dict:
    proposal = accepted_proposal()
    proposal["hypothesis_payload"]["evidence_refs"] = []
    return proposal


def test_needs_review_for_safe_proposal_without_evidence_refs() -> None:
    proposal = needs_review_proposal()

    decision = verify_proposal(proposal)
    item = review_queue_item(proposal, decision)

    assert decision["verifier_status"] == "needs_review"
    assert decision["rejection_reasons"] == ["insufficient_deterministic_evidence"]
    assert decision["acceptance_evidence_refs"] == []
    assert item["schema_version"] == "legalgraph-review-queue-item/v1"
    assert item["verifier_status"] == "needs_review"
    assert item["review_reason"] == "insufficient_deterministic_evidence"
    serialized = json.dumps(item, ensure_ascii=False)
    assert "Федеральный закон" not in serialized
    assert "/tmp/" not in serialized


def test_cli_writes_decision_and_review_queue_outputs(tmp_path: Path) -> None:
    proposal_path = tmp_path / "proposal.json"
    output_dir = tmp_path / "out"
    proposal_path.write_text(json.dumps(needs_review_proposal()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(proposal_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert json.loads(completed.stdout)["verifier_status"] == "needs_review"
    decision = json.loads((output_dir / "verifier_decision.json").read_text(encoding="utf-8"))
    item = json.loads((output_dir / "review_queue_item.json").read_text(encoding="utf-8"))
    assert decision["verifier_status"] == "needs_review"
    assert item["proposal_id"] == decision["proposal_id"]


def test_cli_rejected_smoke_writes_decision_only_and_exits_one(tmp_path: Path) -> None:
    proposal = accepted_proposal()
    proposal["hypothesis_payload"]["raw_vectors"] = [0.1]
    proposal_path = tmp_path / "proposal.json"
    output_dir = tmp_path / "out"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(proposal_path), "--output-dir", str(output_dir)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    decision = json.loads((output_dir / "verifier_decision.json").read_text(encoding="utf-8"))
    assert decision["verifier_status"] == "rejected"
    assert not (output_dir / "review_queue_item.json").exists()


def test_cli_help_and_accepted_smoke(tmp_path: Path) -> None:
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(accepted_proposal()), encoding="utf-8")

    help_run = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(proposal_path)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Deterministic no-LLM source hypothesis verifier" in help_run.stdout
    assert json.loads(completed.stdout)["verifier_status"] == "accepted"
