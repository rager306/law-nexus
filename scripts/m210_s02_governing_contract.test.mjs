// M210-3afp79 S02 T04 governing-surface contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s02-governing-surface-check.json: the separate check,
// due BEFORE S03, of whether a tracked governing surface actually carries human
// adoption of the S01 IR semantics, what admissible scope a grant would cover,
// and which revision is tested. No adoption is declared here and no Review Case
// event is written.
//
// The claims under test are that the three checks (governing_surface,
// allowed_scope, revision) are present and non-empty, that every evidence row
// carries a repository-relative path plus a line number whose content really
// contains the recorded claim, that the review-case actor path is
// caller-supplied and the Review Case CLI has no submit subcommand (so
// actor_bound_path_available is false and claiming otherwise is refused), that
// the governing-surface verdict is absent and a verified verdict is refused
// while the actor path is unauthenticated, that the admissible scope is bounded
// and the tested revision is pinned as sha256:<64hex>, that resume_condition
// names an interactive source, that F13 stays on hold and is never derived from
// the IR answer, that the artifact carries no runtime marker and no raw text,
// and that each documented fail-closed code is empirically emitted by a
// mutation.
//
// This contract spawns no subprocess, opens no socket and reads only
// repository-relative tracked artifacts under prd/, doc/, src/ and scripts/. It
// never writes a file.
//
// Run: node --test scripts/m210_s02_governing_contract.test.mjs

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// governing_surface_absent: the governing-surface finding is not recorded as absent: the check set is incomplete, a check verdict is outside the dictionary, the top-level verdict claims a verified surface, or an adoption-surface candidate is marked as carrying an adoption while no tracked surface carries one.
// actor_bound_path_claimed: an actor-bound (authenticated) path is claimed without resolving file:line evidence: actor_bound_path_available is not false, or a candidate declares an authenticated actor.
// review_case_trust_boundary_unbound: the top-level verdict claims governing_surface_verified while the trust-boundary evidence confirms the review-case actor identity is caller-supplied or missing.
// scope_unbounded: the admissible scope carries no bounds, or its in-scope or out-of-scope bound list is missing, empty or not a list of non-empty strings.
// revision_unpinned: the tested source revision is absent, is not pinned as sha256:<64hex>, or differs from the T01 rebind snapshot.
// evidence_line_missing: a check or trust-boundary evidence row is missing, is not resolvable to a repository-relative tracked file, or its claim is not present on the recorded line.
// resume_condition_missing: the resume condition is absent or does not name an interactive source (an interaction id, an authenticated subjective-UAT reference or a criterion id).
// f13_inferred_from_ir: the F13 status is not hold while no separate F13 answer exists, or the record declares an F13 derivation from the IR answer.
// runtime_claim_present: the record carries a Rust implementation marker.
// raw_text_leak: the record carries a non-ASCII byte, an XML tag or a provider text marker.
// DOCUMENTED_CODES_END

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const GOVERNING_REL = "prd/architecture/m210-s02-governing-surface-check.json";
export const CONTRACT_REL = "scripts/m210_s02_governing_contract.test.mjs";
export const REBIND_REPORT_REL = "prd/architecture/m210-s02-rebind-report.json";
export const ANSWER_REL = "prd/architecture/m210-s02-answer-record.json";
export const PACKET_REL = "prd/architecture/m210-s02-owner-decision-packet.json";
export const RC28_REL = "prd/architecture/review-cases/rc28-remediation-program.md";
export const APPLICATION_REL = "src/law_nexus_harness/review_case/application.py";
export const CLI_REL = "src/law_nexus_harness/cli.py";

export const SCHEMA = "law-nexus/m210-s02-governing-surface-check/v1";
export const KIND = "m210-s02-governing-surface-check";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S02";
export const TASK = "T04";
export const LIFECYCLE = ["proposed"];
export const REQUIREMENT_REFS = ["RC28-F18", "R074"];

