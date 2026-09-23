// M209 S04 T03 contract: the R035 gate-by-gate acceptance adjudication
// (D537, D539, D558).
//
// The contract is offline. It never imports the module's parsers to derive the
// expected answer: the README R035 table, the verifier constants, the S01 gate
// register and the frozen M202 snapshot are parsed here independently, and the
// disposition rule is repeated here from the D558 text. On top of that it
// asserts the documented fail-closed block is exactly the emitted one (each
// code fires on a mutated in-memory copy), that the committed artifact is
// byte-identical to the live re-derivation and that every live canonical source
// still hashes to its declared pin.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  ARTIFACT_PATH,
  CANONICAL_PINS,
  CORROBORATION_PATH,
  DISPOSITION_VOCABULARY,
  EVIDENCE_RELATIONS,
  FAIL_CLOSED_CODES,
  FROZEN_M202_PATH,
  INVENTORY_QUANTIFIERS,
  README_PATH,
  REGISTER_PATH,
  SCHEMA,
  VERIFIER_PATH,
  adjudicationBundle,
  assertAsciiOnly,
  assertCanonicalPins,
  assertNoRawText,
  assertNonEmpty,
  assertRepoRelative,
  checkRenderedBytes,
  deriveGateRules,
  evaluateProofPackage,
  isRepoRelative,
  loadCanonicalSources,
  loadJsonArtifact,
  renderEvidence,
  resolveOutTarget,
  sha256Pin,
  validateBundle,
  validateDebtItem,
  validateGateRow,
} from "./m209_s04_gate_adjudication.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MODULE_PATH = "scripts/m209_s04_gate_adjudication.mjs";
const CONTRACT_PATH = "scripts/m209_s04_gate_adjudication_contract.test.mjs";
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The heartbeat the milestone closeout greps for. The required run must appear
// contiguously in the CLI output.
const EXPECTED_HEARTBEAT = "gates=7 hold=6 owner-decision=1 accepted=0 gates_promoted=0 drift=0";

// The documented fail-closed vocabulary, transcribed independently of the
// module. A silent expansion of the module's list must fail this test.
const DOCUMENTED_CODES = Object.freeze([
  "accepted_without_proof_package",
  "artifact_empty",
  "canonical_source_drift",
  "debt_record_incomplete",
  "evidence_drift",
  "gate_set_mismatch",
  "input_absent",
  "input_artifact_shape_invalid",
  "inventory_count_as_quantifier",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "owner_decision_required_collapsed",
  "path_not_repository_relative",
  "proof_level_below_minimum",
  "proof_package_gate_mismatch",
  "proof_package_path_absent",
  "promotion_claim_present",
  "quantifier_threshold_absent",
  "raw_text_leak",
  "required_evidence_class_absent",
  "unsupported_disposition",
]);

// The required non-claim fragments (D430, D536, D537, D538, D539, D543, D558).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "s01-register-is-not-overridden-or-smoothed",
  "d536",
  "d538",
  "gate-g015",
  "never averaged",
  "bounded-input-is-not-a-proof-package",
  "102-identity",
  "166-row",
  "0-punkt",
  "proof_package=null",
  "bounded-input-acceptance-is-not-gate-acceptance",
  "no-proof-package-is-attributed",
  "gates_promoted=0",
  "r035-stays-active",
  "d430",
  "no requirement record is mutated",
  "count-only-and-ascii-only",
  "d537",
  "never executed as a gate",
  "inventory-counts-are-not-quantifiers",
  "d539",
  "hold-requires-owner-decision",
  "quantifiers-are-acceptance-contracts-not-measurements",
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
// independent live-source parsers (deliberately not the module's)
// ---------------------------------------------------------------------------

const README_HEADER = "| R035 trigger terms | Current safe bucket | Required promotion gate | Minimum validated proof level |";

