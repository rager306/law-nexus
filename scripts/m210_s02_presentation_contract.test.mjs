// M210-3afp79 S02 T02 presentation contract.
//
// Offline and fail-closed. The artifacts under test are
// prd/architecture/m210-s02-owner-decision-packet.json (the machine-readable
// owner decision packet) and prd/architecture/m210-s02-owner-decision-presentation.md
// (the single human-readable entry for the S02 interactive decision). Nothing
// here is accepted semantics; the claims under test are that the IR question
// carries the complete five-option set with non-empty consequences and no
// preselected option, that the recommendation is explicitly advisory and never
// consent, that F13 is a separate decision with its own concrete alternative
// and an explicit HOLD when unanswered, that the source revision is copied from
// the T01 rebind report, that the evidence class summary, limitations and
// non-claims are non-empty, that the two artifacts are canonical ASCII with no
// raw legal text and no Rust implementation marker, and that each documented
// fail-closed code is empirically emitted by a mutation.
//
// This contract spawns no subprocess, opens no socket and reads only
// repository-relative tracked artifacts under prd/ and scripts/. It never
// writes a file.
//
// Run: node --test scripts/m210_s02_presentation_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// question_missing: the IR or F13 question is absent, or carries no question id and prompt.
// option_set_incomplete: the IR option set is not exactly A, B, C, reject_all and defer, or a recommendation names an option outside the set.
// option_consequences_missing: an option carries no consequences or no what_it_cannot_prove.
// recommendation_as_consent: a recommendation is not marked advisory:true with is_consent:false.
// recommendation_without_evidence: a recommendation carries no evidence refs, or a ref does not resolve.
// f13_folded_into_ir_question: the F13 question is missing, not marked separate, or shares the IR question id.
// f13_inference_allowed: an F13 outcome may be inferred from the IR answer, or the unanswered status is not hold.
// source_revision_missing: the source revision is absent, malformed, or differs from the T01 rebind report.
// limitations_missing: the limitations list is missing or empty.
// evidence_class_missing: the evidence class summary is missing, empty, or carries an unknown class, an empty scope, a runtime claim or an unresolvable artifact ref.
// preselected_option: the packet preselects an option, at top level or on an option.
// non_claims_missing: the non-claims list is missing or empty.
// runtime_claim_present: an artifact carries a Rust implementation marker.
// raw_text_leak: an artifact carries an XML tag or a provider text marker.
// non_ascii_artifact: an artifact carries a non-ASCII byte.
// DOCUMENTED_CODES_END

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const PACKET_REL = "prd/architecture/m210-s02-owner-decision-packet.json";
export const PRESENTATION_REL = "prd/architecture/m210-s02-owner-decision-presentation.md";
export const CONTRACT_REL = "scripts/m210_s02_presentation_contract.test.mjs";
export const REBIND_REPORT_REL = "prd/architecture/m210-s02-rebind-report.json";
export const EXAMPLES_REL = "prd/architecture/m210-s01-source-bound-examples.json";
export const ALTERNATIVES_REL = "prd/architecture/m210-s01-ir-alternatives.json";
export const FAMILY_REGISTER_REL = "prd/architecture/m210-s01-normative-family-register.json";

export const SCHEMA = "law-nexus/m210-s02-owner-decision-packet/v1";
export const KIND = "m210-s02-owner-decision-packet";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S02";
export const TASK = "T02";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

export const IR_OPTION_IDS = ["A", "B", "C", "reject_all", "defer"];
export const F13_OPTION_IDS = ["adopt_amendment_operation_contract", "defer_amendment_operations"];
export const EVIDENCE_CLASSES = ["inert-artifact", "source-bound-span", "runtime-absent"];
export const FAMILY_DICTIONARY = [
  "obligation",
  "permission",
  "prohibition",
  "definition",
  "competence",
  "condition",
  "exception",
  "temporal_qualification",
];
export const PRESELECTION_KEYS = [
  "preselected_option",
  "selected_option",
  "chosen_option",
  "default_option",
  "preselected",
];

export const EMITTABLE_CODES = [
  "question_missing",
  "option_set_incomplete",
  "option_consequences_missing",
  "recommendation_as_consent",
  "recommendation_without_evidence",
  "f13_folded_into_ir_question",
  "f13_inference_allowed",
  "source_revision_missing",
  "limitations_missing",
  "evidence_class_missing",
  "preselected_option",
  "non_claims_missing",
  "runtime_claim_present",
  "raw_text_leak",
  "non_ascii_artifact",
];

