// M209 S04 T05 contract: the requirement acceptance ledger (D430, D416, D540,
// D558, D561).
//
// The contract is offline. It never imports the module's derivation to obtain
// the expected answer: the committed ledger, the T03 gate adjudication, the T04
// scope adjudication, the T01/T02 corroboration artifacts and the S01 punkt
// checkpoint are parsed here independently, the aggregates are re-tallied from
// the rows, and the carried gate/leg rows are compared byte-for-byte against
// their upstream artifacts. On top of that it asserts the documented
// fail-closed block is exactly the emitted one (each code fires on a mutated
// in-memory copy), that the committed artifact is byte-identical to the live
// re-derivation, and that the Rust boundary guard exists and stays semantic
// (include_str!, no raw sha256 pin) as D561 requires.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  ACCEPTANCE_DECISION,
  ADMISSIONS_PATH,
  ARTIFACT_PATH,
  CORPUS_RECOUNT_PATH,
  CORROBORATION_PATH,
  DECISION,
  DISPOSITION_VOCABULARY,
  EDITION_RECONCILIATION_PATH,
  FAIL_CLOSED_CODES,
  GATE_ADJUDICATION_PATH,
  GATE_ORDER,
  LEG_ORDER,
  PUNKT_CHECKPOINT_PATH,
  PUNKT_GRANT_FIELDS,
  REQUIRED_OWNER_DECISION_KINDS,
  RUST_GUARD_PATH,
  SCHEMA,
  SCOPE_ADJUDICATION_PATH,
  S03_SCOPE_LEDGER_PATH,
  acceptanceBundle,
  assertAllChecksPass,
  assertAsciiOnly,
  assertInputPins,
  assertNoRawText,
  assertNonEmpty,
  assertRepoRelative,
  assertRowSet,
  checkRenderedBytes,
  isTrackedPath,
  loadInputs,
  loadJsonArtifact,
  renderEvidence,
  resolveOutTarget,
  sha256Pin,
  validateBundle,
  validateCarriedRow,
  validateCorpusVerification,
  validateDebtItem,
  validateEditionReconciliation,
  validateOwnerDecisions,
  validatePromotionCounters,
  validateProofPackages,
  validatePunkt,
  validateRequirement,
} from "./m209_s04_acceptance_ledger.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MODULE_PATH = "scripts/m209_s04_acceptance_ledger.mjs";
const CONTRACT_PATH = "scripts/m209_s04_acceptance_contract.test.mjs";
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The heartbeat the milestone closeout greps for. The required run must appear
// contiguously in the CLI output.
const EXPECTED_HEARTBEAT =
  "gates=7 legs=4 gates_promoted=0 legs_promoted=0 proof_packages=0 requirement_mutations=0 punkt_rows=0 punkt_rows_live=0 drift=0 cross=24 failed=0 mode=ledger";

// The documented fail-closed vocabulary, transcribed independently of the
// module. A silent expansion of the module's list must fail this test.
const DOCUMENTED_CODES = Object.freeze([
  "aggregate_mismatch",
  "artifact_empty",
  "carried_row_drift",
  "corpus_verification_failed",
  "cross_check_failed",
  "debt_dropped_for_hold_row",
  "debt_not_carried",
  "debt_record_incomplete",
  "disposition_upgraded",
  "edition_partition_broken",
  "evidence_drift",
  "input_absent",
  "input_artifact_shape_invalid",
  "input_hash_mismatch",
  "input_not_tracked",
  "missing_gate_row",
  "missing_leg_row",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "owner_decision_dropped",
  "owner_decision_incomplete",
  "path_not_repository_relative",
  "promotion_claimed",
  "proof_package_claimed",
  "punkt_admission_upgraded",
  "punkt_row_minted",
  "raw_text_leak",
  "requirement_status_changed",
  "silently_dropped_edition",
  "unsupported_disposition",
]);