function independentReadmeRows(text) {
  const lines = text.split("\n");
  const headerIndex = lines.indexOf(README_HEADER);
  assert.ok(headerIndex > 0, "readme R035 table header must be present verbatim");
  const rows = [];
  for (let index = headerIndex + 2; index < lines.length; index += 1) {
    if (!lines[index].startsWith("|")) break;
    const cells = lines[index]
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());
    assert.equal(cells.length, 4, `readme row ${index} must have four cells`);
    rows.push({
      gate_ids: cells[2].split("`").join("").split(" or ").map((id) => id.trim()),
      level: cells[3].split("`").join("").trim(),
      safe_bucket: cells[1].split("`").join("").trim(),
    });
  }
  assert.equal(rows.length, 7, "the README R035 table must have exactly seven rows");
  return rows;
}

function independentBlock(text, marker, open, close) {
  const at = text.indexOf(marker);
  assert.ok(at >= 0, `missing block ${marker}`);
  const start = text.indexOf(open, at);
  assert.ok(start >= 0, `missing ${open} after ${marker}`);
  let depth = 0;
  for (let index = start; index < text.length; index += 1) {
    if (text[index] === open) depth += 1;
    else if (text[index] === close) {
      depth -= 1;
      if (depth === 0) return text.slice(start, index + 1);
    }
  }
  throw new Error(`unbalanced ${marker}`);
}

function independentSetDict(text, marker) {
  const block = independentBlock(text, marker, "{", "}");
  const out = {};
  const entry = /"([a-z][a-z-]*)":\s*\{([^}]*)\}/g;
  let match = entry.exec(block);
  while (match !== null) {
    out[match[1]] = [...match[2].matchAll(/"([^"]+)"/g)].map((row) => row[1]);
    match = entry.exec(block);
  }
  return out;
}

function independentOntologyRules(text) {
  const block = independentBlock(text, "ONTOLOGY_PROMOTION_RULES", "(", ")");
  const rules = [];
  const dicts = block.match(/\{[^{}]*\}/g) ?? [];
  for (const dict of dicts) {
    const label = /"label":\s*"([^"]+)"/.exec(dict);
    const gates = /"required_gate_ids":\s*\(([^)]*)\)/.exec(dict);
    const level = /"minimum_proof_level":\s*"([^"]+)"/.exec(dict);
    if (label === null || gates === null || level === null) continue;
    rules.push({
      gate_ids: [...gates[1].matchAll(/"([^"]+)"/g)].map((row) => row[1]),
      level: level[1],
    });
  }
  assert.ok(rules.length >= 7, "the verifier must declare at least seven ontology rules");
  return rules;
}

const SOURCES = loadCanonicalSources();
const README_TEXT = SOURCES.readme.text;
const VERIFIER_TEXT = SOURCES.verifier.text;
const README_ROWS = independentReadmeRows(README_TEXT);
const README_PRIMARY = new Map(README_ROWS.map((row) => [row.gate_ids[0], row]));
const RULE_PRIMARY = new Map();
for (const rule of independentOntologyRules(VERIFIER_TEXT)) {
  const list = RULE_PRIMARY.get(rule.gate_ids[0]) ?? [];
  list.push(rule.level);
  RULE_PRIMARY.set(rule.gate_ids[0], list);
}
const REQUIRED_CLASSES = independentSetDict(VERIFIER_TEXT, "PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES");
const REGISTER = JSON.parse(readRepo(REGISTER_PATH));
const FROZEN = JSON.parse(readRepo(FROZEN_M202_PATH));
const REGISTER_BY_ID = new Map(REGISTER.gates.map((gate) => [gate.gate_id, gate]));
const FROZEN_BY_ID = new Map(FROZEN.promotion_gates.map((gate) => [gate.gate_id, gate]));
const LIVE_GATE_IDS = [...new Set(README_ROWS.flatMap((row) => row.gate_ids))].sort();
const ARTIFACT_RAW = readRepo(ARTIFACT_PATH);
const ARTIFACT = JSON.parse(ARTIFACT_RAW);
const ARTIFACT_BY_ID = new Map(ARTIFACT.gates.map((row) => [row.gate_id, row]));

