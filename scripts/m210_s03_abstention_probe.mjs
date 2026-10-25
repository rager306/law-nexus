#!/usr/bin/env node
// M210-3afp79 S03 T03 -- fail-closed abstention diagnostic over every source-bound input of S01.
//
// WHY THIS FILE EXISTS
// The milestone success criterion demands fail-closed diagnostics while the S03
// sketch forbids a runtime. A declaration ("the runtime abstains") is not
// evidence; an empirical diagnostic over the actual source-bound inputs is. This
// generator walks all eighteen inputs S01 committed -- eight dispute cards,
// eight corpus probes and two negative examples -- and records, per input, that
// the bounded candidate layer *is adopted* (admission_granted, variant C) yet
// *is not executed*, so that no candidate is emitted, no Conflict is reachable
// and the outcome is Unknown with the one reason `candidate_layer_not_executed`.
// It mints no candidate, computes no semantics and writes no legal text.
//
// The point of the diagnostic is the separation: candidates are absent because
// the adopted layer is not executed, NOT because adoption is absent. A v1-style
// reading (`no_adopted_construct`) is refused by name as
// `execution_read_as_adoption`; a claim of emission on the strength of adoption
// is refused as `adoption_read_as_execution`.
//
// WHAT IS DERIVED, FROM WHERE
//   * admission verdict, adopted_construct_set, execution_state, source_revision,
//     guards                        <- prd/architecture/m210-s03-start-gate.json
//   * the outcome dictionary and the emission rule (read, never re-decided)
//                                     <- prd/architecture/m210-s03-bounded-semantics-contract.json
//   * the eighteen inputs and their anchors (cards, corpus probes, negatives)
//                                     <- prd/architecture/m210-s01-source-bound-examples.json
//   * the declared sha256 of the examples artifact
//                                     <- prd/architecture/m210-s01-packet-index.json
//   * the granted admission source    <- prd/architecture/m210-s02-adoption-checkpoint-v2.md
//   * the section 3 pin               <- prd/temporal-legal-model.md
//
// THE CORPUS
//   * A corpus probe's count-only pin (path, span, bytes, sha256) is copied from
//     the tracked S01 artifact and re-verified against live bytes when the
//     licensed corpus (consru_export/, untracked) resolves locally. When it does
//     not, the probe still renders: the report bytes never depend on the corpus
//     being mounted, so --check stays byte-stable on a machine without it.
//
// WHAT IS NEVER WRITTEN
//   * No legal text, no XML tag and no corpus content: a corpus anchor carries
//     only path, span, bytes and sha256, and the artifact is ASCII-only with a
//     closed marker set.
//   * No candidate record and no Conflict verdict: while execution_state.executed
//     is false both are refused, and every committed S03 artifact is scanned for
//     candidate records and reported Conflict verdicts.
//   * No timestamp and no aggregate engine hash: the artifact is canonical
//     compact ASCII JSON with a fixed key order, so a whole-file byte compare in
//     --check mode is the determinism proof.
//
// NAMED FAIL-CLOSED CODES (each is exercised by the contract test)
//   probe_coverage_incomplete              the eighteen inputs are not all covered once, or a family is uncovered
//   adopted_set_misreported                the adopted_construct_set drifted, is empty under admission_granted, or the variant/verdict drifted
//   candidate_emitted_while_not_executed   a candidate record or candidate outcome exists while execution_state.executed is false
//   conflict_reported_while_absent         a Conflict verdict or outcome is reported while execution_state.executed is false
//   unknown_miscounted                     the counts block disagrees with the outcomes, or a non-Unknown outcome slipped in
//   absence_as_falsity                     absence of evidence is read as falsity, or an Unknown outcome is not reason-bound
//   adoption_read_as_execution             the report claims execution or an emitted candidate on the strength of adoption
//   execution_read_as_adoption             the report reads non-execution as non-adoption (adoption_established is not true, or the reason is no_adopted_construct)
//   input_missing_silent                   an input anchor is absent, not repository-relative, or outside the corpus root
//   input_hash_mismatch                    an input anchor sha256 (or a consumed revision) differs from the live bytes
//   report_not_byte_identical              --check rendered bytes differ from the committed artifact
//   runtime_claim_present                  the artifact claims a runtime, an evaluator or a crate surface
//   non_ascii_artifact                     the artifact carries a non-ASCII byte
//   raw_text_leak                          the artifact carries an XML tag, a provider marker or a corpus anchor key outside the closed set
//
// USAGE
//   node scripts/m210_s03_abstention_probe.mjs --write      # default
//   node scripts/m210_s03_abstention_probe.mjs --check
//   node scripts/m210_s03_abstention_probe.mjs --print      # JSON to stdout, markers to stderr
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, no cargo, byte-stable output for byte-stable inputs.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const ARTIFACT_RELATIVE_PATH = "prd/architecture/m210-s03-abstention-report.json";