export const CONTRACT_MARKER = "M210_S02_PRESENTATION_OK";
export const SOURCE_REVISION_PATTERN = /^sha256:[0-9a-f]{64}$/;

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const PRESENTATION_SECTIONS = [
  "## Scope",
  "## Source revision and evidence class",
  "## Limitations and non-claims",
  "## Alternatives and consequences for S03",
  "## Comparison with the existing NormRule spine",
  "## Disputed cards and negative examples",
  "## Proof ceiling",
  "## Recommendation (advisory only, not consent)",
  "## The exact IR question",
  "## F13 is a separate decision",
  "## Read-back template",
  "## Interactive conduit fields",
];

const CONDUIT_FIELDS = [
  "criterionKey",
  "description",
  "focusedPrompt",
  "recommendedDisposition",
  "recommendationRationale",
  "recommendationEvidence",
  "testedSourceRevision",
];

const READBACK_FIELDS = [
  "ir_question_id",
  "ir_selected_option",
  "ir_verbatim_response",
  "f13_question_id",
  "f13_selected_option",
  "f13_verbatim_response",
  "f13_status",
  "source_revision",
  "presented_fields",
  "not_a_consent",
];

// ---------------------------------------------------------------------------
// shared fixtures
// ---------------------------------------------------------------------------

export const root = REPO_ROOT;
export const packetAbsolute = path.join(root, PACKET_REL);
export const presentationAbsolute = path.join(root, PRESENTATION_REL);

export const committedText = readFileSync(packetAbsolute, "utf8");
export const packet = JSON.parse(committedText);
export const presentationText = readFileSync(presentationAbsolute, "utf8");
export const rebindReport = JSON.parse(readFileSync(path.join(root, REBIND_REPORT_REL), "utf8"));
export const examples = JSON.parse(readFileSync(path.join(root, EXAMPLES_REL), "utf8"));
export const alternatives = JSON.parse(readFileSync(path.join(root, ALTERNATIVES_REL), "utf8"));
export const familyRegister = JSON.parse(readFileSync(path.join(root, FAMILY_REGISTER_REL), "utf8"));

export function relativeExists(relativePath) {
  if (typeof relativePath !== "string" || relativePath === "") return false;
  if (path.isAbsolute(relativePath) || relativePath.split("/").includes("..")) return false;
  return existsSync(path.join(root, relativePath));
}

// A recommendation evidence ref may carry a fragment (`path#anchor`); only the
// path part has to resolve.
export function evidenceRefExists(ref) {
  if (typeof ref !== "string" || ref.trim() === "") return false;
  return relativeExists(ref.split("#")[0]);
}

