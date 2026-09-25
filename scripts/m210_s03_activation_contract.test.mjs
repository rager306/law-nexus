// M210-3afp79 S03 T04 gated runtime-activation delta contract.
//
// Offline and fail-closed. The artifact under test is
// prd/architecture/m210-s03-runtime-activation-delta.json, the gated activation
// delta for the conditional bounded semantic runtime. The claim under test is
// that the delta stays applied false while the live runtime admission
// checkpoint records admission: not-adopted, that the sanctioned stop is
// recorded rather than replaced by a soft pass, and that activation is named as
// ordered steps with owners plus a closed argv whitelist of repository-relative
// scripts, gated on admission: granted, a real interactive owner reference, a
// verified governing surface, the byte-bound semantics contract and a green
// regression battery.
//
// The delta is a design-only record: it is proposed and unapplied, it creates
// no runtime surface, it activates no variant and it promotes nothing. Applying
// it without a granted checkpoint is delta_applied_without_grant. The
// activation_commands list is validated as argv arrays, never as shell strings,
// so the latent command-injection surface named by the slice threat surface
// (Q3) is closed by construction: no argv element may carry a shell
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
// activation_step_missing: an activation step or command is missing its id, owner, requirement, evidence, argv or expected marker, or names an inadmissible argv, a duplicate id, a non-whitelisted script or a missing tracked script.
// activation_without_governing_surface: activation is declared without a governing_surface_verified requirement.
// activation_without_owner_ref: activation is declared without a required interactive owner reference whose accepted forms are the closed two-element set.
// activation_without_regression_battery: the regression battery roles or the green_regression_battery step with command references are absent.
// activation_without_semantics_contract: the delta does not bind the byte-live semantics contract path and sha256.
// delta_applied_without_grant: the gate is applied, or a conditional variant is activated, while the checkpoint verdict is not granted.
// non_ascii_artifact: the artifact carries a non-ASCII byte.
// out_of_scope_activation: an out-of-scope surface is activated, or the not_adopted state claims an activation.
// raw_text_leak: the artifact carries an XML tag or a provider text marker.
// resume_condition_missing: the resume condition is absent or does not name an interactive source.
// runtime_claim_present: the artifact carries a Rust implementation marker, or a runtime surface is declared created or exists on disk.
// runtime_demo_claimed: runtime_demo is not not-proven.
// DOCUMENTED_CODES_END

const DELTA_REL = "prd/architecture/m210-s03-runtime-activation-delta.json";
const CHECKPOINT_REL = "prd/architecture/m210-s03-runtime-admission.md";
const SEMANTICS_REL = "prd/architecture/m210-s03-bounded-semantics-contract.json";
const START_GATE_REL = "prd/architecture/m210-s03-start-gate.json";
const IR_ALTERNATIVES_REL = "prd/architecture/m210-s01-ir-alternatives.json";
const SECTION3_REL = "prd/temporal-legal-model.md";

const SCHEMA = "law-nexus/m210-s03-runtime-activation-delta/v1";
const KIND = "m210-s03-runtime-activation-delta";
const MILESTONE = "M210-3afp79";
const SLICE = "S03";
const TASK = "T04";
const LIFECYCLE = ["proposed"];
const REQUIREMENT_REFS = ["RC28-F18", "R074"];
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;
const VERDICT_PATTERN = /^\*\*admission: (granted|not-adopted)\*\*$/gm;
const VERDICT_LINE_PATTERN = /^\*\*admission: (granted|not-adopted)\*\*$/m;

const EMITTABLE_CODES = [
  "activation_step_missing",
  "activation_without_governing_surface",
  "activation_without_owner_ref",
  "activation_without_regression_battery",
  "activation_without_semantics_contract",
  "delta_applied_without_grant",
  "non_ascii_artifact",
  "out_of_scope_activation",
  "raw_text_leak",
  "resume_condition_missing",
  "runtime_claim_present",
  "runtime_demo_claimed",
];

