// M209/S01 gate-register contract (T02).
//
// Offline and fail-closed: the live register must validate against the LIVE
// enforcement surfaces (README §R035 table + PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES
// and ONTOLOGY_PROMOTION_RULES inside scripts/verify-architecture-graph.py), and
// every named fail-closed code must be provable against a mutated copy of that
// register or of one declared source, so the suite cannot fool itself by
// asserting codes it would never actually emit.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (frozen-input proof). No cargo, no
// network, and no `.gsd` / ignored / absolute path is ever read as evidence.
// scripts/verify-architecture-graph.py is parsed as text only and never run:
// its own baseline is fail/256 diagnostics (D537).
//
// Frozen M202 pin (Q3 rework, Q3-M202-PIN-UNSATISFIABLE, 2026-09-22):
// crates/ln-kb-ontology/tests/r035_proof_gate.rs carries NO
// PROOF_GATE_JSON_SHA256 / PROOF_GATE_JSON_BYTES constant, so this contract
// never invents one and never edits that frozen file. The real inherited pin is
// semantic and textual, reproduced here exactly:
//   - exactly 7 `"gate_id":` and exactly 7 `"gate_verdict": "unsatisfied"`;
//   - zero promoted-verdict substrings and zero bare `"validated"` value;
//   - `"disposition": "active"`, `"disposition_decision": "D430"`,
//     `"authoritative": false`, `"punkt_admitted": 0` present;
//   - each of the four external sha256 hexes, extracted live from the Rust
//     suite constants, appears in M202 as text exactly once.
// M202's own sha256/bytes are read from the register as a *captured-at
// baseline* explicitly labelled not-Rust-anchored (`pin_kind`), which is drift
// detection, not an anchor claim.
//
// Run: node --test scripts/m209_s01_gate_register_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const REGISTER = "prd/architecture/m209-s01-r035-gate-register.json";
const README = "prd/architecture/README.md";
const VERIFIER = "scripts/verify-architecture-graph.py";
const M202 = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
const ITEMS = "prd/architecture/architecture_items.jsonl";
const LEDGER = "prd/architecture/claims_ledger.md";
const RUST_PIN = "crates/ln-kb-ontology/tests/r035_proof_gate.rs";
const CONTRACT_PATH = "scripts/m209_s01_gate_register_contract.test.mjs";

const M202_S02 = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_S03 = "prd/migration/rust-evidence/m202-s03-registry-regeneration.json";
const ADMISSIONS_YAML = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const REGISTRY_YAML = "prd/architecture/kb-hierarchy-registry.yaml";

// The frozen M202 inputs: the four external artifacts M202 byte-pins, plus M202
// itself. Any worktree delta here is frozen-input drift.
const FROZEN_INPUTS = [M202, M202_S02, M202_S03, ADMISSIONS_YAML, REGISTRY_YAML];

// Rust-suite constant stem -> the live file that constant binds.
const RUST_SHA_CONSTANTS = [
  ["S02_JSON", M202_S02],
  ["S03_JSON", M202_S03],
  ["ADMISSIONS_YAML", ADMISSIONS_YAML],
  ["REGISTRY_YAML", REGISTRY_YAML],
];

const REGISTER_SCHEMA_VERSION = "law-nexus/r035-gate-register/v1";

// The seven canonical R035 promotion gates (D536). The live parses below must
// agree with this constant; a drift in the enforcement surface is a failure.
const CANONICAL_GATE_IDS = [
  "GATE-AKOMA-FRBR-NORMALIZATION",
  "GATE-LKIF-DEONTIC-BENCHMARK",
  "GATE-RUSLEGALCORE-SCOPE",
  "GATE-BFO-GOST-ALIGNMENT",
  "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
  "GATE-G015",
  "GATE-PILOT-SCALE-READINESS",
];

const FACETS = ["registry_status", "frozen_snapshot_verdict", "derived_view_status"];

// Raw registry/projection states -> disposition states. Mirrors the register's
// normalization_vocabulary, which the validator pins to this constant.
const NORMALIZATION = {
  blocked: "unsatisfied",
  unsatisfied: "unsatisfied",
  superseded: "superseded",
  deferred: "deferred",
  satisfied: "satisfied",
};

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The complete fail-closed code set. The `## Fail-closed codes` comment block
// below is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "schema_version_mismatch",
  "gate_count_mismatch",
  "gate_id_unknown",
  "gate_id_missing",
  "gate_id_duplicated",
  "owner_missing",
  "owner_path_missing",
  "owner_path_untracked",
  "evidence_class_unknown",
  "evidence_class_not_required_by_proof_level",
  "evidence_class_basis_missing",
  "proof_level_mismatch",
  "quantifier_missing",
  "quantifier_name_forbidden",
  "quantifier_name_duplicated",
  "quantifier_acceptance_not_quantified",
  "disposition_unknown",
  "disposition_basis_missing",
  "disposition_basis_duplicated",
  "disposition_decision_shared",
  "disposition_decision_malformed",
  "conflict_smoothed",
  "conflict_undetected",
  "conflict_list_empty",
  "proof_package_without_satisfied_disposition",
  "satisfied_without_proof_package",
  "m202_semantic_pin_broken",
  "m202_semantic_pin_missing",
  "m202_pin_mislabelled",
  "inventory_count_as_quantifier",
  "inventory_displacement_mismatch",
  "claims_ledger_marked_authoritative",
  "out_of_register_id_promoted",
  "ignored_path_as_source",
  "absolute_path_as_source",
  "r035_promoted_to_validated",
  "non_claims_missing",
];

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// schema_version_mismatch: register identity/schema/requirement_id drifted.
// gate_count_mismatch: register does not carry exactly seven gate rows.
// gate_id_unknown: a registered gate id is absent from the live surface.
// gate_id_missing: a live canonical gate id is absent from the register.
// gate_id_duplicated: the same gate id appears twice.
// owner_missing: a gate row has no owner.
// owner_path_missing: a gate row has no owner_path.
// owner_path_untracked: owner_path does not exist or is not git-tracked.
// evidence_class_unknown: evidence class is not in the live class union.
// evidence_class_not_required_by_proof_level: class is not the level's class set.
// evidence_class_basis_missing: no derivation basis for the evidence class.
// proof_level_mismatch: level is not live-derived from README and the rules.
// quantifier_missing: name/unit/acceptance is not fully named.
// quantifier_name_forbidden: the name is a documented forbidden quantifier.
// quantifier_name_duplicated: two gates share one quantifier name.
// quantifier_acceptance_not_quantified: acceptance carries no measurable count.
// disposition_unknown: disposition is outside the vocabulary.
// disposition_basis_missing: no per-gate derivation basis for the disposition.
// disposition_basis_duplicated: two gates share one disposition basis.
// disposition_decision_shared: one decision authorises two gates.
// disposition_decision_malformed: decision reference is not D<digits>.
// conflict_smoothed: divergent states collapsed into one disposition.
// conflict_undetected: a conflict was missed or invented.
// conflict_list_empty: a conflicted gate does not enumerate each state.
// proof_package_without_satisfied_disposition: a package without the disposition.
// satisfied_without_proof_package: satisfied with no attached proof package.
// m202_semantic_pin_broken: the inherited semantic M202 pin no longer holds.
// m202_semantic_pin_missing: the inherited pin mechanism cannot be read.
// m202_pin_mislabelled: the captured-at baseline is presented as a Rust anchor.
// inventory_count_as_quantifier: an inventory count stands as a quantifier.
// inventory_displacement_mismatch: displaced counts drifted from frozen M202.
// claims_ledger_marked_authoritative: the derived ledger view gained authority.
// out_of_register_id_promoted: a non-canonical gate id entered the register.
// ignored_path_as_source: a cited source anchor is an ignored overlay path.
// absolute_path_as_source: a cited source anchor is absolute or traversing.
// r035_promoted_to_validated: R035 was moved off active before its gates prove.
// non_claims_missing: register or gate row carries no non-claims.
// DOCUMENTED_CODES_END

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

