#!/usr/bin/env node
// M210-3afp79 S04 T01 -- admission reconciliation for RC28-F18.
//
// WHY THIS FILE EXISTS
// An earlier S04 draft declared `selected_for_s04=strict_record_based` and
// `admission_state=not-established`, denying the bounded variant C adoption. That
// reading is stale: commit 2f67de0 records an authenticated bounded adoption of
// variant C in the superseding S02 v2 checkpoint (`admission: granted`, criterion
// 37181c25-88b0-4896-bffe-d10642970e6f) and in the v2 answer record
// (`status: owner_decision_recorded`, `f13_status: deferred-explicit`). This
// generator reconciles the supersession chain truthfully and emits one canonical
// ASCII JSON so every downstream S04 artifact derives from a single source.
//
// IT DERIVES, IT DOES NOT INVENT
//   * supersession_chain -- the v1 checkpoint and v1 answer record that the v2
//     records supersede, each re-hashed live and each bound to the digest the v2
//     source records. The v1 bytes are preserved; nothing is rewritten behind them.
//   * readings[] -- the two honest readings. The v1 reading (strict_record_based /
//     not-established) is accurate for the superseded v1 state and is retained as
//     history; the v2 reading (authenticated_bounded_adoption /
//     established-bounded-candidate-layer) is accurate for the current state and is
//     the one selected. Neither reading is a lie; only one of them is current.
//   * three separated states -- adoption (established), technical gate/activation
//     (the candidate layer is permitted by the grant, but not-activated: nothing is
//     implemented), and review_case submission (the actor-bound path is unavailable
//     and its scope is record_human_disposition, never the subjective-UAT channel).
//   * f18 -- bounded adoption evidence is present (the v2 references); independent
//     evaluation and ledger disposition are separately and still pending, and
//     auto-close is forbidden.
//   * consumed_by_s03_gate -- the S03 start gate originally read the superseded v1
//     source; that reading is registered here as historical and fixed in S03/T01,
//     and the S03 gate artifact is never rewritten by this record.
//
// NOT ADOPTION AGAIN, NOT EXECUTION
//   No repeat owner decision is required or requested. Adoption is not activation
//   (the candidate layer is permitted, not built) and it is not submission
//   authority (the actor-bound path stays unavailable for record_human_disposition).
//
// SOURCE REVISION IS A SNAPSHOT, NOT A LIVE INVARIANT
//   The engine aggregate hash covers tracked content plus untracked non-ignored
//   files (`git ls-files --cached --others --exclude-standard`), so writing this
//   report shifts the aggregate. The stored value is the revision captured at
//   render time, before this report existed; it is not a live invariant. `--check`
//   re-renders with the committed revision for the byte compare while still
//   capturing the live revision to prove the capture path.
//
// USAGE
//   node scripts/m210_s04_admission_reconcile.mjs --write   # default
//   node scripts/m210_s04_admission_reconcile.mjs --check
//   node scripts/m210_s04_admission_reconcile.mjs --print

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const RECONCILIATION_RELATIVE_PATH = "prd/architecture/m210-s04-admission-reconciliation.json";
export const ADMISSION_RELATIVE_PATH = "prd/architecture/m210-s04-runtime-admission.md";

// The authoritative (live) S02 sources this reconciliation binds.
export const S02_CHECKPOINT_V2_PATH = "prd/architecture/m210-s02-adoption-checkpoint-v2.md";
export const S02_ANSWER_V2_PATH = "prd/architecture/m210-s02-answer-record-v2.json";
export const S02_GOVERNING_PATH = "prd/architecture/m210-s02-governing-surface-check.json";
// The superseded (historical) S02 sources; their bytes must survive untouched.
export const S02_CHECKPOINT_V1_PATH = "prd/architecture/m210-s02-adoption-checkpoint.md";
export const S02_ANSWER_V1_PATH = "prd/architecture/m210-s02-answer-record.json";
// The S03 gate that originally read the superseded v1 checkpoint, fixed in S03/T01.
export const S03_START_GATE_PATH = "prd/architecture/m210-s03-start-gate.json";
export const S03_ADMISSION_PATH = "prd/architecture/m210-s03-runtime-admission.md";
export const SECTION3_PATH = "prd/temporal-legal-model.md";
export const SOURCE_REVISION_SCRIPT = "scripts/m204_s08_source_revision.mjs";
export const CONTRACT_PATH = "scripts/m210_s04_admission_contract.test.mjs";

export const SCHEMA = "law-nexus/m210-s04-admission-reconciliation/v1";
export const SCHEMA_VERSION = 1;
export const KIND = "m210-s04-admission-reconciliation";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S04";
export const TASK = "T01";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "RC28-F19", "R074"];

// The recorded pin of prd/temporal-legal-model.md section 3. It is a target-file
// pin, not the aggregate source revision, and it is the only 64-hex literal this
// generator may carry.
export const SECTION3_PIN =
  "sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6";

export const ADMISSION = "granted";
export const SELECTED_FOR_S04 = "authenticated_bounded_adoption";
export const ADMISSION_STATE = "established-bounded-candidate-layer";
export const ACTIVATION_STATE = "not-activated";
export const CONSUMED_BY_S03_GATE = "gate_reads_superseded_checkpoint";
export const F13_DEFERRED_EXPLICIT = "deferred-explicit";
export const F13_MISSING = "missing";
export const F13_HOLD = "hold";

