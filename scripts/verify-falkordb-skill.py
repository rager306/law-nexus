#!/usr/bin/env python3
"""Verify the universal FalkorDB PI/GSD skill pack structure.

This verifier checks the reusable FalkorDB router plus Phase 1 and Phase 2
focused skills, not the LegalGraph-specific falkordb-legalgraph skill.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_ROUTER_FILES = [
    "SKILL.md",
    "workflows/check-capability.md",
    "workflows/design-graph-model.md",
    "workflows/write-cypher.md",
    "workflows/use-python-client.md",
    "workflows/use-falkordblite.md",
    "workflows/debug-performance.md",
    "references/capability-evidence.md",
    "references/cypher-falkordb.md",
    "references/graph-modeling.md",
    "references/indexes-search-vector.md",
    "references/python-client.md",
    "references/falkordblite.md",
    "references/troubleshooting.md",
    "references/skill-authoring-notes.md",
    "templates/capability-answer.md",
    "templates/graph-model-review.md",
    "templates/query-review.md",
]

REQUIRED_FOCUSED_SKILLS = {
    "falkordb-cypher": ["Cypher", "GRAPH.EXPLAIN", "Neo4j"],
    "falkordb-modeling": ["graph data models", "direction", "cardinality"],
    "falkordb-python": ["falkordb-py", "close/aclose", "parameters"],
    "falkordb-ops-debug": ["GRAPH.SLOWLOG", "GRAPH.INFO", "GRAPH.MEMORY"],
    "falkordb-index-search": ["range", "full-text", "vector"],
    "falkordb-capability-evidence": ["runtime-confirmed", "neo4j-only", "smoke-needed"],
    "falkordb-algorithms": ["BFS", "PageRank", "WCC"],
    "falkordb-udf-flex": ["UDF", "FLEX", "QuickJS"],
    "falkordb-ingest-integrations": ["LOAD CSV", "Bulk Loader", "Kafka"],
    "falkordb-genai-mcp-graphrag": ["GraphRAG", "MCP", "LangChain"],
    "falkordb-browser-rest": ["Browser", "REST", "bearer"],
}

REQUIRED_SKILL_TERMS = [
    "FalkorDB-first",
    "Retrieval-led reasoning",
    "neo4j-only",
    "runtime-confirmed",
    "smoke-needed",
    "blocked-environment",
    "workflows/check-capability.md",
    "references/skill-authoring-notes.md",
    "falkordb-cypher",
    "falkordb-capability-evidence",
    "falkordb-algorithms",
    "falkordb-udf-flex",
    "falkordb-genai-mcp-graphrag",
]

REQUIRED_AUTHORING_TERMS = [
    "PI/GSD already provides native skill-authoring guidance",
    "neo4j-contrib/neo4j-skills",
    "Vercel",
    "AgentSkills",
    "Anthropic",
    "AGENTS.md",
    "May 2026 skill pack decision",
]

FORBIDDEN_PROJECT_SPECIFIC_TERMS = [
    "LegalGraph Nexus",
    "legalgraph-nexus",
    "falkordb-legalgraph",
    "Russian legal",
    "44-fz",
    "Old_project",
]

REQUIRED_XML_TAGS = [
    "essential_principles",
    "quick_reference",
    "routing",
    "reference_index",
    "workflows_index",
    "success_criteria",
]


def fail(message: str) -> None:
    raise SystemExit(f"FalkorDB skill verification failed: {message}")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing required file: {path}")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        fail("SKILL.md missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        fail("SKILL.md frontmatter is not closed")
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            fail(f"invalid frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def verify_xml_sections(text: str, label: str, tags: list[str]) -> None:
    for tag in tags:
        if f"<{tag}>" not in text or f"</{tag}>" not in text:
            fail(f"{label} missing XML tag pair: {tag}")


def verify_no_project_specific_terms(text: str, label: str) -> None:
    for forbidden in FORBIDDEN_PROJECT_SPECIFIC_TERMS:
        if forbidden.lower() in text.lower():
            fail(f"{label} contains project-specific term: {forbidden}")


def verify_evals(skill_root: Path, expected_name: str) -> None:
    evals_path = skill_root / "evals" / "evals.json"
    if not evals_path.is_file():
        fail(f"{expected_name} missing evals/evals.json")
    data = json.loads(read(evals_path))
    if data.get("skill_name") != expected_name:
        fail(f"{expected_name} evals skill_name mismatch")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 2:
        fail(f"{expected_name} must have at least one positive eval and one boundary eval")
    if not any(item.get("should_trigger") is False or item.get("category") == "boundary" for item in evals):
        fail(f"{expected_name} evals must include a boundary/should-not-trigger case")


def verify_workflow_file(path: Path) -> None:
    text = read(path)
    for tag in ["required_reading", "process", "success_criteria"]:
        if f"<{tag}>" not in text or f"</{tag}>" not in text:
            fail(f"workflow lacks required XML sections: {path}")


def verify_focused_skill(skills_dir: Path, name: str, required_terms: list[str]) -> None:
    root = skills_dir / name
    if not root.is_dir():
        fail(f"missing Phase 1 focused skill: {name}")
    for rel in ["SKILL.md", "workflows/main.md", "references/main.md", "evals/evals.json"]:
        if not (root / rel).is_file():
            fail(f"{name} missing required file: {rel}")
    skill = read(root / "SKILL.md")
    fm = parse_frontmatter(skill)
    if fm.get("name") != name:
        fail(f"{name} frontmatter name mismatch")
    desc = fm.get("description", "")
    if not desc or len(desc) > 1024 or "Use" not in desc:
        fail(f"{name} description must be non-empty, <=1024 chars, and state when to use it")
    verify_xml_sections(skill, f"{name}/SKILL.md", REQUIRED_XML_TAGS)
    combined = "\n".join([skill, read(root / "workflows/main.md"), read(root / "references/main.md")])
    verify_no_project_specific_terms(combined, name)
    for term in [*required_terms, "FalkorDB", "falkordb-capability-evidence", "Neo4j"]:
        if term.lower() not in combined.lower():
            fail(f"{name} missing required term: {term}")
    verify_workflow_file(root / "workflows/main.md")
    verify_evals(root, name)


def verify(root: Path) -> None:
    if not root.exists():
        fail(f"skill root does not exist: {root}")

    skills_dir = root.parent
    for rel in REQUIRED_ROUTER_FILES:
        if not (root / rel).is_file():
            fail(f"missing required file: {rel}")

    skill = read(root / "SKILL.md")
    fm = parse_frontmatter(skill)
    if fm.get("name") != "falkordb":
        fail("router SKILL.md name must be 'falkordb'")
    description = fm.get("description", "")
    if not description or len(description) > 1024:
        fail("router description must be non-empty and <= 1024 characters")
    if "Use" not in description and "use" not in description:
        fail("router description must state when to use the skill")

    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            fail(f"router SKILL.md missing required term: {term}")

    if len(skill.splitlines()) > 500:
        fail("router SKILL.md exceeds 500 lines")
    verify_xml_sections(skill, "router SKILL.md", REQUIRED_XML_TAGS)

    all_router_text = "\n".join(read(root / rel) for rel in REQUIRED_ROUTER_FILES)
    verify_no_project_specific_terms(all_router_text, "universal router skill")

    authoring = read(root / "references/skill-authoring-notes.md")
    for term in REQUIRED_AUTHORING_TERMS:
        if term not in authoring:
            fail(f"skill-authoring-notes.md missing required term: {term}")

    capability = read(root / "references/capability-evidence.md")
    for cls in [
        "runtime-confirmed",
        "source-backed",
        "docs-backed",
        "smoke-needed",
        "blocked-environment",
        "neo4j-only",
        "redisgraph-legacy",
        "unknown",
    ]:
        if cls not in capability:
            fail(f"capability evidence missing claim class: {cls}")

    for workflow in (root / "workflows").glob("*.md"):
        verify_workflow_file(workflow)

    referenced = set(re.findall(r"`((?:workflows|references|templates)/[^`]+)`", skill))
    for rel in referenced:
        if not (root / rel).exists():
            fail(f"router SKILL.md references missing file: {rel}")

    for name, terms in REQUIRED_FOCUSED_SKILLS.items():
        verify_focused_skill(skills_dir, name, terms)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".agents/skills/falkordb")
    args = parser.parse_args()
    verify(Path(args.root))
    print(f"FalkorDB skill pack verification passed: {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