function repoBytes(relativePath) {
  return readFileSync(path.join(root, relativePath)).length;
}

// `git status --porcelain` restricted to the frozen inputs: an empty result
// means none of those tracked artifacts carries a worktree delta.
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

function byId(register, gateId) {
  return (register?.gates ?? []).find((gate) => gate?.gate_id === gateId);
}

// ---------------------------------------------------------------------------
// live-surface parsers (text only; the verifier is never run)
// ---------------------------------------------------------------------------

// PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES / PROOF_LEVEL_ORDER /
// ONTOLOGY_PROMOTION_RULES, read out of the live enforcement script.
function parseVerifier(text) {
  const evidenceClassesByLevel = new Map();
  const evidenceBlock = text.match(/PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES\s*=\s*\{([\s\S]*?)\n\}/);
  if (evidenceBlock) {
    for (const line of evidenceBlock[1].split("\n")) {
      const match = line.match(/^\s*"([a-z-]+)":\s*\{([^}]*)\},?\s*$/);
      if (!match) continue;
      const classes = match[2]
        .split(",")
        .map((entry) => entry.trim().replace(/^"|"$/g, ""))
        .filter((entry) => entry.length > 0);
      if (classes.length > 0) evidenceClassesByLevel.set(match[1], classes);
    }
  }

  const proofLevelOrder = new Map();
  const orderBlock = text.match(/PROOF_LEVEL_ORDER\s*=\s*\{([\s\S]*?)\n\}/);
  if (orderBlock) {
    for (const match of orderBlock[1].matchAll(/"([a-z-]+)":\s*(\d+)/g)) {
      proofLevelOrder.set(match[1], Number(match[2]));
    }
  }

  const gateMinLevels = new Map();
  const rulesBlock = text.match(/ONTOLOGY_PROMOTION_RULES[^=]*=\s*\(([\s\S]*?)\n\)\n/);
  const rulesText = rulesBlock ? rulesBlock[1] : "";
  for (const match of rulesText.matchAll(
    /"required_gate_ids":\s*\(([^)]*)\),\s*"minimum_proof_level":\s*"([^"]+)"/g,
  )) {
    const level = match[2];
    for (const gate of match[1].matchAll(/(GATE-[A-Za-z0-9-]+)/g)) {
      if (!gateMinLevels.has(gate[1])) gateMinLevels.set(gate[1], new Set());
      gateMinLevels.get(gate[1]).add(level);
    }
  }

  const gateIds = new Set(gateMinLevels.keys());
  const union = new Set();
  for (const classes of evidenceClassesByLevel.values()) {
    for (const entry of classes) union.add(entry);
  }
  return { evidenceClassesByLevel, proofLevelOrder, gateMinLevels, gateIds, union };
}

// The README §R035 promotion-gate table: required gate ids and minimum levels.
function parseReadmeR035(text) {
  const lines = text.split("\n");
  const headerIndex = lines.findIndex(
    (line) => line.includes("Required promotion gate") && line.includes("Minimum validated proof level"),
  );
  const gateIds = new Set();
  const gateMinLevels = new Map();
  const rows = [];
  if (headerIndex === -1) return { gateIds, gateMinLevels, rows };
  for (let i = headerIndex + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.startsWith("|")) break;
    const cells = line.split("|").map((cell) => cell.trim());
    if (cells.length < 6) continue;
    if (/^-+$/.test((cells[1] ?? "").replace(/\s/g, ""))) continue;
    const gateCell = cells[3] ?? "";
    const level = (cells[4] ?? "").replace(/`/g, "").trim();
    const ids = [...gateCell.matchAll(/`([^`]+)`/g)].map((match) => match[1]);
    if (ids.length === 0 || level.length === 0) continue;
    rows.push({ trigger: cells[1], bucket: cells[2], ids, level });
    for (const id of ids) {
      gateIds.add(id);
      if (!gateMinLevels.has(id)) gateMinLevels.set(id, new Set());
      gateMinLevels.get(id).add(level);
    }
  }
  return { gateIds, gateMinLevels, rows };
}

// architecture_items.jsonl: proof_gate rows carry the registry status.
function parseItemsGateStatus(text) {
  const map = new Map();
  for (const line of String(text).split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    let record;
    try {
      record = JSON.parse(trimmed);
    } catch {
      continue;
    }
    if (record?.type === "proof_gate" && typeof record.id === "string") {
      map.set(record.id, record.status);
    }
  }
  return map;
}

// The frozen M202 snapshot: promotion_gates[].gate_id -> gate_verdict.
function parseM202(text) {
  if (typeof text !== "string") return { gates: new Map(), counts: null };
  let doc;
  try {
    doc = JSON.parse(text);
  } catch {
    return { gates: new Map(), counts: null };
  }
  const gates = new Map();
  for (const gate of doc?.promotion_gates ?? []) {
    if (typeof gate?.gate_id === "string") gates.set(gate.gate_id, gate.gate_verdict);
  }
  return { gates, counts: doc?.mapping_counts ?? null };
}

// claims_ledger.md: the derived view's Status column, first table wins so the
// R035 Gate Status crosswalk outranks the quarantine listings.
function parseLedgerStatus(text) {
  const map = new Map();
  const lines = String(text).split("\n");
  let headerSeen = false;
  let idIndex = -1;
  let statusIndex = -1;
  for (const line of lines) {
    if (line.startsWith("## ")) {
      headerSeen = false;
      idIndex = -1;
      statusIndex = -1;
      continue;
    }
    if (!line.startsWith("|")) continue;
    const cells = line.split("|").map((cell) => cell.trim());
    if (!headerSeen) {
      headerSeen = true;
      idIndex = cells.findIndex((cell) => cell === "ID");
      statusIndex = cells.findIndex((cell) => cell === "Status");
      continue;
    }
    if (idIndex < 0 || statusIndex < 0) continue;
    if (/^-+$/.test((cells[1] ?? "").replace(/\s/g, ""))) continue;
    const id = (cells[idIndex] ?? "").replace(/`/g, "").trim();
    const status = (cells[statusIndex] ?? "").replace(/`/g, "").trim();
    if (/^GATE-[A-Za-z0-9-]+$/.test(id) && status.length > 0 && !map.has(id)) {
      map.set(id, status);
    }
  }
  return map;
}

// All GATE-* identifiers named anywhere in the derived ledger view.
function ledgerGateIds(text) {
  return new Set([...String(text).matchAll(/GATE-[A-Za-z0-9-]+/g)].map((match) => match[0]));
}