function hasText(value) {
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) {
    return value.length > 0 && value.every((entry) => typeof entry === "string" && entry.trim() !== "");
  }
  return false;
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validatePacket(candidate, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(candidate);
  const markdown = typeof env.presentationText === "string" ? env.presentationText : "";
  const combined = `${text}\n${markdown}`;
  const exists = env.exists ?? (() => true);
  const expectedSourceRevision = env.expectedSourceRevision;

  // 1. text hygiene across both artifacts: ASCII-only, no XML or provider text
  //    marker, no Rust implementation marker.
  const offending = [...combined].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_artifact", `non-ascii character at index ${offending}`);
  for (const marker of RAW_TEXT_MARKERS) {
    if (combined.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (combined.includes(marker)) code("runtime_claim_present", `runtime marker ${marker}`);
  }

  // 2. the source revision is copied from the T01 rebind report, never invented.
  const revision = candidate?.source_revision;
  if (typeof revision !== "string" || !SOURCE_REVISION_PATTERN.test(revision)) {
    code("source_revision_missing", `source_revision=${JSON.stringify(revision)}`);
  } else if (typeof expectedSourceRevision === "string" && revision !== expectedSourceRevision) {
    code("source_revision_missing", "source_revision differs from the T01 rebind report");
  }

  // 3. evidence class summary: non-empty, closed dictionary, no runtime claim.
  const summary = Array.isArray(candidate?.evidence_class_summary) ? candidate.evidence_class_summary : null;
  if (!summary || summary.length === 0) {
    code("evidence_class_missing", "evidence_class_summary is missing or empty");
  } else {
    for (const entry of summary) {
      const scope = `evidence class ${JSON.stringify(entry?.evidence_class)}`;
      if (!EVIDENCE_CLASSES.includes(entry?.evidence_class)) {
        code("evidence_class_missing", `${scope} is not in the closed dictionary`);
        continue;
      }
      if (typeof entry?.claim_scope !== "string" || entry.claim_scope.trim() === "") {
        code("evidence_class_missing", `${scope} carries no claim_scope`);
      }
      if (entry?.runtime !== false) {
        code("evidence_class_missing", `${scope} claims a runtime surface`);
      }
      if (typeof entry?.claim_count !== "number") {
        code("evidence_class_missing", `${scope} carries no claim_count`);
      }
      if (!exists(entry?.artifact_ref)) {
        code("evidence_class_missing", `${scope} names an unresolvable artifact_ref`);
      }
    }
  }

  // 4. limitations and non-claims must be carried, not implied.
  if (!Array.isArray(candidate?.limitations) || candidate.limitations.length === 0) {
    code("limitations_missing", "limitations is missing or empty");
  }
  if (!Array.isArray(candidate?.non_claims) || candidate.non_claims.length === 0) {
    code("non_claims_missing", "non_claims is missing or empty");
  }

  // 5. no option may be preselected, at top level or on an option.
  for (const key of PRESELECTION_KEYS) {
    const value = candidate?.[key];
    if (value !== undefined && value !== null && value !== false) {
      code("preselected_option", `the packet carries ${key}`);
    }
  }

  const checkRecommendation = (recommendation, scope, allowedOptionIds) => {
    if (!recommendation || typeof recommendation !== "object") {
      code("recommendation_without_evidence", `${scope} is missing`);
      return;
    }
    const refs = Array.isArray(recommendation.evidence_refs) ? recommendation.evidence_refs : null;
    if (!refs || refs.length === 0) {
      code("recommendation_without_evidence", `${scope} carries no evidence_refs`);
    } else {
      for (const ref of refs) {
        if (!evidenceRefExists(ref)) {
          code("recommendation_without_evidence", `${scope} evidence ref ${JSON.stringify(ref)} does not resolve`);
        }
      }
    }
    if (
      recommendation.advisory !== true ||
      recommendation.is_consent !== false ||
      recommendation.consent === true ||
      recommendation.accepted === true
    ) {
      code("recommendation_as_consent", `${scope} is not marked advisory:true with is_consent:false`);
    }
    if (!allowedOptionIds.includes(recommendation.option_id)) {
      code("option_set_incomplete", `${scope} names option ${JSON.stringify(recommendation.option_id)}`);
    }
  };

  const checkOptions = (options, scope, requireCannotProve) => {
    if (!Array.isArray(options) || options.length === 0) {
      code("option_set_incomplete", `${scope} carries no option array`);
      return;
    }
    for (const option of options) {
      const label = `option ${JSON.stringify(option?.option_id)}`;
      if (!hasText(option?.consequences)) {
        code("option_consequences_missing", `${scope} ${label} carries no consequences`);
      }
      if (requireCannotProve && !hasText(option?.what_it_cannot_prove)) {
        code("option_consequences_missing", `${scope} ${label} carries no what_it_cannot_prove`);
      }
      for (const key of PRESELECTION_KEYS) {
        if (option?.[key] === true) code("preselected_option", `${scope} ${label} is marked ${key}`);
      }
    }
  };

  // 6. the IR question: exact option set, no preselection, advisory recommendation.
  const ir = candidate?.ir_question;
  if (
    !ir ||
    typeof ir !== "object" ||
    typeof ir.question_id !== "string" ||
    ir.question_id.trim() === "" ||
    typeof ir.prompt !== "string" ||
    ir.prompt.trim() === ""
  ) {
    code("question_missing", "ir_question is missing or carries no question_id and prompt");
  } else {
    const options = Array.isArray(ir.options) ? ir.options : null;
    if (!options) {
      code("option_set_incomplete", "ir_question carries no option array");
    } else {
      const ids = options.map((option) => option?.option_id);
      if (new Set(ids).size !== ids.length) code("option_set_incomplete", "ir_question repeats an option_id");
      const missing = IR_OPTION_IDS.filter((id) => !ids.includes(id));
      const extra = ids.filter((id) => !IR_OPTION_IDS.includes(id));
      if (missing.length > 0 || extra.length > 0) {
        code("option_set_incomplete", `missing [${missing.join(",")}] extra [${extra.join(",")}]`);
      }
      checkOptions(options, "ir_question", true);
    }
    checkRecommendation(ir.recommendation, "ir_question.recommendation", IR_OPTION_IDS);
  }

  // 7. F13 is a separate decision and never inferred from the IR answer.
  const f13 = candidate?.f13_question;
  if (!f13 || typeof f13 !== "object") {
    code("f13_folded_into_ir_question", "f13_question is missing");
  } else {
    if (f13.is_separate_decision !== true) {
      code("f13_folded_into_ir_question", "f13_question is not marked a separate decision");
    }
    if (
      typeof f13.question_id !== "string" ||
      f13.question_id.trim() === "" ||
      f13.question_id === ir?.question_id
    ) {
      code("f13_folded_into_ir_question", "f13_question carries no distinct question_id");
    }
    if (typeof f13.prompt !== "string" || f13.prompt.trim() === "") {
      code("question_missing", "f13_question carries no prompt");
    }
    checkOptions(f13.options, "f13_question", false);
    checkRecommendation(f13.recommendation, "f13_question.recommendation", F13_OPTION_IDS);
    if (
      f13.inference_from_ir_forbidden !== true ||
      f13.status_if_unanswered !== "hold" ||
      f13.inferred_from_ir === true
    ) {
      code("f13_inference_allowed", "an F13 outcome may be inferred from the IR answer");
    }
  }

  return { ok: errors.length === 0, errors };
}

export function baseEnv(overrides = {}) {
  return {
    text: committedText,
    presentationText,
    expectedSourceRevision: rebindReport.source_revision,
    exists: relativeExists,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// harness
// ---------------------------------------------------------------------------

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function codesFor(mutated, overrides = {}) {
  const env = baseEnv({ text: JSON.stringify(mutated), ...overrides });
  return validatePacket(mutated, env).errors.map((error) => error.name);
}

function contractSource() {
  return readFileSync(path.join(root, CONTRACT_REL), "utf8");
}

function documentedBlock() {
  const source = contractSource();
  const begin = source.indexOf("DOCUMENTED_CODES_BEGIN");
  const end = source.indexOf("DOCUMENTED_CODES_END");
  assert.ok(begin > 0 && end > begin, "the documented code block must be present");
  return source
    .slice(begin, end)
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+): /)?.[1])
    .filter((name) => typeof name === "string");
}

