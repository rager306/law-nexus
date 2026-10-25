# M210/S02 external analysis brief — the open normative-IR adoption question

Status: NON-AUTHORITATIVE working brief for an external analyst agent.
This file is not part of the S02 owner-decision packet, is not hash-bound in
`m210-s02-adoption-checkpoint.md`, adopts nothing, and authorizes nothing.
It only explains the open decision, its governance boundary, and where every
authoritative source lives, so an outside agent can study approaches without
re-deriving context.

Prepared: 2026-09-24. Head at time of writing: `f15612b` (pushed to origin).

---

## 1. TL;DR

The law-nexus product parses Russian legal texts and must, at some point,
represent normative statements (obligations, prohibitions, definitions, ...)
as addressable records. Before any of that is built, the human owner must
choose ONE of three representation designs (A/B/C), or reject all, or defer —
per RC28-F18 in `doc/review/review-28-10-09-2026.md`. The engineering side
(S01, S02) has prepared a fail-closed decision packet with source-bound
evidence; the decision itself is deliberately blocked on a real human answer,
because a chat answer by an agent does not count as legal-semantics adoption.
The question this brief exposes for external study: **which representation
design should be adopted, and what should an external analysis say about the
trade-offs?**

## 2. Project context in one page

- Product: law-nexus — Rust-only runtime for processing Russian legal corpora
  (Consultant Plus XML exports, ~43,785 documents in
  `consru_export/consru_export/exports/`). Python exists only as repository
  control harness (`src/law_nexus_harness/`). Direction contract:
  `prd/ARCHITECTURE.md` (Active Direction Contract).
- Governance vocabulary lives in `prd/temporal-legal-model.md` section 3 —
  a closed glossary where the core normative terms (NormRule, Condition,
  LegalEffect, Exception, Defeater, ApplicabilitySelector) are deliberately
  **deferred-undefined**: nobody may use them in runtime until a human adopts
  their meaning. Pin: `a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6`.
- Review 28 (`doc/review/review-28-10-09-2026.md`) declared RC28 findings.
  Two matter here:
  - **RC28-F18** (line 86): normative semantics needs *separate adoption* —
    an explicit contract separating obligation/permission/prohibition,
    definitions, competence, conditions, exceptions, temporal qualification,
    with N:M provision-to-rule provenance; must distinguish "absence of
    obligation" from "prohibition" and "lack of evidence" from "falsity".
    Human legal acceptance required; parser cue fixes do not authorize it.
  - **RC28-F13** (line 66): amendment syntax (replace / new wording / insert /
    remove / repeal, nested target scope, quoted operands) is the missing
    bridge to the temporal compiler; owning contracts must be adopted first.
- Milestone M210-3afp79 "Separate adoption of normative semantics and bounded
  IR" has 4 slices:
  - **S01 (complete)**: produced the decision *inputs* — closed 8-family
    register, three IR alternatives with N:M provenance, source-bound dispute
    cards and negative examples. Committed `7909004..44c2f33`.
  - **S02 (complete)**: rebound all 18 S01 inputs to live sha256, presented
    the packet to the owner, recorded a *sanctioned pending stop* (no answer
    exists), ran a fail-closed governing-surface check, wrote the adoption
    checkpoint `not-adopted`, and froze the section 3 dictionary. Committed
    `91477ee..f15612b`.
  - **S03 (planned, not started)**: 5 tasks planned in
    `.gsd/phases/210-3afp79-bounded-ir/210-03-PLAN.md` — T01 is a source-bound
    **start gate** (`scripts/m210_s03_start_gate.mjs` +
    `prd/architecture/m210-s03-runtime-admission.md`) that re-validates the
    checkpoint and refuses runtime implementation while
    `admission: not-adopted`.
  - **S04**: not planned yet.

## 3. Plain-language glossary