export const ADOPTED_VARIANT = "C";
export const ADOPTED_VARIANT_LABEL = "abstention_first_candidates_only";
export const RUNTIME_STOP_STATE = "lifted_candidate_layer_only";
export const RUNTIME_STOP_LIFTED_FOR = "adopted candidate layer";
export const RUNTIME_STOP_STILL_ACTIVE = [
  "composed-rule runtime",
  "applicability runtime",
  "section 3 promotion",
];
export const EXCLUDED_CONSTRUCT_SET = [
  "rule_composition",
  "precedence_resolution",
  "facet_defaults",
  "case_applicability",
];

export const OWNER_CRITERION = "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f";
export const OWNER_CRITERION_ID = "37181c25-88b0-4896-bffe-d10642970e6f";
export const OWNER_QUESTION_ID = "57ef54f3-aa0a-4e5e-82a7-b4dc7057e25c";
export const OWNER_INTERACTION_ID = "456709c8-4da5-4835-a0fe-7a2af3a45e64";
export const F13_CRITERION_ID = "70e39300-851b-4412-a322-a8f0c51ca71c";
export const AUTHENTICATED_CHANNEL = "authenticated subjective-UAT";
export const OWNER_DECISION_RECORDED = "owner_decision_recorded";
export const DISPOSITION_ACCEPTED = "accepted";
export const ACTOR_BOUND_SCOPE = "record_human_disposition";

export const V1_SELECTED_FOR_S04 = "strict_record_based";
export const V1_ADMISSION_STATE = "not-established";
export const V1_ADMISSION = "not-adopted";
export const V1_ANSWER_STATUS = "pending_human_decision";

// The surfaces the adopted candidate layer would later create. They are declared,
// not created: this slice is design/evidence-only, so every one must stay absent.
export const DECLARED_ABSENT_RUNTIME_SURFACES = [
  "crates/ln-temporal/src/normative_candidate.rs",
  "crates/ln-temporal/src/bounded_semantics.rs",
  "crates/ln-temporal/tests/normative_candidate_contract.rs",
  "crates/ln-decode/src/candidate_emission.rs",
  "scripts/m210_s03_verify.sh",
];

export const OUT_OF_SCOPE_SURFACES = [
  "rule composition",
  "precedence resolution",
  "facet defaults",
  "case applicability",
  "section 3 promotion",
  "F13 operation grammar",
  "ln-applicability NormRule",
  "RuVector",
  "TEI",
];

export const REQUIRED_HEADERS = [
  "recorded",
  "milestone / slice",
  "classification",
  "scope",
  "source_revision",
  "owner_admission_ref",
  "admission_basis",
  "selection",
  "admission_state",
  "activation_state",
  "submission_gate",
  "runtime_stop",
  "f13_status",
  "review_case_events_written",
  "requirements_promoted",
  "section3_pin",
  "contract",
];

export const REQUIRED_SECTIONS = [
  "## Purpose and boundary",
  "## Supersession chain",
  "## Governing surface",
  "## Owner choices not required",
  "## Non-claims",
  "## Fail-closed boundary",
  "## Resume condition",
];

export const EMITTABLE_CODES = [
  "supersession_chain_broken",
  "chain_hash_mismatch",
  "gate_reads_superseded_checkpoint",
  "owner_reacceptance_demanded",
  "adoption_denied_despite_v2",
  "actor_bound_scope_confused",
  "governing_surface_v1_stale_read",
  "adoption_read_as_activation",
  "adoption_read_as_submission_authority",
  "f13_missing_answer_misread",
  "review_case_event_written",
  "section3_mutated",
  "requirement_promoted",
  "crate_touched",
  "non_ascii_artifact",
  "raw_text_leak",
  "check_not_byte_identical",
  "runtime_stop_blanket_lifted",
  "verdict_missing",
  "verdict_ambiguous",
  "header_field_missing",
  "section_missing",
];

export const WRITTEN_MARKER = "M210_S04_ADMISSION_WRITTEN";
export const CHECK_OK_MARKER = "M210_S04_ADMISSION_CHECK_OK";
export const PRINT_MARKER = "M210_S04_ADMISSION_PRINTED";
export const MD_ABSENT_NOTE = "M210_S04_ADMISSION_MD_ABSENT";
export const CONTRACT_MARKER = "M210_S04_ADMISSION_OK";

export const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const SOURCE_REVISION_PATTERN = /^sha256:[0-9a-f]{64}$/;
export const VERDICT_RE = /^\*\*admission: (granted|not-adopted)\*\*$/m;
export const VERDICT_ANY_RE = /^\*\*admission: .*\*\*$/gm;

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];
const TABLE_ROW_SKIP_PATH = new Set(["Source", "source", "Path", "path"]);

