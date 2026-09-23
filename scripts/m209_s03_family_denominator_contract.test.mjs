// M209/S03 family-denominator contract (T01).
//
// Offline and fail-closed. The claim under test is a *denominator*, not an
// inventory count (D539/D547/D552): the `families` emitter re-derives, from one
// named corpus revision (the untracked, licensed provider export under
// consru_export/), the record count of each of the four provider manifests, the
// file inventory of the four provider export directories, and the
// edition-directory count of the named cc:44-fz chain — and pins every input by
// repository-relative path, byte count and sha256.
//
// The artifact is canonical compact ASCII JSON with a fixed top-level key order
// and no timestamps (D424), so `JSON.stringify(JSON.parse(text)) === text` and a
// whole-file byte compare in `--check` mode is the determinism proof.
//
// Everything measured here is re-derived from the live files, never trusted
// from prose: when the export dir resolves, the four manifest record counts, the
// four export inventories and the 44-FZ edition count are recomputed with this
// file's own walker and compared against the artifact, under a named code on
// drift; when it does not resolve, the corpus-gated block prints
// M209_S03_CORPUS_ABSENT and only the mandatory artifact-integrity block runs.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (frozen-path delta proof). No cargo, no
// network, no emitter re-run, no `.gsd` / ignored / absolute path is ever read
// as evidence, and this contract never writes a file.
//
// Run: node --test scripts/m209_s03_family_denominator_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s03-family-denominator.json";
const CONTRACT_PATH = "scripts/m209_s03_family_denominator_contract.test.mjs";
const RUST_MODULE = "crates/ln-consultant-parser/src/amendment_provenance.rs";
const RUST_BIN = "crates/ln-consultant-parser/src/bin/m209-amendment-provenance.rs";
const CARGO_MANIFEST = "crates/ln-consultant-parser/Cargo.toml";
const LIB_RS = "crates/ln-consultant-parser/src/lib.rs";

// Frozen M201 boundary: the T01 artifact must not widen it, and the pins must
// stay tracked and carry no worktree delta.
const FROZEN_M201 = [
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
];

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const CHAIN_ID = "cc:44-fz";
const EDITION_DIR_TAIL = "exports/npa/law_2013-04-05_44-fz";
const ROOT_KEY = "__root__";

const SCHEMA = "law-nexus/r070-family-denominator/v1";
const KIND = "m209-s03-family-denominator";
const LIFECYCLE = "[bounded]";
const REQUIREMENT_ID = "R070";
const DISPOSITION = "active";
const DISPOSITION_DECISION = "D416";
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;

// Fixed family table of the artifact: id, kind, path relative to the export root.
const FAMILY_TABLE = [
  ["manifest_layer1_44fz_and_amending_laws", "manifest", "manifest_layer1_44fz_and_amending_laws.jsonl"],
  ["manifest_layer2_subordinate_normative_acts", "manifest", "manifest_layer2_subordinate_normative_acts.jsonl"],
  ["manifest_layer3_court_practice_2025_2026", "manifest", "manifest_layer3_court_practice_2025_2026.jsonl"],
  ["manifest_layer3_fas_practice_2025_2026", "manifest", "manifest_layer3_fas_practice_2025_2026.jsonl"],
  ["exports_npa", "directory", "exports/npa"],
  ["exports_xml", "directory", "exports/xml"],
  ["exports_courts", "directory", "exports/courts"],
  ["exports_fas", "directory", "exports/fas"],
];

// Regression anchors for the accepted corpus revision (D552). The emitter never
// hardcodes these — it re-derives them live — but the contract anchors them so a
// silent export change cannot pass through as a revised denominator without a
// decision (D552 is explicitly revisable when the corpus revision changes).
const ANCHORED_TOTALS = {
  manifest_layer1_44fz_and_amending_laws: 122,
  manifest_layer2_subordinate_normative_acts: 921,
  manifest_layer3_court_practice_2025_2026: 5625,
  manifest_layer3_fas_practice_2025_2026: 30493,
  exports_npa: 916,
  exports_xml: 6803,
  exports_courts: 5667,
  exports_fas: 30399,
};
const ANCHORED_EDITIONS_TOTAL = 118;

