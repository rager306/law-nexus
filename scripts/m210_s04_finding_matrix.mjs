#!/usr/bin/env node
// M210-3afp79 S04 T02 -- finding evidence matrix for the 19 RC28 findings.
//
// WHY THIS FILE EXISTS
// M210/S04 has to hand a human reviewer one source-bound card per RC28 finding:
// the verbatim required proof, its class, the live evidence digests, whether the
// evidence class actually matches, the machine verdict, the residual scope, the
// non-claims and whether the material is sufficient for a human disposition. It
// also has to prove, in the same record, that no requirement was promoted and no
// Review Case event was written. This generator renders that record once, from
// a single declarative table plus live reads of the tracked sources, so that the
// matrix cannot drift from the artifacts it cites without failing `--check`.
//
// IT DERIVES, IT DOES NOT INVENT
//   * required_proof -- the packet carries `required_proof_class` but no
//     required-proof sentence. The sentence is therefore taken verbatim from the
//     owning program record (`rc28-remediation-program.md`, "Finding coverage and
//     acceptance") and is re-validated live as a substring of that file by the
//     contract. The derivation is disclosed in `required_proof_derivation`.
//   * required_proof_class -- read live from the packet's own findings; a row that
//     disagrees with the packet is a fail-closed `proof_class_mismatch`.
//   * evidence_paths -- every path is re-resolved and re-hashed live on every run.
//   * reverification -- only RC28-F02, RC28-F04, RC28-F05 and RC28-F14 were
//     re-verified in this pass; each re-verification is expressed as live token
//     and pointer assertions over the cited files, so it is re-proved on every
//     run rather than asserted once.
//   * requirement_evidence -- the four rows mirror the tracked
//     `m204-s15-requirement-class/v1` classification (live cross-checked) and add
//     only the canonical class supplied by the T02 plan contract. Every row stays
//     `class_matched: false` and `status_effect: unchanged`.
//   * review_case -- the packet's own declared content hash is compared with the
//     live hash of the review document, the embedded events are counted, and the
//     absence of a `RC-2026-09-10-001/` events directory is checked on disk.
//
// WHAT IT REFUSES TO DO
//   No Review Case event, no `record_human_disposition` call, no requirement
//   promotion, no lifecycle smoothing, no DATABASE read, no runtime mutation, no
//   rewrite of any cited source. D519 is recorded as a scope deferral and never as
//   proof. RC28-F18's bounded variant C adoption is recorded as evidence, not as
//   closure, and auto-close stays forbidden.
//
// LIVE BINDINGS THAT ARE DELIBERATELY NOT RE-DERIVED OFFLINE
//   The review-case rollup (finding_count 35, closed 10, open 21, blocked 0,
//   partial 0, stale 0) comes from
//   `uv run python -m law_nexus_harness review-case validate`, executed in this
//   unit. The ledger FSM cannot be re-implemented here, so the rollup is stored as
//   a recorded live CLI observation and cross-checked against the parts that ARE
//   re-derivable offline (packet files, total findings, RC28 open findings, ledger
//   event directories).
//
// USAGE
//   node scripts/m210_s04_finding_matrix.mjs --write   # default
//   node scripts/m210_s04_finding_matrix.mjs --check
//   node scripts/m210_s04_finding_matrix.mjs --print

import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const MATRIX_RELATIVE_PATH = "prd/architecture/m210-s04-finding-evidence-matrix.json";
export const PACKET_RELATIVE_PATH =
  "prd/architecture/review-cases/packets/RC-2026-09-10-001.json";
export const PACKET_DIR_RELATIVE_PATH = "prd/architecture/review-cases/packets";
export const PACKET_EVENTS_DIR_RELATIVE_PATH =
  "prd/architecture/review-cases/packets/RC-2026-09-10-001";
export const SOURCE_REVIEW_RELATIVE_PATH = "doc/review/review-28-10-09-2026.md";
export const PROGRAM_RELATIVE_PATH = "prd/architecture/review-cases/rc28-remediation-program.md";
export const INVENTORY_RELATIVE_PATH = "assessment/33-rc28-disposition-inventory.md";
export const S15_RELATIVE_PATH = "prd/migration/rust-evidence/m204-s15-requirement-class.json";
export const CONTRACT_RELATIVE_PATH = "scripts/m210_s04_finding_matrix_contract.test.mjs";

export const SCHEMA = "law-nexus/m210-s04-finding-evidence-matrix/v1";
export const SCHEMA_VERSION = 1;
export const KIND = "m210-s04-finding-evidence-matrix";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S04";
export const TASK = "T02";
export const LIFECYCLE = ["proposed"];

export const PACKET_ID = "RC-2026-09-10-001";
export const PACKET_CONTENT_SHA256 =
  "sha256:baad2d036a629be39fa049c7aab7d1383ffc77524db38e7ce2767252533b15a1";
export const REVIEWED_GIT_REVISION = "6f1a27537a659f291e0147e0fbd8be6ca199261c";
export const REVIEWED_GIT_REVISION_FORMAT = "git40";

export const REQUIRED_PROOF_CLASSES = ["evidence", "process", "implementation", "design", "docs"];
export const MACHINE_VERDICTS = [
  "evidence_present_class_matched",
  "evidence_present_residual_named",
  "evidence_absent_residual_named",
  "evidence_class_mismatch",
  "awaiting_owner_decision",
  "gate_hold",
];
export const MISMATCH_REASON_CODES = [
  "adoption_docs_are_not_implementation_proof",
  "measurement_protocol_is_not_measured_evidence",
  "human_labels_absent",
  "operational_acceptance_non_pass",
  "pending_task_identity_unresolved",
  "adoption_owner_absent",
  "gate_conflicted_no_promotion",
  "work_identity_evidence_is_not_class_matched",
];
export const REVERIFICATION_REQUIRED_IDS = ["RC28-F02", "RC28-F04", "RC28-F05", "RC28-F14"];

export const FINDING_IDS = [
  "RC28-F01",
  "RC28-F02",
  "RC28-F03",
  "RC28-F04",
  "RC28-F05",
  "RC28-F06",
  "RC28-F07",
  "RC28-F08",
  "RC28-F09",
  "RC28-F10",
  "RC28-F11",
  "RC28-F12",
  "RC28-F13",
  "RC28-F14",
  "RC28-F15",
  "RC28-F16",
  "RC28-F17",
  "RC28-F18",
  "RC28-F19",
];

export const EMITTABLE_CODES = [
  "row_count_incomplete",
  "finding_id_unknown",
  "proof_class_mismatch",
  "evidence_path_unresolved",
  "evidence_hash_mismatch",
  "reverification_missing",
  "class_mismatch_unexplained",
  "verdict_unknown",
  "d519_treated_as_proof",
  "lifecycle_smoothing_detected",
  "f18_auto_close",
  "f13_missing_answer_misread",
  "owner_choice_folded",
  "non_ascii_artifact",
  "raw_text_leak",
  "check_not_byte_identical",
  "status_effect_missing",
  "requirement_promotion_claimed",
  "requirement_namespace_confusion",
  "review_case_event_written",
];

export const WRITTEN_MARKER = "M210_S04_MATRIX_WRITTEN";
export const CHECK_OK_MARKER = "M210_S04_MATRIX_CHECK_OK";
export const PRINT_MARKER = "M210_S04_MATRIX_PRINTED";
export const CONTRACT_MARKER = "M210_S04_MATRIX_OK";

