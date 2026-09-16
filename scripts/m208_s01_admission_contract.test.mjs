// M208/S01 admission checkpoint contract (T01).
//
// Offline, subprocess-free (except `git ls-files` for tracked-file proof) and
// fail-closed: the real admission document must validate, and every named
// fail-closed case must be provable against a mutated copy of that document.
//
// Run: node --test scripts/m208_s01_admission_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ADMISSION_DOC = "prd/architecture/m208-s01-runtime-admission.md";
const CONTRACT_PATH = "scripts/m208_s01_admission_contract.test.mjs";

const BASELINE_GATES = ["G01", "G02", "G14"];
const REQUESTED_ROW_GATES = ["G05", "G11", "G12", "G13"];
const ALL_D388_GATES = Array.from({ length: 16 }, (_, i) => `G${String(i + 1).padStart(2, "0")}`);

const M205_MATRIX = "prd/architecture/m205-s01-pullenti-matrix.yaml";
const M205_S04_PIN = "prd/architecture/m205-s04-docs-reconciliation.yaml";
const M206_ADOPTION_STATES = [
  "prd/architecture/m206-s01-adoption-state.md",
  "prd/architecture/m206-s02-adoption-state.md",
  "prd/architecture/m206-s03-adoption-state.md",
  "prd/architecture/m206-s04-adoption-state.md",
];

const CHANGE_FAMILY_ROWS = [
  "PC-C-OWNER",
  "PC-C-KIND",
  "PC-C-CHILD",
  "PC-C-VALUE",
  "PC-C-PARAM",
  "PC-C-LOCVALUE",
  "PC-C-value-kind",
  "PC-C-no-auto-reinterpret",
];

const M208_RUNTIME_SURFACES = [
  "crates/ln-decode/src/change_operand.rs",
  "crates/ln-decode/src/change_operation.rs",
  "crates/ln-decode/tests/npa_change_operand_contract.rs",
  "crates/ln-decode/tests/npa_change_operand_hostile_contract.rs",
  "crates/ln-decode/tests/npa_change_operation_contract.rs",
  "crates/ln-decode/tests/npa_change_operation_hostile_contract.rs",
  "scripts/m208_s01_change_battery.test.mjs",
  "prd/migration/rust-evidence/m208-s01-change-battery.json",
  "crates/ln-decode/tests/m208_frozen_surface_guard.rs",
  "scripts/m208_s01_t05_verify.sh",
];

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

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

