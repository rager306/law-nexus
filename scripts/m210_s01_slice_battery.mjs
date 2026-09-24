#!/usr/bin/env node
// M210-3afp79 S01 T04 slice battery.
//
// Sequentially runs `node --test` over the three S01 enforcement contracts
// (family register, IR alternatives, source-bound examples), collects the
// per-contract counts, prints a per-contract line plus one aggregate marker,
// and exits non-zero if any contract fails, is missing, or reports zero
// checks. Offline: no network, no dependency install, no git mutation.
//
// The aggregate marker is `M210_S01_BATTERY_OK checks=N failed=0`. On any
// failure the script prints `M210_S01_BATTERY_FAILED failed=N` plus the tail of
// the failing contract output and exits 1, so the failure is observable in the
// captured evidence rather than only in an exit code.
//
// Run: node scripts/m210_s01_slice_battery.mjs
// This script never includes the battery contract itself, so there is no
// recursion: the battery contract spawns this runner, and this runner spawns
// the three upstream contracts only.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const BATTERY_MARKER = "M210_S01_BATTERY_OK";
export const BATTERY_FAILED_MARKER = "M210_S01_BATTERY_FAILED";

// The three S01 enforcement contracts, in dependency order. The battery
// contract is deliberately absent: it drives this runner.
export const CONTRACTS = [
  "scripts/m210_s01_family_register_contract.test.mjs",
  "scripts/m210_s01_ir_alternatives_contract.test.mjs",
  "scripts/m210_s01_examples_contract.test.mjs",
];

// Floor for a meaningful run: the three contracts currently report 50 passing
// checks in total. A total below the floor means the run was silently empty or
// truncated, which fails closed.
export const MIN_CHECKS = 45;

const OUTPUT_TAIL_CHARS = 4000;

// Node's test runner marks each child test process with NODE_TEST_CONTEXT. A
// contract spawned from inside `node --test` inherits it, and the nested runner
// then suppresses the reporter output: the run still exits 0 but prints no
// parseable counts, which would look green. Strip it for every contract spawn so
// the counts are real and a silent run fails closed.
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
    const spawned = spawnSync(execPath, ["--test", absolute], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      timeout: timeoutMs,
      maxBuffer: 64 * 1024 * 1024,
      env: cleanTestEnv(),
    });
    const output = `${spawned.stdout || ""}${spawned.stderr || ""}`;
    const counts = parseTestCounts(output);
    results.push({
      contract,
      missing: false,
      exitCode: typeof spawned.status === "number" ? spawned.status : null,
      signal: spawned.signal || null,
      pass: counts.pass || 0,
      fail: counts.fail || 0,
      output,
    });
  }
  const checks = results.reduce((sum, result) => sum + result.pass, 0);
  const failed =
    results.reduce((sum, result) => sum + result.fail, 0) +
    results.filter((result) => result.missing || result.exitCode !== 0).length;
  return { results, checks, failed, ok: failed === 0 && checks >= MIN_CHECKS };
}

// Fail-closed validation of a battery result. Emits `battery_failed` for any
// failed, missing, crashed or under-floor contract. Kept pure so the contract
// can exercise it on mutated results.
export function validateBattery(result) {
  const codes = new Set();
  if (!result || typeof result !== "object") {
    return ["battery_failed"];
  }
  if (result.ok !== true) codes.add("battery_failed");
  if (result.failed !== 0) codes.add("battery_failed");
  if (!(typeof result.checks === "number" && result.checks >= MIN_CHECKS)) codes.add("battery_failed");
  if (!Array.isArray(result.results) || result.results.length !== CONTRACTS.length) {
    codes.add("battery_failed");
  } else {
    for (const entry of result.results) {
      if (!entry || entry.missing === true) codes.add("battery_failed");
      if (entry && entry.exitCode !== 0) codes.add("battery_failed");
      if (entry && entry.fail !== 0) codes.add("battery_failed");
      if (entry && !(entry.pass > 0)) codes.add("battery_failed");
    }
  }
  return [...codes].sort();
}

function tail(text) {
  const value = typeof text === "string" ? text : "";
  return value.length <= OUTPUT_TAIL_CHARS ? value : value.slice(value.length - OUTPUT_TAIL_CHARS);
}

function main() {
  const result = runBattery();
  for (const entry of result.results) {
    const state = entry.missing ? "missing" : `exit=${entry.exitCode}`;
    process.stdout.write(
      `M210_S01_BATTERY_CONTRACT ${entry.contract} pass=${entry.pass} fail=${entry.fail} ${state}\n`,
    );
  }
  const codes = validateBattery(result);
  if (result.ok && codes.length === 0) {
    process.stdout.write(`${BATTERY_MARKER} checks=${result.checks} failed=${result.failed}\n`);
    process.exit(0);
  }
  process.stdout.write(`${BATTERY_FAILED_MARKER} failed=${result.failed} checks=${result.checks}\n`);
  for (const entry of result.results) {
    if (entry.missing || entry.exitCode !== 0 || entry.fail !== 0) {
      process.stdout.write(`M210_S01_BATTERY_TAIL ${entry.contract}\n`);
      process.stdout.write(`${tail(entry.output)}\n`);
    }
  }
  process.exit(1);
}

const invokedDirectly =
  typeof process.argv[1] === "string" && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main();
}