function expectedDisposition(gateId) {
  const registerGate = REGISTER_BY_ID.get(gateId);
  const states = new Set(registerGate.recorded_states.map((state) => state.normalized_state));
  if (states.size > 1) return "hold-requires-owner-decision";
  // No gate has a proof package (D539/D558), so no gate is accepted.
  assert.ok(EVIDENCE_RELATIONS[gateId] !== undefined, `${gateId} must have an evidence relation`);
  return "hold-with-precise-debt";
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
  assert.equal(ARTIFACT.kind, "m209-s04-r035-gate-adjudication");
  assert.equal(ARTIFACT.milestone, "M209-2yg6ix");
  assert.equal(ARTIFACT.slice, "S04");
  assert.equal(ARTIFACT.task, "T03");
  assert.equal(ARTIFACT.lifecycle, "[bounded]");
  assert.equal(ARTIFACT.authoritative, false);
  assert.equal(ARTIFACT.count_only, true);
  assert.equal(ARTIFACT.ascii_only, true);
  assert.equal(ARTIFACT.requirement_id, "R035");
  assert.equal(ARTIFACT.requirement_disposition, "active");
  assert.equal(ARTIFACT.requirement_disposition_decision, "D430");
  assert.equal(ARTIFACT.register_decision, "D536");
  assert.equal(ARTIFACT.decision, "D558");
  assert.equal(ARTIFACT.gate_count, 7);
  assert.equal(ARTIFACT.gates_promoted, 0);
  assert.equal(ARTIFACT.requirement_records_mutated, 0);
  assert.equal(ARTIFACT.proof_packages_attached, 0);
  assert.deepEqual([...ARTIFACT.disposition_vocabulary].sort(), [...DISPOSITION_VOCABULARY].sort());
});

test("artifact paths are repository-relative and carry no provider prose", () => {
  for (const source of Object.values(ARTIFACT.canonical_sources)) {
    assert.equal(isRepoRelative(source.relative_path), true, source.relative_path);
  }
  for (const row of ARTIFACT.gates) {
    for (const artifact of row.evidence_relation.artifacts) {
      assert.equal(isRepoRelative(artifact.relative_path), true, artifact.relative_path);
    }
    for (const debt of row.debt) {
      for (const artifact of debt.closest_evidence.artifacts) {
        assert.equal(isRepoRelative(artifact), true, artifact);
      }
      assert.equal(
        typeof debt.closest_evidence.why_insufficient === "string" &&
          debt.closest_evidence.why_insufficient.length > 0,
        true,
      );
    }
  }
});

test("documented fail-closed vocabulary equals the emitted one", () => {
  assert.deepEqual([...FAIL_CLOSED_CODES].sort(), [...DOCUMENTED_CODES].sort());
  assert.deepEqual([...ARTIFACT.fail_closed_codes].sort(), [...DOCUMENTED_CODES].sort());
});

test("non-claims bound the artifact (D430, D536, D537, D538, D539, D558)", () => {
  const joined = ARTIFACT.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment.toLowerCase()), `missing non-claim fragment ${fragment}`);
  }
});

// ---------------------------------------------------------------------------
// independent repetition of the gate set and of the disposition rule
// ---------------------------------------------------------------------------

test("the live gate set is the seven README primary gates and matches both frozen legs", () => {
  const registerIds = REGISTER.gates.map((gate) => gate.gate_id).sort();
  const frozenIds = FROZEN.promotion_gates.map((gate) => gate.gate_id).sort();
  assert.deepEqual(LIVE_GATE_IDS, [...README_PRIMARY.keys()].sort());
  assert.deepEqual(LIVE_GATE_IDS, [...RULE_PRIMARY.keys()].sort());
  assert.deepEqual(LIVE_GATE_IDS, registerIds);
  assert.deepEqual(LIVE_GATE_IDS, frozenIds);
  assert.equal(LIVE_GATE_IDS.length, 7);
  assert.deepEqual(
    [...ARTIFACT_BY_ID.keys()].sort(),
    LIVE_GATE_IDS,
    "artifact rows must cover exactly the live gate set",
  );
});

