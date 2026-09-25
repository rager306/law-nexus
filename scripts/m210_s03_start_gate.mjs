#!/usr/bin/env node
// M210-3afp79 S03 T01 -- explicit S03 start gate and runtime admission checkpoint,
// bound to the superseding S02 v2 admission.
//
// WHY THIS FILE EXISTS
// The milestone vision forbids starting the bounded semantic runtime before the
// owner adopts it. S02 first closed with `admission: not-adopted` and was then
// superseded by the v2 records that carry the owner's authenticated bounded
// adoption of variant C. This harness cannot enforce a milestone dependency, so
// S03 carries an explicit, machine-checked start gate instead of starting by the
// mere fact that S02 closed. This generator derives that gate from the live v2
// S02 artifacts and writes it as canonical ASCII JSON.
//
// WHAT IS DERIVED, FROM WHERE
//   * the single verdict line of prd/architecture/m210-s02-adoption-checkpoint-v2.md
//   * every row of that checkpoint's source table, re-hashed live from its
//     repository-relative path (8 rows). Both digest spellings are accepted --
//     a bare 64-hex value and a `sha256:`-prefixed value -- and are normalized
//     to the prefixed form before any comparison; a digest-shaped cell in any
//     other spelling is rejected by name rather than silently skipped.
//   * prd/architecture/m210-s02-answer-record-v2.json (status, answer source,
//     authenticated interactive references, f13 status and supersession claim)
//   * the superseded v1 checkpoint and v1 answer record, re-hashed live to prove
//     they were not rewritten behind the supersession
//   * prd/architecture/m210-s02-governing-surface-check.json, re-read under v2:
//     its `governing_surface_absent` verdict and its
//     `actor_bound_path_available: false` finding belong to the v1 state, so
//     they are recorded as a v1-scoped pre-decision finding rather than a
//     blocker. No repeat owner decision is required.
//   * the engine aggregate source revision, captured live from
//     scripts/m204_s08_source_revision.mjs (never hardcoded)
//
// THE GRANT RULE (fail-closed)
//   admission_granted is emitted only when ALL of the following hold at once:
//     - the v2 checkpoint carries exactly one verdict line reading `granted`;
//     - the v2 answer record status is `owner_decision_recorded`, its answer
//       source is an authenticated interactive conduit, and its interactive
//       reference carries an accepted disposition on an authenticated channel;
//     - the owner admission reference is exactly the criterion recorded in that
//       answer record (a superseded or foreign reference is refused);
//     - the grant scope is bounded exactly to variant C: rule composition,
//       precedence resolution, facet defaults and case applicability stay
//       outside it;
//     - the runtime stop is lifted for the adopted candidate layer only and
//       stays active for composed-rule runtime, applicability runtime and any
//       section 3 promotion (a blanket lift is refused);
//     - the superseded v1 checkpoint and v1 answer record are byte-identical to
//       the digests the v2 records bind, so no receipt was silently rewritten.
//   A GSD milestone lock, an integrity or battery PASS, a milestone closeout, an
//   ADR status and any bare name or role title are never grantor references and
//   are rejected by their own named codes.
//
// ADOPTION IS NOT EXECUTION
//   The gate records the adoption in `adoption_state` and the fact that nothing
//   was executed in `execution_state`. A grant does not emit candidates by
//   itself, so `executed` stays false, `candidates_emitted` stays 0 and the
//   runtime demo stays not-proven. Reading adoption as execution, or execution
//   as adoption, is refused by its own named code.
//
// SOURCE REVISION IS A SNAPSHOT, NOT A LIVE INVARIANT
//   The engine aggregate hash covers tracked content plus untracked non-ignored
//   files (`git ls-files --cached --others --exclude-standard`), so writing this
//   report shifts the aggregate. The stored value is therefore the revision
//   captured at render time, before this report existed; it is not a live
//   invariant. `--check` re-renders with the committed revision for the byte
//   compare while still capturing the live revision to prove the capture path.
//
// USAGE
//   node scripts/m210_s03_start_gate.mjs --write   # default
//   node scripts/m210_s03_start_gate.mjs --check
//   node scripts/m210_s03_start_gate.mjs --print

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const START_GATE_RELATIVE_PATH = "prd/architecture/m210-s03-start-gate.json";
export const ADMISSION_RELATIVE_PATH = "prd/architecture/m210-s03-runtime-admission.md";

// The authoritative (live) S02 sources this gate binds.
export const S02_CHECKPOINT_PATH = "prd/architecture/m210-s02-adoption-checkpoint-v2.md";
export const S02_ANSWER_PATH = "prd/architecture/m210-s02-answer-record-v2.json";
export const S02_GOVERNING_PATH = "prd/architecture/m210-s02-governing-surface-check.json";
// The superseded (historical) S02 sources; their bytes must survive untouched.
export const S02_CHECKPOINT_V1_PATH = "prd/architecture/m210-s02-adoption-checkpoint.md";
export const S02_ANSWER_V1_PATH = "prd/architecture/m210-s02-answer-record.json";
export const S02_REBIND_PATH = "prd/architecture/m210-s02-rebind-report.json";
export const SOURCE_REVISION_SCRIPT = "scripts/m204_s08_source_revision.mjs";
export const SECTION3_PATH = "prd/temporal-legal-model.md";
export const CONTRACT_PATH = "scripts/m210_s03_start_gate_contract.test.mjs";

export const SCHEMA = "law-nexus/m210-s03-start-gate/v2";
export const SCHEMA_VERSION = 2;
export const KIND = "m210-s03-start-gate";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S03";
export const TASK = "T01";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

// The recorded pin of prd/temporal-legal-model.md section 3. It is a target-file
// pin, not the aggregate source revision, and it is the only 64-hex literal this
// generator may carry.
export const SECTION3_PIN =
  "sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6";

// The surfaces a granted S03 could later create. They are declared, not created:
// this slice is gate integration, so every one of them must stay absent on disk.
export const DECLARED_ABSENT_RUNTIME_SURFACES = [
  "crates/ln-temporal/src/normative_candidate.rs",
  "crates/ln-temporal/src/bounded_semantics.rs",
  "crates/ln-temporal/tests/normative_candidate_contract.rs",
  "crates/ln-decode/src/candidate_emission.rs",
  "scripts/m210_s03_verify.sh",
];

// Surfaces that are explicitly out of scope and must never be claimed here.
export const OUT_OF_SCOPE_SURFACES = [
  "ln-applicability NormRule",
  "RuVector",
  "TEI",
  "F13 operation grammar",
];

// The adopted construct layer (variant C) and its hard ceiling.
export const ADOPTED_VARIANT = "C";
export const ADOPTED_VARIANT_LABEL = "abstention_first_candidates_only";
export const ADOPTED_CONSTRUCT_SET = [
  "candidate_emission",
  "source_anchors",
  "family_classification_hypotheses",
  "unknown_verdict",
  "conflict_verdict",
  "provenance_links",
];
export const EXCLUDED_CONSTRUCT_SET = [
  "rule_composition",
  "precedence_resolution",
  "facet_defaults",
  "case_applicability",
];

export const REQUIRED_HEADERS = [
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
];

export const REQUIRED_SECTIONS = [
  "## Purpose and boundary",
  "## Sources checked",
  "## Start gate verdict",
  "## Owning surfaces (declared, not created)",
  "## Non-claims",
  "## Fail-closed boundary",
  "## Marker semantics",
  "## Resume condition",
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
  "admission_verdict_mismatch",
  "grant_without_interactive_ref",
  "grant_without_governing_surface",
  "non_owner_surface_as_grantor",
  "lock_as_admission",
  "integrity_pass_as_admission",
  "milestone_closeout_as_admission",
  "runtime_permitted_without_admission",
  "runtime_stop_inverted",
  "no_start_directive_missing",
  "runtime_demo_claimed",
  "s03_surface_present",
  "lib_rs_registration_present",
  "crate_touched",
  "requirements_promoted",
  "review_case_event_written",
  "section3_mutated",
  "out_of_scope_surface_claimed",
  "f13_scope_borrowed",
  "runtime_claim_present",
  "check_not_byte_identical",
  "non_ascii_artifact",
  "raw_text_leak",
  "v2_source_not_wired",
  "superseded_source_selected",
  "superseded_hash_accepted",
  "superseded_ref_accepted",
  "scope_overclaim",
  "owner_decision_read_as_answered",
  "f13_hold_misread",
  "source_pin_form_rejected",
  "runtime_stop_blanket_lifted",
  "adoption_read_as_execution",
  "execution_read_as_adoption",
  "receipt_silently_rewritten",
];

