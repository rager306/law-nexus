// M210-3afp79 S03 T01 start-gate contract.
//
// Offline and fail-closed. The artifacts under test are
// prd/architecture/m210-s03-start-gate.json (the derived start gate) and
// prd/architecture/m210-s03-runtime-admission.md (the runtime admission
// checkpoint). The gate is bound to the superseding S02 v2 admission: the v2
// checkpoint carries the single verdict line `admission: granted` for the
// adopted candidate layer of variant C, and the superseded v1 checkpoint and v1
// answer record stay byte-identical as history.
//
// The claims under test are that exactly one verdict line matches
// /^\*\*admission: (granted|not-adopted)\*\*$/m, that the mandatory header fields
// and level-## sections are present and non-empty, that every cited S02 source
// resolves repository-relative and still hashes to its recorded digest in either
// digest spelling (bare 64-hex and `sha256:`-prefixed, normalized before
// comparison), that a grant is accepted only with the authenticated interactive
// reference recorded in the v2 answer record bound to the tested revision (a
// lock, an integrity or battery PASS, a milestone closeout, an ADR status or a
// bare name is refused), that adoption is recorded separately from execution, that
// the runtime stop is lifted for the adopted candidate layer only while the
// composed-rule runtime, the applicability runtime and any section 3 promotion
// stay stopped, that the superseded v1 bytes were not rewritten, that every
// declared runtime surface is absent and no crate module is registered, that
// section 3 of prd/temporal-legal-model.md is byte-identical to its pin, that
// out-of-scope surfaces are not claimed, that `--check` re-renders
// byte-identically, that both artifacts carry no runtime marker, no raw text and
// no non-ASCII byte, and that each documented fail-closed code is empirically
// emitted by a mutation.
//
// All subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof), `git status --porcelain` (no-write proof) and the generator's live
// `node scripts/m204_s08_source_revision.mjs` capture. No network, no ignored
// path and no `.gsd`, `.agents`, `.lex`, `.planning` or `.audits` path is read as
// evidence, and this contract never writes a file.
//
// Run: node --test scripts/m210_s03_start_gate_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  ADMISSION_RELATIVE_PATH,
  ADOPTED_CONSTRUCT_SET,
  ADOPTED_VARIANT,
  ADOPTED_VARIANT_LABEL,
  AUTHENTICATED_CHANNEL,
  AUTHENTICATED_CHANNEL_RE,
  CHECK_OK_MARKER,
  CONTRACT_MARKER,
  CONTRACT_PATH,
  DECLARED_ABSENT_RUNTIME_SURFACES,
  EMITTABLE_CODES,
  F13_DEFERRED_EXPLICIT,
  GRANTED_PERMITTED_WORK,
  INTERACTIVE_REF_RE,
  KIND,
  LIFECYCLE,
  MILESTONE,
  MIN_MD_SOURCES,
  MIN_S02_SOURCES,
  OUT_OF_SCOPE_SURFACES,
  PRINT_MARKER,
  REPO_ROOT,
  REQUIREMENT_REFS,
  RUNTIME_PERMITTED_WORK,
  RUNTIME_STOP_ACTIVE,
  RUNTIME_STOP_LIFTED,
  RUNTIME_STOP_STILL_ACTIVE,
  S02_ANSWER_PATH,
  S02_ANSWER_V1_PATH,
  S02_CHECKPOINT_PATH,
  S02_CHECKPOINT_V1_PATH,
  S02_GOVERNING_PATH,
  SCHEMA,
  SCHEMA_VERSION,
  SECTION3_PATH,
  SECTION3_PIN,
  SLICE,
  SOURCE_REVISION_PATTERN,
  SOURCE_REVISION_SCRIPT,
  START_GATE_RELATIVE_PATH,
  TASK,
  VERDICT_RE,
  WRITTEN_MARKER,
  admissionSourceRows,
  captureSourceRevision,
  declaredModuleNames,
  fileLookup,
  findModRegistrations,
  headerValue,
  isAuthenticatedChannel,
  normalizePin,
  renderStartGate,
  runStartGate,
  sha256Text,
  validateAdmissionCheckpoint,
  validateStartGate,
} from "./m210_s03_start_gate.mjs";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// verdict_missing: the checkpoint carries no verdict line matching the admission expression.
// verdict_ambiguous: the checkpoint carries more than one verdict line.
// header_field_missing: a mandatory bold header field is absent or empty.
// section_missing: a mandatory level-## section is absent.
// sources_insufficient: a source table carries fewer rows than the declared minimum.
// source_unresolved: a cited source is not repository-relative, is ignored, is absolute, traverses or does not exist.
// source_hash_mismatch: a cited source digest does not match the live file content.
// source_revision_mismatch: the source revision is absent or malformed, differs from the live capture, or the grant is not bound to the tested revision.
// admission_verdict_mismatch: the admission verdict is unknown, or it contradicts the checkpoint verdict, the permit flag or the permitted work.
// grant_without_interactive_ref: a grant lacks the authenticated interactive reference, the authenticated channel or the accepted disposition.
// grant_without_governing_surface: a grant is recorded without the v2 re-read of the governing-surface check.
// non_owner_surface_as_grantor: an ADR status, a contract PASS, a bare name or a role title is used as the basis of a grant.
// lock_as_admission: a GSD milestone lock is used as the basis of a grant.
// integrity_pass_as_admission: an integrity or battery PASS is used as the basis of a grant.
// milestone_closeout_as_admission: a milestone closeout is used as the basis of a grant.
// runtime_permitted_without_admission: the runtime is permitted, or an adopted set or variant is claimed, while admission is absent.
// runtime_stop_inverted: the runtime stop is not recorded as active while admission is absent, or the checkpoint does not state it is active.
// no_start_directive_missing: the permitted work is not the fail-closed no-start contour, or the checkpoint carries no no-start directive.
// runtime_demo_claimed: the runtime demo or the runtime work is not exactly not-proven and not-started.
// s03_surface_present: a declared runtime surface exists on disk.
// lib_rs_registration_present: a declared runtime module is registered in a crate lib.rs.
// crate_touched: the crates_touched guard is non-empty.
// requirements_promoted: the requirements_promoted guard is non-zero or a promotion is claimed.
// review_case_event_written: the Review Case event guard is non-zero.
// section3_mutated: section 3 of prd/temporal-legal-model.md no longer matches its pin, or the recorded pin is wrong.
// out_of_scope_surface_claimed: an out-of-scope surface is claimed or the declared out-of-scope set does not match the required set.
// f13_scope_borrowed: the F13 status is neither hold nor deferred-explicit, so F13 scope was borrowed.
// runtime_claim_present: an artifact carries a Rust implementation marker.
// check_not_byte_identical: --check rendered bytes differ from the committed report.
// non_ascii_artifact: an artifact carries a non-ASCII byte.
// raw_text_leak: an artifact carries an angle bracket or a provider text marker.
// v2_source_not_wired: the report does not carry the v2 binding block or the binding is incomplete.
// superseded_source_selected: a superseded v1 S02 artifact is selected as the binding source.
// superseded_hash_accepted: a digest that belongs to a superseded v1 artifact is accepted as a binding digest.
// superseded_ref_accepted: a superseded, foreign or not-yet-recorded answer reference is accepted as the owner admission ref.
// scope_overclaim: the adopted scope reaches beyond the adopted candidate layer of variant C.
// owner_decision_read_as_answered: the recorded owner_decision_recorded status is read or reported as answered.
// f13_hold_misread: the deferred-explicit F13 status is read as hold.
// source_pin_form_rejected: a digest-shaped cell is in neither accepted spelling, so no pin could be formed.
// runtime_stop_blanket_lifted: the runtime stop is lifted without the adopted candidate-layer bound.
// adoption_read_as_execution: the recorded adoption is treated as if the runtime had executed.
// execution_read_as_adoption: an execution claim, or anything other than the authenticated v2 adoption, is treated as the adoption.
// receipt_silently_rewritten: a superseded receipt is presented as preserved while its bytes moved or its binding was dropped.
// DOCUMENTED_CODES_END

