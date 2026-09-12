#!/usr/bin/env python3
"""Adversarial subprocess contracts for the M204 S17 frozen census CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s17_loop_note.py")
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
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s17-")
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

    def check_rejected(self, *, census: dict | None = None, manifest: dict | None = None) -> None:
        if census is not None:
            self.write_json(self.census, census)
        if manifest is not None:
            self.write_json(self.manifest, manifest)
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_positive_control_is_subprocess_only_and_worktree_independent(self) -> None:
        result = invoke(self.root, self.census, self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S17_T01_CENSUS_OK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

    def test_rejects_abort_count_shape_order_duplicate_and_forged_third_abort(self) -> None:
        original = self.read_json(self.census)
        third = {**original["aborts"][1], "ordinal": 3, "flow_id": "forged-third"}
        mutations = (
            ("count", {**original, "abort_count": 3}),
            ("missing", {**original, "aborts": original["aborts"][:1]}),
            ("extra", {**original, "aborts": [*original["aborts"], third]}),
            ("unordered", {**original, "aborts": list(reversed(original["aborts"]))}),
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
                self.check_rejected(census=mutation)
                self.write_json(self.census, original)

    def test_rejects_intercept_misclassification_and_predispatch_claims(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("kind", "no-artifact"),
            ("journal_unit_start_present", True),
            ("interrupted", False),
            ("tool_calls", 1),
            ("classify_status", "running"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                mutation = json.loads(json.dumps(original))
                mutation["intercept"][key] = value
                self.check_rejected(census=mutation)
                self.write_json(self.census, original)

    def test_rejects_abort_status_and_exact_engine_messages(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("unit_end_status", "validated"),
            ("finalize_status", "done"),
            ("iteration_end_reason", "retry"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                mutation = json.loads(json.dumps(original))
                mutation["aborts"][0][key] = value
                self.check_rejected(census=mutation)
                self.write_json(self.census, original)
        for key, value in (
            ("sql_abort_message", "truncated SQL"),
            ("trigger_name", "other_trigger"),
        ):
            with self.subTest(key=key):
                mutation = {**original, key: value}
                self.check_rejected(census=mutation)
                self.write_json(self.census, original)

    def test_rejects_fixed_or_promoted_lifecycle_claims(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("s17_called_validate_milestone", True),
            ("law_nexus_fixable", True),
            ("engine_fix", "fixed"),
            ("upstream_issue", "filed"),
            ("retry_substitute", True),
            ("same_defect_as_s09", False),
            ("s12_hard_block_stopped_dispatch", True),
            ("s16_census_stopped_dispatch", True),
            ("validation_projection_present", True),
            ("c4_acceptance", "pass"),
            ("status_effect", "validated"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                mutation = {**original, key: value}
                self.check_rejected(census=mutation)
                self.write_json(self.census, original)

    def test_rejects_closed_schema_duplicates_and_integer_boolean_confusion(self) -> None:
        original = self.read_json(self.census)
        mutation = {**original, "unexpected": None}
        self.check_rejected(census=mutation)
        self.write_json(self.census, original)
        raw = self.census.read_text(encoding="utf-8")
        self.census.write_text(
            raw.replace('"abort_count": 2', '"abort_count": 2,\n  "abort_count": 2'),
            encoding="utf-8",
        )
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate JSON key", result.stderr)
        self.write_json(self.census, original)
        original_manifest = self.read_json(self.manifest)
        for path, field in ((self.census, "abort_count"), (self.manifest, "files")):
            value = self.read_json(path)
            if field == "abort_count":
                value[field] = True
            else:
                value[field][0]["size_bytes"] = True
            self.check_rejected(
                census=value if path == self.census else None,
                manifest=value if path == self.manifest else None,
            )
            if path == self.census:
                self.write_json(self.census, original)
            else:
                self.write_json(self.manifest, original_manifest)

    def test_rejects_unsafe_paths_symlinks_and_tampered_pins(self) -> None:
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
        self.write_json(self.manifest, original)
        predecessor = self.root / "prd/migration/rust-evidence" / PREDECESSORS[0]
        predecessor.write_text(predecessor.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest pin drift", result.stderr)

    def test_rejects_manifest_pin_substitution_and_intercept_timestamp_or_pid_drift(self) -> None:
        original = self.read_json(self.manifest)
        mutation = json.loads(json.dumps(original))
        mutation["files"] = list(reversed(mutation["files"]))
        self.check_rejected(manifest=mutation)
        self.write_json(self.manifest, original)
        census = self.read_json(self.census)
        for key, value in (("query_at", "2026-09-12T17:22:08"), ("headless_pid", 1000787)):
            with self.subTest(key=key):
                changed = json.loads(json.dumps(census))
                changed["intercept"][key] = value
                self.check_rejected(census=changed)
                self.write_json(self.census, census)

    def test_malformed_json_and_missing_inputs_fail_within_bounded_timeout(self) -> None:
        self.census.write_text("{not-json", encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expecting property name", result.stderr)
        self.census.unlink()
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
