// M209/S03 amending-act and affected-provision contract (T02).
//
// Offline and fail-closed. The claim under test is the *amending-act and
// affected-provision leg* of R070 for the named cc:44-fz chain: the explicit
// `amends` edges of the catalog relation run rooted at cp:LAW:508812, joined by
// document_key to the layer1 manifest and by the declared identity pair (act
// number, act date) to the act exports under exports/npa, with the catalog
// edition_id hash as the corroborating field. Every edge lands in exactly one
// outcome, the outcome partition sums to the declared denominator, and statya
// level candidate provision targets are resolved against the chain needle of
// prd/architecture/kb-hierarchy-registry.yaml.
//
// The artifact is canonical compact ASCII JSON with a fixed top-level key order
// and no timestamps (D424), so `JSON.stringify(JSON.parse(text)) === text` and a
// whole-file byte compare in `--check` mode is the determinism proof.
//
// Nothing measured here is trusted from prose: when the export dir resolves,
// this file re-derives — with its own walker, its own port of the admitted
// hyperlink scanner and its own read-only `node:sqlite` handle — the relation
// run, the 120 explicit `amends` edges, the layer1 denominators, the registry
// bindings, the exports/npa inventory and every per-edge resolution outcome,
// and compares them against the artifact under a named code on drift. When the
// export dir does not resolve, the corpus-gated block prints
// M209_S03_CORPUS_ABSENT and only the mandatory artifact-integrity block runs.
//
// Subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof) and `git status --porcelain` (frozen-path delta proof). The catalog is
// opened read-only through the built-in `node:sqlite` module — no new
// dependency, no cargo, no network, no emitter re-run — and this contract never
// writes a file and never echoes corpus text.
//
// Run: node --test scripts/m209_s03_amends_provision_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
const CONTRACT_PATH = "scripts/m209_s03_amends_provision_contract.test.mjs";
const RUST_MODULE = "crates/ln-consultant-parser/src/amendment_provenance.rs";
const RUST_BIN = "crates/ln-consultant-parser/src/bin/m209-amendment-provenance.rs";
const CARGO_MANIFEST = "crates/ln-consultant-parser/Cargo.toml";
const LIB_RS = "crates/ln-consultant-parser/src/lib.rs";
const CATALOG_SQLITE = "crates/ln-consultant-parser/src/catalog_sqlite.rs";
const REGISTRY = "prd/architecture/kb-hierarchy-registry.yaml";

// Frozen M201 boundary: this artifact must not widen it, and the pins must stay
// tracked and carry no worktree delta.
const FROZEN_M201 = [
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
];

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const LAYER1_MANIFEST_TAIL = "manifest_layer1_44fz_and_amending_laws.jsonl";
const NPA_TAIL = "exports/npa";
const CATALOG_LINKS_PREFIX = "catalog-links-";
const CATALOG_LINKS_SUFFIX = ".sqlite";

const SCHEMA = "law-nexus/r070-amending-act-provision/v1";
const KIND = "m209-s03-amending-act-provision";
const TASK = "T02";
const LIFECYCLE = "[bounded]";
const REQUIREMENT_ID = "R070";
const DISPOSITION = "active";
const DISPOSITION_DECISION = "D416";
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;

const REGISTRY_NEEDLE = "law_2013-04-05_44-fz";
const CHAIN_ROOT_SOURCE_ID = "cp:LAW:508812";
const CHAIN_PROFILE = "procurement-core";
const CHAIN_STATUS = "complete";
const AMENDS_EDGE_LIMIT = 4096;

// The declared reference rule: a hyperlink names the 44-FZ Work when its own
// text or its paragraph carries one of these two needles.
const NEEDLES = ["44-ФЗ", "О контрактной системе"];

const INPUT_IDS = ["catalog_links_sqlite", "layer1_manifest", "kb_hierarchy_registry"];

// The outcome vocabulary: every edge lands in exactly one of these.
const REASON_CODES = [
  "resolved-provision",
  "provision-not-in-registry",
  "no-statya-reference",
  "target-not-44fz",
  "unparsed-act",
  "no-export-file",
  "no-layer1-record",
];

// The complete fail-closed code set: the six structural codes shared with the
// families mode plus every outcome code, because an outcome whose recorded
// counts do not justify it is itself a refusal.
const FAIL_CLOSED_CODES = [
  "input_absent",
  "input_hash_mismatch",
  "family_count_unsupported",
  "zero_denominator",
  "non_ascii_evidence",
  "raw_text_leak",
  "no-layer1-record",
  "no-export-file",
  "unparsed-act",
  "target-not-44fz",
  "provision-not-in-registry",
  "no-statya-reference",
  "resolved-provision",
];

// Regression anchors for the accepted corpus revision. The emitter never
// hardcodes these — it re-derives them live and refuses on drift — but the
// contract anchors them so a silent export change cannot pass through as a
// revised measurement without a decision.
const ANCHORED = {
  amends_edges_total: 120,
  layer1_records_total: 122,
  layer1_core_acts: 1,
  layer1_amending_acts: 121,
  registry_statya_bindings: 94,
  registry_glava_bindings: 8,
  registry_bindings_total: 102,
  distinct_statya_refs: 30,
  distinct_statya_refs_resolved: 26,
  "resolved-provision": 40,
  "no-statya-reference": 26,
  "target-not-44fz": 11,
  "provision-not-in-registry": 1,
  "unparsed-act": 42,
  "no-export-file": 0,
  "no-layer1-record": 0,
};

/// Total parsed hyperlink count of the accepted revision (the sum over every
/// pinned act export); it is a structural cross-check, not a denominator.
const ANCHORED_EXPORT_LINKS_TOTAL = 4008;
/// File inventory of the single-act export directory of the accepted revision.
const ANCHORED_NPA_FILES_TOTAL = 916;

// ## Reason codes (documented set; asserted equal to REASON_CODES)
// DOCUMENTED_REASON_CODES_BEGIN
// resolved-provision: the pinned act export carries a hyperlink naming the 44-FZ Work whose leading statya reference binds to the chain needle of the registry.
// provision-not-in-registry: the pinned act export carries such a hyperlink and a statya level reference, but no referenced statya number binds to the chain needle of the registry.
// no-statya-reference: the pinned act export carries a hyperlink naming the 44-FZ Work, but no such hyperlink carries a statya level reference in its own text.
// target-not-44fz: the pinned act export carries hyperlinks, but none of them names the 44-FZ Work.
// unparsed-act: the export rendition pinned for this act carries zero WordML hlink elements, so no reference could be parsed from it; this is not a claim that the act has no legal references.
// no-export-file: the declared identity pair (act number, act date from the layer1 record) matches no act export under exports/npa, or the layer1 record carries no law identity pair at all.
// no-layer1-record: the catalog edge points at a document_key that the layer1 manifest does not carry.
// DOCUMENTED_REASON_CODES_END