export const WRITTEN_MARKER = "M210_S03_START_GATE_WRITTEN";
export const CHECK_OK_MARKER = "M210_S03_START_GATE_CHECK_OK";
export const PRINT_MARKER = "M210_S03_START_GATE_PRINTED";
export const MD_ABSENT_NOTE = "M210_S03_ADMISSION_MD_ABSENT";
export const CONTRACT_MARKER = "M210_S03_START_GATE_OK";

export const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const SOURCE_REVISION_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const VERDICT_RE = /^\*\*admission: (granted|not-adopted)\*\*$/m;
export const VERDICT_ANY_RE = /^\*\*admission: .*\*\*$/gm;
const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
export const INTERACTIVE_REF_RE = new RegExp(
  `^(?:subjective-UAT criterion\\s+)?${UUID}$|^(?:interaction\\s+)?${UUID}$|^criterion[:/][A-Za-z0-9][A-Za-z0-9._:/-]{3,}$`,
  "i",
);
export const OWNER_REF_RE = new RegExp(`^subjective-UAT criterion\\s+${UUID}$`, "i");

// Only an authenticated interactive conduit can carry a grant. A saved answer, a
// design pin, a lock, a battery result and a closeout are all excluded.
export const AUTHENTICATED_ANSWER_SOURCES = ["interactive", "subjective_uat_criterion"];
// The v2 status is `owner_decision_recorded`; it is never normalized to the older
// `answered` spelling, and that misreading has its own named code.
export const OWNER_DECISION_RECORDED = "owner_decision_recorded";
export const ACCEPTED_ANSWER_STATUSES = [OWNER_DECISION_RECORDED];
export const AUTHENTICATED_CHANNEL_RE = /authenticated/i;

export const F13_HOLD = "hold";
export const F13_DEFERRED_EXPLICIT = "deferred-explicit";

export const RUNTIME_PERMITTED_WORK = "fail_closed_no_start";
export const GRANTED_PERMITTED_WORK = "bounded_semantic_runtime_implementation";

export const RUNTIME_STOP_ACTIVE = "active";
export const RUNTIME_STOP_LIFTED = "lifted_candidate_layer_only";
export const RUNTIME_WORK_NOT_STARTED = "not-started";
export const RUNTIME_DEMO_NOT_PROVEN = "not-proven";
export const RUNTIME_STOP_STILL_ACTIVE = [
  "composed-rule runtime",
  "applicability runtime",
  "section 3 promotion",
];

export const MIN_S02_SOURCES = 8;
export const MIN_MD_SOURCES = 12;

export const SOURCE_VERDICTS = ["match", "unresolved", "hash_mismatch"];

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const LOCK_RE = /\bd499\b|\bgsd[_ ]?milestone[_ ]?lock\b|\bmilestone lock\b/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b/i;
const CLOSEOUT_RE = /\bcloseout\b|\bmilestone\s+(?:closeout|completion)\b/i;
const NON_OWNER_RE =
  /\badr[-\s]?\d+\b|\baccept(?:ed|ance)\s+status\b|\bcontract\s+pass\b|\bbare\s+name\b|\brole\s+title\b/i;

const NON_CLAIMS = [
  "This gate is a start-gate record: it is not a grant, not an approval, not a waiver, not a requirement closure, not a Review Case disposition, not a legal conclusion and not a lifecycle promotion.",
  "admission_granted is derived from the authenticated bounded adoption of variant C recorded in the superseding S02 v2 sources: it permits the adopted candidate layer only and it is not an execution of that layer.",
  "The adoption is a bounded construct-layer adoption and not a normative semantics adoption: section 3 of prd/temporal-legal-model.md stays byte-identical to its pin and its deferred terms stay deferred-undefined.",
  "No runtime surface is created by this gate: every declared runtime surface is named as declared-and-absent and none of them exists on disk.",
  "RC28-F18 requires a human-owned legal IR adoption before implementation; a milestone lock, an integrity result, a milestone closeout, an ADR status and any bare name or role title are never grantor references.",
  "F13 stays deferred-explicit: it is a separate decision with its own owning surfaces and it is never derived from the bounded IR.",
  "The superseded v1 S02 checkpoint and the superseded v1 S02 answer record stay byte-identical and hash-bound as history; nothing is rewritten behind them.",
  "Out-of-scope surfaces stay untouched: ln-applicability NormRule, RuVector, TEI and the F13 operation grammar are not claimed here.",
  "The bounded semantics contract, the abstention diagnostic and the activation delta stay design-only and are not created by this gate.",
];

export class StartGateError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "StartGateError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new StartGateError(code, detail);
}

// ---------------------------------------------------------------------------
// path and text helpers
// ---------------------------------------------------------------------------

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  if (value.startsWith("/")) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

export function isIgnoredPath(value) {
  return (
    typeof value === "string" && IGNORED_SOURCE_PREFIXES.some((prefix) => value.startsWith(prefix))
  );
}

export function admissiblePath(value) {
  return isRepoRelative(value) && !isIgnoredPath(value);
}

export function sha256Text(text) {
  return `sha256:${createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex")}`;
}

// Node's test runner marks each child test process with NODE_TEST_CONTEXT. A
// contract spawned from inside `node --test` inherits it and the nested runner
// then suppresses reporter output: the run exits 0 but prints no parseable
// counts, which would look green. Strip it for every spawn (S01 precedent).
export function cleanTestEnv(env = process.env) {
  const cleaned = { ...env };
  delete cleaned.NODE_TEST_CONTEXT;
  return cleaned;
}

export function fileLookup(rootDir = REPO_ROOT) {
  const realRoot = realpathSync(rootDir);
  const bytesCache = new Map();
  const insideCache = new Map();
  const bytes = (relativePath) => {
    if (bytesCache.has(relativePath)) return bytesCache.get(relativePath);
    let value = null;
    try {
      value = readFileSync(path.join(rootDir, relativePath));
    } catch {
      value = null;
    }
    bytesCache.set(relativePath, value);
    return value;
  };
  return {
    exists: (relativePath) => existsSync(path.join(rootDir, relativePath)),
    bytes,
    // Symlink escapes are fail-closed: a declared path whose real target leaves
    // the repository root is not admissible, whatever its spelling.
    insideRoot: (relativePath) => {
      if (insideCache.has(relativePath)) return insideCache.get(relativePath);
      let inside = false;
      try {
        const real = realpathSync(path.join(rootDir, relativePath));
        inside = real === realRoot || real.startsWith(`${realRoot}${path.sep}`);
      } catch {
        inside = false;
      }
      insideCache.set(relativePath, inside);
      return inside;
    },
    sha256: (relativePath) => {
      const value = bytes(relativePath);
      if (!value) return null;
      return `sha256:${createHash("sha256").update(value).digest("hex")}`;
    },
  };
}

function readText(rootDir, relativePath) {
  const absolute = path.join(rootDir, relativePath);
  if (!existsSync(absolute)) fail("source_unresolved", `${relativePath} is absent`);
  return readFileSync(absolute, "utf8");
}

function flat(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/\s+/g, " ")
    .trim();
}

export function headerValue(doc, key) {
  const lines = String(doc).split("\n");
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

// A header may carry the digest plus trailing prose; the digest is what binds.
export function firstDigest(value) {
  const match = String(value ?? "").match(/sha256:[0-9a-f]{64}/);
  if (match) return match[0];
  return flat(value) === "" ? null : flat(value);
}

export function section(doc, heading) {
  const lines = String(doc).split("\n");
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

// ---------------------------------------------------------------------------
// source pin parsing (both digest spellings, normalized before comparison)
// ---------------------------------------------------------------------------

export const PIN_FORM_BARE = "bare64";
export const PIN_FORM_PREFIXED = "sha256_prefixed";

// A pin is accepted in exactly two spellings: a bare 64-hex digest and the
// canonical `sha256:`-prefixed digest. Anything else is not a pin.
export function normalizePin(value) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (/^[0-9a-f]{64}$/.test(trimmed)) return `sha256:${trimmed}`;
  if (/^sha256:[0-9a-f]{64}$/.test(trimmed)) return trimmed;
  return null;
}

export function pinForm(value) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (/^[0-9a-f]{64}$/.test(trimmed)) return PIN_FORM_BARE;
  if (/^sha256:[0-9a-f]{64}$/.test(trimmed)) return PIN_FORM_PREFIXED;
  return null;
}

const TABLE_ROW_SKIP_PATH = new Set(["Source", "source", "Path", "path"]);

// A cell looks like a pin if, after an optional `sha256:` prefix, it is a run of
// hex digits and colons. Cells in this shape that do not form a valid pin are
// rejected by name instead of being skipped, so a malformed digest cannot pass as
// prose.
function looksLikeDigest(cell) {
  return /^[0-9a-fA-F:]{32,}$/.test(String(cell).replace(/^sha256:/i, ""));
}

