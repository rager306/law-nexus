#!/usr/bin/env node
// M210-3afp79 S04 T05 slice battery.
//
// Sequentially runs the four S04 enforcement contracts (admission, matrix,
// cards, session) in dependency order, then the five regression gates that keep
// the surrounding proofs alive: the S01 packet battery
// (`node scripts/m210_s01_slice_battery.mjs`), the S02 adoption battery
// (`node scripts/m210_s02_slice_battery.mjs`), the S03 slice battery
// (`node scripts/m210_s03_slice_battery.mjs`, which itself carries the S01 and
// S02 batteries, the M209/S04 verify mode and the live source revision), the
// M209/S04 battery verify mode (`node scripts/m209_s04_slice_battery.mjs
// --verify`, which carries the frozen M201/M202 zero-delta guard and the
// R035/R070 proof-gate suites) and the live engine source revision
// (`node scripts/m204_s08_source_revision.mjs`, which must print a
// sha256:<64hex>).
//
// It prints one `M210_S04_BATTERY_CONTRACT <path> pass=N fail=N exit=M` line per
// contract followed by the contract's own OK marker line verbatim, one
// `M210_S04_BATTERY_REGRESSION <id> exit=M checks=N marker=...` line per
// regression gate (followed by the gate's own marker line verbatim, so the
// nested markers are visible in the captured evidence), and one aggregate
// marker `M210_S04_BATTERY_OK checks=N failed=0`. On any failed, missing,
// substituted or under-floor contract, or any failed regression gate, it prints
// `M210_S04_BATTERY_FAILED failed=N` (N = failing steps plus 1 for an
// under-floor total, never 0) plus a `M210_S04_BATTERY_FAILED_CODES <codes>`
// line naming the refusal codes, then the tails of the failing steps under
// `M210_S04_BATTERY_TAIL <path>` (or, when no single step produced the tail, a
// `M210_S04_BATTERY_TAIL scripts/m210_s04_slice_battery.mjs` line carrying the
// floor and the observed totals), and exits 1, so a red run is diagnosable from
// the log alone rather than only from an exit code.
//
// Offline: no network, no dependency install, no git mutation. The battery only
// reads and spawns; it writes no file and edits no artifact.
//
// Run: node scripts/m210_s04_slice_battery.mjs
// This script never includes its own contract
// (`m210_s04_slice_battery_contract.test.mjs`), so there is no recursion: the
// battery contract drives this runner, and this runner drives the four S04
// contracts and the five regressions.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const BATTERY_MARKER = "M210_S04_BATTERY_OK";
export const BATTERY_FAILED_MARKER = "M210_S04_BATTERY_FAILED";
export const BATTERY_FAILED_CODES_MARKER = "M210_S04_BATTERY_FAILED_CODES";
export const BATTERY_TAIL_MARKER = "M210_S04_BATTERY_TAIL";
export const BATTERY_CONTRACT_MARKER = "M210_S04_BATTERY_CONTRACT";
export const BATTERY_REGRESSION_MARKER = "M210_S04_BATTERY_REGRESSION";

// The four S04 enforcement contracts, in dependency order: the admission
// reconciliation proves the established bounded adoption and the separated
// states, the finding matrix re-verifies the 19 findings, the review cards are
// derived from that matrix, and the session contract sits on top of the cards.
// The battery contract is deliberately absent: it drives this runner.
export const CONTRACTS = [
  "scripts/m210_s04_admission_contract.test.mjs",
  "scripts/m210_s04_finding_matrix_contract.test.mjs",
  "scripts/m210_s04_review_cards_contract.test.mjs",
  "scripts/m210_s04_session_contract.test.mjs",
];

// The OK marker each contract prints only after every one of its own cases
// passed. The battery prints the matched marker line verbatim, so the S04
// integration is provable from the aggregate log, and a contract that exits 0
// without printing its marker is refused as a failed contract (a truncated or
// suppressed run must not look green).
export const CONTRACT_MARKERS = {
  "scripts/m210_s04_admission_contract.test.mjs": /^M210_S04_ADMISSION_OK.*$/m,
  "scripts/m210_s04_finding_matrix_contract.test.mjs": /^M210_S04_MATRIX_OK.*$/m,
  "scripts/m210_s04_review_cards_contract.test.mjs": /^M210_S04_CARDS_OK.*$/m,
  "scripts/m210_s04_session_contract.test.mjs": /^M210_S04_SESSION_OK.*$/m,
};