const root = REPO_ROOT;
const GENERATOR = "scripts/m210_s03_start_gate.mjs";
const CONTRACT = CONTRACT_PATH;

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

// The complete set of subprocess commands this contract may spawn. The live
// source revision capture is reached through the generator's own capture path.
const CONTRACT_SPAWN_HEADS = ["git"];

// ---------------------------------------------------------------------------
// live artifacts and fixtures
// ---------------------------------------------------------------------------

const reportAbsolute = path.join(root, START_GATE_RELATIVE_PATH);
const committedText = readFileSync(reportAbsolute, "utf8");
const report = JSON.parse(committedText);
const liveMdText = readFileSync(path.join(root, ADMISSION_RELATIVE_PATH), "utf8");
const liveCheckpointText = readFileSync(path.join(root, S02_CHECKPOINT_PATH), "utf8");
const liveAnswer = JSON.parse(readFileSync(path.join(root, S02_ANSWER_PATH), "utf8"));
const liveGoverning = JSON.parse(readFileSync(path.join(root, S02_GOVERNING_PATH), "utf8"));
const liveSection3Text = readFileSync(path.join(root, SECTION3_PATH), "utf8");
const lookup = fileLookup(root);

// A live render that reuses the committed source revision: everything else is
// re-derived from disk, so this is the exact byte compare the --check mode makes.
const live = renderStartGate({ rootDir: root, lookup, sourceRevision: report.source_revision });

const VERDICT_LINE = "**admission: granted**";
const ABSENT_LINE = "**admission: not-adopted**";
const F13_CRITERION_REF = "subjective-UAT criterion 70e39300-851b-4412-a322-a8f0c51ca71c";
const INTERACTION_REF = "interaction 33333333-3333-3333-3333-333333333333";
const ZERO_SHA = `sha256:${"0".repeat(64)}`;
const MD_ANSWER_ROW_PATH = `\`${S02_ANSWER_PATH}\``;
const MD_ABSENT_ROW_PATH = "`prd/architecture/m210-s03-absent.json`";

// Tapping the superseded v1 sources is the fail-closed fallback contour: it must
// still derive the absent verdict and name the superseded selection.
const absentRender = renderStartGate({
  rootDir: root,
  lookup,
  sourceRevision: report.source_revision,
  binding: { checkpoint: S02_CHECKPOINT_V1_PATH, answer: S02_ANSWER_V1_PATH },
});
const absentReport = absentRender.report;

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

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function sha256File(relativePath) {
  return lookup.sha256(relativePath);
}

function gitStatus() {
  const spawned = spawnSync("git", ["status", "--porcelain"], {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  return `${spawned.stdout || ""}`;
}

function gitTracks(relativePath) {
  const spawned = spawnSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
    cwd: root,
    stdio: ["ignore", "ignore", "ignore"],
  });
  return spawned.status === 0;
}

function generatorSource() {
  return readFileSync(path.join(root, GENERATOR), "utf8");
}

function contractSource() {
  return readFileSync(path.join(root, CONTRACT), "utf8");
}

// Node's test runner keeps running after a failing case, so a marker printed
// from the last case would still look green on a red run. Record every failure
// and let the last case refuse to print the marker if any earlier case failed.
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

const documentedBlock = () => {
  const source = contractSource();
  const begin = source.indexOf("DOCUMENTED_CODES_BEGIN");
  const end = source.indexOf("DOCUMENTED_CODES_END");
  assert.ok(begin > 0 && end > begin, "the documented code block must be present");
  return source
    .slice(begin, end)
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z][a-z0-9_]*): /)?.[1])
    .filter((name) => typeof name === "string");
};

// ---------------------------------------------------------------------------
// validation harness
// ---------------------------------------------------------------------------

function baseEnv(overrides = {}) {
  return {
    sourceRevision: report.source_revision,
    checkRevisionEcho: true,
    section3Sha: lookup.sha256(SECTION3_PATH),
    modRegistrations: findModRegistrations(root),
    exists: lookup.exists,
    sha256: lookup.sha256,
    insideRoot: lookup.insideRoot,
    checkpointText: liveCheckpointText,
    ...overrides,
  };
}

function codesFor(renderedOrReport, md = liveMdText, env = {}) {
  const rep = renderedOrReport?.report ?? renderedOrReport;
  const text = renderedOrReport?.text ?? JSON.stringify(rep);
  const environment = baseEnv({ text, ...env });
  const startErrors = validateStartGate(rep, environment).errors.map((entry) => entry.name);
  const mdErrors = validateAdmissionCheckpoint(md, rep, environment).errors.map((entry) => entry.name);
  return [...startErrors, ...mdErrors];
}

function expectCode(renderedOrReport, expected, md = liveMdText, env = {}) {
  const codes = codesFor(renderedOrReport, md, env);
  assert.ok(codes.includes(expected), `expected ${expected}, got ${JSON.stringify(codes)}`);
  return codes;
}

function mutated(overrides, base = report) {
  const rep = clone(base);
  overrides(rep);
  return rep;
}

// ---------------------------------------------------------------------------
// the live artifacts
// ---------------------------------------------------------------------------

