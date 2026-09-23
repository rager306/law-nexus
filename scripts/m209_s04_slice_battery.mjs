#!/usr/bin/env node
// M209 S04 T06 slice battery runner (D554 shape, D558/D559/D560 acceptance).
//
// The S04 slice contract fixes its own proof carrier here instead of leaving it
// in hand-assembled gsd_exec logs (the known S03 limitation: the T04 evidence
// had no carrier and the battery was assembled by hand). One offline ESM script
// owns the mandatory check set, runs it group by group, merges each finished
// check into `prd/migration/rust-evidence/m209-s04-slice-battery.json` by
// `check_id`, and re-reads that artifact in `--verify` mode.
//
// Usage:
//   node scripts/m209_s04_slice_battery.mjs --run --group <name>
//   node scripts/m209_s04_slice_battery.mjs --verify
//   node scripts/m209_s04_slice_battery.mjs --list [--verbose]
//
// `--run --group <name>` executes exactly one group, records one entry per
// check (`check_id`, `group`, `command`, `exit_code`, `duration_ms`, `verdict`,
// `observed_counts`) and writes the artifact atomically after every check, so
// an interrupted run leaves a consistent partial artifact rather than a torn
// one. `--verify` exits 1 on an absent `check_id`, a non-zero `exit_code`,
// a missing `observed_counts`, a non-canonical artifact, or an incomplete
// mandatory set. `--list` prints the mandatory `check_id`s, which is what the
// sibling contract compares against its own independently transcribed list so
// the set cannot be narrowed silently.
//
// Every check is read-only: the node contracts and the `--check` emitters
// re-render in memory and byte-compare, `cargo fmt`/`clippy`/`check` and
// `git diff HEAD --exit-code` mutate nothing. The only file this runner writes
// is the battery artifact itself, atomically (sibling temp + rename).
//
// Groups are sized for the 600 s tool bound: `node-contracts`, `rust-suites`,
// `emitters`, `lint`, `frozen`.
//
// The battery records its own contract check (`s04_slice_battery_contract`,
// last entry of the `frozen` group). A check's previous record is dropped from
// the artifact before it is re-run, so the artifact never carries a stale record
// for a check that is currently in flight and the contract is never asked to
// validate the record it is itself producing. `--verify` is strict: it always
// requires the full mandatory set, so an interrupted run fails closed instead of
// looking complete. FAIL_CLOSED_CODES below is mirrored, independently
// transcribed, in `scripts/m209_s04_slice_battery_contract.test.mjs`.

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const ARTIFACT_REL = "prd/migration/rust-evidence/m209-s04-slice-battery.json";
export const ARTIFACT_PATH = path.join(ROOT, ARTIFACT_REL);
export const SCHEMA = "law-nexus/slice-battery/v1";
export const KIND = "m209-s04-slice-battery";
export const MILESTONE = "M209-2yg6ix";
export const SLICE = "S04";
export const TASK = "T06";
export const CHECK_TIMEOUT_MS = 570_000;
export const TMP_SUFFIX = ".tmp-m209-s04-t06";

export const GROUPS = Object.freeze(["node-contracts", "rust-suites", "emitters", "lint", "frozen"]);

// Frozen M201/M202 paths plus the canonical registry pair and the two frozen
// pin suites. Zero delta is observed with `git diff HEAD --exit-code`, not
// re-derived (D545 keeps the canonical admission-pair swap as debt).
export const FROZEN_PATHS = Object.freeze([
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
  "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
  "prd/architecture/kb-hierarchy-registry.yaml",
  "prd/architecture/kb-hierarchy-registry-admissions.yaml",
  "crates/ln-kb-ontology/tests/r035_proof_gate.rs",
  "crates/ln-temporal/tests/r070_proof_gate.rs",
]);

// The S04 audit heartbeats are printed on stdout, the S03 emitter heartbeats on
// stderr; the extractor reads both and never trusts an ordering.
const S04_AUDIT_HEARTBEAT = "heartbeat";
const EXIT_ONLY = "exit";
const FROZEN_DELTA = "frozen";

