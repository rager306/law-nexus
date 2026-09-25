// M210-3afp79 S04 T04 review session contract.
//
// Offline and fail-closed. The artifacts under test are
// prd/architecture/m210-s04-review-session-contract.json,
// prd/architecture/m210-s04-event-submission-delta.json and
// prd/architecture/m210-s04-review-session-state.json: a design-only session
// contract over the T03 review cards, a submission delta that stays inert, and
// the current session state in which no session ran.
//
// The claims under test are that a per-finding individual choice is required
// and blanket confirmation, preselection and agent confirmation are forbidden,
// that a recommendation is not consent, that only explicitly confirmed answers
// may persist, that a read-back after each answer echoes finding_id,
// selected_disposition, rationale, tested_source_revision, packet_content_sha256,
// card_set_sha256 and a deterministic event_id, that the read-back comparison
// rejects a different or missing event_id, that the event identity is a
// specification with closed inputs and a version rather than a created event,
// that the tested_source_revision content digest and the reviewed_git_revision
// commit are distinct, non-interchangeable namespaces with no fake mapping, that
// drift of any fingerprint invalidates the proposal and forbids recording, that
// the submission gate stays applied=false until a host-controlled actor-bound
// path with verified session identity and an authority epoch exists, that a
// caller-supplied actor_class and actor_id are insufficient, that the artifacts
// are canonical ASCII with no raw legal text and no fabricated execution, and
// that each documented fail-closed code is empirically emitted by a mutation.
//
// This contract spawns no subprocess, opens no socket and reads only
// repository-relative tracked artifacts under prd/, scripts/ and src/. It never
// writes a file.
//
// Run: node --test scripts/m210_s04_session_contract.test.mjs

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

// ## Fail-closed codes (documented set; asserted equal to EMITTABLE_CODES)
// DOCUMENTED_CODES_BEGIN
// blanket_confirmation_forbidden: per-finding individual choice must be required and blanket confirmation forbidden.
// preselect_forbidden: no option may be preselected before the human answers.
// agent_confirmation_forbidden: an agent may not confirm a per-finding disposition.
// recommendation_as_consent: the recommendation must stay advisory and must not be consent.
// unconfirmed_answer_recorded: only explicitly confirmed answers may persist.
// readback_missing: a read-back must be required after each answer and echo the full field set.
// event_id_missing: the read-back must name a deterministic event identity with closed inputs and no created event.
// event_id_mismatch: the read-back comparison must reject a different or missing event_id.
// event_identity_version_not_pinned: the event identity version must be the exact pinned value, not an arbitrary nonempty string.
// event_identity_inputs_not_canonical: the identity inputs must be the exact ordered closed seven and their canonicalization must be pinned.
// event_identity_not_host_derived: the future event identity must be host-derived and verified against the canonical inputs before persistence.
// caller_supplied_event_id_forbidden: no caller-supplied event id may enter the identity or the submission argv.
// host_controlled_path_substituted: the host-controlled executable path token and submission path must not be caller-substituted.
// drift_invalidates_proposal: drift of a fingerprint must invalidate the proposal and forbid recording.
// revision_namespace_confused: the tested_source_revision digest and the reviewed_git_revision commit must stay distinct.
// revision_unbound: every revision claim must resolve to a live immutable input and the confirmed card.
// submission_without_actor_bound_path: the submission gate must stay applied=false while the actor-bound path is unavailable.
// actor_bound_scope_confused: the actor-bound scope must be record_human_disposition, not the subjective-UAT path.
// self_asserted_identity: a caller-supplied actor_class or actor_id must not be treated as authority.
// authority_binding_missing: a submission must require a verified host authority binding and an authority epoch.
// forbidden_actor_source: a submission must not derive authority from a forbidden actor source.
// agent_may_not_submit: an agent may not submit a per-finding human disposition.
// choice_not_allowed: the allowed choice set must be exactly the closed set.
// shell_string_command: submission commands must be argv-only and never a shell string.
// argv_not_array: every submission command must carry a non-empty argv array.
// contract_hash_mismatch: the delta must bind to the live session contract digest.
// session_state_inconsistent: the current session state must stay not-run, hold and zero.
// review_case_event_written: no Review Case event may be written and the packet events directory must be absent.
// non_ascii_artifact: the artifacts must carry no non-ASCII byte.
// raw_text_leak: the artifacts must carry no XML tag or provider text marker.
// DOCUMENTED_CODES_END

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const CONTRACT_REL = "prd/architecture/m210-s04-review-session-contract.json";
export const DELTA_REL = "prd/architecture/m210-s04-event-submission-delta.json";
export const STATE_REL = "prd/architecture/m210-s04-review-session-state.json";
export const CARDS_REL = "prd/architecture/m210-s04-rc28-review-cards.json";
export const MATRIX_REL = "prd/architecture/m210-s04-finding-evidence-matrix.json";
export const PACKET_REL = "prd/architecture/review-cases/packets/RC-2026-09-10-001.json";
export const REVIEW_DOC_REL = "doc/review/review-28-10-09-2026.md";
export const TRUST_BOUNDARY_REL = "prd/architecture/m210-s02-governing-surface-check.json";
export const PACKET_EVENTS_REL = "prd/architecture/review-cases/packets/RC-2026-09-10-001";
export const CLI_REL = "src/law_nexus_harness/cli.py";
export const APPLICATION_REL = "src/law_nexus_harness/review_case/application.py";
export const CONTRACT_SELF_REL = "scripts/m210_s04_session_contract.test.mjs";

export const SCHEMA = "law-nexus/m210-s04-review-session-contract/v1";
export const DELTA_SCHEMA = "law-nexus/m210-s04-event-submission-delta/v1";
export const STATE_SCHEMA = "law-nexus/m210-s04-review-session-state/v1";
export const KIND = "m210-s04-review-session-contract";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S04";
export const TASK = "T04";
export const LIFECYCLE = ["proposed"];
export const PACKET_ID = "RC-2026-09-10-001";
export const F18_CRITERION_ID = "37181c25-88b0-4896-bffe-d10642970e6f";

