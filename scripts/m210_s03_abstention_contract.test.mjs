// M210/S03 fail-closed abstention contract (T03).
//
// Offline and fail-closed. The subject is the *diagnostic* the milestone success
// criterion demands: over every source-bound input S01 committed (eight dispute
// cards, eight corpus probes, two negative examples) the runtime is shown to
// abstain *while the bounded candidate layer is adopted*. No candidate record
// exists, no Conflict was observed, every outcome is Unknown for one stated
// reason (`candidate_layer_not_executed`), and a missing or drifted input is a
// visible fail-closed error rather than a quiet Unknown.
//
// The whole point is the separation: the absent candidate is absent because the
// adopted layer is not executed, NOT because adoption is absent. Reading
// non-execution as non-adoption is refused by name (`execution_read_as_adoption`);
// reading adoption as execution is refused by name (`adoption_read_as_execution`).
//
// Nothing here is executed semantics. The report is canonical compact ASCII JSON
// with a fixed key order and no timestamp, so `JSON.stringify(JSON.parse(text))
// === text` and the byte compare in --check mode is the determinism proof.
// Structural mutations round-trip through JSON, so every mutation stays
// parseable on purpose.
//
// The corpus (consru_export/, licensed, untracked) is read only when it resolves
// locally. When it does not, this contract prints M210_S03_CORPUS_ABSENT and
// checks the tracked subset only: the committed corpus pins, which come from the
// tracked S01 artifact, are used unchanged. The report bytes never depend on the
// corpus being mounted.
//
// Subprocesses are limited to `git ls-files` (tracked-file proof) and
// `node scripts/m210_s03_abstention_probe.mjs --check` (the generator under
// test). No network, no cargo, and no `.gsd` / ignored / absolute path is read.
//
// Run: node --test scripts/m210_s03_abstention_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

import {
  ADOPTED_CONSTRUCT_SET,
  ADOPTED_VARIANT,
  ADMISSION_VERDICT,
  ARTIFACT_RELATIVE_PATH,
  CANDIDATE_OUTCOME,
  CONFLICT_OUTCOME,
  CONTRACT_PATH,
  CORPUS_ROOT_RELATIVE,
  CORPUS_DIR_ENV,
  EMITTABLE_CODES,
  EXPECTED_COUNTS,
  EXPECTED_COVERAGE,
  KIND,
  LIFECYCLE,
  MILESTONE,
  NOT_EXECUTED,
  REPO_ROOT,
  REQUIREMENT_REFS,
  S01_EXAMPLES_PATH,
  S01_PACKET_INDEX_PATH,
  SCHEMA,
  SECTION3_PATH,
  SHA_PATTERN,
  SLICE,
  START_GATE_PATH,
  TASK,
  UNKNOWN_OUTCOME,
  UNKNOWN_REASON,
  VERDICT,
  corpusPresent,
  liveCorpusAnchors,
  liveEnv,
  renderReport,
  validateReport,
} from "./m210_s03_abstention_probe.mjs";

const root = REPO_ROOT;
const GENERATOR = "scripts/m210_s03_abstention_probe.mjs";
const SELF_PATH = fileURLToPath(import.meta.url);

// The complete fail-closed code set. The block below is asserted to document
// exactly this set (no more, no less), and the same set is asserted equal to the
// artifact's declared `fail_closed_codes`.
// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// probe_coverage_incomplete: the eighteen inputs are not all covered once, or a family is uncovered.
// adopted_set_misreported: the adopted_construct_set drifted, is empty under admission_granted, or the variant/verdict drifted.
// candidate_emitted_while_not_executed: a candidate record or candidate outcome exists while execution_state.executed is false.
// conflict_reported_while_absent: a Conflict verdict or outcome is reported while execution_state.executed is false.
// unknown_miscounted: the counts block disagrees with the outcomes, or a non-Unknown outcome slipped in.
// absence_as_falsity: absence of evidence is read as falsity, or an Unknown outcome is not reason-bound.
// adoption_read_as_execution: the report claims execution or an emitted candidate on the strength of adoption.
// execution_read_as_adoption: the report reads non-execution as non-adoption (adoption_established not true, or a no_adopted_construct reason).
// input_missing_silent: an input anchor is absent, not repository-relative, or outside the corpus root.
// input_hash_mismatch: an input anchor sha256 (or a consumed revision) differs from the live bytes.
// report_not_byte_identical: --check rendered bytes differ from the committed artifact.
// runtime_claim_present: the artifact claims a runtime, an evaluator or a crate surface.
// non_ascii_artifact: the artifact carries a non-ASCII byte.
// raw_text_leak: the artifact carries an XML tag, a provider marker or a corpus anchor key outside the closed set.
// DOCUMENTED_CODES_END