// The complete fail-closed code set. The `## Fail-closed codes` comment block
// below is asserted to document exactly this set (no more, no less), and the
// same set is asserted equal to the artifact's `fail_closed_codes` field and to
// the Rust `FAMILY_DENOMINATOR_CODES` array.
const EMITTABLE_CODES = [
  "input_absent",
  "input_hash_mismatch",
  "family_count_unsupported",
  "zero_denominator",
  "non_ascii_evidence",
  "raw_text_leak",
  "edition_dir_unreadable",
];

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// input_absent: a declared family input path or the named chain edition directory is absent from disk, or the tracked artifact is missing in `--check` mode.
// input_hash_mismatch: the live input pin (sha256 or byte count) differs from the pin recorded in the tracked artifact, or a recorded pin is malformed.
// family_count_unsupported: the declaration itself is unsupported — schema, kind, lifecycle, requirement or disposition drift, a missing or duplicated family, a decomposition that does not sum to its declared total, a live record total that differs from the tracked total, or a family absent from the tracked artifact.
// zero_denominator: a declared total is zero or not a positive integer; a zero denominator is not a measurement.
// non_ascii_evidence: the artifact bytes carry a non-ASCII byte, or a decomposition key is not ASCII.
// raw_text_leak: the artifact carries provider prose (a corpus text marker) or a decomposition key outside the count-only token rule.
// edition_dir_unreadable: the named chain edition directory exists but cannot be read as a directory, so the chain denominator cannot be re-derived.
// DOCUMENTED_CODES_END

// Provider prose markers that must never reach a count-only artifact.
const CORPUS_TEXT_MARKERS = ["consultantplus://", "<w:", "screenTip"];

// Ignored local overlays: never a durable evidence anchor.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The artifact must bound its own claims (D416 / D539 / D552).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "scoped family denominator",
  "not every-edition coverage",
  "no corpus text is copied",
  "frozen m201 r070 proof gate is not widened",
  "zero denominator is not a measurement",
  "r070 stays active (d416)",
  "no m202 inventory count may stand as a quantifier",
  "d539",
];

const ALLOWED_KEY_TOKEN = /^[A-Za-z0-9_.:-]{1,64}$/;

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

// ---------------------------------------------------------------------------
// live re-derivation (mirrors crates/ln-consultant-parser/amendment_provenance.rs)
// ---------------------------------------------------------------------------

function walkFiles(directory, base = directory, out = []) {
  const entries = readdirSync(directory, { withFileTypes: true }).sort((left, right) =>
    left.name < right.name ? -1 : left.name > right.name ? 1 : 0,
  );
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walkFiles(absolute, base, out);
    } else if (entry.isFile()) {
      out.push({
        relative: path.relative(base, absolute).split(path.sep).join("/"),
        size: statSync(absolute).size,
      });
    }
  }
  return out;
}

function inventoryDirectory(directory) {
  const files = walkFiles(directory).sort((left, right) =>
    left.relative < right.relative ? -1 : left.relative > right.relative ? 1 : 0,
  );
  const digest = createHash("sha256");
  let inputBytes = 0;
  for (const file of files) {
    inputBytes += file.size;
    digest.update(`${file.relative}\u0000${file.size}\n`);
  }
  return {
    records_total: files.length,
    input_bytes: inputBytes,
    input_sha256: `sha256:${digest.digest("hex")}`,
  };
}

