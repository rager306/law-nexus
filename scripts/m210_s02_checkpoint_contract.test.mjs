// M210-3afp79 S02 T05 admission-checkpoint contract.
//
// Offline and fail-closed. The artifacts under test are
// prd/architecture/m210-s02-adoption-checkpoint.md (the human-gate checkpoint)
// and prd/architecture/m210-s02-dictionary-delta.json (the gated section 3
// dictionary delta). The checkpoint is a checkpoint, not a grant: while it
// records `**admission: not-adopted**` nothing is adopted, no section 3 row is
// applied and no requirement is promoted.
//
// The claims under test are that exactly one verdict line matches
// /^\*\*admission: (granted|not-adopted)\*\*$/m, that the mandatory header
// fields and level-## sections are present and non-empty, that a grant is
// accepted only with a real interactive reference AND a verified governing
// surface AND an answered interactive source (a bare name, a role, a milestone
// closeout, a lock or an integrity PASS is refused), that the resume condition
// names an interactive source, that F13 stays on hold and is never derived from
// the IR answer, that the Review Case event guard is zero and no requirement is
// promoted, that the dictionary delta stays applied false while the verdict is
// not granted and prd/temporal-legal-model.md stays byte-identical to its pin,
// that the delta materializes exactly the required_new_adr_terms of the three
// S01 variants, that the checkpoint cites resolvable tracked sources by sha256,
// that the artifacts carry no runtime marker, no raw text and no non-ASCII byte,
// and that each documented fail-closed code is empirically emitted by a
// mutation.
//
// This contract spawns no subprocess, opens no socket and reads only
// repository-relative tracked artifacts under prd/, doc/ and scripts/. It never
// writes a file.
//
// Run: node --test scripts/m210_s02_checkpoint_contract.test.mjs

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// verdict_missing: the checkpoint carries no verdict line matching the admission expression.
// verdict_ambiguous: the checkpoint carries more than one verdict line.
// header_field_missing: a mandatory bold header field is absent or empty.
// section_missing: a mandatory level-## section is absent.
// sources_insufficient: the Sources checked table carries fewer rows than the declared minimum.
// source_unresolved: a cited source is not repository-relative, is ignored, is absolute, traverses, or does not exist.
// source_hash_mismatch: a cited source digest does not match the live file content.
// source_revision_mismatch: the source revision is absent, malformed, or differs from the T01 rebind snapshot.
// owner_admission_ref_missing: a grant lacks a real interactive reference, a verified governing surface or an answered interactive source; or a not-adopted checkpoint carries an inadmissible reference.
// lock_as_admission: a lock is used as the basis of a grant.
// integrity_pass_as_admission: an integrity result is used as the basis of a grant.
// resume_condition_missing: the resume condition is absent or does not name an interactive source.
// f13_status_missing: the F13 status header is absent or empty.
// f13_inferred_from_ir: the F13 status is not hold while no separate F13 answer exists.
// review_case_event_written: the Review Case event guard is not zero.
// requirements_promoted: a requirement promotion is declared or a promotion header is non-zero.
// delta_applied_without_grant: the dictionary delta is applied while the checkpoint verdict is not granted.
// section3_mutated: the live section 3 target no longer matches the recorded pin, or the delta points at another target.
// proposed_rows_mismatch: the delta proposed rows or the per-variant conditional rows disagree with the S01 variant terms or carry an applied shape.
// runtime_claim_present: an artifact carries a Rust implementation marker.
// raw_text_leak: an artifact carries an XML tag or a provider text marker.
// non_ascii_artifact: an artifact carries a non-ASCII byte.
// DOCUMENTED_CODES_END

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const root = path.resolve(HERE, "..");

export const CHECKPOINT_REL = "prd/architecture/m210-s02-adoption-checkpoint.md";
export const DELTA_REL = "prd/architecture/m210-s02-dictionary-delta.json";
export const CONTRACT_REL = "scripts/m210_s02_checkpoint_contract.test.mjs";
export const ANSWER_REL = "prd/architecture/m210-s02-answer-record.json";
export const GOVERNING_REL = "prd/architecture/m210-s02-governing-surface-check.json";
export const REBIND_REL = "prd/architecture/m210-s02-rebind-report.json";
export const IR_ALTERNATIVES_REL = "prd/architecture/m210-s01-ir-alternatives.json";
export const SECTION3_REL = "prd/temporal-legal-model.md";

export const SCHEMA = "law-nexus/m210-s02-dictionary-delta/v1";
export const KIND = "m210-s02-dictionary-delta";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S02";
export const TASK = "T05";
export const TARGET_FILE = "prd/temporal-legal-model.md";
export const TARGET_SECTION = "section 3 Glossary and ownership";

export const REQUIRED_HEADERS = [
  "recorded",
  "milestone / slice",
  "classification",
  "scope",
  "source_revision",
  "owner_admission_ref",
  "interaction_ref",
  "f13_status",
  "runtime_stop",
  "review_case_events_written",
  "dictionary_delta",
  "contract",
];

