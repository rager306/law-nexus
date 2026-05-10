from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / ".agents/skills/legalgraph-architecture-verification/SKILL.md"
README_PATH = ROOT / "prd/architecture/README.md"
SCHEMA_PATH = ROOT / "prd/architecture/architecture.schema.json"

CANONICAL_COMMANDS = [
    "uv run python scripts/verify-architecture-graph.py",
    "uv run python scripts/extract-prd-architecture-items.py --check",
    "uv run python scripts/build-architecture-graph.py --check",
    "uv run python scripts/extract-prd-architecture-items.py",
    "uv run python scripts/build-architecture-graph.py",
]

REQUIRED_PATHS = [
    "prd/architecture/README.md",
    "prd/architecture/architecture.schema.json",
    "prd/architecture/architecture_items.jsonl",
    "prd/architecture/architecture_edges.jsonl",
    "prd/architecture/architecture_graph_report.json",
    "prd/architecture/architecture_report.md",
    "scripts/verify-architecture-graph.py",
    "scripts/extract-prd-architecture-items.py",
    "scripts/build-architecture-graph.py",
]

SOURCE_BOUNDARY_PHRASES = [
    "source of truth",
    "derived",
    "non-authoritative",
    "do not hand-edit",
    "never override anchored",
    "PRD/GSD/ADR/source/runtime evidence",
]

FAILURE_CLASS_PHRASES = [
    "Extractor freshness drift",
    "Graph/report freshness drift",
    "Schema or JSONL shape failure",
    "Unsafe source anchor",
    "Graph integrity failure",
    "Decision fitness failure",
    "Positive overclaim failure",
]

README_FAILURE_CLASS_EQUIVALENTS = {
    "Extractor freshness drift": "Extractor freshness drift",
    "Graph/report freshness drift": "Graph/report freshness drift",
    "Schema or JSONL shape failure": "Malformed or invalid JSONL",
    "Unsafe source anchor": "Unsafe or stale source anchors",
    "Graph integrity failure": "Graph integrity failures",
    "Decision fitness failure": "Decision fitness failures",
    "Positive overclaim failure": "Positive overclaim failures",
}

ROUTING_RULE_PHRASES = [
    "legalgraph-nexus",
    "falkordb-legalgraph",
    "russian-legal-evidence",
    "R017",
    "M003",
]

PROOF_BOUNDARY_PHRASES = [
    "runtime behavior",
    "parser completeness",
    "retrieval quality",
    "generated-Cypher safety",
    "FalkorDB production scale",
    "legal-answer correctness",
    "LLM authority",
]

FORBIDDEN_POSITIVE_OVERCLAIM_PATTERNS = [
    re.compile(
        r"\bLegalGraph(?: Nexus)?\b[^.\n]{0,120}\b(?:is|are|provides|delivers|guarantees|validates)\b"
        r"[^.\n]{0,120}\b(?:product readiness|production-ready|validated product|legal correctness)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Legal KnowQL|ODT|parser|retrieval|FalkorDB|generated-Cypher|legal-answer)\b"
        r"[^.\n]{0,120}\b(?:is|are|supports|proves|validates|guarantees|delivers|scales)\b"
        r"[^.\n]{0,120}\b(?:complete|correct|safe|production scale|production-ready|quality|validated|runtime proof)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bLLM\b[^.\n]{0,120}\b(?:is|acts as|serves as|can be used as)\b"
        r"[^.\n]{0,120}\b(?:legal authority|architecture validation|source evidence|proof-level upgrade evidence)\b",
        re.IGNORECASE,
    ),
]

BOUNDARY_WORDS = (
    "does not",
    "do not",
    "must not",
    "not validate",
    "non-authoritative",
    "negative boundary",
    "without proof",
    "without matching proof",
    "unless",
    "until",
    "below validated",
    "unproven",
    "overclaim",
    "forbidden",
    "avoid",
    "keep claims bounded",
)


def read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def assert_contains(text: str, phrase: str) -> None:
    assert phrase in text, f"missing required phrase/path: {phrase}"


def iter_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+|\n-\s+", text) if sentence.strip()]


def is_boundary_sentence(sentence: str) -> bool:
    lowered = sentence.casefold()
    return any(word in lowered for word in BOUNDARY_WORDS)


def test_architecture_skill_references_current_canonical_paths_and_commands() -> None:
    skill = read_skill()

    for path in REQUIRED_PATHS:
        assert_contains(skill, path)
        assert (ROOT / path).exists(), f"skill references missing repository path: {path}"

    for command in CANONICAL_COMMANDS:
        assert_contains(skill, command)


def test_architecture_skill_preserves_source_of_truth_hierarchy() -> None:
    skill = read_skill()

    for phrase in SOURCE_BOUNDARY_PHRASES:
        assert_contains(skill, phrase)

    assert skill.index("Source of truth") < skill.index("Schema contract") < skill.index("Derived projections")
    assert "this skill" in skill and "never override anchored" in skill


def test_architecture_skill_names_expected_failure_classes_and_routing_rules() -> None:
    skill = read_skill()

    for phrase in FAILURE_CLASS_PHRASES:
        assert_contains(skill, phrase)

    for phrase in ROUTING_RULE_PHRASES:
        assert_contains(skill, phrase)

    for phrase in PROOF_BOUNDARY_PHRASES:
        assert_contains(skill, phrase)


def test_architecture_skill_stays_consistent_with_readme_contract() -> None:
    skill = read_skill()
    readme = README_PATH.read_text(encoding="utf-8")

    for command in CANONICAL_COMMANDS:
        assert_contains(readme, command)
        assert_contains(skill, command)

    for skill_phrase, readme_phrase in README_FAILURE_CLASS_EQUIVALENTS.items():
        assert_contains(readme, readme_phrase)
        assert_contains(skill, skill_phrase)

    assert_contains(readme, "S05 workflow integration should package this command")
    assert_contains(skill, "verified registry contract")


def test_architecture_skill_uses_schema_proof_levels_without_inventing_new_levels() -> None:
    skill = read_skill()
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    expected_levels = [
        "source-anchor",
        "static-check",
        "unit-test",
        "integration-test",
        "runtime-smoke",
        "real-document-proof",
        "production-observation",
    ]

    for level in expected_levels:
        assert_contains(schema, f'"{level}"')
        assert_contains(skill, f"`{level}`")


def test_architecture_skill_does_not_make_forbidden_positive_overclaims() -> None:
    offenders: list[str] = []
    for sentence in iter_sentences(read_skill()):
        if is_boundary_sentence(sentence):
            continue
        for pattern in FORBIDDEN_POSITIVE_OVERCLAIM_PATTERNS:
            if pattern.search(sentence):
                offenders.append(f"pattern={pattern.pattern} sentence={sentence}")

    assert not offenders, "forbidden overclaim pattern(s) found:\n" + "\n".join(offenders)