export const FAIL_CLOSED_CODES = Object.freeze([
  "battery_artifact_absent",
  "battery_artifact_invalid",
  "battery_ascii_only_missing",
  "battery_check_failed",
  "battery_check_missing",
  "battery_checks_failed_mismatch",
  "battery_checks_failed_nonzero",
  "battery_checks_missing",
  "battery_checks_total_mismatch",
  "battery_counts_missing",
  "battery_count_only_missing",
  "battery_frozen_paths_mismatch",
  "battery_frozen_paths_not_unchanged",
  "battery_group_missing",
  "battery_group_unknown",
  "battery_kind_mismatch",
  "battery_lifecycle_mismatch",
  "battery_mandatory_set_mismatch",
  "battery_not_ascii",
  "battery_not_canonical",
  "battery_schema_mismatch",
  "battery_unexpected_check",
  "battery_usage",
  "battery_write_failed",
]);

const NON_CLAIMS = Object.freeze([
  "This battery is count-only ASCII evidence of the S04 slice contract checks on one named tree; it records exit codes and observed counts, not new product capability.",
  "It mutates no requirement record and promotes no gate and no R070 leg: the frozen paths are checked for zero delta, not re-derived, and the acceptance ledger stays the only disposition carrier.",
  "Running `--check` emitters and the node contracts proves determinism and byte identity on this tree; it is not an independent re-implementation of the corpus classifiers (D559).",
  "A later milestone validation supersedes this battery only by re-running the same mandatory set against the then-current tree; a missing or failed check is never removed from the list, it is repaired.",
  "The battery contract check is the last entry of the `frozen` group and its own previous record is dropped before it is re-run; `--verify` is strict and requires the full mandatory set, so a missing or failed check is repaired, never erased.",
]);

