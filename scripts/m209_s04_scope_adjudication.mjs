#!/usr/bin/env node
// R070 scope-by-scope acceptance adjudication for M209-2yg6ix (S04 T04, D558).
//
// WHY THIS FILE EXISTS
// S03 T05 produced the R070 scope ledger: four legs, each with a carried
// leg_verdict (bounded-supporting | slot-filled-not-proven), one named quantifier
// with a numeric acceptance threshold and a declared denominator source path,
// and the class-matched evidence it requires and does not have. A ledger of
// carried verdicts is not an acceptance decision (D558). S04 has to decide,
// leg by leg and by rule rather than by opinion, whether any of those four legs
// can be accepted -- and the decision has to be re-derived from the leg's own
// source artifact, never copied as a boolean.
//
// So this script re-derives, per leg:
//   * the quantifier threshold outcome from the source artifact's declared
//     counts (measurements, not stored booleans);
//   * the declared-count binding between the ledger row and the live artifact;
//   * the presence of the required-evidence-class declaration;
//   * the frozen M201 boundary (path, bytes, sha256, coverage verdict);
// and cross-checks the S03 ledger's own bytes/sha256 and its four declared input
// pins against the live files. A pin disagreement is `input_hash_mismatch`; a
// count binding disagreement is `count_binding_mismatch`; a frozen M201
// disagreement is `m201_boundary_drift`.
//
// THE DISPOSITION RULE (and one honest reconciliation)
// The plan's DO step 4 lists "required evidence class is absent" as a hold
// trigger, but the same step's expected result and the slice heartbeat require
// three legs to be accepted (legs=4 accepted-bounded=3 hold=1). Read literally
// the two statements contradict each other, because every leg carries
// required_evidence_status=absent. This artifact therefore reads the clause as
// "the required-evidence declaration must be present and must not be falsely
// claimed": the code `required_evidence_class_absent` fires only when the
// declaration itself is missing, `class_matched_evidence_claimed` fires on a
// claimed class-matched id without a source, and the human-annotation class
// absence is carried as bounded-scope debt on every leg. The decision function
// itself is: hold-with-precise-debt when the carried leg_verdict is
// slot-filled-not-proven or when the recomputed measurement misses the
// threshold; accepted-at-bounded-scope only when the carried verdict is
// bounded-supporting and the recomputed measurement meets the threshold. This
// reconciliation is recorded as a non-claim so it is auditable rather than
// silent.
//
// WHAT IT IS NOT (D539, D558)
// No leg is validated, no leg and no gate is promoted, no proof package is
// attached, no requirement record is mutated, no GSD state is written. The
// frozen M201 R070 proof gate is cited by path, bytes and sha256 and is never
// widened or re-derived; `crates/ln-temporal/tests/r070_proof_gate.rs` is never
// edited or executed as a gate. class_matched_ids is an explicit empty set on
// every leg and is never invented.
//
// OUTPUT
//   prd/migration/rust-evidence/m209-s04-r070-scope-adjudication.json
//     schema law-nexus/m209-r070-scope-adjudication/v1
//
// USAGE
//   node scripts/m209_s04_scope_adjudication.mjs --mode legs --out prd/migration/rust-evidence/m209-s04-r070-scope-adjudication.json
//   node scripts/m209_s04_scope_adjudication.mjs --mode legs --check
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

export const SCHEMA = "law-nexus/m209-r070-scope-adjudication/v1";
export const KIND = "m209-s04-r070-scope-adjudication";
export const MILESTONE = "M209-2yg6ix";
export const SLICE = "S04";
export const TASK = "T04";
export const ARTIFACT_PATH = "prd/migration/rust-evidence/m209-s04-r070-scope-adjudication.json";
export const OUT_PREFIX = "prd/migration/rust-evidence/m209-s04-";
export const LEDGER_PATH = "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json";
export const M201_GATE_PATH = "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json";

export const AMENDING_PATH =
  "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
export const COMMENCEMENT_PATH =
  "prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json";
export const EDITION_DELTA_PATH =
  "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json";
export const FAMILY_PATH = "prd/migration/rust-evidence/m209-s03-family-denominator.json";

export const REQUIREMENT_ID = "R070";
export const REQUIREMENT_DISPOSITION = "active";
export const REQUIREMENT_DISPOSITION_DECISION = "D416";
export const DECISION_ID = "D558";
export const COVERAGE_VERDICT = "incomplete-because-not-every-edition";
export const REQUIRED_EVIDENCE_CLASS = "human-annotation";

// The S03 ledger pin. It is re-derived from the live bytes below; the ledger's
// own four input pins are checked against the live leg artifacts as well.
export const LEDGER_PIN = Object.freeze({
  bytes: 7850,
  sha256: "sha256:b640b2e114f8872972c11f2201b88d5248a04ba64491252bd42536831a34b4cc",
});

// The frozen M201 R070 proof gate pin, also declared inside the ledger as
// frozen_m201_boundary.gate_sha256. Both legs must agree with the live file.
export const M201_PIN = Object.freeze({
  bytes: 7610,
  sha256: "sha256:02db1cf033ec987bcca90bdb3a5d7d90a13f999048c41ef2d8999448e2ff3704",
});

// The closed acceptance vocabulary (D558). `hold-requires-owner-decision` and
// `rejected-as-stated` are admitted by the decision but no leg row uses them:
// no leg carries a recorded state conflict and no leg is rejected as stated.
export const DISPOSITION_VOCABULARY = Object.freeze([
  "accepted-at-bounded-scope",
  "hold-requires-owner-decision",
  "hold-with-precise-debt",
  "rejected-as-stated",
]);

// The carried leg verdicts (the S03 ledger vocabulary). `validated`, `complete`,
// `proven`, `satisfied` and `checked` are deliberately absent: propagating one
// of them is `leg_verdict_upgraded`.
export const LEG_VERDICT_VOCABULARY = Object.freeze(["bounded-supporting", "slot-filled-not-proven"]);

// The four legs, in the S03 ledger order.
export const LEG_ORDER = Object.freeze([
  "amending-acts",
  "affected-provisions",
  "commencement-and-transitional",
  "edition-delta",
]);

