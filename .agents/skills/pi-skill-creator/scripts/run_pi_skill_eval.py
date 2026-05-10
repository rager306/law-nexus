#!/usr/bin/env python3
"""Create a PI/GSD skill evaluation workspace.

This runner intentionally does not fake model output. It prepares the same
with-skill/baseline directory shape Anthropic's skill-creator uses, writes exact
executor prompts/instructions for PI subagents or manual runs, snapshots the
skill, and records metadata. Use grade_pi_skill_eval.py after outputs are saved.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from validate_pi_skill import validate_skill


def load_evals(skill_dir: Path) -> dict[str, Any]:
    evals_path = skill_dir / "evals" / "evals.json"
    if not evals_path.is_file():
        raise SystemExit(f"Missing eval file: {evals_path}")
    data = json.loads(evals_path.read_text(encoding="utf-8"))
    if data.get("skill_name") != skill_dir.name:
        raise SystemExit("evals/evals.json skill_name must match skill directory name")
    return data


def next_iteration(workspace: Path) -> int:
    if not workspace.exists():
        return 1
    numbers = []
    for child in workspace.iterdir():
        if child.is_dir() and child.name.startswith("iteration-"):
            suffix = child.name.removeprefix("iteration-")
            if suffix.isdigit():
                numbers.append(int(suffix))
    return max(numbers, default=0) + 1


def slug(text: str) -> str:
    chars = []
    for ch in text.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "-":
            chars.append("-")
    value = "".join(chars).strip("-")[:60]
    return value or "eval"


def write_executor_prompt(path: Path, *, skill_dir: Path, eval_item: dict[str, Any], configuration: str) -> None:
    skill_clause = (
        f"Use this PI/GSD skill as the primary guidance: {skill_dir}\n"
        if configuration == "with_skill"
        else "Do not use the candidate skill. Answer from baseline project/system context only.\n"
    )
    files = eval_item.get("files", [])
    expectations = "\n".join(f"- {item}" for item in eval_item.get("expectations", []))
    path.write_text(
        f"# Executor Prompt — {configuration}\n\n"
        f"{skill_clause}\n"
        f"Task prompt:\n\n{eval_item['prompt']}\n\n"
        f"Expected output:\n\n{eval_item['expected_output']}\n\n"
        f"Input files: {files if files else 'none'}\n\n"
        f"Expectations to satisfy:\n{expectations}\n\n"
        "Save the final answer or artifact summary to `outputs/answer.md`. "
        "If files are created, put them under `outputs/` and list them in `outputs/metrics.json`.\n",
        encoding="utf-8",
    )


def run(skill_dir: Path, workspace: Path, iteration: int | None, baseline: str) -> Path:
    validate_skill(skill_dir, require_evals=True)
    evals = load_evals(skill_dir)
    iteration_num = iteration or next_iteration(workspace)
    iteration_dir = workspace / f"iteration-{iteration_num}"
    iteration_dir.mkdir(parents=True, exist_ok=False)

    snapshot_dir = iteration_dir / "skill-snapshot"
    shutil.copytree(skill_dir, snapshot_dir, ignore=shutil.ignore_patterns("*-workspace", "quality-report.*"))

    manifest = {
        "skill_name": skill_dir.name,
        "skill_path": str(skill_dir),
        "workspace": str(workspace),
        "iteration": iteration_num,
        "mode": "prepared_workspace",
        "baseline": baseline,
        "created_at": datetime.now(UTC).isoformat(),
        "eval_count": len(evals.get("evals", [])),
        "status": "pending_outputs",
    }
    (iteration_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    for item in evals.get("evals", []):
        eval_dir = iteration_dir / f"eval-{item['id']}-{slug(item['prompt'])}"
        eval_dir.mkdir()
        metadata = {
            "eval_id": item["id"],
            "eval_name": slug(item["prompt"]),
            "prompt": item["prompt"],
            "expected_output": item["expected_output"],
            "files": item.get("files", []),
            "expectations": item.get("expectations", []),
            "assertions": item.get("assertions", []),
        }
        (eval_dir / "eval_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        for configuration in ["with_skill", baseline]:
            run_dir = eval_dir / configuration
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(parents=True)
            write_executor_prompt(run_dir / "EXECUTOR_PROMPT.md", skill_dir=skill_dir, eval_item=item, configuration=configuration)
            (run_dir / "status.json").write_text(
                json.dumps({"status": "pending", "outputs_expected": "outputs/answer.md"}, indent=2),
                encoding="utf-8",
            )
    return iteration_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare PI/GSD skill eval workspace")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--iteration", type=int, default=None)
    parser.add_argument("--baseline", choices=["baseline", "old_skill"], default="baseline")
    args = parser.parse_args()
    workspace = args.workspace or args.skill_dir.with_name(f"{args.skill_dir.name}-workspace")
    iteration_dir = run(args.skill_dir, workspace, args.iteration, args.baseline)
    print(f"Prepared PI skill eval workspace: {iteration_dir}")
    print("Next: execute each EXECUTOR_PROMPT.md, save outputs/answer.md, then run grade_pi_skill_eval.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
