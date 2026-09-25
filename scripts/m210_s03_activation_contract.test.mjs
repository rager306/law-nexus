// M210-3afp79 S03 T04 gated runtime-activation delta contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s03-runtime-activation-delta.json, the gated activation
// delta for the conditional bounded semantic runtime. The claim under test is
// that the bounded candidate-layer grant is recorded (grant_recorded true,
// grant_scope candidate_layer_only) while the delta stays applied false, that
// the grant is never read as implementation or readiness, that the sanctioned
// stop stays active outside the adopted candidate layer, and that activation is
// named as ordered steps with owners plus a closed argv whitelist of
// repository-relative scripts.
//
// The delta is a design-only record: it mints no runtime surface, it activates
// no variant and it promotes nothing. Applying it without the adopted layer
// actually implemented and without a green battery is delta_applied_without_grant.
// The activation_commands list is validated as argv arrays, never as shell
// strings, so the latent command-injection surface named by the slice threat
// surface (Q3) is closed by construction: no argv element may carry a shell
// metacharacter or a whitespace character, argv[0] must be node, exactly one
// scripts/ path is admissible per command and it must be inside a closed
// whitelist.
//
// This contract spawns one subprocess on load, `git ls-files`, for the
// tracked-file proof. It opens no socket, runs no cargo, reads only
// repository-relative tracked artifacts under prd/, doc/ and scripts/, and
// never writes a file.
//
// Run: node --test scripts/m210_s03_activation_contract.test.mjs

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SELF_PATH = fileURLToPath(import.meta.url);

// The complete fail-closed code set. The block below is asserted to document
// exactly this set (no more, no less), and the same set is asserted equal to
// the artifact's declared `fail_closed_codes`.
// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// activation_step_missing: an activation step or command is missing its id, owner, requirement, evidence, argv or expected marker, names an inadmissible argv, a duplicate id, a non-whitelisted script, a missing tracked script or an out-of-order step.
// activation_without_owner_ref: activation is declared without a required interactive owner reference whose accepted forms are the closed two-element set.
// activation_without_regression_battery: the regression battery roles or the green_regression_battery step with command references are absent.
// activation_without_semantics_contract: the delta does not bind the byte-live semantics contract path and sha256.
// delta_applied_without_grant: the delta is applied, the grant is not recorded, the application prerequisites are not both required, or a conditional variant is activated while the delta stays unapplied.
// grant_read_as_implementation: the grant is read as implementation or readiness, or a not-yet-applied step is marked satisfied by the grant.
// implementation_fabricated: the grant claims the runtime implementation exists, or a runtime surface is declared created.
// non_ascii_artifact: the artifact carries a non-ASCII byte.
// out_of_scope_activation: an out-of-scope surface is activated, the out-of-scope set differs, or the adopted variant is absent or not marked adopted.
// raw_text_leak: the artifact carries an XML tag or a provider text marker.
// readiness_fabricated: readiness is claimed while the adopted layer is not implemented.
// resume_condition_missing: the resume condition is absent or does not name the v2 checkpoint and its authenticated refs.
// runtime_claim_present: the artifact carries a Rust implementation marker, or a declared runtime surface exists on disk.
// runtime_demo_claimed: runtime_demo is not not-proven.
// runtime_stop_blanket_lifted: the stop is not sanctioned, blanket_lifted is not false, or the still-active surfaces are absent.
// DOCUMENTED_CODES_END

const DELTA_REL = "prd/architecture/m210-s03-runtime-activation-delta.json";
const CHECKPOINT_REL = "prd/architecture/m210-s03-runtime-admission.md";
const SEMANTICS_REL = "prd/architecture/m210-s03-bounded-semantics-contract.json";
const START_GATE_REL = "prd/architecture/m210-s03-start-gate.json";
const IR_ALTERNATIVES_REL = "prd/architecture/m210-s01-ir-alternatives.json";
const SECTION3_REL = "prd/temporal-legal-model.md";

const SCHEMA = "law-nexus/m210-s03-runtime-activation-delta/v2";
const KIND = "m210-s03-runtime-activation-delta";
const MILESTONE = "M210-3afp79";
const SLICE = "S03";
const TASK = "T04";
const LIFECYCLE = ["proposed"];
const REQUIREMENT_REFS = ["RC28-F18", "R074"];
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
const VERDICT_PATTERN = /^\*\*admission: (granted|not-adopted)\*\*$/gm;
const VERDICT_LINE_PATTERN = /^\*\*admission: (granted|not-adopted)\*\*$/m;

const CHECKPOINT_V2 = "prd/architecture/m210-s02-adoption-checkpoint-v2.md";
const ADOPTED_VARIANT = "abstention_first_candidates_only";
const IR_CRITERION = "subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f";
const F13_CRITERION = "subjective-UAT criterion 70e39300-851b-4412-a322-a8f0c51ca71c";
const ADOPTED_CONSTRUCT_SET = [
  "candidate_emission",
  "source_anchors",
  "family_classification_hypotheses",
  "unknown_verdict",
  "conflict_verdict",
  "provenance_links",
];

const EMITTABLE_CODES = [
  "activation_step_missing",
  "activation_without_owner_ref",
  "activation_without_regression_battery",
  "activation_without_semantics_contract",
  "delta_applied_without_grant",
  "grant_read_as_implementation",
  "implementation_fabricated",
  "non_ascii_artifact",
  "out_of_scope_activation",
  "raw_text_leak",
  "readiness_fabricated",
  "resume_condition_missing",
  "runtime_claim_present",
  "runtime_demo_claimed",
  "runtime_stop_blanket_lifted",
];

const REQUIRED_STEPS = [
  "actual_candidate_layer_implementation",
  "named_adopted_construct_set_from_v2",
  "rebind_inputs_by_live_sha256",
  "green_regression_battery",
  "separate_decision_for_composed_rule_applicability_section3",
];

