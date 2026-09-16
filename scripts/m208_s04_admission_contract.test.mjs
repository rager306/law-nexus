// M208/S04 admission checkpoint contract (T03).
//
// Offline and fail-closed: the real admission record must validate, and every
// named fail-closed case must be provable against a mutated copy of that record
// (or an injected filesystem view), so the suite cannot fool itself by asserting
// codes it would never actually emit.
//
// Subprocesses are limited to `git ls-files` (tracked-file proof) and
// `git status --porcelain` (frozen-scope proof). No cargo, no network, and no
// `.gsd` / ignored / absolute path is ever read as evidence.
//
// Run: node --test scripts/m208_s04_admission_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ADMISSION_DOC = "prd/architecture/m208-s04-admission-bounded-replay.md";
const CONTRACT_PATH = "scripts/m208_s04_admission_contract.test.mjs";
const S01_CONTRACT_PATH = "scripts/m208_s01_admission_contract.test.mjs";
const S02_CONTRACT_PATH = "scripts/m208_s02_admission_contract.test.mjs";
const S03_CONTRACT_PATH = "scripts/m208_s03_admission_contract.test.mjs";
const S01_DOC = "prd/architecture/m208-s01-runtime-admission.md";
const S02_DOC = "prd/architecture/m208-s02-nested-target-admission.md";
const S03_DOC = "prd/architecture/m208-s03-admission-commencement.md";
const M206_ADMISSION = "prd/architecture/m206-s05-runtime-admission.md";
const PULLENTI_MATRIX = "prd/architecture/m205-s01-pullenti-matrix.yaml";
const M205_S03_PIN = "prd/architecture/m205-s03-context-fsm.yaml";
const M205_S04_PIN = "prd/architecture/m205-s04-docs-reconciliation.yaml";
const M205_PINS = [PULLENTI_MATRIX, M205_S03_PIN, M205_S04_PIN];
const M205_RUNTIME_STOP_PINS = [M205_S03_PIN, M205_S04_PIN];
const TEMPORAL_LEGAL_MODEL = "prd/temporal-legal-model.md";
const ADR_0028 = "doc/adr/0028-typed-lexer-legal-marker-lexicon.md";
const ARCHITECTURE = "prd/ARCHITECTURE.md";
const FROZEN_M201_ARTIFACT = "prd/migration/rust-evidence/m201-s03-tracked-chain.json";

// The frozen bounded edition-chain packet inventory. `canon_bytes` is the
// discriminator: exactly these two tracked design pins declare a pinned canon
// byte length, so a third one is a chain minted beyond the frozen packet.
const FROZEN_CHAIN_PACKETS = [
  "prd/architecture/fz44-tracked-edition-chain.yaml",
  "prd/architecture/m203-s07-staged-edition-manifest.yaml",
];
const CHAIN_PACKET_MARKER = "canon_bytes:";
const CHAIN_PACKET_DIR = "prd/architecture/*.yaml";

const BASELINE_GATES = ["G01", "G02", "G14"];
// S04 requests nothing: every matrix row whose `unblocks` contains `S04` is a
// `leave` row with `d388_gates: []`, so the requested union is empty by
// construction of the matrix (D511).
const REQUESTED_NOT_SELECTED_GATES = [];
const DEFERRED_GATES = [
  "G03",
  "G04",
  "G05",
  "G06",
  "G07",
  "G08",
  "G09",
  "G10",
  "G11",
  "G12",
  "G13",
  "G15",
  "G16",
];
// Derived observation: the gates the S04 legs would need if they were ever
// admitted. Recorded as absent dependencies, never as an S04 request.
const DERIVED_LEG_GATES = ["G05", "G11", "G12", "G13", "G15"];
const ALL_D388_GATES = Array.from({ length: 16 }, (_, i) => `G${String(i + 1).padStart(2, "0")}`);
const MIN_SOURCES = 12;

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const LIB_RS = "crates/ln-temporal/src/lib.rs";
const LIB_REGISTRATION_RE = /^\s*(?:pub\s+)?mod\s+(?:bounded_chain_replay|oracle_exam)\s*;/m;
const EXISTING_TEMPORAL_MODULES = [
  "adapters",
  "application",
  "calendar",
  "document_context",
  "domain",
  "identity_binding",
  "ports",
  "provenance",
  "semantic_annotation",
  "semantic_scope",
];

const MATRIX_S04_ROWS = [
  "PC-X-SemanticService",
  "PC-X-MorphEngine",
  "PC-X-global-analyzer-init",
  "PC-X-Instrument-tree",
  "PC-X-occurrence-span",
];

// Declared S04 runtime surfaces: the declared scope of absence. None of these
// may exist while the verdict is `not-adopted`.
const S04_RUNTIME_SURFACES = [
  "crates/ln-temporal/src/bounded_chain_replay.rs",
  "crates/ln-temporal/src/oracle_exam.rs",
  "crates/ln-temporal/tests/npa_bounded_chain_replay_contract.rs",
  "crates/ln-temporal/tests/npa_oracle_discrepancy_contract.rs",
  "crates/ln-temporal/tests/npa_known_as_of_preservation_contract.rs",
  "scripts/m208_s04_bounded_replay_battery.test.mjs",
  "prd/migration/rust-evidence/m208-s04-bounded-replay-battery.json",
  "crates/ln-temporal/tests/m208_s04_frozen_surface_guard.rs",
  "scripts/m208_s04_t05_verify.sh",
];

// Inherited S01 runtime surfaces: not re-scoped by this record, still absent.
const S01_RUNTIME_SURFACES = [
  "crates/ln-decode/src/change_operand.rs",
  "crates/ln-decode/src/change_operation.rs",
];

// Inherited S02 runtime surfaces: not re-scoped by this record, still absent.
const S02_RUNTIME_SURFACES = ["crates/ln-decode/src/change_target.rs"];

// Inherited S03 runtime surfaces: not re-scoped by this record, still absent.
const S03_RUNTIME_SURFACES = [
  "crates/ln-temporal/src/operation_admission.rs",
  "crates/ln-decode/src/change_commencement.rs",
  "crates/ln-temporal/tests/npa_operation_admission_contract.rs",
  "crates/ln-temporal/tests/npa_operation_admission_hostile_contract.rs",
  "crates/ln-decode/tests/npa_change_commencement_contract.rs",
  "scripts/m208_s03_admission_commencement_battery.test.mjs",
  "prd/migration/rust-evidence/m208-s03-admission-commencement-battery.json",
  "crates/ln-temporal/tests/m208_s03_frozen_surface_guard.rs",
  "scripts/m208_s03_t05_verify.sh",
];

const M200_M201_FROZEN_ARTIFACTS = [
  "prd/migration/rust-evidence/m200-s01-scanner-fixture-gate.json",
  "prd/migration/rust-evidence/m200-s02-corpus-acceptance.json",
  "prd/migration/rust-evidence/m200-s02-corpus-smoke-rate.json",
  "prd/migration/rust-evidence/m200-s02-npa-bounds-scan.jsonl",
  "prd/migration/rust-evidence/m200-s03-outlier-review.json",
  "prd/migration/rust-evidence/m200-s04-contract-reconciliation.json",
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
];

const FROZEN_SCOPE = [
  ...M200_M201_FROZEN_ARTIFACTS,
  ...M205_PINS,
  ADR_0028,
  ARCHITECTURE,
  S01_DOC,
  S02_DOC,
  S03_DOC,
];

const REQUIRED_SECTIONS = [
  "## Sources checked",
  "## Owning surfaces",
  "## Non-claims",
  "## Fail-closed boundary",
  "## Marker semantics",
  "## Resume condition",
  "## Prohibited changes",
  "## Neighbouring admitted contours",
];

// The complete fail-closed code set. The record's `## Fail-closed boundary`
// table is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "verdict_missing",
  "verdict_ambiguous",
  "sources_insufficient",
  "source_unresolved",
  "source_not_tracked",
  "source_hash_mismatch",
  "ignored_path_as_source",
  "self_minted_adoption",
  "owner_admission_ref_missing",
  "integrity_pass_as_admission",
  "lock_as_admission",
  "s01_basis_not_adopted",
  "s02_basis_not_adopted",
  "s03_basis_not_adopted",
  "gate_outside_selected_baseline",
  "gate_deferred_mismatch",
  "requested_gate_set_mismatch",
  "derived_leg_gates_mismatch",
  "runtime_stop_inverted",
  "no_start_directive_missing",
  "section_missing",
  "contract_reference_missing",
  "s04_surface_present",
  "s01_surface_present",
  "s02_surface_present",
  "s03_surface_present",
  "lib_rs_registration_present",
  "leave_row_as_admission",
  "pc_x_provenance_resolved_by_guess",
  "adr0028_reopened",
  "s04_owns_adr_claim",
  "new_chain_minted_beyond_frozen_packet",
  "frozen_m201_artifact_modified",
  "oracle_discrepancy_glossary_cell_minted",
  "known_as_of_checkout_claimed",
  "m207_pilot_as_annotation_evidence",
  "neighbouring_contour_as_evidence",
  "runtime_proof_claimed",
  "verify_marker_reachable_claim",
  "contract_pass_as_runtime_proof",
  "lock_as_runtime_proof",
  "s01_contract_missing",
  "s02_contract_missing",
  "s03_contract_missing",
  "t02_note_missing",
];

