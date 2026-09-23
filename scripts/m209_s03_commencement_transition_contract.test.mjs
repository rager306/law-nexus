// M209 S03 T03 contract: the fail-closed commencement and transitional leg of
// R070 for the named `cc:44-fz` chain.
//
// The contract is offline by default and corpus-gated: when the untracked
// licensed provider export resolves it re-derives every slot of the declared
// denominator from the live manifest, the act exports under `exports/npa` and
// the tracked admission records, and compares the whole leg field by field;
// when it does not resolve it prints `M209_S03_CORPUS_ABSENT` and asserts the
// artifact-integrity block only.
//
// It also asserts that the documented fail-closed code block, the emitted
// artifact and the Rust `COMMENCEMENT_*` arrays carry exactly the same code
// sets, and that every documented code is empirically exercised by a mutant.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

const ARTIFACT = "prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json";
const CONTRACT_PATH = "scripts/m209_s03_commencement_transition_contract.test.mjs";
const RUST_MODULE = "crates/ln-consultant-parser/src/amendment_provenance.rs";
const RUST_BIN = "crates/ln-consultant-parser/src/bin/m209-amendment-provenance.rs";
const CARGO_MANIFEST = "crates/ln-consultant-parser/Cargo.toml";
const LIB_RS = "crates/ln-consultant-parser/src/lib.rs";

const T02_ARTIFACT = "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
const M201_GATE = "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json";
const M208_S03_DOC = "prd/architecture/m208-s03-admission-commencement.md";
const M208_S04_DOC = "prd/architecture/m208-s04-admission-bounded-replay.md";
const M207_PROTOCOL = "prd/annotation/m207-s04-c4-protocol.md";
const M207_RECEIPT = "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json";

const FROZEN_M201 = [
  "prd/migration/rust-evidence/m201-s03-tracked-chain.json",
  "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json",
  "prd/architecture/fz44-tracked-edition-chain.yaml",
];

const EXPORT_DIR_ENV = "CONSULTANT_EXPORT_DIR";
const EXPORT_DIR_DEFAULT = "consru_export";
const EXPORT_ROOT_TAIL = "consru_export";
const LAYER1_MANIFEST_TAIL = "manifest_layer1_44fz_and_amending_laws.jsonl";
const NPA_TAIL = "exports/npa";

const SCHEMA = "law-nexus/r070-commencement-transition/v1";
const KIND = "m209-s03-commencement-transition";
const TASK = "T03";
const LIFECYCLE = "[bounded]";
const REQUIREMENT_ID = "R070";
const DISPOSITION = "active";
const DISPOSITION_DECISION = "D416";
const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/;

// Grounding pins of the accepted revision (T03 plan, cross-checked with T02).
const EXPECTED_LAYER1_RECORDS = 122;
const EXPECTED_LAYER1_AMENDING = 121;
const EXPECTED_AMENDS_EDGES = 120;

const REQUIRED_EVIDENCE_CLASS = "human-annotation";
const REQUIRED_EVIDENCE_STATUS = "absent";
const TRANSITIONAL_JUSTIFICATION_ID = "m201-frozen-commencement-boundary";
const FROZEN_GATE_CLAIM = {
  evidence_class: "hypothesized_from_oracle_diff",
  commencement_rule_ref: "rec:commencement:484-93:hypothesized",
  transitional: "explicitly_absent",
};

const SLOT_KINDS = ["named-chain", "amending-act"];
const EVIDENCE_CLASSES = ["absent", "editorial_hint", "hypothesized_from_oracle_diff"];
const SLOT_VERDICTS = ["explicitly-absent", "slot-filled-not-proven"];
const TRANSITIONAL_VALUES = ["explicitly_absent", "unresolved"];

const INPUT_IDS = [
  "layer1_manifest",
  "t02_amending_act_evidence",
  "m201_r070_proof_gate",
  "m208_s03_admission",
  "m208_s04_admission",
  "m207_c4_protocol",
  "m207_c4_receipt",
];

// The complete reason-code set. The `## Reason codes` comment block below is
// asserted to document exactly this set (no more, no less), and the same set is
// asserted equal to the artifact's `reason_codes` field and to the Rust
// `COMMENCEMENT_REASON_CODES` array.
const REASON_CODES = [
  "no-legislative-commencement-source",
  "m207-human-pilot-absent",
  "m208-s03-not-adopted",
  "act-text-not-admitted",
];

// ## Reason codes (documented set; asserted equal to REASON_CODES)
// DOCUMENTED_REASON_CODES_BEGIN
// no-legislative-commencement-source: the slot's act text is admitted and inspectable, but no admitted Legislative commencement source exists for it; the frozen M201 boundary is the only filled slot and it stays an unproven hypothesized class (D415).
// m207-human-pilot-absent: the M208/S04 checkpoint no longer declares the human-pilot-absent markers, or the M207/S04 C4 operational receipt no longer claims a non-pass acceptance with unmeasured rates, so the declared reason itself has changed.
// m208-s03-not-adopted: a M208 commencement checkpoint no longer declares admission: not-adopted, owner_admission_ref: none and runtime_work: not-started, so the boundary premise itself has changed.
// act-text-not-admitted: the slot's declared identity pair resolves to no act text in the evaluated revision, so the slot carries nothing that could even be examined for a commencement source.
// DOCUMENTED_REASON_CODES_END

// The complete fail-closed code set.
const FAIL_CLOSED_CODES = [
  "input_absent",
  "input_hash_mismatch",
  "family_count_unsupported",
  "zero_denominator",
  "non_ascii_evidence",
  "raw_text_leak",
  "legislative_upgrade_attempt",
  "vocabulary_minted",
  "date-as-commencement",
  "no-legislative-commencement-source",
  "m207-human-pilot-absent",
  "m208-s03-not-adopted",
  "act-text-not-admitted",
];

// ## Fail-closed codes (documented set; asserted equal to FAIL_CLOSED_CODES)
// DOCUMENTED_FAIL_CLOSED_BEGIN
// input_absent: a declared input path is absent from disk, or the tracked artifact is missing in `--check` mode.
// input_hash_mismatch: the live input pin (sha256 or byte count) differs from the pin recorded in the tracked artifact, or a recorded pin is malformed.
// family_count_unsupported: the declaration itself is unsupported — schema, kind, lifecycle, requirement or disposition drift, a denominator that does not reproduce the T02 amending-act denominator, a slot row that does not cover the denominator, a partition that does not sum to it, a live slot or partition that differs, a named-chain slot that drifted from the frozen boundary, a missing required evidence class, or a non-empty class_matched_ids.
// zero_denominator: the declared slot total or amending-act total is zero or not a positive integer; a zero denominator is not a measurement.
// non_ascii_evidence: the artifact bytes carry a non-ASCII byte, or a partition key is not ASCII.
// raw_text_leak: the artifact carries provider prose (a corpus text marker) or a partition key outside the count-only token rule.
// legislative_upgrade_attempt: a slot carries the string `legislative` as an evidence-class value, or an amending-act slot claims commencement evidence the frozen boundary does not give it.
// vocabulary_minted: the artifact mints ActivationTrigger, TransitionalResolver, EvidenceAnchor or LegislativeEffect (D216).
// date-as-commencement: a commencement rule reference is date-shaped or file-name-shaped, or a filled evidence class carries no declared rule reference (D289).
// no-legislative-commencement-source: an amending-act slot records this reason for a slot whose admitted act text says otherwise.
// m207-human-pilot-absent: an amending-act slot records this reason, or the admission gate no longer carries the absent human pilot.
// m208-s03-not-adopted: an amending-act slot records this reason, or the admission gate no longer carries an unadopted M208 premise.
// act-text-not-admitted: an amending-act slot records this reason for a slot whose admitted act text says otherwise.
// DOCUMENTED_FAIL_CLOSED_END