contract("the start gate is canonical ASCII JSON and declares the M210 envelope", () => {
  assert.ok(existsSync(reportAbsolute), `${START_GATE_RELATIVE_PATH} must exist`);
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
  assert.ok(Array.isArray(report.non_claims) && report.non_claims.length >= 5);
  assert.equal(EMITTABLE_CODES.length, 43);
  assert.equal(live.text, committedText, "a live re-render must be byte-identical to the committed report");
  assert.deepEqual(
    validateStartGate(report, baseEnv({ text: committedText })).errors,
    [],
    "the live report must validate clean",
  );
});

contract("the gate records the granted bounded candidate-layer admission", () => {
  assert.equal(report.admission_verdict, "admission_granted");
  assert.equal(report.runtime_implementation_permitted, true);
  assert.deepEqual(report.permitted_work, [GRANTED_PERMITTED_WORK]);
  assert.equal(report.adopted_variant, ADOPTED_VARIANT);
  assert.equal(report.adopted_variant_label, ADOPTED_VARIANT_LABEL);
  assert.deepEqual(report.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(report.owner_admission_ref, "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f");
  assert.equal(INTERACTIVE_REF_RE.test(report.owner_admission_ref), true);
  assert.equal(report.runtime_stop, RUNTIME_STOP_LIFTED);
  assert.equal(report.runtime_stop_scope.lifted_for, "adopted candidate layer");
  for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
    assert.ok(report.runtime_stop_scope.still_active_for.includes(surface), `${surface} must stay stopped`);
  }
  assert.equal(report.runtime_work, "not-started");
  assert.equal(report.runtime_demo, "not-proven");
  assert.equal(report.f13_status, F13_DEFERRED_EXPLICIT);
  assert.equal(report.answer_provenance.status, "owner_decision_recorded");
  assert.equal(report.answer_provenance.answer_source, "interactive");
  assert.equal(report.answer_provenance.interactive_ref_present, true);
  assert.equal(report.answer_provenance.owner_ref_matches_criterion, true);
  assert.equal(report.answer_provenance.governing_surface_verdict, "governing_surface_absent");
  assert.equal(report.answer_provenance.governing_surface_reread, "v2_supersession");
  assert.equal(report.answer_provenance.governing_blocking, false);
  assert.deepEqual(report.guards.crates_touched, []);
  assert.equal(report.guards.requirements_promoted, 0);
  assert.equal(report.guards.review_case_events_written, 0);
  assert.equal(report.guards.semantics_adopted, false);
  assert.equal(report.guards.section3_pin, SECTION3_PIN);
  assert.deepEqual(report.declared_absent_runtime_surfaces, DECLARED_ABSENT_RUNTIME_SURFACES);
  assert.deepEqual(
    report.out_of_scope_surfaces.map((entry) => entry.name),
    OUT_OF_SCOPE_SURFACES,
  );
  assert.equal(report.out_of_scope_surfaces.every((entry) => entry.claimed === false), true);
  assert.match(report.source_revision, SOURCE_REVISION_PATTERN);
});

contract("adoption is recorded separately from execution", () => {
  assert.equal(report.adoption_state.adoption_established, true);
  assert.equal(report.adoption_state.adopted_variant, ADOPTED_VARIANT);
  assert.equal(report.adoption_state.authenticated_via, "authenticated subjective-UAT v2");
  assert.equal(report.adoption_state.normative_semantics_adopted, false);
  assert.equal(report.adoption_state.section3_terms, "deferred-undefined");
  assert.equal(report.adoption_state.execution_separated, true);
  assert.equal(report.execution_state.executed, false);
  assert.equal(report.execution_state.candidates_emitted, 0);
  assert.equal(report.execution_state.conflicts, 0);
  assert.equal(report.execution_state.runtime_work, "not-started");
  assert.equal(report.execution_state.runtime_demo, "not-proven");
  assert.deepEqual(codesFor(live, liveMdText), [], "a granted-and-not-executed record must validate clean");
});

contract("the checkpoint carries exactly one verdict line and the mandatory structure", () => {
  const lines = liveMdText.split("\n").filter((line) => line.startsWith("**admission: "));
  assert.equal(lines.length, 1, "exactly one verdict line");
  assert.match(liveMdText, VERDICT_RE);
  assert.match(liveMdText, /^\*\*admission: granted\*\*$/m);
  for (const heading of [
    "## Purpose and boundary",
    "## Sources checked",
    "## Start gate verdict",
    "## Owning surfaces (declared, not created)",
    "## Non-claims",
    "## Fail-closed boundary",
    "## Marker semantics",
    "## Resume condition",
  ]) {
    assert.ok(liveMdText.split("\n").includes(heading), `${heading} must be a level-## heading`);
  }
  for (const key of [
    "recorded",
    "milestone / slice",
    "classification",
    "scope",
    "source_revision",
    "owner_admission_ref",
    "admission_basis",
    "adopted_variant",
    "adopted_construct_set",
    "runtime_stop",
    "runtime_work",
    "runtime_demo",
    "review_case_events_written",
    "requirements_promoted",
    "section3_pin",
    "f13_status",
    "contract",
  ]) {
    const value = headerValue(liveMdText, key);
    assert.ok(value !== null && value.trim() !== "", `${key} must be a non-empty header field`);
  }
  assert.equal(headerValue(liveMdText, "contract"), CONTRACT);
  assert.equal(headerValue(liveMdText, "source_revision"), report.source_revision);
  assert.equal(headerValue(liveMdText, "owner_admission_ref"), report.owner_admission_ref);
  assert.equal(headerValue(liveMdText, "adopted_variant"), "C (abstention_first_candidates_only)");
  assert.equal(headerValue(liveMdText, "adopted_construct_set"), ADOPTED_CONSTRUCT_SET.join(", "));
  assert.equal(headerValue(liveMdText, "runtime_work"), "not-started");
  assert.equal(headerValue(liveMdText, "runtime_demo"), "not-proven");
  assert.equal(headerValue(liveMdText, "review_case_events_written"), "0");
  assert.equal(headerValue(liveMdText, "requirements_promoted"), "0");
  assert.equal(headerValue(liveMdText, "section3_pin"), SECTION3_PIN);
  assert.match(headerValue(liveMdText, "f13_status"), /^deferred-explicit/);
  assert.match(headerValue(liveMdText, "runtime_stop"), /lifted for the adopted candidate-layer scope only/i);
  assert.match(headerValue(liveMdText, "runtime_stop"), /stays active for composed-rule runtime/i);
  assert.match(liveMdText, /no-start/i, "the checkpoint must carry a no-start directive");
  assert.deepEqual(
    validateAdmissionCheckpoint(liveMdText, report, baseEnv()).errors,
    [],
    "the live checkpoint must validate clean",
  );
});

