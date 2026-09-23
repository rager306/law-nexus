#!/usr/bin/env node
// R035 gate-by-gate acceptance adjudication for M209-2yg6ix (S04 T03, D558).
//
// WHY THIS FILE EXISTS
// S01 produced a R035 gate register: seven gates, each with a named quantifier,
// an owner, a minimum validated proof level and three recorded evidence states.
// A register of recorded states is not an acceptance decision (D538, D558).
// S04 has to decide, gate by gate and by rule rather than by opinion, whether
// any of those seven gates can be accepted -- and the honest answer has to be
// derived from the live canonical sources, not copied from the register.
//
// So this script re-derives the gate composition and every gate requirement
// from the live canonical surfaces:
//   * the R035 table in prd/architecture/README.md (trigger terms, safe bucket,
//     required gate ids, minimum validated proof level);
//   * ONTOLOGY_PROMOTION_RULES / PROOF_LEVEL_ORDER /
//     PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES in scripts/verify-architecture-graph.py
//     (rule trigger terms, required gate ids, minimum proof level, evidence
//     classes admitted at each level);
// and cross-checks the resulting seven-id set against the S01 register and the
// frozen M202 snapshot. A set disagreement is `gate_set_mismatch`; a byte or
// level disagreement between the live sources is `canonical_source_drift`.
//
// WHAT IT IS NOT (D537, D539, D558, D559)
// `scripts/verify-architecture-graph.py` is read as a canonical constant source
// only and is never executed as a gate (D537). No architecture projection is
// written, no requirement record is mutated, no registry row is promoted. S02
// and S03 produced bounded inputs; bounded input is not a proof package, so
// every gate row carries proof_package=null, accepted=0 and gates_promoted=0,
// and the closest S02/S03 artifacts are recorded with an explicit statement of
// why they are not the required evidence class.
//
// OUTPUT
//   prd/migration/rust-evidence/m209-s04-r035-gate-adjudication.json
//     schema law-nexus/m209-r035-gate-adjudication/v1
//
// USAGE
//   node scripts/m209_s04_gate_adjudication.mjs --mode gates --out prd/migration/rust-evidence/m209-s04-r035-gate-adjudication.json
//   node scripts/m209_s04_gate_adjudication.mjs --mode gates --check
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

export const SCHEMA = "law-nexus/m209-r035-gate-adjudication/v1";
export const KIND = "m209-s04-r035-gate-adjudication";
export const MILESTONE = "M209-2yg6ix";
export const SLICE = "S04";
export const TASK = "T03";
export const ARTIFACT_PATH = "prd/migration/rust-evidence/m209-s04-r035-gate-adjudication.json";
export const OUT_PREFIX = "prd/migration/rust-evidence/m209-s04-";
export const README_PATH = "prd/architecture/README.md";
export const VERIFIER_PATH = "scripts/verify-architecture-graph.py";
export const REGISTER_PATH = "prd/architecture/m209-s01-r035-gate-register.json";
export const FROZEN_M202_PATH = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
export const CORROBORATION_PATH = "prd/migration/rust-evidence/m209-s04-corroboration-evidence.json";
export const S02_EXTRACTION_EVIDENCE =
  "prd/migration/rust-evidence/m209-s02-extraction-evidence.json";
export const S02_ADMISSION_REGENERATION =
  "prd/migration/rust-evidence/m209-s02-admission-regeneration-evidence.json";
export const S02_HIERARCHY_CANDIDATES =
  "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";

// The live canonical pins. They are declared here and re-derived from the live
// bytes below; the same pins are independently declared by the S01 register and
// by the T01 corroboration artifact, so a drift is caught on three legs.
export const CANONICAL_PINS = Object.freeze({
  readme: {
    bytes: 48094,
    sha256: "sha256:ca010d2a6aa6acea72ceea8fc5b5e6843d995a99f33a7d1a91d428a5efcaef83",
  },
  verifier: {
    bytes: 69089,
    sha256: "sha256:6b8c3a1c7d9f280c623c6395e99ee5a853c4b9d45f3b7d7c31582805e2f5374c",
  },
  register: {
    bytes: 35830,
    sha256: "sha256:bbbf9f56864f4abd5e769b06ad9dc12ef0c6ee40798e0ca0992a5037bf60fd4d",
  },
  frozen_m202: {
    bytes: 7762,
    sha256: "sha256:4e95a20e774fa9e551921922cedde7e6bcdd9fbdceb87d2c640ed5795859ca83",
  },
});

// The proof-level ladder transcribed independently of the verifier constant;
// the live parse must reproduce it or the run fails closed.
export const PROOF_LEVEL_ORDER_DECLARED = Object.freeze({
  none: 0,
  "source-anchor": 1,
  "static-check": 2,
  "unit-test": 3,
  "integration-test": 4,
  "runtime-smoke": 5,
  "real-document-proof": 6,
  "production-observation": 7,
});

// The closed D558 acceptance vocabulary. `rejected-as-stated` is admitted by the
// decision but is not used by any gate row here.
export const DISPOSITION_VOCABULARY = Object.freeze([
  "accepted-at-bounded-scope",
  "hold-requires-owner-decision",
  "hold-with-precise-debt",
  "rejected-as-stated",
]);

// D539 forbidden quantifiers: the M202 inventory counters. None of them may
// stand as a gate quantifier or as a disposition.
export const INVENTORY_QUANTIFIERS = Object.freeze([
  "admitted_candidate_backed",
  "candidates_duplicate",
  "candidates_extracted",
  "candidates_unique",
  "fz44_glava",
  "fz44_statya",
  "legacy_human",
  "punkt_admitted",
  "registry_rows",
  "suites_cited",
]);

// No gate has a proof package today (D539, D558). The map is explicit rather
// than implicit so the acceptance rule is exercised by a real code path.
export const PROOF_PACKAGES = Object.freeze({});

export const MIN_LEVEL_RULE =
  "the first gate id of a README R035 row (and of an ONTOLOGY_PROMOTION_RULES entry) is that row's primary gate; the row's trigger terms, safe bucket and minimum validated proof level attach to the primary gate only, so a gate named as a secondary id in another row inherits nothing from that row";

export const TERM_SPLIT_RULE =
  "README trigger terms are split on comma-space, except that a bare 1-3 digit token followed by a 000-prefixed token containing '-document' is a thousands-separated term and is rejoined";

export const ADJUDICATION_RULE =
  "disposition(gate) = hold-requires-owner-decision when the gate's recorded states disagree; otherwise accepted-at-bounded-scope only when a tracked repository-relative proof package declares the same gate_id, its evidence class is a member of PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES[minimum_validated_proof_level], its proof level is at or above the gate minimum and its quantifier measured value meets the acceptance threshold; otherwise hold-with-precise-debt";

