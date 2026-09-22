// M209/S01 punkt registry-admission decision contract (T04).
//
// Offline and fail-closed: the live checkpoint must validate against the LIVE
// punkt-absence state (the admissions YAML, the 44-FZ registry projection, the
// frozen M202/S02-S04 evidence and the kb-ontology granularity catalog), and
// every named fail-closed code must be provable against a mutated copy of that
// checkpoint or of one declared source, so the suite cannot fool itself by
// asserting codes it would never emit.
//
// The checkpoint is a checkpoint, not a grant. While it records
// `**admission: not-adopted**` the only accepted verdict is `not-adopted`; a
// `granted` verdict is itself the fail-closed case `verdict_not_adopted`,
// because this record carries neither the required decision fields nor an owner
// interaction reference. `prd/architecture/m209-s01-punkt-decision.md` declares
// that a fresh tracked owner grant supersedes it and re-points this contract.
//
// The verdict grammar and the admission codes are the M208/S01 grammar
// (`scripts/m208_s01_admission_contract.test.mjs`): exactly one line matching
// `/^\*\*admission: (granted|not-adopted)\*\*$/m`, bold header fields and
// level-`##` sections.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (frozen-input proof). No cargo, no
// network, and no `.gsd` / ignored / absolute path is ever read as evidence.
//
// Run: node --test scripts/m209_s01_punkt_decision_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const DECISION_DOC = "prd/architecture/m209-s01-punkt-decision.md";
const CONTRACT_PATH = "scripts/m209_s01_punkt_decision_contract.test.mjs";
const M208_S01_CONTRACT = "scripts/m208_s01_admission_contract.test.mjs";

const ADMISSIONS = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const REGISTRY = "prd/architecture/kb-hierarchy-registry.yaml";
const M202_S02 = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_S03 = "prd/migration/rust-evidence/m202-s03-registry-regeneration.json";
const M202_S04 = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
const KB_ONTOLOGY = "prd/architecture/kb-ontology.yaml";

const MIN_SOURCES = 6;
const EXPECTED_SOURCES = 12;

// The frozen M202 inputs plus the two kb-hierarchy YAMLs. Any worktree delta
// here is frozen-input drift: the punkt checkpoint read these bytes.
const FROZEN_INPUTS = [M202_S02, M202_S03, M202_S04, ADMISSIONS, REGISTRY];

const EXPECTED_ADMISSION_ROWS = 166;
const EXPECTED_GLAVA_ROWS = 14;
const EXPECTED_STATYA_ROWS = 152;
const EXPECTED_ADMITTED_CC = [
  "cc:44-fz:glava-1",
  "cc:44-fz:statya-4",
  "cc:44-fz:statya-5",
];
const EXPECTED_CANDIDATE_PUNKT = 3;

// The six mandatory level-`##` sections of the checkpoint.
const REQUIRED_SECTIONS = [
  "## Sources checked",
  "## Required decision fields",
  "## Resume condition",
  "## Fail-closed boundary",
  "## Marker semantics",
  "## Non-claims",
];

// The anchors a future individual owner decision must carry. `declared_denominator`
// is checked by its own code (`denominator_missing`) so the two checks stay
// independently reachable.
const MANDATORY_DECISION_FIELDS = [
  "verdict_line",
  "granted_by",
  "scope",
  "cc_identity_form",
  "admission_rows",
  "sources_checked",
  "fail_closed_boundary",
  "supersede_rebind",
];
const MIN_DECISION_FIELDS = 8;

// punkt as YAML granularity / ladder token (validated, R087) must stay separate
// from punkt as registry admission identity (blocked). These are the live
// `document_groups` facts the contract parses from kb-ontology.yaml.
const PUNKT_PROFILES = {
  "federal_law@v1": { granularity: "statya", role: "subunit", maxDepth: "2" },
  government_resolution: { granularity: "punkt", role: "unit", maxDepth: "3" },
  departmental_order: { granularity: "punkt", role: "unit", maxDepth: "4" },
};

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const UNTRACKED_SOURCE = "prd/architecture/m209-s01-punkt-untracked.yaml";
const MISSING_SOURCE = "prd/architecture/m209-s01-punkt-missing.md";
// Built by join so this contract never carries an ignored or absolute path as a
// declared string literal: the offline self-check below refuses those.
const IGNORED_SOURCE = [
  ".agents",
  "skills",
  "law-nexus-rust",
  "references",
  "verification-matrix.md",
].join("/");
const ABSOLUTE_SOURCE = ["", "tmp", "m209-s01-punkt-source.md"].join("/");

// The complete fail-closed code set. The checkpoint's `## Fail-closed boundary`
// section is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "verdict_missing",
  "verdict_ambiguous",
  "verdict_not_adopted",
  "self_minted_adoption",
  "owner_admission_ref_missing",
  "integrity_pass_as_admission",
  "lock_as_admission",
  "sources_insufficient",
  "source_unresolved",
  "source_not_tracked",
  "source_hash_mismatch",
  "ignored_path_as_source",
  "absolute_path_as_source",
  "section_missing",
  "required_decision_fields_missing",
  "resume_condition_missing",
  "punkt_row_admitted_without_decision",
  "punkt_admission_gate_claimed",
  "punkt_rows_mismatch",
  "admitted_cc_mismatch",
  "denominator_missing",
  "s02_preauthorized",
  "s02_punkt_admission_authorized",
  "contract_pass_as_admission",
  "cross_slice_authorization_granted",
  "metric_baseline_relabelled_as_admission",
  "m202_s03_modified",
  "admissions_yaml_modified",
  "granularity_confused_with_registry_admission",
  "r087_invalidated",
];

// Anti-claim sentinels: the checkpoint's own non-claims. Dropping a disclaimer
// is the fail-closed case for the code it protects.
const S02_DISCLAIMER_SENTINELS = [
  ["S02 is not pre-authorized to admit punkt", "s02_preauthorized"],
  ["S02 is not pre-authorized to admit punkt", "s02_punkt_admission_authorized"],
  ["no cross-slice authorization is granted by this record", "cross_slice_authorization_granted"],
];