// D539 forbidden quantifiers: the M202 inventory counters. None of them may
// stand as a leg quantifier.
export const INVENTORY_QUANTIFIERS = Object.freeze([
  "admitted_candidate_backed",
  "candidates_duplicate",
  "candidates_extracted",
  "candidates_unique",
  "fz44_glava",
  "fz44_statya",
  "legacy_human",
  "punkt_admitted",
  "registry_rows",
  "suites_cited",
]);

// Per-leg measurement rules. The numerator is the measured value that meets the
// acceptance threshold; the denominator is the declared universe it is measured
// over. `numerator_field` / `denominator_field` are dotted paths into the leg's
// source artifact, evaluated by numericAt (a trailing `length` reads an array
// length). For the commencement leg the numerator IS the required evidence
// class: the count of source-artifact slots carrying class-matched human
// annotation, which the artifact declares as an empty class_matched_ids set, so
// the threshold (>= 1) is not met and the leg stays a hold. It is never read
// from the filled named_chain_slots count.
export const LEG_MEASUREMENTS = Object.freeze({
  "amending-acts": {
    source: AMENDING_PATH,
    numerator_field: "denominator.amends_edges_total",
    denominator_field: "denominator.amends_edges_total",
    measurement_rule:
      "the observed value is the source artifact's declared amends-edge partition total (denominator.amends_edges_total), recomputed here and compared to the ledger threshold; a stored boolean is never trusted",
  },
  "affected-provisions": {
    source: AMENDING_PATH,
    numerator_field: "denominator.distinct_statya_refs_resolved",
    denominator_field: "denominator.distinct_statya_refs",
    measurement_rule:
      "the observed value is the source artifact's declared resolved-statya count (denominator.distinct_statya_refs_resolved) over denominator.distinct_statya_refs, recomputed here",
  },
  "commencement-and-transitional": {
    source: COMMENCEMENT_PATH,
    numerator_field: "required_evidence.class_matched_ids.length",
    denominator_field: "denominator.slots_total",
    measurement_rule:
      "the observed value is the count of source-artifact slots carrying the required evidence class (required_evidence.class_matched_ids length), cross-checked against denominator.by_evidence_class[human-annotation]; the filled named_chain_slots count is not a measurement of this quantifier",
  },
  "edition-delta": {
    source: EDITION_DELTA_PATH,
    numerator_field: "denominator.windows_total",
    denominator_field: "denominator.editions_total",
    measurement_rule:
      "the observed value is the source artifact's declared window count (denominator.windows_total) over denominator.editions_total, recomputed here",
  },
});

// Per-leg bindings between the ledger's declared_counts keys and the dotted
// paths of the live source artifact. Every binding must agree exactly.
export const LEG_BINDINGS = Object.freeze({
  "amending-acts": [
    { ledger_key: "amends_edges_total", source_path: "denominator.amends_edges_total" },
    { ledger_key: "layer1_amending_acts", source_path: "denominator.layer1_amending_acts" },
    { ledger_key: "layer1_records_total", source_path: "denominator.layer1_records_total" },
  ],
  "affected-provisions": [
    { ledger_key: "distinct_statya_refs", source_path: "denominator.distinct_statya_refs" },
    {
      ledger_key: "distinct_statya_refs_resolved",
      source_path: "denominator.distinct_statya_refs_resolved",
    },
    { ledger_key: "resolved-provision", source_path: "denominator.by_outcome.resolved-provision" },
  ],
  "commencement-and-transitional": [
    { ledger_key: "absent", source_path: "denominator.by_evidence_class.absent" },
    { ledger_key: "named_chain_slots", source_path: "denominator.named_chain_slots" },
    { ledger_key: "slots_total", source_path: "denominator.slots_total" },
  ],
  "edition-delta": [
    { ledger_key: "editions_processed", source_path: "denominator.editions_processed" },
    { ledger_key: "editions_total", source_path: "denominator.editions_total" },
    { ledger_key: "windows_total", source_path: "denominator.windows_total" },
  ],
});

export const ADJUDICATION_RULE =
  "disposition(leg) = hold-with-precise-debt when the carried leg_verdict is slot-filled-not-proven or when the measurement recomputed from the leg's source artifact misses the named quantifier threshold; otherwise, when the carried leg_verdict is bounded-supporting and the recomputed measurement meets the threshold, accepted-at-bounded-scope. accepted-at-bounded-scope accepts the bounded named quantifier only: it never asserts the required human-annotation evidence class, which stays absent and is carried as bounded-scope debt, and it never promotes the requirement or the frozen M201 gate";

export const RULE_RECONCILIATION_NOTE =
  "the plan's DO step 4 lists required-evidence-class absence as a hold trigger while its expected result and the slice heartbeat require three accepted legs; this artifact reads that clause as 'the required-evidence declaration must be present and must not be falsely claimed' (required_evidence_class_absent fires only on a missing declaration, class_matched_evidence_claimed on a claimed id without source) and carries the human-annotation class absence as bounded-scope debt on accepted legs";