export const CHECK_IDS = ["governing_surface", "allowed_scope", "revision"];
export const CHECK_VERDICTS = ["verified", "absent", "unbounded", "unpinned"];
export const VERDICTS = ["governing_surface_verified", "governing_surface_absent"];
export const F13_STATUSES = ["hold", "answered"];

export const REVISION_RE = /^sha256:[0-9a-f]{64}$/;
export const RESUME_RE = /interaction|subjective-UAT|criterion id/;

// Paths that must never be read: gitignored vaults and absolute escapes.
export const IGNORED_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

export const EMITTABLE_CODES = [
  "governing_surface_absent",
  "actor_bound_path_claimed",
  "review_case_trust_boundary_unbound",
  "scope_unbounded",
  "revision_unpinned",
  "evidence_line_missing",
  "resume_condition_missing",
  "f13_inferred_from_ir",
  "runtime_claim_present",
  "raw_text_leak",
];

export const CONTRACT_MARKER = "M210_S02_GOVERNING_OK";

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

// ---------------------------------------------------------------------------
// shared fixtures
// ---------------------------------------------------------------------------

export const root = REPO_ROOT;
export const governingAbsolute = path.join(root, GOVERNING_REL);

export const committedText = readFileSync(path.join(root, GOVERNING_REL), "utf8");
export const governing = JSON.parse(committedText);
export const rebindReport = JSON.parse(readFileSync(path.join(root, REBIND_REPORT_REL), "utf8"));
export const answerRecord = JSON.parse(readFileSync(path.join(root, ANSWER_REL), "utf8"));
export const packet = JSON.parse(readFileSync(path.join(root, PACKET_REL), "utf8"));

// ---------------------------------------------------------------------------
// evidence resolution
// ---------------------------------------------------------------------------

export function safeRelative(relativePath) {
  if (typeof relativePath !== "string" || relativePath === "") return false;
  if (path.isAbsolute(relativePath)) return false;
  if (relativePath.split("/").includes("..")) return false;
  if (IGNORED_PREFIXES.some((prefix) => relativePath.startsWith(prefix))) return false;
  return true;
}