const REQUIRED_STEPS = [
  "granted_checkpoint",
  "governing_surface_verified",
  "named_variant_and_construct_set",
  "rebind_inputs",
  "declare_runtime_surfaces_and_lift_stop",
  "green_regression_battery",
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
  "gate.applied is false",
  "runtime_demo stays not-proven",
  "admission: granted",
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
  const verdict = env.verdict;

  // hygiene: ASCII only, no raw text, no Rust runtime marker.
  if (!/^[\x00-\x7f]*$/.test(text)) add("non_ascii_artifact", "the artifact carries a non-ASCII byte");
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) add("raw_text_leak", `raw text marker: ${marker}`);
  }
  for (const marker of RUNTIME_MARKERS) {
    if (text.includes(marker)) add("runtime_claim_present", `runtime marker: ${marker}`);
  }

  // the gate: applied false and gated on admission: granted.
  const gate = delta?.gate ?? {};
  if (gate.applied_requires !== "admission: granted") {
    add("delta_applied_without_grant", `applied_requires=${JSON.stringify(gate.applied_requires)}`);
  }
  if (verdict !== "granted" && gate.applied !== false) {
    add(
      "delta_applied_without_grant",
      `applied=${JSON.stringify(gate.applied)} while the checkpoint verdict is ${String(verdict)}`,
    );
  }

  // the sanctioned stop and the named resume condition.
  const stop = delta?.stop ?? {};
  if (stop.runtime_demo !== "not-proven") {
    add("runtime_demo_claimed", `runtime_demo=${JSON.stringify(stop.runtime_demo)}`);
  }
  const resume = stop.resume_condition;
  if (
    !resume ||
    resume.present !== true ||
    resume.names_interactive_source !== true ||
    typeof resume.source_kind !== "string" ||
    !/authenticated/i.test(resume.source_kind) ||
    !/interaction id/i.test(resume.source_kind)
  ) {
    add("resume_condition_missing", "the resume condition is absent or does not name an interactive source");
  }

  // the activation steps: named, owned and ordered.
  const steps = Array.isArray(delta?.activation_requires) ? delta.activation_requires : [];
  const stepIds = steps.map((step) => step?.step_id);
  if (steps.length < REQUIRED_STEPS.length) {
    add("activation_step_missing", `activation_requires carries ${steps.length} steps`);
  }
  if (new Set(stepIds).size !== stepIds.length) add("activation_step_missing", "duplicate step_id");
  for (const required of REQUIRED_STEPS) {
    if (!stepIds.includes(required)) add("activation_step_missing", `missing step ${required}`);
  }
  for (const step of steps) {
    if (typeof step?.step_id !== "string" || step.step_id === "") {
      add("activation_step_missing", "a step carries no step_id");
    }
    if (typeof step?.owner !== "string" || step.owner === "") {
      add("activation_step_missing", `a step carries no owner: ${String(step?.step_id)}`);
    }
    if (typeof step?.requires !== "string" || step.requires === "") {
      add("activation_step_missing", `a step carries no requirement: ${String(step?.step_id)}`);
    }
    if (typeof step?.evidence !== "string" || step.evidence === "") {
      add("activation_step_missing", `a step carries no evidence: ${String(step?.step_id)}`);
    }
  }

  // activation without an interactive owner reference.
  const granted = steps.find((step) => step?.step_id === "granted_checkpoint");
  if (!granted) {
    add("activation_without_owner_ref", "no granted_checkpoint step");
  } else {
    const ref = granted.interactive_ref;
    if (!ref || ref.required !== true) {
      add("activation_without_owner_ref", "the granted_checkpoint step does not require an interactive reference");
    } else if (!sameSet(ref.accepted_forms, ACCEPTED_FORMS)) {
      add("activation_without_owner_ref", `accepted_forms=${JSON.stringify(ref.accepted_forms)}`);
    }
  }

  // activation without a verified governing surface.
  const governing = steps.find((step) => step?.step_id === "governing_surface_verified");
  if (!governing || governing.required !== true) {
    add("activation_without_governing_surface", "no governing_surface_verified requirement");
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

  // out-of-scope activation and the not_adopted state.
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
  const notAdopted = variants.not_adopted;
  if (!notAdopted || notAdopted.activated !== false) {
    add("out_of_scope_activation", "the not_adopted state is absent or claims an activation");
  } else if (Array.isArray(notAdopted.surfaces_to_create) && notAdopted.surfaces_to_create.length > 0) {
    add("out_of_scope_activation", "the not_adopted state declares surfaces to create");
  }
  if (verdict !== "granted") {
    for (const [key, variant] of Object.entries(variants)) {
      if (key === "not_adopted") continue;
      if (variant?.activated !== false) {
        add("delta_applied_without_grant", `variant ${key} is activated while the verdict is ${String(verdict)}`);
      }
    }
  }

  // no runtime surface may be created or exist.
  const surfaces = Array.isArray(delta?.runtime_surfaces_to_create) ? delta.runtime_surfaces_to_create : [];
  for (const surface of surfaces) {
    if (surface?.created !== false) {
      add("runtime_claim_present", `runtime surface declared created: ${String(surface?.path)}`);
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

test("the envelope is the declared non-adopting activation delta", () => {
  assert.equal(LIVE_DELTA.schema, SCHEMA);
  assert.equal(LIVE_DELTA.schema_version, 1);
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
});

test("the gate stays applied false and is bound to the live not-adopted checkpoint", () => {
  assert.equal(LIVE_DELTA.gate.applied, false, "the gate must stay applied false");
  assert.equal(LIVE_DELTA.gate.applied_requires, "admission: granted");
  assert.ok(typeof LIVE_DELTA.gate.reason === "string" && LIVE_DELTA.gate.reason.length > 0);
  assert.equal(LIVE_DELTA.checkpoint_verdict, "not-adopted");

  const matches = CHECKPOINT_TEXT.match(VERDICT_PATTERN) || [];
  assert.equal(matches.length, 1, "the checkpoint must carry exactly one verdict line");
  assert.ok(VERDICT_LINE_PATTERN.test(CHECKPOINT_TEXT));
  assert.equal(VERDICT, "not-adopted", "the live checkpoint verdict must be not-adopted");
  assert.equal(LIVE_DELTA.checkpoint_verdict, VERDICT);
  assert.match(LIVE_DELTA.checkpoint_sha256, SHA_PATTERN);
  assert.equal(LIVE_DELTA.checkpoint_sha256, sha256Repo(CHECKPOINT_REL), "the checkpoint pin must match live bytes");

  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV), { ok: true, errors: [] });
});

test("the sanctioned stop is recorded and the resume condition names an interactive source", () => {
  const { stop } = LIVE_DELTA;
  assert.equal(stop.sanctioned, true, "the stop must be explicitly sanctioned");
  assert.equal(stop.runtime_work, "not-started");
  assert.equal(stop.runtime_demo, "not-proven");
  assert.equal(stop.classification, "design-only no-start");
  const effective = stop.resume_condition;
  assert.equal(effective.present, true);
  assert.equal(effective.names_interactive_source, true);
  assert.match(effective.source_kind, /authenticated subjective-UAT criterion id/);
  assert.match(effective.source_kind, /owner interaction id with a timestamp/);
  assert.ok(typeof effective.note === "string" && effective.note.length > 0);

  const section = resumeSection(CHECKPOINT_TEXT);
  assert.ok(section, "the live checkpoint must carry a Resume condition section");
  assert.match(section, /interactive/i, "the checkpoint resume condition must name an interactive source");

  // The sanctioned stop is never a soft pass.
  assert.ok(!("verdict" in LIVE_DELTA) || LIVE_DELTA.verdict === "not-adopted");
  assert.ok(!("outcome" in LIVE_DELTA) || LIVE_DELTA.outcome === "not-adopted");
  assert.equal(LIVE_DELTA.gate.applied, false);
});

test("activation is named as ordered steps with owners, a named command and an owner reference", () => {
  const steps = LIVE_DELTA.activation_requires;
  assert.ok(Array.isArray(steps) && steps.length >= REQUIRED_STEPS.length);
  assert.deepEqual(
    steps.map((step) => step.step_id),
    REQUIRED_STEPS,
    "the steps must carry the six required ids in order",
  );
  assert.deepEqual(
    steps.map((step) => step.order),
    [1, 2, 3, 4, 5, 6],
    "the steps must be ordered",
  );
  assert.equal(new Set(steps.map((step) => step.step_id)).size, steps.length, "step ids must be unique");
  for (const step of steps) {
    assert.ok(typeof step.owner === "string" && step.owner.length > 0, `${step.step_id} must name an owner`);
    assert.ok(typeof step.requires === "string" && step.requires.length > 0, `${step.step_id} must name what it requires`);
    assert.ok(typeof step.evidence === "string" && step.evidence.length > 0, `${step.step_id} must name its evidence`);
  }

  const granted = steps[0];
  assert.equal(granted.step_id, "granted_checkpoint");
  assert.equal(granted.interactive_ref.required, true);
  assert.deepEqual(granted.interactive_ref.accepted_forms, ACCEPTED_FORMS);
  assert.deepEqual(granted.interactive_ref.rejected_as_grantor, REJECTED_AS_GRANTOR);

  const governing = steps.find((step) => step.step_id === "governing_surface_verified");
  assert.equal(governing.required, true, "the governing surface must be a required prerequisite");

  const rebind = steps.find((step) => step.step_id === "rebind_inputs");
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
    [...liveVariantIds, "not_adopted"].sort(),
    "the conditional surface map must carry every live S01 variant plus the not_adopted state",
  );
  for (const live of IR_ALTERNATIVES.variants) {
    const entry = variants[live.variant_id];
    assert.equal(entry.variant_id, live.variant_id);
    assert.equal(entry.variant_label, live.label);
    assert.equal(entry.activated, false, `${live.variant_id} must be inactive`);
    assert.deepEqual(entry.required_new_adr_terms, live.required_new_adr_terms);
    assert.deepEqual(entry.section3_terms_to_define, live.required_new_adr_terms);
    assert.equal(entry.consequences_for_S03, live.consequences_for_S03);
    assert.ok(Array.isArray(entry.would_touch) && entry.would_touch.length > 0);
    assert.ok(Array.isArray(entry.non_claims) && entry.non_claims.length >= 2);
  }
  assert.equal(variants.not_adopted.activated, false);
  assert.equal(variants.not_adopted.variant_id, null);
  assert.deepEqual(variants.not_adopted.surfaces_to_create, []);

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

test("non-claims state the sanctioned stop and refuse adoption and runtime claims", () => {
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
    code: "activation_without_governing_surface",
    mutate: (delta) => {
      delta.activation_requires = delta.activation_requires.filter(
        (step) => step.step_id !== "governing_surface_verified",
      );
    },
  },
  {
    code: "activation_without_owner_ref",
    mutate: (delta) => {
      delete delta.activation_requires.find((step) => step.step_id === "granted_checkpoint").interactive_ref;
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
    code: "resume_condition_missing",
    mutate: (delta) => {
      delta.stop.resume_condition.names_interactive_source = false;
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

test("negative: an applied gate, an unowned step and a red battery are all refused", () => {
  expectCode((delta) => {
    delta.gate.applied = true;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.gate.applied_requires = "battery pass";
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.activation_requires[0].interactive_ref.accepted_forms = ["bare_name"];
  }, "activation_without_owner_ref");
  expectCode((delta) => {
    delta.activation_requires = delta.activation_requires.filter(
      (step) => step.step_id !== "governing_surface_verified",
    );
  }, "activation_without_governing_surface");
  expectCode((delta) => {
    delete delta.semantics_contract;
  }, "activation_without_semantics_contract");
  expectCode((delta) => {
    delta.activation_commands = delta.activation_commands.filter((command) => command.role !== "regression_m209_s04");
  }, "activation_without_regression_battery");
  expectCode((delta) => {
    delta.activation_requires[3].owner = "";
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.stop.resume_condition.source_kind = "when the owner decides";
  }, "resume_condition_missing");
  expectCode((delta) => {
    delta.stop.runtime_demo = "proven";
  }, "runtime_demo_claimed");
  expectCode((delta) => {
    delta.conditional_surfaces_by_variant.not_adopted.activated = true;
  }, "out_of_scope_activation");
  expectCode((delta) => {
    delta.conditional_surfaces_by_variant.abstention_first_candidates_only.activated = true;
  }, "delta_applied_without_grant");
  expectCode((delta) => {
    delta.runtime_surfaces_to_create[0].created = true;
  }, "runtime_claim_present");
  expectCode((delta) => {
    delta.non_claims[0] = `${delta.non_claims[0]} pub struct Envelope;`;
  }, "runtime_claim_present");
  expectCode((delta) => {
    delta.non_claims[1] = `${delta.non_claims[1]} consultantplus://x`;
  }, "raw_text_leak");
  expectCode((delta) => {
    delta.non_claims[2] = `${delta.non_claims[2]} \u041d\u043e\u0440\u043c\u0430`;
  }, "non_ascii_artifact");
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
  expectCode((delta) => {
    delta.activation_requires[1].step_id = "rebind_inputs";
  }, "activation_step_missing");
  expectCode((delta) => {
    delta.activation_commands[0].argv[1] = "scripts/m210_s03_slice_battery.mjs";
    delta.activation_commands[0].created_by = "existing";
  }, "activation_step_missing");
});

// ---------------------------------------------------------------------------
// markers (emitted only after the contract holds)
// ---------------------------------------------------------------------------

test("M210 S03 activation contract markers", () => {
  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV), { ok: true, errors: [] });
  assert.equal(LIVE_DELTA.gate.applied, false);
  assert.equal(LIVE_DELTA.stop.runtime_demo, "not-proven");
  assert.equal(LIVE_DELTA.conditional_surfaces_by_variant.not_adopted.activated, false);
  assert.deepEqual(validateDelta(LIVE_DELTA, LIVE_ENV).errors, []);
  console.log("M210_S03_ACTIVATION_OK");
  console.log(`activation_steps=${LIVE_DELTA.activation_requires.length}`);
  console.log(`activation_commands=${LIVE_DELTA.activation_commands.length}`);
  console.log(`variants=${Object.keys(LIVE_DELTA.conditional_surfaces_by_variant).length}`);
  console.log(`gate_applied=${LIVE_DELTA.gate.applied}`);
  console.log(`runtime_demo=${LIVE_DELTA.stop.runtime_demo}`);
  console.log(`fail_closed_codes=${LIVE_DELTA.fail_closed_codes.length}`);
});
