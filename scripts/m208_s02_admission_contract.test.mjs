// M208/S02 admission checkpoint contract (T03).
//
// Offline and fail-closed: the real admission record must validate, and every
// named fail-closed case must be provable against a mutated copy of that record
// (or an injected filesystem view), so the suite cannot fool itself by asserting
// codes it would never actually emit.
//
// Subprocesses are limited to `git ls-files` (tracked-file proof) and
// `git status --porcelain` (frozen-scope proof). No cargo, no network, and no
// `.gsd` / ignored / absolute path is ever read as evidence.
//
// Run: node --test scripts/m208_s02_admission_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ADMISSION_DOC = "prd/architecture/m208-s02-nested-target-admission.md";
const CONTRACT_PATH = "scripts/m208_s02_admission_contract.test.mjs";
const S01_CONTRACT_PATH = "scripts/m208_s01_admission_contract.test.mjs";
const S01_DOC = "prd/architecture/m208-s01-runtime-admission.md";

const BASELINE_GATES = ["G01", "G02", "G14"];
const REQUESTED_ROW_GATES = ["G05", "G11", "G12", "G13"];
const ALL_D388_GATES = Array.from({ length: 16 }, (_, i) => `G${String(i + 1).padStart(2, "0")}`);
const MIN_SOURCES = 8;

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const M205_MATRIX = "prd/architecture/m205-s01-pullenti-matrix.yaml";
const M205_S03_PIN = "prd/architecture/m205-s03-context-fsm.yaml";
const M205_S04_PIN = "prd/architecture/m205-s04-docs-reconciliation.yaml";
const M205_PINS = [M205_MATRIX, M205_S03_PIN, M205_S04_PIN];
const M205_RUNTIME_STOP_PINS = [M205_S03_PIN, M205_S04_PIN];

const LIB_RS = "crates/ln-decode/src/lib.rs";
const LIB_REGISTRATION_RE = /^\s*(?:pub\s+)?mod\s+change_target\s*;/m;

// Declared S02 runtime surfaces: the declared scope of absence. None of these
// may exist while the verdict is `not-adopted`.
const S02_RUNTIME_SURFACES = [
  "crates/ln-decode/src/change_target.rs",
  "crates/ln-decode/tests/npa_change_target_contract.rs",
  "crates/ln-decode/tests/npa_change_target_hostile_contract.rs",
  "scripts/m208_s02_nested_target_battery.test.mjs",
  "prd/migration/rust-evidence/m208-s02-nested-target-battery.json",
  "crates/ln-decode/tests/m208_s02_frozen_surface_guard.rs",
  "scripts/m208_s02_t04_verify.sh",
];

// Inherited S01 runtime surfaces: not re-scoped by this record, still absent.
const S01_RUNTIME_SURFACES = [
  "crates/ln-decode/src/change_operand.rs",
  "crates/ln-decode/src/change_operation.rs",
];

const M200_M201_FROZEN_ARTIFACTS = [
  "prd/migration/rust-evidence/m200-s01-scanner-fixture-gate.json",
  "prd/migration/rust-evidence/m200-s02-corpus-acceptance.json",
  "prd/migration/rust-evidence/m200-s02-corpus-smoke-rate.json",
  "prd/migration/rust-evidence/m200-s02-npa-bounds-scan.jsonl",
  "prd/migration/rust-evidence/m200-s03-outlier-review.json",
  "prd/migration/rust-evidence/m200-s04-contract-reconciliation.json",
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
];

const FROZEN_SCOPE = [
  ...M200_M201_FROZEN_ARTIFACTS,
  ...M205_PINS,
  "doc/adr/0028-typed-lexer-legal-marker-lexicon.md",
  "prd/ARCHITECTURE.md",
  S01_DOC,
];

const REQUIRED_SECTIONS = [
  "## Sources checked",
  "## Owning surfaces",
  "## Non-claims",
  "## Fail-closed boundary",
  "## Marker semantics",
  "## Resume condition",
];

// The complete fail-closed code set. The record's `## Fail-closed boundary`
// table is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "verdict_missing",
  "verdict_ambiguous",
  "sources_insufficient",
  "source_unresolved",
  "source_not_tracked",
  "source_hash_mismatch",
  "ignored_path_as_source",
  "self_minted_adoption",
  "owner_admission_ref_missing",
  "integrity_pass_as_admission",
  "lock_as_admission",
  "s01_basis_not_adopted",
  "gate_outside_selected_baseline",
  "gate_deferred_mismatch",
  "runtime_stop_inverted",
  "no_start_directive_missing",
  "section_missing",
  "contract_reference_missing",
  "s02_surface_present",
  "s01_surface_present",
  "lib_rs_registration_present",
  "runtime_proof_claimed",
  "verify_marker_reachable_claim",
  "contract_pass_as_runtime_proof",
  "lock_as_runtime_proof",
  "s01_contract_missing",
  "t02_note_missing",
];