export function evidenceResolvable(entry) {
  if (!entry || typeof entry !== "object") return false;
  if (!safeRelative(entry.path)) return false;
  if (!Number.isInteger(entry.line) || entry.line < 1) return false;
  if (typeof entry.claim !== "string" || entry.claim === "") return false;
  const absolute = path.join(root, entry.path);
  if (!existsSync(absolute)) return false;
  const lines = readFileSync(path.join(root, entry.path), "utf8").split("\n");
  if (entry.line > lines.length) return false;
  return lines[entry.line - 1].includes(entry.claim);
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateGoverning(candidate, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : JSON.stringify(candidate);
  const expectedSourceRevision = env.expectedSourceRevision;
  const answer = env.answerRecord ?? answerRecord;
  const resolve = env.resolveEvidence ?? evidenceResolvable;

  // 1. text hygiene: ASCII-only, no XML or provider text marker, no Rust
  //    implementation marker.
  if ([...text].some((character) => character.charCodeAt(0) > 0x7f)) {
    code("raw_text_leak", "non-ascii byte in the record");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) code("runtime_claim_present", `runtime marker ${marker}`);
  }

  // 2. the tested revision is the T01 rebind snapshot, pinned as a sha256 digest.
  const revision = candidate?.source_revision;
  if (typeof revision !== "string" || !REVISION_RE.test(revision)) {
    code("revision_unpinned", `source_revision=${JSON.stringify(revision)}`);
  } else if (typeof expectedSourceRevision === "string" && revision !== expectedSourceRevision) {
    code("revision_unpinned", "source_revision differs from the T01 rebind snapshot");
  }

  // 3. the three checks are present exactly once, non-empty and evidence-bound.
  const checks = Array.isArray(candidate?.checks) ? candidate.checks : null;
  const byId = new Map();
  if (!checks) {
    code("governing_surface_absent", "checks[] is missing");
  } else {
    for (const checkId of CHECK_IDS) {
      const found = checks.filter((check) => check?.check_id === checkId);
      if (found.length !== 1) code("governing_surface_absent", `check ${checkId} count ${found.length}`);
      else byId.set(checkId, found[0]);
    }
    for (const check of checks) {
      if (!CHECK_IDS.includes(check?.check_id)) {
        code("governing_surface_absent", `unknown check ${JSON.stringify(check?.check_id)}`);
        continue;
      }
      if (!CHECK_VERDICTS.includes(check?.verdict)) {
        code("governing_surface_absent", `check ${check.check_id} verdict ${JSON.stringify(check.verdict)}`);
      }
      if (!Array.isArray(check?.evidence) || check.evidence.length === 0) {
        code("evidence_line_missing", `check ${check.check_id} has no evidence`);
        continue;
      }
      for (const row of check.evidence) {
        if (!resolve(row)) code("evidence_line_missing", `check ${check.check_id} evidence ${JSON.stringify(row)}`);
      }
    }
  }

  // 4. the governing surface is absent; a verified verdict is refused here.
  const governingCheck = byId.get("governing_surface");
  if (governingCheck && governingCheck.verdict !== "absent") {
    code("governing_surface_absent", `governing_surface verdict ${JSON.stringify(governingCheck.verdict)}`);
  }
  const verdict = candidate?.verdict;
  if (!VERDICTS.includes(verdict)) {
    code("governing_surface_absent", `verdict ${JSON.stringify(verdict)} is outside the dictionary`);
  } else if (verdict !== "governing_surface_absent") {
    code("governing_surface_absent", `verdict ${JSON.stringify(verdict)} claims a surface that does not exist`);
  }

  // 5. the admissible scope must be bounded.
  const scopeCheck = byId.get("allowed_scope");
  const bounds = scopeCheck?.bounds;
  const nonEmptyStrings = (value) =>
    Array.isArray(value) && value.length > 0 && value.every((item) => typeof item === "string" && item.trim() !== "");
  if (
    !bounds ||
    typeof bounds !== "object" ||
    bounds.bounded !== true ||
    !nonEmptyStrings(bounds.in_scope) ||
    !nonEmptyStrings(bounds.out_of_scope)
  ) {
    code("scope_unbounded", "allowed_scope bounds are missing or empty");
  }

  // 6. the review-case actor path is caller-supplied, so no actor-bound path is
  //    available and no actor-bound claim may stand without file:line evidence.
  const trustBoundary = Array.isArray(candidate?.trust_boundary) ? candidate.trust_boundary : null;
  if (!trustBoundary || trustBoundary.length === 0) {
    code("actor_bound_path_claimed", "trust_boundary evidence is missing");
  } else {
    for (const row of trustBoundary) {
      if (!resolve(row)) code("evidence_line_missing", `trust_boundary ${JSON.stringify(row)}`);
    }
  }
  if (candidate?.actor_bound_path_available !== false) {
    code("actor_bound_path_claimed", `actor_bound_path_available=${JSON.stringify(candidate?.actor_bound_path_available)}`);
  }
  const actorProof = (trustBoundary ?? []).some((row) => row?.kind === "authenticated_actor" && resolve(row));
  if (candidate?.actor_bound_path_available === true && !actorProof) {
    code("actor_bound_path_claimed", "no file:line evidence of an authenticated actor");
  }
  for (const candidate_ of candidate?.adoption_surface_candidates ?? []) {
    if (candidate_?.authenticated === true || candidate_?.actor_bound === true) {
      code("actor_bound_path_claimed", `candidate ${candidate_?.path} claims an actor-bound path`);
    }
    if (candidate_?.adoption_present === true) {
      code("governing_surface_absent", `candidate ${candidate_?.path} claims a present adoption`);
    }
  }

  // 7. governing_surface_verified is refused while the actor path is
  //    unauthenticated (or the trust boundary is absent).
  const unbound = (trustBoundary ?? []).some(
    (row) => typeof row?.kind === "string" && row.kind.startsWith("caller_supplied") && resolve(row),
  );
  if (verdict === "governing_surface_verified" && (unbound || !trustBoundary || trustBoundary.length === 0)) {
    code(
      "review_case_trust_boundary_unbound",
      "governing_surface_verified while the review-case actor path is caller-supplied",
    );
  }

  // 8. the resume condition must name an interactive source.
  const resumeCondition = candidate?.resume_condition;
  if (typeof resumeCondition !== "string" || !RESUME_RE.test(resumeCondition)) {
    code("resume_condition_missing", "resume_condition must name an interactive source");
  }

  // 9. F13 is a separate decision and is never derived from the IR answer.
  const f13Status = candidate?.f13_status;
  if (!F13_STATUSES.includes(f13Status)) {
    code("f13_inferred_from_ir", `f13_status=${JSON.stringify(f13Status)}`);
  } else if (f13Status !== "hold") {
    code("f13_inferred_from_ir", "f13_status is not hold while no separate F13 answer exists");
  }
  if (candidate?.f13_derived_from_ir === true || candidate?.f13_inferred_from_ir === true) {
    code("f13_inferred_from_ir", "the record declares an F13 derivation from the IR answer");
  }
  if (answer && answer.status === "pending_human_decision" && f13Status !== "hold") {
    code("f13_inferred_from_ir", "F13 must stay hold while the answer record is pending");
  }

  return { ok: errors.length === 0, errors };
}

