// M209 S03 T05 contract: the R070 scoped coverage ledger and the frozen M201
// boundary it hands to S04.
//
// The contract is offline and corpus-gated: when the untracked licensed
// provider export resolves the named chain directory it re-derives the declared
// edition total from the live listing; when it does not it prints
// `M209_S03_CORPUS_ABSENT` and asserts the artifact-integrity, aggregation and
// frozen-pin blocks only.
//
// It asserts the D539 quantifier rules (a named measure with a numeric
// comparator threshold and an existing denominator source path; no M202 or
// inventory count may stand as a quantifier), that the ledger's declared counts
// are the four source artifacts' own counts, that no leg is promoted, and that
// the documented fail-closed code block equals the emitted and Rust code sets.

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json";
const CONTRACT_PATH = "scripts/m209_s03_scope_ledger_contract.test.mjs";
const RUST_MODULE = "crates/ln-consultant-parser/src/amendment_provenance.rs";
const RUST_SUITE = "crates/ln-temporal/tests/m209_s03_frozen_m201_guard.rs";

const FAMILY_ARTIFACT = "prd/migration/rust-evidence/m209-s03-family-denominator.json";
const AMENDS_ARTIFACT = "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
const COMMENCEMENT_ARTIFACT =
  "prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json";
const EDITION_ARTIFACT = "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json";

const FROZEN_TRACKED_CHAIN = "prd/migration/rust-evidence/m201-s03-tracked-chain.json";
const FROZEN_TRACKED_YAML = "prd/architecture/fz44-tracked-edition-chain.yaml";
const FROZEN_C1_CANON =
  "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml";

const SCHEMA = "law-nexus/r070-scope-ledger/v1";
const KIND = "m209-s03-r070-scope-ledger";
const TASK = "T05";
const LIFECYCLE = "[bounded]";
const REQUIREMENT_ID = "R070";
const DISPOSITION = "active";
const DISPOSITION_DECISION = "D416";
const COVERAGE_VERDICT = "incomplete-because-not-every-edition";

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const CHAIN_TAIL = "exports/npa/law_2013-04-05_44-fz";

const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const LEG_IDS = [
  "amending-acts",
  "affected-provisions",
  "commencement-and-transitional",
  "edition-delta",
];
const LEG_VERDICTS = ["bounded-supporting", "slot-filled-not-proven"];

// M202 inventory counts that must never stand as an R070 quantifier (D539).
const FORBIDDEN_QUANTIFIER_KEYS = [
  "registry_rows",
  "legacy_human",
  "punkt_admitted",
  "candidates_extracted",
  "candidates_unique",
  "candidates_duplicate",
  "admitted_candidate_backed",
  "fz44_glava",
  "fz44_statya",
  "suites_cited",
];

const FROZEN_TRACKED_CHAIN_SHA256 =
  "9db7a0650ef8ba7054c620e97ec4bc6e037dbf80ef1349d1f0f6266d7bdc6531";
const FROZEN_TRACKED_YAML_SHA256 =
  "5f7a7a17cb898f693bcb17f729286fb07d3d720c0726d9ced44caef10ab0a2e8";

// The complete fail-closed code set. The documented block below is asserted to
// document exactly this set, and the same set is asserted equal to the
// artifact's `fail_closed_codes` field and to the Rust `LEDGER_FAIL_CLOSED_CODES`.
const FAIL_CLOSED_CODES = [
  "input_absent",
  "input_hash_mismatch",
  "family_count_unsupported",
  "zero_denominator",
  "non_ascii_evidence",
  "raw_text_leak",
  "leg_verdict_upgraded",
  "disposition_upgraded",
  "quantifier_unsupported",
  "denominator_source_absent",
  "m201_boundary_drift",
];