// Parse every source row of a markdown table, accepting both digest spellings and
// an optional parenthetical annotation after the path. A digest-shaped cell in
// any other spelling is reported as a rejected pin form instead of being dropped
// silently, so the parser never weakens validation.
export function parseSourceTable(doc) {
  const rows = [];
  const rejects = [];
  for (const line of String(doc).split("\n")) {
    if (!line.startsWith("|")) continue;
    const cells = line.split("|");
    if (cells.length < 4) continue;
    const rawPath = cells[1].replace(/`/g, "").trim();
    const rawPin = cells[2].replace(/`/g, "").trim();
    if (rawPath === "" || rawPin === "") continue;
    if (TABLE_ROW_SKIP_PATH.has(rawPath)) continue;
    if (/^-{2,}$/.test(rawPin) || rawPin === "sha256") continue;
    const normalized = normalizePin(rawPin);
    if (normalized === null) {
      if (looksLikeDigest(rawPin)) rejects.push({ path: rawPath, pin: rawPin });
      continue;
    }
    rows.push({
      path: rawPath.replace(/\s+\([^)]*\)$/, ""),
      sha256: normalized,
      pin_form: pinForm(rawPin),
    });
  }
  return { rows, rejects };
}

export function sourcePinFormRejections(doc) {
  return parseSourceTable(doc).rejects;
}

// Historical names kept so earlier importers keep working; both now normalize.
export function checkpointSourceRows(doc) {
  return parseSourceTable(doc).rows;
}

export function admissionSourceRows(doc) {
  return parseSourceTable(doc).rows;
}

// ---------------------------------------------------------------------------
// declared module registration
// ---------------------------------------------------------------------------

export function declaredModuleNames(surfaces = DECLARED_ABSENT_RUNTIME_SURFACES) {
  const names = new Map();
  for (const surface of surfaces) {
    const match = /^crates\/([^/]+)\/src\/([^/]+)\.rs$/.exec(surface);
    if (match) names.set(match[2], `crates/${match[1]}/src/lib.rs`);
  }
  return [...names.entries()].map(([name, lib]) => ({ name, lib }));
}

export function findModRegistrations(rootDir = REPO_ROOT, surfaces = DECLARED_ABSENT_RUNTIME_SURFACES) {
  const found = [];
  for (const { name, lib } of declaredModuleNames(surfaces)) {
    const absolute = path.join(rootDir, lib);
    if (!existsSync(absolute)) continue;
    const text = readFileSync(absolute, "utf8");
    const re = new RegExp(`(?:^|\\n)\\s*(?:pub\\s+)?mod\\s+${name}\\s*;`);
    if (re.test(text)) found.push(name);
  }
  return found;
}

// ---------------------------------------------------------------------------
// source revision capture (live subprocess, never a stored literal)
// ---------------------------------------------------------------------------

export function captureSourceRevision(rootDir = REPO_ROOT, options = {}) {
  const spawned = spawnSync(options.execPath ?? process.execPath, [SOURCE_REVISION_SCRIPT], {
    cwd: rootDir,
    encoding: "utf8",
    timeout: options.timeoutMs ?? 120000,
    maxBuffer: 8 * 1024 * 1024,
    env: cleanTestEnv(options.env ?? process.env),
  });
  const output = `${spawned.stdout || ""}${spawned.stderr || ""}`.trim();
  if (spawned.status !== 0) {
    fail("source_revision_mismatch", `${SOURCE_REVISION_SCRIPT} exited ${spawned.status}: ${output}`);
  }
  let parsed;
  try {
    parsed = JSON.parse(output.split("\n").filter(Boolean).pop());
  } catch {
    fail("source_revision_mismatch", `${SOURCE_REVISION_SCRIPT} printed no JSON: ${output}`);
  }
  if (parsed?.ok !== true || typeof parsed.source_revision !== "string") {
    fail("source_revision_mismatch", `${SOURCE_REVISION_SCRIPT} returned ${JSON.stringify(parsed)}`);
  }
  if (!SOURCE_REVISION_PATTERN.test(parsed.source_revision)) {
    fail("source_revision_mismatch", `unexpected source revision shape: ${parsed.source_revision}`);
  }
  return parsed.source_revision;
}

// ---------------------------------------------------------------------------
// S02 input parsing
// ---------------------------------------------------------------------------

// Extract the canonical owner reference from the checkpoint header. The v2 header
// carries the criterion plus the question and interaction ids on one line, so the
// canonical criterion form is extracted rather than compared verbatim.
export function parseOwnerRef(doc) {
  const raw = flat(headerValue(doc, "owner_admission_ref"));
  if (raw === "") return null;
  const criterion = raw.match(new RegExp(`subjective-UAT criterion\\s+(${UUID})`, "i"));
  if (criterion) return `subjective-UAT criterion ${criterion[1]}`;
  const uuid = raw.match(new RegExp(UUID, "i"));
  if (uuid && /\binteraction\b/i.test(raw)) return `interaction ${uuid[0]}`;
  return raw;
}

export function parseS02Checkpoint(doc) {
  const text = String(doc);
  // The phrases under test are prose that wraps across lines, so they are
  // matched against a whitespace-normalized copy rather than the raw text.
  const flatText = flat(text);
  const verdictLines = text.match(VERDICT_ANY_RE) || [];
  const match = text.match(VERDICT_RE);
  const table = parseSourceTable(text);
  const runtimeStopHeader = flat(headerValue(text, "runtime_stop"));
  return {
    text,
    verdictLines,
    verdict: match ? match[1] : null,
    sources: table.rows,
    sourceRejects: table.rejects,
    pinForms: [...new Set(table.rows.map((row) => row.pin_form))].filter(Boolean).sort(),
    f13Status: flat(headerValue(text, "f13_status")),
    ownerAdmissionRef: parseOwnerRef(text),
    rawOwnerAdmissionRef: flat(headerValue(text, "owner_admission_ref")),
    sourceRevision: flat(headerValue(text, "source_revision")),
    testedSourceRevision: firstDigest(headerValue(text, "tested_source_revision")),
    resumeCondition: flat(section(text, "## Resume condition")),
    scopeBounded:
      /scope of the grant is bounded exactly to what the owner adopted/i.test(flatText) &&
      /rule composition, precedence resolution, facet defaults and case applicability remain outside the adopted scope/i.test(
        flatText,
      ),
    variantCFound:
      flatText.includes(ADOPTED_VARIANT_LABEL) && /variant\s+C|variant\s+3/i.test(flatText),
    runtimeStopScoped: /lifted for the adopted candidate-layer scope only/i.test(runtimeStopHeader),
    runtimeStopHeader,
  };
}

export function parseAnswerRecord(answer) {
  const ir = answer?.interactive_refs?.ir ?? {};
  const f13 = answer?.interactive_refs?.f13 ?? {};
  const fallback = answer?.ir_answer ?? {};
  const supersedes = answer?.supersedes ?? {};
  const irCriterion = typeof ir.criterion_id === "string" && ir.criterion_id !== "" ? ir.criterion_id : null;
  const f13Criterion = typeof f13.criterion_id === "string" && f13.criterion_id !== "" ? f13.criterion_id : null;
  let irRef = null;
  if (irCriterion) irRef = `subjective-UAT criterion ${irCriterion}`;
  else if (typeof fallback.interaction_id === "string" && fallback.interaction_id !== "")
    irRef = `interaction ${fallback.interaction_id}`;
  else if (typeof fallback.criterion_id === "string" && fallback.criterion_id !== "")
    irRef = fallback.criterion_id;
  return {
    status: typeof answer?.status === "string" ? answer.status : null,
    answerSource: typeof answer?.answer_source === "string" ? answer.answer_source : null,
    irRef,
    f13Ref: f13Criterion ? `subjective-UAT criterion ${f13Criterion}` : null,
    channel: typeof ir.channel === "string" ? ir.channel : null,
    disposition: typeof ir.disposition === "string" ? ir.disposition : null,
    f13Status: typeof answer?.f13_status === "string" ? answer.f13_status : null,
    supersedesPath: typeof supersedes.path === "string" ? supersedes.path : null,
    supersedesPin: normalizePin(supersedes.sha256),
    testedSourceRevision:
      firstDigest(answer?.ir_answer?.tested_source_revision) ||
      firstDigest(answer?.f13_answer?.tested_source_revision) ||
      null,
    guards: answer?.guards ?? {},
  };
}

export function collectInteractiveRefs(answer) {
  const ir = answer?.ir_answer ?? {};
  const candidates = [ir.criterion_id, ir.interaction_id, answer?.criterion_id, answer?.interaction_id];
  return candidates.filter((value) => typeof value === "string" && value.trim() !== "");
}