export const REQUIRED_SECTIONS = [
  "## Purpose and boundary",
  "## Sources checked",
  "## Answer provenance",
  "## Governing surface check",
  "## Scope and revision",
  "## F13 status",
  "## Dictionary delta",
  "## Resume condition",
  "## Fail-closed boundary",
  "## Marker semantics",
  "## Non-claims",
];

export const EMITTABLE_CODES = [
  "verdict_missing",
  "verdict_ambiguous",
  "header_field_missing",
  "section_missing",
  "sources_insufficient",
  "source_unresolved",
  "source_hash_mismatch",
  "source_revision_mismatch",
  "owner_admission_ref_missing",
  "lock_as_admission",
  "integrity_pass_as_admission",
  "resume_condition_missing",
  "f13_status_missing",
  "f13_inferred_from_ir",
  "review_case_event_written",
  "requirements_promoted",
  "delta_applied_without_grant",
  "section3_mutated",
  "proposed_rows_mismatch",
  "runtime_claim_present",
  "raw_text_leak",
  "non_ascii_artifact",
];

export const DELTA_CODES = [
  "delta_applied_without_grant",
  "section3_mutated",
  "proposed_rows_mismatch",
  "non_ascii_artifact",
  "runtime_claim_present",
];

export const CONTRACT_MARKER = "M210_S02_CHECKPOINT_OK";

const MIN_SOURCES = 6;
const EXPECTED_SOURCES = 10;

const REVISION_RE = /^sha256:[0-9a-f]{64}$/;
const RESUME_RE = /interaction|subjective-UAT|criterion id/;
const VERDICT_RE = /^\*\*admission: (granted|not-adopted)\*\*$/m;
const VERDICT_ANY_RE = /^\*\*admission: .*\*\*$/gm;
const INTERACTIVE_REF_RE =
  /^(?:interaction\s+)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|^criterion[:/][A-Za-z0-9][A-Za-z0-9._:/-]{3,}$/i;
const LOCK_RE = /d499|\bgsd[_ ]?milestone[_ ]?lock\b/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b/i;

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const IGNORED_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const UNTRACKED_SOURCE = "prd/architecture/m210-s02-checkpoint-untracked.yaml";
const MISSING_SOURCE = "prd/architecture/m210-s02-checkpoint-missing.md";
// Built by join so this contract never carries an ignored or absolute path as a
// declared string literal.
const IGNORED_SOURCE = [".agents", "skills", "law-nexus-rust", "SKILL.md"].join("/");
const ABSOLUTE_SOURCE = ["", "tmp", "m210-s02-checkpoint.md"].join("/");

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
}

const hashCache = new Map();

function sha256(relativePath) {
  if (hashCache.has(relativePath)) return hashCache.get(relativePath);
  const digest = createHash("sha256")
    .update(readFileSync(path.join(root, relativePath)))
    .digest("hex");
  hashCache.set(relativePath, digest);
  return digest;
}

function sha256Text(text) {
  return createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex");
}

// ---------------------------------------------------------------------------
// document parsing helpers
// ---------------------------------------------------------------------------

function headerValue(doc, key) {
  const lines = doc.split("\n");
  const prefix = `**${key}:**`;
  const start = lines.findIndex((line) => line.startsWith(prefix));
  if (start === -1) return null;
  const parts = [lines[start].slice(prefix.length)];
  for (let i = start + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.startsWith("**") || line.startsWith("#") || line.trim() === "") break;
    parts.push(line);
  }
  return parts.join(" ").trim();
}

function section(doc, heading) {
  const lines = doc.split("\n");
  const start = lines.findIndex((line) => line === heading);
  if (start === -1) return null;
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i += 1) {
    if (lines[i].startsWith("## ")) {
      end = i;
      break;
    }
  }
  return lines.slice(start, end).join("\n");
}

function flat(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/\s+/g, " ")
    .trim();
}