// ## Fail-closed codes (documented set; asserted equal to FAIL_CLOSED_CODES)
// DOCUMENTED_FAIL_CLOSED_BEGIN
// input_absent: one of the four declared S03 leg artifacts, or the frozen M201 gate, is absent from disk, or the tracked ledger is missing in `--check` mode.
// input_hash_mismatch: a live leg artifact pin or the frozen M201 gate pin differs from the tracked ledger, so the ledger is no longer a projection of the current legs.
// family_count_unsupported: the ledger legs are not the four declared R070 legs in order, a declared count is absent or not an unsigned count, or the edition-delta leg no longer reproduces the T01 chain declaration.
// zero_denominator: a quantifier carries a threshold of zero; a zero denominator is not a measurement.
// non_ascii_evidence: an input artifact or the rendered ledger carries a non-ASCII byte.
// raw_text_leak: a rendered value carries provider corpus prose rather than a count or a validated categorical key.
// leg_verdict_upgraded: a leg carries a verdict outside the closed set, the commencement leg is not slot-filled-not-proven, class_matched_ids is not an explicit empty set, or an S03 leg artifact claims authoritative true.
// disposition_upgraded: the ledger would carry `validated`, `complete` or `authoritative: true`, so a promoted disposition is refused.
// quantifier_unsupported: a quantifier is unnamed, is a forbidden M202 inventory key, or its acceptance does not carry its own numeric threshold.
// denominator_source_absent: a declared denominator source path is absolute, empty or does not resolve on disk.
// m201_boundary_drift: the frozen M201 R070 proof gate bytes or its active/bounded/coverage verdict drifted.
// DOCUMENTED_FAIL_CLOSED_END

const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not every consolidated legal edition",
  "incomplete-because-not-every-edition",
  "validated, complete or authoritative",
  "gates_promoted is 0",
  "r070 stays active",
  "d416",
  "numeric acceptance threshold",
  "d539",
  "zero denominator is not a measurement",
  "d552",
  "frozen m201 r070 proof gate",
  "d216",
  "class_matched_ids is an explicit empty set",
];

// The frozen M201 gate whose bytes and verdicts this ledger cites.
const M201_GATE = "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json";
const M201_GATE_SHA256 = "02db1cf033ec987bcca90bdb3a5d7d90a13f999048c41ef2d8999448e2ff3704";

const INPUT_IDS = [
  "t01_family_denominator",
  "t02_amending_act_provision",
  "t03_commencement_transition",
  "t04_edition_delta",
];

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(root, relative), "utf8");
}

function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

