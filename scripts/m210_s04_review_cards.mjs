#!/usr/bin/env node
// M210-3afp79 S04 T03 -- RC28 review cards and the grouped review presentation.
//
// WHY THIS FILE EXISTS
// M210/S04 has to put 19 source-bound cards in front of a human reviewer before
// any choice is made. A card may not be a summary of a summary: it has to carry
// the packet identity, the reviewed revision, the live content digest of the
// review document, the proof class, the check outcome actually observed, the
// residual scope, the non-claims, a proposed disposition with its basis, the
// lawful alternatives and a session question -- and it must be impossible for the
// cards to drift from the artifact that produced them (T02's finding evidence
// matrix) without failing `--check`.
//
// IT DERIVES, IT DOES NOT INVENT
//   * summary / concern_class -- read live from the packet findings.
//   * source{packet_id, source_path, reviewed_git_revision, content_sha256} --
//     the packet's own source binding, re-checked live against the review
//     document hash and the matrix's review_case block.
//   * tested_source_revision -- the live content sha256 of T02's matrix, i.e. the
//     exact revision of the tested evidence the card is derived from. Drift of
//     the matrix changes every card revision and therefore fails `--check`.
//   * proof_class / check_outcome / residual_scope / non_claims /
//     mismatch_reason_code -- copied one-to-one from the matrix row.
//   * evidence_class -- the class of the evidence surface actually available: the
//     proof class when the matrix records a class match, otherwise `docs`
//     (adoption-state documents are docs, never implementation proof).
//   * F18 adoption refs / criterion id -- the v2 checkpoint and the v2 answer
//     record named by the matrix, plus the subjective-UAT criterion id that the
//     matrix residual scope carries verbatim.
//   * proposed_disposition -- this file's only human-facing judgement. It is
//     advisory, non-consent, never preselected, and structurally constrained by
//     the matrix verdict (see PROPOSAL_RULES below).
//
// WHAT IT REFUSES TO DO
//   No Review Case event, no `record_human_disposition` call, no disposition
//   recorded, no option selected, no requirement promotion, no lifecycle
//   smoothing, no runtime mutation, no DATABASE read, no rewrite of a cited
//   source. D519 is an explicit deferral and never proof. RC28-F18's bounded
//   variant C adoption is adoption evidence, and auto-close stays forbidden.
//
// USAGE
//   node scripts/m210_s04_review_cards.mjs --write   # default
//   node scripts/m210_s04_review_cards.mjs --check
//   node scripts/m210_s04_review_cards.mjs --print   # cards JSON on stdout

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(HERE, "..");

export const CARDS_RELATIVE_PATH = "prd/architecture/m210-s04-rc28-review-cards.json";
export const PRESENTATION_RELATIVE_PATH = "prd/architecture/m210-s04-rc28-review-presentation.md";
export const MATRIX_RELATIVE_PATH = "prd/architecture/m210-s04-finding-evidence-matrix.json";
export const PACKET_RELATIVE_PATH =
  "prd/architecture/review-cases/packets/RC-2026-09-10-001.json";
export const SOURCE_REVIEW_RELATIVE_PATH = "doc/review/review-28-10-09-2026.md";
export const PACKET_EVENTS_DIR_RELATIVE_PATH =
  "prd/architecture/review-cases/packets/RC-2026-09-10-001";
export const CONTRACT_RELATIVE_PATH = "scripts/m210_s04_review_cards_contract.test.mjs";

export const SCHEMA = "law-nexus/m210-s04-rc28-review-cards/v1";
export const SCHEMA_VERSION = 1;
export const KIND = "m210-s04-rc28-review-cards";
export const MILESTONE = "M210-3afp79";
export const SLICE = "S04";
export const TASK = "T03";
export const LIFECYCLE = ["proposed"];

export const PACKET_ID = "RC-2026-09-10-001";
export const MATRIX_SCHEMA = "law-nexus/m210-s04-finding-evidence-matrix/v1";

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

// Closed vocabularies. `proof_class` / `evidence_class` mirror the review-case
// schema's proof_class enum; `check_outcome` mirrors the T02 matrix verdict enum;
// `proposed_disposition` mirrors the review-case disposition_status enum.
export const PROOF_CLASSES = ["evidence", "process", "implementation", "design", "docs"];
export const CHECK_OUTCOMES = [
  "evidence_present_class_matched",
  "evidence_present_residual_named",
  "evidence_absent_residual_named",
  "evidence_class_mismatch",
  "awaiting_owner_decision",
  "gate_hold",
];
export const RC28_DISPOSITIONS = [
  "open",
  "needs_discussion",
  "needs_research",
  "accepted_as_gap",
  "accepted_as_requirement_candidate",
  "accepted_as_decision_candidate",
  "accepted_as_process_defect",
  "already_satisfied",
  "rejected",
  "deferred",
  "duplicate",
  "superseded",
  "not_applicable",
];
export const ALTERNATIVE_IDS = ["change", "defer", "stop_session"];