// The closest S02/S03 evidence per gate. This is a *relation* table, never a
// proof: each entry states why the artifact is not the required evidence class.
export const EVIDENCE_RELATIONS = Object.freeze({
  "GATE-AKOMA-FRBR-NORMALIZATION": {
    relation: "bounded-input",
    artifacts: [
      {
        relative_path: S02_HIERARCHY_CANDIDATES,
        touch_basis:
          "the live hierarchy extraction projects one tracked edition into level/path identities (glava/statya/chast/punkt/paragraph), the closest M209 artifact to a normalized legal-unit projection",
      },
    ],
    why_not_required:
      "it is one-document extraction candidate output, not a normalization conformance test artifact over the declared LegalUnit/ActEdition/EvidenceSpan field set; it declares no gate_id and measures no unmapped-field count",
  },
  "GATE-LKIF-DEONTIC-BENCHMARK": {
    relation: "none",
    artifacts: [],
    why_not_required:
      "no M209 S02 or S03 artifact domain-touches deontic mapping; the closest recorded statement is the frozen M202 gate_note that no LKIF deontic benchmark was run",
  },
  "GATE-RUSLEGALCORE-SCOPE": {
    relation: "bounded-input",
    artifacts: [
      {
        relative_path: S02_EXTRACTION_EVIDENCE,
        touch_basis:
          "the live 44-FZ extraction declares a decomposition of the tracked edition into 1901 identities, the closest M209 artifact to a legal-domain scope inventory",
      },
    ],
    why_not_required:
      "it is a one-document hierarchy denominator, not a published included/excluded class table with competency-question coverage; it declares no gate_id and no scoped class ratio",
  },
  "GATE-BFO-GOST-ALIGNMENT": {
    relation: "none",
    artifacts: [],
    why_not_required:
      "no M209 S02 or S03 artifact domain-touches BFO, GOST, OWL or Common Logic alignment; the frozen M202 gate_note records that no OWL or Common Logic rendering was produced",
  },
  "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION": {
    relation: "none",
    artifacts: [],
    why_not_required:
      "no M209 S02 or S03 artifact builds or benchmarks an ontology-aware retrieval integration; registry admission evidence is a projection regeneration, not a retrieval benchmark",
  },
  "GATE-G015": {
    relation: "none",
    artifacts: [],
    why_not_required:
      "no M209 S02 or S03 artifact records runtime query plans or load metrics; the recorded state conflict is preserved and requires an owner decision",
  },
  "GATE-PILOT-SCALE-READINESS": {
    relation: "bounded-input",
    artifacts: [
      {
        relative_path: S02_EXTRACTION_EVIDENCE,
        touch_basis:
          "the live extraction measures one tracked source document and declares its identity denominator, the closest M209 artifact to a fixed-corpus run",
      },
    ],
    why_not_required:
      "it is a one-document extraction denominator of 1901 identities, not a 1000-document repeatable run with success/failure thresholds; it declares no gate_id and no document count",
  },
});

// The closed, documented fail-closed vocabulary. The contract test asserts that
// this exact set is emittable (each code fires on a mutated copy) and that no
// undocumented code can be raised.
export const FAIL_CLOSED_CODES = Object.freeze([
  "accepted_without_proof_package",
  "artifact_empty",
  "canonical_source_drift",
  "debt_record_incomplete",
  "evidence_drift",
  "gate_set_mismatch",
  "input_absent",
  "input_artifact_shape_invalid",
  "inventory_count_as_quantifier",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "owner_decision_required_collapsed",
  "path_not_repository_relative",
  "proof_level_below_minimum",
  "proof_package_gate_mismatch",
  "proof_package_path_absent",
  "promotion_claim_present",
  "quantifier_threshold_absent",
  "raw_text_leak",
  "required_evidence_class_absent",
  "unsupported_disposition",
]);

export const NON_CLAIMS = Object.freeze([
  "s01-register-is-not-overridden-or-smoothed (D536/D538): this adjudication re-derives the gate set, minimum levels and required evidence classes from the live README table and the live verifier constants; the register's per-gate recorded states are carried verbatim and the GATE-G015 disagreement is preserved, never averaged.",
  "bounded-input-is-not-a-proof-package: the S02/S03 artifacts, including the 102-identity / 166-row / 0-punkt candidate-backed admission expansion, satisfy no gate; every gate row carries proof_package=null and accepted=0.",
  "bounded-input-acceptance-is-not-gate-acceptance: an evidence_relation row names the closest S02/S03 artifacts and states explicitly why they are not the required evidence class; no relation row is evidence for its gate.",
  "no-proof-package-is-attributed: gates_promoted=0, proof_packages_attached=0 and no gate is accepted; acceptance is only reachable through a tracked artifact that declares the same gate_id in the required evidence class at or above the required proof level with a measured quantifier meeting the acceptance threshold.",
  "r035-stays-active (D430) and no requirement record is mutated by this artifact; it performs no requirement closure and no lifecycle move of any registry record.",
  "count-only-and-ascii-only: no XML bytes, no provider prose, no corpus text and no fabricated quantifier value are carried; only rule ids, trigger terms, evidence classes, proof levels, repository-relative paths, byte counts and sha256 pins are written.",
  "d537-in-force: scripts/verify-architecture-graph.py is read as a canonical constant source and is never executed as a gate; no architecture projection is written and the D7 missing-anchor quarantine is not lifted.",
  "inventory-counts-are-not-quantifiers (D539): the M202 inventory counters (registry_rows, legacy_human, punkt_admitted, candidates_*, admitted_candidate_backed, fz44_glava, fz44_statya, suites_cited) are rejected both as gate quantifiers and as dispositions.",
  "g015-requires-an-owner-decision: the recorded disagreement between the registry/derived-view superseded state and the frozen unsatisfied snapshot is a conflict, not a smoothing opportunity; it stays hold-requires-owner-decision.",
  "trigger-terms-carry-both-live-spellings: the README prose spelling is the artifact's trigger_terms and the verifier tuple spelling is recorded alongside; no claim is made that the two spellings are character-identical.",
  "quantifiers-are-acceptance-contracts-not-measurements: every gate row declares what would have to be measured and where, and no gate records a measured value for its quantifier.",
]);

// Provider prose markers that must never reach a count-only artifact.
const RAW_TEXT_MARKERS = Object.freeze([
  "consultantplus://",
  "<w:",
  "screenTip",
  "\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d",
]);

const README_SECTION_MARKER = "### R035 ontology and external-standard promotion gates";
const README_TABLE_HEADER =
  "| R035 trigger terms | Current safe bucket | Required promotion gate | Minimum validated proof level |";
const REGISTER_DECISION = "D536";
const DECISION_ID = "D558";
const REQUIREMENT_DISPOSITION_DECISION = "D430";
const GATE_ID_RE = /^GATE-[A-Z0-9-]+$/;

// ---------------------------------------------------------------------------
// errors and small guards
// ---------------------------------------------------------------------------

export class AdjudicationError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "AdjudicationError";
    this.code = code;
    this.detail = detail;
  }
}

export function fail(code, detail) {
  throw new AdjudicationError(code, detail);
}

export function assertNonEmpty(text) {
  if (typeof text !== "string" || text.length === 0) {
    fail("artifact_empty", "rendered evidence is empty");
  }
  return true;
}

export function assertAsciiOnly(text) {
  for (let index = 0; index < text.length; index += 1) {
    if (text.charCodeAt(index) > 0x7f) {
      fail("non_ascii_evidence", `non-ASCII code unit at index ${index}`);
    }
  }
  return true;
}

export function checkRenderedBytes(rendered, committed) {
  if (rendered !== committed) {
    fail("evidence_drift", "rendered bytes differ from the committed artifact");
  }
  return true;
}

export function renderEvidence(bundle) {
  return `${JSON.stringify(bundle)}\n`;
}

export function assertNoRawText(text) {
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) fail("raw_text_leak", `artifact carries ${marker}`);
  }
  return true;
}

export function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== "." && part !== "..");
}

export function assertRepoRelative(relative, label) {
  if (!isRepoRelative(relative)) {
    fail("path_not_repository_relative", `${label}: ${String(relative)}`);
  }
  return true;
}

export function sha256Hex(bytes) {
  // node:crypto is a stdlib module, not a dependency.
  return createHash("sha256").update(bytes).digest("hex");
}

export function sha256Pin(bytes) {
  return `sha256:${sha256Hex(bytes)}`;
}

export function normalizePin(value) {
  if (typeof value !== "string") return null;
  return value.startsWith("sha256:") ? value.slice(7) : value;
}

export function hasNumericThreshold(text) {
  return typeof text === "string" && /\d/.test(text);
}

export function isTrackedPath(relativePath, root = REPO_ROOT) {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: root,
      stdio: "ignore",
    });
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// canonical source loading
// ---------------------------------------------------------------------------

export function loadTextSource(relativePath, label, probes = {}) {
  assertRepoRelative(relativePath, label);
  const read = probes.readFileSync ?? readFileSync;
  const exists = probes.existsSync ?? existsSync;
  const root = probes.repoRoot ?? REPO_ROOT;
  const absolute = path.join(root, relativePath);
  if (!exists(absolute)) fail("input_absent", relativePath);
  let text;
  try {
    text = read(absolute, "utf8");
  } catch (error) {
    fail("input_absent", `${relativePath}: ${error.code ?? error.message}`);
  }
  const bytes = Buffer.from(text, "utf8");
  return { relative_path: relativePath, bytes: bytes.length, sha256: sha256Pin(bytes), text };
}

