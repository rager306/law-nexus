// M209 S04 T04 contract: the R070 scope-by-scope acceptance adjudication
// (D416, D539, D558).
//
// The contract is offline. It never imports the module's derivation to obtain
// the expected answer: the S03 ledger, the four leg artifacts and the frozen
// M201 gate are parsed here independently, the per-leg measurement and the
// disposition rule are repeated here from the plan text, and the S03 ledger's
// own bytes/sha256 pins are re-checked against the live files. On top of that
// it asserts the documented fail-closed block is exactly the emitted one (each
// code fires on a mutated in-memory copy) and that the committed artifact is
// byte-identical to the live re-derivation.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  AMENDING_PATH,
  ARTIFACT_PATH,
  COMMENCEMENT_PATH,
  COVERAGE_VERDICT,
  DISPOSITION_VOCABULARY,
  EDITION_DELTA_PATH,
  FAIL_CLOSED_CODES,
  LEG_ORDER,
  LEG_VERDICT_VOCABULARY,
  LEDGER_PATH,
  LEDGER_PIN,
  M201_GATE_PATH,
  M201_PIN,
  REQUIRED_EVIDENCE_CLASS,
  SCHEMA,
  adjudicationBundle,
  assertAllChecksPass,
  assertAsciiOnly,
  assertCountBindings,
  assertInputPins,
  assertLedgerShape,
  assertM201Boundary,
  assertNoRawText,
  assertNonEmpty,
  assertRepoRelative,
  assertRequiredEvidenceDeclaration,
  checkRenderedBytes,
  isRepoRelative,
  loadJsonArtifact,
  numericAt,
  renderEvidence,
  resolveDenominatorSource,
  resolveOutTarget,
  sha256Pin,
  validateBundle,
  validateDebtItem,
  validateLegRow,
} from "./m209_s04_scope_adjudication.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MODULE_PATH = "scripts/m209_s04_scope_adjudication.mjs";
const CONTRACT_PATH = "scripts/m209_s04_scope_adjudication_contract.test.mjs";
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The heartbeat the milestone closeout greps for. The required run must appear
// contiguously in the CLI output.
const EXPECTED_HEARTBEAT =
  "legs=4 accepted-bounded=3 hold=1 legs_promoted=0 coverage=incomplete-because-not-every-edition drift=0";

// The documented fail-closed vocabulary, transcribed independently of the
// module. A silent expansion of the module's list must fail this test.
const DOCUMENTED_CODES = Object.freeze([
  "artifact_empty",
  "class_matched_evidence_claimed",
  "count_binding_mismatch",
  "coverage_verdict_upgraded",
  "cross_check_failed",
  "debt_record_incomplete",
  "denominator_source_absent",
  "evidence_drift",
  "input_absent",
  "input_artifact_shape_invalid",
  "input_hash_mismatch",
  "input_not_tracked",
  "inventory_count_as_quantifier",
  "ledger_leg_set_mismatch",
  "leg_verdict_upgraded",
  "legs_promoted_nonzero",
  "m201_boundary_drift",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "path_not_repository_relative",
  "promotion_claim_present",
  "quantifier_threshold_unmet",
  "raw_text_leak",
  "required_evidence_class_absent",
  "unsupported_disposition",
]);

// Required non-claim fragments (D416, D539, D545, D558).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not-r070-validation",
  "commencement-and-transitional-remains-hold",
  "coverage-verdict-carried-not-promoted",
  "leg-verdicts-carried-verbatim",
  "m201-gate-not-widened",
  "class-matched-ids-stay-empty",
  "no-requirement-record-mutated",
  "count-only-and-ascii-only",
  "inventory-counts-are-not-quantifiers",
  "quantifier-thresholds-are-recomputed-not-read",
  "adjudication-rule-reconciliation",
  "d416",
  "d539",
  "d545",
  "d558",
];

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(ROOT, relative), "utf8");
}

function sha256OfRepoFile(relative) {
  return sha256Pin(Buffer.from(readRepo(relative), "utf8"));
}