// Required non-claim fragments: the ledger may not close, promote or claim.
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "this-ledger-closes-and-promotes-no-requirement",
  "requirement-records-are-not-mutated",
  "bounded-scope-acceptance-is-not-validation",
  "punkt-is-not-admitted",
  "gate-g015-requires-an-owner-decision",
  "dispositions-are-carried-not-re-derived",
  "no-proof-package-is-attached",
  "rust-boundary-guard-is-semantic-not-a-digest-freeze",
  "edition-reconciliation-is-carried-whole",
  "count-only-ascii-only-and-repository-relative",
];

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(ROOT, relative), "utf8");
}

function readJson(relative) {
  return JSON.parse(readRepo(relative));
}

const ARTIFACT = readJson(ARTIFACT_PATH);
const T03 = readJson(GATE_ADJUDICATION_PATH);
const T04 = readJson(SCOPE_ADJUDICATION_PATH);
const RECONCILIATION = readJson(EDITION_RECONCILIATION_PATH);
const CORROBORATION = readJson(CORROBORATION_PATH);
const RECOUNT = readJson(CORPUS_RECOUNT_PATH);

const HOLD_GATE = ARTIFACT.gates.find((row) => row.disposition === "hold-with-precise-debt");
const HOLD_LEG = ARTIFACT.legs.find((row) => row.scope_disposition === "hold-with-precise-debt");
const OPEN_LEG = ARTIFACT.legs.find(
  (row) => row.scope_disposition === "accepted-at-bounded-scope",
);

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("artifact is canonical one-line ASCII count-only evidence", () => {
  const raw = readRepo(ARTIFACT_PATH);
  assert.equal(raw.endsWith("\n"), true, "the artifact ends with one newline");
  assert.equal(raw.trimEnd().includes("\n"), false, "the artifact is one canonical line");
  assert.equal(/^[\u0000-\u007f]*$/.test(raw), true, "the artifact is ASCII-only");

  assert.equal(ARTIFACT.schema, SCHEMA);
  assert.equal(ARTIFACT.lifecycle, "[bounded]");
  assert.equal(ARTIFACT.authoritative, false);
  assert.equal(ARTIFACT.count_only, true);
  assert.equal(ARTIFACT.ascii_only, true);
  assert.equal(ARTIFACT.decision, DECISION);
  assert.equal(ARTIFACT.acceptance_decision, ACCEPTANCE_DECISION);
});

test("the nine declared inputs are pinned to live bytes and tracked", () => {
  assert.equal(ARTIFACT.inputs.length, 9);
  const seen = new Set();
  for (const input of ARTIFACT.inputs) {
    assert.equal(seen.has(input.input_id), false, `duplicate input ${input.input_id}`);
    seen.add(input.input_id);
    const live = readRepo(input.relative_path);
    const bytes = Buffer.byteLength(live, "utf8");
    assert.equal(bytes, input.bytes, `${input.relative_path}: byte count is recomputed`);
    const digest = sha256Pin(live);
    assert.equal(digest, input.sha256, `${input.relative_path}: sha256 is recomputed`);
    assert.equal(input.sha256.startsWith("sha256:"), true);
    assert.equal(isTrackedPath(input.relative_path), true, `${input.relative_path} is tracked`);
  }
  assert.deepEqual(
    [...seen].sort(),
    [
      "corpus_recount_evidence",
      "corroboration_evidence",
      "edition_coverage_reconciliation",
      "kb_hierarchy_registry_admissions",
      "punkt_decision_checkpoint",
      "r035_gate_adjudication",
      "r035_gate_register",
      "r070_scope_adjudication",
      "s03_r070_scope_ledger",
    ],
    "all nine declared inputs are named",
  );
});

test("documented fail-closed vocabulary equals the emitted one", () => {
  assert.deepEqual([...FAIL_CLOSED_CODES].sort(), [...DOCUMENTED_CODES].sort());
  assert.deepEqual([...ARTIFACT.fail_closed_codes].sort(), [...DOCUMENTED_CODES].sort());
  assert.deepEqual(
    [...ARTIFACT.disposition_vocabulary].sort(),
    [...DISPOSITION_VOCABULARY].sort(),
  );
});

