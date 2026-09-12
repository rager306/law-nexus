#!/usr/bin/env python3
"""Independent subprocess adversarial contracts for the M204 S18 census CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s18_loop_note.py")
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


class S18ValidateLoopSubprocessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s18-")
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
        self.assertNotIn("S18_T01_CENSUS_OK", result.stdout)
        return result

    def test_positive_control_is_subprocess_only_and_bounded(self) -> None:
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S18_T01_CENSUS_OK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

    def test_rejects_abort_count_shape_order_duplicate_and_third_abort(self) -> None:
        original = self.read_json(self.census)
        third = {**original["aborts"][1], "ordinal": 3, "flow_id": "forged-third"}
        mutations = (
            ("wrong-count", {**original, "abort_count": 3}),
            ("missing-row", {**original, "aborts": original["aborts"][:1]}),
            ("extra-row", {**original, "aborts": [*original["aborts"], third]}),
            ("reordered", {**original, "aborts": list(reversed(original["aborts"]))}),
            (
                "duplicate-flow",
                {
                    **original,
                    "aborts": [
                        original["aborts"][0],
                        {**original["aborts"][1], "flow_id": original["aborts"][0]["flow_id"]},
                    ],
                },
            ),
        )
        for name, mutation in mutations:
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_intercept_as_abort_and_forged_post_research_abort(self) -> None:
        original = self.read_json(self.census)
        for name, mutation in (
            (
                "intercept-as-third-abort",
                {**original, "aborts": [*original["aborts"], original["intercept"]]},
            ),
            (
                "forged-after-research-start",
                {
                    **original,
                    "aborts": [
                        original["aborts"][0],
                        {**original["aborts"][1], "unit_start_at": "2026-09-12T19:02:00Z"},
                    ],
                },
            ),
        ):
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_intercept_kind_status_and_dispatch_claims(self) -> None:
        original = self.read_json(self.census)
        for key, value in (
            ("kind", "no-artifact"),
            ("classify_status", "running"),
            ("interrupted", False),
            ("tool_calls", 1),
            ("journal_unit_start_present", True),
            ("query_at", "2026-09-12T17:22:08Z"),
            ("headless_pid", 1130972),
            ("next_unit_type", "validate-milestone"),
        ):
            with self.subTest(key=key):
                mutation = json.loads(json.dumps(original))
                mutation["intercept"][key] = value
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_exact_status_sql_and_trigger_strings(self) -> None:
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
                mutation = {**original, key: value}
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_every_promotion_flag_and_extra_classifier_claim(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("s17_census_stopped_dispatch", True),
            ("s18_called_validate_milestone", True),
            ("validation_projection_present", True),
            ("engine_fix", "fixed"),
            ("law_nexus_fixable", True),
            ("upstream_issue", "filed"),
            ("c4_acceptance", "pass"),
            ("status_effect", "validated"),
            ("status_effect", "advanced"),
            ("status_effect", "closed"),
            ("classification", "canonical-validation"),
            ("class_matched_ids", ["R001"]),
        )
        for key, value in changes:
            with self.subTest(key=key, value=value):
                mutation = {**original, key: value}
                self.write_json(self.census, mutation)
                self.rejected()
                self.write_json(self.census, original)

    def test_rejects_closed_schema_duplicate_keys_and_bool_as_int(self) -> None:
        original = self.read_json(self.census)
        self.write_json(self.census, {**original, "unexpected": None})
        self.rejected()
        self.write_json(self.census, original)
        raw = self.census.read_text(encoding="utf-8")
        self.census.write_text(
            raw.replace('"abort_count": 2', '"abort_count": 2,\n  "abort_count": 2'),
            encoding="utf-8",
        )
        result = self.rejected()
        self.assertIn("duplicate JSON key", result.stderr)
        self.write_json(self.census, original)
        original_manifest = self.read_json(self.manifest)
        self.write_json(self.census, {**original, "abort_count": True})
        self.rejected()
        self.write_json(self.census, original)
        manifest = json.loads(json.dumps(original_manifest))
        manifest["files"][0]["size_bytes"] = True
        self.write_json(self.manifest, manifest)
        self.rejected()
        self.write_json(self.manifest, original_manifest)

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
        for index in range(len(PREDECESSORS)):
            predecessor = evidence / PREDECESSORS[index]
            predecessor.write_bytes(predecessor.read_bytes() + b"\n")
            self.rejected()
            shutil.copy2(EVIDENCE / PREDECESSORS[index], predecessor)

    def test_malformed_json_and_missing_inputs_fail_within_timeout(self) -> None:
        self.census.write_text("{not-json", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S18_T01_CENSUS_OK", result.stdout)
        self.census.unlink()
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