function expectCode(code, fn) {
  let thrown = null;
  try {
    fn();
  } catch (error) {
    thrown = error;
  }
  assert.ok(thrown !== null, `expected ${code} to be raised`);
  assert.equal(thrown.code, code, `expected ${code}, got ${thrown.code}: ${thrown.detail}`);
}

// ---------------------------------------------------------------------------
// independent live parsing of the four sources
// ---------------------------------------------------------------------------

const LEDGER_RAW = readRepo(LEDGER_PATH);
const LEDGER = JSON.parse(LEDGER_RAW);
const LEDGER_LOADED = loadJsonArtifact(LEDGER_PATH, "r070 scope ledger");
const M201_LOADED = loadJsonArtifact(M201_GATE_PATH, "frozen m201 r070 proof gate");
const M201 = M201_LOADED.parsed;
const AMENDING = JSON.parse(readRepo(AMENDING_PATH));
const COMMENCEMENT = JSON.parse(readRepo(COMMENCEMENT_PATH));
const EDITION_DELTA = JSON.parse(readRepo(EDITION_DELTA_PATH));
const ARTIFACT_RAW = readRepo(ARTIFACT_PATH);
const ARTIFACT = JSON.parse(ARTIFACT_RAW);
const ARTIFACT_BY_ID = new Map(ARTIFACT.legs.map((row) => [row.leg_id, row]));
const LEDGER_BY_ID = new Map(LEDGER.legs.map((leg) => [leg.leg_id, leg]));

// The per-leg measurement contract, transcribed from the plan independently of
// the module: numerator field, denominator field, threshold and source path.
const INDEPENDENT_MEASUREMENTS = Object.freeze({
  "amending-acts": {
    source: AMENDING,
    numerator: ["denominator", "amends_edges_total"],
    denominator: ["denominator", "amends_edges_total"],
    threshold: 120,
  },
  "affected-provisions": {
    source: AMENDING,
    numerator: ["denominator", "distinct_statya_refs_resolved"],
    denominator: ["denominator", "distinct_statya_refs"],
    threshold: 26,
  },
  "commencement-and-transitional": {
    source: COMMENCEMENT,
    numerator: ["required_evidence", "class_matched_ids"],
    denominator: ["denominator", "slots_total"],
    threshold: 1,
  },
  "edition-delta": {
    source: EDITION_DELTA,
    numerator: ["denominator", "windows_total"],
    denominator: ["denominator", "editions_total"],
    threshold: 117,
  },
});

function independentMeasure(legId) {
  const rule = INDEPENDENT_MEASUREMENTS[legId];
  let numerator = rule.source;
  for (const part of rule.numerator) numerator = numerator[part];
  if (Array.isArray(numerator)) numerator = numerator.length;
  let denominator = rule.source;
  for (const part of rule.denominator) denominator = denominator[part];
  return { numerator, denominator, threshold: rule.threshold };
}

function independentDisposition(legVerdict, satisfied) {
  if (legVerdict === "slot-filled-not-proven" || satisfied !== true) return "hold-with-precise-debt";
  return "accepted-at-bounded-scope";
}

// ---------------------------------------------------------------------------
// artifact integrity and vocabulary
// ---------------------------------------------------------------------------