export const EMITTABLE_CODES = [
  "card_count_incomplete",
  "card_source_missing",
  "card_proof_class_missing",
  "card_outcome_missing",
  "card_residual_missing",
  "card_non_claims_missing",
  "card_alternatives_insufficient",
  "recommendation_as_consent",
  "card_preselected",
  "presentation_finding_missing",
  "presentation_finding_duplicated",
  "f18_auto_close",
  "f13_missing_answer_misread",
  "d519_treated_as_proof",
  "already_satisfied_unsupported",
  "non_ascii_artifact",
  "raw_text_leak",
  "check_not_byte_identical",
];

export const WRITTEN_MARKER = "M210_S04_CARDS_WRITTEN";
export const CHECK_OK_MARKER = "M210_S04_CARDS_CHECK_OK";
export const PRINT_MARKER = "M210_S04_CARDS_PRINTED";
export const CONTRACT_MARKER = "M210_S04_CARDS_OK";

export const F18_CRITERION_ID = "37181c25-88b0-4896-bffe-d10642970e6f";
export const F18_ADOPTION_REFS = [
  { path: "prd/architecture/m210-s02-adoption-checkpoint-v2.md", kind: "v2_checkpoint" },
  { path: "prd/architecture/m210-s02-answer-record-v2.json", kind: "v2_answer_record" },
];

// Grouping is for reading only. It never turns one confirmation into 19
// decisions; every finding keeps its own session question and answer slot.
export const GROUP_DEFS = [
  { group_id: "g-evidence", concern_class: "evidence", label_ru: "evidence" },
  { group_id: "g-process", concern_class: "process", label_ru: "process" },
  { group_id: "g-implementation", concern_class: "implementation", label_ru: "implementation" },
  { group_id: "g-design", concern_class: "design", label_ru: "design" },
  { group_id: "g-docs", concern_class: "docs", label_ru: "docs" },
];

// PROPOSAL_RULES (also enforced by validateCards):
//   * the proposal is always one of RC28_DISPOSITIONS;
//   * a row whose evidence is absent or class-mismatched never proposes
//     `already_satisfied` (a D519 row doing so is `d519_treated_as_proof`, any
//     other row is `already_satisfied_unsupported`);
//   * a class-matched row proposes `already_satisfied`;
//   * RC28-F18 proposes `deferred` with auto_close=false (adoption evidence is
//     present, the independent evaluation and the ledger disposition are not);
//   * RC28-F13 proposes `deferred` with owner_status=deferred-explicit;
//   * RC28-F01 / RC28-F15 propose `deferred` citing D519, never `already_satisfied`.
const DISPOSITION_PROPOSALS = {
  "RC28-F01": {
    disposition: "deferred",
    basis:
      "D519 is a scope deferral, not evidence: the coder-bound measurement is absent and only the frozen protocol and the non-pass receipt exist",
  },
  "RC28-F02": {
    disposition: "deferred",
    basis:
      "the frozen protocol is class-matched but no measured strata exist; the measurement is the named residual",
  },
  "RC28-F03": {
    disposition: "accepted_as_gap",
    basis:
      "the C4 receipt self-declares operational_acceptance non-pass; the operational criterion is not met",
  },
  "RC28-F04": {
    disposition: "already_satisfied",
    basis:
      "the sanctioned outcome and its fresh repeat are class-matched and re-verified with a predecessor digest chain",
  },
  "RC28-F05": {
    disposition: "accepted_as_process_defect",
    basis:
      "the claim dispatch defect is reproduced and lawfully recovered, but four pending task identities stay unresolved",
  },
  "RC28-F06": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the container sibling closure gap remains",
  },
  "RC28-F07": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the continuation eligibility gap remains",
  },
  "RC28-F08": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the ThisRef ownership gap remains",
  },
  "RC28-F09": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the already captured member dependency gap remains",
  },
  "RC28-F10": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the token and range variant divergence remains",
  },
  "RC28-F11": {
    disposition: "accepted_as_gap",
    basis:
      "adoption-state documents are not implementation proof; the substring cue and whole-block Actor gap remains",
  },
  "RC28-F12": {
    disposition: "accepted_as_gap",
    basis:
      "the self, antecedent, alias and edition reference distinction remains a design gap with a named residual",
  },
  "RC28-F13": {
    disposition: "deferred",
    basis:
      "explicit owner defer: no live adoption owner exists and M208 recorded not-adopted three times",
  },
  "RC28-F14": {
    disposition: "already_satisfied",
    basis:
      "the functional prior-art matrix is class-matched and re-verified with design-only non-claims",
  },
  "RC28-F15": {
    disposition: "deferred",
    basis:
      "D519 is a scope deferral, not evidence: the independent annotation and the source-bound human acceptance are absent",
  },
  "RC28-F16": {
    disposition: "deferred",
    basis:
      "the gate register is delivered but GATE-G015 is conflicted and nothing is promoted, so the gate stays held",
  },
  "RC28-F17": {
    disposition: "accepted_as_gap",
    basis:
      "scoped coverage is delivered while the M208 components stay not-adopted as the historical admission attempt",
  },
  "RC28-F18": {
    disposition: "deferred",
    basis:
      "bounded adoption evidence for variant C is present; the independent evaluation and the ledger disposition are separate and pending, and auto-close is forbidden",
  },
  "RC28-F19": {
    disposition: "accepted_as_gap",
    basis:
      "the docs and matrix synchronization is class-matched here, but the broader correction stays with the owning handoff",
  },
};