function deriveLive() {
  const exportDir = exportRoot();
  const families = {};
  for (const [familyId, kind, tail] of FAMILY_TABLE) {
    const absolute = path.join(exportDir, tail);
    if (kind === "manifest") {
      const bytes = readFileSync(absolute);
      families[familyId] = {
        input_bytes: bytes.length,
        input_sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
        records_total: bytes
          .toString("utf8")
          .split("\n")
          .filter((line) => line.trim() !== "").length,
      };
    } else {
      families[familyId] = inventoryDirectory(absolute);
    }
  }
  const chainDirectory = path.join(exportDir, EDITION_DIR_TAIL);
  const chainInventory = inventoryDirectory(chainDirectory);
  return {
    families,
    chain: { ...chainInventory, editions_total: chainInventory.records_total },
    editionDirExists: existsSync(chainDirectory),
    editionDirReadable: statSync(chainDirectory).isDirectory(),
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateFamilyDenominator(artifact, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ code: name, detail });
  const text = env.artifactText ?? JSON.stringify(artifact);

  // 1. raw bytes: ASCII-only, count-only.
  if (text.length === 0) code("non_ascii_evidence", "artifact is empty");
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_evidence", `non-ascii character at index ${offending}`);
  for (const marker of CORPUS_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `corpus text marker ${marker}`);
  }

  // 2. envelope.
  if (artifact?.schema !== SCHEMA) code("family_count_unsupported", "schema mismatch");
  if (artifact?.kind !== KIND) code("family_count_unsupported", "kind mismatch");
  if (artifact?.lifecycle !== LIFECYCLE) code("family_count_unsupported", "lifecycle mismatch");
  if (artifact?.authoritative !== false) {
    code("family_count_unsupported", "authoritative must be false");
  }
  if (
    artifact?.requirement_id !== REQUIREMENT_ID ||
    artifact?.disposition !== DISPOSITION ||
    artifact?.disposition_decision !== DISPOSITION_DECISION
  ) {
    code("family_count_unsupported", "R070 disposition drift");
  }
  if (artifact?.count_only !== true || artifact?.ascii_only !== true) {
    code("family_count_unsupported", "count_only and ascii_only must both be true");
  }
  if (typeof artifact?.count_basis !== "string" || artifact.count_basis.trim() === "") {
    code("family_count_unsupported", "count_basis is missing");
  }
  if (!Array.isArray(artifact?.fail_closed_codes)) {
    code("family_count_unsupported", "fail_closed_codes is missing");
  } else if (sortJoin(artifact.fail_closed_codes) !== sortJoin(EMITTABLE_CODES)) {
    code("family_count_unsupported", "fail_closed_codes drift");
  }

  // 3. non-claims.
  if (!Array.isArray(artifact?.non_claims) || artifact.non_claims.length === 0) {
    code("family_count_unsupported", "non_claims is missing");
  } else {
    const joined = artifact.non_claims.join(" ").toLowerCase();
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      if (!joined.includes(fragment)) code("family_count_unsupported", `non-claim missing: ${fragment}`);
    }
  }

  // 4. families.
  if (!Array.isArray(artifact?.families) || artifact.families.length === 0) {
    code("family_count_unsupported", "families is missing");
  } else {
    const seen = new Set();
    for (const family of artifact.families) {
      const id = typeof family?.family_id === "string" ? family.family_id : "<unnamed>";
      if (seen.has(id)) code("family_count_unsupported", `duplicate family ${id}`);
      seen.add(id);
      if (!isRepoRelative(family?.input_relative_path)) {
        code("family_count_unsupported", `family ${id} input path is not repository-relative`);
      }
      if (family?.kind !== "manifest" && family?.kind !== "directory") {
        code("family_count_unsupported", `family ${id} kind is not manifest or directory`);
      }
      if (typeof family?.input_sha256 !== "string" || !SHA_PATTERN.test(family.input_sha256)) {
        code("input_hash_mismatch", `family ${id} sha256 pin is malformed`);
      }
      if (!Number.isInteger(family?.input_bytes) || family.input_bytes <= 0) {
        code("input_hash_mismatch", `family ${id} byte pin is malformed`);
      }
      if (!Number.isInteger(family?.records_total) || family.records_total <= 0) {
        code("zero_denominator", `family ${id} declared total is not a positive integer`);
      }
      checkDecomposition(code, `family ${id}`, family?.decomposition, family?.records_total);
      if (typeof env.exists === "function" && !env.exists(family?.input_relative_path)) {
        code("input_absent", `family ${id} input is absent: ${family?.input_relative_path}`);
      }
    }
  }

  // 5. named chain.
  const chain = artifact?.chain;
  if (!chain || typeof chain !== "object") {
    code("family_count_unsupported", "chain block is missing");
  } else {
    if (chain.chain_id !== CHAIN_ID) code("family_count_unsupported", "chain id drift");
    if (!isRepoRelative(chain.edition_directory_relative_path)) {
      code("family_count_unsupported", "chain edition path is not repository-relative");
    }
    if (typeof chain.input_sha256 !== "string" || !SHA_PATTERN.test(chain.input_sha256)) {
      code("input_hash_mismatch", "chain sha256 pin is malformed");
    }
    if (!Number.isInteger(chain.input_bytes) || chain.input_bytes <= 0) {
      code("input_hash_mismatch", "chain byte pin is malformed");
    }
    if (!Number.isInteger(chain.editions_total) || chain.editions_total <= 0) {
      code("zero_denominator", "chain edition total is not a positive integer");
    }
    checkDecomposition(code, "chain", chain.decomposition, chain.editions_total);
    if (env.editionDirExists === false) {
      code("edition_dir_unreadable", "chain edition directory is absent");
    } else if (env.editionDirReadable === false) {
      code("edition_dir_unreadable", "chain edition directory is not a readable directory");
    }
  }

  // 6. live re-derivation.
  const live = env.live;
  if (live) {
    for (const family of artifact?.families ?? []) {
      const observed = live.families?.[family?.family_id];
      if (!observed) continue;
      if (
        observed.input_bytes !== family.input_bytes ||
        observed.input_sha256 !== family.input_sha256
      ) {
        code("input_hash_mismatch", `family ${family.family_id} live pin differs`);
      }
      if (observed.records_total !== family.records_total) {
        code("family_count_unsupported", `family ${family.family_id} live total differs`);
      }
    }
    if (live.chain) {
      if (
        live.chain.input_bytes !== chain?.input_bytes ||
        live.chain.input_sha256 !== chain?.input_sha256
      ) {
        code("input_hash_mismatch", "chain live pin differs");
      }
      if (live.chain.editions_total !== chain?.editions_total) {
        code("family_count_unsupported", "chain live edition total differs");
      }
    }
  }

  return { ok: errors.length === 0, errors };
}

