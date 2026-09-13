#!/usr/bin/env python3
"""Independent adversarial subprocess contracts for the M204 S22 packet."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s22_liveness.py")
ROOT = SCRIPT.parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
LEDGER_NAME = "ledger.json"
MANIFEST_NAME = "manifest.json"
S21 = ROOT / "scripts/m204_s21_loop_note.py"
S15 = ROOT / "scripts/m204_s15_requirement_class.py"
S21_FILES = (
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
    "m204-s18-post-s17-validate-loop.json",
    "m204-s18-frozen-hashes.json",
    "m204-s19-post-s18-validate-abort.json",
    "m204-s19-frozen-hashes.json",
    "m204-s20-post-s19-validate-loop.json",
    "m204-s20-frozen-hashes.json",
)
S22_FILES = S21_FILES + (
    "m204-s21-post-s20-validate-loop.json",
    "m204-s21-frozen-hashes.json",
    "m204-s14-c4-acceptance.json",
    "m204-s14-verification-battery.json",
    "m204-s10-c4-operational-receipt.json",
    "m204-validation-battery-20260912-s10.json",
)


def invoke(
    root: Path,
    ledger: Path,
    manifest: Path,
    command: str = "check",
    timeout: float = 5.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            command,
            "--root",
            str(root),
            "--ledger",
            str(ledger),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


class S22LivenessSubprocessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s22-")
        self.root = Path(self.temp.name)
        evidence = self.root / "prd/migration/rust-evidence"
        evidence.mkdir(parents=True)
        for name in S22_FILES:
            shutil.copy2(EVIDENCE / name, evidence / name)
        self.ledger = evidence / LEDGER_NAME
        self.manifest = evidence / MANIFEST_NAME
        composed = invoke(self.root, self.ledger, self.manifest, "compose")
        self.assertEqual(composed.returncode, 0, composed.stderr)
        self.original_ledger = self.ledger.read_bytes()
        self.original_manifest = self.manifest.read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def restore(self) -> None:
        self.ledger.write_bytes(self.original_ledger)
        self.manifest.write_bytes(self.original_manifest)

    def rejected(self) -> subprocess.CompletedProcess[str]:
        result = invoke(self.root, self.ledger, self.manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("S22_T01_BLOCKER_OK", result.stdout)
        return result

    def test_positive_roundtrip_is_bounded_and_exact(self) -> None:
        result = invoke(self.root, self.ledger, self.manifest, timeout=2.0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(), ["S22_T01_BLOCKER_OK", "S22_T01_EXACT_RECORDS_OK"]
        )
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)
        ledger = self.read_json(self.ledger)
        manifest = self.read_json(self.manifest)
        self.assertEqual(ledger["c4_control"], "not-run")
        self.assertEqual(ledger["c4_operational_acceptance"], "non-pass")
        self.assertFalse(ledger["retry_substitute"])
        self.assertEqual(ledger["classification"], "supporting-only")
        self.assertEqual(len(manifest["files"]), 22)
        self.assertEqual([row["path"] for row in manifest["files"][:16]], list(S21_PATHS))
        self.assertEqual(len({row["path"] for row in manifest["files"]}), 22)

    def test_compose_is_deterministic_and_does_not_overwrite(self) -> None:
        first_ledger = self.ledger.read_bytes()
        first_manifest = self.manifest.read_bytes()
        result = invoke(self.root, self.ledger, self.manifest, "compose")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing destination", result.stderr)
        self.assertEqual(self.ledger.read_bytes(), first_ledger)
        self.assertEqual(self.manifest.read_bytes(), first_manifest)

    def test_rejects_promotion_lifecycle_and_conflation_claims(self) -> None:
        original = self.read_json(self.ledger)
        mutations = (
            ("recovery-pass", {"gsd_recovery_liveness": "pass"}),
            ("liveness-pass", {"gsd_recovery_liveness": "passing"}),
            ("operational-pass", {"c4_operational_acceptance": "pass"}),
            ("control-pass", {"c4_control": "pass"}),
            ("extra-acceptance", {"c4_acceptance": "pass"}),
            ("fixed-engine", {"engine_fix": "fixed"}),
            ("filed-upstream", {"upstream_issue": "filed"}),
            ("fixable", {"law_nexus_fixable": True}),
            ("different-defect", {"same_defect_as_s09": False}),
            ("validate-called", {"s22_called_validate_milestone": True}),
            ("retry", {"retry_substitute": True}),
            ("product-not-distinct", {"product_failed_distinct": False}),
            ("status-promotion", {"status_effect": "validated"}),
        )
        for name, change in mutations:
            with self.subTest(name=name):
                mutation = copy.deepcopy(original)
                mutation.update(change)
                self.write_json(self.ledger, mutation)
                self.rejected()
                self.restore()

    def test_rejects_schema_types_duplicates_and_unknown_keys(self) -> None:
        original = self.read_json(self.ledger)
        extra = {**original, "unexpected": None}
        self.write_json(self.ledger, extra)
        self.rejected()
        self.restore()

        raw = self.ledger.read_text(encoding="utf-8")
        self.ledger.write_text(
            raw.replace('"duration_ms": 4969991', '"duration_ms": true', 1), encoding="utf-8"
        )
        self.rejected()
        self.restore()

        raw = self.ledger.read_text(encoding="utf-8")
        self.ledger.write_text(
            raw.replace(
                '"duration_ms": 4969991', '"duration_ms": 4969991,\n  "duration_ms": 4969991', 1
            ),
            encoding="utf-8",
        )
        result = self.rejected()
        self.assertIn("duplicate JSON key", result.stderr)
        self.restore()

    def test_rejects_manifest_tamper_order_duplicates_and_each_pin(self) -> None:
        original = self.read_json(self.manifest)
        cases = []
        reordered = copy.deepcopy(original)
        reordered["files"][0], reordered["files"][1] = reordered["files"][1], reordered["files"][0]
        cases.append(("reordered", reordered))
        missing = copy.deepcopy(original)
        missing["files"] = missing["files"][:-1]
        cases.append(("missing", missing))
        duplicate = copy.deepcopy(original)
        duplicate["files"].append(copy.deepcopy(duplicate["files"][-1]))
        cases.append(("duplicate", duplicate))
        self_hash = copy.deepcopy(original)
        self_hash["files"].append(
            {"path": MANIFEST_NAME, "sha256": "sha256:" + "0" * 64, "size_bytes": 1}
        )
        cases.append(("self-hash", self_hash))
        for index in range(22):
            forged = copy.deepcopy(original)
            forged["files"][index]["sha256"] = "sha256:" + "f" * 64
            cases.append((f"pin-{index}", forged))
        for name, mutation in cases:
            with self.subTest(name=name):
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.restore()

    def test_rejects_unsafe_paths_symlink_and_compose_escape(self) -> None:
        original = self.read_json(self.manifest)
        for path in ("/tmp/escape", "../escape", "x\\escape", ".git/secret", ".gsd/secret"):
            with self.subTest(path=path):
                mutation = copy.deepcopy(original)
                mutation["files"][0]["path"] = path
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.restore()

        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = self.root / "link"
        link.symlink_to(outside)
        mutation = copy.deepcopy(original)
        mutation["files"][0]["path"] = "link"
        self.write_json(self.manifest, mutation)
        self.rejected()
        self.restore()

        outside_ledger = self.root.parent / "m204-s22-outside-ledger.json"
        outside_manifest = self.root.parent / "m204-s22-outside-manifest.json"
        try:
            result = invoke(self.root, outside_ledger, self.manifest, "compose")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(outside_ledger.exists())
        finally:
            outside_ledger.unlink(missing_ok=True)
            outside_manifest.unlink(missing_ok=True)

    def test_malformed_json_and_missing_inputs_fail_closed_without_success_marker(self) -> None:
        before = self.ledger.read_bytes()
        self.ledger.write_text('{"schema":', encoding="utf-8")
        result = self.rejected()
        self.assertNotIn("S22_T01_EXACT_RECORDS_OK", result.stdout)
        self.ledger.write_bytes(before)
        self.manifest.unlink()
        result = invoke(self.root, self.ledger, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S22_T01_BLOCKER_OK", result.stdout)

    def test_independent_s21_and_s15_consumers_use_real_output_shapes(self) -> None:
        s21_manifest = EVIDENCE / "m204-s21-frozen-hashes.json"
        s21_census = EVIDENCE / "m204-s21-post-s20-validate-loop.json"
        s21 = subprocess.run(
            [
                sys.executable,
                str(S21),
                "check",
                "--root",
                str(ROOT),
                "--census",
                str(s21_census),
                "--manifest",
                str(s21_manifest),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(s21.returncode, 0, s21.stderr)
        self.assertIn("S21_T01_CENSUS_OK", s21.stdout)

        s15 = subprocess.run(
            [sys.executable, str(S15), "classify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(s15.returncode, 0, s15.stderr)
        self.assertEqual(s15.stderr, "")
        observed = json.loads(s15.stdout)
        self.assertEqual(observed["c4_acceptance"], "non-pass")
        self.assertEqual(observed["class_matched_ids"], [])
        self.assertEqual(observed["status_effect"], "unchanged")


S21_PATHS = tuple(f"prd/migration/rust-evidence/{name}" for name in S21_FILES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
