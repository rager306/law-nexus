// M210-3afp79 S04 T01 admission-reconciliation contract.
//
// Offline and fail-closed. The artifacts under test are
// prd/architecture/m210-s04-admission-reconciliation.json (the derived
// reconciliation) and prd/architecture/m210-s04-runtime-admission.md (the
// checkpoint). The reconciliation is bound to the superseding S02 v2 admission:
// the v2 checkpoint carries the single verdict line `admission: granted` for the
// bounded candidate layer of variant C, and the superseded v1 checkpoint and v1
// answer record stay byte-identical as history.
//
// The claims under test are that the supersession chain is intact (v1 superseded
// byte-identically, v2 current, both digest-bound), that exactly one honest
// reading is selected for S04 (authenticated_bounded_adoption,
// established-bounded-candidate-layer) while the other honest reading stays
// historical, that no repeat owner acceptance is demanded, that adoption is
// separated from activation (not-activated) and from submission authority (the
// actor-bound path is unavailable and its scope is record_human_disposition, never
// the authenticated subjective-UAT channel), that the v1 governing-surface finding
// is read as v1-scoped and non-blocking, that F13 is an explicit owner defer
// (deferred-explicit) rather than a missing answer, that the runtime stop is lifted
// for the candidate layer only, that the product footprint guards stay empty, that
// `--check` re-renders byte-identically, that both artifacts carry no runtime
// marker, no raw text and no non-ASCII byte, and that each documented fail-closed
// code is empirically emitted by a mutation.
//
// No network, no ignored path and no .gsd, .agents, .lex, .planning or .audits path
// is read as evidence, and this contract never writes a file.
//
// Run: node --test scripts/m210_s04_admission_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  ACTIVATION_STATE,
  ADMISSION,
  ADMISSION_RELATIVE_PATH,
  ADMISSION_STATE,
  ADOPTED_VARIANT,
  ADOPTED_VARIANT_LABEL,
  AUTHENTICATED_CHANNEL,
  CHECK_OK_MARKER,
  CONSUMED_BY_S03_GATE,
  CONTRACT_MARKER,
  CONTRACT_PATH,
  DECLARED_ABSENT_RUNTIME_SURFACES,
  EMITTABLE_CODES,
  F13_DEFERRED_EXPLICIT,
  KIND,
  LIFECYCLE,
  MILESTONE,
  OWNER_CRITERION,
  OWNER_CRITERION_ID,
  OWNER_INTERACTION_ID,
  OWNER_QUESTION_ID,
  RECONCILIATION_RELATIVE_PATH,
  REPO_ROOT,
  REQUIREMENT_REFS,
  REQUIRED_HEADERS,
  REQUIRED_SECTIONS,
  RUNTIME_STOP_STATE,
  RUNTIME_STOP_STILL_ACTIVE,
  S02_ANSWER_V1_PATH,
  S02_ANSWER_V2_PATH,
  S02_CHECKPOINT_V1_PATH,
  S02_CHECKPOINT_V2_PATH,
  S02_GOVERNING_PATH,
  SCHEMA,
  SCHEMA_VERSION,
  SECTION3_PATH,
  SECTION3_PIN,
  SELECTED_FOR_S04,
  SLICE,
  SOURCE_REVISION_PATTERN,
  SOURCE_REVISION_SCRIPT,
  TASK,
  V1_ADMISSION,
  V1_ADMISSION_STATE,
  V1_SELECTED_FOR_S04,
  fileLookup,
  headerValue,
  liveEnv,
  normalizePin,
  renderReconciliation,
  runAdmission,
  section,
  validateAdmissionDoc,
  validateReconciliation,
} from "./m210_s04_admission_reconcile.mjs";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// supersession_chain_broken: the v1-to-v2 chain, the two-reading set or the selected reading is not intact.
// chain_hash_mismatch: a chain digest is malformed, differs from live bytes, or disagrees with the digest the v2 source recorded.
// gate_reads_superseded_checkpoint: the S03 gate read of the superseded v1 checkpoint is not registered as historical and fixed in S03/T01.
// owner_reacceptance_demanded: a repeat owner acceptance is required or requested for an already established adoption.
// adoption_denied_despite_v2: the established bounded variant C adoption is denied, narrowed or discarded despite the granted v2 sources.
// actor_bound_scope_confused: the unavailable actor-bound path is attributed to the authenticated subjective-UAT channel, or its scope is not record_human_disposition.
// governing_surface_v1_stale_read: the v1 governing-surface finding is read as a live v2 blocker instead of a v1-scoped non-blocking record.
// adoption_read_as_activation: the bounded adoption is read as if the candidate layer had been implemented or activated.
// adoption_read_as_submission_authority: the bounded adoption is read as if it granted Review Case submission authority.
// f13_missing_answer_misread: the explicit deferred-explicit owner defer is read as a missing answer or as a hold.
// review_case_event_written: a Review Case event is written, or the event guard is non-zero, or the events directory exists.
// section3_mutated: section 3 of prd/temporal-legal-model.md no longer matches its pin, or the recorded pin is wrong.
// requirement_promoted: a requirement is promoted, or the promotion guard is non-zero.
// crate_touched: a crate or a declared runtime surface exists, the crates_touched guard is non-empty, or a runtime marker is present.
// non_ascii_artifact: an artifact carries a non-ASCII byte.
// raw_text_leak: an artifact carries an angle bracket or a provider text marker.
// check_not_byte_identical: --check rendered bytes differ from the committed report.
// runtime_stop_blanket_lifted: the runtime stop is lifted without the adopted candidate-layer bound.
// verdict_missing: the checkpoint carries no verdict line matching the admission expression.
// verdict_ambiguous: the checkpoint carries more than one verdict line.
// header_field_missing: a mandatory bold header field is absent or empty.
// section_missing: a mandatory level-## section is absent.
// DOCUMENTED_CODES_END