contract("every cited S02 source is repository-relative and hash-bound", () => {
  assert.equal(report.s02_sources.length, MIN_S02_SOURCES, "the v2 checkpoint cites eight sources");
  assert.equal(new Set(report.s02_sources.map((row) => row.path)).size, MIN_S02_SOURCES);
  for (const row of report.s02_sources) {
    assert.ok(!row.path.startsWith("/"), `${row.path} must be repository-relative`);
    assert.ok(!row.path.split("/").includes(".."), `${row.path} must not traverse`);
    assert.ok(lookup.exists(row.path), `${row.path} must exist`);
    assert.equal(lookup.insideRoot(row.path), true, `${row.path} must resolve inside the repository`);
    assert.equal(row.verdict, "match", `${row.path} must be a bound match`);
    assert.equal(sha256File(row.path), row.recorded_sha256, `${row.path} must match its recorded digest`);
    assert.equal(row.live_sha256, row.recorded_sha256, `${row.path} live digest must equal the recorded one`);
    assert.equal(normalizePin(row.recorded_sha256), row.recorded_sha256, `${row.path} must normalize`);
    assert.ok(["bare64", "sha256_prefixed"].includes(row.pin_form), `${row.path} pin form must be known`);
  }
  assert.equal(report.s02_checkpoint.path, S02_CHECKPOINT_PATH);
  assert.equal(report.s02_checkpoint.verdict, "granted");
  assert.equal(sha256File(S02_CHECKPOINT_PATH), report.s02_checkpoint.recorded_sha256);
  assert.equal(report.s02_answer.path, S02_ANSWER_PATH);
  assert.equal(report.s02_answer.status, "owner_decision_recorded");
  assert.equal(sha256File(S02_ANSWER_PATH), report.s02_answer.recorded_sha256);

  const mdRows = admissionSourceRows(liveMdText);
  assert.ok(mdRows.length >= MIN_MD_SOURCES, `the checkpoint table must cite at least ${MIN_MD_SOURCES} sources`);
  const mdPaths = mdRows.map((row) => row.path);
  assert.equal(new Set(mdPaths).size, mdPaths.length, "the checkpoint table must carry no duplicate row");
  assert.ok(mdPaths.includes(S02_CHECKPOINT_PATH), "the checkpoint table must cite the v2 checkpoint");
  for (const row of report.s02_sources) {
    assert.ok(mdPaths.includes(row.path), `${row.path} must appear in the checkpoint table`);
  }
  for (const row of mdRows) {
    assert.equal(lookup.exists(row.path), true, `${row.path} must exist`);
    assert.equal(sha256File(row.path), row.sha256, `${row.path} must match its recorded digest`);
  }
});

contract("both digest spellings are accepted and normalized on live sources", () => {
  const bareBare = report.s02_sources.every((row) => row.pin_form === "bare64");
  assert.equal(bareBare, true, "the v2 checkpoint table uses the bare spelling");
  const mdRows = admissionSourceRows(liveMdText);
  assert.equal(
    mdRows.every((row) => row.pin_form === "sha256_prefixed"),
    true,
    "the admission table uses the prefixed spelling",
  );
  assert.deepEqual(report.source_pin_form.accepted_forms, ["bare64", "sha256_prefixed"]);
  assert.deepEqual(report.source_pin_form.checkpoint_forms, ["bare64"]);
  assert.deepEqual(report.source_pin_form.rejected, []);

  // The same v2 table in the other accepted spelling must still resolve and grant.
  const prefixedCheckpoint = liveCheckpointText.replace(/\| ([0-9a-f]{64}) \|/g, "| sha256:$1 |");
  assert.notEqual(prefixedCheckpoint, liveCheckpointText, "the fixture must change the table");
  const prefixedRender = renderStartGate({
    rootDir: root,
    lookup,
    sourceRevision: report.source_revision,
    checkpointText: prefixedCheckpoint,
  });
  assert.equal(prefixedRender.report.admission_verdict, "admission_granted");
  assert.deepEqual(
    prefixedRender.report.s02_sources.map((row) => row.recorded_sha256),
    report.s02_sources.map((row) => row.recorded_sha256),
    "normalization must produce the same digests",
  );
  assert.equal(
    prefixedRender.report.source_pin_form.checkpoint_forms.join(","),
    "sha256_prefixed",
    "the prefixed spelling must be recognized",
  );
  assert.deepEqual(codesFor(prefixedRender, liveMdText, { checkpointText: prefixedCheckpoint }), []);
});

contract("a digest-shaped pin in any other spelling is rejected by name", () => {
  const badPin = liveCheckpointText.replace(
    /(\| )([0-9a-f]{64})( \|)/,
    (match, before, digest, after) => `${before}sha256:${digest.slice(0, 60)}${after}`,
  );
  assert.notEqual(badPin, liveCheckpointText);
  const badRender = renderStartGate({
    rootDir: root,
    lookup,
    sourceRevision: report.source_revision,
    checkpointText: badPin,
  });
  assert.equal(badRender.report.source_pin_form.rejected.length, 1, "the malformed pin must be reported");
  const codes = expectCode(badRender, "source_pin_form_rejected", liveMdText, { checkpointText: badPin });
  assert.ok(codes.includes("sources_insufficient"), "the rejected row must not count as a source");
});

contract("the superseded v1 bytes are preserved and hash-bound", () => {
  const superseded = report.binding.superseded;
  assert.equal(superseded.checkpoint_v1.path, S02_CHECKPOINT_V1_PATH);
  assert.equal(superseded.checkpoint_v1.verdict, "preserved");
  assert.equal(superseded.checkpoint_v1.v1_verdict, "not-adopted");
  assert.equal(sha256File(S02_CHECKPOINT_V1_PATH), superseded.checkpoint_v1.live_sha256);
  assert.equal(superseded.checkpoint_v1.live_sha256, superseded.checkpoint_v1.expected_sha256);
  assert.equal(superseded.answer_v1.path, S02_ANSWER_V1_PATH);
  assert.equal(superseded.answer_v1.verdict, "preserved");
  assert.equal(superseded.answer_v1.v1_status, "pending_human_decision");
  assert.equal(sha256File(S02_ANSWER_V1_PATH), superseded.answer_v1.live_sha256);
  assert.equal(superseded.answer_v1.live_sha256, superseded.answer_v1.expected_sha256);
  assert.equal(superseded.answer_v1.table_sha256, superseded.answer_v1.expected_sha256);
  assert.equal(report.superseded_receipts.checkpoint_v1, S02_CHECKPOINT_V1_PATH);
  assert.equal(report.superseded_receipts.answer_v1, S02_ANSWER_V1_PATH);
  assert.ok(report.superseded_receipts.policy.includes("rewrites nothing"));
  assert.ok(
    readFileSync(path.join(root, S02_CHECKPOINT_V1_PATH), "utf8").includes(ABSENT_LINE),
    "the v1 checkpoint must still carry its original verdict",
  );
});