test("every gate is adjudicated hold-with-precise-debt except the recorded conflict", () => {
  let hold = 0;
  let ownerDecision = 0;
  let accepted = 0;
  for (const gateId of LIVE_GATE_IDS) {
    const row = ARTIFACT_BY_ID.get(gateId);
    const registerGate = REGISTER_BY_ID.get(gateId);
    const expected = expectedDisposition(gateId);
    assert.equal(row.disposition, expected, `${gateId} disposition`);
    assert.equal(row.proof_package, null, `${gateId} must not carry a proof package`);
    assert.deepEqual(row.required_evidence_classes, REQUIRED_CLASSES[row.minimum_validated_proof_level]);
    assert.equal(row.minimum_validated_proof_level, README_PRIMARY.get(gateId).level);
    assert.equal(row.minimum_validated_proof_level, RULE_PRIMARY.get(gateId)[0]);
    assert.equal(row.minimum_validated_proof_level, registerGate.minimum_validated_proof_level);
    assert.equal(row.evidence_class, registerGate.evidence_class);
    assert.equal(row.owner, registerGate.owner);
    assert.equal(row.owner_path, registerGate.owner_path);
    assert.equal(row.quantifier.name, registerGate.quantifier.name);
    assert.equal(row.quantifier.unit, registerGate.quantifier.unit);
    assert.equal(row.quantifier.acceptance, registerGate.quantifier.acceptance);
    assert.equal(row.quantifier.acceptance_threshold_present, true);
    assert.equal(row.frozen_gate_verdict, FROZEN_BY_ID.get(gateId).gate_verdict);
    assert.equal(INVENTORY_QUANTIFIERS.includes(row.quantifier.name), false);
    const states = new Set(registerGate.recorded_states.map((state) => state.normalized_state));
    assert.equal(row.recorded_conflict, states.size > 1, `${gateId} conflict flag`);
    if (row.disposition === "hold-requires-owner-decision") ownerDecision += 1;
    else if (row.disposition === "hold-with-precise-debt") hold += 1;
    else if (row.disposition === "accepted-at-bounded-scope") accepted += 1;
    else assert.fail(`unexpected disposition ${row.disposition}`);
  }
  assert.equal(hold, 6);
  assert.equal(ownerDecision, 1);
  assert.equal(accepted, 0);
  assert.equal(ARTIFACT.accepted_total, 0);
  assert.equal(ARTIFACT.hold_with_precise_debt_total, 6);
  assert.equal(ARTIFACT.hold_requires_owner_decision_total, 1);
  assert.equal(ARTIFACT.debt_total, 7);
  assert.equal(ARTIFACT.gates_promoted, 0);
  assert.equal(ARTIFACT_BY_ID.get("GATE-G015").disposition, "hold-requires-owner-decision");
});