export function baseEnv(overrides = {}) {
  return {
    text: committedText,
    expectedSourceRevision: rebindReport.source_revision,
    answerRecord,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// harness
// ---------------------------------------------------------------------------

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function codesFor(mutated, overrides = {}) {
  const env = baseEnv({ text: JSON.stringify(mutated), ...overrides });
  return validateGoverning(mutated, env).errors.map((error) => error.name);
}

function contractSource() {
  return readFileSync(path.join(root, CONTRACT_REL), "utf8");
}

function documentedBlock() {
  const source = contractSource();
  const begin = source.indexOf("DOCUMENTED_CODES_BEGIN");
  const end = source.indexOf("DOCUMENTED_CODES_END");
  assert.ok(begin > 0 && end > begin, "the documented code block must be present");
  return source
    .slice(begin, end)
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_]+): /)?.[1])
    .filter((name) => typeof name === "string");
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

// ---------------------------------------------------------------------------
// artifact shape
// ---------------------------------------------------------------------------

contract("the governing-surface check exists and is canonical ASCII JSON with the M210 envelope", () => {
  assert.ok(existsSync(governingAbsolute), `${GOVERNING_REL} must exist`);
  assert.ok(!committedText.endsWith("\n"), "the record must carry no trailing newline");
  assert.ok(
    ![...committedText].some((character) => character.charCodeAt(0) > 0x7f),
    "the record must be ASCII-only",
  );
  assert.equal(JSON.stringify(governing), committedText, "the record must be canonical JSON that round-trips");
  assert.equal(governing.schema, SCHEMA);
  assert.equal(governing.kind, KIND);
  assert.equal(governing.milestone, MILESTONE);
  assert.equal(governing.slice, SLICE);
  assert.equal(governing.task, TASK);
  assert.deepEqual(governing.lifecycle, LIFECYCLE);
  assert.equal(governing.authoritative, false);
  assert.equal(governing.ascii_only, true);
  assert.deepEqual(governing.requirement_refs, REQUIREMENT_REFS);
});