const T02_NOTE_HEADINGS = [
  "## T02 no-start note: nested change target and nesting depth",
  "## T02 no-start note: amending-act scope binding and sibling / quote anti-leakage",
  "## T02 no-start note: no hostile contour, no battery, no runtime proof",
];
const T02_PROVENANCE = ["f436a10e", "532e9062", "D503", "D504"];
const T02_REQUIRED_TOKENS = [
  "keep-nested",
  "cross-occurrence",
  "scope_container_id",
  "ContextConflict",
  "hostile_proof: deferred",
  "runtime_work: not-started",
];

const RUNTIME_CLAIM_SENTINELS = [
  ["runtime_proof: not-claimed", "runtime_proof_claimed"],
  ["verify_marker: unreachable", "verify_marker_reachable_claim"],
  ["contract_pass_is_not_runtime_proof: true", "contract_pass_as_runtime_proof"],
  ["lock_is_not_runtime_proof: true", "lock_as_runtime_proof"],
];

const INTERACTION_RE =
  /interaction\s+[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const LOCK_RE = /d499|gsd_milestone_lock/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b|\bPASS\b/;

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
}

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function sha256(relativePath) {
  return createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex");
}

function isTracked(relativePath) {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: root,
      stdio: ["ignore", "ignore", "ignore"],
    });
    return true;
  } catch {
    return false;
  }
}

// `git status --porcelain` restricted to the frozen scope: an empty result means
// none of those tracked artifacts carries a worktree delta.
function worktreeDelta(paths) {
  try {
    return execFileSync("git", ["status", "--porcelain", "--", ...paths], {
      cwd: root,
      encoding: "utf8",
    }).trim();
  } catch {
    return "git status failed";
  }
}

// ---------------------------------------------------------------------------
// document parsing helpers
// ---------------------------------------------------------------------------

function headerValue(doc, key) {
  const lines = doc.split("\n");
  const prefix = `**${key}:**`;
  const start = lines.findIndex((line) => line.startsWith(prefix));
  if (start === -1) return null;
  const parts = [lines[start].slice(prefix.length)];
  for (let i = start + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.startsWith("**") || line.startsWith("#") || line.trim() === "") break;
    parts.push(line);
  }
  return parts.join(" ").trim();
}

function gateList(value) {
  if (!value) return [];
  return value.split(/[,\s]+/).filter((token) => /^G\d{2}$/.test(token));
}

function sameSet(a, b) {
  return a.length === b.length && a.every((item) => b.includes(item));
}

