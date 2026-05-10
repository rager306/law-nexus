#!/usr/bin/env python3
"""Evaluate trigger proxy behavior across the FalkorDB skill pack.

This aggregates `pi-skill-creator/scripts/analyze_skill_triggers.py` reports for
the router and focused FalkorDB skills. It is still a proxy: it checks whether
skill descriptions align with should-trigger/boundary eval prompts, not whether
PI/GSD actually loaded a SKILL.md at runtime.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_SKILLS = [
    "falkordb",
    "falkordb-cypher",
    "falkordb-modeling",
    "falkordb-python",
    "falkordb-ops-debug",
    "falkordb-index-search",
    "falkordb-capability-evidence",
    "falkordb-algorithms",
    "falkordb-udf-flex",
    "falkordb-ingest-integrations",
    "falkordb-genai-mcp-graphrag",
    "falkordb-browser-rest",
]


def run_trigger_analyzer(analyzer: Path, skill_dir: Path, output: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(analyzer), str(skill_dir), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in {0, 2}:  # 2 means proxy completed but below threshold.
        raise RuntimeError(completed.stderr or completed.stdout or f"trigger analyzer failed for {skill_dir}")
    return json.loads(output.read_text(encoding="utf-8"))


def evaluate(skills_dir: Path, analyzer: Path, report_dir: Path, skills: list[str]) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    total = 0
    passed = 0
    false_negatives = 0
    false_positives = 0
    for skill in skills:
        skill_dir = skills_dir / skill
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Missing skill directory: {skill_dir}")
        output = report_dir / f"{skill}-trigger-proxy.json"
        report = run_trigger_analyzer(analyzer, skill_dir, output)
        summary = report["summary"]
        total += int(summary["total"])
        passed += int(summary["passed"])
        false_negatives += int(summary["false_negatives"])
        false_positives += int(summary["false_positives"])
        reports.append({
            "skill": skill,
            "report_path": str(output),
            "summary": summary,
            "actual_activation": report.get("actual_activation", "unavailable"),
        })
    return {
        "pack_name": "falkordb",
        "mode": "deterministic_trigger_proxy_pack",
        "actual_activation_supported": False,
        "actual_activation": "unavailable",
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "false_negatives": false_negatives,
            "false_positives": false_positives,
        },
        "skills": reports,
        "limitations": [
            "This is a description/eval trigger proxy, not PI/GSD runtime activation proof.",
            "actual_activation remains unavailable until headless tool-call or skill-read telemetry exists.",
        ],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# FalkorDB Skill Pack Trigger Proxy Evaluation",
        "",
        f"Mode: `{report['mode']}`",
        "",
        "## Summary",
        "",
        f"- Passed: {report['summary']['passed']}",
        f"- Failed: {report['summary']['failed']}",
        f"- Total: {report['summary']['total']}",
        f"- Pass rate: {report['summary']['pass_rate']:.2%}",
        f"- False negatives: {report['summary']['false_negatives']}",
        f"- False positives: {report['summary']['false_positives']}",
        f"- Actual activation: `{report['actual_activation']}`",
        "",
        "## Skills",
        "",
    ]
    for item in report["skills"]:
        marker = "✅" if item["summary"]["failed"] == 0 else "❌"
        lines.append(
            f"- {marker} `{item['skill']}` — "
            f"{item['summary']['passed']}/{item['summary']['total']} "
            f"({item['summary']['pass_rate']:.2%}); "
            f"FN={item['summary']['false_negatives']} FP={item['summary']['false_positives']} — "
            f"{item['report_path']}"
        )
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FalkorDB skill pack trigger proxy")
    parser.add_argument("--skills-dir", type=Path, default=Path(".agents/skills"))
    parser.add_argument("--analyzer", type=Path, default=Path(".agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py"))
    parser.add_argument("--report-dir", type=Path, default=Path(".agents/skills/falkordb/evals/trigger-proxy"))
    parser.add_argument("--json-output", type=Path, default=Path(".agents/skills/falkordb/evals/trigger-proxy-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path(".agents/skills/falkordb/evals/trigger-proxy-report.md"))
    parser.add_argument("--skill", action="append", dest="skills", help="Skill name to include; repeatable. Defaults to the FalkorDB pack.")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    try:
        report = evaluate(args.skills_dir, args.analyzer, args.report_dir, args.skills or DEFAULT_SKILLS)
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        write_markdown(report, args.markdown_output)
    except Exception as exc:  # noqa: BLE001
        print(f"FalkorDB trigger proxy evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "FalkorDB trigger proxy evaluation: "
        f"{report['summary']['passed']}/{report['summary']['total']} prompts passed "
        f"({report['summary']['pass_rate']:.2%}); "
        f"FN={report['summary']['false_negatives']} FP={report['summary']['false_positives']}"
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