// The sha256 / byte constants the frozen Rust suite carries, read live. The
// suite has no PROOF_GATE_JSON_* constant by design; its M202 pin is semantic.
function rustShaConstants(text) {
  const sha = new Map();
  const bytes = new Map();
  for (const match of String(text).matchAll(
    /const\s+([A-Z0-9_]+)_SHA256:\s*&str\s*=\s*(?:\r?\n\s*)?"([0-9a-f]{64})"/g,
  )) {
    sha.set(match[1], match[2]);
  }
  for (const match of String(text).matchAll(/const\s+([A-Z0-9_]+)_BYTES:\s*usize\s*=\s*(\d+)/g)) {
    bytes.set(match[1], Number(match[2]));
  }
  return { sha, bytes };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateRegister(register, overrides = {}) {
  const pick = (key, fallback) => (overrides[key] === undefined ? fallback : overrides[key]);
  const readmeText = pick("readmeText", liveReadme);
  const verifierText = pick("verifierText", liveVerifier);
  const m202Text = pick("m202Text", liveM202);
  const itemsText = pick("itemsText", liveItems);
  const ledgerText = pick("ledgerText", liveLedger);
  const rustText = pick("rustText", liveRust);
  const registerText = pick("registerText", JSON.stringify(register ?? null));
  const fileExists = pick("fileExists", repoExists);
  const tracked = pick("isTracked", isTracked);
  const frozenDelta = pick("frozenDelta", worktreeDelta(FROZEN_INPUTS));

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  const gates = Array.isArray(register?.gates) ? register.gates : [];

  // (1) register identity and shape.
  if (register?.schema_version !== REGISTER_SCHEMA_VERSION) {
    add("schema_version_mismatch", `schema_version=${register?.schema_version}`);
  }
  if (register?.kind !== "m209-s01-r035-gate-register") {
    add("schema_version_mismatch", `kind=${register?.kind}`);
  }
  if (register?.requirement_id !== "R035") {
    add("schema_version_mismatch", `requirement_id=${register?.requirement_id}`);
  }
  if (gates.length !== 7 || register?.gate_count !== gates.length) {
    add("gate_count_mismatch", `gates=${gates.length} gate_count=${register?.gate_count}`);
  }
  if (!sameSet(register?.normalization_vocabulary ? Object.keys(register.normalization_vocabulary) : [], Object.keys(NORMALIZATION))) {
    add("disposition_unknown", "normalization_vocabulary drifted from the contract constant");
  }

  const ids = gates.map((gate) => gate?.gate_id);
  const idSet = new Set(ids);

  // (2) gate ids derived live from README §R035 and ONTOLOGY_PROMOTION_RULES.
  const verifier = parseVerifier(verifierText);
  const readme = parseReadmeR035(readmeText);
  if (!sameSet([...verifier.gateIds], CANONICAL_GATE_IDS)) {
    add("gate_id_unknown", `verifier union drifted: ${[...verifier.gateIds].join(",")}`);
  }
  if (!sameSet([...readme.gateIds], CANONICAL_GATE_IDS)) {
    add("gate_id_missing", `readme union drifted: ${[...readme.gateIds].join(",")}`);
  }
  if (idSet.size !== ids.length) add("gate_id_duplicated", ids.join(","));
  for (const id of ids) {
    if (!CANONICAL_GATE_IDS.includes(id)) add("gate_id_unknown", `register:${id}`);
  }
  for (const id of CANONICAL_GATE_IDS) {
    if (!idSet.has(id)) add("gate_id_missing", `register:${id}`);
  }
  for (const [label, derived] of [
    ["verifier", verifier.gateIds],
    ["readme", readme.gateIds],
  ]) {
    for (const id of idSet) if (!derived.has(id)) add("gate_id_unknown", `${label}:${id}`);
    for (const id of derived) if (!idSet.has(id)) add("gate_id_missing", `${label}:${id}`);
  }

  // (3) proof level and evidence class derived from the live enforcement data.
  const m202 = parseM202(m202Text);
  const itemsStatus = parseItemsGateStatus(itemsText);
  const ledgerStatus = parseLedgerStatus(ledgerText);
  const vocabulary = Array.isArray(register?.disposition_vocabulary)
    ? register.disposition_vocabulary
    : [];
  const forbiddenQuantifiers = new Set(
    Array.isArray(register?.forbidden_quantifiers) ? register.forbidden_quantifiers : [],
  );
  const inventoryCounters = new Set([
    ...Object.keys(register?.inventory_counts_displaced?.mapping_counts ?? {}),
    ...Object.keys(m202.counts ?? {}),
  ]);

  for (const gate of gates) {
    const id = gate?.gate_id ?? "?";
    const level = gate?.minimum_validated_proof_level;
    const readmeLevels = readme.gateMinLevels.get(id) ?? new Set();
    const verifierLevels = verifier.gateMinLevels.get(id) ?? new Set();
    const allowedLevels = [...readmeLevels].filter((candidate) => verifierLevels.has(candidate));
    if (!allowedLevels.includes(level)) {
      add("proof_level_mismatch", `${id}:${level} allowed=${allowedLevels.join("|") || "none"}`);
    }
    const requiredClasses = verifier.evidenceClassesByLevel.get(level);
    if (!requiredClasses) {
      add("evidence_class_unknown", `${id}:level ${level}`);
    } else if (!requiredClasses.includes(gate?.evidence_class)) {
      add("evidence_class_not_required_by_proof_level", `${id}:${gate?.evidence_class}`);
    }
    if (nonEmpty(gate?.evidence_class) && !verifier.union.has(gate.evidence_class)) {
      add("evidence_class_unknown", `${id}:${gate.evidence_class}`);
    }
    const declaredClasses = Array.isArray(gate?.required_evidence_classes)
      ? gate.required_evidence_classes
      : [];
    for (const cls of declaredClasses) {
      if (!verifier.union.has(cls)) add("evidence_class_unknown", `${id}:${cls}`);
    }
    if (requiredClasses) {
      const expected = [...requiredClasses].sort();
      const declared = [...declaredClasses].sort();
      if (JSON.stringify(declared) !== JSON.stringify(expected)) {
        add(
          "evidence_class_not_required_by_proof_level",
          `${id}: declared=${declared.join("|")} expected=${expected.join("|")}`,
        );
      }
    }

    // (4) owner, owner_path, evidence-class basis, quantifier, disposition basis.
    if (!nonEmpty(gate?.owner)) add("owner_missing", id);
    if (!nonEmpty(gate?.owner_path)) {
      add("owner_path_missing", id);
    } else if (!fileExists(gate.owner_path) || !tracked(gate.owner_path)) {
      add("owner_path_untracked", `${id}:${gate.owner_path}`);
    }
    if (!nonEmpty(gate?.evidence_class_basis)) add("evidence_class_basis_missing", id);

    // (5) quantifier: named, distinct, measurable, never an inventory count.
    const quantifier = gate?.quantifier ?? {};
    if (!nonEmpty(quantifier.name) || !nonEmpty(quantifier.unit) || !nonEmpty(quantifier.acceptance)) {
      add("quantifier_missing", id);
    }
    if (nonEmpty(quantifier.name)) {
      if (forbiddenQuantifiers.has(quantifier.name)) {
        add("quantifier_name_forbidden", `${id}:${quantifier.name}`);
      }
      if (inventoryCounters.has(quantifier.name)) {
        add("inventory_count_as_quantifier", `${id}:${quantifier.name}`);
      }
    }
    if (nonEmpty(quantifier.acceptance) && !/\d/.test(quantifier.acceptance)) {
      add("quantifier_acceptance_not_quantified", id);
    }

    // (6) anti-smoothing: per-gate disposition derived from live facets only.
    const facetValues = [
      ["registry_status", itemsStatus.get(id), ITEMS],
      ["frozen_snapshot_verdict", m202.gates.get(id), M202],
      ["derived_view_status", ledgerStatus.get(id), LEDGER],
    ];
    for (const [facet, raw, source] of facetValues) {
      if (typeof raw !== "string") {
        add("conflict_undetected", `${id}:${facet} unreadable from ${source}`);
      } else if (!(raw in NORMALIZATION)) {
        add("disposition_unknown", `${id}:${facet}=${raw}`);
      }
    }
    const derivedStates = facetValues
      .filter(([, raw]) => typeof raw === "string" && raw in NORMALIZATION)
      .map(([, raw]) => NORMALIZATION[raw]);
    const distinctStates = [...new Set(derivedStates)];
    const recorded = Array.isArray(gate?.recorded_states) ? gate.recorded_states : [];
    for (const [facet, raw] of facetValues) {
      const entry = recorded.find((candidate) => candidate?.facet === facet);
      if (!entry) {
        add("conflict_undetected", `${id}:${facet} unrecorded`);
        continue;
      }
      if (entry.raw_value !== raw) {
        add("conflict_undetected", `${id}:${facet} raw ${entry.raw_value} != ${raw}`);
      }
      const expected = typeof raw === "string" && raw in NORMALIZATION ? NORMALIZATION[raw] : null;
      if (expected !== null && entry.normalized_state !== expected) {
        add("conflict_smoothed", `${id}:${facet} ${entry.normalized_state} != ${expected}`);
      }
    }
    const recordedStates = [...new Set(recorded.map((entry) => entry?.normalized_state))];
    if (!sameSet(recordedStates, distinctStates)) {
      add(
        "conflict_undetected",
        `${id}: recorded=${recordedStates.join("|")} derived=${distinctStates.join("|")}`,
      );
    }

    if (!vocabulary.includes(gate?.disposition)) {
      add("disposition_unknown", `${id}:${gate?.disposition}`);
    } else if (distinctStates.length > 1) {
      if (gate.disposition !== "conflicted-requires-decision") {
        add("conflict_smoothed", `${id}: ${distinctStates.join("|")} -> ${gate.disposition}`);
      }
      const conflicts = Array.isArray(gate?.conflicts) ? gate.conflicts : [];
      if (conflicts.length === 0) {
        add("conflict_list_empty", id);
      } else {
        const listed = new Set(conflicts.map((conflict) => conflict?.normalized_state));
        for (const state of distinctStates) {
          if (!listed.has(state)) add("conflict_list_empty", `${id}: missing ${state}`);
        }
      }
    } else {
      if (gate.disposition === "conflicted-requires-decision") {
        add("conflict_undetected", `${id}: single state ${distinctStates.join("|")}`);
      }
      if (!["unsatisfied", "satisfied-by-proof-package"].includes(gate.disposition)) {
        add("conflict_undetected", `${id}: ${distinctStates.join("|") || "?"} -> ${gate.disposition}`);
      }
      if (gate.disposition === "satisfied-by-proof-package" && distinctStates.some((s) => s !== "satisfied")) {
        add("conflict_smoothed", `${id}: satisfied over ${distinctStates.join("|")}`);
      }
    }

    // (7) no proof package may be attached to an unproven gate.
    if (gate?.proof_package != null && gate.disposition !== "satisfied-by-proof-package") {
      add("proof_package_without_satisfied_disposition", id);
    }
    if (
      gate?.disposition === "satisfied-by-proof-package" &&
      (gate.proof_package == null ||
        (typeof gate.proof_package === "object" && Object.keys(gate.proof_package).length === 0))
    ) {
      add("satisfied_without_proof_package", id);
    }

    // (8) disposition basis present and per gate.
    if (!nonEmpty(gate?.disposition_basis)) add("disposition_basis_missing", id);

    // (13) source anchors: repo-relative, tracked, never ignored or escaping.
    const anchors = Array.isArray(gate?.source_anchors) ? gate.source_anchors : [];
    for (const anchor of anchors) {
      const anchorPath = anchor?.path;
      if (!nonEmpty(anchorPath)) {
        add("absolute_path_as_source", `${id}: empty anchor`);
        continue;
      }
      if (anchorPath.startsWith("/")) {
        add("absolute_path_as_source", anchorPath);
        continue;
      }
      if (anchorPath.split("/").includes("..")) {
        add("absolute_path_as_source", anchorPath);
        continue;
      }
      if (IGNORED_SOURCE_PREFIXES.some((prefix) => anchorPath.startsWith(prefix))) {
        add("ignored_path_as_source", anchorPath);
      }
    }

    // (33) non-claims on every row.
    if (!Array.isArray(gate?.non_claims) || gate.non_claims.length === 0) {
      add("non_claims_missing", id);
    }
  }

  // (8) pairwise distinct bases, names and decision references.
  const duplicateOf = (values) => {
    const seen = new Map();
    for (const value of values) seen.set(value, (seen.get(value) ?? 0) + 1);
    return [...seen.entries()].filter(([, occurrences]) => occurrences > 1).map(([value]) => value);
  };
  for (const basis of duplicateOf(gates.map((gate) => gate?.disposition_basis))) {
    add("disposition_basis_duplicated", basis);
  }
  for (const name of duplicateOf(gates.map((gate) => gate?.quantifier?.name).filter(nonEmpty))) {
    add("quantifier_name_duplicated", name);
  }
  const decisions = gates
    .map((gate) => gate?.disposition_decision)
    .filter((decision) => decision != null && decision !== "");
  for (const decision of decisions) {
    if (!/^D[0-9]+$/.test(String(decision))) add("disposition_decision_malformed", String(decision));
  }
  for (const decision of duplicateOf(decisions.map(String))) {
    add("disposition_decision_shared", decision);
  }

  // (9) frozen M202 pin: inherited semantic/textual mechanism, never minted.
  const frozen = register?.canonical_sources?.frozen_snapshot ?? {};
  const pinKind = typeof frozen.pin_kind === "string" ? frozen.pin_kind : "";
  if (!/captured-at/.test(pinKind) || !/not[- ]rust[- ]anchored/i.test(pinKind)) {
    add("m202_pin_mislabelled", `pin_kind=${pinKind || "absent"}`);
  }
  if (/"PROOF_GATE_JSON_SHA256"|"PROOF_GATE_JSON_BYTES"/.test(registerText)) {
    add("m202_pin_mislabelled", "register invents a Rust-side M202 constant");
  }
  if (typeof m202Text !== "string") {
    add("m202_semantic_pin_missing", "M202 unreadable");
  } else {
    const { sha, bytes } = rustShaConstants(rustText);
    const stems = RUST_SHA_CONSTANTS.map(([stem]) => stem);
    if (sha.size !== stems.length || bytes.size !== stems.length || !stems.every((stem) => sha.has(stem) && bytes.has(stem))) {
      add("m202_semantic_pin_missing", `rust constants=${[...sha.keys()].join(",") || "none"}`);
    } else {
      if (count(m202Text, '"gate_id":') !== 7) {
        add("m202_semantic_pin_broken", `gate_id count=${count(m202Text, '"gate_id":')}`);
      }
      if (count(m202Text, '"gate_verdict": "unsatisfied"') !== 7) {
        add(
          "m202_semantic_pin_broken",
          `unsatisfied verdict count=${count(m202Text, '"gate_verdict": "unsatisfied"')}`,
        );
      }
      for (const banned of [
        '"gate_verdict": "validated"',
        '"gate_verdict": "complete',
        '"gate_verdict": "satisfied"',
        '"gate_verdict": "checked"',
        '"gate_verdict": "proven',
        '"validated"',
      ]) {
        if (m202Text.includes(banned)) add("m202_semantic_pin_broken", `banned ${banned}`);
      }
      for (const token of [
        '"disposition": "active"',
        '"disposition_decision": "D430"',
        '"authoritative": false',
        '"punkt_admitted": 0',
      ]) {
        if (!m202Text.includes(token)) add("m202_semantic_pin_broken", `missing ${token}`);
      }
      for (const [stem, livePath] of RUST_SHA_CONSTANTS) {
        const hex = sha.get(stem);
        const occurrences = count(m202Text, hex);
        if (occurrences !== 1) {
          add("m202_semantic_pin_broken", `${stem} hex occurrences=${occurrences}`);
        }
        if (fileExists(livePath)) {
          if (sha256(livePath) !== hex) add("m202_semantic_pin_broken", `${livePath} live sha drift`);
          if (repoBytes(livePath) !== bytes.get(stem)) {
            add("m202_semantic_pin_broken", `${livePath} live bytes drift`);
          }
        } else {
          add("m202_semantic_pin_broken", `${livePath} missing`);
        }
      }
      // Captured-at baseline drift (detection only, not an anchor claim).
      if (frozen.sha256 !== sha256(M202)) {
        add("m202_semantic_pin_broken", `captured-at sha drift: ${frozen.sha256}`);
      }
      if (frozen.bytes !== repoBytes(M202)) {
        add("m202_semantic_pin_broken", `captured-at bytes drift: ${frozen.bytes}`);
      }
    }
  }
  if (frozenDelta !== "") {
    add("m202_semantic_pin_broken", `frozen input worktree delta: ${frozenDelta}`);
  }

  // (10) the displaced inventory counts must stay verbatim frozen M202 counts.
  const displacedCounts = register?.inventory_counts_displaced?.mapping_counts ?? null;
  const frozenCounts = m202.counts;
  if (
    displacedCounts === null ||
    frozenCounts === null ||
    JSON.stringify(Object.entries(displacedCounts).sort()) !==
      JSON.stringify(Object.entries(frozenCounts).sort())
  ) {
    add(
      "inventory_displacement_mismatch",
      `register=${JSON.stringify(displacedCounts)} frozen=${JSON.stringify(frozenCounts)}`,
    );
  }

  // (11) the derived ledger view must never be marked authoritative.
  const ledgerAuthority = register?.canonical_sources?.derived_non_authoritative_view?.authority;
  if (typeof ledgerAuthority !== "string" || !/non-authoritative/i.test(ledgerAuthority)) {
    add("claims_ledger_marked_authoritative", `authority=${ledgerAuthority}`);
  }
  if (register?.authoritative !== false) {
    add("claims_ledger_marked_authoritative", `register.authoritative=${register?.authoritative}`);
  }

  // (12) out-of-register ids: exactly the ledger ids absent from the live surface.
  const derivedExtras = [...ledgerGateIds(ledgerText)]
    .filter((id) => !readme.gateIds.has(id) && !verifier.gateIds.has(id))
    .sort();
  const declaredExtras = (Array.isArray(register?.out_of_register_gate_ids)
    ? register.out_of_register_gate_ids
    : []
  )
    .map((entry) => (typeof entry === "string" ? entry : entry?.gate_id))
    .filter(nonEmpty)
    .sort();
  if (!sameSet(declaredExtras, derivedExtras)) {
    add(
      "out_of_register_id_promoted",
      `declared=${declaredExtras.join(",")} derived=${derivedExtras.join(",")}`,
    );
  }
  for (const id of declaredExtras) {
    if (idSet.has(id)) add("out_of_register_id_promoted", `${id} is registered as a gate`);
    if (readme.gateIds.has(id) || verifier.gateIds.has(id)) {
      add("out_of_register_id_promoted", `${id} appears in the live surface`);
    }
  }

  // (13) register-level source anchors and non-claims.
  for (const [label, anchorPath] of Object.entries(register?.canonical_sources ?? {})) {
    const candidate = anchorPath?.path;
    if (!nonEmpty(candidate)) continue;
    if (candidate.startsWith("/") || candidate.split("/").includes("..")) {
      add("absolute_path_as_source", `${label}:${candidate}`);
    } else if (IGNORED_SOURCE_PREFIXES.some((prefix) => candidate.startsWith(prefix))) {
      add("ignored_path_as_source", `${label}:${candidate}`);
    }
  }
  if (!Array.isArray(register?.non_claims) || register.non_claims.length === 0) {
    add("non_claims_missing", "register");
  }

  // (R035 honesty) R035 stays active until every named gate carries a package.
  if (register?.requirement_disposition !== "active") {
    add("r035_promoted_to_validated", `requirement_disposition=${register?.requirement_disposition}`);
  }
  if (register?.requirement_disposition_decision !== "D430") {
    add("r035_promoted_to_validated", `decision=${register?.requirement_disposition_decision}`);
  }
  if (/"validated"/.test(registerText)) {
    add("r035_promoted_to_validated", 'bare "validated" value present in the register');
  }

  return { ok: errors.length === 0, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const liveRegisterText = readRepo(REGISTER);
const liveRegister = JSON.parse(liveRegisterText);
const liveReadme = readRepo(README);
const liveVerifier = readRepo(VERIFIER);
const liveM202 = readRepo(M202);
const liveItems = readRepo(ITEMS);
const liveLedger = readRepo(LEDGER);
const liveRust = readRepo(RUST_PIN);

const register = liveRegister;

function cloneRegister() {
  return JSON.parse(liveRegisterText);
}

function fixture(mutate) {
  const next = cloneRegister();
  const returned = mutate(next) ?? next;
  assert.notEqual(
    JSON.stringify(returned),
    JSON.stringify(liveRegister),
    "fixture mutation did not modify the register",
  );
  return returned;
}

function expectCode(result, expected) {
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
}

const BT = String.fromCharCode(96);

function readmeRow(trigger, bucket, gateId, level) {
  return `| ${trigger} | ${bucket} | ${BT}${gateId}${BT} | ${BT}${level}${BT} |`;
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M209 S01 gate register validates against the live enforcement surfaces", () => {
  const result = validateRegister(register);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors, null, 2)}`);
  assert.equal(result.ok, true);
});

test("register gate ids are derived from README R035 and ONTOLOGY_PROMOTION_RULES", () => {
  const verifier = parseVerifier(liveVerifier);
  const readme = parseReadmeR035(liveReadme);
  assert.ok(sameSet([...verifier.gateIds], CANONICAL_GATE_IDS), `verifier=${[...verifier.gateIds].join(",")}`);
  assert.ok(sameSet([...readme.gateIds], CANONICAL_GATE_IDS), `readme=${[...readme.gateIds].join(",")}`);
  assert.ok(sameSet(register.gates.map((gate) => gate.gate_id), CANONICAL_GATE_IDS));
  assert.equal(register.gates.length, 7, "register must carry exactly seven gates");
  assert.equal(register.gate_count, 7, "gate_count must be seven");
});

test("per-gate evidence class is derived from PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES", () => {
  const verifier = parseVerifier(liveVerifier);
  const readme = parseReadmeR035(liveReadme);
  assert.ok(verifier.evidenceClassesByLevel.size >= 6, "live class table must be parsed");
  for (const gate of register.gates) {
    const id = gate.gate_id;
    const level = gate.minimum_validated_proof_level;
    const allowed = [...(readme.gateMinLevels.get(id) ?? [])].filter((candidate) =>
      (verifier.gateMinLevels.get(id) ?? new Set()).has(candidate),
    );
    assert.ok(allowed.includes(level), `${id}: ${level} not live-derived (${allowed.join("|")})`);
    const required = verifier.evidenceClassesByLevel.get(level);
    assert.ok(required, `${id}: no live class set for ${level}`);
    assert.ok(required.includes(gate.evidence_class), `${id}: ${gate.evidence_class} not required`);
    assert.ok(
      [...gate.required_evidence_classes].sort().join("|") === [...required].sort().join("|"),
      `${id}: declared classes ${gate.required_evidence_classes.join("|")} != live ${[...required].join("|")}`,
    );
  }
});

test("anti-smoothing: every gate carries its own derived disposition", () => {
  const itemsStatus = parseItemsGateStatus(liveItems);
  const m202 = parseM202(liveM202);
  const ledgerStatus = parseLedgerStatus(liveLedger);
  const stateSets = new Map();
  for (const gate of register.gates) {
    const states = [
      NORMALIZATION[itemsStatus.get(gate.gate_id)],
      NORMALIZATION[m202.gates.get(gate.gate_id)],
      NORMALIZATION[ledgerStatus.get(gate.gate_id)],
    ].filter((state) => state !== undefined);
    stateSets.set(gate.gate_id, new Set(states));
  }
  for (const gate of register.gates) {
    const states = stateSets.get(gate.gate_id);
    if (states.size === 1) {
      assert.ok(
        ["unsatisfied", "satisfied-by-proof-package"].includes(gate.disposition),
        `${gate.gate_id}: single state ${[...states].join("|")} must not be ${gate.disposition}`,
      );
    } else {
      assert.equal(
        gate.disposition,
        "conflicted-requires-decision",
        `${gate.gate_id}: divergent states ${[...states].join("|")} must stay conflicted`,
      );
      assert.ok(gate.conflicts.length > 0, `${gate.gate_id}: conflicts must be enumerated`);
      for (const state of states) {
        assert.ok(
          gate.conflicts.some((conflict) => conflict.normalized_state === state),
          `${gate.gate_id}: conflicts must list ${state}`,
        );
      }
    }
  }
  // GATE-G015 is the live divergence: registry/derived say superseded, M202 says unsatisfied.
  assert.ok(
    sameSet([...stateSets.get("GATE-G015")], ["superseded", "unsatisfied"]),
    "GATE-G015 must diverge across sources",
  );
  assert.equal(byId(register, "GATE-G015").disposition, "conflicted-requires-decision");
  const bases = register.gates.map((gate) => gate.disposition_basis);
  assert.equal(new Set(bases).size, 7, "disposition_basis must be pairwise distinct");
  const decisions = register.gates.map((gate) => gate.disposition_decision).filter((value) => value != null);
  assert.equal(new Set(decisions).size, decisions.length, "no decision may authorise two gates");
  for (const gate of register.gates) {
    assert.equal(gate.proof_package, null, `${gate.gate_id}: no proof package may be attached`);
  }
});

test("frozen M202 pin is inherited from the Rust suite, never minted here", () => {
  const { sha, bytes } = rustShaConstants(liveRust);
  assert.equal(sha.size, 4, "the suite must carry exactly four external sha constants");
  assert.equal(bytes.size, 4, "the suite must carry exactly four external byte constants");
  assert.ok(!/PROOF_GATE_JSON_SHA256|PROOF_GATE_JSON_BYTES/.test(liveRust), "no M202 hash constant may exist");
  for (const [stem, livePath] of RUST_SHA_CONSTANTS) {
    assert.equal(count(liveM202, sha.get(stem)), 1, `${stem} hex must occur once in M202`);
    assert.equal(sha256(livePath), sha.get(stem), `${livePath} sha must match the Rust constant`);
    assert.equal(repoBytes(livePath), bytes.get(stem), `${livePath} bytes must match the Rust constant`);
  }
  assert.equal(count(liveM202, '"gate_id":'), 7);
  assert.equal(count(liveM202, '"gate_verdict": "unsatisfied"'), 7);
  assert.equal(count(liveM202, '"validated"'), 0);
  assert.ok(register.canonical_sources.frozen_snapshot.pin_kind.startsWith("captured-at"));
  assert.ok(!/"PROOF_GATE_JSON_SHA256"/.test(liveRegisterText));
  assert.equal(register.canonical_sources.frozen_snapshot.sha256, sha256(M202));
  assert.equal(register.canonical_sources.frozen_snapshot.bytes, repoBytes(M202));
  assert.equal(worktreeDelta(FROZEN_INPUTS), "", "the frozen inputs must carry no worktree delta");
});

test("inventory counts are displaced, never standing as a quantifier", () => {
  const m202 = parseM202(liveM202);
  const displaced = register.inventory_counts_displaced.mapping_counts;
  assert.deepEqual(displaced, m202.counts, "displaced counts must match frozen M202 verbatim");
  const counters = new Set(Object.keys(displaced));
  for (const gate of register.gates) {
    assert.ok(!counters.has(gate.quantifier.name), `${gate.quantifier.name} is an inventory count`);
    assert.ok(
      !register.forbidden_quantifiers.includes(gate.quantifier.name),
      `${gate.quantifier.name} is forbidden`,
    );
    assert.ok(/\d/.test(gate.quantifier.acceptance), `${gate.gate_id}: acceptance must be quantified`);
  }
  assert.equal(new Set(register.gates.map((gate) => gate.quantifier.name)).size, 7);
});

test("out-of-register ids are exactly the derived ledger extras", () => {
  const readme = parseReadmeR035(liveReadme);
  const verifier = parseVerifier(liveVerifier);
  const derived = [...ledgerGateIds(liveLedger)]
    .filter((id) => !readme.gateIds.has(id) && !verifier.gateIds.has(id))
    .sort();
  const declared = register.out_of_register_gate_ids.map((entry) => entry.gate_id).sort();
  assert.ok(sameSet(declared, derived), `declared=${declared.join(",")} derived=${derived.join(",")}`);
  assert.equal(derived.length, 7, "exactly seven extras are expected");
});

test("the register and its declared inputs are tracked", () => {
  for (const artifact of [REGISTER, README, VERIFIER, M202, ITEMS, LEDGER, RUST_PIN]) {
    assert.ok(repoExists(artifact), `${artifact} must exist`);
    assert.ok(isTracked(artifact), `${artifact} must stay tracked`);
  }
  // This contract is authored in T02 and committed by closeout, so it must
  // exist and be repository-relative, but `git ls-files` cannot see it yet.
  assert.ok(repoExists(CONTRACT_PATH), `${CONTRACT_PATH} must exist`);
  assert.ok(!CONTRACT_PATH.startsWith("/"), "the contract must be repository-relative");
  for (const gate of register.gates) {
    assert.ok(isTracked(gate.owner_path), `${gate.gate_id}: ${gate.owner_path} must stay tracked`);
  }
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

test("the contract never reads an ignored, .gsd or absolute path as evidence", () => {
  const source = readRepo(CONTRACT_PATH);
  const declared = [...source.matchAll(/^const\s+[A-Za-z_$][\w$]*\s*=\s*"([^"]+)";$/gm)].map(
    (match) => match[1],
  );
  for (const value of declared) {
    assert.ok(!value.startsWith("/"), `absolute path literal ${value} is not admissible evidence`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!value.startsWith(prefix), `ignored path literal ${value} is not admissible evidence`);
    }
  }
  for (const entry of [
    REGISTER,
    README,
    VERIFIER,
    M202,
    ITEMS,
    LEDGER,
    RUST_PIN,
    CONTRACT_PATH,
    ...FROZEN_INPUTS,
    ...RUST_SHA_CONSTANTS.map(([, livePath]) => livePath),
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
});

test("the contract uses only the two allowed git subprocesses", () => {
  const source = readRepo(CONTRACT_PATH);
  assert.ok(source.includes('"ls-files", "--error-unmatch"'), "tracked-file proof is required");
  assert.ok(source.includes('"status", "--porcelain"'), "frozen-input proof is required");
  // Only subprocess launch syntax is asserted here: a bare word in prose is not
  // an executable invocation.
  for (const executable of ["car" + "go", "cu" + "rl", "wg" + "et", "n" + "pm", "n" + "px", "kubectl"]) {
    const launch = new RegExp(
      "(?:execFileSync|spawnSync|execSync|spawn)\\(\\s*[\"'`]" + executable + "\\b",
    );
    assert.ok(!launch.test(source), `${executable} must not be launched by this contract`);
  }
});

