// M209 S04 T06 contract: the slice battery carrier (D554 shape, D558/D559/D560
// acceptance, D430/D416 dispositions).
//
// The known S03 limitation was that the slice-level proof was hand-assembled
// and had no carrier. This contract is the carrier's guard: it reads the
// committed battery on disk, re-tallies every aggregate independently, and
// compares the runner's declared mandatory set (`--list`) against the list
// transcribed here by hand, so the set cannot be narrowed silently — a check
// removed from the runner fails this contract even if the artifact is edited to
// match. It also re-applies the same predicate the CLI uses (`verifyBattery`,
// `verifyArtifactText`) to mutated in-memory copies, so each documented
// fail-closed code must actually fire.
//
// Offline: `node:test` + `node:assert/strict` plus two read-only subprocesses
// (the runner's `--list` / `--verify` / usage paths, which write nothing).

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  ARTIFACT_PATH,
  ARTIFACT_REL,
  CHECKS,
  FAIL_CLOSED_CODES,
  FROZEN_PATHS,
  GROUPS,
  KIND,
  MANDATORY_CHECK_IDS,
  ROOT,
  SCHEMA,
  buildDocument,
  verifyArtifactText,
  verifyBattery,
  writeDocumentTo,
} from "./m209_s04_slice_battery.mjs";

const RUNNER_REL = "scripts/m209_s04_slice_battery.mjs";
const RUNNER_PATH = path.join(ROOT, RUNNER_REL);
const SELF_CHECK_ID = "s04_slice_battery_contract";

// DOCUMENTED_CHECK_IDS is transcribed by hand from the slice plan (T06 step 2),
// not imported from the module. `--list` must equal it exactly.
const DOCUMENTED_CHECK_IDS = Object.freeze(
  [
    "cargo_check_workspace",
    "clippy_workspace",
    "fmt_check",
    "frozen_zero_delta",
    "hierarchy_registry_admission_suite",
    "punkt_subunit_ctv_contract_suite",
    "r035_proof_gate_suite",
    "r070_proof_gate_suite",
    "s02_build_admissions_check",
    "s02_extraction_contract",
    "s02_hierarchy_candidate_check",
    "s02_regeneration_contract",
    "s02_registry_generator_check",
    "s03_amends_provision_contract",
    "s03_commencement_transition_contract",
    "s03_edition_chain_contract",
    "s03_emitter_amends_check",
    "s03_emitter_commencement_check",
    "s03_emitter_edition_chain_check",
    "s03_emitter_families_check",
    "s03_emitter_ledger_check",
    "s03_family_denominator_contract",
    "s03_frozen_m201_guard_suite",
    "s03_scope_ledger_contract",
    "s04_acceptance_boundary_suite",
    "s04_acceptance_contract",
    "s04_acceptance_ledger_check",
    "s04_corpus_recount_check",
    "s04_corpus_recount_contract",
    "s04_corroboration_contract",
    "s04_evidence_audit_check",
    "s04_gate_adjudication_check",
    "s04_gate_adjudication_contract",
    "s04_scope_adjudication_check",
    "s04_scope_adjudication_contract",
    "s04_slice_battery_contract",
  ].sort(),
);

// The ten frozen paths the battery must observe at zero delta (T06 step 2).
const DOCUMENTED_FROZEN_PATHS = Object.freeze([
  "crates/ln-kb-ontology/tests/r035_proof_gate.rs",
  "crates/ln-temporal/tests/r070_proof_gate.rs",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
  "prd/architecture/kb-hierarchy-registry-admissions.yaml",
  "prd/architecture/kb-hierarchy-registry.yaml",
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
  "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
  "prd/migration/rust-evidence/m202-s04-r035-proof-gate.json",
]);

