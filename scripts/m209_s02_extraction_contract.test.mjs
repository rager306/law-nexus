// M209/S02 candidate-backed coverage contract (T01).
//
// Offline and fail-closed. The claim under test is a *denominator*, not an
// inventory count (D547): one live extractor run over one named tracked edition
// of 44-ФЗ produced a candidate artifact whose identities are counted by level,
// of which only the 102 glava/statya identities resolve one-to-one into an
// already-existing ComponentConcept row of kb-hierarchy-registry.yaml. The
// remaining 1799 nested identities stay unadmitted under a named reason code,
// 0 of 997 punkt candidates are admitted, and no ComponentConcept is minted.
//
// Everything measured here is re-derived from the live files, never trusted
// from prose:
//   - the artifact's counts, ladder and identity set are read from the artifact;
//   - `source_digest` is recomputed as FNV-1a 64 over the exact source bytes;
//   - `identity_digest` is recomputed as FNV-1a 64 over the canonical identity
//     stream (NUL-separated fields, one record per line, candidates in document
//     order then duplicate diagnostics) exactly as
//     crates/ln-decode/src/hierarchy_artifact.rs renders it;
//   - the resolvable set is recomputed by intersecting the artifact's
//     glava/statya candidates with the registry's `law_2013-04-05_44-fz` rows.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (clean-worktree proof). No cargo, no
// network, no extractor re-run, no `.gsd` / ignored / absolute path is ever read
// as evidence, and this contract never writes a file.
//
// The M209/S02 candidate artifact and its evidence record are authored in T01
// and committed by closeout, so `git ls-files` cannot see them at first run;
// they are therefore asserted to exist and to be repository-relative, while the
// tracked source and every frozen M202 input are asserted tracked.
//
// Run: node --test scripts/m209_s02_extraction_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const SOURCE =
  "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml";
const ARTIFACT = "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";
const EVIDENCE = "prd/migration/rust-evidence/m209-s02-extraction-evidence.json";
const REGISTRY = "prd/architecture/kb-hierarchy-registry.yaml";
const M202_S02 = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_S03 = "prd/migration/rust-evidence/m202-s03-registry-regeneration.json";
const M202_S04 = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
const ADMISSIONS_YAML = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const RUST_PIN = "crates/ln-kb-ontology/tests/r035_proof_gate.rs";
const CONTRACT_PATH = "scripts/m209_s02_extraction_contract.test.mjs";

// Frozen M202 evidence: any worktree delta here is frozen-input drift.
const FROZEN_M202_INPUTS = [M202_S02, M202_S03, M202_S04, ADMISSIONS_YAML, REGISTRY, RUST_PIN];

const ARTIFACT_SCHEMA = "law-nexus-hierarchy-candidate-artifact/v1";
const ARTIFACT_LIFECYCLE = "[proposed]";
const ARTIFACT_PAYLOAD_REF = "payload:m209-s02-fz44-edition";
const EVIDENCE_SCHEMA = "law-nexus/m209-s02-extraction-evidence/v1";
const EVIDENCE_LIFECYCLE = "[bounded]";
const NEEDLE = "law_2013-04-05_44-fz";
const NESTED_REASON = "nested-level-no-existing-cc-identity";
const FNV_PATTERN = /^fnv1a64:[0-9a-f]{16}$/;

// The full catalog ladder the artifact renders, and the declared denominator
// decomposition D547 binds to the extracted total.
const ALL_LEVELS = ["razdel", "glava", "paragraph", "statya", "chast", "punkt", "podpunkt"];
const DECLARED_BY_LEVEL = { glava: 8, statya: 94, chast: 793, punkt: 997, paragraph: 9 };
const DENOMINATOR_TOTAL = 1901;
const RESOLVABLE_TOTAL = 102;
const RESOLVABLE_BY_LEVEL = { glava: 8, statya: 94 };
const UNADMITTED_TOTAL = 1799;
const UNADMITTED_LEVELS = ["chast", "punkt", "paragraph"];
const PUNKT_DECISION_REFS = ["D540", "D426", "D192"];

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// Raw legal prose must never enter a count-only candidate artifact.
const RAW_LEGAL_TEXT_MARKERS = ["Статья", "Глава", "Федеральный закон", "Article ", "Federal Law"];

// The evidence record must bound its own claims (D547 / RC28-F16).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not admission",
  "no componentconcept identifier is minted",
  "not r035 validation",
  "no promotion gate is promoted",
  "legacy-human registry inventory is not extraction proof",
  "punkt registry admission stays blocked",
  "frozen m202 evidence are untouched",
  "r070 is not affected",
];

// The complete fail-closed code set. The `## Fail-closed codes` comment block
// below is asserted to document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "artifact_count_mismatch",
  "artifact_by_level_mismatch",
  "artifact_denominator_missing",
  "denominator_zero_treated_as_measurement",
  "source_digest_mismatch",
  "identity_digest_mismatch",
  "source_untracked",
  "source_modified",
  "unresolved_identity",
  "registry_only_identity",
  "punkt_admitted_without_decision",
  "cc_minted",
  "ignored_path_as_source",
  "absolute_path_as_source",
  "raw_legal_text_in_artifact",
  "frozen_m202_artifact_modified",
  "r035_promoted",
  "non_claims_missing",
];

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// artifact_count_mismatch: the validated pair is not the pinned pair — the artifact or evidence record is missing or unparsable, the record identity drifted, the live artifact does not match its path/schema/sha256/byte-count/payload-ref pin, or the artifact counts are not internally consistent with the declared denominator total.
// artifact_by_level_mismatch: the artifact's level ladder or per-level counts drifted from the declared decomposition, the declared denominator's by_level disagrees with the artifact, or the by-level accounting of the 1799 unadmitted remainder (level, count, reason code, decision refs) drifted.
// artifact_denominator_missing: the declared denominator block is absent, its total disagrees with the artifact's extracted count, its derivation basis or definition is empty, its decision ref is not D547, or the declared source path is missing.
// denominator_zero_treated_as_measurement: a zero denominator, a zero-sum level decomposition, or an unset zero_denominator_is_not_a_measurement flag is being presented as a measurement.
// source_digest_mismatch: the FNV-1a 64 digest or sha256 of the exact source bytes, the recorded source byte count, or the recorded source digest binding drifted from a well-formed fnv1a64 value.
// identity_digest_mismatch: the FNV-1a 64 digest of the canonical identity stream, the recorded identity digest binding, or the identity digest's distinctness from the source digest drifted.
// source_untracked: the declared source path is missing, is not the one named tracked edition, or is not git-tracked, or the record claims tracked=false.
// source_modified: the tracked source carries a worktree delta.
// unresolved_identity: an extracted glava/statya identity has no registry binding, its key_path is not its number, or the recomputed matched/unmatched counts disagree with the declared ones.
// registry_only_identity: a registry needle row has no extracted counterpart, a declared resolvable identity is not a live extracted candidate, or the declared registry_only count is not zero.
// punkt_admitted_without_decision: punkt_admitted is not exactly 0 of 997, a punkt candidate is declared resolvable, or the punkt decision refs D540/D426/D192 are missing.
// cc_minted: a declared ComponentConcept identifier is not the registry row for that identity, is reused across identities, the artifact text carries a ComponentConcept identifier, or the resolved identites collide.
// ignored_path_as_source: a declared source anchor is an ignored overlay path.
// absolute_path_as_source: a declared source anchor is absolute or traversing.
// raw_legal_text_in_artifact: the artifact is not count_only/ascii_only, its text is not ASCII, or it carries raw legal prose.
// frozen_m202_artifact_modified: a frozen M202 input is missing, untracked, or carries a worktree delta.
// r035_promoted: the record promotes itself or R035 past bounded extraction evidence — R035 left active, the disposition decision drifted, authority or an unbounded lifecycle was claimed, or the frozen M202 snapshot shows a promoted gate verdict.
// non_claims_missing: the evidence record carries no non-claims or omits a required one.
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