contract("binding the gate back to the superseded v1 sources fails closed", () => {
  assert.equal(absentReport.admission_verdict, "admission_absent");
  assert.deepEqual(absentReport.permitted_work, [RUNTIME_PERMITTED_WORK]);
  assert.equal(absentReport.runtime_implementation_permitted, false);
  assert.equal(absentReport.runtime_stop, RUNTIME_STOP_ACTIVE);
  assert.equal(absentReport.f13_status, "hold");
  assert.deepEqual(absentReport.adopted_construct_set, []);
  assert.equal(absentReport.adopted_variant, null);
  assert.equal(absentReport.owner_admission_ref, "none");
  const codes = codesFor(absentRender, liveMdText, { checkpointText: absentRender.checkpointText });
  for (const expected of ["superseded_source_selected", "superseded_ref_accepted", "superseded_hash_accepted"]) {
    assert.ok(codes.includes(expected), `binding to v1 must emit ${expected}, got ${JSON.stringify(codes)}`);
  }
});

contract("no declared runtime surface exists and no module is registered", () => {
  for (const surface of DECLARED_ABSENT_RUNTIME_SURFACES) {
    assert.equal(existsSync(path.join(root, surface)), false, `${surface} must be absent`);
    assert.equal(gitTracks(surface), false, `${surface} must not be tracked`);
  }
  const modules = declaredModuleNames();
  assert.deepEqual(
    modules.map((entry) => entry.name).sort(),
    ["bounded_semantics", "candidate_emission", "normative_candidate"],
  );
  assert.deepEqual(findModRegistrations(root), [], "no declared module may be registered");
  const batteryMarker = ["M210_S03", "VERIFY_OK"].join("_");
  assert.ok(!generatorSource().includes(batteryMarker), `${batteryMarker} must be unreachable`);
});

contract("section 3 is byte-identical to its pin", () => {
  assert.equal(sha256Text(liveSection3Text), SECTION3_PIN);
  assert.equal(sha256File(SECTION3_PATH), SECTION3_PIN);
  assert.equal(report.guards.section3_pin, SECTION3_PIN);
  assert.equal(liveGoverning.verdict, "governing_surface_absent");
  assert.equal(liveGoverning.answer_record_ref, S02_ANSWER_V1_PATH);
  assert.equal(liveGoverning.actor_bound_path_available, false);
});

contract("the grant rule refuses a grant without the authenticated interactive source", () => {
  expectCode(
    mutated((rep) => {
      rep.answer_provenance.interactive_ref_present = false;
    }),
    "grant_without_interactive_ref",
  );
  expectCode(
    mutated((rep) => {
      rep.owner_admission_ref = "none";
    }),
    "grant_without_interactive_ref",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.channel = "manual";
    }),
    "grant_without_interactive_ref",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.disposition = "rejected";
    }),
    "grant_without_interactive_ref",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.status = "pending_human_decision";
      rep.answer_provenance.status = "pending_human_decision";
    }),
    "superseded_ref_accepted",
  );
  expectCode(
    mutated((rep) => {
      rep.answer_provenance.governing_surface_reread = "not-reread";
    }),
    "grant_without_governing_surface",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.governing.answer_record_ref = S02_ANSWER_PATH;
    }),
    "grant_without_governing_surface",
  );
});

// The genuine v2 answer record carries exactly one channel value on the ir
// interactive ref. Every other spelling - a negation, a bare word, a substring,
// a case or separator variant, a padded string or an unknown value - must be
// refused by the closed channel contract. The pre-rework /authenticated/i test
// wrongly accepted `unauthenticated`, `not authenticated` and `authenticated`.
const REFUSED_CHANNELS = [
  "unauthenticated",
  "not authenticated",
  "authenticated",
  "unauthenticated subjective-UAT",
  "not authenticated subjective-UAT",
  "nauthenticated subjective-UAT",
  "authenticatedXsubjective-UAT",
  "Authenticated Subjective-UAT",
  "authenticated subjective-uat",
  "authenticated-subjective-UAT",
  "authenticated subjective-UAT extended",
  " authenticated subjective-UAT",
  "authenticated subjective-UAT ",
  "subjective-UAT",
  "manual",
  "",
];

contract("the authenticated channel is a closed exact value, not a substring match", () => {
  assert.equal(AUTHENTICATED_CHANNEL, "authenticated subjective-UAT");
  assert.equal(isAuthenticatedChannel(AUTHENTICATED_CHANNEL), true);
  assert.equal(AUTHENTICATED_CHANNEL_RE.test(AUTHENTICATED_CHANNEL), true);
  assert.equal(
    AUTHENTICATED_CHANNEL_RE.test(`${AUTHENTICATED_CHANNEL}\n`),
    false,
    "the anchored contract must not match a trailing newline",
  );
  for (const value of REFUSED_CHANNELS) {
    assert.equal(isAuthenticatedChannel(value), false, `${JSON.stringify(value)} must be refused`);
    assert.equal(
      AUTHENTICATED_CHANNEL_RE.test(String(value)),
      false,
      `${JSON.stringify(value)} must not match the anchored channel contract`,
    );
  }
  assert.equal(isAuthenticatedChannel(null), false);
  assert.equal(isAuthenticatedChannel(undefined), false);
  assert.equal(isAuthenticatedChannel(42), false);
});

contract("the report validator refuses every non-genuine channel spelling", () => {
  for (const value of REFUSED_CHANNELS) {
    expectCode(
      mutated((rep) => {
        rep.binding.answer.channel = value;
      }),
      "grant_without_interactive_ref",
    );
    expectCode(
      mutated((rep) => {
        rep.answer_provenance.channel = value;
      }),
      "grant_without_interactive_ref",
    );
  }
  // Only the exact genuine value keeps the granted record clean.
  const genuine = mutated((rep) => {
    rep.binding.answer.channel = AUTHENTICATED_CHANNEL;
    rep.answer_provenance.channel = AUTHENTICATED_CHANNEL;
  });
  assert.deepEqual(codesFor(genuine), []);
});

contract("channel recognition in derivation refuses negation, substrings and unknown strings", () => {
  for (const value of REFUSED_CHANNELS) {
    const answer = clone(liveAnswer);
    answer.interactive_refs.ir.channel = value;
    const rendered = renderStartGate({
      rootDir: root,
      lookup,
      sourceRevision: report.source_revision,
      answer,
    });
    assert.equal(
      rendered.report.admission_verdict,
      "admission_absent",
      `channel ${JSON.stringify(value)} must not derive a grant`,
    );
    assert.equal(
      rendered.report.answer_provenance.interactive_ref_present,
      false,
      `channel ${JSON.stringify(value)} must not count as an authenticated direction`,
    );
    assert.equal(rendered.report.runtime_implementation_permitted, false);
    assert.equal(rendered.report.binding.answer.channel, value);
  }
  const genuine = renderStartGate({
    rootDir: root,
    lookup,
    sourceRevision: report.source_revision,
    answer: clone(liveAnswer),
  });
  assert.equal(genuine.report.admission_verdict, "admission_granted");
  assert.equal(genuine.report.answer_provenance.interactive_ref_present, true);
  assert.equal(genuine.report.answer_provenance.channel, AUTHENTICATED_CHANNEL);
});