function sha256Of(relative) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relative))).digest("hex")}`;
}

function corpusExportDir() {
  const fromEnv = process.env[EXPORT_DIR_ENV];
  return typeof fromEnv === "string" && fromEnv.trim() !== ""
    ? fromEnv.trim()
    : EXPORT_DIR_DEFAULT;
}

function chainDir() {
  return path.resolve(root, corpusExportDir(), EXPORT_ROOT_TAIL, CHAIN_TAIL);
}

// ---------------------------------------------------------------------------
// fixtures and the live artifact
// ---------------------------------------------------------------------------

const liveText = readRepo(ARTIFACT);
const ledger = JSON.parse(liveText);
const amends = JSON.parse(readRepo(AMENDS_ARTIFACT));
const commencement = JSON.parse(readRepo(COMMENCEMENT_ARTIFACT));
const edition = JSON.parse(readRepo(EDITION_ARTIFACT));

/// Maps a declared-count key to the value its source artifact declares.
const DECLARED_COUNT_SOURCE = {
  layer1_records_total: () => amends.denominator.layer1_records_total,
  layer1_amending_acts: () => amends.denominator.layer1_amending_acts,
  amends_edges_total: () => amends.denominator.amends_edges_total,
  distinct_statya_refs: () => amends.denominator.distinct_statya_refs,
  "distinct_statya_refs_resolved": () => amends.denominator.distinct_statya_refs_resolved,
  "resolved-provision": () => amends.denominator.by_outcome["resolved-provision"],
  slots_total: () => commencement.denominator.slots_total,
  named_chain_slots: () => commencement.denominator.named_chain_slots,
  absent: () => commencement.denominator.by_evidence_class.absent,
  editions_total: () => edition.denominator.editions_total,
  editions_processed: () => edition.denominator.editions_processed,
  windows_total: () => edition.denominator.windows_total,
};

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("the artifact is repository-relative, ASCII-only, non-empty and canonical", () => {
  assert.ok(isRepoRelative(ARTIFACT));
  assert.ok(liveText.length > 0, "the artifact must not be empty");
  assert.ok(!liveText.includes("\n"), "the artifact must be one canonical line");
  assert.ok(!/[\x80-\uffff]/.test(liveText), "the artifact must be pure ASCII");
  assert.equal(JSON.stringify(ledger), liveText, "the artifact must be canonical JSON");
  assert.equal(liveText.trim(), liveText, "the artifact carries no surrounding whitespace");
});

test("the artifact carries the declared envelope and promotes nothing", () => {
  assert.equal(ledger.schema, SCHEMA);
  assert.equal(ledger.schema_version, 5);
  assert.equal(ledger.kind, KIND);
  assert.equal(ledger.task, TASK);
  assert.equal(ledger.lifecycle, LIFECYCLE);
  assert.equal(ledger.authoritative, false);
  assert.equal(ledger.requirement_id, REQUIREMENT_ID);
  assert.equal(ledger.disposition, DISPOSITION);
  assert.equal(ledger.disposition_decision, DISPOSITION_DECISION);
  assert.equal(ledger.coverage_verdict, COVERAGE_VERDICT);
  assert.equal(ledger.gates_promoted, 0);
  assert.equal(ledger.count_only, true);
  assert.equal(ledger.ascii_only, true);
  for (const banned of [
    '"validated"',
    '"complete"',
    '"leg_verdict":"proven"',
    '"leg_verdict":"validated"',
  ]) {
    assert.ok(!liveText.includes(banned), `the artifact must not carry ${banned}`);
  }
});

test("the frozen M201 boundary block cites the gate bytes and verdict", () => {
  assert.equal(ledger.frozen_m201_boundary.gate_relative_path, M201_GATE);
  assert.equal(ledger.frozen_m201_boundary.gate_sha256, `sha256:${M201_GATE_SHA256}`);
  assert.equal(ledger.frozen_m201_boundary.gate_coverage_verdict, COVERAGE_VERDICT);
  assert.equal(ledger.frozen_m201_boundary.gate_disposition, DISPOSITION);
  assert.equal(sha256Of(M201_GATE), `sha256:${M201_GATE_SHA256}`);
});

test("every declared input anchor is repository-relative, pinned and resolves on disk", () => {
  assert.ok(Array.isArray(ledger.inputs) && ledger.inputs.length === INPUT_IDS.length);
  assert.deepEqual(
    ledger.inputs.map((pin) => pin.input_id).sort(),
    [...INPUT_IDS].sort(),
  );
  for (const pin of ledger.inputs) {
    assert.ok(isRepoRelative(pin.relative_path), `${pin.input_id} path must be repository-relative`);
    assert.match(pin.input_sha256, SHA_PATTERN);
    assert.ok(Number.isInteger(pin.input_bytes) && pin.input_bytes > 0);
    const absolute = path.join(root, pin.relative_path);
    assert.ok(existsSync(absolute), `${pin.input_id} must resolve on disk`);
    const bytes = readFileSync(absolute);
    assert.equal(pin.input_bytes, bytes.length, `${pin.input_id} byte count must match`);
    assert.equal(
      pin.input_sha256,
      `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
      `${pin.input_id} pin must match live bytes`,
    );
  }
});

// ---------------------------------------------------------------------------
// aggregation over the four source artifacts
// ---------------------------------------------------------------------------

test("the ledger carries exactly the four R070 legs in order with only two verdicts", () => {
  assert.equal(ledger.legs.length, LEG_IDS.length);
  assert.deepEqual(
    ledger.legs.map((leg) => leg.leg_id),
    LEG_IDS,
  );
  for (const leg of ledger.legs) {
    assert.ok(LEG_VERDICTS.includes(leg.leg_verdict), `${leg.leg_id} verdict`);
    assert.ok(Array.isArray(leg.class_matched_ids) && leg.class_matched_ids.length === 0);
    assert.equal(leg.required_evidence_class, "human-annotation");
    assert.equal(leg.required_evidence_status, "absent");
    assert.ok(Array.isArray(leg.non_claims) && leg.non_claims.length > 0);
  }
  const commencementLeg = ledger.legs.find(
    (leg) => leg.leg_id === "commencement-and-transitional",
  );
  assert.equal(commencementLeg.leg_verdict, "slot-filled-not-proven");
});

test("every declared count is the count its source artifact declares", () => {
  for (const leg of ledger.legs) {
    const path = leg.tracked_evidence.artifact_relative_path;
    assert.ok(
      [AMENDS_ARTIFACT, COMMENCEMENT_ARTIFACT, EDITION_ARTIFACT].includes(path),
      `${leg.leg_id} must name a source artifact`,
    );
    const counts = leg.tracked_evidence.declared_counts;
    assert.ok(Object.keys(counts).length > 0);
    for (const [key, value] of Object.entries(counts)) {
      const source = DECLARED_COUNT_SOURCE[key];
      assert.ok(typeof source === "function", `${key} must be a known declared count`);
      assert.equal(value, source(), `${leg.leg_id} declared ${key} must equal its source`);
      assert.ok(Number.isInteger(value) && value >= 0);
    }
  }
});

