#!/usr/bin/env python3
"""Read-only installation checks; does not prove LLM/phase integration readiness."""

import argparse
import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

SHARED = runpy.run_path(str(Path(__file__).with_name("stack-env.py")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-path-state", action="store_true")
    args = parser.parse_args()
    try:
        ROOT = SHARED["canonical_root"](Path(__file__).resolve().parents[2])
        host_env = SHARED["build_env"](ROOT, isolated=False)
        host_env["HOME"] = host_env["AI_STACK_HOST_HOME"]
        agent_env = SHARED["build_env"](ROOT, host_env, isolated=True)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print("FAIL  shared environment: " + str(error))
        return 1
    LOCAL = ROOT / ".ai/local"
    pins = json.loads((ROOT / ".ai/versions.json").read_text())
    failures = []

    def check(name, ok, detail=""):
        print(("OK    " if ok else "FAIL  ") + name + (": " + detail if detail else ""))
        if not ok:
            failures.append(name)

    def call(command, timeout=30, env=None):
        try:
            return subprocess.run(
                list(map(str, command)),
                cwd=ROOT,
                text=True,
                env=host_env if env is None else env,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return subprocess.CompletedProcess(command, 1, "", str(error))

    ignored = call(["git", "check-ignore", "-q", "--no-index", ".ai/local/probe"])
    check("local data ignored", ignored.returncode == 0)
    tracked = call(["git", "ls-files", ".ai/local"])
    check("no tracked local data", tracked.returncode == 0 and not tracked.stdout.strip())
    check("isolated Allspark HOME", Path(agent_env["HOME"]) == LOCAL / "allspark-home")
    check(
        "shared Path worktree storage",
        host_env["GSD_PATH_WORKTREE_ROOT"] == agent_env["GSD_PATH_WORKTREE_ROOT"],
        agent_env["GSD_PATH_WORKTREE_ROOT"]
        + " ("
        + agent_env["AI_STACK_PATH_WORKTREE_ROOT_SOURCE"]
        + ")",
    )
    for name, command, wanted, env in [
        ("Node", [LOCAL / "node/bin/node", "--version"], "v" + pins["node"]["version"], host_env),
        (
            "Allspark",
            [LOCAL / "allspark-dist/bin/allspark", "--version"],
            pins["allspark"]["versionOutput"],
            agent_env,
        ),
        ("uv", [LOCAL / "tools/bin/uv", "--version"], "uv " + pins["uv"]["version"], host_env),
        (
            "PDD",
            [sys.executable, ROOT / "scripts/ai/pdd", "--version"],
            pins["pdd"]["version"],
            host_env,
        ),
    ]:
        result = call(command, env=env)
        actual = result.stdout.strip()
        ok = result.returncode == 0 and (
            actual == wanted or (name == "uv" and actual.startswith(wanted + " "))
        )
        check(name, ok, actual or result.stderr.strip()[:220])

    profile = call([sys.executable, ROOT / "scripts/ai/allspark", "--check-config"])
    check("Allspark profile", profile.returncode == 0, profile.stderr.strip()[:240])
    if profile.returncode == 0:
        info = json.loads(profile.stdout)
        if not info.get("defaultModel"):
            print(
                "PENDING model selection: start Allspark, use /login then /model; export-model afterwards."
            )
        template = json.loads((ROOT / ".ai/allspark/settings.json").read_text())
        for key in ("defaultProvider", "defaultModel"):
            if template.get(key) is not None and template[key] != info.get(key):
                check(
                    "tracked " + key + " applied",
                    False,
                    "run allspark-settings.py apply, or export intended model",
                )

    source = Path(agent_env["PI_PACKAGE_DIR"])
    source_marker = source / ".ai-install.json"
    try:
        receipt = json.loads(source_marker.read_text())
        check("Allspark source pin", receipt.get("commit") == pins["allspark"]["commit"])
    except (OSError, ValueError, AttributeError):
        check("Allspark source pin", False, "missing/invalid source install receipt")
    check(
        "full Allspark bundled skills",
        (source / "skills/edit/SKILL.md").is_file()
        and (source / "skills/graph/SKILL.md").is_file()
        and (source / "skills/edit/pyproject.toml").is_file(),
    )
    check(
        "kernel path outside task worktree",
        Path(agent_env["PRIME_AGENT_KERNEL_VENV"]) == LOCAL / "kernel-venv",
    )
    for tool in ("cargo", "rustup"):
        if shutil.which(tool, path=agent_env["PATH"]):
            print(
                "INFO  " + tool + " executable available; project toolchain/build not tested here."
            )
        else:
            print(
                "PENDING " + tool + " executable: install the Law-Nexus toolchain before its pilot."
            )

    skills = ROOT / ".agents/skills"
    required = ["path", "gsd-path", "gsd-path-build", "pdd-map", "pdd-ideate", "pdd-verify"]
    check(
        "required full skill directories",
        all((skills / name / "SKILL.md").is_file() for name in required),
    )
    check(
        "PDD helper/reference files",
        all(
            (skills / "pdd-verify" / rel).is_file()
            for rel in ("scripts/run-pdd-kit.mjs", "references/verification-rubric.md")
        ),
    )
    marker = skills / ".pdd-kit-install.json"
    try:
        data = json.loads(marker.read_text())
        # Fields below are verified against the 0.37.1 install output.
        check(
            "PDD install marker",
            isinstance(data, dict)
            and data.get("version") == pins["pdd"]["version"]
            and data.get("orchestrate") == "off",
        )
    except (OSError, ValueError):
        check("PDD install marker", False, "missing/invalid; reinstall full pinned skill bundle")

    declaration = ROOT / ".gsd-path/runtime.json"
    try:
        data = json.loads(declaration.read_text())
        ok = (
            isinstance(data, dict)
            and data.get("schema") == "gsd-path/runtime/v1"
            and data.get("version") == pins["path"]["version"]
            and data.get("digest") == pins["path"]["runtimeDigest"]
        )
        check("Path runtime declaration", ok)
    except (OSError, ValueError):
        check("Path runtime declaration", False, "missing/invalid")
    runtime_command = [
        sys.executable,
        "-B",
        ROOT / ".gsd-path/status_runtime.py",
        "--repo",
        ROOT,
        "--runtime-path",
    ]
    for label, env in (("host", host_env), ("Allspark", agent_env)):
        resolved = call(runtime_command, env=env)
        expected = Path(env["HOME"]) / ".gsd-path/runtimes" / pins["path"]["runtimeDigest"]
        valid = resolved.returncode == 0 and Path(resolved.stdout.strip()) == expected
        check(
            "Path runtime verified in " + label + " HOME",
            valid,
            str(expected) if valid else resolved.stderr.strip()[:240],
        )
    try:
        run_settings = json.loads((ROOT / ".ai/path-run.json").read_text())
        worker = run_settings.get("worker", []) if isinstance(run_settings, dict) else []
        check(
            "headless Allspark worker",
            isinstance(worker, list)
            and worker
            and worker[0] == "scripts/ai/allspark-worker"
            and any(flag in worker for flag in ("-p", "--print")),
        )
    except (OSError, ValueError):
        check("headless Allspark worker", False, "missing/invalid path-run.json")
    hook_dirs = {}
    for label, env in (("host", host_env), ("Allspark", agent_env)):
        result = call(
            ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks"], env=env
        )
        directory = Path(result.stdout.strip()).resolve() if result.returncode == 0 else None
        hook_dirs[label] = directory
        for hook in ("pre-commit", "commit-msg", "pre-push"):
            path = directory / hook if directory else Path("/nonexistent")
            present = path.is_file() and os.access(path, os.X_OK)
            has_path_guard = present and "gsd-path" in path.read_text(errors="replace")
            check("Path Git hook " + hook + " in " + label, has_path_guard)
    check(
        "same effective Git hooks in both homes",
        hook_dirs["host"] is not None and hook_dirs["host"] == hook_dirs["Allspark"],
        "review repo-local core.hooksPath if host global configuration differs",
    )
    for kind in ("AUTHOR", "COMMITTER"):
        identities = []
        for env in (host_env, agent_env):
            result = call(["git", "var", "GIT_" + kind + "_IDENT"], env=env)
            identities.append(
                result.stdout.strip().rsplit(" ", 2)[0] if result.returncode == 0 else None
            )
        check(
            "Git " + kind.lower() + " identity available and identical",
            bool(identities[0]) and identities[0] == identities[1],
            "configure reviewed repo-local identity if needed; values not printed",
        )
    signing = {}
    for label, env in (("host", host_env), ("Allspark", agent_env)):
        signing[label] = {}
        for key in (
            "commit.gpgsign",
            "gpg.format",
            "user.signingkey",
            "gpg.program",
            "gpg.ssh.program",
        ):
            result = call(["git", "config", "--get", key], env=env)
            signing[label][key] = result.stdout.strip() if result.returncode == 0 else None
    check(
        "same Git signing configuration in both homes",
        signing["host"] == signing["Allspark"],
        "preserve required signing; do not disable it to pass this check",
    )
    if signing["Allspark"].get("commit.gpgsign") in {"true", "yes", "on", "1"}:
        print(
            "PENDING signing readiness: verify access to the configured key/agent at the first real commit."
        )
    print(
        "INFO  Git remote authentication not tested; use a configured agent/helper, without copying auth into Git."
    )

    project = ROOT / ".project"
    state = project / "STATE.md"
    if not project.exists() and not project.is_symlink():
        print(
            "PENDING Path initialization: expected before bootstrap PR merge and clean origin baseline."
        )
        if args.require_path_state:
            check("Path state required", False)
    elif not state.is_file() or project.is_symlink() or state.is_symlink():
        check("Path ownership", False, "existing/orphan .project requires native classify/recovery")
    else:
        result = call([sys.executable, ROOT / "scripts/ai/path-run.py", "validate"])
        try:
            validation = json.loads(result.stdout)
            valid = (
                result.returncode == 0
                and isinstance(validation, dict)
                and validation.get("schema") == "gsd-path/state/v1"
                and validation.get("status") == "valid"
            )
        except ValueError:
            valid = False
        check("native Path state validation", valid, result.stderr.strip()[:240])
        if valid:
            result = call([sys.executable, ROOT / "scripts/ai/path-run.py", "status"])
            try:
                status = json.loads(result.stdout)
                typed = (
                    result.returncode == 0
                    and isinstance(status, dict)
                    and status.get("schema") == "gsd-path/status/v1"
                )
                check("native Path status", typed, result.stderr.strip()[:240])
                if typed:
                    action = status.get("route", {}).get("action")
                    print(
                        "INFO  Native route action: "
                        + str(action)
                        + " (follow native routing/recovery)"
                    )
                    if action == "block":
                        check("Path route unblocked", False)
            except (ValueError, AttributeError):
                check("native Path status", False, "invalid typed JSON")
    print(
        "No model call made. Phase dispatch, runtime tests, approval and cutover need separate evidence."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
