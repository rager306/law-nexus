# M210 S03 bounded semantics contract (design-only)

Companion to `prd/architecture/m210-s03-bounded-semantics-contract.json`
(`law-nexus/m210-s03-bounded-semantics-contract/v1`, milestone `M210-3afp79`,
slice `S03`, task `T02`, lifecycle `[proposed]`, `authoritative: false`,
`design_only: true`).

This document states the conditional semantics of the bounded semantic runtime.
It is a contract of what a future adopted construct could produce, not a
runtime. It adopts nothing, mints no candidate, composes no rule and edits no
section 3 row.

## What is conditional

The S02 admission checkpoint records `admission: not-adopted`, so the committed
`adopted_construct_set` is empty and `adopted_variant` is null. The whole
contract is conditional on that set:

- the closed eight-family dictionary (`obligation`, `permission`, `prohibition`,
  `definition`, `competence`, `condition`, `exception`,
  `temporal_qualification`) is not redeclared here; it is referenced from the
  S01 register by path and sha256, together with the vocabulary status of each
  family, and no status is promoted;
- a candidate can be emitted only when its `family_id` is in the
  `adopted_construct_set`, at least one proven source span establishes the
  family and the anchors agree;
- while the `adopted_construct_set` is empty, **no candidate can be emitted**
  and every outcome is `Unknown`.

`spec_table_is_not_adoption` is true: the outcome predicates below are a
specification, not an adoption, and the committed artifact must keep
`is_adoption: false`.

## The three outcomes

The outcome set is exactly `{candidate_emitted, Unknown, Conflict}`.

| Outcome | Predicate (summary) |
|---|---|
| `candidate_emitted` | `family_id` is in the closed eight, is in the `adopted_construct_set`, at least one proven source span establishes the family and the anchors agree |
| `Unknown` | no proven source span establishes the family, or no adopted construct exists; absence of a proven source span is never falsity |
| `Conflict` | at least two anchors of an adopted construct disagree; never a majority pick and never a silent preference |

Only `candidate_emitted` corresponds to an emitted candidate. `Unknown` and
`Conflict` are distinct non-emission outcomes: they must never be materialized
as candidates and must never be read as one another.

## Why Unknown is not Conflict

`Unknown` is the outcome when nothing has been proven: the evidence is missing,
so the honest result is abstention. `Conflict` is the outcome when at least two
anchors of an **adopted** construct actively disagree: the evidence is present
but contradictory. Collapsing them into one code would lose exactly the
distinction the closed family boundaries require, because absence of evidence is
not disagreement and disagreement is not absence.

Three consequences follow and all are fail-closed:

1. absence of a proven source span is never a negative finding (no
   `absence_as_falsity`);
2. `Unknown` and `Conflict` must remain separate outcomes with separate codes
   (no `unknown_conflict_collapsed`) and separate predicates (no
   `outcome_indistinct`);
3. with an empty `adopted_construct_set`, `Conflict` is unreachable
   (`conflict_unreachable_without_adoption`), so `Unknown` is the only possible
   outcome in the committed state.

## Candidate envelope and anchors

The candidate envelope is design-only and `minted: false`; `minted_field_count`
is zero. Its fields are `candidate_id`, `family_id`, `source_anchor`,
`evidence_class`, `verdict` and `adopted_construct_ref`.

An anchor without a repository-relative path and a sha256 is not an anchor
(`anchor_missing`). An `evidence_class` outside the closed dictionary
`{inert-artifact, source-bound-span, runtime-absent}` is inadmissible
(`evidence_class_unknown`). An envelope without an `adopted_construct_ref` is
not a candidate (`candidate_without_adopted_construct`).

## Emission rule

The emission rule is declared in the artifact and re-checked by the contract
test. A candidate requires an `adopted_construct_ref` inside the
`adopted_construct_set`. A `Conflict` requires an adopted construct and at
least two divergent anchors. Because the committed set is empty, the emission
rule mints zero candidates and `Conflict` is unreachable; the specification
truth table in `scripts/m210_s03_semantics_contract.test.mjs` proves this
against the abstract predicate `adopted`, which lives only in the test.

## Boundaries

Classification is not composition. No composed rule, no facet default and no
applicability evaluation is performed or promised (`composed_rule_emitted`,
`facet_default_applied`, `applicability_evaluated`). `NormRule`, `Condition`,
`LegalEffect`, `Exception`, `Defeater` and `ApplicabilitySelector` stay
`deferred-undefined`, and no section 3 row is minted or promoted
(`normrule_minted`, `section3_promoted`). F13 is a separate decision with its own
adoption and is never derived from the bounded IR (`f13_scope_borrowed`).
`Applicable`, RuVector and TEI are out of scope and are not claimed.

## Proof ceiling

This contract proves exactly three things: the outcome set is exactly three and
its predicates are distinguishable, a candidate cannot exist without an adopted
construct, and `Conflict` is unreachable while the `adopted_construct_set` is
empty. It does not prove that any family classification is legally correct, it
does not prove that any candidate is complete for a provision, and it does not
prove runtime fitness. The runtime is **not** adopted, **not** implemented and
**not** promised: no candidate was emitted, and the contract is a conditional
specification with a documented ceiling.

## What activates the grant

The contract becomes a runtime obligation only when a new source-bound owner
grant in the tracked repository names, through an authenticated interactive
source, the variant it adopts with its admissible scope and owning surfaces.
Until then `adopted_construct_set` stays empty, `is_adoption` stays false and
the contract stays conditional. A milestone lock, an integrity result or a
milestone closeout is never such a grant.

## Fail-closed boundary

`scripts/m210_s03_semantics_contract.test.mjs` rejects each declared condition
with its own named code, empirically, against a mutated copy of this contract:
`outcome_set_incomplete`, `outcome_indistinct`, `unknown_conflict_collapsed`,
`candidate_without_adopted_construct`, `conflict_without_adopted_construct`,
`anchor_missing`, `evidence_class_unknown`, `composed_rule_emitted`,
`facet_default_applied`, `applicability_evaluated`, `normrule_minted`,
`section3_promoted`, `spec_table_as_adoption`, `absence_as_falsity`,
`f13_scope_borrowed`, `runtime_claim_present`, `non_ascii_artifact`,
`raw_text_leak`.

## Non-claims

- This contract is design-only and commits no record.
- It is not an adoption of normative semantics; a specification table is not an
  adoption.
- `Unknown` is not `Conflict`, and absence of a proven source span is never
  falsity.
- Classification is not composition.
- The six section 3 terms stay `deferred-undefined` and no term is promoted.
- F13 stays on hold and is separate.
- No candidate can be emitted and `Conflict` is unreachable while the
  `adopted_construct_set` is empty.