// ---------------------------------------------------------------------------
// D539 quantifier rules
// ---------------------------------------------------------------------------

test("every quantifier is a named measure with a numeric threshold and an existing denominator source", () => {
  for (const leg of ledger.legs) {
    const quantifier = leg.quantifier;
    assert.equal(typeof quantifier.name, "string");
    assert.ok(quantifier.name.length > 0, `${leg.leg_id} quantifier name`);
    assert.ok(quantifier.unit.length > 0, `${leg.leg_id} quantifier unit`);
    assert.ok(
      !FORBIDDEN_QUANTIFIER_KEYS.includes(quantifier.name),
      `${leg.leg_id} quantifier name must not be an M202 inventory key`,
    );
    assert.ok(
      Number.isInteger(quantifier.threshold) && quantifier.threshold > 0,
      `${leg.leg_id} quantifier threshold must be a positive integer`,
    );
    assert.ok(
      String(quantifier.acceptance).includes(String(quantifier.threshold)),
      `${leg.leg_id} acceptance must carry its numeric threshold`,
    );
    assert.ok(
      /[<>=]{1,2}/.test(quantifier.acceptance),
      `${leg.leg_id} acceptance must carry a comparator`,
    );
    assert.ok(
      isRepoRelative(quantifier.denominator_source_path),
      `${leg.leg_id} denominator source path must be repository-relative`,
    );
    assert.ok(
      existsSync(path.join(root, quantifier.denominator_source_path)),
      `${leg.leg_id} denominator source path must exist on disk`,
    );
  }
});

test("quantifier names are pairwise distinct and no leg reuses an inventory key", () => {
  const names = ledger.legs.map((leg) => leg.quantifier.name);
  assert.equal(new Set(names).size, names.length);
  const declaredCountKeys = new Set(
    ledger.legs.flatMap((leg) => Object.keys(leg.tracked_evidence.declared_counts)),
  );
  for (const key of FORBIDDEN_QUANTIFIER_KEYS) {
    assert.ok(!names.includes(key));
  }
  assert.ok(declaredCountKeys.size > 0);
});

// ---------------------------------------------------------------------------
// S04 handoff and non-claims
// ---------------------------------------------------------------------------

test("the s04 handoff names the exact unmet conditions and promotes nothing", () => {
  const handoff = ledger.s04_handoff;
  assert.equal(handoff.coverage_verdict, COVERAGE_VERDICT);
  assert.equal(handoff.disposition, DISPOSITION);
  assert.ok(Array.isArray(handoff.unmet_conditions) && handoff.unmet_conditions.length >= 4);
  const joined = handoff.unmet_conditions.join(" ").toLowerCase();
  for (const fragment of [
    "legislative commencement and transitional evidence is absent",
    "class-matched human evidence is absent",
    "m207 human pilot was not run",
    "superseding the frozen pin suite",
    "d540",
  ]) {
    assert.ok(joined.includes(fragment), `the handoff must name ${fragment}`);
  }
});

test("the record carries the D416, D539, D552 and D216 non-claims", () => {
  assert.ok(Array.isArray(ledger.non_claims) && ledger.non_claims.length > 0);
  const joined = ledger.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `the non-claims must carry ${fragment}`);
  }
  assert.ok(!liveText.includes('"legislative"'), "no legislative value may be minted");
  for (const token of [
    "ActivationTrigger",
    "TransitionalResolver",
    "EvidenceAnchor",
    "LegislativeEffect",
  ]) {
    assert.ok(!liveText.includes(token), `the artifact must not mint ${token}`);
  }
});

// ---------------------------------------------------------------------------
// the frozen M201 pins
// ---------------------------------------------------------------------------

test("the two tracked frozen M201 pins are byte-identical", () => {
  assert.equal(sha256Of(FROZEN_TRACKED_CHAIN), `sha256:${FROZEN_TRACKED_CHAIN_SHA256}`);
  assert.equal(sha256Of(FROZEN_TRACKED_YAML), `sha256:${FROZEN_TRACKED_YAML_SHA256}`);
});

