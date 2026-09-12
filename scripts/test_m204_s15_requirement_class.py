from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import m204_s15_requirement_class as classifier


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(Path(__file__).with_name("m204_s15_requirement_class.py")), *args],
        cwd=classifier.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_live_classify_is_empty_class_match() -> None:
    result = run("classify")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "class_matched_ids": [],
        "status_effect": "unchanged",
    }


def test_forged_promotion_is_rejected() -> None:
    value = classifier.classify()
    forged = copy.deepcopy(value)
    forged["class_matched_ids"] = ["R064"]
    forged["rows"][2]["class_matched"] = True
    with pytest.raises(ValueError):
        classifier.validate(forged)


def test_duplicate_json_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        classifier.load(path)


def test_compose_and_check_are_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "s15.json"
    first = run("compose", "--out", str(out))
    second = run("compose", "--out", str(out))
    checked = run("check", "--out", str(out))
    assert first.returncode == second.returncode == checked.returncode == 0
    assert out.read_bytes() == out.read_bytes()


def test_unsafe_source_paths_rejected() -> None:
    for path in (
        "../escape.json",
        "/tmp/escape.json",
        "a\\b.json",
        ".gsd/secret.json",
        ".git/config",
    ):
        with pytest.raises(ValueError):
            classifier.safe_source(path)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