const NON_CLAIMS = [
  "This reconciliation is a record, not a grant, not an approval, not a waiver, not a requirement closure, not a Review Case disposition, not a legal conclusion and not a lifecycle promotion.",
  "Variant C is established as a bounded adoption only: the candidate layer is adopted and permitted; composition, precedence resolution, facet defaults, case applicability and any section 3 promotion stay outside the adopted scope and unavailable.",
  "No repeat owner decision is required or requested: the authenticated bounded adoption already exists in the superseding S02 v2 sources and this record never demands re-acceptance.",
  "Adoption is not activation: the candidate layer is permitted by the grant but nothing is implemented, so activation_state stays not-activated and zero runtime surfaces exist.",
  "Adoption is not submission authority: the actor-bound path stays unavailable and its scope is record_human_disposition, never the authenticated subjective-UAT channel.",
  "F13 is an explicit owner defer (deferred-explicit), not a missing answer and not a hold.",
  "F18 carries bounded adoption evidence (the v2 references); its independent evaluation and its ledger disposition are separate, still pending, and auto-close is forbidden.",
  "The superseded v1 S02 checkpoint and the v1 S02 answer record stay byte-identical and hash-bound as history; the S03 gate read of the superseded v1 source is registered as historical and fixed in S03/T01, and no S02 or S03 artifact is rewritten here.",
  "No Review Case event is written and no requirement is promoted by this record.",
];

export class AdmissionError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "AdmissionError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new AdmissionError(code, detail);
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
// counts, which would look green. Strip it for every spawn.
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

function readJson(rootDir, relativePath) {
  try {
    return JSON.parse(readText(rootDir, relativePath));
  } catch (error) {
    if (error instanceof AdmissionError) throw error;
    fail("source_unresolved", `${relativePath} is not JSON: ${String(error?.message || error)}`);
  }
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

// The heading itself may contain a word the body assertion also looks for (for
// example "## Owner choices not required"), so prose assertions are made against
// the body only, never against the heading line.
export function sectionBody(doc, heading) {
  const full = section(doc, heading);
  if (full === null) return null;
  return full.split("\n").slice(1).join("\n");
}

export function normalizePin(value) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (/^[0-9a-f]{64}$/.test(trimmed)) return `sha256:${trimmed}`;
  if (/^sha256:[0-9a-f]{64}$/.test(trimmed)) return trimmed;
  return null;
}

export function isAuthenticatedChannel(value) {
  return typeof value === "string" && value === AUTHENTICATED_CHANNEL;
}

// Parse every two-column source row of a markdown table, accepting both digest
// spellings. A digest-shaped cell that is not a valid pin is dropped here; the
// reconciliation only needs the v1 pin from the v2 checkpoint table.
export function parseSourceTable(doc) {
  const rows = [];
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
    if (normalized === null) continue;
    rows.push({ path: rawPath.replace(/\s+\([^)]*\)$/, ""), sha256: normalized });
  }
  return rows;
}

export function tablePinFor(doc, relativePath) {
  const row = parseSourceTable(doc).find((entry) => entry.path === relativePath);
  return row ? row.sha256 : null;
}

