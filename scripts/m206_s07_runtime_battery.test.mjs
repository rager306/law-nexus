// M206/S07 composed runtime battery.
//
// This is a composition/manifest verifier, not a second auto-accept oracle:
// it re-runs the already-named suites, checks that each really executed and
// produced nonzero counts, maps every S01-S04 scenario id to a real runtime
// test, and binds the result to the source content it observed.
//
// Modes
//   default            read-only verification: recompute, compare against the
//                      tracked manifest, reject stale/absent/missing tests.
//   M206_WRITE_BATTERY=1 write the tracked manifest from the observed run.
//
// The manifest deliberately excludes itself from `source_hashes`, and it
// carries no invented aggregate `testedSourceRevision`: it records per-file
// content hashes plus the commands and counts it actually observed.
//
// Determinism: write mode runs inside the host source-integrity window, so the
// tracked manifest must be byte-reproducible for an unchanged tree. Volatile
// wall-clock timings are therefore never persisted - they are printed to stdout
// (durable in the exec log) - and an identical manifest is not rewritten at
// all, so a verification pass touches no tracked byte.

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));
const MANIFEST_PATH = "prd/migration/rust-evidence/m206-s07-runtime-battery.json";
const writeMode = process.env.M206_WRITE_BATTERY === "1";
const governorReportPath = process.env.M206_GOVERNOR_REPORT ?? "";

const GREEN_ORACLE = {
  command: "env",
  args: [
    "M206_EXPECT=green",
    "node",
    "--test",
    "--test-reporter=tap",
    "scripts/m206_s06_reproduction.test.mjs",
  ],
  label: "M206_EXPECT=green node --test scripts/m206_s06_reproduction.test.mjs",
  minPassed: 12,
};

const SUITES = [
  {
    package: "ln-decode",
    test: "m206_grammar_context_regressions",
    minPassed: 19,
    changeClass: "S06 red reproduction oracle for RC28-F06..F10",
  },
  {
    package: "ln-temporal",
    test: "m206_scope_regressions",
    minPassed: 18,
    changeClass: "S06 red reproduction oracle for RC28-F11..F12",
  },
  {
    package: "ln-temporal",
    test: "reference_binding_endpoints",
    minPassed: 10,
    changeClass: "RC28-F10 endpoint and membership boundary",
  },
  {
    package: "ln-testkit",
    test: "decode_port_contracts",
    minPassed: 8,
    changeClass: "RC28-F12 composed reference vertical and provider isolation",
  },
];

