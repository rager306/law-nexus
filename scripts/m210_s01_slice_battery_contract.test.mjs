// M210-3afp79 S01 T04 packet index and slice battery contract.
//
// Offline and fail-closed. The artifact under test is the S01 decision packet
// index (prd/architecture/m210-s01-packet-index.json): the single machine-checked
// entry for the S02 interactive decision. Nothing here is accepted semantics;
// the claims under test are that every packet artifact and every tracked input
// is live and hash-pinned, that the guards are unasserted, that the proof
// ceiling states both what the packet proves and what it does not, that the
// decision packet carries the exact owner question and its non-claims, and that
// the slice battery runs every S01 contract with a clean total.
//
// All subprocesses are limited to `node scripts/m210_s01_slice_battery.mjs`
// (which runs the three upstream S01 contracts) and `git ls-files
// --error-unmatch` (tracked-input proof). No network, no `.gsd` / ignored /
// absolute path is read as evidence, and this contract never writes a file.
//
// Run: node --test scripts/m210_s01_slice_battery_contract.test.mjs

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";

import {
  BATTERY_MARKER,
  CONTRACTS,
  MIN_CHECKS,
  REPO_ROOT,
  runBattery,
  validateBattery,
} from "./m210_s01_slice_battery.mjs";

const root = REPO_ROOT;
const BATTERY = "scripts/m210_s01_slice_battery.mjs";
const PACKET_REL = "prd/architecture/m210-s01-packet-index.json";
const DECISION_REL = "prd/architecture/m210-s01-decision-packet.md";

const PACKET_SCHEMA = "law-nexus/m210-packet-index/v1";
const PACKET_KIND = "m210-s01-packet-index";
const PACKET_TASK = "T04";
const MILESTONE = "M210-3afp79";
const SLICE = "S01";
const LIFECYCLE = ["proposed"];
const ALLOWED_ROOTS = ["prd/", "scripts/"];
const CRATES_ROOT = "crates/";
const ARTIFACT_MIN = 6;

// The guards the packet must leave untouched. `crates_touched` is the only list
// and must stay empty.
const REQUIRED_GUARDS = {
  product_runtime_changed: false,
  semantics_adopted: false,
  review_case_events_written: 0,
  requirements_promoted: 0,
  crates_touched: [],
};

// The closed set of things the packet explicitly does not prove.
const PROOF_TOPICS = ["legal_semantics", "reading_correctness", "human_gold", "runtime_fitness"];

// The exact question the S02 owner is asked. Asserted present verbatim in the
// decision packet, so a reworded question fails closed instead of drifting.
const DECISION_QUESTION =
  "Decision question for the owner: which bounded normative IR alternative should be adopted - " +
  "A family_typed_record_ir, B single_facet_slot_rule_record, or C abstention_first_candidates_only? " +
  "Accept one of A, B or C; or reject all three; or defer.";
const NON_CLAIMS_HEADING = "## Non-claims";
const VARIANT_IDS = [
  "family_typed_record_ir",
  "single_facet_slot_rule_record",
  "abstention_first_candidates_only",
];

// Rust-implementation markers, assembled at runtime so this contract does not
// itself contain the literals it refuses in every packet file.
const RUNTIME_MARKERS = ["pub" + " fn", "pub" + " struct", "imp" + "l "];

const AGGREGATE_HASH_LINE = /aggregate[_-](engine[_-])?(source[_-])?(revision|hash)"\s*:\s*"sha256:/i;

// The complete fail-closed code set. The `## Fail-closed codes` block below is
// asserted to document exactly this set (no more, no less), and the same set is
// asserted equal to the packet index's declared `fail_closed_codes`.
// ## Fail-closed codes (documented set; asserted equal to the declared set)
// DOCUMENTED_CODES_BEGIN
// battery_failed: a battery contract failed, crashed, went missing or fell below the check floor.
// artifact_missing: a declared artifact path is absent, empty or unresolvable.
// artifact_hash_mismatch: a declared artifact sha256 differs from the live file.
// artifact_outside_allowed_roots: a declared artifact path is outside prd/ and scripts/.
// crates_path_in_packet: a declared artifact path is under crates/, claiming product runtime.
// guard_asserted: a guard is missing or asserted.
// proof_ceiling_incomplete: the proven set, unproven set or a required unproven topic is missing.
// aggregate_hash_hardcoded: the aggregate engine hash is stored, or the policy stops forbidding that.
// decision_question_missing: the decision packet lacks the exact owner question or the non-claims block.
// runtime_claim_present: a packet file carries a Rust implementation marker.
// DOCUMENTED_CODES_END

