# M210 S02 adoption checkpoint v2

Supersedes `prd/architecture/m210-s02-adoption-checkpoint.md` (v1) under the
RC28-F19 append-or-supersede policy: v1 stays byte-identical; nothing is
rewritten behind it. This checkpoint records the owner's authenticated
interactive decision on the bounded normative IR.

**admission: granted**

Scope of the grant is bounded exactly to what the owner adopted: variant C,
`abstention_first_candidates_only` - source-bound candidate emission with
explicit Unknown or Conflict verdicts. Rule composition, precedence
resolution, facet defaults and case applicability remain outside the adopted
scope and stay unavailable. The final format of normative rules is a separate
future decision; this grant does not preselect it.

**owner_admission_ref:** subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f, question 57ef54f3-aa0a-4e5e-82a7-b4dc7057e25c, interaction 456709c8-4da5-4835-a0fe-7a2af3a45e64 (disposition accepted, authenticated channel)
**interaction_ref:** answer-record-v2 `prd/architecture/m210-s02-answer-record-v2.json`, sha256 b45762e9cb0a67dc7b7eb01501a347200ae652be0381efa7db876ff4c3e4c8cd
**interaction_ref_2:** subjective-UAT criterion 70e39300-851b-4412-a322-a8f0c51ca71c, question a4b5bc2d-0519-45db-bc78-a5d0a3b6a99d, interaction 5bb68ce2-fdfe-47ac-8db3-e1446377f38c (disposition accepted, authenticated channel)
**tested_source_revision:** sha256:618aaf127decb28e211b9fbb044516f442c55b25be90d47e197abaf5311c6eb7 (rebind check re-verified M210_S02_REBIND_CHECK_OK immediately before the questions)
**f13_status:** deferred-explicit (owner answered: keep amendment operations deferred; the owning slice reopens F13 with a fresh rebind before any bounded temporal replay relies on it)
**review_case_events_written:** 0
**requirements_promoted:** 0

## Basis

The v1 resume condition required a real interactive owner reference and a
separately verified governing surface. Both are now satisfied for the bounded
scope: the authenticated subjective-UAT channel recorded the owner's accepted
dispositions bound to the shown revision, and the owner's verbatim direction
is preserved unedited in the answer record v2 (Russian verbatim retained
intentionally; ASCII-only is not asserted for that artifact). The v1
`governing_surface_absent` finding applied to the v1 state, where no such
record existed; this checkpoint and the answer record v2 now carry the human
adoption decision as tracked, hash-bound surfaces.

## What the grant permits and forbids

Permitted: implementation of the adopted candidate layer only - candidate
emission, source anchors, family classification hypotheses, Unknown and
Conflict verdicts, provenance links, their contracts, diagnostics and tests.

Still forbidden without a separate adopted contract: rule composition,
facet defaults, precedence, exception defeat mechanics, case applicability,
any promotion of section 3 terms, any Review Case event, any human-gold
accuracy claim. The three section 3 rows that variants A and B would require
are not defined and are not needed by variant C.

**runtime_stop:** lifted for the adopted candidate-layer scope only; it stays
active for composed-rule runtime, applicability runtime and any section 3
promotion.

## Sources

| Source | sha256 |
|---|---|
| prd/architecture/m210-s02-adoption-checkpoint.md (superseded v1) | 31ed55b9f5db500a40441ce642b773127b6523b016a2453038fc8648d81f7031 |
| prd/architecture/m210-s02-answer-record.json (superseded v1) | efc1b820506dabadde87d1ff8f338b95d6bd85417bce127ca17a07e5b3f9528b |
| prd/architecture/m210-s02-answer-record-v2.json | b45762e9cb0a67dc7b7eb01501a347200ae652be0381efa7db876ff4c3e4c8cd |
| prd/architecture/m210-s02-owner-decision-packet-v2.json | e0900eb3480e601126ca499e5b6c77da95c9bb1d0077b3aa7b7f18959240517d |
| prd/architecture/m210-s02-owner-decision-presentation-v2.md | 0b17919a62b7c1ef27f44e6a761de0c3f781d6920315b2ad89c922ba5789afeb |
| prd/architecture/m210-s02-packet-corrections-v2.md | 582c28158f7bfdce06f8ab8221714d21e2e131de8addd65f5170ca626ab32355 |
| prd/architecture/m210-s02-rebind-report.json | e6689b8137534eb7a6d367e78d87e21329d33bc6fa601edb382e49bd5221736b |
| prd/temporal-legal-model.md (section 3, byte-identical to pin) | a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6 |

## Next gate

The S03 T01 start gate re-verifies this checkpoint at S03 start: admission
verdict, adopted scope (variant C only), interactive references and the
section 3 pin. Any drift fails closed. Runtime work outside the candidate
layer still requires its own adopted contract and its own checkpoint.

## Non-claims

This checkpoint is not a legal conclusion, not a Review Case disposition, not
a requirement closure and not an ADR. It does not prove the legal correctness
of any classification or reading. It records a human design-direction decision
with its interactive evidence and bounds what may be implemented next.
