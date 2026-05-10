#!/usr/bin/env python3
"""Evaluate the FalkorDB focused skill pack against deterministic quality rubrics.

The structural verifier proves files exist. This quality gate checks whether each
focused skill actually contains the evidence boundaries, gotchas, and routing
signals expected for its May-2026 FalkorDB surface.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    skill: str
    files: tuple[str, ...]
    patterns: tuple[str, ...]
    description: str


PACK_CHECKS: list[Check] = [
    Check("falkordb-cypher", ("SKILL.md", "references/main.md"), ("Cypher", "GRAPH.QUERY", "GRAPH.EXPLAIN", "Neo4j"), "cypher routing and plan review"),
    Check("falkordb-cypher", ("references/main.md",), ("Parameterize", "do not interpolate", "capability-evidence"), "query safety and capability routing"),
    Check("falkordb-modeling", ("SKILL.md", "references/main.md"), ("labels", "relationships", "direction", "cardinality"), "modeling primitives"),
    Check("falkordb-modeling", ("references/main.md",), ("access patterns", "query", "Indexes"), "query-driven model/index guidance"),
    Check("falkordb-python", ("SKILL.md", "references/main.md"), ("falkordb-py", "from_url", "close/aclose"), "python client version surface"),
    Check("falkordb-python", ("references/main.md",), ("Never log credentials", "parameters", "UDF API"), "python safety and UDF notes"),
    Check("falkordb-ops-debug", ("SKILL.md", "references/main.md"), ("GRAPH.SLOWLOG", "GRAPH.INFO", "GRAPH.MEMORY", "GRAPH.CONFIG"), "ops command surface"),
    Check("falkordb-ops-debug", ("references/main.md",), ("4.18.x", "Bolt/WebSocket", "one variable"), "version-aware debugging"),
    Check("falkordb-index-search", ("SKILL.md", "references/main.md"), ("range", "full-text", "vector"), "index/search surfaces"),
    Check("falkordb-index-search", ("references/main.md",), ("docs-backed", "runtime-confirmed", "Neo4j vector syntax"), "index evidence boundary"),
    Check("falkordb-capability-evidence", ("SKILL.md", "references/main.md"), ("runtime-confirmed", "source-backed", "docs-backed", "smoke-needed"), "claim classes"),
    Check("falkordb-capability-evidence", ("references/main.md",), ("neo4j-only", "redisgraph-legacy", "unknown"), "drift classes"),
    Check("falkordb-algorithms", ("SKILL.md", "references/main.md"), ("BFS", "PageRank", "WCC", "MSF"), "algorithm coverage"),
    Check("falkordb-algorithms", ("references/main.md",), ("Neo4j GDS", "small fixtures", "output shape"), "algorithm boundary and proof"),
    Check("falkordb-udf-flex", ("SKILL.md", "references/main.md"), ("UDF", "FLEX", "QuickJS", "graph.getNodeById"), "UDF/FLEX surface"),
    Check("falkordb-udf-flex", ("references/main.md",), ("APOC", "Resource limits", "security review"), "UDF safety boundary"),
    Check("falkordb-ingest-integrations", ("SKILL.md", "references/main.md"), ("LOAD CSV", "Bulk Loader", "Kafka", "Snowflake"), "ingest/integration surface"),
    Check("falkordb-ingest-integrations", ("references/main.md",), ("idempotency", "batching", "verification counts"), "ingest correctness"),
    Check("falkordb-genai-mcp-graphrag", ("SKILL.md", "references/main.md"), ("GraphRAG", "MCP", "LangChain", "LlamaIndex"), "GenAI/MCP surface"),
    Check("falkordb-genai-mcp-graphrag", ("references/main.md",), ("retrieval quality", "citation", "traceability"), "retrieval quality boundary"),
    Check("falkordb-browser-rest", ("SKILL.md", "references/main.md"), ("Browser", "REST", "auth tokens", "graph endpoints"), "Browser/REST surface"),
    Check("falkordb-browser-rest", ("references/main.md",), ("bearer", "Do not conflate", "File upload"), "REST security boundary"),
]


FORBIDDEN_ACROSS_PACK = [
    "LegalGraph Nexus",
    "Russian legal",
    "44-fz",
    "Old_project",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def contains_all(text: str, patterns: tuple[str, ...]) -> tuple[bool, str]:
    haystack = normalize(text)
    missing = [pattern for pattern in patterns if normalize(pattern) not in haystack]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "matched: " + "; ".join(patterns)


def read_combined(skills_dir: Path, skill: str, files: tuple[str, ...]) -> str:
    parts = []
    for rel in files:
        path = skills_dir / skill / rel
        if not path.is_file():
            raise FileNotFoundError(f"Missing {skill}/{rel}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def evaluate(skills_dir: Path) -> dict:
    results = []
    passed = 0
    for check in PACK_CHECKS:
        text = read_combined(skills_dir, check.skill, check.files)
        ok, evidence = contains_all(text, check.patterns)
        passed += int(ok)
        results.append({
            "skill": check.skill,
            "description": check.description,
            "passed": ok,
            "evidence": f"{', '.join(check.files)}: {evidence}",
        })

    forbidden_results = []
    for skill_dir in sorted(skills_dir.glob("falkordb*")):
        if not skill_dir.is_dir() or skill_dir.name == "falkordb-legalgraph":
            continue
        markdown_files = [
            path
            for path in skill_dir.rglob("*.md")
            if not path.relative_to(skill_dir).parts[0] == "evals"
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files)
        for forbidden in FORBIDDEN_ACROSS_PACK:
            ok = normalize(forbidden) not in normalize(combined)
            passed += int(ok)
            results.append({
                "skill": skill_dir.name,
                "description": f"no project-specific leakage: {forbidden}",
                "passed": ok,
                "evidence": "absent" if ok else f"found forbidden term {forbidden!r}",
            })
            forbidden_results.append(ok)

    total = len(results)
    return {
        "pack_name": "falkordb",
        "mode": "deterministic_focused_skill_pack_quality",
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
        "results": results,
        "limitations": [
            "This checks focused skill artifacts, not live model behavior.",
            "Runtime capability claims still need source/docs/runtime smoke evidence per skill.",
        ],
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# FalkorDB Focused Skill Pack Quality Evaluation",
        "",
        f"Mode: `{report['mode']}`",
        "",
        "## Summary",
        "",
        f"- Passed: {report['summary']['passed']}",
        f"- Failed: {report['summary']['failed']}",
        f"- Total: {report['summary']['total']}",
        f"- Pass rate: {report['summary']['pass_rate']:.2%}",
        "",
        "## Results",
        "",
    ]
    for item in report["results"]:
        marker = "✅" if item["passed"] else "❌"
        lines.append(f"- {marker} `{item['skill']}` — {item['description']} — {item['evidence']}")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FalkorDB focused skill pack quality")
    parser.add_argument("--skills-dir", type=Path, default=Path(".agents/skills"))
    parser.add_argument("--json-output", type=Path, default=Path(".agents/skills/falkordb/evals/pack-quality-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path(".agents/skills/falkordb/evals/pack-quality-report.md"))
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    try:
        report = evaluate(args.skills_dir)
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        write_markdown(report, args.markdown_output)
    except Exception as exc:  # noqa: BLE001
        print(f"FalkorDB focused skill pack quality evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "FalkorDB focused skill pack quality evaluation: "
        f"{report['summary']['passed']}/{report['summary']['total']} checks passed "
        f"({report['summary']['pass_rate']:.2%})"
    )
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    if report["summary"]["pass_rate"] < args.min_pass_rate:
        print(
            f"Pass rate {report['summary']['pass_rate']:.2%} below required {args.min_pass_rate:.2%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
