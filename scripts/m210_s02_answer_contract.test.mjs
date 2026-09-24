// M210-3afp79 S02 T03 answer contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s02-answer-record.json: the record of the interactive
// owner answer, or an honest pending stop when no authenticated interactive
// answer exists. Nothing here is accepted semantics and no answer is invented.
//
// The claims under test are that the answer slot format matches the
// authenticated interactive conduit (criterion_id, question_id, interaction_id,
// selected_option_id, verbatim_response, rationale, tested_source_revision),
// that status answered requires an interactive answer source plus non-empty
// criterion, question, interaction and verbatim references and a read-back,
// that status pending_human_decision is the only lawful state when there is no
// interactive answer (answer_source none, selected_option_id null), that an
// explicit option resolution must be present in the verbatim text, that no
// agent selection, no automatic adoption, no F13 inference from the IR answer
// and no Review Case event may appear, that the verbatim text is length-bounded
// and cannot hijack a verdict or a heading, that the source revision is the T01
// rebind revision, that the artifact is canonical ASCII with no raw legal text
// and no Rust implementation marker, and that each documented fail-closed code
// is empirically emitted by a mutation.
//
// This contract spawns no subprocess, opens no socket and reads only
// repository-relative tracked artifacts under prd/ and scripts/. It never
// writes a file.
//
// Run: node --test scripts/m210_s02_answer_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// answer_field_set_incomplete: an answer slot is missing, is not an object, or does not carry exactly the conduit field set.
// answer_source_not_interactive: the answer source is outside the closed dictionary, or an answered status does not name the authenticated interactive criterion source.
// verbatim_missing: a verbatim response is absent, is not a string, or is empty while the status is answered.
// readback_missing: the read-back block is missing, carries no presented fields, or carries no read-back text while the status is answered.
// reference_missing: a question, criterion or interaction reference is absent, is not a string, is empty while answered, or does not match the packet question id.
// pending_state_not_exclusive: the pending state is mixed with an answer source, a selected option or a resolved option.
// option_unresolved: an option resolution is unknown, an answered slot resolves no option present in its verbatim text, or a selected option is outside the question option set.
// agent_selected_answer: the record marks an agent-selected option or a top-level agent selection.
// answer_as_automatic_adoption: the record treats the saved answer as an adoption, or promotes a requirement.
// f13_inferred_from_ir: an F13 status or option is derived from the IR answer slot instead of a separate decision.
// review_case_event_written: the Review Case event guard is not zero.
// raw_text_leak: the record carries an XML tag or a provider text marker.
// verbatim_too_long: a verbatim response exceeds the declared maximum length.
// verbatim_field_hijack: a verbatim response carries a verdict line or a markdown heading.
// stale_answer_revision: the source revision is absent, malformed, differs from the T01 rebind report, or an answered slot was tested against another revision.
// status_not_in_dictionary: the status is outside the closed dictionary.
// non_ascii_artifact: the record carries a non-ASCII byte.
// runtime_claim_present: the record carries a Rust implementation marker.
// DOCUMENTED_CODES_END

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const ANSWER_REL = "prd/architecture/m210-s02-answer-record.json";
export const CONTRACT_REL = "scripts/m210_s02_answer_contract.test.mjs";
export const PACKET_REL = "prd/architecture/m210-s02-owner-decision-packet.json";
export const PRESENTATION_REL = "prd/architecture/m210-s02-owner-decision-presentation.md";
export const REBIND_REPORT_REL = "prd/architecture/m210-s02-rebind-report.json";

export const SCHEMA = "law-nexus/m210-s02-answer-record/v1";
export const KIND = "m210-s02-answer-record";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S02";
export const TASK = "T03";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

export const ANSWER_SOURCES = ["subjective_uat_criterion", "none"];
export const STATUSES = ["answered", "pending_human_decision"];
export const OPTION_RESOLUTIONS = ["explicit_in_verbatim", "unresolved"];
export const F13_STATUSES = ["hold", "answered"];

// The authenticated interactive conduit field set. An answer slot must carry
// exactly these keys, so a paraphrase or a partial record cannot pass as an
// answer.
export const ANSWER_FIELDS = [
  "question_id",
  "criterion_id",
  "question_id_ref",
  "interaction_id",
  "selected_option_id",
  "option_resolution",
  "verbatim_response",
  "rationale",
  "tested_source_revision",
];