test("the contract never emits the slice verify marker", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifyMarker = ["M209_S01", "VERIFY_OK"].join("_");
  const emitter = new RegExp("console\\.log\\(\\s*[\"'`]" + verifyMarker);
  assert.ok(!emitter.test(source), `${verifyMarker} must be unreachable by construction`);
});

test("the contract never runs the architecture verifier", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifierName = "verify-architecture-graph";
  const runPattern = new RegExp(
    "(?:execFileSync|spawnSync|execSync)\\(\\s*[\"'`][^\"'`]*" + verifierName,
  );
  assert.ok(!runPattern.test(source), "scripts/verify-architecture-graph.py must be parsed as text only");
  const checkFlag = "-".repeat(2) + "check";
  assert.ok(!source.includes(checkFlag), `the verifier must never be run with ${checkFlag} here`);
});

// ---------------------------------------------------------------------------
// fail-closed negatives (each code fires against a mutated register or source)
// ---------------------------------------------------------------------------

test("negative: register identity and gate-count drift", () => {
  expectCode(validateRegister(fixture((r) => { r.schema_version = "law-nexus/other/v9"; })), "schema_version_mismatch");
  expectCode(validateRegister(fixture((r) => { r.gates.pop(); })), "gate_count_mismatch");
});

test("negative: gate id set drift", () => {
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].gate_id = "GATE-LEGAL-COLLISION-POLICY"; })),
    "gate_id_unknown",
  );
  expectCode(validateRegister(fixture((r) => { r.gates.splice(0, 1); })), "gate_id_missing");
  expectCode(
    validateRegister(fixture((r) => { r.gates[1].gate_id = r.gates[0].gate_id; })),
    "gate_id_duplicated",
  );
});