// Node's test runner keeps running after a failing case, so a marker printed
// from the last case would still look green on a red run. Record every failure
// and let the last case refuse to print the marker if any earlier case failed.
const failures = [];
function contract(title, body) {
  test(title, () => {
    try {
      body();
    } catch (error) {
      failures.push(title);
      throw error;
    }
  });
}

// ---------------------------------------------------------------------------
// artifact shape
// ---------------------------------------------------------------------------

contract("both artifacts exist and the packet is canonical ASCII JSON with the M210 envelope", () => {
  assert.ok(existsSync(packetAbsolute), `${PACKET_REL} must exist`);
  assert.ok(existsSync(presentationAbsolute), `${PRESENTATION_REL} must exist`);
  assert.ok(!committedText.endsWith("\n"), "the packet must carry no trailing newline");
  assert.ok(
    ![...committedText].some((character) => character.charCodeAt(0) > 0x7f),
    "the packet must be ASCII-only",
  );
  assert.equal(JSON.stringify(packet), committedText, "the packet must be canonical JSON that round-trips");
  assert.equal(packet.schema, SCHEMA);
  assert.equal(packet.kind, KIND);
  assert.equal(packet.milestone, MILESTONE);
  assert.equal(packet.slice, SLICE);
  assert.equal(packet.task, TASK);
  assert.deepEqual(packet.lifecycle, LIFECYCLE);
  assert.equal(packet.authoritative, false);
  assert.equal(packet.semantics_adopted, false);
  assert.equal(packet.ascii_only, true);
  assert.deepEqual(packet.requirement_refs, REQUIREMENT_REFS);
});

