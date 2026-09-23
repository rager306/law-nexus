// M209/S02 admission + regeneration contract (T03).
//
// Offline and fail-closed. The claim under test is *zero delta at a wider
// denominator*: the successor admission source marks 102 rows
// `m209-candidate-backed` (D545 / D548) while the canonical projection
// `prd/architecture/kb-hierarchy-registry.yaml` stays byte-identical to the
// frozen M202 generation's output, its `cc` multiset is unchanged, 0 of 997
// punkt identities are admitted, and no ComponentConcept is minted.
//
// Everything measured here is re-derived from the live files, never trusted
// from prose:
//   - the denominator is recomputed from the live candidate artifact's
//     `counts.by_level` and must sum to the declared extraction total (D547);
//   - the provenance counts, the flat (bare-number) key_path rule, the absence
//     of punkt rows and the frozen `cc` multiset are recomputed from the two
//     live admission sources;
//   - every `sha256` / `bytes` pin in the evidence record is recomputed from
//     the live file bytes;
//   - the frozen M202 pair and its proof-gate pin are proven unmodified with
//     `git status --porcelain`.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (clean-worktree proof). No cargo, no
// network, no `.gsd` / ignored / absolute path is ever read as evidence, and
// this contract never writes a file.
//
// The M209 successor artifact, its admission source and its evidence record
// are authored in this slice and committed by closeout, so `git ls-files`
// cannot see them at first run; they are therefore asserted to exist and to be
// repository-relative, while every frozen M202 input is asserted tracked.
//
// Run: node --test scripts/m209_s02_regeneration_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";
const EVIDENCE = "prd/migration/rust-evidence/m209-s02-admission-regeneration-evidence.json";
const M209_ADMISSIONS = "prd/architecture/m209-s02-kb-hierarchy-registry-admissions.yaml";
const FROZEN_ADMISSIONS = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const REGISTRY = "prd/architecture/kb-hierarchy-registry.yaml";
const M202_ARTIFACT = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_S03 = "prd/migration/rust-evidence/m202-s03-registry-regeneration.json";
const M202_S04 = "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json";
const RUST_PIN = "crates/ln-kb-ontology/tests/r035_proof_gate.rs";
const CONTRACT_PATH = "scripts/m209_s02_regeneration_contract.test.mjs";

// Frozen M202 evidence: any worktree delta here is frozen-input drift (D544).
const FROZEN_INPUTS = [M202_ARTIFACT, M202_S03, M202_S04, FROZEN_ADMISSIONS, REGISTRY, RUST_PIN];

const EVIDENCE_SCHEMA = "law-nexus-m209-admission-regeneration-evidence/v1";
const EVIDENCE_LIFECYCLE = "[proposed]";
const NEEDLE = "law_2013-04-05_44-fz";
const M209_PROVENANCE = "m209-candidate-backed";
const LEGACY_PROVENANCE = "legacy-human";

// Declared denominator (D547): one live extraction over one named tracked
// edition, decomposed by level.
const DECLARED_EXTRACTED = 1901;
const DECLARED_BY_LEVEL = { glava: 8, statya: 94, chast: 793, punkt: 997, paragraph: 9 };
const DECLARED_CANDIDATE_BACKED = 102;
const DECLARED_UNADMITTED = 1799;
const DECLARED_PUNKT_ADMITTED = 0;

const ROWS_TOTAL = 166;
const ROWS_M209_LEGACY = 64;
const REGISTRY_SHA256 = "6d7952b716b60d3b15ce302833323375e4964b70bb36b20a608331cfa3193c38";

// Ignored local overlays. A cited "source" under any of these is not a tracked
// durable proof anchor and must be refused before it is read.
const IGNORED_PREFIXES = [".gsd/", ".planning/", ".audits/", "target/", "node_modules/"];