function checkDecomposition(code, scope, decomposition, declaredTotal) {
  if (!decomposition || typeof decomposition !== "object" || Array.isArray(decomposition)) {
    code("family_count_unsupported", `${scope} decomposition is missing`);
    return;
  }
  const parts = Object.entries(decomposition);
  if (parts.length === 0) {
    code("family_count_unsupported", `${scope} decomposition is empty`);
    return;
  }
  let sum = 0;
  for (const [key, value] of parts) {
    if (!Number.isInteger(value) || value < 0) {
      code("family_count_unsupported", `${scope} part ${key} is not a count`);
      continue;
    }
    sum += value;
    if (!/^[\x20-\x7f]*$/.test(key)) {
      code("non_ascii_evidence", `${scope} key is not ascii`);
    } else if (!ALLOWED_KEY_TOKEN.test(key)) {
      code("raw_text_leak", `${scope} key ${key} is outside the count-only token rule`);
    }
  }
  if (Number.isInteger(declaredTotal) && declaredTotal > 0 && sum !== declaredTotal) {
    code(
      "family_count_unsupported",
      `${scope} decomposition sums to ${sum}, not the declared total ${declaredTotal}`,
    );
  }
}

function sortJoin(values) {
  return [...values].sort().join(",");
}

function codesFor(result) {
  return [...new Set(result.errors.map((error) => error.code))];
}

