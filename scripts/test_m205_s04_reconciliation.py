#!/usr/bin/env python3
"""Offline adversarial tests for the M205/S04 reconciliation verifier."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "m205_s04_reconciliation.py"
PIN = ROOT / "prd/architecture/m205-s04-docs-reconciliation.yaml"
MARKERS = ("S04_T01_RECONCILIATION_OK", "S04_T01_BOUNDARIES_OK")
BINDING_PREFIX = "  - {path: prd/architecture/m205-s01-pullenti-matrix.yaml"


class ReconciliationVerifierCliTests(unittest.TestCase):
    """Exercise the real CLI, including hostile and semantic fail-closed paths."""

    def run_cli(
        self, input_path: str, *, root: Path = ROOT, check_docs: bool = False
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VERIFIER),
            "check",
            "--root",
            str(root),
            "--input",
            input_path,
        ]
        if check_docs:
            command.append("--check-docs")
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=10
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S04 verifier: OK", result.stdout)

    def assert_fail_closed(self, result: subprocess.CompletedProcess[str]) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        for marker in MARKERS:
            self.assertNotIn(marker, output)

    def write_fixture(self, directory: Path, name: str, content: str) -> str:
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return os.path.relpath(path, ROOT)

    def mutate(self, directory: Path, name: str, old: str, new: str) -> str:
        content = PIN.read_text(encoding="utf-8")
        self.assertIn(old, content, f"fixture anchor missing: {old!r}")
        return self.write_fixture(directory, name, content.replace(old, new, 1))

    def test_authoritative_pin_passes(self) -> None:
        self.assert_success(self.run_cli("prd/architecture/m205-s04-docs-reconciliation.yaml"))

    def test_path_and_filesystem_boundaries_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            valid = directory_path / "valid.yaml"
            shutil.copyfile(PIN, valid)
            link = directory_path / "link.yaml"
            link.symlink_to(valid)
            for input_path in (
                "/etc/passwd",
                "../etc/passwd",
                "prd/architecture/../m205-s04-docs-reconciliation.yaml",
                "prd\\architecture\\m205-s04-docs-reconciliation.yaml",
                os.path.relpath(link, ROOT),
            ):
                with self.subTest(input_path=input_path):
                    self.assert_fail_closed(self.run_cli(input_path))

            directory_input = directory_path / "directory.yaml"
            directory_input.mkdir()
            self.assert_fail_closed(self.run_cli(os.path.relpath(directory_input, ROOT)))

    def test_yaml_parser_hostiles_fail_closed(self) -> None:
        cases = {
            "duplicate.yaml": "a: 1\na: 2\n",
            "merge.yaml": "base: {x: 1}\nvalue: {<<: *base}\n",
            "alias.yaml": "base: &base [1, 2]\nvalue: [*base]\n",
            "malformed.yaml": "value: [unterminated\n",
        }
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            for name, content in cases.items():
                with self.subTest(name=name):
                    self.assert_fail_closed(
                        self.run_cli(self.write_fixture(directory_path, name, content))
                    )
            invalid = directory_path / "invalid-utf8.yaml"
            invalid.write_bytes(b"schema: \xff\n")
            self.assert_fail_closed(self.run_cli(os.path.relpath(invalid, ROOT)))
            oversized = directory_path / "oversized.yaml"
            oversized.write_bytes(b"x" * (64 * 1024 + 1))
            result = self.run_cli(os.path.relpath(oversized, ROOT))
            self.assert_fail_closed(result)
            self.assertIn("byte limit", result.stderr)

    def test_unknown_nested_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            for old, new in (
                (
                    "rc28: {primary: [F19], boundary_only: [F18], disposition: open}",
                    "rc28: {primary: [F19], boundary_only: [F18], disposition: open, extra: true}",
                ),
                ("runtime_stop_active: true", "runtime_stop_active: true\nextra_root: true"),
                ("take_or_leave: leave", "take_or_leave: leave\n    extra: true"),
            ):
                with self.subTest(new=new):
                    path = self.mutate(directory_path, "unknown.yaml", old, new)
                    self.assert_fail_closed(self.run_cli(path))

    def test_semantic_non_promotion_mutations_fail_closed(self) -> None:
        mutations = (
            ("authoritative: false", "authoritative: true"),
            ("runtime_stop_active: true", "runtime_stop_active: false"),
            ("human_adoption: pending", "human_adoption: accepted"),
            ("p9_status: not-s04-after-this/deferred-to-later", "p9_status: emitted-by-s04"),
            ("s04_owns_p9: false", "s04_owns_p9: true"),
            ("resolved_is_not_sufficient: true", "resolved_is_not_sufficient: false"),
            ("merge_forbidden: true", "merge_forbidden: false"),
            ("g02_status: already-wired-do-not-implement-twice", "g02_status: rewire"),
            ("G15, G16]", "G14, G16]"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            for index, (old, new) in enumerate(mutations):
                with self.subTest(old=old):
                    path = self.mutate(directory_path, f"semantic-{index}.yaml", old, new)
                    self.assert_fail_closed(self.run_cli(path))

    def test_source_binding_tamper_and_missing_diagnostic_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory_path = Path(directory)
            path = self.mutate(
                directory_path,
                "tampered.yaml",
                BINDING_PREFIX,
                "  - {path: prd/architecture/m205-s02-pre-capture-grammar.yaml",
            )
            result = self.run_cli(path)
            self.assert_fail_closed(result)
            self.assertIn("source hash drift", result.stderr)

    def test_check_docs_fixture_requires_meaning_bearing_companions(self) -> None:
        companions = (
            "doc/adr/0028-typed-lexer-legal-marker-lexicon.md",
            "prd/ARCHITECTURE.md",
            "doc/adr/README.md",
            "doc/adr-architecture-cross-matrix.md",
            "prd/architecture/review-cases/rc28-remediation-program.md",
            ".agents/skills/law-nexus-rust/references/verification-matrix.md",
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fixture_root = Path(directory)
            (fixture_root / "prd/architecture").mkdir(parents=True)
            (fixture_root / "prd/migration/rust-evidence").mkdir(parents=True)
            sources = []
            for row in PIN.read_text(encoding="utf-8").splitlines():
                if "path: " in row and ", sha256:" in row:
                    sources.append(row.split("path: ", 1)[1].split(", sha256:", 1)[0])
            for source in sorted(set(sources)):
                target = fixture_root / source
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / source, target)
            pin_target = fixture_root / "prd/architecture/m205-s04-docs-reconciliation.yaml"
            shutil.copyfile(PIN, pin_target)
            fixture_text = {
                companions[
                    0
                ]: "m205-s04-docs-reconciliation/v1 D459 human_adoption runtime_stop G15 P9 F19",
                companions[1]: "m205-s04-docs-reconciliation/v1 ADR-0028 [proposed] G02 P9 F19",
                companions[2]: "m205-s04-docs-reconciliation/v1 D459 G02 already-wired P9",
                companions[3]: "m205-s04-docs-reconciliation/v1 design-only G02 P9 F19",
                companions[
                    4
                ]: "m205-s04-docs-reconciliation/v1 G02 already-wired P9 not-s04-after-this F19",
                companions[
                    5
                ]: "design-only offline fail-closed verifier adversarial hashed closeout ADR conformance non-claims",
            }
            for companion in companions:
                target = fixture_root / companion
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(fixture_text[companion], encoding="utf-8")
            self.assert_success(
                self.run_cli(
                    "prd/architecture/m205-s04-docs-reconciliation.yaml",
                    root=fixture_root,
                    check_docs=True,
                )
            )
            (fixture_root / companions[0]).write_text("G02 only", encoding="utf-8")
            result = self.run_cli(
                "prd/architecture/m205-s04-docs-reconciliation.yaml",
                root=fixture_root,
                check_docs=True,
            )
            self.assert_fail_closed(result)


if __name__ == "__main__":
    unittest.main()