// DOCUMENTED_CODES_BEGIN
// file_missing: a cited input path does not exist on disk
// schema_mismatch: evidence schema id is not the successor regeneration schema
// lifecycle_drift: lifecycle is not [proposed] or authority is claimed
// required_key_missing: a mandatory evidence field is absent
// absolute_path: a cited path is absolute or escapes the repository root
// ignored_overlay_reference: a cited path lives under an ignored local overlay
// raw_legal_text: evidence carries non-ASCII (raw legal) content
// denominator_mismatch: declared denominator disagrees with the live artifact
// provenance_count_mismatch: declared row counts disagree with the live sources
// cc_multiset_mismatch: the successor cc multiset differs from the frozen one
// punkt_row_present: a punkt row was admitted, or the zero claim was dropped
// key_path_not_flat: a candidate-backed row carries a nested key_path
// digest_mismatch: a declared sha256 disagrees with the live file bytes
// byte_count_mismatch: a declared byte count disagrees with the live file
// zero_delta_missing: the projection is not pinned byte-identical
// heartbeat_mismatch: the recorded heartbeat disagrees with the row counts
// exit_code_not_zero: the recorded regeneration exit code is not zero
// frozen_input_modified: the worktree shows a frozen M202 input as modified
// DOCUMENTED_CODES_END

const EMITTABLE_CODES = [
  "file_missing",
  "schema_mismatch",
  "lifecycle_drift",
  "required_key_missing",
  "absolute_path",
  "ignored_overlay_reference",
  "raw_legal_text",
  "denominator_mismatch",
  "provenance_count_mismatch",
  "cc_multiset_mismatch",
  "punkt_row_present",
  "key_path_not_flat",
  "digest_mismatch",
  "byte_count_mismatch",
  "zero_delta_missing",
  "heartbeat_mismatch",
  "exit_code_not_zero",
  "frozen_input_modified",
];

// ---------------------------------------------------------------------------
// reading helpers (tracked, repository-relative inputs only)
// ---------------------------------------------------------------------------

function readRepo(relative) {
  for (const prefix of IGNORED_PREFIXES) {
    assert.ok(
      !relative.startsWith(prefix),
      `${relative} is an ignored local overlay, not a durable proof anchor`,
    );
  }
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  return readFileSync(path.join(root, relative), "utf8");
}

function readJson(relative) {
  return JSON.parse(readRepo(relative));
}

function sha256Of(relative) {
  return createHash("sha256").update(readFileSync(path.join(root, relative))).digest("hex");
}

function bytesOf(relative) {
  return readFileSync(path.join(root, relative)).length;
}

function isTracked(relative) {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", relative], { cwd: root, stdio: "pipe" });
    return true;
  } catch {
    return false;
  }
}

function dirtyPaths() {
  const out = execFileSync("git", ["status", "--porcelain"], { cwd: root, encoding: "utf8" });
  return out
    .split("\n")
    .filter(Boolean)
    .map((line) => line.slice(3).trim())
    .filter((entry) => entry.length > 0);
}

/// The closed admission row schema is exactly
/// {path_needle, level, number, key_path, cc, provenance}; rows are rendered in
/// the frozen flow style, so a small tolerant parse is enough here.
function parseRows(text) {
  const rows = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("- {") || !line.includes("provenance:")) continue;
    const open = line.indexOf("{");
    const close = line.lastIndexOf("}");
    assert.ok(open >= 0 && close > open, `malformed admission row: ${line}`);
    const inner = line.slice(open + 1, close);
    const fields = {};
    let current = "";
    let quoted = false;
    const parts = [];
    for (const ch of inner) {
      if (ch === '"') quoted = !quoted;
      if (ch === "," && !quoted) {
        parts.push(current);
        current = "";
        continue;
      }
      current += ch;
    }
    parts.push(current);
    for (const part of parts) {
      const at = part.indexOf(":");
      assert.ok(at > 0, `malformed admission field: ${part}`);
      fields[part.slice(0, at).trim()] = part.slice(at + 1).trim().replace(/^"|"$/g, "");
    }
    rows.push(fields);
  }
  return rows;
}

