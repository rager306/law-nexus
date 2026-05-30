#!/usr/bin/env python3
"""Run M048/S09 isolated git-lex functional-fit proof diagnostics.

The harness is intentionally main-repo safe. It never runs `git lex init`, never
creates `.lex` in the law-nexus checkout, and performs all fixture/projection
work in a disposable temporary workspace copied from tracked S04 ACP fixtures.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
S04_HARNESS_PATH = ROOT / "scripts/run-m048-s04-git-lex-proof.py"
S05_HARNESS_PATH = ROOT / "scripts/run-m048-s05-git-lex-workflows.py"
S08_CONTRACT_PATH = ROOT / "prd/architecture/acp/M048-S08-GIT-LEX-PROOF-CONTRACT.md"
RUNTIME_DIAGNOSTICS_PATH = ROOT / "prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md"
FIT_REPORT_PATH = ROOT / "prd/architecture/acp/M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md"
RESULTS_PATH = ROOT / "build/acp/m048-s09/git_lex_capability_results.json"
MAIN_REPO_LEX_DIR = ROOT / ".lex"

SCENARIOS = [
    "source-record-lifecycle",
    "blocked-claim",
    "projection-boundary",
    "recovery-query",
    "git-semantics",
    "isolation-safety",
]


@dataclass
class CapabilityResult:
    scenario_id: str
    capability_id: str
    capability_name: str
    result_state: str
    failure_category: str | None
    evidence_anchor: str
    source_projection_authority_status: str
    workspace_path_class: str
    rollback_status: str
    allowed_next_action: str
    value_beyond_acp_native_git: str
    notes: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_probe(command: list[str], cwd: Path) -> dict[str, Any]:
    started = monotonic_ms()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout_preview": completed.stdout[:500],
            "stderr_preview": completed.stderr[:500],
            "duration_ms": monotonic_ms() - started,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout_preview": (exc.stdout or "")[:500] if isinstance(exc.stdout, str) else "",
            "stderr_preview": (exc.stderr or "")[:500] if isinstance(exc.stderr, str) else "",
            "duration_ms": monotonic_ms() - started,
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout_preview": "",
            "stderr_preview": str(exc),
            "duration_ms": monotonic_ms() - started,
            "timed_out": False,
        }


def runtime_diagnostics() -> dict[str, Any]:
    s04 = load_module(S04_HARNESS_PATH, "m048_s04_git_lex_proof_for_s09")
    s05 = load_module(S05_HARNESS_PATH, "m048_s05_git_lex_workflows_for_s09")
    main_lex_before = MAIN_REPO_LEX_DIR.exists()
    probes = [run_probe(["git", "lex", "--help"], ROOT), run_probe(["git-lex", "--help"], ROOT)]
    runtime_available = any(item.get("exit_code") == 0 and not item.get("timed_out") for item in probes)
    s05_contract = s05.build_contract()
    main_lex_after = MAIN_REPO_LEX_DIR.exists()
    return {
        "status": "pass" if not main_lex_before and not main_lex_after else "fail",
        "runtime_status": "available" if runtime_available else "blocked",
        "blocker_class": None if runtime_available else "UnsupportedGitLexRuntime",
        "safe_acquisition_policy": "no clone/install/download/durable build/git-lex-init from law-nexus",
        "tool_versions": {
            "python": sys.version.split()[0],
            "git_lex_runtime": "available" if runtime_available else "unavailable",
        },
        "workspace": {
            "main_repo": str(ROOT),
            "isolated_workspace_policy": "TemporaryDirectory outside the main checkout; copied tracked fixtures only; deleted after proof.",
        },
        "commands": probes,
        "s05_contract_status": s05_contract.get("status"),
        "s05_workflow_statuses": s05_contract.get("workflow_statuses", {}),
        "mutation_guard": {
            "checked": True,
            "main_lex_before": main_lex_before,
            "main_lex_after": main_lex_after,
            "safe": not main_lex_before and not main_lex_after,
        },
    }


def ordinary_git_semantics(workspace: Path) -> dict[str, Any]:
    """Exercise ordinary git in a disposable workspace for comparison only."""
    started = monotonic_ms()
    commands: list[dict[str, Any]] = []

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        commands.append({
            "command": command,
            "exit_code": completed.returncode,
            "stdout_preview": completed.stdout[:300],
            "stderr_preview": completed.stderr[:300],
        })
        return completed

    try:
        (workspace / "record.md").write_text("state: candidate\nvalue: alpha\n", encoding="utf-8")
        for command in [
            ["git", "init"],
            ["git", "config", "user.email", "s09@example.invalid"],
            ["git", "config", "user.name", "M048 S09 Harness"],
            ["git", "add", "record.md"],
            ["git", "commit", "-m", "candidate record"],
            ["git", "checkout", "-b", "accepted"],
        ]:
            run(command)
        (workspace / "record.md").write_text("state: accepted\nvalue: alpha\n", encoding="utf-8")
        for command in [
            ["git", "diff"],
            ["git", "add", "record.md"],
            ["git", "commit", "-m", "accept record"],
            ["git", "log", "--oneline", "--", "record.md"],
            ["git", "checkout", "master"],
        ]:
            run(command)
        (workspace / "record.md").write_text("state: blocked\nvalue: alpha\n", encoding="utf-8")
        for command in [
            ["git", "commit", "-am", "block record"],
            ["git", "merge", "accepted"],
        ]:
            run(command)
        conflict_seen = "<<<<<<<" in (workspace / "record.md").read_text(encoding="utf-8")
        ok = all(item["exit_code"] == 0 for item in commands[:10]) and conflict_seen
        return {
            "status": "pass" if ok else "blocked",
            "duration_ms": monotonic_ms() - started,
            "conflict_seen": conflict_seen,
            "commands": commands,
            "summary": "Ordinary git preserves branch/diff/history/conflict mechanics but has no ACP record-aware proof semantics.",
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic harness must fail closed.
        return {
            "status": "blocked",
            "duration_ms": monotonic_ms() - started,
            "error": str(exc),
            "commands": commands,
            "summary": "Ordinary git comparison could not complete in disposable workspace.",
        }


def run_functional_fit() -> dict[str, Any]:
    started = monotonic_ms()
    main_lex_before = MAIN_REPO_LEX_DIR.exists()
    runtime = runtime_diagnostics()
    s04 = load_module(S04_HARNESS_PATH, "m048_s04_git_lex_proof_for_s09_fit")
    cleanup_path = None
    cleanup_status = "not_started"
    results: list[CapabilityResult] = []
    fatal_failures: list[str] = []

    if main_lex_before:
        fatal_failures.append("main repository .lex exists before S09 proof")

    with tempfile.TemporaryDirectory(prefix="m048-s09-git-lex-fit-") as tmp:
        workspace = Path(tmp)
        cleanup_path = str(workspace)
        isolated_fixture_dir = workspace / "git-lex-isolated-proof"
        shutil.copytree(s04.FIXTURE_DIR, isolated_fixture_dir)
        records = s04.load_records(isolated_fixture_dir)
        validation_failures = s04.validate_records(records)
        projection = s04.acp_projection(records)
        lifecycle_failures = s04.validate_lifecycle(records)
        profile_failures = s04.validate_profile_boundary(records)
        blocked_failures = s04.validate_blocked_actions(records)
        git_result = ordinary_git_semantics(workspace / "ordinary-git") if shutil.which("git") else {
            "status": "blocked",
            "summary": "git executable unavailable for ordinary-git comparison.",
            "commands": [],
        }

        deterministic_failures = validation_failures + lifecycle_failures + profile_failures + blocked_failures
        deterministic_state = "pass" if not deterministic_failures else "fail"
        projection_state = "pass" if projection.get("authority_status") == "non_authoritative" else "fail"
        recovery_ok = any(item.get("record_kind") == "architecture_decision" and item.get("id") == "AD-ACP-0001" for item in projection.get("records", []))
        gate_edges = projection.get("edges", {}).get("PG-ACP-0001", [])

        results.extend([
            CapabilityResult(
                "source-record-lifecycle", "ACP-S09-C01", "Typed source record lifecycle",
                deterministic_state, None if deterministic_state == "pass" else "InsufficientEvidence",
                "prd/architecture/acp/fixtures/git-lex-isolated-proof/*.md",
                "source_records_authoritative_projection_non_authoritative",
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "implement_acp_native_or_adapter_later", "No runtime git-lex value proven; ACP-native typed fixtures satisfy the lifecycle proof contract deterministically.",
                "S04 fixture records validate taxonomy, anchors, lifecycle states, profile boundary, and blocked actions." if deterministic_state == "pass" else "; ".join(deterministic_failures),
                {"record_count": len(records), "record_ids": sorted(records)},
            ),
            CapabilityResult(
                "blocked-claim", "ACP-S09-C02", "Blocked claim and proof-gate diagnostics",
                "pass" if not blocked_failures and runtime["runtime_status"] == "blocked" else deterministic_state,
                "UnsupportedGitLexRuntime" if runtime["runtime_status"] == "blocked" else None,
                "prd/architecture/acp/fixtures/git-lex-isolated-proof/blocked-action.md",
                "source_records_authoritative_projection_non_authoritative",
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "keep_runtime_adoption_blocked_deferred", "git-lex adds no proven value while runtime is unavailable; explicit blocked diagnostics are ACP-native and durable.",
                "Runtime unavailability is recorded as a blocked/deferred result, not a pass and not adoption evidence.",
                {"runtime_status": runtime["runtime_status"], "blocker_class": runtime["blocker_class"]},
            ),
            CapabilityResult(
                "projection-boundary", "ACP-S09-C03", "Projection boundary and stale projection handling",
                projection_state, None if projection_state == "pass" else "ImitativeArtifact",
                "temporary derived projection generated from tracked fixtures",
                projection.get("authority_status", "unknown"),
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "keep_projection_derived_non_authoritative", "No git-lex runtime value proven; ACP can generate and reject authority inheritance with native source/projection markers.",
                "Derived projection stayed non-authoritative and cannot validate R035/R037/R038 or override source records.",
                {"projection_kind": projection.get("projection_kind"), "authority_status": projection.get("authority_status")},
            ),
            CapabilityResult(
                "recovery-query", "ACP-S09-C04", "Recovery query over source, proof gate, evidence, and dependents",
                "pass" if recovery_ok and "EA-ACP-0001" in gate_edges else "fail",
                None if recovery_ok and "EA-ACP-0001" in gate_edges else "InsufficientEvidence",
                "temporary derived projection generated from tracked fixtures",
                "source_records_authoritative_projection_non_authoritative",
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "continue_acp_native_recovery", "No git-lex runtime value proven; deterministic source-record recovery covers the required cold-reader chain.",
                "Recovered AD-ACP-0001 and PG-ACP-0001 -> EA-ACP-0001 evidence edge without relying on polished prose.",
                {"architecture_decision_recovered": recovery_ok, "proof_gate_edges": gate_edges},
            ),
            CapabilityResult(
                "git-semantics", "ACP-S09-C05", "Record-aware value beyond ordinary git",
                "blocked" if runtime["runtime_status"] == "blocked" else "partial",
                "UnsupportedGitLexRuntime" if runtime["runtime_status"] == "blocked" else None,
                "build/acp/m048-s09/git_lex_capability_results.json",
                "not_applicable_no_git_lex_projection",
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "ordinary_git_plus_acp_native_records_remains_sufficient", "Ordinary git covers branch/diff/history/conflict mechanics; no record-aware git-lex value was proven because the runtime is unavailable.",
                git_result.get("summary", "ordinary git comparison recorded"),
                {"ordinary_git": git_result, "runtime_status": runtime["runtime_status"]},
            ),
            CapabilityResult(
                "isolation-safety", "ACP-S09-C06", "Isolation safety and no-main-repo .lex guard",
                "pass" if runtime["mutation_guard"]["safe"] else "fail",
                None if runtime["mutation_guard"]["safe"] else "UnsafeMutation",
                "prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md",
                "not_applicable_safety_guard",
                "temporary_disposable_workspace", "deleted_by_TemporaryDirectory",
                "allow_future_isolated_adapter_spike_only", "No git-lex runtime state touched the main checkout; safety is preserved but adoption remains blocked/deferred.",
                "Main checkout .lex absence checked before and after; proof workspace is disposable.",
                {"mutation_guard": runtime["mutation_guard"], "cleanup_path": cleanup_path},
            ),
        ])
        cleanup_status = "deleted_by_TemporaryDirectory"

    main_lex_after = MAIN_REPO_LEX_DIR.exists()
    if main_lex_after:
        fatal_failures.append("main repository .lex exists after S09 proof")

    status = "fail" if fatal_failures or any(r.result_state == "fail" for r in results) else "blocked"
    if status != "fail" and all(r.result_state == "pass" for r in results):
        status = "pass"

    return {
        "harness": "m048-s09-git-lex-functional-fit",
        "status": status,
        "duration_ms": monotonic_ms() - started,
        "scenario_ids": SCENARIOS,
        "runtime": runtime,
        "main_repo_mutation_guard": {
            "checked": True,
            "main_lex_before": main_lex_before,
            "main_lex_after": main_lex_after,
            "safe": not main_lex_before and not main_lex_after,
        },
        "workspace": {"cleanup_path": cleanup_path, "cleanup_status": cleanup_status},
        "results": [r.__dict__ for r in results],
        "fatal_failures": fatal_failures,
        "adoption_conclusion": "Do not adopt runtime git-lex from S09 evidence. Keep ACP-native records plus ordinary git as sufficient baseline; consider adapter-only work only after explicit acquisition/runtime proof.",
    }


def render_runtime_markdown(diagnostics: dict[str, Any]) -> str:
    command_rows = "\n".join(
        f"| `{' '.join(item['command'])}` | {item['exit_code']} | {item['timed_out']} | {item['duration_ms']} ms | `{(item.get('stderr_preview') or item.get('stdout_preview') or '').strip()[:120]}` |"
        for item in diagnostics["commands"]
    )
    return f"""# M048 S09 git-lex Runtime Diagnostics