// DOCUMENTED_FAIL_CLOSED_BEGIN
const DOCUMENTED_FAIL_CLOSED_CODES = Object.freeze(
  [
    "battery_artifact_absent",
    "battery_artifact_invalid",
    "battery_ascii_only_missing",
    "battery_check_failed",
    "battery_check_missing",
    "battery_checks_failed_mismatch",
    "battery_checks_failed_nonzero",
    "battery_checks_missing",
    "battery_checks_total_mismatch",
    "battery_counts_missing",
    "battery_count_only_missing",
    "battery_frozen_paths_mismatch",
    "battery_frozen_paths_not_unchanged",
    "battery_group_missing",
    "battery_group_unknown",
    "battery_kind_mismatch",
    "battery_lifecycle_mismatch",
    "battery_mandatory_set_mismatch",
    "battery_not_ascii",
    "battery_not_canonical",
    "battery_schema_mismatch",
    "battery_unexpected_check",
    "battery_usage",
    "battery_write_failed",
  ].sort(),
);
// DOCUMENTED_FAIL_CLOSED_END

// Observed counts are ASCII key=value lines. Keys may carry a hyphen
// (`edition-chain=`, `candidate-backed=`) and the S04 auditors prefix a bare
// marker token (`M209_S04_AUDIT_OK`), so one optional leading marker is allowed.
const COUNT_ASSIGNMENT = "[A-Za-z0-9_-]+=[A-Za-z0-9_.:-]+";
const COUNT_TOKEN = new RegExp(`^(?:[A-Za-z0-9_-]+ )?${COUNT_ASSIGNMENT}(?: ${COUNT_ASSIGNMENT})*$`);

function selfRecorded(document) {
  return document.checks.some((entry) => entry.check_id === SELF_CHECK_ID);
}

function readArtifactText() {
  return readFileSync(ARTIFACT_PATH, "utf8");
}

function readArtifact() {
  return JSON.parse(readArtifactText());
}