const REQUIRED_COMMAND_ROLES = [
  "slice_battery",
  "regression_s01",
  "regression_s02",
  "regression_m209_s04",
  "source_revision",
];

const REGRESSION_ROLES = ["regression_s01", "regression_s02", "regression_m209_s04"];

const ACCEPTED_FORMS = ["authenticated_subjective_uat_criterion_id", "owner_interaction_id_with_timestamp"];

const REJECTED_AS_GRANTOR = [
  "bare_name",
  "role_title",
  "gsd_milestone_lock",
  "adr_status",
  "integrity_pass",
  "battery_pass",
  "milestone_closeout",
];

const COMMAND_WHITELIST = new Set([
  "scripts/m210_s03_slice_battery.mjs",
  "scripts/m210_s01_slice_battery.mjs",
  "scripts/m210_s02_slice_battery.mjs",
  "scripts/m209_s04_slice_battery.mjs",
  "scripts/m204_s08_source_revision.mjs",
]);

const OUT_OF_SCOPE = ["Applicable", "RuVector", "TEI", "F13 operation grammar"];
const STILL_ACTIVE_FOR = ["composed-rule runtime", "applicability runtime", "section 3 promotion"];

const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl ", "#[test]", "fn main"];
const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const FORBIDDEN_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

const FORBIDDEN_ARGV_CHARS = new Set([
  " ",
  "\t",
  "\r",
  "\n",
  ";",
  "&",
  "|",
  "<",
  ">",
  "$",
  "`",
  "\\",
  "'",
  '"',
  "*",
  "?",
  "(",
  ")",
  "{",
  "}",
  "[",
  "]",
  "!",
  "~",
  "#",
]);

const NON_CLAIM_FRAGMENTS = [
  "grant is recorded, not applied",
  "grant is not implementation",
  "grant is not readiness",
  "runtime_demo stays not-proven",
  "runtime_stop stays active",
  "v2 checkpoint",
  "not a decision",
  "out-of-scope",
  "no crate is touched",
  "whitelist",
];

// ---------------------------------------------------------------------------
// repository helpers
// ---------------------------------------------------------------------------

const TRACKED = new Set(
  execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
    .split("\n")
    .filter((line) => line.length > 0),
);

function readRepo(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function sha256Repo(relativePath) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex")}`;
}

function isRepoRelative(value) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    !path.isAbsolute(value) &&
    !value.includes("..") &&
    !FORBIDDEN_PREFIXES.some((prefix) => value.startsWith(prefix))
  );
}

function sameSet(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
  const sortedLeft = [...left].sort();
  const sortedRight = [...right].sort();
  return sortedLeft.every((value, index) => value === sortedRight[index]);
}

function codesOf(result) {
  return [...new Set(result.errors.map((error) => error.name))];
}

// ---------------------------------------------------------------------------
// live surfaces
// ---------------------------------------------------------------------------

const LIVE_DOC = readRepo(DELTA_REL);
const LIVE_DELTA = JSON.parse(LIVE_DOC);
const CHECKPOINT_TEXT = readRepo(CHECKPOINT_REL);
const START_GATE = JSON.parse(readRepo(START_GATE_REL));
const IR_ALTERNATIVES = JSON.parse(readRepo(IR_ALTERNATIVES_REL));

const verdictMatches = CHECKPOINT_TEXT.match(VERDICT_PATTERN) || [];
const VERDICT = verdictMatches.length === 1 ? verdictMatches[0].replace("**admission: ", "").replace("**", "") : null;

const LIVE_ENV = {
  text: LIVE_DOC,
  verdict: VERDICT,
  semanticsSha: sha256Repo(SEMANTICS_REL),
  tracked: TRACKED,
};

function envFor(delta) {
  return { ...LIVE_ENV, text: JSON.stringify(delta) };
}

// ---------------------------------------------------------------------------
// the fail-closed validator
// ---------------------------------------------------------------------------