contract("a lock, an integrity result, a closeout or an ADR status is never the basis of a grant", () => {
  const cases = [
    ["lock_as_admission", `D499 GSD_MILESTONE_LOCK authorises this adoption (${INTERACTION_REF}).`],
    [
      "integrity_pass_as_admission",
      `The M206 runtime battery integrity PASS authorises this adoption (${INTERACTION_REF}).`,
    ],
    [
      "milestone_closeout_as_admission",
      `The M210 milestone closeout authorises this adoption (${INTERACTION_REF}).`,
    ],
    ["non_owner_surface_as_grantor", `The ADR-0028 Accepted status authorises this adoption (${INTERACTION_REF}).`],
  ];
  for (const [code, basis] of cases) {
    expectCode(report, code, liveMdText, { grantBasisText: basis });
  }
});

contract("--check re-renders byte-identically and writes nothing", () => {
  const before = gitStatus();
  const run = runStartGate(["--check"], { rootDir: root, lookup });
  const after = gitStatus();
  assert.equal(after, before, "--check must not change the worktree");
  assert.equal(run.exitCode, 0, run.stderr.join("\n"));
  assert.ok(run.stdout.includes(CHECK_OK_MARKER), "the check marker must be printed");
  assert.equal(run.wrote, false);
});

contract("--print captures a live revision without writing the report", () => {
  const before = gitStatus();
  const run = runStartGate(["--print"], { rootDir: root, lookup });
  const after = gitStatus();
  assert.equal(after, before, "--print must not change the worktree");
  assert.equal(run.exitCode, 0, run.stderr.join("\n"));
  assert.equal(run.wrote, false);
  assert.ok(run.stderr.includes(PRINT_MARKER), "the print marker must be printed");
  const printed = JSON.parse(run.stdout.join("\n"));
  assert.match(printed.source_revision, SOURCE_REVISION_PATTERN);
  assert.equal(printed.admission_verdict, "admission_granted");
  assert.equal(printed.s02_sources.length, MIN_S02_SOURCES);
});

contract("write mode validates and would write exactly the report", () => {
  const before = gitStatus();
  const run = runStartGate(["--write"], { rootDir: root, lookup, dryRun: true });
  const after = gitStatus();
  assert.equal(after, before, "a dry-run write must not change the worktree");
  assert.equal(run.exitCode, 0, run.stderr.join("\n"));
  assert.equal(run.wrote, false);
  assert.ok(run.stdout.includes(WRITTEN_MARKER), "the write marker must be printed");
  // Write mode captures a fresh snapshot revision, so the re-render is compared
  // field by field rather than byte for byte.
  const reparsed = JSON.parse(run.text);
  assert.equal(JSON.stringify(reparsed), run.text, "the write render must be canonical JSON");
  assert.equal(reparsed.admission_verdict, report.admission_verdict);
  assert.equal(reparsed.runtime_implementation_permitted, report.runtime_implementation_permitted);
  assert.equal(reparsed.runtime_stop, report.runtime_stop);
  assert.deepEqual(reparsed.s02_sources, report.s02_sources);
  assert.deepEqual(reparsed.guards, report.guards);
  assert.match(reparsed.source_revision, SOURCE_REVISION_PATTERN);
});

contract("the live source revision capture path works and is never hardcoded", () => {
  const captured = captureSourceRevision(root);
  assert.match(captured, SOURCE_REVISION_PATTERN, "the capture path must return sha256:<64hex>");
  const source = generatorSource();
  const literals = source.match(/sha256:[0-9a-f]{64}/g) || [];
  assert.deepEqual(literals, [SECTION3_PIN], "the only stored digest may be the section 3 pin");
  assert.equal(SOURCE_REVISION_SCRIPT, "scripts/m204_s08_source_revision.mjs");
});

contract("both artifacts carry no runtime marker, no raw text and no non-ASCII byte", () => {
  for (const [label, text] of [
    ["report", committedText],
    ["checkpoint", liveMdText],
  ]) {
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!text.includes(marker), `${label}: runtime marker ${marker} must be absent`);
    }
    for (const marker of RAW_TEXT_MARKERS) {
      assert.ok(!text.includes(marker), `${label}: raw text marker ${marker} must be absent`);
    }
    assert.ok(
      [...text].every((character) => character.charCodeAt(0) < 0x80),
      `${label} must be ASCII-only`,
    );
  }
});

// ---------------------------------------------------------------------------
// fail-closed codes
// ---------------------------------------------------------------------------

contract("the documented code set equals the declared code set", () => {
  const documented = documentedBlock();
  assert.equal(new Set(documented).size, documented.length, "the documented block must carry no duplicate");
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.equal(EMITTABLE_CODES.length, 43);
  const boundary = liveMdText.slice(liveMdText.indexOf("## Fail-closed boundary"));
  for (const code of EMITTABLE_CODES) {
    assert.ok(boundary.includes(`\`${code}\``), `${code} must be documented in the checkpoint boundary`);
  }
});

