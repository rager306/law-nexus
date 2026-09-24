# M210 S01 normative IR alternatives (design-only)

Companion to `prd/architecture/m210-s01-ir-alternatives.json`
(`law-nexus/m210-normative-ir-alternatives/v1`, milestone `M210-3afp79`,
slice `S01`, task `T02`, lifecycle `[proposed]`, `authoritative: false`,
`semantics_adopted: false`).

This is the comparison input for the S02 interactive decision. It presents
three source-bound alternatives for a bounded normative IR. It adopts none of
them, mints no Rust type, changes no section 3 row and writes no Review Case
event. The recommendation at the end is advisory only.

## Variants

| Variant | id | Shape | Separates | Collapses | New section 3 terms |
|---|---|---|---|---|---|
| A | `family_typed_record_ir` | one addressable record kind per family plus a shared envelope and a separate link record | all eight | none | Condition, Exception, Defeater |
| B | `single_facet_slot_rule_record` | one NormRule-like record whose family content lives in typed facets | seven | definition | NormRule, Condition, LegalEffect, Exception, Defeater, ApplicabilitySelector |
| C | `abstention_first_candidates_only` | no composed rule; source-bound candidates with a family classification and an Unknown or Conflict verdict | all eight | none | none (empty on purpose) |

Family dictionary (closed, from RC28-F18 via the T01 register): `obligation`,
`permission`, `prohibition`, `definition`, `competence`, `condition`,
`exception`, `temporal_qualification`.

Variant B records `definition` as collapsed because a definitional norm is
carried as a `definition_scope` facet of the same rule record, so the
definition/rule boundary is not type-enforced. Variants A and C collapse no
family; their honest limits live in `collapse_risks` instead.

## N to M provenance cardinality

All three variants declare the same shape, so the cardinality contract does not
depend on the S02 choice:

```text
  source provisions (unbounded)                family records / rules (unbounded)
        |                                                    |
        |  provision_to_rule: min 0, max N                   |
        +-------------- link records (N to M) ---------------+
                                                             |
                       rule_to_provision: min 1, max M ------+
```

| Direction | min | max | Policy field | What the policy states |
|---|---|---|---|---|
| `provision_to_rule` | 0 | `N` | `unknown_policy` | a provision with no record yields Unknown; absence of provenance is never the statement that no rule exists |
| `rule_to_provision` | 1 | `M` | `unresolved_policy` | a record without at least one resolved anchor is unresolved and cannot be emitted as resolved |

`max` is the unbounded token, not a number: the direction is N to M, never 1 to
1 and never a fixed ceiling. Quietly collapsing this cardinality is forbidden
and is reported with the code `cardinality_collapsed`.

## Provenance contract rules

Link record form: `from`, `to`, `family`, `evidence_class`,
`source_anchor {path, span, sha256}`, `verdict` from `{resolved, unresolved,
conflicted}`, `non_claims`.

- `absence_yields_unknown` - absence of provenance yields Unknown; it never
  means that no rule exists.
- `unresolved_anchor_yields_unresolved` - an unresolved static anchor yields
  verdict unresolved, never a resolved link and never a silent omission.
- `contradiction_yields_conflicted` - two anchors that contradict each other
  yield verdict conflicted, never a majority pick.
- `cardinality_collapse_forbidden` - silent collapse of the declared N to M
  cardinality is forbidden and is reported with the code `cardinality_collapsed`.

## Consequences and risks

| Variant | Consequence for S03 | Main collapse risk |
|---|---|---|
| A | mint and validate eight record kinds plus envelope and link record; define Condition, Exception and Defeater first | a missing duty can be filed under the prohibition kind; a definition kind and an obligation kind can share an anchor |
| B | extend the existing `ln-applicability` NormRule spine (RC11-F04a) with a deontic operator, a definition scope and a competence source; define all six section 3 rows | an absent `deontic_operator` facet can default to permission or prohibition, collapsing absence of obligation into prohibition |
| C | build only candidate emission and the fail-closed Unknown or Conflict verdicts; composition stays deferred | a classified candidate can be read as a composed rule; an absent candidate can be read as a negative finding |

None of the three proves legal correctness: each `what_it_cannot_prove` list
says so explicitly. The N to M cardinality is a declared contract shape, not
evidence that any provision-to-rule link is proven.

## Decision question

Asked of the human owner in S02: which normative IR alternative should be
adopted for the bounded normative IR - A `family_typed_record_ir`,
B `single_facet_slot_rule_record`, or C `abstention_first_candidates_only`? The
owner may also reject all three or defer the decision. No option is preselected
and no consent is prefilled. An answer in chat is not an ADR, not a Review Case
event and not an authorization to implement.

## Not an adoption of semantics

- This artifact is not an adoption of normative semantics: no variant,
  cardinality or reading here is accepted.
- It is non-authoritative: it cannot satisfy a requirement, promote a lifecycle,
  close a gap row or establish legal correctness.
- No runtime surface exists or is promised: no normative IR, no rule graph and
  no applicability evaluator is created here.
- The recommendation is advisory only and is not the owner's decision.
- Section 3 is unchanged: the deferred terms stay deferred-undefined.

Revision policy: S02 must re-hash every source binding, re-read the section 3
and gap-register statuses and re-bind this artifact before showing it. No
timestamp and no aggregate engine hash are stored here.

## Fail-closed codes

- `variant_count_insufficient` - fewer than three alternatives are present.
- `variant_id_duplicated` - two alternatives share an id.
- `missing_required_field` - a required field, source binding or frozen input is
  absent, empty or drifted.
- `cardinality_not_nm` - a cardinality side is not declared as N to M with min,
  unbounded max and policy.
- `cardinality_collapsed` - silent collapse of the declared cardinality is
  allowed or its forbidding rule is missing.
- `adoption_claim` - a variant claims adoption, or the artifact claims
  authority or a non-proposed lifecycle.
- `semantics_adopted_claim` - the artifact claims that normative semantics are
  adopted.
- `collapse_risk_missing` - a variant names no collapse risk.
- `deferred_term_unlisted` - a required new ADR term is outside the closed
  section 3 deferred set, or an empty list carries no rationale.
- `non_claims_missing` - the non-claims block is missing or empty.
