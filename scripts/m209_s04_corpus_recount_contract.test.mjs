// M209 S04 T02 contract: the fail-closed live corpus recount and the
// 118-edition causal-coverage reconciliation for the named `cc:44-fz` chain
// (D539 / D560).
//
// The contract is offline and corpus-gated. Every corpus-free assertion runs
// everywhere: the artifact integrity of both evidence files, the arithmetic
// reconciliation, the non-claims, the output containment and a mutation
// negative for every documented fail-closed code. The corpus-gated assertions
// independently repeat the live measurement -- listing digest, name grammar,
// act dates, class partition, residual sums and the s03 window correspondence
// -- and are skipped with `M209_S04_CORPUS_ABSENT` when the untracked licensed
// provider export is not present.
//
// The test never ports the module: its own listing digest, name parser, date
// parser and partition are written from the documented rules. It also asserts
// that the documented fail-closed block, the emitted artifacts and the module
// carry exactly the same code set.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

import {
  ARTIFACT_RECOUNT,
  ARTIFACT_RECONCILIATION,
  FAIL_CLOSED_CODES,
  FROZEN_PINS,
  KIND_RECOUNT,
  KIND_RECONCILIATION,
  SCHEMA_RECOUNT,
  SCHEMA_RECONCILIATION,
  S03_EDITION_DELTA,
  S03_FAMILY_DENOMINATOR,
  assertAsciiOnly,
  assertNoCorpusText,
  assertNoRawText,
  assertNonEmpty,
  assertS03Shape,
  checkRenderedBytes,
  computeCrossChecks,
  computePromotionChecks,
  computeRecount,
  computeWindows,
  coverageBundle,
  editionDirRelative,
  loadCorpusView,
  loadJsonArtifact,
  loadS03Inputs,
  manifestRelative,
  recountBundle,
  renderEvidence,
  resolveOutTarget,
  sha256Pin,
} from "./m209_s04_corpus_recount.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CONTRACT_PATH = "scripts/m209_s04_corpus_recount_contract.test.mjs";
const MODULE_PATH = "scripts/m209_s04_corpus_recount.mjs";
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The heartbeat the milestone closeout greps for.
const EXPECTED_HEARTBEAT = "editions=118 matched=117 initial=1 windows_checked=117 drift=0";

