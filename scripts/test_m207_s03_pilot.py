#!/usr/bin/env python3
"""Offline adversarial subprocess suite for the M207 S03 frozen-evaluation contour (T05).

Every case invokes a real CLI -- the slice verifier ``scripts/m207_s03_pilot.py``,
the rate engine ``scripts/m207_s03_metrics.py``, the manifest gate
``scripts/m207_s03_eval_manifest.py``, or the reused S02 input contour -- on a
throw-away copy of the frozen surface or on a synthetic human world inside
``tempfile.mkdtemp``, mutates exactly one thing, and asserts that the run fails
closed with a *named* diagnostic (``FAIL <NAME>:``).  Nothing is mocked, nothing
is imported from the tools under test (subprocess only, D472), and nothing here
reads ``.gsd/``, touches the network, the git index, the product stores or the
repository working tree.

WHY THIS EXISTS BEFORE THE NUMBERS DO.  S03 owns the most fabricable surface of
the pilot: a *metric*.  An empty stratum silently becomes ``1.0``, a proxy
artifact is read as an "independent evaluation", the holdout is scored on the dev
slice, and a producer promotes itself into a measurement.  The refusals therefore
have to be proven *before* a human types anything, and they have to be proven at
the CLI boundary rather than against in-process helpers.  The suite is written
against the frozen contract, so a later change that quietly widens a denominator,
drops the empty ``garant`` stratum or accepts a proxy input turns it red.

The positive controls matter as much as the refusals: a suite that merely rejects
everything is worthless.  So the clean catalogue root must still verify with
``M207_S03_MACHINERY_OK``, a synthetic two-pass human world driven through the
real S02 intake -> agreement -> adjudication CLIs must still publish a report with
honest denominators, and that report must pass the engine's own ``check``.

The two invariants this slice cannot delegate:

* **RC28-F01** -- a producer may never promote itself into a measurement: with an
  absent human reference the engine exits ``3`` with ``HUMAN_PILOT_ABSENT`` and
  writes **no** report, and ``0.0``/``1.0`` with a zero denominator is
  ``RATE_UNDEFINED`` rather than a number;
* **the human gate marker** -- ``M207_S03_VERIFY_OK`` must never be printed by any
  machinery run, whatever the input.

An empty suite is itself a failure: ``SuiteIntegrityTests`` requires the hostile
case registry to be populated and every registered case to exist.
"""

from __future__ import annotations

import atexit
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
VERIFIER = ROOT / "scripts" / "m207_s03_pilot.py"
METRICS = ROOT / "scripts" / "m207_s03_metrics.py"
MANIFEST_TOOL = ROOT / "scripts" / "m207_s03_eval_manifest.py"
INTAKE = ROOT / "scripts" / "m207_s02_intake.py"
AGREEMENT = ROOT / "scripts" / "m207_s02_agreement.py"
ADJUDICATE = ROOT / "scripts" / "m207_s02_adjudicate.py"

# The battery opt-ins must never leak into a child process: a case that expects the
# read-only contract would otherwise observe a write, and a "writes no artifact"
# case would observe a created artifact.
WRITE_ENV_VARS = ("M207_S03_WRITE_BATTERY", "M207_S02_WRITE_BATTERY")
CHILD_ENV = {key: value for key, value in os.environ.items() if key not in WRITE_ENV_VARS}

MARKER = "M207_S03_MACHINERY_OK"
HUMAN_DATA_MARKER = "M207_S03_MACHINERY_HUMAN_DATA_PRESENT"
BATTERY_MARKER = "M207_S03_BATTERY_OK"
HUMAN_GATE_MARKER = "M207_S03_VERIFY_OK"
METRICS_MARKER = "M207_S03_METRICS_OK"

ANN = "prd/annotation"
EVID = "prd/migration/rust-evidence"
FIXTURE = "crates/ln-decode/tests/fixtures/npa-lawref"

S01_CASES = f"{EVID}/m207-s01-pilot-cases.json"
KIT_PASS1 = f"{EVID}/m207-s02-coder-kit-pass1.json"
KIT_PASS2 = f"{EVID}/m207-s02-coder-kit-pass2.json"
S02_SCHEMAS = f"{ANN}/m207-s02-schemas.json"
S02_PROTOCOL = f"{ANN}/m207-s02-coder-protocol.md"
S03_SCHEMAS = f"{ANN}/m207-s03-schemas.json"
S03_PROTOCOL = f"{ANN}/m207-s03-eval-protocol.md"
S03_MANIFEST = f"{EVID}/m207-s03-eval-manifest.json"
S03_LEAKAGE = f"{EVID}/m207-s03-leakage-report.json"
C3_MANIFEST = f"{EVID}/m203-s08-c3-holdout-manifest.json"
REPORT = f"{EVID}/m207-s03-evaluation-report.json"
BATTERY = f"{EVID}/m207-s03-battery.json"
SUBMISSIONS = f"{ANN}/m207-s02-submissions"
ADJUDICATIONS = f"{ANN}/m207-s02-adjudications"
INTAKE_RECORD = f"{EVID}/m207-s02-intake-record.json"
AGREEMENT_REPORT = f"{EVID}/m207-s02-agreement-report.json"
INVENTORY = f"{EVID}/m207-s02-disagreement-inventory.json"
ADJUDICATION_RECORD = f"{EVID}/m207-s02-adjudication-record.json"
PILOT_RECEIPT = f"{EVID}/m207-s02-pilot-receipt.json"

# The frozen content pins the verifier re-hashes.  This suite copies exactly these
# files plus the sources the manifest declares, and nothing else.
FROZEN_FILES = (
    f"{ANN}/m207-s01-codebook.md",
    f"{ANN}/m207-s01-schemas.json",
    S01_CASES,
    f"{EVID}/m207-s01-prompt-packets.jsonl",
    f"{EVID}/m207-s01-battery.json",
    S02_PROTOCOL,
    S02_SCHEMAS,
    KIT_PASS1,
    KIT_PASS2,
    f"{EVID}/m207-s02-battery.json",
    S03_PROTOCOL,
    S03_SCHEMAS,
    S03_MANIFEST,
    S03_LEAKAGE,
)