function sourceRows(doc) {
  return [...doc.matchAll(/^\| `([^`]+)` \| `([0-9a-f]{64})` \|/gm)].map((match) => ({
    path: match[1],
    sha: match[2],
  }));
}

function section(doc, heading) {
  const lines = doc.split("\n");
  const start = lines.findIndex((line) => line === heading);
  if (start === -1) return null;
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i += 1) {
    if (lines[i].startsWith("## ")) {
      end = i;
      break;
    }
  }
  return lines.slice(start, end).join("\n");
}

function verdictOf(text) {
  const lines = text.match(/^\*\*admission: .*\*\*$/gm) || [];
  const match = text.match(/^\*\*admission: (granted|not-adopted)\*\*$/m);
  return { lines, value: match ? match[1] : null };
}

// ---------------------------------------------------------------------------
// section guards
// ---------------------------------------------------------------------------

// T02 note guard: the three design-only no-start notes must stay present with
// their provenance and their design sentinels while the verdict is not-adopted.
function t02NoteErrors(text) {
  const notes = T02_NOTE_HEADINGS.map((heading) => section(text, heading));
  if (notes.some((note) => note === null)) return ["t02_note_missing"];
  const body = notes.join("\n");
  if (!T02_PROVENANCE.every((ref) => body.includes(ref))) return ["t02_note_missing"];
  if (!T02_REQUIRED_TOKENS.every((token) => body.includes(token))) return ["t02_note_missing"];
  if (!body.includes("verdict=not-adopted")) return ["t02_note_missing"];
  return [];
}

// Anti-claim guard: no runtime proof, verify marker, contract PASS or D499 lock
// may be claimed as a runtime result while the verdict is not-adopted.
function runtimeClaimErrors(text, verdict) {
  if (verdict !== "not-adopted") return [];
  const errors = [];
  for (const [token, code] of RUNTIME_CLAIM_SENTINELS) {
    if (!text.includes(token)) errors.push(code);
  }
  if (/runtime_proof:\s*(?:claimed|proven|passed|pass)\b/i.test(text)) errors.push("runtime_proof_claimed");
  if (/runtime_demo:\s*(?:proven|delivered|shipped)\b/i.test(text)) errors.push("runtime_proof_claimed");
  if (/verify_marker:\s*(?:reachable|emitted|available)\b/i.test(text)) {
    errors.push("verify_marker_reachable_claim");
  }
  if (/contract_pass_is_not_runtime_proof:\s*(?:false|no)\b/i.test(text)) {
    errors.push("contract_pass_as_runtime_proof");
  }
  if (/lock_is_not_runtime_proof:\s*(?:false|no)\b/i.test(text)) errors.push("lock_as_runtime_proof");
  return [...new Set(errors)];
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateAdmission(doc, options = {}) {
  const {
    s01Text = readRepo(S01_DOC),
    libText = readRepo(LIB_RS),
    fileExists = repoExists,
    surfaceExists = repoExists,
    s01ContractExists = repoExists(S01_CONTRACT_PATH),
  } = options;

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  // (1) verdict: at least one, at most one, and one of the two known values.
  const { lines: verdictLines, value: verdict } = verdictOf(doc);
  if (verdictLines.length === 0 || verdict === null) add("verdict_missing", verdictLines.join(" | "));
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));

  // (3) byte-bound sources: repository-relative, resolvable, tracked, hash-equal.
  const rows = sourceRows(doc);
  if (rows.length < MIN_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    if (IGNORED_SOURCE_PREFIXES.some((prefix) => row.path.startsWith(prefix))) {
      add("ignored_path_as_source", row.path);
      continue;
    }
    if (row.path.startsWith("/")) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (!fileExists(row.path)) {
      add("source_unresolved", row.path);
      continue;
    }
    if (!isTracked(row.path)) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (sha256(row.path) !== row.sha) add("source_hash_mismatch", row.path);
  }

  // (4) gate partition: selected / requested-not-selected / deferred.
  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  const allowedSelected =
    verdict === "granted" ? [...BASELINE_GATES, ...REQUESTED_ROW_GATES] : [...BASELINE_GATES];
  for (const gate of selected) {
    if (!allowedSelected.includes(gate)) add("gate_outside_selected_baseline", gate);
  }
  const expectedDeferred = ALL_D388_GATES.filter((gate) => !selected.includes(gate));
  if (!sameSet(deferred, expectedDeferred)) {
    add("gate_deferred_mismatch", `deferred=${deferred.join(",")}`);
  }
  if (verdict === "not-adopted") {
    for (const gate of requested) {
      if (!deferred.includes(gate)) add("gate_deferred_mismatch", `requested ${gate} is not deferred`);
      if (selected.includes(gate)) add("gate_deferred_mismatch", `requested ${gate} must not be selected`);
    }
    if (!sameSet(requested, REQUESTED_ROW_GATES)) {
      add("gate_deferred_mismatch", `requested=${requested.join(",")}`);
    }
  }

  // (2) not-adopted invariants: the stop stands and a no-start directive exists.
  const runtimeStop = headerValue(doc, "runtime_stop") || "";
  const runtimeWork = headerValue(doc, "runtime_work") || "";
  if (verdict === "not-adopted") {
    if (/\blifted\b/i.test(runtimeStop) || !/remains active for M208\/S02/i.test(runtimeStop)) {
      add("runtime_stop_inverted", runtimeStop);
    }
    if (!runtimeWork.startsWith("not-started")) add("no_start_directive_missing", runtimeWork);
    if (!doc.includes("**no_start_directive:**")) {
      add("no_start_directive_missing", "no_start_directive header absent");
    }
  }

  // Self-minted adoption: a grant can never be derived from pins, an integrity
  // PASS or the milestone lock.
  const basis = headerValue(doc, "admission_basis") || "";
  const ownerRef = headerValue(doc, "owner_admission_ref") || "";
  if (verdict === "granted") {
    const hasInteraction = INTERACTION_RE.test(`${basis} ${ownerRef}`);
    if (!hasInteraction) add("owner_admission_ref_missing", ownerRef);
    if (LOCK_RE.test(`${basis} ${ownerRef}`)) add("lock_as_admission", basis);
    if (INTEGRITY_RE.test(basis) && !hasInteraction) add("integrity_pass_as_admission", basis);
    if (rows.length > 0 && rows.every((row) => /\.ya?ml$/i.test(row.path))) {
      add("self_minted_adoption", rows.map((row) => row.path).join(","));
    }
  }

  // (5) required sections and the contract reference.
  for (const heading of REQUIRED_SECTIONS) {
    if (!doc.includes(heading)) add("section_missing", heading);
  }
  if (!doc.includes(CONTRACT_PATH)) add("contract_reference_missing", CONTRACT_PATH);

  // (6) S01 basis: cited among the sources and still reading `not-adopted`.
  const s01Cited = rows.some((row) => row.path === S01_DOC);
  const s01Verdict = verdictOf(s01Text).value;
  if (!s01Cited || s01Verdict !== "not-adopted") {
    add("s01_basis_not_adopted", `cited=${s01Cited} s01_verdict=${s01Verdict}`);
  }
  if (!s01ContractExists) add("s01_contract_missing", S01_CONTRACT_PATH);

  // T02 no-start notes and the anti-claim sentinels.
  for (const code of t02NoteErrors(doc)) add(code, "T02 no-start note guard");
  for (const code of runtimeClaimErrors(doc, verdict)) add(code, "runtime claim guard");

  // Machine proof of absence: no declared S02 or inherited S01 runtime surface,
  // and no `mod change_target` registration, may exist.
  for (const surface of S02_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s02_surface_present", surface);
  }
  for (const surface of S01_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s01_surface_present", surface);
  }
  if (LIB_REGISTRATION_RE.test(libText)) add("lib_rs_registration_present", LIB_RS);

  return { ok: errors.length === 0, verdict, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const doc = readRepo(ADMISSION_DOC);

// The live `admission_basis` block, byte-exact, so a granted fixture provably
// replaces it instead of silently no-oping.
const NOT_ADOPTED_BASIS = `**admission_basis:** No source-bound owner admission covering RC28-F13 (nested
amendment targets and their scope binding) for M208/S02 exists in the tracked
repository; the M208/S01 checkpoint stands at \`not-adopted\`; every owning
Change-family pin keeps \`human_adoption: pending\`. The only admitted runtime scope
recorded in this area (RC28-F06..F12, M206/S05-S07) does not include F13.`;

function fixture(mutate) {
  const next = mutate(doc);
  assert.notEqual(next, doc, "fixture mutation did not modify the document");
  return next;
}

function grantedFixture(basisText, extra) {
  assert.ok(doc.includes(NOT_ADOPTED_BASIS), "fixture basis block must match the live record");
  const next = grantedText(doc, basisText, extra);
  assert.ok(next.includes(`**admission_basis:** ${basisText}`), "fixture basis replacement failed");
  return next;
}

function grantedText(text, basisText, extra) {
  assert.ok(text.includes(NOT_ADOPTED_BASIS), "granted mutation requires the live basis block");
  let next = text.replace("**admission: not-adopted**", "**admission: granted**");
  next = next.replace(NOT_ADOPTED_BASIS, `**admission_basis:** ${basisText}`);
  return extra ? extra(next) : next;
}

function expectCode(text, expected, options) {
  const result = validateAdmission(text, options);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

const STRIP_SOURCE_ROWS = /^\| `[^`]+` \| `[0-9a-f]{64}` \|.*$\n?/gm;
const YAML_ONLY_ROWS = [
  M205_MATRIX,
  M205_S03_PIN,
  M205_S04_PIN,
  "prd/architecture/npa-document-context.yaml",
  "prd/architecture/operation-registry.yaml",
  "prd/architecture/m205-s02-pre-capture-grammar.yaml",
  "prd/architecture/npa-semantic-process.yaml",
  "prd/architecture/m206-s05-runtime-admission.yaml",
]
  .map((entry) => `| \`${entry}\` | \`${"0".repeat(64)}\` | pin |`)
  .join("\n");

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M208 S02 admission checkpoint is valid, byte-bound and fail-closed", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  assert.ok(
    sourceRows(doc).length >= MIN_SOURCES,
    `checkpoint must cite at least ${MIN_SOURCES} byte-bound sources`,
  );
});

