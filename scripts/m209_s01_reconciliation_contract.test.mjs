// M209/S01 R035 gate-reconciliation contract (T05).
//
// Offline and fail-closed. The reconciliation artifact is the claim; this
// contract re-derives every load-bearing fact from the LIVE repository:
//   - the seven gate ids are re-parsed from README §R035, from
//     ONTOLOGY_PROMOTION_RULES inside scripts/verify-architecture-graph.py, from
//     the frozen M202 artifact and from the T01 register, and all four sets must
//     agree with each other and with the recorded lists;
//   - the recorded derived extras (out_of_register_gate_ids) are re-derived from
//     claims_ledger.md table cells and must match exactly;
//   - the GATE-G015 divergence is re-read from three live locators
//     (architecture_items.jsonl status, claims_ledger.md quarantined Status
//     column, M202 promotion_gates[].gate_verdict) and may not be smoothed;
//   - every recorded source sha256/bytes is compared against the live bytes, and
//     the two architecture projections are additionally checked through
//     `git status --porcelain` so a silent regeneration is visible even if the
//     hash was updated alongside it;
//   - every frozen M202 inventory count is re-read verbatim and must be displaced
//     by a named register quantifier;
//   - the architecture verifier baseline is asserted to stay a pre-existing fail
//     (D537) and is never relabelled as pass.
//
// Q3 rework (Q3-M202-FROZEN-PIN-SCOPE, 2026-09-22): crates/ln-kb-ontology/tests/
// r035_proof_gate.rs carries NO PROOF_GATE_JSON_SHA256 / PROOF_GATE_JSON_BYTES
// constant, so the four inputs that DO carry Rust constants (m202-s02, m202-s03,
// kb-hierarchy-registry-admissions.yaml, kb-hierarchy-registry.yaml) are checked
// against those constants, while M202 is checked as a captured-at baseline that
// must be explicitly labelled not-Rust-anchored and is protected instead by the
// suite's semantic pins. This contract never invents a Rust constant and never
// edits that frozen file.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file proof)
// and `git status --porcelain` (frozen-input proof). No cargo, no network, and no
// `.gsd` / ignored / absolute path is ever read as evidence.
// scripts/verify-architecture-graph.py is parsed as text only and never run: its
// own baseline is fail/256 diagnostics (D537).
//
// Run: node --test scripts/m209_s01_reconciliation_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const RECON = "prd/migration/rust-evidence/m209-s01-r035-gate-reconciliation.json";
const CONTRACT_PATH = "scripts/m209_s01_reconciliation_contract.test.mjs";
const README = "prd/architecture/README.md";
const VERIFIER = "scripts/verify-architecture-graph.py";
const M202 = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
const M202_S02 = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_S03 = "prd/migration/rust-evidence/m202-s03-registry-regeneration.json";
const ITEMS = "prd/architecture/architecture_items.jsonl";
const EDGES = "prd/architecture/architecture_edges.jsonl";
const LEDGER = "prd/architecture/claims_ledger.md";
const ADMISSIONS_YAML = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const REGISTRY_YAML = "prd/architecture/kb-hierarchy-registry.yaml";
const REGISTER = "prd/architecture/m209-s01-r035-gate-register.json";
const PUNKT_DOC = "prd/architecture/m209-s01-punkt-decision.md";
const RUST_PIN = "crates/ln-kb-ontology/tests/r035_proof_gate.rs";

const RECON_SCHEMA_VERSION = "law-nexus/m209-r035-gate-reconciliation/v1";

// The seven canonical R035 promotion gates (D536). The four live parses below
// must agree with this constant; a drift in any enforcement surface is a failure.
const CANONICAL_GATE_IDS = [
  "GATE-AKOMA-FRBR-NORMALIZATION",
  "GATE-LKIF-DEONTIC-BENCHMARK",
  "GATE-RUSLEGALCORE-SCOPE",
  "GATE-BFO-GOST-ALIGNMENT",
  "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
  "GATE-G015",
  "GATE-PILOT-SCALE-READINESS",
];

// Recorded source key -> the repository-relative path it must name. The keys are
// the artifact's own source slots; a missing or re-pointed slot fails closed.
const EXPECTED_SOURCE_PATHS = {
  readme_gate_table: README,
  enforcement_rules: VERIFIER,
  frozen_m202: M202,
  m202_s02_candidates: M202_S02,
  m202_s03_regeneration: M202_S03,
  architecture_items: ITEMS,
  architecture_edges: EDGES,
  claims_ledger: LEDGER,
  admissions_yaml: ADMISSIONS_YAML,
  registry_yaml: REGISTRY_YAML,
  gate_register: REGISTER,
  punkt_decision_record: PUNKT_DOC,
};

const PROJECTION_PATHS = [ITEMS, EDGES];
const RUST_ANCHORED_PATHS = [M202_S02, M202_S03, ADMISSIONS_YAML, REGISTRY_YAML];
const FROZEN_INPUTS = [M202, M202_S02, M202_S03, ADMISSIONS_YAML, REGISTRY_YAML];
const DELTA_PATHS = [...FROZEN_INPUTS, ...PROJECTION_PATHS];

// Raw registry/projection states -> disposition states. Mirrors the artifact's
// normalization_vocabulary, which is asserted against this constant.
const NORMALIZATION = {
  blocked: "unsatisfied",
  unsatisfied: "unsatisfied",
  superseded: "superseded",
  deferred: "deferred",
  satisfied: "satisfied",
  rejected: "rejected",
};

const CLOSED_NORMALIZED_STATES = ["unsatisfied", "superseded", "deferred", "satisfied", "rejected"];

const REQUIRED_G015_FACETS = ["registry_status", "derived_view_status", "frozen_snapshot_verdict"];

// Bare status tokens as they appear in claims_ledger.md table cells.
const LEDGER_STATUS_TOKENS = new Set([
  "blocked",
  "superseded",
  "deferred",
  "satisfied",
  "unsatisfied",
  "rejected",
  "out-of-scope",
]);

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The complete fail-closed code set. The `## Fail-closed codes` comment block
// below is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "gate_ids_disagree",
  "register_ids_mismatch",
  "source_bytes_mismatch",
  "source_hash_mismatch",
  "architecture_items_regenerated",
  "architecture_edges_regenerated",
  "m202_modified",
  "hidden_frozen_input_modified",
  "gate_g015_conflict_smoothed",
  "conflict_locator_missing",
  "quantifier_is_inventory_count",
  "displacement_missing",
  "inventory_count_as_proof",
  "punkt_row_admitted",
  "claims_ledger_as_authority",
  "verifier_baseline_relabelled_as_pass",
  "r035_promoted",
  "ignored_path_as_source",
];

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// gate_ids_disagree: the four live gate-id sets, the recorded lists, the resolved disjunction or the derived ledger extras drifted apart.
// register_ids_mismatch: the register gate ids (live or recorded) are not exactly the canonical seven.
// source_bytes_mismatch: a recorded non-frozen source byte count differs from the live file.
// source_hash_mismatch: a recorded non-frozen source sha256 differs from the live file, or a source slot is missing/renamed.
// architecture_items_regenerated: architecture_items.jsonl no longer matches its recorded sha256 or carries a worktree delta.
// architecture_edges_regenerated: architecture_edges.jsonl no longer matches its recorded sha256 or carries a worktree delta.
// m202_modified: the frozen M202 captured-at baseline, its semantic pins or its worktree state drifted.
// hidden_frozen_input_modified: one of the four Rust-anchored frozen inputs drifted from its sha256/bytes constant or its recorded value.
// gate_g015_conflict_smoothed: the GATE-G015 divergence was collapsed to fewer than two distinct normalized states.
// conflict_locator_missing: a GATE-G015 state is malformed, unlocatable or no longer matches its live source value, or the resolution is not the deferred decision-free form.
// quantifier_is_inventory_count: an inventory count stands as a quantifier, or a recorded quantifier set drifted from the register.
// displacement_missing: an inventory counter has no named displacement, or its verbatim value drifted from frozen M202.
// inventory_count_as_proof: the artifact claims an inventory count can stand as gate proof.
// punkt_row_admitted: a punkt admission row exists anywhere, or the recorded verdict/row count is not the fail-closed zero.
// claims_ledger_as_authority: the derived ledger view was given authority or stopped being marked derived non-authoritative.
// verifier_baseline_relabelled_as_pass: the pre-existing verifier baseline was relabelled, made internally inconsistent or made a stopping condition.
// r035_promoted: R035 left active, a gate left the non-promoted disposition set, or the recorded disposition map drifted.
// ignored_path_as_source: a cited source path is an ignored overlay, absolute or traversing.
// DOCUMENTED_CODES_END

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
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

function repoBytes(relativePath) {
  return readFileSync(path.join(root, relativePath)).length;
}

