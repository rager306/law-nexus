#!/usr/bin/env node
// Successor candidate-backed admission-source generation (M209-2yg6ix S02 T02,
// D545 / D546).
//
// WHY THIS FILE EXISTS
// The frozen M202 pair is byte-pinned and may not be edited in place:
//   prd/architecture/kb-hierarchy-registry-admissions.yaml
//     (19982 bytes, sha256 1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19)
//   prd/architecture/kb-hierarchy-registry.yaml
//     (16699 bytes, sha256 6d7952b716b60d3b15ce302833323375e4964b70bb36b20a608331cfa3193c38)
// are `include_str!`-pinned with exact byte counts by
// crates/ln-kb-ontology/tests/r035_proof_gate.rs, and their sha256 hex
// appears exactly once in prd/migration/rust-evidence/m202-s04-r035-proof-gate.json.
// Editing either file would force a self-referential rewrite of frozen M202
// evidence, which D544 and D431 forbid.
//
// So the expanded candidate-backed coverage is published as this SEPARATE
// successor generation, whose rows carry their own provenance literal
// `m209-candidate-backed` — never a relabel of `m202-candidate-backed`
// (D546), so the frozen M202 rows keep their own pin and provenance.
//
// NON-AUTHORITY
// Lifecycle stays [proposed] and authoritative stays false. Each row binds an
// already-existing ComponentConcept identifier named explicitly by the row's
// `cc:` field; the extractor never mints a CC from level/number. Punkt rows
// are absent by construction (D546). The closed row schema is exactly
// {path_needle, level, number, key_path, cc, provenance}; a generation link
// (e.g. "supersedes the M202 generation") is recorded in the task evidence and
// in the comments below, never smuggled into the closed schema as an extra key.
//
// DERIVATION RULE
// The needle(s) eligible for the successor generation are derived from the
// frozen source itself: the path_needle(s) of rows already marked
// `m202-candidate-backed`. That is data-derived, not hardcoded, and it keeps
// unrelated needles (n-402-fz / n-435-fz / n-44-fz) out of the expansion.
// A row becomes `m209-candidate-backed` when all of the following hold:
//   1. its path_needle is an eligible needle;
//   2. (level, number) resolves to a candidate identity in the M209 artifact;
//   3. the frozen registry binds the same (path_needle, level, number) to the
//      same cc the row names.
// Otherwise the row is re-emitted unchanged as `legacy-human`. Point 3 is what
// makes the widening safe: the successor source can only ever confirm a CC
// identity that the frozen registry already states for that exact key.
//
// INPUTS (read-only): frozen admissions YAML, M209 candidate artifact JSON,
// frozen registry YAML.
// OUTPUT: prd/architecture/m209-s02-kb-hierarchy-registry-admissions.yaml
//
// NAMED FAIL-CLOSED CODES (every one is exercised by --selftest)
//   refused_frozen_source        --out resolves to the frozen M202 admissions
//   refused_registry_path        --out resolves to kb-hierarchy-registry.yaml
//   input_missing                a required input file is absent
//   source_key_unknown           unknown top-level or row key in a source YAML
//   row_parse_failed             malformed row / duplicate registry key
//   artifact_shape_invalid       candidate artifact lacks required digests
//   needle_not_derived           frozen source has no m202-candidate-backed row
//   key_path_not_flat            an emitted candidate key_path is not the number
//   punkt_row_minted             any row would carry level punkt
//   cc_set_mismatch              emitted cc multiset != frozen cc multiset
//   candidate_backed_count_mismatch  counts are not 102 candidate-backed / 64 legacy
//   admissions_drift             --check bytes differ from the committed file
//
// USAGE
//   node scripts/m209_s02_build_admissions.mjs --write   # default
//   node scripts/m209_s02_build_admissions.mjs --check
//   node scripts/m209_s02_build_admissions.mjs --selftest
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

const FROZEN_ADMISSIONS_PATH = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
const REGISTRY_PATH = "prd/architecture/kb-hierarchy-registry.yaml";
const CANDIDATE_ARTIFACT_PATH =
  "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";
const SUCCESSOR_PATH = "prd/architecture/m209-s02-kb-hierarchy-registry-admissions.yaml";

const ADMISSION_SCHEMA_V1 = "law-nexus-kb-hierarchy-admission/v1";
const CANDIDATE_ARTIFACT_SCHEMA_V1 = "law-nexus-hierarchy-candidate-artifact/v1";
const PROVENANCE_LEGACY = "legacy-human";
const PROVENANCE_M202 = "m202-candidate-backed";
const PROVENANCE_M209 = "m209-candidate-backed";