export function declaredModuleNames(surfaces = DECLARED_ABSENT_RUNTIME_SURFACES) {
  const names = new Map();
  for (const surface of surfaces) {
    const match = /^crates\/([^/]+)\/src\/([^/]+)\.rs$/.exec(surface);
    if (match) names.set(match[2], `crates/${match[1]}/src/lib.rs`);
  }
  return [...names.entries()].map(([name, lib]) => ({ name, lib }));
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
// derivation
// ---------------------------------------------------------------------------

export function deriveReconciliation(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const v2CheckpointText =
    options.v2CheckpointText ?? readText(rootDir, S02_CHECKPOINT_V2_PATH);
  const v2Answer = options.v2Answer ?? readJson(rootDir, S02_ANSWER_V2_PATH);
  const v1CheckpointText =
    options.v1CheckpointText ?? readText(rootDir, S02_CHECKPOINT_V1_PATH);
  const v1Answer = options.v1Answer ?? readJson(rootDir, S02_ANSWER_V1_PATH);
  const governing = options.governing ?? readJson(rootDir, S02_GOVERNING_PATH);
  const s03Gate = options.s03Gate ?? readJson(rootDir, S03_START_GATE_PATH);
  const sourceRevision = options.sourceRevision;
  if (!SOURCE_REVISION_PATTERN.test(String(sourceRevision))) {
    fail("source_revision_mismatch", `source revision ${sourceRevision} is not sha256:<64hex>`);
  }

  const v1CheckpointSha = lookup.sha256(S02_CHECKPOINT_V1_PATH);
  const v1CheckpointPinFromV2 = tablePinFor(v2CheckpointText, S02_CHECKPOINT_V1_PATH);
  const v2CheckpointSha = lookup.sha256(S02_CHECKPOINT_V2_PATH);
  const v1AnswerSha = lookup.sha256(S02_ANSWER_V1_PATH);
  const v2AnswerSha = lookup.sha256(S02_ANSWER_V2_PATH);
  const governingSha = lookup.sha256(S02_GOVERNING_PATH);
  const s03GateSha = lookup.sha256(S03_START_GATE_PATH);

  const v2AnswerSupersedesPin = normalizePin(v2Answer?.supersedes?.sha256);
  const ir = v2Answer?.interactive_refs?.ir ?? {};
  const f13 = v2Answer?.interactive_refs?.f13 ?? {};

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
    admission: ADMISSION,
    admission_basis:
      "granted is derived from the superseding S02 v2 sources: the v2 checkpoint carries exactly one verdict line reading granted for the bounded candidate layer of variant C, the v2 answer record status is owner_decision_recorded with an authenticated interactive source and an accepted disposition, and the superseded v1 checkpoint and v1 answer record stay byte-identical and hash-bound.",
    selected_for_s04: SELECTED_FOR_S04,
    admission_state: ADMISSION_STATE,
    activation_state: ACTIVATION_STATE,
    scope: {
      adopted_variant: ADOPTED_VARIANT,
      adopted_variant_label: ADOPTED_VARIANT_LABEL,
      bounded_to_candidate_layer: true,
      excluded: EXCLUDED_CONSTRUCT_SET,
    },
    owner_admission_ref: OWNER_CRITERION,
    owner_admission_refs: {
      criterion_id: OWNER_CRITERION_ID,
      question_id: OWNER_QUESTION_ID,
      interaction_id: OWNER_INTERACTION_ID,
      f13_criterion_id: F13_CRITERION_ID,
      channel: typeof ir.channel === "string" ? ir.channel : null,
      disposition: typeof ir.disposition === "string" ? ir.disposition : null,
      answer_record: S02_ANSWER_V2_PATH,
      answer_record_sha256: v2AnswerSha,
      f13_channel: typeof f13.channel === "string" ? f13.channel : null,
      f13_disposition: typeof f13.disposition === "string" ? f13.disposition : null,
    },
    owner_choices: {
      reacceptance_required: false,
      repeat_owner_decision_requested: false,
      note:
        "the authenticated bounded adoption already exists in the v2 sources; a further owner decision is neither required nor requested here",
    },
    supersession_chain: {
      policy:
        "append-or-supersede: the superseded v1 bytes stay byte-identical; this reconciliation rewrites nothing behind them",
      v1: {
        path: S02_CHECKPOINT_V1_PATH,
        admission: V1_ADMISSION,
        status: "superseded",
        verdict_applies_to: "v1",
        sha256: v1CheckpointSha,
        sha256_from_v2_table: v1CheckpointPinFromV2,
      },
      v2: {
        path: S02_CHECKPOINT_V2_PATH,
        admission: ADMISSION,
        status: "current",
        verdict_applies_to: "v2",
        supersedes: S02_CHECKPOINT_V1_PATH,
        sha256: v2CheckpointSha,
      },
      answer_v1: {
        path: S02_ANSWER_V1_PATH,
        status: V1_ANSWER_STATUS,
        sha256: v1AnswerSha,
        sha256_from_v2_binding: v2AnswerSupersedesPin,
      },
      answer_v2: {
        path: S02_ANSWER_V2_PATH,
        status: typeof v2Answer?.status === "string" ? v2Answer.status : null,
        sha256: v2AnswerSha,
      },
    },
    readings: [
      {
        reading_id: "v1_superseded",
        source: S02_CHECKPOINT_V1_PATH,
        selected_for_s04: V1_SELECTED_FOR_S04,
        admission_state: V1_ADMISSION_STATE,
        admission: V1_ADMISSION,
        status: "superseded",
        verdict_applies_to: "v1",
        honest: true,
        selected: false,
        note:
          "accurate for the superseded v1 state, in which no authenticated interactive answer existed; retained as history and never presented as current",
      },
      {
        reading_id: "v2_current",
        source: S02_CHECKPOINT_V2_PATH,
        selected_for_s04: SELECTED_FOR_S04,
        admission_state: ADMISSION_STATE,
        admission: ADMISSION,
        status: "current",
        verdict_applies_to: "v2",
        honest: true,
        selected: true,
        note:
          "accurate for the current v2 state: the owner recorded an authenticated bounded adoption of variant C",
      },
    ],
    governing_surface: {
      path: S02_GOVERNING_PATH,
      sha256: governingSha,
      verdict: typeof governing?.verdict === "string" ? governing.verdict : null,
      verdict_applies_to: "v1",
      blocking: false,
      actor_bound_path_available: governing?.actor_bound_path_available ?? null,
      actor_bound_scope: ACTOR_BOUND_SCOPE,
      subjective_uat_channel: AUTHENTICATED_CHANNEL,
    },
    submission_gate: {
      applied: false,
      actor_bound_path_available: false,
      scope: ACTOR_BOUND_SCOPE,
      subjective_uat_is_submission_path: false,
      authority: "none",
      note:
        "actor_bound_path_available=false is a current limitation of record_human_disposition submission, not a sign that bounded adoption of variant C is absent; the subjective-UAT channel is authenticated and already used in S02 but it is not a submission path and is never substituted for one",
    },
    runtime_stop: {
      state: RUNTIME_STOP_STATE,
      lifted_for: RUNTIME_STOP_LIFTED_FOR,
      still_active_for: RUNTIME_STOP_STILL_ACTIVE,
    },
    f13_status: F13_DEFERRED_EXPLICIT,
    f13_criterion_id: F13_CRITERION_ID,
    f18: {
      bounded_adoption_evidence_present: true,
      evidence_refs: [S02_CHECKPOINT_V2_PATH, S02_ANSWER_V2_PATH, OWNER_CRITERION],
      independent_evaluation: "pending",
      ledger_disposition: "pending",
      auto_close: "forbidden",
    },
    consumed_by_s03_gate: CONSUMED_BY_S03_GATE,
    s03_gate: {
      path: S03_START_GATE_PATH,
      sha256: s03GateSha,
      admission: typeof s03Gate?.admission_verdict === "string" ? s03Gate.admission_verdict : null,
      reads_superseded_checkpoint: true,
      fixed_in: "S03/T01",
      rewritten: false,
      current_reading: "v2",
      note:
        "the S03 start gate initially consumed the superseded v1 checkpoint reading; that reading is registered here as historical and fixed in S03/T01, and the S03 gate artifact is not rewritten by this record",
    },
    declared_absent_runtime_surfaces: DECLARED_ABSENT_RUNTIME_SURFACES,
    out_of_scope_surfaces: OUT_OF_SCOPE_SURFACES.map((name) => ({ name, claimed: false })),
    guards: {
      crates_touched: [],
      requirements_promoted: 0,
      review_case_events_written: 0,
      section3_pin: SECTION3_PIN,
    },
    source_revision: sourceRevision,
    fail_closed_codes: EMITTABLE_CODES,
    non_claims: NON_CLAIMS,
  };

  return { report, v2CheckpointText, v1CheckpointText, v2Answer, v1Answer, governing, s03Gate };
}