test("every hold row carries a complete debt record naming the missing artifact", () => {
  const requiredKeys = [
    "quantifier_name",
    "acceptance_text",
    "required_proof_level",
    "required_evidence_class",
    "missing_artifact_kind",
    "closest_evidence",
    "unblock_condition",
  ];
  for (const row of ARTIFACT.gates) {
    assert.equal(row.debt.length, 1, `${row.gate_id} must carry exactly one debt item`);
    const debt = row.debt[0];
    for (const key of requiredKeys) {
      assert.ok(Object.prototype.hasOwnProperty.call(debt, key), `${row.gate_id} debt.${key} absent`);
    }
    for (const key of requiredKeys) {
      if (key === "closest_evidence") continue;
      assert.equal(typeof debt[key], "string");
      assert.ok(debt[key].length > 0, `${row.gate_id} debt.${key}`);
    }
    assert.equal(validateDebtItem(debt), true);
    assert.equal(debt.quantifier_name, row.quantifier.name);
    assert.equal(debt.required_proof_level, row.minimum_validated_proof_level);
    assert.equal(debt.required_evidence_class, row.evidence_class);
    assert.ok(debt.unblock_condition.includes(row.gate_id));
    assert.ok(debt.unblock_condition.includes(row.quantifier.name));
    assert.equal(debt.closest_evidence.relation, row.evidence_relation.relation);
  }
});

test("S02 candidate-backed expansion is not a proof package for any gate", () => {
  const block = ARTIFACT.s02_candidate_backed_is_not_a_proof_package;
  assert.equal(block.candidate_backed_identities, 102);
  assert.equal(block.registry_rows, 166);
  assert.equal(block.punkt_admitted, 0);
  assert.equal(block.accepted_gates, 0);
  assert.deepEqual(
    block.source_artifacts,
    [
      "prd/migration/rust-evidence/m209-s02-extraction-evidence.json",
      "prd/migration/rust-evidence/m209-s02-admission-regeneration-evidence.json",
    ],
  );
  for (const row of ARTIFACT.gates) assert.equal(row.proof_package, null);
  const checks = new Map(ARTIFACT.promotion_checks.map((check) => [check.check_id, check]));
  assert.equal(checks.get("s02_candidate_backed_is_not_a_proof_package").verdict, "pass");
  assert.equal(checks.get("no_inventory_counter_as_quantifier").verdict, "pass");
});

test("artifact rows survive the module's own row and bundle validation", () => {
  for (const row of ARTIFACT.gates) assert.equal(validateGateRow(row, {}), true);
  assert.equal(validateBundle(ARTIFACT), true);
});

// ---------------------------------------------------------------------------
// live canonical sources and byte stability
// ---------------------------------------------------------------------------

test("every live canonical source still hashes to its declared pin", () => {
  assert.equal(sha256OfRepoFile(README_PATH), CANONICAL_PINS.readme.sha256);
  assert.equal(sha256OfRepoFile(VERIFIER_PATH), CANONICAL_PINS.verifier.sha256);
  assert.equal(sha256OfRepoFile(REGISTER_PATH), CANONICAL_PINS.register.sha256);
  assert.equal(sha256OfRepoFile(FROZEN_M202_PATH), CANONICAL_PINS.frozen_m202.sha256);
  assert.equal(SOURCES.readme.bytes, CANONICAL_PINS.readme.bytes);
  assert.equal(SOURCES.verifier.bytes, CANONICAL_PINS.verifier.bytes);
  assert.equal(SOURCES.register.bytes, CANONICAL_PINS.register.bytes);
  assert.equal(SOURCES.frozen_m202.bytes, CANONICAL_PINS.frozen_m202.bytes);
  for (const row of ARTIFACT.cross_checks) {
    if (row.check_id.startsWith("canonical_pin_")) assert.equal(row.verdict, "pass", row.check_id);
  }
  assert.equal(ARTIFACT.canonical_sources.readme_gate_table.sha256, CANONICAL_PINS.readme.sha256);
  assert.equal(ARTIFACT.canonical_sources.enforcement_rules.sha256, CANONICAL_PINS.verifier.sha256);
  assert.equal(ARTIFACT.canonical_sources.gate_register.sha256, CANONICAL_PINS.register.sha256);
  assert.equal(ARTIFACT.canonical_sources.frozen_m202.sha256, CANONICAL_PINS.frozen_m202.sha256);
  // The S01 register declares the README and verifier pins independently.
  const registerDeclared = REGISTER.canonical_sources;
  assert.equal(registerDeclared.gate_table.sha256, CANONICAL_PINS.readme.sha256.slice(7));
  assert.equal(registerDeclared.enforcement_rules.sha256, CANONICAL_PINS.verifier.sha256.slice(7));
  assert.equal(registerDeclared.frozen_snapshot.sha256, CANONICAL_PINS.frozen_m202.sha256.slice(7));
  assert.equal(registerDeclared.frozen_snapshot.bytes, CANONICAL_PINS.frozen_m202.bytes);
  // The T01 corroboration artifact binds the register byte-for-byte.
  const corroboration = JSON.parse(readRepo(CORROBORATION_PATH));
  const binding = corroboration.bindings.find((row) => row.relative_path === REGISTER_PATH);
  assert.ok(binding, "T01 must bind the S01 gate register");
  assert.equal(binding.declared_bytes, CANONICAL_PINS.register.bytes);
  assert.equal(binding.declared_sha256, CANONICAL_PINS.register.sha256.slice(7));
  assert.equal(assertCanonicalPins(SOURCES).length, 4);
});

