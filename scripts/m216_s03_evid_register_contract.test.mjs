// M216/S03 retrieval EVID retarget register contract (T03).
//
// Offline and fail-closed: the live register must parse and map exactly the
// five declared retrieval evidence rows, every ACTIVE anchor must resolve to a
// tracked, repo-relative path outside prd/archive/, every closed row must carry
// status + proof_level + non-empty non-claims, the real-artifact row must cite
// the pinned document sha256 and the proof command, and the D537 consistency
// block must be present. S04 closed the two benchmark rows in this same
// standalone register; the S03-era `pending-s04` premise is retired here and now
// owned by scripts/m216_s04_metrics_register_contract.test.mjs.
//
// No subprocess, no network, no cargo: this contract reads the register and the
// declared anchor paths from disk only, and never reads a `.gsd` / ignored /
// absolute path as evidence. Every documented fail-closed code is exercised by
// a mutation so the suite cannot assert a code it would never actually emit.
//
// Run: node --test scripts/m216_s03_evid_register_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const REGISTER = "prd/migration/rust-evidence/m216-retrieval-evid-register.json";
const CONTRACT_PATH = "scripts/m216_s03_evid_register_contract.test.mjs";

const REGISTER_SCHEMA_VERSION = "law-nexus-m216-retrieval-evid-register/v1";
const REGISTER_KIND = "m216-retrieval-evid-register";
const MILESTONE = "M216-8dps6e";
const SLICE = "S03";
const REGISTRY_REQUIREMENT = "R034";

const PINNED_DOC =
  "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
const PINNED_SHA256 = "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d";
const PINNED_BYTES = 193726;
const PROOF_COMMAND = "cargo test -p ln-query --offline --test real_artifact_retrieval -- --nocapture";

const DECLARED_EVID_IDS = [
  "EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF",
  "EVID-OFFLINE-CITATION-RETRIEVAL-PROOF",
  "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF",
  "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF",
  "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF",
];

// S04 closed the two benchmark rows in the same standalone register (see
// scripts/m216_s04_metrics_register_contract.test.mjs); all five rows are now
// bounded evidence.
const CLOSED_EVID_IDS = [
  "EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF",
  "EVID-OFFLINE-CITATION-RETRIEVAL-PROOF",
  "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF",
  "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF",
  "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF",
];

const REAL_ARTIFACT_EVID_ID = "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF";

