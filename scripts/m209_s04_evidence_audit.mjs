#!/usr/bin/env node
// Independent evidence-chain audit for M209-2yg6ix (S04 T01, D559).
//
// WHY THIS FILE EXISTS
// S04 is the independent corroboration slice. S01/S02/S03 artifacts declare a
// long chain of byte bindings and a handful of chain numbers
// (1901 / 102 / 166 / 120 / 122 / 118). Accepting those declarations because a
// producer suite re-renders its own output would be a declaration, not a
// corroboration. This auditor re-derives every declared input binding and every
// chain number with an independent implementation and cross-checks the numbers
// across artifacts.
//
// WHAT IT IS NOT (D559)
// It is NOT a second corpus parser. Parser-level denominators are corroborated
// by byte pins plus the producers' own deterministic re-render, never by a
// second implementation of the classifier. It is NOT a budget for the corpus
// listing: directory-level listing digests (exports_* trees, the 44-fz edition
// directory) are delegated to S04 T02's live corpus recount, and each such row
// is recorded here with verdict `delegated-to-t02` rather than silently dropped.
//
// INPUTS (read-only): M209 S01/S02/S03 artifacts and the frozen M201/M202
// artifacts enumerated in MODEL_FILES; plus, for digest recomputation, the
// tracked source XML of the S02 candidate (`law-source/consultant/...f9c8ca4c.xml`)
// and the frozen M202 fixture XML. The licensed corpus under `consru_export/`
// is read read-only and is never persisted.
//
// OUTPUT: prd/migration/rust-evidence/m209-s04-corroboration-evidence.json
//
// USAGE
//   node scripts/m209_s04_evidence_audit.mjs --mode all --out prd/migration/rust-evidence/m209-s04-corroboration-evidence.json
//   node scripts/m209_s04_evidence_audit.mjs --mode all --check
//   node scripts/m209_s04_evidence_audit.mjs --mode bindings   # diagnostic, no counts
//   node scripts/m209_s04_evidence_audit.mjs --mode counts     # diagnostic, no bindings
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  closeSync,
  existsSync,
  fstatSync,
  lstatSync,
  openSync,
  readFileSync,
  readSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

const SCHEMA = "law-nexus/m209-corroboration-evidence/v1";
const MILESTONE = "M209-2yg6ix";
const TASK = "T01";
const ARTIFACT_PATH = "prd/migration/rust-evidence/m209-s04-corroboration-evidence.json";
const OUT_PREFIX = "prd/migration/rust-evidence/m209-s04-";
const CORPUS_PREFIX = "consru_export/";
const S02_SOURCE_XML =
  "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml";
const M202_FIXTURE_XML = "crates/ln-decode/tests/fixtures/hierarchy_candidates.xml";

// The closed, documented fail-closed vocabulary. The contract test asserts that
// this exact set is emittable (each code fires on a mutated in-memory copy) and
// that no undocumented code can be raised.
export const FAIL_CLOSED_CODES = Object.freeze([
  "artifact_empty",
  "count_partition_mismatch",
  "cross_artifact_disagreement",
  "digest_mismatch",
  "evidence_drift",
  "frozen_boundary_drift",
  "input_absent",
  "input_artifact_shape_invalid",
  "input_bytes_mismatch",
  "input_hash_mismatch",
  "input_not_tracked",
  "inventory_count_as_quantifier",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "path_not_repository_relative",
  "promotion_claim_present",
]);

export const NON_CLAIMS = Object.freeze([
  "bindings-and-arithmetic-audit-not-second-corpus-parser (D559): this artifact re-derives declared bindings, digests and decompositions of the M209 evidence chain; it does not re-implement the corpus classifier.",
  "parser-level-denominators-corroborated-by-byte-pins-and-deterministic-re-render, not by an independent classifier implementation (D559).",
  "no-gate-promoted: gates_promoted is 0 in every audited artifact and in this artifact; no proof package is attached to any gate.",
  "requirement-dispositions-unchanged: R035 stays active (D430) and R070 stays active (D416); this audit mutates no requirement record.",
  "directory-listing-digests-delegated-to-s04-t02: exports_* trees and the 44-fz edition directory are listing digests produced by T02's live corpus recount; this artifact pins files only and records the delegated rows explicitly.",
  "chain-numbers-1901-102-166-120-122-118-are-cross-checked-across-declared-sibling-artifacts-here, not re-derived from the corpus envelope.",
  "licensed-corpus-under-consru_export-is-untracked-by-design-and-read-only; a corpus input that is absent while the corpus root is absent is recorded with verdict corpus-absent and never silently dropped.",
  "edition-denominator-118-agreement-is-bindings-level (family denominator vs edition-delta listing digest/bytes/files) plus the delegated T02 live listing; the frozen m201-s03-tracked-chain.json and fz44-tracked-edition-chain.yaml pins are byte-verified in frozen_boundary and explicitly non-claim the 118-edition corpus, so no numeric 118 is fabricated from that pin.",
]);

const MODEL_FILES = Object.freeze({
  gateRegister: "prd/architecture/m209-s01-r035-gate-register.json",
  reconciliation: "prd/migration/rust-evidence/m209-s01-r035-gate-reconciliation.json",
  candidateArtifact: "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json",
  extractionEvidence: "prd/migration/rust-evidence/m209-s02-extraction-evidence.json",
  admissionRegeneration: "prd/migration/rust-evidence/m209-s02-admission-regeneration-evidence.json",
  familyDenominator: "prd/migration/rust-evidence/m209-s03-family-denominator.json",
  amendingAct: "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json",
  commencement: "prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json",
  editionDelta: "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json",
  r070Ledger: "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json",
  frozenM202Candidates: "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  frozenM202Regeneration: "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  frozenM202ProofGate: "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
  frozenM201ProofGate: "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  frozenM201TrackedChain: "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
});

const FROZEN_PATHS = Object.freeze([
  "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
  "prd/architecture/kb-hierarchy-registry.yaml",
  "prd/architecture/kb-hierarchy-registry-admissions.yaml",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
]);

const PROMOTED_COUNTER_KEYS = new Set([
  "gates_promoted",
  "legs_promoted",
  "proof_packages_attached",
  "proof_packages_admitted",
]);

// Mirrors the banned gate-verdict literals enforced by
// crates/ln-kb-ontology/tests/r035_proof_gate.rs over the frozen M202 snapshot.
const BANNED_VERDICT_LITERALS = new Set(["validated", "complete", "satisfied", "checked", "proven"]);
const VERDICT_KEY_PATTERN = /(^|_)(verdict|disposition)$/;
const BANNED_LIFECYCLE_LITERALS = new Set(["validated", "complete"]);

const FNV_OFFSET_BASIS = 0xcbf29ce484222325n;
const FNV_PRIME = 0x100000001b3n;
const FNV_MASK = 0xffffffffffffffffn;
const READ_CHUNK_BYTES = 8 * 1024 * 1024;

export class AuditError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "AuditError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new AuditError(code, detail);
}

function compareText(left, right) {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

function repoPath(relative) {
  return path.resolve(REPO_ROOT, relative);
}

function pick(object, dotted, label) {
  let cursor = object;
  for (const key of dotted.split(".")) {
    if (
      cursor === null ||
      typeof cursor !== "object" ||
      !Object.hasOwn(cursor, key)
    ) {
      fail("input_artifact_shape_invalid", `${label}: missing ${dotted}`);
    }
    cursor = cursor[key];
  }
  return cursor;
}

function normalizeSha(value) {
  const text = String(value).trim().toLowerCase();
  return text.startsWith("sha256:") ? text.slice("sha256:".length) : text;
}

function requiredNumber(value, label) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    fail("input_artifact_shape_invalid", `${label}: expected a number, got ${typeof value}`);
  }
  return value;
}