// Full S01-S04 scenario map. `path` is the negative/protective character of
// the case: every row runs one exact Rust test and records its real outcome.
const SCENARIOS = [
  // S02 (RC28-F09, RC28-F10)
  ["S02", "F09-independent-sentences", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_independent_sentences_are_not_merged", "positive"],
  ["S02", "F09-incomplete-tail", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_incomplete_tail_stays_observable", "negative"],
  ["S02", "F09-boundaries", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_sentence_and_heading_boundaries_stay_distinct", "negative"],
  ["S02", "F09-refused-token-only", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_refused_token_only_evidence_never_completes_a_member", "negative"],
  ["S02", "F09-identical-origins", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_identical_origins_keep_slot_fingerprint", "positive"],
  ["S02", "F09-overlap", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_overlap_is_a_conflict_set_not_order_resolution", "negative"],
  ["S02", "F09-order", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f09_producer_order_is_not_precedence", "negative"],
  ["S02", "F10-original-spans", "ln-decode", "m206_grammar_context_regressions", "m206_s02_f10_original_spans_and_unavailable_morphology_stay_explicit", "positive"],
  // S03 (RC28-F07, RC28-F08, RC28-F12)
  ["S03", "F08-self-positive", "ln-decode", "m206_grammar_context_regressions", "rc28_f08_self_positive_authorizes_through_typed_request_evidence", "positive"],
  ["S03", "F08-cited-act-negative", "ln-decode", "m206_grammar_context_regressions", "rc28_f08_cited_act_negative_and_missing_sidecar_stay_refused", "negative"],
  ["S03", "F08-self-missing-conflict", "ln-decode", "m206_grammar_context_regressions", "rc28_f08_self_missing_or_conflicting_sidecar_fails_closed", "negative"],
  ["S03", "F12-antecedent-positive", "ln-temporal", "m206_scope_regressions", "rc28_f12_antecedent_positive_and_unproven_cited_act_stay_separate", "positive"],
  ["S03", "F12-antecedent-unproven", "ln-temporal", "m206_scope_regressions", "rc28_f12_antecedent_positive_and_unproven_cited_act_stay_separate", "negative"],
  ["S03", "F12-alias-declare-use", "ln-temporal", "m206_scope_regressions", "rc28_f12_alias_declare_use_shadow_conflict_and_boundary", "positive"],
  ["S03", "F12-alias-shadow-conflict", "ln-temporal", "m206_scope_regressions", "rc28_f12_alias_declare_use_shadow_conflict_and_boundary", "negative"],
  ["S03", "F12-alias-boundary", "ln-temporal", "m206_scope_regressions", "rc28_f12_alias_declare_use_shadow_conflict_and_boundary", "negative"],
  ["S03", "F07-series-positive", "ln-decode", "m206_grammar_context_regressions", "rc28_f07_series_positive_proven_head_open_tail_and_document_order", "positive"],
  ["S03", "F07-three-unrelated", "ln-decode", "m206_grammar_context_regressions", "rc28_f07_three_unrelated_blocks_have_no_parent_edges", "negative"],
  ["S03", "F07-series-invalid", "ln-decode", "m206_grammar_context_regressions", "rc28_f07_series_invalid_order_boundary_and_unproven_head_mint_nothing", "negative"],
  ["S03", "F12-edition-relation", "ln-temporal", "m206_scope_regressions", "rc28_f12_edition_relation_is_a_source_backed_candidate_not_identity", "positive"],
  // S04 (RC28-F10 range rows, RC28-F11 cue rows, RC28-F12 vertical rows)
  ["S04", "F10-CUE-TOKEN", "ln-temporal", "m206_scope_regressions", "rc28_f11_s04_f10_cue_token_scoped_negation_stays_separate", "negative"],
  ["S04", "F10-CUE-POSITIVE", "ln-temporal", "m206_scope_regressions", "rc28_f11_s04_f10_cue_positive_stays_a_candidate", "positive"],
  ["S04", "F10-ACTOR-ANCHORED", "ln-temporal", "m206_scope_regressions", "rc28_f11_s04_f10_actor_anchored_span_is_exact", "positive"],
  ["S04", "F10-ACTOR-NEGATIVE", "ln-temporal", "m206_scope_regressions", "rc28_f11_s04_f10_actor_negative_is_typed_absence", "negative"],
  ["S04", "F11-ENDPOINTS", "ln-temporal", "reference_binding_endpoints", "rc28_f10_s04_f11_endpoints_pair_keeps_only_the_two_written_endpoints", "positive"],
  ["S04", "F11-MEMBERSHIP", "ln-temporal", "reference_binding_endpoints", "rc28_f10_s04_f11_membership_requires_a_selected_edition_index", "negative"],
  ["S04", "F11-MISSING-MEMBER", "ln-temporal", "reference_binding_endpoints", "rc28_f10_s04_f11_missing_member_is_typed_incomplete_with_endpoints_preserved", "negative"],
  ["S04", "F11-RANGE-INVALID", "ln-temporal", "reference_binding_endpoints", "rc28_f10_s04_f11_invalid_or_reversed_range_is_refused_without_arithmetic", "negative"],
  ["S04", "F12-VERTICAL-POSITIVE", "ln-testkit", "decode_port_contracts", "rc28_f12_s04_f12_vertical_positive_composes_for_consultant", "positive"],
  ["S04", "F12-VERTICAL-NEGATIVE", "ln-testkit", "decode_port_contracts", "rc28_f12_s04_f12_vertical_negative_missing_context_stays_typed_unknown", "negative"],
  ["S04", "F12-CONTEXT-SEPARATION", "ln-temporal", "m206_scope_regressions", "rc28_f12_construction_separation_keeps_authorizations_apart", "positive"],
  ["S04", "F12-NO-IR", "ln-temporal", "m206_scope_regressions", "rc28_f12_edition_relation_is_a_source_backed_candidate_not_identity", "negative"],
].map(([slice, id, packageName, suite, name, path]) => ({
  slice,
  id,
  package: packageName,
  suite,
  test: name,
  path,
}));

// S01 is design-only with no runtime scenario table; the battery records the
// historical no-start provenance verbatim instead of inventing a test map.
const S01_PROVENANCE = {
  slice: "S01",
  status: "design-only",
  batteryStatus: "NOT_RUN",
  ownerDecision: "Reject",
  interaction: "04fd05a2-338f-45af-a1cc-13501717dc53",
  source: "prd/architecture/m206-s01-adoption-state.md",
  scenarioIds: [],
  outcome: "not-executed",
  evidenceNote:
    "S01 recorded a source-bound owner Reject for the F06/F10 adoption and left its composition battery NOT_RUN; the marker is preserved, never flipped.",
};

const HISTORICAL_GUARDS = [
  {
    label: "bash scripts/m206_s02_t02_verify.sh",
    command: "bash",
    args: ["scripts/m206_s02_t02_verify.sh"],
    expectStdout: "M206_S02_T02_VERIFY_OK",
    minPassed: null,
  },
  {
    label: "node --test scripts/m206_s03_adoption_contract.test.mjs",
    command: "node",
    args: ["--test", "--test-reporter=tap", "scripts/m206_s03_adoption_contract.test.mjs"],
    expectStdout: "",
    minPassed: 1,
  },
  {
    label: "node --test scripts/m206_s04_adoption_contract.test.mjs",
    command: "node",
    args: ["--test", "--test-reporter=tap", "scripts/m206_s04_adoption_contract.test.mjs"],
    expectStdout: "",
    minPassed: 1,
  },
];

const HASHED_SOURCES = [
  "crates/ln-decode/src/capture_bounds.rs",
  "crates/ln-decode/src/document_context.rs",
  "crates/ln-decode/src/lawref.rs",
  "crates/ln-decode/src/local_grammar.rs",
  "crates/ln-decode/src/sentence.rs",
  "crates/ln-temporal/src/document_context.rs",
  "crates/ln-temporal/src/identity_binding.rs",
  "crates/ln-temporal/src/semantic_scope.rs",
  "crates/ln-decode/tests/m206_grammar_context_regressions.rs",
  "crates/ln-temporal/tests/m206_scope_regressions.rs",
  "crates/ln-temporal/tests/reference_binding_endpoints.rs",
  "crates/ln-testkit/tests/decode_port_contracts.rs",
  "scripts/m206_s06_reproduction.test.mjs",
  "scripts/m206_s07_admission_contract.test.mjs",
  "scripts/m206_s07_runtime_battery.test.mjs",
  "prd/architecture/m206-s07-runtime-admission.md",
  "doc/review/review-28-10-09-2026.md",
];

/// Node's colour reporters interleave ANSI escapes between a label and its
/// number, so every captured stream is stripped before it is parsed.
// eslint-disable-next-line no-control-regex
const ANSI = /\u001b\[[0-9;]*m/g;

function stripAnsi(text) {
  return text.replace(ANSI, "");
}

/// A child process of a `node --test` run inherits `NODE_TEST_CONTEXT`, which
/// makes a nested `node --test` silently skip every file and exit 0 with empty
/// output - a textbook 0-test green. Remove it so the nested runner really runs,
/// and assert observed counts afterwards instead of trusting the exit status.
function childEnv(extra = {}) {
  const env = { ...process.env, ...extra };
  delete env.NODE_TEST_CONTEXT;
  return env;
}

function run(command, args, options = {}) {
  const started = Date.now();
  const result = spawnSync(command, args, {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
    env: options.env ?? childEnv(),
  });
  const durationMs = Date.now() - started;
  const stdout = stripAnsi(result.stdout ?? "");
  const stderr = stripAnsi(result.stderr ?? "");
  assert.equal(
    result.error,
    undefined,
    `${command} ${args.join(" ")} could not execute: ${result.error?.message}\n${stderr}`,
  );
  assert.equal(
    result.signal,
    null,
    `${command} ${args.join(" ")} was terminated by a signal\n${stderr}`,
  );
  assert.equal(
    typeof result.status,
    "number",
    `${command} ${args.join(" ")} has no concrete exit status\n${stderr}`,
  );
  return { status: result.status, stdout, stderr, durationMs };
}

function bounded(text, limit = 400) {
  const trimmed = text.trim();
  return trimmed.length <= limit ? trimmed : `...${trimmed.slice(-limit)}`;
}

function sha256(relativePath) {
  const bytes = readFileSync(`${root}/${relativePath}`);
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

function suiteRun(suite) {
  const result = run("cargo", [
    "test",
    "-p",
    suite.package,
    "--offline",
    "--test",
    suite.test,
  ]);
  const counts = result.stdout.match(
    /test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out/,
  );
  assert.ok(
    counts,
    `${suite.package}/${suite.test} produced no parseable test result\n${bounded(result.stdout, 800)}`,
  );
  const passed = Number(counts[2]);
  const failed = Number(counts[3]);
  assert.equal(
    result.status,
    0,
    `${suite.package}/${suite.test} exited ${result.status}\n${bounded(result.stdout, 800)}`,
  );
  assert.equal(failed, 0, `${suite.package}/${suite.test} reported ${failed} failures`);
  assert.ok(
    passed >= suite.minPassed,
    `${suite.package}/${suite.test} ran ${passed} tests, expected at least ${suite.minPassed}`,
  );
  return {
    label: `cargo test -p ${suite.package} --offline --test ${suite.test}`,
    status: result.status,
    passed,
    failed,
    ignored: Number(counts[4]),
    filteredOut: Number(counts[6]),
    durationMs: result.durationMs,
    changeClass: suite.changeClass,
  };
}

/// Wall-clock timings live in the in-memory observation only. They are printed
/// to stdout and stripped before persistence, because the tracked manifest is
/// rewritten while the host is hashing the tree.
function timingLine(observed) {
  const rows = [
    ...observed.commands.map((row) => `${row.label}=${row.durationMs}ms`),
    ...observed.historicalGuards.map((row) => `${row.label}=${row.durationMs}ms`),
  ];
  const scenariosMs = observed.scenarioMap.reduce((sum, row) => sum + row.durationMs, 0);
  return `[m206-s07-battery] timings: scenarios(${observed.scenarioMap.length})=${scenariosMs}ms; ${rows.join(
    "; ",
  )}`;
}

function persistedView(observed) {
  const stripTiming = (row) => {
    const { durationMs: _unpersisted, ...rest } = row;
    return rest;
  };
  return {
    ...observed,
    commands: observed.commands.map(stripTiming),
    scenarioMap: observed.scenarioMap.map(stripTiming),
    historicalGuards: observed.historicalGuards.map(stripTiming),
  };
}

function scenarioRun(scenario) {
  const result = run("cargo", [
    "test",
    "-p",
    scenario.package,
    "--offline",
    "--test",
    scenario.suite,
    scenario.test,
    "--",
    "--exact",
    "--nocapture",
  ]);
  const executed = result.stdout.match(/running (\d+) test(?:s)?/);
  assert.ok(
    executed,
    `${scenario.id} did not report a Rust test count\n${bounded(result.stdout, 800)}`,
  );
  assert.equal(
    executed[1],
    "1",
    `${scenario.id} executed ${executed[1]} tests; an --exact no-test exit is not evidence`,
  );
  const escaped = scenario.test.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const observed = [
    ...result.stdout.matchAll(new RegExp(`^test ${escaped} \\.* (ok|FAILED)$`, "gm")),
  ];
  assert.equal(
    observed.length,
    1,
    `${scenario.id} did not provide exactly one result for ${scenario.test}`,
  );
  assert.equal(result.status, 0, `${scenario.id} exited ${result.status}`);
  assert.equal(observed[0][1], "ok", `${scenario.id} did not pass ${scenario.test}`);
  return {
    slice: scenario.slice,
    id: scenario.id,
    path: scenario.path,
    package: scenario.package,
    suite: scenario.suite,
    test: scenario.test,
    outcome: "passed",
    status: result.status,
    durationMs: result.durationMs,
  };
}

function governorBlock() {
  // Checks that are inherited, tracked roadmap/projection bookkeeping rather
  // than S07 product evidence. Anything failing outside this allowlist is a
  // NEW defect and fails the battery (the plan's "новый дефект blocker" rule).
  const INHERITED_FAILING_CHECKS = new Set([
    "roadmap-current-tracks-gsd",
    "roadmap-range-coverage",
    "gsd-planned-inventory-visibility",
    "review-case-integrity.open-findings",
    "journal-retry-loops",
    "compat-marker-hygiene",
  ]);
  if (!governorReportPath || !existsSync(governorReportPath)) {
    return {
      status: "not-run-in-battery",
      note: "Governor is recorded separately by the closeout unit; pass M206_GOVERNOR_REPORT to bind it here.",
      pass_count: null,
      warn_count: null,
      error_count: null,
      inherited: ["empty_entities projection compatibility drift (DECISIONS.md first offender)"],
      newDefects: [],
    };
  }
  const text = readFileSync(governorReportPath, "utf8");
  const start = text.indexOf("{");
  const report = start > 0 ? JSON.parse(text.slice(start)) : JSON.parse(text);
  const findings = Array.isArray(report.findings) ? report.findings : [];
  const failing = findings.filter((finding) => finding.status === "fail");
  const inheritedGroups = new Map();
  for (const finding of failing) {
    if (!INHERITED_FAILING_CHECKS.has(finding.check_id)) {
      continue;
    }
    const entry = inheritedGroups.get(finding.check_id) ?? {
      checkId: finding.check_id,
      severity: finding.severity,
      count: 0,
      observed: finding.observed,
      note: "inherited tracked-projection bookkeeping, outside the S07 product contour",
    };
    entry.count += 1;
    inheritedGroups.set(finding.check_id, entry);
  }
  const inherited = [...inheritedGroups.values()];
  const newDefects = failing
    .filter((finding) => !INHERITED_FAILING_CHECKS.has(finding.check_id))
    .map((finding) => ({ checkId: finding.check_id, observed: finding.observed }));
  return {
    status: report.status,
    schema: report.schema_version ?? "law-nexus-governor-report/v1",
    pass_count: report.pass_count ?? null,
    warn_count: report.warn_count ?? null,
    error_count: report.error_count ?? null,
    total_findings: findings.length,
    inherited,
    newDefects,
    note: "read from the governor report supplied via M206_GOVERNOR_REPORT; the governor is not re-run by the battery",
  };
}

function observe() {
  const commands = [];
  const green = run(GREEN_ORACLE.command, GREEN_ORACLE.args);
  const greenCounts = green.stdout.match(/(?:^#\s*pass|pass)\s+(\d+)\s*$/m);
  const greenFail = green.stdout.match(/(?:^#\s*fail|fail)\s+(\d+)\s*$/m);
  assert.equal(green.status, 0, `green reproduction oracle exited ${green.status}`);
  assert.ok(greenCounts, "green reproduction oracle produced no pass count");
  assert.ok(
    Number(greenCounts[1]) >= GREEN_ORACLE.minPassed,
    `green reproduction oracle passed only ${greenCounts[1]} tests`,
  );
  assert.equal(Number(greenFail?.[1] ?? "0"), 0, "green reproduction oracle reported failures");
  commands.push({
    label: GREEN_ORACLE.label,
    status: green.status,
    passed: Number(greenCounts[1]),
    failed: Number(greenFail?.[1] ?? "0"),
    durationMs: green.durationMs,
    changeClass: "Composed RC28-F06..F12 closeout oracle",
  });

  for (const suite of SUITES) {
    commands.push(suiteRun(suite));
  }

  const scenarios = SCENARIOS.map(scenarioRun);
  const ids = new Set(scenarios.map((scenario) => scenario.id));
  assert.equal(ids.size, SCENARIOS.length, "scenario ids must be unique");
  for (const slice of ["S02", "S03", "S04"]) {
    const expectedCount = { S02: 8, S03: 12, S04: 12 }[slice];
    assert.equal(
      scenarios.filter((scenario) => scenario.slice === slice).length,
      expectedCount,
      `${slice} scenario map must stay complete`,
    );
  }

  const historical = HISTORICAL_GUARDS.map((guard) => {
    const result = run(guard.command, guard.args);
    assert.equal(result.status, 0, `${guard.label} exited ${result.status}`);
    if (guard.expectStdout) {
      assert.ok(
        result.stdout.includes(guard.expectStdout),
        `${guard.label} did not print ${guard.expectStdout}`,
      );
    }
    let passed = null;
    if (guard.minPassed !== null) {
      const counts = result.stdout.match(/(?:^#\s*pass|pass)\s+(\d+)\s*$/m);
      const failures = result.stdout.match(/(?:^#\s*fail|fail)\s+(\d+)\s*$/m);
      assert.ok(counts, `${guard.label} produced no test count; a skipped run is not evidence`);
      passed = Number(counts[1]);
      assert.ok(
        passed >= guard.minPassed,
        `${guard.label} ran ${passed} tests, expected at least ${guard.minPassed}`,
      );
      assert.equal(Number(failures?.[1] ?? "0"), 0, `${guard.label} reported failures`);
    }
    return {
      label: guard.label,
      status: result.status,
      outcome: "passed",
      passed,
      note: "historical S01-S04 provenance still describes the design-only stop honestly",
      durationMs: result.durationMs,
    };
  });

  const sourceHashes = {};
  for (const path of HASHED_SOURCES) {
    assert.ok(existsSync(`${root}/${path}`), `hashed source ${path} is missing`);
    sourceHashes[path] = sha256(path);
  }

  return {
    schema: "m206-s07-runtime-battery/v1",
    milestone: "M206-jnbhlz",
    slice: "S07",
    admission: "prd/architecture/m206-s07-runtime-admission.md",
    admissionCheck: "scripts/m206_s07_admission_contract.test.mjs",
    greenOracle: GREEN_ORACLE.label,
    commands,
    scenarioMap: scenarios,
    s01Provenance: S01_PROVENANCE,
    historicalGuards: historical,
    sourceHashes,
    governor: governorBlock(),
    counts: {
      suites: commands.length,
      scenarios: scenarios.length,
      scenarioPassed: scenarios.filter((s) => s.outcome === "passed").length,
      negativePaths: scenarios.filter((s) => s.path === "negative").length,
    },
    diagnostics:
      "Bounded execution evidence only: every row above ran one named command; no raw legal text is stored. Wall-clock timings are not persisted (they are printed to stdout), so the manifest stays byte-reproducible for an unchanged tree.",
  };
}

let observedCache = null;
function observedOnce() {
  if (observedCache === null) {
    observedCache = observe();
  }
  return observedCache;
}

function compareManifest(observed) {
  if (!existsSync(`${root}/${MANIFEST_PATH}`)) {
    assert.fail(
      `${MANIFEST_PATH} is absent; run with M206_WRITE_BATTERY=1 to record it before this read-only verification`,
    );
  }
  const recorded = JSON.parse(readFileSync(`${root}/${MANIFEST_PATH}`, "utf8"));
  assert.equal(recorded.schema, observed.schema, "manifest schema mismatch");
  for (const [path, digest] of Object.entries(observed.sourceHashes)) {
    assert.equal(
      recorded.sourceHashes?.[path],
      digest,
      `manifest is stale for ${path}: the recorded content hash no longer matches the tree`,
    );
  }
  const recordedIds = (recorded.scenarioMap ?? []).map((row) => row.id).sort();
  const observedIds = observed.scenarioMap.map((row) => row.id).sort();
  assert.deepEqual(recordedIds, observedIds, "manifest scenario map drifted from the tree");
  const recordedTests = new Map(
    (recorded.scenarioMap ?? []).map((row) => [row.id, row.test]),
  );
  for (const row of observed.scenarioMap) {
    assert.equal(
      recordedTests.get(row.id),
      row.test,
      `manifest maps ${row.id} to a different test than the tree provides`,
    );
  }
  assert.deepEqual(
    recorded.counts,
    observed.counts,
    "manifest counts drifted from the observed run",
  );
  return recorded;
}

test("M206/S07 composed runtime battery runs every named suite and scenario", () => {
  const observed = observedOnce();
  console.log(timingLine(observed));
  if (writeMode) {
    const target = `${root}/${MANIFEST_PATH}`;
    const serialized = `${JSON.stringify(persistedView(observed), null, 2)}\n`;
    const current = existsSync(target) ? readFileSync(target, "utf8") : null;
    if (current !== serialized) {
      writeFileSync(target, serialized, "utf8");
      console.log(`[m206-s07-battery] manifest written: ${MANIFEST_PATH}`);
    } else {
      console.log(
        `[m206-s07-battery] manifest already current, left untouched: ${MANIFEST_PATH}`,
      );
    }
    assert.equal(
      readFileSync(target, "utf8"),
      serialized,
      "write mode must leave the reproducible manifest on disk",
    );
  } else {
    compareManifest(observed);
  }
  assert.ok(observed.counts.scenarioPassed === observed.counts.scenarios);
});

test("M206/S07 battery rejects an absent or stale manifest in read-only mode", () => {
  const observed = observedOnce();
  if (writeMode) {
    return;
  }
  const recorded = compareManifest(observed);
  assert.ok(
    Array.isArray(recorded.commands) && recorded.commands.length >= 5,
    "manifest must record every command it ran",
  );
  assert.ok(
    recorded.historicalGuards?.length === HISTORICAL_GUARDS.length,
    "manifest must record the historical provenance guards",
  );
  assert.ok(
    recorded.s01Provenance?.batteryStatus === "NOT_RUN",
    "S01 historical no-start provenance must be preserved, never flipped",
  );
  assert.ok(
    Array.isArray(recorded.governor?.newDefects) && recorded.governor.newDefects.length === 0,
    `governor reported new defects outside the inherited allowlist: ${JSON.stringify(
      recorded.governor?.newDefects,
    )}`,
  );
});