export const READBACK_ECHO_FIELDS = [
  "finding_id",
  "selected_disposition",
  "rationale",
  "tested_source_revision",
  "packet_content_sha256",
  "card_set_sha256",
  "event_id",
];
export const ALLOWED_CHOICES = ["accept_as_proposed", "change_disposition", "defer", "stop_session"];
export const DRIFT_FINGERPRINTS = [
  "packet_content_sha256",
  "reviewed_git_revision",
  "card_set_sha256",
  "tested_source_revision",
];
export const ACTIVATION_REQUIRES = [
  "actor_bound_path",
  "per_finding_readback",
  "fingerprints",
  "confirmed_only",
  "ledger_verified_same_event",
  "host_authority_binding",
];
export const HOST_AUTHORITY_FIELDS = [
  "host_authority_verified",
  "session_identity_verified",
  "operation_fenced_actor_ref",
  "operation_fenced_acceptance_ref",
  "authority_epoch_required",
  "per_finding_decision_bound",
  "ledger_readback_same_event_required",
];
export const FORBIDDEN_ACTOR_SOURCES = [
  "caller_asserted_human",
  "s02_subjective_uat_acceptance",
  "agent_self_assertion",
  "blank_actor_id",
  "milestone_or_gsd_lock",
];
export const NAMED_FAIL_CLOSED = [
  "self_asserted_identity",
  "authority_binding_missing",
  "submission_without_actor_bound_path",
  "forbidden_actor_source",
];
export const RULE_KEYS = [
  "per_finding_individual_choice_required",
  "blanket_confirmation_forbidden",
  "preselect_forbidden",
  "agent_confirmation_forbidden",
  "recommendation_is_not_consent",
  "persist_only_confirmed",
  "ledger_readback_verified_per_choice",
];
export const REVISION_NAMESPACES = ["sha256_content_digest", "git_commit"];
export const EVENT_IDENTITY_VERSION = "review-case-event-identity/v1";
export const EVENT_IDENTITY_OWNER = "host";
export const EVENT_IDENTITY_INPUTS = [
  "packet_id",
  "finding_id",
  "selected_disposition",
  "actor_ref",
  "acceptance_ref",
  "authority_epoch",
  "source_revision",
];
export const HOST_PATH_TOKEN = "uv";
export const HOST_SUBMISSION_PATH = "future host-controlled actor-bound submission path";

export const EMITTABLE_CODES = [
  "blanket_confirmation_forbidden",
  "preselect_forbidden",
  "agent_confirmation_forbidden",
  "recommendation_as_consent",
  "unconfirmed_answer_recorded",
  "readback_missing",
  "event_id_missing",
  "event_id_mismatch",
  "event_identity_version_not_pinned",
  "event_identity_inputs_not_canonical",
  "event_identity_not_host_derived",
  "caller_supplied_event_id_forbidden",
  "host_controlled_path_substituted",
  "drift_invalidates_proposal",
  "revision_namespace_confused",
  "revision_unbound",
  "submission_without_actor_bound_path",
  "actor_bound_scope_confused",
  "self_asserted_identity",
  "authority_binding_missing",
  "forbidden_actor_source",
  "agent_may_not_submit",
  "choice_not_allowed",
  "shell_string_command",
  "argv_not_array",
  "contract_hash_mismatch",
  "session_state_inconsistent",
  "review_case_event_written",
  "non_ascii_artifact",
  "raw_text_leak",
];

export const CONTRACT_MARKER = "M210_S04_SESSION_OK";
export const SHA_PATTERN_SOURCE = "^sha256:[0-9a-f]{64}$";
export const GIT_PATTERN_SOURCE = "^[0-9a-f]{40}$";

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];
const RUNTIME_MARKERS = ["pub fn", "pub struct", "impl "];
const ISO_TIMESTAMP_RE = /\d{4}-\d{2}-\d{2}T/;

// ---------------------------------------------------------------------------
// shared fixtures
// ---------------------------------------------------------------------------

export const root = REPO_ROOT;

