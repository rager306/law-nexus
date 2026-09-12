#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import m204_s12_hard_block as hard_block


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_actual_carrier_is_closed_and_resolved() -> None:
    repo = Path.cwd()
    value = read_json(repo / "prd/migration/rust-evidence/m204-s12-validate-hard-block.json")
    hard_block.verify_record(value, repo)
    assert value["abort_message"] == hard_block.ABORT_MESSAGE
    assert value["s12_called_validate_milestone"] is False
    assert value["classification"] == "supporting-only"


def test_forged_status_and_auto_closure_are_rejected() -> None:
    repo = Path.cwd()
    value = read_json(repo / "prd/migration/rust-evidence/m204-s12-validate-hard-block.json")
    for key, forged in (
        ("s12_called_validate_milestone", True),
        ("findings", []),
        ("status_effect", "closed"),
    ):
        candidate = copy.deepcopy(value)
        candidate[key] = forged
        try:
            hard_block.verify_record(candidate, repo)
        except ValueError:
            pass
        else:
            raise AssertionError(f"forged {key} was accepted")


def test_tampered_pin_and_manifest_path_escape_are_rejected() -> None:
    repo = Path.cwd()
    value = read_json(repo / "prd/migration/rust-evidence/m204-s12-validate-hard-block.json")
    manifest = read_json(repo / value["frozen_manifest"])
    tampered = copy.deepcopy(manifest)
    tampered["files"][0]["sha256"] = "sha256:" + "0" * 64
    try:
        hard_block.verify_manifest(tampered, repo)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered frozen pin was accepted")
    escaped = copy.deepcopy(value)
    escaped["frozen_manifest"] = "../outside.json"
    try:
        hard_block.verify_record(escaped, repo)
    except ValueError:
        pass
    else:
        raise AssertionError("manifest path escape was accepted")


def test_identity_source_mismatch_is_rejected_in_isolated_copy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / hard_block.IDENTITY).parent.mkdir(parents=True)
        identity = read_json(Path.cwd() / hard_block.IDENTITY)
        identity["identity_status"] = "unresolved"
        (root / hard_block.IDENTITY).write_text(json.dumps(identity), encoding="utf-8")
        try:
            hard_block.load_identity(root)
        except (ValueError, FileNotFoundError):
            pass
        else:
            raise AssertionError("unresolved identity was accepted")


def test_composer_does_not_call_validate_or_read_gsd() -> None:
    source = Path.cwd() / "scripts/m204_s12_hard_block.py"
    text = source.read_text(encoding="utf-8")
    assert "gsd_validate_milestone" not in text
    assert "sqlite" not in text.lower()


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