const INTERACTION_RE = /interaction\s+[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const LOCK_RE = /d499|gsd_milestone_lock/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b|\bPASS\b/;

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateAdmission(doc) {
  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  const verdictLines = doc.match(/^\*\*admission: .*\*\*$/gm) || [];
  const verdictMatch = doc.match(/^\*\*admission: (granted|not-adopted)\*\*$/m);
  if (verdictLines.length === 0 || !verdictMatch) add("verdict_missing", verdictLines.join(" | "));
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));
  const verdict = verdictMatch ? verdictMatch[1] : null;

  const rows = sourceRows(doc);
  if (rows.length < 6) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    if (row.path.startsWith("/") || row.path.startsWith(".gsd/")) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (!existsSync(path.join(root, row.path))) {
      add("source_unresolved", row.path);
      continue;
    }
    if (!isTracked(row.path)) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (sha256(row.path) !== row.sha) add("source_hash_mismatch", row.path);
  }

  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  const allowedSelected = verdict === "granted" ? [...BASELINE_GATES, ...REQUESTED_ROW_GATES] : [...BASELINE_GATES];
  for (const gate of selected) {
    if (!allowedSelected.includes(gate)) add("gate_outside_selected_baseline", gate);
  }
  const expectedDeferred = ALL_D388_GATES.filter((gate) => !selected.includes(gate));
  if (!sameSet(deferred, expectedDeferred)) {
    add("gate_deferred_mismatch", `deferred=${deferred.join(",")}`);
  }
  for (const gate of requested) {
    if (!deferred.includes(gate)) add("requested_gate_not_deferred", gate);
  }

  const runtimeStop = headerValue(doc, "runtime_stop") || "";
  const runtimeWork = headerValue(doc, "runtime_work") || "";
  if (verdict === "not-adopted") {
    if (/\blifted\b/i.test(runtimeStop)) add("runtime_stop_inverted", runtimeStop);
    if (!/remains active/i.test(runtimeStop)) add("runtime_stop_claim_missing", runtimeStop);
    if (!runtimeWork.startsWith("not-started")) add("no_start_directive_missing", runtimeWork);
  }

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

  for (const section of ["## Owning surfaces", "## Non-claims", "## Fail-closed boundary"]) {
    if (!doc.includes(section)) add("section_missing", section);
  }
  if (!doc.includes(CONTRACT_PATH)) add("contract_reference_missing", CONTRACT_PATH);

  return { ok: errors.length === 0, verdict, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
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

// T03 no-start note guard: the five local change operations stay design-only
// names while the verdict is not-adopted, and their runtime surfaces stay absent.
const T03_NOTE_HEADING = "## T03 no-start note: five local change operations";
const T03_OPERATIONS = ["Replace", "NewWording", "Insert", "Remove", "Repeal"];
const T03_PROVENANCE = ["f436a10e", "532e9062", "D503"];
const T03_FORBIDDEN_RUNTIME = [
  "crates/ln-decode/src/change_operation.rs",
  "crates/ln-decode/tests/npa_change_operation_contract.rs",
];

function t03NoteErrors(text) {
  const note = section(text, T03_NOTE_HEADING);
  if (!note) return ["t03_note_missing"];
  const errors = [];
  for (const operation of T03_OPERATIONS) {
    if (!note.includes(`\`${operation}\``)) errors.push("t03_operation_missing");
  }
  for (const ref of T03_PROVENANCE) {
    if (!note.includes(ref)) errors.push("t03_provenance_missing");
  }
  if (!note.includes("kind_not_runtime")) errors.push("t03_pin_citation_missing");
  if (!/`Remove` is \*\*not\*\* `Expire`/.test(note)) errors.push("t03_remove_expire_merged");
  for (const file of T03_FORBIDDEN_RUNTIME) {
    if (existsSync(path.join(root, file))) errors.push("t03_runtime_surface_present");
  }
  return errors;
}

// T04 no-start note guard: the hostile KIND-rewrite contour (missing operands
// stay IncompleteBecause) stays design-only while the verdict is not-adopted, and
// its hostile suite must stay absent.
const T04_NOTE_HEADING = "## T04 no-start note: hostile IncompleteBecause contour";
const T04_PROVENANCE = ["f436a10e", "532e9062", "D503", "RC28-F13"];
const T04_KIND_REWRITE_INVARIANT = "missing_operand_is_IncompleteBecause_without_KIND_rewrite";
const T04_DEFERRED_SENTINEL = "hostile_proof: deferred";
const T04_FORBIDDEN_RUNTIME = [
  "crates/ln-decode/tests/npa_change_operation_hostile_contract.rs",
  "crates/ln-decode/src/change_operation.rs",
];

function t04NoteErrors(text) {
  const note = section(text, T04_NOTE_HEADING);
  if (!note) return ["t04_note_missing"];
  const errors = [];
  for (const ref of T04_PROVENANCE) {
    if (!note.includes(ref)) errors.push("t04_provenance_missing");
  }
  if (!note.includes(T04_KIND_REWRITE_INVARIANT)) errors.push("t04_kind_rewrite_rule_missing");
  if (!note.includes(T04_DEFERRED_SENTINEL)) errors.push("t04_proof_not_deferred");
  if (!note.includes("`IncompleteBecause`")) errors.push("t04_incomplete_because_missing");
  for (const file of T04_FORBIDDEN_RUNTIME) {
    if (existsSync(path.join(root, file))) errors.push("t04_runtime_surface_present");
  }
  return errors;
}

// T05 no-start note guard: the slice proof battery and the frozen-surface guard
// stay unstarted while the verdict is not-adopted, no contract or milestone-lock
// PASS is re-labelled as runtime proof, and the M200/M201 frozen evidence
// artifacts stay untouched in the worktree.
const T05_NOTE_HEADING = "## T05 no-start note: no battery, no frozen-surface guard, no runtime proof";
const T05_PROVENANCE = ["f436a10e", "532e9062", "D503", "RC28-F13"];
const T05_BATTERY_SENTINEL = "battery_proof: deferred";
const T05_FROZEN_SENTINEL = "frozen_surface_proof: deferred";
const T05_CLAIM_SENTINELS = [
  ["runtime_proof: not-claimed", "t05_runtime_proof_claimed"],
  ["verify_marker: unreachable", "t05_marker_reachable_claim"],
  ["contract_pass_is_not_runtime_proof: true", "t05_contract_pass_as_runtime_proof"],
  ["lock_is_not_runtime_proof: true", "t05_lock_as_runtime_proof"],
];
const T05_SURFACES = [
  "scripts/m208_s01_change_battery.test.mjs",
  "prd/migration/rust-evidence/m208-s01-change-battery.json",
  "crates/ln-decode/tests/m208_frozen_surface_guard.rs",
  "scripts/m208_s01_t05_verify.sh",
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

function unmodifiedFrozenArtifacts(paths) {
  try {
    const status = execFileSync("git", ["status", "--porcelain", "--", ...paths], {
      cwd: root,
      encoding: "utf8",
    });
    return status.trim() === "";
  } catch {
    return false;
  }
}

function t05NoteErrors(text) {
  const note = section(text, T05_NOTE_HEADING);
  if (!note) return ["t05_note_missing"];
  const errors = [];
  for (const ref of T05_PROVENANCE) {
    if (!note.includes(ref)) errors.push("t05_provenance_missing");
  }
  if (!note.includes(T05_BATTERY_SENTINEL)) errors.push("t05_battery_proof_not_deferred");
  if (!note.includes(T05_FROZEN_SENTINEL)) errors.push("t05_frozen_surface_proof_not_deferred");
  for (const [token, code] of T05_CLAIM_SENTINELS) {
    if (!note.includes(token)) errors.push(code);
  }
  if (/runtime_proof:\s*(claimed|proven|passed|pass)\b/i.test(note)) {
    errors.push("t05_runtime_proof_claimed");
  }
  if (/verify_marker:\s*(emitted|reachable)\b/i.test(note)) {
    errors.push("t05_marker_reachable_claim");
  }
  for (const surface of T05_SURFACES) {
    if (!note.includes(`\`${surface}\``)) errors.push("t05_surface_citation_missing");
  }
  for (const file of T05_SURFACES) {
    if (existsSync(path.join(root, file))) errors.push("t05_runtime_surface_present");
  }
  return errors;
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const doc = readRepo(ADMISSION_DOC);

function fixture(mutate) {
  const next = mutate(doc);
  assert.notEqual(next, doc, "fixture mutation did not modify the document");
  return next;
}

function expectCode(text, expected) {
  const result = validateAdmission(text);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

const STRIP_SOURCE_ROWS = /^\| `[^`]+` \| `[0-9a-f]{64}` \|.*$\n?/gm;
const YAML_ONLY_ROWS = [
  `| \`${M205_MATRIX}\` | \`${"0".repeat(64)}\` | pin |`,
  `| \`${M205_S04_PIN}\` | \`${"0".repeat(64)}\` | pin |`,
  `| \`prd/architecture/m205-s03-context-fsm.yaml\` | \`${"0".repeat(64)}\` | pin |`,
  `| \`prd/architecture/operation-registry.yaml\` | \`${"0".repeat(64)}\` | registry |`,
  `| \`prd/architecture/npa-document-context.yaml\` | \`${"0".repeat(64)}\` | owner |`,
  `| \`prd/architecture/npa-semantic-process.yaml\` | \`${"0".repeat(64)}\` | owner |`,
].join("\n");

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M208 S01 admission checkpoint is valid, byte-bound and fail-closed", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  assert.ok(sourceRows(doc).length >= 6, "checkpoint must cite at least six byte-bound sources");
});