export function loadJsonArtifact(relativePath, label, probes = {}) {
  assertRepoRelative(relativePath, label);
  const read = probes.readFileSync ?? readFileSync;
  const exists = probes.existsSync ?? existsSync;
  const root = probes.repoRoot ?? REPO_ROOT;
  const absolute = path.join(root, relativePath);
  if (!exists(absolute)) fail("input_absent", relativePath);
  let raw;
  try {
    raw = read(absolute, "utf8");
  } catch (error) {
    fail("input_absent", `${relativePath}: ${error.code ?? error.message}`);
  }
  let text;
  if (typeof raw === "string") {
    text = raw;
  } else {
    text = Buffer.from(raw).toString("utf8");
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
  }
  const bytes = Buffer.from(text, "utf8");
  return { relative_path: relativePath, bytes: bytes.length, sha256: sha256Pin(bytes), parsed };
}

export function loadCanonicalSources(probes = {}) {
  return {
    readme: loadTextSource(README_PATH, "readme", probes),
    verifier: loadTextSource(VERIFIER_PATH, "verifier", probes),
    register: loadJsonArtifact(REGISTER_PATH, "gate register", probes),
    frozen_m202: loadJsonArtifact(FROZEN_M202_PATH, "frozen m202 proof gate", probes),
    corroboration: loadJsonArtifact(CORROBORATION_PATH, "t01 corroboration evidence", probes),
  };
}

// ---------------------------------------------------------------------------
// live canonical parsing
// ---------------------------------------------------------------------------

/// Slices a balanced literal block (respecting string literals) that starts at
/// the first `open` after `marker` and ends at its matching `close`.
export function sliceBalancedBlock(text, marker, open, close) {
  const at = typeof text === "string" ? text.indexOf(marker) : -1;
  if (at < 0) fail("input_artifact_shape_invalid", `missing block ${marker}`);
  const start = text.indexOf(open, at);
  if (start < 0) fail("input_artifact_shape_invalid", `missing ${open} after ${marker}`);
  let depth = 0;
  let inString = false;
  let quote = "";
  for (let index = start; index < text.length; index += 1) {
    const ch = text[index];
    if (inString) {
      if (ch === "\\") {
        index += 1;
        continue;
      }
      if (ch === quote) inString = false;
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      continue;
    }
    if (ch === open) depth += 1;
    else if (ch === close) {
      depth -= 1;
      if (depth === 0) return text.slice(start, index + 1);
    }
  }
  fail("input_artifact_shape_invalid", `unbalanced block ${marker}`);
}

function stripBackticks(value) {
  return String(value).split("`").join("");
}

export function splitReadmeTerms(cell) {
  const raw = stripBackticks(cell)
    .split(", ")
    .map((term) => term.trim())
    .filter((term) => term !== "");
  const terms = [];
  for (let index = 0; index < raw.length; index += 1) {
    if (
      /^\d{1,3}$/.test(raw[index]) &&
      index + 1 < raw.length &&
      /^000/.test(raw[index + 1]) &&
      raw[index + 1].includes("-document")
    ) {
      terms.push(`${raw[index]},${raw[index + 1]}`);
      index += 1;
    } else {
      terms.push(raw[index]);
    }
  }
  return terms;
}

export function splitGateIds(cell) {
  const ids = stripBackticks(cell)
    .split(" or ")
    .map((id) => id.trim())
    .filter((id) => id !== "");
  for (const id of ids) {
    if (!GATE_ID_RE.test(id)) {
      fail("input_artifact_shape_invalid", `unparsed gate id ${id}`);
    }
  }
  if (ids.length === 0) fail("input_artifact_shape_invalid", "empty required gate cell");
  return ids;
}

export function parseReadmeGateRows(text) {
  const sectionAt = typeof text === "string" ? text.indexOf(README_SECTION_MARKER) : -1;
  if (sectionAt < 0) fail("input_artifact_shape_invalid", `readme section absent`);
  const headerAt = text.indexOf(README_TABLE_HEADER, sectionAt);
  if (headerAt < 0) fail("input_artifact_shape_invalid", "readme R035 table header absent");
  const lines = text.slice(headerAt).split("\n");
  const rows = [];
  for (let index = 2; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.startsWith("|")) break;
    const cells = line.split("|").map((cell) => cell.trim());
    const body = cells.slice(1, cells.length - 1);
    if (body.length !== 4) {
      fail("input_artifact_shape_invalid", `readme row ${index} has ${body.length} cells`);
    }
    const level = stripBackticks(body[3]).trim();
    if (!/^[a-z][a-z-]*$/.test(level)) {
      fail("input_artifact_shape_invalid", `unparsed proof level ${level}`);
    }
    rows.push({
      trigger_terms: splitReadmeTerms(body[0]),
      safe_bucket: stripBackticks(body[1]).trim(),
      required_gate_ids: splitGateIds(body[2]),
      minimum_validated_proof_level: level,
    });
  }
  if (rows.length === 0) fail("input_artifact_shape_invalid", "readme R035 table is empty");
  return rows;
}

export function parseSetDict(text, marker) {
  const block = sliceBalancedBlock(text, marker, "{", "}");
  const out = {};
  const entry = /"([a-z][a-z-]*)":\s*\{([^}]*)\}/g;
  let match = entry.exec(block);
  while (match !== null) {
    const tokens = [];
    const token = /"([^"]+)"/g;
    let inner = token.exec(match[2]);
    while (inner !== null) {
      tokens.push(inner[1]);
      inner = token.exec(match[2]);
    }
    out[match[1]] = tokens;
    match = entry.exec(block);
  }
  if (Object.keys(out).length === 0) {
    fail("input_artifact_shape_invalid", `empty mapping ${marker}`);
  }
  return out;
}

export function parseIntDict(text, marker) {
  const block = sliceBalancedBlock(text, marker, "{", "}");
  const out = {};
  const entry = /"([a-z][a-z-]*)":\s*(\d+)/g;
  let match = entry.exec(block);
  while (match !== null) {
    out[match[1]] = Number(match[2]);
    match = entry.exec(block);
  }
  if (Object.keys(out).length === 0) {
    fail("input_artifact_shape_invalid", `empty mapping ${marker}`);
  }
  return out;
}

export function extractDicts(block) {
  const dicts = [];
  let index = 0;
  while (index < block.length) {
    if (block[index] !== "{") {
      index += 1;
      continue;
    }
    let depth = 0;
    let inString = false;
    let quote = "";
    let end = -1;
    for (let scan = index; scan < block.length; scan += 1) {
      const ch = block[scan];
      if (inString) {
        if (ch === "\\") {
          scan += 1;
          continue;
        }
        if (ch === quote) inString = false;
        continue;
      }
      if (ch === '"' || ch === "'") {
        inString = true;
        quote = ch;
        continue;
      }
      if (ch === "{") depth += 1;
      else if (ch === "}") {
        depth -= 1;
        if (depth === 0) {
          end = scan;
          break;
        }
      }
    }
    if (end < 0) fail("input_artifact_shape_invalid", "unbalanced dict literal");
    dicts.push(block.slice(index, end + 1));
    index = end + 1;
  }
  return dicts;
}

function firstMatch(text, pattern) {
  const match = pattern.exec(text);
  return match === null ? null : match[1];
}

function quotedTokens(value) {
  const tokens = [];
  const token = /"([^"]+)"/g;
  let match = token.exec(value);
  while (match !== null) {
    tokens.push(match[1]);
    match = token.exec(value);
  }
  return tokens;
}

export function parseOntologyRules(text) {
  const block = sliceBalancedBlock(text, "ONTOLOGY_PROMOTION_RULES", "(", ")");
  const dicts = extractDicts(block);
  const rules = [];
  for (const dict of dicts) {
    const label = firstMatch(dict, /"label":\s*"([^"]+)"/);
    const triggerSource = firstMatch(dict, /"trigger_terms":\s*\(([^)]*)\)/);
    const gateSource = firstMatch(dict, /"required_gate_ids":\s*\(([^)]*)\)/);
    const level = firstMatch(dict, /"minimum_proof_level":\s*"([^"]+)"/);
    if (label === null || triggerSource === null || gateSource === null || level === null) {
      fail("input_artifact_shape_invalid", "unparsed ontology promotion rule");
    }
    rules.push({
      label,
      trigger_terms: quotedTokens(triggerSource),
      required_gate_ids: quotedTokens(gateSource),
      minimum_proof_level: level,
    });
  }
  if (rules.length === 0) fail("input_artifact_shape_invalid", "no ontology promotion rules");
  return rules;
}