const T02_NOTE_HEADINGS = [
  "## T02 no-start note: bounded chain replay and scoped oracle exam",
  "## T02 no-start note: known-as-of preservation and unclaimed scope",
  "## T02 no-start note: no hostile contour, no battery, no runtime proof",
];
const T02_PROVENANCE = ["f436a10e", "532e9062", "D503", "D504", "D507", "D508"];
const T02_REQUIRED_TOKENS = [
  "hostile_proof: deferred",
  "battery_proof: deferred",
  "frozen_surface_proof: deferred",
  "runtime_work: not-started",
  "runtime_proof: not-claimed",
  "contract_pass_is_not_runtime_proof: true",
  "lock_is_not_runtime_proof: true",
];

// Anti-claim guards. Each guard names the disclaimer the record must carry and
// the assertion that would contradict it. A guard fires when its disclaimer is
// removed, or when the matching `<code>: true` assertion appears. Every guard is
// additionally reachable through the repo-state checks in `validateAdmission`.
const CLAIM_GUARDS = [
  {
    code: "leave_row_as_admission",
    requires: ["It does not read the five `PC-X-*` leave rows as an admission"],
  },
  {
    code: "pc_x_provenance_resolved_by_guess",
    requires: ["The ambiguity is **not** resolved by guesswork"],
  },
  {
    code: "adr0028_reopened",
    requires: ["It does not reopen ADR-0028."],
    patterns: [/ADR-0028 (?:is|was) reopened\b/i],
  },
  {
    code: "s04_owns_adr_claim",
    requires: ["does not amend that ADR"],
  },
  {
    code: "new_chain_minted_beyond_frozen_packet",
    requires: ["It does not mint a new edition chain beyond the frozen"],
  },
  {
    code: "frozen_m201_artifact_modified",
    requires: ["frozen M201 evidence artifact"],
  },
  {
    code: "oracle_discrepancy_glossary_cell_minted",
    requires: ['mint an "oracle discrepancy" glossary first-cell'],
  },
  {
    code: "known_as_of_checkout_claimed",
    requires: ["bitemporal checkout (no legal_as_of / known_as_of / VIEW)"],
  },
  {
    code: "m207_pilot_as_annotation_evidence",
    requires: ["**absence** of accepted annotations"],
  },
  {
    code: "neighbouring_contour_as_evidence",
    requires: ["No PASS of any neighbouring surface may be quoted as S04 evidence"],
  },
  {
    code: "runtime_proof_claimed",
    requires: ["runtime_proof: not-claimed"],
    patterns: [
      /runtime_proof:\s*(?:claimed|proven|passed)\b/i,
      /runtime_demo:\s*\*{0,2}\s*(?:proven|delivered|shipped)\b/i,
    ],
  },
  {
    code: "verify_marker_reachable_claim",
    requires: ["verify_marker: unreachable"],
    patterns: [/verify_marker:\s*(?:reachable|emitted|available)\b/i],
  },
  {
    code: "contract_pass_as_runtime_proof",
    requires: ["contract_pass_is_not_runtime_proof: true"],
    patterns: [/contract_pass_is_not_runtime_proof:\s*(?:false|no)\b/i],
  },
  {
    code: "lock_as_runtime_proof",
    requires: ["lock_is_not_runtime_proof: true"],
    patterns: [/lock_is_not_runtime_proof:\s*(?:false|no)\b/i],
  },
];