// The documented m209 chain pins, transcribed here independently of the module.
const DOCUMENTED_PINS = Object.freeze({
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

// The documented fail-closed vocabulary, transcribed independently of the
// module. A silent expansion of the module's list must fail this test.
const DOCUMENTED_CODES = Object.freeze([
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

// The artifact must bound its own claims (D289 / D415 / D416 / D539 / D540 / D560).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "limited to one named chain",
  "cc:44-fz",
  "not a legal ground",
  "d289",
  "d415",
  "structural match",
  "causality",
  "no causal",
  "r070-stays-active",
  "r035-stays-active",
  "d416",
  "d430",
  "d540",
  "no requirement record is mutated",
  "no-corpus-text-is-copied-into-this-artifact",
  "read read-only",
  "two-independent-legs",
  "no bijection",
  "no proof package",
  "d539",
  "zero_denominator",
];

// The Russian `Federal law of` title prefix, kept as \u escapes so this source
// file stays pure ASCII.
const ACT_TITLE_PREFIX =
  "\u0424\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u043e\u043d \u043e\u0442 ";
const INDEPENDENT_DATE_RE = new RegExp(`${ACT_TITLE_PREFIX}\\s*(\\d{2})\\.(\\d{2})\\.(\\d{4})`);
const INDEPENDENT_NAME_RE =
  /^edition-(\d+)_rev-([A-Za-z0-9._-]+)_from-([A-Za-z0-9._-]+)_([0-9a-f]+)\.xml$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(ROOT, relative), "utf8");
}

const recountRaw = readRepo(ARTIFACT_RECOUNT);
const coverageRaw = readRepo(ARTIFACT_RECONCILIATION);
const recountArtifact = JSON.parse(recountRaw);
const coverageArtifact = JSON.parse(coverageRaw);

// ---------------------------------------------------------------------------
// synthetic count-only fixture: a valid tiny corpus view
// ---------------------------------------------------------------------------

const SYNTH_DIR = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz";
const SYNTH_MANIFEST = "consru_export/consru_export/manifest_layer1_44fz_and_amending_laws.jsonl";

function synthManifestLine({ core, date }) {
  const lawNumber = core ? "N 44-\u0424\u0417" : "N 188-\u0424\u0417";
  return JSON.stringify({
    bank: "LAW",
    document_key: core ? "synth0001" : "synth0002",
    is_core_act: core,
    law_number: lawNumber,
    offline_uri: "synth-offline",
    title: `${ACT_TITLE_PREFIX}${date} ${lawNumber}`,
  });
}

function synthView(overrides = {}) {
  const manifest = [
    synthManifestLine({ core: true, date: "05.04.2013" }),
    synthManifestLine({ core: false, date: "01.01.2099" }),
  ].join("\n");
  return {
    editionDirRelative: SYNTH_DIR,
    manifestRelative: SYNTH_MANIFEST,
    editionFiles: [
      { name: "edition-0001_rev-initial_from-unknown_aaaaaaaa.xml", size: 10 },
      { name: "edition-0002_rev-2099-01-01_from-unknown_bbbbbbbb.xml", size: 20 },
    ],
    manifestBytes: `${manifest}\n`,
    ...overrides,
  };
}

function mutatedView(mutate) {
  const view = synthView();
  mutate(view);
  return view;
}

let cachedS03 = null;
function s03Model() {
  if (cachedS03 === null) cachedS03 = loadS03Inputs();
  return cachedS03;
}

function syntheticCounted() {
  return computeRecount(synthView(), null).counted;
}

/// Assert that `run()` raises `RecountError` carrying exactly `code`.
function fails(code, run) {
  return () => {
    assert.throws(run, (error) => {
      assert.ok(
        error instanceof Error && error.name === "RecountError",
        `expected RecountError, got ${error?.name}: ${error?.message}`,
      );
      assert.equal(error.code, code, `expected ${code}, got ${error.code}: ${error.detail}`);
      return true;
    });
  };
}

// ---------------------------------------------------------------------------
// (a) documented vocabulary == emittable vocabulary
// ---------------------------------------------------------------------------

const NEGATIVE_CASES = Object.freeze({
  artifact_empty: fails("artifact_empty", () => assertNonEmpty("")),
  corpus_recount_disagreement: fails("corpus_recount_disagreement", () => {
    const s03 = structuredClone({ familyDenominator: s03Model().familyDenominator, editionDelta: s03Model().editionDelta });
    s03.editionDelta.denominator.edition_dir_listing_sha256 = `sha256:${"00".repeat(32)}`;
    return computeCrossChecks(syntheticCounted(), s03);
  }),
  count_partition_mismatch: fails("count_partition_mismatch", () =>
    computeRecount(
      mutatedView((view) => {
        view.editionFiles[1].name = "edition-0002_rev-2099-02-02_from-unknown_bbbbbbbb.xml";
      }),
      null,
    ),
  ),
  edition_dir_extra_file: fails("edition_dir_extra_file", () =>
    computeRecount(
      mutatedView((view) => {
        view.editionFiles.push({ name: "notes.txt", size: 3 });
      }),
      null,
    ),
  ),
  edition_dir_unreadable: fails("edition_dir_unreadable", () =>
    loadCorpusView(
      {},
      {
        readdirSync: () => {
          const error = new Error("no such directory");
          error.code = "ENOENT";
          throw error;
        },
      },
    ),
  ),
  edition_name_unparsed: fails("edition_name_unparsed", () =>
    computeRecount(
      mutatedView((view) => {
        view.editionFiles.push({ name: "edition-0003_rev-broken.xml", size: 4 });
      }),
      null,
    ),
  ),
  evidence_drift: fails("evidence_drift", () => checkRenderedBytes("rendered", "committed")),
  input_absent: fails("input_absent", () =>
    loadJsonArtifact("prd/migration/rust-evidence/m209-s04-absent-fixture.json", "absent fixture"),
  ),
  input_artifact_shape_invalid: fails("input_artifact_shape_invalid", () =>
    assertS03Shape({ familyDenominator: null, editionDelta: {} }),
  ),
  non_ascii_evidence: fails("non_ascii_evidence", () => assertAsciiOnly(renderEvidence({ probe: "\u00e9" }))),
  out_absolute: fails("out_absolute", () => resolveOutTarget("/tmp/m209-s04-outside.json")),
  out_not_evidence_path: fails("out_not_evidence_path", () =>
    resolveOutTarget("scripts/m209-s04-not-evidence.json"),
  ),
  out_of_repo_out: fails("out_of_repo_out", () => resolveOutTarget("../m209-s04-outside.json")),
  out_symlink_target: fails("out_symlink_target", () =>
    resolveOutTarget(ARTIFACT_RECOUNT, {
      existsSync: () => true,
      lstatSync: () => ({ isSymbolicLink: () => true }),
    }),
  ),
  path_not_repository_relative: fails("path_not_repository_relative", () =>
    computeRecount(
      mutatedView((view) => {
        view.editionDirRelative = "/etc/passwd";
      }),
      null,
    ),
  ),
  promotion_claim_present: fails("promotion_claim_present", () => {
    const s03 = structuredClone({ familyDenominator: s03Model().familyDenominator, editionDelta: s03Model().editionDelta });
    s03.editionDelta.disposition = "closed";
    return computePromotionChecks(s03);
  }),
  raw_text_leak: fails("raw_text_leak", () =>
    assertNoRawText('{"offline_uri":"consultantplus://offline/0"}'),
  ),
  window_listing_disagreement: fails("window_listing_disagreement", () =>
    computeWindows(computeRecount(synthView(), null).rows, [
      { from_edition: 1, to_edition: 2, revision_from: "initial", revision_to: "1999-12-31" },
    ]),
  ),
  zero_denominator: fails("zero_denominator", () =>
    computeRecount(
      mutatedView((view) => {
        view.editionFiles = [];
      }),
      null,
    ),
  ),
});

test("the documented fail-closed vocabulary is exactly the emittable set", () => {
  assert.deepEqual([...FAIL_CLOSED_CODES], DOCUMENTED_CODES);
  assert.deepEqual(Object.keys(NEGATIVE_CASES).sort(), [...DOCUMENTED_CODES].sort());
  for (const [code, run] of Object.entries(NEGATIVE_CASES)) {
    assert.equal(typeof run, "function", `${code} case missing`);
    run();
  }
});

// documented codes, one line each -- asserted equal to DOCUMENTED_CODES
// DOCUMENTED_FAIL_CLOSED_BEGIN
// artifact_empty: the rendered artifact is an empty string.
// corpus_recount_disagreement: the live recount differs from the frozen m209 chain pins or from the tracked s03 declarations on either leg.
// count_partition_mismatch: the class partition does not sum to the live edition total, the initial or ISO revision token count is not exactly one-per-class, or an edition falls into no class.
// edition_dir_extra_file: the chain directory carries a file that is not an admitted `edition-*.xml` file.
// edition_dir_unreadable: the chain directory cannot be listed or a listing entry cannot be stat-ed.
// edition_name_unparsed: an admitted `edition-*.xml` name does not parse into number, revision, from and content tokens.
// evidence_drift: `--check` renders bytes that differ from the committed artifact, or the committed artifact is missing.
// input_absent: a declared input -- the layer1 manifest or a tracked s03 artifact -- is absent from disk.
// input_artifact_shape_invalid: a declared input is not parseable, or an s03 artifact lacks a required block, integer or window field.
// non_ascii_evidence: the artifact bytes carry a non-ASCII code unit.
// out_absolute: `--out` is an absolute path.
// out_not_evidence_path: `--out` is outside the `prd/migration/rust-evidence/m209-s04-*.json` allowlist.
// out_of_repo_out: `--out` escapes the repository after canonicalizing its parent directory.
// out_symlink_target: `--out` resolves to an existing symlink.
// path_not_repository_relative: a declared corpus path is absolute, carries `..`, or falls outside the corpus root.
// promotion_claim_present: an s03 input claims authority or a non-zero promotion, leg or requirement-record counter, or is no longer disposition active.
// raw_text_leak: provider prose, a corpus field name, or a manifest title reached the rendered artifact.
// window_listing_disagreement: an s03 window revision token does not equal the live revision token of the same edition number.
// zero_denominator: the live edition listing or the live layer1 manifest declares zero records.
// DOCUMENTED_FAIL_CLOSED_END

test("the documented code block equals the module and artifact code sets", () => {
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
  assert.deepEqual(documented, DOCUMENTED_CODES);
  assert.deepEqual([...recountArtifact.fail_closed_codes], DOCUMENTED_CODES);
  assert.deepEqual([...coverageArtifact.fail_closed_codes], DOCUMENTED_CODES);
});

// ---------------------------------------------------------------------------
// synthetic fixture coherence
// ---------------------------------------------------------------------------

test("the synthetic count-only fixture is coherent", () => {
  const recount = computeRecount(synthView(), null);
  assert.equal(recount.counted.editions_files_total, 2);
  assert.equal(recount.counted.editions_parsed_total, 2);
  assert.equal(recount.counted.editions_initial_total, 1);
  assert.deepEqual(recount.classes.map((row) => row.count), [1, 1]);
  assert.deepEqual(recount.residuals.map((row) => row.count), [0, 0, 0]);
  assert.equal(recount.counted.classes_total, 2);
  assert.equal(recount.counted.windows_total, 0, "a recount without s03 inputs declares no window");
  assert.equal(recount.core_act.core_acts_total, 1);
  assert.equal(recount.core_act.core_act_title_date, "2013-04-05");
  assert.equal(recount.core_act.directory_date_token, "2013-04-05");
  assert.equal(recount.core_act.law_number_digits, "44");
  const windows = computeWindows(recount.rows, [
    { from_edition: 1, to_edition: 2, revision_from: "initial", revision_to: "2099-01-01" },
  ]);
  assert.equal(windows.windows_checked, 1);
  assert.equal(windows.mismatches_total, 0);
});

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("artifact integrity: repository-relative, ASCII-only, non-empty, one canonical line", () => {
  for (const relative of [ARTIFACT_RECOUNT, ARTIFACT_RECONCILIATION]) {
    assert.equal(path.isAbsolute(relative), false);
    assert.equal(relative.split("/").includes(".."), false);
    assert.equal(resolveOutTarget(relative).repoRelative, relative);
  }
  for (const raw of [recountRaw, coverageRaw]) {
    assertNonEmpty(raw);
    assertAsciiOnly(raw);
    assert.equal(raw.endsWith("\n"), true, "the artifact must end with a single newline");
    assert.equal(raw.trimEnd().includes("\n"), false, "the artifact must be one canonical JSON line");
  }
  assert.equal(JSON.stringify(recountArtifact), recountRaw.trimEnd());
  assert.equal(JSON.stringify(coverageArtifact), coverageRaw.trimEnd());
});

test("both artifacts carry the bounded envelope and the anti-promotion zeros", () => {
  const envelopes = [
    [recountArtifact, SCHEMA_RECOUNT, KIND_RECOUNT],
    [coverageArtifact, SCHEMA_RECONCILIATION, KIND_RECONCILIATION],
  ];
  for (const [artifact, schema, kind] of envelopes) {
    assert.equal(artifact.schema, schema);
    assert.equal(artifact.schema_version, 1);
    assert.equal(artifact.kind, kind);
    assert.equal(artifact.milestone, "M209-2yg6ix");
    assert.equal(artifact.slice, "S04");
    assert.equal(artifact.task, "T02");
    assert.equal(artifact.lifecycle, "[bounded]");
    assert.equal(artifact.authoritative, false);
    assert.equal(artifact.count_only, true);
    assert.equal(artifact.ascii_only, true);
    assert.equal(artifact.requirement_id, "R070");
    assert.deepEqual(artifact.requirement_dispositions, { R035: "active", R070: "active" });
    assert.equal(artifact.disposition_decision, "D416");
    assert.equal(artifact.gates_promoted, 0);
    assert.equal(artifact.legs_promoted, 0);
    assert.equal(artifact.proof_packages_attached, 0);
    assert.equal(artifact.requirement_records_mutated, 0);
    assert.deepEqual(artifact.fail_closed_codes, DOCUMENTED_CODES);
    assert.deepEqual(artifact.non_claims, [...artifact.non_claims]);
    assert.ok(artifact.inputs.length >= 4);
    assert.ok(artifact.cross_checks.length >= 15);
    assert.ok(artifact.promotion_checks.length > 0);
    assert.equal(artifact.windows.windows_total, FROZEN_PINS.windows_total);
  }
});

test("every declared input anchor resolves on disk and matches its live bytes", () => {
  for (const artifact of [recountArtifact, coverageArtifact]) {
    for (const pin of artifact.inputs) {
      assert.equal(path.isAbsolute(pin.relative_path), false);
      assert.match(pin.sha256, SHA_PATTERN, `${pin.input_id} pin`);
      assert.ok(Number.isInteger(pin.bytes) && pin.bytes > 0, `${pin.input_id} bytes`);
      if (pin.input_kind === "directory-listing") {
        assert.equal(pin.relative_path, editionDirRelative());
        continue;
      }
      const absolute = path.join(ROOT, pin.relative_path);
      assert.ok(existsSync(absolute), `${pin.input_id} must resolve on disk`);
      const bytes = readFileSync(absolute);
      assert.equal(pin.bytes, bytes.length, `${pin.input_id} byte count must match`);
      assert.equal(pin.sha256, sha256Pin(bytes), `${pin.input_id} pin must match live bytes`);
    }
  }
  assert.deepEqual(
    recountArtifact.inputs.map((pin) => pin.input_id),
    coverageArtifact.inputs.map((pin) => pin.input_id),
  );
});

test("every cross-check and promotion row passes and the two artifacts agree", () => {
  assert.deepEqual(recountArtifact.cross_checks, coverageArtifact.cross_checks);
  assert.deepEqual(recountArtifact.promotion_checks, coverageArtifact.promotion_checks);
  for (const row of [...recountArtifact.cross_checks, ...recountArtifact.promotion_checks]) {
    assert.equal(row.verdict, "pass", `${row.check_id} must pass`);
  }
  const sources = recountArtifact.cross_checks.map((row) => row.source).join(" ");
  assert.ok(sources.includes(S03_FAMILY_DENOMINATOR), "the family denominator leg must be checked");
  assert.ok(sources.includes(S03_EDITION_DELTA), "the edition delta leg must be checked");
  assert.ok(sources.includes("m209 chain pin"), "the frozen-pin leg must be checked");
});

// ---------------------------------------------------------------------------
// independent arithmetic
// ---------------------------------------------------------------------------

test("the declared partition, residuals and windows reconcile arithmetically", () => {
  const counted = recountArtifact.counted;
  const coverage = coverageArtifact;
  assert.equal(counted.editions_files_total, counted.editions_accepted_total + counted.editions_unaccepted_total);
  assert.equal(counted.editions_accepted_total, counted.editions_parsed_total + counted.editions_unparsed_total);
  assert.equal(counted.editions_parsed_total, counted.editions_initial_total + counted.editions_revision_dated_total);
  assert.equal(counted.manifest_records_total, counted.manifest_core_acts_total + counted.manifest_amending_acts_total);
  assert.ok(counted.manifest_amending_acts_date_matched_total <= counted.manifest_amending_acts_with_act_date_total);
  assert.ok(counted.manifest_amending_acts_with_act_date_total <= counted.manifest_amending_acts_total);
  assert.equal(counted.classes_total, counted.editions_files_total);
  assert.equal(counted.windows_total, counted.editions_revision_dated_total);
  assert.equal(counted.manifest_amending_acts_date_matched_total, 111);
  assert.equal(coverage.classes_total, coverage.editions_total);
  assert.equal(coverage.classes_total, coverage.classes.reduce((sum, row) => sum + row.count, 0));
  assert.deepEqual(coverage.classes.map((row) => row.class_id), [
    "core-act-initial-edition",
    "amending-act-date-matched",
  ]);
  assert.deepEqual(coverage.residuals.map((row) => row.residual_id), [
    "manifest-amending-act-without-distinct-edition",
    "same-revision-date-collapse",
    "edition-without-manifest-date",
  ]);
  assert.equal(coverage.residuals[2].expected_zero, true);
  assert.equal(coverage.residual_unnamed_total, coverage.residuals[2].count);
  assert.equal(coverage.residual_unnamed_total, 0);
  assert.equal(
    coverage.residual_collapse_total,
    counted.editions_revision_dated_total - counted.editions_distinct_revision_dates_total,
  );
  assert.equal(
    coverage.residual_unmatched_total,
    counted.manifest_amending_acts_with_act_date_total -
      counted.manifest_amending_acts_date_matched_total +
      (counted.manifest_amending_acts_total - counted.manifest_amending_acts_with_act_date_total),
  );
  assert.equal(
    counted.manifest_amending_acts_date_matched_total + coverage.residual_unmatched_total,
    counted.manifest_amending_acts_total,
    "every amending act is either date-matched to an edition or declared as a residual",
  );
  assert.equal(coverage.windows.windows_total, counted.windows_total);
  assert.equal(coverage.windows.windows_checked, counted.windows_total);
  assert.equal(coverage.windows.mismatches_total, 0);
  assert.match(coverage.windows.stream_sha256, SHA_PATTERN);
  assert.equal(coverage.windows.stream_sha256, recountArtifact.windows.stream_sha256);
  for (const pin of Object.keys(DOCUMENTED_PINS)) {
    assert.equal(FROZEN_PINS[pin], DOCUMENTED_PINS[pin], `${pin} module pin must match the documented pin`);
  }
  assert.equal(counted.editions_files_total, DOCUMENTED_PINS.editions_files_total);
  assert.equal(counted.editions_bytes_total, DOCUMENTED_PINS.editions_bytes_total);
  assert.equal(counted.editions_listing_sha256, DOCUMENTED_PINS.editions_listing_sha256);
  assert.equal(counted.manifest_records_total, DOCUMENTED_PINS.manifest_records_total);
  assert.equal(counted.manifest_bytes_total, DOCUMENTED_PINS.manifest_bytes_total);
  assert.equal(counted.manifest_sha256, DOCUMENTED_PINS.manifest_sha256);
  assert.equal(counted.windows_total, DOCUMENTED_PINS.windows_total);
});

// ---------------------------------------------------------------------------
// count-only surface and non-claims
// ---------------------------------------------------------------------------

test("the count-only surface carries no corpus prose, corpus key or s03 drift", () => {
  for (const raw of [recountRaw, coverageRaw]) {
    assertNoRawText(raw);
    assert.equal(raw.includes('"mode"'), false, "the artifact must be mode-independent");
    for (const token of ['"title"', '"offline_uri"', '"document_key"']) {
      assert.equal(raw.includes(token), false, `${token} must not be an artifact key`);
    }
  }
  assert.equal(
    recountRaw.includes("legislative"),
    false,
    "no legislative value may be minted from a revision date",
  );
});

test("both records carry the D289/D415, D416, D539 and D560 non-claims", () => {
  for (const artifact of [recountArtifact, coverageArtifact]) {
    assert.ok(Array.isArray(artifact.non_claims) && artifact.non_claims.length > 0);
    const joined = artifact.non_claims.join(" ").toLowerCase();
    // The non-claims are written as hyphenated kebab tokens, so a fragment is
    // accepted either verbatim or with hyphens and underscores read as spaces.
    const spaced = joined.replace(/[-_]/g, " ");
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      const needle = fragment.toLowerCase();
      const spacedNeedle = needle.replace(/[-_]/g, " ");
      assert.ok(
        joined.includes(needle) || spaced.includes(spacedNeedle),
        `the non-claims must carry ${fragment}`,
      );
    }
  }
});

