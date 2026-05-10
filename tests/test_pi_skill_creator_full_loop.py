from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

LOOP = Path(".agents/skills/pi-skill-creator/scripts/run_pi_skill_loop.py")
PACKAGE = Path(".agents/skills/pi-skill-creator/scripts/package_pi_skill.py")
SUGGEST = Path(".agents/skills/pi-skill-creator/scripts/suggest_description.py")
TRIGGERS = Path(".agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py")
EXECUTOR = Path(".agents/skills/pi-skill-creator/scripts/execute_pi_skill_eval.py")
PI_SKILL = Path(".agents/skills/pi-skill-creator")


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def fill_outputs(iteration: Path) -> None:
    for eval_dir in sorted(iteration.glob("eval-*")):
        metadata = json.loads((eval_dir / "eval_metadata.json").read_text(encoding="utf-8"))
        answer = "\n".join([metadata["expected_output"], *metadata["expectations"]])
        for run_dir in [p for p in eval_dir.iterdir() if p.is_dir() and (p / "outputs").is_dir()]:
            (run_dir / "outputs" / "answer.md").write_text(answer, encoding="utf-8")


def test_run_loop_pending_then_grades_and_reports(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    result = run_cmd([sys.executable, str(LOOP), str(PI_SKILL), "--workspace", str(workspace), "--iteration", "1"])
    assert result.returncode == 2, result.stderr + result.stdout
    iteration = workspace / "iteration-1"
    manifest = json.loads((iteration / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "pending_outputs"

    fill_outputs(iteration)
    result = run_cmd([
        sys.executable,
        str(LOOP),
        str(PI_SKILL),
        "--workspace",
        str(workspace),
        "--iteration",
        "1",
        "--no-prepare",
        "--min-pass-rate",
        "1.0",
    ])
    assert result.returncode == 0, result.stderr + result.stdout
    assert (iteration / "benchmark.json").is_file()
    assert (iteration / "eval-report.md").is_file()
    assert (iteration / "eval-report.html").is_file()
    history = json.loads((workspace / "history.json").read_text(encoding="utf-8"))
    assert history["current_best"] == "iteration-1"
    assert history["iterations"][0]["pass_rate"] == 1.0


def test_execute_pi_skill_eval_command_backend_and_loop_integration(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    result = run_cmd([sys.executable, str(LOOP), str(PI_SKILL), "--workspace", str(workspace), "--iteration", "1"])
    assert result.returncode == 2, result.stderr + result.stdout
    iteration = workspace / "iteration-1"
    command = (
        f"{sys.executable} -c "
        "\"import sys; prompt=sys.argv[1]; "
        "print('The output distinguishes structural validation from quality validation. '"
        "+ 'The output checks or asks for evals/evals.json. '"
        "+ 'The output reports missing evals as a limitation rather than claiming the skill is fully proven. '"
        "+ 'The output keeps the intent/draft/eval/iterate/description-improvement loop. '"
        "+ 'The output rejects blind copying of .claude/commands or claude -p assumptions. '"
        "+ 'The output maps the result to PI/GSD SKILL.md workflows references templates and scripts. '"
        "+ 'The output uses .agents/skills/ for project-local scope unless the user chooses global. '"
        "+ 'The output includes or asks for trigger conditions and expected output format. '"
        "+ 'The output includes eval prompts or a plan to create evals/evals.json. '"
        "+ 'The output runs or recommends validate_pi_skill.py or a project-specific verifier. '"
        "+ prompt[:20])\""
    )
    result = run_cmd([
        sys.executable,
        str(LOOP),
        str(PI_SKILL),
        "--workspace",
        str(workspace),
        "--iteration",
        "1",
        "--no-prepare",
        "--execute",
        "command",
        "--execute-command",
        command,
        "--min-pass-rate",
        "0.9",
    ])
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((iteration / "execution-summary.json").read_text(encoding="utf-8"))
    assert report["execution_kind"] == "real_subprocess"
    assert report["actual_activation"] == "unavailable"
    assert report["summary"]["failed"] == 0
    assert all((run_dir / "outputs" / "answer.md").is_file() for run_dir in iteration.glob("eval-*/*") if (run_dir / "outputs").is_dir())


def test_package_pi_skill_excludes_pycache_and_quality_reports(tmp_path: Path) -> None:
    archive = tmp_path / "pi-skill-creator.tar.gz"
    result = run_cmd([sys.executable, str(PACKAGE), str(PI_SKILL), "--output", str(archive), "--require-evals"])
    assert result.returncode == 0, result.stderr + result.stdout
    assert archive.is_file()
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "pi-skill-creator/SKILL.md" in names
    assert all("__pycache__" not in name for name in names)
    assert all(not name.endswith(".pyc") for name in names)


def test_suggest_description_outputs_candidate(tmp_path: Path) -> None:
    output = tmp_path / "suggestion.json"
    result = run_cmd([sys.executable, str(SUGGEST), str(PI_SKILL), "--output", str(output)])
    assert result.returncode == 0, result.stderr + result.stdout
    suggestion = json.loads(output.read_text(encoding="utf-8"))
    assert suggestion["skill_name"] == "pi-skill-creator"
    assert 0 < len(suggestion["candidate_description"]) <= 1024
    assert "current_description" in suggestion


def test_analyze_skill_triggers_reports_proxy_not_activation(tmp_path: Path) -> None:
    output = tmp_path / "trigger-proxy.json"
    result = run_cmd([sys.executable, str(TRIGGERS), str(PI_SKILL), "--output", str(output), "--min-pass-rate", "0.5"])
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["skill_name"] == "pi-skill-creator"
    assert report["actual_activation_supported"] is False
    assert report["actual_activation"] == "unavailable"
    assert report["trigger_proxy_kind"] == "static_description_eval_overlap"
    assert report["summary"]["total"] >= 3
    assert all(item["actual_activation"] == "unavailable" for item in report["results"])


def test_analyze_skill_triggers_handles_boundary_prompts(tmp_path: Path) -> None:
    skill_copy = tmp_path / "pi-skill-creator"
    shutil.copytree(PI_SKILL, skill_copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    evals_path = skill_copy / "evals" / "evals.json"
    evals = json.loads(evals_path.read_text(encoding="utf-8"))
    evals["evals"].append({
        "id": 99,
        "category": "boundary",
        "should_trigger": False,
        "prompt": "Debug a React hydration error in a frontend page.",
        "expected_output": "This should use a React/frontend/debugging skill, not pi-skill-creator.",
        "files": [],
        "expectations": ["The pi skill creator should not trigger for ordinary React debugging."],
    })
    evals_path.write_text(json.dumps(evals, indent=2), encoding="utf-8")
    output = tmp_path / "boundary-trigger-proxy.json"
    result = run_cmd([sys.executable, str(TRIGGERS), str(skill_copy), "--output", str(output), "--min-pass-rate", "1.0"])
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    boundary = next(item for item in report["results"] if item["eval_id"] == 99)
    assert boundary["should_trigger"] is False
    assert boundary["predicted_trigger"] is False
    assert boundary["passed"] is True