export const SCHEMA = "law-nexus/m210-s03-abstention-report/v1";
export const KIND = "m210-s03-abstention-report";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S03";
export const TASK = "T03";
export const LIFECYCLE = ["proposed"];
export const VERDICT = "abstention_total";
export const ADMISSION_VERDICT = "admission_granted";
export const ADOPTED_VARIANT = "C";
export const ADOPTED_VARIANT_LABEL = "abstention_first_candidates_only";
export const ADOPTED_CONSTRUCT_SET = [
  "candidate_emission",
  "source_anchors",
  "family_classification_hypotheses",
  "unknown_verdict",
  "conflict_verdict",
  "provenance_links",
];
export const OWNER_ADMISSION_REF = "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f";
export const AUTHENTICATED_VIA = "authenticated subjective-UAT v2";
export const NOT_EXECUTED = "not-executed";
export const UNKNOWN_REASON = "candidate_layer_not_executed";
export const LEGACY_REASON_MISREAD = "no_adopted_construct";
export const UNKNOWN_OUTCOME = "Unknown";
export const CANDIDATE_OUTCOME = "candidate_emitted";
export const CONFLICT_OUTCOME = "Conflict";
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];
export const ORIGINATING_REVIEW = "doc/review/review-28-10-09-2026.md RC28-F18";

export const S01_EXAMPLES_PATH = "prd/architecture/m210-s01-source-bound-examples.json";
export const S01_PACKET_INDEX_PATH = "prd/architecture/m210-s01-packet-index.json";
export const S01_REGISTER_PATH = "prd/architecture/m210-s01-normative-family-register.json";
export const START_GATE_PATH = "prd/architecture/m210-s03-start-gate.json";
export const CONTRACT_PATH = "prd/architecture/m210-s03-bounded-semantics-contract.json";
export const ADOPTION_CHECKPOINT_PATH = "prd/architecture/m210-s02-adoption-checkpoint-v2.md";
export const SECTION3_PATH = "prd/temporal-legal-model.md";

// The three committed S03 artifacts scanned for candidate records and Conflict verdicts.
export const S03_ARTIFACT_PATHS = [START_GATE_PATH, CONTRACT_PATH, ARTIFACT_RELATIVE_PATH];

export const INPUT_KINDS = ["dispute_card", "corpus_probe", "negative_example"];

export const EXPECTED_COVERAGE = {
  families: 8,
  dispute_cards: 8,
  corpus_probes: 8,
  negative_examples: 2,
  inputs: 18,
};

export const EXPECTED_COUNTS = {
  adopted_constructs: ADOPTED_CONSTRUCT_SET.length,
  candidates: 0,
  conflicts: 0,
  unknown: EXPECTED_COVERAGE.inputs,
};

export const EMITTABLE_CODES = [
  "absence_as_falsity",
  "adopted_set_misreported",
  "adoption_read_as_execution",
  "candidate_emitted_while_not_executed",
  "conflict_reported_while_absent",
  "execution_read_as_adoption",
  "input_hash_mismatch",
  "input_missing_silent",
  "non_ascii_artifact",
  "probe_coverage_incomplete",
  "raw_text_leak",
  "report_not_byte_identical",
  "runtime_claim_present",
  "unknown_miscounted",
];

export const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;

export const CORPUS_ROOT_RELATIVE = "consru_export/consru_export/exports/npa";
export const CORPUS_DIR_ENV = "M210_S03_CORPUS_DIR";
export const CORPUS_SPAN_CAP = 4096;

// A corpus anchor carries exactly these keys: any extra key is refused, because
// the only honest corpus record is a count-only pin.
const CORPUS_ANCHOR_KEYS = new Set(["anchor_kind", "path", "span", "bytes", "sha256"]);

const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// XML tags and provider text markers: never legitimate in a count-only artifact.
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl ", "#[test]", "fn main"];

const NON_CLAIMS = [
  "This report is a diagnostic, not a runtime: no evaluator, no semantic object and no crate surface is created or promised.",
  "The bounded candidate layer is adopted: adoption_state records admission_granted with variant C and its construct set, and adoption is established as a state of its own.",
  "Adoption is not execution and execution is not adoption: adoption_established is true while execution_state records not-executed, zero candidates and zero conflicts.",
  "Every one of the eighteen source-bound inputs resolves to Unknown with reason candidate_layer_not_executed: candidates are absent because the adopted candidate layer is not executed, not because adoption is absent.",
  "Unknown is not Conflict and neither is a negative finding: absence of a proven source span is never falsity, and no input is reported as false.",
  "A corpus anchor carries only path, span, bytes and sha256; no legal text is copied and a probe is a coverage label, not a reading.",
  "Section 3 of prd/temporal-legal-model.md is byte-identical to its recorded pin and the deferred terms stay deferred-undefined.",
  "F13 stays deferred-explicit: it is a separate decision with its own owning surfaces and is never derived from the bounded IR.",
  "Guards stay at their required zero: no crate is touched, no requirement is promoted, no Review Case event is written and no normative semantics is adopted.",
];

const REVISION_POLICY =
  "Re-derive before use: re-hash every consumed path, re-read the eighteen inputs from the S01 artifact, re-read the admission and execution state from the S03 start gate and the authenticated S02 v2 checkpoint, and re-render; no timestamp and no aggregate engine hash are stored here.";

class BuildError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "BuildError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new BuildError(code, detail);
}

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

function assertReadable(relativePath) {
  if (!isRepoRelative(relativePath)) {
    fail("input_missing_silent", `${relativePath} is not repository-relative`);
  }
  for (const prefix of FORBIDDEN_PREFIXES) {
    if (relativePath.startsWith(prefix)) {
      fail("input_missing_silent", `${relativePath} is an ignored overlay path`);
    }
  }
}

