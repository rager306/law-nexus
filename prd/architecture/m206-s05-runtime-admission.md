# M206/S05 runtime admission: RC28-F06..F12 grammar context and binding candidates

**admission: granted**
**granted_by: owner (interactive session instruction, 2026-09-14 ~15:05Z, option A)**
**scope: M206/S05 runtime implementation of RC28-F06, RC28-F07, RC28-F08, RC28-F09, RC28-F10, RC28-F11, RC28-F12**
**classification: source-bound runtime admission**
**runtime_stop: lifted for M206/S05 scope only**
**prerequisites: M204-w2ktfw complete (validated pass, human adoption accepted); M205-p7xc54 complete (validated pass, human adoption accepted)**
**human_adoption_for_m204_m205: accepted**
**resume_of: prd/architecture/m206-s01-adoption-state.md, prd/architecture/m206-s02-adoption-state.md, prd/architecture/m206-s03-adoption-state.md, prd/architecture/m206-s04-adoption-state.md**

## Purpose and boundary

This document is the new explicit source-bound owner admission required by the
resume conditions recorded in the M206 adoption-state documents
(s01/s02/s03/s04). The owner granted runtime admission for milestone
M206-jnbhlz slice S05 on 2026-09-14 via the interactive operator session
(owner instruction selecting the admission option; recorded by the operator in
this tracked document because a chat instruction is not itself source-bound).

This admission covers the owning product surfaces named by the review packet
RC-2026-09-10-001 (source: doc/review/review-28-10-09-2026.md):

- `crates/ln-decode/src/document_context.rs` — RC28-F06 sibling/parent
  closure, RC28-F07 continuation eligibility;
- `crates/ln-decode/src/local_grammar.rs` — RC28-F09 local grammar origins;
- `crates/ln-decode/src/lawref.rs` — RC28-F10 token/range variant
  normalization;
- `crates/ln-decode/src/document_context.rs` (CurrentDocumentRequisites
  dispatch) and `crates/ln-temporal/src/document_context.rs` — RC28-F08
  ThisRef evidence parity;
- `crates/ln-temporal/src/semantic_scope.rs` — RC28-F11 token-bound cue
  matching, scoped negation, source-backed participant spans;
- RC28-F12 self/antecedent/alias/edition authorization — design separation
  realized across the surfaces above.

## Accepted policies, gates and runtime-test surfaces

The runtime implementation must be proven by the future-battery scenarios
declared (not executed) in the adoption-state documents, now admitted as the
owning runtime-test surfaces for S05:

- F09 scenarios: `F09-independent-sentences`, `F09-incomplete-tail`,
  `F09-boundaries`, `F09-refused-token-only`, `F09-identical-origins`,
  `F09-overlap`, `F09-order` (source: m206-s02-adoption-state.md);
- F10 scenarios: `F10-original-spans` (source: m206-s02-adoption-state.md);
  F06/F10 composition and lexical scope from the descoped S01 T03/T04
  charters (source: m206-s01-adoption-state.md, 206-01-REPLAN.md);
- S03/S04 no-start contracts: `scripts/m206_s03_adoption_contract.test.mjs`,
  `scripts/m206_s04_adoption_contract.test.mjs`,
  `scripts/m206_s02_t02_verify.sh` stay green (documents remain accurate as
  provenance records; they do not gate runtime code, they gate their own
  document state);
- regression invariants: R086 structural/profile/article-body suites and
  R087 component-path/membership/unknown-forms suites (validated) must pass
  unchanged unless a source-bound regression is itself the finding under
  repair with a reproducing test;
- standard gates: `cargo fmt --all --check`, `cargo check --workspace
  --offline`, targeted `cargo test -p <crate> --offline --test <suite>`,
  `uv run python -m law_nexus_harness governor` advisory run (status report
  cited, not smoothed).

## Prerequisites confirmed

M204-w2ktfw is complete with validated pass (2026-09-14, tested source
revision sha256:f3c2b564… era, human adoption accepted by the owner).
M205-p7xc54 is complete with validated pass (2026-09-14, human adoption
accepted; interaction d1630290; TSR sha256:021dafc7…). Both are recorded in
the GSD registry and their 20X-SUMMARY projections.

## Non-claims

- This admission is not product readiness, not a `[validated]` lifecycle
  promotion, and not a corpus-wide correctness claim.
- It does not amend ADR-0028 lifecycle, the M205 pins, requirements register,
  findings dispositions, or roadmap status of any other milestone.
- Pullenti remains a development-stage prior-art alphabet (D380); no Pullenti
  port is admitted.
- NormRule, Condition, LegalEffect, Exception and force vocabulary stays
  deferred-undefined; cue recognition is not a NormRule; no cross-block
  TextAnchor; no TokenKind widening beyond the owning contracts.
- The admission does not by itself complete M206/S05: implementation requires
  the separately sanctioned S05 plan (the in-progress refine/plan cycle) and
  each task still passes its own verification gate.

## Interaction with earlier states

- The S01 owner Reject (interaction 04fd05a2-338f-45af-a1cc-13501717dc53,
  2026-09-14) remains the historical provenance of the S01 stop; this
  admission supersedes the runtime stop it recorded, for M206/S05 scope only.
- The S01–S04 adoption-state documents and no-start contracts remain immutable
  evidence; their `runtime_stop_active` lines are historical records of the
  state before this admission and are not rewritten retroactively.
- If fresh sources contradict this record, the result is a blocker; no policy
  is chosen by inference.

This document is repository-relative, tracked, and design-side. Its sole
purpose is to convert the owner's runtime-admission decision into the
source-bound form required by the M206 resume conditions.
