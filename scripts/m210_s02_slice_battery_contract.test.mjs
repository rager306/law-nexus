// M210-3afp79 S02 T06 slice battery contract.
//
// Offline and fail-closed. The artifact under test is the S02 slice battery
// (scripts/m210_s02_slice_battery.mjs): it must run the five S02 enforcement
// contracts and the three regression gates (the S01 packet battery, the M209/S04
// battery verify mode with the frozen M201/M202 zero-delta guard, and the live
// engine source revision) with a clean aggregate total, and it must fail closed
// when any contract is failed, crashed, missing or substituted, when the
// aggregate check total is zeroed or falls below the floor, or when a regression
// gate is red or absent.
//
// This contract also asserts the S02 stopping-condition guards directly on the
// package: the packet guard fields stay unasserted (requirements_promoted=0,
// review_case_events_written=0, crates_touched=[], semantics_adopted=false),
// prd/temporal-legal-model.md stays byte-identical to its pin while the dictionary
// delta stays applied:false, the checkpoint records the honest not-adopted verdict
// with F13 on hold, no S02 package file claims crates/, and every S02 package
// artifact is ASCII-only and free of Rust runtime markers.
//
// Subprocesses are limited to `node scripts/m210_s02_slice_battery.mjs` (which
// drives the upstream contracts and the regression gates), `node --test` on this
// file's own path, and read-only `git ls-files`. No network, no dependency
// install, no git mutation, no `.gsd` / ignored / absolute path is read as
// evidence, and this contract writes no file.
//
// Run: node --test scripts/m210_s02_slice_battery_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  BATTERY_FAILED_MARKER,
  BATTERY_MARKER,
  CONTRACTS,
  MIN_CHECKS,
  REGRESSIONS,
  REPO_ROOT,
  S02_ENFORCEMENT_DIR,
  S02_ENFORCEMENT_PREFIX,
  S02_PACKAGE_ARTIFACTS,
  TEMPORAL_LEGAL_MODEL,
  TEMPORAL_LEGAL_MODEL_PIN,
  runBattery,
  validateBattery,
} from "./m210_s02_slice_battery.mjs";

const root = REPO_ROOT;
const BATTERY = "scripts/m210_s02_slice_battery.mjs";
const SELF = "scripts/m210_s02_slice_battery_contract.test.mjs";
const CHECKPOINT_REL = "prd/architecture/m210-s02-adoption-checkpoint.md";
const ANSWER_REL = "prd/architecture/m210-s02-answer-record.json";
const PACKET_REL = "prd/architecture/m210-s02-owner-decision-packet.json";
const DELTA_REL = "prd/architecture/m210-s02-dictionary-delta.json";
const GOVERNING_REL = "prd/architecture/m210-s02-governing-surface-check.json";
const S01_INDEX_REL = "prd/architecture/m210-s01-packet-index.json";
const CRATES_ROOT = "crates/";
const ARTIFACT_MIN = 8;

// Rust-implementation markers, assembled at runtime so this contract does not
// itself contain the literals it refuses in every package file.
const RUNTIME_MARKERS = ["pub" + " fn", "pub" + " struct", "imp" + "l "];

// The battery's OK marker line, as printed by the runner.
const OK_LINE = new RegExp(`^${BATTERY_MARKER} checks=(\\d+) failed=0$`, "m");

// The complete fail-closed code set of the battery, mirrored independently here
// and asserted equal to the set documented in the battery module. The documented
// block below is machine-read and asserted equal to this list, and every code is
// asserted to be empirically emitted by a mutation.
// DOCUMENTED_CODES_BEGIN
// battery_failed: the aggregate flag is false, a step failed, or the result shape is unusable.
// checks_below_floor: the aggregate check total is below MIN_CHECKS.
// contract_missing: a declared contract is absent from disk or from the results.
// contract_substituted: a result entry is not the expected contract at its position.
// contract_failed: a contract exited non-zero or reported a failing check.
// contract_counts_missing: a contract reported no parseable passing checks.
// regression_missing: a required regression gate is absent from the results.
// regression_failed: a regression gate exited non-zero or its marker is absent or invalid.
// DOCUMENTED_CODES_END

const SELF_SOURCE = readFileSync(path.join(root, SELF), "utf8");
const BATTERY_SOURCE = readFileSync(path.join(root, BATTERY), "utf8");