contract("the clean packet passes the validator with no error", () => {
  const result = validatePacket(packet, baseEnv());
  assert.equal(result.ok, true, JSON.stringify(result.errors));
});

contract("the presentation is ASCII markdown with every required section and field list", () => {
  assert.ok(
    ![...presentationText].some((character) => character.charCodeAt(0) > 0x7f),
    "the presentation must be ASCII-only",
  );
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!presentationText.includes(marker), `the presentation must not carry the text marker ${marker}`);
  }
  for (const section of PRESENTATION_SECTIONS) {
    assert.ok(presentationText.includes(section), `the presentation must carry the section ${section}`);
  }
  for (const field of CONDUIT_FIELDS) {
    assert.ok(
      presentationText.includes(`\`${field}\``),
      `the presentation must name the conduit field ${field}`,
    );
  }
  for (const field of READBACK_FIELDS) {
    assert.ok(presentationText.includes(field), `the presentation must name the read-back field ${field}`);
  }
  assert.ok(presentationText.includes("HOLD"), "the presentation must state that an unanswered F13 stays at HOLD");
});

// ---------------------------------------------------------------------------
// question shape
// ---------------------------------------------------------------------------

contract("the IR question carries the complete option set with non-empty consequences", () => {
  const ids = packet.ir_question.options.map((option) => option.option_id);
  assert.deepEqual(ids.slice().sort(), IR_OPTION_IDS.slice().sort());
  assert.equal(new Set(ids).size, ids.length, "no option may be repeated");
  for (const option of packet.ir_question.options) {
    assert.ok(
      typeof option.consequences === "string" && option.consequences.trim() !== "",
      `option ${option.option_id} must carry consequences`,
    );
    assert.ok(
      Array.isArray(option.what_it_cannot_prove) && option.what_it_cannot_prove.length > 0,
      `option ${option.option_id} must carry what_it_cannot_prove`,
    );
  }
  assert.match(packet.ir_question.prompt, /preselected/i, "the prompt must state that no option is preselected");
});

contract("the recommendation is advisory, is not consent and carries resolving evidence refs", () => {
  for (const [scope, recommendation] of [
    ["ir", packet.ir_question.recommendation],
    ["f13", packet.f13_question.recommendation],
  ]) {
    assert.equal(recommendation.advisory, true, `${scope} recommendation must be advisory`);
    assert.equal(recommendation.is_consent, false, `${scope} recommendation must not be consent`);
    assert.ok(Array.isArray(recommendation.evidence_refs) && recommendation.evidence_refs.length > 0);
    for (const ref of recommendation.evidence_refs) {
      assert.ok(evidenceRefExists(ref), `${scope} evidence ref ${ref} must resolve to a tracked artifact`);
    }
  }
  assert.equal(packet.ir_question.recommendation.option_id, "C");
  assert.ok(IR_OPTION_IDS.includes(packet.ir_question.recommendation.option_id));
});

contract("F13 is a separate decision with its own concrete alternative and an unanswered HOLD", () => {
  const f13 = packet.f13_question;
  assert.equal(f13.is_separate_decision, true);
  assert.equal(f13.inference_from_ir_forbidden, true);
  assert.equal(f13.status_if_unanswered, "hold");
  assert.notEqual(f13.question_id, packet.ir_question.question_id);
  assert.ok(f13.options.length >= 2, "F13 must carry its own concrete alternatives");
  const ids = f13.options.map((option) => option.option_id);
  assert.deepEqual(ids.slice().sort(), F13_OPTION_IDS.slice().sort());
  for (const option of f13.options) {
    assert.ok(typeof option.consequences === "string" && option.consequences.trim() !== "");
  }
  assert.ok(F13_OPTION_IDS.includes(f13.recommendation.option_id));
  assert.equal(f13.originating_review_ref.split("#")[1], "RC28-F13");
});

contract("no option is preselected anywhere in the packet", () => {
  for (const key of PRESELECTION_KEYS) {
    assert.equal(packet[key], undefined, `the packet must not carry ${key}`);
  }
  for (const [scope, options] of [
    ["ir", packet.ir_question.options],
    ["f13", packet.f13_question.options],
  ]) {
    for (const option of options) {
      for (const key of PRESELECTION_KEYS) {
        assert.notEqual(option[key], true, `${scope} option ${option.option_id} must not be marked ${key}`);
      }
    }
  }
});