/// The mandatory check set. `kind` selects the observed-count extractor.
export const CHECKS = Object.freeze([
  // S04 node contracts (T01-T05) and the S02/S03 regression contracts.
  {
    check_id: "s04_corroboration_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s04_corroboration_contract.test.mjs",
  },
  {
    check_id: "s04_corpus_recount_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s04_corpus_recount_contract.test.mjs",
  },
  {
    check_id: "s04_gate_adjudication_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s04_gate_adjudication_contract.test.mjs",
  },
  {
    check_id: "s04_scope_adjudication_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s04_scope_adjudication_contract.test.mjs",
  },
  {
    check_id: "s04_acceptance_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s04_acceptance_contract.test.mjs",
  },
  {
    check_id: "s02_extraction_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s02_extraction_contract.test.mjs",
  },
  {
    check_id: "s02_regeneration_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s02_regeneration_contract.test.mjs",
  },
  {
    check_id: "s02_build_admissions_check",
    group: "node-contracts",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s02_build_admissions.mjs --check",
  },
  {
    check_id: "s03_family_denominator_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s03_family_denominator_contract.test.mjs",
  },
  {
    check_id: "s03_amends_provision_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s03_amends_provision_contract.test.mjs",
  },
  {
    check_id: "s03_commencement_transition_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s03_commencement_transition_contract.test.mjs",
  },
  {
    check_id: "s03_edition_chain_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s03_edition_chain_contract.test.mjs",
  },
  {
    check_id: "s03_scope_ledger_contract",
    group: "node-contracts",
    kind: "node-test",
    command: "node --test scripts/m209_s03_scope_ledger_contract.test.mjs",
  },
  // Rust pin and boundary suites.
  {
    check_id: "s04_acceptance_boundary_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-kb-ontology --offline --test m209_s04_acceptance_boundary",
  },
  {
    check_id: "r035_proof_gate_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-kb-ontology --offline --test r035_proof_gate",
  },
  {
    check_id: "r070_proof_gate_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-temporal --offline --test r070_proof_gate",
  },
  {
    check_id: "s03_frozen_m201_guard_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-temporal --offline --test m209_s03_frozen_m201_guard",
  },
  // The two punkt / registry-admission suites that guard the ledger's punkt
  // non-claim (`status: unchanged`, `punkt_rows_admitted: 0`, D540). They are
  // in the battery so the non-claim is not stronger than its check coverage.
  {
    check_id: "punkt_subunit_ctv_contract_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-kb-ontology --offline --test punkt_subunit_ctv_contract",
  },
  {
    check_id: "hierarchy_registry_admission_suite",
    group: "rust-suites",
    kind: "cargo-test",
    command: "cargo test -p ln-kb-ontology --offline --test hierarchy_registry_admission",
  },
  // Producer determinism: the five S03 emitter `--check` modes, the S04 auditor
  // `--check` modes (the S04 evidence artifacts re-render byte-identically), the
  // live candidate artifact and the successor-pair registry generator.
  {
    check_id: "s03_emitter_families_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-consultant-parser --offline --bin m209-amendment-provenance -- --mode families --out prd/migration/rust-evidence/m209-s03-family-denominator.json --check",
  },
  {
    check_id: "s03_emitter_amends_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-consultant-parser --offline --bin m209-amendment-provenance -- --mode amends-provisions --out prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json --check",
  },
  {
    check_id: "s03_emitter_commencement_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-consultant-parser --offline --bin m209-amendment-provenance -- --mode commencement --out prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json --check",
  },
  {
    check_id: "s03_emitter_edition_chain_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-consultant-parser --offline --bin m209-amendment-provenance -- --mode edition-chain --out prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json --check",
  },
  {
    check_id: "s03_emitter_ledger_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-consultant-parser --offline --bin m209-amendment-provenance -- --mode ledger --out prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json --check",
  },
  {
    check_id: "s04_evidence_audit_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s04_evidence_audit.mjs --mode all --check",
  },
  {
    check_id: "s04_corpus_recount_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s04_corpus_recount.mjs --mode all --check",
  },
  {
    check_id: "s04_gate_adjudication_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s04_gate_adjudication.mjs --mode gates --check",
  },
  {
    check_id: "s04_scope_adjudication_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s04_scope_adjudication.mjs --mode legs --check",
  },
  {
    check_id: "s04_acceptance_ledger_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command: "node scripts/m209_s04_acceptance_ledger.mjs --mode ledger --check",
  },
  {
    check_id: "s02_hierarchy_candidate_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run --offline -q -p ln-decode --bin hierarchy-candidate-artifact -- --source 'law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml' --label 'payload:m209-s02-fz44-edition' --check --out prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json",
  },
  {
    check_id: "s02_registry_generator_check",
    group: "emitters",
    kind: S04_AUDIT_HEARTBEAT,
    command:
      "cargo run -q -p ln-product-cli --offline --bin hierarchy-registry-generator -- --candidate-artifact prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json --admissions prd/architecture/m209-s02-kb-hierarchy-registry-admissions.yaml --out prd/architecture/kb-hierarchy-registry.yaml --check",
  },
  // Workspace hygiene, unweakened.
  {
    check_id: "fmt_check",
    group: "lint",
    kind: EXIT_ONLY,
    command: "cargo fmt --all -- --check",
  },
  {
    check_id: "clippy_workspace",
    group: "lint",
    kind: EXIT_ONLY,
    command: "cargo clippy --workspace --offline --all-targets -- -D warnings",
  },
  {
    check_id: "cargo_check_workspace",
    group: "lint",
    kind: EXIT_ONLY,
    command: "cargo check --workspace --offline",
  },
  // Frozen zero delta, then the battery's own contract check.
  {
    check_id: "frozen_zero_delta",
    group: "frozen",
    kind: FROZEN_DELTA,
    command: `git diff HEAD --exit-code -- ${FROZEN_PATHS.join(" ")}`,
  },
  {
    check_id: "s04_slice_battery_contract",
    group: "frozen",
    kind: "node-test",
    command: "node --test scripts/m209_s04_slice_battery_contract.test.mjs",
  },
]);

export const MANDATORY_CHECK_IDS = Object.freeze(CHECKS.map((check) => check.check_id));