export function parseVerifierRules(text) {
  return {
    required_evidence_classes: parseSetDict(text, "PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES"),
    proof_level_order: parseIntDict(text, "PROOF_LEVEL_ORDER"),
    ontology_rules: parseOntologyRules(text),
  };
}

// ---------------------------------------------------------------------------
// canonical pin verification (three legs per source)
// ---------------------------------------------------------------------------

function pinRow(checkId, source, legs) {
  const values = legs
    .filter((leg) => leg.value !== null && leg.value !== undefined)
    .map((leg) => ({ leg: leg.leg, bytes: leg.bytes ?? null, sha256: normalizePin(leg.value) }));
  const live = normalizePin(source.sha256);
  const bytesLive = source.bytes;
  const agreed = values.every((row) => row.sha256 === live);
  const bytesAgreed = legs
    .filter((leg) => typeof leg.bytes === "number")
    .every((leg) => leg.bytes === bytesLive);
  return {
    check_id: checkId,
    scope: "declared bytes/sha256 of a live canonical source on every independent leg",
    expected: live,
    observed: values.map((row) => `${row.leg}=${row.sha256}`).join(","),
    verdict: agreed && bytesAgreed ? "pass" : "fail",
    live_bytes: bytesLive,
    live_sha256: live,
  };
}

function registerLeg(registerParsed, key, leg) {
  const block = registerParsed?.canonical_sources?.[key];
  if (block === undefined || block === null) return { leg, bytes: null, value: null };
  return { leg, bytes: block.bytes ?? null, value: normalizePin(block.sha256) };
}

function corroborationLeg(corroboration, relativePath, leg) {
  const bindings = corroboration?.bindings;
  if (!Array.isArray(bindings)) return { leg, bytes: null, value: null };
  const found = bindings.find((row) => row.relative_path === relativePath);
  if (found === undefined) return { leg, bytes: null, value: null };
  return {
    leg,
    bytes: typeof found.declared_bytes === "number" ? found.declared_bytes : null,
    value: normalizePin(found.declared_sha256),
  };
}

export function assertCanonicalPins(sources) {
  const checks = [
    pinRow("canonical_pin_readme", sources.readme, [
      { leg: "module", value: CANONICAL_PINS.readme.sha256, bytes: CANONICAL_PINS.readme.bytes },
      registerLeg(sources.register.parsed, "gate_table", "gate_register"),
      corroborationLeg(sources.corroboration.parsed, README_PATH, "t01_binding"),
    ]),
    pinRow("canonical_pin_verifier", sources.verifier, [
      { leg: "module", value: CANONICAL_PINS.verifier.sha256, bytes: CANONICAL_PINS.verifier.bytes },
      registerLeg(sources.register.parsed, "enforcement_rules", "gate_register"),
      corroborationLeg(sources.corroboration.parsed, VERIFIER_PATH, "t01_binding"),
    ]),
    pinRow("canonical_pin_register", sources.register, [
      { leg: "module", value: CANONICAL_PINS.register.sha256, bytes: CANONICAL_PINS.register.bytes },
      corroborationLeg(sources.corroboration.parsed, REGISTER_PATH, "t01_binding"),
    ]),
    pinRow("canonical_pin_frozen_m202", sources.frozen_m202, [
      {
        leg: "module",
        value: CANONICAL_PINS.frozen_m202.sha256,
        bytes: CANONICAL_PINS.frozen_m202.bytes,
      },
      registerLeg(sources.register.parsed, "frozen_snapshot", "gate_register"),
      corroborationLeg(sources.corroboration.parsed, FROZEN_M202_PATH, "t01_binding"),
    ]),
  ];
  const failed = checks.filter((check) => check.verdict !== "pass");
  if (failed.length > 0) {
    fail(
      "canonical_source_drift",
      failed.map((check) => `${check.check_id}:${check.observed}`).join(";"),
    );
  }
  return checks;
}

export function assertRegisterShape(register) {
  if (!Array.isArray(register?.gates) || register.gates.length === 0) {
    fail("input_artifact_shape_invalid", "register has no gates array");
  }
  for (const gate of register.gates) {
    const quantifier = gate.quantifier;
    if (
      typeof gate.gate_id !== "string" ||
      typeof gate.minimum_validated_proof_level !== "string" ||
      !Array.isArray(gate.required_evidence_classes) ||
      typeof gate.evidence_class !== "string" ||
      typeof gate.owner !== "string" ||
      typeof gate.owner_path !== "string" ||
      quantifier === null ||
      typeof quantifier !== "object" ||
      typeof quantifier.name !== "string" ||
      typeof quantifier.unit !== "string" ||
      typeof quantifier.acceptance !== "string" ||
      !Array.isArray(gate.recorded_states)
    ) {
      fail("input_artifact_shape_invalid", `register gate ${gate.gate_id} is malformed`);
    }
  }
  return true;
}

export function assertFrozenShape(frozen) {
  if (!Array.isArray(frozen?.promotion_gates) || frozen.promotion_gates.length === 0) {
    fail("input_artifact_shape_invalid", "frozen m202 has no promotion_gates");
  }
  for (const gate of frozen.promotion_gates) {
    if (typeof gate.gate_id !== "string") {
      fail("input_artifact_shape_invalid", "frozen gate row without gate_id");
    }
  }
  return true;
}

// ---------------------------------------------------------------------------
// live-derived gate rules
// ---------------------------------------------------------------------------

function levelsForGate(map, gateId, label) {
  const values = map.get(gateId) ?? [];
  if (values.length === 0) fail("gate_set_mismatch", `${gateId} absent from ${label}`);
  const levels = new Set(values);
  if (levels.size !== 1) {
    fail("canonical_source_drift", `${gateId} has disagreeing levels in ${label}`);
  }
  return [...levels][0];
}

export function deriveGateRules(readmeText, verifierText) {
  const readmeRows = parseReadmeGateRows(readmeText);
  const verifier = parseVerifierRules(verifierText);
  const orderLive = verifier.proof_level_order;
  const orderDeclared = PROOF_LEVEL_ORDER_DECLARED;
  const orderKeys = Object.keys(orderDeclared).sort();
  const liveKeys = Object.keys(orderLive).sort();
  if (orderKeys.join(",") !== liveKeys.join(",")) {
    fail("canonical_source_drift", "live PROOF_LEVEL_ORDER keys differ from the declared ladder");
  }
  for (const key of orderKeys) {
    if (orderLive[key] !== orderDeclared[key]) {
      fail("canonical_source_drift", `live PROOF_LEVEL_ORDER[${key}] differs`);
    }
  }

  const readmePrimary = new Map();
  const readmeAll = new Set();
  for (const row of readmeRows) {
    for (const id of row.required_gate_ids) readmeAll.add(id);
    const primary = row.required_gate_ids[0];
    readmePrimary.set(primary, [...(readmePrimary.get(primary) ?? []), row]);
  }
  const rulePrimary = new Map();
  const ruleAll = new Set();
  for (const rule of verifier.ontology_rules) {
    for (const id of rule.required_gate_ids) ruleAll.add(id);
    const primary = rule.required_gate_ids[0];
    rulePrimary.set(primary, [...(rulePrimary.get(primary) ?? []), rule]);
  }
  const liveIds = [...new Set([...readmeAll, ...ruleAll])].sort();
  const readmePrimaryIds = [...readmePrimary.keys()].sort();
  const rulePrimaryIds = [...rulePrimary.keys()].sort();
  if (readmePrimaryIds.join(",") !== liveIds.join(",")) {
    fail("gate_set_mismatch", "readme primary gates do not cover the live gate set");
  }
  if (rulePrimaryIds.join(",") !== liveIds.join(",")) {
    fail("gate_set_mismatch", "ontology rule primary gates do not cover the live gate set");
  }
  return { readmeRows, verifier, orderLive, readmePrimary, readmeAll, rulePrimary, ruleAll, liveIds };
}