test("M208 S02 admission verdict is unambiguous and not-adopted", () => {
  const result = validateAdmission(doc);
  assert.equal(result.verdict, "not-adopted");
  assert.equal((doc.match(/^\*\*admission: /gm) || []).length, 1, "exactly one verdict line");
  assert.match(doc, /^\*\*owner_admission_ref:\*\* none$/m);
  assert.match(doc, /^\*\*runtime_work:\*\* not-started$/m);
  assert.ok(doc.includes("runtime_demo: not-proven"), "the S02 demo stays not-proven");
  assert.equal(headerValue(doc, "contract"), CONTRACT_PATH, "the record must name its own contract");
});

test("M208 S02 sources are resolvable, tracked and hash-bound", () => {
  const rows = sourceRows(doc);
  assert.equal(rows.length, 8, "the checkpoint cites exactly eight admission sources");
  for (const row of rows) {
    assert.ok(!row.path.startsWith("/"), `${row.path} must be repository-relative`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!row.path.startsWith(prefix), `${row.path} must not be an ignored path`);
    }
    assert.ok(repoExists(row.path), `${row.path} must exist`);
    assert.ok(isTracked(row.path), `${row.path} must be tracked`);
    assert.equal(sha256(row.path), row.sha, `${row.path} must match its recorded sha256`);
  }
  assert.ok(
    rows.some((row) => row.path === S01_DOC),
    "the S01 checkpoint must be cited as the S02 admission basis",
  );
  assert.match(readRepo(S01_DOC), /^\*\*admission: not-adopted\*\*$/m);
});