const root = REPO_ROOT;
const GENERATOR = "scripts/m210_s04_admission_reconcile.mjs";

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const ZERO_SHA = `sha256:${"0".repeat(64)}`;

const EXPECTED_KEYS = [
  "schema",
  "schema_version",
  "kind",
  "milestone",
  "slice",
  "task",
  "lifecycle",
  "authoritative",
  "ascii_only",
  "requirement_refs",
  "admission",
  "admission_basis",
  "selected_for_s04",
  "admission_state",
  "activation_state",
  "scope",
  "owner_admission_ref",
  "owner_admission_refs",
  "owner_choices",
  "supersession_chain",
  "readings",
  "governing_surface",
  "submission_gate",
  "runtime_stop",
  "f13_status",
  "f13_criterion_id",
  "f18",
  "consumed_by_s03_gate",
  "s03_gate",
  "declared_absent_runtime_surfaces",
  "out_of_scope_surfaces",
  "guards",
  "source_revision",
  "fail_closed_codes",
  "non_claims",
];

// ---------------------------------------------------------------------------
// live artifacts and fixtures
// ---------------------------------------------------------------------------

const reportAbsolute = path.join(root, RECONCILIATION_RELATIVE_PATH);
const committedText = readFileSync(reportAbsolute, "utf8");
const report = JSON.parse(committedText);
const liveMdText = readFileSync(path.join(root, ADMISSION_RELATIVE_PATH), "utf8");
const lookup = fileLookup(root);

// A live render that reuses the committed source revision: everything else is
// re-derived from disk, so this is the exact byte compare the --check mode makes.
const live = renderReconciliation({ rootDir: root, lookup, sourceRevision: report.source_revision });