function sourceRows(doc) {
  return [...doc.matchAll(/^\| `([^`]+)` \| `([0-9a-f]{64})` \|/gm)].map((match) => ({
    path: match[1],
    sha: match[2],
  }));
}

function sameSet(a, b) {
  return Array.isArray(a) && a.length === b.length && a.every((item) => b.includes(item));
}

// ---------------------------------------------------------------------------
// live artifacts
// ---------------------------------------------------------------------------

const liveCheckpointText = readRepo(CHECKPOINT_REL);
const liveDeltaText = readRepo(DELTA_REL);
const liveAnswer = JSON.parse(readRepo(ANSWER_REL));
const liveGoverning = JSON.parse(readRepo(GOVERNING_REL));
const liveRebind = JSON.parse(readRepo(REBIND_REL));
const liveIrAlternatives = JSON.parse(readRepo(IR_ALTERNATIVES_REL));
const liveDelta = JSON.parse(liveDeltaText);
const liveSection3Text = readRepo(SECTION3_REL);

const live = {
  answer: liveAnswer,
  governing: liveGoverning,
  delta: liveDelta,
  irAlternatives: liveIrAlternatives,
  section3Text: liveSection3Text,
  expectedRevision: liveRebind.source_revision,
};

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateCheckpoint(doc, options = {}) {
  const answer = options.answer ?? live.answer;
  const governing = options.governing ?? live.governing;
  const delta = options.delta ?? live.delta;
  const irAlternatives = options.irAlternatives ?? live.irAlternatives;
  const section3Text = options.section3Text ?? live.section3Text;
  const expectedRevision = options.expectedRevision ?? live.expectedRevision;
  const fileExists = options.fileExists ?? repoExists;

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });
  const flatDoc = flat(doc);

  // (1) text hygiene.
  if ([...doc].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the checkpoint carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (doc.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (doc.includes(marker)) add("runtime_claim_present", `runtime marker ${marker}`);
  }

  // (2) verdict shape: at most one line, and only one of the two known values.
  const verdictLines = doc.match(VERDICT_ANY_RE) || [];
  const verdictMatch = doc.match(VERDICT_RE);
  const verdict = verdictMatch ? verdictMatch[1] : null;
  if (verdictLines.length === 0 || verdict === null) {
    add("verdict_missing", verdictLines.join(" | "));
  }
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));

  // (3) mandatory header fields and sections.
  for (const key of REQUIRED_HEADERS) {
    const value = headerValue(doc, key);
    if (value === null || value.trim() === "") add("header_field_missing", key);
  }
  for (const heading of REQUIRED_SECTIONS) {
    if (!doc.split("\n").includes(heading)) add("section_missing", heading);
  }

  // (4) byte-bound sources.
  const rows = sourceRows(doc);
  if (rows.length < MIN_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    if (IGNORED_PREFIXES.some((prefix) => row.path.startsWith(prefix))) {
      add("source_unresolved", `ignored ${row.path}`);
      continue;
    }
    if (row.path.startsWith("/")) {
      add("source_unresolved", `absolute ${row.path}`);
      continue;
    }
    if (row.path.split("/").includes("..")) {
      add("source_unresolved", `traversal ${row.path}`);
      continue;
    }
    if (!fileExists(row.path)) {
      add("source_unresolved", row.path);
      continue;
    }
    if (sha256(row.path) !== row.sha) add("source_hash_mismatch", row.path);
  }

  // (5) the tested revision is the T01 rebind snapshot.
  const revision = flat(headerValue(doc, "source_revision"));
  if (!REVISION_RE.test(revision)) {
    add("source_revision_mismatch", `malformed ${revision}`);
  } else if (typeof expectedRevision === "string" && revision !== expectedRevision) {
    add("source_revision_mismatch", "differs from the T01 rebind snapshot");
  }

  // (6) grant provenance. A grant needs a real interactive reference, a verified
  // governing surface and an answered interactive source; a lock, an integrity
  // result, a bare name or a role is never a grantor reference.
  const ownerRef = flat(headerValue(doc, "owner_admission_ref"));
  const interactionRef = flat(headerValue(doc, "interaction_ref"));
  const basis = flat(headerValue(doc, "admission_basis"));
  const answered = answer?.status === "answered";
  const surfaceVerified = governing?.verdict === "governing_surface_verified";
  const interactiveRefs =
    INTERACTIVE_REF_RE.test(ownerRef) && INTERACTIVE_REF_RE.test(interactionRef);

  if (verdict === "granted") {
    if (!interactiveRefs || !surfaceVerified || !answered) {
      add(
        "owner_admission_ref_missing",
        `owner=${ownerRef} interaction=${interactionRef} surface=${governing?.verdict} answer=${answer?.status}`,
      );
    }
    const grantBasis = `${basis} ${ownerRef} ${interactionRef}`;
    if (LOCK_RE.test(grantBasis)) add("lock_as_admission", grantBasis);
    if (INTEGRITY_RE.test(grantBasis)) add("integrity_pass_as_admission", grantBasis);
  } else if (verdict === "not-adopted") {
    const refNone = ownerRef === "none" && interactionRef === "none";
    if (!refNone && !(interactiveRefs && answered)) {
      add("owner_admission_ref_missing", `not-adopted carries an inadmissible reference owner=${ownerRef}`);
    }
  }

  // (7) resume condition names an interactive source.
  const resumeSection = section(doc, "## Resume condition");
  if (resumeSection === null || !RESUME_RE.test(flat(resumeSection))) {
    add("resume_condition_missing", flat(resumeSection || "").slice(0, 80));
  }

  // (8) F13 stays on hold while no separate F13 answer exists.
  const f13 = flat(headerValue(doc, "f13_status"));
  if (f13 === "") add("f13_status_missing", "the F13 status header is empty");
  const f13Selected = answer?.f13_answer?.selected_option_id ?? null;
  if (f13Selected === null && f13 !== "hold") {
    add("f13_inferred_from_ir", `f13_status=${f13}`);
  }

  // (9) guards: no Review Case event, no requirement promotion.
  const reviewCaseHeader = flat(headerValue(doc, "review_case_events_written"));
  if (reviewCaseHeader !== "0" || (answer?.guards?.review_case_events_written ?? 0) !== 0) {
    add("review_case_event_written", `header=${reviewCaseHeader}`);
  }
  const promotedHeader = headerValue(doc, "requirements_promoted");
  if (promotedHeader !== null && flat(promotedHeader) !== "0") {
    add("requirements_promoted", `header=${flat(promotedHeader)}`);
  }
  if (/requirements_promoted[:=]\s*(?:true|[1-9]\d*)/i.test(flatDoc)) {
    add("requirements_promoted", "a positive promotion claim is present");
  }

  // (10) the dictionary delta stays gated while the verdict is not granted.
  if (verdict !== "granted") {
    if (delta?.gate?.applied !== false) {
      add("delta_applied_without_grant", `applied=${JSON.stringify(delta?.gate?.applied)}`);
    }
    const deltaHeader = flat(headerValue(doc, "dictionary_delta"));
    if (/applied:true/i.test(deltaHeader)) add("delta_applied_without_grant", deltaHeader);
  }

  // (11) section 3 is byte-identical to its pin, and the delta pins that target.
  const pin = delta?.target_file_sha256_pin;
  const livePin = sha256Text(section3Text);
  if (typeof pin !== "string" || pin !== livePin) {
    add("section3_mutated", `pin=${pin} live=${livePin}`);
  }
  if (delta?.target_file !== TARGET_FILE) {
    add("section3_mutated", `target_file=${delta?.target_file}`);
  }
  if (delta?.target_section !== TARGET_SECTION) {
    add("section3_mutated", `target_section=${delta?.target_section}`);
  }
  const temporalRow = rows.find((row) => row.path === SECTION3_REL);
  if (!temporalRow) {
    add("section3_mutated", "no section 3 row in the Sources checked table");
  } else if (typeof pin === "string" && temporalRow.sha !== pin) {
    add("section3_mutated", "the Sources checked pin differs from the delta pin");
  }

  // (12) the delta materializes exactly the S01 variant terms.
  const expectedByVariant = new Map();
  for (const variant of irAlternatives?.variants || []) {
    expectedByVariant.set(variant.variant_id, variant.required_new_adr_terms || []);
  }
  const selected = delta?.selected_variant ?? null;
  const proposedRows = Array.isArray(delta?.proposed_rows) ? delta.proposed_rows : null;
  if (proposedRows === null) add("proposed_rows_mismatch", "proposed_rows is not a list");
  if (selected === null) {
    if (proposedRows && proposedRows.length !== 0) {
      add("proposed_rows_mismatch", "rows are proposed without a selected variant");
    }
  } else {
    const expected = expectedByVariant.get(selected);
    if (!expected) {
      add("proposed_rows_mismatch", `unknown selected variant ${selected}`);
    } else if (!sameSet((proposedRows || []).map((row) => row?.term), expected)) {
      add("proposed_rows_mismatch", `proposed terms for ${selected}`);
    }
  }
  for (const row of proposedRows || []) {
    if (row?.owning_adr !== null || row?.status !== "proposed-unapplied") {
      add("proposed_rows_mismatch", `an applied row shape is present for ${row?.term}`);
    }
  }
  const conditional = delta?.conditional_rows_by_variant || {};
  for (const [variantId, terms] of expectedByVariant.entries()) {
    const rowsFor = conditional[variantId];
    if (!Array.isArray(rowsFor)) {
      add("proposed_rows_mismatch", `conditional rows for ${variantId} are missing`);
      continue;
    }
    if (!sameSet(rowsFor.map((row) => row?.term), terms)) {
      add("proposed_rows_mismatch", `conditional terms for ${variantId}`);
      continue;
    }
    for (const row of rowsFor) {
      const shaped =
        row?.owning_adr === null &&
        row?.status === "proposed-unapplied" &&
        typeof row?.proposed_definition_scope === "string" &&
        row.proposed_definition_scope !== "" &&
        Array.isArray(row?.non_claims) &&
        row.non_claims.length > 0;
      if (!shaped) add("proposed_rows_mismatch", `row shape for ${row?.term}`);
    }
  }

  return { ok: errors.length === 0, verdict, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fail-closed code documentation
// ---------------------------------------------------------------------------

function documentedBlock() {
  const source = readRepo(CONTRACT_REL);
  const match = source.match(/DOCUMENTED_CODES_BEGIN\n([\s\S]*?)DOCUMENTED_CODES_END/);
  if (!match) return [];
  return [...match[1].matchAll(/^\/\/ ([a-z][a-z0-9_]*):/gm)].map((entry) => entry[1]);
}

function checkpointDocumentedCodes() {
  const boundary = section(liveCheckpointText, "## Fail-closed boundary");
  if (boundary === null) return [];
  return [...boundary.matchAll(/`([a-z][a-z0-9_]*)`/g)].map((match) => match[1]);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const VERDICT_LINE = "**admission: not-adopted**";
const GRANTED_LINE = "**admission: granted**";
const OWNER_REF_LINE = "**owner_admission_ref:** none";
const INTERACTION_REF_LINE = "**interaction_ref:** none";
const BASIS_PREFIX = "**admission_basis:** ";
const RECORDED_LINE = "**recorded:** 2026-09-24";
const F13_LINE = "**f13_status:** hold";
const RC_LINE = "**review_case_events_written:** 0";
const RP_LINE = "**requirements_promoted:** 0";
const REVISION_HEX = "618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7";
const ANSWER_ROW = `| \`${ANSWER_REL}\` |`;
const FIRST_SOURCE_SHA = "efc1b820506dabadde87d1ff8f338b95d6bd85417bce127ca17a07e5b3f9528b";
const STRIP_SOURCE_ROWS = /^\| `[^`]+` \| `[0-9a-f]{64}` \|.*$\n?/gm;

const INTERACTION_A = "interaction 00000000-0000-0000-0000-000000000000";
const INTERACTION_B = "interaction 11111111-1111-1111-1111-111111111111";

const cleanAnswer = {
  ...liveAnswer,
  status: "answered",
  answer_source: "subjective_uat_criterion",
  ir_answer: {
    ...liveAnswer.ir_answer,
    criterion_id: "criterion:m210-s02-ir",
    interaction_id: INTERACTION_B,
    selected_option_id: "C",
    option_resolution: "explicit_in_verbatim",
    verbatim_response: "Adopt option C.",
    tested_source_revision: liveRebind.source_revision,
  },
};

const cleanGoverning = { ...liveGoverning, verdict: "governing_surface_verified" };

function fixture(mutate) {
  const next = mutate(liveCheckpointText);
  assert.notEqual(next, liveCheckpointText, "fixture mutation did not modify the checkpoint");
  return next;
}

function granted(text) {
  assert.ok(text.includes(VERDICT_LINE), "granted fixture requires the live verdict line");
  const withVerdict = text.replace(VERDICT_LINE, GRANTED_LINE);
  return withVerdict
    .replace(OWNER_REF_LINE, `**owner_admission_ref:** ${INTERACTION_A}`)
    .replace(INTERACTION_REF_LINE, `**interaction_ref:** ${INTERACTION_B}`);
}

function grantedFixture(extra) {
  const next = granted(liveCheckpointText);
  return extra ? extra(next) : next;
}

function basisPrefix(text, sentence) {
  assert.ok(text.includes(BASIS_PREFIX), "basis fixture requires the live basis prefix");
  return text.replace(BASIS_PREFIX, `${BASIS_PREFIX}${sentence} `);
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

function replaceSourcePath(text, nextPath) {
  assert.ok(text.includes(ANSWER_ROW), "source fixture requires the live answer-record row");
  return text.replace(ANSWER_ROW, `| \`${nextPath}\` |`);
}