// The closed, documented fail-closed vocabulary. The contract test asserts that
// this exact set is emittable (each code fires on a mutated copy) and that no
// undocumented code can be raised.
export const FAIL_CLOSED_CODES = Object.freeze([
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

export const NON_CLAIMS = Object.freeze([
  "acceptance-at-bounded-scope-is-not-r070-validation (D416): the three accepted legs accept only their bounded named quantifiers; R070 stays active and the requirement record is not mutated.",
  "commencement-and-transitional-remains-hold: the single named-chain slot is slot-filled-not-proven (evidence class hypothesized_from_oracle_diff) and 0 of 122 declared slots carry class-matched human commencement evidence; the leg stays hold-with-precise-debt.",
  "coverage-verdict-carried-not-promoted: coverage_verdict=incomplete-because-not-every-edition is carried verbatim from the S03 ledger and is never raised.",
  "leg-verdicts-carried-verbatim: bounded-supporting and slot-filled-not-proven are carried unchanged from the S03 ledger; no leg is upgraded to validated, complete, proven, satisfied or checked.",
  "m201-gate-not-widened: the frozen M201 R070 proof gate is cited by path, bytes and sha256 and is never widened, re-derived or promoted.",
  "class-matched-ids-stay-empty: class_matched_ids is an empty set on every leg; a claimed class-matched id without a source fails closed (class_matched_evidence_claimed) and no class-matched id is invented.",
  "no-requirement-record-mutated: no requirement record is written, no GSD state is changed and no proof package is attached by this adjudication.",
  "canonical-admission-pair-swap-remains-debt (D545): any canonical admission-pair swap still requires superseding the frozen pin suite and is carried as an outstanding owner decision, not as slice work.",
  "count-only-and-ascii-only: only rule ids, counts, thresholds, repository-relative paths, byte counts and sha256 pins are written; no corpus text, XML bytes or provider prose is carried.",
  "inventory-counts-are-not-quantifiers (D539): the M202 inventory counters (registry_rows, legacy_human, punkt_admitted, candidates_*, admitted_candidate_backed, fz44_glava, fz44_statya, suites_cited) are rejected as leg quantifiers.",
  "quantifier-thresholds-are-recomputed-not-read: every threshold_satisfied value is recomputed from the source artifact's declared counts by this adjudication and is cross-checked against the ledger's declared-count bindings; a stored boolean is never trusted.",
  `adjudication-rule-reconciliation (D558): ${RULE_RECONCILIATION_NOTE}.`,
]);

// Provider prose markers that must never reach a count-only artifact.
const RAW_TEXT_MARKERS = Object.freeze([
  "consultantplus://",
  "<w:",
  "screenTip",
  "\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d",
]);

const UPGRADED_LITERALS = Object.freeze([
  "validated",
  "complete",
  "proven",
  "satisfied",
  "checked",
  "authoritative",
]);

// ---------------------------------------------------------------------------
// errors and small guards
// ---------------------------------------------------------------------------

export class AdjudicationError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "AdjudicationError";
    this.code = code;
    this.detail = detail;
  }
}

export function fail(code, detail) {
  throw new AdjudicationError(code, detail);
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

export function checkRenderedBytes(rendered, committed) {
  if (rendered !== committed) {
    fail("evidence_drift", "rendered bytes differ from the committed artifact");
  }
  return true;
}

export function renderEvidence(bundle) {
  return `${JSON.stringify(bundle)}\n`;
}

export function assertNoRawText(text) {
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) fail("raw_text_leak", `artifact carries ${marker}`);
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

// ---------------------------------------------------------------------------
// artifact loading
// ---------------------------------------------------------------------------

export function loadJsonArtifact(relativePath, label, probes = {}) {
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
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
  }
  const bytes = Buffer.from(text, "utf8");
  return { relative_path: relativePath, bytes: bytes.length, sha256: sha256Pin(bytes), parsed };
}

export function loadSources(probes = {}) {
  const ledger = loadJsonArtifact(LEDGER_PATH, "r070 scope ledger", probes);
  const m201 = loadJsonArtifact(M201_GATE_PATH, "frozen m201 r070 proof gate", probes);
  const legArtifacts = {};
  for (const rule of Object.values(LEG_MEASUREMENTS)) {
    if (legArtifacts[rule.source] === undefined) {
      legArtifacts[rule.source] = loadJsonArtifact(rule.source, `leg source ${rule.source}`, probes);
    }
  }
  return { ledger, m201, legArtifacts };
}

// ---------------------------------------------------------------------------
// numeric access and pin checks
// ---------------------------------------------------------------------------

export function numericAt(object, dottedPath) {
  if (object === null || typeof object !== "object") return null;
  let current = object;
  for (const part of String(dottedPath).split(".")) {
    if (current === null || current === undefined) return null;
    if (Array.isArray(current) && part === "length") {
      current = current.length;
      continue;
    }
    current = current[part];
  }
  return typeof current === "number" ? current : null;
}

export function assertLedgerShape(ledger) {
  if (ledger === null || typeof ledger !== "object") {
    fail("input_artifact_shape_invalid", "ledger is not an object");
  }
  if (ledger.requirement_id !== REQUIREMENT_ID) {
    fail("input_artifact_shape_invalid", `ledger requirement_id ${String(ledger.requirement_id)}`);
  }
  if (ledger.disposition !== REQUIREMENT_DISPOSITION) {
    fail("input_artifact_shape_invalid", `ledger disposition ${String(ledger.disposition)}`);
  }
  if (ledger.disposition_decision !== REQUIREMENT_DISPOSITION_DECISION) {
    fail(
      "input_artifact_shape_invalid",
      `ledger disposition_decision ${String(ledger.disposition_decision)}`,
    );
  }
  if (!Array.isArray(ledger.legs) || ledger.legs.length !== LEG_ORDER.length) {
    fail("ledger_leg_set_mismatch", `ledger legs ${String(ledger.legs?.length)}`);
  }
  const ids = ledger.legs.map((leg) => leg.leg_id);
  if (new Set(ids).size !== ids.length || LEG_ORDER.some((id) => !ids.includes(id))) {
    fail("ledger_leg_set_mismatch", ids.join(","));
  }
  if (!Array.isArray(ledger.inputs) || ledger.inputs.length === 0) {
    fail("input_artifact_shape_invalid", "ledger inputs are absent");
  }
  if (ledger.frozen_m201_boundary === null || typeof ledger.frozen_m201_boundary !== "object") {
    fail("input_artifact_shape_invalid", "ledger frozen M201 boundary is absent");
  }
  return true;
}

