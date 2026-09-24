#!/usr/bin/env node
// M210-3afp79 S02 T06 slice battery.
//
// Sequentially runs the five S02 enforcement contracts (rebind, presentation,
// answer, governing, checkpoint) in dependency order, then the three regression
// gates that keep the surrounding proofs alive: the S01 packet battery
// (`node scripts/m210_s01_slice_battery.mjs`), the M209/S04 battery verify mode
// (`node scripts/m209_s04_slice_battery.mjs --verify`, which carries the frozen
// M201/M202 zero-delta guard and the R035/R070 proof-gate suites), and the live
// engine source revision (`node scripts/m204_s08_source_revision.mjs`, which
// must print a sha256:<64hex>).
//
// It prints one `M210_S02_BATTERY_CONTRACT <path> pass=N fail=N exit=M` line per
// contract, one `M210_S02_BATTERY_REGRESSION <id> exit=M checks=N marker=...`
// line per regression gate (followed by the gate's own marker line verbatim, so
// the nested markers are visible in the captured evidence), and one aggregate
// marker `M210_S02_BATTERY_OK checks=N failed=0`. On any failed, missing,
// substituted or under-floor contract, or any failed regression gate, it prints
// `M210_S02_BATTERY_FAILED failed=N` (N = failing steps plus 1 for an
// under-floor total, never 0) plus a `M210_S02_BATTERY_FAILED_CODES <codes>`
// line naming the refusal codes, then the tails of the failing steps under
// `M210_S02_BATTERY_TAIL <path>` (or, when no single step produced the tail, an
// `M210_S02_BATTERY_TAIL scripts/m210_s02_slice_battery.mjs` line carrying the
// floor and the observed totals), and exits 1, so a red run is diagnosable from
// the log alone rather than only from an exit code.
//
// Offline: no network, no dependency install, no git mutation. The battery only
// reads and spawns; it writes no file and edits no artifact.
//
// Run: node scripts/m210_s02_slice_battery.mjs
// This script never includes its own contract (`m210_s02_slice_battery_contract
// .test.mjs`), so there is no recursion: the battery contract drives this runner,
// and this runner drives the five upstream contracts and the three regressions.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const BATTERY_MARKER = "M210_S02_BATTERY_OK";
export const BATTERY_FAILED_MARKER = "M210_S02_BATTERY_FAILED";
export const BATTERY_TAIL_MARKER = "M210_S02_BATTERY_TAIL";
export const BATTERY_CONTRACT_MARKER = "M210_S02_BATTERY_CONTRACT";
export const BATTERY_REGRESSION_MARKER = "M210_S02_BATTERY_REGRESSION";

// The five S02 enforcement contracts, in dependency order (rebind feeds the
// presentation, which feeds the answer slot, which feeds the governing check,
// which feeds the checkpoint). The battery contract is deliberately absent: it
// drives this runner.
export const CONTRACTS = [
  "scripts/m210_s02_rebind_contract.test.mjs",
  "scripts/m210_s02_presentation_contract.test.mjs",
  "scripts/m210_s02_answer_contract.test.mjs",
  "scripts/m210_s02_governing_contract.test.mjs",
  "scripts/m210_s02_checkpoint_contract.test.mjs",
];

// The regression gates the S02 slice may not break. `marker` is matched against
// the combined stdout+stderr of the gate; `checks` is read from the marker so the
// nested batteries' own check totals are folded into this battery's aggregate
// (D554 shape: a nested battery that silently reports zero checks must not look
// green). `drift` requires a `drift=0` field when the marker declares one.
export const REGRESSIONS = [
  {
    id: "s01_slice_battery",
    script: "scripts/m210_s01_slice_battery.mjs",
    args: [],
    marker: /^M210_S01_BATTERY_OK checks=(\d+) failed=0$/m,
    describe: "the S01 packet battery (family register, IR alternatives, source-bound examples)",
  },
  {
    id: "m209_s04_slice_battery_verify",
    script: "scripts/m209_s04_slice_battery.mjs",
    args: ["--verify"],
    marker:
      /^M209_S04_BATTERY_OK checks=(\d+) failed=(\d+) mandatory=(\d+) frozen_paths_unchanged=(\d+) groups=(\d+) drift=(\d+)$/m,
    requireFields: { failed: 0, frozen_paths_unchanged: 1, drift: 0 },
    describe: "the M209/S04 battery verify mode (R035/R070 proof gates, frozen M201/M202 zero delta)",
  },
  {
    id: "source_revision",
    script: "scripts/m204_s08_source_revision.mjs",
    args: [],
    jsonShape: true,
    describe: "the live engine source revision (must be sha256:<64hex>)",
  },
];

