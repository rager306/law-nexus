# M210 S03 bounded semantics contract (design-only)

Companion to `prd/architecture/m210-s03-bounded-semantics-contract.json`
(`law-nexus/m210-s03-bounded-semantics-contract/v1`, milestone `M210-3afp79`,
slice `S03`, task `T02`, lifecycle `[proposed]`, `authoritative: false`,
`design_only: true`).

This document states the semantics of the bounded semantic runtime now that the
owner has established an authenticated adoption. It is a contract of what an
executed adopted construct could produce, not a runtime. It composes no rule,
mints no candidate and edits no section 3 row.

## What is conditional

The S02 v2 admission checkpoint records `admission: granted` for variant `C`
(`abstention_first_candidates_only`), so `adoption_state.adoption_established` is
true and `adopted_construct_set` carries the adopted candidate layer:
`candidate_emission`, `source_anchors`, `family_classification_hypotheses`,
`unknown_verdict`, `conflict_verdict`, `provenance_links`.

The closed eight-family dictionary (`obligation`, `permission`, `prohibition`,
`definition`, `competence`, `condition`, `exception`, `temporal_qualification`)
is not redeclared here; it is referenced from the S01 register by path and
sha256, together with the vocabulary status of each family, and no status is
promoted. Adopting the candidate layer is not a promotion of normative
semantics: `normative_semantics_adopted` is false and `promoted_statuses` is
empty.

The contract is still conditional in a second sense. Adoption is established, but
execution is not: `execution_state.executed` is false, `candidates_emitted` is
zero and `conflicts` is zero. Until execution actually establishes proven source
spans, no candidate is emitted and `Conflict` is unreachable, so every outcome is
`Unknown`. The outcome table below is a specification, not the adoption
instrument.

## Adoption is not execution

Adoption and execution are two separate states and are never read as one another:

- `adoption_state` is established from the authenticated S02 v2 grant. It names
  the variant, the adopted construct set and the objective admission reference.
- `execution_state` records that nothing ran. `executed` is false, no candidate
  was emitted and no conflict was found.

Reading adoption as execution is refused by name
(`adoption_read_as_execution`): adoption alone never mints a candidate and never
makes `Conflict` reachable. Reading execution as adoption is refused by name
(`execution_read_as_adoption`): a run that produced no authenticated adoption
never becomes an adoption, and `adoption_state.adoption_established` is never
derived from `execution_state`.

## The three outcomes

The outcome set is exactly `{candidate_emitted, Unknown, Conflict}`.

| Outcome | Predicate (summary) |
|---|---|
| `candidate_emitted` | the `adopted_construct_ref` is in the `adopted_construct_set` and the construct was actually executed: at least one proven source span establishes the family in execution and the anchors agree |
| `Unknown` | no proven source span has been established in execution, because execution was not performed or no span was proven; absence of a proven source span is never falsity |
| `Conflict` | at least two anchors of an adopted construct diverge in execution; never a majority pick and never a silent preference |

Only `candidate_emitted` corresponds to an emitted candidate, and only after
execution. `Unknown` and `Conflict` are distinct non-emission outcomes: they must
never be materialized as candidates and must never be read as one another.

## Why Unknown is not Conflict

`Unknown` is the outcome when nothing has been proven in execution: the evidence
is missing, so the honest result is abstention. `Conflict` is the outcome when at
least two anchors of an **executed adopted** construct actively disagree: the
evidence is present but contradictory. Collapsing them into one code would lose
exactly the distinction the closed family boundaries require, because absence of
evidence is not disagreement and disagreement is not absence.

Three consequences follow and all are fail-closed:

1. absence of a proven source span is never a negative finding (no
   `absence_as_falsity`);
2. `Unknown` and `Conflict` must remain separate outcomes with separate codes
   (no `unknown_conflict_collapsed`) and separate predicates (no
   `outcome_indistinct`);
3. Conflict is unreachable without execution: it requires an executed adopted
   construct and at least two divergent anchors, so while
   `execution_state.executed` is false, `Unknown` is the only possible outcome.

## Candidate envelope and anchors

The candidate envelope is design-only and `minted: false`; `minted_field_count`
is zero. Its fields are `candidate_id`, `family_id`, `source_anchor`,
`evidence_class`, `verdict` and `adopted_construct_ref`.

An anchor without a repository-relative path and a sha256 is not an anchor
(`anchor_missing`). An `evidence_class` outside the closed dictionary
`{inert-artifact, source-bound-span, runtime-absent}` is inadmissible
(`evidence_class_unknown`). An envelope without an `adopted_construct_ref` is not
a candidate (`candidate_without_adopted_construct`).

## Emission rule

The emission rule is declared in the artifact and re-checked by the contract
test. A candidate requires an `adopted_construct_ref` inside the
`adopted_construct_set` and an executed construct. A `Conflict` requires an
executed adopted construct and at least two divergent anchors. Because execution
has not run, the emission rule mints zero candidates and `Conflict` is
unreachable; the specification truth table in
`scripts/m210_s03_semantics_contract.test.mjs` proves this against the abstract
predicate `executed`, which lives only in the test.

## Boundaries

Classification is not composition. No composed rule, no precedence resolution,
no facet default and no applicability evaluation is performed or promised
(`composed_rule_emitted`, `facet_default_applied`, `applicability_evaluated`).
`NormRule`, `Condition`, `LegalEffect`, `Exception`, `Defeater` and
`ApplicabilitySelector` stay `deferred-undefined`, and no section 3 row is minted
or promoted (`normrule_minted`, `section3_promoted`). F13 is a separate decision
with its own adoption and is never derived from the bounded IR
(`f13_scope_borrowed`). `Applicable`, RuVector and TEI are out of scope and are
not claimed.

## Proof ceiling

This contract proves exactly four things: the outcome set is exactly three and
its predicates are distinguishable, `Unknown` and `Conflict` are not collapsed,
a candidate requires an adopted construct and actual execution, and Conflict is
unreachable without execution. It does not prove that any family classification
is legally correct, it does not prove that any candidate is complete for a
provision, and it does not prove runtime fitness. Normative semantics are **not**
adopted by this contract, execution has **not** happened and no candidate was
emitted: the runtime is a conditional specification with a documented ceiling.

## Fail-closed boundary

`scripts/m210_s03_semantics_contract.test.mjs` rejects each declared condition
with its own named code, empirically, against a mutated copy of this contract:
`outcome_set_incomplete`, `outcome_indistinct`, `unknown_conflict_collapsed`,
`candidate_without_adopted_construct`, `conflict_without_adopted_construct`,
`anchor_missing`, `evidence_class_unknown`, `adoption_read_as_execution`,
`execution_read_as_adoption`, `composed_rule_emitted`, `facet_default_applied`,
`applicability_evaluated`, `normrule_minted`, `section3_promoted`,
`absence_as_falsity`, `f13_scope_borrowed`, `runtime_claim_present`,
`non_ascii_artifact`, `raw_text_leak`.

## Non-claims

- This contract is design-only and commits no record.
- It is not an adoption of normative semantics; the adopted candidate layer is
  not a promotion of the eight families.
- Adoption is not execution, and execution is not adoption.
- `Unknown` is not `Conflict`, and absence of a proven source span is never
  falsity.
- Classification is not composition.
- The six section 3 terms stay `deferred-undefined` and no term is promoted.
- F13 stays on hold and is separate.
- No candidate is emitted and `Conflict` is unreachable while
  `execution_state.executed` is false, even though the adopted construct set is
  non-empty.