test("non-claims bound the artifact", () => {
  const joined = ARTIFACT.non_claims.join("\n").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.equal(joined.includes(fragment), true, `non-claims must carry ${fragment}`);
  }
  assert.equal(joined.includes("d540"), true, "non-claims name the punkt decision");
  assert.equal(joined.includes("d558"), true, "non-claims name the acceptance rule");
  assert.equal(joined.includes("d561"), true, "non-claims name the boundary guard rule");
});

// ---------------------------------------------------------------------------
// independent aggregate audit
// ---------------------------------------------------------------------------

function tally(rows, key) {
  const counts = { "accepted-at-bounded-scope": 0, "hold-with-precise-debt": 0 };
  counts["hold-requires-owner-decision"] = 0;
  counts["rejected-as-stated"] = 0;
  let debt = 0;
  let empty = 0;
  for (const row of rows) {
    assert.equal(
      DISPOSITION_VOCABULARY.includes(row[key]),
      true,
      `${row[key]} is outside the D558 vocabulary`,
    );
    counts[row[key]] += 1;
    const records = row.debt;
    assert.equal(Array.isArray(records) && records.length > 0, true, "every row keeps its debt");
    if (records.length === 0) empty += 1;
    debt += records.length;
  }
  return { counts, debt, empty };
}

test("the aggregate partition is re-tallied from the rows, not read from the totals", () => {
  assert.equal(ARTIFACT.gates.length, 7, "exactly seven gate rows");
  assert.equal(ARTIFACT.legs.length, 4, "exactly four leg rows");
  assert.deepEqual(
    ARTIFACT.gates.map((row) => row.gate_id),
    [...GATE_ORDER],
  );
  assert.deepEqual(
    ARTIFACT.legs.map((row) => row.leg_id),
    [...LEG_ORDER],
  );

  const gates = tally(ARTIFACT.gates, "disposition");
  const legs = tally(ARTIFACT.legs, "scope_disposition");
  const r035 = ARTIFACT.requirements.find((row) => row.requirement_id === "R035");
  const r070 = ARTIFACT.requirements.find((row) => row.requirement_id === "R070");

  assert.equal(gates.counts["accepted-at-bounded-scope"], 0, "no R035 gate is accepted");
  assert.equal(gates.counts["hold-with-precise-debt"], 6);
  assert.equal(gates.counts["hold-requires-owner-decision"], 1);
  assert.equal(gates.counts["rejected-as-stated"], 0);
  assert.equal(
    gates.counts["accepted-at-bounded-scope"] +
      gates.counts["hold-with-precise-debt"] +
      gates.counts["hold-requires-owner-decision"] +
      gates.counts["rejected-as-stated"],
    ARTIFACT.gates.length,
    "the gate partition sums to the gate count",
  );
  assert.equal(legs.counts["accepted-at-bounded-scope"], 3, "three R070 legs are accepted");
  assert.equal(legs.counts["hold-with-precise-debt"], 1, "one R070 leg stays on hold");
  assert.equal(
    legs.counts["accepted-at-bounded-scope"] +
      legs.counts["hold-with-precise-debt"] +
      legs.counts["hold-requires-owner-decision"] +
      legs.counts["rejected-as-stated"],
    ARTIFACT.legs.length,
    "the leg partition sums to the leg count",
  );
  assert.equal(ARTIFACT.gate_count, ARTIFACT.gates.length);
  assert.equal(ARTIFACT.leg_count, ARTIFACT.legs.length);
  assert.equal(ARTIFACT.debt_total, gates.debt + legs.debt, "the debt total is re-summed");
  assert.equal(ARTIFACT.empty_debt_rows, 0);

  assert.equal(r035.status, "active");
  assert.equal(r035.disposition_decision, "D430");
  assert.equal(r035.gates_total, ARTIFACT.gates.length);
  assert.equal(r035.gates_accepted, gates.counts["accepted-at-bounded-scope"]);
  assert.equal(r035.gates_hold, gates.counts["hold-with-precise-debt"]);
  assert.equal(r035.gates_owner_decision, gates.counts["hold-requires-owner-decision"]);
  assert.equal(r035.gates_rejected, gates.counts["rejected-as-stated"]);
  assert.equal(r035.promotion, "none");

  assert.equal(r070.status, "active");
  assert.equal(r070.disposition_decision, "D416");
  assert.equal(r070.legs_total, ARTIFACT.legs.length);
  assert.equal(r070.accepted_at_bounded_scope, legs.counts["accepted-at-bounded-scope"]);
  assert.equal(r070.hold, legs.counts["hold-with-precise-debt"]);
  assert.equal(r070.coverage_verdict, "incomplete-because-not-every-edition");
  assert.equal(r070.promotion, "none");
});

