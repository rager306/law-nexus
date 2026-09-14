#!/usr/bin/env python3
"""Offline hostile-input tests for the M205/S03 FSM verifier."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "m205_s03_fsm.py"
CONTRACT = ROOT / "prd" / "architecture" / "m205-s03-context-fsm.yaml"
SUCCESS_MARKERS = ("S03_T01_FSM_OK", "S03_T01_BOUNDARIES_OK")


class FsmVerifierCliTests(unittest.TestCase):
    """Exercise the S03 verifier's successful and fail-closed CLI paths."""

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
        self.assertIn("S03 verifier: OK", result.stdout)

    def assert_fail_closed(self, result: subprocess.CompletedProcess[str]) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        for marker in SUCCESS_MARKERS:
            self.assertNotIn(marker, output)

    def write_fixture(self, directory: Path, name: str, content: str) -> str:
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return os.path.relpath(path, ROOT)

    def test_authoritative_contract_passes(self) -> None:
        self.assert_success(self.run_verifier("prd/architecture/m205-s03-context-fsm.yaml"))

    def test_absolute_traversal_and_backslash_paths_fail_closed(self) -> None:
        cases = (
            "/etc/passwd",
            "../etc/passwd",
            "prd/architecture/../m205-s03-context-fsm.yaml",
            "prd\\architecture\\m205-s03-context-fsm.yaml",
        )
        for input_path in cases:
            with self.subTest(input_path=input_path):
                self.assert_fail_closed(self.run_verifier(input_path))

    def test_symlink_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            target = directory_path / "valid.yaml"
            target.write_text(CONTRACT.read_text(encoding="utf-8"), encoding="utf-8")
            link = directory_path / "symlink.yaml"
            link.symlink_to(target)
            result = self.run_verifier(os.path.relpath(link, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("symlink path rejected", result.stderr)

    def test_duplicate_yaml_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            input_path = self.write_fixture(Path(directory), "duplicate.yaml", "a: 1\na: 2\n")
            result = self.run_verifier(input_path)
            self.assert_fail_closed(result)
            self.assertIn("duplicate YAML key", result.stderr)

    def test_merge_key_and_inline_alias_fail_closed(self) -> None:
        cases = {
            "merge.yaml": "base: {x: 1}\nvalue: {<<: *base}\n",
            "inline-alias.yaml": "base: &base [1, 2]\nvalue: [*base]\n",
        }
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            for name, content in cases.items():
                with self.subTest(name=name):
                    input_path = self.write_fixture(Path(directory), name, content)
                    self.assert_fail_closed(self.run_verifier(input_path))

    def test_malformed_yaml_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            input_path = self.write_fixture(
                Path(directory), "malformed.yaml", "value: [unterminated\n"
            )
            result = self.run_verifier(input_path)
            self.assert_fail_closed(result)
            self.assertIn("S03 verifier rejected input", result.stderr)

    def test_input_over_64_kib_fails_before_parse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "oversized.yaml"
            path.write_bytes(b"not: [valid yaml\n" + b"x" * (64 * 1024))
            result = self.run_verifier(os.path.relpath(path, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("byte limit", result.stderr)


if __name__ == "__main__":
    unittest.main()