test("negative: owner and owner_path drift", () => {
  expectCode(validateRegister(fixture((r) => { r.gates[0].owner = ""; })), "owner_missing");
  expectCode(validateRegister(fixture((r) => { r.gates[0].owner_path = ""; })), "owner_path_missing");
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].owner_path = "crates/no-such-owner"; })),
    "owner_path_untracked",
  );
});

test("negative: evidence class and proof level drift", () => {
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].evidence_class = "galaxy-brain"; })),
    "evidence_class_unknown",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].evidence_class = "runtime-artifact"; })),
    "evidence_class_not_required_by_proof_level",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].evidence_class_basis = ""; })),
    "evidence_class_basis_missing",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].minimum_validated_proof_level = "production-observation"; })),
    "proof_level_mismatch",
  );
});

test("negative: quantifier drift", () => {
  expectCode(validateRegister(fixture((r) => { delete r.gates[0].quantifier; })), "quantifier_missing");
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].quantifier.name = "registry_rows"; })),
    "quantifier_name_forbidden",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[1].quantifier.name = r.gates[0].quantifier.name; })),
    "quantifier_name_duplicated",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].quantifier.acceptance = "no numbers at all"; })),
    "quantifier_acceptance_not_quantified",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].quantifier.name = "fz44_statya"; })),
    "inventory_count_as_quantifier",
  );
});