test("nothing is promoted, attached or mutated", () => {
  assert.equal(ARTIFACT.gates_promoted, 0);
  assert.equal(ARTIFACT.legs_promoted, 0);
  assert.equal(ARTIFACT.proof_packages_attached, 0);
  assert.equal(ARTIFACT.requirement_records_mutated, 0);
  for (const row of ARTIFACT.gates) {
    assert.equal(row.proof_package, null, `${row.gate_id} attaches no proof package`);
  }
  for (const check of ARTIFACT.cross_checks) {
    assert.equal(check.verdict, "pass", `${check.check_id} must pass`);
  }
  assert.equal(ARTIFACT.counted.cross_checks_failed, 0);
  assert.equal(ARTIFACT.counted.cross_checks_total, ARTIFACT.cross_checks.length);
});

// ---------------------------------------------------------------------------
// carried rows, edition reconciliation, punkt
// ---------------------------------------------------------------------------

test("every gate row and every leg row is carried from T03/T04 without smoothing", () => {
  assert.equal(T03.gate_count, 7);
  assert.equal(T04.leg_count, 4);
  for (const row of ARTIFACT.gates) {
    const upstream = T03.gates.find((candidate) => candidate.gate_id === row.gate_id);
    assert.notEqual(upstream, undefined, `${row.gate_id} exists upstream`);
    assert.equal(
      JSON.stringify(row),
      JSON.stringify(upstream),
      `${row.gate_id} is carried byte-for-byte`,
    );
    assert.equal(row.disposition, upstream.disposition, "the disposition is copied, not re-derived");
    assert.equal(JSON.stringify(row.debt), JSON.stringify(upstream.debt), "the debt is copied");
  }
  for (const row of ARTIFACT.legs) {
    const upstream = T04.legs.find((candidate) => candidate.leg_id === row.leg_id);
    assert.notEqual(upstream, undefined, `${row.leg_id} exists upstream`);
    assert.equal(JSON.stringify(row), JSON.stringify(upstream), `${row.leg_id} is carried`);
    assert.equal(row.scope_disposition, upstream.scope_disposition);
    assert.equal(JSON.stringify(row.debt), JSON.stringify(upstream.debt));
  }
  assert.equal(HOLD_LEG.leg_id, "commencement-and-transitional", "the hold leg is named");
  assert.equal(HOLD_GATE.disposition, "hold-with-precise-debt");
  assert.equal(OPEN_LEG.scope_disposition, "accepted-at-bounded-scope");
});