const ARCHIVE_PREFIX = "prd/archive/";
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// DOCUMENTED_CODES_BEGIN
// schema_version_mismatch: the register schema_version is not the declared one.
// register_kind_mismatch: the register kind is not the declared one.
// register_identity_mismatch: milestone/slice/authoritative drift.
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
// closed_row_metadata_missing: a closed row lacks status/proof_level/command.
// closed_row_non_claims_missing: a closed row has no non-claims.
// real_artifact_pin_missing: the real-artifact row does not cite the pin.
// real_artifact_command_missing: the real-artifact row does not cite the command.
// d537_block_missing: the D537 consistency block is absent.
// d537_block_inconsistent: the D537 consistency block is not fail-closed.
// prior_art_not_archived: a prior_art entry is not under prd/archive/.
// prior_art_disk_missing: a prior_art path does not exist on disk.
// python_era_anchor_promoted: an archived Python anchor is used as an active anchor.
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
  "real_artifact_pin_missing",
  "real_artifact_command_missing",
  "d537_block_missing",
  "d537_block_inconsistent",
  "prior_art_not_archived",
  "prior_art_disk_missing",
  "python_era_anchor_promoted",
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
  if (
    register?.milestone !== MILESTONE ||
    register?.slice !== SLICE ||
    register?.authoritative !== false
  ) {
    add(
      "register_identity_mismatch",
      `milestone=${register?.milestone} slice=${register?.slice} authoritative=${register?.authoritative}`,
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
    if (row?.status !== "bounded-evidence" || !nonEmpty(row?.proof_level) || !nonEmpty(row?.proof_command)) {
      add(
        "closed_row_metadata_missing",
        `${id}: status=${row?.status} proof_level=${row?.proof_level} command=${row?.proof_command}`,
      );
    }
    if (!Array.isArray(row?.non_claims) || row.non_claims.length === 0) {
      add("closed_row_non_claims_missing", id);
    }
  }

  // (6) the real-artifact row cites the pinned sha256 and the proof command.
  const realRow = byId(register, REAL_ARTIFACT_EVID_ID);
  if (realRow?.pinned_document?.sha256 !== PINNED_SHA256 || realRow?.pinned_document?.bytes !== PINNED_BYTES) {
    add(
      "real_artifact_pin_missing",
      `sha256=${realRow?.pinned_document?.sha256} bytes=${realRow?.pinned_document?.bytes}`,
    );
  }
  if (
    !nonEmpty(realRow?.proof_command) ||
    !String(realRow.proof_command).includes(PROOF_COMMAND) ||
    !registerText.includes(PINNED_SHA256) ||
    !registerText.includes(PROOF_COMMAND)
  ) {
    add("real_artifact_command_missing", `command=${realRow?.proof_command}`);
  }

  // (7) D537 consistency block.
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

  // (8) register-level non-claims.
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

test("M216 S03 retrieval EVID register validates against its contract", () => {
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

test("all five rows carry bounded metadata and non-claims", () => {
  for (const id of CLOSED_EVID_IDS) {
    const row = byId(liveRegister, id);
    assert.equal(row.status, "bounded-evidence", `${id} must be bounded-evidence`);
    assert.ok(nonEmpty(row.proof_level), `${id} must declare a proof_level`);
    assert.ok(Array.isArray(row.non_claims) && row.non_claims.length > 0, `${id} must declare non-claims`);
  }
});

test("the real-artifact row cites the pinned document and the proof command", () => {
  const row = byId(liveRegister, REAL_ARTIFACT_EVID_ID);
  assert.equal(row.pinned_document.sha256, PINNED_SHA256);
  assert.equal(row.pinned_document.bytes, PINNED_BYTES);
  assert.equal(row.pinned_document.path, PINNED_DOC);
  assert.ok(row.proof_command.includes(PROOF_COMMAND));
  assert.ok(liveRegisterText.includes(PINNED_SHA256));
  assert.ok(liveRegisterText.includes(PROOF_COMMAND));
  // The proof counts recorded here are the T02 bounded summary.
  assert.equal(row.proof_counts.mismatch_count, 0);
  assert.equal(row.proof_counts.total, 8);
});

test("the D537 consistency block is present and fail-closed", () => {
  assert.equal(liveRegister.d537_consistency.decision, "D537");
  assert.equal(liveRegister.d537_consistency.written_or_regenerated, false);
  assert.equal(liveRegister.d537_consistency.retarget_deferred_to, "RC28-F19");
  assert.ok(liveRegister.d537_consistency.frozen_registry_inputs.includes("prd/architecture/architecture_items.jsonl"));
  assert.ok(liveRegister.d537_consistency.frozen_registry_inputs.includes("prd/architecture/architecture_edges.jsonl"));
});

test("the two benchmark rows are closed by S04 with archived prior art retained", () => {
  for (const id of [
    "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF",
    "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF",
  ]) {
    const row = byId(liveRegister, id);
    assert.equal(row.status, "bounded-evidence", `${id} must be closed by S04`);
    assert.ok(row.active_anchors.length > 0, `${id} must claim a tracked active anchor`);
    assert.ok(Array.isArray(row.prior_art) && row.prior_art.length > 0, `${id} keeps prior art`);
    for (const prior of row.prior_art) {
      assert.ok(prior.path.startsWith(ARCHIVE_PREFIX), `${id}: ${prior.path} must be archived prior art`);
    }
  }
  assert.equal(liveRegister.s04_closure.closed_rows, 5);
  assert.equal(liveRegister.s04_closure.pending_rows, 0);
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

test("negative: closed row contract drift", () => {
  expectCode(validateRegister(fixture((r) => { r.rows[0].status = "pending-s04"; })), "closed_row_metadata_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[0].proof_level = ""; })), "closed_row_metadata_missing");
  expectCode(validateRegister(fixture((r) => { r.rows[0].non_claims = []; })), "closed_row_non_claims_missing");
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

test("negative: D537 block and prior-art drift", () => {
  expectCode(validateRegister(fixture((r) => { delete r.d537_consistency; })), "d537_block_missing");
  expectCode(validateRegister(fixture((r) => { r.d537_consistency.written_or_regenerated = true; })), "d537_block_inconsistent");
  expectCode(validateRegister(fixture((r) => { r.rows[0].prior_art[0].path = "prd/retrieval/x.md"; })), "prior_art_not_archived");
  expectCode(validateRegister(fixture((r) => { r.rows[0].prior_art[0].path = "prd/archive/no-such.md"; })), "prior_art_disk_missing");
  expectCode(
    validateRegister(fixture((r) => { r.rows[0].active_anchors[0].path = r.rows[0].python_era_anchors[0]; })),
    "python_era_anchor_promoted",
  );
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
  { code: "closed_row_metadata_missing", mutate: (r) => { r.rows[0].status = "pending-s04"; } },
  { code: "closed_row_non_claims_missing", mutate: (r) => { r.rows[0].non_claims = []; } },
  { code: "real_artifact_pin_missing", mutate: (r) => { byId(r, REAL_ARTIFACT_EVID_ID).pinned_document.sha256 = "deadbeef"; } },
  { code: "real_artifact_command_missing", mutate: (r) => { byId(r, REAL_ARTIFACT_EVID_ID).proof_command = "echo nope"; } },
  { code: "d537_block_missing", mutate: (r) => { delete r.d537_consistency; } },
  { code: "d537_block_inconsistent", mutate: (r) => { r.d537_consistency.written_or_regenerated = true; } },
  { code: "prior_art_not_archived", mutate: (r) => { r.rows[0].prior_art[0].path = "prd/retrieval/x.md"; } },
  { code: "prior_art_disk_missing", mutate: (r) => { r.rows[0].prior_art[0].path = "prd/archive/no-such.md"; } },
  { code: "python_era_anchor_promoted", mutate: (r) => { r.rows[0].active_anchors[0].path = r.rows[0].python_era_anchors[0]; } },
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

test("M216 S03 retrieval EVID register markers", () => {
  const result = validateRegister(liveRegister);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors)}`);
  console.log("M216_S03_EVID_REGISTER_OK");
  console.log(`register_rows=${liveRegister.rows.length}`);
  console.log("M216_S03_EVID_IDS_OK");
  console.log(`closed_rows=${CLOSED_EVID_IDS.length}`);
  console.log("pending_rows=0");
});