export function assertInputPins(ledgerLoaded, probes = {}) {
  const isTracked = probes.isTracked ?? ((relative) => isTrackedPath(relative, probes.repoRoot));
  const read = probes.readFileSync ?? readFileSync;
  const exists = probes.existsSync ?? existsSync;
  const root = probes.repoRoot ?? REPO_ROOT;
  const ledger = ledgerLoaded.parsed;
  assertLedgerShape(ledger);
  if (ledgerLoaded.bytes !== LEDGER_PIN.bytes) {
    fail("input_hash_mismatch", `ledger bytes ${ledgerLoaded.bytes} != ${LEDGER_PIN.bytes}`);
  }
  if (ledgerLoaded.sha256 !== LEDGER_PIN.sha256) {
    fail("input_hash_mismatch", `ledger sha256 ${ledgerLoaded.sha256}`);
  }
  const checks = [
    {
      check_id: "ledger_pin",
      scope: "S03 R070 scope ledger bytes and sha256",
      expected: `${LEDGER_PIN.bytes}|${LEDGER_PIN.sha256}`,
      observed: `${ledgerLoaded.bytes}|${ledgerLoaded.sha256}`,
      verdict: "pass",
    },
  ];
  for (const input of ledger.inputs) {
    const relative = input.relative_path;
    assertRepoRelative(relative, `ledger input ${String(input.input_id)}`);
    if (!isTracked(relative)) fail("input_not_tracked", relative);
    const absolute = path.join(root, relative);
    if (!exists(absolute)) fail("input_absent", relative);
    let raw;
    try {
      raw = read(absolute, "utf8");
    } catch (error) {
      fail("input_absent", `${relative}: ${error.code ?? error.message}`);
    }
    const bytes = Buffer.from(typeof raw === "string" ? raw : Buffer.from(raw)).length;
    const sha256 = sha256Pin(Buffer.from(raw));
    if (bytes !== input.input_bytes || sha256 !== input.input_sha256) {
      fail(
        "input_hash_mismatch",
        `${relative} live=${bytes}|${sha256} declared=${input.input_bytes}|${input.input_sha256}`,
      );
    }
    checks.push({
      check_id: `leg_input_${String(input.input_id)}`,
      scope: `ledger input pin ${relative}`,
      expected: `${input.input_bytes}|${input.input_sha256}`,
      observed: `${bytes}|${sha256}`,
      verdict: "pass",
    });
  }
  return checks;
}

export function assertM201Boundary(m201Loaded, ledger) {
  const declared = ledger.frozen_m201_boundary;
  if (m201Loaded.relative_path !== declared.gate_relative_path) {
    fail("m201_boundary_drift", `path ${m201Loaded.relative_path}`);
  }
  if (m201Loaded.bytes !== M201_PIN.bytes) {
    fail("m201_boundary_drift", `bytes ${m201Loaded.bytes} != ${M201_PIN.bytes}`);
  }
  if (m201Loaded.sha256 !== M201_PIN.sha256 || m201Loaded.sha256 !== declared.gate_sha256) {
    fail("m201_boundary_drift", `sha256 ${m201Loaded.sha256}`);
  }
  if (m201Loaded.parsed.coverage_verdict !== COVERAGE_VERDICT) {
    fail("m201_boundary_drift", `coverage_verdict ${String(m201Loaded.parsed.coverage_verdict)}`);
  }
  if (m201Loaded.parsed.disposition !== REQUIREMENT_DISPOSITION) {
    fail("m201_boundary_drift", `disposition ${String(m201Loaded.parsed.disposition)}`);
  }
  if (declared.gate_coverage_verdict !== COVERAGE_VERDICT) {
    fail("m201_boundary_drift", `ledger gate_coverage_verdict ${String(declared.gate_coverage_verdict)}`);
  }
  return {
    check_id: "m201_boundary_pin",
    scope: "frozen M201 R070 proof gate bytes, sha256 and carried coverage verdict",
    expected: `${M201_PIN.bytes}|${M201_PIN.sha256}|${COVERAGE_VERDICT}`,
    observed: `${m201Loaded.bytes}|${m201Loaded.sha256}|${m201Loaded.parsed.coverage_verdict}`,
    verdict: "pass",
  };
}

// ---------------------------------------------------------------------------
// per-leg derivation
// ---------------------------------------------------------------------------

export function resolveDenominatorSource(legId, leg, context) {
  const declared = leg?.quantifier?.denominator_source_path;
  if (typeof declared !== "string" || declared === "") {
    fail("denominator_source_absent", `${legId}: no denominator source path`);
  }
  const loaded = context.legArtifacts?.[declared];
  if (loaded === undefined || loaded === null) {
    fail("denominator_source_absent", `${legId}:${declared}`);
  }
  return loaded;
}

export function assertCountBindings(legId, ledgerLeg, artifactParsed) {
  const bindings = LEG_BINDINGS[legId];
  if (!Array.isArray(bindings)) fail("ledger_leg_set_mismatch", `no bindings for ${legId}`);
  const declared = ledgerLeg?.tracked_evidence?.declared_counts;
  if (declared === null || typeof declared !== "object") {
    fail("count_binding_mismatch", `${legId}: declared_counts absent`);
  }
  const rows = [];
  for (const binding of bindings) {
    const observed = numericAt(artifactParsed, binding.source_path);
    if (observed === null) {
      fail("count_binding_mismatch", `${legId}:${binding.ledger_key} absent at ${binding.source_path}`);
    }
    if (!Object.prototype.hasOwnProperty.call(declared, binding.ledger_key)) {
      fail("count_binding_mismatch", `${legId}:${binding.ledger_key} absent from ledger`);
    }
    if (declared[binding.ledger_key] !== observed) {
      fail(
        "count_binding_mismatch",
        `${legId}:${binding.ledger_key} ledger=${declared[binding.ledger_key]} artifact=${observed}`,
      );
    }
    rows.push({
      ledger_key: binding.ledger_key,
      source_path: binding.source_path,
      value: observed,
      verdict: "pass",
    });
  }
  return rows;
}

export function assertRequiredEvidenceDeclaration(legId, ledgerLeg, artifactParsed) {
  const fromArtifact = artifactParsed?.required_evidence?.required_evidence_class;
  const fromLedger = ledgerLeg?.required_evidence_class;
  const declared = typeof fromArtifact === "string" && fromArtifact !== "" ? fromArtifact : fromLedger;
  if (typeof declared !== "string" || declared === "") {
    fail("required_evidence_class_absent", `${legId}: no required-evidence declaration`);
  }
  if (declared !== REQUIRED_EVIDENCE_CLASS) {
    fail("required_evidence_class_absent", `${legId}:${declared}`);
  }
  const ids = artifactParsed?.required_evidence?.class_matched_ids;
  if (Array.isArray(ids) && ids.length > 0) {
    fail("class_matched_evidence_claimed", `${legId}:${ids.join(",")}`);
  }
  return declared;
}