test("negative: disposition drift and smoothing", () => {
  expectCode(validateRegister(fixture((r) => { r.gates[0].disposition = "sorted"; })), "disposition_unknown");
  expectCode(validateRegister(fixture((r) => { r.gates[0].disposition_basis = ""; })), "disposition_basis_missing");
  expectCode(
    validateRegister(fixture((r) => { r.gates[1].disposition_basis = r.gates[0].disposition_basis; })),
    "disposition_basis_duplicated",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].disposition_decision = "D430"; r.gates[1].disposition_decision = "D430"; })),
    "disposition_decision_shared",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].disposition_decision = "Dxx"; })),
    "disposition_decision_malformed",
  );
});

test("negative: conflict detection cannot be smoothed or invented", () => {
  expectCode(
    validateRegister(fixture((r) => { byId(r, "GATE-G015").disposition = "unsatisfied"; })),
    "conflict_smoothed",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].disposition = "conflicted-requires-decision"; })),
    "conflict_undetected",
  );
  expectCode(
    validateRegister(fixture((r) => { byId(r, "GATE-G015").conflicts = []; })),
    "conflict_list_empty",
  );
});

test("negative: proof packages cannot be smuggled in", () => {
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].proof_package = { ref: "minted" }; })),
    "proof_package_without_satisfied_disposition",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].disposition = "satisfied-by-proof-package"; })),
    "satisfied_without_proof_package",
  );
});

