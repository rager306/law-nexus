// M210-3afp79 S04 T02 finding-evidence-matrix contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s04-finding-evidence-matrix.json, rendered by
// scripts/m210_s04_finding_matrix.mjs from a single declarative table plus live
// reads of the tracked sources.
//
// The claims under test are that all 19 RC28 findings appear exactly once with a
// proof class that agrees with the packet and a required-proof sentence that is a
// verbatim substring of the owning program record, that every cited evidence path
// resolves and carries its live digest, that exactly RC28-F02/F04/F05/F14 are
// re-verified in this pass and each re-verification is re-proved live, that every
// finding row keeps status_effect=unchanged while each requirement row keeps
// class_matched=false, that the requirement namespace binding never promotes the
// PRD-namespace RQ-009 into a canonical GSD R###, that D519 is never treated as
// proof, that RC28-F13 stays an explicit owner defer, that RC28-F18 forbids
// auto-close, that the disposition model stays per-finding, that no Review Case
// human disposition event is claimed, that the review-case rollup is the observed
// ok rollup 35/10/21/0/0 bound to the live packet store and the declared review
// document hash, that the rendered artifact is byte-identical on re-render, carries
// no timestamp, no raw text and no non-ASCII code point, and that every documented
// fail-closed code is empirically emitted by a mutation.
//
// No network, no subprocess, no ignored path and no .gsd, .agents, .lex, .planning
// or .audits path is read as evidence, and this contract never writes a file.
//
// Run: node --test scripts/m210_s04_finding_matrix_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test, after } from "node:test";
import path from "node:path";

import {
  CHECK_OK_MARKER,
  CONTRACT_MARKER,
  EMITTABLE_CODES,
  FINDING_IDS,
  INVENTORY_RELATIVE_PATH,
  KIND,
  LIFECYCLE,
  MACHINE_VERDICTS,
  MATRIX_RELATIVE_PATH,
  MILESTONE,
  MISMATCH_REASON_CODES,
  PACKET_CONTENT_SHA256,
  PACKET_RELATIVE_PATH,
  PROGRAM_RELATIVE_PATH,
  REPO_ROOT,
  REQUIRED_PROOF_CLASSES,
  REVERIFICATION_REQUIRED_IDS,
  REVIEWED_GIT_REVISION,
  REVIEWED_GIT_REVISION_FORMAT,
  SCHEMA,
  SCHEMA_VERSION,
  SLICE,
  SOURCE_REVIEW_RELATIVE_PATH,
  TASK,
  WRITTEN_MARKER,
  loadMatrixContext,
  normalizeSha,
  renderMatrix,
  runCli,
  validateMatrix,
} from "./m210_s04_finding_matrix.mjs";

const MATRIX_PATH = path.join(REPO_ROOT, MATRIX_RELATIVE_PATH);
const committedText = existsSync(MATRIX_PATH) ? readFileSync(MATRIX_PATH, "utf8") : null;
const report = committedText === null ? null : JSON.parse(committedText);
const context = loadMatrixContext(REPO_ROOT);
const rowById = new Map((report?.rows ?? []).map((row) => [row.finding_id, row]));

function clone() {
  return JSON.parse(JSON.stringify(report));
}

function codesFor(mutate) {
  const candidate = clone();
  mutate(candidate);
  return validateMatrix(candidate, context).map((entry) => entry.code);
}

const observedCodes = new Set();

function expectCode(code, mutate) {
  const codes = codesFor(mutate);
  observedCodes.add(code);
  assert.ok(
    codes.includes(code),
    `expected the mutation to emit ${code}; observed ${JSON.stringify([...new Set(codes)])}`,
  );
}

test("artifact exists, parses and carries the expected identity", () => {
  assert.ok(committedText !== null, `${MATRIX_RELATIVE_PATH} is absent`);
  assert.ok(report !== null, "the matrix is not JSON");
  assert.equal(report.schema, SCHEMA);
  assert.equal(report.schema_version, SCHEMA_VERSION);
  assert.equal(report.kind, KIND);
  assert.equal(report.milestone, MILESTONE);
  assert.equal(report.slice, SLICE);
  assert.equal(report.task, TASK);
  assert.deepEqual(report.lifecycle, LIFECYCLE);
  assert.equal(report.authoritative, false);
  assert.equal(report.ascii_only, true);
  assert.equal(report.status_effect, "unchanged");
  assert.equal(report.requirement_promotion, false);
});

