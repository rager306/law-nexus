// M210-3afp79 S03 T01 adoption-v2 integration contract.
//
// Offline integration contract for the v2 rebind of the S03 start gate. It binds
// the claims of the rebind to live data rather than to declarations:
//
//   * the gate reads the superseding sources
//     prd/architecture/m210-s02-adoption-checkpoint-v2.md and
//     prd/architecture/m210-s02-answer-record-v2.json, and records the owner
//     admission ref of the authenticated subjective-UAT criterion that the v2
//     answer record carries;
//   * the adopted scope is exactly the candidate layer of variant C, the runtime
//     stop is lifted for that layer only, and F13 is deferred-explicit (never
//     read as hold) while the recorded status stays owner_decision_recorded
//     (never read as answered);
//   * adoption and execution stay separate states: the grant is recorded, nothing
//     was executed and no candidate was emitted;
//   * the superseded v1 S02 checkpoint and v1 answer record stay byte-identical
//     to the digests the v2 records bind, and the earlier S03 receipts are named
//     as superseded rather than rewritten;
//   * both digest spellings are accepted and normalized, and a digest-shaped pin
//     in any other spelling is rejected by name;
//   * re-pointing the gate at the superseded v1 sources fails closed.
//
// Every negative claim is exercised by an in-memory mutation or by an injected
// source text; no file is written and no real artifact is modified.
//
// Run: node --test scripts/m210_s03_adoption_v2_contract.test.mjs

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  ADOPTED_CONSTRUCT_SET,
  ADOPTED_VARIANT,
  ADOPTED_VARIANT_LABEL,
  ADMISSION_RELATIVE_PATH,
  EMITTABLE_CODES,
  EXCLUDED_CONSTRUCT_SET,
  F13_DEFERRED_EXPLICIT,
  INTERACTIVE_REF_RE,
  MIN_S02_SOURCES,
  OWNER_DECISION_RECORDED,
  RUNTIME_STOP_LIFTED,
  RUNTIME_STOP_STILL_ACTIVE,
  S02_ANSWER_PATH,
  S02_ANSWER_V1_PATH,
  S02_CHECKPOINT_PATH,
  S02_CHECKPOINT_V1_PATH,
  SCHEMA_VERSION,
  S02_GOVERNING_PATH,
  START_GATE_RELATIVE_PATH,
  fileLookup,
  findModRegistrations,
  normalizePin,
  parseAnswerRecord,
  parseSourceTable,
  renderStartGate,
  validateAdmissionCheckpoint,
  validateStartGate,
} from "./m210_s03_start_gate.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const lookup = fileLookup(root);
const report = JSON.parse(readFileSync(path.join(root, START_GATE_RELATIVE_PATH), "utf8"));
const mdText = readFileSync(path.join(root, ADMISSION_RELATIVE_PATH), "utf8");
const checkpointText = readFileSync(path.join(root, S02_CHECKPOINT_PATH), "utf8");
const answerRecord = JSON.parse(readFileSync(path.join(root, S02_ANSWER_PATH), "utf8"));
const v1CheckpointText = readFileSync(path.join(root, S02_CHECKPOINT_V1_PATH), "utf8");
const v1AnswerRecord = JSON.parse(readFileSync(path.join(root, S02_ANSWER_V1_PATH), "utf8"));
const governing = JSON.parse(readFileSync(path.join(root, S02_GOVERNING_PATH), "utf8"));

const IR_CRITERION_REF = "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f";
const F13_CRITERION_REF = "subjective-UAT criterion 70e39300-851b-4412-a322-a8f0c51ca71c";
const MARKER = "M210_S03_ADOPTION_V2_OK";

// Render once on live data. This is the real positive integration path: the
// generator reads v2 from disk, re-hashes every cited source and derives the gate.
const live = renderStartGate({ rootDir: root, lookup, sourceRevision: report.source_revision });

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mutated(overrides) {
  const rep = clone(report);
  overrides(rep);
  return rep;
}

function env(overrides = {}) {
  return {
    sourceRevision: report.source_revision,
    checkRevisionEcho: true,
    section3Sha: lookup.sha256("prd/temporal-legal-model.md"),
    modRegistrations: findModRegistrations(root),
    exists: lookup.exists,
    sha256: lookup.sha256,
    insideRoot: lookup.insideRoot,
    checkpointText,
    text: JSON.stringify(report),
    ...overrides,
  };
}

