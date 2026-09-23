// M209 S03 T04 contract: the fail-closed edition-delta leg of R070 for the
// named `cc:44-fz` chain.
//
// The contract is offline and corpus-gated: when the untracked licensed
// provider export resolves the named chain directory it independently counts
// the admitted edition files and their unparsed residual from the live listing;
// when it does not resolve it prints `M209_S03_CORPUS_ABSENT` and asserts the
// artifact-integrity and reconciliation blocks only. The walk itself is the
// Rust suite's job (and the emitter's own `--check` guarantee); this file never
// ports the admitted parser.
//
// It also asserts that the documented fail-closed code block, the emitted
// artifact and the Rust `EDITION_DELTA_FAIL_CLOSED_CODES` array carry exactly
// the same code sets.

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json";
const CONTRACT_PATH = "scripts/m209_s03_edition_chain_contract.test.mjs";
const RUST_MODULE = "crates/ln-consultant-parser/src/amendment_provenance.rs";
const RUST_SUITE = "crates/ln-consultant-parser/tests/m209_s03_edition_chain_walk.rs";
const T01_ARTIFACT = "prd/migration/rust-evidence/m209-s03-family-denominator.json";

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const CHAIN_TAIL = "exports/npa/law_2013-04-05_44-fz";

const SCHEMA = "law-nexus/r070-edition-delta/v1";
const KIND = "m209-s03-edition-delta";
const TASK = "T04";
const LIFECYCLE = "[bounded]";
const REQUIREMENT_ID = "R070";
const DISPOSITION = "active";
const DISPOSITION_DECISION = "D416";
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
const ALLOWED_TOKEN = /^[A-Za-z0-9_.:-]{1,64}$/;
const EXPECTED_EDITIONS = 118;
const TOP_N = 10;

// Provider prose markers that must never reach a count-only artifact.
const CORPUS_TEXT_MARKERS = ["consultantplus://", "<w:", "screenTip"];
// Ignored local overlays: never a durable evidence anchor.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const INPUT_IDS = ["t01_family_denominator"];

// The complete fail-closed code set. The documented block below is asserted to
// document exactly this set (no more, no less), and the same set is asserted
// equal to the artifact's `fail_closed_codes` field and to the Rust
// `EDITION_DELTA_FAIL_CLOSED_CODES` array.
const FAIL_CLOSED_CODES = [
  "input_absent",
  "input_hash_mismatch",
  "family_count_unsupported",
  "zero_denominator",
  "non_ascii_evidence",
  "raw_text_leak",
  "edition_dir_unreadable",
];

// ## Fail-closed codes (documented set; asserted equal to FAIL_CLOSED_CODES)
// DOCUMENTED_FAIL_CLOSED_BEGIN
// input_absent: a declared input path is absent from disk, or the tracked artifact is missing in `--check` mode.
// input_hash_mismatch: the live input pin or the chain digest differs from the tracked artifact, or the live edition-directory listing digest differs from the frozen T01 pin.
// family_count_unsupported: the declaration itself is unsupported — the directory subtree and the admitted edition filter disagree on the count, the admitted walk is not strictly ordered, the declared counts do not reconcile, a window does not name or reproduce its own two editions, the aggregate is not the sum of the windows, the top-N is not a bounded prefix, or the live inventory no longer reproduces the frozen T01 declaration.
// zero_denominator: the declared edition total is zero; a zero denominator is not a measurement.
// non_ascii_evidence: the artifact bytes carry a non-ASCII byte.
// raw_text_leak: a declared revision label is outside the count-only token rule.
// edition_dir_unreadable: the named chain edition directory cannot be listed or read, so the leg fails closed on an absence rather than measuring an empty chain.
// DOCUMENTED_FAIL_CLOSED_END

