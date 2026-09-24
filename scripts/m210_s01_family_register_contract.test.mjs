// M210/S01 normative family register contract (T01).
//
// Offline and fail-closed. The subject is a *closed dictionary*, not an
// adoption: `prd/architecture/m210-s01-normative-family-register.json` must
// carry exactly the eight RC28-F18 normative families, each bound to a tracked
// owning source whose sha256 is re-derived live, each capped at the vocabulary
// status its owning source actually grants, with a fail-closed boundary, an
// evidence class and non_adoption=true; plus the two negative distinctions
// RC28-F18 names, and the M209 source-side family axis marked explicitly as not
// an IR family.
//
// The register is canonical compact ASCII JSON with a fixed key order and no
// timestamp, so `JSON.stringify(JSON.parse(text)) === text` and the contract
// never has to guess a formatting convention.
//
// Every documented fail-closed code is provable against a mutated copy of the
// live register (or its markdown companion), so the suite cannot assert a code
// it would never emit. Subprocesses are limited to `git ls-files --error-unmatch`
// (tracked-file proof) and `git status --porcelain` (frozen-input proof). No
// cargo, no network, no `.gsd` / ignored / absolute path is read as evidence.
//
// Run: node --test scripts/m210_s01_family_register_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const REGISTER = "prd/architecture/m210-s01-normative-family-register.json";
const COMPANION = "prd/architecture/m210-s01-normative-family-register.md";
const CONTRACT_PATH = "scripts/m210_s01_family_register_contract.test.mjs";

const SCHEMA = "law-nexus/m210-normative-family-register/v1";
const KIND = "m210-s01-normative-family-register";
const MILESTONE = "M210-3afp79";
const SLICE = "S01";
const TASK = "T01";
const LIFECYCLE = "[proposed]";

// The closed family set RC28-F18 requires be separated.
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

// The closed vocabulary-status dictionary, ordered weakest to strongest.
const VOCABULARY_STATUS = ["no_owning_row", "deferred-undefined", "proposed", "bounded"];
const STATUS_RANK = Object.fromEntries(VOCABULARY_STATUS.map((status, index) => [status, index]));

// The ceiling each family's owning source actually grants. `no_owning_row` means
// section 3 carries no row for the family at all; the honest status is the gap.
const STATUS_CEILING = {
  obligation: "deferred-undefined",
  permission: "deferred-undefined",
  prohibition: "deferred-undefined",
  definition: "no_owning_row",
  competence: "proposed",
  condition: "deferred-undefined",
  exception: "deferred-undefined",
  temporal_qualification: "proposed",
};

const EVIDENCE_CLASSES = ["inert-artifact", "source-bound-span", "runtime-absent"];
const OWNING_SOURCE_KINDS = ["review_requirement", "term_row", "gap_row", "no_owning_row"];

const EXPECTED_DISTINCTIONS = [
  "absence_of_obligation_is_not_prohibition",
  "lack_of_evidence_is_not_falsity",
];
const EXPECTED_DISTINCTION_CODES = {
  absence_of_obligation_is_not_prohibition: "absence_of_obligation_conflated_with_prohibition",
  lack_of_evidence_is_not_falsity: "lack_of_evidence_conflated_with_falsity",
};

// The M209 source-side denominator axis. These are corpus families, never IR
// families.
const M209_SOURCE_FAMILIES = [
  "manifest_layer1_44fz_and_amending_laws",
  "manifest_layer2_subordinate_normative_acts",
  "manifest_layer3_court_practice_2025_2026",
  "manifest_layer3_fas_practice_2025_2026",
  "exports_npa",
  "exports_xml",
  "exports_courts",
  "exports_fas",
];
const NOT_IR_FRAGMENT = "not an IR family";

// The five frozen inputs the register is derived from.
const EXPECTED_BINDINGS = [
  "prd/temporal-legal-model.md",
  "prd/architecture/temporal-semantic-gap-register.md",
  "doc/review/review-28-10-09-2026.md",
  "prd/architecture/kb-ontology-l1-l3-draft.md",
  "prd/migration/rust-evidence/m209-s03-family-denominator.json",
];