// ---------------------------------------------------------------------------
// live-bound claims
// ---------------------------------------------------------------------------

contract("the source revision is copied from the T01 rebind report", () => {
  assert.match(packet.source_revision, SOURCE_REVISION_PATTERN);
  assert.equal(packet.source_revision, rebindReport.source_revision);
  assert.equal(packet.source_revision_ref, REBIND_REPORT_REL);
  assert.equal(packet.evidence_class_summary.length, EVIDENCE_CLASSES.length);
  assert.deepEqual(
    packet.evidence_class_summary.map((entry) => entry.evidence_class).slice().sort(),
    EVIDENCE_CLASSES.slice().sort(),
  );
});

contract("evidence counts, limitations and non-claims are non-empty and live-derived", () => {
  assert.ok(packet.limitations.length > 0);
  assert.ok(packet.non_claims.length > 0);
  const byClass = new Map(packet.evidence_class_summary.map((entry) => [entry.evidence_class, entry]));
  const spanClaims =
    examples.dispute_cards.length + examples.negative_examples.length + examples.corpus_probes.length;
  assert.equal(byClass.get("source-bound-span").claim_count, spanClaims);
  assert.equal(byClass.get("inert-artifact").claim_count, rebindReport.rebound_inputs.length);
  assert.equal(byClass.get("runtime-absent").claim_count, 0);
  for (const entry of packet.evidence_class_summary) {
    assert.equal(entry.runtime, false);
    assert.ok(entry.claim_scope.trim() !== "");
    assert.ok(relativeExists(entry.artifact_ref));
  }
});

contract("the disputed and negative example references match the examples artifact live", () => {
  const ref = packet.disputed_examples_ref;
  assert.equal(ref.path, EXAMPLES_REL);
  assert.equal(ref.card_count, examples.dispute_cards.length);
  const verdicts = examples.dispute_cards.map((card) => card.verdict);
  assert.equal(ref.conflicted, verdicts.filter((verdict) => verdict === "conflicted").length);
  assert.equal(ref.unresolved, verdicts.filter((verdict) => verdict === "unresolved").length);
  assert.equal(ref.resolved, 0);
  assert.ok(!verdicts.includes("resolved"), "no card may carry a resolved verdict");
  assert.deepEqual(ref.families.slice().sort(), FAMILY_DICTIONARY.slice().sort());
  assert.equal(ref.requires_human_source_review, true);
  assert.equal(ref.adopted, false);
  for (const card of examples.dispute_cards) {
    assert.equal(card.requires_human_source_review, true);
    assert.equal(card.adopted, false);
  }
  assert.deepEqual(
    packet.negative_examples_ref.map((entry) => entry.example_id).slice().sort(),
    examples.negative_examples.map((entry) => entry.example_id).slice().sort(),
  );
  for (const entry of packet.negative_examples_ref) {
    const live = examples.negative_examples.find((candidate) => candidate.example_id === entry.example_id);
    assert.ok(live, `${entry.example_id} must exist in the examples artifact`);
    assert.equal(entry.fail_closed_code, live.fail_closed_code);
    assert.equal(entry.path, EXAMPLES_REL);
  }
});

contract("the family dictionary matches the T01 register and the alternatives artifact", () => {
  assert.deepEqual(
    familyRegister.families.map((family) => family.family_id).slice().sort(),
    FAMILY_DICTIONARY.slice().sort(),
  );
  assert.deepEqual(alternatives.family_dictionary.slice().sort(), FAMILY_DICTIONARY.slice().sort());
  assert.deepEqual(alternatives.section3_deferred_terms.slice().sort(), [
    "ApplicabilitySelector",
    "Condition",
    "Defeater",
    "Exception",
    "LegalEffect",
    "NormRule",
  ].sort());
});

// ---------------------------------------------------------------------------
// fail-closed codes
// ---------------------------------------------------------------------------

