from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SENTINEL = ROOT / "law-source" / "consultant" / "runtime" / "gsd-ignore-smoke" / "sentinel.generated.json"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_runtime_generated_outputs_are_ignored_by_gitignore() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "law-source/consultant/runtime/" in gitignore

    RUNTIME_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_SENTINEL.write_text('{"generated": true}\n', encoding="utf-8")
    try:
        ignored = git("check-ignore", "law-source/consultant/runtime/gsd-ignore-smoke/sentinel.generated.json")
        assert ignored.returncode == 0, ignored.stderr
        status = git("status", "--short", "--untracked-files=all")
        assert "law-source/consultant/runtime/gsd-ignore-smoke/sentinel.generated.json" not in status.stdout
    finally:
        RUNTIME_SENTINEL.unlink(missing_ok=True)
        try:
            RUNTIME_SENTINEL.parent.rmdir()
        except OSError:
            pass


def test_source_proof_script_and_test_paths_remain_trackable() -> None:
    for path in [
        "law-source/consultant/44-FZ-2026.xml",
        "prd/research/source_structuring/19-runtime-tracking-policy-proof.md",
        "scripts/source_lifecycle.py",
        "tests/test_source_runtime_tracking_policy.py",
    ]:
        ignored = git("check-ignore", path)
        assert ignored.returncode == 1, f"{path} should remain trackable, got {ignored.stdout!r}"
