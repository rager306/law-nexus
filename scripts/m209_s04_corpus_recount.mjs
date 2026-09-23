#!/usr/bin/env node
// Live corpus recount and edition-coverage reconciliation for M209-2yg6ix
// (S04 T02, D539 / D560).
//
// WHY THIS FILE EXISTS
// The milestone criterion is "118-edition inventory reconciled with actual
// causal coverage". An inventory counter is not a measurement (D539), and the
// T01 evidence audit explicitly delegated every directory-level listing digest
// to this task. So this script re-derives the corpus envelope from the raw
// provider files -- the live edition listing and the layer1 manifest -- with an
// independently written implementation, then reconciles the 118 editions with
// the coverage that is actually derivable: one core-act initial edition plus
// the date-matched amending acts, with every remaining act declared under a
// named residual code and zero silently lost editions (D560).
//
// WHAT IT IS NOT
// It is NOT a second corpus parser and NOT a causal proof. It reads no XML
// bytes: it lists edition files (names and sizes), reads the layer1 manifest
// and parses act dates out of manifest titles in memory. A matching act date
// and revision date is a structural correspondence, never an amending,
// commencement or applicability relation. It does not read the Rust emitters
// as truth: the frozen pins below and the tracked S03 declarations are two
// independent agreement legs, and a disagreement fails closed instead of
// trusting either side.
//
// INPUTS (read-only): the untracked licensed provider export under
// `consru_export/consru_export` (the `44-fz` edition directory and
// `manifest_layer1_44fz_and_amending_laws.jsonl`) plus the tracked S03
// artifacts `m209-s03-family-denominator.json` and
// `m209-s03-edition-delta-evidence.json`. Nothing is ever written into the
// corpus and no corpus text is copied into an artifact.
//
// OUTPUTS
//   prd/migration/rust-evidence/m209-s04-corpus-recount-evidence.json
//     schema law-nexus/m209-corpus-recount-evidence/v1
//   prd/migration/rust-evidence/m209-s04-edition-coverage-reconciliation.json
//     schema law-nexus/m209-edition-coverage-reconciliation/v1
//
// USAGE
//   node scripts/m209_s04_corpus_recount.mjs --mode all --out prd/migration/rust-evidence/m209-s04-corpus-recount-evidence.json
//   node scripts/m209_s04_corpus_recount.mjs --mode all --check
//   node scripts/m209_s04_corpus_recount.mjs --mode recount   # recount artifact only
//   node scripts/m209_s04_corpus_recount.mjs --mode editions  # reconciliation artifact only
//
// `--out PATH` overrides the primary artifact target of the selected mode:
// the recount artifact for `recount` / `all`, the reconciliation artifact for
// `editions`. Every other artifact keeps its canonical path.
//
// Offline, dependency-free (node stdlib only), deterministic: no clock, no
// randomness, no network, byte-stable output for byte-stable inputs. The
// corpus root is `consru_export`, overridable through `CONSULTANT_EXPORT_DIR`
// with empty-as-unset semantics; the export payload lives one level below it
// in `consru_export/`.

import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");

export const SCHEMA_RECOUNT = "law-nexus/m209-corpus-recount-evidence/v1";
export const SCHEMA_RECONCILIATION = "law-nexus/m209-edition-coverage-reconciliation/v1";
export const KIND_RECOUNT = "m209-s04-corpus-recount";
export const KIND_RECONCILIATION = "m209-s04-edition-coverage-reconciliation";
export const MILESTONE = "M209-2yg6ix";
export const SLICE = "S04";
export const TASK = "T02";
export const ARTIFACT_RECOUNT = "prd/migration/rust-evidence/m209-s04-corpus-recount-evidence.json";
export const ARTIFACT_RECONCILIATION =
  "prd/migration/rust-evidence/m209-s04-edition-coverage-reconciliation.json";
export const OUT_PREFIX = "prd/migration/rust-evidence/m209-s04-";
export const S03_FAMILY_DENOMINATOR = "prd/migration/rust-evidence/m209-s03-family-denominator.json";
export const S03_EDITION_DELTA = "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json";

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const EDITION_DIR_TAIL = "exports/npa/law_2013-04-05_44-fz";
const MANIFEST_TAIL = "manifest_layer1_44fz_and_amending_laws.jsonl";
const CHAIN_ID = "cc:44-fz";
const CORPUS_PREFIX = "consru_export/";

// The frozen m209 chain pins. They are re-derived from the live corpus below;
// agreement with the live bytes is a re-derivation, never a hand-typed
// measurement (D539). A disagreement fails closed as
// `corpus_recount_disagreement`.
export const FROZEN_PINS = Object.freeze({
  editions_files_total: 118,
  editions_bytes_total: 508427429,
  editions_listing_sha256:
    "sha256:bdacfd380ae21e768d3673239bd6b6251c36ff9e8169c6d3a220c710873d02f2",
  manifest_records_total: 122,
  manifest_bytes_total: 70276,
  manifest_sha256:
    "sha256:d11a58737ecd0131065539c85daac3db723717b46a982acbad55d2399051210a",
  windows_total: 117,
});

// The listing digest rule reproduced from the S03 emitter: per file the
// `\0`-separated relative path and decimal size, terminated by `\n`,
// concatenated in ascending relative-path order. The relative path is relative
// to the digested directory itself.
export const LISTING_RULE =
  "sha256 over the concatenation of `<relative-path>\\u0000<size>\\n` for every file, sorted by ascending relative path (byte order); the relative path is relative to the digested directory";