test("negative: frozen M202 pin breaks, goes missing or is mislabelled", () => {
  expectCode(
    validateRegister(register, {
      m202Text: liveM202.replace('"gate_verdict": "unsatisfied"', '"gate_verdict": "satisfied"'),
    }),
    "m202_semantic_pin_broken",
  );
  expectCode(validateRegister(register, { m202Text: null }), "m202_semantic_pin_missing");
  expectCode(
    validateRegister(fixture((r) => { delete r.canonical_sources.frozen_snapshot.pin_kind; })),
    "m202_pin_mislabelled",
  );
});

test("negative: inventory displacement and ledger authority drift", () => {
  expectCode(
    validateRegister(fixture((r) => { r.inventory_counts_displaced.mapping_counts.punkt_admitted = 1; })),
    "inventory_displacement_mismatch",
  );
  expectCode(
    validateRegister(
      fixture((r) => { r.canonical_sources.derived_non_authoritative_view.authority = "authoritative"; }),
    ),
    "claims_ledger_marked_authoritative",
  );
});

test("negative: non-canonical gate promoted into the live surface", () => {
  const promoted = `${readmeRow("legal collision policy", "proof-gated legal-priority candidate", "GATE-LEGAL-COLLISION-POLICY", "static-check")}\n`;
  expectCode(
    validateRegister(register, {
      readmeText: liveReadme.replace(
        "| Akoma Ntoso, LegalDocML, FRBR |",
        `${promoted}| Akoma Ntoso, LegalDocML, FRBR |`,
      ),
    }),
    "out_of_register_id_promoted",
  );
});