function baseEnv(overrides = {}) {
  return liveEnv({
    rootDir: root,
    lookup,
    text: committedText,
    committedText,
    checkRevisionEcho: true,
    eventsDirExists: false,
    ...overrides,
  });
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mutated(overrides, base = report) {
  const copy = clone(base);
  overrides(copy);
  return copy;
}

function replaceHeaderValue(text, key, value) {
  const lines = text.split("\n");
  const prefix = `**${key}:**`;
  const start = lines.findIndex((line) => line.startsWith(prefix));
  assert.notEqual(start, -1, `replaceHeaderValue requires ${prefix}`);
  let end = start + 1;
  while (
    end < lines.length &&
    !lines[end].startsWith("**") &&
    !lines[end].startsWith("#") &&
    lines[end].trim() !== ""
  ) {
    end += 1;
  }
  return [...lines.slice(0, start), `${prefix} ${value}`, ...lines.slice(end)].join("\n");
}

function removeHeaderLines(text, key) {
  const lines = text.split("\n");
  const prefix = `**${key}:**`;
  const start = lines.findIndex((line) => line.startsWith(prefix));
  assert.notEqual(start, -1, `removeHeaderLines requires ${prefix}`);
  let end = start + 1;
  while (
    end < lines.length &&
    !lines[end].startsWith("**") &&
    !lines[end].startsWith("#") &&
    lines[end].trim() !== ""
  ) {
    end += 1;
  }
  return [...lines.slice(0, start), ...lines.slice(end)].join("\n");
}

function replaceSectionBody(text, heading, body) {
  const lines = text.split("\n");
  const start = lines.findIndex((line) => line === heading);
  assert.notEqual(start, -1, `replaceSectionBody requires ${heading}`);
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i += 1) {
    if (lines[i].startsWith("## ")) {
      end = i;
      break;
    }
  }
  return [...lines.slice(0, start + 1), "", body, "", ...lines.slice(end)].join("\n");
}

// Node's test runner keeps running after a failing case, so a marker printed from
// the last case would still look green on a red run. Record every failure and let
// the last case refuse to print the marker if any earlier case failed.
const failures = [];
let caseCount = 0;
function contract(title, body) {
  test(title, () => {
    caseCount += 1;
    try {
      body();
    } catch (error) {
      failures.push(title);
      throw error;
    }
  });
}

// ---------------------------------------------------------------------------
// validation harness
// ---------------------------------------------------------------------------

const observed = new Set();

function codesFor(renderedOrReport, md = liveMdText, env = {}) {
  const rep = renderedOrReport?.report ?? renderedOrReport;
  const text = renderedOrReport?.text ?? JSON.stringify(rep);
  const environment = baseEnv({ text, ...env });
  const jsonErrors = validateReconciliation(rep, environment).errors.map((entry) => entry.name);
  const mdErrors = validateAdmissionDoc(md, rep, environment).errors.map((entry) => entry.name);
  return [...jsonErrors, ...mdErrors];
}

function expectCode(renderedOrReport, expected, md = liveMdText, env = {}) {
  const codes = codesFor(renderedOrReport, md, env);
  for (const code of codes) observed.add(code);
  assert.ok(codes.includes(expected), `expected ${expected}, got ${JSON.stringify(codes)}`);
  return codes;
}

function generatorSource() {
  return readFileSync(path.join(root, GENERATOR), "utf8");
}

function contractSource() {
  return readFileSync(path.join(root, CONTRACT_PATH), "utf8");
}

function documentedBlock() {
  const source = contractSource();
  const begin = source.indexOf("DOCUMENTED_CODES_BEGIN");
  const end = source.indexOf("DOCUMENTED_CODES_END");
  assert.ok(begin > 0 && end > begin, "the documented code block must be present");
  return source
    .slice(begin, end)
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z][a-z0-9_]*): /)?.[1])
    .filter((name) => typeof name === "string");
}

// ---------------------------------------------------------------------------
// the live artifacts
// ---------------------------------------------------------------------------

contract("the reconciliation is canonical ASCII JSON with a fixed key order", () => {
  assert.ok(existsSync(reportAbsolute), `${RECONCILIATION_RELATIVE_PATH} must exist`);
  assert.ok(!committedText.endsWith("\n"), "the report must carry no trailing newline");
  assert.ok(
    [...committedText].every((character) => character.charCodeAt(0) < 0x80),
    "the report must be ASCII-only",
  );
  assert.equal(
    JSON.stringify(JSON.parse(committedText)),
    committedText,
    "the report must round-trip byte-identically",
  );
  assert.deepEqual(Object.keys(report), EXPECTED_KEYS, "the report must keep a fixed key order");
  assert.ok(!/timestamp/i.test(committedText), "the report must carry no timestamp field");
  assert.ok(!/\d{4}-\d{2}-\d{2}T/.test(committedText), "the report must carry no ISO timestamp");
  assert.equal(report.schema, SCHEMA);
  assert.equal(report.schema_version, SCHEMA_VERSION);
  assert.equal(report.kind, KIND);
  assert.equal(report.milestone, MILESTONE);
  assert.equal(report.slice, SLICE);
  assert.equal(report.task, TASK);
  assert.deepEqual(report.lifecycle, LIFECYCLE);
  assert.equal(report.authoritative, false);
  assert.equal(report.ascii_only, true);
  assert.deepEqual(report.requirement_refs, REQUIREMENT_REFS);
  assert.deepEqual(report.fail_closed_codes, EMITTABLE_CODES);
  assert.equal(EMITTABLE_CODES.length, 22);
  assert.ok(Array.isArray(report.non_claims) && report.non_claims.length >= 5);
  assert.match(report.source_revision, SOURCE_REVISION_PATTERN);
  assert.equal(live.text, committedText, "a live re-render must be byte-identical to the committed report");
  assert.deepEqual(
    validateReconciliation(report, baseEnv({ text: committedText })).errors,
    [],
    "the live report must validate clean",
  );
});

