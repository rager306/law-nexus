# M210 S02 owner decision presentation (design-only)

Companion to `prd/architecture/m210-s02-owner-decision-packet.json`
(`law-nexus/m210-s02-owner-decision-packet/v1`, milestone `M210-3afp79`,
slice `S02`, task `T02`, lifecycle `[proposed]`, `authoritative: false`,
`semantics_adopted: false`).

This is the single human-readable entry for the S02 interactive owner
decision. It adopts no normative semantics, mints no Rust type, promotes no
requirement, changes no section 3 row and writes no Review Case event. The
machine-checked surface is the packet JSON, not this file.

## Scope

In scope for the S02 decision: choose one bounded normative IR alternative, or
reject all three, or defer. In scope for the separate F13 decision: adopt a
source-level amendment operation-candidate contract, or keep amendment
operations deferred.

Out of scope: any adoption of legal semantics, any runtime surface, any
section 3 term promotion, any requirement promotion, any Review Case event and
any implementation authorization.

The closed family dictionary used throughout is the T01 register set:
`obligation`, `permission`, `prohibition`, `definition`, `competence`,
`condition`, `exception`, `temporal_qualification`.

## Source revision and evidence class

The source revision shown to the owner is copied from the T01 rebind report
(`prd/architecture/m210-s02-rebind-report.json`):

```text
source_revision: sha256:618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7
```

Every tracked input behind this presentation was re-bound before it was shown:
the rebind report carries 18 rebound input rows, all verdict `match`, and 8
corpus anchors. The stored revision is a rebind-time snapshot, because the
engine aggregate hash includes untracked non-ignored files and is therefore not
reproducible after the report was written. The real stale gate is the per-input
live sha256, which the rebind contract re-derives on every run.

Evidence class by claim class:

| Claim class | Evidence class | What carries it |
|---|---|---|
| alternatives and their consequences | inert-artifact | `m210-s01-ir-alternatives.json` and its companion, re-hashed by the rebind report |
| dispute cards, negative examples, corpus anchors | source-bound-span | tracked anchors with live sha256 and byte spans; a span is an anchor, not a reading |
| runtime behaviour | runtime-absent | nothing: no normative IR, rule graph or applicability evaluator exists or is promised |

## Limitations and non-claims

Limitations carried by this presentation:

- corpus anchors are verified only when the licensed corpus resolves locally;
  in corpus-absent mode every anchor is marked `verified: false` with reason
  `corpus_absent`, so the owner would see explicitly unverified anchors rather
  than carried-over pins;
- the stored source revision is a rebind-time snapshot and is not reproducible
  afterwards; the stale gate is the per-input live sha256;
- two of the eight dispute cards are `conflicted` (`competence`,
  `temporal_qualification`) and six are `unresolved`; no card carries a
  `resolved` verdict;
- the `definition` family has no owning section 3 row (`no_owning_row`) and the
  `competence` ceiling is only `proposed`, so the family set is not uniformly
  bounded;
- no human-labelled gold set exists here and none is implied;
- no runtime surface exists or is promised;
- the recommendation below is advisory and is not the owner's consent.

Non-claims of this presentation:

- it is not an adoption of normative semantics;
- it is non-authoritative: it cannot satisfy a requirement, promote a
  lifecycle, close a gap row or establish legal correctness;
- the recommendation is not consent and the agent does not choose an option for
  the owner;
- the F13 question is a separate decision and an IR answer never determines it;
- an answer given in an interactive conduit is not an ADR, not a Review Case
  event and not an authorization to implement;
- section 3 is unchanged: the deferred terms stay deferred-undefined.

## Alternatives and consequences for S03

All three variants declare the same N to M provenance cardinality
(`provision_to_rule`: min 0, unbounded max; `rule_to_provision`: min 1,
unbounded max), so the cardinality contract does not depend on this choice.
None of the three proves legal correctness.

| Variant | id | Shape | Collapses | Consequence for S03 | Main collapse risk |
|---|---|---|---|---|---|
| A | `family_typed_record_ir` | one addressable record kind per family (eight kinds) plus a shared envelope and a separate link record | none | mint and validate eight record kinds plus envelope and link record; define Condition, Exception and Defeater first | a missing duty can be filed under the prohibition kind; a definition kind and an obligation kind can share an anchor |
| B | `single_facet_slot_rule_record` | one NormRule-like record whose family content lives in typed facets | definition | extend the existing `ln-applicability` NormRule spine (RC11-F04a) with a deontic operator, a definition scope and a competence source; define all six normative section 3 rows | an absent `deontic_operator` facet can default to permission or prohibition, collapsing absence of obligation into prohibition |
| C | `abstention_first_candidates_only` | no composed rule; source-bound candidates with a family classification and an Unknown or Conflict verdict | none | build only candidate emission and the fail-closed Unknown or Conflict verdicts; composition stays deferred | a classified candidate can be read as a composed rule; an absent candidate can be read as a negative finding |

The two alternatives that are not variants:

| Option | Consequence |
|---|---|
| reject all three | no bounded normative IR is adopted now; S03 has no adopted scope and a later decision must reopen the question with a fresh rebind |
| defer | the decision moves to a later slice; the packet stays proposed and unadopted and the question must be re-presented with a fresh rebind |

## Comparison with the existing NormRule spine

The existing `ln-applicability` NormRule spine (RC11-F04a) carries `id`,
`revision`, `conditions`, `exceptions`, `defeaters` and a temporal scope as
structural design types. Section 3 keeps NormRule and its relatives
deferred-undefined.