// The conduit fields that were (or would be) passed to the interactive
// question, as named in the T02 presentation.
export const CONDUIT_FIELDS = [
  "criterionKey",
  "description",
  "focusedPrompt",
  "recommendedDisposition",
  "recommendationRationale",
  "recommendationEvidence",
  "testedSourceRevision",
];

export const IR_OPTION_IDS = ["A", "B", "C", "reject_all", "defer"];
export const F13_OPTION_IDS = ["adopt_amendment_operation_contract", "defer_amendment_operations"];

export const GUARD_FIELDS = ["review_case_events_written", "answer_treated_as_adoption", "agent_selected"];
export const ADOPTION_KEYS = ["adoption", "semantic_adoption", "answer_treated_as_adoption", "requirements_promoted"];

export const VERBATIM_MAX = 2000;

export const EMITTABLE_CODES = [
  "answer_field_set_incomplete",
  "answer_source_not_interactive",
  "verbatim_missing",
  "readback_missing",
  "reference_missing",
  "pending_state_not_exclusive",
  "option_unresolved",
  "agent_selected_answer",
  "answer_as_automatic_adoption",
  "f13_inferred_from_ir",
  "review_case_event_written",
  "raw_text_leak",
  "verbatim_too_long",
  "verbatim_field_hijack",
  "stale_answer_revision",
  "status_not_in_dictionary",
  "non_ascii_artifact",
  "runtime_claim_present",
];

export const CONTRACT_MARKER = "M210_S02_ANSWER_OK";
export const SOURCE_REVISION_PATTERN = /^sha256:[0-9a-f]{64}$/;

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const VERDICT_LINE_RE = /^\*\*admission: (granted|not-adopted)\*\*$/m;
const HEADING_RE = /^#{1,6}\s/m;

// ---------------------------------------------------------------------------
// shared fixtures
// ---------------------------------------------------------------------------

export const root = REPO_ROOT;
export const answerAbsolute = path.join(root, ANSWER_REL);
export const packetAbsolute = path.join(root, PACKET_REL);
export const presentationAbsolute = path.join(root, PRESENTATION_REL);

export const committedText = readFileSync(answerAbsolute, "utf8");
export const answer = JSON.parse(committedText);
export const packet = JSON.parse(readFileSync(packetAbsolute, "utf8"));
export const presentationText = readFileSync(presentationAbsolute, "utf8");
export const rebindReport = JSON.parse(readFileSync(path.join(root, REBIND_REPORT_REL), "utf8"));

export function relativeExists(relativePath) {
  if (typeof relativePath !== "string" || relativePath === "") return false;
  if (path.isAbsolute(relativePath) || relativePath.split("/").includes("..")) return false;
  return existsSync(path.join(root, relativePath));
}

