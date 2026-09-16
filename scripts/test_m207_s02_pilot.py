#!/usr/bin/env python3
"""Offline adversarial subprocess suite for the M207 S02 human-pilot contour (T06).

Every case invokes a real CLI -- ``scripts/m207_s02_pilot.py`` (the slice
verifier), or the intake/agreement/adjudication gates -- on a throw-away copy of
the frozen surface or on a hostile envelope in a temp directory, mutates exactly
one thing, and asserts that the run fails closed with a *named* diagnostic
(``FAIL <NAME>:``).  Nothing here is mocked, nothing is imported from the tools
under test (subprocess only, D472), and nothing touches the network, the git
index, the product stores or the repository working tree.

The suite exists **before any human labelling** (D476): the whole S02 contour
takes untrusted human input, so its refusals must be proven before a human is
asked to type anything.  It also pins the *positive* controls, so a suite that
merely rejects everything cannot make these tests green:

* the real repository root still verifies with ``M207_S02_MACHINERY_OK`` and the
  real S01 closeout chain (``scripts/m207_s01_t04_verify.sh``) run as a
  subprocess;
* an unmutated copy of the frozen surface passes with real counters;
* a complete synthetic pilot driven through the real intake -> agreement ->
  adjudication CLIs produces a receipt, and the verifier then reports *human data
  present* instead of machinery-green.

The two invariants this slice cannot delegate:

* **RC28-F01** -- removing the second coder envelope must refuse publication
  (no rewritten report, no promoted ``alpha``), never report success;
* **the human gate marker** -- ``M207_S02_VERIFY_OK`` must never be printed by
  any machinery run, whatever the inputs.

An empty suite is itself a failure: ``SuiteIntegrityTests`` requires the hostile
case registry to be populated and every registered case to exist.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "m207_s02_pilot.py"
INTAKE = ROOT / "scripts" / "m207_s02_intake.py"
AGREEMENT = ROOT / "scripts" / "m207_s02_agreement.py"
ADJUDICATE = ROOT / "scripts" / "m207_s02_adjudicate.py"

# Child processes must not inherit a mode-switching environment: the T07 closeout
# chain may be launched with M207_S02_WRITE_BATTERY=1 for its single battery
# write, and a battery test that expects the read-only contract would otherwise
# observe a write (and lose the MISSING_ARTIFACT / BATTERY_STALE refusals).
CHILD_ENV = {k: v for k, v in os.environ.items() if k != "M207_S02_WRITE_BATTERY"}

MARKER = "M207_S02_MACHINERY_OK"
HUMAN_DATA_MARKER = "M207_S02_MACHINERY_HUMAN_DATA_PRESENT"
BATTERY_MARKER = "M207_S02_BATTERY_OK"
BATTERY_TIMINGS = "M207_S02_BATTERY_TIMINGS"
HUMAN_GATE_MARKER = "M207_S02_VERIFY_OK"
S01_CHAIN_PATH = ROOT / "scripts" / "m207_s01_t04_verify.sh"

ANN = "prd/annotation"
EVID = "prd/migration/rust-evidence"
FIXTURES = "crates/ln-decode/tests/fixtures/npa-lawref"
S02_SCHEMAS = f"{ANN}/m207-s02-schemas.json"
BATTERY_REL = f"{EVID}/m207-s02-battery.json"

FROZEN_FILES = (
    f"{ANN}/m207-s01-codebook.md",
    f"{ANN}/m207-s01-schemas.json",
    f"{ANN}/m207-s02-coder-protocol.md",
    f"{ANN}/m207-s02-schemas.json",
    f"{EVID}/m199-s01-annotation-protocol.md",
    f"{EVID}/m199-s01-gold-sample-manifest.json",
    f"{EVID}/m207-s01-pilot-cases.json",
    f"{EVID}/m207-s01-prompt-packets.jsonl",
    f"{EVID}/m207-s01-battery.json",
    f"{EVID}/m207-s02-coder-kit-pass1.json",
    f"{EVID}/m207-s02-coder-kit-pass2.json",
)
BENIGN_CRATE = "crates/ln-decode/src/lib.rs"

CHAIN_CHECKS = (
    "gate-schemas",
    "gate-coder-kit",
    "gate-intake",
    "gate-agreement",
    "gate-adjudication",
    "adversarial-suite",
    "verifier-pilot",
    "s01-regression",
    "ruff-format-check",
    "ruff-lint",
    "adr-conformance",
)

# The hostile cases this suite must own.  ``SuiteIntegrityTests`` fails with
# EMPTY_SUITE if the registry is empty or any registered case has disappeared.
REQUIRED_HOSTILE_CASES = (
    "test_ninth_slot_fails",
    "test_label_key_fails",
    "test_authoritative_authority_fails",
    "test_provided_suggestion_status_fails",
    "test_model_invoked_fails",
    "test_rule_seed_provenance_fails",
    "test_span_beyond_eof_fails",
    "test_span_splitting_utf8_codepoint_fails",
    "test_span_not_at_origin_fails",
    "test_unknown_case_id_fails",
    "test_duplicate_coder_id_fails",
    "test_replayed_submission_id_fails",
    "test_unfilled_kit_as_submission_fails",
    "test_test_fixture_in_product_store_fails",
    "test_classification_pass_fails",
    "test_threshold_requested_fails",
    "test_gold_claim_fails",
    "test_adjudication_by_machine_fails",
    "test_second_coder_envelope_removed_refuses_publication",
    "test_report_mutation_after_adjudication_fails",
    "test_forged_receipt_with_promotion_fails",
    "test_repinned_agreement_report_fails",
    "test_unresolved_adjudication_record_fails",
    "test_tracked_battery_with_wallclock_fails",
    "test_seed_enlarged_to_181_fails",
    "test_frozen_s01_codebook_mutation_fails",
    "test_forged_product_reference_fails",
    "test_s01_regression_red_fails",
    "test_path_traversal_argument_fails",
    "test_backslash_argument_fails",
    "test_absolute_path_argument_fails",
    "test_battery_empty_result_table_fails",
)
MIN_HOSTILE_CASES = 32

TIMEOUT = 900


# --------------------------------------------------------------------------- #
# Frozen declarations read from the pinned schemas (never restated here).
# --------------------------------------------------------------------------- #


def frozen_schemas() -> dict[str, Any]:
    return json.loads((ROOT / S02_SCHEMAS).read_text(encoding="utf-8"))


def block(name: str) -> dict[str, Any]:
    return frozen_schemas()["schemas"][name]


def closed_doc(name: str, **values: Any) -> dict[str, Any]:
    """A shape-valid derived artifact, so one semantic mutation is isolated."""
    document: dict[str, Any] = dict.fromkeys(block(name)["closed_keys"])
    document["schema"] = block(name)["schema_id"]
    document["schema_version"] = 1
    document["non_claims"] = frozen_schemas()["non_claims"]
    document["lifecycle"] = frozen_schemas()["lifecycle"]
    document.update(values)
    return document


def iter_test_ids(suite: unittest.TestSuite) -> list[str]:
    identifiers: list[str] = []
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            identifiers.extend(iter_test_ids(entry))
        else:
            identifiers.append(entry.id())
    return identifiers


# --------------------------------------------------------------------------- #
# Base scaffolding.
# --------------------------------------------------------------------------- #


class SuiteBase(unittest.TestCase):
    """Shared temp-root, subprocess and assertion helpers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.base_root = cls._build_base_root()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.base_root.parent, ignore_errors=True)

    @staticmethod
    def _build_base_root() -> Path:
        holder = Path(tempfile.mkdtemp(prefix="m207-s02-suite-base-"))
        root = holder / "root"
        for relative in FROZEN_FILES:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        shutil.copytree(ROOT / FIXTURES, root / FIXTURES)
        crate = root / BENIGN_CRATE
        crate.parent.mkdir(parents=True, exist_ok=True)
        crate.write_text("// product runtime: no pilot reader here\n", encoding="utf-8")
        return root

    # -- temp scaffolding -------------------------------------------------
    def temp_dir(self, prefix: str = "m207-s02-suite-") -> Path:
        directory = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def make_root(self) -> Path:
        holder = self.temp_dir()
        root = holder / "root"
        shutil.copytree(self.base_root, root)
        return root

    def stub_chain(self, body: str, *, code: int = 0) -> Path:
        directory = self.temp_dir()
        script = directory / "s01-chain-stub.sh"
        script.write_text(f"#!/usr/bin/env bash\n{body}\nexit {code}\n", encoding="utf-8")
        return script

    def green_chain(self) -> Path:
        return self.stub_chain("echo M207_S01_VERIFY_OK")

    # -- cli --------------------------------------------------------------
    def run_verifier(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VERIFIER), "check", "--root", str(root), *extra]
        return subprocess.run(
            command,
            cwd=ROOT,
            env=CHILD_ENV,
            text=True,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
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
            command,
            cwd=ROOT,
            env=CHILD_ENV,
            text=True,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
        )

    def run_cli(
        self, script: Path, *args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(script), *args]
        return subprocess.run(
            command,
            cwd=str(cwd or ROOT),
            env=CHILD_ENV,
            text=True,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
        )

    # -- assertions -------------------------------------------------------
    def assert_ok(self, result: subprocess.CompletedProcess[str], *fragments: str) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(MARKER, result.stdout)
        self.assertNotIn(HUMAN_GATE_MARKER, result.stdout + result.stderr)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout, result.stdout)

    def assert_diagnostic(
        self, result: subprocess.CompletedProcess[str], *diagnostics: str, detail: str = ""
    ) -> None:
        self.assertNotEqual(
            result.returncode, 0, f"expected a refusal, got exit 0:\n{result.stdout}"
        )
        joined = result.stdout + result.stderr
        self.assertNotIn(HUMAN_GATE_MARKER, joined)
        matched = [name for name in diagnostics if f"FAIL {name}:" in joined]
        self.assertTrue(matched, f"expected one of {list(diagnostics)} to be named in:\n{joined}")
        if detail:
            self.assertIn(detail, joined)

    # -- battery helpers --------------------------------------------------
    def result_table(self, rows: tuple[tuple[str, int, int], ...]) -> Path:
        directory = self.temp_dir()
        path = directory / "results.tsv"
        path.write_text(
            "".join(
                f"{identifier}\t{status}\t{duration}\tuv run python {identifier}\n"
                for identifier, status, duration in rows
            ),
            encoding="utf-8",
        )
        return path

    def green_table(self, duration: int = 10) -> Path:
        return self.result_table(tuple((name, 0, duration) for name in CHAIN_CHECKS))

    def empty_table(self) -> Path:
        path = self.temp_dir() / "empty.tsv"
        path.write_text("", encoding="utf-8")
        return path

    def write_battery(self, root: Path, table: Path) -> subprocess.CompletedProcess[str]:
        return self.run_battery(root, table, "--write")

    def tracked_battery(self, root: Path) -> Path:
        return root / BATTERY_REL


