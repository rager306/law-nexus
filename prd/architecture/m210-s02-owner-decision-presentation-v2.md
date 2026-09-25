# M210 S02 owner decision presentation v2 (design-only)

Supersedes `m210-s02-owner-decision-presentation.md` (v1) for any future
re-presentation. Companion to
`prd/architecture/m210-s02-owner-decision-packet-v2.json`
(`law-nexus/m210-s02-owner-decision-packet/v2`). Correction lineage:
`prd/architecture/m210-s02-packet-corrections-v2.md` (RC28-F19 policy; v1
stays byte-identical and hash-bound in the adoption checkpoint).

This presentation adopts no normative semantics, mints no Rust type,
promotes no requirement, changes no section 3 row and writes no Review
Case event. The machine-checked surface is the packet JSON, not this file.

## What changed since v1 (corrections only)

- Candidate verdicts and provenance-link verdicts are now declared as two
  separate domains. A verified anchor resolves a link; it never raises the
  legal status of a classification. A verified anchor and a legal Unknown
  coexist on one candidate.
- Absence semantics are explicit for every variant: absence of a record or
  candidate yields Unknown; it never means that no norm exists.
- The C recommendation rationale is restated: smallest new section 3
  decision surface plus abstention-first staging. C is not claimed to be
  the only safe representation; fail-closed behaviour is a property of the
  creation, verification, transformation and use contracts.
- The existing `ln-applicability` NormRule spine is documented as a
  structural prototype with four migration-blocking algebra defaults
  (missing exception or defeater fact counts inactive; first-match fact
  lookup without duplicate rejection; an exception carves conditions
  without target addressing). Variant B's reuse advantage is qualified.
- The S01 corpus probes are stated as coverage labels over [0,4096) byte
  ranges; the dispute-card anchors are review, glossary and gap-register
  boundaries. The decision basis is structure and fail-closed boundaries,
  not demonstrated extraction of concrete norms.
- The adoption conduit is specified: authenticated subjective-UAT
  criterion id; receipt bound to the shown revision; separated acceptance
  roles for format, codebook and formalization. A bare UUID is an
  identifier, not proof that an authorized human decided.

Unchanged: the question set, the five options and their consequences, the
answer conduit requirements, the read-back discipline, and the advisory
nature of every recommendation.

## Scope

In scope for the S02 decision: choose one bounded normative IR
alternative, or reject all three, or defer. In scope for the separate F13
decision: adopt a source-level amendment operation-candidate contract, or
keep amendment operations deferred. Out of scope: any adoption of legal
semantics, any runtime surface, any section 3 term promotion, any
requirement promotion, any Review Case event and any implementation
authorization.

## Source revision and evidence class

The source revision shown to the owner is copied from the T01 rebind
report (`prd/architecture/m210-s02-rebind-report.json`):

    source_revision: sha256:618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7

Every tracked input behind this presentation was re-bound before it was
shown (18 inputs, all verdict match, 8 corpus anchors). The stored
revision is a rebind-time snapshot; the real stale gate is the per-input
live sha256, which `node scripts/m210_s02_rebind.mjs --check` re-derives
on every run. Re-run it immediately before the owner answers.

Evidence class by claim class: alternatives and consequences are
inert-artifact; dispute cards, negative examples and corpus anchors are
source-bound-span (a span is an anchor, not a reading); runtime behaviour
is runtime-absent: no normative IR, rule graph or applicability evaluator
exists or is promised.

## Limitations and non-claims

- corpus anchors are verified only when the licensed corpus resolves
  locally; corpus-absent mode marks every anchor `verified: false`;
- the stored source revision is a snapshot; the stale gate is the live
  per-input sha256;
- two of the eight dispute cards are `conflicted`
  (`competence`, `temporal_qualification`) and six are `unresolved`; no
  card carries a `resolved` verdict; a card is a boundary, not a reading;
- the eight corpus probes are coverage labels over [0,4096) byte ranges;
  they do not demonstrate that a family label was extracted from a real
  norm fragment;
- the `definition` family has no owning section 3 row and the
  `competence` ceiling is only `proposed`;
- no human-labelled gold set exists here and none is implied;
- no runtime surface exists or is promised;
- the recommendations are advisory and are not the owner's consent.

Non-claims: not an adoption of normative semantics; non-authoritative;
the recommendation is not consent; the F13 question is a separate
decision; an interactive answer is not an ADR, not a Review Case event
and not an authorization to implement; section 3 stays unchanged; a
verified provenance anchor never raises the legal status of a
classification; absence of a record or candidate never means that no norm
exists.

## Alternatives and consequences for S03

All three variants declare the same N to M provenance cardinality
(`provision_to_rule` min 0, unbounded max; `rule_to_provision` min 1,
unbounded max). None proves legal correctness.

