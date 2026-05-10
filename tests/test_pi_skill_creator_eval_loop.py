from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RUNNER = Path(".agents/skills/pi-skill-creator/scripts/run_pi_skill_eval.py")
GRADER = Path(".agents/skills/pi-skill-creator/scripts/grade_pi_skill_eval.py")
AGGREGATOR = Path(".agents/skills/pi-skill-creator/scripts/aggregate_pi_skill_benchmark.py")
PI_SKILL = Path(".agents/skills/pi-skill-creator")


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def test_eval_runner_grader_and_aggregator_roundtrip(tmp_path: Path) -> None:
    workspace = tmp_path / "pi-skill-creator-workspace"
    result = run_cmd([sys.executable, str(RUNNER), str(PI_SKILL), "--workspace", str(workspace), "--iteration", "1"])
    assert result.returncode == 0, result.stderr + result.stdout

    iteration = workspace / "iteration-1"
    assert (iteration / "run_manifest.json").is_file()
    eval_dirs = sorted(iteration.glob("eval-*"))
    assert eval_dirs

    for eval_dir in eval_dirs:
        metadata = json.loads((eval_dir / "eval_metadata.json").read_text(encoding="utf-8"))
        answer = "\n".join([metadata["expected_output"], *metadata["expectations"]])
        for config in ["with_skill", "baseline"]:
            output = eval_dir / config / "outputs" / "answer.md"
            output.write_text(answer, encoding="utf-8")

    result = run_cmd([sys.executable, str(GRADER), str(iteration), "--min-pass-rate", "1.0"])
    assert result.returncode == 0, result.stderr + result.stdout
    grading_summary = json.loads((iteration / "grading-summary.json").read_text(encoding="utf-8"))
    assert grading_summary["summary"]["pass_rate"] == 1.0

    result = run_cmd([sys.executable, str(AGGREGATOR), str(iteration)])
    assert result.returncode == 0, result.stderr + result.stdout
    benchmark = json.loads((iteration / "benchmark.json").read_text(encoding="utf-8"))
    assert {item["configuration"] for item in benchmark["configurations"]} == {"baseline", "with_skill"}
    assert (iteration / "benchmark.md").is_file()


def test_grader_reports_missing_outputs(tmp_path: Path) -> None:
    workspace = tmp_path / "pi-skill-creator-workspace"
    result = run_cmd([sys.executable, str(RUNNER), str(PI_SKILL), "--workspace", str(workspace), "--iteration", "1"])
    assert result.returncode == 0, result.stderr + result.stdout

    iteration = workspace / "iteration-1"
    result = run_cmd([sys.executable, str(GRADER), str(iteration), "--min-pass-rate", "1.0"])
    assert result.returncode != 0
    grading_summary = json.loads((iteration / "grading-summary.json").read_text(encoding="utf-8"))
    assert grading_summary["summary"]["pass_rate"] == 0.0
    assert any(item["status"] == "missing_output" for item in grading_summary["results"])