// Paths that can never be evidence: ignored overlays, absolute paths, traversal.
const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/"];

// The complete fail-closed code set. The register and its companion must
// document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "family_duplicated",
  "negative_distinction_missing",
  "non_claims_missing",
  "owning_source_missing",
  "runtime_claim_present",
  "source_family_as_ir_family",
  "source_hash_mismatch",
  "source_not_tracked",
  "status_promoted",
  "status_unknown",
  "unknown_family",
];

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl ", "crates/"];

const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "not an adoption of normative semantics",
  "non-authoritative",
  "no runtime surface exists",
];

const TIMESTAMP_MARKERS = [/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/, /\b1[6-9]\d{11}\b/];

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

function repoExists(relativePath) {
  return existsSync(path.join(root, relativePath));
}

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

const trackedCache = new Map();

function isTracked(relativePath) {
  if (trackedCache.has(relativePath)) return trackedCache.get(relativePath);
  let tracked = true;
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", relativePath], {
      cwd: root,
      stdio: ["ignore", "ignore", "ignore"],
    });
  } catch {
    tracked = false;
  }
  trackedCache.set(relativePath, tracked);
  return tracked;
}

const hashCache = new Map();

function sha256(relativePath) {
  if (hashCache.has(relativePath)) return hashCache.get(relativePath);
  const digest = createHash("sha256")
    .update(readFileSync(path.join(root, relativePath)))
    .digest("hex");
  hashCache.set(relativePath, digest);
  return digest;
}

// `git status --porcelain` restricted to the frozen scope: an empty result means
// none of those tracked inputs carries a worktree delta.
function worktreeDelta(paths) {
  try {
    return execFileSync("git", ["status", "--porcelain", "--", ...paths], {
      cwd: root,
      encoding: "utf8",
    }).trim();
  } catch {
    return "git status failed";
  }
}

function isForbiddenPath(relativePath) {
  if (path.isAbsolute(relativePath) || relativePath.startsWith("/")) return true;
  if (FORBIDDEN_PREFIXES.some((prefix) => relativePath.startsWith(prefix))) return true;
  return relativePath.split("/").includes("..");
}