test("M208 S01 admission verdict is unambiguous and not-adopted", () => {
  const result = validateAdmission(doc);
  assert.equal(result.verdict, "not-adopted");
  assert.equal((doc.match(/^\*\*admission: /gm) || []).length, 1, "exactly one verdict line");
  assert.match(doc, /^\*\*owner_admission_ref:\*\* none$/m);
  assert.match(doc, /^\*\*runtime_work:\*\* not-started$/m);
});

test("M208 S01 gate partition selects only the admitted baseline", () => {
  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  assert.deepEqual([...selected].sort(), [...BASELINE_GATES].sort());
  assert.deepEqual([...requested].sort(), [...REQUESTED_ROW_GATES].sort());
  for (const gate of requested) assert.ok(deferred.includes(gate), `${gate} must stay deferred`);
  assert.equal(selected.length + deferred.length, ALL_D388_GATES.length);
  assert.deepEqual(
    [...deferred].sort(),
    [...ALL_D388_GATES.filter((gate) => !selected.includes(gate))].sort(),
  );
});

test("M205 pins keep the Change-family rows pending and unedited", () => {
  const matrix = readRepo(M205_MATRIX);
  for (const row of CHANGE_FAMILY_ROWS) {
    assert.ok(matrix.includes(`id: ${row}`), `${row} must exist in the M205 matrix`);
  }
  assert.ok(
    (matrix.match(/human_adoption: pending/g) || []).length >= CHANGE_FAMILY_ROWS.length,
    "every Change-family row must keep human_adoption: pending",
  );
  const m208Unblocking = matrix
    .split("\n")
    .filter((line) => line.includes("unblocks: [S03, M208]"))
    .map((line) => (line.match(/id: (PC-C-[a-zA-Z-]+)/) || [])[1]);
  assert.deepEqual(
    [...m208Unblocking].sort(),
    ["PC-C-KIND", "PC-C-OWNER", "PC-C-VALUE"],
    "only OWNER/KIND/VALUE unblock M208",
  );
  assert.ok(matrix.includes("lifecycle: [proposed]"), "pins stay proposed");
  assert.match(readRepo(M205_S04_PIN), /^runtime_stop_active: true$/m);
  assert.match(readRepo(M205_S04_PIN), /^human_adoption: pending$/m);
});

