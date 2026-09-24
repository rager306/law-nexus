// M210/S01 normative IR alternatives contract (T02).
//
// Offline and fail-closed. The subject is a *comparison* of alternatives, not an
// adoption: `prd/architecture/m210-s01-ir-alternatives.json` must carry at least
// three source-bound normative-IR alternatives, each with an honest separates /
// collapses split over the closed eight RC28-F18 families, an N to M
// provision-to-rule cardinality declared in both directions with min, unbounded
// max and policy, at least two "cannot prove" statements including legal
// correctness, at least one collapse risk, a section 3 deferred-term list (or an
// explicit empty list with a rationale), an advisory-only recommendation and
// adopted=false. The artifact must also carry the four provenance rules and an
// unprefilled decision question for the S02 owner.
//
// The artifact is canonical compact ASCII JSON with a fixed key order and no
// timestamp, so `JSON.stringify(JSON.parse(text)) === text` and the contract
// never has to guess a formatting convention. Structural mutations round-trip
// through JSON so every mutation stays parseable on purpose.
//
// Every documented fail-closed code is provable against a mutated copy of the
// live artifact (or its markdown companion), so the suite cannot assert a code
// it would never emit. Subprocesses are limited to `git ls-files --error-unmatch`
// (tracked-file proof) and `git status --porcelain` (frozen-input proof). No
// cargo, no network, no `.gsd` / ignored / absolute path is read as evidence.
//
// Run: node --test scripts/m210_s01_ir_alternatives_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/architecture/m210-s01-ir-alternatives.json";
const COMPANION = "prd/architecture/m210-s01-ir-alternatives.md";

const SCHEMA = "law-nexus/m210-normative-ir-alternatives/v1";
const KIND = "m210-s01-normative-ir-alternatives";
const MILESTONE = "M210-3afp79";
const SLICE = "S01";
const TASK = "T02";
const LIFECYCLE = "[proposed]";

// The closed RC28-F18 family set (T01 register), ordered as in the plan.
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

// The closed section 3 deferred-undefined vocabulary a variant may have to define.
const SECTION3_DEFERRED_TERMS = [
  "NormRule",
  "Condition",
  "LegalEffect",
  "Exception",
  "Defeater",
  "ApplicabilitySelector",
];

const EXPECTED_VARIANT_IDS = [
  "family_typed_record_ir",
  "single_facet_slot_rule_record",
  "abstention_first_candidates_only",
];

const EVIDENCE_CLASSES = ["inert-artifact", "source-bound-span", "runtime-absent"];
const VERDICT_DOMAIN = ["resolved", "unresolved", "conflicted"];

// The two cardinality directions. `max` is the unbounded token, never a number:
// a fixed numeric max would silently turn N to M into a closed 1 to 1 ceiling.
const CARDINALITY_SIDES = {
  provision_to_rule: { max: "N", policy: "unknown_policy", min: 0 },
  rule_to_provision: { max: "M", policy: "unresolved_policy", min: 1 },
};

const PROVENANCE_RULE_IDS = [
  "absence_yields_unknown",
  "unresolved_anchor_yields_unresolved",
  "contradiction_yields_conflicted",
  "cardinality_collapse_forbidden",
];
const CARDINALITY_GUARD_RULE = "cardinality_collapse_forbidden";

// Non-empty string fields every variant must carry.
const REQUIRED_VARIANT_STRING_FIELDS = [
  "variant_id",
  "label",
  "representation_shape",
  "separation_rationale",
  "consequences_for_S03",
  "required_new_adr_terms_note",
  "compatibility_with_existing_vocab",
  "cost_and_risk",
  "recommendation_rationale",
];

const REQUIRED_TOP_LEVEL_STRINGS = ["schema", "kind", "milestone", "slice", "task"];

// The six frozen inputs the alternatives are derived from.
const EXPECTED_BINDINGS = [
  "prd/architecture/m210-s01-normative-family-register.json",
  "prd/temporal-legal-model.md",
  "prd/architecture/operation-registry.yaml",
  "prd/architecture/assertion-lifecycle-contract.yaml",
  "prd/architecture/force-interval-set-contract.yaml",
  "prd/architecture/kb-ontology-l1-l3-draft.md",
];

// Paths that can never be evidence: ignored overlays, absolute paths, traversal.
const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/"];

// The complete fail-closed code set. The artifact and its companion must
// document exactly this set (no more, no less).
const EMITTABLE_CODES = [
  "variant_count_insufficient",
  "variant_id_duplicated",
  "missing_required_field",
  "cardinality_not_nm",
  "cardinality_collapsed",
  "adoption_claim",
  "semantics_adopted_claim",
  "collapse_risk_missing",
  "deferred_term_unlisted",
  "non_claims_missing",
];

