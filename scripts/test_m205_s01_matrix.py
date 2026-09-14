#!/usr/bin/env python3
"""Adversarial subprocess tests for the M205/S01 design-only matrix verifier."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/m205_s01_matrix.py"
MATRIX = ROOT / "prd/architecture/m205-s01-pullenti-matrix.yaml"


def run_verifier(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", str(VERIFIER), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def load_matrix() -> dict[str, Any]:
    with MATRIX.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    assert isinstance(value, dict)
    return value


def write_fixture(root: Path, value: dict[str, Any]) -> str:
    path = root / "fixture.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return "fixture.yaml"


class MatrixAdversarialTests(unittest.TestCase):
    def assert_rejected(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        value = copy.deepcopy(load_matrix())
        mutate(value)
        with tempfile.TemporaryDirectory(prefix="m205-s01-adversarial-") as raw:
            root = Path(raw)
            relative = write_fixture(root, value)
            result = run_verifier("check", "--root", str(root), "--input", relative)
            self.assertNotEqual(
                result.returncode,
                0,
                msg=f"tamper unexpectedly accepted:\nstdout={result.stdout}\nstderr={result.stderr}",
            )

    def test_extra_top_level_key_is_rejected(self) -> None:
        self.assert_rejected(lambda value: value.update({"unexpected": True}))

    def test_extra_row_key_is_rejected(self) -> None:
        self.assert_rejected(lambda value: value["rows"][0].update({"unexpected": True}))

    def test_change_row_requires_pending_human_adoption(self) -> None:
        def mutate(value: dict[str, Any]) -> None:
            row = next(row for row in value["rows"] if row["family"] == "decree_change")
            row["human_adoption"] = "accepted"

        self.assert_rejected(mutate)

    def test_d457_wording_tension_record_is_required(self) -> None:
        def mutate(value: dict[str, Any]) -> None:
            value["non_claims"] = [
                item for item in value["non_claims"] if not item.startswith("D457/MEM1537")
            ]

        self.assert_rejected(mutate)

    def test_promotion_and_skip_washing_fields_are_rejected(self) -> None:
        cases: tuple[Callable[[dict[str, Any]], None], ...] = (
            lambda value: value.update({"passing-recovery": True}),
            lambda value: value.update({"engine_fix": "fixed"}),
            lambda value: value.update({"law_nexus_fixable": True}),
            lambda value: value.update({"s23_status": "complete"}),
            lambda value: value.update({"schema": "law-nexus/m205-s22/v1"}),
            lambda value: value.update({"schema": "law-nexus/m205-s23/v1"}),
            lambda value: value.update({"schema": "law-nexus/m205-s24/v1"}),
        )
        for mutate in cases:
            with self.subTest(mutate=mutate):
                self.assert_rejected(mutate)

    def test_norm_rule_and_force_surface_are_rejected(self) -> None:
        def norm_rule(value: dict[str, Any]) -> None:
            value["rows"][0]["law_nexus_surface"] = "NormRule"

        def force_field(value: dict[str, Any]) -> None:
            value["rows"][0]["force"] = True

        self.assert_rejected(norm_rule)
        self.assert_rejected(force_field)

    def test_vendor_import_is_absent_from_host_verifier(self) -> None:
        probe = (
            "from pathlib import Path; import re; "
            "text = Path('scripts/m205_s01_matrix.py').read_text(); "
            "match = re.search(r'(?m)^\\s*(?:from|import)\\s+pullenti\\b', text); "
            "raise SystemExit(1) if match else SystemExit(0)"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_compose_writes_only_requested_safe_temp_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m205-s01-compose-") as raw:
            root = Path(raw)
            source = root / "fixture.yaml"
            source.write_text(MATRIX.read_text(encoding="utf-8"), encoding="utf-8")
            output = "nested/copy.yaml"
            result = run_verifier(
                "compose", "--root", str(root), "--input", "fixture.yaml", "--output", output
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((root / output).is_file())
            self.assertFalse((ROOT / "nested/copy.yaml").exists())
            self.assertNotEqual((root / output).read_text(encoding="utf-8"), "")

    def test_compose_rejects_unsafe_output_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="m205-s01-output-") as raw:
            root = Path(raw)
            source = root / "fixture.yaml"
            source.write_text(MATRIX.read_text(encoding="utf-8"), encoding="utf-8")
            for output in ("../escaped.yaml", "/tmp/m205-escaped.yaml", "nested\\escaped.yaml"):
                with self.subTest(output=output):
                    result = run_verifier(
                        "compose",
                        "--root",
                        str(root),
                        "--input",
                        "fixture.yaml",
                        "--output",
                        output,
                    )
                    self.assertNotEqual(result.returncode, 0, msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
