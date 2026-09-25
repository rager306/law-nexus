// M210-3afp79 S03 T05 slice battery contract.
//
// Offline and fail-closed. The artifact under test is the S03 slice battery
// (scripts/m210_s03_slice_battery.mjs): it must run the five S03 enforcement
// contracts (the v2 adoption contract, the start gate, the bounded semantics
// contract, the abstention diagnostic and the activation delta) and the four
// regression gates (the S01 packet battery, the S02
// adoption battery, the M209/S04 battery verify mode with the frozen M201/M202
// zero-delta guard, and the live engine source revision) with a clean aggregate
// total, and it must fail closed when any contract is failed, crashed, missing or
// substituted, when the aggregate check total is zeroed or falls below the floor,
// or when a regression gate is red or absent.
//
// This contract also asserts the S03 stopping-condition guards directly on the
// package: the start gate's guard fields stay unasserted (crates_touched=[],
// requirements_promoted=0, review_case_events_written=0, semantics_adopted=false),
// prd/temporal-legal-model.md stays byte-identical to its pin while the runtime
// activation delta stays applied:false, the admission checkpoint records the
// bounded granted v2 verdict with execution still separated, no S03 data artifact claims crates/, every S03 data
// artifact is ASCII-only and free of Rust runtime markers, and every declared
// absent runtime surface is still absent.
//
// Subprocesses are limited to `node scripts/m210_s03_slice_battery.mjs` (which
// drives the upstream contracts and the regression gates), `node --test` on this
// file's own path, and read-only `git ls-files`. No network, no dependency
// install, no git mutation, no `.gsd` / ignored / absolute path is read as
// evidence, and this contract writes only ephemeral mutated copies under the OS
// temp directory (outside the repository), which it removes again.
//
// Run: node --test scripts/m210_s03_slice_battery_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { test } from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

import {
  BATTERY_FAILED_MARKER,
  BATTERY_MARKER,
  CONTRACTS,
  CONTRACT_MARKERS,
  CRATES_ROOT,
  MIN_CHECKS,
  REGRESSIONS,
  REPO_ROOT,
  S03_ENFORCEMENT_DIR,
  S03_ENFORCEMENT_PREFIX,
  S03_PACKAGE_ARTIFACTS,
  TEMPORAL_LEGAL_MODEL,
  TEMPORAL_LEGAL_MODEL_PIN,
  runBattery,
  validateBattery,
} from "./m210_s03_slice_battery.mjs";

const root = REPO_ROOT;
const BATTERY = "scripts/m210_s03_slice_battery.mjs";
const SELF = "scripts/m210_s03_slice_battery_contract.test.mjs";
const START_GATE_REL = "prd/architecture/m210-s03-start-gate.json";
const ADMISSION_REL = "prd/architecture/m210-s03-runtime-admission.md";
const ACTIVATION_REL = "prd/architecture/m210-s03-runtime-activation-delta.json";
const ARTIFACT_MIN = 6;

// Rust-implementation markers and the never-emitted verify marker, assembled from
// fragments at runtime so this contract does not itself contain the literals it
// refuses in the S03 package.
const RUNTIME_MARKERS = [
  ["pub", "fn"].join(" "),
  ["pub", "struct"].join(" "),
  ["impl", ""].join(" "),
];
const FORBIDDEN_VERIFY_MARKER = ["M210_S03_", "VERIFY", "_OK"].join("");

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
// Keys may carry digits (`section3_pin`).
function headerFields(md) {
  const fields = {};
  for (const line of md.split("\n")) {
    const match = line.match(/^\*\*([a-z0-9_]+):\*\*\s*(.*)$/);
    if (match) fields[match[1]] = match[2].trim();
  }
  return fields;
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
      timeout: 900000,
      maxBuffer: 64 * 1024 * 1024,
    });
    cachedOutput = {
      status: spawned.status,
      text: `${spawned.stdout || ""}${spawned.stderr || ""}`,
    };
  }
  return cachedOutput;
}

// A mutated copy of the battery module, written under the OS temp directory
// (outside the repository) and loaded as a separate module so its own constants
// - not the live ones - drive validateBattery. The caller removes the directory.
function mutatedBatteryModule(transform) {
  const mutated = transform(BATTERY_SOURCE);
  assert.notEqual(mutated, BATTERY_SOURCE, "a mutated battery copy must differ from the original source");
  const dir = mkdtempSync(path.join(tmpdir(), "m210-s03-battery-"));
  const file = path.join(dir, "slice_battery.mjs");
  writeFileSync(file, mutated, "utf8");
  return { dir, url: pathToFileURL(file).href };
}