test("M206 runtime_stop_active records are not inverted", () => {
  assert.match(readRepo(M206_ADOPTION_STATES[1]), /^\*\*runtime_stop_active: true\*\*$/m);
  assert.match(readRepo(M206_ADOPTION_STATES[2]), /^\*\*runtime_stop_active: true\*\*$/m);
  assert.match(readRepo(M206_ADOPTION_STATES[3]), /^\*\*runtime_stop_active: true\*\*$/m);
  for (const state of M206_ADOPTION_STATES) {
    const text = readRepo(state);
    assert.ok(text.includes("runtime_stop_active: true"), `${state} keeps the stop active`);
    assert.ok(!/runtime_stop_active:\s*false/.test(text), `${state} must not invert the stop`);
  }
  assert.ok(
    !/\*\*runtime_stop_active: false\*\*/.test(doc),
    "the M208 checkpoint must not declare M206's stop inverted",
  );
});

test("no M208 runtime surface exists while the verdict is not-adopted", () => {
  for (const surface of M208_RUNTIME_SURFACES) {
    assert.equal(existsSync(path.join(root, surface)), false, `${surface} must not exist yet`);
  }
  const lib = readRepo("crates/ln-decode/src/lib.rs");
  assert.ok(!lib.includes("change_operand"), "lib.rs must not register change_operand");
  assert.ok(!lib.includes("change_operation"), "lib.rs must not register change_operation");
});

// ---------------------------------------------------------------------------
// fail-closed negatives
// ---------------------------------------------------------------------------

test("negative: missing verdict", () => {
  expectCode(fixture((text) => text.replace("**admission: not-adopted**", "**admission_state: pending**")), "verdict_missing");
});

test("negative: ambiguous verdict", () => {
  expectCode(
    fixture((text) => text.replace("**admission: not-adopted**", "**admission: not-adopted**\n**admission: granted**")),
    "verdict_ambiguous",
  );
});

test("negative: insufficient byte-bound sources", () => {
  expectCode(fixture((text) => text.replace(STRIP_SOURCE_ROWS, "")), "sources_insufficient");
});

