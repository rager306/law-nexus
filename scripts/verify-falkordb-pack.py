#!/usr/bin/env python3
"""Run the complete FalkorDB skill pack verification suite.

This is the single command future agents/CI should use before claiming the
FalkorDB skill pack is healthy. It wraps:
- structural pack verification
- router deterministic quality gate
- focused pack deterministic quality gate
- trigger proxy gate
- PI/GSD structural validation for router and focused skills

It does not run live model benchmarks or runtime FalkorDB smoke tests.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PACK_SKILLS = [
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


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]


def run_step(step: Step) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(step.command, text=True, capture_output=True, check=False)
    duration_ms = int((time.monotonic() - started) * 1000)
    return {
        "name": step.name,
        "command": step.command,
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_steps(python: str, skills_dir: Path) -> list[Step]:
    steps = [
        Step("pack-structure", [python, "scripts/verify-falkordb-skill.py", "--root", str(skills_dir / "falkordb")]),
        Step("router-quality", [python, "scripts/evaluate-falkordb-skill-quality.py", "--min-pass-rate", "1.0"]),
        Step("focused-pack-quality", [python, "scripts/evaluate-falkordb-pack-quality.py", "--skills-dir", str(skills_dir), "--min-pass-rate", "1.0"]),
        Step("trigger-proxy", [python, "scripts/evaluate-falkordb-trigger-proxy.py", "--skills-dir", str(skills_dir), "--min-pass-rate", "1.0"]),
    ]
    validator = skills_dir / "pi-skill-creator" / "scripts" / "validate_pi_skill.py"
    for skill in PACK_SKILLS:
        steps.append(
            Step(
                f"pi-validation:{skill}",
                [python, str(validator), str(skills_dir / skill), "--require-evals"],
            )
        )
    return steps


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    return {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# FalkorDB Skill Pack Verification Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Passed: {report['summary']['passed']}",
        f"- Failed: {report['summary']['failed']}",
        f"- Total: {report['summary']['total']}",
        f"- Pass rate: {report['summary']['pass_rate']:.2%}",
        "",
        "## Steps",
        "",
    ]
    for result in report["results"]:
        marker = "✅" if result["passed"] else "❌"
        lines.append(
            f"- {marker} `{result['name']}` — exit {result['exit_code']} — {result['duration_ms']} ms"
        )
        if not result["passed"]:
            stderr = result["stderr"].strip()
            stdout = result["stdout"].strip()
            if stderr:
                lines.append(f"  - stderr: `{stderr[:500]}`")
            if stdout:
                lines.append(f"  - stdout: `{stdout[:500]}`")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This verifies skill artifacts and trigger proxies, not live model benchmark quality.",
            "- This verifies skill guidance, not live FalkorDB runtime capability behavior.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def verify(skills_dir: Path, json_output: Path, markdown_output: Path, python: str) -> dict[str, Any]:
    results = [run_step(step) for step in build_steps(python, skills_dir)]
    report = {
        "pack_name": "falkordb",
        "mode": "complete_skill_pack_verification",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summarize(results),
        "results": results,
        "limitations": [
            "No live model with-skill/baseline benchmark is run.",
            "No live FalkorDB runtime smoke test is run.",
        ],
    }
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, markdown_output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run complete FalkorDB skill pack verification")
    parser.add_argument("--skills-dir", type=Path, default=Path(".agents/skills"))
    parser.add_argument("--json-output", type=Path, default=Path(".agents/skills/falkordb/evals/verification-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path(".agents/skills/falkordb/evals/verification-report.md"))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    report = verify(args.skills_dir, args.json_output, args.markdown_output, args.python)
    print(
        "FalkorDB pack verification: "
        f"{report['summary']['passed']}/{report['summary']['total']} steps passed "
        f"({report['summary']['pass_rate']:.2%})"
    )
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