test("the module stays offline and dependency-free", () => {
  const source = readRepo(MODULE_PATH);
  const imports = [...source.matchAll(/^import .*? from "([^"]+)";/gms)].map((match) => match[1]);
  assert.ok(imports.length > 0, "the module must import something");
  for (const specifier of imports) {
    assert.ok(specifier.startsWith("node:"), `${specifier} must be a node: builtin`);
  }
  for (const forbidden of ["node:child_process", "node:http", "node:https", "node:net", "node:dgram"]) {
    assert.equal(imports.includes(forbidden), false, `${forbidden} must not be imported`);
  }
  assert.equal(source.includes("fetch("), false, "the module must not use fetch");
});

// ---------------------------------------------------------------------------
// corpus-gated live re-derivation
// ---------------------------------------------------------------------------

function corpusDir() {
  return path.join(ROOT, editionDirRelative());
}

function corpusAvailable() {
  return existsSync(corpusDir());
}

/// The test's own listing digest: names plus sizes, ascending, `\0`-separated,
/// `\n`-terminated -- transcribed from the documented rule, not imported.
function independentListing() {
  const dir = corpusDir();
  const names = readdirSync(dir)
    .filter((name) => statSync(path.join(dir, name)).isFile())
    .sort();
  const files = names.map((name) => ({ name, size: statSync(path.join(dir, name)).size }));
  let stream = "";
  for (const file of files) stream += `${file.name}\u0000${file.size}\n`;
  return {
    files,
    bytes: files.reduce((sum, file) => sum + file.size, 0),
    sha256: sha256Pin(Buffer.from(stream, "utf8")),
  };
}