function readRepoBuffer(relativePath) {
  return readFileSync(path.join(root, relativePath));
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
    .update(readRepoBuffer(relativePath))
    .digest("hex");
  hashCache.set(relativePath, digest);
  return digest;
}

function sha256Buffer(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function repoBytes(relativePath) {
  return readRepoBuffer(relativePath).length;
}

// `git status --porcelain` restricted to the given paths: an empty result means
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

// Exact key set and exact values (JSON.stringify would compare key order too,
// and the artifact ladder is rendered in a different order than the denominator).
function sameByLevel(a, b) {
  const ka = Object.keys(a ?? {}).sort();
  const kb = Object.keys(b ?? {}).sort();
  if (ka.length !== kb.length || ka.some((key, index) => key !== kb[index])) return false;
  return ka.every((key) => a[key] === b[key]);
}

function identityKey(level, number) {
  return `${level}\u0000${number}`;
}

function isIgnoredPath(value) {
  return (
    typeof value === "string" && IGNORED_SOURCE_PREFIXES.some((prefix) => value.startsWith(prefix))
  );
}

function isAbsolutePath(value) {
  if (typeof value !== "string") return false;
  return value.startsWith("/") || value.split("/").includes("..");
}

// FNV-1a 64 over exact bytes, matching ln_decode::domain::fingerprint_bytes
// (offset basis 0xcbf29ce484222325, prime 0x100000001b3, `fnv1a64:%016x`).
function fnv1a64(buffer) {
  let hash = 0xcbf29ce484222325n;
  const mask = (1n << 64n) - 1n;
  for (const byte of buffer) {
    hash ^= BigInt(byte);
    hash = (hash * 0x100000001b3n) & mask;
  }
  return `fnv1a64:${hash.toString(16).padStart(16, "0")}`;
}

// The canonical identity stream the artifact pins: unique candidates in document
// order, then duplicate diagnostics, NUL-separated fields, one line per record.
function identityStream(artifact) {
  const candidates = Array.isArray(artifact?.candidates) ? artifact.candidates : [];
  const duplicates = Array.isArray(artifact?.diagnostics?.duplicate_keys)
    ? artifact.diagnostics.duplicate_keys
    : [];
  let stream = "";
  for (const row of candidates) {
    stream += `${row?.catalog_token}\u0000${row?.number}\u0000${row?.path == null ? "" : row.path}\u0000${row?.key_path}\u0000${String(row?.depth)}\n`;
  }
  for (const row of duplicates) {
    stream += `dup\u0000${row?.catalog_token}\u0000${row?.key_path}\u0000${String(row?.first_index)}\u0000${String(row?.later_index)}\n`;
  }
  return stream;
}

// The registry's explicit marker -> ComponentConcept rows for one path needle.
function parseRegistryBindings(text, needle) {
  const bindings = [];
  for (const line of String(text).split("\n")) {
    const match = line.match(
      /^-\s*\{path_needle:\s*([^,]+),\s*level:\s*([^,]+),\s*number:\s*"?([^",]+)"?,\s*cc:\s*([^}]+)\}\s*$/,
    );
    if (!match) continue;
    if (match[1].trim() !== needle) continue;
    bindings.push({ level: match[2].trim(), number: match[3].trim(), cc: match[4].trim() });
  }
  return bindings;
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateExtraction(artifact, evidence, overrides = {}) {
  const pick = (key, fallback) => (overrides[key] === undefined ? fallback : overrides[key]);
  const sourceBytes = pick("sourceBytes", liveSourceBytes);
  const artifactText = pick("artifactText", liveArtifactText);
  const registryText = pick("registryText", liveRegistryText);
  const m202Text = pick("m202Text", liveM202Text);
  const trackedSource = pick("trackedSource", isTracked(SOURCE));
  const sourceDelta = pick("sourceDelta", worktreeDelta([SOURCE]));
  const frozenDelta = pick("frozenDelta", worktreeDelta(FROZEN_M202_INPUTS));

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  const counts = artifact?.counts ?? {};
  const byLevel = counts?.by_level ?? {};
  const candidates = Array.isArray(artifact?.candidates) ? artifact.candidates : [];
  const duplicateRows = Array.isArray(artifact?.diagnostics?.duplicate_keys)
    ? artifact.diagnostics.duplicate_keys
    : [];
  const sourceBinding = artifact?.source_binding ?? {};
  const evidenceArtifact = evidence?.extraction?.artifact ?? {};
  const evidenceSource = evidence?.extraction?.source ?? {};
  const denominator = evidence?.declared_denominator ?? {};
  const resolvability = evidence?.resolvability ?? {};
  const declaredIdentities = Array.isArray(resolvability?.identities) ? resolvability.identities : [];
  const unadmitted = Array.isArray(evidence?.unadmitted_classes) ? evidence.unadmitted_classes : [];

  // (1) record identity and artifact pin. The count is only meaningful once we
  // know which artifact and which record were counted.
  if (artifact === null || typeof artifact !== "object") {
    add("artifact_count_mismatch", "the artifact is missing or unparsable");
  }
  if (evidence === null || typeof evidence !== "object") {
    add("artifact_count_mismatch", "the evidence record is missing or unparsable");
  }
  if (evidence?.schema !== EVIDENCE_SCHEMA) add("artifact_count_mismatch", `evidence schema=${evidence?.schema}`);
  if (evidence?.schema_version !== 1) add("artifact_count_mismatch", `evidence schema_version=${evidence?.schema_version}`);
  if (evidence?.kind !== "m209-s02-extraction-evidence") add("artifact_count_mismatch", `kind=${evidence?.kind}`);
  if (evidence?.milestone !== "M209-2yg6ix") add("artifact_count_mismatch", `milestone=${evidence?.milestone}`);
  if (evidence?.slice !== "S02") add("artifact_count_mismatch", `slice=${evidence?.slice}`);
  if (evidence?.task !== "T01") add("artifact_count_mismatch", `task=${evidence?.task}`);
  if (artifact?.schema !== ARTIFACT_SCHEMA) add("artifact_count_mismatch", `artifact schema=${artifact?.schema}`);
  if (artifact?.schema_version !== 1) add("artifact_count_mismatch", `artifact schema_version=${artifact?.schema_version}`);
  if (sourceBinding?.kind !== "file") add("artifact_count_mismatch", `source_binding.kind=${sourceBinding?.kind}`);
  if (sourceBinding?.payload_ref !== ARTIFACT_PAYLOAD_REF) {
    add("artifact_count_mismatch", `payload_ref=${sourceBinding?.payload_ref}`);
  }
  if (evidenceArtifact?.path !== ARTIFACT) add("artifact_count_mismatch", `evidence artifact path=${evidenceArtifact?.path}`);
  if (evidenceArtifact?.schema !== ARTIFACT_SCHEMA) {
    add("artifact_count_mismatch", `evidence artifact schema=${evidenceArtifact?.schema}`);
  }
  if (evidenceArtifact?.sha256 !== sha256(ARTIFACT)) {
    add("artifact_count_mismatch", `artifact sha256 pin ${evidenceArtifact?.sha256} != ${sha256(ARTIFACT)}`);
  }
  if (evidenceArtifact?.bytes !== repoBytes(ARTIFACT)) {
    add("artifact_count_mismatch", `artifact bytes pin ${evidenceArtifact?.bytes} != ${repoBytes(ARTIFACT)}`);
  }

  // (2) counts internal consistency: extracted == unique == rows == sum(ladder)
  // == the declared denominator total, and the duplicate row count agrees.
  const byLevelSum = ALL_LEVELS.reduce((sum, level) => sum + (byLevel[level] ?? 0), 0);
  const nestedRows = candidates.filter((row) => row?.path != null).length;
  if (counts?.extracted !== DENOMINATOR_TOTAL) add("artifact_count_mismatch", `extracted=${counts?.extracted}`);
  if (counts?.unique !== counts?.extracted) add("artifact_count_mismatch", `unique=${counts?.unique} extracted=${counts?.extracted}`);
  if (candidates.length !== counts?.extracted) {
    add("artifact_count_mismatch", `candidate rows=${candidates.length} extracted=${counts?.extracted}`);
  }
  if (counts?.duplicate !== duplicateRows.length) {
    add("artifact_count_mismatch", `duplicate=${counts?.duplicate} rows=${duplicateRows.length}`);
  }
  if (byLevelSum !== counts?.extracted) {
    add("artifact_count_mismatch", `ladder sum=${byLevelSum} extracted=${counts?.extracted}`);
  }
  if (counts?.nested !== nestedRows) add("artifact_count_mismatch", `nested=${counts?.nested} rows=${nestedRows}`);

  // (3) declared by-level decomposition, of both the artifact and the remainder.
  if (!sameSet(Object.keys(byLevel), ALL_LEVELS)) {
    add("artifact_by_level_mismatch", `ladder keys=${Object.keys(byLevel).join("|")}`);
  }
  for (const level of ALL_LEVELS) {
    const expected = DECLARED_BY_LEVEL[level] ?? 0;
    if (byLevel[level] !== expected) {
      add("artifact_by_level_mismatch", `${level}=${byLevel[level]} expected ${expected}`);
    }
  }
  if (!sameByLevel(denominator?.by_level, DECLARED_BY_LEVEL)) {
    add("artifact_by_level_mismatch", `declared by_level=${JSON.stringify(denominator?.by_level)}`);
  }
  if (!sameSet(unadmitted.map((entry) => entry?.level), UNADMITTED_LEVELS)) {
    add("artifact_by_level_mismatch", `unadmitted levels=${unadmitted.map((entry) => entry?.level).join("|")}`);
  }
  for (const entry of unadmitted) {
    const level = entry?.level;
    if (entry?.count !== DECLARED_BY_LEVEL[level]) {
      add("artifact_by_level_mismatch", `${level} unadmitted=${entry?.count} expected ${DECLARED_BY_LEVEL[level]}`);
    }
    if (entry?.reason_code !== NESTED_REASON) {
      add("artifact_by_level_mismatch", `${level} reason_code=${entry?.reason_code}`);
    }
    for (const decision of ["D192", "D426"]) {
      if (!Array.isArray(entry?.decision_refs) || !entry.decision_refs.includes(decision)) {
        add("artifact_by_level_mismatch", `${level} missing decision ref ${decision}`);
      }
    }
  }
  const unadmittedTotal = unadmitted.reduce(
    (sum, entry) => sum + (Number.isFinite(entry?.count) ? entry.count : 0),
    0,
  );
  if (unadmittedTotal !== UNADMITTED_TOTAL) {
    add("artifact_by_level_mismatch", `unadmitted total=${unadmittedTotal} expected ${UNADMITTED_TOTAL}`);
  }

  // (4) the denominator declaration itself.
  if (!nonEmpty(denominator?.definition)) add("artifact_denominator_missing", "definition is empty");
  if (!nonEmpty(denominator?.denominator_basis)) add("artifact_denominator_missing", "denominator_basis is empty");
  if (denominator?.decision_ref !== "D547") add("artifact_denominator_missing", `decision_ref=${denominator?.decision_ref}`);
  if (denominator?.denominator_total !== DENOMINATOR_TOTAL) {
    add("artifact_denominator_missing", `denominator_total=${denominator?.denominator_total}`);
  }
  if (denominator?.denominator_total !== counts?.extracted) {
    add("artifact_denominator_missing", `denominator_total=${denominator?.denominator_total} extracted=${counts?.extracted}`);
  }
  if (!nonEmpty(denominator?.declared_source_path)) {
    add("artifact_denominator_missing", "declared_source_path is empty");
  }

  // (5) a zero denominator is not a measurement (D547).
  const denominatorSum = Object.values(denominator?.by_level ?? {}).reduce(
    (sum, value) => sum + (Number.isFinite(value) ? value : 0),
    0,
  );
  if (!(Number(denominator?.denominator_total) > 0) || denominatorSum === 0) {
    add("denominator_zero_treated_as_measurement", `total=${denominator?.denominator_total} sum=${denominatorSum}`);
  }
  if (denominator?.zero_denominator_is_not_a_measurement !== true) {
    add("denominator_zero_treated_as_measurement", "zero_denominator_is_not_a_measurement is not true");
  }

  // (6) source binding: shape, trackability, digests, cleanliness.
  const sourceDeclarations = [
    ["artifact.source_binding.path", sourceBinding?.path],
    ["evidence.extraction.source.path", evidenceSource?.path],
    ["declared_denominator.declared_source_path", denominator?.declared_source_path],
  ];
  for (const [label, declared] of sourceDeclarations) {
    if (!nonEmpty(declared)) {
      add("source_untracked", `${label} is missing`);
      continue;
    }
    if (isIgnoredPath(declared)) {
      add("ignored_path_as_source", `${label}=${declared}`);
      continue;
    }
    if (isAbsolutePath(declared)) {
      add("absolute_path_as_source", `${label}=${declared}`);
      continue;
    }
    if (declared !== SOURCE || !trackedSource || !isTracked(declared)) {
      add("source_untracked", `${label}=${declared}`);
    }
  }
  if (evidenceSource?.tracked !== true) add("source_untracked", `tracked=${evidenceSource?.tracked}`);
  if (sourceDelta !== "") add("source_modified", sourceDelta);

  const liveSourceDigest = fnv1a64(sourceBytes);
  const liveSourceSha = sha256Buffer(sourceBytes);
  if (!FNV_PATTERN.test(String(sourceBinding?.source_digest ?? ""))) {
    add("source_digest_mismatch", `source_digest=${sourceBinding?.source_digest}`);
  }
  if (sourceBinding?.source_digest !== liveSourceDigest) {
    add("source_digest_mismatch", `artifact digest=${sourceBinding?.source_digest} live=${liveSourceDigest}`);
  }
  if (evidenceSource?.digest !== liveSourceDigest) {
    add("source_digest_mismatch", `evidence digest=${evidenceSource?.digest} live=${liveSourceDigest}`);
  }
  if (evidenceArtifact?.source_digest !== liveSourceDigest) {
    add("source_digest_mismatch", `evidence artifact source_digest=${evidenceArtifact?.source_digest}`);
  }
  if (evidenceSource?.sha256 !== liveSourceSha) {
    add("source_digest_mismatch", `evidence sha256=${evidenceSource?.sha256} live=${liveSourceSha}`);
  }
  if (evidenceSource?.bytes !== sourceBytes.length) {
    add("source_digest_mismatch", `evidence bytes=${evidenceSource?.bytes} live=${sourceBytes.length}`);
  }

  // (7) the identity digest is re-derived from the canonical stream, never trusted.
  const liveIdentityDigest = fnv1a64(Buffer.from(identityStream(artifact), "utf8"));
  if (!FNV_PATTERN.test(String(artifact?.identity_digest ?? ""))) {
    add("identity_digest_mismatch", `identity_digest=${artifact?.identity_digest}`);
  }
  if (artifact?.identity_digest !== liveIdentityDigest) {
    add("identity_digest_mismatch", `artifact=${artifact?.identity_digest} live=${liveIdentityDigest}`);
  }
  if (evidenceArtifact?.identity_digest !== artifact?.identity_digest) {
    add("identity_digest_mismatch", `evidence=${evidenceArtifact?.identity_digest} artifact=${artifact?.identity_digest}`);
  }
  if (artifact?.identity_digest === sourceBinding?.source_digest) {
    add("identity_digest_mismatch", "identity digest collapsed into the source digest");
  }

  // (8) resolvability, recomputed live against the registry needle.
  if (resolvability?.needle !== NEEDLE) add("unresolved_identity", `needle=${resolvability?.needle}`);
  if (resolvability?.registry_path !== REGISTRY) add("unresolved_identity", `registry_path=${resolvability?.registry_path}`);
  if (resolvability?.registry_sha256 !== sha256(REGISTRY)) {
    add("unresolved_identity", `registry_sha256=${resolvability?.registry_sha256} != ${sha256(REGISTRY)}`);
  }
  const bindings = parseRegistryBindings(registryText, NEEDLE);
  const bindingByKey = new Map(bindings.map((row) => [identityKey(row.level, row.number), row.cc]));
  const topLevelRows = candidates.filter(
    (row) => row?.catalog_token === "glava" || row?.catalog_token === "statya",
  );
  const liveResolved = [];
  for (const row of topLevelRows) {
    if (row?.key_path !== row?.number) {
      add("unresolved_identity", `key_path=${row?.key_path} number=${row?.number}`);
      continue;
    }
    const cc = bindingByKey.get(identityKey(row.catalog_token, row.number));
    if (cc === undefined) {
      add("unresolved_identity", `${row.catalog_token} ${row.number} has no registry binding`);
      continue;
    }
    liveResolved.push({ level: row.catalog_token, number: row.number, cc });
  }
  const liveResolvedByLevel = { glava: 0, statya: 0 };
  for (const row of liveResolved) liveResolvedByLevel[row.level] += 1;
  const liveResolvedKeys = new Set(liveResolved.map((row) => identityKey(row.level, row.number)));

  if (liveResolved.length !== RESOLVABLE_TOTAL) {
    add("unresolved_identity", `live resolvable=${liveResolved.length} expected ${RESOLVABLE_TOTAL}`);
  }
  if (!sameByLevel(liveResolvedByLevel, RESOLVABLE_BY_LEVEL)) {
    add("unresolved_identity", `live by level=${JSON.stringify(liveResolvedByLevel)}`);
  }
  if (resolvability?.matched !== liveResolved.length) {
    add("unresolved_identity", `declared matched=${resolvability?.matched} live=${liveResolved.length}`);
  }
  if (!sameByLevel(resolvability?.matched_by_level, liveResolvedByLevel)) {
    add("unresolved_identity", `declared matched_by_level=${JSON.stringify(resolvability?.matched_by_level)}`);
  }
  if (resolvability?.unmatched !== 0) add("unresolved_identity", `unmatched=${resolvability?.unmatched}`);

  const registryOnly = bindings.filter((row) => !liveResolvedKeys.has(identityKey(row.level, row.number)));
  if (registryOnly.length !== 0) {
    add("registry_only_identity", `${registryOnly.length} registry rows have no extracted identity`);
  }
  if (resolvability?.registry_only !== 0 || resolvability?.registry_only !== registryOnly.length) {
    add("registry_only_identity", `declared registry_only=${resolvability?.registry_only}`);
  }

  const declaredKeys = new Set();
  for (const entry of declaredIdentities) {
    const level = entry?.level;
    const number = entry?.number;
    const key = identityKey(level, number);
    const cc = bindingByKey.get(key);
    if (entry?.key_path !== number) add("unresolved_identity", `declared key_path=${entry?.key_path} number=${number}`);
    if (!liveResolvedKeys.has(key)) {
      add("registry_only_identity", `declared ${level} ${number} is not a live resolved identity`);
    }
    if (cc === undefined) {
      add("unresolved_identity", `declared ${level} ${number} has no registry binding`);
    } else if (entry?.cc !== cc) {
      add("cc_minted", `declared cc=${entry?.cc} registry cc=${cc}`);
    }
    if (declaredKeys.has(key)) add("cc_minted", `identity ${level} ${number} declared twice`);
    declaredKeys.add(key);
    if (level === "punkt") add("punkt_admitted_without_decision", `punkt ${number} is declared resolvable`);
  }
  if (declaredIdentities.length !== liveResolved.length) {
    add("unresolved_identity", `declared identities=${declaredIdentities.length} live=${liveResolved.length}`);
  }
  const liveTriples = liveResolved.map((row) => `${row.level}|${row.number}|${row.cc}`).sort().join(",");
  const declaredTriples = declaredIdentities
    .map((entry) => `${entry?.level}|${entry?.number}|${entry?.cc}`)
    .sort()
    .join(",");
  if (liveTriples !== declaredTriples) {
    add("unresolved_identity", "declared identity set drifted from the live resolved identity set");
  }
  const declaredCcs = declaredIdentities.map((entry) => entry?.cc);
  if (new Set(declaredCcs).size !== declaredCcs.length) add("cc_minted", "a ComponentConcept is reused");

  // (9) punkt stays blocked at 0 of 997 (D540).
  if (evidence?.punkt_admitted?.admitted !== 0) {
    add("punkt_admitted_without_decision", `admitted=${evidence?.punkt_admitted?.admitted}`);
  }
  if (evidence?.punkt_admitted?.of !== DECLARED_BY_LEVEL.punkt) {
    add("punkt_admitted_without_decision", `of=${evidence?.punkt_admitted?.of}`);
  }
  const punktRefs = evidence?.punkt_admitted?.decision_refs;
  for (const decision of PUNKT_DECISION_REFS) {
    if (!Array.isArray(punktRefs) || !punktRefs.includes(decision)) {
      add("punkt_admitted_without_decision", `missing decision ref ${decision}`);
    }
  }

  // (10) the artifact stays count-only: no raw legal text, no minted identity.
  const rawText = `${artifactText}\n${JSON.stringify(artifact ?? null)}`;
  if (artifact?.count_only !== true) add("raw_legal_text_in_artifact", `count_only=${artifact?.count_only}`);
  if (artifact?.ascii_only !== true) add("raw_legal_text_in_artifact", `ascii_only=${artifact?.ascii_only}`);
  if (!/^[\x00-\x7F]*$/.test(rawText)) add("raw_legal_text_in_artifact", "artifact text is not ASCII-only");
  for (const marker of RAW_LEGAL_TEXT_MARKERS) {
    if (rawText.includes(marker)) add("raw_legal_text_in_artifact", `raw legal text marker ${marker}`);
  }
  if (rawText.includes("cc:")) add("cc_minted", "the artifact text carries a ComponentConcept identifier");

  // (11) the frozen M202 generation must stay byte-stable.
  if (frozenDelta !== "") add("frozen_m202_artifact_modified", frozenDelta);
  for (const frozen of FROZEN_M202_INPUTS) {
    if (!repoExists(frozen) || !isTracked(frozen)) {
      add("frozen_m202_artifact_modified", `${frozen} is missing or untracked`);
    }
  }

  // (12) R035 stays active and nothing is promoted (D430).
  if (evidence?.requirement_id !== "R035") add("r035_promoted", `requirement_id=${evidence?.requirement_id}`);
  if (evidence?.requirement_disposition !== "active") {
    add("r035_promoted", `requirement_disposition=${evidence?.requirement_disposition}`);
  }
  if (evidence?.requirement_disposition_decision !== "D430") {
    add("r035_promoted", `requirement_disposition_decision=${evidence?.requirement_disposition_decision}`);
  }
  if (evidence?.authoritative !== false) add("r035_promoted", `evidence authoritative=${evidence?.authoritative}`);
  if (artifact?.authoritative !== false) add("r035_promoted", `artifact authoritative=${artifact?.authoritative}`);
  if (artifact?.lifecycle !== ARTIFACT_LIFECYCLE) add("r035_promoted", `artifact lifecycle=${artifact?.lifecycle}`);
  if (evidence?.lifecycle !== EVIDENCE_LIFECYCLE) add("r035_promoted", `evidence lifecycle=${evidence?.lifecycle}`);
  if (count(m202Text, '"gate_verdict": "unsatisfied"') !== 7) {
    add("r035_promoted", "the frozen M202 snapshot no longer carries seven unsatisfied gate verdicts");
  }
  if (typeof m202Text !== "string" || count(m202Text, '"gate_verdict": "satisfied"') !== 0) {
    add("r035_promoted", "the frozen M202 snapshot shows a promoted gate verdict");
  }
  if (typeof m202Text !== "string" || count(m202Text, '"validated"') !== 0) {
    add("r035_promoted", "the frozen M202 snapshot carries a validated value");
  }

  // (13) the record bounds its own claims.
  const nonClaims = Array.isArray(evidence?.non_claims) ? evidence.non_claims.map(String) : [];
  if (nonClaims.length === 0) add("non_claims_missing", "the evidence record carries no non-claims");
  const joinedClaims = nonClaims.join("\n").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    if (!joinedClaims.includes(fragment)) add("non_claims_missing", `missing fragment: ${fragment}`);
  }

  return { ok: errors.length === 0, errors };
}