export function interactiveRefPresent(answer) {
  const source = answer?.answer_source;
  if (!AUTHENTICATED_ANSWER_SOURCES.includes(source)) return false;
  if (!ACCEPTED_ANSWER_STATUSES.includes(answer?.status)) return false;
  return collectInteractiveRefs(answer).some((value) => INTERACTIVE_REF_RE.test(value));
}

// ---------------------------------------------------------------------------
// derivation
// ---------------------------------------------------------------------------

export function deriveStartGate(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const bindingPaths = {
    checkpoint: options.binding?.checkpoint ?? S02_CHECKPOINT_PATH,
    answer: options.binding?.answer ?? S02_ANSWER_PATH,
  };
  const checkpointText = options.checkpointText ?? readText(rootDir, bindingPaths.checkpoint);
  const answerRecord = options.answer ?? JSON.parse(readText(rootDir, bindingPaths.answer));
  const governing = options.governing ?? JSON.parse(readText(rootDir, S02_GOVERNING_PATH));
  const v1CheckpointText = options.v1CheckpointText ?? readText(rootDir, S02_CHECKPOINT_V1_PATH);
  const v1AnswerRecord = options.v1Answer ?? JSON.parse(readText(rootDir, S02_ANSWER_V1_PATH));
  const sourceRevision = options.sourceRevision;
  if (!SOURCE_REVISION_PATTERN.test(String(sourceRevision))) {
    fail("source_revision_mismatch", `source revision ${sourceRevision} is not sha256:<64hex>`);
  }

  const checkpoint = parseS02Checkpoint(checkpointText);
  const answer = parseAnswerRecord(answerRecord);
  const v1Checkpoint = parseS02Checkpoint(v1CheckpointText);
  const v1Answer = parseAnswerRecord(v1AnswerRecord);

  const channelAuthenticated = AUTHENTICATED_CHANNEL_RE.test(String(answer.channel ?? ""));
  const dispositionAccepted = String(answer.disposition ?? "").toLowerCase() === "accepted";
  const statusAccepted = ACCEPTED_ANSWER_STATUSES.includes(answer.status);
  const authenticatedDirection =
    statusAccepted &&
    AUTHENTICATED_ANSWER_SOURCES.includes(answer.answerSource) &&
    answer.irRef !== null &&
    channelAuthenticated &&
    dispositionAccepted;

  const ownerRef = checkpoint.ownerAdmissionRef;
  const ownerRefMatches = ownerRef !== null && ownerRef === answer.irRef;

  const granted =
    checkpoint.verdict === "granted" &&
    checkpoint.verdictLines.length === 1 &&
    authenticatedDirection &&
    ownerRefMatches &&
    checkpoint.scopeBounded &&
    checkpoint.variantCFound &&
    checkpoint.runtimeStopScoped &&
    answer.f13Status === F13_DEFERRED_EXPLICIT;

  const admissionVerdict = granted ? "admission_granted" : "admission_absent";
  const verdictText = checkpoint.verdict === null ? "absent" : checkpoint.verdict;
  const admissionBasis = granted
    ? "admission_granted is derived from the superseding S02 v2 sources: the adoption checkpoint carries exactly one verdict line reading granted with the bounded variant C scope, the answer record v2 status is owner_decision_recorded with an authenticated interactive source and an accepted disposition on an authenticated channel, the governing-surface check verdict governing_surface_absent is re-read under v2 as a v1-scoped pre-decision finding rather than a blocker, and the superseded v1 checkpoint and v1 answer record stay byte-identical."
    : `admission_absent is derived from the bound S02 sources: the checkpoint verdict is ${verdictText}, the answer record status is ${answer.status} with answer_source ${answer.answerSource}, the interactive reference is ${ownerRef === null ? "absent" : ownerRef}, and the governing-surface check verdict is ${governing?.verdict ?? "absent"}.`;

  const s02Sources = checkpoint.sources.map((row) => {
    let verdict = "match";
    let live = "";
    if (!admissiblePath(row.path) || !lookup.insideRoot(row.path)) {
      verdict = "unresolved";
    } else if (!lookup.exists(row.path)) {
      verdict = "unresolved";
    } else {
      live = lookup.sha256(row.path) ?? "";
      if (live !== row.sha256) verdict = "hash_mismatch";
    }
    return {
      path: row.path,
      recorded_sha256: row.sha256,
      live_sha256: live,
      pin_form: row.pin_form,
      verdict,
    };
  });

  const tableDigest = (relativePath) => {
    const row = checkpoint.sources.find((entry) => entry.path === relativePath);
    return row ? row.sha256 : null;
  };

  const v1CheckpointExpected = tableDigest(S02_CHECKPOINT_V1_PATH);
  const v1AnswerExpectedFromTable = tableDigest(S02_ANSWER_V1_PATH);
  const v1CheckpointLive = lookup.sha256(S02_CHECKPOINT_V1_PATH) ?? null;
  const v1AnswerLive = lookup.sha256(S02_ANSWER_V1_PATH) ?? null;
  const v1AnswerExpected = answer.supersedesPin ?? v1AnswerExpectedFromTable;

  const checkpointSha = lookup.sha256(bindingPaths.checkpoint) ?? "";
  const answerSha = lookup.sha256(bindingPaths.answer) ?? "";
  const governingSha = lookup.sha256(S02_GOVERNING_PATH) ?? "";

  const rebind = options.rebind ?? JSON.parse(readText(rootDir, S02_REBIND_PATH));
  const rebindRevision = flat(rebind?.source_revision);

  const report = {
    schema: SCHEMA,
    schema_version: SCHEMA_VERSION,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: LIFECYCLE,
    authoritative: false,
    ascii_only: true,
    requirement_refs: REQUIREMENT_REFS,
    admission_verdict: admissionVerdict,
    admission_basis: admissionBasis,
    binding: {
      checkpoint: {
        path: bindingPaths.checkpoint,
        recorded_sha256: checkpointSha,
        live_sha256: checkpointSha,
        verdict: verdictText,
        tested_source_revision: checkpoint.testedSourceRevision || null,
        scope_bounded_to_variant_c: checkpoint.scopeBounded === true,
        variant_c_found: checkpoint.variantCFound === true,
        runtime_stop_scoped: checkpoint.runtimeStopScoped === true,
        superseded_v1_path: S02_CHECKPOINT_V1_PATH,
      },
      answer: {
        path: bindingPaths.answer,
        recorded_sha256: answerSha,
        live_sha256: answerSha,
        status: answer.status,
        answer_source: answer.answerSource,
        ir_criterion_ref: answer.irRef,
        f13_criterion_ref: answer.f13Ref,
        channel: answer.channel,
        disposition: answer.disposition,
        f13_status: answer.f13Status,
        supersedes_path: answer.supersedesPath,
        supersedes_pin: answer.supersedesPin,
      },
      governing: {
        path: S02_GOVERNING_PATH,
        recorded_sha256: governingSha,
        live_sha256: governingSha,
        verdict: governing?.verdict ?? null,
        answer_record_ref: governing?.answer_record_ref ?? null,
        source_revision: flat(governing?.source_revision) || null,
        actor_bound_path_available: governing?.actor_bound_path_available ?? null,
        reread_under: "v2",
        verdict_applies_to: "v1",
        blocking: false,
      },
      superseded: {
        checkpoint_v1: {
          path: S02_CHECKPOINT_V1_PATH,
          expected_sha256: v1CheckpointExpected,
          live_sha256: v1CheckpointLive,
          v1_verdict: v1Checkpoint.verdict,
          verdict:
            v1CheckpointExpected !== null && v1CheckpointLive === v1CheckpointExpected
              ? "preserved"
              : "rewritten",
        },
        answer_v1: {
          path: S02_ANSWER_V1_PATH,
          expected_sha256: v1AnswerExpected,
          table_sha256: v1AnswerExpectedFromTable,
          live_sha256: v1AnswerLive,
          v1_status: v1Answer.status,
          verdict:
            v1AnswerExpected !== null && v1AnswerLive === v1AnswerExpected ? "preserved" : "rewritten",
        },
      },
    },
    s02_checkpoint: {
      path: bindingPaths.checkpoint,
      recorded_sha256: checkpointSha,
      live_sha256: checkpointSha,
      verdict: verdictText,
    },
    s02_answer: {
      path: bindingPaths.answer,
      recorded_sha256: answerSha,
      live_sha256: answerSha,
      status: answer.status,
    },
    s02_sources: s02Sources,
    source_pin_form: {
      accepted_forms: [PIN_FORM_BARE, PIN_FORM_PREFIXED],
      checkpoint_forms: checkpoint.pinForms,
      rejected: checkpoint.sourceRejects.map((reject) => ({ path: reject.path, pin_form: "unrecognized" })),
    },
    answer_provenance: {
      path: bindingPaths.answer,
      status: answer.status,
      answer_source: answer.answerSource,
      interactive_ref_present: authenticatedDirection,
      channel: answer.channel,
      disposition: answer.disposition,
      ir_criterion_ref: answer.irRef,
      f13_criterion_ref: answer.f13Ref,
      owner_ref_matches_criterion: ownerRefMatches,
      governing_surface_verdict: governing?.verdict ?? null,
      governing_surface_reread: "v2_supersession",
      governing_blocking: false,
    },
    adoption_state: {
      admission_verdict: admissionVerdict,
      adoption_established: granted,
      adopted_variant: granted ? ADOPTED_VARIANT : null,
      adopted_variant_label: granted ? ADOPTED_VARIANT_LABEL : null,
      adopted_construct_set: granted ? ADOPTED_CONSTRUCT_SET : [],
      authenticated_via: granted ? "authenticated subjective-UAT v2" : "none",
      owner_admission_ref: granted && ownerRef ? ownerRef : "none",
      normative_semantics_adopted: false,
      section3_terms: "deferred-undefined",
      execution_separated: true,
    },
    execution_state: {
      executed: false,
      candidates_emitted: 0,
      conflicts: 0,
      runtime_work: RUNTIME_WORK_NOT_STARTED,
      runtime_demo: RUNTIME_DEMO_NOT_PROVEN,
    },
    revision_binding: {
      checkpoint_tested_source_revision: checkpoint.testedSourceRevision || null,
      answer_tested_source_revision: answer.testedSourceRevision,
      rebind_report_source_revision: rebindRevision,
      checkpoint_matches_answer:
        checkpoint.testedSourceRevision !== "" &&
        checkpoint.testedSourceRevision === answer.testedSourceRevision,
      checkpoint_matches_rebind_report:
        checkpoint.testedSourceRevision !== "" && checkpoint.testedSourceRevision === rebindRevision,
    },
    superseded_receipts: {
      checkpoint_v1: S02_CHECKPOINT_V1_PATH,
      answer_v1: S02_ANSWER_V1_PATH,
      prior_start_gate_record: START_GATE_RELATIVE_PATH,
      prior_start_gate_commits: "c72e2e3..0e0ea68",
      policy:
        "append-or-supersede: the superseded v1 S02 bytes and every earlier S03 receipt stay in git history; this record rewrites nothing behind them",
    },
    runtime_implementation_permitted: granted,
    permitted_work: granted ? [GRANTED_PERMITTED_WORK] : [RUNTIME_PERMITTED_WORK],
    adopted_variant: granted ? ADOPTED_VARIANT : null,
    adopted_variant_label: granted ? ADOPTED_VARIANT_LABEL : null,
    adopted_construct_set: granted ? ADOPTED_CONSTRUCT_SET : [],
    declared_absent_runtime_surfaces: DECLARED_ABSENT_RUNTIME_SURFACES,
    out_of_scope_surfaces: OUT_OF_SCOPE_SURFACES.map((name) => ({ name, claimed: false })),
    owner_admission_ref: granted && ownerRef ? ownerRef : "none",
    runtime_stop: granted ? RUNTIME_STOP_LIFTED : RUNTIME_STOP_ACTIVE,
    runtime_stop_scope: granted
      ? { lifted_for: "adopted candidate layer", still_active_for: RUNTIME_STOP_STILL_ACTIVE }
      : { lifted_for: "none", still_active_for: ["the whole bounded semantic runtime"] },
    runtime_work: RUNTIME_WORK_NOT_STARTED,
    runtime_demo: RUNTIME_DEMO_NOT_PROVEN,
    f13_status: granted
      ? answer.f13Status || F13_DEFERRED_EXPLICIT
      : checkpoint.f13Status || flat(governing?.f13_status) || F13_HOLD,
    source_revision: sourceRevision,
    guards: {
      crates_touched: [],
      requirements_promoted: 0,
      review_case_events_written: 0,
      semantics_adopted: false,
      section3_pin: SECTION3_PIN,
    },
    fail_closed_codes: EMITTABLE_CODES,
    non_claims: NON_CLAIMS,
  };
  return {
    report,
    checkpoint,
    answer,
    governing,
    v1Checkpoint,
    v1Answer,
    checkpointText,
    binding: bindingPaths,
    lookup,
    rootDir,
    sourceRevision,
  };
}