export function renderReconciliation(options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const sourceRevision = options.sourceRevision ?? captureSourceRevision(rootDir, options);
  const derived = deriveReconciliation({ ...options, rootDir, lookup, sourceRevision });
  const text = JSON.stringify(derived.report);
  return { ...derived, text, lookup, rootDir, sourceRevision };
}

// ---------------------------------------------------------------------------
// validators
// ---------------------------------------------------------------------------

function textHygiene(text, add) {
  if ([...text].some((character) => character.charCodeAt(0) > 0x7f)) {
    add("non_ascii_artifact", "the artifact carries a non-ASCII byte");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) add("raw_text_leak", `text marker ${marker}`);
  }
}

export function validateReconciliation(report, env = {}) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(report);
  const exists = env.exists ?? (() => false);
  const sha256 = env.sha256 ?? (() => null);
  const insideRoot = env.insideRoot ?? (() => true);
  const section3Sha = env.section3Sha ?? null;

  // 1. text hygiene and runtime-footprint hygiene.
  textHygiene(text, add);
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) add("crate_touched", `runtime marker ${marker}`);
  }

  const chain = report?.supersession_chain ?? null;
  const readings = Array.isArray(report?.readings) ? report.readings : [];

  // 2. the supersession chain is intact and names exactly two honest readings.
  if (chain === null) {
    add("supersession_chain_broken", "the supersession chain is absent");
  } else {
    const v1 = chain.v1 ?? {};
    const v2 = chain.v2 ?? {};
    if (v1.path !== S02_CHECKPOINT_V1_PATH || v2.path !== S02_CHECKPOINT_V2_PATH) {
      add("supersession_chain_broken", "the chain does not name the v1 and v2 checkpoints");
    }
    if (v2.supersedes !== S02_CHECKPOINT_V1_PATH) {
      add("supersession_chain_broken", `v2.supersedes=${JSON.stringify(v2.supersedes)}`);
    }
    if (v1.status !== "superseded" || v2.status !== "current") {
      add("supersession_chain_broken", `v1.status=${v1.status} v2.status=${v2.status}`);
    }
    if (v1.admission !== V1_ADMISSION || v2.admission !== ADMISSION) {
      add("supersession_chain_broken", `v1.admission=${v1.admission} v2.admission=${v2.admission}`);
    }
    if (chain.answer_v1?.path !== S02_ANSWER_V1_PATH || chain.answer_v2?.path !== S02_ANSWER_V2_PATH) {
      add("supersession_chain_broken", "the chain does not name the v1 and v2 answer records");
    }
    if (
      chain.answer_v2?.status !== OWNER_DECISION_RECORDED ||
      chain.answer_v1?.status !== V1_ANSWER_STATUS
    ) {
      add(
        "supersession_chain_broken",
        `answer_v1.status=${chain.answer_v1?.status} answer_v2.status=${chain.answer_v2?.status}`,
      );
    }
  }

  if (readings.length !== 2) {
    add("supersession_chain_broken", `the reconciliation must carry exactly two readings and carries ${readings.length}`);
  }
  const selected = readings.filter((entry) => entry?.selected === true);
  const unselected = readings.filter((entry) => entry?.selected !== true);
  if (selected.length !== 1) {
    add("supersession_chain_broken", `exactly one reading must be selected and ${selected.length} are`);
  }
  if (unselected.length !== 1) {
    add("supersession_chain_broken", `exactly one reading must stay unselected and ${unselected.length} do`);
  }
  for (const entry of readings) {
    if (entry?.honest !== true) {
      add("supersession_chain_broken", `reading ${entry?.reading_id} is not marked honest`);
    }
  }
  const currentReading = selected[0] ?? null;
  if (
    currentReading === null ||
    currentReading.source !== S02_CHECKPOINT_V2_PATH ||
    currentReading.selected_for_s04 !== SELECTED_FOR_S04 ||
    currentReading.admission_state !== ADMISSION_STATE
  ) {
    add("supersession_chain_broken", `the selected reading is ${JSON.stringify(currentReading)}`);
  }
  const supersededReading = unselected[0] ?? null;
  if (
    supersededReading === null ||
    supersededReading.source !== S02_CHECKPOINT_V1_PATH ||
    supersededReading.status !== "superseded" ||
    supersededReading.verdict_applies_to !== "v1" ||
    supersededReading.selected_for_s04 !== V1_SELECTED_FOR_S04 ||
    supersededReading.admission_state !== V1_ADMISSION_STATE
  ) {
    add("supersession_chain_broken", `the superseded reading is ${JSON.stringify(supersededReading)}`);
  }

  // 3. every chain digest is a well-formed pin and matches live bytes plus the
  // digest the v2 source recorded.
  const chainDigests = [
    [chain?.v1, S02_CHECKPOINT_V1_PATH, "v1 checkpoint"],
    [chain?.v2, S02_CHECKPOINT_V2_PATH, "v2 checkpoint"],
    [chain?.answer_v1, S02_ANSWER_V1_PATH, "v1 answer record"],
    [chain?.answer_v2, S02_ANSWER_V2_PATH, "v2 answer record"],
  ];
  for (const [entry, relativePath, scope] of chainDigests) {
    if (entry === null || entry === undefined) {
      add("chain_hash_mismatch", `${scope} is absent from the chain`);
      continue;
    }
    const pin = normalizePin(entry.sha256);
    if (pin === null) {
      add("chain_hash_mismatch", `${scope} recorded sha256 is malformed`);
      continue;
    }
    if (!admissiblePath(relativePath) || !insideRoot(relativePath)) {
      add("chain_hash_mismatch", `${scope} is not an admissible repository-relative path`);
      continue;
    }
    const live = sha256(relativePath);
    if (live !== pin) add("chain_hash_mismatch", `${scope} live sha256 differs from the recorded digest`);
  }
  if (chain?.v1 !== undefined) {
    if (normalizePin(chain?.v1?.sha256_from_v2_table) !== normalizePin(chain?.v1?.sha256)) {
      add("chain_hash_mismatch", "the v1 checkpoint pin disagrees with the pin recorded in the v2 source table");
    }
  }
  if (chain?.answer_v1 !== undefined) {
    if (normalizePin(chain?.answer_v1?.sha256_from_v2_binding) !== normalizePin(chain?.answer_v1?.sha256)) {
      add("chain_hash_mismatch", "the v1 answer pin disagrees with the supersedes binding in the v2 answer record");
    }
  }

  // 4. the S03 gate's superseded read is registered as historical, not rewritten.
  const s03Gate = report?.s03_gate ?? {};
  if (
    report?.consumed_by_s03_gate !== CONSUMED_BY_S03_GATE ||
    s03Gate.reads_superseded_checkpoint !== true ||
    s03Gate.fixed_in !== "S03/T01" ||
    s03Gate.rewritten !== false ||
    s03Gate.current_reading !== "v2"
  ) {
    add(
      "gate_reads_superseded_checkpoint",
      `consumed_by_s03_gate=${JSON.stringify(report?.consumed_by_s03_gate)} fixed_in=${JSON.stringify(
        s03Gate.fixed_in,
      )} rewritten=${JSON.stringify(s03Gate.rewritten)}`,
    );
  }

  // 5. no repeat owner acceptance is demanded.
  const ownerChoices = report?.owner_choices ?? {};
  if (
    ownerChoices.reacceptance_required !== false ||
    ownerChoices.repeat_owner_decision_requested !== false
  ) {
    add("owner_reacceptance_demanded", JSON.stringify(ownerChoices));
  }

  // 6. the admission is established as a bounded variant C adoption.
  if (
    report?.admission !== ADMISSION ||
    report?.admission_state !== ADMISSION_STATE ||
    report?.selected_for_s04 !== SELECTED_FOR_S04 ||
    report?.scope?.adopted_variant !== ADOPTED_VARIANT ||
    chain?.v2?.admission !== ADMISSION
  ) {
    add(
      "adoption_denied_despite_v2",
      `admission=${JSON.stringify(report?.admission)} admission_state=${JSON.stringify(
        report?.admission_state,
      )} selected_for_s04=${JSON.stringify(report?.selected_for_s04)}`,
    );
  }

  // 7. the three states are separated: gate/activation, and submission authority.
  const submissionGate = report?.submission_gate ?? {};
  if (
    submissionGate.scope !== ACTOR_BOUND_SCOPE ||
    submissionGate.subjective_uat_is_submission_path !== false ||
    report?.governing_surface?.actor_bound_scope !== ACTOR_BOUND_SCOPE
  ) {
    add(
      "actor_bound_scope_confused",
      `submission scope=${JSON.stringify(submissionGate.scope)} subjective_uat_is_submission_path=${JSON.stringify(
        submissionGate.subjective_uat_is_submission_path,
      )}`,
    );
  }
  if (
    submissionGate.actor_bound_path_available !== false ||
    submissionGate.authority !== "none" ||
    submissionGate.applied !== false
  ) {
    add(
      "adoption_read_as_submission_authority",
      `actor_bound_path_available=${JSON.stringify(
        submissionGate.actor_bound_path_available,
      )} authority=${JSON.stringify(submissionGate.authority)}`,
    );
  }
  if (report?.activation_state !== ACTIVATION_STATE) {
    add("adoption_read_as_activation", `activation_state=${JSON.stringify(report?.activation_state)}`);
  }

  // 8. the v1 governing-surface finding is read as v1-scoped and non-blocking.
  const governing = report?.governing_surface ?? {};
  if (
    governing.verdict !== "governing_surface_absent" ||
    governing.verdict_applies_to !== "v1" ||
    governing.blocking !== false
  ) {
    add(
      "governing_surface_v1_stale_read",
      `verdict=${JSON.stringify(governing.verdict)} applies_to=${JSON.stringify(
        governing.verdict_applies_to,
      )} blocking=${JSON.stringify(governing.blocking)}`,
    );
  }

  // 9. F13 is an explicit owner defer, never a missing answer or a hold.
  const f13 = flat(report?.f13_status);
  if (f13 !== F13_DEFERRED_EXPLICIT) {
    add("f13_missing_answer_misread", `f13_status=${JSON.stringify(report?.f13_status)}`);
  }

  // 10. the runtime stop is lifted for the candidate layer only.
  const stop = report?.runtime_stop ?? {};
  const stillActive = Array.isArray(stop.still_active_for) ? stop.still_active_for : [];
  if (
    stop.state !== RUNTIME_STOP_STATE ||
    stop.lifted_for !== RUNTIME_STOP_LIFTED_FOR ||
    RUNTIME_STOP_STILL_ACTIVE.some((surface) => !stillActive.includes(surface))
  ) {
    add("runtime_stop_blanket_lifted", JSON.stringify(stop));
  }

  // 11. product footprint guards.
  const guards = report?.guards ?? {};
  if (!Array.isArray(guards.crates_touched) || guards.crates_touched.length !== 0) {
    add("crate_touched", JSON.stringify(guards.crates_touched));
  }
  const surfaces = Array.isArray(report?.declared_absent_runtime_surfaces)
    ? report.declared_absent_runtime_surfaces
    : [];
  for (const surface of surfaces) {
    if (typeof surface !== "string" || surface === "") {
      add("crate_touched", "a declared runtime surface is unnamed");
      continue;
    }
    if (exists(surface)) add("crate_touched", `${surface} exists on disk`);
  }
  if (guards.requirements_promoted !== 0) {
    add("requirement_promoted", `requirements_promoted=${JSON.stringify(guards.requirements_promoted)}`);
  }
  if (guards.review_case_events_written !== 0 || env.eventsDirExists === true) {
    add(
      "review_case_event_written",
      `review_case_events_written=${JSON.stringify(guards.review_case_events_written)}`,
    );
  }
  if (guards.section3_pin !== SECTION3_PIN) {
    add("section3_mutated", `section3_pin=${JSON.stringify(guards.section3_pin)}`);
  }
  if (typeof section3Sha === "string" && section3Sha !== SECTION3_PIN) {
    add("section3_mutated", `live section 3 digest ${section3Sha} differs from the pin`);
  }

  // 12. --check byte identity.
  if (typeof env.committedText === "string" && env.committedText !== text) {
    add("check_not_byte_identical", "rendered bytes differ from the committed report");
  }

  return {
    ok: errors.length === 0,
    admission: report?.admission ?? null,
    errors,
  };
}