// Positive claim forms: asserting any of these is the fail-closed case.
const POSITIVE_CLAIM_PATTERNS = [
  [/s02_preauthorized:\s*(?:true|yes)\b/i, "s02_preauthorized"],
  [/s02_punkt_admission_authorized:\s*(?:true|yes)\b/i, "s02_punkt_admission_authorized"],
  [/cross_slice_authorization_granted:\s*(?:true|yes)\b/i, "cross_slice_authorization_granted"],
  [/S02 is pre-authorized to admit punkt/i, "s02_preauthorized"],
  [/S02 may admit punkt/i, "s02_punkt_admission_authorized"],
  [/this (?:record|checkpoint) authorizes S02 to admit punkt/i, "s02_punkt_admission_authorized"],
  [
    /punkt_admission_gate:\s*(?:implemented|present|exists|true|granted|adopted)\b/i,
    "punkt_admission_gate_claimed",
  ],
];

const VERDICT_RE = /^\*\*admission: (granted|not-adopted)\*\*$/m;
const VERDICT_ANY_RE = /^\*\*admission: .*\*\*$/gm;
const M208_VERDICT_LITERAL = String.raw`/^\*\*admission: (granted|not-adopted)\*\*$/m`;

const INTERACTION_RE =
  /interaction\s+[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const LOCK_RE = /d499|\bgsd[_ ]?milestone[_ ]?lock\b/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b/i;
const CONTRACT_PASS_RE = /contract[_ ]?pass\b|contract[^.\n]{0,40}pass\b|\bgreen state\b/i;
const PIN_RE = /\bpins?\b|\bdesign\b|\bmatrix\b|\bYAML\b/i;
const INVENTORY_COUNTER_RE =
  /\b(?:registry_rows|legacy_human|candidates_extracted|candidates_unique|candidates_duplicate|admitted_candidate_backed|fz44_glava|fz44_statya|rows_total|rows_legacy_human|binding_rows_total|binding_rows_legacy|suites_cited)\b/;
const R087_INVALIDATED_RE = /(?:invalidat|supersed|reject|withdraw|fail)\w*[^.\n]{0,40}\(R087\)/i;
const CONFLATION_RE =
  /punkt[^.\n]{0,80}granularity[^.\n]{0,60}\b(?:is|equals|implies|means|counts as)\b[^.\n]{0,60}admission/i;

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
}

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

const trackedCache = new Map();

function isTracked(relativePath) {
  if (trackedCache.has(relativePath)) return trackedCache.get(relativePath);
  let tracked = true;
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: root,
      stdio: ["ignore", "ignore", "ignore"],
    });
  } catch {
    tracked = false;
  }
  trackedCache.set(relativePath, tracked);
  return tracked;
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

// `git status --porcelain` restricted to the frozen scope: an empty result means
// none of those tracked artifacts carries a worktree delta.
function worktreeDelta(paths) {
  try {
    return execFileSync("git", ["status", "--porcelain", "--", ...paths], {
      cwd: root,
      encoding: "utf8",
    }).trim();
  } catch {
    return "git status failed";
  }
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

// Prose checks must survive the checkpoint's hard line wrapping: collapse every
// whitespace run before matching a sentence-shaped sentinel.
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

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// YAML flow mappings: `- {path_needle: ..., level: ..., ...}`. Used for both the
// admissions list (indented) and the registry bindings (column zero). The
// registry also carries indented editions/works rows without a `level`, so the
// two shapes are parsed separately.
function flowRows(text) {
  return [...text.matchAll(/^\s*- \{([^}]*)\}\s*$/gm)].map((match) => match[1]);
}

function bindingRows(text) {
  return [...text.matchAll(/^- \{([^}]*)\}\s*$/gm)].map((match) => match[1]);
}

function admissionLevels(text) {
  const rows = flowRows(text);
  const counts = {};
  for (const row of rows) {
    const level = (row.match(/\blevel: ([A-Za-z]+)/) || [])[1] || "unknown";
    counts[level] = (counts[level] || 0) + 1;
  }
  return { rows: rows.length, counts };
}