function codesFor(renderedOrReport, md = mdText, overrides = {}) {
  const rep = renderedOrReport?.report ?? renderedOrReport;
  const text = renderedOrReport?.text ?? JSON.stringify(rep);
  const environment = env({ text, ...overrides });
  return [
    ...validateStartGate(rep, environment).errors.map((entry) => entry.name),
    ...validateAdmissionCheckpoint(md, rep, environment).errors.map((entry) => entry.name),
  ];
}

function expectCode(renderedOrReport, expected, md = mdText, overrides = {}) {
  const codes = codesFor(renderedOrReport, md, overrides);
  assert.ok(codes.includes(expected), `expected ${expected}, got ${JSON.stringify(codes)}`);
  return codes;
}

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
// the v2 binding is real, not declared
// ---------------------------------------------------------------------------

contract("the gate is wired to the superseding v2 sources", () => {
  assert.equal(report.schema_version, SCHEMA_VERSION);
  assert.equal(report.binding.checkpoint.path, S02_CHECKPOINT_PATH);
  assert.equal(report.binding.answer.path, S02_ANSWER_PATH);
  assert.equal(report.binding.governing.path, S02_GOVERNING_PATH);
  assert.equal(report.s02_checkpoint.path, S02_CHECKPOINT_PATH);
  assert.equal(report.s02_answer.path, S02_ANSWER_PATH);
  assert.notEqual(report.s02_checkpoint.path, S02_CHECKPOINT_V1_PATH);
  assert.notEqual(report.s02_answer.path, S02_ANSWER_V1_PATH);
  assert.equal(report.binding.checkpoint.recorded_sha256, lookup.sha256(S02_CHECKPOINT_PATH));
  assert.equal(report.binding.answer.recorded_sha256, lookup.sha256(S02_ANSWER_PATH));
  assert.equal(report.admission_verdict, "admission_granted");
  assert.equal(report.binding.checkpoint.verdict, "granted");
  assert.equal(report.s02_sources.length, MIN_S02_SOURCES);
  assert.equal(report.s02_sources.every((row) => row.verdict === "match"), true);
  assert.deepEqual(codesFor(live), [], "the live v2 binding must validate clean");
});

contract("the owner admission ref is the criterion the v2 answer record carries", () => {
  const parsed = parseAnswerRecord(answerRecord);
  assert.equal(parsed.status, OWNER_DECISION_RECORDED);
  assert.equal(parsed.answerSource, "interactive");
  assert.equal(parsed.irRef, IR_CRITERION_REF);
  assert.equal(parsed.f13Ref, F13_CRITERION_REF);
  assert.equal(parsed.channel, "authenticated subjective-UAT");
  assert.equal(parsed.disposition, "accepted");
  assert.equal(report.owner_admission_ref, parsed.irRef);
  assert.equal(report.answer_provenance.ir_criterion_ref, parsed.irRef);
  assert.equal(report.answer_provenance.owner_ref_matches_criterion, true);
  assert.equal(report.binding.answer.ir_criterion_ref, parsed.irRef);
  assert.equal(INTERACTIVE_REF_RE.test(report.owner_admission_ref), true);
  // The F13 criterion is a different authenticated ref; borrowing it is refused.
  assert.notEqual(report.owner_admission_ref, F13_CRITERION_REF);
  assert.equal(report.answer_provenance.interactive_ref_present, true);
});

contract("the admitted scope is exactly the candidate layer of variant C", () => {
  assert.equal(report.adopted_variant, ADOPTED_VARIANT);
  assert.equal(report.adopted_variant_label, ADOPTED_VARIANT_LABEL);
  assert.deepEqual(report.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(report.binding.checkpoint.scope_bounded_to_variant_c, true);
  assert.equal(report.binding.checkpoint.variant_c_found, true);
  assert.equal(report.binding.checkpoint.runtime_stop_scoped, true);
  for (const excluded of EXCLUDED_CONSTRUCT_SET) {
    assert.equal(report.adopted_construct_set.includes(excluded), false, `${excluded} must stay outside`);
  }
  assert.equal(report.runtime_stop, RUNTIME_STOP_LIFTED);
  assert.equal(report.runtime_stop_scope.lifted_for, "adopted candidate layer");
  for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
    assert.ok(report.runtime_stop_scope.still_active_for.includes(surface), `${surface} must stay stopped`);
  }
  assert.match(mdText, /no-start/i, "the checkpoint must still carry the no-start directive");
});

contract("adoption is separated from execution on the live records", () => {
  assert.equal(report.adoption_state.adoption_established, true);
  assert.equal(report.adoption_state.normative_semantics_adopted, false);
  assert.equal(report.adoption_state.section3_terms, "deferred-undefined");
  assert.equal(report.adoption_state.execution_separated, true);
  assert.equal(report.execution_state.executed, false);
  assert.equal(report.execution_state.candidates_emitted, 0);
  assert.equal(report.execution_state.conflicts, 0);
  assert.equal(report.runtime_work, "not-started");
  assert.equal(report.runtime_demo, "not-proven");
  assert.equal(report.permitted_work.length, 1);
});