export function readRelative(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

export function relativeExists(relativePath) {
  if (typeof relativePath !== "string" || relativePath === "") return false;
  if (path.isAbsolute(relativePath) || relativePath.split("/").includes("..")) return false;
  return existsSync(path.join(root, relativePath));
}

export function sha256OfRelative(relativePath) {
  return `sha256:${createHash("sha256").update(readFileSync(path.join(root, relativePath))).digest("hex")}`;
}

export const committedContractText = readRelative(CONTRACT_REL);
export const committedDeltaText = readRelative(DELTA_REL);
export const committedStateText = readRelative(STATE_REL);
export const contract = JSON.parse(committedContractText);
export const delta = JSON.parse(committedDeltaText);
export const state = JSON.parse(committedStateText);
export const cards = JSON.parse(readRelative(CARDS_REL));
export const matrix = JSON.parse(readRelative(MATRIX_REL));

export const FINDING_IDS = cards.cards.map((card) => card.finding_id);

export const baseBundle = { contract, delta, state };

export function liveEnv(overrides = {}) {
  return {
    findingIds: FINDING_IDS,
    liveContractSha: sha256OfRelative(CONTRACT_REL),
    liveCardsSha: sha256OfRelative(CARDS_REL),
    liveMatrixSha: sha256OfRelative(MATRIX_REL),
    livePacketSha: sha256OfRelative(PACKET_REL),
    liveStateSha: sha256OfRelative(STATE_REL),
    liveReviewedGitRevision: matrix.review_case.reviewed_git_revision,
    ...overrides,
  };
}

function cloneBundle(bundle = baseBundle) {
  return JSON.parse(JSON.stringify(bundle));
}

function sortedJson(value) {
  return JSON.stringify([...value].sort());
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

export function validateSession(bundle, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ name, detail });
  const c = bundle?.contract ?? {};
  const d = bundle?.delta ?? {};
  const s = bundle?.state ?? {};

  const findingIds = env.findingIds ?? FINDING_IDS;
  const liveContractSha = env.liveContractSha ?? sha256OfRelative(CONTRACT_REL);
  const liveCardsSha = env.liveCardsSha ?? sha256OfRelative(CARDS_REL);
  const liveMatrixSha = env.liveMatrixSha ?? sha256OfRelative(MATRIX_REL);
  const livePacketSha = env.livePacketSha ?? sha256OfRelative(PACKET_REL);
  const liveStateSha = env.liveStateSha ?? sha256OfRelative(STATE_REL);
  const liveReviewedGitRevision =
    env.liveReviewedGitRevision ?? matrix.review_case.reviewed_git_revision;

  // 0. text hygiene: ASCII-only, no XML or provider text marker.
  const text = typeof env.text === "string" ? env.text : JSON.stringify([c, d, s]);
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_artifact", `non-ascii character at index ${offending}`);
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `text marker ${marker}`);
  }

  // 1. the closed rule set: individual choice, no blanket, no preselect, no
  //    agent confirmation, recommendation is not consent, persist only
  //    confirmed, per-choice read-back.
  const rules = c.rules ?? {};
  if (
    rules.per_finding_individual_choice_required !== true ||
    rules.blanket_confirmation_forbidden !== true
  ) {
    code(
      "blanket_confirmation_forbidden",
      "a per-finding individual choice must be required and blanket confirmation forbidden",
    );
  }
  if (rules.preselect_forbidden !== true) {
    code("preselect_forbidden", "no option may be preselected");
  }
  if (rules.agent_confirmation_forbidden !== true) {
    code("agent_confirmation_forbidden", "an agent may not confirm a disposition");
  }
  if (rules.recommendation_is_not_consent !== true) {
    code("recommendation_as_consent", "the recommendation must stay advisory and not be consent");
  }
  if (rules.persist_only_confirmed !== true) {
    code("unconfirmed_answer_recorded", "only explicitly confirmed answers may persist");
  }

  // 2. the allowed choice set is exactly the closed set.
  const choices = Array.isArray(c.allowed_choices) ? [...c.allowed_choices].sort() : [];
  if (JSON.stringify(choices) !== sortedJson(ALLOWED_CHOICES)) {
    code("choice_not_allowed", `allowed_choices=${JSON.stringify(c.allowed_choices)}`);
  }

  // 3. read-back: required after each answer, full echo set, deterministic
  //    event identity with closed inputs, and a comparison that rejects a
  //    different or missing event_id.
  const readback = c.read_back ?? {};
  const echoFields = Array.isArray(readback.echo_fields) ? readback.echo_fields : [];
  if (
    rules.ledger_readback_verified_per_choice !== true ||
    readback.required !== true ||
    readback.after_each_answer !== true ||
    !READBACK_ECHO_FIELDS.every((field) => echoFields.includes(field))
  ) {
    code(
      "readback_missing",
      "a read-back must be required after each answer and echo the full field set",
    );
  }
  const eventId = readback.event_id;
  const eventIdOk =
    eventId &&
    typeof eventId === "object" &&
    eventId.role === "deterministic_identity_of_future_event" &&
    eventId.artifact_status === "specification_only_no_event_created" &&
    eventId.event_created === false &&
    typeof eventId.identity_version === "string" &&
    eventId.identity_version.trim() !== "" &&
    Array.isArray(eventId.closed_field_inputs) &&
    eventId.closed_field_inputs.length > 0 &&
    eventId.closed_field_inputs.every((field) => typeof field === "string" && field.trim() !== "");
  if (!eventIdOk) {
    code(
      "event_id_missing",
      "the read-back must name a deterministic event identity with closed inputs and no created event",
    );
  }
  if (eventId?.identity_version !== EVENT_IDENTITY_VERSION) {
    code(
      "event_identity_version_not_pinned",
      `identity_version=${JSON.stringify(eventId?.identity_version)}`,
    );
  }
  if (
    !Array.isArray(eventId?.closed_field_inputs) ||
    JSON.stringify(eventId.closed_field_inputs) !== JSON.stringify(EVENT_IDENTITY_INPUTS)
  ) {
    code(
      "event_identity_inputs_not_canonical",
      `closed_field_inputs=${JSON.stringify(eventId?.closed_field_inputs)}`,
    );
  }
  const canonicalization = eventId?.canonicalization ?? {};
  if (
    canonicalization.order !== "closed_field_inputs_array_order" ||
    canonicalization.encoding !== "utf8" ||
    canonicalization.serialization !== "json_array_no_insignificant_whitespace" ||
    canonicalization.digest !== "sha256" ||
    canonicalization.version_included !== true ||
    canonicalization.implementation_status !== "specified_not_implemented"
  ) {
    code(
      "event_identity_inputs_not_canonical",
      "the canonicalization must be pinned and unambiguous",
    );
  }
  const derivation = eventId?.derivation ?? {};
  if (
    derivation.owner !== EVENT_IDENTITY_OWNER ||
    derivation.host_derived !== true ||
    derivation.caller_supplied_event_id_forbidden !== true ||
    derivation.derived_before_persistence !== true ||
    derivation.verified_against_canonical_inputs_before_readback !== true ||
    derivation.missing_derivation_requirement_is_failure !== true
  ) {
    code(
      "event_identity_not_host_derived",
      "the future event identity must be host-derived and verified against canonical inputs before persistence",
    );
  }
  const comparison = readback.comparison ?? {};
  const mustCompare = Array.isArray(comparison.must_compare) ? comparison.must_compare : [];
  if (
    comparison.mode !== "exact_event_id_and_confirmed_fields" ||
    comparison.event_id_mismatch_is_failure !== true ||
    comparison.missing_event_id_is_failure !== true ||
    !READBACK_ECHO_FIELDS.every((field) => mustCompare.includes(field))
  ) {
    code("event_id_mismatch", "the read-back comparison must reject a different or missing event_id");
  }

  // 4. drift policy: every fingerprint invalidates the proposal and forbids
  //    recording.
  const drift = c.drift_policy ?? {};
  const fingerprintNames = Array.isArray(drift.fingerprints)
    ? drift.fingerprints.map((item) => item?.name)
    : [];
  if (
    drift.invalidates_proposal !== true ||
    drift.recording_forbidden !== true ||
    !DRIFT_FINGERPRINTS.every((name) => fingerprintNames.includes(name))
  ) {
    code("drift_invalidates_proposal", "drift must invalidate the proposal and forbid recording");
  }

  // 5. revision namespaces stay distinct and non-interchangeable.
  const namespaces = c.revision_namespaces ?? {};
  const tested = namespaces.tested_source_revision ?? {};
  const reviewed = namespaces.reviewed_git_revision ?? {};
  if (
    tested.namespace !== REVISION_NAMESPACES[0] ||
    tested.pattern !== SHA_PATTERN_SOURCE ||
    tested.whole_tree_aggregate !== false ||
    tested.interchangeable_with_reviewed_git_revision !== false ||
    reviewed.namespace !== REVISION_NAMESPACES[1] ||
    reviewed.pattern !== GIT_PATTERN_SOURCE ||
    reviewed.interchangeable_with_tested_source_revision !== false ||
    namespaces.cross_namespace_mapping !== "forbidden"
  ) {
    code(
      "revision_namespace_confused",
      "the two revision namespaces must stay distinct and non-interchangeable",
    );
  }

  // 6. every revision claim resolves to a live immutable input; no fake
  //    sha256-to-git mapping.
  const futureProof = c.required_future_proof ?? {};
  const bindings = Array.isArray(futureProof.bindings) ? futureProof.bindings : [];
  const boundNames = bindings.map((item) => item?.name);
  const bindingsComplete = bindings.every(
    (item) => typeof item?.immutable_input === "string" && item.immutable_input.trim() !== "",
  );
  if (
    futureProof.confirmed_card_required !== true ||
    futureProof.fake_sha256_to_git_mapping_forbidden !== true ||
    futureProof.unbound_revision_is_failure !== true ||
    !["tested_source_revision", "reviewed_git_revision"].every((name) => boundNames.includes(name)) ||
    !bindingsComplete
  ) {
    code("revision_unbound", "both revisions must bind to immutable inputs and the confirmed card");
  }
  if (c.cards_binding?.sha256 !== liveCardsSha) {
    code("revision_unbound", "the cards binding does not resolve to the live cards artifact");
  }
  if (c.matrix_binding?.sha256 !== liveMatrixSha) {
    code("revision_unbound", "the matrix binding does not resolve to the live matrix artifact");
  }
  if (c.reviewed_git_revision !== liveReviewedGitRevision) {
    code("revision_unbound", "reviewed_git_revision does not resolve to the live packet revision");
  }
  if (c.packet_binding?.content_sha256 !== livePacketSha) {
    code("revision_unbound", "the packet binding does not resolve to the live packet artifact");
  }
  if (
    typeof cards.review_case?.source_content_sha256 === "string" &&
    c.packet_binding?.source_content_sha256 !== cards.review_case.source_content_sha256
  ) {
    code("revision_unbound", "the packet source binding does not resolve to the live review document");
  }
  if (c.session_state_binding?.sha256 !== liveStateSha) {
    code("revision_unbound", "the session state binding does not resolve to the live state artifact");
  }

  // 7. submission gate stays inert and scoped to the actor-bound disposition
  //    path.
  const gate = c.submission_gate ?? {};
  const appliedRequires = gate.applied_requires ?? {};
  const deltaGate = d.gate ?? {};
  const activation = deltaGate.activation_requires ?? {};
  if (gate.applied !== false || deltaGate.applied !== false) {
    code(
      "submission_without_actor_bound_path",
      "the submission gate must stay applied=false while the actor-bound path is unavailable",
    );
  }
  if (!ACTIVATION_REQUIRES.every((key) => activation[key] === true)) {
    code(
      "submission_without_actor_bound_path",
      `delta activation_requires is missing one of ${ACTIVATION_REQUIRES.join(",")}`,
    );
  }
  if (
    gate.actor_bound_scope !== "record_human_disposition" ||
    gate.trust_boundary_ref !== TRUST_BOUNDARY_REL ||
    deltaGate.scope !== "per_finding_disposition_submission" ||
    gate.per_finding_decision !== true
  ) {
    code("actor_bound_scope_confused", "the actor-bound scope must be record_human_disposition");
  }
  if (
    gate.caller_supplied_identity_insufficient !== true ||
    !Array.isArray(gate.caller_supplied_fields_insufficient) ||
    !gate.caller_supplied_fields_insufficient.includes("actor_class=HUMAN") ||
    !gate.caller_supplied_fields_insufficient.includes("nonempty actor_id")
  ) {
    code("self_asserted_identity", "a caller-supplied identity must be declared insufficient");
  }
  const namedFailClosed = Array.isArray(gate.named_fail_closed)
    ? gate.named_fail_closed.map((item) => item?.code)
    : [];
  if (!namedFailClosed.includes("self_asserted_identity")) {
    code("self_asserted_identity", "a named fail-closed for self-asserted identity is required");
  }
  if (!HOST_AUTHORITY_FIELDS.every((key) => appliedRequires[key] === true)) {
    code(
      "authority_binding_missing",
      `applied_requires must require a verified host authority binding (${HOST_AUTHORITY_FIELDS.join(",")})`,
    );
  }
  if (
    appliedRequires.path !== HOST_SUBMISSION_PATH ||
    appliedRequires.path_owner !== "host" ||
    appliedRequires.caller_supplied_path_forbidden !== true
  ) {
    code(
      "host_controlled_path_substituted",
      "the host-controlled submission path must be pinned and not caller-substituted",
    );
  }
  const forbidden = Array.isArray(gate.forbidden_actor_sources) ? gate.forbidden_actor_sources : [];
  if (
    forbidden.length === 0 ||
    !FORBIDDEN_ACTOR_SOURCES.every((source) => forbidden.includes(source)) ||
    forbidden.some((source) => !FORBIDDEN_ACTOR_SOURCES.includes(source))
  ) {
    code("forbidden_actor_source", "the forbidden actor source list is missing or admits an unknown source");
  }
  if (gate.agent_may_submit !== false) {
    code("agent_may_not_submit", "an agent may not submit a per-finding disposition");
  }
  const variants = Array.isArray(deltaGate.variants) ? deltaGate.variants : [];
  if (variants.length === 0 || variants.some((variant) => variant?.activated !== false)) {
    code("submission_without_actor_bound_path", "no submission variant may be activated");
  }
  if (!variants.some((variant) => variant?.id === "agent_self_submission")) {
    code("agent_may_not_submit", "the agent self-submission variant must be named and deactivated");
  }
  if (!variants.some((variant) => variant?.id === "subjective_uat_reuse")) {
    code("actor_bound_scope_confused", "the subjective-UAT reuse variant must be named and deactivated");
  }
  if (gate.existing_s02_acceptance_is_disposition_authority !== false) {
    code(
      "actor_bound_scope_confused",
      "the S02 variant C acceptance must not be disposition authority",
    );
  }

  // 8. the delta binds to the live session contract digest.
  if (
    d.bound_to_session_contract?.sha256 !== liveContractSha ||
    d.bound_to_session_contract?.path !== CONTRACT_REL
  ) {
    code("contract_hash_mismatch", "the delta must bind to the live session contract digest");
  }

  // 9. commands are argv-only and none of them ran.
  const commands = Array.isArray(d.commands) ? d.commands : [];
  if (commands.length === 0 || d.command_policy?.argv_only !== true) {
    code("argv_not_array", "the command specification must be present and argv-only");
  }
  for (const command of commands) {
    if (
      typeof command === "string" ||
      command?.shell_string === true ||
      typeof command?.invocation === "string" ||
      command?.argv_only !== true
    ) {
      code("shell_string_command", "submission commands must be argv-only and never a shell string");
    }
    if (!command || !Array.isArray(command.argv) || command.argv.length === 0) {
      code("argv_not_array", "every submission command must carry a non-empty argv array");
    }
    if (command?.executed === true || command?.available === true) {
      code(
        "submission_without_actor_bound_path",
        "a submission command must not be available or executed while the gate is inert",
      );
    }
    if (
      Array.isArray(command?.argv) &&
      command.argv.some((token) => token === "--event-id" || token === "{event_id}")
    ) {
      code(
        "caller_supplied_event_id_forbidden",
        "a caller-supplied event id must not enter the submission argv",
      );
    }
    if (
      command?.executable_path_token !== HOST_PATH_TOKEN ||
      command?.executable_path_owner !== "host" ||
      !Array.isArray(command?.argv) ||
      command.argv[0] !== HOST_PATH_TOKEN
    ) {
      code(
        "host_controlled_path_substituted",
        "the executable path token must be pinned host-controlled and not caller-substituted",
      );
    }
  }
  if (d.command_policy?.executed_commands !== 0) {
    code("submission_without_actor_bound_path", "no submission command may have executed");
  }

  // 10. session state stays not-run and on hold, with all answers null.
  const answers = s.per_finding_answers;
  const answerKeys = answers && typeof answers === "object" ? Object.keys(answers).sort() : [];
  const allNull = answerKeys.length > 0 && answerKeys.every((key) => answers[key] === null);
  if (
    !allNull ||
    JSON.stringify(answerKeys) !== sortedJson(findingIds) ||
    s.session_run !== false ||
    s.confirmed_count !== 0 ||
    s.events_written !== 0 ||
    s.outcome !== "hold" ||
    s.sanctioned_stop !== true ||
    s.choices_made !== 0 ||
    s.preselected_count !== 0 ||
    s.agent_confirmed_count !== 0 ||
    s.read_backs_verified !== 0 ||
    s.submission_gate_applied !== false
  ) {
    code("session_state_inconsistent", "the current session state must stay not-run, hold and zero");
  }
  if (answers && typeof answers === "object") {
    for (const key of Object.keys(answers)) {
      const answer = answers[key];
      if (
        answer &&
        typeof answer === "object" &&
        answer.confirmed === true &&
        (answer.read_back_verified !== true || !answer.read_back_event_id)
      ) {
        code(
          "unconfirmed_answer_recorded",
          `${key} records a confirmed answer without a verified read-back`,
        );
      }
    }
  }
  if (
    s.events_written !== 0 ||
    s.boundary?.review_case_events_written !== false ||
    c.boundary?.review_case_events_written !== false ||
    d.boundary?.review_case_events_written !== false ||
    deltaGate.events_written !== 0 ||
    existsSync(path.join(root, PACKET_EVENTS_REL))
  ) {
    code("review_case_event_written", "no Review Case event may be written");
  }

  return { ok: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// tests
// ---------------------------------------------------------------------------

test("artifacts parse with the declared schema, kind, lifecycle and non-authoritative flag", () => {
  for (const [label, artifact, schema, kind] of [
    ["contract", contract, SCHEMA, KIND],
    ["delta", delta, DELTA_SCHEMA, "m210-s04-event-submission-delta"],
    ["state", state, STATE_SCHEMA, "m210-s04-review-session-state"],
  ]) {
    assert.equal(artifact.schema, schema, `${label} schema`);
    assert.equal(artifact.kind, kind, `${label} kind`);
    assert.equal(artifact.milestone, MILESTONE, `${label} milestone`);
    assert.equal(artifact.slice, SLICE, `${label} slice`);
    assert.equal(artifact.task, TASK, `${label} task`);
    assert.deepEqual(artifact.lifecycle, LIFECYCLE, `${label} lifecycle`);
    assert.equal(artifact.authoritative, false, `${label} authoritative`);
    assert.equal(artifact.ascii_only, true, `${label} ascii_only`);
    assert.equal(artifact.status_effect, "unchanged", `${label} status_effect`);
  }
  assert.equal(contract.packet_id, PACKET_ID);
  assert.equal(delta.packet_id, PACKET_ID);
  assert.equal(state.packet_id, PACKET_ID);
});

test("the committed session bundle validates clean", () => {
  const result = validateSession(baseBundle, liveEnv());
  assert.deepEqual(result.errors, [], JSON.stringify(result.errors, null, 2));
  assert.equal(result.ok, true);
});

test("every binding resolves to the live immutable input", () => {
  const env = liveEnv();
  assert.equal(contract.cards_binding.sha256, env.liveCardsSha);
  assert.equal(contract.cards_binding.card_count, FINDING_IDS.length);
  assert.equal(contract.matrix_binding.sha256, env.liveMatrixSha);
  assert.equal(contract.matrix_binding.row_count, FINDING_IDS.length);
  assert.equal(contract.reviewed_git_revision, env.liveReviewedGitRevision);
  assert.match(contract.reviewed_git_revision, new RegExp(GIT_PATTERN_SOURCE));
  assert.equal(contract.packet_binding.content_sha256, env.livePacketSha);
  assert.equal(contract.packet_binding.source_content_sha256, cards.review_case.source_content_sha256);
  assert.equal(contract.session_state_binding.sha256, env.liveStateSha);
  assert.equal(delta.bound_to_session_contract.sha256, env.liveContractSha);
  assert.equal(delta.bound_to_session_contract.path, CONTRACT_REL);
  assert.equal(delta.bound_to_session_contract.schema, SCHEMA);
});

test("the session state keeps all 19 answers null and the outcome on hold", () => {
  assert.equal(state.session_run, false);
  assert.equal(state.confirmed_count, 0);
  assert.equal(state.events_written, 0);
  assert.equal(state.choices_made, 0);
  assert.equal(state.preselected_count, 0);
  assert.equal(state.agent_confirmed_count, 0);
  assert.equal(state.read_backs_verified, 0);
  assert.equal(state.submission_gate_applied, false);
  assert.equal(state.sanctioned_stop, true);
  assert.equal(state.outcome, "hold");
  const keys = Object.keys(state.per_finding_answers);
  assert.deepEqual([...keys].sort(), [...FINDING_IDS].sort());
  assert.equal(keys.length, 19);
  for (const key of keys) assert.equal(state.per_finding_answers[key], null, key);
  assert.match(state.hold_basis, /actor-bound record_human_disposition/);
  assert.match(state.hold_is_not, /adoption/);
});

test("every submission gate and variant stays inert", () => {
  assert.equal(contract.submission_gate.applied, false);
  assert.equal(delta.gate.applied, false);
  assert.equal(delta.gate.actor_bound_path_available, false);
  assert.equal(delta.gate.submit_command_implemented, false);
  assert.equal(delta.gate.events_written, 0);
  assert.equal(contract.submission_gate.actor_bound_path_available, false);
  assert.equal(contract.submission_gate.agent_may_submit, false);
  assert.equal(contract.submission_gate.existing_s02_acceptance_is_disposition_authority, false);
  for (const variant of delta.gate.variants) {
    assert.equal(variant.activated, false, variant.id);
    assert.ok(typeof variant.reason === "string" && variant.reason.trim() !== "", variant.id);
  }
  const variantIds = delta.gate.variants.map((variant) => variant.id);
  for (const required of ["subjective_uat_reuse", "caller_asserted_human", "agent_self_submission"]) {
    assert.ok(variantIds.includes(required), required);
  }
  assert.equal(contract.adoption_basis.variant, "C");
  assert.equal(contract.adoption_basis.is_disposition_authority, false);
  assert.equal(contract.adoption_basis.criterion_id, F18_CRITERION_ID);
});

test("the read-back contract carries the full echo set and a deterministic event identity", () => {
  assert.equal(contract.read_back.required, true);
  assert.equal(contract.read_back.after_each_answer, true);
  assert.deepEqual([...contract.read_back.echo_fields].sort(), [...READBACK_ECHO_FIELDS].sort());
  const eventId = contract.read_back.event_id;
  assert.equal(eventId.role, "deterministic_identity_of_future_event");
  assert.equal(eventId.artifact_status, "specification_only_no_event_created");
  assert.equal(eventId.event_created, false);
  assert.equal(eventId.identity_version, EVENT_IDENTITY_VERSION);
  assert.deepEqual(eventId.closed_field_inputs, EVENT_IDENTITY_INPUTS);
  assert.equal(eventId.closed_field_inputs.length, 7);
  assert.ok(eventId.closed_field_inputs.includes("event_id") === false);
  assert.equal(eventId.canonicalization.order, "closed_field_inputs_array_order");
  assert.equal(eventId.canonicalization.serialization, "json_array_no_insignificant_whitespace");
  assert.equal(eventId.canonicalization.implementation_status, "specified_not_implemented");
  assert.equal(contract.read_back.comparison.mode, "exact_event_id_and_confirmed_fields");
  assert.equal(contract.read_back.comparison.event_id_mismatch_is_failure, true);
  assert.equal(contract.read_back.comparison.missing_event_id_is_failure, true);
  assert.deepEqual([...contract.read_back.comparison.must_compare].sort(), [...READBACK_ECHO_FIELDS].sort());
  assert.ok(!JSON.stringify(contract).includes("event_created\": true"));
});

test("the event identity pins the exact version and the ordered closed seven inputs", () => {
  const inputs = [...EVENT_IDENTITY_INPUTS];
  assert.equal(contract.read_back.event_id.identity_version, EVENT_IDENTITY_VERSION);
  assert.deepEqual(contract.read_back.event_id.closed_field_inputs, inputs);
  const cases = [
    ["version swap", (b) => { b.contract.read_back.event_id.identity_version = "review-case-event-identity/v2"; }, "event_identity_version_not_pinned"],
    ["input added", (b) => { b.contract.read_back.event_id.closed_field_inputs.push("extra_input"); }, "event_identity_inputs_not_canonical"],
    ["input dropped", (b) => { b.contract.read_back.event_id.closed_field_inputs.pop(); }, "event_identity_inputs_not_canonical"],
    ["input renamed", (b) => { b.contract.read_back.event_id.closed_field_inputs[0] = "packet"; }, "event_identity_inputs_not_canonical"],
    ["input reordered", (b) => { b.contract.read_back.event_id.closed_field_inputs = [...inputs].reverse(); }, "event_identity_inputs_not_canonical"],
    ["canonicalization unpinned", (b) => { b.contract.read_back.event_id.canonicalization.serialization = "unspecified"; }, "event_identity_inputs_not_canonical"],
  ];
  for (const [label, apply, expected] of cases) {
    const bundle = cloneBundle();
    apply(bundle);
    const names = new Set(validateSession(bundle, liveEnv()).errors.map((error) => error.name));
    assert.ok(
      names.has(expected),
      `${label} must emit ${expected}; got [${[...names].sort().join(",")}]`,
    );
  }
});

test("the future event identity is host-derived and never a caller argv input", () => {
  const eventId = contract.read_back.event_id;
  assert.equal(eventId.derivation.owner, EVENT_IDENTITY_OWNER);
  assert.equal(eventId.derivation.host_derived, true);
  assert.equal(eventId.derivation.caller_supplied_event_id_forbidden, true);
  assert.equal(eventId.derivation.derived_before_persistence, true);
  assert.equal(eventId.derivation.verified_against_canonical_inputs_before_readback, true);
  assert.equal(eventId.derivation.missing_derivation_requirement_is_failure, true);
  assert.equal(contract.submission_gate.applied_requires.path, HOST_SUBMISSION_PATH);
  assert.equal(contract.submission_gate.applied_requires.path_owner, "host");
  assert.equal(contract.submission_gate.applied_requires.caller_supplied_path_forbidden, true);
  assert.equal(delta.command_policy.executable_path_token, HOST_PATH_TOKEN);
  assert.equal(delta.command_policy.executable_path_owner, "host");
  assert.equal(delta.command_policy.caller_supplied_executable_forbidden, true);
  for (const command of delta.commands) {
    assert.equal(command.executable_path_token, HOST_PATH_TOKEN, command.id);
    assert.equal(command.executable_path_owner, "host", command.id);
    assert.equal(command.argv[0], HOST_PATH_TOKEN, command.id);
    assert.ok(!command.argv.includes("--event-id"), command.id);
    assert.ok(!command.argv.includes("{event_id}"), command.id);
  }
  const cases = [
    ["caller event-id injected", (b) => { b.delta.commands[0].argv.push("--event-id", "{event_id}"); }, "caller_supplied_event_id_forbidden"],
    ["derivation requirement missing", (b) => { delete b.contract.read_back.event_id.derivation.verified_against_canonical_inputs_before_readback; }, "event_identity_not_host_derived"],
    ["derivation requirement false", (b) => { b.contract.read_back.event_id.derivation.host_derived = false; }, "event_identity_not_host_derived"],
    ["caller executable substituted", (b) => { b.delta.commands[0].argv[0] = "{caller_executable}"; }, "host_controlled_path_substituted"],
    ["submission path substituted", (b) => { b.contract.submission_gate.applied_requires.path = "caller-asserted path"; }, "host_controlled_path_substituted"],
    ["path owner substituted", (b) => { b.contract.submission_gate.applied_requires.path_owner = "caller"; }, "host_controlled_path_substituted"],
  ];
  for (const [label, apply, expected] of cases) {
    const bundle = cloneBundle();
    apply(bundle);
    const names = new Set(validateSession(bundle, liveEnv()).errors.map((error) => error.name));
    assert.ok(
      names.has(expected),
      `${label} must emit ${expected}; got [${[...names].sort().join(",")}]`,
    );
  }
});

test("the two revision namespaces stay distinct with no fake mapping", () => {
  const tested = contract.revision_namespaces.tested_source_revision;
  const reviewed = contract.revision_namespaces.reviewed_git_revision;
  assert.equal(tested.namespace, "sha256_content_digest");
  assert.equal(tested.pattern, SHA_PATTERN_SOURCE);
  assert.equal(tested.subject, MATRIX_REL);
  assert.equal(tested.whole_tree_aggregate, false);
  assert.equal(tested.interchangeable_with_reviewed_git_revision, false);
  assert.equal(reviewed.namespace, "git_commit");
  assert.equal(reviewed.pattern, GIT_PATTERN_SOURCE);
  assert.equal(reviewed.interchangeable_with_tested_source_revision, false);
  assert.equal(contract.revision_namespaces.cross_namespace_mapping, "forbidden");
  assert.notEqual(
    contract.matrix_binding.sha256.replace(/^sha256:/, ""),
    contract.reviewed_git_revision,
  );
  const boundNames = contract.required_future_proof.bindings.map((item) => item.name).sort();
  assert.deepEqual(boundNames, ["reviewed_git_revision", "tested_source_revision"]);
  assert.equal(contract.required_future_proof.fake_sha256_to_git_mapping_forbidden, true);
  assert.equal(contract.required_future_proof.unbound_revision_is_failure, true);
  assert.equal(contract.required_future_proof.confirmed_card_required, true);
});

test("the allowed choices, drift fingerprints and actor-bound requirements are complete", () => {
  assert.deepEqual([...contract.allowed_choices].sort(), [...ALLOWED_CHOICES].sort());
  const fingerprintNames = contract.drift_policy.fingerprints.map((item) => item.name).sort();
  assert.deepEqual(fingerprintNames, [...DRIFT_FINGERPRINTS].sort());
  assert.equal(contract.drift_policy.invalidates_proposal, true);
  assert.equal(contract.drift_policy.recording_forbidden, true);
  assert.deepEqual(
    [...contract.submission_gate.forbidden_actor_sources].sort(),
    [...FORBIDDEN_ACTOR_SOURCES].sort(),
  );
  const named = contract.submission_gate.named_fail_closed.map((item) => item.code);
  for (const name of NAMED_FAIL_CLOSED) assert.ok(named.includes(name), name);
  assert.equal(contract.submission_gate.caller_supplied_identity_insufficient, true);
  assert.deepEqual(
    contract.submission_gate.caller_supplied_fields_insufficient,
    ["actor_class=HUMAN", "nonempty actor_id"],
  );
  for (const key of HOST_AUTHORITY_FIELDS) {
    assert.equal(contract.submission_gate.applied_requires[key], true, key);
  }
});

test("commands are argv-only, unavailable and unexecuted", () => {
  assert.equal(delta.command_policy.argv_only, true);
  assert.equal(delta.command_policy.shell_string_forbidden, true);
  assert.equal(delta.command_policy.executed_commands, 0);
  assert.ok(delta.commands.length >= 1);
  for (const command of delta.commands) {
    assert.equal(command.available, false, command.id);
    assert.equal(command.executed, false, command.id);
    assert.equal(command.argv_only, true, command.id);
    assert.equal(command.shell_string, false, command.id);
    assert.ok(Array.isArray(command.argv) && command.argv.length > 0, command.id);
    assert.ok(command.argv.every((token) => typeof token === "string" && token.trim() !== ""), command.id);
  }
  assert.ok(!committedDeltaText.includes('"executed": true'));
  assert.ok(!committedContractText.includes('"executed": true'));
});

test("the fail-closed code set is closed and shared by all three artifacts", () => {
  const expected = sortedJson(EMITTABLE_CODES);
  assert.equal(sortedJson(contract.fail_closed_codes), expected);
  assert.equal(sortedJson(delta.fail_closed_codes), expected);
  assert.equal(sortedJson(state.fail_closed_codes), expected);
  assert.equal(new Set(EMITTABLE_CODES).size, EMITTABLE_CODES.length);
});

test("the documented comment set matches EMITTABLE_CODES exactly", () => {
  const source = readRelative(CONTRACT_SELF_REL);
  const block = source.split("DOCUMENTED_CODES_BEGIN")[1]?.split("DOCUMENTED_CODES_END")[0];
  assert.ok(typeof block === "string" && block.length > 0, "the documented code block is missing");
  const documented = [...block.matchAll(/^\/\/ ([a-z][a-z0-9_]*):/gm)].map((match) => match[1]);
  assert.equal(sortedJson(documented), sortedJson(EMITTABLE_CODES));
});

test("the artifacts are canonical ASCII with no raw marker, timestamp or runtime claim", () => {
  for (const [label, text] of [
    ["contract", committedContractText],
    ["delta", committedDeltaText],
    ["state", committedStateText],
  ]) {
    assert.ok(!/[\u0080-\uffff]/.test(text), `${label} carries a non-ASCII code point`);
    assert.ok(!ISO_TIMESTAMP_RE.test(text), `${label} carries an ISO timestamp`);
    assert.ok(!/generated_at|captured_at/.test(text), `${label} carries a generation clock`);
    for (const marker of RAW_TEXT_MARKERS) {
      assert.ok(!text.includes(marker), `${label} carries raw marker ${marker}`);
    }
    for (const marker of RUNTIME_MARKERS) {
      assert.ok(!text.includes(marker), `${label} carries runtime marker ${marker}`);
    }
  }
});

test("the design-only boundary holds: no event, no submission, no promotion, no crate", () => {
  for (const [label, artifact] of [
    ["contract", contract],
    ["delta", delta],
    ["state", state],
  ]) {
    const boundary = artifact.boundary ?? {};
    assert.equal(boundary.review_case_events_written, false, `${label} events`);
    assert.equal(boundary.record_human_disposition_called, false, `${label} record_human_disposition`);
    assert.notEqual(boundary.submit_command_implemented, true, `${label} submit command`);
    assert.equal(boundary.requirement_status_mutated, false, `${label} requirement mutation`);
    assert.deepEqual(boundary.requirements_promoted, [], `${label} requirement promotion`);
    assert.deepEqual(boundary.crates_touched, [], `${label} crates`);
    assert.deepEqual(boundary.source_artifacts_rewritten, [], `${label} rewrites`);
    assert.equal(boundary.runtime_touched, false, `${label} runtime`);
  }
  assert.equal(relativeExists(PACKET_EVENTS_REL), false, "the packet events directory must be absent");
  assert.equal(relativeExists(TRUST_BOUNDARY_REL), true, "the trust boundary reference must exist");
  const trustBoundary = JSON.parse(readRelative(TRUST_BOUNDARY_REL));
  assert.equal(trustBoundary.actor_bound_path_available, false);
  const boundaryKinds = Array.isArray(trustBoundary.trust_boundary)
    ? trustBoundary.trust_boundary.map((item) => item.kind)
    : [];
  for (const kind of ["caller_supplied_actor", "validation_only", "cli_no_submit_branch"]) {
    assert.ok(boundaryKinds.includes(kind), kind);
  }
  assert.equal(matrix.review_case.actor_bound_scope, "record_human_disposition");
  assert.equal(matrix.review_case.actor_bound_path_available, false);
  assert.equal(matrix.review_case.human_disposition_event_count, 0);
});

test("the review-case runtime still exposes no submit command and no authority binding", () => {
  const cliText = readRelative(CLI_REL);
  assert.ok(!/record-human-disposition/.test(cliText), "no submit subcommand may exist");
  assert.ok(!/review_case_command\s*==\s*"submit"/.test(cliText), "no submit branch may exist");
  assert.match(cliText, /"register",/);
  assert.match(cliText, /"validate",/);
  const applicationText = readRelative(APPLICATION_REL);
  assert.match(applicationText, /_require_human_actor/);
  assert.match(applicationText, /actor_class: ActorClass = ActorClass\.HUMAN/);
  assert.match(applicationText, /actor_id: str/);
});

test("this contract source is offline, ASCII and clock-free", () => {
  const source = readRelative(CONTRACT_SELF_REL);
  const joined = (...parts) => parts.join("");
  assert.ok(!/[\u0080-\uffff]/.test(source), "the contract source carries a non-ASCII code point");
  assert.ok(!source.includes(joined("child", "_process")), "the contract must stay offline");
  assert.ok(!source.includes(joined("spawn", "Sync")), "the contract must stay offline");
  assert.ok(!source.includes(joined("writeFile", "Sync")), "the contract must not write");
  assert.ok(!source.includes(joined("appendFile", "Sync")), "the contract must not write");
  assert.ok(!source.includes(joined("Date", ".now")), "the contract must be clock-free");
  assert.ok(!source.includes(joined("new ", "Date(")), "the contract must be clock-free");
  assert.ok(!source.includes(joined("node:", "http")), "the contract must not open a network");
  assert.ok(!source.includes(joined("fetch", "(")), "the contract must not open a network");
  const modules = [...source.matchAll(/^import\s+[^;]*?from\s+"([^"]+)";/gm)].map(
    (match) => match[1],
  );
  assert.deepEqual(modules.sort(), [
    "node:assert/strict",
    "node:crypto",
    "node:fs",
    "node:path",
    "node:test",
    "node:url",
  ]);
});

