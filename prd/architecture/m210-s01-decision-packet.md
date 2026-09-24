# M210 S01 decision packet for the bounded normative IR (design-only)

Companion to `prd/architecture/m210-s01-packet-index.json`
(`law-nexus/m210-packet-index/v1`, milestone `M210-3afp79`, slice `S01`,
task `T04`, lifecycle `[proposed]`, `authoritative: false`,
`semantics_adopted: false`).

This is the single presentation entry for the S02 interactive decision. It
adopts no normative semantics, mints no Rust type, writes no Review Case event
and promotes no requirement. The packet index - not this file - is the
machine-checked surface: it pins every package artifact and every tracked input
by sha256.

## Scope

In scope for the S02 decision: choose one bounded normative IR alternative, or
reject all three, or defer. Out of scope for this packet: any adoption of legal
semantics, any runtime surface, any section 3 term promotion, any requirement
promotion, any Review Case event.

The closed family dictionary used throughout is the T01 register set:
`obligation`, `permission`, `prohibition`, `definition`, `competence`,
`condition`, `exception`, `temporal_qualification`.

## Source revision and re-binding

S02 must re-bind every tracked input and re-derive the corpus anchors before
showing this packet. Every entry in `artifacts[]` and `source_bindings[]` of the
packet index carries a repository-relative path and a sha256 of the live file;
a drift in any of them is a fail-closed condition, not a warning.

The aggregate engine hash is not stored in this packet and is not hardcoded
anywhere in it: it is supplied at validate time by the validating unit and
compared there. `source_revision_policy` in the packet index states this and
`hardcode_forbidden` is asserted true by the slice battery contract.

## Alternatives

Three source-bound alternatives are presented by the T02 artifact. All three
declare the same N to M provenance cardinality, so the cardinality contract does
not depend on this choice.

| Variant | id | Shape | Collapses | Consequence for S03 | Main collapse risk |
|---|---|---|---|---|---|
| A | `family_typed_record_ir` | one addressable record kind per family, plus a shared envelope and a separate link record | none | mint and validate eight record kinds plus envelope and link record; define Condition, Exception and Defeater first | a missing duty can be filed under the prohibition kind; a definition kind and an obligation kind can share an anchor |
| B | `single_facet_slot_rule_record` | one NormRule-like record whose family content lives in typed facets | definition | extend the existing `ln-applicability` NormRule spine (RC11-F04a) with a deontic operator, a definition scope and a competence source | an absent `deontic_operator` facet can default to permission or prohibition, collapsing absence of obligation into prohibition |
| C | `abstention_first_candidates_only` | no composed rule; source-bound candidates with a family classification and an Unknown or Conflict verdict | none | build only candidate emission and the fail-closed Unknown or Conflict verdicts; composition stays deferred | a classified candidate can be read as a composed rule; an absent candidate can be read as a negative finding |

None of the three proves legal correctness. The N to M cardinality
(`provision_to_rule`: min 0, unbounded max; `rule_to_provision`: min 1, unbounded
max) is a declared contract shape, never evidence that any link is proven.
Silent collapse of that cardinality is forbidden and is reported with the code
`cardinality_collapsed` by the T02 contract.

## Disputed readings and negative examples

The T03 artifact carries exactly one dispute card per family: 8 cards, of which
2 are `conflicted` (`competence`, `temporal_qualification`) and 6 are
`unresolved`. Every card is bound to a tracked source anchor with a live
sha256, sets `requires_human_source_review: true` and `adopted: false`, and
refuses a `resolved` verdict by construction.

Two negative examples mark the boundaries of this packet:

- `absence_of_obligation_is_not_prohibition` - a missing duty is not a ban.
- `lack_of_evidence_is_not_falsity` - an unproven claim stays Unknown.

The bounded corpus probe set records only path, span, bytes and sha256 for 8
regular corpus files. No legal text is copied into any artifact, and a family
label on a probe is a coverage label, not a claim about the span.

## Proof ceiling

What this packet does prove:

- structure: the packet has a closed family dictionary, three alternatives and a
  declared N to M provenance contract;
- anchors: every claim is bound to a tracked source anchor with a live sha256;
- fail-closed boundaries: the documented codes are empirically emitted by the
  enforcing contracts;
- the presence of alternatives: three distinct IR alternatives exist and none is
  preselected.

What this packet does not prove:

- legal semantics: no reading, verdict or family membership is legally correct;
- reading correctness: a `conflicted` or `unresolved` card is a boundary, not a
  resolution;
- human gold: no human-labelled gold set exists here and none is implied;
- runtime fitness: no normative IR, rule graph or applicability evaluator exists
  or is promised.

## Non-claims

- This packet is not an adoption of normative semantics: no reading, card,
  variant or verdict here is accepted.
- It is non-authoritative: it cannot satisfy a requirement, promote a lifecycle,
  close a gap row or establish legal correctness.
- No runtime surface exists or is promised: no normative IR, no rule graph and
  no applicability evaluator is created here.
- The recommendation carried by the T02 artifact is advisory only and is not the
  owner's consent.
- Section 3 is unchanged: the deferred terms stay deferred-undefined.

## Decision question

Decision question for the owner: which bounded normative IR alternative should be adopted - A family_typed_record_ir, B single_facet_slot_rule_record, or C abstention_first_candidates_only? Accept one of A, B or C; or reject all three; or defer.

The recommendation in the packet is not consent. An answer in chat is not an
ADR, not a Review Case event and not an authorization to implement.

## Fail-closed codes

- `battery_failed` - the slice battery reports a failed contract, a missing
  contract or a check total below the floor.
- `artifact_missing` - a declared artifact path is absent, empty or unresolvable.
- `artifact_hash_mismatch` - a declared artifact sha256 differs from the live
  file.
- `artifact_outside_allowed_roots` - a declared artifact path is outside `prd/`
  and `scripts/`.
- `crates_path_in_packet` - a declared artifact path is under `crates/`, so the
  packet claims product runtime.
- `guard_asserted` - a guard is missing or asserted (`product_runtime_changed`,
  `semantics_adopted`, `review_case_events_written`, `requirements_promoted`,
  `crates_touched`).
- `proof_ceiling_incomplete` - the proof ceiling is missing its proven set, its
  unproven set or a required unproven topic.
- `aggregate_hash_hardcoded` - the aggregate engine hash is stored in the packet
  or the policy stops forbidding that.
- `decision_question_missing` - the decision packet lacks the exact owner
  question or the non-claims block.
- `runtime_claim_present` - a packet file carries a Rust implementation marker.
