from __future__ import annotations

import json
import subprocess

import pytest

import m204_s15_evidence_verify as verifier


def test_live_manifest_and_result_are_bounded() -> None:
    verifier.verify()


def test_unsafe_paths_and_symlinks_are_rejected(tmp_path) -> None:
    for value in (
        "../escape.json",
        "/tmp/escape.json",
        "a\\b.json",
        ".git/config",
        ".gsd/secret.json",
        ".planning/secret.json",
        ".audits/secret.json",
    ):
        with pytest.raises(ValueError):
            verifier.safe_source(value)
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        verifier.safe_source(str(link.relative_to(verifier.ROOT)))


def test_run_json_rejects_dependency_failure_timeout_and_non_strict_output(monkeypatch) -> None:
    class Completed:
        returncode = 7
        stdout = ""
        stderr = "dependency failed"

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Completed())
    with pytest.raises(ValueError, match="failed"):
        verifier.run_json(["fake"], "dependency")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    monkeypatch.setattr(verifier.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out"):
        verifier.run_json(["fake"], "dependency")

    class Invalid:
        returncode = 0
        stdout = "not-json"
        stderr = ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Invalid())
    with pytest.raises(ValueError, match="invalid JSON"):
        verifier.run_json(["fake"], "dependency")


def test_run_json_rejects_stderr_and_forged_polarity(monkeypatch) -> None:
    class Noisy:
        returncode = 0
        stdout = json.dumps(verifier.S14_RESULT)
        stderr = "warning"

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Noisy())
    with pytest.raises(ValueError, match="strict JSON"):
        verifier.run_json(["fake"], "consumer")

    class Forged:
        returncode = 0
        stdout = json.dumps({"integrity": "pass", "c4_acceptance": "pass"})
        stderr = ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Forged())
    result = verifier.run_json(["fake"], "consumer")
    assert result["c4_acceptance"] == "pass"
    assert result != verifier.S14_RESULT


def test_marker_runner_rejects_nonzero_missing_marker_and_timeout(monkeypatch) -> None:
    class Failed:
        returncode = 1
        stdout = ""
        stderr = "controlled failure"

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Failed())
    with pytest.raises(ValueError, match="failed"):
        verifier.run_marker(["fake"], "MARKER", "host")

    class Missing:
        returncode = 0
        stdout = "other\n"
        stderr = ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: Missing())
    with pytest.raises(ValueError, match="missing marker"):
        verifier.run_marker(["fake"], "MARKER", "host")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    monkeypatch.setattr(verifier.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out"):
        verifier.run_marker(["fake"], "MARKER", "host")


def test_s14_manifest_rejects_missing_extra_or_tampered_entry(monkeypatch) -> None:
    original = verifier.load(verifier.S14_MANIFEST)
    for mutation in (
        {**original, "files": original["files"][:-1]},
        {**original, "files": [*original["files"], original["files"][0]]},
    ):
        monkeypatch.setattr(verifier, "load", lambda path, value=mutation: value)
        with pytest.raises(ValueError, match="source drift|closed|required pin set is incomplete"):
            verifier.verify_s14_manifest()

    tampered = json.loads(json.dumps(original))
    tampered["files"][0]["sha256"] = "sha256:forged"
    monkeypatch.setattr(verifier, "load", lambda path: tampered)
    with pytest.raises(ValueError, match="source drift"):
        verifier.verify_s14_manifest()


def test_artifact_cannot_promote_class_match(monkeypatch) -> None:
    live_load = verifier.load
    artifact = live_load(verifier.S15_ARTIFACT)
    artifact["class_matched_ids"] = ["R064"]

    def fake_load(path):
        return artifact if path == verifier.S15_ARTIFACT else live_load(path)

    monkeypatch.setattr(verifier, "load", fake_load)
    with pytest.raises(ValueError, match="class-matched"):
        verifier.verify()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