// Check floor for a meaningful run: the three S02 regression-path batteries plus
// the five contracts would report 67 contract checks + 50 nested S01 checks +
// 36 nested M209/S04 checks + 1 source-revision assertion = 154 checks. The floor
// is 138, i.e. 90% of the observed total, the same ratio the S01 battery used
// (floor 45 of 50). It is a coarse backstop against a truncated or silently empty
// run - every individual contract and regression remains separately gated by its
// own exit code, marker and positive count, so no lost check can hide behind the
// floor.
export const MIN_CHECKS = 138;

export const SOURCE_REVISION_SCRIPT = "scripts/m204_s08_source_revision.mjs";

// This runner's own repository-relative path, used for the aggregate-only
// failure tail when no single step is red.
export const BATTERY_SELF = "scripts/m210_s02_slice_battery.mjs";

// The section 3 pin the S02 slice must leave untouched. It is asserted against
// the live file AND against the dictionary delta's declared pin, so a silent
// re-pin on both sides still fails closed.
export const TEMPORAL_LEGAL_MODEL = "prd/temporal-legal-model.md";
export const TEMPORAL_LEGAL_MODEL_PIN =
  "sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6";

// The S02 package's content artifacts plus its bounded generator. These are the
// files the slice produced; each must exist, stay outside crates/, stay ASCII and
// carry no Rust runtime marker. The enforcement contracts are not listed here:
// they must be allowed to name the very markers they refuse, so they are handled
// by confinement rules instead (see S02_ENFORCEMENT_DIR below).
export const S02_PACKAGE_ARTIFACTS = [
  "prd/architecture/m210-s02-rebind-report.json",
  "prd/architecture/m210-s02-owner-decision-packet.json",
  "prd/architecture/m210-s02-owner-decision-presentation.md",
  "prd/architecture/m210-s02-answer-record.json",
  "prd/architecture/m210-s02-governing-surface-check.json",
  "prd/architecture/m210-s02-adoption-checkpoint.md",
  "prd/architecture/m210-s02-dictionary-delta.json",
  "scripts/m210_s02_rebind.mjs",
];

export const S02_ENFORCEMENT_DIR = "scripts/";
export const S02_ENFORCEMENT_PREFIX = "m210_s02_";
export const CRATES_ROOT = "crates/";

const OUTPUT_TAIL_CHARS = 4000;

// Node's test runner marks each child test process with NODE_TEST_CONTEXT. A
// nested `node --test` runner that inherits it suppresses its reporter output:
// the run still exits 0 but prints no parseable counts, which would look green.
// Strip it for every child spawn so the counts are real and a silent run fails
// closed.
export function cleanTestEnv(env = process.env) {
  const cleaned = { ...env };
  delete cleaned.NODE_TEST_CONTEXT;
  return cleaned;
}

// node's spec reporter prints `i tests 14` / `i pass 14` / `i fail 0` (the info
// glyph), and the TAP reporter prints the same lines prefixed with `#`. Parse
// both so the battery is not tied to one reporter.
export function parseTestCounts(output) {
  const text = typeof output === "string" ? output : "";
  const read = (label) => {
    const re = new RegExp(`^[\\s]*(?:\\u2139|#)\\s*${label}\\s+(\\d+)\\s*$`, "gm");
    let last = null;
    for (const match of text.matchAll(re)) last = Number.parseInt(match[1], 10);
    return last;
  };
  return { tests: read("tests"), pass: read("pass"), fail: read("fail") };
}

function spawnStep(execPath, args, timeoutMs) {
  return spawnSync(execPath, args, {
    cwd: REPO_ROOT,
    encoding: "utf8",
    timeout: timeoutMs,
    maxBuffer: 64 * 1024 * 1024,
    env: cleanTestEnv(),
  });
}

function combine(spawned) {
  return `${(spawned && spawned.stdout) || ""}${(spawned && spawned.stderr) || ""}`;
}