// One `git status --porcelain` call over the frozen set, attributed per path. An
// empty value per path means that tracked artifact carries no worktree delta; a
// git failure yields a non-empty sentinel so the check fails closed instead of
// silently passing.
function frozenDeltaByPath(paths) {
  let raw;
  try {
    raw = execFileSync("git", ["status", "--porcelain", "--", ...paths], {
      cwd: root,
      encoding: "utf8",
    }).trim();
  } catch {
    raw = "git status failed";
  }
  const deltas = new Map();
  for (const p of paths) {
    if (raw === "git status failed") {
      deltas.set(p, raw);
      continue;
    }
    const hit = raw.split("\n").find((line) => line.includes(p));
    deltas.set(p, hit ?? "");
  }
  return deltas;
}

// ---------------------------------------------------------------------------
// small helpers
// ---------------------------------------------------------------------------

function count(haystack, needle) {
  if (typeof haystack !== "string" || needle.length === 0) return 0;
  let total = 0;
  let index = haystack.indexOf(needle);
  while (index !== -1) {
    total += 1;
    index = haystack.indexOf(needle, index + needle.length);
  }
  return total;
}

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function sameSet(a, b) {
  const sa = [...new Set(a)].sort();
  const sb = [...new Set(b)].sort();
  return sa.length === sb.length && sa.every((value, index) => value === sb[index]);
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function nonEmptyLines(text) {
  return text.split("\n").filter((line) => line.trim().length > 0).length;
}

function isRefusedPath(candidate) {
  if (!nonEmpty(candidate)) return true;
  if (candidate.startsWith("/")) return true;
  if (candidate.split("/").includes("..")) return true;
  return IGNORED_SOURCE_PREFIXES.some((prefix) => candidate.startsWith(prefix));
}

// ---------------------------------------------------------------------------
// live-surface parsers (text only; the verifier is never run)
// ---------------------------------------------------------------------------

// README §R035 promotion-gate table: the required gate ids (a cell may hold a
// disjunction, in which case every id in it counts).
function parseReadmeGateIds(text) {
  const lines = text.split("\n");
  const ids = new Set();
  const headerIndex = lines.findIndex(
    (line) => line.includes("Required promotion gate") && line.includes("Minimum validated proof level"),
  );
  if (headerIndex === -1) return ids;
  for (let i = headerIndex + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim().startsWith("|")) break;
    const cells = line.split("|").map((cell) => cell.trim());
    if ((cells[1] ?? "").replace(/\s/g, "").length === 0) continue;
    if (/^-+$/.test((cells[1] ?? "").replace(/\s/g, ""))) continue;
    const gateCell = cells[3] ?? "";
    for (const match of gateCell.matchAll(/(GATE-[A-Za-z0-9-]+)/g)) ids.add(match[1]);
  }
  return ids;
}

// ONTOLOGY_PROMOTION_RULES: the union of every rule's required_gate_ids.
function parseVerifierGateIds(text) {
  const ids = new Set();
  const block = text.match(/ONTOLOGY_PROMOTION_RULES[^=]*=\s*\(([\s\S]*?)\n\)\n/);
  const rulesText = block ? block[1] : "";
  for (const match of rulesText.matchAll(/"required_gate_ids":\s*\(([^)]*)\)/g)) {
    for (const gate of match[1].matchAll(/(GATE-[A-Za-z0-9-]+)/g)) ids.add(gate[1]);
  }
  return ids;
}

// DERIVED_NON_AUTHORITATIVE_PATH_PATTERNS: paths the verifier itself refuses to
// treat as tracked evidence anchors.
function parseVerifierDerivedPatterns(text) {
  const block = text.match(/DERIVED_NON_AUTHORITATIVE_PATH_PATTERNS\s*=\s*\(([\s\S]*?)\n\)/);
  if (!block) return [];
  return [...block[1].matchAll(/"([^"]+)"/g)].map((match) => match[1]);
}

// The Rust pin suite: sha256 / bytes constants keyed by their full constant name.
function parseRustPins(text) {
  const sha = new Map();
  const bytes = new Map();
  for (const match of String(text).matchAll(
    /const\s+([A-Z0-9_]+_SHA256):\s*&str\s*=\s*"([a-f0-9]{64})"/g,
  )) {
    sha.set(match[1], match[2]);
  }
  for (const match of String(text).matchAll(/const\s+([A-Z0-9_]+)_BYTES:\s*usize\s*=\s*(\d+)/g)) {
    bytes.set(`${match[1]}_BYTES`, Number(match[2]));
  }
  return { sha, bytes };
}

function parseM202GateIds(text) {
  const parsed = safeJson(text);
  if (!parsed || !Array.isArray(parsed.promotion_gates)) return new Set();
  return new Set(parsed.promotion_gates.map((gate) => gate?.gate_id).filter(nonEmpty));
}

function parseRegister(text) {
  return safeJson(text);
}

function parseRegisterGateIds(text) {
  const parsed = safeJson(text);
  if (!parsed || !Array.isArray(parsed.gates)) return new Set();
  return new Set(parsed.gates.map((gate) => gate?.gate_id).filter(nonEmpty));
}

// architecture_items.jsonl: the status facet of one record, plus its line.
function parseItemsStatus(text, recordId) {
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    if (!lines[i].trim()) continue;
    const record = safeJson(lines[i]);
    if (record?.id === recordId) {
      return { status: record.status, line: i + 1 };
    }
  }
  return null;
}

// claims_ledger.md table rows: every GATE-* id that appears as a whole cell.
function parseLedgerGateIds(text) {
  const ids = new Set();
  for (const line of text.split("\n")) {
    if (!line.trim().startsWith("|")) continue;
    for (const cell of line.split("|")) {
      const trimmed = cell.trim().replace(/^`|`$/g, "");
      if (/^GATE-[A-Za-z0-9-]+$/.test(trimmed)) ids.add(trimmed);
    }
  }
  return ids;
}

// claims_ledger.md: the Status cell of a table row identified by its id cell.
function parseLedgerGateStatus(text, gateId) {
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim().startsWith("|")) continue;
    const cells = line.split("|").map((cell) => cell.trim().replace(/^`|`$/g, ""));
    if (!cells.includes(gateId)) continue;
    const status = cells.find((cell) => LEDGER_STATUS_TOKENS.has(cell));
    if (status) return { status, line: i + 1 };
  }
  return null;
}

// The line holding the GATE-G015 promotion verdict inside the frozen M202 file.
function parseM202VerdictLine(text, gateId) {
  const lines = text.split("\n");
  const gateLine = lines.findIndex((line) => line.includes(`"gate_id": "${gateId}"`));
  if (gateLine === -1) return null;
  for (let i = gateLine; i < Math.min(gateLine + 4, lines.length); i += 1) {
    if (lines[i].includes('"gate_verdict":')) return i + 1;
  }
  return null;
}

// ---------------------------------------------------------------------------
// live inputs (read once)
// ---------------------------------------------------------------------------