// ## Fail-closed codes (documented set; asserted equal to FAIL_CLOSED_CODES)
// DOCUMENTED_FAIL_CLOSED_BEGIN
// input_absent: a declared input path (the catalog relation database, the layer1 manifest or the frozen registry) is absent, unreadable, or a malformed catalog cannot be read, or the tracked artifact is missing in `--check` mode.
// input_hash_mismatch: a live input pin (sha256 or byte count) differs from the pin recorded in the tracked artifact, or a recorded pin is malformed.
// family_count_unsupported: the declaration itself is unsupported — envelope drift, the declared denominators or grounding pins drifting from the accepted revision, a partition that does not sum to its total, or a malformed registry identity.
// zero_denominator: a declared total is zero or not a positive integer; a zero denominator is not a measurement.
// non_ascii_evidence: the artifact bytes carry a non-ASCII byte, or a recorded identifier is not ASCII.
// raw_text_leak: the artifact carries provider prose (a corpus text marker) or a field outside the count-only token rule.
// no-layer1-record: an edge recorded as no-layer1-record is in fact joined to a layer1 record, or a row without a layer1 record records another outcome.
// no-export-file: no-export-file is recorded while candidate files exist, or a row without a law identity pair records another outcome.
// unparsed-act: unparsed-act is recorded while hyperlinks were parsed from the pinned export.
// target-not-44fz: target-not-44fz is recorded while a hyperlink naming the 44-FZ Work is present, or while no hyperlink was parsed at all.
// provision-not-in-registry: provision-not-in-registry is recorded while a statya reference resolved, or with no statya reference at all.
// no-statya-reference: no-statya-reference is recorded while a statya level reference is present, or while no hyperlink names the 44-FZ Work.
// resolved-provision: resolved-provision is recorded with zero resolved statya level targets.
// DOCUMENTED_FAIL_CLOSED_END

// Provider prose markers that must never reach a count-only artifact.
const CORPUS_TEXT_MARKERS = ["consultantplus://", "<w:", "screenTip"];

// Ignored local overlays: never a durable evidence anchor.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The artifact must bound its own claims (D416 / D539 / D552).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "scoped to the named cc:44-fz chain",
  "not every amending act of the corpus",
  "candidate provision targets are candidates, not legal determinations",
  "no commencement is inferred",
  "no corpus text is copied",
  "frozen m201 r070 proof gate is not widened",
  "zero denominator is not a measurement",
  "r070 stays active (d416)",
  "no m202 inventory count may stand as a quantifier",
  "destination_json column is carried only as a bounded catalog identifier",
];

const ALLOWED_TOKEN = /^[A-Za-z0-9_.:-]{1,64}$/;
const ACT_NUMBER = /^\d+$/;
const ACT_DATE = /^\d{4}-\d{2}-\d{2}$/;
const EXPORT_FILE = /^law_(\d{4}-\d{2}-\d{2})_(\d+)-fz_rev-([A-Za-z0-9-]+)_([0-9a-f]{8})\.xml$/;

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
    files_total: files.length,
    bytes_total: inputBytes,
    listing_sha256: `sha256:${digest.digest("hex")}`,
  };
}

/// Port of `hyperlink::extract_text_content`.
function extractTextContent(xml) {
  let result = "";
  let search = 0;
  for (;;) {
    const open = xml.indexOf("<w:t", search);
    if (open < 0) break;
    const gt = xml.indexOf(">", open);
    if (gt < 0) break;
    const textStart = gt + 1;
    const close = xml.indexOf("</w:t>", textStart);
    if (close < 0) break;
    result += xml.slice(textStart, close);
    search = close + 6;
  }
  return result;
}

/// Port of `hyperlink::extract_attr`.
function extractAttr(xml, start, name) {
  const pattern = `${name}="`;
  const attrStart = xml.indexOf(pattern, start);
  if (attrStart < 0) return null;
  const valueStart = attrStart + pattern.length;
  const valueEnd = xml.indexOf('"', valueStart);
  if (valueEnd < 0) return null;
  return xml.slice(valueStart, valueEnd);
}

/// Port of `hyperlink::extract_hyperlinks` (the admitted scanner).
function extractHyperlinks(xml) {
  const links = [];
  let searchFrom = 0;
  for (;;) {
    const absStart = xml.indexOf("<w:hlink", searchFrom);
    if (absStart < 0) break;
    let paraStart = xml.lastIndexOf("<w:p", absStart);
    if (paraStart < 0) paraStart = 0;
    let paraEnd = xml.indexOf("</w:p>", absStart);
    paraEnd = paraEnd < 0 ? xml.length : paraEnd + 6;
    const context = extractTextContent(xml.slice(paraStart, paraEnd));
    const dest = extractAttr(xml, absStart, "w:dest");
    const close = xml.indexOf("</w:hlink>", absStart);
    if (close < 0) break;
    const text = extractTextContent(xml.slice(absStart, close));
    if (dest !== null) links.push({ dest, text, context });
    searchFrom = close + 10;
  }
  return links;
}

const STATYA_SUFFIXES = [
  "ьями",
  "ьям",
  "ьях",
  "ьей",
  "ья",
  "ьи",
  "ье",
  "ью",
  "ей",
  "я",
  "е",
  "и",
  "ю",
  "ь",
];

/// Port of `first_statya_reference`: the leading full-word statya locator of a
/// link text, for example `в статье 8:` yields `8`.
function firstStatyaReference(text) {
  const stem = "стат";
  let search = 0;
  for (;;) {
    const start = text.indexOf(stem, search);
    if (start < 0) return null;
    search = start + stem.length;
    if (start > 0 && /[\p{L}\p{N}]/u.test(text[start - 1])) continue;
    let tail = null;
    for (const suffix of STATYA_SUFFIXES) {
      if (text.startsWith(suffix, start + stem.length)) {
        tail = text.slice(start + stem.length + suffix.length);
        break;
      }
    }
    if (tail === null) continue;
    const trimmed = tail.replace(/^\s+/, "");
    if (trimmed.length === tail.length) continue;
    const match = /^\d+(?:\.\d+)?/.exec(trimmed);
    if (match) return match[0];
  }
}

function namesChainWork(link) {
  return NEEDLES.some((needle) => link.text.includes(needle) || link.context.includes(needle));
}

/// Port of `act_date_from_title`: `DD.MM.YYYY` in the title normalised to
/// `YYYY-MM-DD`. The title itself never leaves this function.
function actDateFromTitle(title) {
  const needle = "от ";
  let search = 0;
  for (;;) {
    const offset = title.indexOf(needle, search);
    if (offset < 0) return null;
    const start = offset + needle.length;
    search = start;
    const candidate = title.slice(start, start + 10);
    if (!/^\d{2}\.\d{2}\.\d{4}$/.test(candidate)) continue;
    return `${candidate.slice(6, 10)}-${candidate.slice(3, 5)}-${candidate.slice(0, 2)}`;
  }
}