class BatteryError extends Error {
  constructor(code, exitCode) {
    super(code);
    this.code = code;
    this.exitCode = exitCode;
  }
}

function isAscii(text) {
  for (let index = 0; index < text.length; index += 1) {
    if (text.charCodeAt(index) > 0x7f) return false;
  }
  return true;
}

function firstMatch(text, patterns) {
  for (const pattern of patterns) {
    const match = pattern.exec(text);
    if (match) return Number.parseInt(match[1], 10);
  }
  return null;
}

/// Extracts the observed counts for one finished check. Returns null when the
/// check produced no countable observation; the caller fails closed instead of
/// recording an empty count.
export function extractObservedCounts(check, stdout, stderr, exitCode) {
  const text = `${stdout}\n${stderr}`;
  if (check.kind === "node-test") {
    const pass = firstMatch(text, [/# pass (\d+)/, /\u2139 pass (\d+)/, /\bpass (\d+)\b/]);
    const fail = firstMatch(text, [/# fail (\d+)/, /\u2139 fail (\d+)/, /\bfail (\d+)\b/]);
    if (pass === null || fail === null) return null;
    return `pass=${pass} fail=${fail}`;
  }
  if (check.kind === "cargo-test") {
    const pattern = /test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed/g;
    let passed = 0;
    let failed = 0;
    let seen = false;
    for (const match of text.matchAll(pattern)) {
      seen = true;
      passed += Number.parseInt(match[1], 10);
      failed += Number.parseInt(match[2], 10);
    }
    if (!seen) return null;
    return `passed=${passed} failed=${failed}`;
  }
  if (check.kind === S04_AUDIT_HEARTBEAT) {
    // Heartbeats are ASCII key=value lines. Keys may carry a hyphen
    // (`edition-chain=`, `candidate-backed=`) and the S04 auditors prefix a bare
    // marker token (`M209_S04_AUDIT_OK`); a line must carry at least one
    // assignment to count, so ordinary prose or diagnostics are never accepted.
    const assignment = /^[A-Za-z0-9_-]+=[A-Za-z0-9_.:-]+$/;
    const marker = /^[A-Za-z0-9_-]+$/;
    const lines = text.split("\n").reverse();
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.length === 0 || !isAscii(trimmed)) continue;
      const tokens = trimmed.split(/\s+/);
      if (!tokens.some((part) => assignment.test(part))) continue;
      if (tokens.every((part) => assignment.test(part) || marker.test(part))) return trimmed;
    }
    return null;
  }
  if (check.kind === EXIT_ONLY) {
    return `exit=${exitCode}`;
  }
  if (check.kind === FROZEN_DELTA) {
    const changed = stdout.trim().length === 0 && exitCode === 0 ? 0 : 1;
    return `paths=${FROZEN_PATHS.length} changed=${changed}`;
  }
  return null;
}

function entryFor(check, exitCode, durationMs, observedCounts) {
  return {
    check_id: check.check_id,
    group: check.group,
    command: check.command,
    exit_code: exitCode,
    duration_ms: durationMs,
    verdict: exitCode === 0 ? "pass" : "fail",
    observed_counts: observedCounts === null ? "" : observedCounts,
  };
}

export function buildDocument(entries) {
  const merged = entries instanceof Map ? entries : new Map(entries.map((entry) => [entry.check_id, entry]));
  const ordered = [];
  for (const checkId of MANDATORY_CHECK_IDS) {
    if (merged.has(checkId)) ordered.push(merged.get(checkId));
  }
  const extras = [...merged.keys()].filter((checkId) => !MANDATORY_CHECK_IDS.includes(checkId)).sort();
  for (const checkId of extras) ordered.push(merged.get(checkId));
  const failed = ordered.filter((entry) => entry.exit_code !== 0).length;
  const frozen = merged.get("frozen_zero_delta");
  return {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: "[bounded]",
    count_only: true,
    ascii_only: true,
    checks_total: ordered.length,
    checks_failed: failed,
    mandatory_check_ids: [...MANDATORY_CHECK_IDS],
    groups: [...GROUPS],
    groups_recorded: GROUPS.filter((group) => ordered.some((entry) => entry.group === group)),
    unexpected_check_ids: extras,
    frozen_paths: [...FROZEN_PATHS],
    frozen_paths_unchanged: frozen && frozen.exit_code === 0 ? 1 : 0,
    checks: ordered,
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };
}

/// The one predicate behind `--verify` and the sibling contract. Returns a
/// sorted list of named fail-closed codes; an empty list means the battery is
/// complete and green. `options.inflight` exempts exactly the check currently
/// being recorded (the battery's own contract check) from the presence rule.
export function verifyBattery(document, options = {}) {
  const mandatory = options.mandatory ?? MANDATORY_CHECK_IDS;
  const frozenPaths = options.frozenPaths ?? FROZEN_PATHS;
  const inflight = options.inflight ?? null;
  const errors = [];
  if (!document || typeof document !== "object") return ["battery_artifact_invalid"];
  if (document.kind !== KIND) errors.push("battery_kind_mismatch");
  if (document.schema !== SCHEMA) errors.push("battery_schema_mismatch");
  if (document.lifecycle !== "[bounded]") errors.push("battery_lifecycle_mismatch");
  if (document.count_only !== true) errors.push("battery_count_only_missing");
  if (document.ascii_only !== true) errors.push("battery_ascii_only_missing");
  const checks = Array.isArray(document.checks) ? document.checks : null;
  if (!checks) return [...errors, "battery_checks_missing"].sort();
  if (document.checks_total !== checks.length) errors.push("battery_checks_total_mismatch");
  const failed = checks.filter((entry) => entry.exit_code !== 0).length;
  if (failed !== 0) errors.push(`battery_checks_failed_nonzero:${failed}`);
  if (document.checks_failed !== failed) errors.push("battery_checks_failed_mismatch");
  const declaredMandatory = Array.isArray(document.mandatory_check_ids) ? document.mandatory_check_ids : [];
  const mandatoryMatches =
    declaredMandatory.length === mandatory.length && mandatory.every((id) => declaredMandatory.includes(id));
  if (!mandatoryMatches) errors.push("battery_mandatory_set_mismatch");
  const byId = new Map(checks.map((entry) => [entry.check_id, entry]));
  for (const checkId of mandatory) {
    if (checkId === inflight) continue;
    const entry = byId.get(checkId);
    if (!entry) {
      errors.push(`battery_check_missing:${checkId}`);
      continue;
    }
    if (entry.exit_code !== 0) errors.push(`battery_check_failed:${checkId}:${entry.exit_code}`);
    if (typeof entry.observed_counts !== "string" || entry.observed_counts.length === 0) {
      errors.push(`battery_counts_missing:${checkId}`);
    }
  }
  for (const entry of checks) {
    if (entry.exit_code !== 0) continue;
    if (typeof entry.observed_counts !== "string" || entry.observed_counts.length === 0) {
      const code = `battery_counts_missing:${entry.check_id}`;
      if (!errors.includes(code)) errors.push(code);
    }
  }
  if (document.frozen_paths_unchanged !== 1) errors.push("battery_frozen_paths_not_unchanged");
  const declaredFrozen = Array.isArray(document.frozen_paths) ? document.frozen_paths : [];
  const frozenMatches =
    declaredFrozen.length === frozenPaths.length && frozenPaths.every((entry) => declaredFrozen.includes(entry));
  if (!frozenMatches) errors.push("battery_frozen_paths_mismatch");
  const recordedGroups = Array.isArray(document.groups_recorded) ? document.groups_recorded : [];
  for (const group of GROUPS) {
    if (!recordedGroups.includes(group)) errors.push(`battery_group_missing:${group}`);
  }
  for (const entry of checks) {
    if (!mandatory.includes(entry.check_id)) errors.push(`battery_unexpected_check:${entry.check_id}`);
  }
  return [...new Set(errors)].sort();
}

/// Text-level verification: canonical form and ASCII are properties of the
/// written bytes, so they are checked before the document predicate. Returns a
/// sorted, de-duplicated list of codes; `null` means the artifact is absent.
export function verifyArtifactText(raw, options = {}) {
  if (raw === null || raw === undefined) return ["battery_artifact_absent"];
  const problems = [];
  if (!isAscii(raw)) problems.push("battery_not_ascii");
  if (!raw.endsWith("\n") || raw.trimEnd().includes("\n")) problems.push("battery_not_canonical");
  let document = null;
  try {
    document = JSON.parse(raw);
  } catch {
    problems.push("battery_artifact_invalid");
  }
  if (document !== null) {
    if (JSON.stringify(document) !== raw.trimEnd()) problems.push("battery_not_canonical");
    problems.push(...verifyBattery(document, options));
  }
  return [...new Set(problems)].sort();
}

function readRaw() {
  if (!existsSync(ARTIFACT_PATH)) return null;
  return readFileSync(ARTIFACT_PATH, "utf8");
}

function loadExistingEntries() {
  const raw = readRaw();
  if (raw === null) return new Map();
  let document;
  try {
    document = JSON.parse(raw);
  } catch {
    throw new BatteryError("battery_artifact_invalid", 2);
  }
  if (!document || document.kind !== KIND || !Array.isArray(document.checks)) {
    throw new BatteryError("battery_artifact_invalid", 2);
  }
  return new Map(document.checks.map((entry) => [entry.check_id, entry]));
}

/// Atomic write (sibling temp + rename) of the canonical one-line document.
/// Exported so the sibling contract can exercise the write-failure path against
/// a target outside the repository instead of mutating tracked bytes.
export function writeDocumentTo(targetPath, entries) {
  const document = buildDocument(entries);
  const text = `${JSON.stringify(document)}\n`;
  const tmpPath = `${targetPath}${TMP_SUFFIX}`;
  try {
    writeFileSync(tmpPath, text);
    renameSync(tmpPath, targetPath);
  } catch {
    try {
      unlinkSync(tmpPath);
    } catch {
      // best effort cleanup; the write failure is reported below
    }
    throw new BatteryError("battery_write_failed", 4);
  }
  return document;
}

function writeDocument(entries) {
  return writeDocumentTo(ARTIFACT_PATH, entries);
}

/// The last few lines of a failing check's output, ASCII-sanitized and bounded,
/// so a red battery entry is diagnosable without re-running the check by hand.
export function failureTail(stdout, stderr, limit = 25) {
  const lines = `${stdout}\n${stderr}`
    .split("\n")
    .map((line) => line.replace(/[\u0000-\u001f\u007f-\uffff]/g, "?"))
    .filter((line) => line.trim().length > 0);
  return lines.slice(-limit).map((line) => (line.length > 400 ? `${line.slice(0, 400)}...` : line));
}

function parseArgs(argv) {
  const options = { mode: null, group: null, verbose: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--run") {
      options.mode = "run";
    } else if (arg === "--verify") {
      options.mode = "verify";
    } else if (arg === "--list") {
      options.mode = "list";
    } else if (arg === "--verbose") {
      options.verbose = true;
    } else if (arg === "--group") {
      index += 1;
      if (index >= argv.length) return { error: "battery_usage" };
      options.group = argv[index];
    } else {
      return { error: "battery_usage" };
    }
  }
  if (options.mode === "run" && !options.group) return { error: "battery_usage" };
  if (options.mode !== "run" && options.group) return { error: "battery_usage" };
  if (!options.mode) return { error: "battery_usage" };
  return options;
}

function runGroup(group) {
  if (!GROUPS.includes(group)) {
    console.error(`M209_S04_BATTERY_FAIL battery_group_unknown group=${group}`);
    return 3;
  }
  const checks = CHECKS.filter((check) => check.group === group);
  const entries = loadExistingEntries();
  let groupFailed = 0;
  let countsMissing = 0;
  for (const check of checks) {
    // Drop the previous record before re-running: a check's stale result is
    // never presented as its current one, and the battery's own contract check
    // is not asked to validate a record it is itself producing.
    entries.delete(check.check_id);
    writeDocument(entries);
    const startedAt = Date.now();
    const result = spawnSync(check.command, {
      cwd: ROOT,
      shell: "/bin/bash",
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
      timeout: CHECK_TIMEOUT_MS,
    });
    const durationMs = Date.now() - startedAt;
    const stdout = typeof result.stdout === "string" ? result.stdout : "";
    const stderr = typeof result.stderr === "string" ? result.stderr : "";
    const exitCode = typeof result.status === "number" ? result.status : 1;
    const observed = extractObservedCounts(check, stdout, stderr, exitCode);
    if (exitCode === 0 && observed === null) {
      countsMissing += 1;
      console.error(`M209_S04_BATTERY_COUNTS_MISSING check_id=${check.check_id}`);
    }
    const entry = entryFor(check, exitCode, durationMs, observed);
    entries.set(check.check_id, entry);
    writeDocument(entries);
    if (exitCode === 0) {
      console.error(
        `M209_S04_BATTERY_CHECK check_id=${check.check_id} group=${group} exit=0 duration_ms=${durationMs} observed="${entry.observed_counts}"`,
      );
    } else {
      groupFailed += 1;
      console.error(
        `M209_S04_BATTERY_CHECK_FAIL check_id=${check.check_id} group=${group} exit=${exitCode} duration_ms=${durationMs}`,
      );
      // Fail-path observability: the failing check's tail is printed so the
      // cause is diagnosable from the run log alone. Diagnostics stay on
      // stderr; the artifact records counts only.
      for (const line of failureTail(stdout, stderr)) {
        console.error(`M209_S04_BATTERY_DETAIL check_id=${check.check_id} ${line}`);
      }
    }
  }
  const document = writeDocument(entries);
  const pending = MANDATORY_CHECK_IDS.filter(
    (checkId) => !document.checks.some((entry) => entry.check_id === checkId),
  );
  console.error(
    `M209_S04_BATTERY_GROUP_OK group=${group} group_checks=${checks.length} recorded=${document.checks_total} mandatory=${MANDATORY_CHECK_IDS.length} pending=${pending.length} failed=${groupFailed} counts_missing=${countsMissing} frozen_paths_unchanged=${document.frozen_paths_unchanged}`,
  );
  return groupFailed === 0 && countsMissing === 0 ? 0 : 1;
}

function runVerify() {
  const raw = readRaw();
  const problems = verifyArtifactText(raw);
  if (problems.length > 0) {
    for (const problem of problems) console.error(`M209_S04_BATTERY_FAIL ${problem}`);
    console.error(`M209_S04_BATTERY_VERIFY_FAIL problems=${problems.length}`);
    return 1;
  }
  const document = JSON.parse(raw);
  console.error(
    `M209_S04_BATTERY_OK checks=${document.checks_total} failed=${document.checks_failed} mandatory=${MANDATORY_CHECK_IDS.length} frozen_paths_unchanged=${document.frozen_paths_unchanged} groups=${document.groups_recorded.length} drift=0`,
  );
  return 0;
}

function runList(verbose) {
  for (const check of CHECKS) {
    process.stdout.write(verbose ? `${check.check_id}\t${check.group}\t${check.command}\n` : `${check.check_id}\n`);
  }
  return 0;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error) {
    console.error("usage: m209_s04_slice_battery.mjs --run --group <name> | --verify | --list [--verbose]");
    console.error(`M209_S04_BATTERY_FAIL ${options.error}`);
    return 2;
  }
  try {
    if (options.mode === "run") return runGroup(options.group);
    if (options.mode === "verify") return runVerify();
    return runList(options.verbose);
  } catch (error) {
    const code = error instanceof BatteryError ? error.code : "battery_artifact_invalid";
    const exitCode = error instanceof BatteryError ? error.exitCode : 2;
    console.error(`M209_S04_BATTERY_FAIL ${code}`);
    return exitCode;
  }
}

const invokedDirectly = process.argv[1] !== undefined && pathToFileURL(process.argv[1]).href === import.meta.url;
if (invokedDirectly) {
  process.exitCode = main();
}
