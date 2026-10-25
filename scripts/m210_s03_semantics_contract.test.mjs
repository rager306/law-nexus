// M210/S03 bounded semantics contract (T02).
//
// Offline and fail-closed. The subject is the semantics of the bounded semantic
// runtime after the owner established an authenticated adoption (S02 v2):
// adoption is *established* while execution is *not performed*, and the two are
// separate states. Adoption alone emits no candidate and makes `Conflict`
// unreachable, so in the committed state every outcome is `Unknown`.
//
// The contract is design-only: it mints no candidate record, composes no rule
// and edits no section 3 row. The abstract predicate `executed` lives only here,
// together with the specification truth table over it; it is a specification,
// not a product evaluator.
//
// The artifact is canonical compact ASCII JSON with a fixed key order and no
// timestamp, so `JSON.stringify(JSON.parse(text)) === text` and the contract
// never has to guess a formatting convention. Structural mutations round-trip
// through JSON so every mutation stays parseable on purpose.
//
// Every documented fail-closed code is provable against a mutated copy of the
// live artifact, so the suite cannot assert a code it would never emit.
//
// Subprocesses are limited to one `git ls-files` (tracked-file proof). No
// cargo, no network, no `.gsd` / ignored / absolute path is read as evidence.
//
// Run: node --test scripts/m210_s03_semantics_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/architecture/m210-s03-bounded-semantics-contract.json";
const COMPANION = "prd/architecture/m210-s03-bounded-semantics-contract.md";
const REGISTER = "prd/architecture/m210-s01-normative-family-register.json";
const START_GATE = "prd/architecture/m210-s03-start-gate.json";
const ADOPTION_V2 = "prd/architecture/m210-s02-adoption-checkpoint-v2.md";
const ALTERNATIVES = "prd/architecture/m210-s01-ir-alternatives.json";

const SCHEMA = "law-nexus/m210-s03-bounded-semantics-contract/v1";
const KIND = "m210-s03-bounded-semantics-contract";
const MILESTONE = "M210-3afp79";
const SLICE = "S03";
const TASK = "T02";
const LIFECYCLE = ["proposed"];

// The closed RC28-F18 family set (S01 register), ordered as in the plan. The
// contract references it and must never redeclare divergent identities.
const CLOSED_FAMILIES = [
  "obligation",
  "permission",
  "prohibition",
  "definition",
  "competence",
  "condition",
  "exception",
  "temporal_qualification",
];

// The adopted candidate-layer construct set (mirrors the live S03 start gate).
const ADOPTED_CONSTRUCT_SET = [
  "candidate_emission",
  "source_anchors",
  "family_classification_hypotheses",
  "unknown_verdict",
  "conflict_verdict",
  "provenance_links",
];

// The closed S01 evidence-class dictionary.
const EVIDENCE_CLASSES = ["inert-artifact", "source-bound-span", "runtime-absent"];

// The closed S01 vocabulary-status dictionary.
const VOCABULARY_STATUSES = ["bounded", "deferred-undefined", "no_owning_row", "proposed"];

// The closed section 3 deferred-undefined vocabulary the contract must leave alone.
const SECTION3_DEFERRED_TERMS = [
  "NormRule",
  "Condition",
  "LegalEffect",
  "Exception",
  "Defeater",
  "ApplicabilitySelector",
];

// The exact outcome set.
const OUTCOME_SET = ["candidate_emitted", "Unknown", "Conflict"];

// Out-of-scope surfaces the contract must not claim.
const OUT_OF_SCOPE_SURFACES = ["Applicable", "RuVector", "TEI", "F13 operation grammar"];

// Every declared fail-closed code, one coverage entry each.
const EMITTABLE_CODES = [
  "absence_as_falsity",
  "adoption_read_as_execution",
  "anchor_missing",
  "applicability_evaluated",
  "candidate_without_adopted_construct",
  "composed_rule_emitted",
  "conflict_without_adopted_construct",
  "evidence_class_unknown",
  "execution_read_as_adoption",
  "f13_scope_borrowed",
  "facet_default_applied",
  "non_ascii_artifact",
  "normrule_minted",
  "outcome_indistinct",
  "outcome_set_incomplete",
  "raw_text_leak",
  "runtime_claim_present",
  "section3_promoted",
  "unknown_conflict_collapsed",
];

// Paths that can never be evidence: ignored overlays, absolute paths, traversal.
const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const TIMESTAMP_MARKERS = [/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/, /\b1[6-9]\d{11}\b/];

// Fields the committed artifact must never carry: the abstract predicate and its
// truth table live only in this test, never in a committed artifact.
const FORBIDDEN_ARTIFACT_KEYS = ["decision_table", "truth_table", "executor", "evaluator", "minted_candidates"];

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

const TRACKED = new Set(
  execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
    .split("\n")
    .filter((line) => line.length > 0),
);

function assertRepoRelative(relativePath) {
  assert.ok(typeof relativePath === "string" && relativePath.length > 0, "path must be a non-empty string");
  assert.ok(!path.isAbsolute(relativePath), `path must be repository-relative: ${relativePath}`);
  assert.ok(!relativePath.includes(".."), `path must not traverse: ${relativePath}`);
  assert.ok(
    !FORBIDDEN_PREFIXES.some((prefix) => relativePath.startsWith(prefix)),
    `path must not be an ignored overlay: ${relativePath}`,
  );
}