export const ROLLUP = {
  observed_via: "uv run python -m law_nexus_harness review-case validate",
  observation_kind: "recorded_live_cli_observation",
  ok: true,
  finding_count: 35,
  closed_count: 10,
  open_count: 21,
  blocked_count: 0,
  partial_count: 0,
  stale_count: 0,
  rollup_digits: [35, 10, 21, 0, 0],
};

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const NON_CLAIMS = [
  "This matrix is a machine-prepared evidence record for a human reviewer. It is not a Review Case disposition, not a legal conclusion, not a requirement closure and not a lifecycle promotion.",
  "Every row carries status_effect=unchanged and every requirement row carries class_matched=false; no requirement, ADR, roadmap entry, finding status or milestone state is changed by this record.",
  "No Review Case event is written, no actor-bound human disposition path is invoked, and no disposition is fabricated; the RC28 findings stay open until a human records a disposition through a sanctioned path.",
  "The machine verdict is about the class compatibility and the residual scope of the available evidence, never about acceptance; a human decides the disposition.",
  "The evidence paths are hashed live, but a live hash proves identity, not truth; the content is authoritative only in its own owning artifact.",
  "The review-case rollup is a recorded live CLI observation; only its packet-level parts are re-derived offline, and the ledger FSM is not re-implemented here.",
  "The bounded adoption of variant C recorded for RC28-F18 is adoption evidence; independent evaluation and the ledger disposition are separate, still pending, and auto-close is forbidden.",
];

// ---------------------------------------------------------------------------
// Declarative finding table. `required_proof` is the verbatim program sentence;
// the contract re-validates each sentence against the program document.
// ---------------------------------------------------------------------------