test("artifact is canonical one-line ASCII count-only evidence", () => {
  assertNonEmpty(ARTIFACT_RAW);
  assertAsciiOnly(ARTIFACT_RAW);
  assertNoRawText(ARTIFACT_RAW);
  assert.equal(ARTIFACT_RAW.endsWith("\n"), true);
  assert.equal(ARTIFACT_RAW.split("\n").length, 2, "artifact must be exactly one line");
  assert.equal(renderEvidence(ARTIFACT), ARTIFACT_RAW);
  assert.equal(isRepoRelative(ARTIFACT_PATH), true);
  assert.equal(assertRepoRelative(ARTIFACT_PATH, "artifact"), true);
  assert.equal(ARTIFACT.schema, SCHEMA);
  assert.equal(ARTIFACT.kind, "m209-s04-r070-scope-adjudication");
  assert.equal(ARTIFACT.milestone, "M209-2yg6ix");
  assert.equal(ARTIFACT.slice, "S04");
  assert.equal(ARTIFACT.task, "T04");
  assert.equal(ARTIFACT.lifecycle, "[bounded]");
  assert.equal(ARTIFACT.authoritative, false);
  assert.equal(ARTIFACT.count_only, true);
  assert.equal(ARTIFACT.ascii_only, true);
  assert.equal(ARTIFACT.requirement_id, "R070");
  assert.equal(ARTIFACT.disposition, "active");
  assert.equal(ARTIFACT.disposition_decision, "D416");
  assert.equal(ARTIFACT.decision, "D558");
  assert.equal(ARTIFACT.coverage_verdict, COVERAGE_VERDICT);
  assert.equal(ARTIFACT.coverage_verdict_source, "carried-verbatim-from-s03-r070-scope-ledger");
  assert.equal(ARTIFACT.leg_count, 4);
  assert.equal(ARTIFACT.legs_promoted, 0);
  assert.equal(ARTIFACT.gates_promoted, 0);
  assert.equal(ARTIFACT.proof_packages_attached, 0);
  assert.equal(ARTIFACT.requirement_records_mutated, 0);
  assert.deepEqual([...ARTIFACT.disposition_vocabulary].sort(), [...DISPOSITION_VOCABULARY].sort());
  assert.deepEqual([...ARTIFACT.leg_verdict_vocabulary].sort(), [...LEG_VERDICT_VOCABULARY].sort());
});

test("artifact paths are repository-relative", () => {
  for (const source of ARTIFACT.leg_sources) {
    assert.equal(isRepoRelative(source.relative_path), true, source.relative_path);
  }
  assert.equal(isRepoRelative(ARTIFACT.ledger_source.relative_path), true);
  assert.equal(isRepoRelative(ARTIFACT.m201_boundary.relative_path), true);
  for (const row of ARTIFACT.legs) {
    assert.equal(isRepoRelative(row.tracked_evidence.artifact_relative_path), true);
    assert.equal(isRepoRelative(row.quantifier.denominator_source_path), true);
    for (const debt of row.debt) {
      for (const relative of debt.closest_evidence.relative_paths) {
        assert.equal(isRepoRelative(relative), true, relative);
      }
      assert.ok(debt.closest_evidence.why_insufficient.length > 0);
    }
  }
  for (const owner of ARTIFACT.owner_decisions_outstanding) {
    for (const relative of owner.evidence_paths) {
      assert.equal(isRepoRelative(relative), true, relative);
    }
  }
});

test("documented fail-closed vocabulary equals the emitted one", () => {
  assert.deepEqual([...FAIL_CLOSED_CODES].sort(), [...DOCUMENTED_CODES].sort());
  assert.deepEqual([...ARTIFACT.fail_closed_codes].sort(), [...DOCUMENTED_CODES].sort());
});

test("non-claims bound the artifact (D416, D539, D545, D558)", () => {
  const joined = ARTIFACT.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment.toLowerCase()), `missing non-claim fragment ${fragment}`);
  }
  assert.ok(ARTIFACT.adjudication_rule_reconciliation.length > 0);
  assert.ok(ARTIFACT.adjudication_rule.length > 0);
});

// ---------------------------------------------------------------------------
// independent repetition of the rule and of every threshold
// ---------------------------------------------------------------------------