const ALTERNATIVES = [
  {
    id: "change",
    label: "Change",
    description: "record a change or repair disposition for this finding",
  },
  {
    id: "defer",
    label: "Defer",
    description: "record an explicit deferral that names the residual scope",
  },
  {
    id: "stop_session",
    label: "Stop session",
    description: "stop the review session without recording any disposition",
  },
];

const RAW_TEXT_MARKERS = ["<", ">", "consultantplus://", "screenTip"];

const NON_CLAIMS = [
  "These cards are a machine-prepared presentation for a human reviewer. They are not a Review Case disposition, not a legal conclusion, not a requirement closure and not a lifecycle promotion.",
  "No Review Case event is written, no actor-bound human disposition path is invoked, no option is selected and no disposition is recorded; the RC28 findings stay open until a human records a disposition through a sanctioned path.",
  "A recommendation is advisory and is not consent. Nothing is preselected: every card keeps preselected=false, selected=false and human_answer=null.",
  "The packet, the reviewed revision and the review-document digest are shown on every card, but a live digest proves identity, not truth; the review document is authoritative only in its own artifact.",
  "The bounded adoption of variant C recorded for RC28-F18 is adoption evidence. The independent evaluation and the ledger disposition are separate, still pending, and auto-close is forbidden.",
  "D519 removed an M207 obligation; it is an explicit deferral and is never evidence for RC28-F01 or RC28-F15.",
  "A RC28 HOLD remains until valid human dispositions exist; the adoption of variant C does not close any finding automatically.",
];

const SESSION_RULES = [
  "Every finding is answered individually. Grouping reduces reading only and never turns one blanket confirmation into 19 decisions.",
  "A recommendation is advisory and is not consent; the recommendation field keeps advisory=true and is_consent=false.",
  "After each answer, read back the finding id, the chosen outcome, the tested revision and the rationale.",
  "Drift of a source, an evidence digest or a packet fingerprint between display and submission cancels the proposal and requires a new review.",
  "Only findings explicitly confirmed are persisted, and only through an actor-bound submission path.",
  "The session writes no Review Case event and selects no option on the human's behalf.",
];

const PRESENTATION_SECTIONS = [
  "What this is",
  "Groups",
  "Session rules",
  "Non-claims",
];

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

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

export function loadCardsContext(rootDir = REPO_ROOT) {
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

  const matrix = readJson(MATRIX_RELATIVE_PATH);
  const packet = readJson(PACKET_RELATIVE_PATH);
  const packetFindings = Array.isArray(packet?.findings) ? packet.findings : [];
  const packetById = new Map();
  for (const finding of packetFindings) {
    if (finding && typeof finding.finding_id === "string") packetById.set(finding.finding_id, finding);
  }
  const matrixRows = Array.isArray(matrix?.rows) ? matrix.rows : [];
  const matrixById = new Map();
  for (const row of matrixRows) {
    if (row && typeof row.finding_id === "string") matrixById.set(row.finding_id, row);
  }

  return {
    rootDir,
    readText,
    readJson,
    sha,
    matrix,
    matrixRows,
    matrixById,
    matrixSha: sha(MATRIX_RELATIVE_PATH),
    matrixSchema: matrix?.schema ?? null,
    packet,
    packetById,
    packetFindings,
    sourceReviewText: readText(SOURCE_REVIEW_RELATIVE_PATH),
    sourceReviewSha: sha(SOURCE_REVIEW_RELATIVE_PATH),
    reviewedGitRevision: matrix?.review_case?.reviewed_git_revision ?? null,
    sourceContentSha256: normalizeSha(matrix?.review_case?.source_content_sha256),
    humanDispositionEventCount: matrix?.review_case?.human_disposition_event_count ?? null,
    eventsDirectoryPresent:
      typeof matrix?.review_case?.events_directory_present === "boolean"
        ? matrix.review_case.events_directory_present
        : existsSync(path.join(rootDir, PACKET_EVENTS_DIR_RELATIVE_PATH)),
    matrixFindingsOpen: matrix?.review_case?.findings_open ?? null,
  };
}

// ---------------------------------------------------------------------------
// report construction
// ---------------------------------------------------------------------------

function groupIdForConcernClass(concernClass) {
  const def = GROUP_DEFS.find((group) => group.concern_class === concernClass);
  return def ? def.group_id : null;
}