test("artifact bytes are ASCII and carry no timestamp", () => {
  assert.ok(!/[^\u0000-\u007f]/.test(committedText), "the artifact carries a non-ASCII code point");
  assert.ok(!/timestamp/i.test(committedText), "the artifact must carry no timestamp field");
  assert.ok(!/generated_at|captured_at/.test(committedText), "the artifact must carry no generation clock");
  assert.ok(!/\d{4}-\d{2}-\d{2}T/.test(committedText), "the artifact must carry no ISO timestamp");
});

test("19 findings appear exactly once and every row is validated clean", () => {
  assert.equal(report.rows.length, 19);
  assert.deepEqual(
    report.rows.map((row) => row.finding_id),
    FINDING_IDS,
    "the row order must be RC28-F01..RC28-F19",
  );
  assert.equal(report.summary.finding_count, 19);
  assert.deepEqual(validateMatrix(report, context), []);
  assert.deepEqual(renderMatrix(REPO_ROOT).codes, []);
});

test("each required proof sentence is verbatim in the owning program record", () => {
  const programText = context.readText(PROGRAM_RELATIVE_PATH);
  assert.ok(typeof programText === "string" && programText.length > 0, "the program record is unreadable");
  const inventoryText = context.readText(INVENTORY_RELATIVE_PATH);
  assert.ok(typeof inventoryText === "string" && inventoryText.length > 0, "the inventory is unreadable");
  for (const row of report.rows) {
    assert.equal(
      row.required_proof_verbatim_source,
      PROGRAM_RELATIVE_PATH,
      `${row.finding_id} must name the verbatim source`,
    );
    assert.ok(
      programText.includes(row.required_proof),
      `${row.finding_id} required_proof is not verbatim in ${PROGRAM_RELATIVE_PATH}`,
    );
  }
  assert.equal(report.required_proof_derivation.packet_has_verbatim_required_proof, false);
  assert.equal(report.required_proof_derivation.verbatim_source, PROGRAM_RELATIVE_PATH);
});

test("each proof class agrees with the packet and the closed vocabulary", () => {
  for (const id of FINDING_IDS) {
    const row = rowById.get(id);
    assert.ok(row, `missing row ${id}`);
    assert.ok(REQUIRED_PROOF_CLASSES.includes(row.required_proof_class), `${id} class is outside the vocabulary`);
    assert.equal(
      row.required_proof_class,
      context.packetClassById.get(id),
      `${id} proof class disagrees with the packet`,
    );
  }
  assert.deepEqual([...report.vocabularies.required_proof_class].sort(), [...REQUIRED_PROOF_CLASSES].sort());
  assert.deepEqual([...report.vocabularies.machine_verdict].sort(), [...MACHINE_VERDICTS].sort());
  assert.deepEqual([...report.vocabularies.mismatch_reason_code].sort(), [...MISMATCH_REASON_CODES].sort());
});

test("every evidence path resolves and carries its live digest", () => {
  let checked = 0;
  for (const row of report.rows) {
    assert.ok(row.evidence_paths.length > 0, `${row.finding_id} has no evidence path`);
    for (const entry of row.evidence_paths) {
      const live = context.sha(entry.path);
      assert.ok(live !== null, `${row.finding_id} evidence path ${entry.path} is unresolved`);
      assert.equal(entry.sha256, live, `${row.finding_id} evidence digest drifted for ${entry.path}`);
      checked += 1;
    }
  }
  assert.equal(checked, report.summary.evidence_path_count);
  assert.ok(checked >= 19, "at least one evidence path per finding is expected");
});