function independentManifest() {
  const raw = readFileSync(path.join(ROOT, manifestRelative()));
  const lines = raw.toString("utf8").split("\n").filter((line) => line.trim() !== "");
  const actDates = [];
  const titles = [];
  let core = 0;
  let amending = 0;
  let amendingWithoutDate = 0;
  for (const line of lines) {
    const record = JSON.parse(line);
    const title = typeof record.title === "string" ? record.title : "";
    titles.push(title);
    const match = INDEPENDENT_DATE_RE.exec(title);
    const date = match === null ? null : `${match[3]}-${match[2]}-${match[1]}`;
    if (record.is_core_act === true) core += 1;
    else {
      amending += 1;
      if (date === null) amendingWithoutDate += 1;
      else actDates.push(date);
    }
  }
  return {
    recordsTotal: lines.length,
    bytes: raw.length,
    sha256: sha256Pin(raw),
    core,
    amending,
    amendingWithoutDate,
    amendingDates: actDates,
    titles,
  };
}

function independentReconciliation() {
  const listing = independentListing();
  const rows = [];
  for (const file of listing.files) {
    const match = INDEPENDENT_NAME_RE.exec(file.name);
    if (match !== null) rows.push({ edition_number: Number(match[1]), revision_token: match[2] });
  }
  rows.sort((left, right) => left.edition_number - right.edition_number);
  const revisionDates = new Set(
    rows.map((row) => row.revision_token).filter((token) => ISO_DATE.test(token)),
  );
  const manifest = independentManifest();
  const distinctActDates = new Set(manifest.amendingDates);
  const initial = rows.filter((row) => row.revision_token === "initial").length;
  const matched = rows.filter(
    (row) => row.revision_token !== "initial" && distinctActDates.has(row.revision_token),
  ).length;
  const amendingMatched = manifest.amendingDates.filter((date) => revisionDates.has(date)).length;
  return {
    listing,
    manifest,
    rows,
    revisionDates,
    initial,
    matched,
    unnamed: rows.length - initial - matched,
    withoutDistinctEdition:
      manifest.amendingDates.length - amendingMatched + manifest.amendingWithoutDate,
    collapse: rows.length - initial - revisionDates.size,
  };
}

