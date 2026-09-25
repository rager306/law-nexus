// M210-3afp79 S04 T05 slice battery contract.
//
// Offline and fail-closed. The artifact under test is the S04 slice battery
// (scripts/m210_s04_slice_battery.mjs): it must run the four S04 enforcement
// contracts (the admission reconciliation, the 19-finding evidence matrix, the
// review cards and the review session contract) and the five regression gates
// (the S01 packet battery, the S02 adoption battery, the S03 slice battery, the
// M209/S04 battery verify mode with the frozen M201/M202 zero-delta guard, and
// the live engine source revision) with a clean aggregate total, and it must
// fail closed when any contract is failed, crashed, missing or substituted,
// when the aggregate check total is zeroed or falls below the floor, or when a
// regression gate is red or absent.
//
// This contract also asserts the S04 stopping-condition guards directly on the
// package: the admission reconciliation's guard fields stay unasserted
// (crates_touched=[], requirements_promoted=0, review_case_events_written=0),
// prd/temporal-legal-model.md stays byte-identical to its pin, the RC28 final
// check carries exactly one `rc28: hold` verdict whose hold basis is the
// absence of valid per-finding dispositions (never an absence of variant C
// adoption), the 19 machine-verdict rows match the live T02 matrix, no S04 data
// artifact claims crates/, every S04 JSON data artifact is ASCII and free of
// Rust runtime markers, and the declared absent Review Case events directory is
// still absent.
//
// Subprocesses are limited to `node scripts/m210_s04_slice_battery.mjs` (which
// drives the upstream contracts and the regression gates), `node --test` on this
// file's own path, and read-only `git ls-files`. No network, no dependency
// install, no git mutation, no `.gsd` / ignored / absolute path is read as
// evidence, and this contract writes only ephemeral mutated copies under the OS
// temp directory (outside the repository), which it removes again.
//
// Run: node --test scripts/m210_s04_slice_battery_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { test } from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

import {
  BATTERY_CHECKPOINT_MARKER,
  BATTERY_FAILED_MARKER,
  BATTERY_MARKER,
  CONTRACTS,
  CONTRACT_MARKERS,
  CRATES_ROOT,
  EVENTS_DIR,
  FORBIDDEN_PRIOR_DEFER_LITERAL,
  MIN_CHECKS,
  RC28_COUNT_KEYS,
  RC28_EXACT_MATCH_VERDICT,
  RC28_FINAL_CHECK,
  RC28_MATRIX,
  RC28_PACKET_FILE,
  RC28_SOURCE_DOCUMENT,
  RC28_VERDICT_PATTERN,
  REGRESSIONS,
  REPO_ROOT,
  S04_DATA_ARTIFACTS,
  S04_ENFORCEMENT_DIR,
  S04_ENFORCEMENT_PREFIX,
  S04_TRACKED_MARKDOWN_ARTIFACTS,
  S04_PACKAGE_ARTIFACTS,
  TEMPORAL_LEGAL_MODEL,
  TEMPORAL_LEGAL_MODEL_PIN,
  deriveRc28Counts,
  observeRc28Checkpoint,
  parseCheckpointHeader,
  parseCheckpointVerdicts,
  runBattery,
  validateBattery,
  validateRc28Checkpoint,
} from "./m210_s04_slice_battery.mjs";

const root = REPO_ROOT;
const BATTERY = "scripts/m210_s04_slice_battery.mjs";
const SELF = "scripts/m210_s04_slice_battery_contract.test.mjs";
const ADMISSION_REL = "prd/architecture/m210-s04-admission-reconciliation.json";
const MATRIX_REL = "prd/architecture/m210-s04-finding-evidence-matrix.json";
const ARTIFACT_MIN = 8;

// Rust-implementation markers, assembled from fragments at runtime so this
// contract does not itself contain the literals it refuses in the S04 package.
const RUNTIME_MARKERS = [
  ["pub", "fn"].join(" "),
  ["pub", "struct"].join(" "),
  ["impl", ""].join(" "),
];