const CODE_COVERAGE = [
  {
    code: "verdict_missing",
    md: () => liveMdText.replace(VERDICT_LINE, "**admission_state: pending**"),
  },
  { code: "verdict_ambiguous", md: () => liveMdText.replace(VERDICT_LINE, `${VERDICT_LINE}\n${ABSENT_LINE}`) },
  { code: "header_field_missing", md: () => replaceHeaderValue(liveMdText, "recorded", "") },
  { code: "section_missing", md: () => liveMdText.replace("## Marker semantics", "## Marker semantics note") },
  {
    code: "sources_insufficient",
    report: () => mutated((rep) => { rep.s02_sources = []; }),
  },
  {
    code: "source_unresolved",
    report: () => mutated((rep) => { rep.s02_sources[0].path = "prd/architecture/m210-s03-absent.md"; }),
  },
  {
    code: "source_hash_mismatch",
    report: () => mutated((rep) => { rep.s02_sources[0].recorded_sha256 = ZERO_SHA; }),
  },
  {
    code: "source_revision_mismatch",
    report: () => mutated((rep) => { rep.source_revision = "deadbeef"; }),
  },
  {
    code: "admission_verdict_mismatch",
    report: () => mutated((rep) => { rep.admission_verdict = "bogus"; }),
  },
  {
    code: "grant_without_interactive_ref",
    report: () => mutated((rep) => { rep.binding.answer.channel = "unauthenticated"; }),
  },
  {
    code: "grant_without_governing_surface",
    report: () => mutated((rep) => { rep.answer_provenance.governing_surface_reread = "not-reread"; }),
  },
  {
    code: "non_owner_surface_as_grantor",
    env: { grantBasisText: `The ADR-0028 Accepted status authorises this adoption (${INTERACTION_REF}).` },
  },
  {
    code: "lock_as_admission",
    env: { grantBasisText: `D499 GSD_MILESTONE_LOCK authorises this adoption (${INTERACTION_REF}).` },
  },
  {
    code: "integrity_pass_as_admission",
    env: { grantBasisText: "The M206 runtime battery integrity PASS authorises this adoption." },
  },
  {
    code: "milestone_closeout_as_admission",
    env: { grantBasisText: "The M210 milestone closeout authorises this adoption." },
  },
  {
    code: "runtime_permitted_without_admission",
    report: () => mutated((rep) => { rep.runtime_implementation_permitted = true; }, absentReport),
  },
  {
    code: "runtime_stop_inverted",
    report: () =>
      mutated((rep) => {
        rep.admission_verdict = "admission_absent";
        rep.runtime_implementation_permitted = false;
        rep.runtime_stop = RUNTIME_STOP_ACTIVE;
      }),
    md: () => replaceHeaderValue(liveMdText, "runtime_stop", "lifted for the bounded semantic runtime."),
  },
  {
    code: "no_start_directive_missing",
    md: () => replaceSectionBody(liveMdText, "## Start gate verdict", "The gate records the derived verdict only."),
  },
  {
    code: "runtime_demo_claimed",
    report: () => mutated((rep) => { rep.runtime_demo = "proven"; }, absentReport),
  },
  { code: "s03_surface_present", env: { exists: () => true } },
  { code: "lib_rs_registration_present", env: { modRegistrations: ["candidate_emission"] } },
  {
    code: "crate_touched",
    report: () => mutated((rep) => { rep.guards.crates_touched = ["crates/ln-temporal/src/domain.rs"]; }),
  },
  { code: "requirements_promoted", report: () => mutated((rep) => { rep.guards.requirements_promoted = 1; }) },
  {
    code: "review_case_event_written",
    report: () => mutated((rep) => { rep.guards.review_case_events_written = 1; }),
  },
  {
    code: "section3_mutated",
    report: () => mutated((rep) => { rep.guards.section3_pin = ZERO_SHA; }),
  },
  {
    code: "out_of_scope_surface_claimed",
    report: () => mutated((rep) => { rep.out_of_scope_surfaces[0].claimed = true; }),
  },
  { code: "f13_scope_borrowed", report: () => mutated((rep) => { rep.f13_status = "answered"; }) },
  { code: "runtime_claim_present", md: () => `${liveMdText}\npub fn activate() {}\n` },
  { code: "check_not_byte_identical", env: { committedText: `${committedText} ` } },
  { code: "non_ascii_artifact", md: () => `${liveMdText}\n\u041d\u043e\u0440\u043c\u0430\n` },
  { code: "raw_text_leak", md: () => `${liveMdText}\n<p>raw</p>\n` },
  {
    code: "v2_source_not_wired",
    report: () => {
      const rep = clone(report);
      delete rep.binding;
      return rep;
    },
  },
  {
    code: "superseded_source_selected",
    report: () => mutated((rep) => { rep.binding.checkpoint.path = S02_CHECKPOINT_V1_PATH; }),
  },
  {
    code: "superseded_hash_accepted",
    report: () =>
      mutated((rep) => {
        rep.binding.answer.recorded_sha256 = rep.binding.superseded.answer_v1.live_sha256;
      }),
  },
  {
    code: "superseded_ref_accepted",
    report: () => mutated((rep) => { rep.owner_admission_ref = F13_CRITERION_REF; }),
  },
  {
    code: "scope_overclaim",
    report: () => mutated((rep) => { rep.binding.checkpoint.scope_bounded_to_variant_c = false; }),
  },
  {
    code: "owner_decision_read_as_answered",
    report: () => mutated((rep) => { rep.answer_provenance.status = "answered"; }),
  },
  { code: "f13_hold_misread", report: () => mutated((rep) => { rep.f13_status = "hold"; }) },
  {
    code: "source_pin_form_rejected",
    report: () => mutated((rep) => { rep.binding.superseded.answer_v1.expected_sha256 = "efc1b820"; }),
  },
  { code: "runtime_stop_blanket_lifted", report: () => mutated((rep) => { rep.runtime_stop = "lifted"; }) },
  {
    code: "adoption_read_as_execution",
    report: () => mutated((rep) => { rep.execution_state.executed = true; }),
  },
  {
    code: "execution_read_as_adoption",
    report: () => mutated((rep) => { rep.adoption_state.adoption_established = false; }),
  },
  {
    code: "receipt_silently_rewritten",
    report: () => mutated((rep) => { rep.binding.superseded.answer_v1.verdict = "rewritten"; }),
  },
];

contract("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const rendered = entry.rendered ? entry.rendered() : entry.report ? entry.report() : report;
    const md = entry.md ? entry.md() : liveMdText;
    if (entry.report) {
      assert.notDeepEqual(rendered, report, `${entry.code}: the mutation must change the report`);
    }
    if (entry.md) {
      assert.notEqual(md, liveMdText, `${entry.code}: the mutation must change the checkpoint`);
    }
    if (entry.env?.modRegistrations) {
      assert.notDeepEqual(findModRegistrations(root), entry.env.modRegistrations);
    }
    const codes = codesFor(rendered, md, entry.env ?? {});
    assert.ok(codes.includes(entry.code), `${entry.code} must be emitted, got ${JSON.stringify(codes)}`);
    covered.add(entry.code);
  }
  assert.deepEqual([...covered].sort(), EMITTABLE_CODES.slice().sort(), "every emittable code must be covered");
  assert.deepEqual(
    CODE_COVERAGE.map((entry) => entry.code).slice().sort(),
    EMITTABLE_CODES.slice().sort(),
    "the coverage registry must carry exactly one entry per code",
  );
});

// ---------------------------------------------------------------------------
// negative: sources, structure and grant provenance
// ---------------------------------------------------------------------------