test("negative: unresolvable and untracked source references", () => {
  expectCode(
    fixture((text) => text.replace(`| \`${M205_MATRIX}\` |`, "| `prd/architecture/m205-does-not-exist.yaml` |")),
    "source_unresolved",
  );
  expectCode(
    fixture((text) =>
      text.replace(`| \`${M205_MATRIX}\` |`, "| `.gsd/phases/208-wrz6fg-temporal/208-01-PLAN.md` |"),
    ),
    "source_not_tracked",
  );
});

test("negative: sha256 mismatch against the live source content", () => {
  expectCode(
    fixture((text) => text.replace(sha256(M205_MATRIX), "0".repeat(64))),
    "source_hash_mismatch",
  );
});

test("negative: adoption minted from pins alone", () => {
  const text = fixture((source) =>
    source
      .replace("**admission: not-adopted**", "**admission: granted**")
      .replace(
        "**admission_basis:** No source-bound owner admission covering RC28-F13\n(amendment operands and the Change operation alphabet) for M208/S01 exists in\nthe tracked repository; every owning pin keeps `human_adoption: pending`, and the\nonly admitted runtime scope recorded for this area (RC28-F06..F12, M206/S05-S07)\ndoes not include F13.",
        "**admission_basis:** the Change-family pin rows unblock M208 and the design matrix declares the vocabulary.",
      )
      .replace(`**owner_admission_ref:** none`, "**owner_admission_ref:** derived from the pin")
      .replace(STRIP_SOURCE_ROWS, `${YAML_ONLY_ROWS}\n`),
  );
  expectCode(text, "self_minted_adoption");
  expectCode(text, "owner_admission_ref_missing");
});

test("negative: integrity/pass and lock cannot substitute for an admission", () => {
  const granted = (basis) =>
    fixture((source) =>
      source
        .replace("**admission: not-adopted**", "**admission: granted**")
        .replace(
          "**admission_basis:** No source-bound owner admission covering RC28-F13\n(amendment operands and the Change operation alphabet) for M208/S01 exists in\nthe tracked repository; every owning pin keeps `human_adoption: pending`, and the\nonly admitted runtime scope recorded for this area (RC28-F06..F12, M206/S05-S07)\ndoes not include F13.",
          `**admission_basis:** ${basis}`,
        ),
    );
  expectCode(granted("M206 runtime battery integrity PASS authorises M208/S01."), "integrity_pass_as_admission");
  expectCode(
    granted("D499 GSD_MILESTONE_LOCK authorises M208/S01 (interaction 00000000-0000-0000-0000-000000000000)."),
    "lock_as_admission",
  );
});

