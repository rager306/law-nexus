#!/usr/bin/env node
// M210-3afp79 S03 T03 -- fail-closed abstention diagnostic over every source-bound input of S01.
//
// WHY THIS FILE EXISTS
// The milestone success criterion demands fail-closed diagnostics while the S03
// sketch forbids a runtime. A declaration ("the runtime abstains") is not
// evidence; an empirical diagnostic over the actual source-bound inputs is. This
// generator walks all eighteen inputs S01 committed -- eight dispute cards,
// eight corpus probes and two negative examples -- and records, per input, that
// no construct is adopted, that the outcome is Unknown and that the reason is
// `no_adopted_construct`. It mints no candidate, computes no semantics and
// writes no legal text.
//
// WHAT IS DERIVED, FROM WHERE
//   * admission verdict, adopted_construct_set, source_revision, guards
//                      <- prd/architecture/m210-s03-start-gate.json
//   * the outcome dictionary and the emission rule (read, never re-decided)
//                      <- prd/architecture/m210-s03-bounded-semantics-contract.json
//   * the eighteen inputs and their anchors (cards, corpus probes, negatives)
//                      <- prd/architecture/m210-s01-source-bound-examples.json
//   * the declared sha256 of that S01 artifact (binding cross-check)
//                      <- prd/architecture/m210-s01-packet-index.json
//   * the section 3 pin (guards.section3_pin)
//                      <- prd/temporal-legal-model.md
//
// THE ONE PREDICATE
//   resolveOutcome({ adoptedConstructSet }) returns Unknown with reason
//   `no_adopted_construct` while the adopted set is empty, and returns null when
//   a construct *is* adopted. That second branch is deliberately undecided: an
//   adopted state is outside this diagnostic and must fail closed with
//   `adopted_set_not_empty`, so no non-abstention outcome is ever fabricated
//   here. There is no evaluator, no truth table and no runtime object.
//
// WHY AN ABSENT INPUT CANNOT BECOME A QUIET Unknown
//   A missing anchor resolves to `input_missing_silent` and a drifted anchor to
//   `input_hash_mismatch`; both are visible fail-closed codes, so a broken input
//   can never be reported as an ordinary Unknown. Tracked anchors are always
//   verified against live bytes. Corpus anchors are verified against live bytes
//   whenever the licensed corpus resolves locally; when it does not, the probe
//   prints M210_S03_CORPUS_ABSENT on stderr and the committed pins carried over
//   from the tracked S01 artifact are used unchanged. The report bytes never
//   depend on the corpus being mounted, so --check stays byte-stable on a
//   machine without it.
//
// WHAT IS NEVER WRITTEN
//   * No legal text, no XML tag and no corpus content: a corpus anchor carries
//     only path, span, bytes and sha256, and the artifact is ASCII-only with a
//     closed marker set.
//   * No candidate record and no Conflict verdict: while the adopted set is
//     empty both are refused, and every committed S03 artifact is scanned for
//     candidate records and reported Conflict verdicts.
//   * No timestamp and no aggregate engine hash: the artifact is canonical
//     compact ASCII JSON with a fixed key order, so a whole-file byte compare in
//     --check mode is the determinism proof.
//
// NAMED FAIL-CLOSED CODES (each is exercised by the contract test)
//   probe_coverage_incomplete      the eighteen inputs are not all covered once, or a family is uncovered
//   adopted_set_not_empty          the adopted_construct_set is not empty, is_adoption is true, or the admission verdict drifted
//   candidate_emitted_while_absent a candidate record or candidate outcome exists while no construct is adopted
//   conflict_reported_while_absent a Conflict verdict or outcome is reported while no construct is adopted
//   unknown_miscounted             the counts block disagrees with the outcomes, or a non-Unknown outcome slipped in
//   absence_as_falsity             absence of evidence is read as falsity, or an Unknown outcome is not reason-bound
//   input_missing_silent           an input anchor is absent, not repository-relative, or outside the corpus root
//   input_hash_mismatch            an input anchor sha256 (or a consumed revision) differs from the live bytes
//   report_not_byte_identical      --check rendered bytes differ from the committed artifact
//   guard_not_zero                 a guard field is not the required empty or zero value
//   runtime_claim_present          the artifact claims a runtime, an evaluator or a crate surface
//   non_ascii_artifact             the artifact carries a non-ASCII byte
//   raw_text_leak                  the artifact carries an XML tag, a provider marker or a corpus anchor key outside the closed set
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
export const ADMISSION_VERDICT = "admission_absent";
export const UNKNOWN_REASON = "no_adopted_construct";
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
export const ADOPTION_CHECKPOINT_PATH = "prd/architecture/m210-s02-adoption-checkpoint.md";
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
  adopted_constructs: 0,
  candidates: 0,
  conflicts: 0,
  unknown: EXPECTED_COVERAGE.inputs,
};