export function buildCards(ctx) {
  return FINDING_IDS.map((id) => {
    const row = ctx.matrixById.get(id) ?? null;
    const finding = ctx.packetById.get(id) ?? null;
    const proposal = DISPOSITION_PROPOSALS[id] ?? { disposition: null, basis: null };
    const group = groupIdForConcernClass(finding?.concern_class ?? null);
    const classMatch = row?.class_match === true;
    const card = {
      finding_id: id,
      summary: finding?.summary ?? null,
      concern_class: finding?.concern_class ?? null,
      group,
      source: {
        packet_id: ctx.packet?.packet_id ?? null,
        source_path: SOURCE_REVIEW_RELATIVE_PATH,
        reviewed_git_revision: ctx.reviewedGitRevision,
        content_sha256: ctx.sourceContentSha256,
      },
      proof_class: row?.required_proof_class ?? null,
      tested_source_revision: ctx.matrixSha,
      evidence_class: classMatch ? row?.required_proof_class ?? null : "docs",
      check_outcome: row?.machine_verdict ?? null,
      mismatch_reason_code: row?.mismatch_reason_code ?? null,
      residual_scope: row?.residual_scope ?? null,
      non_claims: Array.isArray(row?.non_claims) ? [...row.non_claims] : [],
      proposed_disposition: proposal.disposition,
      proposed_disposition_basis: proposal.basis,
      alternatives: ALTERNATIVES.map((alternative) => ({ ...alternative })),
      recommendation: { advisory: true, is_consent: false },
      preselected: false,
      selected: false,
      human_answer: null,
      session_question:
        `${id}: ${finding?.summary ?? "unknown finding"}. Which disposition should the owner record? ` +
        `Advisory recommendation: ${proposal.disposition}. Alternatives: change, defer, stop_session.`,
    };
    if (row?.deferral_reference !== undefined) {
      card.deferral_reference = row.deferral_reference;
      card.deferral_treated_as_proof = row.deferral_treated_as_proof === true;
    }
    if (row?.owner_status !== undefined) card.owner_status = row.owner_status;
    if (id === "RC28-F18") {
      card.adoption_evidence_status = "bounded_adoption_evidence_present";
      card.auto_close = false;
      card.criterion_id = F18_CRITERION_ID;
      card.adoption_refs = F18_ADOPTION_REFS.map((ref) => ({
        ...ref,
        sha256: ctx.sha(ref.path),
      }));
      card.independent_evaluation_status = "pending";
      card.ledger_disposition_status = "pending";
    }
    return card;
  });
}

function buildGrouping(cards) {
  return GROUP_DEFS.map((def) => {
    const findingIds = cards
      .filter((card) => card.group === def.group_id)
      .map((card) => card.finding_id);
    return {
      group_id: def.group_id,
      concern_class: def.concern_class,
      label_ru: def.label_ru,
      finding_ids: findingIds,
      count: findingIds.length,
    };
  });
}

function buildSummary(cards, grouping) {
  const dispositionCounts = {};
  const outcomeCounts = {};
  for (const card of cards) {
    dispositionCounts[card.proposed_disposition] =
      (dispositionCounts[card.proposed_disposition] ?? 0) + 1;
    outcomeCounts[card.check_outcome] = (outcomeCounts[card.check_outcome] ?? 0) + 1;
  }
  const findingsPerGroup = {};
  for (const group of grouping) findingsPerGroup[group.group_id] = group.count;
  return {
    card_count: cards.length,
    group_count: grouping.length,
    findings_per_group: findingsPerGroup,
    proposed_disposition_counts: dispositionCounts,
    check_outcome_counts: outcomeCounts,
    evidence_class_values: [...new Set(cards.map((card) => card.evidence_class))].sort(),
    alternatives_minimum: ALTERNATIVE_IDS,
    advisory_recommendation_count: cards.filter(
      (card) => card.recommendation?.advisory === true && card.recommendation?.is_consent === false,
    ).length,
    preselected_count: cards.filter((card) => card.preselected === true).length,
    selected_count: cards.filter((card) => card.selected === true).length,
    human_answer_count: cards.filter((card) => card.human_answer !== null).length,
    status_effect_values: ["unchanged"],
  };
}