// Design-only artifact: a Rust marker means the boundary was crossed. This is
// checked by a helper, not by a fail-closed code, because the plan's documented
// code set for T02 carries no runtime code.
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

function runtimeMarkersIn(text) {
  return RUNTIME_MARKERS.filter((marker) => text.includes(marker));
}

function sortJoin(values) {
  return [...values].sort().join("\n");
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

const liveCompanion = readRepo(COMPANION);

function validateAlternatives(rawText, options = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ code: name, detail });
  const tracked = options.tracked || isTracked;
  const companionText = options.companionText ?? liveCompanion;

  // Parsing is fatal, not a degraded pass: a document that is not JSON is not
  // this artifact. Mutations stay parseable on purpose.
  const artifact = JSON.parse(rawText);

  // 1. top-level identity.
  for (const field of REQUIRED_TOP_LEVEL_STRINGS) {
    if (!isNonEmptyString(artifact?.[field])) code("missing_required_field", `top-level ${field}`);
  }
  if (artifact?.schema !== SCHEMA) code("missing_required_field", `schema must be ${SCHEMA}`);
  if (artifact?.kind !== KIND) code("missing_required_field", `kind must be ${KIND}`);
  if (artifact?.milestone !== MILESTONE) code("missing_required_field", `milestone must be ${MILESTONE}`);
  if (artifact?.slice !== SLICE) code("missing_required_field", `slice must be ${SLICE}`);
  if (artifact?.task !== TASK) code("missing_required_field", `task must be ${TASK}`);

  // 2. adoption and authority claims.
  if (artifact?.semantics_adopted !== false) {
    code("semantics_adopted_claim", "semantics_adopted must stay false");
  }
  if (artifact?.authoritative !== false) {
    code("adoption_claim", "authoritative must stay false");
  }
  if (artifact?.lifecycle !== LIFECYCLE) {
    code("adoption_claim", `lifecycle must stay ${LIFECYCLE}`);
  }
  const refs = Array.isArray(artifact?.requirement_refs) ? artifact.requirement_refs : [];
  for (const required of ["RC28-F18", "R074"]) {
    if (!refs.includes(required)) code("missing_required_field", `requirement_refs missing ${required}`);
  }

  // 3. variants: at least three, unique ids, complete fields, honest split.
  const variants = artifact?.variants;
  if (!Array.isArray(variants) || variants.length < 3) {
    code("variant_count_insufficient", `at least three variants are required, got ${variants?.length}`);
  }
  if (Array.isArray(variants)) {
    const seenIds = new Set();
    for (const variant of variants) {
      const id = isNonEmptyString(variant?.variant_id) ? variant.variant_id : "<unnamed>";
      if (seenIds.has(id)) code("variant_id_duplicated", id);
      seenIds.add(id);

      // required non-empty string fields.
      for (const field of REQUIRED_VARIANT_STRING_FIELDS) {
        if (!isNonEmptyString(variant?.[field])) {
          code("missing_required_field", `${id}: ${field}`);
        }
      }
      for (const field of ["separates", "collapses", "what_it_cannot_prove", "collapse_risks", "required_new_adr_terms"]) {
        if (!Array.isArray(variant?.[field])) code("missing_required_field", `${id}: ${field} not an array`);
      }

      // honest separates / collapses split over the closed eight families.
      const separates = Array.isArray(variant?.separates) ? variant.separates : [];
      const collapses = Array.isArray(variant?.collapses) ? variant.collapses : [];
      if (separates.length === 0) code("missing_required_field", `${id}: separates is empty`);
      for (const familyId of [...separates, ...collapses]) {
        if (!CLOSED_FAMILIES.includes(familyId)) {
          code("missing_required_field", `${id}: unknown family ${familyId}`);
        }
      }
      const overlap = separates.filter((familyId) => collapses.includes(familyId));
      if (overlap.length > 0) {
        code("missing_required_field", `${id}: family both separated and collapsed: ${overlap.join(",")}`);
      }
      if (sortJoin([...new Set([...separates, ...collapses])]) !== sortJoin(CLOSED_FAMILIES)) {
        code(
          "missing_required_field",
          `${id}: separated and collapsed families must account for all eight`,
        );
      }

      // N to M cardinality, declared in both directions.
      const cardinality = variant?.provenance_cardinality;
      if (cardinality === null || typeof cardinality !== "object") {
        code("cardinality_not_nm", `${id}: provenance_cardinality missing`);
      } else {
        for (const [side, contract] of Object.entries(CARDINALITY_SIDES)) {
          const declared = cardinality[side];
          if (declared === null || typeof declared !== "object") {
            code("cardinality_not_nm", `${id}: ${side} missing`);
            continue;
          }
          if (!Number.isInteger(declared.min) || declared.min !== contract.min) {
            code("cardinality_not_nm", `${id}: ${side}.min must be ${contract.min}`);
          }
          if (declared.max !== contract.max) {
            code(
              "cardinality_not_nm",
              `${id}: ${side}.max must be the unbounded token ${contract.max}`,
            );
          }
          if (!isNonEmptyString(declared[contract.policy])) {
            code("cardinality_not_nm", `${id}: ${side}.${contract.policy} missing`);
          }
        }
      }
      if (variant?.cardinality_collapse_allowed === true) {
        code("cardinality_collapsed", `${id}: cardinality collapse must not be allowed`);
      }

      // what it cannot prove: at least two, including legal correctness.
      const cannotProve = Array.isArray(variant?.what_it_cannot_prove)
        ? variant.what_it_cannot_prove
        : [];
      if (cannotProve.length < 2) {
        code("missing_required_field", `${id}: what_it_cannot_prove needs at least two entries`);
      }
      if (!cannotProve.join(" ").toLowerCase().includes("legal correctness")) {
        code("missing_required_field", `${id}: what_it_cannot_prove must include legal correctness`);
      }

      // at least one collapse risk.
      const risks = Array.isArray(variant?.collapse_risks)
        ? variant.collapse_risks.filter(isNonEmptyString)
        : [];
      if (risks.length === 0) code("collapse_risk_missing", `${id}: no collapse risk named`);

      // required new ADR terms from the closed section 3 deferred set.
      const terms = Array.isArray(variant?.required_new_adr_terms) ? variant.required_new_adr_terms : [];
      if (terms.length === 0) {
        if (!isNonEmptyString(variant?.required_new_adr_terms_note)) {
          code("deferred_term_unlisted", `${id}: an empty term list needs a rationale note`);
        }
      } else {
        for (const term of terms) {
          if (!SECTION3_DEFERRED_TERMS.includes(term)) {
            code("deferred_term_unlisted", `${id}: ${term} is not a section 3 deferred term`);
          }
        }
      }

      // recommendation is advisory and never an adoption.
      const recommendation = variant?.recommendation;
      if (recommendation === null || typeof recommendation !== "object") {
        code("missing_required_field", `${id}: recommendation block missing`);
      } else {
        if (typeof recommendation.recommended !== "boolean") {
          code("missing_required_field", `${id}: recommendation.recommended must be boolean`);
        }
        if (recommendation.advisory_only !== true) {
          code("adoption_claim", `${id}: recommendation must be advisory only`);
        }
        if (recommendation.not_an_acceptance !== true) {
          code("adoption_claim", `${id}: recommendation must not be an acceptance`);
        }
      }

      if (variant?.adopted !== false) code("adoption_claim", `${id}: adopted must stay false`);
    }
  }

  // 4. provenance contract: link record form plus the four rules.
  const provenance = artifact?.provenance_contract;
  if (provenance === null || typeof provenance !== "object") {
    code("missing_required_field", "provenance_contract missing");
  } else {
    const form = provenance.link_record_form;
    if (form === null || typeof form !== "object") {
      code("missing_required_field", "provenance_contract.link_record_form missing");
    } else {
      for (const field of ["from", "to", "family"]) {
        if (!isNonEmptyString(form[field])) {
          code("missing_required_field", `link_record_form.${field}`);
        }
      }
      const anchor = form.source_anchor;
      if (anchor === null || typeof anchor !== "object") {
        code("missing_required_field", "link_record_form.source_anchor missing");
      } else {
        for (const field of ["path", "span", "sha256"]) {
          if (!isNonEmptyString(anchor[field])) {
            code("missing_required_field", `link_record_form.source_anchor.${field}`);
          }
        }
      }
      if (sortJoin(form.evidence_class_domain ?? []) !== sortJoin(EVIDENCE_CLASSES)) {
        code("missing_required_field", "link_record_form.evidence_class_domain drift");
      }
      if (sortJoin(form.verdict_domain ?? []) !== sortJoin(VERDICT_DOMAIN)) {
        code("missing_required_field", "link_record_form.verdict_domain drift");
      }
      const formNonClaims = Array.isArray(form.non_claims) ? form.non_claims : [];
      if (formNonClaims.filter(isNonEmptyString).length === 0) {
        code("non_claims_missing", "link_record_form.non_claims is empty");
      }
    }
    const rules = Array.isArray(provenance.rules) ? provenance.rules : [];
    const ruleIds = rules.map((rule) => rule?.rule_id);
    for (const ruleId of PROVENANCE_RULE_IDS) {
      if (!ruleIds.includes(ruleId)) {
        if (ruleId === CARDINALITY_GUARD_RULE) {
          // Absent guard means cardinality collapse is not forbidden.
          code("cardinality_collapsed", "the cardinality collapse guard rule is missing");
        } else {
          code("missing_required_field", `provenance rule missing ${ruleId}`);
        }
      }
    }
    const guard = rules.find((rule) => rule?.rule_id === CARDINALITY_GUARD_RULE);
    if (guard && guard.code !== "cardinality_collapsed") {
      code("cardinality_collapsed", "the collapse guard rule must cite cardinality_collapsed");
    }
    if (guard && !isNonEmptyString(guard.statement)) {
      code("missing_required_field", "the collapse guard rule needs a statement");
    }
    for (const rule of rules) {
      if (isNonEmptyString(rule?.rule_id) && !isNonEmptyString(rule?.statement)) {
        code("missing_required_field", `provenance rule ${rule.rule_id} needs a statement`);
      }
    }
  }

  // 5. decision question belongs to the owner and is not prefilled.
  const decision = artifact?.decision_question;
  if (decision === null || typeof decision !== "object") {
    code("missing_required_field", "decision_question missing");
  } else {
    const question = isNonEmptyString(decision.question) ? decision.question : "";
    if (question === "") code("missing_required_field", "decision_question.question");
    for (const variantId of EXPECTED_VARIANT_IDS) {
      if (!question.includes(variantId)) {
        code("missing_required_field", `decision_question must name ${variantId}`);
      }
    }
    const options = Array.isArray(decision.options) ? decision.options.join(" ").toLowerCase() : "";
    if (!options.includes("reject")) {
      code("missing_required_field", "decision_question needs a reject option");
    }
    if (!options.includes("defer")) {
      code("missing_required_field", "decision_question needs a defer option");
    }
    if (decision.no_prefilled_consent !== true) {
      code("adoption_claim", "decision_question must declare no_prefilled_consent");
    }
  }

  // 6. recommendation summary matches exactly the variant marked recommended.
  const marked = Array.isArray(variants)
    ? variants.filter((variant) => variant?.recommendation?.recommended === true)
    : [];
  const summary = artifact?.recommendation_summary;
  if (summary === null || typeof summary !== "object") {
    code("missing_required_field", "recommendation_summary missing");
  } else {
    if (summary.is_recommendation_only !== true) {
      code("adoption_claim", "recommendation_summary must be advisory only");
    }
    if (summary.not_an_acceptance !== true) {
      code("adoption_claim", "recommendation_summary must not be an acceptance");
    }
    const markedIds = marked.map((variant) => variant.variant_id);
    if (markedIds.length !== 1 || markedIds[0] !== summary.recommended_variant_id) {
      code(
        "missing_required_field",
        `recommendation_summary must match the single recommended variant, marked ${JSON.stringify(markedIds)}`,
      );
    }
  }

  // 7. source bindings: repository-relative, existing, tracked, hash-matching.
  const bindings = Array.isArray(artifact?.source_bindings) ? artifact.source_bindings : [];
  if (bindings.length === 0) code("missing_required_field", "source_bindings is empty");
  const declaredBindingPaths = new Set();
  for (const binding of bindings) {
    const relPath = binding?.path;
    if (!isNonEmptyString(relPath)) {
      code("missing_required_field", "source binding path is missing");
      continue;
    }
    declaredBindingPaths.add(relPath);
    if (!isNonEmptyString(binding?.section)) {
      code("missing_required_field", `source binding ${relPath} needs a section`);
    }
    if (!/^[0-9a-f]{64}$/.test(binding?.sha256 ?? "")) {
      code("missing_required_field", `source binding ${relPath} needs a sha256`);
      continue;
    }
    if (isForbiddenPath(relPath)) {
      code("missing_required_field", `source binding ${relPath} is not repository-relative`);
      continue;
    }
    if (!repoExists(relPath)) {
      code("missing_required_field", `source binding ${relPath} does not exist`);
      continue;
    }
    if (!tracked(relPath)) {
      code("missing_required_field", `source binding ${relPath} is not tracked`);
      continue;
    }
    if (binding.sha256 !== sha256(relPath)) {
      code("missing_required_field", `source binding ${relPath} hash drift versus the live file`);
    }
  }
  for (const expectedPath of EXPECTED_BINDINGS) {
    if (!declaredBindingPaths.has(expectedPath)) {
      code("missing_required_field", `source binding missing ${expectedPath}`);
    }
  }

  // 8. frozen inputs: a worktree delta on a pinned source invalidates the pin.
  const delta = options.frozenDelta ?? worktreeDelta(EXPECTED_BINDINGS);
  if (typeof delta === "string" && delta.trim() !== "") {
    code("missing_required_field", `frozen input worktree delta: ${delta}`);
  }

  // 9. documented fail-closed code set is exact.
  if (!Array.isArray(artifact?.fail_closed_codes)) {
    code("missing_required_field", "fail_closed_codes is not an array");
  } else if (sortJoin(artifact.fail_closed_codes) !== sortJoin(EMITTABLE_CODES)) {
    code("missing_required_field", "fail_closed_codes drift");
  }

  // 10. non-claims present and complete.
  const nonClaims = Array.isArray(artifact?.non_claims) ? artifact.non_claims : [];
  if (nonClaims.filter(isNonEmptyString).length === 0) {
    code("non_claims_missing", "non_claims is missing or empty");
  } else {
    const joined = nonClaims.join(" ").toLowerCase();
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      if (!joined.includes(fragment.toLowerCase())) {
        code("non_claims_missing", `non-claim missing: ${fragment}`);
      }
    }
  }
  if (!isNonEmptyString(artifact?.revision_policy)) {
    code("missing_required_field", "revision_policy");
  }

  // 11. no runtime marker in the artifact or its companion.
  for (const marker of runtimeMarkersIn(rawText)) {
    code("missing_required_field", `artifact contains a runtime marker: ${marker}`);
  }
  for (const marker of runtimeMarkersIn(companionText)) {
    code("missing_required_field", `companion contains a runtime marker: ${marker}`);
  }

  return { ok: errors.length === 0, errors };
}