export function optionTokenPresent(optionId, text) {
  if (typeof optionId !== "string" || optionId === "" || typeof text !== "string") return false;
  const escaped = optionId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?:^|[^A-Za-z0-9_])${escaped}(?:[^A-Za-z0-9_]|$)`).test(text);
}

function slotKeys(slot) {
  if (!slot || typeof slot !== "object") return [];
  return Object.keys(slot).slice().sort();
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateAnswer(candidate, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(candidate);
  const expectedSourceRevision = env.expectedSourceRevision;
  const questionPacket = env.packet ?? packet;
  const maxVerbatim =
    typeof candidate?.max_verbatim_chars === "number" ? candidate.max_verbatim_chars : VERBATIM_MAX;

  // 1. text hygiene: ASCII-only, no XML or provider text marker, no Rust
  //    implementation marker.
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_artifact", `non-ascii character at index ${offending}`);
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) code("runtime_claim_present", `runtime marker ${marker}`);
  }

  // 2. the record is bound to the T01 rebind revision, never to a guessed one.
  const revision = candidate?.source_revision;
  if (typeof revision !== "string" || !SOURCE_REVISION_PATTERN.test(revision)) {
    code("stale_answer_revision", `source_revision=${JSON.stringify(revision)}`);
  } else if (typeof expectedSourceRevision === "string" && revision !== expectedSourceRevision) {
    code("stale_answer_revision", "source_revision differs from the T01 rebind report");
  }

  // 3. closed dictionaries for the answer source and the status.
  const status = candidate?.status;
  if (!STATUSES.includes(status)) code("status_not_in_dictionary", `status=${JSON.stringify(status)}`);
  const answerSource = candidate?.answer_source;
  if (!ANSWER_SOURCES.includes(answerSource)) {
    code("answer_source_not_interactive", `answer_source=${JSON.stringify(answerSource)}`);
  }

  // 4. read-back: a non-empty presented-field list and a read-back text.
  const readback = candidate?.readback;
  const presentedFields = Array.isArray(readback?.presented_fields) ? readback.presented_fields : null;
  if (
    !readback ||
    typeof readback !== "object" ||
    !presentedFields ||
    presentedFields.length === 0 ||
    !presentedFields.every((field) => typeof field === "string" && field.trim() !== "") ||
    typeof readback.read_back_text !== "string"
  ) {
    code("readback_missing", "readback must carry a non-empty presented_fields list and a read_back_text string");
  }

  // 5. guards: no Review Case event, no automatic adoption, no agent selection.
  const guards = candidate?.guards;
  if (!guards || guards.review_case_events_written !== 0) {
    code("review_case_event_written", `review_case_events_written=${JSON.stringify(guards?.review_case_events_written)}`);
  }
  const adoptionClaim =
    guards?.answer_treated_as_adoption === true ||
    candidate?.answer_treated_as_adoption === true ||
    candidate?.semantics_adopted === true ||
    candidate?.semantic_adoption !== undefined ||
    candidate?.adoption !== undefined ||
    (candidate?.requirements_promoted !== undefined && candidate.requirements_promoted !== 0);
  if (!guards || guards.answer_treated_as_adoption !== false || adoptionClaim) {
    code("answer_as_automatic_adoption", "the saved answer text must not be treated as an adoption");
  }
  const agentPicked =
    guards?.agent_selected === true ||
    candidate?.agent_selected === true ||
    candidate?.agent_selected_option !== undefined ||
    candidate?.agent_picked_option !== undefined;
  if (!guards || guards.agent_selected !== false || agentPicked) {
    code("agent_selected_answer", "no option may be selected by the agent");
  }

  const checkSlot = (slot, scope, allowedOptionIds, questionId) => {
    if (!slot || typeof slot !== "object") {
      code("answer_field_set_incomplete", `${scope} is missing`);
      return;
    }
    const keys = slotKeys(slot);
    const expected = [...ANSWER_FIELDS].slice().sort();
    if (JSON.stringify(keys) !== JSON.stringify(expected)) {
      code("answer_field_set_incomplete", `${scope} keys [${keys.join(",")}]`);
    }
    for (const ref of ["question_id", "question_id_ref", "criterion_id", "interaction_id"]) {
      if (typeof slot[ref] !== "string") code("reference_missing", `${scope}.${ref} must be a string`);
    }
    if (typeof slot.verbatim_response !== "string") {
      code("verbatim_missing", `${scope}.verbatim_response must be a string`);
    }
    if (typeof slot.rationale !== "string") {
      code("answer_field_set_incomplete", `${scope}.rationale must be a string`);
    }
    if (typeof slot.tested_source_revision !== "string") {
      code("stale_answer_revision", `${scope}.tested_source_revision must be a string`);
    }
    if (!OPTION_RESOLUTIONS.includes(slot.option_resolution)) {
      code("option_unresolved", `${scope}.option_resolution=${JSON.stringify(slot.option_resolution)}`);
    }
    if (slot.selected_option_id !== null && !allowedOptionIds.includes(slot.selected_option_id)) {
      code("option_unresolved", `${scope}.selected_option_id=${JSON.stringify(slot.selected_option_id)}`);
    }
    if (questionId !== undefined && slot.question_id !== questionId) {
      code("reference_missing", `${scope}.question_id does not match the packet question`);
    }
    if (questionId !== undefined && slot.question_id_ref !== questionId) {
      code("reference_missing", `${scope}.question_id_ref does not match the packet question`);
    }
    if (typeof slot.verbatim_response === "string") {
      if (slot.verbatim_response.length > maxVerbatim) {
        code("verbatim_too_long", `${scope} verbatim length ${slot.verbatim_response.length}`);
      }
      if (VERDICT_LINE_RE.test(slot.verbatim_response) || HEADING_RE.test(slot.verbatim_response)) {
        code("verbatim_field_hijack", `${scope} verbatim carries a verdict line or a heading`);
      }
    }
  };

  const irAllowed = Array.isArray(questionPacket?.ir_question?.options)
    ? questionPacket.ir_question.options.map((option) => option.option_id)
    : IR_OPTION_IDS;
  const f13Allowed = Array.isArray(questionPacket?.f13_question?.options)
    ? questionPacket.f13_question.options.map((option) => option.option_id)
    : F13_OPTION_IDS;

  const ir = candidate?.ir_answer;
  const f13 = candidate?.f13_answer;
  checkSlot(ir, "ir_answer", irAllowed, questionPacket?.ir_question?.question_id);
  checkSlot(f13, "f13_answer", f13Allowed, questionPacket?.f13_question?.question_id);

  // 6. status-specific rules.
  if (status === "answered") {
    if (answerSource !== "subjective_uat_criterion") {
      code("answer_source_not_interactive", "an answered status requires the authenticated interactive answer source");
    }
    if (typeof readback?.read_back_text !== "string" || readback.read_back_text.trim() === "") {
      code("readback_missing", "an answered status requires a non-empty read_back_text");
    }
    for (const [scope, slot] of [
      ["ir_answer", ir],
      ["f13_answer", f13],
    ]) {
      if (!slot || typeof slot !== "object") continue;
      for (const ref of ["criterion_id", "question_id", "interaction_id"]) {
        if (typeof slot[ref] !== "string" || slot[ref].trim() === "") {
          code("reference_missing", `${scope}.${ref} is empty while the status is answered`);
        }
      }
      if (typeof slot.verbatim_response !== "string" || slot.verbatim_response.trim() === "") {
        code("verbatim_missing", `${scope}.verbatim_response is empty while the status is answered`);
      }
      if (typeof slot.tested_source_revision !== "string" || slot.tested_source_revision !== candidate.source_revision) {
        code("stale_answer_revision", `${scope} was not tested against the record source revision`);
      }
      if (slot.option_resolution === "explicit_in_verbatim") {
        if (
          slot.selected_option_id === null ||
          !optionTokenPresent(slot.selected_option_id, slot.verbatim_response)
        ) {
          code("option_unresolved", `${scope} resolves no option present in its verbatim_response`);
        }
      } else {
        code("option_unresolved", `${scope} is answered but its option resolution is ${JSON.stringify(slot.option_resolution)}`);
      }
      if (slot.selected_option_id === null) {
        code("option_unresolved", `${scope} is answered with no selected option`);
      }
    }
  }

  if (status === "pending_human_decision") {
    if (answerSource !== "none") {
      code("pending_state_not_exclusive", `answer_source=${JSON.stringify(answerSource)} while the status is pending`);
    }
    for (const [scope, slot] of [
      ["ir_answer", ir],
      ["f13_answer", f13],
    ]) {
      if (!slot || typeof slot !== "object") continue;
      if (slot.selected_option_id !== null) {
        code("pending_state_not_exclusive", `${scope} selects an option while the status is pending`);
      }
      if (slot.option_resolution !== "unresolved") {
        code("pending_state_not_exclusive", `${scope} resolves an option while the status is pending`);
      }
    }
  }

  // 7. F13 is a separate decision and is never derived from the IR answer.
  const f13Status = candidate?.f13_status;
  if (!F13_STATUSES.includes(f13Status)) {
    code("f13_inferred_from_ir", `f13_status=${JSON.stringify(f13Status)}`);
  } else if (f13?.selected_option_id === null && f13Status !== "hold") {
    code("f13_inferred_from_ir", "f13_status is answered while no separate F13 option is selected");
  } else if (f13?.selected_option_id !== null && f13Status !== "answered") {
    code("f13_inferred_from_ir", "an F13 option is selected while f13_status is not answered");
  }
  if (candidate?.f13_inferred_from_ir === true) code("f13_inferred_from_ir", "the record declares an IR inference");
  if (f13?.derived_from_ir === true || f13?.inferred_from_ir === true || f13?.derived_from === "ir_answer") {
    code("f13_inferred_from_ir", "the F13 slot is marked as derived from the IR answer");
  }
  if (ir && f13 && ir.question_id === f13.question_id) {
    code("f13_inferred_from_ir", "the F13 slot shares the IR question id");
  }
  if (
    ir &&
    f13 &&
    f13.selected_option_id !== null &&
    (typeof f13.interaction_id !== "string" ||
      f13.interaction_id.trim() === "" ||
      f13.interaction_id === ir.interaction_id)
  ) {
    code("f13_inferred_from_ir", "an F13 selection carries no independent interaction reference");
  }

  return { ok: errors.length === 0, errors };
}

export function baseEnv(overrides = {}) {
  return {
    text: committedText,
    expectedSourceRevision: rebindReport.source_revision,
    packet,
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
  return validateAnswer(mutated, env).errors.map((error) => error.name);
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

contract("the answer record exists and is canonical ASCII JSON with the M210 envelope", () => {
  assert.ok(existsSync(answerAbsolute), `${ANSWER_REL} must exist`);
  assert.ok(!committedText.endsWith("\n"), "the record must carry no trailing newline");
  assert.ok(
    ![...committedText].some((character) => character.charCodeAt(0) > 0x7f),
    "the record must be ASCII-only",
  );
  assert.equal(JSON.stringify(answer), committedText, "the record must be canonical JSON that round-trips");
  assert.equal(answer.schema, SCHEMA);
  assert.equal(answer.kind, KIND);
  assert.equal(answer.milestone, MILESTONE);
  assert.equal(answer.slice, SLICE);
  assert.equal(answer.task, TASK);
  assert.deepEqual(answer.lifecycle, LIFECYCLE);
  assert.equal(answer.authoritative, false);
  assert.equal(answer.ascii_only, true);
  assert.deepEqual(answer.requirement_refs, REQUIREMENT_REFS);
  assert.equal(answer.packet_ref, PACKET_REL);
  assert.equal(answer.presentation_ref, PRESENTATION_REL);
  assert.equal(answer.max_verbatim_chars, VERBATIM_MAX);
});

contract("the clean record passes the validator with no error", () => {
  const result = validateAnswer(answer, baseEnv());
  assert.equal(result.ok, true, JSON.stringify(result.errors));
});

contract("both answer slots carry exactly the authenticated conduit field set", () => {
  const expected = [...ANSWER_FIELDS].slice().sort();
  for (const [scope, slot] of [
    ["ir_answer", answer.ir_answer],
    ["f13_answer", answer.f13_answer],
  ]) {
    assert.equal(typeof slot, "object", `${scope} must be an object`);
    assert.deepEqual(slotKeys(slot), expected, `${scope} must carry exactly the conduit field set`);
  }
  // The conduit fields are the ones named in the T02 presentation, not invented here.
  for (const field of CONDUIT_FIELDS) {
    assert.ok(
      presentationText.includes(`\`${field}\``),
      `the presentation must name the conduit field ${field}`,
    );
  }
  assert.deepEqual(answer.readback.presented_fields.slice().sort(), CONDUIT_FIELDS.slice().sort());
});

