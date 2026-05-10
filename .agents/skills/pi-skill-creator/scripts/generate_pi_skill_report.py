#!/usr/bin/env python3
"""Generate a static PI/GSD skill eval report from benchmark artifacts."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_markdown(iteration_dir: Path, benchmark: dict[str, Any], grading: dict[str, Any]) -> str:
    lines = [
        f"# PI Skill Eval Report: {benchmark['metadata']['skill_name']}",
        "",
        f"Iteration: `{iteration_dir.name}`",
        f"Mode: `{benchmark['metadata']['mode']}`",
        "",
        "## Configuration Summary",
        "",
        "| Configuration | Runs | Passed | Failed | Total | Pass rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for config in benchmark.get("configurations", []):
        lines.append(
            f"| {config['configuration']} | {config['runs']} | {config['passed']} | {config['failed']} | {config['total']} | {config['pass_rate']:.2%} |"
        )
    lines.extend(["", "## Eval Runs", ""])
    for run in benchmark.get("runs", []):
        lines.append(f"### Eval {run['eval_id']} — `{run['configuration']}`")
        lines.append("")
        lines.append(f"Status: `{run['status']}`; pass rate: {run['summary']['pass_rate']:.2%}")
        lines.append("")
        for expectation in run.get("expectations", []):
            marker = "✅" if expectation.get("passed") else "❌"
            lines.append(f"- {marker} {expectation['text']} — {expectation['evidence']}")
        lines.append("")
    lines.extend([
        "## Interpretation",
        "",
        "- Treat this as local benchmark evidence only when outputs were produced by real with-skill/baseline runs.",
        "- If outputs were manually authored or dry-reviewed, record that limitation in the workspace notes.",
        "- Improve the skill only from repeated or high-severity failures, not one-off prompt overfitting.",
        "",
        "## Raw Artifacts",
        "",
        "- `benchmark.json`",
        "- `grading-summary.json`",
        "- per-run `grading.json` files",
        "",
    ])
    return "\n".join(lines)


def render_html(markdown: str, title: str) -> str:
    body = html.escape(markdown)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 2rem; line-height: 1.45; }}
    pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 1rem; border-radius: 8px; }}
  </style>
</head>
<body>
  <pre>{body}</pre>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PI skill eval report")
    parser.add_argument("iteration_dir", type=Path)
    args = parser.parse_args()
    benchmark_path = args.iteration_dir / "benchmark.json"
    grading_path = args.iteration_dir / "grading-summary.json"
    if not benchmark_path.is_file() or not grading_path.is_file():
        raise SystemExit("benchmark.json and grading-summary.json are required")
    benchmark = load_json(benchmark_path)
    grading = load_json(grading_path)
    markdown = render_markdown(args.iteration_dir, benchmark, grading)
    md_path = args.iteration_dir / "eval-report.md"
    html_path = args.iteration_dir / "eval-report.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(render_html(markdown, f"PI Skill Eval Report: {benchmark['metadata']['skill_name']}"), encoding="utf-8")
    print(f"Wrote report: {md_path}")
    print(f"Wrote report: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