## Status

- Runtime status: `{diagnostics['runtime_status']}`
- Blocker class: `{diagnostics['blocker_class'] or 'none'}`
- Safe acquisition policy: {diagnostics['safe_acquisition_policy']}
- Main-repo mutation guard: `{'pass' if diagnostics['mutation_guard']['safe'] else 'fail'}`

## Workspace

- Main repository: `{diagnostics['workspace']['main_repo']}`
- Isolated workspace policy: {diagnostics['workspace']['isolated_workspace_policy']}

## Tool Versions

- Python: `{diagnostics['tool_versions']['python']}`
- git-lex runtime: `{diagnostics['tool_versions']['git_lex_runtime']}`

## Command Diagnostics

| Command | Exit code | Timed out | Duration | Preview |
| --- | ---: | --- | ---: | --- |
{command_rows}

## Main-repo `.lex` Guard

| Check | Result |
| --- | --- |
| `.lex` absent before proof | `{not diagnostics['mutation_guard']['main_lex_before']}` |
| `.lex` absent after proof | `{not diagnostics['mutation_guard']['main_lex_after']}` |
| Guard safe | `{diagnostics['mutation_guard']['safe']}` |

## S05 Carry-forward Contract

- S05 contract status: `{diagnostics['s05_contract_status']}`
- S05 workflow statuses: `{json.dumps(diagnostics['s05_workflow_statuses'], sort_keys=True)}`

