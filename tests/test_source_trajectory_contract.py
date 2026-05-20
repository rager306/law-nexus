from pathlib import Path

CONTRACT_PATH = Path("prd/research/source_structuring/09-trajectory-log-contract.md")


def read_contract() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def test_contract_defines_minimum_trajectory_file_set() -> None:
    text = read_contract()

    required_files = [
        "trajectory.jsonl",
        "discovery_steps.jsonl",
        "filtering_decisions.jsonl",
        "rejected_branches.jsonl",
        "conclusion_trace.json",
    ]

    missing = [file_name for file_name in required_files if file_name not in text]
    assert missing == []


def test_contract_defines_event_types_and_common_envelope() -> None:
    text = read_contract()

    required_markers = [
        "Event types",
        "run_started",
        "source_manifest_loaded",
        "source_structure_observed",
        "minimax_attempt_prepared",
        "minimax_attempt_completed",
        "candidate_extracted",
        "verifier_decision_recorded",
        "branch_rejected",
        "conclusion_recorded",
        "Common envelope fields",
        "schema_version",
        "record_id",
        "event_type",
        "phase",
        "timestamp_utc",
        "observed_context",
        "non_authoritative",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_contract_defines_concrete_record_shapes() -> None:
    text = read_contract()

    required_markers = [
        "`trajectory.jsonl` record",
        "run_status",
        "phase_status",
        "artifact_counts",
        "`discovery_steps.jsonl` record",
        "observed_structure",
        "supporting_context",
        "attempt_refs",
        "candidate_refs",
        "confidence_bucket",
        "`filtering_decisions.jsonl` record",
        "filter_result",
        "verifier_decision_ref",
        "`rejected_branches.jsonl` record",
        "rejection_reasons",
        "salvageable_observations",
        "retry_recommendation",
        "`conclusion_trace.json` object",
        "useful_discoveries",
        "open_questions",
        "next_actions",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_contract_defines_cross_reference_and_lifecycle_model() -> None:
    text = read_contract()

    required_markers = [
        "Cross-reference model",
        "trajectory:",
        "attempt:",
        "candidate:",
        "verifier:",
        "branch:",
        "review:",
        "assessment:",
        "source:",
        "Candidate lifecycle states",
        "proposed",
        "normalized",
        "filtered",
        "routed_to_verifier",
        "accepted",
        "rejected",
        "needs_review",
        "promoted_summary",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_contract_preserves_minimax_verifier_and_external_review_boundaries() -> None:
    text = read_contract()

    required_markers = [
        "MiniMax can move a candidate only to `proposed`",
        "It cannot move a candidate to `accepted`",
        "The verifier is the first component that may move a candidate to `accepted`",
        "GPT-5.5 is external control over CLI outputs",
        "It is not the runtime gate that accepts candidates",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_contract_preserves_open_data_logging_stance_and_non_claims() -> None:
    text = read_contract()

    required_markers = [
        "The legal source data is open.",
        "Trajectory logs may preserve useful source/legal context",
        "Open legal/source context can appear",
        "Do not strip useful context simply because it is legal text.",
        "legal correctness",
        "parser completeness",
        "product retrieval quality",
        "R035 validation",
        "R038 validation",
    ]

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_contract_avoids_concrete_secret_and_host_path_examples() -> None:
    text = read_contract()

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