test("the live corpus re-derives the declared envelope, partition and residuals", () => {
  if (!corpusAvailable()) {
    console.log("M209_S04_CORPUS_ABSENT");
    return;
  }
  const view = loadCorpusView();
  const s03 = loadS03Inputs();
  const recount = recountBundle(view, s03);
  const coverage = coverageBundle(view, s03);
  assert.equal(renderEvidence(recount), recountRaw, "--check must reproduce the recount artifact");
  assert.equal(renderEvidence(coverage), coverageRaw, "--check must reproduce the reconciliation artifact");

  const independent = independentReconciliation();
  const counted = recount.counted;
  assert.equal(independent.listing.files.length, counted.editions_files_total);
  assert.equal(independent.listing.bytes, counted.editions_bytes_total);
  assert.equal(independent.listing.sha256, counted.editions_listing_sha256);
  assert.equal(independent.manifest.recordsTotal, counted.manifest_records_total);
  assert.equal(independent.manifest.bytes, counted.manifest_bytes_total);
  assert.equal(independent.manifest.sha256, counted.manifest_sha256);
  assert.equal(independent.manifest.core, counted.manifest_core_acts_total);
  assert.equal(independent.manifest.amending, counted.manifest_amending_acts_total);
  assert.equal(independent.initial, coverage.classes[0].count);
  assert.equal(independent.matched, coverage.classes[1].count);
  assert.equal(independent.unnamed, coverage.residual_unnamed_total);
  assert.equal(independent.withoutDistinctEdition, coverage.residual_unmatched_total);
  assert.equal(independent.collapse, coverage.residual_collapse_total);
  assert.equal(independent.revisionDates.size, coverage.distinct_revision_dates_total);

  const byNumber = new Map(independent.rows.map((row) => [row.edition_number, row.revision_token]));
  let stream = "";
  for (const window of s03.editionDelta.windows) {
    assert.equal(byNumber.get(window.from_edition), window.revision_from, `window ${window.from_edition} from`);
    assert.equal(byNumber.get(window.to_edition), window.revision_to, `window ${window.to_edition} to`);
    stream += `${window.from_edition}|${window.revision_from}|${window.to_edition}|${window.revision_to}\n`;
  }
  assert.equal(coverage.windows.windows_checked, s03.editionDelta.windows.length);
  assert.equal(sha256Pin(Buffer.from(stream, "utf8")), coverage.windows.stream_sha256);

  for (const title of independent.manifest.titles) {
    const trimmed = title.trim();
    if (trimmed.length < 8) continue;
    assert.equal(recountRaw.includes(trimmed), false, "no manifest title may reach the recount artifact");
    assert.equal(coverageRaw.includes(trimmed), false, "no manifest title may reach the reconciliation artifact");
  }
  assertNoCorpusText(recountRaw, view);
  assertNoCorpusText(coverageRaw, view);

  console.log(
    `[corpus-recount] editions=${counted.editions_files_total} matched=${coverage.classes[1].count} ` +
      `initial=${coverage.classes[0].count} windows=${coverage.windows.windows_checked} ` +
      `residual_unmatched=${coverage.residual_unmatched_total} collapse=${coverage.residual_collapse_total} ` +
      `unnamed=${coverage.residual_unnamed_total}`,
  );
});