contract("the reconciliation records the established bounded variant C adoption", () => {
  assert.equal(report.admission, ADMISSION);
  assert.equal(report.selected_for_s04, SELECTED_FOR_S04);
  assert.equal(report.admission_state, ADMISSION_STATE);
  assert.equal(report.activation_state, ACTIVATION_STATE);
  assert.equal(report.scope.adopted_variant, ADOPTED_VARIANT);
  assert.equal(report.scope.adopted_variant_label, ADOPTED_VARIANT_LABEL);
  assert.equal(report.scope.bounded_to_candidate_layer, true);
  assert.equal(report.owner_admission_ref, OWNER_CRITERION);
  assert.equal(report.owner_admission_refs.criterion_id, OWNER_CRITERION_ID);
  assert.equal(report.owner_admission_refs.question_id, OWNER_QUESTION_ID);
  assert.equal(report.owner_admission_refs.interaction_id, OWNER_INTERACTION_ID);
  assert.equal(report.owner_admission_refs.channel, AUTHENTICATED_CHANNEL);
  assert.equal(report.owner_choices.reacceptance_required, false);
  assert.equal(report.owner_choices.repeat_owner_decision_requested, false);
  assert.equal(report.consumed_by_s03_gate, CONSUMED_BY_S03_GATE);
  assert.equal(report.s03_gate.reads_superseded_checkpoint, true);
  assert.equal(report.s03_gate.fixed_in, "S03/T01");
  assert.equal(report.s03_gate.rewritten, false);
  assert.equal(report.s03_gate.current_reading, "v2");
  assert.equal(report.f13_status, F13_DEFERRED_EXPLICIT);
  assert.equal(report.f18.bounded_adoption_evidence_present, true);
  assert.equal(report.f18.independent_evaluation, "pending");
  assert.equal(report.f18.ledger_disposition, "pending");
  assert.equal(report.f18.auto_close, "forbidden");
  assert.equal(report.runtime_stop.state, RUNTIME_STOP_STATE);
  assert.equal(report.runtime_stop.lifted_for, "adopted candidate layer");
  for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
    assert.ok(report.runtime_stop.still_active_for.includes(surface), `${surface} must stay stopped`);
  }
  assert.deepEqual(report.guards.crates_touched, []);
  assert.equal(report.guards.requirements_promoted, 0);
  assert.equal(report.guards.review_case_events_written, 0);
  assert.equal(report.guards.section3_pin, SECTION3_PIN);
  assert.deepEqual(report.out_of_scope_surfaces.map((entry) => entry.claimed), report.out_of_scope_surfaces.map(() => false));
  assert.deepEqual(codesFor(live, liveMdText), [], "the live pair must validate clean");
});