export function coveragePredicate(readmeTerm, ruleTerm) {
  const norm = (value) =>
    String(value)
      .toLowerCase()
      .split("-")
      .join(" ")
      .split(",")
      .join(" ")
      .split(/\s+/)
      .filter((token) => token !== "")
      .join(" ");
  const left = norm(readmeTerm);
  const right = norm(ruleTerm);
  return left === right || left.startsWith(`${right} `);
}

export function termsAgree(readmeTerms, ruleTerms) {
  const forward = ruleTerms.every((ruleTerm) =>
    readmeTerms.some((readmeTerm) => coveragePredicate(readmeTerm, ruleTerm)),
  );
  const backward = readmeTerms.every((readmeTerm) =>
    ruleTerms.some((ruleTerm) => coveragePredicate(readmeTerm, ruleTerm)),
  );
  return forward && backward;
}

// ---------------------------------------------------------------------------
// proof-package evaluation (the acceptance gate)
// ---------------------------------------------------------------------------

export function evaluateProofPackage(gate, proofPackage, options = {}) {
  if (proofPackage === null || proofPackage === undefined) {
    fail("accepted_without_proof_package", `${gate.gate_id} claims acceptance without a package`);
  }
  const relativePath = proofPackage.relative_path;
  assertRepoRelative(relativePath, `${gate.gate_id} proof package`);
  const exists = options.existsSync ?? existsSync;
  const read = options.readFileSync ?? readFileSync;
  const isTracked = options.isTracked ?? isTrackedPath;
  const root = options.repoRoot ?? REPO_ROOT;
  const order = options.proof_level_order ?? PROOF_LEVEL_ORDER_DECLARED;
  const absolute = path.join(root, relativePath);
  if (!exists(absolute) || !isTracked(relativePath, root)) {
    fail("proof_package_path_absent", relativePath);
  }
  let raw;
  try {
    raw = read(absolute, "utf8");
  } catch (error) {
    fail("proof_package_path_absent", `${relativePath}: ${error.code ?? error.message}`);
  }
  const text = typeof raw === "string" ? raw : Buffer.from(raw).toString("utf8");
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
  }
  if (parsed.gate_id !== gate.gate_id) {
    fail("proof_package_gate_mismatch", `${relativePath} declares ${String(parsed.gate_id)}`);
  }
  if (!gate.required_evidence_classes.includes(parsed.evidence_class)) {
    fail("required_evidence_class_absent", `${relativePath} carries ${String(parsed.evidence_class)}`);
  }
  const packageLevel = order[parsed.proof_level];
  const gateLevel = order[gate.minimum_validated_proof_level];
  if (packageLevel === undefined || gateLevel === undefined) {
    fail("input_artifact_shape_invalid", `unknown proof level in ${relativePath}`);
  }
  if (packageLevel < gateLevel) {
    fail("proof_level_below_minimum", `${relativePath} at ${parsed.proof_level}`);
  }
  const measured = typeof parsed.measured_value === "number" ? parsed.measured_value : null;
  const threshold =
    typeof parsed.acceptance_threshold === "number" ? parsed.acceptance_threshold : null;
  const accepted = measured !== null && threshold !== null && measured >= threshold;
  return {
    accepted,
    relative_path: relativePath,
    gate_id: parsed.gate_id,
    evidence_class: parsed.evidence_class,
    proof_level: parsed.proof_level,
    quantifier_name: typeof parsed.quantifier_name === "string" ? parsed.quantifier_name : null,
    measured_value: measured,
    acceptance_threshold: threshold,
  };
}

export function validateDebtItem(debt) {
  const required = [
    "quantifier_name",
    "acceptance_text",
    "required_proof_level",
    "required_evidence_class",
    "missing_artifact_kind",
    "closest_evidence",
    "unblock_condition",
  ];
  if (debt === null || typeof debt !== "object") {
    fail("debt_record_incomplete", "debt entry is not an object");
  }
  for (const key of required) {
    const value = debt[key];
    if (key === "closest_evidence") {
      if (
        value === null ||
        typeof value !== "object" ||
        !Array.isArray(value.artifacts) ||
        typeof value.why_insufficient !== "string" ||
        value.why_insufficient === ""
      ) {
        fail("debt_record_incomplete", `closest_evidence is incomplete`);
      }
      continue;
    }
    if (typeof value !== "string" || value === "") {
      fail("debt_record_incomplete", `missing ${key}`);
    }
  }
  return true;
}

export function validateGateRow(row, options = {}) {
  if (!DISPOSITION_VOCABULARY.includes(row.disposition)) {
    fail("unsupported_disposition", `${row.gate_id}:${String(row.disposition)}`);
  }
  if (INVENTORY_QUANTIFIERS.includes(row.quantifier.name)) {
    fail("inventory_count_as_quantifier", row.quantifier.name);
  }
  if (!hasNumericThreshold(row.quantifier.acceptance)) {
    fail("quantifier_threshold_absent", row.gate_id);
  }
  if (!row.required_evidence_classes.includes(row.evidence_class)) {
    fail("required_evidence_class_absent", `${row.gate_id}:${row.evidence_class}`);
  }
  const relationOk =
    (row.evidence_relation.relation === "bounded-input" &&
      row.evidence_relation.artifacts.length > 0) ||
    (row.evidence_relation.relation === "none" && row.evidence_relation.artifacts.length === 0);
  if (!relationOk) {
    fail("input_artifact_shape_invalid", `${row.gate_id} evidence_relation is inconsistent`);
  }
  const conflict = row.recorded_conflict === true;
  if (conflict && row.disposition !== "hold-requires-owner-decision") {
    fail("owner_decision_required_collapsed", `${row.gate_id} conflict was collapsed`);
  }
  if (!conflict && row.disposition === "hold-requires-owner-decision") {
    fail("owner_decision_required_collapsed", `${row.gate_id} owner decision was invented`);
  }
  if (row.disposition === "accepted-at-bounded-scope") {
    evaluateProofPackage(row, row.proof_package, options);
  } else {
    if (!Array.isArray(row.debt) || row.debt.length === 0) {
      fail("debt_record_incomplete", `${row.gate_id} has no debt record`);
    }
  }
  for (const debt of row.debt ?? []) validateDebtItem(debt);
  return true;
}

// ---------------------------------------------------------------------------
// adjudication
// ---------------------------------------------------------------------------

export function loadEvidenceRelations(probes = {}) {
  const loaded = {};
  for (const [gateId, relation] of Object.entries(EVIDENCE_RELATIONS)) {
    const artifacts = [];
    for (const item of relation.artifacts) {
      const source = loadJsonArtifact(item.relative_path, `evidence relation ${gateId}`, probes);
      artifacts.push({
        relative_path: source.relative_path,
        bytes: source.bytes,
        sha256: source.sha256,
        touch_basis: item.touch_basis,
      });
    }
    loaded[gateId] = {
      relation: relation.relation,
      artifacts,
      why_not_required: relation.why_not_required,
    };
  }
  return loaded;
}

export function loadS02Counters(probes = {}) {
  const extraction = loadJsonArtifact(S02_EXTRACTION_EVIDENCE, "s02 extraction evidence", probes);
  const admission = loadJsonArtifact(
    S02_ADMISSION_REGENERATION,
    "s02 admission regeneration",
    probes,
  );
  const matched = extraction.parsed?.resolvability?.matched;
  const punkt = extraction.parsed?.punkt_admitted?.admitted;
  const candidateBacked = admission.parsed?.denominator?.candidate_backed_identities;
  const rowsTotal = admission.parsed?.inputs?.admission_source?.rows_total;
  const rowsCandidateBacked = admission.parsed?.inputs?.admission_source?.rows_m209_candidate_backed;
  const rowsPunkt = admission.parsed?.inputs?.admission_source?.rows_punkt;
  if (
    typeof matched !== "number" ||
    typeof punkt !== "number" ||
    typeof candidateBacked !== "number" ||
    typeof rowsTotal !== "number" ||
    typeof rowsCandidateBacked !== "number" ||
    typeof rowsPunkt !== "number"
  ) {
    fail("input_artifact_shape_invalid", "s02 counters are absent or non-numeric");
  }
  if (matched !== candidateBacked || punkt !== rowsPunkt || rowsPunkt !== 0) {
    fail("canonical_source_drift", "s02 candidate-backed counters disagree between artifacts");
  }
  return {
    candidate_backed_identities: candidateBacked,
    registry_rows: rowsTotal,
    rows_m209_candidate_backed: rowsCandidateBacked,
    punkt_admitted: punkt,
    extraction_evidence: S02_EXTRACTION_EVIDENCE,
    admission_regeneration: S02_ADMISSION_REGENERATION,
  };
}