test("the edition reconciliation partitions 118 editions with zero silently dropped", () => {
  const summary = ARTIFACT.edition_reconciliation;
  assert.equal(summary.editions_total, 118);
  assert.equal(summary.classes_total, 118);
  assert.equal(summary.class_sum, 118);
  assert.equal(summary.silently_dropped_total, 0);
  const byClass = new Map(summary.classes.map((entry) => [entry.class_id, entry.count]));
  assert.equal(byClass.get("core-act-initial-edition"), 1);
  assert.equal(byClass.get("amending-act-date-matched"), 117);
  assert.equal(
    summary.classes.reduce((total, entry) => total + entry.count, 0),
    summary.editions_total,
    "the class partition sums to the inventory",
  );
  for (const residual of summary.residuals) {
    assert.equal(typeof residual.residual_id === "string" && residual.residual_id !== "", true);
    assert.equal(typeof residual.count, "number");
  }
  assert.equal(summary.residual_unnamed_total, 0, "every residual carries a named reason code");

  // Independently confirmed against the live T02 reconciliation artifact.
  assert.equal(RECONCILIATION.editions_total, 118);
  assert.equal(RECONCILIATION.residual_unnamed_total, 0);
  assert.deepEqual(
    RECONCILIATION.classes.map((entry) => entry.count),
    [1, 117],
    "the T02 class partition is 1 + 117",
  );
  assert.equal(RECONCILIATION.residuals.length, 3);
});

test("the corpus verification summary carries the T01/T02 counters, all zero-failure", () => {
  const summary = ARTIFACT.corpus_verification;
  assert.equal(summary.corroboration_artifact, CORROBORATION_PATH);
  assert.equal(summary.corpus_recount_artifact, CORPUS_RECOUNT_PATH);
  for (const key of [
    "bindings_failed",
    "digests_failed",
    "arithmetic_failed",
    "cross_artifact_failed",
    "frozen_boundary_failed",
    "recount_cross_checks_failed",
    "recount_promotion_checks_failed",
    "window_mismatches_total",
    "editions_unaccepted_total",
  ]) {
    assert.equal(summary[key], 0, `${key} must be zero`);
  }
  assert.equal(summary.editions_files_total, 118);
  assert.equal(summary.editions_accepted_total, 118);
  assert.equal(summary.bindings_total, CORROBORATION.bindings_total);
  assert.equal(summary.bindings_passed, CORROBORATION.bindings_passed);
  assert.equal(summary.bindings_failed, CORROBORATION.bindings_failed);
  assert.equal(summary.digests_total, CORROBORATION.digests_total);
  assert.equal(summary.recount_cross_checks_total, RECOUNT.cross_checks.length);
  assert.equal(summary.recount_cross_checks_failed, 0);
});

test("punkt stays not-adopted with zero admitted rows and twelve grant fields", () => {
  const punkt = ARTIFACT.punkt;
  assert.equal(punkt.admission, "not-adopted");
  assert.equal(punkt.punkt_admission, "not-adopted");
  assert.equal(punkt.punkt_rows_admitted, 0);
  assert.equal(punkt.live_punkt_rows_admitted, 0);
  assert.equal(punkt.owner_admission_ref, "none");
  assert.equal(punkt.decision, "D540");
  assert.equal(punkt.status, "unchanged");
  assert.equal(punkt.checkpoint_path, PUNKT_CHECKPOINT_PATH);
  assert.deepEqual([...punkt.required_grant_fields], [...PUNKT_GRANT_FIELDS]);
  assert.equal(punkt.required_grant_fields.length, 12);

  // Independently re-read from the checkpoint markdown and the live admissions.
  const checkpoint = readRepo(PUNKT_CHECKPOINT_PATH);
  assert.equal(/^\*\*admission: not-adopted\*\*$/m.test(checkpoint), true);
  assert.equal(/^\*\*punkt_admission:\*\*\s*not-adopted\s*$/m.test(checkpoint), true);
  assert.equal(/^\*\*punkt_rows_admitted:\*\*\s*0\s*$/m.test(checkpoint), true);
  assert.equal(/^\*\*owner_admission_ref:\*\*\s*none\s*$/m.test(checkpoint), true);
  assert.equal(checkpoint.includes("D540"), true);
  const admissions = readRepo(ADMISSIONS_PATH);
  assert.equal((admissions.match(/level:\s*punkt\b/g) ?? []).length, 0, "no live punkt row");
});