function codesFor(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const liveArtifactText = readRepo(ARTIFACT);
const liveEvidenceText = readRepo(EVIDENCE);
const liveArtifact = JSON.parse(liveArtifactText);
const liveEvidence = JSON.parse(liveEvidenceText);
const liveSourceBytes = readRepoBuffer(SOURCE);
const liveRegistryText = readRepo(REGISTRY);
const liveM202Text = readRepo(M202_S04);

function cloneArtifact() {
  return JSON.parse(liveArtifactText);
}

function cloneEvidence() {
  return JSON.parse(liveEvidenceText);
}

function fixtureArtifact(mutate) {
  const next = cloneArtifact();
  const returned = mutate(next) ?? next;
  assert.notEqual(
    JSON.stringify(returned),
    JSON.stringify(liveArtifact),
    "artifact mutation did not modify the artifact",
  );
  return returned;
}

function fixtureEvidence(mutate) {
  const next = cloneEvidence();
  const returned = mutate(next) ?? next;
  assert.notEqual(
    JSON.stringify(returned),
    JSON.stringify(liveEvidence),
    "evidence mutation did not modify the evidence record",
  );
  return returned;
}

function expectCode(result, expected) {
  assert.ok(
    codesFor(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codesFor(result))}`,
  );
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("the live artifact and evidence record validate end to end", () => {
  const result = validateExtraction(liveArtifact, liveEvidence);
  assert.deepEqual(result.errors, [], `extraction errors: ${JSON.stringify(result.errors, null, 2)}`);
  assert.equal(result.ok, true);
});

test("the artifact is the pinned artifact and its counts are internally consistent", () => {
  assert.equal(liveArtifact.schema, ARTIFACT_SCHEMA);
  assert.equal(liveArtifact.schema_version, 1);
  assert.equal(liveArtifact.lifecycle, ARTIFACT_LIFECYCLE);
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.count_only, true);
  assert.equal(liveArtifact.ascii_only, true);
  assert.equal(liveEvidence.extraction.artifact.path, ARTIFACT);
  assert.equal(liveEvidence.extraction.artifact.sha256, sha256(ARTIFACT));
  assert.equal(liveEvidence.extraction.artifact.bytes, repoBytes(ARTIFACT));
  assert.equal(liveArtifact.source_binding.path, SOURCE);
  assert.equal(liveArtifact.source_binding.payload_ref, ARTIFACT_PAYLOAD_REF);

  const counts = liveArtifact.counts;
  assert.equal(counts.extracted, DENOMINATOR_TOTAL);
  assert.equal(counts.unique, counts.extracted);
  assert.equal(liveArtifact.candidates.length, counts.extracted);
  assert.equal(counts.duplicate, 0);
  assert.equal(liveArtifact.diagnostics.duplicate_key_count, 0);
  assert.equal(liveArtifact.diagnostics.duplicate_keys.length, 0);
  assert.equal(
    ALL_LEVELS.reduce((sum, level) => sum + (counts.by_level[level] ?? 0), 0),
    counts.extracted,
    "the level ladder must sum to the extracted total",
  );
  assert.equal(
    counts.nested,
    liveArtifact.candidates.filter((row) => row.path != null).length,
    "nested must count the rows carrying a path",
  );
});

test("the declared denominator is bound to one tracked source and decomposes exactly", () => {
  const denominator = liveEvidence.declared_denominator;
  assert.equal(denominator.decision_ref, "D547");
  assert.equal(denominator.declared_source_path, SOURCE);
  assert.equal(denominator.denominator_total, DENOMINATOR_TOTAL);
  assert.equal(denominator.zero_denominator_is_not_a_measurement, true);
  assert.ok(denominator.definition.trim().length > 0);
  assert.ok(denominator.denominator_basis.trim().length > 0);
  assert.deepEqual(denominator.by_level, { ...DECLARED_BY_LEVEL });
  assert.equal(
    Object.values(denominator.by_level).reduce((sum, value) => sum + value, 0),
    denominator.denominator_total,
  );
  assert.deepEqual(
    Object.fromEntries(Object.keys(DECLARED_BY_LEVEL).map((level) => [level, liveArtifact.counts.by_level[level]])),
    { ...DECLARED_BY_LEVEL },
    "the artifact ladder must reproduce the declared denominator",
  );

  const unadmitted = liveEvidence.unadmitted_classes;
  assert.deepEqual(unadmitted.map((entry) => entry.level).sort(), [...UNADMITTED_LEVELS].sort());
  for (const entry of unadmitted) {
    assert.equal(entry.count, DECLARED_BY_LEVEL[entry.level]);
    assert.equal(entry.reason_code, NESTED_REASON);
    assert.ok(entry.decision_refs.includes("D192"));
    assert.ok(entry.decision_refs.includes("D426"));
  }
  assert.equal(
    unadmitted.reduce((sum, entry) => sum + entry.count, 0),
    UNADMITTED_TOTAL,
    "102 admitted + 1799 unadmitted must exhaust the 1901 denominator",
  );
  assert.equal(RESOLVABLE_TOTAL + UNADMITTED_TOTAL, DENOMINATOR_TOTAL);
});

test("102 glava/statya identities resolve 1:1 into the registry needle", () => {
  const bindings = parseRegistryBindings(liveRegistryText, NEEDLE);
  assert.equal(bindings.length, RESOLVABLE_TOTAL);
  assert.deepEqual(
    bindings.reduce((acc, row) => ({ ...acc, [row.level]: (acc[row.level] ?? 0) + 1 }), {}),
    { ...RESOLVABLE_BY_LEVEL },
  );

  const topLevel = liveArtifact.candidates.filter(
    (row) => row.catalog_token === "glava" || row.catalog_token === "statya",
  );
  assert.equal(topLevel.length, RESOLVABLE_TOTAL);
  for (const row of topLevel) {
    assert.equal(row.key_path, row.number, `${row.catalog_token} ${row.number}: key_path must be the number`);
  }

  const byKey = new Map(bindings.map((row) => [identityKey(row.level, row.number), row.cc]));
  const resolved = topLevel.map((row) => ({
    level: row.catalog_token,
    number: row.number,
    cc: byKey.get(identityKey(row.catalog_token, row.number)),
  }));
  assert.equal(resolved.filter((row) => row.cc === undefined).length, 0, "0 unmatched identities");
  const resolvedKeys = new Set(resolved.map((row) => identityKey(row.level, row.number)));
  assert.equal(
    bindings.filter((row) => !resolvedKeys.has(identityKey(row.level, row.number))).length,
    0,
    "0 registry-only identities",
  );
  assert.equal(liveEvidence.resolvability.matched, RESOLVABLE_TOTAL);
  assert.equal(liveEvidence.resolvability.unmatched, 0);
  assert.equal(liveEvidence.resolvability.registry_only, 0);
  assert.equal(liveEvidence.resolvability.identities.length, RESOLVABLE_TOTAL);
  // the declared identity set is exactly the live resolved identity set
  assert.equal(
    liveEvidence.resolvability.identities
      .map((entry) => `${entry.level}|${entry.number}|${entry.cc}`)
      .sort()
      .join(","),
    resolved.map((row) => `${row.level}|${row.number}|${row.cc}`).sort().join(","),
  );
});

test("source and identity digests are live re-derivations, not prose", () => {
  const liveSourceDigest = fnv1a64(liveSourceBytes);
  assert.equal(liveSourceDigest, liveArtifact.source_binding.source_digest);
  assert.equal(liveSourceDigest, liveEvidence.extraction.source.digest);
  assert.equal(sha256Buffer(liveSourceBytes), liveEvidence.extraction.source.sha256);
  assert.equal(liveEvidence.extraction.source.bytes, liveSourceBytes.length);
  assert.equal(liveEvidence.extraction.source.tracked, true);

  const liveIdentityDigest = fnv1a64(Buffer.from(identityStream(liveArtifact), "utf8"));
  assert.equal(liveIdentityDigest, liveArtifact.identity_digest);
  assert.equal(liveEvidence.extraction.artifact.identity_digest, liveArtifact.identity_digest);
  assert.notEqual(liveArtifact.identity_digest, liveArtifact.source_binding.source_digest);
  assert.ok(FNV_PATTERN.test(liveArtifact.identity_digest));
});

test("punkt stays blocked at 0 of 997 and the record bounds its own claims", () => {
  assert.equal(liveEvidence.punkt_admitted.admitted, 0);
  assert.equal(liveEvidence.punkt_admitted.of, DECLARED_BY_LEVEL.punkt);
  for (const decision of PUNKT_DECISION_REFS) {
    assert.ok(liveEvidence.punkt_admitted.decision_refs.includes(decision), `missing ${decision}`);
  }
  assert.equal(
    liveEvidence.resolvability.identities.filter((entry) => entry.level === "punkt").length,
    0,
    "no punkt candidate may be declared resolvable",
  );
  const claims = liveEvidence.non_claims.join("\n").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(claims.includes(fragment), `non-claims must include: ${fragment}`);
  }
});

test("the tracked source and the frozen M202 inputs are clean and tracked", () => {
  assert.ok(repoExists(SOURCE), `${SOURCE} must exist`);
  assert.ok(isTracked(SOURCE), `${SOURCE} must stay tracked`);
  assert.equal(worktreeDelta([SOURCE]), "", "the tracked source must carry no worktree delta");
  assert.equal(worktreeDelta(FROZEN_M202_INPUTS), "", "the frozen M202 inputs must carry no worktree delta");
  for (const frozen of FROZEN_M202_INPUTS) {
    assert.ok(repoExists(frozen), `${frozen} must exist`);
    assert.ok(isTracked(frozen), `${frozen} must stay tracked`);
  }
  // The T01 artifacts are authored here and committed by closeout, so they must
  // exist and be repository-relative even though git cannot see them yet.
  for (const authored of [ARTIFACT, EVIDENCE, CONTRACT_PATH]) {
    assert.ok(repoExists(authored), `${authored} must exist`);
    assert.ok(!authored.startsWith("/"), `${authored} must be repository-relative`);
    assert.ok(!isIgnoredPath(authored), `${authored} must not be an ignored path`);
  }
});

test("the record never promotes R035 or a gate", () => {
  assert.equal(liveEvidence.requirement_id, "R035");
  assert.equal(liveEvidence.requirement_disposition, "active");
  assert.equal(liveEvidence.requirement_disposition_decision, "D430");
  assert.equal(liveEvidence.authoritative, false);
  assert.equal(liveEvidence.lifecycle, EVIDENCE_LIFECYCLE);
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.lifecycle, ARTIFACT_LIFECYCLE);
  assert.equal(count(liveM202Text, '"gate_verdict": "unsatisfied"'), 7);
  assert.equal(count(liveM202Text, '"gate_verdict": "satisfied"'), 0);
  assert.equal(count(liveM202Text, '"validated"'), 0);
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
    SOURCE,
    ARTIFACT,
    EVIDENCE,
    REGISTRY,
    CONTRACT_PATH,
    ...FROZEN_M202_INPUTS,
    ...ALL_LEVELS,
  ]) {
    assert.ok(!entry.startsWith("/"), `${entry} must be repository-relative`);
    assert.ok(!isIgnoredPath(entry), `${entry} must not be an ignored path`);
  }
  assert.ok(
    !/readRepoBuffer?\(\s*"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readRepoBuffer?\(\s*"\//.test(source), "the contract must not read an absolute path");
});

test("the contract uses only the two allowed git subprocesses and writes nothing", () => {
  const source = readRepo(CONTRACT_PATH);
  assert.ok(source.includes('"ls-files", "--error-unmatch"'), "tracked-file proof is required");
  assert.ok(source.includes('"status", "--porcelain"'), "clean-worktree proof is required");
  for (const executable of ["car" + "go", "cu" + "rl", "wg" + "et", "n" + "pm", "n" + "px", "kubectl", "python3"]) {
    const launch = new RegExp(
      "(?:execFileSync|spawnSync|execSync|spawn)\\(\\s*[\"'`]" + executable + "\\b",
    );
    assert.ok(!launch.test(source), `${executable} must not be launched by this contract`);
  }
  // The writer names are split so this guard cannot match its own literal list.
  for (const writer of [
    "write" + "FileSync",
    "append" + "FileSync",
    "create" + "WriteStream",
    "mkdir" + "Sync",
    "unlink" + "Sync",
    "rm" + "Sync",
  ]) {
    assert.ok(!source.includes(writer), `${writer} must not appear: the contract never writes`);
  }
});