function gateDebt(gate, relation) {
  return {
    quantifier_name: gate.quantifier.name,
    acceptance_text: gate.quantifier.acceptance,
    required_proof_level: gate.minimum_validated_proof_level,
    required_evidence_class: gate.evidence_class,
    required_evidence_classes: [...gate.required_evidence_classes],
    missing_artifact_kind: `${gate.gate_id.toLowerCase()}/${gate.evidence_class}`,
    closest_evidence: {
      relation: relation.relation,
      artifacts: relation.artifacts.map((artifact) => artifact.relative_path),
      why_insufficient: relation.why_not_required,
    },
    unblock_condition: `record a tracked ${gate.evidence_class} artifact that declares gate_id=${gate.gate_id} and whose quantifier ${gate.quantifier.name} measured over ${gate.quantifier.unit} satisfies: ${gate.quantifier.acceptance}; then re-run this adjudication`,
  };
}

export function deriveAdjudication(context) {
  const sources = context.sources;
  const rules = deriveGateRules(sources.readme.text, sources.verifier.text);
  const register = sources.register.parsed;
  const frozen = sources.frozen_m202.parsed;
  assertRegisterShape(register);
  assertFrozenShape(frozen);
  const evidenceRelations = context.evidenceRelations;
  const proofPackages = context.proofPackages ?? PROOF_PACKAGES;

  const registerById = new Map(register.gates.map((gate) => [gate.gate_id, gate]));
  const frozenById = new Map(frozen.promotion_gates.map((gate) => [gate.gate_id, gate]));
  const registerIds = [...registerById.keys()].sort();
  const frozenIds = [...frozenById.keys()].sort();
  if (registerIds.join(",") !== rules.liveIds.join(",")) {
    fail("gate_set_mismatch", "live gate set differs from the S01 register");
  }
  if (frozenIds.join(",") !== rules.liveIds.join(",")) {
    fail("gate_set_mismatch", "live gate set differs from the frozen M202 snapshot");
  }

  const crossChecks = [];
  const rows = [];
  for (const gateId of rules.liveIds) {
    const readmeLevels = (rules.readmePrimary.get(gateId) ?? []).map(
      (row) => row.minimum_validated_proof_level,
    );
    const ruleLevels = (rules.rulePrimary.get(gateId) ?? []).map(
      (rule) => rule.minimum_proof_level,
    );
    const readmeLevel = levelsForGate(
      new Map([[gateId, readmeLevels]]),
      gateId,
      "readme primary rows",
    );
    const ruleLevel = levelsForGate(new Map([[gateId, ruleLevels]]), gateId, "ontology rules");
    const registerGate = registerById.get(gateId);
    if (readmeLevel !== ruleLevel || readmeLevel !== registerGate.minimum_validated_proof_level) {
      fail("canonical_source_drift", `${gateId}: minimum level disagrees across live sources`);
    }
    const requiredClasses = rules.verifier.required_evidence_classes[readmeLevel];
    if (!Array.isArray(requiredClasses) || requiredClasses.length === 0) {
      fail("input_artifact_shape_invalid", `${gateId}: no evidence classes for ${readmeLevel}`);
    }
    const registerClasses = [...registerGate.required_evidence_classes].sort().join(",");
    const liveClasses = [...requiredClasses].sort().join(",");
    if (registerClasses !== liveClasses) {
      fail("canonical_source_drift", `${gateId}: required evidence classes differ`);
    }
    const registerPrimary = rules.readmePrimary.get(gateId)[0];
    const registerRuleTerms = (rules.rulePrimary.get(gateId) ?? [])
      .flatMap((rule) => rule.trigger_terms)
      .filter((term, index, all) => all.indexOf(term) === index);
    const states = registerGate.recorded_states.map((state) => ({
      facet: state.facet,
      normalized_state: state.normalized_state,
      source_path: state.source_path,
    }));
    const stateValues = new Set(states.map((state) => state.normalized_state));
    const recordedConflict = stateValues.size > 1;
    const registerConflict = registerGate.disposition === "conflicted-requires-decision";
    if (recordedConflict !== registerConflict) {
      fail("canonical_source_drift", `${gateId}: recorded-state conflict disagrees with register`);
    }

    const relation = evidenceRelations[gateId];
    if (relation === undefined) {
      fail("input_artifact_shape_invalid", `${gateId}: no evidence relation declared`);
    }
    const proofPackage = proofPackages[gateId] ?? null;
    const gateFacet = {
      gate_id: gateId,
      minimum_validated_proof_level: readmeLevel,
      required_evidence_classes: [...requiredClasses],
      evidence_class: registerGate.evidence_class,
      quantifier: {
        name: registerGate.quantifier.name,
        unit: registerGate.quantifier.unit,
        acceptance: registerGate.quantifier.acceptance,
      },
    };
    let accepted = false;
    if (proofPackage !== null) {
      accepted = evaluateProofPackage(gateFacet, proofPackage, context.proofPackageOptions ?? {})
        .accepted;
    }
    let disposition;
    if (recordedConflict) disposition = "hold-requires-owner-decision";
    else if (accepted) disposition = "accepted-at-bounded-scope";
    else disposition = "hold-with-precise-debt";

    const row = {
      gate_id: gateId,
      trigger_terms: [...registerPrimary.trigger_terms],
      ontology_rule_trigger_terms: registerRuleTerms,
      safe_bucket: registerPrimary.safe_bucket,
      minimum_validated_proof_level: readmeLevel,
      required_evidence_classes: [...requiredClasses],
      evidence_class: registerGate.evidence_class,
      owner: registerGate.owner,
      owner_path: registerGate.owner_path,
      quantifier: {
        name: registerGate.quantifier.name,
        unit: registerGate.quantifier.unit,
        acceptance: registerGate.quantifier.acceptance,
        acceptance_threshold_present: hasNumericThreshold(registerGate.quantifier.acceptance),
      },
      recorded_states: states,
      recorded_conflict: recordedConflict,
      frozen_gate_verdict: frozenById.get(gateId).gate_verdict,
      proof_package: proofPackage,
      evidence_relation: {
        relation: relation.relation,
        artifacts: relation.artifacts,
        why_not_required: relation.why_not_required,
      },
      disposition,
      disposition_basis:
        disposition === "accepted-at-bounded-scope"
          ? `${gateId}: accepted-at-bounded-scope -- a tracked proof package in the required evidence class at or above the required proof level declares this gate and its measured quantifier meets the acceptance threshold`
          : disposition === "hold-requires-owner-decision"
            ? `${gateId}: hold-requires-owner-decision -- the recorded states disagree (${states
                .map((state) => `${state.facet}=${state.normalized_state}`)
                .join(", ")}); the conflict is preserved and never collapsed`
            : `${gateId}: hold-with-precise-debt -- no proof package is declared (proof_package=null), so no rule-verified acceptance is possible; the closest evidence is ${relation.relation} and is not the required evidence class ${registerGate.evidence_class}`,
      debt: disposition === "accepted-at-bounded-scope" ? [] : [gateDebt(gateFacet, relation)],
    };
    validateGateRow(row, context.proofPackageOptions ?? {});
    rows.push(row);

    crossChecks.push({
      check_id: `min_level_agreement_${gateId}`,
      scope: "readme primary row vs ontology rule vs S01 register",
      expected: readmeLevel,
      observed: `${readmeLevel}|${ruleLevel}|${registerGate.minimum_validated_proof_level}`,
      verdict: "pass",
    });
    crossChecks.push({
      check_id: `required_evidence_classes_${gateId}`,
      scope: "live PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES vs S01 register",
      expected: liveClasses,
      observed: registerClasses,
      verdict: "pass",
    });
    crossChecks.push({
      check_id: `evidence_class_membership_${gateId}`,
      scope: "S01 register evidence_class membership in the live required set",
      expected: registerGate.evidence_class,
      observed: requiredClasses.join(","),
      verdict: requiredClasses.includes(registerGate.evidence_class) ? "pass" : "fail",
    });
    crossChecks.push({
      check_id: `recorded_conflict_${gateId}`,
      scope: "re-derived recorded-state conflict vs S01 register disposition",
      expected: registerGate.disposition,
      observed: `${recordedConflict ? "conflicted-requires-decision" : "not-conflicted"} (${states
        .map((state) => state.normalized_state)
        .join(",")})`,
      verdict: "pass",
    });
    crossChecks.push({
      check_id: `trigger_terms_${gateId}`,
      scope: "readme primary row terms vs ontology rule terms",
      expected: registerPrimary.trigger_terms.join("|"),
      observed: registerRuleTerms.join("|"),
      verdict: termsAgree(registerPrimary.trigger_terms, registerRuleTerms) ? "pass" : "fail",
    });
  }

  const counted = {
    gate_total: rows.length,
    registered_gate_total: registerIds.length,
    frozen_gate_total: frozenIds.length,
    accepted_total: rows.filter((row) => row.disposition === "accepted-at-bounded-scope").length,
    hold_with_precise_debt_total: rows.filter(
      (row) => row.disposition === "hold-with-precise-debt",
    ).length,
    hold_requires_owner_decision_total: rows.filter(
      (row) => row.disposition === "hold-requires-owner-decision",
    ).length,
    rejected_total: rows.filter((row) => row.disposition === "rejected-as-stated").length,
    debt_total: rows.reduce((sum, row) => sum + row.debt.length, 0),
    proof_packages_attached: rows.filter((row) => row.proof_package !== null).length,
    inventory_quantifier_total: rows.filter((row) =>
      INVENTORY_QUANTIFIERS.includes(row.quantifier.name),
    ).length,
    frozen_unsatisfied_total: rows.filter((row) => row.frozen_gate_verdict === "unsatisfied")
      .length,
  };

  crossChecks.push(
    {
      check_id: "gate_set_readme_all",
      scope: "every gate id named by any README R035 row",
      expected: rules.liveIds.join(","),
      observed: [...rules.readmeAll].sort().join(","),
      verdict: "pass",
    },
    {
      check_id: "gate_set_ontology_rules",
      scope: "every gate id named by any ontology promotion rule",
      expected: rules.liveIds.join(","),
      observed: [...rules.ruleAll].sort().join(","),
      verdict: "pass",
    },
    {
      check_id: "gate_set_s01_register",
      scope: "live gate set vs S01 register",
      expected: rules.liveIds.join(","),
      observed: registerIds.join(","),
      verdict: "pass",
    },
    {
      check_id: "gate_set_frozen_m202",
      scope: "live gate set vs frozen M202 snapshot",
      expected: rules.liveIds.join(","),
      observed: frozenIds.join(","),
      verdict: "pass",
    },
    {
      check_id: "gate_count_seven",
      scope: "gate cardinality",
      expected: 7,
      observed: rows.length,
      verdict: rows.length === 7 ? "pass" : "fail",
    },
    {
      check_id: "disposition_vocabulary",
      scope: "artifact vocabulary vs D558",
      expected: [...DISPOSITION_VOCABULARY].sort().join(","),
      observed: [...DISPOSITION_VOCABULARY].sort().join(","),
      verdict: "pass",
    },
    {
      check_id: "accepted_zero",
      scope: "no gate is accepted without a proof package",
      expected: 0,
      observed: counted.accepted_total,
      verdict: counted.accepted_total === 0 ? "pass" : "fail",
    },
    {
      check_id: "gates_promoted_zero",
      scope: "no promotion counter",
      expected: 0,
      observed: 0,
      verdict: "pass",
    },
    {
      check_id: "frozen_verdicts_unsatisfied",
      scope: "frozen M202 disposition of all seven gates",
      expected: 7,
      observed: counted.frozen_unsatisfied_total,
      verdict: counted.frozen_unsatisfied_total === 7 ? "pass" : "fail",
    },
    {
      check_id: "inventory_quantifier_total",
      scope: "no inventory counter stands as a quantifier",
      expected: 0,
      observed: counted.inventory_quantifier_total,
      verdict: counted.inventory_quantifier_total === 0 ? "pass" : "fail",
    },
  );

  return { rows, counted, cross_checks: crossChecks };
}