test("the cited C1 canon still resolves to its pinned sha256 when the corpus is present", () => {
  if (!existsSync(path.join(root, FROZEN_C1_CANON))) {
    console.log("M209_S03_C1_CANON_ABSENT");
    return;
  }
  const bytes = readFileSync(path.join(root, FROZEN_C1_CANON));
  assert.equal(
    `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
    "sha256:67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d",
  );
});

// ---------------------------------------------------------------------------
// the emitter and its suite
// ---------------------------------------------------------------------------

test("the emitter and the guard suite exist and stay inside their crates", () => {
  const module = readRepo(RUST_MODULE);
  for (const symbol of [
    /pub const LEDGER_FAIL_CLOSED_CODES: \[&str; \d+\]/,
    /pub const LEDGER_SCHEMA/,
    /pub struct ScopeLedgerEvidence/,
    /pub fn collect_scope_ledger/,
    /pub fn validate_scope_ledger/,
    /pub fn render_scope_ledger/,
    /pub fn scope_ledger_heartbeat/,
  ]) {
    assert.match(module, symbol);
  }
  const suite = readRepo(RUST_SUITE);
  for (const name of [
    /fn the_three_frozen_pins_are_byte_identical/,
    /fn the_ledger_keeps_r070_active_and_promotes_nothing/,
    /fn every_ledger_leg_is_bounded_supporting_or_slot_filled_not_proven/,
    /fn m208_declared_runtime_surfaces_stay_absent/,
  ]) {
    assert.match(suite, name);
  }
});

// ---------------------------------------------------------------------------
// documented code block equality
// ---------------------------------------------------------------------------

test("the documented code block equals the emitted and Rust code sets", () => {
  const source = readRepo(CONTRACT_PATH);
  const block = source.match(
    /\/\/ DOCUMENTED_FAIL_CLOSED_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_FAIL_CLOSED_END/,
  );
  assert.ok(block, "the documented fail-closed block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual([...documented].sort(), [...FAIL_CLOSED_CODES].sort());
  assert.deepEqual([...ledger.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());

  const module = readRepo(RUST_MODULE);
  const rustBlock = module.match(/pub const LEDGER_FAIL_CLOSED_CODES: \[&str; \d+\] =\s*\[([\s\S]*?)\];/);
  assert.ok(rustBlock, "the Rust LEDGER_FAIL_CLOSED_CODES array must exist");
  assert.deepEqual(
    [...rustBlock[1].matchAll(/"([a-z0-9_-]+)"/g)].map((match) => match[1]).sort(),
    [...FAIL_CLOSED_CODES].sort(),
    "the Rust array must equal the emitted set",
  );
});

// ---------------------------------------------------------------------------
// corpus-gated live re-derivation (counts only)
// ---------------------------------------------------------------------------

test("the live chain directory re-derives the ledger's edition total", () => {
  if (!existsSync(chainDir())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const directory = chainDir();
  let admitted = 0;
  for (const name of readdirSync(directory)) {
    if (!statSync(path.join(directory, name)).isFile()) continue;
    if (name.endsWith(".xml") && name.startsWith("edition-")) admitted += 1;
  }
  const editionLeg = ledger.legs.find((leg) => leg.leg_id === "edition-delta");
  assert.equal(
    admitted,
    editionLeg.tracked_evidence.declared_counts.editions_total,
    "the live admitted edition count must reproduce the declared total",
  );
  assert.equal(admitted, edition.denominator.editions_total);
  const t01 = JSON.parse(readRepo(FAMILY_ARTIFACT));
  assert.equal(admitted, t01.chain.editions_total);
  console.log(
    `[r070-scope-ledger] legs=${ledger.legs.length} editions=${admitted} gates_promoted=${ledger.gates_promoted}`,
  );
});

test("M209 S03 scope-ledger markers", () => {
  assert.match(SCHEMA, /^law-nexus\/r070-scope-ledger\/v1$/);
  assert.match(KIND, /^m209-s03-r070-scope-ledger$/);
  assert.equal(TASK, "T05");
  assert.equal(ledger.gates_promoted, 0);
  assert.equal(ledger.disposition, "active");
  assert.equal(ledger.coverage_verdict, "incomplete-because-not-every-edition");
});
