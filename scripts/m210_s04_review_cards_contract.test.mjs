// M210-3afp79 S04 T03 review-cards contract.
//
// Offline and fail-closed. The artifacts under test are
//   prd/architecture/m210-s04-rc28-review-cards.json and
//   prd/architecture/m210-s04-rc28-review-presentation.md,
// both rendered by scripts/m210_s04_review_cards.mjs from a single declarative
// proposal table plus live reads of the tracked matrix and packet.
//
// The claims under test are that all 19 RC28 findings appear exactly once as a
// card with a complete source binding (packet id, review path, reviewed revision
// and live review-document digest), a proof class and a check outcome that agree
// with the T02 matrix, a tested source revision equal to the live matrix digest,
// a residual scope, non-claims, a proposed disposition from the closed RC28
// dictionary, at least the change/defer/stop_session alternatives and an advisory
// non-consent recommendation; that nothing is preselected or selected and no
// human answer is recorded; that RC28-F18 keeps bounded adoption evidence with a
// forbidden auto-close, RC28-F13 keeps an explicit owner defer, and RC28-F01 /
// RC28-F15 defer on D519 rather than claiming already_satisfied; that the
// presentation carries each finding row exactly once; and that every declared
// fail-closed guard code actually fires when its invariant is broken.
//
// Run: node --test scripts/m210_s04_review_cards_contract.test.mjs
// ok:  M210_S04_CARDS_OK

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { after, test } from "node:test";
import path from "node:path";
import {
  ALTERNATIVE_IDS,
  CARDS_RELATIVE_PATH,
  CHECK_OUTCOMES,
  CONTRACT_MARKER,
  EMITTABLE_CODES,
  F18_ADOPTION_REFS,
  F18_CRITERION_ID,
  FINDING_IDS,
  GROUP_DEFS,
  KIND,
  MATRIX_RELATIVE_PATH,
  MILESTONE,
  PACKET_ID,
  PRESENTATION_RELATIVE_PATH,
  PROOF_CLASSES,
  RC28_DISPOSITIONS,
  REPO_ROOT,
  SCHEMA,
  SLICE,
  SOURCE_REVIEW_RELATIVE_PATH,
  TASK,
  normalizeSha,
  renderAll,
  renderCardsText,
  renderPresentation,
  runCli,
  validateCards,
} from "./m210_s04_review_cards.mjs";

const GENERATOR_SOURCE = readFileSync(path.join(REPO_ROOT, "scripts/m210_s04_review_cards.mjs"), "utf8");

const rendered = renderAll(REPO_ROOT);
const { report, cardsText, presentationText, ctx } = rendered;

const committedCardsText = readFileSync(path.join(REPO_ROOT, CARDS_RELATIVE_PATH), "utf8");
const committedPresentationText = readFileSync(
  path.join(REPO_ROOT, PRESENTATION_RELATIVE_PATH),
  "utf8",
);

const cardById = new Map(report.cards.map((card) => [card.finding_id, card]));
const rowById = new Map(ctx.matrixRows.map((row) => [row.finding_id, row]));

const clone = (value) => JSON.parse(JSON.stringify(value));

function codesFor(mutate, overrides = {}) {
  const mutated = clone(report);
  mutate(mutated);
  return validateCards(mutated, ctx, {
    jsonText: overrides.jsonText ?? cardsText,
    presentationText: overrides.presentationText ?? presentationText,
  }).map((entry) => entry.code);
}

test("the committed cards JSON and presentation are byte-identical to a fresh render", () => {
  assert.equal(committedCardsText, renderCardsText(report));
  assert.equal(committedPresentationText, renderPresentation(report));
  assert.equal(cardsText, committedCardsText);
  assert.equal(presentationText, committedPresentationText);
});