// The forbidden hold rationale, assembled from fragments for the same reason:
// the hold must never be justified by an absence of variant C adoption.
const FORBIDDEN_HOLD_RATIONALE = ["rc28_hold_justified_by_", "missing_acceptance"].join("");

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
// checkpoint_failed: the final RC28 checkpoint's own semantics are invalid.
// DOCUMENTED_CODES_END

// The complete fail-closed code set of the checkpoint validator
// (`validateRc28Checkpoint`), mirrored independently here and asserted equal to
// the set documented in the battery module. Every code is asserted to be
// empirically emitted by a mutation.
// CHECKPOINT_CODES_BEGIN
// checkpoint_missing: the observation or one of its required parts is unusable.
// verdict_invalid: the checkpoint does not carry exactly one hold verdict.
// count_conflation: a count kind is missing, so the kinds are collapsed.
// counts_drift: a declared count disagrees with the live T02 rows.
// matrix_summary_drift: the live T02 summary disagrees with the rows it summarises.
// digest_namespace_confused: a digest is mislabelled, swapped or not bound to its live bytes.
// prior_owner_defer_denied: the established prior F13 owner defer is denied or read as absent.
// prior_decision_ledger_confused: the prior owner decision and the current RC28 ledger are conflated.
// hold_basis_invalid: the hold rests on something other than the missing dispositions.
// CHECKPOINT_CODES_END

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
const CHECKPOINT_DOCUMENTED_CODES = parseDocumentedCodes(
  SELF_SOURCE,
  "CHECKPOINT_CODES_BEGIN",
  "CHECKPOINT_CODES_END",
);
const BATTERY_CHECKPOINT_DOCUMENTED_CODES = parseDocumentedCodes(
  BATTERY_SOURCE,
  "CHECKPOINT_CODES_BEGIN",
  "CHECKPOINT_CODES_END",
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

// The checkpoint's bold single-line header fields (`**key:** value`). The rc28
// verdict has the colon inside the bold span and is read separately. Keys may
// carry digits (`f01_f15`).
function headerFields(md) {
  const fields = {};
  for (const line of md.split("\n")) {
    const match = line.match(/^\*\*([a-z0-9_]+):\*\*\s*(.*)$/);
    if (match) fields[match[1]] = match[2].trim();
  }
  return fields;
}

function rc28Verdicts(md) {
  return [...md.matchAll(/^\*\*rc28: (hold|closed)\*\*$/gm)].map((match) => match[1]);
}

function isAscii(text) {
  return !/[^\x00-\x7F]/.test(text);
}

// Parses the 19-row machine-verdict table from the final check. The header rows
// do not carry an RC28-F## finding id, so only real data rows match.
function findingRows(md) {
  const rows = [];
  const re = /^\|\s*(RC28-F\d{2})\s*\|\s*([a-z]+)\s*\|\s*([a-z_]+)\s*\|$/gm;
  for (const match of md.matchAll(re)) {
    rows.push({ finding_id: match[1], proof_class: match[2], machine_verdict: match[3] });
  }
  return rows;
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
  const dir = mkdtempSync(path.join(tmpdir(), "m210-s04-battery-"));
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
  substitutedContract.results[3].contract = "scripts/m210_s04_bogus_contract.test.mjs";

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

  // The final RC28 checkpoint is part of the battery's own fail-closed surface:
  // any invalid checkpoint code refuses the whole run.
  const failedCheckpoint = clone(good);
  failedCheckpoint.checkpoint = ["counts_drift"];

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
    { code: "checkpoint_failed", result: failedCheckpoint },
  ];
}