// The artifact must bound its own claims (D416 / D424 / D552 / D216).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not a normative text delta",
  "not commencement evidence",
  "never an amendment, an obligation or an applicability finding",
  "no corpus text is copied into this artifact",
  "does not close r070",
  "promotion gate",
  "d416",
  "frozen m201 r070 proof gate",
  "m208 startup surfaces stay absent",
  "zero denominator is not a measurement",
  "d552",
  "no new runtime vocabulary is minted",
  "d216",
];

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(root, relative), "utf8");
}

function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

function corpusExportDir() {
  const fromEnv = process.env[EXPORT_DIR_ENV];
  return typeof fromEnv === "string" && fromEnv.trim() !== ""
    ? fromEnv.trim()
    : EXPORT_DIR_DEFAULT;
}

function exportRoot() {
  return path.resolve(root, corpusExportDir(), EXPORT_ROOT_TAIL);
}

function chainDir() {
  return path.join(exportRoot(), CHAIN_TAIL);
}

// ---------------------------------------------------------------------------
// independent ports of the emitter's listing filter (counts only, no parser)
// ---------------------------------------------------------------------------

/// Mirrors `multi_edition::parse_edition_filename`: an admitted name whose
/// edition number or revision does not parse is an unparsed residual.
function parseEditionFilename(name) {
  if (!name.startsWith("edition-")) return null;
  const numberPart = name.slice("edition-".length).split("_")[0];
  if (!/^[0-9]+$/.test(numberPart)) return null;
  const revIndex = name.indexOf("_rev-");
  if (revIndex < 0) return null;
  const revision = name.slice(revIndex + "_rev-".length).split("_")[0];
  return [Number(numberPart), revision.replace(/^from-/, "")];
}

/// Immediate children of the chain directory: admitted names (extension `xml`
/// and prefix `edition-`) plus every remaining file. The admitted filter has
/// two clauses; an admitted name that does not parse is the declared residual.
function countChainFiles() {
  const dir = chainDir();
  const names = readdirSync(dir);
  let admitted = 0;
  let unparsed = 0;
  let otherFiles = 0;
  for (const name of names) {
    if (!statSync(path.join(dir, name)).isFile()) continue;
    if (!name.endsWith(".xml") || !name.startsWith("edition-")) {
      otherFiles += 1;
      continue;
    }
    admitted += 1;
    if (parseEditionFilename(name) === null) unparsed += 1;
  }
  return { admitted, unparsed, otherFiles, total: admitted + otherFiles };
}

// ---------------------------------------------------------------------------
// determinism digests (FNV-1a 64-bit, re-implemented from the tuple definition)
// ---------------------------------------------------------------------------

function fnv1a64(bytes) {
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  const mask = 0xffffffffffffffffn;
  for (const byte of bytes) {
    hash ^= BigInt(byte);
    hash = (hash * prime) & mask;
  }
  return hash.toString(16).padStart(16, "0");
}

function rowTuple(row) {
  return [
    row.edition_number,
    row.revision_label,
    row.hyperlink_count,
    row.classified_count,
    row.amends_count,
    row.cites_count,
    row.implements_count,
    row.unknown_count,
  ].join("|");
}

// ---------------------------------------------------------------------------
// fixtures and the live artifact
// ---------------------------------------------------------------------------

const liveText = readRepo(ARTIFACT);
const liveArtifact = JSON.parse(liveText);

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("the artifact is repository-relative, ASCII-only, non-empty and canonical", () => {
  assert.ok(isRepoRelative(ARTIFACT));
  assert.ok(liveText.length > 0, "the artifact must not be empty");
  assert.ok(!liveText.includes("\n"), "the artifact must be one canonical line");
  assert.ok(!/[\x80-\uffff]/.test(liveText), "the artifact must be pure ASCII");
  assert.equal(JSON.stringify(liveArtifact), liveText, "the artifact must be canonical JSON");
  assert.equal(liveText.trim(), liveText, "the artifact carries no surrounding whitespace");
});

