// M216/S04 retrieval metrics EVID register closure contract (T04).
//
// Offline and fail-closed: the live standalone retrieval EVID register must
// parse, map exactly the five declared retrieval evidence rows once each, close
// all five as bounded evidence with status + proof_level + non-empty non-claims,
// resolve every active anchor to a tracked repo-relative path outside
// prd/archive/, and carry the D537 consistency block plus the S04 closure
// record. The two benchmark rows must cite the tracked S04 metrics artifacts and
// the metrics proof command.
//
// No subprocess, no network, no cargo: this contract reads the register and the
// declared anchor paths from disk only, and never reads a `.gsd` / ignored /
// absolute path as evidence. Every documented fail-closed code is exercised by a
// mutation so the suite cannot assert a code it would never actually emit.
//
// Run: node --test scripts/m216_s04_metrics_register_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const REGISTER = "prd/migration/rust-evidence/m216-retrieval-evid-register.json";
const CONTRACT_PATH = "scripts/m216_s04_metrics_register_contract.test.mjs";

const REGISTER_SCHEMA_VERSION = "law-nexus-m216-retrieval-evid-register/v1";
const REGISTER_KIND = "m216-retrieval-evid-register";
const MILESTONE = "M216-8dps6e";
const REGISTRY_REQUIREMENT = "R034";

const REAL_ARTIFACT_EVID_ID = "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF";
const QUALITY_EVID_ID = "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF";
const RUNTIME_EVID_ID = "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF";

const PINNED_SHA256 = "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d";
const PINNED_BYTES = 193726;
const REAL_PROOF_COMMAND = "cargo test -p ln-query --offline --test real_artifact_retrieval -- --nocapture";
const BENCHMARK_PROOF_COMMAND = "cargo test -p ln-query --offline --test retrieval_metrics";

const BENCHMARK_ANCHORS = [
  "prd/retrieval/rust_retrieval_metrics_contract.md",
  "crates/ln-query/src/retrieval_metrics.rs",
  "crates/ln-query/tests/retrieval_metrics.rs",
  "prd/retrieval/rust_retrieval_metrics_proof.md",
];

const QUALITY_METRIC_KEYS = [
  "selection_accuracy",
  "positive_selection_rate",
  "scoped_no_answer_accuracy",
  "ambiguous_rejection_rate",
  "unsafe_rejection_rate",
  "unresolvable_citation_rejection_rate",
];

const RUNTIME_PROFILE_KEYS = [
  "documents_processed",
  "projected_views",
  "projected_segments",
  "resolver_evidence_spans",
  "cases_run",
];

const DECLARED_EVID_IDS = [
  "EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF",
  "EVID-OFFLINE-CITATION-RETRIEVAL-PROOF",
  REAL_ARTIFACT_EVID_ID,
  QUALITY_EVID_ID,
  RUNTIME_EVID_ID,
];