function expectCode(result, name) {
  assert.ok(
    codesFor(result).includes(name),
    `expected ${name}, got ${JSON.stringify(result.errors)}`,
  );
  assert.equal(result.ok, false, `${name} must fail closed`);
  return result;
}

// ---------------------------------------------------------------------------
// fixtures and the live artifact
// ---------------------------------------------------------------------------

const liveText = readRepo(ARTIFACT);
const liveArtifact = JSON.parse(liveText);

function cloneArtifact() {
  return JSON.parse(liveText);
}

function artifactTextOf(artifact) {
  return JSON.stringify(artifact);
}

function liveEnv() {
  const env = { artifactText: liveText, exists: (value) => existsSync(path.join(root, value)) };
  if (existsSync(exportRoot())) {
    const derived = deriveLive();
    env.live = { families: derived.families, chain: derived.chain };
    env.editionDirExists = derived.editionDirExists;
    env.editionDirReadable = derived.editionDirReadable;
  }
  return env;
}

// ---------------------------------------------------------------------------
// artifact integrity (always runs, corpus or not)
// ---------------------------------------------------------------------------

test("the artifact is repository-relative, ASCII-only, non-empty and canonical", () => {
  assert.ok(existsSync(path.join(root, ARTIFACT)), `${ARTIFACT} must exist`);
  assert.ok(isRepoRelative(ARTIFACT), "the artifact path must be repository-relative");
  assert.notEqual(liveText.length, 0, "the artifact must be non-empty");
  assert.ok(liveText.isWellFormed(), "the artifact must be well-formed UTF-8");
  assert.equal(liveText, liveText.normalize("NFC"), "the artifact must be NFC-stable");
  assert.match(liveText, /^[\x00-\x7f]*$/, "the artifact must be pure ASCII");
  assert.ok(!liveText.endsWith("\n"), "canonical bytes carry no trailing newline");
  assert.ok(!liveText.includes("\n"), "canonical bytes are a single line");
  assert.equal(
    JSON.stringify(JSON.parse(liveText)),
    liveText,
    "the artifact must round-trip to identical canonical compact bytes (D424)",
  );
  for (const marker of CORPUS_TEXT_MARKERS) {
    assert.ok(!liveText.includes(marker), `the artifact must not carry ${marker}`);
  }
});

test("every declared input anchor is repository-relative and exists", () => {
  for (const family of liveArtifact.families) {
    assert.ok(
      isRepoRelative(family.input_relative_path),
      `family ${family.family_id} path must be repository-relative`,
    );
    assert.ok(
      existsSync(path.join(root, family.input_relative_path)),
      `family ${family.family_id} input must exist: ${family.input_relative_path}`,
    );
  }
  assert.ok(
    isRepoRelative(liveArtifact.chain.edition_directory_relative_path),
    "the chain edition path must be repository-relative",
  );
  assert.ok(
    existsSync(path.join(root, liveArtifact.chain.edition_directory_relative_path)),
    "the chain edition directory must exist",
  );
});

test("the artifact enumerates the fixed family table", () => {
  assert.deepEqual(
    liveArtifact.families.map((family) => [family.family_id, family.kind]),
    FAMILY_TABLE.map(([familyId, kind]) => [familyId, kind]),
  );
  for (const family of liveArtifact.families) {
    const expectedTail = FAMILY_TABLE.find(([familyId]) => familyId === family.family_id)[2];
    assert.ok(
      family.input_relative_path.endsWith(`/${expectedTail}`),
      `family ${family.family_id} must anchor ${expectedTail}`,
    );
  }
  assert.equal(
    liveArtifact.chain.edition_directory_relative_path.endsWith(`/${EDITION_DIR_TAIL}`),
    true,
  );
});

test("every decomposition sums to its declared total", () => {
  for (const family of liveArtifact.families) {
    const sum = Object.values(family.decomposition).reduce((total, value) => total + value, 0);
    assert.equal(
      sum,
      family.records_total,
      `family ${family.family_id} decomposition must sum to ${family.records_total}`,
    );
    assert.ok(family.records_total > 0, `family ${family.family_id} must not declare zero`);
  }
  const chainSum = Object.values(liveArtifact.chain.decomposition).reduce(
    (total, value) => total + value,
    0,
  );
  assert.equal(chainSum, liveArtifact.chain.editions_total, "chain decomposition must sum");
});

