// M210-3afp79 S02 T01 rebind contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s02-rebind-report.json: the S02 pre-show rebind of every
// S01 tracked input and every corpus anchor. Nothing here is accepted semantics;
// the claims under test are that each of the 18 declared packet-index records is
// re-hashed live and still bound, that no corpus anchor is presented as verified
// without an explicit and consistent mark, that the source revision was captured
// live rather than written as a literal, that the report is canonical ASCII JSON
// that re-renders byte-identically, and that each documented fail-closed code is
// empirically emitted by a mutation.
//
// The licensed corpus (consru_export/, untracked) is read only when it resolves
// locally. When it does not, this contract asserts the fail-closed corpus-absent
// render instead: every anchor is explicitly marked verified:false with reason
// corpus_absent and `--check` refuses to report a byte-identical snapshot, rather
// than carrying a committed pin over as if it were verified (S01 Known
// Limitations (b)).
//
// All subprocesses are limited to `git ls-files --error-unmatch` (tracked-file
// proof), `git status --porcelain` (no-write proof) and
// `node scripts/m204_s08_source_revision.mjs` (live source revision). No network,
// no `.gsd` / ignored / absolute path is read as evidence, and this contract
// never writes a file.
//
// Run: node --test scripts/m210_s02_rebind_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  ANCHOR_UNVERIFIED_REASONS,
  CHECK_OK_MARKER,
  CONTRACT_MARKER,
  CORPUS_ABSENT_MARKER,
  EMITTABLE_CODES,
  LIFECYCLE,
  MILESTONE,
  PACKET_INDEX_PATH,
  PROBE_COUNT,
  PROBE_SPAN_CAP,
  REPO_ROOT,
  REPORT_RELATIVE_PATH,
  REQUIREMENT_REFS,
  SCHEMA,
  SHA_PATTERN,
  SLICE,
  SOURCE_REVISION_PATTERN,
  SOURCE_REVISION_SCRIPT,
  TASK,
  captureSourceRevision,
  corpusPresent,
  declaredInputRecords,
  fileLookup,
  loadExamples,
  loadPacketIndex,
  renderReport,
  runRebind,
  validateReport,
} from "./m210_s02_rebind.mjs";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// input_missing: a declared packet-index input is absent from disk, or a live corpus anchor is absent.
// input_hash_mismatch: a live sha256 differs from its pin, a corpus anchor drifted, or a verdict is not a bound verdict.
// input_untracked: a declared input exists on disk but git does not track it.
// input_path_not_repo_relative: a path is absolute, traverses `..`, escapes the repository root, or is an ignored overlay path.
// corpus_anchor_unverified_unmarked: a corpus anchor carries no explicit verified boolean, or its flag contradicts its reason.
// check_not_byte_identical: --check rendered bytes differ from the committed report.
// source_revision_not_captured: source_revision is absent, malformed, or a stored aggregate hash.
// raw_text_leak: the report text carries an XML tag or a provider text marker.
// non_ascii_artifact: the report text carries a non-ASCII byte.
// packet_index_unreadable: the packet index or its source_revision_policy cannot be read.
// DOCUMENTED_CODES_END

const root = REPO_ROOT;
const GENERATOR = "scripts/m210_s02_rebind.mjs";
const CONTRACT = "scripts/m210_s02_rebind_contract.test.mjs";
const REPORT_REL = REPORT_RELATIVE_PATH;

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const DESIGN_ONLY_MARKERS = ["crates/", ".rs"];
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not an adoption of normative semantics",
  "non-authoritative",
  "no legal text is copied",
  "deferred terms stay deferred-undefined",
];

// The complete set of subprocess commands this contract may spawn, and the only
// command forms the generator under test may spawn.
const CONTRACT_SPAWN_HEADS = ["git", "process.execPath"];
const GENERATOR_COMMAND_LITERALS = ['"ls-files", "--error-unmatch"'];
const FORBIDDEN_GENERATOR_GIT_SUBCOMMANDS = ['"commit"', '"push"', '"diff"', '"add"', '"checkout"'];

// ---------------------------------------------------------------------------
// shared fixtures
// ---------------------------------------------------------------------------