const INTERACTION_RE =
  /interaction\s+[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const LOCK_RE = /d499|gsd_milestone_lock/i;
const INTEGRITY_RE = /\bintegrity\b|\bbattery\b|\bPASS\b/;

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

function trackedFiles(pattern) {
  try {
    return execFileSync("git", ["ls-files", "--", pattern], { cwd: root, encoding: "utf8" })
      .trim()
      .split("\n")
      .filter(Boolean)
      .sort();
  } catch {
    return [];
  }
}

// The tracked design pins that declare a pinned canon byte length.
function chainPacketFiles() {
  return trackedFiles(CHAIN_PACKET_DIR).filter((candidate) =>
    readRepo(candidate).includes(CHAIN_PACKET_MARKER),
  );
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

function headerBlock(doc, key) {
  const lines = doc.split("\n");
  const prefix = `**${key}:**`;
  const start = lines.findIndex((line) => line.startsWith(prefix));
  if (start === -1) return null;
  let end = start + 1;
  while (end < lines.length && !lines[end].startsWith("**") && lines[end].trim() !== "") {
    end += 1;
  }
  return lines.slice(start, end).join("\n");
}

function gateList(value) {
  if (!value) return [];
  return value.split(/[,\s]+/).filter((token) => /^G\d{2}$/.test(token));
}

function sameSet(a, b) {
  return a.length === b.length && a.every((item) => b.includes(item));
}

function sourceRows(doc) {
  return [...doc.matchAll(/^\| `([^`]+)` \| `([0-9a-f]{64})` \|/gm)].map((match) => ({
    path: match[1],
    sha: match[2],
  }));
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

function verdictOf(text) {
  const lines = text.match(/^\*\*admission: .*\*\*$/gm) || [];
  const match = text.match(/^\*\*admission: (granted|not-adopted)\*\*$/m);
  return { lines, value: match ? match[1] : null };
}

// The derived-leg observation paragraph: the gates the S04 legs would need,
// recorded as absent dependencies rather than as an S04 request.
function derivedLegGates(text) {
  const lines = text.split("\n");
  const start = lines.findIndex((line) => line.startsWith("**Derived observation"));
  if (start === -1) return [];
  const paragraph = [];
  for (let i = start; i < lines.length; i += 1) {
    if (i > start && lines[i].trim() === "") break;
    paragraph.push(lines[i]);
  }
  const tokens = paragraph.join(" ").match(/\bG\d{2}\b/g) || [];
  return [...new Set(tokens)].sort();
}

// The `## 3. Glossary and ownership` table of `prd/temporal-legal-model.md`,
// normalised so a minted first cell is detectable.
function s3GlossarySection(text) {
  const lines = text.split("\n");
  const start = lines.findIndex((line) => line.startsWith("## 3. Glossary"));
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

function glossaryFirstCells(text) {
  const body = s3GlossarySection(text);
  if (body === null) return [];
  return body
    .split("\n")
    .filter((line) => line.startsWith("|"))
    .map((line) =>
      line
        .split("|")[1]
        .replace(/`/g, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim(),
    )
    .filter((cell) => cell.length > 0 && !/^-+$/.test(cell));
}

// The matrix rows whose `unblocks` contains `S04`, parsed from the live tracked
// YAML rather than from the checkpoint's own restatement. Matrix rows are
// indented list entries (`  - {id: ...}`) in flow-mapping form.
const MATRIX_ROW_RE =
  /^\s*- \{id: ([^,]+),.*?family: ([^,]+),.*?take_or_leave: ([^,]+),.*?owner_crate_or_yaml: ([^,]+),.*?lifecycle: \[([^\]]*)\],.*?d388_gates: \[([^\]]*)\],.*?human_adoption: ([a-z-]+),.*?unblocks: \[([^\]]*)\]\}$/gm;

function matrixRows(text) {
  return [...text.matchAll(MATRIX_ROW_RE)].map((match) => ({
    id: match[1].trim(),
    family: match[2].trim(),
    takeOrLeave: match[3].trim(),
    owner: match[4].trim(),
    lifecycle: match[5].trim(),
    gates: gateList(match[6]),
    adoption: match[7],
    unblocks: match[8].split(",").map((entry) => entry.trim()),
  }));
}

function matrixS04Rows(text) {
  return matrixRows(text).filter((row) => row.unblocks.includes("S04"));
}

// The checkpoint's own restatement of those rows (`## Adoption state ...` table).
const ADOPTION_ROW_RE =
  /^\| `([A-Za-z0-9-]+)` \| `([^`]+)` \| ([^|]+) \| ([a-z-]+) \| `\[([^\]]*)\]` \| `\[([^\]]*)\]` \| ([^|]+) \|$/gm;

function adoptionTableRows(text) {
  const body = section(text, "## Adoption state of the rows that unblock S04");
  if (body === null) return [];
  return [...body.matchAll(ADOPTION_ROW_RE)].map((match) => ({
    id: match[1],
    owner: match[2],
    adoption: match[4],
    gates: gateList(match[5]),
    unblocks: match[7]
      .split(",")
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0),
  }));
}

// ---------------------------------------------------------------------------
// section guards
// ---------------------------------------------------------------------------

// T02 note guard: the three design-only no-start notes must stay present with
// their provenance and their design sentinels while the verdict is not-adopted.
function t02NoteErrors(text) {
  const notes = T02_NOTE_HEADINGS.map((heading) => section(text, heading));
  if (notes.some((note) => note === null)) return ["t02_note_missing"];
  const body = notes.join("\n");
  if (!T02_PROVENANCE.every((ref) => body.includes(ref))) return ["t02_note_missing"];
  if (!T02_REQUIRED_TOKENS.every((token) => body.includes(token))) return ["t02_note_missing"];
  if (!body.includes("verdict=not-adopted")) return ["t02_note_missing"];
  return [];
}

// Anti-claim guard: no runtime proof, verify marker, contract PASS, D499 lock,
// leave-row admission, guessed provenance, reopened ADR, minted chain, modified
// frozen artifact, minted glossary cell, claimed checkout, M207 protocol
// re-label, or neighbouring-contour re-read may be asserted while the checkpoint
// stands.
function claimGuardErrors(text) {
  const errors = [];
  for (const guard of CLAIM_GUARDS) {
    if (guard.requires.some((token) => !text.includes(token))) {
      errors.push(guard.code);
      continue;
    }
    const assertion = new RegExp(`^${guard.code}:\\s*(?:true|yes)\\b`, "im");
    const patterns = [assertion, ...(guard.patterns || [])];
    if (patterns.some((pattern) => pattern.test(text))) errors.push(guard.code);
  }
  return [...new Set(errors)];
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateAdmission(doc, options = {}) {
  const {
    s01Text = liveS01,
    s02Text = liveS02,
    s03Text = liveS03,
    libText = liveLib,
    matrixText = liveMatrix,
    pinTexts = livePinTexts,
    glossaryText = liveGlossary,
    packetFiles = liveChainPackets,
    frozenM201Delta = liveFrozenM201Delta,
    adr0028Text = liveAdr0028,
    adr0028Delta = liveAdr0028Delta,
    fileExists = repoExists,
    surfaceExists = repoExists,
    s01ContractExists = repoExists(S01_CONTRACT_PATH),
    s02ContractExists = repoExists(S02_CONTRACT_PATH),
    s03ContractExists = repoExists(S03_CONTRACT_PATH),
  } = options;

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  // (1) verdict: at least one, at most one, and one of the two known values.
  const { lines: verdictLines, value: verdict } = verdictOf(doc);
  if (verdictLines.length === 0 || verdict === null) {
    add("verdict_missing", verdictLines.join(" | "));
  }
  if (verdictLines.length > 1) add("verdict_ambiguous", verdictLines.join(" | "));

  // (2) byte-bound sources: repository-relative, resolvable, tracked, hash-equal.
  const rows = sourceRows(doc);
  if (rows.length < MIN_SOURCES) add("sources_insufficient", `rows=${rows.length}`);
  for (const row of rows) {
    if (IGNORED_SOURCE_PREFIXES.some((prefix) => row.path.startsWith(prefix))) {
      add("ignored_path_as_source", row.path);
      continue;
    }
    if (row.path.startsWith("/")) {
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

  // (3) gate partition: selected / requested-not-selected / deferred / derived.
  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const requestedRaw = headerValue(doc, "requested_not_selected_d388_gates") || "";
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  const allowedSelected =
    verdict === "granted" ? [...BASELINE_GATES, ...DERIVED_LEG_GATES] : [...BASELINE_GATES];
  for (const gate of selected) {
    if (!allowedSelected.includes(gate)) add("gate_outside_selected_baseline", gate);
  }
  const expectedDeferred = ALL_D388_GATES.filter((gate) => !selected.includes(gate));
  if (!sameSet(deferred, expectedDeferred)) {
    add("gate_deferred_mismatch", `deferred=${deferred.join(",")}`);
  }
  // The requested set is empty by construction of the matrix; it must be
  // recorded as an empty set rather than omitted, and never widened.
  if (!sameSet(requested, REQUESTED_NOT_SELECTED_GATES) || !/empty set/i.test(requestedRaw)) {
    add("requested_gate_set_mismatch", `requested=${requested.join(",")} raw=${requestedRaw}`);
  }
  const derived = derivedLegGates(doc);
  if (!sameSet(derived, DERIVED_LEG_GATES)) {
    add("derived_leg_gates_mismatch", `derived=${derived.join(",")}`);
  }

  // (4) not-adopted invariants: the stop stands and a no-start directive exists.
  const runtimeStop = headerValue(doc, "runtime_stop") || "";
  const runtimeWork = headerValue(doc, "runtime_work") || "";
  const runtimeDemo = headerValue(doc, "runtime_demo") || "";
  const ownerRef = headerValue(doc, "owner_admission_ref") || "";
  const basis = headerValue(doc, "admission_basis") || "";
  if (verdict === "not-adopted") {
    if (/\blifted\b/i.test(runtimeStop) || !/remains active for M208\/S04/i.test(runtimeStop)) {
      add("runtime_stop_inverted", runtimeStop);
    }
    if (!runtimeWork.startsWith("not-started")) add("no_start_directive_missing", runtimeWork);
    if (!doc.includes("**no_start_directive:**")) {
      add("no_start_directive_missing", "no_start_directive header absent");
    }
    if (runtimeDemo !== "not-proven") add("runtime_proof_claimed", `runtime_demo=${runtimeDemo}`);
    if (ownerRef !== "none") {
      add("owner_admission_ref_missing", `owner_admission_ref=${ownerRef} under not-adopted`);
    }
  }

  // Self-minted adoption: a grant can never be derived from pins, an integrity
  // PASS or the milestone lock.
  if (verdict === "granted") {
    const hasInteraction = INTERACTION_RE.test(`${basis} ${ownerRef}`);
    if (!hasInteraction) add("owner_admission_ref_missing", ownerRef);
    if (LOCK_RE.test(`${basis} ${ownerRef}`)) add("lock_as_admission", basis);
    if (INTEGRITY_RE.test(basis) && !hasInteraction) add("integrity_pass_as_admission", basis);
    if (rows.length > 0 && rows.every((row) => /\.ya?ml$/i.test(row.path))) {
      add("self_minted_adoption", rows.map((row) => row.path).join(","));
    }
  }

  // (5) required sections and the contract reference.
  for (const heading of REQUIRED_SECTIONS) {
    if (!doc.includes(heading)) add("section_missing", heading);
  }
  if (!doc.includes(CONTRACT_PATH)) add("contract_reference_missing", CONTRACT_PATH);

  // (6) S01, S02 and S03 bases: cited among the sources and all reading
  // `not-adopted`. None of the three may be inverted by this record.
  const bases = [
    [S01_DOC, s01Text, "s01_basis_not_adopted"],
    [S02_DOC, s02Text, "s02_basis_not_adopted"],
    [S03_DOC, s03Text, "s03_basis_not_adopted"],
  ];
  for (const [basisPath, basisText, code] of bases) {
    const cited = rows.some((row) => row.path === basisPath);
    const basisVerdict = verdictOf(basisText).value;
    if (!cited || basisVerdict !== "not-adopted") {
      add(code, `cited=${cited} verdict=${basisVerdict}`);
    }
  }
  if (!s01ContractExists) add("s01_contract_missing", S01_CONTRACT_PATH);
  if (!s02ContractExists) add("s02_contract_missing", S02_CONTRACT_PATH);
  if (!s03ContractExists) add("s03_contract_missing", S03_CONTRACT_PATH);

  // (7) T02 no-start notes and the anti-claim guards.
  for (const code of t02NoteErrors(doc)) add(code, "T02 no-start note guard");
  for (const code of claimGuardErrors(doc)) add(code, "claim guard");

  // (8) Machine proof of absence: no declared S04 or inherited S01/S02/S03
  // runtime surface may exist, and neither `mod bounded_chain_replay` nor
  // `mod oracle_exam` may be registered.
  for (const surface of S04_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s04_surface_present", surface);
  }
  for (const surface of S01_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s01_surface_present", surface);
  }
  for (const surface of S02_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s02_surface_present", surface);
  }
  for (const surface of S03_RUNTIME_SURFACES) {
    if (surfaceExists(surface)) add("s03_surface_present", surface);
  }
  if (LIB_REGISTRATION_RE.test(libText)) add("lib_rs_registration_present", LIB_RS);

  // (9) Matrix rows whose `unblocks` contains `S04`: all five must stay `leave`
  // rows with no gate, otherwise a row would be readable as an admission and the
  // empty requested set would no longer be a property of the matrix.
  const s04Rows = matrixS04Rows(matrixText);
  if (s04Rows.length !== MATRIX_S04_ROWS.length) {
    add("leave_row_as_admission", `rows=${s04Rows.length}`);
  } else {
    for (const row of s04Rows) {
      if (
        row.family !== "leave" ||
        row.takeOrLeave !== "leave" ||
        row.gates.length > 0 ||
        row.adoption !== "not-required"
      ) {
        add(
          "leave_row_as_admission",
          `${row.id} family=${row.family} take=${row.takeOrLeave} gates=${row.gates.join("|")} adoption=${row.adoption}`,
        );
      }
    }
  }
  const matrixGateUnion = [...new Set(s04Rows.flatMap((row) => row.gates))].sort();
  if (!sameSet(matrixGateUnion, REQUESTED_NOT_SELECTED_GATES)) {
    add("requested_gate_set_mismatch", `matrix gate union=${matrixGateUnion.join(",")}`);
  }

  // (10) M205 pins: the design pins must keep their adoption pending and their
  // runtime stop active; an adoption minted in the design data is not a grant.
  for (const pin of M205_RUNTIME_STOP_PINS) {
    const pinText = pinTexts[pin] || "";
    if (!/^human_adoption: pending$/m.test(pinText)) {
      add("self_minted_adoption", `${pin} no longer keeps human_adoption: pending`);
    }
    if (!/^runtime_stop_active: true$/m.test(pinText)) {
      add("runtime_stop_inverted", `${pin} no longer keeps the runtime stop active`);
    }
  }

  // (11) Frozen bounded chain packet inventory: a third packet declaring pinned
  // canon bytes would be a chain minted beyond the frozen packet.
  if (!sameSet([...packetFiles].sort(), [...FROZEN_CHAIN_PACKETS].sort())) {
    add("new_chain_minted_beyond_frozen_packet", packetFiles.join(","));
  }

  // (12) The frozen M201 evidence artifact carries no worktree delta.
  if (frozenM201Delta !== "") add("frozen_m201_artifact_modified", frozenM201Delta);

  // (13) ADR-0028 is neither modified nor reopened by M208/S04.
  if (adr0028Delta !== "" || /^## .*M208/m.test(adr0028Text)) {
    add("adr0028_reopened", "ADR-0028 carries a worktree delta or a new M208 section");
  }

  // (14) No "oracle discrepancy" glossary first-cell may be minted in
  // `prd/temporal-legal-model.md` §3.
  if (glossaryFirstCells(glossaryText).includes("oracle discrepancy")) {
    add("oracle_discrepancy_glossary_cell_minted", `${TEMPORAL_LEGAL_MODEL} §3`);
  }

  return { ok: errors.length === 0, verdict, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const liveDoc = readRepo(ADMISSION_DOC);
const liveS01 = readRepo(S01_DOC);
const liveS02 = readRepo(S02_DOC);
const liveS03 = readRepo(S03_DOC);
const liveLib = readRepo(LIB_RS);
const liveMatrix = readRepo(PULLENTI_MATRIX);
const livePinTexts = Object.fromEntries(M205_PINS.map((pin) => [pin, readRepo(pin)]));
const liveGlossary = readRepo(TEMPORAL_LEGAL_MODEL);
const liveChainPackets = chainPacketFiles();
const liveAdr0028 = readRepo(ADR_0028);
const liveFrozenM201Delta = worktreeDelta([FROZEN_M201_ARTIFACT]);
const liveAdr0028Delta = worktreeDelta([ADR_0028]);

const doc = liveDoc;

// The live `admission_basis` block, byte-exact, so a granted fixture provably
// replaces it instead of silently no-oping.
const NOT_ADOPTED_BASIS_BLOCK = headerBlock(doc, "admission_basis");

function fixture(mutate) {
  const next = mutate(doc);
  assert.notEqual(next, doc, "fixture mutation did not modify the document");
  return next;
}

function grantedText(text, basisText, extra) {
  assert.ok(
    text.includes(NOT_ADOPTED_BASIS_BLOCK),
    "granted mutation requires the live basis block",
  );
  let next = text.replace("**admission: not-adopted**", "**admission: granted**");
  next = next.replace(NOT_ADOPTED_BASIS_BLOCK, `**admission_basis:** ${basisText}`);
  return extra ? extra(next) : next;
}

function grantedFixture(basisText, extra) {
  const next = grantedText(doc, basisText, extra);
  assert.ok(next.includes(`**admission_basis:** ${basisText}`), "fixture basis replacement failed");
  return next;
}

function expectCode(text, expected, options) {
  const result = validateAdmission(text, options);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

// A guard assertion: appending `<code>: true` is the canonical contradiction for
// every documented claim guard.
function claim(code) {
  return (text) => `${text}\n\n${code}: true\n`;
}

const STRIP_SOURCE_ROWS = /^\| `[^`]+` \| `[0-9a-f]{64}` \|.*$\n?/gm;
const YAML_ONLY_ROWS = [
  PULLENTI_MATRIX,
  M205_S03_PIN,
  M205_S04_PIN,
  "prd/architecture/m205-s02-pre-capture-grammar.yaml",
  "prd/architecture/npa-document-context.yaml",
  "prd/architecture/operation-registry.yaml",
  "prd/architecture/current-document-requisites.yaml",
  "prd/architecture/pending-effects-contract.yaml",
  "prd/architecture/force-interval-set-contract.yaml",
  "prd/architecture/npa-parsing-program.yaml",
  "prd/architecture/npa-identifying-cycle.yaml",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
]
  .map((entry) => `| \`${entry}\` | \`${"0".repeat(64)}\` | pin |`)
  .join("\n");

const SELECTED_LINE = "**selected_d388_gates:** G01, G02, G14";
const DEFERRED_LINE =
  "**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16";
const REQUESTED_LINE = "**requested_not_selected_d388_gates:** (empty set)";

// A §3 glossary carrying a minted "oracle discrepancy" first cell.
function withMintedGlossaryCell() {
  const body = s3GlossarySection(liveGlossary);
  assert.ok(body !== null, "the glossary section must exist");
  const mutated = body.replace(
    /\n\|/,
    "\n| oracle discrepancy | minted by the T03 fixture |\n|",
  );
  assert.notEqual(mutated, body, "the glossary mutation must change the section");
  const next = liveGlossary.replace(body, mutated);
  assert.notEqual(next, liveGlossary, "the glossary mutation must change the document");
  return next;
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M208 S04 admission checkpoint is valid, byte-bound and fail-closed", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  assert.ok(
    sourceRows(doc).length >= MIN_SOURCES,
    `checkpoint must cite at least ${MIN_SOURCES} byte-bound sources`,
  );
});

test("M208 S04 admission verdict is unambiguous and not-adopted", () => {
  const result = validateAdmission(doc);
  assert.equal(result.verdict, "not-adopted");
  assert.equal((doc.match(/^\*\*admission: /gm) || []).length, 1, "exactly one verdict line");
  assert.match(doc, /^\*\*owner_admission_ref:\*\* none$/m);
  assert.match(doc, /^\*\*runtime_work:\*\* not-started$/m);
  assert.equal(headerValue(doc, "runtime_demo"), "not-proven", "the S04 demo stays not-proven");
  assert.match(doc, /^\*\*runtime_stop:\*\* remains active for M208\/S04;/m);
  assert.ok(doc.includes("**no_start_directive:**"), "the record must carry a no-start directive");
  assert.equal(headerValue(doc, "contract"), CONTRACT_PATH, "the record must name its own contract");
});

test("M208 S04 sources are resolvable, tracked and hash-bound", () => {
  const rows = sourceRows(doc);
  assert.ok(rows.length >= MIN_SOURCES, "the checkpoint cites at least twelve sources");
  for (const row of rows) {
    assert.ok(!row.path.startsWith("/"), `${row.path} must be repository-relative`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!row.path.startsWith(prefix), `${row.path} must not be an ignored path`);
    }
    assert.ok(repoExists(row.path), `${row.path} must exist`);
    assert.ok(isTracked(row.path), `${row.path} must be tracked`);
    assert.equal(sha256(row.path), row.sha, `${row.path} must match its recorded sha256`);
  }
  for (const basis of [S01_DOC, S02_DOC, S03_DOC]) {
    assert.ok(
      rows.some((row) => row.path === basis),
      `${basis} must be cited as an S04 admission basis`,
    );
    assert.match(readRepo(basis), /^\*\*admission: not-adopted\*\*$/m, `${basis} stays not-adopted`);
  }
  assert.ok(
    rows.some((row) => row.path === M206_ADMISSION),
    "the only granted scope in this area must be cited as a non-covering admission",
  );
});

test("M208 S04 gate partition selects only the not-adopted baseline", () => {
  const selected = gateList(headerValue(doc, "selected_d388_gates"));
  const requested = gateList(headerValue(doc, "requested_not_selected_d388_gates"));
  const deferred = gateList(headerValue(doc, "deferred_d388_gates"));
  assert.deepEqual([...selected].sort(), [...BASELINE_GATES].sort());
  assert.deepEqual(requested, [], "S04 requests the empty set by construction of the matrix");
  assert.match(headerValue(doc, "requested_not_selected_d388_gates"), /empty set/i);
  assert.deepEqual(
    [...deferred].sort(),
    [...ALL_D388_GATES.filter((gate) => !selected.includes(gate))].sort(),
    "deferred must be the exact complement of selected over G01..G16",
  );
  assert.deepEqual([...deferred].sort(), [...DEFERRED_GATES].sort(), "thirteen gates stay deferred");
  assert.deepEqual(
    derivedLegGates(doc),
    [...DERIVED_LEG_GATES].sort(),
    "the derived-leg observation must be exactly G05/G11/G12/G13/G15",
  );
});

test("the fail-closed code set is synchronized with the checkpoint record", () => {
  const table = section(doc, "## Fail-closed boundary");
  assert.ok(table, "the record must carry a Fail-closed boundary section");
  const nonCodeTokens = new Set(["runtime_stop", "granted", "leave"]);
  const documented = new Set(
    [...table.matchAll(/`([a-z][a-z0-9_]*)`/g)]
      .map((match) => match[1])
      .filter((token) => !nonCodeTokens.has(token)),
  );
  assert.deepEqual(
    [...documented].sort(),
    [...EMITTABLE_CODES].sort(),
    "the documented code set must equal the set this contract can emit",
  );
  // Every named code must be empirically reachable outside the registry array:
  // one mutation per code below must actually make it fire.
  const withoutRegistry = readRepo(CONTRACT_PATH).replace(
    /const EMITTABLE_CODES = \[[\s\S]*?\];/,
    "",
  );
  for (const code of EMITTABLE_CODES) {
    assert.ok(
      withoutRegistry.includes(`"${code}"`),
      `${code} must be reachable in the contract body, not only in the code registry`,
    );
  }
});

test("M205 pins keep the S04 rows unadopted and the stop active", () => {
  const matrix = readRepo(PULLENTI_MATRIX);
  assert.ok(matrix.includes("authoritative: false"), "the matrix stays non-authoritative");
  const s04Rows = matrixS04Rows(matrix);
  assert.equal(s04Rows.length, 5, "exactly five matrix rows must unblock S04");
  for (const row of s04Rows) {
    assert.equal(row.family, "leave", `${row.id} must stay family: leave`);
    assert.equal(row.takeOrLeave, "leave", `${row.id} must stay take_or_leave: leave`);
    assert.deepEqual(row.gates, [], `${row.id} must keep an empty d388_gates set`);
    assert.equal(row.adoption, "not-required", `${row.id} must keep human_adoption: not-required`);
    assert.equal(row.lifecycle, "proposed", `${row.id} must stay lifecycle: [proposed]`);
  }
  assert.deepEqual(
    [...new Set(s04Rows.flatMap((row) => row.gates))],
    REQUESTED_NOT_SELECTED_GATES,
    "the S04 row gate union is empty by construction of the matrix",
  );
  for (const pin of M205_PINS) {
    assert.ok(readRepo(pin).includes("human_adoption: pending"), `${pin} keeps adoption pending`);
  }
  for (const pin of M205_RUNTIME_STOP_PINS) {
    assert.match(readRepo(pin), /^runtime_stop_active: true$/m, `${pin} keeps the runtime stop`);
  }
  const s03Pin = readRepo(M205_S03_PIN);
  assert.match(s03Pin, /must_not_select: \[G08, G09, G10, G11, G12, G13, G15\]/, "pin bars the legs");
  assert.match(
    s03Pin,
    /selected_baseline: \[G01, G02, G14\]/,
    "the pin selects the same baseline as this checkpoint",
  );
  // G05 is requested by the S01 line only; the pin bars G11/G12/G13/G15 by name.
  for (const gate of ["G11", "G12", "G13", "G15"]) {
    assert.ok(
      new RegExp(`must_not_select: \\[[^\\]]*${gate}`).test(s03Pin),
      `${gate} must stay barred from selection in the M205/S03 pin`,
    );
  }
  for (const gate of DERIVED_LEG_GATES) {
    assert.ok(
      !new RegExp(`selected_baseline: \\[[^\\]]*${gate}`).test(s03Pin),
      `${gate} must not enter the M205/S03 selected baseline`,
    );
  }
});

test("the checkpoint restates the five S04 matrix rows without drift", () => {
  const declared = adoptionTableRows(doc);
  assert.equal(declared.length, 5, "the record must restate exactly five S04 rows");
  const live = new Map(matrixS04Rows(readRepo(PULLENTI_MATRIX)).map((row) => [row.id, row]));
  for (const row of declared) {
    const source = live.get(row.id);
    assert.ok(source, `${row.id} must exist in the live matrix`);
    assert.equal(row.owner, source.owner, `${row.id} owning surface must match the live matrix`);
    assert.equal(row.adoption, source.adoption, `${row.id} adoption must match the live matrix`);
    assert.equal(row.adoption, "not-required", `${row.id} must stay not-required in the record`);
    assert.deepEqual([...row.gates].sort(), [...source.gates].sort(), `${row.id} gate drift`);
    assert.deepEqual(
      [...row.unblocks].sort(),
      [...source.unblocks].sort(),
      `${row.id} unblocks drift`,
    );
  }
  assert.deepEqual(
    [...declared.map((row) => row.id)].sort(),
    [...live.keys()].sort(),
    "the record's restated row set must equal the live S04 row set",
  );
});

test("no M208/S04 or inherited S01/S02/S03 runtime surface exists while not-adopted", () => {
  for (const surface of [
    ...S04_RUNTIME_SURFACES,
    ...S01_RUNTIME_SURFACES,
    ...S02_RUNTIME_SURFACES,
    ...S03_RUNTIME_SURFACES,
  ]) {
    assert.equal(repoExists(surface), false, `${surface} must not exist yet`);
  }
  const lib = readRepo(LIB_RS);
  const registered = [...lib.matchAll(/^\s*(?:pub\s+)?mod\s+([a-z_]+)\s*;/gm)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(
    registered,
    [...EXISTING_TEMPORAL_MODULES].sort(),
    "ln-temporal must register exactly its ten existing modules",
  );
  assert.ok(!LIB_REGISTRATION_RE.test(lib), "lib.rs must not register the S04 modules");
  assert.ok(
    !/mod\s+(?:change_operand|change_operation|change_target|change_commencement|operation_admission)\s*;/m.test(
      lib,
    ),
    "lib.rs must not register any inherited no-start module",
  );
});

test("the frozen scope is tracked and carries no worktree delta", () => {
  for (const artifact of M200_M201_FROZEN_ARTIFACTS) {
    assert.ok(isTracked(artifact), `${artifact} must stay tracked`);
  }
  assert.equal(worktreeDelta(FROZEN_SCOPE), "", "the frozen scope must carry no worktree delta");
  assert.equal(worktreeDelta([FROZEN_M201_ARTIFACT]), "", "the frozen M201 artifact is untouched");
  assert.equal(worktreeDelta([ADR_0028]), "", "ADR-0028 must not be edited");
  assert.ok(!/M208/.test(readRepo(ADR_0028)), "ADR-0028 must not be reopened for M208");
  assert.ok(
    readRepo(ADR_0028).includes("## M205/S04 reconciliation companion [proposed]"),
    "the S04 owns ADR wording stays with M205/S04",
  );
  assert.deepEqual(
    [...liveChainPackets].sort(),
    [...FROZEN_CHAIN_PACKETS].sort(),
    "the frozen chain packet inventory must stay closed",
  );
  assert.equal(
    glossaryFirstCells(liveGlossary).includes("oracle discrepancy"),
    false,
    "no oracle-discrepancy glossary cell may be minted",
  );
});

test("the contract only shells out to git and reads no ignored path as evidence", () => {
  const source = readRepo(CONTRACT_PATH);
  const declared = [...source.matchAll(/^(?:const|let)\s+[A-Za-z_$][\w$]*\s*=\s*"([^"]+)";$/gm)].map(
    (match) => match[1],
  );
  for (const value of declared) {
    assert.ok(!value.startsWith("/"), `absolute path literal ${value} is not admissible evidence`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!value.startsWith(prefix), `ignored path literal ${value} is not admissible`);
    }
  }
  for (const entry of [
    ...S04_RUNTIME_SURFACES,
    ...S01_RUNTIME_SURFACES,
    ...S02_RUNTIME_SURFACES,
    ...S03_RUNTIME_SURFACES,
    ...M205_PINS,
    ...M200_M201_FROZEN_ARTIFACTS,
    ...FROZEN_CHAIN_PACKETS,
    ...FROZEN_SCOPE,
  ]) {
    assert.ok(!entry.startsWith("/"), `${entry} must be repository-relative`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!entry.startsWith(prefix), `${entry} must not be an ignored path`);
    }
  }
  assert.ok(
    !/readRepo\(\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readRepo\(\s*"\//.test(source), "the contract must not read an absolute path");
  const binaries = [...source.matchAll(/execFileSync\(\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual([...new Set(binaries)], ["git"], "git is the only subprocess the contract spawns");
  const subcommands = [...source.matchAll(/execFileSync\(\s*"git",\s*\[\s*"([^"]+)"/g)].map(
    (match) => match[1],
  );
  for (const subcommand of subcommands) {
    assert.ok(
      ["ls-files", "status"].includes(subcommand),
      `unexpected git subcommand ${subcommand}`,
    );
  }
  assert.ok(!/\bfetch\b|https?:\/\//.test(source), "the contract must not touch the network");
  assert.ok(
    !/execFileSync\(\s*"(?:cargo|npm|npx|node|sh|bash)"/.test(source),
    "the contract must not spawn non-git subprocesses",
  );
});

test("the contract never emits the verify marker", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifyMarker = ["M208_S04", "VERIFY_OK"].join("_");
  const emitter = new RegExp("console\\.log\\(\\s*[\"'`]" + verifyMarker);
  assert.ok(!emitter.test(source), `${verifyMarker} must be unreachable by construction`);
  assert.ok(doc.includes(verifyMarker), "the record must document the verify marker as unreachable");
  assert.ok(
    doc.includes("verify_marker: unreachable"),
    "the record must keep verify_marker: unreachable",
  );
});

// ---------------------------------------------------------------------------
// fail-closed negatives
// ---------------------------------------------------------------------------

test("negative: missing verdict and ambiguous verdict", () => {
  expectCode(
    fixture((text) => text.replace("**admission: not-adopted**", "**admission_state: pending**")),
    "verdict_missing",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        "**admission: not-adopted**",
        "**admission: not-adopted**\n**admission: granted**",
      ),
    ),
    "verdict_ambiguous",
  );
});

test("negative: insufficient byte-bound sources", () => {
  expectCode(fixture((text) => text.replace(STRIP_SOURCE_ROWS, "")), "sources_insufficient");
});

test("negative: unresolvable, untracked, ignored and absolute source references", () => {
  expectCode(
    fixture((text) =>
      text.replace(`| \`${PULLENTI_MATRIX}\` |`, "| `prd/architecture/m208-s04-missing.yaml` |"),
    ),
    "source_unresolved",
  );
  expectCode(
    fixture((text) => text.replace(`| \`${PULLENTI_MATRIX}\` |`, "| `/tmp/m208-s04-source.md` |")),
    "source_not_tracked",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        `| \`${PULLENTI_MATRIX}\` |`,
        "| `.agents/skills/law-nexus-rust/references/verification-matrix.md` |",
      ),
    ),
    "ignored_path_as_source",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        `| \`${PULLENTI_MATRIX}\` |`,
        "| `.gsd/phases/208-wrz6fg-temporal/208-04-PLAN.md` |",
      ),
    ),
    "ignored_path_as_source",
  );
});

test("negative: sha256 mismatch against the live source content", () => {
  expectCode(
    fixture((text) => text.replace(sha256(PULLENTI_MATRIX), "0".repeat(64))),
    "source_hash_mismatch",
  );
});

test("negative: adoption minted from pins alone", () => {
  const text = grantedFixture(
    "the Change-family pin rows unblock M208 and the design matrix declares the vocabulary.",
    (next) => next.replace(STRIP_SOURCE_ROWS, `${YAML_ONLY_ROWS}\n`),
  );
  expectCode(text, "self_minted_adoption");
  expectCode(text, "owner_admission_ref_missing");
});

test("negative: integrity pass and milestone lock cannot substitute for an admission", () => {
  expectCode(
    grantedFixture("M206 runtime battery integrity PASS authorises M208/S04."),
    "integrity_pass_as_admission",
  );
  expectCode(
    grantedFixture(
      "D499 GSD_MILESTONE_LOCK authorises M208/S04 (interaction 00000000-0000-0000-0000-000000000000).",
    ),
    "lock_as_admission",
  );
});

test("negative: owner admission reference mismatch in both directions", () => {
  expectCode(
    grantedFixture(
      "the owner approved the M208/S04 bounded-replay scope verbally.",
      (next) => next.replace("**owner_admission_ref:** none", "**owner_admission_ref:** verbal"),
    ),
    "owner_admission_ref_missing",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        "**owner_admission_ref:** none",
        "**owner_admission_ref:** interaction 00000000-0000-0000-0000-000000000000",
      ),
    ),
    "owner_admission_ref_missing",
  );
});