## Conclusion

Runtime git-lex remains blocked/deferred when the local executable is unavailable. This is not a failed ACP-native deterministic proof and not adoption evidence. The main checkout stayed free of `.lex` state.
"""


def render_fit_report(payload: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| `{item['scenario_id']}` | `{item['capability_id']}` | `{item['result_state']}` | `{item['failure_category'] or 'none'}` | {item['allowed_next_action']} |"
        for item in payload["results"]
    )
    details = "\n\n".join(
        f"### {item['scenario_id']} / {item['capability_name']}\n\n"
        f"- Result: `{item['result_state']}`\n"
        f"- Failure category: `{item['failure_category'] or 'none'}`\n"
        f"- Evidence anchor: `{item['evidence_anchor']}`\n"
        f"- Authority status: `{item['source_projection_authority_status']}`\n"
        f"- Workspace path class: `{item['workspace_path_class']}`\n"
        f"- Rollback status: `{item['rollback_status']}`\n"
        f"- Value beyond ACP-native files plus ordinary git: {item['value_beyond_acp_native_git']}\n"
        f"- Notes: {item['notes']}"
        for item in payload["results"]
    )
    return f"""# M048 S09 git-lex Functional Fit Report

## Status

- Harness status: `{payload['status']}`
- Runtime status: `{payload['runtime']['runtime_status']}`
- Main-repo mutation guard safe: `{payload['main_repo_mutation_guard']['safe']}`
- Workspace cleanup: `{payload['workspace']['cleanup_status']}`

