#!/usr/bin/env bash
# Offline closeout chain for the M207 S07 successor operational contour (T06).
#
# WHAT THIS CHAIN IS, AND WHAT ITS MARKER MEANS
#
#   * every battery row below is an integrity/policy check over the *new* S07 successor surface
#     (the frozen protocol + closed schema document, the read-only classifier of the two
#     historical receipts, the published successor receipt, the executable failure policy) plus
#     the regression of the frozen S04 contour and the cross-cutting lint/ADR rows;
#   * `M207_S07_VERIFY_OK` means **the S07 integrity/policy chain ran and every row and pin
#     passed**.  It is NOT a C4 pass, NOT operational acceptance, NOT a promotion, NOT gold, NOT
#     an independently measured rate and NOT an independent review.  The frozen S04/M204 receipts
#     keep `claims.operational_acceptance = non-pass`, the promotion verdict stays `none` with
#     `classification = not-authorized`, `human_acceptance` stays `null` and S03 rates stay
#     `not-measured`.  `M207_S04_VERIFY_OK` is the S04 chain's own marker and is deliberately not
#     reused here: this chain requires it from its S04 child and proves the two markers never
#     substitute for one another;
#   * there is no human half.  S07 runs no pilot and holds no human data, so this chain never
#     prints a human gate and never claims one.  The human pilot stays where D519 left it: not a
#     gate.
#
# BATTERY ROWS (nine, in this fixed order; ids are closed)
#
#   1. `s07_schemas`          -- `scripts/m207_s07_schemas.py check` (`M207_S07_SCHEMAS_OK`);
#   2. `s07_classify`         -- `scripts/m207_s07_c4_run.py classify` (`M207_S07_CLASSIFY_OK`).
#      Read-only: it classifies the frozen S04 and M204/S06 receipts and re-hashes both before and
#      after, so a byte shift is `HISTORICAL_BYTES_CHANGED`;
#   3. `s07_c4_receipt`       -- `scripts/m207_s07_c4_run.py check` (`M207_S07_C4_RECEIPT_OK`).
#      It validates the published successor receipt against the frozen contract and the live tree;
#   4. `s07_policy`           -- `scripts/m207_s07_policy.py check` (`M207_S07_POLICY_OK`).  It
#      re-derives the failure policy from the receipt plus its sidecar;
#   5. `s07_hostile_suite`    -- `scripts/test_m207_s07_policy.py` (`OK`): the adversarial suite
#      over the real CLI, including the `operational_acceptance` and `promotion = pass` refusals;
#   6. `s04_regression`       -- the frozen S04 gate, its machinery verifier and the S04 closeout
#      chain as one child: `scripts/m207_s04_c4_run.py check` (`M207_S04_C4_RECEIPT_OK`) +
#      `scripts/m207_s04_pilot.py check` (`M207_S04_PROMOTION_NONE_OK`) +
#      `bash scripts/m207_s04_t04_verify.sh` (`M207_S04_VERIFY_OK`).  All three markers are
#      required; the S04 chain is invoked with no write opt-in, so the frozen S04 battery can
#      never be rewritten from here;
#   7. `ruff_format`, 8. `ruff_check` -- the new S07 Python surface;
#   9. `adr_conformance`      -- `scripts/verify-adr-conformance.py` (`"finding_count": 0`).
#
#   A marker is required, not merely an exit code: a row that exits 0 without printing its own
#   marker is `SUBCLI_FAILURE`, and a row that exits non-zero is `ROW_FAILED` with its id.
#
# CHAIN-LEVEL PINS (deliberately NOT battery rows)
#
#   * the four frozen digests the successor contract names -- the S04 receipt (`423d30de...`), the
#     M204/S06 receipt (`04e41f89...`), the S04 battery (`cc6dbb39...`) and the S03 battery
#     (`76b9a78e...`) -- plus the S03 battery's `human_pilot_performed == false`;
#   * the 180 frozen seed fragments under `crates/ln-decode/tests/fixtures/npa-lawref`;
#   * `crates/**` carries no S07 token: the successor contract stays harness-local.  The reused
#     sidecar schema id `npa-contour-failure-trace/v1` is deliberately NOT part of this pin: it is
#     owned by the Rust writer (`crates/ln-consultant-parser/src/contour_diagnostics.rs`) and has
#     been there since M204/S06, and the S07 contract reuses it verbatim
#     (`failure_policy.sidecar_schema_reused_verbatim = true`).  Requiring its absence from
#     `crates/**` would contradict the frozen contract the same slice publishes.  The pinned S07
#     tokens are `m207-s07` (which also covers the `m207-s07-c4-operational-successor` schema id),
#     `m207_s07` and `M207_S07_`;
#   * the acceptance-lexicon roster: the four new S07 scripts may mention
#     `operational_acceptance` / `promotion ... pass` / `is_gold ... true` only on the reviewed
#     lines of `lexicon.py`'s frozen roster (refusal lists, read-only echoes of the historical
#     claim, and hostile fixtures).  Any additional or changed lexicon line is
#     `ACCEPTANCE_LEXICON_LEAK`, and the scanner proves itself against planted positive claims
#     (`ACCEPTANCE_LEXICON_UNPROVEN` if it ever misses one);
#   * the four S07 selftests (`schemas`, `classify`, `recorder`, `policy`), which are the executable
#     proof that `promotion = pass`, `is_gold = true` and a receipt-carried
#     `operational_acceptance` are refused by name;
#   * the marker-isolation pins: the S07 read-only tools emit no `M207_S04_*` marker, and the S04
#     child's last line is its own `M207_S04_VERIFY_OK` and never `M207_S07_VERIFY_OK`;
#   * `s07-receipt-facts`: compact observation lines (argv digest, predicate outcome, sidecar
#     rows, `aggregate.failed`, `acceptance_effect`, duration, budget, provider/class vocabulary)
#     for the durable log.  They are projections of what the rows above already proved, never a
#     second gate and never a second verdict.
#
# FAIL-CLOSED GUARDS AND THE BATTERY
#
#   * the chain takes NO arguments: it never accepts `--root`, because a foreign forged tree with a
#     self-consistent store would otherwise reach the marker.  The root comes from BASH_SOURCE;
#   * the battery opt-in `M207_S07_WRITE_BATTERY` is read once and then unset together with every
#     other Sxx opt-in, so no child process (the hostile suite, the S04 chain) can inherit a
#     mode-switching variable, and the mandatory read-only confirmation pass can never silently
#     rewrite the tracked artifact -- which would make `BATTERY_STALE` unobservable;
#   * without the opt-in the chain is READ-ONLY with respect to
#     `prd/migration/rust-evidence/m207-s07-battery.json`: it assembles the payload and compares it
#     with the tracked file byte-for-byte, failing closed with `BATTERY_STALE` on any difference.
#     With `M207_S07_WRITE_BATTERY=1` it regenerates the battery exactly once (D473) and then
#     confirms it with the same read-only pass;
#   * the assembler refuses `write` without the environment opt-in (`AUTHORITY_CLAIM`), a result
#     table whose id set or order drifts from the frozen chain (`BATTERY_ROW_SET_DRIFT`), a
#     non-green row (`BATTERY_ROW_NOT_GREEN`), a pin whose digest moved (`PIN_DRIFT`), a missing
#     artifact (`MISSING_ARTIFACT`), a promotion contract that is no longer
#     `none`/`not-authorized`/`null`/`false` (`PROMOTION_CONTRACT_DRIFT`) and any assembled
#     payload that carries an acceptance claim (`ACCEPTANCE_CLAIM_IN_BATTERY`);
#   * `durationMs` is a closed row key and is NORMALIZED TO `null` in the tracked bytes.  The
#     tracked battery persists no wall-clock (the S04 precedent, `BATTERY_WALLCLOCK_FORBIDDEN`);
#     the live timings are printed as `M207_S07_BATTERY_TIMINGS` and never reach the tracked file.
#     That is exactly what makes the byte-for-byte comparison above possible: two consecutive runs
#     produce identical bytes, so any hand edit of a row, a command, an exit code, a pin or an
#     honesty key is `BATTERY_STALE`;
#   * neither the chain nor the battery reads `.gsd/`, `.planning/` or `.audits/`.  Everything is
#     resolved against the working tree.
set -euo pipefail