test("the contract never emits the slice verify marker", () => {
  const source = readRepo(CONTRACT_PATH);
  const verifyMarker = ["M209_S02", "VERIFY_OK"].join("_");
  const emitter = new RegExp("console\\.log\\(\\s*[\"'`]" + verifyMarker);
  assert.ok(!emitter.test(source), `${verifyMarker} must be unreachable by construction`);
});

// ---------------------------------------------------------------------------
// fail-closed negatives (each code fires against a mutated artifact/evidence)
// ---------------------------------------------------------------------------

test("negative: artifact record identity, pin and count drift", () => {
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.schema = "law-nexus/other/v9"; })),
    "artifact_count_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.extraction.artifact.sha256 = "0".repeat(64); })),
    "artifact_count_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.extraction.artifact.bytes = 1; })),
    "artifact_count_mismatch",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.counts.extracted = DENOMINATOR_TOTAL - 1; }), liveEvidence),
    "artifact_count_mismatch",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.counts.unique = DENOMINATOR_TOTAL - 1; }), liveEvidence),
    "artifact_count_mismatch",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.counts.nested = 0; }), liveEvidence),
    "artifact_count_mismatch",
  );
});

test("negative: by-level decomposition and unadmitted accounting drift", () => {
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.counts.by_level.statya = DECLARED_BY_LEVEL.statya - 1; }),
      liveEvidence,
    ),
    "artifact_by_level_mismatch",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { delete a.counts.by_level.podpunkt; }),
      liveEvidence,
    ),
    "artifact_by_level_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.declared_denominator.by_level.punkt = 1; })),
    "artifact_by_level_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.unadmitted_classes.pop(); })),
    "artifact_by_level_mismatch",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.unadmitted_classes[0].reason_code = "unknown"; }),
    ),
    "artifact_by_level_mismatch",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.unadmitted_classes[0].decision_refs = []; }),
    ),
    "artifact_by_level_mismatch",
  );
});