test("M208 S02 gate partition selects only the not-adopted baseline", () => {
  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  assert.deepEqual([...selected].sort(), [...BASELINE_GATES].sort());
  assert.deepEqual([...requested].sort(), [...REQUESTED_ROW_GATES].sort());
  for (const gate of requested) {
    assert.ok(deferred.includes(gate), `${gate} is requested and must stay deferred`);
  }
  assert.deepEqual(
    [...deferred].sort(),
    [...ALL_D388_GATES.filter((gate) => !selected.includes(gate))].sort(),
    "deferred must be the exact complement of selected over G01..G16",
  );
});

test("the fail-closed code set is synchronized with the checkpoint record", () => {
  const table = section(doc, "## Fail-closed boundary");
  assert.ok(table, "the record must carry a Fail-closed boundary section");
  const nonCodeTokens = new Set(["runtime_stop", "granted"]);
  const documented = new Set(
    [...table.matchAll(/`([a-z][a-z0-9_]*)`/g)]
      .map((match) => match[1])
      .filter((token) => !nonCodeTokens.has(token)),
  );
  assert.deepEqual(
    [...documented].sort(),
    [...EMITTABLE_CODES].sort(),
    "the documented code set must equal the set this contract can emit",
  );
  // Every named code must be empirically reachable outside the registry array:
  // one mutation per code below must actually make it fire.
  const withoutRegistry = readRepo(CONTRACT_PATH).replace(/const EMITTABLE_CODES = \[[\s\S]*?\];/, "");
  for (const code of EMITTABLE_CODES) {
    assert.ok(
      withoutRegistry.includes(`"${code}"`),
      `${code} must be reachable in the contract body, not only in the code registry`,
    );
  }
});

test("M205 pins keep the Change-family rows pending and the stop active", () => {
  const matrix = readRepo(M205_MATRIX);
  assert.ok(
    (matrix.match(/human_adoption: pending/g) || []).length >= 8,
    "every Change-family row must keep human_adoption: pending",
  );
  assert.ok(matrix.includes("lifecycle: [proposed]"), "matrix rows stay proposed");
  assert.ok(matrix.includes("authoritative: false"), "the matrix stays non-authoritative");
  for (const pin of M205_PINS) {
    assert.ok(readRepo(pin).includes("human_adoption: pending"), `${pin} keeps adoption pending`);
  }
  for (const pin of M205_RUNTIME_STOP_PINS) {
    assert.match(readRepo(pin), /^runtime_stop_active: true$/m, `${pin} keeps the runtime stop`);
  }
});

test("no M208/S02 or inherited S01 runtime surface exists while not-adopted", () => {
  for (const surface of [...S02_RUNTIME_SURFACES, ...S01_RUNTIME_SURFACES]) {
    assert.equal(repoExists(surface), false, `${surface} must not exist yet`);
  }
  const lib = readRepo(LIB_RS);
  assert.ok(!LIB_REGISTRATION_RE.test(lib), "lib.rs must not register mod change_target");
  assert.ok(!lib.includes("change_operand"), "lib.rs must not register change_operand");
  assert.ok(!lib.includes("change_operation"), "lib.rs must not register change_operation");
});

test("the frozen scope is tracked and carries no worktree delta", () => {
  for (const artifact of M200_M201_FROZEN_ARTIFACTS) {
    assert.ok(isTracked(artifact), `${artifact} must stay tracked`);
  }
  assert.equal(worktreeDelta(FROZEN_SCOPE), "", "the frozen scope must carry no worktree delta");
});

test("the contract never reads an ignored, .gsd or absolute path as evidence", () => {
  const source = readRepo(CONTRACT_PATH);
  const declared = [...source.matchAll(/^(?:const|let)\s+[A-Za-z_$][\w$]*\s*=\s*"([^"]+)";$/gm)].map(
    (match) => match[1],
  );
  for (const value of declared) {
    assert.ok(!value.startsWith("/"), `absolute path literal ${value} is not admissible evidence`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!value.startsWith(prefix), `ignored path literal ${value} is not admissible evidence`);
    }
  }
  for (const entry of [
    ...S02_RUNTIME_SURFACES,
    ...S01_RUNTIME_SURFACES,
    ...M205_PINS,
    ...M200_M201_FROZEN_ARTIFACTS,
    ...FROZEN_SCOPE,
  ]) {
    assert.ok(!entry.startsWith("/"), `${entry} must be repository-relative`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!entry.startsWith(prefix), `${entry} must not be an ignored path`);
    }
  }
  assert.ok(
    !/readRepo\(\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readRepo\(\s*"\//.test(source), "the contract must not read an absolute path");
});

test("the contract never emits the verify marker", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifyMarker = ["M208_S02", "VERIFY_OK"].join("_");
  const emitter = new RegExp(`console\\.log\\(\\s*["'\`]${verifyMarker}`);
  assert.ok(!emitter.test(source), `${verifyMarker} must be unreachable by construction`);
});