test("the committed artifact is byte-identical to the live re-derivation", () => {
  const bundle = adjudicationBundle({});
  checkRenderedBytes(renderEvidence(bundle), ARTIFACT_RAW);
  assert.equal(bundle.counted.cross_checks_failed, 0);
  assert.equal(bundle.counted.promotion_checks_failed, 0);
});

test("CLI --check is drift-free and prints the required heartbeat", () => {
  const stdout = execFileSync("node", [MODULE_PATH, "--mode", "gates", "--check"], {
    cwd: ROOT,
    encoding: "utf8",
  });
  assert.equal(stdout.includes(EXPECTED_HEARTBEAT), true, stdout);
});

// ---------------------------------------------------------------------------
// negative cases: one mutated copy per documented fail-closed code
// ---------------------------------------------------------------------------

const AKOMA_GATE = {
  gate_id: "GATE-AKOMA-FRBR-NORMALIZATION",
  minimum_validated_proof_level: "static-check",
  required_evidence_classes: ["gsd-summary", "source-code", "test-artifact"],
};

function packageProbes(packageObject) {
  return {
    existsSync: () => true,
    readFileSync: () => JSON.stringify(packageObject),
    isTracked: () => true,
  };
}

const validPackage = {
  gate_id: AKOMA_GATE.gate_id,
  evidence_class: "test-artifact",
  proof_level: "static-check",
  quantifier_name: "projection_unmapped_field_count",
  measured_value: 0,
  acceptance_threshold: 0,
};