const FINDING_ROWS = [
  {
    finding_id: "RC28-F01",
    reviewer_severity: "critical",
    required_proof_class: "evidence",
    required_proof: "real coder-bound measurement and producer-to-promotion negative tests",
    evidence_paths: [
      "prd/annotation/m207-s03-eval-protocol.md",
      "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
      "prd/annotation/m207-s02-coder-protocol.md",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_absent_residual_named",
    deferral_reference: "D519",
    deferral_treated_as_proof: false,
    residual_scope:
      "the human coder-bound measurement is absent from M207's revised scope; only the frozen protocol and the fail-closed non-pass receipt exist",
    non_claims: [
      "D519 removed the M207 obligation for that measurement; it is a scope deferral and is not evidence for RC28-F01",
      "the producer-to-promotion negative tests are machine-checkable separately, and no human measurement is claimed to exist",
    ],
    human_sufficiency:
      "sufficient for a deferred/explicit residual disposition citing D519; insufficient for an already_satisfied disposition",
  },
  {
    finding_id: "RC28-F02",
    reviewer_severity: "high",
    required_proof_class: "evidence",
    required_proof: "seeded selection, validated metadata, provider and Work-family leakage checks",
    evidence_paths: [
      "prd/annotation/m207-s03-eval-protocol.md",
      "prd/migration/rust-evidence/m207-s03-eval-manifest.json",
      "prd/migration/rust-evidence/m207-s01-pilot-cases.json",
    ],
    rereverified: true,
    reverification: {
      verified_in: "M210-3afp79/S04/T02",
      method: "live_source_read",
      verdict: "confirmed",
      tokens: [
        { path: "prd/annotation/m207-s03-eval-protocol.md", token: "METADATA_REDERIVED" },
        { path: "prd/annotation/m207-s03-eval-protocol.md", token: "WORK_FAMILY_DOMINANCE" },
        { path: "prd/annotation/m207-s03-eval-protocol.md", token: "not-measured" },
      ],
      observed_fields: [],
      observed: [
        "the frozen contract refuses re-derivation of metadata from a path or a file name and keeps the frozen case metadata as-is",
        "the holdout is family-granular and frozen by seed before measurement, with the Work-family cap and the 180-fragment seed unchanged",
        "provider and Work-family strata are published rather than selected, and every stratum with zero units stays not-measured",
        "the protocol computes no metric: no aspect and no stratum value exists until the two human passes and the adjudication exist",
      ],
    },
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "the evaluation contract is frozen before measurement; no rate is published and the human reference is absent, so the required checks exist as a contract only",
    non_claims: [
      "a frozen evaluation contract is not computed evidence and not a measured rate",
      "no provider stratum, Work-family stratum or aspect value is published by this row",
    ],
    human_sufficiency:
      "sufficient for a class-matched protocol disposition that names measurement as the residual; insufficient to claim measured strata",
  },
  {
    finding_id: "RC28-F03",
    reviewer_severity: "high",
    required_proof_class: "evidence",
    required_proof: "true input/semantic digests, complete argv and actual operational outcome",
    evidence_paths: [
      "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
      "prd/annotation/m207-s04-c4-protocol.md",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "the receipt self-declares operational_acceptance=non-pass; the operational criterion is not met, so the actual operational outcome is negative evidence",
    non_claims: [
      "receipt presence is not runtime freshness, successful admission, parser readiness or legal acceptance",
      "the receipt is not gold and not a promotion",
    ],
    human_sufficiency:
      "sufficient for a fail-closed non-pass disposition; insufficient for an already_satisfied disposition",
  },
  {
    finding_id: "RC28-F04",
    reviewer_severity: "high",
    required_proof_class: "process",
    required_proof:
      "versioned acceptance and equivalent receipt reuse; no silent criterion substitution",
    evidence_paths: [
      "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json",
      "prd/migration/rust-evidence/m204-s07-governor-repeat.json",
      "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
      "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
    ],
    rereverified: true,
    reverification: {
      verified_in: "M210-3afp79/S04/T02",
      method: "live_source_read",
      verdict: "confirmed",
      tokens: [
        {
          path: "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json",
          token: "m204-s06-governor-sanctioned-outcome/v1",
        },
        {
          path: "prd/migration/rust-evidence/m204-s07-governor-repeat.json",
          token: "m204-s07-governor-repeat/v1",
        },
      ],
      observed_fields: [
        {
          path: "prd/migration/rust-evidence/m204-s07-governor-repeat.json",
          pointer: "predecessor.path",
          equals: "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json",
        },
        {
          path: "prd/migration/rust-evidence/m204-s07-governor-repeat.json",
          pointer: "predecessor.sha256",
          equals_file_sha256:
            "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json",
        },
      ],
      observed: [
        "the earlier outcome and its fresh repeat carry distinct versioned schema identifiers",
        "the repeat binds its predecessor by repository-relative path and by the live digest of that predecessor file, so receipt reuse is explicit and predecessor-preserving",
        "no criterion substitution is recorded: both records keep the same check identifier and the same scope",
      ],
    },
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_class_matched",
    residual_scope:
      "none found in this pass for the versioned-acceptance and predecessor-chain part; C4 operational acceptance remains non-pass and is tracked by RC28-F03",
    non_claims: [
      "the sanctioned integrity outcome is process evidence, not semantic acceptance and not C4 operational acceptance",
      "a predecessor digest proves chain identity, not product correctness",
    ],
    human_sufficiency:
      "sufficient for an acceptance-versioning disposition; C4 operational acceptance stays non-pass under RC28-F03",
  },
  {
    finding_id: "RC28-F05",
    reviewer_severity: "high",
    required_proof_class: "process",
    required_proof:
      "identify four pending tasks, reproduce claim/dispatch defect, sanctioned idempotent recovery; upstream actions need separate confirmation",
    evidence_paths: [
      "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json",
      "prd/migration/rust-evidence/m204-s01-gsd-failure-classes.json",
      "prd/migration/rust-evidence/m204-s01-gsd-upstream-debt.json",
      "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json",
      "scripts/m204_s01_t01_verify.py",
    ],
    rereverified: true,
    reverification: {
      verified_in: "M210-3afp79/S04/T02",
      method: "live_source_read",
      verdict: "confirmed",
      tokens: [
        {
          path: "assessment/33-rc28-disposition-inventory.md",
          token: "open-gsd/gsd-pi#2412",
        },
        {
          path: "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json",
          token: "pending_task_ids",
        },
      ],
      observed_fields: [
        {
          path: "prd/migration/rust-evidence/m204-s01-gsd-upstream-debt.json",
          pointer: "status.upstream_issue",
          equals: "not_filed",
        },
        {
          path: "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json",
          pointer: "task_counter.status",
          equals: "unknown",
        },
        {
          path: "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json",
          pointer: "task_counter.pending_task_ids",
          equals: null,
        },
        {
          path: "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json",
          pointer: "task_counter.expected",
          equals: "2184/2188 with pending=4",
        },
      ],
      observed: [
        "the claim-dispatch desync and the completed-no-advance wedge are reproduced and typed with journal evidence references",
        "the sanctioned idempotent recovery is recorded by the governor sanctioned outcome and its fresh repeat",
        "the four pending task identities were NOT resolved: the sanctioned projection exposes no task totals or pending identities and the record states status=unknown with pending_task_ids=null",
        "the upstream debt note records upstream_issue=not_filed; the 2412 filing appears only as prose in the M209 disposition inventory, with no tracked filing artifact",
      ],
    },
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "pending_task_identity_unresolved (four pending task identities are not identified in the recorded inventory, and only the 2184/2188 pending=4 expectation is recorded); the upstream 2412 filing has no tracked filing artifact, only an inventory prose reference",
    non_claims: [
      "the reproduction is not an engine repair and does not fix the upstream defects",
      "this matrix publishes nothing upstream and claims no filing identifier beyond the inventory prose",
    ],
    human_sufficiency:
      "sufficient for a partial disposition that names the unresolved identity and the untracked upstream filing as explicit residuals",
  },
  {
    finding_id: "RC28-F06",
    reviewer_severity: "high",
    required_proof_class: "implementation",
    required_proof: "siblings/annexes, profile hierarchy and downstream owner assertions",
    evidence_paths: [
      "prd/architecture/m206-s01-adoption-state.md",
      "prd/architecture/m205-s01-pullenti-matrix.yaml",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "only M206 adoption-state documentation and the M205 design crosswalk exist; there is no implementation proof of sibling or annex closure",
    non_claims: [
      "an adoption-state record and a design crosswalk are not implementation evidence",
      "no lifecycle smoothing: this row cannot raise the requirement evidence table above class_matched=false",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F07",
    reviewer_severity: "high",
    required_proof_class: "implementation",
    required_proof:
      "authorized derivations, positive and negative ThisRef, no unrelated continuation graph",
    evidence_paths: [
      "prd/architecture/m206-s03-adoption-state.md",
      "prd/architecture/m205-s03-context-fsm.yaml",
      "prd/architecture/m206-s07-runtime-admission.md",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "M206/S03 itself states that F07, F08 and F12 remain open, and the M206/S07 runtime admission is scoped to that slice's remediation only",
    non_claims: [
      "a scoped runtime admission is not implementation proof for this finding",
      "no continuation graph is claimed to be corrected by this row",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F08",
    reviewer_severity: "high",
    required_proof_class: "implementation",
    required_proof:
      "authorized derivations, positive and negative ThisRef, no unrelated continuation graph",
    evidence_paths: [
      "prd/architecture/m206-s03-adoption-state.md",
      "prd/architecture/m205-s03-context-fsm.yaml",
      "prd/architecture/m206-s05-runtime-admission.md",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "M206/S03 states F08 remains open; the ThisRef evidence path is documented as a design obligation, not as a corrected implementation",
    non_claims: [
      "a design obligation is not implementation evidence",
      "constant abstention is not claimed to prove useful completeness or correct resolution",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F09",
    reviewer_severity: "high",
    required_proof_class: "implementation",
    required_proof:
      "pre-capture incomplete members, sentence boundaries, preserved origins and bounded arbitration",
    evidence_paths: [
      "prd/architecture/m206-s02-adoption-state.md",
      "prd/architecture/m205-s01-pullenti-matrix.yaml",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "only the M206/S02 adoption state and the M205 design crosswalk exist; no implementation proof of pre-capture members or bounded arbitration",
    non_claims: [
      "the design crosswalk is prior-art inventory and never product runtime",
      "no D388 gate is adopted by this row",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F10",
    reviewer_severity: "medium",
    required_proof_class: "implementation",
    required_proof:
      "normalization spans, morphology unavailable outcome, endpoint versus edition-index membership distinction",
    evidence_paths: [
      "prd/architecture/m206-s01-adoption-state.md",
      "prd/architecture/m206-s04-adoption-state.md",
      "prd/architecture/m205-s01-pullenti-matrix.yaml",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "adoption-state records and a design crosswalk only; the normalization, morphology and membership distinctions are not proved by implementation evidence",
    non_claims: [
      "no arithmetic range expansion and no vendor threshold copy is claimed",
      "a design deferral is not implementation evidence",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F11",
    reviewer_severity: "high",
    required_proof_class: "implementation",
    required_proof: "token-bound cues, negation differences, participant anchors; not NormRule adoption",
    evidence_paths: [
      "prd/architecture/m206-s04-adoption-state.md",
      "prd/architecture/m205-s03-context-fsm.yaml",
    ],
    rereverified: false,
    class_match: false,
    mismatch_reason_code: "adoption_docs_are_not_implementation_proof",
    machine_verdict: "evidence_class_mismatch",
    residual_scope:
      "only an adoption-state record and a context FSM design document exist; no implementation proof of token-bound matching, negation or participant spans",
    non_claims: [
      "cue recognition is not a NormRule and this row adopts no deferred legal IR",
      "no semantic-cue fix is claimed",
    ],
    human_sufficiency:
      "sufficient only for a residual disposition; the required implementation proof is absent",
  },
  {
    finding_id: "RC28-F12",
    reviewer_severity: "high",
    required_proof_class: "design",
    required_proof:
      "alias declaration/use/scope, antecedent versus self and non-authoritative edition relation",
    evidence_paths: [
      "prd/architecture/m206-s03-adoption-state.md",
      "prd/architecture/m205-s03-context-fsm.yaml",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "M206/S03 states F12 remains open; the edition relation is preserved as a source-backed relation candidate rather than substituted for identity",
    non_claims: [
      "the edition reference is not Expression identity, edition_date, CTV or force",
      "an open adoption state is not a design closure",
    ],
    human_sufficiency:
      "sufficient for a design-partial disposition that names the open adoption state as the residual",
  },
  {
    finding_id: "RC28-F13",
    reviewer_severity: "high",
    required_proof_class: "design",
    required_proof:
      "adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay",
    evidence_paths: [
      "prd/architecture/m205-s03-context-fsm.yaml",
      "prd/architecture/m208-s01-runtime-admission.md",
      "prd/architecture/m208-s03-admission-commencement.md",
      "prd/architecture/m208-s04-admission-bounded-replay.md",
      "prd/architecture/m209-s01-punkt-decision.md",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    owner_status: "deferred-explicit",
    machine_verdict: "awaiting_owner_decision",
    residual_scope:
      "no live adoption owner: the M205 context FSM records runtime_stop_active with the replay handed to M208, M208 recorded not-adopted three times with owner_admission_ref none and runtime_work not-started, and the operation registry stays proposed",
    non_claims: [
      "deferred-explicit is an explicit owner defer, not a missing answer and not a hold",
      "an agent may prepare the three lawful outcomes; only the owner chooses one and records the decision",
      "an extracted operation is not an admitted MicroOperation, LegislativeEffect or InForce",
    ],
    human_sufficiency:
      "sufficient for an owner decision among the three lawful outcomes; no agent may record it, and no agent may impersonate the owner",
  },
  {
    finding_id: "RC28-F14",
    reviewer_severity: "medium",
    required_proof_class: "design",
    required_proof: "functional prior-art matrix; no license or runtime-parity claim",
    evidence_paths: [
      "prd/architecture/m205-s01-pullenti-matrix.yaml",
      "prd/architecture/m207-unit-diagnosis.md",
      "prd/architecture/m207-reassessment-2026-09-21.md",
    ],
    rereverified: true,
    reverification: {
      verified_in: "M210-3afp79/S04/T02",
      method: "live_source_read",
      verdict: "confirmed",
      tokens: [
        {
          path: "prd/architecture/m205-s01-pullenti-matrix.yaml",
          token: "not a license grant, runtime parity, or gold corpus",
        },
        { path: "prd/architecture/m207-unit-diagnosis.md", token: "Not adopted" },
      ],
      observed_fields: [],
      observed: [
        "the crosswalk is a functional prior-art inventory with per-row vendor anchors, take-or-leave decisions and explicit non-claims",
        "the crosswalk declares itself design-only and never product runtime, and it makes no license grant and no runtime-parity claim",
        "the unit diagnosis lists vendor code, dictionaries, thresholds, SemanticService and agreement-with-Pullenti-as-gold as not adopted",
        "any differential run stays optional and license-gated, and agreement with the vendor is not gold and not a second human coder",
      ],
    },
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_class_matched",
    residual_scope:
      "several crosswalk rows keep human_adoption pending and the optional differential run stays license-gated; the M208 optional component is not adopted",
    non_claims: [
      "the prior-art matrix is not a license grant and not runtime parity",
      "agreement with the vendor is not gold and not a second human coder",
    ],
    human_sufficiency:
      "sufficient for a design prior-art disposition; the pending human-adoption rows and the license-gated differential are named residuals",
  },
  {
    finding_id: "RC28-F15",
    reviewer_severity: "high",
    required_proof_class: "evidence",
    required_proof:
      "real independent annotation and source-bound human acceptance; no automatic seed enlargement",
    evidence_paths: [
      "prd/annotation/m207-s01-codebook.md",
      "prd/annotation/m207-s02-coder-protocol.md",
      "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json",
      "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_absent_residual_named",
    deferral_reference: "D519",
    deferral_treated_as_proof: false,
    residual_scope:
      "the human contour is absent and no rate is published; a codebook and a coder kit are neither labels nor gold, and the pilot cannot be enlarged automatically",
    non_claims: [
      "D519 is a scope deferral and is not independent annotation",
      "no automatic seed enlargement and no substitute for human acceptance",
    ],
    human_sufficiency:
      "sufficient for a deferred/explicit residual disposition; insufficient for any already_satisfied disposition",
  },
  {
    finding_id: "RC28-F16",
    reviewer_severity: "high",
    required_proof_class: "evidence",
    required_proof: "each R035 gate plus extractor/admission/regeneration; punkt decision before admission",
    evidence_paths: [
      "prd/architecture/m209-s01-punkt-decision.md",
      "prd/architecture/m209-s01-r035-gate-register.json",
      "prd/migration/rust-evidence/m209-s01-r035-gate-reconciliation.json",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "gate_hold",
    residual_scope:
      "the gate register is delivered with named gates and per-gate quantifiers, but GATE-G015 is conflicted with zero promoted rows and punkt is not-adopted with owner_admission_ref none and zero punkt rows",
    non_claims: [
      "contract counts (28/28, 21/21, 35/35) are not extraction proof and no count-only closure is available",
      "no requirement is promoted from the gate register",
    ],
    human_sufficiency:
      "sufficient for a held-gate disposition that records the conflicted gate and the not-adopted punkt decision; no promotion is available from counts",
  },
  {
    finding_id: "RC28-F17",
    reviewer_severity: "high",
    required_proof_class: "evidence",
    required_proof:
      "operation x provision x commencement x transitions x edition deltas, scoped coverage, frozen M201 untouched",
    evidence_paths: [
      "prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json",
      "prd/migration/rust-evidence/m209-s03-slice-battery.json",
      "prd/migration/rust-evidence/m209-s04-r070-scope-adjudication.json",
      "prd/architecture/m208-s03-admission-commencement.md",
      "prd/architecture/m208-s04-admission-bounded-replay.md",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "M209/S03 delivered scoped coverage and M209/S04 adjudicates the scope, while the M208 components stay not-adopted and R070 remains HOLD",
    non_claims: [
      "consolidated snapshots are oracles, not legislative causes",
      "the frozen M201 pins are untouched and are not provenance for the consolidated editions",
    ],
    human_sufficiency:
      "sufficient for a scoped-coverage disposition with M208's not-adopted history recorded as the historical admission attempt",
  },
  {
    finding_id: "RC28-F18",
    reviewer_severity: "high",
    required_proof_class: "design",
    required_proof: "human-owned legal IR adoption before implementation and independent evaluation",
    evidence_paths: [
      "prd/architecture/m210-s04-admission-reconciliation.json",
      "prd/architecture/m210-s02-adoption-checkpoint-v2.md",
      "prd/architecture/m210-s02-answer-record-v2.json",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    owner_status: "bounded_adoption_established",
    auto_close: false,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "the authenticated bounded adoption of variant C is established by the v2 checkpoint and the v2 answer record (subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f); the independent evaluation and the ledger disposition are separate and still pending",
    non_claims: [
      "adoption is not activation: the candidate layer is permitted but nothing is implemented",
      "adoption is not submission authority: the actor-bound path stays unavailable for record_human_disposition",
      "auto-close is forbidden; no agent may close this finding",
    ],
    human_sufficiency:
      "sufficient for a bounded-adoption disposition; the independent evaluation and the ledger disposition remain open and no agent may record them",
  },
  {
    finding_id: "RC28-F19",
    reviewer_severity: "medium",
    required_proof_class: "docs",
    required_proof: "class-matched docs/matrix consistency without lifecycle smoothing",
    evidence_paths: [
      "prd/architecture/m209-s01-r035-gate-register.json",
      "prd/architecture/m205-s04-docs-reconciliation.yaml",
      "prd/migration/rust-evidence/m204-s05-m073-residue-waiver.json",
      "prd/migration/rust-evidence/m209-s04-requirement-acceptance.json",
    ],
    rereverified: false,
    class_match: true,
    mismatch_reason_code: null,
    machine_verdict: "evidence_present_residual_named",
    residual_scope:
      "this matrix supplies the class-matched docs/matrix check for the RC28 evidence and finds no lifecycle smoothing; the broader documentation synchronization stays with the owning M205/S04 handoff and the owning implementation slices",
    non_claims: [
      "no requirement is promoted and the class-matched requirement id list stays empty",
      "historical reviews and receipts are preserved; corrections append or explicitly supersede and never silently relabel M203 as readiness",
    ],
    human_sufficiency:
      "sufficient for a docs-consistency disposition; no requirement or lifecycle promotion is available",
  },
];

const REQUIREMENT_EVIDENCE = [
  {
    requirement_id: "R038",
    canonical_class: "quality-attribute",
    evidence_class: "source-bound-criterion-plus-c4-gsd-attempt",
    class_matched: false,
    status_effect: "unchanged",
    related_findings: ["RC28-F01", "RC28-F03"],
    class_match_basis:
      "C4 operational acceptance remains non-pass; the evidence supports the criterion and the attempted run only and does not prove an operational pass",
    limitations: ["supports the criterion and the attempted run only; no operational pass"],
  },
  {
    requirement_id: "R063",
    canonical_class: "constraint",
    evidence_class: "process-provenance-without-product-change",
    class_matched: false,
    status_effect: "unchanged",
    related_findings: ["RC28-F03", "RC28-F05"],
    class_match_basis:
      "frozen process provenance is preserved; process provenance is not product composition proof",
    limitations: ["process provenance only; not product composition proof"],
  },
  {
    requirement_id: "R064",
    canonical_class: "operability",
    evidence_class: "thin-harness-operability-retest",
    class_matched: false,
    status_effect: "unchanged",
    related_findings: ["RC28-F03", "RC28-F05"],
    class_match_basis:
      "harness operability is retested; no engine repair, runtime readiness or acceptance is claimed",
    limitations: ["thin-harness operability only; no engine repair and no runtime readiness"],
  },
  {
    requirement_id: "R081",
    canonical_class: "constraint",
    evidence_class: "documentation-residue-no-new-work",
    class_matched: false,
    status_effect: "unchanged",
    related_findings: ["RC28-F03", "RC28-F04", "RC28-F05"],
    class_match_basis:
      "documentation residue is classified only. R081 concerns Work identity, so it must not be counted as class-matched proof for RC28-F03, RC28-F04 or RC28-F05",
    limitations: [
      "documentation residue only; R081 concerns Work identity and is not class-matched proof for F03/F04/F05",
    ],
  },
];

const REQUIREMENT_REFS = [
  { namespace: "gsd", id: "R038", canonical: true, relation: "supporting_only_class_matched_false" },
  { namespace: "gsd", id: "R063", canonical: true, relation: "supporting_only_class_matched_false" },
  { namespace: "gsd", id: "R064", canonical: true, relation: "supporting_only_class_matched_false" },
  { namespace: "gsd", id: "R081", canonical: true, relation: "supporting_only_class_matched_false" },
  {
    namespace: "prd",
    id: "RQ-009",
    canonical: false,
    canonical_gsd_id: null,
    relation: "prd_namespace_only",
    note: "a PRD applicability obligation linked to ADR-0023; it is not a canonical GSD R### requirement and is not proof for any RC28 finding",
  },
];

// ---------------------------------------------------------------------------
// live readers
// ---------------------------------------------------------------------------

export class MatrixError extends Error {
  constructor(code, detail) {
    super(`${code}: ${detail}`);
    this.name = "MatrixError";
    this.code = code;
    this.detail = detail;
  }
}

export function sha256Text(text) {
  return `sha256:${createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex")}`;
}

export function normalizeSha(value) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (/^[0-9a-f]{64}$/.test(trimmed)) return `sha256:${trimmed}`;
  if (/^sha256:[0-9a-f]{64}$/.test(trimmed)) return trimmed;
  return null;
}

export function pointerGet(value, pointer) {
  if (typeof pointer !== "string" || pointer.length === 0) return undefined;
  return pointer.split(".").reduce((acc, key) => {
    if (acc === null || acc === undefined) return undefined;
    return acc[key];
  }, value);
}

export function loadMatrixContext(rootDir = REPO_ROOT) {
  const textCache = new Map();
  const shaCache = new Map();
  const jsonCache = new Map();
  const readText = (relativePath) => {
    if (textCache.has(relativePath)) return textCache.get(relativePath);
    let value = null;
    try {
      value = readFileSync(path.join(rootDir, relativePath), "utf8");
    } catch {
      value = null;
    }
    textCache.set(relativePath, value);
    return value;
  };
  const readJson = (relativePath) => {
    if (jsonCache.has(relativePath)) return jsonCache.get(relativePath);
    const raw = readText(relativePath);
    let value = null;
    if (raw !== null) {
      try {
        value = JSON.parse(raw);
      } catch {
        value = null;
      }
    }
    jsonCache.set(relativePath, value);
    return value;
  };
  const sha = (relativePath) => {
    if (shaCache.has(relativePath)) return shaCache.get(relativePath);
    const raw = readText(relativePath);
    const value = raw === null ? null : sha256Text(raw);
    shaCache.set(relativePath, value);
    return value;
  };

  const packet = readJson(PACKET_RELATIVE_PATH);
  const packetClassById = new Map();
  if (packet && Array.isArray(packet.findings)) {
    for (const finding of packet.findings) {
      if (finding && typeof finding.finding_id === "string") {
        packetClassById.set(finding.finding_id, finding.required_proof_class ?? null);
      }
    }
  }

  let packetFiles = [];
  try {
    packetFiles = readdirSync(path.join(rootDir, PACKET_DIR_RELATIVE_PATH)).filter((name) =>
      name.endsWith(".json"),
    );
  } catch {
    packetFiles = [];
  }
  let packetStoreFindings = 0;
  let packetStoreRc28Open = 0;
  const packetStoreIds = [];
  for (const file of packetFiles) {
    const relative = `${PACKET_DIR_RELATIVE_PATH}/${file}`;
    const parsed = readJson(relative);
    if (!parsed || !Array.isArray(parsed.findings)) continue;
    for (const finding of parsed.findings) {
      packetStoreFindings += 1;
      if (!finding) continue;
      if (parsed.packet_id === PACKET_ID && typeof finding.finding_id === "string") {
        packetStoreIds.push(finding.finding_id);
        if (finding.disposition_status === "open") packetStoreRc28Open += 1;
      }
    }
  }
  let ledgerEventDirectories = 0;
  try {
    for (const entry of readdirSync(path.join(rootDir, PACKET_DIR_RELATIVE_PATH), {
      withFileTypes: true,
    })) {
      if (entry.isDirectory()) ledgerEventDirectories += 1;
    }
  } catch {
    ledgerEventDirectories = -1;
  }

  const s15 = readJson(S15_RELATIVE_PATH);
  const s15Rows = new Map();
  if (s15 && Array.isArray(s15.rows)) {
    for (const row of s15.rows) {
      if (row && typeof row.requirement_id === "string") s15Rows.set(row.requirement_id, row);
    }
  }

  return {
    rootDir,
    readText,
    readJson,
    sha,
    pointer: (relativePath, pointer) => pointerGet(readJson(relativePath), pointer),
    packet,
    packetClassById,
    packetFiles,
    packetStoreFindings,
    packetStoreRc28Open,
    packetStoreIds,
    ledgerEventDirectories,
    s15,
    s15Row: (requirementId) => s15Rows.get(requirementId) ?? null,
    programText: readText(PROGRAM_RELATIVE_PATH) ?? "",
    inventoryText: readText(INVENTORY_RELATIVE_PATH) ?? "",
    eventsDirectoryPresent: existsSync(path.join(rootDir, PACKET_EVENTS_DIR_RELATIVE_PATH)),
  };
}

// ---------------------------------------------------------------------------
// report construction
// ---------------------------------------------------------------------------

function buildRows(ctx) {
  return FINDING_ROWS.map((row) => {
    const built = {
      finding_id: row.finding_id,
      reviewer_severity: row.reviewer_severity,
      required_proof_class: row.required_proof_class,
      required_proof: row.required_proof,
      required_proof_verbatim_source: PROGRAM_RELATIVE_PATH,
      rereverified: row.rereverified,
      reverification: row.reverification ?? null,
      class_match: row.class_match,
      mismatch_reason_code: row.mismatch_reason_code,
      machine_verdict: row.machine_verdict,
      evidence_paths: row.evidence_paths.map((relativePath) => ({
        path: relativePath,
        sha256: ctx.sha(relativePath),
      })),
      residual_scope: row.residual_scope,
      non_claims: row.non_claims,
      human_sufficiency: row.human_sufficiency,
      status_effect: "unchanged",
    };
    if (row.deferral_reference !== undefined) {
      built.deferral_reference = row.deferral_reference;
      built.deferral_treated_as_proof = row.deferral_treated_as_proof;
    }
    if (row.owner_status !== undefined) built.owner_status = row.owner_status;
    if (row.auto_close !== undefined) built.auto_close = row.auto_close;
    return built;
  });
}

function buildRequirementEvidence(ctx) {
  return REQUIREMENT_EVIDENCE.map((row) => ({
    requirement_id: row.requirement_id,
    namespace: "gsd",
    canonical_class: row.canonical_class,
    canonical_class_source: "m210 S04 T02 plan contract",
    evidence_class: row.evidence_class,
    evidence_class_source: S15_RELATIVE_PATH,
    class_matched: row.class_matched,
    status_effect: row.status_effect,
    related_findings: row.related_findings,
    class_match_basis: row.class_match_basis,
    limitations: row.limitations,
    source_paths: [{ path: S15_RELATIVE_PATH, sha256: ctx.sha(S15_RELATIVE_PATH) }],
  }));
}

function buildReviewCase(ctx) {
  const packetFindings = Array.isArray(ctx.packet?.findings) ? ctx.packet.findings : [];
  const embeddedEvents = Array.isArray(ctx.packet?.events) ? ctx.packet.events : [];
  const humanDispositionEvents = embeddedEvents.filter(
    (event) => event && event.actor_class === "human",
  );
  return {
    packet_id: PACKET_ID,
    packet_path: PACKET_RELATIVE_PATH,
    packet_file_sha256: ctx.sha(PACKET_RELATIVE_PATH),
    packet_authoritative: ctx.packet?.authoritative === true,
    packet_authority_required: ctx.packet?.authority_required === true,
    source_path: SOURCE_REVIEW_RELATIVE_PATH,
    source_content_sha256: ctx.sha(SOURCE_REVIEW_RELATIVE_PATH),
    packet_declared_content_sha256: normalizeSha(ctx.packet?.source?.content_sha256),
    packet_declared_content_sha256_raw: ctx.packet?.source?.content_sha256 ?? null,
    reviewed_git_revision: ctx.packet?.source?.reviewed_git_revision ?? null,
    reviewed_git_revision_format: REVIEWED_GIT_REVISION_FORMAT,
    embedded_event_count: embeddedEvents.length,
    embedded_events: embeddedEvents.map((event) => ({
      event_id: event?.event_id ?? null,
      event_type: event?.event_type ?? null,
      actor_class: event?.actor_class ?? null,
      source_revision: event?.source_revision ?? null,
    })),
    human_disposition_event_count: humanDispositionEvents.length,
    events_directory_present: ctx.eventsDirectoryPresent,
    events_directory_path: PACKET_EVENTS_DIR_RELATIVE_PATH,
    findings_total: packetFindings.length,
    findings_open: packetFindings.filter((f) => f?.disposition_status === "open").length,
    actor_bound_path_available: false,
    actor_bound_scope: "record_human_disposition",
    actor_bound_limitation:
      "the review-case application accepts a caller-supplied actor_class and actor_id and the published CLI offers read-only validate/status/inventory only, so no human disposition may be submitted through this record and the packet stays open until a trustworthy actor-bound submission path exists",
    packet_findings_state: packetFindings.map((finding) => ({
      finding_id: finding?.finding_id ?? null,
      concern_class: finding?.concern_class ?? null,
      required_proof_class: finding?.required_proof_class ?? null,
      disposition_status: finding?.disposition_status ?? null,
      kind: finding?.kind ?? null,
    })),
    inventory_observation: {
      observed_via:
        "uv run python -m law_nexus_harness review-case inventory --packet-id RC-2026-09-10-001",
      observation_kind: "recorded_live_cli_observation",
      finding_count: 19,
      residual_counts: [["awaiting_disposition", 19]],
      stage_counts: [["S1_normalized", 19]],
      open_blockers: [],
      last_event: null,
      missing_for_next: ["human disposition_recorded with rationale and source_revision"],
      next_admissible_events: ["disposition_recorded", "normalization_reviewed"],
      non_claims: ["Tool-generated finding; not human disposition or legal acceptance."],
    },
  };
}

function buildSummary(rows, requirementRows) {
  const verdictCounts = {};
  for (const row of rows) {
    verdictCounts[row.machine_verdict] = (verdictCounts[row.machine_verdict] ?? 0) + 1;
  }
  const evidencePathCount = rows.reduce((total, row) => total + row.evidence_paths.length, 0);
  return {
    finding_count: rows.length,
    rows_rereverified: rows.filter((row) => row.rereverified).length,
    class_matched_rows: rows.filter((row) => row.class_match).length,
    class_mismatched_rows: rows.filter((row) => !row.class_match).length,
    machine_verdict_counts: verdictCounts,
    requirement_evidence_rows: requirementRows.length,
    class_matched_requirement_ids: [],
    status_effect_values: ["unchanged"],
    required_proof_class_values: [...new Set(rows.map((row) => row.required_proof_class))].sort(),
    evidence_path_count: evidencePathCount,
  };
}

export function buildReport(ctx) {
  const rows = buildRows(ctx);
  const requirementRows = buildRequirementEvidence(ctx);
  return {
    schema: SCHEMA,
    schema_version: SCHEMA_VERSION,
    kind: KIND,
    milestone: MILESTONE,
    slice: SLICE,
    task: TASK,
    lifecycle: LIFECYCLE,
    authoritative: false,
    ascii_only: true,
    status_effect: "unchanged",
    requirement_promotion: false,
    required_proof_derivation: {
      packet_field: "required_proof_class",
      packet_has_verbatim_required_proof: false,
      verbatim_source: PROGRAM_RELATIVE_PATH,
      inventory_source: INVENTORY_RELATIVE_PATH,
      note: "the packet carries required_proof_class only and no required-proof sentence, so each sentence is taken verbatim from the owning program record (and its Required proof (verbatim) column in the disposition inventory) and is re-validated against the program document by the contract",
    },
    vocabularies: {
      required_proof_class: REQUIRED_PROOF_CLASSES,
      machine_verdict: MACHINE_VERDICTS,
      mismatch_reason_code: MISMATCH_REASON_CODES,
    },
    requirement_refs: REQUIREMENT_REFS,
    canonical_requirement_readings: {
      tool_name: "gsd_requirement_get",
      tool_available_in_unit: false,
      direct_db_read: false,
      read_via: "plan-supplied",
      note: "the execute-task unit surface does not present a canonical requirement reader, so the canonical classes are taken from the T02 plan contract; this record does not query the canonical store and does not assert canonical store contents, requirement status, ownership or validation",
      readings: REQUIREMENT_EVIDENCE.map((row) => ({
        requirement_id: row.requirement_id,
        namespace: "gsd",
        canonical_class: row.canonical_class,
        canonical_class_source: "m210 S04 T02 plan contract",
        canonical_store_queried: false,
      })),
    },
    review_case: buildReviewCase(ctx),
    review_case_rollup: {
      ...ROLLUP,
      cross_check: {
        packet_files: ctx.packetFiles.length,
        packet_store_findings: ctx.packetStoreFindings,
        packet_store_rc28_open: ctx.packetStoreRc28Open,
        ledger_event_directories: ctx.ledgerEventDirectories,
      },
      non_claims: [
        "the rollup is a recorded live CLI observation; only the packet-level parts are re-derived offline",
        "the ledger FSM is not re-implemented here and no ledger status is inferred by this record",
      ],
    },
    disposition_model: {
      mode: "per_finding",
      grouping_allowed: true,
      blanket_confirmation: false,
      preselected_consent: false,
      recommendation_is_not_consent: true,
      read_back_required_after_each_answer: true,
      actor_bound_path_available: false,
      submission_channel_used: "none",
    },
    rows,
    requirement_evidence: requirementRows,
    summary: buildSummary(rows, requirementRows),
    boundary: {
      review_case_events_written: false,
      record_human_disposition_called: false,
      actor_bound_path_available: false,
      requirements_promoted: [],
      requirement_status_mutated: false,
      runtime_touched: false,
      crates_touched: [],
      source_artifacts_rewritten: [],
    },
    non_claims: NON_CLAIMS,
  };
}

// ---------------------------------------------------------------------------
// validation
// ---------------------------------------------------------------------------

export function renderText(report) {
  return `${JSON.stringify(report, null, 2)}\n`;
}

export function validateMatrix(report, ctx, options = {}) {
  const codes = [];
  const add = (code, detail) => codes.push({ code, detail });
  const text = typeof options.text === "string" ? options.text : renderText(report);

  if (/[^\u0000-\u007f]/.test(text)) {
    add("non_ascii_artifact", "the rendered matrix carries a non-ASCII code point");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (text.includes(marker)) {
      add("raw_text_leak", `the rendered matrix carries the raw-text marker ${JSON.stringify(marker)}`);
    }
  }

  const rows = Array.isArray(report?.rows) ? report.rows : [];
  if (rows.length !== FINDING_IDS.length) {
    add("row_count_incomplete", `rows=${rows.length} expected=${FINDING_IDS.length}`);
  }
  if (report?.summary?.finding_count !== rows.length) {
    add("row_count_incomplete", `summary.finding_count=${report?.summary?.finding_count} rows=${rows.length}`);
  }
  if (report?.review_case?.findings_total !== FINDING_IDS.length) {
    add("row_count_incomplete", `review_case.findings_total=${report?.review_case?.findings_total}`);
  }
  if (report?.review_case?.findings_open !== FINDING_IDS.length) {
    add("row_count_incomplete", `review_case.findings_open=${report?.review_case?.findings_open}`);
  }
  if (report?.review_case_rollup?.finding_count !== ctx.packetStoreFindings) {
    add("row_count_incomplete", "review_case_rollup.finding_count disagrees with the live packet store");
  }

  const byId = new Map();
  for (const row of rows) {
    const id = row?.finding_id;
    if (typeof id !== "string" || !FINDING_IDS.includes(id)) {
      add("finding_id_unknown", `unknown finding_id ${JSON.stringify(id)}`);
      continue;
    }
    if (byId.has(id)) {
      add("finding_id_unknown", `duplicate finding_id ${id}`);
      continue;
    }
    byId.set(id, row);
  }
  for (const id of FINDING_IDS) {
    if (!byId.has(id)) add("row_count_incomplete", `missing row ${id}`);
  }

  for (const id of FINDING_IDS) {
    const row = byId.get(id);
    if (!row) continue;
    const packetClass = ctx.packetClassById.get(id) ?? null;
    if (!REQUIRED_PROOF_CLASSES.includes(row.required_proof_class)) {
      add("proof_class_mismatch", `${id} proof class ${JSON.stringify(row.required_proof_class)}`);
    } else if (packetClass !== null && row.required_proof_class !== packetClass) {
      add("proof_class_mismatch", `${id} ${row.required_proof_class} != packet ${packetClass}`);
    }
    if (typeof row.status_effect !== "string" || row.status_effect.length === 0) {
      add("status_effect_missing", id);
    } else if (row.status_effect !== "unchanged") {
      add("requirement_promotion_claimed", `${id} status_effect=${row.status_effect}`);
    }
    if (!MACHINE_VERDICTS.includes(row.machine_verdict)) {
      add("verdict_unknown", `${id} machine_verdict=${JSON.stringify(row.machine_verdict)}`);
    }
    if (row.class_match === false && !MISMATCH_REASON_CODES.includes(row.mismatch_reason_code)) {
      add("class_mismatch_unexplained", `${id} mismatch_reason_code=${JSON.stringify(row.mismatch_reason_code)}`);
    }
    if (row.class_match === true && row.mismatch_reason_code !== null && row.mismatch_reason_code !== undefined) {
      add("class_mismatch_unexplained", `${id} matched but reason=${JSON.stringify(row.mismatch_reason_code)}`);
    }
    for (const entry of Array.isArray(row.evidence_paths) ? row.evidence_paths : []) {
      const live = ctx.sha(entry?.path);
      if (live === null) add("evidence_path_unresolved", `${id} ${JSON.stringify(entry?.path)}`);
      else if (entry.sha256 !== live) add("evidence_hash_mismatch", `${id} ${entry.path}`);
    }
    const reverification = row.reverification;
    if (row.rereverified === true) {
      if (
        !reverification ||
        typeof reverification !== "object" ||
        !Array.isArray(reverification.observed) ||
        reverification.observed.length === 0 ||
        reverification.verdict !== "confirmed"
      ) {
        add("reverification_missing", `${id} empty reverification`);
      } else {
        for (const token of Array.isArray(reverification.tokens) ? reverification.tokens : []) {
          const source = ctx.readText(token?.path);
          if (source === null || !source.includes(token.token)) {
            add("reverification_missing", `${id} token ${JSON.stringify(token?.token)} absent from ${token?.path}`);
          }
        }
        for (const field of Array.isArray(reverification.observed_fields) ? reverification.observed_fields : []) {
          const seen = ctx.pointer(field?.path, field?.pointer);
          if (Object.prototype.hasOwnProperty.call(field, "equals_file_sha256")) {
            const expected = ctx.sha(field.equals_file_sha256);
            if (expected === null || seen !== expected) {
              add("reverification_missing", `${id} pointer ${field.pointer} != live sha of ${field.equals_file_sha256}`);
            }
          } else if (seen !== field.equals) {
            add("reverification_missing", `${id} pointer ${field.pointer}=${JSON.stringify(seen)} expected ${JSON.stringify(field.equals)}`);
          }
        }
      }
    } else if (REVERIFICATION_REQUIRED_IDS.includes(id)) {
      add("reverification_missing", `${id} must be re-verified in this pass`);
    }
    const mentionsD519 = /D519/.test(
      `${row.residual_scope ?? ""} ${(Array.isArray(row.non_claims) ? row.non_claims : []).join(" ")} ${row.human_sufficiency ?? ""}`,
    );
    if (
      (row.deferral_reference === "D519" && row.deferral_treated_as_proof !== false) ||
      (mentionsD519 && row.machine_verdict === "evidence_present_class_matched")
    ) {
      add("d519_treated_as_proof", `${id} treats the D519 deferral as proof`);
    }
    if (id === "RC28-F18" && row.auto_close !== false) {
      add("f18_auto_close", `RC28-F18 auto_close=${JSON.stringify(row.auto_close)}`);
    }
    if (id === "RC28-F13" && row.owner_status !== "deferred-explicit") {
      add("f13_missing_answer_misread", `RC28-F13 owner_status=${JSON.stringify(row.owner_status)}`);
    }
  }

  const requirementRows = Array.isArray(report?.requirement_evidence) ? report.requirement_evidence : [];
  for (const row of requirementRows) {
    const id = row?.requirement_id;
    if (typeof row?.status_effect !== "string" || row.status_effect.length === 0) {
      add("status_effect_missing", `requirement ${id}`);
    } else if (row.status_effect !== "unchanged") {
      add("requirement_promotion_claimed", `requirement ${id} status_effect=${row.status_effect}`);
    }
    if (row.class_matched !== false) {
      add("lifecycle_smoothing_detected", `requirement ${id} class_matched=${JSON.stringify(row.class_matched)}`);
    }
    const tracked = ctx.s15Row(id);
    if (!tracked) {
      add("proof_class_mismatch", `requirement ${id} absent from ${S15_RELATIVE_PATH}`);
    } else if (tracked.evidence_class !== row.evidence_class || tracked.class_matched !== false) {
      add("proof_class_mismatch", `requirement ${id} disagrees with the tracked classification`);
    }
    for (const entry of Array.isArray(row.source_paths) ? row.source_paths : []) {
      const live = ctx.sha(entry?.path);
      if (live === null) add("evidence_path_unresolved", `requirement ${id} ${JSON.stringify(entry?.path)}`);
      else if (entry.sha256 !== live) add("evidence_hash_mismatch", `requirement ${id} ${entry.path}`);
    }
  }

  if ((report?.summary?.class_matched_requirement_ids ?? []).length > 0) {
    add("lifecycle_smoothing_detected", "summary.class_matched_requirement_ids is not empty");
  }
  if (report?.requirement_promotion !== false) {
    add("requirement_promotion_claimed", `requirement_promotion=${JSON.stringify(report?.requirement_promotion)}`);
  }
  if ((report?.boundary?.requirements_promoted ?? []).length > 0) {
    add("requirement_promotion_claimed", "boundary.requirements_promoted is not empty");
  }

  for (const ref of Array.isArray(report?.requirement_refs) ? report.requirement_refs : []) {
    if (ref?.namespace === "gsd") {
      if (!/^R\d{3}$/.test(String(ref?.id))) {
        add("requirement_namespace_confusion", `gsd ref with non-canonical id ${JSON.stringify(ref?.id)}`);
      }
    } else if (ref?.namespace === "prd") {
      if (ref?.canonical !== false || ref?.canonical_gsd_id !== null) {
        add("requirement_namespace_confusion", `prd ref ${JSON.stringify(ref?.id)} claims canonical GSD identity`);
      }
      if (!/^RQ-\d{3}$/.test(String(ref?.id))) {
        add("requirement_namespace_confusion", `prd ref with non-PRD id ${JSON.stringify(ref?.id)}`);
      }
    } else {
      add("requirement_namespace_confusion", `unbound namespace ${JSON.stringify(ref?.namespace)}`);
    }
  }
  if (!(report?.requirement_refs ?? []).some((ref) => ref?.namespace === "prd" && ref?.id === "RQ-009")) {
    add("requirement_namespace_confusion", "the RQ-009 PRD-namespace reference is absent");
  }

  const model = report?.disposition_model;
  if (
    !model ||
    model.mode !== "per_finding" ||
    model.blanket_confirmation !== false ||
    model.preselected_consent !== false
  ) {
    add("owner_choice_folded", "the disposition model is not per-finding individual consent");
  }

  const reviewCase = report?.review_case;
  if (
    reviewCase?.human_disposition_event_count !== 0 ||
    reviewCase?.events_directory_present !== false ||
    report?.boundary?.review_case_events_written !== false
  ) {
    add("review_case_event_written", "a Review Case human disposition event is claimed to exist");
  }
  if (ctx.sha(SOURCE_REVIEW_RELATIVE_PATH) !== reviewCase?.source_content_sha256) {
    add("evidence_hash_mismatch", "review_case.source_content_sha256 disagrees with the live review document");
  }
  if (
    normalizeSha(reviewCase?.packet_declared_content_sha256) !== reviewCase?.source_content_sha256 ||
    normalizeSha(reviewCase?.packet_declared_content_sha256_raw) !== reviewCase?.source_content_sha256
  ) {
    add("evidence_hash_mismatch", "the packet-declared content hash disagrees with the live review document hash");
  }
  if (reviewCase?.packet_id !== ctx.packet?.packet_id) {
    add("row_count_incomplete", `review_case.packet_id=${reviewCase?.packet_id}`);
  }
  if (!/^[0-9a-f]{40}$/.test(String(reviewCase?.reviewed_git_revision ?? ""))) {
    add("verdict_unknown", "reviewed_git_revision is not a 40-hex git revision");
  }
  if (reviewCase?.embedded_event_count !== 1 || (reviewCase?.embedded_events ?? []).length !== 1) {
    add("review_case_event_written", `embedded_event_count=${reviewCase?.embedded_event_count}`);
  }
  const rollup = report?.review_case_rollup;
  if (
    rollup?.ok !== true ||
    rollup?.finding_count !== ROLLUP.finding_count ||
    rollup?.closed_count !== ROLLUP.closed_count ||
    rollup?.open_count !== ROLLUP.open_count ||
    rollup?.blocked_count !== ROLLUP.blocked_count ||
    rollup?.partial_count !== ROLLUP.partial_count ||
    JSON.stringify(rollup?.rollup_digits) !== JSON.stringify(ROLLUP.rollup_digits)
  ) {
    add("verdict_unknown", "review_case_rollup is not the observed ok rollup 35/10/21/0/0");
  }
  if (rollup?.cross_check?.packet_store_findings !== ctx.packetStoreFindings) {
    add("row_count_incomplete", "rollup cross-check finding total disagrees with the live packet store");
  }
  if (rollup?.cross_check?.packet_store_rc28_open !== ctx.packetStoreRc28Open) {
    add("row_count_incomplete", "rollup cross-check RC28 open count disagrees with the live packet store");
  }
  if (rollup?.cross_check?.ledger_event_directories !== ctx.ledgerEventDirectories) {
    add("row_count_incomplete", "rollup cross-check ledger event directory count disagrees with the live store");
  }
  if (rollup?.cross_check?.packet_files !== ctx.packetFiles.length) {
    add("row_count_incomplete", "rollup cross-check packet file count disagrees with the live store");
  }

  return codes;
}

export function renderMatrix(rootDir = REPO_ROOT) {
  const ctx = loadMatrixContext(rootDir);
  const report = buildReport(ctx);
  const text = renderText(report);
  const codes = validateMatrix(report, ctx, { text });
  return { report, text, codes, ctx };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

export function runCli(argv = [], options = {}) {
  const rootDir = options.rootDir ?? REPO_ROOT;
  const stdout = [];
  const stderr = [];
  const args = argv.filter((arg) => typeof arg === "string");
  const mode = args.includes("--check") ? "check" : args.includes("--print") ? "print" : "write";
  const unknown = args.filter((arg) => !["--check", "--print", "--write"].includes(arg));
  if (unknown.length > 0) {
    for (const arg of unknown) stderr.push(`unknown argument: ${arg}`);
    return { mode, exitCode: 2, stdout, stderr, wrote: false };
  }

  let rendered;
  try {
    rendered = renderMatrix(rootDir);
  } catch (error) {
    stderr.push(`render failed: ${String(error?.message || error)}`);
    return { mode, exitCode: 1, stdout, stderr, wrote: false };
  }

  if (mode === "print") {
    if (rendered.codes.length > 0) {
      for (const entry of rendered.codes) stderr.push(`${entry.code}: ${entry.detail}`);
      return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
    }
    stdout.push(rendered.text.replace(/\n$/, ""));
    stderr.push(PRINT_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }

  if (mode === "check") {
    const committedText =
      typeof options.committedText === "string"
        ? options.committedText
        : existsSync(path.join(rootDir, MATRIX_RELATIVE_PATH))
          ? readFileSync(path.join(rootDir, MATRIX_RELATIVE_PATH), "utf8")
          : null;
    if (rendered.codes.length > 0) {
      for (const entry of rendered.codes) stderr.push(`${entry.code}: ${entry.detail}`);
      return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
    }
    if (committedText === null || committedText !== rendered.text) {
      stderr.push(
        `check_not_byte_identical: committed matrix ${committedText === null ? "is absent" : "differs from the rendered matrix"}`,
      );
      return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
    }
    stdout.push(CHECK_OK_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }

  if (rendered.codes.length > 0) {
    for (const entry of rendered.codes) stderr.push(`${entry.code}: ${entry.detail}`);
    return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report, text: rendered.text };
  }
  if (!options.dryRun) writeFileSync(path.join(rootDir, MATRIX_RELATIVE_PATH), rendered.text);
  stdout.push(WRITTEN_MARKER);
  return {
    mode,
    exitCode: 0,
    stdout,
    stderr,
    wrote: !options.dryRun,
    report: rendered.report,
    text: rendered.text,
  };
}

export function main(argv = process.argv.slice(2)) {
  const result = runCli(argv);
  for (const line of result.stderr) process.stderr.write(`${line}\n`);
  for (const line of result.stdout) process.stdout.write(`${line}\n`);
  process.exitCode = result.exitCode;
  return result;
}

const invokedDirectly =
  typeof process.argv[1] === "string" &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  main();
}