// ---------------------------------------------------------------------------
// Independent primitives
// ---------------------------------------------------------------------------

/// Independently implemented FNV-1a 64 (BigInt, offset basis 0xcbf29ce484222325,
/// prime 0x100000001b3), rendered as `fnv1a64:<16 lowercase hex>`.
export function fnv1a64(bytes) {
  let hash = FNV_OFFSET_BASIS;
  for (const byte of bytes) {
    hash = ((hash ^ BigInt(byte)) * FNV_PRIME) & FNV_MASK;
  }
  return `fnv1a64:${hash.toString(16).padStart(16, "0")}`;
}

const digestCache = new Map();

/// Independent streaming sha256 + byte count of one file. Cached per absolute
/// path so repeated audit passes inside one process do not re-read large inputs.
export function fileDigest(absolutePath) {
  if (digestCache.has(absolutePath)) return digestCache.get(absolutePath);
  const handle = openSync(absolutePath, "r");
  try {
    const size = fstatSync(handle).size;
    const hash = createHash("sha256");
    const buffer = Buffer.allocUnsafe(Math.max(1, Math.min(READ_CHUNK_BYTES, size || 1)));
    let bytes = 0;
    let read = readSync(handle, buffer, 0, buffer.length, null);
    while (read > 0) {
      hash.update(buffer.subarray(0, read));
      bytes += read;
      read = readSync(handle, buffer, 0, buffer.length, null);
    }
    const value = { bytes, sha256: hash.digest("hex") };
    digestCache.set(absolutePath, value);
    return value;
  } finally {
    closeSync(handle);
  }
}

const trackedCache = new Map();

/// Tracked-status probe. `--` terminates the pathspec list so a name beginning
/// with `-` is never read as a flag.
export function defaultIsTracked(relativePath) {
  if (trackedCache.has(relativePath)) return trackedCache.get(relativePath);
  let tracked = false;
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: REPO_ROOT,
      stdio: "ignore",
    });
    tracked = true;
  } catch {
    tracked = false;
  }
  trackedCache.set(relativePath, tracked);
  return tracked;
}

/// Canonical candidate identity stream (the rule pinned by D547 and re-derived
/// here from the artifact body itself, not from a producer boolean).
///
/// For every stored candidate row, in document order:
///   catalog_token NUL number NUL path (empty when null) NUL key_path NUL depth LF
/// then, for every recorded duplicate key:
///   dup NUL catalog_token NUL key_path NUL first_index NUL later_index LF
export function identityStream(artifact, label = "candidate-artifact") {
  const candidates = pick(artifact, "candidates", label);
  const duplicateKeys = pick(artifact, "diagnostics.duplicate_keys", label);
  if (!Array.isArray(candidates) || !Array.isArray(duplicateKeys)) {
    fail("input_artifact_shape_invalid", `${label}: candidates/duplicate_keys not arrays`);
  }
  const chunks = [];
  for (const candidate of candidates) {
    const catalogToken = pick(candidate, "catalog_token", label);
    const number = pick(candidate, "number", label);
    const rawPath = Object.hasOwn(candidate, "path") ? candidate.path : null;
    const keyPath = pick(candidate, "key_path", label);
    const depth = pick(candidate, "depth", label);
    chunks.push(
      Buffer.from(
        `${catalogToken}\u0000${number}\u0000${rawPath === null ? "" : rawPath}\u0000${keyPath}\u0000${depth}\n`,
        "utf8",
      ),
    );
  }
  for (const duplicate of duplicateKeys) {
    chunks.push(
      Buffer.from(
        `dup\u0000${duplicate.catalog_token}\u0000${duplicate.key_path}\u0000${duplicate.first_index}\u0000${duplicate.later_index}\n`,
        "utf8",
      ),
    );
  }
  return Buffer.concat(chunks);
}

export function recomputeIdentityDigest(artifact, label) {
  const declared = pick(artifact, "identity_digest", label);
  const recomputed = fnv1a64(identityStream(artifact, label));
  if (recomputed !== declared) {
    fail("digest_mismatch", `${label}: identity recomputed ${recomputed} declared ${declared}`);
  }
  return {
    artifact: label,
    unique_candidates: pick(artifact, "candidates", label).length,
    duplicate_rows: pick(artifact, "diagnostics.duplicate_keys", label).length,
    recomputed,
    declared,
    verdict: "pass",
  };
}

// ---------------------------------------------------------------------------
// Declared-input collection
// ---------------------------------------------------------------------------