test("negative: ignored and absolute source anchors", () => {
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].source_anchors[0].path = ".gsd/phases/x.md"; })),
    "ignored_path_as_source",
  );
  expectCode(
    validateRegister(fixture((r) => { r.gates[0].source_anchors[0].path = "/tmp/x.md"; })),
    "absolute_path_as_source",
  );
});

test("negative: R035 promoted off active and missing non-claims", () => {
  expectCode(
    validateRegister(fixture((r) => { r.requirement_disposition = "validated"; })),
    "r035_promoted_to_validated",
  );
  expectCode(validateRegister(fixture((r) => { r.non_claims = []; })), "non_claims_missing");
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code. The test below asserts
// that each mutation actually makes its code fire and actually makes the register
// fail closed, so a code can never be documented without being reachable, and can
// never be reachable without being documented.
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  { code: "schema_version_mismatch", mutate: (r) => { r.schema_version = "law-nexus/other/v9"; } },
  { code: "gate_count_mismatch", mutate: (r) => { r.gates.pop(); } },
  { code: "gate_id_unknown", mutate: (r) => { r.gates[0].gate_id = "GATE-LEGAL-COLLISION-POLICY"; } },
  { code: "gate_id_missing", mutate: (r) => { r.gates.splice(0, 1); } },
  { code: "gate_id_duplicated", mutate: (r) => { r.gates[1].gate_id = r.gates[0].gate_id; } },
  { code: "owner_missing", mutate: (r) => { r.gates[0].owner = ""; } },
  { code: "owner_path_missing", mutate: (r) => { r.gates[0].owner_path = ""; } },
  { code: "owner_path_untracked", mutate: (r) => { r.gates[0].owner_path = "crates/no-such-owner"; } },
  { code: "evidence_class_unknown", mutate: (r) => { r.gates[0].evidence_class = "galaxy-brain"; } },
  {
    code: "evidence_class_not_required_by_proof_level",
    mutate: (r) => { r.gates[0].evidence_class = "runtime-artifact"; },
  },
  { code: "evidence_class_basis_missing", mutate: (r) => { r.gates[0].evidence_class_basis = ""; } },
  {
    code: "proof_level_mismatch",
    mutate: (r) => { r.gates[0].minimum_validated_proof_level = "production-observation"; },
  },
  { code: "quantifier_missing", mutate: (r) => { delete r.gates[0].quantifier; } },
  { code: "quantifier_name_forbidden", mutate: (r) => { r.gates[0].quantifier.name = "registry_rows"; } },
  {
    code: "quantifier_name_duplicated",
    mutate: (r) => { r.gates[1].quantifier.name = r.gates[0].quantifier.name; },
  },
  {
    code: "quantifier_acceptance_not_quantified",
    mutate: (r) => { r.gates[0].quantifier.acceptance = "no numbers at all"; },
  },
  { code: "disposition_unknown", mutate: (r) => { r.gates[0].disposition = "sorted"; } },
  { code: "disposition_basis_missing", mutate: (r) => { r.gates[0].disposition_basis = ""; } },
  {
    code: "disposition_basis_duplicated",
    mutate: (r) => { r.gates[1].disposition_basis = r.gates[0].disposition_basis; },
  },
  {
    code: "disposition_decision_shared",
    mutate: (r) => { r.gates[0].disposition_decision = "D430"; r.gates[1].disposition_decision = "D430"; },
  },
  { code: "disposition_decision_malformed", mutate: (r) => { r.gates[0].disposition_decision = "Dxx"; } },
  { code: "conflict_smoothed", mutate: (r) => { byId(r, "GATE-G015").disposition = "unsatisfied"; } },
  { code: "conflict_undetected", mutate: (r) => { r.gates[0].disposition = "conflicted-requires-decision"; } },
  { code: "conflict_list_empty", mutate: (r) => { byId(r, "GATE-G015").conflicts = []; } },
  {
    code: "proof_package_without_satisfied_disposition",
    mutate: (r) => { r.gates[0].proof_package = { ref: "minted" }; },
  },
  {
    code: "satisfied_without_proof_package",
    mutate: (r) => { r.gates[0].disposition = "satisfied-by-proof-package"; },
  },
  {
    code: "m202_semantic_pin_broken",
    sources: {
      m202Text: liveM202.replace('"gate_verdict": "unsatisfied"', '"gate_verdict": "satisfied"'),
    },
  },
  { code: "m202_semantic_pin_missing", sources: { m202Text: null } },
  {
    code: "m202_pin_mislabelled",
    mutate: (r) => { delete r.canonical_sources.frozen_snapshot.pin_kind; },
  },
  {
    code: "inventory_count_as_quantifier",
    mutate: (r) => { r.gates[0].quantifier.name = "fz44_statya"; },
  },
  {
    code: "inventory_displacement_mismatch",
    mutate: (r) => { r.inventory_counts_displaced.mapping_counts.punkt_admitted = 1; },
  },
  {
    code: "claims_ledger_marked_authoritative",
    mutate: (r) => { r.canonical_sources.derived_non_authoritative_view.authority = "authoritative"; },
  },
  {
    code: "out_of_register_id_promoted",
    sources: {
      readmeText: liveReadme.replace(
        "| Akoma Ntoso, LegalDocML, FRBR |",
        `${readmeRow("legal collision policy", "proof-gated legal-priority candidate", "GATE-LEGAL-COLLISION-POLICY", "static-check")}\n| Akoma Ntoso, LegalDocML, FRBR |`,
      ),
    },
  },
  {
    code: "ignored_path_as_source",
    mutate: (r) => { r.gates[0].source_anchors[0].path = ".gsd/phases/x.md"; },
  },
  {
    code: "absolute_path_as_source",
    mutate: (r) => { r.gates[0].source_anchors[0].path = "/tmp/x.md"; },
  },
  { code: "r035_promoted_to_validated", mutate: (r) => { r.requirement_disposition = "validated"; } },
  { code: "non_claims_missing", mutate: (r) => { r.non_claims = []; } },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const target = entry.mutate ? fixture(entry.mutate) : register;
    const result = validateRegister(target, entry.sources ?? {});
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    assert.equal(result.ok, false, `${entry.code} must make the register fail closed`);
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
// markers (emitted only after the register contract holds)
// ---------------------------------------------------------------------------

test("M209 S01 gate register markers", () => {
  const result = validateRegister(register);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors)}`);
  const verifier = parseVerifier(liveVerifier);
  console.log("M209_S01_REGISTER_OK");
  console.log(`register_gates=${register.gates.length}`);
  console.log("M209_S01_GATE_IDS_OK");
  console.log(`gate_ids=${CANONICAL_GATE_IDS.length}`);
  console.log("M209_S01_EVIDENCE_CLASS_OK");
  console.log(`proof_levels=${verifier.evidenceClassesByLevel.size}`);
  console.log("M209_S01_ANTISMOOTHING_OK");
  console.log(`distinct_dispositions=${new Set(register.gates.map((gate) => gate.disposition)).size}`);
  console.log("M209_S01_FROZEN_PIN_OK");
});
