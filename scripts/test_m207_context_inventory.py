#!/usr/bin/env python3
"""Offline adversarial suite for the M207 operator-only context inventory.

Every case uses a throw-away root with compact synthetic seed/diagnosis/pilot
fixtures. The real CLI is invoked; nothing here mutates the repository tree,
the git index, or frozen M207 pins.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "scripts" / "m207_context_inventory.py"
MARKER = "M207_CONTEXT_INVENTORY_OK"
RECORD_REL = "prd/migration/rust-evidence/m207-context-inventory.json"
SEED_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
PILOT_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
DIAG_REL = "prd/migration/rust-evidence/m207-unit-diagnosis.json"
FIX_REL = "crates/ln-decode/tests/fixtures/npa-lawref"

TIMEOUT = 30


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ContextInventoryTests(unittest.TestCase):
    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-context-inventory-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        self.populate(directory)
        return directory

    def populate(self, root: Path, **overrides: Any) -> dict[str, bytes]:
        files = {
            "A1": b"ZZHEAD-OPEN,",
            "A2": b"ZZTAIL-CLOSE)",
            "B1": b"ZZot 01.01.2020 N 1",
            "C1": b"ZZTITLE...",
            "D1": b"ZZDUP-TEXT",
            "D2": b"ZZDUP-TEXT",
            "E1": b"ZZCLEAN-REF",
        }
        files.update(overrides.get("files", {}))
        fix = root / FIX_REL
        fix.mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            (fix / f"npa-frag-{name}.txt").write_bytes(raw)

        documents = overrides.get(
            "documents",
            [
                self.document("npa-doc-A", "src/a.xml", "aa" * 32, ["npa-frag-A1", "npa-frag-A2"]),
                self.document("npa-doc-B", "src/b.xml", "bb" * 32, ["npa-frag-B1"]),
                self.document("npa-doc-C", "src/c.xml", "cc" * 32, ["npa-frag-C1"]),
                self.document("npa-doc-D", "src/d.xml", "dd" * 32, ["npa-frag-D1", "npa-frag-D2"]),
                self.document("npa-doc-E", "src/e.xml", "ee" * 32, ["npa-frag-E1"]),
            ],
        )
        fragments = overrides.get(
            "fragments",
            [
                self.seed_frag("A1", "npa-doc-A", 10, files["A1"]),
                self.seed_frag("A2", "npa-doc-A", 11, files["A2"]),
                self.seed_frag("B1", "npa-doc-B", 3, files["B1"]),
                self.seed_frag("C1", "npa-doc-C", 7, files["C1"]),
                self.seed_frag("D1", "npa-doc-D", 1, files["D1"]),
                self.seed_frag("D2", "npa-doc-D", 2, files["D2"]),
                self.seed_frag("E1", "npa-doc-E", 4, files["E1"]),
            ],
        )
        seed = {
            "schema": "npa-lawref-sample/v1",
            "schema_version": 1,
            "documents": documents,
            "fragments": fragments,
        }
        seed.update(overrides.get("seed_extra", {}))
        dump(root / SEED_REL, seed)

        cases = overrides.get(
            "cases",
            [
                self.pilot_case("001", "A1", "npa-doc-A", "aa" * 32, 10, files["A1"]),
                self.pilot_case("002", "B1", "npa-doc-B", "bb" * 32, 3, files["B1"]),
                self.pilot_case("003", "C1", "npa-doc-C", "cc" * 32, 7, files["C1"]),
                self.pilot_case("004", "D1", "npa-doc-D", "dd" * 32, 1, files["D1"]),
                self.pilot_case("005", "D2", "npa-doc-D", "dd" * 32, 2, files["D2"]),
                self.pilot_case("006", "E1", "npa-doc-E", "ee" * 32, 4, files["E1"]),
            ],
        )
        dump(
            root / PILOT_REL,
            {
                "schema": "m207-s01-pilot-cases/v1",
                "schema_version": 1,
                "case_count": len(cases),
                "cases": cases,
            },
        )

        diag_frags = overrides.get(
            "diag_frags",
            [
                self.diag_frag("A1", "npa-doc-A", 10, files["A1"], ["ends-comma", "ed-note-open"]),
                self.diag_frag("A2", "npa-doc-A", 11, files["A2"], ["starts-ot-date"]),
                self.diag_frag("B1", "npa-doc-B", 3, files["B1"], ["starts-ot-date"]),
                self.diag_frag("C1", "npa-doc-C", 7, files["C1"], ["ellipsis"]),
                self.diag_frag("D1", "npa-doc-D", 1, files["D1"], []),
                self.diag_frag("D2", "npa-doc-D", 2, files["D2"], []),
                self.diag_frag("E1", "npa-doc-E", 4, files["E1"], []),
            ],
        )
        series = overrides.get(
            "series",
            [
                {
                    "doc_id": "npa-doc-A",
                    "fragment_ids": ["npa-frag-A1", "npa-frag-A2"],
                    "block_indices": [10, 11],
                    "cross_block_text_anchor": False,
                    "display_join_only": True,
                    "member_count": 2,
                    "kind": "consultant-edition-list",
                }
            ],
        )
        dump(
            root / DIAG_REL,
            {
                "schema": "m207-unit-diagnosis/v1",
                "schema_version": 1,
                "lifecycle": "[bounded]",
                "authoritative": False,
                "fragments": diag_frags,
                "edition_series": series,
            },
        )
        return files

    def document(
        self, doc_id: str, source_path: str, source_sha: str, fragment_ids: list[str]
    ) -> dict[str, Any]:
        return {
            "doc_id": doc_id,
            "source_path": source_path,
            "source_sha256": source_sha,
            "fragment_ids": fragment_ids,
        }

    def seed_frag(self, suffix: str, doc_id: str, block: int, raw: bytes) -> dict[str, Any]:
        return {
            "id": f"npa-frag-{suffix}",
            "file": f"npa-frag-{suffix}.txt",
            "doc_id": doc_id,
            "source_block_index": block,
            "byte_len": len(raw),
            "status": "seed",
            "seed_span": None,
        }

    def diag_frag(
        self, suffix: str, doc_id: str, block: int, raw: bytes, flags: list[str]
    ) -> dict[str, Any]:
        return {
            "fragment_id": f"npa-frag-{suffix}",
            "doc_id": doc_id,
            "source_block_index": block,
            "byte_len": len(raw),
            "text_sha256": sha256_bytes(raw),
            "trunc_flags": flags,
        }

    def pilot_case(
        self,
        suffix: str,
        frag: str,
        doc_id: str,
        source_sha: str,
        block: int,
        raw: bytes,
        *,
        start: int | None = None,
        end: int | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": case_id or f"m207-s01-case-{suffix}",
            "fragment_id": f"npa-frag-{frag}",
            "doc_id": doc_id,
            "source_sha256": source_sha,
            "source_block_index": block,
            "byte_len": len(raw),
            "start": 0 if start is None else start,
            "end": len(raw) if end is None else end,
        }

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(INVENTORY), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def load(self, root: Path, relative: str) -> Any:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    def store(self, root: Path, relative: str, payload: object) -> None:
        dump(root / relative, payload)

    def assert_ok(self, result: subprocess.CompletedProcess[str], *needles: str) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(MARKER, result.stdout)
        for needle in needles:
            self.assertIn(needle, result.stdout, result.stdout)

    def assert_fail_closed(
        self, result: subprocess.CompletedProcess[str], *diagnostics: str
    ) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertNotIn(MARKER, output)
        found = [name for name in diagnostics if f"FAIL {name}" in output]
        self.assertTrue(found, f"none of {diagnostics!r} reported in:\n{output}")

    def write_inventory(self, root: Path) -> dict[str, Any]:
        self.assert_ok(self.run_cli(root, "--write"), "wrote=")
        payload = self.load(root, RECORD_REL)
        self.assertEqual(payload["schema"], "m207-context-inventory/v1")
        self.assertIs(payload["authoritative"], False)
        self.assertIs(payload["coder_facing"], False)
        self.assertIs(payload["human_ready"], False)
        self.assertEqual(payload["lifecycle"], "[bounded]")
        self.assertEqual(payload["counts"]["human_ready_cases"], 0)
        self.assertEqual(payload["counts"]["coder_facing_cases"], 0)
        self.assertEqual(payload["counts"]["cross_block_text_anchor"], 0)
        return payload

    def test_happy_path_write_and_check(self) -> None:
        root = self.make_root()
        payload = self.write_inventory(root)
        by_id = {row["case_id"]: row for row in payload["cases"]}
        self.assertEqual(payload["counts"]["cases"], 6)
        self.assertEqual(payload["counts"]["unique_case_ids"], 6)
        self.assertEqual(payload["counts"]["unique_focus_texts"], 5)
        self.assertEqual(payload["counts"]["diagnosed_series_cases"], 1)
        self.assertEqual(payload["counts"]["orphan_unresolved_cases"], 1)
        self.assertEqual(payload["counts"]["truncation_requires_review_cases"], 1)
        self.assertEqual(payload["counts"]["operator_inventory_only_cases"], 3)
        self.assertEqual(payload["counts"]["duplicate_text_groups"], 1)
        self.assertEqual(payload["counts"]["duplicate_text_cases"], 2)
        self.assertEqual(payload["counts"]["context_refs"], 1)

        series_case = by_id["m207-s01-case-001"]
        self.assertEqual(series_case["eligibility"], "diagnosed-series-context-only")
        self.assertIsNone(series_case["unresolved_head"])
        self.assertEqual(
            [ref["fragment_id"] for ref in series_case["context_refs"]], ["npa-frag-A2"]
        )
        self.assertEqual(series_case["context_refs"][0]["role"], "series-member")
        self.assertEqual(series_case["context_refs"][0]["doc_id"], series_case["focus"]["doc_id"])
        self.assertEqual(series_case["context_refs"][0]["span"]["start"], 0)
        self.assertEqual(
            series_case["context_refs"][0]["span"]["end"],
            series_case["context_refs"][0]["byte_len"],
        )
        self.assertIs(series_case["series"]["cross_block_text_anchor"], False)
        self.assertEqual(series_case["focus"]["span"]["unit"], "byte")
        self.assertIs(series_case["focus"]["span"]["half_open"], True)

        orphan = by_id["m207-s01-case-002"]
        self.assertEqual(orphan["eligibility"], "unavailable-for-coding")
        self.assertEqual(orphan["unresolved_head"]["status"], "unresolved")
        self.assertEqual(orphan["context_refs"], [])

        review = by_id["m207-s01-case-003"]
        self.assertEqual(review["eligibility"], "requires-review")
        self.assertIsNone(review["unresolved_head"])

        dup_a = by_id["m207-s01-case-004"]
        dup_b = by_id["m207-s01-case-005"]
        self.assertEqual(dup_a["eligibility"], "operator-inventory-only")
        self.assertEqual(dup_b["duplicate_text_case_ids"], ["m207-s01-case-004"])
        self.assertEqual(dup_a["duplicate_text_case_ids"], ["m207-s01-case-005"])

        clean = by_id["m207-s01-case-006"]
        self.assertEqual(clean["eligibility"], "operator-inventory-only")
        self.assertNotEqual(clean["eligibility"], "human-ready")

        blob = json.dumps(payload)
        self.assertNotIn("ZZHEAD-OPEN", blob)
        self.assertNotIn("coding_verdict", blob)
        self.assertNotIn("genre", blob)
        self.assertNotIn("joined_preview", blob)
        self.assert_ok(self.run_cli(root, "--check"), "drift=0")

    def test_default_is_check_and_does_not_write(self) -> None:
        root = self.make_root()
        target = root / RECORD_REL
        self.assertFalse(target.exists())
        self.assert_fail_closed(self.run_cli(root), "MISSING_ARTIFACT")
        self.assertFalse(target.exists())
        self.assert_fail_closed(self.run_cli(root, "--check"), "MISSING_ARTIFACT")
        self.assertFalse(target.exists())

    def test_stale_check_does_not_rewrite(self) -> None:
        root = self.make_root()
        self.write_inventory(root)
        target = root / RECORD_REL
        original = target.read_bytes()
        stale = json.loads(original.decode("utf-8"))
        stale["counts"]["human_ready_cases"] = 99
        target.write_bytes(
            (json.dumps(stale, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        mutated = target.read_bytes()
        self.assert_fail_closed(self.run_cli(root, "--check"), "STALE_ARTIFACT")
        self.assertEqual(target.read_bytes(), mutated)
        self.assert_fail_closed(self.run_cli(root), "STALE_ARTIFACT")
        self.assertEqual(target.read_bytes(), mutated)
        self.assertNotEqual(mutated, original)

    def test_wrong_hash_fails_closed(self) -> None:
        root = self.make_root()
        (root / FIX_REL / "npa-frag-A1.txt").write_bytes(b"ZZHEAD-MUTATED,")
        self.assert_fail_closed(self.run_cli(root, "--write"), "WRONG_HASH")
        self.assertFalse((root / RECORD_REL).exists())

    def test_cross_document_series_fails_closed(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="m207-context-inventory-xd-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.populate(
            root,
            series=[
                {
                    "doc_id": "npa-doc-A",
                    "fragment_ids": ["npa-frag-A1", "npa-frag-B1"],
                    "block_indices": [10, 3],
                    "cross_block_text_anchor": False,
                    "display_join_only": True,
                    "member_count": 2,
                    "kind": "consultant-edition-list",
                }
            ],
        )
        self.assert_fail_closed(self.run_cli(root, "--write"), "CROSS_DOCUMENT_SERIES")
        self.assertFalse((root / RECORD_REL).exists())

    def test_duplicate_case_fails_closed(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="m207-context-inventory-dup-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        files = {
            "A1": b"ZZHEAD-OPEN,",
            "A2": b"ZZTAIL-CLOSE)",
            "B1": b"ZZot 01.01.2020 N 1",
            "C1": b"ZZTITLE...",
            "D1": b"ZZDUP-TEXT",
            "D2": b"ZZDUP-TEXT",
            "E1": b"ZZCLEAN-REF",
        }
        self.populate(
            root,
            cases=[
                self.pilot_case("001", "A1", "npa-doc-A", "aa" * 32, 10, files["A1"]),
                self.pilot_case(
                    "001",
                    "E1",
                    "npa-doc-E",
                    "ee" * 32,
                    4,
                    files["E1"],
                    case_id="m207-s01-case-001",
                ),
            ],
        )
        self.assert_fail_closed(self.run_cli(root, "--write"), "DUPLICATE_CASE")
        self.assertFalse((root / RECORD_REL).exists())

    def test_orphan_unresolved_is_explicit(self) -> None:
        root = self.make_root()
        payload = self.write_inventory(root)
        orphan = next(row for row in payload["cases"] if row["case_id"].endswith("002"))
        self.assertEqual(orphan["eligibility"], "unavailable-for-coding")
        self.assertEqual(orphan["truncation_flags"], ["starts-ot-date"])
        self.assertEqual(orphan["unresolved_head"]["status"], "unresolved")
        self.assertIs(payload["human_ready"], False)

    def test_source_shape_missing_schema_fails_closed(self) -> None:
        root = self.make_root()
        seed = self.load(root, SEED_REL)
        del seed["schema"]
        self.store(root, SEED_REL, seed)
        self.assert_fail_closed(self.run_cli(root, "--check"), "SOURCE_SHAPE")

    def test_source_shape_pilot_not_list_fails_closed(self) -> None:
        root = self.make_root()
        pilot = self.load(root, PILOT_REL)
        pilot["cases"] = {"not": "a-list"}
        self.store(root, PILOT_REL, pilot)
        self.assert_fail_closed(self.run_cli(root, "--write"), "SOURCE_SHAPE")

    def test_source_shape_diagnosis_missing_series_fails_closed(self) -> None:
        root = self.make_root()
        diagnosis = self.load(root, DIAG_REL)
        del diagnosis["edition_series"]
        self.store(root, DIAG_REL, diagnosis)
        self.assert_fail_closed(self.run_cli(root, "--check"), "SOURCE_SHAPE")

    def test_cross_block_text_anchor_in_diagnosis_fails_closed(self) -> None:
        root = self.make_root()
        diagnosis = self.load(root, DIAG_REL)
        diagnosis["edition_series"][0]["cross_block_text_anchor"] = True
        self.store(root, DIAG_REL, diagnosis)
        self.assert_fail_closed(self.run_cli(root, "--write"), "CROSS_BLOCK_TEXT_ANCHOR")

    def test_check_and_write_together_is_usage_error(self) -> None:
        root = self.make_root()
        result = self.run_cli(root, "--check", "--write")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("FAIL USAGE", result.stderr)

    def test_missing_source_fails_closed(self) -> None:
        root = self.make_root()
        (root / PILOT_REL).unlink()
        self.assert_fail_closed(self.run_cli(root, "--check"), "MISSING_SOURCE")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContextInventoryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