test("negative: the S01, S02 and S03 bases must be cited and must read not-adopted", () => {
  const s01Granted = liveS01.replace("**admission: not-adopted**", "**admission: granted**");
  expectCode(doc, "s01_basis_not_adopted", { s01Text: s01Granted });
  const s02Granted = liveS02.replace("**admission: not-adopted**", "**admission: granted**");
  expectCode(doc, "s02_basis_not_adopted", { s02Text: s02Granted });
  const s03Granted = liveS03.replace("**admission: not-adopted**", "**admission: granted**");
  expectCode(doc, "s03_basis_not_adopted", { s03Text: s03Granted });
  expectCode(
    fixture((text) =>
      text.replace(`| \`${S01_DOC}\` |`, `| \`${M206_ADMISSION}\` |`),
    ),
    "s01_basis_not_adopted",
  );
  expectCode(
    fixture((text) => text.replace(`| \`${S02_DOC}\` |`, "| `prd/architecture/m208-s07.yaml` |")),
    "s02_basis_not_adopted",
  );
  expectCode(
    fixture((text) => text.replace(`| \`${S03_DOC}\` |`, "| `prd/architecture/m208-s08.yaml` |")),
    "s03_basis_not_adopted",
  );
});

test("negative: gate outside the baseline and broken partitions", () => {
  expectCode(
    fixture((text) =>
      text
        .replace(SELECTED_LINE, "**selected_d388_gates:** G01, G02, G07, G14")
        .replace(
          DEFERRED_LINE,
          "**deferred_d388_gates:** G03, G04, G05, G06, G08, G09, G10, G11, G12, G13, G15, G16",
        ),
    ),
    "gate_outside_selected_baseline",
  );
  expectCode(fixture((text) => text.replace(DEFERRED_LINE, "**deferred_d388_gates:** G03, G04")), "gate_deferred_mismatch");
  expectCode(
    fixture((text) => text.replace(REQUESTED_LINE, "**requested_not_selected_d388_gates:** G12")),
    "requested_gate_set_mismatch",
  );
  expectCode(
    fixture((text) =>
      text.replace(REQUESTED_LINE, "**requested_not_selected_d388_gates:** (none)"),
    ),
    "requested_gate_set_mismatch",
  );
  expectCode(
    fixture((text) =>
      text.replace("`G15` (source-authority policy", "`G16` (source-authority policy"),
    ),
    "derived_leg_gates_mismatch",
  );
});