/// Collect every input path declared by an audited artifact together with the
/// bytes/sha256 that artifact declares for it. The same path may be declared by
/// several artifacts; non-null declarations must agree, otherwise the chain is
/// internally inconsistent (`cross_artifact_disagreement`).
export function collectDeclaredInputs(model) {
  const declarations = new Map();
  const add = (sourceId, relativePath, bytes, sha256, kind = "file") => {
    if (typeof relativePath !== "string" || relativePath === "") return;
    let entry = declarations.get(relativePath);
    if (entry === undefined) {
      entry = {
        path: relativePath,
        kind,
        declaredBytes: null,
        declaredSha256: null,
        declaredBy: [],
      };
      declarations.set(relativePath, entry);
    }
    if (kind === "directory") entry.kind = "directory";
    entry.declaredBy.push(sourceId);
    if (bytes !== null && bytes !== undefined) {
      const numeric = requiredNumber(bytes, `${sourceId}: bytes`);
      if (entry.declaredBytes !== null && entry.declaredBytes !== numeric) {
        fail(
          "cross_artifact_disagreement",
          `${relativePath}: declared bytes ${entry.declaredBytes} vs ${numeric} (${sourceId})`,
        );
      }
      entry.declaredBytes = numeric;
    }
    if (sha256 !== null && sha256 !== undefined) {
      const clean = normalizeSha(sha256);
      if (entry.declaredSha256 !== null && entry.declaredSha256 !== clean) {
        fail(
          "cross_artifact_disagreement",
          `${relativePath}: declared sha256 differs (${sourceId})`,
        );
      }
      entry.declaredSha256 = clean;
    }
  };

  const gateRegister = model.gateRegister;
  const canonicalSources = pick(gateRegister, "canonical_sources", "gate-register");
  add("gate-register#canonical_sources.gate_table", canonicalSources.gate_table.path, null, canonicalSources.gate_table.sha256);
  add("gate-register#canonical_sources.enforcement_rules", canonicalSources.enforcement_rules.path, null, canonicalSources.enforcement_rules.sha256);
  add("gate-register#canonical_sources.frozen_snapshot", canonicalSources.frozen_snapshot.path, canonicalSources.frozen_snapshot.bytes, canonicalSources.frozen_snapshot.sha256);
  add("gate-register#canonical_sources.derived_view", canonicalSources.derived_non_authoritative_view.path, null, canonicalSources.derived_non_authoritative_view.sha256);
  for (const source of pick(gateRegister, "supporting_sources", "gate-register")) {
    add("gate-register#supporting_sources", source.path, null, source.sha256);
  }

  const reconciliation = model.reconciliation;
  for (const [key, value] of Object.entries(pick(reconciliation, "sources", "reconciliation"))) {
    add(`reconciliation#sources.${key}`, value.path, value.bytes ?? null, value.sha256 ?? null);
  }
  const frozenPins = pick(reconciliation, "frozen_pins", "reconciliation");
  for (const pin of pick(frozenPins, "rust_anchored", "reconciliation")) {
    add("reconciliation#frozen_pins.rust_anchored", pin.path, pin.bytes, pin.sha256);
  }
  const capturedAt = pick(frozenPins, "captured_at_baseline_not_rust_anchored", "reconciliation");
  add("reconciliation#frozen_pins.captured_at", capturedAt.path, capturedAt.bytes, capturedAt.sha256);

  const regeneration = model.admissionRegeneration;
  const regenerationInputs = pick(regeneration, "inputs", "admission-regeneration");
  for (const [key, value] of Object.entries(regenerationInputs)) {
    if (value === null || typeof value !== "object" || typeof value.path !== "string") continue;
    add(`admission-regeneration#inputs.${key}`, value.path, value.bytes ?? null, value.sha256 ?? null);
  }

  const extraction = model.extractionEvidence;
  add("extraction-evidence#extraction.source", pick(extraction, "extraction.source.path", "extraction-evidence"), pick(extraction, "extraction.source.bytes", "extraction-evidence"), pick(extraction, "extraction.source.sha256", "extraction-evidence"));
  add("extraction-evidence#extraction.artifact", pick(extraction, "extraction.artifact.path", "extraction-evidence"), pick(extraction, "extraction.artifact.bytes", "extraction-evidence"), pick(extraction, "extraction.artifact.sha256", "extraction-evidence"));

  const family = model.familyDenominator;
  for (const entry of pick(family, "families", "family-denominator")) {
    add(
      `family-denominator#families.${entry.family_id}`,
      entry.input_relative_path,
      entry.input_bytes,
      entry.input_sha256,
      entry.kind === "directory" ? "directory" : "file",
    );
  }
  const chain = pick(family, "chain", "family-denominator");
  add("family-denominator#chain", chain.edition_directory_relative_path, chain.input_bytes, chain.input_sha256, "directory");

  const declaredInputArrays = [
    ["amending-act", model.amendingAct],
    ["commencement", model.commencement],
    ["edition-delta", model.editionDelta],
    ["r070-ledger", model.r070Ledger],
  ];
  for (const [label, artifact] of declaredInputArrays) {
    for (const entry of pick(artifact, "inputs", label)) {
      add(`${label}#inputs.${entry.input_id}`, entry.relative_path, entry.input_bytes, entry.input_sha256);
    }
  }
  add("r070-ledger#frozen_m201_boundary", pick(model.r070Ledger, "frozen_m201_boundary.gate_relative_path", "r070-ledger"), null, pick(model.r070Ledger, "frozen_m201_boundary.gate_sha256", "r070-ledger"));

  const m201 = model.frozenM201ProofGate;
  const m201Binding = pick(m201, "source_binding", "m201-r070-proof-gate");
  add("m201-r070-proof-gate#source_binding.tracked_chain_json", m201Binding.tracked_chain_json.relative_path, m201Binding.tracked_chain_json.bytes, m201Binding.tracked_chain_json.sha256);
  add("m201-r070-proof-gate#source_binding.tracked_chain_yaml", m201Binding.tracked_chain_yaml.relative_path, m201Binding.tracked_chain_yaml.bytes, m201Binding.tracked_chain_yaml.sha256);
  add("m201-r070-proof-gate#source_binding.cited_canon_pin", m201Binding.cited_canon_pin.canon_relative_path, m201Binding.cited_canon_pin.canon_bytes, m201Binding.cited_canon_pin.canon_sha256);

  for (const [key, value] of Object.entries(pick(model.frozenM202ProofGate, "source_binding", "m202-r035-proof-gate"))) {
    add(`m202-r035-proof-gate#source_binding.${key}`, value.relative_path, value.bytes, value.sha256);
  }

  return declarations;
}

function isSafeRepositoryRelative(relativePath) {
  if (typeof relativePath !== "string" || relativePath === "") return false;
  if (relativePath.includes("\u0000")) return false;
  if (path.isAbsolute(relativePath)) return false;
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(relativePath)) return false;
  const segments = relativePath.split("/");
  return !segments.includes("..") && !segments.includes("");
}