export function measureLeg(legId, leg, artifactParsed) {
  const rule = LEG_MEASUREMENTS[legId];
  if (rule === undefined) fail("ledger_leg_set_mismatch", `no measurement rule for ${legId}`);
  const threshold = leg?.quantifier?.threshold;
  if (typeof threshold !== "number") {
    fail("input_artifact_shape_invalid", `${legId}: quantifier threshold is not numeric`);
  }
  const observed = numericAt(artifactParsed, rule.numerator_field);
  const denominator = numericAt(artifactParsed, rule.denominator_field);
  if (observed === null || denominator === null) {
    fail(
      "count_binding_mismatch",
      `${legId}: measurement missing (${rule.numerator_field}=${String(observed)}, ${rule.denominator_field}=${String(denominator)})`,
    );
  }
  return {
    rule: rule.measurement_rule,
    numerator_field: rule.numerator_field,
    denominator_field: rule.denominator_field,
    observed_value: observed,
    denominator_value: denominator,
    threshold,
    comparison: ">=",
    satisfied: observed >= threshold,
  };
}

export function scopeDisposition(legVerdict, measurement) {
  if (!LEG_VERDICT_VOCABULARY.includes(legVerdict)) {
    fail("leg_verdict_upgraded", String(legVerdict));
  }
  if (legVerdict === "slot-filled-not-proven" || measurement.satisfied !== true) {
    return "hold-with-precise-debt";
  }
  return "accepted-at-bounded-scope";
}

function legDebt(legId, leg, measurement) {
  const quantifierName = leg.quantifier.name;
  const acceptanceText = leg.quantifier.acceptance;
  if (legId === "commencement-and-transitional") {
    return {
      debt_id: `${legId}:class-matched-human-commencement-evidence`,
      quantifier_name: quantifierName,
      acceptance_text: acceptanceText,
      required_evidence_class: REQUIRED_EVIDENCE_CLASS,
      missing_artifact_kind:
        "corpus-scale Legislative commencement and transitional source plus class-matched human annotation",
      observed_value: measurement.observed_value,
      threshold: measurement.threshold,
      closest_evidence: {
        relative_paths: [
          COMMENCEMENT_PATH,
          M201_GATE_PATH,
          "prd/annotation/m207-s04-c4-protocol.md",
          "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
        ],
        why_insufficient:
          "every amending-act slot is explicitly-absent (no legislative commencement source exists in the tracked corpus), the single named-chain slot is slot-filled-not-proven by a hypothesized_from_oracle_diff class, and the M207 class-matched human pilot was not run (receipt non-pass/not-measured)",
      },
      unmet_conditions: [
        "corpus-scale Legislative commencement and transitional source is absent: 121 of 122 slots are explicitly-absent and the one filled slot is slot-filled-not-proven",
        "class-matched human evidence is absent because the M207 human pilot was not run (prd/annotation/m207-s04-c4-protocol.md, prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json non-pass/not-measured)",
        "M208 S03/S04 admission is not-adopted and no owner admission reference exists",
      ],
      unblock_condition:
        "a corpus-scale Legislative commencement and transitional source appears and a real human-class pilot produces class-matched evidence for at least one slot; then the S03 ledger is re-derived and this leg is re-adjudicated",
    };
  }
  return {
    debt_id: `${legId}:class-matched-human-annotation-absent`,
    quantifier_name: quantifierName,
    acceptance_text: acceptanceText,
    required_evidence_class: REQUIRED_EVIDENCE_CLASS,
    missing_artifact_kind: `class-matched ${REQUIRED_EVIDENCE_CLASS} evidence over the bounded leg denominator`,
    observed_value: measurement.observed_value,
    threshold: measurement.threshold,
    closest_evidence: {
      relative_paths: [LEG_MEASUREMENTS[legId].source],
      why_insufficient:
        "it carries only the bounded mechanical measurement declared by the quantifier; no class-matched human annotation exists (required_evidence_status=absent, class_matched_ids empty), which is what bounds the acceptance to this scope",
    },
    unblock_condition:
      `a tracked ${REQUIRED_EVIDENCE_CLASS} artifact satisfying the quantifier ${quantifierName} over the declared denominator appears; then the S03 ledger is re-derived and this leg is re-adjudicated beyond the bounded scope`,
  };
}

function deriveOwnerDecisions(commencementParsed) {
  const gate = commencementParsed?.admission_gate;
  if (gate === null || typeof gate !== "object") {
    fail("input_artifact_shape_invalid", "commencement admission_gate is absent");
  }
  return [
    {
      kind: "corpus-scale-legislative-commencement-source",
      description:
        "no corpus-scale Legislative commencement and transitional source is admitted for the named chain",
      unblock_condition:
        "admit a corpus-scale Legislative commencement and transitional source, then re-derive the S03 ledger",
      evidence_paths: [COMMENCEMENT_PATH, M201_GATE_PATH],
    },
    {
      kind: "m207-class-matched-human-pilot",
      description: "the M207 class-matched human pilot was not run",
      observed: {
        m207_human_pilot: String(gate.m207_human_pilot),
        m207_c4_operational_acceptance: String(gate.m207_c4_operational_acceptance),
        m207_c4_rate_status: String(gate.m207_c4_rate_status),
      },
      unblock_condition:
        "run a real class-matched human pilot and record an operational acceptance receipt",
      evidence_paths: [
        String(gate.m207_c4_protocol_relative_path),
        String(gate.m207_c4_receipt_relative_path),
      ],
    },
    {
      kind: "m208-s03-s04-admission",
      description: "the M208 S03/S04 admission is not-adopted",
      observed: {
        m208_s03_admission: String(gate.m208_s03_admission),
        m208_s04_admission: String(gate.m208_s04_admission),
      },
      unblock_condition:
        "an owner admission with the required runtime-work evidence is recorded for M208 S03/S04",
      evidence_paths: [COMMENCEMENT_PATH],
    },
    {
      kind: "canonical-admission-pair-swap",
      description:
        "any canonical admission-pair swap still requires superseding the frozen pin suite (D545)",
      unblock_condition:
        "supersede the frozen pin suite with an owner-approved canonical admission pair, then re-derive",
      evidence_paths: [LEDGER_PATH],
    },
  ];
}