const reportAbsolute = path.join(root, REPORT_REL);
const committedText = readFileSync(reportAbsolute, "utf8");
const report = JSON.parse(committedText);
const lookup = fileLookup(root);
const present = corpusPresent(root);

// A live render that reuses the committed source revision: everything else is
// re-derived from disk, so this is the exact byte compare the --check mode makes.
const live = renderReport({
  rootDir: root,
  lookup,
  corpusPresent: present,
  sourceRevision: report.source_revision,
});

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function baseEnv(overrides = {}) {
  return {
    text: live.text,
    corpusPresent: present,
    liveAnchors: live.liveAnchors,
    declaredInputCount: live.declaredInputCount,
    declaredProbeCount: live.declaredProbeCount,
    sourceRevision: report.source_revision,
    exists: lookup.exists,
    isTracked: lookup.isTracked,
    sha256: lookup.sha256,
    insideRoot: lookup.insideRoot,
    ...overrides,
  };
}

function codesFor(mutated, overrides = {}) {
  const env = baseEnv({ text: JSON.stringify(mutated), ...overrides });
  return validateReport(mutated, env).errors.map((error) => error.name);
}

function gitStatus() {
  const spawned = spawnSync("git", ["status", "--porcelain"], {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  return `${spawned.stdout || ""}`;
}

function generatorSource() {
  return readFileSync(path.join(root, GENERATOR), "utf8");
}

function contractSource() {
  return readFileSync(path.join(root, CONTRACT), "utf8");
}

function sha256File(relativePath) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex")}`;
}

// Node's test runner keeps running after a failing case, so a marker printed
// from the last case would still look green on a red run. Record every failure
// and let the last case refuse to print the marker if any earlier case failed.
const failures = [];
function contract(title, body) {
  test(title, () => {
    try {
      body();
    } catch (error) {
      failures.push(title);
      throw error;
    }
  });
}

const documentedBlock = () => {
  const source = contractSource();
  const begin = source.indexOf("DOCUMENTED_CODES_BEGIN");
  const end = source.indexOf("DOCUMENTED_CODES_END");
  assert.ok(begin > 0 && end > begin, "the documented code block must be present");
  return source
    .slice(begin, end)
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z_]+): /)?.[1])
    .filter((name) => typeof name === "string");
};

// ---------------------------------------------------------------------------
// artifact shape
// ---------------------------------------------------------------------------

contract("the report exists, is canonical ASCII JSON and declares the M210 envelope", () => {
  assert.ok(existsSync(reportAbsolute), `${REPORT_REL} must exist`);
  assert.ok(!committedText.endsWith("\n"), "the report must carry no trailing newline");
  assert.ok(
    [...committedText].every((character) => character.charCodeAt(0) < 0x80),
    "the report must be ASCII-only",
  );
  assert.equal(JSON.stringify(JSON.parse(committedText)), committedText, "the report must round-trip byte-identically");
  assert.equal(report.schema, SCHEMA);
  assert.equal(report.schema_version, 1);
  assert.equal(report.kind, "m210-s02-rebind-report");
  assert.equal(report.milestone, MILESTONE);
  assert.equal(report.slice, SLICE);
  assert.equal(report.task, TASK);
  assert.deepEqual(report.lifecycle, LIFECYCLE);
  assert.equal(report.authoritative, false);
  assert.equal(report.ascii_only, true);
  assert.deepEqual(report.requirement_refs, REQUIREMENT_REFS);
  assert.deepEqual(report.fail_closed_codes, EMITTABLE_CODES);
  assert.equal(PACKET_INDEX_PATH, "prd/architecture/m210-s01-packet-index.json");
});