export const NAME_RULE =
  "an admitted edition file is a file whose name starts with `edition-` and ends with `.xml`; it must also parse as `edition-<number>_rev-<token>_from-<token>_<hex>.xml`, otherwise the name is an unparsed residual";

export const DATE_RULE =
  "the act date of a manifest record is the first `DD.MM.YYYY` that follows the Russian `Federal law of` title prefix, rendered as ISO `YYYY-MM-DD`; a record without that pattern has no act date";

// The closed, documented fail-closed vocabulary. The contract test asserts
// that this exact set is emittable (each code fires on a mutated input) and
// that no undocumented code can be raised.
export const FAIL_CLOSED_CODES = Object.freeze([
  "artifact_empty",
  "corpus_recount_disagreement",
  "count_partition_mismatch",
  "edition_dir_extra_file",
  "edition_dir_unreadable",
  "edition_name_unparsed",
  "evidence_drift",
  "input_absent",
  "input_artifact_shape_invalid",
  "non_ascii_evidence",
  "out_absolute",
  "out_not_evidence_path",
  "out_of_repo_out",
  "out_symlink_target",
  "path_not_repository_relative",
  "promotion_claim_present",
  "raw_text_leak",
  "window_listing_disagreement",
  "zero_denominator",
]);

export const NON_CLAIMS = Object.freeze([
  "coverage-is-limited-to-one-named-chain (cc:44-fz): this reconciliation partitions the 118 editions of the single 44-fz edition directory against the act dates of one provider manifest; it is not every-edition coverage and not every amending act of the corpus.",
  "revision-date-is-not-a-legal-ground (D289/D415): a revision label records the provider's edition date, never the commencement, applicability, transitional or legal effect of any provision.",
  "act-date-and-revision-date-agreement-is-a-structural-match-and-not-a-proof-of-causality: an amending act whose title date equals a revision date is counted as date-matched, and no causal, amending, in-force or normative relation is asserted by that match.",
  "r070-stays-active (D416) and r035-stays-active (D430): no requirement record is mutated by this artifact and no promotion gate is promoted, satisfied or moved off unsatisfied (D540: the punkt stays not-adopted).",
  "no-corpus-text-is-copied-into-this-artifact: no XML bytes, no article text, no provider titles, no offline URIs and no document keys; only counts, repository-relative paths, byte counts, sha256 pins, ISO dates and law-number digits.",
  "the-licensed-corpus-under-consru_export-is-untracked-by-design and is read read-only; nothing is written into the corpus and no corpus byte is persisted.",
  "live-recount-agreement-runs-on-two-independent-legs: the frozen m209 chain pins and the tracked s03 declarations; a disagreement fails closed instead of trusting either side.",
  "edition-to-act-correspondence-is-many-to-many: the date-matched editions and the date-matched amending acts share the same distinct revision dates, so no bijection between editions and amending acts is claimed.",
  "no-proof-package-is-attached-to-any-gate and no gate state is changed by this artifact.",
  "listing-digest-rule-is-re-derived-here (names plus sizes, deterministic order) and reproduces the frozen s03 pin; the corpus envelope is measured live, never taken from an inventory counter (D539).",
  "a-zero-denominator-is-not-a-measurement: an empty edition listing or an empty manifest fails closed as zero_denominator.",
]);

// Provider prose markers that must never reach a count-only artifact.
const RAW_TEXT_MARKERS = Object.freeze([
  "consultantplus://",
  "<w:",
  "screenTip",
  "\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d",
]);
// Corpus field names that must never appear as artifact keys.
const FORBIDDEN_ARTIFACT_KEYS = Object.freeze(['"offline_uri"', '"document_key"', '"title"']);

const ADMITTED_EDITION_NAME = /^edition-(\d{4,})_rev-([A-Za-z0-9._-]{1,64})_from-([A-Za-z0-9._-]{1,64})_([0-9a-f]{8,64})\.xml$/;
// Russian `Federal law of` + `DD.MM.YYYY`, kept as \u escapes so this source
// file stays pure ASCII.
const ACT_DATE_RE =
  /\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d \u043e\u0442\s*(\d{2})\.(\d{2})\.(\d{4})/;
const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DIR_DATE_RE = /^law_(\d{4}-\d{2}-\d{2})_(\d+)-fz$/;

export class RecountError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "RecountError";
    this.code = code;
    this.detail = detail;
  }
}

export function fail(code, detail) {
  throw new RecountError(code, detail);
}

// ---------------------------------------------------------------------------
// small guard helpers
// ---------------------------------------------------------------------------

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

/// The count-only surface: no provider prose, no corpus field name and no
/// corpus text may survive into an artifact.
export function assertNoRawText(text) {
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) fail("raw_text_leak", `artifact carries ${marker}`);
  }
  for (const key of FORBIDDEN_ARTIFACT_KEYS) {
    if (text.includes(key)) fail("raw_text_leak", `artifact carries corpus key ${key}`);
  }
  return true;
}