function readRepo(relativePath) {
  assertRepoRelative(relativePath);
  return readFileSync(path.join(root, relativePath), "utf8");
}

function sha256Repo(relativePath) {
  assertRepoRelative(relativePath);
  const bytes = readFileSync(path.join(root, relativePath));
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

function sortJoin(values) {
  return [...values].sort().join("\n");
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function normalizePredicate(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

const LIVE_DOC = readRepo(ARTIFACT);
const LIVE_COMPANION = readRepo(COMPANION);
const LIVE_REGISTER = JSON.parse(readRepo(REGISTER));
const LIVE_GATE = JSON.parse(readRepo(START_GATE));

function clone() {
  return JSON.parse(LIVE_DOC);
}

function codes(errors) {
  return errors.map((error) => error.name);
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateContract(rawText) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });

  // 1. text hygiene.
  if ([...rawText].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the contract carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (rawText.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (rawText.includes(marker)) add("runtime_claim_present", `runtime marker ${marker}`);
  }

  let contract;
  try {
    contract = JSON.parse(rawText);
  } catch (error) {
    add("outcome_set_incomplete", `unparseable contract: ${error.message}`);
    return errors;
  }

  // 2. outcome set is exactly the three declared outcomes, no duplicates.
  const dictionary = contract?.outcome_dictionary ?? {};
  const outcomes = Array.isArray(dictionary.outcomes) ? dictionary.outcomes : [];
  const ids = outcomes.map((outcome) => outcome.outcome_id);
  if (
    sortJoin(ids) !== sortJoin(OUTCOME_SET) ||
    new Set(ids).size !== ids.length ||
    dictionary.outcome_count !== 3
  ) {
    add("outcome_set_incomplete", `outcome ids ${JSON.stringify(ids)} count ${dictionary.outcome_count}`);
  }
  const byId = new Map(outcomes.map((outcome) => [outcome.outcome_id, outcome]));
  const candidate = byId.get("candidate_emitted");
  const unknown = byId.get("Unknown");
  const conflict = byId.get("Conflict");

  // 3. the outcomes must stay distinguishable, never collapsed.
  const predicateGroups = [
    ["candidate_emitted", candidate],
    ["Unknown", unknown],
    ["Conflict", conflict],
  ].filter(([, outcome]) => outcome);
  for (let i = 0; i < predicateGroups.length; i += 1) {
    for (let j = i + 1; j < predicateGroups.length; j += 1) {
      const [, left] = predicateGroups[i];
      const [, right] = predicateGroups[j];
      if (normalizePredicate(left?.predicate) === normalizePredicate(right?.predicate)) {
        add("outcome_indistinct", `two outcomes share one predicate: ${predicateGroups[i][0]}/${predicateGroups[j][0]}`);
      }
    }
  }
  if (unknown && conflict && unknown.outcome_code === conflict.outcome_code) {
    add("unknown_conflict_collapsed", "Unknown and Conflict share one outcome code");
  }

  // 4. a candidate requires an adopted construct (the adopted_construct_ref).
  const envelope = contract?.candidate_envelope ?? {};
  if (candidate && candidate.requires_adopted_construct !== true) {
    add("candidate_without_adopted_construct", "candidate_emitted does not require an adopted construct");
  }
  const emission = contract?.emission_rule ?? {};
  if (emission.candidate_requires_adopted_construct !== true) {
    add("candidate_without_adopted_construct", "the emission rule does not gate candidates on adoption");
  }
  if (envelope.adopted_construct_ref_required !== true) {
    add("candidate_without_adopted_construct", "the envelope does not require an adopted_construct_ref");
  }

  // 5. a Conflict requires an adopted construct.
  if (conflict && conflict.requires_adopted_construct !== true) {
    add("conflict_without_adopted_construct", "Conflict does not require an adopted construct");
  }
  if (emission.conflict_requires_adopted_construct !== true) {
    add("conflict_without_adopted_construct", "the emission rule does not gate Conflict on adoption");
  }

  // 6. adoption is separated from execution: adoption alone emits nothing and
  //    Conflict is unreachable without execution.
  const adoption = contract?.adoption_state ?? {};
  const execution = contract?.execution_state ?? {};
  if (adoption.executed === true) {
    add("adoption_read_as_execution", "adoption_state carries an execution flag");
  }
  if (emission.candidate_requires_execution !== true) {
    add("adoption_read_as_execution", "the emission rule does not require execution for a candidate");
  }
  if (emission.conflict_requires_execution !== true) {
    add("adoption_read_as_execution", "the emission rule does not require execution for a Conflict");
  }
  if (emission.conflict_unreachable_without_execution !== true) {
    add("adoption_read_as_execution", "the emission rule does not declare Conflict unreachable without execution");
  }
  if (emission.adoption_alone_emits_zero_candidates !== true) {
    add("adoption_read_as_execution", "the emission rule does not declare adoption alone emission-free");
  }
  if (emission.adopted_but_not_executed_all_outcomes_unknown !== true) {
    add("adoption_read_as_execution", "the emission rule does not declare adopted-but-not-executed as Unknown");
  }
  if (emission.adoption_is_not_execution !== true) {
    add("adoption_read_as_execution", "the emission rule does not distinguish adoption from execution");
  }
  if (adoption.execution_separated !== true) {
    add("adoption_read_as_execution", "adoption_state does not declare execution_separated");
  }
  if (
    execution.executed !== true &&
    (Number(execution.candidates_emitted) > 0 || Number(execution.conflicts) > 0)
  ) {
    add("adoption_read_as_execution", "candidates or conflicts exist while execution_state.executed is false");
  }
  if (envelope.minted === true) {
    add("adoption_read_as_execution", "a candidate is minted while execution_state.executed is false");
  }
  if (Array.isArray(contract?.candidates) && contract.candidates.length !== 0) {
    add("adoption_read_as_execution", "committed candidate records exist");
  }

  // 7. execution is not adoption: the adoption is grounded in the authenticated
  //    grant, never in an execution result.
  if (adoption.admission_verdict !== "admission_granted") {
    add("execution_read_as_adoption", "the admission verdict is not admission_granted");
  }
  if (adoption.adoption_established !== true) {
    add("execution_read_as_adoption", "the adoption is not declared established");
  }
  if (adoption.adopted_variant !== "C") {
    add("execution_read_as_adoption", "the adopted variant is not the granted variant C");
  }
  if (!isNonEmptyString(adoption.authenticated_via) || !String(adoption.authenticated_via).toLowerCase().includes("subjective-uat")) {
    add("execution_read_as_adoption", "the adoption is not bound to an authenticated subjective-UAT reference");
  }
  if (adoption.spec_table_is_not_adoption !== true) {
    add("execution_read_as_adoption", "the outcome table is read as the adoption instrument");
  }
  if (execution.adoption_established === true) {
    add("execution_read_as_adoption", "execution_state carries an adoption flag");
  }
  if (emission.execution_is_not_adoption !== true) {
    add("execution_read_as_adoption", "the emission rule does not distinguish execution from adoption");
  }

  // 8. absence of evidence is never falsity.
  if (emission.absence_is_not_falsity !== true) {
    add("absence_as_falsity", "the emission rule does not declare absence as non-falsity");
  }
  if (unknown && unknown.absence_is_falsity === true) {
    add("absence_as_falsity", "Unknown declares absence as falsity");
  }

  // 9. the anchor contract demands a repository-relative path and a sha256.
  const anchor = envelope.anchor_contract ?? {};
  if (anchor.requires_repository_relative_path !== true || anchor.requires_sha256 !== true) {
    add("anchor_missing", "the anchor contract does not require a repository-relative path and a sha256");
  }

  // 10. the evidence class stays inside the closed dictionary.
  if (!Array.isArray(envelope.evidence_class_domain) || sortJoin(envelope.evidence_class_domain) !== sortJoin(EVIDENCE_CLASSES)) {
    add("evidence_class_unknown", "the candidate evidence-class domain is not the closed dictionary");
  }

  // 11. boundaries: no composition, no precedence, no facet default, no applicability.
  const boundaries = contract?.boundaries ?? {};
  if (boundaries.composed_rule_emitted === true || boundaries.composition_performed === true) {
    add("composed_rule_emitted", "a composed rule is emitted");
  }
  if (boundaries.classification_is_not_composition !== true) {
    add("composed_rule_emitted", "classification is not declared distinct from composition");
  }
  if (boundaries.precedence_resolved === true) {
    add("composed_rule_emitted", "precedence is resolved");
  }
  if (boundaries.facet_defaults_applied === true) {
    add("facet_default_applied", "a facet default is applied");
  }
  if (boundaries.applicability_evaluated === true) {
    add("applicability_evaluated", "applicability is evaluated");
  }
  if (boundaries.normrule_minted === true) {
    add("normrule_minted", "a NormRule is minted");
  }
  if (boundaries.section3_promoted === true) {
    add("section3_promoted", "section 3 is promoted");
  }
  if (boundaries.f13_scope_borrowed === true) {
    add("f13_scope_borrowed", "the F13 scope is borrowed");
  }

  return errors;
}

// ---------------------------------------------------------------------------
// specification truth table over the abstract predicates `adopted` / `executed`
// ---------------------------------------------------------------------------

// This is a specification, not a product evaluator: it exists only in this test
// to prove that the declared emission rule is falsifiable. Adoption alone is not
// execution, so an adopted-but-not-executed construct yields Unknown; Conflict
// requires execution and two divergent anchors; a single proven span cannot
// diverge from itself, so `anchorsAgree: false` is only meaningful with
// `provenSpans >= 2`.
function resolveOutcome({ adopted, executed, provenSpans, anchorsAgree }) {
  if (!adopted) return "Unknown";
  if (!executed) return "Unknown";
  if (provenSpans === 0) return "Unknown";
  if (!anchorsAgree && provenSpans >= 2) return "Conflict";
  return "candidate_emitted";
}

const TRUTH_TABLE = [
  {
    name: "not adopted and not executed yields Unknown",
    input: { adopted: false, executed: false, provenSpans: 0, anchorsAgree: false },
    expected: "Unknown",
  },
  {
    name: "execution without adoption still yields Unknown",
    input: { adopted: false, executed: true, provenSpans: 2, anchorsAgree: false },
    expected: "Unknown",
  },
  {
    name: "adopted but not executed yields Unknown, even with divergent anchors",
    input: { adopted: true, executed: false, provenSpans: 4, anchorsAgree: false },
    expected: "Unknown",
  },
  {
    name: "adopted but not executed yields Unknown, never a candidate",
    input: { adopted: true, executed: false, provenSpans: 1, anchorsAgree: true },
    expected: "Unknown",
  },
  {
    name: "executed adoption with no proven span yields Unknown",
    input: { adopted: true, executed: true, provenSpans: 0, anchorsAgree: false },
    expected: "Unknown",
  },
  {
    name: "executed adopted construct with two divergent anchors yields Conflict",
    input: { adopted: true, executed: true, provenSpans: 2, anchorsAgree: false },
    expected: "Conflict",
  },
  {
    name: "executed adopted construct with one agreeing anchor yields a candidate",
    input: { adopted: true, executed: true, provenSpans: 1, anchorsAgree: true },
    expected: "candidate_emitted",
  },
  {
    name: "executed adopted construct with two agreeing anchors yields a candidate",
    input: { adopted: true, executed: true, provenSpans: 2, anchorsAgree: true },
    expected: "candidate_emitted",
  },
];

// ---------------------------------------------------------------------------
// positive: identity, canonical form and hygiene
// ---------------------------------------------------------------------------

test("artifact is canonical compact ASCII JSON with a fixed identity", () => {
  assert.equal(JSON.stringify(JSON.parse(LIVE_DOC)), LIVE_DOC, "the artifact must be canonical compact JSON");
  const contract = clone();
  assert.equal(contract.schema, SCHEMA);
  assert.equal(contract.kind, KIND);
  assert.equal(contract.milestone, MILESTONE);
  assert.equal(contract.slice, SLICE);
  assert.equal(contract.task, TASK);
  assert.deepEqual(contract.lifecycle, LIFECYCLE);
  assert.equal(contract.authoritative, false);
  assert.equal(contract.ascii_only, true);
  assert.equal(contract.design_only, true);
  assert.equal(contract.vocabulary_status, "deferred-undefined");
  assert.ok(isNonEmptyString(contract.revision_policy), "revision_policy must be present");
  assert.ok(
    !TIMESTAMP_MARKERS.some((marker) => marker.test(LIVE_DOC)),
    "the artifact must not carry a timestamp or an epoch",
  );
  for (const forbidden of FORBIDDEN_ARTIFACT_KEYS) {
    assert.ok(!(forbidden in contract), `the abstract predicate must not be committed: ${forbidden}`);
  }
  assert.deepEqual(validateContract(LIVE_DOC), [], "the committed artifact must be clean");
});

test("adoption_state carries the established grant and keeps execution separate", () => {
  const { adoption_state: adoption, execution_state: execution } = clone();
  assert.equal(adoption.admission_verdict, "admission_granted");
  assert.equal(adoption.adoption_source, ADOPTION_V2);
  assert.equal(adoption.adopted_variant, "C");
  assert.equal(adoption.adopted_variant_label, "abstention_first_candidates_only");
  assert.deepEqual(adoption.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(adoption.adoption_established, true);
  assert.equal(adoption.normative_semantics_adopted, false);
  assert.equal(adoption.section3_terms, "deferred-undefined");
  assert.equal(adoption.execution_separated, true);
  assert.equal(adoption.spec_table_is_not_adoption, true);
  assert.match(String(adoption.authenticated_via), /subjective-UAT/i);
  assert.ok(isNonEmptyString(adoption.owner_admission_ref));
  assert.equal(adoption.executed, undefined, "adoption_state must not carry an execution flag");
  assert.ok(isNonEmptyString(adoption.note));

  assert.equal(execution.executed, false);
  assert.equal(execution.candidates_emitted, 0);
  assert.equal(execution.conflicts, 0);
  assert.equal(execution.adoption_established, undefined, "execution_state must not carry an adoption flag");
  assert.ok(isNonEmptyString(execution.note));
});

test("the contract mirrors the live S03 start gate adoption and execution state", () => {
  const contract = clone();
  const gateAdoption = LIVE_GATE.adoption_state;
  const gateExecution = LIVE_GATE.execution_state;
  assert.equal(contract.adoption_state.admission_verdict, gateAdoption.admission_verdict);
  assert.equal(contract.adoption_state.adopted_variant, gateAdoption.adopted_variant);
  assert.equal(contract.adoption_state.adopted_variant_label, gateAdoption.adopted_variant_label);
  assert.deepEqual(contract.adoption_state.adopted_construct_set, gateAdoption.adopted_construct_set);
  assert.equal(contract.adoption_state.adoption_established, gateAdoption.adoption_established);
  assert.equal(contract.adoption_state.authenticated_via, gateAdoption.authenticated_via);
  assert.equal(contract.adoption_state.owner_admission_ref, gateAdoption.owner_admission_ref);
  assert.equal(contract.execution_state.executed, gateExecution.executed);
  assert.equal(contract.execution_state.candidates_emitted, gateExecution.candidates_emitted);
  assert.equal(contract.execution_state.conflicts, gateExecution.conflicts);
  // The committed state is adoption-established and execution-absent.
  assert.equal(gateAdoption.admission_verdict, "admission_granted");
  assert.equal(gateExecution.executed, false);
});

// ---------------------------------------------------------------------------
// positive: dictionaries are bound to the live S01 register
// ---------------------------------------------------------------------------

test("construct dictionary is bound to the live S01 register and redeclares no family", () => {
  const { construct_dictionary: dictionary } = clone();
  const liveRegisterSha = sha256Repo(REGISTER);
  assert.equal(dictionary.source.path, REGISTER);
  assert.equal(dictionary.source.sha256, liveRegisterSha, "the register binding must match the live bytes");
  assert.equal(dictionary.families_redeclared, false);
  assert.deepEqual(dictionary.closed_family_ids, CLOSED_FAMILIES);
  assert.equal(dictionary.family_count, CLOSED_FAMILIES.length);
  assert.deepEqual(dictionary.vocabulary_status_dictionary, VOCABULARY_STATUSES);
  assert.deepEqual(dictionary.promoted_statuses, []);
  assert.equal(dictionary.adoption_does_not_promote_families, true);

  const liveFamilies = Object.fromEntries(
    LIVE_REGISTER.families.map((family) => [family.family_id, family.vocabulary_status]),
  );
  assert.deepEqual(
    dictionary.family_vocabulary_status,
    liveFamilies,
    "the copied family vocabulary status must match the live register",
  );
  assert.deepEqual(dictionary.evidence_class_domain, LIVE_REGISTER.evidence_class_dictionary);
  assert.deepEqual(dictionary.vocabulary_status_dictionary, LIVE_REGISTER.vocabulary_status_dictionary);
});

test("consumes entries are tracked and byte-bound to their live sources", () => {
  const { consumes } = clone();
  assert.ok(Array.isArray(consumes) && consumes.length >= 4, "at least four consumed sources");
  const paths = new Set(consumes.map((entry) => entry.path));
  for (const required of [START_GATE, ADOPTION_V2, REGISTER, ALTERNATIVES]) {
    assert.ok(paths.has(required), `the consumed set must include ${required}`);
  }
  for (const entry of consumes) {
    assertRepoRelative(entry.path);
    assert.ok(TRACKED.has(entry.path), `consumed source must be tracked: ${entry.path}`);
    assert.equal(entry.sha256, sha256Repo(entry.path), `the binding must match the live bytes: ${entry.path}`);
    assert.ok(isNonEmptyString(entry.role), `the consumed source needs a role: ${entry.path}`);
  }
});

// ---------------------------------------------------------------------------
// positive: envelope and outcome dictionary
// ---------------------------------------------------------------------------

test("candidate envelope is design-only, anchored and never minted", () => {
  const { candidate_envelope: envelope } = clone();
  assert.equal(envelope.design_only, true);
  assert.equal(envelope.minted, false);
  assert.equal(envelope.minted_field_count, 0);
  assert.equal(envelope.record_kind, "candidate");
  const names = envelope.fields.map((field) => field.name);
  for (const required of [
    "candidate_id",
    "family_id",
    "source_anchor",
    "evidence_class",
    "verdict",
    "adopted_construct_ref",
  ]) {
    assert.ok(names.includes(required), `the envelope must carry ${required}`);
    assert.equal(envelope.fields.find((field) => field.name === required).required, true);
  }
  assert.equal(envelope.adopted_construct_ref_field, "adopted_construct_ref");
  assert.equal(envelope.adopted_construct_ref_required, true);
  assert.equal(envelope.anchor_contract.requires_repository_relative_path, true);
  assert.equal(envelope.anchor_contract.requires_sha256, true);
  assert.deepEqual(envelope.evidence_class_domain, EVIDENCE_CLASSES);
  assert.equal(envelope.verdict.emission_verdict, "candidate_emitted");
  assert.deepEqual(envelope.verdict.non_emission_verdicts, ["Unknown", "Conflict"]);
});

test("outcome dictionary declares exactly three distinct outcomes", () => {
  const { outcome_dictionary: dictionary } = clone();
  const ids = dictionary.outcomes.map((outcome) => outcome.outcome_id);
  assert.equal(dictionary.outcome_count, 3);
  assert.deepEqual([...ids].sort(), [...OUTCOME_SET].sort());
  assert.equal(new Set(ids).size, 3);
  assert.deepEqual(validateContract(LIVE_DOC), []);

  const predicates = dictionary.outcomes.map((outcome) => normalizePredicate(outcome.predicate));
  assert.equal(new Set(predicates).size, 3, "every outcome predicate must be distinct");
  const codesByOutcome = dictionary.outcomes.map((outcome) => outcome.outcome_code);
  assert.equal(new Set(codesByOutcome).size, 3, "every outcome code must be distinct");

  const unknown = dictionary.outcomes.find((outcome) => outcome.outcome_id === "Unknown");
  const conflict = dictionary.outcomes.find((outcome) => outcome.outcome_id === "Conflict");
  const candidate = dictionary.outcomes.find((outcome) => outcome.outcome_id === "candidate_emitted");
  assert.equal(candidate.requires_adopted_construct, true);
  assert.equal(candidate.requires_execution, true);
  assert.equal(unknown.requires_adopted_construct, false);
  assert.equal(unknown.requires_execution, false);
  assert.equal(conflict.requires_adopted_construct, true);
  assert.equal(conflict.requires_execution, true);
  for (const outcome of dictionary.outcomes) {
    assert.equal(outcome.absence_is_falsity, false);
  }
});

test("emission rule separates adoption from execution", () => {
  const { emission_rule: emission } = clone();
  assert.equal(emission.candidate_requires_adopted_construct, true);
  assert.equal(emission.candidate_requires_execution, true);
  assert.equal(emission.candidate_requires_proven_span, true);
  assert.equal(emission.candidate_requires_agreeing_anchors, true);
  assert.equal(emission.conflict_requires_adopted_construct, true);
  assert.equal(emission.conflict_requires_execution, true);
  assert.equal(emission.conflict_requires_at_least_two_divergent_anchors, true);
  assert.equal(emission.conflict_unreachable_without_execution, true);
  assert.equal(emission.adoption_alone_emits_zero_candidates, true);
  assert.equal(emission.adopted_but_not_executed_all_outcomes_unknown, true);
  assert.equal(emission.adoption_is_not_execution, true);
  assert.equal(emission.execution_is_not_adoption, true);
  assert.equal(emission.absence_is_not_falsity, true);
});

// ---------------------------------------------------------------------------
// positive: boundaries, non-claims and the declared code set
// ---------------------------------------------------------------------------

test("boundaries keep composition, precedence, facet defaults and applicability out of scope", () => {
  const { boundaries } = clone();
  assert.equal(boundaries.classification_is_not_composition, true);
  assert.equal(boundaries.composition_performed, false);
  assert.equal(boundaries.composed_rule_emitted, false);
  assert.equal(boundaries.precedence_resolved, false);
  assert.equal(boundaries.facet_defaults_applied, false);
  assert.equal(boundaries.applicability_evaluated, false);
  assert.equal(boundaries.normrule_minted, false);
  assert.equal(boundaries.section3_promoted, false);
  assert.equal(boundaries.f13_scope_borrowed, false);
  assert.deepEqual(boundaries.deferred_terms, SECTION3_DEFERRED_TERMS);
  assert.equal(boundaries.deferred_terms_status, "deferred-undefined");
  const claimed = boundaries.out_of_scope_surfaces.map((surface) => surface.name);
  assert.deepEqual([...claimed].sort(), [...OUT_OF_SCOPE_SURFACES].sort());
  for (const surface of boundaries.out_of_scope_surfaces) {
    assert.equal(surface.claimed, false, `the out-of-scope surface must stay unclaimed: ${surface.name}`);
  }
});

test("non-claims and the declared fail-closed code set are complete", () => {
  const contract = clone();
  assert.ok(Array.isArray(contract.non_claims) && contract.non_claims.length >= 8);
  const joined = contract.non_claims.join("\n").toLowerCase();
  for (const fragment of [
    "adoption is not execution",
    "execution is not adoption",
    "absence of a proven source span is never falsity",
    "classification is not composition",
    "deferred-undefined",
    "f13",
  ]) {
    assert.ok(joined.includes(fragment), `non_claims must state: ${fragment}`);
  }

  assert.deepEqual(contract.fail_closed_codes, EMITTABLE_CODES, "the declared code set must be exactly the emittable set");
  assert.equal(new Set(contract.fail_closed_codes).size, contract.fail_closed_codes.length);
  assert.ok(contract.fail_closed_codes.every((code) => code === code.toLowerCase()));
});

// ---------------------------------------------------------------------------
// positive: the companion documents the granted contour
// ---------------------------------------------------------------------------

test("the markdown companion exists and documents the granted contour", () => {
  assert.ok(existsSync(path.join(root, COMPANION)), "the companion must exist next to the artifact");
  assert.ok([...LIVE_COMPANION].every((character) => character.charCodeAt(0) <= 0x7f), "the companion must be ASCII");
  const lowered = LIVE_COMPANION.toLowerCase();
  for (const fragment of [
    "admission: granted",
    "adoption_established",
    "adopted_construct_set",
    "adoption is not execution",
    "execution is not adoption",
    "collapsing them into one code",
    "conflict is unreachable without execution",
    "unknown",
    "conflict",
    "proof ceiling",
    "deferred-undefined",
    "f13",
    "fail-closed",
    "adoption_read_as_execution",
    "execution_read_as_adoption",
  ]) {
    assert.ok(lowered.includes(fragment.toLowerCase()), `the companion must state: ${fragment}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!LIVE_COMPANION.includes(marker), `the companion must not claim a runtime marker: ${marker}`);
  }
});

// ---------------------------------------------------------------------------
// positive: the specification truth table
// ---------------------------------------------------------------------------

test("specification truth table separates adoption from execution and makes Conflict unreachable without it", () => {
  for (const row of TRUTH_TABLE) {
    assert.equal(resolveOutcome(row.input), row.expected, row.name);
  }

  // Exhaustive: without adoption or without execution the only reachable outcome
  // is Unknown; every Conflict and every candidate requires both.
  for (const adopted of [false, true]) {
    for (const executed of [false, true]) {
      for (const provenSpans of [0, 1, 2]) {
        for (const anchorsAgree of [false, true]) {
          const input = { adopted, executed, provenSpans, anchorsAgree };
          const outcome = resolveOutcome(input);
          assert.ok(OUTCOME_SET.includes(outcome), `the outcome must be in the closed set: ${outcome}`);
          if (!adopted || !executed) {
            assert.equal(
              outcome,
              "Unknown",
              `no candidate or Conflict without adoption and execution: ${JSON.stringify(input)}`,
            );
          }
          if (outcome === "Conflict") {
            assert.ok(
              adopted && executed && provenSpans >= 2 && !anchorsAgree,
              `Conflict requires adoption, execution and divergence: ${JSON.stringify(input)}`,
            );
          }
          if (outcome === "candidate_emitted") {
            assert.ok(
              adopted && executed && provenSpans >= 1 && !(provenSpans >= 2 && !anchorsAgree),
              `a candidate requires adoption, execution, a proven span and no divergence: ${JSON.stringify(input)}`,
            );
          }
        }
      }
    }
  }

  // Conflict is unreachable without execution, even with divergent anchors.
  assert.equal(
    resolveOutcome({ adopted: true, executed: false, provenSpans: 3, anchorsAgree: false }),
    "Unknown",
    "Conflict must be unreachable without execution",
  );

  // The committed state is adoption-established and execution-absent: every
  // outcome is Unknown, so no candidate exists and Conflict is unreachable.
  const committedOutcomes = new Set();
  for (const provenSpans of [0, 1, 2]) {
    for (const anchorsAgree of [false, true]) {
      committedOutcomes.add(resolveOutcome({ adopted: true, executed: false, provenSpans, anchorsAgree }));
    }
  }
  assert.deepEqual(
    [...committedOutcomes],
    ["Unknown"],
    "with an established adoption and no execution the only outcome is Unknown",
  );
});

// ---------------------------------------------------------------------------
// negative: each declared code is empirically exercised
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "outcome_set_incomplete",
    mutate: (artifact) => {
      artifact.outcome_dictionary.outcomes = artifact.outcome_dictionary.outcomes.filter(
        (outcome) => outcome.outcome_id !== "Conflict",
      );
    },
  },
  {
    code: "outcome_indistinct",
    mutate: (artifact) => {
      const unknown = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Unknown");
      const conflict = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Conflict");
      unknown.predicate = conflict.predicate;
    },
  },
  {
    code: "unknown_conflict_collapsed",
    mutate: (artifact) => {
      const unknown = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Unknown");
      const conflict = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Conflict");
      unknown.outcome_code = conflict.outcome_code;
    },
  },
  {
    code: "candidate_without_adopted_construct",
    mutate: (artifact) => {
      const candidate = artifact.outcome_dictionary.outcomes.find(
        (outcome) => outcome.outcome_id === "candidate_emitted",
      );
      candidate.requires_adopted_construct = false;
    },
  },
  {
    code: "conflict_without_adopted_construct",
    mutate: (artifact) => {
      const conflict = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Conflict");
      conflict.requires_adopted_construct = false;
    },
  },
  {
    code: "adoption_read_as_execution",
    mutate: (artifact) => {
      artifact.emission_rule.candidate_requires_execution = false;
    },
  },
  {
    code: "execution_read_as_adoption",
    mutate: (artifact) => {
      artifact.emission_rule.execution_is_not_adoption = false;
    },
  },
  {
    code: "anchor_missing",
    mutate: (artifact) => {
      artifact.candidate_envelope.anchor_contract.requires_sha256 = false;
    },
  },
  {
    code: "evidence_class_unknown",
    mutate: (artifact) => {
      artifact.candidate_envelope.evidence_class_domain = [...artifact.candidate_envelope.evidence_class_domain, "raw-text"];
    },
  },
  {
    code: "composed_rule_emitted",
    mutate: (artifact) => {
      artifact.boundaries.composed_rule_emitted = true;
    },
  },
  {
    code: "facet_default_applied",
    mutate: (artifact) => {
      artifact.boundaries.facet_defaults_applied = true;
    },
  },
  {
    code: "applicability_evaluated",
    mutate: (artifact) => {
      artifact.boundaries.applicability_evaluated = true;
    },
  },
  {
    code: "normrule_minted",
    mutate: (artifact) => {
      artifact.boundaries.normrule_minted = true;
    },
  },
  {
    code: "section3_promoted",
    mutate: (artifact) => {
      artifact.boundaries.section3_promoted = true;
    },
  },
  {
    code: "absence_as_falsity",
    mutate: (artifact) => {
      const unknown = artifact.outcome_dictionary.outcomes.find((outcome) => outcome.outcome_id === "Unknown");
      unknown.absence_is_falsity = true;
    },
  },
  {
    code: "f13_scope_borrowed",
    mutate: (artifact) => {
      artifact.boundaries.f13_scope_borrowed = true;
    },
  },
  {
    code: "runtime_claim_present",
    mutate: (artifact) => {
      artifact.adoption_state.note = `${artifact.adoption_state.note} pub fn emit()`;
    },
  },
  {
    code: "non_ascii_artifact",
    mutate: (artifact) => {
      artifact.adoption_state.note = `${artifact.adoption_state.note} \u00e9`;
    },
  },
  {
    code: "raw_text_leak",
    mutate: (artifact) => {
      artifact.adoption_state.note = `${artifact.adoption_state.note} <raw>`;
    },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const artifact = clone();
    entry.mutate(artifact);
    const text = JSON.stringify(artifact);
    assert.notEqual(text, LIVE_DOC, `${entry.code}: the mutation must actually change the artifact`);
    const emitted = codes(validateContract(text));
    assert.ok(emitted.includes(entry.code), `${entry.code} was not emitted; got ${JSON.stringify(emitted)}`);
    covered.add(entry.code);
  }
  assert.deepEqual([...covered].sort(), [...EMITTABLE_CODES].sort(), "every declared code must have a firing mutation");
  assert.deepEqual(
    CODE_COVERAGE.map((entry) => entry.code).slice().sort(),
    [...EMITTABLE_CODES].sort(),
    "the coverage registry must carry exactly one entry per code",
  );
});

test("negative: adoption and execution are never read as one another", () => {
  const adoptedAsExecuted = clone();
  adoptedAsExecuted.adoption_state.executed = true;
  assert.ok(codes(validateContract(JSON.stringify(adoptedAsExecuted))).includes("adoption_read_as_execution"));

  const mintedWithoutExecution = clone();
  mintedWithoutExecution.candidate_envelope.minted = true;
  assert.ok(codes(validateContract(JSON.stringify(mintedWithoutExecution))).includes("adoption_read_as_execution"));

  const committedWithoutExecution = clone();
  committedWithoutExecution.candidates = [{ candidate_id: "c1" }];
  assert.ok(codes(validateContract(JSON.stringify(committedWithoutExecution))).includes("adoption_read_as_execution"));

  const countedWithoutExecution = clone();
  countedWithoutExecution.execution_state.candidates_emitted = 1;
  assert.ok(codes(validateContract(JSON.stringify(countedWithoutExecution))).includes("adoption_read_as_execution"));

  const conflictWithoutExecution = clone();
  conflictWithoutExecution.emission_rule.conflict_unreachable_without_execution = false;
  assert.ok(codes(validateContract(JSON.stringify(conflictWithoutExecution))).includes("adoption_read_as_execution"));

  const executedAsAdoption = clone();
  executedAsAdoption.execution_state.adoption_established = true;
  assert.ok(codes(validateContract(JSON.stringify(executedAsAdoption))).includes("execution_read_as_adoption"));

  const wrongVariant = clone();
  wrongVariant.adoption_state.adopted_variant = "A";
  assert.ok(codes(validateContract(JSON.stringify(wrongVariant))).includes("execution_read_as_adoption"));

  const notEstablished = clone();
  notEstablished.adoption_state.adoption_established = false;
  assert.ok(codes(validateContract(JSON.stringify(notEstablished))).includes("execution_read_as_adoption"));
});

test("negative: a cached anchor and an unknown evidence class are rejected", () => {
  const missingPath = clone();
  missingPath.candidate_envelope.anchor_contract.requires_repository_relative_path = false;
  assert.ok(codes(validateContract(JSON.stringify(missingPath))).includes("anchor_missing"));

  const unknownClass = clone();
  unknownClass.candidate_envelope.evidence_class_domain = ["inert-artifact", "source-bound-span"];
  assert.ok(codes(validateContract(JSON.stringify(unknownClass))).includes("evidence_class_unknown"));

  const noRef = clone();
  noRef.candidate_envelope.adopted_construct_ref_required = false;
  assert.ok(codes(validateContract(JSON.stringify(noRef))).includes("candidate_without_adopted_construct"));

  const badOutcomeCount = clone();
  badOutcomeCount.outcome_dictionary.outcome_count = 2;
  assert.ok(codes(validateContract(JSON.stringify(badOutcomeCount))).includes("outcome_set_incomplete"));
});

// ---------------------------------------------------------------------------
// markers (emitted only after the contract holds)
// ---------------------------------------------------------------------------

test("M210 S03 semantics contract markers", () => {
  assert.deepEqual(validateContract(LIVE_DOC), [], "the committed artifact must be clean");
  const contract = clone();
  assert.equal(contract.adoption_state.admission_verdict, "admission_granted");
  assert.equal(contract.adoption_state.adoption_established, true);
  assert.deepEqual(contract.adoption_state.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(contract.execution_state.executed, false);
  assert.equal(contract.execution_state.candidates_emitted, 0);
  assert.equal(contract.candidate_envelope.minted, false);
  assert.equal(contract.outcome_dictionary.outcome_count, 3);
  assert.deepEqual(contract.fail_closed_codes, EMITTABLE_CODES);
  console.log("M210_S03_SEMANTICS_OK");
  console.log("admission=admission_granted");
  console.log(`adopted_constructs=${contract.adoption_state.adopted_construct_set.length}`);
  console.log(`executed=${contract.execution_state.executed}`);
  console.log(`outcomes=${contract.outcome_dictionary.outcome_count}`);
  console.log(`families=${contract.construct_dictionary.family_count}`);
  console.log(`fail_closed_codes=${contract.fail_closed_codes.length}`);
  console.log(`minted=${contract.candidate_envelope.minted}`);
});