// Every result-level mutation the contract refuses. Kept in one place so the
// negative cases and the empirical code-coverage case exercise the same set.
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
  substitutedContract.results[3].contract = "scripts/m210_s03_bogus_contract.test.mjs";

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

  // A contract that exits 0 and reports passing checks but never prints its own
  // OK marker (a truncated or suppressed run) must still fail closed.
  const markerlessContract = clone(good);
  markerlessContract.results[0].markerOk = false;

  return [
    { code: "contract_failed", result: failedContract },
    { code: "contract_failed", result: markerlessContract },
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
  test(name, async () => {
    try {
      await fn();
    } catch (error) {
      failures.push(name);
      throw error;
    }
  });
}

// ---------------------------------------------------------------------------
// the battery
// ---------------------------------------------------------------------------

contract("the battery runs every S03 contract and the regression gates with a clean total", () => {
  const spawned = batteryOutput();
  assert.equal(spawned.status, 0, `the battery must exit 0:\n${spawned.text.slice(-4000)}`);
  const checks = assertCleanBatteryOutput(spawned.text);
  assert.ok(checks >= MIN_CHECKS, "the aggregate total must be at or above the floor");

  // The nested regression markers must be present verbatim, and the M209/S04
  // marker must carry drift=0 with the frozen paths unchanged.
  assert.match(spawned.text, /^M210_S01_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M210_S02_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M209_S04_BATTERY_OK .*frozen_paths_unchanged=1 .*drift=0$/m);
  assert.match(spawned.text, /^sha256:[0-9a-f]{64}$/m);

  // The S03 v2 integration is proven by the adoption marker in the aggregate, and
  // every contract prints its own marker only after all of its cases passed.
  assert.match(spawned.text, /^M210_S03_ADOPTION_V2_OK /m, "the v2 adoption marker must appear in the aggregate");
  for (const contractPath of CONTRACTS) {
    assert.ok(CONTRACT_MARKERS[contractPath], `${contractPath} must declare a marker pattern`);
    assert.match(spawned.text, CONTRACT_MARKERS[contractPath], `${contractPath} must print its marker`);
  }

  for (const contractPath of CONTRACTS) {
    const line = spawned.text.match(
      new RegExp(
        `^M210_S03_BATTERY_CONTRACT ${contractPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} pass=(\\d+) fail=(\\d+) exit=(\\d+)$`,
        "m",
      ),
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
  assert.deepEqual(validateBattery(null), ["battery_failed"]);
  assert.deepEqual(validateBattery({}), ["battery_failed"]);
});

contract("negative: a zeroed total, a lowered floor boundary and a failing regression fail closed", () => {
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
  assert.throws(() => assertCleanBatteryOutput(real.replace(OK_LINE, "M210_S03_BATTERY_OK checks=0 failed=0")));
  assert.throws(() =>
    assertCleanBatteryOutput(real.replace(OK_LINE, `M210_S03_BATTERY_OK checks=${MIN_CHECKS - 1} failed=0`)),
  );
  assert.throws(() => assertCleanBatteryOutput(`${real}\n${BATTERY_FAILED_MARKER} failed=1\n`));
});

contract("negative: mutated copies of the battery fail closed on a raised floor and a dropped contract", async () => {
  const good = batteryRun();
  assert.deepEqual(validateBattery(good), []);

  const raised = mutatedBatteryModule((source) =>
    source.replace(`export const MIN_CHECKS = ${MIN_CHECKS};`, "export const MIN_CHECKS = 100000;"),
  );
  const dropped = mutatedBatteryModule((source) =>
    source.replace(`  "${CONTRACTS[0]}",\n`, ""),
  );
  try {
    const raisedModule = await import(raised.url);
    assert.ok(
      raisedModule.validateBattery(good).includes("checks_below_floor"),
      "a raised floor must refuse the unchanged aggregate",
    );
    const droppedModule = await import(dropped.url);
    const droppedCodes = droppedModule.validateBattery(good);
    assert.ok(droppedCodes.includes("contract_missing"), "a dropped contract must be refused");
    assert.ok(droppedCodes.includes("contract_substituted"), "a shifted contract position must be refused");
  } finally {
    rmSync(raised.dir, { recursive: true, force: true });
    rmSync(dropped.dir, { recursive: true, force: true });
  }
});

// ---------------------------------------------------------------------------
// the S03 stopping-condition guards
// ---------------------------------------------------------------------------

contract("the start gate guards stay unasserted and the checkpoint records the bounded v2 grant", () => {
  const gate = readJson(START_GATE_REL);
  assert.deepEqual(gate.guards.crates_touched, [], "the start gate must touch no crate");
  assert.equal(gate.guards.requirements_promoted, 0, "the start gate must promote no requirement");
  assert.equal(gate.guards.review_case_events_written, 0, "the start gate must write no Review Case event");
  assert.equal(gate.guards.semantics_adopted, false, "the start gate must adopt no normative semantics");
  assert.equal(gate.guards.section3_pin, TEMPORAL_LEGAL_MODEL_PIN, "the start gate must pin section 3");

  // v2 reality: the authenticated S02 v2 adoption is granted, bounded to the
  // adopted candidate layer, while execution stays not-started and unproven.
  assert.equal(gate.admission_verdict, "admission_granted", "the v2 gate must record the granted bounded adoption");
  assert.equal(gate.adoption_state.adoption_established, true, "the adoption must be established from v2");
  assert.equal(gate.adoption_state.adopted_variant, "C", "the adopted variant must be C");
  assert.ok(gate.adopted_construct_set.length > 0, "the adopted construct set must be non-empty");
  assert.deepEqual(
    gate.adopted_construct_set,
    gate.adoption_state.adopted_construct_set,
    "the adopted construct set must agree with the adoption state",
  );
  assert.equal(
    gate.owner_admission_ref,
    "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f",
    "the owner admission ref must be the authenticated subjective-UAT criterion",
  );
  assert.equal(gate.execution_state.executed, false, "adoption must not be execution");
  assert.equal(gate.execution_state.candidates_emitted, 0, "adoption alone emits no candidate");
  assert.equal(gate.runtime_implementation_permitted, true, "the bounded candidate layer is permitted");
  assert.equal(gate.runtime_demo, "not-proven", "runtime demo must stay unproven");
  assert.equal(gate.runtime_stop, "lifted_candidate_layer_only", "the stop lifts only for the candidate layer");
  assert.equal(gate.runtime_stop_scope.lifted_for, "adopted candidate layer", "the lift must be scoped");
  assert.ok(gate.runtime_stop_scope.still_active_for.length > 0, "the stop must stay active outside the layer");
  assert.equal(gate.runtime_work, "not-started", "runtime work must stay not-started");
  assert.ok(Array.isArray(gate.declared_absent_runtime_surfaces), "the absent surfaces must be declared");

  const md = readText(ADMISSION_REL);
  const fields = headerFields(md);
  assert.equal(fields.requirements_promoted, "0", "the checkpoint must promote no requirement");
  assert.equal(fields.review_case_events_written, "0", "the checkpoint must write no Review Case event");
  assert.equal(
    fields.owner_admission_ref,
    "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f",
    "the checkpoint must bind the authenticated owner ref",
  );
  assert.equal(fields.runtime_demo, "not-proven", "the checkpoint must record the unproven demo");
  assert.equal(fields.runtime_work, "not-started", "the checkpoint must record not-started work");
  assert.match(fields.runtime_stop || "", /candidate-layer/i, "the stop must be scoped to the candidate layer");
  const verdicts = admissionVerdicts(md);
  assert.equal(verdicts.length, 1, "exactly one admission verdict line must exist");
  assert.equal(verdicts[0], "granted", "the v2 verdict must be the bounded granted adoption");
});

contract("the section 3 pin is unchanged and the runtime activation delta stays unapplied", () => {
  assert.ok(isTracked(TEMPORAL_LEGAL_MODEL), `${TEMPORAL_LEGAL_MODEL} must be git-tracked`);
  assert.equal(liveSha256(TEMPORAL_LEGAL_MODEL), TEMPORAL_LEGAL_MODEL_PIN, "section 3 drifted from its pin");

  const delta = readJson(ACTIVATION_REL);
  // v2 reality: the bounded grant is recorded, yet the delta stays applied false
  // because the adopted layer is not implemented and the battery has not run.
  assert.equal(delta.gate.grant_recorded, true, "the bounded grant must be recorded");
  assert.equal(delta.gate.grant_scope, "candidate_layer_only", "the grant must stay scoped to the candidate layer");
  assert.equal(delta.gate.applied, false, "the activation delta must stay unapplied");
  assert.equal(delta.gate.grant_is_not_implementation, true, "the grant must not read as implementation");
  assert.equal(delta.gate.grant_is_not_readiness, true, "the grant must not read as readiness");
  assert.equal(delta.gate.implementation_present, false, "no implementation may be claimed");
  assert.equal(delta.gate.readiness, "not-ready", "readiness must not be fabricated");
  assert.equal(delta.gate.applied_requires_implementation, true, "application must require implementation");
  assert.equal(delta.gate.applied_requires_green_battery, true, "application must require a green battery");
  assert.equal(delta.stop.sanctioned, true, "the stop must be sanctioned");
  assert.equal(delta.stop.runtime_stop, "active_outside_candidate_layer", "the stop must stay active outside the layer");
  assert.equal(delta.stop.blanket_lifted, false, "the stop must not be blanket-lifted");
  assert.match(delta.stop.lifted_for || "", /candidate layer/i, "the lift must be scoped");
  assert.equal(delta.stop.runtime_demo, "not-proven", "the delta must keep the demo unproven");
  assert.equal(delta.stop.runtime_work, "not-started", "the delta must keep the work not-started");
});

contract("no S03 data artifact claims crates and every S03 data artifact is ASCII and marker-free", () => {
  assert.ok(S03_PACKAGE_ARTIFACTS.length >= ARTIFACT_MIN, "the package must declare its artifacts");
  for (const rel of S03_PACKAGE_ARTIFACTS) {
    assert.ok(isTracked(rel), `${rel} must be git-tracked`);
    assert.ok(existsSync(path.join(root, rel)), `${rel} must exist`);
    assert.ok(!rel.startsWith(CRATES_ROOT), `${rel} must not claim ${CRATES_ROOT}`);
    const text = readText(rel);
    assert.ok(isAscii(text), `${rel} must stay ASCII-only`);
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!text.includes(marker), `${rel} carries a runtime marker`);
    }
  }

  // No tracked crates/ file belongs to the S03 package.
  const tracked = spawnSync("git", ["ls-files", "--", CRATES_ROOT], { cwd: root, encoding: "utf8" });
  assert.equal(tracked.status, 0, "git ls-files -- crates/ must succeed");
  for (const rel of tracked.stdout.split("\n").filter((line) => line.length > 0)) {
    assert.ok(!/m210_s03/i.test(rel), `${rel} is an S03 package file under ${CRATES_ROOT}`);
  }
});