const ARCHIVE_PREFIX = "prd/archive/";
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// DOCUMENTED_CODES_BEGIN
// schema_version_mismatch: the register schema_version is not the declared one.
// register_kind_mismatch: the register kind is not the declared one.
// register_identity_mismatch: milestone / authoritative / registry_requirement drift.
// row_count_mismatch: the register does not carry exactly five rows.
// evid_id_missing: a declared EVID id is absent.
// evid_id_duplicated: a declared EVID id appears more than once.
// evid_id_unknown: the register carries an undeclared EVID id.
// anchor_missing: an active anchor path is empty.
// anchor_absolute: an active anchor path is absolute.
// anchor_escaping: an active anchor path escapes the repository.
// anchor_ignored: an active anchor path is under an ignored prefix.
// archive_as_active_anchor: an active anchor path is under prd/archive/.
// active_anchor_disk_missing: an active anchor path does not exist on disk.
// closed_row_metadata_missing: a closed row lacks proof_level or proof_command.
// closed_row_non_claims_missing: a closed row has no non-claims.
// pending_row_present: a declared row is still pending, not bounded evidence.
// benchmark_anchor_missing: a benchmark row does not cite every S04 metrics artifact.
// benchmark_proof_level_wrong: a benchmark row carries the wrong proof_level.
// benchmark_command_missing: a benchmark row does not cite the metrics proof command.
// quality_metrics_missing: the quality row lacks a 1.0 metric or is not mismatch-free.
// runtime_profile_missing: the runtime row lacks a positive structural counter.
// host_boundary_timing_asserted: the observed timing is claimed reproducible or asserted.
// real_artifact_pin_missing: the real-artifact row does not cite the pinned sha256.
// real_artifact_command_missing: the real-artifact row does not cite its proof command.
// d537_block_missing: the D537 consistency block is absent.
// d537_block_inconsistent: the D537 consistency block is not fail-closed.
// prior_art_not_archived: a prior_art entry is not under prd/archive/.
// prior_art_disk_missing: a prior_art path does not exist on disk.
// python_era_anchor_promoted: an archived Python anchor is used as an active anchor.
// s04_closure_missing: the S04 closure block is absent.
// s04_closure_inconsistent: the S04 closure block does not match the closed rows.
// register_non_claims_missing: the register has no register-level non-claims.
// DOCUMENTED_CODES_END
const EMITTABLE_CODES = [
  "schema_version_mismatch",
  "register_kind_mismatch",
  "register_identity_mismatch",
  "row_count_mismatch",
  "evid_id_missing",
  "evid_id_duplicated",
  "evid_id_unknown",
  "anchor_missing",
  "anchor_absolute",
  "anchor_escaping",
  "anchor_ignored",
  "archive_as_active_anchor",
  "active_anchor_disk_missing",
  "closed_row_metadata_missing",
  "closed_row_non_claims_missing",
  "pending_row_present",
  "benchmark_anchor_missing",
  "benchmark_proof_level_wrong",
  "benchmark_command_missing",
  "quality_metrics_missing",
  "runtime_profile_missing",
  "host_boundary_timing_asserted",
  "real_artifact_pin_missing",
  "real_artifact_command_missing",
  "d537_block_missing",
  "d537_block_inconsistent",
  "prior_art_not_archived",
  "prior_art_disk_missing",
  "python_era_anchor_promoted",
  "s04_closure_missing",
  "s04_closure_inconsistent",
  "register_non_claims_missing",
];

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
}

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function sameSet(a, b) {
  const sa = [...new Set(a)].sort();
  const sb = [...new Set(b)].sort();
  return sa.length === sb.length && sa.every((value, index) => value === sb[index]);
}

function byId(register, evidId) {
  return (register?.rows ?? []).find((row) => row?.evid_id === evidId);
}