export function buildReport(ctx) {
  const cards = buildCards(ctx);
  const grouping = buildGrouping(cards);
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
    review_case: {
      packet_id: ctx.packet?.packet_id ?? null,
      packet_path: PACKET_RELATIVE_PATH,
      packet_file_sha256: ctx.sha(PACKET_RELATIVE_PATH),
      packet_authoritative: ctx.packet?.authoritative === true,
      packet_authority_required: ctx.packet?.authority_required === true,
      source_path: SOURCE_REVIEW_RELATIVE_PATH,
      source_content_sha256: ctx.sourceReviewSha,
      reviewed_git_revision: ctx.reviewedGitRevision,
      findings_total: ctx.packetFindings.length,
      findings_open: ctx.matrixFindingsOpen,
      human_disposition_event_count: ctx.humanDispositionEventCount,
      events_directory_present: ctx.eventsDirectoryPresent,
      actor_bound_path_available: false,
      actor_bound_scope: "record_human_disposition",
    },
    matrix_binding: {
      path: MATRIX_RELATIVE_PATH,
      sha256: ctx.matrixSha,
      schema: ctx.matrixSchema,
      finding_count: ctx.matrixRows.length,
    },
    tested_source_revision_model: {
      kind: "m210-s04-finding-evidence-matrix content sha256",
      path: MATRIX_RELATIVE_PATH,
      sha256: ctx.matrixSha,
      note: "the cards are derived from the T02 evidence matrix; the live matrix digest is the tested source revision on every card, so matrix drift changes every card revision and fails --check",
    },
    vocabularies: {
      proof_class: PROOF_CLASSES,
      evidence_class: PROOF_CLASSES,
      check_outcome: CHECK_OUTCOMES,
      proposed_disposition: RC28_DISPOSITIONS,
      alternatives: ALTERNATIVE_IDS,
    },
    recommendation_model: {
      advisory: true,
      is_consent: false,
      preselected: false,
      blanket_confirmation_forbidden: true,
      read_back_required_after_each_answer: true,
      drift_cancels_proposal: true,
      submission_channel_used: "none",
      actor_bound_path_available: false,
    },
    session_rules: SESSION_RULES,
    grouping,
    cards,
    summary: buildSummary(cards, grouping),
    presentation: {
      path: PRESENTATION_RELATIVE_PATH,
      group_count: grouping.length,
      finding_references_per_finding: 1,
      sections: PRESENTATION_SECTIONS,
      language: "ru",
    },
    boundary: {
      review_case_events_written: false,
      record_human_disposition_called: false,
      dispositions_recorded: 0,
      options_selected: 0,
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
// rendering
// ---------------------------------------------------------------------------

export function renderCardsText(report) {
  return `${JSON.stringify(report, null, 2)}\n`;
}

function mdCell(value) {
  return String(value ?? "")
    .replace(/\|/g, "\\|")
    .replace(/\r?\n/g, " ")
    .trim();
}

export function renderPresentation(report) {
  const cards = Array.isArray(report?.cards) ? report.cards : [];
  const grouping = Array.isArray(report?.grouping) ? report.grouping : [];
  const byId = new Map(cards.map((card) => [card.finding_id, card]));
  const lines = [];

  lines.push("# RC28: презентация карточек ревью (M210/S04/T03)");
  lines.push("");
  lines.push("## Что это");
  lines.push("");
  lines.push(
    "Производный документ для человека, собранный из `prd/architecture/m210-s04-rc28-review-cards.json`,",
  );
  lines.push(
    "который в свою очередь собран из матрицы доказательств `prd/architecture/m210-s04-finding-evidence-matrix.json`.",
  );
  lines.push("");
  lines.push(
    `Ревью-пакет: \`${report?.review_case?.packet_id ?? ""}\`; источник \`${report?.review_case?.source_path ?? ""}\`;`,
  );
  lines.push(`проверенная ревизия \`${report?.review_case?.reviewed_git_revision ?? ""}\`.`);
  lines.push(
    `Одна карточка на находку, всего ${cards.length}; ни одна опция не предустановлена (preselected=false, selected=false, human_answer=null).`,
  );
  lines.push("");
  lines.push(
    "Ни один ответ не фиксируется этим документом: он показывает источник, ревизию, результат проверки, остаточный объём, non-claims, рекомендацию и альтернативы до любого выбора.",
  );
  lines.push("");
  lines.push("## Группы");
  lines.push("");
  lines.push(
    "Группировка нужна только для чтения. Она не превращает одно общее подтверждение в несколько решений: каждый ответ даётся отдельно по каждой находке.",
  );
  lines.push("");

  for (const group of grouping) {
    lines.push(`### Группа: ${group.label_ru} (${group.count})`);
    lines.push("");
    lines.push(
      "| finding_id | source | revision | proof class | check outcome | residual | non-claims | recommended outcome | alternatives |",
    );
    lines.push("|---|---|---|---|---|---|---|---|---|");
    for (const findingId of group.finding_ids) {
      const card = byId.get(findingId);
      if (!card) continue;
      const source = `${card.source.packet_id}; ${card.source.source_path}`;
      const proof =
        card.evidence_class === card.proof_class
          ? card.proof_class
          : `${card.proof_class} (evidence: ${card.evidence_class})`;
      const nonClaims = (card.non_claims ?? []).join("; ");
      const alternatives = (card.alternatives ?? []).map((alt) => alt.id).join(", ");
      lines.push(
        `| ${mdCell(findingId)} | ${mdCell(source)} | ${mdCell(card.source.reviewed_git_revision)} | ${mdCell(proof)} | ${mdCell(card.check_outcome)} | ${mdCell(card.residual_scope)} | ${mdCell(nonClaims)} | ${mdCell(`${card.proposed_disposition} (advisory)`)} | ${mdCell(alternatives)} |`,
      );
    }
    lines.push("");
  }

  lines.push("## Правила сессии");
  lines.push("");
  for (const rule of SESSION_RULES) lines.push(`- ${rule}`);
  lines.push("");
  lines.push("## Non-claims");
  lines.push("");
  for (const claim of NON_CLAIMS) lines.push(`- ${claim}`);
  lines.push("");

  return `${lines.join("\n")}\n`;
}

// ---------------------------------------------------------------------------
// validation
// ---------------------------------------------------------------------------

export function validateCards(report, ctx, options = {}) {
  const codes = [];
  const add = (code, detail) => codes.push({ code, detail });
  const jsonText = typeof options.jsonText === "string" ? options.jsonText : renderCardsText(report);
  const presentationText =
    typeof options.presentationText === "string"
      ? options.presentationText
      : renderPresentation(report);

  if (/[^\u0000-\u007f]/.test(jsonText)) {
    add("non_ascii_artifact", "the rendered cards JSON carries a non-ASCII code point");
  }
  for (const marker of RAW_TEXT_MARKERS) {
    if (jsonText.includes(marker)) {
      add("raw_text_leak", `the rendered cards JSON carries the raw-text marker ${JSON.stringify(marker)}`);
    }
  }

  const cards = Array.isArray(report?.cards) ? report.cards : [];
  if (cards.length !== FINDING_IDS.length) {
    add("card_count_incomplete", `cards=${cards.length} expected=${FINDING_IDS.length}`);
  }
  if (report?.summary?.card_count !== cards.length) {
    add("card_count_incomplete", `summary.card_count=${report?.summary?.card_count} cards=${cards.length}`);
  }
  if (report?.matrix_binding?.finding_count !== FINDING_IDS.length) {
    add("card_count_incomplete", `matrix_binding.finding_count=${report?.matrix_binding?.finding_count}`);
  }
  if (report?.review_case?.findings_total !== FINDING_IDS.length) {
    add("card_count_incomplete", `review_case.findings_total=${report?.review_case?.findings_total}`);
  }

  const byId = new Map();
  for (const card of cards) {
    const id = card?.finding_id;
    if (typeof id !== "string" || !FINDING_IDS.includes(id)) {
      add("card_count_incomplete", `unknown finding_id ${JSON.stringify(id)}`);
      continue;
    }
    if (byId.has(id)) {
      add("card_count_incomplete", `duplicate card ${id}`);
      continue;
    }
    byId.set(id, card);
  }
  for (const id of FINDING_IDS) {
    if (!byId.has(id)) add("card_count_incomplete", `missing card ${id}`);
  }
  if ((report?.grouping ?? []).length !== GROUP_DEFS.length) {
    add("card_count_incomplete", `grouping=${(report?.grouping ?? []).length} expected=${GROUP_DEFS.length}`);
  }
  const groupedIds = [];
  for (const group of Array.isArray(report?.grouping) ? report.grouping : []) {
    if (typeof group?.group_id !== "string" || !GROUP_DEFS.some((d) => d.group_id === group.group_id)) {
      add("card_count_incomplete", `unknown group ${JSON.stringify(group?.group_id)}`);
    }
    if (group?.count !== (Array.isArray(group?.finding_ids) ? group.finding_ids.length : -1)) {
      add("card_count_incomplete", `group ${group?.group_id} count disagrees with finding_ids`);
    }
    for (const id of Array.isArray(group?.finding_ids) ? group.finding_ids : []) {
      groupedIds.push(id);
      const card = byId.get(id);
      if (!card) add("card_count_incomplete", `group ${group?.group_id} names missing card ${id}`);
      else if (card.group !== group.group_id) {
        add("card_count_incomplete", `card ${id} group=${card.group} but grouped under ${group.group_id}`);
      }
    }
  }
  for (const id of FINDING_IDS) {
    if (!groupedIds.includes(id)) add("card_count_incomplete", `card ${id} is not in any group`);
  }

  const liveSourceSha = ctx.sha(SOURCE_REVIEW_RELATIVE_PATH);
  const liveMatrixSha = ctx.sha(MATRIX_RELATIVE_PATH);
  if (report?.matrix_binding?.sha256 !== liveMatrixSha) {
    add("card_count_incomplete", "matrix_binding.sha256 disagrees with the live matrix");
  }

  for (const id of FINDING_IDS) {
    const card = byId.get(id);
    if (!card) continue;
    const row = ctx.matrixById.get(id) ?? null;

    if (typeof card.summary !== "string" || card.summary.length === 0) {
      add("card_count_incomplete", `${id} summary missing`);
    }
    if (typeof card.concern_class !== "string" || card.concern_class.length === 0) {
      add("card_count_incomplete", `${id} concern_class missing`);
    }
    if (typeof card.session_question !== "string" || card.session_question.length === 0) {
      add("card_count_incomplete", `${id} session_question missing`);
    }

    const source = card.source;
    const sourceOk =
      source &&
      typeof source === "object" &&
      source.packet_id === PACKET_ID &&
      source.source_path === SOURCE_REVIEW_RELATIVE_PATH &&
      /^[0-9a-f]{40}$/.test(String(source.reviewed_git_revision ?? "")) &&
      normalizeSha(source.content_sha256) === liveSourceSha &&
      source.reviewed_git_revision === ctx.reviewedGitRevision;
    if (!sourceOk) {
      add("card_source_missing", `${id} source binding is incomplete or disagrees with the live review document`);
    }

    if (typeof card.tested_source_revision !== "string" || card.tested_source_revision !== liveMatrixSha) {
      add("card_proof_class_missing", `${id} tested_source_revision disagrees with the live matrix digest`);
    }

    if (!PROOF_CLASSES.includes(card.proof_class)) {
      add("card_proof_class_missing", `${id} proof_class=${JSON.stringify(card.proof_class)}`);
    } else if (row && card.proof_class !== row.required_proof_class) {
      add("card_proof_class_missing", `${id} proof_class=${card.proof_class} but matrix=${row.required_proof_class}`);
    }
    const expectedEvidenceClass = row?.class_match === true ? row?.required_proof_class : "docs";
    if (card.evidence_class !== expectedEvidenceClass || !PROOF_CLASSES.includes(card.evidence_class)) {
      add("card_proof_class_missing", `${id} evidence_class=${JSON.stringify(card.evidence_class)}`);
    }
    if (row && (card.mismatch_reason_code ?? null) !== (row.mismatch_reason_code ?? null)) {
      add("card_proof_class_missing", `${id} mismatch_reason_code disagrees with the matrix`);
    }

    if (!CHECK_OUTCOMES.includes(card.check_outcome)) {
      add("card_outcome_missing", `${id} check_outcome=${JSON.stringify(card.check_outcome)}`);
    } else if (row && card.check_outcome !== row.machine_verdict) {
      add("card_outcome_missing", `${id} check_outcome=${card.check_outcome} but matrix=${row.machine_verdict}`);
    }
    if (!RC28_DISPOSITIONS.includes(card.proposed_disposition)) {
      add("card_outcome_missing", `${id} proposed_disposition=${JSON.stringify(card.proposed_disposition)}`);
    }
    if (card.deferral_reference === "D519" && card.deferral_treated_as_proof !== false) {
      add("d519_treated_as_proof", `${id} treats the D519 deferral as proof`);
    }
    const classMatch = row?.class_match === true;
    const verdict = card.check_outcome;
    if (card.proposed_disposition === "already_satisfied") {
      if (card.deferral_reference === "D519") {
        add("d519_treated_as_proof", `${id} proposes already_satisfied on a D519 deferral row`);
      } else if (!classMatch || verdict === "evidence_absent_residual_named" || verdict === "evidence_class_mismatch") {
        add("already_satisfied_unsupported", `${id} proposes already_satisfied without class-matched evidence`);
      }
    }
    if (verdict === "evidence_present_class_matched" && card.proposed_disposition !== "already_satisfied") {
      add("card_outcome_missing", `${id} is class-matched but proposes ${JSON.stringify(card.proposed_disposition)}`);
    }

    if (typeof card.residual_scope !== "string" || card.residual_scope.length === 0) {
      add("card_residual_missing", `${id} residual_scope is empty`);
    } else if (row && card.residual_scope !== row.residual_scope) {
      add("card_residual_missing", `${id} residual_scope disagrees with the matrix`);
    }
    if (!Array.isArray(card.non_claims) || card.non_claims.length === 0) {
      add("card_non_claims_missing", `${id} non_claims is empty`);
    } else if (row && JSON.stringify(card.non_claims) !== JSON.stringify(row.non_claims)) {
      add("card_non_claims_missing", `${id} non_claims disagree with the matrix`);
    }

    const alternatives = Array.isArray(card.alternatives) ? card.alternatives : [];
    for (const required of ALTERNATIVE_IDS) {
      if (!alternatives.some((alt) => alt?.id === required)) {
        add("card_alternatives_insufficient", `${id} misses alternative ${required}`);
      }
    }
    if (alternatives.length < ALTERNATIVE_IDS.length) {
      add("card_alternatives_insufficient", `${id} alternatives=${alternatives.length}`);
    }

    if (card.recommendation?.advisory !== true || card.recommendation?.is_consent !== false) {
      add("recommendation_as_consent", `${id} recommendation is not advisory non-consent`);
    }
    if (card.preselected !== false || card.selected !== false || card.human_answer !== null) {
      add("card_preselected", `${id} preselected/selected/human_answer is not false/false/null`);
    }

    if (id === "RC28-F18") {
      if (card.auto_close !== false) {
        add("f18_auto_close", `RC28-F18 auto_close=${JSON.stringify(card.auto_close)}`);
      }
      if (card.adoption_evidence_status !== "bounded_adoption_evidence_present") {
        add("f18_auto_close", `RC28-F18 adoption_evidence_status=${JSON.stringify(card.adoption_evidence_status)}`);
      }
      if (card.human_answer !== null || card.selected !== false) {
        add("f18_auto_close", "RC28-F18 carries a human answer or a selection");
      }
      if (card.criterion_id !== F18_CRITERION_ID) {
        add("f18_auto_close", `RC28-F18 criterion_id=${JSON.stringify(card.criterion_id)}`);
      }
      const refs = Array.isArray(card.adoption_refs) ? card.adoption_refs : [];
      for (const required of F18_ADOPTION_REFS) {
        if (!refs.some((ref) => ref?.path === required.path)) {
          add("f18_auto_close", `RC28-F18 misses adoption ref ${required.path}`);
        }
      }
      for (const ref of refs) {
        const live = ctx.sha(ref?.path);
        if (live === null || normalizeSha(ref?.sha256) !== live) {
          add("f18_auto_close", `RC28-F18 adoption ref ${ref?.path} digest mismatch`);
        }
      }
      if (typeof row?.residual_scope === "string" && !row.residual_scope.includes(F18_CRITERION_ID)) {
        add("f18_auto_close", "the matrix residual scope does not carry the F18 criterion id");
      }
    }

    if (id === "RC28-F13") {
      if (card.owner_status !== "deferred-explicit") {
        add("f13_missing_answer_misread", `RC28-F13 owner_status=${JSON.stringify(card.owner_status)}`);
      }
      if (card.human_answer !== null) {
        add("f13_missing_answer_misread", "RC28-F13 carries a human answer for an explicit owner defer");
      }
    }
  }

  if ((report?.summary?.preselected_count ?? -1) !== 0) {
    add("card_preselected", `summary.preselected_count=${report?.summary?.preselected_count}`);
  }
  if ((report?.summary?.selected_count ?? -1) !== 0) {
    add("card_preselected", `summary.selected_count=${report?.summary?.selected_count}`);
  }
  if ((report?.summary?.human_answer_count ?? -1) !== 0) {
    add("card_preselected", `summary.human_answer_count=${report?.summary?.human_answer_count}`);
  }

  if (report?.recommendation_model?.advisory !== true || report?.recommendation_model?.is_consent !== false) {
    add("recommendation_as_consent", "recommendation_model is not advisory non-consent");
  }
  if (report?.recommendation_model?.preselected !== false) {
    add("card_preselected", "recommendation_model.preselected is not false");
  }

  // Each finding must be presented exactly once as its own card row. Mentions
  // inside residual scope or non-claims prose are cross-references inherited
  // from the matrix, not duplicate cards, so only row-leading occurrences count.
  const presentationLines = presentationText.split("\n");
  for (const id of FINDING_IDS) {
    const rowPrefix = `| ${id} |`;
    const rows = presentationLines.filter((line) => line.startsWith(rowPrefix)).length;
    if (rows === 0) add("presentation_finding_missing", `presentation has no card row for ${id}`);
    else if (rows > 1) {
      add("presentation_finding_duplicated", `presentation has ${rows} card rows for ${id}`);
    }
  }

  if (report?.boundary?.options_selected !== 0 || report?.boundary?.dispositions_recorded !== 0) {
    add("card_preselected", "boundary claims a selected option or a recorded disposition");
  }
  if (report?.boundary?.review_case_events_written !== false) {
    add("d519_treated_as_proof", "boundary claims a Review Case event was written");
  }

  return codes;
}

export function renderAll(rootDir = REPO_ROOT) {
  const ctx = loadCardsContext(rootDir);
  const report = buildReport(ctx);
  const cardsText = renderCardsText(report);
  const presentationText = renderPresentation(report);
  const codes = validateCards(report, ctx, { jsonText: cardsText, presentationText });
  return { report, cardsText, presentationText, codes, ctx };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function readCommitted(filePath) {
  return existsSync(filePath) ? readFileSync(filePath, "utf8") : null;
}

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
    rendered = renderAll(rootDir);
  } catch (error) {
    stderr.push(`render failed: ${String(error?.message || error)}`);
    return { mode, exitCode: 1, stdout, stderr, wrote: false };
  }

  if (rendered.codes.length > 0) {
    for (const entry of rendered.codes) stderr.push(`${entry.code}: ${entry.detail}`);
    return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report };
  }

  if (mode === "print") {
    stdout.push(rendered.cardsText.replace(/\n$/, ""));
    stderr.push(PRINT_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report };
  }

  if (mode === "check") {
    const committedCards =
      typeof options.committedCardsText === "string"
        ? options.committedCardsText
        : readCommitted(path.join(rootDir, CARDS_RELATIVE_PATH));
    const committedPresentation =
      typeof options.committedPresentationText === "string"
        ? options.committedPresentationText
        : readCommitted(path.join(rootDir, PRESENTATION_RELATIVE_PATH));
    if (committedCards === null || committedCards !== rendered.cardsText) {
      stderr.push(
        `check_not_byte_identical: committed cards ${committedCards === null ? "are absent" : "differ from the rendered cards"}`,
      );
      return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report };
    }
    if (committedPresentation === null || committedPresentation !== rendered.presentationText) {
      stderr.push(
        `check_not_byte_identical: committed presentation ${committedPresentation === null ? "is absent" : "differs from the rendered presentation"}`,
      );
      return { mode, exitCode: 1, stdout, stderr, wrote: false, report: rendered.report };
    }
    stdout.push(CHECK_OK_MARKER);
    return { mode, exitCode: 0, stdout, stderr, wrote: false, report: rendered.report };
  }

  if (!options.dryRun) {
    writeFileSync(path.join(rootDir, CARDS_RELATIVE_PATH), rendered.cardsText);
    writeFileSync(path.join(rootDir, PRESENTATION_RELATIVE_PATH), rendered.presentationText);
  }
  stdout.push(WRITTEN_MARKER);
  return { mode, exitCode: 0, stdout, stderr, wrote: !options.dryRun, report: rendered.report };
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