const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl ", "#[test]", "fn main"];

const CLOSED_FAMILIES = [
  "obligation",
  "permission",
  "prohibition",
  "definition",
  "competence",
  "condition",
  "exception",
  "temporal_qualification",
];

const NON_CLAIM_FRAGMENTS = [
  "not a runtime",
  "candidate_layer_not_executed",
  "adoption is not execution",
  "absence of a proven source span is never falsity",
  "no legal text is copied",
  "section 3",
  "f13",
  "no crate is touched",
];

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

const TRACKED = new Set(
  execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
    .split("\n")
    .filter((line) => line.length > 0),
);

function assertRepoRelative(relativePath) {
  assert.ok(typeof relativePath === "string" && relativePath.length > 0, "path must be a non-empty string");
  assert.ok(!path.isAbsolute(relativePath), `path must be repository-relative: ${relativePath}`);
  assert.ok(!relativePath.includes(".."), `path must not traverse: ${relativePath}`);
  assert.ok(
    !FORBIDDEN_PREFIXES.some((prefix) => relativePath.startsWith(prefix)),
    `path must not be an ignored overlay: ${relativePath}`,
  );
}

function readRepo(relativePath) {
  assertRepoRelative(relativePath);
  return readFileSync(path.join(root, relativePath), "utf8");
}

function sha256Repo(relativePath) {
  assertRepoRelative(relativePath);
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex")}`;
}

function codesOf(result) {
  return [...new Set(result.errors.map((error) => error.name))];
}