// Confinement rule for the S03 scripts: the scripts are the enforcement layer, so
// a script that names a Rust runtime marker must also declare the marker
// detection list, which proves the literal is a detection surface rather than a
// runtime claim. Every S03 script must stay ASCII.
contract("every S03 script is ASCII and any runtime marker literal is a declared detection surface", () => {
  const scripts = readdirSync(path.join(root, S03_ENFORCEMENT_DIR))
    .filter((name) => name.startsWith(S03_ENFORCEMENT_PREFIX))
    .sort();
  assert.ok(scripts.length >= CONTRACTS.length + 1, "the S03 scripts must be present");
  let carriers = 0;
  for (const name of scripts) {
    const rel = `${S03_ENFORCEMENT_DIR}${name}`;
    const text = readText(rel);
    assert.ok(isAscii(text), `${rel} must stay ASCII-only`);
    if (RUNTIME_MARKERS.some((marker) => text.includes(marker))) {
      carriers += 1;
      assert.ok(
        text.includes("RUNTIME_MARKERS"),
        `${rel} carries a runtime marker without a declared detection list`,
      );
    }
  }
  assert.ok(carriers > 0, "at least one S03 script must declare the detection surface it refuses");
});

contract("every declared absent runtime surface is still absent and the verify marker is never emitted", () => {
  const gate = readJson(START_GATE_REL);
  const absent = gate.declared_absent_runtime_surfaces;
  assert.ok(absent.length >= 5, "the five declared absent surfaces must be present");
  for (const rel of absent) {
    assert.ok(typeof rel === "string" && rel.length > 0, "a declared absent surface must be a path");
    assert.ok(!existsSync(path.join(root, rel)), `${rel} must stay absent`);
  }

  const files = [
    ...S03_PACKAGE_ARTIFACTS,
    ...readdirSync(path.join(root, S03_ENFORCEMENT_DIR))
      .filter((name) => name.startsWith(S03_ENFORCEMENT_PREFIX))
      .map((name) => `${S03_ENFORCEMENT_DIR}${name}`),
  ];
  for (const rel of files) {
    assert.ok(!readText(rel).includes(FORBIDDEN_VERIFY_MARKER), `${rel} must never emit the verify marker`);
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
    `M210_S03_SLICE_BATTERY_OK contracts=${CONTRACTS.length} regressions=${REGRESSIONS.length} ` +
      `checks=${result.checks} floor=${MIN_CHECKS} codes=${DOCUMENTED_CODES.length} ` +
      `artifacts=${S03_PACKAGE_ARTIFACTS.length} section3_pin=${TEMPORAL_LEGAL_MODEL_PIN.slice(7, 15)}\n`,
  );
});