contract("every documented fail-closed code is emitted on a mutated copy", () => {
  const base = clone(packet);
  const clean = validatePacket(base, baseEnv({ text: JSON.stringify(base) }));
  assert.equal(clean.ok, true, JSON.stringify(clean.errors));

  const emitted = new Set();
  const collect = (codes) => {
    for (const name of codes) emitted.add(name);
  };

  // question_missing: the IR question or its prompt disappears.
  const noQuestion = clone(base);
  delete noQuestion.ir_question;
  collect(codesFor(noQuestion));
  const emptyPrompt = clone(base);
  emptyPrompt.ir_question.prompt = "";
  collect(codesFor(emptyPrompt));

  // option_set_incomplete: an option is dropped, duplicated or outside the set.
  const droppedOption = clone(base);
  droppedOption.ir_question.options = droppedOption.ir_question.options.filter(
    (option) => option.option_id !== "defer",
  );
  collect(codesFor(droppedOption));
  const duplicatedOption = clone(base);
  duplicatedOption.ir_question.options[1].option_id = "A";
  collect(codesFor(duplicatedOption));
  const unknownRecommendation = clone(base);
  unknownRecommendation.ir_question.recommendation.option_id = "D";
  collect(codesFor(unknownRecommendation));

  // option_consequences_missing: an option loses its consequences or its limits.
  const noConsequences = clone(base);
  noConsequences.ir_question.options[0].consequences = "";
  collect(codesFor(noConsequences));
  const noCannotProve = clone(base);
  noCannotProve.ir_question.options[0].what_it_cannot_prove = [];
  collect(codesFor(noCannotProve));

  // recommendation_as_consent: the recommendation is presented as consent.
  const consent = clone(base);
  consent.ir_question.recommendation.is_consent = true;
  collect(codesFor(consent));
  const notAdvisory = clone(base);
  notAdvisory.f13_question.recommendation.advisory = false;
  collect(codesFor(notAdvisory));

  // recommendation_without_evidence: no refs, or a ref that does not resolve.
  const noEvidence = clone(base);
  noEvidence.ir_question.recommendation.evidence_refs = [];
  collect(codesFor(noEvidence));
  const danglingEvidence = clone(base);
  danglingEvidence.ir_question.recommendation.evidence_refs = ["prd/architecture/does-not-exist.json"];
  collect(codesFor(danglingEvidence));

  // f13_folded_into_ir_question: F13 disappears, stops being separate or shares the IR id.
  const noF13 = clone(base);
  delete noF13.f13_question;
  collect(codesFor(noF13));
  const notSeparate = clone(base);
  notSeparate.f13_question.is_separate_decision = false;
  collect(codesFor(notSeparate));
  const sharedId = clone(base);
  sharedId.f13_question.question_id = sharedId.ir_question.question_id;
  collect(codesFor(sharedId));

  // f13_inference_allowed: an F13 outcome may be inferred, or the status is not hold.
  const inference = clone(base);
  inference.f13_question.inference_from_ir_forbidden = false;
  collect(codesFor(inference));
  const notHold = clone(base);
  notHold.f13_question.status_if_unanswered = "adopted";
  collect(codesFor(notHold));

  // source_revision_missing: absent, malformed, or moved away from the T01 report.
  const badRevision = clone(base);
  badRevision.source_revision = "deadbeef";
  collect(codesFor(badRevision, { expectedSourceRevision: undefined }));
  const movedRevision = clone(base);
  movedRevision.source_revision = `sha256:${"3".repeat(64)}`;
  collect(codesFor(movedRevision));

  // limitations_missing: the limitations list is emptied.
  const noLimitations = clone(base);
  noLimitations.limitations = [];
  collect(codesFor(noLimitations));

  // evidence_class_missing: the summary is emptied, unknown or claims runtime.
  const noEvidenceClass = clone(base);
  noEvidenceClass.evidence_class_summary = [];
  collect(codesFor(noEvidenceClass));
  const unknownEvidenceClass = clone(base);
  unknownEvidenceClass.evidence_class_summary[0].evidence_class = "runtime-span";
  collect(codesFor(unknownEvidenceClass));
  const runtimeEvidenceClass = clone(base);
  runtimeEvidenceClass.evidence_class_summary[0].runtime = true;
  collect(codesFor(runtimeEvidenceClass));
  const unresolvableArtifactRef = clone(base);
  unresolvableArtifactRef.evidence_class_summary[0].artifact_ref = "prd/architecture/absent.json";
  collect(codesFor(unresolvableArtifactRef));

  // preselected_option: the packet or an option preselects an answer.
  const preselectedTop = clone(base);
  preselectedTop.preselected_option = "C";
  collect(codesFor(preselectedTop));
  const preselectedOnOption = clone(base);
  preselectedOnOption.ir_question.options[2].preselected = true;
  collect(codesFor(preselectedOnOption));

  // non_claims_missing: the non-claims list is emptied.
  const noNonClaims = clone(base);
  noNonClaims.non_claims = [];
  collect(codesFor(noNonClaims));

  // runtime_claim_present: a Rust implementation marker in either artifact.
  const runtimeClaim = clone(base);
  runtimeClaim.non_claims[0] = "the packet calls pub fn parse()";
  collect(codesFor(runtimeClaim));
  collect(codesFor(clone(base), { presentationText: `${presentationText}\npub struct Record;` }));

  // raw_text_leak: an XML tag or a provider text marker.
  const rawLeak = clone(base);
  rawLeak.non_claims[0] = "leaked <screenTip>";
  collect(codesFor(rawLeak));
  collect(codesFor(clone(base), { presentationText: `${presentationText}\nconsultantplus://offline` }));

  // non_ascii_artifact: a non-ASCII byte in either artifact.
  const nonAscii = clone(base);
  nonAscii.non_claims[0] = "dash \u2014 not ascii";
  collect(codesFor(nonAscii));
  collect(codesFor(clone(base), { presentationText: `${presentationText}\n\u2014` }));

  assert.deepEqual([...emitted].sort(), EMITTABLE_CODES.slice().sort());
});