# --------------------------------------------------------------------------- #
# Verifier boundary: pins, isolation, lifecycle, regression.
# --------------------------------------------------------------------------- #


class VerifierBoundaryTests(SuiteBase):
    """The slice verifier fails closed on a mutated frozen surface."""

    def test_clean_root_passes_with_counters(self) -> None:
        """The clean control must pass *and* report real work done."""
        root = self.make_root()
        self.assert_ok(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "cases=40",
            "work_family_cap=4",
            "work_families=24",
            "pinned=9/9",
            "fixture_txt=180",
            "fixture_rollup=50b48668cba5b89d",
            "lifecycle_blocks=4",
            "gates=5/5",
            "s01_regression=ok",
            "derived_artifacts=0",
            "human_pilot_performed=false",
            "human=MACHINERY_GREEN_HUMAN_ABSENT",
        )

    def test_real_root_runs_the_real_s01_chain(self) -> None:
        """The default chain is the real S01 closeout chain, as a subprocess."""
        result = self.run_verifier(ROOT)
        self.assert_ok(result, "cases=40", "gates=5/5", "s01_regression=ok")
        self.assertIn(f"s01_chain={S01_CHAIN_PATH.relative_to(ROOT).as_posix()}", result.stdout)
        self.assertIn("human_pilot_performed=false", result.stdout)

    def test_frozen_s01_codebook_mutation_fails(self) -> None:
        root = self.make_root()
        path = root / ANN / "m207-s01-codebook.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "FROZEN_SOURCE_DRIFT",
        )

    def test_frozen_s01_battery_mutation_fails(self) -> None:
        root = self.make_root()
        path = root / EVID / "m207-s01-battery.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["human_pilot_performed"] = True
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "FROZEN_SOURCE_DRIFT",
        )

    def test_frozen_s02_protocol_mutation_fails(self) -> None:
        root = self.make_root()
        path = root / ANN / "m207-s02-coder-protocol.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("[bounded]", "[unbounded]", 1),
            encoding="utf-8",
        )
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "FROZEN_SOURCE_DRIFT",
        )

    def test_frozen_kit_mutation_fails(self) -> None:
        root = self.make_root()
        path = root / EVID / "m207-s02-coder-kit-pass1.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["work_family_cap"] = 8
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "FROZEN_SOURCE_DRIFT",
        )

    def test_seed_enlarged_to_181_fails(self) -> None:
        root = self.make_root()
        (root / FIXTURES / "extra-fragment.txt").write_text("new seed\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "SEED_ENLARGED",
        )

    def test_forged_product_reference_fails(self) -> None:
        """A crate that references the pilot surface breaks prompt isolation."""
        root = self.make_root()
        crate = root / BENIGN_CRATE
        crate.write_text('const PILOT: &str = "m207-s02";\n', encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "PROMPT_ISOLATION_VIOLATION",
        )

    def test_s01_regression_red_fails(self) -> None:
        root = self.make_root()
        red = self.stub_chain("echo 'the S01 chain is red' 1>&2", code=1)
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(red)), "S01_REGRESSION_FAILED"
        )

    def test_s01_regression_marker_without_zero_exit_fails(self) -> None:
        """A marker without a green exit code is not a passing regression."""
        root = self.make_root()
        sneaky = self.stub_chain("echo M207_S01_VERIFY_OK", code=3)
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(sneaky)), "S01_REGRESSION_FAILED"
        )

    def test_path_traversal_argument_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(
            self.run_verifier(
                root, "--s01-chain", str(self.green_chain()), "--cases", "../escape.json"
            ),
            "UNSAFE_PATH",
        )

    def test_backslash_argument_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(
            self.run_verifier(
                root,
                "--s01-chain",
                str(self.green_chain()),
                "--cases",
                "prd\\annotation\\escape.json",
            ),
            "UNSAFE_PATH",
        )

    def test_absolute_path_argument_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(
            self.run_verifier(
                root,
                "--s01-chain",
                str(self.green_chain()),
                "--s02-schemas",
                "/tmp/m207-s02-schemas.json",
            ),
            "UNSAFE_PATH",
        )

    def test_missing_root_fails_closed(self) -> None:
        result = self.run_verifier(Path("/tmp/m207-s02-does-not-exist"))
        self.assert_diagnostic(result, "MISSING_ARTIFACT")
        self.assertNotIn(HUMAN_DATA_MARKER, result.stdout)

    def test_forged_receipt_with_promotion_fails(self) -> None:
        root = self.make_root()
        receipt = closed_doc(
            "pilot_receipt",
            human_pilot_performed=True,
            coder_count=2,
            adjudicator_count=1,
            case_count=40,
            promotion="promoted",
            pre_adjudication_agreement_sha256="a" * 64,
            adjudication_record_sha256="b" * 64,
        )
        path = root / EVID / "m207-s02-pilot-receipt.json"
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "PROMOTION_CLAIM",
        )

    def test_unresolved_adjudication_record_fails(self) -> None:
        root = self.make_root()
        record = closed_doc(
            "adjudication_record",
            append_only=True,
            entries=[],
            entry_count=0,
            resolved_count=0,
            unresolved_count=2,
            adjudicator_provenance="human-reviewed",
            is_gold=False,
            promotion="none",
            pre_adjudication_agreement_sha256="b" * 64,
        )
        path = root / EVID / "m207-s02-adjudication-record.json"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "UNRESOLVED_NONZERO",
        )

    def test_repinned_agreement_report_fails(self) -> None:
        """A report mutated after adjudication breaks the frozen score pin."""
        root = self.make_root()
        report = closed_doc(
            "agreement_report",
            alpha=None,
            axes=[
                {
                    "axis": "reference_decision",
                    "units_total": 40,
                    "units_used": 40,
                    "units_excluded": 0,
                    "abstained_units": 0,
                    "alpha": 0.5,
                    "observed_agreement": 0.9,
                    "measurement_status": "computed",
                }
            ],
            classification="not-authorized",
            promotion="none",
            threshold=None,
            measurement_status="computed",
            pre_adjudication=True,
            submission_refs=[],
            units_total=40,
            units_used=40,
            units_excluded=0,
            work_family_breakdown={},
            work_family_cap=4,
        )
        record = closed_doc(
            "adjudication_record",
            append_only=True,
            entries=[],
            entry_count=0,
            resolved_count=0,
            unresolved_count=0,
            adjudicator_provenance="human-reviewed",
            is_gold=False,
            promotion="none",
            pre_adjudication_agreement_sha256="b" * 64,
        )
        (root / EVID / "m207-s02-agreement-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (root / EVID / "m207-s02-adjudication-record.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "FROZEN_SOURCE_DRIFT",
            detail="re-pinned after adjudication",
        )

    def test_tracked_battery_with_wallclock_fails(self) -> None:
        root = self.make_root()
        document = closed_doc("battery", human_pilot_performed=False, model_invoked=False)
        document["checks"] = [
            {
                "check_id": name,
                "command": f"uv run python {name}",
                "diagnostic": "none",
                "exit_code": 0,
                "status": "pass",
            }
            for name in CHAIN_CHECKS
        ]
        document["checks"][0]["duration_ms"] = 12
        document["pins"] = []
        (root / BATTERY_REL).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        self.assert_diagnostic(
            self.run_verifier(root, "--s01-chain", str(self.green_chain())),
            "BATTERY_WALLCLOCK_FORBIDDEN",
        )

    def test_verifier_never_claims_a_pilot_without_one(self) -> None:
        """A receipt without its companion artifacts is red, not human-present."""
        root = self.make_root()
        receipt = closed_doc(
            "pilot_receipt",
            human_pilot_performed=True,
            coder_count=2,
            adjudicator_count=1,
            case_count=40,
            promotion="none",
            pre_adjudication_agreement_sha256="a" * 64,
            adjudication_record_sha256="b" * 64,
        )
        (root / EVID / "m207-s02-pilot-receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_verifier(root, "--s01-chain", str(self.green_chain()))
        self.assert_diagnostic(result, "MISSING_ARTIFACT")
        self.assertNotIn(HUMAN_DATA_MARKER, result.stdout)
        self.assertNotIn(MARKER, result.stdout)

    def test_never_prints_the_human_gate_marker(self) -> None:
        """No input may make a machinery run speak the human gate marker."""
        outputs: list[str] = []
        root = self.make_root()
        outputs.append(self.run_verifier(root, "--s01-chain", str(self.green_chain())).stdout)
        mutated = self.make_root()
        (mutated / EVID / "m207-s02-coder-kit-pass2.json").write_text("{}", encoding="utf-8")
        red = self.run_verifier(mutated, "--s01-chain", str(self.green_chain()))
        outputs.append(red.stdout + red.stderr)
        outputs.append(self.run_battery(root, self.green_table()).stdout)
        joined = "\n".join(outputs)
        self.assertNotIn(HUMAN_GATE_MARKER, joined)


# --------------------------------------------------------------------------- #
# Battery mode: read-only by default, no wall-clock, deterministic.
# --------------------------------------------------------------------------- #


class BatteryModeTests(SuiteBase):
    """The tracked battery stays a pure function of the observed checks."""

    def test_battery_empty_result_table_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(self.run_battery(root, self.empty_table()), "EMPTY_SUITE")

    def test_battery_missing_tracked_battery_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(self.run_battery(root, self.green_table()), "MISSING_ARTIFACT")

    def test_battery_read_only_rejects_stale_battery(self) -> None:
        root = self.make_root()
        written = self.write_battery(root, self.green_table())
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertIn(BATTERY_MARKER, written.stdout)
        path = self.tracked_battery(root)
        document = json.loads(path.read_text(encoding="utf-8"))
        document["human_pilot_performed"] = True
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assert_diagnostic(self.run_battery(root, self.green_table()), "BATTERY_STALE")

    def test_battery_read_only_leaves_tracked_bytes_untouched(self) -> None:
        """The closeout chain must be safe inside the source-integrity window."""
        root = self.make_root()
        self.assertEqual(self.write_battery(root, self.green_table()).returncode, 0)
        path = self.tracked_battery(root)
        before = path.read_bytes()
        result = self.run_battery(root, self.green_table())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(BATTERY_MARKER, result.stdout)
        self.assertIn("current", result.stdout)
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(HUMAN_GATE_MARKER, result.stdout + result.stderr)

    def test_battery_write_is_deterministic_across_durations(self) -> None:
        root = self.make_root()
        self.assertEqual(self.write_battery(root, self.green_table(duration=7)).returncode, 0)
        path = self.tracked_battery(root)
        first = path.read_bytes()
        second = self.write_battery(root, self.green_table(duration=999))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(path.read_bytes(), first)
        self.assertIn(BATTERY_TIMINGS, second.stdout)
        self.assertIn("999ms", second.stdout)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("duration", text)
        self.assertNotIn("elapsed", text)
        self.assertNotIn("wall_clock", text)
        self.assertNotIn("generated_at", text)

    def test_battery_result_table_must_carry_the_chain_set(self) -> None:
        root = self.make_root()
        partial = self.result_table(tuple((name, 0, 5) for name in CHAIN_CHECKS[:-1]))
        self.assert_diagnostic(self.run_battery(root, partial, "--write"), "SCHEMA_KEY_DRIFT")

    def test_battery_failing_row_fails(self) -> None:
        root = self.make_root()
        failing = self.result_table(
            tuple((name, 1 if name == "gate-intake" else 0, 5) for name in CHAIN_CHECKS)
        )
        self.assert_diagnostic(self.run_battery(root, failing, "--write"), "SUBCLI_FAILURE")


# --------------------------------------------------------------------------- #
# Human input: untrusted envelopes against the real intake CLI.
# --------------------------------------------------------------------------- #


class HostileSubmissionBase(SuiteBase):
    """Build hostile human submissions and feed them to the real intake CLI."""

    def envelope(self, coder_pass: int = 1, coder_id: str = "coder-1") -> dict[str, Any]:
        kit = json.loads(
            (ROOT / EVID / f"m207-s02-coder-kit-pass{coder_pass}.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / EVID / "m207-s01-pilot-cases.json").read_text(encoding="utf-8")
        )
        cases = [
            {
                "case_id": case["case_id"],
                "decision": "not_a_reference",
                "span": {"start": case["start"], "end": case["end"]},
                "slots": {},
                "abstention": "not-abstained",
            }
            for case in manifest["cases"]
        ]
        document = dict(kit["submission_template"])
        document.update(
            {
                "coder_id": coder_id,
                "provenance": "human-reviewed",
                "coder_pass": coder_pass,
                "submission_id": f"m207-s02-submission-pass-{coder_pass}",
                "cases": cases,
            }
        )
        return document

    def probe(self, envelope: dict[str, Any], name: str = "envelope-pass-1.json") -> Any:
        """Validate one envelope read-only against the real CLI, fixture-admitted."""
        directory = self.temp_dir()
        path = directory / name
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        store = directory / "store"
        record = directory / "record.json"
        result = self.run_cli(
            INTAKE,
            "run",
            "--submission",
            str(path),
            "--store",
            str(store),
            "--record",
            str(record),
            "--allow-test-fixtures",
        )
        self.assertFalse(record.exists(), "the intake wrote a record in probe mode")
        self.assertFalse(store.exists(), "the intake created a store in probe mode")
        return result

    def probe_product_mode(self, envelope: dict[str, Any], name: str) -> Any:
        directory = self.temp_dir()
        path = directory / name
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self.run_cli(INTAKE, "run", "--submission", str(path))

    def store_run(self, envelopes: dict[str, dict[str, Any]]) -> Any:
        directory = self.temp_dir()
        store = directory / "store"
        store.mkdir()
        for name, envelope in envelopes.items():
            (store / name).write_text(
                json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        return self.run_cli(
            INTAKE,
            "run",
            "--store",
            str(store),
            "--record",
            str(directory / "record.json"),
            "--allow-test-fixtures",
        )

    def multibyte_case_offset(self) -> tuple[int, int]:
        """A case index and a byte offset that lands inside a code point."""
        manifest = json.loads(
            (ROOT / EVID / "m207-s01-pilot-cases.json").read_text(encoding="utf-8")
        )
        for index, case in enumerate(manifest["cases"]):
            raw = (ROOT / FIXTURES / f"{case['fragment_id']}.txt").read_bytes()
            for offset in range(1, len(raw)):
                if 0x80 <= raw[offset] < 0xC0:
                    return index, offset
        raise AssertionError("no frozen fragment holds a multi-byte code point")


class HostileSubmissionTests(HostileSubmissionBase):
    """Every hostile human envelope must be refused by name."""

    def test_clean_envelope_is_admitted_read_only(self) -> None:
        """Positive control: an unmutated envelope is admitted, nothing written."""
        result = self.probe(self.envelope())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("M207_S02_INTAKE_ACCEPTED", result.stdout)
        self.assertNotIn(HUMAN_GATE_MARKER, result.stdout + result.stderr)

    def test_ninth_slot_fails(self) -> None:
        document = self.envelope()
        document["cases"][0]["slots"] = {"ninth_slot": "reference"}
        self.assert_diagnostic(self.probe(document), "NINTH_SLOT")

    def test_label_key_fails(self) -> None:
        document = self.envelope()
        document["label"] = "reference"
        self.assert_diagnostic(self.probe(document), "LEAK_FORBIDDEN_KEY", "SCHEMA_KEY_DRIFT")

    def test_authoritative_authority_fails(self) -> None:
        document = self.envelope()
        document["authority"] = "authoritative"
        self.assert_diagnostic(self.probe(document), "AUTHORITY_CLAIM")

    def test_provided_suggestion_status_fails(self) -> None:
        document = self.envelope()
        document["suggestion_status"] = "provided"
        self.assert_diagnostic(self.probe(document), "AUTHORITY_CLAIM")

    def test_model_invoked_fails(self) -> None:
        document = self.envelope()
        document["model_invoked"] = True
        self.assert_diagnostic(self.probe(document), "MODEL_INVOKED")

    def test_rule_seed_provenance_fails(self) -> None:
        document = self.envelope()
        document["provenance"] = "rule-seed"
        self.assert_diagnostic(self.probe(document), "PROVENANCE_NOT_HUMAN")

    def test_span_beyond_eof_fails(self) -> None:
        document = self.envelope()
        case = document["cases"][0]
        case["span"] = {"start": case["span"]["start"], "end": case["span"]["end"] + 8}
        self.assert_diagnostic(self.probe(document), "SPAN_BEYOND_EOF")

    def test_span_splitting_utf8_codepoint_fails(self) -> None:
        index, offset = self.multibyte_case_offset()
        document = self.envelope()
        document["cases"][index]["span"] = {"start": offset, "end": offset + 1}
        self.assert_diagnostic(self.probe(document), "SPAN_NOT_UTF8_BOUNDARY")

    def test_span_not_at_origin_fails(self) -> None:
        """The offered window is the whole fragment, so a leaving span is caught here."""
        document = self.envelope()
        document["cases"][0]["span"] = {"start": -1, "end": 5}
        self.assert_diagnostic(self.probe(document), "SPAN_NOT_ORIGIN")

    def test_unknown_case_id_fails(self) -> None:
        document = self.envelope()
        document["cases"][0]["case_id"] = "m207-s01-case-999"
        self.assert_diagnostic(self.probe(document), "UNKNOWN_CASE_ID")

    def test_duplicate_coder_id_fails(self) -> None:
        first = self.envelope(coder_pass=1, coder_id="coder-same")
        second = self.envelope(coder_pass=2, coder_id="coder-same")
        result = self.store_run({"submission-pass-1.json": first, "submission-pass-2.json": second})
        self.assert_diagnostic(result, "DUPLICATE_CODER_ID", "SUBMISSION_CONFLICT")

    def test_replayed_submission_id_fails(self) -> None:
        first = self.envelope(coder_pass=1, coder_id="coder-1")
        replay = self.envelope(coder_pass=1, coder_id="coder-1b")
        result = self.store_run(
            {"submission-pass-1.json": first, "submission-pass-1b.json": replay}
        )
        self.assert_diagnostic(
            result, "DUPLICATE_SUBMISSION_ID", "DUPLICATE_CODER_ID", "SUBMISSION_CONFLICT"
        )

    def test_unfilled_kit_as_submission_fails(self) -> None:
        kit = json.loads(
            (ROOT / EVID / "m207-s02-coder-kit-pass1.json").read_text(encoding="utf-8")
        )
        self.assert_diagnostic(self.probe(kit, "kit-as-submission.json"), "UNFILLED_SUBMISSION")

    def test_test_fixture_in_product_store_fails(self) -> None:
        """A fixture-marked envelope may never enter the product store."""
        result = self.probe_product_mode(self.envelope(), "fixture-envelope.json")
        self.assert_diagnostic(result, "TEST_FIXTURE_IN_STORE")

    def test_classification_pass_fails(self) -> None:
        document = self.envelope()
        document["classification"] = "pass"
        self.assert_diagnostic(self.probe(document), "CLASSIFICATION_REQUESTED")

    def test_threshold_requested_fails(self) -> None:
        document = self.envelope()
        document["threshold"] = 0.8
        self.assert_diagnostic(self.probe(document), "THRESHOLD_REQUESTED")

    def test_gold_claim_fails(self) -> None:
        document = self.envelope()
        document["cases"][0]["is_gold"] = True
        self.assert_diagnostic(self.probe(document), "GOLD_CLAIM")


# --------------------------------------------------------------------------- #
# The full synthetic pilot: real CLIs, end to end, outside the repository.
# --------------------------------------------------------------------------- #


class PilotContourTests(HostileSubmissionBase):
    """Drive the whole human contour over synthetic data outside the product tree."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.pilot = cls._build_pilot()

    @classmethod
    def _envelope(cls, coder_pass: int, coder_id: str) -> dict[str, Any]:
        kit = json.loads(
            (ROOT / EVID / f"m207-s02-coder-kit-pass{coder_pass}.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / EVID / "m207-s01-pilot-cases.json").read_text(encoding="utf-8")
        )
        cases = []
        for index, case in enumerate(manifest["cases"]):
            case_row = {
                "case_id": case["case_id"],
                "decision": "not_a_reference",
                "span": {"start": case["start"], "end": case["end"]},
                "slots": {},
                "abstention": "not-abstained",
            }
            if index == 0:
                case_row["decision"] = "not_a_reference"
            if index == 1:
                case_row["abstention"] = "not-abstained"
            cases.append(case_row)
        # Deliberate disagreements so the inventory is non-empty: a differing
        # decision on case 1, a differing abstention on case 2, a differing slot
        # on case 3.
        if coder_pass == 2:
            cases[0]["decision"] = "reference"
            cases[1]["abstention"] = "ambiguous"
        if coder_pass == 1:
            cases[2]["slots"] = {"date": "2013-12-28"}
        document = dict(kit["submission_template"])
        document.update(
            {
                "coder_id": coder_id,
                "provenance": "human-reviewed",
                "coder_pass": coder_pass,
                "submission_id": f"m207-s02-submission-pass-{coder_pass}",
                "cases": cases,
            }
        )
        return document

    @classmethod
    def _resolution(cls, axis: str) -> str:
        if axis == "reference_decision":
            return "reference"
        if axis == "abstention":
            return "not-abstained"
        if axis == "span_exact":
            return "span_pass_1"
        if axis.startswith("slot_"):
            return "slot_present"
        raise AssertionError(f"no closed resolution for axis {axis!r}")

    @classmethod
    def _build_pilot(cls) -> dict[str, Any]:
        base = Path(tempfile.mkdtemp(prefix="m207-s02-pilot-"))
        store = base / "submissions"
        store.mkdir()
        for coder_pass, coder_id in ((1, "coder-alpha"), (2, "coder-beta")):
            envelope = cls._envelope(coder_pass, coder_id)
            path = store / f"submission-pass-{coder_pass}.json"
            path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
        record = base / "intake-record.json"
        report = base / "agreement-report.json"
        inventory = base / "disagreement-inventory.json"
        adjudications = base / "adjudications"
        adjudications.mkdir()
        adjudication_record = base / "adjudication-record.json"
        receipt = base / "pilot-receipt.json"

        def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(script), *args],
                cwd=str(ROOT),
                env=CHILD_ENV,
                text=True,
                capture_output=True,
                check=False,
                timeout=TIMEOUT,
            )

        intake = run(
            INTAKE,
            "run",
            "--store",
            str(store),
            "--record",
            str(record),
            "--allow-test-fixtures",
        )
        agreement = run(
            AGREEMENT,
            "run",
            "--store",
            str(store),
            "--intake",
            str(record),
            "--report",
            str(report),
            "--inventory",
            str(inventory),
            "--allow-test-fixtures",
        )
        entries: list[dict[str, Any]] = []
        if inventory.is_file():
            for index, entry in enumerate(
                json.loads(inventory.read_text(encoding="utf-8")).get("entries") or [], start=1
            ):
                entries.append(
                    {
                        "schema": "m207-s02-adjudication-input/v1",
                        "schema_version": 1,
                        "adjudication_id": f"adjudication-{index:03d}",
                        "adjudicator_id": "adjudicator-1",
                        "axis": entry["axis"],
                        "case_id": entry["case_id"],
                        "resolution": cls._resolution(str(entry["axis"])),
                        "provenance": "human-reviewed",
                        "rationale": "resolved against the closed codebook decision space",
                        "supersedes": None,
                        "is_gold": False,
                        "non_claims": frozen_schemas()["non_claims"],
                        "lifecycle": frozen_schemas()["lifecycle"],
                    }
                )
        for index, entry in enumerate(entries, start=1):
            (adjudications / f"adjudication-{index:03d}.json").write_text(
                json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        adjudication = run(
            ADJUDICATE,
            "run",
            "--store",
            str(adjudications),
            "--agreement",
            str(report),
            "--inventory",
            str(inventory),
            "--record",
            str(adjudication_record),
            "--receipt",
            str(receipt),
            "--allow-test-fixtures",
        )
        return {
            "base": base,
            "store": store,
            "record": record,
            "report": report,
            "inventory": inventory,
            "adjudications": adjudications,
            "adjudication_record": adjudication_record,
            "receipt": receipt,
            "intake": intake,
            "agreement": agreement,
            "adjudication": adjudication,
            "entry_count": len(entries),
        }

    def test_full_synthetic_pilot_writes_receipt_and_agreement(self) -> None:
        """The contour really runs end to end on real CLIs, outside the product tree."""
        self.assertEqual(self.pilot["intake"].returncode, 0, self.pilot["intake"].stderr)
        self.assertEqual(self.pilot["agreement"].returncode, 0, self.pilot["agreement"].stderr)
        self.assertEqual(
            self.pilot["adjudication"].returncode, 0, self.pilot["adjudication"].stderr
        )
        receipt = json.loads(self.pilot["receipt"].read_text(encoding="utf-8"))
        self.assertIs(receipt["human_pilot_performed"], True)
        self.assertEqual(receipt["coder_count"], 2)
        self.assertGreaterEqual(receipt["adjudicator_count"], 1)
        self.assertEqual(receipt["case_count"], 40)
        for key in ("intake", "agreement", "adjudication"):
            joined = self.pilot[key].stdout + self.pilot[key].stderr
            self.assertNotIn(HUMAN_GATE_MARKER, joined)

    def test_adjudication_by_machine_fails(self) -> None:
        """A machine-authored adjudication must be refused by name."""
        directory = self.temp_dir()
        store = directory / "adjudications"
        store.mkdir()
        entry = {
            "schema": "m207-s02-adjudication-input/v1",
            "schema_version": 1,
            "adjudication_id": "adjudication-001",
            "adjudicator_id": "rule-engine",
            "axis": "reference_decision",
            "case_id": "m207-s01-case-001",
            "resolution": "reference",
            "provenance": "model",
            "rationale": "the machine decided",
            "supersedes": None,
        }
        (store / "adjudication-001.json").write_text(json.dumps(entry, indent=2) + "\n")
        result = self.run_cli(
            ADJUDICATE,
            "run",
            "--store",
            str(store),
            "--agreement",
            str(self.pilot["report"]),
            "--inventory",
            str(self.pilot["inventory"]),
            "--record",
            str(directory / "record.json"),
            "--receipt",
            str(directory / "receipt.json"),
            "--allow-test-fixtures",
        )
        self.assert_diagnostic(result, "ADJUDICATOR_PROVENANCE_NOT_HUMAN")
        self.assertFalse((directory / "record.json").exists())

    def test_verifier_reports_human_data_present_once_a_receipt_exists(self) -> None:
        """Green machinery plus a real receipt is never reported as machinery-green."""
        root = self.make_root()
        for source, relative in (
            (self.pilot["record"], f"{EVID}/m207-s02-intake-record.json"),
            (self.pilot["report"], f"{EVID}/m207-s02-agreement-report.json"),
            (self.pilot["inventory"], f"{EVID}/m207-s02-disagreement-inventory.json"),
            (self.pilot["adjudication_record"], f"{EVID}/m207-s02-adjudication-record.json"),
            (self.pilot["receipt"], f"{EVID}/m207-s02-pilot-receipt.json"),
        ):
            shutil.copyfile(source, root / relative)
        result = self.run_verifier(root, "--s01-chain", str(self.green_chain()))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(HUMAN_DATA_MARKER, result.stdout)
        self.assertNotIn(MARKER, result.stdout)
        self.assertIn("human_pilot_performed=true", result.stdout)
        self.assertIn("derived_artifacts=5", result.stdout)
        self.assertNotIn(HUMAN_GATE_MARKER, result.stdout + result.stderr)

    def test_second_coder_envelope_removed_refuses_publication(self) -> None:
        """RC28-F01: one coder is a refusal, never a promoted alpha."""
        directory = self.temp_dir()
        store = directory / "submissions"
        shutil.copytree(self.pilot["store"], store)
        record = shutil.copyfile(self.pilot["record"], directory / "intake-record.json")
        report = directory / "agreement-report.json"
        before = self.pilot["report"].read_bytes()
        (store / "submission-pass-2.json").unlink()
        result = self.run_cli(
            AGREEMENT,
            "run",
            "--store",
            str(store),
            "--intake",
            str(record),
            "--report",
            str(report),
            "--inventory",
            str(directory / "inventory.json"),
            "--allow-test-fixtures",
        )
        self.assert_diagnostic(
            result, "ONE_CODER_ONLY", "SUBMISSION_CONFLICT", "HUMAN_PILOT_ABSENT"
        )
        self.assertFalse(report.exists(), "a half-pilot report was published")
        self.assertEqual(self.pilot["report"].read_bytes(), before)
        frozen = json.loads(self.pilot["report"].read_text(encoding="utf-8"))
        self.assertNotEqual(frozen["alpha"], 1.0)

    def test_report_mutation_after_adjudication_fails(self) -> None:
        """Re-pinning the frozen pre-adjudication score is detected."""
        directory = self.temp_dir()
        report = shutil.copyfile(self.pilot["report"], directory / "agreement-report.json")
        inventory = shutil.copyfile(self.pilot["inventory"], directory / "inventory.json")
        record = directory / "adjudication-record.json"
        receipt = directory / "pilot-receipt.json"
        first = self.run_cli(
            ADJUDICATE,
            "run",
            "--store",
            str(self.pilot["adjudications"]),
            "--agreement",
            str(report),
            "--inventory",
            str(inventory),
            "--record",
            str(record),
            "--receipt",
            str(receipt),
            "--allow-test-fixtures",
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        pinned = record.read_bytes()
        receipt_bytes = receipt.read_bytes()
        # A byte-level mutation of the frozen pre-adjudication score: the pin in
        # the published record no longer describes the report on disk.
        report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        second = self.run_cli(
            ADJUDICATE,
            "run",
            "--store",
            str(self.pilot["adjudications"]),
            "--agreement",
            str(report),
            "--inventory",
            str(inventory),
            "--record",
            str(record),
            "--receipt",
            str(receipt),
            "--allow-test-fixtures",
        )
        self.assert_diagnostic(second, "FROZEN_SOURCE_DRIFT")
        self.assertEqual(record.read_bytes(), pinned, "the record was rewritten after the freeze")
        self.assertEqual(receipt.read_bytes(), receipt_bytes)


# --------------------------------------------------------------------------- #
# Suite integrity: an empty suite is itself a failure.
# --------------------------------------------------------------------------- #


class SuiteIntegrityTests(unittest.TestCase):
    """The hostile registry must be populated and every case must exist."""

    def test_suite_registry_is_not_empty_and_all_cases_exist(self) -> None:
        if not REQUIRED_HOSTILE_CASES:
            self.fail("FAIL EMPTY_SUITE: the hostile case registry is empty")
        suite = unittest.TestLoader().loadTestsFromName(__name__)
        identifiers = {identifier.rsplit(".", 1)[-1] for identifier in iter_test_ids(suite)}
        missing = [name for name in REQUIRED_HOSTILE_CASES if name not in identifiers]
        self.assertEqual(missing, [], f"registered hostile case(s) missing: {missing}")
        self.assertGreaterEqual(
            len(identifiers),
            MIN_HOSTILE_CASES,
            f"the suite carries only {len(identifiers)} case(s)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