export function hashBytes(bytes) {
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

export function hashFile(rootDir, relativePath) {
  assertReadable(relativePath);
  return hashBytes(readFileSync(path.join(rootDir, relativePath)));
}

function readJson(rootDir, relativePath) {
  assertReadable(relativePath);
  const absolute = path.join(rootDir, relativePath);
  if (!existsSync(absolute) || !statSync(absolute).isFile()) {
    fail("input_missing_silent", `consumed input is absent: ${relativePath}`);
  }
  return JSON.parse(readFileSync(absolute, "utf8"));
}

// ---------------------------------------------------------------------------
// the one predicate
// ---------------------------------------------------------------------------

// The abstention predicate of this diagnostic. The diagnostic is scoped to the
// adopted-but-not-executed state: adoption is established and execution has not
// run, so every input is Unknown for one stated reason. When adoption is not
// established, or when execution *has* run, the state is outside this diagnostic
// and the predicate returns null so the validator fails closed by name
// (execution_read_as_adoption / adoption_read_as_execution). No non-abstention
// outcome is ever invented here.
export function resolveOutcome({ adoptionEstablished, executed } = {}) {
  if (adoptionEstablished !== true) return null;
  if (executed === true) return null;
  return { outcome: UNKNOWN_OUTCOME, reason: UNKNOWN_REASON };
}

// ---------------------------------------------------------------------------
// input derivation
// ---------------------------------------------------------------------------

export function expectedInputIds(s01Examples) {
  const cards = Array.isArray(s01Examples?.dispute_cards) ? s01Examples.dispute_cards : [];
  const probes = Array.isArray(s01Examples?.corpus_probes) ? s01Examples.corpus_probes : [];
  const negatives = Array.isArray(s01Examples?.negative_examples) ? s01Examples.negative_examples : [];
  return [
    ...cards.map((card) => card.card_id),
    ...probes.map((probe) => probe.probe_id),
    ...negatives.map((example) => example.example_id),
  ];
}

// A tracked input anchor: path plus section plus the sha256 pin, copied from the
// tracked S01 artifact and re-verified against live bytes.
function trackedAnchor(anchor) {
  return {
    anchor_kind: "tracked",
    path: anchor.path,
    section: anchor.section,
    sha256: anchor.sha256,
  };
}

// A corpus input anchor: path, span, bytes and sha256 only. No section, no text.
function corpusAnchor(probe) {
  return {
    anchor_kind: "corpus-span",
    path: probe.path,
    span: { start: probe.span?.start, end: probe.span?.end },
    bytes: probe.bytes,
    sha256: probe.sha256,
  };
}

export function buildOutcomes(s01Examples, state = {}) {
  const resolution = resolveOutcome(state);
  const adoptionEstablished = state?.adoptionEstablished === true;
  const executed = state?.executed === true;
  const outcomes = [];
  const push = (input) => {
    outcomes.push({
      input_id: input.input_id,
      input_kind: input.input_kind,
      family_id: input.family_id,
      anchor: input.anchor,
      adoption_established: adoptionEstablished,
      executed,
      outcome: resolution === null ? null : resolution.outcome,
      reason: resolution === null ? null : resolution.reason,
      absence_is_falsity: false,
    });
  };

  for (const card of s01Examples?.dispute_cards ?? []) {
    push({
      input_id: card.card_id,
      input_kind: "dispute_card",
      family_id: card.family,
      anchor: trackedAnchor(card.anchor),
    });
  }
  for (const probe of s01Examples?.corpus_probes ?? []) {
    push({
      input_id: probe.probe_id,
      input_kind: "corpus_probe",
      family_id: probe.family,
      anchor: corpusAnchor(probe),
    });
  }
  for (const example of s01Examples?.negative_examples ?? []) {
    push({
      input_id: example.example_id,
      input_kind: "negative_example",
      family_id: null,
      anchor: trackedAnchor(example.anchor),
    });
  }
  return outcomes;
}

function coverageOf(outcomes) {
  const kinds = new Map(INPUT_KINDS.map((kind) => [kind, 0]));
  const families = new Set();
  for (const outcome of outcomes) {
    if (kinds.has(outcome.input_kind)) kinds.set(outcome.input_kind, kinds.get(outcome.input_kind) + 1);
    if (typeof outcome.family_id === "string") families.add(outcome.family_id);
  }
  return {
    families: families.size,
    dispute_cards: kinds.get("dispute_card"),
    corpus_probes: kinds.get("corpus_probe"),
    negative_examples: kinds.get("negative_example"),
    inputs: outcomes.length,
  };
}

function countsOf(outcomes, adoptedConstructSet) {
  const counts = {
    adopted_constructs: Array.isArray(adoptedConstructSet) ? adoptedConstructSet.length : 0,
    candidates: 0,
    conflicts: 0,
    unknown: 0,
  };
  for (const outcome of outcomes) {
    if (outcome.outcome === CANDIDATE_OUTCOME) counts.candidates += 1;
    else if (outcome.outcome === CONFLICT_OUTCOME) counts.conflicts += 1;
    else if (outcome.outcome === UNKNOWN_OUTCOME) counts.unknown += 1;
  }
  return counts;
}

// ---------------------------------------------------------------------------
// live corpus anchors
// ---------------------------------------------------------------------------

export function corpusPresent(corpusDir, rootDir = REPO_ROOT) {
  const directory = corpusDir ?? path.join(rootDir, CORPUS_ROOT_RELATIVE);
  return existsSync(directory) && statSync(directory).isDirectory();
}

// Re-derive the live corpus pins for every S01 corpus probe whose file resolves
// locally. Used only for verification: the committed report pins come from the
// tracked S01 artifact, never from this function.
export function liveCorpusAnchors(s01Examples, rootDir = REPO_ROOT) {
  const anchors = [];
  for (const probe of s01Examples?.corpus_probes ?? []) {
    const absolute = path.join(rootDir, probe.path);
    if (!existsSync(absolute) || !statSync(absolute).isFile()) continue;
    const bytes = readFileSync(absolute);
    anchors.push({
      family: probe.family,
      path: probe.path,
      span: { start: 0, end: Math.min(bytes.length, CORPUS_SPAN_CAP) },
      bytes: bytes.length,
      sha256: hashBytes(bytes),
    });
  }
  return anchors;
}

// ---------------------------------------------------------------------------
// committed-artifact scan
// ---------------------------------------------------------------------------

function countCandidateRecords(doc) {
  let count = 0;
  if (Array.isArray(doc?.candidates)) count += doc.candidates.length;
  if (Array.isArray(doc?.candidate_records)) count += doc.candidate_records.length;
  if (doc?.candidate_envelope?.minted === true) count += 1;
  if (doc?.minted === true) count += 1;
  return count;
}

function countConflictVerdicts(doc) {
  let count = 0;
  for (const key of ["outcomes", "emitted", "candidate_records", "candidates", "records"]) {
    if (!Array.isArray(doc?.[key])) continue;
    for (const entry of doc[key]) {
      const verdict = entry?.outcome ?? entry?.verdict;
      if (verdict === CONFLICT_OUTCOME) count += 1;
    }
  }
  return count;
}

export function scanCommittedS03(otherArtifacts, report) {
  const documents = [
    { path: START_GATE_PATH, doc: otherArtifacts?.[START_GATE_PATH] },
    { path: CONTRACT_PATH, doc: otherArtifacts?.[CONTRACT_PATH] },
    { path: ARTIFACT_RELATIVE_PATH, doc: report },
  ];
  let candidateRecords = 0;
  let conflictVerdicts = 0;
  for (const entry of documents) {
    candidateRecords += countCandidateRecords(entry.doc);
    conflictVerdicts += countConflictVerdicts(entry.doc);
  }
  return { artifacts_scanned: documents.length, candidate_records: candidateRecords, conflict_verdicts: conflictVerdicts };
}

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------

function deriveConsumes(rootDir) {
  const table = [
    [S01_EXAMPLES_PATH, "the eighteen source-bound inputs: eight dispute cards, eight corpus probes and two negative examples"],
    [S01_PACKET_INDEX_PATH, "declared sha256 of the S01 examples artifact: the input binding cross-check"],
    [START_GATE_PATH, "admission verdict, adopted_construct_set, execution_state, source_revision and the zero guards"],
    [CONTRACT_PATH, "the outcome dictionary and the emission rule read here, never re-decided"],
    [ADOPTION_CHECKPOINT_PATH, "admission source: records granted, so the adopted candidate layer is established and not executed"],
    [SECTION3_PATH, "the section 3 pin carried by guards.section3_pin"],
  ];
  return table.map(([relativePath, role]) => ({
    path: relativePath,
    sha256: hashFile(rootDir, relativePath),
    role,
  }));
}

export function renderReport(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const corpusDir = options.corpusDir;
  const s01Examples = options.s01Examples ?? readJson(rootDir, S01_EXAMPLES_PATH);
  const packetIndex = options.packetIndex ?? readJson(rootDir, S01_PACKET_INDEX_PATH);
  const startGate = options.startGate ?? readJson(rootDir, START_GATE_PATH);
  const contract = options.contract ?? readJson(rootDir, CONTRACT_PATH);

  if (!Array.isArray(startGate?.adopted_construct_set) || startGate.adopted_construct_set.length === 0) {
    fail("adopted_set_misreported", "the start gate must record a non-empty adopted_construct_set");
  }
  if (startGate?.admission_verdict !== ADMISSION_VERDICT) {
    fail("adopted_set_misreported", `the start gate admission verdict must be ${ADMISSION_VERDICT}`);
  }
  if (startGate?.execution_state?.executed === true) {
    fail("adoption_read_as_execution", "the start gate records execution: adoption is not execution");
  }
  if (typeof startGate?.source_revision !== "string") {
    fail("input_hash_mismatch", "the start gate carries no source_revision");
  }
  if (!Array.isArray(contract?.outcome_dictionary?.outcomes)) {
    fail("probe_coverage_incomplete", "the S03 semantics contract carries no outcome dictionary");
  }

  const adoptedConstructSet = startGate.adopted_construct_set;
  const executed = startGate?.execution_state?.executed === true;
  const adoptionEstablished = startGate?.adoption_state?.adoption_established === true;
  if (!adoptionEstablished) {
    fail("execution_read_as_adoption", "the start gate must record adoption_established: non-execution is not non-adoption");
  }

  const outcomes = buildOutcomes(s01Examples, { adoptionEstablished, executed });
  const expectedIds = expectedInputIds(s01Examples);
  if (outcomes.length !== expectedIds.length) {
    fail("probe_coverage_incomplete", `derived ${outcomes.length} inputs, expected ${expectedIds.length}`);
  }

  const report = {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: LIFECYCLE,
    authoritative: false,
    ascii_only: true,
    design_only: true,
    runtime_created: false,
    evaluator_created: false,
    requirement_refs: REQUIREMENT_REFS,
    originating_review: ORIGINATING_REVIEW,
    source_revision: startGate.source_revision,
    adoption_state: {
      admission_verdict: startGate.admission_verdict,
      adoption_established: adoptionEstablished,
      adoption_source: ADOPTION_CHECKPOINT_PATH,
      authenticated_via: startGate?.adoption_state?.authenticated_via ?? AUTHENTICATED_VIA,
      owner_admission_ref: startGate?.owner_admission_ref ?? startGate?.adoption_state?.owner_admission_ref ?? OWNER_ADMISSION_REF,
      adopted_variant: startGate.adopted_variant ?? ADOPTED_VARIANT,
      adopted_variant_label: startGate.adopted_variant_label ?? ADOPTED_VARIANT_LABEL,
      adopted_construct_set: adoptedConstructSet,
      normative_semantics_adopted: false,
      section3_terms: startGate?.adoption_state?.section3_terms ?? "deferred-undefined",
      execution_separated: true,
      note: "The admission verdict is carried from the S03 start gate under the authenticated S02 v2 grant: the bounded candidate layer is adopted (adopted_construct_set is non-empty). Adoption is a state of its own and is not execution; execution_state records that nothing ran.",
    },
    execution_state: {
      state: NOT_EXECUTED,
      executed: false,
      candidates_emitted: 0,
      conflicts: 0,
      runtime_work: startGate?.execution_state?.runtime_work ?? "not-started",
      runtime_demo: startGate?.execution_state?.runtime_demo ?? "not-proven",
      note: "Nothing has been executed: executed is false, candidates_emitted is zero and conflicts is zero. The adopted construct set is non-empty, so emission is permitted in principle, but a candidate requires actual execution of an adopted construct and a proven source span. Adoption alone yields Unknown for every input with reason candidate_layer_not_executed.",
    },
    consumes: deriveConsumes(rootDir),
    coverage: coverageOf(outcomes),
    outcomes,
    counts: countsOf(outcomes, adoptedConstructSet),
    verdict: VERDICT,
    guards: {
      crates_touched: [],
      requirements_promoted: 0,
      review_case_events_written: 0,
      semantics_adopted: false,
      section3_pin: hashFile(rootDir, SECTION3_PATH),
    },
    scan: scanCommittedS03({ [START_GATE_PATH]: startGate, [CONTRACT_PATH]: contract }, null),
    absence_is_not_falsity: true,
    fail_closed_codes: EMITTABLE_CODES,
    non_claims: NON_CLAIMS,
    revision_policy: REVISION_POLICY,
  };

  // The rendered report is scanned as its own third artifact: the scan summary
  // must not depend on whether the report is already committed on disk.
  report.scan = scanCommittedS03({ [START_GATE_PATH]: startGate, [CONTRACT_PATH]: contract }, report);

  return {
    report,
    text: JSON.stringify(report),
    inputs: { s01Examples, packetIndex, startGate, contract },
    corpusPresent: corpusPresent(corpusDir, rootDir),
    liveAnchors: liveCorpusAnchors(s01Examples, rootDir),
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateReport(report, env = {}) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });

  const text = env.reportText ?? JSON.stringify(report);
  const exists = env.exists ?? (() => true);
  const liveSha = env.sha256 ?? (() => null);
  const corpusLive = env.corpusPresent ?? false;
  const liveAnchors = Array.isArray(env.liveCorpusAnchors) ? env.liveCorpusAnchors : [];
  const liveByFamily = new Map(liveAnchors.map((anchor) => [anchor.family, anchor]));
  const s01Examples = env.s01Examples ?? null;
  const startGate = env.startGate ?? null;
  const otherArtifacts = env.s03Artifacts ?? {};

  // 1. text hygiene.
  if ([...text].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the report carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) add("runtime_claim_present", `runtime marker ${marker}`);
  }

  // 2. no runtime and no evaluator claim.
  if (report?.runtime_created === true || report?.evaluator_created === true) {
    add("runtime_claim_present", "the report claims a runtime or an evaluator");
  }
  if (report?.semantics_adopted === true) {
    add("runtime_claim_present", "the report claims adopted semantics");
  }

  // 3. guards stay at their required zero.
  const guards = report?.guards ?? {};
  if (Array.isArray(guards.crates_touched) ? guards.crates_touched.length !== 0 : true) {
    add("runtime_claim_present", "crates_touched must be an empty array");
  }
  if (guards.requirements_promoted !== 0) add("adopted_set_misreported", "requirements_promoted must be 0");
  if (guards.review_case_events_written !== 0) {
    add("adoption_read_as_execution", "review_case_events_written must be 0");
  }
  if (guards.semantics_adopted !== false) add("adopted_set_misreported", "semantics_adopted must be false");
  if (typeof guards.section3_pin !== "string" || !SHA_PATTERN.test(guards.section3_pin)) {
    add("input_hash_mismatch", "section3_pin must be a well-formed sha256 pin");
  } else {
    const liveSection3 = liveSha(env.section3Path ?? SECTION3_PATH);
    if (typeof liveSection3 === "string" && liveSection3 !== guards.section3_pin) {
      add("input_hash_mismatch", "section3_pin differs from the live section 3 bytes");
    }
  }

  // 4. the adopted set must be the granted candidate layer, and the admission
  //    verdict must not drift from the live start gate.
  const adoption = report?.adoption_state ?? {};
  const execution = report?.execution_state ?? {};
  const adoptedSet = Array.isArray(adoption.adopted_construct_set) ? adoption.adopted_construct_set : null;
  const liveAdoptedSet = Array.isArray(startGate?.adopted_construct_set)
    ? startGate.adopted_construct_set
    : ADOPTED_CONSTRUCT_SET;
  if (adoptedSet === null) {
    add("adopted_set_misreported", "adopted_construct_set must be an array");
  } else if (JSON.stringify(adoptedSet) !== JSON.stringify(liveAdoptedSet)) {
    add("adopted_set_misreported", "adopted_construct_set drifted from the live start gate");
  } else if (adoptedSet.length === 0) {
    add("adopted_set_misreported", "adopted_construct_set must be non-empty under admission_granted");
  }
  if (adoption.admission_verdict !== ADMISSION_VERDICT) {
    add("adopted_set_misreported", `admission_verdict must be ${ADMISSION_VERDICT}`);
  }
  if (typeof startGate?.admission_verdict === "string" && adoption.admission_verdict !== startGate.admission_verdict) {
    add("adopted_set_misreported", "admission_verdict drifted from the live start gate");
  }
  if (adoption.adopted_variant !== ADOPTED_VARIANT) {
    add("adopted_set_misreported", `adopted_variant must be ${ADOPTED_VARIANT}`);
  }
  if (adoption.normative_semantics_adopted === true) {
    add("adopted_set_misreported", "the bounded construct adoption must not be read as normative semantics adoption");
  }
  if (adoption.adoption_established !== true) {
    add(
      "execution_read_as_adoption",
      "adoption_established must be true: non-execution is never read as non-adoption",
    );
  }
  if (typeof startGate?.source_revision === "string" && report?.source_revision !== startGate.source_revision) {
    add("input_hash_mismatch", "source_revision drifted from the live start gate");
  }

  // 4b. execution must stay not-executed: adoption is not execution.
  if (execution.executed !== false) {
    add("adoption_read_as_execution", "execution.executed must be false: adoption is not execution");
  }
  if (execution.state !== undefined && execution.state !== NOT_EXECUTED) {
    add("adoption_read_as_execution", `execution.state must be ${NOT_EXECUTED}`);
  }
  if (execution.candidates_emitted !== 0) {
    add("adoption_read_as_execution", "execution.candidates_emitted must be 0");
  }
  if (execution.conflicts !== 0) {
    add("adoption_read_as_execution", "execution.conflicts must be 0");
  }

  // 5. absence is never falsity.
  if (report?.absence_is_not_falsity !== true) {
    add("absence_as_falsity", "the report must declare that absence is not falsity");
  }

  // 6. the eighteen inputs are covered exactly once.
  const outcomes = Array.isArray(report?.outcomes) ? report.outcomes : null;
  if (!outcomes) {
    add("probe_coverage_incomplete", "outcomes is missing");
  } else {
    const ids = outcomes.map((outcome) => outcome?.input_id);
    if (new Set(ids).size !== ids.length) add("probe_coverage_incomplete", "duplicate input ids");
    if (outcomes.length !== EXPECTED_COVERAGE.inputs) {
      add("probe_coverage_incomplete", `expected ${EXPECTED_COVERAGE.inputs} inputs, found ${outcomes.length}`);
    }
    if (s01Examples) {
      const expected = [...expectedInputIds(s01Examples)].sort();
      const actual = [...ids].sort();
      if (JSON.stringify(actual) !== JSON.stringify(expected)) {
        add("probe_coverage_incomplete", "the outcome input ids are not the S01 input ids");
      }
    }
    const derivedCoverage = coverageOf(outcomes.filter((outcome) => outcome && typeof outcome === "object"));
    const declaredCoverage = report?.coverage ?? {};
    for (const key of Object.keys(EXPECTED_COVERAGE)) {
      if (declaredCoverage[key] !== derivedCoverage[key]) {
        add("probe_coverage_incomplete", `coverage.${key} disagrees with the outcomes`);
      }
      if (derivedCoverage[key] !== EXPECTED_COVERAGE[key]) {
        add("probe_coverage_incomplete", `coverage.${key} is ${derivedCoverage[key]}, expected ${EXPECTED_COVERAGE[key]}`);
      }
    }
  }

  // 7. every outcome is Unknown for the one stated reason, is not falsity, and
  //    keeps adoption distinct from execution.
  const executed = execution.executed === true;
  if (outcomes) {
    for (const outcome of outcomes) {
      const scope = `input ${outcome?.input_id ?? "<unnamed>"}`;
      if (outcome?.adoption_established !== true) {
        add("execution_read_as_adoption", `${scope} must record adoption_established true`);
      }
      if (outcome?.executed === true) {
        add("adoption_read_as_execution", `${scope} must record executed false`);
      }
      if (outcome?.absence_is_falsity === true) add("absence_as_falsity", `${scope} reads absence as falsity`);
      if (outcome?.outcome === CANDIDATE_OUTCOME) {
        if (!executed) add("candidate_emitted_while_not_executed", `${scope} is a candidate while execution has not run`);
      } else if (outcome?.outcome === CONFLICT_OUTCOME) {
        if (!executed) add("conflict_reported_while_absent", `${scope} is a Conflict while execution has not run`);
      } else if (outcome?.outcome !== UNKNOWN_OUTCOME) {
        add("unknown_miscounted", `${scope} is not an Unknown outcome`);
      }
      if (outcome?.outcome === UNKNOWN_OUTCOME && outcome?.reason !== UNKNOWN_REASON) {
        add("absence_as_falsity", `${scope} Unknown is not reason-bound to ${UNKNOWN_REASON}`);
        if (outcome?.reason === LEGACY_REASON_MISREAD) {
          add("execution_read_as_adoption", `${scope} reads non-execution as non-adoption`);
        }
      }
      if (!INPUT_KINDS.includes(outcome?.input_kind)) {
        add("probe_coverage_incomplete", `${scope} carries an unknown input kind`);
      }

      // 8. anchors: missing or drifted inputs are visible, never a quiet Unknown.
      const anchor = outcome?.anchor;
      if (!anchor || typeof anchor !== "object" || !isRepoRelative(anchor.path)) {
        add("input_missing_silent", `${scope} anchor path is missing or not repository-relative`);
        continue;
      }
      if (anchor.anchor_kind === "corpus-span") {
        const extra = Object.keys(anchor).filter((key) => !CORPUS_ANCHOR_KEYS.has(key));
        if (extra.length > 0) {
          add("raw_text_leak", `${scope} corpus anchor carries keys outside the count-only set: ${extra.join(",")}`);
        }
        if (!anchor.path.startsWith(`${CORPUS_ROOT_RELATIVE}/`)) {
          add("input_missing_silent", `${scope} corpus anchor is outside the corpus root`);
        }
        if (!Number.isInteger(anchor.bytes) || anchor.bytes <= 0) {
          add("input_hash_mismatch", `${scope} byte pin is malformed`);
        }
        if (typeof anchor.sha256 !== "string" || !SHA_PATTERN.test(anchor.sha256)) {
          add("input_hash_mismatch", `${scope} sha256 pin is malformed`);
        }
        const span = anchor.span;
        if (
          !span ||
          !Number.isInteger(span.start) ||
          !Number.isInteger(span.end) ||
          span.start < 0 ||
          span.end <= span.start
        ) {
          add("input_hash_mismatch", `${scope} span is malformed`);
        }
        if (corpusLive) {
          const live = liveByFamily.get(outcome.family_id);
          if (!live) {
            add("input_missing_silent", `${scope} corpus input does not resolve while the corpus is present`);
          } else {
            if (live.path !== anchor.path) add("input_hash_mismatch", `${scope} corpus path drifted`);
            if (live.bytes !== anchor.bytes) add("input_hash_mismatch", `${scope} corpus byte count drifted`);
            if (live.sha256 !== anchor.sha256) add("input_hash_mismatch", `${scope} corpus sha256 drifted`);
            if (live.span?.start !== span?.start || live.span?.end !== span?.end) {
              add("input_hash_mismatch", `${scope} corpus span drifted`);
            }
          }
        }
        continue;
      }
      if (anchor.anchor_kind !== "tracked") {
        add("input_missing_silent", `${scope} anchor kind is not recognized`);
        continue;
      }
      if (typeof anchor.section !== "string" || anchor.section.trim() === "") {
        add("input_missing_silent", `${scope} tracked anchor carries no section`);
      }
      if (!exists(anchor.path)) {
        add("input_missing_silent", `${scope} input is absent: ${anchor.path}`);
        continue;
      }
      if (typeof anchor.sha256 !== "string" || !SHA_PATTERN.test(anchor.sha256)) {
        add("input_hash_mismatch", `${scope} sha256 pin is malformed`);
        continue;
      }
      const live = liveSha(anchor.path);
      if (typeof live === "string" && live !== anchor.sha256) {
        add("input_hash_mismatch", `${scope} sha256 pin differs from the live input`);
      }
    }
  }

  // 9. counts must agree with the outcomes, and no candidate or Conflict may appear.
  const derivedCounts = countsOf(outcomes ?? [], adoptedSet ?? []);
  const declaredCounts = report?.counts ?? {};
  for (const key of Object.keys(EXPECTED_COUNTS)) {
    if (declaredCounts[key] !== derivedCounts[key]) {
      add("unknown_miscounted", `counts.${key} is ${declaredCounts[key]}, derived ${derivedCounts[key]}`);
    }
    if (derivedCounts[key] !== EXPECTED_COUNTS[key]) {
      add("unknown_miscounted", `derived counts.${key} is ${derivedCounts[key]}, expected ${EXPECTED_COUNTS[key]}`);
    }
  }
  if (report?.verdict !== VERDICT) {
    add("unknown_miscounted", `verdict must be ${VERDICT}`);
  }

  // 10. no committed S03 artifact carries a candidate record or a Conflict verdict
  //     while execution has not run.
  const scan = scanCommittedS03(otherArtifacts, report);
  if (scan.candidate_records !== 0 || derivedCounts.candidates !== 0) {
    add("candidate_emitted_while_not_executed", "a candidate record exists while execution has not run");
  }
  if (scan.conflict_verdicts !== 0 || derivedCounts.conflicts !== 0) {
    add("conflict_reported_while_absent", "a Conflict verdict exists while execution has not run");
  }
  if (report?.scan?.candidate_records !== scan.candidate_records) {
    add("candidate_emitted_while_not_executed", "the scan summary disagrees with the live scan");
  }
  if (report?.scan?.conflict_verdicts !== scan.conflict_verdicts) {
    add("conflict_reported_while_absent", "the reported Conflict scan disagrees with the live scan");
  }
  if (report?.scan?.artifacts_scanned !== S03_ARTIFACT_PATHS.length) {
    add("probe_coverage_incomplete", "the scan must cover every committed S03 artifact");
  }

  // 11. consumed sources are byte-bound, and the S01 packet index agrees.
  const consumes = Array.isArray(report?.consumes) ? report.consumes : [];
  if (consumes.length < 5) add("probe_coverage_incomplete", "the consumed source list is incomplete");
  for (const entry of consumes) {
    if (!isRepoRelative(entry?.path)) {
      add("input_missing_silent", "a consumed source path is not repository-relative");
      continue;
    }
    const live = liveSha(entry.path);
    if (typeof live === "string" && live !== entry.sha256) {
      add("input_hash_mismatch", `consumed source drifted: ${entry.path}`);
    }
  }
  const packetIndex = env.packetIndex ?? null;
  if (packetIndex) {
    const declared = (packetIndex.artifacts ?? []).find((artifact) => artifact.path === S01_EXAMPLES_PATH);
    const liveS01 = liveSha(S01_EXAMPLES_PATH);
    if (!declared) {
      add("input_hash_mismatch", "the S01 packet index does not declare the examples artifact");
    } else if (typeof liveS01 === "string" && declared.sha256 !== liveS01) {
      add("input_hash_mismatch", "the S01 packet index disagrees with the live examples artifact");
    }
  }

  // 12. --check: rendered bytes must equal the committed artifact bytes.
  if (typeof env.committedText === "string" && env.committedText !== text) {
    add("report_not_byte_identical", "rendered bytes differ from the committed report");
  }

  return { ok: errors.length === 0, errors };
}