test("the four legs, their carried verdicts and their thresholds are reproduced", () => {
  assert.deepEqual(
    ARTIFACT.legs.map((row) => row.leg_id),
    [...LEG_ORDER],
  );
  assert.deepEqual(
    LEDGER.legs.map((leg) => leg.leg_id).sort(),
    [...LEG_ORDER].sort(),
  );
  let accepted = 0;
  let hold = 0;
  for (const legId of LEG_ORDER) {
    const row = ARTIFACT_BY_ID.get(legId);
    const ledgerLeg = LEDGER_BY_ID.get(legId);
    const measured = independentMeasure(legId);
    const satisfied = measured.numerator >= measured.threshold;
    const expected = independentDisposition(ledgerLeg.leg_verdict, satisfied);
    assert.equal(row.leg_verdict, ledgerLeg.leg_verdict, `${legId} carried verdict`);
    assert.equal(row.scope_disposition, expected, `${legId} disposition`);
    assert.equal(row.threshold_satisfied, satisfied, `${legId} recomputed threshold`);
    assert.equal(row.measurement.observed_value, measured.numerator, `${legId} numerator`);
    assert.equal(row.measurement.denominator_value, measured.denominator, `${legId} denominator`);
    assert.equal(row.measurement.threshold, measured.threshold, `${legId} threshold`);
    assert.equal(row.quantifier.name, ledgerLeg.quantifier.name);
    assert.equal(row.quantifier.unit, ledgerLeg.quantifier.unit);
    assert.equal(row.quantifier.acceptance, ledgerLeg.quantifier.acceptance);
    assert.equal(row.quantifier.threshold, ledgerLeg.quantifier.threshold);
    assert.equal(
      row.quantifier.denominator_source_path,
      ledgerLeg.quantifier.denominator_source_path,
    );
    assert.equal(row.required_evidence_class, REQUIRED_EVIDENCE_CLASS);
    assert.equal(row.required_evidence_status, ledgerLeg.required_evidence_status);
    assert.deepEqual(row.class_matched_ids, []);
    assert.equal(row.leg_verdict_source, "carried-verbatim-from-s03-r070-scope-ledger");
    assert.equal(row.debt.length >= 1, true);
    assert.equal("validated" === row.leg_verdict, false);
    if (row.scope_disposition === "accepted-at-bounded-scope") accepted += 1;
    else if (row.scope_disposition === "hold-with-precise-debt") hold += 1;
    else assert.fail(`unexpected disposition ${row.scope_disposition}`);
  }
  assert.equal(accepted, 3);
  assert.equal(hold, 1);
  assert.equal(ARTIFACT.accepted_at_bounded_scope_total, 3);
  assert.equal(ARTIFACT.hold_with_precise_debt_total, 1);
  assert.equal(ARTIFACT.hold_requires_owner_decision_total, 0);
  assert.equal(ARTIFACT.rejected_total, 0);
  assert.equal(ARTIFACT.debt_total, 4);
  assert.equal(ARTIFACT_BY_ID.get("commencement-and-transitional").scope_disposition, "hold-with-precise-debt");
  assert.equal(ARTIFACT_BY_ID.get("commencement-and-transitional").threshold_satisfied, false);
});

test("the ledger's declared-count bindings agree with the live source artifacts", () => {
  const sources = {
    [AMENDING_PATH]: AMENDING,
    [COMMENCEMENT_PATH]: COMMENCEMENT,
    [EDITION_DELTA_PATH]: EDITION_DELTA,
  };
  for (const ledgerLeg of LEDGER.legs) {
    const artifact = sources[ledgerLeg.tracked_evidence.artifact_relative_path];
    assert.ok(artifact, `${ledgerLeg.leg_id} source artifact`);
    const declared = ledgerLeg.tracked_evidence.declared_counts;
    const row = ARTIFACT_BY_ID.get(ledgerLeg.leg_id);
    assert.equal(
      row.tracked_evidence.artifact_relative_path,
      ledgerLeg.tracked_evidence.artifact_relative_path,
    );
    assert.equal(row.tracked_evidence.declared_count_bindings.length, Object.keys(declared).length);
    for (const binding of row.tracked_evidence.declared_count_bindings) {
      assert.equal(numericAt(artifact, binding.source_path), binding.value);
      assert.equal(declared[binding.ledger_key], binding.value);
    }
    assert.equal(assertCountBindings(ledgerLeg.leg_id, ledgerLeg, artifact).length >= 3, true);
  }
});