function sortJoin(values) {
  return [...values].sort().join("\n");
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

const liveCompanion = readRepo(COMPANION);

function validateRegister(rawText, options = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ code: name, detail });
  const tracked = options.tracked || isTracked;
  const companionText = options.companionText ?? liveCompanion;

  // Parsing is fatal, not a degraded pass: a register that is not JSON is not a
  // register. Mutations keep the document parseable on purpose.
  const artifact = JSON.parse(rawText);

  // 1. families: exactly the closed eight, no duplicates.
  const families = artifact?.families;
  if (!Array.isArray(families)) {
    code("unknown_family", "families is not an array");
  } else {
    const ids = families.map((family) =>
      typeof family?.family_id === "string" ? family.family_id : "<unnamed>",
    );
    const expected = new Set(CLOSED_FAMILIES);
    const seen = new Set();
    for (const id of ids) {
      if (seen.has(id)) code("family_duplicated", id);
      seen.add(id);
      if (!expected.has(id)) code("unknown_family", `unknown family id ${id}`);
    }
    for (const id of CLOSED_FAMILIES) {
      if (!seen.has(id)) code("unknown_family", `missing family id ${id}`);
    }
    if (ids.length !== CLOSED_FAMILIES.length) {
      code("unknown_family", `family count ${ids.length}`);
    }

    // 2. per-family contract.
    for (const family of families) {
      const id = typeof family?.family_id === "string" ? family.family_id : "<unnamed>";
      if (family?.originating_requirement !== "RC28-F18") {
        code("owning_source_missing", `${id}: originating_requirement`);
      }
      if (!OWNING_SOURCE_KINDS.includes(family?.owning_source_kind)) {
        code("owning_source_missing", `${id}: owning_source_kind`);
      }
      const owning = family?.owning_source;
      if (typeof owning?.path !== "string" || owning.path.trim() === "") {
        code("owning_source_missing", `${id}: owning_source.path`);
      }
      if (typeof owning?.section !== "string" || owning.section.trim() === "") {
        code("owning_source_missing", `${id}: owning_source.section`);
      }
      if (typeof owning?.sha256 !== "string" || !/^[0-9a-f]{64}$/.test(owning.sha256)) {
        code("owning_source_missing", `${id}: owning_source.sha256`);
      }

      const status = family?.vocabulary_status;
      if (!VOCABULARY_STATUS.includes(status)) {
        code("status_unknown", `${id}: vocabulary_status ${JSON.stringify(status)}`);
      } else if (STATUS_RANK[status] > STATUS_RANK[STATUS_CEILING[id]]) {
        code("status_promoted", `${id}: ${status} above ceiling ${STATUS_CEILING[id]}`);
      }
      if (!EVIDENCE_CLASSES.includes(family?.evidence_class)) {
        code("status_unknown", `${id}: evidence_class ${JSON.stringify(family?.evidence_class)}`);
      }
      if (typeof family?.status_basis !== "string" || family.status_basis.trim() === "") {
        code("owning_source_missing", `${id}: status_basis`);
      }
      if (
        typeof family?.what_it_must_separate !== "string" ||
        family.what_it_must_separate.trim() === ""
      ) {
        code("owning_source_missing", `${id}: what_it_must_separate`);
      }
      const boundary = family?.fail_closed_boundary;
      if (typeof boundary?.unknown_outcome !== "string" || boundary.unknown_outcome.trim() === "") {
        code("owning_source_missing", `${id}: fail_closed_boundary.unknown_outcome`);
      }
      if (
        typeof boundary?.conflict_outcome !== "string" ||
        boundary.conflict_outcome.trim() === ""
      ) {
        code("owning_source_missing", `${id}: fail_closed_boundary.conflict_outcome`);
      }
      if (family?.non_adoption !== true) {
        code("owning_source_missing", `${id}: non_adoption`);
      }
      if (id === "definition" && family?.owning_source_kind !== "no_owning_row") {
        code("owning_source_missing", "definition must declare owning_source_kind no_owning_row");
      }
    }
  }

  // 3. owning sources and source bindings: tracked, existing, hash-matching.
  const bindings = [
    ...(Array.isArray(families)
      ? families.map((family) => ({
          path: family?.owning_source?.path,
          declared: family?.owning_source?.sha256,
          label: `${family?.family_id ?? "<unnamed>"} owning_source`,
        }))
      : []),
    ...(Array.isArray(artifact?.source_bindings)
      ? artifact.source_bindings.map((binding) => ({
          path: binding?.path,
          declared: binding?.sha256,
          label: `source_binding ${binding?.path}`,
        }))
      : []),
  ];
  for (const binding of bindings) {
    const relPath = binding.path;
    if (typeof relPath !== "string" || relPath.trim() === "") {
      code("owning_source_missing", `${binding.label}: path`);
      continue;
    }
    if (isForbiddenPath(relPath)) {
      code("source_not_tracked", `${relPath} is not a repository-relative path`);
      continue;
    }
    if (!repoExists(relPath)) {
      code("source_not_tracked", `${relPath} does not exist`);
      continue;
    }
    if (!tracked(relPath)) {
      code("source_not_tracked", `${relPath} is not tracked`);
      continue;
    }
    if (binding.declared !== sha256(relPath)) {
      code("source_hash_mismatch", `${relPath}: declared hash does not match the live file`);
    }
  }

  if (!Array.isArray(artifact?.source_bindings)) {
    code("owning_source_missing", "source_bindings is not an array");
  } else {
    const declaredBindings = new Set(
      artifact.source_bindings.map((binding) => binding?.path).filter((p) => typeof p === "string"),
    );
    for (const expectedPath of EXPECTED_BINDINGS) {
      if (!declaredBindings.has(expectedPath)) {
        code("owning_source_missing", `source binding missing ${expectedPath}`);
      }
    }
  }

  // 4. mandatory register declarations.
  const refs = Array.isArray(artifact?.requirement_refs) ? artifact.requirement_refs : [];
  for (const required of ["RC28-F18", "R074"]) {
    if (!refs.includes(required)) code("owning_source_missing", `requirement_refs missing ${required}`);
  }
  if (!Array.isArray(artifact?.fail_closed_codes)) {
    code("owning_source_missing", "fail_closed_codes is not an array");
  } else if (sortJoin(artifact.fail_closed_codes) !== sortJoin(EMITTABLE_CODES)) {
    code("owning_source_missing", "fail_closed_codes drift");
  }
  if (artifact?.authoritative !== false) {
    code("status_promoted", "authoritative must stay false");
  }
  if (artifact?.lifecycle !== LIFECYCLE) {
    code("status_promoted", `lifecycle must stay ${LIFECYCLE}`);
  }

  // 5. frozen inputs: a worktree delta on a pinned source invalidates the pin.
  const delta = options.frozenDelta ?? worktreeDelta(EXPECTED_BINDINGS);
  if (typeof delta === "string" && delta.trim() !== "") {
    code("source_hash_mismatch", `frozen input worktree delta: ${delta}`);
  }

  // 6. negative distinctions: both rows, with codes and non-claims.
  const distinctions = artifact?.negative_distinctions;
  if (!Array.isArray(distinctions) || distinctions.length !== EXPECTED_DISTINCTIONS.length) {
    code("negative_distinction_missing", "exactly two negative distinctions are required");
  } else {
    const byId = new Map(distinctions.map((row) => [row?.distinction_id, row]));
    for (const expectedId of EXPECTED_DISTINCTIONS) {
      const row = byId.get(expectedId);
      if (!row) {
        code("negative_distinction_missing", `missing ${expectedId}`);
        continue;
      }
      if (row.fail_closed_code !== EXPECTED_DISTINCTION_CODES[expectedId]) {
        code("negative_distinction_missing", `${expectedId}: fail_closed_code`);
      }
      if (typeof row.non_claim !== "string" || row.non_claim.trim() === "") {
        code("negative_distinction_missing", `${expectedId}: non_claim`);
      }
    }
    for (const id of byId.keys()) {
      if (!EXPECTED_DISTINCTIONS.includes(id)) {
        code("negative_distinction_missing", `unexpected ${id}`);
      }
    }
  }

  // 7. the source-family axis is a corpus axis, never an IR family.
  const axis = artifact?.source_family_axis;
  if (!Array.isArray(axis)) {
    code("source_family_as_ir_family", "source_family_axis is not an array");
  } else {
    const axisIds = axis.map((row) => row?.source_family_id);
    if (axisIds.length !== M209_SOURCE_FAMILIES.length) {
      code("source_family_as_ir_family", `axis count ${axisIds.length}`);
    }
    for (const expectedId of M209_SOURCE_FAMILIES) {
      if (!axisIds.includes(expectedId)) {
        code("source_family_as_ir_family", `axis missing ${expectedId}`);
      }
    }
    for (const row of axis) {
      if (typeof row?.role !== "string" || !row.role.includes(NOT_IR_FRAGMENT)) {
        code("source_family_as_ir_family", `${row?.source_family_id}: role is not marked non-IR`);
      }
    }
  }

  // 8. no runtime claim in the register or its companion.
  for (const marker of RUNTIME_MARKERS) {
    if (rawText.includes(marker)) code("runtime_claim_present", `register contains ${marker}`);
    if (companionText.includes(marker)) code("runtime_claim_present", `companion contains ${marker}`);
  }

  // 9. non-claims present and complete.
  if (!Array.isArray(artifact?.non_claims) || artifact.non_claims.length === 0) {
    code("non_claims_missing", "non_claims is missing or empty");
  } else {
    const joined = artifact.non_claims.join(" ").toLowerCase();
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      if (!joined.includes(fragment.toLowerCase())) {
        code("non_claims_missing", `non-claim missing: ${fragment}`);
      }
    }
  }

  return { ok: errors.length === 0, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const doc = readRepo(REGISTER);
const liveSha = {
  TLM: sha256("prd/temporal-legal-model.md"),
  TSG: sha256("prd/architecture/temporal-semantic-gap-register.md"),
  REV28: sha256("doc/review/review-28-10-09-2026.md"),
};

// Locate a family's segment and replace exactly one fragment inside it, so a
// mutation never collides with the same value on a sibling family.
function withFamily(text, familyId, find, replacement) {
  const anchor = `"family_id":"${familyId}"`;
  const start = text.indexOf(anchor);
  assert.notEqual(start, -1, `withFamily: family ${familyId} not found`);
  const nextStart = text.indexOf('"family_id":"', start + anchor.length);
  const limit = nextStart === -1 ? text.length : nextStart;
  const segment = text.slice(start, limit);
  assert.ok(segment.includes(find), `withFamily(${familyId}): fragment not found`);
  return text.slice(0, start) + segment.replace(find, replacement) + text.slice(limit);
}

function fixture(mutate) {
  const next = mutate(doc);
  assert.notEqual(next, doc, "fixture mutation did not modify the register");
  return next;
}

function expectCode(text, expected, options) {
  const result = validateRegister(text, options);
  assert.ok(
    codes(result).includes(expected),
    `expected ${expected}, got ${JSON.stringify(codes(result))}`,
  );
  return result;
}

function companionDocumentedCodes(text) {
  const lines = text.split("\n");
  const start = lines.findIndex((line) => line.trim() === "## Fail-closed codes");
  assert.notEqual(start, -1, "companion must carry a '## Fail-closed codes' section");
  const out = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    if (lines[index].startsWith("## ")) break;
    const match = /^- `([a-z_]+)`/.exec(lines[index]);
    if (match) out.push(match[1]);
  }
  return out;
}

