#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import m204_s12_failure_probe as probe


def sidecar_record(path: str, provider: str = "garant", failure_class: str = "decode") -> str:
    return json.dumps(
        {
            "record_kind": "failure",
            "schema": probe.SIDECAR_SCHEMA,
            "provider": provider,
            "path": path,
            "class": failure_class,
        }
    )


def test_sidecar_accepts_garant_and_rejects_extra_payload() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        source = repo / "law-source/garant/fail.odt"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"fixture")
        sidecar = repo / "failures.jsonl"
        sidecar.write_text(sidecar_record(str(source)) + "\n", encoding="utf-8")
        assert probe.validate_sidecar(sidecar, repo) == [
            {"provider": "garant", "path": "law-source/garant/fail.odt", "class": "decode"}
        ]
        sidecar.write_text(
            sidecar_record(str(source))[:-1] + ', "payload":"secret"}\n', encoding="utf-8"
        )
        try:
            probe.validate_sidecar(sidecar, repo)
        except ValueError as exc:
            assert "extra" in str(exc)
        else:
            raise AssertionError("payload-bearing sidecar was accepted")


def test_sidecar_rejects_traversal_and_provider_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        source = repo / "law-source/garant/fail.odt"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"fixture")
        sidecar = repo / "failures.jsonl"
        sidecar.write_text(sidecar_record(str(repo / "outside.odt")) + "\n", encoding="utf-8")
        try:
            probe.validate_sidecar(sidecar, repo)
        except (ValueError, FileNotFoundError):
            pass
        else:
            raise AssertionError("outside path was accepted")
        sidecar.write_text(
            sidecar_record(str(source), provider="consultant") + "\n", encoding="utf-8"
        )
        try:
            probe.validate_sidecar(sidecar, repo)
        except ValueError as exc:
            assert "binding" in str(exc)
        else:
            raise AssertionError("provider/path mismatch was accepted")


def test_aggregate_requires_exactly_one_record() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "diagnostics.jsonl"
        path.write_text(
            json.dumps({"record_kind": "aggregate", "failed": 1}) + "\n",
            encoding="utf-8",
        )
        assert probe.aggregate_failed(path) == 1
        path.write_text(
            json.dumps({"record_kind": "aggregate", "failed": 0})
            + "\n"
            + json.dumps({"record_kind": "aggregate", "failed": 1})
            + "\n",
            encoding="utf-8",
        )
        try:
            probe.aggregate_failed(path)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate aggregates were accepted")


def test_identity_is_supporting_only_and_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        attempt = repo / "prd/migration/rust-evidence/m204-s12-c4-attempts/a"
        attempt.mkdir(parents=True)
        for name in ("diagnostics.jsonl", "failures.jsonl", "attempt.json"):
            (attempt / name).write_text("{}\n", encoding="utf-8")
        value = {
            "schema": probe.SCHEMA,
            "provider": "garant",
            "path": "law-source/garant/fail.odt",
            "class": "decode",
            "sidecar_sha256": "sha256:" + "0" * 64,
            "attempt_id": "a",
            "attempt_provenance": {
                "diagnostics_path": str((attempt / "diagnostics.jsonl").relative_to(repo)),
                "failures_path": str((attempt / "failures.jsonl").relative_to(repo)),
                "metadata_path": str((attempt / "attempt.json").relative_to(repo)),
                "diagnostics_sha256": "sha256:" + "0" * 64,
                "failures_sha256": "sha256:" + "0" * 64,
            },
            "identity_status": "resolved",
            "s10_bytes_rewritten": False,
            "status_effect": "unchanged",
            "classification": "supporting-only",
            "marker": "S12_T02_FAILURE_IDENTITY_OK",
        }
        probe.validate_identity(value, repo)
        value["classification"] = "closure"
        try:
            probe.validate_identity(value, repo)
        except ValueError as exc:
            assert "supporting" in str(exc)
        else:
            raise AssertionError("closure classification was accepted")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