function codes(result) {
  return result.errors.map((entry) => entry.code);
}

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const doc = readRepo(ARTIFACT);

// Structural mutations round-trip through JSON, so a mutated document is always
// parseable and the mutation itself is provably applied.
function fixture(mutate) {
  const artifact = JSON.parse(doc);
  mutate(artifact);
  const next = JSON.stringify(artifact);
  assert.notEqual(next, doc, "fixture mutation did not modify the artifact");
  return next;
}

function clone() {
  return JSON.parse(doc);
}

function expectCode(text, expected, options) {
  const result = validateAlternatives(text, options);
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

test("the live artifact is canonical compact ASCII JSON with no timestamp", () => {
  assert.equal(JSON.stringify(JSON.parse(doc)), doc, "artifact must be canonical compact JSON");
  const offending = [...doc].findIndex((character) => character.charCodeAt(0) > 0x7f);
  assert.equal(offending, -1, `artifact must be ASCII-only (offence at ${offending})`);
  for (const marker of TIMESTAMP_MARKERS) {
    assert.doesNotMatch(doc, marker, "artifact must not carry a timestamp");
  }
});

test("the artifact passes its own contract and names exactly three alternatives", () => {
  const result = validateAlternatives(doc);
  assert.deepEqual(result.errors, [], `live artifact errors: ${JSON.stringify(result.errors)}`);
  const artifact = JSON.parse(doc);
  assert.equal(artifact.schema, SCHEMA);
  assert.equal(artifact.kind, KIND);
  assert.equal(artifact.milestone, MILESTONE);
  assert.equal(artifact.slice, SLICE);
  assert.equal(artifact.task, TASK);
  assert.equal(artifact.authoritative, false);
  assert.equal(artifact.semantics_adopted, false);
  assert.equal(artifact.lifecycle, LIFECYCLE);
  assert.deepEqual(
    artifact.variants.map((variant) => variant.variant_id),
    EXPECTED_VARIANT_IDS,
  );
  for (const variant of artifact.variants) assert.equal(variant.adopted, false);
});

test("every source binding is tracked, exists, is repository-relative and hash-matches", () => {
  const artifact = JSON.parse(doc);
  assert.deepEqual(
    artifact.source_bindings.map((binding) => binding.path),
    EXPECTED_BINDINGS,
    "the six frozen inputs must be bound in order",
  );
  for (const binding of artifact.source_bindings) {
    assert.ok(repoExists(binding.path), `${binding.path} must exist`);
    assert.ok(isTracked(binding.path), `${binding.path} must be tracked`);
    assert.ok(!isForbiddenPath(binding.path), `${binding.path} must be repository-relative`);
    assert.ok(isNonEmptyString(binding.section), `${binding.path} must name a section`);
    assert.equal(binding.sha256, sha256(binding.path), `${binding.path} hash must match the live file`);
  }
  assert.equal(worktreeDelta(EXPECTED_BINDINGS), "", "frozen inputs must have no worktree delta");
});

test("every variant declares N to M cardinality on both sides with a policy", () => {
  const artifact = JSON.parse(doc);
  for (const variant of artifact.variants) {
    const cardinality = variant.provenance_cardinality;
    assert.equal(cardinality.provision_to_rule.min, 0, `${variant.variant_id}: min 0 expected`);
    assert.equal(cardinality.provision_to_rule.max, "N", `${variant.variant_id}: unbounded N expected`);
    assert.ok(
      isNonEmptyString(cardinality.provision_to_rule.unknown_policy),
      `${variant.variant_id}: unknown_policy expected`,
    );
    assert.equal(cardinality.rule_to_provision.min, 1, `${variant.variant_id}: min 1 expected`);
    assert.equal(cardinality.rule_to_provision.max, "M", `${variant.variant_id}: unbounded M expected`);
    assert.ok(
      isNonEmptyString(cardinality.rule_to_provision.unresolved_policy),
      `${variant.variant_id}: unresolved_policy expected`,
    );
  }
});

test("every variant separates or collapses all eight families exactly once", () => {
  const artifact = JSON.parse(doc);
  for (const variant of artifact.variants) {
    const union = [...variant.separates, ...variant.collapses];
    assert.deepEqual(
      [...new Set(union)].sort(),
      [...CLOSED_FAMILIES].sort(),
      `${variant.variant_id}: separated and collapsed families must cover the closed eight`,
    );
    assert.equal(
      union.length,
      new Set(union).size,
      `${variant.variant_id}: no family may be both separated and collapsed`,
    );
    for (const familyId of union) {
      assert.ok(CLOSED_FAMILIES.includes(familyId), `${variant.variant_id}: unknown family ${familyId}`);
    }
  }
});

test("every variant names a collapse risk, cannot-prove set and section 3 terms", () => {
  const artifact = JSON.parse(doc);
  for (const variant of artifact.variants) {
    assert.ok(variant.collapse_risks.length >= 1, `${variant.variant_id}: collapse risk expected`);
    assert.ok(
      variant.what_it_cannot_prove.length >= 2,
      `${variant.variant_id}: at least two cannot-prove entries expected`,
    );
    assert.ok(
      variant.what_it_cannot_prove.join(" ").toLowerCase().includes("legal correctness"),
      `${variant.variant_id}: cannot-prove must include legal correctness`,
    );
    for (const term of variant.required_new_adr_terms) {
      assert.ok(
        SECTION3_DEFERRED_TERMS.includes(term),
        `${variant.variant_id}: ${term} is not a section 3 deferred term`,
      );
    }
    if (variant.required_new_adr_terms.length === 0) {
      assert.ok(
        isNonEmptyString(variant.required_new_adr_terms_note),
        `${variant.variant_id}: an empty term list needs a rationale note`,
      );
    }
  }
  const abstention = artifact.variants.find(
    (variant) => variant.variant_id === "abstention_first_candidates_only",
  );
  assert.deepEqual(
    abstention.required_new_adr_terms,
    [],
    "the abstention-first variant must list no new section 3 term",
  );
});

test("the provenance contract carries the link form and all four rules", () => {
  const artifact = JSON.parse(doc);
  const contract = artifact.provenance_contract;
  assert.deepEqual(
    [...contract.rules.map((rule) => rule.rule_id)].sort(),
    [...PROVENANCE_RULE_IDS].sort(),
  );
  const guard = contract.rules.find((rule) => rule.rule_id === CARDINALITY_GUARD_RULE);
  assert.equal(guard.code, "cardinality_collapsed");
  assert.deepEqual(contract.link_record_form.verdict_domain, VERDICT_DOMAIN);
  for (const field of ["from", "to", "family"]) {
    assert.ok(isNonEmptyString(contract.link_record_form[field]), `link form ${field} expected`);
  }
  assert.deepEqual(
    contract.link_record_form.evidence_class_domain,
    EVIDENCE_CLASSES,
    "the link form must declare the closed evidence-class domain",
  );
  for (const field of ["path", "span", "sha256"]) {
    assert.ok(
      isNonEmptyString(contract.link_record_form.source_anchor[field]),
      `link form source_anchor.${field} expected`,
    );
  }
});

test("the decision question names all three alternatives and prefills no consent", () => {
  const artifact = JSON.parse(doc);
  const decision = artifact.decision_question;
  for (const variantId of EXPECTED_VARIANT_IDS) {
    assert.ok(decision.question.includes(variantId), `question must name ${variantId}`);
  }
  const options = decision.options.join(" ").toLowerCase();
  assert.ok(options.includes("reject"), "a reject option is required");
  assert.ok(options.includes("defer"), "a defer option is required");
  assert.equal(decision.no_prefilled_consent, true);
  assert.equal(decision.not_an_acceptance_of_semantics, true);
  assert.equal(decision.asked_of, "human owner");
});

test("the recommendation is advisory, single and matched by its summary", () => {
  const artifact = JSON.parse(doc);
  const marked = artifact.variants.filter((variant) => variant.recommendation.recommended === true);
  assert.equal(marked.length, 1, "exactly one variant may be recommended");
  assert.equal(artifact.recommendation_summary.recommended_variant_id, marked[0].variant_id);
  assert.equal(artifact.recommendation_summary.is_recommendation_only, true);
  assert.equal(artifact.recommendation_summary.not_an_acceptance, true);
  for (const variant of artifact.variants) {
    assert.equal(variant.recommendation.advisory_only, true);
    assert.equal(variant.recommendation.not_an_acceptance, true);
  }
});

test("no runtime marker appears in the artifact or its companion", () => {
  assert.deepEqual(runtimeMarkersIn(doc), [], "artifact must not claim runtime");
  assert.deepEqual(runtimeMarkersIn(liveCompanion), [], "companion must not claim runtime");
  for (const section of [
    "## Variants",
    "## N to M provenance cardinality",
    "## Provenance contract rules",
    "## Decision question",
    "## Not an adoption of semantics",
    "## Fail-closed codes",
  ]) {
    assert.ok(liveCompanion.includes(section), `companion must carry '${section}'`);
  }
});

test("the documented fail-closed code set equals the emittable set", () => {
  const artifact = JSON.parse(doc);
  assert.deepEqual(
    [...artifact.fail_closed_codes].sort(),
    [...EMITTABLE_CODES].sort(),
    "the artifact must declare exactly the emittable code set",
  );
  assert.deepEqual(
    companionDocumentedCodes(liveCompanion).sort(),
    [...EMITTABLE_CODES].sort(),
    "the companion must document exactly the emittable code set",
  );
});

// ---------------------------------------------------------------------------
// negative tests (one per documented code, plus the boundary edges)
// ---------------------------------------------------------------------------

test("negative: too few, duplicated or incomplete alternatives are refused", () => {
  expectCode(
    fixture((artifact) => artifact.variants.pop()),
    "variant_count_insufficient",
  );
  expectCode(
    fixture((artifact) => artifact.variants.splice(1, 1)),
    "variant_count_insufficient",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[1].variant_id = artifact.variants[0].variant_id;
    }),
    "variant_id_duplicated",
  );
  expectCode(
    fixture((artifact) => {
      delete artifact.variants[0].representation_shape;
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[1].what_it_cannot_prove = ["It proves nothing."];
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].collapses = ["obligation"];
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].separates = ["obligation"];
      artifact.variants[0].collapses = [];
    }),
    "missing_required_field",
  );
});