const liveReconText = readRepo(RECON);
const liveRecon = safeJson(liveReconText);
const liveReadme = readRepo(README);
const liveVerifier = readRepo(VERIFIER);
const liveM202 = readRepo(M202);
const liveM202S03 = readRepo(M202_S03);
const liveItems = readRepo(ITEMS);
const liveEdges = readRepo(EDGES);
const liveLedger = readRepo(LEDGER);
const liveAdmissions = readRepo(ADMISSIONS_YAML);
const liveRegistry = readRepo(REGISTRY_YAML);
const liveRegisterText = readRepo(REGISTER);
const liveRust = readRepo(RUST_PIN);
const liveDelta = frozenDeltaByPath(DELTA_PATHS);

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateReconciliation(recon, overrides = {}) {
  const pick = (key, fallback) => (overrides[key] === undefined ? fallback : overrides[key]);
  const readmeText = pick("readmeText", liveReadme);
  const verifierText = pick("verifierText", liveVerifier);
  const m202Text = pick("m202Text", liveM202);
  const m202S03Text = pick("m202S03Text", liveM202S03);
  const rustText = pick("rustText", liveRust);
  const itemsText = pick("itemsText", liveItems);
  const edgesText = pick("edgesText", liveEdges);
  const ledgerText = pick("ledgerText", liveLedger);
  const admissionsText = pick("admissionsText", liveAdmissions);
  const registryText = pick("registryText", liveRegistry);
  const registerText = pick("registerText", liveRegisterText);
  const delta = pick("delta", liveDelta);
  const readBytes = pick("bytes", repoBytes);
  const readHash = pick("hash", sha256);

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  const sources = recon?.sources ?? {};
  const agreement = recon?.gate_id_agreement ?? {};

  // (1) recorded sources: path trust, live byte/hash fidelity, class-specific
  // drift codes.
  for (const [key, expectedPath] of Object.entries(EXPECTED_SOURCE_PATHS)) {
    const entry = sources[key];
    if (!entry || typeof entry !== "object") {
      add("source_hash_mismatch", `${key}: source slot missing`);
      continue;
    }
    const recordedPath = entry.path;
    if (isRefusedPath(recordedPath)) {
      add("ignored_path_as_source", `${key}: ${String(recordedPath)}`);
      continue;
    }
    if (recordedPath !== expectedPath) {
      add("source_hash_mismatch", `${key}: ${recordedPath} != ${expectedPath}`);
      continue;
    }
    if (!repoExists(recordedPath)) {
      add("source_hash_mismatch", `${key}: ${recordedPath} missing on disk`);
      continue;
    }
    const liveHash = readHash(recordedPath);
    const liveByteCount = readBytes(recordedPath);
    if (PROJECTION_PATHS.includes(recordedPath)) {
      const code = recordedPath === ITEMS
        ? "architecture_items_regenerated"
        : "architecture_edges_regenerated";
      if (liveHash !== entry.sha256) add(code, `${recordedPath}: sha drifted`);
      if (liveByteCount !== entry.bytes) add(code, `${recordedPath}: bytes drifted`);
      if (nonEmpty(delta.get(recordedPath))) add(code, `${recordedPath}: worktree delta ${delta.get(recordedPath)}`);
    } else if (recordedPath === M202) {
      if (liveHash !== entry.sha256) add("m202_modified", "frozen M202 sha drifted from the captured baseline");
      if (liveByteCount !== entry.bytes) add("m202_modified", "frozen M202 bytes drifted from the captured baseline");
      if (nonEmpty(delta.get(recordedPath))) add("m202_modified", `worktree delta ${delta.get(recordedPath)}`);
    } else if (RUST_ANCHORED_PATHS.includes(recordedPath)) {
      if (liveHash !== entry.sha256) add("hidden_frozen_input_modified", `${recordedPath}: sha drifted`);
      if (liveByteCount !== entry.bytes) add("hidden_frozen_input_modified", `${recordedPath}: bytes drifted`);
      if (nonEmpty(delta.get(recordedPath))) {
        add("hidden_frozen_input_modified", `${recordedPath}: worktree delta ${delta.get(recordedPath)}`);
      }
    } else {
      if (liveByteCount !== entry.bytes) {
        add("source_bytes_mismatch", `${recordedPath}: recorded ${entry.bytes} != live ${liveByteCount}`);
      }
      if (liveHash !== entry.sha256) add("source_hash_mismatch", `${recordedPath}: sha drifted`);
    }
  }

  // (2) gate-id agreement across the four live sources plus the recorded lists,
  // the resolved disjunction and the derived ledger extras.
  const readmeIds = parseReadmeGateIds(readmeText);
  const ontologyIds = parseVerifierGateIds(verifierText);
  const m202Ids = parseM202GateIds(m202Text);
  const registerIds = parseRegisterGateIds(registerText);
  for (const [name, ids] of [
    ["readme", readmeIds],
    ["ontology_rules", ontologyIds],
    ["frozen_m202", m202Ids],
    ["register", registerIds],
  ]) {
    if (!sameSet([...ids], CANONICAL_GATE_IDS)) {
      add("gate_ids_disagree", `${name}: ${[...ids].join(",")}`);
    }
  }
  const recordedLivePairs = [
    ["readme_required_gate_ids", readmeIds],
    ["ontology_rules_required_gate_ids", ontologyIds],
    ["frozen_m202_gate_ids", m202Ids],
    ["register_gate_ids", registerIds],
  ];
  for (const [key, ids] of recordedLivePairs) {
    const recorded = Array.isArray(agreement[key]) ? agreement[key] : [];
    if (!sameSet(recorded, [...ids])) add("gate_ids_disagree", `${key}: recorded != live`);
  }
  if (!sameSet(agreement.canonical_gate_ids ?? [], CANONICAL_GATE_IDS)) {
    add("gate_ids_disagree", "canonical_gate_ids is not the canonical seven");
  }
  if (agreement.agreement !== true) add("gate_ids_disagree", "agreement must be true");
  if (!Array.isArray(agreement.differences) || agreement.differences.length !== 0) {
    add("gate_ids_disagree", "differences must be empty");
  }
  const ledgerIds = parseLedgerGateIds(ledgerText);
  const derivedExtras = [...ledgerIds]
    .filter((id) => !readmeIds.has(id) && !ontologyIds.has(id))
    .sort();
  const recordedExtras = (agreement.out_of_register_gate_ids ?? [])
    .map((entry) => entry?.gate_id)
    .sort();
  if (!sameSet(derivedExtras, recordedExtras)) {
    add("gate_ids_disagree", `extras ${derivedExtras.join(",")} != ${recordedExtras.join(",")}`);
  }
  for (const entry of agreement.out_of_register_gate_ids ?? []) {
    if (!nonEmpty(entry?.reason)) add("gate_ids_disagree", `extras reason missing for ${entry?.gate_id}`);
  }
  const disjunction = agreement.resolved_disjunction ?? {};
  if (disjunction.promotion !== false) add("gate_ids_disagree", "disjunction must not promote");
  if (!sameSet(disjunction.readme_disjunction ?? [], ["GATE-G015", "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"])) {
    add("gate_ids_disagree", "readme disjunction drifted");
  }
  if (!sameSet(disjunction.ontology_rules_required_gate_ids ?? [], ["GATE-G015", "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"])) {
    add("gate_ids_disagree", "rules disjunction drifted");
  }

  // (3) the register itself must carry exactly the canonical seven.
  const liveRegisterObj = parseRegister(registerText);
  if (!Array.isArray(liveRegisterObj?.gates) || liveRegisterObj.gates.length !== 7) {
    add("register_ids_mismatch", "register does not carry exactly seven gate rows");
  }
  if (!sameSet([...registerIds], CANONICAL_GATE_IDS)) add("register_ids_mismatch", "live register ids");
  if (!sameSet(agreement.register_gate_ids ?? [], CANONICAL_GATE_IDS)) {
    add("register_ids_mismatch", "recorded register ids");
  }

  // (4) the GATE-G015 divergence: two distinct normalized states, one locator per
  // state, faithful to live sources, and deferred without a decision.
  const conflict = recon?.gate_g015_state_conflict ?? {};
  const states = Array.isArray(conflict.recorded_states) ? conflict.recorded_states : [];
  const normalized = new Set();
  for (const state of states) {
    const facet = state?.facet;
    if (!nonEmpty(facet) || !nonEmpty(state?.raw_value) || !nonEmpty(state?.normalized_state)) {
      add("conflict_locator_missing", `malformed state ${String(facet)}`);
      continue;
    }
    if (!nonEmpty(state?.source_path) || !nonEmpty(state?.selector)) {
      add("conflict_locator_missing", `${facet}: path/selector missing`);
    } else if (isRefusedPath(state.source_path)) {
      add("ignored_path_as_source", `${facet}: ${state.source_path}`);
    }
    if (typeof state?.line !== "number" || state.line <= 0) {
      add("conflict_locator_missing", `${facet}: no line locator`);
    }
    if (!CLOSED_NORMALIZED_STATES.includes(state.normalized_state)) {
      add("conflict_locator_missing", `${facet}: unknown normalized state ${state.normalized_state}`);
    }
    if (NORMALIZATION[state.raw_value] !== state.normalized_state) {
      add("conflict_locator_missing", `${facet}: ${state.raw_value} -> ${state.normalized_state}`);
    }
    normalized.add(state.normalized_state);
  }
  // The three facets are owned by this contract, never by the artifact: a
  // shrunk declared list must not be able to switch the requirement off.
  for (const facet of REQUIRED_G015_FACETS) {
    if (!states.some((state) => state?.facet === facet)) {
      add("conflict_locator_missing", `required facet missing: ${facet}`);
    }
  }
  if (!sameSet(conflict.required_facets ?? [], REQUIRED_G015_FACETS)) {
    add("conflict_locator_missing", "declared required_facets != the canonical three");
  }
  if (normalized.size < 2) {
    add("gate_g015_conflict_smoothed", `distinct normalized states = ${[...normalized].join(",")}`);
  }
  if (!sameSet(conflict.distinct_normalized_states ?? [], [...normalized])) {
    add("gate_g015_conflict_smoothed", "declared distinct states != derived");
  }
  if (conflict.conflict !== true) add("gate_g015_conflict_smoothed", "conflict flag must be true");
  if (conflict.resolution !== "deferred-to-individual-decision") {
    add("conflict_locator_missing", `resolution=${conflict.resolution}`);
  }
  if (!("decision_ref" in conflict) || conflict.decision_ref !== null) {
    add("conflict_locator_missing", "decision_ref must be null");
  }
  const m202Obj = safeJson(m202Text);
  const itemsStatus = parseItemsStatus(itemsText, "GATE-G015");
  const ledgerStatus = parseLedgerGateStatus(ledgerText, "GATE-G015");
  const m202VerdictLine = parseM202VerdictLine(m202Text, "GATE-G015");
  const g015Verdict = (m202Obj?.promotion_gates ?? []).find((gate) => gate?.gate_id === "GATE-G015")?.gate_verdict;
  const liveFacets = [
    ["registry_status", itemsStatus?.status, itemsStatus?.line],
    ["derived_view_status", ledgerStatus?.status, ledgerStatus?.line],
    ["frozen_snapshot_verdict", g015Verdict, m202VerdictLine],
  ];
  for (const [facet, liveRaw, liveLine] of liveFacets) {
    const state = states.find((candidate) => candidate?.facet === facet);
    if (!state) continue;
    if (!nonEmpty(liveRaw)) {
      add("conflict_locator_missing", `${facet}: live value not found`);
      continue;
    }
    if (state.raw_value !== liveRaw) {
      add("conflict_locator_missing", `${facet}: recorded ${state.raw_value} != live ${liveRaw}`);
    }
    if (typeof liveLine === "number" && state.line !== liveLine) {
      add("conflict_locator_missing", `${facet}: recorded line ${state.line} != live line ${liveLine}`);
    }
  }
  const bucket = conflict.readme_safe_bucket ?? {};
  if (bucket.is_gate_state !== false) {
    add("gate_g015_conflict_smoothed", "README safe bucket must be excluded from gate states");
  }

  // (5) frozen pins: four Rust-anchored inputs vs their constants, plus M202 as a
  // captured-at baseline whose semantic pins must hold.
  const rustPins = parseRustPins(rustText);
  const pins = recon?.frozen_pins ?? {};
  const anchored = Array.isArray(pins.rust_anchored) ? pins.rust_anchored : [];
  if (anchored.length !== RUST_ANCHORED_PATHS.length) {
    add("hidden_frozen_input_modified", `rust_anchored entries=${anchored.length}`);
  }
  const anchoredPaths = new Set();
  for (const pin of anchored) {
    const pinPath = pin?.path;
    if (!RUST_ANCHORED_PATHS.includes(pinPath)) {
      add("hidden_frozen_input_modified", `unknown anchored path ${String(pinPath)}`);
      continue;
    }
    anchoredPaths.add(pinPath);
    const rustSha = rustPins.sha.get(pin?.rust_sha_constant);
    const rustByteCount = rustPins.bytes.get(pin?.rust_bytes_constant);
    if (!rustSha || rustByteCount === undefined) {
      add("hidden_frozen_input_modified", `${pinPath}: Rust constant ${String(pin?.rust_sha_constant)} missing`);
      continue;
    }
    if (pin.sha256 !== rustSha) add("hidden_frozen_input_modified", `${pinPath}: recorded sha != ${pin.rust_sha_constant}`);
    if (pin.bytes !== rustByteCount) add("hidden_frozen_input_modified", `${pinPath}: recorded bytes != ${pin.rust_bytes_constant}`);
    if (pin.anchored !== true) add("hidden_frozen_input_modified", `${pinPath}: anchored flag must be true`);
    if (repoExists(pinPath)) {
      if (readHash(pinPath) !== rustSha) add("hidden_frozen_input_modified", `${pinPath}: live sha != Rust constant`);
      if (readBytes(pinPath) !== rustByteCount) add("hidden_frozen_input_modified", `${pinPath}: live bytes != Rust constant`);
    } else {
      add("hidden_frozen_input_modified", `${pinPath}: missing on disk`);
    }
  }
  for (const pinPath of RUST_ANCHORED_PATHS) {
    if (!anchoredPaths.has(pinPath)) add("hidden_frozen_input_modified", `${pinPath}: not covered by a Rust pin`);
  }
  const baseline = pins.captured_at_baseline_not_rust_anchored ?? {};
  if (baseline.path !== M202) add("m202_modified", `baseline path ${String(baseline.path)}`);
  if (baseline.anchored !== false) add("m202_modified", "M202 must be declared not Rust-anchored");
  if (baseline.rust_sha_constant !== null || baseline.rust_bytes_constant !== null) {
    add("m202_modified", "M202 must not claim a Rust sha/bytes constant");
  }
  if (!/captured-at/i.test(String(baseline.anchor_kind)) || !/not[- ]?rust[- ]?anchored/i.test(String(baseline.anchor_kind))) {
    add("m202_modified", "M202 baseline must be labelled captured-at-not-rust-anchored");
  }
  if (baseline.sha256 !== readHash(M202) || baseline.bytes !== readBytes(M202)) {
    add("m202_modified", "M202 captured-at baseline sha/bytes drifted from the live file");
  }
  if (/PROOF_GATE_JSON_SHA256|PROOF_GATE_JSON_BYTES/.test(rustText)) {
    add("m202_modified", "a PROOF_GATE_JSON constant now exists; the captured-at story is invalid");
  }
  const declaredPins = baseline.semantic_pins ?? {};
  if (!m202Obj) {
    add("m202_modified", "frozen M202 is unreadable");
  } else {
    if (count(m202Text, '"gate_id":') !== 7) add("m202_modified", "M202 gate_id count != 7");
    if (count(m202Text, '"gate_verdict": "unsatisfied"') !== 7) {
      add("m202_modified", "M202 unsatisfied gate verdict count != 7");
    }
    for (const banned of declaredPins.banned_gate_verdict_substrings ?? []) {
      if (count(m202Text, banned) !== 0) add("m202_modified", `banned substring present: ${banned}`);
    }
    if (count(m202Text, '"validated"') !== 0) add("m202_modified", "bare validated value present");
    if (count(m202Text, '"authoritative": true') !== 0) add("m202_modified", "authoritative true present");
    if (m202Obj.disposition !== "active") add("m202_modified", `disposition=${m202Obj.disposition}`);
    if (m202Obj.disposition_decision !== "D430") add("m202_modified", `disposition_decision=${m202Obj.disposition_decision}`);
    if (m202Obj.coverage_verdict !== "incomplete-because-promotion-gates-unsatisfied") {
      add("m202_modified", `coverage_verdict=${m202Obj.coverage_verdict}`);
    }
    if (m202Obj.mapping_counts?.punkt_admitted !== 0) add("m202_modified", "M202 punkt_admitted != 0");
    if (!Array.isArray(m202Obj.admitted_cc) || m202Obj.admitted_cc.length !== 3) {
      add("m202_modified", "M202 admitted_cc length != 3");
    }
    for (const hex of Object.keys(declaredPins.external_sha_hex_occurrences ?? {})) {
      if (count(m202Text, hex) !== 1) add("m202_modified", `external sha hex ${hex.slice(0, 12)} occurrence != 1`);
    }
    if (declaredPins.gate_id_count !== 7 || declaredPins.unsatisfied_gate_verdict_count !== 7) {
      add("m202_modified", "declared semantic pin counts drifted");
    }
    if (declaredPins.forbidden_substring_occurrences !== 0) {
      add("m202_modified", "declared forbidden-substring occurrence count must be 0");
    }
    if (declaredPins.bare_validated_value_occurrences !== 0) {
      add("m202_modified", "declared bare-validated occurrence count must be 0");
    }
    if (declaredPins.disposition !== "active" || declaredPins.disposition_decision !== "D430") {
      add("m202_modified", "declared disposition pins drifted");
    }
    if (declaredPins.authoritative !== false || declaredPins.punkt_admitted !== 0) {
      add("m202_modified", "declared authoritative/punkt pins drifted");
    }
    if (declaredPins.admitted_cc_count !== 3) add("m202_modified", "declared admitted_cc count drifted");
  }

  // (6) quantifier displacement: every frozen inventory count is displaced by a
  // named register quantifier, and no register quantifier is an inventory count.
  const quantifiers = recon?.quantifier_replacement ?? {};
  const forbidden = new Set(Array.isArray(quantifiers.forbidden_quantifiers) ? quantifiers.forbidden_quantifiers : []);
  const liveQuantifiers = new Set(
    (liveRegisterObj?.gates ?? []).map((gate) => gate?.quantifier?.name).filter(nonEmpty),
  );
  if (!sameSet([...liveQuantifiers], quantifiers.register_quantifiers ?? [])) {
    add("quantifier_is_inventory_count", "recorded register_quantifiers != live register quantifiers");
  }
  for (const name of liveQuantifiers) {
    if (forbidden.has(name)) add("quantifier_is_inventory_count", `${name}: register quantifier is an inventory count`);
  }
  const m202Counts = m202Obj?.mapping_counts ?? {};
  const expectedCounters = [...Object.keys(m202Counts), "suites_cited"];
  const displacements = Array.isArray(quantifiers.displacements) ? quantifiers.displacements : [];
  const byCounter = new Map(displacements.map((entry) => [entry?.inventory_counter, entry]));
  for (const counter of expectedCounters) {
    const entry = byCounter.get(counter);
    if (!entry) {
      add("displacement_missing", `${counter}: no displacement recorded`);
      continue;
    }
    if (!nonEmpty(entry.named_quantifier)) {
      add("displacement_missing", `${counter}: named quantifier missing`);
      continue;
    }
    if (forbidden.has(entry.named_quantifier)) {
      add("quantifier_is_inventory_count", `${counter} -> ${entry.named_quantifier} is an inventory count`);
    }
    if (!liveQuantifiers.has(entry.named_quantifier)) {
      add("quantifier_is_inventory_count", `${counter} -> ${entry.named_quantifier} is not a live register quantifier`);
    }
    if (entry.forbidden_as_quantifier !== true) {
      add("displacement_missing", `${counter}: forbidden_as_quantifier must be true`);
    }
    const liveValue = counter === "suites_cited" ? m202Obj?.suites_cited : m202Counts[counter];
    if (JSON.stringify(liveValue) !== JSON.stringify(entry.verbatim_value)) {
      add("displacement_missing", `${counter}: verbatim value drifted`);
    }
  }
  for (const counter of Object.keys(m202Counts)) {
    if (!forbidden.has(counter)) add("displacement_missing", `${counter} missing from forbidden_quantifiers`);
  }
  if (!forbidden.has("suites_cited")) add("displacement_missing", "suites_cited missing from forbidden_quantifiers");
  if (quantifiers.inventory_counts_are_proof !== false) {
    add("inventory_count_as_proof", "inventory_counts_are_proof must be false");
  }
  if (!nonEmpty(quantifiers.statement)) add("inventory_count_as_proof", "displacement statement missing");

  // (7) the architecture verifier baseline stays a pre-existing fail (D537) and
  // is never relabelled as pass or turned into a stopping condition.
  const baselineBlock = recon?.architecture_verifier_baseline ?? {};
  const drift = baselineBlock.drift_counts ?? {};
  const driftSum = Object.values(drift).reduce((total, value) => total + (typeof value === "number" ? value : 0), 0);
  if (baselineBlock.status !== "fail") {
    add("verifier_baseline_relabelled_as_pass", `status=${String(baselineBlock.status)}`);
  }
  if (baselineBlock.failure_count !== driftSum) {
    add("verifier_baseline_relabelled_as_pass", `failure_count ${baselineBlock.failure_count} != drift sum ${driftSum}`);
  }
  if (baselineBlock.pre_existing !== true) add("verifier_baseline_relabelled_as_pass", "pre_existing must be true");
  if (baselineBlock.stopping_condition !== false) {
    add("verifier_baseline_relabelled_as_pass", "stopping_condition must be false");
  }
  if (baselineBlock.regeneration_performed !== false) {
    add("verifier_baseline_relabelled_as_pass", "regeneration_performed must be false");
  }
  if (!/D537/.test(String(baselineBlock.decision_ref))) {
    add("verifier_baseline_relabelled_as_pass", "decision_ref must cite D537");
  }
  if (baselineBlock.items !== nonEmptyLines(itemsText)) {
    add("verifier_baseline_relabelled_as_pass", `items ${baselineBlock.items} != live ${nonEmptyLines(itemsText)}`);
  }
  if (baselineBlock.edges !== nonEmptyLines(edgesText)) {
    add("verifier_baseline_relabelled_as_pass", `edges ${baselineBlock.edges} != live ${nonEmptyLines(edgesText)}`);
  }
  if (baselineBlock.ontology_promotion_diagnostics !== 0) {
    add("verifier_baseline_relabelled_as_pass", "ontology promotion diagnostics must be 0");
  }
  if (!/pre-existing/i.test(String(baselineBlock.interpretation))) {
    add("verifier_baseline_relabelled_as_pass", "interpretation must record a pre-existing baseline");
  }

  // (8) punkt registry admission stays not-adopted with zero admitted rows.
  const punkt = recon?.punkt_registry_state ?? {};
  if (punkt.verdict !== "not-adopted") add("punkt_row_admitted", `verdict=${String(punkt.verdict)}`);
  if (punkt.admitted_rows !== 0) add("punkt_row_admitted", `admitted_rows=${punkt.admitted_rows}`);
  if (punkt.decision_record !== PUNKT_DOC) add("punkt_row_admitted", `decision_record=${String(punkt.decision_record)}`);
  const punktLevelCount = count(admissionsText, "level: punkt");
  if (punktLevelCount !== 0) add("punkt_row_admitted", `admissions carries ${punktLevelCount} punkt rows`);
  const glavaCount = count(admissionsText, "level: glava");
  const statyaCount = count(admissionsText, "level: statya");
  if (glavaCount + statyaCount + punktLevelCount !== 166) {
    add("punkt_row_admitted", `admission rows = ${glavaCount + statyaCount + punktLevelCount} != 166`);
  }
  if (count(registryText, "punkt") !== 0) add("punkt_row_admitted", "registry YAML mentions punkt");
  const m202S03Obj = safeJson(m202S03Text);
  if (m202S03Obj?.output?.punkt_rows_admitted !== 0) {
    add("punkt_row_admitted", `m202-s03 output.punkt_rows_admitted=${String(m202S03Obj?.output?.punkt_rows_admitted)}`);
  }
  if (m202Counts.punkt_admitted !== 0) add("punkt_row_admitted", "M202 punkt_admitted != 0");

  // (9) claims_ledger stays derived and non-authoritative, on every surface.
  const ledgerSource = sources.claims_ledger ?? {};
  if (!/non-authoritative/i.test(String(ledgerSource.authority))) {
    add("claims_ledger_as_authority", `authority=${String(ledgerSource.authority)}`);
  }
  if (!parseVerifierDerivedPatterns(verifierText).includes(LEDGER)) {
    add("claims_ledger_as_authority", "the verifier no longer lists claims_ledger.md as derived non-authoritative");
  }
  if (!/non-authoritative/i.test(ledgerText)) {
    add("claims_ledger_as_authority", "the ledger lost its non-authoritative marker");
  }
  const ledgerState = states.find((state) => state?.source_path === LEDGER);
  if (!ledgerState || ledgerState.derived !== true || ledgerState.authoritative !== false) {
    add("claims_ledger_as_authority", "the ledger facet must be marked derived and non-authoritative");
  }

  // (10) R035 stays active and no gate is promoted.
  if (recon?.requirement_disposition !== "active") {
    add("r035_promoted", `requirement_disposition=${String(recon?.requirement_disposition)}`);
  }
  if (recon?.gates_promoted !== 0) add("r035_promoted", `gates_promoted=${recon?.gates_promoted}`);
  const allowedDispositions = new Set(["unsatisfied", "conflicted-requires-decision"]);
  const liveDispositions = new Map((liveRegisterObj?.gates ?? []).map((gate) => [gate?.gate_id, gate?.disposition]));
  for (const [gateId, disposition] of liveDispositions) {
    if (!allowedDispositions.has(disposition)) add("r035_promoted", `${gateId}: disposition=${disposition}`);
  }
  const recordedDispositions = recon?.register_gate_dispositions ?? {};
  if (Object.keys(recordedDispositions).length !== 7) {
    add("r035_promoted", `recorded disposition map size ${Object.keys(recordedDispositions).length}`);
  }
  for (const [gateId, disposition] of liveDispositions) {
    if (recordedDispositions[gateId] !== disposition) {
      add("r035_promoted", `${gateId}: recorded ${String(recordedDispositions[gateId])} != live ${disposition}`);
    }
  }

  return { ok: errors.length === 0, errors };
}

