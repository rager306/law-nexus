#!/usr/bin/env node
// M209-2yg6ix S04 T05 requirement acceptance ledger (D430, D416, D540, D545,
// D558, D559, D560, D561).
//
// WHY THIS FILE EXISTS
// S04 decided the seven R035 gates gate-by-gate (T03) and the four R070 legs
// scope-by-scope (T04), recounted the live corpus (T02) and audited the whole
// evidence chain node by node (T01). Those are four artifacts with four
// vocabularies. Milestone validation and milestone completion need one
// source-bound acceptance surface they can cite: how many gates and legs are
// accepted, at which scope, which owner decisions are still outstanding, and
// what was NOT claimed. This script assembles that surface.
//
// THE RULE IT APPLIES
//   disposition(row) is carried, never re-derived: a gate row arrives with the
//   disposition T03 recorded and a leg row arrives with the disposition T04
//   recorded. This ledger may only (a) copy it, (b) count it, and (c) refuse to
//   publish if the copy disagrees with the row set, the row's debt, the declared
//   aggregate or the upstream artifact. accepted-at-bounded-scope accepts only
//   the bounded named quantifier; it never asserts the required evidence class,
//   never promotes a gate or a leg and never closes a requirement (D558).
//
// WHAT IT IS NOT
//   It does not mutate any requirement record, does not write GSD state, does
//   not attach a proof package, does not promote a gate or a leg, does not
//   admit the punkt registry rows (D540 keeps `not-adopted`), and does not
//   adjudicate the GATE-G015 recorded conflict (it stays an owner decision).
//   The R035 register, the S03 R070 scope ledger, the T03/T04 adjudications,
//   the T01/T02 verification artifacts, the punkt checkpoint and the canonical
//   admissions source are read-only inputs pinned by bytes and sha256.
//
// THE RUST BOUNDARY GUARD (D561)
//   The ledger is anchored by crates/ln-kb-ontology/tests/m209_s04_acceptance_boundary.rs,
//   which include_str!-compiles this artifact and asserts its semantic
//   invariants plus in-memory mutation refusals. No raw sha256 pin of the
//   ledger is embedded in Rust: the guard is semantic, not a digest freeze.
//
// OUTPUT
//   prd/migration/rust-evidence/m209-s04-requirement-acceptance.json
//     schema law-nexus/m209-requirement-acceptance/v1
//
// USAGE
//   node scripts/m209_s04_acceptance_ledger.mjs --mode ledger --out prd/migration/rust-evidence/m209-s04-requirement-acceptance.json
//   node scripts/m209_s04_acceptance_ledger.mjs --mode ledger --check
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

export const SCHEMA = "law-nexus/m209-requirement-acceptance/v1";
export const KIND = "m209-s04-requirement-acceptance";
export const MILESTONE = "M209-2yg6ix";
export const SLICE = "S04";
export const TASK = "T05";
export const ARTIFACT_PATH =
  "prd/migration/rust-evidence/m209-s04-requirement-acceptance.json";
export const OUT_PREFIX = "prd/migration/rust-evidence/m209-s04-";
export const RUST_GUARD_PATH = "crates/ln-kb-ontology/tests/m209_s04_acceptance_boundary.rs";
export const DECISION = "D561";
export const ACCEPTANCE_DECISION = "D558";
export const PUNKT_DECISION = "D540";
export const COVERAGE_VERDICT = "incomplete-because-not-every-edition";

export const GATE_ADJUDICATION_PATH =
  "prd/migration/rust-evidence/m209-s04-r035-gate-adjudication.json";
export const SCOPE_ADJUDICATION_PATH =
  "prd/migration/rust-evidence/m209-s04-r070-scope-adjudication.json";
export const CORROBORATION_PATH =
  "prd/migration/rust-evidence/m209-s04-corroboration-evidence.json";
export const CORPUS_RECOUNT_PATH =
  "prd/migration/rust-evidence/m209-s04-corpus-recount-evidence.json";
export const EDITION_RECONCILIATION_PATH =
  "prd/migration/rust-evidence/m209-s04-edition-coverage-reconciliation.json";
export const GATE_REGISTER_PATH = "prd/architecture/m209-s01-r035-gate-register.json";
export const S03_SCOPE_LEDGER_PATH =
  "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json";
export const PUNKT_CHECKPOINT_PATH = "prd/architecture/m209-s01-punkt-decision.md";
export const ADMISSIONS_PATH = "prd/architecture/kb-hierarchy-registry-admissions.yaml";

// The nine declared inputs. Each pin is re-computed from the live bytes on every
// build and every --check; a disagreement is `input_hash_mismatch`. The pins are
// frozen here on purpose: a later edit of an upstream artifact must fail the leak,
// not silently move the acceptance surface.
export const INPUT_PINS = Object.freeze([
  {
    input_id: "r035_gate_adjudication",
    input_kind: "json",
    relative_path: GATE_ADJUDICATION_PATH,
    bytes: 41881,
    sha256: "sha256:fa50f3fa6f0848cf1a944e68e45b82e54bf0ae9e853b25c06b5c41090ef84586",
  },
  {
    input_id: "r070_scope_adjudication",
    input_kind: "json",
    relative_path: SCOPE_ADJUDICATION_PATH,
    bytes: 27939,
    sha256: "sha256:bb8214a14637d14690934d2c363d4b68657ad0fa500d23b6d2330d8057f5ff66",
  },
  {
    input_id: "corroboration_evidence",
    input_kind: "json",
    relative_path: CORROBORATION_PATH,
    bytes: 36319,
    sha256: "sha256:94dce091c6fb306ccada859cc59ef2e423d51ba28ea5878851aedb1d7fe21436",
  },
  {
    input_id: "corpus_recount_evidence",
    input_kind: "json",
    relative_path: CORPUS_RECOUNT_PATH,
    bytes: 12418,
    sha256: "sha256:f4b1eb0cf69b472da9a4e328d7bc158fa0b250cae910f1dce121445939a40864",
  },
  {
    input_id: "edition_coverage_reconciliation",
    input_kind: "json",
    relative_path: EDITION_RECONCILIATION_PATH,
    bytes: 12862,
    sha256: "sha256:65d0e02499d3b6e9d4a7b172549edcb1e67b8a014074a9b1203a49ca8d2ca55f",
  },
  {
    input_id: "r035_gate_register",
    input_kind: "json",
    relative_path: GATE_REGISTER_PATH,
    bytes: 35830,
    sha256: "sha256:bbbf9f56864f4abd5e769b06ad9dc12ef0c6ee40798e0ca0992a5037bf60fd4d",
  },
  {
    input_id: "s03_r070_scope_ledger",
    input_kind: "json",
    relative_path: S03_SCOPE_LEDGER_PATH,
    bytes: 7850,
    sha256: "sha256:b640b2e114f8872972c11f2201b88d5248a04ba64491252bd42536831a34b4cc",
  },
  {
    input_id: "punkt_decision_checkpoint",
    input_kind: "markdown",
    relative_path: PUNKT_CHECKPOINT_PATH,
    bytes: 18899,
    sha256: "sha256:0b59f95a96d54cdcf62a08a026a082102fa46d61e55fa73244ae9f242602f2b0",
  },
  {
    input_id: "kb_hierarchy_registry_admissions",
    input_kind: "yaml",
    relative_path: ADMISSIONS_PATH,
    bytes: 19982,
    sha256: "sha256:1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19",
  },
]);

// The closed acceptance vocabulary (D558). Identical to the T03/T04 vocabulary:
// this ledger introduces no fifth disposition and never narrows the set.
export const DISPOSITION_VOCABULARY = Object.freeze([
  "accepted-at-bounded-scope",
  "hold-requires-owner-decision",
  "hold-with-precise-debt",
  "rejected-as-stated",
]);

