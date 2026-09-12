from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import m204_s15_requirement_class as classifier


@pytest.fixture
def worktree_tmp():
    path = classifier.ROOT / "scripts" / ".m204_s15_t02_tmp"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


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


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("class_matched_ids",), ["R064"]),
        (("rows", 2, "class_matched"), True),
        (("rows", 2, "coverage_kind"), "class-matched"),
        (("c4_acceptance",), "pass"),
        (("status_effect",), "validated"),
        (("rows", 0, "status_effect"), "closed"),
        (("rows", 1, "status_effect"), "advanced"),
        (("rows", 0, "evidence_class"), "unknown-class"),
        (("rows", 8, "requirement_id"), "R035"),
    ],
)
def test_semantic_promotions_and_schema_drift_are_rejected(path, replacement) -> None:
    value = copy.deepcopy(classifier.classify())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(ValueError):
        classifier.validate(value)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("open_findings",), True),
        (("rows",), "not-a-list"),
        (("rows", 0, "source_surfaces"), []),
        (("rows", 0, "source_surfaces", 0, "sha256"), 7),
        (("rows", 0, "limitations"), "not-a-list"),
        (("predecessor_pins", "path"), 7),
    ],
)
def test_unknown_types_are_rejected(path, replacement) -> None:
    value = copy.deepcopy(classifier.classify())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(ValueError):
        classifier.validate(value)


def test_duplicate_missing_and_extra_rows_are_rejected() -> None:
    value = classifier.classify()
    duplicate = copy.deepcopy(value)
    duplicate["rows"][9] = copy.deepcopy(duplicate["rows"][8])
    missing = copy.deepcopy(value)
    missing["rows"].pop(3)
    extra = copy.deepcopy(value)
    extra["rows"].append(copy.deepcopy(extra["rows"][-1]))
    for forged in (duplicate, missing, extra):
        with pytest.raises(ValueError, match="rows"):
            classifier.validate(forged)


def test_reserved_rows_cannot_become_real_requirements() -> None:
    value = copy.deepcopy(classifier.classify())
    for row in value["rows"][-2:]:
        row["evidence_class"] = "canonical-owner-validation"
    with pytest.raises(ValueError):
        classifier.validate(value)


def test_affirmative_validation_claims_are_rejected_but_noun_is_allowed() -> None:
    value = copy.deepcopy(classifier.classify())
    value["rows"][0]["limitations"] = ["R038 validated"]
    with pytest.raises(ValueError, match="affirmative claim"):
        classifier.validate(value)
    value = copy.deepcopy(classifier.classify())
    value["rows"][0]["limitations"] = ["validation is not evidence of closure"]
    classifier.validate(value)


def test_duplicate_json_key_is_rejected(worktree_tmp: Path) -> None:
    path = worktree_tmp / "duplicate.json"
    path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        classifier.load(path)


def test_compose_and_check_are_idempotent(worktree_tmp: Path) -> None:
    out = worktree_tmp / "s15.json"
    first = run("compose", "--out", str(out))
    first_bytes = out.read_bytes()
    second = run("compose", "--out", str(out))
    second_bytes = out.read_bytes()
    checked = run("check", "--out", str(out))
    assert first.returncode == second.returncode == checked.returncode == 0
    assert first_bytes == second_bytes


def test_unsafe_source_paths_rejected(worktree_tmp: Path) -> None:
    for path in (
        "../escape.json",
        "/tmp/escape.json",
        "a\\b.json",
        ".gsd/secret.json",
        ".git/config",
        ".planning/secret.json",
        ".audits/secret.json",
    ):
        with pytest.raises(ValueError):
            classifier.safe_source(path)
    outside = worktree_tmp / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    symlink = worktree_tmp / "link.json"
    symlink.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        classifier.safe_source(str(symlink.relative_to(classifier.ROOT)))
    parent = worktree_tmp / "parent"
    parent.mkdir()
    (parent / "file.json").write_text("{}", encoding="utf-8")
    parent_link = worktree_tmp / "parent-link"
    parent_link.symlink_to(parent, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        classifier.safe_source(str((parent_link / "file.json").relative_to(classifier.ROOT)))


def test_s10_missing_status_effect_is_required_semantics(monkeypatch) -> None:
    live_load = classifier.load
    docs = {name: live_load(path) for name, path in classifier.SOURCES.items()}
    docs["s10"]["rows"][0]["status_effect"] = "unchanged"

    def fake_load(path):
        for name, source in classifier.SOURCES.items():
            if path == source:
                return docs[name]
        return live_load(path)

    monkeypatch.setattr(classifier, "load", fake_load)
    with pytest.raises(ValueError, match="S10 unexpectedly invents"):
        classifier.historical()


def test_s14_subprocess_failures_are_fail_closed(monkeypatch) -> None:
    class Completed:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def invoke_failure(*args, **kwargs):
        return Completed(returncode=9, stderr="controlled S14 failure")

    monkeypatch.setattr(classifier.subprocess, "run", invoke_failure)
    with pytest.raises(ValueError, match="S14 classify failed"):
        classifier.verify_s14()

    def invoke_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=20)

    monkeypatch.setattr(classifier.subprocess, "run", invoke_timeout)
    with pytest.raises(ValueError, match="timed out"):
        classifier.verify_s14()

    def invoke_invalid(*args, **kwargs):
        return Completed(stdout="not-json")

    monkeypatch.setattr(classifier.subprocess, "run", invoke_invalid)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        classifier.verify_s14()

    def invoke_forged(*args, **kwargs):
        return Completed(
            stdout=json.dumps(
                {"integrity": "pass", "c4_acceptance": "pass", "classification": "supporting-only"}
            )
        )

    monkeypatch.setattr(classifier.subprocess, "run", invoke_forged)
    with pytest.raises(ValueError, match="polarity mismatch"):
        classifier.verify_s14()


def test_cli_failures_have_nonzero_and_stderr(worktree_tmp: Path) -> None:
    missing = run("check", "--out", str(worktree_tmp / "missing.json"))
    assert missing.returncode != 0
    assert "m204_s15_requirement_class:" in missing.stderr
    invalid = worktree_tmp / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    result = run("check", "--out", str(invalid))
    assert result.returncode != 0
    assert "expected object" in result.stderr
    out = worktree_tmp / "artifact.json"
    assert run("compose", "--out", str(out)).returncode == 0
    out.write_text(out.read_text(encoding="utf-8") + "tamper", encoding="utf-8")
    refused = run("compose", "--out", str(out))
    assert refused.returncode != 0
    assert "refusing to overwrite" in refused.stderr


def test_s07_wrong_predecessor_hash_is_rejected(monkeypatch) -> None:
    live_load = classifier.load
    docs = {name: live_load(path) for name, path in classifier.SOURCES.items()}
    docs["s07"]["predecessor"]["sha256"] = "sha256:forged"

    def fake_load(path):
        for name, source in classifier.SOURCES.items():
            if path == source:
                return docs[name]
        return live_load(path)

    monkeypatch.setattr(classifier, "load", fake_load)
    with pytest.raises(ValueError, match="predecessor hash"):
        classifier.historical()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