// ---------------------------------------------------------------------------
// live checks
// ---------------------------------------------------------------------------

test("the live register is canonical compact ASCII JSON with no timestamp", () => {
  assert.equal(JSON.stringify(JSON.parse(doc)), doc, "register must be canonical compact JSON");
  const offending = [...doc].findIndex((character) => character.charCodeAt(0) > 0x7f);
  assert.equal(offending, -1, `register must be ASCII-only (offence at ${offending})`);
  for (const marker of TIMESTAMP_MARKERS) {
    assert.doesNotMatch(doc, marker, "register must not carry a timestamp");
  }
});

test("the register passes its own contract and the closed family set is exact", () => {
  const result = validateRegister(doc);
  assert.deepEqual(result.errors, [], `live register errors: ${JSON.stringify(result.errors)}`);
  const artifact = JSON.parse(doc);
  assert.equal(artifact.schema, SCHEMA);
  assert.equal(artifact.kind, KIND);
  assert.equal(artifact.milestone, MILESTONE);
  assert.equal(artifact.slice, SLICE);
  assert.equal(artifact.task, TASK);
  assert.equal(artifact.authoritative, false);
  assert.equal(artifact.lifecycle, LIFECYCLE);
  assert.deepEqual(
    artifact.families.map((family) => family.family_id),
    CLOSED_FAMILIES,
  );
});