// Every checkpoint semantics refusal the contract exercises. Kept in one place
// so the negative cases and the empirical code-coverage case share the set. An
// observation is cloned, one field is mutated, and the validator must refuse it.
function checkpointMutations(observation) {
  const verdictInvalid = clone(observation);
  verdictInvalid.verdicts = ["closed"];

  const countConflation = clone(observation);
  delete countConflation.fields.rereverified_rows;

  const countsDrift = clone(observation);
  countsDrift.fields.rereverified_rows = "13";
  countsDrift.fields.exact_class_matched_verdict_rows = "13";

  const summaryDrift = clone(observation);
  summaryDrift.summary = { ...summaryDrift.summary, class_matched_rows: 99 };

  const digestSwap = clone(observation);
  digestSwap.digest.packet_file_sha256 = observation.digest.source_content_sha256;

  const priorDenied = clone(observation);
  priorDenied.fields.f13_prior_owner_decision = FORBIDDEN_PRIOR_DEFER_LITERAL;

  const ledgerConfused = clone(observation);
  ledgerConfused.fields.f13_current_rc28_disposition = "deferred-explicit owner defer";

  const holdBasis = clone(observation);
  holdBasis.fields.hold_basis = "missing variant C adoption";

  return [
    { code: "verdict_invalid", observation: verdictInvalid },
    { code: "count_conflation", observation: countConflation },
    { code: "counts_drift", observation: countsDrift },
    { code: "matrix_summary_drift", observation: summaryDrift },
    { code: "digest_namespace_confused", observation: digestSwap },
    { code: "prior_owner_defer_denied", observation: priorDenied },
    { code: "prior_decision_ledger_confused", observation: ledgerConfused },
    { code: "hold_basis_invalid", observation: holdBasis },
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

contract("the battery runs every S04 contract and the regression gates with a clean total", () => {
  const spawned = batteryOutput();
  assert.equal(spawned.status, 0, `the battery must exit 0:\n${spawned.text.slice(-4000)}`);
  const checks = assertCleanBatteryOutput(spawned.text);
  assert.ok(checks >= MIN_CHECKS, "the aggregate total must be at or above the floor");

  // The nested regression markers must be present verbatim, and the M209/S04
  // marker must carry drift=0 with the frozen paths unchanged.
  assert.match(spawned.text, /^M210_S01_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M210_S02_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M210_S03_BATTERY_OK checks=\d+ failed=0$/m);
  assert.match(spawned.text, /^M209_S04_BATTERY_OK .*frozen_paths_unchanged=1 .*drift=0$/m);
  assert.match(spawned.text, /^sha256:[0-9a-f]{64}$/m);
  assert.match(spawned.text, new RegExp(`^${BATTERY_CHECKPOINT_MARKER} ok codes=none$`, "m"));

  // Every contract prints its own marker only after all of its cases passed.
  for (const contractPath of CONTRACTS) {
    assert.ok(CONTRACT_MARKERS[contractPath], `${contractPath} must declare a marker pattern`);
    assert.match(spawned.text, CONTRACT_MARKERS[contractPath], `${contractPath} must print its marker`);
  }

  for (const contractPath of CONTRACTS) {
    const line = spawned.text.match(
      new RegExp(
        `^M210_S04_BATTERY_CONTRACT ${contractPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} pass=(\\d+) fail=(\\d+) exit=(\\d+)$`,
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
  assert.ok(byCode.get("checkpoint_failed").includes("checkpoint_failed"), "an invalid checkpoint must fail the battery");
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
  assert.throws(() => assertCleanBatteryOutput(real.replace(OK_LINE, "M210_S04_BATTERY_OK checks=0 failed=0")));
  assert.throws(() =>
    assertCleanBatteryOutput(real.replace(OK_LINE, `M210_S04_BATTERY_OK checks=${MIN_CHECKS - 1} failed=0`)),
  );
  assert.throws(() => assertCleanBatteryOutput(`${real}\n${BATTERY_FAILED_MARKER} failed=1\n`));
});

contract("negative: mutated copies of the battery fail closed on a raised floor and a dropped contract", async () => {
  const good = batteryRun();
  assert.deepEqual(validateBattery(good), []);

  const raised = mutatedBatteryModule((source) =>
    source.replace(`export const MIN_CHECKS = ${MIN_CHECKS};`, "export const MIN_CHECKS = 100000;"),
  );
  const dropped = mutatedBatteryModule((source) => source.replace(`  "${CONTRACTS[0]}",\n`, ""));
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
  process.stdout.write("M210_S04_MUTATED_BATTERY_FAIL_CLOSED_OK\n");
});

// ---------------------------------------------------------------------------
// the RC28 final check checkpoint
// ---------------------------------------------------------------------------

contract("the RC28 final check carries exactly one hold verdict with a correct basis and zero dispositions", () => {
  assert.ok(existsSync(path.join(root, RC28_FINAL_CHECK)), `${RC28_FINAL_CHECK} must exist`);
  assert.ok(!RC28_FINAL_CHECK.startsWith(CRATES_ROOT), `${RC28_FINAL_CHECK} must not claim ${CRATES_ROOT}`);
  const md = readText(RC28_FINAL_CHECK);
  assert.ok(isAscii(md), `${RC28_FINAL_CHECK} must stay ASCII-only`);

  const verdicts = rc28Verdicts(md);
  assert.equal(verdicts.length, 1, "exactly one rc28 verdict line must exist");
  assert.equal(verdicts[0], "hold", "the verdict must be hold while no valid disposition exists");
  assert.match(md, RC28_VERDICT_PATTERN);

  const fields = headerFields(md);
  // The independent parser in the battery module must agree with the local one.
  assert.deepEqual(parseCheckpointHeader(md), fields, "the checkpoint header parsers must agree");
  assert.deepEqual(parseCheckpointVerdicts(md), verdicts, "the checkpoint verdict parsers must agree");

  assert.equal(fields.packet_id, "RC-2026-09-10-001", "the packet id must be bound");
  assert.equal(fields.source_path, RC28_SOURCE_DOCUMENT, "the source document path must be named");
  assert.equal(fields.packet_file_path, RC28_PACKET_FILE, "the packet file path must be named");
  assert.match(fields.source_content_sha256 || "", /^sha256:[0-9a-f]{64}$/, "the source digest must be a sha256");
  assert.match(fields.packet_file_sha256 || "", /^sha256:[0-9a-f]{64}$/, "the packet file digest must be a sha256");
  assert.match(
    fields.packet_declared_content_sha256 || "",
    /^sha256:[0-9a-f]{64}$/,
    "the packet-declared content digest must be a sha256",
  );
  assert.ok(
    !Object.prototype.hasOwnProperty.call(fields, "packet_content_sha256"),
    "the checkpoint must not label a digest with the bare packet_content_sha256 name",
  );
  assert.match(fields.reviewed_git_revision || "", /^[0-9a-f]{40}$/, "the reviewed revision must be git40");
  assert.equal(fields.findings_total, "19", "the findings total must be 19");
  assert.equal(fields.rereverified_rows, "4", "4 rows must be marked re-verified");
  assert.equal(fields.class_match_compatibility_rows, "13", "13 rows must carry a true compatibility flag");
  assert.equal(fields.class_mismatch_rows, "6", "6 rows must carry a false compatibility flag");
  assert.equal(fields.exact_class_matched_verdict_rows, "2", "exactly 2 rows must carry the exact class-matched verdict");
  assert.equal(fields.dispositions_recorded, "0", "no disposition may be recorded");
  assert.equal(fields.review_case_events_written, "0", "no Review Case event may be written");
  assert.equal(fields.human_session_run, "false", "no human session may have run");
  assert.match(fields.submission_path || "", /actor_bound_path_available false/, "the submission path must stay unavailable");
  assert.equal(fields.hold_basis, "valid per-finding dispositions absent", "the hold basis must be the missing dispositions");
  assert.match(fields.adoption_basis || "", /variant C established/, "the adoption basis must record the established variant C");
  assert.equal(fields.f01_f15, "residual_d519_not_proof", "F01/F15 must stay a D519 residual, not proof");
  assert.match(fields.f13_prior_owner_decision || "", /deferred-explicit/, "the prior F13 owner defer must stay explicit");
  assert.match(fields.f13_prior_owner_decision || "", /s02/i, "the prior F13 owner defer must stay namespaced to S02");
  assert.match(fields.f13_current_rc28_disposition || "", /none recorded/, "the current RC28 F13 slot must stay empty");
  assert.match(fields.f13_current_rc28_disposition || "", /rc28/i, "the current F13 slot must stay namespaced to RC28");
  assert.match(fields.f18 || "", /bounded_adoption_evidence_present/, "F18 must record the bounded adoption evidence");
  assert.match(fields.f18 || "", /independent_evaluation pending/, "F18 must keep the independent evaluation pending");
  assert.match(fields.f19 || "", /machine_class_match_done/, "F19 must record the machine class match");
  assert.match(fields.f19 || "", /human_sufficiency_pending/, "F19 must keep the human sufficiency pending");
  assert.ok((fields.resume_condition || "").length > 0, "the resume condition must be named");
  assert.equal(fields.contract, SELF, "the checkpoint must name this contract");

  // The hold is a sanctioned fail-closed outcome, and the established adoption
  // of variant C neither closes RC28 nor justifies the hold.
  assert.match(md, /sanctioned fail-closed outcome/, "the hold must be named a sanctioned fail-closed outcome");
  assert.match(md, /does not close RC28/, "the adoption must not read as closing RC28");

  // The reviewer suggestion "no owner defer recorded" is a namespace confusion:
  // the prior S02 owner defer exists, and only the current RC28 slot is empty.
  assert.ok(!md.includes(FORBIDDEN_PRIOR_DEFER_LITERAL), "the checkpoint must not deny the prior owner defer");
  assert.match(md, /prior owner decision/, "the checkpoint must name the prior owner decision namespace");
  assert.match(md, /current RC28 ledger/, "the checkpoint must name the current RC28 ledger namespace");

  for (const section of [
    "Findings machine verdicts",
    "Count semantics",
    "Digest namespaces",
    "Prior owner decision and current RC28 ledger",
    "Human sufficiency",
    "Non-claims",
    "Fail-closed boundary",
    "Resume condition",
  ]) {
    assert.match(md, new RegExp(`^## ${section}$`, "m"), `the ${section} section must be present`);
  }

  // The whole observation must validate cleanly against the live inputs.
  assert.deepEqual(validateRc28Checkpoint(observeRc28Checkpoint(root)), []);
});

contract("the checkpoint counts and digest namespaces are derived live from the T02 matrix", () => {
  const md = readText(RC28_FINAL_CHECK);
  const fields = headerFields(md);
  const matrix = readJson(MATRIX_REL);
  const derived = deriveRc28Counts(matrix);

  // The four count kinds are derived from the live rows, not copied from prose.
  assert.equal(derived.findings_total, 19, "the T02 matrix must carry 19 rows");
  assert.equal(derived.rereverified_rows, 4, "4 rows must be re-verified in live T02");
  assert.equal(derived.class_match_compatibility_rows, 13, "13 live rows must carry a true compatibility flag");
  assert.equal(derived.class_mismatch_rows, 6, "6 live rows must carry a false compatibility flag");
  assert.equal(derived.exact_class_matched_verdict_rows, 2, "2 live rows must carry the exact verdict");

  // The three class counts are distinct kinds; none may stand in for another.
  assert.equal(
    new Set([
      derived.rereverified_rows,
      derived.class_match_compatibility_rows,
      derived.exact_class_matched_verdict_rows,
    ]).size,
    3,
    "the re-verified, compatibility and exact-verdict counts must be distinct kinds",
  );
  assert.notEqual(
    derived.class_match_compatibility_rows,
    derived.exact_class_matched_verdict_rows,
    "a compatibility flag must not stand in for a class-matched verdict",
  );

  for (const key of RC28_COUNT_KEYS) {
    assert.equal(Number(fields[key]), derived[key], `${key} must equal the live-derived count`);
  }
  assert.equal(Number(fields.findings_total), derived.findings_total, "findings_total must equal the live row count");

  // The T02 summary and the rows it summarises must agree.
  assert.equal(matrix.summary.finding_count, derived.findings_total);
  assert.equal(matrix.summary.rows_rereverified, derived.rereverified_rows);
  assert.equal(matrix.summary.class_matched_rows, derived.class_match_compatibility_rows);
  assert.equal(matrix.summary.class_mismatched_rows, derived.class_mismatch_rows);
  assert.equal(matrix.summary.machine_verdict_counts[RC28_EXACT_MATCH_VERDICT], derived.exact_class_matched_verdict_rows);

  // The digest namespaces are bound to their own live bytes and to each other.
  assert.equal(fields.source_content_sha256, liveSha256(RC28_SOURCE_DOCUMENT), "the source digest must bind the live source document");
  assert.equal(fields.packet_file_sha256, liveSha256(RC28_PACKET_FILE), "the packet file digest must bind the live packet file");
  assert.equal(
    fields.packet_declared_content_sha256,
    matrix.review_case.packet_declared_content_sha256,
    "the declared digest must bind the packet declaration",
  );
  assert.equal(
    fields.source_content_sha256,
    fields.packet_declared_content_sha256,
    "the packet-declared content digest is the source document digest",
  );
  assert.notEqual(fields.source_content_sha256, fields.packet_file_sha256, "the two digest namespaces must differ");

  // The prose must explain the compatibility flag and must not claim a
  // class-matched verdict on all 13 compatibility rows.
  assert.match(md, /compatibility flag/, "the checkpoint must explain the compatibility flag");
  assert.match(md, /neither a sufficiency claim nor evidence presence/, "compatibility must not read as sufficiency");
  assert.doesNotMatch(md, /class-matched verdict on 13/, "the checkpoint must not conflate compatibility with a verdict");

  assert.deepEqual(validateRc28Checkpoint(observeRc28Checkpoint(root)), []);
});

contract("negative: checkpoint count drift, conflation, digest swap and prior-defer denial fail closed", () => {
  const observation = observeRc28Checkpoint(root);
  assert.deepEqual(validateRc28Checkpoint(observation), []);

  const byCode = new Map(
    checkpointMutations(observation).map((mutation) => [mutation.code, validateRc28Checkpoint(mutation.observation)]),
  );
  for (const [code, codes] of byCode) {
    assert.ok(codes.includes(code), `${code} must be emitted; got ${JSON.stringify(codes)}`);
  }

  // The compatibility count and the exact-verdict count are distinct kinds: a
  // compatibility number in the exact-verdict slot must drift, not pass.
  const conflated = clone(observation);
  conflated.fields.exact_class_matched_verdict_rows = String(observation.derived.class_match_compatibility_rows);
  assert.ok(validateRc28Checkpoint(conflated).includes("counts_drift"), "a swapped count kind must drift");

  // A digest namespace swap is refused even when both values are valid sha256.
  const swapped = clone(observation);
  swapped.digest.packet_file_sha256 = observation.digest.source_content_sha256;
  const swappedCodes = validateRc28Checkpoint(swapped);
  assert.ok(swappedCodes.includes("digest_namespace_confused"), "a namespace swap must be refused");
  assert.ok(!swappedCodes.includes("counts_drift"), "a digest swap is not a count drift");

  // "no owner defer recorded" is the reviewer namespace confusion, refused.
  const denied = clone(observation);
  denied.fields.f13_prior_owner_decision = FORBIDDEN_PRIOR_DEFER_LITERAL;
  const deniedCodes = validateRc28Checkpoint(denied);
  assert.ok(deniedCodes.includes("prior_owner_defer_denied"), "denying the prior defer must be refused");
  assert.ok(
    !deniedCodes.includes("prior_decision_ledger_confused"),
    "denying the prior defer is not a ledger confusion",
  );

  // The prior defer read as the current RC28 disposition is a ledger confusion.
  const confused = clone(observation);
  confused.fields.f13_current_rc28_disposition = "deferred-explicit owner defer";
  const confusedCodes = validateRc28Checkpoint(confused);
  assert.ok(confusedCodes.includes("prior_decision_ledger_confused"), "a ledger confusion must be refused");
  assert.ok(
    !confusedCodes.includes("prior_owner_defer_denied"),
    "a ledger confusion is not a denial of the prior defer",
  );

  assert.deepEqual(validateRc28Checkpoint(null), ["checkpoint_missing"]);
  assert.deepEqual(validateRc28Checkpoint({}), ["checkpoint_missing"]);
});

contract("the 19 machine verdict rows in the final check match the live T02 matrix", () => {
  const md = readText(RC28_FINAL_CHECK);
  const rows = findingRows(md);
  assert.equal(rows.length, 19, "the final check must carry 19 finding rows");

  const matrix = readJson(MATRIX_REL);
  assert.equal(matrix.rows.length, 19, "the T02 matrix must carry 19 rows");
  const expected = new Map(
    matrix.rows.map((row) => [row.finding_id, { proof_class: row.required_proof_class, machine_verdict: row.machine_verdict }]),
  );

  const seen = new Set();
  for (const row of rows) {
    assert.ok(expected.has(row.finding_id), `${row.finding_id} must exist in the matrix`);
    assert.ok(!seen.has(row.finding_id), `${row.finding_id} must not be duplicated`);
    seen.add(row.finding_id);
    assert.equal(row.proof_class, expected.get(row.finding_id).proof_class, `${row.finding_id} proof class must match`);
    assert.equal(
      row.machine_verdict,
      expected.get(row.finding_id).machine_verdict,
      `${row.finding_id} machine verdict must match`,
    );
  }
  assert.equal(seen.size, 19, "all 19 findings must appear exactly once");
});

contract("the S04 guards stay unasserted and no S04 artifact claims crates", () => {
  const admission = readJson(ADMISSION_REL);
  assert.deepEqual(admission.guards.crates_touched, [], "the admission must touch no crate");
  assert.equal(admission.guards.requirements_promoted, 0, "the admission must promote no requirement");
  assert.equal(admission.guards.review_case_events_written, 0, "the admission must write no Review Case event");
  assert.equal(admission.guards.section3_pin, TEMPORAL_LEGAL_MODEL_PIN, "the admission must pin section 3");

  const matrix = readJson(MATRIX_REL);
  assert.equal(matrix.requirement_promotion, false, "the matrix must promote no requirement");
  assert.deepEqual(matrix.boundary.requirements_promoted, [], "no requirement may be promoted");
  assert.equal(matrix.boundary.requirement_status_mutated, false, "no requirement status may be mutated");
  assert.deepEqual(matrix.boundary.crates_touched, [], "the matrix must touch no crate");
  assert.equal(matrix.boundary.review_case_events_written, false, "the matrix must write no Review Case event");

  assert.ok(S04_PACKAGE_ARTIFACTS.length >= ARTIFACT_MIN, "the package must declare its artifacts");
  for (const rel of S04_PACKAGE_ARTIFACTS) {
    assert.ok(isTracked(rel), `${rel} must be git-tracked`);
    assert.ok(existsSync(path.join(root, rel)), `${rel} must exist`);
    assert.ok(!rel.startsWith(CRATES_ROOT), `${rel} must not claim ${CRATES_ROOT}`);
  }

  // No tracked crates/ file belongs to the S04 package.
  const tracked = spawnSync("git", ["ls-files", "--", CRATES_ROOT], { cwd: root, encoding: "utf8" });
  assert.equal(tracked.status, 0, "git ls-files -- crates/ must succeed");
  for (const rel of tracked.stdout.split("\n").filter((line) => line.length > 0)) {
    assert.ok(!/m210_s04/i.test(rel), `${rel} is an S04 package file under ${CRATES_ROOT}`);
  }
});

contract("section 3 stays byte-identical to its pin and the Review Case events directory stays absent", () => {
  assert.ok(isTracked(TEMPORAL_LEGAL_MODEL), `${TEMPORAL_LEGAL_MODEL} must be git-tracked`);
  assert.equal(liveSha256(TEMPORAL_LEGAL_MODEL), TEMPORAL_LEGAL_MODEL_PIN, "section 3 drifted from its pin");

  assert.ok(!existsSync(path.join(root, EVENTS_DIR)), `${EVENTS_DIR} must stay absent: no event was written`);

  // The forbidden hold rationale must appear nowhere in the S04 package.
  for (const rel of [...S04_PACKAGE_ARTIFACTS, RC28_FINAL_CHECK, BATTERY, SELF]) {
    assert.ok(!readText(rel).includes(FORBIDDEN_HOLD_RATIONALE), `${rel} carries the forbidden hold rationale`);
  }
});

contract("every S04 data artifact is ASCII and free of runtime markers", () => {
  assert.ok(S04_DATA_ARTIFACTS.length >= 6, "the data artifacts must be declared");
  for (const rel of S04_DATA_ARTIFACTS) {
    const text = readText(rel);
    assert.ok(isAscii(text), `${rel} must stay ASCII-only`);
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!text.includes(marker), `${rel} carries a runtime marker`);
    }
  }
  assert.ok(S04_TRACKED_MARKDOWN_ARTIFACTS.length >= 2, "the tracked markdown artifacts must be declared");
  for (const rel of [RC28_FINAL_CHECK, "prd/architecture/m210-s04-runtime-admission.md"]) {
    assert.ok(isAscii(readText(rel)), `${rel} must stay ASCII-only`);
  }
});

// Confinement rule for the S04 scripts: the scripts are the enforcement layer, so
// a script that names a Rust runtime marker must also declare the marker
// detection list, which proves the literal is a detection surface rather than a
// runtime claim.
contract("any S04 script runtime marker literal is a declared detection surface", () => {
  const scripts = readdirSync(path.join(root, S04_ENFORCEMENT_DIR))
    .filter((name) => name.startsWith(S04_ENFORCEMENT_PREFIX))
    .sort();
  assert.ok(scripts.length >= CONTRACTS.length + 1, "the S04 scripts must be present");
  let carriers = 0;
  for (const name of scripts) {
    const rel = `${S04_ENFORCEMENT_DIR}${name}`;
    const text = readText(rel);
    if (RUNTIME_MARKERS.some((marker) => text.includes(marker))) {
      carriers += 1;
      assert.ok(
        text.includes("RUNTIME_MARKERS"),
        `${rel} carries a runtime marker without a declared detection list`,
      );
    }
  }
  assert.ok(carriers > 0, "at least one S04 script must declare the detection surface it refuses");
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

contract("the checkpoint code block equals the battery's checkpoint documented set", () => {
  assert.deepEqual(
    CHECKPOINT_DOCUMENTED_CODES.slice().sort(),
    BATTERY_CHECKPOINT_DOCUMENTED_CODES.slice().sort(),
  );
  assert.equal(
    new Set(CHECKPOINT_DOCUMENTED_CODES).size,
    CHECKPOINT_DOCUMENTED_CODES.length,
    "a documented checkpoint code is duplicated",
  );
});

contract("every documented checkpoint fail-closed code is empirically exercised", () => {
  const emitted = new Set(validateRc28Checkpoint(null));
  for (const mutation of checkpointMutations(observeRc28Checkpoint(root))) {
    for (const code of validateRc28Checkpoint(mutation.observation)) emitted.add(code);
  }
  assert.deepEqual([...emitted].sort(), CHECKPOINT_DOCUMENTED_CODES.slice().sort());
});

// ---------------------------------------------------------------------------
// marker
// ---------------------------------------------------------------------------

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  const result = batteryRun();
  process.stdout.write(
    `M210_S04_SLICE_BATTERY_OK contracts=${CONTRACTS.length} regressions=${REGRESSIONS.length} ` +
      `checks=${result.checks} floor=${MIN_CHECKS} codes=${DOCUMENTED_CODES.length} ` +
      `artifacts=${S04_PACKAGE_ARTIFACTS.length} section3_pin=${TEMPORAL_LEGAL_MODEL_PIN.slice(7, 15)}\n`,
  );
});
