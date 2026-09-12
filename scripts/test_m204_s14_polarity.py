#!/usr/bin/env python3
"""Bounded subprocess and mutation tests for the S14 C4 polarity consumer."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("m204_s14_polarity.py")
ROOT = SCRIPT.parents[1]
ARTIFACT = ROOT / "prd/migration/rust-evidence/m204-s14-c4-acceptance.json"


def run(command: str, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), command, "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class S14PolarityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s14-polarity-")
        self.out = Path(self.temp.name) / "acceptance.json"
        composed = run("compose", self.out)
        self.assertEqual(composed.returncode, 0, composed.stderr)
        self.baseline = json.loads(self.out.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_compose_check_and_classify_are_explicitly_non_pass(self) -> None:
        checked = run("check", self.out)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        classified = run("classify", self.out)
        self.assertEqual(classified.returncode, 0, classified.stderr)
        self.assertEqual(
            json.loads(classified.stdout),
            {"integrity": "pass", "c4_acceptance": "non-pass", "classification": "supporting-only"},
        )
        self.assertEqual(self.baseline["c4_acceptance"], "non-pass")
        self.assertEqual(
            self.baseline["surfaces"]["s10_receipt"]["extracted"]["jsonl_valid"], False
        )
        self.assertEqual(
            self.baseline["surfaces"]["s11_classification"]["extracted"][
                "duplicate_digest_occurrences"
            ],
            2,
        )

    def test_rejects_forged_pass_and_forged_jsonl_claim(self) -> None:
        for key, value in (("c4_acceptance", "pass"),):
            forged = copy.deepcopy(self.baseline)
            forged[key] = value
            self.out.write_text(json.dumps(forged), encoding="utf-8")
            self.assertNotEqual(run("check", self.out).returncode, 0)
        forged = copy.deepcopy(self.baseline)
        forged["surfaces"]["s10_receipt"]["extracted"]["jsonl_valid"] = True
        self.out.write_text(json.dumps(forged), encoding="utf-8")
        self.assertNotEqual(run("check", self.out).returncode, 0)

    def test_rejects_forged_pin_missing_surface_extra_key_and_unsafe_paths(self) -> None:
        cases = []
        forged = copy.deepcopy(self.baseline)
        forged["surfaces"]["s10_receipt"]["sha256"] = "sha256:" + "0" * 64
        cases.append(forged)
        missing = copy.deepcopy(self.baseline)
        del missing["surfaces"]["s13_battery"]
        cases.append(missing)
        extra = copy.deepcopy(self.baseline)
        extra["extra"] = True
        cases.append(extra)
        for unsafe in ("/tmp/receipt.json", "../receipt.json"):
            escaped = copy.deepcopy(self.baseline)
            escaped["surfaces"]["s10_receipt"]["path"] = unsafe
            cases.append(escaped)
        for value in cases:
            self.out.write_text(json.dumps(value), encoding="utf-8")
            self.assertNotEqual(run("check", self.out).returncode, 0)

    def test_refuses_overwrite_and_product_failed_does_not_change_reason(self) -> None:
        second = run("compose", self.out)
        self.assertEqual(second.returncode, 0, second.stderr)
        forged = copy.deepcopy(self.baseline)
        forged["surfaces"]["s11_classification"]["extracted"]["distinct_from_product_failed"] = (
            False
        )
        self.out.write_text(json.dumps(forged), encoding="utf-8")
        self.assertNotEqual(run("check", self.out).returncode, 0)


if __name__ == "__main__":
    unittest.main()
