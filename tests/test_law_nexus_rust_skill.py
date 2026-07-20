from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents/skills/law-nexus-rust"
SKILL = SKILL_DIR / "SKILL.md"
POLICY = SKILL_DIR / "references/project-policy.md"
PROVENANCE = SKILL_DIR / "UPSTREAM.md"
EVALS = SKILL_DIR / "evals/evals.json"

REQUIRED_WORKFLOWS = [
    "implement-rust-slice.md",
    "review-rust-change.md",
    "migrate-python-parity.md",
    "optimize-proven-hot-path.md",
    "review-unsafe-code.md",
]


def test_rust_skill_preserves_language_and_process_boundaries() -> None:
    text = SKILL.read_text(encoding="utf-8")

    for phrase in [
        "Rust owns all product, domain, parser, retrieval, graph, and runtime behavior",
        "subprocess-only",
        "Reject PyO3",
        "deterministic-first",
        "LLM is never legal authority",
        "Do not rebuild the full legal corpus",
    ]:
        assert phrase in text


def test_rust_skill_routes_to_present_workflows_and_references() -> None:
    text = SKILL.read_text(encoding="utf-8")

    for name in REQUIRED_WORKFLOWS:
        assert f"workflows/{name}" in text
        assert (SKILL_DIR / "workflows" / name).is_file()

    for name in [
        "project-policy.md",
        "curated-rust-guidance.md",
        "verification-matrix.md",
    ]:
        assert f"references/{name}" in text
        assert (SKILL_DIR / "references" / name).is_file()


def test_rust_skill_records_pinned_mit_upstream_without_blanket_adoption() -> None:
    provenance = PROVENANCE.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")

    assert "fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9" in provenance
    assert "5a74070e740c8aacec1264adfc537daeab14c0f629bb604943295c08fd9252e6" in provenance
    assert "License: MIT" in provenance
    assert (SKILL_DIR / "LICENSE.upstream").read_text(encoding="utf-8").startswith("MIT License")

    for phrase in [
        "Generic defaults are not project mandates",
        "Do not set `target-cpu=native`",
        "PyO3",
        "standard library for small capabilities",
        "Rust 1.94.1",
        "edition 2021",
    ]:
        assert phrase in policy


def test_rust_skill_evals_cover_trigger_and_boundary_cases() -> None:
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    evals = data["evals"]

    assert data["skill_name"] == "law-nexus-rust"
    assert len(evals) >= 6
    assert any(item.get("should_trigger") is False for item in evals)

    eval_contract = json.dumps(evals, ensure_ascii=False)
    for phrase in ["PyO3", "zero-dependency", "target-cpu=native", "unsafe Rust", "Rust CI"]:
        assert phrase in eval_contract