test("exactly RC28-F02/F04/F05/F14 are re-verified, each with live assertions", () => {
  const rereverified = report.rows.filter((row) => row.rereverified).map((row) => row.finding_id);
  assert.deepEqual(rereverified, REVERIFICATION_REQUIRED_IDS);
  for (const id of REVERIFICATION_REQUIRED_IDS) {
    const reverification = rowById.get(id).reverification;
    assert.equal(reverification.verdict, "confirmed", `${id} reverification is not confirmed`);
    assert.ok(reverification.observed.length > 0, `${id} reverification carries no observation`);
    const liveAssertions =
      (reverification.tokens ?? []).length + (reverification.observed_fields ?? []).length;
    assert.ok(liveAssertions > 0, `${id} reverification is not re-proved live`);
  }
  for (const row of report.rows) {
    if (!REVERIFICATION_REQUIRED_IDS.includes(row.finding_id)) {
      assert.equal(row.rereverified, false, `${row.finding_id} must stay un-re-verified in this pass`);
      assert.equal(row.reverification, null, `${row.finding_id} must carry no reverification`);
    }
  }
});

test("F04 reverification binds the predecessor by its live digest", () => {
  const reverification = rowById.get("RC28-F04").reverification;
  const binding = reverification.observed_fields.find((f) => f.equals_file_sha256);
  assert.ok(binding, "F04 must bind the predecessor by file digest");
  assert.equal(
    context.pointer(binding.path, binding.pointer),
    context.sha(binding.equals_file_sha256),
    "the recorded predecessor digest must equal the live predecessor digest",
  );
});

test("F05 reverification records the unresolved identities and the unfiled upstream debt", () => {
  const reverification = rowById.get("RC28-F05").reverification;
  const pointerEquals = (pointer, value) =>
    reverification.observed_fields.some((f) => f.pointer === pointer && f.equals === value);
  assert.ok(pointerEquals("task_counter.status", "unknown"));
  assert.ok(pointerEquals("task_counter.pending_task_ids", null));
  assert.ok(pointerEquals("status.upstream_issue", "not_filed"));
  assert.ok(reverification.tokens.some((t) => t.token === "open-gsd/gsd-pi#2412"));
  assert.match(rowById.get("RC28-F05").residual_scope, /pending_task_identity_unresolved/);
});

test("no requirement is promoted and no lifecycle smoothing is recorded", () => {
  for (const row of report.rows) {
    assert.equal(row.status_effect, "unchanged", `${row.finding_id} must keep status_effect unchanged`);
  }
  assert.deepEqual(report.summary.class_matched_requirement_ids, []);
  assert.deepEqual(report.summary.status_effect_values, ["unchanged"]);
  assert.deepEqual(report.boundary.requirements_promoted, []);
  assert.equal(report.boundary.requirement_status_mutated, false);
  assert.equal(report.boundary.runtime_touched, false);
});

test("the requirement evidence table stays supporting-only and class-mismatched", () => {
  const expected = [
    ["R038", "quality-attribute", "source-bound-criterion-plus-c4-gsd-attempt"],
    ["R063", "constraint", "process-provenance-without-product-change"],
    ["R064", "operability", "thin-harness-operability-retest"],
    ["R081", "constraint", "documentation-residue-no-new-work"],
  ];
  assert.deepEqual(
    report.requirement_evidence.map((row) => [row.requirement_id, row.canonical_class, row.evidence_class]),
    expected,
  );
  for (const row of report.requirement_evidence) {
    assert.equal(row.namespace, "gsd");
    assert.equal(row.class_matched, false, `${row.requirement_id} must stay class_matched=false`);
    assert.equal(row.status_effect, "unchanged", `${row.requirement_id} must stay unchanged`);
    const tracked = context.s15Row(row.requirement_id);
    assert.ok(tracked, `${row.requirement_id} is absent from the tracked classification`);
    assert.equal(tracked.evidence_class, row.evidence_class);
    assert.equal(tracked.class_matched, false);
    assert.equal(tracked.status_effect, "unchanged");
  }
  const r081 = report.requirement_evidence.find((row) => row.requirement_id === "R081");
  assert.match(r081.class_match_basis, /Work identity/);
  assert.match(r081.class_match_basis, /F03/);
  assert.match(r081.class_match_basis, /F04/);
  assert.match(r081.class_match_basis, /F05/);
});