test("the record carries the D416 and D539 non-claims", () => {
  const joined = liveArtifact.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `non-claim fragment missing: ${fragment}`);
  }
  assert.equal(liveArtifact.disposition, "active");
  assert.equal(liveArtifact.disposition_decision, "D416");
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.lifecycle, "[bounded]");
  assert.equal(liveArtifact.count_only, true);
  assert.equal(liveArtifact.ascii_only, true);
});

test("the artifact-integrity block passes for the tracked artifact", () => {
  const result = validateFamilyDenominator(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `artifact errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
});

// ---------------------------------------------------------------------------
// dependency and wiring guards
// ---------------------------------------------------------------------------

test("the emitter exists, is wired additively and adds no dependency", () => {
  assert.match(readRepo(LIB_RS), /pub mod amendment_provenance;/);
  assert.match(
    readRepo(CARGO_MANIFEST),
    /name = "m209-amendment-provenance"[\s\S]*?path = "src\/bin\/m209-amendment-provenance\.rs"/,
  );
  const bin = readRepo(RUST_BIN);
  assert.match(bin, /parse_provenance_args/);
  assert.match(bin, /run_provenance/);

  const dependencies = readRepo(CARGO_MANIFEST)
    .split("[dependencies]")[1]
    .split("[[bin]]")[0]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "" && !line.startsWith("#"));
  assert.deepEqual(
    dependencies.map((line) => line.split("=")[0].trim()).sort(),
    ["ln-decode", "ln-kb-ontology", "ln-temporal", "rusqlite"],
    "no rust dependency may be added by this task",
  );

  const module = readRepo(RUST_MODULE);
  assert.match(module, /pub const FAMILY_DENOMINATOR_CODES/);
  assert.match(module, /pub fn collect_family_denominator/);
  assert.match(module, /pub fn render_family_denominator/);
  assert.match(module, /pub fn ensure_out_containment/);
});

test("the frozen M201 pins are tracked and carry no worktree delta", () => {
  const tracked = execFileSync("git", ["ls-files", "--error-unmatch", ...FROZEN_M201], {
    cwd: root,
    encoding: "utf8",
  })
    .split("\n")
    .filter((line) => line !== "");
  assert.deepEqual(tracked.sort(), [...FROZEN_M201].sort());
  const status = execFileSync("git", ["status", "--porcelain", "--", ...FROZEN_M201], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(status.trim(), "", `frozen M201 paths carry a worktree delta: ${status}`);
});

// ---------------------------------------------------------------------------
// code coverage: one empirical mutation per documented fail-closed code
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "input_absent",
    mutate: (artifact) => {
      artifact.families[0].input_relative_path = "prd/migration/rust-evidence/absent-manifest.jsonl";
    },
    env: () => ({
      exists: (value) =>
        !value.endsWith("absent-manifest.jsonl") && existsSync(path.join(root, value)),
    }),
  },
  {
    code: "input_hash_mismatch",
    mutate: () => {},
    env: (artifact) => ({
      live: {
        families: {
          [artifact.families[0].family_id]: {
            input_bytes: artifact.families[0].input_bytes,
            input_sha256: `sha256:${"0".repeat(64)}`,
            records_total: artifact.families[0].records_total,
          },
        },
      },
    }),
  },
  {
    code: "family_count_unsupported",
    mutate: (artifact) => {
      artifact.families[0].records_total += 1;
    },
    env: {},
  },
  {
    code: "zero_denominator",
    mutate: (artifact) => {
      artifact.families[0].records_total = 0;
      artifact.families[0].decomposition = { zero: 0 };
    },
    env: {},
  },
  {
    code: "non_ascii_evidence",
    mutate: (artifact) => {
      const parts = Object.entries(artifact.families[0].decomposition);
      artifact.families[0].decomposition = {
        [parts[0][0]]: parts[0][1],
        "\u041f\u0420\u0410\u0412\u041e": parts[1] ? parts[1][1] : 0,
      };
    },
    env: {},
  },
  {
    code: "raw_text_leak",
    mutate: (artifact) => {
      const parts = Object.entries(artifact.families[0].decomposition);
      artifact.families[0].decomposition = {
        [parts[0][0]]: parts[0][1],
        "consultantplus://offline/ref=DEADBEEF": parts[1] ? parts[1][1] : 0,
      };
    },
    env: {},
  },
  {
    code: "edition_dir_unreadable",
    mutate: () => {},
    env: () => ({ editionDirExists: false }),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const artifact = cloneArtifact();
    entry.mutate(artifact);
    const env = {
      artifactText: artifactTextOf(artifact),
      ...(typeof entry.env === "function" ? entry.env(artifact) : {}),
    };
    const result = validateFamilyDenominator(artifact, env);
    expectCode(result, entry.code);
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

test("the documented code block equals the emitted code set", () => {
  const source = readRepo(CONTRACT_PATH);
  const block = source.match(/\/\/ DOCUMENTED_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented codes block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documented.sort(), [...EMITTABLE_CODES].sort());

  assert.deepEqual(
    [...liveArtifact.fail_closed_codes].sort(),
    [...EMITTABLE_CODES].sort(),
    "the artifact must declare exactly the emitted code set",
  );

  const rustBlock = readRepo(RUST_MODULE).match(
    /pub const FAMILY_DENOMINATOR_CODES: \[&str; \d+\] = \[([\s\S]*?)\];/,
  );
  assert.ok(rustBlock, "the Rust FAMILY_DENOMINATOR_CODES array must exist");
  const rustCodes = [...rustBlock[1].matchAll(/"([a-z0-9_]+)"/g)].map((match) => match[1]);
  assert.deepEqual(
    rustCodes.sort(),
    [...EMITTABLE_CODES].sort(),
    "the Rust emitted code set must equal the documented contract set",
  );
});

// ---------------------------------------------------------------------------
// negative paths beyond the code-coverage table
// ---------------------------------------------------------------------------

test("negative: an unsupported envelope fails closed", () => {
  const cases = [
    (artifact) => {
      artifact.schema = "law-nexus/other/v1";
    },
    (artifact) => {
      artifact.lifecycle = "[certified]";
    },
    (artifact) => {
      artifact.authoritative = true;
    },
    (artifact) => {
      artifact.disposition = "validated";
    },
    (artifact) => {
      artifact.disposition_decision = "D999";
    },
    (artifact) => {
      artifact.count_only = false;
    },
    (artifact) => {
      delete artifact.non_claims;
    },
    (artifact) => {
      artifact.fail_closed_codes = ["input_absent"];
    },
    (artifact) => {
      artifact.families = [];
    },
    (artifact) => {
      artifact.families[1].family_id = artifact.families[0].family_id;
    },
    (artifact) => {
      artifact.chain.chain_id = "cc:other";
    },
    (artifact) => {
      delete artifact.chain;
    },
    (artifact) => {
      artifact.families[0].input_sha256 = "sha256:XYZ";
    },
    (artifact) => {
      artifact.families[0].input_relative_path = "/tmp/absolute.jsonl";
    },
    (artifact) => {
      artifact.families[0].input_relative_path = "../../escape.jsonl";
    },
  ];
  for (const mutate of cases) {
    const artifact = cloneArtifact();
    mutate(artifact);
    const result = validateFamilyDenominator(artifact, { artifactText: artifactTextOf(artifact) });
    assert.equal(result.ok, false, `${mutate} must fail closed`);
  }
});

// ---------------------------------------------------------------------------
// corpus-gated re-derivation
// ---------------------------------------------------------------------------

test("the live corpus re-derives the declared denominator", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    console.log(`export_root=${path.relative(root, exportRoot())}`);
    const result = validateFamilyDenominator(liveArtifact, { artifactText: liveText });
    assert.deepEqual(result.errors, [], "the artifact-integrity block must still hold");
    return;
  }

  const derived = deriveLive();
  for (const family of liveArtifact.families) {
    const observed = derived.families[family.family_id];
    assert.ok(observed, `family ${family.family_id} must be re-derivable`);
    assert.equal(
      observed.records_total,
      family.records_total,
      `family ${family.family_id} live record count drifted`,
    );
    assert.equal(
      observed.input_bytes,
      family.input_bytes,
      `family ${family.family_id} live byte count drifted`,
    );
    assert.equal(
      observed.input_sha256,
      family.input_sha256,
      `family ${family.family_id} live sha256 pin drifted`,
    );
    assert.equal(
      observed.records_total,
      ANCHORED_TOTALS[family.family_id],
      `family ${family.family_id} live count left the anchored revision`,
    );
  }

  assert.equal(
    derived.chain.editions_total,
    liveArtifact.chain.editions_total,
    "the 44-FZ edition-directory count drifted",
  );
  assert.equal(
    derived.chain.editions_total,
    ANCHORED_EDITIONS_TOTAL,
    "the 44-FZ edition count left the anchored revision",
  );
  assert.equal(
    derived.chain.input_sha256,
    liveArtifact.chain.input_sha256,
    "the 44-FZ edition-directory listing pin drifted",
  );

  const result = validateFamilyDenominator(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `live errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S03_CORPUS_PRESENT");
  console.log(`manifest_layer1=${derived.families.manifest_layer1_44fz_and_amending_laws.records_total}`);
  console.log(`manifest_layer2=${derived.families.manifest_layer2_subordinate_normative_acts.records_total}`);
  console.log(`manifest_layer3_court=${derived.families.manifest_layer3_court_practice_2025_2026.records_total}`);
  console.log(`manifest_layer3_fas=${derived.families.manifest_layer3_fas_practice_2025_2026.records_total}`);
  console.log(`exports_npa=${derived.families.exports_npa.records_total}`);
  console.log(`exports_xml=${derived.families.exports_xml.records_total}`);
  console.log(`exports_courts=${derived.families.exports_courts.records_total}`);
  console.log(`exports_fas=${derived.families.exports_fas.records_total}`);
  console.log(`chain_editions=${derived.chain.editions_total}`);
});

test("drift in any declared input is detected under a named code", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const derived = deriveLive();
  const drifted = cloneArtifact();
  drifted.families[0].input_sha256 = `sha256:${"1".repeat(64)}`;
  const live = { families: { [drifted.families[0].family_id]: derived.families[drifted.families[0].family_id] } };
  expectCode(
    validateFamilyDenominator(drifted, { artifactText: artifactTextOf(drifted), live }),
    "input_hash_mismatch",
  );

  const miscounted = cloneArtifact();
  miscounted.families[0].records_total += 1;
  const liveTotals = {
    families: {
      [miscounted.families[0].family_id]: {
        ...derived.families[miscounted.families[0].family_id],
        records_total: derived.families[miscounted.families[0].family_id].records_total,
      },
    },
  };
  expectCode(
    validateFamilyDenominator(miscounted, { artifactText: artifactTextOf(miscounted), live: liveTotals }),
    "family_count_unsupported",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the family-denominator contract holds)
// ---------------------------------------------------------------------------

test("M209 S03 family-denominator markers", () => {
  const result = validateFamilyDenominator(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S03_FAMILY_DENOMINATOR_OK");
  console.log("M209_S03_FAMILY_DENOMINATOR_SUM_OK");
  console.log("M209_S03_FAMILY_DENOMINATOR_CODES_OK");
  console.log(`families=${liveArtifact.families.length}`);
  console.log(`editions=${liveArtifact.chain.editions_total}`);
  console.log(`fail_closed_codes=${EMITTABLE_CODES.length}`);
});