export function renderStartGate(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const sourceRevision = options.sourceRevision ?? captureSourceRevision(rootDir, options);
  const derived = deriveStartGate({ ...options, rootDir, lookup, sourceRevision });
  const text = JSON.stringify(derived.report);
  return { ...derived, text, lookup, rootDir, sourceRevision };
}

// ---------------------------------------------------------------------------
// validators
// ---------------------------------------------------------------------------

export function validateStartGate(report, env = {}) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(report);
  const exists = env.exists ?? (() => false);
  const sha256 = env.sha256 ?? (() => null);
  const insideRoot = env.insideRoot ?? (() => true);
  const modRegistrations = Array.isArray(env.modRegistrations) ? env.modRegistrations : [];
  const section3Sha = env.section3Sha ?? null;
  const checkpointText = typeof env.checkpointText === "string" ? env.checkpointText : null;

  // 1. text hygiene.
  if ([...text].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the report carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) add("runtime_claim_present", `runtime marker ${marker}`);
  }

  const verdict = report?.admission_verdict;
  if (verdict !== "admission_granted" && verdict !== "admission_absent") {
    add("admission_verdict_mismatch", `admission_verdict=${JSON.stringify(verdict)}`);
  }

  // 2. the v2 binding block and the superseded-receipt guards.
  const binding = report?.binding ?? null;
  if (report?.schema_version !== SCHEMA_VERSION || binding === null) {
    add("v2_source_not_wired", `schema_version=${report?.schema_version} binding=${binding === null ? "absent" : "present"}`);
  } else {
    const cp = binding.checkpoint ?? {};
    const an = binding.answer ?? {};
    const sup = binding.superseded ?? {};
    const v1cp = sup.checkpoint_v1 ?? {};
    const v1an = sup.answer_v1 ?? {};
    if (cp.path !== S02_CHECKPOINT_PATH) {
      add("superseded_source_selected", `bound checkpoint path ${JSON.stringify(cp.path)}`);
    }
    if (an.path !== S02_ANSWER_PATH) {
      add("superseded_source_selected", `bound answer path ${JSON.stringify(an.path)}`);
    }
    if (cp.verdict !== "granted") {
      add("superseded_source_selected", `bound checkpoint verdict ${JSON.stringify(cp.verdict)}`);
    }
    if (an.status !== OWNER_DECISION_RECORDED) {
      add("superseded_ref_accepted", `bound answer status ${JSON.stringify(an.status)}`);
    }
    if (binding.governing?.path !== S02_GOVERNING_PATH || binding.governing?.reread_under !== "v2") {
      add("v2_source_not_wired", `binding.governing=${JSON.stringify(binding.governing)}`);
    }
    if (v1cp.path !== S02_CHECKPOINT_V1_PATH || v1an.path !== S02_ANSWER_V1_PATH) {
      add("v2_source_not_wired", "the superseded binding does not name the v1 S02 artifacts");
    }
    if (v1cp.verdict !== "preserved" || v1an.verdict !== "preserved") {
      add(
        "receipt_silently_rewritten",
        `superseded checkpoint=${v1cp.verdict} answer=${v1an.verdict}`,
      );
    }
    if (report?.superseded_receipts?.checkpoint_v1 !== S02_CHECKPOINT_V1_PATH) {
      add("receipt_silently_rewritten", "the report does not name the preserved v1 checkpoint");
    }
    if (report?.superseded_receipts?.answer_v1 !== S02_ANSWER_V1_PATH) {
      add("receipt_silently_rewritten", "the report does not name the preserved v1 answer record");
    }
    if (normalizePin(v1cp.expected_sha256) === null) {
      add("source_pin_form_rejected", `superseded checkpoint pin ${JSON.stringify(v1cp.expected_sha256)}`);
    }
    if (normalizePin(v1an.expected_sha256) === null) {
      add("source_pin_form_rejected", `superseded answer pin ${JSON.stringify(v1an.expected_sha256)}`);
    }
    const supersededCheckpointPin = normalizePin(v1cp.expected_sha256);
    const supersededAnswerPin = normalizePin(v1an.expected_sha256);
    if (
      (typeof cp.recorded_sha256 === "string" && cp.recorded_sha256 === v1cp.live_sha256) ||
      (typeof cp.recorded_sha256 === "string" && cp.recorded_sha256 === supersededCheckpointPin)
    ) {
      add("superseded_hash_accepted", "the checkpoint binding digest is the superseded v1 digest");
    }
    if (
      (typeof an.recorded_sha256 === "string" && an.recorded_sha256 === v1an.live_sha256) ||
      (typeof an.recorded_sha256 === "string" && an.recorded_sha256 === supersededAnswerPin)
    ) {
      add("superseded_hash_accepted", "the answer binding digest is the superseded v1 digest");
    }
    if (an.supersedes_path !== S02_ANSWER_V1_PATH) {
      add("superseded_ref_accepted", `answer supersedes ${JSON.stringify(an.supersedes_path)}`);
    }
    if (
      supersededAnswerPin !== null &&
      v1an.table_sha256 !== null &&
      normalizePin(v1an.table_sha256) !== supersededAnswerPin
    ) {
      add("superseded_hash_accepted", "the superseded answer pin disagrees with the checkpoint table");
    }
    if (report?.admission_verdict === "admission_granted" && cp.verdict !== "granted") {
      add("admission_verdict_mismatch", "a granted report must carry a granted checkpoint verdict");
    }
    if (report?.admission_verdict === "admission_absent" && cp.verdict === "granted") {
      add("admission_verdict_mismatch", "an absent report must not carry a granted checkpoint verdict");
    }
  }

  if (checkpointText !== null) {
    for (const reject of sourcePinFormRejections(checkpointText)) {
      add("source_pin_form_rejected", `${reject.path}: ${reject.pin}`);
    }
  }
  for (const reject of report?.source_pin_form?.rejected ?? []) {
    add("source_pin_form_rejected", `rejected pin form for ${reject?.path ?? "<unnamed>"}`);
  }

  // 3. byte-bound S02 sources.
  const rows = Array.isArray(report?.s02_sources) ? report.s02_sources : [];
  if (rows.length < MIN_S02_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    const scope = `source ${typeof row?.path === "string" ? row.path : "<unnamed>"}`;
    if (!admissiblePath(row?.path) || !insideRoot(row?.path)) {
      add("source_unresolved", `${scope} is not an admissible repository-relative path`);
      continue;
    }
    if (!exists(row.path)) {
      add("source_unresolved", `${scope} is absent`);
      continue;
    }
    if (typeof row.recorded_sha256 !== "string" || !SHA_PATTERN.test(row.recorded_sha256)) {
      add("source_hash_mismatch", `${scope} recorded_sha256 is malformed`);
      continue;
    }
    const live = sha256(row.path);
    if (live !== row.recorded_sha256) {
      add("source_hash_mismatch", `${scope} live sha256 differs from the recorded digest`);
      continue;
    }
    if (row.live_sha256 !== row.recorded_sha256) {
      add("source_hash_mismatch", `${scope} live_sha256 does not match the recorded digest`);
      continue;
    }
    if (!SOURCE_VERDICTS.includes(row.verdict) || row.verdict !== "match") {
      add("source_hash_mismatch", `${scope} verdict ${JSON.stringify(row.verdict)} is not a bound verdict`);
    }
  }
  const checkpointRow = report?.s02_checkpoint;
  if (!admissiblePath(checkpointRow?.path) || !insideRoot(checkpointRow?.path)) {
    add("source_unresolved", "s02_checkpoint is not an admissible repository-relative path");
  } else if (!exists(checkpointRow.path)) {
    add("source_unresolved", "s02_checkpoint is absent");
  } else {
    const live = sha256(checkpointRow.path);
    if (live !== checkpointRow.recorded_sha256) {
      add("source_hash_mismatch", "s02_checkpoint live sha256 differs from the recorded digest");
    }
  }

  // 4. the tested revision was captured live and is well formed.
  const revision = report?.source_revision;
  if (typeof revision !== "string" || !SOURCE_REVISION_PATTERN.test(revision)) {
    add("source_revision_mismatch", `source_revision=${JSON.stringify(revision)}`);
  } else if (typeof env.sourceRevision === "string" && env.sourceRevision !== revision) {
    add("source_revision_mismatch", "source_revision differs from the live capture");
  }

  // 5. grant provenance, the adoption/execution split and the no-start contour.
  const basis = flat(env.grantBasisText ?? report?.admission_basis);
  const provenance = report?.answer_provenance ?? {};
  if (verdict === "admission_granted") {
    if (provenance.interactive_ref_present !== true) {
      add("grant_without_interactive_ref", `interactive_ref_present=${provenance.interactive_ref_present}`);
    }
    if (!INTERACTIVE_REF_RE.test(String(report?.owner_admission_ref ?? ""))) {
      add("grant_without_interactive_ref", `owner_admission_ref=${JSON.stringify(report?.owner_admission_ref)}`);
    }
    const bindingStatus = binding?.answer?.status ?? null;
    if (provenance.status !== bindingStatus) {
      add(
        "owner_decision_read_as_answered",
        `provenance.status=${JSON.stringify(provenance.status)} binding.answer.status=${JSON.stringify(bindingStatus)}`,
      );
    }
    if (provenance.status !== OWNER_DECISION_RECORDED) {
      add("owner_decision_read_as_answered", `provenance.status=${JSON.stringify(provenance.status)}`);
    }
    const bindingRef = binding?.answer?.ir_criterion_ref ?? null;
    if (bindingRef === null || report?.owner_admission_ref !== bindingRef) {
      add(
        "superseded_ref_accepted",
        `owner_admission_ref=${JSON.stringify(report?.owner_admission_ref)} binding ref=${JSON.stringify(bindingRef)}`,
      );
    }
    if (provenance.ir_criterion_ref !== report?.owner_admission_ref) {
      add(
        "superseded_ref_accepted",
        `provenance.ir_criterion_ref=${JSON.stringify(provenance.ir_criterion_ref)}`,
      );
    }
    if (!AUTHENTICATED_CHANNEL_RE.test(String(binding?.answer?.channel ?? ""))) {
      add("grant_without_interactive_ref", `channel=${JSON.stringify(binding?.answer?.channel)}`);
    }
    if (String(binding?.answer?.disposition ?? "").toLowerCase() !== "accepted") {
      add("grant_without_interactive_ref", `disposition=${JSON.stringify(binding?.answer?.disposition)}`);
    }
    if (
      provenance.governing_surface_reread !== "v2_supersession" ||
      provenance.governing_blocking !== false
    ) {
      add(
        "grant_without_governing_surface",
        `reread=${provenance.governing_surface_reread} blocking=${provenance.governing_blocking}`,
      );
    }
    if (binding?.governing?.answer_record_ref !== S02_ANSWER_V1_PATH) {
      add(
        "grant_without_governing_surface",
        `governing answer_record_ref=${JSON.stringify(binding?.governing?.answer_record_ref)}`,
      );
    }
    if (binding?.governing?.verdict !== "governing_surface_absent") {
      add("grant_without_governing_surface", `governing verdict=${JSON.stringify(binding?.governing?.verdict)}`);
    }
    if (report?.runtime_implementation_permitted !== true) {
      add("admission_verdict_mismatch", "a granted verdict must permit the adopted candidate layer");
    }
    const permitted = Array.isArray(report?.permitted_work) ? report.permitted_work : [];
    if (!permitted.includes(GRANTED_PERMITTED_WORK) || permitted.length !== 1) {
      add("admission_verdict_mismatch", `permitted_work=${JSON.stringify(report?.permitted_work)}`);
    }
    const f13 = flat(report?.f13_status);
    if (f13 === F13_HOLD) {
      add("f13_hold_misread", `f13_status=${JSON.stringify(report?.f13_status)}`);
    } else if (f13 !== F13_DEFERRED_EXPLICIT) {
      add("f13_scope_borrowed", `f13_status=${JSON.stringify(report?.f13_status)}`);
    }
    if (
      report?.adoption_state?.adoption_established !== true ||
      report?.adoption_state?.adopted_variant !== ADOPTED_VARIANT
    ) {
      add(
        "execution_read_as_adoption",
        `adoption_established=${report?.adoption_state?.adoption_established} adopted_variant=${JSON.stringify(
          report?.adoption_state?.adopted_variant,
        )}`,
      );
    }
    if (
      report?.execution_state?.executed !== false ||
      report?.execution_state?.candidates_emitted !== 0
    ) {
      add(
        "adoption_read_as_execution",
        `executed=${report?.execution_state?.executed} candidates_emitted=${report?.execution_state?.candidates_emitted}`,
      );
    }
    if (report?.runtime_stop !== RUNTIME_STOP_LIFTED) {
      add("runtime_stop_blanket_lifted", `runtime_stop=${JSON.stringify(report?.runtime_stop)}`);
    }
    const stopScope = report?.runtime_stop_scope ?? {};
    if (stopScope.lifted_for !== "adopted candidate layer") {
      add("runtime_stop_blanket_lifted", `lifted_for=${JSON.stringify(stopScope.lifted_for)}`);
    }
    const stillActive = Array.isArray(stopScope.still_active_for) ? stopScope.still_active_for : [];
    for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
      if (!stillActive.includes(surface)) {
        add("runtime_stop_blanket_lifted", `still_active_for is missing ${surface}`);
      }
    }
    if (report?.runtime_demo !== RUNTIME_DEMO_NOT_PROVEN) {
      add("runtime_demo_claimed", `runtime_demo=${JSON.stringify(report?.runtime_demo)}`);
    }
    if (report?.runtime_work !== RUNTIME_WORK_NOT_STARTED) {
      add("runtime_demo_claimed", `runtime_work=${JSON.stringify(report?.runtime_work)}`);
    }
    const adopted = Array.isArray(report?.adopted_construct_set) ? report.adopted_construct_set : [];
    for (const construct of adopted) {
      if (EXCLUDED_CONSTRUCT_SET.includes(construct)) {
        add("scope_overclaim", `${construct} is outside the adopted candidate layer`);
      }
    }
    if (report?.adopted_variant_label !== ADOPTED_VARIANT_LABEL) {
      add("scope_overclaim", `adopted_variant_label=${JSON.stringify(report?.adopted_variant_label)}`);
    }
    if (binding?.checkpoint?.scope_bounded_to_variant_c !== true) {
      add("scope_overclaim", "the checkpoint scope is not bounded to variant C");
    }
    if (binding?.checkpoint?.variant_c_found !== true) {
      add("scope_overclaim", "the checkpoint does not name variant C");
    }
    if (binding?.checkpoint?.runtime_stop_scoped !== true) {
      add("runtime_stop_blanket_lifted", "the checkpoint runtime stop is not scoped to the candidate layer");
    }
    if (adopted.length < ADOPTED_CONSTRUCT_SET.length) {
      add("scope_overclaim", "the adopted construct set is narrower than the adopted layer");
    }
    if (
      report?.revision_binding?.checkpoint_matches_answer !== true ||
      report?.revision_binding?.checkpoint_matches_rebind_report !== true
    ) {
      add("source_revision_mismatch", "the grant is not bound to the tested source revision");
    }
    if (binding?.answer?.f13_status !== F13_DEFERRED_EXPLICIT) {
      add("f13_scope_borrowed", `answer f13_status=${JSON.stringify(binding?.answer?.f13_status)}`);
    }
    if (LOCK_RE.test(basis)) add("lock_as_admission", basis);
    if (INTEGRITY_RE.test(basis)) add("integrity_pass_as_admission", basis);
    if (CLOSEOUT_RE.test(basis)) add("milestone_closeout_as_admission", basis);
    if (NON_OWNER_RE.test(basis)) add("non_owner_surface_as_grantor", basis);
  } else if (verdict === "admission_absent") {
    if (report?.runtime_implementation_permitted !== false) {
      add("runtime_permitted_without_admission", `permitted=${report?.runtime_implementation_permitted}`);
    }
    if (report?.runtime_stop !== RUNTIME_STOP_ACTIVE) {
      add("runtime_stop_inverted", `runtime_stop=${report?.runtime_stop}`);
    }
    if (report?.runtime_demo !== RUNTIME_DEMO_NOT_PROVEN) {
      add("runtime_demo_claimed", `runtime_demo=${report?.runtime_demo}`);
    }
    if (!Array.isArray(report?.adopted_construct_set) || report.adopted_construct_set.length !== 0) {
      add("runtime_permitted_without_admission", "adopted_construct_set must stay empty while absent");
    }
    if (report?.adopted_variant !== null) {
      add("runtime_permitted_without_admission", `adopted_variant=${JSON.stringify(report?.adopted_variant)}`);
    }
    if (report?.owner_admission_ref !== "none") {
      add("grant_without_interactive_ref", `owner_admission_ref=${JSON.stringify(report?.owner_admission_ref)}`);
    }
    const permitted = Array.isArray(report?.permitted_work) ? report.permitted_work : [];
    if (!permitted.includes(RUNTIME_PERMITTED_WORK) || permitted.length !== 1) {
      add("no_start_directive_missing", `permitted_work=${JSON.stringify(report?.permitted_work)}`);
    }
    if (flat(report?.f13_status) !== F13_HOLD) {
      add("f13_scope_borrowed", `f13_status=${JSON.stringify(report?.f13_status)}`);
    }
  }

  // 6. declared runtime surfaces must all be absent, and no module may be
  // registered for them.
  const surfaces = Array.isArray(report?.declared_absent_runtime_surfaces)
    ? report.declared_absent_runtime_surfaces
    : [];
  for (const surface of surfaces) {
    if (typeof surface !== "string" || surface === "") {
      add("s03_surface_present", "a declared runtime surface is unnamed");
      continue;
    }
    if (exists(surface)) add("s03_surface_present", `${surface} exists on disk`);
  }
  for (const name of modRegistrations) {
    add("lib_rs_registration_present", `module ${name} is registered`);
  }

  // 7. guards.
  const guards = report?.guards ?? {};
  if (!Array.isArray(guards.crates_touched) || guards.crates_touched.length !== 0) {
    add("crate_touched", JSON.stringify(guards.crates_touched));
  }
  if (guards.requirements_promoted !== 0) {
    add("requirements_promoted", `requirements_promoted=${JSON.stringify(guards.requirements_promoted)}`);
  }
  if (guards.review_case_events_written !== 0) {
    add("review_case_event_written", `review_case_events_written=${JSON.stringify(guards.review_case_events_written)}`);
  }
  if (guards.section3_pin !== SECTION3_PIN) {
    add("section3_mutated", `section3_pin=${JSON.stringify(guards.section3_pin)}`);
  }
  if (typeof section3Sha === "string" && section3Sha !== SECTION3_PIN) {
    add("section3_mutated", `live section 3 digest ${section3Sha} differs from the pin`);
  }

  // 8. out-of-scope surfaces.
  const outOfScope = Array.isArray(report?.out_of_scope_surfaces) ? report.out_of_scope_surfaces : [];
  const names = outOfScope.filter((entry) => entry && typeof entry.name === "string").map((entry) => entry.name);
  if (names.slice().sort().join("|") !== OUT_OF_SCOPE_SURFACES.slice().sort().join("|")) {
    add("out_of_scope_surface_claimed", `declared out-of-scope surfaces are ${JSON.stringify(names)}`);
  }
  for (const entry of outOfScope) {
    if (entry?.claimed === true) add("out_of_scope_surface_claimed", `${entry?.name} is claimed`);
  }

  // 9. --check byte identity.
  if (typeof env.committedText === "string" && env.committedText !== text) {
    add("check_not_byte_identical", "rendered bytes differ from the committed report");
  }

  return { ok: errors.length === 0, verdict: verdict ?? null, errors };
}