test("negative: runtime_stop inversion and missing no-start directive", () => {
  expectCode(
    fixture((text) => text.replace("remains active for M208/S04", "lifted for M208/S04")),
    "runtime_stop_inverted",
  );
  expectCode(
    fixture((text) =>
      text.replace("**runtime_work:** not-started", "**runtime_work:** admitted for T04"),
    ),
    "no_start_directive_missing",
  );
  expectCode(
    fixture((text) => text.replace("**no_start_directive:**", "**start_directive:**")),
    "no_start_directive_missing",
  );
  expectCode(
    fixture((text) => text.replace("**runtime_demo:** not-proven", "**runtime_demo:** proven")),
    "runtime_proof_claimed",
  );
});

test("negative: missing required section and contract reference", () => {
  for (const [heading, replacement] of [
    ["## Sources checked", "## Sources"],
    ["## Owning surfaces", "## Surfaces"],
    ["## Non-claims", "## Nonclaims"],
    ["## Fail-closed boundary", "## Fail-closed"],
    ["## Marker semantics", "## Markers"],
    ["## Resume condition", "## Resume"],
    ["## Prohibited changes under this state", "## Forbidden changes under this state"],
    ["## Neighbouring admitted contours", "## Neighbours"],
  ]) {
    expectCode(fixture((text) => text.replace(heading, replacement)), "section_missing");
  }
  expectCode(
    fixture((text) => text.replaceAll(CONTRACT_PATH, "scripts/m208_s04_other.test.mjs")),
    "contract_reference_missing",
  );
});