test("the commencement hold debt names the corpus gap, the M207 pilot and the M208 admission", () => {
  const row = ARTIFACT_BY_ID.get("commencement-and-transitional");
  const debt = row.debt[0];
  const joined = [
    debt.missing_artifact_kind,
    debt.closest_evidence.why_insufficient,
    ...debt.unmet_conditions,
    debt.unblock_condition,
  ]
    .join(" ")
    .toLowerCase();
  assert.ok(joined.includes("legislative commencement"));
  assert.ok(joined.includes("transitional"));
  assert.ok(joined.includes("m207"));
  assert.ok(joined.includes("prd/annotation/m207-s04-c4-protocol.md"));
  assert.ok(joined.includes("prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json"));
  assert.ok(joined.includes("not-measured"));
  assert.ok(joined.includes("m208"));
  assert.ok(joined.includes("not-adopted"));
  assert.ok(joined.includes("unblock") || joined.includes("appears"));
  assert.deepEqual(debt.unmet_conditions.length, 3);
  assert.equal(debt.required_evidence_class, REQUIRED_EVIDENCE_CLASS);
  assert.equal(debt.observed_value, 0);
  assert.equal(debt.threshold, 1);
  const ownerKinds = ARTIFACT.owner_decisions_outstanding.map((owner) => owner.kind);
  for (const kind of [
    "corpus-scale-legislative-commencement-source",
    "m207-class-matched-human-pilot",
    "m208-s03-s04-admission",
    "canonical-admission-pair-swap",
  ]) {
    assert.ok(ownerKinds.includes(kind), `missing owner decision ${kind}`);
  }
  const handoffFields = ARTIFACT.s04_handoff_consumed.map((entry) => entry.field);
  assert.deepEqual(handoffFields, [
    "coverage_verdict",
    "disposition",
    "disposition_decision",
    "accept_or_hold",
    "unmet_conditions",
  ]);
});

test("accepted legs carry bounded-scope debt without claiming a promotion", () => {
  for (const legId of ["amending-acts", "affected-provisions", "edition-delta"]) {
    const row = ARTIFACT_BY_ID.get(legId);
    assert.equal(row.scope_disposition, "accepted-at-bounded-scope", legId);
    assert.equal(row.required_evidence_status, "absent", legId);
    assert.deepEqual(row.class_matched_ids, [], legId);
    const debt = row.debt[0];
    assert.equal(debt.required_evidence_class, REQUIRED_EVIDENCE_CLASS);
    assert.equal(debt.observed_value, row.measurement.observed_value);
    assert.ok(debt.unblock_condition.includes(row.quantifier.name));
  }
  const checks = new Map(ARTIFACT.promotion_checks.map((check) => [check.check_id, check]));
  assert.equal(checks.get("no_promotion_counter").verdict, "pass");
  assert.equal(checks.get("coverage_verdict_not_promoted").verdict, "pass");
  assert.equal(checks.get("no_nonempty_class_matched_ids").verdict, "pass");
});

test("artifact rows survive the module's own row and bundle validation", () => {
  for (const row of ARTIFACT.legs) assert.equal(validateLegRow(row), true);
  assert.equal(validateBundle(ARTIFACT), true);
});

// ---------------------------------------------------------------------------
// live pins and byte stability
// ---------------------------------------------------------------------------