export function validateAdmissionCheckpoint(doc, report, env = {}) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });
  const md = typeof doc === "string" ? doc : "";
  const exists = env.exists ?? (() => false);
  const sha256 = env.sha256 ?? (() => null);
  const insideRoot = env.insideRoot ?? (() => true);
  const granted = report?.admission_verdict === "admission_granted";

  // 1. text hygiene.
  if ([...md].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the checkpoint carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (md.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (md.includes(marker)) add("runtime_claim_present", `runtime marker ${marker}`);
  }

  // 2. exactly one verdict line.
  const verdictLines = md.match(VERDICT_ANY_RE) || [];
  const match = md.match(VERDICT_RE);
  const verdict = match ? match[1] : null;
  if (verdictLines.length === 0 || verdict === null) {
    add("verdict_missing", verdictLines.join(" | "));
  }
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));
  const expectedVerdict = granted ? "granted" : "not-adopted";
  if (verdict !== null && verdict !== expectedVerdict) {
    add("admission_verdict_mismatch", `checkpoint=${verdict} report=${report?.admission_verdict}`);
  }

  // 3. mandatory headers and sections.
  for (const key of REQUIRED_HEADERS) {
    const value = headerValue(md, key);
    if (value === null || value.trim() === "") add("header_field_missing", key);
  }
  for (const heading of REQUIRED_SECTIONS) {
    if (!md.split("\n").includes(heading)) add("section_missing", heading);
  }

  // 4. the checkpoint echoes the report. runtime_stop is prose in the checkpoint
  // grammar, so it is compared as a token rather than byte for byte.
  const echoes = [
    ["runtime_demo", report?.runtime_demo, "runtime_demo_claimed"],
    ["section3_pin", report?.guards?.section3_pin, "section3_mutated"],
    ["owner_admission_ref", report?.owner_admission_ref, "grant_without_interactive_ref"],
  ];
  // --print and --write render the live revision, so the snapshot echo in the
  // checkpoint necessarily lags by one write; --check re-renders with the
  // committed revision and is therefore the mode that validates the echo.
  if (env.checkRevisionEcho === true) {
    echoes.unshift(["source_revision", report?.source_revision, "source_revision_mismatch"]);
  }
  for (const [key, expected, code] of echoes) {
    const actual = flat(headerValue(md, key));
    if (actual === "" || actual === null) continue;
    if (typeof expected === "string" && actual !== expected) {
      add(code, `${key}: checkpoint=${actual} report=${expected}`);
    }
  }
  const stopHeader = flat(headerValue(md, "runtime_stop"));
  if (stopHeader !== null) {
    if (granted) {
      if (!/lifted for the adopted candidate-layer scope only/i.test(stopHeader)) {
        add("runtime_stop_blanket_lifted", `checkpoint runtime_stop=${stopHeader}`);
      }
      for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
        if (!stopHeader.includes(surface)) {
          add("runtime_stop_blanket_lifted", `checkpoint runtime_stop omits ${surface}`);
        }
      }
      if (!/(?:stays|remains)\s+active/i.test(stopHeader)) {
        add("runtime_stop_blanket_lifted", `checkpoint runtime_stop does not keep the stop active`);
      }
    } else if (report?.runtime_stop === RUNTIME_STOP_ACTIVE) {
      // The checkpoint grammar records this as prose (`remains active ... this
      // record lifts nothing.`), so the assertion is that the header states the
      // stop is active; a header that claims a lift does not state active.
      if (!/(?:remains|stays|is)\s+active/i.test(stopHeader)) {
        add("runtime_stop_inverted", `checkpoint runtime_stop=${stopHeader}`);
      }
    } else if (report?.runtime_stop === "lifted") {
      if (!/\blift(?:ed|s)\b/i.test(stopHeader)) {
        add("runtime_stop_inverted", `checkpoint runtime_stop=${stopHeader}`);
      }
    }
  }
  const f13Header = flat(headerValue(md, "f13_status"));
  if (granted && f13Header !== null) {
    if (f13Header.startsWith(F13_HOLD)) {
      add("f13_hold_misread", `checkpoint f13_status=${f13Header}`);
    } else if (!f13Header.startsWith(F13_DEFERRED_EXPLICIT)) {
      add("f13_scope_borrowed", `checkpoint f13_status=${f13Header}`);
    }
  }
  if (granted) {
    const adoptedVariant = flat(headerValue(md, "adopted_variant"));
    if (adoptedVariant === null || !/\bC\b/.test(adoptedVariant) || /none/i.test(adoptedVariant)) {
      add("scope_overclaim", `checkpoint adopted_variant=${JSON.stringify(adoptedVariant)}`);
    }
    const adoptedSet = flat(headerValue(md, "adopted_construct_set"));
    for (const token of ADOPTED_CONSTRUCT_SET) {
      if (adoptedSet === null || !adoptedSet.includes(token)) {
        add("scope_overclaim", `checkpoint adopted_construct_set omits ${token}`);
      }
    }
    for (const excluded of EXCLUDED_CONSTRUCT_SET) {
      if (adoptedSet !== null && adoptedSet.includes(excluded)) {
        add("scope_overclaim", `checkpoint adopted_construct_set claims ${excluded}`);
      }
    }
  }
  for (const [key, code] of [
    ["review_case_events_written", "review_case_event_written"],
    ["requirements_promoted", "requirements_promoted"],
  ]) {
    const actual = flat(headerValue(md, key));
    if (actual === "" || actual === null) continue;
    if (actual !== "0") add(code, `${key}: checkpoint=${actual}`);
  }

  // 5. the no-start directive for everything outside the adopted layer.
  const verdictSection = section(md, "## Start gate verdict");
  if (verdictSection === null || !/no-start/i.test(flat(verdictSection))) {
    add("no_start_directive_missing", flat(verdictSection || "").slice(0, 80));
  }

  // 6. byte-bound sources in the checkpoint table, in either digest spelling.
  const rows = admissionSourceRows(md);
  if (rows.length < MIN_MD_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    const scope = `source ${row.path}`;
    if (!admissiblePath(row.path) || !insideRoot(row.path)) {
      add("source_unresolved", `${scope} is not an admissible repository-relative path`);
      continue;
    }
    if (!exists(row.path)) {
      add("source_unresolved", `${scope} is absent`);
      continue;
    }
    if (sha256(row.path) !== row.sha256) add("source_hash_mismatch", scope);
  }
  for (const reject of sourcePinFormRejections(md)) {
    add("source_pin_form_rejected", `${reject.path}: ${reject.pin}`);
  }

  return { ok: errors.length === 0, verdict: verdict ?? null, errors };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