function isAbsoluteOrEscaping(value) {
  return (
    value.startsWith("/") ||
    value.startsWith("~") ||
    value.startsWith("\\") ||
    /^[A-Za-z]:[\\/]/.test(value) ||
    value.split("/").includes("..")
  );
}

function stringLeaves(value, out = []) {
  if (typeof value === "string") {
    out.push(value);
  } else if (Array.isArray(value)) {
    for (const item of value) stringLeaves(item, out);
  } else if (value && typeof value === "object") {
    for (const item of Object.values(value)) stringLeaves(item, out);
  }
  return out;
}

// ---------------------------------------------------------------------------
// live inputs
// ---------------------------------------------------------------------------

const liveArtifact = readJson(ARTIFACT);
const liveAdmissions = parseRows(readRepo(M209_ADMISSIONS));
const frozenRows = parseRows(readRepo(FROZEN_ADMISSIONS));
const liveEvidence = readJson(EVIDENCE);

const candidateBacked = liveAdmissions.filter((row) => row.provenance === M209_PROVENANCE);
const legacy = liveAdmissions.filter((row) => row.provenance === LEGACY_PROVENANCE);
const punktRows = liveAdmissions.filter((row) => row.level === "punkt");
const live = {
  artifact: liveArtifact,
  admissions: liveAdmissions,
  frozen: frozenRows,
  candidateBacked,
  legacy,
  punktRows,
  registrySha256: sha256Of(REGISTRY),
  registryBytes: bytesOf(REGISTRY),
  dirty: dirtyPaths(),
  digests: new Map(FROZEN_INPUTS.concat([ARTIFACT, M209_ADMISSIONS]).map((p) => [p, sha256Of(p)])),
  bytes: new Map(FROZEN_INPUTS.concat([ARTIFACT, M209_ADMISSIONS]).map((p) => [p, bytesOf(p)])),
  exists: new Set(FROZEN_INPUTS.concat([ARTIFACT, M209_ADMISSIONS, EVIDENCE])),
};

// ---------------------------------------------------------------------------
// the contract
// ---------------------------------------------------------------------------

function sortedCcMultiset(rows) {
  return rows.map((row) => row.cc).sort();
}