// Comment markers are stripped and run-together comment lines are joined with a
// single space before matching quoted YAML header claims: the raw admissions
// header breaks the punkt non-claim across two `#` lines.
function normalizeComments(text) {
  const collected = [];
  let buffer = [];
  for (const line of text.split("\n")) {
    const match = line.match(/^\s*#\s?(.*)$/);
    if (match) {
      buffer.push(match[1].trim());
      continue;
    }
    if (buffer.length > 0) {
      collected.push(buffer.join(" "));
      buffer = [];
    }
    collected.push(line);
  }
  if (buffer.length > 0) collected.push(buffer.join(" "));
  return collected.join("\n").replace(/\s+/g, " ");
}

// The `document_groups` block of kb-ontology.yaml, parsed as text: for each group
// id, its granularity and its punkt ladder token (role / recursive / max_depth).
function ontologyGroups(text) {
  const groups = new Map();
  const start = text.indexOf("\ndocument_groups:");
  if (start === -1) return groups;
  const end = text.indexOf("\nassembly_fsm:", start);
  const body = text.slice(start, end === -1 ? text.length : end);
  const marks = [...body.matchAll(/^    - id: (\S+)$/gm)].map((match) => ({
    id: match[1],
    index: match.index,
  }));
  for (let i = 0; i < marks.length; i += 1) {
    const block = body.slice(
      marks[i].index,
      i + 1 < marks.length ? marks[i + 1].index : body.length,
    );
    const granularity = (block.match(/^\s+granularity: (\S+)\s*$/m) || [])[1] || null;
    const punktLine = (block.match(/^\s+- \{token: punkt,([^\n}]*)\}\s*$/m) || [])[1] || null;
    const role = punktLine ? (punktLine.match(/\brole: ([a-z-]+)/) || [])[1] || null : null;
    const maxDepth = punktLine ? (punktLine.match(/\bmax_depth: (\d+)/) || [])[1] || null : null;
    groups.set(marks[i].id, { granularity, role, maxDepth });
  }
  return groups;
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validatePunkt(doc, options = {}) {
  const {
    admissionsText = liveAdmissions,
    registryText = liveRegistry,
    m202S02Text = liveM202S02,
    m202S03Text = liveM202S03,
    m202S04Text = liveM202S04,
    ontologyText = liveOntology,
    frozenDelta = liveFrozenDelta,
    fileExists = repoExists,
  } = options;

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });
  const flatDoc = flat(doc);

  // (1) verdict: at most one line, and only one of the two known values. While
  // this checkpoint is not a grant, `granted` is itself fail-closed.
  const verdictLines = doc.match(VERDICT_ANY_RE) || [];
  const verdictMatch = doc.match(VERDICT_RE);
  const verdict = verdictMatch ? verdictMatch[1] : null;
  if (verdictLines.length === 0 || verdict === null) {
    add("verdict_missing", verdictLines.join(" | "));
  }
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));
  if (verdict !== null && verdict !== "not-adopted") add("verdict_not_adopted", verdict);

  // (3) byte-bound sources: repository-relative, resolvable, tracked, hash-equal.
  const rows = sourceRows(doc);
  if (rows.length < MIN_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    if (IGNORED_SOURCE_PREFIXES.some((prefix) => row.path.startsWith(prefix))) {
      add("ignored_path_as_source", row.path);
      continue;
    }
    if (row.path.startsWith("/")) {
      add("absolute_path_as_source", row.path);
      continue;
    }
    if (row.path.split("/").includes("..")) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (!fileExists(row.path)) {
      add("source_unresolved", row.path);
      continue;
    }
    if (!isTracked(row.path)) {
      add("source_not_tracked", row.path);
      continue;
    }
    if (sha256(row.path) !== row.sha) add("source_hash_mismatch", row.path);
  }

  // (4) the six mandatory sections.
  for (const heading of REQUIRED_SECTIONS) {
    if (!doc.includes(heading)) add("section_missing", heading);
  }

  // (5) required decision fields. The checkpoint itself warns that these must be
  // parsed as anchored bold field lines, never as bare substrings: the code
  // names below contain the field names, so a substring test could not fail.
  const decisionFields = section(doc, "## Required decision fields") || "";
  const fieldNames = [...decisionFields.matchAll(/^\d+\.\s+`([a-z_]+)`/gm)].map(
    (match) => match[1],
  );
  const missingFields = MANDATORY_DECISION_FIELDS.filter((name) => !fieldNames.includes(name));
  if (fieldNames.length < MIN_DECISION_FIELDS || missingFields.length > 0) {
    add(
      "required_decision_fields_missing",
      `n=${fieldNames.length} missing=${missingFields.join(",")}`,
    );
  }
  if (!/interaction/i.test(flat(decisionFields))) {
    add("required_decision_fields_missing", "granted_by lacks an owner interaction reference");
  }
  if (!fieldNames.includes("declared_denominator")) {
    add("denominator_missing", "the declared_denominator field is not enumerated");
  }

  // The declared denominator is a named measure (act plus candidate count); an
  // inventory baseline is a different thing and cannot be relabelled into it.
  if (
    /^inventory[_ ]count$/i.test(flat(headerValue(doc, "declared_denominator"))) ||
    INVENTORY_COUNTER_RE.test(flat(headerValue(doc, "declared_denominator")))
  ) {
    add("denominator_missing", "the declared denominator is an inventory baseline");
  }

  // (16) resume condition: the point at which a grant supersedes this checkpoint.
  const resumeSection = section(doc, "## Resume condition");
  if (resumeSection === null) {
    add("resume_condition_missing", "section absent");
  } else {
    const resume = flat(resumeSection);
    if (!/source-bound owner grant/i.test(resume)) {
      add("resume_condition_missing", "no source-bound owner grant is named");
    }
    if (!/denominator/i.test(resume)) {
      add("resume_condition_missing", "no declared denominator is named");
    }
    if (!/interaction|subjective-UAT|criterion id/i.test(resume)) {
      add("resume_condition_missing", "no grantor reference requirement is named");
    }
  }

  // (2) derived assertions: a checkpoint that stays `not-adopted` may not carry
  // an admission reference, an opened admission gate or a lifted runtime stop.
  const runtimeStop = flat(headerValue(doc, "runtime_stop"));
  const ownerRef = headerValue(doc, "owner_admission_ref");
  const ownerRefFlat = flat(ownerRef);
  const basisFlat = flat(headerValue(doc, "admission_basis"));
  const grantRef = `${basisFlat} ${ownerRefFlat}`;
  const hasOwnerInteraction = INTERACTION_RE.test(grantRef);

  if (verdict === "granted") {
    // A grant that is not owner-bound, or that derives itself from pins, an
    // integrity PASS, a contract PASS, a GSD lock or an inventory baseline, is a
    // self-minted adoption.
    if (!hasOwnerInteraction) add("owner_admission_ref_missing", ownerRefFlat || "(absent)");
    if (LOCK_RE.test(grantRef)) add("lock_as_admission", basisFlat);
    if (INTEGRITY_RE.test(basisFlat)) add("integrity_pass_as_admission", basisFlat);
    if (CONTRACT_PASS_RE.test(basisFlat)) add("contract_pass_as_admission", basisFlat);
    if (INVENTORY_COUNTER_RE.test(basisFlat)) {
      add("metric_baseline_relabelled_as_admission", basisFlat);
    }
    const yamlOnly = rows.length > 0 && rows.every((row) => /\.ya?ml$/i.test(row.path));
    if (yamlOnly || PIN_RE.test(grantRef)) add("self_minted_adoption", grantRef);
  } else {
    if (ownerRef !== "none") {
      add("self_minted_adoption", `owner_admission_ref=${ownerRefFlat || "(absent)"}`);
    }
    if (flat(headerValue(doc, "punkt_admission")) !== "not-adopted") {
      add("punkt_admission_gate_claimed", flat(headerValue(doc, "punkt_admission")));
    }
    if (!/remains active for punkt/i.test(runtimeStop) || /\blifted\b/i.test(runtimeStop)) {
      add("punkt_admission_gate_claimed", runtimeStop);
    }
  }

  // (6) the punkt-absence proof: zero punkt rows across every independent source.
  const admissions = admissionLevels(admissionsText);
  const registryRows = bindingRows(registryText);
  const registryPunktRows = registryRows.filter((row) => /\blevel: punkt\b/.test(row)).length;
  const registryPunktCc = registryRows.filter((row) => /\bcc:[^,]*punkt/i.test(row)).length;
  const m202S02 = safeJson(m202S02Text);
  const m202S03 = safeJson(m202S03Text);
  const m202S04 = safeJson(m202S04Text);
  const m202S03Punkt = m202S03 && m202S03.output ? m202S03.output.punkt_rows_admitted : null;
  const m202S04Punkt =
    m202S04 && m202S04.mapping_counts ? m202S04.mapping_counts.punkt_admitted : null;
  const declaredRaw = headerValue(doc, "punkt_rows_admitted");
  const declared =
    declaredRaw !== null && /^\d+$/.test(declaredRaw.trim()) ? Number(declaredRaw.trim()) : null;

  const reported = {
    admissions_punkt_rows: admissions.counts.punkt || 0,
    registry_punkt_rows: registryPunktRows,
    registry_punkt_cc: registryPunktCc,
    m202_s03: m202S03Punkt,
    m202_s04: m202S04Punkt,
  };
  if (verdict !== "granted") {
    for (const [source, count] of Object.entries(reported)) {
      if (typeof count === "number" && count > 0) {
        add("punkt_row_admitted_without_decision", `${source}=${count}`);
      }
    }
  }
  if (declared === null || declared !== 0) {
    add("punkt_rows_mismatch", `declared=${declaredRaw}`);
  }
  for (const [source, count] of Object.entries(reported)) {
    if (count !== declared) add("punkt_rows_mismatch", `${source}=${count} declared=${declared}`);
  }
  if (
    admissions.rows !== EXPECTED_ADMISSION_ROWS ||
    (admissions.counts.glava || 0) !== EXPECTED_GLAVA_ROWS ||
    (admissions.counts.statya || 0) !== EXPECTED_STATYA_ROWS
  ) {
    add(
      "punkt_rows_mismatch",
      `admission rows=${admissions.rows} glava=${admissions.counts.glava || 0} statya=${admissions.counts.statya || 0}`,
    );
  }
  if (registryRows.length !== EXPECTED_ADMISSION_ROWS) {
    add("punkt_rows_mismatch", `registry rows=${registryRows.length}`);
  }
  if (!/^schema: law-nexus-kb-hierarchy-admission\/v1$/m.test(admissionsText)) {
    add("punkt_rows_mismatch", "admissions schema");
  }
  if (!/^lifecycle: "\[proposed\]"$/m.test(admissionsText)) {
    add("punkt_rows_mismatch", "admissions lifecycle");
  }
  if (!/^authoritative: false$/m.test(admissionsText)) {
    add("punkt_rows_mismatch", "admissions authority");
  }
  if (
    !normalizeComments(admissionsText).includes(
      "Punkt candidates stay unadmitted; no ComponentConcept is minted here",
    )
  ) {
    add("punkt_rows_mismatch", "admissions punkt non-claim");
  }
  const admittedCc = m202S04 && Array.isArray(m202S04.admitted_cc) ? m202S04.admitted_cc : null;
  if (!sameSet(admittedCc, EXPECTED_ADMITTED_CC)) {
    add("admitted_cc_mismatch", JSON.stringify(admittedCc));
  }
  for (const id of EXPECTED_ADMITTED_CC) {
    if (!doc.includes(id)) add("admitted_cc_mismatch", `document omits ${id}`);
  }
  const candidatePunkt =
    m202S02 && m202S02.counts && m202S02.counts.by_level ? m202S02.counts.by_level.punkt : null;
  if (candidatePunkt !== EXPECTED_CANDIDATE_PUNKT) {
    add("punkt_rows_mismatch", `m202-s02 candidate punkt=${candidatePunkt}`);
  }
  if (
    !flat(m202S02Text).includes("never admitted to the registry")
  ) {
    add("self_minted_adoption", "candidate artifact no longer disclaims admission");
  }

  // (7) frozen-input drift.
  if (frozenDelta.includes(M202_S03)) add("m202_s03_modified", M202_S03);
  if (frozenDelta.includes(ADMISSIONS)) add("admissions_yaml_modified", ADMISSIONS);

  // (8) granularity is not admission identity: the ontology keeps punkt as a
  // declared granularity/ladder token, and the checkpoint must not conflate it.
  const groups = ontologyGroups(ontologyText);
  for (const [id, expected] of Object.entries(PUNKT_PROFILES)) {
    const actual = groups.get(id);
    if (
      actual === undefined ||
      actual.granularity !== expected.granularity ||
      actual.role !== expected.role ||
      actual.maxDepth !== expected.maxDepth
    ) {
      add("granularity_confused_with_registry_admission", `${id}=${JSON.stringify(actual)}`);
    }
  }
  if (CONFLATION_RE.test(flatDoc)) {
    add(
      "granularity_confused_with_registry_admission",
      "the checkpoint conflates punkt granularity with registry admission",
    );
  }

  // R087 (punkt granularity / fixture-scale ComponentConcept minting) stays
  // validated while punkt registry admission stays blocked.
  if (!flatDoc.includes("remain validated (R087)")) {
    add("r087_invalidated", "the R087 non-claim is absent");
  }
  if (R087_INVALIDATED_RE.test(flatDoc)) {
    add("r087_invalidated", "an R087 invalidation claim is present");
  }

  // (2) admit-claims: the S02 disclaimers must stand and no claim form may be
  // asserted.
  for (const [token, code] of S02_DISCLAIMER_SENTINELS) {
    if (!flatDoc.includes(token)) add(code, token);
  }
  for (const [pattern, code] of POSITIVE_CLAIM_PATTERNS) {
    if (pattern.test(flatDoc)) add(code, String(pattern));
  }

  return { ok: errors.length === 0, verdict, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const liveDoc = readRepo(DECISION_DOC);
const liveAdmissions = readRepo(ADMISSIONS);
const liveRegistry = readRepo(REGISTRY);
const liveM202S02 = readRepo(M202_S02);
const liveM202S03 = readRepo(M202_S03);
const liveM202S04 = readRepo(M202_S04);
const liveOntology = readRepo(KB_ONTOLOGY);
const liveFrozenDelta = worktreeDelta(FROZEN_INPUTS);

const doc = liveDoc;

// The checkpoint's own line wrapping means a sentinel must be broken on the raw
// text: "no cross-slice authorization is" and "granted by this record" sit on
// different source lines, so only the raw fragment is replaceable.
const CROSS_SLICE_FRAGMENT = "no cross-slice authorization is";
const VERDICT_LINE = "**admission: not-adopted**";
const GRANTED_LINE = "**admission: granted**";
const OWNER_REF_LINE = "**owner_admission_ref:** none";
const BASIS_PREFIX = "**admission_basis:** ";

function fixture(mutate) {
  const next = mutate(doc);
  assert.notEqual(next, doc, "fixture mutation did not modify the document");
  return next;
}

function granted(text) {
  assert.ok(text.includes(VERDICT_LINE), "granted fixture requires the live verdict line");
  return text.replace(VERDICT_LINE, GRANTED_LINE);
}

function grantedFixture(extra) {
  const next = granted(doc);
  return extra ? extra(next) : next;
}

function basisPrefix(text, sentence) {
  assert.ok(text.includes(BASIS_PREFIX), "basis fixture requires the live basis prefix");
  return text.replace(BASIS_PREFIX, `${BASIS_PREFIX}${sentence} `);
}

function dropDecisionField(text, name) {
  const pattern = new RegExp(`^\\d+\\. \`${name}\`[\\s\\S]*?(?=^\\d+\\. |^## )`, "m");
  const next = text.replace(pattern, "");
  assert.notEqual(next, text, `dropDecisionField(${name}) must change the document`);
  return next;
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

function expectCode(text, expected, options) {
  const result = validatePunkt(text, options);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

const STRIP_SOURCE_ROWS = /^\| `[^`]+` \| `[0-9a-f]{64}` \|.*$\n?/gm;
const ADMISSIONS_ROW = `| \`${ADMISSIONS}\` |`;

function replaceSourcePath(text, nextPath) {
  assert.ok(text.includes(ADMISSIONS_ROW), "source fixture requires the live admissions row");
  return text.replace(ADMISSIONS_ROW, `| \`${nextPath}\` |`);
}

const PUNKT_ADMISSION_ROW =
  '  - {path_needle: n-435-fz, level: punkt, number: "1", cc: cc:435fz:statya-1/punkt-1, provenance: legacy-human}';

function withPunktRow(text) {
  const anchor = '  - {path_needle: n-435-fz, level: statya, number: "1"';
  assert.ok(text.includes(anchor), "punkt-row fixture requires the first admissions row");
  return text.replace(anchor, `${PUNKT_ADMISSION_ROW}\n${anchor}`);
}

function withExtraAdmittedCc(text) {
  const anchor = '"cc:44-fz:statya-5"\n  ],';
  assert.ok(text.includes(anchor), "admitted_cc fixture requires the live array tail");
  return text.replace(anchor, '"cc:44-fz:statya-5",\n    "cc:44-fz:punkt-1"\n  ],');
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M209 S01 punkt decision checkpoint is valid, byte-bound and not-adopted", () => {
  assert.ok(isTracked(DECISION_DOC), "the checkpoint must be a tracked artifact");
  const result = validatePunkt(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  assert.equal(result.verdict, "not-adopted");
  assert.ok(
    sourceRows(doc).length >= MIN_SOURCES,
    `checkpoint must cite at least ${MIN_SOURCES} byte-bound sources`,
  );
});

test("the punkt verdict is unambiguous and its derived claims are consistent", () => {
  const flatDoc = flat(doc);
  assert.equal((doc.match(/^\*\*admission: /gm) || []).length, 1, "exactly one verdict line");
  assert.match(doc, VERDICT_RE);
  assert.equal(headerValue(doc, "owner_admission_ref"), "none");
  assert.equal(headerValue(doc, "punkt_admission"), "not-adopted");
  assert.equal(headerValue(doc, "punkt_rows_admitted"), "0");
  assert.match(flat(headerValue(doc, "runtime_stop")), /remains active for punkt/i);
  assert.equal(headerValue(doc, "contract"), CONTRACT_PATH);
  for (const [pattern] of POSITIVE_CLAIM_PATTERNS) {
    assert.ok(!pattern.test(flatDoc), `the checkpoint must not assert ${pattern}`);
  }
});

test("the verdict grammar is the M208 admission grammar", () => {
  const m208 = readRepo(M208_S01_CONTRACT);
  assert.ok(
    m208.includes(M208_VERDICT_LITERAL),
    "M208/S01 must carry the shared admission verdict grammar",
  );
  assert.equal(VERDICT_RE.source, "^\\*\\*admission: (granted|not-adopted)\\*\\*$");
});

test("the checkpoint cites exactly twelve resolvable, tracked, hash-bound sources", () => {
  const rows = sourceRows(doc);
  assert.equal(rows.length, EXPECTED_SOURCES, "the checkpoint cites exactly twelve sources");
  for (const row of rows) {
    assert.ok(!row.path.startsWith("/"), `${row.path} must be repository-relative`);
    assert.ok(!row.path.split("/").includes(".."), `${row.path} must not traverse`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!row.path.startsWith(prefix), `${row.path} must not be an ignored path`);
    }
    assert.ok(repoExists(row.path), `${row.path} must exist`);
    assert.ok(isTracked(row.path), `${row.path} must be tracked`);
    assert.equal(sha256(row.path), row.sha, `${row.path} must match its recorded sha256`);
  }
});

test("required sections and required decision fields stay anchored", () => {
  const flatDoc = flat(doc);
  for (const heading of REQUIRED_SECTIONS) {
    assert.ok(doc.split("\n").includes(heading), `${heading} must be a level-## heading`);
  }
  const decisionFields = section(doc, "## Required decision fields");
  const fieldNames = [...decisionFields.matchAll(/^\d+\.\s+`([a-z_]+)`/gm)].map(
    (match) => match[1],
  );
  assert.ok(
    fieldNames.length >= MIN_DECISION_FIELDS,
    `at least ${MIN_DECISION_FIELDS} decision fields are required, got ${fieldNames.length}`,
  );
  for (const name of MANDATORY_DECISION_FIELDS) {
    assert.ok(fieldNames.includes(name), `${name} must be a required decision field`);
  }
  assert.ok(fieldNames.includes("declared_denominator"), "the denominator must be enumerated");
  assert.match(flat(decisionFields), /granted_by`[\s\S]*interaction/i, "granted_by is owner-bound");
  assert.ok(
    flatDoc.includes("required-field assertions must parse the anchored bold field lines"),
    "the checkpoint must warn that field assertions are anchored, never substring",
  );
});

test("the checkpoint proves zero admitted punkt rows in three independent sources", () => {
  const admissions = admissionLevels(liveAdmissions);
  assert.equal(admissions.rows, EXPECTED_ADMISSION_ROWS, "166 admissions rows");
  assert.equal(admissions.counts.glava || 0, EXPECTED_GLAVA_ROWS, "14 glava rows");
  assert.equal(admissions.counts.statya || 0, EXPECTED_STATYA_ROWS, "152 statya rows");
  assert.equal(admissions.counts.punkt || 0, 0, "zero level: punkt rows");
  assert.match(liveAdmissions, /^schema: law-nexus-kb-hierarchy-admission\/v1$/m);
  assert.match(liveAdmissions, /^lifecycle: "\[proposed\]"$/m);
  assert.match(liveAdmissions, /^authoritative: false$/m);
  assert.ok(
    normalizeComments(liveAdmissions).includes(
      "Punkt candidates stay unadmitted; no ComponentConcept is minted here",
    ),
    "the admissions header must keep the punkt non-claim",
  );

  const registryRows = bindingRows(liveRegistry);
  assert.equal(registryRows.length, EXPECTED_ADMISSION_ROWS, "the registry binds 166 rows");
  assert.equal(registryRows.filter((row) => /\blevel: punkt\b/.test(row)).length, 0);
  assert.equal(registryRows.filter((row) => /\bcc:[^,]*punkt/i.test(row)).length, 0);
  assert.equal((liveRegistry.match(/[Pp]unkt/g) || []).length, 1, "punkt stays a comment-only token");

  const m202S03 = safeJson(liveM202S03);
  const m202S04 = safeJson(liveM202S04);
  const m202S02 = safeJson(liveM202S02);
  assert.equal(m202S03.output.punkt_rows_admitted, 0, "m202-s03 admits zero punkt rows");
  assert.equal(m202S04.mapping_counts.punkt_admitted, 0, "m202-s04 admits zero punkt rows");
  assert.ok(sameSet(m202S04.admitted_cc, EXPECTED_ADMITTED_CC), "admitted_cc is the three CC ids");
  assert.equal(m202S02.counts.by_level.punkt, EXPECTED_CANDIDATE_PUNKT, "three punkt candidates");
  assert.ok(
    m202S02.non_claims.some((claim) => claim.includes("never admitted to the registry")),
    "the candidate artifact must keep its admission non-claim",
  );
});

test("the frozen M202 inputs and the two registries carry no worktree delta", () => {
  for (const artifact of FROZEN_INPUTS) {
    assert.ok(isTracked(artifact), `${artifact} must stay tracked`);
  }
  assert.equal(worktreeDelta(FROZEN_INPUTS), "", "the frozen inputs must carry no worktree delta");
});

test("kb-ontology keeps punkt as granularity while registry admission stays blocked", () => {
  const groups = ontologyGroups(liveOntology);
  for (const [id, expected] of Object.entries(PUNKT_PROFILES)) {
    const actual = groups.get(id);
    assert.ok(actual, `${id} must exist in the live document_groups catalog`);
    assert.equal(actual.granularity, expected.granularity, `${id} granularity`);
    assert.equal(actual.role, expected.role, `${id} punkt ladder role`);
    assert.equal(actual.maxDepth, expected.maxDepth, `${id} punkt ladder max_depth`);
  }
  assert.ok(liveOntology.includes("    - punkt\n"), "punkt stays a declared hierarchy level");
  assert.ok(liveOntology.includes("Punkt: punkt"), "punkt stays a decode level alias");
  const flatDoc = flat(doc);
  assert.ok(flatDoc.includes("Out of scope: punkt as YAML granularity and ladder token"));
  assert.ok(flatDoc.includes("punkt as a registry admission identity only"));
  assert.ok(flatDoc.includes("remain validated (R087)"));
});

test("the documented fail-closed code set equals the emittable set", () => {
  const boundary = section(doc, "## Fail-closed boundary");
  assert.ok(boundary, "the checkpoint must carry a Fail-closed boundary section");
  const documented = new Set([...boundary.matchAll(/`([a-z][a-z0-9_]*)`/g)].map((m) => m[1]));
  assert.deepEqual(
    [...documented].sort(),
    [...EMITTABLE_CODES].sort(),
    "the documented code set must equal the set this contract can emit",
  );
  // Every named code must be reachable in the validator body: strip both the
  // code registry and the coverage registry, then require the code literal.
  const withoutRegistries = readRepo(CONTRACT_PATH)
    .replace(/const EMITTABLE_CODES = \[[\s\S]*?\];/, "")
    .replace(/const CODE_COVERAGE = \[[\s\S]*?\n\];/, "");
  for (const code of EMITTABLE_CODES) {
    assert.ok(
      withoutRegistries.includes(`"${code}"`),
      `${code} must be reachable in the validator body, not only in a registry`,
    );
  }
});

test("the contract stays offline, subprocess-limited and never reads .gsd paths", () => {
  const source = readRepo(CONTRACT_PATH);
  assert.ok(source.includes('"ls-files", "--error-unmatch"'), "tracked-file proof is required");
  assert.ok(source.includes('"status", "--porcelain"'), "frozen-input proof is required");
  for (const executable of ["car" + "go", "cu" + "rl", "wg" + "et", "n" + "pm", "n" + "px", "kubectl"]) {
    const launch = new RegExp(
      "(?:execFileSync|spawnSync|execSync|spawn)\\(\\s*[\"'`]" + executable + "\\b",
    );
    assert.ok(!launch.test(source), `${executable} must not be launched by this contract`);
  }
  const declared = [...source.matchAll(/^(?:const|let)\s+[A-Za-z_$][\w$]*\s*=\s*"([^"]+)";$/gm)].map(
    (match) => match[1],
  );
  for (const value of declared) {
    assert.ok(!value.startsWith("/"), `absolute path literal ${value} is not admissible evidence`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(
        !value.startsWith(prefix),
        `ignored path literal ${value} is not admissible evidence`,
      );
    }
  }
  assert.ok(
    !/readRepo\(\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readRepo\(\s*"\//.test(source), "the contract must not read an absolute path");
});

test("the contract never emits the slice verify marker", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifyMarker = ["M209_S01", "VERIFY_OK"].join("_");
  const emitter = new RegExp("console\\.log\\(\\s*[\"'`]" + verifyMarker);
  assert.ok(!emitter.test(source), `${verifyMarker} must be unreachable by construction`);
});