test("negative: existing S04 and inherited S01/S02/S03 runtime surfaces", () => {
  for (const surface of S04_RUNTIME_SURFACES) {
    expectCode(doc, "s04_surface_present", { surfaceExists: (candidate) => candidate === surface });
  }
  for (const surface of S01_RUNTIME_SURFACES) {
    expectCode(doc, "s01_surface_present", { surfaceExists: (candidate) => candidate === surface });
  }
  for (const surface of S02_RUNTIME_SURFACES) {
    expectCode(doc, "s02_surface_present", { surfaceExists: (candidate) => candidate === surface });
  }
  for (const surface of S03_RUNTIME_SURFACES) {
    expectCode(doc, "s03_surface_present", { surfaceExists: (candidate) => candidate === surface });
  }
});

test("negative: lib.rs registrations of mod bounded_chain_replay and mod oracle_exam", () => {
  expectCode(doc, "lib_rs_registration_present", { libText: "pub mod bounded_chain_replay;\n" });
  expectCode(doc, "lib_rs_registration_present", { libText: "    mod oracle_exam ;\n" });
  const live = validateAdmission(doc);
  assert.ok(
    !codes(live).includes("lib_rs_registration_present"),
    "the live lib.rs must not register the S04 modules",
  );
});

test("negative: leave-row, provenance-guess, ADR and S04-owns-ADR claims", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        "It does not read the five `PC-X-*` leave rows as an admission",
        "The five leave rows are an admission",
      ),
    ),
    "leave_row_as_admission",
  );
  expectCode(fixture(claim("leave_row_as_admission")), "leave_row_as_admission");
  expectCode(
    fixture((text) =>
      text.replace("The ambiguity is **not** resolved by guesswork", "The ambiguity is settled"),
    ),
    "pc_x_provenance_resolved_by_guess",
  );
  expectCode(fixture(claim("pc_x_provenance_resolved_by_guess")), "pc_x_provenance_resolved_by_guess");
  expectCode(
    fixture((text) => text.replace("It does not reopen ADR-0028.", "ADR-0028 is reopened.")),
    "adr0028_reopened",
  );
  expectCode(fixture(claim("adr0028_reopened")), "adr0028_reopened");
  expectCode(
    fixture((text) => text.replace("does not amend that ADR", "amends that ADR")),
    "s04_owns_adr_claim",
  );
  expectCode(fixture(claim("s04_owns_adr_claim")), "s04_owns_adr_claim");
});