export const EMITTABLE_CODES = [
  "absence_as_falsity",
  "adopted_set_not_empty",
  "candidate_emitted_while_absent",
  "conflict_reported_while_absent",
  "guard_not_zero",
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
  "It is not an adoption of normative semantics: adopted_construct_set is empty, is_adoption is false and every clause stays conditional.",
  "Every one of the eighteen source-bound inputs resolves to Unknown with reason no_adopted_construct; no candidate record exists and no Conflict verdict was observed.",
  "Unknown is not Conflict and neither is a negative finding: absence of a proven source span is never falsity, and no input is reported as false.",
  "A corpus anchor carries only path, span, bytes and sha256; no legal text is copied and a probe is a coverage label, not a reading.",
  "The adopted_construct_set is empty because the S02 admission checkpoint records not-adopted and the S03 start gate records admission_absent; a specification table is not an adoption.",
  "Section 3 of prd/temporal-legal-model.md is byte-identical to its recorded pin and the deferred terms stay deferred-undefined.",
  "F13 stays on hold: it is a separate decision with its own owning surfaces and is never derived from the bounded IR.",
  "Guards stay at their required zero: no crate is touched, no requirement is promoted, no Review Case event is written and no semantics is adopted.",
];

const REVISION_POLICY =
  "Re-derive before use: re-hash every consumed path, re-read the eighteen inputs from the S01 artifact, re-read the admission verdict from the S03 start gate and re-render; no timestamp and no aggregate engine hash are stored here.";

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