contract("the supersession chain preserves the v1 bytes and selects the v2 reading", () => {
  const chain = report.supersession_chain;
  assert.equal(chain.v1.path, S02_CHECKPOINT_V1_PATH);
  assert.equal(chain.v1.status, "superseded");
  assert.equal(chain.v1.admission, V1_ADMISSION);
  assert.equal(chain.v1.verdict_applies_to, "v1");
  assert.equal(chain.v2.path, S02_CHECKPOINT_V2_PATH);
  assert.equal(chain.v2.status, "current");
  assert.equal(chain.v2.admission, ADMISSION);
  assert.equal(chain.v2.supersedes, S02_CHECKPOINT_V1_PATH);
  assert.equal(chain.v1.sha256, lookup.sha256(S02_CHECKPOINT_V1_PATH));
  assert.equal(chain.v1.sha256, chain.v1.sha256_from_v2_table);
  assert.equal(chain.v2.sha256, lookup.sha256(S02_CHECKPOINT_V2_PATH));
  assert.equal(chain.answer_v1.path, S02_ANSWER_V1_PATH);
  assert.equal(chain.answer_v1.sha256, lookup.sha256(S02_ANSWER_V1_PATH));
  assert.equal(chain.answer_v1.sha256, chain.answer_v1.sha256_from_v2_binding);
  assert.equal(chain.answer_v2.path, S02_ANSWER_V2_PATH);
  assert.equal(chain.answer_v2.sha256, lookup.sha256(S02_ANSWER_V2_PATH));
  assert.equal(chain.answer_v2.status, "owner_decision_recorded");
  assert.equal(normalizePin(chain.v1.sha256_from_v2_table), "sha256:31ed55b9f5db500a40441ce642b773127b6523b016a2453038fc8648d81f7031");

  assert.equal(report.readings.length, 2);
  const [v1Reading, v2Reading] = report.readings;
  assert.equal(v1Reading.selected, false);
  assert.equal(v1Reading.honest, true);
  assert.equal(v1Reading.selected_for_s04, V1_SELECTED_FOR_S04);
  assert.equal(v1Reading.admission_state, V1_ADMISSION_STATE);
  assert.equal(v2Reading.selected, true);
  assert.equal(v2Reading.honest, true);
  assert.equal(v2Reading.selected_for_s04, SELECTED_FOR_S04);
  assert.equal(v2Reading.admission_state, ADMISSION_STATE);

  assert.equal(report.governing_surface.path, S02_GOVERNING_PATH);
  assert.equal(report.governing_surface.sha256, lookup.sha256(S02_GOVERNING_PATH));
  assert.equal(report.governing_surface.verdict, "governing_surface_absent");
  assert.equal(report.governing_surface.verdict_applies_to, "v1");
  assert.equal(report.governing_surface.blocking, false);
  assert.equal(report.submission_gate.actor_bound_path_available, false);
  assert.equal(report.submission_gate.scope, "record_human_disposition");
  assert.equal(report.submission_gate.subjective_uat_is_submission_path, false);
  assert.equal(report.submission_gate.applied, false);
});

contract("the checkpoint carries exactly one verdict line and the mandatory structure", () => {
  const verdictLines = liveMdText.split("\n").filter((line) => line.startsWith("**admission: "));
  assert.equal(verdictLines.length, 1, "exactly one verdict line");
  assert.equal(verdictLines[0], "**admission: granted**");
  for (const heading of REQUIRED_SECTIONS) {
    assert.ok(liveMdText.split("\n").includes(heading), `${heading} must be a level-## heading`);
  }
  for (const key of REQUIRED_HEADERS) {
    const value = headerValue(liveMdText, key);
    assert.ok(value !== null && value.trim() !== "", `${key} must be a non-empty header field`);
  }
  assert.equal(headerValue(liveMdText, "contract"), CONTRACT_PATH);
  assert.equal(headerValue(liveMdText, "source_revision"), report.source_revision);
  assert.equal(headerValue(liveMdText, "owner_admission_ref"), OWNER_CRITERION);
  assert.equal(headerValue(liveMdText, "selection"), SELECTED_FOR_S04);
  assert.equal(headerValue(liveMdText, "admission_state"), ADMISSION_STATE);
  assert.equal(headerValue(liveMdText, "activation_state"), ACTIVATION_STATE);
  assert.equal(headerValue(liveMdText, "review_case_events_written"), "0");
  assert.equal(headerValue(liveMdText, "requirements_promoted"), "0");
  assert.equal(headerValue(liveMdText, "section3_pin"), SECTION3_PIN);
  assert.match(headerValue(liveMdText, "f13_status"), /^deferred-explicit/);
  assert.match(headerValue(liveMdText, "submission_gate"), /actor_bound_path_available=false/);
  assert.match(headerValue(liveMdText, "runtime_stop"), /lifted for the adopted candidate-layer scope only/i);
  assert.match(headerValue(liveMdText, "runtime_stop"), /stays active for composed-rule runtime/i);
  assert.match(section(liveMdText, "## Supersession chain"), /superseded/i);
  assert.match(section(liveMdText, "## Owner choices not required"), /(?:not required|no repeat owner)/i);
  assert.deepEqual(
    validateAdmissionDoc(liveMdText, report, baseEnv()).errors,
    [],
    "the live checkpoint must validate clean",
  );
});