function parseDocumentedCodes(source) {
  const block = source.match(/DOCUMENTED_CODES_BEGIN\r?\n([\s\S]*?)\r?\n\s*\/\/ DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented code block must be present");
  const codes = [];
  for (const line of block[1].split("\n")) {
    const match = line.match(/^\s*\/\/\s*([a-z][a-z0-9_]*):/);
    if (match) codes.push(match[1]);
  }
  return codes;
}

const SELF_SOURCE = readFileSync(path.join(root, "scripts/m210_s01_slice_battery_contract.test.mjs"), "utf8");
const DOCUMENTED_CODES = parseDocumentedCodes(SELF_SOURCE);

function liveSha256(rel) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, rel))).digest("hex")}`;
}

function resolveArtifact(rel) {
  if (typeof rel !== "string" || rel.length === 0) return null;
  const absolute = path.join(root, rel);
  if (!existsSync(absolute)) return null;
  return { sha256: liveSha256(rel) };
}

function readText(rel) {
  return readFileSync(path.join(root, rel), "utf8");
}

function readPacket() {
  return JSON.parse(readText(PACKET_REL));
}

function isTracked(rel) {
  const spawned = spawnSync("git", ["ls-files", "--error-unmatch", "--", rel], {
    cwd: root,
    encoding: "utf8",
  });
  return spawned.status === 0;
}

function packetTexts(index) {
  const entries = [{ path: PACKET_REL, text: readText(PACKET_REL) }];
  for (const artifact of index.artifacts) {
    const rel = typeof artifact === "string" ? artifact : artifact && artifact.path;
    const absolute = path.join(root, rel);
    if (typeof rel === "string" && existsSync(absolute)) {
      entries.push({ path: rel, text: readFileSync(absolute, "utf8") });
    }
  }
  return entries;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// Pure, fail-closed validation of a packet index against a resolver and a set
// of packet file texts. Returns the sorted code set; an empty array means the
// packet is structurally clean. Kept separate from the envelope shape assertion
// so the documented code set stays exactly the ten codes.
function validatePacket(index, opts = {}) {
  const codes = new Set();
  const resolve = opts.resolveArtifact || (() => null);

  const artifacts = index && Array.isArray(index.artifacts) ? index.artifacts : null;
  if (artifacts === null || artifacts.length < ARTIFACT_MIN) {
    codes.add("artifact_missing");
  }
  for (const artifact of artifacts || []) {
    const rel = typeof artifact === "string" ? artifact : artifact && artifact.path;
    if (typeof rel !== "string" || rel.length === 0) {
      codes.add("artifact_missing");
      continue;
    }
    if (rel.startsWith(CRATES_ROOT)) codes.add("crates_path_in_packet");
    if (!ALLOWED_ROOTS.some((allowed) => rel.startsWith(allowed))) {
      codes.add("artifact_outside_allowed_roots");
    }
    const resolved = resolve(rel);
    if (!resolved) {
      codes.add("artifact_missing");
      continue;
    }
    const declared = artifact && typeof artifact.sha256 === "string" ? artifact.sha256 : null;
    if (declared === null || declared !== resolved.sha256) codes.add("artifact_hash_mismatch");
  }

  const guards = index && index.guards;
  if (!guards || typeof guards !== "object") {
    codes.add("guard_asserted");
  } else {
    for (const [key, expected] of Object.entries(REQUIRED_GUARDS)) {
      const actual = guards[key];
      if (Array.isArray(expected)) {
        if (!Array.isArray(actual) || actual.length !== 0) codes.add("guard_asserted");
      } else if (actual !== expected) {
        codes.add("guard_asserted");
      }
    }
  }

  const ceiling = index && index.proof_ceiling;
  const proves = ceiling && ceiling.proves;
  const doesNotProve = ceiling && ceiling.does_not_prove;
  const topics = ceiling && ceiling.does_not_prove_topics;
  if (!Array.isArray(proves) || proves.length === 0) codes.add("proof_ceiling_incomplete");
  if (!Array.isArray(doesNotProve) || doesNotProve.length === 0) codes.add("proof_ceiling_incomplete");
  if (
    !Array.isArray(topics) ||
    topics.slice().sort().join(",") !== PROOF_TOPICS.slice().sort().join(",")
  ) {
    codes.add("proof_ceiling_incomplete");
  }

  const policy = index && index.source_revision_policy;
  if (
    !policy ||
    policy.hardcode_forbidden !== true ||
    policy.aggregate_engine_hash !== "supplied_at_validate_time" ||
    policy.must_rebind_every_tracked_input !== true ||
    policy.must_rederive_corpus_anchors !== true
  ) {
    codes.add("aggregate_hash_hardcoded");
  }
  if (AGGREGATE_HASH_LINE.test(JSON.stringify(index ?? null))) codes.add("aggregate_hash_hardcoded");

  const mdText = typeof opts.mdText === "string" ? opts.mdText : "";
  if (!mdText.includes(DECISION_QUESTION)) codes.add("decision_question_missing");
  if (!mdText.includes(NON_CLAIMS_HEADING)) codes.add("decision_question_missing");

  for (const entry of opts.packetTexts || []) {
    const text = typeof entry === "string" ? entry : entry && entry.text;
    if (typeof text !== "string") continue;
    if (RUNTIME_MARKERS.some((marker) => text.includes(marker))) codes.add("runtime_claim_present");
  }

  return [...codes].sort();
}

// The marker scan covers every packet file, with one precise exception: an
// upstream enforcement contract must name the markers it refuses, so a marker
// literal inside a `*contract.test.mjs` refusal fixture is not a claim about the
// packet. Content artifacts, the index, the generator and the battery get no
// such exemption.
function markerScanTexts(index) {
  return packetTexts(index).filter((entry) => !/contract\.test\.mjs$/.test(entry.path));
}

// Markers may exist in the enforcement contracts only; any other packet file
// that carries one is claiming product runtime.
function assertMarkerConfinement(index) {
  for (const entry of packetTexts(index)) {
    if (!RUNTIME_MARKERS.some((marker) => entry.text.includes(marker))) continue;
    assert.ok(
      /contract\.test\.mjs$/.test(entry.path),
      `${entry.path} carries a runtime marker but is not an enforcement contract`,
    );
  }
}

// The real packet, validated against the live tree: every declared artifact is
// resolved from disk, the decision packet is read from disk and every packet
// claim text is scanned for a runtime marker.
function realCodes(index) {
  return validatePacket(index, {
    resolveArtifact,
    mdText: readText(DECISION_REL),
    packetTexts: markerScanTexts(index),
  });
}

// Envelope drift is refused by a separate assertion, so it never has to borrow
// a code from the documented set.
function assertPacketEnvelope(index) {
  assert.equal(index.schema, PACKET_SCHEMA);
  assert.equal(index.schema_version, 1);
  assert.equal(index.kind, PACKET_KIND);
  assert.equal(index.milestone, MILESTONE);
  assert.equal(index.slice, SLICE);
  assert.equal(index.task, PACKET_TASK);
  assert.deepEqual(index.lifecycle, LIFECYCLE);
  assert.equal(index.authoritative, false);
  assert.equal(index.ascii_only, true);
  assert.equal(index.semantics_adopted, false);
  assert.equal(index.aggregate_hash_stored, false);
  assert.ok(Array.isArray(index.non_claims) && index.non_claims.length > 0, "non_claims must be present");
  assert.deepEqual(
    [...index.fail_closed_codes].sort(),
    DOCUMENTED_CODES.slice().sort(),
    "declared fail-closed codes must equal the documented set",
  );
}

let cachedIndex = null;
function packetIndex() {
  if (cachedIndex === null) cachedIndex = readPacket();
  return cachedIndex;
}

let cachedBattery = null;
function batteryRun() {
  if (cachedBattery === null) cachedBattery = runBattery();
  return cachedBattery;
}

test("the packet index declares the M210 S01 envelope and every artifact is live and hash-pinned", () => {
  const index = packetIndex();
  assertPacketEnvelope(index);
  assert.ok(index.artifacts.length >= ARTIFACT_MIN, "the packet must declare its artifacts");
  const seen = new Set();
  for (const artifact of index.artifacts) {
    assert.equal(typeof artifact.path, "string");
    assert.equal(typeof artifact.sha256, "string");
    assert.equal(typeof artifact.role, "string");
    assert.ok(artifact.role.length > 0, `artifact ${artifact.path} must declare a role`);
    assert.ok(!seen.has(artifact.path), `artifact ${artifact.path} is duplicated`);
    seen.add(artifact.path);
    assert.ok(
      ALLOWED_ROOTS.some((allowed) => artifact.path.startsWith(allowed)),
      `artifact ${artifact.path} is outside ${ALLOWED_ROOTS.join(" and ")}`,
    );
    assert.ok(!artifact.path.startsWith(CRATES_ROOT), `${artifact.path} must not claim crates/`);
    assert.equal(liveSha256(artifact.path), artifact.sha256, `${artifact.path} hash drifted`);
  }
  assert.deepEqual(realCodes(index), [], "the real packet must emit no fail-closed code");
});

test("the packet index binds every tracked input with a live sha256", () => {
  const index = packetIndex();
  assert.ok(Array.isArray(index.source_bindings) && index.source_bindings.length >= 4);
  for (const binding of index.source_bindings) {
    assert.equal(typeof binding.path, "string");
    assert.equal(typeof binding.role, "string");
    assert.equal(binding.sha256, liveSha256(binding.path), `${binding.path} hash drifted`);
    assert.ok(isTracked(binding.path), `${binding.path} must be git-tracked`);
  }
});

test("the guards are unasserted and the proof ceiling is complete", () => {
  const index = packetIndex();
  assert.deepEqual(index.guards, REQUIRED_GUARDS);
  assert.ok(index.proof_ceiling.proves.length >= 3);
  assert.ok(index.proof_ceiling.does_not_prove.length >= 3);
  assert.deepEqual([...index.proof_ceiling.does_not_prove_topics].sort(), PROOF_TOPICS.slice().sort());
});

test("the source revision policy forbids a hardcoded aggregate hash", () => {
  const index = packetIndex();
  const policy = index.source_revision_policy;
  assert.equal(policy.aggregate_engine_hash, "supplied_at_validate_time");
  assert.equal(policy.hardcode_forbidden, true);
  assert.equal(policy.must_rebind_every_tracked_input, true);
  assert.equal(policy.must_rederive_corpus_anchors, true);
  assert.ok(!AGGREGATE_HASH_LINE.test(JSON.stringify(index)));
});

test("the decision packet presents the exact question, the alternatives and no runtime claim", () => {
  const md = readText(DECISION_REL);
  assert.ok(md.includes(DECISION_QUESTION), "the exact owner question must be present verbatim");
  assert.ok(md.includes(NON_CLAIMS_HEADING), "the non-claims block must be present");
  for (const variant of VARIANT_IDS) {
    assert.ok(md.includes(variant), `the decision packet must present ${variant}`);
  }
  // JSON packet files must stay ASCII-only (no Cyrillic prose).
  for (const rel of [PACKET_REL, ...packetIndex().artifacts.map((a) => a.path)]) {
    if (!rel.endsWith(".json")) continue;
    assert.ok(!/[^\x00-\x7F]/.test(readText(rel)), `${rel} must stay ASCII-only`);
  }
  // No packet content file may carry a Rust implementation marker, and the only
  // files allowed to name the markers at all are the enforcement contracts.
  for (const entry of markerScanTexts(packetIndex())) {
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!entry.text.includes(marker), `${entry.path} carries a runtime marker`);
    }
  }
  assertMarkerConfinement(packetIndex());
});

test("negative: a missing, drifted or out-of-root artifact fails closed", () => {
  const index = clone(packetIndex());
  const base = clone(index);

  const missing = clone(base);
  missing.artifacts.push({ path: "prd/architecture/m210-s01-no-such-artifact.json", sha256: "sha256:" + "0".repeat(64), role: "bogus" });
  assert.ok(realCodes(missing).includes("artifact_missing"));

  const drifted = clone(base);
  drifted.artifacts[0].sha256 = `sha256:${"1".repeat(64)}`;
  assert.ok(realCodes(drifted).includes("artifact_hash_mismatch"));

  const outside = clone(base);
  outside.artifacts.push({ path: "doc/review/review-28-10-09-2026.md", sha256: liveSha256("doc/review/review-28-10-09-2026.md"), role: "bogus" });
  const outsideCodes = realCodes(outside);
  assert.ok(outsideCodes.includes("artifact_outside_allowed_roots"));

  const crates = clone(base);
  crates.artifacts.push({ path: "crates/ln-temporal/src/lib.rs", sha256: `sha256:${"2".repeat(64)}`, role: "bogus" });
  const cratesCodes = realCodes(crates);
  assert.ok(cratesCodes.includes("crates_path_in_packet"));
  assert.ok(cratesCodes.includes("artifact_outside_allowed_roots"));
});

test("negative: asserted guards, an incomplete proof ceiling and a hardcoded aggregate hash fail closed", () => {
  const base = clone(packetIndex());

  const guard = clone(base);
  guard.guards.product_runtime_changed = true;
  assert.ok(realCodes(guard).includes("guard_asserted"));

  const cratesGuard = clone(base);
  cratesGuard.guards.crates_touched = ["crates/ln-temporal"];
  assert.ok(realCodes(cratesGuard).includes("guard_asserted"));

  const emptyUnproven = clone(base);
  emptyUnproven.proof_ceiling.does_not_prove = [];
  assert.ok(realCodes(emptyUnproven).includes("proof_ceiling_incomplete"));

  const badTopics = clone(base);
  badTopics.proof_ceiling.does_not_prove_topics = ["legal_semantics"];
  assert.ok(realCodes(badTopics).includes("proof_ceiling_incomplete"));

  const stored = clone(base);
  stored.source_revision_policy.aggregate_engine_hash = `sha256:${"3".repeat(64)}`;
  assert.ok(realCodes(stored).includes("aggregate_hash_hardcoded"));

  const unguarded = clone(base);
  unguarded.source_revision_policy.hardcode_forbidden = false;
  assert.ok(realCodes(unguarded).includes("aggregate_hash_hardcoded"));
});

test("negative: a missing decision question and a runtime marker fail closed", () => {
  const index = packetIndex();
  const realMd = readText(DECISION_REL);
  const noQuestion = realMd.replace(DECISION_QUESTION, "Which alternative?");
  const noQuestionCodes = validatePacket(index, {
    resolveArtifact,
    mdText: noQuestion,
    packetTexts: markerScanTexts(index),
  });
  assert.ok(noQuestionCodes.includes("decision_question_missing"));

  const noNonClaims = realMd.replace(NON_CLAIMS_HEADING, "## Notes");
  assert.ok(
    validatePacket(index, {
      resolveArtifact,
      mdText: noNonClaims,
      packetTexts: markerScanTexts(index),
    }).includes("decision_question_missing"),
  );

  const tainted = markerScanTexts(index).concat([{ path: DECISION_REL, text: `x ${RUNTIME_MARKERS[0]} y` }]);
  assert.ok(
    validatePacket(index, { resolveArtifact, mdText: realMd, packetTexts: tainted }).includes(
      "runtime_claim_present",
    ),
  );
});

test("negative: the packet envelope is refused on drift", () => {
  const base = clone(packetIndex());
  for (const mutate of [
    (index) => (index.schema = "law-nexus/other/v1"),
    (index) => (index.kind = "m210-other"),
    (index) => (index.milestone = "M999"),
    (index) => (index.slice = "S02"),
    (index) => (index.lifecycle = ["accepted"]),
    (index) => (index.authoritative = true),
    (index) => (index.semantics_adopted = true),
    (index) => (index.ascii_only = false),
    (index) => (index.fail_closed_codes = ["artifact_missing"]),
  ]) {
    const mutated = clone(base);
    mutate(mutated);
    assert.throws(() => assertPacketEnvelope(mutated));
  }
});

test("the slice battery runs every S01 contract and reports a clean total", () => {
  const spawned = spawnSync(process.execPath, [path.join(root, BATTERY)], {
    cwd: root,
    encoding: "utf8",
    timeout: 300000,
    maxBuffer: 64 * 1024 * 1024,
  });
  const output = `${spawned.stdout || ""}${spawned.stderr || ""}`;
  assert.equal(spawned.status, 0, `battery must exit 0:\n${output.slice(-4000)}`);
  const marker = output.match(new RegExp(`^${BATTERY_MARKER} checks=(\\d+) failed=0$`, "m"));
  assert.ok(marker, `battery must print the OK marker:\n${output.slice(-4000)}`);
  assert.ok(Number.parseInt(marker[1], 10) >= MIN_CHECKS, "battery check total is below the floor");
  assert.ok(!output.includes("M210_S01_BATTERY_FAILED"));

  const result = batteryRun();
  assert.equal(result.ok, true);
  assert.equal(result.failed, 0);
  assert.ok(result.checks >= MIN_CHECKS);
  assert.equal(result.results.length, CONTRACTS.length);
  for (const entry of result.results) {
    assert.equal(entry.missing, false, `${entry.contract} must exist`);
    assert.equal(entry.exitCode, 0, `${entry.contract} must exit 0`);
    assert.ok(entry.pass > 0, `${entry.contract} must report checks`);
    assert.equal(entry.fail, 0, `${entry.contract} must report no failure`);
  }
  assert.deepEqual(validateBattery(result), []);
});

test("negative: a failed, crashed or missing battery fails closed", () => {
  const good = batteryRun();
  assert.deepEqual(validateBattery(good), []);

  const failing = clone({ results: good.results, checks: good.checks, failed: good.failed, ok: good.ok });
  failing.results[0].exitCode = 1;
  failing.results[0].fail = 2;
  failing.failed = 2;
  failing.ok = false;
  assert.deepEqual(validateBattery(failing), ["battery_failed"]);

  const crashed = clone({ results: good.results, checks: good.checks, failed: good.failed, ok: good.ok });
  crashed.results[1].exitCode = null;
  crashed.results[1].pass = 0;
  crashed.ok = false;
  crashed.failed = 1;
  assert.deepEqual(validateBattery(crashed), ["battery_failed"]);

  const underFloor = clone({ results: good.results, checks: MIN_CHECKS - 1, failed: 0, ok: true });
  assert.deepEqual(validateBattery(underFloor), ["battery_failed"]);

  const missingContract = clone({ results: good.results.slice(1), checks: good.checks, failed: 0, ok: true });
  assert.deepEqual(validateBattery(missingContract), ["battery_failed"]);

  assert.deepEqual(validateBattery(null), ["battery_failed"]);
});

test("every documented fail-closed code is empirically exercised", () => {
  const emitted = new Set();
  const index = packetIndex();
  const realMd = readText(DECISION_REL);
  const base = clone(index);
  const collect = (list) => list.forEach((code) => emitted.add(code));

  const codesFor = (mutated) =>
    validatePacket(mutated, { resolveArtifact, mdText: realMd, packetTexts: markerScanTexts(mutated) });

  const missing = clone(base);
  missing.artifacts.push({ path: "prd/architecture/m210-s01-no-such-artifact.json", sha256: `sha256:${"0".repeat(64)}`, role: "bogus" });
  collect(codesFor(missing));

  const drifted = clone(base);
  drifted.artifacts[0].sha256 = `sha256:${"1".repeat(64)}`;
  collect(codesFor(drifted));

  const outside = clone(base);
  outside.artifacts.push({ path: "doc/review/review-28-10-09-2026.md", sha256: liveSha256("doc/review/review-28-10-09-2026.md"), role: "bogus" });
  collect(codesFor(outside));

  const crates = clone(base);
  crates.artifacts.push({ path: "crates/ln-temporal/src/lib.rs", sha256: `sha256:${"2".repeat(64)}`, role: "bogus" });
  collect(codesFor(crates));

  const guard = clone(base);
  guard.guards.semantics_adopted = true;
  collect(codesFor(guard));

  const ceiling = clone(base);
  ceiling.proof_ceiling.proves = [];
  collect(codesFor(ceiling));

  const stored = clone(base);
  stored.source_revision_policy.aggregate_engine_hash = `sha256:${"3".repeat(64)}`;
  collect(codesFor(stored));

  collect(
    validatePacket(base, { resolveArtifact, mdText: "no question", packetTexts: markerScanTexts(base) }),
  );
  collect(
    validatePacket(base, {
      resolveArtifact,
      mdText: realMd,
      packetTexts: markerScanTexts(base).concat([{ path: DECISION_REL, text: `x ${RUNTIME_MARKERS[2]} y` }]),
    }),
  );

  const failing = clone(batteryRun());
  failing.failed = 1;
  failing.ok = false;
  failing.results[0].fail = 1;
  collect(validateBattery(failing));

  assert.deepEqual([...emitted].sort(), DOCUMENTED_CODES.slice().sort());
});

test("the documented code block equals the declared code set", () => {
  const index = packetIndex();
  assert.deepEqual(DOCUMENTED_CODES.slice().sort(), index.fail_closed_codes.slice().sort());
  assert.equal(new Set(DOCUMENTED_CODES).size, DOCUMENTED_CODES.length);
});

test("M210 S01 slice battery markers", () => {
  const index = packetIndex();
  assert.equal(index.artifacts.length, 12);
  assert.equal(DOCUMENTED_CODES.length, 10);
  process.stdout.write(
    `M210_S01_SLICE_BATTERY_OK packet=${PACKET_REL} artifacts=${index.artifacts.length} ` +
      `codes=${DOCUMENTED_CODES.length} battery_contracts=${CONTRACTS.length}\n`,
  );
});