function validateRegeneration(evidence, data) {
  const codes = [];
  const push = (code) => codes.push(code);

  for (const relative of data.exists) {
    const onDisk = existsSync(path.join(root, relative));
    if (!onDisk) {
      push("file_missing");
      break;
    }
  }

  if (evidence.schema !== EVIDENCE_SCHEMA) push("schema_mismatch");
  if (evidence.lifecycle !== EVIDENCE_LIFECYCLE || evidence.authoritative !== false) {
    push("lifecycle_drift");
  }

  const required = [
    "schema",
    "schema_version",
    "lifecycle",
    "authoritative",
    "milestone",
    "slice",
    "task",
    "generator",
    "index_fix",
    "denominator",
    "inputs",
    "output",
    "regeneration",
    "non_claims",
  ];
  if (required.some((key) => !(key in evidence))) push("required_key_missing");

  const leaves = stringLeaves(evidence);
  if (leaves.some(isAbsoluteOrEscaping)) push("absolute_path");
  if (leaves.some((value) => IGNORED_PREFIXES.some((prefix) => value.includes(prefix)))) {
    push("ignored_overlay_reference");
  }
  if (!/^[\x00-\x7F]*$/.test(JSON.stringify(evidence)) || leaves.some((v) => !/^[\x00-\x7F]*$/.test(v))) {
    push("raw_legal_text");
  }

  const denominator = evidence.denominator ?? {};
  const byLevel = denominator.by_level ?? {};
  const liveByLevel = data.artifact.counts.by_level;
  const declaredSum = Object.values(byLevel).reduce((sum, value) => sum + (value ?? 0), 0);
  const levelsMatch = Object.keys(DECLARED_BY_LEVEL).every(
    (level) => byLevel[level] === DECLARED_BY_LEVEL[level] && liveByLevel[level] === DECLARED_BY_LEVEL[level],
  );
  if (
    !levelsMatch ||
    declaredSum !== DECLARED_EXTRACTED ||
    denominator.extracted_identities !== DECLARED_EXTRACTED ||
    data.artifact.counts.extracted !== DECLARED_EXTRACTED ||
    denominator.candidate_backed_identities !== DECLARED_CANDIDATE_BACKED ||
    denominator.unadmitted_identities !== DECLARED_UNADMITTED ||
    data.artifact.counts.extracted - DECLARED_CANDIDATE_BACKED !== DECLARED_UNADMITTED
  ) {
    push("denominator_mismatch");
  }

  const source = evidence.inputs?.admission_source ?? {};
  if (
    source.rows_total !== data.admissions.length ||
    source.rows_total !== ROWS_TOTAL ||
    source.rows_m209_candidate_backed !== data.candidateBacked.length ||
    source.rows_legacy_human !== data.legacy.length ||
    source.rows_legacy_human !== ROWS_M209_LEGACY
  ) {
    push("provenance_count_mismatch");
  }

  const declaredCc = [...(evidence.output?.m209_candidate_backed_cc ?? [])].sort();
  const liveCandidateCc = sortedCcMultiset(data.candidateBacked);
  const liveAllCc = sortedCcMultiset(data.admissions);
  const frozenCc = sortedCcMultiset(data.frozen);
  if (
    JSON.stringify(declaredCc) !== JSON.stringify(liveCandidateCc) ||
    JSON.stringify(liveAllCc) !== JSON.stringify(frozenCc)
  ) {
    push("cc_multiset_mismatch");
  }

  const punktFree =
    data.punktRows.length === 0 &&
    source.rows_punkt === DECLARED_PUNKT_ADMITTED &&
    evidence.output?.punkt_rows_admitted === DECLARED_PUNKT_ADMITTED &&
    evidence.denominator?.punkt_admitted === DECLARED_PUNKT_ADMITTED;
  if (!punktFree) push("punkt_row_present");

  const flat = data.candidateBacked.every((row) => row.key_path === row.number && !row.key_path.includes("/"));
  if (!flat || source.candidate_key_paths_flat !== true) push("key_path_not_flat");

  const digestChecks = [
    [ARTIFACT, evidence.inputs?.candidate_artifact?.sha256],
    [ARTIFACT, evidence.inputs?.candidate_artifact?.bytes, "bytes"],
    [M209_ADMISSIONS, source.sha256],
    [M209_ADMISSIONS, source.bytes, "bytes"],
    [REGISTRY, evidence.inputs?.frozen_registry?.sha256],
    [REGISTRY, evidence.inputs?.frozen_registry?.bytes, "bytes"],
    [FROZEN_ADMISSIONS, evidence.inputs?.frozen_admissions_source?.sha256],
    [FROZEN_ADMISSIONS, evidence.inputs?.frozen_admissions_source?.bytes, "bytes"],
    [M202_ARTIFACT, evidence.inputs?.frozen_candidate_artifact?.sha256],
    [M202_ARTIFACT, evidence.inputs?.frozen_candidate_artifact?.bytes, "bytes"],
  ];
  for (const [relative, declared, kind] of digestChecks) {
    if (kind === "bytes") {
      if (declared !== undefined && declared !== data.bytes.get(relative)) push("byte_count_mismatch");
    } else if (declared !== data.digests.get(relative)) {
      push("digest_mismatch");
    }
  }

  const output = evidence.output ?? {};
  if (
    output.zero_delta !== true ||
    output.path !== REGISTRY ||
    output.sha256_after_check !== data.registrySha256 ||
    output.sha256_after_check !== output.sha256_before ||
    output.sha256_after_check !== REGISTRY_SHA256 ||
    output.binding_rows_total !== data.admissions.length ||
    output.binding_rows_m209_candidate_backed !== data.candidateBacked.length ||
    output.binding_rows_legacy_human !== data.legacy.length ||
    output.binding_rows_m202_candidate_backed !== 0 ||
    output.cc_multiset_equals_frozen_source !== true
  ) {
    push("zero_delta_missing");
  }

  const expectedHeartbeat = `admitted=${data.admissions.length} legacy=${data.legacy.length} candidate-backed=${data.candidateBacked.length} drift=0`;
  if (evidence.regeneration?.check?.heartbeat !== expectedHeartbeat) push("heartbeat_mismatch");

  if (
    evidence.regeneration?.check?.exit !== 0 ||
    evidence.regeneration?.frozen_m202_check?.exit !== 0 ||
    evidence.index_fix?.after_exit !== 0
  ) {
    push("exit_code_not_zero");
  }

  if (data.dirty.some((entry) => FROZEN_INPUTS.includes(entry))) push("frozen_input_modified");

  return { ok: codes.length === 0, codes };
}

