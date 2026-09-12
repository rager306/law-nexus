#!/usr/bin/env python3
"""Independent subprocess adversarial contracts for the M204 S19 census CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s19_loop_note.py")
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
    "m204-s17-post-s16-validate-loop.json",
    "m204-s17-frozen-hashes.json",
    "m204-s18-post-s17-validate-loop.json",
    "m204-s18-frozen-hashes.json",
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


class S19ValidateLoopSubprocessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s19-")
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

    def rejected(self) -> subprocess.CompletedProcess[str]:
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("S19_T01_CENSUS_OK", result.stdout)
        return result

    def test_positive_control_is_subprocess_only_and_bounded(self) -> None:
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S19_T01_CENSUS_OK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

    def test_consumers_preserve_s18_and_s15_supporting_only_polarity(self) -> None:
        tracked = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "check",
                "--root",
                str(ROOT),
                "--census",
                str(EVIDENCE / "m204-s19-post-s18-validate-abort.json"),
                "--manifest",
                str(EVIDENCE / "m204-s19-frozen-hashes.json"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        self.assertIn("S19_T01_CENSUS_OK", tracked.stdout)

        census = self.read_json(self.census)
        self.assertEqual(census["c4_acceptance"], "non-pass")
        self.assertEqual(census["classification"], "supporting-only")
        self.assertEqual(census["status_effect"], "unchanged")
        self.assertFalse(census["law_nexus_fixable"])
        self.assertFalse(census["retry_substitute"])
        self.assertFalse(census["s19_called_validate_milestone"])

        s18 = subprocess.run(
            [sys.executable, str(ROOT / "scripts/m204_s18_loop_note.py"), "check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(s18.returncode, 0, s18.stderr)
        self.assertIn("S18_T01_CENSUS_OK", s18.stdout)

        s15 = subprocess.run(
            ["uv", "run", "python", "scripts/m204_s15_requirement_class.py", "classify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(s15.returncode, 0, s15.stderr)
        self.assertEqual(s15.stderr, "")
        self.assertEqual(
            json.loads(s15.stdout),
            {
                "c4_acceptance": "non-pass",
                "classification": "supporting-only",
                "class_matched_ids": [],
                "status_effect": "unchanged",
            },
        )

    def test_rejects_abort_count_and_supervisor_shape_confusion(self) -> None:
        original = self.read_json(self.census)
        mutations = (
            ("zero-count", {**original, "abort_count": 0}),
            ("four-retries-is-not-four-aborts", {**original, "abort_count": 4}),
            ("missing-row", {**original, "aborts": []}),
            (
                "supervisor-as-abort",
                {
                    **original,
                    "abort_count": 2,
                    "aborts": [original["aborts"][0], original["supervisor_exit"]],
                },
            ),
            (
                "second-research-abort",
                {
                    **original,
                    "abort_count": 2,
                    "aborts": [
                        original["aborts"][0],
                        {
                            **original["aborts"][0],
                            "ordinal": 2,
                            "unit_start_at": "2026-09-12T20:04:18.077Z",
                            "flow_id": "forged-after-research",
                        },
                    ],
                },
            ),
            (
                "duplicate-flow-id",
                {
                    **original,
                    "abort_count": 2,
                    "aborts": [
                        original["aborts"][0],
                        {
                            **original["aborts"][0],
                            "ordinal": 2,
                            "flow_id": original["aborts"][0]["flow_id"],
                        },
                    ],
                },
            ),
            (
                "s18-window-collapse",
                {
                    **original,
                    "aborts": [
                        {
                            **original["aborts"][0],
                            "flow_id": "f76ce443-afce-43bb-9342-0b0484260951",
                        }
                    ],
                },
            ),
        )
        for name, mutation in mutations:
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_s18_intercept_schema_leak_and_wrong_supervisor_polarity(self) -> None:
        original = self.read_json(self.census)
        self.write_json(self.census, {**original, "intercept": {}})
        self.rejected()
        self.write_json(self.census, original)
        missing = json.loads(json.dumps(original))
        del missing["supervisor_exit"]["stop_text"]
        self.write_json(self.census, missing)
        self.rejected()
        self.write_json(self.census, original)
        extra = json.loads(json.dumps(original))
        extra["supervisor_exit"]["intercept"] = False
        self.write_json(self.census, extra)
        self.rejected()
        self.write_json(self.census, original)
        for key, value in (
            ("kind", "predispatch_cancelled_interrupted"),
            ("kind", "no-artifact"),
            ("classify_status", "cancelled"),
            ("interrupted", True),
            ("tool_calls", 0),
            ("journal_unit_start_present", False),
            ("headless_pid", 1216437),
            ("headless_pid", "1216437"),
            ("exit_reason", "retry"),
            ("closeout_n", True),
        ):
            with self.subTest(key=key, value=value):
                mutation = json.loads(json.dumps(original))
                mutation["supervisor_exit"][key] = value
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_exact_abort_sql_and_supervisor_strings(self) -> None:
        original = self.read_json(self.census)
        for key, value in (
            ("unit_end_status", "validated"),
            ("finalize_status", "done"),
            ("iteration_end_reason", "finalize-retry: altered"),
        ):
            with self.subTest(key=key):
                mutation = json.loads(json.dumps(original))
                mutation["aborts"][0][key] = value
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)
        for key, value in (
            ("sql_abort_message", "truncated SQL"),
            ("trigger_name", "other_trigger"),
        ):
            with self.subTest(key=key):
                self.write_json(self.census, {**original, key: value})
                self.rejected()
                self.write_json(self.census, original)
        mutation = json.loads(json.dumps(original))
        mutation["supervisor_exit"]["stop_text"] = "closeout break"
        self.write_json(self.census, mutation)
        self.rejected()
        self.write_json(self.census, original)

    def test_rejects_every_promotion_flag_and_extra_classifier_claim(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("s18_census_stopped_dispatch", True),
            ("s17_census_stopped_dispatch", True),
            ("s19_called_validate_milestone", True),
            ("validation_projection_present", True),
            ("engine_fix", "fixed"),
            ("law_nexus_fixable", True),
            ("upstream_issue", "filed"),
            ("c4_acceptance", "pass"),
            ("status_effect", "validated"),
            ("status_effect", "advanced"),
            ("classification", "canonical-validation"),
            ("same_defect_as_s09", False),
            ("retry_substitute", True),
            ("class_matched_ids", []),
        )
        for key, value in changes:
            with self.subTest(key=key, value=value):
                self.write_json(self.census, {**original, key: value})
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_closed_schema_duplicates_and_bool_int_confusion(self) -> None:
        original = self.read_json(self.census)
        self.write_json(self.census, {**original, "unexpected": None})
        self.rejected()
        self.write_json(self.census, original)

        raw = self.census.read_text(encoding="utf-8")
        self.census.write_text(
            raw.replace('"abort_count": 1', '"abort_count": 1,\n  "abort_count": 1'),
            encoding="utf-8",
        )
        result = self.rejected()
        self.assertIn("duplicate JSON key", result.stderr)
        self.write_json(self.census, original)

        for key, value in (("abort_count", True), ("law_nexus_fixable", 0)):
            with self.subTest(key=key):
                self.write_json(self.census, {**original, key: value})
                self.rejected()
                self.write_json(self.census, original)
        manifest = self.read_json(self.manifest)
        manifest["files"][0]["size_bytes"] = True
        self.write_json(self.manifest, manifest)
        self.rejected()
        self.write_json(self.manifest, self.read_json(EVIDENCE / "m204-s19-frozen-hashes.json"))

    def test_rejects_unsafe_paths_symlink_and_each_predecessor_pin(self) -> None:
        original = self.read_json(self.manifest)
        for value in ("/tmp/escape", "../escape", "x\\escape", ".git/config", ".gsd/secret"):
            with self.subTest(path=value):
                mutation = json.loads(json.dumps(original))
                mutation["files"][0]["path"] = value
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.write_json(self.manifest, original)

        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link_dir = self.root / "link"
        link_dir.symlink_to(self.root, target_is_directory=True)
        mutation = json.loads(json.dumps(original))
        mutation["files"][0]["path"] = "link/outside.json"
        self.write_json(self.manifest, mutation)
        self.rejected()
        self.write_json(self.manifest, original)

        evidence = self.root / "prd/migration/rust-evidence"
        for index, name in enumerate(PREDECESSORS):
            predecessor = evidence / name
            predecessor.write_bytes(predecessor.read_bytes() + b"\n")
            self.rejected()
            shutil.copy2(EVIDENCE / name, predecessor)

    def test_malformed_json_and_missing_inputs_fail_without_marker(self) -> None:
        self.census.write_text("{not-json", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S19_T01_CENSUS_OK", result.stdout)
        self.census.unlink()
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S19_T01_CENSUS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
