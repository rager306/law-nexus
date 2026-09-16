#!/usr/bin/env python3
"""Offline adversarial subprocess suite for the M207 S04 promotion verdict (T03).

Every case invokes the real CLI ``scripts/m207_s04_pilot.py`` on a throw-away copy
of the frozen S04 surface inside ``tempfile.mkdtemp``, mutates **exactly one**
thing, and asserts that the run fails closed with a *named* diagnostic
(``FAIL <NAME>:``).  Nothing is mocked, nothing is imported from the tool under
test (subprocess only, D472), and nothing here reads ``.gsd/``, touches the
network, the git index or the repository working tree -- except the two explicit
read-only positives that run the pilot against the repository itself and scan the
real ``crates/`` tree.

WHY THIS EXISTS AFTER THE WALK.  T02 produced an honest ``non-pass`` receipt and
T03 owns the layer that makes an operational attempt easiest to launder: the
*verdict*.  A receipt may be edited after the fact, a fast walk may be promoted to
``pass``, a decode failure may quietly become a quality judgement, the S03 aspect
rates may be "reused" as readiness evidence, the 180-fragment seed may grow, and
the integrity battery marker may be read as an acceptance.  Each of those is a
single-key edit, so each of them gets a single-key hostile case here.

The interesting cases are the *substantiated* ones: the receipt and the run's own
JSONL attempt record have to agree.  A tampered record is re-pinned in the receipt
before the pilot runs, because a launderer would do exactly that -- so the case
proves that the pilot re-derives the run facts (argv, digest, counts, toolchain,
run status) instead of trusting the sidecar it is handed.

The two invariants this slice cannot delegate:

* **an unavailable verb is never invented** -- with an absent receipt the pilot
  exits 1 with ``C4_RECEIPT_MISSING`` and never reconstructs a receipt from the
  attempt logs;
* **the integrity marker** -- ``M207_S04_VERIFY_OK`` belongs to the T04 battery and
  must never appear on any line this tool prints, whatever the input.

An empty suite is itself a failure: ``SuiteIntegrityTests`` requires the hostile
registry to stay populated, every named diagnostic to exist in the frozen closed
vocabulary, and every registered case to actually mutate the root it is given.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "scripts" / "m207_s04_pilot.py"

MARKER = "M207_S04_PROMOTION_NONE_OK"
VERDICT_TAG = "M207_S04_PROMOTION_VERDICT"
SEMANTIC_TAG = "M207_S04_SEMANTIC_OBSERVATION"
GATE = "M207_S04_PILOT_GATE"
INTEGRITY_MARKER = "M207_S04_VERIFY_OK"

EVID = "prd/migration/rust-evidence"
ANN = "prd/annotation"
FIXTURE = "crates/ln-decode/tests/fixtures/npa-lawref"
SCHEMAS = f"{ANN}/m207-s04-schemas.json"
RECEIPT = f"{EVID}/m207-s04-c4-operational-receipt.json"
PRIOR = f"{EVID}/m204-s06-c4-operational-receipt.json"
S03_BATTERY = f"{EVID}/m207-s03-battery.json"
REPORT = f"{EVID}/m207-s03-evaluation-report.json"
BATTERY = f"{EVID}/m207-s04-battery.json"

CHILD_ENV = {key: value for key, value in os.environ.items() if not key.startswith("M207_S04_")}
TIMEOUT = 300
MIN_HOSTILE_CASES = 40

Mutator = Callable[[Path], None]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, document: Any) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(
            path.relative_to(root).as_posix().encode("utf-8")
            + b"\x00"
            + sha256_file(path).encode("ascii")
            + b"\n"
        )
    return digest.hexdigest()


def read_receipt(root: Path) -> dict[str, Any]:
    document = load_json(root / RECEIPT)
    assert isinstance(document, dict)
    return document


def write_receipt(root: Path, document: dict[str, Any]) -> None:
    dump_json(root / RECEIPT, document)


def edit_receipt(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    document = read_receipt(root)
    mutate(document)
    write_receipt(root, document)


def read_records(root: Path) -> list[dict[str, Any]]:
    receipt = read_receipt(root)
    path = root / str(receipt["logs"]["stdout"])
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_records(root: Path, records: list[dict[str, Any]], *, repin: bool = True) -> None:
    receipt = read_receipt(root)
    relative = str(receipt["logs"]["stdout"])
    path = root / relative
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    if repin:
        receipt["logs"]["stdout_sha256"] = sha256_file(path)
        write_receipt(root, receipt)


def edit_record(root: Path, kind: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    records = read_records(root)
    for record in records:
        if record.get("record_kind") == kind:
            mutate(record)
    write_records(root, records)


def plant_battery(root: Path, mutate: Callable[[dict[str, Any]], None] | None = None) -> None:
    scopes = load_json(root / SCHEMAS)
    document: dict[str, Any] = {
        "schema": "m207-s04-battery/v1",
        "schema_version": 1,
        "checks": [
            {
                "check_id": "s04_schemas",
                "command": "uv run python scripts/m207_s04_schemas.py check",
                "diagnostic": "none",
                "exit_code": 0,
                "status": "pass",
            }
        ],
        "pins": [{"path": SCHEMAS, "sha256": sha256_file(root / SCHEMAS)}],
        "human_pilot_performed": False,
        "model_invoked": False,
        "lifecycle": dict(scopes["lifecycle"]),
        "non_claims": ["not gold", "not a promotion", "not independent-measured"],
    }
    if mutate is not None:
        mutate(document)
    dump_json(root / BATTERY, document)


# --------------------------------------------------------------------------- #
# Minimal mutations: one thing each.
# --------------------------------------------------------------------------- #


def _drop_receipt_key(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document.pop("terminal", None)

    edit_receipt(root, mutate)


def _change_receipt_schema(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["schema"] = "m204-s06-c4-operational-receipt/v2"

    edit_receipt(root, mutate)


def _corrupt_receipt_json(root: Path) -> None:
    (root / RECEIPT).write_text("{not json", encoding="utf-8")


def _duplicate_receipt_key(root: Path) -> None:
    text = (root / RECEIPT).read_text(encoding="utf-8")
    (root / RECEIPT).write_text(text.replace("{", '{"schema": "x",', 1), encoding="utf-8")


def _argv_limit(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["argv"] = [*document["argv"], "--limit", "10"]

    edit_receipt(root, mutate)


def _argv_missing_flag(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        argv = list(document["argv"])
        index = argv.index("--jobs")
        del argv[index : index + 2]
        document["argv"] = argv

    edit_receipt(root, mutate)


def _identity_not_recomputed(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["argv"] = [*document["argv"], "--jobs", "4"]

    edit_receipt(root, mutate)


def _identity_tampered(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["immutable_attempt_identity"]["argv_sha256"] = "0" * 64

    edit_receipt(root, mutate)


def _unknown_outcome(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["terminal"]["outcome"] = "crashed"

    edit_receipt(root, mutate)


def _incoherent_timeout(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["terminal"] = {
            "outcome": "timeout",
            "exit_code": 0,
            "signal": None,
            "timeout": False,
        }

    edit_receipt(root, mutate)


def _claim_pass_over_a_short_walk(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["claims"]["operational_acceptance"] = "pass"

    edit_receipt(root, mutate)


def _claim_pass_over_a_timeout(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["terminal"] = {
            "outcome": "timeout",
            "exit_code": None,
            "signal": "SIGTERM",
            "timeout": True,
        }
        document["claims"]["operational_acceptance"] = "pass"

    edit_receipt(root, mutate)


def _budget_below_minimum(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["budget_seconds"] = 600

    edit_receipt(root, mutate)


def _receipt_underreports_the_run(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["terminal"] = {
            "outcome": "nonzero",
            "exit_code": 1,
            "signal": None,
            "timeout": False,
        }
        document["claims"]["operational_acceptance"] = "non-pass"

    edit_receipt(root, mutate)


def _promotion_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["promotion"] = "gold"

    edit_receipt(root, mutate)


def _gold_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["human_acceptance"] = "accepted"

    edit_receipt(root, mutate)


def _is_gold_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["is_gold"] = True

    edit_receipt(root, mutate)


def _threshold_requested(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["threshold"] = 0.8

    edit_receipt(root, mutate)


def _classification_requested(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["classification"] = "pass"

    edit_receipt(root, mutate)


def _model_invoked(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["model_invoked"] = True

    edit_receipt(root, mutate)


def _authority_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["legal_claim"] = "resolved"

    edit_receipt(root, mutate)


def _marker_as_acceptance(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["verdict"] = INTEGRITY_MARKER

    edit_receipt(root, mutate)


def _requirement_status_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["requirement_status_effect"] = "R035 closed"

    edit_receipt(root, mutate)


def _rate_imported(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["aspect_rates"] = {"lawref-capture": 0.93}

    edit_receipt(root, mutate)


def _denominator_imported(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["stratum"] = {"garant": {"measurement_status": "measured", "denominator": 12}}

    edit_receipt(root, mutate)


def _log_missing(root: Path) -> None:
    read_receipt(root)
    (root / str(read_receipt(root)["logs"]["stdout"])).unlink()


def _log_hash_drift(root: Path) -> None:
    receipt = read_receipt(root)
    path = root / str(receipt["logs"]["stdout"])
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def _log_not_json(root: Path) -> None:
    receipt = read_receipt(root)
    path = root / str(receipt["logs"]["stdout"])
    path.write_text(path.read_text(encoding="utf-8") + "{oops\n", encoding="utf-8")
    receipt["logs"]["stdout_sha256"] = sha256_file(path)
    write_receipt(root, receipt)


def _log_duplicate_record(root: Path) -> None:
    records = read_records(root)
    header = next(record for record in records if record.get("record_kind") == "header")
    write_records(root, [*records, dict(header)])


def _log_digest_drift(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["inventory_digest"] = "sha256:" + "0" * 64

    edit_record(root, "canonical_payload", mutate)


def _log_count_arithmetic(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["decoded"] = 43790

    edit_record(root, "aggregate", mutate)


def _log_provider_count_drift(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["dimensions"]["provider"]["consultant"] = 43784

    edit_record(root, "inventory", mutate)


def _log_argv_drift(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        argv = list(record["argv"])
        index = argv.index("--jobs")
        del argv[index : index + 2]
        record["argv"] = argv

    edit_record(root, "operational_envelope", mutate)


def _log_rustc_drift(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["observed_rustc_version"] = "rustc 1.0.0 (deadbeef 1970-01-01)"

    edit_record(root, "operational_envelope", mutate)


def _log_run_status_failed(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["run_status"] = "failed"

    edit_record(root, "operational_envelope", mutate)


def _log_duration_exceeds_receipt(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["duration_ms"] = 10_000_000

    edit_record(root, "operational_envelope", mutate)


def _log_profile_drift(root: Path) -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["profile"] = "sample"
        record["limit"] = 50

    edit_record(root, "header", mutate)


def _plant_report(root: Path) -> None:
    report = root / REPORT
    report.parent.mkdir(parents=True, exist_ok=True)
    dump_json(report, {"schema": "m207-s03-evaluation-report/v1", "aspect_rates": {}})


def _battery_pilot_performed(root: Path) -> None:
    battery = load_json(root / S03_BATTERY)
    battery["human_pilot_performed"] = True
    dump_json(root / S03_BATTERY, battery)


def _battery_digest_drift(root: Path) -> None:
    path = root / S03_BATTERY
    path.write_bytes(path.read_bytes() + b"\n")


def _battery_model_invoked(root: Path) -> None:
    battery = load_json(root / S03_BATTERY)
    battery["model_invoked"] = True
    dump_json(root / S03_BATTERY, battery)


def _battery_lifecycle_drift(root: Path) -> None:
    battery = load_json(root / S03_BATTERY)
    battery["lifecycle"]["requirement_status_effect"] = "changed"
    dump_json(root / S03_BATTERY, battery)


def _seed_enlarged(root: Path) -> None:
    (root / FIXTURE / "npa-frag-181.txt").write_text("девяносто девятый\n", encoding="utf-8")


def _seed_drift(root: Path) -> None:
    (root / FIXTURE / "npa-frag-001.txt").write_text("изменённый фрагмент\n", encoding="utf-8")


def _sidecar_drift(root: Path) -> None:
    path = root / FIXTURE / "lawref_seed.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")


def _crates_reference(root: Path) -> None:
    crate = root / "crates" / "ln-decode" / "src"
    crate.mkdir(parents=True, exist_ok=True)
    (crate / "m207_probe.rs").write_text("// reads m207_s03 metrics\n", encoding="utf-8")


def _schema_diagnostic_table_drift(root: Path) -> None:
    document = load_json(root / SCHEMAS)
    document["diagnostics"] = [
        name for name in document["diagnostics"] if name != "C4_TIMEOUT_AS_PASS"
    ]
    dump_json(root / SCHEMAS, document)


def _schema_promotion_contract_drift(root: Path) -> None:
    document = load_json(root / SCHEMAS)
    document["promotion_contract"]["promotion"] = "gold"
    dump_json(root / SCHEMAS, document)


def _schema_seed_pin_drift(root: Path) -> None:
    document = load_json(root / SCHEMAS)
    document["frozen_sources"]["m207_s03_battery"]["sha256"] = "0" * 64
    dump_json(root / SCHEMAS, document)


def _schema_lifecycle_drift(root: Path) -> None:
    document = load_json(root / SCHEMAS)
    document["lifecycle"]["requirement_status_effect"] = "changed"
    dump_json(root / SCHEMAS, document)


def _schemas_missing(root: Path) -> None:
    (root / SCHEMAS).unlink()


def _prior_rewritten(root: Path) -> None:
    prior = load_json(root / PRIOR)
    prior["terminal"] = {
        "outcome": "complete",
        "exit_code": 0,
        "signal": None,
        "timeout": False,
    }
    prior["claims"]["operational_acceptance"] = "pass"
    dump_json(root / PRIOR, prior)


def _prior_semantics_rewritten(root: Path) -> None:
    prior = load_json(root / PRIOR)
    prior["claims"]["operational_acceptance"] = "pass"
    dump_json(root / PRIOR, prior)


def _battery_wallclock(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["generated_at"] = "2026-09-16T09:00:00Z"

    plant_battery(root, mutate)


def _battery_promotion(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["promotion"] = "gold"

    plant_battery(root, mutate)


def _battery_pilot_claim(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["human_pilot_performed"] = True

    plant_battery(root, mutate)


def _battery_schema_drift(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["schema"] = "m207-s04-battery/v2"

    plant_battery(root, mutate)


def _battery_lifecycle_missing(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document.pop("lifecycle", None)

    plant_battery(root, mutate)


def _battery_marker_as_acceptance(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["verdict"] = INTEGRITY_MARKER

    plant_battery(root, mutate)


@dataclass(frozen=True)
class HostileCase:
    """One mutation, one expected diagnostic."""

    name: str
    diagnostic: str
    mutator: Mutator | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)


HOSTILE_CASES: tuple[HostileCase, ...] = (
    HostileCase("receipt-missing", "C4_RECEIPT_MISSING", lambda root: (root / RECEIPT).unlink()),
    HostileCase("receipt-not-json", "SCHEMA_PARSE_ERROR", _corrupt_receipt_json),
    HostileCase("receipt-duplicate-key", "DUPLICATE_JSON_KEY", _duplicate_receipt_key),
    HostileCase("receipt-schema-drift", "C4_RECEIPT_DRIFT", _change_receipt_schema),
    HostileCase("receipt-key-dropped", "C4_RECEIPT_DRIFT", _drop_receipt_key),
    HostileCase("argv-limit", "ARGV_PIN_DRIFT", _argv_limit),
    HostileCase("argv-flag-missing", "ARGV_PIN_DRIFT", _argv_missing_flag),
    HostileCase("identity-not-recomputed", "IMMUTABLE_IDENTITY_MISSING", _identity_not_recomputed),
    HostileCase("identity-tampered", "IMMUTABLE_IDENTITY_MISSING", _identity_tampered),
    HostileCase("terminal-unknown-outcome", "TERMINAL_OUTCOME_DRIFT", _unknown_outcome),
    HostileCase("terminal-incoherent-timeout", "TERMINAL_OUTCOME_DRIFT", _incoherent_timeout),
    HostileCase("claim-pass-over-short-walk", "C4_TIMEOUT_AS_PASS", _claim_pass_over_a_short_walk),
    HostileCase("claim-pass-over-timeout", "C4_TIMEOUT_AS_PASS", _claim_pass_over_a_timeout),
    HostileCase(
        "receipt-underreports-run", "TERMINAL_OUTCOME_DRIFT", _receipt_underreports_the_run
    ),
    HostileCase("budget-below-minimum", "BUDGET_BELOW_MINIMUM", _budget_below_minimum),
    HostileCase("log-missing", "ATTEMPT_LOG_MISSING", _log_missing),
    HostileCase("log-hash-drift", "LOG_HASH_MISSING", _log_hash_drift),
    HostileCase("log-not-json", "SCHEMA_PARSE_ERROR", _log_not_json),
    HostileCase("log-duplicate-record", "C4_RECEIPT_DRIFT", _log_duplicate_record),
    HostileCase("log-digest-drift", "C4_RECEIPT_DRIFT", _log_digest_drift),
    HostileCase("log-count-arithmetic", "C4_RECEIPT_DRIFT", _log_count_arithmetic),
    HostileCase("log-provider-count-drift", "C4_RECEIPT_DRIFT", _log_provider_count_drift),
    HostileCase("log-argv-drift", "ARGV_PIN_DRIFT", _log_argv_drift),
    HostileCase("log-rustc-drift", "TOOLCHAIN_PIN_MISSING", _log_rustc_drift),
    HostileCase("log-run-status-failed", "C4_TIMEOUT_AS_PASS", _log_run_status_failed),
    HostileCase("log-duration-exceeds-receipt", "C4_RECEIPT_DRIFT", _log_duration_exceeds_receipt),
    HostileCase("log-profile-drift", "ARGV_PIN_DRIFT", _log_profile_drift),
    HostileCase("promotion-claim", "PROMOTION_CLAIM", _promotion_claim),
    HostileCase("gold-claim", "GOLD_CLAIM", _gold_claim),
    HostileCase("is-gold-claim", "IS_GOLD_CLAIM", _is_gold_claim),
    HostileCase("threshold-requested", "THRESHOLD_REQUESTED", _threshold_requested),
    HostileCase("classification-requested", "CLASSIFICATION_REQUESTED", _classification_requested),
    HostileCase("model-invoked", "MODEL_INVOKED", _model_invoked),
    HostileCase("authority-claim", "AUTHORITY_CLAIM", _authority_claim),
    HostileCase("marker-as-acceptance", "INTEGRITY_MARKER_AS_ACCEPTANCE", _marker_as_acceptance),
    HostileCase("requirement-status-claim", "REQUIREMENT_STATUS_CLAIM", _requirement_status_claim),
    HostileCase("rate-imported", "S03_RATE_IMPORTED", _rate_imported),
    HostileCase("denominator-imported", "S03_RATE_IMPORTED", _denominator_imported),
    HostileCase("report-without-human-data", "REPORT_WITHOUT_HUMAN_DATA", _plant_report),
    HostileCase(
        "s03-battery-pilot-performed", "S03_BATTERY_PILOT_PERFORMED", _battery_pilot_performed
    ),
    HostileCase("s03-battery-digest-drift", "FROZEN_SOURCE_DRIFT", _battery_digest_drift),
    HostileCase("s03-battery-model-invoked", "MODEL_INVOKED", _battery_model_invoked),
    HostileCase(
        "s03-battery-lifecycle-drift", "MISSING_LIFECYCLE_MARKER", _battery_lifecycle_drift
    ),
    HostileCase("seed-enlarged", "SEED_ENLARGED", _seed_enlarged),
    HostileCase("seed-drift", "SEED_DRIFT", _seed_drift),
    HostileCase("seed-sidecar-drift", "SEED_DRIFT", _sidecar_drift),
    HostileCase("crates-m207-reference", "S03_RATE_IMPORTED", _crates_reference),
    HostileCase("prior-receipt-rewritten", "C4_TIMEOUT_AS_PASS", _prior_rewritten),
    HostileCase("prior-semantics-rewritten", "C4_TIMEOUT_AS_PASS", _prior_semantics_rewritten),
    HostileCase("battery-wallclock", "BATTERY_WALLCLOCK_FORBIDDEN", _battery_wallclock),
    HostileCase("battery-promotion", "PROMOTION_CLAIM", _battery_promotion),
    HostileCase("battery-pilot-claim", "S03_BATTERY_PILOT_PERFORMED", _battery_pilot_claim),
    HostileCase("battery-schema-drift", "SCHEMA_KEY_DRIFT", _battery_schema_drift),
    HostileCase(
        "battery-lifecycle-missing", "MISSING_LIFECYCLE_MARKER", _battery_lifecycle_missing
    ),
    HostileCase(
        "battery-marker-as-acceptance",
        "INTEGRITY_MARKER_AS_ACCEPTANCE",
        _battery_marker_as_acceptance,
    ),
    HostileCase(
        "schema-diagnostic-table", "DIAGNOSTIC_TABLE_DRIFT", _schema_diagnostic_table_drift
    ),
    HostileCase("schema-promotion-drift", "FROZEN_SOURCE_DRIFT", _schema_promotion_contract_drift),
    HostileCase("schema-seed-pin-drift", "FROZEN_SOURCE_DRIFT", _schema_seed_pin_drift),
    HostileCase("schema-lifecycle-drift", "FROZEN_SOURCE_DRIFT", _schema_lifecycle_drift),
    HostileCase("schemas-missing", "MISSING_ARTIFACT", _schemas_missing),
    HostileCase("receipt-absolute-path", "UNSAFE_PATH", None, ("--receipt", "/etc/passwd")),
    HostileCase("receipt-traversal", "UNSAFE_PATH", None, ("--receipt", "../../etc/passwd")),
    HostileCase("seed-root-traversal", "UNSAFE_PATH", None, ("--seed-root", "../outside")),
    HostileCase("root-missing", "MISSING_ARTIFACT", None, ("--root", "/nonexistent/m207-s04-root")),
)


# --------------------------------------------------------------------------- #
# Scaffolding.
# --------------------------------------------------------------------------- #


def _copy_surface(root: Path) -> None:
    """A faithful, minimal copy of the frozen surface the pilot reads."""
    receipt = load_json(ROOT / RECEIPT)
    relatives = [
        SCHEMAS,
        RECEIPT,
        PRIOR,
        S03_BATTERY,
        str(receipt["logs"]["stdout"]),
        str(receipt["logs"]["stderr"]),
    ]
    for relative in relatives:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    shutil.copytree(ROOT / FIXTURE, root / FIXTURE)
    crate = root / "crates" / "ln-decode" / "src"
    crate.mkdir(parents=True, exist_ok=True)
    (crate / "lib.rs").write_text("pub fn version() -> u8 { 1 }\n", encoding="utf-8")
    (root / "crates" / "ln-decode" / "Cargo.toml").write_text(
        '[package]\nname = "ln-decode"\nversion = "0.1.0"\n', encoding="utf-8"
    )


def _build_base_root() -> Path:
    holder = Path(tempfile.mkdtemp(prefix="m207-s04-suite-base-"))
    atexit.register(shutil.rmtree, holder, ignore_errors=True)
    root = holder / "root"
    _copy_surface(root)
    return root


BASE_ROOT = _build_base_root()
BASE_DIGEST = tree_digest(BASE_ROOT)


class SuiteBase(unittest.TestCase):
    """Shared temp-root and subprocess helpers."""

    def temp_root(self) -> Path:
        holder = Path(tempfile.mkdtemp(prefix="m207-s04-suite-"))
        self.addCleanup(shutil.rmtree, holder, ignore_errors=True)
        root = holder / "root"
        shutil.copytree(BASE_ROOT, root)
        return root

    def run_pilot(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PILOT), *args],
            cwd=str(ROOT),
            env=CHILD_ENV,
            text=True,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
        )

    def run_check(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_pilot("check", "--root", str(root), *extra)

    def assert_no_integrity_marker(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertNotIn(INTEGRITY_MARKER, result.stdout)
        self.assertNotIn(INTEGRITY_MARKER, result.stderr)

    def assert_fails_with(self, result: subprocess.CompletedProcess[str], diagnostic: str) -> None:
        self.assert_no_integrity_marker(result)
        self.assertEqual(result.returncode, 1, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn(f"FAIL {diagnostic}:", result.stderr)
        self.assertNotIn(MARKER, result.stdout)


# --------------------------------------------------------------------------- #
# Positive controls.
# --------------------------------------------------------------------------- #


class PositiveControlTests(SuiteBase):
    def test_clean_root_publishes_the_promotion_none_verdict(self) -> None:
        root = self.temp_root()
        result = self.run_check(root)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assert_no_integrity_marker(result)
        self.assertIn(MARKER, result.stdout)

        verdict_line = next(
            line for line in result.stdout.splitlines() if line.startswith(f"{VERDICT_TAG} ")
        )
        verdict = json.loads(verdict_line[len(VERDICT_TAG) + 1 :])
        self.assertEqual(verdict["schema"], "m207-s04-promotion-verdict/v1")
        self.assertEqual(verdict["promotion"], "none")
        self.assertEqual(verdict["classification"], "not-authorized")
        self.assertIsNone(verdict["threshold"])
        self.assertIsNone(verdict["human_acceptance"])
        self.assertIs(verdict["is_gold"], False)
        self.assertIs(verdict["model_invoked"], False)
        self.assertIs(verdict["human_pilot_performed"], False)
        self.assertEqual(verdict["legal_claim"], "forbidden")
        self.assertEqual(verdict["n2_claim"], "forbidden")
        self.assertEqual(verdict["rate_publication"], "forbidden")
        self.assertEqual(verdict["measurement_status_publication"], "forbidden")
        self.assertIs(verdict["corpus_complete_is_not_acceptance"], True)
        self.assertIs(verdict["integrity_marker_is_not_acceptance"], True)
        self.assertEqual(verdict["lifecycle"]["requirement_status_effect"], "unchanged")

        # The acceptance is derived from the terminal facts, never read from the claim.
        self.assertEqual(verdict["operational_acceptance"], "non-pass")
        self.assertEqual(verdict["receipt_published_acceptance"], "non-pass")
        basis = verdict["acceptance_basis"]
        self.assertEqual(basis["terminal_outcome"], "complete")
        self.assertEqual(basis["exit_code"], 0)
        self.assertIs(basis["timeout"], False)
        self.assertLess(basis["duration_ms"], basis["budget_ms"])
        self.assertIs(basis["budget_is_a_ceiling_not_an_achievement"], True)

        # The decode failure is published as an observation, not as a verdict.
        observations = verdict["semantic_observations"]
        self.assertEqual(observations["envelope_run_status"], "complete")
        self.assertEqual(observations["observed_file_count"], 43797)
        self.assertEqual(observations["decoded"], 43796)
        self.assertEqual(observations["failed"], 1)
        self.assertEqual(observations["acceptance_effect"], "none")
        self.assertIs(observations["failed_decode_is_a_parser_observation"], True)
        self.assertIn(SEMANTIC_TAG, result.stdout)
        self.assertIn("failed=1", result.stdout)
        self.assertEqual(verdict["stderr_observed_count"], 43785)

        # The S03 contour stays not-measured.
        isolation = verdict["s03_isolation"]
        self.assertEqual(isolation["evaluation_report"], "absent")
        self.assertIs(isolation["battery_human_pilot_performed"], False)
        self.assertIs(isolation["battery_current"], True)
        self.assertEqual(isolation["seed_fragment_count"], 180)
        self.assertEqual(isolation["crates_m207_references"], 0)
        self.assertEqual(isolation["s03_rates_status"], "not-measured")

    def test_later_battery_is_validated_when_present(self) -> None:
        root = self.temp_root()
        plant_battery(root)
        result = self.run_check(root)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(MARKER, result.stdout)

    def test_observations_never_move_the_verdict(self) -> None:
        """A zero-decode-failure envelope must not promote the acceptance either."""
        root = self.temp_root()

        def mutate(record: dict[str, Any]) -> None:
            record["failed"] = 0
            record["decoded"] = record["files"]
            for stage in record["stages"].values():
                stage["failed"] = 0

        edit_record(root, "aggregate", mutate)
        edit_record(root, "canonical_payload", lambda record: record.update({"failed": 0}))
        result = self.run_check(root)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        verdict = json.loads(
            next(line for line in result.stdout.splitlines() if line.startswith(f"{VERDICT_TAG} "))[
                len(VERDICT_TAG) + 1 :
            ]
        )
        self.assertEqual(verdict["operational_acceptance"], "non-pass")
        self.assertEqual(verdict["promotion"], "none")
        self.assertEqual(verdict["semantic_observations"]["failed"], 0)

    def test_real_repository_is_green_and_read_only(self) -> None:
        before = tree_digest(ROOT / EVID)
        result = self.run_pilot("check", "--root", str(ROOT))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(MARKER, result.stdout)
        self.assert_no_integrity_marker(result)
        self.assertEqual(before, tree_digest(ROOT / EVID))

    def test_check_writes_nothing_into_the_root(self) -> None:
        root = self.temp_root()
        before = tree_digest(root)
        result = self.run_check(root)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(before, tree_digest(root))

    def test_verdict_is_deterministic_and_carries_no_wall_clock(self) -> None:
        root = self.temp_root()
        first = self.run_check(root)
        second = self.run_check(root)
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        verdict = json.loads(
            next(line for line in first.stdout.splitlines() if line.startswith(f"{VERDICT_TAG} "))[
                len(VERDICT_TAG) + 1 :
            ]
        )
        for key in ("generated_at", "started_at", "finished_at", "timestamp", "elapsed_ms"):
            self.assertNotIn(key, verdict)

    def test_real_crates_tree_carries_no_m207_reference(self) -> None:
        """The plan's ``rg m207-s03 crates/`` assertion, re-derived without rg."""
        hits: list[str] = []
        for path in sorted((ROOT / "crates").rglob("*")):
            if not path.is_file() or path.suffix not in {".rs", ".toml", ".md", ".lock"}:
                continue
            if any(part in {"target", ".git"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(token in text for token in ("m207-s03", "m207_s03", "m207-s04", "m207_s04")):
                hits.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(hits, [])


# --------------------------------------------------------------------------- #
# Hostile registry.
# --------------------------------------------------------------------------- #


class HostileMatrixTests(SuiteBase):
    def test_every_hostile_case_fails_closed_with_its_named_diagnostic(self) -> None:
        for case in HOSTILE_CASES:
            with self.subTest(case=case.name):
                root = self.temp_root()
                if case.mutator is not None:
                    case.mutator(root)
                    self.assertNotEqual(
                        tree_digest(root),
                        BASE_DIGEST,
                        msg=f"hostile case {case.name!r} did not mutate its root",
                    )
                result = self.run_check(root, *case.extra_args)
                self.assert_fails_with(result, case.diagnostic)


class SuiteIntegrityTests(unittest.TestCase):
    def test_registry_is_populated_and_names_are_unique(self) -> None:
        self.assertGreaterEqual(len(HOSTILE_CASES), MIN_HOSTILE_CASES)
        names = [case.name for case in HOSTILE_CASES]
        self.assertEqual(len(names), len(set(names)))
        for case in HOSTILE_CASES:
            self.assertTrue(case.name)
            self.assertTrue(case.diagnostic)
            self.assertTrue(case.mutator is not None or case.extra_args)

    def test_every_named_diagnostic_exists_in_the_frozen_vocabulary(self) -> None:
        vocabulary = set(load_json(ROOT / SCHEMAS)["diagnostics"])
        named = {case.diagnostic for case in HOSTILE_CASES}
        self.assertEqual(sorted(named - vocabulary), [])

    def test_every_case_has_a_positive_discriminator(self) -> None:
        """Each hostile case must differ from a case that only breaks the pins."""
        self.assertNotIn("", {case.diagnostic for case in HOSTILE_CASES})
        self.assertGreaterEqual(len({case.diagnostic for case in HOSTILE_CASES}), 20)

    def test_every_emitted_diagnostic_is_declared_and_frozen(self) -> None:
        """A name the tool can speak must be declared by it and frozen by the contract."""
        source = PILOT.read_text(encoding="utf-8")
        emitted = set(re.findall(r'_fail\(\s*[^,]+,\s*"([A-Z][A-Z0-9_]+)"', source))
        emitted |= set(re.findall(r'GateError\(\s*"([A-Z][A-Z0-9_]+)"', source))
        frozen = set(load_json(ROOT / SCHEMAS)["diagnostics"])
        self.assertNotEqual(emitted, set())
        self.assertEqual(sorted(emitted - frozen), [])

        block = source.split("SPOKEN_DIAGNOSTICS = (")[1].split("\n)")[0]
        declared = set(re.findall(r'"([A-Z][A-Z0-9_]+)"', block))
        self.assertEqual(sorted(emitted - declared), [])
        self.assertEqual(sorted(declared - frozen), [])

    def test_gate_name_is_never_confused_with_the_marker(self) -> None:
        self.assertNotEqual(GATE, MARKER)
        self.assertNotIn(INTEGRITY_MARKER, MARKER)


if __name__ == "__main__":
    unittest.main()