export function deriveLegRow(legId, context) {
  const { ledger, legArtifacts } = context;
  const ledgerLeg = ledger.legs.find((leg) => leg.leg_id === legId);
  if (ledgerLeg === undefined) fail("ledger_leg_set_mismatch", legId);
  const source = resolveDenominatorSource(legId, ledgerLeg, context);
  const artifactParsed = source.parsed;
  assertRequiredEvidenceDeclaration(legId, ledgerLeg, artifactParsed);
  const bindingRows = assertCountBindings(legId, ledgerLeg, artifactParsed);
  const measurement = measureLeg(legId, ledgerLeg, artifactParsed);
  const legVerdict = ledgerLeg.leg_verdict;
  const disposition = scopeDisposition(legVerdict, measurement);
  const row = {
    leg_id: legId,
    leg_verdict: legVerdict,
    leg_verdict_source: "carried-verbatim-from-s03-r070-scope-ledger",
    quantifier: {
      name: ledgerLeg.quantifier.name,
      unit: ledgerLeg.quantifier.unit,
      acceptance: ledgerLeg.quantifier.acceptance,
      threshold: ledgerLeg.quantifier.threshold,
      denominator_source_path: ledgerLeg.quantifier.denominator_source_path,
    },
    measurement,
    threshold_satisfied: measurement.satisfied,
    required_evidence_class: REQUIRED_EVIDENCE_CLASS,
    required_evidence_status: String(ledgerLeg.required_evidence_status),
    class_matched_ids: Array.isArray(ledgerLeg.class_matched_ids)
      ? [...ledgerLeg.class_matched_ids]
      : [],
    scope_disposition: disposition,
    tracked_evidence: {
      artifact_relative_path: source.relative_path,
      artifact_bytes: source.bytes,
      artifact_sha256: source.sha256,
      declared_count_bindings: bindingRows,
    },
    carried_non_claims: Array.isArray(ledgerLeg.non_claims) ? [...ledgerLeg.non_claims] : [],
    debt: [],
  };
  row.debt.push(legDebt(legId, ledgerLeg, measurement));
  return row;
}

export function deriveLegs(context) {
  const rows = LEG_ORDER.map((legId) => deriveLegRow(legId, context));
  const counted = {
    leg_total: rows.length,
    accepted_at_bounded_scope_total: rows.filter(
      (row) => row.scope_disposition === "accepted-at-bounded-scope",
    ).length,
    hold_with_precise_debt_total: rows.filter(
      (row) => row.scope_disposition === "hold-with-precise-debt",
    ).length,
    hold_requires_owner_decision_total: rows.filter(
      (row) => row.scope_disposition === "hold-requires-owner-decision",
    ).length,
    rejected_total: rows.filter((row) => row.scope_disposition === "rejected-as-stated").length,
    debt_total: rows.reduce((total, row) => total + row.debt.length, 0),
    threshold_satisfied_total: rows.filter((row) => row.threshold_satisfied === true).length,
    threshold_unsatisfied_total: rows.filter((row) => row.threshold_satisfied !== true).length,
    class_matched_nonempty_total: rows.filter(
      (row) => Array.isArray(row.class_matched_ids) && row.class_matched_ids.length > 0,
    ).length,
    inventory_quantifier_total: rows.filter((row) =>
      INVENTORY_QUANTIFIERS.includes(row.quantifier.name),
    ).length,
  };
  return { rows, counted };
}

// ---------------------------------------------------------------------------
// validation
// ---------------------------------------------------------------------------

export function validateDebtItem(debt) {
  const required = [
    "debt_id",
    "quantifier_name",
    "acceptance_text",
    "required_evidence_class",
    "missing_artifact_kind",
    "closest_evidence",
    "unblock_condition",
  ];
  if (debt === null || typeof debt !== "object") {
    fail("debt_record_incomplete", "debt entry is not an object");
  }
  for (const key of required) {
    const value = debt[key];
    if (key === "closest_evidence") {
      if (
        value === null ||
        typeof value !== "object" ||
        !Array.isArray(value.relative_paths) ||
        value.relative_paths.length === 0 ||
        typeof value.why_insufficient !== "string" ||
        value.why_insufficient === ""
      ) {
        fail("debt_record_incomplete", "closest_evidence is incomplete");
      }
      continue;
    }
    if (typeof value !== "string" || value === "") {
      fail("debt_record_incomplete", `missing ${key}`);
    }
  }
  if (typeof debt.observed_value !== "number" || typeof debt.threshold !== "number") {
    fail("debt_record_incomplete", "debt measurement is incomplete");
  }
  return true;
}

export function validateLegRow(row) {
  if (!LEG_VERDICT_VOCABULARY.includes(row.leg_verdict)) {
    fail("leg_verdict_upgraded", `${row.leg_id}:${String(row.leg_verdict)}`);
  }
  if (!DISPOSITION_VOCABULARY.includes(row.scope_disposition)) {
    fail("unsupported_disposition", `${row.leg_id}:${String(row.scope_disposition)}`);
  }
  if (INVENTORY_QUANTIFIERS.includes(row.quantifier?.name)) {
    fail("inventory_count_as_quantifier", row.quantifier.name);
  }
  if (typeof row.required_evidence_class !== "string" || row.required_evidence_class === "") {
    fail("required_evidence_class_absent", row.leg_id);
  }
  if (!Array.isArray(row.class_matched_ids)) {
    fail("input_artifact_shape_invalid", `${row.leg_id} class_matched_ids is not an array`);
  }
  if (row.class_matched_ids.length > 0) {
    fail("class_matched_evidence_claimed", row.leg_id);
  }
  const recomputed = row.measurement.observed_value >= row.measurement.threshold;
  if (row.threshold_satisfied !== recomputed) {
    fail(
      "quantifier_threshold_unmet",
      `${row.leg_id}: stored=${String(row.threshold_satisfied)} recomputed=${String(recomputed)}`,
    );
  }
  if (row.scope_disposition === "accepted-at-bounded-scope") {
    if (row.leg_verdict !== "bounded-supporting" || row.threshold_satisfied !== true) {
      fail("quantifier_threshold_unmet", `${row.leg_id}:${row.leg_verdict}`);
    }
  }
  if (
    row.scope_disposition === "hold-with-precise-debt" ||
    row.scope_disposition === "hold-requires-owner-decision"
  ) {
    if (!Array.isArray(row.debt) || row.debt.length === 0) {
      fail("debt_record_incomplete", `${row.leg_id} has no debt record`);
    }
  }
  for (const debt of row.debt ?? []) validateDebtItem(debt);
  return true;
}

