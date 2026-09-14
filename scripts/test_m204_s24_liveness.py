#!/usr/bin/env python3
"""Independent subprocess contracts for the M204/S24 criterion-resolution packet.

The suite deliberately invokes each consumer as a CLI.  Temporary repository
fixtures make all mutation tests write outside tracked paths; no checker is
imported as the expected-value oracle.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
S24 = ROOT / "scripts/m204_s24_liveness.py"
S23 = ROOT / "scripts/m204_s23_c4_run.py"
S15 = ROOT / "scripts/m204_s15_requirement_class.py"
S22 = ROOT / "scripts/m204_s22_liveness.py"
S14 = ROOT / "scripts/m204_s14_polarity.py"
PARSER = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"
BINARY = ROOT / "target/debug/npa-contour-diagnostics"

LEDGER_REL = "prd/migration/rust-evidence/m204-s24-criterion-resolution.json"
MANIFEST_REL = "prd/migration/rust-evidence/m204-s24-frozen-hashes.json"
V2_REL = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json"
HISTORICAL_REL = "prd/migration/rust-evidence/m204-s23-c4-operational-receipt.json"


def run(command: list[str], cwd: Path, timeout: float = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False
    )


class S24CriterionResolutionContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s24-")
        self.root = Path(self.temp.name)
        shutil.copytree(EVIDENCE, self.root / "prd/migration/rust-evidence")
        (self.root / LEDGER_REL).unlink(missing_ok=True)
        (self.root / MANIFEST_REL).unlink(missing_ok=True)
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(S24, self.root / "scripts/m204_s24_liveness.py")
        shutil.copy2(S23, self.root / "scripts/m204_s23_c4_run.py")
        shutil.copy2(S15, self.root / "scripts/m204_s15_requirement_class.py")
        shutil.copy2(S14, self.root / "scripts/m204_s14_polarity.py")
        (self.root / "crates/ln-consultant-parser/src").mkdir(parents=True)
        shutil.copy2(PARSER, self.root / "crates/ln-consultant-parser/src/contour_diagnostics.rs")
        (self.root / "prd/architecture").mkdir(parents=True)
        shutil.copy2(CONTRACT, self.root / "prd/architecture/npa-acceptance-contract.yaml")
        binary = self.root / "target/debug/npa-contour-diagnostics"
        binary.parent.mkdir(parents=True)
        shutil.copy2(BINARY, binary)
        self.ledger = self.root / LEDGER_REL
        self.manifest = self.root / MANIFEST_REL
        composed = run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s24_liveness.py"),
                "compose",
                "--root",
                str(self.root),
                "--packet",
                str(self.ledger),
                "--manifest",
                str(self.manifest),
            ],
            ROOT,
            timeout=10,
        )
        self.assertEqual(composed.returncode, 0, composed.stderr)
        self.original_ledger = self.ledger.read_bytes()
        self.original_manifest = self.manifest.read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def s24_check(self, timeout: float = 20) -> subprocess.CompletedProcess[str]:
        return run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s24_liveness.py"),
                "check",
                "--root",
                str(self.root),
                "--packet",
                str(self.ledger),
                "--manifest",
                str(self.manifest),
            ],
            ROOT,
            timeout,
        )

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def restore(self) -> None:
        self.ledger.write_bytes(self.original_ledger)
        self.manifest.write_bytes(self.original_manifest)

    def rejected(self) -> subprocess.CompletedProcess[str]:
        result = self.s24_check()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("S24_T01_CRITERION_OK", result.stdout)
        return result

    def test_positive_roundtrip_and_independent_consumers(self) -> None:
        result = self.s24_check(timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["S24_T01_CRITERION_OK"])
        ledger = self.read(self.ledger)
        self.assertEqual(ledger["path"], "criterion-resolution")
        self.assertEqual(ledger["gsd_recovery_liveness"], "blocked-external")
        self.assertEqual(ledger["c4_operational_acceptance"], "pass")
        self.assertEqual(ledger["classification"], "supporting-only")
        self.assertFalse(ledger["s24_called_validate_milestone"])

        s23 = run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s23_c4_run.py"),
                "--verify-receipt",
                V2_REL,
            ],
            self.root,
        )
        self.assertEqual(s23.returncode, 0, s23.stderr)
        self.assertIn('"operational_acceptance": "pass"', s23.stdout)
        historical = run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s23_c4_run.py"),
                "--verify-receipt",
                HISTORICAL_REL,
            ],
            self.root,
        )
        self.assertEqual(historical.returncode, 0, historical.stderr)
        self.assertIn('"operational_acceptance": "non-pass"', historical.stdout)

        s15 = run([sys.executable, str(S15), "classify"], ROOT)
        self.assertEqual(s15.returncode, 0, s15.stderr)
        self.assertEqual(json.loads(s15.stdout)["class_matched_ids"], [])

        s22 = run([sys.executable, str(S22), "check"], ROOT)
        self.assertEqual(s22.returncode, 0, s22.stderr)
        self.assertIn("S22_T01_BLOCKER_OK", s22.stdout)
        blocker = json.loads(
            (ROOT / "prd/migration/rust-evidence/m204-s22-external-blocker.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(blocker["gsd_recovery_liveness"], "blocked-external")
        self.assertEqual(blocker["c4_operational_acceptance"], "non-pass")

    def test_rejects_all_promotion_and_scope_mutations(self) -> None:
        original = self.read(self.ledger)
        mutations = {
            "path": "passing-recovery",
            "gsd_recovery_liveness": "passing",
            "engine_fix": "fixed",
            "law_nexus_fixable": True,
            "upstream_issue": "filed",
            "local_overlay_preserve_patch": "engine-fix",
            "in_tree_engine_source": True,
            "s24_called_validate_milestone": True,
            "retry_substitute": True,
            "validation_projection_present": True,
            "s23_status": "complete",
            "status_effect": "closed",
            "full_corpus_walk_in_slice": True,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                mutated = copy.deepcopy(original)
                mutated[key] = value
                self.write(self.ledger, mutated)
                self.rejected()
                self.restore()

    def test_rejects_reused_predecessor_schemas(self) -> None:
        original = self.read(self.ledger)
        for schema in (
            "law-nexus/m204-s22-external-blocker/v1",
            "law-nexus/m204-s23-c4-operational-receipt/v1",
        ):
            with self.subTest(schema=schema):
                mutated = copy.deepcopy(original)
                mutated["schema"] = schema
                self.write(self.ledger, mutated)
                self.rejected()
                self.restore()

    def test_rejects_unknown_requirement_and_census_fields(self) -> None:
        original = self.read(self.ledger)
        for key, value in {
            "requirement_ids": ["R035"],
            "abort_count": 1,
            "dispatch_count": 1,
            "unexpected": None,
        }.items():
            with self.subTest(key=key):
                mutated = {**original, key: value}
                self.write(self.ledger, mutated)
                self.rejected()
                self.restore()

    def test_rejects_receipt_polarity_and_historical_laundry(self) -> None:
        original = self.read(self.ledger)
        no_v2_pin = copy.deepcopy(original)
        no_v2_pin["c4_pass_receipt"] = HISTORICAL_REL
        self.write(self.ledger, no_v2_pin)
        self.rejected()
        self.restore()

        historical_path = self.root / HISTORICAL_REL
        historical = self.read(historical_path)
        historical["observed_output"]["jsonl_valid"] = True
        self.write(historical_path, historical)
        self.rejected()
        self.restore()

        s10 = self.root / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
        s10_doc = self.read(s10)
        if "observed_output" in s10_doc:
            s10_doc["observed_output"]["jsonl_valid"] = True
        else:
            s10_doc["jsonl_valid"] = True
        self.write(s10, s10_doc)
        self.rejected()
        self.restore()

    def test_rejects_receipt_calibration_mutations(self) -> None:
        """A pinned receipt still has to be calibrated.

        Each mutation below is re-pinned in the manifest first, so the sha256 pin
        cannot be what rejects it: only S24's own independent calibration
        assertions can. The S23 verifier accepts all three mutated shapes, which
        is exactly why S24 may not rely on that verifier alone.
        """
        v2_path = self.root / V2_REL
        pristine = v2_path.read_bytes()
        cases = {
            "exit_code_false": lambda doc: doc["terminal"].__setitem__("exit_code", False),
            "jobs_eight": lambda doc: doc["c4_binding"].__setitem__("jobs", 8),
            "release_profile": lambda doc: doc.__setitem__("binary_profile", "release"),
        }
        for label, mutate in cases.items():
            receipt = self.read(v2_path)
            mutate(receipt)
            self.write(v2_path, receipt)
            manifest = self.read(self.manifest)
            payload = v2_path.read_bytes()
            for row in manifest["files"]:
                if row["path"] == V2_REL:
                    row["sha256"] = "sha256:" + hashlib.sha256(payload).hexdigest()
                    row["size_bytes"] = len(payload)
            self.write(self.manifest, manifest)
            result = self.s24_check()
            self.assertNotEqual(result.returncode, 0, f"{label} was accepted")
            self.assertNotIn("S24_T01_CRITERION_OK", result.stdout)
            v2_path.write_bytes(pristine)
            self.restore()

    def test_rejects_manifest_tampering_and_binding_mismatch(self) -> None:
        manifest = self.read(self.manifest)
        mutated = copy.deepcopy(manifest)
        mutated["files"][0]["sha256"] = "sha256:" + "f" * 64
        self.write(self.manifest, mutated)
        self.rejected()
        self.restore()

        historical_path = self.root / HISTORICAL_REL
        historical = self.read(historical_path)
        historical["observed_output"]["jsonl_valid"] = True
        self.write(historical_path, historical)
        result = run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s23_c4_run.py"),
                "--verify-receipt",
                HISTORICAL_REL,
                "--require-operational-pass",
            ],
            self.root,
        )
        self.assertNotEqual(result.returncode, 0)
        diagnostic = result.stdout + result.stderr
        self.assertTrue(diagnostic.strip())
        self.assertNotIn('"operational_acceptance": "pass"', diagnostic)

        v2_path = self.root / V2_REL
        v2 = self.read(v2_path)
        v2["observed_output"]["jsonl_valid"] = False
        self.write(v2_path, v2)
        result = self.s24_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S24_T01_CRITERION_OK", result.stdout)

    def test_rejects_unsafe_fixture_destination_without_writes(self) -> None:
        outside = self.root.parent / "m204-s24-outside.json"
        result = run(
            [
                sys.executable,
                str(self.root / "scripts/m204_s24_liveness.py"),
                "compose",
                "--root",
                str(self.root),
                "--packet",
                str(outside),
                "--manifest",
                str(self.manifest),
            ],
            ROOT,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