/// Port of `act_number_from_law_number`: the digits of `N 188-ФЗ`.
function actNumberFromLawNumber(lawNumber) {
  const index = lawNumber.indexOf("N");
  if (index < 0) return null;
  const match = /^\s*(\d+)/.exec(lawNumber.slice(index + 1));
  return match ? match[1] : null;
}

function readLayer1Manifest(exportDir) {
  const bytes = readFileSync(path.join(exportDir, LAYER1_MANIFEST_TAIL));
  let recordsTotal = 0;
  let core = 0;
  let amending = 0;
  const identity = new Map();
  const present = new Set();
  const amendingKeys = [];
  for (const raw of bytes.toString("utf8").split("\n")) {
    const line = raw.trim();
    if (line === "") continue;
    recordsTotal += 1;
    const record = JSON.parse(line);
    const key = record.document_key;
    present.add(key);
    if (record.is_core_act === true) {
      core += 1;
    } else {
      amending += 1;
      amendingKeys.push(key);
    }
    const date = actDateFromTitle(record.title);
    const number = actNumberFromLawNumber(record.law_number);
    if (date !== null && number !== null) identity.set(key, { date, number });
  }
  return {
    input_bytes: bytes.length,
    input_sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
    records_total: recordsTotal,
    core_acts: core,
    amending_acts: amending,
    identity,
    present,
    amendingKeys,
  };
}

function readRegistry() {
  const bytes = readFileSync(path.join(root, REGISTRY));
  const statya = new Set();
  let glava = 0;
  let total = 0;
  for (const raw of bytes.toString("utf8").split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("- {")) continue;
    const body = line.slice(3).replace(/\}$/, "");
    const fields = {};
    for (const part of body.split(",")) {
      const index = part.indexOf(":");
      if (index < 0) continue;
      const key = part.slice(0, index).trim();
      const value = part.slice(index + 1).trim().replace(/^"|"$/g, "").trim();
      fields[key] = value;
    }
    if (
      fields.path_needle === undefined ||
      fields.level === undefined ||
      fields.number === undefined ||
      fields.cc === undefined
    ) {
      continue;
    }
    if (fields.path_needle !== REGISTRY_NEEDLE) continue;
    total += 1;
    if (fields.level === "statya") statya.add(fields.number);
    if (fields.level === "glava") glava += 1;
  }
  return {
    input_bytes: bytes.length,
    input_sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
    statya,
    glava,
    total,
  };
}

function singleCatalogLinks(exportDir) {
  const names = readdirSync(exportDir)
    .filter((name) => name.startsWith(CATALOG_LINKS_PREFIX) && name.endsWith(CATALOG_LINKS_SUFFIX))
    .sort();
  if (names.length !== 1) return null;
  return { name: names[0], absolute: path.join(exportDir, names[0]) };
}

function readCatalog(catalog) {
  const database = new DatabaseSync(catalog.absolute, { readOnly: true });
  try {
    const runsTotal = database.prepare("SELECT COUNT(*) AS c FROM legal_relation_runs").get().c;
    const run = database
      .prepare(
        `SELECT run_id, profile, root_source_id, status,
                source_artifact_sha256, table_artifact_sha256
         FROM legal_relation_runs ORDER BY run_id LIMIT 1`,
      )
      .get();
    const edges = database
      .prepare(
        `SELECT item_id, relation_type, normalization_status, export_status, bank,
                document_key, edition_id
         FROM legal_relation_items
         WHERE run_id = ?1 AND relation_type = 'amends' AND normalization_status = 'explicit'
         ORDER BY item_id LIMIT ?2`,
      )
      .all(run.run_id, AMENDS_EDGE_LIMIT);
    const sha = createHash("sha256").update(readFileSync(catalog.absolute)).digest("hex");
    return {
      runs_total: runsTotal,
      run,
      edges,
      input_bytes: statSync(catalog.absolute).size,
      input_sha256: `sha256:${sha}`,
    };
  } finally {
    database.close();
  }
}