function codes(result) {
  return result.errors.map((error) => error.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const recon = liveRecon;

function cloneRecon() {
  return JSON.parse(liveReconText);
}

function fixture(mutate) {
  const next = cloneRecon();
  const returned = mutate(next) ?? next;
  assert.notEqual(
    JSON.stringify(returned),
    JSON.stringify(liveRecon),
    "fixture mutation did not modify the reconciliation artifact",
  );
  return returned;
}

// `expectCode` accepts either an already-validated result or a raw artifact copy
// (a fixture). A raw copy is validated here, so a negative case can be written as
// `expectCode(fixture((r) => { ... }), "code")` without an extra wrapper.
function expectCode(resultOrArtifact, expected) {
  const result = Array.isArray(resultOrArtifact?.errors)
    ? resultOrArtifact
    : validateReconciliation(resultOrArtifact);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M209 S01 reconciliation validates against the live repository", () => {
  const result = validateReconciliation(recon);
  assert.deepEqual(result.errors, [], `reconciliation errors: ${JSON.stringify(result.errors, null, 2)}`);
  assert.equal(result.ok, true);
});

test("reconciliation identity and scope are declared", () => {
  assert.equal(recon.schema_version, RECON_SCHEMA_VERSION);
  assert.equal(recon.kind, "m209-s01-r035-gate-reconciliation");
  assert.equal(recon.milestone, "M209-2yg6ix");
  assert.equal(recon.slice, "S01");
  assert.equal(recon.task, "T05");
  assert.equal(recon.lifecycle, "[bounded]");
  assert.equal(recon.authoritative, false);
  assert.equal(recon.requirement_id, "R035");
  assert.equal(recon.requirement_disposition, "active");
  assert.equal(recon.requirement_disposition_decision, "D430");
  assert.equal(recon.gates_promoted, 0);
  assert.equal(recon.captured_at, "2026-09-22");
  assert.equal(recon.contract, CONTRACT_PATH);
});

test("the seven gate ids agree across all four live sources", () => {
  const readme = parseReadmeGateIds(liveReadme);
  const ontology = parseVerifierGateIds(liveVerifier);
  const m202 = parseM202GateIds(liveM202);
  const register = parseRegisterGateIds(liveRegisterText);
  for (const [name, ids] of [["readme", readme], ["ontology", ontology], ["m202", m202], ["register", register]]) {
    assert.ok(sameSet([...ids], CANONICAL_GATE_IDS), `${name} = ${[...ids].join(",")}`);
    assert.equal(ids.size, 7, `${name} must hold exactly seven ids`);
  }
  assert.ok(sameSet(recon.gate_id_agreement.readme_required_gate_ids, [...readme]));
  assert.ok(sameSet(recon.gate_id_agreement.ontology_rules_required_gate_ids, [...ontology]));
  assert.ok(sameSet(recon.gate_id_agreement.frozen_m202_gate_ids, [...m202]));
  assert.ok(sameSet(recon.gate_id_agreement.register_gate_ids, [...register]));
  assert.equal(recon.gate_id_agreement.agreement, true);
  assert.deepEqual(recon.gate_id_agreement.differences, []);
});

test("the graph-vector disjunction is resolved as a union without promotion", () => {
  const readme = parseReadmeGateIds(liveReadme);
  const ontology = parseVerifierGateIds(liveVerifier);
  assert.ok(readme.has("GATE-G015") && readme.has("GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"));
  assert.ok(ontology.has("GATE-G015") && ontology.has("GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"));
  assert.equal(recon.gate_id_agreement.resolved_disjunction.promotion, false);
  assert.equal(recon.gate_id_agreement.resolved_disjunction.register_row_disposition, "conflicted-requires-decision");
});

test("out-of-register ids are exactly the derived ledger extras", () => {
  const readme = parseReadmeGateIds(liveReadme);
  const ontology = parseVerifierGateIds(liveVerifier);
  const ledger = parseLedgerGateIds(liveLedger);
  assert.equal(ledger.size, 14, `ledger gate ids = ${[...ledger].join(",")}`);
  const extras = [...ledger].filter((id) => !readme.has(id) && !ontology.has(id)).sort();
  assert.equal(extras.length, 7);
  assert.ok(sameSet(extras, recon.gate_id_agreement.out_of_register_gate_ids.map((entry) => entry.gate_id)));
});

test("the GATE-G015 conflict is real, located and unsmoothed", () => {
  const conflict = recon.gate_g015_state_conflict;
  const normalized = new Set(conflict.recorded_states.map((state) => state.normalized_state));
  assert.deepEqual([...normalized].sort(), ["superseded", "unsatisfied"]);
  assert.equal(conflict.conflict, true);
  assert.equal(conflict.resolution, "deferred-to-individual-decision");
  assert.equal(conflict.decision_ref, null);
  assert.equal(conflict.readme_safe_bucket.is_gate_state, false);
  const itemsStatus = parseItemsStatus(liveItems, "GATE-G015");
  const ledgerStatus = parseLedgerGateStatus(liveLedger, "GATE-G015");
  assert.equal(itemsStatus?.status, "superseded");
  assert.equal(ledgerStatus?.status, "superseded");
  const m202 = safeJson(liveM202);
  assert.equal(
    m202.promotion_gates.find((gate) => gate.gate_id === "GATE-G015").gate_verdict,
    "unsatisfied",
  );
  assert.equal(itemsStatus?.line, 38);
  assert.equal(ledgerStatus?.line, 124);
  assert.equal(parseM202VerdictLine(liveM202, "GATE-G015"), 108);
});

test("recorded sources match the live bytes and are tracked", () => {
  for (const [key, expectedPath] of Object.entries(EXPECTED_SOURCE_PATHS)) {
    const entry = recon.sources[key];
    assert.equal(entry.path, expectedPath, `${key}: path`);
    assert.equal(entry.bytes, repoBytes(expectedPath), `${key}: bytes`);
    assert.equal(entry.sha256, sha256(expectedPath), `${key}: sha256`);
    assert.ok(isTracked(expectedPath), `${key}: ${expectedPath} must be tracked`);
  }
});

test("the architecture projections are byte-identical and not regenerated", () => {
  for (const projection of PROJECTION_PATHS) {
    const entry = Object.values(recon.sources).find((source) => source.path === projection);
    assert.equal(sha256(projection), entry.sha256, `${projection} sha`);
    assert.equal(repoBytes(projection), entry.bytes, `${projection} bytes`);
    assert.equal(liveDelta.get(projection), "", `${projection} must carry no worktree delta`);
  }
});

test("frozen M202 inputs are Rust-anchored, and M202 is an explicit captured-at baseline", () => {
  const rust = parseRustPins(liveRust);
  assert.equal(recon.frozen_pins.rust_anchored.length, 4);
  for (const pin of recon.frozen_pins.rust_anchored) {
    assert.equal(pin.anchored, true, `${pin.path}: anchored`);
    assert.equal(rust.sha.get(pin.rust_sha_constant), pin.sha256, `${pin.path}: recorded sha vs Rust constant`);
    assert.equal(rust.bytes.get(pin.rust_bytes_constant), pin.bytes, `${pin.path}: recorded bytes vs Rust constant`);
    assert.equal(sha256(pin.path), pin.sha256, `${pin.path}: live sha`);
    assert.equal(liveDelta.get(pin.path), "", `${pin.path}: no worktree delta`);
  }
  const baseline = recon.frozen_pins.captured_at_baseline_not_rust_anchored;
  assert.equal(baseline.path, M202);
  assert.equal(baseline.anchored, false);
  assert.equal(baseline.rust_sha_constant, null);
  assert.equal(baseline.rust_bytes_constant, null);
  assert.match(baseline.anchor_kind, /captured-at/);
  assert.match(baseline.anchor_kind, /not[- ]?rust[- ]?anchored/i);
  assert.equal(baseline.sha256, sha256(M202));
  assert.equal(baseline.bytes, repoBytes(M202));
  assert.equal(liveDelta.get(M202), "");
});

test("no Rust sha256 constant exists for M202 (Q3 rework invariant)", () => {
  assert.equal(
    /PROOF_GATE_JSON_SHA256|PROOF_GATE_JSON_BYTES/.test(liveRust),
    false,
    "the Rust pin suite must not carry an M202 sha256/bytes constant",
  );
  assert.equal(count(liveM202, '"validated"'), 0);
  assert.equal(count(liveM202, '"authoritative": true'), 0);
  assert.equal(count(liveM202, '"gate_verdict": "unsatisfied"'), 7);
});

test("every frozen inventory count is displaced by a named register quantifier", () => {
  const m202 = safeJson(liveM202);
  const register = parseRegister(liveRegisterText);
  const liveQuantifiers = new Set(register.gates.map((gate) => gate.quantifier.name));
  const forbidden = new Set(recon.quantifier_replacement.forbidden_quantifiers);
  assert.equal(forbidden.size, 10);
  for (const name of liveQuantifiers) assert.equal(forbidden.has(name), false, `${name} is an inventory count`);
  assert.ok(sameSet([...liveQuantifiers], recon.quantifier_replacement.register_quantifiers));
  const counters = [...Object.keys(m202.mapping_counts), "suites_cited"];
  assert.equal(counters.length, 10);
  assert.equal(recon.quantifier_replacement.displacements.length, 10);
  for (const counter of counters) {
    const displacement = recon.quantifier_replacement.displacements.find(
      (entry) => entry.inventory_counter === counter,
    );
    assert.ok(displacement, `${counter}: displacement must exist`);
    assert.ok(nonEmpty(displacement.named_quantifier), `${counter}: named quantifier`);
    assert.equal(liveQuantifiers.has(displacement.named_quantifier), true, `${counter}: register quantifier`);
    assert.equal(displacement.forbidden_as_quantifier, true);
    const liveValue = counter === "suites_cited" ? m202.suites_cited : m202.mapping_counts[counter];
    assert.deepEqual(displacement.verbatim_value, liveValue, `${counter}: verbatim value`);
  }
  assert.equal(recon.quantifier_replacement.inventory_counts_are_proof, false);
});

test("the architecture verifier baseline stays a pre-existing fail (D537)", () => {
  const baseline = recon.architecture_verifier_baseline;
  assert.equal(baseline.command, "uv run python scripts/verify-architecture-graph.py");
  assert.equal(baseline.status, "fail");
  assert.equal(
    baseline.failure_count,
    Object.values(baseline.drift_counts).reduce((total, value) => total + value, 0),
  );
  assert.equal(baseline.failure_count, 256);
  assert.deepEqual(baseline.drift_counts, {
    "freshness-drift": 2,
    "graph-integrity-drift": 11,
    "source-anchor-drift": 243,
  });
  assert.equal(baseline.items, nonEmptyLines(liveItems));
  assert.equal(baseline.edges, nonEmptyLines(liveEdges));
  assert.equal(baseline.ontology_promotion_diagnostics, 0);
  assert.equal(baseline.pre_existing, true);
  assert.equal(baseline.stopping_condition, false);
  assert.equal(baseline.regeneration_performed, false);
  assert.match(baseline.interpretation, /pre-existing/);
});

test("punkt registry admission remains not-adopted with zero admitted rows", () => {
  assert.equal(recon.punkt_registry_state.verdict, "not-adopted");
  assert.equal(recon.punkt_registry_state.admitted_rows, 0);
  assert.equal(recon.punkt_registry_state.decision_record, PUNKT_DOC);
  assert.equal(count(liveAdmissions, "level: punkt"), 0);
  assert.equal(count(liveAdmissions, "level: glava") + count(liveAdmissions, "level: statya"), 166);
  assert.equal(count(liveRegistry, "punkt"), 0);
  assert.equal(safeJson(liveM202S03).output.punkt_rows_admitted, 0);
  assert.equal(safeJson(liveM202).mapping_counts.punkt_admitted, 0);
});

test("claims_ledger is derived non-authoritative on every surface", () => {
  assert.match(recon.sources.claims_ledger.authority, /non-authoritative/);
  assert.ok(parseVerifierDerivedPatterns(liveVerifier).includes(LEDGER));
  assert.match(liveLedger, /non-authoritative/);
  const state = recon.gate_g015_state_conflict.recorded_states.find(
    (candidate) => candidate.source_path === LEDGER,
  );
  assert.equal(state.derived, true);
  assert.equal(state.authoritative, false);
});

test("R035 stays active and no gate is promoted", () => {
  const register = parseRegister(liveRegisterText);
  const dispositions = new Set(register.gates.map((gate) => gate.disposition));
  assert.ok(sameSet([...dispositions], ["unsatisfied", "conflicted-requires-decision"]));
  for (const gate of register.gates) assert.equal(gate.proof_package, null, `${gate.gate_id}: proof_package`);
  assert.equal(recon.requirement_disposition, "active");
  assert.equal(recon.gates_promoted, 0);
});

test("non-claims keep the reconciliation non-inverting", () => {
  assert.ok(recon.non_claims.length >= 8);
  const joined = recon.non_claims.join(" ");
  assert.match(joined, /not proof for any gate/);
  assert.match(joined, /does not regenerate architecture projections/);
  assert.match(joined, /D7 missing-anchor quarantine/);
  assert.match(joined, /does not pick a winner in the GATE-G015 conflict/);
  assert.match(joined, /does not touch R070/);
  assert.match(joined, /R035 remains active \(D430\)/);
  assert.match(joined, /claims_ledger\.md is a derived non-authoritative view/);
  assert.match(joined, /stopping condition/);
  assert.match(joined, /punkt registry admission remains not-adopted/i);
  assert.match(joined, /Inventory counts are displaced by named quantifiers/);
});

test("the contract never reads an ignored, .gsd or absolute path as evidence", () => {
  const source = readRepo(CONTRACT_PATH);
  assert.ok(!/readRepo\(\s*"\.gsd\//.test(source), "the contract must not read .gsd paths");
  assert.ok(!/readRepo\(\s*"\.agents\//.test(source), "the contract must not read .agents paths");
  assert.ok(!/readRepo\(\s*"\//.test(source), "the contract must not read an absolute path");
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(source.includes(`"${prefix}"`), `the contract must declare ${prefix} as refused`);
  }
});

test("the contract uses only the two allowed git subprocesses", () => {
  const source = readRepo(CONTRACT_PATH);
  for (const executable of ["cargo", "uv", "python", "python3", "sh", "bash"]) {
    const launch = new RegExp(`execFileSync\\(\\s*"${executable}"`);
    assert.ok(!launch.test(source), `${executable} must not be launched by this contract`);
  }
  assert.ok(/execFileSync\("git", \["ls-files", "--error-unmatch"/.test(source));
  assert.ok(/execFileSync\("git", \["status", "--porcelain"/.test(source));
});

test("the contract never runs the architecture verifier and never emits the slice marker", () => {
  const source = readRepo(CONTRACT_PATH);
  assert.ok(!/verify-architecture-graph\.py"\s*,/.test(source), "the verifier must be parsed as text only");
  const verifyMarker = readRepo("scripts/verify-architecture-graph.py").match(
    /M\d+_[A-Z0-9_]+_VERIFY_OK/,
  );
  if (verifyMarker) {
    assert.ok(!source.includes(verifyMarker[0]), "the slice verify marker must be unreachable by construction");
  }
});

// ---------------------------------------------------------------------------
// fail-closed negatives (each code fires against a mutated artifact)
// ---------------------------------------------------------------------------

test("negative: gate-id agreement drift", () => {
  expectCode(
    fixture((r) => { r.gate_id_agreement.readme_required_gate_ids.pop(); }),
    "gate_ids_disagree",
  );
  expectCode(
    fixture((r) => { r.gate_id_agreement.differences.push({ source: "readme", detail: "x" }); }),
    "gate_ids_disagree",
  );
  expectCode(
    fixture((r) => { r.gate_id_agreement.out_of_register_gate_ids.pop(); }),
    "gate_ids_disagree",
  );
  expectCode(
    fixture((r) => { r.gate_id_agreement.resolved_disjunction.promotion = true; }),
    "gate_ids_disagree",
  );
});

test("negative: register id set drift", () => {
  expectCode(
    fixture((r) => { r.gate_id_agreement.register_gate_ids = r.gate_id_agreement.register_gate_ids.slice(0, 6); }),
    "register_ids_mismatch",
  );
});

test("negative: source byte and hash drift", () => {
  expectCode(
    fixture((r) => { r.sources.readme_gate_table.bytes += 1; }),
    "source_bytes_mismatch",
  );
  expectCode(
    fixture((r) => { r.sources.readme_gate_table.sha256 = "0".repeat(64); }),
    "source_hash_mismatch",
  );
  expectCode(
    fixture((r) => { delete r.sources.enforcement_rules; }),
    "source_hash_mismatch",
  );
});

test("negative: architecture projections regenerated", () => {
  expectCode(
    fixture((r) => { r.sources.architecture_items.sha256 = "0".repeat(64); }),
    "architecture_items_regenerated",
  );
  expectCode(
    fixture((r) => { r.sources.architecture_edges.sha256 = "0".repeat(64); }),
    "architecture_edges_regenerated",
  );
  const allPaths = [...DELTA_PATHS];
  expectCode(
    validateReconciliation(recon, { delta: new Map(allPaths.map((p) => [p, " M modified"])) }),
    "architecture_items_regenerated",
  );
});

test("negative: frozen M202 and Rust-anchored inputs drift", () => {
  expectCode(
    fixture((r) => { r.frozen_pins.captured_at_baseline_not_rust_anchored.sha256 = "0".repeat(64); }),
    "m202_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.captured_at_baseline_not_rust_anchored.anchored = true; }),
    "m202_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.captured_at_baseline_not_rust_anchored.rust_sha_constant = "PROOF_GATE_JSON_SHA256"; }),
    "m202_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.captured_at_baseline_not_rust_anchored.semantic_pins.gate_id_count = 6; }),
    "m202_modified",
  );
  expectCode(
    validateReconciliation(recon, {
      m202Text: liveM202.replace('"gate_verdict": "unsatisfied"', '"gate_verdict": "satisfied"'),
    }),
    "m202_modified",
  );
  expectCode(
    validateReconciliation(recon, { rustText: `${liveRust}\nconst PROOF_GATE_JSON_SHA256: &str = "x";\n` }),
    "m202_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.rust_anchored[0].sha256 = "0".repeat(64); }),
    "hidden_frozen_input_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.rust_anchored[0].bytes += 1; }),
    "hidden_frozen_input_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.rust_anchored[0].anchored = false; }),
    "hidden_frozen_input_modified",
  );
  expectCode(
    fixture((r) => { r.frozen_pins.rust_anchored.pop(); }),
    "hidden_frozen_input_modified",
  );
});

test("negative: git failure fails closed instead of passing", () => {
  const allPaths = [...DELTA_PATHS];
  const failed = new Map(allPaths.map((p) => [p, "git status failed"]));
  const result = validateReconciliation(recon, { delta: failed });
  assert.equal(result.ok, false, "a git failure must not silently pass");
  expectCode(result, "hidden_frozen_input_modified");
  expectCode(result, "m202_modified");
  expectCode(result, "architecture_items_regenerated");
  expectCode(result, "architecture_edges_regenerated");
});

test("negative: the GATE-G015 conflict cannot be smoothed or invented", () => {
  expectCode(
    fixture((r) => {
      for (const state of r.gate_g015_state_conflict.recorded_states) state.normalized_state = "unsatisfied";
      r.gate_g015_state_conflict.distinct_normalized_states = ["unsatisfied"];
    }),
    "gate_g015_conflict_smoothed",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.conflict = false; }),
    "gate_g015_conflict_smoothed",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.readme_safe_bucket.is_gate_state = true; }),
    "gate_g015_conflict_smoothed",
  );
});

test("negative: GATE-G015 locators and resolution drift", () => {
  expectCode(
    fixture((r) => { delete r.gate_g015_state_conflict.recorded_states[0].selector; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { delete r.gate_g015_state_conflict.recorded_states[0].line; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.recorded_states[0].normalized_state = "made-up"; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.recorded_states[0].raw_value = "satisfied"; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.recorded_states[0].line = 1; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.resolution = "resolved-by-agent"; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.decision_ref = "D430"; }),
    "conflict_locator_missing",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.required_facets = ["registry_status"]; }),
    "conflict_locator_missing",
  );
});

test("negative: quantifier displacement drift", () => {
  expectCode(
    fixture((r) => { r.quantifier_replacement.displacements[0].named_quantifier = "registry_rows"; }),
    "quantifier_is_inventory_count",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.register_quantifiers.push("registry_rows"); }),
    "quantifier_is_inventory_count",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.displacements[0].named_quantifier = "not_a_register_quantifier"; }),
    "quantifier_is_inventory_count",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.displacements[0].named_quantifier = null; }),
    "displacement_missing",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.displacements[0].verbatim_value = 999; }),
    "displacement_missing",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.displacements.pop(); }),
    "displacement_missing",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.inventory_counts_are_proof = true; }),
    "inventory_count_as_proof",
  );
  expectCode(
    fixture((r) => { r.quantifier_replacement.statement = ""; }),
    "inventory_count_as_proof",
  );
});

