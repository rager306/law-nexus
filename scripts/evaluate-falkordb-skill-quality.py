#!/usr/bin/env python3
"""Evaluate the universal FalkorDB skill against rubric-style quality evals.

This is a deterministic quality gate for the skill artifact itself. It checks
whether the skill's router/workflows/references/templates contain the behaviors
required by `.agents/skills/falkordb/evals/evals.json`.

It is intentionally not a full with/without-skill model benchmark; use the
PI skill-creator eval loop for that later. This gate prevents claiming quality
when the skill lacks routing, proof classes, templates, or gotcha coverage.
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
    file: str
    patterns: tuple[str, ...]
    description: str


EVAL_CHECKS: dict[int, list[Check]] = {
    1: [
        Check("SKILL.md", ("Vector/full-text/index/procedure/UDF claims", "workflows/check-capability.md"), "vector/capability routing"),
        Check("references/capability-evidence.md", ("runtime-confirmed", "source-backed", "docs-backed", "smoke-needed", "blocked-environment", "neo4j-only", "redisgraph-legacy", "unknown"), "complete claim classes"),
        Check("references/capability-evidence.md", ("Neo4j vector syntax", "APOC", "GDS", "Aura"), "Neo4j drift warning"),
        Check("references/indexes-search-vector.md", ("model encode proof", "vector storage/index creation proof", "vector query proof", "product quality proof"), "separated vector proof layers"),
        Check("templates/capability-answer.md", ("Status:", "Evidence:", "Caveats:", "Next proof:", "Verification criterion:"), "capability answer template"),
    ],
    2: [
        Check("SKILL.md", ("Design/review graph schema", "workflows/design-graph-model.md"), "graph model routing"),
        Check("references/graph-modeling.md", ("Model from questions", "not nouns"), "query-driven modeling"),
        Check("workflows/design-graph-model.md", ("direction", "cardinality"), "direction/cardinality requirement"),
        Check("references/graph-modeling.md", ("query pattern it supports", "verification query"), "index access-pattern mapping"),
        Check("templates/graph-model-review.md", ("Query coverage", "Indexes", "Risks", "Verification plan"), "graph review template"),
    ],
    3: [
        Check("SKILL.md", ("Write, translate, or review FalkorDB Cypher", "workflows/write-cypher.md"), "Cypher routing"),
        Check("references/capability-evidence.md", ("APOC", "Graph Data Science", "Aura", "Neo4j GenAI", "Neo4j driver", "Neo4j-specific Cypher"), "Neo4j-only feature filter"),
        Check("references/cypher-falkordb.md", ("Parameterize values", "do not interpolate user input"), "parameterization guardrail"),
        Check("templates/query-review.md", ("Schema assumptions", "Expected result", "Verification fixture", "Safety review"), "query review template"),
        Check("workflows/write-cypher.md", ("procedures", "workflows/check-capability.md"), "non-core behavior proof gate"),
    ],
    4: [
        Check("SKILL.md", ("falkordb-py", "workflows/use-python-client.md"), "Python client routing"),
        Check("workflows/use-python-client.md", ("Identify runtime mode",), "runtime mode preflight"),
        Check("references/python-client.md", ("Do not log credentials", "outside source code"), "secret/config guardrail"),
        Check("workflows/use-python-client.md", ("parameter", "rather than formatting values into query strings"), "parameter passing guardrail"),
        Check("workflows/use-python-client.md", ("graph name", "operation", "phase", "duration", "error"), "observability requirement"),
    ],
    5: [
        Check("SKILL.md", ("FalkorDBLite", "workflows/use-falkordblite.md"), "FalkorDBLite routing"),
        Check("references/falkordblite.md", ("local testing", "quick demos", "CI-like smoke"), "embedded intended role"),
        Check("references/falkordblite.md", ("Do not assume server/container behavior", "Do not assume FalkorDBLite behavior"), "embedded/server boundary"),
        Check("workflows/use-falkordblite.md", ("startup", "basic query", "cleanup"), "embedded verification"),
        Check("workflows/use-falkordblite.md", ("indexes", "full-text", "vector", "UDF", "persistence", "concurrency", "resource"), "capability routing for embedded claims"),
    ],
    6: [
        Check("SKILL.md", ("Slow queries/errors/runtime failures", "workflows/debug-performance.md"), "debug routing"),
        Check("workflows/debug-performance.md", ("graph name", "operation", "query text", "cardinality", "runtime mode", "exact error"), "narrow reproduction"),
        Check("references/troubleshooting.md", ("connection/auth", "unsupported Cypher", "missing index", "cartesian product", "Docker", "memory/resource"), "failure classification"),
        Check("workflows/debug-performance.md", ("smallest synthetic dataset",), "synthetic fixture"),
        Check("workflows/debug-performance.md", ("one variable at a time", "Rerun"), "one-change verification loop"),
    ],
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def contains_all(text: str, patterns: tuple[str, ...]) -> tuple[bool, str]:
    haystack = normalize(text)
    missing = [pattern for pattern in patterns if normalize(pattern) not in haystack]
    if missing:
        return False, f"missing: {', '.join(missing)}"
    return True, "matched: " + "; ".join(patterns)


def read_skill_file(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(f"Missing skill file for quality check: {rel}")
    return path.read_text(encoding="utf-8")


def evaluate(root: Path, evals_path: Path) -> dict:
    evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
    if evals_data.get("skill_name") != "falkordb":
        raise ValueError("evals/evals.json must have skill_name='falkordb'")

    results = []
    total = 0
    passed = 0

    for item in evals_data.get("evals", []):
        eval_id = item["id"]
        checks = EVAL_CHECKS.get(eval_id)
        if not checks:
            raise ValueError(f"No deterministic quality checks registered for eval id {eval_id}")
        expectations = []
        for check in checks:
            total += 1
            text = read_skill_file(root, check.file)
            ok, evidence = contains_all(text, check.patterns)
            passed += int(ok)
            expectations.append(
                {
                    "text": check.description,
                    "passed": ok,
                    "evidence": f"{check.file}: {evidence}",
                }
            )
        eval_passed = all(exp["passed"] for exp in expectations)
        results.append(
            {
                "eval_id": eval_id,
                "prompt": item["prompt"],
                "expected_output": item["expected_output"],
                "passed": eval_passed,
                "expectations": expectations,
            }
        )

    return {
        "skill_name": "falkordb",
        "mode": "deterministic_artifact_quality",
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
        "results": results,
        "limitations": [
            "This verifies the skill artifact against eval rubrics; it is not a live with/without-skill model benchmark.",
            "Future PI subagent benchmark can compare outputs with skill versus baseline/no skill.",
        ],
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# FalkorDB Skill Quality Evaluation",
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
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        lines.extend([f"### Eval {result['eval_id']} — {status}", "", f"Prompt: {result['prompt']}", ""])
        for exp in result["expectations"]:
            marker = "✅" if exp["passed"] else "❌"
            lines.append(f"- {marker} {exp['text']} — {exp['evidence']}")
        lines.append("")
    lines.extend(["## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FalkorDB skill quality against deterministic eval rubrics")
    parser.add_argument("--root", type=Path, default=Path(".agents/skills/falkordb"))
    parser.add_argument("--evals", type=Path, default=Path(".agents/skills/falkordb/evals/evals.json"))
    parser.add_argument("--json-output", type=Path, default=Path(".agents/skills/falkordb/evals/quality-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path(".agents/skills/falkordb/evals/quality-report.md"))
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    try:
        report = evaluate(args.root, args.evals)
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        write_markdown(report, args.markdown_output)
    except Exception as exc:  # noqa: BLE001 - CLI should report any validation failure clearly.
        print(f"FalkorDB skill quality evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "FalkorDB skill quality evaluation: "
        f"{report['summary']['passed']}/{report['summary']['total']} expectations passed "
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
