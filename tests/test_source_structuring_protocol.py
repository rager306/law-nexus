from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "prd" / "research" / "source_structuring" / "05-llm-worker-dspy-protocol.md"


def protocol_text() -> str:
    return PROTOCOL.read_text(encoding="utf-8")


def test_protocol_contains_required_actor_and_input_boundaries() -> None:
    text = protocol_text()

    required = [
        "MiniMax",
        "GPT-5.5",
        "DSPy",
        "RLM",
        "Deterministic verifier",
        "non-authoritative",
        "source_artifact_id",
        "source_revision_id",
        "run_id",
        "output_refs",
        "metrics.safe.json",
        "diagnostics.safe.jsonl",
        "review_pack.json",
        "workspace_tracking.status",
    ]
    missing = [marker for marker in required if marker not in text]
    assert missing == []


def test_protocol_contains_closed_schema_and_status_contract() -> None:
    text = protocol_text()

    required = [
        "structural_hypothesis_proposal",
        "worker_attempt_summary",
        "verifier_decision",
        "review_queue_item",
        "proposal_id",
        "worker_attempt_id",
        "confidence_bucket",
        "pending",
        "accepted",
        "rejected",
        "needs_review",
        "A proposal may be `accepted` only if all of these are true",
    ]
    missing = [marker for marker in required if marker not in text]
    assert missing == []


def test_protocol_contains_failure_taxonomy_and_s06_handoff() -> None:
    text = protocol_text()

    required = [
        "Failure-state taxonomy",
        "schema_violation",
        "missing_safe_ref",
        "forbidden_payload_class",
        "raw_text_detected",
        "absolute_path_detected",
        "provider_payload_detected",
        "legal_answer_prose_detected",
        "insufficient_deterministic_evidence",
        "parser_completeness_overclaim",
        "r035_validation_overclaim",
        "S06 verifier skeleton handoff",
        "without calling any LLM",
        "Rejected hypotheses remain auditable",
    ]
    missing = [marker for marker in required if marker not in text]
    assert missing == []


def test_protocol_preserves_dspy_rlm_deferral_and_non_claims() -> None:
    text = protocol_text()

    required = [
        "No DSPy runtime dependency is added in S05",
        "No RLM runtime dependency is added in S05",
        "No optimizer, router, or training loop runs in S05",
        "Neither DSPy nor RLM may bypass the deterministic verifier",
        "does not claim legal correctness",
        "does not claim parser completeness",
        "does not validate R035",
        "product retrieval-quality claims",
    ]
    missing = [marker for marker in required if marker not in text]
    assert missing == []


def test_protocol_excludes_concrete_forbidden_payload_examples() -> None:
    text = protocol_text()

    forbidden = [
        "/tmp/",
        "/root/law-nexus",
        "Федеральный закон",
        "SHOULD_NOT_APPEAR",
        "sk-",
        "GIGACHAT_AUTH_DATA",
    ]
    violations = [marker for marker in forbidden if marker in text]
    assert violations == []
