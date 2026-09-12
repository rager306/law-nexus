#!/usr/bin/env python3
"""Adversarial subprocess contracts for the M204 S16 frozen census CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s16_loop_note.py")
ROOT = SCRIPT.parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
PREDECESSORS = (
    "m204-s09-gsd-validate-deadlock.json",
    "m204-s09-trigger-sql.json",
    "m204-s12-validate-hard-block.json",
    "m204-s12-frozen-hashes.json",
    "m204-s15-requirement-class.json",
    "m204-s15-frozen-hashes.json",
)


def invoke(
    root: Path, census: Path, manifest: Path, timeout: float = 5.0
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "check",
            "--root",
            str(root),
            "--census",
            str(census),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


class ValidateLoopSubprocessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s16-")
        self.root = Path(self.temp.name)
        evidence = self.root / "prd/migration/rust-evidence"
        evidence.mkdir(parents=True)
        for name in PREDECESSORS:
            shutil.copy2(EVIDENCE / name, evidence / name)
        self.census = evidence / "census.json"
        self.manifest = evidence / "manifest.json"
        composed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "compose",
                "--root",
                str(self.root),
                "--census",
                str(self.census),
                "--manifest",
                str(self.manifest),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(composed.returncode, 0, composed.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def assert_rejected(
        self, path: Path | None = None, *, manifest: bool = False, category: str
    ) -> None:
        result = invoke(
            self.root,
            self.census if path is None or not manifest else path,
            self.manifest if path is None or manifest else path,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(category, result.stderr)

    def test_positive_fixture_is_independent_of_worktree(self) -> None:
        result = invoke(self.root, self.census, self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S16_T01_CENSUS_OK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

    def test_rejects_abort_count_rows_order_and_duplicate_flow(self) -> None:
        original = self.read_json(self.census)
        mutations = {
            "count": {**original, "abort_count": 4},
            "missing": {**original, "aborts": original["aborts"][:2]},
            "extra": {**original, "aborts": original["aborts"] + [original["aborts"][2]]},
            "unordered": {
                **original,
                "aborts": [original["aborts"][1], original["aborts"][0], original["aborts"][2]],
            },
            "duplicate-flow": {
                **original,
                "aborts": [
                    *original["aborts"][:2],
                    {**original["aborts"][2], "flow_id": original["aborts"][0]["flow_id"]},
                ],
            },
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                result = invoke(self.root, self.census, self.manifest)
                self.assertNotEqual(result.returncode, 0)
                self.assertRegex(
                    result.stderr, r"(exactly three aborts|abort row mismatch|census schema)"
                )
                self.write_json(self.census, original)

    def test_rejects_row_polarity_timestamp_and_exact_messages(self) -> None:
        original = self.read_json(self.census)
        cases = (
            ("timestamp", {"unit_start_at": "2026-09-12T15:22:25.040Z"}, "row mismatch"),
            ("status", {"unit_end_status": "validated"}, "row mismatch"),
            ("finalize", {"finalize_status": "done"}, "row mismatch"),
            ("reason", {"iteration_end_reason": "retry"}, "row mismatch"),
            ("sql", {}, "census"),
        )
        for name, change, category in cases:
            with self.subTest(name=name):
                mutation = json.loads(json.dumps(original))
                if name == "sql":
                    mutation["sql_abort_message"] = "altered SQL"
                else:
                    mutation["aborts"][0].update(change)
                self.write_json(self.census, mutation)
                result = invoke(self.root, self.census, self.manifest)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(category, result.stderr)
                self.write_json(self.census, original)

    def test_rejects_fixed_or_promoted_lifecycle_claims_and_extra_keys(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("s16_called_validate_milestone", True),
            ("law_nexus_fixable", True),
            ("engine_fix", "fixed"),
            ("upstream_issue", "filed"),
            ("retry_substitute", True),
            ("same_defect_as_s09", False),
            ("s12_hard_block_stopped_dispatch", True),
            ("validation_projection_present", True),
            ("c4_acceptance", "pass"),
            ("status_effect", "closed"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                mutation = json.loads(json.dumps(original))
                mutation[key] = value
                self.write_json(self.census, mutation)
                result = invoke(self.root, self.census, self.manifest)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("census", result.stderr)
                self.write_json(self.census, original)
        mutation = json.loads(json.dumps(original))
        mutation["unexpected"] = None
        self.write_json(self.census, mutation)
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("closed", result.stderr)

    def test_rejects_schema_duplicates_bool_as_int_and_missing_files(self) -> None:
        raw = self.census.read_text(encoding="utf-8")
        self.census.write_text(
            raw.replace('"abort_count": 3', '"abort_count": 3,\n  "abort_count": 3'),
            encoding="utf-8",
        )
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate JSON key", result.stderr)
        original = self.read_json(self.census)
        original["abort_count"] = True
        self.write_json(self.census, original)
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly three aborts", result.stderr)
        self.census.unlink()
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, r"No such file|not found")

    def test_rejects_unsafe_manifest_paths_and_symlink_components(self) -> None:
        original = self.read_json(self.manifest)
        for value in ("/tmp/escape", "../escape", "x\\escape", ".git/config", ".gsd/secret"):
            with self.subTest(path=value):
                mutation = json.loads(json.dumps(original))
                mutation["files"][0]["path"] = value
                self.write_json(self.manifest, mutation)
                result = invoke(self.root, self.census, self.manifest)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsafe manifest path", result.stderr)
                self.write_json(self.manifest, original)
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link_dir = self.root / "link"
        link_dir.symlink_to(self.root, target_is_directory=True)
        mutation = json.loads(json.dumps(original))
        mutation["files"][0]["path"] = "link/outside.json"
        self.write_json(self.manifest, mutation)
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink component", result.stderr)

    def test_rejects_tampered_pin_and_fabricated_fourth_abort(self) -> None:
        predecessor = self.root / "prd/migration/rust-evidence" / PREDECESSORS[0]
        predecessor.write_text(predecessor.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest pin drift", result.stderr)
        shutil.copy2(EVIDENCE / PREDECESSORS[0], predecessor)
        original = self.read_json(self.census)
        fourth = {**original["aborts"][2], "ordinal": 4, "unit_start_at": "2026-09-12T16:11:44Z"}
        mutation = {**original, "abort_count": 4, "aborts": [*original["aborts"], fourth]}
        self.write_json(self.census, mutation)
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly three aborts", result.stderr)

    def test_malformed_json_fails_within_bounded_timeout(self) -> None:
        self.census.write_text("{not-json", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expecting property name", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