// Provider prose markers that must never reach a count-only artifact.
const CORPUS_TEXT_MARKERS = ["consultantplus://", "<w:", "screenTip"];

// Ignored local overlays: never a durable evidence anchor.
const IGNORED_SOURCE_PREFIXES = [".gsd/", ".agents/", ".planning/", ".audits/", ".lex/"];

// The artifact must bound its own claims (D415 / D416 / D406 / D553).
const REQUIRED_NON_CLAIM_FRAGMENTS = [
  "no legislative upgrade (d415)",
  "not an adr-0021 resolver",
  "no resolver runtime exists",
  "r070 stays active (d416)",
  "class_matched_ids is an explicit empty set",
  "no commencement is inferred from a date, a file name or an edition",
  "frozen m201 r070 proof gate",
  "zero denominator is not a measurement",
  "d552",
];

const ALLOWED_TOKEN = /^[A-Za-z0-9_.:-]{1,64}$/;
const EXPORT_FILE = /^law_(\d{4}-\d{2}-\d{2})_(\d+)-fz_rev-([A-Za-z0-9-]+)_([0-9a-f]{8})\.xml$/;

// ---------------------------------------------------------------------------
// repository access
// ---------------------------------------------------------------------------

function readRepo(relative) {
  assert.ok(!path.isAbsolute(relative), `${relative} must be repository-relative`);
  for (const prefix of IGNORED_SOURCE_PREFIXES) {
    assert.ok(!relative.startsWith(prefix), `${relative} is an ignored overlay path`);
  }
  return readFileSync(path.join(root, relative), "utf8");
}

function isRepoRelative(value) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (path.isAbsolute(value)) return false;
  return value.split("/").every((part) => part !== "" && part !== ".." && part !== ".");
}

function corpusExportDir() {
  const fromEnv = process.env[EXPORT_DIR_ENV];
  return typeof fromEnv === "string" && fromEnv.trim() !== ""
    ? fromEnv.trim()
    : EXPORT_DIR_DEFAULT;
}

function exportRoot() {
  return path.resolve(root, corpusExportDir(), EXPORT_ROOT_TAIL);
}

// ---------------------------------------------------------------------------
// independent ports of the emitter's readers
// ---------------------------------------------------------------------------

function actDateFromTitle(title) {
  const needle = "от ";
  let search = 0;
  for (;;) {
    const offset = title.indexOf(needle, search);
    if (offset < 0) return null;
    const start = offset + needle.length;
    search = start;
    const candidate = [...title.slice(start)].slice(0, 10).join("");
    const bytes = Buffer.from(candidate, "utf8");
    if (
      bytes.length === 10 &&
      bytes[2] === 0x2e &&
      bytes[5] === 0x2e &&
      /^\d\d$/.test(candidate.slice(0, 2)) &&
      /^\d\d$/.test(candidate.slice(3, 5)) &&
      /^\d{4}$/.test(candidate.slice(6, 10))
    ) {
      return `${candidate.slice(6, 10)}-${candidate.slice(3, 5)}-${candidate.slice(0, 2)}`;
    }
  }
}

function actNumberFromLawNumber(lawNumber) {
  const index = lawNumber.indexOf("N");
  if (index < 0) return null;
  const match = /^\s*(\d+)/.exec(lawNumber.slice(index + 1));
  return match ? match[1] : null;
}

function npaNames() {
  return readdirSync(path.join(exportRoot(), NPA_TAIL)).sort();
}

function npaCandidates(names, date, number) {
  const prefix = `law_${date}_${number}-fz_rev-`;
  return names.filter((name) => {
    if (!name.startsWith(prefix) || !name.endsWith(".xml")) return false;
    const stem = name.slice(prefix.length, -4);
    const parts = stem.split("_");
    return parts.length === 2 && /^[0-9a-f]{8}$/.test(parts[1]);
  });
}

function readLayer1Manifest() {
  const bytes = readFileSync(path.join(exportRoot(), LAYER1_MANIFEST_TAIL));
  const records = [];
  for (const raw of bytes.toString("utf8").split("\n")) {
    const line = raw.trim();
    if (line === "") continue;
    records.push(JSON.parse(line));
  }
  return {
    input_bytes: bytes.length,
    input_sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
    records,
    hash: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
  };
}

/// Mirrors `star_field` in the Rust module.
function starField(text, name) {
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("**")) continue;
    const rest = line.slice(2);
    if (!rest.startsWith(name)) continue;
    const after = rest.slice(name.length);
    if (!(after.startsWith(":") || after.startsWith("*"))) continue;
    const value = after.replace(/^[:*\s]+/, "").split("**")[0].trim();
    if (value !== "") return value;
  }
  return null;
}

/// True when a value is date-shaped or file-name-shaped, never a rule reference.
function isDateOrFilename(value) {
  return (
    /^\d{4}-\d{2}-\d{2}$/.test(value) ||
    value.startsWith("law_") ||
    value.startsWith("edition-") ||
    value.endsWith(".xml") ||
    value.includes("rev-unknown")
  );
}

// ---------------------------------------------------------------------------
// live re-derivation of the whole leg
// ---------------------------------------------------------------------------