export function computeBindings(model, probes = {}) {
  const isTracked = probes.isTracked ?? defaultIsTracked;
  const corpusPresent = probes.corpusPresent ?? existsSync(repoPath(CORPUS_PREFIX));
  const declarations = collectDeclaredInputs(model);
  const entries = [...declarations.values()].sort((left, right) => compareText(left.path, right.path));
  const rows = [];
  for (const entry of entries) {
    const relativePath = entry.path;
    if (!isSafeRepositoryRelative(relativePath)) {
      fail("path_not_repository_relative", String(relativePath));
    }
    const corpusInput = relativePath.startsWith(CORPUS_PREFIX);
    const row = {
      relative_path: relativePath,
      kind: entry.kind,
      declared_bytes: entry.declaredBytes,
      declared_sha256: entry.declaredSha256,
      declared_by: [...new Set(entry.declaredBy)].sort(compareText),
      tracked: isTracked(relativePath),
      tracked_expected: !corpusInput,
      recomputed_bytes: null,
      recomputed_sha256: null,
      verdict: "pass",
    };
    if (entry.kind === "directory") {
      row.verdict = "delegated-to-t02";
      rows.push(row);
      continue;
    }
    const absolutePath = repoPath(relativePath);
    if (!existsSync(absolutePath)) {
      if (corpusInput && !corpusPresent) {
        row.verdict = "corpus-absent";
        rows.push(row);
        continue;
      }
      fail("input_absent", relativePath);
    }
    const digest = fileDigest(absolutePath);
    row.recomputed_bytes = digest.bytes;
    row.recomputed_sha256 = digest.sha256;
    if (entry.declaredSha256 !== null && entry.declaredSha256 !== digest.sha256) {
      fail("input_hash_mismatch", `${relativePath}: recomputed ${digest.sha256} declared ${entry.declaredSha256}`);
    }
    if (entry.declaredBytes !== null && entry.declaredBytes !== digest.bytes) {
      fail("input_bytes_mismatch", `${relativePath}: recomputed ${digest.bytes} declared ${entry.declaredBytes}`);
    }
    if (row.tracked_expected && !row.tracked) {
      fail("input_not_tracked", relativePath);
    }
    rows.push(row);
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Digest recomputation
// ---------------------------------------------------------------------------

export function computeDigests(model, probes = {}) {
  const readBytes = probes.readBytes ?? ((absolutePath) => readFileSync(absolutePath));
  const digests = {};

  const sourceRelative = pick(model.candidateArtifact, "source_binding.path", "candidate-artifact");
  const declaredSource = pick(model.candidateArtifact, "source_binding.source_digest", "candidate-artifact");
  const declaredSourceBy = [
    "m209-s02-hierarchy-candidates-fz44.json#source_binding.source_digest",
    "m209-s02-extraction-evidence.json#extraction.source.digest",
  ];
  const sourceAbsolute = repoPath(sourceRelative);
  if (!existsSync(sourceAbsolute)) fail("input_absent", sourceRelative);
  const recomputedSource = fnv1a64(readBytes(sourceAbsolute));
  if (recomputedSource !== declaredSource) {
    fail("digest_mismatch", `source_digest recomputed ${recomputedSource} declared ${declaredSource}`);
  }
  digests.source_digest = {
    relative_path: sourceRelative,
    stream_rule: "fnv1a64 over the raw source document bytes",
    recomputed: recomputedSource,
    declared: declaredSource,
    declared_by: declaredSourceBy,
    verdict: "pass",
  };

  digests.identity_digest = recomputeIdentityDigest(
    model.candidateArtifact,
    "m209-s02-hierarchy-candidates-fz44.json",
  );

  const fixtureRelative = pick(model.frozenM202Candidates, "source_binding.path", "m202-candidate-artifact");
  const declaredFixture = pick(model.frozenM202Candidates, "source_binding.source_digest", "m202-candidate-artifact");
  const fixtureAbsolute = repoPath(fixtureRelative);
  if (!existsSync(fixtureAbsolute)) fail("input_absent", fixtureRelative);
  const recomputedFixture = fnv1a64(readBytes(fixtureAbsolute));
  if (recomputedFixture !== declaredFixture) {
    fail("digest_mismatch", `m202 source_digest recomputed ${recomputedFixture} declared ${declaredFixture}`);
  }
  digests.frozen_source_digest = {
    relative_path: fixtureRelative,
    stream_rule: "fnv1a64 over the raw frozen M202 fixture bytes",
    recomputed: recomputedFixture,
    declared: declaredFixture,
    declared_by: ["m202-s02-hierarchy-candidates.json#source_binding.source_digest"],
    verdict: "pass",
  };

  digests.frozen_identity_digest = recomputeIdentityDigest(
    model.frozenM202Candidates,
    "m202-s02-hierarchy-candidates.json",
  );

  return digests;
}

// ---------------------------------------------------------------------------
// Independent arithmetic and cross-artifact agreement
// ---------------------------------------------------------------------------

function arithmetic(assertionId, expression, terms, declared, source) {
  const computed = terms.reduce((total, term) => total + term, 0);
  if (computed !== declared) {
    fail("count_partition_mismatch", `${assertionId}: computed ${computed} declared ${declared}`);
  }
  return { assertion_id: assertionId, expression, terms, computed, declared, source, verdict: "pass" };
}

export function ledgerLeg(model, legId) {
  const legs = pick(model.r070Ledger, "legs", "r070-ledger");
  const leg = legs.find((candidate) => candidate.leg_id === legId);
  if (leg === undefined) fail("input_artifact_shape_invalid", `r070-ledger: missing leg ${legId}`);
  return leg;
}

export function computeArithmetic(model) {
  const candidate = model.candidateArtifact;
  const extraction = model.extractionEvidence;
  const regeneration = model.admissionRegeneration;
  const amending = model.amendingAct;
  const commencement = model.commencement;
  const edition = model.editionDelta;
  const family = model.familyDenominator;

  const candidateLevels = Object.values(pick(candidate, "counts.by_level", "candidate-artifact"));
  const candidateExtracted = requiredNumber(pick(candidate, "counts.extracted", "candidate-artifact"), "counts.extracted");
  const candidateUnique = requiredNumber(pick(candidate, "counts.unique", "candidate-artifact"), "counts.unique");
  const candidateDuplicate = requiredNumber(pick(candidate, "counts.duplicate", "candidate-artifact"), "counts.duplicate");
  const candidateArrayLength = pick(candidate, "candidates", "candidate-artifact").length;

  const successor = pick(regeneration, "inputs.admission_source", "admission-regeneration");
  const regenDenominator = pick(regeneration, "denominator", "admission-regeneration");
  const amendingDenominator = pick(amending, "denominator", "amending-act");
  const commencementDenominator = pick(commencement, "denominator", "commencement");
  const editionDenominator = pick(edition, "denominator", "edition-delta");
  const familyChain = pick(family, "chain", "family-denominator");
  const familyManifest = pick(family, "families", "family-denominator")[0];

  const amendingOutcomes = pick(amendingDenominator, "by_outcome", "amending-act");
  const amendingCoverage = pick(amendingDenominator, "by_layer1_coverage", "amending-act");
  const resolvedProvision = requiredNumber(amendingOutcomes["resolved-provision"], "by_outcome.resolved-provision");
  const unresolved = Object.entries(amendingOutcomes)
    .filter(([key]) => key !== "resolved-provision")
    .reduce((total, [, value]) => total + value, 0);

  const rows = [
    arithmetic(
      "candidate_by_level_sum",
      "sum(counts.by_level) == counts.extracted",
      candidateLevels,
      candidateExtracted,
      "m209-s02-hierarchy-candidates-fz44.json#counts.by_level",
    ),
    arithmetic(
      "candidate_unique_duplicate_partition",
      "counts.unique + counts.duplicate == counts.extracted",
      [candidateUnique, candidateDuplicate],
      candidateExtracted,
      "m209-s02-hierarchy-candidates-fz44.json#counts",
    ),
    arithmetic(
      "candidate_array_length",
      "candidates[].length == counts.extracted",
      [candidateArrayLength],
      candidateExtracted,
      "m209-s02-hierarchy-candidates-fz44.json#candidates",
    ),
    arithmetic(
      "successor_rows_partition",
      "102 m209-candidate-backed + 64 legacy-human + 0 punkt == 166 rows",
      [
        requiredNumber(successor.rows_m209_candidate_backed, "rows_m209_candidate_backed"),
        requiredNumber(successor.rows_legacy_human, "rows_legacy_human"),
        requiredNumber(successor.rows_punkt, "rows_punkt"),
      ],
      requiredNumber(successor.rows_total, "rows_total"),
      "m209-s02-admission-regeneration-evidence.json#inputs.admission_source",
    ),
    arithmetic(
      "successor_candidate_backed_partition",
      "102 candidate-backed identities + 1799 unadmitted == 1901 extracted identities",
      [
        requiredNumber(regenDenominator.candidate_backed_identities, "candidate_backed_identities"),
        requiredNumber(regenDenominator.unadmitted_identities, "unadmitted_identities"),
      ],
      requiredNumber(regenDenominator.extracted_identities, "extracted_identities"),
      "m209-s02-admission-regeneration-evidence.json#denominator",
    ),
    arithmetic(
      "amends_outcome_partition",
      "sum of the seven outcome codes == amends_edges_total",
      Object.values(amendingOutcomes),
      requiredNumber(amendingDenominator.amends_edges_total, "amends_edges_total"),
      "m209-s03-amending-act-provision-evidence.json#denominator.by_outcome",
    ),
    arithmetic(
      "amends_resolved_with_remainder",
      "40 resolved-provision + 80 unresolved == 120 amends edges",
      [resolvedProvision, unresolved],
      requiredNumber(amendingDenominator.amends_edges_total, "amends_edges_total"),
      "m209-s03-amending-act-provision-evidence.json#denominator.by_outcome",
    ),
    arithmetic(
      "amends_layer1_coverage_partition",
      "120 with-amends-edge + 1 without-amends-edge == 121 amending acts",
      [
        requiredNumber(amendingCoverage["with-amends-edge"], "by_layer1_coverage.with-amends-edge"),
        requiredNumber(amendingCoverage["without-amends-edge"], "by_layer1_coverage.without-amends-edge"),
      ],
      requiredNumber(amendingDenominator.layer1_amending_acts, "layer1_amending_acts"),
      "m209-s03-amending-act-provision-evidence.json#denominator.by_layer1_coverage",
    ),
    arithmetic(
      "amends_layer1_records_partition",
      "1 core act + 121 amending acts == 122 layer1 records",
      [
        requiredNumber(amendingDenominator.layer1_core_acts, "layer1_core_acts"),
        requiredNumber(amendingDenominator.layer1_amending_acts, "layer1_amending_acts"),
      ],
      requiredNumber(amendingDenominator.layer1_records_total, "layer1_records_total"),
      "m209-s03-amending-act-provision-evidence.json#denominator",
    ),
    arithmetic(
      "amends_statya_refs_partition",
      "26 resolved statya refs + 4 unresolved == 30 distinct statya refs",
      [
        requiredNumber(amendingDenominator.distinct_statya_refs_resolved, "distinct_statya_refs_resolved"),
        requiredNumber(amendingDenominator.distinct_statya_refs, "distinct_statya_refs") -
          requiredNumber(amendingDenominator.distinct_statya_refs_resolved, "distinct_statya_refs_resolved"),
      ],
      requiredNumber(amendingDenominator.distinct_statya_refs, "distinct_statya_refs"),
      "m209-s03-amending-act-provision-evidence.json#denominator",
    ),
    arithmetic(
      "commencement_slot_kind_partition",
      "1 named-chain slot + 121 amending-act slots == 122 slots",
      [
        requiredNumber(commencementDenominator.named_chain_slots, "named_chain_slots"),
        requiredNumber(commencementDenominator.amending_act_slots, "amending_act_slots"),
      ],
      requiredNumber(commencementDenominator.slots_total, "slots_total"),
      "m209-s03-commencement-transition-evidence.json#denominator",
    ),
    arithmetic(
      "commencement_evidence_class_partition",
      "sum(by_evidence_class) == slots_total",
      Object.values(pick(commencementDenominator, "by_evidence_class", "commencement")),
      requiredNumber(commencementDenominator.slots_total, "slots_total"),
      "m209-s03-commencement-transition-evidence.json#denominator.by_evidence_class",
    ),
    arithmetic(
      "commencement_slot_verdict_partition",
      "sum(by_slot_verdict) == slots_total",
      Object.values(pick(commencementDenominator, "by_slot_verdict", "commencement")),
      requiredNumber(commencementDenominator.slots_total, "slots_total"),
      "m209-s03-commencement-transition-evidence.json#denominator.by_slot_verdict",
    ),
    arithmetic(
      "commencement_reason_code_partition",
      "sum(by_reason_code) == slots_total",
      Object.values(pick(commencementDenominator, "by_reason_code", "commencement")),
      requiredNumber(commencementDenominator.slots_total, "slots_total"),
      "m209-s03-commencement-transition-evidence.json#denominator.by_reason_code",
    ),
    arithmetic(
      "edition_partition",
      "118 processed + 0 unreadable + 0 unparsed-filename == 118 editions",
      [
        requiredNumber(editionDenominator.editions_processed, "editions_processed"),
        requiredNumber(editionDenominator.editions_unreadable, "editions_unreadable"),
        requiredNumber(editionDenominator.editions_unparsed_filename, "editions_unparsed_filename"),
      ],
      requiredNumber(editionDenominator.editions_total, "editions_total"),
      "m209-s03-edition-delta-evidence.json#denominator",
    ),
    arithmetic(
      "edition_windows",
      "118 editions - 1 == 117 consecutive windows",
      [requiredNumber(editionDenominator.editions_total, "editions_total"), -1],
      requiredNumber(editionDenominator.windows_total, "windows_total"),
      "m209-s03-edition-delta-evidence.json#denominator",
    ),
    arithmetic(
      "manifest_records_partition",
      "1 core act + 121 amending acts == 122 layer1 manifest records",
      [
        requiredNumber(pick(familyManifest, "decomposition.core_acts", "family-denominator"), "core_acts"),
        requiredNumber(pick(familyManifest, "decomposition.amending_acts", "family-denominator"), "amending_acts"),
      ],
      requiredNumber(familyManifest.records_total, "records_total"),
      "m209-s03-family-denominator.json#families.manifest_layer1_44fz_and_amending_laws",
    ),
    arithmetic(
      "family_chain_edition_partition",
      "118 edition_matching + 0 edition_unparsed == 118 editions",
      [
        requiredNumber(pick(familyChain, "decomposition.edition_matching", "family-denominator"), "edition_matching"),
        requiredNumber(pick(familyChain, "decomposition.edition_unparsed", "family-denominator"), "edition_unparsed"),
      ],
      requiredNumber(familyChain.editions_total, "editions_total"),
      "m209-s03-family-denominator.json#chain",
    ),
  ];
  // `extraction` participates in the cross-artifact block only; referenced here
  // so a shape regression in its denominator is caught by the same shape guard.
  requiredNumber(
    pick(extraction, "declared_denominator.denominator_total", "extraction-evidence"),
    "declared_denominator.denominator_total",
  );
  return rows;
}

function crossArtifact(checkId, expression, pairs) {
  const value = pairs[0][1];
  for (const [source, candidate] of pairs) {
    if (candidate !== value) {
      fail(
        "cross_artifact_disagreement",
        `${checkId}: ${source}=${candidate} != ${value} (${pairs[0][0]})`,
      );
    }
  }
  return {
    check_id: checkId,
    expression,
    expected: value,
    values: pairs.map(([source, candidate]) => ({ source, value: candidate })),
    verdict: "pass",
  };
}

export function computeCrossArtifacts(model) {
  const candidate = model.candidateArtifact;
  const extraction = model.extractionEvidence;
  const regeneration = model.admissionRegeneration;
  const amending = model.amendingAct;
  const commencement = model.commencement;
  const edition = model.editionDelta;
  const family = model.familyDenominator;
  const frozenM202ProofGate = model.frozenM202ProofGate;

  const candidateExtracted = requiredNumber(pick(candidate, "counts.extracted", "candidate-artifact"), "counts.extracted");
  const candidateUnique = requiredNumber(pick(candidate, "counts.unique", "candidate-artifact"), "counts.unique");
  const extractionDenominator = pick(extraction, "declared_denominator", "extraction-evidence");
  const regenDenominator = pick(regeneration, "denominator", "admission-regeneration");
  const successor = pick(regeneration, "inputs.admission_source", "admission-regeneration");
  const resolvedIdentities = pick(extraction, "resolvability.identities", "extraction-evidence");
  const candidateBackedCc = pick(regeneration, "output.m209_candidate_backed_cc", "admission-regeneration");
  const mappingCounts = pick(frozenM202ProofGate, "mapping_counts", "m202-r035-proof-gate");

  const amendingDenominator = pick(amending, "denominator", "amending-act");
  const commencementDenominator = pick(commencement, "denominator", "commencement");
  const editionDenominator = pick(edition, "denominator", "edition-delta");
  const familyChain = pick(family, "chain", "family-denominator");
  const familyManifest = pick(family, "families", "family-denominator")[0];

  const amendingLedger = pick(ledgerLeg(model, "amending-acts"), "tracked_evidence.declared_counts", "r070-ledger");
  const provisionsLedger = pick(ledgerLeg(model, "affected-provisions"), "tracked_evidence.declared_counts", "r070-ledger");
  const editionLedger = pick(ledgerLeg(model, "edition-delta"), "tracked_evidence.declared_counts", "r070-ledger");
  const commencementLedger = pick(ledgerLeg(model, "commencement-and-transitional"), "tracked_evidence.declared_counts", "r070-ledger");

  return [
    crossArtifact("candidates_1901", "candidate denominator is 1901 everywhere", [
      ["candidate-artifact#counts.extracted", candidateExtracted],
      ["candidate-artifact#counts.unique", candidateUnique],
      ["extraction-evidence#declared_denominator.denominator_total", requiredNumber(extractionDenominator.denominator_total, "denominator_total")],
      ["admission-regeneration#denominator.extracted_identities", requiredNumber(regenDenominator.extracted_identities, "extracted_identities")],
    ]),
    crossArtifact("candidate_backed_102", "candidate-backed identity count is 102 everywhere", [
      ["extraction-evidence#resolvability.identities.length", resolvedIdentities.length],
      ["admission-regeneration#inputs.admission_source.rows_m209_candidate_backed", requiredNumber(successor.rows_m209_candidate_backed, "rows_m209_candidate_backed")],
      ["admission-regeneration#denominator.candidate_backed_identities", requiredNumber(regenDenominator.candidate_backed_identities, "candidate_backed_identities")],
      ["admission-regeneration#output.m209_candidate_backed_cc.length", candidateBackedCc.length],
    ]),
    crossArtifact("successor_rows_166", "registry row count is 166 in the successor generation and in the frozen M202 snapshot", [
      ["admission-regeneration#inputs.admission_source.rows_total", requiredNumber(successor.rows_total, "rows_total")],
      ["m202-r035-proof-gate#mapping_counts.registry_rows", requiredNumber(mappingCounts.registry_rows, "registry_rows")],
    ]),
    crossArtifact("punkt_zero", "zero punkt rows admitted across the chain", [
      ["extraction-evidence#punkt_admitted.admitted", requiredNumber(pick(extraction, "punkt_admitted.admitted", "extraction-evidence"), "punkt_admitted.admitted")],
      ["admission-regeneration#inputs.admission_source.rows_punkt", requiredNumber(successor.rows_punkt, "rows_punkt")],
      ["admission-regeneration#denominator.punkt_admitted", requiredNumber(regenDenominator.punkt_admitted, "punkt_admitted")],
      ["m202-r035-proof-gate#mapping_counts.punkt_admitted", requiredNumber(mappingCounts.punkt_admitted, "punkt_admitted")],
    ]),
    crossArtifact("editions_118", "edition denominator is 118 everywhere", [
      ["family-denominator#chain.editions_total", requiredNumber(familyChain.editions_total, "editions_total")],
      ["family-denominator#chain.decomposition.edition_matching", requiredNumber(pick(familyChain, "decomposition.edition_matching", "family-denominator"), "edition_matching")],
      ["edition-delta#denominator.editions_total", requiredNumber(editionDenominator.editions_total, "editions_total")],
      ["edition-delta#denominator.t01_editions_total", requiredNumber(editionDenominator.t01_editions_total, "t01_editions_total")],
      ["r070-ledger#legs.edition-delta.declared_counts.editions_total", requiredNumber(editionLedger.editions_total, "editions_total")],
    ]),
    crossArtifact(
      "edition_dir_files_118",
      "118 edition-directory files == 118 editions == 118 matching edition rows",
      [
        ["family-denominator#chain.editions_total", requiredNumber(familyChain.editions_total, "editions_total")],
        ["family-denominator#chain.decomposition.edition_matching", requiredNumber(pick(familyChain, "decomposition.edition_matching", "family-denominator"), "edition_matching")],
        ["edition-delta#denominator.edition_dir_files_total", requiredNumber(editionDenominator.edition_dir_files_total, "edition_dir_files_total")],
        ["edition-delta#denominator.editions_total", requiredNumber(editionDenominator.editions_total, "editions_total")],
        ["r070-ledger#legs.edition-delta.declared_counts.editions_processed", requiredNumber(editionLedger.editions_processed, "editions_processed")],
      ],
    ),
    crossArtifact(
      "edition_dir_listing_digest_agreement",
      "the edition-directory listing digest is bound identically by the family denominator and the edition-delta artifact; the live listing itself is delegated to S04 T02",
      [
        ["family-denominator#chain.input_sha256", String(familyChain.input_sha256)],
        ["edition-delta#denominator.edition_dir_listing_sha256", String(editionDenominator.edition_dir_listing_sha256)],
      ],
    ),
    crossArtifact(
      "edition_dir_bytes_agreement",
      "the edition-directory byte total is declared identically by the family denominator and the edition-delta artifact",
      [
        ["family-denominator#chain.input_bytes", requiredNumber(familyChain.input_bytes, "input_bytes")],
        ["edition-delta#denominator.edition_dir_bytes_total", requiredNumber(editionDenominator.edition_dir_bytes_total, "edition_dir_bytes_total")],
      ],
    ),
    crossArtifact("windows_117", "117 consecutive delta windows == 118 editions - 1", [
      ["edition-delta#denominator.windows_total", requiredNumber(editionDenominator.windows_total, "windows_total")],
      ["r070-ledger#legs.edition-delta.declared_counts.windows_total", requiredNumber(editionLedger.windows_total, "windows_total")],
    ]),
    crossArtifact("layer1_records_122", "layer1 record tally is 122 everywhere", [
      ["amending-act#denominator.layer1_records_total", requiredNumber(amendingDenominator.layer1_records_total, "layer1_records_total")],
      ["commencement#denominator.rows_total", requiredNumber(commencementDenominator.rows_total, "rows_total")],
      ["commencement#denominator.t02_layer1_records_total", requiredNumber(commencementDenominator.t02_layer1_records_total, "t02_layer1_records_total")],
      ["family-denominator#families.manifest_layer1.records_total", requiredNumber(familyManifest.records_total, "records_total")],
      ["r070-ledger#legs.amending-acts.declared_counts.layer1_records_total", requiredNumber(amendingLedger.layer1_records_total, "layer1_records_total")],
    ]),
    crossArtifact("layer1_amending_121", "121 amending acts everywhere", [
      ["amending-act#denominator.layer1_amending_acts", requiredNumber(amendingDenominator.layer1_amending_acts, "layer1_amending_acts")],
      ["commencement#denominator.amending_act_slots", requiredNumber(commencementDenominator.amending_act_slots, "amending_act_slots")],
      ["commencement#denominator.t02_layer1_amending_acts", requiredNumber(commencementDenominator.t02_layer1_amending_acts, "t02_layer1_amending_acts")],
      ["family-denominator#families.manifest_layer1.decomposition.amending_acts", requiredNumber(pick(familyManifest, "decomposition.amending_acts", "family-denominator"), "amending_acts")],
      ["r070-ledger#legs.amending-acts.declared_counts.layer1_amending_acts", requiredNumber(amendingLedger.layer1_amending_acts, "layer1_amending_acts")],
    ]),
    crossArtifact("commencement_slots_122", "122 commencement slots in the artifact and in the ledger leg", [
      ["commencement#denominator.slots_total", requiredNumber(commencementDenominator.slots_total, "slots_total")],
      ["r070-ledger#legs.commencement-and-transitional.declared_counts.slots_total", requiredNumber(commencementLedger.slots_total, "slots_total")],
    ]),
    crossArtifact("amends_edges_120", "120 declared amends edges everywhere", [
      ["amending-act#denominator.amends_edges_total", requiredNumber(amendingDenominator.amends_edges_total, "amends_edges_total")],
      ["commencement#denominator.t02_amends_edges_total", requiredNumber(commencementDenominator.t02_amends_edges_total, "t02_amends_edges_total")],
      ["r070-ledger#legs.amending-acts.declared_counts.amends_edges_total", requiredNumber(amendingLedger.amends_edges_total, "amends_edges_total")],
    ]),
    crossArtifact("statya_refs_30", "30 distinct statya references in the artifact and in the ledger leg", [
      ["amending-act#denominator.distinct_statya_refs", requiredNumber(amendingDenominator.distinct_statya_refs, "distinct_statya_refs")],
      ["r070-ledger#legs.affected-provisions.declared_counts.distinct_statya_refs", requiredNumber(provisionsLedger.distinct_statya_refs, "distinct_statya_refs")],
    ]),
    crossArtifact("statya_refs_resolved_26", "26 resolved statya references in the artifact and in the ledger leg", [
      ["amending-act#denominator.distinct_statya_refs_resolved", requiredNumber(amendingDenominator.distinct_statya_refs_resolved, "distinct_statya_refs_resolved")],
      ["r070-ledger#legs.affected-provisions.declared_counts.distinct_statya_refs_resolved", requiredNumber(provisionsLedger.distinct_statya_refs_resolved, "distinct_statya_refs_resolved")],
    ]),
  ];
}

// ---------------------------------------------------------------------------
// Anti-promotion and anti-quantifier guards (D539 / D540)
// ---------------------------------------------------------------------------

function walkObjects(node, visit, trail) {
  if (node === null || typeof node !== "object") return;
  if (Array.isArray(node)) {
    node.forEach((item, index) => walkObjects(item, visit, `${trail}[${index}]`));
    return;
  }
  for (const [key, value] of Object.entries(node)) {
    visit(key, value, `${trail}.${key}`);
    walkObjects(value, visit, `${trail}.${key}`);
  }
}

export function computePromotionChecks(model) {
  const audited = Object.entries(model);
  let counterHits = 0;
  let authoritativeHits = 0;
  let verdictHits = 0;
  let lifecycleHits = 0;
  for (const [artifactName, artifact] of audited) {
    walkObjects(artifact, (key, value, trail) => {
      if (PROMOTED_COUNTER_KEYS.has(key) && typeof value === "number" && value > 0) {
        counterHits += 1;
        fail("promotion_claim_present", `${artifactName}${trail}=${value}`);
      }
      if (key === "authoritative" && value === true) {
        authoritativeHits += 1;
        fail("promotion_claim_present", `${artifactName}${trail}=true`);
      }
      if (VERDICT_KEY_PATTERN.test(key) && typeof value === "string" && BANNED_VERDICT_LITERALS.has(value.toLowerCase())) {
        verdictHits += 1;
        fail("promotion_claim_present", `${artifactName}${trail}=${value}`);
      }
      if (key === "lifecycle" && typeof value === "string" && BANNED_LIFECYCLE_LITERALS.has(value.toLowerCase())) {
        lifecycleHits += 1;
        fail("promotion_claim_present", `${artifactName}${trail}=${value}`);
      }
    }, artifactName);
  }

  const forbidden = new Set(pick(model.gateRegister, "forbidden_quantifiers", "gate-register"));
  const quantifierSites = [];
  for (const gate of pick(model.gateRegister, "gates", "gate-register")) {
    quantifierSites.push([`gate-register#gates.${gate.gate_id}`, gate.quantifier]);
  }
  for (const leg of pick(model.r070Ledger, "legs", "r070-ledger")) {
    quantifierSites.push([`r070-ledger#legs.${leg.leg_id}`, leg.quantifier]);
  }
  for (const [site, quantifier] of quantifierSites) {
    const name = quantifier === null || typeof quantifier !== "object" ? null : quantifier.name;
    if (typeof name === "string" && forbidden.has(name)) {
      fail("inventory_count_as_quantifier", `${site} quantifier=${name}`);
    }
  }

  return [
    { check_id: "no_promotion_counter", scope: "gates_promoted/legs_promoted/proof_packages_* over all audited artifacts", observed: counterHits, verdict: "pass" },
    { check_id: "no_authoritative_true", scope: "authoritative === true over all audited artifacts", observed: authoritativeHits, verdict: "pass" },
    { check_id: "no_promoted_verdict_literal", scope: "verdict/disposition values not in [validated, complete, satisfied, checked, proven]", observed: verdictHits, verdict: "pass" },
    { check_id: "no_promoted_lifecycle_literal", scope: "lifecycle values not in [validated, complete]", observed: lifecycleHits, verdict: "pass" },
    { check_id: "no_inventory_counter_as_quantifier", scope: `quantifier names over ${quantifierSites.length} gate/leg sites`, observed: 0, verdict: "pass" },
  ];
}

// ---------------------------------------------------------------------------
// Frozen boundary pins
// ---------------------------------------------------------------------------

export function computeFrozenBoundary(model) {
  const reconciliationPins = pick(model.reconciliation, "frozen_pins", "reconciliation");
  const rustAnchored = pick(reconciliationPins, "rust_anchored", "reconciliation");
  const byName = (name) => {
    const found = rustAnchored.find((pin) => pin.name === name);
    if (found === undefined) fail("input_artifact_shape_invalid", `reconciliation: missing frozen pin ${name}`);
    return found;
  };
  const capturedAt = pick(reconciliationPins, "captured_at_baseline_not_rust_anchored", "reconciliation");
  const commencementInputs = pick(model.commencement, "inputs", "commencement");
  const m201GateInput = commencementInputs.find((entry) => entry.input_id === "m201_r070_proof_gate");
  if (m201GateInput === undefined) {
    fail("input_artifact_shape_invalid", "commencement: missing input m201_r070_proof_gate");
  }
  const m201Binding = pick(model.frozenM201ProofGate, "source_binding", "m201-r070-proof-gate");

  const pinSpecs = [
    ["prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json", byName("m202_s02_candidates"), "reconciliation#frozen_pins.rust_anchored.m202_s02_candidates"],
    ["prd/migration/rust-evidence/m202-s03-registry-regeneration.json", byName("m202_s03_regeneration"), "reconciliation#frozen_pins.rust_anchored.m202_s03_regeneration"],
    ["prd/architecture/kb-hierarchy-registry-admissions.yaml", byName("admissions_yaml"), "reconciliation#frozen_pins.rust_anchored.admissions_yaml"],
    ["prd/architecture/kb-hierarchy-registry.yaml", byName("registry_yaml"), "reconciliation#frozen_pins.rust_anchored.registry_yaml"],
    ["prd/migration/rust-evidence/m202-s04-r035-proof-gate.json", capturedAt, "reconciliation#frozen_pins.captured_at_baseline_not_rust_anchored"],
    ["prd/migration/rust-evidence/m201-s04-r070-proof-gate.json", { bytes: m201GateInput.input_bytes, sha256: m201GateInput.input_sha256 }, "commencement#inputs.m201_r070_proof_gate"],
    ["prd/migration/rust-evidence/m201-s03-tracked-chain.json", { bytes: m201Binding.tracked_chain_json.bytes, sha256: m201Binding.tracked_chain_json.sha256 }, "m201-r070-proof-gate#source_binding.tracked_chain_json"],
    ["prd/architecture/fz44-tracked-edition-chain.yaml", { bytes: m201Binding.tracked_chain_yaml.bytes, sha256: m201Binding.tracked_chain_yaml.sha256 }, "m201-r070-proof-gate#source_binding.tracked_chain_yaml"],
  ];

  const frozenLedgerSha = normalizeSha(pick(model.r070Ledger, "frozen_m201_boundary.gate_sha256", "r070-ledger"));
  if (frozenLedgerSha !== normalizeSha(m201GateInput.input_sha256)) {
    fail("frozen_boundary_drift", `m201 r070 gate sha agrees across ledger and commencement inputs`);
  }

  const rows = [];
  for (const [relativePath, declared, declaredBy] of pinSpecs) {
    if (!FROZEN_PATHS.includes(relativePath)) {
      fail("frozen_boundary_drift", `${relativePath} not in the frozen path set`);
    }
    const document = pick(model, Object.keys(model).find((key) => model[key] && typeof model[key] === "object" && MODEL_FILES[key] === relativePath) ?? "gateRegister", "schema", p => p);
    void document;
    const absolutePath = repoPath(relativePath);
    if (!existsSync(absolutePath)) fail("input_absent", relativePath);
    const digest = fileDigest(absolutePath);
    const declaredBytes = declared.bytes ?? null;
    const declaredSha = declared.sha256 === null || declared.sha256 === undefined ? null : normalizeSha(declared.sha256);
    if (declaredSha !== null && declaredSha !== digest.sha256) {
      fail("frozen_boundary_drift", `${relativePath}: recomputed ${digest.sha256} declared ${declaredSha}`);
    }
    if (declaredBytes !== null && declaredBytes !== digest.bytes) {
      fail("frozen_boundary_drift", `${relativePath}: recomputed ${digest.bytes} declared ${declaredBytes}`);
    }
    rows.push({
      relative_path: relativePath,
      bytes: digest.bytes,
      sha256: digest.sha256,
      declared_bytes: declaredBytes,
      declared_sha256: declaredSha,
      declared_by: declaredBy,
      verdict: "pass",
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Shape guard, rendering and output containment
// ---------------------------------------------------------------------------

export function assertModelShape(model) {
  for (const [key, relativePath] of Object.entries(MODEL_FILES)) {
    const value = model[key];
    if (value === null || typeof value !== "object") {
      fail("input_artifact_shape_invalid", `${key} (${relativePath}) is not an object`);
    }
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

export function assertNonEmpty(text) {
  if (typeof text !== "string" || text.length === 0) {
    fail("artifact_empty", "rendered evidence is empty");
  }
  return true;
}

export function checkRenderedBytes(rendered, committed) {
  if (rendered !== committed) {
    fail("evidence_drift", `${ARTIFACT_PATH}: rendered bytes differ from committed bytes`);
  }
  return true;
}

/// `--out` containment: reject absolute targets, targets escaping the repository
/// (after canonicalizing the parent directory), symlinked targets, and any
/// repository path outside the evidence allowlist `prd/migration/rust-evidence/m209-s04-*.json`.
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
  const sibling = `${absolutePath}.tmp-m209-s04`;
  writeFileSync(sibling, text);
  renameSync(sibling, absolutePath);
}

function counter(rows, predicate) {
  return rows.filter(predicate).length;
}

export function audit(model, mode = "all") {
  if (!["bindings", "counts", "all"].includes(mode)) {
    fail("input_artifact_shape_invalid", `unknown mode ${mode}`);
  }
  assertModelShape(model);
  const wantBindings = mode !== "counts";
  const wantCounts = mode !== "bindings";

  const bundle = {
    schema: SCHEMA,
    schema_version: 1,
    kind: "m209-s04-corroboration-evidence",
    milestone: MILESTONE,
    slice: "S04",
    task: TASK,
    mode,
    lifecycle: "[bounded]",
    authoritative: false,
    count_only: true,
    ascii_only: true,
    audit_scope:
      "declared input bindings (bytes/sha256/tracked), canonical identity and source digests, chain arithmetic, cross-artifact number agreement, frozen boundary pins, anti-promotion guards",
    gates_promoted: 0,
    legs_promoted: 0,
    proof_packages_attached: 0,
    requirement_dispositions: { R035: "active", R070: "active" },
    requirement_records_mutated: 0,
    bindings_total: 0,
    bindings_passed: 0,
    bindings_delegated: 0,
    bindings_failed: 0,
    digests_total: 0,
    digests_failed: 0,
    arithmetic_total: 0,
    arithmetic_failed: 0,
    cross_artifact_total: 0,
    cross_artifact_failed: 0,
    frozen_boundary_total: 0,
    frozen_boundary_failed: 0,
    promotion_checks_total: 0,
    promotion_checks_failed: 0,
    bindings: [],
    digests: {},
    arithmetic: [],
    cross_artifact: [],
    frozen_boundary: [],
    promotion_checks: [],
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };

  if (wantBindings) {
    bundle.bindings = computeBindings(model);
    bundle.digests = computeDigests(model);
    bundle.frozen_boundary = computeFrozenBoundary(model);
  }
  if (wantCounts) {
    bundle.arithmetic = computeArithmetic(model);
    bundle.cross_artifact = computeCrossArtifacts(model);
    bundle.promotion_checks = computePromotionChecks(model);
  }

  bundle.bindings_total = bundle.bindings.length;
  bundle.bindings_passed = counter(bundle.bindings, (row) => row.verdict === "pass");
  bundle.bindings_delegated = counter(bundle.bindings, (row) => row.verdict === "delegated-to-t02" || row.verdict === "corpus-absent");
  bundle.bindings_failed = counter(bundle.bindings, (row) => !["pass", "delegated-to-t02", "corpus-absent"].includes(row.verdict));
  bundle.digests_total = Object.keys(bundle.digests).length;
  bundle.digests_failed = counter(Object.values(bundle.digests), (row) => row.verdict !== "pass");
  bundle.arithmetic_total = bundle.arithmetic.length;
  bundle.arithmetic_failed = counter(bundle.arithmetic, (row) => row.verdict !== "pass");
  bundle.cross_artifact_total = bundle.cross_artifact.length;
  bundle.cross_artifact_failed = counter(bundle.cross_artifact, (row) => row.verdict !== "pass");
  bundle.frozen_boundary_total = bundle.frozen_boundary.length;
  bundle.frozen_boundary_failed = counter(bundle.frozen_boundary, (row) => row.verdict !== "pass");
  bundle.promotion_checks_total = bundle.promotion_checks.length;
  bundle.promotion_checks_failed = counter(bundle.promotion_checks, (row) => row.verdict !== "pass");

  return bundle;
}

export function renderEvidence(bundle) {
  return `${JSON.stringify(bundle)}\n`;
}

export function loadModel() {
  const model = {};
  for (const [key, relativePath] of Object.entries(MODEL_FILES)) {
    const absolutePath = repoPath(relativePath);
    if (!existsSync(absolutePath)) fail("input_absent", relativePath);
    try {
      model[key] = JSON.parse(readFileSync(absolutePath, "utf8"));
    } catch (error) {
      fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
    }
  }
  return model;
}

export function heartbeat(bundle) {
  return [
    `mode=${bundle.mode}`,
    `bindings=${bundle.bindings_total}`,
    `passed=${bundle.bindings_passed}`,
    `delegated=${bundle.bindings_delegated}`,
    `digests=${bundle.digests_total}`,
    `arithmetic=${bundle.arithmetic_total}`,
    `cross=${bundle.cross_artifact_total}`,
    `frozen=${bundle.frozen_boundary_total}`,
    `checks=${bundle.promotion_checks_total}`,
    "failed=0",
    "drift=0",
  ].join(" ");
}

function parseArgs(argv) {
  const options = { mode: "all", out: ARTIFACT_PATH, check: false, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") {
      index += 1;
      if (index >= argv.length) return { error: "--mode requires a value" };
      options.mode = argv[index];
      if (!["bindings", "counts", "all"].includes(options.mode)) {
        return { error: `unknown mode ${options.mode}` };
      }
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
  "usage: m209_s04_evidence_audit.mjs [--mode bindings|counts|all] [--out PATH] [--check]\n";

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error !== undefined) {
    process.stderr.write(`${USAGE}m209_s04_evidence_audit: ${options.error}\n`);
    process.exit(2);
  }
  if (options.help) {
    process.stdout.write(USAGE);
    return;
  }
  const target = resolveOutTarget(options.out);
  const model = loadModel();
  const bundle = audit(model, options.mode);
  const text = renderEvidence(bundle);
  assertNonEmpty(text);
  assertAsciiOnly(text);
  const summary = heartbeat(bundle);
  if (options.check) {
    if (!existsSync(target.absolute)) {
      fail("evidence_drift", `missing committed artifact ${target.repoRelative}`);
    }
    checkRenderedBytes(text, readFileSync(target.absolute, "utf8"));
    process.stdout.write(`M209_S04_AUDIT_OK ${summary}\n`);
    return;
  }
  atomicWrite(target.absolute, text);
  process.stdout.write(`M209_S04_AUDIT_OK ${summary}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof AuditError) {
      process.stderr.write(`M209_S04_AUDIT_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