contract("the documented code block equals the declared code set", () => {
  const documented = documentedBlock();
  assert.equal(new Set(documented).size, documented.length, "the documented block must carry no duplicate");
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(packet.fail_closed_codes.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.equal(EMITTABLE_CODES.length, 15);
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

contract("the contract is offline, spawns nothing and reads no ignored or absolute path", () => {
  const source = contractSource();
  // Needles are concatenated so the guard cannot match its own assertion text.
  assert.ok(!source.includes("spawn" + "Sync"), "the contract must spawn no subprocess");
  assert.ok(!source.includes("child" + "_process"), "the contract must not import the child-process module");
  assert.ok(!/\b(?:fetch|https?):\/\//.test(source), "the contract must be offline");
  assert.ok(
    !/readFileSync\(\s*(?:path\.join\(root,\s*)?"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readFileSync\(\s*"\//.test(source), "the contract must not read an absolute path");
  const declared = {
    PACKET_REL,
    PRESENTATION_REL,
    CONTRACT_REL,
    REBIND_REPORT_REL,
    EXAMPLES_REL,
    ALTERNATIVES_REL,
    FAMILY_REGISTER_REL,
  };
  const reads = [
    ...source.matchAll(/readFileSync\(path\.join\(root,\s*([A-Za-z_$][\w$]*)\)/g),
  ].map((match) => match[1]);
  const directReads = [...source.matchAll(/readFileSync\((packetAbsolute|presentationAbsolute)/g)].map(
    (match) => match[1],
  );
  assert.ok(reads.length + directReads.length >= 6, "the contract must read the declared artifacts");
  for (const identifier of new Set(reads)) {
    const relativePath = declared[identifier];
    assert.ok(relativePath, `readFileSync must target a declared artifact constant, got ${identifier}`);
    assert.ok(relativeExists(relativePath), `the contract reads ${relativePath}, which must exist`);
  }
  for (const identifier of new Set(directReads)) {
    const relativePath = identifier === "packetAbsolute" ? PACKET_REL : PRESENTATION_REL;
    assert.ok(relativeExists(relativePath), `the contract reads ${relativePath}, which must exist`);
  }
  assert.ok(source.includes("DOCUMENTED_CODES_BEGIN"), "the documented code block must be machine-readable");
});

// ---------------------------------------------------------------------------
// markers
// ---------------------------------------------------------------------------

contract("M210 S02 presentation markers", () => {
  assert.deepEqual(failures, [], "a failing case must suppress the success marker");
  process.stdout.write(
    `${CONTRACT_MARKER} options=${packet.ir_question.options.length} ` +
      `f13_options=${packet.f13_question.options.length} codes=${EMITTABLE_CODES.length} ` +
      `evidence_classes=${packet.evidence_class_summary.length}\n`,
  );
});
