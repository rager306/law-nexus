from pathlib import Path

POLICY_PATH = Path("prd/research/source_structuring/08-runtime-workspace-policy.md")


def read_policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def test_policy_defines_all_runtime_artifact_roots() -> None:
    text = read_policy()

    required_roots = [
        "runtime/inbox/",
        "runtime/raw/",
        "runtime/registry/",
        "runtime/processed/",
        "runtime/runs/",
        "runtime/trajectory/",
        "runtime/discovery/",
        "runtime/minimax-attempts/",
        "runtime/verifier/",
        "runtime/external-review/",
        "prd/research/source_structuring/",
    ]

    missing = [root for root in required_roots if root not in text]
    assert missing == []


def test_policy_preserves_open_legal_context_without_over_redaction() -> None:
    text = read_policy()

    required_markers = [
        "The source data is open legal data.",
        "should not over-redact useful source context",
        "Open legal/source context may be preserved",
        "Over-redaction is a failure mode",
        "Do not strip open legal/source context",
        "practical reproducibility and hygiene rules",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_policy_sets_tracking_and_promotion_rules() -> None:
    text = read_policy()

    required_markers = [
        "Tracking defaults",
        "ignored/local",
        "selectively tracked after review",
        "Promotion categories",
        "local_only",
        "candidate_durable",
        "promoted_summary",
        "superseded",
        "Runtime to research promotion rule",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_policy_defines_s02_to_s07_handoff_contract() -> None:
    text = read_policy()

    required_markers = [
        "S02 trajectory contract",
        "S03 MiniMax inside CLI contract",
        "S04 candidate contract",
        "S05 deterministic verifier contract",
        "S06 external GPT-5.5 review contract",
        "S07 assessment contract",
        "MiniMax is allowed at this stage",
        "GPT-5.5 remains external control over CLI outputs",
        "not an embedded runtime judge",
        "Deterministic verifier gates candidate adoption",
        "MiniMax output alone is never enough",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_policy_keeps_required_non_claims() -> None:
    text = read_policy()

    required_non_claims = [
        "legal correctness",
        "parser completeness",
        "product retrieval quality",
        "ontology validation",
        "graph-vector behavior",
        "production ETL readiness",
        "pilot readiness",
        "R035 validation",
        "R038 validation",
    ]

    missing = [claim for claim in required_non_claims if claim not in text]
    assert missing == []


def test_policy_avoids_concrete_secret_and_host_path_examples() -> None:
    text = read_policy()

    forbidden_markers = [
        "GIGACHAT_AUTH_DATA",
        "MINIMAX_API_KEY=",
        "OPENAI_API_KEY=",
        "sk-",
        "/root/",
        "/tmp/",
    ]

    present = [marker for marker in forbidden_markers if marker in text]
    assert present == []