| Variant | Relation to the spine |
|---|---|
| A | reuses none of it and mints eight new record kinds, so nothing is duplicated but nothing is reused either; the spine stays unreferenced |
| B | closest to it: conditions map onto `condition_guard`, exceptions and defeaters onto `exception_defeater_list`, temporal scope onto `temporal_qualification`; the deontic operator, definition scope and competence source have no existing field, so it extends the spine and needs all six deferred rows |
| C | does not touch the spine at all; it stays an unreferenced structural design until a later ADR decides composition, and no new normative term is minted |

## Disputed cards and negative examples

The examples artifact carries exactly one dispute card per family: 8 cards, of
which 2 are `conflicted` (`competence`, `temporal_qualification`) and 6 are
`unresolved`. Every card sets `requires_human_source_review: true` and
`adopted: false`, and a `resolved` verdict is refused by construction. A
conflicted or unresolved card is a boundary, not a resolution.

Two negative examples mark the boundaries of this packet:

- `absence_of_obligation_is_not_prohibition` - a missing duty is not a ban;
- `lack_of_evidence_is_not_falsity` - an unproven claim stays Unknown.

## Proof ceiling

What this presentation does prove:

- structure: one owner question with a complete five-option set, a separate F13
  question and a recommendation that is explicitly not consent;
- anchors: every presented claim is bound to a rebound tracked input with a
  live sha256, and the source revision is copied from the T01 rebind report;
- boundaries: the documented fail-closed codes are empirically emitted by the
  packet contract on mutation;
- absence of preselection: no option is preselected and no answer is assumed.

What it does not prove:

- legal semantics: no alternative, family or reading here is legally correct;
- reading correctness: a conflicted or unresolved card is a boundary;
- human gold: no human-labelled gold set exists here;
- runtime fitness: no normative IR, rule graph or applicability evaluator
  exists or is promised;
- owner consent: a recommendation is not an answer and an answer in chat is not
  an adoption.

## Recommendation (advisory only, not consent)

Recommendation for the IR question: **option C,
`abstention_first_candidates_only`**. This is a recommendation, not consent, and
not an acceptance of semantics.

Rationale: all three alternatives are source-bound and none is adopted. C is
recommended because it defines no new section 3 term and composes no rule, so it
stays inside the deferred-undefined boundary that RC28-F18 declares, while A and
B both require deferred section 3 rows before any payload can be built.

Evidence behind the recommendation:

- `prd/architecture/m210-s01-ir-alternatives.json#variant:abstention_first_candidates_only`
- `prd/architecture/m210-s01-normative-family-register.json`
- `doc/review/review-28-10-09-2026.md#RC28-F18`
- `prd/architecture/m210-s02-rebind-report.json`

The owner may accept any option, reject all three, or defer. The agent does not
select an option for the owner.

## The exact IR question

Question id: `m210-s02-ir-question`.

```text
Which bounded normative IR alternative should the owner adopt:
A family_typed_record_ir, B single_facet_slot_rule_record,
or C abstention_first_candidates_only?
The owner may also reject all three or defer the decision.
No option is preselected and no answer is assumed here.
```

Accept one of A, B or C; or reject all three; or defer.

## F13 is a separate decision

Question id: `m210-s02-f13-question`. Origin: RC28-F13, which records amendment
syntax as the missing bridge to the temporal compiler and asks for
independently specified source-level operation candidates for replace, new
wording, insert, remove and repeal, with nested target scope and quoted
operands.

This is a separate decision with its own concrete alternative. An IR answer
never determines it, and inferring an F13 outcome from the IR choice is
forbidden. If no answer is given, F13 stays at **HOLD**.

| Option | Consequence |
|---|---|
| adopt a source-level amendment operation-candidate contract (design-only, owning contracts first) | an owning contract is created for the operation candidates; an extracted operation stays a candidate and is never an admitted MicroOperation, LegislativeEffect or InForce, and no automatic operation reinterpretation happens on missing operands |
| keep amendment operations deferred | amendment syntax stays an unowned gap; the bridge to the temporal compiler stays missing and the owning slice must reopen F13 with a fresh rebind before any bounded temporal replay can rely on it |

Recommendation for the F13 question: **keep amendment operations deferred**.
RC28-F13 is high severity and design class, but its owning surface is not this
decision: the review asks for owning contracts first, the recorded ownership
sits with the amendment and temporal-compiler work, and this packet's scope is
the bounded normative IR. Keeping amendment operations deferred answers F13 with
an explicit boundary instead of a silent omission. This is a recommendation,
not consent.

## Read-back template

After the owner answers, the following is shown back verbatim before anything is
recorded as a direction:

```text
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
```

Nothing is recorded as answered unless the interactive conduit returns a real
criterion, question and interaction reference. An absent or partial answer is a
sanctioned stop (`pending_human_decision`), not a failure and not a pass.

## Interactive conduit fields

These exact fields are passed to the authenticated interactive conduit; no
option is preselected and the recommended disposition is advisory:

| Field | Value |
|---|---|
| `criterionKey` | `m210-s02-ir-question` |
| `description` | Which bounded normative IR alternative should be adopted for the M210 bounded normative IR |
| `focusedPrompt` | The exact IR question above, with all five options and the note that no option is preselected |
| `recommendedDisposition` | `adopt abstention_first_candidates_only` (advisory only, not consent) |
| `recommendationRationale` | C defines no new section 3 term and composes no rule, so it stays inside the deferred-undefined boundary RC28-F18 declares |
| `recommendationEvidence` | The four evidence refs listed under the recommendation section |
| `testedSourceRevision` | `sha256:618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7` |

The F13 field set is passed as a second, separate question
(`criterionKey: m210-s02-f13-question`); the two are never merged.