function deriveCommencementLive() {
  const exportDir = exportRoot();
  const manifest = readLayer1Manifest();
  const names = npaNames();
  const gate = JSON.parse(readRepo(M201_GATE));
  const t02 = JSON.parse(readRepo(T02_ARTIFACT));
  const s03Text = readRepo(M208_S03_DOC);
  const s04Text = readRepo(M208_S04_DOC);
  const receipt = JSON.parse(readRepo(M207_RECEIPT));

  const slots = [];
  let namedChainSlots = 0;
  let amendingActSlots = 0;
  const byEvidenceClass = Object.fromEntries(EVIDENCE_CLASSES.map((key) => [key, 0]));
  const bySlotVerdict = Object.fromEntries(SLOT_VERDICTS.map((key) => [key, 0]));
  const byReasonCode = Object.fromEntries(REASON_CODES.map((key) => [key, 0]));
  const byTransitional = Object.fromEntries(TRANSITIONAL_VALUES.map((key) => [key, 0]));

  for (const record of manifest.records) {
    const core = record.is_core_act === true;
    const actDate = actDateFromTitle(record.title) ?? "";
    const actNumber = actNumberFromLawNumber(record.law_number) ?? "";
    let actTextAdmitted = false;
    if (actDate !== "" && actNumber !== "") {
      actTextAdmitted =
        npaCandidates(names, actDate, actNumber).length > 0 ||
        existsSync(path.join(exportDir, NPA_TAIL, `law_${actDate}_${actNumber}-fz`));
    }
    let slot;
    if (core) {
      namedChainSlots += 1;
      slot = {
        document_key: record.document_key,
        slot_kind: "named-chain",
        act_number: actNumber,
        act_date: actDate,
        act_text_admitted: actTextAdmitted,
        evidence_class: gate.commencement_boundary.evidence_class,
        slot_verdict: "slot-filled-not-proven",
        reason_code: "no-legislative-commencement-source",
        transitional: gate.commencement_boundary.transitional,
        commencement_rule_ref: gate.commencement_boundary.commencement_rule_ref,
        transitional_basis_id: TRANSITIONAL_JUSTIFICATION_ID,
      };
    } else {
      amendingActSlots += 1;
      slot = {
        document_key: record.document_key,
        slot_kind: "amending-act",
        act_number: actNumber,
        act_date: actDate,
        act_text_admitted: actTextAdmitted,
        evidence_class: "absent",
        slot_verdict: "explicitly-absent",
        reason_code: actTextAdmitted
          ? "no-legislative-commencement-source"
          : "act-text-not-admitted",
        transitional: "unresolved",
        commencement_rule_ref: "",
        transitional_basis_id: "",
      };
    }
    byEvidenceClass[slot.evidence_class] += 1;
    bySlotVerdict[slot.slot_verdict] += 1;
    byReasonCode[slot.reason_code] += 1;
    byTransitional[slot.transitional] += 1;
    slots.push(slot);
  }

  return {
    slots,
    named_chain_slots: namedChainSlots,
    amending_act_slots: amendingActSlots,
    slots_total: slots.length,
    by_evidence_class: byEvidenceClass,
    by_slot_verdict: bySlotVerdict,
    by_reason_code: byReasonCode,
    by_transitional: byTransitional,
    manifest,
    frozen: {
      evidence_class: gate.commencement_boundary.evidence_class,
      commencement_rule_ref: gate.commencement_boundary.commencement_rule_ref,
      transitional: gate.commencement_boundary.transitional,
    },
    gate: {
      m208_s03_admission: starField(s03Text, "admission"),
      m208_s03_owner_admission_ref: starField(s03Text, "owner_admission_ref"),
      m208_s03_runtime_work: starField(s03Text, "runtime_work"),
      m208_s04_admission: starField(s04Text, "admission"),
      m208_s04_owner_admission_ref: starField(s04Text, "owner_admission_ref"),
      m208_s04_runtime_work: starField(s04Text, "runtime_work"),
      m207_c4_operational_acceptance: receipt.claims.operational_acceptance,
    },
    t02: {
      t02_layer1_records_total: t02.denominator.layer1_records_total,
      t02_layer1_amending_acts: t02.denominator.layer1_amending_acts,
      t02_amends_edges_total: t02.denominator.amends_edges_total,
    },
  };
}

// ---------------------------------------------------------------------------
// validator
// ---------------------------------------------------------------------------

