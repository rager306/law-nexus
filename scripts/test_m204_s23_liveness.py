#!/usr/bin/env python3
"""Independent subprocess contracts for the S23 external blocker proof."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("m204_s23_liveness.py")
ROOT = SCRIPT.parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
PACKET = "packet.json"
MANIFEST = "manifest.json"
FILES = (
    "m204-s09-gsd-validate-deadlock.json",
    "m204-s09-trigger-sql.json",
    "m204-s21-post-s20-validate-loop.json",
    "m204-s22-frozen-hashes.json",
)


def invoke(
    root: Path, packet: Path, manifest: Path, command: str = "check"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            command,
            "--root",
            str(root),
            "--packet",
            str(packet),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )


class S23LivenessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m204-s23-")
        self.root = Path(self.temp.name)
        evidence = self.root / "prd/migration/rust-evidence"
        evidence.mkdir(parents=True)
        for name in FILES:
            shutil.copy2(EVIDENCE / name, evidence / name)
        self.packet = evidence / PACKET
        self.manifest = evidence / MANIFEST
        result = invoke(self.root, self.packet, self.manifest, "compose")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet_bytes = self.packet.read_bytes()
        self.manifest_bytes = self.manifest.read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def restore(self) -> None:
        self.packet.write_bytes(self.packet_bytes)
        self.manifest.write_bytes(self.manifest_bytes)

    def rejected(self) -> subprocess.CompletedProcess[str]:
        result = invoke(self.root, self.packet, self.manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("S23_T03_BLOCKER_PROOF_OK", result.stdout)
        return result

    def test_truthful_packet_passes_and_is_supporting_only(self) -> None:
        result = invoke(self.root, self.packet, self.manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(), ["S23_T03_BLOCKER_PROOF_OK", "S23_T03_EXTERNAL_BOUNDARY_OK"]
        )
        packet = self.read(self.packet)
        self.assertEqual(packet["gsd_recovery_liveness"], "blocked-external")
        self.assertEqual(packet["disposition"], "needs-remediation")
        self.assertFalse(packet["s23_called_validate_milestone"])
        self.assertEqual(packet["classification"], "supporting-only")
        self.assertEqual(packet["status_effect"], "unchanged")

    def test_compose_never_overwrites_existing_outputs(self) -> None:
        result = invoke(self.root, self.packet, self.manifest, "compose")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing destination", result.stderr)
        self.assertEqual(self.packet.read_bytes(), self.packet_bytes)
        self.assertEqual(self.manifest.read_bytes(), self.manifest_bytes)

    def test_rejects_invented_owner_resolution_and_recovery_promotion(self) -> None:
        original = self.read(self.packet)
        mutations = (
            {"gsd_recovery_liveness": "pass"},
            {"gsd_recovery_liveness": "passing"},
            {"owner_resolution": "fixed"},
            {"disposition": "sanctioned-resolution"},
            {"engine_fix": "fixed"},
            {"law_nexus_fixable": True},
            {"retry_substitute": True},
            {"s23_called_validate_milestone": True},
            {"upstream_issue": "filed"},
            {"status_effect": "validated"},
            {"c4_operational_acceptance": "pass"},
            {"evidence_kind": "live-sql-probe"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(original)
                changed.update(mutation)
                self.write(self.packet, changed)
                self.rejected()
                self.restore()

    def test_rejects_schema_key_type_and_stale_pin_tampering(self) -> None:
        original = self.read(self.packet)
        extra = {**original, "unexpected": None}
        self.write(self.packet, extra)
        self.rejected()
        self.restore()

        changed = copy.deepcopy(original)
        changed["law_nexus_fixable"] = 0
        self.write(self.packet, changed)
        self.rejected()
        self.restore()

        manifest = self.read(self.manifest)
        for index in range(len(manifest["files"])):
            changed_manifest = copy.deepcopy(manifest)
            changed_manifest["files"][index]["sha256"] = "sha256:" + "f" * 64
            self.write(self.manifest, changed_manifest)
            self.rejected()
            self.restore()

    def test_rejects_missing_extra_duplicate_and_unsafe_paths(self) -> None:
        original = self.read(self.manifest)
        cases = []
        missing = copy.deepcopy(original)
        missing["files"] = missing["files"][:-1]
        cases.append(missing)
        extra = copy.deepcopy(original)
        extra["files"].append(copy.deepcopy(extra["files"][-1]))
        cases.append(extra)
        for value in ("/tmp/escape", "../escape", ".git/secret", ".gsd/secret", "x\\escape"):
            changed = copy.deepcopy(original)
            changed["files"][0]["path"] = value
            cases.append(changed)
        for changed in cases:
            self.write(self.manifest, changed)
            self.rejected()
            self.restore()

        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = self.root / "link"
        link.symlink_to(outside)
        changed = copy.deepcopy(original)
        changed["files"][0]["path"] = "link"
        self.write(self.manifest, changed)
        self.rejected()
        self.restore()

    def test_rejects_malformed_and_missing_predecessor_without_marker(self) -> None:
        before = self.packet.read_bytes()
        self.packet.write_text('{"schema":', encoding="utf-8")
        result = self.rejected()
        self.assertNotIn("S23_T03_EXTERNAL_BOUNDARY_OK", result.stdout)
        self.packet.write_bytes(before)
        self.manifest.unlink()
        result = invoke(self.root, self.packet, self.manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("S23_T03_BLOCKER_PROOF_OK", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