contract("the three governing checks are present, non-empty and each carries resolving file:line evidence", () => {
  assert.ok(Array.isArray(governing.checks), "checks[] must be a list");
  assert.deepEqual(
    governing.checks.map((check) => check.check_id),
    CHECK_IDS,
    "the check set must be exactly governing_surface, allowed_scope, revision",
  );
  for (const check of governing.checks) {
    assert.ok(CHECK_VERDICTS.includes(check.verdict), `check ${check.check_id} verdict must be in the dictionary`);
    assert.ok(Array.isArray(check.evidence) && check.evidence.length > 0, `check ${check.check_id} needs evidence`);
    for (const row of check.evidence) {
      assert.ok(safeRelative(row.path), `evidence path ${row.path} must be repository-relative`);
      assert.ok(Number.isInteger(row.line) && row.line >= 1, `evidence line for ${row.path} must be a line number`);
      assert.ok(
        evidenceResolvable(row),
        `the claim for ${row.path}:${row.line} must actually be present on that line`,
      );
    }
    assert.equal(typeof check.note, "string");
    assert.ok(check.note.trim() !== "", `check ${check.check_id} must carry a note`);
  }
});

contract("the governing surface is recorded absent and no adoption is claimed", () => {
  const governingCheck = governing.checks.find((check) => check.check_id === "governing_surface");
  assert.equal(governingCheck.verdict, "absent", "no tracked surface carries an IR adoption");
  assert.equal(governing.verdict, "governing_surface_absent");
  assert.ok(Array.isArray(governing.adoption_surface_candidates));
  assert.ok(governing.adoption_surface_candidates.length > 0, "candidate surfaces must be enumerated");
  for (const candidate of governing.adoption_surface_candidates) {
    assert.ok(existsSync(path.join(root, candidate.path)), `candidate ${candidate.path} must exist`);
    assert.equal(candidate.adoption_present, false, `candidate ${candidate.path} must not claim an adoption`);
    assert.equal(typeof candidate.why_not_adoption, "string");
    assert.ok(candidate.why_not_adoption.trim() !== "", `candidate ${candidate.path} needs a reason`);
  }
  assert.equal(governing.semantics_adopted, undefined);
  assert.equal(governing.adoption, undefined);
  assert.equal(governing.answer_treated_as_adoption, undefined);
});