function validateCommencementArtifact(artifact, env = {}) {
  const errors = [];
  const code = (name, detail) => errors.push({ code: name, detail });
  const text = env.artifactText ?? JSON.stringify(artifact);

  // 1. raw bytes: ASCII-only, count-only.
  if (text.length === 0) code("non_ascii_evidence", "artifact is empty");
  const offending = [...text].findIndex((character) => character.charCodeAt(0) > 0x7f);
  if (offending >= 0) code("non_ascii_evidence", `non-ascii character at index ${offending}`);
  for (const marker of CORPUS_TEXT_MARKERS) {
    if (text.includes(marker)) code("raw_text_leak", `corpus text marker ${marker}`);
  }

  // 2. envelope.
  if (artifact?.schema !== SCHEMA) code("family_count_unsupported", "schema mismatch");
  if (artifact?.kind !== KIND) code("family_count_unsupported", "kind mismatch");
  if (artifact?.task !== TASK) code("family_count_unsupported", "task mismatch");
  if (artifact?.lifecycle !== LIFECYCLE) code("family_count_unsupported", "lifecycle mismatch");
  if (artifact?.authoritative !== false) {
    code("family_count_unsupported", "authoritative must be false");
  }
  if (
    artifact?.requirement_id !== REQUIREMENT_ID ||
    artifact?.disposition !== DISPOSITION ||
    artifact?.disposition_decision !== DISPOSITION_DECISION
  ) {
    code("family_count_unsupported", "R070 disposition drift");
  }
  if (artifact?.count_only !== true || artifact?.ascii_only !== true) {
    code("family_count_unsupported", "count_only and ascii_only must both be true");
  }
  if (typeof artifact?.count_basis !== "string" || artifact.count_basis.trim() === "") {
    code("family_count_unsupported", "count_basis is missing");
  }
  if (!Array.isArray(artifact?.fail_closed_codes)) {
    code("family_count_unsupported", "fail_closed_codes is missing");
  } else if (sortJoin(artifact.fail_closed_codes) !== sortJoin(FAIL_CLOSED_CODES)) {
    code("family_count_unsupported", "fail_closed_codes drift");
  }
  for (const [field, expected] of [
    ["slot_kinds", SLOT_KINDS],
    ["evidence_classes", EVIDENCE_CLASSES],
    ["slot_verdicts", SLOT_VERDICTS],
    ["transitional_values", TRANSITIONAL_VALUES],
    ["reason_codes", REASON_CODES],
  ]) {
    if (!Array.isArray(artifact?.[field]) || sortJoin(artifact[field]) !== sortJoin(expected)) {
      code("family_count_unsupported", `${field} drift`);
    }
  }

  // 3. the required evidence class stays an explicit empty set.
  const required = artifact?.required_evidence;
  if (required?.required_evidence_class !== REQUIRED_EVIDENCE_CLASS) {
    code("family_count_unsupported", "required_evidence_class drift");
  }
  if (required?.required_evidence_status !== REQUIRED_EVIDENCE_STATUS) {
    code("family_count_unsupported", "required_evidence_status drift");
  }
  if (!Array.isArray(required?.class_matched_ids)) {
    code("family_count_unsupported", "class_matched_ids must be an array");
  } else if (required.class_matched_ids.length !== 0) {
    code("family_count_unsupported", "class_matched_ids must be an explicit empty set");
  }

  // 4. non-claims.
  if (!Array.isArray(artifact?.non_claims) || artifact.non_claims.length === 0) {
    code("family_count_unsupported", "non_claims is missing");
  } else {
    const joined = artifact.non_claims.join(" ").toLowerCase();
    for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
      if (!joined.includes(fragment)) {
        code("family_count_unsupported", `non-claim missing: ${fragment}`);
      }
    }
  }

  // 5. zero denominators.
  const denominator = artifact?.denominator;
  if (!Number.isInteger(denominator?.slots_total) || denominator.slots_total <= 0) {
    code("zero_denominator", "the declared slot total is not a positive integer");
  }
  if (!Number.isInteger(denominator?.amending_act_slots) || denominator.amending_act_slots <= 0) {
    code("zero_denominator", "the declared amending-act total is not a positive integer");
  }

  // 6. the named chain contributes exactly one slot.
  if (denominator?.named_chain_slots !== 1) {
    code("family_count_unsupported", "the named chain must contribute exactly one slot");
  }

  // 7. the two global premises the boundary is premised on.
  const gate = artifact?.admission_gate;
  if (
    gate?.m208_s03_admission !== "not-adopted" ||
    gate?.m208_s03_owner_admission_ref !== "none" ||
    gate?.m208_s03_runtime_work !== "not-started" ||
    gate?.m208_s04_admission !== "not-adopted" ||
    gate?.m208_s04_owner_admission_ref !== "none" ||
    gate?.m208_s04_runtime_work !== "not-started"
  ) {
    code("m208-s03-not-adopted", "the M208 commencement gate is no longer unadopted");
  }
  if (
    gate?.m207_human_pilot !== "absent" ||
    gate?.m207_c4_operational_acceptance !== "non-pass" ||
    gate?.m207_c4_rate_status !== "not-measured"
  ) {
    code("m207-human-pilot-absent", "the M207 human pilot absence no longer holds");
  }

  // 8. whole-artifact guards: no legislative value, no minted identifier.
  if (text.includes('"legislative"')) {
    code("legislative_upgrade_attempt", "the artifact carries the string legislative as a value");
  }
  for (const token of ["ActivationTrigger", "TransitionalResolver", "EvidenceAnchor", "LegislativeEffect"]) {
    if (text.includes(token)) code("vocabulary_minted", `the artifact mints ${token}`);
  }

  // 9. per-slot closed vocabularies and slot invariants.
  const frozen = artifact?.frozen_m201_boundary;
  if (
    frozen?.evidence_class !== FROZEN_GATE_CLAIM.evidence_class ||
    frozen?.commencement_rule_ref !== FROZEN_GATE_CLAIM.commencement_rule_ref ||
    frozen?.transitional !== FROZEN_GATE_CLAIM.transitional
  ) {
    code("family_count_unsupported", "the frozen M201 boundary block drifted");
  }
  if (artifact?.transitional_basis?.basis_id !== TRANSITIONAL_JUSTIFICATION_ID) {
    code("family_count_unsupported", "the transitional basis id drifted");
  }
  if (
    typeof artifact?.transitional_basis?.justification !== "string" ||
    artifact.transitional_basis.justification.trim() === ""
  ) {
    code("family_count_unsupported", "the transitional justification is missing");
  }

  let namedChainSeen = 0;
  let amendingSeen = 0;
  if (!Array.isArray(artifact?.slots)) {
    code("family_count_unsupported", "slots is missing");
  } else {
    for (const slot of artifact.slots) {
      if (!SLOT_KINDS.includes(slot?.slot_kind)) {
        code(slot?.reason_code ?? "no-legislative-commencement-source", "undocumented slot kind");
        continue;
      }
      if (!EVIDENCE_CLASSES.includes(slot?.evidence_class)) {
        code("legislative_upgrade_attempt", "undocumented evidence class");
      }
      if (!SLOT_VERDICTS.includes(slot?.slot_verdict)) {
        code(slot?.reason_code ?? "no-legislative-commencement-source", "undocumented slot verdict");
      }
      if (!TRANSITIONAL_VALUES.includes(slot?.transitional)) {
        code(slot?.reason_code ?? "no-legislative-commencement-source", "undocumented transitional value");
      }
      if (!REASON_CODES.includes(slot?.reason_code)) {
        code("no-legislative-commencement-source", "undocumented reason code");
        continue;
      }
      if (!Number.isInteger(slot?.document_key) || slot.document_key <= 0) {
        code(slot.reason_code, "a slot carries a non-positive catalog identifier");
      }
      for (const value of [slot?.commencement_rule_ref, slot?.transitional_basis_id]) {
        if (typeof value === "string" && value !== "" && isDateOrFilename(value)) {
          code("date-as-commencement", "a date or file name is used as a rule reference");
        }
      }
      if (slot.evidence_class !== "absent" && (slot?.commencement_rule_ref ?? "").trim() === "") {
        code("date-as-commencement", "a filled class carries no declared rule reference");
      }
      if (slot.slot_kind === "named-chain") {
        namedChainSeen += 1;
        if (
          slot.evidence_class !== frozen?.evidence_class ||
          slot.commencement_rule_ref !== frozen?.commencement_rule_ref ||
          slot.transitional !== frozen?.transitional
        ) {
          code("family_count_unsupported", "the named-chain slot drifted from the frozen boundary");
        }
      }
      if (slot.slot_kind === "amending-act") {
        amendingSeen += 1;
        if (
          slot.evidence_class !== "absent" ||
          (slot.commencement_rule_ref ?? "") !== "" ||
          (slot.transitional_basis_id ?? "") !== ""
        ) {
          code("legislative_upgrade_attempt", "an amending-act slot claims commencement evidence");
        }
        const expected = slot.act_text_admitted
          ? "no-legislative-commencement-source"
          : "act-text-not-admitted";
        if (slot.reason_code !== expected) {
          code(slot.reason_code, "an amending-act slot does not justify its own reason code");
        }
      }
    }
    if (namedChainSeen !== denominator?.named_chain_slots) {
      code("family_count_unsupported", "the named-chain slot count drifted");
    }
    if (amendingSeen !== denominator?.amending_act_slots) {
      code("family_count_unsupported", "the amending-act slot count drifted");
    }
  }

  // 10. the declared denominator reproduces T02, and the rows cover it.
  if (
    denominator?.t02_layer1_records_total !== EXPECTED_LAYER1_RECORDS ||
    denominator?.t02_layer1_amending_acts !== EXPECTED_LAYER1_AMENDING ||
    denominator?.t02_amends_edges_total !== EXPECTED_AMENDS_EDGES
  ) {
    code("family_count_unsupported", "the T02 amending-act denominator drifted");
  }
  if (denominator?.slots_total !== denominator?.t02_layer1_records_total) {
    code("family_count_unsupported", "the slots do not reproduce the T02 denominator");
  }
  if (denominator?.amending_act_slots !== denominator?.t02_layer1_amending_acts) {
    code("family_count_unsupported", "the amending-act slots do not reproduce the T02 denominator");
  }
  if (
    Number.isInteger(denominator?.named_chain_slots) &&
    Number.isInteger(denominator?.amending_act_slots) &&
    Number.isInteger(denominator?.slots_total) &&
    denominator.named_chain_slots + denominator.amending_act_slots !== denominator.slots_total
  ) {
    code("family_count_unsupported", "the slot kinds do not sum to the declared denominator");
  }
  if (!Array.isArray(artifact?.slots) || artifact.slots.length !== denominator?.slots_total) {
    code("family_count_unsupported", "the per-slot rows do not cover the declared denominator");
  }

  // 11. partitions sum to the denominator and stay count-only tokens.
  for (const [label, partition] of [
    ["by_evidence_class", denominator?.by_evidence_class],
    ["by_slot_verdict", denominator?.by_slot_verdict],
    ["by_reason_code", denominator?.by_reason_code],
    ["by_transitional", denominator?.by_transitional],
  ]) {
    if (!partition || typeof partition !== "object" || Array.isArray(partition)) {
      code("family_count_unsupported", `${label} is missing`);
      continue;
    }
    let sum = 0;
    for (const [key, value] of Object.entries(partition)) {
      if (!Number.isInteger(value) || value < 0) {
        code("family_count_unsupported", `${label} part ${key} is not a count`);
        continue;
      }
      sum += value;
      if (!/^[\x20-\x7f]*$/.test(key)) {
        code("non_ascii_evidence", `${label} key is not ascii`);
      } else if (!ALLOWED_TOKEN.test(key)) {
        code("raw_text_leak", `${label} key ${key} is outside the count-only token rule`);
      }
    }
    if (Number.isInteger(denominator?.slots_total) && denominator.slots_total > 0 && sum !== denominator.slots_total) {
      code("family_count_unsupported", `${label} sums to ${sum}, not ${denominator.slots_total}`);
    }
  }

  // 12. declared input pins: shape and existence.
  if (!Array.isArray(artifact?.inputs) || artifact.inputs.length === 0) {
    code("family_count_unsupported", "inputs is missing");
  } else {
    const seen = new Set();
    for (const pin of artifact.inputs) {
      const id = typeof pin?.input_id === "string" ? pin.input_id : "<unnamed>";
      if (seen.has(id)) code("family_count_unsupported", `duplicate input pin ${id}`);
      seen.add(id);
      if (!isRepoRelative(pin?.relative_path)) {
        code("family_count_unsupported", `input ${id} path is not repository-relative`);
      }
      if (typeof pin?.input_sha256 !== "string" || !SHA_PATTERN.test(pin.input_sha256)) {
        code("input_hash_mismatch", `input ${id} sha256 pin is malformed`);
      }
      if (!Number.isInteger(pin?.input_bytes) || pin.input_bytes <= 0) {
        code("input_hash_mismatch", `input ${id} byte pin is malformed`);
      }
      if (typeof env.exists === "function" && !env.exists(pin?.relative_path)) {
        code("input_absent", `input ${id} is absent: ${pin?.relative_path}`);
      }
    }
  }

  // 13. live re-derivation.
  const live = env.live;
  if (live) {
    for (const pin of artifact?.inputs ?? []) {
      const observed = live.inputs?.[pin?.input_id];
      if (!observed) continue;
      if (
        observed.input_bytes !== pin.input_bytes ||
        observed.input_sha256 !== pin.input_sha256
      ) {
        code("input_hash_mismatch", `input ${pin.input_id} live pin differs`);
      }
    }
    if (live.slots) {
      const observed = new Map(live.slots.map((slot) => [slot.document_key, slot]));
      for (const slot of artifact?.slots ?? []) {
        const expected = observed.get(slot?.document_key);
        if (!expected) {
          code("family_count_unsupported", `slot ${slot?.document_key} is absent from the corpus`);
          continue;
        }
        for (const field of [
          "slot_kind",
          "act_number",
          "act_date",
          "act_text_admitted",
          "evidence_class",
          "slot_verdict",
          "reason_code",
          "transitional",
          "commencement_rule_ref",
          "transitional_basis_id",
        ]) {
          if (slot[field] !== expected[field]) {
            code("family_count_unsupported", `slot ${slot.document_key} ${field} differs`);
          }
        }
      }
      if (live.slots.length !== denominator?.slots_total) {
        code("family_count_unsupported", "the corpus slot count differs from the denominator");
      }
    }
    for (const [label, observed] of [
      ["by_evidence_class", live.by_evidence_class],
      ["by_slot_verdict", live.by_slot_verdict],
      ["by_reason_code", live.by_reason_code],
      ["by_transitional", live.by_transitional],
    ]) {
      if (!observed) continue;
      if (sortJoin(Object.keys(observed)) !== sortJoin(Object.keys(denominator?.[label] ?? {}))) {
        code("family_count_unsupported", `${label} key set differs from the corpus`);
        continue;
      }
      for (const [key, value] of Object.entries(observed)) {
        if (denominator?.[label]?.[key] !== value) {
          code("family_count_unsupported", `${label}.${key} differs from the corpus`);
        }
      }
    }
    if (live.t02) {
      for (const [key, value] of Object.entries(live.t02)) {
        if (denominator?.[key] !== value) {
          code("family_count_unsupported", `denominator.${key} differs from T02`);
        }
      }
    }
    if (live.frozen) {
      for (const [key, value] of Object.entries(live.frozen)) {
        if (frozen?.[key] !== value) {
          code("family_count_unsupported", `frozen_m201_boundary.${key} differs from the gate`);
        }
      }
    }
    if (live.gate) {
      for (const [key, value] of Object.entries(live.gate)) {
        if (gate?.[key] !== value) {
          code("family_count_unsupported", `admission_gate.${key} differs from the records`);
        }
      }
    }
  }

  return { ok: errors.length === 0, errors };
}