test("the S03 ledger and frozen M201 gate still hash to their declared pins", () => {
  assert.equal(sha256OfRepoFile(LEDGER_PATH), LEDGER_PIN.sha256);
  assert.equal(LEDGER_LOADED.bytes, LEDGER_PIN.bytes);
  assert.equal(sha256OfRepoFile(M201_GATE_PATH), M201_PIN.sha256);
  assert.equal(M201_LOADED.bytes, M201_PIN.bytes);
  assert.equal(LEDGER.frozen_m201_boundary.gate_sha256, M201_PIN.sha256);
  assert.equal(LEDGER.frozen_m201_boundary.gate_relative_path, M201_GATE_PATH);
  assert.equal(M201.coverage_verdict, COVERAGE_VERDICT);
  assert.equal(M201.disposition, "active");
  assert.equal(ARTIFACT.m201_boundary.sha256, M201_PIN.sha256);
  assert.equal(ARTIFACT.m201_boundary.bytes, M201_PIN.bytes);
  assert.equal(ARTIFACT.m201_boundary.coverage_verdict, COVERAGE_VERDICT);
  // the ledger declares the four leg input pins; each one still agrees
  assert.equal(LEDGER.inputs.length, 4);
  for (const input of LEDGER.inputs) {
    assert.equal(sha256OfRepoFile(input.relative_path), input.input_sha256, input.relative_path);
  }
  assert.equal(assertInputPins(LEDGER_LOADED).length, 5);
  assert.equal(assertM201Boundary(M201_LOADED, LEDGER).verdict, "pass");
  assert.equal(assertLedgerShape(LEDGER), true);
});

test("the committed artifact is byte-identical to the live re-derivation", () => {
  const bundle = adjudicationBundle({});
  checkRenderedBytes(renderEvidence(bundle), ARTIFACT_RAW);
  assert.equal(bundle.counted.cross_checks_failed, 0);
  assert.equal(bundle.counted.promotion_checks_failed, 0);
  assert.equal(bundle.counted.accepted_at_bounded_scope_total, 3);
  assert.equal(bundle.counted.hold_with_precise_debt_total, 1);
});

test("CLI --check is drift-free and prints the required heartbeat", () => {
  const stdout = execFileSync("node", [MODULE_PATH, "--mode", "legs", "--check"], {
    cwd: ROOT,
    encoding: "utf8",
  });
  assert.equal(stdout.includes(EXPECTED_HEARTBEAT), true, stdout);
  assert.equal(stdout.includes("failed=0"), true, stdout);
});

// ---------------------------------------------------------------------------
// negative cases: one mutated copy per documented fail-closed code
// ---------------------------------------------------------------------------

const BASE_ROW = ARTIFACT_BY_ID.get("amending-acts");
const BASE_LEDGER_LEG = LEDGER_BY_ID.get("amending-acts");

