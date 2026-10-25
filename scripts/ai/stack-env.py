#!/usr/bin/env python3
"""Shared, repository-owned environment for Allspark and native Path helpers.

This is starter glue, not an Allspark or GSD Path API. It never copies auth,
changes Git configuration, creates a worktree, or writes a placement receipt.
Import ``build_env`` for a child process. ``--shell`` leaves the shell HOME alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

MANAGED_KEYS = (
    "AI_STACK_ROOT",
    "AI_STACK_HOST_HOME",
    "ALLSPARK_HOME",
    "AI_STACK_PATH_WORKSPACE",
    "AI_STACK_PATH_WORKTREE_ROOT_SOURCE",
    "GSD_PATH_WORKTREE_ROOT",
    "PRIME_AGENT_CODING_AGENT_DIR",
    "PRIME_AGENT_SESSION_DIR",
    "PRIME_AGENT_KERNEL_VENV",
    "PRIME_AGENT_DAEMON_SOCKET",
    "PI_PACKAGE_DIR",
    "PI_SKIP_VERSION_CHECK",
    "DO_NOT_TRACK",
    "UV_CACHE_DIR",
    "UV_PYTHON_INSTALL_DIR",
    "UV_PYTHON_BIN_DIR",
    "npm_config_cache",
    "npm_config_update_notifier",
    "PYTHONDONTWRITEBYTECODE",
    "CARGO_HOME",
    "RUSTUP_HOME",
    "PATH",
)
# The interactive shell receives only general project tooling. Upstream Prime
# must not inherit a fork profile or runtime just because env.sh was sourced.
# Existing upstream variables in that shell are left untouched; build_env
# supplies the fork-specific overrides only to this stack's child processes.
SHELL_KEYS = tuple(
    key
    for key in MANAGED_KEYS
    if not key.startswith("PRIME_AGENT_")
    and key not in {"PI_PACKAGE_DIR", "PI_SKIP_VERSION_CHECK", "DO_NOT_TRACK"}
)


def git(directory: Path, *arguments: str, env: dict | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode:
        raise ValueError(f"cannot inspect Git checkout {directory}: {result.stderr.strip()}")
    return result.stdout.rstrip("\n")


def common_dir(directory: Path, env: dict | None = None) -> Path:
    return Path(
        git(directory, "rev-parse", "--path-format=absolute", "--git-common-dir", env=env)
    ).resolve()


def canonical_root(script_root: Path, env: dict | None = None) -> Path:
    """Resolve the primary checkout; an override must share its Git common dir.

    A script copied into a linked worktree can find the ordinary primary
    checkout through its common .git directory. Nonstandard/bare layouts must
    supply AI_STACK_ROOT explicitly instead of guessing another checkout.
    """
    source = os.environ if env is None else env
    anchor = Path(script_root).resolve()
    common = common_dir(anchor, dict(source))
    override = source.get("AI_STACK_ROOT")
    if override:
        root = Path(override)
        if not root.is_absolute():
            raise ValueError("AI_STACK_ROOT must be an absolute primary-checkout path")
        root = root.resolve()
    elif common.name == ".git" and (common.parent / ".ai/versions.json").is_file():
        root = common.parent
    else:
        root = anchor
    if common_dir(root, dict(source)) != common:
        raise ValueError("AI_STACK_ROOT and this script must share a Git common directory")
    top = Path(git(root, "rev-parse", "--show-toplevel", env=dict(source))).resolve()
    if top != root or not (root / ".ai/versions.json").is_file():
        raise ValueError("AI_STACK_ROOT must be the prepared primary checkout root")
    return root


def checkout_roots(root: Path, env: dict | None = None) -> list[Path]:
    output = git(root, "worktree", "list", "--porcelain", "-z", env=env)
    return [
        Path(field[len("worktree ") :]).resolve()
        for field in output.split("\0")
        if field.startswith("worktree ")
    ]


def outside_worktrees(path: Path, root: Path, env: dict | None = None) -> None:
    for checkout in checkout_roots(root, env):
        if path.is_relative_to(checkout):
            raise ValueError(
                f"GSD Path worktree storage must be outside all repository worktrees: {path}"
            )


def placement(root: Path, env: dict) -> tuple[Path, Path, str]:
    """Select external storage without changing an existing native placement pin."""
    common = common_dir(root, env)
    common_id = hashlib.sha256(os.fsencode(common)).hexdigest()
    root_id = hashlib.sha256(os.fsencode(root)).hexdigest()
    specified = env.get("GSD_PATH_WORKTREE_ROOT")
    desired = Path(specified) if specified else root.parent / (root.name + "-path-worktrees")
    if not desired.is_absolute():
        raise ValueError("GSD_PATH_WORKTREE_ROOT must be absolute (do not use a literal ~)")
    desired = desired.resolve()
    receipt = common / "gsd-path/workspaces" / (root_id + ".json")
    if receipt.exists() or receipt.is_symlink():
        if receipt.is_symlink() or not receipt.is_file():
            raise ValueError(f"native Path placement receipt is not a regular file: {receipt}")
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"invalid native Path placement receipt: {receipt}") from error
        if (
            not isinstance(data, dict)
            or data.get("primary") != str(root)
            or not isinstance(data.get("root"), str)
            or not Path(data["root"]).is_absolute()
        ):
            raise ValueError(f"invalid native Path placement receipt: {receipt}")
        workspace = Path(data["root"]).resolve()
        if workspace.name != root_id or workspace.parent.name != common_id:
            raise ValueError(
                "existing Path placement uses an unexpected layout; inspect native recovery before changing it"
            )
        recorded = workspace.parent.parent
        if specified and desired != recorded:
            raise ValueError(
                f"GSD_PATH_WORKTREE_ROOT conflicts with native placement {recorded}; do not move active worktrees manually"
            )
        outside_worktrees(recorded, root, env)
        outside_worktrees(workspace, root, env)
        return recorded, workspace, "native-receipt"
    outside_worktrees(desired, root, env)
    return desired, desired / common_id / root_id, "environment" if specified else "starter-default"


def absolute_setting(value: str, label: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute so linked worktrees use the same tools")
    return str(path.resolve())


def _existing_toolchain_home(label: str, preferred: str) -> str:
    """Resolve a Rust home directory that actually carries a toolchain.

    An isolated fork HOME is a fresh profile whose ``.cargo``/``.rustup``
    directories may exist but hold no toolchain, and a session started from a
    nonstandard HOME inherits the same gap. Pointing a child at such a shell
    breaks every cargo/rustup call ("no default toolchain"), so fall back to
    a home that really has one (toolchains dir with entries, or a cargo
    binary). Explicit env values that already carry a toolchain always win;
    otherwise the computed path is kept so the failure stays explicit.
    """

    def _carries_toolchain(home: str) -> bool:
        root = Path(home)
        if not root.is_dir():
            return False
        if label == "RUSTUP_HOME":
            chains = root / "toolchains"
            settings = root / "settings.toml"
            return chains.is_dir() and any(chains.iterdir()) and settings.is_file()
        return (root / "bin" / "cargo").is_file()

    candidates = [preferred]
    fallback = "/root/.rustup" if label == "RUSTUP_HOME" else "/root/.cargo"
    if fallback != preferred:
        candidates.append(fallback)
    home_cargo = str(Path.home() / ".cargo")
    home_rustup = home_cargo.replace(".cargo", ".rustup")
    candidates.append(home_rustup if label == "RUSTUP_HOME" else home_cargo)
    for candidate in dict.fromkeys(candidates):
        if _carries_toolchain(candidate):
            return candidate
    return preferred


def build_env(root: Path, env: dict | None = None, *, isolated: bool = True) -> dict:
    """Return a subprocess environment; only isolated=True changes its HOME.

    For host-cache restoration invoked from an Allspark session, the caller
    explicitly sets its child env HOME to AI_STACK_HOST_HOME. This function
    never mutates os.environ or the interactive shell.
    """
    result = dict(os.environ if env is None else env)
    root = canonical_root(root, result)
    local = root / ".ai/local"
    isolated_home = local / "allspark-home"
    host_value = result.get("AI_STACK_HOST_HOME") or result.get("HOME")
    if not host_value:
        raise ValueError("HOME is unavailable; start the stack from the operator's normal shell")
    host_home = Path(absolute_setting(host_value, "AI_STACK_HOST_HOME"))
    if host_home == isolated_home.resolve():
        raise ValueError(
            "original host home is unknown; start from the normal shell before entering Allspark"
        )
    storage, workspace, source = placement(root, result)
    profile = isolated_home / ".prime/agent"
    # Unix socket paths have a small platform limit. Do not put the socket in
    # a potentially long checkout path, or share the fork's default socket.
    socket_id = hashlib.sha256(os.fsencode(root)).hexdigest()[:16]
    socket = Path("/tmp") / f"allspark-{os.getuid()}-{socket_id}.sock"
    cargo = _existing_toolchain_home(
        "CARGO_HOME",
        absolute_setting(result.get("CARGO_HOME") or str(host_home / ".cargo"), "CARGO_HOME"),
    )
    rustup = _existing_toolchain_home(
        "RUSTUP_HOME",
        absolute_setting(result.get("RUSTUP_HOME") or str(host_home / ".rustup"), "RUSTUP_HOME"),
    )
    path_entries = [str(local / "node/bin"), str(local / "tools/bin"), str(Path(cargo) / "bin")]
    path_entries.extend(result.get("PATH", "").split(os.pathsep))
    result.update(
        {
            "AI_STACK_ROOT": str(root),
            "AI_STACK_HOST_HOME": str(host_home),
            "ALLSPARK_HOME": str(isolated_home),
            "AI_STACK_PATH_WORKSPACE": str(workspace),
            "AI_STACK_PATH_WORKTREE_ROOT_SOURCE": source,
            "GSD_PATH_WORKTREE_ROOT": str(storage),
            "PRIME_AGENT_CODING_AGENT_DIR": str(profile),
            "PRIME_AGENT_SESSION_DIR": str(profile / "sessions"),
            "PRIME_AGENT_KERNEL_VENV": str(local / "kernel-venv"),
            "PRIME_AGENT_DAEMON_SOCKET": str(socket),
            "PI_PACKAGE_DIR": str(local / "allspark-source"),
            "PI_SKIP_VERSION_CHECK": "1",
            "DO_NOT_TRACK": "1",
            "UV_CACHE_DIR": str(local / "uv-cache"),
            "UV_PYTHON_INSTALL_DIR": str(local / "uv-python"),
            "UV_PYTHON_BIN_DIR": str(local / "tools/bin"),
            "npm_config_cache": str(local / "npm-cache"),
            "npm_config_update_notifier": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CARGO_HOME": cargo,
            "RUSTUP_HOME": rustup,
            "PATH": os.pathsep.join(dict.fromkeys(entry for entry in path_entries if entry)),
        }
    )
    result.pop("PRIME_AGENT_KERNEL_PYTHON", None)
    if isolated:
        result["HOME"] = str(isolated_home)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--shell", action="store_true", help="export only managed variables; never export HOME"
    )
    parser.add_argument(
        "--isolated", action="store_true", help="show the isolated child environment in JSON"
    )
    args = parser.parse_args()
    try:
        env = build_env(args.root, isolated=args.isolated)
        if args.shell:
            for key in SHELL_KEYS:
                print(f"export {key}={shlex.quote(env[key])}")
        else:
            print(json.dumps({key: env[key] for key in (*MANAGED_KEYS, "HOME")}, indent=2))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"stack-env: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