test("every owning source and source binding is tracked, exists and hash-matches", () => {
  const artifact = JSON.parse(doc);
  const pairs = [
    ...artifact.families.map((family) => [family.owning_source.path, family.owning_source.sha256]),
    ...artifact.source_bindings.map((binding) => [binding.path, binding.sha256]),
  ];
  for (const [relPath, declared] of pairs) {
    assert.ok(repoExists(relPath), `${relPath} must exist`);
    assert.ok(isTracked(relPath), `${relPath} must be tracked`);
    assert.ok(!isForbiddenPath(relPath), `${relPath} must be repository-relative`);
    assert.equal(declared, sha256(relPath), `${relPath} hash must match the live file`);
  }
  const declaredBindings = artifact.source_bindings.map((binding) => binding.path);
  assert.deepEqual(declaredBindings, EXPECTED_BINDINGS, "the five frozen inputs must be bound");
});

test("definition is the declared no_owning_row gap and statuses stay at their ceiling", () => {
  const artifact = JSON.parse(doc);
  const byId = new Map(artifact.families.map((family) => [family.family_id, family]));
  for (const [familyId, ceiling] of Object.entries(STATUS_CEILING)) {
    const family = byId.get(familyId);
    assert.ok(family, `family ${familyId} must exist`);
    assert.ok(
      STATUS_RANK[family.vocabulary_status] <= STATUS_RANK[ceiling],
      `${familyId} must not exceed its ${ceiling} ceiling`,
    );
  }
  assert.equal(byId.get("definition").owning_source_kind, "no_owning_row");
  assert.equal(byId.get("definition").vocabulary_status, "no_owning_row");
  for (const family of artifact.families) {
    assert.equal(family.non_adoption, true, `${family.family_id} must carry non_adoption=true`);
    assert.ok(
      family.fail_closed_boundary.unknown_outcome.includes("Unknown"),
      `${family.family_id} unknown outcome must be explicit`,
    );
    assert.ok(
      family.fail_closed_boundary.conflict_outcome.includes("Conflict"),
      `${family.family_id} conflict outcome must be explicit`,
    );
  }
});

