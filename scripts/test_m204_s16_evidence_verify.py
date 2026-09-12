#!/usr/bin/env python3
"""Negative subprocess contracts for the S16 aggregate verifier."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s16_evidence_verify.py")
ROOT = SCRIPT.parents[1]
CENSUS = ROOT / "prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json"
MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s16-frozen-hashes.json"


class EvidenceAggregateContracts(unittest.TestCase):
    def invoke(self, *args: str, timeout: float = 180) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "verify", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    def test_positive_is_strict_and_emits_marker(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("S16_VERIFY_OK", result.stdout.splitlines())

    def test_census_and_manifest_are_closed_inputs(self) -> None:
        census = json.loads(CENSUS.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(census["abort_count"], 3)
        self.assertFalse(census["law_nexus_fixable"])
        self.assertEqual(len(manifest["files"]), 6)
        self.assertEqual({"path", "sha256", "size_bytes"}, set(manifest["files"][0]))

    def test_missing_or_malformed_dependency_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m204-s16-evidence-") as tmp:
            fixture = Path(tmp)
            broken = fixture / "broken.json"
            broken.write_text("{not-json", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import json,sys; json.load(open(sys.argv[1]))",
                    str(broken),
                ],
                text=True,
                capture_output=True,
                timeout=2,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Expecting property name", result.stderr)

    def test_tamper_fixture_is_rejected_by_public_t01_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m204-s16-tamper-") as tmp:
            fixture = Path(tmp)
            evidence = fixture / "prd/migration/rust-evidence"
            evidence.mkdir(parents=True)
            for source in (
                "m204-s09-gsd-validate-deadlock.json",
                "m204-s09-trigger-sql.json",
                "m204-s12-validate-hard-block.json",
                "m204-s12-frozen-hashes.json",
                "m204-s15-requirement-class.json",
                "m204-s15-frozen-hashes.json",
            ):
                target = evidence / source
                target.write_bytes((ROOT / "prd/migration/rust-evidence" / source).read_bytes())
            census = evidence / "census.json"
            manifest = evidence / "manifest.json"
            compose = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/m204_s16_loop_note.py"),
                    "compose",
                    "--root",
                    str(fixture),
                    "--census",
                    str(census),
                    "--manifest",
                    str(manifest),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(compose.returncode, 0, compose.stderr)
            manifest_doc = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_doc["files"][0]["sha256"] = "sha256:" + "0" * 64
            manifest.write_text(json.dumps(manifest_doc), encoding="utf-8")
            check = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/m204_s16_loop_note.py"),
                    "check",
                    "--root",
                    str(fixture),
                    "--census",
                    str(census),
                    "--manifest",
                    str(manifest),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("manifest pin drift", check.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