function activeAnchorPaths(row) {
  return (row?.active_anchors ?? []).map((anchor) => anchor?.path).filter(nonEmpty);
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateRegister(register, overrides = {}) {
  const pick = (key, fallback) => (overrides[key] === undefined ? fallback : overrides[key]);
  const fileExists = pick("fileExists", repoExists);
  const registerText = pick("registerText", JSON.stringify(register ?? null));

  const errors = [];
  const add = (code, detail) => errors.push({ code, detail });

  const rows = Array.isArray(register?.rows) ? register.rows : [];

  // (1) register identity and shape.
  if (register?.schema_version !== REGISTER_SCHEMA_VERSION) {
    add("schema_version_mismatch", `schema_version=${register?.schema_version}`);
  }
  if (register?.kind !== REGISTER_KIND) {
    add("register_kind_mismatch", `kind=${register?.kind}`);
  }
  if (register?.milestone !== MILESTONE || register?.authoritative !== false) {
    add(
      "register_identity_mismatch",
      `milestone=${register?.milestone} authoritative=${register?.authoritative}`,
    );
  }
  if (register?.registry_requirement !== REGISTRY_REQUIREMENT) {
    add("register_identity_mismatch", `registry_requirement=${register?.registry_requirement}`);
  }
  if (rows.length !== DECLARED_EVID_IDS.length) {
    add("row_count_mismatch", `rows=${rows.length}`);
  }

  // (2) EVID id set: exactly the declared five, each once.
  const ids = rows.map((row) => row?.evid_id);
  const idSet = new Set(ids);
  if (idSet.size !== ids.length) {
    for (const id of ids) {
      if (ids.filter((candidate) => candidate === id).length > 1) add("evid_id_duplicated", String(id));
    }
  }
  for (const id of DECLARED_EVID_IDS) {
    if (!idSet.has(id)) add("evid_id_missing", id);
  }
  for (const id of idSet) {
    if (!DECLARED_EVID_IDS.includes(id)) add("evid_id_unknown", String(id));
  }

  for (const row of rows) {
    const id = row?.evid_id ?? "?";

    // (3) active anchors: repo-relative, existing, outside the archive.
    for (const anchor of row?.active_anchors ?? []) {
      const anchorPath = anchor?.path;
      if (!nonEmpty(anchorPath)) {
        add("anchor_missing", `${id}: empty anchor`);
        continue;
      }
      if (anchorPath.startsWith("/")) {
        add("anchor_absolute", `${id}:${anchorPath}`);
        continue;
      }
      if (anchorPath.split("/").includes("..")) {
        add("anchor_escaping", `${id}:${anchorPath}`);
        continue;
      }
      if (IGNORED_SOURCE_PREFIXES.some((prefix) => anchorPath.startsWith(prefix))) {
        add("anchor_ignored", `${id}:${anchorPath}`);
        continue;
      }
      if (anchorPath.startsWith(ARCHIVE_PREFIX)) {
        add("archive_as_active_anchor", `${id}:${anchorPath}`);
        continue;
      }
      if (!fileExists(anchorPath)) {
        add("active_anchor_disk_missing", `${id}:${anchorPath}`);
      }
    }

    // (4) archived Python anchors stay prior_art and are never promoted.
    for (const prior of row?.prior_art ?? []) {
      const priorPath = prior?.path;
      if (!nonEmpty(priorPath) || !priorPath.startsWith(ARCHIVE_PREFIX)) {
        add("prior_art_not_archived", `${id}:${priorPath ?? "absent"}`);
        continue;
      }
      if (!fileExists(priorPath)) {
        add("prior_art_disk_missing", `${id}:${priorPath}`);
      }
    }
    const promoted = new Set(activeAnchorPaths(row));
    for (const anchor of row?.python_era_anchors ?? []) {
      if (promoted.has(anchor)) add("python_era_anchor_promoted", `${id}:${anchor}`);
    }

    // (5) every declared row is closed as bounded evidence.
    if (row?.status === "bounded-evidence") {
      if (!nonEmpty(row?.proof_level) || !nonEmpty(row?.proof_command)) {
        add(
          "closed_row_metadata_missing",
          `${id}: status=${row?.status} proof_level=${row?.proof_level} command=${row?.proof_command}`,
        );
      }
    } else {
      add("pending_row_present", `${id}:${row?.status}`);
    }
    if (!Array.isArray(row?.non_claims) || row.non_claims.length === 0) {
      add("closed_row_non_claims_missing", id);
    }
  }

  // (6) benchmark rows cite the tracked S04 metrics artifacts and command.
  const qualityRow = byId(register, QUALITY_EVID_ID);
  const runtimeRow = byId(register, RUNTIME_EVID_ID);
  const benchmarkRows = [
    ["quality", qualityRow, "slice-quality"],
    ["runtime", runtimeRow, "slice-runtime"],
  ];
  for (const [label, row, level] of benchmarkRows) {
    const anchors = activeAnchorPaths(row);
    for (const required of BENCHMARK_ANCHORS) {
      if (!anchors.includes(required)) add("benchmark_anchor_missing", `${label}:${required}`);
    }
    if (row?.proof_level !== level) {
      add("benchmark_proof_level_wrong", `${label}:${row?.proof_level}`);
    }
    if (!nonEmpty(row?.proof_command) || !String(row.proof_command).includes(BENCHMARK_PROOF_COMMAND)) {
      add("benchmark_command_missing", `${label}:${row?.proof_command}`);
    }
  }

  // (6b) quality metrics present, all at the 1.0 threshold, mismatch-free.
  const qualityMetrics = qualityRow?.quality_metrics;
  if (qualityMetrics == null || typeof qualityMetrics !== "object") {
    add("quality_metrics_missing", "quality_metrics absent");
  } else {
    for (const key of QUALITY_METRIC_KEYS) {
      if (qualityMetrics[key] !== 1) add("quality_metrics_missing", `${key}=${qualityMetrics[key]}`);
    }
    if (qualityMetrics.mismatch_count !== 0) {
      add("quality_metrics_missing", `mismatch_count=${qualityMetrics.mismatch_count}`);
    }
    if (qualityMetrics.threshold_breaches !== 0) {
      add("quality_metrics_missing", `threshold_breaches=${qualityMetrics.threshold_breaches}`);
    }
    if (!(qualityMetrics.total_cases > 0)) {
      add("quality_metrics_missing", `total_cases=${qualityMetrics.total_cases}`);
    }
  }

  // (6c) structural runtime profile present; host-boundary timing unasserted.
  const profile = runtimeRow?.runtime_profile;
  if (profile == null || typeof profile !== "object") {
    add("runtime_profile_missing", "runtime_profile absent");
  } else {
    for (const key of RUNTIME_PROFILE_KEYS) {
      if (!(Number.isInteger(profile[key]) && profile[key] > 0)) {
        add("runtime_profile_missing", `${key}=${profile[key]}`);
      }
    }
  }
  const timing = runtimeRow?.observed_timing;
  if (timing == null || timing.reproducible !== false || timing.asserted !== false) {
    add("host_boundary_timing_asserted", JSON.stringify(timing));
  }

  // (7) the real-artifact row cites the pinned sha256 and its proof command.
  const realRow = byId(register, REAL_ARTIFACT_EVID_ID);
  if (
    realRow?.pinned_document?.sha256 !== PINNED_SHA256 ||
    realRow?.pinned_document?.bytes !== PINNED_BYTES
  ) {
    add(
      "real_artifact_pin_missing",
      `sha256=${realRow?.pinned_document?.sha256} bytes=${realRow?.pinned_document?.bytes}`,
    );
  }
  if (
    !nonEmpty(realRow?.proof_command) ||
    !String(realRow.proof_command).includes(REAL_PROOF_COMMAND) ||
    !registerText.includes(PINNED_SHA256) ||
    !registerText.includes(REAL_PROOF_COMMAND)
  ) {
    add("real_artifact_command_missing", `command=${realRow?.proof_command}`);
  }

  // (8) D537 consistency block.
  const d537 = register?.d537_consistency;
  if (d537 == null || typeof d537 !== "object") {
    add("d537_block_missing", "d537_consistency absent");
  } else {
    if (
      d537.decision !== "D537" ||
      d537.written_or_regenerated !== false ||
      d537.retarget_deferred_to !== "RC28-F19" ||
      !nonEmpty(d537.statement)
    ) {
      add(
        "d537_block_inconsistent",
        `decision=${d537.decision} written_or_regenerated=${d537.written_or_regenerated} deferred_to=${d537.retarget_deferred_to}`,
      );
    }
  }

  // (9) S04 closure record.
  const closure = register?.s04_closure;
  if (closure == null || typeof closure !== "object") {
    add("s04_closure_missing", "s04_closure absent");
  } else {
    const closedIds = Array.isArray(closure.closed_evid_ids) ? closure.closed_evid_ids : [];
    if (
      closure.slice !== "S04" ||
      closure.closed_rows !== DECLARED_EVID_IDS.length ||
      closure.pending_rows !== 0 ||
      !nonEmpty(closure.date) ||
      !sameSet(closedIds, DECLARED_EVID_IDS)
    ) {
      add(
        "s04_closure_inconsistent",
        `slice=${closure.slice} closed_rows=${closure.closed_rows} pending_rows=${closure.pending_rows} closed_ids=${closedIds.length}`,
      );
    }
  }

  // (10) register-level non-claims.
  if (!Array.isArray(register?.non_claims) || register.non_claims.length === 0) {
    add("register_non_claims_missing", "register");
  }

  return { ok: errors.length === 0, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const liveRegisterText = readRepo(REGISTER);
const liveRegister = JSON.parse(liveRegisterText);

function cloneRegister() {
  return JSON.parse(liveRegisterText);
}

function fixture(mutate) {
  const next = cloneRegister();
  const returned = mutate(next) ?? next;
  assert.notEqual(
    JSON.stringify(returned),
    JSON.stringify(liveRegister),
    "fixture mutation did not modify the register",
  );
  return returned;
}

function expectCode(result, expected) {
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
}

// ---------------------------------------------------------------------------
// live contract
// ---------------------------------------------------------------------------

test("M216 S04 retrieval EVID register validates against its closure contract", () => {
  const result = validateRegister(liveRegister);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors, null, 2)}`);
  assert.equal(result.ok, true);
});

test("the register maps exactly the five declared retrieval EVID ids", () => {
  assert.ok(sameSet(liveRegister.rows.map((row) => row.evid_id), DECLARED_EVID_IDS));
  assert.equal(liveRegister.rows.length, DECLARED_EVID_IDS.length);
});

test("every active anchor exists on disk and none is under prd/archive/", () => {
  for (const row of liveRegister.rows) {
    for (const anchor of row.active_anchors) {
      assert.ok(!anchor.path.startsWith("/"), `${row.evid_id}: ${anchor.path} must be repo-relative`);
      assert.ok(!anchor.path.split("/").includes(".."), `${row.evid_id}: ${anchor.path} must not escape`);
      assert.ok(!anchor.path.startsWith(ARCHIVE_PREFIX), `${row.evid_id}: ${anchor.path} must not be archived`);
      assert.ok(repoExists(anchor.path), `${row.evid_id}: ${anchor.path} must exist`);
    }
  }
});

test("all five rows are closed as bounded evidence with non-claims", () => {
  for (const row of liveRegister.rows) {
    assert.equal(row.status, "bounded-evidence", `${row.evid_id} must be bounded-evidence`);
    assert.ok(nonEmpty(row.proof_level), `${row.evid_id} must declare a proof_level`);
    assert.ok(nonEmpty(row.proof_command), `${row.evid_id} must declare a proof_command`);
    assert.ok(Array.isArray(row.non_claims) && row.non_claims.length > 0, `${row.evid_id} must declare non-claims`);
  }
});

test("the two benchmark rows cite the S04 metrics artifacts and proof command", () => {
  for (const [id, level] of [
    [QUALITY_EVID_ID, "slice-quality"],
    [RUNTIME_EVID_ID, "slice-runtime"],
  ]) {
    const row = byId(liveRegister, id);
    assert.equal(row.proof_level, level, `${id} must be ${level}`);
    assert.ok(row.proof_command.includes(BENCHMARK_PROOF_COMMAND), `${id} must cite the metrics proof command`);
    for (const required of BENCHMARK_ANCHORS) {
      assert.ok(
        row.active_anchors.some((anchor) => anchor.path === required),
        `${id} must cite active anchor ${required}`,
      );
    }
  }
  const quality = byId(liveRegister, QUALITY_EVID_ID);
  for (const key of QUALITY_METRIC_KEYS) {
    assert.equal(quality.quality_metrics[key], 1, `${key} must meet the 1.0 threshold`);
  }
  assert.equal(quality.quality_metrics.mismatch_count, 0);
  assert.equal(quality.quality_metrics.threshold_breaches, 0);
  const runtime = byId(liveRegister, RUNTIME_EVID_ID);
  for (const key of RUNTIME_PROFILE_KEYS) {
    assert.ok(Number.isInteger(runtime.runtime_profile[key]) && runtime.runtime_profile[key] > 0, `${key} must be a positive counter`);
  }
  assert.equal(runtime.observed_timing.reproducible, false);
  assert.equal(runtime.observed_timing.asserted, false);
});

test("the S04 closure record matches the closed rows", () => {
  assert.equal(liveRegister.s04_closure.slice, "S04");
  assert.equal(liveRegister.s04_closure.closed_rows, DECLARED_EVID_IDS.length);
  assert.equal(liveRegister.s04_closure.pending_rows, 0);
  assert.ok(sameSet(liveRegister.s04_closure.closed_evid_ids, DECLARED_EVID_IDS));
  for (const id of DECLARED_EVID_IDS) {
    assert.equal(byId(liveRegister, id).status, "bounded-evidence", `${id} must be closed`);
  }
});

test("the D537 consistency block is present and fail-closed", () => {
  assert.equal(liveRegister.d537_consistency.decision, "D537");
  assert.equal(liveRegister.d537_consistency.written_or_regenerated, false);
  assert.equal(liveRegister.d537_consistency.retarget_deferred_to, "RC28-F19");
  assert.ok(liveRegister.d537_consistency.frozen_registry_inputs.includes("prd/architecture/architecture_items.jsonl"));
  assert.ok(liveRegister.d537_consistency.frozen_registry_inputs.includes("prd/architecture/architecture_edges.jsonl"));
});

test("the real-artifact row still cites the pinned document and its proof command", () => {
  const row = byId(liveRegister, REAL_ARTIFACT_EVID_ID);
  assert.equal(row.pinned_document.sha256, PINNED_SHA256);
  assert.equal(row.pinned_document.bytes, PINNED_BYTES);
  assert.ok(row.proof_command.includes(REAL_PROOF_COMMAND));
  assert.ok(liveRegisterText.includes(PINNED_SHA256));
  assert.ok(liveRegisterText.includes(REAL_PROOF_COMMAND));
  assert.equal(row.proof_counts.mismatch_count, 0);
});

// ---------------------------------------------------------------------------
// contract self-guards
// ---------------------------------------------------------------------------

test("the contract never reads an ignored, .gsd or absolute path as evidence", () => {
  const source = readRepo(CONTRACT_PATH);
  const declared = [...source.matchAll(/^const\s+[A-Za-z_$][\w$]*\s*=\s*"([^"]+)";$/gm)].map(
    (match) => match[1],
  );
  for (const value of declared) {
    assert.ok(!value.startsWith("/"), `absolute path literal ${value} is not admissible evidence`);
    for (const prefix of IGNORED_SOURCE_PREFIXES) {
      assert.ok(!value.startsWith(prefix), `ignored path literal ${value} is not admissible evidence`);
    }
  }
  assert.ok(!/readRepo\(\s*"\.gsd\//.test(source), "the contract must not read .gsd");
  assert.ok(!/readRepo\(\s*"\//.test(source), "the contract must not read an absolute path");
});

// ---------------------------------------------------------------------------
// negative tests (every documented fail-closed code is exercised)
// ---------------------------------------------------------------------------

test("negative: register identity and row-count drift", () => {
  expectCode(validateRegister(fixture((r) => { r.schema_version = "law-nexus/other/v9"; })), "schema_version_mismatch");
  expectCode(validateRegister(fixture((r) => { r.kind = "other"; })), "register_kind_mismatch");
  expectCode(validateRegister(fixture((r) => { r.authoritative = true; })), "register_identity_mismatch");
  expectCode(validateRegister(fixture((r) => { r.registry_requirement = "R000"; })), "register_identity_mismatch");
  expectCode(validateRegister(fixture((r) => { r.rows.pop(); })), "row_count_mismatch");
});

test("negative: EVID id set drift", () => {
  expectCode(validateRegister(fixture((r) => { r.rows.splice(0, 1); })), "evid_id_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[1].evid_id = r.rows[0].evid_id; })), "evid_id_duplicated");
  expectCode(validateRegister(fixture((r) => { r.rows[0].evid_id = "EVID-UNKNOWN"; })), "evid_id_unknown");
});

test("negative: active anchor path drift", () => {
  expectCode(validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = ""; })), "anchor_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = "/tmp/x.rs"; })), "anchor_absolute");
  expectCode(validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = "../x.rs"; })), "anchor_escaping");
  expectCode(validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = ".gsd/x.rs"; })), "anchor_ignored");
  expectCode(
    validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = "prd/archive/retrieval-era/offline_citation_retrieval_proof.md"; })),
    "archive_as_active_anchor",
  );
  expectCode(
    validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = "crates/no-such-file.rs"; })),
    "active_anchor_disk_missing",
  );
});

test("negative: closed and pending row contract drift", () => {
  expectCode(validateRegister(fixture((r) => { r.rows[0].proof_level = ""; })), "closed_row_metadata_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[0].proof_command = ""; })), "closed_row_metadata_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[0].non_claims = []; })), "closed_row_non_claims_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[3].status = "pending-s04"; })), "pending_row_present");
});

test("negative: benchmark artifact and metrics drift", () => {
  expectCode(
    validateRegister(fixture((r) => { r.rows[3].active_anchors = r.rows[3].active_anchors.slice(0, 3); })),
    "benchmark_anchor_missing",
  );
  expectCode(validateRegister(fixture((r) => { r.rows[3].proof_level = "unit-integration"; })), "benchmark_proof_level_wrong");
  expectCode(validateRegister(fixture((r) => { r.rows[4].proof_command = "echo nope"; })), "benchmark_command_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[3].quality_metrics.mismatch_count = 1; })), "quality_metrics_missing");
  expectCode(
    validateRegister(fixture((r) => { r.rows[3].quality_metrics.selection_accuracy = 0.5; })),
    "quality_metrics_missing",
  );
  expectCode(validateRegister(fixture((r) => { delete r.rows[4].runtime_profile.projected_segments; })), "runtime_profile_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[4].observed_timing.reproducible = true; })), "host_boundary_timing_asserted");
});

test("negative: real-artifact pin and command drift", () => {
  expectCode(
    validateRegister(fixture((r) => { byId(r, REAL_ARTIFACT_EVID_ID).pinned_document.sha256 = "deadbeef"; })),
    "real_artifact_pin_missing",
  );
  expectCode(
    validateRegister(fixture((r) => { byId(r, REAL_ARTIFACT_EVID_ID).proof_command = "echo nope"; })),
    "real_artifact_command_missing",
  );
});

test("negative: D537 block, prior-art and closure drift", () => {
  expectCode(validateRegister(fixture((r) => { delete r.d537_consistency; })), "d537_block_missing");
  expectCode(validateRegister(fixture((r) => { r.d537_consistency.written_or_regenerated = true; })), "d537_block_inconsistent");
  expectCode(validateRegister(fixture((r) => { r.rows[0].prior_art[0].path = "prd/retrieval/x.md"; })), "prior_art_not_archived");
  expectCode(validateRegister(fixture((r) => { r.rows[0].prior_art[0].path = "prd/archive/no-such.md"; })), "prior_art_disk_missing");
  expectCode(
    validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = r.rows[0].python_era_anchors[0]; })),
    "python_era_anchor_promoted",
  );
  expectCode(validateRegister(fixture((r) => { delete r.s04_closure; })), "s04_closure_missing");
  expectCode(validateRegister(fixture((r) => { r.s04_closure.closed_rows = 4; })), "s04_closure_inconsistent");
  expectCode(validateRegister(fixture((r) => { r.non_claims = []; })), "register_non_claims_missing");
});

// ---------------------------------------------------------------------------
// code-coverage registry: every documented code must have a firing mutation
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  { code: "schema_version_mismatch", mutate: (r) => { r.schema_version = "law-nexus/other/v9"; } },
  { code: "register_kind_mismatch", mutate: (r) => { r.kind = "other"; } },
  { code: "register_identity_mismatch", mutate: (r) => { r.authoritative = true; } },
  { code: "row_count_mismatch", mutate: (r) => { r.rows.pop(); } },
  { code: "evid_id_missing", mutate: (r) => { r.rows.splice(0, 1); } },
  { code: "evid_id_duplicated", mutate: (r) => { r.rows[1].evid_id = r.rows[0].evid_id; } },
  { code: "evid_id_unknown", mutate: (r) => { r.rows[0].evid_id = "EVID-UNKNOWN"; } },
  { code: "anchor_missing", mutate: (r) => { r.rows[0].active_anchors[0].path = ""; } },
  { code: "anchor_absolute", mutate: (r) => { r.rows[0].active_anchors[0].path = "/tmp/x.rs"; } },
  { code: "anchor_escaping", mutate: (r) => { r.rows[0].active_anchors[0].path = "../x.rs"; } },
  { code: "anchor_ignored", mutate: (r) => { r.rows[0].active_anchors[0].path = ".gsd/x.rs"; } },
  { code: "archive_as_active_anchor", mutate: (r) => { r.rows[0].active_anchors[0].path = "prd/archive/retrieval-era/offline_citation_retrieval_proof.md"; } },
  { code: "active_anchor_disk_missing", mutate: (r) => { r.rows[0].active_anchors[0].path = "crates/no-such-file.rs"; } },
  { code: "closed_row_metadata_missing", mutate: (r) => { r.rows[0].proof_level = ""; } },
  { code: "closed_row_non_claims_missing", mutate: (r) => { r.rows[0].non_claims = []; } },
  { code: "pending_row_present", mutate: (r) => { r.rows[3].status = "pending-s04"; } },
  { code: "benchmark_anchor_missing", mutate: (r) => { r.rows[3].active_anchors = r.rows[3].active_anchors.slice(0, 3); } },
  { code: "benchmark_proof_level_wrong", mutate: (r) => { r.rows[3].proof_level = "unit-integration"; } },
  { code: "benchmark_command_missing", mutate: (r) => { r.rows[4].proof_command = "echo nope"; } },
  { code: "quality_metrics_missing", mutate: (r) => { r.rows[3].quality_metrics.mismatch_count = 1; } },
  { code: "runtime_profile_missing", mutate: (r) => { delete r.rows[4].runtime_profile.projected_segments; } },
  { code: "host_boundary_timing_asserted", mutate: (r) => { r.rows[4].observed_timing.reproducible = true; } },
  { code: "real_artifact_pin_missing", mutate: (r) => { byId(r, REAL_ARTIFACT_EVID_ID).pinned_document.sha256 = "deadbeef"; } },
  { code: "real_artifact_command_missing", mutate: (r) => { byId(r, REAL_ARTIFACT_EVID_ID).proof_command = "echo nope"; } },
  { code: "d537_block_missing", mutate: (r) => { delete r.d537_consistency; } },
  { code: "d537_block_inconsistent", mutate: (r) => { r.d537_consistency.written_or_regenerated = true; } },
  { code: "prior_art_not_archived", mutate: (r) => { r.rows[0].prior_art[0].path = "prd/retrieval/x.md"; } },
  { code: "prior_art_disk_missing", mutate: (r) => { r.rows[0].prior_art[0].path = "prd/archive/no-such.md"; } },
  { code: "python_era_anchor_promoted", mutate: (r) => { r.rows[0].active_anchors[0].path = r.rows[0].python_era_anchors[0]; } },
  { code: "s04_closure_missing", mutate: (r) => { delete r.s04_closure; } },
  { code: "s04_closure_inconsistent", mutate: (r) => { r.s04_closure.closed_rows = 4; } },
  { code: "register_non_claims_missing", mutate: (r) => { r.non_claims = []; } },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const result = validateRegister(fixture(entry.mutate));
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    assert.equal(result.ok, false, `${entry.code} must make the register fail closed`);
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

test("the documented code block equals the emittable code set", () => {
  const source = readRepo(CONTRACT_PATH);
  const block = source.match(/\/\/ DOCUMENTED_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_CODES_END/);
  assert.ok(block, "the documented codes block must exist");
  const documented = block[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documented.sort(), [...EMITTABLE_CODES].sort());
});

// ---------------------------------------------------------------------------
// markers (emitted only after the register contract holds)
// ---------------------------------------------------------------------------

test("M216 S04 retrieval EVID register markers", () => {
  const result = validateRegister(liveRegister);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors)}`);
  const closedRows = liveRegister.rows.filter((row) => row.status === "bounded-evidence").length;
  const pendingRows = liveRegister.rows.filter((row) => row.status !== "bounded-evidence").length;
  assert.equal(closedRows, 5);
  assert.equal(pendingRows, 0);
  console.log("M216_S04_METRICS_REGISTER_OK");
  console.log(`register_rows=${liveRegister.rows.length}`);
  console.log(`closed_rows=${closedRows}`);
  console.log(`pending_rows=${pendingRows}`);
});