// A validation environment bound to the live tree. `liveCorpusAnchors` re-derives
// the corpus pins only when the licensed corpus resolves; the caller may supply
// its own anchors to keep a mutation independent of whether the corpus is mounted.
export function liveEnv(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const shaCache = new Map();
  return {
    reportText: options.reportText,
    committedText: options.committedText,
    corpusPresent: options.corpusPresent ?? false,
    liveCorpusAnchors: options.liveCorpusAnchors ?? [],
    s01Examples: options.s01Examples ?? null,
    packetIndex: options.packetIndex ?? null,
    startGate: options.startGate ?? null,
    s03Artifacts: options.s03Artifacts ?? {},
    section3Path: options.section3Path ?? SECTION3_PATH,
    exists: (relativePath) => existsSync(path.join(rootDir, relativePath)),
    sha256: (relativePath) => {
      if (shaCache.has(relativePath)) return shaCache.get(relativePath);
      let digest = null;
      try {
        digest = hashFile(rootDir, relativePath);
      } catch {
        digest = null;
      }
      shaCache.set(relativePath, digest);
      return digest;
    },
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function main(argv) {
  const mode = argv.includes("--check") ? "check" : argv.includes("--print") ? "print" : "write";
  const artifactPath = path.join(REPO_ROOT, ARTIFACT_RELATIVE_PATH);
  const committedText = existsSync(artifactPath) ? readFileSync(artifactPath, "utf8") : null;
  const rendered = renderReport({ rootDir: REPO_ROOT, corpusDir: process.env[CORPUS_DIR_ENV] });
  process.stderr.write(
    rendered.corpusPresent
      ? `M210_S03_CORPUS_PRESENT anchors=${rendered.liveAnchors.length}\n`
      : "M210_S03_CORPUS_ABSENT\n",
  );
  const startGate = rendered.inputs.startGate;
  const contract = rendered.inputs.contract;
  const env = liveEnv({
    rootDir: REPO_ROOT,
    reportText: rendered.text,
    committedText: mode === "check" ? committedText ?? undefined : undefined,
    corpusPresent: rendered.corpusPresent,
    liveCorpusAnchors: rendered.liveAnchors,
    s01Examples: rendered.inputs.s01Examples,
    packetIndex: rendered.inputs.packetIndex,
    startGate,
    s03Artifacts: { [START_GATE_PATH]: startGate, [CONTRACT_PATH]: contract },
  });
  const result = validateReport(rendered.report, env);
  if (!result.ok) {
    for (const error of result.errors) process.stderr.write(`${error.name}: ${error.detail}\n`);
    process.exitCode = 1;
    return;
  }
  if (mode === "print") {
    process.stdout.write(`${rendered.text}\n`);
    return;
  }
  if (mode === "check") {
    if (committedText === null) {
      process.stderr.write("report_not_byte_identical: the committed report is absent\n");
      process.exitCode = 1;
      return;
    }
    process.stdout.write("M210_S03_ABSTENTION_CHECK_OK\n");
    return;
  }
  writeFileSync(artifactPath, rendered.text);
  process.stdout.write("M210_S03_ABSTENTION_WRITTEN\n");
}

const invokedDirectly =
  typeof process.argv[1] === "string" && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    if (error instanceof BuildError) {
      process.stderr.write(`${error.code}: ${error.detail}\n`);
      process.exitCode = 1;
    } else {
      throw error;
    }
  }
}