test("negative: punkt admission and ledger authority drift", () => {
  expectCode(
    fixture((r) => { r.punkt_registry_state.admitted_rows = 1; }),
    "punkt_row_admitted",
  );
  expectCode(
    fixture((r) => { r.punkt_registry_state.verdict = "granted"; }),
    "punkt_row_admitted",
  );
  expectCode(
    fixture((r) => { r.punkt_registry_state.decision_record = "prd/architecture/other.md"; }),
    "punkt_row_admitted",
  );
  expectCode(
    fixture((r) => { r.sources.claims_ledger.authority = "authoritative"; }),
    "claims_ledger_as_authority",
  );
  expectCode(
    fixture((r) => {
      const state = r.gate_g015_state_conflict.recorded_states.find(
        (candidate) => candidate.source_path === LEDGER,
      );
      state.derived = false;
    }),
    "claims_ledger_as_authority",
  );
  expectCode(
    validateReconciliation(recon, { verifierText: liveVerifier.replace(`"${LEDGER}",`, "") }),
    "claims_ledger_as_authority",
  );
});

test("negative: verifier baseline relabelled", () => {
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.status = "pass"; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.failure_count = 0; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.pre_existing = false; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.stopping_condition = true; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.regeneration_performed = true; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.decision_ref = "D999"; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.items = 64; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.ontology_promotion_diagnostics = 1; }),
    "verifier_baseline_relabelled_as_pass",
  );
  expectCode(
    fixture((r) => { r.architecture_verifier_baseline.interpretation = "clean run"; }),
    "verifier_baseline_relabelled_as_pass",
  );
});