test("negative: the denominator declaration is missing or unbound", () => {
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { delete e.declared_denominator; })),
    "artifact_denominator_missing",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.declared_denominator.denominator_total = DENOMINATOR_TOTAL + 1; }),
    ),
    "artifact_denominator_missing",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.declared_denominator.definition = ""; })),
    "artifact_denominator_missing",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.declared_denominator.denominator_basis = ""; })),
    "artifact_denominator_missing",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.declared_denominator.decision_ref = "D000"; })),
    "artifact_denominator_missing",
  );
});

test("negative: a zero denominator is not a measurement", () => {
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => {
        e.declared_denominator.denominator_total = 0;
        e.declared_denominator.by_level = { glava: 0, statya: 0, chast: 0, punkt: 0, paragraph: 0 };
      }),
    ),
    "denominator_zero_treated_as_measurement",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.declared_denominator.zero_denominator_is_not_a_measurement = false; }),
    ),
    "denominator_zero_treated_as_measurement",
  );
});

test("negative: source digests and identity digest drift", () => {
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      sourceBytes: Buffer.concat([liveSourceBytes, Buffer.from("\n")]),
    }),
    "source_digest_mismatch",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.source_binding.source_digest = "fnv1a64:0000000000000000"; }),
      liveEvidence,
    ),
    "source_digest_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.extraction.source.digest = "not-a-digest"; })),
    "source_digest_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.extraction.source.sha256 = "0".repeat(64); })),
    "source_digest_mismatch",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.extraction.source.bytes = 1; })),
    "source_digest_mismatch",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.identity_digest = "fnv1a64:0000000000000000"; }),
      liveEvidence,
    ),
    "identity_digest_mismatch",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.candidates[0].number = "9999"; }),
      liveEvidence,
    ),
    "identity_digest_mismatch",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.identity_digest = a.source_binding.source_digest; }),
      liveEvidence,
    ),
    "identity_digest_mismatch",
  );
});

