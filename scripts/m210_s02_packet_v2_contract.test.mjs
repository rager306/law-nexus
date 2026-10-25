// M210 S02 packet v2 correction contract.
//
// Offline node --test contract for the corrected decision packet:
// prd/architecture/m210-s02-owner-decision-packet-v2.json, its human entry
// prd/architecture/m210-s02-owner-decision-presentation-v2.md and the
// correction record prd/architecture/m210-s02-packet-corrections-v2.md.
//
// Claims under test: v2 exists and supersedes the exact v1 bytes; the five
// option identities and labels are byte-equal to v1; candidate verdicts stay
// {Unknown, Conflict} while provenance links stay {resolved, unresolved,
// conflicted}; absence semantics hold for every variant; the corpus probes
// are declared coverage labels; the NormRule spine is declared a structural
// prototype with four algebra defaults; the C recommendation is framed as
// smallest-new-surface and never as the only safe representation; the four
// new fail-closed codes are declared and empirically emitted on mutation;
// every artifact is canonical ASCII with no adoption claim, no raw legal
// text and no Rust implementation marker.
//
// Run: node --test scripts/m210_s02_packet_v2_contract.test.mjs

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const V1 = path.join(ROOT, "prd/architecture/m210-s02-owner-decision-packet.json");
const V2 = path.join(ROOT, "prd/architecture/m210-s02-owner-decision-packet-v2.json");
const PRES = path.join(ROOT, "prd/architecture/m210-s02-owner-decision-presentation-v2.md");
const MEMO = path.join(ROOT, "prd/architecture/m210-s02-packet-corrections-v2.md");

const read = (p) => readFileSync(p, "utf8");
const sha256 = (s) => createHash("sha256").update(s).digest("hex");
const assertAscii = (s, label) => {
  for (let i = 0; i < s.length; i += 1) {
    assert.ok(s.charCodeAt(i) <= 0x7f, `${label} carries a non-ASCII byte at ${i}`);
  }
};

const NEW_CODES = [
  "verdict_semantics_merged",
  "absence_collapsed_to_nonexistence",
  "probe_status_overstated",
  "spine_reuse_overstated",
];

// Detector for the documented fail-closed codes; emitted on mutated copies.
function detectViolations(packet) {
  const codes = [];
  if (packet.semantics_adopted !== false || /admission: granted/.test(JSON.stringify(packet))) {
    codes.push("adoption_claim");
  }
  const vs = packet.verdict_semantics ?? {};
  const candidate = new Set(vs.candidate_verdict_domain ?? []);
  if (candidate.has("resolved") || candidate.has("unresolved") || candidate.has("conflicted")) {
    codes.push("verdict_semantics_merged");
  }
  if (!vs.provenance_link_verdict_domain || vs.provenance_link_verdict_domain.join() !== "resolved,unresolved,conflicted") {
    codes.push("verdict_semantics_merged");
  }
  const abs = packet.absence_semantics ?? {};
  if (typeof abs.rule !== "string" || !abs.rule.includes("never the statement that no norm exists")) {
    codes.push("absence_collapsed_to_nonexistence");
  }
  const probes = packet.probe_evidence_status?.corpus_probes ?? "";
  if (!probes.includes("coverage labels")) {
    codes.push("probe_status_overstated");
  }
  const spine = packet.spine_status?.algebra_defaults ?? [];
  if (!Array.isArray(spine) || spine.length !== 4) {
    codes.push("spine_reuse_overstated");
  }
  return codes;
}

test("v2 artifacts exist and are canonical ASCII", () => {
  for (const [p, label] of [[V2, "packet v2"], [PRES, "presentation v2"], [MEMO, "corrections memo"]]) {
    const s = read(p);
    assertAscii(s, label);
    assert.ok(!/pub fn|pub struct|<Decree|<ЗАКОН/.test(s), `${label} carries an implementation or raw-text marker`);
  }
});

test("v2 supersedes the exact v1 bytes", () => {
  const v1raw = read(V1);
  const packet = JSON.parse(read(V2));
  assert.equal(packet.schema, "law-nexus/m210-s02-owner-decision-packet/v2");
  assert.equal(packet.schema_version, 2);
  assert.equal(packet.supersedes.path, "prd/architecture/m210-s02-owner-decision-packet.json");
  assert.equal(packet.supersedes.sha256, sha256(v1raw));
  assert.ok(read(MEMO).includes("RC28-F19"));
});