contract("every packet index record is present and reconciled against its live file", () => {
  const index = loadPacketIndex(root);
  const declared = declaredInputRecords(index);
  assert.equal(declared.length, 18, "the packet index declares 12 artifacts plus 6 source bindings");
  assert.equal(report.rebound_inputs.length, declared.length, "every declared record must be rebound");
  assert.equal(new Set(report.rebound_inputs.map((row) => row.path)).size, declared.length);

  const byPath = new Map(report.rebound_inputs.map((row) => [row.path, row]));
  const declaredPaths = new Set(declared.map((record) => record.path));
  for (const record of declared) {
    assert.ok(byPath.has(record.path), `${record.path} must appear in rebound_inputs`);
    const row = byPath.get(record.path);
    assert.equal(row.verdict, "match", `${record.path} must still be bound`);
    assert.equal(row.expected_sha256, record.sha256, `${record.path} must echo the index pin`);
    assert.equal(sha256File(record.path), row.expected_sha256, `${record.path} live hash must equal the pin`);
    assert.equal(row.live_sha256, row.expected_sha256, `${record.path} live_sha256 must equal the pin`);
    assert.equal(row.role, record.role, `${record.path} must echo the index role`);
    assert.ok(declaredPaths.has(record.path), `${record.path} must come from the packet index`);
    assert.equal(
      index.artifacts.some((entry) => entry.path === record.path) ||
        index.source_bindings.some((entry) => entry.path === record.path),
      true,
      `${record.path} must be declared as an artifact or a source binding`,
    );
  }
  assert.deepEqual(report.drift, [], "a clean rebind carries no drift");
  assert.equal(live.text, committedText, "a live re-render must be byte-identical to the committed report");
});

// ---------------------------------------------------------------------------
// the Known Limitations (b) closure
// ---------------------------------------------------------------------------

contract("no corpus anchor is left without an explicit verified mark", () => {
  const anchors = report.corpus_anchors;
  assert.equal(anchors.length, PROBE_COUNT, "the examples artifact declares 8 corpus probes");
  assert.equal(new Set(anchors.map((anchor) => anchor.probe_id)).size, PROBE_COUNT);
  for (const anchor of anchors) {
    assert.equal(typeof anchor.verified, "boolean", `${anchor.probe_id} must carry an explicit verified boolean`);
    if (anchor.verified === false) {
      assert.ok(anchor.unverified_reason !== "", `${anchor.probe_id} must name why it is unverified`);
      assert.ok(
        ANCHOR_UNVERIFIED_REASONS.includes(anchor.unverified_reason),
        `${anchor.probe_id} reason ${anchor.unverified_reason} must be documented`,
      );
    } else {
      assert.equal(anchor.unverified_reason, "", `${anchor.probe_id} verified anchors carry no reason`);
    }
    assert.ok(!["<", ">"].some((marker) => JSON.stringify(anchor).includes(marker)), "an anchor carries no text");
  }

  // The corpus-absent render must never present a pin as verified: this is the
  // exact hole S01 Known Limitations (b) left open.
  const absent = renderReport({
    rootDir: root,
    lookup,
    corpusPresent: false,
    sourceRevision: report.source_revision,
  });
  assert.equal(absent.report.corpus_anchors.length, PROBE_COUNT);
  for (const anchor of absent.report.corpus_anchors) {
    assert.equal(anchor.verified, false, `${anchor.probe_id} must be unverified without the corpus`);
    assert.equal(anchor.unverified_reason, "corpus_absent", `${anchor.probe_id} must name corpus_absent`);
  }
  const absentRun = runRebind(["--print"], {
    rootDir: root,
    lookup,
    corpusPresent: false,
    sourceRevision: report.source_revision,
  });
  assert.equal(absentRun.exitCode, 0);
  assert.ok(absentRun.stderr.includes(CORPUS_ABSENT_MARKER), "the corpus-absent marker must be printed");
});