test("negative: minted chain, modified frozen artifact and minted glossary cell", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        "It does not mint a new edition chain beyond the frozen",
        "It mints chains freely",
      ),
    ),
    "new_chain_minted_beyond_frozen_packet",
  );
  expectCode(
    doc,
    "new_chain_minted_beyond_frozen_packet",
    { packetFiles: [...liveChainPackets, "prd/architecture/m208-s05-new-chain.yaml"] },
  );
  expectCode(fixture(claim("frozen_m201_artifact_modified")), "frozen_m201_artifact_modified");
  expectCode(doc, "frozen_m201_artifact_modified", {
    frozenM201Delta: ` M ${FROZEN_M201_ARTIFACT}`,
  });
  expectCode(
    fixture((text) =>
      text.replace(
        'mint an "oracle discrepancy" glossary first-cell',
        "mint the glossary cell",
      ),
    ),
    "oracle_discrepancy_glossary_cell_minted",
  );
  expectCode(doc, "oracle_discrepancy_glossary_cell_minted", {
    glossaryText: withMintedGlossaryCell(),
  });
});

test("negative: claimed checkout, M207 protocol as annotation and contour re-read", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        "bitemporal checkout (no legal_as_of / known_as_of / VIEW)",
        "bitemporal checkout with known_as_of",
      ),
    ),
    "known_as_of_checkout_claimed",
  );
  expectCode(fixture(claim("known_as_of_checkout_claimed")), "known_as_of_checkout_claimed");
  expectCode(
    fixture((text) =>
      text.replace("**absence** of accepted annotations", "presence of accepted annotations"),
    ),
    "m207_pilot_as_annotation_evidence",
  );
  expectCode(fixture(claim("m207_pilot_as_annotation_evidence")), "m207_pilot_as_annotation_evidence");
  expectCode(
    fixture((text) =>
      text.replace(
        "No PASS of any neighbouring surface may be quoted as S04 evidence",
        "A PASS of a neighbouring surface is S04 evidence",
      ),
    ),
    "neighbouring_contour_as_evidence",
  );
  expectCode(fixture(claim("neighbouring_contour_as_evidence")), "neighbouring_contour_as_evidence");
});

test("negative: runtime proof, marker, contract-pass and lock claims", () => {
  expectCode(
    fixture((text) => text.replace("runtime_proof: not-claimed", "runtime_proof: claimed")),
    "runtime_proof_claimed",
  );
  expectCode(
    fixture((text) => text.replaceAll("verify_marker: unreachable", "verify_marker: reachable")),
    "verify_marker_reachable_claim",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        "contract_pass_is_not_runtime_proof: true",
        "contract_pass_is_not_runtime_proof: false",
      ),
    ),
    "contract_pass_as_runtime_proof",
  );
  expectCode(
    fixture((text) =>
      text.replace("lock_is_not_runtime_proof: true", "lock_is_not_runtime_proof: false"),
    ),
    "lock_as_runtime_proof",
  );
  expectCode(fixture(claim("contract_pass_as_runtime_proof")), "contract_pass_as_runtime_proof");
  expectCode(fixture(claim("lock_as_runtime_proof")), "lock_as_runtime_proof");
});

test("negative: missing inherited S01/S02/S03 contracts", () => {
  expectCode(doc, "s01_contract_missing", { s01ContractExists: false });
  expectCode(doc, "s02_contract_missing", { s02ContractExists: false });
  expectCode(doc, "s03_contract_missing", { s03ContractExists: false });
});

test("negative: missing T02 no-start notes and their sentinels", () => {
  expectCode(
    fixture((text) => text.replace(T02_NOTE_HEADINGS[0], "## T02 note dropped")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replace(T02_NOTE_HEADINGS[1], "## T02 note dropped")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replace(T02_NOTE_HEADINGS[2], "## T02 note dropped")),
    "t02_note_missing",
  );
  expectCode(fixture((text) => text.replaceAll("f436a10e", "00000000")), "t02_note_missing");
  expectCode(fixture((text) => text.replaceAll("D508", "D999")), "t02_note_missing");
  expectCode(
    fixture((text) => text.replace("hostile_proof: deferred", "hostile_proof: proven")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replace("battery_proof: deferred", "battery_proof: proven")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replace("frozen_surface_proof: deferred", "frozen_surface_proof: proven")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replaceAll("runtime_work: not-started", "runtime_work: started")),
    "t02_note_missing",
  );
  expectCode(
    fixture((text) => text.replaceAll("`verdict=not-adopted`", "`verdict=not-granted`")),
    "t02_note_missing",
  );
  assert.deepEqual(t02NoteErrors(doc), [], "the live record must satisfy the T02 guard");
});

test("negative: matrix leave-row and M205 pin drift", () => {
  const driftedMatrix = liveMatrix.replace(
    "id: PC-X-SemanticService, family: leave,",
    "id: PC-X-SemanticService, family: take,",
  );
  assert.notEqual(driftedMatrix, liveMatrix, "the matrix fixture must change the file");
  expectCode(doc, "leave_row_as_admission", { matrixText: driftedMatrix });
  const gatedMatrix = liveMatrix.replace(
    "id: PC-X-MorphEngine, family: leave, vendor_type: MorphEngine, vendor_attr_or_kind: m_ru.dat, vendor_anchor: Pullenti/Morph/MorphEngine.cs:m_ru.dat, pullenti_behavior: vendor dictionary and license boundary, take_or_leave: leave, law_nexus_surface: none, owner_adr: ADR-0028, owner_crate_or_yaml: prd/architecture/npa-parsing-program.yaml, lifecycle: [proposed], d388_gates: [],",
    "id: PC-X-MorphEngine, family: leave, vendor_type: MorphEngine, vendor_attr_or_kind: m_ru.dat, vendor_anchor: Pullenti/Morph/MorphEngine.cs:m_ru.dat, pullenti_behavior: vendor dictionary and license boundary, take_or_leave: leave, law_nexus_surface: none, owner_adr: ADR-0028, owner_crate_or_yaml: prd/architecture/npa-parsing-program.yaml, lifecycle: [proposed], d388_gates: [G12],",
  );
  assert.notEqual(gatedMatrix, liveMatrix, "the gated-matrix fixture must change the file");
  expectCode(doc, "leave_row_as_admission", { matrixText: gatedMatrix });
  expectCode(doc, "requested_gate_set_mismatch", { matrixText: gatedMatrix });
  expectCode(doc, "self_minted_adoption", {
    pinTexts: {
      ...livePinTexts,
      [M205_S03_PIN]: livePinTexts[M205_S03_PIN].replace(
        "human_adoption: pending",
        "human_adoption: granted",
      ),
    },
  });
  expectCode(doc, "runtime_stop_inverted", {
    pinTexts: {
      ...livePinTexts,
      [M205_S04_PIN]: livePinTexts[M205_S04_PIN].replace(
        "runtime_stop_active: true",
        "runtime_stop_active: false",
      ),
    },
  });
});