/// Exact check against the live manifest: no record title may appear in the
/// rendered artifact, in whole or as a trimmed fragment.
export function assertNoCorpusText(text, view) {
  const manifest = parseManifest(view.manifestBytes);
  for (const record of manifest.records) {
    const title = record.title.trim();
    if (title.length >= 8 && text.includes(title)) {
      fail("raw_text_leak", `artifact carries manifest title of record ${record.index + 1}`);
    }
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

// ---------------------------------------------------------------------------
// corpus resolution and read-only loading
// ---------------------------------------------------------------------------

export function corpusExportDir(env = process.env) {
  const fromEnv = env[EXPORT_DIR_ENV];
  return typeof fromEnv === "string" && fromEnv.trim() !== "" ? fromEnv.trim() : EXPORT_DIR_DEFAULT;
}

export function exportRootRelative(env = process.env) {
  return `${corpusExportDir(env)}/${EXPORT_ROOT_TAIL}`;
}

export function editionDirRelative(env = process.env) {
  return `${exportRootRelative(env)}/${EDITION_DIR_TAIL}`;
}

export function manifestRelative(env = process.env) {
  return `${exportRootRelative(env)}/${MANIFEST_TAIL}`;
}

/// Lists the chain directory read-only and returns the raw count-only view the
/// pure derivations consume. A directory that cannot be listed fails closed.
export function loadCorpusView(env = process.env, probes = {}) {
  const readdir = probes.readdirSync ?? readdirSync;
  const stat = probes.statSync ?? statSync;
  const read = probes.readFileSync ?? readFileSync;
  const exists = probes.existsSync ?? existsSync;
  const root = probes.repoRoot ?? REPO_ROOT;

  const dirRelative = editionDirRelative(env);
  const manRelative = manifestRelative(env);
  assertRepoRelative(dirRelative, "edition directory");
  assertRepoRelative(manRelative, "manifest");

  const dirAbsolute = path.join(root, dirRelative);
  let names;
  try {
    names = readdir(dirAbsolute);
  } catch (error) {
    fail("edition_dir_unreadable", `${dirRelative}: ${error.code ?? error.message}`);
  }
  const editionFiles = [];
  for (const name of names) {
    let entry;
    try {
      entry = stat(path.join(dirAbsolute, name));
    } catch (error) {
      fail("edition_dir_unreadable", `${dirRelative}/${name}: ${error.code ?? error.message}`);
    }
    if (!entry.isFile()) continue;
    editionFiles.push({ name, size: entry.size });
  }
  editionFiles.sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0));

  const manifestAbsolute = path.join(root, manRelative);
  if (!exists(manifestAbsolute)) fail("input_absent", manRelative);
  let manifestBytes;
  try {
    manifestBytes = read(manifestAbsolute);
  } catch (error) {
    fail("input_absent", `${manRelative}: ${error.code ?? error.message}`);
  }

  return { editionDirRelative: dirRelative, manifestRelative: manRelative, editionFiles, manifestBytes };
}

export function loadJsonArtifact(relativePath, label, probes = {}) {
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
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    fail("input_artifact_shape_invalid", `${relativePath}: ${error.message}`);
  }
  const bytes = Buffer.from(text, "utf8");
  return {
    relative_path: relativePath,
    bytes: bytes.length,
    sha256: sha256Pin(bytes),
    parsed,
  };
}

export function loadS03Inputs(probes = {}) {
  const family = loadJsonArtifact(S03_FAMILY_DENOMINATOR, "s03 family denominator", probes);
  const delta = loadJsonArtifact(S03_EDITION_DELTA, "s03 edition delta", probes);
  return {
    familyDenominator: family.parsed,
    editionDelta: delta.parsed,
    pins: [pinRow("s03_family_denominator", family), pinRow("s03_edition_delta", delta)],
  };
}

function pinRow(inputId, loaded) {
  return {
    input_id: inputId,
    input_kind: "file",
    relative_path: loaded.relative_path,
    bytes: loaded.bytes,
    sha256: loaded.sha256,
  };
}

// ---------------------------------------------------------------------------
// name, date and digest primitives
// ---------------------------------------------------------------------------