test("the CLI reproduces the committed artifacts under --check", () => {
  if (!corpusAvailable()) {
    console.log("M209_S04_CORPUS_ABSENT");
    return;
  }
  const runs = [
    ["--mode", "all", "--check"],
    ["--mode", "all", "--out", ARTIFACT_RECOUNT, "--check"],
    ["--mode", "recount", "--check"],
    ["--mode", "editions", "--check"],
  ];
  for (const args of runs) {
    const stdout = execFileSync(process.execPath, [MODULE_PATH, ...args], {
      cwd: ROOT,
      encoding: "utf8",
    });
    assert.match(stdout, /^M209_S04_CORPUS_OK /, stdout);
    assert.ok(stdout.includes(EXPECTED_HEARTBEAT), `heartbeat missing from: ${stdout}`);
    assert.ok(stdout.includes("failed=0"), stdout);
  }
});

test("live corpus mutations fire the declared codes", () => {
  if (!corpusAvailable()) {
    console.log("M209_S04_CORPUS_ABSENT");
    return;
  }
  const view = loadCorpusView();
  const s03 = loadS03Inputs();
  const clone = () => structuredClone(view);

  // a missing file: the live count drops below the frozen pin
  const missing = clone();
  missing.editionFiles = missing.editionFiles.filter((file) => !file.name.startsWith("edition-0057_"));
  assert.equal(missing.editionFiles.length, view.editionFiles.length - 1);
  fails("corpus_recount_disagreement", () => recountBundle(missing, s03))();

  // an extra edition file that re-uses a live revision date: the partition still
  // holds and the frozen-pin leg is what fires
  const extra = clone();
  extra.editionFiles.push({
    name: "edition-0119_rev-2025-12-28_from-2026-01-01_ffffffff.xml",
    size: 1,
  });
  fails("corpus_recount_disagreement", () => recountBundle(extra, s03))();

  // an extra edition file carrying a date no manifest act has: the partition
  // breaks first and fails closed before any pin comparison
  const extraUnmatched = clone();
  extraUnmatched.editionFiles.push({
    name: "edition-0119_rev-2099-01-01_from-unknown_ffffffff.xml",
    size: 1,
  });
  fails("count_partition_mismatch", () => recountBundle(extraUnmatched, s03))();

  // a substituted revision date: the edition falls into no class
  const swapped = clone();
  swapped.editionFiles = swapped.editionFiles.map((file, index) =>
    index === 5 ? { ...file, name: file.name.replace(/_rev-[^_]+_/, "_rev-2099-02-02_") } : file,
  );
  fails("count_partition_mismatch", () => recountBundle(swapped, s03))();

  // a substituted s03 listing digest: the two legs stop agreeing
  const badDigest = structuredClone(s03);
  badDigest.editionDelta.denominator.edition_dir_listing_sha256 = `sha256:${"00".repeat(32)}`;
  fails("corpus_recount_disagreement", () => recountBundle(view, badDigest))();

  // a substituted window: the declared revision no longer matches the listing
  const badWindows = structuredClone(s03);
  badWindows.editionDelta.windows[0].revision_to = "1999-12-31";
  fails("window_listing_disagreement", () =>
    computeWindows(computeRecount(view, badWindows).rows, badWindows.editionDelta.windows),
  )();

  // a non-ASCII byte appended to the rendered evidence
  fails("non_ascii_evidence", () => assertAsciiOnly(`${recountRaw.trimEnd()}\u00e9`))();

  // a raw corpus marker injected into the rendered evidence
  fails("raw_text_leak", () => assertNoRawText(`${coverageRaw.trimEnd()}\u0020consultantplus://`))();
});