test("negative: a non N-to-M or collapsed cardinality is refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].provenance_cardinality.provision_to_rule.max = 1;
    }),
    "cardinality_not_nm",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].provenance_cardinality.rule_to_provision.max = 3;
    }),
    "cardinality_not_nm",
  );
  expectCode(
    fixture((artifact) => {
      delete artifact.variants[1].provenance_cardinality.rule_to_provision.unresolved_policy;
    }),
    "cardinality_not_nm",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[2].provenance_cardinality.provision_to_rule.min = 1;
    }),
    "cardinality_not_nm",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].cardinality_collapse_allowed = true;
    }),
    "cardinality_collapsed",
  );
  expectCode(
    fixture((artifact) => {
      artifact.provenance_contract.rules = artifact.provenance_contract.rules.filter(
        (rule) => rule.rule_id !== CARDINALITY_GUARD_RULE,
      );
    }),
    "cardinality_collapsed",
  );
});

test("negative: adoption, semantics and missing non-claims are refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].adopted = true;
    }),
    "adoption_claim",
  );
  expectCode(
    fixture((artifact) => {
      artifact.authoritative = true;
    }),
    "adoption_claim",
  );
  expectCode(
    fixture((artifact) => {
      artifact.semantics_adopted = true;
    }),
    "semantics_adopted_claim",
  );
  expectCode(
    fixture((artifact) => {
      artifact.non_claims = [];
    }),
    "non_claims_missing",
  );
  expectCode(
    fixture((artifact) => {
      artifact.provenance_contract.link_record_form.non_claims = [];
    }),
    "non_claims_missing",
  );
  expectCode(
    fixture((artifact) => {
      artifact.non_claims = ["Nothing to see."];
    }),
    "non_claims_missing",
  );
});

