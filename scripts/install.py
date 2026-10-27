#!/usr/bin/env python3
"""Restore the pinned GSD Path runtime from the vendored release tree.

The pinned runtime is machine-local by design, so a fresh checkout restores it
from the tracked vendored archive instead of npm. Verification and publication
reuse the pinned release's own algorithm (GSD Path 1.6.2
``runtime_store.source_manifest`` plus ``status_runtime.manifest_digest`` and
``validate_runtime``): the digest covers exactly the release runtime inventory
below, hashed per file and folded into one sha256 over the sorted JSON
manifest.

Documented bootstrap:

    tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>
    python3 <temporary-dir>/gsd-path/scripts/install.py \
        --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path

Exit 0: the pinned runtime is installed or reused idempotently. Non-zero: a
loud failure carrying the recorded version+digest pair.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

RUNTIME_SCHEMA = "gsd-path/runtime/v1"
DECLARATION_PATH = ".gsd-path/runtime.json"

# Verbatim runtime inventory of the pinned release; the manifest digest covers
# exactly these files plus status_runtime.py.
RUNTIME_FILES = (
    "pipeline_state.py",
    "roadmap.py",
    "check_handoffs.py",
    "check_task_briefs.py",
    "isolation.py",
    "discussion_records.py",
    "pipeline_git.py",
    "promote_lookahead.py",
    "detect_project.py",
    "pipeline_diagnose.py",
    "pipeline_undo.py",
    "archive_milestone.py",
    "review_panel.py",
    "_common.py",
    "worktree_paths.py",
    "build_recovery.py",
    "state_checkpoint.py",
    "state_promote.py",
    "discussion_validate.py",
    "integration.py",
    "build_state.py",
    "lean_verification.py",
    "check_docs_audit.py",
    "path_config.py",
    "model_policy.py",
    "loop_run.py",
    "members.py",
    "review_findings.py",
    "task_context.py",
)
GUARDS = ("guard_hook.py", "git_guard.py")


def manifest_digest(manifest: dict) -> str:
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_manifest(source: Path) -> tuple[dict, dict]:
    version = json.loads((source / "package.json").read_text(encoding="utf-8"))["version"]
    files = {}
    for name in (*RUNTIME_FILES, *GUARDS, "status_runtime.py"):
        path = source / "scripts" / name
        if path.is_symlink():
            raise ValueError(f"symlinked runtime source: {path}")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"version": version, "files": files}
    pin = {"schema": RUNTIME_SCHEMA, "version": version, "digest": manifest_digest(manifest)}
    return manifest, pin


def runtime_home() -> Path:
    return Path.home() / ".gsd-path" / "runtimes"


def declaration(project: Path) -> dict:
    path = project / DECLARATION_PATH
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError(f"unsafe runtime declaration: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("schema") != RUNTIME_SCHEMA
        or not isinstance(data.get("version"), str)
        or not isinstance(data.get("digest"), str)
        or len(data["digest"]) != 64
        or any(char not in "0123456789abcdef" for char in data["digest"])
    ):
        raise ValueError(f"invalid runtime declaration: {path}")
    return data


def validate_runtime(data: dict) -> Path:
    root = runtime_home() / str(data["digest"])
    hint = (
        f"Runtime {data['version']} ({data['digest']}) is unavailable or invalid at {root}; "
        "restore it from the vendored archive (.ai/vendor/gsd-path-1.6.2.tgz)"
    )
    try:
        if any(path.is_symlink() for path in (root, root.parent, root.parent.parent)):
            raise ValueError("symlinked runtime storage")
        manifest_path = root / "manifest.json"
        if manifest_path.is_symlink():
            raise ValueError("symlinked manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or manifest_digest(manifest) != data["digest"]
            or manifest.get("version") != data["version"]
        ):
            raise ValueError("manifest identity mismatch")
        files = manifest.get("files")
        if not isinstance(files, dict) or "pipeline_state.py" not in files:
            raise ValueError("invalid runtime file inventory")
        for name, expected in files.items():
            if Path(name).name != name or not name.endswith(".py"):
                raise ValueError("invalid runtime file name")
            path = root / str(name)
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"runtime file changed: {name}")
        entries = set()
        for path in root.iterdir():
            if path.name == "__pycache__":
                if not stat.S_ISDIR(path.lstat().st_mode):
                    raise ValueError("unexpected runtime files")
                for cached in path.iterdir():
                    if cached.suffix != ".pyc" or not stat.S_ISREG(cached.lstat().st_mode):
                        raise ValueError("unexpected runtime files")
                continue
            entries.add(path.name)
        if entries != set(files) | {"manifest.json"}:
            raise ValueError("unexpected runtime files")
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(hint + f" ({error})") from error
    return root


def publish(source: Path, expected: dict, *, dry_run: bool) -> dict:
    manifest, pin = source_manifest(source)
    if any(pin[key] != expected.get(key) for key in pin):
        raise ValueError(
            f"source does not match declared runtime {expected['version']} "
            f"({expected['digest']}); use its matching package"
        )
    if dry_run:
        return pin
    parent = runtime_home()
    if any(path.is_symlink() for path in (parent, parent.parent)):
        raise ValueError(f"unsafe runtime storage: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / str(pin["digest"])
    if destination.is_symlink():
        raise ValueError(f"unsafe runtime storage: {destination}")
    if destination.exists():
        try:
            validate_runtime(pin)
            return pin
        except ValueError:
            pass  # --runtime-restore repairs an invalid store.
    with tempfile.TemporaryDirectory(prefix=".runtime-stage-", dir=parent) as temporary:
        staging = Path(temporary) / "runtime"
        staging.mkdir()
        for name, digest in manifest["files"].items():
            shutil.copyfile(source / "scripts" / name, staging / name)
            if hashlib.sha256((staging / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"runtime source changed while installing: {name}")
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if destination.exists():
            previous = Path(temporary) / "previous"
            destination.rename(previous)
            try:
                staging.rename(destination)
            except OSError:
                previous.rename(destination)
                raise
        else:
            staging.rename(destination)
    validate_runtime(pin)
    return pin


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _validate_project_git_root(project: Path) -> None:
    probe = project
    while not probe.exists():
        probe = probe.parent
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=probe,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    top_level = result.stdout.strip()
    if result.returncode == 0 and top_level and not _same_path(Path(top_level), project):
        raise ValueError(f"project path is not the Git worktree root: {project}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-restore", action="store_true")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)
    if not arguments.runtime_restore:
        parser.error("only --runtime-restore is supported")
    project = Path(os.path.abspath(os.fspath(arguments.project.expanduser())))
    source_root = Path(os.path.abspath(os.fspath(arguments.source_root.expanduser())))
    try:
        _validate_project_git_root(project)
        pin = publish(source_root, declaration(project), dry_run=arguments.dry_run)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    suffix = " (dry run)" if arguments.dry_run else ""
    print(f"runtime: restore {pin['version']} ({pin['digest']}){suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