export function sha256Hex(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

export function sha256Pin(bytes) {
  return `sha256:${sha256Hex(bytes)}`;
}

export function isAdmittedEditionName(name) {
  return typeof name === "string" && name.startsWith("edition-") && name.endsWith(".xml");
}

export function parseEditionName(name) {
  const match = ADMITTED_EDITION_NAME.exec(name);
  if (match === null) return null;
  return {
    edition_number: Number(match[1]),
    revision_token: match[2],
    from_token: match[3],
    content_token: match[4],
  };
}

export function parseActDate(title) {
  if (typeof title !== "string") return null;
  const match = ACT_DATE_RE.exec(title);
  if (match === null) return null;
  return `${match[3]}-${match[2]}-${match[1]}`;
}

export function isIsoDate(token) {
  if (typeof token !== "string") return false;
  const match = ISO_DATE_RE.exec(token);
  if (match === null) return false;
  const month = Number(match[2]);
  const day = Number(match[3]);
  return month >= 1 && month <= 12 && day >= 1 && day <= 31;
}

export function editionDirToken(relativePath) {
  const base = path.basename(relativePath);
  const match = DIR_DATE_RE.exec(base);
  if (match === null) return null;
  return { date: match[1], law_digits: match[2] };
}

export function listingBytes(editionFiles) {
  let total = 0;
  for (const file of editionFiles) total += file.size;
  return total;
}

export function listingDigest(editionFiles) {
  let listing = "";
  for (const file of editionFiles) listing += `${file.name}\0${file.size}\n`;
  return sha256Pin(Buffer.from(listing, "utf8"));
}

function manifestText(manifestBytes) {
  if (typeof manifestBytes === "string") return manifestBytes;
  return Buffer.from(manifestBytes).toString("utf8");
}

export function parseManifest(manifestBytes) {
  const text = manifestText(manifestBytes);
  const lines = text.split("\n").filter((line) => line.trim() !== "");
  const records = [];
  for (let index = 0; index < lines.length; index += 1) {
    let record;
    try {
      record = JSON.parse(lines[index]);
    } catch (error) {
      fail("input_artifact_shape_invalid", `manifest line ${index + 1}: ${error.message}`);
    }
    if (record === null || typeof record !== "object") {
      fail("input_artifact_shape_invalid", `manifest line ${index + 1} is not an object`);
    }
    if (typeof record.is_core_act !== "boolean") {
      fail("input_artifact_shape_invalid", `manifest line ${index + 1} carries no boolean is_core_act`);
    }
    const title = typeof record.title === "string" ? record.title : "";
    const lawNumber = typeof record.law_number === "string" ? record.law_number : "";
    records.push({
      index,
      is_core_act: record.is_core_act,
      act_date: parseActDate(title),
      law_number_digits: (lawNumber.match(/\d+/) ?? [""])[0],
      title,
    });
  }
  return { records_total: lines.length, records, bytes_total: Buffer.from(text, "utf8").length };
}

// ---------------------------------------------------------------------------
// independent edition enumeration and coverage partition
// ---------------------------------------------------------------------------

export function computeEditions(editionFiles) {
  if (!Array.isArray(editionFiles)) {
    fail("input_artifact_shape_invalid", "the edition listing is not an array");
  }
  let unaccepted = 0;
  let unparsed = 0;
  const rows = [];
  for (const file of editionFiles) {
    if (
      file === null ||
      typeof file !== "object" ||
      typeof file.name !== "string" ||
      !Number.isInteger(file.size) ||
      file.size < 0
    ) {
      fail("input_artifact_shape_invalid", "a listing row is not { name, size }");
    }
    if (!isAdmittedEditionName(file.name)) {
      unaccepted += 1;
      continue;
    }
    const parsed = parseEditionName(file.name);
    if (parsed === null) {
      unparsed += 1;
      continue;
    }
    rows.push({ ...parsed, name: file.name, size: file.size });
  }
  if (unaccepted > 0) {
    fail("edition_dir_extra_file", `${unaccepted} non-admitted file(s) in the chain directory`);
  }
  if (unparsed > 0) {
    fail("edition_name_unparsed", `${unparsed} admitted edition name(s) do not parse`);
  }
  rows.sort((left, right) => left.edition_number - right.edition_number);
  return {
    rows,
    files_total: editionFiles.length,
    accepted_total: rows.length,
    unaccepted_total: unaccepted,
    unparsed_total: unparsed,
    parsed_total: rows.length,
  };
}

/// The whole live measurement: counts, the class partition, the named
/// residuals and the S03 window correspondence. Fails closed on the first
/// violated invariant, in the documented order.
export function computeRecount(view, s03 = null) {
  assertRepoRelative(view.editionDirRelative, "edition directory");
  assertRepoRelative(view.manifestRelative, "manifest");
  if (!view.editionDirRelative.startsWith(`${corpusExportDir()}/`)) {
    fail("path_not_repository_relative", `edition directory outside ${CORPUS_PREFIX}`);
  }
  if (s03 !== null) assertS03Shape(s03);

  const editions = computeEditions(view.editionFiles);
  const manifest = parseManifest(view.manifestBytes);
  if (editions.parsed_total === 0) {
    fail("zero_denominator", "the live edition listing carries no admitted edition file");
  }
  if (manifest.records_total === 0) {
    fail("zero_denominator", "the live layer1 manifest carries no record");
  }

  const revisionDates = new Set(
    editions.rows.map((row) => row.revision_token).filter((token) => isIsoDate(token)),
  );
  const actDates = new Set(
    manifest.records.map((record) => record.act_date).filter((date) => date !== null),
  );

  const coreRows = editions.rows.filter((row) => row.revision_token === "initial");
  if (coreRows.length !== 1) {
    fail("count_partition_mismatch", `the listing carries ${coreRows.length} initial edition(s)`);
  }
  const strayTokens = editions.rows.filter(
    (row) => row.revision_token !== "initial" && !isIsoDate(row.revision_token),
  );
  if (strayTokens.length > 0) {
    fail(
      "count_partition_mismatch",
      `${strayTokens.length} edition(s) carry a revision token that is neither initial nor an ISO date`,
    );
  }

  const matchedRows = editions.rows.filter(
    (row) => row.revision_token !== "initial" && actDates.has(row.revision_token),
  );
  const unnamedRows = editions.rows.filter(
    (row) => row.revision_token !== "initial" && !actDates.has(row.revision_token),
  );
  const classesTotal = coreRows.length + matchedRows.length;
  if (classesTotal !== editions.parsed_total) {
    fail(
      "count_partition_mismatch",
      `${classesTotal} classified edition(s) do not sum to ${editions.parsed_total}`,
    );
  }

  const coreRecords = manifest.records.filter((record) => record.is_core_act);
  const amendingRecords = manifest.records.filter((record) => !record.is_core_act);
  const amendingWithDate = amendingRecords.filter((record) => record.act_date !== null);
  const amendingWithoutDate = amendingRecords.length - amendingWithDate.length;
  const amendingMatched = amendingWithDate.filter((record) => revisionDates.has(record.act_date));
  const withoutDistinctEdition =
    amendingWithDate.length - amendingMatched.length + amendingWithoutDate;
  const collapse = editions.rows.filter((row) => isIsoDate(row.revision_token)).length -
    revisionDates.size;

  const classes = [
    {
      class_id: "core-act-initial-edition",
      count: coreRows.length,
      edition_numbers: coreRows.map((row) => row.edition_number),
      rule:
        "the single edition whose revision token is `initial`; it is the core act 44-fz, it must be edition 1 and it must be the only initial token in the listing",
    },
    {
      class_id: "amending-act-date-matched",
      count: matchedRows.length,
      distinct_revision_dates: revisionDates.size,
      rule:
        "an edition whose revision token is an ISO date equal to the title date parsed from at least one manifest record with is_core_act false",
    },
  ];
  const residuals = [
    {
      residual_id: "manifest-amending-act-without-distinct-edition",
      count: withoutDistinctEdition,
      expected_zero: false,
      rule:
        "manifest records with is_core_act false whose parsed title date is absent from the live revision dates, plus amending records with no parseable title date",
    },
    {
      residual_id: "same-revision-date-collapse",
      count: collapse,
      expected_zero: false,
      rule:
        "revision-dated editions minus distinct revision dates: several amending acts collapse onto one revision date",
    },
    {
      residual_id: "edition-without-manifest-date",
      count: unnamedRows.length,
      expected_zero: true,
      rule:
        "editions whose revision token is neither `initial` nor a manifest act date; any non-zero value also breaks the class partition and fails closed",
    },
  ];

  const coreRecord = coreRecords.length === 1 ? coreRecords[0] : null;
  const dirToken = editionDirToken(view.editionDirRelative);
  const lawDigits = coreRecord === null ? null : coreRecord.law_number_digits;

  const listingSha = listingDigest(view.editionFiles);
  const counted = {
    editions_files_total: editions.files_total,
    editions_accepted_total: editions.accepted_total,
    editions_unaccepted_total: editions.unaccepted_total,
    editions_parsed_total: editions.parsed_total,
    editions_unparsed_total: editions.unparsed_total,
    editions_initial_total: coreRows.length,
    editions_revision_dated_total: editions.parsed_total - coreRows.length,
    editions_distinct_revision_dates_total: revisionDates.size,
    editions_distinct_from_tokens_total: new Set(editions.rows.map((row) => row.from_token)).size,
    editions_bytes_total: listingBytes(view.editionFiles),
    editions_listing_sha256: listingSha,
    manifest_records_total: manifest.records_total,
    manifest_bytes_total: Buffer.from(manifestText(view.manifestBytes), "utf8").length,
    manifest_sha256: sha256Pin(Buffer.from(manifestText(view.manifestBytes), "utf8")),
    manifest_core_acts_total: coreRecords.length,
    manifest_amending_acts_total: amendingRecords.length,
    manifest_records_with_act_date_total: manifest.records.filter((r) => r.act_date !== null).length,
    manifest_amending_acts_with_act_date_total: amendingWithDate.length,
    manifest_amending_acts_date_matched_total: amendingMatched.length,
    manifest_distinct_act_dates_total: actDates.size,
    classes_total: classesTotal,
    windows_total: s03 === null ? 0 : s03.editionDelta.windows.length,
  };

  return {
    counted,
    classes,
    residuals,
    rows: editions.rows,
    manifest,
    revisionDates,
    actDates,
    core_act: {
      core_acts_total: coreRecords.length,
      core_act_index: coreRecord === null ? null : coreRecord.index,
      core_act_title_date: coreRecord === null ? null : coreRecord.act_date,
      directory_date_token: dirToken === null ? null : dirToken.date,
      directory_law_digits: dirToken === null ? null : dirToken.law_digits,
      law_number_digits: lawDigits,
    },
    editions,
  };
}

export function computePromotionChecks(s03) {
  const rows = [];
  for (const [label, artifact] of [
    ["family_denominator", s03.familyDenominator],
    ["edition_delta", s03.editionDelta],
  ]) {
    rows.push({
      check_id: `${label}_authoritative_false`,
      verdict: artifact.authoritative === false ? "pass" : "fail",
      observed: String(artifact.authoritative),
    });
    rows.push({
      check_id: `${label}_requirement_disposition_active`,
      verdict: artifact.disposition === "active" ? "pass" : "fail",
      observed: String(artifact.disposition),
    });
    for (const key of [
      "gates_promoted",
      "legs_promoted",
      "proof_packages_attached",
      "requirement_records_mutated",
    ]) {
      const value = artifact[key] === undefined ? 0 : artifact[key];
      rows.push({
        check_id: `${label}_${key}_zero`,
        verdict: value === 0 ? "pass" : "fail",
        observed: String(value),
      });
    }
  }
  const failed = rows.filter((row) => row.verdict !== "pass");
  if (failed.length > 0) {
    fail("promotion_claim_present", failed.map((row) => row.check_id).join(","));
  }
  return rows;
}

export function computeWindows(editionRows, s03Windows) {
  const byNumber = new Map(editionRows.map((row) => [row.edition_number, row]));
  const mismatches = [];
  for (const window of s03Windows) {
    const from = byNumber.get(window.from_edition);
    const to = byNumber.get(window.to_edition);
    const ok =
      from !== undefined &&
      to !== undefined &&
      window.revision_from === from.revision_token &&
      window.revision_to === to.revision_token;
    if (!ok) mismatches.push(window.from_edition);
  }
  if (mismatches.length > 0) {
    fail(
      "window_listing_disagreement",
      `${mismatches.length} s03 window(s) disagree with the live listing: ${mismatches.slice(0, 5).join(",")}`,
    );
  }
  return {
    windows_total: s03Windows.length,
    windows_checked: s03Windows.length,
    mismatches_total: 0,
    mismatch_windows: [],
    stream_sha256: windowStreamDigest(s03Windows),
    rule:
      "for every s03 window (from_edition, to_edition) the declared revision_from and revision_to must equal the live revision tokens of those two edition numbers",
  };
}

function windowStreamDigest(s03Windows) {
  let stream = "";
  for (const window of s03Windows) {
    stream += `${window.from_edition}|${window.revision_from}|${window.to_edition}|${window.revision_to}\n`;
  }
  return sha256Pin(Buffer.from(stream, "utf8"));
}

export function assertS03Shape(s03) {
  if (s03 === null || typeof s03 !== "object") {
    fail("input_artifact_shape_invalid", "the s03 inputs are not an object");
  }
  const chain = s03.familyDenominator === null || typeof s03.familyDenominator !== "object"
    ? null
    : s03.familyDenominator.chain;
  if (chain === null || typeof chain !== "object") {
    fail("input_artifact_shape_invalid", "the family denominator carries no chain block");
  }
  for (const key of ["editions_total", "input_bytes"]) {
    if (!Number.isInteger(chain[key])) {
      fail("input_artifact_shape_invalid", `family denominator chain.${key} is not an integer`);
    }
  }
  if (typeof chain.input_sha256 !== "string") {
    fail("input_artifact_shape_invalid", "family denominator chain.input_sha256 is not a string");
  }
  const denominator =
    s03.editionDelta === null || typeof s03.editionDelta !== "object"
      ? null
      : s03.editionDelta.denominator;
  if (denominator === null || typeof denominator !== "object") {
    fail("input_artifact_shape_invalid", "the edition delta carries no denominator block");
  }
  for (const key of [
    "editions_total",
    "editions_processed",
    "editions_unreadable",
    "editions_unparsed_filename",
    "edition_dir_files_total",
    "edition_dir_bytes_total",
    "windows_total",
  ]) {
    if (!Number.isInteger(denominator[key])) {
      fail("input_artifact_shape_invalid", `edition delta denominator.${key} is not an integer`);
    }
  }
  if (typeof denominator.edition_dir_listing_sha256 !== "string") {
    fail("input_artifact_shape_invalid", "edition delta listing digest is not a string");
  }
  const windows = s03.editionDelta.windows;
  if (!Array.isArray(windows) || windows.length === 0) {
    fail("input_artifact_shape_invalid", "the edition delta carries no window list");
  }
  for (const window of windows) {
    if (
      window === null ||
      typeof window !== "object" ||
      !Number.isInteger(window.from_edition) ||
      !Number.isInteger(window.to_edition) ||
      typeof window.revision_from !== "string" ||
      typeof window.revision_to !== "string"
    ) {
      fail("input_artifact_shape_invalid", "an edition delta window is not well formed");
    }
  }
  return true;
}

/// The frozen-pin leg plus the tracked-s03-declaration leg. A disagreement on
/// either leg fails closed as `corpus_recount_disagreement`.
export function computeCrossChecks(counted, s03) {
  const chain = s03.familyDenominator.chain;
  const denominator = s03.editionDelta.denominator;
  const manifestFamily = s03.familyDenominator.families.find(
    (family) => family.family_id === "manifest_layer1_44fz_and_amending_laws",
  );
  if (manifestFamily === undefined) {
    fail("input_artifact_shape_invalid", "the family denominator carries no layer1 manifest family");
  }

  const rows = [
    crossRow("frozen_pin_editions_files", "m209 chain pin", FROZEN_PINS.editions_files_total, counted.editions_files_total),
    crossRow("frozen_pin_editions_bytes", "m209 chain pin", FROZEN_PINS.editions_bytes_total, counted.editions_bytes_total),
    crossRow("frozen_pin_editions_listing_sha256", "m209 chain pin", FROZEN_PINS.editions_listing_sha256, counted.editions_listing_sha256),
    crossRow("frozen_pin_manifest_records", "m209 chain pin", FROZEN_PINS.manifest_records_total, counted.manifest_records_total),
    crossRow("frozen_pin_manifest_bytes", "m209 chain pin", FROZEN_PINS.manifest_bytes_total, counted.manifest_bytes_total),
    crossRow("frozen_pin_manifest_sha256", "m209 chain pin", FROZEN_PINS.manifest_sha256, counted.manifest_sha256),
    crossRow("frozen_pin_windows_total", "m209 chain pin", FROZEN_PINS.windows_total, counted.windows_total),
    crossRow("s03_chain_editions_total", `${S03_FAMILY_DENOMINATOR}#chain.editions_total`, chain.editions_total, counted.editions_files_total),
    crossRow("s03_chain_input_bytes", `${S03_FAMILY_DENOMINATOR}#chain.input_bytes`, chain.input_bytes, counted.editions_bytes_total),
    crossRow("s03_chain_input_sha256", `${S03_FAMILY_DENOMINATOR}#chain.input_sha256`, chain.input_sha256, counted.editions_listing_sha256),
    crossRow("s03_chain_edition_matching", `${S03_FAMILY_DENOMINATOR}#chain.decomposition.edition_matching`, chain.decomposition.edition_matching, counted.editions_accepted_total),
    crossRow("s03_chain_edition_unparsed", `${S03_FAMILY_DENOMINATOR}#chain.decomposition.edition_unparsed`, chain.decomposition.edition_unparsed, counted.editions_unparsed_total + counted.editions_unaccepted_total),
    crossRow("s03_manifest_records_total", `${S03_FAMILY_DENOMINATOR}#families.layer1.records_total`, manifestFamily.records_total, counted.manifest_records_total),
    crossRow("s03_manifest_input_bytes", `${S03_FAMILY_DENOMINATOR}#families.layer1.input_bytes`, manifestFamily.input_bytes, counted.manifest_bytes_total),
    crossRow("s03_manifest_input_sha256", `${S03_FAMILY_DENOMINATOR}#families.layer1.input_sha256`, manifestFamily.input_sha256, counted.manifest_sha256),
    crossRow("s03_manifest_core_acts", `${S03_FAMILY_DENOMINATOR}#families.layer1.decomposition.core_acts`, manifestFamily.decomposition.core_acts, counted.manifest_core_acts_total),
    crossRow("s03_manifest_amending_acts", `${S03_FAMILY_DENOMINATOR}#families.layer1.decomposition.amending_acts`, manifestFamily.decomposition.amending_acts, counted.manifest_amending_acts_total),
    crossRow("s03_delta_editions_total", `${S03_EDITION_DELTA}#denominator.editions_total`, denominator.editions_total, counted.editions_files_total),
    crossRow("s03_delta_editions_processed", `${S03_EDITION_DELTA}#denominator.editions_processed`, denominator.editions_processed, counted.editions_parsed_total),
    crossRow("s03_delta_editions_unreadable", `${S03_EDITION_DELTA}#denominator.editions_unreadable`, denominator.editions_unreadable, 0),
    crossRow("s03_delta_editions_unparsed_filename", `${S03_EDITION_DELTA}#denominator.editions_unparsed_filename`, denominator.editions_unparsed_filename, counted.editions_unparsed_total),
    crossRow("s03_delta_listing_sha256", `${S03_EDITION_DELTA}#denominator.edition_dir_listing_sha256`, denominator.edition_dir_listing_sha256, counted.editions_listing_sha256),
    crossRow("s03_delta_edition_dir_bytes", `${S03_EDITION_DELTA}#denominator.edition_dir_bytes_total`, denominator.edition_dir_bytes_total, counted.editions_bytes_total),
    crossRow("s03_delta_edition_dir_files", `${S03_EDITION_DELTA}#denominator.edition_dir_files_total`, denominator.edition_dir_files_total, counted.editions_files_total),
    crossRow("s03_delta_windows_total", `${S03_EDITION_DELTA}#denominator.windows_total`, denominator.windows_total, counted.windows_total),
  ];

  const failed = rows.filter((row) => row.verdict !== "pass");
  if (failed.length > 0) {
    fail("corpus_recount_disagreement", failed.map((row) => row.check_id).join(","));
  }
  return rows;
}

function crossRow(checkId, source, declared, observed) {
  return {
    check_id: checkId,
    source,
    declared,
    observed,
    verdict: declared === observed ? "pass" : "fail",
  };
}

// ---------------------------------------------------------------------------
// bundles
// ---------------------------------------------------------------------------

const ENVELOPE_COMMON = {
  schema_version: 1,
  milestone: MILESTONE,
  slice: SLICE,
  task: TASK,
  lifecycle: "[bounded]",
  authoritative: false,
  count_only: true,
  ascii_only: true,
  requirement_id: "R070",
  requirement_dispositions: { R035: "active", R070: "active" },
  disposition_decision: "D416",
  owner_decision: "D558",
  gates_promoted: 0,
  legs_promoted: 0,
  proof_packages_attached: 0,
  requirement_records_mutated: 0,
};

function buildInputs(view, pins) {
  return [
    {
      input_id: "editions_listing",
      input_kind: "directory-listing",
      relative_path: view.editionDirRelative,
      bytes: listingBytes(view.editionFiles),
      sha256: listingDigest(view.editionFiles),
    },
    {
      input_id: "manifest_layer1",
      input_kind: "file",
      relative_path: view.manifestRelative,
      bytes: parseManifest(view.manifestBytes).bytes_total,
      sha256: sha256Pin(Buffer.from(manifestText(view.manifestBytes), "utf8")),
    },
    ...pins,
  ];
}

/// The live recount artifact. `mode` selects which artifacts the CLI writes;
/// it is deliberately not rendered, so that every artifact is mode-independent
/// and `--check` reproduces the committed bytes under any mode.
export function recountBundle(view, s03) {
  const recount = computeRecount(view, s03);
  const cross = computeCrossChecks(recount.counted, s03);
  const promotion = computePromotionChecks(s03);
  const counted = recount.counted;
  return {
    schema: SCHEMA_RECOUNT,
    ...ENVELOPE_COMMON,
    kind: KIND_RECOUNT,
    chain_id: CHAIN_ID,
    recount_scope:
      "live read-only recount of the 44-fz edition directory listing and the layer1 manifest, cross-checked against the frozen m209 chain pins and the tracked s03 declarations",
    listing_rule: LISTING_RULE,
    name_rule: NAME_RULE,
    date_rule: DATE_RULE,
    counted,
    core_act: recount.core_act,
    inputs: buildInputs(view, s03.pins),
    cross_checks: cross,
    promotion_checks: promotion,
    windows: computeWindows(recount.rows, s03.editionDelta.windows),
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };
}

/// The edition-coverage reconciliation artifact. `mode` is deliberately not
/// rendered here either (see `recountBundle`).
export function coverageBundle(view, s03) {
  const recount = computeRecount(view, s03);
  const cross = computeCrossChecks(recount.counted, s03);
  const promotion = computePromotionChecks(s03);
  const windows = computeWindows(recount.rows, s03.editionDelta.windows);
  return {
    schema: SCHEMA_RECONCILIATION,
    ...ENVELOPE_COMMON,
    kind: KIND_RECONCILIATION,
    chain_id: CHAIN_ID,
    reconciliation_scope:
      "the 118 live editions partitioned into named coverage classes against the act dates of the layer1 manifest, with every remaining act declared under a named residual code and zero silently lost editions",
    classes_total: recount.counted.classes_total,
    editions_total: recount.counted.editions_files_total,
    classes: recount.classes,
    residuals: recount.residuals,
    residual_unmatched_total: recount.residuals[0].count,
    residual_collapse_total: recount.residuals[1].count,
    residual_unnamed_total: recount.residuals[2].count,
    manifest_amending_acts_total: recount.counted.manifest_amending_acts_total,
    manifest_amending_acts_with_act_date_total:
      recount.counted.manifest_amending_acts_with_act_date_total,
    distinct_revision_dates_total: recount.counted.editions_distinct_revision_dates_total,
    windows,
    listing_rule: LISTING_RULE,
    name_rule: NAME_RULE,
    date_rule: DATE_RULE,
    inputs: buildInputs(view, s03.pins),
    cross_checks: cross,
    promotion_checks: promotion,
    fail_closed_codes: [...FAIL_CLOSED_CODES],
    non_claims: [...NON_CLAIMS],
  };
}

export function heartbeat(counted, coverage, mode) {
  return [
    `mode=${mode}`,
    `editions=${counted.editions_files_total}`,
    `matched=${coverage.classes[1].count}`,
    `initial=${coverage.classes[0].count}`,
    `windows_checked=${coverage.windows.windows_checked}`,
    "drift=0",
    `residual_unmatched=${coverage.residual_unmatched_total}`,
    `residual_collapse=${coverage.residual_collapse_total}`,
    `residual_unnamed=${coverage.residual_unnamed_total}`,
    `cross=${coverage.cross_checks.length}`,
    "failed=0",
  ].join(" ");
}

// ---------------------------------------------------------------------------
// output containment, rendering and CLI
// ---------------------------------------------------------------------------

/// `--out` containment: reject absolute targets, targets escaping the
/// repository (after canonicalizing the parent directory), symlinked targets
/// and any repository path outside the evidence allowlist
/// `prd/migration/rust-evidence/m209-s04-*.json`.
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

function parseArgs(argv) {
  const options = { mode: "all", out: null, check: false, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") {
      index += 1;
      if (index >= argv.length) return { error: "--mode requires a value" };
      options.mode = argv[index];
      if (!["recount", "editions", "all"].includes(options.mode)) {
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
  "usage: m209_s04_corpus_recount.mjs [--mode recount|editions|all] [--out PATH] [--check]\n";

/// The `--out` override applies to the primary artifact of the selected mode:
/// the recount artifact for `recount` / `all`, the reconciliation artifact for
/// `editions`. Every other artifact keeps its canonical path.
export function resolveTargets(options) {
  const targets = [];
  if (options.mode !== "editions") {
    const target = resolveOutTarget(options.out === null ? ARTIFACT_RECOUNT : options.out);
    targets.push({ artifact_id: "recount", ...target });
  }
  if (options.mode !== "recount") {
    const primary = options.mode === "editions" && options.out !== null
      ? options.out
      : ARTIFACT_RECONCILIATION;
    targets.push({ artifact_id: "reconciliation", ...resolveOutTarget(primary) });
  }
  return targets;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.error !== undefined) {
    process.stderr.write(`${USAGE}m209_s04_corpus_recount: ${options.error}\n`);
    process.exit(2);
  }
  if (options.help) {
    process.stdout.write(USAGE);
    return;
  }
  const targets = resolveTargets(options);
  const view = loadCorpusView();
  const s03 = loadS03Inputs();
  const recount = recountBundle(view, s03);
  const coverage = coverageBundle(view, s03);
  const rendered = {
    recount: renderEvidence(recount),
    reconciliation: renderEvidence(coverage),
  };
  for (const text of Object.values(rendered)) {
    assertNonEmpty(text);
    assertAsciiOnly(text);
    assertNoRawText(text);
    assertNoCorpusText(text, view);
  }
  const summary = heartbeat(recount.counted, coverage, options.mode);
  for (const target of targets) {
    const text = rendered[target.artifact_id];
    if (options.check) {
      if (!existsSync(target.absolute)) {
        fail("evidence_drift", `missing committed artifact ${target.repoRelative}`);
      }
      checkRenderedBytes(text, readFileSync(target.absolute, "utf8"));
    } else {
      atomicWrite(target.absolute, text);
    }
  }
  process.stdout.write(`M209_S04_CORPUS_OK ${summary}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (error instanceof RecountError) {
      process.stderr.write(`M209_S04_CORPUS_FAILED error=${error.code} detail=${error.detail}\n`);
      process.exit(4);
    }
    throw error;
  }
}
