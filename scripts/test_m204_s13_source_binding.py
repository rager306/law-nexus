#!/usr/bin/env python3
"""Bounded subprocess tests for the S13 source-binding artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("m204_s13_source_binding.py")
ROOT = SCRIPT.parents[1]
SOURCE = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
FIXTURES = (
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/full-walk-001/diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/eligible-run-001/diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-s07-verification-battery.json",
)


def run(command: str, repo: Path, artifact: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), command, "--repo", str(repo), "--artifact", str(artifact)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    temp = tempfile.TemporaryDirectory(prefix="s13-binding-")
    repo = Path(temp.name)
    source = repo / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
    source.parent.mkdir(parents=True)
    shutil.copy2(SOURCE, source)
    for relative in FIXTURES:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    artifact = repo / "binding.json"
    return temp, repo, artifact


def test_compose_and_verify() -> None:
    temp, repo, artifact = fixture()
    try:
        composed = run("compose", repo, artifact)
        assert composed.returncode == 0, composed.stderr
        checked = run("verify", repo, artifact)
        assert checked.returncode == 0, checked.stderr
        assert "S13_T01_BINDING_OK" in checked.stdout
        value = json.loads(artifact.read_text(encoding="utf-8"))
        assert value["current"]["parser_source_sha256"] == digest(
            repo / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
        )
        assert len(value["historical_receipts"]) == 5
    finally:
        temp.cleanup()


def test_rejects_forged_current_and_historical_hash() -> None:
    temp, repo, artifact = fixture()
    try:
        assert run("compose", repo, artifact).returncode == 0
        value = json.loads(artifact.read_text(encoding="utf-8"))
        for section in ("current", "historical"):
            value[section]["parser_source_sha256"] = "sha256:" + "0" * 64
            artifact.write_text(json.dumps(value), encoding="utf-8")
            assert run("verify", repo, artifact).returncode != 0
            value = json.loads((repo / "binding.json").read_text(encoding="utf-8"))
            value[section]["parser_source_sha256"] = (
                digest(repo / "crates/ln-consultant-parser/src/contour_diagnostics.rs")
                if section == "current"
                else "sha256:e53a0961c8ecfaf8fcc133da1b37efcbca9dcbd41ffba28e842fa6d7de34d3a4"
            )
        artifact.write_text(json.dumps(value), encoding="utf-8")
    finally:
        temp.cleanup()


def test_rejects_revision_extra_pin_and_traversal() -> None:
    temp, repo, artifact = fixture()
    try:
        assert run("compose", repo, artifact).returncode == 0
        baseline = json.loads(artifact.read_text(encoding="utf-8"))
        cases = []
        revision = json.loads(json.dumps(baseline))
        revision["parser_revision"] = "forged-revision"
        cases.append(revision)
        extra = json.loads(json.dumps(baseline))
        extra["historical_receipts"].append(
            {"path": "extra", "sha256": "sha256:" + "0" * 64, "size_bytes": 0}
        )
        cases.append(extra)
        escaped = json.loads(json.dumps(baseline))
        escaped["historical_receipts"][0]["path"] = "../escape"
        cases.append(escaped)
        for value in cases:
            artifact.write_text(json.dumps(value), encoding="utf-8")
            assert run("verify", repo, artifact).returncode != 0
    finally:
        temp.cleanup()


if __name__ == "__main__":
    test_compose_and_verify()
    test_rejects_forged_current_and_historical_hash()
    test_rejects_revision_extra_pin_and_traversal()
    print("S13_T01_TESTS_OK")