contract("the review-case actor path is caller-supplied and the Review Case CLI has no submit subcommand", () => {
  assert.equal(governing.actor_bound_path_available, false);
  assert.ok(Array.isArray(governing.trust_boundary) && governing.trust_boundary.length > 0);
  for (const row of governing.trust_boundary) {
    assert.ok(safeRelative(row.path), `trust-boundary path ${row.path} must be repository-relative`);
    assert.ok(evidenceResolvable(row), `trust-boundary claim for ${row.path}:${row.line} must be present`);
  }
  assert.ok(
    governing.trust_boundary.some(
      (row) => typeof row.kind === "string" && row.kind.startsWith("caller_supplied") && evidenceResolvable(row),
    ),
    "the trust boundary must prove an actor_class/actor_id caller-supplied path",
  );

  const application = readFileSync(path.join(root, APPLICATION_REL), "utf8");
  assert.ok(
    application.includes("actor_class: ActorClass = ActorClass.HUMAN"),
    "the actor_class default is caller-supplied, not authenticated",
  );
  assert.ok(application.includes("actor_id: str"), "actor_id is caller-supplied");
  assert.ok(application.includes("def _require_human_actor("), "human actor validation must exist");
  assert.ok(
    application.includes('message="only actor_class=human may record disposition, relation, execution, or reopen"'),
    "the validation checks only the caller-supplied actor_class value",
  );

  const cli = readFileSync(path.join(root, CLI_REL), "utf8");
  const subcommands = [...cli.matchAll(/review_ops\.add_parser\(\s*"([a-z_]+)"/g)].map((match) => match[1]);
  assert.deepEqual(
    subcommands.slice().sort(),
    ["inventory", "register", "status", "validate"],
    "the Review Case CLI exposes exactly register/validate/status/inventory",
  );
  assert.ok(
    !/review_ops\.add_parser\(\s*"(submit|disposition|record|verify|adopt|grant)"/.test(cli),
    "no submit-family subcommand may exist",
  );
  assert.ok(
    cli.includes("unhandled review-case command"),
    "the handler has no submit branch beyond the four read/register operations",
  );
});

contract("the admissible scope is bounded and the revision is pinned to the T01 snapshot", () => {
  const scopeCheck = governing.checks.find((check) => check.check_id === "allowed_scope");
  assert.equal(scopeCheck.bounds.bounded, true);
  assert.ok(Array.isArray(scopeCheck.bounds.in_scope) && scopeCheck.bounds.in_scope.length > 0);
  assert.ok(Array.isArray(scopeCheck.bounds.out_of_scope) && scopeCheck.bounds.out_of_scope.length > 0);

  const revisionCheck = governing.checks.find((check) => check.check_id === "revision");
  assert.equal(revisionCheck.verdict, "verified");
  assert.ok(REVISION_RE.test(governing.source_revision), "the revision must be pinned as sha256:<64hex>");
  assert.equal(governing.source_revision, rebindReport.source_revision);
  assert.equal(governing.source_revision, answerRecord.source_revision);
});

contract("the resume condition names the interactive source and F13 stays on hold", () => {
  assert.match(governing.resume_condition, RESUME_RE);
  assert.equal(governing.f13_status, "hold");
  assert.equal(governing.f13_status, answerRecord.f13_status);
  assert.equal(governing.f13_derived_from_ir, undefined);
  assert.ok(Array.isArray(governing.non_claims) && governing.non_claims.length > 0);
  assert.ok(governing.non_claims.every((claim) => typeof claim === "string" && claim.trim() !== ""));
});

contract("the clean record emits no fail-closed code", () => {
  const result = validateGoverning(governing, baseEnv());
  assert.deepEqual(result.errors, [], `clean record must be code-free: ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, true);
});

// ---------------------------------------------------------------------------
// fail-closed codes
// ---------------------------------------------------------------------------

contract("each documented fail-closed code is empirically emitted by a mutation", () => {
  const emitted = new Set();
  const collect = (codes) => {
    for (const name of codes) emitted.add(name);
  };

  const verifiedVerdict = clone(governing);
  verifiedVerdict.verdict = "governing_surface_verified";
  collect(codesFor(verifiedVerdict));

  const verifiedCheck = clone(governing);
  verifiedCheck.checks.find((check) => check.check_id === "governing_surface").verdict = "verified";
  collect(codesFor(verifiedCheck));

  const presentAdoption = clone(governing);
  presentAdoption.adoption_surface_candidates[0].adoption_present = true;
  collect(codesFor(presentAdoption));

  const actorBound = clone(governing);
  actorBound.actor_bound_path_available = true;
  collect(codesFor(actorBound));

  const authenticatedCandidate = clone(governing);
  authenticatedCandidate.adoption_surface_candidates[0].authenticated = true;
  collect(codesFor(authenticatedCandidate));

  const unbounded = clone(governing);
  delete unbounded.checks.find((check) => check.check_id === "allowed_scope").bounds;
  collect(codesFor(unbounded));

  const emptyInScope = clone(governing);
  emptyInScope.checks.find((check) => check.check_id === "allowed_scope").bounds.in_scope = [];
  collect(codesFor(emptyInScope));

  const unpinned = clone(governing);
  unpinned.source_revision = "sha256:zzz";
  collect(codesFor(unpinned));

  const staleRevision = clone(governing);
  staleRevision.source_revision = `sha256:${"0".repeat(64)}`;
  collect(codesFor(staleRevision));

  const missingEvidence = clone(governing);
  missingEvidence.checks[0].evidence[0].claim = "this claim is not present on that line";
  collect(codesFor(missingEvidence));

  const missingEvidenceRow = clone(governing);
  missingEvidenceRow.checks[2].evidence = [];
  collect(codesFor(missingEvidenceRow));

  const unsafeEvidencePath = clone(governing);
  unsafeEvidencePath.trust_boundary[0].path = "/etc/passwd";
  collect(codesFor(unsafeEvidencePath));

  const ignoredEvidencePath = clone(governing);
  ignoredEvidencePath.trust_boundary[0].path = ".gsd/secret.json";
  collect(codesFor(ignoredEvidencePath));

  const missingResume = clone(governing);
  missingResume.resume_condition = "later";
  collect(codesFor(missingResume));

  const f13Answered = clone(governing);
  f13Answered.f13_status = "answered";
  collect(codesFor(f13Answered));

  const f13Derived = clone(governing);
  f13Derived.f13_derived_from_ir = true;
  collect(codesFor(f13Derived));

  const runtimeClaim = clone(governing);
  runtimeClaim.non_claims.push("pub fn adopt()");
  collect(codesFor(runtimeClaim));

  const rawXml = clone(governing);
  rawXml.non_claims.push("<npa>text</npa>");
  collect(codesFor(rawXml));

  const rawNonAscii = clone(governing);
  rawNonAscii.non_claims.push("Норма");
  collect(codesFor(rawNonAscii));

  const missingChecks = clone(governing);
  missingChecks.checks = [];
  collect(codesFor(missingChecks));

  const unknownVerdict = clone(governing);
  unknownVerdict.verdict = "adopted";
  collect(codesFor(unknownVerdict));

  assert.deepEqual([...emitted].sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(documentedBlock().sort(), EMITTABLE_CODES.slice().sort());
  assert.deepEqual(governing.fail_closed_codes.slice().sort(), EMITTABLE_CODES.slice().sort());
  assert.equal(EMITTABLE_CODES.length, 10);
});

// ---------------------------------------------------------------------------
// self-guards
// ---------------------------------------------------------------------------

contract("the contract is offline, spawns nothing and reads only repository-relative artifacts", () => {
  const source = contractSource();
  const specifiers = [...source.matchAll(/from\s+"(node:[a-z/]+)"/g)].map((match) => match[1]);
  assert.deepEqual(
    specifiers.slice().sort(),
    ["node:assert/strict", "node:fs", "node:test", "node:url", "node:path"].slice().sort(),
  );
  assert.ok(!/\bchild_process\b/.test(source), "no child process import may exist");
  assert.ok(!/\bspawn\(|\bexecSync\(|\bexecFile\(/.test(source), "no process spawn may exist");
  assert.ok(!/\bfetch\(/.test(source), "the contract must stay offline");

  const readTargets = [...source.matchAll(/readFileSync\(\s*([^)]*)\)/g)].map((match) => match[1].trim());
  assert.ok(readTargets.length > 0, "the contract must read its declared artifacts");
  for (const target of readTargets) {
    assert.ok(/^path\.join\(root,/.test(target), `every read must go through path.join(root, ...): ${target}`);
  }

  assert.equal(evidenceResolvable({ path: "doc/adr/README.md", line: 1, claim: "zzz-not-present" }), false);
  assert.equal(evidenceResolvable({ path: "/etc/passwd", line: 1, claim: "root" }), false);
  assert.equal(evidenceResolvable({ path: "../../etc/passwd", line: 1, claim: "root" }), false);
  assert.equal(evidenceResolvable({ path: ".gsd/gsd.db", line: 1, claim: "x" }), false);
  assert.equal(evidenceResolvable({ path: "doc/adr/does-not-exist.md", line: 1, claim: "x" }), false);
  assert.equal(evidenceResolvable({ path: "doc/adr/README.md", line: 0, claim: "x" }), false);
  assert.equal(evidenceResolvable({ path: "doc/adr/README.md", line: 1, claim: "" }), false);
});

contract("the marker is emitted only when every earlier case passed", () => {
  assert.deepEqual(failures, [], `failing cases: ${failures.join(", ")}`);
  process.stdout.write(
    `${CONTRACT_MARKER} checks=${governing.checks.length} codes=${EMITTABLE_CODES.length} ` +
      `trust_boundary=${governing.trust_boundary.length} candidates=${governing.adoption_surface_candidates.length}\n`,
  );
});