test("the two negative distinctions and the non-IR source axis are present", () => {
  const artifact = JSON.parse(doc);
  assert.deepEqual(
    artifact.negative_distinctions.map((row) => row.distinction_id),
    EXPECTED_DISTINCTIONS,
  );
  for (const row of artifact.negative_distinctions) {
    assert.equal(row.fail_closed_code, EXPECTED_DISTINCTION_CODES[row.distinction_id]);
    assert.ok(row.non_claim.length > 0, `${row.distinction_id} needs a non-claim`);
  }
  assert.deepEqual(
    artifact.source_family_axis.map((row) => row.source_family_id),
    M209_SOURCE_FAMILIES,
  );
  for (const row of artifact.source_family_axis) {
    assert.ok(row.role.includes(NOT_IR_FRAGMENT), `${row.source_family_id} must be marked non-IR`);
  }
});

test("no runtime marker appears in the register or its companion", () => {
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!doc.includes(marker), `register must not claim runtime (${marker})`);
    assert.ok(!liveCompanion.includes(marker), `companion must not claim runtime (${marker})`);
  }
  assert.ok(
    liveCompanion.includes("## Not an adoption of semantics"),
    "companion must carry the non-adoption section",
  );
  assert.ok(liveCompanion.includes("## Families"), "companion must carry the family table");
  assert.ok(
    liveCompanion.includes("## Source-family axis"),
    "companion must carry the source-family axis",
  );
});

test("the documented fail-closed code set equals the emittable set", () => {
  const artifact = JSON.parse(doc);
  assert.deepEqual(
    [...artifact.fail_closed_codes].sort(),
    [...EMITTABLE_CODES].sort(),
    "the register must declare exactly the emittable code set",
  );
  assert.deepEqual(
    companionDocumentedCodes(liveCompanion).sort(),
    [...EMITTABLE_CODES].sort(),
    "the companion must document exactly the emittable code set",
  );
});

// ---------------------------------------------------------------------------
// negative tests (one per code, plus the closed-vocabulary edges)
// ---------------------------------------------------------------------------