function cloneDelta(mutate) {
  const next = JSON.parse(JSON.stringify(liveDelta));
  mutate(next);
  return next;
}

function expectCode(text, expected, options) {
  const result = validateCheckpoint(text, options);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

// ---------------------------------------------------------------------------
// node:test wrapper that records failures so the marker stays honest
// ---------------------------------------------------------------------------

const failures = [];

function contract(name, fn) {
  test(name, () => {
    try {
      fn();
    } catch (error) {
      failures.push(name);
      throw error;
    }
  });
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

contract("M210 S02 admission checkpoint is valid, byte-bound and not-adopted", () => {
  const result = validateCheckpoint(liveCheckpointText);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  assert.equal(result.verdict, "not-adopted");
  assert.ok(
    sourceRows(liveCheckpointText).length >= MIN_SOURCES,
    `the checkpoint must cite at least ${MIN_SOURCES} byte-bound sources`,
  );
});

contract("the verdict is unambiguous and the derived header claims are consistent", () => {
  assert.equal(
    (liveCheckpointText.match(/^\*\*admission: /gm) || []).length,
    1,
    "exactly one verdict line",
  );
  assert.match(liveCheckpointText, VERDICT_RE);
  assert.equal(headerValue(liveCheckpointText, "owner_admission_ref"), "none");
  assert.equal(headerValue(liveCheckpointText, "interaction_ref"), "none");
  assert.equal(headerValue(liveCheckpointText, "f13_status"), "hold");
  assert.equal(headerValue(liveCheckpointText, "review_case_events_written"), "0");
  assert.equal(headerValue(liveCheckpointText, "requirements_promoted"), "0");
  assert.equal(headerValue(liveCheckpointText, "contract"), CONTRACT_REL);
  assert.match(flat(headerValue(liveCheckpointText, "runtime_stop")), /remains active/i);
  assert.match(
    flat(headerValue(liveCheckpointText, "dictionary_delta")),
    /applied:false/,
    "the checkpoint must record the delta as unapplied",
  );
  assert.equal(flat(headerValue(liveCheckpointText, "source_revision")), liveRebind.source_revision);
});

contract("the checkpoint cites exactly ten resolvable, hash-bound sources", () => {
  const rows = sourceRows(liveCheckpointText);
  assert.equal(rows.length, EXPECTED_SOURCES, "the checkpoint cites exactly ten sources");
  for (const row of rows) {
    assert.ok(!row.path.startsWith("/"), `${row.path} must be repository-relative`);
    assert.ok(!row.path.split("/").includes(".."), `${row.path} must not traverse`);
    for (const prefix of IGNORED_PREFIXES) {
      assert.ok(!row.path.startsWith(prefix), `${row.path} must not be an ignored path`);
    }
    assert.ok(repoExists(row.path), `${row.path} must exist`);
    assert.equal(sha256(row.path), row.sha, `${row.path} must match its recorded sha256`);
  }
});

contract("mandatory headers and sections are present and anchored", () => {
  const lines = liveCheckpointText.split("\n");
  for (const heading of REQUIRED_SECTIONS) {
    assert.ok(lines.includes(heading), `${heading} must be a level-## heading`);
  }
  for (const key of REQUIRED_HEADERS) {
    const value = headerValue(liveCheckpointText, key);
    assert.ok(value !== null && value.trim() !== "", `${key} must be a non-empty header field`);
  }
});

contract("a grant is refused without an answered interactive source and a verified surface", () => {
  // A grant under the live pending answer and absent surface is refused.
  expectCode(grantedFixture(), "owner_admission_ref_missing");
  // A not-adopted checkpoint carrying a fabricated reference is refused.
  expectCode(
    fixture((text) => text.replace(OWNER_REF_LINE, "**owner_admission_ref:** M210-3afp79")),
    "owner_admission_ref_missing",
  );
  // A grant with an answered interactive source and a verified surface is lawful.
  const clean = validateCheckpoint(grantedFixture(), {
    answer: cleanAnswer,
    governing: cleanGoverning,
  });
  assert.deepEqual(
    clean.errors,
    [],
    `a fully referenced grant must be accepted: ${JSON.stringify(clean.errors)}`,
  );
});

contract("a lock or an integrity result is never the basis of a grant", () => {
  const options = { answer: cleanAnswer, governing: cleanGoverning };
  expectCode(
    grantedFixture((text) =>
      basisPrefix(text, `D499 GSD_MILESTONE_LOCK authorises this adoption (${INTERACTION_A}).`),
    ),
    "lock_as_admission",
    options,
  );
  expectCode(
    grantedFixture((text) =>
      basisPrefix(
        text,
        `M206 runtime battery integrity PASS authorises this adoption (${INTERACTION_A}).`,
      ),
    ),
    "integrity_pass_as_admission",
    options,
  );
});

contract("the dictionary delta is gated and section 3 is byte-identical to its pin", () => {
  assert.equal(liveDelta.schema, SCHEMA);
  assert.equal(liveDelta.kind, KIND);
  assert.equal(liveDelta.milestone, MILESTONE);
  assert.equal(liveDelta.slice, SLICE);
  assert.equal(liveDelta.task, TASK);
  assert.deepEqual(liveDelta.lifecycle, ["proposed"]);
  assert.equal(liveDelta.authoritative, false);
  assert.equal(liveDelta.gate.applied, false);
  assert.equal(liveDelta.gate.applied_requires, "admission: granted");
  assert.equal(liveDelta.target_file, TARGET_FILE);
  assert.equal(liveDelta.target_section, TARGET_SECTION);
  assert.equal(liveDelta.target_file_sha256_pin, sha256Text(liveSection3Text));
  assert.equal(liveDelta.target_file_sha256_pin, sha256(SECTION3_REL));
  assert.equal(liveDelta.selected_variant, null);
  assert.deepEqual(liveDelta.proposed_rows, []);
  assert.ok(liveDelta.non_claims.length > 0, "the delta must carry non-claims");
  assert.deepEqual(liveDelta.fail_closed_codes.slice().sort(), DELTA_CODES.slice().sort());
});

contract("the delta materializes exactly the S01 variant terms", () => {
  const expected = new Map(
    liveIrAlternatives.variants.map((variant) => [
      variant.variant_id,
      variant.required_new_adr_terms || [],
    ]),
  );
  assert.deepEqual(
    [...Object.keys(liveDelta.conditional_rows_by_variant)].sort(),
    [...expected.keys()].sort(),
    "the conditional rows must cover every S01 variant",
  );
  for (const [variantId, terms] of expected.entries()) {
    const rows = liveDelta.conditional_rows_by_variant[variantId];
    assert.deepEqual(rows.map((row) => row.term).sort(), terms.slice().sort(), `${variantId} terms`);
    for (const row of rows) {
      assert.equal(row.owning_adr, null, `${row.term} must not name an owning ADR`);
      assert.equal(row.status, "proposed-unapplied", `${row.term} must stay unapplied`);
      assert.ok(row.non_claims.length > 0, `${row.term} must carry non-claims`);
    }
  }
});

contract("the documented fail-closed code set equals the emittable set", () => {
  const documented = documentedBlock();
  assert.equal(new Set(documented).size, documented.length, "the documented block has no duplicate");
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(
    checkpointDocumentedCodes().slice().sort(),
    EMITTABLE_CODES.slice().sort(),
    "the checkpoint Fail-closed boundary must document exactly this code set",
  );
  // Every named code must be reachable in the validator body, not only in a
  // registry.
  const withoutRegistries = readRepo(CONTRACT_REL)
    .replace(/const EMITTABLE_CODES = \[[\s\S]*?\];/, "")
    .replace(/const CODE_COVERAGE = \[[\s\S]*?\n\];/, "");
  for (const code of EMITTABLE_CODES) {
    assert.ok(
      withoutRegistries.includes(`"${code}"`),
      `${code} must be reachable in the validator body`,
    );
  }
  assert.equal(EMITTABLE_CODES.length, 22);
});

contract("the checkpoint never emits the slice battery marker", () => {
  const source = readRepo(CONTRACT_REL);
  const batteryMarker = ["M210_S02", "BATTERY_OK"].join("_");
  const emitter = new RegExp(`console\\.log\\(\\s*["'\`]${batteryMarker}`);
  assert.ok(!emitter.test(source), `${batteryMarker} must be unreachable by construction`);
});

contract("the contract is offline, spawns nothing and reads no ignored or absolute path", () => {
  const source = readRepo(CONTRACT_REL);
  const specifiers = [...source.matchAll(/from\s+"(node:[a-z/]+)"/g)].map((match) => match[1]);
  assert.deepEqual(
    specifiers.slice().sort(),
    ["node:assert/strict", "node:crypto", "node:fs", "node:test", "node:url", "node:path"].sort(),
  );
  assert.ok(!/\bchild_process\b/.test(source), "no child process import may exist");
  assert.ok(!/\bspawn\(|\bexecSync\(|\bexecFile\(/.test(source), "no process spawn may exist");
  assert.ok(!/\bfetch\(/.test(source), "the contract must stay offline");
  assert.ok(
    !/readFileSync\(\s*path\.join\(root,\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(
      source,
    ),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readFileSync\(\s*"\//.test(source), "the contract must not read an absolute path");
  assert.ok((source.match(/readFileSync\(/g) || []).length >= 2, "declared artifacts must be read");
  const declared = [
    CHECKPOINT_REL,
    DELTA_REL,
    CONTRACT_REL,
    ANSWER_REL,
    GOVERNING_REL,
    REBIND_REL,
    IR_ALTERNATIVES_REL,
    SECTION3_REL,
  ];
  for (const relativePath of declared) {
    assert.ok(repoExists(relativePath), `the contract reads ${relativePath}, which must exist`);
  }
  assert.ok(source.includes("DOCUMENTED_CODES_BEGIN"), "the documented code block must be present");
});

// ---------------------------------------------------------------------------
// empirical coverage: one mutation per documented fail-closed code
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "verdict_missing",
    mutate: (text) => text.replace(VERDICT_LINE, "**admission_state: pending**"),
  },
  {
    code: "verdict_ambiguous",
    mutate: (text) => text.replace(VERDICT_LINE, `${VERDICT_LINE}\n${GRANTED_LINE}`),
  },
  { code: "header_field_missing", mutate: (text) => text.replace(RECORDED_LINE, "**recorded:**") },
  { code: "section_missing", mutate: (text) => text.replace("## Non-claims", "## Nonclaims") },
  { code: "sources_insufficient", mutate: (text) => text.replace(STRIP_SOURCE_ROWS, "") },
  {
    code: "source_unresolved",
    mutate: (text) => replaceSourcePath(text, MISSING_SOURCE),
  },
  {
    code: "source_hash_mismatch",
    mutate: (text) => text.replace(FIRST_SOURCE_SHA, "0".repeat(64)),
  },
  {
    code: "source_revision_mismatch",
    mutate: (text) => text.replace(REVISION_HEX, "1".repeat(64)),
  },
  { code: "owner_admission_ref_missing", mutate: (text) => granted(text) },
  {
    code: "lock_as_admission",
    mutate: (text) =>
      basisPrefix(
        granted(text),
        `D499 GSD_MILESTONE_LOCK authorises this adoption (${INTERACTION_A}).`,
      ),
    options: { answer: cleanAnswer, governing: cleanGoverning },
  },
  {
    code: "integrity_pass_as_admission",
    mutate: (text) =>
      basisPrefix(
        granted(text),
        `M206 runtime battery integrity PASS authorises this adoption (${INTERACTION_A}).`,
      ),
    options: { answer: cleanAnswer, governing: cleanGoverning },
  },
  {
    code: "resume_condition_missing",
    mutate: (text) =>
      replaceSectionBody(text, "## Resume condition", "Adoption resumes when the owner decides."),
  },
  { code: "f13_status_missing", mutate: (text) => text.replace(F13_LINE, "**f13_status:**") },
  {
    code: "f13_inferred_from_ir",
    mutate: (text) => text.replace(F13_LINE, "**f13_status:** answered"),
  },
  { code: "review_case_event_written", mutate: (text) => text.replace(RC_LINE, "**review_case_events_written:** 1") },
  {
    code: "requirements_promoted",
    mutate: (text) => text.replace(RP_LINE, "**requirements_promoted:** 1"),
  },
  {
    code: "delta_applied_without_grant",
    options: { delta: cloneDelta((next) => { next.gate.applied = true; }) },
  },
  {
    code: "section3_mutated",
    options: { section3Text: `${liveSection3Text}\n` },
  },
  {
    code: "proposed_rows_mismatch",
    options: {
      delta: cloneDelta((next) => {
        next.proposed_rows = [
          {
            term: "NormRule",
            proposed_definition_scope: "x",
            owning_adr: null,
            status: "proposed-unapplied",
            non_claims: ["x"],
          },
        ];
      }),
    },
  },
  { code: "runtime_claim_present", mutate: (text) => `${text}\n\npub fn adopt() {}\n` },
  { code: "raw_text_leak", mutate: (text) => `${text}\n\n<p>raw</p>\n` },
  { code: "non_ascii_artifact", mutate: (text) => `${text}\n\n\u041d\u043e\u0440\u043c\u0430\n` },
];

contract("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const text = entry.mutate ? entry.mutate(liveCheckpointText) : liveCheckpointText;
    if (entry.mutate) {
      assert.notEqual(text, liveCheckpointText, `${entry.code}: the mutation must change the record`);
    }
    const result = validateCheckpoint(text, entry.options || {});
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} must be emitted, got ${JSON.stringify(codes(result))}`,
    );
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    EMITTABLE_CODES.slice().sort(),
    "the coverage registry must exercise every emittable code",
  );
  assert.deepEqual(
    CODE_COVERAGE.map((entry) => entry.code).slice().sort(),
    EMITTABLE_CODES.slice().sort(),
    "the coverage registry must carry exactly one entry per code",
  );
});

// ---------------------------------------------------------------------------
// negative: sources, structure and guard claims
// ---------------------------------------------------------------------------

contract("negative: byte-bound source references and revision", () => {
  expectCode(fixture((text) => replaceSourcePath(text, IGNORED_SOURCE)), "source_unresolved");
  expectCode(fixture((text) => replaceSourcePath(text, ABSOLUTE_SOURCE)), "source_unresolved");
  expectCode(fixture((text) => replaceSourcePath(text, UNTRACKED_SOURCE)), "source_unresolved");
  expectCode(
    fixture((text) =>
      replaceSourcePath(text, "prd/architecture/../../etc/passwd"),
    ),
    "source_unresolved",
  );
});

contract("negative: guard headers and F13 provenance", () => {
  expectCode(
    fixture((text) => text.replace(F13_LINE, "**f13_status:** derived from the IR answer")),
    "f13_inferred_from_ir",
  );
  expectCode(
    fixture((text) => `${text}\n\nrequirements_promoted: 2\n`),
    "requirements_promoted",
  );
  expectCode(
    fixture((text) =>
      replaceSectionBody(text, "## Resume condition", "Adoption resumes after a milestone closeout."),
    ),
    "resume_condition_missing",
  );
});

contract("negative: an applied delta while the verdict is not granted", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        "**dictionary_delta:** prd/architecture/m210-s02-dictionary-delta.json (applied:false)",
        "**dictionary_delta:** prd/architecture/m210-s02-dictionary-delta.json (applied:true)",
      ),
    ),
    "delta_applied_without_grant",
  );
  expectCode(
    liveCheckpointText,
    "section3_mutated",
    { delta: cloneDelta((next) => { next.target_file = "prd/other.md"; }) },
  );
});

// ---------------------------------------------------------------------------
// marker
// ---------------------------------------------------------------------------

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  process.stdout.write(
    `${CONTRACT_MARKER} checks=${EMITTABLE_CODES.length} sources=${sourceRows(liveCheckpointText).length} ` +
      `verdict=${validateCheckpoint(liveCheckpointText).verdict} delta_applied=${liveDelta.gate.applied}\n`,
  );
});