contract("the recorded status and F13 status are read verbatim", () => {
  assert.equal(report.answer_provenance.status, OWNER_DECISION_RECORDED);
  assert.equal(report.binding.answer.status, OWNER_DECISION_RECORDED);
  assert.notEqual(report.answer_provenance.status, "answered");
  assert.equal(report.f13_status, F13_DEFERRED_EXPLICIT);
  assert.notEqual(report.f13_status, "hold");
  assert.equal(report.binding.answer.f13_status, F13_DEFERRED_EXPLICIT);
});

contract("the governing-surface check is re-read under v2 rather than re-demanded", () => {
  assert.equal(governing.verdict, "governing_surface_absent");
  assert.equal(governing.answer_record_ref, S02_ANSWER_V1_PATH);
  assert.equal(governing.actor_bound_path_available, false);
  assert.equal(report.answer_provenance.governing_surface_verdict, "governing_surface_absent");
  assert.equal(report.answer_provenance.governing_surface_reread, "v2_supersession");
  assert.equal(report.answer_provenance.governing_blocking, false);
  assert.equal(report.binding.governing.reread_under, "v2");
  assert.equal(report.binding.governing.verdict_applies_to, "v1");
  assert.equal(report.binding.governing.blocking, false);
});

// ---------------------------------------------------------------------------
// supersession keeps history, both pin spellings work
// ---------------------------------------------------------------------------

contract("the superseded v1 bytes are byte-identical to the digests the v2 records bind", () => {
  const tableRows = parseSourceTable(checkpointText).rows;
  const boundV1Checkpoint = tableRows.find((row) => row.path === S02_CHECKPOINT_V1_PATH);
  const boundV1Answer = tableRows.find((row) => row.path === S02_ANSWER_V1_PATH);
  assert.ok(boundV1Checkpoint, "the v2 checkpoint must bind the v1 checkpoint");
  assert.ok(boundV1Answer, "the v2 checkpoint must bind the v1 answer record");
  assert.equal(boundV1Checkpoint.sha256, lookup.sha256(S02_CHECKPOINT_V1_PATH));
  assert.equal(boundV1Answer.sha256, lookup.sha256(S02_ANSWER_V1_PATH));
  assert.equal(report.binding.superseded.checkpoint_v1.expected_sha256, boundV1Checkpoint.sha256);
  assert.equal(report.binding.superseded.answer_v1.expected_sha256, boundV1Answer.sha256);
  assert.equal(report.binding.superseded.checkpoint_v1.verdict, "preserved");
  assert.equal(report.binding.superseded.answer_v1.verdict, "preserved");
  // The v1 records still carry their own original verdict and status.
  assert.match(v1CheckpointText, /^\*\*admission: not-adopted\*\*$/m);
  assert.equal(v1AnswerRecord.status, "pending_human_decision");
  assert.equal(parseAnswerRecord(v1AnswerRecord).status, "pending_human_decision");
  // The v2 answer record's own supersession claim agrees with the v2 table row.
  assert.equal(normalizePin(answerRecord.supersedes.sha256), boundV1Answer.sha256);
  assert.equal(answerRecord.supersedes.path, S02_ANSWER_V1_PATH);
  assert.equal(report.binding.answer.supersedes_path, S02_ANSWER_V1_PATH);
});

contract("the earlier S03 receipts are named as superseded, not rewritten", () => {
  assert.equal(report.superseded_receipts.checkpoint_v1, S02_CHECKPOINT_V1_PATH);
  assert.equal(report.superseded_receipts.answer_v1, S02_ANSWER_V1_PATH);
  assert.equal(report.superseded_receipts.prior_start_gate_record, START_GATE_RELATIVE_PATH);
  assert.ok(report.superseded_receipts.prior_start_gate_commits.includes("c72e2e3"));
  assert.ok(report.superseded_receipts.policy.includes("rewrites nothing"));
  assert.ok(
    report.non_claims.some((claim) => claim.includes("byte-identical and hash-bound as history")),
    "the non-claims must record the preserved history",
  );
});