// The abstention predicate of this diagnostic. While no construct is adopted
// every input is Unknown for one stated reason. A non-empty adopted set is
// *outside* this diagnostic: it returns null and the validator fails closed with
// `adopted_set_not_empty`, so no non-abstention outcome is invented here.
export function resolveOutcome(adoptedConstructSet) {
  const adopted = Array.isArray(adoptedConstructSet) && adoptedConstructSet.length > 0;
  if (adopted) return null;
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

export function buildOutcomes(s01Examples, adoptedConstructSet) {
  const resolution = resolveOutcome(adoptedConstructSet);
  const outcomes = [];
  const push = (input) => {
    outcomes.push({
      input_id: input.input_id,
      input_kind: input.input_kind,
      family_id: input.family_id,
      anchor: input.anchor,
      adopted: false,
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
    [START_GATE_PATH, "admission verdict, adopted_construct_set, source_revision and the zero guards"],
    [CONTRACT_PATH, "the outcome dictionary and the emission rule read here, never re-decided"],
    [ADOPTION_CHECKPOINT_PATH, "admission source: records not-adopted, so the adopted set must stay empty"],
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

  if (typeof startGate?.admission_verdict !== "string") {
    fail("probe_coverage_incomplete", "the start gate carries no admission verdict");
  }
  const adoptedConstructSet = Array.isArray(startGate.adopted_construct_set) ? startGate.adopted_construct_set : [];
  if (!Array.isArray(startGate.adopted_construct_set)) {
    fail("adopted_set_not_empty", "the start gate carries no adopted_construct_set");
  }
  if (typeof startGate?.source_revision !== "string") {
    fail("input_hash_mismatch", "the start gate carries no source_revision");
  }
  if (!Array.isArray(contract?.outcome_dictionary?.outcomes)) {
    fail("probe_coverage_incomplete", "the S03 semantics contract carries no outcome dictionary");
  }

  const outcomes = buildOutcomes(s01Examples, adoptedConstructSet);
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
      adoption_source: ADOPTION_CHECKPOINT_PATH,
      adopted_variant: startGate.adopted_variant ?? null,
      adopted_construct_set: adoptedConstructSet,
      is_adoption: startGate.is_adoption ?? false,
      semantics_adopted: false,
      note: "The admission verdict is carried from the S03 start gate and the adopted_construct_set is empty, so every one of the eighteen inputs is Unknown and no candidate can exist.",
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
    add("guard_not_zero", "crates_touched must be an empty array");
  }
  if (guards.requirements_promoted !== 0) add("guard_not_zero", "requirements_promoted must be 0");
  if (guards.review_case_events_written !== 0) {
    add("guard_not_zero", "review_case_events_written must be 0");
  }
  if (guards.semantics_adopted !== false) add("guard_not_zero", "semantics_adopted must be false");
  if (typeof guards.section3_pin !== "string" || !SHA_PATTERN.test(guards.section3_pin)) {
    add("guard_not_zero", "section3_pin must be a well-formed sha256 pin");
  } else {
    const liveSection3 = liveSha(env.section3Path ?? SECTION3_PATH);
    if (typeof liveSection3 === "string" && liveSection3 !== guards.section3_pin) {
      add("guard_not_zero", "section3_pin differs from the live section 3 bytes");
    }
  }

  // 4. the adopted set must stay empty and the admission verdict must not drift.
  const adoption = report?.adoption_state ?? {};
  const adoptedSet = Array.isArray(adoption.adopted_construct_set) ? adoption.adopted_construct_set : null;
  if (adoptedSet === null) {
    add("adopted_set_not_empty", "adopted_construct_set must be an array");
  } else if (adoptedSet.length !== 0) {
    add("adopted_set_not_empty", "adopted_construct_set must be empty");
  }
  if (adoption.is_adoption !== false) add("adopted_set_not_empty", "is_adoption must be false");
  if (adoption.admission_verdict !== ADMISSION_VERDICT) {
    add("adopted_set_not_empty", `admission_verdict must be ${ADMISSION_VERDICT}`);
  }
  if (typeof startGate?.admission_verdict === "string" && adoption.admission_verdict !== startGate.admission_verdict) {
    add("adopted_set_not_empty", "admission_verdict drifted from the live start gate");
  }
  if (adoption.adopted_variant !== null) add("adopted_set_not_empty", "adopted_variant must be null");
  if (typeof startGate?.source_revision === "string" && report?.source_revision !== startGate.source_revision) {
    add("input_hash_mismatch", "source_revision drifted from the live start gate");
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

  // 7. every outcome is Unknown for the one stated reason, and is not falsity.
  if (outcomes) {
    for (const outcome of outcomes) {
      const scope = `input ${outcome?.input_id ?? "<unnamed>"}`;
      if (outcome?.adopted !== false) add("candidate_emitted_while_absent", `${scope} adopted must be false`);
      if (outcome?.absence_is_falsity === true) add("absence_as_falsity", `${scope} reads absence as falsity`);
      if (adoptedSet !== null && adoptedSet.length === 0) {
        if (outcome?.outcome === CANDIDATE_OUTCOME) {
          add("candidate_emitted_while_absent", `${scope} is a candidate while no construct is adopted`);
        } else if (outcome?.outcome === CONFLICT_OUTCOME) {
          add("conflict_reported_while_absent", `${scope} is a Conflict while no construct is adopted`);
        } else if (outcome?.outcome !== UNKNOWN_OUTCOME) {
          add("unknown_miscounted", `${scope} is not an Unknown outcome`);
        }
        if (outcome?.outcome === UNKNOWN_OUTCOME && outcome?.reason !== UNKNOWN_REASON) {
          add("absence_as_falsity", `${scope} Unknown is not reason-bound to ${UNKNOWN_REASON}`);
        }
        if (!INPUT_KINDS.includes(outcome?.input_kind)) {
          add("probe_coverage_incomplete", `${scope} carries an unknown input kind`);
        }
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

  // 10. no committed S03 artifact carries a candidate record or a Conflict verdict.
  const scan = scanCommittedS03(otherArtifacts, report);
  if (scan.candidate_records !== 0 || derivedCounts.candidates !== 0) {
    add("candidate_emitted_while_absent", "a candidate record exists while no construct is adopted");
  }
  if (scan.conflict_verdicts !== 0) {
    add("conflict_reported_while_absent", "a Conflict verdict exists while no construct is adopted");
  }
  if (report?.scan?.candidate_records !== scan.candidate_records) {
    add("candidate_emitted_while_absent", "the scan summary disagrees with the live scan");
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