function expectCode(report, env, name) {
  const result = validateReport(report, env);
  assert.ok(codesOf(result).includes(name), `expected ${name}, got ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, false, `${name} must fail closed`);
}

// ---------------------------------------------------------------------------
// live surfaces
// ---------------------------------------------------------------------------

const LIVE_DOC = readRepo(ARTIFACT_RELATIVE_PATH);
const LIVE_REPORT = JSON.parse(LIVE_DOC);
const LIVE_S01 = JSON.parse(readRepo(S01_EXAMPLES_PATH));
const LIVE_PACKET = JSON.parse(readRepo(S01_PACKET_INDEX_PATH));
const LIVE_START_GATE = JSON.parse(readRepo(START_GATE_PATH));
const LIVE_CONTRACT = JSON.parse(readRepo(CONTRACT_PATH));
const LIVE_REGISTER = JSON.parse(readRepo("prd/architecture/m210-s01-normative-family-register.json"));

const corpusLive = corpusPresent(process.env[CORPUS_DIR_ENV], root);
const liveCorpus = corpusLive ? liveCorpusAnchors(LIVE_S01, root) : [];
if (!corpusLive) console.log("M210_S03_CORPUS_ABSENT");

const LIVE_ENV = liveEnv({
  rootDir: root,
  reportText: LIVE_DOC,
  corpusPresent: corpusLive,
  liveCorpusAnchors: liveCorpus,
  s01Examples: LIVE_S01,
  packetIndex: LIVE_PACKET,
  startGate: LIVE_START_GATE,
  s03Artifacts: { [START_GATE_PATH]: LIVE_START_GATE, [CONTRACT_PATH]: LIVE_CONTRACT },
});

// The corpus pins taken from the committed report itself. Validating against
// these keeps a code-coverage mutation independent of whether the licensed
// corpus happens to be mounted.
function corpusAnchorList() {
  return LIVE_REPORT.outcomes
    .filter((outcome) => outcome.anchor?.anchor_kind === "corpus-span")
    .map((outcome) => ({
      family: outcome.family_id,
      path: outcome.anchor.path,
      span: outcome.anchor.span,
      bytes: outcome.anchor.bytes,
      sha256: outcome.anchor.sha256,
    }));
}

function coverageEnv(text, anchors = corpusAnchorList()) {
  return liveEnv({
    rootDir: root,
    reportText: text,
    corpusPresent: true,
    liveCorpusAnchors: anchors,
    s01Examples: LIVE_S01,
    packetIndex: LIVE_PACKET,
    startGate: LIVE_START_GATE,
    s03Artifacts: { [START_GATE_PATH]: LIVE_START_GATE, [CONTRACT_PATH]: LIVE_CONTRACT },
  });
}

function clone() {
  return JSON.parse(LIVE_DOC);
}

// ---------------------------------------------------------------------------
// positive: form, identity and hygiene
// ---------------------------------------------------------------------------

test("the report exists, is canonical compact ASCII and carries no raw text", () => {
  assert.ok(existsSync(path.join(root, ARTIFACT_RELATIVE_PATH)), `${ARTIFACT_RELATIVE_PATH} must exist`);
  assert.ok(LIVE_DOC.length > 0, "the report must be non-empty");
  assert.ok(LIVE_DOC.isWellFormed(), "the report must be well-formed UTF-8");
  assert.match(LIVE_DOC, /^[\x00-\x7f]*$/, "the report must be pure ASCII");
  assert.ok(!LIVE_DOC.includes("\n"), "canonical bytes are a single line");
  assert.ok(!LIVE_DOC.endsWith("\n"), "canonical bytes carry no trailing newline");
  assert.equal(
    JSON.stringify(JSON.parse(LIVE_DOC)),
    LIVE_DOC,
    "the report must round-trip to identical canonical compact bytes",
  );
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!LIVE_DOC.includes(marker), `the report must not carry ${marker}`);
  }
  assert.ok(!/[\u0400-\u04ff]/.test(LIVE_DOC), "the report must carry no Cyrillic (raw legal text)");
});

test("the envelope is the declared adoption-aware abstention diagnostic", () => {
  assert.equal(LIVE_REPORT.schema, SCHEMA);
  assert.equal(LIVE_REPORT.schema_version, 1);
  assert.equal(LIVE_REPORT.kind, KIND);
  assert.equal(LIVE_REPORT.milestone, MILESTONE);
  assert.equal(LIVE_REPORT.slice, SLICE);
  assert.equal(LIVE_REPORT.task, TASK);
  assert.deepEqual(LIVE_REPORT.lifecycle, LIFECYCLE);
  assert.equal(LIVE_REPORT.authoritative, false);
  assert.equal(LIVE_REPORT.ascii_only, true);
  assert.equal(LIVE_REPORT.design_only, true);
  assert.equal(LIVE_REPORT.runtime_created, false);
  assert.equal(LIVE_REPORT.evaluator_created, false);
  assert.deepEqual(LIVE_REPORT.requirement_refs, REQUIREMENT_REFS);
  assert.equal(LIVE_REPORT.verdict, VERDICT);
  assert.equal(LIVE_REPORT.absence_is_not_falsity, true);
  assert.ok(typeof LIVE_REPORT.revision_policy === "string" && LIVE_REPORT.revision_policy.length > 0);
  for (const forbidden of ["evaluator", "runtime", "truth_table", "decision_table"]) {
    assert.ok(!(forbidden in LIVE_REPORT), `the report must not carry the key ${forbidden}`);
  }
});

test("guards stay at their required zero and the section 3 pin is live", () => {
  const { guards } = LIVE_REPORT;
  assert.deepEqual(guards.crates_touched, []);
  assert.equal(guards.requirements_promoted, 0);
  assert.equal(guards.review_case_events_written, 0);
  assert.equal(guards.semantics_adopted, false);
  assert.match(guards.section3_pin, SHA_PATTERN);
  assert.equal(guards.section3_pin, sha256Repo(SECTION3_PATH), "the section 3 pin must match the live bytes");
});

test("no runtime surface was created: every declared-absent surface is absent", () => {
  assert.ok(Array.isArray(LIVE_START_GATE.declared_absent_runtime_surfaces));
  assert.ok(LIVE_START_GATE.declared_absent_runtime_surfaces.length >= 3);
  for (const relativePath of LIVE_START_GATE.declared_absent_runtime_surfaces) {
    assertRepoRelative(relativePath);
    if (relativePath.startsWith("crates/")) {
      assert.ok(!existsSync(path.join(root, relativePath)), `no runtime surface may exist: ${relativePath}`);
    }
  }
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!LIVE_DOC.includes(marker), `the report must not claim the runtime marker ${marker}`);
  }
});

test("the committed report is clean under the live environment and is byte-identical to a fresh render", () => {
  assert.deepEqual(validateReport(LIVE_REPORT, LIVE_ENV), { ok: true, errors: [] });
  const rendered = renderReport({ rootDir: root });
  assert.equal(rendered.text, LIVE_DOC, "a fresh render must be byte-identical to the committed report");
  assert.deepEqual(validateReport(rendered.report, { ...LIVE_ENV, committedText: LIVE_DOC }), {
    ok: true,
    errors: [],
  });
});

// ---------------------------------------------------------------------------
// positive: adoption state, execution state and coverage
// ---------------------------------------------------------------------------

test("adoption is established from the live S02 v2 grant, not read off execution", () => {
  const { adoption_state: adoption } = LIVE_REPORT;
  assert.equal(adoption.admission_verdict, ADMISSION_VERDICT);
  assert.equal(adoption.admission_verdict, LIVE_START_GATE.admission_verdict);
  assert.equal(adoption.adoption_established, true);
  assert.equal(adoption.adoption_source, "prd/architecture/m210-s02-adoption-checkpoint-v2.md");
  assert.equal(adoption.authenticated_via, "authenticated subjective-UAT v2");
  assert.equal(adoption.owner_admission_ref, LIVE_START_GATE.owner_admission_ref);
  assert.equal(adoption.adopted_variant, ADOPTED_VARIANT);
  assert.deepEqual(adoption.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.deepEqual(adoption.adopted_construct_set, LIVE_START_GATE.adopted_construct_set);
  assert.equal(adoption.normative_semantics_adopted, false);
  assert.equal(adoption.execution_separated, true);
  assert.ok(typeof adoption.note === "string" && adoption.note.length > 0);
  assert.equal(LIVE_REPORT.source_revision, LIVE_START_GATE.source_revision);
});

test("execution stays not-executed and is separate from adoption", () => {
  const { execution_state: execution } = LIVE_REPORT;
  assert.equal(execution.state, NOT_EXECUTED);
  assert.equal(execution.executed, false);
  assert.equal(execution.candidates_emitted, 0);
  assert.equal(execution.conflicts, 0);
  assert.equal(LIVE_START_GATE.execution_state.executed, false);
  assert.ok(typeof execution.note === "string" && execution.note.length > 0);
});

test("coverage is complete over the eighteen inputs and the eight closed families", () => {
  const { coverage } = LIVE_REPORT;
  assert.deepEqual(coverage, EXPECTED_COVERAGE);
  const ids = LIVE_REPORT.outcomes.map((outcome) => outcome.input_id);
  assert.equal(new Set(ids).size, ids.length, "input ids must be unique");
  const expectedIds = [
    ...LIVE_S01.dispute_cards.map((card) => card.card_id),
    ...LIVE_S01.corpus_probes.map((probe) => probe.probe_id),
    ...LIVE_S01.negative_examples.map((example) => example.example_id),
  ];
  assert.deepEqual([...ids].sort(), [...expectedIds].sort(), "coverage must be exactly the S01 inputs");
  const families = [...new Set(LIVE_REPORT.outcomes.map((outcome) => outcome.family_id).filter(Boolean))];
  assert.deepEqual([...families].sort(), [...CLOSED_FAMILIES].sort());
  assert.deepEqual([...LIVE_REGISTER.families.map((family) => family.family_id)].sort(), [...CLOSED_FAMILIES].sort());
});

test("every input is Unknown for the one stated reason and none is read as falsity", () => {
  assert.equal(LIVE_REPORT.outcomes.length, EXPECTED_COVERAGE.inputs);
  for (const outcome of LIVE_REPORT.outcomes) {
    assert.equal(outcome.adoption_established, true, `${outcome.input_id} must record the adopted layer`);
    assert.equal(outcome.executed, false, `${outcome.input_id} must record not-executed`);
    assert.equal(outcome.outcome, UNKNOWN_OUTCOME, `${outcome.input_id} must be Unknown`);
    assert.equal(outcome.reason, UNKNOWN_REASON, `${outcome.input_id} must state the abstention reason`);
    assert.equal(outcome.absence_is_falsity, false, `${outcome.input_id} must not read absence as falsity`);
  }
  assert.deepEqual(LIVE_REPORT.counts, EXPECTED_COUNTS);
  assert.equal(LIVE_REPORT.counts.adopted_constructs, ADOPTED_CONSTRUCT_SET.length);
  assert.equal(LIVE_REPORT.counts.candidates, 0);
  assert.equal(LIVE_REPORT.counts.conflicts, 0);
  assert.equal(LIVE_REPORT.counts.unknown, EXPECTED_COVERAGE.inputs);
});

// ---------------------------------------------------------------------------
// positive: anchors, the committed scan and the consumed sources
// ---------------------------------------------------------------------------

test("tracked anchors are tracked and hash-pinned; corpus anchors are count-only", () => {
  const corpusAnchorKeys = ["anchor_kind", "path", "span", "bytes", "sha256"];
  for (const outcome of LIVE_REPORT.outcomes) {
    assertRepoRelative(outcome.anchor.path);
    if (outcome.anchor.anchor_kind === "tracked") {
      assert.ok(TRACKED.has(outcome.anchor.path), `anchor must be tracked: ${outcome.anchor.path}`);
      assert.equal(outcome.anchor.sha256, sha256Repo(outcome.anchor.path), "anchor pin must match live bytes");
      assert.ok(typeof outcome.anchor.section === "string" && outcome.anchor.section.length > 0);
      continue;
    }
    assert.equal(outcome.anchor.anchor_kind, "corpus-span");
    assert.deepEqual(
      Object.keys(outcome.anchor),
      corpusAnchorKeys,
      "a corpus anchor must carry exactly the count-only keys in canonical order",
    );
    assert.ok(outcome.anchor.path.startsWith(`${CORPUS_ROOT_RELATIVE}/`));
    assert.match(outcome.anchor.sha256, SHA_PATTERN);
    assert.ok(Number.isInteger(outcome.anchor.bytes) && outcome.anchor.bytes > 0);
    assert.ok(Number.isInteger(outcome.anchor.span.start) && outcome.anchor.span.end > outcome.anchor.span.start);
  }
});

test("no committed S03 artifact carries a candidate record or a Conflict verdict", () => {
  assert.deepEqual(LIVE_REPORT.scan, {
    artifacts_scanned: 3,
    candidate_records: 0,
    conflict_verdicts: 0,
  });
  assert.ok(!("candidates" in LIVE_CONTRACT), "the semantics contract must not carry candidate records");
  assert.equal(LIVE_CONTRACT.candidate_envelope.minted, false);
  for (const outcome of LIVE_REPORT.outcomes) {
    assert.notEqual(outcome.outcome, CANDIDATE_OUTCOME);
    assert.notEqual(outcome.outcome, CONFLICT_OUTCOME);
  }
});

test("consumed sources are tracked and byte-bound, and the S01 packet index agrees", () => {
  assert.ok(LIVE_REPORT.consumes.length >= 5);
  for (const entry of LIVE_REPORT.consumes) {
    assertRepoRelative(entry.path);
    assert.ok(TRACKED.has(entry.path), `consumed source must be tracked: ${entry.path}`);
    assert.equal(entry.sha256, sha256Repo(entry.path), `consumed source must match live bytes: ${entry.path}`);
    assert.ok(typeof entry.role === "string" && entry.role.length > 0);
  }
  const declared = LIVE_PACKET.artifacts.find((artifact) => artifact.path === S01_EXAMPLES_PATH);
  assert.ok(declared, "the S01 packet index must declare the examples artifact");
  assert.equal(declared.sha256, sha256Repo(S01_EXAMPLES_PATH));
});

test("corpus anchors carry no legal text: live corpus byte windows never appear in the report", () => {
  if (!corpusLive) {
    console.log("M210_S03_CORPUS_ABSENT: skipping the live corpus anti-leak sample");
    return;
  }
  assert.equal(liveCorpus.length, LIVE_S01.corpus_probes.length, "every corpus probe must resolve locally");
  const reportBytes = readFileSync(path.join(root, ARTIFACT_RELATIVE_PATH));
  let windows = 0;
  for (const anchor of liveCorpus) {
    const bytes = readFileSync(path.join(root, anchor.path));
    for (const offset of [0, 128, Math.max(0, bytes.length - 256)]) {
      const window = bytes.subarray(offset, offset + 96);
      if (window.length < 16) continue;
      assert.ok(
        !reportBytes.includes(window),
        `no corpus bytes may leak into the report: ${anchor.path}@${offset}`,
      );
      windows += 1;
    }
    assert.equal(anchor.sha256, sha256Repo(anchor.path), "the live corpus pin must match the committed pin");
  }
  assert.ok(windows > 0, "the anti-leak sample must have inspected at least one corpus window");
});

// ---------------------------------------------------------------------------
// positive: the declared code set and the companion documentation
// ---------------------------------------------------------------------------

test("the declared fail-closed code set matches the documented set", () => {
  assert.deepEqual(LIVE_REPORT.fail_closed_codes, EMITTABLE_CODES);
  assert.equal(new Set(LIVE_REPORT.fail_closed_codes).size, LIVE_REPORT.fail_closed_codes.length);
  assert.deepEqual(
    [...LIVE_REPORT.fail_closed_codes].sort(),
    [...LIVE_REPORT.fail_closed_codes],
    "the declared code set must be sorted for a stable projection",
  );

  const source = readFileSync(SELF_PATH, "utf8");
  const block = source.match(/DOCUMENTED_CODES_BEGIN\n([\s\S]*?)DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented code block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.replace(/^\/\/\s*/, "").trim())
    .filter((line) => line.length > 0)
    .map((line) => line.split(":")[0].trim());
  assert.deepEqual([...documented].sort(), [...EMITTABLE_CODES].sort(), "documented codes must equal the declared set");
});

test("non-claims state the adopted-but-not-executed contour and refuse runtime claims", () => {
  assert.ok(Array.isArray(LIVE_REPORT.non_claims) && LIVE_REPORT.non_claims.length >= 6);
  const joined = LIVE_REPORT.non_claims.join("\n").toLowerCase();
  for (const fragment of NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment.toLowerCase()), `non-claims must state: ${fragment}`);
  }
});

// ---------------------------------------------------------------------------
// positive: --check writes nothing and is byte-identical
// ---------------------------------------------------------------------------

test("the generator --check is byte-identical and writes nothing", () => {
  const before = readFileSync(path.join(root, ARTIFACT_RELATIVE_PATH), "utf8");
  const result = spawnSync("node", [GENERATOR, "--check"], { cwd: root, encoding: "utf8" });
  assert.equal(result.status, 0, `--check must exit 0: ${result.stderr}`);
  assert.match(result.stdout, /M210_S03_ABSTENTION_CHECK_OK/);
  const after = readFileSync(path.join(root, ARTIFACT_RELATIVE_PATH), "utf8");
  assert.equal(after, before, "--check must not modify the committed report");
});

// ---------------------------------------------------------------------------
// negative: each declared code is empirically exercised
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "probe_coverage_incomplete",
    mutate: (report) => {
      report.outcomes.pop();
    },
  },
  {
    code: "adopted_set_misreported",
    mutate: (report) => {
      report.adoption_state.adopted_construct_set = ["obligation"];
    },
  },
  {
    code: "candidate_emitted_while_not_executed",
    mutate: (report) => {
      report.outcomes[0].outcome = CANDIDATE_OUTCOME;
    },
  },
  {
    code: "conflict_reported_while_absent",
    mutate: (report) => {
      report.outcomes[1].outcome = CONFLICT_OUTCOME;
    },
  },
  {
    code: "unknown_miscounted",
    mutate: (report) => {
      report.counts.unknown = EXPECTED_COUNTS.unknown - 1;
    },
  },
  {
    code: "absence_as_falsity",
    mutate: (report) => {
      report.absence_is_not_falsity = false;
    },
  },
  {
    code: "adoption_read_as_execution",
    mutate: (report) => {
      report.execution_state.executed = true;
      report.execution_state.state = "executed";
    },
  },
  {
    code: "execution_read_as_adoption",
    mutate: (report) => {
      report.adoption_state.adoption_established = false;
    },
  },
  {
    code: "input_missing_silent",
    mutate: (report) => {
      report.outcomes[0].anchor.path = "prd/architecture/m210-s03-absent-input.json";
    },
  },
  {
    code: "input_hash_mismatch",
    mutate: (report) => {
      report.outcomes[0].anchor.sha256 = `sha256:${"0".repeat(64)}`;
    },
  },
  {
    code: "report_not_byte_identical",
    unchanged: true,
    mutate: () => {},
    env: (env, text) => {
      env.committedText = `${text}\n`;
    },
  },
  {
    code: "runtime_claim_present",
    mutate: (report) => {
      report.runtime_created = true;
    },
  },
  {
    code: "non_ascii_artifact",
    mutate: (report) => {
      report.non_claims[0] = `${report.non_claims[0]} \u00e9`;
    },
  },
  {
    code: "raw_text_leak",
    mutate: (report) => {
      const corpusOutcome = report.outcomes.find((outcome) => outcome.anchor.anchor_kind === "corpus-span");
      corpusOutcome.anchor.text = "forbidden-corpus-text";
    },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const report = clone();
    entry.mutate(report);
    const text = JSON.stringify(report);
    if (entry.unchanged !== true) {
      assert.notEqual(text, LIVE_DOC, `${entry.code}: the mutation must actually change the artifact`);
    }
    const env = coverageEnv(text);
    if (typeof entry.env === "function") entry.env(env, text);
    const result = validateReport(report, env);
    assert.ok(
      codesOf(result).includes(entry.code),
      `${entry.code} was not emitted; got ${JSON.stringify(result.errors)}`,
    );
    covered.add(entry.code);
  }
  assert.deepEqual([...covered].sort(), [...EMITTABLE_CODES].sort(), "every declared code must have a firing mutation");
  assert.deepEqual(
    CODE_COVERAGE.map((entry) => entry.code).sort(),
    [...EMITTABLE_CODES].sort(),
    "the coverage registry must carry exactly one entry per code",
  );
});

test("negative: an absent input, a drifted input and a non-abstention outcome are all refused", () => {
  // A corpus input that does not resolve while the corpus is present is a visible
  // fail-closed error, never a quiet Unknown.
  const absentCorpus = clone();
  expectCode(
    absentCorpus,
    coverageEnv(
      JSON.stringify(absentCorpus),
      corpusAnchorList().filter((anchor) => anchor.family !== "obligation"),
    ),
    "input_missing_silent",
  );

  const absentTracked = clone();
  absentTracked.outcomes[0].anchor.path = "prd/architecture/m210-s03-absent-input.json";
  expectCode(absentTracked, coverageEnv(JSON.stringify(absentTracked)), "input_missing_silent");

  const driftedCorpus = clone();
  driftedCorpus.outcomes[8].anchor.sha256 = `sha256:${"1".repeat(64)}`;
  expectCode(driftedCorpus, coverageEnv(JSON.stringify(driftedCorpus)), "input_hash_mismatch");

  const strayText = clone();
  strayText.outcomes[8].anchor.text = "forbidden-corpus-text";
  expectCode(strayText, coverageEnv(JSON.stringify(strayText)), "raw_text_leak");

  const falseOutcome = clone();
  falseOutcome.outcomes[0].outcome = CONFLICT_OUTCOME;
  expectCode(falseOutcome, coverageEnv(JSON.stringify(falseOutcome)), "conflict_reported_while_absent");

  const candidateOutcome = clone();
  candidateOutcome.outcomes[0].outcome = CANDIDATE_OUTCOME;
  expectCode(candidateOutcome, coverageEnv(JSON.stringify(candidateOutcome)), "candidate_emitted_while_not_executed");

  const falsityReason = clone();
  falsityReason.outcomes[0].reason = "absent_so_false";
  expectCode(falsityReason, coverageEnv(JSON.stringify(falsityReason)), "absence_as_falsity");

  const legacyReason = clone();
  legacyReason.outcomes[0].reason = "no_adopted_construct";
  expectCode(legacyReason, coverageEnv(JSON.stringify(legacyReason)), "execution_read_as_adoption");

  const adopted = clone();
  adopted.adoption_state.adopted_construct_set = ["obligation"];
  expectCode(adopted, coverageEnv(JSON.stringify(adopted)), "adopted_set_misreported");

  const executed = clone();
  executed.execution_state.executed = true;
  expectCode(executed, coverageEnv(JSON.stringify(executed)), "adoption_read_as_execution");

  const missingConsume = clone();
  missingConsume.consumes[0].sha256 = `sha256:${"2".repeat(64)}`;
  expectCode(missingConsume, coverageEnv(JSON.stringify(missingConsume)), "input_hash_mismatch");
});

// ---------------------------------------------------------------------------
// markers (emitted only after the contract holds)
// ---------------------------------------------------------------------------

test("M210 S03 abstention contract markers", () => {
  assert.deepEqual(validateReport(LIVE_REPORT, LIVE_ENV), { ok: true, errors: [] });
  assert.deepEqual(LIVE_REPORT.adoption_state.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(LIVE_REPORT.adoption_state.adoption_established, true);
  assert.equal(LIVE_REPORT.execution_state.executed, false);
  assert.equal(LIVE_REPORT.counts.unknown, EXPECTED_COVERAGE.inputs);
  assert.equal(LIVE_REPORT.counts.candidates, 0);
  assert.equal(LIVE_REPORT.counts.conflicts, 0);
  assert.equal(LIVE_REPORT.coverage.families, EXPECTED_COVERAGE.families);
  assert.deepEqual(LIVE_REPORT.scan, { artifacts_scanned: 3, candidate_records: 0, conflict_verdicts: 0 });
  console.log("M210_S03_ABSTENTION_OK");
  console.log(`inputs=${LIVE_REPORT.coverage.inputs}`);
  console.log(`families=${LIVE_REPORT.coverage.families}`);
  console.log(`adopted_constructs=${LIVE_REPORT.counts.adopted_constructs}`);
  console.log(`candidates=${LIVE_REPORT.counts.candidates}`);
  console.log(`conflicts=${LIVE_REPORT.counts.conflicts}`);
  console.log(`unknown=${LIVE_REPORT.counts.unknown}`);
  console.log(`fail_closed_codes=${LIVE_REPORT.fail_closed_codes.length}`);
});