readonly MARKER="M207_S07_VERIFY_OK"
readonly FAIL_EXIT=1

# The closing chain never accepts a foreign root: a forged tree would otherwise be
# indistinguishable from the repository.  Named, fail-closed.
if [ "$#" -ne 0 ]; then
  printf 'FAIL UNSAFE_PATH: the closing chain takes no arguments; --root is refused and the repository root comes from BASH_SOURCE\n' >&2
  exit "$FAIL_EXIT"
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

readonly EVIDENCE="prd/migration/rust-evidence"
readonly BATTERY="$EVIDENCE/m207-s07-battery.json"
readonly S03_BATTERY="$EVIDENCE/m207-s03-battery.json"
readonly S04_RECEIPT="$EVIDENCE/m207-s04-c4-operational-receipt.json"
readonly M204_RECEIPT="$EVIDENCE/m204-s06-c4-operational-receipt.json"
readonly S04_BATTERY="$EVIDENCE/m207-s04-battery.json"
readonly S07_RECEIPT="$EVIDENCE/m207-s07-c4-operational-receipt.json"

readonly S04_RECEIPT_SHA256="423d30de06080fce1c3da255d1d03cc3f19548d29e4338c74d913f4771e9e935"
readonly M204_RECEIPT_SHA256="04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c"
readonly S04_BATTERY_SHA256="cc6dbb3933bc8e5d91c3cf7866ed28e40061a5740c77429b923d4e487ade91fc"
readonly S03_BATTERY_SHA256="76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533"

# The S07 tokens that must stay out of the product tree.  `npa-contour-failure-trace` is excluded
# on purpose: it is the pre-existing Rust-owned sidecar schema id reused verbatim by S07 (see the
# header), so pinning its absence would contradict the frozen contract this chain validates.
readonly CRATES_FORBIDDEN_TOKENS='m207-s07|m207_s07|M207_S07_'

readonly SEED_ROOT="crates/ln-decode/tests/fixtures/npa-lawref"

readonly S04_REGRESSION_COMMAND='uv run python scripts/m207_s04_c4_run.py check && uv run python scripts/m207_s04_pilot.py check && bash scripts/m207_s04_t04_verify.sh'