// The seven R035 gate ids in the T03 artifact order.
export const GATE_ORDER = Object.freeze([
  "GATE-AKOMA-FRBR-NORMALIZATION",
  "GATE-BFO-GOST-ALIGNMENT",
  "GATE-G015",
  "GATE-LKIF-DEONTIC-BENCHMARK",
  "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
  "GATE-PILOT-SCALE-READINESS",
  "GATE-RUSLEGALCORE-SCOPE",
]);

// The four R070 leg ids in the T04 artifact order.
export const LEG_ORDER = Object.freeze([
  "amending-acts",
  "affected-provisions",
  "commencement-and-transitional",
  "edition-delta",
]);

export const GATE_OWNER_DECISION_ID = "GATE-G015";

// The five owner decisions the plan requires the ledger to carry, plus the
// m208 admission that T04 already carried (carried as a superset, never dropped:
// see the `owner-decision-enumeration-is-a-superset` non-claim).
export const REQUIRED_OWNER_DECISION_KINDS = Object.freeze([
  "punkt-registry-admission",
  "gate-g015-recorded-conflict",
  "corpus-scale-legislative-commencement-source",
  "m207-class-matched-human-pilot",
  "canonical-admission-pair-swap",
]);

// The twelve mandatory grant fields of the M209/S01 punkt checkpoint, in the
// checkpoint's own order. A grant that does not name all twelve is not a grant.
export const PUNKT_GRANT_FIELDS = Object.freeze([
  "verdict_line",
  "granted_by",
  "scope",
  "cc_identity_form",
  "admission_rows",
  "declared_denominator",
  "selected_gates_and_deferred_gates",
  "sources_checked",
  "fail_closed_boundary",
  "non_claims",
  "owning_surfaces",
  "supersede_rebind",
]);

// The closed, documented fail-closed vocabulary. The contract test asserts this
// exact set is emittable (each code fires on a mutated copy) and that no
// undocumented code can be raised.
export const FAIL_CLOSED_CODES = Object.freeze([
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

const RULE_RECONCILIATION_NOTE =
  "the plan enumerates five owner decisions for this ledger (punkt admission, GATE-G015, the corpus-scale commencement source, the M207 human pilot and the D545 admission-pair swap) while the T04 scope adjudication already carried a sixth (the M208 S03/S04 admission); this ledger carries all six rather than dropping one, so the enumeration is a documented superset of the plan list and no outstanding owner decision is silently smoothed away";

export const NON_CLAIMS = Object.freeze([
  "this-ledger-closes-and-promotes-no-requirement (D430/D416): it publishes dispositions, it does not validate, close, satisfy or promote R035 or R070, and it attaches no proof package.",
  "requirement-records-are-not-mutated: R035 stays active with D430 and R070 stays active with D416; no requirement row is written, no GSD state is changed and no requirement record is touched by this ledger.",
  "bounded-scope-acceptance-is-not-validation (D558): the three accepted R070 legs and the zero accepted R035 gates accept only their bounded named quantifiers; the required human-annotation evidence class stays absent and is carried as bounded-scope debt.",
  "punkt-is-not-admitted (D540): the punkt registry admission stays not-adopted with punkt_rows_admitted 0 and owner_admission_ref none; the twelve mandatory grant fields are recorded as an outstanding owner decision, not satisfied here.",
  "gate-g015-requires-an-owner-decision: the recorded state conflict of GATE-G015 is preserved and carried as an outstanding owner decision; this ledger never collapses it into a hold-with-debt or an acceptance.",
  "dispositions-are-carried-not-re-derived (D558): every gate row is the T03 row and every leg row is the T04 row, byte-for-byte on the disposition and on the debt array; a disagreement with the upstream artifact fails closed instead of being smoothed.",
  "no-proof-package-is-attached: proof_packages_attached is 0 and every gate row keeps proof_package null; gates_promoted and legs_promoted stay 0.",
  "rust-boundary-guard-is-semantic-not-a-digest-freeze (D561): the ledger is anchored by an include_str!-compiled test that asserts its invariants and refuses mutated in-memory copies; no raw sha256 pin of this ledger is embedded in Rust.",
  "owner-decision-enumeration-is-a-superset: the plan lists five outstanding owner decisions and this ledger carries six (the M208 S03/S04 admission is kept from T04 rather than dropped)",
  "independent-verification-ceiling-is-recorded-not-hidden (D559): the corpus verification summary cites the T01 binding/digest/arithmetic audit and the T02 live recount; parser-level denominators stay corroborated by byte pins and deterministic re-render, never by a second classifier implementation.",
  "edition-reconciliation-is-carried-whole (D560): 118 editions partition into 1 core-act-initial-edition plus 117 amending-act-date-matched with named residual classes; the class partition sums to 118 and 0 editions are silently dropped.",
  "count-only-ascii-only-and-repository-relative: only rule ids, counts, thresholds, repository-relative paths, byte counts and sha256 pins are written; no corpus text, XML bytes or provider prose is carried and no absolute or ignored-overlay path is emitted.",
  "pending-milestone-closeout-is-not-fired-here: this artifact is the acceptance surface the milestone validation and completion units cite; it performs neither step itself.",
]);

// Provider prose markers that must never reach a count-only artifact.
const RAW_TEXT_MARKERS = Object.freeze([
  "consultantplus://",
  "<w:",
  "screenTip",
  "\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d",
]);

// ---------------------------------------------------------------------------
// errors and small guards
// ---------------------------------------------------------------------------

export class LedgerError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "LedgerError";
    this.code = code;
    this.detail = detail;
  }
}

export function fail(code, detail) {
  throw new LedgerError(code, detail);
}

export function assertNonEmpty(text) {
  if (typeof text !== "string" || text.length === 0) {
    fail("artifact_empty", "rendered evidence is empty");
  }
  return true;
}

export function assertAsciiOnly(text) {
  for (let index = 0; index < text.length; index += 1) {
    if (text.charCodeAt(index) > 0x7f) {
      fail("non_ascii_evidence", `non-ASCII code unit at index ${index}`);
    }
  }
  return true;
}

export function assertNoRawText(text) {
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) fail("raw_text_leak", `artifact carries ${marker}`);
  }
  return true;
}

export function renderEvidence(bundle) {
  return `${JSON.stringify(bundle)}\n`;
}

export function checkRenderedBytes(rendered, committed) {
  if (rendered !== committed) {
    fail("evidence_drift", "rendered bytes differ from the committed artifact");
  }
  return true;
}

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== "." && part !== "..");
}

export function assertRepoRelative(relative, label) {
  if (!isRepoRelative(relative)) {
    fail("path_not_repository_relative", `${label}: ${String(relative)}`);
  }
  return true;
}

export function sha256Hex(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

export function sha256Pin(bytes) {
  return `sha256:${sha256Hex(bytes)}`;
}

export function isTrackedPath(relativePath, root = REPO_ROOT) {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: root,
      stdio: "ignore",
    });
    return true;
  } catch {
    return false;
  }
}

export function assertAllChecksPass(checks) {
  const failed = checks.filter((check) => check.verdict !== "pass");
  if (failed.length > 0) {
    fail("cross_check_failed", failed.map((check) => check.check_id).join(","));
  }
  return true;
}