function validateDelta(delta, env) {
  const errors = [];
  const add = (name, detail) => errors.push({ name, detail });
  const text = typeof env.text === "string" ? env.text : "";

  // hygiene: ASCII only, no raw text, no Rust runtime marker.
  if (!/^[\x00-\x7f]*$/.test(text)) add("non_ascii_artifact", "the artifact carries a non-ASCII byte");
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) add("raw_text_leak", `raw text marker: ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) add("runtime_claim_present", `runtime marker: ${marker}`);
  }

  // the gate: a recorded bounded grant that stays unapplied and is never read as implementation.
  const gate = delta?.gate ?? {};
  if (gate.grant_recorded !== true) add("delta_applied_without_grant", "the bounded grant is not recorded");
  if (gate.applied !== false) add("delta_applied_without_grant", `applied=${JSON.stringify(gate.applied)}`);
  if (gate.applied_requires_implementation !== true || gate.applied_requires_green_battery !== true) {
    add("delta_applied_without_grant", "the application prerequisites are not both required");
  }
  if (gate.grant_is_not_implementation !== true || gate.grant_is_not_readiness !== true) {
    add("grant_read_as_implementation", "the grant is read as implementation or readiness");
  }
  if (gate.implementation_present !== false) {
    add("implementation_fabricated", `implementation_present=${JSON.stringify(gate.implementation_present)}`);
  }
  if (gate.readiness !== "not-ready") add("readiness_fabricated", `readiness=${JSON.stringify(gate.readiness)}`);

  // the sanctioned stop, scoped to the candidate layer.
  const stop = delta?.stop ?? {};
  if (stop.sanctioned !== true) add("runtime_stop_blanket_lifted", "the stop is not sanctioned");
  if (stop.runtime_demo !== "not-proven") add("runtime_demo_claimed", `runtime_demo=${JSON.stringify(stop.runtime_demo)}`);
  if (
    stop.runtime_stop !== "active_outside_candidate_layer" ||
    stop.blanket_lifted !== false ||
    !Array.isArray(stop.still_active_for) ||
    stop.still_active_for.length === 0
  ) {
    add(
      "runtime_stop_blanket_lifted",
      `runtime_stop=${JSON.stringify(stop.runtime_stop)} blanket_lifted=${JSON.stringify(stop.blanket_lifted)}`,
    );
  }

  // the resume condition names the v2 checkpoint and its authenticated refs.
  const resume = stop?.resume_condition;
  if (
    !resume ||
    resume.present !== true ||
    resume.names_v2 !== true ||
    resume.names_checkpoint_v2 !== CHECKPOINT_V2 ||
    !Array.isArray(resume.authenticated_refs) ||
    resume.authenticated_refs.length === 0
  ) {
    add("resume_condition_missing", "the resume condition is absent or does not name the v2 checkpoint and its refs");
  }

  // the activation steps: named, owned, ordered and never satisfied by the grant.
  const steps = Array.isArray(delta?.activation_requires) ? delta.activation_requires : [];
  const stepIds = steps.map((step) => step?.step_id);
  if (steps.length !== REQUIRED_STEPS.length) add("activation_step_missing", `activation_requires carries ${steps.length} steps`);
  if (new Set(stepIds).size !== stepIds.length) add("activation_step_missing", "duplicate step_id");
  for (const required of REQUIRED_STEPS) {
    if (!stepIds.includes(required)) add("activation_step_missing", `missing step ${required}`);
  }
  steps.forEach((step, index) => {
    if (typeof step?.step_id !== "string" || step.step_id === "") {
      add("activation_step_missing", "a step carries no step_id");
    }
    if (step?.order !== index + 1) add("activation_step_missing", `step ${String(step?.step_id)} is out of order`);
    if (typeof step?.owner !== "string" || step.owner === "") {
      add("activation_step_missing", `a step carries no owner: ${String(step?.step_id)}`);
    }
    if (typeof step?.requires !== "string" || step.requires === "") {
      add("activation_step_missing", `a step carries no requirement: ${String(step?.step_id)}`);
    }
    if (typeof step?.evidence !== "string" || step.evidence === "") {
      add("activation_step_missing", `a step carries no evidence: ${String(step?.step_id)}`);
    }
    if (step?.satisfied_now !== false) {
      add("grant_read_as_implementation", `step ${String(step?.step_id)} is read as satisfied by the grant`);
    }
  });

  // activation without an interactive owner reference.
  const ownerStep = steps.find((step) => step?.step_id === "separate_decision_for_composed_rule_applicability_section3");
  if (!ownerStep) {
    add("activation_without_owner_ref", "no separate_decision step");
  } else {
    const ref = ownerStep.interactive_ref;
    if (!ref || ref.required !== true) {
      add("activation_without_owner_ref", "the separate_decision step does not require an interactive reference");
    } else if (!sameSet(ref.accepted_forms, ACCEPTED_FORMS)) {
      add(
        "activation_without_owner_ref",
        `accepted_forms=${JSON.stringify(ref.accepted_forms)}`,
      );
    } else if (!sameSet(ref.rejected_as_grantor, REJECTED_AS_GRANTOR)) {
      add(
        "activation_without_owner_ref",
        `rejected_as_grantor=${JSON.stringify(ref.rejected_as_grantor)}`,
      );
    }
  }

  // activation without the byte-live semantics contract.
  const semantics = delta?.semantics_contract;
  if (!semantics || typeof semantics.path !== "string" || typeof semantics.sha256 !== "string") {
    add("activation_without_semantics_contract", "no semantics contract binding");
  } else if (!env.tracked.has(semantics.path)) {
    add("activation_without_semantics_contract", `the semantics contract is not tracked: ${semantics.path}`);
  } else if (semantics.sha256 !== env.semanticsSha) {
    add("activation_without_semantics_contract", "the semantics contract digest does not match the live bytes");
  }

  // the activation commands: a closed argv whitelist and a green regression battery.
  const commands = Array.isArray(delta?.activation_commands) ? delta.activation_commands : [];
  const roles = commands.map((command) => command?.role);
  for (const role of REGRESSION_ROLES) {
    if (!roles.includes(role)) add("activation_without_regression_battery", `missing command role ${role}`);
  }
  const green = steps.find((step) => step?.step_id === "green_regression_battery");
  if (!green || !Array.isArray(green.command_refs) || green.command_refs.length === 0) {
    add("activation_without_regression_battery", "no green_regression_battery step with command references");
  }
  const commandIds = commands.map((command) => command?.command_id);
  if (new Set(commandIds).size !== commandIds.length) add("activation_step_missing", "duplicate command_id");
  const declaredScripts = new Set();
  for (const command of commands) {
    if (typeof command?.command_id !== "string" || command.command_id === "") {
      add("activation_step_missing", "a command carries no command_id");
    }
    if (typeof command?.owner !== "string" || command.owner === "") {
      add("activation_step_missing", `a command carries no owner: ${String(command?.command_id)}`);
    }
    if (typeof command?.role !== "string" || command.role === "") {
      add("activation_step_missing", `a command carries no role: ${String(command?.command_id)}`);
    }
    if (typeof command?.expected_marker !== "string" || command.expected_marker === "") {
      add("activation_step_missing", `a command carries no expected marker: ${String(command?.command_id)}`);
    }
    const argv = command?.argv;
    if (!Array.isArray(argv) || argv.length === 0) {
      add("activation_step_missing", `a command carries no argv: ${String(command?.command_id)}`);
      continue;
    }
    if (argv[0] !== "node") add("activation_step_missing", `argv[0] must be node: ${String(command?.command_id)}`);
    for (const element of argv) {
      if (typeof element !== "string" || element === "") {
        add("activation_step_missing", `an argv element is not a non-empty string: ${String(command?.command_id)}`);
      } else if ([...element].some((character) => FORBIDDEN_ARGV_CHARS.has(character))) {
        add("activation_step_missing", `an argv element carries a shell metacharacter: ${element}`);
      }
    }
    for (const element of argv.slice(2)) {
      if (typeof element === "string" && !/^--[a-z][a-z0-9-]*$/.test(element)) {
        add("activation_step_missing", `inadmissible argv tail: ${element}`);
      }
    }
    const scriptPaths = argv.filter((element) => typeof element === "string" && element.startsWith("scripts/"));
    if (scriptPaths.length !== 1) {
      add("activation_step_missing", `a command must name exactly one scripts/ path: ${String(command?.command_id)}`);
      continue;
    }
    const scriptPath = scriptPaths[0];
    if (!isRepoRelative(scriptPath) || !scriptPath.startsWith("scripts/") || !scriptPath.endsWith(".mjs")) {
      add("activation_step_missing", `a command names a non-repository-relative script: ${scriptPath}`);
      continue;
    }
    if (!COMMAND_WHITELIST.has(scriptPath)) {
      add("activation_step_missing", `a command names a non-whitelisted script: ${scriptPath}`);
      continue;
    }
    declaredScripts.add(scriptPath);
    if (command.created_by === "existing") {
      if (!env.tracked.has(scriptPath)) add("activation_step_missing", `a command script is not tracked: ${scriptPath}`);
      else if (!existsSync(path.join(root, scriptPath))) {
        add("activation_step_missing", `a command script is absent: ${scriptPath}`);
      }
    } else if (command.created_by !== "T05") {
      add("activation_step_missing", `a command carries an inadmissible created_by: ${String(command.created_by)}`);
    }
  }
  for (const required of COMMAND_WHITELIST) {
    if (!declaredScripts.has(required)) {
      add("activation_without_regression_battery", `missing activation command ${required}`);
    }
  }

  // out-of-scope surfaces stay inactive and the adopted variant is marked adopted.
  const outOfScope = Array.isArray(delta?.out_of_scope_surfaces) ? delta.out_of_scope_surfaces : [];
  if (outOfScope.length === 0) add("out_of_scope_activation", "no out_of_scope_surfaces declared");
  for (const surface of outOfScope) {
    if (surface?.activated !== false) {
      add("out_of_scope_activation", `out-of-scope surface activated: ${String(surface?.name)}`);
    }
  }
  if (!sameSet(outOfScope.map((surface) => surface?.name), OUT_OF_SCOPE)) {
    add("out_of_scope_activation", "the out-of-scope surface set differs from the declared closed set");
  }
  const variants = delta?.conditional_surfaces_by_variant ?? {};
  for (const key of Object.keys(variants)) {
    const variant = variants[key];
    if (variant?.activated !== false || variant?.activated_in_this_slice !== false) {
      add("delta_applied_without_grant", `variant ${key} is activated while the delta stays unapplied`);
    }
  }
  const adopted = variants[ADOPTED_VARIANT];
  if (!adopted || adopted.adopted !== true) {
    add("out_of_scope_activation", "the adopted variant is absent or not marked adopted");
  }

  // no runtime surface may be created or exist.
  const surfaces = Array.isArray(delta?.runtime_surfaces_to_create) ? delta.runtime_surfaces_to_create : [];
  for (const surface of surfaces) {
    if (surface?.created !== false) {
      add("implementation_fabricated", `runtime surface declared created: ${String(surface?.path)}`);
    }
    if (typeof surface?.path === "string" && existsSync(path.join(root, surface.path))) {
      add("runtime_claim_present", `runtime surface exists on disk: ${surface.path}`);
    }
  }

  return { ok: errors.length === 0, errors };
}

function clone() {
  return JSON.parse(LIVE_DOC);
}

function expectCode(mutate, code) {
  const delta = clone();
  mutate(delta);
  const result = validateDelta(delta, envFor(delta));
  assert.ok(codesOf(result).includes(code), `expected ${code}, got ${JSON.stringify(result.errors)}`);
  assert.equal(result.ok, false, `${code} must fail closed`);
}

function resumeSection(text) {
  const match = text.match(/## Resume condition\n([\s\S]*?)(?:\n## |\n$)/);
  return match ? match[1] : null;
}

// ---------------------------------------------------------------------------
// positive: form, identity and hygiene
// ---------------------------------------------------------------------------

test("the delta exists, is canonical compact ASCII and carries no raw text", () => {
  assert.ok(existsSync(path.join(root, DELTA_REL)), `${DELTA_REL} must exist`);
  assert.ok(LIVE_DOC.length > 0, "the delta must be non-empty");
  assert.ok(LIVE_DOC.isWellFormed(), "the delta must be well-formed UTF-8");
  assert.match(LIVE_DOC, /^[\x00-\x7f]*$/, "the delta must be pure ASCII");
  assert.ok(!LIVE_DOC.includes("\n"), "canonical bytes are a single line");
  assert.ok(!LIVE_DOC.endsWith("\n"), "canonical bytes carry no trailing newline");
  assert.equal(
    JSON.stringify(JSON.parse(LIVE_DOC)),
    LIVE_DOC,
    "the delta must round-trip to identical canonical compact bytes",
  );
  for (const marker of RAW_TEXT_MARKERS) {
    assert.ok(!LIVE_DOC.includes(marker), `the delta must not carry ${marker}`);
  }
  assert.ok(!/[\u0400-\u04ff]/.test(LIVE_DOC), "the delta must carry no Cyrillic (raw legal text)");
  for (const marker of RUNTIME_MARKERS) {
    assert.ok(!LIVE_DOC.includes(marker), `the delta must not claim the runtime marker ${marker}`);
  }
});

test("the envelope is the declared bounded activation delta", () => {
  assert.equal(LIVE_DELTA.schema, SCHEMA);
  assert.equal(LIVE_DELTA.schema_version, 2);
  assert.equal(LIVE_DELTA.kind, KIND);
  assert.equal(LIVE_DELTA.milestone, MILESTONE);
  assert.equal(LIVE_DELTA.slice, SLICE);
  assert.equal(LIVE_DELTA.task, TASK);
  assert.deepEqual(LIVE_DELTA.lifecycle, LIFECYCLE);
  assert.equal(LIVE_DELTA.authoritative, false);
  assert.equal(LIVE_DELTA.ascii_only, true);
  assert.equal(LIVE_DELTA.design_only, true);
  assert.deepEqual(LIVE_DELTA.requirement_refs, REQUIREMENT_REFS);
  assert.equal(LIVE_DELTA.checkpoint_ref, CHECKPOINT_REL);
  assert.equal(LIVE_DELTA.start_gate_ref, START_GATE_REL);
  assert.match(LIVE_DELTA.source_revision, SHA_PATTERN);
  assert.ok(typeof LIVE_DELTA.originating_review === "string" && LIVE_DELTA.originating_review.length > 0);

  const admission = LIVE_DELTA.admission_ref;
  assert.equal(admission.checkpoint_v2.path, CHECKPOINT_V2);
  assert.equal(admission.checkpoint_v2.verdict, "granted");
  assert.match(admission.checkpoint_v2.sha256, SHA_PATTERN);
  assert.deepEqual(admission.checkpoint_v2.adopted_construct_set, ADOPTED_CONSTRUCT_SET);
  assert.equal(admission.checkpoint_v2.adopted_variant, "C");
  assert.match(admission.authenticated_via, /authenticated/i);
  assert.equal(admission.owner_admission_ref, IR_CRITERION);
  assert.deepEqual(admission.interaction_refs, [IR_CRITERION, F13_CRITERION]);
  assert.equal(admission.superseded_v1.checkpoint_v1, "prd/architecture/m210-s02-adoption-checkpoint.md");
  assert.equal(admission.superseded_v1.answer_v1, "prd/architecture/m210-s02-answer-record.json");
});

test("the gate records the bounded grant and stays applied false", () => {
  assert.equal(LIVE_DELTA.gate.grant_recorded, true, "the bounded grant must be recorded");
  assert.equal(LIVE_DELTA.gate.grant_scope, "candidate_layer_only");
  assert.equal(LIVE_DELTA.gate.grant_kind, "bounded_candidate_layer_admission");
  assert.ok(LIVE_DELTA.gate.grant_ref.includes("37181c25"));
  assert.equal(LIVE_DELTA.gate.applied, false, "the gate must stay applied false");
  assert.equal(LIVE_DELTA.gate.applied_requires_implementation, true);
  assert.equal(LIVE_DELTA.gate.applied_requires_green_battery, true);
  assert.equal(LIVE_DELTA.gate.grant_is_not_implementation, true, "a grant is not an implementation");
  assert.equal(LIVE_DELTA.gate.grant_is_not_readiness, true, "a grant is not readiness");
  assert.equal(LIVE_DELTA.gate.implementation_present, false);
  assert.equal(LIVE_DELTA.gate.readiness, "not-ready");
  assert.ok(typeof LIVE_DELTA.gate.reason === "string" && LIVE_DELTA.gate.reason.length > 0);

  assert.equal(LIVE_DELTA.checkpoint_verdict, "granted");

  const matches = CHECKPOINT_TEXT.match(VERDICT_PATTERN) || [];
  assert.equal(matches.length, 1, "the checkpoint must carry exactly one verdict line");
  assert.ok(VERDICT_LINE_PATTERN.test(CHECKPOINT_TEXT));
  assert.equal(VERDICT, "granted", "the live checkpoint verdict must be granted");
  assert.equal(LIVE_DELTA.checkpoint_verdict, VERDICT);
  assert.match(LIVE_DELTA.checkpoint_sha256, SHA_PATTERN);
  assert.equal(LIVE_DELTA.checkpoint_sha256, sha256Repo(CHECKPOINT_REL), "the checkpoint pin must match live bytes");

  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV), { ok: true, errors: [] });
});

test("the sanctioned stop is scoped and the resume condition names the v2 refs", () => {
  const { stop } = LIVE_DELTA;
  assert.equal(stop.sanctioned, true, "the stop must be explicitly sanctioned");
  assert.equal(stop.runtime_work, "not-started");
  assert.equal(stop.runtime_demo, "not-proven");
  assert.equal(stop.runtime_stop, "active_outside_candidate_layer");
  assert.equal(stop.blanket_lifted, false);
  assert.match(stop.lifted_for, /candidate layer/i);
  assert.deepEqual(stop.still_active_for, STILL_ACTIVE_FOR);

  const resume = stop.resume_condition;
  assert.equal(resume.present, true);
  assert.equal(resume.names_v2, true);
  assert.equal(resume.names_checkpoint_v2, CHECKPOINT_V2);
  assert.deepEqual(resume.authenticated_refs, [IR_CRITERION, F13_CRITERION]);
  assert.match(resume.source_kind, /authenticated/i);
  assert.match(resume.source_kind, /interaction id/i);
  assert.ok(typeof resume.note === "string" && resume.note.length > 0);
  assert.ok(Array.isArray(resume.resume_requires) && resume.resume_requires.length >= 4);

  const section = resumeSection(CHECKPOINT_TEXT);
  assert.ok(section, "the live checkpoint must carry a Resume condition section");
  assert.match(section, /adopted candidate layer/i, "the checkpoint resume condition must name the bounded scope");
  assert.match(section, /regression battery/i, "the checkpoint resume condition must name the green battery");

  // The granted, scoped stop is never a soft pass.
  assert.equal(LIVE_DELTA.gate.applied, false);
  assert.equal(LIVE_DELTA.gate.readiness, "not-ready");
});

test("activation is named as ordered steps with owners and an interactive owner reference", () => {
  const steps = LIVE_DELTA.activation_requires;
  assert.ok(Array.isArray(steps) && steps.length === REQUIRED_STEPS.length);
  assert.deepEqual(
    steps.map((step) => step.step_id),
    REQUIRED_STEPS,
    "the steps must carry the five required ids in order",
  );
  assert.deepEqual(steps.map((step) => step.order), [1, 2, 3, 4, 5], "the steps must be ordered");
  assert.equal(new Set(steps.map((step) => step.step_id)).size, steps.length, "step ids must be unique");
  for (const step of steps) {
    assert.ok(typeof step.owner === "string" && step.owner.length > 0, `${step.step_id} must name an owner`);
    assert.ok(typeof step.requires === "string" && step.requires.length > 0, `${step.step_id} must name what it requires`);
    assert.ok(typeof step.evidence === "string" && step.evidence.length > 0, `${step.step_id} must name its evidence`);
    assert.equal(step.satisfied_now, false, `${step.step_id} must not be read as satisfied by the grant`);
  }

  const impl = steps[0];
  assert.equal(impl.step_id, "actual_candidate_layer_implementation");
  assert.equal(impl.owner_kind, "slice", "the implementation step must belong to a separate sanctioned slice");

  const owner = steps[4];
  assert.equal(owner.step_id, "separate_decision_for_composed_rule_applicability_section3");
  assert.equal(owner.owner_kind, "human");
  assert.equal(owner.interactive_ref.required, true);
  assert.deepEqual(owner.interactive_ref.accepted_forms, ACCEPTED_FORMS);
  assert.deepEqual(owner.interactive_ref.rejected_as_grantor, REJECTED_AS_GRANTOR);

  const rebind = steps.find((step) => step.step_id === "rebind_inputs_by_live_sha256");
  assert.ok(rebind.command_refs.includes("source_revision"), "rebind_inputs must name the source-revision command");

  const green = steps.find((step) => step.step_id === "green_regression_battery");
  assert.ok(Array.isArray(green.command_refs) && green.command_refs.length > 0);
  for (const commandId of green.command_refs) {
    assert.ok(
      LIVE_DELTA.activation_commands.some((command) => command.command_id === commandId),
      `the green battery must reference a declared command: ${commandId}`,
    );
  }
});

test("the activation commands are a closed argv whitelist under scripts and resolve to tracked runners", () => {
  const commands = LIVE_DELTA.activation_commands;
  assert.ok(Array.isArray(commands) && commands.length === COMMAND_WHITELIST.size);
  assert.equal(new Set(commands.map((command) => command.command_id)).size, commands.length);
  assert.deepEqual(
    commands.map((command) => command.role).slice().sort(),
    REQUIRED_COMMAND_ROLES.slice().sort(),
    "the command roles must be exactly the declared closed set",
  );

  const declared = new Set();
  for (const command of commands) {
    assert.ok(Array.isArray(command.argv) && command.argv.length >= 2, `${command.command_id} must carry an argv array`);
    assert.equal(command.argv[0], "node");
    for (const element of command.argv) {
      assert.ok(typeof element === "string" && element.length > 0);
      assert.ok(
        ![...element].some((character) => FORBIDDEN_ARGV_CHARS.has(character)),
        `argv must not carry a shell metacharacter: ${element}`,
      );
    }
    const scripts = command.argv.filter((element) => element.startsWith("scripts/"));
    assert.equal(scripts.length, 1, `${command.command_id} must name exactly one scripts/ path`);
    assert.ok(COMMAND_WHITELIST.has(scripts[0]), `script must be whitelisted: ${scripts[0]}`);
    declared.add(scripts[0]);
    assert.ok(typeof command.owner === "string" && command.owner.length > 0);
    assert.ok(typeof command.expected_marker === "string" && command.expected_marker.length > 0);
  }
  assert.deepEqual([...declared].sort(), [...COMMAND_WHITELIST].sort());

  const pending = commands.filter((command) => command.created_by !== "existing");
  assert.equal(pending.length, 1, "exactly one activation command may be created by the slice closeout");
  const sliceBattery = commands.find((command) => command.role === "slice_battery");
  assert.equal(sliceBattery.created_by, "T05");
  assert.equal(sliceBattery.argv[1], "scripts/m210_s03_slice_battery.mjs");
  for (const command of commands) {
    const script = command.argv.find((element) => element.startsWith("scripts/"));
    if (command.created_by !== "existing") continue;
    assert.ok(TRACKED.has(script), `an existing activation command must be tracked: ${script}`);
    assert.ok(existsSync(path.join(root, script)), `an existing activation command must resolve: ${script}`);
  }
});

test("every conditional variant is inactive and bound to the live S01 variant dictionary", () => {
  const variants = LIVE_DELTA.conditional_surfaces_by_variant;
  const liveVariantIds = IR_ALTERNATIVES.variants.map((variant) => variant.variant_id);
  assert.deepEqual(
    Object.keys(variants).slice().sort(),
    [...liveVariantIds].sort(),
    "the conditional surface map must carry exactly the live S01 variants",
  );
  for (const live of IR_ALTERNATIVES.variants) {
    const entry = variants[live.variant_id];
    assert.equal(entry.variant_id, live.variant_id);
    assert.equal(entry.variant_label, live.label);
    assert.equal(entry.activated, false, `${live.variant_id} must be inactive`);
    assert.equal(entry.activated_in_this_slice, false, `${live.variant_id} activates nothing in this slice`);
    assert.deepEqual(entry.required_new_adr_terms, live.required_new_adr_terms);
    assert.deepEqual(entry.section3_terms_to_define, live.required_new_adr_terms);
    assert.equal(entry.consequences_for_S03, live.consequences_for_S03);
    assert.ok(Array.isArray(entry.would_touch) && entry.would_touch.length > 0);
    assert.ok(Array.isArray(entry.non_claims) && entry.non_claims.length >= 2);
    assert.equal(entry.adopted, live.variant_id === ADOPTED_VARIANT);
  }
  assert.equal(variants[ADOPTED_VARIANT].adopted, true);

  const surfaces = LIVE_DELTA.runtime_surfaces_to_create;
  assert.deepEqual(
    surfaces.map((surface) => surface.path),
    START_GATE.declared_absent_runtime_surfaces,
    "the runtime surfaces to create must be exactly the declared absent surfaces of the start gate",
  );
  for (const surface of surfaces) {
    assert.equal(surface.created, false, `${surface.path} must not be created`);
    assert.ok(!existsSync(path.join(root, surface.path)), `no runtime surface may exist: ${surface.path}`);
  }
});

test("the out-of-scope surfaces stay inactive and the section 3 pin is live", () => {
  assert.deepEqual(
    LIVE_DELTA.out_of_scope_surfaces.map((surface) => surface.name),
    OUT_OF_SCOPE,
  );
  for (const surface of LIVE_DELTA.out_of_scope_surfaces) {
    assert.equal(surface.activated, false, `${surface.name} must stay inactive`);
  }
  assert.equal(LIVE_DELTA.semantics_contract.path, SEMANTICS_REL);
  assert.equal(LIVE_DELTA.semantics_contract.sha256, sha256Repo(SEMANTICS_REL));
  assert.match(LIVE_DELTA.semantics_contract.sha256, SHA_PATTERN);
  assert.equal(LIVE_DELTA.semantics_contract.sha256, LIVE_ENV.semanticsSha);
  assert.equal(sha256Repo(SECTION3_REL), START_GATE.guards.section3_pin, "section 3 must stay byte-identical to its pin");
});

test("non-claims state the sanctioned stop and refuse fabrication claims", () => {
  assert.ok(Array.isArray(LIVE_DELTA.non_claims) && LIVE_DELTA.non_claims.length >= 8);
  const joined = LIVE_DELTA.non_claims.join("\n").toLowerCase();
  for (const fragment of NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment.toLowerCase()), `non-claims must state: ${fragment}`);
  }
});

test("the declared fail-closed code set matches the documented set", () => {
  assert.deepEqual(LIVE_DELTA.fail_closed_codes, EMITTABLE_CODES);
  assert.equal(new Set(LIVE_DELTA.fail_closed_codes).size, LIVE_DELTA.fail_closed_codes.length);
  assert.deepEqual(
    [...LIVE_DELTA.fail_closed_codes].sort(),
    [...LIVE_DELTA.fail_closed_codes],
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

// ---------------------------------------------------------------------------
// negative: each declared code is empirically exercised
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "activation_step_missing",
    mutate: (delta) => {
      delta.activation_requires[3].owner = "";
    },
  },
  {
    code: "activation_without_owner_ref",
    mutate: (delta) => {
      delete delta.activation_requires[4].interactive_ref;
    },
  },
  {
    code: "activation_without_regression_battery",
    mutate: (delta) => {
      delta.activation_commands = delta.activation_commands.filter((command) => command.role !== "regression_s02");
    },
  },
  {
    code: "activation_without_semantics_contract",
    mutate: (delta) => {
      delta.semantics_contract.sha256 = `sha256:${"0".repeat(64)}`;
    },
  },
  {
    code: "delta_applied_without_grant",
    mutate: (delta) => {
      delta.gate.applied = true;
    },
  },
  {
    code: "grant_read_as_implementation",
    mutate: (delta) => {
      delta.activation_requires[0].satisfied_now = true;
    },
  },
  {
    code: "implementation_fabricated",
    mutate: (delta) => {
      delta.runtime_surfaces_to_create[0].created = true;
    },
  },
  {
    code: "non_ascii_artifact",
    mutate: (delta) => {
      delta.non_claims[0] = `${delta.non_claims[0]} \u00e9`;
    },
  },
  {
    code: "out_of_scope_activation",
    mutate: (delta) => {
      delta.out_of_scope_surfaces[0].activated = true;
    },
  },
  {
    code: "raw_text_leak",
    mutate: (delta) => {
      delta.non_claims[1] = `${delta.non_claims[1]} <p>`;
    },
  },
  {
    code: "readiness_fabricated",
    mutate: (delta) => {
      delta.gate.readiness = "ready";
    },
  },
  {
    code: "resume_condition_missing",
    mutate: (delta) => {
      delta.stop.resume_condition.names_v2 = false;
    },
  },
  {
    code: "runtime_claim_present",
    mutate: (delta) => {
      delta.non_claims[2] = `${delta.non_claims[2]} pub fn activate()`;
    },
  },
  {
    code: "runtime_demo_claimed",
    mutate: (delta) => {
      delta.stop.runtime_demo = "proven";
    },
  },
  {
    code: "runtime_stop_blanket_lifted",
    mutate: (delta) => {
      delta.stop.runtime_stop = "lifted";
    },
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  const covered = new Set();
  for (const entry of CODE_COVERAGE) {
    const delta = clone();
    entry.mutate(delta);
    const text = JSON.stringify(delta);
    assert.notEqual(text, LIVE_DOC, `${entry.code}: the mutation must actually change the artifact`);
    const result = validateDelta(delta, { ...LIVE_ENV, text });
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

test("negative: an applied gate, a fabricated implementation and fabricated readiness are refused", () => {
  expectCode((delta) => {
    delta.gate.applied = true;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.gate.grant_recorded = false;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.gate.applied_requires_green_battery = false;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.gate.grant_is_not_implementation = false;
  }, "grant_read_as_implementation");
  expectCode((delta) => {
    delta.gate.implementation_present = true;
  }, "implementation_fabricated");
  expectCode((delta) => {
    delta.runtime_surfaces_to_create[0].created = true;
  }, "implementation_fabricated");
  expectCode((delta) => {
    delta.gate.readiness = "ready";
  }, "readiness_fabricated");
  expectCode((delta) => {
    delta.stop.runtime_stop = "lifted";
  }, "runtime_stop_blanket_lifted");
  expectCode((delta) => {
    delta.stop.blanket_lifted = true;
  }, "runtime_stop_blanket_lifted");
  expectCode((delta) => {
    delta.stop.still_active_for = [];
  }, "runtime_stop_blanket_lifted");
  expectCode((delta) => {
    delta.stop.runtime_demo = "proven";
  }, "runtime_demo_claimed");
  expectCode((delta) => {
    delta.conditional_surfaces_by_variant.abstention_first_candidates_only.activated = true;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.conditional_surfaces_by_variant.family_typed_record_ir.activated_in_this_slice = true;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.out_of_scope_surfaces[0].activated = true;
  }, "out_of_scope_activation");
  expectCode((delta) => {
    delta.conditional_surfaces_by_variant.abstention_first_candidates_only.adopted = false;
  }, "out_of_scope_activation");
});

test("negative: unowned activation and a red battery are refused", () => {
  expectCode((delta) => {
    delta.activation_requires[4].interactive_ref.accepted_forms = ["bare_name"];
  }, "activation_without_owner_ref");
  expectCode((delta) => {
    delta.activation_requires[4].interactive_ref.required = false;
  }, "activation_without_owner_ref");
  expectCode((delta) => {
    delta.activation_commands = delta.activation_commands.filter((command) => command.role !== "regression_m209_s04");
  }, "activation_without_regression_battery");
  expectCode((delta) => {
    delta.activation_commands = delta.activation_commands.filter((command) => command.role !== "regression_s01");
  }, "activation_without_regression_battery");
  expectCode((delta) => {
    delta.activation_requires[3].command_refs = [];
  }, "activation_without_regression_battery");
  expectCode((delta) => {
    delta.activation_requires[3].owner = "";
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_requires[3].step_id = "green_regression_battery_renamed";
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.stop.resume_condition.source_kind = "when the owner decides";
    delta.stop.resume_condition.names_v2 = false;
  }, "resume_condition_missing");
  expectCode((delta) => {
    delete delta.semantics_contract;
  }, "activation_without_semantics_contract");
  expectCode((delta) => {
    delta.activation_requires[0].satisfied_now = true;
  }, "grant_read_as_implementation");
});

test("negative: the activation command whitelist refuses injection, traversal and out-of-tree paths", () => {
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "scripts/m210_s03_slice_battery.mjs", "--verify", "&& rm -rf /"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "scripts/m210_s03_slice_battery.mjs; rm -rf /"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "scripts/m210_s03_slice_battery.mjs", "$(whoami)"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "/etc/passwd"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "scripts/../../etc/passwd"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["node", "scripts/other_runner.mjs"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv = ["sh", "scripts/m210_s03_slice_battery.mjs"];
  }, "activation_step_missing");
  expectCode((delta) => {
    delete delta.activation_commands[0].argv;
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].owner = "";
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].created_by = "whenever";
  }, "activation_step_missing");
  // provenance: an `existing` claim must be backed by a tracked, present script.
  // T05 has since minted scripts/m210_s03_slice_battery.mjs, so the absent-on-disk
  // branch can no longer be produced from the live tree; the rule is exercised with
  // an env where that runner is not tracked instead of against a transient absence.
  {
    const delta = clone();
    delta.activation_commands[0].created_by = "existing";
    const env = envFor(delta);
    const untrackedEnv = {
      ...env,
      tracked: new Set([...env.tracked].filter((rel) => rel !== "scripts/m210_s03_slice_battery.mjs")),
    };
    const result = validateDelta(delta, untrackedEnv);
    assert.ok(
      codesOf(result).includes("activation_step_missing"),
      `an existing claim on an untracked runner must fail closed; got ${JSON.stringify(result.errors)}`,
    );
    assert.ok(
      result.errors.some(
        (error) => error.name === "activation_step_missing" && /is not tracked/.test(error.detail),
      ),
      `the untracked-runner branch must be the one that fired; got ${JSON.stringify(result.errors)}`,
    );
    assert.equal(result.ok, false, "an existing claim on an untracked runner must fail closed");
  }
  // hygiene: a runtime surface that exists on disk is a runtime claim.
  {
    const delta = clone();
    delta.runtime_surfaces_to_create[0].path = "scripts/m210_s03_activation_contract.test.mjs";
    const result = validateDelta(delta, envFor(delta));
    assert.ok(
      codesOf(result).includes("runtime_claim_present"),
      `an existing declared runtime surface must fail closed; got ${JSON.stringify(result.errors)}`,
    );
  }
});

// ---------------------------------------------------------------------------
// markers (emitted only after the contract holds)
// ---------------------------------------------------------------------------

test("M210 S03 activation contract markers", () => {
  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV), { ok: true, errors: [] });
  assert.equal(LIVE_DELTA.gate.grant_recorded, true);
  assert.equal(LIVE_DELTA.gate.applied, false);
  assert.equal(LIVE_DELTA.stop.runtime_demo, "not-proven");
  assert.equal(LIVE_DELTA.stop.runtime_stop, "active_outside_candidate_layer");
  assert.equal(LIVE_DELTA.conditional_surfaces_by_variant[ADOPTED_VARIANT].adopted, true);
  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV).errors, []);
  console.log("M210_S03_ACTIVATION_OK");
  console.log(`activation_steps=${LIVE_DELTA.activation_requires.length}`);
  console.log(`activation_commands=${LIVE_DELTA.activation_commands.length}`);
  console.log(`variants=${Object.keys(LIVE_DELTA.conditional_surfaces_by_variant).length}`);
  console.log(`gate_applied=${LIVE_DELTA.gate.applied}`);
  console.log(`runtime_demo=${LIVE_DELTA.stop.runtime_demo}`);
  console.log(`fail_closed_codes=${LIVE_DELTA.fail_closed_codes.length}`);
});