// ---------------------------------------------------------------------------
// fail-closed negatives
// ---------------------------------------------------------------------------

test("negative: missing verdict", () => {
  expectCode(
    fixture((text) => text.replace("**admission: not-adopted**", "**admission_state: pending**")),
    "verdict_missing",
  );
});

test("negative: ambiguous verdict", () => {
  expectCode(
    fixture((text) =>
      text.replace("**admission: not-adopted**", "**admission: not-adopted**\n**admission: granted**"),
    ),
    "verdict_ambiguous",
  );
});

test("negative: insufficient byte-bound sources", () => {
  expectCode(fixture((text) => text.replace(STRIP_SOURCE_ROWS, "")), "sources_insufficient");
});

test("negative: unresolvable, untracked, ignored and absolute source references", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        `| \`${M205_MATRIX}\` |`,
        "| `prd/architecture/m205-s02-does-not-exist.yaml` |",
      ),
    ),
    "source_unresolved",
  );
  expectCode(
    fixture((text) => text.replace(`| \`${M205_MATRIX}\` |`, "| `/tmp/m208-s02-source.md` |")),
    "source_not_tracked",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        `| \`${M205_MATRIX}\` |`,
        "| `.agents/skills/law-nexus-rust/references/verification-matrix.md` |",
      ),
    ),
    "ignored_path_as_source",
  );
  expectCode(
    fixture((text) =>
      text.replace(`| \`${M205_MATRIX}\` |`, "| `.gsd/phases/208-wrz6fg-temporal/208-02-PLAN.md` |"),
    ),
    "ignored_path_as_source",
  );
});

test("negative: sha256 mismatch against the live source content", () => {
  expectCode(
    fixture((text) => text.replace(sha256(M205_MATRIX), "0".repeat(64))),
    "source_hash_mismatch",
  );
});

test("negative: adoption minted from pins alone", () => {
  const text = grantedFixture(
    "the Change-family pin rows unblock M208 and the design matrix declares the vocabulary.",
    (next) =>
      next
        .replace("**owner_admission_ref:** none", "**owner_admission_ref:** derived from the pin")
        .replace(STRIP_SOURCE_ROWS, `${YAML_ONLY_ROWS}\n`),
  );
  expectCode(text, "self_minted_adoption");
  expectCode(text, "owner_admission_ref_missing");
});

test("negative: integrity pass and milestone lock cannot substitute for an admission", () => {
  expectCode(
    grantedFixture("M206 runtime battery integrity PASS authorises M208/S02."),
    "integrity_pass_as_admission",
  );
  expectCode(
    grantedFixture(
      "D499 GSD_MILESTONE_LOCK authorises M208/S02 (interaction 00000000-0000-0000-0000-000000000000).",
    ),
    "lock_as_admission",
  );
});

test("negative: the S01 basis must be cited and must read not-adopted", () => {
  // (a) the live S01 record superseded by a grant
  const s01Text = readRepo(S01_DOC).replace("**admission: not-adopted**", "**admission: granted**");
  expectCode(doc, "s01_basis_not_adopted", { s01Text });
  // (b) the S01 record dropped from the cited sources
  expectCode(
    fixture((text) => text.replace(`| \`${S01_DOC}\` |`, "| `prd/architecture/m206-s05-runtime-admission.md` |")),
    "s01_basis_not_adopted",
  );
});

test("negative: gate outside the admitted set and broken partition", () => {
  expectCode(
    fixture((text) =>
      text
        .replace(
          "**selected_d388_gates:** G01, G02, G14",
          "**selected_d388_gates:** G01, G02, G07, G14",
        )
        .replace(
          "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16",
          "**deferred_d388_gates:** G03, G04, G05, G06, G08, G09, G10, G11, G12, G13, G15, G16",
        ),
    ),
    "gate_outside_selected_baseline",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16",
        "**deferred_d388_gates:** G03, G04, G05",
      ),
    ),
    "gate_deferred_mismatch",
  );
  expectCode(
    fixture((text) => text.replace("**requested_not_selected_d388_gates:** G05, G11, G12, G13", "**requested_not_selected_d388_gates:** G12")),
    "gate_deferred_mismatch",
  );
});

test("negative: runtime_stop inversion and missing no-start directive", () => {
  expectCode(
    fixture((text) => text.replace("remains active for M208/S02", "lifted for M208/S02")),
    "runtime_stop_inverted",
  );
  expectCode(
    fixture((text) => text.replace("**runtime_work:** not-started", "**runtime_work:** admitted for T04")),
    "no_start_directive_missing",
  );
  expectCode(
    fixture((text) => text.replace("**no_start_directive:**", "**start_directive:**")),
    "no_start_directive_missing",
  );
});