test("negative: ADR-0028 edit or new M208 section", () => {
  expectCode(doc, "adr0028_reopened", { adr0028Delta: ` M ${ADR_0028}` });
  expectCode(doc, "adr0028_reopened", {
    adr0028Text: `${liveAdr0028}\n## M208/S04 amendment\n`,
  });
  const live = validateAdmission(doc);
  assert.ok(!codes(live).includes("adr0028_reopened"), "the live ADR-0028 must stay untouched");
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
    mutate: (text) => text.replace("**admission: not-adopted**", "**admission_state: pending**"),
  },
  {
    code: "verdict_ambiguous",
    mutate: (text) =>
      text.replace(
        "**admission: not-adopted**",
        "**admission: not-adopted**\n**admission: granted**",
      ),
  },
  { code: "sources_insufficient", mutate: (text) => text.replace(STRIP_SOURCE_ROWS, "") },
  {
    code: "source_unresolved",
    mutate: (text) =>
      text.replace(`| \`${PULLENTI_MATRIX}\` |`, "| `prd/architecture/m208-s04-missing.yaml` |"),
  },
  {
    code: "source_not_tracked",
    mutate: (text) => text.replace(`| \`${PULLENTI_MATRIX}\` |`, "| `/tmp/m208-s04-source.md` |"),
  },
  {
    code: "ignored_path_as_source",
    mutate: (text) =>
      text.replace(
        `| \`${PULLENTI_MATRIX}\` |`,
        "| `.gsd/phases/208-wrz6fg-temporal/208-04-PLAN.md` |",
      ),
  },
  {
    code: "source_hash_mismatch",
    mutate: (text) => text.replace(sha256(PULLENTI_MATRIX), "0".repeat(64)),
  },
  {
    code: "self_minted_adoption",
    mutate: (text) =>
      grantedText(text, "the M205 pins declare the vocabulary.", (next) =>
        next.replace(STRIP_SOURCE_ROWS, `${YAML_ONLY_ROWS}\n`),
      ),
  },
  {
    code: "owner_admission_ref_missing",
    mutate: (text) =>
      grantedText(text, "the owner approved the S04 scope verbally.", (next) =>
        next.replace("**owner_admission_ref:** none", "**owner_admission_ref:** verbal"),
      ),
  },
  {
    code: "integrity_pass_as_admission",
    mutate: (text) => grantedText(text, "M206 runtime battery integrity PASS authorises M208/S04."),
  },
  {
    code: "lock_as_admission",
    mutate: (text) =>
      grantedText(
        text,
        "D499 GSD_MILESTONE_LOCK authorises M208/S04 (interaction 00000000-0000-0000-0000-000000000000).",
      ),
  },
  {
    code: "s01_basis_not_adopted",
    mutate: (text) => text.replace(`| \`${S01_DOC}\` |`, `| \`${M206_ADMISSION}\` |`),
  },
  {
    code: "s02_basis_not_adopted",
    mutate: (text) => text.replace(`| \`${S02_DOC}\` |`, "| `prd/architecture/m208-s07.yaml` |"),
  },
  {
    code: "s03_basis_not_adopted",
    mutate: (text) => text.replace(`| \`${S03_DOC}\` |`, "| `prd/architecture/m208-s08.yaml` |"),
  },
  {
    code: "gate_outside_selected_baseline",
    mutate: (text) =>
      text
        .replace(SELECTED_LINE, "**selected_d388_gates:** G01, G02, G07, G14")
        .replace(
          DEFERRED_LINE,
          "**deferred_d388_gates:** G03, G04, G05, G06, G08, G09, G10, G11, G12, G13, G15, G16",
        ),
  },
  {
    code: "gate_deferred_mismatch",
    mutate: (text) => text.replace(DEFERRED_LINE, "**deferred_d388_gates:** G03, G04"),
  },
  {
    code: "requested_gate_set_mismatch",
    mutate: (text) => text.replace(REQUESTED_LINE, REQUESTED_LINE.replace("(empty set)", "G12")),
  },
  {
    code: "derived_leg_gates_mismatch",
    mutate: (text) =>
      text.replace("`G15` (source-authority policy", "`G16` (source-authority policy"),
  },
  {
    code: "runtime_stop_inverted",
    mutate: (text) => text.replace("remains active for M208/S04", "lifted for M208/S04"),
  },
  {
    code: "no_start_directive_missing",
    mutate: (text) => text.replace("**runtime_work:** not-started", "**runtime_work:** admitted"),
  },
  {
    code: "section_missing",
    mutate: (text) => text.replace("## Non-claims", "## Nonclaims"),
  },
  {
    code: "contract_reference_missing",
    mutate: (text) => text.replaceAll(CONTRACT_PATH, "scripts/m208_s04_other.test.mjs"),
  },
  {
    code: "s04_surface_present",
    options: { surfaceExists: (candidate) => candidate === S04_RUNTIME_SURFACES[0] },
  },
  {
    code: "s01_surface_present",
    options: { surfaceExists: (candidate) => candidate === S01_RUNTIME_SURFACES[0] },
  },
  {
    code: "s02_surface_present",
    options: { surfaceExists: (candidate) => candidate === S02_RUNTIME_SURFACES[0] },
  },
  {
    code: "s03_surface_present",
    options: { surfaceExists: (candidate) => candidate === S03_RUNTIME_SURFACES[0] },
  },
  { code: "lib_rs_registration_present", options: { libText: "mod bounded_chain_replay;\n" } },
  {
    code: "leave_row_as_admission",
    mutate: (text) =>
      text.replace(
        "It does not read the five `PC-X-*` leave rows as an admission",
        "The five leave rows are an admission",
      ),
  },
  {
    code: "pc_x_provenance_resolved_by_guess",
    mutate: (text) =>
      text.replace("The ambiguity is **not** resolved by guesswork", "The ambiguity is settled"),
  },
  {
    code: "adr0028_reopened",
    mutate: (text) => text.replace("It does not reopen ADR-0028.", "ADR-0028 is reopened."),
  },
  {
    code: "s04_owns_adr_claim",
    mutate: (text) => text.replace("does not amend that ADR", "amends that ADR"),
  },
  {
    code: "new_chain_minted_beyond_frozen_packet",
    mutate: (text) =>
      text.replace(
        "It does not mint a new edition chain beyond the frozen",
        "It mints chains freely",
      ),
  },
  {
    code: "frozen_m201_artifact_modified",
    options: { frozenM201Delta: ` M ${FROZEN_M201_ARTIFACT}` },
  },
  {
    code: "oracle_discrepancy_glossary_cell_minted",
    mutate: (text) =>
      text.replace('mint an "oracle discrepancy" glossary first-cell', "mint the glossary cell"),
  },
  {
    code: "known_as_of_checkout_claimed",
    mutate: (text) =>
      text.replace(
        "bitemporal checkout (no legal_as_of / known_as_of / VIEW)",
        "bitemporal checkout with known_as_of",
      ),
  },
  {
    code: "m207_pilot_as_annotation_evidence",
    mutate: (text) =>
      text.replace("**absence** of accepted annotations", "presence of accepted annotations"),
  },
  {
    code: "neighbouring_contour_as_evidence",
    mutate: (text) =>
      text.replace(
        "No PASS of any neighbouring surface may be quoted as S04 evidence",
        "A PASS of a neighbouring surface is S04 evidence",
      ),
  },
  {
    code: "runtime_proof_claimed",
    mutate: (text) => text.replace("runtime_proof: not-claimed", "runtime_proof: claimed"),
  },
  {
    code: "verify_marker_reachable_claim",
    mutate: (text) => text.replaceAll("verify_marker: unreachable", "verify_marker: reachable"),
  },
  {
    code: "contract_pass_as_runtime_proof",
    mutate: (text) =>
      text.replace(
        "contract_pass_is_not_runtime_proof: true",
        "contract_pass_is_not_runtime_proof: false",
      ),
  },
  {
    code: "lock_as_runtime_proof",
    mutate: (text) =>
      text.replace("lock_is_not_runtime_proof: true", "lock_is_not_runtime_proof: false"),
  },
  { code: "s01_contract_missing", options: { s01ContractExists: false } },
  { code: "s02_contract_missing", options: { s02ContractExists: false } },
  { code: "s03_contract_missing", options: { s03ContractExists: false } },
  {
    code: "t02_note_missing",
    mutate: (text) => text.replace(T02_NOTE_HEADINGS[0], "## T02 note dropped"),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const text = entry.mutate ? entry.mutate(doc) : doc;
    if (entry.mutate) {
      assert.notEqual(text, doc, `${entry.code}: the mutation must actually change the record`);
    }
    const result = validateAdmission(text, entry.options || {});
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

test("M208 S04 checkpoint markers", () => {
  const result = validateAdmission(doc);
  assert.deepEqual(result.errors, [], `checkpoint errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.verdict, "not-adopted");
  const surfacesPresent = [
    ...S04_RUNTIME_SURFACES,
    ...S01_RUNTIME_SURFACES,
    ...S02_RUNTIME_SURFACES,
    ...S03_RUNTIME_SURFACES,
  ].filter((surface) => repoExists(surface)).length;
  assert.equal(surfacesPresent, 0, "runtime_surfaces_present must be 0");
  console.log("M208_S04_ADMISSION_OK");
  console.log(`admission_verdict=${result.verdict}`);
  console.log("M208_S04_ADMISSION_NOT_GRANTED");
  console.log("M208_S04_GATES_OK");
  console.log("M208_S04_ADMISSION_NO_START_OK");
  console.log(`runtime_surfaces_present=${surfacesPresent}`);
});
