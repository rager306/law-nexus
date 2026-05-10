#!/usr/bin/env python3
"""Grade PI/GSD skill eval outputs.

Reads an iteration workspace produced by run_pi_skill_eval.py. Each run should
save `outputs/answer.md`. Expectations are graded by explicit structured
assertions when present, otherwise by conservative keyword overlap against the
expectation text. This is deterministic and evidence-producing; for subjective
judgment, replace or supplement grading.json manually with reviewer evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "without", "is", "are", "be", "as", "by", "it", "this", "that", "skill", "answer", "output", "includes", "include", "uses", "use", "should", "must", "when", "whether",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9_.`/-]+", text.lower())
    result = []
    for word in words:
        clean = word.strip("`.,:;()[]{}")
        if len(clean) >= 4 and clean not in STOPWORDS:
            result.append(clean)
    return result[:8]


def read_output(run_dir: Path) -> str:
    outputs = run_dir / "outputs"
    answer = outputs / "answer.md"
    if answer.is_file():
        return answer.read_text(encoding="utf-8")
    parts = []
    for path in sorted(outputs.rglob("*")):
        if path.is_file() and path.stat().st_size < 200_000:
            try:
                parts.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return "\n".join(parts)


def grade_assertion(assertion: dict[str, Any], output: str) -> tuple[bool, str]:
    kind = assertion.get("kind", "contains")
    pattern = str(assertion.get("pattern", ""))
    text = normalize(output)
    needle = normalize(pattern)
    if kind == "contains":
        ok = needle in text
        return ok, f"contains {pattern!r}: {ok}"
    if kind == "not_contains":
        ok = needle not in text
        return ok, f"not_contains {pattern!r}: {ok}"
    if kind == "regex":
        ok = re.search(pattern, output, re.MULTILINE | re.IGNORECASE) is not None
        return ok, f"regex {pattern!r}: {ok}"
    raise ValueError(f"Unsupported assertion kind: {kind}")


def grade_expectation(expectation: str, output: str) -> tuple[bool, str]:
    keys = keywords(expectation)
    if not output.strip():
        return False, "no output found"
    if not keys:
        return False, "expectation has no gradeable keywords"
    text = normalize(output)
    matched = [key for key in keys if normalize(key) in text]
    threshold = max(1, min(len(keys), (len(keys) + 1) // 2))
    ok = len(matched) >= threshold
    return ok, f"matched {len(matched)}/{len(keys)} keywords: {matched}; threshold={threshold}"


def grade_run(eval_dir: Path, run_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    output = read_output(run_dir)
    expectations = []
    assertions = metadata.get("assertions") or []
    if assertions:
        for assertion in assertions:
            ok, evidence = grade_assertion(assertion, output)
            expectations.append({"text": assertion.get("text", assertion.get("pattern", "assertion")), "passed": ok, "evidence": evidence})
    else:
        for expectation in metadata.get("expectations", []):
            ok, evidence = grade_expectation(expectation, output)
            expectations.append({"text": expectation, "passed": ok, "evidence": evidence})
    passed = sum(1 for item in expectations if item["passed"])
    total = len(expectations)
    grading = {
        "eval_id": metadata["eval_id"],
        "eval_name": metadata["eval_name"],
        "configuration": run_dir.name,
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
        "output_chars": len(output),
        "status": "graded" if output.strip() else "missing_output",
    }
    (run_dir / "grading.json").write_text(json.dumps(grading, indent=2), encoding="utf-8")
    return grading


def grade_iteration(iteration_dir: Path) -> dict[str, Any]:
    results = []
    for eval_dir in sorted(iteration_dir.glob("eval-*")):
        metadata_path = eval_dir / "eval_metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for run_dir in sorted(child for child in eval_dir.iterdir() if child.is_dir() and child.name != "outputs"):
            if (run_dir / "outputs").is_dir():
                results.append(grade_run(eval_dir, run_dir, metadata))
    passed = sum(item["summary"]["passed"] for item in results)
    total = sum(item["summary"]["total"] for item in results)
    report = {
        "iteration": iteration_dir.name,
        "run_count": len(results),
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
        "results": results,
    }
    (iteration_dir / "grading-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade PI skill eval outputs")
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--min-pass-rate", type=float, default=0.0)
    args = parser.parse_args()
    report = grade_iteration(args.iteration_dir)
    print(
        f"PI skill grading: {report['summary']['passed']}/{report['summary']['total']} expectations passed "
        f"({report['summary']['pass_rate']:.2%}) across {report['run_count']} runs"
    )
    if report["summary"]["pass_rate"] < args.min_pass_rate:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