test("negative: missing required section and contract reference", () => {
  for (const [heading, replacement] of [
    ["## Sources checked", "## Sources"],
    ["## Owning surfaces", "## Surfaces"],
    ["## Non-claims", "## Nonclaims"],
    ["## Fail-closed boundary", "## Fail-closed"],
    ["## Marker semantics", "## Markers"],
    ["## Resume condition", "## Resume"],
  ]) {
    expectCode(fixture((text) => text.replace(heading, replacement)), "section_missing");
  }
  expectCode(
    fixture((text) => text.replaceAll(CONTRACT_PATH, "scripts/m208_s02_other.test.mjs")),
    "contract_reference_missing",
  );
});

test("negative: existing S02 and inherited S01 runtime surfaces", () => {
  for (const surface of S02_RUNTIME_SURFACES) {
    expectCode(doc, "s02_surface_present", {
      surfaceExists: (candidate) => candidate === surface,
    });
  }
  for (const surface of S01_RUNTIME_SURFACES) {
    expectCode(doc, "s01_surface_present", {
      surfaceExists: (candidate) => candidate === surface,
    });
  }
});

test("negative: lib.rs registration of mod change_target", () => {
  expectCode(doc, "lib_rs_registration_present", { libText: "pub mod change_target;\n" });
  expectCode(doc, "lib_rs_registration_present", { libText: "mod change_target ;\n" });
  const live = validateAdmission(doc);
  assert.ok(
    !codes(live).includes("lib_rs_registration_present"),
    "the live lib.rs must not register mod change_target",
  );
});

test("negative: runtime proof, marker, contract-pass and lock claims", () => {
  expectCode(
    fixture((text) => text.replace("runtime_proof: not-claimed", "runtime_proof: claimed")),
    "runtime_proof_claimed",
  );
  expectCode(
    fixture((text) => text.replace("runtime_demo: not-proven", "runtime_demo: proven")),
    "runtime_proof_claimed",
  );
  expectCode(
    fixture((text) => text.replaceAll("verify_marker: unreachable", "verify_marker: reachable")),
    "verify_marker_reachable_claim",
  );
  expectCode(
    fixture((text) =>
      text.replace("contract_pass_is_not_runtime_proof: true", "contract_pass_is_not_runtime_proof: false"),
    ),
    "contract_pass_as_runtime_proof",
  );
  expectCode(
    fixture((text) => text.replace("lock_is_not_runtime_proof: true", "lock_is_not_runtime_proof: false")),
    "lock_as_runtime_proof",
  );
});

test("negative: missing inherited S01 contract", () => {
  expectCode(doc, "s01_contract_missing", { s01ContractExists: false });
});