contract("negative: unresolvable and mismatched source references", () => {
  expectCode(
    mutated((rep) => { rep.s02_sources[0].path = ".agents/skills/x/SKILL.md"; }),
    "source_unresolved",
  );
  expectCode(
    mutated((rep) => { rep.s02_sources[0].path = `/${["tmp", "m210-s03.json"].join("/")}`; }),
    "source_unresolved",
  );
  expectCode(
    mutated((rep) => { rep.s02_sources[0].path = "prd/architecture/../../etc/passwd"; }),
    "source_unresolved",
  );
  expectCode(
    mutated((rep) => { rep.s02_checkpoint.path = "prd/architecture/m210-s03-absent.md"; }),
    "source_unresolved",
  );
  expectCode(mutated((rep) => { rep.s02_sources[0].verdict = "unresolved"; }), "source_hash_mismatch");
  expectCode(report, "source_unresolved", liveMdText.replace(MD_ANSWER_ROW_PATH, MD_ABSENT_ROW_PATH));
  expectCode(
    report,
    "source_hash_mismatch",
    liveMdText.replace(report.binding.answer.live_sha256, ZERO_SHA),
  );
});

contract("negative: the checkpoint verdict and the report verdict must agree", () => {
  expectCode(report, "admission_verdict_mismatch", liveMdText.replace(VERDICT_LINE, ABSENT_LINE));
  expectCode(absentRender, "admission_verdict_mismatch", liveMdText);
});

contract("negative: the candidate-layer bound cannot be softened or widened", () => {
  expectCode(mutated((rep) => { rep.adopted_construct_set.push("rule_composition"); }), "scope_overclaim");
  expectCode(mutated((rep) => { rep.adoption_state.adopted_variant = "A"; }), "execution_read_as_adoption");
  expectCode(mutated((rep) => { rep.adopted_variant_label = "full_normative_runtime"; }), "scope_overclaim");
  expectCode(
    mutated((rep) => { rep.runtime_stop_scope.lifted_for = "the whole bounded semantic runtime"; }),
    "runtime_stop_blanket_lifted",
  );
  expectCode(
    mutated((rep) => { rep.runtime_stop_scope.still_active_for = ["composed-rule runtime"]; }),
    "runtime_stop_blanket_lifted",
  );
  expectCode(report, "runtime_stop_blanket_lifted", replaceHeaderValue(liveMdText, "runtime_stop", "lifted."));
  expectCode(report, "scope_overclaim", replaceHeaderValue(liveMdText, "adopted_variant", "none"));
  expectCode(report, "scope_overclaim", replaceHeaderValue(liveMdText, "adopted_construct_set", "candidate_emission"));
});

contract("negative: the superseded history cannot be rewritten", () => {
  assert.equal(codesFor(live).includes("receipt_silently_rewritten"), false);
  expectCode(
    mutated((rep) => { rep.superseded_receipts.answer_v1 = S02_ANSWER_PATH; }),
    "receipt_silently_rewritten",
  );
  expectCode(
    mutated((rep) => { rep.binding.superseded.checkpoint_v1.expected_sha256 = "31ed55b9f5db"; }),
    "source_pin_form_rejected",
  );
  expectCode(
    mutated((rep) => { rep.binding.superseded.answer_v1.table_sha256 = ZERO_SHA; }),
    "superseded_hash_accepted",
  );
  expectCode(
    mutated((rep) => { rep.binding.answer.supersedes_path = S02_CHECKPOINT_V1_PATH; }),
    "superseded_ref_accepted",
  );
});

contract("negative: section 3 and the guard headers", () => {
  expectCode(report, "section3_mutated", liveMdText, { section3Sha: `${SECTION3_PIN}x` });
  expectCode(report, "requirements_promoted", replaceHeaderValue(liveMdText, "requirements_promoted", "2"));
  expectCode(report, "review_case_event_written", replaceHeaderValue(liveMdText, "review_case_events_written", "1"));
  expectCode(mutated((rep) => { rep.out_of_scope_surfaces = []; }), "out_of_scope_surface_claimed");
  expectCode(mutated((rep) => { rep.out_of_scope_surfaces[3].name = "F13 grammar"; }), "out_of_scope_surface_claimed");
  expectCode(report, "f13_hold_misread", replaceHeaderValue(liveMdText, "f13_status", "hold"));
  expectCode(report, "f13_scope_borrowed", replaceHeaderValue(liveMdText, "f13_status", "resolved"));
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

contract("the contract uses only the allowed subprocesses and reads no ignored path", () => {
  const source = contractSource();
  const heads = [...source.matchAll(/spawnSync\(\s*([A-Za-z_$][\w$]*(?:\.[\w$]+)*|"[^"]*")/g)]
    .map((match) => match[1])
    .map((head) => (head.startsWith('"') && head.endsWith('"') ? head.slice(1, -1) : head));
  assert.ok(heads.length >= 2, "the contract must spawn the git probes");
  for (const head of heads) {
    assert.ok(
      CONTRACT_SPAWN_HEADS.includes(head),
      `spawnSync head ${head} is outside the allowed set ${CONTRACT_SPAWN_HEADS.join(", ")}`,
    );
  }
  assert.ok(source.includes('["ls-files", "--error-unmatch"'), "tracked-file proof is required");
  assert.ok(source.includes('["status", "--porcelain"]'), "no-write proof is required");
  assert.ok(source.includes("captureSourceRevision"), "live source revision capture is required");
  assert.ok(!/\bchild_process\b.*\bexecSync\b/s.test(source), "no synchronous shell may be used");
  assert.ok(
    !/readFileSync\(\s*path\.join\(root,\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readFileSync\(\s*path\.join\(root,\s*"\//.test(source), "the contract must not read an absolute path");
});

contract("the generator spawns only the revision capture and writes only the report", () => {
  const source = generatorSource();
  const spawns = source.match(/spawnSync\(/g) || [];
  assert.equal(spawns.length, 1, "the generator must spawn exactly the revision capture");
  assert.ok(source.includes("[SOURCE_REVISION_SCRIPT]"), "the generator must capture the live source revision");
  assert.ok(!source.includes('spawnSync("git"'), "the generator must not run git");
  const writes = source.match(/writeFileSync\(/g) || [];
  assert.equal(writes.length, 1, "the generator must write exactly one file");
  assert.ok(source.includes("writeFileSync(reportPath, rendered.text)"));
  assert.ok(!/\bfetch\(|https?:\/\//.test(source), "the generator must be offline");
  assert.ok(!source.includes(["M210_S03", "VERIFY_OK"].join("_")), "the verification marker must be unreachable");
});

// ---------------------------------------------------------------------------
// marker
// ---------------------------------------------------------------------------

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  process.stdout.write(
    `${CONTRACT_MARKER} checks=${caseCount} codes=${EMITTABLE_CODES.length} ` +
      `sources=${report.s02_sources.length + 1} gate_admission=${report.admission_verdict} ` +
      `runtime_implementation_permitted=${report.runtime_implementation_permitted} ` +
      `owner_ref_bound=${report.answer_provenance.owner_ref_matches_criterion}\n`,
  );
});