test("negative: gate outside the admitted set and broken partition", () => {
  expectCode(
    fixture((source) =>
      source
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
    fixture((source) =>
      source.replace(
        "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16",
        "**deferred_d388_gates:** G03, G04, G05",
      ),
    ),
    "gate_deferred_mismatch",
  );
});

test("negative: runtime_stop inversion and missing no-start directive", () => {
  expectCode(
    fixture((source) =>
      source.replace(
        "**runtime_stop:** remains active for M208/S01; this record lifts runtime_stop for\nno scope.",
        "**runtime_stop:** lifted for M208/S01 by this record.",
      ),
    ),
    "runtime_stop_inverted",
  );
  expectCode(
    fixture((source) => source.replace("**runtime_work:** not-started", "**runtime_work:** admitted for T02-T05")),
    "no_start_directive_missing",
  );
});

test("negative: missing required section and contract reference", () => {
  expectCode(fixture((source) => source.replace("## Non-claims", "## Nonclaims")), "section_missing");
  expectCode(
    fixture((source) => source.replaceAll(CONTRACT_PATH, "scripts/m208_s01_other.test.mjs")),
    "contract_reference_missing",
  );
});

test("T02: quoted operand no-start note holds while the verdict is not-adopted", () => {
  const result = validateAdmission(doc);
  // A later slice may supersede this checkpoint with a granted admission; the
  // no-start note and its absences only hold under the not-adopted verdict.
  if (result.verdict !== "not-adopted") return;
  assert.match(doc, /^## T02 no-start note: quoted operand contour$/m);
  for (const ref of ["f436a10e", "532e9062", "D503"]) {
    assert.ok(doc.includes(ref), `the T02 note must cite ${ref}`);
  }
  assert.ok(doc.includes("match_quoted_enum"), "the T02 note must state match_quoted_enum is not reused");
  for (const file of [
    "crates/ln-decode/src/change_operand.rs",
    "crates/ln-decode/src/change_operation.rs",
    "crates/ln-decode/tests/npa_change_operand_contract.rs",
    "crates/ln-decode/tests/npa_change_operand_hostile_contract.rs",
  ]) {
    assert.equal(existsSync(path.join(root, file)), false, `${file} must stay absent`);
  }
});

test("T03: five local change operations stay design-only while the verdict is not-adopted", () => {
  const result = validateAdmission(doc);
  // A later slice may supersede this checkpoint with a granted admission; the
  // T03 no-start note and its absences only hold under the not-adopted verdict.
  if (result.verdict !== "not-adopted") return;
  const errors = t03NoteErrors(doc);
  assert.deepEqual(errors, [], `T03 note errors: ${JSON.stringify(errors)}`);
  const lib = readRepo("crates/ln-decode/src/lib.rs");
  assert.ok(!lib.includes("change_operation"), "lib.rs must not register change_operation");
});

test("negative: T03 no-start note and its absences are genuinely checked", () => {
  const result = validateAdmission(doc);
  if (result.verdict !== "not-adopted") return;
  assert.deepEqual(t03NoteErrors(doc), [], "the live document must pass the T03 guard");
  assert.ok(
    t03NoteErrors(doc.replace(T03_NOTE_HEADING, "## T03 note dropped")).includes("t03_note_missing"),
    "a dropped T03 note must fail closed",
  );
  assert.ok(
    t03NoteErrors(doc.replaceAll("`Repeal`", "Repeal")).includes("t03_operation_missing"),
    "an unnamed design-only operation must fail closed",
  );
  assert.ok(
    t03NoteErrors(doc.replaceAll("`Remove` is **not** `Expire`", "`Remove` is the `Expire` kind")).includes(
      "t03_remove_expire_merged",
    ),
    "mixing Remove with Expire must fail closed",
  );
  assert.ok(
    t03NoteErrors(doc.replace("`kind_not_runtime: [MicroOperation", "`kind_runtime: [MicroOperation")).includes(
      "t03_pin_citation_missing",
    ),
    "dropping the kind_not_runtime citation must fail closed",
  );
  assert.ok(
    t03NoteErrors(doc.replaceAll("f436a10e", "00000000")).includes("t03_provenance_missing"),
    "dropping the T03 provenance must fail closed",
  );
});

test("T05: no-start battery and frozen-surface guard stay absent while the verdict is not-adopted", () => {
  const result = validateAdmission(doc);
  // A later slice may supersede this checkpoint with a granted admission; the
  // T05 no-start note and its absences only hold under the not-adopted verdict.
  if (result.verdict !== "not-adopted") return;
  assert.deepEqual(t05NoteErrors(doc), [], `T05 note errors: ${JSON.stringify(t05NoteErrors(doc))}`);
  for (const surface of T05_SURFACES) {
    assert.equal(existsSync(path.join(root, surface)), false, `${surface} must stay absent`);
  }
  for (const artifact of M200_M201_FROZEN_ARTIFACTS) {
    assert.ok(isTracked(artifact), `${artifact} must stay tracked`);
  }
  assert.ok(
    unmodifiedFrozenArtifacts(M200_M201_FROZEN_ARTIFACTS),
    "the M200/M201 frozen evidence artifacts must stay unmodified in the worktree",
  );
  const contractSource = readRepo(CONTRACT_PATH);
  assert.ok(
    !/console\.log\(\s*["'`]M208_S01_VERIFY_OK/.test(contractSource),
    "the checkpoint contract must never emit M208_S01_VERIFY_OK",
  );
});

test("T04: hostile IncompleteBecause contour stays not-started while the verdict is not-adopted", () => {
  const result = validateAdmission(doc);
  // A later slice may supersede this checkpoint with a granted admission; the
  // T04 no-start note and its absences only hold under the not-adopted verdict.
  if (result.verdict !== "not-adopted") return;
  const errors = t04NoteErrors(doc);
  assert.deepEqual(errors, [], `T04 note errors: ${JSON.stringify(errors)}`);
  assert.equal(
    existsSync(path.join(root, "crates/ln-decode/tests/npa_change_operation_hostile_contract.rs")),
    false,
    "the hostile operation suite must stay absent until RC28-F13 is admitted",
  );
});

test("negative: T04 no-start note and its deferred proof are genuinely checked", () => {
  const result = validateAdmission(doc);
  if (result.verdict !== "not-adopted") return;
  assert.deepEqual(t04NoteErrors(doc), [], "the live document must pass the T04 guard");
  assert.ok(
    t04NoteErrors(doc.replace(T04_NOTE_HEADING, "## T04 note dropped")).includes("t04_note_missing"),
    "a dropped T04 note must fail closed",
  );
  assert.ok(
    t04NoteErrors(doc.replaceAll(T04_KIND_REWRITE_INVARIANT, "missing_operand_is_ContextIncomplete")).includes(
      "t04_kind_rewrite_rule_missing",
    ),
    "dropping the KIND-rewrite invariant must fail closed",
  );
  assert.ok(
    t04NoteErrors(doc.replace(T04_DEFERRED_SENTINEL, "hostile_proof: proven")).includes("t04_proof_not_deferred"),
    "claiming a proven hostile contour must fail closed",
  );
  assert.ok(
    t04NoteErrors(doc.replaceAll("RC28-F13", "RC28-F06")).includes("t04_provenance_missing"),
    "dropping the RC28-F13 provenance must fail closed",
  );
  assert.ok(
    t04NoteErrors(doc.replaceAll("`IncompleteBecause`", "IncompleteBecause")).includes(
      "t04_incomplete_because_missing",
    ),
    "dropping the IncompleteBecause citation must fail closed",
  );
});

test("negative: T05 no-start note and its deferred proofs are genuinely checked", () => {
  const result = validateAdmission(doc);
  if (result.verdict !== "not-adopted") return;
  assert.deepEqual(t05NoteErrors(doc), [], "the live document must pass the T05 guard");
  assert.ok(
    t05NoteErrors(doc.replace(T05_NOTE_HEADING, "## T05 note dropped")).includes("t05_note_missing"),
    "a dropped T05 note must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replace(T05_BATTERY_SENTINEL, "battery_proof: proven")).includes(
      "t05_battery_proof_not_deferred",
    ),
    "claiming a proven battery must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replace(T05_FROZEN_SENTINEL, "frozen_surface_proof: proven")).includes(
      "t05_frozen_surface_proof_not_deferred",
    ),
    "claiming a proven frozen-surface guard must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replace("runtime_proof: not-claimed", "runtime_proof: claimed")).includes(
      "t05_runtime_proof_claimed",
    ),
    "claiming runtime proof must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replace("verify_marker: unreachable", "verify_marker: emitted")).includes(
      "t05_marker_reachable_claim",
    ),
    "claiming the verify marker is reachable must fail closed",
  );
  assert.ok(
    t05NoteErrors(
      doc.replace("contract_pass_is_not_runtime_proof: true", "contract_pass_is_not_runtime_proof: false"),
    ).includes("t05_contract_pass_as_runtime_proof"),
    "reading a contract PASS as runtime proof must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replace("lock_is_not_runtime_proof: true", "lock_is_not_runtime_proof: false")).includes(
      "t05_lock_as_runtime_proof",
    ),
    "reading the D499 lock as runtime proof must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replaceAll("f436a10e", "00000000")).includes("t05_provenance_missing"),
    "dropping the T05 provenance must fail closed",
  );
  assert.ok(
    t05NoteErrors(doc.replaceAll("`scripts/m208_s01_t05_verify.sh`", "the t05 runner")).includes(
      "t05_surface_citation_missing",
    ),
    "dropping a T05 surface citation must fail closed",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the checkpoint contract holds)
// ---------------------------------------------------------------------------

test("M208 S01 checkpoint markers", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.verdict, "not-adopted");
  console.log("M208_S01_ADMISSION_OK");
  console.log(`admission_verdict=${result.verdict}`);
  console.log("M208_S01_ADMISSION_NOT_GRANTED");
  console.log("M208_S01_GATES_OK");
  console.log("M208_S01_T05_NO_START_OK");
});