function sortJoin(values) {
  return [...values].sort().join(",");
}

function codesFor(result) {
  return [...new Set(result.errors.map((error) => error.code))];
}

function expectCode(result, name) {
  assert.ok(
    codesFor(result).includes(name),
    `expected ${name}, got ${JSON.stringify(result.errors)}`,
  );
  assert.equal(result.ok, false, `${name} must fail closed`);
  return result;
}

// ---------------------------------------------------------------------------
// fixtures and the live artifact
// ---------------------------------------------------------------------------

const liveText = readRepo(ARTIFACT);
const liveArtifact = JSON.parse(liveText);

function cloneArtifact() {
  return JSON.parse(liveText);
}

function liveEnv() {
  const env = { artifactText: liveText, exists: (value) => existsSync(path.join(root, value)) };
  if (existsSync(exportRoot())) {
    const derived = deriveCommencementLive();
    env.live = {
      slots: derived.slots,
      by_evidence_class: derived.by_evidence_class,
      by_slot_verdict: derived.by_slot_verdict,
      by_reason_code: derived.by_reason_code,
      by_transitional: derived.by_transitional,
      t02: derived.t02,
      frozen: derived.frozen,
      gate: derived.gate,
      inputs: liveArtifact.inputs.reduce((acc, pin) => {
        const absolute = path.join(root, pin.relative_path);
        if (!existsSync(absolute)) return acc;
        const bytes = readFileSync(absolute);
        acc[pin.input_id] = {
          input_bytes: bytes.length,
          input_sha256: `sha256:${createHash("sha256").update(bytes).digest("hex")}`,
        };
        return acc;
      }, {}),
    };
  }
  return env;
}

// ---------------------------------------------------------------------------
// artifact integrity
// ---------------------------------------------------------------------------

test("the artifact is repository-relative, ASCII-only, non-empty and canonical", () => {
  assert.ok(isRepoRelative(ARTIFACT));
  assert.ok(liveText.length > 0, "the artifact must not be empty");
  assert.ok(!liveText.includes("\n"), "the artifact must be one canonical line");
  assert.ok(!/[\x80-\uffff]/.test(liveText), "the artifact must be pure ASCII");
  assert.equal(JSON.stringify(liveArtifact), liveText, "the artifact must be canonical JSON");
});

