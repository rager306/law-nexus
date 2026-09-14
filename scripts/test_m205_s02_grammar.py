#!/usr/bin/env python3
"""Standalone offline tests for the M205/S02 grammar verifier."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "m205_s02_grammar.py"
CONTRACT = ROOT / "prd" / "architecture" / "m205-s02-pre-capture-grammar.yaml"
SUCCESS_MARKERS = ("S02_T01_GRAMMAR_OK", "S02_T01_BOUNDARIES_OK")


class GrammarVerifierCliTests(unittest.TestCase):
    """Exercise the verifier's success and fail-closed CLI surface."""

    def run_verifier(
        self, input_path: str, *, root: Path = ROOT
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                "--root",
                str(root),
                "--input",
                input_path,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        for marker in SUCCESS_MARKERS:
            self.assertIn(marker, result.stdout)

    def assert_fail_closed(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        for marker in SUCCESS_MARKERS:
            self.assertNotIn(marker, result.stdout)
            self.assertNotIn(marker, result.stderr)

    def test_authoritative_contract_passes(self) -> None:
        result = self.run_verifier("prd/architecture/m205-s02-pre-capture-grammar.yaml")
        self.assert_success(result)

    def test_duplicate_yaml_key_fails_without_success_markers(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text("a: 1\na: 2\n", encoding="utf-8")
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("duplicate YAML key", result.stderr)

    def test_yaml_alias_bomb_fails_without_expanding(self) -> None:
        alias_yaml = "base: &base [1, 2, 3]\n" + "\n".join(
            f"alias_{index}: *base" for index in range(100)
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "alias-bomb.yaml"
            path.write_text(alias_yaml, encoding="utf-8")
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("top-level keys drift", result.stderr)

    def test_byte_cap_is_checked_before_yaml_parse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "oversized.yaml"
            path.write_bytes(b"not: [valid yaml\n" + b"x" * (64 * 1024))
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("byte limit", result.stderr)

    def test_traversal_absolute_and_backslash_paths_fail_closed(self) -> None:
        cases = (
            "../etc/passwd",
            str(Path(tempfile.gettempdir()) / "outside.yaml"),
            "scripts\\x.yaml",
        )
        for input_path in cases:
            with self.subTest(input_path=input_path):
                self.assert_fail_closed(self.run_verifier(input_path))

    def test_symlink_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            target = directory_path / "valid.yaml"
            target.write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")
            link = directory_path / "symlink.yaml"
            link.symlink_to(target)
            result = self.run_verifier(os.path.relpath(link, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("symlink path rejected", result.stderr)

    def test_wrong_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "wrong-schema.yaml"
            path.write_text("schema: wrong\n", encoding="utf-8")
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("top-level keys drift", result.stderr)

    def test_policy_drift_fails_closed(self) -> None:
        contract = CONTRACT.read_text(encoding="utf-8")
        drifted = contract.replace("runtime_stop_active: true", "runtime_stop_active: false", 1)
        self.assertNotEqual(contract, drifted)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "policy-drift.yaml"
            path.write_text(drifted, encoding="utf-8")
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("dependency or runtime-stop pin drift", result.stderr)


if __name__ == "__main__":
    unittest.main()