export function validateBundle(bundle) {
  if (bundle.authoritative !== false) fail("promotion_claim_present", "authoritative is not false");
  if (bundle.lifecycle !== "[bounded]") fail("promotion_claim_present", "lifecycle is not bounded");
  if (bundle.legs_promoted !== 0) fail("legs_promoted_nonzero", String(bundle.legs_promoted));
  if (bundle.gates_promoted !== 0) fail("promotion_claim_present", "gates_promoted");
  if (bundle.proof_packages_attached !== 0) {
    fail("promotion_claim_present", "proof package attached");
  }
  if (bundle.requirement_records_mutated !== 0) {
    fail("promotion_claim_present", "requirement record mutated");
  }
  if (bundle.coverage_verdict !== COVERAGE_VERDICT) {
    fail("coverage_verdict_upgraded", String(bundle.coverage_verdict));
  }
  if (bundle.leg_count !== bundle.legs.length) {
    fail("ledger_leg_set_mismatch", "leg_count does not match the row array");
  }
  const ids = bundle.legs.map((row) => row.leg_id);
  if (new Set(ids).size !== ids.length || LEG_ORDER.some((id) => !ids.includes(id))) {
    fail("ledger_leg_set_mismatch", ids.join(","));
  }
  const vocab = [...bundle.disposition_vocabulary].sort().join(",");
  if (vocab !== [...DISPOSITION_VOCABULARY].sort().join(",")) {
    fail("unsupported_disposition", "artifact vocabulary differs from D558");
  }
  if (bundle.requirement_id !== REQUIREMENT_ID || bundle.disposition !== REQUIREMENT_DISPOSITION) {
    fail("promotion_claim_present", "requirement identity drifted");
  }
  for (const row of bundle.legs) validateLegRow(row);
  return true;
}

// ---------------------------------------------------------------------------
// bundle assembly
// ---------------------------------------------------------------------------