contract("the checkpoint is ASCII and carries no runtime or raw-text marker", () => {
  assert.ok(
    [...liveMdText].every((character) => character.charCodeAt(0) < 0x80),
    "the checkpoint must be ASCII-only",
  );
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!liveMdText.includes(marker), `the checkpoint must not carry ${marker}`);
    assert.ok(!committedText.includes(marker), `the report must not carry ${marker}`);
  }
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!liveMdText.includes(marker), `the checkpoint must not carry ${marker}`);
    assert.ok(!committedText.includes(marker), `the report must not carry ${marker}`);
  }
});

contract("--check re-renders byte-identically and prints the check marker", () => {
  const result = runAdmission(["--check"], { rootDir: root, lookup });
  assert.equal(result.exitCode, 0, JSON.stringify(result.stderr));
  assert.ok(result.stdout.includes(CHECK_OK_MARKER), "the check marker must be printed");
  assert.equal(result.text, committedText, "the check render must be byte-identical");
});

// ---------------------------------------------------------------------------
// negative: supersession chain
// ---------------------------------------------------------------------------

contract("negative: supersession chain", () => {
  expectCode(mutated((rep) => { rep.readings = [rep.readings[1]]; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { rep.supersession_chain.v2.supersedes = "prd/architecture/other.md"; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { rep.supersession_chain.v1.status = "current"; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { rep.supersession_chain.v2.admission = V1_ADMISSION; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { rep.readings[0].selected = true; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { rep.readings[1].honest = false; }), "supersession_chain_broken");
  expectCode(mutated((rep) => { delete rep.supersession_chain; }), "supersession_chain_broken");
  expectCode(live, "supersession_chain_broken", replaceSectionBody(liveMdText, "## Supersession chain", "Nothing here."));
});

contract("negative: chain digests", () => {
  expectCode(mutated((rep) => { rep.supersession_chain.v1.sha256 = ZERO_SHA; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.v2.sha256 = ZERO_SHA; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.answer_v1.sha256 = ZERO_SHA; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.answer_v2.sha256 = ZERO_SHA; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.v1.sha256 = "not-a-pin"; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.v1.sha256_from_v2_table = ZERO_SHA; }), "chain_hash_mismatch");
  expectCode(mutated((rep) => { rep.supersession_chain.answer_v1.sha256_from_v2_binding = ZERO_SHA; }), "chain_hash_mismatch");
});

// ---------------------------------------------------------------------------
// negative: S03 gate historical read, adoption and state separation
// ---------------------------------------------------------------------------

contract("negative: S03 gate superseded read stays historical", () => {
  expectCode(mutated((rep) => { rep.consumed_by_s03_gate = "current_reading"; }), "gate_reads_superseded_checkpoint");
  expectCode(mutated((rep) => { rep.s03_gate.rewritten = true; }), "gate_reads_superseded_checkpoint");
  expectCode(mutated((rep) => { rep.s03_gate.fixed_in = null; }), "gate_reads_superseded_checkpoint");
  expectCode(mutated((rep) => { rep.s03_gate.reads_superseded_checkpoint = false; }), "gate_reads_superseded_checkpoint");
  expectCode(mutated((rep) => { rep.s03_gate.current_reading = "v1"; }), "gate_reads_superseded_checkpoint");
});

contract("negative: owner reacceptance is never demanded", () => {
  expectCode(mutated((rep) => { rep.owner_choices.reacceptance_required = true; }), "owner_reacceptance_demanded");
  expectCode(mutated((rep) => { rep.owner_choices.repeat_owner_decision_requested = true; }), "owner_reacceptance_demanded");
  expectCode(live, "owner_reacceptance_demanded", replaceSectionBody(liveMdText, "## Owner choices not required", "The owner must answer again."));
});

contract("negative: the bounded variant C adoption is never denied", () => {
  expectCode(mutated((rep) => { rep.admission_state = V1_ADMISSION_STATE; }), "adoption_denied_despite_v2");
  expectCode(mutated((rep) => { rep.admission = V1_ADMISSION; }), "adoption_denied_despite_v2");
  expectCode(mutated((rep) => { rep.scope.adopted_variant = "A"; }), "adoption_denied_despite_v2");
  expectCode(live, "adoption_denied_despite_v2", liveMdText.replace("**admission: granted**", "**admission: not-adopted**"));
  expectCode(live, "adoption_denied_despite_v2", replaceHeaderValue(liveMdText, "admission_state", V1_ADMISSION_STATE));
});

contract("negative: actor-bound scope is never confused with subjective-UAT", () => {
  expectCode(mutated((rep) => { rep.submission_gate.scope = "subjective_uat"; }), "actor_bound_scope_confused");
  expectCode(mutated((rep) => { rep.submission_gate.subjective_uat_is_submission_path = true; }), "actor_bound_scope_confused");
  expectCode(mutated((rep) => { rep.governing_surface.actor_bound_scope = "subjective_uat"; }), "actor_bound_scope_confused");
});

contract("negative: the v1 governing-surface finding is never read as a live blocker", () => {
  expectCode(mutated((rep) => { rep.governing_surface.verdict_applies_to = "v2"; }), "governing_surface_v1_stale_read");
  expectCode(mutated((rep) => { rep.governing_surface.blocking = true; }), "governing_surface_v1_stale_read");
  expectCode(mutated((rep) => { rep.governing_surface.verdict = "governing_surface_present"; }), "governing_surface_v1_stale_read");
});

contract("negative: adoption is not activation and not submission authority", () => {
  expectCode(mutated((rep) => { rep.activation_state = "activated"; }), "adoption_read_as_activation");
  expectCode(live, "adoption_read_as_activation", replaceHeaderValue(liveMdText, "activation_state", "activated"));
  expectCode(mutated((rep) => { rep.submission_gate.actor_bound_path_available = true; }), "adoption_read_as_submission_authority");
  expectCode(mutated((rep) => { rep.submission_gate.applied = true; }), "adoption_read_as_submission_authority");
  expectCode(mutated((rep) => { rep.submission_gate.authority = "adoption"; }), "adoption_read_as_submission_authority");
  expectCode(live, "adoption_read_as_submission_authority", replaceHeaderValue(liveMdText, "submission_gate", "actor_bound_path_available=true"));
});

contract("negative: F13 is an explicit defer, never a missing answer", () => {
  expectCode(mutated((rep) => { rep.f13_status = "missing"; }), "f13_missing_answer_misread");
  expectCode(mutated((rep) => { rep.f13_status = "hold"; }), "f13_missing_answer_misread");
  expectCode(mutated((rep) => { delete rep.f13_status; }), "f13_missing_answer_misread");
  expectCode(live, "f13_missing_answer_misread", replaceHeaderValue(liveMdText, "f13_status", "hold"));
});

// ---------------------------------------------------------------------------
// negative: runtime stop and product footprint
// ---------------------------------------------------------------------------

contract("negative: the runtime stop stays bounded to the candidate layer", () => {
  expectCode(mutated((rep) => { rep.runtime_stop.state = "lifted"; }), "runtime_stop_blanket_lifted");
  expectCode(mutated((rep) => { rep.runtime_stop.lifted_for = "the whole runtime"; }), "runtime_stop_blanket_lifted");
  expectCode(mutated((rep) => { rep.runtime_stop.still_active_for = RUNTIME_STOP_STILL_ACTIVE.slice(0, 1); }), "runtime_stop_blanket_lifted");
});

contract("negative: product footprint guards stay empty", () => {
  expectCode(mutated((rep) => { rep.guards.crates_touched = ["crates/ln-temporal/src/x.rs"]; }), "crate_touched");
  expectCode(live, "crate_touched", liveMdText, { exists: (relative) => relative === DECLARED_ABSENT_RUNTIME_SURFACES[0] });
  expectCode(live, "crate_touched", `${liveMdText}\npub fn touch() {}\n`);
  expectCode(mutated((rep) => { rep.guards.requirements_promoted = 1; }), "requirement_promoted");
  expectCode(live, "requirement_promoted", replaceHeaderValue(liveMdText, "requirements_promoted", "1"));
  expectCode(mutated((rep) => { rep.guards.review_case_events_written = 1; }), "review_case_event_written");
  expectCode(live, "review_case_event_written", liveMdText, { eventsDirExists: true });
  expectCode(live, "review_case_event_written", replaceHeaderValue(liveMdText, "review_case_events_written", "1"));
  expectCode(mutated((rep) => { rep.guards.section3_pin = ZERO_SHA; }), "section3_mutated");
  expectCode(live, "section3_mutated", liveMdText, { section3Sha: ZERO_SHA });
  expectCode(live, "section3_mutated", replaceHeaderValue(liveMdText, "section3_pin", ZERO_SHA));
});

// ---------------------------------------------------------------------------
// negative: structure and hygiene
// ---------------------------------------------------------------------------

contract("negative: structure and hygiene codes", () => {
  expectCode(live, "non_ascii_artifact", `${liveMdText}\n\u00e9\n`);
  expectCode(live, "non_ascii_artifact", liveMdText, { text: `${committedText} \u00e9` });
  expectCode(live, "raw_text_leak", `${liveMdText}\n<raw>\n`);
  expectCode(live, "raw_text_leak", liveMdText, { text: `${committedText} <raw>` });
  expectCode(live, "check_not_byte_identical", liveMdText, { committedText: "{}" });
  expectCode(live, "verdict_missing", liveMdText.replace("**admission: granted**\n", ""));
  expectCode(live, "verdict_ambiguous", liveMdText.replace("**admission: granted**", "**admission: granted**\n**admission: granted**"));
  expectCode(live, "header_field_missing", removeHeaderLines(liveMdText, "selection"));
  expectCode(live, "section_missing", liveMdText.replace("## Resume condition", "## Renamed condition"));
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

contract("the generator spawns only the revision capture and writes exactly one file", () => {
  const source = generatorSource();
  const spawns = source.match(/spawnSync\(/g) || [];
  assert.equal(spawns.length, 1, "the generator must spawn exactly the revision capture");
  assert.ok(source.includes("[SOURCE_REVISION_SCRIPT]"), "the generator must capture the live source revision");
  assert.ok(!source.includes('spawnSync("git"'), "the generator must not run git");
  const writes = source.match(/writeFileSync\(/g) || [];
  assert.equal(writes.length, 1, "the generator must write exactly one file");
  assert.ok(source.includes("writeFileSync(reportPath, rendered.text)"));
  assert.ok(!/\bfetch\(|https?:\/\//.test(source), "the generator must be offline");
  assert.ok(source.includes("cleanTestEnv"), "the generator must strip NODE_TEST_CONTEXT for its spawn");
  assert.ok(!source.includes(["M210_S04", "VERIFY_OK"].join("_")), "the verification marker must be unreachable");
});

contract("the contract reads no ignored path and uses no synchronous shell", () => {
  const source = contractSource();
  assert.ok(!/\bexecSync\b/.test(source), "no synchronous shell may be used");
  assert.ok(!/^import\b[^\n]*"node:child_process"/m.test(source), "the contract must not import a process spawner");
  assert.ok(
    !/readFileSync\(\s*path\.join\(root,\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readFileSync\(\s*path\.join\(root,\s*"\//.test(source), "the contract must not read an absolute path");
});

// ---------------------------------------------------------------------------
// code coverage and marker
// ---------------------------------------------------------------------------

contract("CODE_COVERAGE: every documented fail-closed code is exercised", () => {
  const documented = documentedBlock();
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort(), "the documented set must equal the emittable set");
  const missing = EMITTABLE_CODES.filter((code) => !observed.has(code));
  assert.deepEqual(missing, [], `codes without a mutation: ${missing.join(", ")}`);
});

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  process.stdout.write(
    `${CONTRACT_MARKER} checks=${caseCount} codes=${EMITTABLE_CODES.length} ` +
      `chain_readings=${report.readings.length} ` +
      `selected_for_s04=${report.selected_for_s04} ` +
      `activation_state=${report.activation_state} ` +
      `submission_actor_bound=${report.submission_gate.actor_bound_path_available}\n`,
  );
});