test("option identities and labels are byte-equal to v1", () => {
  const v1 = JSON.parse(read(V1));
  const v2 = JSON.parse(read(V2));
  const norm = (p) => p.ir_question.options.map((o) => [o.option_id, o.label, o.consequences]);
  assert.deepEqual(norm(v2), norm(v1));
  assert.deepEqual(v2.ir_question.options.map((o) => o.option_id), ["A", "B", "C", "reject_all", "defer"]);
  for (const key of Object.keys(v1.f13_question)) {
    assert.deepEqual(v2.f13_question[key], v1.f13_question[key], `f13 field ${key} changed`);
  }
  assert.equal(
    v2.f13_question.adjacent_work_note,
    "external review recommends scheduling source-level operation-candidate grammar as separate near-term work against the design-only operation registry; advisory and non-binding, it does not change this HOLD",
  );
});

test("verdict semantics and absence semantics are declared and separated", () => {
  const packet = JSON.parse(read(V2));
  assert.deepEqual(packet.verdict_semantics.candidate_verdict_domain, ["Unknown", "Conflict"]);
  assert.deepEqual(packet.verdict_semantics.provenance_link_verdict_domain, ["resolved", "unresolved", "conflicted"]);
  assert.ok(packet.verdict_semantics.rule.includes("never raises the legal status"));
  assert.equal(Object.keys(packet.verdict_semantics.dimensions).length, 4);
  assert.equal(packet.absence_semantics.applies_to_variants.length, 3);
  assert.ok(packet.absence_semantics.rule.includes("never the statement that no norm exists"));
});

test("probe status and spine prototype status are recorded", () => {
  const packet = JSON.parse(read(V2));
  assert.ok(packet.probe_evidence_status.corpus_probes.includes("[0,4096)"));
  assert.ok(packet.probe_evidence_status.decision_basis.includes("not demonstrated extraction"));
  assert.equal(packet.spine_status.status.includes("structural prototype"), true);
  assert.equal(packet.spine_status.algebra_defaults.length, 4);
});

test("C rationale is minimal-surface framed, never only-safe framed", () => {
  const packet = JSON.parse(read(V2));
  const r = packet.ir_question.recommendation.rationale;
  assert.ok(r.includes("smallest new semantic decision surface"));
  assert.ok(r.includes("not the only safe representation"));
  assert.ok(r.includes("not the owner decision"));
  assert.equal(packet.ir_question.recommendation.option_id, "C");
});

test("new non-claims and fail-closed codes are declared", () => {
  const packet = JSON.parse(read(V2));
  const joined = packet.non_claims.join(" ");
  assert.ok(joined.includes("never raises the legal status"));
  assert.ok(joined.includes("never means that no norm exists"));
  assert.ok(joined.includes("coverage labels"));
  for (const code of NEW_CODES) assert.ok(packet.fail_closed_codes.includes(code), `missing code ${code}`);
});

test("documented fail-closed codes are emitted on mutated copies", () => {
  const base = JSON.parse(read(V2));
  assert.deepEqual(detectViolations(base), []);
  const adopted = JSON.parse(JSON.stringify(base));
  adopted.semantics_adopted = true;
  assert.ok(detectViolations(adopted).includes("adoption_claim"));
  const merged = JSON.parse(JSON.stringify(base));
  merged.verdict_semantics.candidate_verdict_domain.push("resolved");
  assert.ok(detectViolations(merged).includes("verdict_semantics_merged"));
  const absent = JSON.parse(JSON.stringify(base));
  delete absent.absence_semantics;
  assert.ok(detectViolations(absent).includes("absence_collapsed_to_nonexistence"));
  const overstated = JSON.parse(JSON.stringify(base));
  overstated.probe_evidence_status.corpus_probes = "eight extracted obligations";
  assert.ok(detectViolations(overstated).includes("probe_status_overstated"));
  const spineGone = JSON.parse(JSON.stringify(base));
  delete spineGone.spine_status;
  assert.ok(detectViolations(spineGone).includes("spine_reuse_overstated"));
});

test("presentation v2 carries the supersedes line, questions and read-back", () => {
  const pres = read(PRES);
  assert.ok(pres.includes("Supersedes `m210-s02-owner-decision-presentation.md` (v1)"));
  assert.ok(pres.includes("m210-s02-ir-question"));
  assert.ok(pres.includes("m210-s02-f13-question"));
  assert.ok(pres.includes("ir_verbatim_response"));
  assert.ok(pres.includes("no option is preselected"));
  assert.ok(pres.includes("coverage labels"));
  assert.ok(!/admission: granted/.test(pres));
});
