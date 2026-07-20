#!/usr/bin/env python3
"""Verify the repository pre-commit hook is standard and cannot mutate .lex."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSITION = ROOT / "prd/migration/decommission/pre-commit-hook-transition.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lex_fingerprint(root: Path) -> str:
    lex = root / ".lex"
    digest = hashlib.sha256()
    if not lex.exists():
        return "absent"
    for path in sorted(item for item in lex.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def inspect_hook(root: Path) -> dict[str, object]:
    hook = root / ".git/hooks/pre-commit"
    if not hook.exists():
        return {"exists": False, "owner": "missing", "errors": ["hook_missing"]}
    data = hook.read_bytes()
    text = data.decode("utf-8", errors="replace")
    has_git_lex = "git-lex" in text or "git lex" in text
    has_pre_commit = "pre_commit" in text or "pre-commit" in text
    owner = (
        "pre-commit"
        if has_pre_commit and not has_git_lex
        else "git-lex"
        if has_git_lex
        else "unknown"
    )
    errors: list[str] = []
    if owner != "pre-commit":
        errors.append("hook_not_standard_pre_commit")
    if has_git_lex:
        errors.append("git_lex_invocation_present")
    if not hook.stat().st_mode & 0o111:
        errors.append("hook_not_executable")
    legacy_hook = hook.with_name("pre-commit.legacy")
    if legacy_hook.exists():
        errors.append("legacy_hook_present")
    return {
        "exists": True,
        "owner": owner,
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "contains_git_lex": has_git_lex,
        "contains_pre_commit": has_pre_commit,
        "legacy_hook_present": legacy_hook.exists(),
        "errors": errors,
    }


def verify_transition(root: Path, hook: dict[str, object]) -> list[str]:
    path = root / TRANSITION.relative_to(ROOT)
    if not path.exists():
        return ["transition_record_missing"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = payload.get("new_hook", {})
    if hook.get("sha256") != expected.get("sha256"):
        errors.append("hook_sha256_drift")
    if expected.get("contains_git_lex") is not False:
        errors.append("transition_record_allows_git_lex")
    if payload.get("external_repository_mutated") is not False:
        errors.append("external_repository_mutation_not_forbidden")
    return errors


def run_hook(root: Path, timeout: float) -> dict[str, object]:
    hook = root / ".git/hooks/pre-commit"
    before = lex_fingerprint(root)
    start = time.monotonic()
    try:
        completed = subprocess.run(
            [str(hook)],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = {
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "exit_code": None,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    after = lex_fingerprint(root)
    result.update(
        {
            "duration_ms": round((time.monotonic() - start) * 1000),
            "lex_before": before,
            "lex_after": after,
            "lex_unchanged": before == after,
        }
    )
    return result


def verify(
    root: Path = ROOT, *, execute: bool = False, timeout: float = 120.0
) -> dict[str, object]:
    hook = inspect_hook(root)
    errors = list(hook.get("errors", []))
    errors.extend(verify_transition(root, hook))
    execution: dict[str, object] | None = None
    if execute and not errors:
        execution = run_hook(root, timeout)
        if execution["timed_out"]:
            errors.append("hook_timeout")
        elif execution["exit_code"] != 0:
            errors.append("hook_failed")
        if not execution["lex_unchanged"]:
            errors.append("lex_mutated")
    return {
        "status": "pass" if not errors else "fail",
        "phase": "repository_pre_commit_hook",
        "hook": hook,
        "execution": execution,
        "errors": errors,
        "recovery": "uv run pre-commit install --install-hooks --overwrite",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", action="store_true", help="execute the installed hook and prove .lex is unchanged"
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    payload = verify(execute=args.run, timeout=args.timeout)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