export function computePromotionChecks(rows, counted, s02Counters) {
  const checks = [
    {
      check_id: "no_promotion_counter",
      scope: "gates_promoted / proof_packages_attached / accepted_total",
      observed: `${counted.accepted_total}|${counted.proof_packages_attached}`,
      verdict: "pass",
    },
    {
      check_id: "no_authoritative_true",
      scope: "authoritative must be false",
      observed: 0,
      verdict: "pass",
    },
    {
      check_id: "no_promoted_verdict_literal",
      scope: "no row disposition in [validated, complete, satisfied, proven, checked]",
      observed: rows.filter((row) =>
        ["validated", "complete", "satisfied", "proven", "checked"].includes(row.disposition),
      ).length,
      verdict: "pass",
    },
    {
      check_id: "no_inventory_counter_as_quantifier",
      scope: "quantifier names over seven gates",
      observed: counted.inventory_quantifier_total,
      verdict: "pass",
    },
    {
      check_id: "s02_candidate_backed_is_not_a_proof_package",
      scope: "S02 candidate-backed expansion (102 identities / 166 rows / 0 punkt) satisfies no gate",
      observed: `${s02Counters.candidate_backed_identities}|${s02Counters.registry_rows}|${s02Counters.punkt_admitted}`,
      verdict: counted.accepted_total === 0 ? "pass" : "fail",
    },
    {
      check_id: "requirement_records_mutated",
      scope: "R035 disposition stays active (D430); no requirement record is written",
      observed: 0,
      verdict: "pass",
    },
  ];
  const failed = checks.filter((check) => check.verdict !== "pass");
  if (failed.length > 0) {
    fail("promotion_claim_present", failed.map((check) => check.check_id).join(","));
  }
  return checks;
}

// ---------------------------------------------------------------------------
// artifact assembly
// ---------------------------------------------------------------------------

export function validateBundle(bundle) {
  if (bundle.authoritative !== false) fail("promotion_claim_present", "authoritative is not false");
  if (bundle.lifecycle !== "[bounded]") fail("promotion_claim_present", "lifecycle is not bounded");
  if (bundle.gates_promoted !== 0) fail("promotion_claim_present", `gates_promoted`);
  if (bundle.proof_packages_attached !== 0) fail("promotion_claim_present", "proof package attached");
  if (bundle.requirement_records_mutated !== 0) {
    fail("promotion_claim_present", "requirement record mutated");
  }
  if (bundle.gate_count !== bundle.gates.length) {
    fail("gate_set_mismatch", "gate_count does not match the row array");
  }
  const ids = bundle.gates.map((row) => row.gate_id);
  if (new Set(ids).size !== ids.length) fail("gate_set_mismatch", "duplicate gate ids");
  const vocab = [...bundle.disposition_vocabulary].sort().join(",");
  if (vocab !== [...DISPOSITION_VOCABULARY].sort().join(",")) {
    fail("unsupported_disposition", "artifact vocabulary differs from D558");
  }
  for (const row of bundle.gates) validateGateRow(row, {});
  return true;
}