# The Python surface the formatter and the linter cover (the bash chain is not Python; the
# S01--S06 scripts are covered by their own chains).
S07_PY=(
  scripts/m207_s07_schemas.py
  scripts/m207_s07_c4_run.py
  scripts/m207_s07_policy.py
  scripts/test_m207_s07_policy.py
)
readonly S07_PY

work="$(mktemp -d -t m207-s07-t06-XXXXXX)"
readonly results="$work/results.tsv"
readonly stage_log="$work/stage.log"
readonly s04_view="$work/s04-regression.log"

trap 'rm -rf "$work"' EXIT

: >"$results"

# Read the D473 opt-in ONCE, before any child process runs, and then clear every write flag so no
# row, pin or nested chain can inherit a mode-switching variable.  Only the single authorized
# battery command below is handed the opt-in again.
write_battery=0
if [ "${M207_S07_WRITE_BATTERY:-0}" = "1" ]; then
  write_battery=1
fi
unset M207_S07_WRITE_BATTERY
unset M207_S04_WRITE_BATTERY
unset M207_S03_WRITE_BATTERY
unset M207_S02_WRITE_BATTERY
unset M207_S01_WRITE_BATTERY

# --------------------------------------------------------------------------- #
# Helper scripts (kept in the temp workdir; their paths never reach the tracked
# battery because every persisted command column is a fixed display string).
# --------------------------------------------------------------------------- #

readonly LEXICON_PY="$work/lexicon.py"
readonly BATTERY_PY="$work/battery.py"
readonly OBSERVE_PY="$work/observe.py"

cat >"$LEXICON_PY" <<'PY'
#!/usr/bin/env python3
"""Pin: the new S07 scripts carry no unreviewed acceptance lexicon.

The successor contract must be able to *talk* about ``operational_acceptance`` and
``promotion = pass`` -- to forbid them, to echo the historical claim read-only, and to plant them
as hostile fixtures.  It must never *assert* them.  This scanner freezes the exact set of matching
lines that the four S07 scripts are allowed to carry (the reviewed roster below: refusal key
lists, read-only echoes, hostile fixtures and the promotion-contract mutation), so any added or
edited lexicon line is refused by name.  The scanner then proves itself against planted positive
claims, so a silently broken pattern is also refused.
"""

from __future__ import annotations

import pathlib
import re
import sys

PATTERNS = (
    r"operational_acceptance",
    r"promotion.*pass",
    r"is_gold.*true",
)

ROSTER: dict[str, list[str]] = {
    "scripts/m207_s07_schemas.py": [
        'schema["promotion_contract"]["promotion"] = "pass"',
        '("promotion-pass", "PROMOTION_CLAIM", _mutate_promotion),',
    ],
    "scripts/m207_s07_c4_run.py": [
        "* ``claims.operational_acceptance`` is read and echoed for comparison only.  The verdict is",
        "``operational_acceptance`` key at all: ``claims.operational_classification`` is the successor",
        "# The closed receipt closure.  ``operational_acceptance`` is deliberately absent: the successor",
        'RECEIPT_FORBIDDEN_ACCEPTANCE_KEYS = ("operational_acceptance", "acceptance")',
        '"operational_acceptance",',
        '"""Read ``claims.operational_acceptance`` as history, never as a verdict input."""',
        'return claims.get("operational_acceptance")',
        '"claims_operational_acceptance": _claim_view(receipt),',
        '"claims_operational_acceptance": report["claims_operational_acceptance"],',
        '"operational_acceptance leaked into the successor receipt",',
        '"operational_acceptance" not in published,',
        'lambda r: r.__setitem__("operational_acceptance", "pass"),',
        'lambda r: r.__setitem__("promotion", "pass"),',
        'f"{rel} claims.operational_acceptance is "',
        "f\"{item['claims_operational_acceptance']!r}, historical receipts stay non-pass\",",
        'item["claims_operational_acceptance"] == "non-pass",',
        'claims_pass["claims"] = {"operational_acceptance": "pass"}',
        "\"a claims.operational_acceptance of 'pass' must not turn a limited walk into a \"",
    ],
    "scripts/m207_s07_policy.py": [
        "# The closed successor receipt closure.  ``operational_acceptance`` is deliberately absent: the",
        'RECEIPT_FORBIDDEN_ACCEPTANCE_KEYS = ("operational_acceptance", "acceptance")',
        '"receipt_operational_acceptance",',
        'root, lambda document: document.update({"operational_acceptance": "pass"})',
        'root, lambda document: document.update({"promotion": "pass"})',
    ],
    "scripts/test_m207_s07_policy.py": [
        "def _receipt_operational_acceptance(root: Path) -> None:",
        '_edit_receipt(root, lambda document: document.update({"operational_acceptance": "pass"}))',
        '_edit_receipt(root, lambda document: document.update({"promotion": "pass"}))',
        '"receipt-operational-acceptance", "SCHEMA_KEY_DRIFT", _receipt_operational_acceptance',
    ],
}

SYNTHETIC = (
    'RECEIPT = {"promotion": "pass"}',
    'RECEIPT = {"is_gold": true}',
    'claims = {"operational_acceptance": "pass"}',
)


def matches(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if any(re.search(p, line) for p in PATTERNS)]


