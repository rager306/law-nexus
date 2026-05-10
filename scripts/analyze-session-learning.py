#!/usr/bin/env python3
"""Analyze a finished development session and suggest skill/memory improvements.

The script is intentionally conservative: it reads local evidence, writes a
retrospective report, and optionally saves short durable lessons to agentmemory.
It does not edit skills automatically. Humans/agents should review suggested
skill changes before applying them.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FAILURE_TERMS = ("error", "failed", "traceback", "exception", "no such file", "not found")
SKILL_DIR = Path(".agents/skills")


@dataclass(frozen=True)
class ExecRun:
    run_id: str
    purpose: str
    runtime: str
    exit_code: int | None
    stdout_path: Path | None
    stderr_path: Path | None


def read_text(path: Path | None, limit: int = 6000) -> str:
    if path is None or not path.exists() or not path.is_file():
        return ""
    data = path.read_text(encoding="utf-8", errors="replace")
    return data[-limit:]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def recent_exec_runs(gsd_dir: Path, limit: int) -> list[ExecRun]:
    exec_dir = gsd_dir / "exec"
    if not exec_dir.exists():
        return []
    meta_files = sorted(exec_dir.glob("*.meta.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    runs: list[ExecRun] = []
    for meta_file in meta_files[:limit]:
        meta = load_json(meta_file)
        run_id = meta_file.name.removesuffix(".meta.json")
        stdout = meta.get("stdout_path") or str(exec_dir / f"{run_id}.stdout")
        stderr = meta.get("stderr_path") or str(exec_dir / f"{run_id}.stderr")
        exit_code = meta.get("exit_code")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            exit_code = None
        runs.append(
            ExecRun(
                run_id=run_id,
                purpose=str(meta.get("purpose") or meta.get("label") or ""),
                runtime=str(meta.get("runtime") or ""),
                exit_code=exit_code,
                stdout_path=Path(stdout),
                stderr_path=Path(stderr),
            )
        )
    return runs


def git_status() -> list[str]:
    completed = subprocess.run(["git", "status", "--short"], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return [f"git status failed: {completed.stderr.strip() or completed.stdout.strip()}"]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def changed_skill_names(status_lines: list[str]) -> list[str]:
    names: set[str] = set()
    for line in status_lines:
        path = line[3:] if len(line) > 3 else line
        marker = ".agents/skills/"
        if marker not in path:
            continue
        after = path.split(marker, 1)[1]
        skill = after.split("/", 1)[0]
        if skill:
            names.add(skill)
    return sorted(names)


def has_failure_signal(run: ExecRun, stdout: str, stderr: str) -> bool:
    if run.exit_code not in {0, None}:
        return True
    stderr_lower = stderr.lower()
    if any(term in stderr_lower for term in FAILURE_TERMS):
        return True
    stdout_lower = stdout.lower()
    strong_stdout_terms = ("traceback", "exception", "no such file", "command not found")
    return any(term in stdout_lower for term in strong_stdout_terms)


def classify_exec_runs(runs: list[ExecRun]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    successes = 0
    for run in runs:
        stderr = read_text(run.stderr_path, 3000)
        stdout = read_text(run.stdout_path, 3000)
        combined = f"{stderr}\n{stdout}".lower()
        failed = has_failure_signal(run, stdout, stderr)
        if failed:
            failures.append(
                {
                    "id": run.run_id,
                    "purpose": run.purpose,
                    "exit_code": run.exit_code,
                    "signals": [term for term in FAILURE_TERMS if term in combined][:5],
                    "stderr_tail": stderr[-1000:],
                    "stdout_tail": stdout[-1000:],
                }
            )
        else:
            successes += 1
    return {"successes": successes, "failures": failures, "total": len(runs)}


def infer_recommendations(status_lines: list[str], exec_summary: dict[str, Any]) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    skills = changed_skill_names(status_lines)
    if skills:
        recommendations.append(
            {
                "kind": "skill-verification",
                "target": ", ".join(skills),
                "recommendation": "Run the relevant skill verifier after reviewing this session's lessons; for FalkorDB use `uv run python scripts/verify-falkordb-pack.py`.",
            }
        )
    if exec_summary["failures"]:
        recommendations.append(
            {
                "kind": "failure-learning",
                "target": "recent gsd_exec failures",
                "recommendation": "Review failed command tails and update the nearest skill reference/workflow only when the failure reveals a reusable gotcha, not a one-off typo.",
            }
        )
    if any(".agents/skills/pi-skill-creator" in line for line in status_lines):
        recommendations.append(
            {
                "kind": "meta-skill",
                "target": "pi-skill-creator",
                "recommendation": "Re-run PI skill validation and ensure new behavior is represented in evals, not only prose.",
            }
        )
    if any(".gsd/" in line for line in status_lines):
        recommendations.append(
            {
                "kind": "gsd-state",
                "target": ".gsd",
                "recommendation": "Checkpoint the GSD DB before staging and prefer GSD tools over manual artifact edits.",
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "kind": "no-action",
                "target": "session",
                "recommendation": "No obvious reusable skill update found from local evidence. Do not edit skills just to create churn.",
            }
        )
    return recommendations


def memory_candidates(recommendations: list[dict[str, str]], exec_summary: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for rec in recommendations:
        if rec["kind"] in {"failure-learning", "meta-skill", "skill-verification"}:
            candidates.append(
                {
                    "type": "fact" if rec["kind"] == "skill-verification" else "gotcha",
                    "content": f"Session retrospective recommendation ({rec['kind']}): {rec['recommendation']} Target: {rec['target']}.",
                }
            )
    for failure in exec_summary["failures"][:3]:
        purpose = failure.get("purpose") or failure.get("id")
        signals = ", ".join(failure.get("signals") or []) or "failure"
        candidates.append(
            {
                "type": "gotcha",
                "content": f"Recent session command `{purpose}` produced reusable failure signals: {signals}. Review logs before encoding as skill guidance.",
            }
        )
    return candidates[:5]


def save_to_agentmemory(base_url: str, candidate: dict[str, str]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/agentmemory/remember"
    body = json.dumps(candidate).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    secret = os.environ.get("AGENTMEMORY_SECRET")
    if secret:
        request.add_header("Authorization", f"Bearer {secret}")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - local configured endpoint.
            return {"ok": 200 <= response.status < 300, "status": response.status}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Session Learning Retrospective",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Recent exec runs inspected: {report['exec_summary']['total']}",
        f"- Exec failures/signals: {len(report['exec_summary']['failures'])}",
        f"- Changed skills: {', '.join(report['changed_skills']) or 'none'}",
        f"- Git status entries: {len(report['git_status'])}",
        "",
        "## Recommendations",
        "",
    ]
    for rec in report["recommendations"]:
        lines.append(f"- **{rec['kind']}** `{rec['target']}` — {rec['recommendation']}")
    lines.extend(["", "## Memory Candidates", ""])
    for candidate in report["memory_candidates"]:
        lines.append(f"- `{candidate['type']}` — {candidate['content']}")
    lines.extend(["", "## Failed Exec Signals", ""])
    for failure in report["exec_summary"]["failures"]:
        lines.append(f"- `{failure['id']}` `{failure.get('purpose', '')}` exit={failure.get('exit_code')} signals={failure.get('signals')}")
    if not report["exec_summary"]["failures"]:
        lines.append("- none")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    runs = recent_exec_runs(args.gsd_dir, args.exec_limit)
    status_lines = git_status()
    exec_summary = classify_exec_runs(runs)
    recommendations = infer_recommendations(status_lines, exec_summary)
    candidates = memory_candidates(recommendations, exec_summary)
    save_results: list[dict[str, Any]] = []
    if args.save_memory:
        for candidate in candidates:
            result = save_to_agentmemory(args.agentmemory_url, candidate)
            save_results.append({"candidate": candidate, "result": result})
    return {
        "mode": "session_learning_retrospective",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_status": status_lines,
        "changed_skills": changed_skill_names(status_lines),
        "exec_summary": exec_summary,
        "recommendations": recommendations,
        "memory_candidates": candidates,
        "memory_save_results": save_results,
        "limitations": [
            "This is local evidence analysis, not semantic proof that a skill should change.",
            "Skill edits remain manual/reviewed to avoid encoding one-off noise as durable guidance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze session logs and suggest skill/memory improvements")
    parser.add_argument("--gsd-dir", type=Path, default=Path(".gsd"))
    parser.add_argument("--exec-limit", type=int, default=20)
    parser.add_argument("--json-output", type=Path, default=Path(".gsd/session-learning-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path(".gsd/session-learning-report.md"))
    parser.add_argument("--save-memory", action="store_true", help="Save generated memory candidates to agentmemory")
    parser.add_argument("--agentmemory-url", default=os.environ.get("AGENTMEMORY_URL", "http://localhost:3111"))
    args = parser.parse_args()

    report = analyze(args)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(
        "Session learning retrospective: "
        f"{len(report['recommendations'])} recommendations, "
        f"{len(report['memory_candidates'])} memory candidates, "
        f"{len(report['exec_summary']['failures'])} failure signals"
    )
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    if args.save_memory:
        saved = sum(1 for item in report["memory_save_results"] if item["result"].get("ok"))
        print(f"agentmemory saved: {saved}/{len(report['memory_save_results'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
