// M210 S02 adoption v2 contract.
//
// Offline node --test contract binding the corrected decision chain:
// prd/architecture/m210-s02-answer-record-v2.json (the owner's recorded
// direction, superseding the v1 pending stop) and
// prd/architecture/m210-s02-adoption-checkpoint-v2.md (the bounded grant
// superseding the v1 not-adopted checkpoint). Claims under test: v2 records
// supersede the exact v1 bytes; the recorded direction is variant C
// (abstention-first candidates) with authenticated interactive references;
// F13 is an explicit deferred disposition; composition, precedence and case
// applicability stay outside the grant; the grant line appears exactly once
// and requires the interactive reference; the section 3 pin is unchanged;
// the checkpoint file is canonical ASCII while the answer record intentionally
// keeps the Russian owner verbatim.
//
// Run: node --test scripts/m210_s02_adoption_v2_contract.test.mjs

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const V1_REC = path.join(ROOT, "prd/architecture/m210-s02-answer-record.json");
const REC2 = path.join(ROOT, "prd/architecture/m210-s02-answer-record-v2.json");
const CKPT1 = path.join(ROOT, "prd/architecture/m210-s02-adoption-checkpoint.md");
const CKPT2 = path.join(ROOT, "prd/architecture/m210-s02-adoption-checkpoint-v2.md");

const read = (p) => readFileSync(p, "utf8");
const sha256 = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const IR_CRITERION = "37181c25-88b0-4896-bffe-d10642970e6f";
const F13_CRITERION = "70e39300-851b-4412-a322-a8f0c51ca71c";
const PIN = "a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6";

test("answer record v2 supersedes the exact v1 bytes and records the direction", () => {
  const rec = JSON.parse(read(REC2));
  assert.equal(rec.schema, "law-nexus/m210-s02-answer-record/v2");
  assert.equal(rec.supersedes.path, "prd/architecture/m210-s02-answer-record.json");
  assert.equal(rec.supersedes.sha256, sha256(V1_REC));
  assert.equal(rec.answer_source, "interactive");
  assert.equal(rec.status, "owner_decision_recorded");
  assert.equal(rec.sanctioned_stop, false);
  assert.equal(rec.guards.review_case_events_written, 0);
  assert.equal(rec.guards.agent_selected, false);
  assert.equal(rec.ir_answer.interactive_refs ?? rec.interactive_refs.ir.criterion_id, rec.interactive_refs.ir.criterion_id);
  assert.equal(rec.interactive_refs.ir.criterion_id, IR_CRITERION);
  assert.equal(rec.interactive_refs.f13.criterion_id, F13_CRITERION);
  assert.equal(rec.ir_answer.selected_option, "C abstention_first_candidates_only");
  assert.ok(rec.ir_answer.verbatim_response.includes("хранение кандидатов нормативных утверждений"));
  assert.equal(rec.ascii_only, false);
  assert.ok(rec.ascii_only_reason.includes("Russian"));
});

test("F13 is an explicit deferred disposition, never inferred", () => {
  const rec = JSON.parse(read(REC2));
  assert.equal(rec.f13_status, "deferred-explicit");
  assert.equal(rec.f13_answer.selected_option, "keep_deferred");
  assert.ok(rec.f13_answer.verbatim_response.length > 0);
  assert.equal(rec.f13_answer.criterion_id, F13_CRITERION);
});

test("scope exclusions and evidence boundaries are recorded", () => {
  const rec = JSON.parse(read(REC2));
  const joined = rec.non_claims.join(" ");
  assert.ok(joined.includes("Rule composition, precedence resolution and case applicability are outside"));
  assert.ok(joined.includes("separate future decision"));
  assert.ok(joined.includes("No Review Case event"));
  assert.ok(joined.includes("never means that no norm exists"));
  assert.ok(rec.owner_clarifications.some((c) => c.includes("temporal_qualification")));
});

test("checkpoint v2 grants exactly once, bounded, with interactive refs", () => {
  const md = read(CKPT2);
  assertAscii(md, "checkpoint v2");
  assert.equal((md.match(/\*\*admission: granted\*\*/g) || []).length, 1);
  assert.ok(md.includes(CKPT1.slice(ROOT.length + 1)));
  assert.ok(md.includes(`criterion ${IR_CRITERION}`));
  assert.ok(md.includes(`criterion ${F13_CRITERION}`));
  assert.ok(md.includes("**owner_admission_ref:** subjective-UAT criterion"));
  assert.ok(md.includes("lifted for the adopted candidate-layer scope only"));
  assert.ok(md.includes("Still forbidden without a separate adopted contract"));
  assert.ok(md.includes(PIN));
  assert.ok(md.includes(sha256(REC2)));
});

test("checkpoint v2 supersedes the v1 checkpoint without rewriting it", () => {
  const v1 = read(CKPT1);
  assert.ok(v1.includes("**admission: not-adopted**"));
  const v2 = read(CKPT2);
  assert.ok(v2.includes(sha256(CKPT1)));
  assert.ok(v2.includes("v1 stays byte-identical") || v2.includes("stays byte-identical"));
});

test("mutation detectors fail closed", () => {
  const grantRequiresRef = (md) =>
    /admission: granted/.test(md) && !md.includes("**owner_admission_ref:** subjective-UAT criterion")
      ? ["grant_without_interactive_ref"]
      : [];
  const rec = JSON.parse(read(REC2));
  const scopeOverclaim = (obj) =>
    !obj.non_claims.join(" ").includes("case applicability are outside") ? ["scope_overclaim"] : [];
  const mdWithoutRef = read(CKPT2).replace(/\*\*owner_admission_ref:\*\*[^\n]*\n/, "");
  assert.deepEqual(grantRequiresRef(mdWithoutRef), ["grant_without_interactive_ref"]);
  assert.deepEqual(grantRequiresRef(read(CKPT2)), []);
  assert.deepEqual(scopeOverclaim({ non_claims: ["something else"] }), ["scope_overclaim"]);
  assert.deepEqual(scopeOverclaim(rec), []);
});

function assertAscii(s, label) {
  for (let i = 0; i < s.length; i += 1) {
    assert.ok(s.charCodeAt(i) <= 0x7f, `${label} carries a non-ASCII byte at ${i}`);
  }
}
