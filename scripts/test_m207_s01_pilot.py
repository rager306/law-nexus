#!/usr/bin/env python3
"""Offline adversarial subprocess suite for the M207 S01 pilot boundary (T04).

Every case invokes the real CLI (``scripts/m207_s01_pilot.py``, and the three
per-task gates through it) on a throw-away copy of the frozen artifacts, mutates
exactly one thing, and asserts that the run fails closed with a named
diagnostic.  Nothing here is mocked and nothing touches the network, the git
index, or the repository working tree.

The suite also pins the *positive* control: an unmutated copy must pass with
non-zero counters, so a fail-closed verifier that simply rejects everything
cannot make these tests green.  Two invariants live here as well: the pilot
needs no human-coding file to pass (S01 creates none), and the integrity of the
answer/provenance needle split (the frozen schemas may *declare* S02 coder
fields, but a model-facing packet may not carry them).

Finally the suite protects the host's source-integrity window: the closeout
chain must be read-only on the repository, so ``battery`` defaults to a
byte-for-byte comparison with the tracked artifact (``BATTERY_STALE`` on drift)
and ``--write`` is the single opt-in that touches it.  Wall-clock durations are
never persisted -- they are printed as ``M207_S01_BATTERY_TIMINGS`` -- so the
tracked battery stays a pure function of the observed checks and re-running the
chain cannot move the source revision.
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

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "m207_s01_pilot.py"
MARKER = "M207_S01_PILOT_OK"
BATTERY_MARKER = "M207_S01_BATTERY_OK"
BATTERY_TIMINGS = "M207_S01_BATTERY_TIMINGS"
BATTERY_REL = "prd/migration/rust-evidence/m207-s01-battery.json"

CASES = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
PACKETS = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
SEED = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
SCHEMAS = "prd/annotation/m207-s01-schemas.json"
CODEBOOK = "prd/annotation/m207-s01-codebook.md"
METAPROMPT = "prd/annotation/m207-s01-metaprompt.md"
REQUIREMENTS = "prd/REQUIREMENTS.md"
D388_ADMISSION = "prd/architecture/m206-s07-runtime-admission.md"
REVIEW_PROGRAM = "prd/architecture/review-cases/rc28-remediation-program.md"
FIXTURES = "crates/ln-decode/tests/fixtures/npa-lawref"
FENCE = "```json"

COPY = (
    "prd/annotation",
    SEED,
    "prd/migration/rust-evidence/m199-s01-annotation-protocol.md",
    "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-400.json",
    CASES,
    PACKETS,
    REQUIREMENTS,
    D388_ADMISSION,
    REVIEW_PROGRAM,
    FIXTURES,
)
HUMAN_INPUT_MARKERS = ("coder", "submission", "adjudicat")

TIMEOUT = 120


class PilotBoundaryTests(unittest.TestCase):
    """Exercise the real verifier CLI against hostile mutations."""

    # -- fixtures ---------------------------------------------------------
    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-s01-pilot-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        for relative in COPY:
            source = ROOT / relative
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)
        return directory

    def load(self, root: Path, relative: str) -> object:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    def store(self, root: Path, relative: str, payload: object) -> None:
        (root / relative).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def load_packets(self, root: Path) -> list[dict]:
        text = (root / PACKETS).read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def store_packets(self, root: Path, packets: list[dict]) -> None:
        (root / PACKETS).write_text(
            "".join(json.dumps(packet, ensure_ascii=False) + "\n" for packet in packets),
            encoding="utf-8",
        )

    def edit_text(self, root: Path, relative: str, old: str, new: str) -> None:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"mutation anchor {old!r} missing from {relative}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def fence_block(self, root: Path, relative: str) -> dict:
        text = (root / relative).read_text(encoding="utf-8")
        blocks = [part for part in text.split(FENCE) if part.strip()]
        self.assertTrue(blocks, f"no fenced block in {relative}")
        for block in blocks:
            candidate = block.split("```")[0]
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise AssertionError(f"no parseable fenced JSON object in {relative}")

    def fragment_file(self, root: Path, fragment_id: str) -> str:
        seed = self.load(root, SEED)
        for fragment in seed["fragments"]:
            if fragment["id"] == fragment_id:
                return fragment["file"]
        raise AssertionError(f"fragment {fragment_id!r} is not in the seed")

    def multibyte_split_index(self, root: Path) -> tuple[int, int]:
        """Find a fragment byte offset that lands inside a multi-byte code point."""
        cases = self.load(root, CASES)
        for index, case in enumerate(cases["cases"]):
            raw = (root / FIXTURES / self.fragment_file(root, case["fragment_id"])).read_bytes()
            for offset in range(1, len(raw)):
                if 0x80 <= raw[offset] < 0xC0:
                    return index, offset
        raise AssertionError("no frozen fragment holds a multi-byte code point")

    # -- cli --------------------------------------------------------------
    def run_verifier(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VERIFIER), "check", "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def run_battery(
        self, root: Path, results: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VERIFIER),
            "battery",
            "--root",
            str(root),
            "--results",
            str(results),
            *extra,
        ]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def run_subcli(
        self, root: Path, relative: str, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ROOT / relative), "check", "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def result_table(self, *rows: str) -> Path:
        handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed by cleanup
            "w", prefix="m207-s01-results-", suffix=".tsv", delete=False, encoding="utf-8"
        )
        self.addCleanup(Path(handle.name).unlink, True)
        handle.write("".join(row + "\n" for row in rows))
        handle.close()
        return Path(handle.name)

    # -- assertions -------------------------------------------------------
    def assert_ok(self, result: subprocess.CompletedProcess[str], *fragments: str) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(MARKER, result.stdout)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout, result.stdout)

    def assert_fail_closed(
        self, result: subprocess.CompletedProcess[str], *diagnostics: str
    ) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertNotIn(MARKER, output)
        found = [name for name in diagnostics if f"FAIL {name}" in output]
        self.assertTrue(found, f"none of {diagnostics!r} reported in:\n{output}")

    def assert_gate_fail_closed(
        self, result: subprocess.CompletedProcess[str], marker: str, *diagnostics: str
    ) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertNotIn(marker, output)
        found = [name for name in diagnostics if f"FAIL {name}" in output]
        self.assertTrue(found, f"none of {diagnostics!r} reported in:\n{output}")

    # -- per-gate enforcement on throw-away copies ------------------------
    def test_select_cases_gate_rejects_label_injection(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"][1]["predicted_answer"] = "doc_no"
        self.store(root, CASES, cases)
        self.assert_gate_fail_closed(
            self.run_subcli(root, "scripts/m207_s01_select_cases.py"),
            "M207_S01_SELECT_CASES_OK",
            "LEAK_FORBIDDEN_KEY",
            "MANIFEST_DRIFT",
        )

    def test_prompt_packet_gate_rejects_authority_claim(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[1]["authority"] = "authoritative"
        self.store_packets(root, packets)
        self.assert_gate_fail_closed(
            self.run_subcli(root, "scripts/m207_s01_prompt_packet.py"),
            "M207_S01_PROMPT_PACKET_OK",
            "AUTHORITY_CLAIM",
            "PACKET_DRIFT",
        )

    def test_schemas_gate_rejects_ninth_slot(self) -> None:
        root = self.make_root()
        schema = self.load(root, SCHEMAS)
        keys = schema["slot_space"]["closed_keys"]
        schema["slot_space"]["closed_keys"] = [*keys, "ninth_slot"]
        schema["slot_space"]["closed_key_count"] = len(keys) + 1
        self.store(root, SCHEMAS, schema)
        self.assert_gate_fail_closed(
            self.run_subcli(root, "scripts/m207_s01_schemas.py"),
            "M207_S01_SCHEMAS_OK",
            "NINTH_SLOT",
            "SLOT_SET_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    # -- positive control -------------------------------------------------
    def test_unmutated_copy_passes_with_real_counters(self) -> None:
        """The clean control must pass *and* report non-zero work done."""
        root = self.make_root()
        result = self.run_verifier(root)
        self.assert_ok(
            result,
            "cases=40",
            "fixture_txt=180",
            "pinned=7/7",
            "leaks=0",
            "gates_deferred=13",
            "active_guardrails=3",
            "review_rows=1",
            "human_input_tokens=0",
            "subclis=3/3",
        )

    def test_pilot_requires_no_human_coding_artifact(self) -> None:
        """S01 creates no coding, so none may be required to pass."""
        root = self.make_root()
        for path in root.rglob("*"):
            lowered = str(path.relative_to(root)).lower()
            for marker in HUMAN_INPUT_MARKERS:
                self.assertNotIn(marker, lowered, f"unexpected human-coding artifact {path}")
        self.assert_ok(self.run_verifier(root), "subclis=3/3")

    # -- leakage ----------------------------------------------------------
    def test_label_key_injected_into_case_manifest_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"][0]["label"] = "reference"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "LEAK_FORBIDDEN_KEY",
            "CASE_SCHEMA_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_nested_predicted_answer_in_packet_anchor_fails(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["source_anchor"]["predicted_answer"] = "date"
        self.store_packets(root, packets)
        self.assert_fail_closed(
            self.run_verifier(root), "LEAK_FORBIDDEN_KEY", "ANCHOR_DRIFT", "FROZEN_SOURCE_DRIFT"
        )

    def test_forecast_substring_injected_into_packet_fails(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["packet_id"] = "m207-s01-packet-001-gold"
        self.store_packets(root, packets)
        self.assert_fail_closed(
            self.run_verifier(root),
            "LEAK_FORBIDDEN_SUBSTRING",
            "PACKET_ORDER_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_coder_provenance_substring_in_packet_fails(self) -> None:
        """The frozen schemas may declare S02 coder fields; a packet may not carry them."""
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["codebook_ref"] = "coder_id"
        self.store_packets(root, packets)
        self.assert_fail_closed(
            self.run_verifier(root),
            "LEAK_FORBIDDEN_SUBSTRING",
            "PACKET_KEY_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_rule_seed_span_key_in_packet_fails(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["seed_span"] = [0, 5]
        self.store_packets(root, packets)
        self.assert_fail_closed(
            self.run_verifier(root), "LEAK_FORBIDDEN_KEY", "PACKET_KEY_DRIFT", "FROZEN_SOURCE_DRIFT"
        )

    # -- ninth slot -------------------------------------------------------
    def test_ninth_slot_injected_into_schema_fails(self) -> None:
        root = self.make_root()
        schema = self.load(root, SCHEMAS)
        keys = schema["slot_space"]["closed_keys"]
        schema["slot_space"]["closed_keys"] = [*keys, "ninth_slot"]
        schema["slot_space"]["closed_key_count"] = len(keys) + 1
        self.store(root, SCHEMAS, schema)
        self.assert_fail_closed(
            self.run_verifier(root),
            "NINTH_SLOT",
            "SLOT_SET_DRIFT",
            "SCHEMA_KEY_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_ninth_slot_injected_into_codebook_contract_fails(self) -> None:
        root = self.make_root()
        block = self.fence_block(root, CODEBOOK)
        self.assertEqual(block["slot_space"]["closed_key_count"], 9)
        block["slot_space"]["closed_key_count"] = 10
        self.edit_text(root, CODEBOOK, '"closed_key_count": 9', '"closed_key_count": 10')
        self.assert_fail_closed(
            self.run_verifier(root),
            "SLOT_SET_DRIFT",
            "NINTH_SLOT",
            "SCHEMA_KEY_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_ninth_slot_injected_into_metaprompt_contract_fails(self) -> None:
        root = self.make_root()
        self.edit_text(
            root,
            METAPROMPT,
            '"quoted_enum"\n    ],\n    "abstention_values"',
            '"quoted_enum",\n      "ninth_slot"\n    ],\n    "abstention_values"',
        )
        self.assert_fail_closed(
            self.run_verifier(root),
            "PROMPT_CONTRACT_DRIFT",
            "NINTH_SLOT",
            "FROZEN_SOURCE_DRIFT",
        )

    # -- case count and fixture tree --------------------------------------
    def test_nineteen_cases_fail(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"] = cases["cases"][:19]
        cases["case_count"] = 19
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "CASE_COUNT_OUT_OF_RANGE",
            "MANIFEST_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_forty_one_cases_fail(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"] = [*cases["cases"], dict(cases["cases"][0])]
        cases["case_count"] = 41
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "CASE_COUNT_OUT_OF_RANGE",
            "DUPLICATE_CASE",
            "MANIFEST_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_fixture_tree_enlarged_to_181_fails(self) -> None:
        root = self.make_root()
        (root / FIXTURES / "npa-frag-181.txt").write_text(
            "hostile extra fragment", encoding="utf-8"
        )
        self.assert_fail_closed(
            self.run_verifier(root), "SEED_ENLARGED", "FROZEN_SOURCE_DRIFT", "MANIFEST_DRIFT"
        )

    def test_removed_fixture_fails(self) -> None:
        root = self.make_root()
        (root / FIXTURES / "npa-frag-001.txt").unlink()
        self.assert_fail_closed(
            self.run_verifier(root), "MISSING_ARTIFACT", "SEED_ENLARGED", "FROZEN_SOURCE_DRIFT"
        )

    def test_fixture_byte_drift_fails(self) -> None:
        root = self.make_root()
        target = root / FIXTURES / "npa-frag-001.txt"
        target.write_bytes(target.read_bytes() + b"drift")
        self.assert_fail_closed(
            self.run_verifier(root),
            "FROZEN_SOURCE_DRIFT",
            "FRAGMENT_TEXT_DRIFT",
            "MANIFEST_DRIFT",
        )

    def test_byte_len_drift_in_case_manifest_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"][0]["byte_len"] = cases["cases"][0]["byte_len"] + 3
        cases["cases"][0]["end"] = cases["cases"][0]["byte_len"]
        self.store(root, CASES, cases)
        self.assert_fail_closed(self.run_verifier(root), "FROZEN_SOURCE_DRIFT", "MANIFEST_DRIFT")

    def test_zero_cases_fail(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"] = []
        cases["case_count"] = 0
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "CASE_COUNT_OUT_OF_RANGE",
            "MANIFEST_DRIFT",
            "FROZEN_SOURCE_DRIFT",
        )

    # -- spans ------------------------------------------------------------
    def test_span_beyond_eof_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"][0]["end"] = cases["cases"][0]["byte_len"] + 1
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root), "SPAN_OUT_OF_BOUNDS", "FROZEN_SOURCE_DRIFT", "MANIFEST_DRIFT"
        )

    def test_span_splitting_utf8_codepoint_fails(self) -> None:
        root = self.make_root()
        index, offset = self.multibyte_split_index(root)
        cases = self.load(root, CASES)
        self.assertLess(offset, cases["cases"][index]["byte_len"])
        cases["cases"][index]["end"] = offset
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "SPAN_NOT_UTF8_BOUNDARY",
            "SPAN_NOT_FULL_FRAGMENT",
            "SPAN_OUT_OF_BOUNDS",
            "FROZEN_SOURCE_DRIFT",
        )

    # -- authority --------------------------------------------------------
    def test_authoritative_suggestion_is_rejected(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["authority"] = "authoritative"
        self.store_packets(root, packets)
        self.assert_fail_closed(self.run_verifier(root), "AUTHORITY_CLAIM", "FROZEN_SOURCE_DRIFT")

    def test_provided_suggestion_status_is_rejected(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["suggestion_status"] = "provided"
        self.store_packets(root, packets)
        self.assert_fail_closed(self.run_verifier(root), "AUTHORITY_CLAIM", "FROZEN_SOURCE_DRIFT")

    def test_model_invoked_claim_is_rejected(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["model_invoked"] = True
        self.store_packets(root, packets)
        self.assert_fail_closed(self.run_verifier(root), "AUTHORITY_CLAIM", "FROZEN_SOURCE_DRIFT")

    def test_packet_extra_key_fails(self) -> None:
        root = self.make_root()
        packets = self.load_packets(root)
        packets[0]["reviewer_note"] = "unexpected"
        self.store_packets(root, packets)
        self.assert_fail_closed(self.run_verifier(root), "PACKET_KEY_DRIFT", "FROZEN_SOURCE_DRIFT")

    # -- prompt isolation -------------------------------------------------
    def test_forged_product_reference_fails(self) -> None:
        root = self.make_root()
        poison = root / "crates" / "ln-decode" / "src"
        poison.mkdir(parents=True)
        (poison / "lib.rs").write_text("// m207-s01 codebook wiring\n", encoding="utf-8")
        result = self.run_verifier(root)
        self.assert_fail_closed(result, "PROMPT_ISOLATION_VIOLATION")
        self.assertIn("crates/ln-decode/src/lib.rs", result.stdout + result.stderr)

    # -- honesty markers --------------------------------------------------
    def test_gate_selection_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["lifecycle"]["selected_d388_gates"] = "G01"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "GATE_SELECTION_VIOLATION",
            "MISSING_LIFECYCLE_MARKER",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_lifecycle_marker_drift_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["lifecycle"]["human_adoption"] = "accepted"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root),
            "LIFECYCLE_MARKER_DRIFT",
            "MISSING_LIFECYCLE_MARKER",
            "FROZEN_SOURCE_DRIFT",
        )

    def test_deferred_d388_gate_erosion_fails(self) -> None:
        root = self.make_root()
        self.edit_text(root, D388_ADMISSION, "G13, G15, G16", "G13, G15")
        self.assert_fail_closed(self.run_verifier(root), "GATE_SELECTION_VIOLATION")

    def test_requirement_promotion_fails(self) -> None:
        root = self.make_root()
        self.edit_text(
            root,
            REQUIREMENTS,
            "active ontology/evidence guardrails",
            "promoted ontology/evidence guardrails",
        )
        self.assert_fail_closed(self.run_verifier(root), "REQUIREMENT_PROMOTION")

    def test_review_disposition_change_fails(self) -> None:
        root = self.make_root()
        self.edit_text(root, REVIEW_PROGRAM, "F01-F03, F14-F15", "F01-F03")
        self.assert_fail_closed(self.run_verifier(root), "REVIEW_DISPOSITION_PROMOTION")

    def test_guardrail_promotion_prose_fails(self) -> None:
        root = self.make_root()
        self.edit_text(
            root,
            METAPROMPT,
            "## 1. Scope: no model is invoked in this slice",
            "## 1. Scope: R070 closed\n\n## 2. Packet contents",
        )
        self.assert_fail_closed(
            self.run_verifier(root), "REQUIREMENT_PROMOTION", "FROZEN_SOURCE_DRIFT"
        )

    # -- metadata honesty -------------------------------------------------
    def test_path_derived_metadata_source_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        cases["cases"][0]["metadata_source"] = "path-derived"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root), "METADATA_PATH_DERIVED", "FROZEN_SOURCE_DRIFT"
        )

    def test_year_without_validated_provenance_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        self.assertEqual(cases["cases"][0]["metadata_source"], "unknown")
        cases["cases"][0]["year"] = "2020"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root), "METADATA_PATH_DERIVED", "FROZEN_SOURCE_DRIFT"
        )

    def test_work_family_dominance_fails(self) -> None:
        root = self.make_root()
        cases = self.load(root, CASES)
        for case in cases["cases"][:5]:
            case["work_family"] = "stem:hostile-single-work"
        self.store(root, CASES, cases)
        self.assert_fail_closed(
            self.run_verifier(root), "WORK_FAMILY_DOMINANCE", "FROZEN_SOURCE_DRIFT"
        )

    # -- artifacts and paths ----------------------------------------------
    def test_missing_packet_artifact_fails(self) -> None:
        root = self.make_root()
        (root / PACKETS).unlink()
        self.assert_fail_closed(
            self.run_verifier(root),
            "MISSING_ARTIFACT",
            "FROZEN_SOURCE_DRIFT",
            "PACKET_COUNT_MISMATCH",
        )

    def test_duplicate_json_key_fails(self) -> None:
        root = self.make_root()
        path = root / CASES
        text = path.read_text(encoding="utf-8")
        needle = next(
            (
                candidate
                for candidate in ('  "case_count": 40,', '  "case_count": 40')
                if candidate in text
            ),
            None,
        )
        self.assertIsNotNone(needle, "case_count anchor missing")
        path.write_text(text.replace(needle, f'{needle}\n  "case_count": 40', 1), encoding="utf-8")
        self.assert_fail_closed(
            self.run_verifier(root), "DUPLICATE_JSON_KEY", "FROZEN_SOURCE_DRIFT"
        )

    def test_path_traversal_argument_fails_closed(self) -> None:
        root = self.make_root()
        self.assert_fail_closed(self.run_verifier(root, "--cases", "../escape.json"), "UNSAFE_PATH")
        self.assert_fail_closed(
            self.run_verifier(root, "--cases", "prd/annotation/m207-s01-codebook.md"),
            "UNSAFE_PATH",
        )

    def test_backslash_argument_fails_closed(self) -> None:
        root = self.make_root()
        self.assert_fail_closed(
            self.run_verifier(root, "--cases", "prd\\annotation\\x.json"), "UNSAFE_PATH"
        )

    def test_missing_root_fails_closed(self) -> None:
        result = self.run_verifier(Path("/nonexistent-m207-s01-root"))
        self.assert_fail_closed(result, "MISSING_ARTIFACT")

    # -- read-only closeout -----------------------------------------------
    def test_check_chain_is_read_only_on_temp_root(self) -> None:
        """The host source-integrity window forbids tracked writes while checking."""

        def snapshot() -> dict[str, str]:
            return {
                str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }

        root = self.make_root()
        before = snapshot()
        self.assert_ok(self.run_verifier(root), "subclis=3/3")
        self.assertEqual(before, snapshot(), "the check chain mutated the tree it inspected")

    # -- battery ----------------------------------------------------------
    def test_empty_result_table_fails(self) -> None:
        root = self.make_root()
        self.assert_fail_closed(self.run_battery(root, self.result_table()), "EMPTY_SUITE")

    def test_malformed_result_row_fails(self) -> None:
        root = self.make_root()
        self.assert_fail_closed(
            self.run_battery(root, self.result_table("a\tb\tc")), "BATTERY_ROW_MALFORMED"
        )

    def test_failing_result_row_fails(self) -> None:
        root = self.make_root()
        self.assert_fail_closed(
            self.run_battery(root, self.result_table("unit\t1\t12\tuv run python x.py")),
            "SUBCLI_FAILURE",
        )

    def test_battery_outside_evidence_dir_fails(self) -> None:
        root = self.make_root()
        table = self.result_table("unit\t0\t12\tuv run python x.py")
        self.assert_fail_closed(self.run_battery(root, table, "--out", "prd/x.json"), "UNSAFE_PATH")

    def test_green_result_table_writes_battery(self) -> None:
        root = self.make_root()
        table = self.result_table(
            "gate-schemas\t0\t120\tuv run python scripts/m207_s01_schemas.py check",
            "gate-pilot\t0\t420\tuv run python scripts/m207_s01_pilot.py check",
        )
        result = self.run_battery(root, table, "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(BATTERY_MARKER, result.stdout)
        self.assertIn("written", result.stdout)
        self.assertIn(BATTERY_TIMINGS, result.stdout)
        battery = json.loads((root / BATTERY_REL).read_text(encoding="utf-8"))
        self.assertIs(battery["human_pilot_performed"], False)
        self.assertIs(battery["model_invoked"], False)
        self.assertEqual(battery["selected_d388_gates"], "none")
        self.assertEqual(len(battery["deferred_d388_gates"]), 13)
        self.assertEqual(len(battery["pins"]), 7)
        self.assertEqual(battery["check_count"], 2)
        self.assertEqual([row["status"] for row in battery["checks"]], [0, 0])
        self.assertTrue(battery["non_claims"])
        for row in battery["checks"]:
            self.assertNotIn(
                "durationMs", row, "wall-clock timing must stay out of the tracked file"
            )

    def test_battery_read_only_rejects_missing_tracked_battery(self) -> None:
        root = self.make_root()
        table = self.result_table("gate-schemas\t0\t12\tuv run python x.py")
        self.assert_fail_closed(self.run_battery(root, table), "MISSING_ARTIFACT")

    def test_battery_read_only_rejects_stale_tracked_battery(self) -> None:
        root = self.make_root()
        first = self.result_table("gate-schemas\t0\t12\tuv run python x.py")
        self.assertEqual(self.run_battery(root, first, "--write").returncode, 0)
        stale = self.result_table(
            "gate-schemas\t0\t12\tuv run python x.py",
            "gate-extra\t0\t12\tuv run python y.py",
        )
        self.assert_fail_closed(self.run_battery(root, stale), "BATTERY_STALE")

    def test_battery_read_only_session_leaves_tracked_file_untouched(self) -> None:
        root = self.make_root()
        table = self.result_table("gate-schemas\t0\t12\tuv run python x.py")
        self.assertEqual(self.run_battery(root, table, "--write").returncode, 0)
        path = root / BATTERY_REL
        before_bytes = path.read_bytes()
        before_mtime = path.stat().st_mtime_ns
        result = self.run_battery(root, table)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("current", result.stdout)
        self.assertEqual(path.read_bytes(), before_bytes)
        self.assertEqual(
            path.stat().st_mtime_ns, before_mtime, "read-only battery touched the file"
        )

    def test_battery_write_is_deterministic_across_durations(self) -> None:
        root = self.make_root()
        path = root / BATTERY_REL
        slow = self.result_table("gate-schemas\t0\t120\tuv run python x.py")
        slower = self.result_table("gate-schemas\t0\t999999\tuv run python x.py")
        self.assertEqual(self.run_battery(root, slow, "--write").returncode, 0)
        first = path.read_bytes()
        result = self.run_battery(root, slower, "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged", result.stdout)
        self.assertEqual(path.read_bytes(), first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