test("requirement refs are namespace-bound and RQ-009 stays a PRD-only reference", () => {
  const gsdRefs = report.requirement_refs.filter((ref) => ref.namespace === "gsd");
  assert.deepEqual(gsdRefs.map((ref) => ref.id).sort(), ["R038", "R063", "R064", "R081"]);
  for (const ref of gsdRefs) assert.equal(ref.canonical, true);
  const prd = report.requirement_refs.find((ref) => ref.namespace === "prd" && ref.id === "RQ-009");
  assert.ok(prd, "the RQ-009 PRD-namespace reference must be present");
  assert.equal(prd.canonical, false);
  assert.equal(prd.canonical_gsd_id, null);
  assert.match(prd.note, /not a canonical GSD/);
  const readings = report.canonical_requirement_readings;
  assert.equal(readings.tool_available_in_unit, false);
  assert.equal(readings.direct_db_read, false);
  for (const reading of readings.readings) assert.equal(reading.canonical_store_queried, false);
});

test("the class-mismatched rows explain themselves in the closed vocabulary", () => {
  const mismatched = report.rows.filter((row) => row.class_match === false);
  assert.deepEqual(
    mismatched.map((row) => row.finding_id),
    ["RC28-F06", "RC28-F07", "RC28-F08", "RC28-F09", "RC28-F10", "RC28-F11"],
  );
  for (const row of mismatched) {
    assert.ok(MISMATCH_REASON_CODES.includes(row.mismatch_reason_code), `${row.finding_id} reason is outside the vocabulary`);
  }
  for (const row of report.rows.filter((candidate) => candidate.class_match === true)) {
    assert.equal(row.mismatch_reason_code, null, `${row.finding_id} must carry no mismatch reason`);
  }
});

test("D519 is recorded as a deferral and never as proof", () => {
  for (const id of ["RC28-F01", "RC28-F15"]) {
    const row = rowById.get(id);
    assert.equal(row.deferral_reference, "D519");
    assert.equal(row.deferral_treated_as_proof, false);
    assert.notEqual(row.machine_verdict, "evidence_present_class_matched");
    assert.equal(row.machine_verdict, "evidence_absent_residual_named");
    assert.match(row.non_claims.join(" "), /D519/);
  }
  assert.ok(!report.rows.some((row) => row.deferral_reference === "D519" && row.deferral_treated_as_proof !== false));
});

test("RC28-F13 stays an explicit owner defer and RC28-F18 forbids auto-close", () => {
  const f13 = rowById.get("RC28-F13");
  assert.equal(f13.owner_status, "deferred-explicit");
  assert.equal(f13.machine_verdict, "awaiting_owner_decision");
  assert.match(f13.residual_scope, /no live adoption owner/);
  assert.match(f13.non_claims.join(" "), /not a missing answer/);

  const f18 = rowById.get("RC28-F18");
  assert.equal(f18.auto_close, false);
  assert.equal(f18.owner_status, "bounded_adoption_established");
  assert.match(f18.residual_scope, /37181c25-88b0-4896-bffe-d10642970e6f/);
  assert.match(f18.residual_scope, /independent evaluation/);
  assert.match(f18.non_claims.join(" "), /auto-close is forbidden/);
  assert.equal(f18.status_effect, "unchanged");
});

test("the disposition model stays per-finding and no Review Case event is claimed", () => {
  const model = report.disposition_model;
  assert.equal(model.mode, "per_finding");
  assert.equal(model.blanket_confirmation, false);
  assert.equal(model.preselected_consent, false);
  assert.equal(model.recommendation_is_not_consent, true);
  assert.equal(model.actor_bound_path_available, false);
  assert.equal(model.submission_channel_used, "none");
  assert.equal(report.boundary.record_human_disposition_called, false);
  assert.equal(report.boundary.review_case_events_written, false);
  assert.equal(report.review_case.actor_bound_path_available, false);
  assert.equal(report.review_case.actor_bound_scope, "record_human_disposition");
  assert.match(report.review_case.actor_bound_limitation, /actor-bound/);
  assert.equal(report.review_case.human_disposition_event_count, 0);
  assert.equal(report.review_case.embedded_event_count, 1);
  assert.equal(report.review_case.embedded_events[0].event_type, "packet_registered");
  assert.equal(report.review_case.embedded_events[0].actor_class, "tool");
  assert.equal(report.review_case.events_directory_present, false);
  assert.equal(existsSync(path.join(REPO_ROOT, report.review_case.events_directory_path)), false);
});

