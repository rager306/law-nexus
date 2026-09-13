#!/usr/bin/env python3
"""Bounded fixture proof for the versioned S23 C4 receipt seam."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/m204_s23_c4_run.py"
S10_RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
BINARY = ROOT / "target/debug/npa-contour-diagnostics"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"
PARSER = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def make_receipt(work: Path, diagnostics_text: str, *, duration: int = 0) -> Path:
    diagnostics = work / "prd/migration/rust-evidence/m204-s23-fixture-diagnostics.jsonl"
    diagnostics.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.write_text(diagnostics_text, encoding="utf-8")
    # Use the runner's real subprocess shape, but keep the fixture receipt synthetic and
    # local: all source/binary pins still get checked by the production verifier.
    import hashlib

    def digest(path: Path) -> str:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    inventory = "sha256:" + "a" * 64
    stdout = work / "prd/migration/rust-evidence/m204-s23-fixture-stdout.log"
    stderr = work / "prd/migration/rust-evidence/m204-s23-fixture-stderr.log"
    stdout.write_text("", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    argv = [
        str(BINARY),
        "--root",
        str(ROOT / "consru_export/consru_export/exports"),
        "--garant-root",
        str(ROOT / "law-source/garant"),
        "--profile",
        "contour",
        "--jobs",
        "1",
        "--acceptance-contract",
        str(CONTRACT),
        "--source-revision",
        "fixture",
        "--out",
        str(diagnostics),
    ]
    argv_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(argv, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    )
    receipt = {
        "schema": "m204-s23-c4-operational-receipt/v1",
        "attempt_id": "fixture",
        "immutable_attempt_identity": {"attempt_id": "fixture", "argv_sha256": argv_hash},
        "argv": argv,
        "binary": {"path": "target/debug/npa-contour-diagnostics", "sha256": digest(BINARY)},
        "binary_profile": "debug",
        "build_inputs": {
            "binary_sha256": digest(BINARY),
            "contract_sha256": digest(CONTRACT),
            "parser_source_sha256": digest(PARSER),
        },
        "toolchain": {
            "commands_exit_code": {"rustc": 0, "cargo": 0},
            "rustc": "fixture",
            "cargo": "fixture",
        },
        "parser_revision": "m204-s04-c4-contour-v1",
        "source_revision": "fixture",
        "contract": {
            "path": "prd/architecture/npa-acceptance-contract.yaml",
            "sha256": digest(CONTRACT),
            "version": "npa-acceptance-contract/v1",
            "check_id": "c4-live-check",
            "mode": "runtime",
        },
        "corpus": {
            "consultant_xml_count": 43785,
            "consultant_root": "consru_export/consru_export/exports",
            "garant_file_count": 12,
            "garant_root": "law-source/garant",
        },
        "c4_binding": {
            "profile": "contour",
            "limit": None,
            "jobs": 1,
            "binary_profile": "debug",
            "inventory_scope": "consultant XML plus separate Garant files",
            "source_revision": "fixture",
        },
        "started_at": "fixture",
        "finished_at": "fixture",
        "duration_ms": duration,
        "budget_seconds": 3600,
        "terminal": {"outcome": "complete", "exit_code": 0, "signal": None, "timeout": False},
        "observed_output": {
            "diagnostics": diagnostics.relative_to(ROOT).as_posix(),
            "inventory_digest": inventory,
            "jsonl_valid": True,
            "jsonl_lines": len([x for x in diagnostics_text.splitlines() if x.strip()]),
        },
        "logs": {
            "stdout": stdout.relative_to(ROOT).as_posix(),
            "stderr": stderr.relative_to(ROOT).as_posix(),
            "stdout_sha256": digest(stdout),
            "stderr_sha256": digest(stderr),
            "diagnostics_sha256": digest(diagnostics),
        },
        "claims": {
            "operational_acceptance": "pass" if duration >= 3600000 else "non-pass",
            "duration_floor_ms": 3600000,
        },
        "non_claims": ["non-performance: debug timing is not a release performance claim"],
    }
    receipt_path = work / "prd/migration/rust-evidence/m204-s23-fixture-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt_path


def test_equal_duplicate_is_valid_and_s10_is_non_pass() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as raw:
        work = Path(raw)
        digest = "sha256:" + "a" * 64
        fixture = (
            "\n".join(
                json.dumps({"record_kind": kind, "inventory_digest": digest})
                for kind in ("header", "canonical_payload", "operational_envelope")
            )
            + "\n"
        )
        receipt = make_receipt(work, fixture)
        result = run(str(RUNNER), "--verify-receipt", str(receipt))
        assert result.returncode == 0, result.stderr
        assert '"operational_acceptance": "non-pass"' in result.stdout
        historical = json.loads(S10_RECEIPT.read_text(encoding="utf-8"))
        assert historical["claims"]["operational_acceptance"] == "non-pass"
        assert historical["observed_output"]["jsonl_valid"] is False


def test_inventory_fail_closed_cases() -> None:
    cases = {
        "unequal": [("a", "sha256:" + "a" * 64), ("b", "sha256:" + "b" * 64)],
        "missing": [("a", None)],
        "empty": [("a", "")],
        "non_string": [("a", 7)],
        "non_object": [None],
        "malformed": ["{"],
    }
    for name, records in cases.items():
        with tempfile.TemporaryDirectory(dir=ROOT) as raw:
            work = Path(raw)
            lines = []
            for record in records:
                if name == "malformed":
                    lines.append(record)
                elif name == "non_object":
                    lines.append(json.dumps(record))
                else:
                    lines.append(
                        json.dumps({"record_kind": record[0], "inventory_digest": record[1]})
                    )
            receipt = make_receipt(work, "\n".join(lines) + "\n")
            result = run(str(RUNNER), "--verify-receipt", str(receipt))
            assert result.returncode != 0, name


def test_require_operational_pass_rejects_short_fixture() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as raw:
        work = Path(raw)
        digest = "sha256:" + "a" * 64
        receipt = make_receipt(
            work, json.dumps({"record_kind": "header", "inventory_digest": digest}) + "\n"
        )
        result = run(str(RUNNER), "--verify-receipt", str(receipt), "--require-operational-pass")
        assert result.returncode != 0


def test_run_rejects_unsafe_and_existing_outputs() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as raw:
        work = Path(raw)
        args = [
            "--source-revision",
            "fixture",
            "--attempt-id",
            "fixture-run",
            "--binary",
            str(BINARY),
            "--root",
            str(work),
            "--garant-root",
            str(work),
            "--out",
        ]
        unsafe = run(
            str(RUNNER),
            *args,
            "../escape.json",
            "--diagnostics-out",
            "prd/migration/rust-evidence/m204-s23-safe.jsonl",
        )
        assert unsafe.returncode != 0
        collision_rel = f"prd/migration/rust-evidence/m204-s23-fixture-collision-{os.getpid()}.json"
        existing = ROOT / collision_rel
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("sentinel", encoding="utf-8")
        try:
            collision = run(
                str(RUNNER),
                *args,
                collision_rel,
                "--diagnostics-out",
                "prd/migration/rust-evidence/m204-s23-fixture-new.jsonl",
            )
            assert collision.returncode != 0
            assert existing.read_text(encoding="utf-8") == "sentinel"
        finally:
            existing.unlink(missing_ok=True)


def main() -> int:
    tests = [
        test_equal_duplicate_is_valid_and_s10_is_non_pass,
        test_inventory_fail_closed_cases,
        test_require_operational_pass_rejects_short_fixture,
        test_run_rejects_unsafe_and_existing_outputs,
    ]
    for test in tests:
        test()
    print(f"M204_S23_C4_FIXTURE_TESTS_OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
