from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "prd/architecture/acp/M048-S02-SOURCE-RECORD-MODEL.md"


def read_model() -> str:
    return MODEL.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def assert_terms(text: str, terms: list[str]) -> None:
    missing = [term for term in terms if term.casefold() not in text.casefold()]
    assert not missing, f"Missing required contract terms: {missing}"


def assert_patterns(text: str, patterns: list[str]) -> None:
    missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)]
    assert not missing, f"Missing required contract patterns: {missing}"


def section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match, f"Missing section: {heading}"
    return match.group(1)


def test_model_declares_core_categories_and_evidence_anchor_fields() -> None:
    text = read_model()

    assert_terms(
        text,
        [
            "RequirementBinding",
            "ArchitectureDecision",
            "ArchitecturePromptRecord",
            "ArchitectureProposal",
            "DecisionCandidate",
            "ProofGate",
            "EvidenceAnchor",
            "ArchitectureHealthFinding",
            "DerivedProjectionReference",
            "ProfileConstraint",
            "BlockedAction",
        ],
    )

    evidence_anchor = text
    assert_terms(
        evidence_anchor,
        [
            "anchor_kind",
            "repo_relative_path",
            "section_or_line_hint",
            "evidence_role",
            "claim_scope",
            "durability",
            "safety_classification",
        ],
    )


def test_model_covers_s01_surface_mapping_and_downstream_handoffs() -> None:
    text = read_model()
    mapping = section(text, "S01 Surface Mapping")

    assert_terms(
        mapping,
        [
            ".gsd/PROJECT.md",
            ".gsd/REQUIREMENTS.md",
            ".gsd/DECISIONS.md",
            ".gsd/KNOWLEDGE.md",
            ".gsd/STATE.md",
            "prd/project-state/*.md",
            "prd/project-state/data/*.json",
            ".gsd/exec/*",
            "git-lex acquisition/runtime path",
            "main-repo `.lex` absence",
            "durable proof anchor hazards",
            "law-nexus legal/FalkorDB/parser constraints",
        ],
    )
    assert_terms(text, ["Handoff Checklist for S03", "Handoff Checklist for S04", "Handoff Checklist for S06"])


def test_model_preserves_reusable_core_profile_split_and_non_claims() -> None:
    text = read_model()
    split = section(text, "Reusable ACP Core vs law-nexus Profile Split")
    non_claims = section(text, "Required Non-Claims")

    assert_patterns(
        split,
        [
            r"Reusable ACP core.*law-nexus profile",
            r"Source records outrank derived projections.*non-authoritative",
            r"law-nexus.*requirements.*LegalGraph.*Russian legal evidence.*FalkorDB",
            r"Main-repo.*git lex init.*`?\.lex`? state creation.*blocked|Main-repo.*`?\.lex`? state creation.*git lex init.*blocked",
        ],
    )
    assert_terms(non_claims, ["R035", "R037", "R038"])
    assert_patterns(
        non_claims,
        [
            r"does[\s\S]*not[\s\S]*validate[\s\S]*R035",
            r"does[\s\S]*not[\s\S]*validate[\s\S]*R037",
            r"does[\s\S]*not[\s\S]*validate[\s\S]*R038",
        ],
    )


def test_model_blocks_unsafe_authority_promotion_and_anchor_hazards() -> None:
    text = read_model()
    lowered = normalized(text)
    blocked_anchors = section(text, "Evidence-Anchor Rules")
    assertions = section(text, "Document Assertions for Future Agents")

    assert "authority_status: non_authoritative" in text
    assert "DerivedProjectionReference" in text
    assert_patterns(
        text,
        [
            r"derived projections?.*non-authoritative",
            r"prd/project-state/\*.*stale",
            r"\.gsd/exec/\*.*durable proof",
            r"absolute local paths",
            r"external URLs? as (?:the )?sole proof",
            r"raw provider payloads",
            r"raw vectors",
            r"secrets|tokens|credentials",
            r"unnecessary raw legal text",
            r"main-repo `git lex init`.*blocked",
            r"\.lex` state creation.*blocked",
        ],
    )
    assert_patterns(
        blocked_anchors + assertions,
        [
            r"ACP derived JSONL/RDF/recovery/projection files as the sole source",
            r"ProofGate`? definition does not satisfy the proof gate",
        ],
    )
    assert "serve as sole source anchor" in lowered or "sole source for an authoritative claim" in lowered


def test_model_negative_test_section_names_boundary_regressions() -> None:
    text = read_model()
    negative_tests = section(text, "Negative Tests")

    assert_terms(
        negative_tests,
        [
            "Stale `prd/project-state/*` presented as current M048 authority",
            "Derived ACP JSONL/RDF/recovery output presented as source truth",
            "Proof gate definition confused with proof satisfaction",
            "Unsafe or transient anchors cited as durable proof",
            "Main-repo git-lex initialized before isolated proof",
            "law-nexus profile constraints leaked into reusable ACP core",
            "R035/R037/R038 validated by ACP/projection evidence alone",
        ],
    )
