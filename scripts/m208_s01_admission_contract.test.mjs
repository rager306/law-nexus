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
});