contract("a corpus anchor re-derives to the live file when the corpus resolves", () => {
  const examples = loadExamples(root);
  assert.equal(examples.corpus_probes.length, PROBE_COUNT);
  if (!present) {
    for (const anchor of report.corpus_anchors) {
      assert.equal(anchor.verified, false, "without the corpus the committed artifact is not re-verified");
      assert.equal(anchor.unverified_reason, "corpus_absent");
    }
    return;
  }
  for (const anchor of report.corpus_anchors) {
    const absolute = path.join(root, anchor.path);
    assert.ok(existsSync(absolute), `${anchor.path} must resolve in the licensed corpus`);
    const bytes = readFileSync(absolute);
    assert.equal(anchor.bytes, bytes.length, `${anchor.probe_id} byte count must be live`);
    assert.equal(
      anchor.sha256,
      `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
      `${anchor.probe_id} sha256 must be live`,
    );
    assert.deepEqual(anchor.span, { start: 0, end: Math.min(bytes.length, PROBE_SPAN_CAP) });
    assert.equal(anchor.verified, true, `${anchor.probe_id} must be verified while the corpus resolves`);
    const committed = examples.corpus_probes.find((probe) => probe.probe_id === anchor.probe_id);
    assert.equal(committed.path, anchor.path, `${anchor.probe_id} must keep the recorded path`);
  }
});

// ---------------------------------------------------------------------------
// source revision
// ---------------------------------------------------------------------------

contract("source_revision is captured live and never a hardcoded literal", () => {
  assert.match(report.source_revision, SOURCE_REVISION_PATTERN);
  assert.match(report.source_revision, SHA_PATTERN);
  const source = generatorSource();
  assert.ok(
    !/sha256:[0-9a-f]{64}/.test(source),
    "the generator must not carry a hardcoded aggregate hash",
  );
  const captured = captureSourceRevision(root);
  assert.match(captured, SOURCE_REVISION_PATTERN, "the capture path must still return sha256:<64hex>");

  // The rendered revision is the injected one: the field is a capture, not a
  // constant. A hardcoded value would ignore the injection.
  const injected = `sha256:${"0123456789abcdef".repeat(4)}`;
  const injectedRender = renderReport({
    rootDir: root,
    lookup,
    corpusPresent: present,
    sourceRevision: injected,
  });
  assert.equal(injectedRender.report.source_revision, injected);
  assert.notEqual(report.source_revision, injected);
});

contract("the policy echo is read from the packet index, not restated", () => {
  const index = loadPacketIndex(root);
  assert.deepEqual(report.source_revision_policy_echo, {
    must_rebind_every_tracked_input: index.source_revision_policy.must_rebind_every_tracked_input,
    must_rederive_corpus_anchors: index.source_revision_policy.must_rederive_corpus_anchors,
    aggregate_engine_hash: index.source_revision_policy.aggregate_engine_hash,
    hardcode_forbidden: index.source_revision_policy.hardcode_forbidden,
    statement: index.source_revision_policy.statement,
  });
  assert.equal(report.source_revision_policy_echo.aggregate_engine_hash, "supplied_at_validate_time");
  assert.equal(report.source_revision_policy_echo.hardcode_forbidden, true);
});

// ---------------------------------------------------------------------------
// hygiene and non-claims
// ---------------------------------------------------------------------------

contract("the report carries no runtime markers, no raw text and no design-only claims", () => {
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!committedText.includes(marker), `runtime marker ${marker} must be absent`);
  }
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!committedText.includes(marker), `raw text marker ${marker} must be absent`);
  }
  for (const marker of DESIGN_ONLY_MARKERS) {
    assert.ok(!committedText.includes(marker), `design-only marker ${marker} must be absent`);
  }
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(committedText.includes(fragment), `non-claim fragment ${fragment} must be present`);
  }
  assert.ok(Array.isArray(report.non_claims) && report.non_claims.length >= 5);
  assert.equal(report.rebound_inputs.every((row) => !row.path.startsWith("/")), true);
  assert.equal(report.corpus_anchors.every((anchor) => !anchor.path.startsWith("/")), true);
});

// ---------------------------------------------------------------------------
// --check
// ---------------------------------------------------------------------------

contract("--check re-renders byte-identically and writes nothing", () => {
  const before = gitStatus();
  const run = runRebind(["--check"], { rootDir: root, lookup, corpusPresent: present });
  const after = gitStatus();
  assert.equal(after, before, "--check must not change the worktree");
  if (present) {
    assert.equal(run.exitCode, 0, run.stderr.join("\n"));
    assert.ok(run.stdout.includes(CHECK_OK_MARKER), "the check marker must be printed");
    assert.equal(run.wrote, false);
  } else {
    assert.equal(run.exitCode, 1, "without the corpus --check must fail closed rather than pass");
    assert.ok(run.stderr.includes(CORPUS_ABSENT_MARKER));
    assert.ok(run.stderr.some((line) => line.startsWith("check_not_byte_identical")));
  }
});

contract("--print captures a live revision without writing the report", () => {
  const before = gitStatus();
  const run = runRebind(["--print"], { rootDir: root, lookup, corpusPresent: present });
  const after = gitStatus();
  assert.equal(after, before, "--print must not change the worktree");
  assert.equal(run.exitCode, 0, run.stderr.join("\n"));
  assert.equal(run.wrote, false);
  const printed = JSON.parse(run.stdout.join("\n"));
  assert.match(printed.source_revision, SOURCE_REVISION_PATTERN);
  assert.equal(printed.rebound_inputs.length, 18);
  assert.equal(printed.corpus_anchors.length, PROBE_COUNT);
});

// ---------------------------------------------------------------------------
// fail-closed codes
// ---------------------------------------------------------------------------

contract("every documented fail-closed code is emitted on a mutated copy", () => {
  const base = clone(report);
  const clean = validateReport(base, baseEnv({ text: JSON.stringify(base) }));
  assert.equal(clean.ok, true, JSON.stringify(clean.errors));

  const emitted = new Set();
  const collect = (codes) => {
    for (const name of codes) emitted.add(name);
  };

  // input_missing: a declared row disappears (count and existence both fail closed).
  const droppedInput = clone(base);
  droppedInput.rebound_inputs = droppedInput.rebound_inputs.slice(0, droppedInput.rebound_inputs.length - 1);
  collect(codesFor(droppedInput));

  // input_hash_mismatch: a pin no longer matches the live file.
  const wrongPin = clone(base);
  wrongPin.rebound_inputs[0].expected_sha256 = `sha256:${"0".repeat(64)}`;
  collect(codesFor(wrongPin));

  // input_untracked: the live file is present but git does not track it.
  collect(
    codesFor(clone(base), {
      isTracked: (relativePath) => relativePath !== base.rebound_inputs[0].path,
    }),
  );

  // input_path_not_repo_relative: an absolute, traversing or ignored path.
  const absolutePath = clone(base);
  absolutePath.rebound_inputs[0].path = "/etc/passwd";
  collect(codesFor(absolutePath));
  const traversingPath = clone(base);
  traversingPath.rebound_inputs[0].path = "../outside/report.json";
  collect(codesFor(traversingPath));
  const ignoredPath = clone(base);
  ignoredPath.rebound_inputs[0].path = ".agents/rules.md";
  collect(codesFor(ignoredPath));

  // corpus_anchor_unverified_unmarked: the mark is absent or contradicts itself.
  const unmarked = clone(base);
  delete unmarked.corpus_anchors[0].verified;
  collect(codesFor(unmarked));
  const unreasoned = clone(base);
  unreasoned.corpus_anchors[0].verified = false;
  unreasoned.corpus_anchors[0].unverified_reason = "";
  collect(codesFor(unreasoned));
  const contradictory = clone(base);
  contradictory.corpus_anchors[0].verified = true;
  contradictory.corpus_anchors[0].unverified_reason = "corpus_absent";
  collect(codesFor(contradictory));
  // A verified mark with no corpus to back it is the same failure.
  const claimedVerified = clone(base);
  claimedVerified.corpus_anchors[0].verified = true;
  claimedVerified.corpus_anchors[0].unverified_reason = "";
  collect(codesFor(claimedVerified, { corpusPresent: false, liveAnchors: [] }));

  // check_not_byte_identical: the committed bytes differ from the render.
  collect(codesFor(clone(base), { text: live.text, committedText: `${live.text} ` }));

  // source_revision_not_captured: absent, malformed or a stored aggregate hash.
  const badRevision = clone(base);
  badRevision.source_revision = "deadbeef";
  collect(codesFor(badRevision, { sourceRevision: undefined }));
  const storedAggregate = clone(base);
  storedAggregate.source_revision_policy_echo.aggregate_engine_hash = `sha256:${"1".repeat(64)}`;
  collect(codesFor(storedAggregate, { sourceRevision: undefined }));
  const movedRevision = clone(base);
  movedRevision.source_revision = `sha256:${"2".repeat(64)}`;
  collect(codesFor(movedRevision));

  // raw_text_leak: an XML or provider text marker in the report text.
  const rawLeak = clone(base);
  rawLeak.non_claims[0] = "leaked <screenTip>";
  collect(codesFor(rawLeak));

  // non_ascii_artifact: a non-ASCII byte in the report text.
  const nonAscii = clone(base);
  nonAscii.non_claims[0] = "dash \u2014 not ascii";
  collect(codesFor(nonAscii));

  // packet_index_unreadable: the index or its policy cannot be read.
  collect(codesFor(clone(base), { packetIndexError: "packet index is absent" }));
  const noEcho = clone(base);
  delete noEcho.source_revision_policy_echo;
  collect(codesFor(noEcho));
  const noPolicy = clone(base);
  noPolicy.source_revision_policy_echo.must_rebind_every_tracked_input = false;
  collect(codesFor(noPolicy));

  assert.deepEqual([...emitted].sort(), EMITTABLE_CODES.slice().sort());
});

contract("the documented code block equals the declared code set", () => {
  const documented = documentedBlock();
  assert.equal(new Set(documented).size, documented.length, "the documented block must carry no duplicate");
  assert.deepEqual(documented.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(report.fail_closed_codes.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.equal(EMITTABLE_CODES.length, 10);
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

contract("the contract uses only the allowed subprocesses and reads no ignored path", () => {
  const source = contractSource();
  const heads = [...source.matchAll(/spawnSync\(\s*([A-Za-z_$][\w$]*(?:\.[\w$]+)*|"[^"]*")/g)].map(
    (match) => match[1],
  ).map((head) => (head.startsWith('"') && head.endsWith('"') ? head.slice(1, -1) : head));
  assert.ok(heads.length >= 1, "the contract must spawn at least the git probes");
  for (const head of heads) {
    assert.ok(
      CONTRACT_SPAWN_HEADS.includes(head),
      `spawnSync head ${head} is outside the allowed set ${CONTRACT_SPAWN_HEADS.join(", ")}`,
    );
  }
  assert.ok(source.includes('["ls-files", "--error-unmatch"'), "tracked-file proof is required");
  assert.ok(source.includes('["status", "--porcelain"]'), "no-write proof is required");
  assert.ok(source.includes("SOURCE_REVISION_SCRIPT"), "live source revision capture is required");
  assert.ok(
    !/readFileSync\(\s*(?:path\.join\(root,\s*)?"(?:\.gsd|\.agents|\.lex|\.planning|\.audits)\//.test(source),
    "the contract must not read an ignored path",
  );
  assert.ok(!/readFileSync\(\s*path\.join\(root,\s*"\//.test(source), "the contract must not read an absolute path");
});

contract("the generator uses only the allowed subprocesses and writes only the report", () => {
  const source = generatorSource();
  for (const literal of GENERATOR_COMMAND_LITERALS) {
    assert.ok(source.includes(literal), `the generator must use ${literal}`);
  }
  assert.ok(source.includes(SOURCE_REVISION_SCRIPT), "the generator must capture the live source revision");
  for (const forbidden of FORBIDDEN_GENERATOR_GIT_SUBCOMMANDS) {
    assert.ok(!source.includes(forbidden), `the generator must not run git ${forbidden}`);
  }
  assert.ok(!source.includes('spawnSync("git"'), "the generator's git access must stay read-only ls-files");
  const writes = [...source.matchAll(/writeFileSync\(/g)];
  assert.equal(writes.length, 1, "the generator must write exactly one file");
  assert.ok(source.includes("writeFileSync(reportPath, rendered.text)"));
  assert.ok(!/\b(?:fetch|https?):\/\//.test(source), "the generator must be offline");
});

// ---------------------------------------------------------------------------
// markers
// ---------------------------------------------------------------------------

contract("M210 S02 rebind markers", () => {
  assert.deepEqual(failures, [], "a failing case must suppress the success marker");
  process.stdout.write(
    `${CONTRACT_MARKER} inputs=${report.rebound_inputs.length} anchors=${report.corpus_anchors.length} ` +
      `codes=${EMITTABLE_CODES.length} corpus=${present ? "present" : "absent"}\n`,
  );
});