// ---------------------------------------------------------------------------
// fail-closed mutations: every documented code must have a firing mutation
// ---------------------------------------------------------------------------

function mutate(fn) {
  const clone = structuredClone(liveEvidence);
  fn(clone);
  return clone;
}

test("every documented fail-closed code fires from a named mutation", () => {
  const mutations = [
    ["file_missing", (e) => { e.inputs.candidate_artifact.path = "prd/migration/rust-evidence/absent.json"; }, "exists"],
    ["schema_mismatch", (e) => { e.schema = "law-nexus-m209-admission-regeneration-evidence/v0"; }],
    ["lifecycle_drift", (e) => { e.authoritative = true; }],
    ["required_key_missing", (e) => { delete e.denominator; }],
    ["absolute_path", (e) => { e.inputs.admission_source.path = "/root/law-nexus/prd/architecture/x.yaml"; }],
    ["ignored_overlay_reference", (e) => { e.inputs.frozen_registry.path = ".gsd/gsd.db"; }],
    ["raw_legal_text", (e) => { e.non_claims.push("\u0421\u0442\u0430\u0442\u044c\u044f 44"); }],
    ["denominator_mismatch", (e) => { e.denominator.by_level.punkt = 996; }],
    ["provenance_count_mismatch", (e) => { e.inputs.admission_source.rows_m209_candidate_backed = 101; }],
    ["cc_multiset_mismatch", (e) => { e.output.m209_candidate_backed_cc.pop(); }],
    ["punkt_row_present", (e) => { e.output.punkt_rows_admitted = 1; }],
    ["key_path_not_flat", (e) => { e.inputs.admission_source.candidate_key_paths_flat = false; }],
    ["digest_mismatch", (e) => { e.inputs.candidate_artifact.sha256 = "0".repeat(64); }],
    ["byte_count_mismatch", (e) => { e.inputs.candidate_artifact.bytes = 1; }],
    ["zero_delta_missing", (e) => { e.output.zero_delta = false; }],
    ["heartbeat_mismatch", (e) => { e.regeneration.check.heartbeat = "admitted=166 legacy=64 candidate-backed=3 drift=0"; }],
    ["exit_code_not_zero", (e) => { e.regeneration.check.exit = 6; }],
    ["frozen_input_modified", (e) => { e.__dirty = [REGISTRY]; }],
  ];

  const covered = new Set();
  for (const [code, apply, kind] of mutations) {
    const evidence = mutate(apply);
    const data =
      kind === "exists"
        ? { ...live, exists: new Set([...live.exists, "prd/migration/rust-evidence/absent.json"]) }
        : code === "frozen_input_modified"
          ? { ...live, dirty: [REGISTRY] }
          : live;
    const result = validateRegeneration(evidence, data);
    assert.ok(
      result.codes.includes(code),
      `${code} was not emitted by its mutation; got ${JSON.stringify(result.codes)}`,
    );
    assert.equal(result.ok, false, `${code} must make the record fail closed`);
    covered.add(code);
  }
  assert.deepEqual([...covered].sort(), [...EMITTABLE_CODES].sort());
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
// live shape, tracked anchors and the denominator
// ---------------------------------------------------------------------------

test("successor artifact, admission source and evidence are live repository-relative files", () => {
  for (const relative of [ARTIFACT, M209_ADMISSIONS, EVIDENCE]) {
    assert.ok(existsSync(path.join(root, relative)), `${relative} must exist`);
    assert.ok(!path.isAbsolute(relative));
  }
  assert.equal(liveArtifact.schema, "law-nexus-hierarchy-candidate-artifact/v1");
  assert.equal(liveArtifact.counts.extracted, DECLARED_EXTRACTED);
  // Frozen anchors stay tracked: the pins those files carry cannot be orphaned.
  for (const relative of FROZEN_INPUTS) {
    assert.ok(isTracked(relative), `${relative} must stay tracked`);
  }
});

test("declared denominator decomposes the live artifact and leaves the remainder unadmitted", () => {
  const result = validateRegeneration(liveEvidence, live);
  assert.deepEqual(result.codes, [], `regeneration errors: ${JSON.stringify(result.codes)}`);
  assert.equal(liveArtifact.counts.extracted, DECLARED_EXTRACTED);
  assert.equal(liveArtifact.counts.unique, DECLARED_EXTRACTED);
  assert.equal(DECLARED_EXTRACTED - DECLARED_CANDIDATE_BACKED, DECLARED_UNADMITTED);
  assert.equal(liveEvidence.denominator.unadmitted_reason, "nested-level-no-existing-cc-identity");
  // 0 of 997 punkt identities admitted, and no punkt row exists to admit.
  assert.equal(live.punktRows.length, 0);
  assert.equal(DECLARED_BY_LEVEL.punkt, 997);
});

test("all 102 candidate-backed rows are flat and resolve into the frozen cc multiset", () => {
  assert.equal(live.candidateBacked.length, DECLARED_CANDIDATE_BACKED);
  assert.equal(live.legacy.length, ROWS_M209_LEGACY);
  assert.equal(live.admissions.length, ROWS_TOTAL);
  for (const row of live.candidateBacked) {
    assert.equal(row.path_needle, NEEDLE);
    assert.ok(["glava", "statya"].includes(row.level), `${row.level} must stay a flat level`);
    assert.equal(row.key_path, row.number, "candidate-backed key_path stays the bare number");
  }
  assert.deepEqual(sortedCcMultiset(live.candidateBacked.concat(live.legacy)), sortedCcMultiset(live.frozen));
});

test("frozen M202 inputs are unmodified in the worktree", () => {
  const dirtyFrozen = live.dirty.filter((entry) => FROZEN_INPUTS.includes(entry));
  assert.deepEqual(dirtyFrozen, [], "frozen M202 inputs must not move");
  assert.equal(live.registrySha256, REGISTRY_SHA256);
  assert.equal(live.digests.get(M202_ARTIFACT), "50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6");
  assert.equal(live.digests.get(FROZEN_ADMISSIONS), "1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19");
  assert.ok(!FROZEN_INPUTS.includes(M209_ADMISSIONS), "the successor source is not a frozen input");
  assert.ok(!FROZEN_INPUTS.includes(ARTIFACT), "the successor artifact is not a frozen input");
});

// ---------------------------------------------------------------------------
// markers (emitted only after the regeneration contract holds)
// ---------------------------------------------------------------------------

test("M209 S02 regeneration markers", () => {
  const result = validateRegeneration(liveEvidence, live);
  assert.deepEqual(result.codes, [], `regeneration errors: ${JSON.stringify(result.codes)}`);
  console.log("M209_S02_REGENERATION_OK");
  console.log("M209_S02_ZERO_DELTA_OK");
  console.log(`denominator=${liveArtifact.counts.extracted}`);
  console.log(`candidate_backed=${live.candidateBacked.length}`);
  console.log(`legacy=${live.legacy.length}`);
  console.log(`unadmitted=${DECLARED_UNADMITTED}`);
});