test("negative: the source is untracked, modified, ignored or absolute", () => {
  expectCode(validateExtraction(liveArtifact, liveEvidence, { trackedSource: false }), "source_untracked");
  expectCode(validateExtraction(liveArtifact, liveEvidence, { sourceDelta: " M " + SOURCE }), "source_modified");
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      sourceDelta: ' M law-source/consultant/other.xml',
    }),
    "source_modified",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.source_binding.path = ".gsd/sources/fz44.xml"; }),
      liveEvidence,
    ),
    "ignored_path_as_source",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.source_binding.path = "/tmp/fz44.xml"; }),
      liveEvidence,
    ),
    "absolute_path_as_source",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.source_binding.path = "../law-source/fz44.xml"; }),
      liveEvidence,
    ),
    "absolute_path_as_source",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.declared_denominator.declared_source_path = "law-source/consultant/other.xml"; }),
    ),
    "source_untracked",
  );
});

test("negative: identity resolution drift", () => {
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.candidates.find((c) => c.catalog_token === "statya").number = "9999"; }),
      liveEvidence,
    ),
    "unresolved_identity",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.candidates.find((c) => c.catalog_token === "glava").key_path = "glava-1"; }),
      liveEvidence,
    ),
    "unresolved_identity",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.resolvability.matched = 3; })),
    "unresolved_identity",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.resolvability.unmatched = 1; })),
    "unresolved_identity",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.resolvability.identities.pop(); })),
    "unresolved_identity",
  );
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      registryText: liveRegistryText.replace('path_needle: law_2013-04-05_44-fz, level: statya', "path_needle: other-needle, level: statya"),
    }),
    "unresolved_identity",
  );
});