const NEGATIVE_CASES = Object.freeze({
  accepted_without_proof_package: () =>
    validateGateRow(
      { ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION"), disposition: "accepted-at-bounded-scope" },
      {},
    ),
  artifact_empty: () => assertNonEmpty(""),
  canonical_source_drift: () =>
    assertCanonicalPins({
      ...SOURCES,
      readme: { ...SOURCES.readme, sha256: "sha256:0000000000000000000000000000000000000000000000000000000000000000" },
    }),
  debt_record_incomplete: () =>
    validateDebtItem({
      quantifier_name: "x",
      acceptance_text: "0",
      required_proof_level: "static-check",
      required_evidence_class: "test-artifact",
      missing_artifact_kind: "x",
      closest_evidence: { relation: "none", artifacts: [], why_insufficient: "y" },
    }),
  evidence_drift: () => checkRenderedBytes("a", "b"),
  gate_set_mismatch: () =>
    deriveGateRules(
      README_TEXT.split("\n")
        .filter((line) => !line.startsWith("| pilot-scale"))
        .join("\n"),
      VERIFIER_TEXT,
    ),
  input_absent: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-not-present.json", "absent"),
  input_artifact_shape_invalid: () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-broken.json", "broken", {
      existsSync: () => true,
      readFileSync: () => "{",
    }),
  inventory_count_as_quantifier: () =>
    validateGateRow(
      {
        ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION"),
        quantifier: { ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION").quantifier, name: "registry_rows" },
      },
      {},
    ),
  non_ascii_evidence: () => assertAsciiOnly("\u00e9"),
  out_absolute: () => resolveOutTarget("/tmp/m209-s04.json"),
  out_not_evidence_path: () => resolveOutTarget("scripts/m209_s04_gate_adjudication.mjs"),
  out_of_repo_out: () =>
    resolveOutTarget(`${ARTIFACT_PATH}`, {
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
  owner_decision_required_collapsed: () =>
    validateGateRow(
      { ...ARTIFACT_BY_ID.get("GATE-G015"), disposition: "hold-with-precise-debt" },
      {},
    ),
  path_not_repository_relative: () => assertRepoRelative("../escaped.json", "escaped"),
  proof_level_below_minimum: () =>
    evaluateProofPackage(
      AKOMA_GATE,
      { relative_path: README_PATH },
      packageProbes({ ...validPackage, proof_level: "source-anchor" }),
    ),
  proof_package_gate_mismatch: () =>
    evaluateProofPackage(
      AKOMA_GATE,
      { relative_path: README_PATH },
      packageProbes({ ...validPackage, gate_id: "GATE-OTHER" }),
    ),
  proof_package_path_absent: () =>
    evaluateProofPackage(
      AKOMA_GATE,
      { relative_path: README_PATH },
      { existsSync: () => false, readFileSync: () => "{}", isTracked: () => true },
    ),
  promotion_claim_present: () => validateBundle({ ...ARTIFACT, gates_promoted: 1 }),
  quantifier_threshold_absent: () =>
    validateGateRow(
      {
        ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION"),
        quantifier: { ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION").quantifier, acceptance: "no threshold" },
      },
      {},
    ),
  raw_text_leak: () => assertNoRawText("consultantplus://obtained"),
  required_evidence_class_absent: () =>
    evaluateProofPackage(
      AKOMA_GATE,
      { relative_path: README_PATH },
      packageProbes({ ...validPackage, evidence_class: "runtime-artifact" }),
    ),
  unsupported_disposition: () =>
    validateGateRow(
      { ...ARTIFACT_BY_ID.get("GATE-AKOMA-FRBR-NORMALIZATION"), disposition: "validated" },
      {},
    ),
});

test("every documented fail-closed code fires on a mutated copy", () => {
  assert.deepEqual(Object.keys(NEGATIVE_CASES).sort(), [...DOCUMENTED_CODES].sort());
  for (const [code, fn] of Object.entries(NEGATIVE_CASES)) expectCode(code, fn);
});

test("the acceptance rule accepts a compliant package and rejects a weak measurement", () => {
  const accepted = evaluateProofPackage(
    AKOMA_GATE,
    { relative_path: README_PATH },
    packageProbes(validPackage),
  );
  assert.equal(accepted.accepted, true);
  const weak = evaluateProofPackage(
    AKOMA_GATE,
    { relative_path: README_PATH },
    packageProbes({ ...validPackage, measured_value: 0, acceptance_threshold: 1 }),
  );
  assert.equal(weak.accepted, false);
});

// ---------------------------------------------------------------------------
// module hygiene
// ---------------------------------------------------------------------------

test("module stays offline, dependency-free and never executes the verifier", () => {
  const source = readRepo(MODULE_PATH);
  const imports = [...source.matchAll(/from "([^"]+)"/g)].map((match) => match[1]);
  assert.ok(imports.length > 0);
  for (const specifier of imports) {
    assert.ok(specifier.startsWith("node:"), `unexpected import ${specifier}`);
  }
  assert.equal(/execFileSync\("python/.test(source), false);
  assert.equal(/\bfetch\(/.test(source), false);
  const contract = readRepo(CONTRACT_PATH);
  assert.ok(contract.length > 0);
});