test("negative: the closed family set refuses unknown, duplicated and missing rows", () => {
  expectCode(
    fixture((text) => text.replace('"family_id":"obligation"', '"family_id":"deontic_obligation"')),
    "unknown_family",
  );
  expectCode(fixture((text) => text.replace('"families":[', '"families":[] ,"families_ignored":[')), "unknown_family");
  expectCode(
    fixture((text) => text.replace('"family_id":"permission"', '"family_id":"obligation"')),
    "family_duplicated",
  );
});

test("negative: missing owning-source declarations and missing non-claims are refused", () => {
  expectCode(
    fixture((text) =>
      withFamily(text, "definition", '"owning_source_kind":"no_owning_row"', '"owning_source_kind":""'),
    ),
    "owning_source_missing",
  );
  expectCode(
    fixture((text) =>
      withFamily(text, "condition", '"what_it_must_separate":"', '"what_it_must_separate":"" ,"unused":"'),
    ),
    "owning_source_missing",
  );
  expectCode(
    fixture((text) => text.replace(/("non_claims":)\[[^\]]*\]/, "$1[]")),
    "non_claims_missing",
  );
});

test("negative: untracked, forged and drifted sources are refused", () => {
  expectCode(
    fixture((text) =>
      withFamily(
        text,
        "condition",
        '"path":"prd/temporal-legal-model.md"',
        '"path":".gsd/normative-family-register.json"',
      ),
    ),
    "source_not_tracked",
  );
  expectCode(
    fixture((text) =>
      withFamily(text, "condition", '"path":"prd/temporal-legal-model.md"', '"path":"tmp/ghost.md"'),
    ),
    "source_not_tracked",
  );
  expectCode(
    fixture((text) =>
      withFamily(
        text,
        "exception",
        `"sha256":"${liveSha.TLM}"`,
        `"sha256":"${"0".repeat(64)}"`,
      ),
    ),
    "source_hash_mismatch",
  );
  expectCode(doc, "source_hash_mismatch", { frozenDelta: ` M ${EXPECTED_BINDINGS[0]}` });
});

test("negative: promoted status, unknown vocabulary and an authoritative claim are refused", () => {
  expectCode(
    fixture((text) =>
      withFamily(text, "condition", '"vocabulary_status":"deferred-undefined"', '"vocabulary_status":"bounded"'),
    ),
    "status_promoted",
  );
  expectCode(
    fixture((text) =>
      withFamily(text, "definition", '"vocabulary_status":"no_owning_row"', '"vocabulary_status":"proposed"'),
    ),
    "status_promoted",
  );
  expectCode(
    fixture((text) => text.replace('"authoritative":false', '"authoritative":true')),
    "status_promoted",
  );
  expectCode(
    fixture((text) =>
      withFamily(text, "competence", '"vocabulary_status":"proposed"', '"vocabulary_status":"canonical"'),
    ),
    "status_unknown",
  );
  expectCode(
    fixture((text) =>
      withFamily(text, "competence", '"evidence_class":"source-bound-span"', '"evidence_class":"runtime-proven"'),
    ),
    "status_unknown",
  );
});

test("negative: a dropped distinction, an IR-claimed axis and a runtime claim are refused", () => {
  expectCode(
    fixture((text) =>
      text.replace(
        '"distinction_id":"lack_of_evidence_is_not_falsity"',
        '"distinction_id":"lack_of_evidence"',
      ),
    ),
    "negative_distinction_missing",
  );
  expectCode(
    fixture((text) =>
      text.replace(
        '"role":"source-side axis of N to M provenance, not an IR family"',
        '"role":"source-side IR family"',
      ),
    ),
    "source_family_as_ir_family",
  );
  expectCode(
    fixture((text) =>
      text.replace('"revision_policy":"', '"runtime_note":"pub struct RuleRecord","revision_policy":"'),
    ),
    "runtime_claim_present",
  );
  expectCode(doc, "runtime_claim_present", {
    companionText: `${liveCompanion}\n\npub fn mint_rule() {}\n`,
  });
});