contract("both digest spellings resolve to the same bound digests", () => {
  const bare = parseSourceTable(checkpointText).rows;
  assert.equal(bare.every((row) => row.pin_form === "bare64"), true);
  const prefixed = parseSourceTable(
    checkpointText.replace(/\| ([0-9a-f]{64}) \|/g, "| sha256:$1 |"),
  ).rows;
  assert.equal(prefixed.every((row) => row.pin_form === "sha256_prefixed"), true);
  assert.deepEqual(
    prefixed.map((row) => row.sha256),
    bare.map((row) => row.sha256),
    "normalization must yield identical digests for both spellings",
  );
  const prefixedRender = renderStartGate({
    rootDir: root,
    lookup,
    sourceRevision: report.source_revision,
    checkpointText: checkpointText.replace(/\| ([0-9a-f]{64}) \|/g, "| sha256:$1 |"),
  });
  assert.equal(prefixedRender.report.admission_verdict, "admission_granted");
});

// ---------------------------------------------------------------------------
// negatives
// ---------------------------------------------------------------------------

contract("negative: a superseded source cannot be selected", () => {
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.path = S02_CHECKPOINT_V1_PATH;
    }),
    "superseded_source_selected",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.path = S02_ANSWER_V1_PATH;
    }),
    "superseded_source_selected",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.verdict = "not-adopted";
    }),
    "superseded_source_selected",
  );
});

contract("negative: a superseded hash cannot be accepted as the binding digest", () => {
  expectCode(
    mutated((rep) => {
      rep.binding.answer.recorded_sha256 = rep.binding.superseded.answer_v1.live_sha256;
    }),
    "superseded_hash_accepted",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.recorded_sha256 = rep.binding.superseded.checkpoint_v1.live_sha256;
    }),
    "superseded_hash_accepted",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.superseded.answer_v1.table_sha256 = "sha256:" + "0".repeat(64);
    }),
    "superseded_hash_accepted",
  );
});

contract("negative: a superseded or foreign reference cannot be the owner ref", () => {
  expectCode(
    mutated((rep) => {
      rep.owner_admission_ref = F13_CRITERION_REF;
    }),
    "superseded_ref_accepted",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.status = "pending_human_decision";
    }),
    "superseded_ref_accepted",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.answer.supersedes_path = S02_CHECKPOINT_V1_PATH;
    }),
    "superseded_ref_accepted",
  );
});

contract("negative: the scope cannot be widened beyond the candidate layer", () => {
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.scope_bounded_to_variant_c = false;
    }),
    "scope_overclaim",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.variant_c_found = false;
    }),
    "scope_overclaim",
  );
  expectCode(
    mutated((rep) => {
      rep.adopted_construct_set = ADOPTED_CONSTRUCT_SET.concat(["rule_composition"]);
    }),
    "scope_overclaim",
  );
  expectCode(
    mutated((rep) => {
      rep.adopted_variant_label = "whole_bounded_semantic_runtime";
    }),
    "scope_overclaim",
  );
  expectCode(
    mutated((rep) => {
      rep.adopted_construct_set = ["candidate_emission"];
    }),
    "scope_overclaim",
  );
});

contract("negative: the two reading misreads keep their own codes", () => {
  expectCode(
    mutated((rep) => {
      rep.answer_provenance.status = "answered";
    }),
    "owner_decision_read_as_answered",
  );
  expectCode(
    mutated((rep) => {
      rep.f13_status = "hold";
    }),
    "f13_hold_misread",
  );
  expectCode(
    mutated((rep) => {
      rep.f13_status = "answered";
    }),
    "f13_scope_borrowed",
  );
});

contract("negative: adoption and execution cannot be collapsed", () => {
  expectCode(
    mutated((rep) => {
      rep.execution_state.executed = true;
    }),
    "adoption_read_as_execution",
  );
  expectCode(
    mutated((rep) => {
      rep.execution_state.candidates_emitted = 1;
    }),
    "adoption_read_as_execution",
  );
  expectCode(
    mutated((rep) => {
      rep.adoption_state.adoption_established = false;
    }),
    "execution_read_as_adoption",
  );
  expectCode(
    mutated((rep) => {
      rep.adoption_state.adopted_variant = "B";
    }),
    "execution_read_as_adoption",
  );
});

contract("negative: the runtime stop cannot be lifted wholesale", () => {
  expectCode(
    mutated((rep) => {
      rep.runtime_stop = "lifted";
    }),
    "runtime_stop_blanket_lifted",
  );
  expectCode(
    mutated((rep) => {
      rep.runtime_stop_scope.lifted_for = "the whole runtime";
    }),
    "runtime_stop_blanket_lifted",
  );
  expectCode(
    mutated((rep) => {
      rep.runtime_stop_scope.still_active_for = RUNTIME_STOP_STILL_ACTIVE.slice(0, 1);
    }),
    "runtime_stop_blanket_lifted",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.checkpoint.runtime_stop_scoped = false;
    }),
    "runtime_stop_blanket_lifted",
  );
});

