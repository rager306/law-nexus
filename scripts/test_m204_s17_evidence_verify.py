#!/usr/bin/env python3
"""Subprocess-only integration negatives for the S17 aggregate verifier."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s17_evidence_verify.py")
ROOT = SCRIPT.parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
PREDECESSORS = (
    "m204-s09-gsd-validate-deadlock.json",
    "m204-s09-trigger-sql.json",
    "m204-s12-validate-hard-block.json",
    "m204-s12-frozen-hashes.json",
    "m204-s15-requirement-class.json",
    "m204-s15-frozen-hashes.json",
    "m204-s16-post-s15-validate-loop.json",
    "m204-s16-frozen-hashes.json",
)


def run(root: Path, *, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{root / 'bin'}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["python", str(SCRIPT), "verify", "--root", str(root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


class EvidenceAggregateContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s17-aggregate-")
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "bin").mkdir()
        (self.root / "bin/uv").write_text('#!/bin/sh\nshift\nexec "$@"\n', encoding="utf-8")
        (self.root / "bin/uv").chmod(0o755)
        (self.root / "doc").mkdir()
        (self.root / "prd/architecture/review-cases").mkdir(parents=True)
        shutil.copy2(SCRIPT, self.root / "scripts/m204_s17_evidence_verify.py")
        shutil.copy2(
            ROOT / "scripts/m204_s17_loop_note.py", self.root / "scripts/m204_s17_loop_note.py"
        )
        shutil.copy2(
            ROOT / "scripts/m204_s17_t01_verify.sh", self.root / "scripts/m204_s17_t01_verify.sh"
        )
        (self.root / "scripts/m204_s17_t02_verify.sh").write_text(
            "#!/bin/sh\nprintf '%s\\n' S17_T02_NEGATIVES_OK\n", encoding="utf-8"
        )
        (self.root / "scripts/m204_s17_t02_verify.sh").chmod(0o755)
        (self.root / "scripts/m204_s16_loop_note.py").write_text(
            "print('S16_T01_CENSUS_OK')\n", encoding="utf-8"
        )
        (self.root / "scripts/m204_s15_requirement_class.py").write_text(
            'import json\nprint(json.dumps({"c4_acceptance": "non-pass", "classification": "supporting-only", "class_matched_ids": [], "status_effect": "unchanged"}, separators=(\',\', \':\')))\n',
            encoding="utf-8",
        )
        for path in (
            "doc/gsd-headless-supervisor.md",
            "prd/architecture/review-cases/rc28-remediation-program.md",
        ):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        evidence = self.root / "prd/migration/rust-evidence"
        evidence.mkdir(parents=True)
        for name in PREDECESSORS:
            shutil.copy2(EVIDENCE / name, evidence / name)
        subprocess.run(
            [
                "python",
                str(ROOT / "scripts/m204_s17_loop_note.py"),
                "compose",
                "--root",
                str(self.root),
                "--census",
                str(evidence / "m204-s17-post-s16-validate-loop.json"),
                "--manifest",
                str(evidence / "m204-s17-frozen-hashes.json"),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def mutate_census(self, **changes: object) -> None:
        path = self.root / "prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value.update(changes)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def test_positive_control_is_subprocess_only(self) -> None:
        result = run(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S17_VERIFY_OK", result.stdout)

    def test_promoted_polarity_is_rejected_before_children(self) -> None:
        self.mutate_census(law_nexus_fixable=True, engine_fix="fixed")
        self.assertNotEqual(run(self.root).returncode, 0)

    def test_missing_operator_document_is_rejected(self) -> None:
        (self.root / "doc/gsd-headless-supervisor.md").unlink()
        self.assertNotEqual(run(self.root).returncode, 0)

    def test_malformed_classifier_and_timeout_boundaries_are_nonzero(self) -> None:
        classifier = self.root / "scripts/m204_s15_requirement_class.py"
        classifier.write_text("raise SystemExit(7)\n", encoding="utf-8")
        result = run(self.root, timeout=5.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed", result.stderr)

    def test_predecessor_pin_drift_is_rejected(self) -> None:
        (self.root / "prd/migration/rust-evidence" / PREDECESSORS[0]).write_text(
            "{}\n", encoding="utf-8"
        )
        self.assertNotEqual(run(self.root).returncode, 0)


if __name__ == "__main__":
    unittest.main()