test("every declared input anchor is repository-relative and exists", () => {
  assert.ok(Array.isArray(liveArtifact.inputs) && liveArtifact.inputs.length > 0);
  const inputIds = liveArtifact.inputs.map((pin) => pin.input_id).sort();
  assert.deepEqual(inputIds, [...INPUT_IDS].sort());
  for (const pin of liveArtifact.inputs) {
    assert.ok(isRepoRelative(pin.relative_path), `${pin.input_id} path must be repository-relative`);
    assert.match(pin.input_sha256, SHA_PATTERN);
    assert.ok(Number.isInteger(pin.input_bytes) && pin.input_bytes > 0);
    assert.ok(
      existsSync(path.join(root, pin.relative_path)),
      `${pin.input_id} must resolve on disk`,
    );
  }
});

test("the artifact enumerates exactly the documented code sets", () => {
  assert.deepEqual([...liveArtifact.slot_kinds].sort(), [...SLOT_KINDS].sort());
  assert.deepEqual([...liveArtifact.evidence_classes].sort(), [...EVIDENCE_CLASSES].sort());
  assert.deepEqual([...liveArtifact.slot_verdicts].sort(), [...SLOT_VERDICTS].sort());
  assert.deepEqual([...liveArtifact.transitional_values].sort(), [...TRANSITIONAL_VALUES].sort());
  assert.deepEqual([...liveArtifact.reason_codes].sort(), [...REASON_CODES].sort());
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());
});

test("the artifact is bound to the T02 denominator and the frozen M201 boundary", () => {
  const denominator = liveArtifact.denominator;
  assert.equal(denominator.t02_layer1_records_total, EXPECTED_LAYER1_RECORDS);
  assert.equal(denominator.t02_layer1_amending_acts, EXPECTED_LAYER1_AMENDING);
  assert.equal(denominator.t02_amends_edges_total, EXPECTED_AMENDS_EDGES);
  assert.equal(denominator.slots_total, denominator.t02_layer1_records_total);
  assert.equal(denominator.amending_act_slots, denominator.t02_layer1_amending_acts);
  assert.equal(denominator.named_chain_slots + denominator.amending_act_slots, denominator.slots_total);
  assert.equal(liveArtifact.slots.length, denominator.slots_total);

  const t02 = JSON.parse(readRepo(T02_ARTIFACT));
  assert.equal(denominator.t02_layer1_records_total, t02.denominator.layer1_records_total);
  assert.equal(denominator.t02_layer1_amending_acts, t02.denominator.layer1_amending_acts);
  assert.equal(denominator.t02_amends_edges_total, t02.denominator.amends_edges_total);

  const gate = JSON.parse(readRepo(M201_GATE)).commencement_boundary;
  assert.deepEqual(liveArtifact.frozen_m201_boundary, {
    gate_relative_path: M201_GATE,
    evidence_class: gate.evidence_class,
    commencement_rule_ref: gate.commencement_rule_ref,
    transitional: gate.transitional,
  });
  assert.equal(liveArtifact.transitional_basis.basis_id, TRANSITIONAL_JUSTIFICATION_ID);
  assert.equal(liveArtifact.transitional_basis.source_relative_path, M201_GATE);
});

test("the partitions sum to the declared denominator", () => {
  const denominator = liveArtifact.denominator;
  for (const label of ["by_evidence_class", "by_slot_verdict", "by_reason_code", "by_transitional"]) {
    const partition = denominator[label];
    assert.ok(partition && typeof partition === "object" && !Array.isArray(partition), `${label}`);
    let sum = 0;
    for (const [key, value] of Object.entries(partition)) {
      assert.ok(Number.isInteger(value) && value >= 0, `${label}.${key} must be a count`);
      assert.match(key, ALLOWED_TOKEN, `${label}.${key} must be a count-only token`);
      sum += value;
    }
    assert.equal(sum, denominator.slots_total, `${label} must sum to the denominator`);
  }
});

test("every slot verdict is bounded and class_matched_ids is an explicit empty array", () => {
  assert.deepEqual(liveArtifact.required_evidence.class_matched_ids, []);
  assert.equal(liveArtifact.required_evidence.required_evidence_class, REQUIRED_EVIDENCE_CLASS);
  assert.equal(liveArtifact.required_evidence.required_evidence_status, REQUIRED_EVIDENCE_STATUS);

  let namedChain = 0;
  for (const slot of liveArtifact.slots) {
    assert.ok(
      ["slot-filled-not-proven", "explicitly-absent"].includes(slot.slot_verdict),
      `slot ${slot.document_key} carries the verdict ${slot.slot_verdict}`,
    );
    assert.ok(SLOT_KINDS.includes(slot.slot_kind));
    assert.ok(EVIDENCE_CLASSES.includes(slot.evidence_class));
    assert.ok(REASON_CODES.includes(slot.reason_code));
    assert.ok(TRANSITIONAL_VALUES.includes(slot.transitional));
    if (slot.slot_kind === "named-chain") namedChain += 1;
  }
  assert.equal(namedChain, 1, "exactly one slot is the named chain");
  assert.equal(liveArtifact.denominator.by_slot_verdict["slot-filled-not-proven"], 1);
});

test("the artifact carries zero legislative values and mints no M208 identifier", () => {
  assert.equal(liveText.split('"legislative"').length - 1, 0, "no legislative value");
  for (const token of ["ActivationTrigger", "TransitionalResolver", "EvidenceAnchor", "LegislativeEffect"]) {
    assert.ok(!liveText.includes(token), `the artifact must not mint ${token}`);
  }
  for (const slot of liveArtifact.slots) {
    assert.notEqual(slot.evidence_class, "legislative");
  }
  assert.equal(liveArtifact.admission_gate.m208_s03_admission, "not-adopted");
  assert.equal(liveArtifact.admission_gate.m208_s03_owner_admission_ref, "none");
  assert.equal(liveArtifact.admission_gate.m208_s04_admission, "not-adopted");
  assert.equal(liveArtifact.admission_gate.m207_human_pilot, "absent");
  assert.equal(liveArtifact.admission_gate.m207_c4_operational_acceptance, "non-pass");
  assert.equal(liveArtifact.admission_gate.m207_c4_rate_status, "not-measured");
});

test("the record carries the D415, D416, D406 and D553 non-claims", () => {
  const joined = liveArtifact.non_claims.join(" ").toLowerCase();
  for (const fragment of REQUIRED_NON_CLAIM_FRAGMENTS) {
    assert.ok(joined.includes(fragment), `the non-claims must carry ${fragment}`);
  }
});