test("negative: missing collapse risks and unlisted deferred terms are refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.variants[1].collapse_risks = [];
    }),
    "collapse_risk_missing",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].required_new_adr_terms = ["NormativeFacet"];
    }),
    "deferred_term_unlisted",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[2].required_new_adr_terms_note = "";
    }),
    "deferred_term_unlisted",
  );
});

test("negative: an unresolved or forged source binding is refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.source_bindings[1].sha256 = "0".repeat(64);
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.source_bindings[1].path = ".gsd/normative-ir-alternatives.json";
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.source_bindings[1].path = "tmp/ghost.md";
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.source_bindings.pop();
    }),
    "missing_required_field",
  );
  expectCode(doc, "missing_required_field", { frozenDelta: ` M ${EXPECTED_BINDINGS[1]}` });
});

test("negative: a drifted decision question or recommendation summary is refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.decision_question.question = "Should we proceed?";
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.decision_question.options = ["adopt A", "adopt B", "adopt C"];
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.decision_question.no_prefilled_consent = false;
    }),
    "adoption_claim",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].recommendation.recommended = true;
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].recommendation.advisory_only = false;
    }),
    "adoption_claim",
  );
});

test("negative: a claimed lifecycle, kind drift and a non-proposed status are refused", () => {
  expectCode(
    fixture((artifact) => {
      artifact.lifecycle = "[bounded]";
    }),
    "adoption_claim",
  );
  expectCode(
    fixture((artifact) => {
      artifact.kind = "m210-s01-normative-ir";
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.fail_closed_codes = ["variant_count_insufficient"];
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.variants[0].compatibility_with_existing_vocab = "";
    }),
    "missing_required_field",
  );
  expectCode(
    fixture((artifact) => {
      artifact.provenance_contract.link_record_form.evidence_class_domain = ["runtime-proven"];
    }),
    "missing_required_field",
  );
});