test("negative: registry-only identities and minted ComponentConcepts", () => {
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      registryText: liveRegistryText.replace(
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\",",
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"99\",",
      ),
    }),
    "registry_only_identity",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.resolvability.registry_only = 1; })),
    "registry_only_identity",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.resolvability.identities.push({ key_path: "9999", level: "statya", number: "9999", cc: "cc:44-fz:statya-9999" }); }),
    ),
    "registry_only_identity",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.resolvability.identities[0].cc = "cc:44-fz:glava-99"; }),
    ),
    "cc_minted",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.resolvability.identities[1].cc = e.resolvability.identities[0].cc; }),
    ),
    "cc_minted",
  );
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      artifactText: liveArtifactText.replace('"count_only": true', '"count_only": true, "minted": "cc:44-fz:statya-9999"'),
    }),
    "cc_minted",
  );
});

test("negative: punkt admitted without its decision", () => {
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.punkt_admitted.admitted = 1; })),
    "punkt_admitted_without_decision",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.punkt_admitted.of = 1; })),
    "punkt_admitted_without_decision",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.punkt_admitted.decision_refs = []; })),
    "punkt_admitted_without_decision",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      fixtureEvidence((e) => { e.resolvability.identities[0] = { key_path: "1", level: "punkt", number: "1", cc: "cc:44-fz:punkt-1" }; }),
    ),
    "punkt_admitted_without_decision",
  );
});