test("the emitter exists, is wired additively and adds no dependency", () => {
  assert.match(readRepo(LIB_RS), /pub mod amendment_provenance;/);
  assert.match(
    readRepo(CARGO_MANIFEST),
    /name = "m209-amendment-provenance"[\s\S]*?path = "src\/bin\/m209-amendment-provenance\.rs"/,
  );
  const bin = readRepo(RUST_BIN);
  assert.match(bin, /parse_provenance_args/);
  assert.match(bin, /run_provenance/);
  assert.match(bin, /commencement/);

  const dependencies = readRepo(CARGO_MANIFEST)
    .split("[dependencies]")[1]
    .split("[[bin]]")[0]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "" && !line.startsWith("#"));
  assert.deepEqual(
    dependencies.map((line) => line.split("=")[0].trim()).sort(),
    ["ln-decode", "ln-kb-ontology", "ln-temporal", "rusqlite"],
    "no rust dependency may be added by this task",
  );

  const module = readRepo(RUST_MODULE);
  for (const symbol of [
    /pub const COMMENCEMENT_EVIDENCE_CLASSES/,
    /pub const COMMENCEMENT_SLOT_VERDICTS/,
    /pub const COMMENCEMENT_REASON_CODES/,
    /pub const COMMENCEMENT_TRANSITIONAL_VALUES/,
    /pub const COMMENCEMENT_SLOT_KINDS/,
    /pub const COMMENCEMENT_FAIL_CLOSED_CODES/,
    /pub fn collect_commencement_transition/,
    /pub fn validate_commencement_transition/,
    /pub fn render_commencement_transition/,
  ]) {
    assert.match(module, symbol);
  }
  // The boundary suite is the ln-temporal half of this task.
  assert.match(
    readRepo("crates/ln-temporal/tests/m209_s03_commencement_boundary.rs"),
    /fn no_m208_selector_identifier_is_minted_under_ln_temporal_src/,
  );
});

test("the frozen M201 and T02 artifacts carry no worktree delta", () => {
  const tracked = execFileSync("git", ["ls-files", "--error-unmatch", ...FROZEN_M201, T02_ARTIFACT], {
    cwd: root,
    encoding: "utf8",
  })
    .split("\n")
    .filter((line) => line !== "");
  assert.deepEqual(tracked.sort(), [...FROZEN_M201, T02_ARTIFACT].sort());
  const status = execFileSync("git", ["status", "--porcelain", "--", ...FROZEN_M201, T02_ARTIFACT], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(status.trim(), "", `declared input pins carry a worktree delta: ${status}`);
});

// ---------------------------------------------------------------------------
// code coverage: one empirical mutation per documented fail-closed code
// ---------------------------------------------------------------------------

const CODE_COVERAGE = [
  {
    code: "input_absent",
    mutate: (artifact) => {
      artifact.inputs[0].relative_path = "prd/migration/rust-evidence/absent-manifest.jsonl";
    },
    env: () => ({
      exists: (value) =>
        !value.endsWith("absent-manifest.jsonl") && existsSync(path.join(root, value)),
    }),
  },
  {
    code: "input_hash_mismatch",
    mutate: () => {},
    env: (artifact) => ({
      live: {
        inputs: {
          [artifact.inputs[0].input_id]: {
            input_bytes: artifact.inputs[0].input_bytes,
            input_sha256: `sha256:${"0".repeat(64)}`,
          },
        },
      },
    }),
  },
  {
    code: "family_count_unsupported",
    mutate: (artifact) => {
      artifact.denominator.slots_total += 1;
    },
    env: {},
  },
  {
    code: "zero_denominator",
    mutate: (artifact) => {
      artifact.denominator.slots_total = 0;
      artifact.denominator.amending_act_slots = 0;
    },
    env: {},
  },
  {
    code: "non_ascii_evidence",
    mutate: (artifact) => {
      artifact.count_basis = `${artifact.count_basis}\u041f\u0420\u0410\u0412\u041e`;
    },
    env: {},
  },
  {
    code: "raw_text_leak",
    mutate: (artifact) => {
      artifact.count_basis = "corpus content: consultantplus://offline/ref=DEADBEEF";
    },
    env: {},
  },
  {
    code: "legislative_upgrade_attempt",
    mutate: (artifact) => {
      artifact.slots[0].evidence_class = "legislative";
    },
    env: {},
  },
  {
    code: "vocabulary_minted",
    mutate: (artifact) => {
      artifact.slots[0].slot_kind = "ActivationTrigger";
    },
    env: {},
  },
  {
    code: "date-as-commencement",
    mutate: (artifact) => {
      artifact.slots[0].commencement_rule_ref = "2013-04-05";
    },
    env: {},
  },
  {
    code: "no-legislative-commencement-source",
    mutate: (artifact) => {
      const slot = artifact.slots.find((row) => row.slot_kind === "amending-act");
      slot.act_text_admitted = false;
    },
    env: {},
  },
  {
    code: "act-text-not-admitted",
    mutate: (artifact) => {
      const slot = artifact.slots.find((row) => row.reason_code === "act-text-not-admitted");
      slot.act_text_admitted = true;
    },
    env: {},
  },
  {
    code: "m208-s03-not-adopted",
    mutate: (artifact) => {
      artifact.admission_gate.m208_s03_admission = "adopted";
    },
    env: {},
  },
  {
    code: "m207-human-pilot-absent",
    mutate: (artifact) => {
      artifact.admission_gate.m207_human_pilot = "present";
    },
    env: {},
  },
];

test("every documented fail-closed code is empirically exercised", () => {
  assert.equal(CODE_COVERAGE.length, FAIL_CLOSED_CODES.length);
  for (const entry of CODE_COVERAGE) {
    assert.ok(FAIL_CLOSED_CODES.includes(entry.code), `${entry.code} must be documented`);
    const artifact = cloneArtifact();
    entry.mutate(artifact);
    const injected = typeof entry.env === "function" ? entry.env(artifact) : entry.env;
    const env = { ...injected, artifactText: JSON.stringify(artifact) };
    expectCode(validateCommencementArtifact(artifact, env), entry.code);
  }
  // The unmutated artifact passes the same validator.
  const result = validateCommencementArtifact(cloneArtifact(), {
    artifactText: liveText,
    exists: (value) => existsSync(path.join(root, value)),
  });
  assert.equal(result.ok, true, JSON.stringify(result.errors));
});

test("the documented code blocks equal the emitted code sets", () => {
  const source = readRepo(CONTRACT_PATH);

  const reasonBlock = source.match(
    /\/\/ DOCUMENTED_REASON_CODES_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_REASON_CODES_END/,
  );
  assert.ok(reasonBlock, "the documented reason-code block must exist");
  const documentedReasons = reasonBlock[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documentedReasons.sort(), [...REASON_CODES].sort());
  assert.deepEqual([...liveArtifact.reason_codes].sort(), [...REASON_CODES].sort());

  const failBlock = source.match(
    /\/\/ DOCUMENTED_FAIL_CLOSED_BEGIN\n([\s\S]*?)\/\/ DOCUMENTED_FAIL_CLOSED_END/,
  );
  assert.ok(failBlock, "the documented fail-closed block must exist");
  const documentedFailClosed = failBlock[1]
    .split("\n")
    .map((line) => line.match(/^\/\/ ([a-z0-9_-]+):/))
    .filter(Boolean)
    .map((match) => match[1]);
  assert.deepEqual(documentedFailClosed.sort(), [...FAIL_CLOSED_CODES].sort());
  assert.deepEqual([...liveArtifact.fail_closed_codes].sort(), [...FAIL_CLOSED_CODES].sort());

  const module = readRepo(RUST_MODULE);
  for (const [name, expected] of [
    ["COMMENCEMENT_REASON_CODES", REASON_CODES],
    ["COMMENCEMENT_FAIL_CLOSED_CODES", FAIL_CLOSED_CODES],
    ["COMMENCEMENT_EVIDENCE_CLASSES", EVIDENCE_CLASSES],
    ["COMMENCEMENT_SLOT_VERDICTS", SLOT_VERDICTS],
    ["COMMENCEMENT_TRANSITIONAL_VALUES", TRANSITIONAL_VALUES],
    ["COMMENCEMENT_SLOT_KINDS", SLOT_KINDS],
  ]) {
    const block = module.match(
      new RegExp(`pub const ${name}: \\[&str; \\d+\\] =\\s*\\[([\\s\\S]*?)\\];`),
    );
    assert.ok(block, `the Rust ${name} array must exist`);
    assert.deepEqual(
      [...block[1].matchAll(/"([a-z0-9_-]+)"/g)].map((match) => match[1]).sort(),
      [...expected].sort(),
      `${name} must equal the emitted set`,
    );
  }
});

test("negative: an unsupported envelope fails closed", () => {
  const result = validateCommencementArtifact(cloneArtifact(), {
    artifactText: liveText,
    exists: (value) => existsSync(path.join(root, value)),
  });
  assert.equal(result.ok, true, JSON.stringify(result.errors));

  for (const [mutate, expected] of [
    [(artifact) => (artifact.required_evidence.class_matched_ids = ["annotation:1"]), "family_count_unsupported"],
    [(artifact) => (artifact.required_evidence.required_evidence_class = "machine"), "family_count_unsupported"],
    [(artifact) => (artifact.slots[0].commencement_rule_ref = ""), "date-as-commencement"],
    [(artifact) => (artifact.slots[1].evidence_class = "hypothesized_from_oracle_diff"), "legislative_upgrade_attempt"],
    [(artifact) => (artifact.slots[1].commencement_rule_ref = "rec:commencement:1"), "legislative_upgrade_attempt"],
    [(artifact) => (artifact.slots.find((row) => row.slot_kind === "named-chain").commencement_rule_ref = "law_2013-04-05_44-fz"), "date-as-commencement"],
    [(artifact) => (artifact.denominator.t02_layer1_records_total = 999), "family_count_unsupported"],
    [(artifact) => (artifact.slots.length = 0), "family_count_unsupported"],
    [(artifact) => (artifact.denominator.by_reason_code = { "no-legislative-commencement-source": 1 }), "family_count_unsupported"],
    [(artifact) => (artifact.admission_gate.m208_s04_admission = "adopted"), "m208-s03-not-adopted"],
    [(artifact) => (artifact.admission_gate.m207_c4_operational_acceptance = "pass"), "m207-human-pilot-absent"],
  ]) {
    const artifact = cloneArtifact();
    mutate(artifact);
    expectCode(
      validateCommencementArtifact(artifact, { artifactText: JSON.stringify(artifact) }),
      expected,
    );
  }
});

// ---------------------------------------------------------------------------
// corpus-gated re-derivation
// ---------------------------------------------------------------------------

test("the live corpus re-derives the declared leg", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const derived = deriveCommencementLive();
  const denominator = liveArtifact.denominator;

  assert.equal(derived.slots_total, denominator.slots_total);
  assert.equal(derived.named_chain_slots, denominator.named_chain_slots);
  assert.equal(derived.amending_act_slots, denominator.amending_act_slots);
  assert.deepEqual(derived.by_evidence_class, denominator.by_evidence_class);
  assert.deepEqual(derived.by_slot_verdict, denominator.by_slot_verdict);
  assert.deepEqual(derived.by_reason_code, denominator.by_reason_code);
  assert.deepEqual(derived.by_transitional, denominator.by_transitional);
  assert.deepEqual(derived.t02, {
    t02_layer1_records_total: denominator.t02_layer1_records_total,
    t02_layer1_amending_acts: denominator.t02_layer1_amending_acts,
    t02_amends_edges_total: denominator.t02_amends_edges_total,
  });

  const observed = new Map(derived.slots.map((slot) => [slot.document_key, slot]));
  assert.equal(observed.size, liveArtifact.slots.length);
  for (const slot of liveArtifact.slots) {
    const expected = observed.get(slot.document_key);
    assert.ok(expected, `slot ${slot.document_key} must re-derive from the corpus`);
    assert.deepEqual(slot, expected, `slot ${slot.document_key} must re-derive field for field`);
  }

  // The declared input pins must match the live bytes, including the manifest.
  const manifest = liveArtifact.inputs.find((pin) => pin.input_id === "layer1_manifest");
  assert.equal(manifest.input_bytes, derived.manifest.input_bytes);
  assert.equal(manifest.input_sha256, derived.manifest.input_sha256);

  // The validator agrees with the corpus.
  const result = validateCommencementArtifact(cloneArtifact(), liveEnv());
  assert.equal(result.ok, true, JSON.stringify(result.errors));

  console.log(
    `[commencement] slots=${derived.slots_total} named=${derived.named_chain_slots} amending=${derived.amending_act_slots} filled=${derived.by_slot_verdict["slot-filled-not-proven"]} absent=${derived.by_slot_verdict["explicitly-absent"]} class_matched=0`,
  );
});

