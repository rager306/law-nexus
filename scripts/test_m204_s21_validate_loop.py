#!/usr/bin/env python3
"""Independent subprocess adversarial contracts for the M204 S21 census CLI."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s21_loop_note.py")
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
    "m204-s19-post-s18-validate-abort.json",
    "m204-s19-frozen-hashes.json",
    "m204-s20-post-s19-validate-loop.json",
    "m204-s20-frozen-hashes.json",
)
EXPECTED_ABORT_FLOWS = (
    "061fea44-c911-4578-b952-f123e3cf0319",
    "9f2369bd-5e43-406a-a9bd-555a895bebc6",
)
EXPECTED_CANCELLED_FLOWS = (
    "5c9ed6e5-06e7-4228-ac9a-0b7b9322ac29",
    "581f8dbe-b14f-4426-9b81-0cf5adc41ea4",
)
EXPECTED_PIN_COUNT = 16


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


class S21ValidateLoopSubprocessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s21-")
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
        self.original_census = self.census.read_bytes()
        self.original_manifest = self.manifest.read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def restore(self) -> None:
        self.census.write_bytes(self.original_census)
        self.manifest.write_bytes(self.original_manifest)

    def rejected(self) -> subprocess.CompletedProcess[str]:
        result = invoke(self.root, self.census, self.manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("S21_T01_CENSUS_OK", result.stdout)
        return result

    def test_positive_control_is_bounded_and_has_independent_mixed_counts(self) -> None:
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S21_T01_CENSUS_OK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

        census = self.read_json(self.census)
        self.assertEqual(census["dispatch_count"], 4)
        self.assertEqual(census["abort_count"], 2)
        self.assertEqual(census["cancelled_count"], 2)
        self.assertEqual(tuple(row["flow_id"] for row in census["aborts"]), EXPECTED_ABORT_FLOWS)
        self.assertEqual(
            tuple(row["flow_id"] for row in census["cancelled"]),
            EXPECTED_CANCELLED_FLOWS,
        )
        self.assertEqual(len(self.read_json(self.manifest)["files"]), EXPECTED_PIN_COUNT)
        self.assertFalse(census["law_nexus_fixable"])
        self.assertEqual(census["engine_fix"], "not_fixed")
        self.assertEqual(census["c4_acceptance"], "non-pass")
        self.assertFalse(census["retry_substitute"])

    def test_rejects_count_confusion_and_cancelled_as_aborts(self) -> None:
        original = self.read_json(self.census)
        cases = (
            ("abort-count-four", {**original, "abort_count": 4}),
            ("dispatch-count-three", {**original, "dispatch_count": 3}),
            ("dispatch-count-five", {**original, "dispatch_count": 5}),
            ("cancelled-count-zero", {**original, "cancelled_count": 0}),
            ("missing-cancelled", {**original, "cancelled": []}),
            (
                "cancelled-folded-into-aborts",
                {
                    **original,
                    "abort_count": 4,
                    "aborts": original["aborts"] + original["cancelled"],
                    "cancelled_count": 0,
                    "cancelled": [],
                },
            ),
            (
                "abort-folded-into-cancelled",
                {
                    **original,
                    "abort_count": 0,
                    "aborts": [],
                    "cancelled_count": 4,
                    "cancelled": original["cancelled"] + original["aborts"],
                },
            ),
        )
        for name, mutation in cases:
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.restore()

    def test_rejects_missing_or_fake_intercepts_and_cancelled_finalize(self) -> None:
        original = self.read_json(self.census)
        cases = []
        missing_start = copy.deepcopy(original)
        del missing_start["cancelled"][0]["journal_unit_start_present"]
        cases.append(("missing-cancelled-unit-start", missing_start))
        fake_intercept = copy.deepcopy(original)
        fake_intercept["cancelled"][0]["journal_unit_start_present"] = False
        fake_intercept["cancelled"][0]["unit_end_status"] = "intercept"
        cases.append(("fake-intercept", fake_intercept))
        injected_finalize = copy.deepcopy(original)
        injected_finalize["cancelled"][0]["finalize_status"] = "retry"
        cases.append(("finalize-in-cancelled", injected_finalize))
        cancelled_interrupted = copy.deepcopy(original)
        cancelled_interrupted["supervisor_exit"]["interrupted"] = True
        cases.append(("supervisor-interrupted", cancelled_interrupted))
        cancelled_classify = copy.deepcopy(original)
        cancelled_classify["supervisor_exit"]["classify_status"] = "cancelled"
        cases.append(("supervisor-classified-cancelled", cancelled_classify))
        for name, mutation in cases:
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.restore()

    def test_rejects_provider_category_strings_and_ordinal_flow_time_drift(self) -> None:
        original = self.read_json(self.census)
        mutations = []
        provider = copy.deepcopy(original)
        provider["cancelled"][0]["error_category"] = "sql"
        mutations.append(("provider-category-drift", provider))
        message = copy.deepcopy(original)
        message["cancelled"][0]["error_message"] = "Provider error: timeout."
        mutations.append(("provider-error-drift", message))
        ordinal = copy.deepcopy(original)
        ordinal["cancelled"][0]["ordinal"] = 2
        mutations.append(("duplicate-cancelled-ordinal", ordinal))
        flow = copy.deepcopy(original)
        flow["aborts"][1]["flow_id"] = EXPECTED_ABORT_FLOWS[0]
        mutations.append(("duplicate-dispatch-flow", flow))
        time_drift = copy.deepcopy(original)
        time_drift["aborts"][0]["unit_start_at"] = "2026-09-13T02:35:23.836Z"
        mutations.append(("abort-time-drift", time_drift))
        bind = copy.deepcopy(original)
        bind["supervisor_exit"]["headless_pid"] = "dispatch-3"
        mutations.append(("supervisor-bound-to-dispatch-three", bind))
        for name, mutation in mutations:
            with self.subTest(name=name):
                self.write_json(self.census, mutation)
                self.rejected()
                self.restore()

    def test_rejects_promotion_and_stop_retry_claims(self) -> None:
        original = self.read_json(self.census)
        changes = (
            ("law_nexus_fixable", True),
            ("engine_fix", "fixed"),
            ("c4_acceptance", "pass"),
            ("classification", "canonical-validation"),
            ("status_effect", "validated"),
            ("s21_called_validate_milestone", True),
            ("validation_projection_present", True),
            ("retry_substitute", True),
            ("supervisor_exit", {**original["supervisor_exit"], "closeout_n": 4}),
            (
                "supervisor_exit",
                {
                    **original["supervisor_exit"],
                    "stop_text": "closeout break not recovering after 2 retries",
                },
            ),
        )
        for key, value in changes:
            with self.subTest(key=key):
                mutation = copy.deepcopy(original)
                if key == "supervisor_exit":
                    mutation[key] = value
                else:
                    mutation[key] = value
                self.write_json(self.census, mutation)
                self.rejected()
                self.restore()

    def test_rejects_closed_schema_duplicates_and_bool_integer_confusion(self) -> None:
        original = self.read_json(self.census)
        extra = {**original, "unexpected": None}
        self.write_json(self.census, extra)
        self.rejected()
        self.restore()

        raw = self.census.read_text(encoding="utf-8")
        self.census.write_text(
            raw.replace(
                '"dispatch_count": 4',
                '"dispatch_count": 4,\n  "dispatch_count": 4',
                1,
            ),
            encoding="utf-8",
        )
        result = self.rejected()
        self.assertIn("duplicate JSON key", result.stderr)
        self.restore()

        for path, value in (
            (("dispatch_count",), True),
            (("abort_count",), False),
            (("cancelled", 0, "artifact_verified"), 0),
            (("supervisor_exit", "tool_calls"), False),
        ):
            with self.subTest(path=path, value=value):
                mutation = copy.deepcopy(original)
                target = mutation
                for part in path[:-1]:
                    target = target[part] if not isinstance(part, int) else target[part]
                target[path[-1]] = value
                self.write_json(self.census, mutation)
                self.rejected()
                self.restore()

    def test_rejects_pin_order_shape_and_self_hash(self) -> None:
        original = self.read_json(self.manifest)
        cases = []
        reordered = copy.deepcopy(original)
        reordered["files"][0], reordered["files"][1] = (
            reordered["files"][1],
            reordered["files"][0],
        )
        cases.append(("reordered-pins", reordered))
        missing = copy.deepcopy(original)
        missing["files"] = missing["files"][:-1]
        cases.append(("missing-pin", missing))
        extra = copy.deepcopy(original)
        extra["files"].append(copy.deepcopy(extra["files"][-1]))
        cases.append(("extra-pin", extra))
        self_hash = copy.deepcopy(original)
        self_hash["files"].append(
            {
                "path": "prd/migration/rust-evidence/manifest.json",
                "sha256": "sha256:" + "0" * 64,
                "size_bytes": 1,
            }
        )
        cases.append(("self-hash", self_hash))
        for name, mutation in cases:
            with self.subTest(name=name):
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.restore()

    def test_rejects_hash_size_drift_and_unsafe_paths_without_mutating_inputs(self) -> None:
        original_manifest = self.read_json(self.manifest)
        predecessor = self.root / "prd/migration/rust-evidence" / PREDECESSORS[0]
        predecessor_before = predecessor.read_bytes()
        census_before = self.census.read_bytes()
        manifest_before = self.manifest.read_bytes()

        for name, mutation in (
            (
                "hash-drift",
                {
                    **original_manifest,
                    "files": [
                        {**original_manifest["files"][0], "sha256": "sha256:" + "f" * 64},
                        *original_manifest["files"][1:],
                    ],
                },
            ),
            (
                "size-drift",
                {
                    **original_manifest,
                    "files": [
                        {**original_manifest["files"][0], "size_bytes": 1},
                        *original_manifest["files"][1:],
                    ],
                },
            ),
        ):
            with self.subTest(name=name):
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.restore()

        for path in ("/tmp/escape", "../escape", "x\\escape", ".gsd/secret"):
            with self.subTest(path=path):
                mutation = copy.deepcopy(original_manifest)
                mutation["files"][0]["path"] = path
                self.write_json(self.manifest, mutation)
                self.rejected()
                self.restore()

        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        mutation = copy.deepcopy(original_manifest)
        mutation["files"][0]["path"] = "link/outside.json"
        self.write_json(self.manifest, mutation)
        self.rejected()
        self.restore()

        self.assertEqual(predecessor.read_bytes(), predecessor_before)
        self.assertEqual(self.census.read_bytes(), census_before)
        self.assertEqual(self.manifest.read_bytes(), manifest_before)

    def test_malformed_json_and_missing_inputs_fail_closed(self) -> None:
        self.census.write_text('{"dispatch_count": 4', encoding="utf-8")
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S21_T01_CENSUS_OK", result.stdout)
        self.restore()

        self.census.unlink()
        result = invoke(self.root, self.census, self.manifest, timeout=2.0)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S21_T01_CENSUS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