test("the cards record carries the M210/S04/T03 envelope and no clock", () => {
  assert.equal(report.schema, SCHEMA);
  assert.equal(report.kind, KIND);
  assert.equal(report.milestone, MILESTONE);
  assert.equal(report.slice, SLICE);
  assert.equal(report.task, TASK);
  assert.deepEqual(report.lifecycle, ["proposed"]);
  assert.equal(report.authoritative, false);
  assert.equal(report.ascii_only, true);
  assert.equal(report.status_effect, "unchanged");
  assert.equal(report.review_case.packet_id, PACKET_ID);
  assert.ok(!/[\u0080-\uffff]/.test(cardsText), "the cards JSON carries a non-ASCII code point");
  assert.ok(!/\d{4}-\d{2}-\d{2}T/.test(cardsText), "the cards JSON carries an ISO timestamp");
  assert.ok(!/generated_at|captured_at/i.test(cardsText), "the cards JSON carries a generation clock");
  assert.ok(!/child_process/.test(GENERATOR_SOURCE), "the generator must stay offline");
  assert.ok(!/Date\.now|new Date\(/.test(GENERATOR_SOURCE), "the generator must be clock-free");
  const writes = GENERATOR_SOURCE.split("writeFileSync(").length - 1;
  assert.equal(writes, 2, "the generator writes exactly the two derived artifacts");
});

test("there are exactly 19 unique cards, one per RC28 finding", () => {
  assert.equal(report.cards.length, FINDING_IDS.length);
  assert.deepEqual(
    report.cards.map((card) => card.finding_id),
    FINDING_IDS,
  );
  assert.equal(new Set(report.cards.map((card) => card.finding_id)).size, FINDING_IDS.length);
  assert.equal(report.summary.card_count, FINDING_IDS.length);
  assert.equal(report.matrix_binding.finding_count, FINDING_IDS.length);
  assert.equal(report.matrix_binding.sha256, ctx.sha(MATRIX_RELATIVE_PATH));
  assert.equal(report.matrix_binding.schema, ctx.matrix.schema);
});

test("every card carries a complete live source binding and tested revision", () => {
  const liveReviewSha = ctx.sha(SOURCE_REVIEW_RELATIVE_PATH);
  assert.equal(normalizeSha(report.review_case.source_content_sha256), liveReviewSha);
  for (const card of report.cards) {
    assert.equal(card.source.packet_id, PACKET_ID);
    assert.equal(card.source.source_path, SOURCE_REVIEW_RELATIVE_PATH);
    assert.match(String(card.source.reviewed_git_revision), /^[0-9a-f]{40}$/);
    assert.equal(card.source.reviewed_git_revision, ctx.reviewedGitRevision);
    assert.equal(normalizeSha(card.source.content_sha256), liveReviewSha);
    assert.equal(card.tested_source_revision, ctx.sha(MATRIX_RELATIVE_PATH));
    assert.ok(typeof card.summary === "string" && card.summary.length > 0);
    assert.ok(typeof card.concern_class === "string" && card.concern_class.length > 0);
    assert.ok(typeof card.session_question === "string" && card.session_question.length > 0);
  }
});

test("proof class, evidence class, check outcome, residual and non-claims agree with the matrix", () => {
  for (const card of report.cards) {
    const row = rowById.get(card.finding_id);
    assert.ok(row, `matrix row missing for ${card.finding_id}`);
    assert.ok(PROOF_CLASSES.includes(card.proof_class));
    assert.equal(card.proof_class, row.required_proof_class);
    assert.equal(card.evidence_class, row.class_match === true ? row.required_proof_class : "docs");
    assert.ok(PROOF_CLASSES.includes(card.evidence_class));
    assert.ok(CHECK_OUTCOMES.includes(card.check_outcome));
    assert.equal(card.check_outcome, row.machine_verdict);
    assert.equal(card.mismatch_reason_code ?? null, row.mismatch_reason_code ?? null);
    assert.equal(card.residual_scope, row.residual_scope);
    assert.deepEqual(card.non_claims, row.non_claims);
    assert.ok(card.non_claims.length > 0);
  }
});

test("every proposed disposition is in the closed RC28 dictionary and constrained by the verdict", () => {
  for (const card of report.cards) {
    assert.ok(
      RC28_DISPOSITIONS.includes(card.proposed_disposition),
      `${card.finding_id} disposition ${card.proposed_disposition}`,
    );
    assert.equal(card.proposed_disposition === "already_satisfied", card.check_outcome === "evidence_present_class_matched");
    if (card.check_outcome === "evidence_absent_residual_named" || card.check_outcome === "evidence_class_mismatch") {
      assert.notEqual(card.proposed_disposition, "already_satisfied");
    }
  }
});

test("nothing is preselected, selected or answered, and the recommendation is advisory non-consent", () => {
  for (const card of report.cards) {
    assert.deepEqual(card.recommendation, { advisory: true, is_consent: false });
    assert.equal(card.preselected, false);
    assert.equal(card.selected, false);
    assert.equal(card.human_answer, null);
    for (const required of ALTERNATIVE_IDS) {
      assert.ok(
        card.alternatives.some((alternative) => alternative.id === required),
        `${card.finding_id} misses alternative ${required}`,
      );
    }
  }
  assert.equal(report.summary.preselected_count, 0);
  assert.equal(report.summary.selected_count, 0);
  assert.equal(report.summary.human_answer_count, 0);
  assert.equal(report.summary.advisory_recommendation_count, FINDING_IDS.length);
  assert.equal(report.recommendation_model.advisory, true);
  assert.equal(report.recommendation_model.is_consent, false);
  assert.equal(report.recommendation_model.preselected, false);
  assert.equal(report.boundary.options_selected, 0);
  assert.equal(report.boundary.dispositions_recorded, 0);
  assert.equal(report.boundary.review_case_events_written, false);
  assert.equal(report.boundary.record_human_disposition_called, false);
  assert.deepEqual(report.boundary.requirements_promoted, []);
});

test("grouping is by concern class and covers all 19 findings exactly once", () => {
  assert.equal(report.grouping.length, GROUP_DEFS.length);
  const seen = [];
  for (const group of report.grouping) {
    const def = GROUP_DEFS.find((candidate) => candidate.group_id === group.group_id);
    assert.ok(def, `unknown group ${group.group_id}`);
    assert.equal(group.concern_class, def.concern_class);
    assert.equal(group.count, group.finding_ids.length);
    for (const id of group.finding_ids) {
      seen.push(id);
      assert.equal(cardById.get(id).group, group.group_id);
      assert.equal(cardById.get(id).concern_class, def.concern_class);
    }
  }
  assert.deepEqual(seen.sort(), [...FINDING_IDS].sort());
});

test("RC28-F18 keeps bounded adoption evidence, live v2 refs and a forbidden auto-close", () => {
  const card = cardById.get("RC28-F18");
  assert.equal(card.auto_close, false);
  assert.equal(card.adoption_evidence_status, "bounded_adoption_evidence_present");
  assert.equal(card.criterion_id, F18_CRITERION_ID);
  assert.equal(card.owner_status, "bounded_adoption_established");
  assert.equal(card.independent_evaluation_status, "pending");
  assert.equal(card.ledger_disposition_status, "pending");
  assert.equal(card.proposed_disposition, "deferred");
  for (const required of F18_ADOPTION_REFS) {
    const ref = card.adoption_refs.find((candidate) => candidate.path === required.path);
    assert.ok(ref, `missing adoption ref ${required.path}`);
    assert.equal(normalizeSha(ref.sha256), ctx.sha(required.path));
  }
  assert.ok(rowById.get("RC28-F18").residual_scope.includes(F18_CRITERION_ID));
});

test("RC28-F13 is an explicit owner defer and RC28-F01 / RC28-F15 defer on D519 without already_satisfied", () => {
  const f13 = cardById.get("RC28-F13");
  assert.equal(f13.owner_status, "deferred-explicit");
  assert.equal(f13.proposed_disposition, "deferred");
  assert.equal(f13.human_answer, null);
  for (const id of ["RC28-F01", "RC28-F15"]) {
    const card = cardById.get(id);
    assert.equal(card.deferral_reference, "D519");
    assert.equal(card.deferral_treated_as_proof, false);
    assert.equal(card.proposed_disposition, "deferred");
    assert.notEqual(card.proposed_disposition, "already_satisfied");
  }
});

test("the presentation carries each finding row exactly once and the required sections", () => {
  const lines = presentationText.split("\n");
  for (const id of FINDING_IDS) {
    const rows = lines.filter((line) => line.startsWith(`| ${id} |`)).length;
    assert.equal(rows, 1, `presentation rows for ${id}`);
  }
  for (const header of ["## Что это", "## Группы", "## Правила сессии", "## Non-claims"]) {
    assert.ok(presentationText.includes(header), `presentation misses ${header}`);
  }
  for (const def of GROUP_DEFS) {
    assert.ok(presentationText.includes(`### Группа: ${def.label_ru}`), `missing group ${def.label_ru}`);
  }
  assert.ok(presentationText.includes("preselected=false"));
  assert.ok(presentationText.includes("read back"));
  assert.ok(presentationText.includes("RC28 HOLD") || presentationText.includes("HOLD"));
  assert.ok(presentationText.includes("auto_close=false") || presentationText.includes("auto-close"));
  assert.ok(/[А-Яа-я]/.test(presentationText), "the presentation must be Russian prose");
});

test("validateCards reports no findings on the real artifacts", () => {
  assert.deepEqual(validateCards(report, ctx, { jsonText: cardsText, presentationText }), []);
  assert.deepEqual(rendered.codes, []);
});

test("the CLI checks byte identity, prints the cards and rejects unknown arguments", () => {
  const check = runCli(["--check"]);
  assert.equal(check.exitCode, 0);
  assert.ok(check.stdout.includes("M210_S04_CARDS_CHECK_OK"));

  const print = runCli(["--print"]);
  assert.equal(print.exitCode, 0);
  assert.ok(print.stderr.includes("M210_S04_CARDS_PRINTED"));
  const printed = JSON.parse(print.stdout.join("\n"));
  assert.equal(printed.cards.length, FINDING_IDS.length);

  const dryRun = runCli(["--write"], { dryRun: true });
  assert.equal(dryRun.exitCode, 0);
  assert.equal(dryRun.wrote, false);

  const bad = runCli(["--nope"]);
  assert.equal(bad.exitCode, 2);
  assert.ok(bad.stderr.some((line) => line.includes("unknown argument")));

  const driftCards = runCli(["--check"], { committedCardsText: `${cardsText}x` });
  assert.equal(driftCards.exitCode, 1);
  assert.ok(driftCards.stderr.some((line) => line.includes("check_not_byte_identical")));

  const driftPresentation = runCli(["--check"], { committedPresentationText: `${presentationText}x` });
  assert.equal(driftPresentation.exitCode, 1);
  assert.ok(driftPresentation.stderr.some((line) => line.includes("check_not_byte_identical")));
});

test("CODE_COVERAGE: every declared fail-closed code is empirically emitted", () => {
  const observed = new Set();
  const record = (codes) => {
    for (const code of codes) observed.add(code);
  };

  record(codesFor((r) => r.cards.pop()));
  record(codesFor((r) => delete r.cards[0].source.content_sha256));
  record(codesFor((r) => delete r.cards[0].proof_class));
  record(codesFor((r) => delete r.cards[0].check_outcome));
  record(codesFor((r) => (r.cards[0].residual_scope = "")));
  record(codesFor((r) => (r.cards[0].non_claims = [])));
  record(
    codesFor((r) => {
      r.cards[0].alternatives = r.cards[0].alternatives.filter((alt) => alt.id !== "stop_session");
    }),
  );
  record(codesFor((r) => (r.cards[0].recommendation.is_consent = true)));
  record(codesFor((r) => (r.cards[0].selected = true)));
  record(
    codesFor(() => {}, {
      presentationText: presentationText.replace(/^\| RC28-F19 \|.*$/m, ""),
    }),
  );
  record(
    codesFor(() => {}, {
      presentationText: presentationText.replace(/^(\| RC28-F01 \|)/m, "$1\n$1"),
    }),
  );
  record(
    codesFor((r) => {
      r.cards.find((card) => card.finding_id === "RC28-F18").auto_close = true;
    }),
  );
  record(
    codesFor((r) => {
      r.cards.find((card) => card.finding_id === "RC28-F13").owner_status = "missing-answer";
    }),
  );
  record(
    codesFor((r) => {
      r.cards.find((card) => card.finding_id === "RC28-F01").deferral_treated_as_proof = true;
    }),
  );
  record(
    codesFor((r) => {
      r.cards.find((card) => card.finding_id === "RC28-F06").proposed_disposition = "already_satisfied";
    }),
  );
  record(codesFor(() => {}, { jsonText: `${cardsText}\u00e9` }));
  record(codesFor(() => {}, { jsonText: `${cardsText}<` }));

  const checkDrift = runCli(["--check"], { committedCardsText: `${cardsText}x` });
  for (const line of checkDrift.stderr) {
    const code = line.split(":")[0];
    if (code === "check_not_byte_identical") observed.add(code);
  }

  const missing = EMITTABLE_CODES.filter((code) => !observed.has(code));
  assert.deepEqual(missing, [], `codes never emitted: ${missing.join(", ")}`);
  for (const code of observed) {
    assert.ok(EMITTABLE_CODES.includes(code), `undeclared code emitted: ${code}`);
  }
});

after(() => {
  process.stdout.write(`${CONTRACT_MARKER}\n`);
});