test("drift in any declared input or count is detected under a named code", () => {
  if (!existsSync(exportRoot())) {
    console.log("M209_S03_CORPUS_ABSENT");
    return;
  }
  const derived = deriveCommencementLive();
  const live = liveEnv().live;

  const slotDrift = cloneArtifact();
  slotDrift.slots[3].act_text_admitted = !slotDrift.slots[3].act_text_admitted;
  expectCode(
    validateCommencementArtifact(slotDrift, { artifactText: JSON.stringify(slotDrift), live }),
    "family_count_unsupported",
  );

  const partitionDrift = cloneArtifact();
  partitionDrift.denominator.by_transitional.unresolved += 1;
  expectCode(
    validateCommencementArtifact(partitionDrift, {
      artifactText: JSON.stringify(partitionDrift),
      live,
    }),
    "family_count_unsupported",
  );

  const gateDrift = cloneArtifact();
  gateDrift.admission_gate.m208_s03_runtime_work = "started";
  expectCode(
    validateCommencementArtifact(gateDrift, { artifactText: JSON.stringify(gateDrift), live }),
    "m208-s03-not-adopted",
  );

  const frozenDrift = cloneArtifact();
  frozenDrift.frozen_m201_boundary.transitional = "unresolved";
  expectCode(
    validateCommencementArtifact(frozenDrift, { artifactText: JSON.stringify(frozenDrift), live }),
    "family_count_unsupported",
  );
});

test("M209 S03 commencement markers", () => {
  assert.match(SCHEMA, /^law-nexus\/r070-commencement-transition\/v1$/);
  assert.match(KIND, /^m209-s03-commencement-transition$/);
  assert.ok(TRANSITIONAL_JUSTIFICATION_ID.length > 0);
  assert.equal(EXPECTED_LAYER1_RECORDS, EXPECTED_LAYER1_AMENDING + 1);
  assert.equal(liveArtifact.denominator.slots_total, liveArtifact.denominator.rows_total);
  assert.equal(
    liveArtifact.denominator.by_slot_verdict["slot-filled-not-proven"] +
      liveArtifact.denominator.by_slot_verdict["explicitly-absent"],
    liveArtifact.denominator.slots_total,
  );
  assert.equal(liveArtifact.denominator.by_transitional["explicitly_absent"], 1);
});