test("CODE_COVERAGE: every documented fail-closed code is emitted by a mutation", () => {
  const mutations = [
    ["blanket_confirmation_forbidden", (bundle) => { bundle.contract.rules.blanket_confirmation_forbidden = false; }],
    ["preselect_forbidden", (bundle) => { bundle.contract.rules.preselect_forbidden = false; }],
    ["agent_confirmation_forbidden", (bundle) => { bundle.contract.rules.agent_confirmation_forbidden = false; }],
    ["recommendation_as_consent", (bundle) => { bundle.contract.rules.recommendation_is_not_consent = false; }],
    ["unconfirmed_answer_recorded", (bundle) => { bundle.contract.rules.persist_only_confirmed = false; }],
    ["readback_missing", (bundle) => { bundle.contract.rules.ledger_readback_verified_per_choice = false; }],
    ["event_id_missing", (bundle) => { bundle.contract.read_back.event_id.artifact_status = "created"; }],
    ["event_id_mismatch", (bundle) => { bundle.contract.read_back.comparison.event_id_mismatch_is_failure = false; }],
    ["event_identity_version_not_pinned", (bundle) => { bundle.contract.read_back.event_id.identity_version = "review-case-event-identity/v2"; }],
    ["event_identity_inputs_not_canonical", (bundle) => { bundle.contract.read_back.event_id.closed_field_inputs = ["packet_id", "finding_id", "selected_disposition", "actor_ref", "acceptance_ref", "authority_epoch"]; }],
    ["event_identity_not_host_derived", (bundle) => { bundle.contract.read_back.event_id.derivation.owner = "caller"; }],
    ["caller_supplied_event_id_forbidden", (bundle) => { bundle.delta.commands[0].argv.push("--event-id", "{event_id}"); }],
    ["host_controlled_path_substituted", (bundle) => { bundle.delta.commands[0].argv[0] = "{caller_executable}"; }],
    ["drift_invalidates_proposal", (bundle) => { bundle.contract.drift_policy.recording_forbidden = false; }],
    ["revision_namespace_confused", (bundle) => { bundle.contract.revision_namespaces.tested_source_revision.pattern = "^[0-9a-f]{40}$"; }],
    ["revision_unbound", (bundle) => { bundle.contract.reviewed_git_revision = "0".repeat(40); }],
    ["submission_without_actor_bound_path", (bundle) => { bundle.delta.gate.applied = true; }],
    ["actor_bound_scope_confused", (bundle) => { bundle.contract.submission_gate.actor_bound_scope = "subjective_uat"; }],
    ["self_asserted_identity", (bundle) => { bundle.contract.submission_gate.caller_supplied_identity_insufficient = false; }],
    ["authority_binding_missing", (bundle) => { bundle.contract.submission_gate.applied_requires.host_authority_verified = false; }],
    ["forbidden_actor_source", (bundle) => { bundle.contract.submission_gate.forbidden_actor_sources = []; }],
    ["agent_may_not_submit", (bundle) => { bundle.contract.submission_gate.agent_may_submit = true; }],
    ["choice_not_allowed", (bundle) => { bundle.contract.allowed_choices = ["accept_as_proposed", "defer"]; }],
    ["shell_string_command", (bundle) => { bundle.delta.commands[0].shell_string = true; }],
    ["argv_not_array", (bundle) => { bundle.delta.commands[0].argv = "uv run python"; }],
    ["contract_hash_mismatch", (bundle) => { bundle.delta.bound_to_session_contract.sha256 = `sha256:${"0".repeat(64)}`; }],
    ["session_state_inconsistent", (bundle) => { bundle.state.confirmed_count = 1; }],
    ["review_case_event_written", (bundle) => { bundle.state.events_written = 1; }],
    ["non_ascii_artifact", (bundle) => { bundle.contract.packet_id = "RC-2026-09-10-001\u00e9"; }],
    ["raw_text_leak", (bundle) => { bundle.contract.packet_id = "RC-2026-09-10-001<x>"; }],
  ];
  assert.equal(mutations.length, EMITTABLE_CODES.length, "one mutation per documented code");
  const emitted = new Set();
  for (const [expectedCode, apply] of mutations) {
    const bundle = cloneBundle();
    apply(bundle);
    const result = validateSession(bundle, liveEnv());
    const names = new Set(result.errors.map((error) => error.name));
    assert.ok(
      names.has(expectedCode),
      `${expectedCode} was not emitted by its mutation; got [${[...names].sort().join(",")}]`,
    );
    for (const name of names) emitted.add(name);
  }
  const missing = EMITTABLE_CODES.filter((name) => !emitted.has(name));
  assert.deepEqual(missing, [], `codes with no triggering mutation: ${missing.join(",")}`);
  const unexpected = [...emitted].filter((name) => !EMITTABLE_CODES.includes(name));
  assert.deepEqual(unexpected, [], `undocumented emitted codes: ${unexpected.join(",")}`);
});

test("the committed bundle is not mutated by validation", () => {
  const before = JSON.stringify([contract, delta, state]);
  validateSession(baseBundle, liveEnv());
  assert.equal(JSON.stringify([contract, delta, state]), before);
});

test("emits the contract marker", () => {
  const result = validateSession(baseBundle, liveEnv());
  assert.equal(result.ok, true, JSON.stringify(result.errors));
  process.stdout.write(`${CONTRACT_MARKER}\n`);
});