export function sameJson(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function countBy(rows, key, value) {
  return rows.filter((row) => row[key] === value).length;
}

// ---------------------------------------------------------------------------
// artifact loading
// ---------------------------------------------------------------------------

export function loadTextArtifact(relativePath, label, probes = {}) {
  assertRepoRelative(relativePath, label);
  const read = probes.readFileSync ?? readFileSync;
  const exists = probes.existsSync ?? existsSync;
  const root = probes.repoRoot ?? REPO_ROOT;
  const absolute = path.join(root, relativePath);
  if (!exists(absolute)) fail("input_absent", relativePath);
  let raw;
  try {
    raw = read(absolute, "utf8");
  } catch (error) {
    fail("input_absent", `${relativePath}: ${error.code ?? error.message}`);
  }
  const text = typeof raw === "string" ? raw : Buffer.from(raw).toString("utf8");
  const bytes = Buffer.from(text, "utf8");
  return { relative_path: relativePath, bytes: bytes.length, sha256: sha256Pin(bytes), text };
}

export function loadJsonArtifact(relativePath, label, probes = {}) {
  const loaded = loadTextArtifact(relativePath, label, probes);
  let parsed;
  try {
    parsed = JSON.parse(loaded.text);
  } catch (error) {
    fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
  }
  return { ...loaded, parsed };
}

export function loadInputs(probes = {}) {
  const jsonIds = new Set(["json"]);
  const inputs = {};
  for (const pin of INPUT_PINS) {
    inputs[pin.input_id] = jsonIds.has(pin.input_kind)
      ? loadJsonArtifact(pin.relative_path, `input ${pin.input_id}`, probes)
      : loadTextArtifact(pin.relative_path, `input ${pin.input_id}`, probes);
  }
  return inputs;
}

// ---------------------------------------------------------------------------
// pins
// ---------------------------------------------------------------------------

export function assertInputPins(inputs, probes = {}) {
  const isTracked = probes.isTracked ?? ((relative) => isTrackedPath(relative, probes.repoRoot));
  const checks = [];
  for (const pin of INPUT_PINS) {
    const loaded = inputs[pin.input_id];
    if (loaded === undefined || loaded === null) fail("input_absent", pin.relative_path);
    assertRepoRelative(pin.relative_path, `input ${pin.input_id}`);
    if (!isTracked(pin.relative_path)) fail("input_not_tracked", pin.relative_path);
    if (loaded.bytes !== pin.bytes || loaded.sha256 !== pin.sha256) {
      fail(
        "input_hash_mismatch",
        `${pin.relative_path} live=${loaded.bytes}|${loaded.sha256} declared=${pin.bytes}|${pin.sha256}`,
      );
    }
    checks.push({
      check_id: `input_pin_${pin.input_id}`,
      scope: `declared input pin ${pin.relative_path}`,
      expected: `${pin.bytes}|${pin.sha256}`,
      observed: `${loaded.bytes}|${loaded.sha256}`,
      verdict: "pass",
    });
  }
  return checks;
}

// The register, the S03 scope ledger and the admissions YAML are also pinned
// inside the artifacts this ledger reads. Those declared pins are re-checked
// against the live bytes: an upstream self-description that no longer agrees
// with the file it describes is `input_hash_mismatch`, never a soft warning.
export function assertUpstreamPins(inputs) {
  const checks = [];
  const expect = (checkId, scope, declared, live) => {
    if (declared !== null && declared !== undefined && declared !== live) {
      fail("input_hash_mismatch", `${scope}: declared=${String(declared)} live=${String(live)}`);
    }
    checks.push({
      check_id: checkId,
      scope,
      expected: String(live),
      observed: String(declared),
      verdict: "pass",
    });
  };

  const gateAdjudication = inputs.r035_gate_adjudication.parsed;
  const registerPin = gateAdjudication?.canonical_sources?.gate_register;
  if (registerPin === null || typeof registerPin !== "object") {
    fail("input_artifact_shape_invalid", "T03 canonical_sources.gate_register is absent");
  }
  expect(
    "upstream_register_pin",
    "T03 declared gate-register bytes|sha256 vs live register",
    `${registerPin.bytes}|${registerPin.sha256}`,
    `${inputs.r035_gate_register.bytes}|${inputs.r035_gate_register.sha256}`,
  );
  expect(
    "upstream_register_path",
    "T03 declared gate-register path vs ledger input path",
    registerPin.relative_path,
    GATE_REGISTER_PATH,
  );

  const scopeAdjudication = inputs.r070_scope_adjudication.parsed;
  const ledgerPin = scopeAdjudication?.ledger_source;
  if (ledgerPin === null || typeof ledgerPin !== "object") {
    fail("input_artifact_shape_invalid", "T04 ledger_source is absent");
  }
  expect(
    "upstream_s03_ledger_pin",
    "T04 declared S03 scope-ledger bytes|sha256 vs live ledger",
    `${ledgerPin.bytes}|${ledgerPin.sha256}`,
    `${inputs.s03_r070_scope_ledger.bytes}|${inputs.s03_r070_scope_ledger.sha256}`,
  );
  const m201 = scopeAdjudication?.m201_boundary;
  if (m201 === null || typeof m201 !== "object") {
    fail("input_artifact_shape_invalid", "T04 m201_boundary is absent");
  }
  expect(
    "upstream_m201_coverage",
    "T04 frozen M201 coverage verdict",
    m201.coverage_verdict,
    COVERAGE_VERDICT,
  );

  const checkpoint = inputs.punkt_decision_checkpoint.text;
  const declaredAdmissions = checkpointPinFor(checkpoint, ADMISSIONS_PATH);
  if (declaredAdmissions === null) {
    fail(
      "input_artifact_shape_invalid",
      "the punkt checkpoint declares no pin for the admissions source",
    );
  }
  expect(
    "upstream_admissions_pin",
    "punkt checkpoint declared admissions sha256 vs live admissions",
    declaredAdmissions,
    inputs.kb_hierarchy_registry_admissions.sha256,
  );
  return checks;
}

export function checkpointPinFor(checkpointText, relativePath) {
  const escaped = relativePath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = checkpointText.match(new RegExp(`\`${escaped}\`\\s*\\|\\s*\`([0-9a-f]{64})\``));
  return match === null ? null : `sha256:${match[1]}`;
}

// ---------------------------------------------------------------------------
// row carrying
// ---------------------------------------------------------------------------

export function assertRowSet(ids, order, kind) {
  const code = kind === "gate" ? "missing_gate_row" : "missing_leg_row";
  if (!Array.isArray(ids) || ids.length !== order.length) {
    fail(code, `row count ${String(ids?.length)} != ${order.length}`);
  }
  if (new Set(ids).size !== ids.length) fail(code, `duplicate row ids: ${ids.join(",")}`);
  for (const id of order) {
    if (!ids.includes(id)) fail(code, `missing ${id}`);
  }
  for (const id of ids) {
    if (!order.includes(id)) fail(code, `unexpected ${id}`);
  }
  return true;
}

export function validateDebtItem(debt) {
  if (debt === null || typeof debt !== "object") {
    fail("debt_record_incomplete", "debt entry is not an object");
  }
  for (const key of ["quantifier_name", "acceptance_text", "missing_artifact_kind", "unblock_condition"]) {
    if (typeof debt[key] !== "string" || debt[key] === "") {
      fail("debt_record_incomplete", `missing ${key}`);
    }
  }
  if (typeof debt.required_evidence_class !== "string" || debt.required_evidence_class === "") {
    fail("debt_record_incomplete", "missing required_evidence_class");
  }
  const evidence = debt.closest_evidence;
  if (evidence === null || typeof evidence !== "object") {
    fail("debt_record_incomplete", "missing closest_evidence");
  }
  const paths = Array.isArray(evidence.relative_paths)
    ? evidence.relative_paths
    : evidence.artifacts;
  if (!Array.isArray(paths)) {
    fail("debt_record_incomplete", "closest_evidence carries no path array");
  }
  if (typeof evidence.why_insufficient !== "string" || evidence.why_insufficient === "") {
    fail("debt_record_incomplete", "closest_evidence.why_insufficient is empty");
  }
  for (const relative of paths) assertRepoRelative(relative, "debt closest_evidence path");
  return true;
}

export const ROW_KEYS = Object.freeze({
  gate: { id: "gate_id", disposition: "disposition" },
  leg: { id: "leg_id", disposition: "scope_disposition" },
});

export function validateCarriedRow(row, upstream, kind) {
  const keys = ROW_KEYS[kind];
  if (keys === undefined) fail("carried_row_drift", `unknown row kind ${String(kind)}`);
  const rowId = row[keys.id];
  if (!DISPOSITION_VOCABULARY.includes(row[keys.disposition])) {
    fail("unsupported_disposition", `${rowId}:${String(row[keys.disposition])}`);
  }
  if (!DISPOSITION_VOCABULARY.includes(upstream?.[keys.disposition])) {
    fail("disposition_upgraded", `${rowId}: upstream disposition unsupported`);
  }
  if (row[keys.disposition] !== upstream[keys.disposition]) {
    fail(
      "disposition_upgraded",
      `${rowId}: ledger=${row[keys.disposition]} upstream=${upstream[keys.disposition]}`,
    );
  }
  if (kind === "gate" && row.proof_package !== null) {
    fail("proof_package_claimed", `${rowId}: proof_package is not null`);
  }
  const hold = row[keys.disposition].startsWith("hold");
  if (!Array.isArray(row.debt) || row.debt.length === 0) {
    fail(
      hold ? "debt_dropped_for_hold_row" : "debt_not_carried",
      `${rowId} carries no debt record`,
    );
  }
  for (const debt of row.debt) validateDebtItem(debt);
  if (!Array.isArray(upstream.debt) || !sameJson(row.debt, upstream.debt)) {
    fail("debt_not_carried", `${rowId}: debt differs from the upstream artifact`);
  }
  for (const key of Object.keys(upstream)) {
    if (key === keys.disposition || key === "debt") continue;
    if (!sameJson(row[key], upstream[key])) {
      fail("carried_row_drift", `${rowId}:${key}`);
    }
  }
  if (Object.keys(row).length !== Object.keys(upstream).length) {
    fail("carried_row_drift", `${rowId}: carried row key set differs from upstream`);
  }
  return true;
}

export function carriedRows(upstreamRows, order, kind) {
  const keys = ROW_KEYS[kind];
  if (!Array.isArray(upstreamRows)) {
    fail("input_artifact_shape_invalid", `${kind} rows are absent`);
  }
  const ids = upstreamRows.map((row) => row?.[keys.id]);
  assertRowSet(ids, order, kind);
  const ordered = order.map((id) => upstreamRows.find((row) => row[keys.id] === id));
  for (const row of ordered) validateCarriedRow(row, row, kind);
  return ordered;
}

export function rowDebtIds(row) {
  if (!Array.isArray(row.debt)) return [];
  return row.debt.map((debt, index) => `${debt.debt_id ?? `${ROW_KEYS.gate.id}#${index}`}`);
}

export function debtIndex(rows, kind) {
  const keys = ROW_KEYS[kind];
  return rows.map((row) => ({
    row_id: row[keys.id],
    row_kind: kind,
    disposition: row[keys.disposition],
    debt_count: Array.isArray(row.debt) ? row.debt.length : 0,
    debt_ids: rowDebtIds(row),
  }));
}

// ---------------------------------------------------------------------------
// requirements, aggregates, promotion counters
// ---------------------------------------------------------------------------

export function validateRequirement(entry) {
  if (entry === null || typeof entry !== "object") {
    fail("requirement_status_changed", "requirement entry is not an object");
  }
  if (entry.requirement_id !== "R035" && entry.requirement_id !== "R070") {
    fail("requirement_status_changed", `unexpected requirement ${String(entry.requirement_id)}`);
  }
  if (entry.status !== "active") {
    fail("requirement_status_changed", `${entry.requirement_id}:${String(entry.status)}`);
  }
  const expectedDecision = entry.requirement_id === "R035" ? "D430" : "D416";
  if (entry.disposition_decision !== expectedDecision) {
    fail(
      "requirement_status_changed",
      `${entry.requirement_id}:${String(entry.disposition_decision)} != ${expectedDecision}`,
    );
  }
  if (entry.promotion !== "none") {
    fail("promotion_claimed", `${entry.requirement_id} promotion=${String(entry.promotion)}`);
  }
  return true;
}

export function recomputeTotals(bundle) {
  const gates = bundle.gates ?? [];
  const legs = bundle.legs ?? [];
  return {
    gate_count: gates.length,
    leg_count: legs.length,
    gates_accepted: countBy(gates, "disposition", "accepted-at-bounded-scope"),
    gates_hold: countBy(gates, "disposition", "hold-with-precise-debt"),
    gates_owner_decision: countBy(gates, "disposition", "hold-requires-owner-decision"),
    gates_rejected: countBy(gates, "disposition", "rejected-as-stated"),
    legs_accepted: countBy(legs, "scope_disposition", "accepted-at-bounded-scope"),
    legs_hold: countBy(legs, "scope_disposition", "hold-with-precise-debt"),
    legs_owner_decision: countBy(legs, "scope_disposition", "hold-requires-owner-decision"),
    legs_rejected: countBy(legs, "scope_disposition", "rejected-as-stated"),
    debt_total: [...gates, ...legs].reduce(
      (total, row) => total + (Array.isArray(row.debt) ? row.debt.length : 0),
      0,
    ),
    empty_debt_rows: [...gates, ...legs].filter(
      (row) => !Array.isArray(row.debt) || row.debt.length === 0,
    ).length,
  };
}

export function validateAggregates(bundle) {
  const totals = recomputeTotals(bundle);
  const byId = new Map((bundle.requirements ?? []).map((entry) => [entry.requirement_id, entry]));
  const r035 = byId.get("R035");
  const r070 = byId.get("R070");
  if (r035 === undefined || r070 === undefined) {
    fail("requirement_status_changed", "requirements[] must carry R035 and R070");
  }
  const pairs = [
    ["gate_count", bundle.gate_count, totals.gate_count],
    ["gates_total", r035.gates_total, totals.gate_count],
    ["gates_accepted", r035.gates_accepted, totals.gates_accepted],
    ["gates_hold", r035.gates_hold, totals.gates_hold],
    ["gates_owner_decision", r035.gates_owner_decision, totals.gates_owner_decision],
    ["gates_rejected", r035.gates_rejected, totals.gates_rejected],
    ["leg_count", bundle.leg_count, totals.leg_count],
    ["legs_total", r070.legs_total, totals.leg_count],
    ["accepted_at_bounded_scope", r070.accepted_at_bounded_scope, totals.legs_accepted],
    ["hold", r070.hold, totals.legs_hold],
    ["legs_owner_decision", r070.legs_owner_decision, totals.legs_owner_decision],
    ["legs_rejected", r070.legs_rejected, totals.legs_rejected],
    ["debt_total", bundle.debt_total, totals.debt_total],
    ["empty_debt_rows", bundle.empty_debt_rows, totals.empty_debt_rows],
  ];
  for (const [label, declared, recomputed] of pairs) {
    if (declared !== recomputed) {
      fail("aggregate_mismatch", `${label}: declared=${String(declared)} recomputed=${String(recomputed)}`);
    }
  }
  if (
    totals.gates_accepted + totals.gates_hold + totals.gates_owner_decision + totals.gates_rejected !==
    totals.gate_count
  ) {
    fail("aggregate_mismatch", "gate disposition partition does not sum to the gate count");
  }
  if (
    totals.legs_accepted + totals.legs_hold + totals.legs_owner_decision + totals.legs_rejected !==
    totals.leg_count
  ) {
    fail("aggregate_mismatch", "leg disposition partition does not sum to the leg count");
  }
  return totals;
}

export function validatePromotionCounters(bundle) {
  if (bundle.lifecycle !== "[bounded]") {
    fail("promotion_claimed", `lifecycle=${String(bundle.lifecycle)}`);
  }
  if (bundle.authoritative !== false) {
    fail("promotion_claimed", `authoritative=${String(bundle.authoritative)}`);
  }
  for (const key of [
    "gates_promoted",
    "legs_promoted",
    "proof_packages_attached",
    "requirement_records_mutated",
  ]) {
    if (bundle[key] !== 0) fail("promotion_claimed", `${key}=${String(bundle[key])}`);
  }
  return true;
}

export function validateProofPackages(bundle) {
  for (const row of bundle.gates ?? []) {
    if (row.proof_package !== null) {
      fail("proof_package_claimed", `${String(row.gate_id)}: proof_package is not null`);
    }
  }
  if (bundle.proof_packages_attached !== 0) {
    fail("proof_package_claimed", "proof_packages_attached is not 0");
  }
  return true;
}

// ---------------------------------------------------------------------------
// edition reconciliation, corpus verification, punkt
// ---------------------------------------------------------------------------

export function validateEditionReconciliation(reconciliation) {
  if (reconciliation === null || typeof reconciliation !== "object") {
    fail("edition_partition_broken", "edition reconciliation is absent");
  }
  const classes = reconciliation.classes;
  if (!Array.isArray(classes) || classes.length === 0) {
    fail("edition_partition_broken", "class partition is absent");
  }
  const total = classes.reduce((sum, entry) => sum + entry.count, 0);
  if (total !== reconciliation.classes_total || total !== reconciliation.editions_total) {
    fail(
      "edition_partition_broken",
      `class sum ${total} != classes_total ${reconciliation.classes_total} / editions_total ${reconciliation.editions_total}`,
    );
  }
  if (reconciliation.silently_dropped_total !== 0) {
    fail("silently_dropped_edition", String(reconciliation.silently_dropped_total));
  }
  for (const residual of reconciliation.residuals ?? []) {
    if (typeof residual.residual_id !== "string" || residual.residual_id === "") {
      fail("edition_partition_broken", "a residual carries no named reason code");
    }
    if (typeof residual.count !== "number") {
      fail("edition_partition_broken", `${residual.residual_id}: count is not numeric`);
    }
  }
  return true;
}

export function validateCorpusVerification(corpus) {
  if (corpus === null || typeof corpus !== "object") {
    fail("corpus_verification_failed", "corpus verification summary is absent");
  }
  for (const key of [
    "bindings_failed",
    "digests_failed",
    "arithmetic_failed",
    "cross_artifact_failed",
    "frozen_boundary_failed",
    "recount_cross_checks_failed",
    "recount_promotion_checks_failed",
    "window_mismatches_total",
  ]) {
    if (corpus[key] !== 0) {
      fail("corpus_verification_failed", `${key}=${String(corpus[key])}`);
    }
  }
  if (corpus.editions_files_total !== corpus.editions_accepted_total) {
    fail("corpus_verification_failed", "edition listing files != accepted editions");
  }
  return true;
}

export function parsePunktCheckpoint(checkpointText, admissionsText) {
  const admission = checkpointText.match(/^\*\*admission: (granted|not-adopted)\*\*$/m);
  const punktAdmission = checkpointText.match(/^\*\*punkt_admission:\*\*\s*(\S+)\s*$/m);
  const rowsAdmitted = checkpointText.match(/^\*\*punkt_rows_admitted:\*\*\s*(\d+)\s*$/m);
  const ownerRef = checkpointText.match(/^\*\*owner_admission_ref:\*\*\s*(\S+)\s*$/m);
  return {
    admission: admission === null ? null : admission[1],
    punkt_admission: punktAdmission === null ? null : punktAdmission[1],
    declared_rows_admitted: rowsAdmitted === null ? null : Number(rowsAdmitted[1]),
    owner_admission_ref: ownerRef === null ? null : ownerRef[1],
    live_rows_admitted: (admissionsText.match(/level:\s*punkt\b/g) ?? []).length,
    checkpoint_decision: (checkpointText.match(/D540/) ?? []).length > 0 ? PUNKT_DECISION : null,
  };
}

export function validatePunkt(punkt) {
  if (punkt === null || typeof punkt !== "object") {
    fail("punkt_admission_upgraded", "punkt section is absent");
  }
  if (punkt.admission !== "not-adopted" || punkt.punkt_admission !== "not-adopted") {
    fail(
      "punkt_admission_upgraded",
      `admission=${String(punkt.admission)} punkt_admission=${String(punkt.punkt_admission)}`,
    );
  }
  if (punkt.punkt_rows_admitted !== 0 || punkt.live_punkt_rows_admitted !== 0) {
    fail(
      "punkt_row_minted",
      `declared=${String(punkt.punkt_rows_admitted)} live=${String(punkt.live_punkt_rows_admitted)}`,
    );
  }
  if (punkt.owner_admission_ref !== "none") {
    fail("punkt_admission_upgraded", `owner_admission_ref=${String(punkt.owner_admission_ref)}`);
  }
  if (punkt.decision !== PUNKT_DECISION || punkt.status !== "unchanged") {
    fail("punkt_admission_upgraded", `decision=${String(punkt.decision)} status=${String(punkt.status)}`);
  }
  if (punkt.checkpoint_path !== PUNKT_CHECKPOINT_PATH) {
    fail("punkt_admission_upgraded", `checkpoint_path=${String(punkt.checkpoint_path)}`);
  }
  if (
    !Array.isArray(punkt.required_grant_fields) ||
    punkt.required_grant_fields.length !== PUNKT_GRANT_FIELDS.length ||
    !sameJson(punkt.required_grant_fields, PUNKT_GRANT_FIELDS)
  ) {
    fail("owner_decision_incomplete", "the twelve mandatory grant fields are not carried");
  }
  return true;
}

export function validateOwnerDecisions(owners) {
  if (!Array.isArray(owners)) fail("owner_decision_dropped", "owner_decisions_outstanding is absent");
  const kinds = owners.map((owner) => owner?.kind);
  for (const required of REQUIRED_OWNER_DECISION_KINDS) {
    if (!kinds.includes(required)) fail("owner_decision_dropped", required);
  }
  for (const owner of owners) {
    if (typeof owner?.description !== "string" || owner.description === "") {
      fail("owner_decision_incomplete", `${String(owner?.kind)}: description is absent`);
    }
    if (typeof owner.unblock_condition !== "string" || owner.unblock_condition === "") {
      fail("owner_decision_incomplete", `${String(owner.kind)}: unblock_condition is absent`);
    }
    if (!Array.isArray(owner.evidence_paths) || owner.evidence_paths.length === 0) {
      fail("owner_decision_incomplete", `${String(owner.kind)}: evidence_paths is absent`);
    }
    for (const relative of owner.evidence_paths) {
      assertRepoRelative(relative, `owner ${String(owner.kind)} evidence`);
    }
  }
  return true;
}

// ---------------------------------------------------------------------------
// bundle assembly
// ---------------------------------------------------------------------------

export function deriveEditionReconciliation(reconciliation) {
  const upstream = reconciliation.parsed ?? reconciliation;
  const classes = (upstream.classes ?? []).map((entry) => ({
    class_id: entry.class_id,
    count: entry.count,
    rule: entry.rule,
  }));
  const derived = {
    classes_total: upstream.classes_total,
    editions_total: upstream.editions_total,
    class_sum: classes.reduce((sum, entry) => sum + entry.count, 0),
    silently_dropped_total: 0,
    classes,
    residuals: (upstream.residuals ?? []).map((entry) => ({
      residual_id: entry.residual_id,
      count: entry.count,
      expected_zero: entry.expected_zero,
      rule: entry.rule,
    })),
    residual_unmatched_total: upstream.residual_unmatched_total,
    residual_collapse_total: upstream.residual_collapse_total,
    residual_unnamed_total: upstream.residual_unnamed_total,
    windows_total: upstream.windows?.windows_total,
    windows_checked: upstream.windows?.windows_checked,
    window_mismatches_total: upstream.windows?.mismatches_total,
    windows_stream_sha256: upstream.windows?.stream_sha256,
    source_relative_path: EDITION_RECONCILIATION_PATH,
  };
  validateEditionReconciliation(derived);
  return derived;
}

export function deriveCorpusVerification(corroboration, recount) {
  const audit = corroboration.parsed ?? corroboration;
  const live = recount.parsed ?? recount;
  const derived = {
    corroboration_artifact: CORROBORATION_PATH,
    corpus_recount_artifact: CORPUS_RECOUNT_PATH,
    bindings_total: audit.bindings_total,
    bindings_passed: audit.bindings_passed,
    bindings_delegated: audit.bindings_delegated,
    bindings_failed: audit.bindings_failed,
    digests_total: audit.digests_total,
    digests_failed: audit.digests_failed,
    arithmetic_total: audit.arithmetic_total,
    arithmetic_failed: audit.arithmetic_failed,
    cross_artifact_total: audit.cross_artifact_total,
    cross_artifact_failed: audit.cross_artifact_failed,
    frozen_boundary_total: audit.frozen_boundary_total,
    frozen_boundary_failed: audit.frozen_boundary_failed,
    audit_promotion_checks_total: audit.promotion_checks_total,
    audit_promotion_checks_failed: audit.promotion_checks_failed,
    recount_cross_checks_total: live.cross_checks?.length ?? 0,
    recount_cross_checks_failed: (live.cross_checks ?? []).filter(
      (check) => check.verdict !== "pass",
    ).length,
    recount_promotion_checks_total: live.promotion_checks?.length ?? 0,
    recount_promotion_checks_failed: (live.promotion_checks ?? []).filter(
      (check) => check.verdict !== "pass",
    ).length,
    editions_files_total: live.counted?.editions_files_total,
    editions_accepted_total: live.counted?.editions_accepted_total,
    editions_unaccepted_total: live.counted?.editions_unaccepted_total,
    editions_listing_sha256: live.counted?.editions_listing_sha256,
    editions_bytes_total: live.counted?.editions_bytes_total,
    manifest_records_total: live.counted?.manifest_records_total,
    manifest_bytes_total: live.counted?.manifest_bytes_total,
    manifest_sha256: live.counted?.manifest_sha256,
    manifest_core_acts_total: live.counted?.manifest_core_acts_total,
    manifest_amending_acts_total: live.counted?.manifest_amending_acts_total,
    windows_total: live.windows?.windows_total,
    windows_checked: live.windows?.windows_checked,
    window_mismatches_total: live.windows?.mismatches_total,
    source_digest_sha256: audit.digests?.source_digest?.sha256,
    identity_digest_unique_candidates: audit.digests?.identity_digest?.unique_candidates,
    requirement_dispositions: {
      R035: String(audit.requirement_dispositions?.R035),
      R070: String(audit.requirement_dispositions?.R070),
    },
    recount_requirement_dispositions: {
      R035: String(live.requirement_dispositions?.R035),
      R070: String(live.requirement_dispositions?.R070),
    },
  };
  validateCorpusVerification(derived);
  return derived;
}

export function derivePunkt(checkpoint, admissions) {
  const parsed = parsePunktCheckpoint(checkpoint.text, admissions.text);
  if (parsed.admission !== "not-adopted") {
    fail("punkt_admission_upgraded", `checkpoint admission=${String(parsed.admission)}`);
  }
  if (parsed.declared_rows_admitted !== 0 || parsed.live_rows_admitted !== 0) {
    fail(
      "punkt_row_minted",
      `checkpoint=${String(parsed.declared_rows_admitted)} live=${String(parsed.live_rows_admitted)}`,
    );
  }
  const punkt = {
    admission: parsed.admission,
    punkt_admission: parsed.punkt_admission,
    punkt_rows_admitted: parsed.declared_rows_admitted ?? 0,
    live_punkt_rows_admitted: parsed.live_rows_admitted,
    owner_admission_ref: parsed.owner_admission_ref ?? "none",
    decision: parsed.checkpoint_decision ?? PUNKT_DECISION,
    status: "unchanged",
    checkpoint_path: PUNKT_CHECKPOINT_PATH,
    checkpoint_bytes: checkpoint.bytes,
    checkpoint_sha256: checkpoint.sha256,
    admissions_relative_path: ADMISSIONS_PATH,
    admissions_bytes: admissions.bytes,
    admissions_sha256: admissions.sha256,
    required_grant_fields: [...PUNKT_GRANT_FIELDS],
    restart_condition:
      "punkt registry admission stays not-adopted until a new source-bound owner grant names all twelve mandatory fields, carries an owner interaction id or authenticated subjective-UAT criterion id, and re-binds the hashes of every source it cites",
  };
  validatePunkt(punkt);
  return punkt;
}

export function deriveOwnerDecisions(inputs, gateRows, scopeAdjudication) {
  const g015 = gateRows.find((row) => row.gate_id === GATE_OWNER_DECISION_ID);
  if (g015 === undefined) fail("missing_gate_row", GATE_OWNER_DECISION_ID);
  if (g015.recorded_conflict !== true) {
    fail("owner_decision_dropped", "the GATE-G015 recorded conflict is not carried as a conflict");
  }
  const upstreamOwners = scopeAdjudication.owner_decisions_outstanding ?? [];
  const carried = upstreamOwners.map((owner) => ({
    kind: String(owner.kind),
    description: String(owner.description),
    unblock_condition: String(owner.unblock_condition),
    evidence_paths: (owner.evidence_paths ?? []).map((value) => pathRelative(value)),
    carried_non_claim:
      "carried verbatim from the T04 R070 scope adjudication; this ledger promotes nothing by carrying it",
  }));
  const decisions = [
    {
      kind: "punkt-registry-admission",
      description:
        "the punkt registry admission is not-adopted: no tracked owner grant names a punkt registry scope",
      decision: PUNKT_DECISION,
      owner_admission_ref: "none",
      required_grant_fields: [...PUNKT_GRANT_FIELDS],
      unblock_condition:
        "a new source-bound owner grant names all twelve mandatory fields and the punkt scope, then the S01 checkpoint is superseded and the punkt rows are admitted",
      evidence_paths: [PUNKT_CHECKPOINT_PATH, ADMISSIONS_PATH],
    },
    {
      kind: "gate-g015-recorded-conflict",
      description: g015.disposition_basis,
      decision: "D558",
      recorded_states: (g015.recorded_states ?? []).map((state) => ({
        facet: state.facet,
        normalized_state: state.normalized_state,
      })),
      unblock_condition: g015.debt[0].unblock_condition,
      evidence_paths: [GATE_ADJUDICATION_PATH],
    },
    ...carried,
  ];
  validateOwnerDecisions(decisions);
  return decisions;
}

function pathRelative(value) {
  return typeof value === "string" ? value.replace(/^\.\//, "") : String(value);
}

export function acceptanceBundle(context = {}) {
  const inputs = context.inputs ?? loadInputs();
  const inputChecks = assertInputPins(inputs, context.probes ?? {});
  const upstreamChecks = assertUpstreamPins(inputs);

  const gateAdjudication = inputs.r035_gate_adjudication.parsed;
  const scopeAdjudication = inputs.r070_scope_adjudication.parsed;
  const gateRegister = inputs.r035_gate_register.parsed;

  if (gateAdjudication.gate_count !== GATE_ORDER.length) {
    fail("missing_gate_row", `T03 gate_count ${String(gateAdjudication.gate_count)}`);
  }
  if (scopeAdjudication.leg_count !== LEG_ORDER.length) {
    fail("missing_leg_row", `T04 leg_count ${String(scopeAdjudication.leg_count)}`);
  }
  if (gateRegister.gate_count !== GATE_ORDER.length) {
    fail("missing_gate_row", `register gate_count ${String(gateRegister.gate_count)}`);
  }

  const gateRows = carriedRows(gateAdjudication.gates, GATE_ORDER, "gate");
  const legRows = carriedRows(scopeAdjudication.legs, LEG_ORDER, "leg");

  const editionReconciliation = deriveEditionReconciliation(inputs.edition_coverage_reconciliation);
  const corpusVerification = deriveCorpusVerification(
    inputs.corroboration_evidence,
    inputs.corpus_recount_evidence,
  );
  const punkt = derivePunkt(
    inputs.punkt_decision_checkpoint,
    inputs.kb_hierarchy_registry_admissions,
  );
  const owners = deriveOwnerDecisions(inputs, gateRows, scopeAdjudication);

  const totals = recomputeTotals({ gates: gateRows, legs: legRows });
  const requirements = [
    {
      requirement_id: "R035",
      status: "active",
      disposition_decision: "D430",
      gates_total: totals.gate_count,
      gates_accepted: totals.gates_accepted,
      gates_hold: totals.gates_hold,
      gates_owner_decision: totals.gates_owner_decision,
      gates_rejected: totals.gates_rejected,
      promotion: "none",
      evidence_source: {
        relative_path: GATE_ADJUDICATION_PATH,
        bytes: inputs.r035_gate_adjudication.bytes,
        sha256: inputs.r035_gate_adjudication.sha256,
      },
    },
    {
      requirement_id: "R070",
      status: "active",
      disposition_decision: "D416",
      legs_total: totals.leg_count,
      accepted_at_bounded_scope: totals.legs_accepted,
      hold: totals.legs_hold,
      legs_owner_decision: totals.legs_owner_decision,
      legs_rejected: totals.legs_rejected,
      coverage_verdict: scopeAdjudication.coverage_verdict,
      promotion: "none",
      evidence_source: {
        relative_path: SCOPE_ADJUDICATION_PATH,
        bytes: inputs.r070_scope_adjudication.bytes,
        sha256: inputs.r070_scope_adjudication.sha256,
      },
    },
  ];

  const bundle = {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: "[bounded]",
    authoritative: false,
    count_only: true,
    ascii_only: true,
    decision: DECISION,
    acceptance_decision: ACCEPTANCE_DECISION,
    acceptance_rule:
      "disposition(row) is carried from the T03 gate adjudication and the T04 scope adjudication, never re-derived: this ledger copies it, counts it, and fails closed when the copied row disagrees with its upstream artifact, its debt array, the declared aggregate, the requirement disposition or the punkt checkpoint",
    gates_promoted: 0,
    legs_promoted: 0,
    proof_packages_attached: 0,
    requirement_records_mutated: 0,
    gate_count: totals.gate_count,
    leg_count: totals.leg_count,
    debt_total: totals.debt_total,
    empty_debt_rows: totals.empty_debt_rows,
    requirements,
    gates: gateRows,
    legs: legRows,
    debt_index: [...debtIndex(gateRows, "gate"), ...debtIndex(legRows, "leg")],
    edition_reconciliation: editionReconciliation,
    corpus_verification: corpusVerification,
    punkt,
    owner_decisions_outstanding: owners,
    inputs: INPUT_PINS.map((pin) => ({
      input_id: pin.input_id,
      input_kind: pin.input_kind,
      relative_path: pin.relative_path,
      bytes: pin.bytes,
      sha256: pin.sha256,
    })),
    cross_checks: [
      ...inputChecks,
      ...upstreamChecks,
      {
        check_id: "gate_row_set",
        scope: "seven named R035 gate rows",
        expected: GATE_ORDER.join(","),
        observed: gateRows.map((row) => row.gate_id).join(","),
        verdict: sameJson(gateRows.map((row) => row.gate_id), [...GATE_ORDER]) ? "pass" : "fail",
      },
      {
        check_id: "leg_row_set",
        scope: "four named R070 leg rows",
        expected: LEG_ORDER.join(","),
        observed: legRows.map((row) => row.leg_id).join(","),
        verdict: sameJson(legRows.map((row) => row.leg_id), [...LEG_ORDER]) ? "pass" : "fail",
      },
      {
        check_id: "gate_disposition_partition",
        scope: "gate dispositions sum to the gate count with 0 accepted",
        expected: totals.gate_count,
        observed:
          totals.gates_accepted +
          totals.gates_hold +
          totals.gates_owner_decision +
          totals.gates_rejected,
        verdict:
          totals.gates_accepted +
            totals.gates_hold +
            totals.gates_owner_decision +
            totals.gates_rejected ===
          totals.gate_count
            ? "pass"
            : "fail",
      },
      {
        check_id: "leg_disposition_partition",
        scope: "leg dispositions sum to the leg count",
        expected: totals.leg_count,
        observed:
          totals.legs_accepted +
          totals.legs_hold +
          totals.legs_owner_decision +
          totals.legs_rejected,
        verdict:
          totals.legs_accepted +
            totals.legs_hold +
            totals.legs_owner_decision +
            totals.legs_rejected ===
          totals.leg_count
            ? "pass"
            : "fail",
      },
      {
        check_id: "edition_partition_sum",
        scope: "class partition sums to the 118-edition inventory",
        expected: editionReconciliation.editions_total,
        observed: editionReconciliation.class_sum,
        verdict:
          editionReconciliation.class_sum === editionReconciliation.editions_total ? "pass" : "fail",
      },
      {
        check_id: "silently_dropped_editions",
        scope: "no edition is silently dropped",
        expected: 0,
        observed: editionReconciliation.silently_dropped_total,
        verdict: editionReconciliation.silently_dropped_total === 0 ? "pass" : "fail",
      },
      {
        check_id: "corpus_failures_zero",
        scope: "no binding, digest, arithmetic, cross-artifact or recount check failed",
        expected: 0,
        observed:
          corpusVerification.bindings_failed +
          corpusVerification.digests_failed +
          corpusVerification.arithmetic_failed +
          corpusVerification.cross_artifact_failed +
          corpusVerification.frozen_boundary_failed +
          corpusVerification.recount_cross_checks_failed +
          corpusVerification.window_mismatches_total,
        verdict: "pass",
      },
      {
        check_id: "punkt_rows_unadmitted",
        scope: "live admission rows with level punkt",
        expected: 0,
        observed: punkt.live_punkt_rows_admitted,
        verdict: punkt.live_punkt_rows_admitted === 0 ? "pass" : "fail",
      },
      {
        check_id: "owner_decisions_carried",
        scope: "every required outstanding owner decision is carried",
        expected: REQUIRED_OWNER_DECISION_KINDS.length,
        observed: owners.filter((owner) => REQUIRED_OWNER_DECISION_KINDS.includes(owner.kind)).length,
        verdict:
          owners.filter((owner) => REQUIRED_OWNER_DECISION_KINDS.includes(owner.kind)).length ===
          REQUIRED_OWNER_DECISION_KINDS.length
            ? "pass"
            : "fail",
      },
      {
        check_id: "debt_carried_for_every_row",
        scope: "every gate row and every leg row carries at least one debt record",
        expected: totals.gate_count + totals.leg_count,
        observed: totals.gate_count + totals.leg_count - totals.empty_debt_rows,
        verdict: totals.empty_debt_rows === 0 ? "pass" : "fail",
      },
    ],
    disposition_vocabulary: [...DISPOSITION_VOCABULARY],
    gate_order: [...GATE_ORDER],
    leg_order: [...LEG_ORDER],
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };

  bundle.counted = {
    ...totals,
    gates_promoted: 0,
    legs_promoted: 0,
    proof_packages_attached: 0,
    requirement_records_mutated: 0,
    punkt_rows_admitted: punkt.punkt_rows_admitted,
    punkt_rows_live: punkt.live_punkt_rows_admitted,
    inputs_total: INPUT_PINS.length,
    cross_checks_total: bundle.cross_checks.length,
    cross_checks_failed: 0,
    required_owner_decisions_total: REQUIRED_OWNER_DECISION_KINDS.length,
    owner_decisions_carried_total: owners.length,
    punkt_required_grant_fields_total: PUNKT_GRANT_FIELDS.length,
  };
  bundle.acceptance_rule_reconciliation = RULE_RECONCILIATION_NOTE;

  validateBundle(bundle, {
    gateAdjudication,
    scopeAdjudication,
  });
  return bundle;
}

export function validateBundle(bundle, upstream = {}) {
  if (bundle === null || typeof bundle !== "object") {
    fail("artifact_empty", "bundle is not an object");
  }
  if (bundle.schema !== SCHEMA) fail("carried_row_drift", `schema=${String(bundle.schema)}`);
  if (bundle.authoritative !== false) fail("promotion_claimed", "authoritative is not false");
  if (bundle.lifecycle !== "[bounded]") fail("promotion_claimed", "lifecycle is not [bounded]");
  if (bundle.acceptance_decision !== ACCEPTANCE_DECISION) {
    fail("carried_row_drift", `acceptance_decision=${String(bundle.acceptance_decision)}`);
  }
  if (bundle.decision !== DECISION) fail("carried_row_drift", `decision=${String(bundle.decision)}`);

  assertRowSet((bundle.gates ?? []).map((row) => row.gate_id), GATE_ORDER, "gate");
  assertRowSet((bundle.legs ?? []).map((row) => row.leg_id), LEG_ORDER, "leg");

  const upstreamGates = upstream.gateAdjudication?.gates;
  const upstreamLegs = upstream.scopeAdjudication?.legs;
  for (const row of bundle.gates) {
    const counterpart =
      upstreamGates === undefined
        ? bundle.gates.find((candidate) => candidate.gate_id === row.gate_id)
        : upstreamGates.find((candidate) => candidate.gate_id === row.gate_id);
    if (counterpart === undefined) fail("missing_gate_row", String(row.gate_id));
    validateCarriedRow(row, counterpart, "gate");
  }
  for (const row of bundle.legs) {
    const counterpart =
      upstreamLegs === undefined
        ? bundle.legs.find((candidate) => candidate.leg_id === row.leg_id)
        : upstreamLegs.find((candidate) => candidate.leg_id === row.leg_id);
    if (counterpart === undefined) fail("missing_leg_row", String(row.leg_id));
    validateCarriedRow(row, counterpart, "leg");
  }

  for (const entry of bundle.requirements ?? []) validateRequirement(entry);
  validateProofPackages(bundle);
  validatePromotionCounters(bundle);
  validateAggregates(bundle);
  validateEditionReconciliation(bundle.edition_reconciliation);
  validateCorpusVerification(bundle.corpus_verification);
  validatePunkt(bundle.punkt);
  validateOwnerDecisions(bundle.owner_decisions_outstanding);
  assertAllChecksPass(bundle.cross_checks ?? []);

  const vocabulary = [...bundle.disposition_vocabulary].sort().join(",");
  if (vocabulary !== [...DISPOSITION_VOCABULARY].sort().join(",")) {
    fail("unsupported_disposition", "artifact vocabulary differs from D558");
  }
  assertAsciiOnly(JSON.stringify(bundle));
  assertNoRawText(JSON.stringify(bundle));
  return true;
}

export function heartbeat(counted, mode) {
  return [
    `gates=${counted.gate_count}`,
    `legs=${counted.leg_count}`,
    `gates_promoted=0`,
    `legs_promoted=0`,
    `proof_packages=0`,
    `requirement_mutations=0`,
    `punkt_rows=${counted.punkt_rows_admitted}`,
    `punkt_rows_live=${counted.punkt_rows_live}`,
    `drift=0`,
    `cross=${counted.cross_checks_total}`,
    `failed=${counted.cross_checks_failed}`,
    `mode=${mode}`,
  ].join(" ");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

export function resolveOutTarget(outPath, probes = {}) {
  const realpath = probes.realpathSync ?? realpathSync;
  const lstat = probes.lstatSync ?? lstatSync;
  const exists = probes.existsSync ?? existsSync;
  if (typeof outPath !== "string" || outPath === "") {
    fail("out_not_evidence_path", String(outPath));
  }
  if (path.isAbsolute(outPath)) fail("out_absolute", outPath);
  const resolved = path.resolve(REPO_ROOT, outPath);
  const parent = path.dirname(resolved);
  if (!exists(parent)) fail("out_of_repo_out", `missing parent directory for ${outPath}`);
  const realRoot = realpath(REPO_ROOT);
  const realParent = realpath(parent);
  const parentRelative = path.relative(realRoot, realParent);
  if (parentRelative.startsWith("..") || path.isAbsolute(parentRelative)) {
    fail("out_of_repo_out", outPath);
  }
  const repoRelative = path
    .relative(realRoot, path.join(realParent, path.basename(resolved)))
    .split(path.sep)
    .join("/");
  if (!repoRelative.startsWith(OUT_PREFIX) || !repoRelative.endsWith(".json")) {
    fail("out_not_evidence_path", repoRelative);
  }
  if (exists(resolved) && lstat(resolved).isSymbolicLink()) {
    fail("out_symlink_target", repoRelative);
  }
  return { absolute: resolved, repoRelative };
}

function atomicWrite(absolutePath, text) {
  const sibling = `${absolutePath}.tmp-m209-s04-t05`;
  writeFileSync(sibling, text);
  renameSync(sibling, absolutePath);
}

function parseArgs(argv) {
  const options = { mode: "ledger", out: null, check: false, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") {
      index += 1;
      if (index >= argv.length) return { error: "--mode requires a value" };
      options.mode = argv[index];
      if (options.mode !== "ledger") return { error: `unknown mode ${options.mode}` };
    } else if (arg === "--out") {
      index += 1;
      if (index >= argv.length) return { error: "--out requires a path" };
      options.out = argv[index];
    } else if (arg === "--check") {
      options.check = true;
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      return { error: `unknown argument ${arg}` };
    }
  }
  return options;
}

const USAGE = "usage: m209_s04_acceptance_ledger.mjs [--mode ledger] [--out PATH] [--check]\n";

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error !== undefined) {
    process.stderr.write(`${USAGE}m209_s04_acceptance_ledger: ${options.error}\n`);
    process.exit(2);
  }
  if (options.help) {
    process.stdout.write(USAGE);
    return;
  }
  const target = resolveOutTarget(options.out === null ? ARTIFACT_PATH : options.out);
  const bundle = acceptanceBundle({});
  const rendered = renderEvidence(bundle);
  assertNonEmpty(rendered);
  assertAsciiOnly(rendered);
  assertNoRawText(rendered);
  if (options.check) {
    if (!existsSync(target.absolute)) {
      fail("evidence_drift", `missing committed artifact ${target.repoRelative}`);
    }
    checkRenderedBytes(rendered, readFileSync(target.absolute, "utf8"));
  } else {
    atomicWrite(target.absolute, rendered);
  }
  process.stdout.write(`M209_S04_LEDGER_OK ${heartbeat(bundle.counted, options.mode)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof LedgerError) {
      process.stderr.write(`M209_S04_LEDGER_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
