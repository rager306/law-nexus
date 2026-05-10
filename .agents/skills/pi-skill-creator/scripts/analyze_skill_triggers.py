#!/usr/bin/env python3
"""Analyze PI/GSD skill trigger behavior without claiming runtime activation.

This is a deterministic trigger proxy. It compares the skill frontmatter
`description` against eval prompts and optional should_trigger metadata. It does
not inspect PI/GSD headless tool-call transcripts and therefore always reports
actual_activation as unavailable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STOPWORDS = {
    "about",
    "actually",
    "after",
    "against",
    "and",
    "answer",
    "because",
    "before",
    "catch",
    "check",
    "code",
    "existing",
    "expected",
    "file",
    "for",
    "from",
    "have",
    "into",
    "just",
    "local",
    "make",
    "need",
    "output",
    "project",
    "prompt",
    "should",
    "that",
    "the",
    "them",
    "this",
    "use",
    "user",
    "when",
    "with",
    "wants",
    "whether",
    "would",
    "your",
}

TRIGGER_KEYWORDS = {
    "adapt",
    "benchmark",
    "compare",
    "create",
    "description",
    "eval",
    "evals",
    "export",
    "improve",
    "package",
    "rubric",
    "skill",
    "skills",
    "test",
    "trigger",
    "validate",
}

BOUNDARY_KEYWORDS = {
    "accessibility",
    "cloudflare",
    "database",
    "debug",
    "deploy",
    "falkordb",
    "frontend",
    "github",
    "legalgraph",
    "migration",
    "react",
    "security",
    "sql",
    "typescript",
}


def load_frontmatter(skill_dir: Path) -> dict[str, str]:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed")
    frontmatter: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter


def load_evals(skill_dir: Path) -> dict[str, Any]:
    evals_path = skill_dir / "evals" / "evals.json"
    if not evals_path.is_file():
        raise FileNotFoundError(f"Missing evals file: {evals_path}")
    return json.loads(evals_path.read_text(encoding="utf-8"))


def terms(text: str) -> set[str]:
    found = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower()):
        token = raw.strip("_-.")
        if len(token) >= 3 and token not in STOPWORDS:
            found.add(token)
    return found


def should_trigger(item: dict[str, Any]) -> bool:
    if "should_trigger" in item:
        return bool(item["should_trigger"])
    category = str(item.get("category", "")).lower()
    if category in {"should-not-trigger", "should_not_trigger", "boundary", "false-positive", "false_positive"}:
        return False
    return True


def score_eval(description_terms: set[str], item: dict[str, Any]) -> dict[str, Any]:
    prompt = str(item.get("prompt", ""))
    expected = should_trigger(item)
    prompt_terms = terms(prompt)
    matched = sorted(description_terms & prompt_terms)
    trigger_matches = sorted(prompt_terms & TRIGGER_KEYWORDS)
    boundary_matches = sorted(prompt_terms & BOUNDARY_KEYWORDS)

    positive_score = 0.0
    if prompt_terms:
        positive_score += min(0.7, len(matched) / max(4, len(prompt_terms)))
    positive_score += min(0.3, len(trigger_matches) * 0.1)
    positive_score = round(min(1.0, positive_score), 4)

    if expected:
        predicted = positive_score >= 0.12 or bool(trigger_matches)
        passed = predicted
    else:
        # For boundary prompts, a generic domain term alone should not trigger the skill.
        predicted = positive_score >= 0.25 and len(trigger_matches) >= 2
        passed = not predicted

    return {
        "eval_id": item.get("id"),
        "prompt": prompt,
        "should_trigger": expected,
        "predicted_trigger": predicted,
        "passed": passed,
        "trigger_proxy_score": positive_score,
        "matched_description_terms": matched,
        "trigger_terms": trigger_matches,
        "boundary_terms": boundary_matches,
        "actual_activation": "unavailable",
        "activation_note": "Static trigger proxy only; no PI/GSD runtime skill-load telemetry was inspected.",
    }


def analyze(skill_dir: Path) -> dict[str, Any]:
    frontmatter = load_frontmatter(skill_dir)
    description = frontmatter.get("description", "")
    description_terms = terms(description)
    eval_data = load_evals(skill_dir)
    results = [score_eval(description_terms, item) for item in eval_data.get("evals", [])]
    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    false_negatives = [item for item in results if item["should_trigger"] and not item["predicted_trigger"]]
    false_positives = [item for item in results if not item["should_trigger"] and item["predicted_trigger"]]
    return {
        "skill_name": skill_dir.name,
        "description": description,
        "description_terms": sorted(description_terms),
        "actual_activation_supported": False,
        "actual_activation": "unavailable",
        "trigger_proxy_kind": "static_description_eval_overlap",
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "false_negatives": len(false_negatives),
            "false_positives": len(false_positives),
        },
        "results": results,
        "limitations": [
            "This report is a trigger proxy, not proof of actual PI/GSD skill activation.",
            "Actual activation requires headless tool-call transcript or durable skill-read telemetry.",
        ],
        "next_runtime_work": [
            "Expose Skill/read tool calls in PI/GSD headless JSON output.",
            "Record reads of .../skills/{name}/SKILL.md for print/headless sessions.",
            "Populate actual_activation separately from trigger_proxy_score.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze PI/GSD skill trigger proxy behavior")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-pass-rate", type=float, default=0.0)
    args = parser.parse_args()

    try:
        report = analyze(args.skill_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Trigger proxy analysis failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote trigger proxy report: {args.output}")
    else:
        print(text)
    return 0 if report["summary"]["pass_rate"] >= args.min_pass_rate else 2


if __name__ == "__main__":
    raise SystemExit(main())