export function adjudicationBundle(context) {
  const sources = context.sources ?? loadCanonicalSources();
  const evidenceRelations = context.evidenceRelations ?? loadEvidenceRelations();
  const s02Counters = context.s02Counters ?? loadS02Counters();
  const canonicalChecks = assertCanonicalPins(sources);
  const derived = deriveAdjudication({ ...context, sources, evidenceRelations });
  const promotionChecks = computePromotionChecks(derived.rows, derived.counted, s02Counters);
  const crossChecks = [...derived.cross_checks, ...canonicalChecks].map((check) => ({
    check_id: check.check_id,
    scope: check.scope,
    expected: check.expected,
    observed: check.observed,
    verdict: check.verdict,
  }));
  const failed = crossChecks.filter((check) => check.verdict !== "pass");
  if (failed.length > 0) {
    fail("canonical_source_drift", failed.map((check) => check.check_id).join(","));
  }
  const counted = {
    ...derived.counted,
    canonical_sources_total: 4,
    cross_checks_total: crossChecks.length,
    cross_checks_failed: 0,
    promotion_checks_total: promotionChecks.length,
    promotion_checks_failed: 0,
    s02_candidate_backed_identities: s02Counters.candidate_backed_identities,
    s02_registry_rows: s02Counters.registry_rows,
    s02_punkt_admitted: s02Counters.punkt_admitted,
  };
  const bundle = {
    schema: SCHEMA,
    schema_version: 1,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: "[bounded]",
    authoritative: false,
    count_only: true,
    ascii_only: true,
    requirement_id: "R035",
    requirement_disposition: "active",
    requirement_disposition_decision: REQUIREMENT_DISPOSITION_DECISION,
    register_decision: REGISTER_DECISION,
    decision: DECISION_ID,
    min_level_rule: MIN_LEVEL_RULE,
    term_split_rule: TERM_SPLIT_RULE,
    adjudication_rule: ADJUDICATION_RULE,
    gate_count: derived.rows.length,
    accepted_total: counted.accepted_total,
    hold_with_precise_debt_total: counted.hold_with_precise_debt_total,
    hold_requires_owner_decision_total: counted.hold_requires_owner_decision_total,
    rejected_total: counted.rejected_total,
    debt_total: counted.debt_total,
    gates_promoted: 0,
    proof_packages_attached: counted.proof_packages_attached,
    requirement_records_mutated: 0,
    inventory_quantifier_total: counted.inventory_quantifier_total,
    canonical_sources: {
      readme_gate_table: {
        relative_path: sources.readme.relative_path,
        section: "R035 ontology and external-standard promotion gates",
        bytes: sources.readme.bytes,
        sha256: sources.readme.sha256,
        authority:
          "canonical: trigger terms, safe bucket, required gate ids and minimum validated proof level per R035 row",
      },
      enforcement_rules: {
        relative_path: sources.verifier.relative_path,
        sections: [
          "PROOF_LEVEL_REQUIRED_EVIDENCE_CLASSES",
          "PROOF_LEVEL_ORDER",
          "ONTOLOGY_PROMOTION_RULES",
        ],
        bytes: sources.verifier.bytes,
        sha256: sources.verifier.sha256,
        authority:
          "canonical: rule trigger terms, required gate ids, minimum proof level and the evidence classes admitted at each proof level; read-only, never executed as a gate (D537)",
      },
      gate_register: {
        relative_path: sources.register.relative_path,
        bytes: sources.register.bytes,
        sha256: sources.register.sha256,
        role: "owner, owner_path, named quantifier, evidence class and recorded states per gate",
      },
      frozen_m202: {
        relative_path: sources.frozen_m202.relative_path,
        selector: "promotion_gates[].gate_id",
        bytes: sources.frozen_m202.bytes,
        sha256: sources.frozen_m202.sha256,
        role: "frozen gate-id set and per-gate verdict",
      },
    },
    s02_candidate_backed_is_not_a_proof_package: {
      candidate_backed_identities: s02Counters.candidate_backed_identities,
      registry_rows: s02Counters.registry_rows,
      punkt_admitted: s02Counters.punkt_admitted,
      accepted_gates: 0,
      source_artifacts: [s02Counters.extraction_evidence, s02Counters.admission_regeneration],
      note: "the candidate-backed admission expansion is bounded input: it is not a proof package for any gate and no inventory counter stands as a quantifier",
    },
    gates: derived.rows,
    counted,
    cross_checks: crossChecks,
    promotion_checks: promotionChecks,
    disposition_vocabulary: [...DISPOSITION_VOCABULARY],
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };
  validateBundle(bundle);
  return bundle;
}

export function heartbeat(counted, mode) {
  const summary = [
    `gates=${counted.gate_total}`,
    `hold=${counted.hold_with_precise_debt_total}`,
    `owner-decision=${counted.hold_requires_owner_decision_total}`,
    `accepted=${counted.accepted_total}`,
    `gates_promoted=0`,
    `drift=0`,
    `cross=${counted.cross_checks_total}`,
    `promotion=${counted.promotion_checks_total}`,
    `failed=${counted.cross_checks_failed + counted.promotion_checks_failed}`,
    `mode=${mode}`,
  ];
  return summary.join(" ");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

export function resolveOutTarget(outPath, probes = {}) {
  const realpath = probes.realpathSync ?? realpathSync;
  const lstat = probes.lstatSync ?? lstatSync;
  const exists = probes.existsSync ?? existsSync;
  if (typeof outPath !== "string" || outPath === "") {
    fail("out_not_evidence_path", String(outPath));
  }
  if (path.isAbsolute(outPath)) fail("out_absolute", outPath);
  const resolved = path.resolve(REPO_ROOT, outPath);
  const parent = path.dirname(resolved);
  if (!exists(parent)) fail("out_of_repo_out", `missing parent directory for ${outPath}`);
  const realRoot = realpath(REPO_ROOT);
  const realParent = realpath(parent);
  const parentRelative = path.relative(realRoot, realParent);
  if (parentRelative.startsWith("..") || path.isAbsolute(parentRelative)) {
    fail("out_of_repo_out", outPath);
  }
  const repoRelative = path
    .relative(realRoot, path.join(realParent, path.basename(resolved)))
    .split(path.sep)
    .join("/");
  if (!repoRelative.startsWith(OUT_PREFIX) || !repoRelative.endsWith(".json")) {
    fail("out_not_evidence_path", repoRelative);
  }
  if (exists(resolved) && lstat(resolved).isSymbolicLink()) {
    fail("out_symlink_target", repoRelative);
  }
  return { absolute: resolved, repoRelative };
}

function atomicWrite(absolutePath, text) {
  const sibling = `${absolutePath}.tmp-m209-s04-t03`;
  writeFileSync(sibling, text);
  renameSync(sibling, absolutePath);
}

function parseArgs(argv) {
  const options = { mode: "gates", out: null, check: false, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") {
      index += 1;
      if (index >= argv.length) return { error: "--mode requires a value" };
      options.mode = argv[index];
      if (options.mode !== "gates") return { error: `unknown mode ${options.mode}` };
    } else if (arg === "--out") {
      index += 1;
      if (index >= argv.length) return { error: "--out requires a path" };
      options.out = argv[index];
    } else if (arg === "--check") {
      options.check = true;
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      return { error: `unknown argument ${arg}` };
    }
  }
  return options;
}

const USAGE =
  "usage: m209_s04_gate_adjudication.mjs [--mode gates] [--out PATH] [--check]\n";

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error !== undefined) {
    process.stderr.write(`${USAGE}m209_s04_gate_adjudication: ${options.error}\n`);
    process.exit(2);
  }
  if (options.help) {
    process.stdout.write(USAGE);
    return;
  }
  const target = resolveOutTarget(options.out === null ? ARTIFACT_PATH : options.out);
  const bundle = adjudicationBundle({});
  const rendered = renderEvidence(bundle);
  assertNonEmpty(rendered);
  assertAsciiOnly(rendered);
  assertNoRawText(rendered);
  if (options.check) {
    if (!existsSync(target.absolute)) {
      fail("evidence_drift", `missing committed artifact ${target.repoRelative}`);
    }
    checkRenderedBytes(rendered, readFileSync(target.absolute, "utf8"));
  } else {
    atomicWrite(target.absolute, rendered);
  }
  process.stdout.write(`M209_S04_GATES_OK ${heartbeat(bundle.counted, options.mode)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof AdjudicationError) {
      process.stderr.write(`M209_S04_GATES_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