const EXPECTED_ROWS = 166;
const EXPECTED_CANDIDATE_BACKED = 102;
const EXPECTED_LEGACY = 64;

const TOP_LEVEL_KEYS = new Set([
  "schema",
  "lifecycle",
  "authoritative",
  "candidate_artifact_path",
  "candidate_artifact_sha256",
  "candidate_source_digest",
  "candidate_identity_digest",
  "admissions",
]);
const ROW_KEYS = new Set(["path_needle", "level", "number", "key_path", "cc", "provenance"]);
const PROVENANCE_LITERALS = new Set([PROVENANCE_LEGACY, PROVENANCE_M202, PROVENANCE_M209]);

class BuildError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "BuildError";
    this.code = code;
    this.detail = detail;
  }
}

function fail(code, detail) {
  throw new BuildError(code, detail);
}

function repoPath(relative) {
  return path.resolve(REPO_ROOT, relative);
}

function sha256Hex(text) {
  return createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex");
}

function stripComment(line) {
  const index = line.indexOf("#");
  return (index === -1 ? line : line.slice(0, index)).trim();
}

function unquote(value) {
  const trimmed = value.trim();
  if (trimmed.length >= 2 && trimmed.startsWith('"') && trimmed.endsWith('"')) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/// Parse one closed-schema admission source (`law-nexus-kb-hierarchy-admission/v1`).
/// Unknown top-level keys, unknown row keys and unknown provenance literals
/// fail closed, so a smuggled field cannot ride along unnoticed.
export function parseAdmissionSource(text, label = "source") {
  const header = new Map();
  const rows = [];
  let admissionsSeen = false;
  for (const raw of text.split("\n")) {
    const trimmed = stripComment(raw);
    if (trimmed === "") continue;
    if (trimmed.startsWith("-")) {
      if (!admissionsSeen) {
        fail("row_parse_failed", `${label}: row before admissions:`);
      }
      rows.push(parseRow(trimmed, label));
      continue;
    }
    const colon = trimmed.indexOf(":");
    if (colon === -1) {
      fail("source_key_unknown", `${label}: ${trimmed}`);
    }
    const key = trimmed.slice(0, colon).trim();
    const value = trimmed.slice(colon + 1).trim();
    if (!TOP_LEVEL_KEYS.has(key)) {
      fail("source_key_unknown", `${label}: ${key}`);
    }
    if (key === "admissions") {
      admissionsSeen = true;
      continue;
    }
    if (header.has(key)) {
      fail("source_key_unknown", `${label}: duplicate ${key}`);
    }
    header.set(key, unquote(value));
  }
  if (!admissionsSeen) {
    fail("source_key_unknown", `${label}: admissions missing`);
  }
  for (const key of TOP_LEVEL_KEYS) {
    if (key !== "admissions" && !header.has(key)) {
      fail("source_key_unknown", `${label}: missing ${key}`);
    }
  }
  if (header.get("schema") !== ADMISSION_SCHEMA_V1) {
    fail("source_key_unknown", `${label}: schema ${header.get("schema")}`);
  }
  return { header, rows };
}

function parseRow(line, label, { requireProvenance = true } = {}) {
  const open = line.indexOf("{");
  const close = line.lastIndexOf("}");
  if (open === -1 || close === -1 || close < open) {
    fail("row_parse_failed", `${label}: ${line}`);
  }
  if (line.slice(close + 1).trim() !== "") {
    fail("row_parse_failed", `${label}: trailing text after row`);
  }
  const row = {};
  for (const field of line.slice(open + 1, close).split(",")) {
    const piece = field.trim();
    if (piece === "") continue;
    const colon = piece.indexOf(":");
    if (colon === -1) {
      fail("row_parse_failed", `${label}: ${piece}`);
    }
    const key = piece.slice(0, colon).trim();
    const value = unquote(piece.slice(colon + 1));
    if (!ROW_KEYS.has(key)) {
      fail("source_key_unknown", `${label}: row key ${key}`);
    }
    if (Object.hasOwn(row, key)) {
      fail("row_parse_failed", `${label}: duplicate row key ${key}`);
    }
    row[key] = value;
  }
  for (const required of ["path_needle", "level", "number", "cc"]) {
    if (!row[required]) {
      fail("row_parse_failed", `${label}: missing ${required}`);
    }
  }
  if (requireProvenance) {
    if (!row.provenance) {
      fail("row_parse_failed", `${label}: missing provenance`);
    }
    if (!PROVENANCE_LITERALS.has(row.provenance)) {
      fail("source_key_unknown", `${label}: provenance ${row.provenance}`);
    }
  }
  return row;
}

function rowKey(row) {
  return `${row.path_needle}|${row.level}|${row.number}`;
}

/// Parse the frozen registry's explicit marker -> ComponentConcept bindings.
/// Only the `bindings:` section is a binding table; the `works:` / `editions:`
/// sections carry different row shapes and are skipped by section, never by
/// guessing at the row's keys.
export function parseRegistryBindings(text, label = "registry") {
  const bindings = new Map();
  let inBindings = false;
  for (const raw of text.split("\n")) {
    const trimmed = stripComment(raw);
    if (trimmed === "") continue;
    if (trimmed.startsWith("-")) {
      if (!inBindings) continue;
      const row = parseRow(trimmed, label, { requireProvenance: false });
      const key = rowKey(row);
      if (bindings.has(key)) {
        fail("row_parse_failed", `${label}: duplicate binding ${key}`);
      }
      bindings.set(key, row.cc);
      continue;
    }
    const isHeading = trimmed.endsWith(":") && raw.length === raw.trimStart().length;
    if (isHeading) {
      inBindings = trimmed === "bindings:";
    }
  }
  if (bindings.size === 0) {
    fail("row_parse_failed", `${label}: no bindings`);
  }
  return bindings;
}

/// Normalized candidate index from the M209 candidate artifact.
///
/// The artifact has no path_needle (candidates come from one named source), so
/// needle eligibility is derived from the frozen source. Only FLAT identities
/// are indexed (`path === null`), keyed by `level|number`: flat identities are
/// unique that way in the live artifact, while the nested ones (chast / punkt)
/// repeat their number under different ladders and are never admissible here
/// (D546). The plan's "(level, number) matches a candidate" rule therefore
/// resolves 1:1 for the 102 flat glava/statya rows.
///
/// `key_path` alone is NOT unique in the live artifact (flat glava-N / statya-N
/// / paragraph-N share the bare-number key_path), so the collision set is
/// computed and reported rather than assumed away.
export function candidateIndex(artifact) {
  if (
    !artifact ||
    artifact.schema !== CANDIDATE_ARTIFACT_SCHEMA_V1 ||
    typeof artifact.identity_digest !== "string" ||
    artifact.identity_digest === "" ||
    !artifact.source_binding ||
    typeof artifact.source_binding.source_digest !== "string" ||
    !Array.isArray(artifact.candidates) ||
    artifact.candidates.length === 0
  ) {
    fail("artifact_shape_invalid", "candidate artifact lacks schema/digests/candidates");
  }
  const flat = new Map();
  const seenKeyPaths = new Set();
  const collisions = new Set();
  for (const candidate of artifact.candidates) {
    if (seenKeyPaths.has(candidate.key_path)) {
      collisions.add(candidate.key_path);
    } else {
      seenKeyPaths.add(candidate.key_path);
    }
    if (candidate.path !== null) continue;
    const key = `${candidate.catalog_token}|${candidate.number}`;
    if (flat.has(key)) {
      fail("artifact_shape_invalid", `duplicate flat candidate ${key}`);
    }
    flat.set(key, candidate);
  }
  return {
    flat,
    keyPathCollisions: [...collisions].sort(compareText),
    total: artifact.candidates.length,
  };
}

/// Derive the needles eligible for the successor generation from the frozen
/// source's own `m202-candidate-backed` rows (data-derived, not hardcoded).
export function eligibleNeedles(frozenRows) {
  const needles = new Set();
  for (const row of frozenRows) {
    if (row.provenance === PROVENANCE_M202) needles.add(row.path_needle);
  }
  if (needles.size === 0) {
    fail("needle_not_derived", "no m202-candidate-backed row in frozen source");
  }
  return needles;
}

function compareText(left, right) {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

/// Build the successor rows: candidate-back the eligible-needle rows whose
/// (level, number) resolves to a candidate and whose cc the frozen registry
/// already states for that exact key; re-emit everything else unchanged.
export function buildRows({ frozenRows, registryBindings, candidates }) {
  const needles = eligibleNeedles(frozenRows);
  const seen = new Set();
  const rows = [];
  for (const row of frozenRows) {
    const key = rowKey(row);
    if (seen.has(key)) {
      fail("row_parse_failed", `duplicate admission row ${key}`);
    }
    seen.add(key);
    const candidate = needles.has(row.path_needle)
      ? candidates.flat.get(`${row.level}|${row.number}`)
      : undefined;
    const registryCc = registryBindings.get(key);
    const promoted = candidate !== undefined && registryCc === row.cc;
    if (!promoted) {
      rows.push({ ...row, provenance: PROVENANCE_LEGACY, key_path: undefined });
      continue;
    }
    if (candidate.key_path !== row.number) {
      fail("key_path_not_flat", `${key}: key_path=${candidate.key_path}`);
    }
    rows.push({ ...row, provenance: PROVENANCE_M209, key_path: candidate.key_path });
  }
  rows.sort(
    (left, right) =>
      compareText(left.path_needle, right.path_needle) ||
      compareText(left.level, right.level) ||
      compareText(left.number, right.number),
  );
  return rows;
}

/// Guard: no row of any generation may carry a punkt level (D546).
function assertNoPunkt(rows, label) {
  for (const row of rows) {
    if (row.level === "punkt") {
      fail("punkt_row_minted", `${label}: ${rowKey(row)}`);
    }
  }
}

/// Guard: the emitted cc multiset must equal the frozen source's cc multiset,
/// so a generation can neither mint nor lose a CC binding.
function assertCcMultiset(emitted, frozen) {
  const left = emitted.map((row) => row.cc).sort(compareText).join("\n");
  const right = frozen.map((row) => row.cc).sort(compareText).join("\n");
  if (left !== right) {
    fail("cc_set_mismatch", "emitted cc multiset differs from frozen source");
  }
}

function renderSource({
  rows,
  frozenSha256,
  candidateArtifactPath,
  artifactSha256,
  sourceDigest,
  identityDigest,
}) {
  const lines = [
    "# Successor candidate-backed admission source for the kb-hierarchy registry",
    "# projection (M209-2yg6ix S02 T02, D545 / D546).",
    "#",
    `# Predecessor (frozen, byte-pinned, never edited): ${FROZEN_ADMISSIONS_PATH}`,
    `#   sha256 ${frozenSha256}`,
    "# The frozen pair is include_str!-pinned by",
    "# crates/ln-kb-ontology/tests/r035_proof_gate.rs and its sha256 hex is",
    "# embedded in m202-s04-r035-proof-gate.json, so the widened coverage is",
    "# published as this separate successor generation (D545) instead of an",
    "# in-place edit of frozen evidence (D544 / D431).",
    "#",
    "# Lifecycle: [proposed]",
    "# Non-authority: an admission decision, not legal truth, not InForce, not",
    "# Applicable. Every row binds the already-existing CC identifier named by",
    "# its own `cc:` field; level/number never mint a ComponentConcept.",
    "# Rows are sorted by (path_needle, level, number), byte-lexicographic.",
    "# Candidate-backed rows resolve through FLAT candidate identities (bare",
    "# number key_path, path null); nested ladders never admit here (D546).",
    "# Punkt rows are absent by construction; nested candidacy stays unadmitted",
    "# (D546). The closed row schema is exactly",
    "# {path_needle, level, number, key_path, cc, provenance}; a generation link",
    "# to the M202 generation is recorded in evidence, not as an extra YAML key.",
    "#",
    `# Regenerate: node scripts/m209_s02_build_admissions.mjs --write`,
    `# Verify:     node scripts/m209_s02_build_admissions.mjs --check`,
    "",
    `schema: ${ADMISSION_SCHEMA_V1}`,
    `lifecycle: "[proposed]"`,
    "authoritative: false",
    `candidate_artifact_path: ${candidateArtifactPath}`,
    `candidate_artifact_sha256: ${artifactSha256}`,
    `candidate_source_digest: ${sourceDigest}`,
    `candidate_identity_digest: ${identityDigest}`,
    "admissions:",
  ];
  for (const row of rows) {
    let line = `  - {path_needle: ${row.path_needle}, level: ${row.level}, number: "${row.number}"`;
    if (row.provenance === PROVENANCE_M209) {
      line += `, key_path: "${row.key_path}"`;
    }
    line += `, cc: ${row.cc}, provenance: ${row.provenance}}`;
    lines.push(line);
  }
  lines.push("");
  return lines.join("\n");
}

/// Pure build: frozen texts + parsed artifact in, rendered successor text out.
export function buildSuccessor({
  frozenText,
  artifact,
  registryText,
  frozenSha256 = sha256Hex(frozenText),
  artifactSha256 = artifactSha256FromDisk(),
  expectedCandidateBacked = EXPECTED_CANDIDATE_BACKED,
  expectedLegacy = EXPECTED_LEGACY,
}) {
  const { rows: frozenRows } = parseAdmissionSource(frozenText, "frozen-admissions");
  const registryBindings = parseRegistryBindings(registryText, "registry");
  const candidates = candidateIndex(artifact);
  assertNoPunkt(frozenRows, "frozen-admissions");
  const rows = buildRows({ frozenRows, registryBindings, candidates });
  assertNoPunkt(rows, "successor");
  assertCcMultiset(rows, frozenRows);
  const candidateBacked = rows.filter((row) => row.provenance === PROVENANCE_M209).length;
  const legacy = rows.filter((row) => row.provenance === PROVENANCE_LEGACY).length;
  // Every row carries exactly one of the two provenances, so pinning both
  // counts pins the 166-row total as well.
  if (candidateBacked !== expectedCandidateBacked || legacy !== expectedLegacy) {
    fail(
      "candidate_backed_count_mismatch",
      `rows=${rows.length} candidate_backed=${candidateBacked} legacy=${legacy}`,
    );
  }
  const text = renderSource({
    rows,
    frozenSha256,
    candidateArtifactPath: CANDIDATE_ARTIFACT_PATH,
    artifactSha256,
    sourceDigest: artifact.source_binding.source_digest,
    identityDigest: artifact.identity_digest,
  });
  return {
    text,
    rows,
    candidateBacked,
    legacy,
    keyPathCollisions: candidates.keyPathCollisions,
    candidatesTotal: candidates.total,
  };
}

let diskArtifactSha256 = null;
function artifactSha256FromDisk() {
  if (diskArtifactSha256 === null) {
    diskArtifactSha256 = sha256Hex(readFileSync(repoPath(CANDIDATE_ARTIFACT_PATH), "utf8"));
  }
  return diskArtifactSha256;
}

function checkOutTarget(outPath) {
  const resolved = path.resolve(REPO_ROOT, outPath);
  if (resolved === repoPath(FROZEN_ADMISSIONS_PATH)) {
    fail("refused_frozen_source", FROZEN_ADMISSIONS_PATH);
  }
  if (resolved === repoPath(REGISTRY_PATH)) {
    fail("refused_registry_path", REGISTRY_PATH);
  }
  return resolved;
}

function readInput(relative) {
  const resolved = repoPath(relative);
  if (!existsSync(resolved)) {
    fail("input_missing", relative);
  }
  return readFileSync(resolved, "utf8");
}

function parseArgs(argv) {
  const options = { mode: "write", out: SUCCESSOR_PATH };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--check") options.mode = "check";
    else if (arg === "--write") options.mode = "write";
    else if (arg === "--selftest") options.mode = "selftest";
    else if (arg === "--help" || arg === "-h") options.mode = "help";
    else if (arg === "--out") {
      index += 1;
      if (index >= argv.length) fail("input_missing", "--out requires a path");
      options.out = argv[index];
    } else {
      fail("input_missing", `unknown argument ${arg}`);
    }
  }
  return options;
}

function expectCode(code, thunk) {
  try {
    thunk();
  } catch (error) {
    if (error instanceof BuildError && error.code === code) return;
    throw new Error(`selftest: expected ${code}, got ${error.message}`);
  }
  throw new Error(`selftest: expected ${code}, but no failure was raised`);
}

function selftest() {
  const frozenText = readInput(FROZEN_ADMISSIONS_PATH);
  const registryText = readInput(REGISTRY_PATH);
  const artifact = JSON.parse(readInput(CANDIDATE_ARTIFACT_PATH));
  const { rows: frozenRows } = parseAdmissionSource(frozenText, "selftest");

  expectCode("refused_frozen_source", () => checkOutTarget(FROZEN_ADMISSIONS_PATH));
  expectCode("refused_registry_path", () => checkOutTarget(REGISTRY_PATH));
  expectCode("input_missing", () => readInput("prd/architecture/does-not-exist.yaml"));
  expectCode("source_key_unknown", () =>
    parseAdmissionSource(`${frozenText}\nminted: true\n`, "selftest"),
  );
  expectCode("source_key_unknown", () =>
    parseAdmissionSource(
      `${frozenText}  - {path_needle: n-44-fz, level: statya, number: "1", cc: cc:44fz:s1, supersedes: m202, provenance: legacy-human}\n`,
      "selftest",
    ),
  );
  expectCode("row_parse_failed", () => parseAdmissionSource(frozenText.replace("{", ""), "selftest"));
  expectCode("artifact_shape_invalid", () => candidateIndex({ schema: CANDIDATE_ARTIFACT_SCHEMA_V1 }));
  expectCode("needle_not_derived", () =>
    eligibleNeedles(frozenRows.map((row) => ({ ...row, provenance: PROVENANCE_LEGACY }))),
  );
  expectCode("key_path_not_flat", () =>
    buildSuccessor({
      frozenText,
      artifact: {
        ...artifact,
        candidates: artifact.candidates.map((candidate) =>
          candidate.catalog_token === "glava" && candidate.number === "2"
            ? { ...candidate, key_path: "statya-1/punkt-9" }
            : candidate,
        ),
      },
      registryText,
    }),
  );
  expectCode("punkt_row_minted", () =>
    buildSuccessor({
      frozenText: `${frozenText}  - {path_needle: law_2013-04-05_44-fz, level: punkt, number: "1", cc: cc:44-fz:statya-1-punkt-1, provenance: legacy-human}\n`,
      artifact,
      registryText,
    }),
  );
  expectCode("cc_set_mismatch", () =>
    assertCcMultiset([{ cc: "cc:a:1" }], [{ cc: "cc:a:2" }]),
  );
  expectCode("candidate_backed_count_mismatch", () =>
    buildSuccessor({
      frozenText,
      artifact,
      registryText,
      expectedCandidateBacked: 999,
      expectedLegacy: EXPECTED_LEGACY,
    }),
  );
  expectCode("admissions_drift", () => checkBytes("rendered", "committed"));
  const built = buildSuccessor({
    frozenText,
    artifact,
    registryText,
    frozenSha256: sha256Hex(frozenText),
    artifactSha256: sha256Hex(readInput(CANDIDATE_ARTIFACT_PATH)),
  });
  process.stdout.write(
    `M209_S02_BUILD_SELFTEST_OK codes=12 rows=${built.rows.length} ` +
      `candidate_backed=${built.candidateBacked} legacy=${built.legacy} ` +
      `key_path_collisions=${built.keyPathCollisions.length}\n`,
  );
}

function checkBytes(rendered, existing) {
  if (rendered !== existing) {
    fail("admissions_drift", `${SUCCESSOR_PATH} differs from render`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === "help") {
    process.stdout.write(
      "usage: m209_s02_build_admissions.mjs [--write|--check|--selftest] [--out PATH]\n",
    );
    return;
  }
  if (options.mode === "selftest") {
    selftest();
    return;
  }
  const outPath = checkOutTarget(options.out);
  const frozenText = readInput(FROZEN_ADMISSIONS_PATH);
  const registryText = readInput(REGISTRY_PATH);
  const artifactText = readInput(CANDIDATE_ARTIFACT_PATH);
  const artifact = JSON.parse(artifactText);
  const built = buildSuccessor({
    frozenText,
    artifact,
    registryText,
    frozenSha256: sha256Hex(frozenText),
    artifactSha256: sha256Hex(artifactText),
  });
  const heartbeat =
    `rows=${built.rows.length} candidate_backed=${built.candidateBacked} ` +
    `legacy=${built.legacy} punkt=0 key_path_collisions=${built.keyPathCollisions.length} drift=0`;
  process.stderr.write(`${heartbeat}\n`);
  if (options.mode === "check") {
    if (!existsSync(outPath)) {
      fail("admissions_drift", `missing ${options.out}`);
    }
    parseAdmissionSource(readFileSync(outPath, "utf8"), "committed");
    checkBytes(built.text, readFileSync(outPath, "utf8"));
    process.stdout.write(`M209_S02_ADMISSIONS_OK ${heartbeat}\n`);
    return;
  }
  const sibling = `${outPath}.tmp-m209-s02`;
  writeFileSync(sibling, built.text);
  renameSync(sibling, outPath);
  process.stdout.write(`M209_S02_ADMISSIONS_OK ${heartbeat}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof BuildError) {
      process.stderr.write(`M209_S02_BUILD_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