test("the review-case binding is live and the rollup matches the observed rollup", () => {
  const reviewCase = report.review_case;
  assert.equal(reviewCase.packet_id, "RC-2026-09-10-001");
  assert.equal(reviewCase.packet_path, PACKET_RELATIVE_PATH);
  assert.equal(reviewCase.source_path, SOURCE_REVIEW_RELATIVE_PATH);
  assert.equal(context.sha(PACKET_RELATIVE_PATH), reviewCase.packet_file_sha256);
  assert.equal(context.sha(SOURCE_REVIEW_RELATIVE_PATH), reviewCase.source_content_sha256);
  assert.equal(reviewCase.source_content_sha256, PACKET_CONTENT_SHA256);
  assert.equal(normalizeSha(reviewCase.packet_declared_content_sha256_raw), PACKET_CONTENT_SHA256);
  assert.equal(reviewCase.packet_declared_content_sha256, PACKET_CONTENT_SHA256);
  assert.equal(reviewCase.reviewed_git_revision, REVIEWED_GIT_REVISION);
  assert.equal(reviewCase.reviewed_git_revision_format, REVIEWED_GIT_REVISION_FORMAT);
  assert.match(reviewCase.reviewed_git_revision, /^[0-9a-f]{40}$/);
  assert.equal(reviewCase.findings_total, 19);
  assert.equal(reviewCase.findings_open, 19);
  assert.equal(reviewCase.packet_findings_state.length, 19);
  for (const finding of reviewCase.packet_findings_state) {
    assert.equal(finding.disposition_status, "open", `${finding.finding_id} must stay open`);
  }
  assert.deepEqual(reviewCase.inventory_observation.residual_counts, [["awaiting_disposition", 19]]);
  assert.deepEqual(reviewCase.inventory_observation.stage_counts, [["S1_normalized", 19]]);
  assert.equal(reviewCase.inventory_observation.last_event, null);

  const rollup = report.review_case_rollup;
  assert.equal(rollup.observed_via, "uv run python -m law_nexus_harness review-case validate");
  assert.equal(rollup.ok, true);
  assert.deepEqual(rollup.rollup_digits, [35, 10, 21, 0, 0]);
  assert.equal(rollup.finding_count, 35);
  assert.equal(rollup.closed_count, 10);
  assert.equal(rollup.open_count, 21);
  assert.equal(rollup.blocked_count, 0);
  assert.equal(rollup.partial_count, 0);
  assert.equal(rollup.stale_count, 0);
  assert.equal(rollup.cross_check.packet_files, context.packetFiles.length);
  assert.equal(rollup.cross_check.packet_store_findings, context.packetStoreFindings);
  assert.equal(rollup.cross_check.packet_store_rc28_open, context.packetStoreRc28Open);
  assert.equal(rollup.cross_check.ledger_event_directories, context.ledgerEventDirectories);
});

test("every machine verdict is inside the closed vocabulary", () => {
  for (const row of report.rows) {
    assert.ok(MACHINE_VERDICTS.includes(row.machine_verdict), `${row.finding_id} verdict ${row.machine_verdict}`);
    assert.equal(typeof row.residual_scope, "string");
    assert.ok(row.residual_scope.length > 0, `${row.finding_id} has no residual scope`);
    assert.ok(row.non_claims.length > 0, `${row.finding_id} has no non-claims`);
    assert.ok(row.human_sufficiency.length > 0, `${row.finding_id} has no human-sufficiency statement`);
  }
});

