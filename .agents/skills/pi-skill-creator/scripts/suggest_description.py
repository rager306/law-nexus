#!/usr/bin/env python3
"""Suggest a PI/GSD skill description from eval failures and current content.

This is a local, non-model helper. It does not replace a human/agent rewrite; it
summarizes trigger categories and emits a concise candidate under 1024 chars.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def current_description(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def extract_terms(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
    seen = []
    for word in words:
        low = word.lower()
        if low in {"skill", "output", "expected", "answer", "should", "with", "when", "user", "prompt", "this", "that"}:
            continue
        if low not in [x.lower() for x in seen]:
            seen.append(word)
        if len(seen) >= 12:
            break
    return seen


def failed_prompts(benchmark_path: Path) -> list[str]:
    if not benchmark_path.is_file():
        return []
    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    prompts = []
    for run in data.get("runs", []):
        if run.get("configuration") != "with_skill":
            continue
        if run.get("summary", {}).get("pass_rate", 1.0) < 1.0:
            prompts.append(str(run.get("eval_name") or run.get("eval_id")))
    return prompts


def suggest(skill_dir: Path, benchmark_path: Path | None) -> dict[str, str | list[str]]:
    desc = current_description(skill_dir)
    evals_path = skill_dir / "evals" / "evals.json"
    evals_text = evals_path.read_text(encoding="utf-8") if evals_path.is_file() else ""
    terms = extract_terms(desc + "\n" + evals_text)
    failures = failed_prompts(benchmark_path) if benchmark_path else []
    skill_name = skill_dir.name
    phrase = ", ".join(terms[:8])
    candidate = (
        f"Create, adapt, validate, and benchmark PI/GSD skills for {phrase}. "
        f"Use when users want to create or improve a skill, add evals/rubrics, compare with-skill against baseline outputs, grade expectations, aggregate benchmark reports, package skills, or tune trigger descriptions."
    )
    if len(candidate) > 1024:
        candidate = candidate[:1000].rsplit(" ", 1)[0] + "."
    return {
        "skill_name": skill_name,
        "current_description": desc,
        "candidate_description": candidate,
        "terms_used": terms,
        "failed_with_skill_runs": failures,
        "note": "Local heuristic suggestion; review before applying. Do not overfit to one eval prompt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest improved PI skill description")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--benchmark", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = suggest(args.skill_dir, args.benchmark)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote description suggestion: {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