function exitCodeOf(spawned) {
  return spawned && typeof spawned.status === "number" ? spawned.status : null;
}

// Validates one regression gate's combined output. Returns the parsed check
// count when the gate is green, or null when its marker is absent or its
// required fields do not hold.
export function evaluateRegression(gate, output, exitCode) {
  if (exitCode !== 0) return { checks: 0, markerOk: false, markerLine: null };
  const text = typeof output === "string" ? output : "";
  if (gate.jsonShape) {
    const match = text.match(/\{"ok":true,"source_revision":"(sha256:[0-9a-f]{64})"\}/);
    if (!match) return { checks: 0, markerOk: false, markerLine: null };
    return { checks: 1, markerOk: true, markerLine: match[1] };
  }
  const match = text.match(gate.marker);
  if (!match) return { checks: 0, markerOk: false, markerLine: null };
  const fields = { checks: Number.parseInt(match[1], 10) };
  for (const [index, name] of (gate.markerFieldNames || ["failed", "mandatory", "frozen_paths_unchanged", "groups", "drift"]).entries()) {
    if (match[index + 2] !== undefined) fields[name] = Number.parseInt(match[index + 2], 10);
  }
  if (!(fields.checks > 0)) return { checks: 0, markerOk: false, markerLine: null };
  for (const [name, expected] of Object.entries(gate.requireFields || {})) {
    if (fields[name] !== expected) return { checks: fields.checks, markerOk: false, markerLine: match[0] };
  }
  return { checks: fields.checks, markerOk: true, markerLine: match[0] };
}

export function runBattery(options = {}) {
  const execPath = options.execPath || process.execPath;
  const timeoutMs = options.timeoutMs ?? 300000;
  const results = [];
  for (const contract of CONTRACTS) {
    const absolute = path.join(REPO_ROOT, contract);
    if (!existsSync(absolute)) {
      results.push({ contract, missing: true, exitCode: null, signal: null, pass: 0, fail: 0, output: "" });
      continue;
    }
    const spawned = spawnStep(execPath, ["--test", absolute], timeoutMs);
    const output = combine(spawned);
    const counts = parseTestCounts(output);
    results.push({
      contract,
      missing: false,
      exitCode: exitCodeOf(spawned),
      signal: (spawned && spawned.signal) || null,
      pass: counts.pass || 0,
      fail: counts.fail || 0,
      output,
    });
  }

  const regressions = [];
  for (const gate of REGRESSIONS) {
    const absolute = path.join(REPO_ROOT, gate.script);
    if (!existsSync(absolute)) {
      regressions.push({ id: gate.id, script: gate.script, exitCode: null, checks: 0, markerOk: false, markerLine: null, output: "" });
      continue;
    }
    const spawned = spawnStep(execPath, [absolute, ...gate.args], timeoutMs);
    const output = combine(spawned);
    const exitCode = exitCodeOf(spawned);
    const evaluated = evaluateRegression(gate, output, exitCode);
    regressions.push({ id: gate.id, script: gate.script, exitCode, ...evaluated, output });
  }

  const contractChecks = results.reduce((sum, entry) => sum + entry.pass, 0);
  const regressionChecks = regressions.reduce((sum, entry) => sum + entry.checks, 0);
  const checks = contractChecks + regressionChecks;
  const failed =
    results.reduce((sum, entry) => sum + entry.fail, 0) +
    results.filter((entry) => entry.missing || entry.exitCode !== 0).length +
    regressions.filter((entry) => entry.exitCode !== 0 || entry.markerOk !== true).length;
  return { results, regressions, contractChecks, regressionChecks, checks, failed, ok: failed === 0 && checks >= MIN_CHECKS };
}