// ---------------------------------------------------------------------------
// fail-closed negatives (each code fires against a mutated checkpoint or source)
// ---------------------------------------------------------------------------

test("negative: verdict shape and the granted verdict", () => {
  expectCode(
    fixture((text) => text.replace(VERDICT_LINE, "**admission_state: pending**")),
    "verdict_missing",
  );
  expectCode(
    fixture((text) => text.replace(VERDICT_LINE, `${VERDICT_LINE}\n${GRANTED_LINE}`)),
    "verdict_ambiguous",
  );
  expectCode(grantedFixture(), "verdict_not_adopted");
  expectCode(grantedFixture(), "owner_admission_ref_missing");
});

test("negative: byte-bound source references", () => {
  expectCode(fixture((text) => text.replace(STRIP_SOURCE_ROWS, "")), "sources_insufficient");
  expectCode(fixture((text) => replaceSourcePath(text, MISSING_SOURCE)), "source_unresolved");
  expectCode(
    fixture((text) => replaceSourcePath(text, UNTRACKED_SOURCE)),
    "source_not_tracked",
    { fileExists: (candidate) => candidate === UNTRACKED_SOURCE || repoExists(candidate) },
  );
  expectCode(fixture((text) => replaceSourcePath(text, IGNORED_SOURCE)), "ignored_path_as_source");
  expectCode(
    fixture((text) => replaceSourcePath(text, `.gsd/phases/209-2yg6ix/209-01-PLAN.md`)),
    "ignored_path_as_source",
  );
  expectCode(fixture((text) => replaceSourcePath(text, ABSOLUTE_SOURCE)), "absolute_path_as_source");
  expectCode(fixture((text) => text.replace(sha256(ADMISSIONS), "0".repeat(64))), "source_hash_mismatch");
});