export function validateAdmissionDoc(doc, report, env = {}) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });
  const md = typeof doc === "string" ? doc : "";

  // 1. text hygiene.
  textHygiene(md, add);
  for (const marker of RUNTIME_MARKERS) {
    if (md.includes(marker)) add("crate_touched", `runtime marker ${marker}`);
  }

  // 2. exactly one verdict line, and it must match the report admission.
  const verdictLines = md.match(VERDICT_ANY_RE) || [];
  const match = md.match(VERDICT_RE);
  const verdict = match ? match[1] : null;
  if (verdictLines.length === 0 || verdict === null) {
    add("verdict_missing", verdictLines.join(" | "));
  }
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));
  const expectedVerdict = report?.admission === ADMISSION ? "granted" : "not-adopted";
  if (verdict !== null && verdict !== expectedVerdict) {
    add("adoption_denied_despite_v2", `checkpoint=${verdict} report=${report?.admission}`);
  }

  // 3. mandatory headers and sections.
  for (const key of REQUIRED_HEADERS) {
    const value = headerValue(md, key);
    if (value === null || value.trim() === "") add("header_field_missing", key);
  }
  for (const heading of REQUIRED_SECTIONS) {
    if (!md.split("\n").includes(heading)) add("section_missing", heading);
  }

  // 4. the checkpoint echoes the report.
  const echoes = [
    ["owner_admission_ref", report?.owner_admission_ref, "owner_reacceptance_demanded"],
    ["section3_pin", report?.guards?.section3_pin, "section3_mutated"],
    ["selection", report?.selected_for_s04, "adoption_denied_despite_v2"],
    ["admission_state", report?.admission_state, "adoption_denied_despite_v2"],
    ["activation_state", report?.activation_state, "adoption_read_as_activation"],
  ];
  if (env.checkRevisionEcho === true) {
    echoes.unshift(["source_revision", report?.source_revision, "chain_hash_mismatch"]);
  }
  for (const [key, expected, code] of echoes) {
    const actual = flat(headerValue(md, key));
    if (actual === "" || actual === null) continue;
    if (typeof expected === "string" && actual !== expected) {
      add(code, `${key}: checkpoint=${actual} report=${expected}`);
    }
  }

  const submissionHeader = flat(headerValue(md, "submission_gate"));
  if (submissionHeader !== null && !/actor_bound_path_available=false/.test(submissionHeader)) {
    add("adoption_read_as_submission_authority", `checkpoint submission_gate=${submissionHeader}`);
  }

  const stopHeader = flat(headerValue(md, "runtime_stop"));
  if (stopHeader !== null) {
    if (!/lifted for the adopted candidate-layer scope only/i.test(stopHeader)) {
      add("runtime_stop_blanket_lifted", `checkpoint runtime_stop=${stopHeader}`);
    }
    for (const surface of RUNTIME_STOP_STILL_ACTIVE) {
      if (!stopHeader.includes(surface)) {
        add("runtime_stop_blanket_lifted", `checkpoint runtime_stop omits ${surface}`);
      }
    }
    if (!/(?:stays|remains)\s+active/i.test(stopHeader)) {
      add("runtime_stop_blanket_lifted", "checkpoint runtime_stop does not keep the stop active");
    }
  }

  const f13Header = flat(headerValue(md, "f13_status"));
  if (f13Header !== null && !f13Header.startsWith(F13_DEFERRED_EXPLICIT)) {
    add("f13_missing_answer_misread", `checkpoint f13_status=${f13Header}`);
  }

  for (const [key, code] of [
    ["review_case_events_written", "review_case_event_written"],
    ["requirements_promoted", "requirement_promoted"],
  ]) {
    const actual = flat(headerValue(md, key));
    if (actual === "" || actual === null) continue;
    if (actual !== "0") add(code, `${key}: checkpoint=${actual}`);
  }

  // 5. no resurrection of a superseded reading is permitted in prose.
  const supersessionSection = flat(sectionBody(md, "## Supersession chain"));
  if (supersessionSection === null || !/superseded/i.test(supersessionSection)) {
    add("supersession_chain_broken", "the checkpoint carries no supersession-chain section");
  }
  const ownerSection = flat(sectionBody(md, "## Owner choices not required"));
  if (ownerSection === null || !/(?:not required|no repeat owner|no further owner)/i.test(ownerSection)) {
    add("owner_reacceptance_demanded", "the checkpoint does not state that no repeat owner choice is required");
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
    section3Sha: options.section3Sha ?? lookup.sha256(SECTION3_PATH),
    eventsDirExists:
      options.eventsDirExists ??
      existsSync(
        path.join(rootDir, "prd/architecture/review-cases/packets/RC-2026-09-10-001/events"),
      ),
    exists: options.exists ?? lookup.exists,
    sha256: options.sha256 ?? lookup.sha256,
    insideRoot: options.insideRoot ?? lookup.insideRoot,
    ...options.env,
  };
}