## Scenario Results

| Scenario | Capability | Result | Failure category | Allowed next action |
| --- | --- | --- | --- | --- |
{rows}

## Capability Evidence

{details}

## Value Assessment

S09 did not prove runtime git-lex adoption. Deterministic ACP-native fixtures provide typed records, lifecycle states, evidence anchors, proof gates, projection boundaries, and recovery/query behavior. Ordinary git provides branch, diff, history, and conflict mechanics. Because no local git-lex runtime responded to safe help probes, S09 found no proven record-aware git-lex value beyond ACP-native files plus ordinary git.

## Adoption Conclusion

{payload['adoption_conclusion']}

## Machine-readable Evidence

Per-capability rows are written to `build/acp/m048-s09/git_lex_capability_results.json`.
"""


def write_outputs(runtime: dict[str, Any] | None, fit: dict[str, Any] | None) -> None:
    if runtime is not None:
        RUNTIME_DIAGNOSTICS_PATH.write_text(render_runtime_markdown(runtime), encoding="utf-8")
    if fit is not None:
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(json.dumps(fit, indent=2, sort_keys=True), encoding="utf-8")
        FIT_REPORT_PATH.write_text(render_fit_report(fit), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-runtime", action="store_true", help="Run runtime probes and write runtime diagnostics.")
    parser.add_argument("--run-all", action="store_true", help="Run all S09 functional-fit scenarios.")
    parser.add_argument("--write-report", action="store_true", help="Write Markdown and JSON reports.")
    parser.add_argument("--no-main-repo-mutation", action="store_true", help="Fail if main checkout .lex exists before or after.")
    args = parser.parse_args()

    if not args.check_runtime and not args.run_all:
        parser.error("choose --check-runtime or --run-all")

    runtime = runtime_diagnostics() if args.check_runtime or args.run_all else None
    fit = run_functional_fit() if args.run_all else None
    if args.check_runtime or args.write_report:
        write_outputs(runtime, fit)

    output: dict[str, Any] = {"runtime": runtime}
    if fit is not None:
        output["functional_fit"] = fit
    print(json.dumps(output, indent=2, sort_keys=True))

    unsafe = False
    if args.no_main_repo_mutation:
        unsafe = MAIN_REPO_LEX_DIR.exists()
    if runtime and runtime["mutation_guard"]["safe"] is False:
        unsafe = True
    if fit and fit["main_repo_mutation_guard"]["safe"] is False:
        unsafe = True
    return 1 if unsafe else 0


if __name__ == "__main__":
    sys.exit(main())