test("negative: R035 promoted or gate dispositions drifted", () => {
  expectCode(
    fixture((r) => { r.requirement_disposition = "validated"; }),
    "r035_promoted",
  );
  expectCode(
    fixture((r) => { r.gates_promoted = 1; }),
    "r035_promoted",
  );
  expectCode(
    fixture((r) => { r.register_gate_dispositions["GATE-G015"] = "unsatisfied"; }),
    "r035_promoted",
  );
  expectCode(
    fixture((r) => {
      const key = Object.keys(r.register_gate_dispositions)[0];
      r.register_gate_dispositions[key] = "satisfied-by-proof-package";
    }),
    "r035_promoted",
  );
});

test("negative: ignored, absolute and traversing source paths", () => {
  expectCode(
    fixture((r) => { r.sources.readme_gate_table.path = ".gsd/phases/x.md"; }),
    "ignored_path_as_source",
  );
  expectCode(
    fixture((r) => { r.sources.readme_gate_table.path = "/tmp/x.md"; }),
    "ignored_path_as_source",
  );
  expectCode(
    fixture((r) => { r.sources.readme_gate_table.path = "../outside.md"; }),
    "ignored_path_as_source",
  );
  expectCode(
    fixture((r) => { r.gate_g015_state_conflict.recorded_states[0].source_path = ".agents/x.md"; }),
    "ignored_path_as_source",
  );
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code. The test below asserts
// that each mutation actually makes its code fire and actually makes the artifact
// fail closed, so a code can never be documented without being reachable, and can
// never be reachable without being documented.
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "gate_ids_disagree",
    mutate: (r) => { r.gate_id_agreement.readme_required_gate_ids.pop(); },
  },
  {
    code: "register_ids_mismatch",
    mutate: (r) => { r.gate_id_agreement.register_gate_ids = r.gate_id_agreement.register_gate_ids.slice(0, 6); },
  },
  { code: "source_bytes_mismatch", mutate: (r) => { r.sources.readme_gate_table.bytes += 1; } },
  { code: "source_hash_mismatch", mutate: (r) => { r.sources.readme_gate_table.sha256 = "0".repeat(64); } },
  {
    code: "architecture_items_regenerated",
    mutate: (r) => { r.sources.architecture_items.sha256 = "0".repeat(64); },
  },
  {
    code: "architecture_edges_regenerated",
    mutate: (r) => { r.sources.architecture_edges.sha256 = "0".repeat(64); },
  },
  {
    code: "m202_modified",
    mutate: (r) => { r.frozen_pins.captured_at_baseline_not_rust_anchored.sha256 = "0".repeat(64); },
  },
  {
    code: "hidden_frozen_input_modified",
    mutate: (r) => { r.frozen_pins.rust_anchored[0].sha256 = "0".repeat(64); },
  },
  {
    code: "gate_g015_conflict_smoothed",
    mutate: (r) => {
      for (const state of r.gate_g015_state_conflict.recorded_states) state.normalized_state = "unsatisfied";
      r.gate_g015_state_conflict.distinct_normalized_states = ["unsatisfied"];
    },
  },
  {
    code: "conflict_locator_missing",
    mutate: (r) => { delete r.gate_g015_state_conflict.recorded_states[0].line; },
  },
  {
    code: "quantifier_is_inventory_count",
    mutate: (r) => { r.quantifier_replacement.displacements[0].named_quantifier = "registry_rows"; },
  },
  {
    code: "displacement_missing",
    mutate: (r) => { r.quantifier_replacement.displacements[0].named_quantifier = null; },
  },
  {
    code: "inventory_count_as_proof",
    mutate: (r) => { r.quantifier_replacement.inventory_counts_are_proof = true; },
  },
  { code: "punkt_row_admitted", mutate: (r) => { r.punkt_registry_state.admitted_rows = 1; } },
  {
    code: "claims_ledger_as_authority",
    mutate: (r) => { r.sources.claims_ledger.authority = "authoritative"; },
  },
  {
    code: "verifier_baseline_relabelled_as_pass",
    mutate: (r) => { r.architecture_verifier_baseline.status = "pass"; },
  },
  { code: "r035_promoted", mutate: (r) => { r.requirement_disposition = "validated"; } },
  {
    code: "ignored_path_as_source",
    mutate: (r) => { r.sources.readme_gate_table.path = ".gsd/phases/x.md"; },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const target = entry.mutate ? fixture(entry.mutate) : recon;
    const result = validateReconciliation(target, entry.overrides ?? {});
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    assert.equal(result.ok, false, `${entry.code} must make the reconciliation fail closed`);
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

test("the documented code block equals the emittable code set", () => {
  const source = readRepo(CONTRACT_PATH);
  const block = source.match(/\/\/ DOCUMENTED_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented codes block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documented.sort(), [...EMITTABLE_CODES].sort());
});

// ---------------------------------------------------------------------------
// markers (emitted only after the reconciliation contract holds)
// ---------------------------------------------------------------------------

test("M209 S01 reconciliation markers", () => {
  const result = validateReconciliation(recon);
  assert.deepEqual(result.errors, [], `reconciliation errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S01_RECONCILIATION_OK");
  console.log(`sources=${Object.keys(recon.sources).length}`);
  console.log("M209_S01_GATE_AGREEMENT_OK");
  console.log(`gate_ids=${CANONICAL_GATE_IDS.length}`);
  console.log("M209_S01_QUANTIFIER_DISPLACEMENT_OK");
  console.log(`displacements=${recon.quantifier_replacement.displacements.length}`);
  console.log("M209_S01_FROZEN_INPUTS_INTACT_OK");
  console.log(`frozen_inputs=${FROZEN_INPUTS.length}`);
});