test("negative: missing T02 no-start notes and their sentinels", () => {
  expectCode(
    fixture((text) => text.replace(T02_NOTE_HEADINGS[0], "## T02 note dropped")),
    "t02_note_missing",
  );
  expectCode(fixture((text) => text.replaceAll("keep-nested", "keep-flat")), "t02_note_missing");
  expectCode(
    fixture((text) => text.replace("hostile_proof: deferred", "hostile_proof: proven")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replaceAll("runtime_work: not-started", "runtime_work: started")),
    "t02_note_missing",
  );
  expectCode(fixture((text) => text.replaceAll("f436a10e", "00000000")), "t02_note_missing");
  expectCode(
    fixture((text) => text.replaceAll("scope_container_id", "scope_container")),
    "t02_note_missing",
  );
  expectCode(fixture((text) => text.replaceAll("cross-occurrence", "cross-span")), "t02_note_missing");
  expectCode(
    fixture((text) => text.replaceAll("`verdict=not-adopted`", "`verdict=not-granted`")),
    "t02_note_missing",
  );
  // the live record must pass the T02 guard
  assert.deepEqual(t02NoteErrors(doc), [], "the live record must satisfy the T02 guard");
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code. The test below asserts
// that each mutation actually makes its code fire, so a code can never be
// documented without being reachable, and can never be reachable without being
// documented.
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "verdict_missing",
    mutate: (text) => text.replace("**admission: not-adopted**", "**admission_state: pending**"),
  },
  {
    code: "verdict_ambiguous",
    mutate: (text) =>
      text.replace("**admission: not-adopted**", "**admission: not-adopted**\n**admission: granted**"),
  },
  { code: "sources_insufficient", mutate: (text) => text.replace(STRIP_SOURCE_ROWS, "") },
  {
    code: "source_unresolved",
    mutate: (text) =>
      text.replace(`| \`${M205_MATRIX}\` |`, "| `prd/architecture/m205-s02-missing.yaml` |"),
  },
  {
    code: "source_not_tracked",
    mutate: (text) => text.replace(`| \`${M205_MATRIX}\` |`, "| `/tmp/m208-s02-source.md` |"),
  },
  {
    code: "ignored_path_as_source",
    mutate: (text) =>
      text.replace(
        `| \`${M205_MATRIX}\` |`,
        "| `.gsd/phases/208-wrz6fg-temporal/208-02-PLAN.md` |",
      ),
  },
  {
    code: "source_hash_mismatch",
    mutate: (text) => text.replace(sha256(M205_MATRIX), "0".repeat(64)),
  },
  {
    code: "self_minted_adoption",
    mutate: (text) =>
      grantedText(text, "the M205 pins declare the vocabulary.", (next) =>
        next.replace(STRIP_SOURCE_ROWS, `${YAML_ONLY_ROWS}\n`),
      ),
  },
  {
    code: "owner_admission_ref_missing",
    mutate: (text) =>
      grantedText(text, "the owner approved the S02 scope verbally.", (next) =>
        next.replace("**owner_admission_ref:** none", "**owner_admission_ref:** verbal"),
      ),
  },
  {
    code: "integrity_pass_as_admission",
    mutate: (text) => grantedText(text, "M206 runtime battery integrity PASS authorises M208/S02."),
  },
  {
    code: "lock_as_admission",
    mutate: (text) =>
      grantedText(
        text,
        "D499 GSD_MILESTONE_LOCK authorises M208/S02 (interaction 00000000-0000-0000-0000-000000000000).",
      ),
  },
  {
    code: "s01_basis_not_adopted",
    mutate: (text) =>
      text.replace(`| \`${S01_DOC}\` |`, "| `prd/architecture/m206-s05-runtime-admission.md` |"),
  },
  {
    code: "gate_outside_selected_baseline",
    mutate: (text) =>
      text
        .replace(
          "**selected_d388_gates:** G01, G02, G14",
          "**selected_d388_gates:** G01, G02, G07, G14",
        )
        .replace(
          "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16",
          "**deferred_d388_gates:** G03, G04, G05, G06, G08, G09, G10, G11, G12, G13, G15, G16",
        ),
  },
  {
    code: "gate_deferred_mismatch",
    mutate: (text) =>
      text.replace(
        "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16",
        "**deferred_d388_gates:** G03, G04, G05",
      ),
  },
  {
    code: "runtime_stop_inverted",
    mutate: (text) => text.replace("remains active for M208/S02", "lifted for M208/S02"),
  },
  {
    code: "no_start_directive_missing",
    mutate: (text) => text.replace("**runtime_work:** not-started", "**runtime_work:** admitted"),
  },
  {
    code: "section_missing",
    mutate: (text) => text.replace("## Non-claims", "## Nonclaims"),
  },
  {
    code: "contract_reference_missing",
    mutate: (text) => text.replaceAll(CONTRACT_PATH, "scripts/m208_s02_other.test.mjs"),
  },
  {
    code: "s02_surface_present",
    options: { surfaceExists: (candidate) => candidate === S02_RUNTIME_SURFACES[0] },
  },
  {
    code: "s01_surface_present",
    options: { surfaceExists: (candidate) => candidate === S01_RUNTIME_SURFACES[0] },
  },
  { code: "lib_rs_registration_present", options: { libText: "mod change_target;\n" } },
  {
    code: "runtime_proof_claimed",
    mutate: (text) => text.replace("runtime_proof: not-claimed", "runtime_proof: claimed"),
  },
  {
    code: "verify_marker_reachable_claim",
    mutate: (text) => text.replaceAll("verify_marker: unreachable", "verify_marker: reachable"),
  },
  {
    code: "contract_pass_as_runtime_proof",
    mutate: (text) =>
      text.replace("contract_pass_is_not_runtime_proof: true", "contract_pass_is_not_runtime_proof: false"),
  },
  {
    code: "lock_as_runtime_proof",
    mutate: (text) => text.replace("lock_is_not_runtime_proof: true", "lock_is_not_runtime_proof: false"),
  },
  { code: "s01_contract_missing", options: { s01ContractExists: false } },
  {
    code: "t02_note_missing",
    mutate: (text) => text.replace(T02_NOTE_HEADINGS[0], "## T02 note dropped"),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const text = entry.mutate ? entry.mutate(doc) : doc;
    if (entry.mutate) {
      assert.notEqual(text, doc, `${entry.code}: the mutation must actually change the record`);
    }
    const result = validateAdmission(text, entry.options || {});
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the checkpoint contract holds)
// ---------------------------------------------------------------------------

test("M208 S02 checkpoint markers", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.verdict, "not-adopted");
  const surfacesPresent = [...S02_RUNTIME_SURFACES, ...S01_RUNTIME_SURFACES].filter((surface) =>
    repoExists(surface),
  ).length;
  assert.equal(surfacesPresent, 0, "runtime_surfaces_present must be 0");
  console.log("M208_S02_ADMISSION_OK");
  console.log(`admission_verdict=${result.verdict}`);
  console.log("M208_S02_ADMISSION_NOT_GRANTED");
  console.log("M208_S02_GATES_OK");
  console.log("M208_S02_NESTED_NO_START_OK");
  console.log(`runtime_surfaces_present=${surfacesPresent}`);
});
