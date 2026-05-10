#!/usr/bin/env python3
"""Aggregate PI/GSD skill eval grading into benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_gradings(iteration_dir: Path) -> list[dict[str, Any]]:
    gradings = []
    for path in sorted(iteration_dir.glob("eval-*/*/grading.json")):
        gradings.append(json.loads(path.read_text(encoding="utf-8")))
    return gradings


def aggregate(iteration_dir: Path, skill_name: str) -> dict[str, Any]:
    gradings = load_gradings(iteration_dir)
    by_config: dict[str, list[dict[str, Any]]] = {}
    for grading in gradings:
        by_config.setdefault(grading["configuration"], []).append(grading)

    configurations = []
    for config, items in sorted(by_config.items()):
        pass_rates = [item["summary"]["pass_rate"] for item in items]
        passed = sum(item["summary"]["passed"] for item in items)
        total = sum(item["summary"]["total"] for item in items)
        configurations.append(
            {
                "configuration": config,
                "runs": len(items),
                "passed": passed,
                "failed": total - passed,
                "total": total,
                "pass_rate": round(passed / total, 4) if total else 0.0,
                "mean_eval_pass_rate": round(statistics.mean(pass_rates), 4) if pass_rates else 0.0,
                "stdev_eval_pass_rate": round(statistics.pstdev(pass_rates), 4) if len(pass_rates) > 1 else 0.0,
            }
        )

    benchmark = {
        "metadata": {
            "skill_name": skill_name,
            "iteration_dir": str(iteration_dir),
            "timestamp": datetime.now(UTC).isoformat(),
            "mode": "pi_local_grading_aggregate",
        },
        "configurations": configurations,
        "runs": gradings,
    }
    (iteration_dir / "benchmark.json").write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    write_markdown(benchmark, iteration_dir / "benchmark.md")
    return benchmark


def write_markdown(benchmark: dict[str, Any], path: Path) -> None:
    lines = [
        f"# Skill Benchmark: {benchmark['metadata']['skill_name']}",
        "",
        f"Mode: `{benchmark['metadata']['mode']}`",
        "",
        "## Configuration Summary",
        "",
        "| Configuration | Runs | Passed | Failed | Total | Pass rate | Mean eval pass rate | Stddev |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in benchmark["configurations"]:
        lines.append(
            f"| {item['configuration']} | {item['runs']} | {item['passed']} | {item['failed']} | {item['total']} | "
            f"{item['pass_rate']:.2%} | {item['mean_eval_pass_rate']:.2%} | {item['stdev_eval_pass_rate']:.2%} |"
        )
    lines.extend(["", "## Runs", ""])
    for run in benchmark["runs"]:
        lines.append(
            f"- Eval {run['eval_id']} `{run['configuration']}`: "
            f"{run['summary']['passed']}/{run['summary']['total']} "
            f"({run['summary']['pass_rate']:.2%}) — {run['status']}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate PI skill benchmark artifacts")
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--skill-name", default=None)
    args = parser.parse_args()
    manifest_path = args.iteration_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    skill_name = args.skill_name or manifest.get("skill_name") or args.iteration_dir.parent.name.removesuffix("-workspace")
    benchmark = aggregate(args.iteration_dir, skill_name)
    print(f"Wrote benchmark: {args.iteration_dir / 'benchmark.json'}")
    for item in benchmark["configurations"]:
        print(f"{item['configuration']}: {item['passed']}/{item['total']} ({item['pass_rate']:.2%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