test("negative: required sections, decision fields and the resume condition", () => {
  for (const [heading, replacement] of [
    ["## Sources checked", "## Sources"],
    ["## Required decision fields", "## Required fields"],
    ["## Resume condition", "## Resume"],
    ["## Fail-closed boundary", "## Fail-closed"],
    ["## Marker semantics", "## Markers"],
    ["## Non-claims", "## Nonclaims"],
  ]) {
    expectCode(fixture((text) => text.replace(heading, replacement)), "section_missing");
  }
  expectCode(fixture((text) => dropDecisionField(text, "granted_by")), "required_decision_fields_missing");
  expectCode(
    fixture((text) =>
      replaceSectionBody(
        text,
        "## Required decision fields",
        [
          "1. `verdict_line` — exactly one verdict line.",
          "2. `granted_by` — the grantor.",
          "3. `scope` — the profiles covered.",
          "4. `cc_identity_form` — the identifier form.",
          "5. `admission_rows` — the rows to add.",
          "6. `declared_denominator` — the act plus candidates.",
          "7. `sources_checked` — byte-bound sources.",
          "8. `fail_closed_boundary` — the rejected codes.",
          "9. `supersede_rebind` — the supersede clause.",
        ].join("\n"),
      ),
    ),
    "required_decision_fields_missing",
  );
  expectCode(fixture((text) => dropDecisionField(text, "declared_denominator")), "denominator_missing");
  expectCode(
    fixture((text) =>
      replaceSectionBody(
        text,
        "## Resume condition",
        "Punkt admission resumes when the owner decides.",
      ),
    ),
    "resume_condition_missing",
  );
});