test("the outstanding owner decisions are carried with unblock conditions", () => {
  const kinds = ARTIFACT.owner_decisions_outstanding.map((owner) => owner.kind);
  for (const required of REQUIRED_OWNER_DECISION_KINDS) {
    assert.equal(kinds.includes(required), true, `${required} is carried`);
  }
  for (const owner of ARTIFACT.owner_decisions_outstanding) {
    assert.equal(typeof owner.description === "string" && owner.description !== "", true);
    assert.equal(typeof owner.unblock_condition === "string" && owner.unblock_condition !== "", true);
    assert.equal(Array.isArray(owner.evidence_paths) && owner.evidence_paths.length > 0, true);
    for (const relative of owner.evidence_paths) {
      assert.ok(!path.isAbsolute(relative), `${relative} is repository-relative`);
      assert.equal(existsSync(path.join(ROOT, relative)), true, `${relative} exists`);
    }
  }
  assert.equal(ARTIFACT.acceptance_rule_reconciliation.includes("superset"), true);
});

// ---------------------------------------------------------------------------
// module agreement and boundary guard
// ---------------------------------------------------------------------------

test("artifact rows survive the module's own row and bundle validation", () => {
  assert.equal(validateBundle(ARTIFACT), true);
});

test("the committed artifact is byte-identical to the live re-derivation", () => {
  const bundle = acceptanceBundle({});
  const rendered = renderEvidence(bundle);
  assert.equal(checkRenderedBytes(rendered, readRepo(ARTIFACT_PATH)), true);
  assert.equal(assertNonEmpty(rendered), true);
  assert.equal(assertAsciiOnly(rendered), true);
  assert.equal(assertNoRawText(rendered), true);
});

test("CLI --check is drift-free and prints the required heartbeat", () => {
  const stdout = execFileSync("node", [MODULE_PATH, "--check"], {
    cwd: ROOT,
    encoding: "utf8",
  });
  assert.equal(stdout.includes(EXPECTED_HEARTBEAT), true, stdout);
  const tail = execFileSync("node", [MODULE_PATH, "--check"], { cwd: ROOT, encoding: "utf8" });
  assert.equal(tail.trimEnd().endsWith(EXPECTED_HEARTBEAT), true, tail);
});

test("the Rust boundary guard is semantic and pins no ledger digest (D561)", () => {
  const guard = readRepo(RUST_GUARD_PATH);
  assert.equal(
    guard.includes(`include_str!("../../../prd/migration/rust-evidence/m209-s04-requirement-acceptance.json")`),
    true,
    "the guard compiles the ledger in",
  );
  assert.equal(/sha256:[0-9a-f]{64}/.test(guard), false, "no raw sha256 pin in Rust");
  assert.equal(/(^|[^0-9a-f])[0-9a-f]{64}([^0-9a-f]|$)/m.test(guard), false, "no bare digest");
  assert.equal(guard.includes("#[test]"), true, "the guard carries executed tests");
  assert.equal(guard.includes("fn check_boundary"), true, "the guard carries a semantic predicate");
  assert.equal(
    guard.includes("DISPOSITIONS") || guard.includes("DISPOSITION"),
    true,
    "the guard carries the closed D558 vocabulary",
  );
});

