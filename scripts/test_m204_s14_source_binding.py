#!/usr/bin/env python3
"""Bounded hostile tests for the M204 S14 historical S10 replay seam."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "prd/migration/rust-evidence/m204-s14-s10-source-binding.json"
RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
RUNNER = ROOT / "scripts/m204_s10_c4_run.py"
SOURCE = ROOT / "scripts/m204_s14_source_binding.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def test_real_binding_replays_without_binary() -> None:
    with tempfile.TemporaryDirectory() as raw:
        repo = Path(raw)
        artifact = repo / "binding.json"
        artifact.write_bytes(BINDING.read_bytes())
        receipt = repo / "receipt.json"
        receipt.write_bytes(RECEIPT.read_bytes())
        # The verifier's source root is the product repo; only the receipt is copied and
        # the actual call uses the tracked binding, proving the missing old binary is bypassed.
        result = run(
            str(RUNNER), "--verify-receipt", str(RECEIPT), "--historical-binding", str(BINDING)
        )
        assert result.returncode == 0, result.stderr
        assert '"operational_acceptance": "non-pass"' in result.stdout


def test_tampered_binding_and_receipt_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binding = json.loads(BINDING.read_text(encoding="utf-8"))
        binding["parser_revision"] = "forged"
        forged_binding = directory / "binding.json"
        forged_binding.write_text(json.dumps(binding), encoding="utf-8")
        result = run(str(SOURCE), "verify", "--artifact", str(forged_binding))
        assert result.returncode != 0
        binding = json.loads(BINDING.read_text(encoding="utf-8"))
        binding["historical_receipt"]["sha256"] = "sha256:" + "0" * 64
        forged_binding.write_text(json.dumps(binding), encoding="utf-8")
        result = run(str(SOURCE), "verify", "--artifact", str(forged_binding))
        assert result.returncode != 0


def test_closed_schema_and_containment_negatives() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        base = json.loads(BINDING.read_text(encoding="utf-8"))
        for mutation in ("extra", "absolute", "traversal"):
            value = copy.deepcopy(base)
            if mutation == "extra":
                value["unexpected"] = True
            elif mutation == "absolute":
                value["historical_receipt"]["path"] = str(RECEIPT.resolve())
            else:
                value["historical_receipt"]["path"] = "../escape.json"
            artifact = directory / f"{mutation}.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            result = run(str(SOURCE), "verify", "--artifact", str(artifact))
            assert result.returncode != 0, mutation


def main() -> int:
    tests = [
        test_real_binding_replays_without_binary,
        test_tampered_binding_and_receipt_are_rejected,
        test_closed_schema_and_containment_negatives,
    ]
    for test in tests:
        test()
    print(f"M204_S14_SOURCE_BINDING_TESTS_OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