test("negative: admission minted from a non-decision", () => {
  expectCode(
    fixture((text) =>
      granted(text).replace(OWNER_REF_LINE, "**owner_admission_ref:** derived from the design pins"),
    ),
    "self_minted_adoption",
  );
  expectCode(
    fixture((text) => text.replace(OWNER_REF_LINE, `**owner_admission_ref:** interaction decision`)),
    "self_minted_adoption",
  );
  expectCode(
    fixture((text) =>
      granted(text).replace(OWNER_REF_LINE, "**owner_admission_ref:** verbal approval"),
    ),
    "owner_admission_ref_missing",
  );
  expectCode(
    fixture((text) =>
      basisPrefix(granted(text), "M206 runtime battery integrity PASS authorises the punkt admission."),
    ),
    "integrity_pass_as_admission",
  );
  expectCode(
    fixture((text) =>
      basisPrefix(
        granted(text),
        "D499 GSD_MILESTONE_LOCK authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
    ),
    "lock_as_admission",
  );
  expectCode(
    fixture((text) =>
      basisPrefix(
        granted(text),
        "The m209_s01_punkt_decision_contract PASS authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
    ),
    "contract_pass_as_admission",
  );
  expectCode(
    fixture((text) =>
      basisPrefix(
        granted(text),
        "The registry_rows baseline of 166 authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
    ),
    "metric_baseline_relabelled_as_admission",
  );
});

test("negative: cross-slice authorization claims", () => {
  expectCode(fixture((text) => `${text}\n\ns02_preauthorized: true\n`), "s02_preauthorized");
  expectCode(
    fixture((text) => `${text}\n\ns02_punkt_admission_authorized: true\n`),
    "s02_punkt_admission_authorized",
  );
  expectCode(
    fixture((text) => `${text}\n\ncross_slice_authorization_granted: true\n`),
    "cross_slice_authorization_granted",
  );
  expectCode(
    fixture((text) =>
      text.replace("S02 is not pre-authorized to admit punkt", "S02 is pre-authorized to admit punkt"),
    ),
    "s02_preauthorized",
  );
  expectCode(
    fixture((text) =>
      text.replace(CROSS_SLICE_FRAGMENT, "cross-slice authorization is granted by this record;"),
    ),
    "cross_slice_authorization_granted",
  );
});

test("negative: punkt rows admitted or misreported", () => {
  expectCode(doc, "punkt_row_admitted_without_decision", {
    admissionsText: withPunktRow(liveAdmissions),
  });
  expectCode(doc, "punkt_row_admitted_without_decision", {
    m202S04Text: liveM202S04.replace('"punkt_admitted": 0', '"punkt_admitted": 3'),
  });
  expectCode(
    fixture((text) => text.replace("**punkt_admission:** not-adopted", "**punkt_admission:** granted")),
    "punkt_admission_gate_claimed",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        "remains active for punkt registry admission",
        "lifted for punkt registry admission",
      ),
    ),
    "punkt_admission_gate_claimed",
  );
  expectCode(
    fixture((text) => text.replace("**punkt_rows_admitted:** 0", "**punkt_rows_admitted:** 3")),
    "punkt_rows_mismatch",
  );
  expectCode(
    fixture((text) => text.replace(EXPECTED_ADMITTED_CC[0], "cc:44-fz:glava-9")),
    "admitted_cc_mismatch",
  );
  expectCode(doc, "admitted_cc_mismatch", { m202S04Text: withExtraAdmittedCc(liveM202S04) });
});

test("negative: frozen input drift", () => {
  expectCode(doc, "m202_s03_modified", { frozenDelta: ` M ${M202_S03}` });
  expectCode(doc, "admissions_yaml_modified", { frozenDelta: ` M ${ADMISSIONS}` });
});

test("negative: granularity conflated with registry admission and R087 invalidated", () => {
  expectCode(
    fixture((text) => `${text}\n\nThe punkt granularity is a registry admission.\n`),
    "granularity_confused_with_registry_admission",
  );
  expectCode(doc, "granularity_confused_with_registry_admission", {
    ontologyText: liveOntology.replace("      granularity: statya", "      granularity: punkt"),
  });
  expectCode(
    fixture((text) => text.replace("remain validated (R087)", "are invalidated (R087)")),
    "r087_invalidated",
  );
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code. The test below asserts
// that each mutation actually makes its code fire, so a code can never be
// documented without being reachable, and can never be reachable without being
// documented.
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
  { code: "verdict_not_adopted", mutate: (text) => granted(text) },
  {
    code: "self_minted_adoption",
    mutate: (text) =>
      granted(text).replace(OWNER_REF_LINE, "**owner_admission_ref:** derived from the design pins"),
  },
  {
    code: "owner_admission_ref_missing",
    mutate: (text) => granted(text).replace(OWNER_REF_LINE, "**owner_admission_ref:** verbal"),
  },
  {
    code: "integrity_pass_as_admission",
    mutate: (text) =>
      basisPrefix(granted(text), "M206 runtime battery integrity PASS authorises the punkt admission."),
  },
  {
    code: "lock_as_admission",
    mutate: (text) =>
      basisPrefix(
        granted(text),
        "D499 GSD_MILESTONE_LOCK authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
  },
  { code: "sources_insufficient", mutate: (text) => text.replace(STRIP_SOURCE_ROWS, "") },
  { code: "source_unresolved", mutate: (text) => replaceSourcePath(text, MISSING_SOURCE) },
  {
    code: "source_not_tracked",
    mutate: (text) => replaceSourcePath(text, UNTRACKED_SOURCE),
    options: { fileExists: (candidate) => candidate === UNTRACKED_SOURCE || repoExists(candidate) },
  },
  {
    code: "source_hash_mismatch",
    mutate: (text) => text.replace(sha256(ADMISSIONS), "0".repeat(64)),
  },
  { code: "ignored_path_as_source", mutate: (text) => replaceSourcePath(text, IGNORED_SOURCE) },
  { code: "absolute_path_as_source", mutate: (text) => replaceSourcePath(text, ABSOLUTE_SOURCE) },
  { code: "section_missing", mutate: (text) => text.replace("## Non-claims", "## Nonclaims") },
  {
    code: "required_decision_fields_missing",
    mutate: (text) => dropDecisionField(text, "granted_by"),
  },
  {
    code: "resume_condition_missing",
    mutate: (text) =>
      replaceSectionBody(text, "## Resume condition", "Punkt admission resumes on owner decision."),
  },
  {
    code: "punkt_row_admitted_without_decision",
    options: { admissionsText: withPunktRow(liveAdmissions) },
  },
  {
    code: "punkt_admission_gate_claimed",
    mutate: (text) =>
      text.replace("**punkt_admission:** not-adopted", "**punkt_admission:** granted"),
  },
  {
    code: "punkt_rows_mismatch",
    mutate: (text) => text.replace("**punkt_rows_admitted:** 0", "**punkt_rows_admitted:** 3"),
  },
  {
    code: "admitted_cc_mismatch",
    options: { m202S04Text: withExtraAdmittedCc(liveM202S04) },
  },
  {
    code: "denominator_missing",
    mutate: (text) => dropDecisionField(text, "declared_denominator"),
  },
  {
    code: "s02_preauthorized",
    mutate: (text) => `${text}\n\ns02_preauthorized: true\n`,
  },
  {
    code: "s02_punkt_admission_authorized",
    mutate: (text) => `${text}\n\ns02_punkt_admission_authorized: true\n`,
  },
  {
    code: "contract_pass_as_admission",
    mutate: (text) =>
      basisPrefix(
        granted(text),
        "The m209_s01_punkt_decision_contract PASS authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
  },
  {
    code: "cross_slice_authorization_granted",
    mutate: (text) => `${text}\n\ncross_slice_authorization_granted: true\n`,
  },
  {
    code: "metric_baseline_relabelled_as_admission",
    mutate: (text) =>
      basisPrefix(
        granted(text),
        "The registry_rows baseline of 166 authorises the punkt admission (interaction 00000000-0000-0000-0000-000000000000).",
      ),
  },
  { code: "m202_s03_modified", options: { frozenDelta: ` M ${M202_S03}` } },
  { code: "admissions_yaml_modified", options: { frozenDelta: ` M ${ADMISSIONS}` } },
  {
    code: "granularity_confused_with_registry_admission",
    options: { ontologyText: liveOntology.replace("      granularity: statya", "      granularity: punkt") },
  },
  {
    code: "r087_invalidated",
    mutate: (text) => text.replace("remain validated (R087)", "are invalidated (R087)"),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const text = entry.mutate ? entry.mutate(doc) : doc;
    if (entry.mutate) {
      assert.notEqual(text, doc, `${entry.code}: the mutation must actually change the record`);
    }
    const result = validatePunkt(text, entry.options || {});
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the checkpoint contract holds)
// ---------------------------------------------------------------------------

test("M209 S01 punkt decision markers", () => {
  const result = validatePunkt(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.verdict, "not-adopted");
  assert.equal(admissionLevels(liveAdmissions).counts.punkt || 0, 0);
  assert.equal(safeJson(liveM202S03).output.punkt_rows_admitted, 0);
  assert.equal(safeJson(liveM202S04).mapping_counts.punkt_admitted, 0);
  console.log("M209_S01_PUNKT_OK");
  console.log("M209_S01_PUNKT_NOT_ADOPTED");
  console.log("M209_S01_PUNKT_ROWS_ZERO");
  console.log("punkt_admission=not-adopted");
  console.log("punkt_rows_admitted=0");
});