contract("negative: the superseded receipts cannot be dropped or rewritten", () => {
  expectCode(
    mutated((rep) => {
      rep.binding.superseded.answer_v1.verdict = "rewritten";
    }),
    "receipt_silently_rewritten",
  );
  expectCode(
    mutated((rep) => {
      rep.superseded_receipts.answer_v1 = S02_ANSWER_PATH;
    }),
    "receipt_silently_rewritten",
  );
  expectCode(
    mutated((rep) => {
      delete rep.binding;
    }),
    "v2_source_not_wired",
  );
  expectCode(
    mutated((rep) => {
      rep.binding.superseded.checkpoint_v1.expected_sha256 = "31ed55b9f5db";
    }),
    "source_pin_form_rejected",
  );
});

contract("negative: the preserved fail-closed codes are not weakened", () => {
  for (const code of [
    "verdict_missing",
    "verdict_ambiguous",
    "source_unresolved",
    "source_hash_mismatch",
    "source_revision_mismatch",
    "grant_without_interactive_ref",
    "grant_without_governing_surface",
    "runtime_permitted_without_admission",
    "crate_touched",
    "requirements_promoted",
    "review_case_event_written",
  ]) {
    assert.ok(EMITTABLE_CODES.includes(code), `${code} must remain emittable`);
  }
  expectCode(mutated((rep) => { rep.owner_admission_ref = "none"; }), "grant_without_interactive_ref");
  expectCode(
    mutated((rep) => { rep.answer_provenance.governing_blocking = true; }),
    "grant_without_governing_surface",
  );
  expectCode(mutated((rep) => { rep.source_revision = "deadbeef"; }), "source_revision_mismatch");
  expectCode(
    mutated((rep) => { rep.s02_sources[0].path = "prd/architecture/m210-s03-absent.md"; }),
    "source_unresolved",
  );
  expectCode(mutated((rep) => { rep.s02_sources[0].recorded_sha256 = "sha256:" + "0".repeat(64); }), "source_hash_mismatch");
  expectCode(report, "verdict_missing", mdText.replace("**admission: granted**", "**admission_state: pending**"));
  expectCode(report, "verdict_ambiguous", mdText.replace("**admission: granted**", "**admission: granted**\n**admission: not-adopted**"));
});

contract("negative: the authenticated channel is exact, never a substring", () => {
  const refused = [
    "unauthenticated",
    "not authenticated",
    "authenticated",
    "unauthenticated subjective-UAT",
    "not authenticated subjective-UAT",
    "Authenticated Subjective-UAT",
    "authenticated subjective-uat",
    "authenticated-subjective-UAT",
    "authenticatedXsubjective-UAT",
    "authenticated subjective-UAT extended",
    "authenticated subjective-UAT ",
    "manual",
    "",
  ];
  for (const value of refused) {
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
    const answer = clone(answerRecord);
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
  }
  // The genuine v2 channel still derives the grant on live data.
  assert.equal(live.report.admission_verdict, "admission_granted");
  assert.equal(live.report.answer_provenance.channel, "authenticated subjective-UAT");
  assert.equal(live.report.answer_provenance.interactive_ref_present, true);
});

contract("negative: re-pointing the gate at the superseded v1 sources fails closed", () => {
  const absentRender = renderStartGate({
    rootDir: root,
    lookup,
    sourceRevision: report.source_revision,
    binding: { checkpoint: S02_CHECKPOINT_V1_PATH, answer: S02_ANSWER_V1_PATH },
  });
  assert.equal(absentRender.report.admission_verdict, "admission_absent");
  assert.equal(absentRender.report.runtime_implementation_permitted, false);
  assert.equal(absentRender.report.owner_admission_ref, "none");
  const codes = codesFor(absentRender, mdText, { checkpointText: absentRender.checkpointText });
  for (const expected of ["superseded_source_selected", "superseded_ref_accepted"]) {
    assert.ok(codes.includes(expected), `re-pointing at v1 must emit ${expected}, got ${JSON.stringify(codes)}`);
  }
});

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  process.stdout.write(
    `${MARKER} checks=${caseCount} binding=v2 verdict=${report.admission_verdict} ` +
      `owner_ref_bound=${report.answer_provenance.owner_ref_matches_criterion} ` +
      `v1_preserved=${report.binding.superseded.checkpoint_v1.verdict}/${report.binding.superseded.answer_v1.verdict} ` +
      `executed=${report.execution_state.executed}\n`,
  );
});