// ---------------------------------------------------------------------------
// code-coverage registry
//
// One empirical mutation per documented fail-closed code, so a code can never be
// documented without being reachable and never reachable without being
// documented.
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "unknown_family",
    mutate: (text) => text.replace('"family_id":"obligation"', '"family_id":"deontic_obligation"'),
  },
  {
    code: "family_duplicated",
    mutate: (text) => text.replace('"family_id":"permission"', '"family_id":"obligation"'),
  },
  {
    code: "owning_source_missing",
    mutate: (text) =>
      withFamily(text, "definition", '"owning_source_kind":"no_owning_row"', '"owning_source_kind":""'),
  },
  {
    code: "source_not_tracked",
    mutate: (text) =>
      withFamily(
        text,
        "condition",
        '"path":"prd/temporal-legal-model.md"',
        '"path":".gsd/normative-family-register.json"',
      ),
  },
  {
    code: "source_hash_mismatch",
    mutate: (text) =>
      withFamily(text, "exception", `"sha256":"${liveSha.TLM}"`, `"sha256":"${"0".repeat(64)}"`),
  },
  {
    code: "status_unknown",
    mutate: (text) =>
      withFamily(text, "competence", '"vocabulary_status":"proposed"', '"vocabulary_status":"canonical"'),
  },
  {
    code: "status_promoted",
    mutate: (text) =>
      withFamily(text, "condition", '"vocabulary_status":"deferred-undefined"', '"vocabulary_status":"bounded"'),
  },
  {
    code: "negative_distinction_missing",
    mutate: (text) =>
      text.replace(
        '"distinction_id":"lack_of_evidence_is_not_falsity"',
        '"distinction_id":"lack_of_evidence"',
      ),
  },
  {
    code: "source_family_as_ir_family",
    mutate: (text) =>
      text.replace(
        '"role":"source-side axis of N to M provenance, not an IR family"',
        '"role":"source-side IR family"',
      ),
  },
  {
    code: "runtime_claim_present",
    mutate: (text) =>
      text.replace('"revision_policy":"', '"runtime_note":"pub struct RuleRecord","revision_policy":"'),
  },
  {
    code: "non_claims_missing",
    mutate: (text) => text.replace(/("non_claims":)\[[^\]]*\]/, "$1[]"),
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const text = entry.mutate(doc);
    assert.notEqual(text, doc, `${entry.code}: the mutation must actually change the register`);
    const result = validateRegister(text);
    assert.ok(
      codes(result).includes(entry.code),
      `${entry.code} was not emitted by its mutation; got ${JSON.stringify(codes(result))}`,
    );
    covered.add(entry.code);
  }
  assert.deepEqual(
    [...covered].sort(),
    [...EMITTABLE_CODES].sort(),
    "every documented fail-closed code must have a firing mutation",
  );
});

// ---------------------------------------------------------------------------
// markers (emitted only after the register contract holds)
// ---------------------------------------------------------------------------

test("M210 S01 family register markers", () => {
  const result = validateRegister(doc);
  assert.deepEqual(result.errors, [], `register errors: ${JSON.stringify(result.errors)}`);
  const artifact = JSON.parse(doc);
  assert.equal(artifact.authoritative, false);
  assert.equal(artifact.families.length, CLOSED_FAMILIES.length);
  assert.equal(artifact.negative_distinctions.length, EXPECTED_DISTINCTIONS.length);
  assert.equal(artifact.source_family_axis.length, M209_SOURCE_FAMILIES.length);
  assert.ok(repoExists(COMPANION), "the companion must exist next to the register");
  console.log("M210_S01_FAMILY_REGISTER_OK");
  console.log(`families=${artifact.families.length}`);
  console.log(`negative_distinctions=${artifact.negative_distinctions.length}`);
  console.log(`source_family_axis=${artifact.source_family_axis.length}`);
  console.log(`fail_closed_codes=${EMITTABLE_CODES.length}`);
});
