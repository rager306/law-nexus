# M210/S01 normative family register

**Lifecycle:** `[proposed]` design-only. **Authoritative:** false.
**Kind:** `m210-s01-normative-family-register` (machine form:
`prd/architecture/m210-s01-normative-family-register.json`).

This register is the S02 input that names the eight normative families RC28-F18
requires be separated, records the vocabulary status each family actually holds
today, and fixes the fail-closed boundary for each. It is a register, not an
adoption: no family, status or boundary below is accepted, promoted or made
executable by this document.

## Purpose and provenance

RC28-F18 (`doc/review/review-28-10-09-2026.md`) requires an explicit contract
separating obligation, permission, prohibition, definitions, competence,
conditions, exceptions and temporal qualification, and distinguishing absence of
obligation from prohibition and lack of evidence from falsity. This register is
the closed dictionary for that contract at T01 scope.

Statuses are copied from the owning sources, never assigned here:

- `prd/temporal-legal-model.md` section 3 holds `NormRule`, `Condition`,
  `LegalEffect`, `Exception` / `Defeater`, `ApplicabilitySelector` and the
  temporal rows as `deferred-undefined` or qualified-view-only.
- `prd/architecture/temporal-semantic-gap-register.md` holds TSG-005
  (norm-rule intermediate representation), TSG-006 (applicability protocol) and
  TSG-007 (competence, delegation, hierarchy) as active gaps with `[deferred]`
  or `[proposed]` ceilings.
- `prd/architecture/kb-ontology-l1-l3-draft.md` section 6 keeps a NormRule
  product graph out of L1-L3 core truth.

## Families

| family_id | vocabulary_status | owning_source | what_it_must_separate | unknown_outcome | conflict_outcome |
| --- | --- | --- | --- | --- | --- |
| obligation | deferred-undefined | `doc/review/review-28-10-09-2026.md` RC28-F18 | a duty to act from permission and from prohibition | no proven source span establishes a duty | two anchors disagree on whether a duty exists |
| permission | deferred-undefined | `doc/review/review-28-10-09-2026.md` RC28-F18 | an entitlement from the absence of a prohibition and from a duty | no proven source span establishes permission | two anchors disagree on whether the act is permitted |
| prohibition | deferred-undefined | `doc/review/review-28-10-09-2026.md` RC28-F18 | a ban from the absence of a duty and from permission | no proven source span establishes a ban | two anchors disagree on whether the act is banned |
| definition | no_owning_row | `doc/review/review-28-10-09-2026.md` RC28-F18 (no owning row) | a definitional norm from an obligation and from a condition | no proven source span establishes a definitional norm | two anchors disagree on what a term is defined as |
| competence | proposed | `prd/architecture/temporal-semantic-gap-register.md` TSG-007 | a power to act from a duty and from a permission of the addressee | no proven source span establishes a competence | two anchors disagree on which body is competent |
| condition | deferred-undefined | `prd/temporal-legal-model.md` section 3 Condition row | a guard on a norm from a factual premise and from an exception | no proven source span establishes a guard | two anchors disagree on the guard content |
| exception | deferred-undefined | `prd/temporal-legal-model.md` section 3 Exception / Defeater row | an exception or defeater from a condition and from a scope limitation | no proven source span establishes a defeat | two anchors disagree on whether the norm is defeated |
| temporal_qualification | proposed | `prd/temporal-legal-model.md` section 3 Event time row | the time a norm is qualified to from the time a fact occurred and from publication | the qualification is not proven, so the norm is not applied in time | two anchors disagree on the governing time |

### Status ceilings

`no_owning_row` < `deferred-undefined` < `proposed` < `bounded`. A family may
only be at or below the ceiling its owning source grants: obligation, permission,
prohibition, condition and exception at `deferred-undefined`; definition at
`no_owning_row` (there is no row to own it, and that gap is declared rather than
papered over with a minted term); competence and temporal_qualification at
`proposed`. Any higher status is the fail-closed code `status_promoted`.

## Negative distinctions

RC28-F18 names two collapses that must never hold. Each is a first-class row with
its own fail-closed code and non-claim.

| distinction_id | collapse forbidden | fail_closed_code | non-claim |
| --- | --- | --- | --- |
| absence_of_obligation_is_not_prohibition | a missing duty read as a ban | absence_of_obligation_conflated_with_prohibition | a missing duty is not a ban, and a ban is not a missing duty |
| lack_of_evidence_is_not_falsity | an unproven claim read as false | lack_of_evidence_conflated_with_falsity | an unproven claim stays Unknown; absence of a proven span is never falsity |

## Source-family axis

The eight families below are the source-side denominator families of the M209
corpus count (`prd/migration/rust-evidence/m209-s03-family-denominator.json`).
They are listed here only to fix the axis of N to M provenance. Each carries the
role `source-side axis of N to M provenance, not an IR family`: corpus families
are never assigned as normative IR families.

| source_family_id | kind |
| --- | --- |
| manifest_layer1_44fz_and_amending_laws | manifest |
| manifest_layer2_subordinate_normative_acts | manifest |
| manifest_layer3_court_practice_2025_2026 | manifest |
| manifest_layer3_fas_practice_2025_2026 | manifest |
| exports_npa | directory |
| exports_xml | directory |
| exports_courts | directory |
| exports_fas | directory |

## Fail-closed codes

The register refuses, never degrades. The documented code set is exactly:

- `unknown_family` - a family id outside the closed eight, or a family set that is not exactly the closed eight.
- `family_duplicated` - the same family id appears twice.
- `owning_source_missing` - a mandatory register or family field is missing, empty or drifted (owning-source path, section or hash included).
- `source_not_tracked` - a bound path is not a tracked repository-relative file (absolute, traversal, ignored or untracked).
- `source_hash_mismatch` - the declared sha256 of a bound path differs from the live file, or a pinned input carries a worktree delta.
- `status_unknown` - a closed-vocabulary value outside its dictionary (vocabulary status or evidence class).
- `status_promoted` - a family status above its owning-source ceiling, an authoritative claim, or a lifecycle above proposed.
- `negative_distinction_missing` - either required negative distinction is absent or has no fail-closed code.
- `source_family_as_ir_family` - a source-family axis row is not marked as non-IR, or the axis is not the M209 set.
- `runtime_claim_present` - a runtime marker appears in the register or its companion.
- `non_claims_missing` - the non-claims block is empty or absent.

## Not an adoption of semantics

- This register is not an adoption of normative semantics: no family, status or boundary here is accepted.
- It is non-authoritative: it cannot satisfy a requirement, promote a lifecycle, close a gap row or establish legal correctness.
- No runtime surface exists or is promised: there is no normative IR, no rule graph and no applicability evaluator.
- The source-family axis is a corpus denominator axis of N to M provenance, not an IR family.
- The vocabulary statuses are copied from the owning sources; a change there invalidates this register until it is re-derived.
- Definition is recorded as `no_owning_row`: the absence of a section 3 row is a declared gap, not a minted term.

## Revision policy

Re-derive before use: S02 must re-hash every source binding and owning-source
path, re-read each status from section 3 and the gap register, and re-bind this
register before showing it. No timestamp and no aggregate engine hash are stored
here; the contract compares the register byte for byte against its canonical
compact form.