contract("the question ids and option sets are bound live to the T02 packet", () => {
  assert.equal(answer.ir_answer.question_id, packet.ir_question.question_id);
  assert.equal(answer.ir_answer.question_id_ref, packet.ir_question.question_id);
  assert.equal(answer.f13_answer.question_id, packet.f13_question.question_id);
  assert.equal(answer.f13_answer.question_id_ref, packet.f13_question.question_id);
  assert.notEqual(answer.ir_answer.question_id, answer.f13_answer.question_id);
  assert.deepEqual(
    packet.ir_question.options.map((option) => option.option_id).slice().sort(),
    IR_OPTION_IDS.slice().sort(),
  );
  assert.deepEqual(
    packet.f13_question.options.map((option) => option.option_id).slice().sort(),
    F13_OPTION_IDS.slice().sort(),
  );
  assert.equal(packet.f13_question.status_if_unanswered, "hold");
});

contract("the source revision is the T01 rebind revision, live and unchanged", () => {
  assert.match(answer.source_revision, SOURCE_REVISION_PATTERN);
  assert.equal(answer.source_revision, rebindReport.source_revision);
  assert.equal(answer.source_revision, packet.source_revision);
});

// ---------------------------------------------------------------------------
// pending honesty
// ---------------------------------------------------------------------------