export function runAdmission(argv = [], options = {}) {
  const mode = argv.includes("--check") ? "check" : argv.includes("--print") ? "print" : "write";
  const rootDir = options.rootDir ?? REPO_ROOT;
  const reportPath = path.join(rootDir, RECONCILIATION_RELATIVE_PATH);
  const committedText = existsSync(reportPath) ? readFileSync(reportPath, "utf8") : null;
  const lookup = options.lookup ?? fileLookup(rootDir);
  const stderr = [];
  const stdout = [];

  let liveRevision;
  try {
    liveRevision = options.sourceRevision ?? captureSourceRevision(rootDir, options);
  } catch (error) {
    const detail = error instanceof AdmissionError ? `${error.code}: ${error.detail}` : String(error);
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
    rendered = renderReconciliation({
      rootDir,
      lookup,
      sourceRevision: renderRevision,
      v2CheckpointText: options.v2CheckpointText,
      v2Answer: options.v2Answer,
      v1CheckpointText: options.v1CheckpointText,
      v1Answer: options.v1Answer,
      governing: options.governing,
      s03Gate: options.s03Gate,
    });
  } catch (error) {
    const detail = error instanceof AdmissionError ? `${error.code}: ${error.detail}` : String(error);
    return { mode, exitCode: 1, stdout: "", stderr: [...stderr, detail], wrote: false };
  }

  const env = liveEnv({
    rootDir,
    lookup,
    text: rendered.text,
    committedText: mode === "check" ? committedText ?? "" : undefined,
    sourceRevision: mode === "write" ? liveRevision : undefined,
    checkRevisionEcho: mode === "check",
    eventsDirExists: options.eventsDirExists,
  });
  const errors = [...validateReconciliation(rendered.report, env).errors];

  const mdPath = path.join(rootDir, ADMISSION_RELATIVE_PATH);
  const mdText = existsSync(mdPath) ? readFileSync(mdPath, "utf8") : null;
  if (mdText === null) {
    stderr.push(MD_ABSENT_NOTE);
    if (mode === "check") {
      errors.push({ name: "section_missing", detail: `${ADMISSION_RELATIVE_PATH} is absent` });
    }
  } else {
    errors.push(...validateAdmissionDoc(mdText, rendered.report, env).errors);
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
  const result = runAdmission(argv);
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