function parseDocumentedCodes(source, begin, end) {
  const block = source.match(new RegExp(`${begin}\\r?\\n([\\s\\S]*?)\\r?\\n\\s*//\\s*${end}`));
  assert.ok(block, `the documented code block ${begin} must be present`);
  const codes = [];
  for (const line of block[1].split("\n")) {
    const match = line.match(/^\s*\/\/\s*([a-z][a-z0-9_]*):/);
    if (match) codes.push(match[1]);
  }
  return codes;
}

const DOCUMENTED_CODES = parseDocumentedCodes(SELF_SOURCE, "DOCUMENTED_CODES_BEGIN", "DOCUMENTED_CODES_END");
const BATTERY_DOCUMENTED_CODES = parseDocumentedCodes(
  BATTERY_SOURCE,
  "DOCUMENTED_CODES_BEGIN",
  "DOCUMENTED_CODES_END",
);

function readText(rel) {
  return readFileSync(path.join(root, rel), "utf8");
}

function readJson(rel) {
  return JSON.parse(readText(rel));
}

function liveSha256(rel) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, rel))).digest("hex")}`;
}

function isTracked(rel) {
  const spawned = spawnSync("git", ["ls-files", "--error-unmatch", "--", rel], { cwd: root, encoding: "utf8" });
  return spawned.status === 0;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// The checkpoint's bold single-line header fields (`**key:** value`). The
// admission verdict has the colon inside the bold span and is read separately.
// Keys may carry digits (`f13_status`).
function headerFields(md) {
  const fields = {};
  for (const line of md.split("\n")) {
    const match = line.match(/^\*\*([a-z0-9_]+):\*\*\s*(.*)$/);
    if (match) fields[match[1]] = match[2].trim();
  }
  return fields;
}

// The dictionary delta stores its section 3 pin as a bare 64-hex digest, while
// the engine and the packet use the `sha256:` form. Normalize before comparing so
// either lawful spelling is accepted but a different digest still fails closed.
function normalizeHash(value) {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value) ? value : `sha256:${value}`;
}

function admissionVerdicts(md) {
  return [...md.matchAll(/^\*\*admission: (granted|not-adopted)\*\*$/gm)].map((match) => match[1]);
}

function isAscii(text) {
  return !/[^\x00-\x7F]/.test(text);
}

// The output-level stopping condition: the OK marker with a total at or above
// the floor and no failure marker. Kept as a function so the negative cases can
// prove it refuses a zeroed total and a present failure marker.
function assertCleanBatteryOutput(output) {
  assert.ok(!output.includes(BATTERY_FAILED_MARKER), "a failure marker must never accompany a clean run");
  const marker = output.match(OK_LINE);
  assert.ok(marker, "the battery must print the OK marker");
  const checks = Number.parseInt(marker[1], 10);
  assert.ok(checks >= MIN_CHECKS, "the aggregate check total is below the floor");
  return checks;
}

let cachedRun = null;
function batteryRun() {
  if (cachedRun === null) cachedRun = runBattery();
  return cachedRun;
}

let cachedOutput = null;
function batteryOutput() {
  if (cachedOutput === null) {
    const spawned = spawnSync(process.execPath, [path.join(root, BATTERY)], {
      cwd: root,
      encoding: "utf8",
      timeout: 600000,
      maxBuffer: 64 * 1024 * 1024,
    });
    cachedOutput = {
      status: spawned.status,
      text: `${spawned.stdout || ""}${spawned.stderr || ""}`,
    };
  }
  return cachedOutput;
}

// Every mutation the contract refuses. Kept in one place so the negative cases
// and the empirical code-coverage case exercise the same set.
function mutations(good) {
  const failedContract = clone(good);
  failedContract.results[0].exitCode = 1;
  failedContract.results[0].fail = 1;

  const countsMissing = clone(good);
  countsMissing.results[1].pass = 0;

  const missingContract = clone(good);
  missingContract.results[2] = {
    contract: CONTRACTS[2],
    missing: true,
    exitCode: null,
    pass: 0,
    fail: 0,
    output: "",
  };

  const substitutedContract = clone(good);
  substitutedContract.results[3].contract = "scripts/m210_s02_bogus_contract.test.mjs";

  const truncatedContracts = clone(good);
  truncatedContracts.results = truncatedContracts.results.slice(1);

  const zeroedChecks = clone(good);
  zeroedChecks.checks = 0;

  const underFloor = clone(good);
  underFloor.checks = MIN_CHECKS - 1;

  const aggregateFailed = clone(good);
  aggregateFailed.ok = false;

  const countedFailed = clone(good);
  countedFailed.failed = 1;

  const failedRegression = clone(good);
  failedRegression.regressions[1].exitCode = 1;
  failedRegression.regressions[1].markerOk = false;

  const markerlessRegression = clone(good);
  markerlessRegression.regressions[0].markerOk = false;

  const missingRegression = clone(good);
  missingRegression.regressions = missingRegression.regressions.slice(1);

  return [
    { code: "contract_failed", result: failedContract },
    { code: "contract_counts_missing", result: countsMissing },
    { code: "contract_missing", result: missingContract },
    { code: "contract_substituted", result: substitutedContract },
    { code: "contract_missing", result: truncatedContracts },
    { code: "checks_below_floor", result: zeroedChecks },
    { code: "checks_below_floor", result: underFloor },
    { code: "battery_failed", result: aggregateFailed },
    { code: "battery_failed", result: countedFailed },
    { code: "regression_failed", result: failedRegression },
    { code: "regression_failed", result: markerlessRegression },
    { code: "regression_missing", result: missingRegression },
  ];
}

// node:test wrapper that records failures so the marker stays honest
const failures = [];
function contract(name, fn) {
  test(name, () => {
    try {
      fn();
    } catch (error) {
      failures.push(name);
      throw error;
    }
  });
}

// ---------------------------------------------------------------------------
// the battery
// ---------------------------------------------------------------------------

contract("the battery runs every S02 contract and the regression gates with a clean total", () => {
  const spawned = batteryOutput();
  assert.equal(spawned.status, 0, `the battery must exit 0:\n${spawned.text.slice(-4000)}`);
  const checks = assertCleanBatteryOutput(spawned.text);
  assert.ok(checks >= MIN_CHECKS, "the aggregate total must be at or above the floor");

  // The nested regression markers must be present verbatim, and the M209/S04
  // marker must carry drift=0 with the frozen paths unchanged.
  assert.match(spawned.text, /^M210_S01_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M209_S04_BATTERY_OK .*frozen_paths_unchanged=1 .*drift=0$/m);
  assert.match(spawned.text, /^sha256:[0-9a-f]{64}$/m);

  for (const contractPath of CONTRACTS) {
    const line = spawned.text.match(
      new RegExp(`^M210_S02_BATTERY_CONTRACT ${contractPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} pass=(\\d+) fail=(\\d+) exit=(\\d+)$`, "m"),
    );
    assert.ok(line, `${contractPath} must report a per-contract line`);
    assert.ok(Number.parseInt(line[1], 10) > 0, `${contractPath} must report passing checks`);
    assert.equal(Number.parseInt(line[2], 10), 0, `${contractPath} must report no failure`);
    assert.equal(Number.parseInt(line[3], 10), 0, `${contractPath} must exit 0`);
  }

  const result = batteryRun();
  assert.equal(result.ok, true);
  assert.equal(result.failed, 0);
  assert.ok(result.checks >= MIN_CHECKS);
  assert.equal(result.checks, checks, "the in-process total must equal the printed total");
  assert.equal(result.results.length, CONTRACTS.length);
  for (const entry of result.results) {
    assert.equal(entry.missing, false, `${entry.contract} must exist`);
    assert.equal(entry.exitCode, 0, `${entry.contract} must exit 0`);
    assert.ok(entry.pass > 0, `${entry.contract} must report checks`);
    assert.equal(entry.fail, 0, `${entry.contract} must report no failure`);
  }
  assert.equal(result.regressions.length, REGRESSIONS.length);
  for (const gate of REGRESSIONS) {
    const entry = result.regressions.find((candidate) => candidate.id === gate.id);
    assert.ok(entry, `${gate.id} must be recorded`);
    assert.equal(entry.exitCode, 0, `${gate.id} must exit 0`);
    assert.equal(entry.markerOk, true, `${gate.id} must print its marker`);
    assert.ok(entry.checks > 0, `${gate.id} must report checks`);
  }
  assert.deepEqual(validateBattery(result), []);
});

contract("negative: a failed, crashed, missing or substituted contract fails closed", () => {
  const good = batteryRun();
  assert.deepEqual(validateBattery(good), []);
  const byCode = new Map(mutations(good).map((mutation) => [mutation.code, validateBattery(mutation.result)]));
  assert.ok(byCode.get("contract_failed").includes("contract_failed"));
  assert.ok(byCode.get("contract_counts_missing").includes("contract_counts_missing"));
  assert.ok(byCode.get("contract_missing").includes("contract_missing"));
  assert.ok(byCode.get("contract_substituted").includes("contract_substituted"));
  assert.ok(byCode.get("contract_substituted").includes("contract_substituted"));
  assert.deepEqual(validateBattery(null), ["battery_failed"]);
  assert.deepEqual(validateBattery({}), ["battery_failed"]);
});

contract("negative: a zeroed total, a removed floor and a failing regression fail closed", () => {
  const good = batteryRun();
  const byCode = new Map(mutations(good).map((mutation) => [mutation.code, validateBattery(mutation.result)]));

  assert.ok(byCode.get("checks_below_floor").includes("checks_below_floor"), "a zeroed total must fail");
  assert.ok(byCode.get("battery_failed").includes("battery_failed"), "an aggregate failure must fail");
  assert.ok(byCode.get("regression_failed").includes("regression_failed"), "a red regression must fail");
  assert.ok(byCode.get("regression_missing").includes("regression_missing"), "a missing regression must fail");

  // The floor must be live: strictly below the observed total, strictly positive,
  // inclusive at the boundary, and refusing one check less.
  assert.ok(MIN_CHECKS > 0, "the floor must exist");
  assert.ok(MIN_CHECKS < good.checks, "the floor must sit below the observed total");
  const atFloor = clone(good);
  atFloor.checks = MIN_CHECKS;
  assert.ok(!validateBattery(atFloor).includes("checks_below_floor"));
  const belowFloor = clone(good);
  belowFloor.checks = MIN_CHECKS - 1;
  assert.ok(validateBattery(belowFloor).includes("checks_below_floor"));

  // Output-level stopping condition: the real output passes, a zeroed total and a
  // present failure marker are both refused.
  const real = batteryOutput().text;
  assert.equal(assertCleanBatteryOutput(real), good.checks);
  assert.throws(() => assertCleanBatteryOutput(real.replace(OK_LINE, "M210_S02_BATTERY_OK checks=0 failed=0")));
  assert.throws(() => assertCleanBatteryOutput(real.replace(OK_LINE, `M210_S02_BATTERY_OK checks=${MIN_CHECKS - 1} failed=0`)));
  assert.throws(() => assertCleanBatteryOutput(`${real}\n${BATTERY_FAILED_MARKER} failed=1\n`));
});

// ---------------------------------------------------------------------------
// the S02 stopping-condition guards
// ---------------------------------------------------------------------------

contract("the packet guard fields stay unasserted and cross-consistent", () => {
  const index = readJson(S01_INDEX_REL);
  assert.equal(index.guards.product_runtime_changed, false);
  assert.equal(index.guards.semantics_adopted, false);
  assert.equal(index.guards.review_case_events_written, 0);
  assert.equal(index.guards.requirements_promoted, 0);
  assert.deepEqual(index.guards.crates_touched, []);

  const packet = readJson(PACKET_REL);
  assert.equal(packet.semantics_adopted, false);
  assert.equal(packet.authoritative, false);
  assert.equal(packet.ascii_only, true);

  const answer = readJson(ANSWER_REL);
  assert.equal(answer.guards.review_case_events_written, 0, "the answer record must write no Review Case event");
  assert.equal(answer.guards.answer_treated_as_adoption, false);
  assert.equal(answer.guards.agent_selected, false);

  const checkpoint = readText(CHECKPOINT_REL);
  const fields = headerFields(checkpoint);
  assert.equal(fields.requirements_promoted, "0", "the checkpoint must promote no requirement");
  assert.equal(fields.review_case_events_written, "0", "the checkpoint must write no Review Case event");
});

contract("the section 3 pin is unchanged and the dictionary delta stays unapplied", () => {
  assert.ok(isTracked(TEMPORAL_LEGAL_MODEL), `${TEMPORAL_LEGAL_MODEL} must be git-tracked`);
  assert.equal(liveSha256(TEMPORAL_LEGAL_MODEL), TEMPORAL_LEGAL_MODEL_PIN, "section 3 drifted from its pin");

  const delta = readJson(DELTA_REL);
  assert.equal(delta.target_file, TEMPORAL_LEGAL_MODEL);
  assert.equal(
    normalizeHash(delta.target_file_sha256_pin),
    TEMPORAL_LEGAL_MODEL_PIN,
    "the delta re-pinned section 3",
  );
  assert.equal(delta.target_section, "section 3 Glossary and ownership");
  assert.equal(delta.gate.applied, false, "the delta must stay unapplied while the gate is not granted");
  assert.equal(delta.gate.applied_requires, "admission: granted");

  const checkpoint = readText(CHECKPOINT_REL);
  const verdicts = admissionVerdicts(checkpoint);
  assert.equal(verdicts.length, 1, "exactly one admission verdict line must exist");
  assert.equal(verdicts[0], "not-adopted", "no interactive answer exists, so the honest verdict is not-adopted");
  const fields = headerFields(checkpoint);
  assert.equal(fields.owner_admission_ref, "none");
  assert.equal(fields.interaction_ref, "none");
  assert.equal(fields.f13_status, "hold", "F13 must stay on hold without its own answer");
  assert.ok(
    /\(applied:false\)/.test(fields.dictionary_delta || ""),
    "the checkpoint must record the unapplied delta",
  );

  const governing = readJson(GOVERNING_REL);
  assert.equal(governing.verdict, "governing_surface_absent");

  const answer = readJson(ANSWER_REL);
  assert.equal(answer.status, "pending_human_decision");
  assert.equal(answer.answer_source, "none");
  assert.equal(answer.f13_status, "hold", "F13 must stay on hold without its own answer");
  assert.equal(answer.ir_answer.selected_option_id, null);
  assert.equal(answer.ir_answer.option_resolution, "unresolved");
});

contract("no S02 package artifact claims crates and the package is ASCII and marker-free", () => {
  assert.ok(S02_PACKAGE_ARTIFACTS.length >= ARTIFACT_MIN, "the package must declare its artifacts");
  for (const rel of S02_PACKAGE_ARTIFACTS) {
    assert.ok(existsSync(path.join(root, rel)), `${rel} must exist`);
    assert.ok(!rel.startsWith(CRATES_ROOT), `${rel} must not claim ${CRATES_ROOT}`);
    const text = readText(rel);
    assert.ok(isAscii(text), `${rel} must stay ASCII-only`);
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!text.includes(marker), `${rel} carries a runtime marker`);
    }
  }

  // No tracked crates/ file belongs to the S02 package.
  const tracked = spawnSync("git", ["ls-files", "--", CRATES_ROOT], { cwd: root, encoding: "utf8" });
  assert.equal(tracked.status, 0, "git ls-files -- crates/ must succeed");
  for (const rel of tracked.stdout.split("\n").filter((line) => line.length > 0)) {
    assert.ok(!/m210_s02/i.test(rel), `${rel} is an S02 package file under ${CRATES_ROOT}`);
  }

  // The enforcement contracts must be the only S02 scripts allowed to name the
  // markers they refuse or to carry a non-ASCII refusal fixture.
  const enforcement = readdirSync(path.join(root, S02_ENFORCEMENT_DIR)).filter((name) =>
    name.startsWith(S02_ENFORCEMENT_PREFIX),
  );
  assert.ok(enforcement.length >= CONTRACTS.length + 1, "the S02 scripts must be present");
  for (const name of enforcement) {
    const rel = `${S02_ENFORCEMENT_DIR}${name}`;
    const text = readText(rel);
    const isContract = /contract\.test\.mjs$/.test(name);
    if (!isAscii(text)) assert.ok(isContract, `${rel} carries non-ASCII bytes but is not an enforcement contract`);
    if (RUNTIME_MARKERS.some((marker) => text.includes(marker))) {
      assert.ok(isContract, `${rel} carries a runtime marker but is not an enforcement contract`);
    }
  }
});

// ---------------------------------------------------------------------------
// documented codes
// ---------------------------------------------------------------------------

contract("the documented code block equals the battery's documented set", () => {
  assert.deepEqual(DOCUMENTED_CODES.slice().sort(), BATTERY_DOCUMENTED_CODES.slice().sort());
  assert.equal(new Set(DOCUMENTED_CODES).size, DOCUMENTED_CODES.length, "a documented code is duplicated");
});

contract("every documented fail-closed code is empirically exercised", () => {
  const emitted = new Set();
  for (const mutation of mutations(batteryRun())) {
    for (const code of validateBattery(mutation.result)) emitted.add(code);
  }
  for (const code of validateBattery(null)) emitted.add(code);
  assert.deepEqual([...emitted].sort(), DOCUMENTED_CODES.slice().sort());
});

// ---------------------------------------------------------------------------
// marker
// ---------------------------------------------------------------------------

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  const result = batteryRun();
  process.stdout.write(
    `M210_S02_SLICE_BATTERY_OK contracts=${CONTRACTS.length} regressions=${REGRESSIONS.length} ` +
      `checks=${result.checks} floor=${MIN_CHECKS} codes=${DOCUMENTED_CODES.length} ` +
      `artifacts=${S02_PACKAGE_ARTIFACTS.length} section3_pin=${TEMPORAL_LEGAL_MODEL_PIN.slice(7, 15)}\n`,
  );
});