const NEGATIVE_CASES = Object.freeze({
  artifact_empty: () => assertNonEmpty(""),
  class_matched_evidence_claimed: () =>
    validateLegRow({ ...BASE_ROW, class_matched_ids: ["m207-slot-1"] }),
  count_binding_mismatch: () =>
    assertCountBindings(
      "amending-acts",
      {
        ...BASE_LEDGER_LEG,
        tracked_evidence: {
          declared_counts: { amends_edges_total: 119, layer1_amending_acts: 121, layer1_records_total: 122 },
        },
      },
      AMENDING,
    ),
  coverage_verdict_upgraded: () => validateBundle({ ...ARTIFACT, coverage_verdict: "every-edition" }),
  cross_check_failed: () => assertAllChecksPass([{ check_id: "mutated", verdict: "fail" }]),
  debt_record_incomplete: () =>
    validateDebtItem({
      debt_id: "x",
      quantifier_name: "x",
      acceptance_text: "0",
      required_evidence_class: "human-annotation",
      missing_artifact_kind: "x",
      closest_evidence: { relative_paths: [], why_insufficient: "y" },
      unblock_condition: "z",
      observed_value: 0,
      threshold: 1,
    }),
  denominator_source_absent: () =>
    resolveDenominatorSource(
      "amending-acts",
      { quantifier: { denominator_source_path: "prd/migration/rust-evidence/m209-s04-absent.json" } },
      { legArtifacts: {} },
    ),
  evidence_drift: () => checkRenderedBytes("a", "b"),
  input_absent: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-not-present.json", "absent"),
  input_artifact_shape_invalid: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-broken.json", "broken", {
      existsSync: () => true,
      readFileSync: () => "{",
    }),
  input_hash_mismatch: () =>
    assertInputPins(
      {
        ...LEDGER_LOADED,
        parsed: {
          ...LEDGER,
          inputs: [{ ...LEDGER.inputs[0], input_bytes: 1 }, ...LEDGER.inputs.slice(1)],
        },
      },
      { isTracked: () => true },
    ),
  input_not_tracked: () => assertInputPins(LEDGER_LOADED, { isTracked: () => false }),
  inventory_count_as_quantifier: () =>
    validateLegRow({ ...BASE_ROW, quantifier: { ...BASE_ROW.quantifier, name: "registry_rows" } }),
  ledger_leg_set_mismatch: () => assertLedgerShape({ ...LEDGER, legs: LEDGER.legs.slice(0, 3) }),
  leg_verdict_upgraded: () => validateLegRow({ ...BASE_ROW, leg_verdict: "validated" }),
  legs_promoted_nonzero: () => validateBundle({ ...ARTIFACT, legs_promoted: 1 }),
  m201_boundary_drift: () =>
    assertM201Boundary(
      { ...M201_LOADED, sha256: "sha256:0000000000000000000000000000000000000000000000000000000000000000" },
      LEDGER,
    ),
  non_ascii_evidence: () => assertAsciiOnly("\u00e9"),
  out_absolute: () => resolveOutTarget("/tmp/m209-s04.json"),
  out_not_evidence_path: () => resolveOutTarget("scripts/m209_s04_scope_adjudication.mjs"),
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
  path_not_repository_relative: () => assertRepoRelative("../escaped.json", "escaped"),
  promotion_claim_present: () => validateBundle({ ...ARTIFACT, authoritative: true }),
  quantifier_threshold_unmet: () =>
    validateLegRow({
      ...BASE_ROW,
      leg_verdict: "bounded-supporting",
      scope_disposition: "accepted-at-bounded-scope",
      threshold_satisfied: false,
      measurement: { ...BASE_ROW.measurement, observed_value: 0, threshold: 1, satisfied: false },
    }),
  raw_text_leak: () => assertNoRawText("consultantplus://obtained"),
  required_evidence_class_absent: () =>
    validateLegRow({
      ...BASE_ROW,
      required_evidence_class: "",
      class_matched_ids: [REQUIRED_EVIDENCE_CLASS],
    }),
  unsupported_disposition: () => validateLegRow({ ...BASE_ROW, scope_disposition: "validated" }),
});

test("every documented fail-closed code fires on a mutated copy", () => {
  assert.deepEqual(Object.keys(NEGATIVE_CASES).sort(), [...DOCUMENTED_CODES].sort());
  for (const [code, fn] of Object.entries(NEGATIVE_CASES)) expectCode(code, fn);
});

test("the rule rejects a legitimately unmet threshold and a missing evidence declaration", () => {
  expectCode("quantifier_threshold_unmet", () =>
    validateLegRow({
      ...BASE_ROW,
      leg_verdict: "bounded-supporting",
      scope_disposition: "accepted-at-bounded-scope",
      threshold_satisfied: true,
      measurement: { ...BASE_ROW.measurement, observed_value: 0, threshold: 1, satisfied: false },
    }),
  );
  expectCode("required_evidence_class_absent", () =>
    assertRequiredEvidenceDeclaration("amending-acts", { required_evidence_class: "" }, {}),
  );
});

// ---------------------------------------------------------------------------
// module hygiene
// ---------------------------------------------------------------------------

test("module stays offline, dependency-free and never executes Rust as a gate", () => {
  const source = readRepo(MODULE_PATH);
  const imports = [...source.matchAll(/from "([^"]+)"/g)].map((match) => match[1]);
  assert.ok(imports.length > 0);
  for (const specifier of imports) {
    assert.ok(specifier.startsWith("node:"), `unexpected import ${specifier}`);
  }
  assert.equal(/execFileSync\("python/.test(source), false);
  assert.equal(/execFileSync\("cargo/.test(source), false);
  assert.equal(/\bfetch\(/.test(source), false);
  assert.equal(
    /writeFileSync\([^)]*r070_proof_gate/.test(source),
    false,
    "the frozen Rust gate must never be written",
  );
  const contract = readRepo(CONTRACT_PATH);
  assert.ok(contract.length > 0);
});