// The regression gates the S04 slice may not break. `marker` is matched against
// the combined stdout+stderr of the gate; `checks` is read from the marker so the
// nested batteries' own check totals are folded into this battery's aggregate (a
// nested battery that silently reports zero checks must not look green).
// `requireFields` pins the fields the S04 stopping condition depends on: the
// M209/S04 verify mode must report failed=0, frozen_paths_unchanged=1 and drift=0
// (R035/R070 and the frozen M201/M202 zero delta). The S03 marker is matched
// without pinning its check total, because that total shifts when the S03
// enforcement is repaired; only failed=0 is required there.
export const REGRESSIONS = [
  {
    id: "s01_slice_battery",
    script: "scripts/m210_s01_slice_battery.mjs",
    args: [],
    marker: /^M210_S01_BATTERY_OK checks=(\d+) failed=0$/m,
    describe: "the S01 packet battery (family register, IR alternatives, source-bound examples)",
  },
  {
    id: "s02_slice_battery",
    script: "scripts/m210_s02_slice_battery.mjs",
    args: [],
    marker: /^M210_S02_BATTERY_OK checks=(\d+) failed=0$/m,
    describe: "the S02 adoption battery (packet, presentation, answer, governing surface, checkpoint)",
  },
  {
    id: "s03_slice_battery",
    script: "scripts/m210_s03_slice_battery.mjs",
    args: [],
    marker: /^M210_S03_BATTERY_OK checks=(\d+) failed=0$/m,
    describe: "the S03 slice battery (v2 adoption, start gate, semantics, abstention, activation)",
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

// Check floor for a meaningful run. The observed aggregate is 663 checks, built
// as the four S04 contracts (22 admission + 21 matrix + 14 cards + 20 session =
// 77 contract checks) plus the regressions (50 S01 battery checks + 154 S02
// battery checks + 345 S03 battery checks + 36 M209/S04 checks + 1
// source-revision assertion = 586 regression checks). The S02 and S03
// batteries are reached both transitively (inside the S03 run) and standalone,
// so nested checks are counted more than once; that is inherited from the S03
// precedent and is deliberate, because the standalone runs are what gate the
// regression independently. The floor is 596, i.e. 90% of 663 rounded down, the
// same ratio the S01 battery (floor 45 of 50), the S02 battery (floor 138 of
// 154) and the S03 battery (floor 305 of 339) used. It is a coarse backstop
// against a truncated or silently empty run - every individual contract and
// regression remains separately gated by its own exit code, marker and positive
// count, so no lost check can hide behind the floor. It is a ratio, never a pin
// on one historic total: when a contract legitimately gains checks the observed
// total moves and the floor moves with it.
export const MIN_CHECKS = 596;

export const SOURCE_REVISION_SCRIPT = "scripts/m204_s08_source_revision.mjs";

// This runner's own repository-relative path, used for the aggregate-only
// failure tail when no single step is red.
export const BATTERY_SELF = "scripts/m210_s04_slice_battery.mjs";

// The section 3 pin the S04 slice must leave untouched. It is asserted against
// the live file AND against the admission reconciliation's declared pin, so a
// silent re-pin on both sides still fails closed.
export const TEMPORAL_LEGAL_MODEL = "prd/temporal-legal-model.md";
export const TEMPORAL_LEGAL_MODEL_PIN =
  "sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6";

// The S04 JSON data artifacts. These carry the slice's data; each must exist,
// stay outside crates/, stay ASCII and carry no Rust runtime marker.
export const S04_DATA_ARTIFACTS = [
  "prd/architecture/m210-s04-admission-reconciliation.json",
  "prd/architecture/m210-s04-finding-evidence-matrix.json",
  "prd/architecture/m210-s04-rc28-review-cards.json",
  "prd/architecture/m210-s04-review-session-contract.json",
  "prd/architecture/m210-s04-event-submission-delta.json",
  "prd/architecture/m210-s04-review-session-state.json",
];

// The tracked S04 markdown artifacts produced by the earlier tasks. The review
// presentation is a tracked Russian surface (it is the human-facing
// presentation), so it is deliberately excluded from the ASCII rule; it is still
// checked for existence and location. The T05 final check is a separate ASCII
// machine checkpoint and is tracked on its own.
export const S04_TRACKED_MARKDOWN_ARTIFACTS = [
  "prd/architecture/m210-s04-runtime-admission.md",
  "prd/architecture/m210-s04-rc28-review-presentation.md",
];

export const S04_PACKAGE_ARTIFACTS = [...S04_DATA_ARTIFACTS, ...S04_TRACKED_MARKDOWN_ARTIFACTS];

export const S04_ENFORCEMENT_DIR = "scripts/";
export const S04_ENFORCEMENT_PREFIX = "m210_s04_";
export const CRATES_ROOT = "crates/";

// The final RC28 checkpoint and its single verdict line.
export const RC28_FINAL_CHECK = "prd/architecture/m210-s04-rc28-final-check.md";
export const RC28_VERDICT_PATTERN = /^\*\*rc28: (hold|closed)\*\*$/m;

// The Review Case events directory that must stay absent: no event was written.
export const EVENTS_DIR = "prd/architecture/review-cases/packets/RC-2026-09-10-001/events";

// The hold rationale that is forbidden: the hold must never be justified by an
// absence of variant C adoption. The literal is assembled from fragments so the
// enforcement layer may name the code it refuses without carrying the literal
// itself as a claim.
export const FORBIDDEN_HOLD_RATIONALE = ["rc28_hold_justified_by_", "missing_acceptance"].join("");

// The checkpoint marker printed by this runner once the final RC28 checkpoint's
// own semantics are validated (its counts re-derived from the live T02 rows and
// its digests re-hashed live). It makes the checkpoint a visible part of the
// battery's fail-closed surface instead of a contract-only concern.
export const BATTERY_CHECKPOINT_MARKER = "M210_S04_BATTERY_CHECKPOINT";

// The T02 evidence matrix is the immutable machine input the final checkpoint is
// derived from. The packet JSON file and the review source document are two
// distinct digest namespaces: the packet is the transmitted envelope, while the
// source document is what the packet declares it reviewed. They must never share
// a field.
export const RC28_MATRIX = "prd/architecture/m210-s04-finding-evidence-matrix.json";
export const RC28_PACKET_FILE = "prd/architecture/review-cases/packets/RC-2026-09-10-001.json";
export const RC28_SOURCE_DOCUMENT = "doc/review/review-28-10-09-2026.md";

// The four count kinds the final checkpoint must keep separate. A single
// "class matched" number conflates them: 4 rows were re-verified against live
// sources, 13 rows carry a true `class_match` compatibility flag, 6 carry a
// false one, and exactly 2 rows carry the `evidence_present_class_matched`
// verdict. A true compatibility flag says the evidence is of the required proof
// class; it is neither a sufficiency claim nor evidence presence.
export const RC28_COUNT_KEYS = [
  "rereverified_rows",
  "class_match_compatibility_rows",
  "class_mismatch_rows",
  "exact_class_matched_verdict_rows",
];

// The exact class-matched machine verdict, and the compatibility flag it must
// not be conflated with.
export const RC28_EXACT_MATCH_VERDICT = "evidence_present_class_matched";

// The mandated hold basis and the established adoption basis. The hold rests on
// the absence of valid per-finding dispositions; it must never rest on an
// absence of variant C adoption.
export const RC28_HOLD_BASIS = "valid per-finding dispositions absent";
export const RC28_ADOPTION_BASIS_PATTERN = /variant C established/;

// The prior owner decision recorded in S02 (an explicit F13 defer) and the note
// that the current RC28 ledger slot is still empty. The two namespaces must stay
// separate: "none recorded" on the current ledger is not evidence that the prior
// owner defer is absent. The forbidden prior-defer literal is the reviewer-side
// namespace confusion this validator refuses.
export const RC28_PRIOR_DECISION_PATTERN = /deferred-explicit[\s\S]*\bs02\b/i;
export const RC28_CURRENT_DISPOSITION_PATTERN = /none recorded[\s\S]*rc28/i;
export const FORBIDDEN_PRIOR_DEFER_LITERAL = "no owner defer recorded";

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
// count when the gate is green, or a zero-check non-marker when its marker is
// absent or its required fields do not hold.
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

// A live sha256 over one repository-relative file, used to bind the checkpoint's
// digest namespaces to the bytes they claim to describe.
function sha256File(absolute) {
  return createHash("sha256").update(readFileSync(absolute)).digest("hex");
}

// The checkpoint's bold single-line header fields (`**key:** value`).
export function parseCheckpointHeader(md) {
  const fields = {};
  for (const line of String(md).split("\n")) {
    const match = line.match(/^\*\*([a-z0-9_]+):\*\*\s*(.*)$/);
    if (match) fields[match[1]] = match[2].trim();
  }
  return fields;
}

// The bold single-line rc28 verdicts; exactly one `hold` is required while no
// valid disposition exists.
export function parseCheckpointVerdicts(md) {
  return [...String(md).matchAll(/^\*\*rc28: (hold|closed)\*\*$/gm)].map((match) => match[1]);
}

// Derives the four independent count kinds from the live T02 rows. This is the
// single source of truth for the checkpoint's counts: a declared count is only
// accepted when it equals the value derived here.
export function deriveRc28Counts(matrix) {
  const rows = Array.isArray(matrix && matrix.rows) ? matrix.rows.filter((row) => row && typeof row === "object") : [];
  const count = (predicate) => rows.filter(predicate).length;
  return {
    findings_total: rows.length,
    rereverified_rows: count((row) => row.rereverified === true),
    class_match_compatibility_rows: count((row) => row.class_match === true),
    class_mismatch_rows: count((row) => row.class_match === false),
    exact_class_matched_verdict_rows: count((row) => row.machine_verdict === RC28_EXACT_MATCH_VERDICT),
  };
}

// Reads the checkpoint, the live T02 matrix and the live digest inputs into one
// plain observation object. Kept pure enough that the sibling contract can clone
// it, mutate one field and prove each refusal empirically.
export function observeRc28Checkpoint(root = REPO_ROOT) {
  const text = readFileSync(path.join(root, RC28_FINAL_CHECK), "utf8");
  const matrix = JSON.parse(readFileSync(path.join(root, RC28_MATRIX), "utf8"));
  const fields = parseCheckpointHeader(text);
  const reviewCase = matrix.review_case && typeof matrix.review_case === "object" ? matrix.review_case : {};
  return {
    text,
    fields,
    verdicts: parseCheckpointVerdicts(text),
    derived: deriveRc28Counts(matrix),
    summary: matrix.summary,
    digest: {
      source_content_sha256: fields.source_content_sha256,
      packet_file_sha256: fields.packet_file_sha256,
      packet_declared_content_sha256: fields.packet_declared_content_sha256,
      live_source_content_sha256: `sha256:${sha256File(path.join(root, RC28_SOURCE_DOCUMENT))}`,
      live_packet_file_sha256: `sha256:${sha256File(path.join(root, RC28_PACKET_FILE))}`,
      matrix_source_content_sha256: reviewCase.source_content_sha256,
      matrix_packet_file_sha256: reviewCase.packet_file_sha256,
      matrix_packet_declared_content_sha256: reviewCase.packet_declared_content_sha256,
    },
  };
}

// Fail-closed validation of the final RC28 checkpoint's own semantics. Kept pure
// so the sibling contract can exercise it on cloned-and-mutated observations.
// Returns a sorted, de-duplicated code set; an empty array means the checkpoint
// keeps its counts separate, its digest namespaces bound and its hold basis
// right.
//
// Documented codes (asserted equal to the contract's documented set):
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
export function validateRc28Checkpoint(observation) {
  const codes = new Set();
  if (!observation || typeof observation !== "object") return ["checkpoint_missing"];
  const fields = observation.fields;
  const derived = observation.derived;
  const digest = observation.digest;
  if (!fields || typeof fields !== "object" || !derived || typeof derived !== "object" || !digest || typeof digest !== "object") {
    return ["checkpoint_missing"];
  }

  const verdicts = Array.isArray(observation.verdicts) ? observation.verdicts : [];
  const text = typeof observation.text === "string" ? observation.text : "";
  if (verdicts.length !== 1 || verdicts[0] !== "hold" || !RC28_VERDICT_PATTERN.test(text)) {
    codes.add("verdict_invalid");
  }

  // Every count kind must be declared separately. A missing kind means the kinds
  // are collapsed into one number, which is exactly the conflation this guards.
  const hasCount = (key) => Object.prototype.hasOwnProperty.call(fields, key);
  if (!hasCount("findings_total")) codes.add("count_conflation");
  for (const key of RC28_COUNT_KEYS) {
    if (!hasCount(key)) codes.add("count_conflation");
  }
  // A declared count is accepted only when it equals the live-derived value.
  if (hasCount("findings_total") && Number(fields.findings_total) !== derived.findings_total) codes.add("counts_drift");
  for (const key of RC28_COUNT_KEYS) {
    if (!hasCount(key)) continue;
    if (Number(fields[key]) !== derived[key]) codes.add("counts_drift");
  }

  // The live T02 summary must agree with the rows it summarises, so a silently
  // changed matrix cannot be papered over by the checkpoint prose.
  const summary = observation.summary && typeof observation.summary === "object" ? observation.summary : {};
  const summaryVerdicts =
    summary.machine_verdict_counts && typeof summary.machine_verdict_counts === "object"
      ? summary.machine_verdict_counts
      : {};
  if (
    Number(summary.finding_count) !== derived.findings_total ||
    Number(summary.rows_rereverified) !== derived.rereverified_rows ||
    Number(summary.class_matched_rows) !== derived.class_match_compatibility_rows ||
    Number(summary.class_mismatched_rows) !== derived.class_mismatch_rows ||
    Number(summaryVerdicts[RC28_EXACT_MATCH_VERDICT]) !== derived.exact_class_matched_verdict_rows
  ) {
    codes.add("matrix_summary_drift");
  }

  // The digest namespaces must be bound to their own live bytes and agree with
  // the T02 declaration. A source digest placed in the packet field (or the
  // reverse) is a namespace confusion, not a cosmetic slip.
  const source = digest.source_content_sha256;
  const packet = digest.packet_file_sha256;
  const declared = digest.packet_declared_content_sha256;
  const sourceBound = source === digest.live_source_content_sha256 && source === digest.matrix_source_content_sha256;
  const packetBound = packet === digest.live_packet_file_sha256 && packet === digest.matrix_packet_file_sha256;
  const declaredBound = declared === digest.matrix_packet_declared_content_sha256 && declared === source;
  if (!sourceBound || !packetBound || !declaredBound || source === packet) codes.add("digest_namespace_confused");

  // F13: the prior S02 owner defer and the current RC28 ledger slot are separate
  // namespaces. The prior defer exists and must not be denied; the current RC28
  // slot is still empty and must not be read as the prior defer.
  const priorDecision = String(fields.f13_prior_owner_decision || "");
  const currentDisposition = String(fields.f13_current_rc28_disposition || "");
  if (
    !RC28_PRIOR_DECISION_PATTERN.test(priorDecision) ||
    priorDecision.includes(FORBIDDEN_PRIOR_DEFER_LITERAL) ||
    text.includes(FORBIDDEN_PRIOR_DEFER_LITERAL)
  ) {
    codes.add("prior_owner_defer_denied");
  }
  if (!RC28_CURRENT_DISPOSITION_PATTERN.test(currentDisposition) || RC28_PRIOR_DECISION_PATTERN.test(currentDisposition)) {
    codes.add("prior_decision_ledger_confused");
  }

  // The hold basis must be the missing dispositions, not a missing adoption.
  if (
    String(fields.hold_basis || "") !== RC28_HOLD_BASIS ||
    !RC28_ADOPTION_BASIS_PATTERN.test(String(fields.adoption_basis || "")) ||
    text.includes(FORBIDDEN_HOLD_RATIONALE)
  ) {
    codes.add("hold_basis_invalid");
  }

  return [...codes].sort();
}

export function runBattery(options = {}) {
  const execPath = options.execPath || process.execPath;
  const timeoutMs = options.timeoutMs ?? 600000;
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
    const exitCode = exitCodeOf(spawned);
    const markerMatch = output.match(CONTRACT_MARKERS[contract]);
    results.push({
      contract,
      missing: false,
      exitCode,
      signal: (spawned && spawned.signal) || null,
      pass: counts.pass || 0,
      fail: counts.fail || 0,
      markerOk: exitCode === 0 && markerMatch !== null,
      markerLine: markerMatch ? markerMatch[0] : null,
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
  // The final RC28 checkpoint is part of the battery's fail-closed surface: its
  // counts are re-derived from the live T02 rows and its digest namespaces are
  // re-hashed live. A missing or unreadable input refuses the checkpoint rather
  // than crashing the run.
  let checkpoint;
  try {
    checkpoint = validateRc28Checkpoint(observeRc28Checkpoint());
  } catch {
    checkpoint = ["checkpoint_missing"];
  }

  const failed =
    results.reduce((sum, entry) => sum + entry.fail, 0) +
    results.filter((entry) => entry.missing || entry.exitCode !== 0).length +
    regressions.filter((entry) => entry.exitCode !== 0 || entry.markerOk !== true).length +
    (checkpoint.length > 0 ? 1 : 0);
  return {
    results,
    regressions,
    checkpoint,
    contractChecks,
    regressionChecks,
    checks,
    failed,
    ok: failed === 0 && checks >= MIN_CHECKS,
  };
}

// Fail-closed validation of a battery result. Kept pure so the sibling contract
// can exercise it on mutated results and on copies loaded from a mutated
// configuration. Returns a sorted, de-duplicated code set; an empty array means
// the battery is complete and green.
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
// checkpoint_failed: the final RC28 checkpoint's own semantics are invalid.
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
    if (entry.markerOk !== true) codes.add("contract_failed");
    if (!(typeof entry.pass === "number" && entry.pass > 0)) codes.add("contract_counts_missing");
  }
  if (!(typeof result.checks === "number" && result.checks >= MIN_CHECKS)) codes.add("checks_below_floor");
  if (result.failed !== 0) codes.add("battery_failed");
  if (result.ok !== true) codes.add("battery_failed");
  if (!Array.isArray(result.checkpoint) || result.checkpoint.length > 0) codes.add("checkpoint_failed");
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
    if (entry.markerLine) process.stdout.write(`${entry.markerLine}\n`);
  }
  for (const entry of result.regressions) {
    process.stdout.write(
      `${BATTERY_REGRESSION_MARKER} ${entry.id} exit=${entry.exitCode} checks=${entry.checks} ` +
        `marker=${entry.markerOk ? "ok" : "missing"}\n`,
    );
    if (entry.markerLine) process.stdout.write(`${entry.markerLine}\n`);
  }
  process.stdout.write(
    `${BATTERY_CHECKPOINT_MARKER} ${result.checkpoint.length === 0 ? "ok" : "fail"} ` +
      `codes=${result.checkpoint.length === 0 ? "none" : result.checkpoint.join(",")}\n`,
  );

  const codes = validateBattery(result);
  if (result.ok && codes.length === 0) {
    process.stdout.write(`${BATTERY_MARKER} checks=${result.checks} failed=${result.failed}\n`);
    process.exit(0);
  }

  process.stdout.write(`${BATTERY_FAILED_MARKER} failed=${failedCount(result)}\n`);
  process.stdout.write(`${BATTERY_FAILED_CODES_MARKER} ${codes.join(",")}\n`);
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
  if (result.checkpoint.length > 0) {
    process.stdout.write(`${BATTERY_TAIL_MARKER} ${RC28_FINAL_CHECK}\n`);
    process.stdout.write(`checkpoint_codes=${result.checkpoint.join(",")}\n`);
    tailed = true;
  }
  if (!tailed) {
    // No single step is red, yet the battery is refused: the cause is the
    // aggregate (an under-floor total). Its tail is the arithmetic itself, so a
    // `M210_S04_BATTERY_TAIL` line is still emitted and the failure stays
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