test("the module stays offline, dependency-free and never shells out to a build tool", () => {
  const source = readRepo(MODULE_PATH);
  const specifiers = [...source.matchAll(/from "([^"]+)"/g)].map((match) => match[1]);
  assert.ok(specifiers.length > 0, "the module imports something");
  for (const specifier of specifiers) {
    assert.equal(
      specifier.startsWith("node:") || specifier.startsWith("."),
      true,
      `unexpected import ${specifier}`,
    );
  }
  assert.equal(source.includes("fetch("), false);
  assert.equal(/execFileSync\("(cargo|python)/.test(source), false);
  assert.equal(/\brequire\(/.test(source), false);
});

// ---------------------------------------------------------------------------
// negative cases: every documented fail-closed code fires
// ---------------------------------------------------------------------------

const LOADED_INPUTS = loadInputs();
const firstInputId = Object.keys(LOADED_INPUTS)[0];

function expectCode(code, fn) {
  try {
    fn();
  } catch (error) {
    assert.equal(error.code, code, `${code}: raised ${String(error.code)} (${error.message})`);
    return;
  }
  assert.fail(`expected ${code} to be raised`);
}

const NEGATIVE_CASES = {
  aggregate_mismatch: () => validateBundle({ ...ARTIFACT, gate_count: 6 }),
  artifact_empty: () => assertNonEmpty(""),
  carried_row_drift: () =>
    validateCarriedRow({ ...HOLD_GATE, safe_bucket: "mutated" }, HOLD_GATE, "gate"),
  corpus_verification_failed: () =>
    validateCorpusVerification({ ...ARTIFACT.corpus_verification, bindings_failed: 1 }),
  cross_check_failed: () => assertAllChecksPass([{ check_id: "mutated", verdict: "fail" }]),
  debt_dropped_for_hold_row: () => validateCarriedRow({ ...HOLD_GATE, debt: [] }, HOLD_GATE, "gate"),
  debt_not_carried: () => validateCarriedRow({ ...OPEN_LEG, debt: [] }, OPEN_LEG, "leg"),
  debt_record_incomplete: () => validateDebtItem({}),
  disposition_upgraded: () =>
    validateCarriedRow(
      { ...HOLD_GATE, disposition: "accepted-at-bounded-scope" },
      HOLD_GATE,
      "gate",
    ),
  edition_partition_broken: () =>
    validateEditionReconciliation({ ...ARTIFACT.edition_reconciliation, classes: [] }),
  evidence_drift: () => checkRenderedBytes("a", "b"),
  input_absent: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-absent-ledger-input.json", "absent"),
  input_artifact_shape_invalid: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-broken-ledger-input.json", "broken", {
      existsSync: () => true,
      readFileSync: () => "{",
    }),
  input_hash_mismatch: () =>
    assertInputPins(
      { ...LOADED_INPUTS, [firstInputId]: { ...LOADED_INPUTS[firstInputId], sha256: "sha256:dead" } },
      { isTracked: () => true },
    ),
  input_not_tracked: () => assertInputPins(LOADED_INPUTS, { isTracked: () => false }),
  missing_gate_row: () => assertRowSet(GATE_ORDER.slice(0, 6), GATE_ORDER, "gate"),
  missing_leg_row: () => assertRowSet(LEG_ORDER.slice(0, 3), LEG_ORDER, "leg"),
  non_ascii_evidence: () => assertAsciiOnly("\u00e9"),
  out_absolute: () => resolveOutTarget("/tmp/m209-s04-ledger.json"),
  out_not_evidence_path: () => resolveOutTarget(MODULE_PATH),
  out_of_repo_out: () =>
    resolveOutTarget(ARTIFACT_PATH, {
      existsSync: () => true,
      realpathSync: (value) => (value === ROOT ? ROOT : "/tmp/outside-m209"),
      lstatSync: () => ({ isSymbolicLink: () => false }),
    }),
  out_symlink_target: () =>
    resolveOutTarget(ARTIFACT_PATH, {
      existsSync: () => true,
      realpathSync: (value) => value,
      lstatSync: () => ({ isSymbolicLink: () => true }),
    }),
  owner_decision_dropped: () =>
    validateOwnerDecisions(
      ARTIFACT.owner_decisions_outstanding.filter(
        (owner) => owner.kind !== "gate-g015-recorded-conflict",
      ),
    ),
  owner_decision_incomplete: () =>
    validateOwnerDecisions(
      REQUIRED_OWNER_DECISION_KINDS.map((kind) => ({
        kind,
        description: "",
        unblock_condition: "named",
        evidence_paths: [PUNKT_CHECKPOINT_PATH],
      })),
    ),
  path_not_repository_relative: () => assertRepoRelative("../escaped.json", "escaped"),
  promotion_claimed: () => validatePromotionCounters({ ...ARTIFACT, gates_promoted: 1 }),
  proof_package_claimed: () =>
    validateProofPackages({
      ...ARTIFACT,
      gates: [{ ...HOLD_GATE, proof_package: {} }, ...ARTIFACT.gates.slice(1)],
    }),
  punkt_admission_upgraded: () => validatePunkt({ ...ARTIFACT.punkt, admission: "granted" }),
  punkt_row_minted: () => validatePunkt({ ...ARTIFACT.punkt, punkt_rows_admitted: 1 }),
  raw_text_leak: () => assertNoRawText("consultantplus://document"),
  requirement_status_changed: () =>
    validateRequirement({ ...ARTIFACT.requirements[0], status: "validated" }),
  silently_dropped_edition: () =>
    validateEditionReconciliation({
      ...ARTIFACT.edition_reconciliation,
      silently_dropped_total: 1,
    }),
  unsupported_disposition: () =>
    validateCarriedRow({ ...HOLD_GATE, disposition: "validated" }, HOLD_GATE, "gate"),
};

test("every documented fail-closed code fires on a mutated copy", () => {
  assert.deepEqual(Object.keys(NEGATIVE_CASES).sort(), [...DOCUMENTED_CODES].sort());
  for (const [code, fn] of Object.entries(NEGATIVE_CASES)) expectCode(code, fn);
});

test("row-set, disposition and promotion mutations are rejected by name", () => {
  expectCode("missing_gate_row", () => assertRowSet([...GATE_ORDER].slice(0, 6), GATE_ORDER, "gate"));
  expectCode("missing_leg_row", () => assertRowSet([...LEG_ORDER].slice(0, 3), LEG_ORDER, "leg"));
  expectCode("disposition_upgraded", () =>
    validateCarriedRow(
      { ...HOLD_GATE, disposition: "accepted-at-bounded-scope" },
      { ...HOLD_GATE, disposition: "validated" },
      "gate",
    ),
  );
  expectCode("debt_dropped_for_hold_row", () =>
    validateCarriedRow({ ...HOLD_GATE, debt: [] }, HOLD_GATE, "gate"),
  );
  expectCode("proof_package_claimed", () =>
    validateProofPackages({ ...ARTIFACT, proof_packages_attached: 1 }),
  );
  expectCode("requirement_status_changed", () =>
    validateRequirement({ ...ARTIFACT.requirements[1], status: "complete" }),
  );
  expectCode("punkt_row_minted", () =>
    validatePunkt({ ...ARTIFACT.punkt, live_punkt_rows_admitted: 1 }),
  );
  expectCode("promotion_claimed", () => validatePromotionCounters({ ...ARTIFACT, legs_promoted: 1 }));
});

// The contract file itself must not sit in an ignored overlay.
test("the contract reads only tracked evidence paths", () => {
  assert.equal(readRepo(CONTRACT_PATH).length > 0, true);
  for (const relative of [
    ARTIFACT_PATH,
    GATE_ADJUDICATION_PATH,
    SCOPE_ADJUDICATION_PATH,
    EDITION_RECONCILIATION_PATH,
    CORROBORATION_PATH,
    CORPUS_RECOUNT_PATH,
    PUNKT_CHECKPOINT_PATH,
    ADMISSIONS_PATH,
    S03_SCOPE_LEDGER_PATH,
    RUST_GUARD_PATH,
  ]) {
    assert.ok(!path.isAbsolute(relative), `${relative} is repository-relative`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.equal(relative.startsWith(prefix), false, `${relative} is not in ${prefix}`);
    }
  }
});