contract("with no authenticated interactive answer the record is an honest pending stop", () => {
  assert.equal(answer.conduit_available, false);
  assert.equal(answer.sanctioned_stop, true);
  assert.equal(answer.answer_source, "none");
  assert.equal(answer.status, "pending_human_decision");
  assert.ok(typeof answer.pending_reason === "string" && answer.pending_reason.trim() !== "");
  for (const [scope, slot] of [
    ["ir_answer", answer.ir_answer],
    ["f13_answer", answer.f13_answer],
  ]) {
    assert.equal(slot.selected_option_id, null, `${scope} must select no option`);
    assert.equal(slot.option_resolution, "unresolved", `${scope} must resolve no option`);
    assert.equal(slot.verbatim_response, "", `${scope} must store no invented answer text`);
    assert.equal(slot.criterion_id, "", `${scope} must claim no criterion`);
    assert.equal(slot.interaction_id, "", `${scope} must claim no interaction`);
    assert.equal(slot.tested_source_revision, "", `${scope} must claim no tested revision`);
  }
  assert.equal(answer.f13_status, "hold");
});

contract("the record carries no adoption claim, no agent selection and no Review Case event", () => {
  assert.deepEqual(answer.guards, {
    review_case_events_written: 0,
    answer_treated_as_adoption: false,
    agent_selected: false,
  });
  for (const key of ADOPTION_KEYS) {
    assert.equal(answer[key], undefined, `the record must not carry ${key}`);
  }
  assert.equal(answer.semantics_adopted, undefined, "the record must not claim adopted semantics");
  assert.equal(answer.requirements_promoted, undefined, "the record must not promote a requirement");
  assert.equal(answer.agent_selected_option, undefined, "the record must not select an option");
  assert.ok(Array.isArray(answer.non_claims) && answer.non_claims.length > 0);
  assert.ok(answer.non_claims.some((claim) => /sanctioned stop/i.test(claim)));
});