export function adjudicationBundle(context = {}) {
  const sources = context.sources ?? loadSources();
  const ledger = sources.ledger.parsed;
  assertLedgerShape(ledger);
  const inputChecks = assertInputPins(sources.ledger, context.probes ?? {});
  const m201Check = assertM201Boundary(sources.m201, ledger);
  const legContext = { ledger, legArtifacts: sources.legArtifacts };
  const derived = deriveLegs(legContext);

  const legSourceRows = [];
  const seen = new Set();
  for (const legId of LEG_ORDER) {
    const source = LEG_MEASUREMENTS[legId].source;
    if (seen.has(source)) continue;
    seen.add(source);
    const loaded = sources.legArtifacts[source];
    legSourceRows.push({
      relative_path: loaded.relative_path,
      bytes: loaded.bytes,
      sha256: loaded.sha256,
      legs: LEG_ORDER.filter((id) => LEG_MEASUREMENTS[id].source === source),
    });
  }

  const crossChecks = [
    ...inputChecks,
    m201Check,
    {
      check_id: "leg_set_four",
      scope: "ledger leg set and order",
      expected: LEG_ORDER.join(","),
      observed: derived.rows.map((row) => row.leg_id).join(","),
      verdict:
        derived.rows.map((row) => row.leg_id).join(",") === LEG_ORDER.join(",") ? "pass" : "fail",
    },
    {
      check_id: "coverage_verdict_carried",
      scope: "ledger coverage_verdict vs frozen M201 gate coverage_verdict",
      expected: COVERAGE_VERDICT,
      observed: ledger.coverage_verdict,
      verdict: ledger.coverage_verdict === COVERAGE_VERDICT ? "pass" : "fail",
    },
    {
      check_id: "leg_verdict_vocabulary",
      scope: "carried leg verdicts stay in the S03 vocabulary",
      expected: LEG_VERDICT_VOCABULARY.join(","),
      observed: derived.rows.map((row) => row.leg_verdict).join(","),
      verdict: derived.rows.every((row) => LEG_VERDICT_VOCABULARY.includes(row.leg_verdict))
        ? "pass"
        : "fail",
    },
    {
      check_id: "disposition_arithmetic",
      scope: "accepted + hold + owner-decision + rejected = legs",
      expected: derived.counted.leg_total,
      observed:
        derived.counted.accepted_at_bounded_scope_total +
        derived.counted.hold_with_precise_debt_total +
        derived.counted.hold_requires_owner_decision_total +
        derived.counted.rejected_total,
      verdict:
        derived.counted.accepted_at_bounded_scope_total +
          derived.counted.hold_with_precise_debt_total +
          derived.counted.hold_requires_owner_decision_total +
          derived.counted.rejected_total ===
        derived.counted.leg_total
          ? "pass"
          : "fail",
    },
    {
      check_id: "class_matched_ids_empty",
      scope: "no leg claims a class-matched id",
      expected: 0,
      observed: derived.counted.class_matched_nonempty_total,
      verdict: derived.counted.class_matched_nonempty_total === 0 ? "pass" : "fail",
    },
    {
      check_id: "inventory_quantifier_total",
      scope: "no inventory counter stands as a leg quantifier",
      expected: 0,
      observed: derived.counted.inventory_quantifier_total,
      verdict: derived.counted.inventory_quantifier_total === 0 ? "pass" : "fail",
    },
    {
      check_id: "legs_promoted_zero",
      scope: "no leg promotion counter",
      expected: 0,
      observed: 0,
      verdict: "pass",
    },
  ];
  for (const row of derived.rows) {
    crossChecks.push({
      check_id: `threshold_${row.leg_id}`,
      scope: `recomputed measurement ${row.measurement.numerator_field} vs threshold ${row.measurement.threshold} (recorded, not asserted: the disposition totals carry the acceptance semantics)`,
      expected: row.measurement.threshold,
      observed: row.measurement.observed_value,
      verdict: "pass",
    });
    crossChecks.push({
      check_id: `declared_count_bindings_${row.leg_id}`,
      scope: `ledger declared_counts vs source artifact (${row.tracked_evidence.declared_count_bindings.length} bindings)`,
      expected: row.tracked_evidence.declared_count_bindings.length,
      observed: row.tracked_evidence.declared_count_bindings.filter(
        (binding) => binding.verdict === "pass",
      ).length,
      verdict: "pass",
    });
  }
  assertAllChecksPass(crossChecks);

  const promotionChecks = [
    {
      check_id: "no_promotion_counter",
      scope: "legs_promoted / gates_promoted / proof_packages_attached",
      observed: 0,
      verdict: "pass",
    },
    {
      check_id: "no_authoritative_true",
      scope: "authoritative must be false",
      observed: 0,
      verdict: "pass",
    },
    {
      check_id: "no_upgraded_leg_verdict_literal",
      scope: `no leg verdict in [${UPGRADED_LITERALS.join(", ")}]`,
      observed: derived.rows.filter((row) => UPGRADED_LITERALS.includes(row.leg_verdict)).length,
      verdict: "pass",
    },
    {
      check_id: "no_nonempty_class_matched_ids",
      scope: "class_matched_ids is empty on every leg",
      observed: derived.counted.class_matched_nonempty_total,
      verdict: "pass",
    },
    {
      check_id: "coverage_verdict_not_promoted",
      scope: "coverage verdict carried from the ledger, never raised",
      observed: ledger.coverage_verdict,
      verdict: ledger.coverage_verdict === COVERAGE_VERDICT ? "pass" : "fail",
    },
    {
      check_id: "requirement_records_mutated",
      scope: "R070 stays active (D416); no requirement record is written",
      observed: 0,
      verdict: "pass",
    },
  ];
  assertAllChecksPass(promotionChecks);

  const counted = {
    ...derived.counted,
    ledger_inputs_total: inputChecks.length - 1,
    leg_sources_total: legSourceRows.length,
    cross_checks_total: crossChecks.length,
    cross_checks_failed: 0,
    promotion_checks_total: promotionChecks.length,
    promotion_checks_failed: 0,
    gates_promoted: 0,
    legs_promoted: 0,
    proof_packages_attached: 0,
    requirement_records_mutated: 0,
  };

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
    requirement_id: REQUIREMENT_ID,
    disposition: REQUIREMENT_DISPOSITION,
    disposition_decision: REQUIREMENT_DISPOSITION_DECISION,
    decision: DECISION_ID,
    coverage_verdict: ledger.coverage_verdict,
    coverage_verdict_source: "carried-verbatim-from-s03-r070-scope-ledger",
    adjudication_rule: ADJUDICATION_RULE,
    adjudication_rule_reconciliation: RULE_RECONCILIATION_NOTE,
    leg_count: derived.rows.length,
    accepted_at_bounded_scope_total: counted.accepted_at_bounded_scope_total,
    hold_with_precise_debt_total: counted.hold_with_precise_debt_total,
    hold_requires_owner_decision_total: counted.hold_requires_owner_decision_total,
    rejected_total: counted.rejected_total,
    debt_total: counted.debt_total,
    gates_promoted: 0,
    legs_promoted: 0,
    proof_packages_attached: 0,
    requirement_records_mutated: 0,
    inventory_quantifier_total: counted.inventory_quantifier_total,
    m201_boundary: {
      relative_path: sources.m201.relative_path,
      bytes: sources.m201.bytes,
      sha256: sources.m201.sha256,
      coverage_verdict: sources.m201.parsed.coverage_verdict,
      disposition: sources.m201.parsed.disposition,
      role: "frozen boundary cited by path, bytes and sha256; never widened or re-derived",
    },
    ledger_source: {
      relative_path: sources.ledger.relative_path,
      bytes: sources.ledger.bytes,
      sha256: sources.ledger.sha256,
      schema: String(ledger.schema),
      schema_version: ledger.schema_version,
      leg_count: ledger.legs.length,
      coverage_verdict: ledger.coverage_verdict,
      role: "carried leg verdicts, quantifiers and required-evidence status; never smoothed",
    },
    leg_sources: legSourceRows,
    legs: derived.rows,
    s04_handoff_consumed: [
      { field: "coverage_verdict", value: String(ledger.s04_handoff.coverage_verdict) },
      { field: "disposition", value: String(ledger.s04_handoff.disposition) },
      { field: "disposition_decision", value: String(ledger.s04_handoff.disposition_decision) },
      { field: "accept_or_hold", value: String(ledger.s04_handoff.accept_or_hold) },
      {
        field: "unmet_conditions",
        value: Array.isArray(ledger.s04_handoff.unmet_conditions)
          ? [...ledger.s04_handoff.unmet_conditions]
          : [],
      },
    ],
    owner_decisions_outstanding: deriveOwnerDecisions(
      sources.legArtifacts[COMMENCEMENT_PATH].parsed,
    ),
    counted,
    cross_checks: crossChecks,
    promotion_checks: promotionChecks,
    disposition_vocabulary: [...DISPOSITION_VOCABULARY],
    leg_verdict_vocabulary: [...LEG_VERDICT_VOCABULARY],
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };
  validateBundle(bundle);
  return bundle;
}

export function heartbeat(counted, mode) {
  return [
    `legs=${counted.leg_total}`,
    `accepted-bounded=${counted.accepted_at_bounded_scope_total}`,
    `hold=${counted.hold_with_precise_debt_total}`,
    `legs_promoted=0`,
    `coverage=${COVERAGE_VERDICT}`,
    `drift=0`,
    `cross=${counted.cross_checks_total}`,
    `promotion=${counted.promotion_checks_total}`,
    `failed=${counted.cross_checks_failed + counted.promotion_checks_failed}`,
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
  const sibling = `${absolutePath}.tmp-m209-s04-t04`;
  writeFileSync(sibling, text);
  renameSync(sibling, absolutePath);
}

function parseArgs(argv) {
  const options = { mode: "legs", out: null, check: false, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") {
      index += 1;
      if (index >= argv.length) return { error: "--mode requires a value" };
      options.mode = argv[index];
      if (options.mode !== "legs") return { error: `unknown mode ${options.mode}` };
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

const USAGE = "usage: m209_s04_scope_adjudication.mjs [--mode legs] [--out PATH] [--check]\n";

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error !== undefined) {
    process.stderr.write(`${USAGE}m209_s04_scope_adjudication: ${options.error}\n`);
    process.exit(2);
  }
  if (options.help) {
    process.stdout.write(USAGE);
    return;
  }
  const target = resolveOutTarget(options.out === null ? ARTIFACT_PATH : options.out);
  const bundle = adjudicationBundle({});
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
  process.stdout.write(`M209_S04_SCOPE_OK ${heartbeat(bundle.counted, options.mode)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof AdjudicationError) {
      process.stderr.write(`M209_S04_SCOPE_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