function isAsciiOnly(text) {
  for (let index = 0; index < text.length; index += 1) {
    if (text.charCodeAt(index) > 0x7f) return false;
  }
  return true;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// spawnSync, not execFileSync: both streams must be readable on the success
// path too, since the `--verify` parity test also asserts the success heartbeat.
function runRunner(args) {
  const result = spawnSync(process.execPath, [RUNNER_PATH, ...args], {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return {
    status: typeof result.status === "number" ? result.status : 1,
    stdout: typeof result.stdout === "string" ? result.stdout : "",
    stderr: typeof result.stderr === "string" ? result.stderr : "",
  };
}

test("the runner declares exactly the documented mandatory check set", () => {
  const result = runRunner(["--list"]);
  assert.equal(result.status, 0, result.stderr);
  const declared = result.stdout
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  assert.equal(declared.length, new Set(declared).size, "no duplicate check_id");
  assert.deepEqual([...declared].sort(), [...DOCUMENTED_CHECK_IDS]);
  const verbose = runRunner(["--list", "--verbose"]);
  assert.equal(verbose.status, 0, verbose.stderr);
  const verboseRows = verbose.stdout
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => line.split("\t"));
  assert.equal(verboseRows.length, DOCUMENTED_CHECK_IDS.length);
  for (const row of verboseRows) {
    assert.equal(row.length, 3, `verbose row has three fields: ${row.join("|")}`);
    const [, group, ...rest] = row;
    assert.ok(GROUPS.includes(group), `declared group is a known group: ${group}`);
    assert.ok(rest.join("\t").length > 0, `declared command is non-empty for ${row[0]}`);
  }
});

test("the artifact is canonical one-line ASCII count-only evidence", () => {
  const raw = readArtifactText();
  assert.equal(raw.endsWith("\n"), true, "the artifact ends with one newline");
  assert.equal(raw.trimEnd().includes("\n"), false, "the artifact is one canonical line");
  assert.equal(isAsciiOnly(raw), true, "the artifact is ASCII-only");
  const document = JSON.parse(raw);
  assert.equal(JSON.stringify(document), raw.trimEnd(), "canonical compact JSON, no reordering");
  assert.equal(document.schema, SCHEMA);
  assert.equal(document.kind, KIND);
  assert.equal(document.milestone, "M209-2yg6ix");
  assert.equal(document.slice, "S04");
  assert.equal(document.task, "T06");
  assert.equal(document.lifecycle, "[bounded]");
  assert.equal(document.count_only, true);
  assert.equal(document.ascii_only, true);
  assert.equal(path.relative(ROOT, ARTIFACT_PATH), ARTIFACT_REL);
});

test("documented fail-closed vocabulary equals the module's and the artifact's", () => {
  const document = readArtifact();
  assert.deepEqual([...FAIL_CLOSED_CODES].sort(), [...DOCUMENTED_FAIL_CLOSED_CODES]);
  assert.deepEqual([...document.fail_closed_codes].sort(), [...DOCUMENTED_FAIL_CLOSED_CODES]);
});

test("every mandatory check is recorded, green and countable", () => {
  const document = readArtifact();
  const checks = document.checks;
  assert.equal(Array.isArray(checks), true);
  assert.equal(document.checks_total, checks.length, "checks_total equals the checks length");
  const failed = checks.filter((entry) => entry.exit_code !== 0).length;
  assert.equal(failed, 0, "no recorded check has a non-zero exit code");
  assert.equal(document.checks_failed, 0);
  assert.equal(document.checks_failed, failed);
  const byId = new Map(checks.map((entry) => [entry.check_id, entry]));
  for (const checkId of DOCUMENTED_CHECK_IDS) {
    const entry = byId.get(checkId);
    if (!entry) {
      // Only the battery's own contract check may be absent, and only because
      // the runner drops its previous record before re-running it. `--verify`
      // is strict and still requires it, which the next test asserts.
      assert.equal(checkId, SELF_CHECK_ID, `mandatory check recorded: ${checkId}`);
      continue;
    }
    if (checkId === SELF_CHECK_ID) assert.equal(entry.exit_code, 0, "the self check record is green once written");
    assert.equal(entry.exit_code, 0, `exit_code is 0 for ${checkId}`);
    assert.equal(entry.verdict, "pass", `verdict is pass for ${checkId}`);
    assert.equal(typeof entry.observed_counts, "string", `observed_counts is a string for ${checkId}`);
    assert.ok(entry.observed_counts.length > 0, `observed_counts is non-empty for ${checkId}`);
    assert.equal(isAsciiOnly(entry.observed_counts), true, `observed_counts is ASCII for ${checkId}`);
    assert.ok(
      COUNT_TOKEN.test(entry.observed_counts) || entry.observed_counts === "exit=0",
      `observed_counts is a count token line for ${checkId}: ${entry.observed_counts}`,
    );
    assert.equal(typeof entry.duration_ms, "number", `duration_ms is a number for ${checkId}`);
    assert.ok(entry.duration_ms >= 0);
  }
  const manifest = new Map(CHECKS.map((check) => [check.check_id, check]));
  for (const entry of checks) {
    const declared = manifest.get(entry.check_id);
    assert.ok(declared, `recorded check is declared by the runner: ${entry.check_id}`);
    assert.equal(entry.group, declared.group, `group matches the manifest for ${entry.check_id}`);
    assert.equal(entry.command, declared.command, `command matches the manifest for ${entry.check_id}`);
  }
});

test("the mandatory set is declared inside the artifact too", () => {
  const document = readArtifact();
  assert.deepEqual([...document.mandatory_check_ids].sort(), [...DOCUMENTED_CHECK_IDS]);
  assert.deepEqual([...document.groups].sort(), [...GROUPS].sort());
  assert.equal(document.unexpected_check_ids.length, 0, "no check outside the mandatory set was recorded");
});

test("all five groups are recorded and no pending check is left beside the self check", () => {
  const document = readArtifact();
  assert.deepEqual([...document.groups_recorded].sort(), [...GROUPS].sort());
  const recorded = new Set(document.checks.map((entry) => entry.check_id));
  const missing = MANDATORY_CHECK_IDS.filter((checkId) => checkId !== SELF_CHECK_ID && !recorded.has(checkId));
  assert.deepEqual(missing, [], "every mandatory check other than the self check is recorded");
  const selfEntry = document.checks.find((entry) => entry.check_id === SELF_CHECK_ID);
  assert.equal(selfEntry === undefined, !selfRecorded(document));
});

test("the frozen paths are pinned and observed at zero delta", () => {
  const document = readArtifact();
  assert.equal(document.frozen_paths_unchanged, 1);
  assert.deepEqual([...document.frozen_paths].sort(), [...DOCUMENTED_FROZEN_PATHS]);
  assert.deepEqual([...FROZEN_PATHS].sort(), [...DOCUMENTED_FROZEN_PATHS]);
  const entry = document.checks.find((row) => row.check_id === "frozen_zero_delta");
  assert.ok(entry, "frozen_zero_delta is recorded");
  assert.equal(entry.exit_code, 0);
  assert.match(entry.observed_counts, /^paths=10 changed=0$/);
});

test("the committed artifact satisfies the same predicate the CLI verifies", () => {
  const raw = readArtifactText();
  const document = JSON.parse(raw);
  const selfPresent = selfRecorded(document);
  const strict = verifyArtifactText(raw);
  assert.deepEqual(strict, selfPresent ? [] : [`battery_check_missing:${SELF_CHECK_ID}`]);
  const result = runRunner(["--verify"]);
  if (selfPresent) {
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stderr, /M209_S04_BATTERY_OK checks=36 failed=0/);
    assert.match(result.stderr, /frozen_paths_unchanged=1 groups=5 drift=0/);
  } else {
    assert.equal(result.status, 1, "--verify is strict while the self check is in flight");
    assert.match(result.stderr, /battery_check_missing:s04_slice_battery_contract/);
    assert.match(result.stderr, /M209_S04_BATTERY_VERIFY_FAIL problems=1/);
  }
});

test("the verify predicate exempts exactly one in-flight check", () => {
  const artifact = readArtifact();
  const withSelf = clone(artifact);
  const alreadyPresent = selfRecorded(withSelf);
  if (!alreadyPresent) {
    withSelf.checks.push({
      check_id: SELF_CHECK_ID,
      group: "frozen",
      command: "node --test scripts/m209_s04_slice_battery_contract.test.mjs",
      exit_code: 0,
      duration_ms: 1,
      verdict: "pass",
      observed_counts: "pass=12 fail=0",
    });
    withSelf.checks_total += 1;
  }
  assert.deepEqual(verifyBattery(withSelf), [], "a complete green battery verifies");
  const withoutSelf = clone(withSelf);
  withoutSelf.checks = withoutSelf.checks.filter((entry) => entry.check_id !== SELF_CHECK_ID);
  const strict = verifyBattery(withoutSelf);
  assert.ok(strict.includes(`battery_check_missing:${SELF_CHECK_ID}`));
  const exempt = verifyBattery(withoutSelf, { inflight: SELF_CHECK_ID });
  assert.equal(exempt.includes(`battery_check_missing:${SELF_CHECK_ID}`), false);
  assert.ok(exempt.includes("battery_checks_total_mismatch"), "the exemption does not repair the tally");
  const alsoMissing = clone(withoutSelf);
  alsoMissing.checks = alsoMissing.checks.filter((entry) => entry.check_id !== "fmt_check");
  const wide = verifyBattery(alsoMissing, { inflight: SELF_CHECK_ID });
  assert.ok(wide.includes("battery_check_missing:fmt_check"), "the exemption is one check wide");
});

test("every documented fail-closed code fires on a mutated copy", () => {
  const document = readArtifact();
  const expected = new Map([
    [
      "battery_kind_mismatch",
      (doc) => {
        doc.kind = "not-the-battery";
      },
    ],
    [
      "battery_schema_mismatch",
      (doc) => {
        doc.schema = "law-nexus/not-the-schema/v1";
      },
    ],
    [
      "battery_lifecycle_mismatch",
      (doc) => {
        doc.lifecycle = "[validated]";
      },
    ],
    [
      "battery_count_only_missing",
      (doc) => {
        doc.count_only = false;
      },
    ],
    [
      "battery_ascii_only_missing",
      (doc) => {
        doc.ascii_only = false;
      },
    ],
    [
      "battery_checks_total_mismatch",
      (doc) => {
        doc.checks_total += 1;
      },
    ],
    [
      "battery_checks_failed_nonzero:1",
      (doc) => {
        doc.checks.find((entry) => entry.check_id === "clippy_workspace").exit_code = 1;
        doc.checks_failed = 1;
      },
    ],
    [
      "battery_checks_failed_mismatch",
      (doc) => {
        doc.checks_failed = 1;
      },
    ],
    [
      "battery_check_failed:clippy_workspace:1",
      (doc) => {
        doc.checks.find((entry) => entry.check_id === "clippy_workspace").exit_code = 1;
      },
    ],
    [
      "battery_check_missing:frozen_zero_delta",
      (doc) => {
        doc.checks = doc.checks.filter((entry) => entry.check_id !== "frozen_zero_delta");
      },
    ],
    [
      "battery_counts_missing:fmt_check",
      (doc) => {
        doc.checks.find((entry) => entry.check_id === "fmt_check").observed_counts = "";
      },
    ],
    [
      "battery_frozen_paths_not_unchanged",
      (doc) => {
        doc.frozen_paths_unchanged = 0;
      },
    ],
    [
      "battery_frozen_paths_mismatch",
      (doc) => {
        doc.frozen_paths = doc.frozen_paths.filter((entry) => !entry.endsWith("r070_proof_gate.rs"));
      },
    ],
    [
      "battery_group_missing:lint",
      (doc) => {
        doc.groups_recorded = doc.groups_recorded.filter((group) => group !== "lint");
      },
    ],
    [
      "battery_mandatory_set_mismatch",
      (doc) => {
        doc.mandatory_check_ids = doc.mandatory_check_ids.filter((id) => id !== "frozen_zero_delta");
      },
    ],
    [
      "battery_unexpected_check:rogue_check",
      (doc) => {
        doc.checks.push({ ...doc.checks[0], check_id: "rogue_check" });
        doc.checks_total += 1;
      },
    ],
    [
      "battery_checks_missing",
      (doc) => {
        doc.checks = null;
      },
    ],
  ]);
  for (const [code, mutate] of expected) {
    const mutant = clone(document);
    mutate(mutant);
    const problems = verifyBattery(mutant);
    assert.ok(problems.includes(code), `expected ${code} for mutant; got ${problems.join(",")}`);
  }
  assert.deepEqual(verifyBattery(null), ["battery_artifact_invalid"]);
  // The remaining codes are text-level or CLI-level, not document-level.
  assert.deepEqual(verifyArtifactText(null), ["battery_artifact_absent"]);
  assert.deepEqual(verifyArtifactText("{not json\n"), ["battery_artifact_invalid"]);
  assert.ok(verifyArtifactText('{"a":"\u00e9"}\n').includes("battery_not_ascii"));
  assert.ok(verifyArtifactText("{ }\n").includes("battery_not_canonical"));
  assert.ok(verifyArtifactText(`${JSON.stringify(document)}\n${JSON.stringify(document)}\n`).includes("battery_not_canonical"));
  const documented = new Set(DOCUMENTED_FAIL_CLOSED_CODES);
  const covered = new Set([
    ...expected.keys().map((code) => code.split(":")[0]),
    "battery_artifact_invalid",
    "battery_artifact_absent",
    "battery_not_ascii",
    "battery_not_canonical",
  ]);
  const uncovered = [...documented].filter((code) => !covered.has(code));
  assert.deepEqual(uncovered, ["battery_group_unknown", "battery_usage", "battery_write_failed"]);
});

test("the CLI reports the unknown group and usage codes fail-closed", () => {
  const unknownGroup = runRunner(["--run", "--group", "not-a-group"]);
  assert.equal(unknownGroup.status, 3);
  assert.match(unknownGroup.stderr, /battery_group_unknown/);
  const badUsage = runRunner(["--bogus"]);
  assert.equal(badUsage.status, 2);
  assert.match(badUsage.stderr, /battery_usage/);
  const missingGroup = runRunner(["--run"]);
  assert.equal(missingGroup.status, 2);
  assert.match(missingGroup.stderr, /battery_usage/);
});

test("the write path fails closed outside the repository and writes atomically", () => {
  const entries = new Map(readArtifact().checks.map((entry) => [entry.check_id, entry]));
  const missingParent = path.join(os.tmpdir(), `m209-s04-t06-absent-${process.pid}`, "battery.json");
  assert.throws(() => writeDocumentTo(missingParent, entries), /battery_write_failed/);
  const document = buildDocument(entries);
  assert.equal(document.checks_total, entries.size);
  assert.equal(document.checks_failed, 0);
  assert.equal(document.frozen_paths_unchanged, 1);
});