test("negative: raw legal text or a non count-only artifact", () => {
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, {
      artifactText: liveArtifactText.replace('"count_only": true', '"count_only": true, "text": "Статья 44"'),
    }),
    "raw_legal_text_in_artifact",
  );
  expectCode(
    validateExtraction(
      fixtureArtifact((a) => { a.candidates[0].number = "Статья-1"; }),
      liveEvidence,
    ),
    "raw_legal_text_in_artifact",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.count_only = false; }), liveEvidence),
    "raw_legal_text_in_artifact",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.ascii_only = false; }), liveEvidence),
    "raw_legal_text_in_artifact",
  );
});

test("negative: frozen M202 inputs modified and R035 promoted", () => {
  expectCode(
    validateExtraction(liveArtifact, liveEvidence, { frozenDelta: " M " + M202_S02 }),
    "frozen_m202_artifact_modified",
  );
  expectCode(
    validateExtraction(
      liveArtifact,
      liveEvidence,
      { m202Text: liveM202Text.replace('"gate_verdict": "unsatisfied"', '"gate_verdict": "satisfied"') },
    ),
    "r035_promoted",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.requirement_disposition = "validated"; })),
    "r035_promoted",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.requirement_disposition_decision = "D000"; })),
    "r035_promoted",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.authoritative = true; })),
    "r035_promoted",
  );
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.lifecycle = "[certified]"; })),
    "r035_promoted",
  );
  expectCode(
    validateExtraction(fixtureArtifact((a) => { a.lifecycle = "[certified]"; }), liveEvidence),
    "r035_promoted",
  );
});

test("negative: the record carries no non-claims", () => {
  expectCode(validateExtraction(liveArtifact, fixtureEvidence((e) => { e.non_claims = []; })), "non_claims_missing");
  expectCode(
    validateExtraction(liveArtifact, fixtureEvidence((e) => { e.non_claims = ["This proves R035."]; })),
    "non_claims_missing",
  );
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code. The test below asserts
// that each mutation actually makes its code fire and actually makes the record
// fail closed, so a code can never be documented without being reachable, and can
// never be reachable without being documented.
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "artifact_count_mismatch",
    mutate: (a, e) => { a.counts.extracted = DENOMINATOR_TOTAL - 1; },
  },
  {
    code: "artifact_by_level_mismatch",
    mutate: (a, e) => { a.counts.by_level.chast = DECLARED_BY_LEVEL.chast - 1; },
  },
  {
    code: "artifact_denominator_missing",
    mutate: (a, e) => { delete e.declared_denominator; },
  },
  {
    code: "denominator_zero_treated_as_measurement",
    mutate: (a, e) => {
      e.declared_denominator.denominator_total = 0;
      e.declared_denominator.by_level = { glava: 0, statya: 0, chast: 0, punkt: 0, paragraph: 0 };
    },
  },
  {
    code: "source_digest_mismatch",
    mutate: (a, e) => { a.source_binding.source_digest = "fnv1a64:0000000000000000"; },
  },
  {
    code: "identity_digest_mismatch",
    mutate: (a, e) => { a.identity_digest = "fnv1a64:0000000000000000"; },
  },
  {
    code: "source_untracked",
    mutate: (a, e) => { e.extraction.source.tracked = false; },
  },
  {
    code: "source_modified",
    sources: { sourceDelta: " M " + SOURCE },
  },
  {
    code: "unresolved_identity",
    mutate: (a, e) => { e.resolvability.matched = RESOLVABLE_TOTAL - 1; },
  },
  {
    code: "registry_only_identity",
    mutate: (a, e) => { e.resolvability.registry_only = 1; },
  },
  {
    code: "punkt_admitted_without_decision",
    mutate: (a, e) => { e.punkt_admitted.admitted = 1; },
  },
  {
    code: "cc_minted",
    mutate: (a, e) => { e.resolvability.identities[0].cc = "cc:44-fz:glava-99"; },
  },
  {
    code: "ignored_path_as_source",
    mutate: (a, e) => { a.source_binding.path = ".gsd/sources/fz44.xml"; },
  },
  {
    code: "absolute_path_as_source",
    mutate: (a, e) => { a.source_binding.path = "/tmp/fz44.xml"; },
  },
  {
    code: "raw_legal_text_in_artifact",
    mutate: (a, e) => { a.candidates[0].number = "Статья-1"; },
  },
  {
    code: "frozen_m202_artifact_modified",
    sources: { frozenDelta: " M " + M202_S02 },
  },
  {
    code: "r035_promoted",
    mutate: (a, e) => { e.requirement_disposition = "validated"; },
  },
  {
    code: "non_claims_missing",
    mutate: (a, e) => { e.non_claims = []; },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const artifact = cloneArtifact();
    const evidence = cloneEvidence();
    if (entry.mutate) entry.mutate(artifact, evidence);
    const result = validateExtraction(artifact, evidence, entry.sources ?? {});
    assert.ok(
      codesFor(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codesFor(result))}`,
    );
    assert.equal(result.ok, false, `${entry.code} must make the record fail closed`);
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
// markers (emitted only after the extraction contract holds)
// ---------------------------------------------------------------------------

test("M209 S02 extraction markers", () => {
  const result = validateExtraction(liveArtifact, liveEvidence);
  assert.deepEqual(result.errors, [], `extraction errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S02_EXTRACTION_OK");
  console.log("M209_S02_DENOMINATOR_OK");
  console.log("M209_S02_RESOLUTION_OK");
  console.log(`candidates_total=${liveArtifact.counts.extracted}`);
  console.log(`resolvable=${liveEvidence.resolvability.matched}`);
});