test("the artifact carries the declared envelope", () => {
  assert.equal(liveArtifact.schema, SCHEMA);
  assert.equal(liveArtifact.schema_version, 4);
  assert.equal(liveArtifact.kind, KIND);
  assert.equal(liveArtifact.task, TASK);
  assert.equal(liveArtifact.lifecycle, LIFECYCLE);
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.requirement_id, REQUIREMENT_ID);
  assert.equal(liveArtifact.disposition, DISPOSITION);
  assert.equal(liveArtifact.disposition_decision, DISPOSITION_DECISION);
  assert.equal(liveArtifact.count_only, true);
  assert.equal(liveArtifact.ascii_only, true);
  assert.equal(liveArtifact.chain.chain_id, "cc:44-fz");
  assert.ok(isRepoRelative(liveArtifact.chain.edition_directory_relative_path));
  assert.equal(
    liveArtifact.chain.edition_directory_relative_path,
    `${corpusExportDir()}/${EXPORT_ROOT_TAIL}/${CHAIN_TAIL}`,
  );
  assert.equal(liveArtifact.chain.admitted_runtime, "multi_edition::process_editions_directory");
});

test("every declared input anchor is repository-relative, pinned and resolves on disk", () => {
  assert.ok(Array.isArray(liveArtifact.inputs) && liveArtifact.inputs.length > 0);
  assert.deepEqual(
    liveArtifact.inputs.map((pin) => pin.input_id).sort(),
    [...INPUT_IDS].sort(),
  );
  for (const pin of liveArtifact.inputs) {
    assert.ok(isRepoRelative(pin.relative_path), `${pin.input_id} path must be repository-relative`);
    assert.match(pin.input_sha256, SHA_PATTERN);
    assert.ok(Number.isInteger(pin.input_bytes) && pin.input_bytes > 0);
    const absolute = path.join(root, pin.relative_path);
    assert.ok(existsSync(absolute), `${pin.input_id} must resolve on disk`);
    const bytes = readFileSync(absolute);
    assert.equal(pin.input_bytes, bytes.length, `${pin.input_id} byte count must match`);
    assert.equal(
      pin.input_sha256,
      `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
      `${pin.input_id} pin must match live bytes`,
    );
  }
});

// ---------------------------------------------------------------------------
// reconciliation
// ---------------------------------------------------------------------------

test("the declared counts reconcile to the live inventory", () => {
  const denominator = liveArtifact.denominator;
  assert.equal(denominator.editions_total, EXPECTED_EDITIONS);
  assert.equal(
    denominator.editions_total,
    denominator.editions_processed +
      denominator.editions_unreadable +
      denominator.editions_unparsed_filename,
    "processed + unreadable + unparsed must equal the declared total",
  );
  assert.equal(
    denominator.windows_total,
    denominator.editions_processed - 1,
    "one window per adjacent edition pair",
  );
  assert.equal(liveArtifact.windows.length, denominator.windows_total);
  assert.equal(liveArtifact.editions.length, denominator.editions_processed);
  assert.equal(denominator.edition_dir_files_total, denominator.editions_total);
  assert.equal(
    liveArtifact.top_amends_windows.length,
    Math.min(denominator.windows_total, TOP_N),
    "the top-N must be a bounded prefix of the windows",
  );
});

test("the artifact reconciles with the tracked T01 declaration", () => {
  const denominator = liveArtifact.denominator;
  const t01 = JSON.parse(readRepo(T01_ARTIFACT));
  assert.equal(denominator.t01_editions_total, t01.chain.editions_total);
  assert.equal(denominator.t01_edition_matching, t01.chain.decomposition.edition_matching);
  assert.equal(
    denominator.edition_dir_listing_sha256,
    t01.chain.input_sha256,
    "the live listing digest must equal the frozen T01 chain pin",
  );
  assert.equal(denominator.t01_editions_total, denominator.editions_total);
  assert.equal(denominator.t01_edition_matching, denominator.editions_total);
});

test("every window reproduces the delta of its two adjacent editions", () => {
  const editions = liveArtifact.editions;
  assert.equal(liveArtifact.windows.length, editions.length - 1);
  for (let index = 0; index < liveArtifact.windows.length; index += 1) {
    const window = liveArtifact.windows[index];
    const from = editions[index];
    const to = editions[index + 1];
    assert.equal(window.from_edition, from.edition_number);
    assert.equal(window.to_edition, to.edition_number);
    assert.equal(window.revision_from, from.revision_label);
    assert.equal(window.revision_to, to.revision_label);
    assert.equal(window.amends_change, to.amends_count - from.amends_count);
    assert.equal(window.cites_change, to.cites_count - from.cites_count);
    assert.equal(window.implements_change, to.implements_count - from.implements_count);
    assert.equal(window.unknown_change, to.unknown_count - from.unknown_count);
  }
  // The declared aggregate is the sum of the declared windows.
  const sum = liveArtifact.windows.reduce(
    (acc, window) => ({
      amends_change: acc.amends_change + window.amends_change,
      cites_change: acc.cites_change + window.cites_change,
      implements_change: acc.implements_change + window.implements_change,
      unknown_change: acc.unknown_change + window.unknown_change,
    }),
    { amends_change: 0, cites_change: 0, implements_change: 0, unknown_change: 0 },
  );
  assert.deepEqual(liveArtifact.aggregate, sum);
});

test("every declared digest covers its own tuple and the whole chain", () => {
  for (const row of liveArtifact.editions) {
    assert.equal(
      row.digest,
      `fnv1a64:${fnv1a64(Buffer.from(rowTuple(row), "utf8"))}`,
      `edition ${row.edition_number} digest must cover its own tuple`,
    );
  }
  const stream = liveArtifact.editions.map((row) => `${row.digest}\n`).join("");
  assert.equal(
    liveArtifact.determinism.chain_digest,
    `fnv1a64:${fnv1a64(Buffer.from(stream, "utf8"))}`,
    "the chain digest must cover the ordered per-edition digests",
  );
  assert.equal(liveArtifact.determinism.diagnostic_only, true);
});

// ---------------------------------------------------------------------------
// count-only surface
// ---------------------------------------------------------------------------

test("every revision label is a count-only token and no corpus prose leaks", () => {
  for (const row of liveArtifact.editions) {
    assert.match(row.revision_label, ALLOWED_TOKEN, `edition ${row.edition_number} revision label`);
  }
  for (const window of liveArtifact.windows) {
    assert.match(window.revision_from, ALLOWED_TOKEN);
    assert.match(window.revision_to, ALLOWED_TOKEN);
  }
  for (const marker of CORPUS_TEXT_MARKERS) {
    assert.ok(!liveText.includes(marker), `the artifact must not carry ${marker}`);
  }
  assert.ok(!liveText.includes('"legislative"'), "no legislative value may be minted");
  for (const token of ["ActivationTrigger", "TransitionalResolver", "EvidenceAnchor", "LegislativeEffect"]) {
    assert.ok(!liveText.includes(token), `the artifact must not mint ${token}`);
  }
});

test("the record carries the D416, D424, D552 and D216 non-claims", () => {
  assert.ok(Array.isArray(liveArtifact.non_claims) && liveArtifact.non_claims.length > 0);
  const joined = liveArtifact.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `the non-claims must carry ${fragment}`);
  }
});

test("the emitter and its suite exist and stay inside this crate", () => {
  const module = readRepo(RUST_MODULE);
  for (const symbol of [
    /pub const EDITION_DELTA_FAIL_CLOSED_CODES/,
    /pub const EDITION_DELTA_SCHEMA/,
    /pub struct EditionDeltaEvidence/,
    /pub fn collect_edition_delta/,
    /pub fn validate_edition_delta/,
    /pub fn render_edition_delta/,
    /pub fn edition_delta_heartbeat/,
  ]) {
    assert.match(module, symbol);
  }
  const suite = readRepo(RUST_SUITE);
  for (const name of [
    /fn the_walk_reconciles_the_declared_chain_inventory/,
    /fn absent_chain_directory_and_out_of_repo_artifact_fail_closed/,
    /run_provenance/,
    /edition_dir_unreadable/,
  ]) {
    assert.match(suite, name);
  }
});

// ---------------------------------------------------------------------------
// documented code block equality
// ---------------------------------------------------------------------------

test("the documented code block equals the emitted and Rust code sets", () => {
  const source = readRepo(CONTRACT_PATH);
  const block = source.match(
    /\/\/ DOCUMENTED_FAIL_CLOSED_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_FAIL_CLOSED_END/,
  );
  assert.ok(block, "the documented fail-closed block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual([...documented].sort(), [...FAIL_CLOSED_CODES].sort());
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());

  const module = readRepo(RUST_MODULE);
  const rustBlock = module.match(
    /pub const EDITION_DELTA_FAIL_CLOSED_CODES: \[&str; \d+\] =\s*\[([\s\S]*?)\];/,
  );
  assert.ok(rustBlock, "the Rust EDITION_DELTA_FAIL_CLOSED_CODES array must exist");
  assert.deepEqual(
    [...rustBlock[1].matchAll(/"([a-z0-9_-]+)"/g)].map((match) => match[1]).sort(),
    [...FAIL_CLOSED_CODES].sort(),
    "the Rust array must equal the emitted set",
  );
});

// ---------------------------------------------------------------------------
// corpus-gated live re-derivation (counts only)
// ---------------------------------------------------------------------------

test("the live chain directory re-derives the declared inventory", () => {
  if (!existsSync(chainDir())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const observed = countChainFiles();
  const denominator = liveArtifact.denominator;

  assert.equal(
    observed.admitted,
    denominator.editions_total,
    "the admitted edition filter must reproduce the declared total",
  );
  assert.equal(
    observed.total,
    denominator.edition_dir_files_total,
    "the immediate children must reproduce the declared directory total",
  );
  assert.equal(
    observed.unparsed,
    denominator.editions_unparsed_filename,
    "the unparsed residual must reproduce",
  );
  assert.equal(observed.unparsed, 0, "zero admitted names may be unparsed");
  assert.equal(observed.otherFiles, 0, "the chain directory carries no non-admitted file");

  // The declared edition numbers and revision labels are exactly the admitted
  // filenames, sorted, without porting the parser.
  const names = readdirSync(chainDir())
    .filter((name) => name.endsWith(".xml") && name.startsWith("edition-"))
    .sort();
  const parsed = names.map(parseEditionFilename);
  assert.equal(parsed.length, liveArtifact.editions.length);
  for (let index = 0; index < parsed.length; index += 1) {
    assert.equal(parsed[index][0], liveArtifact.editions[index].edition_number);
    assert.equal(parsed[index][1], liveArtifact.editions[index].revision_label);
  }

  console.log(
    `[edition-chain] admitted=${observed.admitted} unparsed=${observed.unparsed} windows=${liveArtifact.windows.length} editions=${liveArtifact.editions.length}`,
  );
});

test("M209 S03 edition-chain markers", () => {
  assert.match(SCHEMA, /^law-nexus\/r070-edition-delta\/v1$/);
  assert.match(KIND, /^m209-s03-edition-delta$/);
  assert.equal(TASK, "T04");
  assert.equal(EXPECTED_EDITIONS, liveArtifact.denominator.editions_total);
  assert.equal(
    liveArtifact.denominator.editions_processed + liveArtifact.denominator.editions_unreadable,
    liveArtifact.denominator.editions_total,
  );
  assert.equal(liveArtifact.denominator.editions_unparsed_filename, 0);
});