contract("the pending stop is a sanctioned stop and not an error state", () => {
  // A pending record is not a failure: the validator emits no code at all, and
  // the stop is declared as sanctioned rather than as an error state.
  const result = validateAnswer(answer, baseEnv());
  assert.deepEqual(result.errors, [], JSON.stringify(result.errors));
  assert.equal(answer.sanctioned_stop, true);
  assert.ok(
    answer.non_claims.some((claim) => /sanctioned stop, not a failure and not a pass/i.test(claim)),
    "the non-claims must state that the pending state is a sanctioned stop, not a failure",
  );
  // The documented code list is the guard surface, not the emitted set: it
  // always carries every code, including the two pending-related ones.
  assert.deepEqual(answer.fail_closed_codes.slice().sort(), EMITTABLE_CODES.slice().sort());
});

// ---------------------------------------------------------------------------
// fail-closed codes
// ---------------------------------------------------------------------------

contract("every documented fail-closed code is emitted on a mutated copy", () => {
  const base = clone(answer);
  const clean = validateAnswer(base, baseEnv({ text: JSON.stringify(base) }));
  assert.equal(clean.ok, true, JSON.stringify(clean.errors));

  const emitted = new Set();
  const collect = (codes) => {
    for (const name of codes) emitted.add(name);
  };

  // A record whose status is answered and whose slots are fully filled, so the
  // mutations below isolate a single rule instead of tripping the pending rule.
  const answeredBase = clone(base);
  answeredBase.answer_source = "subjective_uat_criterion";
  answeredBase.status = "answered";
  answeredBase.conduit_available = true;
  answeredBase.readback.read_back_text = "Read back the answer exactly as given.";
  for (const [scope, optionId] of [
    ["ir_answer", "C"],
    ["f13_answer", "defer_amendment_operations"],
  ]) {
    const slot = answeredBase[scope];
    slot.criterion_id = `criterion-${scope}`;
    slot.interaction_id = `interaction-${scope}`;
    slot.selected_option_id = optionId;
    slot.option_resolution = "explicit_in_verbatim";
    slot.verbatim_response = `I choose ${optionId} as my answer.`;
    slot.rationale = "Recorded verbatim from the interactive conduit.";
    slot.tested_source_revision = answeredBase.source_revision;
  }
  answeredBase.f13_status = "answered";
  const answeredClean = validateAnswer(answeredBase, baseEnv({ text: JSON.stringify(answeredBase) }));
  assert.equal(answeredClean.ok, true, JSON.stringify(answeredClean.errors));

  // answer_field_set_incomplete: a slot loses a field or is not an object.
  const missingField = clone(base);
  delete missingField.ir_answer.rationale;
  collect(codesFor(missingField));
  const droppedSlot = clone(base);
  delete droppedSlot.f13_answer;
  collect(codesFor(droppedSlot));

  // answer_source_not_interactive: an unknown source, or an answered status
  // without the authenticated interactive source.
  const unknownSource = clone(base);
  unknownSource.answer_source = "chat_paraphrase";
  collect(codesFor(unknownSource));
  const answeredWithoutConduit = clone(answeredBase);
  answeredWithoutConduit.answer_source = "none";
  collect(codesFor(answeredWithoutConduit));

  // verbatim_missing: an answered slot carries no verbatim text.
  const noVerbatim = clone(answeredBase);
  noVerbatim.ir_answer.verbatim_response = "";
  collect(codesFor(noVerbatim));

  // readback_missing: the read-back block or its text disappears.
  const noReadback = clone(base);
  delete noReadback.readback;
  collect(codesFor(noReadback));
  const noReadbackText = clone(answeredBase);
  noReadbackText.readback.read_back_text = "";
  collect(codesFor(noReadbackText));
  const noPresentedFields = clone(base);
  noPresentedFields.readback.presented_fields = [];
  collect(codesFor(noPresentedFields));

  // reference_missing: a criterion, interaction or question reference is empty
  // while answered, or the question id moves away from the packet.
  const noCriterion = clone(answeredBase);
  noCriterion.ir_answer.criterion_id = "";
  collect(codesFor(noCriterion));
  const noInteraction = clone(answeredBase);
  noInteraction.f13_answer.interaction_id = "";
  collect(codesFor(noInteraction));
  const movedQuestion = clone(base);
  movedQuestion.ir_answer.question_id = "m210-s02-other-question";
  collect(codesFor(movedQuestion));

  // pending_state_not_exclusive: the pending state is mixed with an answer.
  const pendingWithOption = clone(base);
  pendingWithOption.ir_answer.selected_option_id = "C";
  collect(codesFor(pendingWithOption));
  const pendingWithSource = clone(base);
  pendingWithSource.answer_source = "subjective_uat_criterion";
  collect(codesFor(pendingWithSource));
  const pendingWithResolution = clone(base);
  pendingWithResolution.f13_answer.option_resolution = "explicit_in_verbatim";
  collect(codesFor(pendingWithResolution));

  // option_unresolved: the resolved option is not in the verbatim text, the
  // resolution is unknown, or the selected option is outside the option set.
  const optionNotInVerbatim = clone(answeredBase);
  optionNotInVerbatim.ir_answer.verbatim_response = "I answered something else entirely.";
  collect(codesFor(optionNotInVerbatim));
  const unknownResolution = clone(answeredBase);
  unknownResolution.ir_answer.option_resolution = "assumed";
  collect(codesFor(unknownResolution));
  const outsideOptionSet = clone(answeredBase);
  outsideOptionSet.f13_answer.selected_option_id = "D";
  collect(codesFor(outsideOptionSet));
  const answeredNoOption = clone(answeredBase);
  answeredNoOption.ir_answer.selected_option_id = null;
  collect(codesFor(answeredNoOption));

  // agent_selected_answer: the agent marks a selection.
  const agentSelected = clone(base);
  agentSelected.guards.agent_selected = true;
  collect(codesFor(agentSelected));
  const agentSelectedTop = clone(base);
  agentSelectedTop.agent_selected_option = "C";
  collect(codesFor(agentSelectedTop));

  // answer_as_automatic_adoption: the saved answer is treated as an adoption.
  const treatedAsAdoption = clone(base);
  treatedAsAdoption.guards.answer_treated_as_adoption = true;
  collect(codesFor(treatedAsAdoption));
  const adoptionKey = clone(base);
  adoptionKey.adoption = "granted";
  collect(codesFor(adoptionKey));
  const promotedRequirement = clone(base);
  promotedRequirement.requirements_promoted = 1;
  collect(codesFor(promotedRequirement));

  // f13_inferred_from_ir: the F13 outcome is derived from the IR answer.
  const f13SharedId = clone(base);
  f13SharedId.f13_answer.question_id = f13SharedId.ir_answer.question_id;
  collect(codesFor(f13SharedId));
  const f13AnsweredWithoutOption = clone(base);
  f13AnsweredWithoutOption.f13_status = "answered";
  collect(codesFor(f13AnsweredWithoutOption));
  const f13Derived = clone(base);
  f13Derived.f13_answer.derived_from_ir = true;
  collect(codesFor(f13Derived));
  const f13SharedInteraction = clone(answeredBase);
  f13SharedInteraction.f13_answer.interaction_id = f13SharedInteraction.ir_answer.interaction_id;
  collect(codesFor(f13SharedInteraction));

  // review_case_event_written: the guard is not zero.
  const reviewCaseEvent = clone(base);
  reviewCaseEvent.guards.review_case_events_written = 1;
  collect(codesFor(reviewCaseEvent));

  // raw_text_leak: an XML tag or a provider text marker.
  const rawLeak = clone(base);
  rawLeak.non_claims[0] = "leaked <screenTip>";
  collect(codesFor(rawLeak));

  // verbatim_too_long: the verbatim text exceeds the declared maximum.
  const tooLong = clone(answeredBase);
  tooLong.ir_answer.verbatim_response = `I choose C. ${"x".repeat(VERBATIM_MAX + 1)}`;
  collect(codesFor(tooLong));

  // verbatim_field_hijack: the verbatim text carries a verdict line or a heading.
  const verdictHijack = clone(answeredBase);
  verdictHijack.ir_answer.verbatim_response = "I choose C.\n**admission: granted**";
  collect(codesFor(verdictHijack));
  const headingHijack = clone(answeredBase);
  headingHijack.ir_answer.verbatim_response = "I choose C.\n## Admission";
  collect(codesFor(headingHijack));

  // stale_answer_revision: the record or an answered slot is bound to another revision.
  const movedRevision = clone(base);
  movedRevision.source_revision = `sha256:${"3".repeat(64)}`;
  collect(codesFor(movedRevision));
  const staleSlot = clone(answeredBase);
  staleSlot.ir_answer.tested_source_revision = `sha256:${"4".repeat(64)}`;
  collect(codesFor(staleSlot));

  // status_not_in_dictionary: the status is outside the closed dictionary.
  const unknownStatus = clone(base);
  unknownStatus.status = "granted";
  collect(codesFor(unknownStatus));

  // non_ascii_artifact: a non-ASCII byte.
  const nonAscii = clone(base);
  nonAscii.non_claims[0] = "dash \u2014 not ascii";
  collect(codesFor(nonAscii));

  // runtime_claim_present: a Rust implementation marker.
  const runtimeClaim = clone(base);
  runtimeClaim.non_claims[0] = "the record calls pub fn parse()";
  collect(codesFor(runtimeClaim));

  assert.deepEqual([...emitted].sort(), EMITTABLE_CODES.slice().sort());
});