def main() -> int:
    problems: list[str] = []
    root = pathlib.Path.cwd()
    total = 0
    for rel, expected in ROSTER.items():
        path = root / rel
        if not path.is_file():
            problems.append(f"MISSING_ARTIFACT: {rel}")
            continue
        observed = matches(path.read_text(encoding="utf-8"))
        total += len(observed)
        if observed != list(expected):
            gained = [line for line in observed if line not in expected]
            lost = [line for line in expected if line not in observed]
            problems.append(
                f"ACCEPTANCE_LEXICON_LEAK: {rel} gained {gained!r} and lost {lost!r}; the "
                "successor surface may only carry the reviewed refusal/echo/hostile roster"
            )
    for sample in SYNTHETIC:
        if not matches(sample):
            problems.append(
                f"ACCEPTANCE_LEXICON_UNPROVEN: the scanner missed the planted positive claim "
                f"{sample!r}"
            )
    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    if problems:
        print(f"FAIL ACCEPTANCE_LEXICON_PIN: {len(problems)} finding(s)", file=sys.stderr)
        return 1
    print(
        f"acceptance_lexicon roster_lines={total} files={len(ROSTER)} synthetic_controls={len(SYNTHETIC)} clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat >"$OBSERVE_PY" <<'PY'
#!/usr/bin/env python3
"""Read-only observation lines for the published S07 attempt and its failure sidecar.

Projections of what the gate rows already proved: never a second gate, never a second verdict.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

receipt_rel = sys.argv[1]
root = pathlib.Path.cwd()
receipt = json.loads((root / receipt_rel).read_text(encoding="utf-8"))

sidecar_rel = receipt["failure_policy"]["failures_out_path"]
sidecar = root / sidecar_rel
if not sidecar.is_file():
    print(f"FAIL MISSING_SIDECAR: {sidecar_rel}", file=sys.stderr)
    raise SystemExit(1)
raw = sidecar.read_bytes()
rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]

identity = receipt["immutable_attempt_identity"]
terminal = receipt["terminal"]
policy = receipt["failure_policy"]
print(
    "s07_receipt attempt=%s argv_sha256=%s outcome=%s full_walk=%s timeout=%s terminal=%s/%s/%s "
    "duration_ms=%d budget_seconds=%d acceptance_effect=%s"
    % (
        receipt["attempt_id"],
        identity["argv_sha256"],
        receipt["predicates"]["outcome"],
        receipt["predicates"]["full_walk"],
        receipt["predicates"]["timeout"],
        terminal["outcome"],
        terminal["exit_code"],
        terminal["signal"],
        receipt["duration_ms"],
        receipt["budget_seconds"],
        policy["acceptance_effect"],
    )
)
print(
    "s07_sidecar rows=%d aggregate_failed=%d sidecar_sha256=%s providers=%s classes=%s "
    "record_kinds=%s"
    % (
        len(rows),
        policy["aggregate_failed"],
        hashlib.sha256(raw).hexdigest(),
        sorted({str(row.get("provider")) for row in rows}),
        sorted({str(row.get("class")) for row in rows}),
        sorted({str(row.get("record_kind")) for row in rows}),
    )
)
if len(rows) != policy["sidecar_rows"]:
    print(
        f"FAIL SIDECAR_COUNT_DRIFT: {len(rows)} rows against published sidecar_rows="
        f"{policy['sidecar_rows']}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

cat >"$BATTERY_PY" <<'PY'
#!/usr/bin/env python3
"""Assemble (write) or verify (read) the tracked M207 S07 battery.

The payload is a projection of the frozen S07 contract plus live observations: rows come from the
chain's own result table, the honesty keys come from the contract's promotion/s03 blocks (each one
asserted, never trusted blindly), the pins are re-hashed from the live tree and compared with the
digests the contract names, and `new_receipt_classification` is the outcome the receipt gate
recomputed for the live successor attempt.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

SCHEMA_ID = "m207-s07-battery/v1"
SCHEMA_VERSION = 1
SCHEMAS_REL = "prd/annotation/m207-s07-schemas.json"
S03_BATTERY_REL = "prd/migration/rust-evidence/m207-s03-battery.json"
SEED_ROOT = "crates/ln-decode/tests/fixtures/npa-lawref"
SEED_COUNT = 180

ROW_IDS = [
    "s07_schemas",
    "s07_classify",
    "s07_c4_receipt",
    "s07_policy",
    "s07_hostile_suite",
    "s04_regression",
    "ruff_format",
    "ruff_check",
    "adr_conformance",
]
ROW_KEYS = {"id", "status", "durationMs", "command", "exit_code"}

PINS = {
    "m204_s06_c4_operational_receipt": (
        "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
        "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c",
    ),
    "m207_s03_battery": (
        "prd/migration/rust-evidence/m207-s03-battery.json",
        "76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533",
    ),
    "m207_s04_battery": (
        "prd/migration/rust-evidence/m207-s04-battery.json",
        "cc6dbb3933bc8e5d91c3cf7866ed28e40061a5740c77429b923d4e487ade91fc",
    ),
    "m207_s04_c4_operational_receipt": (
        "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
        "423d30de06080fce1c3da255d1d03cc3f19548d29e4338c74d913f4771e9e935",
    ),
}

OUTCOMES = ("full_walk", "timeout", "nonzero", "launch_error")

FORBIDDEN_CLAIM_KEYS = ("operational_acceptance", "acceptance")


def main() -> int:
    problems: list[str] = []

    def fail(code: str, detail: str) -> None:
        problems.append(f"{code}: {detail}")

    results_rel, battery_rel, mode, new_classification = sys.argv[1:5]
    root = pathlib.Path.cwd()

    # 1. The result table: closed id set, frozen order, every row green.
    rows: list[dict[str, object]] = []
    seen: list[str] = []
    durations: list[tuple[str, int]] = []
    for raw in pathlib.Path(results_rel).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 4:
            fail("BATTERY_RESULTS_MALFORMED", f"row {raw!r} is not id/status/durationMs/command")
            continue
        row_id, status, duration_ms, command = parts
        seen.append(row_id)
        try:
            exit_code = int(status)
            durations.append((row_id, int(duration_ms)))
        except ValueError:
            fail("BATTERY_RESULTS_MALFORMED", f"row {row_id} carries a non-integer status/duration")
            continue
        row = {
            "id": row_id,
            "status": "pass" if exit_code == 0 else "fail",
            "durationMs": None,
            "command": command,
            "exit_code": exit_code,
        }
        if set(row) != ROW_KEYS:
            fail("SCHEMA_KEY_DRIFT", f"battery row {row_id} is not a closed battery row")
        if row["status"] != "pass":
            fail("BATTERY_ROW_NOT_GREEN", f"row {row_id} carries exit_code {exit_code}")
        rows.append(row)
    if seen != ROW_IDS:
        fail(
            "BATTERY_ROW_SET_DRIFT",
            f"the observed row ids {seen!r} are not the frozen chain {ROW_IDS!r}",
        )

    # 2. Honesty keys, asserted against the frozen contract document.
    schemas = json.loads((root / SCHEMAS_REL).read_text(encoding="utf-8"))
    promotion = schemas["promotion_contract"]
    isolation = schemas["s03_isolation"]
    non_claims = schemas["non_claims"]
    lifecycle = schemas["lifecycle"]
    for label, observed, expected in (
        ("promotion_contract.promotion", promotion.get("promotion"), "none"),
        ("promotion_contract.classification", promotion.get("classification"), "not-authorized"),
        ("promotion_contract.human_acceptance", promotion.get("human_acceptance"), None),
        ("promotion_contract.is_gold", promotion.get("is_gold"), False),
        ("promotion_contract.model_invoked", promotion.get("model_invoked"), False),
        (
            "promotion_contract.acceptance_effect_of_failures",
            promotion.get("acceptance_effect_of_failures"),
            "none",
        ),
        (
            "s03_isolation.s03_rates_required_status",
            isolation.get("s03_rates_required_status"),
            "not-measured",
        ),
        (
            "s03_isolation.s03_battery_human_pilot_performed_required",
            isolation.get("s03_battery_human_pilot_performed_required"),
            False,
        ),
        ("lifecycle.requirement_status_effect", lifecycle.get("requirement_status_effect"), "unchanged"),
    ):
        if observed != expected:
            fail("PROMOTION_CONTRACT_DRIFT", f"{label} is {observed!r}, expected {expected!r}")
    if not isinstance(non_claims, list) or not non_claims:
        fail("MISSING_NON_CLAIM", "the frozen non-claims could not be read from the contract")
    elif not all(isinstance(item, str) and item.startswith("not ") for item in non_claims):
        fail("MISSING_NON_CLAIM", "every frozen non-claim must be stated as a refusal")

    # 3. Pins, re-hashed from the live tree and compared with the contract's digests.
    pins: dict[str, object] = {}
    for name, (rel, expected) in PINS.items():
        path = root / rel
        if not path.is_file():
            fail("MISSING_ARTIFACT", f"the pinned artifact {rel} is missing")
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            fail("PIN_DRIFT", f"pin {name} moved: {observed} != {expected} ({rel})")
            continue
        pins[name] = {"path": rel, "sha256": observed}
    seed_root = root / SEED_ROOT
    seed_count = len(list(seed_root.glob("*.txt"))) if seed_root.is_dir() else -1
    if seed_count != SEED_COUNT:
        fail("SEED_ENLARGE", f"{SEED_ROOT} carries {seed_count} fragments, expected {SEED_COUNT}")
    s03_battery = json.loads((root / S03_BATTERY_REL).read_text(encoding="utf-8"))
    if s03_battery.get("human_pilot_performed") is not False:
        fail(
            "S03_BATTERY_PILOT_PERFORMED",
            "the S03 battery no longer records human_pilot_performed = false",
        )
    pins["s03_human_pilot_performed"] = False
    pins["seed_fragment_count"] = SEED_COUNT

    # 4. The live outcome the receipt gate recomputed for the successor attempt.
    if new_classification not in OUTCOMES:
        fail(
            "RECEIPT_CLASSIFICATION_DRIFT",
            f"the live receipt outcome {new_classification!r} is outside the closed set {OUTCOMES!r}",
        )

    # 5. The payload.
    payload = {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "rows": rows,
        "promotion": promotion.get("promotion"),
        "classification": promotion.get("classification"),
        "human_acceptance": promotion.get("human_acceptance"),
        "is_gold": promotion.get("is_gold"),
        "model_invoked": promotion.get("model_invoked"),
        "human_pilot_performed": False,
        "s03_rates_status": isolation.get("s03_rates_required_status"),
        "operational_acceptance_effect": promotion.get("acceptance_effect_of_failures"),
        "new_receipt_classification": new_classification,
        "pins": pins,
        "non_claims": non_claims,
        "lifecycle": lifecycle,
    }
    scan_claims(payload, fail)

    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    target = root / battery_rel
    timings = " ".join(f"{row_id}={ms}ms" for row_id, ms in durations)
    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    if problems:
        print(f"FAIL M207_S07_BATTERY_GATE: {len(problems)} finding(s)", file=sys.stderr)
        return 1
    if mode == "write":
        if os.environ.get("M207_S07_WRITE_BATTERY") != "1":
            print(
                "FAIL AUTHORITY_CLAIM: battery write requires M207_S07_WRITE_BATTERY=1",
                file=sys.stderr,
            )
            return 1
        target.write_text(text, encoding="utf-8")
        print(f"M207_S07_BATTERY_OK checks={len(rows)} path={target.name} written sha256={digest}")
    elif mode == "read":
        if not target.is_file():
            print(f"FAIL MISSING_ARTIFACT: the tracked battery {battery_rel} is missing", file=sys.stderr)
            return 1
        tracked = target.read_text(encoding="utf-8")
        if tracked != text:
            detail = first_difference(tracked, text)
            print(f"FAIL BATTERY_STALE: {battery_rel} differs from the live run at {detail}", file=sys.stderr)
            return 1
        print(f"M207_S07_BATTERY_OK checks={len(rows)} path={target.name} current sha256={digest}")
    else:
        print(f"FAIL BATTERY_MODE: unknown mode {mode!r}", file=sys.stderr)
        return 1
    print(f"M207_S07_BATTERY_TIMINGS {timings}")
    return 0


def first_difference(tracked: str, fresh: str) -> str:
    """Name the first differing line of the tracked and freshly assembled payloads."""
    tracked_lines = tracked.splitlines()
    fresh_lines = fresh.splitlines()
    for index, (left, right) in enumerate(zip(tracked_lines, fresh_lines), start=1):
        if left != right:
            return f"line {index}: tracked={left.strip()!r} fresh={right.strip()!r}"
    return f"line count: tracked={len(tracked_lines)} fresh={len(fresh_lines)}"


def scan_claims(payload: object, fail) -> None:
    """Refuse any positive acceptance claim in the assembled payload.

    The battery is an honesty ledger: it may record `"none"`, `"not-authorized"`, `null` and
    `false`, and nothing else.  A missing key is drift too, because a reader must be able to see
    the refusals rather than infer them from absence.
    """
    expected = {
        "promotion": ("none",),
        "classification": ("not-authorized",),
        "human_acceptance": (None,),
        "is_gold": (False,),
        "model_invoked": (False,),
        "human_pilot_performed": (False,),
        "s03_rates_status": ("not-measured",),
        "operational_acceptance_effect": ("none",),
    }
    if not isinstance(payload, dict):
        fail("ACCEPTANCE_CLAIM_IN_BATTERY", "the assembled battery is not an object")
        return
    for key, allowed in expected.items():
        if key not in payload:
            fail("ACCEPTANCE_CLAIM_IN_BATTERY", f"the honesty key {key} is missing")
            continue
        if payload[key] not in allowed:
            fail(
                "ACCEPTANCE_CLAIM_IN_BATTERY",
                f"{key} is {payload[key]!r}, expected one of {allowed!r}",
            )
    for key in FORBIDDEN_CLAIM_KEYS:
        if key in payload:
            fail("ACCEPTANCE_CLAIM_IN_BATTERY", f"the forbidden claim key {key!r} is present")
    for pointer, value in walk(payload):
        if isinstance(value, str) and value.lower() in {"pass", "accepted", "gold", "true"}:
            tail = pointer.rsplit(".", 1)[-1].lower()
            if any(token in tail for token in ("promotion", "acceptance", "gold", "claim")):
                fail(
                    "ACCEPTANCE_CLAIM_IN_BATTERY",
                    f"{pointer} carries the positive value {value!r}",
                )


def walk(node: object, pointer: str = "battery"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f"{pointer}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{pointer}[{index}]")
    else:
        yield pointer, node


if __name__ == "__main__":
    raise SystemExit(main())
PY

# --------------------------------------------------------------------------- #
# Battery-row machinery: execute, require the row's own marker, commit the row.
# --------------------------------------------------------------------------- #

failed=0
row_status=0
row_ms=0
row_display=""

row_eval() {
  local id="$1" command="$2" display="${3:-$2}"
  local start end
  start="$(date +%s%N)"
  : >"$stage_log"
  if bash -c "$command" >"$stage_log" 2>&1; then
    row_status=0
  else
    row_status=$?
    failed=1
  fi
  end="$(date +%s%N)"
  row_ms=$(( (end - start) / 1000000 ))
  row_display="$display"
  printf '[m207-s07] %-20s exit=%d %8dms %s\n' "$id" "$row_status" "$row_ms" "$display"
  if [ "$row_status" -eq 0 ]; then
    tail -n 2 "$stage_log" | sed 's/^/    /'
  else
    tail -n 25 "$stage_log" | sed 's/^/    /'
  fi
}

# A row whose gate must also print the marker it claims: a zero exit without the marker is a
# contract failure, not a success.
row_check_marker() {
  local id="$1" pattern="$2"
  if [ "$row_status" -eq 0 ] && ! grep -Eq "$pattern" "$stage_log"; then
    printf 'FAIL SUBCLI_FAILURE: row %s exited 0 without printing %s\n' "$id" "$pattern" >&2
    row_status=1
    failed=1
  fi
}

row_finish() {
  local id="$1"
  if [ "$row_status" -ne 0 ]; then
    printf 'FAIL ROW_FAILED: row %s is not green (exit %d)\n' "$id" "$row_status" >&2
  fi
  printf '%s\t%d\t%d\t%s\n' "$id" "$row_status" "$row_ms" "$row_display" >>"$results"
}

# Chain-level pins: executed like rows but never persisted as battery rows.
pin() {
  local id="$1" command="$2" display="${3:-$2}"
  row_eval "$id" "$command" "$display"
  if [ "$row_status" -ne 0 ]; then
    printf 'FAIL PIN_FAILED: pin %s is not green (exit %d)\n' "$id" "$row_status" >&2
  fi
}

pin_sha() {
  local id="$1" rel="$2" expected="$3"
  local command
  command='test "$(sha256sum '"$rel"' | cut -d" " -f1)" = "'"$expected"'"'
  pin "$id" "$command" "sha256($rel) == $expected"
}

printf '%s\n' '[m207-s07] offline S07 closeout chain (integrity/policy battery; not a C4 pass)'

# --------------------------------------------------------------------------- #
# 1. Machinery: the nine frozen battery rows, in the frozen order.
# --------------------------------------------------------------------------- #
row_eval s07_schemas 'uv run python scripts/m207_s07_schemas.py check'
row_check_marker s07_schemas 'M207_S07_SCHEMAS_OK'
row_finish s07_schemas

row_eval s07_classify 'uv run python scripts/m207_s07_c4_run.py classify'
row_check_marker s07_classify 'M207_S07_CLASSIFY_OK'
row_finish s07_classify

row_eval s07_c4_receipt 'uv run python scripts/m207_s07_c4_run.py check'
row_check_marker s07_c4_receipt 'M207_S07_C4_RECEIPT_OK'
row_finish s07_c4_receipt

row_eval s07_policy 'uv run python scripts/m207_s07_policy.py check'
row_check_marker s07_policy 'M207_S07_POLICY_OK'
row_finish s07_policy

row_eval s07_hostile_suite 'uv run python scripts/test_m207_s07_policy.py'
row_check_marker s07_hostile_suite '^OK$'
row_finish s07_hostile_suite

row_eval s04_regression "$S04_REGRESSION_COMMAND" \
  "$S04_REGRESSION_COMMAND (markers M207_S04_C4_RECEIPT_OK, M207_S04_PROMOTION_NONE_OK and M207_S04_VERIFY_OK required)"
row_check_marker s04_regression 'M207_S04_C4_RECEIPT_OK'
row_check_marker s04_regression 'M207_S04_PROMOTION_NONE_OK'
row_check_marker s04_regression 'M207_S04_VERIFY_OK'
cp "$stage_log" "$s04_view"
row_finish s04_regression

row_eval ruff_format "uv run ruff format --check ${S07_PY[*]}"
row_finish ruff_format

row_eval ruff_check "uv run ruff check ${S07_PY[*]}"
row_finish ruff_check

row_eval adr_conformance 'uv run python scripts/verify-adr-conformance.py'
row_check_marker adr_conformance '"finding_count": ?0'
row_finish adr_conformance

# --------------------------------------------------------------------------- #
# 2. Chain-level pins (not battery rows).  A green pin is not a status change.
# --------------------------------------------------------------------------- #
pin_sha pin-s04-receipt "$S04_RECEIPT" "$S04_RECEIPT_SHA256"
pin_sha pin-m204-receipt "$M204_RECEIPT" "$M204_RECEIPT_SHA256"
pin_sha pin-s04-battery "$S04_BATTERY" "$S04_BATTERY_SHA256"
pin_sha pin-s03-battery "$S03_BATTERY" "$S03_BATTERY_SHA256"

pin pin-s03-human-pilot-absent \
  "uv run python -c 'import json,pathlib; d=json.loads(pathlib.Path(\"$S03_BATTERY\").read_text(encoding=\"utf-8\")); raise SystemExit(0 if d.get(\"human_pilot_performed\") is False else 1)'" \
  'm207-s03-battery human_pilot_performed == false'

pin pin-seed-count \
  "test \"\$(find $SEED_ROOT -name '*.txt' | wc -l | tr -d ' ')\" = 180" \
  "seed fragment count under $SEED_ROOT == 180"

pin pin-crates-local \
  "! grep -rIE --exclude-dir=target '$CRATES_FORBIDDEN_TOKENS' crates/" \
  "no S07 token under crates/ ($CRATES_FORBIDDEN_TOKENS)"

pin pin-acceptance-lexicon \
  "uv run python '$LEXICON_PY'" \
  'the four new S07 scripts carry no unreviewed acceptance lexicon (frozen roster + planted controls)'

pin pin-s07-schemas-selftest \
  'uv run python scripts/m207_s07_schemas.py selftest' \
  'uv run python scripts/m207_s07_schemas.py selftest (M207_S07_SCHEMAS_SELFTEST_OK: promotion=pass and is_gold=true refused)'
pin pin-s07-classify-selftest \
  'uv run python scripts/m207_s07_c4_run.py selftest' \
  'uv run python scripts/m207_s07_c4_run.py selftest (M207_S07_C4_CLASSIFY_SELFTEST_OK)'
pin pin-s07-recorder-selftest \
  'uv run python scripts/m207_s07_c4_run.py recorder-selftest' \
  'uv run python scripts/m207_s07_c4_run.py recorder-selftest (M207_S07_C4_RECORDER_SELFTEST_OK)'
pin pin-s07-policy-selftest \
  'uv run python scripts/m207_s07_policy.py selftest' \
  'uv run python scripts/m207_s07_policy.py selftest (M207_S07_POLICY_SELFTEST_OK)'

pin pin-s07-tools-emit-no-s04-marker \
  '! { uv run python scripts/m207_s07_schemas.py check; uv run python scripts/m207_s07_c4_run.py classify; uv run python scripts/m207_s07_c4_run.py check; uv run python scripts/m207_s07_policy.py check; } 2>&1 | grep -q "M207_S04"' \
  'the S07 read-only tools emit no M207_S04 marker'

pin pin-s04-chain-marker-isolate \
  "tail -n 1 '$s04_view' | grep -qx M207_S04_VERIFY_OK && ! grep -q M207_S07_VERIFY_OK '$s04_view'" \
  'the S04 child ends on its own S04 marker and never prints the S07 marker'

pin pin-s07-receipt-facts \
  "uv run python '$OBSERVE_PY' '$S07_RECEIPT'" \
  'uv run python <observe> prd/migration/rust-evidence/m207-s07-c4-operational-receipt.json (receipt + sidecar observation lines)'

# The live outcome the receipt gate recomputed for the successor attempt: assembled into the
# battery as `new_receipt_classification`, never read from a claim.
new_classification=""
if ! new_classification="$(uv run python scripts/m207_s07_c4_run.py check 2>/dev/null \
  | uv run python -c 'import json,sys; print(json.load(sys.stdin)["predicates"]["outcome"])')"; then
  printf '%s\n' '[m207-s07] FAIL SUBCLI_FAILURE: the successor receipt outcome could not be recomputed' >&2
  exit "$FAIL_EXIT"
fi
printf '[m207-s07] %-20s %s\n' 'new-classification' "$new_classification"

if [ "$failed" -ne 0 ]; then
  printf '%s\n' '[m207-s07] FAILED -- the S07 integrity/policy contour is red; see the failing row or pin above' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 3. Battery: assemble from the result table (write only under the D473 opt-in),
#    then confirm with a read-only pass that must stay current.  The opt-in was
#    read once at the top and unset, so the confirmation run cannot rewrite
#    anything -- which is what keeps `BATTERY_STALE` observable.
# --------------------------------------------------------------------------- #
if [ "$write_battery" -eq 1 ]; then
  printf '%s\n' '[m207-s07] M207_S07_WRITE_BATTERY=1: regenerating the tracked battery once'
  # The opt-in was read once at the top and then unset, so the authorization is re-supplied to
  # this one command only: `write` without M207_S07_WRITE_BATTERY=1 is refused by the assembler
  # itself (AUTHORITY_CLAIM), and the read-only confirmation below still runs with a clean
  # environment.
  if ! M207_S07_WRITE_BATTERY=1 uv run python "$BATTERY_PY" "$results" "$BATTERY" write "$new_classification" >"$stage_log" 2>&1; then
    sed 's/^/    /' "$stage_log"
    printf '%s\n' '[m207-s07] FAILED -- the authorized battery write failed' >&2
    exit "$FAIL_EXIT"
  fi
  sed 's/^/    /' "$stage_log"
fi

battery_status=0
if uv run python "$BATTERY_PY" "$results" "$BATTERY" read "$new_classification" >"$stage_log" 2>&1; then
  battery_status=0
else
  battery_status=$?
fi
if [ "$battery_status" -ne 0 ]; then
  sed 's/^/    /' "$stage_log"
  printf '%s\n' '[m207-s07] FAILED -- the tracked battery is stale or malformed; regenerate once with M207_S07_WRITE_BATTERY=1 before host verification' >&2
  exit "$FAIL_EXIT"
fi
if ! grep -q '^M207_S07_BATTERY_OK ' "$stage_log"; then
  printf '%s\n' '[m207-s07] FAILED -- the battery assembler exited 0 without printing M207_S07_BATTERY_OK' >&2
  exit "$FAIL_EXIT"
fi
sed 's/^/    /' "$stage_log"

# --------------------------------------------------------------------------- #
# 4. The integrity marker.  Printed last, and only after every row and pin above
#    passed and the tracked battery was confirmed current.
# --------------------------------------------------------------------------- #
printf '%s\n' \
  '[m207-s07] the successor attempt stays a classification, not a verdict: the frozen S04/M204 receipts keep claims.operational_acceptance=non-pass and promotion stays none with classification=not-authorized'
printf '%s\n' \
  '[m207-s07] M207_S07_VERIFY_OK means the S07 integrity/policy chain ran and every row and pin passed: not a C4 pass, not operational acceptance, not a promotion, not gold and not an independently measured rate'
printf '%s\n' "$MARKER"