test("negative: a runtime marker in the artifact or companion is refused", () => {
  const withMarker = doc.replace(
    '"revision_policy":"',
    '"runtime_note":"pub struct RuleRecord","revision_policy":"',
  );
  assert.notEqual(withMarker, doc, "the marker mutation must change the artifact");
  assert.ok(runtimeMarkersIn(withMarker).length > 0, "the mutation must be visible to the marker probe");
  expectCode(withMarker, "missing_required_field");
  assert.ok(
    runtimeMarkersIn(`${liveCompanion}\n\npub fn mint_rule() {}\n`).length > 0,
    "the companion probe must detect a runtime marker",
  );
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
    code: "variant_count_insufficient",
    mutate: (artifact) => {
      artifact.variants.pop();
    },
  },
  {
    code: "variant_id_duplicated",
    mutate: (artifact) => {
      artifact.variants[1].variant_id = artifact.variants[0].variant_id;
    },
  },
  {
    code: "missing_required_field",
    mutate: (artifact) => {
      delete artifact.variants[0].representation_shape;
    },
  },
  {
    code: "cardinality_not_nm",
    mutate: (artifact) => {
      artifact.variants[0].provenance_cardinality.provision_to_rule.max = 1;
    },
  },
  {
    code: "cardinality_collapsed",
    mutate: (artifact) => {
      artifact.variants[0].cardinality_collapse_allowed = true;
    },
  },
  {
    code: "adoption_claim",
    mutate: (artifact) => {
      artifact.variants[0].adopted = true;
    },
  },
  {
    code: "semantics_adopted_claim",
    mutate: (artifact) => {
      artifact.semantics_adopted = true;
    },
  },
  {
    code: "collapse_risk_missing",
    mutate: (artifact) => {
      artifact.variants[1].collapse_risks = [];
    },
  },
  {
    code: "deferred_term_unlisted",
    mutate: (artifact) => {
      artifact.variants[0].required_new_adr_terms = ["NormativeFacet"];
    },
  },
  {
    code: "non_claims_missing",
    mutate: (artifact) => {
      artifact.non_claims = [];
    },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const artifact = clone();
    entry.mutate(artifact);
    const text = JSON.stringify(artifact);
    assert.notEqual(text, doc, `${entry.code}: the mutation must actually change the artifact`);
    const result = validateAlternatives(text);
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
// markers (emitted only after the contract holds)
// ---------------------------------------------------------------------------

test("M210 S01 IR alternatives markers", () => {
  const result = validateAlternatives(doc);
  assert.deepEqual(result.errors, [], `artifact errors: ${JSON.stringify(result.errors)}`);
  const artifact = JSON.parse(doc);
  assert.equal(artifact.semantics_adopted, false);
  assert.equal(artifact.variants.length, 3);
  assert.equal(artifact.fail_closed_codes.length, EMITTABLE_CODES.length);
  assert.ok(repoExists(COMPANION), "the companion must exist next to the artifact");
  console.log("M210_S01_IR_ALTERNATIVES_OK");
  console.log(`variants=${artifact.variants.length}`);
  console.log(`families=${CLOSED_FAMILIES.length}`);
  console.log(`provenance_rules=${PROVENANCE_RULE_IDS.length}`);
  console.log(`fail_closed_codes=${EMITTABLE_CODES.length}`);
});
