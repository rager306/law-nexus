#!/usr/bin/env python3
"""Subprocess-only integration negatives for the S18 aggregate verifier."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s18_evidence_verify.py")
ROOT = SCRIPT.parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
PINS = (
    "m204-s09-gsd-validate-deadlock.json",
    "m204-s09-trigger-sql.json",
    "m204-s12-validate-hard-block.json",
    "m204-s12-frozen-hashes.json",
    "m204-s15-requirement-class.json",
    "m204-s15-frozen-hashes.json",
    "m204-s16-post-s15-validate-loop.json",
    "m204-s16-frozen-hashes.json",
    "m204-s17-post-s16-validate-loop.json",
    "m204-s17-frozen-hashes.json",
)


def run(root: Path, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{root / 'bin'}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["python", "scripts/m204_s18_evidence_verify.py", "verify"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


class S18AggregateContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s18-aggregate-")
        self.root = Path(self.temp.name)
        for path in (
            "scripts",
            "bin",
            "doc",
            "prd/architecture/review-cases",
            "prd/migration/rust-evidence",
        ):
            (self.root / path).mkdir(parents=True, exist_ok=True)
        (self.root / "bin/uv").write_text('#!/bin/sh\nshift\nexec "$@"\n', encoding="utf-8")
        (self.root / "bin/uv").chmod(0o755)
        for name in (
            "m204_s18_evidence_verify.py",
            "m204_s18_loop_note.py",
            "m204_s18_t01_verify.sh",
            "test_m204_s18_validate_loop.py",
            "m204_s17_loop_note.py",
            "m204_s17_t01_verify.sh",
            "m204_s15_requirement_class.py",
        ):
            shutil.copy2(ROOT / "scripts" / name, self.root / "scripts" / name)
        (self.root / "scripts/m204_s18_t02_verify.sh").write_text(
            "#!/bin/sh\nprintf '%s\\n' S18_T02_NEGATIVES_OK\n", encoding="utf-8"
        )
        (self.root / "scripts/m204_s18_t02_verify.sh").chmod(0o755)
        (self.root / "scripts/m204_s16_loop_note.py").write_text(
            "print('S16_T01_CENSUS_OK')\n", encoding="utf-8"
        )
        for path in (
            "doc/gsd-headless-supervisor.md",
            "prd/architecture/review-cases/rc28-remediation-program.md",
        ):
            shutil.copy2(ROOT / path, self.root / path)
        for name in PINS + ("m204-s18-post-s17-validate-loop.json", "m204-s18-frozen-hashes.json"):
            shutil.copy2(EVIDENCE / name, self.root / "prd/migration/rust-evidence" / name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_positive_control_is_subprocess_only(self) -> None:
        result = run(self.root, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S18_VERIFY_OK", result.stdout)

    def test_child_failure_is_nonzero_without_success_marker(self) -> None:
        path = self.root / "scripts/test_m204_s18_validate_loop.py"
        path.write_text("raise SystemExit(7)\n", encoding="utf-8")
        path.chmod(0o755)
        result = run(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S18_VERIFY_OK", result.stdout)

    def test_classifier_promotion_is_rejected(self) -> None:
        path = self.root / "scripts/m204_s15_requirement_class.py"
        path.write_text(
            'import json\nprint(json.dumps({"c4_acceptance":"pass","classification":"canonical","class_matched_ids":["R038"],"status_effect":"advanced"}))\n',
            encoding="utf-8",
        )
        result = run(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S18_VERIFY_OK", result.stdout)

    def test_predecessor_pin_drift_is_rejected(self) -> None:
        path = self.root / "prd/migration/rust-evidence" / PINS[-1]
        path.write_text(path.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
        result = run(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S18_VERIFY_OK", result.stdout)

    def test_missing_new_operator_text_is_rejected(self) -> None:
        path = self.root / "doc/gsd-headless-supervisor.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Post-S17", "Removed-S17"), encoding="utf-8"
        )
        result = run(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S18_VERIFY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