export function liveEnv(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  return {
    text: options.text,
    committedText: options.committedText,
    sourceRevision: options.sourceRevision,
    checkRevisionEcho: options.checkRevisionEcho,
    checkpointText: options.checkpointText,
    section3Sha: lookup.sha256(SECTION3_PATH),
    modRegistrations: options.modRegistrations ?? findModRegistrations(rootDir),
    exists: lookup.exists,
    sha256: lookup.sha256,
    insideRoot: lookup.insideRoot,
  };
}

export function runStartGate(argv = [], options = {}) {
  const mode = argv.includes("--check") ? "check" : argv.includes("--print") ? "print" : "write";
  const rootDir = options.rootDir ?? REPO_ROOT;
  const reportPath = path.join(rootDir, START_GATE_RELATIVE_PATH);
  const committedText = existsSync(reportPath) ? readFileSync(reportPath, "utf8") : null;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const stderr = [];
  const stdout = [];

  let liveRevision;
  try {
    liveRevision = options.sourceRevision ?? captureSourceRevision(rootDir, options);
  } catch (error) {
    const detail = error instanceof StartGateError ? `${error.code}: ${error.detail}` : String(error);
    return { mode, exitCode: 1, stdout: "", stderr: [...stderr, detail], wrote: false };
  }

  // source_revision is a snapshot: the report's own bytes shift the engine
  // aggregate, so --check reuses the committed value for the byte compare and
  // still captures the live revision above to prove the capture path works.
  let renderRevision = liveRevision;
  if (mode === "check" && committedText !== null) {
    try {
      const committed = JSON.parse(committedText);
      if (typeof committed?.source_revision === "string") renderRevision = committed.source_revision;
    } catch {
      renderRevision = liveRevision;
    }
  }

  let rendered;
  try {
    rendered = renderStartGate({
      rootDir,
      lookup,
      sourceRevision: renderRevision,
      checkpointText: options.checkpointText,
      answer: options.answer,
      governing: options.governing,
      binding: options.binding,
      v1CheckpointText: options.v1CheckpointText,
      v1Answer: options.v1Answer,
    });
  } catch (error) {
    const detail = error instanceof StartGateError ? `${error.code}: ${error.detail}` : String(error);
    return { mode, exitCode: 1, stdout: "", stderr: [...stderr, detail], wrote: false };
  }

  const env = liveEnv({
    rootDir,
    lookup,
    text: rendered.text,
    committedText: mode === "check" ? committedText ?? "" : undefined,
    sourceRevision: mode === "write" ? liveRevision : undefined,
    checkRevisionEcho: mode === "check",
    checkpointText: rendered.checkpointText,
  });
  const errors = [...validateStartGate(rendered.report, env).errors];

  const mdPath = path.join(rootDir, ADMISSION_RELATIVE_PATH);
  const mdText = existsSync(mdPath) ? readFileSync(mdPath, "utf8") : null;
  if (mdText === null) {
    stderr.push(MD_ABSENT_NOTE);
  } else {
    errors.push(...validateAdmissionCheckpoint(mdText, rendered.report, env).errors);
  }

  if (errors.length > 0) {
    for (const error of errors) stderr.push(`${error.name}: ${error.detail}`);
    return {
      mode,
      exitCode: 1,
      stdout: "",
      stderr,
      wrote: false,
      report: rendered.report,
      text: rendered.text,
      errors,
    };
  }

  if (mode === "print") {
    stdout.push(rendered.text);
    stderr.push(PRINT_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }
  if (mode === "check") {
    if (committedText === null) {
      return {
        mode,
        exitCode: 1,
        stdout: "",
        stderr: [...stderr, "check_not_byte_identical: the committed report is absent"],
        wrote: false,
      };
    }
    stdout.push(CHECK_OK_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }
  if (!options.dryRun) writeFileSync(reportPath, rendered.text);
  stdout.push(WRITTEN_MARKER);
  return {
    mode,
    exitCode: 0,
    stdout,
    stderr,
    wrote: !options.dryRun,
    report: rendered.report,
    text: rendered.text,
  };
}

export function main(argv = process.argv.slice(2)) {
  const result = runStartGate(argv);
  for (const line of result.stderr) process.stderr.write(`${line}\n`);
  for (const line of result.stdout) process.stdout.write(`${line}\n`);
  process.exitCode = result.exitCode;
  return result;
}

const invokedDirectly =
  typeof process.argv[1] === "string" &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  main();
}