contract("the documented code block equals the declared code set", () => {
  const documented = documentedBlock();
  assert.equal(new Set(documented).size, documented.length, "the documented block must carry no duplicate");
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(answer.fail_closed_codes.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.equal(EMITTABLE_CODES.length, 18);
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
    ANSWER_REL,
    CONTRACT_REL,
    REBIND_REPORT_REL,
  };
  const reads = [...source.matchAll(/readFileSync\(path\.join\(root,\s*([A-Za-z_$][\w$]*)\)/g)].map(
    (match) => match[1],
  );
  const directReads = [
    ...source.matchAll(/readFileSync\((answerAbsolute|packetAbsolute|presentationAbsolute)/g),
  ].map((match) => match[1]);
  assert.ok(reads.length + directReads.length >= 5, "the contract must read the declared artifacts");
  for (const identifier of new Set(reads)) {
    const relativePath = declared[identifier];
    assert.ok(relativePath, `readFileSync must target a declared artifact constant, got ${identifier}`);
    assert.ok(relativeExists(relativePath), `the contract reads ${relativePath}, which must exist`);
  }
  const directMap = {
    answerAbsolute: ANSWER_REL,
    packetAbsolute: PACKET_REL,
    presentationAbsolute: PRESENTATION_REL,
  };
  for (const identifier of new Set(directReads)) {
    const relativePath = directMap[identifier];
    assert.ok(relativePath, `readFileSync must target a declared artifact constant, got ${identifier}`);
    assert.ok(relativeExists(relativePath), `the contract reads ${relativePath}, which must exist`);
  }
  assert.ok(source.includes("DOCUMENTED_CODES_BEGIN"), "the documented code block must be machine-readable");
});

// ---------------------------------------------------------------------------
// markers
// ---------------------------------------------------------------------------

contract("M210 S02 answer markers", () => {
  assert.deepEqual(failures, [], "a failing case must suppress the success marker");
  process.stdout.write(
    `${CONTRACT_MARKER} answer_source=${answer.answer_source} status=${answer.status} ` +
      `codes=${EMITTABLE_CODES.length} fields=${ANSWER_FIELDS.length}\n`,
  );
});