/// The whole leg, re-derived from the live corpus.
function deriveAmendsLive() {
  const exportDir = exportRoot();
  const catalog = singleCatalogLinks(exportDir);
  assert.ok(catalog, "exactly one catalog-links database must exist under the export root");
  const layer1 = readLayer1Manifest(exportDir);
  const registry = readRegistry();
  const catalogData = readCatalog(catalog);

  const npaDirectory = path.join(exportDir, NPA_TAIL);
  const npaInventory = inventoryDirectory(npaDirectory);
  const npaNames = readdirSync(npaDirectory).filter((name) => statSync(path.join(npaDirectory, name)).isFile());

  const rows = [];
  const byOutcome = new Map();
  const edgesWithLayer1 = new Set();
  const occurrences = new Map();
  const resolvedOccurrences = new Set();

  for (const edge of catalogData.edges) {
    const edition = typeof edge.edition_id === "string" ? edge.edition_id : "";
    const corroborating = edition.startsWith("edition-") ? edition.slice(8, 16) : null;
    const identity = layer1.identity.get(edge.document_key);
    const present = layer1.present.has(edge.document_key);
    const bump = (code) => byOutcome.set(code, (byOutcome.get(code) ?? 0) + 1);
    const base = {
      item_id: edge.item_id,
      document_key: edge.document_key,
      act_number: "",
      act_date: "",
      layer1_record_present: present,
      candidate_files: 0,
      edition_id_corroborated: false,
      export_file_bytes: 0,
      export_links_total: 0,
      export_links_naming_44fz: 0,
      statya_refs_distinct: 0,
      statya_refs_resolved: 0,
      outcome: "no-layer1-record",
    };

    if (identity === undefined) {
      if (!present) {
        bump("no-layer1-record");
        rows.push(base);
        continue;
      }
      bump("no-export-file");
      rows.push({ ...base, outcome: "no-export-file" });
      continue;
    }

    const actDate = identity.date;
    const actNumber = identity.number;
    const candidates = npaNames
      .map((name) => EXPORT_FILE.exec(name))
      .filter((match) => match && match[1] === actDate && match[2] === actNumber)
      .map((match) => ({
        revision: match[3],
        hash: match[4],
        name: match[0],
        bytes: statSync(path.join(npaDirectory, match[0])).size,
      }))
      .sort((left, right) =>
        `${left.revision}\u0000${left.hash}` < `${right.revision}\u0000${right.hash}` ? -1 : 1,
      );
    const corroborated = candidates.filter((candidate) => candidate.hash === corroborating);
    const selected = corroborated.length > 0 ? corroborated : candidates;
    edgesWithLayer1.add(edge.document_key);

    if (selected.length === 0) {
      bump("no-export-file");
      rows.push({
        ...base,
        act_number: actNumber,
        act_date: actDate,
        candidate_files: candidates.length,
        outcome: "no-export-file",
      });
      continue;
    }

    let exportFileBytes = 0;
    let linksTotal = 0;
    let naming = 0;
    const refs = new Set();
    for (const candidate of selected) {
      const xml = readFileSync(path.join(npaDirectory, candidate.name), "utf8");
      exportFileBytes += candidate.bytes;
      const links = extractHyperlinks(xml);
      linksTotal += links.length;
      for (const link of links) {
        if (!namesChainWork(link)) continue;
        naming += 1;
        const number = firstStatyaReference(link.text);
        if (number !== null) refs.add(number);
      }
    }

    let resolved = 0;
    for (const number of refs) {
      occurrences.set(number, (occurrences.get(number) ?? 0) + 1);
      if (registry.statya.has(number)) {
        resolved += 1;
        resolvedOccurrences.add(number);
      }
    }

    let outcome;
    if (linksTotal === 0) outcome = "unparsed-act";
    else if (naming === 0) outcome = "target-not-44fz";
    else if (refs.size === 0) outcome = "no-statya-reference";
    else if (resolved === 0) outcome = "provision-not-in-registry";
    else outcome = "resolved-provision";
    bump(outcome);

    rows.push({
      item_id: edge.item_id,
      document_key: edge.document_key,
      act_number: actNumber,
      act_date: actDate,
      layer1_record_present: true,
      candidate_files: candidates.length,
      edition_id_corroborated: corroborated.length > 0,
      export_file_bytes: exportFileBytes,
      export_links_total: linksTotal,
      export_links_naming_44fz: naming,
      statya_refs_distinct: refs.size,
      statya_refs_resolved: resolved,
      outcome,
    });
  }

  const withoutEdge = layer1.amendingKeys.filter((key) => !edgesWithLayer1.has(key)).length;
  return {
    exportDir,
    catalog,
    layer1,
    registry,
    catalogData,
    npaInventory,
    rows,
    byOutcome,
    layer1Coverage: {
      "with-amends-edge": layer1.amendingKeys.length - withoutEdge,
      "without-amends-edge": withoutEdge,
    },
    distinctStatyaRefs: occurrences.size,
    distinctStatyaRefsResolved: resolvedOccurrences.size,
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateAmendsArtifact(artifact, env = {}) {
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
  if (artifact?.task !== TASK) code("family_count_unsupported", "task mismatch");
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
  if (!Array.isArray(artifact?.reason_codes)) {
    code("family_count_unsupported", "reason_codes is missing");
  } else if (sortJoin(artifact.reason_codes) !== sortJoin(REASON_CODES)) {
    code("family_count_unsupported", "reason_codes drift");
  }
  if (!Array.isArray(artifact?.fail_closed_codes)) {
    code("family_count_unsupported", "fail_closed_codes is missing");
  } else if (sortJoin(artifact.fail_closed_codes) !== sortJoin(FAIL_CLOSED_CODES)) {
    code("family_count_unsupported", "fail_closed_codes drift");
  }

  // 3. non-claims.
  if (!Array.isArray(artifact?.non_claims) || artifact.non_claims.length === 0) {
    code("family_count_unsupported", "non_claims is missing");
  } else {
    const joined = artifact.non_claims.join(" ").toLowerCase();
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      if (!joined.includes(fragment)) {
        code("family_count_unsupported", `non-claim missing: ${fragment}`);
      }
    }
  }

  // 4. relation run and grounding.
  const run = artifact?.relation_run;
  if (!run || typeof run !== "object") {
    code("family_count_unsupported", "relation_run block is missing");
  } else {
    if (run.root_source_id !== CHAIN_ROOT_SOURCE_ID) {
      code("family_count_unsupported", "the run no longer roots the declared chain");
    }
    if (run.profile !== CHAIN_PROFILE || run.status !== CHAIN_STATUS) {
      code("family_count_unsupported", "relation run profile or status drift");
    }
    if (!SHA_PATTERN.test(run.source_artifact_sha256 ?? "")) {
      code("input_hash_mismatch", "run source artifact pin is malformed");
    }
    if (!SHA_PATTERN.test(run.table_artifact_sha256 ?? "")) {
      code("input_hash_mismatch", "run table artifact pin is malformed");
    }
    if (run.runs_total !== 1) code("family_count_unsupported", "exactly one relation run is declared");
  }

  // 5. registry block.
  const registry = artifact?.registry;
  if (!registry || typeof registry !== "object") {
    code("family_count_unsupported", "registry block is missing");
  } else {
    if (registry.relative_path !== REGISTRY || registry.needle !== REGISTRY_NEEDLE) {
      code("family_count_unsupported", "registry needle drift");
    }
    if (!Number.isInteger(registry.statya_bindings) || registry.statya_bindings <= 0) {
      code("zero_denominator", "the statya binding denominator is not a positive integer");
    }
    if (registry.bindings_total !== (registry.statya_bindings ?? 0) + (registry.glava_bindings ?? 0)) {
      code("family_count_unsupported", "registry binding levels do not sum to the total");
    }
  }

  // 6. denominators and partitions.
  const denominator = artifact?.denominator;
  if (!denominator || typeof denominator !== "object") {
    code("family_count_unsupported", "denominator block is missing");
    return { ok: errors.length === 0, errors };
  }
  if (
    !Number.isInteger(denominator.amends_edges_total) ||
    denominator.amends_edges_total <= 0 ||
    !Number.isInteger(denominator.layer1_amending_acts) ||
    denominator.layer1_amending_acts <= 0
  ) {
    code("zero_denominator", "the declared denominators must be positive integers");
  }
  checkPartition(
    code,
    "by_outcome",
    denominator.by_outcome,
    denominator.amends_edges_total,
    REASON_CODES,
  );
  checkPartition(code, "by_layer1_coverage", denominator.by_layer1_coverage, denominator.layer1_amending_acts, []);
  if (denominator.rows_total !== denominator.amends_edges_total) {
    code("family_count_unsupported", "rows_total must equal the declared denominator");
  }
  if (denominator.layer1_core_acts + denominator.layer1_amending_acts !== denominator.layer1_records_total) {
    code("family_count_unsupported", "the layer1 level partition does not sum to the record total");
  }
  if (!Number.isInteger(denominator.distinct_statya_refs) || denominator.distinct_statya_refs < 0) {
    code("family_count_unsupported", "distinct_statya_refs is not a count");
  }
  if (
    !Number.isInteger(denominator.distinct_statya_refs_resolved) ||
    denominator.distinct_statya_refs_resolved > denominator.distinct_statya_refs
  ) {
    code("family_count_unsupported", "more distinct targets resolved than were declared");
  }

  // 7. npa exports inventory.
  const npa = artifact?.npa_exports;
  if (!npa || typeof npa !== "object") {
    code("family_count_unsupported", "npa_exports block is missing");
  } else {
    if (!isRepoRelative(npa.relative_path) || !npa.relative_path.endsWith(NPA_TAIL)) {
      code("family_count_unsupported", "the npa anchor is not the declared export directory");
    }
    if (!SHA_PATTERN.test(npa.listing_sha256 ?? "")) {
      code("input_hash_mismatch", "the npa listing pin is malformed");
    }
    if (!Number.isInteger(npa.files_total) || npa.files_total <= 0) {
      code("zero_denominator", "the npa file inventory is not a positive integer");
    }
  }

  // 8. input pins.
  if (!Array.isArray(artifact?.inputs)) {
    code("family_count_unsupported", "inputs is missing");
  } else {
    const ids = artifact.inputs.map((pin) => pin?.input_id);
    if (sortJoin(ids) !== sortJoin(INPUT_IDS)) {
      code("family_count_unsupported", "the declared input pins drifted");
    }
    for (const pin of artifact.inputs) {
      if (!isRepoRelative(pin?.relative_path)) {
        code("family_count_unsupported", `anchor is not repository-relative: ${pin?.input_id}`);
      }
      if (!SHA_PATTERN.test(pin?.input_sha256 ?? "")) {
        code("input_hash_mismatch", `pin is malformed: ${pin?.input_id}`);
      }
      if (!Number.isInteger(pin?.input_bytes) || pin.input_bytes <= 0) {
        code("input_hash_mismatch", `byte pin is malformed: ${pin?.input_id}`);
      }
      if (typeof env.exists === "function" && !env.exists(pin?.relative_path)) {
        code("input_absent", `input is absent: ${pin?.relative_path}`);
      }
    }
  }

  // 9. per-edge rows.
  if (!Array.isArray(artifact?.edges) || artifact.edges.length === 0) {
    code("family_count_unsupported", "edges is missing");
  } else {
    for (const row of artifact.edges) {
      checkRow(code, row);
    }
    if (artifact.edges.length !== denominator.amends_edges_total) {
      code("family_count_unsupported", "the per-edge rows do not cover the declared denominator");
    }
  }

  // 10. live re-derivation.
  const live = env.live;
  if (live) {
    for (const pin of artifact?.inputs ?? []) {
      const observed = live.inputs?.[pin?.input_id];
      if (!observed) continue;
      if (
        observed.input_bytes !== pin.input_bytes ||
        observed.input_sha256 !== pin.input_sha256
      ) {
        code("input_hash_mismatch", `live pin differs: ${pin.input_id}`);
      }
    }
  }

  return { ok: errors.length === 0, errors };
}

function checkPartition(code, scope, partition, declaredTotal, allowedKeys) {
  if (!partition || typeof partition !== "object" || Array.isArray(partition)) {
    code("family_count_unsupported", `${scope} is missing`);
    return;
  }
  const parts = Object.entries(partition);
  if (parts.length === 0) {
    code("family_count_unsupported", `${scope} is empty`);
    return;
  }
  let sum = 0;
  for (const [key, value] of parts) {
    if (!Number.isInteger(value) || value < 0) {
      code("family_count_unsupported", `${scope} part ${key} is not a count`);
      continue;
    }
    sum += value;
    if (!isAscii(key)) code("non_ascii_evidence", `${scope} key is not ascii`);
    else if (!ALLOWED_TOKEN.test(key)) {
      code("raw_text_leak", `${scope} key ${key} is outside the count-only token rule`);
    }
    if (allowedKeys.length > 0 && !allowedKeys.includes(key)) {
      code("family_count_unsupported", `${scope} carries an undocumented code ${key}`);
    }
  }
  if (allowedKeys.length > 0) {
    for (const key of allowedKeys) {
      if (!(key in partition)) {
        code("family_count_unsupported", `${scope} omits the documented code ${key}`);
      }
    }
  }
  if (Number.isInteger(declaredTotal) && declaredTotal > 0 && sum !== declaredTotal) {
    code(
      "family_count_unsupported",
      `${scope} sums to ${sum}, not the declared total ${declaredTotal}`,
    );
  }
}

/// An outcome is a refusal whenever the row's own counts do not justify it.
function checkRow(code, row) {
  const outcome = row?.outcome;
  if (!REASON_CODES.includes(outcome)) {
    code("family_count_unsupported", `edge ${row?.item_id} carries an undocumented outcome`);
    return;
  }
  if (!Number.isInteger(row?.item_id) || row.item_id <= 0) {
    code(outcome, "a row carries a non-positive catalog identifier");
  }
  if (!Number.isInteger(row?.document_key) || row.document_key <= 0) {
    code(outcome, "a row carries a non-positive document key");
  }
  if (row?.layer1_record_present !== true && outcome !== "no-layer1-record") {
    code(outcome, "a row without a layer1 record must record no-layer1-record");
  }
  if (outcome === "no-layer1-record" && row?.layer1_record_present === true) {
    code("no-layer1-record", "no-layer1-record is recorded for a joined row");
  }
  if (row?.layer1_record_present === true) {
    if (!Number.isInteger(row?.candidate_files) || row.candidate_files < 0) {
      code(outcome, "candidate_files is not a count");
    }
    if (typeof row?.act_number === "string" && row.act_number !== "") {
      if (!ACT_NUMBER.test(row.act_number) || !ACT_DATE.test(row.act_date ?? "")) {
        code(outcome, "a joined row carries a non-token act identity");
      }
    } else if (outcome !== "no-export-file") {
      code(outcome, "a row without a law identity pair must record no-export-file");
    }
  }
  if (outcome === "no-export-file" && row?.candidate_files !== 0) {
    code("no-export-file", "no-export-file is recorded while candidate files exist");
  }
  if (outcome === "unparsed-act" && row?.export_links_total !== 0) {
    code("unparsed-act", "unparsed-act is recorded while links were parsed");
  }
  if (
    outcome === "target-not-44fz" &&
    (row?.export_links_naming_44fz !== 0 || row?.export_links_total === 0)
  ) {
    code("target-not-44fz", "target-not-44fz is recorded while a 44-FZ reference is present");
  }
  if (
    outcome === "no-statya-reference" &&
    (row?.export_links_naming_44fz === 0 || row?.statya_refs_distinct !== 0)
  ) {
    code("no-statya-reference", "no-statya-reference is recorded while a statya reference is present");
  }
  if (
    outcome === "provision-not-in-registry" &&
    (row?.statya_refs_distinct === 0 || row?.statya_refs_resolved !== 0)
  ) {
    code(
      "provision-not-in-registry",
      "provision-not-in-registry is recorded while a target resolved",
    );
  }
  if (outcome === "resolved-provision" && row?.statya_refs_resolved === 0) {
    code("resolved-provision", "resolved-provision is recorded with zero resolved targets");
  }
  if (row?.statya_refs_resolved > row?.statya_refs_distinct) {
    code(outcome, "a row resolves more targets than it declares");
  }
}

function isAscii(value) {
  return typeof value === "string" && /^[\x00-\x7f]*$/.test(value);
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

/**
 * The live derivation is expensive (it hashes the 419 MB relation database and
 * scans every pinned act export), so it is computed at most once per process.
 */
let derivedCache = null;
function derivedLive() {
  if (derivedCache === null) derivedCache = deriveAmendsLive();
  return derivedCache;
}

function liveEnv() {
  const env = { artifactText: liveText, exists: (value) => existsSync(path.join(root, value)) };
  if (existsSync(exportRoot())) {
    const derived = derivedLive();
    env.live = {
      inputs: {
        catalog_links_sqlite: {
          input_bytes: derived.catalogData.input_bytes,
          input_sha256: derived.catalogData.input_sha256,
        },
        layer1_manifest: {
          input_bytes: derived.layer1.input_bytes,
          input_sha256: derived.layer1.input_sha256,
        },
        kb_hierarchy_registry: {
          input_bytes: derived.registry.input_bytes,
          input_sha256: derived.registry.input_sha256,
        },
      },
    };
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
  for (const pin of liveArtifact.inputs) {
    assert.ok(
      isRepoRelative(pin.relative_path),
      `input ${pin.input_id} path must be repository-relative`,
    );
    assert.ok(
      existsSync(path.join(root, pin.relative_path)),
      `input ${pin.input_id} must exist: ${pin.relative_path}`,
    );
  }
  assert.ok(
    isRepoRelative(liveArtifact.npa_exports.relative_path),
    "the npa exports anchor must be repository-relative",
  );
  assert.ok(
    existsSync(path.join(root, liveArtifact.npa_exports.relative_path)),
    "the npa exports directory must exist",
  );
  assert.equal(liveArtifact.registry.relative_path, REGISTRY);
});

test("the artifact enumerates exactly the documented code sets", () => {
  assert.deepEqual([...liveArtifact.reason_codes].sort(), [...REASON_CODES].sort());
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());
  for (const code of liveArtifact.reason_codes) {
    assert.ok(liveArtifact.fail_closed_codes.includes(code), `${code} must be a fail-closed code`);
  }
  assert.equal(new Set(liveArtifact.fail_closed_codes).size, liveArtifact.fail_closed_codes.length);
});

test("the artifact is bound to one named chain root and one registry needle", () => {
  assert.equal(liveArtifact.relation_run.root_source_id, CHAIN_ROOT_SOURCE_ID);
  assert.equal(liveArtifact.relation_run.profile, CHAIN_PROFILE);
  assert.equal(liveArtifact.relation_run.status, CHAIN_STATUS);
  assert.equal(liveArtifact.relation_run.runs_total, 1);
  assert.equal(liveArtifact.registry.needle, REGISTRY_NEEDLE);
  assert.equal(liveArtifact.lifecycle, "[bounded]");
  assert.equal(liveArtifact.authoritative, false);
  assert.equal(liveArtifact.disposition, "active");
  assert.equal(liveArtifact.disposition_decision, "D416");
  for (const [field, total] of Object.entries(ANCHORED)) {
    if (REASON_CODES.includes(field)) {
      assert.equal(
        liveArtifact.denominator.by_outcome[field],
        total,
        `outcome ${field} left the anchored revision`,
      );
      continue;
    }
    if (field in liveArtifact.denominator) {
      assert.equal(liveArtifact.denominator[field], total, `${field} left the anchored revision`);
    } else if (field in liveArtifact.registry) {
      assert.equal(liveArtifact.registry[field], total, `${field} left the anchored revision`);
    } else if (field in liveArtifact.npa_exports) {
      assert.equal(liveArtifact.npa_exports[field], total, `${field} left the anchored revision`);
    }
  }
  const linkSum = liveArtifact.edges.reduce((total_, row) => total_ + row.export_links_total, 0);
  assert.equal(
    linkSum,
    ANCHORED_EXPORT_LINKS_TOTAL,
    "the parsed hyperlink total left the anchored revision",
  );
  assert.equal(
    liveArtifact.npa_exports.files_total,
    ANCHORED_NPA_FILES_TOTAL,
    "the npa file inventory left the anchored revision",
  );
});

test("the partitions sum to their declared totals", () => {
  const outcomeSum = Object.values(liveArtifact.denominator.by_outcome).reduce(
    (total, value) => total + value,
    0,
  );
  assert.equal(outcomeSum, liveArtifact.denominator.amends_edges_total);
  const coverageSum = Object.values(liveArtifact.denominator.by_layer1_coverage).reduce(
    (total, value) => total + value,
    0,
  );
  assert.equal(coverageSum, liveArtifact.denominator.layer1_amending_acts);
  assert.equal(
    liveArtifact.denominator.layer1_core_acts + liveArtifact.denominator.layer1_amending_acts,
    liveArtifact.denominator.layer1_records_total,
  );
  assert.equal(
    Object.values(liveArtifact.denominator.by_outcome).length,
    liveArtifact.reason_codes.length,
  );
  assert.equal(liveArtifact.edges.length, liveArtifact.denominator.amends_edges_total);
  const counts = new Map();
  for (const row of liveArtifact.edges) {
    counts.set(row.outcome, (counts.get(row.outcome) ?? 0) + 1);
  }
  for (const code of liveArtifact.reason_codes) {
    assert.equal(
      counts.get(code) ?? 0,
      liveArtifact.denominator.by_outcome[code],
      `per-edge rows disagree with the by_outcome partition for ${code}`,
    );
  }
});

test("every per-edge outcome is justified by its own counts", () => {
  const result = validateAmendsArtifact(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `artifact errors: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
  for (const row of liveArtifact.edges) {
    assert.ok(REASON_CODES.includes(row.outcome), `edge ${row.item_id} outcome`);
    assert.equal(row.admitted_hyperlink_count, row.export_links_total);
  }
});

test("the record carries the D416 and D539 non-claims", () => {
  const joined = liveArtifact.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `non-claim fragment missing: ${fragment}`);
  }
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
  assert.match(module, /pub const AMENDS_PROVISION_REASON_CODES/);
  assert.match(module, /pub const AMENDS_PROVISION_FAIL_CLOSED_CODES/);
  assert.match(module, /pub fn collect_amends_provisions/);
  assert.match(module, /pub fn render_amends_provisions/);
  assert.match(module, /pub fn validate_amends_provisions/);

  // The additive catalog method keeps the read-only discipline.
  const catalog = readRepo(CATALOG_SQLITE);
  assert.match(catalog, /pub fn amends_edge_set/);
  assert.match(catalog, /SQLITE_OPEN_READ_ONLY/);
  assert.ok(
    !catalog.includes("raw_tooltip FROM") || !catalog.includes("raw_tooltip, visible_text"),
    "the additive method must not project prose columns",
  );
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
      artifact.inputs[0].relative_path = "prd/migration/rust-evidence/absent-catalog.sqlite";
    },
    env: () => ({
      exists: (value) =>
        !value.endsWith("absent-catalog.sqlite") && existsSync(path.join(root, value)),
    }),
  },
  {
    code: "input_hash_mismatch",
    mutate: () => {},
    env: (artifact) => ({
      live: {
        inputs: {
          [artifact.inputs[0].input_id]: {
            input_bytes: artifact.inputs[0].input_bytes,
            input_sha256: `sha256:${"0".repeat(64)}`,
          },
        },
      },
    }),
  },
  {
    code: "family_count_unsupported",
    mutate: (artifact) => {
      artifact.denominator.amends_edges_total += 1;
    },
    env: {},
  },
  {
    code: "zero_denominator",
    mutate: (artifact) => {
      artifact.denominator.layer1_amending_acts = 0;
      artifact.denominator.by_layer1_coverage = { zero: 0 };
    },
    env: {},
  },
  {
    code: "non_ascii_evidence",
    mutate: (artifact) => {
      artifact.count_basis = `${artifact.count_basis}\u041f\u0420\u0410\u0412\u041e`;
    },
    env: {},
  },
  {
    code: "raw_text_leak",
    mutate: (artifact) => {
      artifact.count_basis = "corpus content: consultantplus://offline/ref=DEADBEEF";
    },
    env: {},
  },
  {
    code: "no-export-file",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.outcome === "unparsed-act");
      row.outcome = "no-export-file";
      row.candidate_files = 2;
    },
    env: {},
  },
  {
    code: "no-layer1-record",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.layer1_record_present === true);
      row.outcome = "no-layer1-record";
      row.layer1_record_present = true;
    },
    env: {},
  },
  {
    code: "unparsed-act",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.export_links_total > 0);
      row.outcome = "unparsed-act";
    },
    env: {},
  },
  {
    code: "target-not-44fz",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.export_links_naming_44fz > 0);
      row.outcome = "target-not-44fz";
    },
    env: {},
  },
  {
    code: "no-statya-reference",
    mutate: (artifact) => {
      const row = artifact.edges.find(
        (edge) => edge.export_links_naming_44fz > 0 && edge.statya_refs_distinct > 0,
      );
      row.outcome = "no-statya-reference";
    },
    env: {},
  },
  {
    code: "provision-not-in-registry",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.statya_refs_resolved > 0);
      row.outcome = "provision-not-in-registry";
    },
    env: {},
  },
  {
    code: "resolved-provision",
    mutate: (artifact) => {
      const row = artifact.edges.find((edge) => edge.statya_refs_resolved > 0);
      row.outcome = "resolved-provision";
      row.statya_refs_resolved = 0;
      row.statya_refs_distinct = 1;
    },
    env: {},
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
    const result = validateAmendsArtifact(artifact, env);
    expectCode(result, entry.code);
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...FAIL_CLOSED_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

test("the documented code blocks equal the emitted code sets", () => {
  const source = readRepo(CONTRACT_PATH);

  const reasonBlock = source.match(
    /\/\/ DOCUMENTED_REASON_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_REASON_CODES_END/,
  );
  assert.ok(reasonBlock, "the documented reason-code block must exist");
  const documentedReasons = reasonBlock[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documentedReasons.sort(), [...REASON_CODES].sort());
  assert.deepEqual([...liveArtifact.reason_codes].sort(), [...REASON_CODES].sort());

  const failBlock = source.match(
    /\/\/ DOCUMENTED_FAIL_CLOSED_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_FAIL_CLOSED_END/,
  );
  assert.ok(failBlock, "the documented fail-closed block must exist");
  const documentedFailClosed = failBlock[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documentedFailClosed.sort(), [...FAIL_CLOSED_CODES].sort());
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());

  const module = readRepo(RUST_MODULE);
  const rustReason = module.match(
    /pub const AMENDS_PROVISION_REASON_CODES: \[&str; \d+\] = \[([\s\S]*?)\];/,
  );
  assert.ok(rustReason, "the Rust AMENDS_PROVISION_REASON_CODES array must exist");
  assert.deepEqual(
    [...rustReason[1].matchAll(/"([a-z0-9_-]+)"/g)].map((match) => match[1]).sort(),
    [...REASON_CODES].sort(),
  );
  const rustFail = module.match(
    /pub const AMENDS_PROVISION_FAIL_CLOSED_CODES: \[&str; \d+\] = \[([\s\S]*?)\];/,
  );
  assert.ok(rustFail, "the Rust AMENDS_PROVISION_FAIL_CLOSED_CODES array must exist");
  assert.deepEqual(
    [...rustFail[1].matchAll(/"([a-z0-9_-]+)"/g)].map((match) => match[1]).sort(),
    [...FAIL_CLOSED_CODES].sort(),
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
      artifact.task = "T09";
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
      artifact.reason_codes = ["resolved-provision"];
    },
    (artifact) => {
      artifact.fail_closed_codes = ["input_absent"];
    },
    (artifact) => {
      artifact.relation_run.root_source_id = "cp:LAW:000000";
    },
    (artifact) => {
      artifact.relation_run.runs_total = 2;
    },
    (artifact) => {
      artifact.registry.needle = "n-44-fz";
    },
    (artifact) => {
      delete artifact.denominator.by_outcome["unparsed-act"];
    },
    (artifact) => {
      artifact.denominator.by_outcome["unparsed-act"] += 1;
    },
    (artifact) => {
      delete artifact.edges;
    },
    (artifact) => {
      artifact.inputs[0].input_sha256 = "sha256:XYZ";
    },
    (artifact) => {
      artifact.inputs[0].relative_path = "/tmp/absolute.sqlite";
    },
    (artifact) => {
      artifact.inputs[0].relative_path = "../../escape.sqlite";
    },
    (artifact) => {
      artifact.npa_exports.files_total = 0;
    },
    (artifact) => {
      const row = artifact.edges[0];
      row.outcome = "resolved-provision";
      row.statya_refs_resolved = 0;
    },
  ];
  for (const mutate of cases) {
    const artifact = cloneArtifact();
    mutate(artifact);
    const result = validateAmendsArtifact(artifact, {
      artifactText: artifactTextOf(artifact),
    });
    assert.equal(result.ok, false, `${mutate} must fail closed`);
  }
});

// ---------------------------------------------------------------------------
// corpus-gated re-derivation
// ---------------------------------------------------------------------------

test("the live corpus re-derives the declared leg", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    console.log(`export_root=${path.relative(root, exportRoot())}`);
    const result = validateAmendsArtifact(liveArtifact, { artifactText: liveText });
    assert.deepEqual(result.errors, [], "the artifact-integrity block must still hold");
    return;
  }

  const derived = derivedLive();
  const denominator = liveArtifact.denominator;

  assert.equal(derived.catalogData.runs_total, liveArtifact.relation_run.runs_total);
  assert.equal(derived.catalogData.run.root_source_id, liveArtifact.relation_run.root_source_id);
  assert.equal(derived.catalogData.run.profile, liveArtifact.relation_run.profile);
  assert.equal(derived.catalogData.run.status, liveArtifact.relation_run.status);
  assert.equal(derived.layer1.records_total, denominator.layer1_records_total);
  assert.equal(derived.layer1.core_acts, denominator.layer1_core_acts);
  assert.equal(derived.layer1.amending_acts, denominator.layer1_amending_acts);
  assert.equal(derived.registry.statya.size, liveArtifact.registry.statya_bindings);
  assert.equal(derived.registry.glava, liveArtifact.registry.glava_bindings);
  assert.equal(derived.registry.total, liveArtifact.registry.bindings_total);
  assert.equal(derived.npaInventory.files_total, liveArtifact.npa_exports.files_total);
  assert.equal(derived.npaInventory.bytes_total, liveArtifact.npa_exports.bytes_total);
  assert.equal(derived.npaInventory.listing_sha256, liveArtifact.npa_exports.listing_sha256);
  assert.equal(derived.distinctStatyaRefs, denominator.distinct_statya_refs);
  assert.equal(derived.distinctStatyaRefsResolved, denominator.distinct_statya_refs_resolved);
  for (const [code, total] of Object.entries(denominator.by_outcome)) {
    assert.equal(
      derived.byOutcome.get(code) ?? 0,
      total,
      `outcome ${code} drifted from the live corpus`,
    );
  }
  for (const [code, total] of Object.entries(denominator.by_layer1_coverage)) {
    assert.equal(derived.layer1Coverage[code], total, `layer1 coverage ${code} drifted`);
  }

  // Per-edge re-derivation: every count and outcome is reproduced.
  assert.equal(derived.rows.length, liveArtifact.edges.length);
  for (const [index, row] of liveArtifact.edges.entries()) {
    const observed = derived.rows[index];
    assert.equal(observed.item_id, row.item_id, `edge ${index} item_id drifted`);
    assert.equal(observed.document_key, row.document_key, `edge ${row.item_id} document_key drifted`);
    assert.equal(observed.act_number, row.act_number, `edge ${row.item_id} act number drifted`);
    assert.equal(observed.act_date, row.act_date, `edge ${row.item_id} act date drifted`);
    assert.equal(
      observed.layer1_record_present,
      row.layer1_record_present,
      `edge ${row.item_id} layer1 join drifted`,
    );
    assert.equal(
      observed.candidate_files,
      row.candidate_files,
      `edge ${row.item_id} candidate count drifted`,
    );
    assert.equal(
      observed.edition_id_corroborated,
      row.edition_id_corroborated,
      `edge ${row.item_id} edition corroboration drifted`,
    );
    assert.equal(
      observed.export_file_bytes,
      row.export_file_bytes,
      `edge ${row.item_id} export byte pin drifted`,
    );
    assert.equal(
      observed.export_links_total,
      row.export_links_total,
      `edge ${row.item_id} hyperlink count drifted`,
    );
    assert.equal(
      observed.export_links_naming_44fz,
      row.export_links_naming_44fz,
      `edge ${row.item_id} 44-FZ naming count drifted`,
    );
    assert.equal(
      observed.statya_refs_distinct,
      row.statya_refs_distinct,
      `edge ${row.item_id} statya reference count drifted`,
    );
    assert.equal(
      observed.statya_refs_resolved,
      row.statya_refs_resolved,
      `edge ${row.item_id} resolved target count drifted`,
    );
    assert.equal(observed.outcome, row.outcome, `edge ${row.item_id} outcome drifted`);
  }

  const result = validateAmendsArtifact(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `live errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S03_CORPUS_PRESENT");
  console.log(`amends_edges=${denominator.amends_edges_total}`);
  console.log(`layer1_records=${denominator.layer1_records_total}`);
  console.log(`layer1_amending=${denominator.layer1_amending_acts}`);
  console.log(`registry_statya=${liveArtifact.registry.statya_bindings}`);
  console.log(`records_with_edge=${derived.layer1Coverage["with-amends-edge"]}`);
  console.log(`records_without_edge=${derived.layer1Coverage["without-amends-edge"]}`);
  console.log(`resolved=${denominator.by_outcome["resolved-provision"]}`);
  console.log(`unresolved=${denominator.amends_edges_total - denominator.by_outcome["resolved-provision"]}`);
});

test("drift in any declared input or count is detected under a named code", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const derived = derivedLive();

  const pinned = cloneArtifact();
  pinned.inputs[0].input_sha256 = `sha256:${"1".repeat(64)}`;
  expectCode(
    validateAmendsArtifact(pinned, {
      artifactText: artifactTextOf(pinned),
      live: {
        inputs: {
          catalog_links_sqlite: {
            input_bytes: derived.catalogData.input_bytes,
            input_sha256: derived.catalogData.input_sha256,
          },
        },
      },
    }),
    "input_hash_mismatch",
  );

  const miscounted = cloneArtifact();
  miscounted.denominator.amends_edges_total += 1;
  expectCode(
    validateAmendsArtifact(miscounted, { artifactText: artifactTextOf(miscounted) }),
    "family_count_unsupported",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the amending-act contract holds)
// ---------------------------------------------------------------------------

test("M209 S03 amending-act markers", () => {
  const result = validateAmendsArtifact(liveArtifact, liveEnv());
  assert.deepEqual(result.errors, [], `errors: ${JSON.stringify(result.errors)}`);
  console.log("M209_S03_AMENDS_PROVISION_OK");
  console.log("M209_S03_AMENDS_PROVISION_SUM_OK");
  console.log("M209_S03_AMENDS_PROVISION_CODES_OK");
  console.log(`edges=${liveArtifact.edges.length}`);
  console.log(`resolved=${liveArtifact.denominator.by_outcome["resolved-provision"]}`);
  console.log(`reason_codes=${liveArtifact.reason_codes.length}`);
  console.log(`fail_closed_codes=${liveArtifact.fail_closed_codes.length}`);
});