test("the generator is offline, clock-free and writes exactly once", () => {
  const source = readFileSync(path.join(REPO_ROOT, "scripts/m210_s04_finding_matrix.mjs"), "utf8");
  assert.ok(!/\bfetch\(|https?:\/\//.test(source), "the generator must be offline");
  assert.ok(!/^import\b[^\n]*"node:child_process"/m.test(source), "the generator must not spawn a process");
  assert.ok(!/\bexecSync\b/.test(source), "the generator must not use execSync");
  assert.ok(!/\bnew Date\b|\bDate\.now\b/.test(source), "the generator must not read a clock");
  const writes = source.match(/writeFileSync\(/g) ?? [];
  assert.equal(writes.length, 1, "the generator must write exactly once");
  assert.ok(!/^import\b[^\n]*"node:child_process"/m.test(readFileSync(new URL(import.meta.url), "utf8")));
});

test("the CLI modes behave", () => {
  const check = runCli(["--check"]);
  assert.equal(check.exitCode, 0);
  assert.deepEqual(check.stdout, [CHECK_OK_MARKER]);

  const mismatch = runCli(["--check"], { committedText: "{\"schema\":\"drifted\"}\n" });
  assert.equal(mismatch.exitCode, 1);
  assert.ok(mismatch.stderr.some((line) => line.startsWith("check_not_byte_identical")));
  observedCodes.add("check_not_byte_identical");

  const dryRun = runCli([], { dryRun: true });
  assert.equal(dryRun.exitCode, 0);
  assert.equal(dryRun.wrote, false);
  assert.deepEqual(dryRun.stdout, [WRITTEN_MARKER]);
  assert.equal(dryRun.text, committedText);

  const printed = runCli(["--print"]);
  assert.equal(printed.exitCode, 0);

  const usage = runCli(["--nope"]);
  assert.equal(usage.exitCode, 2);
});

test("CODE_COVERAGE: every documented fail-closed code is exercised", () => {
  expectCode("row_count_incomplete", (c) => c.rows.pop());
  expectCode("finding_id_unknown", (c) => {
    c.rows[0].finding_id = "RC28-F20";
  });
  expectCode("proof_class_mismatch", (c) => {
    c.rows[0].required_proof_class = "process";
  });
  expectCode("evidence_path_unresolved", (c) => {
    c.rows[0].evidence_paths[0].path = "prd/architecture/m210-s04-not-a-real-artifact.md";
  });
  expectCode("evidence_hash_mismatch", (c) => {
    c.rows[0].evidence_paths[0].sha256 = `sha256:${"0".repeat(64)}`;
  });
  expectCode("reverification_missing", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F02").rereverified = false;
  });
  expectCode("reverification_missing", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F02").reverification.tokens[0].token =
      "token-that-does-not-exist-in-the-source";
  });
  expectCode("class_mismatch_unexplained", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F06").mismatch_reason_code = null;
  });
  expectCode("verdict_unknown", (c) => {
    c.rows[0].machine_verdict = "accepted";
  });
  expectCode("d519_treated_as_proof", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F01").machine_verdict = "evidence_present_class_matched";
  });
  expectCode("d519_treated_as_proof", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F01").deferral_treated_as_proof = true;
  });
  expectCode("lifecycle_smoothing_detected", (c) => {
    c.requirement_evidence[0].class_matched = true;
  });
  expectCode("f18_auto_close", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F18").auto_close = true;
  });
  expectCode("f13_missing_answer_misread", (c) => {
    c.rows.find((row) => row.finding_id === "RC28-F13").owner_status = "missing";
  });
  expectCode("owner_choice_folded", (c) => {
    c.disposition_model.blanket_confirmation = true;
  });
  expectCode("non_ascii_artifact", (c) => {
    c.rows[0].residual_scope = `${c.rows[0].residual_scope} e-acute-\u00e9`;
  });
  expectCode("raw_text_leak", (c) => {
    c.rows[0].residual_scope = `${c.rows[0].residual_scope} <span>`;
  });
  expectCode("status_effect_missing", (c) => {
    delete c.rows[0].status_effect;
  });
  expectCode("requirement_promotion_claimed", (c) => {
    c.rows[0].status_effect = "promoted";
  });
  expectCode("requirement_namespace_confusion", (c) => {
    c.requirement_refs.find((ref) => ref.id === "RQ-009").canonical_gsd_id = "R009";
  });
  expectCode("review_case_event_written", (c) => {
    c.review_case.human_disposition_event_count = 1;
  });

  const uncovered = EMITTABLE_CODES.filter((code) => !observedCodes.has(code));
  assert.deepEqual(uncovered, [], `uncovered fail-closed codes: ${JSON.stringify(uncovered)}`);
  assert.equal(EMITTABLE_CODES.length, 20);
});

after(() => {
  process.stdout.write(`${CONTRACT_MARKER}\n`);
});