// Fail-closed validation of a battery result. Kept pure so the sibling contract
// can exercise it on mutated results. Returns a sorted, de-duplicated code set;
// an empty array means the battery is complete and green.
//
// Documented codes (asserted equal to the contract's documented set):
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
export function validateBattery(result) {
  const codes = new Set();
  if (!result || typeof result !== "object") return ["battery_failed"];
  if (!Array.isArray(result.results) || !Array.isArray(result.regressions)) return ["battery_failed"];
  if (result.results.length !== CONTRACTS.length) codes.add("contract_missing");
  for (const [index, entry] of result.results.entries()) {
    if (!entry || entry.missing === true || typeof entry.contract !== "string" || entry.contract.length === 0) {
      codes.add("contract_missing");
      continue;
    }
    if (CONTRACTS.indexOf(entry.contract) !== index) codes.add("contract_substituted");
    if (entry.exitCode !== 0) codes.add("contract_failed");
    if (entry.fail !== 0) codes.add("contract_failed");
    if (!(typeof entry.pass === "number" && entry.pass > 0)) codes.add("contract_counts_missing");
  }
  if (!(typeof result.checks === "number" && result.checks >= MIN_CHECKS)) codes.add("checks_below_floor");
  if (result.failed !== 0) codes.add("battery_failed");
  if (result.ok !== true) codes.add("battery_failed");
  if (result.regressions.length !== REGRESSIONS.length) codes.add("regression_missing");
  for (const gate of REGRESSIONS) {
    const entry = result.regressions.find((candidate) => candidate && candidate.id === gate.id);
    if (!entry) {
      codes.add("regression_missing");
      continue;
    }
    if (entry.exitCode !== 0) codes.add("regression_failed");
    if (entry.markerOk !== true) codes.add("regression_failed");
  }
  return [...codes].sort();
}

function tail(text) {
  const value = typeof text === "string" ? text : "";
  return value.length <= OUTPUT_TAIL_CHARS ? value : value.slice(value.length - OUTPUT_TAIL_CHARS);
}

// The number reported by the FAILED marker. It counts the failing steps and adds
// one for an under-floor aggregate, so a refused run never reports `failed=0`.
// The precise reason is always enumerated by the FAILED_CODES line.
function failedCount(result) {
  const underFloor = !(typeof result.checks === "number" && result.checks >= MIN_CHECKS);
  return Math.max(1, result.failed + (underFloor ? 1 : 0));
}

function main() {
  const result = runBattery();
  for (const entry of result.results) {
    const state = entry.missing ? "missing" : `exit=${entry.exitCode}`;
    process.stdout.write(
      `${BATTERY_CONTRACT_MARKER} ${entry.contract} pass=${entry.pass} fail=${entry.fail} ${state}\n`,
    );
  }
  for (const entry of result.regressions) {
    process.stdout.write(
      `${BATTERY_REGRESSION_MARKER} ${entry.id} exit=${entry.exitCode} checks=${entry.checks} ` +
        `marker=${entry.markerOk ? "ok" : "missing"}\n`,
    );
    if (entry.markerLine) process.stdout.write(`${entry.markerLine}\n`);
  }

  const codes = validateBattery(result);
  if (result.ok && codes.length === 0) {
    process.stdout.write(`${BATTERY_MARKER} checks=${result.checks} failed=${result.failed}\n`);
    process.exit(0);
  }

  process.stdout.write(`${BATTERY_FAILED_MARKER} failed=${failedCount(result)}\n`);
  process.stdout.write(`M210_S02_BATTERY_FAILED_CODES ${codes.join(",")}\n`);
  let tailed = false;
  for (const entry of result.results) {
    if (entry.missing || entry.exitCode !== 0 || entry.fail !== 0) {
      process.stdout.write(`${BATTERY_TAIL_MARKER} ${entry.contract}\n`);
      process.stdout.write(`${tail(entry.output)}\n`);
      tailed = true;
    }
  }
  for (const entry of result.regressions) {
    if (entry.exitCode !== 0 || entry.markerOk !== true) {
      process.stdout.write(`${BATTERY_TAIL_MARKER} ${entry.script}\n`);
      process.stdout.write(`${tail(entry.output)}\n`);
      tailed = true;
    }
  }
  if (!tailed) {
    // No single step is red, yet the battery is refused: the cause is the
    // aggregate (an under-floor total). Its tail is the arithmetic itself, so a
    // `M210_S02_BATTERY_TAIL` line is still emitted and the failure stays
    // diagnosable without re-running the battery by hand.
    process.stdout.write(`${BATTERY_TAIL_MARKER} ${BATTERY_SELF}\n`);
    process.stdout.write(
      `floor=${MIN_CHECKS} checks=${result.checks} contract_checks=${result.contractChecks} ` +
        `regression_checks=${result.regressionChecks} failed_steps=${result.failed}\n`,
    );
  }
  process.exit(1);
}

const invokedDirectly =
  typeof process.argv[1] === "string" && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main();
}
