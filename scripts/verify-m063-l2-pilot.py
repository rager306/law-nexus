#!/usr/bin/env python3
"""Run the M063 bounded git-lex L2 diagnostic pilot harness.

This harness is intentionally constrained:
- runtime state is limited to disposable /tmp/m063-l2-* workspaces;
- persistent diagnostics append only to prd/architecture/acp/runtime/<milestone>/diagnostics.jsonl;
- the main checkout must never contain .lex, Squad, Raw, or .artifacts;
- ACP init uses the explicit canonical kit spec rager306/git-lex-kit-acp;
- law-nexus-kit is installed through a local-equivalent configured-kit scaffold copy.

The emitted diagnostics are pilot/runtime diagnostics only. They are not ACP
source truth, production adoption, main .lex adoption, or validation proof for
law-nexus requirements.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MILESTONE_ID = "M063-qp7ial"
RUNTIME_ROOT = ROOT / "prd/architecture/acp/runtime"
ACP_KIT_SPEC = "rager306/git-lex-kit-acp"
LAW_NEXUS_LOCAL_KIT = "local/git-lex-kit-law-nexus"
GIT_LEX_BIN_DIR = Path("/root/vendor-source/git-lex/target/debug")
MAIN_RESIDUE_NAMES = (".lex", "Squad", "Raw", ".artifacts")
WORKSPACE_PREFIX = "m063-l2-"
OUTPUT_LIMIT = 2048
MAX_WORKSPACE_BYTES = 1_000_000_000
MAX_WORKSPACE_FILES = 1000

CLASSIFICATION_VOCABULARY = frozenset(
    {
        "pass",
        "pass-with-shape-violation",
        "fail-closed",
        "blocked",
        "residue-violation",
        "pilot-aborted",
    }
)

FAILURE_MODES = (
    "state-corruption",
    "network-failure",
    "hook-failure",
    "validation-overflow",
    "workspace-retention-overrun",
    "main-repo-residue",
    "acp-native-only-overclaim",
    "user-abort",
)


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class FailureContext:
    result: CommandResult | None = None
    workspace: Path | None = None
    residue: dict[str, bool] | None = None
    record: dict[str, object] | None = None
    exception: BaseException | None = None


@dataclass(frozen=True)
class RecoveryPolicy:
    detection: str
    recovery: str
    classification: str
    default_action: str


class ResidueViolation(RuntimeError):
    """Raised when forbidden main-checkout residue is detected."""

    def __init__(self, residue: dict[str, bool]) -> None:
        present = ", ".join(name for name, exists in residue.items() if exists)
        super().__init__(f"main checkout residue present: {present}")
        self.residue = residue


RunCommand = Callable[[Sequence[str], Path, dict[str, str]], CommandResult]


RECOVERY_POLICIES: dict[str, RecoveryPolicy] = {
    "state-corruption": RecoveryPolicy(
        detection="git-lex validate non-zero or store read error",
        recovery="snapshot workspace, reset, retry once within the disposable pilot",
        classification="fail-closed",
        default_action="retry once, then fail closed",
    ),
    "network-failure": RecoveryPolicy(
        detection="git-lex init exit 127 or connection/fetch error",
        recovery="use the local-equivalent configured-kit scaffold path where possible",
        classification="blocked",
        default_action="fall back locally only inside the disposable workspace",
    ),
    "hook-failure": RecoveryPolicy(
        detection="git commit non-zero with hook/git-lex failure text",
        recovery="verify PATH includes the git-lex binary, retry once",
        classification="fail-closed",
        default_action="fail closed if the hook remains broken",
    ),
    "validation-overflow": RecoveryPolicy(
        detection="validator emits more than 100 violation lines",
        recovery="truncate output and keep diagnostics bounded",
        classification="pass-with-shape-violation",
        default_action="continue only as flagged diagnostic evidence",
    ),
    "workspace-retention-overrun": RecoveryPolicy(
        detection="workspace exceeds 1 GB or 1000 files",
        recovery="cleanup and rotate to a fresh disposable workspace",
        classification="pilot-aborted",
        default_action="halt pilot and raise to the user",
    ),
    "main-repo-residue": RecoveryPolicy(
        detection="any forbidden main-residue assert fails",
        recovery="halt immediately; do not auto-clean the main checkout",
        classification="residue-violation",
        default_action="fail closed and raise to the user",
    ),
    "acp-native-only-overclaim": RecoveryPolicy(
        detection="a JSONL record claims git-lex authority for ACP-native-only evidence",
        recovery="reject the authority claim and re-emit as diagnostic-only",
        classification="fail-closed",
        default_action="do not promote the claim",
    ),
    "user-abort": RecoveryPolicy(
        detection="KeyboardInterrupt or process exit 130",
        recovery="cleanup workspace and emit pilot-aborted",
        classification="pilot-aborted",
        default_action="wait for user direction",
    ),
}


REQUIRED_RECORD_FIELDS = frozenset(
    {
        "phase",
        "step",
        "command",
        "exit_code",
        "stdout_truncated",
        "stderr_truncated",
        "classification",
        "pre_residue",
        "post_residue",
        "workspace",
        "timestamp",
        "milestone_id",
    }
)


def truncate(value: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"


def main_residue_paths(root: Path = ROOT) -> list[Path]:
    return [root / name for name in MAIN_RESIDUE_NAMES]


def check_main_residue(root: Path = ROOT) -> dict[str, bool]:
    return {path.name: path.exists() for path in main_residue_paths(root)}


def assert_no_main_residue(root: Path = ROOT) -> dict[str, bool]:
    residue = check_main_residue(root)
    if any(residue.values()):
        raise ResidueViolation(residue)
    return residue


def git_lex_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{GIT_LEX_BIN_DIR}:{env.get('PATH', '')}"
    return env


def default_run_command(command: Sequence[str], cwd: Path, env: dict[str, str]) -> CommandResult:
    completed = subprocess.run(  # noqa: S603 - harness commands are explicit inputs.
        list(command),
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return CommandResult(
        command=list(command),
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def command_to_string(command: Sequence[str]) -> str:
    return " ".join(command)


def runtime_dir(milestone_id: str, root: Path = ROOT) -> Path:
    return root / "prd/architecture/acp/runtime" / milestone_id


def diagnostics_path(milestone_id: str, root: Path = ROOT) -> Path:
    return runtime_dir(milestone_id, root) / "diagnostics.jsonl"


def is_disposable_workspace(path: Path) -> bool:
    resolved = path.resolve()
    return resolved.parent == Path("/tmp") and resolved.name.startswith(WORKSPACE_PREFIX)


def create_workspace(workspace_dir: Path | None = None) -> tuple[Path, bool]:
    if workspace_dir is None:
        workspace = Path("/tmp") / f"{WORKSPACE_PREFIX}{uuid.uuid4().hex[:12]}"
        workspace.mkdir(parents=True, exist_ok=False)
        return workspace, True
    workspace = workspace_dir.resolve()
    if not is_disposable_workspace(workspace):
        raise ValueError("--workspace-dir must resolve to /tmp/m063-l2-<id>")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace, False


def enforce_state_locations(
    workspace: Path,
    milestone_id: str = DEFAULT_MILESTONE_ID,
    *,
    root: Path = ROOT,
    create_persistent: bool = True,
) -> dict[str, str]:
    if not is_disposable_workspace(workspace):
        raise ValueError("disposable workspace must be under /tmp/m063-l2-*")
    assert_no_main_residue(root)
    persistent = runtime_dir(milestone_id, root)
    expected_parent = root / "prd/architecture/acp/runtime"
    if expected_parent not in persistent.parents:
        raise ValueError("persistent diagnostics must stay under prd/architecture/acp/runtime")
    if create_persistent:
        persistent.mkdir(parents=True, exist_ok=True)
    return {
        "disposable": str(workspace.resolve()),
        "persistent": str(persistent.resolve()),
        "forbidden_main": str(root.resolve()),
    }


def make_record(
    *,
    phase: str,
    step: str,
    command: Sequence[str] | str,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
    classification: str,
    pre_residue: dict[str, bool] | None = None,
    post_residue: dict[str, bool] | None = None,
    workspace: Path | str,
    milestone_id: str = DEFAULT_MILESTONE_ID,
) -> dict[str, object]:
    if classification not in CLASSIFICATION_VOCABULARY:
        raise ValueError(f"unsupported classification: {classification}")
    command_string = command if isinstance(command, str) else command_to_string(command)
    return {
        "phase": phase,
        "step": step,
        "command": command_string,
        "exit_code": exit_code,
        "stdout_truncated": truncate(stdout),
        "stderr_truncated": truncate(stderr),
        "classification": classification,
        "pre_residue": pre_residue or {name: False for name in MAIN_RESIDUE_NAMES},
        "post_residue": post_residue or {name: False for name in MAIN_RESIDUE_NAMES},
        "workspace": str(workspace),
        "timestamp": datetime.now(UTC).isoformat(),
        "milestone_id": milestone_id,
    }


def record_shape_valid(record: dict[str, object]) -> bool:
    return REQUIRED_RECORD_FIELDS.issubset(record.keys())


def write_jsonl(
    records: Iterable[dict[str, object]],
    *,
    milestone_id: str = DEFAULT_MILESTONE_ID,
    root: Path = ROOT,
) -> None:
    path = diagnostics_path(milestone_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_checked_command(
    command: Sequence[str],
    cwd: Path,
    *,
    phase: str,
    step: str,
    workspace: Path,
    milestone_id: str,
    runner: RunCommand = default_run_command,
    root: Path = ROOT,
) -> dict[str, object]:
    try:
        pre = assert_no_main_residue(root)
    except ResidueViolation as exc:
        return make_record(
            phase=phase,
            step=step,
            command=command,
            exit_code=1,
            stderr=str(exc),
            classification="residue-violation",
            pre_residue=exc.residue,
            post_residue=exc.residue,
            workspace=workspace,
            milestone_id=milestone_id,
        )
    result = runner(command, cwd, git_lex_env())
    post = check_main_residue(root)
    classification = "pass" if result.exit_code == 0 else classify_command_failure(result, workspace)
    if any(post.values()):
        classification = "residue-violation"
    return make_record(
        phase=phase,
        step=step,
        command=result.command,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        classification=classification,
        pre_residue=pre,
        post_residue=post,
        workspace=workspace,
        milestone_id=milestone_id,
    )


def run_python_step(
    action: Callable[[], str],
    *,
    phase: str,
    step: str,
    command: str,
    workspace: Path,
    milestone_id: str,
    root: Path = ROOT,
) -> dict[str, object]:
    try:
        pre = assert_no_main_residue(root)
    except ResidueViolation as exc:
        return make_record(
            phase=phase,
            step=step,
            command=command,
            exit_code=1,
            stderr=str(exc),
            classification="residue-violation",
            pre_residue=exc.residue,
            post_residue=exc.residue,
            workspace=workspace,
            milestone_id=milestone_id,
        )
    try:
        stdout = action()
        exit_code = 0
        stderr = ""
        classification = "pass"
    except Exception as exc:  # noqa: BLE001 - convert pilot setup exceptions into diagnostics.
        stdout = ""
        stderr = str(exc)
        exit_code = 1
        classification = "fail-closed"
    post = check_main_residue(root)
    if any(post.values()):
        classification = "residue-violation"
    return make_record(
        phase=phase,
        step=step,
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        classification=classification,
        pre_residue=pre,
        post_residue=post,
        workspace=workspace,
        milestone_id=milestone_id,
    )


def copy_kit_scaffold(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"missing kit scaffold: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def set_repo_kit(repo_yml: Path, kit: str) -> None:
    if not repo_yml.exists():
        raise FileNotFoundError(f"missing git-lex repo config: {repo_yml}")
    lines = repo_yml.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("kit:"):
            updated.append(f"kit: {kit}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"kit: {kit}")
    repo_yml.write_text("\n".join(updated) + "\n", encoding="utf-8")


def copy_scaffolds_to_workspace(workspace: Path, *, root: Path = ROOT) -> str:
    copied_root = workspace / ".m063-l2-kit-source"
    copy_kit_scaffold(root / "git-lex-kit-acp", copied_root / "git-lex-kit-acp")
    copy_kit_scaffold(root / "git-lex-kit-law-nexus", copied_root / "git-lex-kit-law-nexus")
    return str(copied_root)


def install_law_nexus_local_kit(workspace: Path) -> str:
    copied_root = workspace / ".m063-l2-kit-source"
    source = copied_root / "git-lex-kit-law-nexus"
    destination = workspace / ".lex/kit/local/git-lex-kit-law-nexus"
    copy_kit_scaffold(source, destination)
    ontology_source = source / "ontology/law-nexus/law-nexus.ttl"
    if ontology_source.exists():
        ontology_dest = workspace / ".lex/ontology/law-nexus"
        ontology_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ontology_source, ontology_dest / "law-nexus.ttl")
    set_repo_kit(workspace / ".lex/repo.yml", LAW_NEXUS_LOCAL_KIT)
    return LAW_NEXUS_LOCAL_KIT


def workspace_stats(workspace: Path) -> tuple[int, int]:
    total_bytes = 0
    file_count = 0
    if not workspace.exists():
        return total_bytes, file_count
    for path in workspace.rglob("*"):
        if path.is_file():
            file_count += 1
            total_bytes += path.stat().st_size
    return total_bytes, file_count


def count_violation_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if "violation" in line.lower())


def detect_state_corruption(context: FailureContext) -> bool:
    result = context.result
    if result is None:
        return False
    text = f"{result.stdout}\n{result.stderr}".lower()
    return (
        "validate" in command_to_string(result.command)
        and result.exit_code != 0
        or "store read error" in text
        or "state corruption" in text
    )


def detect_network_failure(context: FailureContext) -> bool:
    result = context.result
    if result is None:
        return False
    text = f"{result.stdout}\n{result.stderr}".lower()
    return result.exit_code == 127 or any(
        marker in text
        for marker in ("connection", "network", "could not resolve", "failed to fetch", "timeout")
    )


def detect_hook_failure(context: FailureContext) -> bool:
    result = context.result
    if result is None:
        return False
    text = f"{result.stdout}\n{result.stderr}".lower()
    return "git commit" in command_to_string(result.command) and result.exit_code != 0 and (
        "hook" in text or "git-lex" in text
    )


def detect_validation_overflow(context: FailureContext) -> bool:
    result = context.result
    if result is None:
        return False
    return count_violation_lines(f"{result.stdout}\n{result.stderr}") > 100


def detect_workspace_retention_overrun(context: FailureContext) -> bool:
    if context.workspace is None:
        return False
    total_bytes, file_count = workspace_stats(context.workspace)
    return total_bytes > MAX_WORKSPACE_BYTES or file_count > MAX_WORKSPACE_FILES


def detect_main_repo_residue(context: FailureContext) -> bool:
    return bool(context.residue and any(context.residue.values()))


def detect_acp_native_only_overclaim(context: FailureContext) -> bool:
    record = context.record or {}
    tier = record.get("evidence_tier") or record.get("category")
    authority = record.get("authority") or record.get("authority_claim")
    return tier == "ACP-native-only" and authority not in (None, "diagnostic-only", False)


def detect_user_abort(context: FailureContext) -> bool:
    if isinstance(context.exception, KeyboardInterrupt):
        return True
    result = context.result
    return bool(result and result.exit_code == 130)


DETECTION_FUNCTIONS: dict[str, Callable[[FailureContext], bool]] = {
    "state-corruption": detect_state_corruption,
    "network-failure": detect_network_failure,
    "hook-failure": detect_hook_failure,
    "validation-overflow": detect_validation_overflow,
    "workspace-retention-overrun": detect_workspace_retention_overrun,
    "main-repo-residue": detect_main_repo_residue,
    "acp-native-only-overclaim": detect_acp_native_only_overclaim,
    "user-abort": detect_user_abort,
}


def detect_failure_mode(mode: str, context: FailureContext) -> bool:
    return DETECTION_FUNCTIONS[mode](context)


def classify_command_failure(result: CommandResult, workspace: Path) -> str:
    context = FailureContext(result=result, workspace=workspace)
    for mode in FAILURE_MODES:
        if detect_failure_mode(mode, context):
            return RECOVERY_POLICIES[mode].classification
    return "blocked"


def sample_context_for_failure_mode(mode: str, tmp_dir: Path | None = None) -> FailureContext:
    if mode == "state-corruption":
        return FailureContext(
            result=CommandResult(["git-lex", "validate"], "/tmp/m063-l2-sample", 1, stderr="store read error")
        )
    if mode == "network-failure":
        return FailureContext(
            result=CommandResult(
                ["git-lex", "init", "--kit", ACP_KIT_SPEC, "/tmp/m063-l2-sample"],
                "/tmp/m063-l2-sample",
                127,
                stderr="connection failed",
            )
        )
    if mode == "hook-failure":
        return FailureContext(
            result=CommandResult(["git", "commit", "-m", "x"], "/tmp/m063-l2-sample", 1, stderr="git-lex hook failed")
        )
    if mode == "validation-overflow":
        stdout = "\n".join(f"violation {idx}" for idx in range(101))
        return FailureContext(result=CommandResult(["git-lex", "validate"], "/tmp/m063-l2-sample", 1, stdout=stdout))
    if mode == "workspace-retention-overrun":
        workspace = (tmp_dir or Path("/tmp")) / "m063-l2-retention-sample"
        workspace.mkdir(parents=True, exist_ok=True)
        for idx in range(MAX_WORKSPACE_FILES + 1):
            (workspace / f"f{idx}.txt").write_text("x", encoding="utf-8")
        return FailureContext(workspace=workspace)
    if mode == "main-repo-residue":
        return FailureContext(residue={".lex": True, "Squad": False, "Raw": False, ".artifacts": False})
    if mode == "acp-native-only-overclaim":
        return FailureContext(record={"evidence_tier": "ACP-native-only", "authority": "git-lex"})
    if mode == "user-abort":
        return FailureContext(exception=KeyboardInterrupt())
    raise KeyError(mode)


def run_setup_steps(
    workspace: Path,
    *,
    milestone_id: str = DEFAULT_MILESTONE_ID,
    runner: RunCommand = default_run_command,
    root: Path = ROOT,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    records.append(
        run_checked_command(
            ["git", "-C", str(workspace), "init"],
            root,
            phase="setup",
            step="git-init-workspace",
            workspace=workspace,
            milestone_id=milestone_id,
            runner=runner,
            root=root,
        )
    )
    if records[-1]["classification"] != "pass":
        return records
    records.append(
        run_python_step(
            lambda: copy_scaffolds_to_workspace(workspace, root=root),
            phase="setup",
            step="copy-kit-scaffolds",
            command="copy git-lex-kit-acp and git-lex-kit-law-nexus scaffolds into workspace",
            workspace=workspace,
            milestone_id=milestone_id,
            root=root,
        )
    )
    if records[-1]["classification"] != "pass":
        return records
    records.append(
        run_checked_command(
            ["git-lex", "init", "--kit", ACP_KIT_SPEC, str(workspace)],
            workspace,
            phase="setup",
            step="git-lex-init-acp",
            workspace=workspace,
            milestone_id=milestone_id,
            runner=runner,
            root=root,
        )
    )
    if records[-1]["classification"] != "pass":
        return records
    records.append(
        run_python_step(
            lambda: install_law_nexus_local_kit(workspace),
            phase="setup",
            step="install-law-nexus-local-kit",
            command="copy law-nexus kit into .lex/kit/local and set repo.yml kit",
            workspace=workspace,
            milestone_id=milestone_id,
            root=root,
        )
    )
    return records


def run_failure_mode_checks(
    workspace: Path,
    *,
    milestone_id: str = DEFAULT_MILESTONE_ID,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    sample_root = workspace / ".failure-mode-samples"
    for mode in FAILURE_MODES:
        context = sample_context_for_failure_mode(mode, sample_root)
        detected = detect_failure_mode(mode, context)
        policy = RECOVERY_POLICIES[mode]
        stdout = json.dumps(
            {
                "mode": mode,
                "detected": detected,
                "detection": policy.detection,
                "recovery": policy.recovery,
                "policy_classification": policy.classification,
                "default_action": policy.default_action,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        records.append(
            make_record(
                phase="negative",
                step=f"failure-mode-{mode}",
                command="internal failure-mode detection check",
                exit_code=0 if detected else 1,
                stdout=stdout,
                classification="pass" if detected else "fail-closed",
                workspace=workspace,
                milestone_id=milestone_id,
            )
        )
    return records


def cleanup_workspace_records(
    workspace: Path,
    *,
    milestone_id: str = DEFAULT_MILESTONE_ID,
    root: Path = ROOT,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    records.append(
        run_python_step(
            lambda: shutil.rmtree(workspace) or str(workspace),
            phase="cleanup",
            step="cleanup-workspace",
            command=f"rm -rf {workspace}",
            workspace=workspace,
            milestone_id=milestone_id,
            root=root,
        )
        if workspace.exists()
        else make_record(
            phase="cleanup",
            step="cleanup-workspace",
            command=f"rm -rf {workspace}",
            exit_code=0,
            stdout="workspace already absent",
            classification="pass",
            workspace=workspace,
            milestone_id=milestone_id,
        )
    )
    cleanup_ok = not workspace.exists()
    residue = check_main_residue(root)
    records.append(
        make_record(
            phase="cleanup",
            step="verify-cleanup",
            command=f"test ! -e {workspace}",
            exit_code=0 if cleanup_ok else 1,
            stdout="workspace removed" if cleanup_ok else "workspace still present",
            classification="pass" if cleanup_ok else "pilot-aborted",
            pre_residue=residue,
            post_residue=residue,
            workspace=workspace,
            milestone_id=milestone_id,
        )
    )
    main_clean = not any(residue.values())
    records.append(
        make_record(
            phase="cleanup",
            step="verify-main-state",
            command="test ! -e /root/law-nexus/.lex && test ! -e /root/law-nexus/Squad && test ! -e /root/law-nexus/Raw && test ! -e /root/law-nexus/.artifacts",
            exit_code=0 if main_clean else 1,
            stdout="main checkout clean" if main_clean else "main checkout residue detected",
            classification="pass" if main_clean else "residue-violation",
            pre_residue=residue,
            post_residue=residue,
            workspace=workspace,
            milestone_id=milestone_id,
        )
    )
    return records


def should_abort(records: Sequence[dict[str, object]]) -> bool:
    return any(
        record["classification"] in {"fail-closed", "blocked", "residue-violation", "pilot-aborted"}
        for record in records
    )


def run_pilot(
    *,
    positive: bool,
    negative: bool,
    workspace_dir: Path | None = None,
    milestone_id: str = DEFAULT_MILESTONE_ID,
    runner: RunCommand = default_run_command,
    root: Path = ROOT,
) -> dict[str, object]:
    workspace, _created = create_workspace(workspace_dir)
    records: list[dict[str, object]] = []
    status = "pass"
    try:
        enforce_state_locations(workspace, milestone_id, root=root)
        if positive:
            records.extend(
                run_setup_steps(workspace, milestone_id=milestone_id, runner=runner, root=root)
            )
            if should_abort(records):
                status = "blocked"
        if negative and status == "pass":
            records.extend(run_failure_mode_checks(workspace, milestone_id=milestone_id))
            if should_abort(records):
                status = "blocked"
    except KeyboardInterrupt:
        status = "blocked"
        residue = check_main_residue(root)
        records.append(
            make_record(
                phase="abort",
                step="user-abort",
                command="KeyboardInterrupt",
                exit_code=130,
                stderr="user abort",
                classification="pilot-aborted",
                pre_residue=residue,
                post_residue=residue,
                workspace=workspace,
                milestone_id=milestone_id,
            )
        )
    except ResidueViolation as exc:
        status = "blocked"
        records.append(
            make_record(
                phase="setup",
                step="state-location-enforcement",
                command="verify main checkout residue absence",
                exit_code=1,
                stderr=str(exc),
                classification="residue-violation",
                pre_residue=exc.residue,
                post_residue=exc.residue,
                workspace=workspace,
                milestone_id=milestone_id,
            )
        )
    except Exception as exc:  # noqa: BLE001 - fail closed and preserve diagnostic record.
        status = "blocked"
        residue = check_main_residue(root)
        records.append(
            make_record(
                phase="setup",
                step="state-location-enforcement",
                command="enforce state locations",
                exit_code=1,
                stderr=str(exc),
                classification="fail-closed",
                pre_residue=residue,
                post_residue=residue,
                workspace=workspace,
                milestone_id=milestone_id,
            )
        )
    finally:
        records.extend(cleanup_workspace_records(workspace, milestone_id=milestone_id, root=root))
    write_jsonl(records, milestone_id=milestone_id, root=root)
    if should_abort(records):
        status = "blocked"
    return {
        "status": status,
        "milestone_id": milestone_id,
        "workspace": str(workspace),
        "diagnostics_path": str(diagnostics_path(milestone_id, root)),
        "record_count": len(records),
        "records": records,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--positive", action="store_true", help="run setup/init positive pilot path")
    mode.add_argument("--negative", action="store_true", help="run failure-mode detection checks")
    mode.add_argument("--all", action="store_true", help="run positive setup and negative checks")
    parser.add_argument("--workspace-dir", type=Path, default=None)
    parser.add_argument("--milestone-id", default=DEFAULT_MILESTONE_ID)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    positive = bool(args.positive or args.all or not (args.positive or args.negative or args.all))
    negative = bool(args.negative or args.all)
    result = run_pilot(
        positive=positive,
        negative=negative,
        workspace_dir=args.workspace_dir,
        milestone_id=args.milestone_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
