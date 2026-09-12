#!/usr/bin/env python3
"""Fail-closed tests for the S08 engine hasher replica."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "m204_s08_source_revision.mjs"
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
ENGINE_REV = re.compile(r"^sha256:[0-9a-f]{64}$")


def capture() -> dict:
    proc = subprocess.run(
        ["node", str(HELPER)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"hasher exit {proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    if payload.get("ok") is not True:
        raise AssertionError(f"hasher non-ok payload: {payload}")
    return payload


def test_helper_prints_engine_sha256_not_git_sha() -> None:
    payload = capture()
    revision = payload["source_revision"]
    assert ENGINE_REV.fullmatch(revision), revision
    assert not GIT_SHA.fullmatch(revision), revision
    assert not GIT_SHA.fullmatch(revision.removeprefix("sha256:")), revision


def test_two_captures_on_unchanged_tree_are_equal() -> None:
    first = capture()["source_revision"]
    second = capture()["source_revision"]
    assert first == second


if __name__ == "__main__":
    test_helper_prints_engine_sha256_not_git_sha()
    test_two_captures_on_unchanged_tree_are_equal()
    print("S08_SOURCE_REVISION_TESTS_OK")