# The nine frozen battery check ids (T06's chain must match them by name).
CHAIN_CHECKS = (
    "s03_schemas",
    "s03_eval_manifest",
    "s03_metrics",
    "s03_hostile_suite",
    "s03_machinery_verifier",
    "s02_regression",
    "ruff_format",
    "ruff_check",
    "adr_conformance",
)

# The hostile cases this suite must own.  ``SuiteIntegrityTests`` fails with
# EMPTY_SUITE if the registry is empty or any registered case has disappeared.
REQUIRED_HOSTILE_CASES = (
    "test_clean_root_passes_with_counters",
    "test_real_root_verifies_machinery_green",
    "test_frozen_s02_artifact_mutation_fails",
    "test_frozen_s03_protocol_mutation_fails",
    "test_missing_root_fails_closed",
    "test_seed_enlarged_to_181_fails",
    "test_work_family_dominance_fails",
    "test_holdout_leakage_fails",
    "test_provider_stratum_dropped_fails",
    "test_provider_quota_unjustified_fails",
    "test_provider_misattributed_fails",
    "test_report_without_human_data_fails",
    "test_authority_claim_fails",
    "test_threshold_requested_fails",
    "test_classification_requested_fails",
    "test_promotion_claim_fails",
    "test_gold_claim_fails",
    "test_model_invoked_fails",
    "test_crates_reference_fails",
    "test_path_traversal_argument_fails",
    "test_absolute_path_argument_fails",
    "test_verifier_never_prints_the_human_gate_marker",
    "test_s02_chain_failure_fails",
    "test_battery_empty_result_table_fails",
    "test_battery_result_table_must_carry_the_chain_set",
    "test_battery_failing_row_fails",
    "test_battery_missing_tracked_battery_fails",
    "test_battery_stale_tracked_battery_fails",
    "test_absent_human_reference_refuses_and_publishes_nothing",
    "test_synthetic_report_has_honest_denominators",
    "test_imputed_zero_value_fails",
    "test_imputed_one_value_fails",
    "test_metric_provider_stratum_dropped_fails",
    "test_metric_provider_misattributed_fails",
    "test_metric_abstention_collapse_fails",
    "test_metric_measurement_status_drift_fails",
    "test_metric_dev_slice_is_never_an_evaluation",
    "test_metric_report_without_human_reference_fails",
    "test_metric_report_missing_with_human_reference_fails",
    "test_metric_proxy_input_is_refused",
    "test_metric_unresolvable_store_never_yields_a_measurement",
    "test_store_path_traversal_fails",
    "test_metric_pre_adjudication_pin_drift_fails",
    "test_c3_isolation_overlap_fails",
    "test_c3_unsealed_fails",
    "test_metadata_rederived_fails",
    "test_cases_manifest_unsafe_path_fails",
    "test_ninth_slot_fails",
)
MIN_HOSTILE_CASES = 40

TIMEOUT = 900


def iter_test_ids(suite: unittest.TestSuite) -> list[str]:
    identifiers: list[str] = []
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            identifiers.extend(iter_test_ids(entry))
        else:
            identifiers.append(entry.id())
    return identifiers


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def rewrite(path: Path, mutate: Any) -> None:
    document = load_json(path)
    mutate(document)
    dump_json(path, document)


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
        """A catalogue-shaped copy: the pinned files plus every declared upstream source."""
        holder = Path(tempfile.mkdtemp(prefix="m207-s03-suite-base-"))
        root = holder / "root"
        for relative in FROZEN_FILES:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        manifest = load_json(ROOT / S03_MANIFEST)
        for entry in manifest["pins"]["sources"].values():
            relative = str(entry["path"])
            target = root / relative
            if target.is_file():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        shutil.copytree(ROOT / FIXTURE, root / FIXTURE)
        # A benign product crate: the isolation scan must have something to scan.
        crate = root / "crates" / "ln-decode" / "src"
        crate.mkdir(parents=True, exist_ok=True)
        (crate / "lib.rs").write_text("pub fn version() -> u8 { 1 }\n", encoding="utf-8")
        (root / "crates" / "ln-decode" / "Cargo.toml").write_text(
            '[package]\nname = "ln-decode"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        return root

    # -- temp scaffolding -------------------------------------------------
    def temp_dir(self, prefix: str = "m207-s03-suite-") -> Path:
        directory = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def make_root(self) -> Path:
        holder = self.temp_dir()
        root = holder / "root"
        shutil.copytree(self.base_root, root)
        return root

    def world_clone(self) -> Path:
        holder = self.temp_dir(prefix="m207-s03-suite-world-")
        root = holder / "root"
        shutil.copytree(world_root(), root)
        return root

    @staticmethod
    def real_root_carries_human_data() -> bool:
        """True once an operator has dropped an envelope into a fixed human store.

        The suite drives temp copies everywhere else; only one positive control
        looks at the repository itself, and that control is only meaningful while
        the repository is still human-absent.
        """
        return any(
            (ROOT / store).is_dir() and any((ROOT / store).glob("*.json"))
            for store in (SUBMISSIONS, ADJUDICATIONS)
        )

    # -- hand-built CLI doubles -------------------------------------------
    def stub_chain(self, body: str, *, code: int = 0) -> Path:
        directory = self.temp_dir(prefix="m207-s03-suite-chain-")
        script = directory / "s02-chain-stub.sh"
        script.write_text(f"#!/usr/bin/env bash\n{body}\nexit {code}\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    def green_chain(self) -> Path:
        return self.stub_chain("echo M207_S02_VERIFY_OK")

    def result_table(self, rows: tuple[tuple[str, int, int], ...]) -> Path:
        path = self.temp_dir(prefix="m207-s03-suite-table-") / "results.tsv"
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
        path = self.temp_dir(prefix="m207-s03-suite-table-") / "empty.tsv"
        path.write_text("", encoding="utf-8")
        return path

    # -- cli --------------------------------------------------------------
    def run_cli(self, script: Path, *args: str, cwd: Path | None = None) -> Any:
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

    def run_verifier(self, root: Path, *extra: str) -> Any:
        return self.run_cli(
            VERIFIER,
            "check",
            "--root",
            str(root),
            "--s02-chain",
            str(self.green_chain()),
            *extra,
        )

    def run_battery(self, root: Path, results: Path, *extra: str) -> Any:
        return self.run_cli(
            VERIFIER,
            "battery",
            "--root",
            str(root),
            "--results",
            str(results),
            *extra,
        )

    def run_metrics(self, root: Path, mode: str, *extra: str) -> Any:
        return self.run_cli(METRICS, mode, "--root", str(root), *extra)

    def run_manifest(self, root: Path, mode: str, *extra: str) -> Any:
        return self.run_cli(MANIFEST_TOOL, mode, "--root", str(root), *extra)

    # -- assertions -------------------------------------------------------
    def assert_ok(self, result: Any, *fragments: str) -> None:
        joined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, joined)
        self.assertIn(MARKER, result.stdout)
        self.assertNotIn(HUMAN_GATE_MARKER, joined)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout, result.stdout)

    def assert_diagnostic(self, result: Any, *diagnostics: str, detail: str = "") -> None:
        joined = result.stdout + result.stderr
        self.assertNotEqual(
            result.returncode, 0, f"expected a refusal, got exit 0:\n{result.stdout}"
        )
        self.assertNotIn(HUMAN_GATE_MARKER, joined)
        matched = [name for name in diagnostics if f"FAIL {name}:" in joined]
        self.assertTrue(matched, f"expected one of {list(diagnostics)} to be named in:\n{joined}")
        if detail:
            self.assertIn(detail, joined)