- **Provision** — a specific clause/paragraph of a law (e.g. "абзац второй
  пункта 2 статьи 5").
- **Normative family** — what kind of norm a provision carries. The closed
  set of eight: `obligation`, `permission`, `prohibition`, `definition`,
  `competence`, `condition`, `exception`, `temporal_qualification`
  (`m210-s01-normative-family-register.json`).
- **IR (intermediate representation)** — the machine-readable "card" a norm is
  stored as, so later stages (applicability, temporal replay) can use it.
- **§3 deferred-undefined** — the project's rule that core legal terms stay
  *undefined by design* until a human adopts their contract. Code may carry
  structural types named like them, but they are design placeholders, not
  adopted legal semantics.
- **Fail-closed** — when evidence is missing or contradictory, the system must
  answer "Unknown/Conflict/unresolved", never guess.
- **Adoption** — the owner's recorded human decision that a representation is
  accepted as the project's normative semantics. Not derivable from tests,
  UAT, or agent chat text.

## 4. The core question, in plain language

The system reads a provision like:

> «Организация обязана подать уведомление в течение десяти дней»
> (an obligation) or «Запрещается ...» (a prohibition), or
> «под уведомлением понимается ...» (a definition).

S01 already extracts *candidates* with anchors (file + byte span + sha256).
The open question is: **into what shape do we store these candidates so later
stages can rely on them without silently inventing legal meaning?**

Three designs were specified (`m210-s01-ir-alternatives.json`), all sharing the
same N:M provenance contract (a provision may map to many norms; a norm must
have ≥1 provision anchor).

### Variant A — `family_typed_record_ir` (one record kind per family)

Eight record kinds + a shared envelope `{source_anchor, family, evidence_class,
verdict}` + a separate link record connecting provisions to records.

- Example: «обязана подать уведомление» → one `obligation` record; «под
  уведомлением понимается ...» → a separate `definition` record; both may
  anchor the same provision text, connected by link records.
- Strongest separation: family identity is a *type boundary*; a missing family
  is a missing record, never an empty field.
- Costs: largest new surface; must define §3 terms `Condition`, `Exception`,
  `Defeater` before any family payload can carry a guard or defeat; the
  existing code spine is not reused.
- Collapse risks: a classifier that prefers bans can file a *missing duty* as
  `prohibition`; a `definition` and an `obligation` record can share one
  provision and be read as one norm unless link records forbid it.
- Reuses none of the existing `NormRule` spine.

### Variant B — `single_facet_slot_rule_record` (one record, typed facets)

One NormRule-like record whose content lives in typed facets:
`deontic_operator`, `definition_scope`, `competence_source`,
`condition_guard`, `exception_defeater_list`, `temporal_qualification`.

- Example: the same provision → one record with facet
  `deontic_operator = "обязан"`.
- Closest to existing code: it *extends* the `ln-applicability` NormRule spine
  (RC11-F04a) — `crates/ln-applicability/src/domain.rs:270`:

  ```rust
  pub struct NormRule {
      id: NormRuleId,
      revision: NormRuleRevision,
      conditions: Vec<NormRuleCondition>,
      exceptions: Vec<Exception>,
      defeaters: Vec<Defeater>,
      temporal_scope: TemporalScope,
  }
  ```

  conditions map onto `condition_guard`, exceptions/defeaters onto
  `exception_defeater_list`, temporal scope onto `temporal_qualification`.
  The deontic operator, definition scope and competence source have **no
  existing field** — they would be new spine fields.
- Costs: **largest §3 surface** — requires defining all six deferred terms
  (`NormRule`, `Condition`, `LegalEffect`, `Exception`, `Defeater`,
  `ApplicabilitySelector`).
- Collapse risks: `definition` is *collapsed* by design into a facet, so a
  definitional norm is not independently addressable; an absent
  `deontic_operator` facet must never default to permission/prohibition, yet
  facet defaults are exactly where silent collapse hides
  (RC28-F18's "absence of obligation ≠ prohibition").

### Variant C — `abstention_first_candidates_only` (recommended, advisory)

No composed rule is emitted at all. Each source-bound candidate carries a
family classification, an anchor, and a verdict from `{Unknown, Conflict}`.
Composition, facet defaults, applicability — all deferred.

- Example: «обязана подать уведомление ...» → candidate
  `{family: obligation, anchor: path#span, verdict: resolved}`; a provision
  the parser cannot classify → `{verdict: Unknown}`; two contradicting anchors
  → `{verdict: Conflict}`.
- **Defines zero new §3 terms** and composes nothing — the only variant that
  stays entirely inside the deferred-undefined boundary.
- Costs: real work postponed — a later composition ADR must reopen §3 anyway;
  a classified candidate must never be read as a settled rule, and an absent
  candidate must never be read as "no norm exists"
  (`lack_of_evidence_is_not_falsity`).

### Non-variant options

- **reject_all**: nothing adopted; S03 has no scope; question reopens later
  with a fresh rebind (inputs re-hashed).
- **defer**: decision moves to a later slice; same fresh-rebind requirement.

## 5. The second, independent question — F13 (amendment syntax)

RC28-F13 (`doc/review/review-28-10-09-2026.md`, lines 66–70): amendments in
Russian laws are expressed by fixed operations — «изложить в редакции»
(replace), «дополнить» (insert), «заменить слово» (new wording), «признать
утратившим силу» (repeal), «исключить» (remove) — with nested target scope and
quoted operands. Local Pullenti prior art:
`sdk/Pullenti/Ner/Decree/DecreeChangeReferent.cs:16-57` (OWNER, KIND, CHILD,
VALUE, PARAM, LOCVALUE) and `DecreeAnalyzer.cs:1263-1440` (nested changes).

Question: adopt a **design-only operation-candidate contract** (an extracted
operation is a *candidate*, never an admitted `MicroOperation`,
`LegislativeEffect` or `InForce`; no automatic reinterpretation on missing
operands), or **keep deferred** (the temporal-compiler bridge stays missing;
the owning slice reopens F13 with a fresh rebind). Recommendation (advisory):
keep deferred — the owning surface is the amendment/temporal work, not this
packet. IR answer never determines F13; unanswered F13 stays **HOLD**.

## 6. Why this is blocked on a human (governance mechanics)

This is the part external agents most often get wrong, so precisely:

1. The machine-checked decision surface is
   `prd/architecture/m210-s02-owner-decision-packet.json`
   (`law-nexus/m210-s02-owner-decision-packet/v1`); the human-readable entry is
   `m210-s02-owner-decision-presentation.md`. Both are `authoritative: false`
   and `semantics_adopted: false`.
2. The answer slot `m210-s02-answer-record.json` is
   `pending_human_decision`, `answer_source: none`, both question slots
   unresolved, `conduit_available: false` (no interactive tool existed in the
   execute-task unit that wrote it). Fail-closed codes forbid
   `agent_selected_answer`, `answer_as_automatic_adoption`,
   `f13_inferred_from_ir`, `verbatim_field_hijack`, etc.
3. `m210-s02-adoption-checkpoint.md` records exactly one verdict line
   `**admission: not-adopted**` with `owner_admission_ref: none`,
   `interaction_ref: none`, `f13_status: hold`,
   `runtime_stop: remains active`, `review_case_events_written: 0`, and a
   **named resume condition**: a real interactive owner reference plus a
   separately verified governing surface. The dictionary delta
   (`m210-s02-dictionary-delta.json`) is `applied: false` and gated on
   `admission: granted`; section 3 stays byte-identical to pin `a8f7184d…`.
4. `m210-s02-governing-surface-check.json` found `governing_surface_absent`:
   no tracked surface carries human adoption of S01 IR semantics; the Review
   Case CLI (`src/law_nexus_harness/review_case/application.py`) exposes only
   register/validate/status/inventory — **no submit** — and trusts
   caller-supplied `actor_class`/`actor_id`, so it is not identity
   authentication; `actor_bound_path_available: false`.
5. The valid interactive reference is a **UUID or an authenticated
   subjective-UAT criterion id** (`210-03-PLAN.md` T01). The sanctioned
   interactive surface in a GSD session is the subjective-UAT pair
   (`gsd_prepare_milestone_subjective_uat` → present questions verbatim →
   owner answers in their own words → `gsd_answer_milestone_subjective_uat`
   records the answer verbatim, actor derived from the session), producing
   criterion/interaction ids the start gate can validate.
6. Consequence: an answer in chat, a test pass, UAT PASS, or an agent-written
   "HUMAN" event is **not** adoption. RC28-F18 also requires an ADR to record
   the adopted contract; S03 T01 (`m210-s03-start-gate.mjs` design:
   `admission_verdict=admission_absent`,
   `runtime_implementation_permitted=false`) re-checks all of this at S03
   start.

## 7. Evidence quality and known limitations

- Rebind report `m210-s02-rebind-report.json`: 18 inputs re-bound, all
  `match`; 8 corpus anchors `verified_true`; drift 0. Corpus-present mode
  (root `consru_export/consru_export/exports/`); corpus-absent mode would mark
  anchors `verified: false` with reason `corpus_absent` instead of carrying
  pins.
- The stored `source_revision sha256:618aaf12…` is a rebind-time snapshot;
  the real stale gate is per-input live sha256 re-derived by
  `node scripts/m210_s02_rebind.mjs --check` on every run.
- Dispute cards: exactly one per family (8), 2 `conflicted`
  (`competence`, `temporal_qualification`), 6 `unresolved`;
  `resolved` is refused by construction; all `requires_human_source_review:
  true`, `adopted: false` (`m210-s01-source-bound-examples.json`).
- Negative examples (system boundaries): `absence_of_obligation_is_not_
  prohibition`; `lack_of_evidence_is_not_falsity`.
- No human-labelled gold set exists anywhere in this chain (RC28-F15
  territory); nothing here claims human-gold accuracy.
- Reproduce with: `node scripts/m210_s02_slice_battery.mjs` →
  `M210_S02_BATTERY_OK checks=154 failed=0` (floor 138); regressions
  `m209_s04_slice_battery.mjs` (36/0) and `m210_s01_slice_battery.mjs` (50/0).

## 8. What S03 would do under each answer

Per `.gsd/phases/210-3afp79-bounded-ir/210-03-PLAN.md` (5 tasks, gated by
T01 start gate):

- **Adopt A**: mint/validate 8 record kinds + envelope + link record; first
  define §3 `Condition`, `Exception`, `Defeater`.
- **Adopt B**: extend the NormRule spine with `deontic_operator`,
  `definition_scope`, `competence_source`; define all six §3 rows; facet
  default policy is the first fail-closed runtime surface.
- **Adopt C**: build candidate emission + Unknown/Conflict verdicts only;
  §3 untouched; composition deferred to a later ADR.
- **reject/defer**: S03 runs the sanctioned-stop path (no runtime work;
  T04 "sanctioned stop + gated activation" task exists in the plan for
  exactly this case).

## 9. Open research questions for external analysis

1. **Representation theory**: how do established formalisms separate norm
   kinds — LegalRuleML (obligation/prehibition/permission with proper
   deontic operators and violation/reparations), ISO OASIS legalRuleML
   activations/fillers, Power/Intention ontologies? Does a type-per-family
   (A) or facet-per-family (B) mapping better preserve
   absence-vs-prohibition and definitional addressability?
2. **Facet default policy**: for B, what do mature systems do with an absent
   deontic operator? Is "Unknown facet" enforceable in practice, or do
   defaults creep in? What contract language prevents it?
3. **Abstention-first economics**: is C a practical staging (candidates now,
   composition later) or does it risk wasted work? What did the early M2xx
   chain work cost when composition was deferred?
4. **Provenance N:M**: audit the declared contract
   (`provision_to_rule` 0..N with unknown_policy; `rule_to_provision` 1..M
   with unresolved_policy; rules `absence_yields_unknown`,
   `unresolved_anchor_yields_unresolved`, `contradiction_yields_conflicted`,
   `cardinality_collapse_forbidden`) against real provisions: are 8 families
   exhaustive? Where does a single provision carry two norms of one family?
5. **F13 scope**: compare Pullenti DecreeChange model (OWNER/KIND/CHILD/VALUE)
   against Russian amendment grammar — are five operations
   (replace/new wording/insert/remove/repeal) sufficient with nested scope and
   quoted operands? What edge cases (repeal-of-amendment, operative-date
   clauses) must the owning contract name?
6. **Adoption UX**: is the UUID / authenticated-subjective-UAT-criterion
   reference model sound for proving "a human decided"? What would an
   external auditor need beyond criterion/interaction ids?

## 10. Source index (authoritative pointers)

Governance and direction:

- `prd/ARCHITECTURE.md` — Active Direction Contract (Rust-only, lifecycle tags).
- `prd/temporal-legal-model.md` §3 — closed glossary; deferred-undefined terms;
  pin `a8f7184d…`.
- `doc/adr/README.md` and ADR 0004–0027 (0004 covers the bounded program;
  0024 `doc/adr/0024-review-case-intake-and-disposition.md` — Review Case
  intake/disposition; no submit subcommand exists).
- `doc/review/review-28-10-09-2026.md` — RC28-F13 (line 66), RC28-F18
  (line 86), F15 (human gold), F14 (Pullenti not normative authority).
- `assessment/33-rc28-disposition-inventory.md` — minimal interactive review
  contract (`6ba987f`).

Decision artifacts (S01):

- `prd/architecture/m210-s01-normative-family-register.json` — closed 8-family
  set, negative distinctions.
- `prd/architecture/m210-s01-ir-alternatives.json` — variants A/B/C full
  specs: `representation_shape`, `separates`/`collapses`,
  `provenance_cardinality`, `what_it_cannot_prove`, `collapse_risks`,
  `required_new_adr_terms`, `compatibility_with_existing_vocab`,
  `cost_and_risk`, per-variant advisory recommendation.
- `prd/architecture/m210-s01-source-bound-examples.json` — 8 dispute cards +
  2 negative examples with byte spans.
- `prd/architecture/m210-s01-packet-index.json`, `m210-s01-decision-packet.md`.

Decision artifacts (S02):

- `prd/architecture/m210-s02-owner-decision-packet.json` — machine surface:
  `ir_question` (5 options), `f13_question`, `proof_ceiling`, non_claims.
- `prd/architecture/m210-s02-owner-decision-presentation.md` — human entry
  (250 lines; full tables cited above).
- `prd/architecture/m210-s02-answer-record.json` — pending stop with guard
  fields and fail-closed codes.
- `prd/architecture/m210-s02-adoption-checkpoint.md` — the not-adopted verdict
  and resume condition.
- `prd/architecture/m210-s02-dictionary-delta.json` — `applied:false`,
  gated on `admission: granted`.
- `prd/architecture/m210-s02-governing-surface-check.json` —
  `governing_surface_absent`, 8 candidates `adoption_present:false`.
- `prd/architecture/m210-s02-rebind-report.json` — 18 rebound inputs, 8 corpus
  anchors, drift 0.

Code:

- `crates/ln-applicability/src/domain.rs:270` — `NormRule` spine (RC11-F04a):
  fields cited in §4-B; `try_new` rejects empty conditions.
- `crates/ln-applicability/tests/norm_rule_ir_contract.rs`,
  `predicate_algebra_contract.rs` — existing spine contracts.
- `crates/ln-kb-ontology/src/registry_admission.rs` — registry admission
  pattern used by M209 (identity-pair resolution D548/D549).
- `src/law_nexus_harness/review_case/application.py` — Review Case CLI
  (register/validate/status/inventory only).
- Contract scripts: `scripts/m210_s02_rebind.mjs`,
  `scripts/m210_s02_slice_battery.mjs`, `scripts/m210_s02_*_contract.test.mjs`;
  planned `scripts/m210_s03_start_gate.mjs` (S03 T01 design).
- Plan: `.gsd/phases/210-3afp79-bounded-ir/210-03-PLAN.md` (S03 T01–T05),
  `210-02-ASSESSMENT.md` (UAT PASS 9/9 with non-claims), `210-ROADMAP.md`.

## 11. Corrections after external review (2026-09-24, same head f15612b)

Two external reviews were received and their factual claims were re-checked
against the repository. Corrections accepted into this brief:

1. **C example verdict fixed.** §4 Variant C example said
   `{verdict: resolved}`; C candidates carry verdicts from `{Unknown,
   Conflict}` only. The `resolved/unresolved/conflicted` domain belongs to
   **provenance link records**, not candidate classification. Four dimensions
   must stay separate: source-link resolution / classification hypothesis /
   legal verdict / permitted use. A verified anchor and a legal `Unknown`
   legitimately coexist on one candidate.
2. **S01 probes are coverage labels, not extraction proof.** The 8 corpus
   probes in `m210-s01-source-bound-examples.json` all use the byte range
   `[0,4096)` and the artifact itself states the family label is a coverage
   label; dispute-card anchors point to review/glossary/gap-register, not to
   corpus norm fragments. Earlier phrasing that S01 "already extracts
   candidates" overstated this.
3. **NormRule spine is a structural prototype, not a near-complete model.**
   Verified at `crates/ln-applicability/src/domain.rs`: `evaluate_exception`
   and `evaluate_defeater` treat `Some(false)` and `None` identically
   (missing fact = inactive, domain.rs:525–541); `CaseFactSet::get` returns
   the first match and `try_from_pairs` does not reject duplicate ids
   (domain.rs:482–488); `compose_norm_rule_predicates` lets a satisfied
   exception flip an overall condition failure to `Satisfied` without
   addressing which condition/rule it carves (domain.rs:547+). These are
   fenced off from the product by the capability-boundary tests today, but
   they are migration-blocking defaults for any future composed IR.
4. **Imprecise standard name.** §9 said "ISO OASIS legalRuleML
   activations/fillers"; the checkable name is **OASIS LegalRuleML Core 1.0**
   with specific sections. Weak-permission semantics do not license inferring
   permission from an absent prohibition in an incomplete base.
5. **Absence semantics (against a later PDF misreading):** variant A's own
   contract says absence of a family record yields `Unknown` — the absence of
   a record is absence of evidence, never the statement that no norm exists.
6. **`.gsd` plan path:** `.gsd/phases/210-3afp79-bounded-ir/210-03-PLAN.md`
   exists locally only (`.gsd` is a symlink outside the pushed tree); an
   external reader's 404 is expected, not a repository defect.

Not independently verified here (external literature claims accepted as
plausible, to be checked against primary sources before any ADR cites them):
Waltl et al. F1 figures; De Jure judge scores; NLLP 2023 metrics; DDL
extraction numbers; AI Act paper precision/accuracy; RusLawOD v3.1 corpus
figures and its `textIPS`/`taggedTextIPS` layer split; NORMA-O annotation
provenance model; LRMoo bibliographic status and version differences; the
Минтруд ч.2 ст.39 44-ФЗ multi-obligation example; Методические рекомендации
2021 п.49/64/102; NIST SP 800-63-4 distinction of identity proofing vs
authentication vs federation.

## 12. Non-claims of this brief

- This brief is not an adoption, not an ADR, not a Review Case event, not an
  authorization to implement.
- It does not claim any variant is legally correct; the packet proves only
  structure, anchors and fail-closed behaviour.
- It does not speak for the owner; the owner's answer does not exist yet
  (`pending_human_decision`).
- The recommendation (C; F13 defer) is advisory and belongs to the packet, not
  to the analyst.