| Variant | Shape | Collapses | Consequence for S03 | Main collapse risk |
|---|---|---|---|---|
| A `family_typed_record_ir` | one addressable record kind per family (eight kinds) plus shared envelope and a separate link record | none | mint and validate eight record kinds plus envelope and link record; define Condition, Exception and Defeater in section 3 first | a missing duty filed under the prohibition kind; a definition and an obligation record sharing one anchor |
| B `single_facet_slot_rule_record` | one NormRule-like record whose family content lives in typed facets | definition (as an independently addressable record) | extend the NormRule spine with deontic operator, definition scope, competence source; define all six normative section 3 rows | an absent deontic facet defaulting to permission or prohibition |
| C `abstention_first_candidates_only` | no composed rule; source-bound candidates with a family classification and an Unknown or Conflict verdict | none | build only candidate emission and the fail-closed Unknown or Conflict verdicts; composition stays deferred | a classified candidate read as a composed rule; an absent candidate read as a negative finding |
| reject all three | nothing adopted now; S03 has no adopted scope | n/a | a later decision must reopen the question with a fresh rebind | n/a |
| defer | decision moves to a later slice; packet stays proposed | n/a | re-presentation with a fresh rebind | n/a |

Absence semantics (all variants): absence of a record or candidate yields
Unknown for that provision; it is never the statement that no norm exists.

## Relation to the existing NormRule spine

The `ln-applicability` spine (`crates/ln-applicability/src/domain.rs`)
carries `id`, `revision`, `conditions`, `exceptions`, `defeaters`,
`temporal_scope` as structural design types. Section 3 keeps NormRule and
relatives deferred-undefined. Verified prototype caveats: its evaluation
algebra treats a missing exception or defeater fact as inactive, resolves
case facts by first match without rejecting duplicates, and lets a
satisfied exception flip an overall condition failure to Satisfied
without addressing which condition or rule is carved. These defaults are
fenced off from the product today, but any variant that reuses the spine
must first adopt an algebra revision contract.

| Variant | Relation to the spine |
|---|---|
| A | reuses none of it; mints eight new record kinds |
| B | closest to it; extends the spine with fields that do not exist yet; requires all six deferred section 3 rows |
| C | does not touch the spine at all; no new normative term is minted |

## Dispute cards, probes and negative examples

One dispute card per family: 8 cards, 2 `conflicted`
(`competence`, `temporal_qualification`), 6 `unresolved`;
`resolved` refused by construction; every card sets
`requires_human_source_review: true` and `adopted: false`. The eight
corpus probes are coverage labels over [0,4096) byte ranges; they bound
coverage, they do not demonstrate extraction. Negative examples mark the
boundaries: `absence_of_obligation_is_not_prohibition`;
`lack_of_evidence_is_not_falsity`.

## Proof ceiling

Proves: one owner question with a complete five-option set; a separate F13
question; every presented claim bound to a rebound tracked input with a
live sha256; documented fail-closed codes emitted by the packet contract
on mutation; no preselection.

Does not prove: legal semantics of any alternative; reading correctness;
human gold; runtime fitness; owner consent.

## Recommendation (advisory only, not consent)

IR recommendation: **option C, `abstention_first_candidates_only`**.
Rationale: C defines no new section 3 term and composes no rule, so it is
the variant with the smallest new semantic decision surface and an
abstention-first staging; it is not the only safe representation, and
fail-closed behaviour is a property of the creation, verification,
transformation and use contracts rather than of representation arity.
Evidence: `m210-s01-ir-alternatives.json`,
`m210-s01-normative-family-register.json`,
`doc/review/review-28-10-09-2026.md` (RC28-F18),
`m210-s02-rebind-report.json`.

F13 recommendation: **keep amendment operations deferred** in this
decision, and schedule source-level operation-candidate grammar as
separate near-term work against the design-only operation registry. This
is advisory; F13 stays at **HOLD** unless answered separately.

## The exact questions

IR question id: `m210-s02-ir-question` (five options; nothing
preselected). F13 question id: `m210-s02-f13-question` (separate; an IR
answer never determines it).

## Read-back template

After the owner answers, the following is shown back verbatim before
anything is recorded as a direction:

    ir_question_id:        m210-s02-ir-question
    ir_selected_option:    the option id exactly as answered, or null
    ir_verbatim_response:  the answer text exactly as given, unedited
    f13_question_id:       m210-s02-f13-question
    f13_selected_option:   the option id exactly as answered, or null
    f13_verbatim_response: the answer text exactly as given, unedited
    f13_status:            hold when no separate F13 answer was given
    source_revision:       the revision this presentation was shown at
    presented_fields:      the field list below, as actually passed
    not_a_consent:         the recommendation is not consent and no option was preselected

Nothing is recorded as answered unless the interactive conduit returns a
real criterion, question and interaction reference. An absent or partial
answer is a sanctioned stop (`pending_human_decision`), not a failure and
not a pass.

## Interactive conduit fields

Passed to the authenticated interactive conduit (subjective-UAT
criterion id; receipt bound to the shown revision; no option
preselected; recommendation advisory):

| Field | Value |
|---|---|
| `criterionKey` | `m210-s02-ir-question` |
| `description` | Which bounded normative IR alternative should be adopted for the M210 bounded normative IR |
| `focusedPrompt` | The exact IR question above, with all five options and the note that no option is preselected |
| `recommendedDisposition` | `adopt abstention_first_candidates_only` (advisory only, not consent) |
| `recommendationRationale` | smallest new section 3 decision surface; abstention-first staging; not the only safe representation |
| `recommendationEvidence` | the four evidence refs listed under the recommendation section |
| `testedSourceRevision` | `sha256:618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7` |

The F13 field set is passed as a second, separate question
(`criterionKey: m210-s02-f13-question`); the two are never merged.