# --------------------------------------------------------------------------- #
# Verifier boundary: pins, counters, strata, claims, isolation.
# --------------------------------------------------------------------------- #


class VerifierBoundaryTests(SuiteBase):
    """The slice verifier fails closed on a mutated frozen surface."""

    def test_clean_root_passes_with_counters(self) -> None:
        """Positive control: the clean catalogue verifies and reports real work."""
        self.assert_ok(
            self.run_verifier(self.make_root()),
            "pinned=14/14",
            "cases=40",
            "families=24",
            "work_family_cap=4",
            "holdout_cases=14",
            "provider_strata=consultant:40,garant:0",
            "fragments=180",
            "aspects=6",
            "battery_checks=9",
            "diagnostics=80",
            "s02_regression=exit0",
            "report=absent",
            "human_pilot_performed=false",
            "human=MACHINERY_GREEN_HUMAN_ABSENT",
        )

    def test_real_root_verifies_machinery_green(self) -> None:
        """The repository itself is green, and the default chain is the real S02 one.

        The assertion pins the *pre-pilot* catalogue
        (``human_pilot_performed=false``).  Once an operator performs the S03
        human pilot the real root is no longer human-absent -- and a human
        reference without a published report is a lawful refusal
        (``REPORT_MISSING_WITH_HUMAN_DATA``) -- so this control stands down
        instead of turning the closing chain red and making the human ending
        unreachable.  The human-absent machinery path keeps its positive control
        in ``test_clean_root_passes_with_counters`` (a temp root), and the
        post-pilot path is covered by the closing chain's own verifier row.
        """
        if self.real_root_carries_human_data():
            self.skipTest(
                "the real repository carries a human pilot: the pre-pilot machinery-green "
                "assertion does not apply"
            )
        result = self.run_cli(
            VERIFIER, "check", "--root", str(ROOT), "--s02-chain", str(self.green_chain())
        )
        self.assert_ok(result, "pinned=14/14", "cases=40", "human_pilot_performed=false")
        # The default chain this verifier re-runs is the real S02 closeout chain.
        self.assertTrue((ROOT / "scripts" / "m207_s02_t07_verify.sh").is_file())

    def test_frozen_s02_artifact_mutation_fails(self) -> None:
        root = self.make_root()
        (root / S02_PROTOCOL).write_text("mutated protocol\n", encoding="utf-8")
        self.assert_diagnostic(self.run_verifier(root), "FROZEN_SOURCE_DRIFT")

    def test_frozen_s03_protocol_mutation_fails(self) -> None:
        root = self.make_root()
        path = root / S03_PROTOCOL
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_diagnostic(self.run_verifier(root), "FROZEN_SOURCE_DRIFT")

    def test_missing_root_fails_closed(self) -> None:
        missing = self.temp_dir() / "absent"
        self.assert_diagnostic(self.run_verifier(missing), "MISSING_ARTIFACT")

    def test_seed_enlarged_to_181_fails(self) -> None:
        """The 180-fragment seed is a denominator boundary, not a suggestion."""
        root = self.make_root()
        (root / FIXTURE / "npa-frag-181.txt").write_text("extra\n", encoding="utf-8")
        self.assert_diagnostic(self.run_verifier(root), "SEED_ENLARGED")

    def test_work_family_dominance_fails(self) -> None:
        """A fifth case of one Work family breaks the held-out family cap of four."""
        root = self.make_root()

        def mutate(document: dict[str, Any]) -> None:
            counts: dict[str, int] = {}
            for case in document["cases"]:
                counts[case["work_family"]] = counts.get(case["work_family"], 0) + 1
            capped = sorted(name for name, count in counts.items() if count == 4)[0]
            donor = sorted(name for name, count in counts.items() if count < 4 and name != capped)
            for case in document["cases"]:
                if case["work_family"] == donor[0]:
                    case["work_family"] = capped
                    return

        rewrite(root / S03_MANIFEST, mutate)
        self.assert_diagnostic(self.run_verifier(root), "WORK_FAMILY_DOMINANCE")

    def test_holdout_leakage_fails(self) -> None:
        """A family cannot straddle the holdout and the dev slice."""
        root = self.make_root()

        def mutate(document: dict[str, Any]) -> None:
            holdout = sorted(document["holdout_families"])[0]
            for case in document["cases"]:
                if case["work_family"] == holdout:
                    case["family_scope"] = "dev"
                    return

        rewrite(root / S03_MANIFEST, mutate)
        self.assert_diagnostic(self.run_verifier(root), "HOLDOUT_LEAKAGE")

    def test_provider_stratum_dropped_fails(self) -> None:
        root = self.make_root()

        def mutate(document: dict[str, Any]) -> None:
            document["provider_strata"] = [
                row for row in document["provider_strata"] if row["provider"] != "garant"
            ]

        rewrite(root / S03_MANIFEST, mutate)
        self.assert_diagnostic(self.run_verifier(root), "PROVIDER_STRATUM_DROPPED")

    def test_provider_quota_unjustified_fails(self) -> None:
        root = self.make_root()

        def mutate(document: dict[str, Any]) -> None:
            for row in document["provider_strata"]:
                if row["provider"] == "garant":
                    row["quota"] = 5

        rewrite(root / S03_MANIFEST, mutate)
        self.assert_diagnostic(self.run_verifier(root), "PROVIDER_QUOTA_UNJUSTIFIED")

    def test_provider_misattributed_fails(self) -> None:
        """Provider attribution follows the declared root, never digits in a file name."""
        root = self.make_root()

        def mutate(document: dict[str, Any]) -> None:
            document["cases"][0]["provider"] = "garant"

        rewrite(root / S03_MANIFEST, mutate)
        self.assert_diagnostic(self.run_verifier(root), "PROVIDER_MISATTRIBUTED")

    def test_report_without_human_data_fails(self) -> None:
        """A report exists iff an independent human reference exists."""
        root = self.make_root()
        (root / REPORT).write_text("{}\n", encoding="utf-8")
        self.assert_diagnostic(self.run_verifier(root), "REPORT_WITHOUT_HUMAN_DATA")

    def _claim(self, root: Path, key: str, value: Any) -> None:
        def mutate(document: dict[str, Any]) -> None:
            document["output_contract"][key] = value

        rewrite(root / S03_SCHEMAS, mutate)

    def test_authority_claim_fails(self) -> None:
        root = self.make_root()
        self._claim(root, "authority", "authoritative")
        self.assert_diagnostic(self.run_verifier(root), "AUTHORITY_CLAIM")

    def test_threshold_requested_fails(self) -> None:
        root = self.make_root()
        self._claim(root, "threshold", 0.8)
        self.assert_diagnostic(self.run_verifier(root), "THRESHOLD_REQUESTED")

    def test_classification_requested_fails(self) -> None:
        root = self.make_root()
        self._claim(root, "classification", "pass")
        self.assert_diagnostic(self.run_verifier(root), "CLASSIFICATION_REQUESTED")

    def test_promotion_claim_fails(self) -> None:
        root = self.make_root()
        self._claim(root, "promotion", "gold")
        self.assert_diagnostic(self.run_verifier(root), "PROMOTION_CLAIM")

    def test_gold_claim_fails(self) -> None:
        root = self.make_root()
        self._claim(root, "human_acceptance", "accepted")
        self.assert_diagnostic(self.run_verifier(root), "GOLD_CLAIM")

    def test_model_invoked_fails(self) -> None:
        """No model is invoked anywhere in M207, so nothing may claim one was."""
        root = self.make_root()
        self._claim(root, "model_invoked", True)
        self.assert_diagnostic(self.run_verifier(root), "MODEL_INVOKED")

    def test_crates_reference_fails(self) -> None:
        """The product runtime gains no reader of the annotation surface (D466/D487)."""
        for relative, body in (
            ("crates/ln-decode/src/lib.rs", 'pub const X: &str = "m207-s03";\n'),
            ("crates/ln-decode/build.rs", "fn main() { /* prd/annotation */ }\n"),
            ("crates/ln-decode/Cargo.toml", '# m207_s03\n[package]\nname = "ln-decode"\n'),
        ):
            with self.subTest(relative=relative):
                root = self.make_root()
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
                self.assert_diagnostic(self.run_verifier(root), "PROMPT_ISOLATION_VIOLATION")

    def test_path_traversal_argument_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(
            self.run_verifier(root, "--s03-schemas", "../../etc/passwd"), "UNSAFE_PATH"
        )

    def test_absolute_path_argument_fails(self) -> None:
        root = self.make_root()
        self.assert_diagnostic(
            self.run_verifier(root, "--s03-schemas", "/etc/passwd"), "UNSAFE_PATH"
        )

    def test_s02_chain_failure_fails(self) -> None:
        """A non-zero S02 chain is a dependency failure refused by name, never ignored.

        The S02 closeout chain is this verifier's only external subprocess dependency:
        an exit outside {0, 3} must fail the slice check by name (Q5).
        """
        chain = self.stub_chain("echo 's02 chain broke'", code=1)
        result = self.run_cli(
            VERIFIER, "check", "--root", str(self.make_root()), "--s02-chain", str(chain)
        )
        self.assert_diagnostic(result, "S02_REGRESSION_FAILED")

    def test_verifier_never_prints_the_human_gate_marker(self) -> None:
        """The marker belongs to T06's chain; no machinery input may produce it."""
        clean = self.run_verifier(self.make_root())
        self.assertNotIn(HUMAN_GATE_MARKER, clean.stdout + clean.stderr)
        hostile = self.make_root()
        (hostile / REPORT).write_text("{}\n", encoding="utf-8")
        for result in (
            clean,
            self.run_verifier(hostile),
            self.run_battery(self.make_root(), self.empty_table()),
            self.run_cli(VERIFIER, "check", "--root", str(self.make_root())),
        ):
            with self.subTest(result=result.returncode):
                self.assertNotIn(HUMAN_GATE_MARKER, result.stdout + result.stderr)


# --------------------------------------------------------------------------- #
# Battery mode: the slice battery is assembled, never invented.
# --------------------------------------------------------------------------- #


class BatteryModeTests(SuiteBase):
    """Battery assembly refuses an empty or drifting result table."""

    def test_battery_empty_result_table_fails(self) -> None:
        self.assert_diagnostic(
            self.run_battery(self.make_root(), self.empty_table(), "--out", BATTERY),
            "EMPTY_SUITE",
        )

    def test_battery_result_table_must_carry_the_chain_set(self) -> None:
        table = self.result_table(
            tuple((name, 0, 1) for name in CHAIN_CHECKS[:-1]) + (("not_a_chain_check", 0, 1),)
        )
        self.assert_diagnostic(
            self.run_battery(self.make_root(), table, "--out", BATTERY), "SCHEMA_KEY_DRIFT"
        )

    def test_battery_failing_row_fails(self) -> None:
        table = self.result_table(
            tuple((name, 1 if name == "s03_metrics" else 0, 1) for name in CHAIN_CHECKS)
        )
        self.assert_diagnostic(
            self.run_battery(self.make_root(), table, "--out", BATTERY), "SUBCLI_FAILURE"
        )

    def test_battery_missing_tracked_battery_fails(self) -> None:
        self.assert_diagnostic(
            self.run_battery(self.make_root(), self.green_table(), "--out", BATTERY),
            "MISSING_ARTIFACT",
        )

    def test_battery_stale_tracked_battery_fails(self) -> None:
        """A tracked battery that no longer matches the assembled payload is refused.

        The read-only pass is what makes the D473 write observable: a battery
        edited by hand -- or one left behind by a chain whose check set has
        drifted -- is refused with ``BATTERY_STALE`` instead of being reported as
        current, because write mode is the only path that ever rewrites it.
        """
        root = self.make_root()
        (root / BATTERY).write_text(
            json.dumps(
                {"schema": "m207-s03-battery/v1", "schema_version": 1, "checks": []},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.assert_diagnostic(
            self.run_battery(root, self.green_table(), "--out", BATTERY),
            "BATTERY_STALE",
            detail="regenerate once with M207_S03_WRITE_BATTERY=1",
        )

    def test_battery_write_without_the_authorized_env_fails(self) -> None:
        root = self.make_root()
        (root / BATTERY).write_text(
            json.dumps({"schema": "m207-s03-battery/v1", "rows": []}) + "\n", encoding="utf-8"
        )
        self.assert_diagnostic(
            self.run_battery(root, self.green_table(), "--out", BATTERY, "--write"),
            "AUTHORITY_CLAIM",
        )


# --------------------------------------------------------------------------- #
# The synthetic human world: real CLIs, end to end, outside the repository.
# --------------------------------------------------------------------------- #


_WORLD_HOLDER: Path | None = None
_WORLD_ROOT: Path | None = None


def envelope(root: Path, coder_pass: int, coder_id: str) -> dict[str, Any]:
    """One synthetic coding pass with deliberate, aspect-covering disagreements."""
    kit = load_json(root / f"{EVID}/m207-s02-coder-kit-pass{coder_pass}.json")
    manifest = load_json(root / S01_CASES)
    cases: list[dict[str, Any]] = []
    for index, case in enumerate(manifest["cases"]):
        rule = index % 10
        start, end = int(case["start"]), int(case["end"])
        row: dict[str, Any] = {
            "case_id": case["case_id"],
            "decision": "reference",
            "span": {"start": start, "end": end},
            "slots": {},
            "abstention": "not-abstained",
        }
        if rule == 0:
            row["decision"] = "not_a_reference"
        elif rule == 1:
            row["slots"] = {"hier_nums": "ст. 5 части 1"}
            if coder_pass == 2:
                row["slots"] = {"marker_chain": "п. 3"}
        elif rule == 2:
            row["slots"] = {"marker_chain": "п. 2"}
        elif rule == 3:
            row["slots"] = {"anaphora": "указанный документ"}
        elif rule == 4:
            row["slots"] = {"doc_no": "558"}
            if coder_pass == 2:
                row["abstention"] = "ambiguous"
        elif rule == 5:
            if coder_pass == 2:
                row["span"] = {"start": start, "end": max(start + 1, end - 1)}
            row["slots"] = {"law_code": "44-ФЗ"}
        elif rule == 6:
            row["slots"] = {"hier_nums": "ст. 7"}
            if coder_pass == 2:
                row["decision"] = "not_a_reference"
        elif rule == 7:
            row["slots"] = {"doc_no": "77"}
            if coder_pass == 2:
                row["abstention"] = "insufficient-context"
        elif rule == 8:
            row["slots"] = {"hier_nums": "ст. 9"} if coder_pass == 1 else {"marker_chain": "п. 9"}
        else:
            row["slots"] = {"law_code": "44-ФЗ"}
            if coder_pass == 2:
                row["decision"] = "not_a_reference"
        cases.append(row)
    document: dict[str, Any] = dict(kit["submission_template"])
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


def resolution_for(axis: str) -> str:
    """The synthetic adjudicator's lawful choice inside the frozen resolution space."""
    if axis == "reference_decision":
        return "reference"
    if axis == "abstention":
        return "not-abstained"
    if axis == "span_exact":
        return "span_pass_1"
    if axis.startswith("slot_"):
        return "slot_present"
    raise AssertionError(f"no closed resolution for axis {axis!r}")


def _drive(script: Path, *args: str) -> Any:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        env=CHILD_ENV,
        text=True,
        capture_output=True,
        check=False,
        timeout=TIMEOUT,
    )


def _build_world() -> Path:
    """Drive the real S02 CLIs to publish a valid human reference, then the S03 engine."""
    global _WORLD_HOLDER
    _WORLD_HOLDER = Path(tempfile.mkdtemp(prefix="m207-s03-suite-world-base-"))
    atexit.register(shutil.rmtree, _WORLD_HOLDER, ignore_errors=True)
    root = _WORLD_HOLDER / "root"
    shutil.copytree(SuiteBase._build_base_root(), root)
    schemas = load_json(root / S02_SCHEMAS)
    store = root / SUBMISSIONS
    store.mkdir(parents=True, exist_ok=True)
    for coder_pass, coder_id in ((1, "coder-alpha"), (2, "coder-beta")):
        (store / f"submission-pass-{coder_pass}.json").write_bytes(
            (
                json.dumps(envelope(root, coder_pass, coder_id), ensure_ascii=False, indent=2)
                + "\n"
            ).encode("utf-8")
        )
    record = root / INTAKE_RECORD
    report = root / AGREEMENT_REPORT
    inventory = root / INVENTORY
    adjudications = root / ADJUDICATIONS
    adjudications.mkdir(parents=True, exist_ok=True)
    intake = _drive(
        INTAKE, "run", "--store", str(store), "--record", str(record), "--allow-test-fixtures"
    )
    if intake.returncode != 0:
        raise AssertionError(f"intake refused the synthetic world: {intake.stderr}")
    agreement = _drive(
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
    if agreement.returncode != 0:
        raise AssertionError(f"agreement refused the synthetic world: {agreement.stderr}")
    entries = load_json(inventory).get("entries") or []
    for index, entry in enumerate(entries, start=1):
        (adjudications / f"adjudication-{index:03d}.json").write_bytes(
            (
                json.dumps(
                    {
                        "schema": "m207-s02-adjudication-input/v1",
                        "schema_version": 1,
                        "adjudication_id": f"adjudication-{index:03d}",
                        "adjudicator_id": "adjudicator-1",
                        "axis": entry["axis"],
                        "case_id": entry["case_id"],
                        "resolution": resolution_for(str(entry["axis"])),
                        "provenance": "human-reviewed",
                        "rationale": "resolved against the closed codebook decision space",
                        "supersedes": None,
                        "is_gold": False,
                        "non_claims": schemas["non_claims"],
                        "lifecycle": schemas["lifecycle"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ).encode("utf-8")
        )
    adjudication = _drive(
        ADJUDICATE,
        "run",
        "--store",
        str(adjudications),
        "--agreement",
        str(report),
        "--inventory",
        str(inventory),
        "--record",
        str(root / ADJUDICATION_RECORD),
        "--receipt",
        str(root / PILOT_RECEIPT),
        "--allow-test-fixtures",
    )
    if adjudication.returncode != 0:
        raise AssertionError(f"adjudication refused the synthetic world: {adjudication.stderr}")
    published = _drive(METRICS, "run", "--root", str(root))
    if published.returncode != 0:
        raise AssertionError(f"the engine refused the synthetic world: {published.stderr}")
    return root


def world_root() -> Path:
    """One synthetic world per run; every case gets a private clone of it."""
    global _WORLD_ROOT
    if _WORLD_ROOT is None:
        _WORLD_ROOT = _build_world()
    return _WORLD_ROOT


class MetricWorldBase(SuiteBase):
    """Shared synthetic world plus the report-mutation helpers."""

    def world(self) -> Path:
        return self.world_clone()

    def mutate_report(self, root: Path, mutate: Any) -> None:
        rewrite(root / REPORT, mutate)

    def assert_metrics_refusal(self, root: Path, mode: str, diagnostic: str) -> None:
        self.assert_diagnostic(self.run_metrics(root, mode), diagnostic)


# --------------------------------------------------------------------------- #
# The metric surface: honest denominators and typed publication (RC28-F01).
# --------------------------------------------------------------------------- #


class MetricEngineTests(MetricWorldBase):
    """The rate engine is the most fabricable surface, so it is attacked hardest."""

    def test_synthetic_report_has_honest_denominators(self) -> None:
        """Positive control: a real two-pass world publishes rates, empty strata stay null."""
        root = self.world()
        checked = self.run_metrics(root, "check")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn(METRICS_MARKER, checked.stdout)
        self.assertIn("human=present", checked.stdout)
        self.assertIn("report=present", checked.stdout)
        report = load_json(root / REPORT)
        rows = report["strata"]
        self.assertTrue(rows, "the report published no stratum at all")
        empty = [row for row in rows if row["denominator"] == 0]
        self.assertTrue(empty, "no empty stratum was published: the garant stratum vanished")
        for row in empty:
            with self.subTest(stratum=row["stratum_id"]):
                self.assertIsNone(row["value"], "a zero denominator produced a value")
                self.assertEqual(row["measurement_status"], "not-measured")
        for row in rows:
            if row["value"] is not None:
                with self.subTest(stratum=row["stratum_id"]):
                    self.assertGreater(row["denominator"], 0)
        self.assertEqual(
            [row["aspect"] for row in report["aspects"]],
            ["span", "slot", "scope", "binding", "abstention", "false_authority"],
        )
        for row in report["aspects"]:
            with self.subTest(aspect=row["aspect"]):
                self.assertGreater(row["denominator"], 0)
        garant = [row for row in rows if row["stratum_id"].startswith("garant|")]
        self.assertTrue(garant, "the declared but empty provider stratum was dropped")

    def test_absent_human_reference_refuses_and_publishes_nothing(self) -> None:
        """RC28-F01: a producer-to-promotion negative -- no human input, no metric."""
        root = self.world()
        shutil.rmtree(root / SUBMISSIONS)
        shutil.rmtree(root / ADJUDICATIONS)
        (root / REPORT).unlink()
        result = self.run_metrics(root, "run")
        joined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 3, joined)
        self.assertIn("FAIL HUMAN_PILOT_ABSENT:", joined)
        self.assertFalse((root / REPORT).exists(), "the engine published a metric without a human")

    def test_imputed_zero_value_fails(self) -> None:
        """An absent denominator is not a measurement, and 0.0 is an imputed value."""
        root = self.world()

        def mutate(document: dict[str, Any]) -> None:
            for row in document["strata"]:
                if row["denominator"] == 0:
                    row["value"] = 0.0
                    return

        self.mutate_report(root, mutate)
        self.assert_metrics_refusal(root, "check", "RATE_UNDEFINED")

    def test_imputed_one_value_fails(self) -> None:
        """1.0 without a denominator is the signature failure RC28-F01 names."""
        root = self.world()

        def mutate(document: dict[str, Any]) -> None:
            for row in document["strata"]:
                if row["denominator"] == 0:
                    row["value"] = 1.0
                    return

        self.mutate_report(root, mutate)
        self.assert_metrics_refusal(root, "check", "RATE_UNDEFINED")

    def test_metric_provider_stratum_dropped_fails(self) -> None:
        root = self.world()
        self.mutate_report(
            root,
            lambda document: document.update(
                {
                    "strata": [
                        row
                        for row in document["strata"]
                        if not row["stratum_id"].startswith("garant|")
                    ]
                }
            ),
        )
        self.assert_metrics_refusal(root, "check", "PROVIDER_STRATUM_DROPPED")

    def test_metric_provider_misattributed_fails(self) -> None:
        root = self.world()

        def mutate(document: dict[str, Any]) -> None:
            for row in document["strata"]:
                provider, rest = row["stratum_id"].split("|", 1)
                if provider == "garant":
                    row["stratum_id"] = f"acme|{rest}"
                    return

        self.mutate_report(root, mutate)
        self.assert_metrics_refusal(root, "check", "PROVIDER_MISATTRIBUTED")

    def test_metric_abstention_collapse_fails(self) -> None:
        """Abstention is a measurement, so it may not be excluded from its own denominator."""
        root = self.world()

        def mutate(document: dict[str, Any]) -> None:
            for entry in document["aspect_table"]:
                if entry["aspect"] == "abstention":
                    entry["units_excluded_reasons"] = sorted(
                        set(entry["units_excluded_reasons"]) | {"abstained"}
                    )
                    return

        rewrite(root / S03_SCHEMAS, mutate)
        self.assert_metrics_refusal(root, "check", "ABSTENTION_COLLAPSE")

    def test_metric_measurement_status_drift_fails(self) -> None:
        root = self.world()

        def mutate(document: dict[str, Any]) -> None:
            for row in document["aspects"]:
                if row["denominator"] > 0:
                    row["measurement_status"] = "proxy-measured"
                    return

        self.mutate_report(root, mutate)
        self.assert_metrics_refusal(root, "check", "MEASUREMENT_STATUS_DRIFT")

    def test_metric_dev_slice_is_never_an_evaluation(self) -> None:
        """The holdout is the evaluation; the dev slice is published dev-only."""
        root = self.world()
        self.mutate_report(
            root,
            lambda document: document["dev"].update({"evaluation_status": "evaluation"}),
        )
        self.assert_metrics_refusal(root, "check", "DEVELOPMENT_SLICE_NOT_EVALUATION")

    def test_metric_report_without_human_reference_fails(self) -> None:
        root = self.world()
        shutil.rmtree(root / SUBMISSIONS)
        shutil.rmtree(root / ADJUDICATIONS)
        self.assert_metrics_refusal(root, "check", "REPORT_WITHOUT_HUMAN_DATA")

    def test_metric_report_missing_with_human_reference_fails(self) -> None:
        root = self.world()
        (root / REPORT).unlink()
        self.assert_metrics_refusal(root, "check", "REPORT_MISSING_WITH_HUMAN_DATA")

    def test_metric_proxy_input_is_refused(self) -> None:
        """A producer receipt is a proxy input, never an independent evaluation."""
        root = self.world()
        (root / SUBMISSIONS / "proxy-receipt.json").write_bytes(
            json.dumps({"schema": "npa-quality-receipts/v1", "schema_version": 1}, indent=2).encode(
                "utf-8"
            )
        )
        self.assert_metrics_refusal(root, "run", "PROXY_INPUT_REFUSED")

    def test_metric_unresolvable_store_never_yields_a_measurement(self) -> None:
        """An unresolvable drop box is a refusal, never a silently empty denominator.

        The engine treats an unresolvable store as *absent human reference* rather than
        surfacing the resolver's own ``UNSAFE_PATH``, so the property worth pinning here
        is the one that carries the contract: whatever shape the hostile store path has,
        no metric is published.  The ``UNSAFE_PATH`` refusals themselves are proved on
        the argument surface (the verifier) and on the input contour that owns the store
        (``test_store_path_traversal_fails``).
        """
        root = self.world()
        for raw in ("../../etc/passwd", "synthetic\\store", "/etc/passwd"):
            with self.subTest(raw=raw):
                self.assert_diagnostic(
                    self.run_metrics(root, "run", "--submissions", raw),
                    "REPORT_WITHOUT_HUMAN_DATA",
                    "UNSAFE_PATH",
                    "HUMAN_PILOT_ABSENT",
                )

    def test_metric_pre_adjudication_pin_drift_fails(self) -> None:
        """The resolved reference stays pinned to the frozen pre-adjudication score."""
        root = self.world()
        rewrite(
            root / ADJUDICATION_RECORD,
            lambda document: document.update({"pre_adjudication_agreement_sha256": "0" * 64}),
        )
        self.assert_metrics_refusal(root, "run", "FROZEN_SOURCE_DRIFT")

    def test_metric_claim_keys_are_refused(self) -> None:
        """Gold, threshold, classification and promotion claims on the report itself."""
        for key, value, diagnostic in (
            ("human_acceptance", "accepted", "GOLD_CLAIM"),
            ("is_gold", True, "IS_GOLD_CLAIM"),
            ("threshold", 0.5, "THRESHOLD_REQUESTED"),
            ("classification", "accepted", "CLASSIFICATION_REQUESTED"),
            ("promotion", "promoted", "PROMOTION_CLAIM"),
            ("model_invoked", True, "MODEL_INVOKED"),
        ):
            with self.subTest(key=key):
                root = self.world()
                self.mutate_report(root, lambda document, k=key, v=value: document.update({k: v}))
                self.assert_metrics_refusal(root, "check", diagnostic)


# --------------------------------------------------------------------------- #
# The manifest gate: holdout isolation, provider accounting, derived metadata.
# --------------------------------------------------------------------------- #


class ManifestGateTests(SuiteBase):
    """The evaluation manifest is rebuilt from its sources and must stay isolated."""

    def test_c3_isolation_overlap_fails(self) -> None:
        """A holdout case may never reappear inside the sealed C3 holdout."""
        root = self.make_root()
        holdout = next(
            case["source_sha256"]
            for case in load_json(root / S03_MANIFEST)["cases"]
            if case["family_scope"] == "holdout"
        )

        def mutate(document: dict[str, Any]) -> None:
            document["entries"][0]["content_hash"] = f"sha256:{holdout}"

        rewrite(root / C3_MANIFEST, mutate)
        self.assert_manifest_refusal(root, "C3_ISOLATION_VIOLATION")

    def test_c3_unsealed_fails(self) -> None:
        root = self.make_root()
        rewrite(root / C3_MANIFEST, lambda document: document.update({"sealed": False}))
        self.assert_manifest_refusal(root, "C3_ISOLATION_VIOLATION")

    def test_metadata_rederived_fails(self) -> None:
        """Year and document type come from the declared root, never from a path guess."""
        root = self.make_root()
        rewrite(
            root / S01_CASES,
            lambda document: document["cases"][0].update({"year": "2020"}),
        )
        self.assert_manifest_refusal(root, "METADATA_REDERIVED")

    def test_cases_manifest_unsafe_path_fails(self) -> None:
        """A source path may not escape the declared corpus root."""
        root = self.make_root()
        rewrite(
            root / S01_CASES,
            lambda document: document["cases"][0].update({"source_path": "../escape.xml"}),
        )
        self.assert_manifest_refusal(root, "UNSAFE_PATH")

    def assert_manifest_refusal(self, root: Path, diagnostic: str) -> None:
        self.assert_diagnostic(self.run_manifest(root, "run", "--refreeze"), diagnostic)


# --------------------------------------------------------------------------- #
# The reused input contour: S03 redefines no submission key (D475).
# --------------------------------------------------------------------------- #


class InputContourTests(SuiteBase):
    """The frozen submission form is reused verbatim, so its refusals are S03's too."""

    def _envelope(self, root: Path) -> dict[str, Any]:
        kit = load_json(root / KIT_PASS1)
        manifest = load_json(root / S01_CASES)
        document: dict[str, Any] = dict(kit["submission_template"])
        document.update(
            {
                "coder_id": "coder-1",
                "provenance": "human-reviewed",
                "coder_pass": 1,
                "submission_id": "m207-s02-submission-pass-1",
                "cases": [
                    {
                        "case_id": case["case_id"],
                        "decision": "not_a_reference",
                        "span": {"start": case["start"], "end": case["end"]},
                        "slots": {},
                        "abstention": "not-abstained",
                    }
                    for case in manifest["cases"]
                ],
            }
        )
        return document

    def test_ninth_slot_fails(self) -> None:
        """Eight closed slot keys; a ninth is a new annotation surface, not a slot."""
        root = self.make_root()
        document = self._envelope(root)
        document["cases"][0]["slots"] = {"ninth_slot": "reference"}
        self.assert_intake_refusal(root, document, "NINTH_SLOT")

    def test_store_path_traversal_fails(self) -> None:
        """A human drop box may not escape the repository, by traversal or by a backslash."""
        for raw in ("../../etc/passwd", "synthetic\\store"):
            with self.subTest(raw=raw):
                result = self.run_cli(
                    INTAKE,
                    "run",
                    "--store",
                    raw,
                    "--record",
                    str(self.temp_dir() / "record.json"),
                    "--allow-test-fixtures",
                )
                self.assert_diagnostic(result, "UNSAFE_PATH")

    def test_clean_envelope_is_admitted_read_only(self) -> None:
        """Positive control: an unmutated envelope is admitted and writes nothing."""
        root = self.make_root()
        directory = self.temp_dir()
        path = directory / "envelope.json"
        path.write_text(
            json.dumps(self._envelope(root), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("M207_S02_INTAKE_ACCEPTED", result.stdout)
        self.assertFalse(record.exists(), "the intake wrote a record in probe mode")
        self.assertFalse(store.exists(), "the intake created a store in probe mode")

    def assert_intake_refusal(self, root: Path, document: dict[str, Any], name: str) -> None:
        directory = self.temp_dir()
        path = directory / "hostile-envelope.json"
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        store = directory / "store"
        result = self.run_cli(
            INTAKE,
            "run",
            "--submission",
            str(path),
            "--store",
            str(store),
            "--record",
            str(directory / "record.json"),
            "--allow-test-fixtures",
        )
        self.assert_diagnostic(result, name)
        self.assertFalse(store.exists(), "a refused envelope created a store")


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

    def test_suite_never_drives_a_path_inside_the_repository(self) -> None:
        """Every root the suite drives is a temp copy: the checkout is never a target."""
        base = SuiteBase._build_base_root()
        self.addCleanup(shutil.rmtree, base.parent, ignore_errors=True)
        temporary = Path(tempfile.gettempdir()).resolve()
        repository = ROOT.resolve()
        for path in (base, world_root()):
            with self.subTest(path=str(path)):
                resolved = path.resolve()
                self.assertTrue(str(resolved).startswith(str(temporary)), str(resolved))
                self.assertFalse(str(resolved).startswith(str(repository)), str(resolved))


if __name__ == "__main__":
    unittest.main(verbosity=2)
